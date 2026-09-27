"""Stage 6: reproducible initial-context variants with controlled defects.

Only the *first* retrieval result is modified. After a retry the pipeline
searches the unchanged corpus as usual; the injector is never applied again.

Four conditions per technically eligible question (both gold supporting
documents inside the normal top-5):

    CLEAN         the unchanged top-5;
    PARTIAL       one gold supporting document removed (seeded choice);
    EMPTY         both gold supporting documents removed;
    INCONSISTENT  both gold documents kept, one non-gold document replaced by
                  a synthetic document that contradicts a gold sentence.

Removed documents are replaced by the highest-ranked admissible documents
outside the initial five (ranks 6..10 of the saved ranking), so every
condition has exactly five documents and unchanged documents keep their
positions. Replacement documents are *distractor candidates*: nothing here
proves they carry no alternative evidence.

The defect operation and the actual state of the context are different
things. `expected_state` is a hypothesis; the actual state is decided by a
human reviewer in reviews.jsonl. Nothing in this module decides pipeline
actions, and the pipeline input file (contexts.jsonl) carries no condition
name, expected state, gold answer, supporting facts or synthetic markers.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from typed_rag import hotpotqa, nodes, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.download import sha256_file
from typed_rag.hotpotqa import DatasetError

FAULT_FORMAT_VERSION = "1.0"
FAULT_CASES_DIRNAME = "fault_cases"
CONTEXTS_FILENAME = "contexts.jsonl"
ANNOTATIONS_FILENAME = "annotations.jsonl"
REVIEWS_FILENAME = "reviews.jsonl"
MANIFEST_FILENAME = "manifest.json"
EDITS_RELPATH = Path("config") / "inconsistent_edits.json"
SAVED_RETRIEVAL_FILENAME = "pilot_retrieval.jsonl"

CONDITION_CLEAN = "CLEAN"
CONDITION_PARTIAL = "PARTIAL"
CONDITION_EMPTY = "EMPTY"
CONDITION_INCONSISTENT = "INCONSISTENT"
CONDITIONS = (CONDITION_CLEAN, CONDITION_PARTIAL, CONDITION_EMPTY, CONDITION_INCONSISTENT)

EXPECTED_STATE = {
    CONDITION_CLEAN: nodes.STATE_OK,
    CONDITION_PARTIAL: nodes.STATE_PARTIAL,
    CONDITION_EMPTY: nodes.STATE_EMPTY,
    CONDITION_INCONSISTENT: nodes.STATE_INCONSISTENT,
}

CONTEXT_SIZE = 5

REVIEW_PENDING = "pending"
REVIEW_APPROVED = "approved"
REVIEW_REJECTED = "rejected"
REVIEW_STATUSES = (REVIEW_PENDING, REVIEW_APPROVED, REVIEW_REJECTED)

BUILD_OK = "built"
BUILD_FAILED = "construction_failed"

REPLACEMENT_RULE = (
    "removed documents are replaced, position by position, with the highest-ranked "
    "documents of the saved top-10 ranking that are outside the initial top-5, are not "
    "gold supporting documents and are not already in the context"
)
PARTIAL_CHOICE_RULE = (
    "random.Random(f'{seed}:{question_id}').choice(sorted(supporting_doc_ids)) selects the "
    "removed gold document"
)
INCONSISTENT_SLOT_RULE = (
    "the lowest-ranked non-gold document of the initial top-5 is replaced by the synthetic "
    "document; the synthetic document is a copy of the target gold document with one sentence "
    "edited, under the same title; doc_id = SHA-256 of canonical JSON of title + sentences"
)


class FaultCaseError(Exception):
    """Raised when fault cases cannot be built or read."""


def fault_cases_dir(config: ExperimentConfig) -> Path:
    return config.paths["data_processed"] / FAULT_CASES_DIRNAME


def edits_path(config: ExperimentConfig) -> Path:
    return config.project_root / EDITS_RELPATH


def case_id_for(question_id: str, condition: str, seed: int) -> str:
    """Opaque, deterministic case identifier (does not reveal the condition)."""
    payload = f"fault-case|{FAULT_FORMAT_VERSION}|{question_id}|{condition}|{seed}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def context_hash(documents: list[dict]) -> str:
    return nodes.sha256_json([document["doc_id"] for document in documents])


# --- inputs -------------------------------------------------------------------------


def load_saved_retrieval(config: ExperimentConfig) -> tuple[list[dict], dict]:
    """The stage 3 ranking, verified against the current index and questions."""
    path = config.paths["results"] / SAVED_RETRIEVAL_FILENAME
    if not path.is_file():
        raise FaultCaseError(f"Saved retrieval not found: {path}. Run: python -m typed_rag --evaluate-retrieval")
    rows = hotpotqa.read_jsonl(path)

    manifest_path = config.index_dir / retrieval.INDEX_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise FaultCaseError(f"Index manifest not found: {manifest_path}")
    manifest = hotpotqa.read_json(manifest_path)
    current_corpus = sha256_file(retrieval.corpus_path(config))
    if manifest.get("corpus_sha256") != current_corpus:
        raise FaultCaseError("Index manifest corpus_sha256 does not match the current corpus")

    questions = {q["question_id"]: q["question"] for q in hotpotqa.load_pilot_questions(config.processed_dir)}
    problems = []
    if len(rows) != len(questions):
        problems.append(f"{len(rows)} saved rows for {len(questions)} pilot questions")
    for row in rows:
        if row.get("index_id") != manifest.get("index_sha256"):
            problems.append(f"{row.get('question_id')}: index_id differs from the current index")
        if questions.get(row.get("question_id")) != row.get("question"):
            problems.append(f"{row.get('question_id')}: question text differs from pilot_questions.jsonl")
        if len(row.get("results", [])) < CONTEXT_SIZE:
            problems.append(f"{row.get('question_id')}: fewer than {CONTEXT_SIZE} results")
    if problems:
        raise FaultCaseError("Saved retrieval does not match the current setup:\n  " + "\n  ".join(problems))
    provenance = {
        "file": str(path),
        "sha256": sha256_file(path),
        "index_id": manifest["index_sha256"],
        "corpus_sha256": manifest["corpus_sha256"],
        "saved_top_k": len(rows[0]["results"]),
    }
    return rows, provenance


def load_edits(config: ExperimentConfig) -> tuple[dict, str]:
    path = edits_path(config)
    if not path.is_file():
        raise FaultCaseError(f"Edits file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["edits"], sha256_file(path)


# --- construction --------------------------------------------------------------------


def _document_record(document: dict) -> dict:
    return {"doc_id": document["doc_id"], "title": document["title"], "text": document["text"]}


def _replacements(ranking: list[dict], corpus: dict, excluded: set[str], count: int) -> list[dict]:
    """Highest-ranked admissible documents outside the initial five."""
    chosen = []
    for result in ranking[CONTEXT_SIZE:]:
        if len(chosen) == count:
            break
        if result["doc_id"] in excluded:
            continue
        chosen.append(corpus[result["doc_id"]])
        excluded.add(result["doc_id"])
    return chosen


def _build_synthetic(edit: dict, corpus_by_title: dict) -> tuple[dict | None, dict, str | None]:
    """Copy of the target gold document with one sentence replaced."""
    target = corpus_by_title.get(edit["target_title"])
    if target is None:
        return None, {}, f"target title not in corpus: {edit['target_title']!r}"
    index = edit["sentence_index"]
    if not 0 <= index < len(target["sentences"]):
        return None, {}, f"sentence_index {index} out of range for {edit['target_title']!r}"
    if target["sentences"][index] != edit["original_sentence"]:
        return None, {}, "original_sentence does not match the corpus sentence"
    if edit["edited_sentence"] == edit["original_sentence"]:
        return None, {}, "edited_sentence is identical to original_sentence"
    sentences = list(target["sentences"])
    sentences[index] = edit["edited_sentence"]
    doc_id = hotpotqa.document_id(target["title"], sentences)
    synthetic = {
        "doc_id": doc_id,
        "title": target["title"],
        "sentences": sentences,
        "text": hotpotqa.paragraph_text(sentences),
    }
    provenance = {
        "kind": "sentence_edit_copy",
        "source_doc_id": target["doc_id"],
        "source_title": target["title"],
        "sentence_index": index,
        "original_fragment": edit["original_sentence"],
        "edited_fragment": edit["edited_sentence"],
        "edit": {"replace_sentence": index, "with": edit["edited_sentence"]},
        "incompatible_claims": [edit["claim_original"], edit["claim_edited"]],
        "property": edit["property"],
        "relevance_to_question": edit["relevance"],
    }
    return synthetic, provenance, None


def _checks_common(documents: list[dict], initial_ids: list[str]) -> dict:
    ids = [d["doc_id"] for d in documents]
    return {
        "document_count_ok": len(documents) == CONTEXT_SIZE,
        "no_duplicates": len(set(ids)) == len(ids),
        "unchanged_positions_kept": all(
            ids[i] == initial_ids[i] for i in range(min(len(ids), len(initial_ids))) if ids[i] in initial_ids
        ),
    }


def build_cases(config: ExperimentConfig) -> dict:
    """Build every candidate case for every pilot question; returns all artefacts."""
    rows, retrieval_provenance = load_saved_retrieval(config)
    edits, edits_sha256 = load_edits(config)
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    annotations = {a["question_id"]: a for a in hotpotqa.load_pilot_annotations(config.processed_dir)}
    corpus_docs = hotpotqa.load_pilot_corpus(config.processed_dir)
    corpus = {d["doc_id"]: d for d in corpus_docs}
    corpus_by_title = {d["title"]: d for d in corpus_docs}
    ranking_by_qid = {row["question_id"]: row["results"] for row in rows}
    seed = config.seed

    contexts: list[dict] = []
    case_annotations: list[dict] = []
    eligibility: list[dict] = []

    for position, question in enumerate(questions):
        qid = question["question_id"]
        gold = annotations[qid]
        supporting = sorted(gold["supporting_doc_ids"])
        ranking = ranking_by_qid[qid]
        initial_ids = [r["doc_id"] for r in ranking[:CONTEXT_SIZE]]
        found = [s for s in supporting if s in initial_ids]
        eligible = len(found) == len(supporting) and len(supporting) == 2
        record = {
            "question_index": position,
            "question_id": qid,
            "eligible": eligible,
            "gold_documents_in_top5": len(found),
            "gold_document_count": len(supporting),
        }
        if not eligible:
            record["reason"] = (
                f"only {len(found)} of {len(supporting)} gold supporting documents in the normal top-5; "
                "the paired-context procedure needs both"
            )
            eligibility.append(record)
            continue
        eligibility.append(record)

        initial_docs = [corpus[doc_id] for doc_id in initial_ids]
        initial_hash = context_hash(initial_docs)

        for condition in CONDITIONS:
            case_id = case_id_for(qid, condition, seed)
            documents = [dict(d) for d in initial_docs]
            removed: list[str] = []
            added: list[str] = []
            synthetic_provenance: dict | None = None
            build_status = BUILD_OK
            failure_reason = None
            checks: dict = {}

            if condition == CONDITION_PARTIAL:
                removed = [random.Random(f"{seed}:{qid}").choice(supporting)]
            elif condition == CONDITION_EMPTY:
                removed = list(supporting)

            if condition in (CONDITION_PARTIAL, CONDITION_EMPTY):
                excluded = set(initial_ids) | set(supporting)
                replacements = _replacements(ranking, corpus, excluded, len(removed))
                if len(replacements) < len(removed):
                    build_status, failure_reason = BUILD_FAILED, "not enough admissible replacement documents in the saved top-10"
                else:
                    for doc_id, replacement in zip(removed, replacements):
                        documents[initial_ids.index(doc_id)] = replacement
                        added.append(replacement["doc_id"])
                ids = [d["doc_id"] for d in documents]
                checks = {
                    **_checks_common(documents, initial_ids),
                    "removed_absent": all(r not in ids for r in removed),
                    "added_present": all(a in ids for a in added),
                    "remaining_gold_count": sum(1 for s in supporting if s in ids),
                    "remaining_gold_count_ok": sum(1 for s in supporting if s in ids) == (1 if condition == CONDITION_PARTIAL else 0),
                }

            elif condition == CONDITION_INCONSISTENT:
                edit = edits.get(qid)
                if edit is None:
                    build_status, failure_reason = BUILD_FAILED, "no hand-prepared edit for this question"
                else:
                    synthetic, synthetic_provenance, error = _build_synthetic(edit, corpus_by_title)
                    if error:
                        build_status, failure_reason = BUILD_FAILED, error
                    elif synthetic["doc_id"] in corpus:
                        build_status, failure_reason = BUILD_FAILED, "synthetic document collides with a corpus document"
                    elif synthetic_provenance["source_doc_id"] not in supporting:
                        build_status, failure_reason = BUILD_FAILED, "edit target is not a gold supporting document"
                    else:
                        non_gold_positions = [i for i, doc_id in enumerate(initial_ids) if doc_id not in supporting]
                        slot = non_gold_positions[-1]
                        removed = [initial_ids[slot]]
                        documents[slot] = synthetic
                        added = [synthetic["doc_id"]]
                ids = [d["doc_id"] for d in documents]
                source = corpus.get((synthetic_provenance or {}).get("source_doc_id", ""))
                checks = {
                    **_checks_common(documents, initial_ids),
                    "both_gold_present": all(s in ids for s in supporting),
                    "synthetic_present": bool(added) and added[0] in ids,
                    "synthetic_text_differs_from_source": bool(source) and documents[ids.index(added[0])]["text"] != source["text"] if added else False,
                    "synthetic_not_in_corpus": bool(added) and added[0] not in corpus,
                }
            else:  # CLEAN
                checks = {**_checks_common(documents, initial_ids), "identical_to_initial": context_hash(documents) == initial_hash}

            checks["all_passed"] = build_status == BUILD_OK and all(v is True for k, v in checks.items() if k not in ("remaining_gold_count",))

            if build_status == BUILD_OK:
                contexts.append(
                    {
                        "case_id": case_id,
                        "question_id": qid,
                        "question": question["question"],
                        "documents": [_document_record(d) for d in documents],
                    }
                )
            case_annotations.append(
                {
                    "case_id": case_id,
                    "question_id": qid,
                    "question_index": position,
                    "condition": condition,
                    "operation": {
                        CONDITION_CLEAN: "none",
                        CONDITION_PARTIAL: "remove_one_gold_document_and_replace",
                        CONDITION_EMPTY: "remove_both_gold_documents_and_replace",
                        CONDITION_INCONSISTENT: "replace_one_non_gold_document_with_contradicting_synthetic_copy",
                    }[condition],
                    "expected_state": EXPECTED_STATE[condition],
                    "expected_state_note": "hypothesis implied by the operation; the actual state is set by a reviewer in reviews.jsonl",
                    "build_status": build_status,
                    "failure_reason": failure_reason,
                    "initial_doc_ids": initial_ids,
                    "gold_supporting_doc_ids": supporting,
                    "removed_doc_ids": removed,
                    "added_doc_ids": added,
                    "added_doc_kind": "distractor_candidate" if condition in (CONDITION_PARTIAL, CONDITION_EMPTY) else ("synthetic" if condition == CONDITION_INCONSISTENT else None),
                    "final_doc_ids": [d["doc_id"] for d in documents] if build_status == BUILD_OK else None,
                    "context_sha256_before": initial_hash,
                    "context_sha256_after": context_hash(documents) if build_status == BUILD_OK else None,
                    "synthetic_provenance": synthetic_provenance,
                    "technical_checks": checks,
                    "candidate_explanation": _explanation(condition, removed, added, corpus, synthetic_provenance),
                }
            )

    return {
        "contexts": contexts,
        "annotations": case_annotations,
        "eligibility": eligibility,
        "retrieval_provenance": retrieval_provenance,
        "edits_sha256": edits_sha256,
    }


def _explanation(condition: str, removed: list[str], added: list[str], corpus: dict, provenance: dict | None) -> str:
    titles = lambda ids: ", ".join(corpus[i]["title"] for i in ids if i in corpus)
    if condition == CONDITION_CLEAN:
        return "unchanged top-5; expected OK only if the two gold documents really carry every needed fact"
    if condition == CONDITION_PARTIAL:
        return (
            f"gold document '{titles(removed)}' removed and replaced by distractor candidate '{titles(added)}'; "
            "expected PARTIAL only if the missing fact is not recoverable from the remaining documents"
        )
    if condition == CONDITION_EMPTY:
        return (
            f"both gold documents ('{titles(removed)}') removed and replaced by distractor candidates "
            f"('{titles(added)}'); expected EMPTY only if no remaining document helps establish the needed facts"
        )
    if provenance:
        return (
            f"non-gold document '{titles(removed)}' replaced by a copy of '{provenance['source_title']}' whose "
            f"sentence {provenance['sentence_index']} now states: {provenance['incompatible_claims'][1]} "
            f"(original: {provenance['incompatible_claims'][0]}); the original document stays in the context"
        )
    return "construction failed"


# --- writing and reading --------------------------------------------------------------


def _review_template(case_id: str) -> dict:
    return {"case_id": case_id, "review_status": REVIEW_PENDING, "observed_state": None, "reviewer": None, "note": ""}


def write_cases(config: ExperimentConfig, built: dict) -> dict:
    """Write contexts, annotations, reviews (preserving existing reviews) and manifest."""
    out_dir = fault_cases_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)

    contexts_path = out_dir / CONTEXTS_FILENAME
    annotations_path = out_dir / ANNOTATIONS_FILENAME
    reviews_path = out_dir / REVIEWS_FILENAME

    hotpotqa.write_jsonl(contexts_path, built["contexts"])
    hotpotqa.write_jsonl(annotations_path, built["annotations"])

    existing = {r["case_id"]: r for r in hotpotqa.read_jsonl(reviews_path)} if reviews_path.is_file() else {}
    built_ids = [c["case_id"] for c in built["contexts"]]
    reviews = [existing.get(case_id, _review_template(case_id)) for case_id in built_ids]
    preserved = sum(1 for case_id in built_ids if case_id in existing)
    hotpotqa.write_jsonl(reviews_path, reviews)

    counts = {c: 0 for c in CONDITIONS}
    failed = {c: 0 for c in CONDITIONS}
    for a in built["annotations"]:
        (counts if a["build_status"] == BUILD_OK else failed)[a["condition"]] += 1

    manifest = {
        "fault_format_version": FAULT_FORMAT_VERSION,
        "prepared_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": config.seed,
        "context_size": CONTEXT_SIZE,
        "conditions": list(CONDITIONS),
        "expected_state_by_condition": EXPECTED_STATE,
        "rules": {
            "eligibility": "both gold supporting documents present in the normal top-5 of the saved ranking",
            "partial_choice": PARTIAL_CHOICE_RULE,
            "replacement": REPLACEMENT_RULE,
            "inconsistent_slot": INCONSISTENT_SLOT_RULE,
            "case_id": "sha256('fault-case|<format>|<question_id>|<condition>|<seed>')[:16]",
            "injection_scope": "first retrieval result only; retries search the unchanged index",
        },
        "sources": {
            "saved_retrieval": built["retrieval_provenance"],
            "edits_file": {"path": str(edits_path(config)), "sha256": built["edits_sha256"]},
            "corpus_sha256": sha256_file(retrieval.corpus_path(config)),
            "questions_sha256": sha256_file(config.processed_dir / hotpotqa.QUESTIONS_FILENAME),
            "annotations_sha256": sha256_file(config.processed_dir / hotpotqa.ANNOTATIONS_FILENAME),
        },
        "counts": {
            "pilot_questions": len(built["eligibility"]),
            "eligible_questions": sum(1 for e in built["eligibility"] if e["eligible"]),
            "ineligible_questions": sum(1 for e in built["eligibility"] if not e["eligible"]),
            "cases_built": counts,
            "construction_failed": failed,
            "reviews_preserved": preserved,
        },
        "eligibility": built["eligibility"],
        "file_sha256": {
            CONTEXTS_FILENAME: sha256_file(contexts_path),
            ANNOTATIONS_FILENAME: sha256_file(annotations_path),
            REVIEWS_FILENAME: sha256_file(reviews_path),
        },
    }
    hotpotqa.write_json(out_dir / MANIFEST_FILENAME, manifest)
    return manifest


def load_fault_contexts(config: ExperimentConfig) -> list[dict]:
    """Pipeline input: question and documents only. Reads nothing else."""
    return hotpotqa.read_jsonl(fault_cases_dir(config) / CONTEXTS_FILENAME)


def load_fault_annotations(config: ExperimentConfig) -> list[dict]:
    """Research metadata: never read by the pipeline."""
    return hotpotqa.read_jsonl(fault_cases_dir(config) / ANNOTATIONS_FILENAME)


def load_fault_reviews(config: ExperimentConfig) -> list[dict]:
    path = fault_cases_dir(config) / REVIEWS_FILENAME
    return hotpotqa.read_jsonl(path) if path.is_file() else []


def load_fault_manifest(config: ExperimentConfig) -> dict:
    return hotpotqa.read_json(fault_cases_dir(config) / MANIFEST_FILENAME)


def find_context(config: ExperimentConfig, case_id: str) -> dict:
    for context in load_fault_contexts(config):
        if context["case_id"] == case_id:
            return context
    raise FaultCaseError(f"Unknown case_id: {case_id}")


def find_annotation(config: ExperimentConfig, case_id: str) -> dict:
    for annotation in load_fault_annotations(config):
        if annotation["case_id"] == case_id:
            return annotation
    raise FaultCaseError(f"Unknown case_id: {case_id}")


def review_status(config: ExperimentConfig, case_id: str) -> dict:
    for review in load_fault_reviews(config):
        if review["case_id"] == case_id:
            return review
    return _review_template(case_id)


# --- running a case through the controller -----------------------------------------------


def run_fault_case(
    config: ExperimentConfig,
    case_id: str,
    branch: str,
    dry_run: bool = False,
    transport=None,
    index=None,
    model=None,
) -> dict:
    """Feed a prepared context to the stage 5 controller as its initial context.

    A real run requires an approved case. A dry run is allowed for a pending
    case and is marked as such in run.json. The controller receives only the
    question and the documents; the review status is written to run.json after
    the run, as research metadata, and never influences an action.
    """
    from typed_rag import controller, rag_run

    context = find_context(config, case_id)
    review = review_status(config, case_id)
    if not dry_run and review["review_status"] != REVIEW_APPROVED:
        raise FaultCaseError(
            f"Case {case_id} has review_status={review['review_status']!r}; a real run requires an approved case "
            "(dry runs are allowed)"
        )
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    positions = [i for i, q in enumerate(questions) if q["question_id"] == context["question_id"]]
    if not positions:
        raise FaultCaseError(f"Case {case_id} refers to a question that is not in the pilot")
    run = controller.run_controlled(
        config, positions[0], branch, dry_run=dry_run, transport=transport, index=index, model=model,
        initial_context=context,
    )
    run["fault_case_review_status"] = review["review_status"]
    run["fault_case_note"] = (
        "dry run on a case that is not approved; technical check only" if dry_run and review["review_status"] != REVIEW_APPROVED
        else "case approved by a reviewer" if review["review_status"] == REVIEW_APPROVED else ""
    )
    rag_run._write_json(Path(run["run_dir"]) / controller.RUN_FILENAME, run)
    return run


# --- review validation -----------------------------------------------------------------


def validate_reviews(config: ExperimentConfig) -> dict:
    """Check reviews.jsonl and count what is ready. Never changes any status."""
    annotations = {a["case_id"]: a for a in load_fault_annotations(config)}
    built = {a["case_id"] for a in annotations.values() if a["build_status"] == BUILD_OK}
    reviews = load_fault_reviews(config)
    problems: list[str] = []
    seen: set[str] = set()
    status_counts = {s: 0 for s in REVIEW_STATUSES}
    approved_matching = set()
    approved_other_state = []

    for number, review in enumerate(reviews, start=1):
        case_id = review.get("case_id")
        if case_id not in built:
            problems.append(f"line {number}: unknown or unbuilt case_id {case_id!r}")
            continue
        if case_id in seen:
            problems.append(f"line {number}: duplicate case_id {case_id}")
            continue
        seen.add(case_id)
        status = review.get("review_status")
        if status not in REVIEW_STATUSES:
            problems.append(f"line {number}: review_status must be one of {REVIEW_STATUSES}, got {status!r}")
            continue
        observed = review.get("observed_state")
        if observed is not None and observed not in nodes.STATES:
            problems.append(f"line {number}: observed_state must be null or one of {nodes.STATES}, got {observed!r}")
            continue
        if status == REVIEW_APPROVED and observed is None:
            problems.append(f"line {number}: approved review needs a non-null observed_state")
            continue
        if status == REVIEW_APPROVED and not (review.get("reviewer") or "").strip():
            problems.append(f"line {number}: approved review needs a reviewer")
            continue
        status_counts[status] += 1
        if status == REVIEW_APPROVED:
            if observed == annotations[case_id]["expected_state"]:
                approved_matching.add(case_id)
            else:
                approved_other_state.append({"case_id": case_id, "expected_state": annotations[case_id]["expected_state"], "observed_state": observed})

    missing = sorted(built - seen)
    if missing:
        problems.append(f"{len(missing)} built cases have no review entry (run --prepare-fault-cases to add pending entries)")

    by_question: dict[str, dict] = {}
    for a in annotations.values():
        if a["build_status"] == BUILD_OK:
            by_question.setdefault(a["question_id"], {})[a["condition"]] = a["case_id"]
    ready = [
        qid for qid, cases in sorted(by_question.items())
        if all(c in cases and cases[c] in approved_matching for c in CONDITIONS)
    ]
    return {
        "valid": not problems,
        "problems": problems,
        "review_counts": status_counts,
        "reviewed_cases": len(seen),
        "built_cases": len(built),
        "approved_with_expected_state": len(approved_matching),
        "approved_with_other_state": approved_other_state,
        "ready_full_quadruples": ready,
        "ready_full_quadruple_count": len(ready),
        "note": "a question enters the paired series only when all four variants are approved with observed_state equal to expected_state",
    }


# --- formatting ------------------------------------------------------------------------


def format_summary(config: ExperimentConfig) -> str:
    manifest = load_fault_manifest(config)
    counts = manifest["counts"]
    validation = validate_reviews(config)
    lines = [
        f"fault cases dir : {fault_cases_dir(config)}",
        f"format version  : {manifest['fault_format_version']}  prepared at {manifest['prepared_at']}",
        f"index id        : {manifest['sources']['saved_retrieval']['index_id'][:16]}",
        f"pilot questions : {counts['pilot_questions']}  eligible {counts['eligible_questions']}  ineligible {counts['ineligible_questions']}",
        "cases built     : " + ", ".join(f"{c}={n}" for c, n in counts["cases_built"].items()),
        "construction failed: " + ", ".join(f"{c}={n}" for c, n in counts["construction_failed"].items()),
        "reviews         : " + ", ".join(f"{s}={n}" for s, n in validation["review_counts"].items()),
        f"ready quadruples: {validation['ready_full_quadruple_count']}",
    ]
    if not validation["valid"]:
        lines.append("review problems : " + "; ".join(validation["problems"]))
    lines.append("")
    lines.append("ineligible questions:")
    for e in manifest["eligibility"]:
        if not e["eligible"]:
            lines.append(f"  [{e['question_index']:2d}] {e['question_id']}: {e['reason']}")
    return "\n".join(lines)


def format_case(config: ExperimentConfig, case_id: str, with_annotations: bool) -> str:
    context = find_context(config, case_id)
    lines = [f"case id       : {case_id}", f"question id   : {context['question_id']}", f"question      : {context['question']}", ""]
    for position, document in enumerate(context["documents"], start=1):
        lines.append(f"[{position}] {document['title']}  ({document['doc_id'][:12]})")
        lines.append("    " + document["text"].replace("\n", "\n    "))
    if not with_annotations:
        return "\n".join(lines)
    annotation = find_annotation(config, case_id)
    review = review_status(config, case_id)
    lines += [
        "",
        "--- researcher view (never sent to the LLM) ---",
        f"condition     : {annotation['condition']}  operation: {annotation['operation']}",
        f"expected state: {annotation['expected_state']} (hypothesis)",
        f"build status  : {annotation['build_status']}" + (f" - {annotation['failure_reason']}" if annotation["failure_reason"] else ""),
        f"gold docs     : {[d[:12] for d in annotation['gold_supporting_doc_ids']]}",
        f"removed       : {[d[:12] for d in annotation['removed_doc_ids']]}",
        f"added         : {[d[:12] for d in annotation['added_doc_ids']]} ({annotation['added_doc_kind']})",
        f"context hash  : {annotation['context_sha256_before'][:12]} -> {(annotation['context_sha256_after'] or '')[:12]}",
        f"checks        : {annotation['technical_checks']}",
        f"explanation   : {annotation['candidate_explanation']}",
    ]
    if annotation["synthetic_provenance"]:
        p = annotation["synthetic_provenance"]
        lines += [
            f"synthetic     : copy of '{p['source_title']}', sentence {p['sentence_index']} edited",
            f"  original    : {p['original_fragment'].strip()}",
            f"  edited      : {p['edited_fragment'].strip()}",
            f"  claims      : {p['incompatible_claims'][0]}  <->  {p['incompatible_claims'][1]}",
            f"  property    : {p['property']}",
            f"  relevance   : {p['relevance_to_question']}",
        ]
    lines.append(f"review        : {review['review_status']}  observed_state={review['observed_state']}  reviewer={review['reviewer']}  note={review['note']!r}")
    return "\n".join(lines)


def format_validation(report: dict) -> str:
    lines = [
        f"reviews valid   : {report['valid']}",
        f"built cases     : {report['built_cases']}  reviewed {report['reviewed_cases']}",
        "statuses        : " + ", ".join(f"{s}={n}" for s, n in report["review_counts"].items()),
        f"approved = expected state: {report['approved_with_expected_state']}",
        f"approved with other state: {len(report['approved_with_other_state'])}",
        f"ready quadruples: {report['ready_full_quadruple_count']} {report['ready_full_quadruples']}",
    ]
    for problem in report["problems"]:
        lines.append(f"  problem: {problem}")
    lines.append(report["note"])
    return "\n".join(lines)
