"""OpenAI access for the LLM nodes: key resolution, client, one-call transport.

Only this module imports the `openai` SDK. Everything above it works with a
`Transport` object exposing `send(request) -> TransportResult`, so tests
substitute a fake transport and never reach the network.

Design constraints of stage 4:
* every call is independent (no previous_response_id, no tools, no streaming);
* max_retries=0 in the SDK client - a failed call is recorded, not repeated;
* the API key is never logged, printed or written anywhere.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from typed_rag.config import ExperimentConfig

# --- error kinds recorded in calls.jsonl -------------------------------------------
# Transport-level outcomes (the HTTP call itself):
TRANSPORT_OK = "ok"
AUTHENTICATION = "authentication"
RATE_LIMIT_OR_QUOTA = "rate_limit_or_quota"
MODEL_UNAVAILABLE = "model_unavailable"
PERMISSION_DENIED = "permission_denied"
TIMEOUT = "timeout"
CONNECTION = "connection"
BAD_REQUEST = "bad_request"
API_STATUS = "api_status_error"
UNEXPECTED = "unexpected_exception"
# Response-level outcomes (a response arrived but carries no usable JSON):
PROVIDER_REFUSAL = "provider_refusal"
INCOMPLETE_RESPONSE = "incomplete_response"
RESPONSE_FAILED = "response_failed"
EMPTY_OUTPUT = "empty_output"
# Local outcome (stage 7): the batch API-call budget forbade the attempt, so
# no request was sent. Distinct from every provider-side failure.
API_BUDGET_STOP = "api_budget_stop"

KEY_CONFIGURED = "configured"
KEY_MISSING = "missing"


class MissingAPIKeyError(Exception):
    """Raised before any client is created when no non-empty key is available."""


class APIBudgetStop(Exception):
    """Raised by a budgeted transport instead of sending when no attempts remain."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# --- API key ---------------------------------------------------------------------


def resolve_api_key(config: ExperimentConfig) -> tuple[str | None, str | None]:
    """Return (key, source). Environment wins over `.env`; empty values count as missing.

    The returned key must only ever be handed to the SDK client.
    """
    name = config.llm.api_key_env
    value = os.environ.get(name, "")
    if value.strip():
        return value.strip(), "environment"

    env_path = config.env_file_path
    if env_path.is_file():
        from dotenv import dotenv_values

        value = dotenv_values(env_path, encoding="utf-8").get(name) or ""
        if value.strip():
            return value.strip(), config.llm.env_filename
    return None, None


def api_key_status(config: ExperimentConfig) -> dict:
    """Safe summary for reports: configured/missing and where it came from."""
    key, source = resolve_api_key(config)
    return {"status": KEY_CONFIGURED if key else KEY_MISSING, "source": source}


def ensure_env_file(config: ExperimentConfig) -> bool:
    """Create an empty `.env` when none exists; never touch an existing one."""
    path = config.env_file_path
    if path.exists():
        return False
    path.write_text(f"{config.llm.api_key_env}=\n", encoding="utf-8", newline="\n")
    return True


def env_file_is_ignored(config: ExperimentConfig) -> bool:
    """Whether `.gitignore` lists the `.env` file name on its own line."""
    gitignore = config.project_root / ".gitignore"
    if not gitignore.is_file():
        return False
    patterns = {line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()}
    return config.llm.env_filename in patterns


def sdk_version() -> str | None:
    try:
        import openai
    except ImportError:
        return None
    return getattr(openai, "__version__", None)


# --- transport -------------------------------------------------------------------


@dataclass
class TransportResult:
    """What one Responses API call returned, before any local validation."""

    response_id: str | None = None
    request_id: str | None = None
    model: str | None = None
    status: str | None = None
    incomplete_reason: str | None = None
    error: dict | None = None
    output_text: str | None = None
    refusal: str | None = None
    usage: dict | None = None
    raw_response: dict = field(default_factory=dict)


class Transport(Protocol):
    def send(self, request: dict) -> TransportResult: ...


def create_client(config: ExperimentConfig, api_key: str) -> Any:
    from openai import OpenAI

    return OpenAI(
        api_key=api_key,
        timeout=config.llm.timeout_seconds,
        max_retries=config.llm.max_retries,
    )


class OpenAIResponsesTransport:
    """Thin adapter over `client.responses.create` for the real SDK."""

    def __init__(self, client: Any):
        self._client = client

    def send(self, request: dict) -> TransportResult:
        raw = self._client.responses.with_raw_response.create(**request)
        response = raw.parse()
        return summarise_response(response, request_id=getattr(raw, "request_id", None))


def summarise_response(response: Any, request_id: str | None = None) -> TransportResult:
    """Extract text, refusal, status and usage from an SDK Response object."""
    output_text_parts: list[str] = []
    refusal_parts: list[str] = []
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            part_type = getattr(part, "type", None)
            if part_type == "output_text":
                output_text_parts.append(part.text)
            elif part_type == "refusal":
                refusal_parts.append(part.refusal)

    incomplete = getattr(response, "incomplete_details", None)
    error = getattr(response, "error", None)
    usage = getattr(response, "usage", None)
    return TransportResult(
        response_id=getattr(response, "id", None),
        request_id=request_id or getattr(response, "_request_id", None),
        model=getattr(response, "model", None),
        status=getattr(response, "status", None),
        incomplete_reason=getattr(incomplete, "reason", None) if incomplete else None,
        error=error.model_dump() if error is not None else None,
        output_text="".join(output_text_parts) if output_text_parts else None,
        refusal="".join(refusal_parts) if refusal_parts else None,
        usage=usage.model_dump() if usage is not None else None,
        raw_response=response.model_dump(mode="json"),
    )


# --- error classification -----------------------------------------------------------


def classify_exception(exc: BaseException) -> dict:
    """Map an SDK exception to a recorded error kind. Messages carry no secrets."""
    try:
        import openai
    except ImportError:  # pragma: no cover - the SDK is a declared dependency
        openai = None

    info = {
        "kind": UNEXPECTED,
        "exception_type": type(exc).__name__,
        "message": str(exc),
        "status_code": None,
        "error_code": None,
    }
    if openai is None:
        return info

    if isinstance(exc, openai.APITimeoutError):
        info["kind"] = TIMEOUT
    elif isinstance(exc, openai.APIConnectionError):
        info["kind"] = CONNECTION
    elif isinstance(exc, openai.APIStatusError):
        info["status_code"] = exc.status_code
        info["error_code"] = getattr(exc, "code", None)
        if isinstance(exc, openai.AuthenticationError):
            info["kind"] = AUTHENTICATION
        elif isinstance(exc, openai.RateLimitError):
            # HTTP 429 covers both rate limits and an exhausted quota.
            info["kind"] = RATE_LIMIT_OR_QUOTA
        elif isinstance(exc, openai.PermissionDeniedError):
            info["kind"] = PERMISSION_DENIED
        elif isinstance(exc, openai.NotFoundError):
            info["kind"] = MODEL_UNAVAILABLE
        elif isinstance(exc, openai.BadRequestError):
            info["kind"] = BAD_REQUEST
        else:
            info["kind"] = API_STATUS
    return info


def transport_outcome(result: TransportResult) -> tuple[str, str | None]:
    """Classify a delivered response: ok, refusal, incomplete, failed or empty."""
    if result.status == "failed" or result.error:
        return RESPONSE_FAILED, (result.error or {}).get("message")
    if result.refusal is not None:
        return PROVIDER_REFUSAL, result.refusal
    if result.status == "incomplete":
        return INCOMPLETE_RESPONSE, result.incomplete_reason
    if not result.output_text:
        return EMPTY_OUTPUT, "response contains no output_text"
    return TRANSPORT_OK, None


def call(transport: Transport, request: dict) -> dict:
    """Execute one call and describe it. Never retries, never raises for API errors.

    `latency_seconds` is the wall clock around `transport.send`: request
    serialisation, network round trip and response parsing. Client creation
    and local validation lie outside it.
    """
    started_at = utc_now()
    started = time.perf_counter()
    try:
        result = transport.send(request)
    except APIBudgetStop as exc:
        # Nothing was sent: the batch budget stopped the attempt before the network.
        return {
            "started_at_utc": started_at,
            "latency_seconds": 0.0,
            "transport_status": API_BUDGET_STOP,
            "error": {"kind": API_BUDGET_STOP, "message": str(exc)},
            "response": None,
        }
    except Exception as exc:  # noqa: BLE001 - every failure must be recorded, not raised
        latency = time.perf_counter() - started
        error = classify_exception(exc)
        return {
            "started_at_utc": started_at,
            "latency_seconds": round(latency, 4),
            "transport_status": error["kind"],
            "error": error,
            "response": None,
        }
    latency = time.perf_counter() - started
    status, detail = transport_outcome(result)
    record = {
        "started_at_utc": started_at,
        "latency_seconds": round(latency, 4),
        "transport_status": status,
        "error": None if status == TRANSPORT_OK else {"kind": status, "message": detail},
        "response": {
            "response_id": result.response_id,
            "request_id": result.request_id,
            "model_returned": result.model,
            "status": result.status,
            "incomplete_reason": result.incomplete_reason,
            "output_text": result.output_text,
            "refusal": result.refusal,
            "usage": result.usage,
            "raw_response": result.raw_response,
        },
    }
    return record
