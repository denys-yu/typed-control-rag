"""Stage 13 focused offline checks: identity preservation, counts, selection order.

Nothing here rewrites a result file; it reads the supplied package, the frozen
stage 12 artefacts and the stage 13 outputs and prints one line per check.

    python tools/stage13_validate.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import fault_cases, hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage12_main_prep as prep
import stage13_adjudicate as adj


def main() -> int:
    config = load_config()
    results = config.paths["results"]
    paths = prep.MainPaths.of(config)

    supplied = [
        json.loads(line)
        for line in (results / adj.SUPPLIED_PROPOSALS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    v2 = hotpotqa.read_jsonl(results / adj.PROPOSALS_V2)
    sample = hotpotqa.read_json(results / adj.SAMPLE_PROPOSAL)
    report = hotpotqa.read_json(results / adj.REPORT)
    annotations = {
        a["case_id"]: a for a in hotpotqa.read_jsonl(paths.results / prep.FAULT_ANNOTATIONS_FILENAME)
    }
    reviews = hotpotqa.read_jsonl(paths.results / prep.FAULT_REVIEWS_FILENAME)
    summary = hotpotqa.read_json(results / adj.SUPPLIED_SUMMARY)

    checks: list[tuple[str, bool, str]] = []

    stable = all(
        a["case_id"] == b["case_id"]
        and a["question_id"] == b["question_id"]
        and a["condition"] == b["condition"]
        and a["content_identity"] == b["content_identity"]
        and a["eligible_question_number"] == b["eligible_question_number"]
        and a["candidate_position"] == b["candidate_position"]
        for a, b in zip(supplied, v2)
    )
    checks.append(
        (
            "identities_preserved_row_for_row",
            len(v2) == len(supplied) == 572 and stable,
            f"{len(v2)} rows, same order and identity fields as the supplied proposals",
        )
    )

    adjudicated = {row["case_id"] for row in v2 if row["adjudicated_at_stage13"]}
    carried = [
        (a, b)
        for a, b in zip(supplied, v2)
        if b["case_id"] not in adjudicated
    ]
    unchanged = all(
        a["proposed_observed_state"] == b["proposed_observed_state"]
        and a["proposed_review_status"] == b["proposed_review_status"]
        and a["note"] == b["note"]
        for a, b in carried
    )
    checks.append(
        (
            "untouched_decisions_carried_over",
            unchanged and len(adjudicated) == 23,
            f"{len(carried)} carried over unchanged, {len(adjudicated)} adjudicated",
        )
    )

    content_ok = all(
        row["content_identity"] == annotations[row["case_id"]]["content_identity"] for row in v2
    )
    checks.append(
        ("content_identity_matches_annotations", content_ok, "every row keeps its stage 12 content identity")
    )

    originals_pending = all(
        r["review_status"] == fault_cases.REVIEW_PENDING and r["observed_state"] is None
        and r["reviewer"] is None
        for r in reviews
    )
    source_hashes_hold = all(
        sha256_file(paths.results / name) == digest
        for name, digest in summary["source_files_sha256"].items()
        if (paths.results / name).is_file()
    )
    checks.append(
        (
            "originals_untouched",
            originals_pending and source_hashes_hold,
            f"{len(reviews)} original review rows still pending with no reviewer; "
            "stage 12 source hashes still match the supplied summary",
        )
    )

    no_reviewer = all(row.get("reviewer") is None for row in v2)
    all_flagged = all(row["requires_researcher_confirmation"] for row in v2)
    checks.append(
        (
            "no_acceptance_recorded",
            no_reviewer and all_flagged,
            "no reviewer name on any proposed decision; every row still flagged for confirmation",
        )
    )

    states = Counter(str(row["proposed_observed_state"]) for row in v2)
    statuses = Counter(row["proposed_review_status"] for row in v2)
    counts_match = (
        report["counts"]["status_totals"] == dict(statuses)
        and report["counts"]["unresolved_cases_remaining"] == states["None"]
    )
    checks.append(
        (
            "counts_consistent_with_report",
            counts_match,
            f"statuses {dict(statuses)}, unresolved cases {states['None']}",
        )
    )

    by_question: dict[str, dict] = {}
    for row in v2:
        by_question.setdefault(row["question_id"], {})[row["condition"]] = row["proposed_observed_state"]
    matching = [
        q
        for q in by_question
        if all(
            by_question[q][c] == fault_cases.EXPECTED_STATE[c] for c in fault_cases.CONDITIONS
        )
    ]
    numbers = {row["question_id"]: row["eligible_question_number"] for row in v2}
    expected_first60 = [
        q for q in sorted(matching, key=lambda item: numbers[item])
    ][: adj.TARGET_QUESTIONS]
    selected = [item["question_id"] for item in sample["selected_questions"]]
    positions = [item["eligible_question_number"] for item in sample["selected_questions"]]
    checks.append(
        (
            "selection_is_first_n_in_frozen_order",
            selected == expected_first60
            and positions == sorted(positions)
            and len(set(selected)) == len(selected),
            f"{len(selected)} questions, strictly increasing candidate order, "
            f"{len(matching)} matching quadruplets available",
        )
    )

    unresolved_questions = {
        row["question_id"] for row in v2 if row["proposed_observed_state"] is None
    }
    blocking = [
        q
        for q in unresolved_questions
        if numbers[q] <= sample["cutoff_eligible_question_number"]
        and not any(
            by_question[q][c] is not None and by_question[q][c] != fault_cases.EXPECTED_STATE[c]
            for c in fault_cases.CONDITIONS
        )
    ]
    checks.append(
        (
            "no_unresolved_question_can_change_membership",
            not blocking,
            f"{len(unresolved_questions)} questions still carry an unresolved case, all of them "
            "with a definite mismatch as well",
        )
    )

    checks.append(
        (
            "offline_claims",
            report["provider_api_calls"] == 0
            and report["original_reviews_modified"] is False
            and report["experiment_executed"] is False,
            "provider_api_calls=0, original_reviews_modified=false, experiment_executed=false",
        )
    )

    for name, passed, detail in checks:
        print(f"[{'ok' if passed else 'FAILED'}] {name}: {detail}")
    return 0 if all(passed for _, passed, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
