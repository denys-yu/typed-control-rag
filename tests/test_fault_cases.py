"""Unit tests for stage 6: fault-case construction, review gating, controller injection.

Synthetic corpus, saved ranking and fake transport; no model, no network.
Passing structural tests does not show that any expected state is
semantically right - that is what reviews.jsonl is for.

Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from typed_rag import controller, fault_cases, hotpotqa, llm, nodes
from typed_rag.config import ControllerConfig, DatasetConfig, ExperimentConfig, LLMConfig, RetrievalConfig
from typed_rag.download import sha256_file
from typed_rag.retrieval import INDEX_MANIFEST_FILENAME, LoadedIndex

PROJECT_PROMPTS = Path(__file__).resolve().parents[1] / "prompts"

FORBIDDEN_IN_PIPELINE_INPUT = (
    "condition", "expected_state", "answer", "supporting", "removed", "added", "synthetic",
    "gold", "CLEAN", "PARTIAL", "EMPTY", "INCONSISTENT", "review",
)


def doc(title: str, sentences: list[str]) -> dict:
    return {
        "doc_id": hotpotqa.document_id(title, sentences),
        "title": title,
        "sentences": sentences,
        "text": hotpotqa.paragraph_text(sentences),
    }


class FakeTransport:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        if not self.outcomes:
            raise AssertionError("unexpected API call")
        return self.outcomes.pop(0)


def completed(payload) -> llm.TransportResult:
    return llm.TransportResult(
        response_id="resp", request_id="req", model="test-model", status="completed",
        output_text=json.dumps(payload),
        usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2, "input_tokens_details": {"cached_tokens": 0}},
        raw_response={},
    )


class FaultProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="typed_rag_stage6_")
        root = Path(self.tmp)
        paths = {k: root / v for k, v in {"data_raw": "data/raw", "data_processed": "data/processed", "artifacts": "artifacts", "results": "results"}.items()}
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(PROJECT_PROMPTS, root / "prompts")
        (root / "config").mkdir()
        self.config = ExperimentConfig(
            experiment_name="test", seed=42, pilot_size=2,
            dataset=DatasetConfig(name="hotpotqa", split="dev", setting="distractor", version="v1", filename="raw.json", processed_dirname="hotpotqa", url="https://example.invalid/raw.json", mirror_urls=()),
            retrieval=RetrievalConfig(model_name="fake-model", model_revision="a" * 40, index_dirname="retrieval", model_cache_dirname="models", batch_size=8, top_k=5),
            llm=LLMConfig(provider="openai", api="responses", model="test-model", temperature=0.0, max_output_tokens=800, timeout_seconds=60.0, max_retries=0, store=False, prompts_dirname="prompts", runs_dirname="rag_runs", dry_runs_dirname="rag_dry_runs", api_key_env="OPENAI_API_KEY", env_filename=".env"),
            project_root=root, config_path=root / "config/experiment.json", paths=paths,
            controller=ControllerConfig(max_search_retries=1, policy_version="test-v1", runs_dirname="controlled_runs", dry_runs_dirname="controlled_dry_runs"),
        )
        # Corpus: 2 gold docs (G1, G2) for question 1, plus distractors D1..D8.
        self.g1 = doc("Alpha Corp", ["Alpha Corp was founded in 1990.", "It is based in Oslo."])
        self.g2 = doc("Beta Ltd", ["Beta Ltd was founded in 1985.", "It is based in Bergen."])
        self.distractors = [doc(f"Distractor {i}", [f"Distractor sentence {i}."]) for i in range(1, 9)]
        corpus = sorted([self.g1, self.g2, *self.distractors], key=lambda d: d["doc_id"])
        pdir = self.config.processed_dir
        pdir.mkdir(parents=True)
        hotpotqa.write_jsonl(pdir / hotpotqa.CORPUS_FILENAME, corpus)
        self.q1 = {"question": "Which company was founded first, Alpha Corp or Beta Ltd?", "question_id": "q1" * 12}
        self.q2 = {"question": "Where is Gamma based?", "question_id": "q2" * 12}
        hotpotqa.write_jsonl(pdir / hotpotqa.QUESTIONS_FILENAME, [self.q1, self.q2])
        hotpotqa.write_jsonl(pdir / hotpotqa.ANNOTATIONS_FILENAME, [
            {"question_id": self.q1["question_id"], "answer": "Beta Ltd", "supporting_doc_ids": [self.g1["doc_id"], self.g2["doc_id"]], "supporting_facts": [["Alpha Corp", 0], ["Beta Ltd", 0]], "type": "comparison", "level": "hard"},
            {"question_id": self.q2["question_id"], "answer": "Oslo", "supporting_doc_ids": [self.g1["doc_id"], self.distractors[7]["doc_id"]], "supporting_facts": [], "type": "bridge", "level": "hard"},
        ])
        # Index manifest (no matrix needed for building) and a saved ranking.
        self.config.index_dir.mkdir(parents=True)
        hotpotqa.write_json(self.config.index_dir / INDEX_MANIFEST_FILENAME, {"index_sha256": "f" * 64, "corpus_sha256": sha256_file(pdir / hotpotqa.CORPUS_FILENAME), "model_name": "fake-model", "model_revision": "a" * 40})
        d = self.distractors
        self.ranking_q1 = [self.g1, d[0], self.g2, d[1], d[2], d[3], d[4], d[5], d[6], d[7]]  # gold at ranks 1 and 3
        ranking_q2 = [d[0], d[1], d[2], d[3], d[4], self.g1, d[7], d[5], d[6], self.g2]  # gold outside top-5
        rows = []
        for q, ranking in ((self.q1, self.ranking_q1), (self.q2, ranking_q2)):
            rows.append({"question_id": q["question_id"], "question": q["question"], "index_id": "f" * 64, "top_k": 10,
                         "search_seconds": 0.0, "results": [{"rank": i + 1, "doc_id": x["doc_id"], "score": 1.0 - i * 0.05} for i, x in enumerate(ranking)]})
        hotpotqa.write_jsonl(paths["results"] / fault_cases.SAVED_RETRIEVAL_FILENAME, rows)
        self.write_edits({
            self.q1["question_id"]: {
                "target_title": "Beta Ltd", "sentence_index": 0,
                "original_sentence": "Beta Ltd was founded in 1985.", "edited_sentence": "Beta Ltd was founded in 1995.",
                "claim_original": "Beta founded 1985", "claim_edited": "Beta founded 1995", "property": "founding year of Beta Ltd", "relevance": "decides which was founded first",
            }
        })
        # Retrieval for the controller: the real LoadedIndex with unit vectors; the fake
        # model returns the vector of a chosen document so a retry retrieves it first.
        self.corpus = corpus
        vectors = np.eye(len(corpus), dtype=np.float32)
        self.index = LoadedIndex(embeddings=vectors, documents=corpus, manifest={"index_sha256": "f" * 64, "model_name": "fake-model", "model_revision": "a" * 40})
        g2_row = [x["doc_id"] for x in corpus].index(self.g2["doc_id"])
        self.model = type("M", (), {"encode": lambda _self, texts, **kw: np.tile(vectors[g2_row], (len(texts), 1)), "queries": []})()
        self._env = os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self):
        if self._env is not None:
            os.environ["OPENAI_API_KEY"] = self._env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_edits(self, edits: dict) -> None:
        fault_cases.edits_path(self.config).write_text(json.dumps({"edits": edits}), encoding="utf-8")

    def prepare(self) -> dict:
        return fault_cases.write_cases(self.config, fault_cases.build_cases(self.config))

    def annotation(self, condition: str, qid: str | None = None) -> dict:
        qid = qid or self.q1["question_id"]
        return next(a for a in fault_cases.load_fault_annotations(self.config) if a["question_id"] == qid and a["condition"] == condition)

    def source_hashes(self) -> dict:
        pdir = self.config.processed_dir
        return {name: sha256_file(pdir / name) for name in (hotpotqa.CORPUS_FILENAME, hotpotqa.QUESTIONS_FILENAME, hotpotqa.ANNOTATIONS_FILENAME)} | {"manifest": sha256_file(self.config.index_dir / INDEX_MANIFEST_FILENAME)}


class ConstructionTests(FaultProject):
    def test_eligibility_and_counts(self):
        manifest = self.prepare()
        self.assertEqual(manifest["counts"]["eligible_questions"], 1)
        self.assertEqual(manifest["counts"]["ineligible_questions"], 1)
        self.assertEqual(manifest["counts"]["cases_built"], {c: 1 for c in fault_cases.CONDITIONS})
        ineligible = next(e for e in manifest["eligibility"] if not e["eligible"])
        self.assertEqual(ineligible["question_id"], self.q2["question_id"])
        self.assertIn("0 of 2", ineligible["reason"])
        self.assertEqual(len(fault_cases.load_fault_contexts(self.config)), 4)
        self.assertEqual(len(hotpotqa.load_pilot_questions(self.config.processed_dir)), 2)  # pilot untouched

    def test_sources_unchanged_and_reproducible(self):
        before = self.source_hashes()
        self.prepare()
        first = {name: sha256_file(fault_cases.fault_cases_dir(self.config) / name) for name in (fault_cases.CONTEXTS_FILENAME, fault_cases.ANNOTATIONS_FILENAME)}
        self.prepare()
        second = {name: sha256_file(fault_cases.fault_cases_dir(self.config) / name) for name in first}
        self.assertEqual(first, second)
        self.assertEqual(before, self.source_hashes())
        ids = {c["case_id"] for c in fault_cases.load_fault_contexts(self.config)}
        self.assertEqual(ids, {fault_cases.case_id_for(self.q1["question_id"], c, 42) for c in fault_cases.CONDITIONS})

    def test_each_condition_structure(self):
        self.prepare()
        contexts = {c["case_id"]: c for c in fault_cases.load_fault_contexts(self.config)}
        gold = {self.g1["doc_id"], self.g2["doc_id"]}
        initial = [x["doc_id"] for x in self.ranking_q1[:5]]
        for condition in fault_cases.CONDITIONS:
            with self.subTest(condition=condition):
                a = self.annotation(condition)
                ids = [d["doc_id"] for d in contexts[a["case_id"]]["documents"]]
                self.assertEqual(len(ids), 5)
                self.assertEqual(len(set(ids)), 5)
                self.assertTrue(a["technical_checks"]["all_passed"])
                for i, doc_id in enumerate(ids):
                    if doc_id in initial:
                        self.assertEqual(initial[i], doc_id)  # unchanged positions kept
                self.assertTrue(all(r not in ids for r in a["removed_doc_ids"]))
                self.assertTrue(all(x in ids for x in a["added_doc_ids"]))
        clean = self.annotation("CLEAN")
        self.assertEqual(clean["final_doc_ids"], initial)
        self.assertEqual(clean["context_sha256_before"], clean["context_sha256_after"])
        partial = self.annotation("PARTIAL")
        self.assertEqual(len(partial["removed_doc_ids"]), 1)
        self.assertIn(partial["removed_doc_ids"][0], gold)
        self.assertEqual(len(gold & set(partial["final_doc_ids"])), 1)
        self.assertEqual(partial["added_doc_ids"], [self.distractors[3]["doc_id"]])  # rank 6
        empty = self.annotation("EMPTY")
        self.assertEqual(set(empty["removed_doc_ids"]), gold)
        self.assertEqual(gold & set(empty["final_doc_ids"]), set())
        self.assertEqual(empty["added_doc_ids"], [self.distractors[3]["doc_id"], self.distractors[4]["doc_id"]])
        inc = self.annotation("INCONSISTENT")
        self.assertTrue(gold <= set(inc["final_doc_ids"]))
        self.assertEqual(inc["removed_doc_ids"], [self.distractors[2]["doc_id"]])  # lowest-ranked non-gold (rank 5)
        synthetic = next(d for d in contexts[inc["case_id"]]["documents"] if d["doc_id"] == inc["added_doc_ids"][0])
        self.assertEqual(synthetic["title"], "Beta Ltd")
        self.assertIn("1995", synthetic["text"])
        self.assertNotEqual(synthetic["text"], self.g2["text"])
        self.assertNotIn(synthetic["doc_id"], {d["doc_id"] for d in self.corpus})
        self.assertEqual(synthetic["doc_id"], hotpotqa.document_id("Beta Ltd", ["Beta Ltd was founded in 1995.", "It is based in Bergen."]))
        self.assertEqual(inc["synthetic_provenance"]["incompatible_claims"], ["Beta founded 1985", "Beta founded 1995"])

    def test_partial_choice_is_seeded(self):
        self.prepare()
        chosen = self.annotation("PARTIAL")["removed_doc_ids"][0]
        import random
        expected = random.Random(f"42:{self.q1['question_id']}").choice(sorted([self.g1["doc_id"], self.g2["doc_id"]]))
        self.assertEqual(chosen, expected)

    def test_construction_failed_is_recorded_not_faked(self):
        self.write_edits({self.q1["question_id"]: {"target_title": "Beta Ltd", "sentence_index": 0, "original_sentence": "WRONG", "edited_sentence": "x", "claim_original": "", "claim_edited": "", "property": "", "relevance": ""}})
        manifest = self.prepare()
        self.assertEqual(manifest["counts"]["construction_failed"]["INCONSISTENT"], 1)
        inc = self.annotation("INCONSISTENT")
        self.assertEqual(inc["build_status"], "construction_failed")
        self.assertIn("original_sentence", inc["failure_reason"])
        self.assertEqual(len(fault_cases.load_fault_contexts(self.config)), 3)
        self.assertEqual(len(fault_cases.load_fault_reviews(self.config)), 3)

    def test_pipeline_input_carries_no_research_markers(self):
        self.prepare()
        text = (fault_cases.fault_cases_dir(self.config) / fault_cases.CONTEXTS_FILENAME).read_text(encoding="utf-8")
        for row in text.splitlines():
            record = json.loads(row)
            self.assertEqual(set(record), {"case_id", "question_id", "question", "documents"})
            for d in record["documents"]:
                self.assertEqual(set(d), {"doc_id", "title", "text"})
        keys = json.dumps([list(json.loads(r)) for r in text.splitlines()])
        for marker in FORBIDDEN_IN_PIPELINE_INPUT:
            self.assertNotIn(marker, keys)

    def test_saved_retrieval_mismatch_is_refused(self):
        hotpotqa.write_json(self.config.index_dir / INDEX_MANIFEST_FILENAME, {"index_sha256": "e" * 64, "corpus_sha256": sha256_file(self.config.processed_dir / hotpotqa.CORPUS_FILENAME), "model_name": "fake-model", "model_revision": "a" * 40})
        with self.assertRaises(fault_cases.FaultCaseError):
            fault_cases.build_cases(self.config)


class ReviewTests(FaultProject):
    def test_reviews_start_pending_and_are_preserved(self):
        self.prepare()
        reviews = fault_cases.load_fault_reviews(self.config)
        self.assertEqual({r["review_status"] for r in reviews}, {"pending"})
        self.assertTrue(all(r["observed_state"] is None and r["reviewer"] is None for r in reviews))
        reviews[0].update({"review_status": "approved", "observed_state": "OK", "reviewer": "r1", "note": "fine"})
        hotpotqa.write_jsonl(fault_cases.fault_cases_dir(self.config) / fault_cases.REVIEWS_FILENAME, reviews)
        manifest = self.prepare()
        self.assertEqual(manifest["counts"]["reviews_preserved"], 4)
        kept = next(r for r in fault_cases.load_fault_reviews(self.config) if r["case_id"] == reviews[0]["case_id"])
        self.assertEqual(kept["review_status"], "approved")

    def test_validate_reviews(self):
        self.prepare()
        report = fault_cases.validate_reviews(self.config)
        self.assertTrue(report["valid"])
        self.assertEqual(report["review_counts"]["pending"], 4)
        self.assertEqual(report["ready_full_quadruple_count"], 0)
        reviews = fault_cases.load_fault_reviews(self.config)
        expected = {a["case_id"]: a["expected_state"] for a in fault_cases.load_fault_annotations(self.config)}
        for r in reviews:
            r.update({"review_status": "approved", "observed_state": expected[r["case_id"]], "reviewer": "r1"})
        hotpotqa.write_jsonl(fault_cases.fault_cases_dir(self.config) / fault_cases.REVIEWS_FILENAME, reviews)
        report = fault_cases.validate_reviews(self.config)
        self.assertTrue(report["valid"])
        self.assertEqual(report["ready_full_quadruples"], [self.q1["question_id"]])
        # one variant approved with another state -> not ready, but recorded
        reviews[0]["observed_state"] = "PARTIAL" if expected[reviews[0]["case_id"]] != "PARTIAL" else "OK"
        hotpotqa.write_jsonl(fault_cases.fault_cases_dir(self.config) / fault_cases.REVIEWS_FILENAME, reviews)
        report = fault_cases.validate_reviews(self.config)
        self.assertEqual(report["ready_full_quadruple_count"], 0)
        self.assertEqual(len(report["approved_with_other_state"]), 1)
        # malformed entries are reported
        reviews[1]["review_status"] = "approved"; reviews[1]["observed_state"] = None
        reviews[2]["observed_state"] = "MAYBE"
        hotpotqa.write_jsonl(fault_cases.fault_cases_dir(self.config) / fault_cases.REVIEWS_FILENAME, reviews)
        report = fault_cases.validate_reviews(self.config)
        self.assertFalse(report["valid"])
        self.assertEqual(len(report["problems"]), 2)


class ControllerIntegrationTests(FaultProject):
    def grade(self, state, action, ids=None):
        return completed({"state": state, "proposed_action": action, "evidence_doc_ids": ids or [], "reason": "r"})

    def test_real_run_refused_unless_approved(self):
        self.prepare()
        case_id = self.annotation("PARTIAL")["case_id"]
        for status in ("pending", "rejected"):
            reviews = fault_cases.load_fault_reviews(self.config)
            for r in reviews:
                if r["case_id"] == case_id:
                    r["review_status"] = status
            hotpotqa.write_jsonl(fault_cases.fault_cases_dir(self.config) / fault_cases.REVIEWS_FILENAME, reviews)
            with self.subTest(status=status):
                transport = FakeTransport([])
                with self.assertRaises(fault_cases.FaultCaseError):
                    fault_cases.run_fault_case(self.config, case_id, "D", transport=transport, index=self.index, model=self.model)
                self.assertEqual(transport.requests, [])

    def test_dry_run_allowed_for_pending_and_marked(self):
        self.prepare()
        case_id = self.annotation("EMPTY")["case_id"]
        run = fault_cases.run_fault_case(self.config, case_id, "D", dry_run=True, index=self.index, model=self.model)
        self.assertEqual(run["status"], "dry_run")
        self.assertEqual(run["mode"], "stage6_fault_check")
        self.assertEqual(run["fault_case_review_status"], "pending")
        self.assertIn("not approved", run["fault_case_note"])
        self.assertEqual(run["searches"], 0)
        saved = json.loads((Path(run["run_dir"]) / controller.REQUESTS_FILENAME).read_text(encoding="utf-8"))
        # The instruction prompt legitimately names the states; the user input must not
        # carry any research marker.
        request_text = saved["first_grader_request"]["input"][0]["content"][0]["text"]
        for marker in ("case_id", "condition", "expected_state", "synthetic", "EMPTY", "removed", "gold"):
            self.assertNotIn(marker, request_text)
        self.assertIn(self.q1["question"], request_text)

    def test_same_initial_context_for_all_branches(self):
        self.prepare()
        case_id = self.annotation("INCONSISTENT")["case_id"]
        hashes = set()
        inputs = set()
        for branch in "ABCD":
            run = fault_cases.run_fault_case(self.config, case_id, branch, dry_run=True, index=self.index, model=self.model)
            ctx = json.loads((Path(run["run_dir"]) / controller.CONTEXT_FILENAME).read_text(encoding="utf-8"))
            hashes.add(ctx["contexts"][0]["context_sha256"])
            self.assertEqual(ctx["contexts"][0]["query_kind"], "injected_initial")
            saved = json.loads((Path(run["run_dir"]) / controller.REQUESTS_FILENAME).read_text(encoding="utf-8"))
            inputs.add(saved["first_grader_request"]["input"][0]["content"][0]["text"])
        self.assertEqual(len(hashes), 1)
        self.assertEqual(len(inputs), 1)
        self.assertEqual(hashes.pop(), self.annotation("INCONSISTENT")["context_sha256_after"])

    def test_injected_partial_then_retry_uses_normal_retrieval(self):
        self.prepare()
        annotation = self.annotation("PARTIAL")
        case_id = annotation["case_id"]
        reviews = fault_cases.load_fault_reviews(self.config)
        for r in reviews:
            if r["case_id"] == case_id:
                r.update({"review_status": "approved", "observed_state": "PARTIAL", "reviewer": "r1"})
        hotpotqa.write_jsonl(fault_cases.fault_cases_dir(self.config) / fault_cases.REVIEWS_FILENAME, reviews)
        g1, g2 = self.g1["doc_id"], self.g2["doc_id"]
        transport = FakeTransport([
            self.grade("PARTIAL", "retry"),
            completed({"rewritten_query": "when was Beta Ltd founded", "reason": "r"}),
            self.grade("OK", "answer", [g2]),
            completed({"decision": "answer", "answer": "Beta Ltd", "evidence_doc_ids": [g2], "reason": "r"}),
        ])
        run = fault_cases.run_fault_case(self.config, case_id, "D", transport=transport, index=self.index, model=self.model)
        self.assertEqual(run["status"], controller.RUN_COMPLETED)
        self.assertEqual(run["final_outcome"], controller.OUTCOME_ANSWERED)
        self.assertEqual(run["executed_actions"], ["retry", "answer"])
        self.assertEqual(run["searches"], 1)  # injected initial + one real retry search
        self.assertEqual(run["fault_case_review_status"], "approved")
        ctx = json.loads((Path(run["run_dir"]) / controller.CONTEXT_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(len(ctx["contexts"]), 2)
        self.assertEqual(ctx["contexts"][0]["query_kind"], "injected_initial")
        self.assertEqual(ctx["contexts"][0]["doc_ids"], annotation["final_doc_ids"])
        self.assertEqual(ctx["contexts"][1]["query_kind"], "rewritten")
        self.assertEqual(ctx["contexts"][1]["doc_ids"][0], g2)  # normal search over the unchanged corpus
        self.assertNotEqual(ctx["contexts"][1]["doc_ids"], annotation["final_doc_ids"])
        self.assertTrue(all(d in {x["doc_id"] for x in self.corpus} for d in ctx["contexts"][1]["doc_ids"]))
        # first grader input = injected docs; second = retrieved docs; nothing merged
        first = transport.requests[0]["input"][0]["content"][0]["text"]
        second = transport.requests[2]["input"][0]["content"][0]["text"]
        self.assertIn(annotation["added_doc_ids"][0], first)
        self.assertNotIn(annotation["removed_doc_ids"][0], first)
        self.assertIn(g2, second)
        for text in (first, second):
            for marker in ("case_id", "condition", "expected_state", "synthetic", "removed", "gold"):
                self.assertNotIn(marker, text)

    def test_wrong_question_context_is_rejected(self):
        self.prepare()
        context = fault_cases.find_context(self.config, self.annotation("CLEAN")["case_id"])
        context = {**context, "question_id": self.q2["question_id"]}
        with self.assertRaises(ValueError):
            controller.run_controlled(self.config, 0, "D", dry_run=True, index=self.index, model=self.model, initial_context=context)


if __name__ == "__main__":
    unittest.main()
