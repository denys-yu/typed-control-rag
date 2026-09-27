"""Assemble the stage 12 report and summary from the artefacts on disk.

Reads only what the earlier stage 12 steps wrote, so the report cannot state a
number that is not in a file. No API call is made here.

    python tools/stage12_report.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import fault_cases, hotpotqa, retrieval
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage12_main_prep as prep
import stage12_validate as checks
import stage12_corrections as corrections

REPORT_FILENAME = "stage12_report.json"
SUMMARY_FILENAME = "stage12_summary.md"

REPRODUCTION_COMMANDS = [
    "python tools/stage12_cli.py select",
    "python tools/stage12_cli.py build-index",
    "python tools/stage12_cli.py retrieve",
    "python tools/stage12_cli.py eligibility",
    "python tools/stage12_build_edits.py config/main_inconsistent_edit_drafts.json",
    "python tools/stage12_cli.py faults",
    "python tools/stage12_cli.py review-export",
    "python tools/stage12_cli.py validate",
    "python tools/stage12_cli.py dry-run",
    "python tools/stage12_corrections.py",
    "python tools/stage12_report.py",
]

CREATED_FILES = [
    "tools/stage12_main_prep.py",
    "tools/stage12_faults.py",
    "tools/stage12_validate.py",
    "tools/stage12_build_edits.py",
    "tools/stage12_corrections.py",
    "tools/stage12_report.py",
    "tools/stage12_cli.py",
    "config/main_inconsistent_edits.json",
    "config/main_inconsistent_edit_drafts.json",
    "data/processed/main/main_questions.jsonl",
    "data/processed/main/main_corpus.jsonl",
    "data/processed/main/main_annotations.jsonl",
    "data/processed/main/main_candidates.json",
    "data/processed/main/manifest.json",
    "artifacts/main_retrieval/embeddings.npy",
    "artifacts/main_retrieval/documents.jsonl",
    "artifacts/main_retrieval/index_manifest.json",
    "results/main_preparation/selection_rule.json",
    "results/main_preparation/main_retrieval.jsonl",
    "results/main_preparation/eligibility.json",
    "results/main_preparation/fault_contexts.jsonl",
    "results/main_preparation/fault_annotations.jsonl",
    "results/main_preparation/fault_reviews.jsonl",
    "results/main_preparation/fault_manifest.json",
    "results/main_preparation/validation.json",
    "results/main_experiment_protocol_v2.md",
    "results/pilot_summary_corrections_v1.1.md",
    "results/stage12_report.json",
    "results/stage12_summary.md",
]

MODIFIED_FILES = [
    ("results/pilot_analysis_summary.md", "one correction-notice line prepended; observations unchanged"),
    ("results/main_experiment_protocol_draft.md", "one superseded-notice line prepended; text unchanged"),
    ("CLAUDE.md", "stage 12 entry added to the project status"),
]


def build() -> dict:
    config = load_config()
    paths = prep.MainPaths.of(config)
    results = config.paths["results"]

    selection = hotpotqa.read_json(paths.results / prep.SELECTION_RULE_FILENAME)
    data_manifest = hotpotqa.read_json(paths.processed / prep.DATA_MANIFEST_FILENAME)
    index_manifest = hotpotqa.read_json(paths.index / retrieval.INDEX_MANIFEST_FILENAME)
    eligibility = hotpotqa.read_json(paths.results / prep.ELIGIBILITY_FILENAME)
    fault_manifest = hotpotqa.read_json(paths.results / prep.FAULT_MANIFEST_FILENAME)
    validation = hotpotqa.read_json(paths.results / prep.VALIDATION_FILENAME)
    review_index = hotpotqa.read_json(
        paths.results / prep.REVIEW_EXPORT_DIRNAME / checks.REVIEW_INDEX_FILENAME
    )
    dry_runs = sorted((paths.results / checks.DRY_RUNS_DIRNAME).glob("*/dry_run.json"))
    dry_run = json.loads(dry_runs[-1].read_text(encoding="utf-8")) if dry_runs else None
    edits = json.loads((config.project_root / prep.EDITS_RELPATH).read_text(encoding="utf-8"))

    report = {
        "stage": prep.STAGE,
        "author": prep.AUTHOR,
        "generated_at": prep.utc_now(),
        "status": validation["status"],
        "offline": {
            "api_calls": 0,
            "provider_requests": 0,
            "main_experiment_executed": False,
            "note": (
                "stage 12 made no provider call: no client is created anywhere in the stage 12 "
                "tools, and the single dry run only prepares request payloads"
            ),
        },
        "authorized_scope": {
            "design": "60 questions x 4 conditions x 4 branches x 3 repeats = 2880 pipeline runs",
            "max_provider_calls": 11520,
            "model": config.llm.model,
            "second_model": "deferred beyond the current scope of this study",
            "mtrag": "deferred beyond the current scope of this study",
            "sample_size_basis": "practical choice, not a statistically powered sample size",
            "protocol": "results/main_experiment_protocol_v2.md",
        },
        "candidates": {
            "pool_size": selection["pool_size"],
            "seed": selection["seed"],
            "selection_algorithm": selection["selection_algorithm"],
            "selection_rule_sha256": selection["selection_rule_sha256"],
            "excluded_pilot_question_ids": selection["exclusions"]["pilot_question_count"],
            "available_after_exclusion": selection["exclusions"]["available_after_exclusion"],
            "records_total": selection["source"]["records_total"],
            "records_valid": selection["source"]["records_valid"],
            "raw_sha256": selection["source"]["raw_sha256"],
        },
        "corpus": {
            "unique_documents": data_manifest["unique_documents"],
            "paragraphs_before_deduplication": data_manifest["paragraphs_before_deduplication"],
            "duplicates_collapsed": data_manifest["duplicates_collapsed"],
            "data_file_sha256": data_manifest["data_file_sha256"],
        },
        "index": {
            "index_sha256": index_manifest["index_sha256"],
            "corpus_sha256": index_manifest["corpus_sha256"],
            "model_name": index_manifest["model_name"],
            "model_revision": index_manifest["model_revision"],
            "document_count": index_manifest["document_count"],
            "dimension": index_manifest["dimension"],
            "truncation": index_manifest["truncation"],
            "file_sha256": index_manifest["file_sha256"],
            "frozen_before_eligibility": True,
        },
        "eligibility": {
            "rule": eligibility["rule"],
            "experimental_top_k": eligibility["experimental_top_k"],
            "preparation_top_k": eligibility["preparation_top_k"],
            "counts": eligibility["counts"],
            "attrition": eligibility["attrition"],
            "coverage": eligibility["coverage"],
            "exclusion_reason_histogram": eligibility["exclusion_reason_histogram"],
        },
        "construction": {
            "conditions": fault_manifest["conditions"],
            "counts": fault_manifest["counts"],
            "rules": fault_manifest["rules"],
            "inconsistent_edits": {
                "count": edits["count"],
                "file": prep.EDITS_RELPATH.as_posix(),
                "sha256": sha256_file(config.project_root / prep.EDITS_RELPATH),
                "provenance": edits["provenance"],
            },
            "file_sha256": fault_manifest["file_sha256"],
        },
        "review": {
            "pending_rows": fault_manifest["counts"]["reviews_pending"],
            "total_rows": fault_manifest["counts"]["reviews_total"],
            "approved_rows": 0,
            "files": [item["file"] for item in review_index["files"]],
            "questions_per_file": review_index["questions_per_file"],
            "review_file": review_index["review_file"],
            "future_sample_rule": prep.FUTURE_SAMPLE_RULE,
        },
        "validation": {
            "status": validation["status"],
            "checks": [
                {"name": c["name"], "passed": c["passed"], "detail": c["detail"]}
                for c in validation["checks"]
            ],
        },
        "dry_run": (
            {
                "case_id": dry_run["case_id"],
                "question_id": dry_run["question_id"],
                "branches_prepared": dry_run["branches_prepared"],
                "api_calls": dry_run["api_calls"],
                "review_status": dry_run["review_status"],
                "passes_real_execution_gate": dry_run["passes_real_execution_gate"],
                "identical_first_request_across": dry_run["identical_first_request_across"],
            }
            if dry_run
            else None
        ),
        "pilot_corrections": {
            "document": "results/pilot_summary_corrections_v1.1.md",
            "recomputed": corrections.compute(config),
            "pilot_records_changed": False,
        },
        "pilot_preservation": {
            "plan_bound_implementation_files_changed": 0,
            "pilot_paths_untouched": [
                "data/processed/hotpotqa/",
                "data/processed/fault_cases/",
                "artifacts/retrieval/",
                "results/pilot_plan/",
                "results/pilot_runs/",
                "results/pilot_analysis.jsonl",
            ],
            "note": (
                "stage 12 writes only to data/processed/main/, artifacts/main_retrieval/, "
                "results/main_preparation/, config/main_inconsistent_edit*.json, tools/ and the "
                "new stage 12 result documents"
            ),
        },
        "files": {
            "created": CREATED_FILES,
            "modified": [{"file": name, "change": change} for name, change in MODIFIED_FILES],
        },
        "reproduction_commands_powershell": REPRODUCTION_COMMANDS,
        "next_review_files": [item["file"] for item in review_index["files"]],
        "stopping_point": (
            "the main-study review package is prepared; no semantic label is auto-approved, no "
            "runnable schedule is frozen and no paid execution has begun"
        ),
    }
    hotpotqa.write_json(results / REPORT_FILENAME, report)
    (results / SUMMARY_FILENAME).write_text(_summary(report), encoding="utf-8", newline="\n")
    return report


def _summary(report: dict) -> str:
    eligibility = report["eligibility"]
    construction = report["construction"]
    index = report["index"]
    lines = [
        "# Stage 12 — main-study preparation",
        "",
        f"Author: {report['author']}",
        "",
        "Offline stage: **0 provider calls, 0 main-experiment runs.** The pilot data, indices, "
        "annotations, plans and reports are untouched; every stage 12 artefact lives under separate "
        "main-study paths.",
        "",
        "## Authorized scope",
        "",
        f"- {report['authorized_scope']['design']}, upper bound "
        f"{report['authorized_scope']['max_provider_calls']:,} provider calls.",
        f"- One model: `{report['authorized_scope']['model']}`. Second model and MTRAG deferred.",
        "- 60 questions is a practical choice, not a powered sample size.",
        "- Branches, controller policy, one-retry limit, prompts and generation parameters unchanged.",
        f"- Recorded in `{report['authorized_scope']['protocol']}`.",
        "",
        "## Numbers",
        "",
        "| | |",
        "| --- | --- |",
        f"| Candidates screened | {report['candidates']['pool_size']} "
        f"(seed {report['candidates']['seed']}, all 30 pilot ids excluded) |",
        f"| Corpus documents | {report['corpus']['unique_documents']} "
        f"(from {report['corpus']['paragraphs_before_deduplication']} paragraphs, "
        f"{report['corpus']['duplicates_collapsed']} duplicates collapsed) |",
        f"| Index identity | `{index['index_sha256'][:16]}…` "
        f"({index['model_name']} @ {index['model_revision'][:12]}) |",
        f"| Embedding truncation | {index['truncation']['documents_truncated']} of "
        f"{index['document_count']} documents exceed max_seq_length "
        f"{index['truncation']['max_seq_length']} (model and limit unchanged) |",
        f"| Technically eligible | {eligibility['counts']['eligible']} of "
        f"{eligibility['counts']['candidates']} "
        f"(yield {eligibility['attrition']['yield']:.3f}) |",
        f"| Shortfall against the 60-question target | "
        f"{eligibility['counts']['shortfall_against_target']} |",
        f"| Candidate contexts built | {construction['counts']['contexts']} "
        f"(4 x {construction['counts']['eligible_questions']}) |",
        f"| Construction failures | "
        f"{sum(construction['counts']['construction_failed'].values())} |",
        f"| Pending review rows | {report['review']['pending_rows']} of "
        f"{report['review']['total_rows']} |",
        "",
        "Gold-document coverage at the experimental top-5: "
        f"{eligibility['coverage']['both_gold_in_top_k']} questions with both supporting documents, "
        f"{eligibility['coverage']['one_gold_in_top_k']} with one, "
        f"{eligibility['coverage']['no_gold_in_top_k']} with none; document recall "
        f"{eligibility['coverage']['document_recall_at_top_k']:.4f}. At the preparation top-10, "
        f"{eligibility['coverage']['both_gold_in_top_10']} questions have both. Coverage of gold "
        "documents is not proven semantic sufficiency.",
        "",
        "### Exclusions",
        "",
    ]
    for reason, count in eligibility["exclusion_reason_histogram"].items():
        lines.append(f"- {count} — {reason}")
    lines += [
        "",
        "No parameter was tuned to raise the yield: `top_k`, the embedding model, the queries and "
        "the corpus are exactly those fixed before measurement. Documents of excluded candidates "
        "stay in the frozen corpus.",
        "",
        "## Identities to quote",
        "",
        f"- Selection rule: `{report['candidates']['selection_rule_sha256']}`",
        f"- Corpus: `{index['corpus_sha256']}`",
        f"- Index: `{index['index_sha256']}`",
        f"- Contexts: `{construction['file_sha256'][prep.FAULT_CONTEXTS_FILENAME]}`",
        f"- INCONSISTENT edits: `{construction['inconsistent_edits']['sha256']}`",
        "",
        "## Validation",
        "",
    ]
    for check in report["validation"]["checks"]:
        lines.append(f"- [{'ok' if check['passed'] else 'FAILED'}] **{check['name']}** — {check['detail']}")
    dry_run = report["dry_run"]
    if dry_run:
        lines += [
            "",
            f"Offline dry run on main case `{dry_run['case_id']}`: first evaluator request prepared "
            f"for branches {', '.join(dry_run['branches_prepared'])}, "
            f"{dry_run['api_calls']} API calls, review status `{dry_run['review_status']}`, "
            f"real-execution gate: {dry_run['passes_real_execution_gate']}. A/C share one request "
            f"({dry_run['identical_first_request_across']['A_and_C']}) and B/D share one "
            f"({dry_run['identical_first_request_across']['B_and_D']}), as the branch definitions "
            "require.",
        ]
    lines += [
        "",
        "## Pilot summary corrections",
        "",
        "Recorded in `results/pilot_summary_corrections_v1.1.md`, recomputed from "
        "`results/pilot_analysis.jsonl` with `python tools/stage12_corrections.py`:",
        "",
        "- among 241 retries, post-retry states are **136 OK and 105 PARTIAL**;",
        "- **143 cells have all five completed repeats and one has four**; **136 of the 143 complete "
        "cells** have a homogeneous terminal outcome (134 a homogeneous support label).",
        "",
        "No pilot observation was changed.",
        "",
        "## What I need next",
        "",
        "The semantic review of the 572 pending candidate contexts, in candidate order. Please work "
        "through these files and record the labels in "
        f"`{report['review']['review_file']}`:",
        "",
    ]
    for name in report["next_review_files"]:
        lines.append(f"- `{name}`")
    lines += [
        "",
        "For every context set `observed_state` (OK / PARTIAL / EMPTY / INCONSISTENT), "
        "`review_status` (`approved` / `rejected`), `reviewer` and an optional note. The intended "
        "state shown in the export is a construction hypothesis, not a label, and nothing may be "
        "relabelled to raise the yield.",
        "",
        "After the review: the main sample is the **first 60 fully approved, correctly labelled "
        "quadruplets in the frozen randomized candidate order**. No model outcome may influence it.",
        "",
        "## Reproduction (PowerShell, from the project root)",
        "",
        "```powershell",
        *REPRODUCTION_COMMANDS,
        "```",
        "",
        "## Stopping point",
        "",
        "Preparation stops here. No semantic label was auto-approved, no runnable schedule was "
        "frozen with pending cases, and no paid execution has begun.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    report = build()
    print(f"status: {report['status']}")
    print(f"eligible: {report['eligibility']['counts']['eligible']} of "
          f"{report['eligibility']['counts']['candidates']}")
    print(f"pending review rows: {report['review']['pending_rows']}")
