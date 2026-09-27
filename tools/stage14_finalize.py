"""Stage 14: rebuild the run index with the corrected generator-field reader.

`main_study.consolidate` reads the generator payload from `generator["result"]`,
but the runner writes it to `generator["output"]`. The consequence was confined
to three read-side fields of the index (`answer`, `returned_evidence_doc_ids`,
`citation_id_membership_valid`), which came out null. Nothing that was sent,
executed or recorded during the run is affected: every run.json, context.json,
calls.jsonl and raw response is untouched, and no coordinate is re-run.

`src/typed_rag/main_study.py` is bound by the frozen plan and is deliberately
**not** edited after execution, so this correction lives here and rebuilds the
index from the same run records.

    python tools/stage14_finalize.py

No provider API call is made here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import controller, hotpotqa, main_study, pilot, rag_run
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage14_cli

CORRECTION_FILENAME = "stage14_index_correction.json"
CORRECTED_FIELDS = ("answer", "returned_evidence_doc_ids", "citation_id_membership_valid")


def generator_output(result: dict) -> dict:
    """The generator payload as the runner actually records it."""
    generator = result.get("generator") or {}
    return generator.get("output") or generator.get("result") or {}


def rebuild(config, batch_dir: Path) -> dict:
    results = config.paths["results"]
    base = main_study.consolidate(config, batch_dir)
    rows = hotpotqa.read_jsonl(results / main_study.RUN_INDEX_FILENAME)

    corrected = 0
    answered = 0
    citation_counts = {"valid": 0, "invalid": 0, "not_applicable": 0}
    for row in rows:
        if row["record_status"] != pilot.RUN_COMPLETED:
            row["citation_id_membership_valid"] = "not_applicable"
            citation_counts["not_applicable"] += 1
            continue
        run_dir = batch_dir / pilot.RUNS_DIRNAME / row["run_id"]
        result = hotpotqa.read_json(run_dir / controller.RUN_FILENAME)
        output = generator_output(result)
        row["generator_decision"] = output.get("decision")
        row["generator_explanation"] = output.get("reason")
        if result.get("final_outcome") == "answered" and output:
            answered += 1
            row["answer"] = output.get("answer")
            row["returned_evidence_doc_ids"] = list(output.get("evidence_doc_ids") or [])
            context_record = hotpotqa.read_json(run_dir / rag_run.CONTEXT_FILENAME)
            final_ids = set(context_record["contexts"][-1]["doc_ids"])
            valid = all(doc_id in final_ids for doc_id in row["returned_evidence_doc_ids"])
            row["citation_id_membership_valid"] = valid
            citation_counts["valid" if valid else "invalid"] += 1
            corrected += 1
        else:
            row["citation_id_membership_valid"] = "not_applicable"
            citation_counts["not_applicable"] += 1

    hotpotqa.write_jsonl(results / main_study.RUN_INDEX_FILENAME, rows)
    correction = {
        "stage": "stage14_index_correction",
        "recorded_at_utc": pilot.utc_now(),
        "defect": (
            "main_study.consolidate reads the generator payload from generator['result']; the "
            "runner writes it to generator['output']"
        ),
        "scope": (
            "read-side only: the three index fields "
            + ", ".join(CORRECTED_FIELDS)
            + " were null. No request, response, run record or coordinate is affected and nothing "
            "was re-run"
        ),
        "frozen_implementation_unchanged": (
            "src/typed_rag/main_study.py is bound by the frozen plan and was not edited after "
            "execution; the correction is applied by tools/stage14_finalize.py when rebuilding "
            "the index from the same run records"
        ),
        "rows": len(rows),
        "answered_runs_filled": corrected,
        "answered_runs_seen": answered,
        "citation_id_membership": citation_counts,
        "run_index_sha256": sha256_file(results / main_study.RUN_INDEX_FILENAME),
    }
    hotpotqa.write_json(results / CORRECTION_FILENAME, correction)
    return {"base": base, "correction": correction}


def main() -> int:
    config = load_config()
    manifest, _ = main_study.load_plan(config)
    payload = rebuild(config, stage14_cli.batch_dir_for(manifest["plan_id"]))
    print(json.dumps(payload["correction"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
