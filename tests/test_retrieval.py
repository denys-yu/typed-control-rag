"""Unit tests for ranking, row correspondence and stale-index detection.

Everything here runs on synthetic vectors: no model is loaded, nothing is
downloaded. The real model is exercised separately by the integration check.

Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from typed_rag import hotpotqa, retrieval
from typed_rag.config import DatasetConfig, ExperimentConfig, LLMConfig, RetrievalConfig
from typed_rag.retrieval import (
    DOCUMENTS_FILENAME,
    EMBEDDINGS_FILENAME,
    INDEX_MANIFEST_FILENAME,
    LoadedIndex,
    MissingIndexError,
    SearchError,
    StaleIndexError,
)


def make_documents(count: int = 4) -> list[dict]:
    """Documents in the canonical order: ascending doc_id."""
    documents = [
        {
            "doc_id": f"{index:064x}",
            "title": f"Title {index}",
            "sentences": [f"Sentence {index}."],
            "text": f"Sentence {index}.",
        }
        for index in range(count)
    ]
    return sorted(documents, key=lambda document: document["doc_id"])


def normalise(matrix: np.ndarray) -> np.ndarray:
    return (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).astype(np.float32)


class FakeModel:
    """Returns a fixed normalised query vector; never touches the network."""

    def __init__(self, vector: np.ndarray):
        self.vector = vector
        self.calls: list[str] = []

    def encode(self, texts, **kwargs):
        self.calls.extend(texts)
        return np.tile(self.vector, (len(texts), 1)).astype(np.float32)


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.documents = make_documents(4)
        # Row i deliberately gets a different similarity to the query below.
        self.embeddings = normalise(
            np.array(
                [
                    [1.0, 0.0],
                    [0.0, 1.0],
                    [0.9, 0.1],
                    [0.5, 0.5],
                ],
                dtype=np.float32,
            )
        )
        self.index = LoadedIndex(
            embeddings=self.embeddings,
            documents=self.documents,
            manifest={"index_sha256": "test", "model_name": "fake", "model_revision": "0" * 40},
        )
        self.query = np.array([1.0, 0.0], dtype=np.float32)

    def test_ranks_by_descending_score(self):
        hits = retrieval.rank(self.index, self.query, top_k=4)
        scores = [hit.score for hit in hits]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([hit.rank for hit in hits], [1, 2, 3, 4])
        self.assertEqual(hits[0].doc_id, self.documents[0]["doc_id"])

    def test_rows_match_documents(self):
        hits = retrieval.rank(self.index, self.query, top_k=4)
        for hit in hits:
            row = next(
                position
                for position, document in enumerate(self.documents)
                if document["doc_id"] == hit.doc_id
            )
            self.assertEqual(hit.title, self.documents[row]["title"])
            self.assertEqual(hit.text, self.documents[row]["text"])
            self.assertAlmostEqual(hit.score, float(self.embeddings[row] @ self.query), places=6)

    def test_equal_scores_are_ordered_by_doc_id(self):
        documents = make_documents(3)
        identical = normalise(np.ones((3, 2), dtype=np.float32))
        index = LoadedIndex(embeddings=identical, documents=documents, manifest={})
        hits = retrieval.rank(index, np.array([1.0, 1.0], dtype=np.float32) / np.sqrt(2), top_k=3)
        self.assertEqual(
            [hit.doc_id for hit in hits], sorted(document["doc_id"] for document in documents)
        )

    def test_top_k_larger_than_corpus_returns_all(self):
        hits = retrieval.rank(self.index, self.query, top_k=99)
        self.assertEqual(len(hits), len(self.documents))

    def test_scores_are_finite(self):
        hits = retrieval.rank(self.index, self.query, top_k=4)
        self.assertTrue(all(np.isfinite(hit.score) for hit in hits))

    def test_rounding_happens_only_for_display(self):
        hits = retrieval.rank(self.index, self.query, top_k=2)
        payload = hits[0].as_dict(score_digits=2)
        self.assertEqual(payload["score"], round(hits[0].score, 2))
        self.assertNotEqual(hits[0].score, 0.0)

    def test_invalid_top_k_is_rejected(self):
        model = FakeModel(self.query)
        for bad in (0, -1, True, 2.5, "5"):
            with self.assertRaises(SearchError):
                retrieval.search(self.index, model, "question", bad)

    def test_empty_query_is_rejected(self):
        model = FakeModel(self.query)
        for bad in ("", "   ", None):
            with self.assertRaises(SearchError):
                retrieval.search(self.index, model, bad, 5)

    def test_search_sends_only_the_query_to_the_model(self):
        model = FakeModel(self.query)
        retrieval.search(self.index, model, "Who wrote it?", 2)
        self.assertEqual(model.calls, ["Who wrote it?"])


class TextRuleTests(unittest.TestCase):
    def test_embedding_text_is_title_newline_text(self):
        document = {"title": "Alpha", "text": "First.\nSecond."}
        self.assertEqual(retrieval.build_text(document), "Alpha\nFirst.\nSecond.")


class IndexFileTests(unittest.TestCase):
    """Stale-index detection, driven by files in a temporary project tree."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        paths = {
            "data_raw": root / "data/raw",
            "data_processed": root / "data/processed",
            "artifacts": root / "artifacts",
            "results": root / "results",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

        self.config = ExperimentConfig(
            experiment_name="test",
            seed=42,
            pilot_size=1,
            dataset=DatasetConfig(
                name="hotpotqa",
                split="dev",
                setting="distractor",
                version="v1",
                filename="raw.json",
                processed_dirname="hotpotqa",
                url="https://example.invalid/raw.json",
                mirror_urls=(),
            ),
            retrieval=RetrievalConfig(
                model_name="fake-model",
                model_revision="a" * 40,
                index_dirname="retrieval",
                model_cache_dirname="models",
                batch_size=8,
                top_k=5,
            ),
            llm=LLMConfig(
                provider="openai",
                api="responses",
                model="test-model",
                temperature=0.0,
                max_output_tokens=800,
                timeout_seconds=60.0,
                max_retries=0,
                store=False,
                prompts_dirname="prompts",
                runs_dirname="rag_runs",
                dry_runs_dirname="rag_dry_runs",
                api_key_env="OPENAI_API_KEY",
                env_filename=".env",
            ),
            project_root=root,
            config_path=root / "config/experiment.json",
            paths=paths,
        )
        self.documents = make_documents(3)
        self.config.processed_dir.mkdir(parents=True, exist_ok=True)
        hotpotqa.write_jsonl(
            self.config.processed_dir / hotpotqa.CORPUS_FILENAME, self.documents
        )

    def tearDown(self):
        self.temporary.cleanup()

    def write_index(self, **overrides) -> np.ndarray:
        index_dir = self.config.index_dir
        index_dir.mkdir(parents=True, exist_ok=True)
        embeddings = normalise(np.eye(3, 2, dtype=np.float32) + 0.1)
        np.save(index_dir / EMBEDDINGS_FILENAME, embeddings, allow_pickle=False)
        hotpotqa.write_jsonl(index_dir / DOCUMENTS_FILENAME, self.documents)
        manifest = {
            **retrieval.expected_state(self.config, max_seq_length=256),
            "document_count": len(self.documents),
            "dimension": 2,
            "index_sha256": "x" * 64,
            **overrides,
        }
        hotpotqa.write_json(index_dir / INDEX_MANIFEST_FILENAME, manifest)
        return embeddings

    def test_missing_index_is_reported(self):
        with self.assertRaises(MissingIndexError):
            retrieval.load_index(self.config)

    def test_matching_index_loads(self):
        embeddings = self.write_index()
        index = retrieval.load_index(self.config)
        self.assertEqual(index.size, 3)
        np.testing.assert_array_equal(index.embeddings, embeddings)

    def test_changed_corpus_is_detected(self):
        self.write_index()
        extended = [*self.documents, make_documents(4)[3]]
        hotpotqa.write_jsonl(self.config.processed_dir / hotpotqa.CORPUS_FILENAME, extended)
        with self.assertRaises(StaleIndexError):
            retrieval.load_index(self.config)

    def test_changed_model_revision_is_detected(self):
        self.write_index(model_revision="b" * 40)
        with self.assertRaises(StaleIndexError):
            retrieval.load_index(self.config)

    def test_changed_text_rule_is_detected(self):
        self.write_index(text_rule="text only")
        with self.assertRaises(StaleIndexError):
            retrieval.load_index(self.config)

    def test_row_count_mismatch_is_detected(self):
        self.write_index()
        hotpotqa.write_jsonl(
            self.config.index_dir / DOCUMENTS_FILENAME, self.documents[:2]
        )
        with self.assertRaises(StaleIndexError):
            retrieval.load_index(self.config)

    def test_matrix_loads_without_pickle(self):
        self.write_index()
        matrix = np.load(self.config.index_dir / EMBEDDINGS_FILENAME, allow_pickle=False)
        self.assertEqual(matrix.dtype, np.float32)

    def test_search_works_without_annotations_file(self):
        self.write_index()
        annotations = self.config.processed_dir / hotpotqa.ANNOTATIONS_FILENAME
        self.assertFalse(annotations.exists())
        index = retrieval.load_index(self.config)
        model = FakeModel(np.array([1.0, 0.0], dtype=np.float32))
        hits = retrieval.search(index, model, "anything", 2)
        self.assertEqual(len(hits), 2)


class EvaluationScoringTests(unittest.TestCase):
    def test_metrics_on_a_known_ranking(self):
        from typed_rag.evaluate import score_retrieval

        rows = [
            {
                "question_id": "q1",
                "results": [{"rank": i + 1, "doc_id": f"d{i}"} for i in range(10)],
            },
            {
                "question_id": "q2",
                "results": [{"rank": i + 1, "doc_id": f"e{i}"} for i in range(10)],
            },
        ]
        annotations = [
            {"question_id": "q1", "supporting_doc_ids": ["d0", "d1"]},  # both in top-5
            {"question_id": "q2", "supporting_doc_ids": ["e0", "e7"]},  # one in top-5
        ]
        scored = score_retrieval(rows, annotations)
        metrics = scored["metrics"]
        self.assertEqual(metrics["recall_at_5"], 0.75)
        self.assertEqual(metrics["recall_at_10"], 1.0)
        self.assertEqual(metrics["all_support_at_5"], 0.5)
        self.assertEqual(metrics["all_support_at_10"], 1.0)
        self.assertEqual(metrics["supporting_documents_found_at_5"], {"0": 0, "1": 1, "2": 1})


if __name__ == "__main__":
    unittest.main()
