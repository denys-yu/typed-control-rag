"""Local dense retrieval: exact cosine search over the shared pilot corpus.

The index is nothing more than a saved matrix of normalised embeddings, the
matching documents in row order, and a manifest describing how it was built.
300 documents need no vector database.

Nothing in this module reads gold annotations, and nothing here restricts the
search to the ten source paragraphs of a question: search always runs over the
whole shared corpus.
"""

from __future__ import annotations

import json
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from typed_rag import hotpotqa
from typed_rag.config import ExperimentConfig
from typed_rag.download import sha256_file

EMBEDDINGS_FILENAME = "embeddings.npy"
DOCUMENTS_FILENAME = "documents.jsonl"
INDEX_MANIFEST_FILENAME = "index_manifest.json"

INDEX_FORMAT_VERSION = "1.0"
TEXT_RULE = "title + chr(10) + text"
DOCUMENT_ORDER_RULE = "documents sorted by full doc_id ascending; matrix rows follow that order"
RANKING_RULE = (
    "score = dot product of L2-normalised float32 embeddings (cosine similarity); "
    "rank by descending score, ties broken by ascending doc_id"
)
NORMALISATION = "l2"
DTYPE = "float32"

# Manifest fields that must agree with the current corpus and configuration.
# batch_size is recorded but does not invalidate an index on its own.
INVALIDATING_FIELDS = (
    "corpus_sha256",
    "model_name",
    "model_revision",
    "text_rule",
    "normalisation",
    "dtype",
    "max_seq_length",
    "index_format_version",
)


class IndexError_(Exception):
    """Base class for index problems."""


class MissingIndexError(IndexError_):
    """Raised when no index has been built yet."""


class StaleIndexError(IndexError_):
    """Raised when the stored index no longer matches corpus or configuration."""


class SearchError(Exception):
    """Raised for invalid search input."""


@dataclass(frozen=True)
class SearchHit:
    rank: int
    doc_id: str
    title: str
    score: float
    text: str

    def as_dict(self, score_digits: int = 6) -> dict:
        """Rounding happens here, for display and logging only - never before ranking."""
        return {
            "rank": self.rank,
            "doc_id": self.doc_id,
            "title": self.title,
            "score": round(self.score, score_digits),
            "text": self.text,
        }


@dataclass(frozen=True)
class LoadedIndex:
    embeddings: np.ndarray
    documents: list[dict]
    manifest: dict

    @property
    def size(self) -> int:
        return len(self.documents)

    @property
    def index_id(self) -> str:
        """Short identity of this index, for result files."""
        return self.manifest["index_sha256"]


# --- model access ---------------------------------------------------------------


def library_versions() -> dict:
    """Actual versions of the libraries that define the embeddings."""
    versions = {"python": platform.python_version(), "numpy": np.__version__}
    for name, module_name in (
        ("torch", "torch"),
        ("sentence_transformers", "sentence_transformers"),
        ("transformers", "transformers"),
    ):
        try:
            module = __import__(module_name)
        except ImportError:
            versions[name] = None
        else:
            versions[name] = getattr(module, "__version__", None)
    return versions


def load_model(config: ExperimentConfig) -> Any:
    """Load the pinned embedding model on CPU in evaluation mode.

    The revision is a commit SHA, never a moving branch. If the model cannot be
    loaded, the error propagates: no other model is ever substituted.
    """
    import torch
    from sentence_transformers import SentenceTransformer

    cache_dir = config.model_cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)

    model = SentenceTransformer(
        config.retrieval.model_name,
        revision=config.retrieval.model_revision,
        cache_folder=str(cache_dir),
        device="cpu",
    )
    model.eval()
    torch.set_grad_enabled(False)
    return model


def build_text(document: dict) -> str:
    """Embedding input for a document: title, newline, paragraph text."""
    return document["title"] + "\n" + document["text"]


def count_truncated(model: Any, texts: list[str]) -> dict:
    """How many texts the model would truncate, measured without truncating.

    Truncation only affects the embedding; the stored document always keeps its
    full original text.
    """
    max_seq_length = int(model.max_seq_length)
    tokenizer = model.tokenizer
    # Special tokens count towards the limit, so keep them in the measurement.
    lengths = [
        len(tokenizer(text, add_special_tokens=True, truncation=False)["input_ids"])
        for text in texts
    ]
    truncated = [length for length in lengths if length > max_seq_length]
    return {
        "max_seq_length": max_seq_length,
        "documents_truncated": len(truncated),
        "max_token_length": max(lengths) if lengths else 0,
        "mean_token_length": round(sum(lengths) / len(lengths), 2) if lengths else 0.0,
        "tokens_over_limit_max": max(truncated) - max_seq_length if truncated else 0,
    }


# --- index construction ----------------------------------------------------------


def corpus_path(config: ExperimentConfig) -> Path:
    return config.processed_dir / hotpotqa.CORPUS_FILENAME


def load_sorted_corpus(config: ExperimentConfig) -> list[dict]:
    """Corpus documents in the canonical order that defines the matrix rows."""
    documents = hotpotqa.load_pilot_corpus(config.processed_dir)
    return sorted(documents, key=lambda document: document["doc_id"])


def expected_state(config: ExperimentConfig, max_seq_length: int | None = None) -> dict:
    """The manifest fields the current corpus and configuration imply."""
    state = {
        "corpus_sha256": sha256_file(corpus_path(config)),
        "model_name": config.retrieval.model_name,
        "model_revision": config.retrieval.model_revision,
        "text_rule": TEXT_RULE,
        "normalisation": NORMALISATION,
        "dtype": DTYPE,
        "index_format_version": INDEX_FORMAT_VERSION,
    }
    if max_seq_length is not None:
        state["max_seq_length"] = max_seq_length
    return state


def build_index(config: ExperimentConfig, rebuild: bool = False) -> dict:
    """Embed the corpus and store matrix, documents and manifest.

    An index that already matches the corpus and configuration is reused unless
    `rebuild` is set.
    """
    index_dir = config.index_dir
    index_dir.mkdir(parents=True, exist_ok=True)

    if not rebuild:
        try:
            existing = load_index(config)
        except IndexError_:
            pass
        else:
            manifest = dict(existing.manifest)
            manifest["reused_existing_index"] = True
            return manifest

    documents = load_sorted_corpus(config)
    if not documents:
        raise IndexError_(f"Corpus is empty: {corpus_path(config)}")

    model = load_model(config)
    texts = [build_text(document) for document in documents]
    truncation = count_truncated(model, texts)

    started = time.perf_counter()
    embeddings = model.encode(
        texts,
        batch_size=config.retrieval.batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32)
    build_seconds = time.perf_counter() - started

    if embeddings.shape[0] != len(documents):
        raise IndexError_(
            f"Embedding matrix has {embeddings.shape[0]} rows for {len(documents)} documents"
        )
    if not np.isfinite(embeddings).all():
        raise IndexError_("Embedding matrix contains non-finite values")

    np.save(index_dir / EMBEDDINGS_FILENAME, embeddings, allow_pickle=False)
    hotpotqa.write_jsonl(index_dir / DOCUMENTS_FILENAME, documents)

    norms = np.linalg.norm(embeddings, axis=1)
    manifest = {
        **expected_state(config, truncation["max_seq_length"]),
        "document_count": len(documents),
        "dimension": int(embeddings.shape[1]),
        "batch_size": config.retrieval.batch_size,
        "device": "cpu",
        "document_order_rule": DOCUMENT_ORDER_RULE,
        "ranking_rule": RANKING_RULE,
        "normalised": True,
        "norm_min": float(norms.min()),
        "norm_max": float(norms.max()),
        "truncation": truncation,
        "corpus_file": str(corpus_path(config)),
        "library_versions": library_versions(),
        "build_seconds": round(build_seconds, 3),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "file_sha256": {
            EMBEDDINGS_FILENAME: sha256_file(index_dir / EMBEDDINGS_FILENAME),
            DOCUMENTS_FILENAME: sha256_file(index_dir / DOCUMENTS_FILENAME),
        },
        "reused_existing_index": False,
    }
    # Identity of the index content, independent of timestamps.
    manifest["index_sha256"] = _index_identity(manifest)
    hotpotqa.write_json(index_dir / INDEX_MANIFEST_FILENAME, manifest)
    return manifest


def _index_identity(manifest: dict) -> str:
    """SHA-256 over the fields that define the index content."""
    import hashlib

    payload = {
        "file_sha256": manifest["file_sha256"],
        **{field: manifest.get(field) for field in INVALIDATING_FIELDS},
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- index loading and search -----------------------------------------------------


def load_index(config: ExperimentConfig, verify: bool = True) -> LoadedIndex:
    """Load the stored index, refusing a stale one instead of rebuilding silently."""
    index_dir = config.index_dir
    manifest_path = index_dir / INDEX_MANIFEST_FILENAME
    matrix_path = index_dir / EMBEDDINGS_FILENAME
    documents_path = index_dir / DOCUMENTS_FILENAME

    for path in (manifest_path, matrix_path, documents_path):
        if not path.is_file():
            raise MissingIndexError(
                f"No index at {path}. Run: python -m typed_rag --build-index"
            )

    manifest = hotpotqa.read_json(manifest_path)
    # No pickle anywhere: neither for documents nor for the matrix.
    embeddings = np.load(matrix_path, allow_pickle=False)
    documents = hotpotqa.read_jsonl(documents_path)

    if embeddings.shape[0] != len(documents):
        raise StaleIndexError(
            f"Index has {embeddings.shape[0]} rows but {len(documents)} documents"
        )

    if verify:
        current = expected_state(config)
        differences = [
            f"{field}: index={manifest.get(field)!r} current={current[field]!r}"
            for field in INVALIDATING_FIELDS
            if field in current and manifest.get(field) != current[field]
        ]
        if differences:
            raise StaleIndexError(
                "Stale index: the stored index no longer matches the current corpus "
                "or configuration:\n  "
                + "\n  ".join(differences)
                + "\nRun: python -m typed_rag --build-index --rebuild"
            )

    return LoadedIndex(embeddings=embeddings, documents=documents, manifest=manifest)


def embed_query(model: Any, query: str) -> np.ndarray:
    """Embed a query with the same model, revision and normalisation as the corpus.

    The query is the question text only: no gold answer, no supporting facts,
    no hidden hints.
    """
    vector = model.encode(
        [query],
        batch_size=1,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).astype(np.float32)
    return vector[0]


def rank(index: LoadedIndex, query_vector: np.ndarray, top_k: int) -> list[SearchHit]:
    """Exact cosine ranking over the whole corpus.

    Documents are stored in ascending doc_id order and the sort is stable, so
    equal scores come out ordered by doc_id.
    """
    if top_k < 1:
        raise SearchError(f"top_k must be a positive integer, got {top_k}")

    scores = index.embeddings @ query_vector
    if not np.isfinite(scores).all():
        raise SearchError("Similarity scores contain non-finite values")

    order = np.argsort(-scores, kind="stable")[: min(top_k, index.size)]
    return [
        SearchHit(
            rank=position + 1,
            doc_id=index.documents[row]["doc_id"],
            title=index.documents[row]["title"],
            score=float(scores[row]),
            text=index.documents[row]["text"],
        )
        for position, row in enumerate(order)
    ]


def search(index: LoadedIndex, model: Any, query: str, top_k: int) -> list[SearchHit]:
    """Search the shared corpus for `query`."""
    if not isinstance(query, str) or not query.strip():
        raise SearchError("Query must be a non-empty string")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise SearchError(f"top_k must be a positive integer, got {top_k!r}")
    return rank(index, embed_query(model, query), top_k)


def format_hits(hits: list[SearchHit], index: LoadedIndex, top_k: int, text_chars: int = 300) -> str:
    """Human-readable search output."""
    lines = [
        f"index         : {index.index_id[:16]} ({index.size} documents)",
        f"model         : {index.manifest['model_name']} @ {index.manifest['model_revision'][:12]}",
        f"top_k         : requested {top_k}, returned {len(hits)}",
        "",
    ]
    if top_k > index.size:
        lines.insert(3, f"note          : top_k exceeds corpus size; all {index.size} documents returned")
    for hit in hits:
        text = hit.text.replace("\n", " ")
        if len(text) > text_chars:
            text = text[:text_chars].rstrip() + " ..."
        lines.append(f"{hit.rank}. score={hit.score:.4f}  [{hit.doc_id[:12]}] {hit.title}")
        lines.append(f"   {text}")
    return "\n".join(lines)


def format_index_summary(config: ExperimentConfig) -> str:
    index = load_index(config)
    manifest = index.manifest
    truncation = manifest["truncation"]
    versions = manifest["library_versions"]
    return "\n".join(
        [
            f"index dir       : {config.index_dir}",
            f"index id        : {manifest['index_sha256']}",
            f"documents       : {manifest['document_count']}",
            f"matrix          : {index.embeddings.shape[0]} x {index.embeddings.shape[1]} "
            f"{manifest['dtype']} (normalised: {manifest['normalised']})",
            f"model           : {manifest['model_name']}",
            f"revision        : {manifest['model_revision']}",
            f"text rule       : {manifest['text_rule']}",
            f"order rule      : {manifest['document_order_rule']}",
            f"ranking rule    : {manifest['ranking_rule']}",
            f"max_seq_length  : {truncation['max_seq_length']} (batch size {manifest['batch_size']})",
            f"truncated docs  : {truncation['documents_truncated']} of {manifest['document_count']} "
            f"(max token length {truncation['max_token_length']})",
            f"corpus sha256   : {manifest['corpus_sha256']}",
            f"build seconds   : {manifest['build_seconds']}",
            f"built at (UTC)  : {manifest['built_at']}",
            f"libraries       : torch {versions['torch']}, sentence-transformers "
            f"{versions['sentence_transformers']}, transformers {versions['transformers']}, "
            f"numpy {versions['numpy']}",
        ]
    )
