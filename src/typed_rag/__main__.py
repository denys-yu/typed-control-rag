"""Command line entry point: `python -m typed_rag --check`, `--prepare-data`, `--run-rag-example`, `--plan-pilot`, ..."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from typed_rag import __version__, preview
from typed_rag.config import ConfigError, ExperimentConfig, load_config
from typed_rag.download import DownloadError
from typed_rag.hotpotqa import DatasetError
from typed_rag.controller import BranchError
from typed_rag.fault_cases import FaultCaseError
from typed_rag.llm import MissingAPIKeyError
from typed_rag.pilot import PilotError, StalePlanError
from typed_rag.prepare import REPORT_FILENAME, prepare_data
from typed_rag.retrieval import IndexError_, SearchError

ENVIRONMENT_REPORT_NAME = "environment_check.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="typed_rag",
        description="Typed control over retrieval-failure propagation in agentic RAG.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate configuration, prepare working directories and write an environment report",
    )
    parser.add_argument(
        "--prepare-data",
        action="store_true",
        help="download HotpotQA dev/distractor, validate it and build the pilot files",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="re-download the raw dataset even if a valid local copy exists",
    )
    parser.add_argument(
        "--data-summary",
        action="store_true",
        help="print a summary of the prepared data",
    )
    parser.add_argument(
        "--show-example",
        type=int,
        metavar="INDEX",
        default=None,
        help="show one pilot item by its index in the pilot list",
    )
    parser.add_argument(
        "--with-gold",
        action="store_true",
        help="researcher view: also show the answer and supporting sentences",
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="embed the pilot corpus and store the local vector index",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="with --build-index: rebuild even if the stored index still matches",
    )
    parser.add_argument(
        "--index-summary",
        action="store_true",
        help="print the stored index manifest",
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        default=None,
        help="search the shared corpus for a free-text query",
    )
    parser.add_argument(
        "--search-example",
        type=int,
        metavar="INDEX",
        default=None,
        help="search the shared corpus using the text of pilot question INDEX",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        metavar="K",
        help="number of documents to return (default: retrieval.top_k from the configuration)",
    )
    parser.add_argument(
        "--evaluate-retrieval",
        action="store_true",
        help="run retrieval for every pilot question and score it against gold documents",
    )
    parser.add_argument(
        "--check-llm-config",
        action="store_true",
        help="validate LLM settings, SDK, prompts and key presence locally; no API call",
    )
    parser.add_argument(
        "--run-rag-example",
        type=int,
        metavar="INDEX",
        default=None,
        help="stage4_diagnostic run on pilot question INDEX: retrieval + grader + generator "
        "(at most two API calls)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --run-rag-example / --run-controlled-example / --run-pilot: prepare the request(s) "
        "but create no client and send nothing",
    )
    parser.add_argument(
        "--show-controller-rules",
        action="store_true",
        help="print the branch definitions and transition rules of stage 5; no API call",
    )
    parser.add_argument(
        "--run-controlled-example",
        type=int,
        metavar="INDEX",
        default=None,
        help="stage5_controller_check run of one branch on pilot question INDEX "
        "(at most four API calls, at most one retry search)",
    )
    parser.add_argument(
        "--branch",
        default=None,
        metavar="A|B|C|D",
        help="with --run-controlled-example: which experimental branch to run",
    )
    parser.add_argument(
        "--prepare-fault-cases",
        action="store_true",
        help="build the CLEAN/PARTIAL/EMPTY/INCONSISTENT candidate contexts for eligible pilot questions",
    )
    parser.add_argument(
        "--fault-summary",
        action="store_true",
        help="print counts, eligibility and review status of the prepared fault cases",
    )
    parser.add_argument(
        "--show-fault-case",
        metavar="CASE_ID",
        default=None,
        help="show a prepared case: question and documents only",
    )
    parser.add_argument(
        "--with-annotations",
        action="store_true",
        help="with --show-fault-case: researcher view with operation, expected state, provenance and review status",
    )
    parser.add_argument(
        "--validate-fault-reviews",
        action="store_true",
        help="check reviews.jsonl and count approved cases and ready quadruples",
    )
    parser.add_argument(
        "--run-fault-case",
        metavar="CASE_ID",
        default=None,
        help="feed a prepared case to the controller (--branch required; real runs need an approved case)",
    )
    parser.add_argument(
        "--plan-pilot",
        action="store_true",
        help="stage 7: derive the matched subset from the reviews and freeze the pilot plan (no API call)",
    )
    parser.add_argument(
        "--replace-plan",
        action="store_true",
        help="with --plan-pilot: explicitly replace an existing, different frozen plan",
    )
    parser.add_argument(
        "--run-pilot",
        action="store_true",
        help="stage 7: execute the frozen plan; with --dry-run validate it and prepare requests without any API call",
    )
    parser.add_argument(
        "--max-api-calls",
        type=int,
        default=None,
        metavar="N",
        help="with --run-pilot (real execution): mandatory maximum number of API-call attempts for this invocation",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="with --run-pilot: continue a started batch of the same frozen plan; finished, failed and "
        "interrupted runs are skipped, never repeated",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        metavar="N",
        help="with --run-pilot: execute at most N pending pipeline runs in this invocation",
    )
    parser.add_argument(
        "--pilot-summary",
        action="store_true",
        help="stage 7: diagnostic summary of the executed batch of the frozen plan (no API call)",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help="with --run-pilot, --check-scope or --pilot-summary: execute, resume or summarise this batch "
        "directory instead of the configured default <results>/pilot_runs/<plan_id>; the destination is "
        "operational metadata only and changes no scientific input",
    )
    parser.add_argument(
        "--scope-file",
        type=Path,
        default=None,
        help="with --run-pilot or --check-scope: restrict and order execution to the run ids listed in this "
        "scope file; a batch started with a scope stays bound to it",
    )
    parser.add_argument(
        "--check-scope",
        action="store_true",
        help="offline check of a --scope-file against the frozen plan, the batch checkpoint and the output "
        "paths of the destination (no API call)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="path to the experiment configuration (default: config/experiment.json)",
    )
    return parser


def build_report(config: ExperimentConfig) -> dict:
    """Technical environment facts only; never environment variables or secrets."""
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "ok",
        "package_version": __version__,
        "experiment_name": config.experiment_name,
        "seed": config.seed,
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "project_root": str(config.project_root),
        "config_path": str(config.config_path),
        "paths": {key: str(value) for key, value in config.paths.items()},
    }


def run_check(config: ExperimentConfig) -> int:
    config.ensure_directories()

    report = build_report(config)
    report_path = config.paths["results"] / ENVIRONMENT_REPORT_NAME
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"experiment    : {config.experiment_name}")
    print(f"seed          : {config.seed}")
    print(f"project root  : {config.project_root}")
    print(f"config        : {config.config_path}")
    print(f"python        : {report['python_version']}")
    print(f"interpreter   : {report['python_executable']}")
    print(f"platform      : {report['platform']}")
    for key in sorted(config.paths):
        print(f"path {key:<15}: {config.paths[key]}")
    print(f"report        : {report_path}")
    print("environment check: OK")
    return 0


def run_prepare_data(config: ExperimentConfig, force_download: bool) -> int:
    report = prepare_data(config, force_download=force_download)
    download = report["download"]

    print(f"dataset       : {report['dataset']}")
    print(f"source used   : {download['source_url_used'] or 'existing local file'}")
    print(f"raw sha256    : {download['raw_sha256']}")
    print(f"records total : {report['structural_checks']['records_total']}")
    print(f"records valid : {report['structural_checks']['records_valid']}")
    print(f"excluded      : {report['structural_checks']['excluded_count']}")
    print(f"pilot size    : {report['pilot']['size']}")
    print(f"corpus docs   : {report['corpus']['unique_documents']} "
          f"(from {report['corpus']['paragraphs_before_deduplication']} paragraphs)")
    print(f"candidates    : {report['separation_checks']['main_candidate_count']}")
    print(f"pilot/reserve overlap: {report['separation_checks']['pilot_candidate_overlap_count']}")
    print(f"report        : {config.paths['results'] / REPORT_FILENAME}")
    print("data preparation: OK")
    return 0


def pilot_scope(config: ExperimentConfig, scope_file: Path | None) -> dict | None:
    """Load an optional continuation scope for --run-pilot; None means the whole plan."""
    if scope_file is None:
        return None
    from typed_rag import pilot

    manifest, runs = pilot.load_plan(config)
    return pilot.load_scope(scope_file, manifest["plan_id"], runs)


def pilot_question(config: ExperimentConfig, index: int) -> dict:
    """One pilot question by position; only id and text exist in that file."""
    from typed_rag.rag_run import pilot_question as _pilot_question

    return _pilot_question(config, index)


def run_check_llm_config(config: ExperimentConfig) -> int:
    from typed_rag.rag_run import format_llm_config_check

    text, ok = format_llm_config_check(config)
    print(text)
    return 0 if ok else 8


def run_controlled_example(config: ExperimentConfig, index: int, branch: str | None, dry_run: bool) -> int:
    from typed_rag.controller import RUN_COMPLETED, format_controlled_run, run_controlled

    if branch is None:
        raise BranchError("--run-controlled-example requires --branch A|B|C|D")
    run = run_controlled(config, index, branch, dry_run=dry_run)
    print(format_controlled_run(run))
    return 0 if run["status"] in (RUN_COMPLETED, "dry_run") else 9


def run_rag_example(config: ExperimentConfig, index: int, dry_run: bool) -> int:
    from typed_rag.rag_run import RUN_TECHNICAL_FAILURE, format_run, run_example

    run = run_example(config, index, dry_run=dry_run)
    print(format_run(run))
    return 9 if run["status"] == RUN_TECHNICAL_FAILURE else 0


def run_build_index(config: ExperimentConfig, rebuild: bool) -> None:
    from typed_rag import retrieval

    manifest = retrieval.build_index(config, rebuild=rebuild)
    state = "reused existing index" if manifest["reused_existing_index"] else "built"
    print(f"index         : {state}")
    print(f"documents     : {manifest['document_count']}")
    print(f"matrix        : {manifest['document_count']} x {manifest['dimension']} {manifest['dtype']}")
    print(f"model         : {manifest['model_name']} @ {manifest['model_revision']}")
    print(f"max_seq_length: {manifest['truncation']['max_seq_length']}")
    print(f"truncated docs: {manifest['truncation']['documents_truncated']}")
    print(f"build seconds : {manifest['build_seconds']}")
    print(f"index id      : {manifest['index_sha256']}")
    print(f"index dir     : {config.index_dir}")


def _use_utf8_output() -> None:
    """Dataset text is not ASCII; a legacy Windows console codepage must not crash us."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def run_search(config: ExperimentConfig, query: str, top_k: int, label: str | None = None) -> None:
    """Plain search over the whole shared corpus; annotations are never read."""
    from typed_rag import retrieval

    index = retrieval.load_index(config)
    model = retrieval.load_model(config)
    hits = retrieval.search(index, model, query, top_k)
    if label:
        print(label)
    print(f"query         : {query}")
    print(retrieval.format_hits(hits, index, top_k))


def main(argv: list[str] | None = None) -> int:
    _use_utf8_output()
    parser = build_parser()
    args = parser.parse_args(argv)

    actions = [
        args.check,
        args.prepare_data,
        args.data_summary,
        args.show_example is not None,
        args.build_index,
        args.index_summary,
        args.search is not None,
        args.search_example is not None,
        args.evaluate_retrieval,
        args.check_llm_config,
        args.run_rag_example is not None,
        args.show_controller_rules,
        args.run_controlled_example is not None,
        args.prepare_fault_cases,
        args.fault_summary,
        args.show_fault_case is not None,
        args.validate_fault_reviews,
        args.run_fault_case is not None,
        args.plan_pilot,
        args.run_pilot,
        args.check_scope,
        args.pilot_summary,
    ]
    if not any(actions):
        parser.print_help()
        return 0

    try:
        config = load_config(args.config)
        if args.check:
            run_check(config)
        if args.prepare_data:
            run_prepare_data(config, args.force_download)
        if args.data_summary:
            print(preview.format_summary(config))
        if args.show_example is not None:
            print(preview.format_example(config, args.show_example, args.with_gold))
        if args.build_index:
            run_build_index(config, args.rebuild)
        if args.index_summary:
            from typed_rag import retrieval

            print(retrieval.format_index_summary(config))
        top_k = args.top_k if args.top_k is not None else config.retrieval.top_k
        if args.search is not None:
            run_search(config, args.search, top_k)
        if args.search_example is not None:
            question = pilot_question(config, args.search_example)
            run_search(
                config,
                question["question"],
                top_k,
                label=f"pilot index   : {args.search_example} ({question['question_id']})",
            )
        if args.evaluate_retrieval:
            from typed_rag.evaluate import evaluate_retrieval, format_evaluation

            report = evaluate_retrieval(config)
            print(format_evaluation(report))
            print(f"results       : {config.paths['results']}")
        exit_code = 0
        if args.check_llm_config:
            exit_code = run_check_llm_config(config) or exit_code
        if args.run_rag_example is not None:
            exit_code = run_rag_example(config, args.run_rag_example, args.dry_run) or exit_code
        if args.show_controller_rules:
            from typed_rag.controller import format_rules

            print(format_rules(config))
        if args.run_controlled_example is not None:
            exit_code = (
                run_controlled_example(config, args.run_controlled_example, args.branch, args.dry_run)
                or exit_code
            )
        if args.prepare_fault_cases:
            from typed_rag import fault_cases

            manifest = fault_cases.write_cases(config, fault_cases.build_cases(config))
            counts = manifest["counts"]
            print(f"fault cases   : {fault_cases.fault_cases_dir(config)}")
            print(f"questions     : {counts['pilot_questions']} pilot, {counts['eligible_questions']} eligible")
            print("built         : " + ", ".join(f"{c}={n}" for c, n in counts["cases_built"].items()))
            print("failed        : " + ", ".join(f"{c}={n}" for c, n in counts["construction_failed"].items()))
            print(f"reviews kept  : {counts['reviews_preserved']} (new cases start as pending)")
            print("fault case preparation: OK")
        if args.fault_summary:
            from typed_rag import fault_cases

            print(fault_cases.format_summary(config))
        if args.show_fault_case is not None:
            from typed_rag import fault_cases

            print(fault_cases.format_case(config, args.show_fault_case, args.with_annotations))
        if args.validate_fault_reviews:
            from typed_rag import fault_cases

            report = fault_cases.validate_reviews(config)
            print(fault_cases.format_validation(report))
            exit_code = exit_code or (0 if report["valid"] else 11)
        if args.run_fault_case is not None:
            from typed_rag import fault_cases
            from typed_rag.controller import RUN_COMPLETED, format_controlled_run

            if args.branch is None:
                raise BranchError("--run-fault-case requires --branch A|B|C|D")
            run = fault_cases.run_fault_case(config, args.run_fault_case, args.branch, dry_run=args.dry_run)
            print(format_controlled_run(run))
            print(f"case review   : {run['fault_case_review_status']} - {run['fault_case_note']}")
            exit_code = exit_code or (0 if run["status"] in (RUN_COMPLETED, "dry_run") else 9)
        if args.plan_pilot:
            from typed_rag import pilot

            manifest, runs = pilot.build_plan(config)
            written = pilot.write_plan(config, manifest, runs, replace=args.replace_plan)
            print(pilot.format_plan(manifest, runs, written))
        if args.run_pilot:
            from typed_rag import pilot

            if args.dry_run:
                report = pilot.dry_run_batch(config)
                print(pilot.format_dry_run(report))
                exit_code = exit_code or (0 if report["checks"]["all_passed"] else 12)
            else:
                if args.max_api_calls is None:
                    raise PilotError("--run-pilot without --dry-run requires --max-api-calls N (an explicit API-call budget)")
                result = pilot.run_batch(
                    config,
                    args.max_api_calls,
                    resume=args.resume,
                    max_runs=args.max_runs,
                    batch_dir=args.batch_dir,
                    scope=pilot_scope(config, args.scope_file),
                )
                print(pilot.format_batch_result(result))
                non_completed = sum(v for k, v in result["executed_status_counts"].items() if k != pilot.RUN_COMPLETED)
                exit_code = exit_code or (9 if non_completed else 0)
        if args.check_scope:
            from typed_rag import pilot

            if args.scope_file is None:
                raise PilotError("--check-scope requires --scope-file PATH")
            report = pilot.check_scope(config, args.scope_file, args.batch_dir)
            print(pilot.format_scope_check(report))
            exit_code = exit_code or (0 if report["ok"] else 12)
        if args.pilot_summary:
            from typed_rag import pilot

            batch_dir = args.batch_dir.resolve() if args.batch_dir is not None else None
            print(pilot.format_summary(pilot.summarise_batch(config, batch_dir)))
        return exit_code
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    except DownloadError as exc:
        print(f"download error: {exc}", file=sys.stderr)
        return 4
    except DatasetError as exc:
        print(f"dataset error: {exc}", file=sys.stderr)
        return 5
    except SearchError as exc:
        print(f"search error: {exc}", file=sys.stderr)
        return 6
    except IndexError_ as exc:
        print(f"index error: {exc}", file=sys.stderr)
        return 7
    except MissingAPIKeyError as exc:
        print(f"llm error: {exc}", file=sys.stderr)
        return 8
    except BranchError as exc:
        print(f"branch error: {exc}", file=sys.stderr)
        return 10
    except FaultCaseError as exc:
        print(f"fault case error: {exc}", file=sys.stderr)
        return 11
    except StalePlanError as exc:
        print(f"stale plan: {exc}", file=sys.stderr)
        return 13
    except PilotError as exc:
        print(f"pilot error: {exc}", file=sys.stderr)
        return 12
    except OSError as exc:
        print(f"filesystem error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
