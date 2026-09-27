"""Stage 14 execution driver: repeated bounded invocations until the plan is done.

Every iteration is a full invocation of the existing runner: the frozen plan is
verified, the cumulative stage 14 ledger is read, the per-invocation budget is
set to min(4 x scheduled coordinates, remaining global allowance), and the batch
runs with checkpoint and resume. The driver adds no execution logic of its own;
it only decides whether to start another invocation.

It stops immediately on a systemic problem: any exception from the runner
(authentication, quota, stale plan, persistence, accounting disagreement), an
interrupted coordinate, or too many failed runs in one invocation. An isolated,
correctly recorded technical failure does not stop it.

    python tools/stage14_execute.py [--coordinates 100] [--invocations N]

Progress is appended to results/stage14_execution_log.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import controller, hotpotqa, llm, main_study, pilot, rag_run
from typed_rag.config import load_config

import stage14_cli

LOG_FILENAME = "stage14_execution_log.jsonl"

# A failure kind that points at the environment rather than at one question: it
# would repeat on the next coordinate, so the driver stops and preserves evidence.
SYSTEMIC_FAILURE_KINDS = (
    llm.AUTHENTICATION,
    llm.RATE_LIMIT_OR_QUOTA,
    llm.MODEL_UNAVAILABLE,
    llm.PERMISSION_DENIED,
    llm.BAD_REQUEST,
    llm.API_STATUS,
    llm.UNEXPECTED,
    llm.CONNECTION,
)
# Isolated, correctly recorded technical outcomes of one trajectory. They stay
# missing and execution continues while they remain rare.
ISOLATED_FAILURE_KINDS = (
    llm.INCOMPLETE_RESPONSE,
    llm.PROVIDER_REFUSAL,
    llm.RESPONSE_FAILED,
    llm.EMPTY_OUTPUT,
    llm.TIMEOUT,
)
MAX_FAILURES_PER_INVOCATION = 10
MAX_CUMULATIVE_FAILURE_RATE = 0.03


def failure_kinds(config, batch_dir: Path, run_ids: list[str]) -> dict:
    """The recorded failure kind of each non-completed run."""
    kinds: dict[str, str] = {}
    for run_id in run_ids:
        path = batch_dir / pilot.RUNS_DIRNAME / run_id / controller.RUN_FILENAME
        if not path.is_file():
            kinds[run_id] = "run_json_missing"
            continue
        result = hotpotqa.read_json(path)
        failure = result.get("failure") or {}
        kinds[run_id] = (failure.get("error") or {}).get("kind") or result.get("status") or "unknown"
    return kinds


def batch_failures(config, batch_dir: Path) -> dict:
    """Every finished run that is not completed, with its failure kind."""
    checkpoint = pilot.read_checkpoint(batch_dir / pilot.CHECKPOINT_FILENAME)
    failed = [
        run_id
        for run_id, record in checkpoint["finished"].items()
        if record["batch_status"] != pilot.RUN_COMPLETED
    ]
    kinds = failure_kinds(config, batch_dir, failed)
    systemic = {run_id: kind for run_id, kind in kinds.items() if kind in SYSTEMIC_FAILURE_KINDS}
    unknown = {
        run_id: kind
        for run_id, kind in kinds.items()
        if kind not in SYSTEMIC_FAILURE_KINDS and kind not in ISOLATED_FAILURE_KINDS
    }
    return {
        "finished": len(checkpoint["finished"]),
        "failed": len(failed),
        "kinds": kinds,
        "systemic": systemic,
        "unclassified": unknown,
    }


def log(config, payload: dict) -> None:
    rag_run._append_jsonl(config.paths["results"] / LOG_FILENAME, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 14 execution driver")
    parser.add_argument("--coordinates", type=int, default=100)
    parser.add_argument("--invocations", type=int, default=100)
    args = parser.parse_args(argv)

    config = load_config()
    manifest, _ = main_study.load_plan(config)
    batch_dir = stage14_cli.batch_dir_for(manifest["plan_id"])

    for number in range(1, args.invocations + 1):
        state = main_study.remaining_global_budget(config, batch_dir)
        if state["remaining_global_budget"] <= 0:
            log(config, {"event": "stopped", "reason": "global attempt ceiling reached", **state})
            print("stopped: global attempt ceiling reached")
            return 1
        try:
            result = main_study.run_main_batch(
                config,
                batch_dir=batch_dir,
                max_coordinates=args.coordinates,
                resume=True,
            )
        except BaseException as exc:  # noqa: BLE001 - a systemic problem must stop the driver
            log(
                config,
                {
                    "event": "stopped",
                    "reason": "runner raised",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc()[-2000:],
                    "budget": main_study.remaining_global_budget(config, batch_dir),
                },
            )
            print(f"stopped: {type(exc).__name__}: {exc}")
            return 2

        if result.get("scheduled_coordinates") == 0:
            log(config, {"event": "finished", "reason": "nothing pending", "budget": result["budget"]})
            print("finished: nothing pending")
            return 0

        counts = result.get("executed_status_counts", {})
        failures = sum(value for key, value in counts.items() if key != pilot.RUN_COMPLETED)
        entry = {
            "event": "invocation",
            "number": number,
            "executed_now": result["executed_now"],
            "status_counts": counts,
            "failures": failures,
            "finished_total": result["finished_total"],
            "interrupted_total": result["interrupted_total"],
            "remaining": result["remaining"],
            "attempts_this_invocation": result["invocation"]["attempts_this_invocation"],
            "cumulative_attempts": result["budget"]["cumulative_attempts"],
            "remaining_global_budget": result["budget"]["remaining_global_budget"],
            "stopped_reason": result["stopped_reason"],
            "at_utc": pilot.utc_now(),
        }
        log(config, entry)
        print(json.dumps(entry))

        if result["interrupted_total"] > 0:
            log(config, {"event": "stopped", "reason": "an interrupted coordinate exists", **entry})
            print("stopped: an interrupted coordinate exists")
            return 3
        if failures >= MAX_FAILURES_PER_INVOCATION:
            log(config, {"event": "stopped", "reason": "too many failures in one invocation", **entry})
            print("stopped: too many failures in one invocation")
            return 4

        state = batch_failures(config, batch_dir)
        rate = state["failed"] / max(state["finished"], 1)
        entry["failure_kinds"] = sorted(set(state["kinds"].values()))
        entry["cumulative_failed"] = state["failed"]
        entry["cumulative_failure_rate"] = round(rate, 4)
        if state["systemic"]:
            log(config, {"event": "stopped", "reason": "systemic failure kind", "systemic": state["systemic"], **entry})
            print(f"stopped: systemic failure kind {sorted(set(state['systemic'].values()))}")
            return 5
        if state["unclassified"]:
            log(config, {"event": "stopped", "reason": "unclassified failure kind", "unclassified": state["unclassified"], **entry})
            print(f"stopped: unclassified failure kind {sorted(set(state['unclassified'].values()))}")
            return 6
        if rate > MAX_CUMULATIVE_FAILURE_RATE:
            log(config, {"event": "stopped", "reason": "cumulative failure rate above threshold", **entry})
            print(f"stopped: cumulative failure rate {rate:.3f}")
            return 7
        if result["remaining"] == 0:
            log(config, {"event": "finished", "reason": "plan exhausted", **entry})
            print("finished: plan exhausted")
            return 0

    log(config, {"event": "paused", "reason": "invocation limit reached"})
    print("paused: invocation limit reached")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
