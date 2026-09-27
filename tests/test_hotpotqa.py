"""Small unittest suite for the risky parts of stage 2.

Covered risks: gold/input separation, supporting-fact mapping, deduplication
(including same title with different text), duplicate question ids and the
determinism of the pilot selection.

Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import copy
import json
import unittest

from typed_rag import hotpotqa

PARAGRAPH_A = ["Alpha is a town.", "It lies near Beta."]
PARAGRAPH_B = ["Beta is a river.", "It flows east."]
PARAGRAPH_A_VARIANT = ["Alpha is a band.", "It formed in 1990."]


def make_record(question_id: str, context=None, supporting=None) -> dict:
    return {
        "_id": question_id,
        "question": f"Question {question_id}?",
        "answer": "Alpha",
        "type": "bridge",
        "level": "hard",
        "context": context
        if context is not None
        else [["Alpha", list(PARAGRAPH_A)], ["Beta", list(PARAGRAPH_B)]],
        "supporting_facts": supporting if supporting is not None else [["Alpha", 0], ["Beta", 1]],
    }


class DocumentIdTests(unittest.TestCase):
    def test_same_paragraph_gives_same_id(self):
        self.assertEqual(
            hotpotqa.document_id("Alpha", list(PARAGRAPH_A)),
            hotpotqa.document_id("Alpha", list(PARAGRAPH_A)),
        )

    def test_same_title_different_text_gives_different_ids(self):
        self.assertNotEqual(
            hotpotqa.document_id("Alpha", PARAGRAPH_A),
            hotpotqa.document_id("Alpha", PARAGRAPH_A_VARIANT),
        )

    def test_id_is_sha256_hex(self):
        doc_id = hotpotqa.document_id("Alpha", PARAGRAPH_A)
        self.assertEqual(len(doc_id), 64)
        int(doc_id, 16)


class CorpusTests(unittest.TestCase):
    def test_identical_paragraphs_are_deduplicated(self):
        records = [make_record("q1"), make_record("q2")]
        corpus, before = hotpotqa.build_corpus(records)
        self.assertEqual(before, 4)
        self.assertEqual(len(corpus), 2)

    def test_same_title_different_text_stays_separate(self):
        records = [
            make_record("q1"),
            make_record(
                "q2",
                context=[["Alpha", list(PARAGRAPH_A_VARIANT)], ["Beta", list(PARAGRAPH_B)]],
                supporting=[["Alpha", 0], ["Beta", 0]],
            ),
        ]
        corpus, before = hotpotqa.build_corpus(records)
        self.assertEqual(before, 4)
        self.assertEqual(len(corpus), 3)
        alpha_docs = [doc for doc in corpus if doc["title"] == "Alpha"]
        self.assertEqual(len(alpha_docs), 2)

    def test_documents_carry_no_gold_fields(self):
        corpus, _ = hotpotqa.build_corpus([make_record("q1")])
        for document in corpus:
            self.assertEqual(sorted(document), ["doc_id", "sentences", "text", "title"])
            for field in hotpotqa.FORBIDDEN_DOCUMENT_FIELDS:
                self.assertNotIn(field, document)

    def test_sentence_order_and_text_are_preserved(self):
        corpus, _ = hotpotqa.build_corpus([make_record("q1")])
        alpha = next(doc for doc in corpus if doc["title"] == "Alpha")
        self.assertEqual(alpha["sentences"], PARAGRAPH_A)
        self.assertEqual(alpha["text"], "\n".join(PARAGRAPH_A))


class QuestionFileTests(unittest.TestCase):
    def test_questions_contain_only_id_and_text(self):
        rows = hotpotqa.build_questions([make_record("q1")])
        self.assertEqual(sorted(rows[0]), ["question", "question_id"])


class AnnotationTests(unittest.TestCase):
    def test_supporting_facts_map_to_documents_and_sentences(self):
        record = make_record("q1")
        annotation = hotpotqa.build_annotations([record])[0]
        self.assertEqual(annotation["question_id"], "q1")
        facts = annotation["supporting_sentences"]
        self.assertEqual(len(facts), 2)
        self.assertEqual(facts[0]["doc_id"], hotpotqa.document_id("Alpha", PARAGRAPH_A))
        self.assertEqual(facts[0]["sentence"], PARAGRAPH_A[0])
        self.assertEqual(facts[1]["sentence"], PARAGRAPH_B[1])
        self.assertEqual(len(annotation["context_doc_ids"]), 2)

    def test_mapping_picks_the_right_paragraph_when_titles_repeat_across_questions(self):
        records = [
            make_record("q1"),
            make_record(
                "q2",
                context=[["Alpha", list(PARAGRAPH_A_VARIANT)], ["Beta", list(PARAGRAPH_B)]],
                supporting=[["Alpha", 1], ["Beta", 0]],
            ),
        ]
        first, second = hotpotqa.build_annotations(records)
        self.assertEqual(first["supporting_sentences"][0]["sentence"], PARAGRAPH_A[0])
        self.assertEqual(second["supporting_sentences"][0]["sentence"], PARAGRAPH_A_VARIANT[1])
        self.assertNotEqual(
            first["supporting_sentences"][0]["doc_id"],
            second["supporting_sentences"][0]["doc_id"],
        )


class ValidationTests(unittest.TestCase):
    def test_valid_record_has_no_reasons(self):
        self.assertEqual(hotpotqa.validate_record(make_record("q1")), [])

    def test_out_of_range_sentence_index_is_rejected(self):
        record = make_record("q1", supporting=[["Alpha", 9], ["Beta", 0]])
        reasons = hotpotqa.validate_record(record)
        self.assertTrue(any("out of range" in reason for reason in reasons))

    def test_unknown_supporting_title_is_rejected(self):
        record = make_record("q1", supporting=[["Gamma", 0]])
        reasons = hotpotqa.validate_record(record)
        self.assertTrue(any("absent from context" in reason for reason in reasons))

    def test_missing_field_is_rejected(self):
        record = make_record("q1")
        del record["answer"]
        self.assertTrue(any("answer" in reason for reason in hotpotqa.validate_record(record)))

    def test_duplicate_titles_in_one_context_are_rejected(self):
        record = make_record(
            "q1",
            context=[["Alpha", list(PARAGRAPH_A)], ["Alpha", list(PARAGRAPH_A_VARIANT)]],
            supporting=[["Alpha", 0]],
        )
        reasons = hotpotqa.validate_record(record)
        self.assertTrue(any("duplicate context titles" in reason for reason in reasons))

    def test_duplicate_question_ids_exclude_every_occurrence(self):
        records = [make_record("q1"), make_record("q1"), make_record("q2")]
        outcome = hotpotqa.validate_records(records)
        self.assertEqual([record["_id"] for record in outcome.valid], ["q2"])
        self.assertEqual(len(outcome.excluded), 2)
        for item in outcome.excluded:
            self.assertTrue(any("duplicate question id" in reason for reason in item.reasons))


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.records = [make_record(f"q{index:03d}") for index in range(50)]

    def test_selection_is_deterministic_and_disjoint(self):
        pilot_a, rest_a = hotpotqa.select_pilot_ids(self.records, seed=42, pilot_size=30)
        pilot_b, rest_b = hotpotqa.select_pilot_ids(self.records, seed=42, pilot_size=30)
        self.assertEqual(pilot_a, pilot_b)
        self.assertEqual(rest_a, rest_b)
        self.assertEqual(len(pilot_a), 30)
        self.assertEqual(len(set(pilot_a) & set(rest_a)), 0)
        self.assertEqual(len(set(pilot_a) | set(rest_a)), 50)

    def test_input_order_does_not_change_the_selection(self):
        shuffled = list(reversed(copy.deepcopy(self.records)))
        self.assertEqual(
            hotpotqa.select_pilot_ids(self.records, seed=42, pilot_size=30)[0],
            hotpotqa.select_pilot_ids(shuffled, seed=42, pilot_size=30)[0],
        )

    def test_different_seed_changes_the_selection(self):
        self.assertNotEqual(
            hotpotqa.select_pilot_ids(self.records, seed=42, pilot_size=30)[0],
            hotpotqa.select_pilot_ids(self.records, seed=7, pilot_size=30)[0],
        )

    def test_too_few_records_raises_instead_of_shrinking(self):
        with self.assertRaises(hotpotqa.DatasetError):
            hotpotqa.select_pilot_ids(self.records[:10], seed=42, pilot_size=30)


class WriterTests(unittest.TestCase):
    def test_jsonl_is_byte_stable_and_lf_terminated(self):
        import tempfile
        from pathlib import Path

        rows = hotpotqa.build_questions([make_record("q1"), make_record("q2")])
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.jsonl"
            second = Path(directory) / "b.jsonl"
            hotpotqa.write_jsonl(first, rows)
            hotpotqa.write_jsonl(second, rows)
            data = first.read_bytes()
            self.assertEqual(data, second.read_bytes())
            self.assertNotIn(b"\r\n", data)
            self.assertEqual(json.loads(data.splitlines()[0])["question_id"], "q1")


if __name__ == "__main__":
    unittest.main()
