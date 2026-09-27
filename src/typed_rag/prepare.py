"""Stage 2 pipeline: download HotpotQA, validate it, build the pilot files.

The output is split into pipeline inputs (questions, shared corpus) and gold
annotations, plus a manifest and a preparation report.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from typed_rag import hotpotqa
from typed_rag.config import ExperimentConfig
from typed_rag.download import DownloadResult, download_dataset, sha256_file
from typed_rag.hotpotqa import (
    ANNOTATIONS_FILENAME,
    CORPUS_FILENAME,
    DATA_FORMAT_VERSION,
    MAIN_CANDIDATES_FILENAME,
    MANIFEST_FILENAME,
    PILOT_IDS_FILENAME,
    QUESTIONS_FILENAME,
    SELECTION_ALGORITHM,
    DatasetError,
)

REPORT_FILENAME = "data_preparation_report.json"
YES_NO_ANSWERS = {"yes", "no"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _download_summary(result: DownloadResult, configured_urls: list[str]) -> dict:
    return {
        "configured_urls": configured_urls,
        "source_url_used": result.source_url,
        "reused_existing_file": result.reused_existing,
        "raw_path": str(result.path),
        "raw_size_bytes": result.size_bytes,
        "raw_sha256": result.sha256,
        "attempts": result.attempts,
        "provenance": result.provenance,
    }


def _reason_category(reason: str) -> str:
    """Replace indices, numbers and quoted names so reasons group into classes."""
    text = re.sub(r"\[\d+\]", "[i]", reason)
    text = re.sub(r"'[^']*'", "'X'", text)
    return re.sub(r"\b\d+\b", "N", text)


def _exclusion_summary(excluded: list[hotpotqa.ExcludedRecord]) -> dict:
    reason_counter: Counter[str] = Counter()
    for item in excluded:
        for reason in item.reasons:
            reason_counter[_reason_category(reason)] += 1
    return {
        "excluded_count": len(excluded),
        "reason_histogram": dict(sorted(reason_counter.items())),
        "excluded_records": [
            {
                "question_id": item.question_id,
                "position": item.position,
                "reasons": item.reasons,
            }
            for item in excluded
        ],
    }


def _pilot_distribution(annotations: list[dict]) -> dict:
    types = Counter(item["type"] for item in annotations)
    levels = Counter(item["level"] for item in annotations)
    yes_no = sum(1 for item in annotations if item["answer"].strip().lower() in YES_NO_ANSWERS)
    supporting_docs = Counter(len(item["supporting_doc_ids"]) for item in annotations)
    supporting_sentences = Counter(len(item["supporting_sentences"]) for item in annotations)
    return {
        "type": dict(sorted(types.items())),
        "level": dict(sorted(levels.items())),
        "yes_no_answers": yes_no,
        "other_answers": len(annotations) - yes_no,
        "supporting_documents_per_question": {
            str(key): value for key, value in sorted(supporting_docs.items())
        },
        "supporting_sentences_per_question": {
            str(key): value for key, value in sorted(supporting_sentences.items())
        },
    }


def prepare_data(config: ExperimentConfig, force_download: bool = False) -> dict:
    """Run the whole stage 2 preparation and return the report payload."""
    config.ensure_directories()
    dataset = config.dataset
    processed_dir = config.processed_dir
    processed_dir.mkdir(parents=True, exist_ok=True)

    urls = [dataset.url, *dataset.mirror_urls]
    download = download_dataset(urls, config.raw_dataset_path, force=force_download)

    records = hotpotqa.load_raw_records(download.path)
    outcome = hotpotqa.validate_records(records)

    pilot_ids, candidate_ids = hotpotqa.select_pilot_ids(
        outcome.valid, config.seed, config.pilot_size
    )
    by_id = {record["_id"]: record for record in outcome.valid}
    pilot_records = [by_id[qid] for qid in pilot_ids]

    questions = hotpotqa.build_questions(pilot_records)
    corpus, paragraphs_before_dedup = hotpotqa.build_corpus(pilot_records)
    annotations = hotpotqa.build_annotations(pilot_records)

    hotpotqa.write_jsonl(processed_dir / QUESTIONS_FILENAME, questions)
    hotpotqa.write_jsonl(processed_dir / CORPUS_FILENAME, corpus)
    hotpotqa.write_jsonl(processed_dir / ANNOTATIONS_FILENAME, annotations)
    hotpotqa.write_json(
        processed_dir / PILOT_IDS_FILENAME,
        {
            "seed": config.seed,
            "pilot_size": config.pilot_size,
            "selection_algorithm": SELECTION_ALGORITHM,
            "question_ids": pilot_ids,
        },
    )
    hotpotqa.write_json(
        processed_dir / MAIN_CANDIDATES_FILENAME,
        {
            "count": len(candidate_ids),
            "note": (
                "Structurally valid records left after the pilot, in selection order. "
                "Reserve pool for the main study; the main sample is not fixed yet."
            ),
            "question_ids": candidate_ids,
        },
    )

    data_files = [
        QUESTIONS_FILENAME,
        CORPUS_FILENAME,
        ANNOTATIONS_FILENAME,
        PILOT_IDS_FILENAME,
        MAIN_CANDIDATES_FILENAME,
    ]
    file_hashes = {name: sha256_file(processed_dir / name) for name in data_files}

    manifest = {
        "dataset_name": dataset.name,
        "dataset_split": dataset.split,
        "dataset_setting": dataset.setting,
        "dataset_version": dataset.version,
        "official_source_url": dataset.url,
        "configured_mirror_urls": list(dataset.mirror_urls),
        "source_url_used": download.source_url,
        "reused_existing_file": download.reused_existing,
        "provenance": download.provenance,
        "raw_file": dataset.filename,
        "raw_sha256": download.sha256,
        "raw_size_bytes": download.size_bytes,
        "sha256_note": (
            "Self-computed SHA-256 of the local file. It proves the file is identical "
            "between runs; it is not a match against an official published checksum, "
            "because the dataset publishes none."
        ),
        "seed": config.seed,
        "pilot_size": config.pilot_size,
        "selection_algorithm": SELECTION_ALGORITHM,
        "records_total": outcome.total,
        "records_valid": len(outcome.valid),
        "records_excluded": len(outcome.excluded),
        "pilot_question_ids": pilot_ids,
        "main_candidate_count": len(candidate_ids),
        "unique_documents": len(corpus),
        "paragraphs_before_deduplication": paragraphs_before_dedup,
        "data_file_sha256": file_hashes,
        "data_format_version": DATA_FORMAT_VERSION,
        "prepared_at": _utc_now(),
    }
    hotpotqa.write_json(processed_dir / MANIFEST_FILENAME, manifest)

    overlap = sorted(set(pilot_ids) & set(candidate_ids))
    forbidden_hits = sorted(
        {field for document in corpus for field in hotpotqa.FORBIDDEN_DOCUMENT_FIELDS if field in document}
    )
    questions_fields = sorted({key for row in questions for key in row})

    report = {
        "generated_at": _utc_now(),
        "status": "ok" if not overlap and not forbidden_hits else "failed",
        "experiment_name": config.experiment_name,
        "dataset": dataset.label,
        "download": _download_summary(download, urls),
        "structural_checks": {
            "records_total": outcome.total,
            "records_valid": len(outcome.valid),
            **_exclusion_summary(outcome.excluded),
        },
        "pilot": {
            "size": len(pilot_ids),
            "question_ids": pilot_ids,
            "demo_question_ids": pilot_ids[:10],
            "distribution": _pilot_distribution(annotations),
        },
        "corpus": {
            "paragraphs_before_deduplication": paragraphs_before_dedup,
            "unique_documents": len(corpus),
            "duplicates_collapsed": paragraphs_before_dedup - len(corpus),
            "distinct_titles": len({document["title"] for document in corpus}),
        },
        "separation_checks": {
            "pilot_candidate_overlap": overlap,
            "pilot_candidate_overlap_count": len(overlap),
            "main_candidate_count": len(candidate_ids),
            "forbidden_fields_in_corpus": forbidden_hits,
            "question_file_fields": questions_fields,
        },
        "output_files": {
            name: str(processed_dir / name) for name in [*data_files, MANIFEST_FILENAME]
        },
        "data_file_sha256": file_hashes,
        "data_format_version": DATA_FORMAT_VERSION,
    }

    report_path = config.paths["results"] / REPORT_FILENAME
    hotpotqa.write_json(report_path, report)

    if report["status"] != "ok":
        raise DatasetError(
            "Preparation finished with failed separation checks; see " f"{report_path}"
        )
    return report
