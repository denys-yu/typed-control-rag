"""Stage 14 command line: plan, verify, execute and consolidate the main experiment.

    python tools/stage14_cli.py plan [--replace]
    python tools/stage14_cli.py verify
    python tools/stage14_cli.py preflight
    python tools/stage14_cli.py budget
    python tools/stage14_cli.py run --coordinates N [--no-resume]
    python tools/stage14_cli.py consolidate

`run` is the only command that can make a provider call. It verifies the frozen
plan, reads the cumulative stage 14 ledger and limits the invocation to the
smaller of four attempts per scheduled coordinate and the remaining global
allowance.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import main_study, pilot
from typed_rag.config import load_config

BATCH_ROOT = Path.home() / "trfp_runs"


def batch_dir_for(plan_id: str) -> Path:
    return BATCH_ROOT / f"m{plan_id[:12]}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 14 main experiment")
    sub = parser.add_subparsers(dest="command", required=True)
    plan_parser = sub.add_parser("plan", help="freeze the main plan")
    plan_parser.add_argument("--replace", action="store_true")
    sub.add_parser("verify", help="verify the frozen plan against the current files")
    sub.add_parser("preflight", help="run every offline gate, including the output-path probe")
    sub.add_parser("budget", help="show the cumulative attempt ledger")
    run_parser = sub.add_parser("run", help="execute pending coordinates (paid)")
    run_parser.add_argument("--coordinates", type=int, required=True)
    run_parser.add_argument("--no-resume", action="store_true")
    sub.add_parser("consolidate", help="write one index row per planned coordinate")
    args = parser.parse_args(argv)

    config = load_config()

    if args.command == "plan":
        manifest, runs = main_study.build_plan(config)
        written = main_study.write_plan(config, manifest, runs, replace=args.replace)
        counts = manifest["counts"]
        print(f"plan id              : {manifest['plan_id']}")
        print(f"questions            : {counts['questions']}")
        print(f"approved contexts    : {counts['approved_initial_contexts']}")
        print(f"planned coordinates  : {counts['planned_coordinates']} ({counts['planned_coordinates_formula']})")
        print(f"attempt ceiling      : {counts['provider_attempt_ceiling']}")
        print(f"written              : {written['written']}")
        print(f"batch directory      : {batch_dir_for(manifest['plan_id'])}")
        return 0

    if args.command == "verify":
        manifest, runs = main_study.load_plan(config)
        problems = main_study.verify_plan(config, manifest)
        print(f"plan id : {manifest['plan_id']}")
        print(f"runs    : {len(runs)}")
        if problems:
            for problem in problems:
                print(f"  CHANGED {problem}")
            return 1
        print("status  : plan matches the current files")
        return 0

    if args.command == "preflight":
        manifest, _ = main_study.load_plan(config)
        checks = main_study.offline_checks(config, batch_dir_for(manifest["plan_id"]))
        for key, value in checks.items():
            if key in ("isolation_problems", "output_path_check", "generation_parameters", "controller"):
                continue
            print(f"{key:52s}: {value}")
        path_check = checks["output_path_check"]
        print(f"{'longest output path':52s}: {path_check['longest_path_length']} chars (limit {path_check['max_path']})")
        print(f"{'output path probe':52s}: {path_check['probe']['write_ok']} / read back {path_check['probe']['read_back_ok']}")
        if checks["isolation_problems"]:
            for problem in checks["isolation_problems"]:
                print(f"  ISOLATION {problem}")
        print(f"{'all_passed':52s}: {checks['all_passed']}")
        return 0 if checks["all_passed"] else 1

    if args.command == "budget":
        manifest, _ = main_study.load_plan(config)
        state = main_study.remaining_global_budget(config, batch_dir_for(manifest["plan_id"]))
        print(json.dumps(state, indent=2, sort_keys=True))
        return 0 if state["agreement"] else 1

    if args.command == "run":
        manifest, _ = main_study.load_plan(config)
        batch_dir = batch_dir_for(manifest["plan_id"])
        result = main_study.run_main_batch(
            config,
            batch_dir=batch_dir,
            max_coordinates=args.coordinates,
            resume=not args.no_resume,
        )
        if result.get("scheduled_coordinates") == 0:
            print("nothing pending")
            return 0
        print(f"executed now         : {result['executed_now']} {result.get('executed_status_counts')}")
        print(f"finished total       : {result['finished_total']}")
        print(f"interrupted total    : {result['interrupted_total']}")
        print(f"remaining coordinates: {result['remaining']}")
        print(f"attempts this run    : {result['invocation']['attempts_this_invocation']}")
        print(f"cumulative attempts  : {result['budget']['cumulative_attempts']}")
        print(f"remaining budget     : {result['budget']['remaining_global_budget']}")
        print(f"stopped reason       : {result['stopped_reason']}")
        return 0

    if args.command == "consolidate":
        manifest, _ = main_study.load_plan(config)
        summary = main_study.consolidate(config, batch_dir_for(manifest["plan_id"]))
        print(json.dumps(summary, indent=2, sort_keys=True)[:4000])
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
