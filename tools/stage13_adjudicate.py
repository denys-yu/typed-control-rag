"""Stage 13: adjudicate the unresolved review proposals and size the main sample.

Offline. Reads the supplied proposal package and the frozen stage 12 artefacts,
applies the decisions recorded in `tools/stage13_decisions.json`, and writes a
revised proposal file, an adjudication document, a sample disposition and a
report. Nothing supplied is modified: the four review files, the original
`fault_reviews.jsonl`, the contexts, the edits, the candidate order, the corpus
and the index are read-only here.

Every decision names its evidence by document title; this module resolves those
to the exact doc_ids of the case context and refuses to build if an excerpt is
not a literal substring of the named document.

    python tools/stage13_adjudicate.py

No provider API call is made anywhere in this file.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import fault_cases, hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage12_main_prep as prep

STAGE = "stage13_adjudication"
AUTHOR_NOTE = (
    "Proposals prepared for researcher acceptance. No reviewer name is assigned to any "
    "decision, and this is not an independent human review."
)

DECISIONS_RELPATH = Path("tools") / "stage13_decisions.json"
SUPPLIED_PROPOSALS = "main_fault_review_proposals.jsonl"
SUPPLIED_SUMMARY = "main_fault_review_summary.json"
SUPPLIED_ADJUDICATION = "main_fault_adjudication.md"
SUPPLIED_README = "README_main_fault_review.md"

PROPOSALS_V2 = "main_fault_review_proposals_v2.jsonl"
ADJUDICATION_DOC = "stage13_adjudication.md"
SAMPLE_PROPOSAL = "main_sample_proposal.json"
REPORT = "stage13_report.json"
AMENDMENT_DOC = "main_protocol_amendment_proposal.md"

TARGET_QUESTIONS = 60
REPEATS = 3
BRANCHES = 4
CONDITIONS = 4
CALLS_PER_RUN = 4


def load_inputs(config):
    paths = prep.MainPaths.of(config)
    results = config.paths["results"]
    supplied = [json.loads(line) for line in (results / SUPPLIED_PROPOSALS).read_text(encoding="utf-8").splitlines() if line.strip()]
    annotations = {a["case_id"]: a for a in hotpotqa.read_jsonl(paths.results / prep.FAULT_ANNOTATIONS_FILENAME)}
    contexts = {c["case_id"]: c for c in hotpotqa.read_jsonl(paths.results / prep.FAULT_CONTEXTS_FILENAME)}
    reviews = {r["case_id"]: r for r in hotpotqa.read_jsonl(paths.results / prep.FAULT_REVIEWS_FILENAME)}
    eligibility = hotpotqa.read_json(paths.results / prep.ELIGIBILITY_FILENAME)
    decisions = json.loads((config.project_root / DECISIONS_RELPATH).read_text(encoding="utf-8"))
    return paths, supplied, annotations, contexts, reviews, eligibility, decisions


def verify_inputs(supplied, annotations, contexts, reviews, eligibility) -> dict:
    """Identity checks between the supplied proposals and the frozen artefacts."""
    case_ids = [row["case_id"] for row in supplied]
    order = [record["question_id"] for record in eligibility["records"] if record["eligible"]]
    proposal_order: list[str] = []
    for row in supplied:
        if row["question_id"] not in proposal_order:
            proposal_order.append(row["question_id"])

    field_mismatches = [
        row["case_id"]
        for row in supplied
        if annotations[row["case_id"]]["question_id"] != row["question_id"]
        or annotations[row["case_id"]]["condition"] != row["condition"]
        or annotations[row["case_id"]]["content_identity"] != row["content_identity"]
        or reviews[row["case_id"]]["content_identity"] != row["content_identity"]
    ]
    numbering = {row["question_id"]: row["eligible_question_number"] for row in supplied}
    return {
        "proposal_rows": len(supplied),
        "unique_case_ids": len(set(case_ids)),
        "case_ids_match_annotations": set(case_ids) == set(annotations),
        "case_ids_match_contexts": set(case_ids) == set(contexts),
        "case_ids_match_reviews": set(case_ids) == set(reviews),
        "question_condition_identity_mismatches": len(field_mismatches),
        "frozen_candidate_order_preserved": proposal_order == order,
        "question_numbering_matches_order": [numbering[q] for q in order] == list(range(1, len(order) + 1)),
        "original_review_rows_all_pending": all(
            r["review_status"] == fault_cases.REVIEW_PENDING and r["observed_state"] is None
            for r in reviews.values()
        ),
    }


def categorise(states: dict) -> str:
    intended = fault_cases.EXPECTED_STATE
    if any(states[c] is not None and states[c] != intended[c] for c in fault_cases.CONDITIONS):
        return "known_mismatch"
    if any(states[c] is None for c in fault_cases.CONDITIONS):
        return "unresolved_only"
    return "matching_quadruplet"


def resolve_evidence(decision: dict, context: dict, annotation: dict) -> list[dict]:
    """Resolve titles to exact doc_ids and verify every excerpt literally."""
    resolved = []
    for item in decision["evidence"]:
        matches = [d for d in context["documents"] if d["title"] == item["title"]]
        if not matches:
            raise SystemExit(
                f"{decision['case_id']}: no document titled {item['title']!r} in the case context"
            )
        added = set(annotation["added_doc_ids"])
        gold = set(annotation["gold_supporting_doc_ids"])
        if len(matches) > 1:
            wanted_added = "added" in item["role"]
            narrowed = [d for d in matches if (d["doc_id"] in added) == wanted_added]
            matches = narrowed or matches
        document = matches[0]
        if item["excerpt"] not in document["text"]:
            raise SystemExit(
                f"{decision['case_id']}: excerpt not found verbatim in {item['title']!r}"
            )
        resolved.append(
            {
                "doc_id": document["doc_id"],
                "title": document["title"],
                "position_in_context": [d["doc_id"] for d in context["documents"]].index(document["doc_id"]) + 1,
                "role": item["role"],
                "is_gold_supporting": document["doc_id"] in gold,
                "is_added_document": document["doc_id"] in added,
                "excerpt": item["excerpt"],
            }
        )
    return resolved


def build_v2(supplied, decisions, contexts, annotations) -> tuple[list[dict], list[dict]]:
    """Revised proposals for all 572 cases; untouched decisions are carried over."""
    by_case = {d["case_id"]: d for d in decisions["decisions"]}
    rows: list[dict] = []
    changes: list[dict] = []
    for row in supplied:
        case_id = row["case_id"]
        new = dict(row)
        new["source"] = "carried_over_stage13_input"
        new["adjudicated_at_stage13"] = False
        new["applied_rules"] = []
        new["evidence"] = []
        decision = by_case.get(case_id)
        if decision is not None:
            annotation = annotations[case_id]
            evidence = resolve_evidence(decision, contexts[case_id], annotation)
            changes.append(
                {
                    "case_id": case_id,
                    "question_id": row["question_id"],
                    "eligible_question_number": row["eligible_question_number"],
                    "condition": row["condition"],
                    "old_observed_state": row["proposed_observed_state"],
                    "new_observed_state": decision["state"],
                    "old_review_status": row["proposed_review_status"],
                    "new_review_status": decision["status"],
                    "intended_state": fault_cases.EXPECTED_STATE[row["condition"]],
                    "matches_intended": decision["state"] == fault_cases.EXPECTED_STATE[row["condition"]],
                    "rules": decision["rules"],
                    "reason": decision["reasoning"],
                    "competing_reading": decision["competing_reading"],
                    "evidence": evidence,
                }
            )
            new.update(
                {
                    "proposed_observed_state": decision["state"],
                    "proposed_review_status": decision["status"],
                    "note": decision["reasoning"],
                    "competing_reading": decision["competing_reading"],
                    "applied_rules": decision["rules"],
                    "evidence": evidence,
                    "source": "adjudicated_stage13",
                    "adjudicated_at_stage13": True,
                    "previous_proposed_observed_state": row["proposed_observed_state"],
                    "previous_proposed_review_status": row["proposed_review_status"],
                }
            )
        new["requires_researcher_confirmation"] = True
        new["reviewer"] = None
        rows.append(new)
    return rows, changes


def question_disposition(rows: list[dict]) -> tuple[list[dict], dict]:
    by_question: dict[str, dict] = defaultdict(dict)
    meta: dict[str, dict] = {}
    for row in rows:
        by_question[row["question_id"]][row["condition"]] = row
        meta.setdefault(
            row["question_id"],
            {
                "question_id": row["question_id"],
                "eligible_question_number": row["eligible_question_number"],
                "candidate_position": row["candidate_position"],
            },
        )
    ordered = sorted(meta.values(), key=lambda item: item["eligible_question_number"])
    disposition = []
    for item in ordered:
        cases = by_question[item["question_id"]]
        states = {c: cases[c]["proposed_observed_state"] for c in fault_cases.CONDITIONS}
        category = categorise(states)
        mismatches = [
            {
                "condition": c,
                "intended": fault_cases.EXPECTED_STATE[c],
                "proposed": states[c],
            }
            for c in fault_cases.CONDITIONS
            if states[c] is not None and states[c] != fault_cases.EXPECTED_STATE[c]
        ]
        disposition.append(
            {
                **item,
                "proposed_states": states,
                "category": category,
                "mismatches": mismatches,
                "unresolved_conditions": [c for c in fault_cases.CONDITIONS if states[c] is None],
                "adjudicated_at_stage13": any(
                    cases[c]["adjudicated_at_stage13"] for c in fault_cases.CONDITIONS
                ),
            }
        )
    counts = Counter(item["category"] for item in disposition)
    return disposition, dict(counts)


def build_sample(disposition: list[dict]) -> dict:
    matching = [d for d in disposition if d["category"] == "matching_quadruplet"]
    selected = matching[:TARGET_QUESTIONS]
    exclusions = []
    cutoff = selected[-1]["eligible_question_number"] if selected else None
    for item in disposition:
        if cutoff is not None and item["eligible_question_number"] > cutoff:
            continue
        if item["category"] == "matching_quadruplet" and item in selected:
            continue
        exclusions.append(
            {
                "eligible_question_number": item["eligible_question_number"],
                "question_id": item["question_id"],
                "category": item["category"],
                "reasons": [
                    f"{m['condition']}: intended {m['intended']}, proposed {m['proposed']}"
                    for m in item["mismatches"]
                ]
                or [f"unresolved: {', '.join(item['unresolved_conditions'])}"],
            }
        )
    unresolved_before_cutoff = [
        item["eligible_question_number"]
        for item in disposition
        if item["unresolved_conditions"]
        and not item["mismatches"]
        and (cutoff is None or item["eligible_question_number"] <= cutoff)
    ]
    available = len(matching)
    return {
        "stage": STAGE,
        "status": "proposal_pending_researcher_acceptance",
        "note": AUTHOR_NOTE,
        "target_questions": TARGET_QUESTIONS,
        "matching_quadruplets_available": available,
        "shortfall": max(0, TARGET_QUESTIONS - available),
        "selection_rule": (
            "the first 60 fully matching quadruplets in the frozen randomized candidate order; "
            "no model outcome influences the selection"
        ),
        "selection_is_provisional": bool(unresolved_before_cutoff),
        "provisional_reason": (
            "unresolved cases remain in questions at or before the cut-off that carry no definite "
            "mismatch, so their resolution could change membership"
            if unresolved_before_cutoff
            else "no question at or before the cut-off is unresolved-only, so membership is "
            "unambiguous given these proposals"
        ),
        "unresolved_questions_before_cutoff": unresolved_before_cutoff,
        "cutoff_eligible_question_number": cutoff,
        "selected_questions": [
            {
                "sample_position": position,
                "eligible_question_number": item["eligible_question_number"],
                "candidate_position": item["candidate_position"],
                "question_id": item["question_id"],
                "adjudicated_at_stage13": item["adjudicated_at_stage13"],
            }
            for position, item in enumerate(selected, start=1)
        ],
        "reserve_questions": [
            {
                "eligible_question_number": item["eligible_question_number"],
                "question_id": item["question_id"],
            }
            for item in matching[TARGET_QUESTIONS:]
        ],
        "exclusions_before_cutoff": exclusions,
        "run_plan_if_accepted": {
            "questions": len(selected),
            "conditions": CONDITIONS,
            "branches": BRANCHES,
            "repeats": REPEATS,
            "pipeline_runs": len(selected) * CONDITIONS * BRANCHES * REPEATS,
            "provider_call_ceiling": len(selected) * CONDITIONS * BRANCHES * REPEATS * CALLS_PER_RUN,
            "ceiling_note": (
                "four calls per run is the verified maximum trajectory, not an expected count"
            ),
        },
        "not_frozen": (
            "this is a disposition proposal; no execution plan is frozen and no run has been executed"
        ),
    }


def write_outputs(config, rows, changes, disposition, counts, sample, verification, decisions):
    results = config.paths["results"]
    hotpotqa.write_jsonl(results / PROPOSALS_V2, rows)
    hotpotqa.write_json(results / SAMPLE_PROPOSAL, sample)

    by_condition: dict[str, Counter] = defaultdict(Counter)
    state_counts: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        by_condition[row["condition"]][row["proposed_review_status"]] += 1
        state_counts[row["condition"]][str(row["proposed_observed_state"])] += 1

    paths = prep.MainPaths.of(config)
    report = {
        "stage": STAGE,
        "generated_at": prep.utc_now(),
        "status": "proposals_only_not_accepted_reviews",
        "provider_api_calls": 0,
        "original_reviews_modified": False,
        "experiment_executed": False,
        "independent_human_review": False,
        "input_sha256": {
            f"results/{name}": sha256_file(results / name)
            for name in (SUPPLIED_PROPOSALS, SUPPLIED_SUMMARY, SUPPLIED_ADJUDICATION, SUPPLIED_README)
        }
        | {
            "results/main_preparation/fault_reviews.jsonl": sha256_file(paths.results / prep.FAULT_REVIEWS_FILENAME),
            "results/main_preparation/fault_contexts.jsonl": sha256_file(paths.results / prep.FAULT_CONTEXTS_FILENAME),
            "results/main_preparation/fault_annotations.jsonl": sha256_file(paths.results / prep.FAULT_ANNOTATIONS_FILENAME),
            "results/main_preparation/eligibility.json": sha256_file(paths.results / prep.ELIGIBILITY_FILENAME),
            "config/main_inconsistent_edits.json": sha256_file(config.project_root / prep.EDITS_RELPATH),
            "tools/stage13_decisions.json": sha256_file(config.project_root / DECISIONS_RELPATH),
        },
        "verification": verification,
        "rules_applied": decisions["rules"],
        "new_rules_proposed": ["G-1", "K-1"],
        "changed_decisions": changes,
        "counts": {
            "cases_total": len(rows),
            "cases_adjudicated_at_stage13": len(changes),
            "cases_changed_state": sum(
                1 for c in changes if c["old_observed_state"] != c["new_observed_state"]
            ),
            "by_condition_status": {k: dict(v) for k, v in by_condition.items()},
            "by_condition_state": {k: dict(v) for k, v in state_counts.items()},
            "status_totals": dict(Counter(row["proposed_review_status"] for row in rows)),
            "unresolved_cases_remaining": sum(
                1 for row in rows if row["proposed_observed_state"] is None
            ),
        },
        "question_categories": counts,
        "question_categories_before": {
            "matching_quadruplet": 55,
            "unresolved_only": 18,
            "known_mismatch": 70,
        },
        "sample": {
            "available_matching_quadruplets": sample["matching_quadruplets_available"],
            "target": TARGET_QUESTIONS,
            "shortfall": sample["shortfall"],
            "sample_available": sample["shortfall"] == 0,
            "selection_is_provisional": sample["selection_is_provisional"],
            "cutoff_eligible_question_number": sample["cutoff_eligible_question_number"],
            "pipeline_runs": sample["run_plan_if_accepted"]["pipeline_runs"],
            "provider_call_ceiling": sample["run_plan_if_accepted"]["provider_call_ceiling"],
        },
        "restored_inputs": {
            "data/processed/main/main_candidates.json": (
                "the file was absent from the working tree at the start of stage 13; it was "
                "rebuilt from the candidate_ids recorded in results/main_preparation/"
                "selection_rule.json and is byte-identical to the frozen artefact, matching the "
                "hash recorded independently in data/processed/main/manifest.json and in "
                "results/main_fault_review_summary.json "
                "(b0fec829cdf5956f3921d70f49c8ea2d808d6f01c535ce5897bdb6ea6888d737). No content "
                "was invented and nothing else was rebuilt."
            )
        },
        "preserved_unchanged": [
            f"results/{SUPPLIED_PROPOSALS}",
            f"results/{SUPPLIED_SUMMARY}",
            f"results/{SUPPLIED_ADJUDICATION}",
            f"results/{SUPPLIED_README}",
            "results/main_preparation/fault_reviews.jsonl",
            "results/main_preparation/fault_contexts.jsonl",
            "results/main_preparation/fault_annotations.jsonl",
            "config/main_inconsistent_edits.json",
            "data/processed/main/",
            "artifacts/main_retrieval/",
        ],
        "outputs": {},
    }

    (results / ADJUDICATION_DOC).write_text(
        adjudication_markdown(changes, disposition, counts, sample, decisions), encoding="utf-8", newline="\n"
    )
    report["outputs"] = {
        f"results/{name}": sha256_file(results / name)
        for name in (PROPOSALS_V2, ADJUDICATION_DOC, SAMPLE_PROPOSAL)
    }
    hotpotqa.write_json(results / REPORT, report)
    report["outputs"][f"results/{REPORT}"] = sha256_file(results / REPORT)
    return report


def adjudication_markdown(changes, disposition, counts, sample, decisions) -> str:
    lines = [
        "# Stage 13 - adjudication of the unresolved review proposals",
        "",
        AUTHOR_NOTE,
        "",
        "Scope: the 23 unresolved cases inside the 18 unresolved-only questions. Decisions in the "
        "supplied package that this adjudication does not touch are carried over unchanged into "
        "`results/main_fault_review_proposals_v2.jsonl`.",
        "",
        "## Rules applied",
        "",
    ]
    for code, text in decisions["rules"].items():
        new = " **(new, proposed at stage 13)**" if code in ("G-1", "K-1") else ""
        lines.append(f"- **{code}**{new}: {text}")
    lines += [
        "",
        "R-1, R-1b, R-2, R-3 and R-4 restate standards already in force: the pilot annotation "
        "rules, the accepted evidence standard of the supplied package, and the distinctions the "
        "researcher set for this stage. G-1 and K-1 are new interpretive clarifications and are "
        "proposed, not preregistered and not previously accepted.",
        "",
        "## Case decisions",
        "",
    ]
    for change in changes:
        lines += [
            f"### Q{change['eligible_question_number']} / {change['condition']} - case `{change['case_id']}`",
            "",
            f"- proposed observed state: **{change['new_observed_state']}** "
            f"(was {change['old_observed_state']}); intended {change['intended_state']}; "
            f"matches intended: {change['matches_intended']}",
            f"- proposed review status: **{change['new_review_status']}** (was {change['old_review_status']})",
            f"- rules: {', '.join(change['rules'])}",
            "- evidence:",
        ]
        for item in change["evidence"]:
            flag = "gold" if item["is_gold_supporting"] else ("added" if item["is_added_document"] else "other")
            lines.append(
                f"    - `{item['doc_id']}` ({flag}, position {item['position_in_context']}, "
                f"{item['title']}): \"{item['excerpt']}\""
            )
        lines += [
            f"- reasoning: {change['reason']}",
            f"- competing reading: {change['competing_reading']}",
            "",
        ]
    lines += [
        "## Question-level result",
        "",
        "| Category | Before | After |",
        "| --- | ---: | ---: |",
        f"| matching quadruplet | 55 | {counts.get('matching_quadruplet', 0)} |",
        f"| unresolved only | 18 | {counts.get('unresolved_only', 0)} |",
        f"| known mismatch | 70 | {counts.get('known_mismatch', 0)} |",
        "",
        "Questions that moved into the matching set: "
        + ", ".join(
            f"Q{d['eligible_question_number']}"
            for d in disposition
            if d["category"] == "matching_quadruplet" and d["adjudicated_at_stage13"]
        )
        + ".",
        "",
        "Questions that moved from unresolved-only to a definite mismatch: "
        + ", ".join(
            f"Q{d['eligible_question_number']}"
            for d in disposition
            if d["category"] == "known_mismatch" and d["adjudicated_at_stage13"]
        )
        + ".",
        "",
        "## Consistency inspection of decisions this stage did not reopen",
        "",
        "The two new clarifications and the coexistence rule were checked against the decisions "
        "already supplied, limited to the cases they could touch:",
        "",
        "- **All 55 INCONSISTENT cases of the previously matching questions** were listed by the "
        "property their edit changes. Their conflicts are dates, quantities, distances, venues, "
        "single-valued category assignments or explicit denials, none of which R-1 covers. Two were "
        "inspected in full because their property names looked like coexistence categories: Q15 "
        "(the edit also reassigns which national team claimed the 1976 title, a singular-event "
        "attribution under R-3) and Q110 (language of production, a single-valued production "
        "attribute). Neither decision changes.",
        "- **The two questions whose only mismatch is a rejected INCONSISTENT case** (Q114 Reagan's "
        "earlier profession, Q115 a weaker numerical lower bound) were re-read. Both rejections "
        "follow R-1 and the compatible-lower-bounds distinction and stand unchanged.",
        "- **The nine questions whose only mismatch is a CLEAN or PARTIAL case** were re-read to see "
        "whether G-1 applies. All of them turn on alternative evidence surviving a removal, not on "
        "identifier granularity; none changes.",
        "",
        "No decision outside the 23 adjudicated cases is altered by this stage.",
        "",
        "## Sample consequence",
        "",
        f"- matching quadruplets available: **{sample['matching_quadruplets_available']}** "
        f"(target {sample['target_questions']})",
        f"- shortfall: **{sample['shortfall']}**",
        f"- selection provisional: **{sample['selection_is_provisional']}** - {sample['provisional_reason']}",
        "",
        "Two of the decisions carrying the sample are the ones that rest on the new clarifications: "
        "Q23 and Q88 under K-1, and Q90 under G-1. If the researcher rejects K-1, questions 23 and "
        "88 leave the matching set; if the researcher rejects G-1, question 90 leaves it. Each such "
        "rejection reduces the available set by one question, and the sample falls below 60 as soon "
        "as two of those three decisions are overturned.",
        "",
        "Nothing here is frozen. The proposals still need researcher acceptance, and no reviewer "
        "name has been recorded for any of them.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    config = load_config()
    paths, supplied, annotations, contexts, reviews, eligibility, decisions = load_inputs(config)
    verification = verify_inputs(supplied, annotations, contexts, reviews, eligibility)
    problems = [k for k, v in verification.items() if v is False]
    if problems:
        raise SystemExit(f"input verification failed: {problems}")

    rows, changes = build_v2(supplied, decisions, contexts, annotations)
    disposition, counts = question_disposition(rows)
    sample = build_sample(disposition)
    report = write_outputs(config, rows, changes, disposition, counts, sample, verification, decisions)

    print(f"adjudicated cases        : {len(changes)}")
    print(f"question categories      : {counts}")
    print(f"matching quadruplets     : {sample['matching_quadruplets_available']} "
          f"(target {TARGET_QUESTIONS}, shortfall {sample['shortfall']})")
    print(f"selection provisional    : {sample['selection_is_provisional']}")
    print(f"pipeline runs if accepted: {sample['run_plan_if_accepted']['pipeline_runs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
