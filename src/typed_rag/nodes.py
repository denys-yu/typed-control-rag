"""The LLM nodes: context graders, query rewriter and answer generator.

This module is the single home of the output schemas, the prompt files, the
request payloads sent to the Responses API and the local validation of what
comes back. It never talks to the network and never reads gold annotations:
a node sees the question text, the retrieved documents and (for the stage 5
graders) the retry-budget state, nothing else. No node ever sees the branch
name or whether code will enforce the policy.

Stage 4 nodes: grade_binary (binary verdict only) and answer (shared generator).
Stage 5 nodes: grade_binary_action and grade_typed_action (verdict plus a
proposed action in one structured result, so no separate router call is
needed) and rewrite_query (one rewritten search query for the single retry).

Validation here establishes structural correctness and referential
correctness (every cited doc_id exists in the context). It does not establish
that an answer is true or that the cited documents actually support it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from typed_rag.config import ExperimentConfig

NODE_GRADE = "grade_binary"
NODE_ANSWER = "answer"
NODE_GRADE_BINARY_ACTION = "grade_binary_action"
NODE_GRADE_TYPED_ACTION = "grade_typed_action"
NODE_REWRITE = "rewrite_query"
NODE_NAMES = (NODE_GRADE, NODE_ANSWER)  # stage 4 diagnostic pair
ALL_NODE_NAMES = (
    NODE_GRADE,
    NODE_ANSWER,
    NODE_GRADE_BINARY_ACTION,
    NODE_GRADE_TYPED_ACTION,
    NODE_REWRITE,
)

DECISION_ANSWER = "answer"
DECISION_ABSTAIN = "abstain"

# Controller vocabulary shared by every branch; the binary rule set simply
# never produces "escalate" - that is part of its definition, not a restriction
# of the schema.
ACTION_ANSWER = "answer"
ACTION_RETRY = "retry"
ACTION_ABSTAIN = "abstain"
ACTION_ESCALATE = "escalate"
ACTIONS = (ACTION_ANSWER, ACTION_RETRY, ACTION_ABSTAIN, ACTION_ESCALATE)

STATE_OK = "OK"
STATE_EMPTY = "EMPTY"
STATE_PARTIAL = "PARTIAL"
STATE_INCONSISTENT = "INCONSISTENT"
STATES = (STATE_OK, STATE_EMPTY, STATE_PARTIAL, STATE_INCONSISTENT)

# Validation outcome labels; a node call is "ok" only when the outcome is VALID.
VALID = "valid"
JSON_ERROR = "json_error"
SCHEMA_ERROR = "schema_error"
UNKNOWN_EVIDENCE = "unknown_evidence_doc_ids"
INCONSISTENT_DECISION = "inconsistent_decision"
EMPTY_REWRITE = "empty_rewritten_query"


# --- output schemas (defined once, used for the API and for local validation) ---


class GradeOutput(BaseModel):
    """Binary sufficiency judgement. No four-state typing at this stage."""

    model_config = ConfigDict(extra="forbid", strict=True)

    sufficient: bool
    evidence_doc_ids: list[str]
    reason: str


class AnswerOutput(BaseModel):
    """Answer or abstention, with citations restricted to the given context."""

    model_config = ConfigDict(extra="forbid", strict=True)

    decision: Literal["answer", "abstain"]
    answer: str
    evidence_doc_ids: list[str]
    reason: str


class BinaryGradeActionOutput(BaseModel):
    """Stage 5 binary grader: verdict plus proposed action in one result."""

    model_config = ConfigDict(extra="forbid", strict=True)

    sufficient: bool
    proposed_action: Literal["answer", "retry", "abstain", "escalate"]
    evidence_doc_ids: list[str]
    reason: str


class TypedGradeActionOutput(BaseModel):
    """Stage 5 typed grader: one of four states plus proposed action."""

    model_config = ConfigDict(extra="forbid", strict=True)

    state: Literal["OK", "EMPTY", "PARTIAL", "INCONSISTENT"]
    proposed_action: Literal["answer", "retry", "abstain", "escalate"]
    evidence_doc_ids: list[str]
    reason: str


class RewriteOutput(BaseModel):
    """One rewritten search query for the single retry."""

    model_config = ConfigDict(extra="forbid", strict=True)

    rewritten_query: str
    reason: str


@dataclass(frozen=True)
class NodeSpec:
    name: str
    prompt_filename: str
    schema_name: str
    output_model: type[BaseModel]


NODE_SPECS: dict[str, NodeSpec] = {
    NODE_GRADE: NodeSpec(NODE_GRADE, "grade_binary.txt", "context_grade", GradeOutput),
    NODE_ANSWER: NodeSpec(NODE_ANSWER, "answer.txt", "grounded_answer", AnswerOutput),
    NODE_GRADE_BINARY_ACTION: NodeSpec(
        NODE_GRADE_BINARY_ACTION,
        "grade_binary_action.txt",
        "context_grade_binary_action",
        BinaryGradeActionOutput,
    ),
    NODE_GRADE_TYPED_ACTION: NodeSpec(
        NODE_GRADE_TYPED_ACTION,
        "grade_typed_action.txt",
        "context_grade_typed_action",
        TypedGradeActionOutput,
    ),
    NODE_REWRITE: NodeSpec(NODE_REWRITE, "rewrite_query.txt", "query_rewrite", RewriteOutput),
}


def json_schema(node: str) -> dict:
    """Strict JSON Schema for a node, derived from its Pydantic model.

    `extra="forbid"` yields `additionalProperties: false`, and fields without
    defaults are all required - exactly what strict Structured Outputs need.
    """
    schema = NODE_SPECS[node].output_model.model_json_schema()
    if schema.get("additionalProperties") is not False:
        raise ValueError(f"Schema for {node} must forbid additional properties")
    if set(schema.get("required", [])) != set(schema["properties"]):
        raise ValueError(f"Schema for {node} must require every property")
    return schema


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(payload: object) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(canonical)


# --- prompts and context text ------------------------------------------------------


def prompt_path(config: ExperimentConfig, node: str) -> Path:
    return config.prompts_dir / NODE_SPECS[node].prompt_filename


def load_prompt(config: ExperimentConfig, node: str) -> str:
    path = prompt_path(config, node)
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Prompt file is empty: {path}")
    return text


def format_context(question: str, documents: list[dict]) -> str:
    """User-turn text: the question and the documents in retrieval order.

    Full doc_id, title and full text are passed. Scores are deliberately left
    out: they stay in the retrieval log and must not act as a sufficiency hint.
    """
    lines = [f"Question: {question}", "", "Retrieved documents (in retrieval order):"]
    for position, document in enumerate(documents, start=1):
        lines += [
            "",
            f"[Document {position}]",
            f"doc_id: {document['doc_id']}",
            f"title: {document['title']}",
            "text:",
            document["text"],
        ]
    return "\n".join(lines)


def format_grader_input(
    question: str, documents: list[dict], retries_used: int, max_retries: int
) -> str:
    """Stage 5 grader input: question, context and the retry-budget state.

    The branch name and the enforcement mode are deliberately absent.
    """
    remaining = max(max_retries - retries_used, 0)
    lines = [
        format_context(question, documents),
        "",
        f"Retry budget: {retries_used} retry used of {max_retries}; {remaining} remaining.",
    ]
    return "\n".join(lines)


def format_rewrite_input(question: str, documents: list[dict], assessment: dict) -> str:
    """Rewriter input: original question, current documents, grader assessment.

    `assessment` holds the grader's verdict (sufficient or state) and reason;
    no gold data, no answer.
    """
    verdict = "; ".join(f"{key}: {value}" for key, value in assessment.items())
    lines = [
        format_context(question, documents),
        "",
        f"Grader assessment of the documents above: {verdict}",
        "",
        "Write one new search query for the same document collection that targets the missing evidence.",
    ]
    return "\n".join(lines)


# --- request construction --------------------------------------------------------


def build_request_from_text(config: ExperimentConfig, node: str, user_text: str) -> dict:
    """Exact keyword arguments for `client.responses.create`.

    One independent call: no previous_response_id, no tools, no streaming,
    no server-side storage.
    """
    spec = NODE_SPECS[node]
    llm = config.llm
    return {
        "model": llm.model,
        "instructions": load_prompt(config, node),
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            }
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": spec.schema_name,
                "schema": json_schema(node),
                "strict": True,
            }
        },
        "temperature": llm.temperature,
        "max_output_tokens": llm.max_output_tokens,
        "store": llm.store,
    }


def build_request(config: ExperimentConfig, node: str, question: str, documents: list[dict]) -> dict:
    """Request whose user turn is the question plus the documents (stage 4 nodes)."""
    return build_request_from_text(config, node, format_context(question, documents))


def request_hashes(request: dict) -> dict:
    """Hashes of the instruction prompt, the schema and the user input actually sent."""
    return {
        "prompt_sha256": sha256_text(request["instructions"]),
        "schema_sha256": sha256_json(request["text"]["format"]["schema"]),
        "input_sha256": sha256_text(request["input"][0]["content"][0]["text"]),
    }


# --- validation ------------------------------------------------------------------


@dataclass
class ValidationResult:
    status: str
    errors: list[str] = field(default_factory=list)
    output: dict | None = None

    @property
    def ok(self) -> bool:
        return self.status == VALID

    def as_dict(self) -> dict:
        return {"status": self.status, "errors": list(self.errors)}


def validate_output(node: str, output_text: str, context_doc_ids: list[str]) -> ValidationResult:
    """Parse and check a node's output text. Never repairs, never retries."""
    try:
        parsed = json.loads(output_text)
    except ValueError as exc:
        return ValidationResult(JSON_ERROR, [f"output is not valid JSON: {exc}"])

    try:
        model = NODE_SPECS[node].output_model.model_validate(parsed)
    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
            for error in exc.errors()
        ]
        return ValidationResult(SCHEMA_ERROR, errors)

    output = model.model_dump()
    errors: list[str] = []
    status = VALID

    if node == NODE_REWRITE:
        if not output["rewritten_query"].strip():
            return ValidationResult(EMPTY_REWRITE, ["rewritten_query is empty"], output)
        return ValidationResult(VALID, [], output)

    known = set(context_doc_ids)
    unknown = [doc_id for doc_id in output["evidence_doc_ids"] if doc_id not in known]
    if unknown:
        status = UNKNOWN_EVIDENCE
        errors.append(f"evidence_doc_ids not in context: {', '.join(unknown)}")

    if node == NODE_ANSWER:
        decision_errors = []
        if output["decision"] == DECISION_ANSWER:
            if not output["answer"].strip():
                decision_errors.append("decision is 'answer' but answer is empty")
            if not output["evidence_doc_ids"]:
                decision_errors.append("decision is 'answer' but evidence_doc_ids is empty")
        elif output["answer"] != "":
            decision_errors.append("decision is 'abstain' but answer is not empty")
        if decision_errors:
            if status == VALID:
                status = INCONSISTENT_DECISION
            errors.extend(decision_errors)

    return ValidationResult(status, errors, output)
