"""Materialise the hand-drafted INCONSISTENT edits into the stage 12 edits file.

The author writes one draft per eligible question: which gold supporting
document and which sentence to change, the replacement sentence, the two
incompatible claims, the affected property and the relevance to the question.
This script copies the *original* sentence out of the main corpus rather than
having it retyped, checks that the target really is a gold supporting document
of that question, and writes `config/main_inconsistent_edits.json` in the same
schema as the stage 6 edits file.

It generates no text of its own: every edited sentence comes from the drafts.
No API call is made here.

    python tools/stage12_build_edits.py <drafts.json> [<drafts.json> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config

import stage12_main_prep as prep

DRAFT_FIELDS = (
    "question_id",
    "target_title",
    "sentence_index",
    "edited_sentence",
    "claim_original",
    "claim_edited",
    "property",
    "relevance",
)


def build(draft_paths: list[Path]) -> dict:
    config = load_config()
    paths = prep.MainPaths.of(config)
    annotations = {
        a["question_id"]: a
        for a in hotpotqa.read_jsonl(paths.processed / prep.ANNOTATIONS_FILENAME)
    }
    corpus = {
        d["doc_id"]: d for d in hotpotqa.read_jsonl(paths.processed / prep.CORPUS_FILENAME)
    }
    eligibility = hotpotqa.read_json(paths.results / prep.ELIGIBILITY_FILENAME)
    eligible = set(eligibility["eligible_question_ids"])

    drafts: list[dict] = []
    for path in draft_paths:
        drafts.extend(json.loads(path.read_text(encoding="utf-8")))

    edits: dict[str, dict] = {}
    problems: list[str] = []
    for draft in drafts:
        missing = [field for field in DRAFT_FIELDS if field not in draft]
        if missing:
            problems.append(f"{draft.get('question_id')}: missing draft fields {missing}")
            continue
        qid = draft["question_id"]
        if qid not in eligible:
            problems.append(f"{qid}: not a technically eligible question")
            continue
        if qid in edits:
            problems.append(f"{qid}: more than one draft for the same question")
            continue

        gold = annotations[qid]
        targets = [
            corpus[doc_id]
            for doc_id in gold["supporting_doc_ids"]
            if corpus[doc_id]["title"] == draft["target_title"]
        ]
        if len(targets) != 1:
            problems.append(
                f"{qid}: {len(targets)} gold supporting documents match title "
                f"{draft['target_title']!r}"
            )
            continue
        target = targets[0]
        index = draft["sentence_index"]
        if not 0 <= index < len(target["sentences"]):
            problems.append(f"{qid}: sentence_index {index} out of range for the target document")
            continue
        original = target["sentences"][index]
        if draft["edited_sentence"].strip() == original.strip():
            problems.append(f"{qid}: the edited sentence is identical to the original")
            continue

        edits[qid] = {
            "question_id": qid,
            "target_title": draft["target_title"],
            "target_doc_id": target["doc_id"],
            "sentence_index": index,
            "original_sentence": original,
            "edited_sentence": draft["edited_sentence"],
            "claim_original": draft["claim_original"],
            "claim_edited": draft["claim_edited"],
            "property": draft["property"],
            "relevance": draft["relevance"],
        }

    payload = {
        "stage": prep.STAGE,
        "author": prep.AUTHOR,
        "schema": "same fields as config/inconsistent_edits.json (stage 6)",
        "provenance": (
            "each edit is hand-drafted by the author against the gold supporting sentence; "
            "the original sentence is copied from data/processed/main/main_corpus.jsonl, only "
            "the replacement sentence and the claim description are authored. No LLM produced "
            "these edits and they are not independently verified."
        ),
        "model_facing_text_rule": (
            "the edited sentence contains no instruction to the model and no label such as "
            "'synthetic' or 'contradiction'; provenance lives in the research annotations only"
        ),
        "count": len(edits),
        "edits": edits,
    }
    out_path = config.project_root / prep.EDITS_RELPATH
    hotpotqa.write_json(out_path, payload)
    return {"path": out_path, "count": len(edits), "problems": problems, "drafts": len(drafts)}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    result = build([Path(item) for item in argv])
    print(f"drafts read : {result['drafts']}")
    print(f"edits written: {result['count']} -> {result['path']}")
    for problem in result["problems"]:
        print(f"  problem: {problem}")
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
