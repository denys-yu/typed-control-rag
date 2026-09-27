"""Stage 14: deduplicated review materials for the semantic annotation that follows.

Two independent review sets are exported, both with every row pending:

* **post-retry context sufficiency** - the distinct contexts that a retry search
  produced, deduplicated by question plus ordered documents. An initial-context
  label is never copied onto them.
* **answer grounding** - the distinct (final context, generator output) cases of
  answered runs, deduplicated by a documented canonical hash, judged against the
  context the generator actually received.

The review presentation carries no branch, condition, repeat, grader assessment,
outcome frequency or benchmark answer; those mappings live in the lookup files.
Nothing is auto-filled and no label is inferred from exact match, citation
membership or the model's own explanation.

    python tools/stage14_review.py

No provider API call is made here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import controller, hotpotqa, main_study, nodes, pilot, rag_run
from typed_rag.config import load_config

import stage14_cli

POST_RETRY_CASES = "main_post_retry_contexts.jsonl"
POST_RETRY_REVIEWS = "main_post_retry_reviews.jsonl"
POST_RETRY_LOOKUP = "main_post_retry_lookup.json"
POST_RETRY_DOC = "main_post_retry_review.md"

GROUNDING_CASES = "main_answer_grounding_cases.jsonl"
GROUNDING_REVIEWS = "main_answer_grounding_reviews.jsonl"
GROUNDING_LOOKUP = "main_answer_grounding_lookup.json"
GROUNDING_DOC = "main_answer_grounding_review.md"

GROUNDING_LABELS = ("FULLY_SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONFLICTED", "UNCLEAR")
STATE_LABELS = ("OK", "PARTIAL", "EMPTY", "INCONSISTENT")

CONTEXT_HASH_RULE = (
    "sha256 of the canonical JSON of {question, documents:[{doc_id,title,text} in supplied order]}; "
    "two runs collapse only when the question and the ordered documents are identical"
)
GROUNDING_HASH_RULE = (
    "sha256 of the canonical JSON of {question, documents:[{doc_id,title,text} in supplied order], "
    "generator_output:{decision,answer,reason,evidence_doc_ids in returned order}}; two runs collapse "
    "only when all three parts are identical"
)


def context_hash(question: str, documents: list[dict]) -> str:
    return nodes.sha256_json(
        {
            "question": question,
            "documents": [
                {"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in documents
            ],
        }
    )


def grounding_hash(question: str, documents: list[dict], output: dict) -> str:
    return nodes.sha256_json(
        {
            "question": question,
            "documents": [
                {"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in documents
            ],
            "generator_output": {
                "decision": output.get("decision"),
                "answer": output.get("answer"),
                "reason": output.get("reason"),
                "evidence_doc_ids": list(output.get("evidence_doc_ids") or []),
            },
        }
    )


def _documents(entry: dict) -> list[dict]:
    return [{"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]} for d in entry["documents"]]


def build(config, batch_dir: Path) -> dict:
    results = config.paths["results"]
    index_rows = hotpotqa.read_jsonl(results / main_study.RUN_INDEX_FILENAME)
    completed = [row for row in index_rows if row["record_status"] == pilot.RUN_COMPLETED]

    post_retry: dict[str, dict] = {}
    post_retry_lookup: dict[str, list[dict]] = {}
    grounding: dict[str, dict] = {}
    grounding_lookup: dict[str, list[dict]] = {}

    for row in completed:
        run_dir = batch_dir / pilot.RUNS_DIRNAME / row["run_id"]
        context_path = run_dir / rag_run.CONTEXT_FILENAME
        run_path = run_dir / controller.RUN_FILENAME
        if not context_path.is_file() or not run_path.is_file():
            continue
        context_record = hotpotqa.read_json(context_path)
        result = hotpotqa.read_json(run_path)
        question = context_record["question"]

        for entry in context_record["contexts"][1:]:
            documents = _documents(entry)
            digest = context_hash(question, documents)
            post_retry.setdefault(
                digest,
                {
                    "context_sha256": digest,
                    "question_id": context_record["question_id"],
                    "question": question,
                    "documents": documents,
                },
            )
            post_retry_lookup.setdefault(digest, []).append(
                {
                    "run_id": row["run_id"],
                    "coordinate": row["coordinate"],
                    "iteration": entry["iteration"],
                    "query_kind": entry.get("query_kind"),
                    "branch": row["branch"],
                    "condition": row["condition"],
                    "repeat": row["repeat"],
                }
            )

        generator = result.get("generator") or {}
        # The runner records the generator payload under "output".
        output = generator.get("output") or generator.get("result") or {}
        if result.get("final_outcome") != "answered" or not output:
            continue
        final_documents = _documents(context_record["contexts"][-1])
        digest = grounding_hash(question, final_documents, output)
        grounding.setdefault(
            digest,
            {
                "case_sha256": digest,
                "question_id": context_record["question_id"],
                "question": question,
                "documents": final_documents,
                "generator_output": {
                    "decision": output.get("decision"),
                    "answer": output.get("answer"),
                    "reason": output.get("reason"),
                    "evidence_doc_ids": list(output.get("evidence_doc_ids") or []),
                },
            },
        )
        grounding_lookup.setdefault(digest, []).append(
            {
                "run_id": row["run_id"],
                "coordinate": row["coordinate"],
                "branch": row["branch"],
                "condition": row["condition"],
                "repeat": row["repeat"],
                "citation_id_membership_valid": row.get("citation_id_membership_valid"),
            }
        )

    post_rows = sorted(post_retry.values(), key=lambda item: item["context_sha256"])
    ground_rows = sorted(grounding.values(), key=lambda item: item["case_sha256"])

    hotpotqa.write_jsonl(results / POST_RETRY_CASES, post_rows)
    hotpotqa.write_jsonl(
        results / POST_RETRY_REVIEWS,
        [
            {
                "context_sha256": row["context_sha256"],
                "observed_state": None,
                "review_status": "pending",
                "reviewer": None,
                "note": "",
            }
            for row in post_rows
        ],
    )
    hotpotqa.write_json(
        results / POST_RETRY_LOOKUP,
        {
            "rule": CONTEXT_HASH_RULE,
            "cases": len(post_rows),
            "instances": sum(len(v) for v in post_retry_lookup.values()),
            "by_case": post_retry_lookup,
        },
    )

    hotpotqa.write_jsonl(results / GROUNDING_CASES, ground_rows)
    hotpotqa.write_jsonl(
        results / GROUNDING_REVIEWS,
        [
            {
                "case_sha256": row["case_sha256"],
                "answer_support": None,
                "explanation_support": None,
                "review_status": "pending",
                "reviewer": None,
                "note": "",
            }
            for row in ground_rows
        ],
    )
    hotpotqa.write_json(
        results / GROUNDING_LOOKUP,
        {
            "rule": GROUNDING_HASH_RULE,
            "cases": len(ground_rows),
            "instances": sum(len(v) for v in grounding_lookup.values()),
            "by_case": grounding_lookup,
        },
    )

    _write_post_retry_document(results / POST_RETRY_DOC, post_rows)
    _write_grounding_document(results / GROUNDING_DOC, ground_rows)

    return {
        "post_retry_cases": len(post_rows),
        "post_retry_instances": sum(len(v) for v in post_retry_lookup.values()),
        "grounding_cases": len(ground_rows),
        "grounding_instances": sum(len(v) for v in grounding_lookup.values()),
        "completed_runs_scanned": len(completed),
        "files": [
            POST_RETRY_CASES,
            POST_RETRY_REVIEWS,
            POST_RETRY_LOOKUP,
            POST_RETRY_DOC,
            GROUNDING_CASES,
            GROUNDING_REVIEWS,
            GROUNDING_LOOKUP,
            GROUNDING_DOC,
        ],
        "all_rows_pending": True,
    }


def _document_block(document: dict, order: int) -> list[str]:
    return [
        f"**{order}. {document['title']}**  `{document['doc_id']}`",
        "",
        "```text",
        document["text"],
        "```",
        "",
    ]


def _write_post_retry_document(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Main study - post-retry context sufficiency review",
        "",
        "Author: Denys Yuvzhenko",
        "",
        f"{len(rows)} distinct contexts produced by a retry search, deduplicated by question plus "
        "ordered documents. Each case is judged on its own: **the reviewed state of the initial "
        "context says nothing about the context a retry produced.**",
        "",
        f"Deduplication rule: {CONTEXT_HASH_RULE}",
        "",
        "For every case decide the state you observe - " + " / ".join(STATE_LABELS) + " - and record "
        f"it in `results/{POST_RETRY_REVIEWS}` by `context_sha256`, with your name and a short note. "
        "Every row starts pending and nothing is auto-filled.",
        "",
        "Branch, condition, repeat, the grader's own assessment, the produced answer and outcome "
        "frequencies are deliberately not shown here; the mapping to runs is in "
        f"`results/{POST_RETRY_LOOKUP}`.",
        "",
    ]
    for position, row in enumerate(rows, start=1):
        lines += [
            f"## {position}. `{row['context_sha256']}`",
            "",
            f"**Question:** {row['question'].strip()}",
            "",
        ]
        for order, document in enumerate(row["documents"], start=1):
            lines += _document_block(document, order)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _write_grounding_document(path: Path, rows: list[dict]) -> None:
    lines = [
        "# Main study - answer grounding review",
        "",
        "Author: Denys Yuvzhenko",
        "",
        f"{len(rows)} distinct cases of (final context, generator output) from answered runs, "
        "deduplicated by a canonical hash. Judge each answer **only against the documents printed "
        "with it**, which are exactly what the generator received.",
        "",
        f"Deduplication rule: {GROUNDING_HASH_RULE}",
        "",
        "Labels: " + " / ".join(GROUNDING_LABELS) + ". Record them in "
        f"`results/{GROUNDING_REVIEWS}` by `case_sha256`, with an optional separate "
        "`explanation_support` label, your name and a short note.",
        "",
        "Rules for this review:",
        "",
        "- the benchmark answer is not shown and must not be consulted;",
        "- agreement with a remembered fact is not grounding: the context must support the answer;",
        "- the model's own explanation is not evidence; it is labelled separately;",
        "- whether a cited doc_id belongs to the context is a separate structural measure, not part "
        "of the grounding label;",
        "- branch, condition, repeat and outcome frequencies are not shown; the mapping is in "
        f"`results/{GROUNDING_LOOKUP}`.",
        "",
    ]
    for position, row in enumerate(rows, start=1):
        output = row["generator_output"]
        lines += [
            f"## {position}. `{row['case_sha256']}`",
            "",
            f"**Question:** {row['question'].strip()}",
            "",
            "### Context supplied to the generator",
            "",
        ]
        for order, document in enumerate(row["documents"], start=1):
            lines += _document_block(document, order)
        lines += [
            "### Generator output",
            "",
            f"- answer: {output.get('answer')}",
            f"- cited doc_ids: {', '.join(output.get('evidence_doc_ids') or []) or 'none'}",
            f"- explanation (labelled separately, not evidence): {output.get('reason')}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    config = load_config()
    manifest, _ = main_study.load_plan(config)
    summary = build(config, stage14_cli.batch_dir_for(manifest["plan_id"]))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
