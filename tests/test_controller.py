"""Unit tests for stage 5: branches A-D, transition rules, retry, logging.

Every LLM response here is a fixed fake. This checks the controllers, not the
research question. No network, no client, no gold annotations.

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

from typed_rag import controller, hotpotqa, llm, nodes, rag_run
from typed_rag.config import (
    ControllerConfig,
    DatasetConfig,
    ExperimentConfig,
    LLMConfig,
    RetrievalConfig,
)
from typed_rag.controller import (
    OUTCOME_ANSWERED,
    OUTCOME_BUDGET_EXHAUSTED,
    OUTCOME_CONTROLLER_ABSTAINED,
    OUTCOME_ESCALATED,
    OUTCOME_GENERATOR_ABSTAINED,
    OUTCOME_INVALID_GRADER_OUTPUT,
    OUTCOME_TECHNICAL_FAILURE,
    RUN_BUDGET_EXHAUSTED,
    RUN_COMPLETED,
    RUN_TECHNICAL_FAILURE,
    expected_action_binary,
    expected_action_typed,
)
from typed_rag.retrieval import LoadedIndex

PROJECT_PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
FAKE_SECRET = "sk-unit-test-secret-value-0123456789"


def make_documents(count: int = 4) -> list[dict]:
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


class QueryModel:
    """Query text decides the vector: the rewritten query moves the ranking."""

    def __init__(self, vectors: dict[str, np.ndarray], default: np.ndarray):
        self.vectors = vectors
        self.default = default
        self.queries: list[str] = []

    def encode(self, texts, **kwargs):
        self.queries.extend(texts)
        return np.stack([self.vectors.get(text, self.default) for text in texts]).astype(np.float32)


class FakeTransport:
    def __init__(self, outcomes: list):
        self.outcomes = list(outcomes)
        self.requests: list[dict] = []

    def send(self, request: dict) -> llm.TransportResult:
        self.requests.append(request)
        if not self.outcomes:
            raise AssertionError("more API calls than expected")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def completed(payload, **overrides) -> llm.TransportResult:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    values = {
        "response_id": "resp_test",
        "request_id": "req_test",
        "model": "test-model",
        "status": "completed",
        "output_text": text,
        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "input_tokens_details": {"cached_tokens": 0}},
        "raw_response": {"id": "resp_test"},
    }
    values.update(overrides)
    return llm.TransportResult(**values)


def http_error(cls, status: int, message: str):
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return cls(message, response=httpx.Response(status, request=request), body=None)


class ControllerProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="typed_rag_stage5_")
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
                name="hotpotqa", split="dev", setting="distractor", version="v1",
                filename="raw.json", processed_dirname="hotpotqa",
                url="https://example.invalid/raw.json", mirror_urls=(),
            ),
            retrieval=RetrievalConfig(
                model_name="fake-model", model_revision="a" * 40, index_dirname="retrieval",
                model_cache_dirname="models", batch_size=8, top_k=2,
            ),
            llm=LLMConfig(
                provider="openai", api="responses", model="test-model", temperature=0.0,
                max_output_tokens=800, timeout_seconds=60.0, max_retries=0, store=False,
                prompts_dirname="prompts", runs_dirname="rag_runs", dry_runs_dirname="rag_dry_runs",
                api_key_env="OPENAI_API_KEY", env_filename=".env",
            ),
            project_root=root,
            config_path=root / "config/experiment.json",
            paths=paths,
            controller=ControllerConfig(
                max_search_retries=1, policy_version="test-v1",
                runs_dirname="controlled_runs", dry_runs_dirname="controlled_dry_runs",
            ),
        )
        self.documents = make_documents(4)
        self.ids = [d["doc_id"] for d in self.documents]
        self.config.processed_dir.mkdir(parents=True, exist_ok=True)
        self.question = "What is sentence 1 about?"
        hotpotqa.write_jsonl(
            self.config.processed_dir / hotpotqa.QUESTIONS_FILENAME,
            [{"question": self.question, "question_id": "q1" * 12}],
        )
        vectors = np.eye(4, dtype=np.float32)
        self.index = LoadedIndex(
            embeddings=vectors, documents=self.documents,
            manifest={"index_sha256": "f" * 64, "model_name": "fake-model", "model_revision": "a" * 40},
        )
        # Original question -> docs 1,0 ; rewritten query -> docs 3,2 ; other -> same as original.
        self.rewritten = "find sentence three"
        self.model = QueryModel(
            {self.question: vectors[1] + 0.5 * vectors[0], self.rewritten: vectors[3] + 0.5 * vectors[2]},
            vectors[1] + 0.5 * vectors[0],
        )
        self.first_ids = [self.ids[1], self.ids[0]]
        self.second_ids = [self.ids[3], self.ids[2]]
        self._env = os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self):
        if self._env is not None:
            os.environ["OPENAI_API_KEY"] = self._env
        shutil.rmtree(self.tmp, ignore_errors=True)

    # canned outputs -----------------------------------------------------------
    def binary(self, sufficient, action, ids=None):
        return completed({"sufficient": sufficient, "proposed_action": action, "evidence_doc_ids": ids or [], "reason": "r"})

    def typed(self, state, action, ids=None):
        return completed({"state": state, "proposed_action": action, "evidence_doc_ids": ids or [], "reason": "r"})

    def rewrite(self, query=None):
        return completed({"rewritten_query": self.rewritten if query is None else query, "reason": "r"})

    def answer(self, decision="answer", text="Sentence 1", ids=None):
        return completed({"decision": decision, "answer": text, "evidence_doc_ids": ids if ids is not None else [self.ids[1]], "reason": "r"})

    def run_branch(self, branch, outcomes, dry_run=False):
        transport = FakeTransport(outcomes)
        run = controller.run_controlled(
            self.config, 0, branch, dry_run=dry_run, transport=transport, index=self.index, model=self.model
        )
        return run, transport

    def calls(self, run):
        return hotpotqa.read_jsonl(Path(run["run_dir"]) / controller.CALLS_FILENAME)

    def context(self, run):
        return json.loads((Path(run["run_dir"]) / controller.CONTEXT_FILENAME).read_text(encoding="utf-8"))


# --- pure rules ----------------------------------------------------------------


class RuleTests(unittest.TestCase):
    def test_binary_rules(self):
        self.assertEqual(expected_action_binary(True, 0, 1), "answer")
        self.assertEqual(expected_action_binary(True, 1, 1), "answer")
        self.assertEqual(expected_action_binary(False, 0, 1), "retry")
        self.assertEqual(expected_action_binary(False, 1, 1), "abstain")

    def test_typed_rules(self):
        self.assertEqual(expected_action_typed("OK", 0, 1), "answer")
        self.assertEqual(expected_action_typed("EMPTY", 0, 1), "abstain")
        self.assertEqual(expected_action_typed("INCONSISTENT", 0, 1), "escalate")
        self.assertEqual(expected_action_typed("INCONSISTENT", 1, 1), "escalate")
        self.assertEqual(expected_action_typed("PARTIAL", 0, 1), "retry")
        self.assertEqual(expected_action_typed("PARTIAL", 1, 1), "abstain")
        with self.assertRaises(ValueError):
            expected_action_typed("MAYBE", 0, 1)

    def test_binary_policy_never_escalates(self):
        for sufficient in (True, False):
            for used in (0, 1):
                self.assertNotEqual(expected_action_binary(sufficient, used, 1), "escalate")

    def test_branches(self):
        self.assertEqual(controller.get_branch("a").name, "A")
        with self.assertRaises(controller.BranchError):
            controller.get_branch("E")
        self.assertEqual(controller.BRANCHES["A"].grader_node, controller.BRANCHES["C"].grader_node)
        self.assertEqual(controller.BRANCHES["B"].grader_node, controller.BRANCHES["D"].grader_node)
        self.assertNotEqual(controller.BRANCHES["A"].grader_node, controller.BRANCHES["B"].grader_node)

    def test_new_schemas_are_strict(self):
        for node in (nodes.NODE_GRADE_BINARY_ACTION, nodes.NODE_GRADE_TYPED_ACTION, nodes.NODE_REWRITE):
            schema = nodes.json_schema(node)
            self.assertIs(schema["additionalProperties"], False)
            self.assertEqual(set(schema["required"]), set(schema["properties"]))
        self.assertEqual(nodes.json_schema(nodes.NODE_GRADE_BINARY_ACTION)["properties"]["proposed_action"]["enum"], list(nodes.ACTIONS))
        self.assertEqual(nodes.json_schema(nodes.NODE_GRADE_TYPED_ACTION)["properties"]["state"]["enum"], list(nodes.STATES))
        # stage 4 schema untouched
        self.assertEqual(list(nodes.json_schema(nodes.NODE_GRADE)["properties"]), ["sufficient", "evidence_doc_ids", "reason"])

    def test_validation_of_new_nodes(self):
        bad = nodes.validate_output(nodes.NODE_GRADE_TYPED_ACTION, json.dumps({"state": "MAYBE", "proposed_action": "answer", "evidence_doc_ids": [], "reason": ""}), [])
        self.assertEqual(bad.status, nodes.SCHEMA_ERROR)
        bad = nodes.validate_output(nodes.NODE_GRADE_BINARY_ACTION, json.dumps({"sufficient": True, "proposed_action": "think", "evidence_doc_ids": [], "reason": ""}), [])
        self.assertEqual(bad.status, nodes.SCHEMA_ERROR)
        empty = nodes.validate_output(nodes.NODE_REWRITE, json.dumps({"rewritten_query": "  ", "reason": ""}), [])
        self.assertEqual(empty.status, nodes.EMPTY_REWRITE)
        ok = nodes.validate_output(nodes.NODE_REWRITE, json.dumps({"rewritten_query": "x", "reason": ""}), [])
        self.assertTrue(ok.ok)


# --- trajectories --------------------------------------------------------------


class BinaryBranchTests(ControllerProject):
    def test_sufficient_true_answers(self):
        for branch in ("A", "C"):
            with self.subTest(branch=branch):
                run, transport = self.run_branch(branch, [self.binary(True, "answer", [self.ids[1]]), self.answer()])
                self.assertEqual(run["status"], RUN_COMPLETED)
                self.assertEqual(run["final_outcome"], OUTCOME_ANSWERED)
                self.assertEqual(run["executed_actions"], ["answer"])
                self.assertEqual(run["searches"], 1)
                self.assertEqual(run["api_calls"], 2)
                self.assertFalse(run["any_policy_mismatch"])
                self.assertEqual(run["generator"]["output"]["answer"], "Sentence 1")

    def test_insufficient_then_sufficient_after_retry(self):
        for branch in ("A", "C"):
            with self.subTest(branch=branch):
                run, transport = self.run_branch(
                    branch,
                    [self.binary(False, "retry"), self.rewrite(), self.binary(True, "answer", [self.ids[3]]), self.answer(ids=[self.ids[3]])],
                )
                self.assertEqual(run["final_outcome"], OUTCOME_ANSWERED)
                self.assertEqual(run["executed_actions"], ["retry", "answer"])
                self.assertEqual(run["searches"], 2)
                self.assertEqual(run["retries_used"], 1)
                self.assertEqual(run["api_calls"], 4)
                ctx = self.context(run)
                self.assertEqual(ctx["contexts"][0]["doc_ids"], self.first_ids)
                self.assertEqual(ctx["contexts"][1]["doc_ids"], self.second_ids)
                self.assertEqual(ctx["contexts"][1]["query"], self.rewritten)
                self.assertFalse(ctx["contexts"][1]["same_as_previous"])
                # both graders and the generator saw the *current* context, never a merge
                second_grader_input = transport.requests[2]["input"][0]["content"][0]["text"]
                self.assertIn(self.ids[3], second_grader_input)
                self.assertNotIn(self.ids[1], second_grader_input)
                self.assertIn("1 retry used of 1; 0 remaining", second_grader_input)
                generator_input = transport.requests[3]["input"][0]["content"][0]["text"]
                self.assertIn(self.question, generator_input)
                self.assertNotIn(self.rewritten, generator_input)
                # exactly two searches per run: the original question and the rewritten query
                self.assertEqual(self.model.queries[-2:], [self.question, self.rewritten])

    def test_insufficient_twice_abstains(self):
        for branch in ("A", "C"):
            with self.subTest(branch=branch):
                run, _ = self.run_branch(branch, [self.binary(False, "retry"), self.rewrite(), self.binary(False, "abstain")])
                self.assertEqual(run["status"], RUN_COMPLETED)
                self.assertEqual(run["final_outcome"], OUTCOME_CONTROLLER_ABSTAINED)
                self.assertEqual(run["executed_actions"], ["retry", "abstain"])
                self.assertEqual(run["api_calls"], 3)
                self.assertEqual(run["generator"]["status"], "not_run")

    def test_mismatch_A_executes_proposed_C_executes_expected(self):
        # Same grader output: sufficient=false but the LLM proposes "answer".
        outcome = lambda: self.binary(False, "answer", [self.ids[1]])
        run_a, _ = self.run_branch("A", [outcome(), self.answer()])
        self.assertEqual(run_a["executed_actions"], ["answer"])
        self.assertTrue(run_a["trajectory"][0]["policy_mismatch"])
        self.assertFalse(run_a["trajectory"][0]["policy_override"])
        self.assertEqual(run_a["trajectory"][0]["expected_action"], "retry")
        self.assertEqual(run_a["final_outcome"], OUTCOME_ANSWERED)

        run_c, _ = self.run_branch("C", [outcome(), self.rewrite(), self.binary(False, "abstain")])
        self.assertEqual(run_c["executed_actions"], ["retry", "abstain"])
        self.assertTrue(run_c["trajectory"][0]["policy_mismatch"])
        self.assertTrue(run_c["trajectory"][0]["policy_override"])
        self.assertEqual(run_c["proposed_actions"], ["answer", "abstain"])
        self.assertEqual(run_c["final_outcome"], OUTCOME_CONTROLLER_ABSTAINED)

    def test_retry_after_budget_exhausted_in_A(self):
        run, transport = self.run_branch("A", [self.binary(False, "retry"), self.rewrite(), self.binary(False, "retry")])
        self.assertEqual(run["status"], RUN_BUDGET_EXHAUSTED)
        self.assertEqual(run["final_outcome"], OUTCOME_BUDGET_EXHAUSTED)
        self.assertEqual(run["executed_actions"], ["retry", None])
        self.assertTrue(run["trajectory"][1]["budget_violation"])
        self.assertEqual(run["trajectory"][1]["expected_action"], "abstain")
        self.assertTrue(run["trajectory"][1]["policy_mismatch"])
        self.assertEqual(run["searches"], 2)
        self.assertEqual(len(transport.requests), 3)
        self.assertEqual(run["generator"]["status"], "not_run")

    def test_same_C_input_never_exceeds_budget(self):
        run, _ = self.run_branch("C", [self.binary(False, "retry"), self.rewrite(), self.binary(False, "retry")])
        self.assertEqual(run["status"], RUN_COMPLETED)
        self.assertEqual(run["executed_actions"], ["retry", "abstain"])
        self.assertTrue(run["trajectory"][1]["policy_override"])


class TypedBranchTests(ControllerProject):
    def test_each_state(self):
        cases = {
            "OK": (["answer"], OUTCOME_ANSWERED, [self.typed("OK", "answer", [self.ids[1]]), self.answer()]),
            "EMPTY": (["abstain"], OUTCOME_CONTROLLER_ABSTAINED, [self.typed("EMPTY", "abstain")]),
            "INCONSISTENT": (["escalate"], OUTCOME_ESCALATED, [self.typed("INCONSISTENT", "escalate", [self.ids[1], self.ids[0]])]),
            "PARTIAL": (["retry", "answer"], OUTCOME_ANSWERED, [self.typed("PARTIAL", "retry"), self.rewrite(), self.typed("OK", "answer", [self.ids[3]]), self.answer(ids=[self.ids[3]])]),
        }
        for branch in ("B", "D"):
            for state, (executed, outcome, outcomes) in cases.items():
                with self.subTest(branch=branch, state=state):
                    run, _ = self.run_branch(branch, list(outcomes))
                    self.assertEqual(run["status"], RUN_COMPLETED)
                    self.assertEqual(run["executed_actions"], executed)
                    self.assertEqual(run["final_outcome"], outcome)
                    self.assertFalse(run["any_policy_mismatch"])
                    if state == "INCONSISTENT":
                        self.assertIsNotNone(run["escalation"])
                        self.assertEqual(run["generator"]["status"], "not_run")

    def test_partial_retry_partial_abstain(self):
        for branch in ("B", "D"):
            with self.subTest(branch=branch):
                run, _ = self.run_branch(branch, [self.typed("PARTIAL", "retry"), self.rewrite(), self.typed("PARTIAL", "abstain")])
                self.assertEqual(run["executed_actions"], ["retry", "abstain"])
                self.assertEqual(run["final_outcome"], OUTCOME_CONTROLLER_ABSTAINED)
                self.assertEqual(run["retries_used"], 1)

    def test_partial_retry_inconsistent_escalate(self):
        for branch in ("B", "D"):
            with self.subTest(branch=branch):
                run, _ = self.run_branch(branch, [self.typed("PARTIAL", "retry"), self.rewrite(), self.typed("INCONSISTENT", "escalate")])
                self.assertEqual(run["executed_actions"], ["retry", "escalate"])
                self.assertEqual(run["final_outcome"], OUTCOME_ESCALATED)
                self.assertEqual(run["escalation"]["iteration"], 2)

    def test_mismatch_B_vs_D(self):
        # Same output: state EMPTY but the LLM proposes retry.
        run_b, _ = self.run_branch("B", [self.typed("EMPTY", "retry"), self.rewrite(), self.typed("EMPTY", "abstain")])
        self.assertEqual(run_b["executed_actions"], ["retry", "abstain"])
        self.assertTrue(run_b["trajectory"][0]["policy_mismatch"])
        self.assertFalse(run_b["trajectory"][0]["policy_override"])

        run_d, _ = self.run_branch("D", [self.typed("EMPTY", "retry")])
        self.assertEqual(run_d["executed_actions"], ["abstain"])
        self.assertTrue(run_d["trajectory"][0]["policy_override"])
        self.assertEqual(run_d["searches"], 1)
        self.assertEqual(run_d["api_calls"], 1)

    def test_budget_exhausted_in_B(self):
        run, _ = self.run_branch("B", [self.typed("PARTIAL", "retry"), self.rewrite(), self.typed("PARTIAL", "retry")])
        self.assertEqual(run["status"], RUN_BUDGET_EXHAUSTED)
        self.assertEqual(run["executed_actions"], ["retry", None])
        self.assertNotEqual(run["final_outcome"], OUTCOME_CONTROLLER_ABSTAINED)


class GeneratorAndFailureTests(ControllerProject):
    def test_generator_abstain_after_answer_action(self):
        run, _ = self.run_branch("D", [self.typed("OK", "answer", [self.ids[1]]), self.answer("abstain", "", ids=[])])
        self.assertEqual(run["status"], RUN_COMPLETED)
        self.assertEqual(run["executed_actions"], ["answer"])
        self.assertEqual(run["final_outcome"], OUTCOME_GENERATOR_ABSTAINED)
        self.assertEqual(run["generator"]["output"]["decision"], "abstain")

    def test_generator_input_identical_across_branches_and_stage4(self):
        inputs = {}
        for branch in ("A", "B", "C", "D"):
            grade = self.binary(True, "answer", [self.ids[1]]) if branch in "AC" else self.typed("OK", "answer", [self.ids[1]])
            run, transport = self.run_branch(branch, [grade, self.answer()])
            inputs[branch] = transport.requests[1]
        self.assertEqual(len({json.dumps(r, sort_keys=True) for r in inputs.values()}), 1)
        stage4 = nodes.build_request(self.config, nodes.NODE_ANSWER, self.question, [{k: d[k] for k in ("doc_id", "title", "text")} for d in [self.documents[1], self.documents[0]]])
        self.assertEqual(json.dumps(stage4, sort_keys=True), json.dumps(inputs["A"], sort_keys=True))
        text = json.dumps(inputs["A"])
        for forbidden in ("branch", "proposed_action", "sufficient", '"state"', "Retry budget"):
            self.assertNotIn(forbidden, text)

    def test_grader_requests_identical_for_AC_and_for_BD(self):
        reqs = {}
        for branch in ("A", "B", "C", "D"):
            grade = self.binary(True, "answer") if branch in "AC" else self.typed("OK", "answer")
            _, transport = self.run_branch(branch, [grade, self.answer()])
            reqs[branch] = json.dumps(transport.requests[0], sort_keys=True)
        self.assertEqual(reqs["A"], reqs["C"])
        self.assertEqual(reqs["B"], reqs["D"])
        self.assertNotEqual(reqs["A"], reqs["B"])
        for branch, text in reqs.items():
            lowered = text.lower()
            for forbidden in ("branch a", "branch b", "branch c", "branch d", '"branch"', "enforce", "contract"):
                self.assertNotIn(forbidden, lowered, branch)

    def test_rewrite_failure_is_technical(self):
        for outcome in (http_error(openai.RateLimitError, 429, "slow"), completed({"rewritten_query": "", "reason": ""}), completed(None, refusal="no")):
            with self.subTest(outcome=type(outcome).__name__):
                run, _ = self.run_branch("D", [self.typed("PARTIAL", "retry"), outcome])
                self.assertEqual(run["status"], RUN_TECHNICAL_FAILURE)
                self.assertEqual(run["final_outcome"], OUTCOME_TECHNICAL_FAILURE)
                self.assertEqual(run["failure"]["stage"], "rewrite")
                self.assertEqual(run["searches"], 1)
                self.assertEqual(run["retries_used"], 1)

    def test_second_grader_failure_is_technical(self):
        run, _ = self.run_branch("C", [self.binary(False, "retry"), self.rewrite(), http_error(openai.AuthenticationError, 401, "bad")])
        self.assertEqual(run["status"], RUN_TECHNICAL_FAILURE)
        self.assertEqual(run["failure"]["stage"], "grader")
        self.assertEqual(run["failure"]["iteration"], 2)
        self.assertEqual(run["failure"]["error"]["kind"], llm.AUTHENTICATION)
        self.assertEqual(run["final_outcome"], OUTCOME_TECHNICAL_FAILURE)
        self.assertEqual(run["trajectory"][1]["executed_action"], None)
        self.assertEqual(run["searches"], 2)

    def test_invalid_grader_json_is_not_abstention(self):
        run, _ = self.run_branch("A", [completed('{"sufficient": tru')])
        self.assertEqual(run["status"], RUN_TECHNICAL_FAILURE)
        self.assertEqual(run["final_outcome"], OUTCOME_INVALID_GRADER_OUTPUT)

    def test_unknown_evidence_is_logged_but_trajectory_continues(self):
        run, _ = self.run_branch("D", [self.typed("OK", "answer", ["9" * 64]), self.answer()])
        self.assertEqual(run["status"], RUN_COMPLETED)
        self.assertEqual(run["trajectory"][0]["grader_status"], nodes.UNKNOWN_EVIDENCE)
        self.assertEqual(len(run["validation_issues"]), 1)

    def test_generator_technical_failure(self):
        run, _ = self.run_branch("A", [self.binary(True, "answer"), http_error(openai.NotFoundError, 404, "gone")])
        self.assertEqual(run["status"], RUN_TECHNICAL_FAILURE)
        self.assertEqual(run["failure"]["stage"], "generator")
        self.assertEqual(run["executed_actions"], ["answer"])

    def test_identical_retrieval_after_rewrite_is_recorded(self):
        run, _ = self.run_branch("D", [self.typed("PARTIAL", "retry"), self.rewrite("something else"), self.typed("PARTIAL", "abstain")])
        ctx = self.context(run)
        self.assertTrue(ctx["contexts"][1]["same_as_previous"])
        self.assertEqual(run["retries_used"], 1)
        self.assertEqual(run["final_outcome"], OUTCOME_CONTROLLER_ABSTAINED)


class LoggingTests(ControllerProject):
    def test_dry_run_no_client_no_calls(self):
        with mock.patch.object(llm, "create_client", side_effect=AssertionError("client")):
            run, transport = self.run_branch("D", [AssertionError("no")], dry_run=True)
        self.assertEqual(run["status"], "dry_run")
        self.assertEqual(transport.requests, [])
        self.assertEqual(run["searches"], 1)
        saved = json.loads((Path(run["run_dir"]) / controller.REQUESTS_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual(saved["first_grader_request"]["text"]["format"]["name"], "context_grade_typed_action")
        self.assertFalse((Path(run["run_dir"]) / controller.CALLS_FILENAME).exists())
        self.assertEqual(Path(run["run_dir"]).parent.name, "controlled_dry_runs")

    def test_missing_key(self):
        with self.assertRaises(llm.MissingAPIKeyError):
            controller.run_controlled(self.config, 0, "A", index=self.index, model=self.model)

    def test_logs_complete_and_secret_free(self):
        os.environ["OPENAI_API_KEY"] = FAKE_SECRET
        run, _ = self.run_branch("D", [self.typed("PARTIAL", "retry"), self.rewrite(), self.typed("OK", "answer", [self.ids[3]]), self.answer(ids=[self.ids[3]])])
        run_dir = Path(run["run_dir"])
        calls = self.calls(run)
        self.assertEqual([c["node"] for c in calls], ["grade_typed_action", "rewrite_query", "grade_typed_action", "answer"])
        self.assertEqual([c["iteration"] for c in calls], [1, 1, 2, 2])
        for c in calls:
            self.assertEqual(c["branch"], "D")
            self.assertIn("prompt_sha256", c["hashes"])
            self.assertEqual(c["request"]["text"]["format"]["strict"], True)
        raw = sorted(p.relative_to(run_dir).as_posix() for p in (run_dir / "raw").rglob("*.json"))
        self.assertEqual(len(raw), 4)
        for path in run_dir.rglob("*"):
            if path.is_file():
                self.assertNotIn(FAKE_SECRET, path.read_text(encoding="utf-8"))
        steps = run["trajectory"]
        for key in ("iteration", "context_sha256", "assessment", "proposed_action", "expected_action", "executed_action", "policy_mismatch", "policy_override", "retries_used_before", "retries_remaining_before"):
            self.assertIn(key, steps[0])
        self.assertEqual(steps[0]["retries_remaining_before"], 1)
        self.assertEqual(steps[1]["retries_used_before"], 1)
        self.assertEqual(run["policy_version"], "test-v1")
        self.assertEqual(run["usage_totals"]["total_tokens"], 60)
        self.assertFalse((self.config.processed_dir / hotpotqa.ANNOTATIONS_FILENAME).exists())

    def test_stage4_run_still_works(self):
        transport = FakeTransport([
            completed({"sufficient": True, "evidence_doc_ids": [self.ids[1]], "reason": "r"}),
            self.answer(),
        ])
        run = rag_run.run_example(self.config, 0, transport=transport, index=self.index, model=self.model)
        self.assertEqual(run["status"], rag_run.RUN_COMPLETED)
        self.assertEqual(run["mode"], "stage4_diagnostic")


if __name__ == "__main__":
    unittest.main()
