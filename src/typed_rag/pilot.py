"""Stage 7: the frozen technical-pilot subset and a minimal sequential batch runner.

What this module does:

* derives the *matched* subset from the reviewed fault cases: a question enters
  the technical pilot only when all four of its candidate contexts are approved
  with the observed state equal to the intended state (CLEAN->OK, PARTIAL->PARTIAL,
  EMPTY->EMPTY, INCONSISTENT->INCONSISTENT); everything else stays in the source
  data and is listed with its exclusion reason;
* freezes a plan: a manifest binding the exact question texts, ordered documents,
  review/annotation files, index identity, prompts, schemas, controller policy,
  model parameters, design (branches x conditions x repeats) and implementation
  files by SHA-256, plus one stable run identifier per planned pipeline run and
  a deterministic shuffled execution order;
* executes the plan sequentially through the existing stage 5 controller with a
  mandatory API-call budget, a checkpoint after every pipeline run and a resume
  that never repeats a finished, failed or interrupted run;
* dry-runs the plan without an API key, a client or any network traffic;
* summarises executed (or explicitly mock) trajectories as diagnostics.

What this module deliberately does not do: it never regenerates faults, never
selects replacement questions, never touches the index, never reads a gold
answer inside the execution path (only the dry-run isolation check and the
summary read research metadata), never caches or reuses an LLM response, and
never converts a technical failure or a budget stop into an abstention.

This is a technical pilot on a selected subset, not a confirmatory study.
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from typed_rag import controller, fault_cases, hotpotqa, llm, nodes, rag_run, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.download import sha256_file
from typed_rag.llm import Transport

PLAN_FORMAT_VERSION = "1.0"
MODE = controller.MODE_PILOT

MANIFEST_FILENAME = "manifest.json"
RUNS_FILENAME = "runs.jsonl"
BATCH_FILENAME = "batch.json"
CHECKPOINT_FILENAME = "checkpoint.jsonl"
BUDGET_FILENAME = "budget.json"
RUNS_DIRNAME = "runs"
SUMMARY_FILENAME = "summary.json"
DRY_RUN_FILENAME = "dry_run.json"
REPRESENTATIVE_FILENAME = "representative_requests.json"
PROBE_DIRNAME = "_path_probe"

# Windows refuses a path of 260 characters or more unless long paths are enabled for the
# host; other systems are far more permissive. The batch runner checks its own output paths
# against this limit before the first provider call rather than failing after one.
MAX_OUTPUT_PATH = 260

EXECUTION_REAL = "real"
EXECUTION_MOCK = "mock"

EVENT_STARTED = "started"
EVENT_FINISHED = "finished"

# Run-level bookkeeping of the batch (distinct from the controller's run status).
RUN_PENDING = "pending"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"
RUN_INTERRUPTED = "interrupted"
RUN_API_BUDGET_STOPPED = "api_budget_stopped"
RUN_RETRY_BUDGET_EXHAUSTED = "retry_budget_exhausted"

IMPLEMENTATION_FILES = (
    "src/typed_rag/controller.py",
    "src/typed_rag/__main__.py",
    "src/typed_rag/nodes.py",
    "src/typed_rag/llm.py",
    "src/typed_rag/rag_run.py",
    "src/typed_rag/retrieval.py",
    "src/typed_rag/fault_cases.py",
    "src/typed_rag/pilot.py",
    "src/typed_rag/config.py",
    "config/experiment.json",
)

MATCHED_RULE = (
    "a question is included only when all four conditions are approved and the reviewer's "
    "observed_state equals the state intended by the condition (CLEAN->OK, PARTIAL->PARTIAL, "
    "EMPTY->EMPTY, INCONSISTENT->INCONSISTENT); nothing is relabelled"
)
ORDER_RULE = (
    "runs are listed in canonical order (question_index, condition, branch, repeat) and shuffled "
    "once with random.Random(f'{seed}:{plan_id}'); the seed fixes the execution order only and "
    "says nothing about API responses"
)
SCOPE_NOTE = (
    "the original pilot has 30 questions; 18 have both supporting documents in the original top-5; "
    "the current semantic review yields the matched sets listed here; findings from these sets concern "
    "this selected subset, not all 30 questions or HotpotQA in general; this is a technical pilot, "
    "not a confirmatory study"
)


class PilotError(Exception):
    """Plan cannot be built, loaded or executed."""


class StalePlanError(PilotError):
    """A frozen plan no longer matches the current inputs; execution is refused."""


class OutputPathError(PilotError):
    """Output paths of the selected runs cannot be written on this host; nothing was sent."""


class BatchExecutionError(PilotError):
    """An unexpected error escaped the run loop; the original exception is kept as the cause.

    `finalization_error` is set when the invocation record could not be written
    afterwards; the original failure is reported either way, never masked.
    """

    def __init__(self, message: str, original: BaseException, finalization_error: BaseException | None = None):
        super().__init__(message)
        self.original = original
        self.finalization_error = finalization_error


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- hashing helpers ------------------------------------------------------------------


def case_content_hash(context: dict) -> str:
    """SHA-256 of the canonical JSON of the exact question and ordered documents."""
    payload = {
        "question": context["question"],
        "documents": [
            {"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in context["documents"]
        ],
    }
    return nodes.sha256_json(payload)


def question_hash(question: str) -> str:
    return nodes.sha256_text(question)


def _implementation_hashes(config: ExperimentConfig) -> dict:
    hashes = {}
    for relpath in IMPLEMENTATION_FILES:
        path = config.project_root / relpath
        hashes[relpath] = sha256_file(path) if path.is_file() else None
    return hashes


def _git_state(config: ExperimentConfig) -> dict:
    """Git revision plus an explicit record of uncommitted changes; never fails the plan."""

    def run(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args], cwd=config.project_root, capture_output=True, text=True, timeout=20, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    head = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    changed = [line for line in (status or "").splitlines() if line.strip()]
    return {
        "head": head,
        "uncommitted_change_count": len(changed) if status is not None else None,
        "uncommitted_paths": [line[3:] for line in changed],
        "note": (
            "no commit exists; the implementation identity is the file hash list"
            if head is None
            else "file hashes are authoritative; HEAD alone does not cover uncommitted changes"
        ),
    }


def prompt_and_schema_hashes(config: ExperimentConfig) -> dict:
    return {
        node: {
            "prompt_file": nodes.NODE_SPECS[node].prompt_filename,
            "prompt_sha256": nodes.sha256_text(nodes.load_prompt(config, node)),
            "schema_name": nodes.NODE_SPECS[node].schema_name,
            "schema_sha256": nodes.sha256_json(nodes.json_schema(node)),
        }
        for node in (nodes.NODE_GRADE_BINARY_ACTION, nodes.NODE_GRADE_TYPED_ACTION, nodes.NODE_REWRITE, nodes.NODE_ANSWER)
    }


def index_identity(config: ExperimentConfig) -> dict:
    manifest_path = config.index_dir / retrieval.INDEX_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise PilotError(f"Index manifest not found: {manifest_path}")
    manifest = hotpotqa.read_json(manifest_path)
    return {
        "index_sha256": manifest["index_sha256"],
        "corpus_sha256": manifest["corpus_sha256"],
        "model_name": manifest["model_name"],
        "model_revision": manifest["model_revision"],
        "document_count": manifest.get("document_count"),
        "file_sha256": manifest.get("file_sha256"),
        "top_k": config.retrieval.top_k,
    }


# --- call bound derived from the control flow ---------------------------------------------


def max_llm_calls_per_run(max_search_retries: int) -> dict:
    """Upper bound of LLM calls in one pipeline run, from the controller's control flow.

    Every iteration starts with one grader call. A retry (only possible while
    retries_used < max_search_retries) adds one rewrite call and one more
    iteration. The run ends with at most one generator call. Hence
    graders = max_search_retries + 1, rewrites = max_search_retries, generator = 1.
    """
    graders = max_search_retries + 1
    rewrites = max_search_retries
    trajectory = []
    for i in range(max_search_retries):
        trajectory += [f"grade[{i + 1}]", f"rewrite[{i + 1}]"]
    trajectory += [f"grade[{max_search_retries + 1}]", "answer"]
    return {
        "max_search_retries": max_search_retries,
        "grader_calls": graders,
        "rewrite_calls": rewrites,
        "generator_calls": 1,
        "max_llm_calls_per_run": graders + rewrites + 1,
        "longest_trajectory": " -> ".join(trajectory),
        "derivation": max_llm_calls_per_run.__doc__.strip().splitlines()[0],
        "note": "an upper bound, not an expected call count; abstain and escalate end a run without a generator call",
    }


# --- subset selection -------------------------------------------------------------------------


def _validate_review_rows(config: ExperimentConfig) -> tuple[dict, dict, dict, list[str]]:
    """The stage 6 validation plus the stricter stage 7 requirements."""
    base = fault_cases.validate_reviews(config)
    problems = list(base["problems"])
    annotations = {a["case_id"]: a for a in fault_cases.load_fault_annotations(config)}
    contexts = {c["case_id"]: c for c in fault_cases.load_fault_contexts(config)}
    reviews_rows = fault_cases.load_fault_reviews(config)
    reviews: dict[str, dict] = {}
    for number, review in enumerate(reviews_rows, start=1):
        case_id = review.get("case_id")
        if case_id in reviews:
            continue  # already reported by the base validation as a duplicate
        if case_id not in annotations or case_id not in contexts:
            if case_id in annotations and case_id not in contexts:
                problems.append(f"line {number}: case {case_id} has an annotation but no context")
            continue
        reviews[case_id] = review
        status = review.get("review_status")
        if status in (fault_cases.REVIEW_APPROVED, fault_cases.REVIEW_REJECTED):
            if not (review.get("reviewer") or "").strip():
                problems.append(f"line {number}: {status} review of {case_id} has no reviewer")
            if not (review.get("note") or "").strip():
                problems.append(f"line {number}: {status} review of {case_id} has an empty justification")
        if status == fault_cases.REVIEW_APPROVED and review.get("observed_state") != annotations[case_id]["expected_state"]:
            problems.append(
                f"line {number}: approved review of {case_id} has observed_state={review.get('observed_state')!r} "
                f"but the intended state is {annotations[case_id]['expected_state']!r}; approved must mean the "
                "candidate implements its condition"
            )
    if len(contexts) != len(annotations):
        problems.append(f"{len(contexts)} contexts but {len(annotations)} annotations")
    for case_id, annotation in annotations.items():
        if annotation["build_status"] == fault_cases.BUILD_OK and case_id not in reviews:
            problems.append(f"built case {case_id} has no review row")
    return annotations, contexts, reviews, sorted(set(problems), key=problems.index)


def select_matched_questions(config: ExperimentConfig) -> dict:
    """Derive the matched subset from the files. Never modifies a review."""
    annotations, contexts, reviews, problems = _validate_review_rows(config)
    fault_manifest = fault_cases.load_fault_manifest(config)
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    position_of = {q["question_id"]: i for i, q in enumerate(questions)}

    counts = {s: 0 for s in fault_cases.REVIEW_STATUSES}
    for review in reviews.values():
        if review.get("review_status") in counts:
            counts[review["review_status"]] += 1

    by_question: dict[str, dict] = {}
    for annotation in annotations.values():
        by_question.setdefault(annotation["question_id"], {})[annotation["condition"]] = annotation

    included: list[dict] = []
    excluded: list[dict] = []
    for entry in fault_manifest["eligibility"]:
        qid = entry["question_id"]
        if not entry["eligible"]:
            excluded.append(
                {
                    "question_index": entry["question_index"],
                    "question_id": qid,
                    "stage": "eligibility",
                    "reason": entry["reason"],
                    "cases": {},
                }
            )
            continue
        cases = by_question.get(qid, {})
        case_report = {}
        reasons = []
        for condition in fault_cases.CONDITIONS:
            annotation = cases.get(condition)
            if annotation is None or annotation["build_status"] != fault_cases.BUILD_OK:
                case_report[condition] = {"case_id": None, "review_status": None, "observed_state": None}
                reasons.append(f"{condition}: not built")
                continue
            review = reviews.get(annotation["case_id"], {})
            status = review.get("review_status")
            observed = review.get("observed_state")
            case_report[condition] = {
                "case_id": annotation["case_id"],
                "intended_state": annotation["expected_state"],
                "review_status": status,
                "observed_state": observed,
            }
            if status != fault_cases.REVIEW_APPROVED:
                reasons.append(f"{condition} {status or 'unreviewed'} (observed_state={observed})")
            elif observed != annotation["expected_state"]:
                reasons.append(f"{condition} approved with observed_state={observed} != {annotation['expected_state']}")
        if reasons:
            excluded.append(
                {
                    "question_index": position_of[qid],
                    "question_id": qid,
                    "stage": "semantic_review",
                    "reason": "; ".join(reasons),
                    "cases": case_report,
                }
            )
        else:
            included.append(
                {
                    "question_index": position_of[qid],
                    "question_id": qid,
                    "question": contexts[cases["CLEAN"]["case_id"]]["question"],
                    "question_sha256": question_hash(contexts[cases["CLEAN"]["case_id"]]["question"]),
                    "cases": {
                        condition: {
                            "case_id": cases[condition]["case_id"],
                            "intended_state": cases[condition]["expected_state"],
                            "observed_state": reviews[cases[condition]["case_id"]]["observed_state"],
                            "doc_ids": [d["doc_id"] for d in contexts[cases[condition]["case_id"]]["documents"]],
                            "context_sha256": case_content_hash(contexts[cases[condition]["case_id"]]),
                        }
                        for condition in fault_cases.CONDITIONS
                    },
                }
            )
    included.sort(key=lambda q: q["question_index"])
    excluded.sort(key=lambda q: q["question_index"])
    return {
        "valid": not problems,
        "problems": problems,
        "review_counts": counts,
        "reviewed_cases": len(reviews),
        "built_cases": sum(1 for a in annotations.values() if a["build_status"] == fault_cases.BUILD_OK),
        "eligible_questions": sum(1 for e in fault_manifest["eligibility"] if e["eligible"]),
        "pilot_questions": len(questions),
        "included": included,
        "excluded": excluded,
        "rule": MATCHED_RULE,
    }


# --- plan construction ------------------------------------------------------------------


def _run_id(plan_id: str, run: dict) -> str:
    coordinates = f"{plan_id}|{run['question_id']}|{run['case_id']}|{run['branch']}|{run['repeat']}"
    digest = hashlib.sha256(coordinates.encode("utf-8")).hexdigest()[:12]
    return f"{run['branch']}_q{run['question_index']:02d}_{run['case_id']}_r{run['repeat']}_{digest}"


def _binding(config: ExperimentConfig, selection: dict) -> dict:
    """Everything the plan identity depends on and everything verified before execution."""
    fault_dir = fault_cases.fault_cases_dir(config)
    return {
        "plan_format_version": PLAN_FORMAT_VERSION,
        "mode": MODE,
        "design": {
            "branches": list(config.pilot.branches),
            "conditions": list(fault_cases.CONDITIONS),
            "repeats": config.pilot.repeats,
            "scheduling_seed": config.seed,
            "order_rule": ORDER_RULE,
        },
        "questions": selection["included"],
        "sources": {
            "reviews_sha256": sha256_file(fault_dir / fault_cases.REVIEWS_FILENAME),
            "annotations_sha256": sha256_file(fault_dir / fault_cases.ANNOTATIONS_FILENAME),
            "contexts_sha256": sha256_file(fault_dir / fault_cases.CONTEXTS_FILENAME),
            "fault_manifest_sha256": sha256_file(fault_dir / fault_cases.MANIFEST_FILENAME),
            "pilot_questions_sha256": sha256_file(config.processed_dir / hotpotqa.QUESTIONS_FILENAME),
        },
        "index": index_identity(config),
        "prompts": prompt_and_schema_hashes(config),
        "controller": {
            "policy_version": config.controller.policy_version,
            "max_search_retries": config.controller.max_search_retries,
        },
        "llm": {
            "provider": config.llm.provider,
            "api": config.llm.api,
            "model": config.llm.model,
            "generation_parameters": rag_run.generation_parameters(config),
            "structured_outputs": "json_schema, strict=true",
        },
        "implementation_files": _implementation_hashes(config),
    }


def build_plan(config: ExperimentConfig) -> tuple[dict, list[dict]]:
    """Derive the matched subset and freeze the plan. Reads files only; no API."""
    selection = select_matched_questions(config)
    if not selection["valid"]:
        raise PilotError("reviews.jsonl is inconsistent:\n  " + "\n  ".join(selection["problems"]))
    if not selection["included"]:
        raise PilotError("no question has all four cases approved with matching observed_state; nothing to plan")

    for branch in config.pilot.branches:
        controller.get_branch(branch)

    binding = _binding(config, selection)
    plan_id = nodes.sha256_json(binding)
    bound = max_llm_calls_per_run(config.controller.max_search_retries)

    canonical: list[dict] = []
    for question in selection["included"]:
        for condition in fault_cases.CONDITIONS:
            case = question["cases"][condition]
            for branch in config.pilot.branches:
                for repeat in range(1, config.pilot.repeats + 1):
                    run = {
                        "question_index": question["question_index"],
                        "question_id": question["question_id"],
                        "case_id": case["case_id"],
                        "condition": condition,
                        "branch": branch,
                        "repeat": repeat,
                        "context_sha256": case["context_sha256"],
                    }
                    run["run_id"] = _run_id(plan_id, run)
                    canonical.append(run)
    order = list(range(len(canonical)))
    random.Random(f"{config.seed}:{plan_id}").shuffle(order)
    runs = [dict(canonical[i], schedule_position=position) for position, i in enumerate(order)]
    if len({r["run_id"] for r in runs}) != len(runs):
        raise PilotError("run identifiers are not unique")  # pragma: no cover - defensive

    n_runs = len(runs)
    manifest = {
        "plan_id": plan_id,
        "stage": 7,
        "created_at_utc": utc_now(),
        "binding": binding,
        "counts": {
            "pilot_questions": selection["pilot_questions"],
            "eligible_questions": selection["eligible_questions"],
            "matched_questions": len(selection["included"]),
            "excluded_questions": len(selection["excluded"]),
            "review_counts": selection["review_counts"],
            "pipeline_runs": n_runs,
            "pipeline_runs_formula": (
                f"{len(selection['included'])} questions x {len(fault_cases.CONDITIONS)} conditions x "
                f"{len(config.pilot.branches)} branches x {config.pilot.repeats} repeats"
            ),
            "api_call_upper_bound": n_runs * bound["max_llm_calls_per_run"],
            "api_call_upper_bound_note": (
                "pipeline runs x maximum LLM calls per run; an upper bound derived from the control flow, "
                "not an expected call count and not a monetary estimate"
            ),
        },
        "call_bound": bound,
        "excluded_questions": selection["excluded"],
        "selection_rule": MATCHED_RULE,
        "scope_note": SCOPE_NOTE,
        "implementation_git": _git_state(config),
        "case_id_note": (
            "case_id = sha256('fault-case|<format>|<question_id>|<condition>|<seed>')[:16]; it does not depend "
            "on the context content or document order, so every case is additionally bound by context_sha256 "
            "over the exact question and ordered documents, and that hash is verified whenever the plan is loaded"
        ),
        "binding_note": (
            "binding performed at stage 7 plan time against the files present then; this manifest records that "
            "binding and is not evidence that any earlier review content hash was verified"
        ),
        "note": "planning made no API call",
    }
    return manifest, runs


def plan_paths(config: ExperimentConfig) -> tuple[Path, Path]:
    return config.pilot_plan_dir / MANIFEST_FILENAME, config.pilot_plan_dir / RUNS_FILENAME


def write_plan(config: ExperimentConfig, manifest: dict, runs: list[dict], replace: bool = False) -> dict:
    """Persist the plan. An existing different plan is never overwritten silently."""
    manifest_path, runs_path = plan_paths(config)
    outcome = "written"
    if manifest_path.is_file():
        existing = hotpotqa.read_json(manifest_path)
        if existing.get("plan_id") == manifest["plan_id"]:
            outcome = "unchanged"
            return {"outcome": outcome, "plan_id": manifest["plan_id"], "manifest_path": manifest_path, "runs_path": runs_path}
        if not replace:
            changed = _compare_bindings(existing.get("binding", {}), manifest["binding"])
            raise PilotError(
                f"a different plan {existing.get('plan_id', '?')[:16]} already exists at {manifest_path}; "
                "changed components: " + (", ".join(changed) or "unknown") + ". Pass --replace-plan to freeze a new plan explicitly"
            )
        outcome = "replaced"
    rag_run._write_json(manifest_path, manifest)
    with runs_path.open("w", encoding="utf-8", newline="\n") as handle:
        for run in runs:
            handle.write(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n")
    return {"outcome": outcome, "plan_id": manifest["plan_id"], "manifest_path": manifest_path, "runs_path": runs_path}


def load_plan(config: ExperimentConfig) -> tuple[dict, list[dict]]:
    manifest_path, runs_path = plan_paths(config)
    if not manifest_path.is_file() or not runs_path.is_file():
        raise PilotError(f"No frozen plan at {config.pilot_plan_dir}. Run: python -m typed_rag --plan-pilot")
    manifest = hotpotqa.read_json(manifest_path)
    runs = hotpotqa.read_jsonl(runs_path)
    if manifest.get("plan_id") != nodes.sha256_json(manifest.get("binding")):
        raise StalePlanError("plan_id does not match the stored binding; the manifest was edited")
    if len(runs) != manifest["counts"]["pipeline_runs"] or len({r["run_id"] for r in runs}) != len(runs):
        raise StalePlanError("runs.jsonl does not match the manifest (count or duplicate run_id)")
    return manifest, sorted(runs, key=lambda r: r["schedule_position"])


def _compare_bindings(frozen: dict, current: dict) -> list[str]:
    changed: list[str] = []

    def walk(prefix: str, a: Any, b: Any) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                walk(f"{prefix}.{key}" if prefix else key, a.get(key), b.get(key))
        elif a != b:
            changed.append(prefix)

    walk("", frozen, current)
    return changed


def verify_plan(config: ExperimentConfig, manifest: dict) -> list[str]:
    """Recompute the binding from the current files and name every changed component."""
    selection = select_matched_questions(config)
    if not selection["valid"]:
        return ["reviews.jsonl: " + "; ".join(selection["problems"])]
    current = _binding(config, selection)
    changed = _compare_bindings(manifest["binding"], current)
    # Re-verify the case contents explicitly, independently of the selection logic.
    contexts = {c["case_id"]: c for c in fault_cases.load_fault_contexts(config)}
    for question in manifest["binding"]["questions"]:
        for condition, case in question["cases"].items():
            context = contexts.get(case["case_id"])
            if context is None:
                changed.append(f"case {case['case_id']} ({condition}): context missing")
            elif case_content_hash(context) != case["context_sha256"]:
                changed.append(f"case {case['case_id']} ({condition}): context content or document order changed")
            elif context["question_id"] != question["question_id"]:
                changed.append(f"case {case['case_id']} ({condition}): question_id changed")
    return sorted(set(changed), key=changed.index)


def require_current_plan(config: ExperimentConfig) -> tuple[dict, list[dict]]:
    manifest, runs = load_plan(config)
    changed = verify_plan(config, manifest)
    if changed:
        raise StalePlanError(
            f"frozen plan {manifest['plan_id'][:16]} no longer matches the current inputs; "
            "changed components: " + ", ".join(changed) + ". Execution refused; the plan is not regenerated automatically"
        )
    return manifest, runs


# --- API-call budget ------------------------------------------------------------------


class BudgetedTransport:
    """Counts every attempt (successful or not) against a fixed budget, persisted before sending.

    With `max_calls == 0` the inner transport is never touched; `inner` may then be None.
    """

    def __init__(self, inner: Transport | None, max_calls: int, ledger_path: Path, attempts_before: int = 0):
        if max_calls < 0:
            raise PilotError("the API-call budget must be a non-negative integer")
        if max_calls > 0 and inner is None:
            raise PilotError("a transport is required when the budget allows calls")
        self.inner = inner
        self.max_calls = max_calls
        self.ledger_path = ledger_path
        self.attempts = 0
        self.attempts_before = attempts_before
        self.started_at = utc_now()
        self._write()

    @property
    def remaining(self) -> int:
        return self.max_calls - self.attempts

    def _write(self) -> None:
        rag_run._write_json(
            self.ledger_path,
            {
                "invocation_started_at_utc": self.started_at,
                "max_api_calls_this_invocation": self.max_calls,
                "attempts_this_invocation": self.attempts,
                "attempts_before_this_invocation": self.attempts_before,
                "attempts_total": self.attempts_before + self.attempts,
                "note": "attempts are counted before the request is sent; failed attempts count",
            },
        )

    def send(self, request: dict) -> llm.TransportResult:
        if self.attempts >= self.max_calls:
            raise llm.APIBudgetStop(
                f"API-call budget of {self.max_calls} exhausted ({self.attempts} attempts used); request not sent"
            )
        self.attempts += 1
        self._write()
        assert self.inner is not None
        return self.inner.send(request)


# --- checkpoint ---------------------------------------------------------------------------


def read_checkpoint(path: Path) -> dict:
    """Finished runs, and runs that started but never finished (interrupted)."""
    finished: dict[str, dict] = {}
    started: dict[str, dict] = {}
    if path.is_file():
        for record in hotpotqa.read_jsonl(path):
            if record["event"] == EVENT_STARTED:
                started[record["run_id"]] = record
            elif record["event"] == EVENT_FINISHED:
                finished[record["run_id"]] = record
    interrupted = {run_id: rec for run_id, rec in started.items() if run_id not in finished}
    return {"finished": finished, "interrupted": interrupted}


def batch_status_of(run: dict) -> str:
    """Batch bookkeeping label of a finished controller run."""
    status = run["status"]
    if status == controller.RUN_COMPLETED:
        return RUN_COMPLETED
    if status == controller.RUN_API_BUDGET_STOPPED:
        return RUN_API_BUDGET_STOPPED
    if status == controller.RUN_BUDGET_EXHAUSTED:
        return RUN_RETRY_BUDGET_EXHAUSTED
    return RUN_FAILED


def batch_dir_for(config: ExperimentConfig, plan_id: str, execution_kind: str) -> Path:
    base = config.pilot_mock_runs_dir if execution_kind == EXECUTION_MOCK else config.pilot_runs_dir
    return base / plan_id


def resolve_batch_dir(
    config: ExperimentConfig, plan_id: str, execution_kind: str, batch_dir: Path | str | None = None
) -> Path:
    """The directory a batch is executed in: the configured default, or an explicit one.

    The destination is operational metadata only: it never enters the plan binding
    and never relaxes plan verification. An explicit directory is accepted for
    execution, resume and summary alike; omitting it keeps the configured default
    `<results>/<pilot runs dir>/<plan_id>`. A non-empty destination that does not
    hold a batch of this plan is refused rather than written into.
    """
    if batch_dir is None:
        return batch_dir_for(config, plan_id, execution_kind)
    resolved = Path(batch_dir).expanduser().resolve()
    if resolved.exists() and not resolved.is_dir():
        raise PilotError(f"batch directory {resolved} exists and is not a directory")
    batch_path = resolved / BATCH_FILENAME
    if batch_path.is_file():
        existing = hotpotqa.read_json(batch_path)
        if existing.get("plan_id") != plan_id:
            raise PilotError(
                f"{resolved} holds a batch of plan {str(existing.get('plan_id'))[:16]}, not the frozen plan "
                f"{plan_id[:16]}; refusing to write into another plan's batch"
            )
        if existing.get("execution_kind") != execution_kind:
            raise PilotError(
                f"{resolved} holds a {existing.get('execution_kind')!r} batch, not {execution_kind!r}; "
                "real and mock executions never share a directory"
            )
    elif resolved.is_dir() and any(resolved.iterdir()):
        raise PilotError(
            f"{resolved} is not empty and holds no {BATCH_FILENAME} of this plan; refusing to write into it"
        )
    return resolved


# --- continuation scope -------------------------------------------------------------------


def scope_id(plan_id: str, run_ids: list[str]) -> str:
    """Identity of an ordered continuation scope; binds a batch to exactly these runs."""
    return nodes.sha256_json({"plan_id": plan_id, "run_ids": run_ids})


def load_scope(path: Path, plan_id: str, runs: list[dict]) -> dict:
    """Read and validate an explicit continuation scope: a subset of this plan, in order.

    The file names its plan and lists the allowed run identifiers in the order they
    are to be executed. It restricts and reorders execution of a diagnostic batch;
    it never adds a run, never relabels one and never touches the plan itself.
    """
    scope = hotpotqa.read_json(Path(path))
    if scope.get("plan_id") != plan_id:
        raise PilotError(
            f"scope file names plan {str(scope.get('plan_id'))[:16]}, not the frozen plan {plan_id[:16]}"
        )
    run_ids = scope.get("run_ids")
    if not isinstance(run_ids, list) or not run_ids:
        raise PilotError("scope file must list a non-empty 'run_ids' array")
    if len(set(run_ids)) != len(run_ids):
        raise PilotError("scope file lists a duplicate run_id")
    known = {r["run_id"]: r for r in runs}
    unknown = [run_id for run_id in run_ids if run_id not in known]
    if unknown:
        raise PilotError(f"scope file lists {len(unknown)} run_id(s) that are not in this plan: {unknown[:3]}")
    return {
        "path": str(Path(path).resolve()),
        "plan_id": plan_id,
        "run_ids": list(run_ids),
        "scope_id": scope_id(plan_id, list(run_ids)),
        "runs": [known[run_id] for run_id in run_ids],
        "label": scope.get("label"),
    }


# --- output path preflight ----------------------------------------------------------------


def output_paths_for_run(batch_dir: Path, run_id: str) -> list[Path]:
    """Every path the runner can write for one pipeline run, by the real construction rules."""
    run_dir = batch_dir / RUNS_DIRNAME / run_id
    paths = [run_dir / rag_run.RUN_FILENAME, run_dir / rag_run.CONTEXT_FILENAME, run_dir / rag_run.CALLS_FILENAME]
    nodes_used = (
        nodes.NODE_GRADE_BINARY_ACTION,
        nodes.NODE_GRADE_TYPED_ACTION,
        nodes.NODE_REWRITE,
        nodes.NODE_ANSWER,
    )
    # Call indices 1..max: the longest trajectory is grade -> rewrite -> grade -> answer.
    calls = max_llm_calls_per_run(1)["max_llm_calls_per_run"]
    for index in range(1, calls + 1):
        for node in nodes_used:
            paths.append(run_dir / rag_run.RAW_DIRNAME / f"{index:02d}_{node}" / f"{node}_response.json")
    return paths


def _probe_write(batch_dir: Path, target_length: int) -> dict:
    """Write, read back and delete one clearly synthetic file of the worst-case length.

    The probe lives in its own directory beside the runs, never inside a real run
    directory, and holds no experiment content.
    """
    probe_dir = batch_dir / PROBE_DIRNAME
    stem, suffix = "probe", "_response.json"
    needed = target_length - len(str(probe_dir)) - 1 - len(suffix)
    name = f"{stem}{'x' * max(needed - len(stem), 0)}{suffix}"
    path = probe_dir / name
    payload = {"probe": True, "synthetic": "output path probe, not a provider response and not an experiment record"}
    result = {"probe_path": str(path), "probe_path_length": len(str(path)), "target_length": target_length}
    try:
        rag_run._write_json(path, payload)
        result["write_ok"] = True
        result["read_back_ok"] = json.loads(path.read_text(encoding="utf-8")) == payload
    except OSError as exc:
        result.update({"write_ok": False, "read_back_ok": False, "error": f"{type(exc).__name__}: {exc}"})
    finally:
        try:
            if path.is_file():
                path.unlink()
            if probe_dir.is_dir() and not any(probe_dir.iterdir()):
                probe_dir.rmdir()
        except OSError as exc:
            result["cleanup_error"] = f"{type(exc).__name__}: {exc}"
        result["cleaned_up"] = not path.exists()
    return result


def check_output_paths(batch_dir: Path, run_ids: list[str], max_path: int | None = None) -> dict:
    """Are the output paths of these runs writable on this host? No provider call, no run record.

    `rag_run._write_json` and `_append_jsonl` open the final path directly, so there
    is no temporary name to account for: the longest final path is the worst case.
    """
    max_path = MAX_OUTPUT_PATH if max_path is None else max_path
    longest_path, longest_run = None, None
    too_long: list[str] = []
    for run_id in run_ids:
        for path in output_paths_for_run(batch_dir, run_id):
            text = str(path)
            if longest_path is None or len(text) > len(longest_path):
                longest_path, longest_run = text, run_id
            if len(text) >= max_path:
                too_long.append(text)
    report = {
        "batch_dir": str(batch_dir),
        "batch_dir_length": len(str(batch_dir)),
        "runs_checked": len(run_ids),
        "max_path": max_path,
        "longest_path": longest_path,
        "longest_path_length": len(longest_path) if longest_path else 0,
        "longest_path_run_id": longest_run,
        "paths_over_limit": len(too_long),
        "paths_over_limit_examples": too_long[:3],
        "temporary_filenames_used": False,
        "temporary_filenames_note": "the writers open the final path directly; no temporary name or atomic rename is involved",
    }
    report["probe"] = _probe_write(batch_dir, report["longest_path_length"])
    report["ok"] = not too_long and bool(report["probe"].get("write_ok")) and bool(report["probe"].get("read_back_ok"))
    return report


def require_writable_output_paths(batch_dir: Path, run_ids: list[str], max_path: int | None = None) -> dict:
    """Refuse to spend any API budget when the results of the selected runs cannot be stored."""
    max_path = MAX_OUTPUT_PATH if max_path is None else max_path
    report = check_output_paths(batch_dir, run_ids, max_path)
    if report["ok"]:
        return report
    probe = report["probe"]
    if report["paths_over_limit"]:
        detail = (
            f"{report['paths_over_limit']} output path(s) reach the {max_path}-character limit of this host; "
            f"the longest is {report['longest_path_length']} characters ({report['longest_path_run_id']})"
        )
    else:
        detail = f"the output path probe failed: {probe.get('error', 'write or read-back did not succeed')}"
    raise OutputPathError(
        f"{detail}. Nothing was sent and no API budget was used. Choose a shorter batch directory with "
        f"--batch-dir (current: {batch_dir}, {report['batch_dir_length']} characters), or enable long paths on "
        "this host."
    )


# --- execution ----------------------------------------------------------------------------


def run_batch(
    config: ExperimentConfig,
    max_api_calls: int | None,
    resume: bool = False,
    max_runs: int | None = None,
    transport: Transport | None = None,
    index: Any | None = None,
    model: Any | None = None,
    execution_kind: str = EXECUTION_REAL,
    batch_dir: Path | str | None = None,
    scope: dict | None = None,
    plan: tuple[dict, list[dict]] | None = None,
    contexts: dict | None = None,
    questions: dict | None = None,
    mode: str | None = None,
) -> dict:
    """Execute the frozen plan sequentially with a mandatory API-call budget.

    Each planned run is one fresh `controller.run_controlled` call on the
    prepared initial context of its case: fresh controller state, fresh retry
    budget, no shared LLM responses. A checkpoint row is written before and
    after every run; on resume, finished, failed and interrupted runs are
    skipped and reported, never repeated automatically.

    `batch_dir` moves the output of the batch to an explicit directory; it is
    operational metadata and changes no scientific input. `scope` restricts and
    orders execution within the plan (see `load_scope`); a batch started with a
    scope stays bound to it, so a resume can neither broaden nor reorder it.

    `plan`, `contexts`, `questions` and `mode` (stage 14) let another study drive
    the same loop with its own frozen plan, its own approved contexts and its own
    question file. Omitting them keeps the stage 7 pilot behaviour: the frozen
    pilot plan, the pilot fault contexts, the pilot questions by position and the
    pilot mode. The caller is responsible for having verified the plan it passes.
    """
    if execution_kind not in (EXECUTION_REAL, EXECUTION_MOCK):
        raise PilotError(f"unknown execution kind {execution_kind!r}")
    if max_api_calls is None:
        raise PilotError("real execution requires an explicit API-call budget (--max-api-calls N)")
    mode = MODE if mode is None else mode
    manifest, runs = require_current_plan(config) if plan is None else plan
    plan_id = manifest["plan_id"]
    if scope is not None and scope.get("plan_id") != plan_id:
        raise PilotError("the supplied scope belongs to another plan")
    if contexts is None:
        contexts = {c["case_id"]: c for c in fault_cases.load_fault_contexts(config)}

    batch_dir = resolve_batch_dir(config, plan_id, execution_kind, batch_dir)
    checkpoint_path = batch_dir / CHECKPOINT_FILENAME
    checkpoint = read_checkpoint(checkpoint_path)
    if (checkpoint["finished"] or checkpoint["interrupted"]) and not resume:
        raise PilotError(
            f"batch {batch_dir} already has {len(checkpoint['finished'])} finished and "
            f"{len(checkpoint['interrupted'])} interrupted runs; pass --resume to continue the same frozen plan"
        )
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_path = batch_dir / BATCH_FILENAME
    batch = hotpotqa.read_json(batch_path) if batch_path.is_file() else {
        "plan_id": plan_id,
        "execution_kind": execution_kind,
        "mode": mode,
        "created_at_utc": utc_now(),
        "invocations": [],
        "note": (
            "real execution through the OpenAI Responses API"
            if execution_kind == EXECUTION_REAL
            else "MOCK execution with a fake transport; never a real result"
        ),
    }
    if batch.get("plan_id") != plan_id or batch.get("execution_kind") != execution_kind:
        raise PilotError(f"{batch_path} belongs to another plan or execution kind")

    # A scoped batch stays bound to its scope: a later invocation cannot silently
    # broaden it to the whole plan, drop it, or reorder its runs.
    frozen_scope = batch.get("scope")
    if frozen_scope is None and scope is not None and (checkpoint["finished"] or checkpoint["interrupted"]):
        raise PilotError(f"batch {batch_dir} was started without a scope; it cannot be narrowed to one now")
    if frozen_scope is not None:
        if scope is None:
            raise PilotError(
                f"batch {batch_dir} is bound to scope {frozen_scope['scope_id'][:16]}; resume it with the same "
                "scope file"
            )
        if scope["scope_id"] != frozen_scope["scope_id"]:
            raise PilotError(
                f"the supplied scope {scope['scope_id'][:16]} does not match the scope "
                f"{frozen_scope['scope_id'][:16]} this batch was started with; a resume may not broaden or "
                "reorder the scope"
            )
    if scope is not None:
        batch["scope"] = {
            "scope_id": scope["scope_id"],
            "run_ids": scope["run_ids"],
            "source_file": scope["path"],
            "label": scope.get("label"),
            "note": "an operational restriction of this diagnostic batch; the frozen plan is unchanged",
        }

    budget_path = batch_dir / BUDGET_FILENAME
    attempts_before = hotpotqa.read_json(budget_path).get("attempts_total", 0) if budget_path.is_file() else 0
    invocation = {
        "started_at_utc": utc_now(),
        "batch_dir": str(batch_dir),
        "scope_id": scope["scope_id"] if scope else None,
        "max_api_calls": max_api_calls,
        "max_runs": max_runs,
        "resume": resume,
        "skipped_finished": len(checkpoint["finished"]),
        "skipped_interrupted": len(checkpoint["interrupted"]),
        "executed": [],
        "stopped_reason": None,
    }
    batch["invocations"].append(invocation)
    rag_run._write_json(batch_path, batch)

    # Checkpoint skipping and --max-runs apply inside the scope only; runs outside it
    # are never pulled in to fill the invocation.
    candidates = scope["runs"] if scope else runs
    pending = [r for r in candidates if r["run_id"] not in checkpoint["finished"] and r["run_id"] not in checkpoint["interrupted"]]
    if max_runs is not None:
        pending = pending[: max(max_runs, 0)]

    executed: list[dict] = []
    stopped_reason = None
    execution_error: BaseException | None = None
    if pending:
        # Refuse before the first request if the results of these runs cannot be stored.
        invocation["output_path_check"] = require_writable_output_paths(batch_dir, [r["run_id"] for r in pending])
        rag_run._write_json(batch_path, batch)
        inner = transport
        if inner is None and max_api_calls > 0 and execution_kind == EXECUTION_REAL:
            inner = rag_run.default_transport(config)
        budgeted = BudgetedTransport(inner, max_api_calls, budget_path, attempts_before)
        if index is None:
            index = retrieval.load_index(config)
        if model is None:
            model = retrieval.load_model(config)
        try:
            for planned in pending:
                if budgeted.remaining <= 0:
                    stopped_reason = f"API-call budget {max_api_calls} exhausted before run {planned['run_id']}"
                    break
                context = contexts[planned["case_id"]]
                if case_content_hash(context) != planned["context_sha256"]:
                    raise StalePlanError(f"context of case {planned['case_id']} changed since the plan was frozen")
                run_dir = batch_dir / RUNS_DIRNAME / planned["run_id"]
                rag_run._append_jsonl(checkpoint_path, {"event": EVENT_STARTED, "run_id": planned["run_id"], "at_utc": utc_now()})
                attempts_at_start = budgeted.attempts
                result = controller.run_controlled(
                    config,
                    planned["question_index"],
                    planned["branch"],
                    transport=budgeted,
                    index=index,
                    model=model,
                    initial_context=context,
                    run_id=planned["run_id"],
                    run_dir=run_dir,
                    mode=mode,
                    question=questions[planned["question_id"]] if questions else None,
                )
                result["pilot"] = {
                    "plan_id": plan_id,
                    "execution_kind": execution_kind,
                    "repeat": planned["repeat"],
                    "schedule_position": planned["schedule_position"],
                    "api_attempts": budgeted.attempts - attempts_at_start,
                    "note": "condition and reviewed state are research metadata; see the plan manifest and reviews.jsonl",
                }
                rag_run._write_json(run_dir / controller.RUN_FILENAME, result)
                record = {
                    "event": EVENT_FINISHED,
                    "run_id": planned["run_id"],
                    "at_utc": utc_now(),
                    "batch_status": batch_status_of(result),
                    "status": result["status"],
                    "final_outcome": result["final_outcome"],
                    "api_calls": result["api_calls"],
                    "api_attempts": budgeted.attempts - attempts_at_start,
                }
                rag_run._append_jsonl(checkpoint_path, record)
                executed.append(record)
                invocation["executed"] = [r["run_id"] for r in executed]
                rag_run._write_json(batch_path, batch)
        except Exception as exc:  # noqa: BLE001 - any failure ends the invocation; nothing is retried
            execution_error = exc
            stopped_reason = f"execution error: {type(exc).__name__}: {exc}"
        invocation["api_attempts_this_invocation"] = budgeted.attempts
    else:
        stopped_reason = "nothing pending"

    invocation["stopped_reason"] = stopped_reason
    invocation["finished_at_utc"] = utc_now()
    if execution_error is not None:
        invocation["execution_error"] = {
            "type": type(execution_error).__name__,
            "message": str(execution_error),
            "note": (
                "the invocation stopped here; a run that had started without finishing stays interrupted and is "
                "never reported as an abstention. Missing response content, token usage and timing stay missing"
            ),
        }
    # Best effort: storage may be exactly what failed, so a write here can fail too.
    finalization_error: BaseException | None = None
    try:
        rag_run._write_json(batch_path, batch)
    except OSError as exc:
        finalization_error = exc
        if execution_error is None:
            raise
    if execution_error is not None:
        message = f"batch execution stopped: {type(execution_error).__name__}: {execution_error}"
        if finalization_error is not None:
            message += (
                f"; in addition the invocation record could not be written: "
                f"{type(finalization_error).__name__}: {finalization_error}"
            )
        else:
            message += f"; the invocation record was finalized in {batch_path}"
        raise BatchExecutionError(message, execution_error, finalization_error) from execution_error
    checkpoint = read_checkpoint(checkpoint_path)
    in_scope = {r["run_id"] for r in candidates}
    return {
        "plan_id": plan_id,
        "execution_kind": execution_kind,
        "batch_dir": batch_dir,
        "scope_id": scope["scope_id"] if scope else None,
        "scoped_runs": len(candidates) if scope else None,
        "planned": len(runs),
        "executed_now": len(executed),
        "executed_status_counts": _count(r["batch_status"] for r in executed),
        "finished_total": len(checkpoint["finished"]),
        "interrupted_total": len(checkpoint["interrupted"]),
        "remaining": len(in_scope - set(checkpoint["finished"]) - set(checkpoint["interrupted"])),
        "api_attempts_this_invocation": invocation.get("api_attempts_this_invocation", 0),
        "stopped_reason": stopped_reason,
    }


def _count(values) -> dict:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


# --- dry run ------------------------------------------------------------------------------


def _gold_answers(config: ExperimentConfig) -> dict[str, str]:
    """Research metadata for the isolation check only; the execution path never calls this."""
    return {a["question_id"]: a["answer"] for a in hotpotqa.load_pilot_annotations(config.processed_dir)}


def check_request_isolation(
    config: ExperimentConfig, request: dict, context: dict, annotation: dict, review: dict, gold_answer: str | None
) -> list[str]:
    """Verify that a first evaluator request carries only the question and the documents."""
    problems: list[str] = []
    user_text = request["input"][0]["content"][0]["text"]
    expected = nodes.format_grader_input(
        context["question"],
        [{"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in context["documents"]],
        0,
        config.controller.max_search_retries,
    )
    if user_text != expected:
        problems.append("user input differs from question + ordered documents + retry budget")
    # Strip the legitimate content in an order that cannot damage later matches:
    # the question, then every text, then every title, then every doc_id.
    residual = user_text.replace(context["question"], "")
    for field in ("text", "title", "doc_id"):
        for document in context["documents"]:
            residual = residual.replace(document[field], "")
    markers = {
        "case_id": context["case_id"],
        "condition label": annotation["condition"],
        "expected_state field": "expected_state",
        "observed_state field": "observed_state",
        "review_status field": "review_status",
    }
    note = (review.get("note") or "").strip()
    if note:
        markers["review note"] = note
    if gold_answer:
        markers["gold answer"] = gold_answer
    serialized = json.dumps(request, ensure_ascii=False)
    for label, marker in markers.items():
        if label == "gold answer":
            # The answer string may occur naturally inside dataset text; only the
            # residual (everything except question and documents) and the
            # instruction prompt are checked.
            if marker in residual or marker in request["instructions"]:
                problems.append(f"{label} appears outside the document texts")
        elif label == "condition label":
            # State names (PARTIAL, EMPTY, INCONSISTENT) legitimately appear in the
            # typed grader instructions as the answer vocabulary; the condition of
            # this case must not appear in the user input outside the documents.
            if marker in residual or (marker not in nodes.STATES and marker in request["instructions"]):
                problems.append(f"{label} appears outside the document texts")
        elif marker in serialized:
            problems.append(f"{label} appears in the request")
    if "case_id" in serialized:
        problems.append("the key name case_id appears in the request")
    return problems


def dry_run_batch(config: ExperimentConfig) -> dict:
    """Validate the frozen plan and prepare first requests; no client, no key, no network."""
    manifest, runs = require_current_plan(config)
    plan_id = manifest["plan_id"]
    contexts = {c["case_id"]: c for c in fault_cases.load_fault_contexts(config)}
    annotations = {a["case_id"]: a for a in fault_cases.load_fault_annotations(config)}
    reviews = {r["case_id"]: r for r in fault_cases.load_fault_reviews(config)}
    gold = _gold_answers(config)

    checks = {
        "plan_verified_against_current_files": True,
        "index_manifest_matches_plan": True,
        "runs_unique": len({r["run_id"] for r in runs}) == len(runs),
        "identical_initial_context_per_case": True,
        "identical_first_input_across_branches_and_repeats": True,
        "isolation_problems": [],
    }
    inputs_by_case: dict[str, set[str]] = {}
    representative: dict[str, dict] = {}
    for run in runs:
        context = contexts[run["case_id"]]
        if case_content_hash(context) != run["context_sha256"]:
            checks["identical_initial_context_per_case"] = False
        branch = controller.get_branch(run["branch"])
        request = controller.first_grader_request(config, branch, context["question"], context["documents"])
        inputs_by_case.setdefault(run["case_id"], set()).add(request["input"][0]["content"][0]["text"])
        problems = check_request_isolation(
            config, request, context, annotations[run["case_id"]], reviews.get(run["case_id"], {}), gold.get(run["question_id"])
        )
        for problem in problems:
            checks["isolation_problems"].append({"run_id": run["run_id"], "problem": problem})
        if run["branch"] not in representative:
            representative[run["branch"]] = {
                "run_id": run["run_id"],
                "schedule_position": run["schedule_position"],
                "question_index": run["question_index"],
                "case_id": run["case_id"],
                "grader_node": branch.grader_node,
                "first_grader_request": request,
                "hashes": nodes.request_hashes(request),
            }
    checks["identical_first_input_across_branches_and_repeats"] = all(len(v) == 1 for v in inputs_by_case.values())
    checks["all_passed"] = (
        checks["runs_unique"]
        and checks["identical_initial_context_per_case"]
        and checks["identical_first_input_across_branches_and_repeats"]
        and not checks["isolation_problems"]
    )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = config.pilot_dry_runs_dir / f"dry_{stamp}_{plan_id[:12]}"
    out_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "plan_id": plan_id,
        "dry_run": True,
        "created_at_utc": utc_now(),
        "pipeline_runs": len(runs),
        "matched_questions": manifest["counts"]["matched_questions"],
        "api_call_upper_bound": manifest["counts"]["api_call_upper_bound"],
        "call_bound": manifest["call_bound"],
        "api_calls": 0,
        "api_key_required": False,
        "checks": checks,
        "representative_runs": {b: {k: v for k, v in r.items() if k != "first_grader_request"} for b, r in representative.items()},
        "first_scheduled_runs": [r["run_id"] for r in runs[:8]],
        "out_dir": str(out_dir),
        "note": (
            "only the first evaluator request of a run can be prepared; later evaluator outputs, rewritten "
            "queries, answers, token usage and latency depend on the LLM and are not invented here"
        ),
    }
    rag_run._write_json(out_dir / DRY_RUN_FILENAME, report)
    rag_run._write_json(out_dir / REPRESENTATIVE_FILENAME, {"plan_id": plan_id, "requests": representative})
    report["representative_requests"] = representative
    return report


def check_scope(
    config: ExperimentConfig,
    scope_path: Path,
    batch_dir: Path | str | None = None,
    execution_kind: str = EXECUTION_REAL,
) -> dict:
    """Offline check of a continuation scope and its output paths; no client, no network."""
    manifest, runs = require_current_plan(config)
    plan_id = manifest["plan_id"]
    scope = load_scope(Path(scope_path), plan_id, runs)
    resolved = resolve_batch_dir(config, plan_id, execution_kind, batch_dir)
    checkpoint = read_checkpoint(resolved / CHECKPOINT_FILENAME)
    pending = [r for r in scope["runs"] if r["run_id"] not in checkpoint["finished"] and r["run_id"] not in checkpoint["interrupted"]]
    batch_path = resolved / BATCH_FILENAME
    batch = hotpotqa.read_json(batch_path) if batch_path.is_file() else None
    frozen_scope = batch.get("scope") if batch else None
    paths = check_output_paths(resolved, [r["run_id"] for r in scope["runs"]])
    return {
        "plan_id": plan_id,
        "scope_file": scope["path"],
        "scope_id": scope["scope_id"],
        "label": scope.get("label"),
        "batch_dir": str(resolved),
        "batch_present": batch is not None,
        "batch_scope_id": frozen_scope["scope_id"] if frozen_scope else None,
        "batch_scope_matches": (frozen_scope["scope_id"] == scope["scope_id"]) if frozen_scope else None,
        "scope_runs": len(scope["runs"]),
        "already_finished": [r["run_id"] for r in scope["runs"] if r["run_id"] in checkpoint["finished"]],
        "already_interrupted": [r["run_id"] for r in scope["runs"] if r["run_id"] in checkpoint["interrupted"]],
        "pending": [r["run_id"] for r in pending],
        "pending_count": len(pending),
        "output_paths": paths,
        "api_calls": 0,
        "ok": paths["ok"],
        "note": "offline check only; it prepares no request and contacts no provider",
    }


# --- summary ------------------------------------------------------------------------------


def summarise_batch(config: ExperimentConfig, batch_dir: Path | None = None) -> dict:
    """Diagnostic summary of executed (or explicitly mock) trajectories of the frozen plan."""
    manifest, runs = load_plan(config)
    plan_id = manifest["plan_id"]
    if batch_dir is None:
        batch_dir = batch_dir_for(config, plan_id, EXECUTION_REAL)
    batch_path = batch_dir / BATCH_FILENAME
    batch = hotpotqa.read_json(batch_path) if batch_path.is_file() else None
    if batch is not None and batch.get("plan_id") != plan_id:
        raise PilotError(f"{batch_dir} was executed for plan {batch.get('plan_id', '?')[:16]}, not the frozen plan {plan_id[:16]}")
    checkpoint = read_checkpoint(batch_dir / CHECKPOINT_FILENAME)
    # The reviewed state of every initial context as frozen in the plan, not the live file.
    reviewed_by_case = {
        case["case_id"]: case["observed_state"]
        for question in manifest["binding"]["questions"]
        for case in question["cases"].values()
    }
    budget_path = batch_dir / BUDGET_FILENAME
    budget = hotpotqa.read_json(budget_path) if budget_path.is_file() else None

    status_counts = {RUN_PENDING: 0, RUN_COMPLETED: 0, RUN_FAILED: 0, RUN_INTERRUPTED: 0, RUN_API_BUDGET_STOPPED: 0, RUN_RETRY_BUDGET_EXHAUSTED: 0}
    outcomes: dict[str, dict[str, dict[str, int]]] = {}
    confusion: dict[str, dict[str, dict[str, int]]] = {"typed": {}, "binary": {}}
    policy = {"steps_total": 0, "steps_mismatch": 0, "steps_override": 0, "runs_any_mismatch": 0, "runs_any_override": 0, "by_branch": {}}
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0, "calls_with_usage": 0}
    api_calls_logged = 0
    timings = {"runs_with_timing": 0, "total_seconds_sum": 0.0, "grader_seconds_sum": 0.0, "rewrite_seconds_sum": 0.0, "generator_seconds_sum": 0.0}
    post_retry = {"runs_with_retry_search": 0, "note": "the semantic label of a context retrieved after a retry is UNREVIEWED; the reviewed state applies to the initial context only"}
    failures: list[dict] = []

    for run in runs:
        run_id = run["run_id"]
        condition = run["condition"]
        branch = run["branch"]
        if run_id in checkpoint["interrupted"]:
            status_counts[RUN_INTERRUPTED] += 1
            failures.append({"run_id": run_id, "batch_status": RUN_INTERRUPTED, "detail": "started but not finished; not repeated automatically"})
            continue
        if run_id not in checkpoint["finished"]:
            status_counts[RUN_PENDING] += 1
            continue
        record = checkpoint["finished"][run_id]
        status_counts[record["batch_status"]] += 1
        run_path = batch_dir / RUNS_DIRNAME / run_id / controller.RUN_FILENAME
        if not run_path.is_file():
            failures.append({"run_id": run_id, "batch_status": record["batch_status"], "detail": "run.json missing"})
            continue
        result = hotpotqa.read_json(run_path)
        if record["batch_status"] != RUN_COMPLETED:
            failures.append({"run_id": run_id, "batch_status": record["batch_status"], "status": result["status"], "final_outcome": result["final_outcome"], "failure": result.get("failure")})
        outcomes.setdefault(branch, {}).setdefault(condition, {})
        outcome = result["final_outcome"] or "none"
        outcomes[branch][condition][outcome] = outcomes[branch][condition].get(outcome, 0) + 1
        api_calls_logged += result["api_calls"]
        for key in ("input_tokens", "output_tokens", "total_tokens", "cached_tokens", "calls_with_usage"):
            usage[key] += result["usage_totals"].get(key, 0)
        t = result.get("timings", {})
        if t.get("total_seconds") is not None:
            timings["runs_with_timing"] += 1
            for key in ("total_seconds", "grader_seconds", "rewrite_seconds", "generator_seconds"):
                timings[f"{key}_sum"] = round(timings[f"{key}_sum"] + (t.get(key) or 0.0), 4)
        trajectory = result.get("trajectory", [])
        if len(trajectory) > 1:
            post_retry["runs_with_retry_search"] += 1
        first = trajectory[0] if trajectory else None
        reviewed = reviewed_by_case.get(run["case_id"]) or "unreviewed"
        if first and first.get("assessment"):
            grader = "typed" if "state" in first["assessment"] else "binary"
            predicted = str(first["assessment"].get("state", first["assessment"].get("sufficient")))
            table = confusion[grader].setdefault(reviewed, {})
            table[predicted] = table.get(predicted, 0) + 1
        by_branch = policy["by_branch"].setdefault(branch, {"steps": 0, "mismatch": 0, "override": 0, "runs": 0, "runs_any_mismatch": 0})
        by_branch["runs"] += 1
        for step in trajectory:
            if step.get("proposed_action") is None:
                continue
            policy["steps_total"] += 1
            by_branch["steps"] += 1
            if step.get("policy_mismatch"):
                policy["steps_mismatch"] += 1
                by_branch["mismatch"] += 1
            if step.get("policy_override"):
                policy["steps_override"] += 1
                by_branch["override"] += 1
        if result.get("any_policy_mismatch"):
            policy["runs_any_mismatch"] += 1
            by_branch["runs_any_mismatch"] += 1
        if result.get("any_policy_override"):
            policy["runs_any_override"] += 1

    summary = {
        "plan_id": plan_id,
        "batch_dir": str(batch_dir),
        "scope": batch.get("scope") if batch else None,
        "execution_kind": batch.get("execution_kind") if batch else None,
        "batch_present": batch is not None,
        "generated_at_utc": utc_now(),
        "planned": len(runs),
        "status_counts": status_counts,
        "outcomes_by_branch_and_condition": outcomes,
        "first_evaluation_confusion": {
            "note": "rows: reviewed observed_state of the INITIAL context as frozen in the plan manifest; columns: first grader verdict (typed: state; binary: sufficient)",
            **confusion,
        },
        "policy": policy,
        "api": {
            "attempts_recorded_by_budget_ledger": budget.get("attempts_total") if budget else None,
            "calls_logged_in_runs": api_calls_logged,
            "usage_totals": usage,
        },
        "timing": timings,
        "post_retry": post_retry,
        "non_completed_runs": failures,
        "interpretation_limits": [
            "no claim about final-answer grounding: matching an answer string does not show the answer is supported by its final context",
            "no claim about silent-failure conversion, recovery, statistical significance or non-inferiority",
            "the reviewed initial state is not a label for a context retrieved after a retry",
            "this is a technical pilot on a selected subset",
        ],
    }
    if batch is not None:
        rag_run._write_json(batch_dir / SUMMARY_FILENAME, summary)
    return summary


# --- formatting ---------------------------------------------------------------------------


def format_plan(manifest: dict, runs: list[dict], written: dict | None = None) -> str:
    counts = manifest["counts"]
    lines = [
        f"plan id       : {manifest['plan_id']}",
        f"plan dir      : {written['manifest_path'].parent if written else ''} ({written['outcome'] if written else 'loaded'})",
        f"mode          : {manifest['binding']['mode']}",
        f"questions     : {counts['pilot_questions']} pilot, {counts['eligible_questions']} eligible, "
        f"{counts['matched_questions']} matched, {counts['excluded_questions']} excluded",
        "matched       : " + ", ".join(f"[{q['question_index']}] {q['question_id']}" for q in manifest["binding"]["questions"]),
        "reviews       : " + ", ".join(f"{s}={n}" for s, n in counts["review_counts"].items()),
        f"design        : branches {manifest['binding']['design']['branches']} x conditions {manifest['binding']['design']['conditions']} "
        f"x repeats {manifest['binding']['design']['repeats']}; scheduling seed {manifest['binding']['design']['scheduling_seed']}",
        f"pipeline runs : {counts['pipeline_runs']} ({counts['pipeline_runs_formula']})",
        f"call bound    : {counts['api_call_upper_bound']} = {counts['pipeline_runs']} x {manifest['call_bound']['max_llm_calls_per_run']} "
        f"({manifest['call_bound']['longest_trajectory']}); upper bound, not an expected count",
        f"model         : {manifest['binding']['llm']['model']}  policy {manifest['binding']['controller']['policy_version']}, "
        f"max retries {manifest['binding']['controller']['max_search_retries']}",
        f"index         : {manifest['binding']['index']['index_sha256'][:16]}",
        f"first in order: {', '.join(r['run_id'] for r in runs[:4])}",
    ]
    for excluded in manifest["excluded_questions"]:
        lines.append(f"excluded [{excluded['question_index']:2d}] {excluded['question_id']}: {excluded['reason']}")
    lines.append("planning made no API call")
    return "\n".join(lines)


def format_dry_run(report: dict) -> str:
    checks = report["checks"]
    lines = [
        f"plan id       : {report['plan_id']}",
        f"pipeline runs : {report['pipeline_runs']} on {report['matched_questions']} matched questions",
        f"call bound    : {report['api_call_upper_bound']} ({report['call_bound']['longest_trajectory']}); upper bound, not an expected count",
        f"api calls     : {report['api_calls']} (dry run; no client, no key required)",
        f"checks        : plan verified={checks['plan_verified_against_current_files']}, unique runs={checks['runs_unique']}, "
        f"same context per case={checks['identical_initial_context_per_case']}, "
        f"same first input across branches/repeats={checks['identical_first_input_across_branches_and_repeats']}, "
        f"isolation problems={len(checks['isolation_problems'])}, all passed={checks['all_passed']}",
        f"first in order: {', '.join(report['first_scheduled_runs'][:4])}",
    ]
    for branch, rep in sorted(report["representative_requests"].items()):
        request = rep["first_grader_request"]
        lines.append(f"--- branch {branch}: first evaluator request of {rep['run_id']} (node {rep['grader_node']})")
        lines.append(f"model={request['model']} temperature={request['temperature']} max_output_tokens={request['max_output_tokens']} store={request['store']}")
        lines.append(f"prompt sha256={rep['hashes']['prompt_sha256'][:16]} schema sha256={rep['hashes']['schema_sha256'][:16]} input sha256={rep['hashes']['input_sha256'][:16]}")
        lines.append("input:")
        lines.append(request["input"][0]["content"][0]["text"])
    for problem in checks["isolation_problems"]:
        lines.append(f"isolation problem: {problem['run_id']}: {problem['problem']}")
    lines.append(f"dry run dir   : {report['out_dir']}")
    lines.append(report["note"])
    return "\n".join(lines)


def format_batch_result(result: dict) -> str:
    scope = (
        f"{result['scope_id'][:16]} ({result['scoped_runs']} runs)" if result.get("scope_id") else "whole plan"
    )
    return "\n".join(
        [
            f"plan id       : {result['plan_id']}",
            f"execution     : {result['execution_kind']}  batch dir {result['batch_dir']}",
            f"scope         : {scope}",
            f"planned       : {result['planned']}  finished total {result['finished_total']}  interrupted {result['interrupted_total']}  remaining {result['remaining']}",
            f"executed now  : {result['executed_now']} " + ", ".join(f"{k}={v}" for k, v in result["executed_status_counts"].items()),
            f"api attempts  : {result['api_attempts_this_invocation']} this invocation",
            f"stopped       : {result['stopped_reason'] or 'all pending runs executed'}",
        ]
    )


def format_scope_check(report: dict) -> str:
    paths = report["output_paths"]
    probe = paths["probe"]
    return "\n".join(
        [
            f"plan id       : {report['plan_id']}",
            f"scope file    : {report['scope_file']}",
            f"scope id      : {report['scope_id']}  ({report['scope_runs']} runs, label {report['label']})",
            f"batch dir     : {report['batch_dir']} ({'batch present' if report['batch_present'] else 'new batch'})",
            f"bound scope   : {report['batch_scope_id'] or 'none'}  matches={report['batch_scope_matches']}",
            f"already done  : {len(report['already_finished'])} finished, {len(report['already_interrupted'])} interrupted",
            f"pending       : {report['pending_count']}",
            f"longest path  : {paths['longest_path_length']} chars (limit {paths['max_path']}), over limit {paths['paths_over_limit']}",
            f"write probe   : ok={probe.get('write_ok')} read_back={probe.get('read_back_ok')} cleaned={probe.get('cleaned_up')}",
            f"result        : {'OK' if report['ok'] else 'NOT USABLE'}  (no API call made)",
        ]
    )


def format_summary(summary: dict) -> str:
    lines = [
        f"plan id       : {summary['plan_id']}",
        f"batch dir     : {summary['batch_dir']} ({'execution: ' + str(summary['execution_kind']) if summary['batch_present'] else 'no executed batch'})",
        f"planned       : {summary['planned']}",
        "status        : " + ", ".join(f"{k}={v}" for k, v in summary["status_counts"].items()),
    ]
    for branch, by_condition in sorted(summary["outcomes_by_branch_and_condition"].items()):
        for condition, counts in by_condition.items():
            lines.append(f"outcomes {branch} {condition:<12}: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    for grader in ("typed", "binary"):
        table = summary["first_evaluation_confusion"][grader]
        for reviewed, predicted in sorted(table.items()):
            lines.append(f"first eval {grader:<6} reviewed={reviewed:<12}: " + ", ".join(f"{k}={v}" for k, v in sorted(predicted.items())))
    p = summary["policy"]
    lines.append(f"policy        : steps {p['steps_total']}, mismatch {p['steps_mismatch']}, override {p['steps_override']}; runs any mismatch {p['runs_any_mismatch']}, any override {p['runs_any_override']}")
    for branch, b in sorted(p["by_branch"].items()):
        lines.append(f"  branch {branch}    : runs {b['runs']}, steps {b['steps']}, mismatch {b['mismatch']}, override {b['override']}, runs any mismatch {b['runs_any_mismatch']}")
    a = summary["api"]
    u = a["usage_totals"]
    lines.append(f"api           : attempts (ledger) {a['attempts_recorded_by_budget_ledger']}, calls logged {a['calls_logged_in_runs']}, tokens in={u['input_tokens']} out={u['output_tokens']} total={u['total_tokens']} cached={u['cached_tokens']}")
    t = summary["timing"]
    lines.append(f"timing        : runs {t['runs_with_timing']}, total {t['total_seconds_sum']}s, grader {t['grader_seconds_sum']}s, rewrite {t['rewrite_seconds_sum']}s, generator {t['generator_seconds_sum']}s")
    lines.append(f"post-retry    : runs with retry search {summary['post_retry']['runs_with_retry_search']}; {summary['post_retry']['note']}")
    for failure in summary["non_completed_runs"][:20]:
        lines.append(f"non-completed : {failure}")
    if len(summary["non_completed_runs"]) > 20:
        lines.append(f"non-completed : ... {len(summary['non_completed_runs']) - 20} more in summary.json")
    for limit in summary["interpretation_limits"]:
        lines.append(f"limit         : {limit}")
    return "\n".join(lines)
