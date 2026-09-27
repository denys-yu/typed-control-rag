"""Stage 12 command line: offline main-study preparation steps.

Every step is offline. No provider API call is made anywhere in this file.

    python tools/stage12_cli.py select
    python tools/stage12_cli.py build-index [--rebuild]
    python tools/stage12_cli.py retrieve
    python tools/stage12_cli.py eligibility
    python tools/stage12_cli.py faults
    python tools/stage12_cli.py review-export
    python tools/stage12_cli.py validate
    python tools/stage12_cli.py dry-run [--question-id ID] [--branch D]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag.config import load_config

import stage12_main_prep as prep
import stage12_faults as faults
import stage12_validate as checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 12 main-study preparation (offline)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("select", help="draw and freeze the 300-candidate screening pool")
    index_parser = sub.add_parser("build-index", help="build the main corpus index")
    index_parser.add_argument("--rebuild", action="store_true")
    sub.add_parser("retrieve", help="rank the main corpus for every candidate question")
    sub.add_parser("eligibility", help="measure technical eligibility against the frozen index")
    sub.add_parser("faults", help="construct the four candidate contexts per eligible question")
    sub.add_parser("review-export", help="write the readable review package")
    sub.add_parser("validate", help="run the stage 12 property checks")
    dry = sub.add_parser("dry-run", help="offline controller dry run on one main case")
    dry.add_argument("--question-id")
    dry.add_argument("--branch", default="D")
    args = parser.parse_args(argv)

    config = load_config()

    if args.command == "select":
        result = prep.select_candidates(config)
        manifest = result["manifest"]
        print(f"candidates       : {manifest['candidate_count']}")
        print(f"documents        : {manifest['unique_documents']} "
              f"(from {manifest['paragraphs_before_deduplication']} paragraphs)")
        print(f"selection rule   : {manifest['selection_rule_sha256']}")
        return 0

    if args.command == "build-index":
        manifest = prep.build_main_index(config, rebuild=args.rebuild)
        print(f"index id         : {manifest['index_sha256']}")
        print(f"documents        : {manifest['document_count']} x {manifest['dimension']}")
        print(f"truncated docs   : {manifest['truncation']['documents_truncated']}")
        print(f"reused existing  : {manifest['reused_existing_index']}")
        return 0

    if args.command == "retrieve":
        summary = prep.run_main_retrieval(config)
        print(f"questions ranked : {summary['questions']} (top-{summary['top_k']})")
        print(f"index id         : {summary['index_id']}")
        return 0

    if args.command == "eligibility":
        payload = prep.measure_eligibility(config)
        counts = payload["counts"]
        print(f"candidates       : {counts['candidates']}")
        print(f"eligible         : {counts['eligible']}")
        print(f"excluded         : {counts['excluded']}")
        print(f"shortfall vs 60  : {counts['shortfall_against_target']}")
        for reason, number in payload["exclusion_reason_histogram"].items():
            print(f"  {number:4d}  {reason}")
        return 0

    if args.command == "faults":
        payload = faults.build_fault_cases(config)
        counts = payload["counts"]
        print(f"eligible questions : {counts['eligible_questions']}")
        print(f"cases built        : {counts['cases_built']}")
        print(f"construction failed: {counts['construction_failed']}")
        print(f"complete quadruples: {counts['complete_quadruples']}")
        print(f"reviews preserved  : {counts['reviews_preserved']}")
        print(f"reviews invalidated: {counts['reviews_invalidated']}")
        return 0

    if args.command == "review-export":
        payload = checks.export_review_package(config)
        print(f"files      : {len(payload['files'])}")
        for item in payload["files"]:
            print(f"  {item['file']}  ({item['questions']} questions)")
        return 0

    if args.command == "validate":
        payload = checks.validate(config)
        for check in payload["checks"]:
            print(f"[{'ok' if check['passed'] else 'FAILED'}] {check['name']}: {check['detail']}")
        print(f"status: {payload['status']}")
        return 0 if payload["status"] == "ok" else 1

    if args.command == "dry-run":
        payload = checks.dry_run_case(config, question_id=args.question_id, branch=args.branch)
        print(f"case_id    : {payload['case_id']}")
        print(f"branch     : {payload['branch']}")
        print(f"api_calls  : {payload['api_calls']}")
        print(f"output     : {payload['output_dir']}")
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
