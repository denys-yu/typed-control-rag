"""Stage 14 execution audit: persistence, identities, accounting and isolation.

Reads the frozen plan and the executed batch and checks every finished run that
it has not been told to skip. It sends nothing and changes nothing.

    python tools/stage14_audit.py [--limit N] [--write results/stage14_audit_<tag>.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import controller, hotpotqa, main_study, nodes, pilot, rag_run
from typed_rag.config import load_config

import stage14_cli

RESEARCH_KEYS = ("case_id", "condition", "expected_state", "observed_state", "review_status")


def audit(config, batch_dir: Path, limit: int | None = None) -> dict:
    manifest, runs = main_study.load_plan(config)
    by_run = {r["run_id"]: r for r in runs}
    contexts = {c["case_id"]: c for c in main_study.load_contexts(config)}
    gold = main_study.gold_answers(config)
    checkpoint = pilot.read_checkpoint(batch_dir / pilot.CHECKPOINT_FILENAME)

    finished = list(checkpoint["finished"])
    if limit is not None:
        finished = finished[:limit]

    problems: list[str] = []
    calls_seen = 0
    attempts_seen = 0
    usage_known_runs = 0
    models = set()
    store_flags = set()
    branches_seen: dict[str, int] = {}
    node_calls: dict[str, int] = {}

    for run_id in finished:
        planned = by_run.get(run_id)
        if planned is None:
            problems.append(f"{run_id}: not a coordinate of the frozen plan")
            continue
        run_dir = batch_dir / pilot.RUNS_DIRNAME / run_id
        run_path = run_dir / controller.RUN_FILENAME
        context_path = run_dir / rag_run.CONTEXT_FILENAME
        calls_path = run_dir / rag_run.CALLS_FILENAME
        for path in (run_path, context_path, calls_path):
            if not path.is_file():
                problems.append(f"{run_id}: missing {path.name}")
        if not run_path.is_file():
            continue
        result = hotpotqa.read_json(run_path)

        # identities
        if result["question_id"] != planned["question_id"]:
            problems.append(f"{run_id}: question_id differs from the plan")
        if result["branch"] != planned["branch"]:
            problems.append(f"{run_id}: branch differs from the plan")
        if (result.get("initial_context_source") or {}).get("case_id") != planned["case_id"]:
            problems.append(f"{run_id}: case_id differs from the plan")
        if result.get("mode") != main_study.MODE:
            problems.append(f"{run_id}: mode is {result.get('mode')!r}")
        if result.get("index_id") != manifest["binding"]["index"]["index_sha256"]:
            problems.append(f"{run_id}: index identity differs from the plan")
        if (result.get("pilot") or {}).get("repeat") != planned["repeat"]:
            problems.append(f"{run_id}: repeat differs from the plan")
        branches_seen[planned["branch"]] = branches_seen.get(planned["branch"], 0) + 1

        # the initial context is the frozen approved one, in order
        context_record = hotpotqa.read_json(context_path) if context_path.is_file() else {}
        first = (context_record.get("contexts") or [{}])[0]
        expected_ids = [d["doc_id"] for d in contexts[planned["case_id"]]["documents"]]
        if first.get("doc_ids") != expected_ids:
            problems.append(f"{run_id}: initial context documents differ from the approved case")
        if first.get("query_kind") != "injected_initial":
            problems.append(f"{run_id}: the initial context was not the injected one")

        # accounting
        calls = hotpotqa.read_jsonl(calls_path) if calls_path.is_file() else []
        if len(calls) != result["api_calls"]:
            problems.append(f"{run_id}: {len(calls)} logged calls but api_calls={result['api_calls']}")
        calls_seen += result["api_calls"]
        attempts_seen += (result.get("pilot") or {}).get("api_attempts") or 0
        if result.get("usage_totals", {}).get("calls_with_usage"):
            usage_known_runs += 1

        # provider settings and isolation of what was actually sent
        answer = gold.get(planned["question_id"])
        for call in calls:
            node = call.get("node")
            node_calls[node] = node_calls.get(node, 0) + 1
            request = call.get("request") or {}
            if request:
                models.add(request.get("model"))
                store_flags.add(request.get("store"))
                if request.get("previous_response_id") is not None:
                    problems.append(f"{run_id}: a request carried previous_response_id")
                serialized = json.dumps(request, ensure_ascii=False)
                for key in RESEARCH_KEYS:
                    if f'"{key}"' in serialized:
                        problems.append(f"{run_id}: request carries the key {key}")
            raw_dir = run_dir / rag_run.RAW_DIRNAME
            if not raw_dir.is_dir():
                problems.append(f"{run_id}: no raw response directory")
        if answer:
            # Documents the pipeline legitimately saw in this run: the injected initial
            # context and, after a retry, whatever the unchanged index returned. A gold
            # answer inside those texts is ordinary corpus content, not a leak; only the
            # residual - everything except the question and those documents - is checked.
            supplied = [
                document
                for record in (context_record.get("contexts") or [])
                for document in record.get("documents", [])
            ]
            # The rewriter also receives the grader's own assessment (established stage 5
            # design, unchanged from the pilot). That text is model output derived from
            # the documents, so it is stripped too - but only after checking that it is
            # exactly what the model returned in this run, which is what makes it
            # model-generated rather than injected.
            model_texts: list[str] = []
            for step in result.get("trajectory", []):
                sources = [step, step.get("assessment") or {}, step.get("rewrite") or {}]
                for source in sources:
                    for key in ("reason", "state", "sufficient", "rewritten_query", "rewrite_reason"):
                        value = source.get(key)
                        if isinstance(value, str) and value:
                            model_texts.append(value)
            generator = result.get("generator") or {}
            for key in ("answer", "reason"):
                value = (generator.get("result") or {}).get(key)
                if isinstance(value, str) and value:
                    model_texts.append(value)
            for call in calls:
                request = call.get("request") or {}
                if not request:
                    continue
                text = request.get("input", [{}])[0].get("content", [{}])[0].get("text", "")
                residual = text.replace(contexts[planned["case_id"]]["question"], "")
                # Model output first: a document title quoted inside a grader reason would
                # otherwise be removed from it and break the verbatim match.
                carried_model_text = [value for value in model_texts if value in residual]
                for value in carried_model_text:
                    residual = residual.replace(value, "")
                for field in ("text", "title", "doc_id"):
                    for document in supplied:
                        value = document.get(field)
                        if value:
                            residual = residual.replace(value, "")
                if answer in residual:
                    problems.append(
                        f"{run_id}: gold answer appears in a sent user input outside the "
                        f"supplied documents and this run's own model output ({call.get('node')})"
                    )
                elif carried_model_text and call.get("node") not in (
                    nodes.NODE_REWRITE,
                    nodes.NODE_GRADE_BINARY_ACTION,
                    nodes.NODE_GRADE_TYPED_ACTION,
                ):
                    problems.append(
                        f"{run_id}: {call.get('node')} received earlier model output, which its "
                        "node contract forbids"
                    )
                if call.get("node") == nodes.NODE_ANSWER and carried_model_text:
                    problems.append(f"{run_id}: the generator received the grader's own text")

    ledger_attempts = main_study.batch_attempts(batch_dir)
    budget_state = main_study.remaining_global_budget(config, batch_dir)
    report = {
        "stage": "stage14_audit",
        "generated_at_utc": pilot.utc_now(),
        "plan_id": manifest["plan_id"],
        "batch_dir": str(batch_dir),
        "runs_audited": len(finished),
        "problems": problems,
        "problem_count": len(problems),
        "accounting": {
            "attempts_in_batch_budget": ledger_attempts,
            "attempts_summed_from_runs": attempts_seen,
            "calls_logged_in_runs": calls_seen,
            "attempts_at_least_calls": ledger_attempts >= calls_seen,
            "cumulative_stage14_attempts": budget_state["cumulative_attempts"],
            "ledger_agreement": budget_state["agreement"],
            "remaining_global_budget": budget_state["remaining_global_budget"],
        },
        "provider_settings": {
            "models": sorted(m for m in models if m),
            "store_flags": sorted(str(s) for s in store_flags),
            "single_model": len(models) == 1,
        },
        "runs_with_known_usage": usage_known_runs,
        "branches_seen": branches_seen,
        "calls_by_node": node_calls,
    }
    report["passed"] = not problems and report["accounting"]["ledger_agreement"]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 14 execution audit")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--write")
    args = parser.parse_args(argv)
    config = load_config()
    manifest, _ = main_study.load_plan(config)
    batch_dir = stage14_cli.batch_dir_for(manifest["plan_id"])
    report = audit(config, batch_dir, args.limit)
    if args.write:
        hotpotqa.write_json(config.project_root / args.write, report)
    printable = {k: v for k, v in report.items() if k != "problems"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    for problem in report["problems"][:20]:
        print(f"  PROBLEM {problem}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
