"""Stage 15.1: build the compact manuscript evidence package.

Collects the final protocol, corrected analysis outputs, accepted annotations,
experimental prompts and schemas, routing rules, configuration and manifests,
and the code needed to reproduce the analysis from `main_analysis.jsonl`, into
`results/manuscript_evidence_package.zip` with a README and a SHA-256 manifest.

Secrets, virtual environments, model caches and raw run directories are never
included. Anything a manuscript reader might expect but that is not in the
package is listed in the README.

    python tools/stage15_package.py

Offline; no provider call, no coordinate re-run.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import controller, hotpotqa, nodes
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage15_analysis as analysis

PACKAGE = "manuscript_evidence_package.zip"
MANIFEST_NAME = "SHA256SUMS.txt"
README_NAME = "README.md"
ROUTING_NAME = "methods/branch_routing_rules.json"

# (source path relative to the project root, path inside the archive)
FILES: tuple[tuple[str, str], ...] = (
    ("results/main_experiment_protocol_v3.md", "protocol/main_experiment_protocol_v3.md"),
    ("results/main_analysis_summary.md", "results/main_analysis_summary.md"),
    ("results/main_analysis_results.json", "results/main_analysis_results.json"),
    ("results/main_analysis.jsonl", "results/main_analysis.jsonl"),
    ("results/main_run_index.jsonl", "results/main_run_index.jsonl"),
    ("results/stage15_acceptance.json", "reports/stage15_acceptance.json"),
    ("results/stage15_validation.json", "reports/stage15_validation.json"),
    ("results/stage15_report.json", "reports/stage15_report.json"),
    ("results/stage15_1_correction_report.json", "reports/stage15_1_correction_report.json"),
    ("results/stage14_report.json", "reports/stage14_report.json"),
    ("results/stage14_summary.md", "reports/stage14_summary.md"),
    ("results/main_analysis_tables/branch_outcomes.csv", "tables/branch_outcomes.csv"),
    ("results/main_analysis_tables/contrasts.csv", "tables/contrasts.csv"),
    ("results/main_analysis_tables/terminal_outcomes.csv", "tables/terminal_outcomes.csv"),
    (
        "results/main_analysis_figures/figure1_branch_outcome_composition.svg",
        "figures/figure1_branch_outcome_composition.svg",
    ),
    (
        "results/main_analysis_figures/figure2_effect_estimates.svg",
        "figures/figure2_effect_estimates.svg",
    ),
    ("prompts/grade_binary_action.txt", "methods/prompts/grade_binary_action.txt"),
    ("prompts/grade_typed_action.txt", "methods/prompts/grade_typed_action.txt"),
    ("prompts/rewrite_query.txt", "methods/prompts/rewrite_query.txt"),
    ("prompts/answer.txt", "methods/prompts/answer.txt"),
    ("config/experiment.json", "methods/config/experiment.json"),
    ("requirements-frozen.txt", "methods/config/requirements-frozen.txt"),
    ("data/processed/main/manifest.json", "methods/manifests/main_data_manifest.json"),
    ("results/main_preparation/selection_rule.json", "methods/manifests/selection_rule.json"),
    ("results/main_preparation/eligibility.json", "methods/manifests/eligibility.json"),
    ("results/main_preparation/fault_manifest.json", "methods/manifests/fault_manifest.json"),
    ("artifacts/main_retrieval/index_manifest.json", "methods/manifests/index_manifest.json"),
    ("results/main_plan/manifest.json", "methods/manifests/main_plan_manifest.json"),
    ("results/main_sample_final.json", "methods/manifests/main_sample_final.json"),
    ("results/main_post_retry_reviews.jsonl", "annotations/main_post_retry_reviews.jsonl"),
    ("results/main_post_retry_contexts.jsonl", "annotations/main_post_retry_contexts.jsonl"),
    ("results/main_post_retry_lookup.json", "annotations/main_post_retry_lookup.json"),
    ("results/main_post_retry_lookup_augmented.json", "annotations/main_post_retry_lookup_augmented.json"),
    ("results/main_answer_grounding_reviews.jsonl", "annotations/main_answer_grounding_reviews.jsonl"),
    ("results/main_answer_grounding_cases.jsonl", "annotations/main_answer_grounding_cases.jsonl"),
    ("results/main_answer_grounding_lookup.json", "annotations/main_answer_grounding_lookup.json"),
    ("results/main_semantic_review_summary.md", "annotations/main_semantic_review_summary.md"),
    ("results/main_semantic_review_manifest.json", "annotations/main_semantic_review_manifest.json"),
    ("results/main_preparation/fault_reviews.jsonl", "annotations/initial_context_reviews.jsonl"),
    ("tools/stage15_analysis.py", "code/stage15_analysis.py"),
    ("tools/stage15_outputs.py", "code/stage15_outputs.py"),
    ("tools/stage15_run.py", "code/stage15_run.py"),
    ("tools/stage15_validate.py", "code/stage15_validate.py"),
    ("tools/stage15_accept.py", "code/stage15_accept.py"),
    ("tools/stage15_1_correction.py", "code/stage15_1_correction.py"),
)

NOT_INCLUDED = (
    "raw per-run directories (`run.json`, `context.json`, `calls.jsonl` and raw provider "
    "responses for 2,880 coordinates) - they live outside the repository in the execution "
    "directory and are far too large for this package; `results/main_run_index.jsonl` and "
    "`results/main_analysis.jsonl` carry one row per coordinate derived from them",
    "the HotpotQA source file, the 2,981-document main corpus and the embedding matrix - "
    "identified by the manifests in `methods/manifests/` (dataset, corpus and index hashes, "
    "embedding model and pinned revision) rather than shipped",
    "the fault-construction contexts and synthetic edits of the 240 initial contexts - "
    "described by `methods/manifests/fault_manifest.json`; the accepted initial-context reviews "
    "are included in `annotations/initial_context_reviews.jsonl`",
    "`.env`, API keys, authorization headers, the virtual environment and the local model cache - "
    "deliberately excluded",
)


def routing_rules(config) -> dict:
    """The A-D routing rules and retry-budget behaviour, read from the code.

    The decision tables are produced by calling the policy functions themselves,
    so the export cannot drift from the code that ran the experiment.
    """
    max_retries = config.controller.max_search_retries
    branches = {}
    for name in ("A", "B", "C", "D"):
        branch = controller.get_branch(name)
        branches[name] = {
            "grader": branch.grader,
            "decider": branch.decider,
            "grader_node": branch.grader_node,
            "generator_node": nodes.NODE_ANSWER,
            "rewrite_node": nodes.NODE_REWRITE,
            "description": branch.description,
        }
    return {
        "policy_version": config.controller.policy_version,
        "max_search_retries": config.controller.max_search_retries,
        "branches": branches,
        "expected_action_binary": {
            "docstring": controller.expected_action_binary.__doc__.strip(),
            "decision_table": {
                f"sufficient={sufficient}, retries_remaining={remaining}": (
                    controller.expected_action_binary(sufficient, max_retries - remaining, max_retries)
                )
                for sufficient in (True, False)
                for remaining in (max_retries, 0)
            },
        },
        "expected_action_typed": {
            "docstring": controller.expected_action_typed.__doc__.strip(),
            "decision_table": {
                f"state={state}, retries_remaining={remaining}": (
                    controller.expected_action_typed(state, max_retries - remaining, max_retries)
                )
                for state in nodes.STATES
                for remaining in (max_retries, 0)
            },
        },
        "retry_budget_behaviour": (
            "at most one search retry per run (max_search_retries = 1). A retry is only available "
            "while retries_used < max_search_retries; it adds one query-rewrite call and one more "
            "grading iteration. A retry beyond the budget in the LLM-decided branches A and B ends "
            "the run with status budget_exhausted, which is a technical status and never an "
            "abstention. The fault affects the initial context only; a retry searches the "
            "unchanged main index"
        ),
        "execution_rules": (
            "A and B execute the action the LLM proposed; C and D execute the policy action and "
            "log the proposal beside it. One generator serves every branch and never receives the "
            "branch name, the proposed action, the grader verdict or its reason"
        ),
        "source": "src/typed_rag/controller.py",
    }


def readme_text(config, files: list[tuple[str, str]]) -> str:
    payload = hotpotqa.read_json(config.paths["results"] / analysis.RESULTS_FILE)
    primary = payload["full_60"]["primary_D_minus_C_not_fully_supported"]
    companion = payload["full_60"]["companions_D_minus_C"][analysis.CAT_FULL]
    lines = [
        "# Manuscript evidence package",
        "",
        "Author: Denys Yuvzhenko",
        "",
        "Evidence for the study *The Effect of Typed Control on Retrieval-Failure Propagation in "
        "Agentic RAG Systems*. This package contains final, already-produced artefacts; it adds no "
        "new analysis and contains no article text.",
        "",
        "## Fixed scope of the experiment",
        "",
        "One model (`gpt-4o-mini-2024-07-18`), one dataset (HotpotQA dev/distractor), one retriever "
        "(`sentence-transformers/all-MiniLM-L6-v2`, pinned revision), one local corpus and index, "
        "and one reviewed sample of 60 questions x 4 initial-context conditions x 4 branches x 3 "
        "repeats = 2,880 planned coordinates. 2,873 completed; seven coordinates failed technically "
        "in total, three of those failures after a retry. Nothing here generalises beyond that "
        "setting.",
        "",
        "## Annotation provenance",
        "",
        "Initial-context states were reviewed before data collection. Post-retry context states "
        "(335 cases) and answer grounding (347 cases) were reviewed afterwards, proposed as a "
        "package and accepted by the researcher under the rubric already in force; they are not "
        "preregistered and not an independent second review, so no inter-rater reliability is "
        "claimed. `reports/stage15_acceptance.json` records the acceptance time, the accepted "
        "proposal hashes and the archived pending hashes.",
        "",
        "## Which files support which part of the manuscript",
        "",
        "**Methods**",
        "",
        "- `protocol/main_experiment_protocol_v3.md` - the frozen protocol: design, outcome "
        "definitions, estimator, sensitivity subset.",
        "- `methods/prompts/*.txt` - the exact node prompts used in the experiment.",
        "- `methods/json_schemas.json` - the strict JSON Schemas of the four nodes.",
        "- `methods/branch_routing_rules.json` - routing for branches A-D and retry-budget "
        "behaviour.",
        "- `methods/config/experiment.json`, `methods/config/requirements-frozen.txt` - runtime "
        "configuration and dependency snapshot.",
        "- `methods/manifests/*.json` - candidate selection, eligibility, fault construction, "
        "corpus and index identity (embedding model and pinned revision), the frozen plan and the "
        "final sample.",
        "",
        "**Results**",
        "",
        "- `results/main_analysis_summary.md` - the reported numbers in prose and tables.",
        "- `results/main_analysis_results.json` - every estimate, interval and diagnostic.",
        "- `results/main_analysis.jsonl` - one row per planned coordinate with accepted labels.",
        "- `results/main_run_index.jsonl` - the execution record per coordinate.",
        "- `tables/*.csv`, `figures/*.svg` - the core tables and the two figures (SVG only; no "
        "rasteriser is installed in the analysis environment).",
        f"- Headline: D - C on defective inputs, not fully supported {primary['mean_difference_pp']:+.2f} pp "
        f"[{primary['ci95_pp'][0]:+.2f}, {primary['ci95_pp'][1]:+.2f}], fully supported "
        f"{companion['mean_difference_pp']:+.2f} pp [{companion['ci95_pp'][0]:+.2f}, "
        f"{companion['ci95_pp'][1]:+.2f}].",
        "",
        "**Limitations and integrity**",
        "",
        "- `reports/stage15_validation.json` - the offline checks behind the analysis.",
        "- `reports/stage15_1_correction_report.json` - the reporting corrections and proof that "
        "the estimates did not change.",
        "- `reports/stage14_report.json`, `reports/stage14_summary.md` - execution accounting, "
        "technical missingness and audits.",
        "- `annotations/` - accepted labels, the reviewed cases they attach to, and the lookups "
        "that expand them to runs.",
        "",
        "## Reproducing the analysis offline",
        "",
        "From the project root, with `main_analysis.jsonl` and the accepted annotation files in "
        "`results/`:",
        "",
        "```powershell",
        "python tools/stage15_run.py",
        "python tools/stage15_validate.py",
        "```",
        "",
        "`code/` holds the same modules as `tools/` for reference. The analysis makes no network "
        "call and needs only the Python standard library; the figures are written as SVG text.",
        "",
        "## How this differs from a complete raw-data repository",
        "",
        "This is a compact evidence package, not a full replication archive. The following are "
        "referenced by hash or manifest rather than included:",
        "",
    ]
    for item in NOT_INCLUDED:
        lines.append(f"- {item}")
    lines += [
        "",
        "## Integrity",
        "",
        f"`{MANIFEST_NAME}` lists the SHA-256 of every file in this archive except itself. Paths "
        "are relative to the archive root.",
        "",
        f"Files in this package: {len(files) + 3} (including this README, the schema export and "
        "the routing rules).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    config = load_config()
    results = config.paths["results"]
    root = config.project_root

    present: list[tuple[str, str]] = []
    missing: list[str] = []
    for source, target in FILES:
        (present if (root / source).is_file() else missing).append(
            (source, target) if (root / source).is_file() else source
        )
    if missing:
        print("missing source files: " + ", ".join(missing))

    schemas = {
        node: {
            "schema_name": nodes.NODE_SPECS[node].schema_name,
            "json_schema": nodes.json_schema(node),
        }
        for node in (
            nodes.NODE_GRADE_BINARY_ACTION,
            nodes.NODE_GRADE_TYPED_ACTION,
            nodes.NODE_REWRITE,
            nodes.NODE_ANSWER,
        )
    }
    generated = {
        "methods/json_schemas.json": json.dumps(schemas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        ROUTING_NAME: json.dumps(routing_rules(config), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        README_NAME: readme_text(config, present),
    }

    archive_path = results / PACKAGE
    if archive_path.exists():
        archive_path.unlink()

    entries: dict[str, str] = {}
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for source, target in present:
            bundle.write(root / source, target)
            entries[target] = sha256_file(root / source)
        for target, text in generated.items():
            bundle.writestr(target, text)
            import hashlib

            entries[target] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        manifest_text = "".join(f"{digest}  {name}\n" for name, digest in sorted(entries.items()))
        bundle.writestr(MANIFEST_NAME, manifest_text)

    # Validate the archive: readable, manifest matches contents, nothing forbidden inside.
    problems: list[str] = []
    forbidden = (".env", "site-packages", ".venv", "models--", "api_key", "authorization")
    with zipfile.ZipFile(archive_path) as bundle:
        bad = bundle.testzip()
        if bad is not None:
            problems.append(f"corrupt entry: {bad}")
        names = set(bundle.namelist())
        if MANIFEST_NAME not in names:
            problems.append("manifest missing from the archive")
        listed = {}
        for line in bundle.read(MANIFEST_NAME).decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            listed[name] = digest
        if set(listed) != names - {MANIFEST_NAME}:
            problems.append("manifest does not list exactly the archive contents")
        import hashlib

        for name, digest in listed.items():
            actual = hashlib.sha256(bundle.read(name)).hexdigest()
            if actual != digest:
                problems.append(f"{name}: manifest hash mismatch")
        for name in names:
            if any(token in name.lower() for token in forbidden):
                problems.append(f"{name}: forbidden path")

    summary = {
        "archive": f"results/{PACKAGE}",
        "archive_sha256": sha256_file(archive_path),
        "size_bytes": archive_path.stat().st_size,
        "entries": len(entries) + 1,
        "manifest_excludes_itself": True,
        "missing_sources": missing,
        "validation_problems": problems,
        "valid": not problems,
    }
    hotpotqa.write_json(results / "manuscript_evidence_package_manifest.json", {
        "stage": "stage15_1_packaging",
        "generated_at_utc": analysis.utc_now(),
        "author": "Denys Yuvzhenko",
        **summary,
        "contents_sha256": entries,
        "not_included": list(NOT_INCLUDED),
    })
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
