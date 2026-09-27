"""Stage 15 step 1-3: validate, accept and expand the semantic annotations.

Offline. Validates the supplied proposal package against the frozen stage 14
exports, archives the pending review files, writes the accepted labels into the
existing review schemas, records the acceptance, and verifies the three
supplemental post-retry mappings against the local run records.

The proposal files themselves are never modified, and neither are the frozen
plan, protocol, sample, initial reviews, prompts, schemas, controller, model
parameters, index or raw observations.

    python tools/stage15_accept.py

No provider API call is made here and no coordinate is re-run.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from typed_rag import hotpotqa
from typed_rag.config import load_config
from typed_rag.download import sha256_file

import stage14_cli
import stage14_review as review_export

STAGE = "stage15_acceptance"
REVIEWER = "Denys Yuvzhenko"
ACCEPTANCE_BASIS = (
    "researcher acceptance of supplied annotation proposals, recorded through the stage 15 "
    "instruction; not an independent second human review"
)
TIMING_STATEMENT = (
    "these annotations were accepted after main data collection, under the rubric and conventions "
    "already in force; they are not preregistered and the acceptance time is the real time of this "
    "run, not backdated"
)

MANIFEST = "main_semantic_review_manifest.json"
SUMMARY = "main_semantic_review_summary.md"
CONTEXT_PROPOSALS = "main_post_retry_review_proposals.jsonl"
ANSWER_PROPOSALS = "main_answer_grounding_review_proposals.jsonl"
LOOKUP_ADDITIONS = "main_post_retry_lookup_additions.json"

CONTEXT_CASES = "main_post_retry_contexts.jsonl"
CONTEXT_REVIEWS = "main_post_retry_reviews.jsonl"
CONTEXT_LOOKUP = "main_post_retry_lookup.json"
ANSWER_CASES = "main_answer_grounding_cases.jsonl"
ANSWER_REVIEWS = "main_answer_grounding_reviews.jsonl"
ANSWER_LOOKUP = "main_answer_grounding_lookup.json"

AUGMENTED_LOOKUP = "main_post_retry_lookup_augmented.json"
ACCEPTANCE_FILE = "stage15_acceptance.json"
ARCHIVE_DIRNAME = "stage15_archive"

STATE_LABELS = ("OK", "PARTIAL", "EMPTY", "INCONSISTENT")
SUPPORT_LABELS = ("FULLY_SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONFLICTED", "UNCLEAR")
STATUSES = ("approved", "rejected")

EXPECTED_CONTEXTS = 335
EXPECTED_ANSWERS = 347
EXPECTED_COMPLETED_RETRY_INSTANCES = 1024
EXPECTED_TECHNICAL_RETRY_INSTANCES = 3


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- validation -----------------------------------------------------------------------


def validate(results: Path) -> dict:
    manifest = hotpotqa.read_json(results / MANIFEST)
    problems: list[str] = []

    supplied_hashes = {
        name: sha256_file(results / name) for name in manifest["output_sha256"]
    }
    for name, expected in manifest["output_sha256"].items():
        if supplied_hashes[name] != expected:
            problems.append(f"{name}: content differs from the manifest hash")
    # The two review files are the only sources this stage rewrites. Before acceptance they
    # must still be the pending files of the package; afterwards they carry the accepted
    # labels, which `already_accepted` checks line by line, so a changed hash there is the
    # expected end state rather than a violation.
    rewritten = {CONTEXT_REVIEWS, ANSWER_REVIEWS}
    accepted_record = results / ACCEPTANCE_FILE
    source_hashes = {}
    for name, expected in manifest["source_sha256"].items():
        path = results / name
        if not path.is_file():
            problems.append(f"{name}: source file missing")
            continue
        source_hashes[name] = sha256_file(path)
        if source_hashes[name] == expected:
            continue
        if name in rewritten and accepted_record.is_file():
            source_hashes[name] = f"{source_hashes[name]} (accepted labels applied)"
            continue
        problems.append(f"{name}: source file changed since the package was built")

    contexts = {c["context_sha256"]: c for c in read_jsonl(results / CONTEXT_CASES)}
    cases = {c["case_sha256"]: c for c in read_jsonl(results / ANSWER_CASES)}
    context_reviews = read_jsonl(results / CONTEXT_REVIEWS)
    answer_reviews = read_jsonl(results / ANSWER_REVIEWS)
    context_proposals = read_jsonl(results / CONTEXT_PROPOSALS)
    answer_proposals = read_jsonl(results / ANSWER_PROPOSALS)

    if len(context_proposals) != EXPECTED_CONTEXTS or len(
        {p["context_sha256"] for p in context_proposals}
    ) != EXPECTED_CONTEXTS:
        problems.append(
            f"{len(context_proposals)} context proposals "
            f"({len({p['context_sha256'] for p in context_proposals})} unique), expected {EXPECTED_CONTEXTS}"
        )
    if len(answer_proposals) != EXPECTED_ANSWERS or len(
        {p["case_sha256"] for p in answer_proposals}
    ) != EXPECTED_ANSWERS:
        problems.append(
            f"{len(answer_proposals)} answer proposals "
            f"({len({p['case_sha256'] for p in answer_proposals})} unique), expected {EXPECTED_ANSWERS}"
        )
    if {p["context_sha256"] for p in context_proposals} != {r["context_sha256"] for r in context_reviews}:
        problems.append("context proposals are not one-to-one with their review templates")
    if {p["case_sha256"] for p in answer_proposals} != {r["case_sha256"] for r in answer_reviews}:
        problems.append("answer proposals are not one-to-one with their review templates")
    if {p["context_sha256"] for p in context_proposals} != set(contexts):
        problems.append("context proposals do not match the exported canonical context hashes")
    if {p["case_sha256"] for p in answer_proposals} != set(cases):
        problems.append("answer proposals do not match the exported canonical case hashes")

    for proposal in context_proposals:
        case = contexts.get(proposal["context_sha256"])
        label = proposal["proposed_observed_state"]
        if label not in STATE_LABELS:
            problems.append(f"{proposal['review_id']}: invalid state {label!r}")
        if proposal["proposed_review_status"] not in STATUSES:
            problems.append(f"{proposal['review_id']}: invalid review status")
        if not (proposal.get("note") or "").strip():
            problems.append(f"{proposal['review_id']}: empty note")
        if case and proposal["question_id"] != case["question_id"]:
            problems.append(f"{proposal['review_id']}: question_id differs from the exported case")
        if case and not set(proposal.get("evidence_doc_ids") or []) <= {
            d["doc_id"] for d in case["documents"]
        }:
            problems.append(f"{proposal['review_id']}: evidence doc_id outside its context")

    for proposal in answer_proposals:
        case = cases.get(proposal["case_sha256"])
        for field in ("proposed_answer_support", "proposed_explanation_support"):
            if proposal[field] not in SUPPORT_LABELS:
                problems.append(f"{proposal['review_id']}: invalid {field} {proposal[field]!r}")
        if proposal["proposed_review_status"] not in STATUSES:
            problems.append(f"{proposal['review_id']}: invalid review status")
        if not (proposal.get("note") or "").strip():
            problems.append(f"{proposal['review_id']}: empty note")
        if case and proposal["question_id"] != case["question_id"]:
            problems.append(f"{proposal['review_id']}: question_id differs from the exported case")
        if case and not set(proposal.get("evidence_doc_ids") or []) <= {
            d["doc_id"] for d in case["documents"]
        }:
            problems.append(f"{proposal['review_id']}: evidence doc_id outside its case context")

    return {
        "problems": problems,
        "manifest": manifest,
        "supplied_hashes": supplied_hashes,
        "source_hashes": source_hashes,
        "contexts": contexts,
        "cases": cases,
        "context_proposals": context_proposals,
        "answer_proposals": answer_proposals,
        "context_reviews": context_reviews,
        "answer_reviews": answer_reviews,
        "label_counts": {
            "post_retry_states": dict(Counter(p["proposed_observed_state"] for p in context_proposals)),
            "answer_support": dict(Counter(p["proposed_answer_support"] for p in answer_proposals)),
            "explanation_support": dict(
                Counter(p["proposed_explanation_support"] for p in answer_proposals)
            ),
        },
    }


# --- supplemental lookup ----------------------------------------------------------------


def verify_additions(config, results: Path, contexts: dict) -> dict:
    """Check the three supplemental mappings against the local run records."""
    from typed_rag import pilot, rag_run

    manifest, _ = __import__("typed_rag.main_study", fromlist=["x"]).load_plan(config)
    batch_dir = stage14_cli.batch_dir_for(manifest["plan_id"])
    additions = hotpotqa.read_json(results / LOOKUP_ADDITIONS)

    verified: list[dict] = []
    unresolved: list[dict] = []
    for item in additions["additions"]:
        run_dir = batch_dir / pilot.RUNS_DIRNAME / item["run_id"]
        context_path = run_dir / rag_run.CONTEXT_FILENAME
        run_path = run_dir / "run.json"
        reasons = []
        if not context_path.is_file() or not run_path.is_file():
            reasons.append("local run records missing")
        else:
            record = hotpotqa.read_json(context_path)
            result = hotpotqa.read_json(run_path)
            entries = [e for e in record["contexts"] if e["iteration"] == item["iteration"]]
            if not entries:
                reasons.append(f"no context at iteration {item['iteration']}")
            else:
                entry = entries[0]
                documents = [
                    {"doc_id": d["doc_id"], "title": d["title"], "text": d["text"]}
                    for d in entry["documents"]
                ]
                exported = contexts.get(item["context_sha256"])
                digest = review_export.context_hash(record["question"], documents)
                if exported is None:
                    reasons.append("context_sha256 is not an exported reviewed context")
                else:
                    if record["question_id"] != exported["question_id"] or record["question"] != exported["question"]:
                        reasons.append("question identity differs from the exported context")
                    if [
                        (d["doc_id"], d["title"], d["text"]) for d in documents
                    ] != [
                        (d["doc_id"], d["title"], d["text"]) for d in exported["documents"]
                    ]:
                        reasons.append("ordered documents or their content differ from the exported context")
                if digest != item["context_sha256"]:
                    reasons.append("recomputed context identity differs from the supplement")
                if entry.get("context_sha256") != item.get("run_final_context_sha256"):
                    reasons.append("run-level context hash differs from the supplement")
                if result.get("status") != "technical_failure":
                    reasons.append(f"run status is {result.get('status')!r}, not a technical failure")
        target = unresolved if reasons else verified
        target.append({**item, "verification_problems": reasons})

    original = hotpotqa.read_json(results / CONTEXT_LOOKUP)
    completed_instances = sum(len(v) for v in original["by_case"].values())
    augmented = {
        "stage": STAGE,
        "generated_at_utc": utc_now(),
        "basis": (
            "the original completed-run lookup is unchanged; this augmented file adds the verified "
            "technical-failure mappings with an explicit scope field"
        ),
        "rule": original["rule"],
        "original_lookup_sha256": sha256_file(results / CONTEXT_LOOKUP),
        "scopes": {
            "completed": "post-retry contexts of completed runs (semantic outcomes analysed)",
            "technical_failure": (
                "post-retry contexts of runs that failed technically after retrieval; retrieval "
                "coverage only. These runs add no completed outcome, no recovery success and no "
                "answer, and stay technically missing in the semantic analysis"
            ),
        },
        "counts": {
            "distinct_reviewed_contexts": len(contexts),
            "completed_retry_instances": completed_instances,
            "technical_failure_retry_instances": len(verified),
            "total_retry_instances": completed_instances + len(verified),
            "unresolved_supplemental_mappings": len(unresolved),
        },
        "by_case": {},
        "unresolved": unresolved,
    }
    for case_hash, instances in original["by_case"].items():
        augmented["by_case"][case_hash] = [
            {**instance, "scope": "completed"} for instance in instances
        ]
    for item in verified:
        augmented["by_case"].setdefault(item["context_sha256"], []).append(
            {
                "run_id": item["run_id"],
                "coordinate": item["coordinate"],
                "iteration": item["iteration"],
                "query_kind": item["query_kind"],
                "branch": item["branch"],
                "condition": item["condition"],
                "repeat": item["repeat"],
                "scope": "technical_failure",
                "record_status": item["record_status"],
            }
        )
    hotpotqa.write_json(results / AUGMENTED_LOOKUP, augmented)
    return {
        "verified": verified,
        "unresolved": unresolved,
        "counts": augmented["counts"],
        "augmented_sha256": sha256_file(results / AUGMENTED_LOOKUP),
        "reconciled": (
            completed_instances == EXPECTED_COMPLETED_RETRY_INSTANCES
            and len(verified) == EXPECTED_TECHNICAL_RETRY_INSTANCES
            and len(contexts) == EXPECTED_CONTEXTS
        ),
    }


# --- acceptance ---------------------------------------------------------------------------


def already_accepted(results: Path, validation: dict) -> bool:
    """True when the review files already carry exactly these accepted labels."""
    path = results / ACCEPTANCE_FILE
    if not path.is_file():
        return False
    context_reviews = {r["context_sha256"]: r for r in read_jsonl(results / CONTEXT_REVIEWS)}
    answer_reviews = {r["case_sha256"]: r for r in read_jsonl(results / ANSWER_REVIEWS)}
    for proposal in validation["context_proposals"]:
        row = context_reviews.get(proposal["context_sha256"])
        if not row or row.get("observed_state") != proposal["proposed_observed_state"]:
            return False
        if row.get("reviewer") != REVIEWER or row.get("review_status") != proposal["proposed_review_status"]:
            return False
    for proposal in validation["answer_proposals"]:
        row = answer_reviews.get(proposal["case_sha256"])
        if not row or row.get("answer_support") != proposal["proposed_answer_support"]:
            return False
        if row.get("explanation_support") != proposal["proposed_explanation_support"]:
            return False
        if row.get("reviewer") != REVIEWER or row.get("review_status") != proposal["proposed_review_status"]:
            return False
    return True


def apply_acceptance(results: Path, validation: dict) -> dict:
    archive_dir = results / ARCHIVE_DIRNAME
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = {}
    for name in (CONTEXT_REVIEWS, ANSWER_REVIEWS):
        digest = sha256_file(results / name)
        target = archive_dir / f"{Path(name).stem}_pending_{digest[:12]}.jsonl"
        shutil.copy2(results / name, target)
        archived[name] = {
            "archived_to": target.relative_to(results.parent).as_posix(),
            "sha256": digest,
        }

    context_by_hash = {p["context_sha256"]: p for p in validation["context_proposals"]}
    answer_by_hash = {p["case_sha256"]: p for p in validation["answer_proposals"]}

    context_rows = []
    for row in validation["context_reviews"]:
        proposal = context_by_hash[row["context_sha256"]]
        context_rows.append(
            {
                "context_sha256": row["context_sha256"],
                "observed_state": proposal["proposed_observed_state"],
                "review_status": proposal["proposed_review_status"],
                "reviewer": REVIEWER,
                "note": proposal["note"],
            }
        )
    answer_rows = []
    for row in validation["answer_reviews"]:
        proposal = answer_by_hash[row["case_sha256"]]
        answer_rows.append(
            {
                "case_sha256": row["case_sha256"],
                "answer_support": proposal["proposed_answer_support"],
                "explanation_support": proposal["proposed_explanation_support"],
                "review_status": proposal["proposed_review_status"],
                "reviewer": REVIEWER,
                "note": proposal["note"],
            }
        )
    if any(set(r) != {"context_sha256", "observed_state", "review_status", "reviewer", "note"} for r in context_rows):
        raise SystemExit("context review schema changed; refusing to write")
    if any(
        set(r) != {"case_sha256", "answer_support", "explanation_support", "review_status", "reviewer", "note"}
        for r in answer_rows
    ):
        raise SystemExit("answer review schema changed; refusing to write")

    hotpotqa.write_jsonl(results / CONTEXT_REVIEWS, context_rows)
    hotpotqa.write_jsonl(results / ANSWER_REVIEWS, answer_rows)
    return {"archived": archived, "context_rows": len(context_rows), "answer_rows": len(answer_rows)}


def main() -> int:
    config = load_config()
    results = config.paths["results"]
    validation = validate(results)
    if validation["problems"]:
        for problem in validation["problems"][:20]:
            print(f"PROBLEM {problem}")
        raise SystemExit(f"{len(validation['problems'])} validation problems; nothing was accepted")

    accepted_before = already_accepted(results, validation)
    if accepted_before:
        record = hotpotqa.read_json(results / ACCEPTANCE_FILE)
        print("acceptance already complete and identical; review files left untouched")
        print(f"accepted_at_utc: {record['accepted_at_utc']}")
        applied = {"archived": record["archived_inputs"], "context_rows": EXPECTED_CONTEXTS, "answer_rows": EXPECTED_ANSWERS}
    else:
        applied = apply_acceptance(results, validation)

    additions = verify_additions(config, results, validation["contexts"])

    record = {
        "stage": STAGE,
        "accepted_at_utc": (
            hotpotqa.read_json(results / ACCEPTANCE_FILE)["accepted_at_utc"] if accepted_before else utc_now()
        ),
        "recorded_at_utc": utc_now(),
        "reviewer": REVIEWER,
        "acceptance_basis": ACCEPTANCE_BASIS,
        "timing_statement": TIMING_STATEMENT,
        "independent_human_review": False,
        "preregistered": False,
        "interpretations_accepted": (
            "the readings listed in results/main_semantic_review_summary.md, section 'Decisions "
            "worth confirming first', are accepted as supplied"
        ),
        "counts": {
            "context_reviews_accepted": applied["context_rows"],
            "answer_reviews_accepted": applied["answer_rows"],
            **validation["label_counts"],
        },
        "accepted_proposal_hashes": validation["supplied_hashes"],
        "source_hashes_verified": validation["source_hashes"],
        "archived_inputs": applied["archived"],
        "accepted_output_hashes": {
            CONTEXT_REVIEWS: sha256_file(results / CONTEXT_REVIEWS),
            ANSWER_REVIEWS: sha256_file(results / ANSWER_REVIEWS),
            AUGMENTED_LOOKUP: additions["augmented_sha256"],
        },
        "post_retry_supplement": {
            "verified": [item["run_id"] for item in additions["verified"]],
            "unresolved": [item["run_id"] for item in additions["unresolved"]],
            "counts": additions["counts"],
            "reconciled": additions["reconciled"],
            "constraint": (
                "these three runs stay technically missing; the supplement concerns retrieval "
                "coverage only and adds no completed outcome"
            ),
        },
        "provider_calls": 0,
        "coordinate_reruns": 0,
        "proposal_files_unchanged": True,
    }
    hotpotqa.write_json(results / ACCEPTANCE_FILE, record)

    print(f"context reviews accepted : {applied['context_rows']}")
    print(f"answer reviews accepted  : {applied['answer_rows']}")
    print(f"label counts             : {validation['label_counts']}")
    print(f"supplement verified      : {len(additions['verified'])} unresolved {len(additions['unresolved'])}")
    print(f"retry instances          : {additions['counts']}")
    print(f"accepted_at_utc          : {record['accepted_at_utc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
