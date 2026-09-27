"""Stage 12: review package, property checks and an offline main-case dry run.

Everything here is offline. The dry run prepares the first evaluator request
for each branch with `typed_rag.controller.first_grader_request`; it creates no
client and sends nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from typed_rag import controller, fault_cases, hotpotqa, nodes, retrieval
from typed_rag.config import ExperimentConfig
from typed_rag.download import sha256_file

import stage12_main_prep as prep
import stage12_faults as faults

QUESTIONS_PER_FILE = 20
REVIEW_INDEX_FILENAME = "review_index.json"
DRY_RUNS_DIRNAME = "dry_runs"

CONTEXT_ALLOWED_KEYS = {"case_id", "question_id", "question", "documents"}
DOCUMENT_ALLOWED_KEYS = {"doc_id", "title", "text"}

RESEARCH_ONLY_KEYS = (
    "condition",
    "expected_state",
    "gold_supporting_doc_ids",
    "removed_doc_ids",
    "added_doc_ids",
    "synthetic_provenance",
    "operation",
)


# --- review package -----------------------------------------------------------------


def _render_question(
    position: int,
    question_id: str,
    question: str,
    cases: list[tuple[dict, dict]],
) -> str:
    """One review section: the question and its four candidate contexts.

    Documents are printed in full and in order. Nothing is truncated and no
    document is replaced by a back reference.
    """
    lines = [
        f"## {position}. {question_id}",
        "",
        f"**Question:** {question.strip()}",
        "",
    ]
    for annotation, context in cases:
        condition = annotation["condition"]
        lines += [
            f"### {question_id} / {condition}  (case {annotation['case_id']})",
            "",
            f"- intended state (construction hypothesis, not a label): "
            f"**{annotation['expected_state']}**",
            f"- content identity: `{annotation['content_identity']}`",
            f"- review row: `{annotation['case_id']}` in `fault_reviews.jsonl` - "
            "set `observed_state` yourself; do not copy the intended state",
            "",
            "#### Context as the model would receive it",
            "",
        ]
        for order, document in enumerate(context["documents"], start=1):
            lines += [
                f"**{order}. {document['title']}**  `{document['doc_id']}`",
                "",
                "```text",
                document["text"],
                "```",
                "",
            ]
        lines += ["#### Research section (not sent to any model)", ""]
        lines.append(f"- operation: {annotation['operation']}")
        lines.append(f"- gold supporting doc_ids: {', '.join(annotation['gold_supporting_doc_ids'])}")
        lines.append(
            f"- removed: {', '.join(annotation['removed_doc_ids']) or 'none'}; "
            f"added: {', '.join(annotation['added_doc_ids']) or 'none'} "
            f"({annotation['added_doc_kind'] or 'n/a'})"
        )
        lines.append(f"- construction note: {annotation['candidate_explanation']}")
        provenance = annotation.get("synthetic_provenance")
        if provenance:
            lines += [
                "- conflicting-edit provenance:",
                f"    - source document: {provenance['source_title']} "
                f"(`{provenance['source_doc_id']}`), sentence {provenance['sentence_index']}",
                f"    - original sentence: {provenance['original_fragment']}",
                f"    - edited sentence: {provenance['edited_fragment']}",
                f"    - incompatible claims: {provenance['incompatible_claims'][0]} "
                f"|| {provenance['incompatible_claims'][1]}",
                f"    - affected property: {provenance['property']}",
                f"    - relevance to the question: {provenance['relevance_to_question']}",
                "    - drafted by the author for this study; not independently verified",
            ]
        lines.append("")
    return "\n".join(lines)


def _header(part: int, total_parts: int, count: int, manifest: dict) -> str:
    rubric = "\n".join(f"- {point}" for point in faults.RUBRIC_POINTS)
    return "\n".join(
        [
            f"# Main-study fault review - part {part} of {total_parts}",
            "",
            f"Author: {prep.AUTHOR}",
            "",
            f"Questions in this file: {count}. Candidate order is the frozen randomized order; "
            "it is not a ranking.",
            "",
            f"Index identity: `{manifest['sources']['index_id']}`",
            "",
            "## How to review",
            "",
            "For every context decide the state you actually observe - OK, PARTIAL, EMPTY or "
            "INCONSISTENT - and write it into `observed_state` in "
            "`results/main_preparation/fault_reviews.jsonl`, together with `review_status` "
            "(`approved` or `rejected`), your name in `reviewer` and an optional note.",
            "",
            "The intended state printed with each context is the hypothesis implied by the "
            "construction, not a label. A removed support document may leave alternative "
            "evidence, and a proposed contradiction may turn out to be ambiguous.",
            "",
            "Rubric points carried over from the pilot:",
            "",
            rubric,
            "",
            "Structural validation is not semantic approval. Every row starts pending.",
            "",
        ]
    )


def export_review_package(config: ExperimentConfig) -> dict:
    """Write the readable review package, split into files of at most 20 questions."""
    paths = prep.MainPaths.of(config)
    manifest = hotpotqa.read_json(paths.results / prep.FAULT_MANIFEST_FILENAME)
    annotations = hotpotqa.read_jsonl(paths.results / prep.FAULT_ANNOTATIONS_FILENAME)
    contexts = {
        c["case_id"]: c for c in hotpotqa.read_jsonl(paths.results / prep.FAULT_CONTEXTS_FILENAME)
    }

    by_question: dict[str, list[dict]] = {}
    order: list[str] = []
    for annotation in sorted(
        annotations, key=lambda a: (a["candidate_position"], fault_cases.CONDITIONS.index(a["condition"]))
    ):
        qid = annotation["question_id"]
        if qid not in by_question:
            by_question[qid] = []
            order.append(qid)
        by_question[qid].append(annotation)

    export_dir = paths.results / prep.REVIEW_EXPORT_DIRNAME
    export_dir.mkdir(parents=True, exist_ok=True)
    for stale in export_dir.glob("main_fault_review_part*.md"):
        stale.unlink()

    chunks = [order[i : i + QUESTIONS_PER_FILE] for i in range(0, len(order), QUESTIONS_PER_FILE)]
    files = []
    position = 0
    for part, chunk in enumerate(chunks, start=1):
        sections = []
        case_ids = []
        for qid in chunk:
            position += 1
            entries = [
                (annotation, contexts[annotation["case_id"]])
                for annotation in by_question[qid]
                if annotation["case_id"] in contexts
            ]
            case_ids += [annotation["case_id"] for annotation, _ in entries]
            sections.append(
                _render_question(
                    position,
                    qid,
                    entries[0][1]["question"],
                    entries,
                )
            )
        text = _header(part, len(chunks), len(chunk), manifest) + "\n".join(sections)
        path = export_dir / f"main_fault_review_part{part:02d}.md"
        path.write_text(text, encoding="utf-8", newline="\n")
        files.append(
            {
                "file": path.relative_to(config.project_root).as_posix(),
                "part": part,
                "questions": len(chunk),
                "question_ids": chunk,
                "case_ids": case_ids,
                "sha256": sha256_file(path),
            }
        )

    index = {
        "stage": prep.STAGE,
        "author": prep.AUTHOR,
        "generated_at": prep.utc_now(),
        "questions": len(order),
        "questions_per_file": QUESTIONS_PER_FILE,
        "files": files,
        "review_file": (paths.results / prep.FAULT_REVIEWS_FILENAME)
        .relative_to(config.project_root)
        .as_posix(),
        "note": (
            "the export is a rendering of fault_contexts.jsonl and fault_annotations.jsonl; "
            "labels are recorded in the review file, not in these documents"
        ),
    }
    hotpotqa.write_json(export_dir / REVIEW_INDEX_FILENAME, index)
    return index


# --- property checks ------------------------------------------------------------------


def _check(name: str, passed: bool, detail: str) -> dict:
    return {"name": name, "passed": bool(passed), "detail": detail}


def validate(config: ExperimentConfig) -> dict:
    """Focused checks on the properties stage 12 has to establish."""
    paths = prep.MainPaths.of(config)
    checks: list[dict] = []

    candidates = hotpotqa.read_json(paths.processed / prep.CANDIDATES_FILENAME)["question_ids"]
    pilot_ids = set(
        hotpotqa.read_json(config.processed_dir / hotpotqa.PILOT_IDS_FILENAME)["question_ids"]
    )
    overlap = sorted(set(candidates) & pilot_ids)
    checks.append(
        _check(
            "candidate_pool",
            len(candidates) == prep.CANDIDATE_POOL_SIZE
            and len(set(candidates)) == len(candidates)
            and not overlap,
            f"{len(candidates)} ids, {len(set(candidates))} unique, "
            f"{len(overlap)} overlapping with the 30 pilot ids",
        )
    )

    # index identity and row alignment
    index = prep.load_main_index(config)
    corpus = hotpotqa.read_jsonl(paths.processed / prep.CORPUS_FILENAME)
    expected_order = [d["doc_id"] for d in sorted(corpus, key=lambda d: d["doc_id"])]
    stored_order = [d["doc_id"] for d in index.documents]
    manifest = index.manifest
    file_hashes_ok = all(
        sha256_file(paths.index / name) == digest
        for name, digest in manifest["file_sha256"].items()
    )
    checks.append(
        _check(
            "index_identity_and_alignment",
            stored_order == expected_order
            and index.embeddings.shape[0] == len(stored_order)
            and file_hashes_ok
            and manifest["index_sha256"] == retrieval._index_identity(manifest),
            f"{index.embeddings.shape[0]} rows for {len(stored_order)} documents, "
            f"row order matches the doc_id order, stored hashes match, "
            f"index id {manifest['index_sha256'][:16]}",
        )
    )

    norms = np.linalg.norm(index.embeddings, axis=1)
    checks.append(
        _check(
            "embeddings_normalised",
            bool(np.all(np.abs(norms - 1.0) < 1e-4)),
            f"row norms in [{norms.min():.6f}, {norms.max():.6f}]",
        )
    )

    # retrieval never reads annotations
    sources = {
        "tools/stage12_main_prep.py": (config.project_root / "tools/stage12_main_prep.py"),
        "src/typed_rag/retrieval.py": (config.project_root / "src/typed_rag/retrieval.py"),
    }
    gold_tokens = (
        prep.ANNOTATIONS_FILENAME,
        hotpotqa.ANNOTATIONS_FILENAME,
        "load_pilot_annotations",
        "build_annotations",
        "supporting_doc_ids",
    )
    prep_body = sources["tools/stage12_main_prep.py"].read_text(encoding="utf-8")
    ranking_body = prep_body[
        prep_body.index("def run_main_retrieval") : prep_body.index("def measure_eligibility")
    ]
    retrieval_module = sources["src/typed_rag/retrieval.py"].read_text(encoding="utf-8")
    gold_free = not any(
        token in body for body in (ranking_body, retrieval_module) for token in gold_tokens
    )
    checks.append(
        _check(
            "retrieval_is_gold_free",
            gold_free,
            "run_main_retrieval and typed_rag.retrieval never open the annotations file; "
            "eligibility reads it only after the ranking is saved",
        )
    )

    # contexts carry no research fields
    contexts = hotpotqa.read_jsonl(paths.results / prep.FAULT_CONTEXTS_FILENAME)
    key_problems = [
        c["case_id"]
        for c in contexts
        if set(c) != CONTEXT_ALLOWED_KEYS
        or any(set(d) != DOCUMENT_ALLOWED_KEYS for d in c["documents"])
    ]
    serialised = json.dumps(contexts, ensure_ascii=False)
    leaked = [key for key in RESEARCH_ONLY_KEYS if f'"{key}"' in serialised]
    checks.append(
        _check(
            "model_facing_payload_clean",
            not key_problems and not leaked,
            f"{len(contexts)} contexts carry exactly {sorted(CONTEXT_ALLOWED_KEYS)}; "
            f"research-only keys present: {leaked or 'none'}",
        )
    )

    # deterministic contexts, identical across branches
    annotations = hotpotqa.read_jsonl(paths.results / prep.FAULT_ANNOTATIONS_FILENAME)
    by_case = {a["case_id"]: a for a in annotations}
    identity_ok = all(
        faults.content_identity(c["documents"]) == by_case[c["case_id"]]["content_identity"]
        for c in contexts
    )
    branch_free = not any(
        token in json.dumps(contexts, ensure_ascii=False) for token in ('"branch"', '"repeat"')
    )
    checks.append(
        _check(
            "contexts_deterministic_and_branch_independent",
            identity_ok and branch_free,
            "each stored context reproduces its recorded content identity; a context carries "
            "no branch or repeat, so A, B, C and D start from the identical ordered input",
        )
    )

    # replacement rules
    rows = {
        r["question_id"]: r for r in hotpotqa.read_jsonl(paths.results / prep.RETRIEVAL_FILENAME)
    }
    replacement_problems = []
    for annotation in annotations:
        if annotation["build_status"] != fault_cases.BUILD_OK:
            continue
        ranking = rows[annotation["question_id"]]["results"]
        initial = [r["doc_id"] for r in ranking[: fault_cases.CONTEXT_SIZE]]
        beyond = [r["doc_id"] for r in ranking[fault_cases.CONTEXT_SIZE :]]
        gold = annotation["gold_supporting_doc_ids"]
        final = annotation["final_doc_ids"]
        if len(final) != fault_cases.CONTEXT_SIZE or len(set(final)) != len(final):
            replacement_problems.append(f"{annotation['case_id']}: context size or duplicates")
        if annotation["condition"] in (fault_cases.CONDITION_PARTIAL, fault_cases.CONDITION_EMPTY):
            for added in annotation["added_doc_ids"]:
                if added not in beyond or added in gold or added in initial:
                    replacement_problems.append(
                        f"{annotation['case_id']}: replacement {added[:12]} is not an admissible "
                        "rank 6-10 non-gold document"
                    )
            kept = [d for d in final if d in initial]
            if [d for d in initial if d in kept] != kept:
                replacement_problems.append(f"{annotation['case_id']}: kept documents moved")
        if annotation["condition"] == fault_cases.CONDITION_INCONSISTENT:
            if not all(g in final for g in gold):
                replacement_problems.append(f"{annotation['case_id']}: a gold document is missing")
            if annotation["removed_doc_ids"] and annotation["removed_doc_ids"][0] in gold:
                replacement_problems.append(f"{annotation['case_id']}: a gold slot was overwritten")
    checks.append(
        _check(
            "replacement_rules",
            not replacement_problems,
            f"{len(annotations)} annotations checked; {len(replacement_problems)} problems"
            + ("" if not replacement_problems else f": {replacement_problems[:3]}"),
        )
    )

    fault_manifest = hotpotqa.read_json(paths.results / prep.FAULT_MANIFEST_FILENAME)
    checks.append(
        _check(
            "index_unchanged_by_construction",
            fault_manifest["sources"]["index_id"] == manifest["index_sha256"]
            and fault_manifest["sources"]["corpus_sha256"] == manifest["corpus_sha256"],
            "fault construction is bound to the same frozen index and corpus; synthetic "
            "documents are never added to the corpus or the index",
        )
    )
    synthetic_in_corpus = [
        a["case_id"]
        for a in annotations
        if a["condition"] == fault_cases.CONDITION_INCONSISTENT
        and a["build_status"] == fault_cases.BUILD_OK
        and a["added_doc_ids"]
        and a["added_doc_ids"][0] in {d["doc_id"] for d in corpus}
    ]
    checks.append(
        _check(
            "synthetic_documents_outside_corpus",
            not synthetic_in_corpus,
            f"{len(synthetic_in_corpus)} synthetic documents found in the corpus",
        )
    )

    # review export matches the structured contexts
    export_dir = paths.results / prep.REVIEW_EXPORT_DIRNAME
    index_payload = hotpotqa.read_json(export_dir / REVIEW_INDEX_FILENAME)
    export_problems = []
    context_by_case = {c["case_id"]: c for c in contexts}
    for item in index_payload["files"]:
        path = config.project_root / item["file"]
        if sha256_file(path) != item["sha256"]:
            export_problems.append(f"{item['file']}: content changed after export")
            continue
        text = path.read_text(encoding="utf-8")
        for case_id in item["case_ids"]:
            context = context_by_case[case_id]
            if case_id not in text:
                export_problems.append(f"{item['file']}: case {case_id} missing")
                continue
            for document in context["documents"]:
                if document["doc_id"] not in text or document["text"] not in text:
                    export_problems.append(
                        f"{item['file']}: document {document['doc_id'][:12]} of {case_id} "
                        "missing or truncated"
                    )
    exported_cases = sum(len(item["case_ids"]) for item in index_payload["files"])
    checks.append(
        _check(
            "review_export_matches_contexts",
            not export_problems and exported_cases == len(contexts),
            f"{exported_cases} cases exported over {len(index_payload['files'])} files; "
            f"{len(export_problems)} mismatches",
        )
    )

    # pending cases cannot enter a real experiment
    reviews = hotpotqa.read_jsonl(paths.results / prep.FAULT_REVIEWS_FILENAME)
    runnable = [r["case_id"] for r in reviews if runnable_for_real_execution(r, by_case)]
    pending = sum(1 for r in reviews if r["review_status"] == fault_cases.REVIEW_PENDING)
    matched = matched_questions(reviews, by_case)
    checks.append(
        _check(
            "pending_cases_not_runnable",
            not runnable and pending == len(reviews) and not matched,
            f"{pending} of {len(reviews)} review rows pending; {len(runnable)} cases would pass "
            f"the real-execution gate; {len(matched)} fully approved quadruplets",
        )
    )

    payload = {
        "stage": prep.STAGE,
        "checked_at": prep.utc_now(),
        "status": "ok" if all(c["passed"] for c in checks) else "failed",
        "checks": checks,
        "counts": {
            "candidates": len(candidates),
            "corpus_documents": len(corpus),
            "contexts": len(contexts),
            "review_rows": len(reviews),
            "pending_review_rows": pending,
            "approved_quadruplets": len(matched),
        },
    }
    hotpotqa.write_json(paths.results / prep.VALIDATION_FILENAME, payload)
    return payload


def runnable_for_real_execution(review: dict, annotations_by_case: dict) -> bool:
    """A case may enter a real run only when it is approved and correctly labelled."""
    annotation = annotations_by_case.get(review["case_id"])
    if annotation is None:
        return False
    return (
        review["review_status"] == fault_cases.REVIEW_APPROVED
        and review["observed_state"] == annotation["expected_state"]
        and bool(review.get("reviewer"))
        and review.get("content_identity") == annotation["content_identity"]
    )


def matched_questions(reviews: list[dict], annotations_by_case: dict) -> list[str]:
    """Questions whose four variants are all approved with the intended state."""
    per_question: dict[str, set[str]] = {}
    for review in reviews:
        if runnable_for_real_execution(review, annotations_by_case):
            annotation = annotations_by_case[review["case_id"]]
            per_question.setdefault(annotation["question_id"], set()).add(annotation["condition"])
    return sorted(
        qid
        for qid, conditions in per_question.items()
        if len(conditions) == len(fault_cases.CONDITIONS)
    )


# --- offline dry run --------------------------------------------------------------------


def dry_run_case(config: ExperimentConfig, question_id: str | None, branch: str = "D") -> dict:
    """Prepare the first evaluator request of a main case for every branch.

    Uses `controller.first_grader_request`, the same function a real run and the
    pilot batch dry run use, so what is shown is what a run would send first.
    The frozen pilot code is not modified and no client is created.
    """
    paths = prep.MainPaths.of(config)
    contexts = hotpotqa.read_jsonl(paths.results / prep.FAULT_CONTEXTS_FILENAME)
    annotations = {
        a["case_id"]: a
        for a in hotpotqa.read_jsonl(paths.results / prep.FAULT_ANNOTATIONS_FILENAME)
    }
    reviews = {
        r["case_id"]: r for r in hotpotqa.read_jsonl(paths.results / prep.FAULT_REVIEWS_FILENAME)
    }
    if question_id is None:
        question_id = contexts[0]["question_id"]
    case = next(
        (
            c
            for c in contexts
            if c["question_id"] == question_id
            and annotations[c["case_id"]]["condition"] == fault_cases.CONDITION_INCONSISTENT
        ),
        None,
    ) or next(c for c in contexts if c["question_id"] == question_id)

    review = reviews[case["case_id"]]
    gate = runnable_for_real_execution(review, annotations)

    requests = {}
    for name in config.pilot.branches:
        branch_definition = controller.get_branch(name)
        request = controller.first_grader_request(
            config, branch_definition, case["question"], case["documents"]
        )
        requests[name] = {
            "grader_node": branch_definition.grader_node,
            "request": request,
            "hashes": nodes.request_hashes(request),
        }

    run_dir = paths.results / DRY_RUNS_DIRNAME / f"{case['case_id']}_{prep.utc_now()[:10]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": prep.STAGE,
        "mode": "stage12_main_dry_run",
        "dry_run": True,
        "api_calls": 0,
        "created_at_utc": prep.utc_now(),
        "case_id": case["case_id"],
        "question_id": case["question_id"],
        "condition_of_this_case": annotations[case["case_id"]]["condition"],
        "branch": branch,
        "branches_prepared": list(config.pilot.branches),
        "review_status": review["review_status"],
        "passes_real_execution_gate": gate,
        "initial_doc_ids": [d["doc_id"] for d in case["documents"]],
        "context_sha256": fault_cases.context_hash(case["documents"]),
        "requests": requests,
        "identical_first_request_across": {
            "A_and_C": requests["A"]["hashes"] == requests["C"]["hashes"],
            "B_and_D": requests["B"]["hashes"] == requests["D"]["hashes"],
        },
        "note": (
            "offline preparation only: no client, no network, no evaluator output, no answer, "
            "no token usage and no latency are invented. A pending case cannot enter a real run."
        ),
    }
    hotpotqa.write_json(run_dir / "dry_run.json", payload)
    payload["output_dir"] = str(run_dir)
    return payload
