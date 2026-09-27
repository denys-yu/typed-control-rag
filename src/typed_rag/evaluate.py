"""Diagnostic evaluation of retrieval on the pilot.

This is the only module allowed to read pilot_annotations.jsonl, and it reads
them only *after* retrieval has produced its ranking: gold documents never
influence the query, the corpus or the ranking.

What is measured here is coverage of the gold supporting documents. Retrieving
both supporting documents is a technical coverage result; it is not proof that
the retrieved context is semantically sufficient to answer the question.
"""

from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from typed_rag import hotpotqa, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.retrieval import LoadedIndex

RETRIEVAL_RESULTS_FILENAME = "pilot_retrieval.jsonl"
RETRIEVAL_REPORT_FILENAME = "retrieval_report.json"

EVALUATION_DEPTH = 10
METRIC_CUTOFFS = (5, 10)

LATENCY_SCOPE = (
    "per-question wall clock around query embedding + matrix product + ranking, "
    "measured with time.perf_counter on CPU; model loading and index loading are "
    "outside the measured span; no warm-up run is excluded, so the first question "
    "carries first-call overhead"
)

COVERAGE_NOTE = (
    "document recall counts gold supporting documents present in top-k. It is a "
    "technical coverage measure, not evidence of semantic sufficiency of the "
    "retrieved context."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_retrieval(
    config: ExperimentConfig, index: LoadedIndex, model: object, depth: int = EVALUATION_DEPTH
) -> list[dict]:
    """Search for every pilot question; no gold data is touched here."""
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    rows = []
    for item in questions:
        started = time.perf_counter()
        hits = retrieval.search(index, model, item["question"], depth)
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "question_id": item["question_id"],
                "question": item["question"],
                "index_id": index.index_id,
                "top_k": depth,
                "search_seconds": round(elapsed, 4),
                "results": [
                    {"rank": hit.rank, "doc_id": hit.doc_id, "score": round(hit.score, 6)}
                    for hit in hits
                ],
            }
        )
    return rows


def score_retrieval(rows: list[dict], annotations: list[dict]) -> dict:
    """Compare an existing ranking against gold supporting documents."""
    gold = {item["question_id"]: set(item["supporting_doc_ids"]) for item in annotations}

    metrics = {}
    per_question = []
    for cutoff in METRIC_CUTOFFS:
        recalls = []
        complete = 0
        found_counter: Counter[int] = Counter()
        for row in rows:
            expected = gold[row["question_id"]]
            retrieved = {result["doc_id"] for result in row["results"][:cutoff]}
            found = expected & retrieved
            recalls.append(len(found) / len(expected))
            found_counter[len(found)] += 1
            if found == expected:
                complete += 1
        metrics[f"recall_at_{cutoff}"] = round(sum(recalls) / len(recalls), 4)
        metrics[f"all_support_at_{cutoff}"] = round(complete / len(rows), 4)
        metrics[f"questions_with_all_support_at_{cutoff}"] = complete
        metrics[f"supporting_documents_found_at_{cutoff}"] = {
            str(count): found_counter.get(count, 0) for count in (0, 1, 2)
        }

    for row in rows:
        expected = gold[row["question_id"]]
        ranks = {
            result["doc_id"]: result["rank"]
            for result in row["results"]
            if result["doc_id"] in expected
        }
        per_question.append(
            {
                "question_id": row["question_id"],
                "gold_document_count": len(expected),
                "gold_ranks": [ranks.get(doc_id) for doc_id in sorted(expected)],
                "found_at_5": sum(1 for rank in ranks.values() if rank <= 5),
                "found_at_10": len(ranks),
            }
        )
    return {"metrics": metrics, "per_question": per_question}


def _reproducibility_checks(config: ExperimentConfig, index: LoadedIndex, model: object) -> dict:
    """Same query twice, and a freshly reloaded index, must rank identically."""
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    probe = questions[0]["question"]

    first = retrieval.search(index, model, probe, EVALUATION_DEPTH)
    second = retrieval.search(index, model, probe, EVALUATION_DEPTH)
    reloaded_index = retrieval.load_index(config)
    third = retrieval.search(reloaded_index, model, probe, EVALUATION_DEPTH)

    ids_first = [hit.doc_id for hit in first]
    scores_first = [hit.score for hit in first]
    return {
        "probe_question_id": questions[0]["question_id"],
        "repeated_query_same_order": ids_first == [hit.doc_id for hit in second],
        "repeated_query_same_scores": scores_first == [hit.score for hit in second],
        "reloaded_index_same_order": ids_first == [hit.doc_id for hit in third],
        "reloaded_index_same_scores": scores_first == [hit.score for hit in third],
        "note": (
            "Identity is asserted for this environment and this stored index. "
            "Embeddings recomputed on different hardware or library versions may "
            "differ in the last bits; the stored index, its hashes and this ranking "
            "are the reproducibility anchor."
        ),
    }


def evaluate_retrieval(config: ExperimentConfig) -> dict:
    """Run retrieval for the pilot, score it against gold and write both files."""
    index = retrieval.load_index(config)
    model = retrieval.load_model(config)

    rows = run_retrieval(config, index, model)
    results_path = config.paths["results"] / RETRIEVAL_RESULTS_FILENAME
    hotpotqa.write_jsonl(results_path, rows)

    # Gold labels enter only now, to score a ranking that is already fixed.
    annotations = hotpotqa.load_pilot_annotations(config.processed_dir)
    scored = score_retrieval(rows, annotations)

    latencies = sorted(row["search_seconds"] for row in rows)
    manifest = index.manifest
    report = {
        "generated_at": _utc_now(),
        "status": "ok",
        "experiment_name": config.experiment_name,
        "question_count": len(rows),
        "document_count": index.size,
        "evaluation_depth": EVALUATION_DEPTH,
        "index": {
            "index_id": index.index_id,
            "model_name": manifest["model_name"],
            "model_revision": manifest["model_revision"],
            "dimension": manifest["dimension"],
            "dtype": manifest["dtype"],
            "normalised": manifest["normalised"],
            "batch_size": manifest["batch_size"],
            "device": manifest["device"],
            "text_rule": manifest["text_rule"],
            "document_order_rule": manifest["document_order_rule"],
            "ranking_rule": manifest["ranking_rule"],
            "max_seq_length": manifest["truncation"]["max_seq_length"],
            "documents_truncated": manifest["truncation"]["documents_truncated"],
            "max_token_length": manifest["truncation"]["max_token_length"],
            "build_seconds": manifest["build_seconds"],
            "built_at": manifest["built_at"],
            "corpus_sha256": manifest["corpus_sha256"],
            "library_versions": manifest["library_versions"],
        },
        "metrics": scored["metrics"],
        "metric_note": COVERAGE_NOTE,
        "latency": {
            "scope": LATENCY_SCOPE,
            "total_seconds": round(sum(latencies), 3),
            "mean_seconds": round(sum(latencies) / len(latencies), 4),
            "median_seconds": latencies[len(latencies) // 2],
            "min_seconds": latencies[0],
            "max_seconds": latencies[-1],
        },
        "reproducibility": _reproducibility_checks(config, index, model),
        "per_question": scored["per_question"],
        "output_files": {
            RETRIEVAL_RESULTS_FILENAME: str(results_path),
        },
    }

    report_path = config.paths["results"] / RETRIEVAL_REPORT_FILENAME
    hotpotqa.write_json(report_path, report)
    return report


def format_evaluation(report: dict) -> str:
    metrics = report["metrics"]
    lines = [
        f"questions        : {report['question_count']}",
        f"documents        : {report['document_count']}",
        f"index id         : {report['index']['index_id'][:16]}",
        f"model            : {report['index']['model_name']} @ {report['index']['model_revision'][:12]}",
        f"truncated docs   : {report['index']['documents_truncated']}",
        "",
        f"recall@5         : {metrics['recall_at_5']}",
        f"recall@10        : {metrics['recall_at_10']}",
        f"all-support@5    : {metrics['all_support_at_5']} "
        f"({metrics['questions_with_all_support_at_5']} of {report['question_count']} questions)",
        f"all-support@10   : {metrics['all_support_at_10']} "
        f"({metrics['questions_with_all_support_at_10']} of {report['question_count']} questions)",
        f"found at 5 (0/1/2): {metrics['supporting_documents_found_at_5']['0']}"
        f"/{metrics['supporting_documents_found_at_5']['1']}"
        f"/{metrics['supporting_documents_found_at_5']['2']}",
        f"found at 10 (0/1/2): {metrics['supporting_documents_found_at_10']['0']}"
        f"/{metrics['supporting_documents_found_at_10']['1']}"
        f"/{metrics['supporting_documents_found_at_10']['2']}",
        "",
        f"search mean/max  : {report['latency']['mean_seconds']}s / {report['latency']['max_seconds']}s",
        f"note             : {report['metric_note']}",
    ]
    return "\n".join(lines)
