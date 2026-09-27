"""Stage 5: the four experimental branches A-D and the control contract.

One pipeline, parameterised by `branch`:

    A - binary grader,  the LLM's proposed action is executed;
    B - typed grader,   the LLM's proposed action is executed;
    C - binary grader,  the action is computed by Python rules;
    D - typed grader,   the action is computed by the programmatic contract.

The grader of every branch returns its verdict *and* a proposed action in one
structured result, so no extra router call is needed. In A/B the proposed
action is executed as is (a deviation from the policy is an observable, not a
bug to correct). In C/D the proposed action is logged and the executed action
is the one the rules return. One technical limit holds for every branch: at
most `controller.max_search_retries` (= 1) retry searches. If A/B propose a
retry after the budget is exhausted, the run ends with status
`budget_exhausted`; the violation is recorded and is not rewritten as abstain.

Four notions are kept apart in the logs and must not be conflated:

* the context assessment  - `sufficient` (binary) or `state` (typed);
* the proposed action     - what the grader LLM recommended;
* the executed action     - what the controller actually did;
* the generator decision  - `answer` / `abstain` returned by the shared
                            generator when the executed action was `answer`.

Mode `stage5_controller_check` is a technical check of the controllers, not
the main experiment. Nothing here reads gold annotations.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from typed_rag import llm, nodes, rag_run, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.llm import Transport
from typed_rag.nodes import (
    ACTION_ABSTAIN,
    ACTION_ANSWER,
    ACTION_ESCALATE,
    ACTION_RETRY,
    ACTIONS,
    STATE_EMPTY,
    STATE_INCONSISTENT,
    STATE_OK,
    STATE_PARTIAL,
)
from typed_rag.retrieval import LoadedIndex

MODE = "stage5_controller_check"
MODE_FAULT = "stage6_fault_check"
MODE_PILOT = "stage7_technical_pilot"

GRADER_BINARY = "binary"
GRADER_TYPED = "typed"
DECIDER_LLM = "llm"
DECIDER_RULES = "rules"


@dataclass(frozen=True)
class Branch:
    name: str
    grader: str  # binary | typed
    decider: str  # llm | rules
    description: str

    @property
    def grader_node(self) -> str:
        return nodes.NODE_GRADE_BINARY_ACTION if self.grader == GRADER_BINARY else nodes.NODE_GRADE_TYPED_ACTION

    @property
    def enforces_policy(self) -> bool:
        return self.decider == DECIDER_RULES


BRANCHES: dict[str, Branch] = {
    "A": Branch("A", GRADER_BINARY, DECIDER_LLM, "binary grade; the action proposed by the LLM is executed"),
    "B": Branch("B", GRADER_TYPED, DECIDER_LLM, "four states; the action proposed by the LLM is executed"),
    "C": Branch("C", GRADER_BINARY, DECIDER_RULES, "binary grade; the action is computed by Python rules"),
    "D": Branch("D", GRADER_TYPED, DECIDER_RULES, "four states; the action is computed by the programmatic contract"),
}

# Final outcomes of a run.
OUTCOME_ANSWERED = "answered"
OUTCOME_GENERATOR_ABSTAINED = "generator_abstained"
OUTCOME_CONTROLLER_ABSTAINED = "controller_abstained"
OUTCOME_ESCALATED = "escalated"
OUTCOME_BUDGET_EXHAUSTED = "budget_exhausted"
OUTCOME_TECHNICAL_FAILURE = "technical_failure"
OUTCOME_INVALID_GRADER_OUTPUT = "invalid_grader_output"
OUTCOME_API_BUDGET_STOPPED = "api_budget_stopped"
OUTCOME_DRY_RUN = "dry_run"

RUN_COMPLETED = "completed"
RUN_BUDGET_EXHAUSTED = "budget_exhausted"  # retry budget of the controller (A/B violation)
RUN_TECHNICAL_FAILURE = "technical_failure"
RUN_API_BUDGET_STOPPED = "api_budget_stopped"  # batch API-call budget (stage 7), nothing sent
RUN_DRY = "dry_run"

RUN_FILENAME = rag_run.RUN_FILENAME
CONTEXT_FILENAME = rag_run.CONTEXT_FILENAME
CALLS_FILENAME = rag_run.CALLS_FILENAME
REQUESTS_FILENAME = rag_run.REQUESTS_FILENAME
RAW_DIRNAME = rag_run.RAW_DIRNAME


class BranchError(Exception):
    """Unknown branch name."""


# --- policy rules (pure functions, no LLM) ---------------------------------------


def expected_action_binary(sufficient: bool, retries_used: int, max_retries: int) -> str:
    """Binary policy shared by A (as instruction) and C (as enforced rule)."""
    if sufficient:
        return ACTION_ANSWER
    if retries_used < max_retries:
        return ACTION_RETRY
    return ACTION_ABSTAIN


def expected_action_typed(state: str, retries_used: int, max_retries: int) -> str:
    """Typed contract shared by B (as instruction) and D (as enforced rule)."""
    if state == STATE_OK:
        return ACTION_ANSWER
    if state == STATE_EMPTY:
        return ACTION_ABSTAIN
    if state == STATE_INCONSISTENT:
        return ACTION_ESCALATE
    if state == STATE_PARTIAL:
        return ACTION_RETRY if retries_used < max_retries else ACTION_ABSTAIN
    raise ValueError(f"Unknown state: {state!r}")


def expected_action(branch: Branch, output: dict, retries_used: int, max_retries: int) -> str:
    if branch.grader == GRADER_BINARY:
        return expected_action_binary(output["sufficient"], retries_used, max_retries)
    return expected_action_typed(output["state"], retries_used, max_retries)


def assessment_of(branch: Branch, output: dict) -> dict:
    """The verdict part of a grader output: {'sufficient': ..} or {'state': ..}."""
    key = "sufficient" if branch.grader == GRADER_BINARY else "state"
    return {key: output[key]}


def rules_table(max_retries: int) -> dict:
    """The transition rules as data, for --show-controller-rules and reports."""
    return {
        "policy_version": None,  # filled by caller from the configuration
        "max_search_retries": max_retries,
        "actions": list(ACTIONS),
        "binary_policy (A: instruction to the LLM, C: enforced by code)": {
            "sufficient=true": ACTION_ANSWER,
            "sufficient=false, retry available": ACTION_RETRY,
            "sufficient=false, retry used": ACTION_ABSTAIN,
            "note": "escalate is never produced by the binary policy; this is part of its definition",
        },
        "typed_policy (B: instruction to the LLM, D: enforced by code)": {
            STATE_OK: ACTION_ANSWER,
            STATE_EMPTY: ACTION_ABSTAIN,
            STATE_INCONSISTENT: ACTION_ESCALATE,
            f"{STATE_PARTIAL}, retry available": ACTION_RETRY,
            f"{STATE_PARTIAL}, retry used": ACTION_ABSTAIN,
        },
        "technical_limit (all branches)": (
            f"at most {max_retries} retry search; a retry proposed by A/B beyond the budget is not "
            "executed, the run ends with status budget_exhausted and the violation is recorded"
        ),
        "execution": {
            "A/B": "executed_action = proposed_action (policy_override is always false)",
            "C/D": "executed_action = expected_action; policy_override = proposed_action != expected_action",
        },
    }


def format_rules(config: ExperimentConfig) -> str:
    table = rules_table(config.controller.max_search_retries)
    table["policy_version"] = config.controller.policy_version
    lines = [f"policy version : {table['policy_version']}", f"max retries    : {table['max_search_retries']}", ""]
    for name, branch in BRANCHES.items():
        lines.append(f"branch {name}: grader={branch.grader:<6} decider={branch.decider:<5} - {branch.description}")
        lines.append(f"          grader node={branch.grader_node}, generator node={nodes.NODE_ANSWER}")
    lines.append("")
    for key in (
        "binary_policy (A: instruction to the LLM, C: enforced by code)",
        "typed_policy (B: instruction to the LLM, D: enforced by code)",
    ):
        lines.append(key)
        for condition, action in table[key].items():
            lines.append(f"  {condition:<38} -> {action}")
    lines.append("")
    lines.append("technical limit : " + table["technical_limit (all branches)"])
    for key, value in table["execution"].items():
        lines.append(f"execution {key:<5} : {value}")
    lines.append("")
    lines.append("retry: rewrite_query node -> search the same index with the rewritten query -> replace the")
    lines.append("       context with the new top_k -> grade again -> apply the branch policy. The generator")
    lines.append("       always answers the original question and never sees branch, verdict or proposed action.")
    return "\n".join(lines)


# --- helpers ---------------------------------------------------------------------


def get_branch(name: str) -> Branch:
    key = (name or "").strip().upper()
    if key not in BRANCHES:
        raise BranchError(f"Unknown branch {name!r}; expected one of {', '.join(BRANCHES)}")
    return BRANCHES[key]


def make_run_id(branch: Branch, position: int, question_id: str, dry_run: bool, case_id: str | None = None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "dry_" if dry_run else ""
    case = f"_case{case_id}" if case_id else ""
    return f"{prefix}{stamp}_{branch.name}_q{position:02d}_{question_id[:8]}{case}_{secrets.token_hex(3)}"


def context_hash(documents: list[dict]) -> str:
    """Identity of a context: the ordered doc_id list (doc_ids are content hashes)."""
    return nodes.sha256_json([document["doc_id"] for document in documents])


def _llm_documents(documents: list[dict]) -> list[dict]:
    return [{"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in documents]


def first_grader_request(config: ExperimentConfig, branch: Branch, question: str, documents: list[dict]) -> dict:
    """The first evaluator request of a run: question, documents, fresh retry budget.

    Shared by the run itself and by the stage 7 batch dry run, so that what a
    dry run shows is exactly what a real run would send first.
    """
    return nodes.build_request_from_text(
        config,
        branch.grader_node,
        nodes.format_grader_input(question, _llm_documents(documents), 0, config.controller.max_search_retries),
    )


def _transport_failure(record: dict) -> tuple[str, str]:
    """Run status and outcome for a call that produced no usable response."""
    if record["transport_status"] == llm.API_BUDGET_STOP:
        return RUN_API_BUDGET_STOPPED, OUTCOME_API_BUDGET_STOPPED
    return RUN_TECHNICAL_FAILURE, OUTCOME_TECHNICAL_FAILURE


def _context_record(iteration: int, query: str, query_kind: str, hits, search_seconds: float, previous: dict | None) -> dict:
    return _context_record_from_documents(
        iteration, query, query_kind, [hit.as_dict() for hit in hits], search_seconds, previous
    )


def _context_record_from_documents(
    iteration: int, query: str, query_kind: str, documents: list[dict], search_seconds: float | None, previous: dict | None
) -> dict:
    record = {
        "iteration": iteration,
        "query": query,
        "query_kind": query_kind,
        "search_seconds": round(search_seconds, 4) if search_seconds is not None else None,
        "context_sha256": context_hash(documents),
        "doc_ids": [d["doc_id"] for d in documents],
        "documents": documents,
    }
    if previous is not None:
        record["same_as_previous"] = record["context_sha256"] == previous["context_sha256"]
        record["overlap_with_previous"] = len(set(record["doc_ids"]) & set(previous["doc_ids"]))
    return record


class _Runner:
    """State of one controlled run; keeps the file writing in one place."""

    def __init__(self, config: ExperimentConfig, branch: Branch, run_id: str, run_dir: Path, transport: Transport | None, mode: str = MODE):
        self.config = config
        self.mode = mode
        self.branch = branch
        self.run_id = run_id
        self.run_dir = run_dir
        self.transport = transport
        self.calls: list[dict] = []
        self.timings: dict[str, float] = {"grader_seconds": 0.0, "rewrite_seconds": 0.0, "generator_seconds": 0.0}

    def call(self, node: str, request: dict, context_doc_ids: list[str], iteration: int) -> dict:
        """One API call, raw response saved before validation, record appended."""
        assert self.transport is not None
        index = len(self.calls) + 1
        raw_dir = self.run_dir / RAW_DIRNAME
        raw_dir.mkdir(parents=True, exist_ok=True)
        # execute_node names the raw file by node; several grader calls per run
        # need distinct names, so a per-call directory is used.
        record = rag_run.execute_node(self.transport, node, request, context_doc_ids, raw_dir / f"{index:02d}_{node}")
        entry = {
            "call_index": index,
            "run_id": self.run_id,
            "mode": self.mode,
            "branch": self.branch.name,
            "iteration": iteration,
            "generation_parameters": rag_run.generation_parameters(self.config),
            "request": request,
            "hashes": nodes.request_hashes(request),
            **record,
        }
        rag_run._append_jsonl(self.run_dir / CALLS_FILENAME, entry)
        self.calls.append(entry)
        bucket = {
            nodes.NODE_GRADE_BINARY_ACTION: "grader_seconds",
            nodes.NODE_GRADE_TYPED_ACTION: "grader_seconds",
            nodes.NODE_REWRITE: "rewrite_seconds",
            nodes.NODE_ANSWER: "generator_seconds",
        }[node]
        self.timings[bucket] = round(self.timings[bucket] + (record["latency_seconds"] or 0.0), 4)
        return entry


# --- the pipeline ----------------------------------------------------------------


def run_controlled(
    config: ExperimentConfig,
    position: int,
    branch_name: str,
    dry_run: bool = False,
    transport: Transport | None = None,
    index: LoadedIndex | None = None,
    model: Any | None = None,
    initial_context: dict | None = None,
    run_id: str | None = None,
    run_dir: Path | None = None,
    mode: str | None = None,
    question: dict | None = None,
) -> dict:
    """Run one branch on one pilot question. At most four API calls, two searches.

    `initial_context` (stage 6) replaces the first retrieval result with a
    prepared context: {"case_id", "question_id", "question", "documents"}.
    It is applied exactly once, before the first grading; a retry searches the
    unchanged index. The dict carries no condition name, expected state or
    gold data, and nothing here reads any.

    `run_id`, `run_dir` and `mode` (stage 7) let a batch place the run under
    its own directory with a stable, plan-derived identifier; every call still
    starts from fresh controller state and a fresh retry budget.

    `question` (stage 14) supplies the question record explicitly, for a study
    whose questions are not the pilot file; omitting it keeps the pilot lookup
    by position unchanged. The question still carries only an id and text, and
    `initial_context` is still checked against it.
    """
    total_started = time.perf_counter()
    created_at = rag_run.utc_now()
    branch = get_branch(branch_name)
    max_retries = config.controller.max_search_retries

    if question is None:
        question = rag_run.pilot_question(config, position)
    case_id = None
    if initial_context is not None:
        if initial_context["question_id"] != question["question_id"] or initial_context["question"] != question["question"]:
            raise ValueError("initial_context does not belong to the question at this position")
        case_id = initial_context["case_id"]
    if mode is None:
        mode = MODE_FAULT if initial_context is not None else MODE
    if run_id is None:
        run_id = make_run_id(branch, position, question["question_id"], dry_run, case_id)
    if run_dir is None:
        run_dir = (config.controlled_dry_runs_dir if dry_run else config.controlled_runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    timings: dict[str, Any] = {}
    started = time.perf_counter()
    if index is None:
        index = retrieval.load_index(config)
    timings["index_load_seconds"] = round(time.perf_counter() - started, 4)
    started = time.perf_counter()
    if model is None:
        model = retrieval.load_model(config)
    timings["model_load_seconds"] = round(time.perf_counter() - started, 4)

    top_k = config.retrieval.top_k
    original = question["question"]

    def search(query: str) -> tuple[list, float]:
        started = time.perf_counter()
        hits = retrieval.search(index, model, query, top_k)
        return hits, time.perf_counter() - started

    if initial_context is None:
        hits, seconds = search(original)
        contexts = [_context_record(1, original, "original", hits, seconds, None)]
        searches_done = 1
    else:
        injected = [
            {"rank": position_ + 1, "doc_id": d["doc_id"], "title": d["title"], "text": d["text"], "score": None}
            for position_, d in enumerate(initial_context["documents"])
        ]
        contexts = [_context_record_from_documents(1, original, "injected_initial", injected, None, None)]
        searches_done = 0

    run: dict = {
        "run_id": run_id,
        "mode": mode,
        "initial_context_source": {"kind": "fault_case", "case_id": case_id} if case_id else {"kind": "retrieval"},
        "branch": branch.name,
        "branch_definition": {
            "grader": branch.grader,
            "decider": branch.decider,
            "grader_node": branch.grader_node,
            "generator_node": nodes.NODE_ANSWER,
            "rewrite_node": nodes.NODE_REWRITE,
            "description": branch.description,
        },
        "policy_version": config.controller.policy_version,
        "max_search_retries": max_retries,
        "dry_run": dry_run,
        "created_at_utc": created_at,
        "question_index": position,
        "question_id": question["question_id"],
        "question": original,
        "index_id": index.index_id,
        "top_k": top_k,
        "llm": {
            "provider": config.llm.provider,
            "api": config.llm.api,
            "model_requested": config.llm.model,
            "sdk_version": llm.sdk_version(),
            "generation_parameters": rag_run.generation_parameters(config),
            "structured_outputs": "json_schema, strict=true",
        },
        "timing_scope": {
            **{k: v for k, v in rag_run.TIMING_SCOPE.items() if k in ("index_load_seconds", "model_load_seconds")},
            "search_seconds": "per search, in context.json: query embedding + matrix product + ranking",
            "grader_seconds": "sum of wall clock around grader HTTP calls (1 or 2 calls)",
            "rewrite_seconds": "wall clock around the rewrite HTTP call, 0 if none",
            "generator_seconds": "wall clock around the generator HTTP call, 0 if none",
            "total_seconds": "from entering run_controlled to assembling run.json",
        },
    }

    def write_context() -> None:
        rag_run._write_json(
            run_dir / CONTEXT_FILENAME,
            {
                "run_id": run_id,
                "mode": mode,
                "initial_context_source": run["initial_context_source"],
                "branch": branch.name,
                "question_index": position,
                "question_id": question["question_id"],
                "question": original,
                "index_id": index.index_id,
                "embedding_model": index.manifest["model_name"],
                "embedding_model_revision": index.manifest["model_revision"],
                "corpus_document_count": index.size,
                "top_k": top_k,
                "searches": searches_done + len(contexts) - 1,
                "contexts": contexts,
                "note": "scores are logged here only; LLM nodes receive doc_id, title and full text",
            },
        )

    write_context()

    first_request = first_grader_request(config, branch, original, contexts[0]["documents"])

    if dry_run:
        rag_run._write_json(
            run_dir / REQUESTS_FILENAME,
            {
                "run_id": run_id,
                "branch": branch.name,
                "first_grader_request": first_request,
                "hashes": nodes.request_hashes(first_request),
                "note": "only the first grader request can be prepared; the rest of the trajectory depends on the LLM response",
            },
        )
        timings["total_seconds"] = round(time.perf_counter() - total_started, 4)
        run.update(
            {
                "status": RUN_DRY,
                "final_outcome": OUTCOME_DRY_RUN,
                "api_calls": 0,
                "searches": searches_done,
                "retries_used": 0,
                "trajectory": [],
                "usage_totals": rag_run._usage_totals([]),
                "timings": timings,
                "run_dir": str(run_dir),
                "note": "dry run: initial search done, first grader request saved; no client, no network",
            }
        )
        rag_run._write_json(run_dir / RUN_FILENAME, run)
        return run

    if transport is None:
        transport = rag_run.default_transport(config)
    runner = _Runner(config, branch, run_id, run_dir, transport, mode)

    trajectory: list[dict] = []
    retries_used = 0
    iteration = 1
    status = RUN_COMPLETED
    outcome: str | None = None
    generator: dict = {"status": "not_run"}
    escalation: dict | None = None
    failure: dict | None = None
    request = first_request

    while True:
        current = contexts[-1]
        doc_ids = current["doc_ids"]
        grade = runner.call(branch.grader_node, request, doc_ids, iteration)
        step: dict = {
            "iteration": iteration,
            "context_sha256": current["context_sha256"],
            "context_doc_ids": doc_ids,
            "retries_used_before": retries_used,
            "retries_remaining_before": max_retries - retries_used,
            "grader_node": branch.grader_node,
            "grader_call_index": grade["call_index"],
            "grader_status": grade["node_status"],
            "grader_validation": grade["validation"],
        }
        if grade["transport_status"] != llm.TRANSPORT_OK:
            step.update({"assessment": None, "proposed_action": None, "expected_action": None, "executed_action": None})
            trajectory.append(step)
            status, outcome = _transport_failure(grade)
            failure = {"stage": "grader", "iteration": iteration, "error": grade["error"]}
            break
        output = grade["output"]
        if output is None:
            # JSON or schema error: no usable verdict or action. This is a
            # technical outcome, not an abstention.
            step.update({"assessment": None, "proposed_action": None, "expected_action": None, "executed_action": None})
            trajectory.append(step)
            status, outcome = RUN_TECHNICAL_FAILURE, OUTCOME_INVALID_GRADER_OUTPUT
            failure = {"stage": "grader", "iteration": iteration, "validation": grade["validation"]}
            break

        assessment = assessment_of(branch, output)
        proposed = output["proposed_action"]
        expected = expected_action(branch, output, retries_used, max_retries)
        if branch.enforces_policy:
            executed = expected
        else:
            executed = proposed
        mismatch = proposed != expected
        step.update(
            {
                "assessment": assessment,
                "reason": output["reason"],
                "evidence_doc_ids": output["evidence_doc_ids"],
                "proposed_action": proposed,
                "expected_action": expected,
                "executed_action": executed,
                "policy_mismatch": mismatch,
                "policy_override": branch.enforces_policy and mismatch,
                "budget_violation": False,
            }
        )

        if executed == ACTION_RETRY and retries_used >= max_retries:
            # Only reachable in A/B: the rules never return retry here.
            step["executed_action"] = None
            step["budget_violation"] = True
            trajectory.append(step)
            status, outcome = RUN_BUDGET_EXHAUSTED, OUTCOME_BUDGET_EXHAUSTED
            break
        trajectory.append(step)

        if executed == ACTION_ANSWER:
            answer_request = nodes.build_request(config, nodes.NODE_ANSWER, original, _llm_documents(current["documents"]))
            answer = runner.call(nodes.NODE_ANSWER, answer_request, doc_ids, iteration)
            generator = rag_run._node_summary(answer, nodes.NODE_ANSWER)
            generator["call_index"] = answer["call_index"]
            if answer["transport_status"] != llm.TRANSPORT_OK:
                status, outcome = _transport_failure(answer)
                failure = {"stage": "generator", "iteration": iteration, "error": answer["error"]}
            elif answer["output"] is None:
                status, outcome = RUN_TECHNICAL_FAILURE, OUTCOME_TECHNICAL_FAILURE
                failure = {"stage": "generator", "iteration": iteration, "validation": answer["validation"]}
            elif answer["output"]["decision"] == nodes.DECISION_ABSTAIN:
                outcome = OUTCOME_GENERATOR_ABSTAINED
            else:
                outcome = OUTCOME_ANSWERED
            break

        if executed == ACTION_ABSTAIN:
            outcome = OUTCOME_CONTROLLER_ABSTAINED
            break

        if executed == ACTION_ESCALATE:
            escalation = {
                "requested_at_utc": rag_run.utc_now(),
                "iteration": iteration,
                "assessment": assessment,
                "reason": output["reason"],
                "evidence_doc_ids": output["evidence_doc_ids"],
                "note": "external review requested; no automatic answer produced, no external service contacted",
            }
            outcome = OUTCOME_ESCALATED
            break

        # executed == retry, budget available
        retries_used += 1
        rewrite_request = nodes.build_request_from_text(
            config,
            nodes.NODE_REWRITE,
            nodes.format_rewrite_input(
                original, _llm_documents(current["documents"]), {**assessment, "reason": output["reason"]}
            ),
        )
        rewrite = runner.call(nodes.NODE_REWRITE, rewrite_request, doc_ids, iteration)
        step["rewrite_call_index"] = rewrite["call_index"]
        step["rewrite_status"] = rewrite["node_status"]
        if rewrite["transport_status"] != llm.TRANSPORT_OK or rewrite["output"] is None or not rewrite["output"]["rewritten_query"].strip():
            status, outcome = _transport_failure(rewrite)
            failure = {"stage": "rewrite", "iteration": iteration, "error": rewrite["error"], "validation": rewrite["validation"]}
            break
        rewritten = rewrite["output"]["rewritten_query"].strip()
        step["rewritten_query"] = rewritten
        hits, seconds = search(rewritten)
        iteration += 1
        contexts.append(_context_record(iteration, rewritten, "rewritten", hits, seconds, contexts[-1]))
        write_context()
        request = nodes.build_request_from_text(
            config,
            branch.grader_node,
            nodes.format_grader_input(original, _llm_documents(contexts[-1]["documents"]), retries_used, max_retries),
        )

    validation_issues = [
        {"call_index": c["call_index"], "node": c["node"], "status": c["node_status"], "errors": (c["validation"] or {}).get("errors", [])}
        for c in runner.calls
        if c["transport_status"] == llm.TRANSPORT_OK and c["node_status"] != rag_run.NODE_OK
    ]
    timings.update(runner.timings)
    timings["total_seconds"] = round(time.perf_counter() - total_started, 4)
    run.update(
        {
            "status": status,
            "final_outcome": outcome,
            "api_calls": len(runner.calls),
            "searches": searches_done + len(contexts) - 1,
            "retries_used": retries_used,
            "trajectory": trajectory,
            "proposed_actions": [s["proposed_action"] for s in trajectory],
            "expected_actions": [s["expected_action"] for s in trajectory],
            "executed_actions": [s["executed_action"] for s in trajectory],
            "any_policy_mismatch": any(s.get("policy_mismatch") for s in trajectory),
            "any_policy_override": any(s.get("policy_override") for s in trajectory),
            "generator": generator,
            "escalation": escalation,
            "failure": failure,
            "validation_issues": validation_issues,
            "usage_totals": rag_run._usage_totals(runner.calls),
            "timings": timings,
            "run_dir": str(run_dir),
            "note": (
                f"{mode}: "
                + (
                    "technical pilot on a reviewed initial context, not a confirmatory study; "
                    if mode == MODE_PILOT
                    else "technical check of the controllers, not the main experiment; "
                )
                + "the generator never sees branch, verdict or proposed action."
            ),
        }
    )
    rag_run._write_json(run_dir / RUN_FILENAME, run)
    return run


def format_controlled_run(run: dict) -> str:
    lines = [
        f"run id        : {run['run_id']}",
        f"mode          : {run['mode']} (dry run: {run['dry_run']})",
        f"branch        : {run['branch']} - {run['branch_definition']['description']}",
        f"policy        : {run['policy_version']}, max retries {run['max_search_retries']}",
        f"question      : [{run['question_index']}] {run['question']}",
        f"model         : {run['llm']['model_requested']}",
        f"status        : {run['status']} / outcome: {run['final_outcome']}",
        f"searches      : {run['searches']}, api calls: {run['api_calls']}, retries used: {run['retries_used']}",
    ]
    for step in run.get("trajectory", []):
        lines.append(
            f"iteration {step['iteration']}   : assessment={step.get('assessment')} proposed={step.get('proposed_action')} "
            f"expected={step.get('expected_action')} executed={step.get('executed_action')} "
            f"mismatch={step.get('policy_mismatch')} override={step.get('policy_override')}"
        )
        if step.get("reason"):
            lines.append(f"    reason           : {step['reason']}")
        if step.get("rewritten_query"):
            lines.append(f"    rewritten query  : {step['rewritten_query']}")
        if step.get("budget_violation"):
            lines.append("    budget violation : retry proposed after the budget was exhausted; not executed")
    if run.get("generator", {}).get("output"):
        out = run["generator"]["output"]
        lines.append(f"generator     : decision={out['decision']} answer={out['answer']!r}")
        lines.append(f"    reason           : {out['reason']}")
    elif run.get("generator"):
        lines.append(f"generator     : {run['generator'].get('status')}")
    if run.get("escalation"):
        lines.append("escalation    : external review requested (no automatic answer)")
    if run.get("failure"):
        lines.append(f"failure       : {run['failure']}")
    usage = run["usage_totals"]
    lines.append(
        f"usage         : input={usage['input_tokens']} output={usage['output_tokens']} "
        f"total={usage['total_tokens']} cached={usage['cached_tokens']}"
    )
    lines.append("timings (s)   : " + ", ".join(f"{k.removesuffix('_seconds')}={v}" for k, v in run["timings"].items()))
    lines.append(f"run dir       : {run['run_dir']}")
    return "\n".join(lines)
