"""Stage 15 steps 4-6: analysis dataset, frozen estimator and diagnostics.

Implements protocol v3 exactly:

* one row per planned coordinate, accepted labels expanded through their lookups;
* four mutually exclusive semantic categories for completed runs only;
* question-level aggregation - repeats averaged, the three defective conditions
  weighted one third each, branches compared through paired per-question
  differences;
* paired bootstrap of whole questions, 10,000 resamples, random.Random(42),
  95% percentile intervals.

Pooled run proportions are never substituted for the question-level estimator. They are
reported separately, as clearly labelled descriptive diagnostics.

    python tools/stage15_analysis.py

No provider API call is made and no coordinate is re-run.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

RUN_INDEX = "main_run_index.jsonl"
ANALYSIS_ROWS = "main_analysis.jsonl"
RESULTS_FILE = "main_analysis_results.json"
SUMMARY_FILE = "main_analysis_summary.md"
FIGURE_DIRNAME = "main_analysis_figures"
TABLE_DIRNAME = "main_analysis_tables"

CONTEXT_REVIEWS = "main_post_retry_reviews.jsonl"
ANSWER_REVIEWS = "main_answer_grounding_reviews.jsonl"
ANSWER_LOOKUP = "main_answer_grounding_lookup.json"
AUGMENTED_LOOKUP = "main_post_retry_lookup_augmented.json"
SAMPLE_FILE = "main_sample_final.json"
PROTOCOL = "main_experiment_protocol_v3.md"

BRANCHES = ("A", "B", "C", "D")
CONDITIONS = ("CLEAN", "PARTIAL", "EMPTY", "INCONSISTENT")
DEFECTIVE = ("PARTIAL", "EMPTY", "INCONSISTENT")

CAT_FULL = "fully_supported_answer"
CAT_NOT_FULL = "not_fully_supported_answer"
CAT_UNCLEAR = "unclear_answer"
CAT_ABSTAIN = "abstention_or_escalation"
CATEGORIES = (CAT_FULL, CAT_NOT_FULL, CAT_UNCLEAR, CAT_ABSTAIN)
NOT_FULL_LABELS = ("PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONFLICTED")

RESAMPLES = 10000
SEED = 42
QUESTION_ORDER_RULE = (
    "questions in ascending sample_position of results/main_sample_final.json (1..60), the frozen "
    "candidate order; the bootstrap resamples positions of that list"
)
PERCENTILE_RULE = (
    "percentile by linear interpolation between order statistics: with sorted values v and "
    "h = q*(n-1), the quantile is v[floor(h)] + (h - floor(h)) * (v[ceil(h)] - v[floor(h)]) "
    "(the numpy 'linear' convention)"
)
BOOTSTRAP_RULE = (
    "paired bootstrap of whole questions: each resample draws len(questions) question positions "
    "with replacement using random.Random(42); a sampled question carries all of its condition and "
    "branch cell means, so branches stay paired. Individual runs are never resampled. The same "
    "resample index sets are reused across outcomes and contrasts that share a question set"
)
SENSITIVITY_EXCLUSIONS = {
    "5ae532e955429908b632656f": 20,
    "5a7412b655429979e28828a1": 23,
    "5a8e4b7c5542990e94052ab7": 88,
    "5aba55f25542994dbf0198e0": 90,
    "5ab950bd55429970cfb8ea4c": 132,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- step 4: analysis dataset ------------------------------------------------------------


def build_dataset(config) -> dict:
    results = config.paths["results"]
    index_rows = read_jsonl(results / RUN_INDEX)
    sample = hotpotqa.read_json(results / SAMPLE_FILE)
    answer_lookup = hotpotqa.read_json(results / ANSWER_LOOKUP)
    context_lookup = hotpotqa.read_json(results / AUGMENTED_LOOKUP)
    answer_reviews = {r["case_sha256"]: r for r in read_jsonl(results / ANSWER_REVIEWS)}
    context_reviews = {r["context_sha256"]: r for r in read_jsonl(results / CONTEXT_REVIEWS)}

    case_of_run: dict[str, str] = {}
    for case_hash, instances in answer_lookup["by_case"].items():
        for instance in instances:
            case_of_run[instance["run_id"]] = case_hash
    context_of_run: dict[str, tuple[str, str]] = {}
    for case_hash, instances in context_lookup["by_case"].items():
        for instance in instances:
            context_of_run[instance["run_id"]] = (case_hash, instance["scope"])

    question_position = {q["question_id"]: q["sample_position"] for q in sample["questions"]}

    rows: list[dict] = []
    problems: list[str] = []
    for source in index_rows:
        run_id = source["run_id"]
        completed = source["record_status"] == "completed"
        answered = completed and source["terminal_outcome"] == "answered"

        case_hash = case_of_run.get(run_id)
        answer_review = answer_reviews.get(case_hash) if case_hash else None
        context_hash, context_scope = context_of_run.get(run_id, (None, None))
        context_review = context_reviews.get(context_hash) if context_hash else None

        if answered and answer_review is None:
            problems.append(f"{run_id}: answered run without an accepted grounding label")
        if not answered and case_hash is not None:
            problems.append(f"{run_id}: non-answered run mapped to a grounding case")
        if source.get("retried") and context_hash is None:
            problems.append(f"{run_id}: retried run without a post-retry context mapping")

        answer_support = answer_review["answer_support"] if answer_review else None
        if completed:
            if answered:
                if answer_support == "FULLY_SUPPORTED":
                    category = CAT_FULL
                elif answer_support in NOT_FULL_LABELS:
                    category = CAT_NOT_FULL
                elif answer_support == "UNCLEAR":
                    category = CAT_UNCLEAR
                else:
                    category = None
                    problems.append(f"{run_id}: unusable answer label {answer_support!r}")
            else:
                category = CAT_ABSTAIN
            semantic_status = "completed"
        else:
            category = None
            semantic_status = "missing_technical_failure"

        rows.append(
            {
                "coordinate": source["coordinate"],
                "run_id": run_id,
                "question_id": source["question_id"],
                "sample_position": question_position.get(source["question_id"]),
                "case_id": source["case_id"],
                "condition": source["condition"],
                "branch": source["branch"],
                "repeat": source["repeat"],
                "record_status": source["record_status"],
                "technical_status": source["status"],
                "terminal_outcome": source["terminal_outcome"],
                "semantic_status": semantic_status,
                "semantic_category": category,
                "answer_support": answer_support if answered else ("not_applicable" if completed else None),
                "explanation_support": (
                    answer_review["explanation_support"] if (answered and answer_review) else
                    ("not_applicable" if completed else None)
                ),
                "grounding_case_sha256": case_hash,
                "initial_reviewed_state": source["initial_reviewed_state"],
                "post_retry_reviewed_state": context_review["observed_state"] if context_review else None,
                "post_retry_context_sha256": context_hash,
                "post_retry_scope": context_scope,
                "retried": source.get("retried"),
                "retrieval_change_after_retry": source.get("retrieval_change_after_retry"),
                "answer": source.get("answer"),
                "returned_evidence_doc_ids": source.get("returned_evidence_doc_ids"),
                "citation_id_membership_valid": source.get("citation_id_membership_valid"),
                "generator_decision": source.get("generator_decision"),
                "final_context_sha256": source.get("final_context_sha256"),
                "searches": source.get("searches"),
                "api_calls": source.get("api_calls"),
                "api_attempts": source.get("api_attempts"),
                "token_usage": source.get("token_usage"),
                "latency_seconds": source.get("latency_seconds"),
                "any_policy_mismatch": source.get("any_policy_mismatch"),
                "any_policy_override": source.get("any_policy_override"),
                "proposed_actions": source.get("proposed_actions"),
                "executed_actions": source.get("executed_actions"),
                "expected_actions": source.get("expected_actions"),
                "first_evaluator_assessment": source.get("first_evaluator_assessment"),
                "second_evaluator_assessment": source.get("second_evaluator_assessment"),
            }
        )

    hotpotqa.write_jsonl(results / ANALYSIS_ROWS, rows)
    reconciliation = {
        "rows": len(rows),
        "completed": sum(1 for r in rows if r["record_status"] == "completed"),
        "technical_failures": sum(1 for r in rows if r["record_status"] != "completed"),
        "answered": sum(1 for r in rows if r["terminal_outcome"] == "answered"),
        "provider_attempts": sum(r["api_attempts"] or 0 for r in rows),
        "expected": {
            "rows": 2880,
            "completed": 2873,
            "technical_failures": 7,
            "answered": 1106,
            "provider_attempts": 6049,
        },
    }
    reconciliation["matches_expected"] = all(
        reconciliation[key] == value for key, value in reconciliation["expected"].items()
    )
    return {"rows": rows, "problems": problems, "reconciliation": reconciliation}


# --- step 5: the frozen estimator ----------------------------------------------------------


def cell_means(rows: list[dict]) -> dict:
    """Mean of the outcome indicators over completed repeats of every cell."""
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if row["semantic_status"] != "completed":
            continue
        buckets[(row["question_id"], row["condition"], row["branch"])].append(row)
    means = {}
    for key, cell in buckets.items():
        means[key] = {
            "n_completed": len(cell),
            **{
                category: sum(1 for r in cell if r["semantic_category"] == category) / len(cell)
                for category in CATEGORIES
            },
        }
    return means


def question_values(means: dict, questions: list[str], branch: str, outcome: str, conditions) -> dict:
    """Question-level value for one branch: equal weight over the given conditions."""
    values = {}
    for question in questions:
        cells = [means.get((question, condition, branch)) for condition in conditions]
        if any(cell is None for cell in cells):
            values[question] = None
            continue
        values[question] = sum(cell[outcome] for cell in cells) / len(cells)
    return values


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    if len(ordered) == 1:
        return ordered[0]
    h = q * (len(ordered) - 1)
    low = int(h)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (h - low) * (ordered[high] - ordered[low])


class Resampler:
    """Bootstrap index sets, generated once per question set and reused."""

    def __init__(self, resamples: int = RESAMPLES, seed: int = SEED):
        self.resamples = resamples
        self.seed = seed
        self._cache: dict[tuple, list[list[int]]] = {}

    def indices(self, questions: tuple[str, ...]) -> list[list[int]]:
        if questions not in self._cache:
            rng = random.Random(self.seed)
            size = len(questions)
            self._cache[questions] = [
                [rng.randrange(size) for _ in range(size)] for _ in range(self.resamples)
            ]
        return self._cache[questions]


def paired_contrast(
    means: dict,
    questions: list[str],
    branch_a: str,
    branch_b: str,
    outcome: str,
    conditions,
    resampler: Resampler,
) -> dict:
    """branch_a - branch_b on the question-level aggregate, with a paired bootstrap."""
    values_a = question_values(means, questions, branch_a, outcome, conditions)
    values_b = question_values(means, questions, branch_b, outcome, conditions)
    available = [q for q in questions if values_a[q] is not None and values_b[q] is not None]
    excluded = [
        {
            "question_id": q,
            "reason": (
                f"no completed run in a required cell for branch "
                f"{branch_a if values_a[q] is None else branch_b}"
            ),
        }
        for q in questions
        if values_a[q] is None or values_b[q] is None
    ]
    if not available:
        return {"available_questions": 0, "excluded_questions": excluded, "estimate": None}

    differences = [values_a[q] - values_b[q] for q in available]
    point = sum(differences) / len(differences)
    indices = resampler.indices(tuple(available))
    draws = [sum(differences[i] for i in draw) / len(draw) for draw in indices]
    return {
        "contrast": f"{branch_a} - {branch_b}",
        "outcome": outcome,
        "conditions": list(conditions),
        "available_questions": len(available),
        "excluded_questions": excluded,
        "mean_difference": point,
        "mean_difference_pp": round(point * 100, 2),
        "ci95_pp": [round(percentile(draws, 0.025) * 100, 2), round(percentile(draws, 0.975) * 100, 2)],
        "branch_rates_pp": {
            branch_a: round(sum(values_a[q] for q in available) / len(available) * 100, 2),
            branch_b: round(sum(values_b[q] for q in available) / len(available) * 100, 2),
        },
        "direction_note": (
            f"positive means branch {branch_a} has the higher {outcome} rate than branch {branch_b}"
        ),
    }


def aggregated_rate(means: dict, questions: list[str], branch: str, outcome: str, conditions) -> float | None:
    """Unrounded question-level rate of one outcome for one branch."""
    values = question_values(means, questions, branch, outcome, conditions)
    available = [values[q] for q in questions if values[q] is not None]
    return sum(available) / len(available) if available else None


def weighted_conditional(means: dict, questions: list[str], conditions) -> dict:
    """Ratio of question/condition-weighted rates - descriptive, not a pooled proportion.

    The denominator is the weighted answer rate: fully supported + not fully
    supported + unclear. Everything is computed from unrounded aggregates and
    rounded only for presentation; a zero denominator gives an undefined ratio.
    """
    table = {}
    for branch in BRANCHES:
        parts = {
            outcome: aggregated_rate(means, questions, branch, outcome, conditions)
            for outcome in (CAT_FULL, CAT_NOT_FULL, CAT_UNCLEAR)
        }
        if any(value is None for value in parts.values()):
            table[branch] = {
                "weighted_answer_rate_percent": None,
                "weighted_fully_supported_share_percent": None,
                "defined": False,
                "reason": "no available question-level value for this branch",
            }
            continue
        answered = sum(parts.values())
        defined = answered > 0
        table[branch] = {
            "weighted_answer_rate_percent": round(answered * 100, 2),
            "weighted_fully_supported_share_percent": (
                round(parts[CAT_FULL] / answered * 100, 2) if defined else None
            ),
            "defined": defined,
            "unrounded": {
                "weighted_answer_rate": answered,
                "weighted_fully_supported_rate": parts[CAT_FULL],
                "weighted_fully_supported_share": (parts[CAT_FULL] / answered) if defined else None,
            },
            "denominator_includes_unclear": True,
        }
        if not defined:
            table[branch]["reason"] = "weighted answer rate is zero; the ratio is undefined"
    return table


def pooled_conditional(rows: list[dict], questions: list[str], conditions) -> dict:
    """Pooled descriptive counts among observed runs; a different denominator again."""
    wanted = set(questions)
    table = {}
    for branch in BRANCHES:
        selected = [
            r
            for r in rows
            if r["branch"] == branch and r["condition"] in conditions and r["question_id"] in wanted
        ]
        completed = [r for r in selected if r["semantic_status"] == "completed"]
        answered = [r for r in completed if r["terminal_outcome"] == "answered"]
        fully = [r for r in answered if r["answer_support"] == "FULLY_SUPPORTED"]
        table[branch] = {
            "completed_runs": len(completed),
            "answered_runs": len(answered),
            "fully_supported_answers": len(fully),
            "answered_of_completed_percent": (
                round(len(answered) / len(completed) * 100, 2) if completed else None
            ),
            "fully_supported_of_answered_percent": (
                round(len(fully) / len(answered) * 100, 2) if answered else None
            ),
            "defined": bool(answered),
        }
        if not answered:
            table[branch]["reason"] = "no answered run; the conditional proportion is undefined"
    return table


def branch_levels(means: dict, questions: list[str], conditions, resampler: Resampler) -> dict:
    """Question-level rate of every outcome for every branch, with its own interval."""
    levels = {}
    for branch in BRANCHES:
        levels[branch] = {}
        for outcome in CATEGORIES:
            values = question_values(means, questions, branch, outcome, conditions)
            available = [q for q in questions if values[q] is not None]
            if not available:
                levels[branch][outcome] = None
                continue
            series = [values[q] for q in available]
            point = sum(series) / len(series)
            draws = [
                sum(series[i] for i in draw) / len(draw) for draw in resampler.indices(tuple(available))
            ]
            levels[branch][outcome] = {
                "rate_pp": round(point * 100, 2),
                "ci95_pp": [
                    round(percentile(draws, 0.025) * 100, 2),
                    round(percentile(draws, 0.975) * 100, 2),
                ],
                "available_questions": len(available),
            }
    return levels


def analysis_set(rows: list[dict], questions: list[str], label: str, resampler: Resampler) -> dict:
    means = cell_means(rows)
    primary = paired_contrast(means, questions, "D", "C", CAT_NOT_FULL, DEFECTIVE, resampler)
    companions = {
        outcome: paired_contrast(means, questions, "D", "C", outcome, DEFECTIVE, resampler)
        for outcome in (CAT_FULL, CAT_ABSTAIN, CAT_UNCLEAR)
    }
    clean = {
        outcome: paired_contrast(means, questions, "D", "C", outcome, ("CLEAN",), resampler)
        for outcome in CATEGORIES
    }
    exploratory = {
        f"{a}-{b}": {
            outcome: paired_contrast(means, questions, a, b, outcome, DEFECTIVE, resampler)
            for outcome in (CAT_NOT_FULL, CAT_FULL, CAT_ABSTAIN, CAT_UNCLEAR)
        }
        for a, b in (("B", "A"), ("C", "A"), ("D", "B"))
    }
    per_condition = {
        condition: {
            outcome: paired_contrast(means, questions, "D", "C", outcome, (condition,), resampler)
            for outcome in (CAT_NOT_FULL, CAT_FULL, CAT_ABSTAIN)
        }
        for condition in CONDITIONS
    }
    defective_levels = branch_levels(means, questions, DEFECTIVE, resampler)
    answer_conditional = weighted_conditional(means, questions, DEFECTIVE)
    return {
        "label": label,
        "questions": len(questions),
        "question_ids": questions,
        "answer_conditional_descriptive": {
            "label": "Ratio of question/condition-weighted rates - descriptive",
            "note": (
                "the ratio of two question-level aggregated rates on defective inputs, computed "
                "from unrounded values and rounded only for presentation. The denominator is the "
                "weighted answer rate (fully supported + not fully supported + unclear); a zero "
                "denominator is reported as undefined. This is not a pooled proportion among "
                "observed answers and it does not replace the protocol-v3 estimator"
            ),
            "by_branch": answer_conditional,
        },
        "pooled_conditional_descriptive": {
            "label": "Pooled proportions among observed runs - descriptive",
            "note": (
                "counts pooled over all completed runs of the defective conditions, ignoring the "
                "question-level weighting. Branches answer different subsets of runs, so a "
                "conditional proportion alone does not establish equal or superior answer quality, "
                "and it does not replace the protocol-v3 estimator"
            ),
            "conditions": list(DEFECTIVE),
            "by_branch": pooled_conditional(rows, questions, DEFECTIVE),
        },
        "branch_levels_defective": defective_levels,
        "branch_levels_clean": branch_levels(means, questions, ("CLEAN",), resampler),
        "primary_D_minus_C_not_fully_supported": primary,
        "companions_D_minus_C": companions,
        "clean_utility_D_minus_C": clean,
        "exploratory_contrasts": exploratory,
        "per_condition_D_minus_C": per_condition,
    }


# --- step 6: diagnostics ---------------------------------------------------------------------


def diagnostics(rows: list[dict]) -> dict:
    completed = [r for r in rows if r["semantic_status"] == "completed"]
    answered = [r for r in completed if r["terminal_outcome"] == "answered"]
    retried = [r for r in completed if r["retried"]]

    outcomes = defaultdict(lambda: defaultdict(Counter))
    for row in rows:
        key = row["terminal_outcome"] or row["technical_status"] or "unknown"
        outcomes[row["branch"]][row["condition"]][key] += 1

    typed_confusion: dict[str, Counter] = defaultdict(Counter)
    binary_confusion: dict[str, Counter] = defaultdict(Counter)
    for row in completed:
        assessment = row["first_evaluator_assessment"] or {}
        reviewed = row["initial_reviewed_state"]
        if "state" in assessment:
            typed_confusion[reviewed][str(assessment["state"])] += 1
        elif "sufficient" in assessment:
            binary_confusion["OK" if reviewed == "OK" else "non-OK"][str(assessment["sufficient"])] += 1

    steps_total = 0
    proposed_mismatch = 0
    executed_violation = 0
    by_branch = defaultdict(lambda: {"steps": 0, "proposed_mismatch": 0, "executed_violation": 0})
    for row in completed:
        proposed = row["proposed_actions"] or []
        expected = row["expected_actions"] or []
        executed = row["executed_actions"] or []
        for index, expect in enumerate(expected):
            if index >= len(proposed) or proposed[index] is None:
                continue
            steps_total += 1
            by_branch[row["branch"]]["steps"] += 1
            if proposed[index] != expect:
                proposed_mismatch += 1
                by_branch[row["branch"]]["proposed_mismatch"] += 1
            if index < len(executed) and executed[index] != expect:
                executed_violation += 1
                by_branch[row["branch"]]["executed_violation"] += 1

    restoration = Counter()
    for row in retried:
        state = row["post_retry_reviewed_state"]
        restoration[f"post_retry_{state}"] += 1
        if state == "OK":
            restoration[f"post_retry_OK_then_{row['semantic_category']}"] += 1

    citation = Counter(str(row["citation_id_membership_valid"]) for row in rows)
    citation_by_support = defaultdict(Counter)
    for row in answered:
        citation_by_support[row["answer_support"]][str(row["citation_id_membership_valid"])] += 1

    usage = Counter()
    latencies = []
    for row in rows:
        tokens = row["token_usage"] or {}
        for key in ("input_tokens", "output_tokens", "total_tokens", "cached_tokens", "calls_with_usage"):
            usage[key] += tokens.get(key, 0)
        usage["api_calls"] += row["api_calls"] or 0
        usage["api_attempts"] += row["api_attempts"] or 0
        if row["latency_seconds"] is not None:
            latencies.append(row["latency_seconds"])

    return {
        "denominators": {
            "planned_coordinates": len(rows),
            "completed_runs": len(completed),
            "technical_failures": len(rows) - len(completed),
            "answered_runs": len(answered),
            "retried_completed_runs": len(retried),
        },
        "terminal_outcomes_by_branch_and_condition": {
            branch: {condition: dict(counter) for condition, counter in conditions.items()}
            for branch, conditions in outcomes.items()
        },
        "initial_evaluator_typed_confusion": {
            "note": (
                "rows: accepted reviewed state of the initial context; columns: the typed grader's "
                "first verdict. Completed runs of branches B and D only"
            ),
            "table": {k: dict(v) for k, v in typed_confusion.items()},
        },
        "initial_evaluator_binary_confusion": {
            "note": (
                "rows: accepted reviewed state collapsed to OK vs non-OK; columns: the binary "
                "grader's first sufficiency verdict. Completed runs of branches A and C only"
            ),
            "table": {k: dict(v) for k, v in binary_confusion.items()},
        },
        "policy": {
            "note": (
                "proposed-action mismatch counts how often the LLM's proposed action differed from "
                "the policy action, in every branch. What happened next depends on the branch by "
                "design: A and B execute the proposal, so a divergent execution there is the "
                "design, not a defect; C and D execute the policy action, so any divergence there "
                "would be a contract violation. Enforced compliance is not evidence that the "
                "evaluator's state assessment was correct"
            ),
            "steps_with_a_proposal": steps_total,
            "proposed_action_mismatches": proposed_mismatch,
            "executions_differing_from_the_policy_action": executed_violation,
            "contract_violations_in_C_and_D": sum(
                v["executed_violation"] for branch, v in by_branch.items() if branch in ("C", "D")
            ),
            "policy_divergent_executions_by_design_in_A_and_B": sum(
                v["executed_violation"] for branch, v in by_branch.items() if branch in ("A", "B")
            ),
            "by_branch": {
                branch: {
                    "steps_with_a_proposal": v["steps"],
                    "proposed_action_mismatches": v["proposed_mismatch"],
                    "executions_differing_from_the_policy_action": v["executed_violation"],
                }
                for branch, v in by_branch.items()
            },
        },
        "retry": {
            "note": (
                "a changed document set is a retrieval change, not recovery; an OK post-retry "
                "context is reported separately from what the run then produced"
            ),
            "retried_completed_runs": len(retried),
            "retry_rate_of_completed_pp": round(len(retried) / len(completed) * 100, 2),
            "retrieval_change_after_retry": dict(
                Counter(row["retrieval_change_after_retry"] for row in retried)
            ),
            "post_retry_states_and_following_outcome": dict(restoration),
        },
        "citation_id_validity": {
            "note": "structural measure, independent of grounding; invalid citations are retained",
            "counts": dict(citation),
            "by_answer_support": {k: dict(v) for k, v in citation_by_support.items()},
        },
        "usage": {
            "provider_attempts": usage["api_attempts"],
            "provider_calls": usage["api_calls"],
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "total_tokens": usage["total_tokens"],
            "cached_tokens": usage["cached_tokens"],
            "calls_with_usage": usage["calls_with_usage"],
            "runs_with_latency": len(latencies),
            "latency_seconds_mean": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "latency_seconds_total": round(sum(latencies), 1),
            "note": "no monetary estimate is given; no verified pricing evidence is on hand",
        },
    }
