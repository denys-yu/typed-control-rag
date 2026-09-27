"""Stage 14 step 1: accept the determinate stage 13 proposals and fix the sample.

Offline. The researcher's instruction accepts every determinate proposal of
`results/main_fault_review_proposals_v2.jsonl`, with one correction: eligible
question 54 is excluded because its CLEAN reading requires repairing the
question's premise. Its CLEAN review therefore stays pending.

The original pending review file is archived before anything is written, the
supplied proposal files and earlier reports are left untouched, and the
correction plus the final sample are recorded in new artefacts.

    python tools/stage14_accept.py

No provider API call is made here.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import fault_cases, hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage12_main_prep as prep

STAGE = "stage14_acceptance"
REVIEWER = "Denys Yuvzhenko"
ACCEPTANCE_BASIS = (
    "accepted by the researcher through the stage 14 instruction; this is a researcher "
    "acceptance of prepared proposals, not a new independent human review"
)

PROPOSALS_V2 = "main_fault_review_proposals_v2.jsonl"
SAMPLE_PROPOSAL = "main_sample_proposal.json"
ARCHIVE_DIRNAME = "stage14_archive"
ACCEPTANCE_FILENAME = "stage14_acceptance.json"
SAMPLE_FINAL_FILENAME = "main_sample_final.json"

TARGET_QUESTIONS = 60
EXCLUDED_QUESTION_NUMBER = 54
EXCLUDED_QUESTION_ID = "5ab56200554299494045ef88"
EXPECTED_REPLACEMENT_ID = "5a82800855429966c78a6a2f"
EXCLUSION_REASON = "ambiguous_question_premise"
EXCLUSION_DETAIL = (
    "the question conflates the beginning of medal awards with the beginning of the "
    "gold/silver/bronze award tradition; its CLEAN reading requires an unsupported repair of the "
    "question premise, so the question is excluded and its CLEAN review stays pending"
)
SENSITIVITY_QUESTION_NUMBERS = [20, 23, 88, 90, 132]
SENSITIVITY_REASON = (
    "these questions entered the sample through the stage 13 conventions G-1 (identifier "
    "granularity) and K-1 (kinship and spouse slots), or through an ordinary-reading call on a "
    "CLEAN context; the sensitivity subset re-runs the same analysis on the remaining questions "
    "using the same runs"
)


def accepted_row(proposal: dict, annotation: dict, forced_pending: bool) -> dict:
    """One review row in the project schema, with identity fields preserved."""
    base = {
        "case_id": proposal["case_id"],
        "question_id": proposal["question_id"],
        "condition": proposal["condition"],
        "content_identity": proposal["content_identity"],
    }
    if forced_pending:
        return {
            **base,
            "review_status": fault_cases.REVIEW_PENDING,
            "observed_state": None,
            "reviewer": None,
            "note": (
                f"kept pending by researcher correction at stage 14: {EXCLUSION_DETAIL}. "
                f"The stage 13 proposal was {proposal['proposed_observed_state']} "
                f"({proposal['proposed_review_status']}); it is not accepted."
            ),
        }
    if proposal["proposed_observed_state"] is None:
        return {
            **base,
            "review_status": fault_cases.REVIEW_PENDING,
            "observed_state": None,
            "reviewer": None,
            "note": (
                "unresolved at stage 13 and not accepted at stage 14; this case cannot enter the "
                f"execution sample. {proposal.get('note', '')}"
            ).strip(),
        }
    return {
        **base,
        "review_status": proposal["proposed_review_status"],
        "observed_state": proposal["proposed_observed_state"],
        "reviewer": REVIEWER,
        "note": f"{proposal['note']} [{ACCEPTANCE_BASIS}]",
    }


def main() -> int:
    config = load_config()
    results = config.paths["results"]
    paths = prep.MainPaths.of(config)
    reviews_path = paths.results / prep.FAULT_REVIEWS_FILENAME

    proposals = [
        json.loads(line)
        for line in (results / PROPOSALS_V2).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    annotations = {
        a["case_id"]: a for a in hotpotqa.read_jsonl(paths.results / prep.FAULT_ANNOTATIONS_FILENAME)
    }
    contexts = {
        c["case_id"]: c for c in hotpotqa.read_jsonl(paths.results / prep.FAULT_CONTEXTS_FILENAME)
    }
    original_reviews = hotpotqa.read_jsonl(reviews_path)
    original_hash = sha256_file(reviews_path)

    # --- archive the pending file before touching anything -------------------------
    archive_dir = results / ARCHIVE_DIRNAME
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"fault_reviews_pending_{original_hash[:12]}.jsonl"
    shutil.copy2(reviews_path, archive_path)

    # --- apply the accepted decisions by case_id -----------------------------------
    excluded_clean_case = next(
        p["case_id"]
        for p in proposals
        if p["question_id"] == EXCLUDED_QUESTION_ID and p["condition"] == fault_cases.CONDITION_CLEAN
    )
    rows = []
    forced = []
    for proposal in proposals:
        forced_pending = proposal["case_id"] == excluded_clean_case
        row = accepted_row(proposal, annotations[proposal["case_id"]], forced_pending)
        if forced_pending:
            forced.append(
                {
                    "case_id": proposal["case_id"],
                    "question_id": proposal["question_id"],
                    "condition": proposal["condition"],
                    "stage13_proposed_state": proposal["proposed_observed_state"],
                    "stage13_proposed_status": proposal["proposed_review_status"],
                    "accepted_state": None,
                    "accepted_status": fault_cases.REVIEW_PENDING,
                }
            )
        rows.append(row)

    identity_ok = all(
        row["content_identity"] == annotations[row["case_id"]]["content_identity"]
        and row["question_id"] == annotations[row["case_id"]]["question_id"]
        and row["condition"] == annotations[row["case_id"]]["condition"]
        for row in rows
    )
    if not identity_ok:
        raise SystemExit("identity fields would change; refusing to write the accepted reviews")
    if {r["case_id"] for r in rows} != {r["case_id"] for r in original_reviews}:
        raise SystemExit("case id set changed; refusing to write the accepted reviews")

    approved_mismatch = [
        row["case_id"]
        for row in rows
        if row["review_status"] == fault_cases.REVIEW_APPROVED
        and row["observed_state"] != annotations[row["case_id"]]["expected_state"]
    ]
    if approved_mismatch:
        raise SystemExit(f"approved rows whose state differs from the intended state: {approved_mismatch}")

    hotpotqa.write_jsonl(reviews_path, rows)

    # --- recompute the sample in the frozen candidate order ------------------------
    by_case = {row["case_id"]: row for row in rows}
    numbers = {p["question_id"]: p["eligible_question_number"] for p in proposals}
    positions = {p["question_id"]: p["candidate_position"] for p in proposals}
    by_question: dict[str, dict] = {}
    for annotation in annotations.values():
        by_question.setdefault(annotation["question_id"], {})[annotation["condition"]] = annotation

    matching: list[str] = []
    excluded: list[dict] = []
    for question_id in sorted(by_question, key=lambda q: numbers[q]):
        cases = by_question[question_id]
        reasons = []
        for condition in fault_cases.CONDITIONS:
            row = by_case[cases[condition]["case_id"]]
            if row["review_status"] != fault_cases.REVIEW_APPROVED:
                reasons.append(f"{condition}: {row['review_status']} (observed_state={row['observed_state']})")
            elif row["observed_state"] != cases[condition]["expected_state"]:
                reasons.append(
                    f"{condition}: approved as {row['observed_state']}, intended {cases[condition]['expected_state']}"
                )
        if reasons:
            entry = {
                "eligible_question_number": numbers[question_id],
                "question_id": question_id,
                "reasons": reasons,
            }
            if question_id == EXCLUDED_QUESTION_ID:
                entry["question_level_exclusion_reason"] = EXCLUSION_REASON
                entry["detail"] = EXCLUSION_DETAIL
            excluded.append(entry)
        else:
            matching.append(question_id)

    selected = matching[:TARGET_QUESTIONS]
    if len(selected) != TARGET_QUESTIONS:
        raise SystemExit(f"{len(matching)} matching questions available, expected at least {TARGET_QUESTIONS}")
    if EXCLUDED_QUESTION_ID in selected:
        raise SystemExit("the excluded question is still in the sample")
    if EXPECTED_REPLACEMENT_ID not in selected:
        raise SystemExit("the expected replacement question did not enter the sample")

    approved_contexts = [
        by_question[q][c]["case_id"] for q in selected for c in fault_cases.CONDITIONS
    ]
    if len(approved_contexts) != 240 or len(set(approved_contexts)) != 240:
        raise SystemExit(f"{len(set(approved_contexts))} distinct approved contexts, expected 240")

    sensitivity_ids = [
        question_id for question_id, number in numbers.items() if number in SENSITIVITY_QUESTION_NUMBERS
    ]
    sensitivity_subset = [q for q in selected if q not in sensitivity_ids]

    sample = {
        "stage": STAGE,
        "status": "final_for_execution",
        "acceptance_basis": ACCEPTANCE_BASIS,
        "selection_rule": (
            "the first 60 questions, in the original frozen randomized candidate order, whose four "
            "contexts are approved with observed_state equal to the intended state; no model "
            "outcome influences the selection and the candidate order is unchanged"
        ),
        "target_questions": TARGET_QUESTIONS,
        "matching_questions_available": len(matching),
        "questions": [
            {
                "sample_position": position,
                "eligible_question_number": numbers[question_id],
                "candidate_position": positions[question_id],
                "question_id": question_id,
                "question": contexts[by_question[question_id]["CLEAN"]["case_id"]]["question"],
                "case_ids": {
                    condition: by_question[question_id][condition]["case_id"]
                    for condition in fault_cases.CONDITIONS
                },
            }
            for position, question_id in enumerate(selected, start=1)
        ],
        "approved_initial_contexts": len(approved_contexts),
        "reserve_questions": [
            {"eligible_question_number": numbers[q], "question_id": q} for q in matching[TARGET_QUESTIONS:]
        ],
        "question_level_exclusions": [
            {
                "eligible_question_number": EXCLUDED_QUESTION_NUMBER,
                "question_id": EXCLUDED_QUESTION_ID,
                "reason": EXCLUSION_REASON,
                "detail": EXCLUSION_DETAIL,
                "clean_case_id": excluded_clean_case,
                "clean_review_status": fault_cases.REVIEW_PENDING,
            }
        ],
        "excluded_questions": excluded,
        "sensitivity_subset": {
            "purpose": "predeclared sensitivity analysis on the same runs; no additional provider calls",
            "excluded_eligible_question_numbers": SENSITIVITY_QUESTION_NUMBERS,
            "excluded_question_ids": [
                {"eligible_question_number": numbers[q], "question_id": q}
                for q in sorted(sensitivity_ids, key=lambda item: numbers[item])
            ],
            "reason": SENSITIVITY_REASON,
            "question_ids": sensitivity_subset,
            "questions": len(sensitivity_subset),
        },
        "design": {
            "questions": TARGET_QUESTIONS,
            "conditions": len(fault_cases.CONDITIONS),
            "branches": list(config.pilot.branches),
            "repeats": 3,
            "planned_coordinates": TARGET_QUESTIONS * 4 * 4 * 3,
            "provider_attempt_ceiling": 11520,
        },
    }
    hotpotqa.write_json(results / SAMPLE_FINAL_FILENAME, sample)

    status_counts = Counter(row["review_status"] for row in rows)
    acceptance = {
        "stage": STAGE,
        "recorded_at": prep.utc_now(),
        "acceptance_basis": ACCEPTANCE_BASIS,
        "reviewer_recorded_for_accepted_decisions": REVIEWER,
        "independent_human_review": False,
        "conventions_accepted": {
            "G-1": (
                "identifier granularity - accepted as an explicit operational annotation "
                "convention finalized before main data collection; not a logical necessity and "
                "not retrospectively preregistered"
            ),
            "K-1": (
                "kinship and spouse slots - accepted as an explicit operational annotation "
                "convention finalized before main data collection; not a logical necessity and "
                "not retrospectively preregistered"
            ),
        },
        "correction": {
            "excluded_question": {
                "eligible_question_number": EXCLUDED_QUESTION_NUMBER,
                "question_id": EXCLUDED_QUESTION_ID,
                "reason": EXCLUSION_REASON,
                "detail": EXCLUSION_DETAIL,
            },
            "forced_pending_cases": forced,
            "replacement_question": {
                "question_id": EXPECTED_REPLACEMENT_ID,
                "eligible_question_number": numbers[EXPECTED_REPLACEMENT_ID],
                "note": "entered by recomputing the first 60 in the unchanged frozen candidate order",
            },
        },
        "counts": {
            "cases": len(rows),
            "review_status": dict(status_counts),
            "accepted_with_reviewer": sum(1 for r in rows if r["reviewer"] == REVIEWER),
            "pending_cases": status_counts[fault_cases.REVIEW_PENDING],
            "matching_questions": len(matching),
            "selected_questions": len(selected),
            "approved_initial_contexts": len(approved_contexts),
            "sensitivity_subset_questions": len(sensitivity_subset),
        },
        "archive": {
            "original_pending_reviews": str(archive_path.relative_to(config.project_root).as_posix()),
            "original_sha256": original_hash,
        },
        "files": {
            "reviews_written": prep.FAULT_REVIEWS_FILENAME,
            "reviews_sha256": sha256_file(reviews_path),
            "sample_final": SAMPLE_FINAL_FILENAME,
            "sample_final_sha256": sha256_file(results / SAMPLE_FINAL_FILENAME),
        },
        "unchanged_inputs": {
            f"results/{PROPOSALS_V2}": sha256_file(results / PROPOSALS_V2),
            f"results/{SAMPLE_PROPOSAL}": sha256_file(results / SAMPLE_PROPOSAL),
            "results/stage13_report.json": sha256_file(results / "stage13_report.json"),
            "results/main_preparation/fault_contexts.jsonl": sha256_file(
                paths.results / prep.FAULT_CONTEXTS_FILENAME
            ),
            "results/main_preparation/fault_annotations.jsonl": sha256_file(
                paths.results / prep.FAULT_ANNOTATIONS_FILENAME
            ),
        },
        "provider_api_calls": 0,
    }
    hotpotqa.write_json(results / ACCEPTANCE_FILENAME, acceptance)

    print(f"archived pending reviews : {archive_path.name}")
    print(f"review rows written      : {len(rows)} {dict(status_counts)}")
    print(f"matching questions       : {len(matching)}")
    print(f"selected questions       : {len(selected)} (approved contexts {len(approved_contexts)})")
    print(f"excluded by correction   : Q{EXCLUDED_QUESTION_NUMBER} {EXCLUDED_QUESTION_ID}")
    print(f"replacement in sample    : Q{numbers[EXPECTED_REPLACEMENT_ID]} {EXPECTED_REPLACEMENT_ID}")
    print(f"sensitivity subset       : {len(sensitivity_subset)} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
