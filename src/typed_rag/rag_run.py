"""Stage 4 diagnostic RAG run: retrieval, then two independent LLM nodes.

Mode `stage4_diagnostic` is a technical check of the integration, not one of
the experimental branches A-D. Both nodes run on the same retrieved context;
the grader's verdict is only logged and does not decide whether the generator
runs. The generator never sees the grader's output.

The only situation in which the generator is skipped is a technical failure
of the grader call (API error, provider refusal, incomplete or failed
response). That is incomplete-run handling, not a routing policy. A grader
response that arrived but failed local validation still lets the generator run,
because the two nodes are independent and the invalid output is kept for
analysis.

Every real run writes results/rag_runs/<run_id>/ with run.json, context.json,
calls.jsonl and the raw responses. Dry runs write results/rag_dry_runs/<run_id>/
with the prepared requests and no API traffic at all.
"""

from __future__ import annotations

import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from typed_rag import hotpotqa, llm, nodes, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.hotpotqa import DatasetError
from typed_rag.llm import Transport
from typed_rag.retrieval import LoadedIndex

MODE = "stage4_diagnostic"

RUN_FILENAME = "run.json"
CONTEXT_FILENAME = "context.json"
CALLS_FILENAME = "calls.jsonl"
REQUESTS_FILENAME = "requests.json"
RAW_DIRNAME = "raw"

# Node status values beyond the transport / validation labels.
NODE_OK = "ok"
NODE_SKIPPED = "skipped_after_grader_failure"
NODE_NOT_RUN = "not_run_dry_run"

RUN_COMPLETED = "completed"
RUN_INVALID_OUTPUT = "completed_with_invalid_output"
RUN_TECHNICAL_FAILURE = "technical_failure"
RUN_DRY = "dry_run"

TIMING_SCOPE = {
    "index_load_seconds": "reading the stored matrix, documents and manifest from disk",
    "model_load_seconds": "loading the embedding model from the local cache (first use only)",
    "search_seconds": "query embedding + matrix product + ranking (time.perf_counter, CPU)",
    "grade_seconds": "wall clock around the grader HTTP call: serialisation, network, "
    "response parsing; excludes client creation and local validation",
    "answer_seconds": "same as grade_seconds, for the generator call",
    "total_seconds": "from entering run_example to the moment run.json is assembled; "
    "includes index/model loading, search, both calls, validation and file writes",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_run_id(position: int, question_id: str, dry_run: bool) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "dry_" if dry_run else ""
    return f"{prefix}{stamp}_q{position:02d}_{question_id[:8]}_{secrets.token_hex(3)}"


def pilot_question(config: ExperimentConfig, position: int) -> dict:
    """One pilot question by position; the questions file carries no gold data."""
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    if not 0 <= position < len(questions):
        raise DatasetError(f"Pilot index {position} out of range (0..{len(questions) - 1})")
    return questions[position]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def generation_parameters(config: ExperimentConfig) -> dict:
    return {
        "temperature": config.llm.temperature,
        "max_output_tokens": config.llm.max_output_tokens,
        "store": config.llm.store,
        "timeout_seconds": config.llm.timeout_seconds,
        "max_retries": config.llm.max_retries,
        "stream": False,
        "tools": None,
        "previous_response_id": None,
    }


def default_transport(config: ExperimentConfig) -> Transport:
    """Real transport: requires a non-empty key, otherwise no client is created."""
    api_key, _source = llm.resolve_api_key(config)
    if not api_key:
        raise llm.MissingAPIKeyError(
            f"No {config.llm.api_key_env} found in the environment or in "
            f"{config.env_file_path.name}. Set it and rerun; use --dry-run to proceed without it."
        )
    return llm.OpenAIResponsesTransport(llm.create_client(config, api_key))


def execute_node(
    transport: Transport,
    node: str,
    request: dict,
    context_doc_ids: list[str],
    raw_dir: Path,
) -> dict:
    """One API call followed by local validation; the raw response is saved first."""
    call = llm.call(transport, request)
    response = call["response"]

    # Keep whatever came back before validating it, so that an invalid result
    # is still available for analysis.
    raw_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        raw_dir / f"{node}_response.json",
        {
            "node": node,
            "started_at_utc": call["started_at_utc"],
            "transport_status": call["transport_status"],
            "error": call["error"],
            "output_text": response["output_text"] if response else None,
            "raw_response": response["raw_response"] if response else None,
        },
    )

    validation = None
    output = None
    if call["transport_status"] == llm.TRANSPORT_OK:
        result = nodes.validate_output(node, response["output_text"], context_doc_ids)
        validation = result.as_dict()
        output = result.output
        node_status = NODE_OK if result.ok else result.status
    else:
        node_status = call["transport_status"]

    return {
        "node": node,
        "started_at_utc": call["started_at_utc"],
        "latency_seconds": call["latency_seconds"],
        "model_requested": request["model"],
        "model_returned": response["model_returned"] if response else None,
        "response_id": response["response_id"] if response else None,
        "request_id": response["request_id"] if response else None,
        "response_status": response["status"] if response else None,
        "incomplete_reason": response["incomplete_reason"] if response else None,
        "output_text": response["output_text"] if response else None,
        "refusal": response["refusal"] if response else None,
        "usage": response["usage"] if response else None,
        "transport_status": call["transport_status"],
        "error": call["error"],
        "validation": validation,
        "output": output,
        "node_status": node_status,
    }


def _usage_totals(calls: list[dict]) -> dict:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0}
    known = 0
    for call in calls:
        usage = call.get("usage")
        if not usage:
            continue
        known += 1
        totals["input_tokens"] += usage.get("input_tokens") or 0
        totals["output_tokens"] += usage.get("output_tokens") or 0
        totals["total_tokens"] += usage.get("total_tokens") or 0
        details = usage.get("input_tokens_details") or {}
        totals["cached_tokens"] += details.get("cached_tokens") or 0
    totals["calls_with_usage"] = known
    return totals


def _node_summary(record: dict | None, node: str) -> dict:
    if record is None:
        return {"status": NODE_NOT_RUN}
    summary = {
        "status": record["node_status"],
        "transport_status": record["transport_status"],
        "validation": record["validation"],
        "latency_seconds": record["latency_seconds"],
    }
    output = record.get("output")
    if output is not None:
        summary["output"] = output
    if record.get("error"):
        summary["error"] = record["error"]
    return summary


def run_example(
    config: ExperimentConfig,
    position: int,
    dry_run: bool = False,
    transport: Transport | None = None,
    index: LoadedIndex | None = None,
    model: Any | None = None,
) -> dict:
    """Run the diagnostic pipeline on one pilot question. At most two API calls."""
    total_started = time.perf_counter()
    created_at = utc_now()

    question = pilot_question(config, position)
    run_id = make_run_id(position, question["question_id"], dry_run)
    run_dir = (config.rag_dry_runs_dir if dry_run else config.rag_runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    timings: dict[str, float | None] = {}
    started = time.perf_counter()
    if index is None:
        index = retrieval.load_index(config)
    timings["index_load_seconds"] = round(time.perf_counter() - started, 4)

    started = time.perf_counter()
    if model is None:
        model = retrieval.load_model(config)
    timings["model_load_seconds"] = round(time.perf_counter() - started, 4)

    top_k = config.retrieval.top_k
    started = time.perf_counter()
    hits = retrieval.search(index, model, question["question"], top_k)
    timings["search_seconds"] = round(time.perf_counter() - started, 4)

    documents = [hit.as_dict() for hit in hits]
    context_doc_ids = [document["doc_id"] for document in documents]
    _write_json(
        run_dir / CONTEXT_FILENAME,
        {
            "run_id": run_id,
            "mode": MODE,
            "question_index": position,
            "question_id": question["question_id"],
            "question": question["question"],
            "index_id": index.index_id,
            "embedding_model": index.manifest["model_name"],
            "embedding_model_revision": index.manifest["model_revision"],
            "corpus_document_count": index.size,
            "top_k": top_k,
            "search_seconds": timings["search_seconds"],
            "documents": documents,
            "note": "scores are logged here only; the LLM nodes receive doc_id, title and full text",
        },
    )

    # Both nodes receive the same question and the same documents, and the
    # generator's request is built without any knowledge of the grader's result.
    llm_documents = [
        {"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in documents
    ]
    requests = {
        node: nodes.build_request(config, node, question["question"], llm_documents)
        for node in nodes.NODE_NAMES
    }
    hashes = {node: nodes.request_hashes(requests[node]) for node in nodes.NODE_NAMES}

    run: dict = {
        "run_id": run_id,
        "mode": MODE,
        "dry_run": dry_run,
        "created_at_utc": created_at,
        "question_index": position,
        "question_id": question["question_id"],
        "question": question["question"],
        "index_id": index.index_id,
        "top_k": top_k,
        "retrieved_doc_ids": context_doc_ids,
        "llm": {
            "provider": config.llm.provider,
            "api": config.llm.api,
            "model_requested": config.llm.model,
            "sdk_version": llm.sdk_version(),
            "generation_parameters": generation_parameters(config),
            "structured_outputs": "json_schema, strict=true",
        },
        "request_hashes": hashes,
        "timing_scope": TIMING_SCOPE,
    }

    if dry_run:
        _write_json(
            run_dir / REQUESTS_FILENAME,
            {"run_id": run_id, "requests": requests, "hashes": hashes},
        )
        timings.update({"grade_seconds": None, "answer_seconds": None})
        timings["total_seconds"] = round(time.perf_counter() - total_started, 4)
        run.update(
            {
                "status": RUN_DRY,
                "api_calls": 0,
                "usage_totals": _usage_totals([]),
                "grader": {"status": NODE_NOT_RUN},
                "generator": {"status": NODE_NOT_RUN},
                "timings": timings,
                "run_dir": str(run_dir),
                "note": "dry run: requests prepared and saved; no client created, no network traffic",
            }
        )
        _write_json(run_dir / RUN_FILENAME, run)
        return run

    if transport is None:
        transport = default_transport(config)

    calls_path = run_dir / CALLS_FILENAME
    raw_dir = run_dir / RAW_DIRNAME
    records: list[dict] = []
    common = {
        "run_id": run_id,
        "mode": MODE,
        "generation_parameters": generation_parameters(config),
    }

    grade_record = execute_node(
        transport, nodes.NODE_GRADE, requests[nodes.NODE_GRADE], context_doc_ids, raw_dir
    )
    _append_jsonl(
        calls_path,
        {
            "call_index": 1,
            **common,
            "request": requests[nodes.NODE_GRADE],
            "hashes": hashes[nodes.NODE_GRADE],
            **grade_record,
        },
    )
    records.append(grade_record)
    timings["grade_seconds"] = grade_record["latency_seconds"]

    answer_record: dict | None = None
    if grade_record["transport_status"] == llm.TRANSPORT_OK:
        answer_record = execute_node(
            transport, nodes.NODE_ANSWER, requests[nodes.NODE_ANSWER], context_doc_ids, raw_dir
        )
        _append_jsonl(
            calls_path,
            {
                "call_index": 2,
                **common,
                "request": requests[nodes.NODE_ANSWER],
                "hashes": hashes[nodes.NODE_ANSWER],
                **answer_record,
            },
        )
        records.append(answer_record)
        timings["answer_seconds"] = answer_record["latency_seconds"]
        generator = _node_summary(answer_record, nodes.NODE_ANSWER)
    else:
        timings["answer_seconds"] = None
        generator = {"status": NODE_SKIPPED, "reason": grade_record["transport_status"]}

    transport_ok = all(r["transport_status"] == llm.TRANSPORT_OK for r in records)
    if not transport_ok or answer_record is None:
        status = RUN_TECHNICAL_FAILURE
    elif all(r["node_status"] == NODE_OK for r in records):
        status = RUN_COMPLETED
    else:
        status = RUN_INVALID_OUTPUT

    timings["total_seconds"] = round(time.perf_counter() - total_started, 4)
    run.update(
        {
            "status": status,
            "api_calls": len(records),
            "usage_totals": _usage_totals(records),
            "grader": _node_summary(grade_record, nodes.NODE_GRADE),
            "generator": generator,
            "timings": timings,
            "run_dir": str(run_dir),
            "note": (
                "stage4_diagnostic: the grader verdict is logged only and does not gate "
                "the generator; the generator never sees the grader output"
            ),
        }
    )
    _write_json(run_dir / RUN_FILENAME, run)
    return run


def format_run(run: dict) -> str:
    """Human-readable summary for the console."""
    lines = [
        f"run id        : {run['run_id']}",
        f"mode          : {run['mode']} (dry run: {run['dry_run']})",
        f"question      : [{run['question_index']}] {run['question']}",
        f"index id      : {run['index_id'][:16]}  top_k={run['top_k']}",
        f"model         : {run['llm']['model_requested']}",
        f"status        : {run['status']}",
        f"api calls     : {run['api_calls']}",
    ]
    for label in ("grader", "generator"):
        node = run[label]
        lines.append(f"{label:<14}: {node['status']}")
        output = node.get("output")
        if output:
            for key, value in output.items():
                if key == "evidence_doc_ids":
                    value = [doc_id[:12] for doc_id in value]
                lines.append(f"    {key:<17}: {value}")
        if node.get("validation") and node["validation"]["errors"]:
            for error in node["validation"]["errors"]:
                lines.append(f"    validation error : {error}")
        if node.get("error"):
            lines.append(f"    error            : {node['error'].get('kind')}: {node['error'].get('message')}")
    usage = run["usage_totals"]
    lines.append(
        f"usage         : input={usage['input_tokens']} output={usage['output_tokens']} "
        f"total={usage['total_tokens']} cached={usage['cached_tokens']}"
    )
    timings = run["timings"]
    lines.append(
        "timings (s)   : "
        + ", ".join(f"{key.removesuffix('_seconds')}={value}" for key, value in timings.items())
    )
    lines.append(f"run dir       : {run['run_dir']}")
    return "\n".join(lines)


def format_llm_config_check(config: ExperimentConfig) -> tuple[str, bool]:
    """Local checks only: settings, SDK, prompts, schemas, key presence. No API call."""
    problems: list[str] = []
    version = llm.sdk_version()
    if version is None:
        problems.append("openai SDK is not installed")

    prompt_lines = []
    for node in nodes.ALL_NODE_NAMES:
        path = nodes.prompt_path(config, node)
        try:
            text = nodes.load_prompt(config, node)
        except (FileNotFoundError, ValueError) as exc:
            problems.append(str(exc))
            prompt_lines.append(f"prompt {node:<13}: MISSING ({path})")
            continue
        prompt_lines.append(f"prompt {node:<13}: {path.name} sha256={nodes.sha256_text(text)[:16]}")
        prompt_lines.append(
            f"schema {node:<13}: {nodes.NODE_SPECS[node].schema_name} "
            f"sha256={nodes.sha256_json(nodes.json_schema(node))[:16]}"
        )

    key = llm.api_key_status(config)
    if key["status"] != llm.KEY_CONFIGURED:
        problems.append(f"{config.llm.api_key_env} is missing (environment or {config.llm.env_filename})")
    ignored = llm.env_file_is_ignored(config)
    if not ignored:
        problems.append(f"{config.llm.env_filename} is not listed in .gitignore")

    lines = [
        f"provider      : {config.llm.provider} / {config.llm.api} API",
        f"model         : {config.llm.model}",
        f"temperature   : {config.llm.temperature}",
        f"max out tokens: {config.llm.max_output_tokens}",
        f"timeout       : {config.llm.timeout_seconds}s, max_retries={config.llm.max_retries}, "
        f"store={config.llm.store}",
        f"openai sdk    : {version or 'not installed'}",
        *prompt_lines,
        f"api key       : {key['status']}" + (f" (source: {key['source']})" if key["source"] else ""),
        f".env ignored  : {ignored}",
        f"runs dir      : {config.rag_runs_dir}",
    ]
    if problems:
        lines.append("llm config check: PROBLEMS")
        lines.extend(f"  - {problem}" for problem in problems)
    else:
        lines.append("llm config check: OK (no API call made)")
    return "\n".join(lines), not problems
