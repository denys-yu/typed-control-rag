"""Stage 12: offline preparation of the main-study candidate pool, index and faults.

This module lives outside `src/typed_rag` on purpose: every file under
`src/typed_rag` is bound by the frozen pilot plan, and stage 12 must not change
any of them. All substantive components are reused from the package:

* structural validation and the `doc_id` / de-duplication rules (`hotpotqa`);
* the pinned embedding model, text rule, normalisation, truncation diagnostics
  and exact cosine ranking (`retrieval`);
* the fault-construction rules, case identifiers and context hashing
  (`fault_cases`).

Main-study artefacts use separate paths and never overwrite pilot files:

    data/processed/main/        questions, corpus, annotations, candidates
    artifacts/main_retrieval/   embeddings, documents, index manifest
    results/main_preparation/   selection rule, eligibility, faults, reviews

Nothing here calls a provider API.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from typed_rag import hotpotqa, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.download import sha256_file

STAGE = "stage12_main_preparation"
MAIN_FORMAT_VERSION = "1.0"
AUTHOR = "Denys Yuvzhenko"

CANDIDATE_POOL_SIZE = 300
TARGET_QUESTIONS = 60
PREPARATION_TOP_K = 10

PROCESSED_DIRNAME = "main"
INDEX_DIRNAME = "main_retrieval"
RESULTS_DIRNAME = "main_preparation"

QUESTIONS_FILENAME = "main_questions.jsonl"
CORPUS_FILENAME = "main_corpus.jsonl"
ANNOTATIONS_FILENAME = "main_annotations.jsonl"
CANDIDATES_FILENAME = "main_candidates.json"
DATA_MANIFEST_FILENAME = "manifest.json"

SELECTION_RULE_FILENAME = "selection_rule.json"
RETRIEVAL_FILENAME = "main_retrieval.jsonl"
ELIGIBILITY_FILENAME = "eligibility.json"
FAULT_CONTEXTS_FILENAME = "fault_contexts.jsonl"
FAULT_ANNOTATIONS_FILENAME = "fault_annotations.jsonl"
FAULT_REVIEWS_FILENAME = "fault_reviews.jsonl"
FAULT_MANIFEST_FILENAME = "fault_manifest.json"
REVIEW_EXPORT_DIRNAME = "review_package"
VALIDATION_FILENAME = "validation.json"

EDITS_RELPATH = Path("config") / "main_inconsistent_edits.json"

SELECTION_ALGORITHM = (
    "keep structurally valid dev/distractor records; drop every original pilot question id; "
    "sort the remaining question ids ascending; draw CANDIDATE_POOL_SIZE ids without "
    "replacement with random.Random(seed).sample(sorted_ids, CANDIDATE_POOL_SIZE); "
    "keep the drawn order as the candidate order"
)
SELECTION_INPUT_RULE = (
    "selection reads only the raw dataset, its structural validity and the pilot id list; "
    "no retrieval result, model output, answer type or annotation difficulty is consulted"
)
FUTURE_SAMPLE_RULE = (
    "the main evaluation sample is the first 60 questions, in the fixed randomized candidate "
    "order, whose four fault variants are all approved with observed_state equal to the "
    "intended state; no model outcome may influence this selection"
)
ELIGIBILITY_RULE = (
    "a candidate is technically eligible when its record has exactly two distinct gold "
    "supporting documents and both appear in the normal top-5 of the main index"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_json(payload: object) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MainPaths:
    """Main-study locations, all separate from the pilot's."""

    processed: Path
    index: Path
    results: Path

    @classmethod
    def of(cls, config: ExperimentConfig) -> "MainPaths":
        return cls(
            processed=config.paths["data_processed"] / PROCESSED_DIRNAME,
            index=config.paths["artifacts"] / INDEX_DIRNAME,
            results=config.paths["results"] / RESULTS_DIRNAME,
        )

    def ensure(self) -> None:
        for path in (self.processed, self.index, self.results):
            path.mkdir(parents=True, exist_ok=True)


# --- step 2: candidate selection --------------------------------------------------


def select_candidates(config: ExperimentConfig, pool_size: int = CANDIDATE_POOL_SIZE) -> dict:
    """Draw the fixed screening pool and write it with its selection rule.

    Runs before any retrieval: the rule and the manifest are on disk before the
    main index exists, so the pool cannot be shaped by retrieval outcomes.
    """
    paths = MainPaths.of(config)
    paths.ensure()

    raw_path = config.raw_dataset_path
    records = hotpotqa.load_raw_records(raw_path)
    outcome = hotpotqa.validate_records(records)

    pilot_ids = hotpotqa.read_json(config.processed_dir / hotpotqa.PILOT_IDS_FILENAME)[
        "question_ids"
    ]
    excluded = set(pilot_ids)

    available = sorted(record["_id"] for record in outcome.valid if record["_id"] not in excluded)
    if len(available) < pool_size:
        raise hotpotqa.DatasetError(
            f"Only {len(available)} candidate ids available for a pool of {pool_size}"
        )
    rng = random.Random(config.seed)
    candidate_ids = rng.sample(available, pool_size)

    by_id = {record["_id"]: record for record in outcome.valid}
    candidate_records = [by_id[qid] for qid in candidate_ids]

    questions = hotpotqa.build_questions(candidate_records)
    corpus, paragraphs_before_dedup = hotpotqa.build_corpus(candidate_records)
    annotations = hotpotqa.build_annotations(candidate_records)

    hotpotqa.write_jsonl(paths.processed / QUESTIONS_FILENAME, questions)
    hotpotqa.write_jsonl(paths.processed / CORPUS_FILENAME, corpus)
    hotpotqa.write_jsonl(paths.processed / ANNOTATIONS_FILENAME, annotations)
    hotpotqa.write_json(
        paths.processed / CANDIDATES_FILENAME,
        {
            "count": len(candidate_ids),
            "seed": config.seed,
            "pool_size": pool_size,
            "selection_algorithm": SELECTION_ALGORITHM,
            "question_ids": candidate_ids,
        },
    )

    selection_rule = {
        "stage": STAGE,
        "author": AUTHOR,
        "purpose": (
            f"fixed screening pool for the main study; a pool of {pool_size} is a buffer over "
            "the rough 200-candidate estimate and is not a guarantee of obtaining 60 approved "
            "questions"
        ),
        "seed": config.seed,
        "pool_size": pool_size,
        "target_questions": TARGET_QUESTIONS,
        "selection_algorithm": SELECTION_ALGORITHM,
        "selection_inputs": SELECTION_INPUT_RULE,
        "rng": "random.Random(seed).sample over the ascending id list; the global RNG is untouched",
        "source": {
            "raw_file": raw_path.name,
            "raw_sha256": sha256_file(raw_path),
            "dataset": config.dataset.label,
            "records_total": outcome.total,
            "records_valid": len(outcome.valid),
            "records_excluded_structurally": len(outcome.excluded),
        },
        "exclusions": {
            "pilot_question_ids": sorted(excluded),
            "pilot_question_count": len(excluded),
            "reason": (
                "all 30 original pilot ids are excluded, screened-but-unused ones included, "
                "because their eligibility and review outcomes are already known"
            ),
            "available_after_exclusion": len(available),
        },
        "future_sample_rule": FUTURE_SAMPLE_RULE,
        "eligibility_rule": ELIGIBILITY_RULE,
        "candidate_ids": candidate_ids,
    }
    selection_rule["selection_rule_sha256"] = sha256_json(selection_rule)
    selection_rule["recorded_at"] = utc_now()
    hotpotqa.write_json(paths.results / SELECTION_RULE_FILENAME, selection_rule)

    data_files = [QUESTIONS_FILENAME, CORPUS_FILENAME, ANNOTATIONS_FILENAME, CANDIDATES_FILENAME]
    manifest = {
        "stage": STAGE,
        "main_format_version": MAIN_FORMAT_VERSION,
        "data_format_version": hotpotqa.DATA_FORMAT_VERSION,
        "prepared_at": utc_now(),
        "dataset": config.dataset.label,
        "raw_file": raw_path.name,
        "raw_sha256": sha256_file(raw_path),
        "seed": config.seed,
        "candidate_count": len(candidate_ids),
        "selection_algorithm": SELECTION_ALGORITHM,
        "selection_rule_sha256": selection_rule["selection_rule_sha256"],
        "excluded_pilot_question_ids": sorted(excluded),
        "unique_documents": len(corpus),
        "paragraphs_before_deduplication": paragraphs_before_dedup,
        "duplicates_collapsed": paragraphs_before_dedup - len(corpus),
        "distinct_titles": len({document["title"] for document in corpus}),
        "data_file_sha256": {name: sha256_file(paths.processed / name) for name in data_files},
        "separation_note": (
            "main_questions.jsonl and main_corpus.jsonl are the only pipeline inputs; "
            "main_annotations.jsonl is read for preparation and evaluation only"
        ),
    }
    hotpotqa.write_json(paths.processed / DATA_MANIFEST_FILENAME, manifest)
    return {"selection_rule": selection_rule, "manifest": manifest}


# --- step 3: main corpus index ------------------------------------------------------


def load_main_corpus(paths: MainPaths) -> list[dict]:
    """Corpus documents in the canonical order that defines the matrix rows."""
    documents = hotpotqa.read_jsonl(paths.processed / CORPUS_FILENAME)
    return sorted(documents, key=lambda document: document["doc_id"])


def build_main_index(config: ExperimentConfig, rebuild: bool = False) -> dict:
    """Embed the main corpus with the pinned model and freeze the index identity.

    Same model, revision, text rule, normalisation, dtype, row order and ranking
    rule as the pilot index; only the corpus and the directory differ.
    """
    paths = MainPaths.of(config)
    paths.ensure()
    manifest_path = paths.index / retrieval.INDEX_MANIFEST_FILENAME
    corpus_file = paths.processed / CORPUS_FILENAME
    corpus_sha256 = sha256_file(corpus_file)

    if manifest_path.is_file() and not rebuild:
        manifest = hotpotqa.read_json(manifest_path)
        if manifest.get("corpus_sha256") != corpus_sha256:
            raise retrieval.StaleIndexError(
                "Stale main index: corpus_sha256 differs from the stored index. "
                "Rebuild explicitly with --build-index --rebuild."
            )
        manifest["reused_existing_index"] = True
        return manifest

    documents = load_main_corpus(paths)
    if not documents:
        raise retrieval.IndexError_(f"Main corpus is empty: {corpus_file}")

    model = retrieval.load_model(config)
    texts = [retrieval.build_text(document) for document in documents]
    truncation = retrieval.count_truncated(model, texts)

    embeddings = model.encode(
        texts,
        batch_size=config.retrieval.batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32)

    if embeddings.shape[0] != len(documents):
        raise retrieval.IndexError_(
            f"Embedding matrix has {embeddings.shape[0]} rows for {len(documents)} documents"
        )
    if not np.isfinite(embeddings).all():
        raise retrieval.IndexError_("Embedding matrix contains non-finite values")

    np.save(paths.index / retrieval.EMBEDDINGS_FILENAME, embeddings, allow_pickle=False)
    hotpotqa.write_jsonl(paths.index / retrieval.DOCUMENTS_FILENAME, documents)

    norms = np.linalg.norm(embeddings, axis=1)
    manifest = {
        "stage": STAGE,
        "index_scope": "main_study",
        "corpus_sha256": corpus_sha256,
        "model_name": config.retrieval.model_name,
        "model_revision": config.retrieval.model_revision,
        "text_rule": retrieval.TEXT_RULE,
        "normalisation": retrieval.NORMALISATION,
        "dtype": retrieval.DTYPE,
        "max_seq_length": truncation["max_seq_length"],
        "index_format_version": retrieval.INDEX_FORMAT_VERSION,
        "document_count": len(documents),
        "dimension": int(embeddings.shape[1]),
        "batch_size": config.retrieval.batch_size,
        "device": "cpu",
        "document_order_rule": retrieval.DOCUMENT_ORDER_RULE,
        "ranking_rule": retrieval.RANKING_RULE,
        "normalised": True,
        "norm_min": float(norms.min()),
        "norm_max": float(norms.max()),
        "truncation": truncation,
        "truncation_note": (
            "diagnostic only; the model and max_seq_length are unchanged and the stored "
            "document always keeps its full original text"
        ),
        "corpus_file": str(corpus_file),
        "library_versions": retrieval.library_versions(),
        "built_at": utc_now(),
        "file_sha256": {
            retrieval.EMBEDDINGS_FILENAME: sha256_file(paths.index / retrieval.EMBEDDINGS_FILENAME),
            retrieval.DOCUMENTS_FILENAME: sha256_file(paths.index / retrieval.DOCUMENTS_FILENAME),
        },
        "reused_existing_index": False,
    }
    manifest["index_sha256"] = retrieval._index_identity(manifest)
    hotpotqa.write_json(manifest_path, manifest)
    return manifest


def load_main_index(config: ExperimentConfig) -> retrieval.LoadedIndex:
    """Load the frozen main index, refusing a stale one instead of rebuilding."""
    paths = MainPaths.of(config)
    manifest_path = paths.index / retrieval.INDEX_MANIFEST_FILENAME
    matrix_path = paths.index / retrieval.EMBEDDINGS_FILENAME
    documents_path = paths.index / retrieval.DOCUMENTS_FILENAME
    for path in (manifest_path, matrix_path, documents_path):
        if not path.is_file():
            raise retrieval.MissingIndexError(f"No main index at {path}. Run: --build-index")

    manifest = hotpotqa.read_json(manifest_path)
    embeddings = np.load(matrix_path, allow_pickle=False)
    documents = hotpotqa.read_jsonl(documents_path)

    problems = []
    if embeddings.shape[0] != len(documents):
        problems.append(f"{embeddings.shape[0]} rows for {len(documents)} documents")
    current_corpus = sha256_file(paths.processed / CORPUS_FILENAME)
    if manifest.get("corpus_sha256") != current_corpus:
        problems.append("corpus_sha256 differs from the current main corpus")
    for field in ("model_name", "model_revision"):
        if manifest.get(field) != getattr(config.retrieval, field):
            problems.append(f"{field} differs from the configuration")
    if problems:
        raise retrieval.StaleIndexError("Stale main index:\n  " + "\n  ".join(problems))
    return retrieval.LoadedIndex(embeddings=embeddings, documents=documents, manifest=manifest)


# --- step 4: retrieval over the frozen index and technical eligibility ---------------


def run_main_retrieval(config: ExperimentConfig, top_k: int = PREPARATION_TOP_K) -> dict:
    """Rank the whole main corpus for every candidate question.

    Reads questions and the index only. Gold annotations are not opened here,
    so no ranking can be gold-aware.
    """
    paths = MainPaths.of(config)
    index = load_main_index(config)
    questions = hotpotqa.read_jsonl(paths.processed / QUESTIONS_FILENAME)
    model = retrieval.load_model(config)

    rows = []
    for position, question in enumerate(questions):
        hits = retrieval.search(index, model, question["question"], top_k)
        rows.append(
            {
                "candidate_position": position,
                "question_id": question["question_id"],
                "question": question["question"],
                "index_id": index.index_id,
                "top_k": top_k,
                "experimental_top_k": config.retrieval.top_k,
                "results": [hit.as_dict() for hit in hits],
            }
        )
    path = paths.results / RETRIEVAL_FILENAME
    hotpotqa.write_jsonl(path, rows)
    return {
        "file": str(path),
        "sha256": sha256_file(path),
        "questions": len(rows),
        "top_k": top_k,
        "index_id": index.index_id,
    }


def measure_eligibility(config: ExperimentConfig) -> dict:
    """Apply the technical eligibility rule to the saved ranking.

    This is the first step that opens main_annotations.jsonl, and it runs after
    the ranking has been written.
    """
    paths = MainPaths.of(config)
    index_manifest = hotpotqa.read_json(paths.index / retrieval.INDEX_MANIFEST_FILENAME)
    rows = hotpotqa.read_jsonl(paths.results / RETRIEVAL_FILENAME)
    annotations = {
        a["question_id"]: a for a in hotpotqa.read_jsonl(paths.processed / ANNOTATIONS_FILENAME)
    }
    experimental_top_k = config.retrieval.top_k

    records = []
    for row in rows:
        qid = row["question_id"]
        gold = annotations[qid]
        supporting = sorted(gold["supporting_doc_ids"])
        initial_ids = [r["doc_id"] for r in row["results"][:experimental_top_k]]
        found = [doc_id for doc_id in supporting if doc_id in initial_ids]
        found_top10 = [doc_id for doc_id in supporting if doc_id in [r["doc_id"] for r in row["results"]]]

        reasons = []
        if len(supporting) != 2:
            reasons.append(
                f"record has {len(supporting)} distinct gold supporting documents, the paired "
                "construction needs exactly 2"
            )
        if len(found) != len(supporting):
            reasons.append(
                f"only {len(found)} of {len(supporting)} gold supporting documents in the normal "
                f"top-{experimental_top_k}"
            )
        records.append(
            {
                "candidate_position": row["candidate_position"],
                "question_id": qid,
                "eligible": not reasons,
                "gold_document_count": len(supporting),
                "gold_documents_in_top_k": len(found),
                "gold_documents_in_top_10": len(found_top10),
                "gold_ranks": [
                    next(
                        (r["rank"] for r in row["results"] if r["doc_id"] == doc_id),
                        None,
                    )
                    for doc_id in supporting
                ],
                "exclusion_reasons": reasons,
            }
        )

    eligible = [r for r in records if r["eligible"]]
    excluded = [r for r in records if not r["eligible"]]
    reason_histogram: dict[str, int] = {}
    for record in excluded:
        for reason in record["exclusion_reasons"]:
            reason_histogram[reason] = reason_histogram.get(reason, 0) + 1

    coverage = {
        "questions": len(records),
        "both_gold_in_top_k": sum(1 for r in records if r["gold_documents_in_top_k"] == 2),
        "one_gold_in_top_k": sum(1 for r in records if r["gold_documents_in_top_k"] == 1),
        "no_gold_in_top_k": sum(1 for r in records if r["gold_documents_in_top_k"] == 0),
        "both_gold_in_top_10": sum(1 for r in records if r["gold_documents_in_top_10"] == 2),
        "gold_documents_total": sum(r["gold_document_count"] for r in records),
        "gold_documents_found_in_top_k": sum(r["gold_documents_in_top_k"] for r in records),
    }
    coverage["document_recall_at_top_k"] = round(
        coverage["gold_documents_found_in_top_k"] / coverage["gold_documents_total"], 4
    )

    payload = {
        "stage": STAGE,
        "measured_at": utc_now(),
        "rule": ELIGIBILITY_RULE,
        "experimental_top_k": experimental_top_k,
        "preparation_top_k": rows[0]["top_k"] if rows else None,
        "index_id": index_manifest["index_sha256"],
        "index_frozen_before_measurement": True,
        "counts": {
            "candidates": len(records),
            "eligible": len(eligible),
            "excluded": len(excluded),
            "target_questions": TARGET_QUESTIONS,
            "shortfall_against_target": max(0, TARGET_QUESTIONS - len(eligible)),
        },
        "attrition": {
            "pool": len(records),
            "technically_eligible": len(eligible),
            "yield": round(len(eligible) / len(records), 4) if records else None,
        },
        "coverage": coverage,
        "exclusion_reason_histogram": reason_histogram,
        "eligible_question_ids": [r["question_id"] for r in eligible],
        "records": records,
        "note": (
            "technical eligibility only; nothing here judges the semantic sufficiency of a "
            "context, and no parameter was tuned to raise the yield"
        ),
    }
    hotpotqa.write_json(paths.results / ELIGIBILITY_FILENAME, payload)
    return payload
