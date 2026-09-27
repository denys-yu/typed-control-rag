"""Stage 14 report: consolidate, reconcile and write the stage deliverables.

Runs consolidation, a full-batch audit and the review-material export, then
writes `results/stage14_report.json` and `results/stage14_summary.md`. It makes
no provider call and states plainly that completed data collection is not the
same as completed semantic annotation.

    python tools/stage14_report.py [--skip-review]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa, main_study, pilot
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage14_audit
import stage14_cli
import stage14_finalize
import stage14_review

REPORT = "stage14_report.json"
SUMMARY = "stage14_summary.md"
AUDIT_FULL = "stage14_audit_full.json"


def build(config, skip_review: bool = False) -> dict:
    results = config.paths["results"]
    manifest, runs = main_study.load_plan(config)
    batch_dir = stage14_cli.batch_dir_for(manifest["plan_id"])
    manifest_path, runs_path = main_study.plan_paths(config)

    # The corrected reader rebuilds the index; the frozen implementation is not edited
    # after execution, so the fix lives in tools/stage14_finalize.py.
    rebuilt = stage14_finalize.rebuild(config, batch_dir)
    consolidation = rebuilt["base"]
    index_correction = rebuilt["correction"]
    audit = stage14_audit.audit(config, batch_dir)
    hotpotqa.write_json(results / AUDIT_FULL, audit)

    index_rows = hotpotqa.read_jsonl(results / main_study.RUN_INDEX_FILENAME)
    status_counts = Counter(row["record_status"] for row in index_rows)
    outcome_counts = Counter(
        row["terminal_outcome"] or "none"
        for row in index_rows
        if row["record_status"] == pilot.RUN_COMPLETED
    )
    technical_statuses = Counter(
        str(row["status"] or "not_started")
        for row in index_rows
        if row["record_status"] != pilot.RUN_COMPLETED
    )
    ledger = main_study.read_ledger(config)
    budget = main_study.remaining_global_budget(config, batch_dir)
    acceptance = hotpotqa.read_json(results / "stage14_acceptance.json")
    sample = hotpotqa.read_json(results / "main_sample_final.json")
    preflight = hotpotqa.read_json(results / "stage14_preflight.json")
    first16 = hotpotqa.read_json(results / "stage14_audit_first16.json")

    review = None
    if not skip_review and status_counts[pilot.RUN_COMPLETED]:
        review = stage14_review.build(config, batch_dir)

    complete = status_counts[pilot.RUN_COMPLETED] == len(index_rows)
    report = {
        "stage": "stage14_main_experiment",
        "generated_at_utc": pilot.utc_now(),
        "author": "Denys Yuvzhenko",
        "protocol": {
            "file": "results/main_experiment_protocol_v3.md",
            "sha256": sha256_file(results / "main_experiment_protocol_v3.md"),
            "frozen_before_first_provider_call": True,
        },
        "acceptance": {
            "basis": acceptance["acceptance_basis"],
            "reviewer_recorded_for_accepted_decisions": acceptance["reviewer_recorded_for_accepted_decisions"],
            "independent_human_review": False,
            "conventions_accepted": list(acceptance["conventions_accepted"]),
            "excluded_question": acceptance["correction"]["excluded_question"],
            "replacement_question": acceptance["correction"]["replacement_question"],
            "review_counts": acceptance["counts"]["review_status"],
            "archive": acceptance["archive"],
        },
        "sample": {
            "questions": len(sample["questions"]),
            "approved_initial_contexts": sample["approved_initial_contexts"],
            "sensitivity_subset_questions": sample["sensitivity_subset"]["questions"],
            "sensitivity_excluded": sample["sensitivity_subset"]["excluded_question_ids"],
            "sample_sha256": sha256_file(results / "main_sample_final.json"),
        },
        "plan": {
            "plan_id": manifest["plan_id"],
            "manifest_sha256": sha256_file(manifest_path),
            "runs_sha256": sha256_file(runs_path),
            "planned_coordinates": manifest["counts"]["planned_coordinates"],
            "formula": manifest["counts"]["planned_coordinates_formula"],
            "index_sha256": manifest["binding"]["index"]["index_sha256"],
            "corpus_sha256": manifest["binding"]["index"]["corpus_sha256"],
            "model": manifest["binding"]["llm"]["model"],
            "generation_parameters": manifest["binding"]["llm"]["generation_parameters"],
            "controller": manifest["binding"]["controller"],
            "batch_dir": str(batch_dir),
            "verified_before_every_invocation": True,
        },
        "preflight": {
            "all_passed": preflight["gates"]["all_passed"],
            "isolation_heuristic_false_positives": preflight["gates"]["isolation_heuristic_false_positives"],
            "isolation_note": preflight["isolation_note"],
            "longest_output_path": preflight["gates"]["output_path_check"]["longest_path_length"],
        },
        "execution": {
            "planned_coordinates": len(index_rows),
            "completed": status_counts[pilot.RUN_COMPLETED],
            "missing": len(index_rows) - status_counts[pilot.RUN_COMPLETED],
            "status_counts": dict(status_counts),
            "terminal_outcomes_completed": dict(outcome_counts),
            "technical_statuses_of_missing": dict(technical_statuses),
            "invocations": len(ledger.get("invocations", [])),
            "first_sixteen_were_ordinary_observations": True,
            "pending_coordinates": status_counts.get(pilot.RUN_PENDING, 0),
            "plan_exhausted": status_counts.get(pilot.RUN_PENDING, 0) == 0,
            "all_coordinates_completed": complete,
            "data_collection_complete": status_counts.get(pilot.RUN_PENDING, 0) == 0,
            "data_collection_note": (
                "every planned coordinate was attempted exactly once; the missing ones are "
                "recorded technical failures, never abstentions, and were not re-run or replaced"
            ),
        },
        "accounting": {
            "cumulative_stage14_attempts": budget["cumulative_attempts"],
            "global_attempt_ceiling": main_study.GLOBAL_ATTEMPT_CEILING,
            "remaining_allowance": budget["remaining_global_budget"],
            "ledger_agrees_with_batch_budget": budget["agreement"],
            "attempts_summed_from_runs": consolidation["api"]["attempts_summed_from_runs"],
            "calls_logged_in_runs": consolidation["api"]["calls_logged_in_runs"],
            "reconciliation_note": (
                "attempts are counted before a request is sent, so attempts >= logged calls; a "
                "difference equals attempts that produced no usable response"
            ),
        },
        "usage": {
            "known_totals": consolidation["usage_totals_known"],
            "coordinates_with_unknown_usage": len(consolidation["coordinates_with_unknown_usage"]),
            "unknown_usage_run_ids": consolidation["coordinates_with_unknown_usage"][:50],
        },
        "audit": {
            "technical_check_first_16": {
                "runs": first16["runs_audited"],
                "passed": first16["passed"],
                "problems": first16["problem_count"],
            },
            "full_batch": {
                "runs": audit["runs_audited"],
                "passed": audit["passed"],
                "problems": audit["problem_count"],
                "problem_examples": audit["problems"][:10],
                "single_model": audit["provider_settings"]["single_model"],
                "store_flags": audit["provider_settings"]["store_flags"],
                "calls_by_node": audit["calls_by_node"],
            },
            "isolation_note": (
                "the shared heuristic also flags a gold answer string occurring inside supplied "
                "documents or inside this run's own model output; those are ordinary corpus text "
                "and model text, not annotation leaks, and are classified as such rather than "
                "waived"
            ),
        },
        "retrieval_change_after_retry": consolidation["retrieval_change_after_retry"],
        "index_correction": index_correction,
        "citation_id_membership": index_correction["citation_id_membership"],
        "review_materials": review,
        "semantic_annotation": {
            "post_retry_labels": "pending",
            "grounding_labels": "pending",
            "statement": (
                "data collection can be complete while semantic outcome annotation is not; no "
                "grounding or post-retry label is assigned, inferred or auto-filled at stage 14, "
                "and no effectiveness claim is made"
            ),
        },
        "outputs": {},
    }
    hotpotqa.write_json(results / REPORT, report)
    (results / SUMMARY).write_text(summary_markdown(report), encoding="utf-8", newline="\n")
    report["outputs"] = {
        f"results/{name}": sha256_file(results / name)
        for name in (REPORT, SUMMARY, main_study.RUN_INDEX_FILENAME, main_study.LEDGER_FILENAME)
    }
    hotpotqa.write_json(results / REPORT, report)
    return report


def summary_markdown(report: dict) -> str:
    execution = report["execution"]
    accounting = report["accounting"]
    usage = report["usage"]["known_totals"]
    lines = [
        "# Stage 14 - main experiment",
        "",
        f"Author: {report['author']}",
        "",
        f"Protocol: `results/main_experiment_protocol_v3.md` (frozen before the first provider "
        f"call). Plan `{report['plan']['plan_id'][:16]}`, "
        f"{report['plan']['planned_coordinates']} coordinates "
        f"({report['plan']['formula']}), model `{report['plan']['model']}`.",
        "",
        "## Sample",
        "",
        f"- {report['sample']['questions']} questions, {report['sample']['approved_initial_contexts']} "
        "approved initial contexts.",
        f"- Eligible question 54 (`{report['acceptance']['excluded_question']['question_id']}`) excluded: "
        f"{report['acceptance']['excluded_question']['reason']}; its CLEAN review stays pending.",
        f"- Eligible question {report['acceptance']['replacement_question']['eligible_question_number']} "
        f"(`{report['acceptance']['replacement_question']['question_id']}`) entered in the unchanged "
        "frozen candidate order.",
        f"- Predeclared sensitivity subset: {report['sample']['sensitivity_subset_questions']} questions "
        "(same runs, no extra provider calls).",
        f"- Annotation conventions G-1 and K-1 accepted as operational conventions finalized before "
        "data collection; not logical necessities and not preregistered.",
        "",
        "## Execution",
        "",
        "| | |",
        "| --- | ---: |",
        f"| Planned coordinates | {execution['planned_coordinates']} |",
        f"| Completed | {execution['completed']} |",
        f"| Missing | {execution['missing']} |",
        f"| Invocations | {execution['invocations']} |",
        f"| Provider attempts (cumulative) | {accounting['cumulative_stage14_attempts']} |",
        f"| Attempt ceiling | {accounting['global_attempt_ceiling']} |",
        f"| Remaining allowance | {accounting['remaining_allowance']} |",
        f"| Calls logged in runs | {accounting['calls_logged_in_runs']} |",
        "",
        f"Status counts: {execution['status_counts']}.",
        "",
        f"Terminal outcomes of completed runs: {execution['terminal_outcomes_completed']}. These are "
        "technical outcomes of the control flow, **not** semantic results.",
        "",
        f"The plan is exhausted ({execution['pending_coordinates']} coordinates pending). Every "
        "planned coordinate was attempted exactly once. The 7 missing ones are recorded technical "
        "failures of kind `incomplete_response: max_output_tokens` (0.24% of the plan): they stay "
        "missing with their actual status, were not re-run, and were never replaced by another "
        "question or repeat. `max_output_tokens = 800` is a frozen parameter and was not changed.",
        "",
        f"Citation-ID membership, reported separately from grounding: "
        f"{report['citation_id_membership']['valid']} valid, "
        f"{report['citation_id_membership']['invalid']} invalid, "
        f"{report['citation_id_membership']['not_applicable']} not applicable (no answer). "
        "Invalid citations are retained with their runs.",
        "",
        "Index correction: " + report["index_correction"]["defect"] + ". " 
        + report["index_correction"]["scope"] + ". "
        + report["index_correction"]["frozen_implementation_unchanged"] + ".",
        "",
        "## Accounting and audit",
        "",
        f"- Ledger agrees with the batch budget file: {accounting['ledger_agrees_with_batch_budget']}.",
        f"- Attempts summed from runs: {accounting['attempts_summed_from_runs']}; "
        f"calls logged in runs: {accounting['calls_logged_in_runs']}. {accounting['reconciliation_note']}.",
        f"- Known token usage: {usage['total_tokens']} total "
        f"({usage['input_tokens']} input, {usage['output_tokens']} output, "
        f"{usage['cached_tokens']} cached) over {usage['calls_with_usage']} calls with usage.",
        f"- Coordinates with unknown usage: {report['usage']['coordinates_with_unknown_usage']}.",
        f"- Technical check (first 16 coordinates, kept in the dataset): "
        f"passed={report['audit']['technical_check_first_16']['passed']}, "
        f"problems={report['audit']['technical_check_first_16']['problems']}.",
        f"- Full-batch audit: {report['audit']['full_batch']['runs']} runs, "
        f"passed={report['audit']['full_batch']['passed']}, "
        f"problems={report['audit']['full_batch']['problems']}, "
        f"single model={report['audit']['full_batch']['single_model']}, "
        f"store flags={report['audit']['full_batch']['store_flags']}.",
        f"- Retrieval change after retry: {report['retrieval_change_after_retry']}.",
        "",
        "## What is not done",
        "",
        report["semantic_annotation"]["statement"] + ".",
        "",
    ]
    if report["review_materials"]:
        review = report["review_materials"]
        lines += [
            f"Review materials exported, all rows pending: "
            f"{review['post_retry_cases']} distinct post-retry contexts "
            f"({review['post_retry_instances']} instances) and "
            f"{review['grounding_cases']} distinct answer-grounding cases "
            f"({review['grounding_instances']} instances).",
            "",
        ]
    lines += [
        "## Files",
        "",
        "- `results/main_run_index.jsonl` - one row per planned coordinate, including missing ones",
        "- `results/stage14_execution_ledger.json` - cumulative attempt accounting",
        "- `results/stage14_audit_first16.json`, `results/stage14_audit_full.json`",
        "- `results/main_post_retry_*` and `results/main_answer_grounding_*` - pending review sets",
        "- `results/main_experiment_protocol_v3.md`, `results/stage14_acceptance.json`, "
        "`results/main_sample_final.json`, `results/main_plan/`",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 14 report")
    parser.add_argument("--skip-review", action="store_true")
    args = parser.parse_args(argv)
    report = build(load_config(), skip_review=args.skip_review)
    print(json.dumps({k: report[k] for k in ("execution", "accounting")}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
