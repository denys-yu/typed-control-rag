"""Unit tests for stage 4: schemas, validation, error handling, logging.

No test here creates an OpenAI client or sends a network request. The
transport is replaced by a fake that returns canned `TransportResult`s or
raises SDK exception objects built locally. Retrieval runs on a synthetic
three-document index with a fake embedding model.

Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
import numpy as np
import openai

from typed_rag import hotpotqa, llm, nodes, rag_run
from typed_rag.config import DatasetConfig, ExperimentConfig, LLMConfig, RetrievalConfig
from typed_rag.retrieval import LoadedIndex

PROJECT_PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
FAKE_SECRET = "sk-unit-test-secret-value-0123456789"


def make_documents(count: int = 3) -> list[dict]:
    documents = [
        {
            "doc_id": f"{index:064x}",
            "title": f"Title {index}",
            "sentences": [f"Sentence {index}."],
            "text": f"Sentence {index}.\nMore text {index}.",
        }
        for index in range(count)
    ]
    return sorted(documents, key=lambda document: document["doc_id"])


class FakeModel:
    def __init__(self, vector: np.ndarray):
        self.vector = vector

    def encode(self, texts, **kwargs):
        return np.tile(self.vector, (len(texts), 1)).astype(np.float32)


class FakeTransport:
    """Returns queued results in order, or raises queued exceptions."""

    def __init__(self, outcomes: list):
        self.outcomes = list(outcomes)
        self.requests: list[dict] = []

    def send(self, request: dict) -> llm.TransportResult:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def completed(text: str, **overrides) -> llm.TransportResult:
    values = {
        "response_id": "resp_test",
        "request_id": "req_test",
        "model": "test-model-returned",
        "status": "completed",
        "output_text": text,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "input_tokens_details": {"cached_tokens": 0},
        },
        "raw_response": {"id": "resp_test", "output_text_echo": text},
    }
    values.update(overrides)
    return llm.TransportResult(**values)


def http_error(cls, status: int, message: str, code: str | None = None):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status, request=request)
    body = {"message": message, "code": code} if code else None
    return cls(message, response=response, body=body)


class TempProject(unittest.TestCase):
    """A temporary project root with prompts, one pilot question and no annotations."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="typed_rag_stage4_")
        root = Path(self.tmp)
        paths = {
            "data_raw": root / "data/raw",
            "data_processed": root / "data/processed",
            "artifacts": root / "artifacts",
            "results": root / "results",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(PROJECT_PROMPTS, root / "prompts")
        (root / ".gitignore").write_text(".env\n", encoding="utf-8")

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
                top_k=2,
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
        self.doc_ids = [document["doc_id"] for document in self.documents]
        self.config.processed_dir.mkdir(parents=True, exist_ok=True)
        hotpotqa.write_jsonl(
            self.config.processed_dir / hotpotqa.QUESTIONS_FILENAME,
            [{"question": "What is sentence 1 about?", "question_id": "q1" * 12}],
        )
        # No annotations file exists in this project on purpose.
        vectors = np.eye(3, dtype=np.float32)
        self.index = LoadedIndex(
            embeddings=vectors,
            documents=self.documents,
            manifest={"index_sha256": "f" * 64, "model_name": "fake-model", "model_revision": "a" * 40},
        )
        self.model = FakeModel(vectors[1])

        self._env = os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self):
        if self._env is not None:
            os.environ["OPENAI_API_KEY"] = self._env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_with(self, outcomes: list, dry_run: bool = False) -> tuple[dict, FakeTransport]:
        transport = FakeTransport(outcomes)
        run = rag_run.run_example(
            self.config, 0, dry_run=dry_run, transport=transport, index=self.index, model=self.model
        )
        return run, transport

    def calls(self, run: dict) -> list[dict]:
        return hotpotqa.read_jsonl(Path(run["run_dir"]) / rag_run.CALLS_FILENAME)


# --- schemas and validation ------------------------------------------------------


class SchemaTests(unittest.TestCase):
    def test_schemas_are_strict(self):
        for node in nodes.NODE_NAMES:
            schema = nodes.json_schema(node)
            self.assertIs(schema["additionalProperties"], False)
            self.assertEqual(set(schema["required"]), set(schema["properties"]))

    def test_grade_valid(self):
        result = nodes.validate_output(
            nodes.NODE_GRADE,
            json.dumps({"sufficient": True, "evidence_doc_ids": ["a"], "reason": "ok"}),
            ["a", "b"],
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.output["sufficient"], True)

    def test_grade_extra_field_is_schema_error(self):
        result = nodes.validate_output(
            nodes.NODE_GRADE,
            json.dumps({"sufficient": True, "evidence_doc_ids": [], "reason": "", "extra": 1}),
            [],
        )
        self.assertEqual(result.status, nodes.SCHEMA_ERROR)

    def test_grade_wrong_type_is_schema_error(self):
        result = nodes.validate_output(
            nodes.NODE_GRADE,
            json.dumps({"sufficient": "yes", "evidence_doc_ids": [], "reason": ""}),
            [],
        )
        self.assertEqual(result.status, nodes.SCHEMA_ERROR)

    def test_invalid_json(self):
        result = nodes.validate_output(nodes.NODE_GRADE, '{"sufficient": tr', [])
        self.assertEqual(result.status, nodes.JSON_ERROR)
        self.assertIsNone(result.output)

    def test_unknown_evidence_ids(self):
        result = nodes.validate_output(
            nodes.NODE_GRADE,
            json.dumps({"sufficient": True, "evidence_doc_ids": ["a", "zzz"], "reason": "r"}),
            ["a"],
        )
        self.assertEqual(result.status, nodes.UNKNOWN_EVIDENCE)
        self.assertIn("zzz", result.errors[0])
        # The parsed output is still kept for analysis.
        self.assertEqual(result.output["evidence_doc_ids"], ["a", "zzz"])

    def test_answer_valid(self):
        result = nodes.validate_output(
            nodes.NODE_ANSWER,
            json.dumps({"decision": "answer", "answer": "42", "evidence_doc_ids": ["a"], "reason": "r"}),
            ["a"],
        )
        self.assertTrue(result.ok)

    def test_answer_invalid_decision_value(self):
        result = nodes.validate_output(
            nodes.NODE_ANSWER,
            json.dumps({"decision": "maybe", "answer": "", "evidence_doc_ids": [], "reason": "r"}),
            ["a"],
        )
        self.assertEqual(result.status, nodes.SCHEMA_ERROR)

    def test_answer_with_empty_answer_is_inconsistent(self):
        result = nodes.validate_output(
            nodes.NODE_ANSWER,
            json.dumps({"decision": "answer", "answer": "  ", "evidence_doc_ids": ["a"], "reason": "r"}),
            ["a"],
        )
        self.assertEqual(result.status, nodes.INCONSISTENT_DECISION)

    def test_answer_without_evidence_is_inconsistent(self):
        result = nodes.validate_output(
            nodes.NODE_ANSWER,
            json.dumps({"decision": "answer", "answer": "42", "evidence_doc_ids": [], "reason": "r"}),
            ["a"],
        )
        self.assertEqual(result.status, nodes.INCONSISTENT_DECISION)

    def test_abstain_with_answer_is_inconsistent(self):
        result = nodes.validate_output(
            nodes.NODE_ANSWER,
            json.dumps({"decision": "abstain", "answer": "42", "evidence_doc_ids": [], "reason": "r"}),
            ["a"],
        )
        self.assertEqual(result.status, nodes.INCONSISTENT_DECISION)

    def test_abstain_valid_with_empty_answer(self):
        result = nodes.validate_output(
            nodes.NODE_ANSWER,
            json.dumps({"decision": "abstain", "answer": "", "evidence_doc_ids": [], "reason": "r"}),
            ["a"],
        )
        self.assertTrue(result.ok)


class RequestTests(TempProject):
    def test_request_shape(self):
        request = nodes.build_request(self.config, nodes.NODE_ANSWER, "Q?", self.documents[:2])
        self.assertEqual(request["model"], "test-model")
        self.assertEqual(request["temperature"], 0.0)
        self.assertEqual(request["max_output_tokens"], 800)
        self.assertIs(request["store"], False)
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertIs(request["text"]["format"]["strict"], True)
        self.assertNotIn("previous_response_id", request)
        self.assertNotIn("tools", request)
        self.assertNotIn("stream", request)
        text = request["input"][0]["content"][0]["text"]
        for document in self.documents[:2]:
            self.assertIn(document["doc_id"], text)
            self.assertIn(document["title"], text)
            self.assertIn(document["text"], text)
        self.assertNotIn("score", text)

    def test_prompts_are_english_files(self):
        for node in nodes.NODE_NAMES:
            self.assertTrue(nodes.load_prompt(self.config, node).strip())


# --- error classification -----------------------------------------------------------


class ClassificationTests(unittest.TestCase):
    def test_kinds(self):
        request = httpx.Request("POST", "https://api.openai.com/v1/responses")
        cases = [
            (http_error(openai.AuthenticationError, 401, "bad key"), llm.AUTHENTICATION),
            (http_error(openai.RateLimitError, 429, "quota", "insufficient_quota"), llm.RATE_LIMIT_OR_QUOTA),
            (http_error(openai.NotFoundError, 404, "no model"), llm.MODEL_UNAVAILABLE),
            (http_error(openai.PermissionDeniedError, 403, "no"), llm.PERMISSION_DENIED),
            (http_error(openai.BadRequestError, 400, "bad"), llm.BAD_REQUEST),
            (http_error(openai.InternalServerError, 500, "boom"), llm.API_STATUS),
            (openai.APITimeoutError(request=request), llm.TIMEOUT),
            (openai.APIConnectionError(request=request), llm.CONNECTION),
            (RuntimeError("weird"), llm.UNEXPECTED),
        ]
        for exc, kind in cases:
            with self.subTest(kind=kind):
                self.assertEqual(llm.classify_exception(exc)["kind"], kind)

    def test_response_outcomes(self):
        self.assertEqual(llm.transport_outcome(completed("{}"))[0], llm.TRANSPORT_OK)
        self.assertEqual(
            llm.transport_outcome(completed(None, refusal="I cannot help"))[0], llm.PROVIDER_REFUSAL
        )
        self.assertEqual(
            llm.transport_outcome(
                completed('{"partial', status="incomplete", incomplete_reason="max_output_tokens")
            )[0],
            llm.INCOMPLETE_RESPONSE,
        )
        self.assertEqual(
            llm.transport_outcome(completed(None, status="failed", error={"message": "x"}))[0],
            llm.RESPONSE_FAILED,
        )
        self.assertEqual(llm.transport_outcome(completed(None))[0], llm.EMPTY_OUTPUT)


# --- full runs with a fake transport ------------------------------------------------


class RunTests(TempProject):
    def grade_text(self, sufficient=True, ids=None):
        return json.dumps(
            {"sufficient": sufficient, "evidence_doc_ids": ids or [self.doc_ids[1]], "reason": "r"}
        )

    def answer_text(self, decision="answer", answer="Sentence 1", ids=None):
        return json.dumps(
            {"decision": decision, "answer": answer, "evidence_doc_ids": ids or [self.doc_ids[1]], "reason": "r"}
        )

    def test_dry_run_makes_no_calls_and_needs_no_client(self):
        with mock.patch.object(llm, "create_client", side_effect=AssertionError("client created")):
            run, transport = self.run_with([AssertionError("must not be called")], dry_run=True)
        self.assertEqual(run["status"], rag_run.RUN_DRY)
        self.assertEqual(run["api_calls"], 0)
        self.assertEqual(transport.requests, [])
        run_dir = Path(run["run_dir"])
        self.assertTrue(run_dir.parent.name == "rag_dry_runs")
        self.assertFalse((run_dir / rag_run.CALLS_FILENAME).exists())
        saved = json.loads((run_dir / rag_run.REQUESTS_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(set(saved["requests"]), set(nodes.NODE_NAMES))
        self.assertEqual(run["grader"], {"status": rag_run.NODE_NOT_RUN})

    def test_missing_key_raises_before_any_client(self):
        with mock.patch.object(llm, "create_client", side_effect=AssertionError("client created")):
            with self.assertRaises(llm.MissingAPIKeyError):
                rag_run.run_example(self.config, 0, index=self.index, model=self.model)

    def test_key_resolution_prefers_environment(self):
        self.config.env_file_path.write_text("OPENAI_API_KEY=from-dotenv\n", encoding="utf-8")
        self.assertEqual(llm.resolve_api_key(self.config), ("from-dotenv", ".env"))
        os.environ["OPENAI_API_KEY"] = "from-env"
        self.assertEqual(llm.resolve_api_key(self.config), ("from-env", "environment"))
        os.environ["OPENAI_API_KEY"] = "   "
        self.assertEqual(llm.resolve_api_key(self.config), ("from-dotenv", ".env"))
        self.config.env_file_path.write_text("OPENAI_API_KEY=\n", encoding="utf-8")
        self.assertEqual(llm.resolve_api_key(self.config), (None, None))
        self.assertEqual(llm.api_key_status(self.config)["status"], llm.KEY_MISSING)

    def test_successful_run_logs_everything(self):
        run, transport = self.run_with([completed(self.grade_text()), completed(self.answer_text())])
        self.assertEqual(run["status"], rag_run.RUN_COMPLETED)
        self.assertEqual(run["api_calls"], 2)
        self.assertEqual(run["grader"]["status"], rag_run.NODE_OK)
        self.assertEqual(run["generator"]["output"]["answer"], "Sentence 1")
        self.assertEqual(run["usage_totals"]["total_tokens"], 240)
        self.assertEqual(run["mode"], "stage4_diagnostic")

        # The generator request carries nothing from the grader.
        answer_request = transport.requests[1]
        self.assertNotIn("sufficient", json.dumps(answer_request))
        self.assertEqual(
            transport.requests[0]["input"], answer_request["input"]
        )

        run_dir = Path(run["run_dir"])
        calls = self.calls(run)
        self.assertEqual([c["node"] for c in calls], [nodes.NODE_GRADE, nodes.NODE_ANSWER])
        for call in calls:
            self.assertEqual(call["model_requested"], "test-model")
            self.assertEqual(call["model_returned"], "test-model-returned")
            self.assertEqual(call["response_id"], "resp_test")
            self.assertEqual(call["request_id"], "req_test")
            self.assertIn("prompt_sha256", call["hashes"])
            self.assertIn("schema_sha256", call["hashes"])
            self.assertEqual(call["request"]["text"]["format"]["strict"], True)
            self.assertEqual(call["usage"]["input_tokens"], 100)
            self.assertIsNotNone(call["latency_seconds"])
        context = json.loads((run_dir / rag_run.CONTEXT_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(len(context["documents"]), 2)
        self.assertIn("score", context["documents"][0])
        self.assertEqual(context["documents"][0]["doc_id"], self.doc_ids[1])
        self.assertTrue((run_dir / rag_run.RAW_DIRNAME / "answer_response.json").exists())

    def test_grader_verdict_does_not_gate_generator(self):
        run, transport = self.run_with(
            [completed(self.grade_text(sufficient=False, ids=[])), completed(self.answer_text("abstain", ""))]
        )
        self.assertEqual(len(transport.requests), 2)
        self.assertEqual(run["status"], rag_run.RUN_COMPLETED)
        self.assertEqual(run["generator"]["output"]["decision"], "abstain")

    def test_unknown_doc_ids_are_flagged_and_raw_kept(self):
        run, _ = self.run_with(
            [completed(self.grade_text(ids=["0" * 63 + "9"])), completed(self.answer_text())]
        )
        self.assertEqual(run["status"], rag_run.RUN_INVALID_OUTPUT)
        self.assertEqual(run["grader"]["status"], nodes.UNKNOWN_EVIDENCE)
        self.assertEqual(run["generator"]["status"], rag_run.NODE_OK)
        raw = json.loads(
            (Path(run["run_dir"]) / rag_run.RAW_DIRNAME / "grade_binary_response.json").read_text(encoding="utf-8")
        )
        self.assertIn("0" * 63 + "9", raw["output_text"])
        self.assertIn("0" * 63 + "9", self.calls(run)[0]["output_text"])

    def test_inconsistent_answer_is_flagged(self):
        run, _ = self.run_with([completed(self.grade_text()), completed(self.answer_text("abstain", "leak"))])
        self.assertEqual(run["generator"]["status"], nodes.INCONSISTENT_DECISION)
        self.assertEqual(run["status"], rag_run.RUN_INVALID_OUTPUT)

    def test_invalid_json_keeps_raw_text(self):
        run, _ = self.run_with([completed('{"sufficient": tru'), completed(self.answer_text())])
        self.assertEqual(run["grader"]["status"], nodes.JSON_ERROR)
        self.assertEqual(self.calls(run)[0]["output_text"], '{"sufficient": tru')
        self.assertIsNone(self.calls(run)[0]["output"])

    def test_provider_refusal_is_not_abstention_and_skips_generator(self):
        run, transport = self.run_with([completed(None, refusal="I cannot do that.")])
        self.assertEqual(run["status"], rag_run.RUN_TECHNICAL_FAILURE)
        self.assertEqual(run["grader"]["status"], llm.PROVIDER_REFUSAL)
        self.assertEqual(run["generator"]["status"], rag_run.NODE_SKIPPED)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(run["api_calls"], 1)
        self.assertEqual(self.calls(run)[0]["refusal"], "I cannot do that.")

    def test_incomplete_response(self):
        run, _ = self.run_with(
            [completed('{"suff', status="incomplete", incomplete_reason="max_output_tokens")]
        )
        self.assertEqual(run["grader"]["status"], llm.INCOMPLETE_RESPONSE)
        self.assertEqual(run["status"], rag_run.RUN_TECHNICAL_FAILURE)
        self.assertEqual(self.calls(run)[0]["incomplete_reason"], "max_output_tokens")
        self.assertEqual(self.calls(run)[0]["output_text"], '{"suff')

    def test_api_errors_are_recorded_not_raised(self):
        for exc, kind in [
            (http_error(openai.AuthenticationError, 401, "bad key"), llm.AUTHENTICATION),
            (http_error(openai.RateLimitError, 429, "quota", "insufficient_quota"), llm.RATE_LIMIT_OR_QUOTA),
            (http_error(openai.NotFoundError, 404, "no such model"), llm.MODEL_UNAVAILABLE),
            (openai.APITimeoutError(request=httpx.Request("POST", "https://x")), llm.TIMEOUT),
        ]:
            with self.subTest(kind=kind):
                run, transport = self.run_with([exc])
                self.assertEqual(run["status"], rag_run.RUN_TECHNICAL_FAILURE)
                self.assertEqual(run["grader"]["status"], kind)
                self.assertEqual(run["generator"]["status"], rag_run.NODE_SKIPPED)
                self.assertEqual(len(transport.requests), 1)
                call = self.calls(run)[0]
                self.assertEqual(call["error"]["kind"], kind)
                self.assertIsNone(call["response_id"])

    def test_generator_api_error_after_good_grader(self):
        run, _ = self.run_with(
            [completed(self.grade_text()), http_error(openai.RateLimitError, 429, "slow down")]
        )
        self.assertEqual(run["status"], rag_run.RUN_TECHNICAL_FAILURE)
        self.assertEqual(run["grader"]["status"], rag_run.NODE_OK)
        self.assertEqual(run["generator"]["status"], llm.RATE_LIMIT_OR_QUOTA)
        self.assertEqual(run["api_calls"], 2)

    def test_runs_without_annotations_file(self):
        self.assertFalse((self.config.processed_dir / hotpotqa.ANNOTATIONS_FILENAME).exists())
        run, _ = self.run_with([completed(self.grade_text()), completed(self.answer_text())])
        self.assertEqual(run["status"], rag_run.RUN_COMPLETED)

    def test_no_secrets_in_logs(self):
        os.environ["OPENAI_API_KEY"] = FAKE_SECRET
        self.config.env_file_path.write_text(f"OPENAI_API_KEY={FAKE_SECRET}\n", encoding="utf-8")
        run, _ = self.run_with([completed(self.grade_text()), completed(self.answer_text())])
        for path in Path(run["run_dir"]).rglob("*"):
            if path.is_file():
                self.assertNotIn(FAKE_SECRET, path.read_text(encoding="utf-8"), path.name)
        self.assertNotIn(FAKE_SECRET, json.dumps(run))
        text, ok = rag_run.format_llm_config_check(self.config)
        self.assertNotIn(FAKE_SECRET, text)
        self.assertIn("api key       : configured", text)

    def test_client_is_built_with_config_but_never_used(self):
        client = llm.create_client(self.config, FAKE_SECRET)
        self.assertEqual(client.max_retries, 0)
        self.assertEqual(client.timeout, 60.0)


if __name__ == "__main__":
    unittest.main()
