"""Pure-Python request and response helpers for the Model Router."""

from __future__ import annotations

import itertools
import json
import os
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlparse


DEFAULT_PROVIDER = "openai_compatible"
DEFAULT_BASE_URL = "http://localhost:11434/v1"
LLAMACPP_BASE_URL = "http://127.0.0.1:8080/v1"
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
    base_url: Optional[str] = None,
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
    if provider_name not in {"openai_compatible", "ollama", "llama.cpp"}:
        raise RouterConfigError(f"unsupported provider: {provider_name}")

    resolved_base_url = LLAMACPP_BASE_URL if provider_name == "llama.cpp" else DEFAULT_BASE_URL

    request_id_value = int(request_id if request_id is not None else next_request_id())
    now = time.time()
    return {
        "request_id": request_id_value,
        "provider": provider_name,
        "base_url": _validate_base_url(str(base_url or resolved_base_url).strip()),
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
        "provider": envelope.get("provider", DEFAULT_PROVIDER),
        "base_url": envelope.get("base_url", DEFAULT_BASE_URL),
        "model": envelope.get("model", DEFAULT_MODEL),
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
        "provider": envelope_or_request_id.get("provider", DEFAULT_PROVIDER)
        if isinstance(envelope_or_request_id, Mapping)
        else DEFAULT_PROVIDER,
        "base_url": envelope_or_request_id.get("base_url", DEFAULT_BASE_URL)
        if isinstance(envelope_or_request_id, Mapping)
        else DEFAULT_BASE_URL,
        "model": envelope_or_request_id.get("model", DEFAULT_MODEL)
        if isinstance(envelope_or_request_id, Mapping)
        else DEFAULT_MODEL,
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
        base_url=last_envelope.get("base_url", None),
        model=str(last_envelope.get("model", DEFAULT_MODEL)),
        timeout=last_envelope.get("timeout", DEFAULT_TIMEOUT_SECONDS),
        messages=last_envelope.get("messages", []),
        callback_target=str(last_envelope.get("callback_target", "")),
        callback_method=str(last_envelope.get("callback_method", "onRouterResult")),
        api_key_source=str(last_envelope.get("api_key_source", "")),
        trigger_source=trigger_source,
    )


def resolve_api_key(envelope: Mapping[str, Any]) -> Optional[str]:
    """Resolve an API key from the envelope's api_key_source field.

    The field can reference an environment variable name or contain a literal key.
    Returns None when no key is configured.
    """
    source = str(envelope.get("api_key_source", "") or "").strip()
    if not source:
        return None
    env_val = os.environ.get(source)
    if env_val is not None:
        return env_val
    return source


def call_openai_compatible(envelope: Mapping[str, Any], opener: Any = None) -> Dict[str, Any]:
    """POST a non-streaming chat completion request and normalize the result."""

    started = time.perf_counter()
    body = json.dumps(build_openai_chat_payload(envelope)).encode("utf-8")
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    api_key = resolve_api_key(envelope)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urlrequest.Request(
        endpoint_for(envelope),
        data=body,
        headers=headers,
        method="POST",
    )
    timeout = float(envelope.get("timeout", DEFAULT_TIMEOUT_SECONDS))
    open_request = opener or urlrequest.urlopen

    try:
        response = open_request(request, timeout=timeout)
        status_code = int(getattr(response, "status", getattr(response, "code", 200)))
        raw_text = response.read().decode("utf-8")
        try:
            json_data = json.loads(raw_text)
        except json.JSONDecodeError:
            json_data = None
        return normalize_http_response(
            envelope,
            status_code=status_code,
            json_data=json_data,
            text=raw_text,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    except urlerror.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return normalize_http_response(
            envelope,
            status_code=int(getattr(exc, "code", 0) or 0),
            text=text,
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    except urlerror.URLError as exc:
        return error_payload(
            envelope,
            error_kind=classify_exception(exc),
            error_text=str(getattr(exc, "reason", exc)),
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )
    except Exception as exc:
        return exception_payload(
            envelope, exc, elapsed_ms=(time.perf_counter() - started) * 1000
        )
