"""Stage 15 step 7: focused offline checks on the acceptance and the analysis.

Checks the joins, the outcome partition, the estimator's weighting and pairing,
the missing-cell rule, the sensitivity membership, determinism across reruns and
the integrity of the frozen inputs. Includes a synthetic example that separates
the required question-level estimator from pooled run weighting.

    python tools/stage15_validate.py

Offline; no provider call and no coordinate re-run.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage15_analysis as analysis
import stage15_accept as accept

CHECKS_FILE = "stage15_validation.json"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def synthetic_weighting_example() -> dict:
    """A case where pooled-run weighting and the protocol estimator disagree.

    One question, branches D and C, three defective conditions. PARTIAL has many
    completed repeats and EMPTY only one, so pooling runs lets PARTIAL dominate,
    while the protocol weights each condition one third.
    """
    rows = []

    def add(branch, condition, repeats, category):
        for repeat in range(1, repeats + 1):
            rows.append(
                {
                    "question_id": "Q1",
                    "condition": condition,
                    "branch": branch,
                    "repeat": repeat,
                    "semantic_status": "completed",
                    "semantic_category": category,
                }
            )

    # D: fails on the single EMPTY run, is clean on the many PARTIAL runs.
    add("D", "PARTIAL", 9, analysis.CAT_FULL)
    add("D", "EMPTY", 1, analysis.CAT_NOT_FULL)
    add("D", "INCONSISTENT", 2, analysis.CAT_FULL)
    # C: fails on some PARTIAL runs only.
    add("C", "PARTIAL", 9, analysis.CAT_NOT_FULL)
    add("C", "EMPTY", 1, analysis.CAT_FULL)
    add("C", "INCONSISTENT", 2, analysis.CAT_FULL)

    means = analysis.cell_means(rows)
    protocol_d = analysis.question_values(means, ["Q1"], "D", analysis.CAT_NOT_FULL, analysis.DEFECTIVE)["Q1"]
    protocol_c = analysis.question_values(means, ["Q1"], "C", analysis.CAT_NOT_FULL, analysis.DEFECTIVE)["Q1"]
    pooled_d = sum(
        1 for r in rows if r["branch"] == "D" and r["semantic_category"] == analysis.CAT_NOT_FULL
    ) / sum(1 for r in rows if r["branch"] == "D")
    pooled_c = sum(
        1 for r in rows if r["branch"] == "C" and r["semantic_category"] == analysis.CAT_NOT_FULL
    ) / sum(1 for r in rows if r["branch"] == "C")
    return {
        "protocol_estimator_difference_pp": round((protocol_d - protocol_c) * 100, 2),
        "pooled_run_difference_pp": round((pooled_d - pooled_c) * 100, 2),
        "differs": abs((protocol_d - protocol_c) - (pooled_d - pooled_c)) > 1e-9,
        "explanation": (
            "pooling runs lets the nine PARTIAL repeats dominate and reverses the sign; the "
            "protocol weights PARTIAL, EMPTY and INCONSISTENT one third each"
        ),
    }


def synthetic_missing_cell_example() -> dict:
    """A question missing one required cell is dropped from that contrast only."""
    rows = []
    for question in ("Q1", "Q2"):
        for branch in ("C", "D"):
            for condition in analysis.DEFECTIVE:
                if question == "Q2" and branch == "D" and condition == "EMPTY":
                    continue  # no completed run in this cell
                rows.append(
                    {
                        "question_id": question,
                        "condition": condition,
                        "branch": branch,
                        "repeat": 1,
                        "semantic_status": "completed",
                        "semantic_category": analysis.CAT_NOT_FULL if branch == "C" else analysis.CAT_FULL,
                    }
                )
    means = analysis.cell_means(rows)
    resampler = analysis.Resampler(resamples=50, seed=analysis.SEED)
    defective = analysis.paired_contrast(
        means, ["Q1", "Q2"], "D", "C", analysis.CAT_NOT_FULL, analysis.DEFECTIVE, resampler
    )
    partial_only = analysis.paired_contrast(
        means, ["Q1", "Q2"], "D", "C", analysis.CAT_NOT_FULL, ("PARTIAL",), resampler
    )
    return {
        "defective_available_questions": defective["available_questions"],
        "defective_excluded": defective["excluded_questions"],
        "partial_only_available_questions": partial_only["available_questions"],
        "dropped_only_from_affected_comparison": (
            defective["available_questions"] == 1 and partial_only["available_questions"] == 2
        ),
    }


def synthetic_conditional_example() -> dict:
    """Weighted and pooled conditional proportions can differ on the same runs.

    One question, one branch, two defective conditions with different completed
    repeat counts: PARTIAL answers often and is never fully supported, EMPTY
    answers once and is fully supported. Pooling runs lets PARTIAL dominate; the
    weighted view gives each condition one half.
    """
    rows = []

    def add(condition, repeats, category):
        for repeat in range(1, repeats + 1):
            rows.append(
                {
                    "question_id": "Q1",
                    "branch": "D",
                    "condition": condition,
                    "repeat": repeat,
                    "semantic_status": "completed",
                    "semantic_category": category,
                    "terminal_outcome": "answered" if category != analysis.CAT_ABSTAIN else "controller_abstained",
                    "answer_support": (
                        "FULLY_SUPPORTED"
                        if category == analysis.CAT_FULL
                        else "PARTIALLY_SUPPORTED"
                        if category == analysis.CAT_NOT_FULL
                        else "not_applicable"
                    ),
                }
            )

    add("PARTIAL", 9, analysis.CAT_NOT_FULL)
    add("EMPTY", 1, analysis.CAT_FULL)
    conditions = ("PARTIAL", "EMPTY")
    means = analysis.cell_means(rows)
    weighted = analysis.weighted_conditional(means, ["Q1"], conditions)["D"]
    pooled = analysis.pooled_conditional(rows, ["Q1"], conditions)["D"]
    return {
        "weighted_fully_supported_share_percent": weighted["weighted_fully_supported_share_percent"],
        "pooled_fully_supported_of_answered_percent": pooled["fully_supported_of_answered_percent"],
        "differs": abs(
            weighted["weighted_fully_supported_share_percent"]
            - pooled["fully_supported_of_answered_percent"]
        )
        > 1e-9,
        "explanation": (
            "the weighted view gives PARTIAL and EMPTY one half each (50.00%), the pooled view "
            "counts nine PARTIAL answers against one EMPTY answer (10.00%)"
        ),
    }


def synthetic_undefined_ratio_example() -> dict:
    """A branch that never answers gives an undefined conditional ratio, not zero."""
    rows = [
        {
            "question_id": "Q1",
            "branch": "D",
            "condition": condition,
            "repeat": 1,
            "semantic_status": "completed",
            "semantic_category": analysis.CAT_ABSTAIN,
            "terminal_outcome": "controller_abstained",
            "answer_support": "not_applicable",
        }
        for condition in ("PARTIAL", "EMPTY")
    ]
    means = analysis.cell_means(rows)
    weighted = analysis.weighted_conditional(means, ["Q1"], ("PARTIAL", "EMPTY"))["D"]
    pooled = analysis.pooled_conditional(rows, ["Q1"], ("PARTIAL", "EMPTY"))["D"]
    return {
        "weighted_defined": weighted["defined"],
        "weighted_share": weighted["weighted_fully_supported_share_percent"],
        "pooled_defined": pooled["defined"],
        "pooled_share": pooled["fully_supported_of_answered_percent"],
        "reported_as_undefined": (
            weighted["defined"] is False
            and weighted["weighted_fully_supported_share_percent"] is None
            and pooled["defined"] is False
            and pooled["fully_supported_of_answered_percent"] is None
        ),
    }


def synthetic_unclear_denominator_example() -> dict:
    """UNCLEAR answers belong in the conditional denominator."""
    rows = []
    for condition, category, support in (
        ("PARTIAL", analysis.CAT_FULL, "FULLY_SUPPORTED"),
        ("EMPTY", analysis.CAT_UNCLEAR, "UNCLEAR"),
    ):
        rows.append(
            {
                "question_id": "Q1",
                "branch": "D",
                "condition": condition,
                "repeat": 1,
                "semantic_status": "completed",
                "semantic_category": category,
                "terminal_outcome": "answered",
                "answer_support": support,
            }
        )
    means = analysis.cell_means(rows)
    weighted = analysis.weighted_conditional(means, ["Q1"], ("PARTIAL", "EMPTY"))["D"]
    return {
        "weighted_answer_rate_percent": weighted["weighted_answer_rate_percent"],
        "weighted_fully_supported_share_percent": weighted["weighted_fully_supported_share_percent"],
        "unclear_counted_in_denominator": (
            abs(weighted["weighted_answer_rate_percent"] - 100.0) < 1e-9
            and abs(weighted["weighted_fully_supported_share_percent"] - 50.0) < 1e-9
        ),
    }


def main() -> int:
    config = load_config()
    results = config.paths["results"]
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    rows = read_jsonl(results / analysis.ANALYSIS_ROWS)
    index_rows = read_jsonl(results / analysis.RUN_INDEX)
    payload = hotpotqa.read_json(results / analysis.RESULTS_FILE)
    answer_reviews = {r["case_sha256"]: r for r in read_jsonl(results / accept.ANSWER_REVIEWS)}
    context_reviews = {r["context_sha256"]: r for r in read_jsonl(results / accept.CONTEXT_REVIEWS)}
    answer_lookup = hotpotqa.read_json(results / accept.ANSWER_LOOKUP)
    augmented = hotpotqa.read_json(results / accept.AUGMENTED_LOOKUP)

    check(
        "one_row_per_planned_coordinate",
        len(rows) == 2880
        and len({r["coordinate"] for r in rows}) == 2880
        and {r["coordinate"] for r in rows} == {r["coordinate"] for r in index_rows},
        f"{len(rows)} rows, {len({r['coordinate'] for r in rows})} unique coordinates, identical to the run index",
    )

    answered = [r for r in rows if r["terminal_outcome"] == "answered"]
    expansion_problems = [
        r["run_id"]
        for r in answered
        if answer_reviews[r["grounding_case_sha256"]]["answer_support"] != r["answer_support"]
        or answer_reviews[r["grounding_case_sha256"]]["explanation_support"] != r["explanation_support"]
    ]
    instances = sum(len(v) for v in answer_lookup["by_case"].values())
    check(
        "deduplicated_annotations_expanded_correctly",
        not expansion_problems and len(answered) == 1106 == instances,
        f"{len(answer_reviews)} accepted grounding cases expanded to {len(answered)} answered runs "
        f"({instances} lookup instances), {len(expansion_problems)} label mismatches",
    )

    retried = [r for r in rows if r["retried"] and r["semantic_status"] == "completed"]
    context_problems = [
        r["run_id"]
        for r in retried
        if context_reviews[r["post_retry_context_sha256"]]["observed_state"] != r["post_retry_reviewed_state"]
    ]
    completed_instances = sum(
        1 for v in augmented["by_case"].values() for i in v if i["scope"] == "completed"
    )
    technical_instances = sum(
        1 for v in augmented["by_case"].values() for i in v if i["scope"] == "technical_failure"
    )
    check(
        "post_retry_labels_expanded_and_scoped",
        not context_problems
        and len(retried) == completed_instances == 1024
        and technical_instances == 3
        and len(context_reviews) == 335,
        f"{len(context_reviews)} contexts -> {len(retried)} completed retried runs; "
        f"{technical_instances} technical-failure instances kept separate",
    )

    failures = [r for r in rows if r["record_status"] != "completed"]
    non_answered = [r for r in rows if r["semantic_status"] == "completed" and r["terminal_outcome"] != "answered"]
    check(
        "technical_failures_and_non_answers",
        len(failures) == 7
        and all(r["semantic_category"] is None and r["semantic_status"] == "missing_technical_failure" for r in failures)
        and all(r["answer_support"] == "not_applicable" for r in non_answered)
        and all(r["semantic_category"] == analysis.CAT_ABSTAIN for r in non_answered),
        f"{len(failures)} technical failures carry no semantic category; "
        f"{len(non_answered)} non-answered completed runs are 'not_applicable', not false",
    )

    completed = [r for r in rows if r["semantic_status"] == "completed"]
    counts = Counter(r["semantic_category"] for r in completed)
    check(
        "mutually_exclusive_categories",
        sum(counts.values()) == len(completed) == 2873 and set(counts) <= set(analysis.CATEGORIES),
        f"{dict(counts)} sums to {len(completed)} completed runs",
    )

    invalid = [r for r in answered if r["citation_id_membership_valid"] is False]
    by_support = Counter(r["answer_support"] for r in invalid)
    check(
        "citation_validity_separate_from_grounding",
        len(invalid) == 243
        and all(
            r["semantic_category"]
            == (
                analysis.CAT_FULL
                if r["answer_support"] == "FULLY_SUPPORTED"
                else analysis.CAT_NOT_FULL
                if r["answer_support"] in analysis.NOT_FULL_LABELS
                else analysis.CAT_UNCLEAR
            )
            for r in invalid
        ),
        f"{len(invalid)} citation-invalid answers retained; their grounding labels are {dict(by_support)}",
    )

    weighting = synthetic_weighting_example()
    check(
        "question_level_estimator_differs_from_pooled_runs",
        weighting["differs"],
        f"synthetic case: protocol {weighting['protocol_estimator_difference_pp']:+.2f} pp vs pooled "
        f"{weighting['pooled_run_difference_pp']:+.2f} pp",
    )

    missing = synthetic_missing_cell_example()
    check(
        "missing_cell_excludes_only_the_affected_comparison",
        missing["dropped_only_from_affected_comparison"],
        f"defective contrast keeps {missing['defective_available_questions']} of 2 questions, "
        f"the PARTIAL-only contrast keeps {missing['partial_only_available_questions']}",
    )

    resampler = analysis.Resampler(resamples=100, seed=analysis.SEED)
    questions = tuple(f"Q{i}" for i in range(10))
    first = resampler.indices(questions)
    second = analysis.Resampler(resamples=100, seed=analysis.SEED).indices(questions)
    check(
        "paired_whole_question_resampling",
        first == second
        and all(len(draw) == len(questions) for draw in first)
        and all(0 <= i < len(questions) for draw in first for i in draw)
        and first is resampler.indices(questions),
        "resamples are deterministic for a given question set, draw whole questions with "
        "replacement, and are reused across outcomes sharing that set",
    )

    sens = payload["sensitivity_55"]
    full_ids = set(payload["full_60"]["question_ids"])
    excluded = set(analysis.SENSITIVITY_EXCLUSIONS)
    check(
        "sensitivity_membership_exact",
        len(sens["question_ids"]) == 55
        and set(sens["question_ids"]) == full_ids - excluded
        and excluded <= full_ids,
        f"55 questions = 60 minus the five predeclared exclusions {sorted(excluded)}",
    )

    # determinism: recompute and compare, ignoring generation timestamps
    ordered = payload["full_60"]["question_ids"]
    sens_ids = payload["sensitivity_55"]["question_ids"]
    fresh_resampler = analysis.Resampler()
    again_full = analysis.analysis_set(rows, ordered, "full_60", fresh_resampler)
    again_sens = analysis.analysis_set(rows, sens_ids, "sensitivity_55", fresh_resampler)
    check(
        "deterministic_across_reruns",
        again_full == payload["full_60"] and again_sens == payload["sensitivity_55"],
        "recomputed estimates are identical to the stored ones (timestamps excluded)",
    )

    manifest = hotpotqa.read_json(results / accept.MANIFEST)
    frozen = {
        name: sha256_file(results / name) == digest
        for name, digest in manifest["source_sha256"].items()
        if name not in (accept.CONTEXT_REVIEWS, accept.ANSWER_REVIEWS)
    }
    proposals_unchanged = all(
        sha256_file(results / name) == digest for name, digest in manifest["output_sha256"].items()
    )
    plan_manifest = hotpotqa.read_json(results / "main_plan" / "manifest.json")
    stage14 = hotpotqa.read_json(results / "stage14_report.json")
    check(
        "frozen_inputs_unchanged",
        all(frozen.values())
        and proposals_unchanged
        and plan_manifest["plan_id"] == stage14["plan"]["plan_id"]
        and sha256_file(results / analysis.PROTOCOL) == stage14["protocol"]["sha256"],
        "protocol, plan, run index, exported cases and the supplied proposal files are byte-identical; "
        "only the two review files were rewritten by the accepted labels",
    )

    # --- stage 15.1 corrections -----------------------------------------------------
    conditional_example = synthetic_conditional_example()
    undefined_example = synthetic_undefined_ratio_example()
    unclear_example = synthetic_unclear_denominator_example()

    weighted = payload["full_60"]["answer_conditional_descriptive"]
    pooled = payload["full_60"]["pooled_conditional_descriptive"]["by_branch"]
    means = analysis.cell_means(rows)
    recomputed = analysis.weighted_conditional(means, payload["full_60"]["question_ids"], analysis.DEFECTIVE)
    unrounded_ok = all(
        (
            weighted["by_branch"][branch]["unrounded"] == recomputed[branch]["unrounded"]
            and weighted["by_branch"][branch]["weighted_fully_supported_share_percent"]
            == round(recomputed[branch]["unrounded"]["weighted_fully_supported_share"] * 100, 2)
        )
        for branch in analysis.BRANCHES
    )
    rounded_first = {
        branch: round(
            round(payload["full_60"]["branch_levels_defective"][branch][analysis.CAT_FULL]["rate_pp"], 2)
            / sum(
                round(payload["full_60"]["branch_levels_defective"][branch][c]["rate_pp"], 2)
                for c in (analysis.CAT_FULL, analysis.CAT_NOT_FULL, analysis.CAT_UNCLEAR)
            )
            * 100,
            6,
        )
        for branch in analysis.BRANCHES
    }
    check(
        "weighted_conditional_uses_unrounded_values",
        unrounded_ok,
        "the weighted ratio is computed from unrounded aggregates and rounded only for "
        f"presentation; rounding first would give {rounded_first}",
    )
    check(
        "weighted_conditional_labelled_and_includes_unclear",
        weighted["label"] == "Ratio of question/condition-weighted rates - descriptive"
        and all(weighted["by_branch"][b]["denominator_includes_unclear"] for b in analysis.BRANCHES)
        and unclear_example["unclear_counted_in_denominator"],
        "labelled as a ratio of question/condition-weighted rates; unclear answers are in the "
        "denominator (synthetic case: 100.00% answer rate, 50.00% fully supported share)",
    )
    check(
        "zero_denominator_reported_as_undefined",
        undefined_example["reported_as_undefined"],
        "a branch that never answers yields an undefined ratio in both views, not zero",
    )

    defective_rows = [
        r
        for r in rows
        if r["condition"] in analysis.DEFECTIVE and r["semantic_status"] == "completed"
    ]
    pooled_totals = {
        "completed": sum(v["completed_runs"] for v in pooled.values()),
        "answered": sum(v["answered_runs"] for v in pooled.values()),
        "fully_supported": sum(v["fully_supported_answers"] for v in pooled.values()),
    }
    direct = {
        "completed": len(defective_rows),
        "answered": sum(1 for r in defective_rows if r["terminal_outcome"] == "answered"),
        "fully_supported": sum(1 for r in defective_rows if r["answer_support"] == "FULLY_SUPPORTED"),
    }
    per_branch_ok = all(
        v["fully_supported_of_answered_percent"]
        == round(v["fully_supported_answers"] / v["answered_runs"] * 100, 2)
        and v["answered_of_completed_percent"]
        == round(v["answered_runs"] / v["completed_runs"] * 100, 2)
        for v in pooled.values()
    )
    check(
        "pooled_counts_reconcile",
        pooled_totals == direct and per_branch_ok,
        f"pooled defective counts {pooled_totals} match the dataset directly; per-branch "
        f"proportions recompute exactly (C {pooled['C']['fully_supported_of_answered_percent']}%, "
        f"D {pooled['D']['fully_supported_of_answered_percent']}%)",
    )
    check(
        "weighted_and_pooled_can_differ",
        conditional_example["differs"],
        f"synthetic case: weighted {conditional_example['weighted_fully_supported_share_percent']}% "
        f"vs pooled {conditional_example['pooled_fully_supported_of_answered_percent']}%",
    )

    archive = results / "stage15_1_archive"
    previous_path = next(archive.glob("main_analysis_results_pre15_1_*.json"), None)
    unchanged_estimates = None
    if previous_path is not None:
        previous = hotpotqa.read_json(previous_path)

        def estimates(source: dict) -> dict:
            out = {}
            for set_name in ("full_60", "sensitivity_55"):
                block = source[set_name]
                out[f"{set_name}:primary"] = block["primary_D_minus_C_not_fully_supported"]
                for outcome, item in block["companions_D_minus_C"].items():
                    out[f"{set_name}:companion:{outcome}"] = item
                for outcome, item in block["clean_utility_D_minus_C"].items():
                    out[f"{set_name}:clean:{outcome}"] = item
                for family, items in block["exploratory_contrasts"].items():
                    for outcome, item in items.items():
                        out[f"{set_name}:exploratory:{family}:{outcome}"] = item
                for condition, items in block["per_condition_D_minus_C"].items():
                    for outcome, item in items.items():
                        out[f"{set_name}:per_condition:{condition}:{outcome}"] = item
                out[f"{set_name}:levels_defective"] = block["branch_levels_defective"]
                out[f"{set_name}:levels_clean"] = block["branch_levels_clean"]
            return out

        unchanged_estimates = estimates(previous) == estimates(payload)
    check(
        "protocol_estimates_and_intervals_unchanged",
        unchanged_estimates is True,
        "every contrast, interval and branch level is identical to the pre-correction report"
        if unchanged_estimates
        else "no pre-correction report found to compare against",
    )

    # Protected inputs: compare against hashes recorded before this correction, or against
    # the stage 14 record where the file predates stage 15.
    stage14 = hotpotqa.read_json(results / "stage14_report.json")
    plan_manifest = hotpotqa.read_json(results / "main_plan" / "manifest.json")
    previous_report = next(archive.glob("stage15_report_pre15_1_*.json"), None)
    recorded = hotpotqa.read_json(previous_report)["outputs_sha256"] if previous_report else {}

    expected = {
        "results/main_analysis.jsonl": recorded.get("results/main_analysis.jsonl"),
        "results/main_post_retry_reviews.jsonl": recorded.get("results/main_post_retry_reviews.jsonl"),
        "results/main_answer_grounding_reviews.jsonl": recorded.get(
            "results/main_answer_grounding_reviews.jsonl"
        ),
        "results/stage15_acceptance.json": recorded.get("results/stage15_acceptance.json"),
        "results/main_post_retry_lookup_augmented.json": recorded.get(
            "results/main_post_retry_lookup_augmented.json"
        ),
        "results/main_run_index.jsonl": stage14["outputs"].get("results/main_run_index.jsonl"),
        "results/main_experiment_protocol_v3.md": stage14["protocol"]["sha256"],
        "results/main_sample_final.json": stage14["sample"]["sample_sha256"],
        "results/main_plan/manifest.json": stage14["plan"]["manifest_sha256"],
        "config/experiment.json": plan_manifest["binding"]["implementation_files"]["config/experiment.json"],
    }
    protected = {name: sha256_file(config.project_root / name) for name in expected}
    differing = [
        name for name, digest in expected.items() if digest is not None and protected[name] != digest
    ]
    unverifiable = [name for name, digest in expected.items() if digest is None]
    check(
        "protected_inputs_byte_identical",
        not differing and not unverifiable,
        f"{len(protected)} protected files match their recorded hashes"
        + (f"; differing: {differing}" if differing else "")
        + (f"; no recorded hash for: {unverifiable}" if unverifiable else ""),
    )

    report = {
        "stage": "stage15_validation",
        "generated_at_utc": analysis.utc_now(),
        "checks": checks,
        "status": "ok" if all(c["passed"] for c in checks) else "failed",
        "synthetic_examples": {
            "weighting": weighting,
            "missing_cell": missing,
            "weighted_vs_pooled_conditional": conditional_example,
            "undefined_ratio": undefined_example,
            "unclear_in_denominator": unclear_example,
        },
        "protected_input_hashes": protected,
    }
    hotpotqa.write_json(results / CHECKS_FILE, report)
    for item in checks:
        print(f"[{'ok' if item['passed'] else 'FAILED'}] {item['name']}: {item['detail']}")
    print(f"status: {report['status']}")
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
