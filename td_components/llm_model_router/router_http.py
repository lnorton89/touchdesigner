"""Pure-Python request and response helpers for the Model Router."""

from __future__ import annotations

import itertools
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse


DEFAULT_PROVIDER = "openai_compatible"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "llama3.2"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_TIMEOUT_SECONDS = 300.0

_REQUEST_COUNTER = itertools.count(1)


class RouterConfigError(ValueError):
    """Raised when a request envelope cannot be safely built."""


def next_request_id() -> int:
    return next(_REQUEST_COUNTER)


def _coerce_timeout(value: Any) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise RouterConfigError("timeout must be a number") from exc

    if timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
        raise RouterConfigError(
            f"timeout must be greater than 0 and no more than {MAX_TIMEOUT_SECONDS:g}"
        )
    return timeout


def _validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RouterConfigError("base_url must be an http or https URL")
    return base_url.rstrip("/")


def _normalize_messages(
    prompt: Optional[str] = None, messages: Optional[Iterable[Mapping[str, Any]]] = None
) -> List[Dict[str, str]]:
    if messages is not None:
        normalized = []
        for item in messages:
            role = str(item.get("role", "user")).strip() or "user"
            content = str(item.get("content", ""))
            normalized.append({"role": role, "content": content})
        if not normalized:
            raise RouterConfigError("messages must contain at least one message")
        return normalized

    if prompt is None:
        raise RouterConfigError("prompt or messages is required")

    return [{"role": "user", "content": str(prompt)}]


def build_request_envelope(
    *,
    provider: str = DEFAULT_PROVIDER,
    base_url: str = DEFAULT_BASE_URL,
    model: str = DEFAULT_MODEL,
    timeout: Any = DEFAULT_TIMEOUT_SECONDS,
    prompt: Optional[str] = None,
    messages: Optional[Iterable[Mapping[str, Any]]] = None,
    callback_target: str = "",
    callback_method: str = "onRouterResult",
    api_key_source: str = "",
    trigger_source: str = "pulse",
    request_id: Optional[int] = None,
) -> Dict[str, Any]:
    provider_name = str(provider or DEFAULT_PROVIDER).strip()
    if provider_name not in {"openai_compatible", "ollama"}:
        raise RouterConfigError(f"unsupported provider: {provider_name}")

    request_id_value = int(request_id if request_id is not None else next_request_id())
    now = time.time()
    return {
        "request_id": request_id_value,
        "provider": provider_name,
        "base_url": _validate_base_url(str(base_url or DEFAULT_BASE_URL).strip()),
        "model": str(model or DEFAULT_MODEL).strip(),
        "timeout": _coerce_timeout(timeout),
        "messages": _normalize_messages(prompt=prompt, messages=messages),
        "callback_target": str(callback_target or ""),
        "callback_method": str(callback_method or "onRouterResult"),
        "api_key_source": str(api_key_source or ""),
        "trigger_source": str(trigger_source or "unknown"),
        "created_at": now,
    }


def build_openai_chat_payload(envelope: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "model": envelope["model"],
        "messages": list(envelope["messages"]),
        "stream": False,
    }


def endpoint_for(envelope: Mapping[str, Any]) -> str:
    return f"{str(envelope['base_url']).rstrip('/')}/chat/completions"


def extract_response_text(data: Mapping[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("response missing choices[0].message.content") from exc
    return str(content)


def success_payload(
    envelope: Mapping[str, Any],
    response_data: Mapping[str, Any],
    *,
    elapsed_ms: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "request_id": envelope["request_id"],
        "status": "complete",
        "response_text": extract_response_text(response_data),
        "error_kind": "",
        "error_text": "",
        "elapsed_ms": elapsed_ms,
        "trigger_source": envelope.get("trigger_source", "unknown"),
    }


def error_payload(
    envelope_or_request_id: Mapping[str, Any] | int,
    *,
    error_kind: str,
    error_text: str,
    elapsed_ms: Optional[float] = None,
    trigger_source: str = "unknown",
) -> Dict[str, Any]:
    if isinstance(envelope_or_request_id, Mapping):
        request_id = envelope_or_request_id.get("request_id", 0)
        trigger_source = str(envelope_or_request_id.get("trigger_source", trigger_source))
    else:
        request_id = envelope_or_request_id

    return {
        "request_id": request_id,
        "status": "error",
        "response_text": "",
        "error_kind": str(error_kind or "error"),
        "error_text": str(error_text or "unknown error"),
        "elapsed_ms": elapsed_ms,
        "trigger_source": trigger_source,
    }


def classify_exception(exc: BaseException) -> str:
    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return "timeout"
    if "connect" in name or "connection" in message or "refused" in message:
        return "connection"
    return "request"


def normalize_http_response(
    envelope: Mapping[str, Any],
    *,
    status_code: int,
    json_data: Optional[Mapping[str, Any]] = None,
    text: str = "",
    elapsed_ms: Optional[float] = None,
) -> Dict[str, Any]:
    if status_code < 200 or status_code >= 300:
        return error_payload(
            envelope,
            error_kind="http_status",
            error_text=f"HTTP {status_code}: {text}".strip(),
            elapsed_ms=elapsed_ms,
        )

    if json_data is None:
        return error_payload(
            envelope,
            error_kind="malformed_json",
            error_text="response body was not valid JSON",
            elapsed_ms=elapsed_ms,
        )

    try:
        return success_payload(envelope, json_data, elapsed_ms=elapsed_ms)
    except ValueError as exc:
        return error_payload(
            envelope,
            error_kind="malformed_response",
            error_text=str(exc),
            elapsed_ms=elapsed_ms,
        )


def exception_payload(
    envelope: Mapping[str, Any], exc: BaseException, *, elapsed_ms: Optional[float] = None
) -> Dict[str, Any]:
    return error_payload(
        envelope,
        error_kind=classify_exception(exc),
        error_text=str(exc),
        elapsed_ms=elapsed_ms,
    )


def rebuild_retry_envelope(
    last_envelope: Mapping[str, Any], *, trigger_source: str = "retry"
) -> Dict[str, Any]:
    return build_request_envelope(
        provider=str(last_envelope.get("provider", DEFAULT_PROVIDER)),
        base_url=str(last_envelope.get("base_url", DEFAULT_BASE_URL)),
        model=str(last_envelope.get("model", DEFAULT_MODEL)),
        timeout=last_envelope.get("timeout", DEFAULT_TIMEOUT_SECONDS),
        messages=last_envelope.get("messages", []),
        callback_target=str(last_envelope.get("callback_target", "")),
        callback_method=str(last_envelope.get("callback_method", "onRouterResult")),
        api_key_source=str(last_envelope.get("api_key_source", "")),
        trigger_source=trigger_source,
    )
