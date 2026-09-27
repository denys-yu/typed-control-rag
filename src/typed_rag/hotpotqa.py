"""HotpotQA structural checks, pilot selection and prepared-data layout.

Three concerns are kept apart on purpose:

* structural validation of raw records (technical only, never semantic);
* construction of pipeline inputs (questions, shared corpus) that carry no
  gold labels at all;
* construction of annotations (answers, supporting facts) used only for
  experiment preparation and evaluation.

Loading questions or the corpus must never pull annotations in; that is why
each artefact has its own loader.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

DATA_FORMAT_VERSION = "1.0"

QUESTIONS_FILENAME = "pilot_questions.jsonl"
CORPUS_FILENAME = "pilot_corpus.jsonl"
ANNOTATIONS_FILENAME = "pilot_annotations.jsonl"
PILOT_IDS_FILENAME = "pilot_ids.json"
MAIN_CANDIDATES_FILENAME = "main_candidate_ids.json"
MANIFEST_FILENAME = "manifest.json"

SELECTION_ALGORITHM = (
    "keep structurally valid records; sort by question id; "
    "shuffle with random.Random(seed); take the first pilot_size"
)

# Fields a pipeline input document is never allowed to carry.
FORBIDDEN_DOCUMENT_FIELDS = (
    "answer",
    "supporting_facts",
    "is_supporting",
    "gold_state",
    "label",
    "type",
    "level",
)


class DatasetError(Exception):
    """Raised when the raw dataset cannot be used as a whole."""


@dataclass(frozen=True)
class ExcludedRecord:
    """A raw record that failed structural validation."""

    question_id: str | None
    position: int
    reasons: list[str]


@dataclass(frozen=True)
class ValidationOutcome:
    valid: list[dict]
    excluded: list[ExcludedRecord]
    total: int


def document_id(title: str, sentences: list[str]) -> str:
    """Stable SHA-256 identifier of a paragraph.

    Built from a canonical JSON form of (title, sentences) so that identical
    paragraphs collapse and same-title/different-text paragraphs do not.
    The built-in hash() is unsuitable: it is salted per process.
    """
    canonical = json.dumps(
        {"title": title, "sentences": list(sentences)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def paragraph_text(sentences: list[str]) -> str:
    """Deterministic paragraph text: original sentence order joined by newline."""
    return "\n".join(sentences)


def load_raw_records(path: Path) -> list[dict]:
    """Read the raw HotpotQA JSON file."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise DatasetError(f"Cannot read raw dataset: {path} ({exc})") from exc
    except ValueError as exc:
        raise DatasetError(f"Raw dataset is not valid JSON: {path} ({exc})") from exc

    if not isinstance(data, list):
        raise DatasetError(f"Raw dataset must be a JSON array: {path}")
    return data


def _check_context(record: dict, reasons: list[str]) -> dict[str, list[str]] | None:
    """Validate `context` and return {title: sentences} when it is well formed."""
    context = record.get("context")
    if not isinstance(context, list) or not context:
        reasons.append("context is missing or not a non-empty list")
        return None

    titles: dict[str, list[str]] = {}
    duplicated: list[str] = []
    well_formed = True

    for position, item in enumerate(context):
        if not isinstance(item, list) or len(item) != 2:
            reasons.append(f"context[{position}] is not a [title, sentences] pair")
            well_formed = False
            continue
        title, sentences = item
        if not isinstance(title, str) or not title.strip():
            reasons.append(f"context[{position}] has an empty or non-string title")
            well_formed = False
            continue
        if not isinstance(sentences, list) or not all(isinstance(s, str) for s in sentences):
            reasons.append(f"context[{position}] sentences are not a list of strings")
            well_formed = False
            continue
        if title in titles:
            duplicated.append(title)
            well_formed = False
            continue
        titles[title] = sentences

    if duplicated:
        # Ambiguous: a supporting fact could not be mapped to a single paragraph.
        reasons.append(f"duplicate context titles: {', '.join(sorted(set(duplicated)))}")

    return titles if well_formed else None


def _check_supporting_facts(
    record: dict, titles: dict[str, list[str]] | None, reasons: list[str]
) -> None:
    facts = record.get("supporting_facts")
    if not isinstance(facts, list) or not facts:
        reasons.append("supporting_facts is missing or not a non-empty list")
        return

    for position, item in enumerate(facts):
        if not isinstance(item, list) or len(item) != 2:
            reasons.append(f"supporting_facts[{position}] is not a [title, sentence_index] pair")
            continue
        title, sentence_index = item
        if not isinstance(title, str) or not title.strip():
            reasons.append(f"supporting_facts[{position}] has an empty or non-string title")
            continue
        if not isinstance(sentence_index, int) or isinstance(sentence_index, bool):
            reasons.append(f"supporting_facts[{position}] sentence index is not an integer")
            continue
        if titles is None:
            continue
        if title not in titles:
            reasons.append(
                f"supporting_facts[{position}] refers to a title absent from context: {title}"
            )
            continue
        # Sentence indices are zero-based.
        if not 0 <= sentence_index < len(titles[title]):
            reasons.append(
                f"supporting_facts[{position}] sentence index {sentence_index} "
                f"out of range for '{title}' ({len(titles[title])} sentences)"
            )


def validate_record(record: object) -> list[str]:
    """Return the structural reasons why a record is unusable (empty == usable).

    Technical checks only: nothing here judges difficulty, question type or
    whether a retriever would find enough context.
    """
    reasons: list[str] = []
    if not isinstance(record, dict):
        return ["record is not a JSON object"]

    for field in ("_id", "question", "answer", "type", "level"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"field '{field}' is missing, empty or not a string")

    titles = _check_context(record, reasons)
    _check_supporting_facts(record, titles, reasons)
    return reasons


def validate_records(records: list) -> ValidationOutcome:
    """Validate every raw record, treating duplicate question ids as unusable.

    Records are never silently overwritten in a dict: every occurrence of a
    duplicated id is excluded and reported.
    """
    id_positions: dict[str, list[int]] = {}
    for position, record in enumerate(records):
        if isinstance(record, dict):
            question_id = record.get("_id")
            if isinstance(question_id, str) and question_id.strip():
                id_positions.setdefault(question_id, []).append(position)

    duplicated_ids = {qid for qid, positions in id_positions.items() if len(positions) > 1}

    valid: list[dict] = []
    excluded: list[ExcludedRecord] = []

    for position, record in enumerate(records):
        reasons = validate_record(record)
        question_id = record.get("_id") if isinstance(record, dict) else None
        if isinstance(question_id, str) and question_id in duplicated_ids:
            occurrences = len(id_positions[question_id])
            reasons.append(f"duplicate question id ({occurrences} occurrences)")
        if reasons:
            excluded.append(
                ExcludedRecord(
                    question_id=question_id if isinstance(question_id, str) else None,
                    position=position,
                    reasons=reasons,
                )
            )
        else:
            valid.append(record)

    return ValidationOutcome(valid=valid, excluded=excluded, total=len(records))


def select_pilot_ids(
    valid_records: list[dict], seed: int, pilot_size: int
) -> tuple[list[str], list[str]]:
    """Return (pilot ids, remaining candidate ids) using a local RNG.

    The shuffle is driven by random.Random(seed) so the global random state is
    untouched and the selection is reproducible.
    """
    ordered = sorted(record["_id"] for record in valid_records)
    if len(ordered) < pilot_size:
        raise DatasetError(
            f"Only {len(ordered)} structurally valid records available, "
            f"but pilot_size is {pilot_size}"
        )
    rng = random.Random(seed)
    shuffled = list(ordered)
    rng.shuffle(shuffled)
    return shuffled[:pilot_size], shuffled[pilot_size:]


def build_questions(records: list[dict]) -> list[dict]:
    """Pipeline input: question id and question text only."""
    return [{"question_id": record["_id"], "question": record["question"]} for record in records]


def build_corpus(records: list[dict]) -> tuple[list[dict], int]:
    """Shared corpus of every paragraph (supporting and distractor alike).

    Returns (documents, paragraphs_before_deduplication). Only fully identical
    title+sentences pairs collapse; identical titles with different text stay
    separate documents. No gold marker is ever attached to a document.
    """
    documents: list[dict] = []
    seen: set[str] = set()
    total = 0

    for record in records:
        for title, sentences in record["context"]:
            total += 1
            doc_id = document_id(title, sentences)
            if doc_id in seen:
                continue
            seen.add(doc_id)
            documents.append(
                {
                    "doc_id": doc_id,
                    "title": title,
                    "sentences": list(sentences),
                    "text": paragraph_text(sentences),
                }
            )
    return documents, total


def build_annotations(records: list[dict]) -> list[dict]:
    """Gold annotations: answers, supporting facts and their document mapping.

    For experiment preparation and evaluation only - never a pipeline input.
    """
    annotations: list[dict] = []
    for record in records:
        by_title = {title: sentences for title, sentences in record["context"]}
        doc_ids = {title: document_id(title, sentences) for title, sentences in record["context"]}

        supporting = []
        for title, sentence_index in record["supporting_facts"]:
            supporting.append(
                {
                    "title": title,
                    "doc_id": doc_ids[title],
                    "sentence_index": sentence_index,
                    "sentence": by_title[title][sentence_index],
                }
            )

        annotations.append(
            {
                "question_id": record["_id"],
                "answer": record["answer"],
                "type": record["type"],
                "level": record["level"],
                "supporting_facts": [list(fact) for fact in record["supporting_facts"]],
                "supporting_sentences": supporting,
                "supporting_doc_ids": sorted({item["doc_id"] for item in supporting}),
                "context_doc_ids": [doc_ids[title] for title, _ in record["context"]],
            }
        )
    return annotations


# --- deterministic writing and separate loaders ---------------------------------


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """Write rows as JSONL with stable key order and LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict) -> None:
    """Write a JSON document with fixed indentation and LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise DatasetError(
            f"Prepared file not found: {path}. Run: python -m typed_rag --prepare-data"
        )
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise DatasetError(f"Malformed JSONL at {path}:{number} ({exc})") from exc
    return rows


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise DatasetError(
            f"Prepared file not found: {path}. Run: python -m typed_rag --prepare-data"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise DatasetError(f"Malformed JSON at {path} ({exc})") from exc


def load_pilot_questions(processed_dir: Path) -> list[dict]:
    """Pipeline input: pilot questions. Reads nothing else."""
    return read_jsonl(processed_dir / QUESTIONS_FILENAME)


def load_pilot_corpus(processed_dir: Path) -> list[dict]:
    """Pipeline input: shared corpus. Reads nothing else."""
    return read_jsonl(processed_dir / CORPUS_FILENAME)


def load_pilot_annotations(processed_dir: Path) -> list[dict]:
    """Gold annotations. Evaluation and preparation only."""
    return read_jsonl(processed_dir / ANNOTATIONS_FILENAME)


def load_manifest(processed_dir: Path) -> dict:
    return read_json(processed_dir / MANIFEST_FILENAME)
