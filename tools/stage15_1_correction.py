"""Stage 15.1: record the reporting corrections.

Reads the regenerated outputs and the pre-correction archive and writes
`results/stage15_1_correction_report.json`. It computes nothing new: the
corrections themselves live in the reporting code
(`tools/stage15_analysis.py`, `tools/stage15_outputs.py`, `tools/stage15_run.py`)
and are applied by rerunning `tools/stage15_run.py`.

    python tools/stage15_1_correction.py

Offline; no provider call, no coordinate re-run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage15_analysis as analysis

REPORT = "stage15_1_correction_report.json"
ARCHIVE_DIRNAME = "stage15_1_archive"

REGENERATED = (
    "main_analysis_summary.md",
    "main_analysis_results.json",
    "stage15_report.json",
    "stage15_validation.json",
    "main_analysis_tables/branch_outcomes.csv",
    "main_analysis_tables/contrasts.csv",
    "main_analysis_tables/terminal_outcomes.csv",
    "main_analysis_figures/figure1_branch_outcome_composition.svg",
    "main_analysis_figures/figure2_effect_estimates.svg",
)
CODE = (
    "tools/stage15_analysis.py",
    "tools/stage15_outputs.py",
    "tools/stage15_run.py",
    "tools/stage15_validate.py",
    "tools/stage15_1_correction.py",
    "tools/stage15_package.py",
)
PROTECTED = (
    "results/main_run_index.jsonl",
    "results/main_analysis.jsonl",
    "results/main_post_retry_reviews.jsonl",
    "results/main_answer_grounding_reviews.jsonl",
    "results/stage15_acceptance.json",
    "results/main_post_retry_lookup_augmented.json",
    "results/main_experiment_protocol_v3.md",
    "results/main_sample_final.json",
    "results/main_plan/manifest.json",
    "config/experiment.json",
)


def main() -> int:
    config = load_config()
    results = config.paths["results"]
    archive = results / ARCHIVE_DIRNAME
    payload = hotpotqa.read_json(results / analysis.RESULTS_FILE)
    validation = hotpotqa.read_json(results / "stage15_validation.json")
    full = payload["full_60"]

    archived = {}
    for name in REGENERATED:
        stem = Path(name).stem
        match = next(archive.glob(f"{stem}_pre15_1_*"), None)
        if match is None:
            continue
        archived[f"results/{name}"] = {
            "pre_correction_sha256": match.name.rsplit("_pre15_1_", 1)[1].split(".")[0],
            "archived_to": f"results/{ARCHIVE_DIRNAME}/{match.name}",
            "post_correction_sha256": sha256_file(results / name),
        }

    previous = next(archive.glob("main_analysis_results_pre15_1_*.json"), None)
    unchanged = None
    if previous is not None:
        before = hotpotqa.read_json(previous)
        unchanged = {
            "primary_D_minus_C_not_fully_supported": (
                before["full_60"]["primary_D_minus_C_not_fully_supported"]
                == full["primary_D_minus_C_not_fully_supported"]
            ),
            "companions": before["full_60"]["companions_D_minus_C"] == full["companions_D_minus_C"],
            "clean_utility": before["full_60"]["clean_utility_D_minus_C"] == full["clean_utility_D_minus_C"],
            "per_condition": before["full_60"]["per_condition_D_minus_C"] == full["per_condition_D_minus_C"],
            "exploratory": before["full_60"]["exploratory_contrasts"] == full["exploratory_contrasts"],
            "branch_levels": (
                before["full_60"]["branch_levels_defective"] == full["branch_levels_defective"]
                and before["full_60"]["branch_levels_clean"] == full["branch_levels_clean"]
            ),
            "sensitivity_55_estimates": all(
                before["sensitivity_55"][key] == payload["sensitivity_55"][key]
                for key in (
                    "primary_D_minus_C_not_fully_supported",
                    "companions_D_minus_C",
                    "clean_utility_D_minus_C",
                    "per_condition_D_minus_C",
                    "exploratory_contrasts",
                    "branch_levels_defective",
                    "branch_levels_clean",
                    "question_ids",
                )
            ),
        }
        unchanged["note"] = (
            "compares every contrast, interval, branch level and question set. The corrected "
            "reports additionally carry the two labelled conditional diagnostics, which are new "
            "descriptive fields rather than changed estimates"
        )

    report = {
        "stage": "stage15_1_reporting_correction",
        "generated_at_utc": analysis.utc_now(),
        "author": "Denys Yuvzhenko",
        "provider_calls": 0,
        "coordinate_reruns": 0,
        "new_analyses_added": False,
        "scope": (
            "reporting corrections only: the conditional diagnostics, the technical-failure prose "
            "and the interpretation wording. No estimate, interval, label or raw record changed"
        ),
        "corrections": {
            "conditional_percentages": {
                "problem": (
                    "the answer-conditional diagnostic was a ratio of question/condition-weighted "
                    "rates computed from rounded values, presented without that label and without "
                    "a pooled counterpart"
                ),
                "fix": (
                    "the weighted ratio is now labelled 'Ratio of question/condition-weighted "
                    "rates - descriptive', computed from unrounded aggregates with unclear answers "
                    "in the denominator and an undefined result for a zero denominator; a separate "
                    "pooled descriptive table over the defective conditions reports completed, "
                    "answered and fully supported counts with both proportions"
                ),
                "weighted_ratio": full["answer_conditional_descriptive"],
                "pooled_counts": full["pooled_conditional_descriptive"],
                "note": (
                    "the two views have different denominators and neither replaces the protocol-v3 "
                    "estimator; branches answer different subsets of runs, so conditional "
                    "proportions alone do not establish equal or superior answer quality"
                ),
            },
            "technical_failure_prose": {
                "problem": "wording could be read as seven failures plus three further failures",
                "fix": (
                    "seven coordinates failed technically in total; three of those failures "
                    "occurred after a retry. Preserved: 2,880 planned, 2,873 completed, "
                    "7 technical failures, 1,024 completed retry instances, 3 technically failed "
                    "retry instances, 1,027 retry instances in total"
                ),
            },
            "interpretation": {
                "problem": (
                    "the conclusion asserted that the reduction was bought by answering less often "
                    "rather than by answering better, which claims a mechanism the data do not "
                    "isolate"
                ),
                "fix": (
                    "the conclusion now states the observed trade-off, says explicitly that the "
                    "descriptive conditional proportions establish neither improved support among "
                    "emitted answers nor the mechanism behind the aggregate differences, defines "
                    "not-fully-supported as PARTIALLY_SUPPORTED + UNSUPPORTED + CONFLICTED without "
                    "calling those answers factually incorrect or hallucinated, and records that "
                    "the acceptability of the CLEAN utility loss was not established because no "
                    "acceptance threshold or non-inferiority margin was specified"
                ),
            },
            "pooled_rates_statement": {
                "problem": "the estimator note said pooled proportions are never reported",
                "fix": (
                    "it now says pooled proportions are never substituted for the estimator and are "
                    "reported separately as labelled descriptive diagnostics"
                ),
            },
        },
        "estimates_unchanged": unchanged,
        "archived_before_replacement": archived,
        "regenerated_files": {
            f"results/{name}": sha256_file(results / name) for name in REGENERATED
        },
        "protected_files_sha256": {
            name: sha256_file(config.project_root / name) for name in PROTECTED
        },
        "code_sha256": {
            name: sha256_file(config.project_root / name)
            for name in CODE
            if (config.project_root / name).is_file()
        },
        "validation": {
            "status": validation["status"],
            "checks": [{"name": c["name"], "passed": c["passed"]} for c in validation["checks"]],
            "synthetic_examples": validation["synthetic_examples"],
        },
        "reproduction_commands_powershell": [
            "python tools/stage15_run.py",
            "python tools/stage15_validate.py",
            "python tools/stage15_report.py",
            "python tools/stage15_1_correction.py",
            "python tools/stage15_package.py",
        ],
    }
    hotpotqa.write_json(results / REPORT, report)
    print(json.dumps({"estimates_unchanged": unchanged, "validation": report["validation"]["status"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
