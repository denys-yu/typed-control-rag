"""Stage 15 driver: build the dataset, run the frozen estimator, write the outputs.

    python tools/stage15_run.py

Offline. No provider call, no coordinate re-run, no frozen input modified.
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
import stage15_outputs as outputs

CONCLUSIONS_TEMPLATE = (
    "On initially defective inputs, branch D (typed state plus a programmatic contract) produced "
    "fewer not-fully-supported answers than branch C (binary grade plus rules), {primary:+.2f} pp "
    "(95% interval [{primary_lo:+.2f}, {primary_hi:+.2f}] pp), and fewer fully supported answers, "
    "{full_diff:+.2f} pp (95% interval [{full_lo:+.2f}, {full_hi:+.2f}] pp), alongside more "
    "abstentions or escalations, {abstain_diff:+.2f} pp (95% interval "
    "[{abstain_lo:+.2f}, {abstain_hi:+.2f}] pp). {direction} This establishes a trade-off in the "
    "evaluated setting. {trade} On CLEAN inputs, D produced {clean_full:+.2f} pp fully supported "
    "answers relative to C and abstained or escalated {clean_abstain:+.2f} pp more often, which is "
    "the utility cost of the stricter branch; whether that cost is acceptable was not established, "
    "because no acceptance threshold and no non-inferiority margin were specified. {sensitivity} "
    "The combined category, not-fully-supported, is PARTIALLY_SUPPORTED plus UNSUPPORTED plus "
    "CONFLICTED against the context the generator actually received; it does not by itself mean an "
    "answer is factually incorrect or hallucinated. No significance test, non-inferiority margin "
    "or power claim is made, and these are descriptive interval estimates over 60 selected "
    "questions."
)


def describe(full: dict, sens: dict) -> str:
    primary = full["primary_D_minus_C_not_fully_supported"]
    supported = full["companions_D_minus_C"][analysis.CAT_FULL]
    clean_full = full["clean_utility_D_minus_C"][analysis.CAT_FULL]
    clean_abstain = full["clean_utility_D_minus_C"][analysis.CAT_ABSTAIN]
    sens_primary = sens["primary_D_minus_C_not_fully_supported"]

    crosses_zero = primary["ci95_pp"][0] <= 0 <= primary["ci95_pp"][1]
    if crosses_zero:
        direction = (
            "The interval for the primary measure includes zero, so this experiment does not "
            "establish a difference in propagation between D and C."
        )
    elif primary["mean_difference_pp"] < 0:
        direction = "The interval for the primary measure stays below zero."
    else:
        direction = "The interval for the primary measure stays above zero."

    if supported["mean_difference_pp"] < 0 and primary["mean_difference_pp"] < 0:
        trade = "Both answer categories are lower under D, and abstention or escalation is higher."
    elif supported["mean_difference_pp"] > 0 and primary["mean_difference_pp"] < 0:
        trade = "D lowered not-fully-supported answers while also producing more fully supported ones."
    elif supported["mean_difference_pp"] < 0 and primary["mean_difference_pp"] > 0:
        trade = "D produced fewer fully supported answers and more not-fully-supported ones."
    else:
        trade = "Both rates moved in the same upward direction, so D answered more often overall."

    same_sign = (sens_primary["mean_difference_pp"] < 0) == (primary["mean_difference_pp"] < 0)
    sens_crosses = sens_primary["ci95_pp"][0] <= 0 <= sens_primary["ci95_pp"][1]
    sensitivity = (
        "The 55-question sensitivity subset gives {v:+.2f} pp [{lo:+.2f}, {hi:+.2f}] on the primary "
        "measure, {agreement}."
    ).format(
        v=sens_primary["mean_difference_pp"],
        lo=sens_primary["ci95_pp"][0],
        hi=sens_primary["ci95_pp"][1],
        agreement=(
            "the same direction and the same qualitative conclusion as the full sample"
            if same_sign and sens_crosses == crosses_zero
            else "a different qualitative reading from the full sample, which is reported as such"
        ),
    )
    pooled = full["pooled_conditional_descriptive"]["by_branch"]
    trade = (
        trade
        + " Two descriptive conditional views are reported beside it, with different denominators. "
        "Pooled over observed runs on defective inputs, "
        f"{pooled['D']['fully_supported_of_answered_percent']:.2f}% of D's answers and "
        f"{pooled['C']['fully_supported_of_answered_percent']:.2f}% of C's answers are fully "
        f"supported, while D answered {pooled['D']['answered_of_completed_percent']:.2f}% of its "
        f"completed runs against {pooled['C']['answered_of_completed_percent']:.2f}% for C. "
        "Because the branches answer different subsets of runs, these conditional proportions do "
        "not establish improved support among emitted answers and do not isolate the mechanism "
        "behind the aggregate differences."
    )
    abstain = full["companions_D_minus_C"][analysis.CAT_ABSTAIN]
    return CONCLUSIONS_TEMPLATE.format(
        primary=primary["mean_difference_pp"],
        primary_lo=primary["ci95_pp"][0],
        primary_hi=primary["ci95_pp"][1],
        abstain_diff=abstain["mean_difference_pp"],
        abstain_lo=abstain["ci95_pp"][0],
        abstain_hi=abstain["ci95_pp"][1],
        full_diff=supported["mean_difference_pp"],
        full_lo=supported["ci95_pp"][0],
        full_hi=supported["ci95_pp"][1],
        direction=direction,
        trade=trade,
        clean_full=clean_full["mean_difference_pp"],
        clean_abstain=clean_abstain["mean_difference_pp"],
        sensitivity=sensitivity,
    )


LIMITATIONS = [
    "One model (`gpt-4o-mini-2024-07-18`), one dataset (HotpotQA dev/distractor), one retriever "
    "and one corpus: branch effects are not separable from this model's habits.",
    "The 60 questions are those whose gold evidence this retriever reaches in the normal top-5 and "
    "whose four fault variants a reviewer accepted; 60 is a practical scope decision, not a "
    "powered sample size.",
    "Semantic labels were accepted after data collection under the existing rubric, by researcher "
    "acceptance of prepared proposals rather than an independent second review, so no inter-rater "
    "reliability is claimed.",
    "The CLEAN utility loss is measured but its acceptability is not established: no acceptance "
    "threshold and no non-inferiority margin were specified in the protocol.",
    "Two annotation conventions (G-1 identifier granularity, K-1 kinship and spouse slots) were "
    "fixed before data collection but after the pilot; the predeclared 55-question subset exists "
    "to show how much the conclusions depend on them.",
    "Seven coordinates failed technically in total; three of those failures occurred after a "
    "retry. All seven are missing from the semantic analysis and are never imputed; the three "
    "post-retry ones additionally contribute retrieval diagnostics only.",
    "Intervals are descriptive bootstrap intervals over questions; repeats and conditions are "
    "dependent observations inside a question and are aggregated before any comparison.",
    "A changed document set after a retry is a retrieval property, not recovery, and an enforced "
    "policy action is not evidence that the evaluator's state assessment was correct.",
]


def main() -> int:
    config = load_config()
    results = config.paths["results"]

    dataset = analysis.build_dataset(config)
    if dataset["problems"]:
        for problem in dataset["problems"][:20]:
            print(f"PROBLEM {problem}")
        raise SystemExit(f"{len(dataset['problems'])} dataset problems; analysis not run")
    rows = dataset["rows"]

    sample = hotpotqa.read_json(results / analysis.SAMPLE_FILE)
    ordered_questions = [
        q["question_id"] for q in sorted(sample["questions"], key=lambda item: item["sample_position"])
    ]
    sensitivity_questions = [
        q for q in ordered_questions if q not in analysis.SENSITIVITY_EXCLUSIONS
    ]
    resampler = analysis.Resampler()
    full = analysis.analysis_set(rows, ordered_questions, "full_60", resampler)
    sens = analysis.analysis_set(rows, sensitivity_questions, "sensitivity_55", resampler)
    diag = analysis.diagnostics(rows)

    payload = {
        "stage": "stage15_analysis",
        "generated_at_utc": analysis.utc_now(),
        "author": "Denys Yuvzhenko",
        "protocol": {
            "file": f"results/{analysis.PROTOCOL}",
            "sha256": sha256_file(results / analysis.PROTOCOL),
        },
        "estimator": {
            "aggregation": (
                "1) average completed repeats within question x condition x branch; 2) within each "
                "question and branch, weight PARTIAL, EMPTY and INCONSISTENT one third each; "
                "3) paired per-question branch difference; 4) mean of those differences over "
                "available questions"
            ),
            "question_order_rule": analysis.QUESTION_ORDER_RULE,
            "bootstrap_rule": analysis.BOOTSTRAP_RULE,
            "percentile_rule": analysis.PERCENTILE_RULE,
            "resamples": analysis.RESAMPLES,
            "seed": analysis.SEED,
            "availability_rule": (
                "a cell is available when it has at least one completed run; if a required cell is "
                "unavailable for either branch, that question is dropped from that paired "
                "comparison only, and the exclusion is reported. Nothing is imputed"
            ),
            "units": "differences in percentage points; rates as percentages of completed runs",
            "pooled_rates_note": (
                "pooled run proportions are never substituted for this estimator; they are "
                "reported separately as clearly labelled descriptive diagnostics, beside the "
                "ratio of question/condition-weighted rates"
            ),
        },
        "dataset_reconciliation": dataset["reconciliation"],
        "sensitivity_definition": {
            "excluded_question_ids": analysis.SENSITIVITY_EXCLUSIONS,
            "questions": len(sensitivity_questions),
            "note": "same runs, no additional provider calls; predeclared in protocol v3 section 3.7",
        },
        "full_60": full,
        "sensitivity_55": sens,
        "diagnostics": diag,
        "conclusions": describe(full, sens),
        "limitations": LIMITATIONS,
        "provider_calls": 0,
        "coordinate_reruns": 0,
    }

    tables = outputs.write_tables(results, full, sens, diag)
    figures = outputs.write_figures(results, full)
    payload["tables"] = [f"{analysis.TABLE_DIRNAME}/{name}" for name in tables]
    payload["figures"] = figures

    hotpotqa.write_json(results / analysis.RESULTS_FILE, payload)
    outputs.write_summary(results / analysis.SUMMARY_FILE, payload)

    primary = full["primary_D_minus_C_not_fully_supported"]
    supported = full["companions_D_minus_C"][analysis.CAT_FULL]
    print(f"rows                 : {dataset['reconciliation']['rows']} "
          f"(reconciled: {dataset['reconciliation']['matches_expected']})")
    print(f"primary D-C notfull  : {primary['mean_difference_pp']:+.2f} pp {primary['ci95_pp']} "
          f"over {primary['available_questions']} questions")
    print(f"companion D-C full   : {supported['mean_difference_pp']:+.2f} pp {supported['ci95_pp']}")
    print(f"sensitivity primary  : {sens['primary_D_minus_C_not_fully_supported']['mean_difference_pp']:+.2f} pp "
          f"{sens['primary_D_minus_C_not_fully_supported']['ci95_pp']}")
    print(f"tables/figures       : {payload['tables']} {figures['files']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
