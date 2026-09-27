"""Integration check for stage 3: the real index and the real model.

Not part of the unittest suite on purpose - it loads the embedding model and
takes seconds rather than milliseconds. The unittest files stay model-free.

Run with:  python tests/integration_check.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from typed_rag import hotpotqa, retrieval
from typed_rag.config import load_config
from typed_rag.download import sha256_file

CHECKS: list[tuple[str, bool, str]] = []


def record(label: str, passed: bool, detail: str = "") -> None:
    CHECKS.append((label, passed, detail))
    print(f"{'PASS' if passed else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))


def run_cli(config_path: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "typed_rag", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(config_path.parent.parent),
    )


def main() -> int:
    config = load_config()
    index = retrieval.load_index(config)
    corpus = hotpotqa.load_pilot_corpus(config.processed_dir)

    # --- matrix and document correspondence ---
    record("matrix rows == corpus documents", index.embeddings.shape[0] == len(corpus),
           f"{index.embeddings.shape[0]} vs {len(corpus)}")
    doc_ids = [document["doc_id"] for document in index.documents]
    record("doc_ids unique", len(set(doc_ids)) == len(doc_ids))
    record("documents stored in ascending doc_id order", doc_ids == sorted(doc_ids))
    record("index documents equal corpus documents",
           {document["doc_id"] for document in corpus} == set(doc_ids))

    # --- vector sanity ---
    record("embeddings are float32", index.embeddings.dtype == np.float32,
           str(index.embeddings.dtype))
    record("embeddings finite", bool(np.isfinite(index.embeddings).all()))
    norms = np.linalg.norm(index.embeddings, axis=1)
    record("unit norm within tolerance", bool(np.allclose(norms, 1.0, atol=1e-5)),
           f"min {norms.min():.6f} max {norms.max():.6f}")

    # --- ranking stability with the real model ---
    model = retrieval.load_model(config)
    questions = hotpotqa.load_pilot_questions(config.processed_dir)
    probe = questions[0]["question"]

    first = retrieval.search(index, model, probe, 10)
    second = retrieval.search(index, model, probe, 10)
    record("repeated query: same doc_ids and order",
           [hit.doc_id for hit in first] == [hit.doc_id for hit in second])
    record("repeated query: identical scores",
           [hit.score for hit in first] == [hit.score for hit in second])

    reloaded = retrieval.load_index(config)
    third = retrieval.search(reloaded, model, probe, 10)
    record("reloaded index: same ranking",
           [hit.doc_id for hit in first] == [hit.doc_id for hit in third])
    record("reloaded index: identical scores",
           [hit.score for hit in first] == [hit.score for hit in third])

    scores = [hit.score for hit in first]
    record("scores descending", scores == sorted(scores, reverse=True))
    record("scores finite", all(np.isfinite(score) for score in scores))

    record("top_k above corpus size returns whole corpus",
           len(retrieval.search(index, model, probe, index.size + 50)) == index.size)

    # --- search must not depend on gold annotations ---
    annotations = config.processed_dir / hotpotqa.ANNOTATIONS_FILENAME
    hidden = annotations.with_suffix(".jsonl.hidden")
    annotations.rename(hidden)
    try:
        without_gold = retrieval.search(retrieval.load_index(config), model, probe, 10)
        record("search works with annotations file absent",
               [hit.doc_id for hit in without_gold] == [hit.doc_id for hit in first])
    finally:
        hidden.rename(annotations)
    record("annotations restored", annotations.is_file())

    # --- stale index detection on a real corpus change ---
    corpus_path = retrieval.corpus_path(config)
    backup = corpus_path.with_suffix(".jsonl.backup")
    original_sha = sha256_file(corpus_path)
    shutil.copy2(corpus_path, backup)
    try:
        with corpus_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"doc_id": "0" * 64, "title": "x", "sentences": [],
                                     "text": ""}, sort_keys=True) + "\n")
        result = run_cli(config.config_path, "--search", probe)
        record("changed corpus makes search report a stale index",
               result.returncode == 7 and "stale" in (result.stdout + result.stderr).lower(),
               f"exit {result.returncode}")
    finally:
        shutil.move(str(backup), str(corpus_path))
    record("corpus restored byte-identically", sha256_file(corpus_path) == original_sha)

    # --- simple commands must not load the model ---
    probe_script = (
        "import sys; from typed_rag.__main__ import main; "
        "main(['--data-summary']); "
        "sys.exit(1 if any(name.startswith(('torch','sentence_transformers','transformers')) "
        "for name in sys.modules) else 0)"
    )
    light = subprocess.run([sys.executable, "-c", probe_script], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(config.project_root))
    record("--data-summary does not import the model stack", light.returncode == 0)

    failed = [label for label, passed, _ in CHECKS if not passed]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("failed: " + "; ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
