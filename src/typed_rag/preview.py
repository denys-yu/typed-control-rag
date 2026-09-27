"""Human inspection of prepared pilot items.

This is a reading aid for the researcher, not a retrieval step: it never uses
an index and it never scores anything. Gold labels stay hidden unless they are
explicitly requested.
"""

from __future__ import annotations

from typed_rag import hotpotqa
from typed_rag.config import ExperimentConfig
from typed_rag.hotpotqa import PILOT_IDS_FILENAME, DatasetError

GOLD_BANNER = "RESEARCHER VIEW WITH GOLD LABELS - not a pipeline input"


def _pilot_ids(config: ExperimentConfig) -> list[str]:
    payload = hotpotqa.read_json(config.processed_dir / PILOT_IDS_FILENAME)
    ids = payload.get("question_ids")
    if not isinstance(ids, list) or not ids:
        raise DatasetError(f"No pilot question ids in {config.processed_dir / PILOT_IDS_FILENAME}")
    return ids


def _raw_record(config: ExperimentConfig, question_id: str) -> dict:
    """Fetch one raw record for display; the prepared files stay untouched."""
    for record in hotpotqa.load_raw_records(config.raw_dataset_path):
        if record.get("_id") == question_id:
            return record
    raise DatasetError(f"Question id not found in the raw dataset: {question_id}")


def format_example(config: ExperimentConfig, index: int, with_gold: bool) -> str:
    ids = _pilot_ids(config)
    if not 0 <= index < len(ids):
        raise DatasetError(f"Example index {index} out of range (0..{len(ids) - 1})")

    question_id = ids[index]
    record = _raw_record(config, question_id)

    lines = [
        f"pilot index   : {index} of {len(ids) - 1}",
        f"question_id   : {question_id}",
        f"question      : {record['question']}",
        "",
        "source contexts (as given by the dataset, no gold markers):",
    ]
    for title, sentences in record["context"]:
        lines.append(f"  [{hotpotqa.document_id(title, sentences)[:12]}] {title}")
        for position, sentence in enumerate(sentences):
            lines.append(f"      {position}: {sentence.strip()}")

    if not with_gold:
        lines += ["", "gold labels hidden; add --with-gold to show them"]
        return "\n".join(lines)

    annotations = {item["question_id"]: item for item in hotpotqa.load_pilot_annotations(config.processed_dir)}
    gold = annotations.get(question_id)
    if gold is None:
        raise DatasetError(f"No annotation found for {question_id}")

    lines += [
        "",
        f"--- {GOLD_BANNER} ---",
        f"answer        : {gold['answer']}",
        f"type / level  : {gold['type']} / {gold['level']}",
        "supporting facts:",
    ]
    for fact in gold["supporting_sentences"]:
        lines.append(
            f"  [{fact['doc_id'][:12]}] {fact['title']} #{fact['sentence_index']}: "
            f"{fact['sentence'].strip()}"
        )
    return "\n".join(lines)


def format_summary(config: ExperimentConfig) -> str:
    """Short overview of what is currently prepared on disk."""
    manifest = hotpotqa.load_manifest(config.processed_dir)
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    corpus = hotpotqa.load_pilot_corpus(config.processed_dir)
    candidates = hotpotqa.read_json(config.processed_dir / hotpotqa.MAIN_CANDIDATES_FILENAME)

    lines = [
        f"dataset            : {manifest['dataset_name']} / {manifest['dataset_split']} / "
        f"{manifest['dataset_setting']} / {manifest['dataset_version']}",
        f"source used        : {manifest['source_url_used'] or 'existing local file'}",
        f"raw sha256         : {manifest['raw_sha256']}",
        f"raw size (bytes)   : {manifest['raw_size_bytes']}",
        f"records total      : {manifest['records_total']}",
        f"records valid      : {manifest['records_valid']}",
        f"records excluded   : {manifest['records_excluded']}",
        f"seed / pilot_size  : {manifest['seed']} / {manifest['pilot_size']}",
        f"pilot questions    : {len(questions)}",
        f"corpus documents   : {len(corpus)} (from {manifest['paragraphs_before_deduplication']} paragraphs)",
        f"main candidates    : {candidates['count']}",
        f"data format        : {manifest['data_format_version']}",
        f"prepared at (UTC)  : {manifest['prepared_at']}",
        f"processed dir      : {config.processed_dir}",
    ]
    return "\n".join(lines)
