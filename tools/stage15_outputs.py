"""Stage 15: CSV tables, SVG figures and the analysis summary.

Everything here reads the computed results; no estimate is recalculated with a
different rule. Figures use the protocol's question-level aggregates, never
pooled run rates.
"""

from __future__ import annotations

import csv
from pathlib import Path

from stage15_analysis import (
    BRANCHES,
    CAT_ABSTAIN,
    CAT_FULL,
    CAT_NOT_FULL,
    CAT_UNCLEAR,
    CONDITIONS,
    FIGURE_DIRNAME,
    TABLE_DIRNAME,
)

CATEGORY_LABELS = {
    CAT_FULL: "fully supported answer",
    CAT_NOT_FULL: "not fully supported answer",
    CAT_UNCLEAR: "unclear answer",
    CAT_ABSTAIN: "abstention or escalation",
}
COLOURS = {CAT_FULL: "#2f6f4e", CAT_NOT_FULL: "#a3403c", CAT_UNCLEAR: "#b08a2e", CAT_ABSTAIN: "#41618c"}


# --- tables --------------------------------------------------------------------------


def write_tables(results: Path, full: dict, sensitivity: dict, diag: dict) -> list[str]:
    directory = results / TABLE_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    path = directory / "branch_outcomes.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["analysis_set", "input_group", "branch", "outcome", "rate_pp", "ci95_low_pp", "ci95_high_pp", "questions"]
        )
        for name, payload in (("full_60", full), ("sensitivity_55", sensitivity)):
            for group, key in (("defective", "branch_levels_defective"), ("clean", "branch_levels_clean")):
                for branch, outcomes in payload[key].items():
                    for outcome, value in outcomes.items():
                        if value:
                            writer.writerow(
                                [name, group, branch, outcome, value["rate_pp"], *value["ci95_pp"], value["available_questions"]]
                            )
    written.append(path.name)

    path = directory / "contrasts.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "analysis_set",
                "family",
                "contrast",
                "conditions",
                "outcome",
                "difference_pp",
                "ci95_low_pp",
                "ci95_high_pp",
                "questions",
            ]
        )

        def emit(name: str, family: str, item: dict | None) -> None:
            if not item or item.get("available_questions", 0) == 0:
                return
            writer.writerow(
                [
                    name,
                    family,
                    item["contrast"],
                    "+".join(item["conditions"]),
                    item["outcome"],
                    item["mean_difference_pp"],
                    *item["ci95_pp"],
                    item["available_questions"],
                ]
            )

        for name, payload in (("full_60", full), ("sensitivity_55", sensitivity)):
            emit(name, "primary", payload["primary_D_minus_C_not_fully_supported"])
            for item in payload["companions_D_minus_C"].values():
                emit(name, "primary_companion", item)
            for item in payload["clean_utility_D_minus_C"].values():
                emit(name, "clean_utility", item)
            for family, items in payload["exploratory_contrasts"].items():
                for item in items.values():
                    emit(name, f"exploratory_{family}", item)
            for condition, items in payload["per_condition_D_minus_C"].items():
                for item in items.values():
                    emit(name, f"per_condition_{condition}", item)
    written.append(path.name)

    path = directory / "terminal_outcomes.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["branch", "condition", "outcome_or_status", "runs"])
        for branch, conditions in sorted(diag["terminal_outcomes_by_branch_and_condition"].items()):
            for condition, counts in sorted(conditions.items()):
                for key, value in sorted(counts.items()):
                    writer.writerow([branch, condition, key, value])
    written.append(path.name)
    return written


# --- figures -------------------------------------------------------------------------


def _header(width: int, height: int, title: str, subtitle: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica,Arial,sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="24" y="34" font-size="18" font-weight="600" fill="#111">{title}</text>',
        f'<text x="24" y="56" font-size="12" fill="#555">{subtitle}</text>',
    ]


def write_figures(results: Path, full: dict) -> dict:
    directory = results / FIGURE_DIRNAME
    directory.mkdir(parents=True, exist_ok=True)

    width, height, left, top, bar_h, gap, scale = 920, 380, 150, 92, 38, 24, 620
    lines = _header(
        width,
        height,
        "Branch outcome composition on initially defective inputs",
        "Question-level aggregates: repeats averaged, then PARTIAL, EMPTY and INCONSISTENT weighted one third each (60 questions)",
    )
    for position, branch in enumerate(BRANCHES):
        y = top + position * (bar_h + gap)
        x = float(left)
        lines.append(
            f'<text x="{left - 16}" y="{y + bar_h * 0.62:.0f}" font-size="13" text-anchor="end" fill="#111">Branch {branch}</text>'
        )
        for category in (CAT_FULL, CAT_NOT_FULL, CAT_UNCLEAR, CAT_ABSTAIN):
            value = full["branch_levels_defective"][branch][category]
            rate = value["rate_pp"] if value else 0.0
            w = rate / 100 * scale
            if w > 0.5:
                lines.append(
                    f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{COLOURS[category]}"/>'
                )
                if w > 44:
                    lines.append(
                        f'<text x="{x + w / 2:.1f}" y="{y + bar_h * 0.62:.0f}" font-size="12" fill="#fff" '
                        f'text-anchor="middle">{rate:.1f}</text>'
                    )
            x += w
    legend_y = top + len(BRANCHES) * (bar_h + gap) + 4
    for position, category in enumerate((CAT_FULL, CAT_NOT_FULL, CAT_UNCLEAR, CAT_ABSTAIN)):
        x = left + (position % 2) * 330
        y = legend_y + (position // 2) * 22
        lines.append(f'<rect x="{x}" y="{y}" width="12" height="12" fill="{COLOURS[category]}"/>')
        lines.append(f'<text x="{x + 18}" y="{y + 11}" font-size="12" fill="#333">{CATEGORY_LABELS[category]}</text>')
    lines.append(
        f'<text x="24" y="{height - 12}" font-size="11" fill="#777">Percentages of completed runs within each cell. '
        "Technical failures are excluded here and reported separately.</text>"
    )
    lines.append("</svg>")
    figure1 = directory / "figure1_branch_outcome_composition.svg"
    figure1.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    entries = [
        ("D - C, not fully supported (defective)", full["primary_D_minus_C_not_fully_supported"]),
        ("D - C, fully supported (defective)", full["companions_D_minus_C"][CAT_FULL]),
        ("D - C, abstention/escalation (defective)", full["companions_D_minus_C"][CAT_ABSTAIN]),
        ("D - C, fully supported (CLEAN)", full["clean_utility_D_minus_C"][CAT_FULL]),
        ("D - C, abstention/escalation (CLEAN)", full["clean_utility_D_minus_C"][CAT_ABSTAIN]),
    ]
    values = [v for _, item in entries for v in (item["mean_difference_pp"], *item["ci95_pp"])] + [0.0]
    low, high = min(values), max(values)
    span = max(high - low, 1.0)
    low, high = low - span * 0.15, high + span * 0.15
    width, height, left, top, row_h, plot_w = 960, 340, 330, 96, 42, 460
    lines = _header(
        width,
        height,
        "Primary effect estimates and CLEAN utility cost",
        "Paired per-question differences in percentage points with 95% bootstrap intervals (10,000 resamples of whole questions)",
    )

    def to_x(value: float) -> float:
        return left + (value - low) / (high - low) * plot_w

    zero = to_x(0.0)
    lines.append(
        f'<line x1="{zero:.1f}" y1="{top - 16}" x2="{zero:.1f}" y2="{top + len(entries) * row_h - 12}" '
        'stroke="#bbb" stroke-dasharray="4 3"/>'
    )
    for position, (label, item) in enumerate(entries):
        y = top + position * row_h
        lo, hi = item["ci95_pp"]
        point = item["mean_difference_pp"]
        colour = "#a3403c" if point > 0 else "#2f6f4e"
        lines.append(f'<text x="{left - 16}" y="{y + 4}" font-size="12" text-anchor="end" fill="#111">{label}</text>')
        lines.append(
            f'<line x1="{to_x(lo):.1f}" y1="{y}" x2="{to_x(hi):.1f}" y2="{y}" stroke="{colour}" stroke-width="2"/>'
        )
        for edge in (lo, hi):
            lines.append(
                f'<line x1="{to_x(edge):.1f}" y1="{y - 6}" x2="{to_x(edge):.1f}" y2="{y + 6}" stroke="{colour}" stroke-width="2"/>'
            )
        lines.append(f'<circle cx="{to_x(point):.1f}" cy="{y}" r="5" fill="{colour}"/>')
        lines.append(
            f'<text x="{left + plot_w + 18}" y="{y + 4}" font-size="12" fill="#333">{point:+.1f} pp  [{lo:+.1f}, {hi:+.1f}]</text>'
        )
    for tick in (low, 0.0, high):
        lines.append(
            f'<text x="{to_x(tick):.1f}" y="{top + len(entries) * row_h + 8}" font-size="11" fill="#777" '
            f'text-anchor="middle">{tick:+.0f} pp</text>'
        )
    lines.append(
        f'<text x="24" y="{height - 12}" font-size="11" fill="#777">Positive means branch D has the higher rate. '
        "Intervals are descriptive; no significance test, non-inferiority margin or power claim is made.</text>"
    )
    lines.append("</svg>")
    figure2 = directory / "figure2_effect_estimates.svg"
    figure2.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    return {
        "files": [f"{FIGURE_DIRNAME}/{figure1.name}", f"{FIGURE_DIRNAME}/{figure2.name}"],
        "format": "SVG only",
        "png_not_produced": (
            "matplotlib is not installed in this environment and adding a plotting dependency for "
            "two figures is out of scope for this stage; both figures are vector SVG and can be "
            "rasterised by any browser or converter"
        ),
        "source_of_values": "the protocol's question-level aggregated estimates, not pooled run rates",
    }


# --- summary -------------------------------------------------------------------------


def _fmt(value: float | None) -> str:
    """Percentages for presentation; an undefined ratio is shown as such."""
    return "undefined" if value is None else f"{value:.2f}"


def _contrast_line(label: str, item: dict) -> str:
    lo, hi = item["ci95_pp"]
    return (
        f"| {label} | {item['mean_difference_pp']:+.2f} | [{lo:+.2f}, {hi:+.2f}] | "
        f"{item['available_questions']} |"
    )


def write_summary(path: Path, payload: dict) -> None:
    full = payload["full_60"]
    sens = payload["sensitivity_55"]
    diag = payload["diagnostics"]
    recon = payload["dataset_reconciliation"]
    primary = full["primary_D_minus_C_not_fully_supported"]
    companion_full = full["companions_D_minus_C"][CAT_FULL]
    companion_abstain = full["companions_D_minus_C"][CAT_ABSTAIN]
    levels = full["branch_levels_defective"]
    clean_levels = full["branch_levels_clean"]

    lines = [
        "# Main experiment - analysis under protocol v3",
        "",
        "Author: Denys Yuvzhenko",
        "",
        "Single model (`gpt-4o-mini-2024-07-18`), single dataset (HotpotQA dev/distractor), one "
        "retriever and one reviewed, selected sample of 60 questions. Nothing here generalises "
        "beyond that. Semantic labels were accepted after data collection under the existing "
        "rubric; they are not preregistered.",
        "",
        "## 1. Coverage and technical missingness",
        "",
        f"- Planned coordinates: **{recon['rows']}**; completed: **{recon['completed']}**; "
        f"technical failures: **{recon['technical_failures']}** (all `incomplete_response: "
        "max_output_tokens`, left missing, never re-run or replaced).",
        "- Seven coordinates failed technically in total; three of those failures occurred after a "
        "retry. Those three contribute retrieval diagnostics only, and their semantic outcomes "
        "remain missing like the other four.",
        f"- Answered runs: **{recon['answered']}**; provider attempts: **{recon['provider_attempts']}**.",
        f"- Accepted labels expanded through their lookups: 347 grounding cases -> "
        f"{recon['answered']} answered runs; 335 post-retry contexts -> "
        f"{diag['retry']['retried_completed_runs']} completed retry instances and 3 "
        "technical-failure retry instances, 1,027 retry instances in total.",
        "- Semantic rates below use **completed runs** as their denominator; technical missingness "
        "is reported against all planned coordinates.",
        "- The accepted grounding labels contain no `UNCLEAR` case, so the unclear-answer category "
        "is defined by the protocol but empty in this dataset; it is still reported as its own "
        "column rather than folded into any other category.",
        "",
        "## 2. Primary contrast: D versus C on initially defective inputs",
        "",
        "Question-level estimator: repeats averaged within each question x condition x branch cell, "
        "the three defective conditions weighted one third each, then paired per-question "
        "differences averaged over questions. Intervals are 95% percentile bootstrap intervals from "
        "10,000 resamples of whole questions (seed 42).",
        "",
        "| Contrast (D - C, defective inputs) | Difference (pp) | 95% interval | Questions |",
        "| --- | ---: | :---: | ---: |",
        _contrast_line("Not fully supported answers (primary)", primary),
        _contrast_line("Fully supported answers", companion_full),
        _contrast_line("Abstention or escalation", companion_abstain),
        _contrast_line("Unclear answers", full["companions_D_minus_C"][CAT_UNCLEAR]),
        "",
        "Branch levels on defective inputs (same aggregation, percentage points):",
        "",
        "| Branch | Fully supported | Not fully supported | Unclear | Abstention/escalation |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for branch in BRANCHES:
        row = levels[branch]
        lines.append(
            f"| {branch} | {row[CAT_FULL]['rate_pp']:.2f} | {row[CAT_NOT_FULL]['rate_pp']:.2f} | "
            f"{row[CAT_UNCLEAR]['rate_pp']:.2f} | {row[CAT_ABSTAIN]['rate_pp']:.2f} |"
        )
    lines += [
        "",
        "### Two descriptive conditional views (neither replaces the estimator above)",
        "",
        "**Ratio of question/condition-weighted rates - descriptive.** Computed from unrounded "
        "question-level aggregates on defective inputs; the denominator is the weighted answer rate "
        "(fully supported + not fully supported + unclear).",
        "",
        "| Branch | Weighted answer rate (%) | Weighted fully supported share (%) |",
        "| --- | ---: | ---: |",
    ] + [
        (
            f"| {branch} | {_fmt(full['answer_conditional_descriptive']['by_branch'][branch]['weighted_answer_rate_percent'])} | "
            f"{_fmt(full['answer_conditional_descriptive']['by_branch'][branch]['weighted_fully_supported_share_percent'])} |"
        )
        for branch in BRANCHES
    ] + [
        "",
        "**Pooled proportions among observed runs - descriptive.** Counts pooled over the completed "
        "runs of the three defective conditions, without question-level weighting.",
        "",
        "| Branch | Completed runs | Answered runs | Fully supported answers | Answered / completed (%) | Fully supported / answered (%) |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ] + [
        (
            f"| {branch} | {row['completed_runs']} | {row['answered_runs']} | {row['fully_supported_answers']} | "
            f"{_fmt(row['answered_of_completed_percent'])} | {_fmt(row['fully_supported_of_answered_percent'])} |"
        )
        for branch, row in ((b, full["pooled_conditional_descriptive"]["by_branch"][b]) for b in BRANCHES)
    ] + [
        "",
        "These are two distinct descriptive diagnostics with different denominators, and neither "
        "replaces the protocol-v3 question-level estimator. Branches answer different subsets of "
        "runs, so a conditional proportion on its own does not establish equal or superior answer "
        "quality. Levels are percentages; contrasts elsewhere are differences in percentage points.",
    ] + [
        "",
        "## 3. CLEAN utility",
        "",
        "| Branch | Fully supported | Not fully supported | Unclear | Abstention/escalation |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for branch in BRANCHES:
        row = clean_levels[branch]
        lines.append(
            f"| {branch} | {row[CAT_FULL]['rate_pp']:.2f} | {row[CAT_NOT_FULL]['rate_pp']:.2f} | "
            f"{row[CAT_UNCLEAR]['rate_pp']:.2f} | {row[CAT_ABSTAIN]['rate_pp']:.2f} |"
        )
    lines += [
        "",
        "| Contrast (D - C, CLEAN inputs) | Difference (pp) | 95% interval | Questions |",
        "| --- | ---: | :---: | ---: |",
        _contrast_line("Fully supported answers", full["clean_utility_D_minus_C"][CAT_FULL]),
        _contrast_line("Abstention or escalation", full["clean_utility_D_minus_C"][CAT_ABSTAIN]),
        _contrast_line("Not fully supported answers", full["clean_utility_D_minus_C"][CAT_NOT_FULL]),
        "",
        "## 4. Per-condition breakdown (D - C)",
        "",
        "| Condition | Not fully supported (pp) | Fully supported (pp) | Abstention/escalation (pp) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for condition in CONDITIONS:
        item = full["per_condition_D_minus_C"][condition]
        lines.append(
            f"| {condition} | {item[CAT_NOT_FULL]['mean_difference_pp']:+.2f} "
            f"[{item[CAT_NOT_FULL]['ci95_pp'][0]:+.2f}, {item[CAT_NOT_FULL]['ci95_pp'][1]:+.2f}] | "
            f"{item[CAT_FULL]['mean_difference_pp']:+.2f} | {item[CAT_ABSTAIN]['mean_difference_pp']:+.2f} |"
        )
    lines += [
        "",
        "## 5. Exploratory contrasts (defective inputs)",
        "",
        "Labelled exploratory: they carry no confirmatory claim.",
        "",
        "| Contrast | Not fully supported (pp) | Fully supported (pp) | Abstention/escalation (pp) |",
        "| --- | ---: | ---: | ---: |",
    ]
    for family, items in full["exploratory_contrasts"].items():
        lines.append(
            f"| {items[CAT_NOT_FULL]['contrast']} | "
            f"{items[CAT_NOT_FULL]['mean_difference_pp']:+.2f} "
            f"[{items[CAT_NOT_FULL]['ci95_pp'][0]:+.2f}, {items[CAT_NOT_FULL]['ci95_pp'][1]:+.2f}] | "
            f"{items[CAT_FULL]['mean_difference_pp']:+.2f} | {items[CAT_ABSTAIN]['mean_difference_pp']:+.2f} |"
        )
    sens_primary = sens["primary_D_minus_C_not_fully_supported"]
    lines += [
        "",
        "## 6. Predeclared sensitivity analysis (55 questions)",
        "",
        "The same runs, excluding the five questions whose sample membership depends on the stage 13 "
        "conventions G-1 and K-1 or on a single ordinary-reading call.",
        "",
        "| Contrast (D - C, defective inputs) | Difference (pp) | 95% interval | Questions |",
        "| --- | ---: | :---: | ---: |",
        _contrast_line("Not fully supported answers (primary)", sens_primary),
        _contrast_line("Fully supported answers", sens["companions_D_minus_C"][CAT_FULL]),
        _contrast_line("Abstention or escalation", sens["companions_D_minus_C"][CAT_ABSTAIN]),
        "",
        "## 7. Diagnostics",
        "",
        f"- Retry: {diag['retry']['retried_completed_runs']} completed runs retried "
        f"({diag['retry']['retry_rate_of_completed_pp']}% of completed runs). Document-set change "
        f"after retry: {diag['retry']['retrieval_change_after_retry']}. A changed document set is a "
        "retrieval change, not recovery.",
        f"- Reviewed post-retry states and what the run then produced: "
        f"{diag['retry']['post_retry_states_and_following_outcome']}. Context restoration to OK is "
        "reported separately from producing a fully supported answer.",
        f"- Policy: {diag['policy']['proposed_action_mismatches']} proposed-action mismatches over "
        f"{diag['policy']['steps_with_a_proposal']} steps with a proposal. "
        f"{diag['policy']['policy_divergent_executions_by_design_in_A_and_B']} executions diverged "
        "from the policy action in A and B, which is those branches' design, and "
        f"{diag['policy']['contract_violations_in_C_and_D']} contract violations occurred in C and "
        "D. Enforced compliance is not evidence that the evaluator's state assessment was correct.",
        f"- Citation-ID validity, independent of grounding: {diag['citation_id_validity']['counts']}. "
        "All invalid-citation answers are retained with their accepted labels.",
        f"- Usage: {diag['usage']['provider_attempts']} provider attempts, "
        f"{diag['usage']['provider_calls']} logged calls, {diag['usage']['total_tokens']} tokens "
        f"({diag['usage']['input_tokens']} input, {diag['usage']['output_tokens']} output, "
        f"{diag['usage']['cached_tokens']} cached); mean recorded run latency "
        f"{diag['usage']['latency_seconds_mean']} s. No monetary estimate is given.",
        "",
        "Initial evaluator against the accepted reviewed state of the initial context:",
        "",
        f"- typed grader (B, D): {diag['initial_evaluator_typed_confusion']['table']}",
        f"- binary grader (A, C): {diag['initial_evaluator_binary_confusion']['table']}",
        "",
        "## 8. What this means",
        "",
        payload["conclusions"],
        "",
        "## 9. Limitations",
        "",
    ]
    for limitation in payload["limitations"]:
        lines.append(f"- {limitation}")
    lines += [
        "",
        "## 10. Reproduction",
        "",
        "```powershell",
        "python tools/stage15_accept.py",
        "python tools/stage15_run.py",
        "python tools/stage15_validate.py",
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
