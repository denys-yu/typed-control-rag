"""Offline reproduction of the published main-study results.

This is a packaging wrapper around the analysis code that produced the results
(`stage15_analysis.py`, `stage15_outputs.py`, `stage15_run.py`, `stage15_validate.py`).
It changes no estimator, repeats no acceptance procedure and rewrites no label. It

* copies the accepted observations and annotations into an isolated working
  directory, so that nothing under `results/` is modified;
* recomputes the analysis dataset from the per-run records in
  `results/main_run_index.jsonl` and the accepted annotation files, rather than
  reading any stored aggregate;
* re-runs the protocol-v3 estimator and the bootstrap over that dataset;
* re-runs the 18 offline checks of `stage15_validate.py`;
* compares every regenerated artefact with the published one, and compares the
  headline numbers with the values fixed at stage 15.1.

    python tools/reproduce_analysis.py

No OPENAI_API_KEY, no network access and no provider call are involved, and no
coordinate is re-run. Outputs are written to `results/reproduction/` only.

Author: Denys Yuvzhenko
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage15_analysis as analysis
import stage15_run
import stage15_validate

OUTPUT_DIRNAME = "reproduction"
WORK_DIRNAME = "work"
REPORT_FILE = "reproduction_report.json"
SUMMARY_FILE = "reproduction_summary.md"

# Observations and accepted annotations the analysis reads. Copied into the working
# directory so that the published files cannot be touched by a reproduction run.
INPUT_FILES = (
    "main_experiment_protocol_v3.md",
    "main_sample_final.json",
    "main_run_index.jsonl",
    "main_post_retry_reviews.jsonl",
    "main_answer_grounding_reviews.jsonl",
    "main_post_retry_lookup.json",
    "main_post_retry_lookup_augmented.json",
    "main_answer_grounding_lookup.json",
    "main_post_retry_contexts.jsonl",
    "main_answer_grounding_cases.jsonl",
    "main_semantic_review_manifest.json",
    "main_semantic_review_summary.md",
    "main_post_retry_lookup_additions.json",
    "main_post_retry_review_proposals.jsonl",
    "main_answer_grounding_review_proposals.jsonl",
    "pilot_answer_grounding_review.md",
    "pilot_post_retry_annotation_rules.md",
    "stage13_adjudication.md",
    "stage14_report.json",
    "stage15_acceptance.json",
)
INPUT_DIRS = ("main_plan", "stage15_1_archive")

# Artefacts the run regenerates; each is compared with the published copy.
REGENERATED = (
    "main_analysis.jsonl",
    "main_analysis_results.json",
    "main_analysis_summary.md",
    "main_analysis_tables/branch_outcomes.csv",
    "main_analysis_tables/contrasts.csv",
    "main_analysis_tables/terminal_outcomes.csv",
    "main_analysis_figures/figure1_branch_outcome_composition.svg",
    "main_analysis_figures/figure2_effect_estimates.svg",
)
# Written with a fresh timestamp on every run, so compared by content, not bytes.
TIMESTAMPED = {"main_analysis_results.json"}

# The state fixed at stage 15.1. These are expectations, never adjusted to a new
# result: a mismatch is a packaging defect to be explained and fixed.
EXPECTED = {
    "rows": 2880,
    "completed": 2873,
    "technical_failures": 7,
    "answered": 1106,
    "provider_attempts": 6049,
    "citation_id_valid": 863,
    "citation_id_invalid": 243,
    "full_sample_questions": 60,
    "sensitivity_questions": 55,
    "primary_D_minus_C_not_fully_supported_pp": [-12.04, -18.15, -6.48],
    "companion_fully_supported_pp": [-19.81, -27.96, -12.04],
    "companion_abstention_pp": [31.85, 23.7, 40.0],
    "clean_fully_supported_pp": [-8.33, -16.11, -1.67],
    "clean_abstention_pp": [7.22, 0.56, 15.0],
    "sensitivity_primary_pp": [-10.71, -16.57, -5.45],
    "pooled_defective_fully_supported_of_answered_percent": {"C": 60.13, "D": 58.02},
    "token_usage_total": 9458529,
}

# Files that a reproduction run must leave byte-identical.
PROTECTED = (
    "results/main_run_index.jsonl",
    "results/main_analysis.jsonl",
    "results/main_analysis_results.json",
    "results/main_analysis_summary.md",
    "results/main_post_retry_reviews.jsonl",
    "results/main_answer_grounding_reviews.jsonl",
    "results/main_post_retry_lookup_augmented.json",
    "results/main_answer_grounding_lookup.json",
    "results/main_sample_final.json",
    "results/main_experiment_protocol_v3.md",
    "results/stage15_acceptance.json",
    "results/main_plan/manifest.json",
    "results/main_plan/runs.jsonl",
    "config/experiment.json",
)


def stage(results: Path, work: Path) -> list[str]:
    """Copy the analysis inputs into an isolated working directory."""
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    staged = []
    for name in INPUT_FILES:
        shutil.copy2(results / name, work / name)
        staged.append(name)
    for name in INPUT_DIRS:
        shutil.copytree(results / name, work / name)
        staged.extend(
            path.relative_to(work).as_posix() for path in sorted((work / name).rglob("*")) if path.is_file()
        )
    for name in REGENERATED:
        assert not (work / name).exists(), f"{name} must be produced, not copied"
    return staged


def strip_volatile(payload: dict) -> dict:
    """Drop the fields that legitimately differ between two runs of the same analysis."""
    stripped = {key: value for key, value in payload.items() if key != "generated_at_utc"}
    return stripped


def compare_artefacts(results: Path, work: Path) -> list[dict]:
    comparisons = []
    for name in REGENERATED:
        published, produced = results / name, work / name
        record = {
            "file": name,
            "published_sha256": sha256_file(published) if published.is_file() else None,
            "reproduced_sha256": sha256_file(produced) if produced.is_file() else None,
        }
        if not produced.is_file():
            record["match"] = False
            record["how"] = "not produced"
        elif name in TIMESTAMPED:
            same = strip_volatile(hotpotqa.read_json(published)) == strip_volatile(
                hotpotqa.read_json(produced)
            )
            record["match"] = same
            record["how"] = "content equal, generation timestamp excluded"
        else:
            record["match"] = record["published_sha256"] == record["reproduced_sha256"]
            record["how"] = "byte-identical"
        comparisons.append(record)
    return comparisons


def compare_headline(payload: dict, rows: list[dict]) -> list[dict]:
    """Compare recomputed values with the numbers fixed at stage 15.1.

    Every observed value is derived from the regenerated row data or from the
    regenerated estimate payload; nothing is read back from a published aggregate.
    """
    full, sens = payload["full_60"], payload["sensitivity_55"]
    diag = payload["diagnostics"]
    reconciliation = payload["dataset_reconciliation"]

    def interval(block: dict) -> list[float]:
        return [block["mean_difference_pp"], block["ci95_pp"][0], block["ci95_pp"][1]]

    citations = diag["citation_id_validity"]["counts"]
    pooled = full["pooled_conditional_descriptive"]["by_branch"]

    observed = {
        "rows": len(rows),
        "completed": sum(1 for row in rows if row["record_status"] == "completed"),
        "technical_failures": sum(1 for row in rows if row["record_status"] != "completed"),
        "answered": sum(1 for row in rows if row["terminal_outcome"] == "answered"),
        "provider_attempts": sum(row["api_attempts"] or 0 for row in rows),
        "citation_id_valid": citations["True"],
        "citation_id_invalid": citations["False"],
        "full_sample_questions": full["questions"],
        "sensitivity_questions": sens["questions"],
        "primary_D_minus_C_not_fully_supported_pp": interval(
            full["primary_D_minus_C_not_fully_supported"]
        ),
        "companion_fully_supported_pp": interval(full["companions_D_minus_C"][analysis.CAT_FULL]),
        "companion_abstention_pp": interval(full["companions_D_minus_C"][analysis.CAT_ABSTAIN]),
        "clean_fully_supported_pp": interval(full["clean_utility_D_minus_C"][analysis.CAT_FULL]),
        "clean_abstention_pp": interval(full["clean_utility_D_minus_C"][analysis.CAT_ABSTAIN]),
        "sensitivity_primary_pp": interval(sens["primary_D_minus_C_not_fully_supported"]),
        "pooled_defective_fully_supported_of_answered_percent": {
            branch: pooled[branch]["fully_supported_of_answered_percent"] for branch in ("C", "D")
        },
        "token_usage_total": diag["usage"]["total_tokens"],
    }
    checks = [
        {
            "name": name,
            "expected": EXPECTED[name],
            "observed": observed[name],
            "match": EXPECTED[name] == observed[name],
        }
        for name in EXPECTED
    ]
    checks.append(
        {
            "name": "reconciliation_matches_expected_flag",
            "expected": True,
            "observed": reconciliation["matches_expected"],
            "match": reconciliation["matches_expected"] is True,
        }
    )
    weighted = full["answer_conditional_descriptive"]
    checks.append(
        {
            "name": "weighted_and_pooled_diagnostics_kept_distinct",
            "expected": "two labelled views with different denominators",
            "observed": {
                "weighted_label": weighted.get("label"),
                "weighted_C_percent": weighted["by_branch"]["C"]["weighted_fully_supported_share_percent"],
                "pooled_C_percent": pooled["C"]["fully_supported_of_answered_percent"],
            },
            "match": (
                "weighted" in (weighted.get("label") or "").lower()
                and weighted["by_branch"]["C"]["weighted_fully_supported_share_percent"] == 60.4
                and pooled["C"]["fully_supported_of_answered_percent"] == 60.13
            ),
        }
    )
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output-dir",
        default=None,
        help="where to write the reproduction (default: results/reproduction)",
    )
    args = parser.parse_args(argv)

    config = load_config()
    results = config.paths["results"]
    output = Path(args.output_dir).resolve() if args.output_dir else results / OUTPUT_DIRNAME
    output.mkdir(parents=True, exist_ok=True)
    work = output / WORK_DIRNAME

    before = {name: sha256_file(config.project_root / name) for name in PROTECTED}
    staged = stage(results, work)
    shim = dataclasses.replace(config, paths={**config.paths, "results": work})

    # The wrapper redirects only where the analysis reads and writes its result
    # files; the estimator, the bootstrap and the checks are the originals.
    stage15_run.load_config = lambda: shim
    stage15_validate.load_config = lambda: shim
    print("--- recomputing the analysis -------------------------------------------")
    stage15_run.main()
    print("--- re-running the offline checks ---------------------------------------")
    stage15_validate.main()

    payload = hotpotqa.read_json(work / analysis.RESULTS_FILE)
    rows = analysis.read_jsonl(work / analysis.ANALYSIS_ROWS)
    validation = hotpotqa.read_json(work / stage15_validate.CHECKS_FILE)

    artefacts = compare_artefacts(results, work)
    headline = compare_headline(payload, rows)
    after = {name: sha256_file(config.project_root / name) for name in PROTECTED}
    untouched = [name for name in PROTECTED if before[name] != after[name]]

    failed_checks = [check["name"] for check in validation["checks"] if not check["passed"]]
    report = {
        "tool": "reproduce_analysis",
        "generated_at_utc": analysis.utc_now(),
        "author": "Denys Yuvzhenko",
        "provider_calls": 0,
        "network_access": False,
        "coordinate_reruns": 0,
        "labels_changed": 0,
        "reference_state": "stage 15.1 corrected reporting",
        "staged_input_files": len(staged),
        "artefact_comparison": artefacts,
        "headline_comparison": headline,
        "offline_checks": {
            "status": validation["status"],
            "count": len(validation["checks"]),
            "failed": failed_checks,
        },
        "protected_files_unchanged": not untouched,
        "protected_files_changed": untouched,
        "status": "ok"
        if all(item["match"] for item in artefacts)
        and all(check["match"] for check in headline)
        and not failed_checks
        and not untouched
        else "mismatch",
    }
    hotpotqa.write_json(output / REPORT_FILE, report)
    write_summary(output / SUMMARY_FILE, report)

    print("--- reproduction --------------------------------------------------------")
    for item in artefacts:
        print(f"[{'ok' if item['match'] else 'DIFF'}] {item['file']} ({item['how']})")
    for check in headline:
        print(f"[{'ok' if check['match'] else 'DIFF'}] {check['name']}: {check['observed']}")
    print(f"offline checks        : {validation['status']} ({len(validation['checks'])} checks)")
    print(f"published files touched: {untouched or 'none'}")
    print(f"status                : {report['status']}")
    print(f"written               : {output}")
    return 0 if report["status"] == "ok" else 1


def write_summary(path: Path, report: dict) -> None:
    lines = [
        "# Offline reproduction of the main-study results",
        "",
        f"Generated: {report['generated_at_utc']} (UTC). Author: {report['author']}.",
        "",
        f"Status: **{report['status']}** against the {report['reference_state']}.",
        "",
        "No provider call, no network access, no coordinate re-run and no label change. "
        "The analysis dataset is recomputed from the per-run records and the accepted "
        "annotations; no stored aggregate is read back.",
        "",
        "## Regenerated artefacts",
        "",
        "| File | Comparison | Result |",
        "|---|---|---|",
    ]
    for item in report["artefact_comparison"]:
        lines.append(f"| `{item['file']}` | {item['how']} | {'match' if item['match'] else 'DIFFERS'} |")
    lines += [
        "",
        "## Headline numbers against stage 15.1",
        "",
        "| Quantity | Expected | Observed | Result |",
        "|---|---|---|---|",
    ]
    for check in report["headline_comparison"]:
        lines.append(
            f"| {check['name']} | `{check['expected']}` | `{check['observed']}` | "
            f"{'match' if check['match'] else 'DIFFERS'} |"
        )
    checks = report["offline_checks"]
    lines += [
        "",
        "## Offline checks",
        "",
        f"`stage15_validate.py`: {checks['count']} checks, status `{checks['status']}`, "
        f"failed: {checks['failed'] or 'none'}.",
        "",
        "## Published files",
        "",
        f"Byte-identical after the run: {'yes' if report['protected_files_unchanged'] else 'NO'}"
        + ("." if report["protected_files_unchanged"] else f"; changed: {report['protected_files_changed']}."),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
