"""Unit tests for stage 7: matched subset, frozen plan, budgeted batch runner, summary.

Everything runs on the synthetic stage 6 fixture with a fake transport: no
model, no network, no API key. Mock batches are written under the mock
directory of a temporary project and are never real results.

Run with:  python -m unittest discover -s tests
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from test_fault_cases import FaultProject, completed

from typed_rag import controller, fault_cases, hotpotqa, llm, nodes, pilot, rag_run


class RuleTransport:
    """Answers every request by node; `rule(node, request)` returns a result or raises."""

    def __init__(self, rule):
        self.rule = rule
        self.requests: list[dict] = []

    def send(self, request: dict) -> llm.TransportResult:
        self.requests.append(request)
        node = {
            "context_grade_binary_action": "binary",
            "context_grade_typed_action": "typed",
            "query_rewrite": "rewrite",
            "grounded_answer": "answer",
        }[request["text"]["format"]["name"]]
        outcome = self.rule(node, request)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def grade(node: str, verdict, action: str, ids=None) -> llm.TransportResult:
    key = "sufficient" if node == "binary" else "state"
    return completed({key: verdict, "proposed_action": action, "evidence_doc_ids": ids or [], "reason": "r"})


def answer_ok(node: str, request: dict) -> llm.TransportResult:
    """Straight-through rule: everything sufficient/OK, answer immediately."""
    if node == "binary":
        return grade(node, True, "answer")
    if node == "typed":
        return grade(node, "OK", "answer")
    if node == "rewrite":
        return completed({"rewritten_query": "q2", "reason": "r"})
    return completed({"decision": "answer", "answer": "Beta Ltd", "evidence_doc_ids": [], "reason": "r"})


def retry_then_answer(node: str, request: dict) -> llm.TransportResult:
    """PARTIAL/insufficient on the first grade, OK after the retry; four calls per run."""
    used = "1 retry used" in request["input"][0]["content"][0]["text"]
    if node == "binary":
        return grade(node, used, "answer" if used else "retry")
    if node == "typed":
        return grade(node, "OK" if used else "PARTIAL", "answer" if used else "retry")
    return answer_ok(node, request)


class PilotProject(FaultProject):
    def setUp(self):
        super().setUp()
        self.prepare()
        self.approve_all(self.q1["question_id"])
        # Silence the stdout-free but slow parts: no model is loaded anywhere here.
        self.assertFalse(os.environ.get("OPENAI_API_KEY"))

    def reviews(self) -> list[dict]:
        return fault_cases.load_fault_reviews(self.config)

    def write_reviews(self, rows: list[dict]) -> None:
        hotpotqa.write_jsonl(fault_cases.fault_cases_dir(self.config) / fault_cases.REVIEWS_FILENAME, rows)

    def approve_all(self, qid: str) -> None:
        annotations = {a["case_id"]: a for a in fault_cases.load_fault_annotations(self.config)}
        rows = self.reviews()
        for row in rows:
            if annotations[row["case_id"]]["question_id"] == qid:
                row.update({"review_status": "approved", "observed_state": annotations[row["case_id"]]["expected_state"], "reviewer": "r1", "note": "matches"})
        self.write_reviews(rows)

    def set_review(self, condition: str, **fields) -> None:
        case_id = self.annotation(condition)["case_id"]
        rows = self.reviews()
        for row in rows:
            if row["case_id"] == case_id:
                row.update(fields)
        self.write_reviews(rows)

    def plan(self) -> tuple[dict, list[dict]]:
        manifest, runs = pilot.build_plan(self.config)
        pilot.write_plan(self.config, manifest, runs)
        return manifest, runs

    def batch(self, transport, max_api_calls: int, **kwargs) -> dict:
        return pilot.run_batch(
            self.config, max_api_calls, transport=transport, index=self.index, model=self.model,
            execution_kind=pilot.EXECUTION_MOCK, **kwargs,
        )

    def run_json(self, batch_dir: Path, run_id: str) -> dict:
        return hotpotqa.read_json(batch_dir / pilot.RUNS_DIRNAME / run_id / controller.RUN_FILENAME)


class SelectionTests(PilotProject):
    def test_matched_question_included_and_ineligible_excluded(self):
        selection = pilot.select_matched_questions(self.config)
        self.assertTrue(selection["valid"], selection["problems"])
        self.assertEqual([q["question_id"] for q in selection["included"]], [self.q1["question_id"]])
        included = selection["included"][0]
        self.assertEqual(set(included["cases"]), set(fault_cases.CONDITIONS))
        self.assertEqual(included["cases"]["CLEAN"]["observed_state"], "OK")
        excluded = {e["question_id"]: e for e in selection["excluded"]}
        self.assertIn(self.q2["question_id"], excluded)
        self.assertEqual(excluded[self.q2["question_id"]]["stage"], "eligibility")
        self.assertIn("gold supporting documents", excluded[self.q2["question_id"]]["reason"])
        self.assertEqual(selection["review_counts"], {"pending": 0, "approved": 4, "rejected": 0})
        self.assertEqual(selection["built_cases"], 4)  # q2 is ineligible, so only q1 has cases

    def test_rejected_partial_annotated_ok_excludes_question_without_relabelling(self):
        self.set_review("PARTIAL", review_status="rejected", observed_state="OK", note="fact recoverable")
        selection = pilot.select_matched_questions(self.config)
        self.assertTrue(selection["valid"], selection["problems"])
        self.assertEqual(selection["included"], [])
        excluded = next(e for e in selection["excluded"] if e["question_id"] == self.q1["question_id"])
        self.assertEqual(excluded["stage"], "semantic_review")
        self.assertIn("PARTIAL rejected (observed_state=OK)", excluded["reason"])
        # The source rows are untouched: still rejected, still OK, still three approved.
        rows = {r["case_id"]: r for r in self.reviews()}
        partial = rows[self.annotation("PARTIAL")["case_id"]]
        self.assertEqual((partial["review_status"], partial["observed_state"]), ("rejected", "OK"))
        with self.assertRaises(pilot.PilotError):
            pilot.build_plan(self.config)

    def test_review_file_problems_are_reported_not_forced(self):
        self.set_review("EMPTY", review_status="approved", observed_state="PARTIAL")
        selection = pilot.select_matched_questions(self.config)
        self.assertFalse(selection["valid"])
        self.assertTrue(any("intended state" in p for p in selection["problems"]))

        self.approve_all(self.q1["question_id"])
        self.set_review("CLEAN", note="")
        self.assertTrue(any("empty justification" in p for p in pilot.select_matched_questions(self.config)["problems"]))

        self.approve_all(self.q1["question_id"])
        rows = self.reviews()
        self.write_reviews(rows + [dict(rows[0])])
        self.assertTrue(any("duplicate" in p for p in pilot.select_matched_questions(self.config)["problems"]))
        self.write_reviews(rows + [{"case_id": "0" * 16, "review_status": "approved", "observed_state": "OK", "reviewer": "r", "note": "n"}])
        self.assertTrue(any("unknown" in p for p in pilot.select_matched_questions(self.config)["problems"]))
        self.write_reviews(rows)
        with mock.patch.object(pilot, "select_matched_questions", return_value={"valid": False, "problems": ["x"], "included": []}):
            with self.assertRaises(pilot.PilotError):
                pilot.build_plan(self.config)


class PlanTests(PilotProject):
    def test_plan_counts_identities_and_deterministic_order(self):
        manifest, runs = self.plan()
        design = manifest["binding"]["design"]
        expected = 1 * 4 * len(design["branches"]) * design["repeats"]
        self.assertEqual(manifest["counts"]["pipeline_runs"], expected)
        self.assertEqual(len(runs), expected)
        self.assertEqual(len({r["run_id"] for r in runs}), expected)
        self.assertEqual(manifest["call_bound"]["max_llm_calls_per_run"], 4)
        self.assertEqual(manifest["counts"]["api_call_upper_bound"], expected * 4)
        self.assertEqual(manifest["plan_id"], nodes.sha256_json(manifest["binding"]))
        again, runs_again = pilot.build_plan(self.config)
        self.assertEqual(again["plan_id"], manifest["plan_id"])
        self.assertEqual([r["run_id"] for r in runs_again], [r["run_id"] for r in runs])
        self.assertEqual([r["schedule_position"] for r in runs], list(range(expected)))
        branches_in_order = [r["branch"] for r in runs]
        self.assertNotEqual(branches_in_order, sorted(branches_in_order))  # not one branch first throughout
        # Every run of a case carries the same context hash and every case is bound by content.
        for run in runs:
            case = manifest["binding"]["questions"][0]["cases"][run["condition"]]
            self.assertEqual(run["case_id"], case["case_id"])
            self.assertEqual(run["context_sha256"], case["context_sha256"])
            self.assertEqual(case["context_sha256"], pilot.case_content_hash(fault_cases.find_context(self.config, run["case_id"])))
        self.assertIn("does not depend on the context content", manifest["case_id_note"])
        self.assertEqual(manifest["binding"]["llm"]["model"], "test-model")
        self.assertEqual(manifest["binding"]["controller"]["policy_version"], "test-v1")
        for node in (nodes.NODE_GRADE_BINARY_ACTION, nodes.NODE_GRADE_TYPED_ACTION, nodes.NODE_REWRITE, nodes.NODE_ANSWER):
            self.assertEqual(manifest["binding"]["prompts"][node]["schema_sha256"], nodes.sha256_json(nodes.json_schema(node)))

    def test_case_id_is_independent_of_content_so_content_hash_is_verified(self):
        case_id = self.annotation("CLEAN")["case_id"]
        self.assertEqual(case_id, fault_cases.case_id_for(self.q1["question_id"], "CLEAN", self.config.seed))
        self.plan()
        path = fault_cases.fault_cases_dir(self.config) / fault_cases.CONTEXTS_FILENAME
        rows = hotpotqa.read_jsonl(path)
        for row in rows:
            if row["case_id"] == case_id:
                row["documents"][0], row["documents"][1] = row["documents"][1], row["documents"][0]  # order only
        hotpotqa.write_jsonl(path, rows)
        manifest, _ = pilot.load_plan(self.config)
        changed = pilot.verify_plan(self.config, manifest)
        self.assertTrue(any(f"case {case_id}" in c and "document order" in c for c in changed), changed)
        with self.assertRaises(pilot.StalePlanError):
            self.batch(RuleTransport(answer_ok), 10)
        with self.assertRaises(pilot.StalePlanError):
            pilot.dry_run_batch(self.config)

    def test_changed_prompt_or_review_refuses_execution_and_replan_needs_explicit_flag(self):
        manifest, runs = self.plan()
        prompt = nodes.prompt_path(self.config, nodes.NODE_ANSWER)
        prompt.write_text(prompt.read_text(encoding="utf-8") + "\nBe brief.", encoding="utf-8")
        with self.assertRaises(pilot.StalePlanError) as ctx:
            self.batch(RuleTransport(answer_ok), 10)
        self.assertIn(f"prompts.{nodes.NODE_ANSWER}.prompt_sha256", str(ctx.exception))
        new_manifest, new_runs = pilot.build_plan(self.config)
        self.assertNotEqual(new_manifest["plan_id"], manifest["plan_id"])
        with self.assertRaises(pilot.PilotError):
            pilot.write_plan(self.config, new_manifest, new_runs)
        self.assertEqual(pilot.load_plan(self.config)[0]["plan_id"], manifest["plan_id"])
        written = pilot.write_plan(self.config, new_manifest, new_runs, replace=True)
        self.assertEqual(written["outcome"], "replaced")
        self.set_review("CLEAN", note="changed wording")
        with self.assertRaises(pilot.StalePlanError) as ctx:
            pilot.require_current_plan(self.config)
        self.assertIn("sources.reviews_sha256", str(ctx.exception))

    def test_edited_manifest_is_rejected(self):
        self.plan()
        path = pilot.plan_paths(self.config)[0]
        manifest = hotpotqa.read_json(path)
        manifest["binding"]["design"]["repeats"] = 1
        hotpotqa.write_json(path, manifest)
        with self.assertRaises(pilot.StalePlanError):
            pilot.load_plan(self.config)


class DryRunTests(PilotProject):
    def test_dry_run_makes_no_call_and_needs_no_key(self):
        manifest, runs = self.plan()
        with mock.patch.object(rag_run, "default_transport", side_effect=AssertionError("client must not be created")), \
                mock.patch.object(llm, "create_client", side_effect=AssertionError("client must not be created")), \
                mock.patch.object(controller, "run_controlled", side_effect=AssertionError("no run in a dry run")):
            report = pilot.dry_run_batch(self.config)
        self.assertEqual(report["api_calls"], 0)
        self.assertFalse(report["api_key_required"])
        self.assertTrue(report["checks"]["all_passed"], report["checks"])
        self.assertEqual(report["pipeline_runs"], len(runs))
        self.assertEqual(report["api_call_upper_bound"], manifest["counts"]["api_call_upper_bound"])
        self.assertEqual(set(report["representative_requests"]), set(self.config.pilot.branches))
        for branch, rep in report["representative_requests"].items():
            request = rep["first_grader_request"]
            self.assertEqual(request["model"], "test-model")
            self.assertEqual(request["text"]["format"]["name"], nodes.NODE_SPECS[controller.get_branch(branch).grader_node].schema_name)
            self.assertIn(self.q1["question"], request["input"][0]["content"][0]["text"])
        saved = hotpotqa.read_json(Path(report["out_dir"]) / pilot.DRY_RUN_FILENAME)
        self.assertNotIn("first_grader_request", json.dumps(saved["representative_runs"]))
        self.assertFalse(list(self.config.pilot_runs_dir.glob("*")) if self.config.pilot_runs_dir.exists() else [])

    def test_isolation_check_catches_leaks(self):
        self.plan()
        context = fault_cases.find_context(self.config, self.annotation("PARTIAL")["case_id"])
        annotation = self.annotation("PARTIAL")
        review = fault_cases.review_status(self.config, context["case_id"])
        request = controller.first_grader_request(self.config, controller.get_branch("D"), context["question"], context["documents"])
        self.assertEqual(pilot.check_request_isolation(self.config, request, context, annotation, review, "Beta Ltd"), [])
        leaked = json.loads(json.dumps(request))
        leaked["input"][0]["content"][0]["text"] += f"\nexpected_state: PARTIAL; case_id={context['case_id']}; answer: Beta Ltd"
        problems = pilot.check_request_isolation(self.config, leaked, context, annotation, review, "Beta Ltd")
        self.assertTrue(any("case_id" in p for p in problems))
        self.assertTrue(any("condition label" in p for p in problems))
        self.assertTrue(any("gold answer" in p for p in problems))
        self.assertTrue(any("expected_state" in p for p in problems))


class BatchTests(PilotProject):
    def test_identical_initial_contexts_and_fresh_state_per_run(self):
        manifest, runs = self.plan()
        transport = RuleTransport(retry_then_answer)
        result = self.batch(transport, 10_000)
        self.assertEqual(result["executed_now"], len(runs))
        self.assertEqual(result["executed_status_counts"], {"completed": len(runs)})
        self.assertEqual(result["execution_kind"], pilot.EXECUTION_MOCK)
        self.assertTrue(str(result["batch_dir"]).startswith(str(self.config.pilot_mock_runs_dir)))
        by_case: dict[str, set] = {}
        for run in runs:
            saved = self.run_json(result["batch_dir"], run["run_id"])
            self.assertEqual(saved["mode"], pilot.MODE)
            self.assertEqual(saved["run_id"], run["run_id"])
            self.assertEqual(saved["pilot"]["plan_id"], manifest["plan_id"])
            self.assertEqual(saved["pilot"]["repeat"], run["repeat"])
            context = hotpotqa.read_json(result["batch_dir"] / pilot.RUNS_DIRNAME / run["run_id"] / controller.CONTEXT_FILENAME)
            by_case.setdefault(run["case_id"], set()).add(context["contexts"][0]["context_sha256"])
            self.assertEqual(context["contexts"][0]["query_kind"], "injected_initial")
            # fresh controller state: every run begins with zero retries and its own call numbering
            self.assertEqual(saved["trajectory"][0]["retries_used_before"], 0)
            self.assertEqual(saved["trajectory"][0]["grader_call_index"], 1)
            self.assertEqual(saved["retries_used"], 1)
            self.assertEqual(saved["api_calls"], 4)
            self.assertEqual(saved["searches"], 1)  # one real search after the retry, none before
            self.assertEqual(context["contexts"][1]["query_kind"], "rewritten")
        self.assertTrue(all(len(hashes) == 1 for hashes in by_case.values()))
        self.assertEqual(len(transport.requests), 4 * len(runs))
        # No response reuse: every run issued its own four requests.
        ledger = hotpotqa.read_json(result["batch_dir"] / pilot.BUDGET_FILENAME)
        self.assertEqual(ledger["attempts_total"], 4 * len(runs))
        summary = pilot.summarise_batch(self.config, result["batch_dir"])
        self.assertEqual(summary["status_counts"]["completed"], len(runs))
        self.assertEqual(summary["api"]["calls_logged_in_runs"], 4 * len(runs))
        self.assertEqual(summary["post_retry"]["runs_with_retry_search"], len(runs))
        # The first-evaluation confusion uses the first step only; the post-retry OK never enters it.
        typed = summary["first_evaluation_confusion"]["typed"]
        self.assertEqual(set(typed), {"OK", "PARTIAL", "EMPTY", "INCONSISTENT"})
        for reviewed, predicted in typed.items():
            self.assertEqual(set(predicted), {"PARTIAL"}, (reviewed, predicted))
        self.assertIn("UNREVIEWED", summary["post_retry"]["note"])

    def test_real_execution_requires_budget_and_zero_budget_never_calls(self):
        self.plan()
        with self.assertRaises(pilot.PilotError):
            pilot.run_batch(self.config, None, transport=RuleTransport(answer_ok), index=self.index, model=self.model, execution_kind=pilot.EXECUTION_MOCK)
        transport = RuleTransport(answer_ok)
        with mock.patch.object(rag_run, "default_transport", side_effect=AssertionError("client must not be created")):
            result = self.batch(transport, 0, max_runs=3)
        self.assertEqual(transport.requests, [])
        self.assertEqual(result["executed_now"], 0)  # the loop halts before the first run starts
        self.assertIn("exhausted before run", result["stopped_reason"])
        self.assertEqual(pilot.read_checkpoint(result["batch_dir"] / pilot.CHECKPOINT_FILENAME)["finished"], {})
        self.assertEqual(hotpotqa.read_json(result["batch_dir"] / pilot.BUDGET_FILENAME)["attempts_total"], 0)
        # A zero budget through the BudgetedTransport itself: the stop is a distinct, non-abstention status.
        stopped = pilot.BudgetedTransport(None, 0, result["batch_dir"] / "probe.json")
        record = llm.call(stopped, {"model": "m"})
        self.assertEqual(record["transport_status"], llm.API_BUDGET_STOP)
        self.assertIsNone(record["response"])

    def test_budget_counts_failed_attempts_and_stops_mid_trajectory(self):
        self.plan()
        calls = {"n": 0}

        def flaky(node, request):
            calls["n"] += 1
            if calls["n"] == 1:
                return RuntimeError("boom")  # a failed attempt still consumes budget
            return retry_then_answer(node, request)

        transport = RuleTransport(flaky)
        result = self.batch(transport, 6, max_runs=3)
        ledger = hotpotqa.read_json(result["batch_dir"] / pilot.BUDGET_FILENAME)
        self.assertEqual(ledger["attempts_total"], 6)
        self.assertEqual(len(transport.requests), 6)
        statuses = [
            self.run_json(result["batch_dir"], run_id)
            for run_id in pilot.read_checkpoint(result["batch_dir"] / pilot.CHECKPOINT_FILENAME)["finished"]
        ]
        by_status = sorted((s["status"], s["final_outcome"], s["api_calls"]) for s in statuses)
        # run 1: technical failure after 1 failed attempt (counted); run 2: 4 attempts, completed;
        # run 3: 1 attempt sent, then the budget stops the rewrite call (the stop itself is not an attempt)
        self.assertEqual(
            by_status,
            sorted([
                (controller.RUN_TECHNICAL_FAILURE, controller.OUTCOME_TECHNICAL_FAILURE, 1),
                (controller.RUN_COMPLETED, controller.OUTCOME_ANSWERED, 4),
                (controller.RUN_API_BUDGET_STOPPED, controller.OUTCOME_API_BUDGET_STOPPED, 2),
            ]),
        )
        stopped = next(s for s in statuses if s["status"] == controller.RUN_API_BUDGET_STOPPED)
        self.assertEqual(stopped["failure"]["stage"], "rewrite")
        self.assertEqual(stopped["pilot"]["api_attempts"], 1)
        summary = pilot.summarise_batch(self.config, result["batch_dir"])
        self.assertEqual(summary["status_counts"]["failed"], 1)
        self.assertEqual(summary["status_counts"]["api_budget_stopped"], 1)
        self.assertEqual(summary["status_counts"]["completed"], 1)
        self.assertEqual(summary["api"]["attempts_recorded_by_budget_ledger"], 6)

    def test_mid_trajectory_budget_stop_is_not_abstention(self):
        self.plan()
        transport = RuleTransport(retry_then_answer)
        result = self.batch(transport, 3, max_runs=1)  # grade, rewrite, grade sent; the answer call is stopped
        run_id = next(iter(pilot.read_checkpoint(result["batch_dir"] / pilot.CHECKPOINT_FILENAME)["finished"]))
        saved = self.run_json(result["batch_dir"], run_id)
        self.assertEqual(saved["status"], controller.RUN_API_BUDGET_STOPPED)
        self.assertEqual(saved["failure"]["stage"], "generator")
        self.assertEqual(saved["executed_actions"], ["retry", "answer"])
        self.assertEqual(saved["generator"]["status"], llm.API_BUDGET_STOP)
        self.assertEqual(len(transport.requests), 3)

    def test_checkpoint_resume_skips_finished_failed_and_interrupted(self):
        _, runs = self.plan()
        first = RuleTransport(answer_ok)
        result = self.batch(first, 1000, max_runs=2)
        self.assertEqual(result["executed_now"], 2)
        with self.assertRaises(pilot.PilotError):
            self.batch(RuleTransport(answer_ok), 1000)  # started batch needs --resume
        # A failed run and an interrupted run appear in the checkpoint.
        broken = RuleTransport(lambda node, request: RuntimeError("down"))
        result = self.batch(broken, 1000, resume=True, max_runs=1)
        self.assertEqual(result["executed_status_counts"], {"failed": 1})
        failed_id = result["executed_now"] and list(pilot.read_checkpoint(result["batch_dir"] / pilot.CHECKPOINT_FILENAME)["finished"])[-1]
        interrupted_id = runs[3]["run_id"]
        rag_run._append_jsonl(result["batch_dir"] / pilot.CHECKPOINT_FILENAME, {"event": "started", "run_id": interrupted_id, "at_utc": "x"})
        second = RuleTransport(answer_ok)
        result = self.batch(second, 1000, resume=True)
        executed = set(pilot.read_checkpoint(result["batch_dir"] / pilot.CHECKPOINT_FILENAME)["finished"])
        self.assertEqual(result["executed_now"], len(runs) - 4)
        self.assertNotIn(interrupted_id, executed)
        self.assertIn(failed_id, executed)  # finished (failed) earlier, not executed again
        self.assertEqual(len(second.requests), 2 * (len(runs) - 4))  # binary/typed grade + answer per run
        self.assertEqual(result["interrupted_total"], 1)
        self.assertEqual(result["remaining"], 0)
        summary = pilot.summarise_batch(self.config, result["batch_dir"])
        self.assertEqual(summary["status_counts"]["interrupted"], 1)
        self.assertEqual(summary["status_counts"]["failed"], 1)
        self.assertEqual(summary["status_counts"]["completed"], len(runs) - 2)
        self.assertEqual(summary["status_counts"]["pending"], 0)
        self.assertTrue(any(f["batch_status"] == "interrupted" for f in summary["non_completed_runs"]))
        # A third resume executes nothing: failed and interrupted runs are never repeated silently.
        third = RuleTransport(answer_ok)
        result = self.batch(third, 1000, resume=True)
        self.assertEqual(result["executed_now"], 0)
        self.assertEqual(third.requests, [])
        batch = hotpotqa.read_json(result["batch_dir"] / pilot.BATCH_FILENAME)
        self.assertEqual(len(batch["invocations"]), 4)
        self.assertEqual(batch["execution_kind"], pilot.EXECUTION_MOCK)

    def test_technical_failure_is_separate_from_semantic_outcomes(self):
        self.plan()
        transport = RuleTransport(lambda node, request: RuntimeError("provider down"))
        result = self.batch(transport, 100, max_runs=4)
        summary = pilot.summarise_batch(self.config, result["batch_dir"])
        self.assertEqual(summary["status_counts"]["failed"], 4)
        outcomes = {o for by_c in summary["outcomes_by_branch_and_condition"].values() for c in by_c.values() for o in c}
        self.assertEqual(outcomes, {controller.OUTCOME_TECHNICAL_FAILURE})
        self.assertEqual(summary["first_evaluation_confusion"]["typed"], {})
        self.assertEqual(summary["first_evaluation_confusion"]["binary"], {})
        self.assertEqual(summary["policy"]["steps_total"], 0)

    def test_summary_refuses_batch_of_another_plan(self):
        self.plan()
        result = self.batch(RuleTransport(answer_ok), 100, max_runs=1)
        batch_path = result["batch_dir"] / pilot.BATCH_FILENAME
        batch = hotpotqa.read_json(batch_path)
        batch["plan_id"] = "0" * 64
        hotpotqa.write_json(batch_path, batch)
        with self.assertRaises(pilot.PilotError):
            pilot.summarise_batch(self.config, result["batch_dir"])


class CallBoundTests(PilotProject):
    def test_max_calls_per_run_matches_the_control_flow(self):
        """Enumerate first/second grader outputs for every branch; the longest run has four calls."""
        bound = pilot.max_llm_calls_per_run(self.config.controller.max_search_retries)
        self.assertEqual(bound["max_llm_calls_per_run"], 4)
        self.assertEqual(bound["longest_trajectory"], "grade[1] -> rewrite[1] -> grade[2] -> answer")
        context = fault_cases.find_context(self.config, self.annotation("CLEAN")["case_id"])
        observed = 0
        verdicts = {"binary": [True, False], "typed": list(nodes.STATES)}
        for branch in "ABCD":
            grader = controller.get_branch(branch).grader
            for first in verdicts[grader]:
                for first_action in nodes.ACTIONS:
                    for second_action in nodes.ACTIONS:
                        def rule(node, request, first=first, fa=first_action, sa=second_action):
                            used = "1 retry used" in request["input"][0]["content"][0]["text"]
                            if node in ("binary", "typed"):
                                return grade(node, first, sa if used else fa)
                            return answer_ok(node, request)
                        run = controller.run_controlled(
                            self.config, 0, branch, transport=RuleTransport(rule), index=self.index, model=self.model,
                            initial_context=context,
                        )
                        observed = max(observed, run["api_calls"])
                        self.assertLessEqual(run["api_calls"], bound["max_llm_calls_per_run"])
        self.assertEqual(observed, bound["max_llm_calls_per_run"])


class ExplicitBatchDirTests(PilotProject):
    """Stage 8 repair: an explicit destination, an output-path preflight and error finalization."""

    def alt(self, name: str = "b") -> Path:
        return Path(self.tmp) / "alt" / name

    def test_execution_and_resume_use_the_explicit_directory_only(self):
        _, runs = self.plan()
        alt = self.alt()
        result = self.batch(RuleTransport(answer_ok), 1000, max_runs=2, batch_dir=alt)
        self.assertEqual(result["batch_dir"], alt.resolve())
        self.assertEqual(result["executed_now"], 2)
        for name in (pilot.BATCH_FILENAME, pilot.CHECKPOINT_FILENAME, pilot.BUDGET_FILENAME):
            self.assertTrue((alt / name).is_file(), name)
        # The configured default is never touched when an explicit directory is given.
        default = pilot.batch_dir_for(self.config, result["plan_id"], pilot.EXECUTION_MOCK)
        self.assertFalse(default.exists())
        # The raw-response writer really works there: a run directory holds a parsed response.
        run_dir = alt / pilot.RUNS_DIRNAME / runs[0]["run_id"]
        raw = sorted((run_dir / rag_run.RAW_DIRNAME).glob("*/*_response.json"))
        self.assertTrue(raw)
        self.assertIn("raw_response", json.loads(raw[0].read_text(encoding="utf-8")))
        self.assertTrue((run_dir / controller.RUN_FILENAME).is_file())
        # Resume continues in the same directory and repeats nothing.
        again = self.batch(RuleTransport(answer_ok), 1000, resume=True, batch_dir=alt)
        self.assertEqual(again["executed_now"], len(runs) - 2)
        self.assertEqual(again["remaining"], 0)
        self.assertFalse(default.exists())
        summary = pilot.summarise_batch(self.config, alt)
        self.assertEqual(summary["status_counts"]["completed"], len(runs))

    def test_directory_of_another_plan_or_foreign_content_is_refused(self):
        self.plan()
        alt = self.alt("foreign")
        alt.mkdir(parents=True)
        hotpotqa.write_json(alt / pilot.BATCH_FILENAME, {"plan_id": "0" * 64, "execution_kind": pilot.EXECUTION_MOCK})
        with self.assertRaises(pilot.PilotError):
            self.batch(RuleTransport(answer_ok), 10, batch_dir=alt)
        other = self.alt("occupied")
        other.mkdir(parents=True)
        (other / "unrelated.txt").write_text("not a batch", encoding="utf-8")
        with self.assertRaises(pilot.PilotError):
            self.batch(RuleTransport(answer_ok), 10, batch_dir=other)
        # A real batch is never reused by a mock execution, and the reverse.
        real = self.alt("kind")
        real.mkdir(parents=True)
        hotpotqa.write_json(real / pilot.BATCH_FILENAME, {"plan_id": pilot.load_plan(self.config)[0]["plan_id"], "execution_kind": pilot.EXECUTION_REAL})
        with self.assertRaises(pilot.PilotError):
            self.batch(RuleTransport(answer_ok), 10, batch_dir=real)

    def test_unusable_output_paths_fail_before_any_provider_call(self):
        self.plan()
        alt = self.alt()
        transport = RuleTransport(answer_ok)
        with mock.patch.object(pilot, "MAX_OUTPUT_PATH", 40):
            with self.assertRaises(pilot.OutputPathError) as raised:
                self.batch(transport, 1000, batch_dir=alt)
        self.assertIn("--batch-dir", str(raised.exception))
        self.assertEqual(transport.requests, [])  # nothing was sent
        self.assertFalse((alt / pilot.BUDGET_FILENAME).exists())  # no budget was opened
        self.assertEqual(pilot.read_checkpoint(alt / pilot.CHECKPOINT_FILENAME)["finished"], {})

    def test_path_probe_is_synthetic_and_leaves_no_run_record(self):
        self.plan()
        alt = self.alt()
        alt.mkdir(parents=True)
        report = pilot.check_output_paths(alt, ["A_q00_case_r1_abcdef123456"])
        self.assertTrue(report["ok"])
        self.assertTrue(report["probe"]["write_ok"])
        self.assertTrue(report["probe"]["read_back_ok"])
        self.assertTrue(report["probe"]["cleaned_up"])
        self.assertEqual(report["probe"]["probe_path_length"], report["longest_path_length"])
        self.assertFalse((alt / pilot.PROBE_DIRNAME).exists())
        self.assertFalse((alt / pilot.RUNS_DIRNAME).exists())

    def test_write_failure_after_a_response_keeps_the_attempt_and_finalizes_the_invocation(self):
        _, runs = self.plan()
        alt = self.alt()
        original_write = rag_run._write_json

        def fail_on_raw(path, payload):
            # Only inside a real run directory: the offline path probe must still work.
            if pilot.RUNS_DIRNAME in Path(path).parts and str(path).endswith("_response.json"):
                raise OSError(2, "No such file or directory")
            return original_write(path, payload)

        transport = RuleTransport(answer_ok)
        with mock.patch.object(rag_run, "_write_json", side_effect=fail_on_raw):
            with self.assertRaises(pilot.BatchExecutionError) as raised:
                self.batch(transport, 1000, batch_dir=alt)
        error = raised.exception
        self.assertIsInstance(error.original, OSError)
        self.assertIs(error.__cause__, error.original)  # the original failure is not masked
        self.assertIsNone(error.finalization_error)
        self.assertEqual(len(transport.requests), 1)  # stopped; no further provider call
        budget = hotpotqa.read_json(alt / pilot.BUDGET_FILENAME)
        self.assertEqual(budget["attempts_total"], 1)  # the spent attempt is preserved
        invocation = hotpotqa.read_json(alt / pilot.BATCH_FILENAME)["invocations"][-1]
        self.assertIn("execution error", invocation["stopped_reason"])
        self.assertTrue(invocation["finished_at_utc"])
        self.assertEqual(invocation["api_attempts_this_invocation"], 1)
        self.assertEqual(invocation["execution_error"]["type"], "FileNotFoundError")
        # The started run stays interrupted; it is neither completed nor an abstention.
        checkpoint = pilot.read_checkpoint(alt / pilot.CHECKPOINT_FILENAME)
        self.assertEqual(list(checkpoint["interrupted"]), [runs[0]["run_id"]])
        self.assertEqual(checkpoint["finished"], {})
        # A resume does not repeat it.
        second = RuleTransport(answer_ok)
        result = self.batch(second, 1000, resume=True, max_runs=1, batch_dir=alt)
        self.assertNotIn(runs[0]["run_id"], result["executed_status_counts"])
        self.assertNotIn(runs[0]["run_id"], [r for r in pilot.read_checkpoint(alt / pilot.CHECKPOINT_FILENAME)["finished"]])

    def test_failed_finalization_reports_both_errors_without_masking_the_original(self):
        self.plan()
        alt = self.alt()
        original_write = rag_run._write_json

        # The batch file must exist before the run loop, so only fail it during finalization.
        state = {"runs_started": False}

        def guarded(path, payload):
            if pilot.RUNS_DIRNAME in Path(path).parts and str(path).endswith("_response.json"):
                state["runs_started"] = True
                raise OSError(2, "No such file or directory")
            if state["runs_started"] and str(path).endswith(pilot.BATCH_FILENAME):
                raise OSError(28, "storage unavailable")
            return original_write(path, payload)

        with mock.patch.object(rag_run, "_write_json", side_effect=guarded):
            with self.assertRaises(pilot.BatchExecutionError) as raised:
                self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt)
        error = raised.exception
        self.assertIsInstance(error.original, OSError)
        self.assertIsInstance(error.finalization_error, OSError)
        self.assertIs(error.__cause__, error.original)
        self.assertIn("No such file or directory", str(error))
        self.assertIn("could not be written", str(error))
        self.assertEqual(hotpotqa.read_json(alt / pilot.BUDGET_FILENAME)["attempts_total"], 1)


class ContinuationScopeTests(PilotProject):
    """Stage 8 repair: an explicit, ordered subset of the plan that a resume cannot widen."""

    def scope_file(self, run_ids: list[str], plan_id: str, name: str = "scope.json") -> Path:
        path = Path(self.tmp) / name
        hotpotqa.write_json(path, {"plan_id": plan_id, "label": "continuation", "run_ids": run_ids})
        return path

    def test_scope_excludes_out_of_scope_runs_and_keeps_its_order(self):
        manifest, runs = self.plan()
        alt = Path(self.tmp) / "alt" / "s"
        chosen = [runs[3]["run_id"], runs[1]["run_id"], runs[2]["run_id"]]  # deliberately not plan order
        scope = pilot.load_scope(self.scope_file(chosen, manifest["plan_id"]), manifest["plan_id"], runs)
        result = self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, scope=scope)
        self.assertEqual(result["executed_now"], 3)
        self.assertEqual(result["remaining"], 0)  # the scope is finished, not the whole plan
        self.assertEqual(result["scoped_runs"], 3)
        executed = [r["run_id"] for r in hotpotqa.read_jsonl(alt / pilot.CHECKPOINT_FILENAME) if r["event"] == "finished"]
        self.assertEqual(executed, chosen)  # the recorded continuation order, not the plan order
        self.assertNotIn(runs[0]["run_id"], executed)  # the excluded coordinate never runs
        self.assertEqual(hotpotqa.read_json(alt / pilot.BATCH_FILENAME)["scope"]["scope_id"], scope["scope_id"])

    def test_max_runs_applies_inside_the_scope_and_never_backfills(self):
        manifest, runs = self.plan()
        alt = Path(self.tmp) / "alt" / "s2"
        chosen = [runs[2]["run_id"], runs[4]["run_id"]]
        scope = pilot.load_scope(self.scope_file(chosen, manifest["plan_id"]), manifest["plan_id"], runs)
        result = self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, scope=scope, max_runs=5)
        self.assertEqual(result["executed_now"], 2)  # max_runs cannot pull in runs outside the scope
        self.assertEqual(result["remaining"], 0)

    def test_resume_cannot_broaden_drop_or_reorder_the_scope(self):
        manifest, runs = self.plan()
        plan_id = manifest["plan_id"]
        alt = Path(self.tmp) / "alt" / "s3"
        chosen = [runs[1]["run_id"], runs[2]["run_id"], runs[3]["run_id"]]
        scope = pilot.load_scope(self.scope_file(chosen, plan_id), plan_id, runs)
        self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, scope=scope, max_runs=1)
        with self.assertRaises(pilot.PilotError):  # dropping the scope would widen the batch
            self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, resume=True)
        broader = pilot.load_scope(self.scope_file(chosen + [runs[4]["run_id"]], plan_id, "wide.json"), plan_id, runs)
        with self.assertRaises(pilot.PilotError):
            self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, resume=True, scope=broader)
        reordered = pilot.load_scope(self.scope_file(list(reversed(chosen)), plan_id, "rev.json"), plan_id, runs)
        with self.assertRaises(pilot.PilotError):
            self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, resume=True, scope=reordered)
        result = self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, resume=True, scope=scope)
        self.assertEqual(result["executed_now"], 2)

    def test_scope_file_validation(self):
        manifest, runs = self.plan()
        plan_id = manifest["plan_id"]
        with self.assertRaises(pilot.PilotError):  # another plan
            pilot.load_scope(self.scope_file([runs[0]["run_id"]], "0" * 64, "other.json"), plan_id, runs)
        with self.assertRaises(pilot.PilotError):  # duplicate
            pilot.load_scope(self.scope_file([runs[0]["run_id"]] * 2, plan_id, "dup.json"), plan_id, runs)
        with self.assertRaises(pilot.PilotError):  # not a member of this plan
            pilot.load_scope(self.scope_file(["not_in_plan"], plan_id, "alien.json"), plan_id, runs)
        with self.assertRaises(pilot.PilotError):  # empty
            pilot.load_scope(self.scope_file([], plan_id, "empty.json"), plan_id, runs)
        scope = pilot.load_scope(self.scope_file([runs[1]["run_id"]], plan_id, "ok.json"), plan_id, runs)
        self.assertEqual(scope["scope_id"], pilot.scope_id(plan_id, [runs[1]["run_id"]]))

    def test_offline_scope_check_makes_no_call_and_sees_the_checkpoint(self):
        manifest, runs = self.plan()
        plan_id = manifest["plan_id"]
        alt = Path(self.tmp) / "alt" / "s4"
        chosen = [runs[1]["run_id"], runs[2]["run_id"]]
        path = self.scope_file(chosen, plan_id)
        scope = pilot.load_scope(path, plan_id, runs)
        self.batch(RuleTransport(answer_ok), 1000, batch_dir=alt, scope=scope, max_runs=1)
        report = pilot.check_scope(self.config, path, alt, execution_kind=pilot.EXECUTION_MOCK)
        self.assertEqual(report["api_calls"], 0)
        self.assertTrue(report["ok"])
        self.assertTrue(report["batch_scope_matches"])
        self.assertEqual(report["already_finished"], [chosen[0]])
        self.assertEqual(report["pending"], [chosen[1]])

    def test_budget_and_run_limits_stay_per_invocation(self):
        manifest, runs = self.plan()
        plan_id = manifest["plan_id"]
        alt = Path(self.tmp) / "alt" / "s5"
        chosen = [r["run_id"] for r in runs[1:4]]
        scope = pilot.load_scope(self.scope_file(chosen, plan_id), plan_id, runs)
        first = self.batch(RuleTransport(answer_ok), 4, batch_dir=alt, scope=scope, max_runs=1)
        self.assertEqual(first["api_attempts_this_invocation"], 2)  # grade + answer
        second = self.batch(RuleTransport(answer_ok), 4, batch_dir=alt, resume=True, scope=scope, max_runs=1)
        self.assertEqual(second["api_attempts_this_invocation"], 2)
        budget = hotpotqa.read_json(alt / pilot.BUDGET_FILENAME)
        # Each invocation gets its own allowance; the running total is recorded, not enforced.
        self.assertEqual(budget["max_api_calls_this_invocation"], 4)
        self.assertEqual(budget["attempts_this_invocation"], 2)
        self.assertEqual(budget["attempts_before_this_invocation"], 2)
        self.assertEqual(budget["attempts_total"], 4)

    def test_stale_plan_verification_still_refuses_a_scoped_batch(self):
        manifest, runs = self.plan()
        scope = pilot.load_scope(self.scope_file([runs[1]["run_id"]], manifest["plan_id"]), manifest["plan_id"], runs)
        prompt = self.config.prompts_dir / "rewrite_query.txt"
        prompt.write_text(prompt.read_text(encoding="utf-8") + "\nextra line\n", encoding="utf-8")
        with self.assertRaises(pilot.StalePlanError):
            self.batch(RuleTransport(answer_ok), 10, batch_dir=Path(self.tmp) / "alt" / "s6", scope=scope)


if __name__ == "__main__":
    unittest.main()
