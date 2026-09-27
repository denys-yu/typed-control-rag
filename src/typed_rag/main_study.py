"""Stage 14: the main experiment - plan, execution and consolidation.

This module adds no new execution framework. It derives the main-study plan
from the accepted reviews and drives the stage 7 batch runner
(`pilot.run_batch`) with that plan, the approved main contexts, the main
question file and the frozen main index. Checkpointing, the budgeted transport,
the output-path preflight, the scope mechanism and the request-isolation check
are the existing ones.

What is main-study specific lives here:

* selecting the sample from `results/main_sample_final.json` and the accepted
  reviews, and refusing anything not approved with the intended state;
* the plan binding and its identity (protocol, acceptance, sample, contexts,
  reviews, index, prompts, schemas, policy, model parameters, implementation);
* the cumulative stage 14 attempt ledger and the global attempt ceiling, which
  is enforced across invocations in addition to the per-invocation budget;
* consolidation into one index row per planned coordinate.

Nothing here reads gold annotations on the execution path.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from typed_rag import controller, fault_cases, hotpotqa, nodes, pilot, rag_run, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.download import sha256_file

MODE = "stage14_main_experiment"
PLAN_FORMAT_VERSION = "1.0"
STAGE = 14

PLAN_DIRNAME = "main_plan"
MANIFEST_FILENAME = "manifest.json"
RUNS_FILENAME = "runs.jsonl"
LEDGER_FILENAME = "stage14_execution_ledger.json"
RUN_INDEX_FILENAME = "main_run_index.jsonl"

PROCESSED_DIRNAME = "main"
QUESTIONS_FILENAME = "main_questions.jsonl"
ANNOTATIONS_FILENAME = "main_annotations.jsonl"
CORPUS_FILENAME = "main_corpus.jsonl"
PREPARATION_DIRNAME = "main_preparation"
INDEX_DIRNAME = "main_retrieval"
CONTEXTS_FILENAME = "fault_contexts.jsonl"
FAULT_ANNOTATIONS_FILENAME = "fault_annotations.jsonl"
REVIEWS_FILENAME = "fault_reviews.jsonl"
SAMPLE_FILENAME = "main_sample_final.json"
ACCEPTANCE_FILENAME = "stage14_acceptance.json"
PROTOCOL_FILENAME = "main_experiment_protocol_v3.md"

REPEATS = 3
PLANNED_COORDINATES = 2880
GLOBAL_ATTEMPT_CEILING = 11520

IMPLEMENTATION_FILES = (
    "src/typed_rag/controller.py",
    "src/typed_rag/nodes.py",
    "src/typed_rag/llm.py",
    "src/typed_rag/rag_run.py",
    "src/typed_rag/retrieval.py",
    "src/typed_rag/pilot.py",
    "src/typed_rag/main_study.py",
    "src/typed_rag/config.py",
    "tools/stage14_cli.py",
    "config/experiment.json",
)

SELECTION_RULE = (
    "the first 60 questions of the frozen randomized candidate order whose four contexts are "
    "approved with observed_state equal to the intended state, after the researcher's stage 14 "
    "acceptance and the exclusion of eligible question 54; recorded in main_sample_final.json"
)
ORDER_RULE = (
    "canonical order question x condition x branch x repeat, then one deterministic shuffle with "
    "random.Random(f'{seed}:{plan_id}')"
)


class MainStudyError(Exception):
    """Raised when the main study cannot be planned, verified or executed."""


class StalePlanError(MainStudyError):
    """Raised when a bound input changed after the plan was frozen."""


# --- paths and inputs ---------------------------------------------------------------


def processed_dir(config: ExperimentConfig) -> Path:
    return config.paths["data_processed"] / PROCESSED_DIRNAME


def preparation_dir(config: ExperimentConfig) -> Path:
    return config.paths["results"] / PREPARATION_DIRNAME


def index_dir(config: ExperimentConfig) -> Path:
    return config.paths["artifacts"] / INDEX_DIRNAME


def plan_dir(config: ExperimentConfig) -> Path:
    return config.paths["results"] / PLAN_DIRNAME


def load_questions(config: ExperimentConfig) -> list[dict]:
    """Pipeline input: main questions. Carries an id and the question text only."""
    return hotpotqa.read_jsonl(processed_dir(config) / QUESTIONS_FILENAME)


def load_contexts(config: ExperimentConfig) -> list[dict]:
    return hotpotqa.read_jsonl(preparation_dir(config) / CONTEXTS_FILENAME)


def load_fault_annotations(config: ExperimentConfig) -> list[dict]:
    return hotpotqa.read_jsonl(preparation_dir(config) / FAULT_ANNOTATIONS_FILENAME)


def load_reviews(config: ExperimentConfig) -> list[dict]:
    return hotpotqa.read_jsonl(preparation_dir(config) / REVIEWS_FILENAME)


def load_sample(config: ExperimentConfig) -> dict:
    path = config.paths["results"] / SAMPLE_FILENAME
    if not path.is_file():
        raise MainStudyError(f"final sample not found: {path}. Run: python tools/stage14_accept.py")
    return hotpotqa.read_json(path)


def load_index(config: ExperimentConfig) -> retrieval.LoadedIndex:
    """The frozen main index, refusing a stale one instead of rebuilding."""
    directory = index_dir(config)
    manifest_path = directory / retrieval.INDEX_MANIFEST_FILENAME
    matrix_path = directory / retrieval.EMBEDDINGS_FILENAME
    documents_path = directory / retrieval.DOCUMENTS_FILENAME
    for path in (manifest_path, matrix_path, documents_path):
        if not path.is_file():
            raise MainStudyError(f"no main index at {path}")
    import numpy as np

    manifest = hotpotqa.read_json(manifest_path)
    embeddings = np.load(matrix_path, allow_pickle=False)
    documents = hotpotqa.read_jsonl(documents_path)
    problems = []
    if embeddings.shape[0] != len(documents):
        problems.append(f"{embeddings.shape[0]} rows for {len(documents)} documents")
    if manifest.get("corpus_sha256") != sha256_file(processed_dir(config) / CORPUS_FILENAME):
        problems.append("corpus_sha256 differs from the current main corpus")
    for field in ("model_name", "model_revision"):
        if manifest.get(field) != getattr(config.retrieval, field):
            problems.append(f"{field} differs from the configuration")
    if problems:
        raise StalePlanError("stale main index:\n  " + "\n  ".join(problems))
    return retrieval.LoadedIndex(embeddings=embeddings, documents=documents, manifest=manifest)


def index_identity(config: ExperimentConfig) -> dict:
    manifest = hotpotqa.read_json(index_dir(config) / retrieval.INDEX_MANIFEST_FILENAME)
    return {
        "index_sha256": manifest["index_sha256"],
        "corpus_sha256": manifest["corpus_sha256"],
        "model_name": manifest["model_name"],
        "model_revision": manifest["model_revision"],
        "document_count": manifest.get("document_count"),
        "file_sha256": manifest.get("file_sha256"),
        "top_k": config.retrieval.top_k,
    }


def implementation_hashes(config: ExperimentConfig) -> dict:
    return {
        relpath: (sha256_file(config.project_root / relpath) if (config.project_root / relpath).is_file() else None)
        for relpath in IMPLEMENTATION_FILES
    }


# --- selection ----------------------------------------------------------------------


def select_sample(config: ExperimentConfig) -> dict:
    """Rebuild the sample from the accepted reviews and check it against the record.

    Membership is derived from the files, never from the sample document alone:
    a question enters only when all four of its contexts are approved with
    observed_state equal to the intended state.
    """
    sample = load_sample(config)
    annotations = {a["case_id"]: a for a in load_fault_annotations(config)}
    contexts = {c["case_id"]: c for c in load_contexts(config)}
    reviews = {r["case_id"]: r for r in load_reviews(config)}
    questions = {q["question_id"]: q for q in load_questions(config)}
    position_of = {q["question_id"]: i for i, q in enumerate(load_questions(config))}

    problems: list[str] = []
    for case_id, review in reviews.items():
        status = review.get("review_status")
        if status in (fault_cases.REVIEW_APPROVED, fault_cases.REVIEW_REJECTED):
            if not (review.get("reviewer") or "").strip():
                problems.append(f"{status} review of {case_id} has no reviewer")
            if not (review.get("note") or "").strip():
                problems.append(f"{status} review of {case_id} has an empty justification")
        if status == fault_cases.REVIEW_APPROVED and review.get("observed_state") != annotations[case_id]["expected_state"]:
            problems.append(f"approved review of {case_id} does not implement its condition")
        if review.get("content_identity") != annotations[case_id]["content_identity"]:
            problems.append(f"review of {case_id} refers to another context version")

    included: list[dict] = []
    for entry in sample["questions"]:
        question_id = entry["question_id"]
        if question_id not in questions:
            problems.append(f"{question_id} is not in the main question file")
            continue
        cases = {}
        for condition in fault_cases.CONDITIONS:
            case_id = entry["case_ids"][condition]
            annotation = annotations.get(case_id)
            review = reviews.get(case_id)
            if annotation is None or review is None:
                problems.append(f"{case_id} has no annotation or review")
                continue
            if review["review_status"] != fault_cases.REVIEW_APPROVED:
                problems.append(f"{case_id} is {review['review_status']}, not approved")
                continue
            if review["observed_state"] != annotation["expected_state"]:
                problems.append(f"{case_id} approved with a state other than the intended one")
                continue
            context = contexts[case_id]
            if context["question"] != questions[question_id]["question"]:
                problems.append(f"{case_id} carries a question text different from the question file")
            cases[condition] = {
                "case_id": case_id,
                "intended_state": annotation["expected_state"],
                "observed_state": review["observed_state"],
                "doc_ids": [d["doc_id"] for d in context["documents"]],
                "context_sha256": pilot.case_content_hash(context),
                "content_identity": annotation["content_identity"],
            }
        if len(cases) == len(fault_cases.CONDITIONS):
            included.append(
                {
                    "sample_position": entry["sample_position"],
                    "question_index": position_of[question_id],
                    "eligible_question_number": entry["eligible_question_number"],
                    "candidate_position": entry["candidate_position"],
                    "question_id": question_id,
                    "question": questions[question_id]["question"],
                    "question_sha256": pilot.question_hash(questions[question_id]["question"]),
                    "cases": cases,
                }
            )
    pilot_ids = set(
        hotpotqa.read_json(config.processed_dir / hotpotqa.PILOT_IDS_FILENAME)["question_ids"]
    )
    overlap = sorted({q["question_id"] for q in included} & pilot_ids)
    if overlap:
        problems.append(f"pilot question ids in the sample: {overlap}")
    if len(included) != len(sample["questions"]):
        problems.append(f"{len(included)} questions reconstructed from {len(sample['questions'])} recorded")
    return {
        "valid": not problems,
        "problems": sorted(set(problems), key=problems.index),
        "included": included,
        "sample_sha256": sha256_file(config.paths["results"] / SAMPLE_FILENAME),
        "pilot_overlap": overlap,
    }


# --- plan ---------------------------------------------------------------------------


def _binding(config: ExperimentConfig, selection: dict) -> dict:
    results = config.paths["results"]
    preparation = preparation_dir(config)
    return {
        "plan_format_version": PLAN_FORMAT_VERSION,
        "mode": MODE,
        "design": {
            "branches": list(config.pilot.branches),
            "conditions": list(fault_cases.CONDITIONS),
            "repeats": REPEATS,
            "scheduling_seed": config.seed,
            "order_rule": ORDER_RULE,
        },
        "questions": selection["included"],
        "sources": {
            "protocol_sha256": sha256_file(results / PROTOCOL_FILENAME),
            "acceptance_sha256": sha256_file(results / ACCEPTANCE_FILENAME),
            "sample_sha256": sha256_file(results / SAMPLE_FILENAME),
            "reviews_sha256": sha256_file(preparation / REVIEWS_FILENAME),
            "annotations_sha256": sha256_file(preparation / FAULT_ANNOTATIONS_FILENAME),
            "contexts_sha256": sha256_file(preparation / CONTEXTS_FILENAME),
            "main_questions_sha256": sha256_file(processed_dir(config) / QUESTIONS_FILENAME),
            "main_corpus_sha256": sha256_file(processed_dir(config) / CORPUS_FILENAME),
        },
        "index": index_identity(config),
        "prompts": pilot.prompt_and_schema_hashes(config),
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
        "implementation_files": implementation_hashes(config),
    }


def build_plan(config: ExperimentConfig) -> tuple[dict, list[dict]]:
    """Freeze the main plan from the accepted sample. Reads files only; no API."""
    selection = select_sample(config)
    if not selection["valid"]:
        raise MainStudyError("the accepted sample is inconsistent:\n  " + "\n  ".join(selection["problems"]))
    for branch in config.pilot.branches:
        controller.get_branch(branch)

    binding = _binding(config, selection)
    plan_id = nodes.sha256_json(binding)
    bound = pilot.max_llm_calls_per_run(config.controller.max_search_retries)

    canonical: list[dict] = []
    for question in selection["included"]:
        for condition in fault_cases.CONDITIONS:
            case = question["cases"][condition]
            for branch in config.pilot.branches:
                for repeat in range(1, REPEATS + 1):
                    run = {
                        "sample_position": question["sample_position"],
                        "question_index": question["question_index"],
                        "question_id": question["question_id"],
                        "case_id": case["case_id"],
                        "condition": condition,
                        "branch": branch,
                        "repeat": repeat,
                        "context_sha256": case["context_sha256"],
                    }
                    run["run_id"] = pilot._run_id(plan_id, run)
                    canonical.append(run)
    if len(canonical) != PLANNED_COORDINATES:
        raise MainStudyError(f"{len(canonical)} coordinates planned, expected {PLANNED_COORDINATES}")

    order = list(range(len(canonical)))
    random.Random(f"{config.seed}:{plan_id}").shuffle(order)
    runs = [dict(canonical[i], schedule_position=position) for position, i in enumerate(order)]
    if len({r["run_id"] for r in runs}) != len(runs):
        raise MainStudyError("run identifiers are not unique")

    manifest = {
        "plan_id": plan_id,
        "stage": STAGE,
        "created_at_utc": pilot.utc_now(),
        "binding": binding,
        "counts": {
            "questions": len(selection["included"]),
            "conditions": len(fault_cases.CONDITIONS),
            "branches": len(config.pilot.branches),
            "repeats": REPEATS,
            "planned_coordinates": len(runs),
            "planned_coordinates_formula": (
                f"{len(selection['included'])} questions x {len(fault_cases.CONDITIONS)} conditions x "
                f"{len(config.pilot.branches)} branches x {REPEATS} repeats"
            ),
            "approved_initial_contexts": len(selection["included"]) * len(fault_cases.CONDITIONS),
            "provider_attempt_ceiling": GLOBAL_ATTEMPT_CEILING,
            "attempt_ceiling_note": (
                "planned coordinates x the verified four-call maximum trajectory; an upper bound "
                "from the control flow, never an expected count or a monetary estimate"
            ),
        },
        "call_bound": bound,
        "selection_rule": SELECTION_RULE,
        "protocol": PROTOCOL_FILENAME,
        "implementation_git": pilot._git_state(config),
        "note": "planning made no API call",
    }
    return manifest, runs


def plan_paths(config: ExperimentConfig) -> tuple[Path, Path]:
    return plan_dir(config) / MANIFEST_FILENAME, plan_dir(config) / RUNS_FILENAME


def write_plan(config: ExperimentConfig, manifest: dict, runs: list[dict], replace: bool = False) -> dict:
    manifest_path, runs_path = plan_paths(config)
    if manifest_path.is_file() and not replace:
        existing = hotpotqa.read_json(manifest_path)
        if existing.get("plan_id") != manifest["plan_id"]:
            raise MainStudyError(
                f"a different plan is already frozen ({str(existing.get('plan_id'))[:16]} vs "
                f"{manifest['plan_id'][:16]}); refusing to overwrite it silently"
            )
        return {"written": False, "plan_id": existing["plan_id"]}
    plan_dir(config).mkdir(parents=True, exist_ok=True)
    hotpotqa.write_json(manifest_path, manifest)
    hotpotqa.write_jsonl(runs_path, runs)
    return {
        "written": True,
        "plan_id": manifest["plan_id"],
        "manifest_sha256": sha256_file(manifest_path),
        "runs_sha256": sha256_file(runs_path),
    }


def load_plan(config: ExperimentConfig) -> tuple[dict, list[dict]]:
    manifest_path, runs_path = plan_paths(config)
    if not manifest_path.is_file() or not runs_path.is_file():
        raise MainStudyError("no frozen main plan; run: python tools/stage14_cli.py plan")
    manifest = hotpotqa.read_json(manifest_path)
    runs = hotpotqa.read_jsonl(runs_path)
    if len(runs) != manifest["counts"]["planned_coordinates"]:
        raise StalePlanError("the frozen runs file does not match the manifest count")
    return manifest, runs


def verify_plan(config: ExperimentConfig, manifest: dict) -> list[str]:
    """Name every bound component that changed since the plan was frozen."""
    selection = select_sample(config)
    problems = list(selection["problems"])
    if selection["valid"]:
        current = _binding(config, selection)
        frozen = manifest["binding"]

        def walk(prefix: str, a: Any, b: Any) -> None:
            if isinstance(a, dict) and isinstance(b, dict):
                for key in sorted(set(a) | set(b)):
                    walk(f"{prefix}.{key}" if prefix else key, a.get(key), b.get(key))
            elif a != b:
                problems.append(f"{prefix}: frozen={a!r} current={b!r}")

        walk("", frozen, current)
        if nodes.sha256_json(current) != manifest["plan_id"]:
            problems.append("the recomputed binding hash differs from the frozen plan_id")
    return problems


def require_current_plan(config: ExperimentConfig) -> tuple[dict, list[dict]]:
    manifest, runs = load_plan(config)
    problems = verify_plan(config, manifest)
    if problems:
        raise StalePlanError(
            "the frozen main plan no longer matches the current files:\n  " + "\n  ".join(problems)
        )
    contexts = {c["case_id"]: c for c in load_contexts(config)}
    for run in runs:
        context = contexts.get(run["case_id"])
        if context is None:
            raise StalePlanError(f"context of case {run['case_id']} is missing")
        if pilot.case_content_hash(context) != run["context_sha256"]:
            raise StalePlanError(f"context of case {run['case_id']} changed since the plan was frozen")
    return manifest, runs


# --- cumulative attempt ledger ---------------------------------------------------------


def ledger_path(config: ExperimentConfig) -> Path:
    return config.paths["results"] / LEDGER_FILENAME


def read_ledger(config: ExperimentConfig) -> dict:
    path = ledger_path(config)
    if not path.is_file():
        return {
            "stage": STAGE,
            "global_attempt_ceiling": GLOBAL_ATTEMPT_CEILING,
            "cumulative_attempts": 0,
            "invocations": [],
            "note": (
                "authoritative cumulative count of provider attempts across all stage 14 "
                "invocations, including failed attempts; every attempt is counted once"
            ),
        }
    return hotpotqa.read_json(path)


def batch_attempts(batch_dir: Path) -> int:
    """Attempts recorded by the budget ledger of a batch directory."""
    budget_path = batch_dir / pilot.BUDGET_FILENAME
    if not budget_path.is_file():
        return 0
    return int(hotpotqa.read_json(budget_path).get("attempts_total", 0))


def remaining_global_budget(config: ExperimentConfig, batch_dir: Path | None = None) -> dict:
    """Cumulative attempts and what is left of the global ceiling."""
    ledger = read_ledger(config)
    recorded = int(ledger.get("cumulative_attempts", 0))
    observed = batch_attempts(batch_dir) if batch_dir is not None else None
    cumulative = max(recorded, observed) if observed is not None else recorded
    return {
        "recorded_in_ledger": recorded,
        "observed_in_batch_budget": observed,
        "cumulative_attempts": cumulative,
        "agreement": observed is None or observed == recorded,
        "global_attempt_ceiling": GLOBAL_ATTEMPT_CEILING,
        "remaining_global_budget": GLOBAL_ATTEMPT_CEILING - cumulative,
    }


def record_invocation(config: ExperimentConfig, entry: dict, cumulative_attempts: int) -> dict:
    ledger = read_ledger(config)
    ledger["invocations"].append(entry)
    ledger["cumulative_attempts"] = cumulative_attempts
    ledger["remaining_global_budget"] = GLOBAL_ATTEMPT_CEILING - cumulative_attempts
    ledger["updated_at_utc"] = pilot.utc_now()
    hotpotqa.write_json(ledger_path(config), ledger)
    return ledger


# --- execution --------------------------------------------------------------------------


def run_main_batch(
    config: ExperimentConfig,
    batch_dir: Path,
    max_coordinates: int,
    resume: bool = True,
    transport: Any | None = None,
    execution_kind: str = pilot.EXECUTION_REAL,
) -> dict:
    """One invocation: verify the plan, size the budget, run, and record the ledger.

    The per-invocation budget is the smaller of four attempts per scheduled
    coordinate and the remaining global stage 14 allowance. Both limits are
    enforced: the transport stops at the per-invocation budget, and this function
    refuses to start when the global allowance is exhausted.
    """
    manifest, runs = require_current_plan(config)
    plan_id = manifest["plan_id"]
    contexts = {c["case_id"]: c for c in load_contexts(config)}
    questions = {q["question_id"]: q for q in load_questions(config)}

    checkpoint = pilot.read_checkpoint(batch_dir / pilot.CHECKPOINT_FILENAME)
    pending = [
        run
        for run in runs
        if run["run_id"] not in checkpoint["finished"] and run["run_id"] not in checkpoint["interrupted"]
    ]
    scheduled = min(max_coordinates, len(pending))
    budget_state = remaining_global_budget(config, batch_dir)
    if not budget_state["agreement"]:
        raise MainStudyError(
            "attempt accounting disagreement between the stage 14 ledger "
            f"({budget_state['recorded_in_ledger']}) and the batch budget file "
            f"({budget_state['observed_in_batch_budget']}); refusing to start an invocation"
        )
    if scheduled == 0:
        return {
            "plan_id": plan_id,
            "scheduled_coordinates": 0,
            "stopped_reason": "nothing pending",
            "budget": budget_state,
        }
    invocation_limit = min(
        4 * scheduled, budget_state["remaining_global_budget"]
    )
    if invocation_limit <= 0:
        raise MainStudyError(
            f"global stage 14 attempt ceiling reached ({budget_state['cumulative_attempts']} of "
            f"{GLOBAL_ATTEMPT_CEILING}); no further provider call is authorized"
        )

    index = load_index(config)
    model = retrieval.load_model(config)
    started = pilot.utc_now()
    error: BaseException | None = None
    try:
        result = pilot.run_batch(
            config,
            max_api_calls=invocation_limit,
            resume=resume,
            max_runs=scheduled,
            transport=transport,
            index=index,
            model=model,
            execution_kind=execution_kind,
            batch_dir=batch_dir,
            plan=(manifest, runs),
            contexts=contexts,
            questions=questions,
            mode=MODE,
        )
    except BaseException as exc:  # noqa: BLE001 - the ledger must record the attempts either way
        error = exc
        result = {"stopped_reason": f"{type(exc).__name__}: {exc}", "api_attempts_this_invocation": None}

    cumulative = batch_attempts(batch_dir)
    entry = {
        "started_at_utc": started,
        "finished_at_utc": pilot.utc_now(),
        "plan_id": plan_id,
        "batch_dir": str(batch_dir),
        "execution_kind": execution_kind,
        "scheduled_coordinates": scheduled,
        "invocation_limit": invocation_limit,
        "limit_basis": (
            "min(4 x scheduled coordinates, remaining global budget)"
        ),
        "attempts_before": budget_state["cumulative_attempts"],
        "attempts_after": cumulative,
        "attempts_this_invocation": cumulative - budget_state["cumulative_attempts"],
        "executed_now": result.get("executed_now"),
        "stopped_reason": result.get("stopped_reason"),
        "error": None if error is None else f"{type(error).__name__}: {error}",
    }
    record_invocation(config, entry, cumulative)
    if error is not None:
        raise error
    result["budget"] = remaining_global_budget(config, batch_dir)
    result["invocation"] = entry
    return result


# --- offline checks ----------------------------------------------------------------------


def gold_answers(config: ExperimentConfig) -> dict[str, str]:
    """Research metadata for the isolation check only; the execution path never calls this."""
    return {
        a["question_id"]: a["answer"]
        for a in hotpotqa.read_jsonl(processed_dir(config) / ANNOTATIONS_FILENAME)
    }


def _residual(config: ExperimentConfig, request: dict, context: dict) -> str:
    """The user input with the question, texts, titles and doc_ids removed."""
    residual = request["input"][0]["content"][0]["text"].replace(context["question"], "")
    for field in ("text", "title", "doc_id"):
        for document in context["documents"]:
            residual = residual.replace(document[field], "")
    return residual


def classify_isolation_problem(
    problem: str, config: ExperimentConfig, request: dict, context: dict, gold_answer: str | None
) -> dict:
    """Separate a real leak from a substring match inside the static prompt.

    The shared heuristic flags a gold answer found anywhere outside the document
    texts, including inside the fixed grader instructions. A short answer such as
    "no" occurs there as an ordinary English word. That is not a leak: the
    instructions are one static file, written before this sample existed and
    identical for every case, so they cannot carry question-specific information.
    A gold answer inside the *user input* residual would be a real leak and stays
    a failure.
    """
    if "gold answer" not in problem or not gold_answer:
        return {"problem": problem, "real": True, "basis": "not a gold-answer heuristic hit"}
    in_residual = gold_answer in _residual(config, request, context)
    return {
        "problem": problem,
        "real": bool(in_residual),
        "basis": (
            "the gold answer appears in the user input outside the documents"
            if in_residual
            else "substring of the static, question-independent grader instructions only; "
            "the user input is clean"
        ),
        "gold_answer_in_user_input_residual": in_residual,
    }


def offline_checks(config: ExperimentConfig, batch_dir: Path) -> dict:
    """Every gate that must pass before the first provider call. No client, no network."""
    manifest, runs = require_current_plan(config)
    contexts = {c["case_id"]: c for c in load_contexts(config)}
    annotations = {a["case_id"]: a for a in load_fault_annotations(config)}
    reviews = {r["case_id"]: r for r in load_reviews(config)}
    questions = {q["question_id"]: q for q in load_questions(config)}
    gold = gold_answers(config)
    pilot_ids = set(
        hotpotqa.read_json(config.processed_dir / hotpotqa.PILOT_IDS_FILENAME)["question_ids"]
    )

    question_ids = {r["question_id"] for r in runs}
    case_ids = {r["case_id"] for r in runs}
    inputs_by_case: dict[str, set[str]] = {}
    isolation_problems: list[str] = []
    heuristic_false_positives: list[dict] = []
    instruction_variants: dict[str, set[str]] = {}
    branch_requests: dict[str, dict[str, str]] = {}

    for case_id in sorted(case_ids):
        context = contexts[case_id]
        hashes = {}
        for branch_name in config.pilot.branches:
            branch = controller.get_branch(branch_name)
            request = controller.first_grader_request(
                config, branch, context["question"], context["documents"]
            )
            hashes[branch_name] = nodes.sha256_json(request)
            inputs_by_case.setdefault(case_id, set()).add(
                nodes.sha256_text(request["input"][0]["content"][0]["text"])
            )
            for problem in pilot.check_request_isolation(
                config,
                request,
                context,
                annotations[case_id],
                reviews[case_id],
                gold.get(context["question_id"]),
            ):
                verdict = classify_isolation_problem(
                    problem, config, request, context, gold.get(context["question_id"])
                )
                entry = f"{case_id}/{branch_name}: {problem}"
                if verdict["real"]:
                    isolation_problems.append(entry)
                else:
                    heuristic_false_positives.append({**verdict, "case_id": case_id, "branch": branch_name})
            instruction_variants.setdefault(branch.grader_node, set()).add(
                nodes.sha256_text(request["instructions"])
            )
        branch_requests[case_id] = hashes

    ac_identical = all(h["A"] == h["C"] for h in branch_requests.values())
    bd_identical = all(h["B"] == h["D"] for h in branch_requests.values())
    same_user_input = all(len(values) == 1 for values in inputs_by_case.values())

    coordinates = {
        (r["question_id"], r["case_id"], r["branch"], r["repeat"]) for r in runs
    }
    path_check = pilot.check_output_paths(batch_dir, [r["run_id"] for r in runs])

    checks = {
        "plan_verified_against_current_files": True,
        "questions": len(question_ids),
        "approved_initial_contexts": len(case_ids),
        "planned_coordinates": len(runs),
        "unique_coordinates": len(coordinates),
        "unique_run_ids": len({r["run_id"] for r in runs}),
        "pilot_question_ids_excluded": not (question_ids & pilot_ids),
        "sixty_questions": len(question_ids) == 60,
        "two_hundred_forty_contexts": len(case_ids) == 240,
        "exactly_planned_coordinates": len(runs) == PLANNED_COORDINATES == len(coordinates),
        "identical_initial_context_across_branches_and_repeats": same_user_input,
        "identical_first_request_A_and_C": ac_identical,
        "identical_first_request_B_and_D": bd_identical,
        "no_research_metadata_in_model_input": not isolation_problems,
        "isolation_problems": isolation_problems[:20],
        "isolation_heuristic_false_positives": len(heuristic_false_positives),
        "isolation_false_positive_examples": heuristic_false_positives[:3],
        "instructions_identical_across_cases": {
            node: len(variants) == 1 for node, variants in sorted(instruction_variants.items())
        },
        "index_identity": manifest["binding"]["index"]["index_sha256"],
        "corpus_sha256": manifest["binding"]["index"]["corpus_sha256"],
        "model": manifest["binding"]["llm"]["model"],
        "generation_parameters": manifest["binding"]["llm"]["generation_parameters"],
        "controller": manifest["binding"]["controller"],
        "output_path_check": path_check,
        "questions_carry_only_id_and_text": all(
            set(q) == {"question_id", "question"} for q in questions.values()
        ),
    }
    checks["all_passed"] = all(
        [
            checks["pilot_question_ids_excluded"],
            checks["sixty_questions"],
            checks["two_hundred_forty_contexts"],
            checks["exactly_planned_coordinates"],
            checks["unique_run_ids"] == len(runs),
            checks["identical_initial_context_across_branches_and_repeats"],
            checks["identical_first_request_A_and_C"],
            checks["identical_first_request_B_and_D"],
            checks["no_research_metadata_in_model_input"],
            checks["questions_carry_only_id_and_text"],
            all(checks["instructions_identical_across_cases"].values()),
            path_check["ok"],
        ]
    )
    return checks


# --- consolidation -------------------------------------------------------------------------


def consolidate(config: ExperimentConfig, batch_dir: Path) -> dict:
    """One index row per planned coordinate, including missing ones."""
    manifest, runs = load_plan(config)
    checkpoint = pilot.read_checkpoint(batch_dir / pilot.CHECKPOINT_FILENAME)
    reviewed_by_case = {
        case["case_id"]: case["observed_state"]
        for question in manifest["binding"]["questions"]
        for case in question["cases"].values()
    }
    rows: list[dict] = []
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0, "calls_with_usage": 0}
    calls_logged = 0
    attempts_logged = 0
    unknown_usage: list[str] = []
    retrieval_changes = {"set_changed": 0, "order_only": 0, "identical": 0, "content_changed_same_ids": 0}

    for run in runs:
        run_id = run["run_id"]
        row = {
            "coordinate": f"{run['question_id']}|{run['case_id']}|{run['branch']}|r{run['repeat']}",
            "run_id": run_id,
            "schedule_position": run["schedule_position"],
            "sample_position": run["sample_position"],
            "question_id": run["question_id"],
            "case_id": run["case_id"],
            "condition": run["condition"],
            "branch": run["branch"],
            "repeat": run["repeat"],
            "initial_reviewed_state": reviewed_by_case.get(run["case_id"]),
            "record_status": pilot.RUN_PENDING,
            "status": None,
            "terminal_outcome": None,
            "answer": None,
            "returned_evidence_doc_ids": None,
            "citation_id_membership_valid": None,
            "final_context_sha256": None,
            "retried": None,
            "searches": None,
            "api_calls": None,
            "api_attempts": None,
            "token_usage": None,
            "usage_known": False,
            "latency_seconds": None,
            "post_retry_reviewed_state": None,
            "answer_support": None,
            "context_state_after_retry": None,
            "retrieval_change_after_retry": None,
        }
        if run_id in checkpoint["interrupted"]:
            row["record_status"] = pilot.RUN_INTERRUPTED
            row["status"] = "interrupted"
            rows.append(row)
            unknown_usage.append(run_id)
            continue
        if run_id not in checkpoint["finished"]:
            rows.append(row)
            continue
        record = checkpoint["finished"][run_id]
        row["record_status"] = record["batch_status"]
        run_path = batch_dir / pilot.RUNS_DIRNAME / run_id / controller.RUN_FILENAME
        if not run_path.is_file():
            row["status"] = "run_json_missing"
            rows.append(row)
            unknown_usage.append(run_id)
            continue
        result = hotpotqa.read_json(run_path)
        trajectory = result.get("trajectory", [])
        generator = result.get("generator") or {}
        row.update(
            {
                "status": result["status"],
                "terminal_outcome": result.get("final_outcome"),
                "answer": (generator.get("result") or {}).get("answer"),
                "returned_evidence_doc_ids": (generator.get("result") or {}).get("evidence_doc_ids"),
                "retried": len(trajectory) > 1,
                "searches": result.get("searches"),
                "api_calls": result.get("api_calls"),
                "api_attempts": (result.get("pilot") or {}).get("api_attempts"),
                "token_usage": result.get("usage_totals"),
                "usage_known": bool(result.get("usage_totals", {}).get("calls_with_usage")),
                "latency_seconds": (result.get("timings") or {}).get("total_seconds"),
                "generator_validation_status": generator.get("status"),
                "any_policy_mismatch": result.get("any_policy_mismatch"),
                "any_policy_override": result.get("any_policy_override"),
                "executed_actions": [s.get("executed_action") for s in trajectory],
                "proposed_actions": [s.get("proposed_action") for s in trajectory],
                "expected_actions": [s.get("expected_action") for s in trajectory],
                "first_evaluator_assessment": trajectory[0].get("assessment") if trajectory else None,
                "second_evaluator_assessment": trajectory[1].get("assessment") if len(trajectory) > 1 else None,
            }
        )
        context_path = batch_dir / pilot.RUNS_DIRNAME / run_id / rag_run.CONTEXT_FILENAME
        if context_path.is_file():
            context_record = hotpotqa.read_json(context_path)
            final = context_record["contexts"][-1]
            row["final_context_sha256"] = final.get("context_sha256")
            row["final_context_doc_ids"] = final.get("doc_ids")
            if len(context_record["contexts"]) > 1:
                first_ids = context_record["contexts"][0]["doc_ids"]
                last_ids = final["doc_ids"]
                if set(first_ids) != set(last_ids):
                    retrieval_changes["set_changed"] += 1
                    row["retrieval_change_after_retry"] = "set_changed"
                elif first_ids != last_ids:
                    retrieval_changes["order_only"] += 1
                    row["retrieval_change_after_retry"] = "order_only"
                else:
                    retrieval_changes["identical"] += 1
                    row["retrieval_change_after_retry"] = "identical"
            if row["returned_evidence_doc_ids"] is not None:
                ids = set(final.get("doc_ids") or [])
                row["citation_id_membership_valid"] = all(
                    doc_id in ids for doc_id in row["returned_evidence_doc_ids"]
                )
        calls_logged += result.get("api_calls", 0)
        attempts_logged += (result.get("pilot") or {}).get("api_attempts", 0) or 0
        for key in usage:
            usage[key] += result.get("usage_totals", {}).get(key, 0)
        if not row["usage_known"]:
            unknown_usage.append(run_id)
        rows.append(row)

    hotpotqa.write_jsonl(config.paths["results"] / RUN_INDEX_FILENAME, rows)
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["record_status"]] = status_counts.get(row["record_status"], 0) + 1
    budget = remaining_global_budget(config, batch_dir)
    return {
        "planned_coordinates": len(rows),
        "status_counts": status_counts,
        "completed": status_counts.get(pilot.RUN_COMPLETED, 0),
        "missing": len(rows) - status_counts.get(pilot.RUN_COMPLETED, 0),
        "api": {
            "attempts_in_batch_budget": batch_attempts(batch_dir),
            "attempts_summed_from_runs": attempts_logged,
            "calls_logged_in_runs": calls_logged,
            "cumulative_stage14_attempts": budget["cumulative_attempts"],
            "remaining_global_budget": budget["remaining_global_budget"],
        },
        "usage_totals_known": usage,
        "coordinates_with_unknown_usage": unknown_usage,
        "retrieval_change_after_retry": retrieval_changes,
        "run_index_file": str((config.paths["results"] / RUN_INDEX_FILENAME).relative_to(config.project_root).as_posix()),
        "note": (
            "data collection accounting only; no semantic outcome is assigned here and no "
            "grounding or post-retry label is inferred"
        ),
    }
