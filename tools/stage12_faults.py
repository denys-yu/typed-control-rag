"""Stage 12: fault construction, review package and property checks (offline).

The construction rules themselves are not restated here: the replacement rule,
the seeded PARTIAL choice, the INCONSISTENT slot rule, the case identifiers,
the context hash and the structural checks all come from
`typed_rag.fault_cases`. Only the inputs are the main-study ones.

No provider API call happens anywhere in this module.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from typed_rag import fault_cases, hotpotqa, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.download import sha256_file

import stage12_main_prep as prep

CONTENT_IDENTITY_RULE = (
    "sha256 of the canonical JSON list of [doc_id, title, text] triples in context order; "
    "a review label is preserved only while this identity is unchanged"
)

RUBRIC_POINTS = (
    "a context is OK only when every relationship needed to identify the answer is supported "
    "by the documents themselves",
    "authorship of a single volume does not establish authorship of a series",
    "a contradiction counts only when both statements concern the same relevant fact and no "
    "temporal or entity distinction resolves them",
    "a removed support document may still leave alternative evidence: judge the context as it "
    "stands, not the operation that produced it",
)


def content_identity(documents: list[dict]) -> str:
    """Identity of a context as the model would see it, in order."""
    return prep.sha256_json([[d["doc_id"], d["title"], d["text"]] for d in documents])


def load_main_edits(config: ExperimentConfig) -> tuple[dict, dict]:
    """Hand-drafted INCONSISTENT edits, one candidate per eligible question."""
    path = config.project_root / prep.EDITS_RELPATH
    if not path.is_file():
        return {}, {"path": str(path), "present": False, "sha256": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["edits"], {"path": str(path), "present": True, "sha256": sha256_file(path)}


# --- construction -------------------------------------------------------------------


def build_fault_cases(config: ExperimentConfig) -> dict:
    """Build the four candidate contexts for every technically eligible question."""
    paths = prep.MainPaths.of(config)
    index_manifest = hotpotqa.read_json(paths.index / retrieval.INDEX_MANIFEST_FILENAME)
    rows = {
        r["question_id"]: r for r in hotpotqa.read_jsonl(paths.results / prep.RETRIEVAL_FILENAME)
    }
    eligibility = hotpotqa.read_json(paths.results / prep.ELIGIBILITY_FILENAME)
    annotations = {
        a["question_id"]: a
        for a in hotpotqa.read_jsonl(paths.processed / prep.ANNOTATIONS_FILENAME)
    }
    questions = {
        q["question_id"]: q["question"]
        for q in hotpotqa.read_jsonl(paths.processed / prep.QUESTIONS_FILENAME)
    }
    corpus_docs = hotpotqa.read_jsonl(paths.processed / prep.CORPUS_FILENAME)
    corpus = {d["doc_id"]: d for d in corpus_docs}
    corpus_by_title = {d["title"]: d for d in corpus_docs}
    edits, edits_source = load_main_edits(config)
    seed = config.seed

    contexts: list[dict] = []
    case_annotations: list[dict] = []

    for record in eligibility["records"]:
        if not record["eligible"]:
            continue
        qid = record["question_id"]
        gold = annotations[qid]
        supporting = sorted(gold["supporting_doc_ids"])
        ranking = rows[qid]["results"]
        initial_ids = [r["doc_id"] for r in ranking[: fault_cases.CONTEXT_SIZE]]
        initial_docs = [corpus[doc_id] for doc_id in initial_ids]
        initial_hash = fault_cases.context_hash(initial_docs)

        for condition in fault_cases.CONDITIONS:
            case_id = fault_cases.case_id_for(qid, condition, seed)
            documents = [dict(d) for d in initial_docs]
            removed: list[str] = []
            added: list[str] = []
            synthetic_provenance: dict | None = None
            build_status = fault_cases.BUILD_OK
            failure_reason: str | None = None
            checks: dict = {}

            if condition == fault_cases.CONDITION_PARTIAL:
                removed = [random.Random(f"{seed}:{qid}").choice(supporting)]
            elif condition == fault_cases.CONDITION_EMPTY:
                removed = list(supporting)

            if condition in (fault_cases.CONDITION_PARTIAL, fault_cases.CONDITION_EMPTY):
                excluded = set(initial_ids) | set(supporting)
                replacements = fault_cases._replacements(ranking, corpus, excluded, len(removed))
                if len(replacements) < len(removed):
                    build_status = fault_cases.BUILD_FAILED
                    failure_reason = "not enough admissible replacement documents in the top-10"
                else:
                    for doc_id, replacement in zip(removed, replacements):
                        documents[initial_ids.index(doc_id)] = replacement
                        added.append(replacement["doc_id"])
                ids = [d["doc_id"] for d in documents]
                remaining_gold = sum(1 for s in supporting if s in ids)
                checks = {
                    **fault_cases._checks_common(documents, initial_ids),
                    "removed_absent": all(r not in ids for r in removed),
                    "added_present": all(a in ids for a in added),
                    "remaining_gold_count": remaining_gold,
                    "remaining_gold_count_ok": remaining_gold
                    == (1 if condition == fault_cases.CONDITION_PARTIAL else 0),
                }

            elif condition == fault_cases.CONDITION_INCONSISTENT:
                edit = edits.get(qid)
                if edit is None:
                    build_status = fault_cases.BUILD_FAILED
                    failure_reason = "no hand-drafted edit for this question"
                else:
                    synthetic, synthetic_provenance, error = fault_cases._build_synthetic(
                        edit, corpus_by_title
                    )
                    if error:
                        build_status, failure_reason = fault_cases.BUILD_FAILED, error
                    elif synthetic["doc_id"] in corpus:
                        build_status = fault_cases.BUILD_FAILED
                        failure_reason = "synthetic document collides with a corpus document"
                    elif synthetic_provenance["source_doc_id"] not in supporting:
                        build_status = fault_cases.BUILD_FAILED
                        failure_reason = "edit target is not a gold supporting document"
                    else:
                        non_gold_positions = [
                            i for i, doc_id in enumerate(initial_ids) if doc_id not in supporting
                        ]
                        if not non_gold_positions:
                            build_status = fault_cases.BUILD_FAILED
                            failure_reason = "no non-gold slot in the initial top-5"
                        else:
                            slot = non_gold_positions[-1]
                            removed = [initial_ids[slot]]
                            documents[slot] = synthetic
                            added = [synthetic["doc_id"]]
                ids = [d["doc_id"] for d in documents]
                source = corpus.get((synthetic_provenance or {}).get("source_doc_id", ""))
                checks = {
                    **fault_cases._checks_common(documents, initial_ids),
                    "both_gold_present": all(s in ids for s in supporting),
                    "synthetic_present": bool(added) and added[0] in ids,
                    "synthetic_text_differs_from_source": (
                        bool(source) and documents[ids.index(added[0])]["text"] != source["text"]
                        if added
                        else False
                    ),
                    "synthetic_not_in_corpus": bool(added) and added[0] not in corpus,
                }
            else:  # CLEAN
                checks = {
                    **fault_cases._checks_common(documents, initial_ids),
                    "identical_to_initial": fault_cases.context_hash(documents) == initial_hash,
                }

            checks["all_passed"] = build_status == fault_cases.BUILD_OK and all(
                value is True
                for key, value in checks.items()
                if key not in ("remaining_gold_count",)
            )

            ok = build_status == fault_cases.BUILD_OK
            identity = content_identity(documents) if ok else None
            if ok:
                contexts.append(
                    {
                        "case_id": case_id,
                        "question_id": qid,
                        "question": questions[qid],
                        "documents": [fault_cases._document_record(d) for d in documents],
                    }
                )
            case_annotations.append(
                {
                    "case_id": case_id,
                    "question_id": qid,
                    "candidate_position": record["candidate_position"],
                    "condition": condition,
                    "operation": {
                        fault_cases.CONDITION_CLEAN: "none",
                        fault_cases.CONDITION_PARTIAL: "remove_one_gold_document_and_replace",
                        fault_cases.CONDITION_EMPTY: "remove_both_gold_documents_and_replace",
                        fault_cases.CONDITION_INCONSISTENT: (
                            "replace_one_non_gold_document_with_contradicting_synthetic_copy"
                        ),
                    }[condition],
                    "expected_state": fault_cases.EXPECTED_STATE[condition],
                    "expected_state_note": (
                        "construction hypothesis implied by the operation; the actual state is "
                        "set by a reviewer. Removing support documents may leave alternative "
                        "evidence, and a proposed contradiction may be ambiguous."
                    ),
                    "build_status": build_status,
                    "failure_reason": failure_reason,
                    "initial_doc_ids": initial_ids,
                    "gold_supporting_doc_ids": supporting,
                    "removed_doc_ids": removed,
                    "added_doc_ids": added,
                    "added_doc_kind": (
                        "distractor_candidate"
                        if condition
                        in (fault_cases.CONDITION_PARTIAL, fault_cases.CONDITION_EMPTY)
                        else (
                            "synthetic"
                            if condition == fault_cases.CONDITION_INCONSISTENT
                            else None
                        )
                    ),
                    "final_doc_ids": [d["doc_id"] for d in documents] if ok else None,
                    "context_sha256_before": initial_hash,
                    "context_sha256_after": (
                        fault_cases.context_hash(documents) if ok else None
                    ),
                    "content_identity": identity,
                    "synthetic_provenance": synthetic_provenance,
                    "technical_checks": checks,
                    "candidate_explanation": fault_cases._explanation(
                        condition, removed, added, corpus, synthetic_provenance
                    ),
                }
            )

    return _write_fault_cases(
        config,
        contexts,
        case_annotations,
        sources={
            "index_id": index_manifest["index_sha256"],
            "corpus_sha256": index_manifest["corpus_sha256"],
            "retrieval_file_sha256": sha256_file(paths.results / prep.RETRIEVAL_FILENAME),
            "eligibility_file_sha256": sha256_file(paths.results / prep.ELIGIBILITY_FILENAME),
            "questions_sha256": sha256_file(paths.processed / prep.QUESTIONS_FILENAME),
            "annotations_sha256": sha256_file(paths.processed / prep.ANNOTATIONS_FILENAME),
            "edits_file": edits_source,
        },
        eligible_questions=len(eligibility["eligible_question_ids"]),
    )


def _review_row(case_id: str, question_id: str, condition: str, identity: str) -> dict:
    return {
        "case_id": case_id,
        "question_id": question_id,
        "condition": condition,
        "content_identity": identity,
        "review_status": fault_cases.REVIEW_PENDING,
        "observed_state": None,
        "reviewer": None,
        "note": "",
    }


def _write_fault_cases(
    config: ExperimentConfig,
    contexts: list[dict],
    annotations: list[dict],
    sources: dict,
    eligible_questions: int,
) -> dict:
    """Write contexts, research annotations, review rows and the fault manifest.

    A label survives regeneration only while the context content identity is
    unchanged; a changed context gets a fresh pending row and the superseded
    label is recorded explicitly instead of being carried over.
    """
    paths = prep.MainPaths.of(config)
    paths.ensure()
    contexts_path = paths.results / prep.FAULT_CONTEXTS_FILENAME
    annotations_path = paths.results / prep.FAULT_ANNOTATIONS_FILENAME
    reviews_path = paths.results / prep.FAULT_REVIEWS_FILENAME

    hotpotqa.write_jsonl(contexts_path, contexts)
    hotpotqa.write_jsonl(annotations_path, annotations)

    existing = (
        {r["case_id"]: r for r in hotpotqa.read_jsonl(reviews_path)}
        if reviews_path.is_file()
        else {}
    )
    by_case = {a["case_id"]: a for a in annotations}

    reviews: list[dict] = []
    invalidated: list[dict] = []
    preserved = 0
    for context in contexts:
        case_id = context["case_id"]
        annotation = by_case[case_id]
        identity = annotation["content_identity"]
        previous = existing.get(case_id)
        if previous is not None and previous.get("content_identity") == identity:
            reviews.append(previous)
            preserved += 1
            continue
        row = _review_row(case_id, annotation["question_id"], annotation["condition"], identity)
        if previous is not None:
            row["note"] = (
                "previous label invalidated: the context content changed "
                f"(old identity {previous.get('content_identity')}, "
                f"old status {previous.get('review_status')}, "
                f"old observed_state {previous.get('observed_state')})"
            )
            invalidated.append(
                {
                    "case_id": case_id,
                    "old_content_identity": previous.get("content_identity"),
                    "new_content_identity": identity,
                    "old_review_status": previous.get("review_status"),
                    "old_observed_state": previous.get("observed_state"),
                }
            )
        reviews.append(row)
    hotpotqa.write_jsonl(reviews_path, reviews)

    built = {c: 0 for c in fault_cases.CONDITIONS}
    failed = {c: 0 for c in fault_cases.CONDITIONS}
    failure_reasons: dict[str, int] = {}
    for annotation in annotations:
        if annotation["build_status"] == fault_cases.BUILD_OK:
            built[annotation["condition"]] += 1
        else:
            failed[annotation["condition"]] += 1
            reason = f"{annotation['condition']}: {annotation['failure_reason']}"
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    per_question: dict[str, set[str]] = {}
    for annotation in annotations:
        if annotation["build_status"] == fault_cases.BUILD_OK:
            per_question.setdefault(annotation["question_id"], set()).add(annotation["condition"])
    complete = [
        annotation["question_id"]
        for annotation in annotations
        if annotation["condition"] == fault_cases.CONDITION_CLEAN
        and len(per_question.get(annotation["question_id"], ())) == len(fault_cases.CONDITIONS)
    ]

    manifest = {
        "stage": prep.STAGE,
        "author": prep.AUTHOR,
        "fault_format_version": fault_cases.FAULT_FORMAT_VERSION,
        "prepared_at": prep.utc_now(),
        "seed": config.seed,
        "context_size": fault_cases.CONTEXT_SIZE,
        "conditions": list(fault_cases.CONDITIONS),
        "expected_state_by_condition": fault_cases.EXPECTED_STATE,
        "rules": {
            "eligibility": prep.ELIGIBILITY_RULE,
            "partial_choice": fault_cases.PARTIAL_CHOICE_RULE,
            "replacement": fault_cases.REPLACEMENT_RULE,
            "inconsistent_slot": fault_cases.INCONSISTENT_SLOT_RULE,
            "case_id": "sha256('fault-case|<format>|<question_id>|<condition>|<seed>')[:16]",
            "content_identity": CONTENT_IDENTITY_RULE,
            "injection_scope": (
                "first retrieval result only; a retry searches the unchanged main index"
            ),
            "future_sample": prep.FUTURE_SAMPLE_RULE,
        },
        "sources": sources,
        "counts": {
            "eligible_questions": eligible_questions,
            "cases_built": built,
            "construction_failed": failed,
            "construction_failure_reasons": failure_reasons,
            "contexts": len(contexts),
            "complete_quadruples": len(complete),
            "reviews_total": len(reviews),
            "reviews_pending": sum(
                1 for r in reviews if r["review_status"] == fault_cases.REVIEW_PENDING
            ),
            "reviews_preserved": preserved,
            "reviews_invalidated": len(invalidated),
        },
        "complete_quadruple_question_ids": complete,
        "invalidated_reviews": invalidated,
        "file_sha256": {
            prep.FAULT_CONTEXTS_FILENAME: sha256_file(contexts_path),
            prep.FAULT_ANNOTATIONS_FILENAME: sha256_file(annotations_path),
            prep.FAULT_REVIEWS_FILENAME: sha256_file(reviews_path),
        },
        "notes": [
            "fault_contexts.jsonl carries case_id, question_id, question and documents only; "
            "condition names, intended states, gold data and synthetic provenance stay in the "
            "research annotations",
            "structural validation is not semantic approval; every new review row starts pending",
            "the INCONSISTENT edits are hand-drafted by the author; they are not independently "
            "verified and no LLM was used to produce them",
        ],
    }
    hotpotqa.write_json(paths.results / prep.FAULT_MANIFEST_FILENAME, manifest)
    return manifest
