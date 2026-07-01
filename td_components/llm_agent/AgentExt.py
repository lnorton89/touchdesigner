"""TouchDesigner extension scaffold for a conversational LLM Agent."""

from __future__ import annotations

import json
import threading
from typing import Any, Dict, Mapping, Optional

try:
    from td_components.llm_model_router import router_http
    from td_components.llm_tool_registry.ToolRegistryExt import ToolRegistry, execute_tool_calls
except ImportError:
    from ..llm_model_router import router_http
    from ..llm_tool_registry.ToolRegistryExt import ToolRegistry, execute_tool_calls


class LLMAgent:
    """Conversation/history layer that delegates model calls to ModelRouter."""

    SYSTEM_PROMPT_PARAM = "Systemprompt"
    MESSAGE_DAT_PARAM = "Messagedat"
    ROUTER_PATH_PARAM = "Routerpath"
    OUTPUT_DAT_PARAM = "Outputdat"
    JSON_OUTPUT_DAT_PARAM = "Jsonoutputdat"
    ERROR_DAT_PARAM = "Errordat"
    STATUS_DAT_PARAM = "Statusdat"
    HISTORY_DAT_PARAM = "Historydat"
    PROVIDER_OVERRIDE_PARAM = "Provideroverride"
    BASE_URL_OVERRIDE_PARAM = "Baseurloverride"
    MODEL_OVERRIDE_PARAM = "Modeloverride"
    TIMEOUT_OVERRIDE_PARAM = "Timeoutoverride"
    TOOL_REGISTRY_PARAM = "Toolregistry"

    CONFIG_PARAM_NAMES = {
        "system_prompt": SYSTEM_PROMPT_PARAM,
        "message_dat": MESSAGE_DAT_PARAM,
        "router_path": ROUTER_PATH_PARAM,
        "output_dat": OUTPUT_DAT_PARAM,
        "json_output_dat": JSON_OUTPUT_DAT_PARAM,
        "error_dat": ERROR_DAT_PARAM,
        "status_dat": STATUS_DAT_PARAM,
        "history_dat": HISTORY_DAT_PARAM,
        "provider_override": PROVIDER_OVERRIDE_PARAM,
        "base_url_override": BASE_URL_OVERRIDE_PARAM,
        "model_override": MODEL_OVERRIDE_PARAM,
        "timeout_override": TIMEOUT_OVERRIDE_PARAM,
        "tool_registry": TOOL_REGISTRY_PARAM,
    }

    def __init__(self, ownerComp: Any = None, router: Any = None):
        self.ownerComp = ownerComp
        self._router = router
        self._history: list[Dict[str, str]] = []
        self._pending_user_message = ""
        self._active_request_id: Optional[int] = None
        self._state = "idle"
        self._response_text = ""
        self._error_text = ""
        self._complete_count = 0
        self._error_count = 0
        self._status_channels = self._build_status_channels()

    def available_tools(self, registry: Optional[ToolRegistry] = None) -> list[Dict[str, Any]]:
        resolved = registry or self._resolve_tool_registry()
        return resolved.provider_tools() if resolved is not None else []

    def apply_tool_calls(
        self,
        tool_calls: list[Mapping[str, Any]],
        registry: Optional[ToolRegistry] = None,
    ) -> Dict[str, Any]:
        resolved = registry or self._resolve_tool_registry()
        if resolved is None:
            raise RuntimeError("ToolRegistry instance not found")

        results = execute_tool_calls(resolved, tool_calls)
        had_error = False
        for result in results:
            self._history.append(
                {
                    "role": "tool",
                    "content": str(result.get("content", "")),
                    "name": str(result.get("name", "")),
                    "tool_call_id": str(result.get("tool_call_id", "")),
                }
            )
            if result.get("status") != "ok":
                had_error = True
                self._error_text = str(result.get("error_text", "tool call failed"))

        self._state = "error" if had_error else "complete"
        if had_error:
            self._error_count += 1
        self._status_channels = self._build_status_channels()
        self._write_outputs()
        return self.state

    def send(
        self,
        message: Optional[str] = None,
        *,
        system_prompt: Optional[str] = None,
        dispatch: bool = True,
        config_overrides: Optional[Mapping[str, Any]] = None,
    ) -> int:
        """Append a user message and submit the full conversation to Router."""
        user_message = str(message if message is not None else self._read_message_dat())
        self._pending_user_message = user_message
        messages = self._build_messages(system_prompt=system_prompt, user_message=user_message)
        envelope = self._build_router_envelope(messages, config_overrides)
        request_id = int(envelope["request_id"])
        self._mark_running(request_id)
        self._write_outputs()
        if dispatch:
            self._submit_worker(envelope)
        return request_id

    def clear_history(self) -> Dict[str, Any]:
        self._history = []
        self._pending_user_message = ""
        self._active_request_id = None
        self._state = "idle"
        self._response_text = ""
        self._error_text = ""
        self._status_channels = self._build_status_channels()
        self._write_outputs()
        return self.state

    def append_history(self, role: str, content: str) -> Dict[str, Any]:
        self._history.append({"role": str(role or "user"), "content": str(content)})
        self._write_outputs()
        return self.state

    def apply_result(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        request_id = int(payload.get("request_id", 0) or 0)
        if self._active_request_id and request_id < self._active_request_id:
            return self.state

        self._active_request_id = request_id
        self._state = str(payload.get("status", "error"))
        self._response_text = str(payload.get("response_text", ""))
        self._error_text = str(payload.get("error_text", ""))

        if self._state == "complete":
            if self._pending_user_message:
                self._history.append({"role": "user", "content": self._pending_user_message})
            self._history.append({"role": "assistant", "content": self._response_text})
            self._pending_user_message = ""
            self._complete_count += 1
        elif self._state == "error":
            self._error_count += 1

        self._status_channels = self._build_status_channels()
        self._write_outputs(payload)
        return self.state

    def _build_router_envelope(
        self,
        messages: list[Dict[str, str]],
        config_overrides: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        router = self._resolve_router()
        overrides = self._read_router_overrides()
        if config_overrides:
            overrides.update({k: v for k, v in config_overrides.items() if v not in (None, "")})
        build_envelope = getattr(router, "build_request_envelope", None)
        if callable(build_envelope):
            return dict(
                build_envelope(
                    messages=messages,
                    trigger_source="agent",
                    config_overrides=overrides,
                )
            )

        request_id = int(
            router.request(
                messages=messages,
                trigger_source="agent",
                dispatch=False,
                config_overrides=overrides,
            )
        )
        envelope = getattr(router, "_last_envelope", None)
        if envelope is None:
            raise RuntimeError("ModelRouter did not expose a request envelope")
        if int(envelope.get("request_id", 0)) != request_id:
            raise RuntimeError("ModelRouter request envelope id mismatch")
        return dict(envelope)

    def _submit_worker(self, envelope: Mapping[str, Any]) -> None:
        plain_envelope = dict(envelope)

        def worker() -> None:
            payload = router_http.call_openai_compatible(plain_envelope)
            self._handoff_result(payload)

        threading.Thread(
            target=worker,
            name=f"LLMAgent-{plain_envelope.get('request_id', 'request')}",
            daemon=True,
        ).start()

    def _handoff_result(self, payload: Mapping[str, Any]) -> None:
        run_func = globals().get("run")
        if callable(run_func) and self.ownerComp is not None:
            try:
                run_func("args[0].apply_result(args[1])", self, dict(payload), endFrame=True)
                return
            except Exception:
                pass
        self.apply_result(payload)

    def _resolve_router(self) -> Any:
        if self._router is not None:
            return self._router

        router_path = self._read_param(self.ROUTER_PATH_PARAM, "../llm_model_router")
        owner_op = getattr(self.ownerComp, "op", None)
        router_comp = owner_op(router_path) if callable(owner_op) else None
        if router_comp is None and self.ownerComp is not None:
            parent = getattr(self.ownerComp, "parent", None)
            parent_obj = parent() if callable(parent) else parent
            parent_op = getattr(parent_obj, "op", None)
            router_comp = parent_op(router_path) if callable(parent_op) else None

        ext = getattr(router_comp, "ext", None)
        router = getattr(ext, "ModelRouter", None) if ext is not None else router_comp
        if router is None:
            raise RuntimeError("ModelRouter instance not found")
        self._router = router
        return router

    def _resolve_tool_registry(self) -> Optional[ToolRegistry]:
        registry_ref = self._read_param(self.TOOL_REGISTRY_PARAM, "llm_tool_registry")
        target = self._lookup_op(registry_ref)
        if target is None:
            return None
        ext = getattr(target, "ext", None)
        registry = getattr(ext, "ToolRegistry", None) if ext is not None else target
        if isinstance(registry, ToolRegistry) or hasattr(registry, "provider_tools"):
            return registry
        return None

    def _build_messages(
        self, *, system_prompt: Optional[str], user_message: str
    ) -> list[Dict[str, str]]:
        messages: list[Dict[str, str]] = []
        resolved_system = str(
            system_prompt
            if system_prompt is not None
            else self._read_param(self.SYSTEM_PROMPT_PARAM, "")
        )
        if resolved_system.strip():
            messages.append({"role": "system", "content": resolved_system})
        messages.extend(dict(item) for item in self._history)
        messages.append({"role": "user", "content": user_message})
        return messages

    def _read_router_overrides(self) -> Dict[str, Any]:
        mapping = {
            "provider": self.PROVIDER_OVERRIDE_PARAM,
            "base_url": self.BASE_URL_OVERRIDE_PARAM,
            "model": self.MODEL_OVERRIDE_PARAM,
            "timeout": self.TIMEOUT_OVERRIDE_PARAM,
        }
        overrides: Dict[str, Any] = {}
        for key, param_name in mapping.items():
            value = self._read_param(param_name, "")
            if value not in (None, ""):
                overrides[key] = value
        return overrides

    def _read_message_dat(self) -> str:
        message_dat_ref = self._read_param(self.MESSAGE_DAT_PARAM, "agent_message")
        dat = self._lookup_op(message_dat_ref)
        if dat is not None and hasattr(dat, "text"):
            return str(dat.text)
        return str(message_dat_ref or "")

    def _read_param(self, name: str, default: Any) -> Any:
        par_collection = getattr(self.ownerComp, "par", None)
        param = getattr(par_collection, name, None) if par_collection is not None else None
        if param is None:
            return default
        return getattr(param, "eval", lambda: getattr(param, "val", default))()

    def _mark_running(self, request_id: int) -> None:
        self._active_request_id = request_id
        self._state = "running"
        self._response_text = ""
        self._error_text = ""
        self._status_channels = self._build_status_channels()

    def _build_status_channels(self) -> Dict[str, int]:
        return {
            "running": int(self._state == "running"),
            "done": int(self._state == "complete"),
            "error": int(self._state == "error"),
            "response_ready": int(self._state == "complete"),
            "request_id": int(self._active_request_id or 0),
            "history_length": len(self._history),
            "complete_count": self._complete_count,
            "error_count": self._error_count,
        }

    def _write_outputs(self, payload: Optional[Mapping[str, Any]] = None) -> None:
        snapshot = self.state
        self._write_text_dat("agent_response", self._response_text)
        self._write_text_dat("agent_error", self._error_text)
        self._write_text_dat("agent_status_json", json.dumps(snapshot, indent=2, default=str))
        self._write_text_dat("agent_history", json.dumps(self._history, indent=2))
        if payload is not None:
            self._write_text_dat("agent_response_json", json.dumps(dict(payload), indent=2, default=str))

    def _write_text_dat(self, default_name: str, text: str) -> None:
        configured_name = {
            "agent_response": self.OUTPUT_DAT_PARAM,
            "agent_response_json": self.JSON_OUTPUT_DAT_PARAM,
            "agent_error": self.ERROR_DAT_PARAM,
            "agent_status_json": self.STATUS_DAT_PARAM,
            "agent_history": self.HISTORY_DAT_PARAM,
        }.get(default_name)
        target_ref = self._read_param(configured_name, default_name) if configured_name else default_name
        dat = self._lookup_op(target_ref)
        if dat is not None and hasattr(dat, "text"):
            dat.text = text

    def _lookup_op(self, name_or_path: Any) -> Any:
        if not self.ownerComp or not name_or_path:
            return None
        if hasattr(name_or_path, "text"):
            return name_or_path

        name = str(name_or_path)
        parent = getattr(self.ownerComp, "parent", None)
        parent_obj = parent() if callable(parent) else parent
        if parent_obj is not None:
            op_lookup = getattr(parent_obj, "op", None)
            if callable(op_lookup):
                result = op_lookup(name)
                if result is not None:
                    return result

        op_lookup = getattr(self.ownerComp, "op", None)
        if callable(op_lookup):
            return op_lookup(name)
        return None

    @property
    def history(self) -> list[Dict[str, str]]:
        return [dict(item) for item in self._history]

    @property
    def state(self) -> Dict[str, Any]:
        return {
            "state": self._state,
            "running": self._state == "running",
            "done": self._state == "complete",
            "error": self._state == "error",
            "request_id": self._active_request_id or 0,
            "history": self.history,
            "history_length": len(self._history),
            "response_text": self._response_text,
            "error_text": self._error_text,
            "complete_count": self._complete_count,
            "error_count": self._error_count,
            "status_channels": dict(self._status_channels),
        }
