"""Stage 15 report: assemble the stage record from the artefacts on disk.

    python tools/stage15_report.py

Offline; reads only what the earlier stage 15 steps wrote.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage15_accept as accept
import stage15_analysis as analysis

REPORT = "stage15_report.json"

OUTPUT_FILES = (
    "stage15_acceptance.json",
    "main_analysis.jsonl",
    "main_analysis_results.json",
    "main_analysis_summary.md",
    "main_post_retry_lookup_augmented.json",
    "stage15_validation.json",
    "main_post_retry_reviews.jsonl",
    "main_answer_grounding_reviews.jsonl",
)
CODE_FILES = (
    "tools/stage15_accept.py",
    "tools/stage15_analysis.py",
    "tools/stage15_outputs.py",
    "tools/stage15_run.py",
    "tools/stage15_validate.py",
    "tools/stage15_report.py",
)


def main() -> int:
    config = load_config()
    results = config.paths["results"]
    acceptance = hotpotqa.read_json(results / accept.ACCEPTANCE_FILE)
    payload = hotpotqa.read_json(results / analysis.RESULTS_FILE)
    validation = hotpotqa.read_json(results / "stage15_validation.json")
    full = payload["full_60"]
    sens = payload["sensitivity_55"]

    report = {
        "stage": "stage15_annotation_acceptance_and_analysis",
        "generated_at_utc": analysis.utc_now(),
        "author": "Denys Yuvzhenko",
        "provider_calls": 0,
        "coordinate_reruns": 0,
        "frozen_inputs_modified": False,
        "acceptance": {
            "accepted_at_utc": acceptance["accepted_at_utc"],
            "reviewer": acceptance["reviewer"],
            "basis": acceptance["acceptance_basis"],
            "timing_statement": acceptance["timing_statement"],
            "independent_human_review": acceptance["independent_human_review"],
            "preregistered": acceptance["preregistered"],
            "counts": acceptance["counts"],
            "accepted_proposal_hashes": acceptance["accepted_proposal_hashes"],
            "archived_inputs": acceptance["archived_inputs"],
            "accepted_output_hashes": acceptance["accepted_output_hashes"],
            "post_retry_supplement": acceptance["post_retry_supplement"],
        },
        "dataset": payload["dataset_reconciliation"],
        "estimator": payload["estimator"],
        "primary": {
            "contrast": "D - C on initially defective inputs",
            "not_fully_supported_answer": full["primary_D_minus_C_not_fully_supported"],
            "fully_supported_answer": full["companions_D_minus_C"][analysis.CAT_FULL],
            "abstention_or_escalation": full["companions_D_minus_C"][analysis.CAT_ABSTAIN],
            "unclear_answer": full["companions_D_minus_C"][analysis.CAT_UNCLEAR],
        },
        "clean_utility": full["clean_utility_D_minus_C"],
        "sensitivity_55": {
            "definition": payload["sensitivity_definition"],
            "primary": sens["primary_D_minus_C_not_fully_supported"],
            "fully_supported_answer": sens["companions_D_minus_C"][analysis.CAT_FULL],
            "conclusion_changes": not (
                (sens["primary_D_minus_C_not_fully_supported"]["mean_difference_pp"] < 0)
                == (full["primary_D_minus_C_not_fully_supported"]["mean_difference_pp"] < 0)
                and (
                    (sens["primary_D_minus_C_not_fully_supported"]["ci95_pp"][0] <= 0 <= sens["primary_D_minus_C_not_fully_supported"]["ci95_pp"][1])
                    == (full["primary_D_minus_C_not_fully_supported"]["ci95_pp"][0] <= 0 <= full["primary_D_minus_C_not_fully_supported"]["ci95_pp"][1])
                )
            ),
        },
        "exploratory_contrasts": full["exploratory_contrasts"],
        "per_condition": full["per_condition_D_minus_C"],
        "answer_conditional_descriptive": full["answer_conditional_descriptive"],
        "diagnostics": payload["diagnostics"],
        "validation": {
            "status": validation["status"],
            "checks": [{"name": c["name"], "passed": c["passed"]} for c in validation["checks"]],
            "synthetic_examples": validation["synthetic_examples"],
        },
        "conclusions": payload["conclusions"],
        "limitations": payload["limitations"],
        "figures": payload["figures"],
        "tables": payload["tables"],
        "outputs_sha256": {
            f"results/{name}": sha256_file(results / name) for name in OUTPUT_FILES
        },
        "code_sha256": {
            name: sha256_file(config.project_root / name) for name in CODE_FILES
        },
        "reproduction_commands_powershell": [
            "python tools/stage15_accept.py",
            "python tools/stage15_run.py",
            "python tools/stage15_validate.py",
            "python tools/stage15_report.py",
        ],
        "scope_statement": (
            "one model, one dataset, one retriever and one reviewed sample of 60 questions; no "
            "generalisation beyond that, and no article is written at this stage"
        ),
    }
    hotpotqa.write_json(results / REPORT, report)
    print(json.dumps({k: report[k] for k in ("primary", "validation")}, indent=2, sort_keys=True)[:1800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
