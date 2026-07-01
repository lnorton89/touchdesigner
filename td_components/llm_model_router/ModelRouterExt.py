"""TouchDesigner extension scaffold for the LLM Model Router."""

from __future__ import annotations

import threading
import json
from typing import Any, Dict, Mapping, Optional

try:
    from . import router_http
except ImportError:
    import router_http


class ModelRouter:
    """Central API used by parameter pulses, DAT callbacks, and retry."""

    PROVIDER_PARAM = "Provider"
    BASE_URL_PARAM = "Baseurl"
    MODEL_PARAM = "Model"
    TIMEOUT_PARAM = "Timeout"
    PROMPT_DAT_PARAM = "Promptdat"
    CALLBACK_TARGET_PARAM = "Callbacktarget"
    CALLBACK_METHOD_PARAM = "Callbackmethod"
    API_KEY_SOURCE_PARAM = "Apikeysource"
    TRIGGER_PULSE_PARAM = "Trigger"
    RESET_PULSE_PARAM = "Reset"
    RETRY_PULSE_PARAM = "Retry"
    STATUS_DISPLAY_PARAM = "Statusdisplay"

    CONFIG_PARAM_NAMES = {
        "provider": PROVIDER_PARAM,
        "base_url": BASE_URL_PARAM,
        "model": MODEL_PARAM,
        "timeout": TIMEOUT_PARAM,
        "prompt_dat": PROMPT_DAT_PARAM,
        "callback_target": CALLBACK_TARGET_PARAM,
        "callback_method": CALLBACK_METHOD_PARAM,
        "api_key_source": API_KEY_SOURCE_PARAM,
        "trigger_pulse": TRIGGER_PULSE_PARAM,
        "reset_pulse": RESET_PULSE_PARAM,
        "retry_pulse": RETRY_PULSE_PARAM,
        "status_display": STATUS_DISPLAY_PARAM,
    }

    def __init__(self, ownerComp: Any = None):
        self.ownerComp = ownerComp
        self._state = "idle"
        self._active_request_id: Optional[int] = None
        self._last_envelope: Optional[Dict[str, Any]] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._response_text = ""
        self._error_text = ""
        self._complete_count = 0
        self._error_count = 0
        self._retry_count = 0
        self._status_channels = self._build_status_channels()

    def request(
        self,
        prompt: Optional[str] = None,
        messages: Optional[list[Mapping[str, Any]]] = None,
        trigger_source: str = "pulse",
        dispatch: bool = True,
        config_overrides: Optional[Mapping[str, Any]] = None,
    ) -> int:
        envelope = self.build_request_envelope(
            prompt=prompt,
            messages=messages,
            trigger_source=trigger_source,
            config_overrides=config_overrides,
        )
        self._mark_running(envelope)
        self._write_outputs()
        if dispatch:
            self._submit_worker(envelope)
        return int(envelope["request_id"])

    def build_request_envelope(
        self,
        prompt: Optional[str] = None,
        messages: Optional[list[Mapping[str, Any]]] = None,
        trigger_source: str = "pulse",
        config_overrides: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a validated Router request envelope without dispatching it."""
        config = self._read_config()
        if config_overrides:
            for key in ("provider", "base_url", "model", "timeout", "api_key_source"):
                if key in config_overrides and config_overrides[key] not in (None, ""):
                    config[key] = config_overrides[key]
        if prompt is None and messages is None:
            prompt = self._read_prompt_dat(config.get("prompt_dat"))

        return router_http.build_request_envelope(
            provider=config["provider"],
            base_url=config["base_url"],
            model=config["model"],
            timeout=config["timeout"],
            prompt=prompt,
            messages=messages,
            callback_target=config["callback_target"],
            callback_method=config["callback_method"],
            api_key_source=config["api_key_source"],
            trigger_source=trigger_source,
        )

    def reset(self) -> Dict[str, Any]:
        self._state = "idle"
        self._active_request_id = None
        self._last_result = None
        self._response_text = ""
        self._error_text = ""
        self._complete_count = 0
        self._error_count = 0
        self._retry_count = 0
        self._status_channels = self._build_status_channels()
        self._write_outputs()
        return self._snapshot_state()

    def retry(self, dispatch: bool = True) -> int:
        if not self._last_envelope:
            raise RuntimeError("no previous request to retry")
        envelope = router_http.rebuild_retry_envelope(self._last_envelope)
        self._retry_count += 1
        self._mark_running(envelope)
        self._write_outputs()
        if dispatch:
            self._submit_worker(envelope)
        return int(envelope["request_id"])

    def apply_result(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        return self._apply_result(payload)

    def _apply_result(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        request_id = int(payload.get("request_id", 0) or 0)
        if self._active_request_id and request_id < self._active_request_id:
            return self._snapshot_state()

        self._last_result = dict(payload)
        self._active_request_id = request_id
        self._state = str(payload.get("status", "error"))
        self._response_text = str(payload.get("response_text", ""))
        self._error_text = str(payload.get("error_text", ""))
        if self._state == "complete":
            self._complete_count += 1
        elif self._state == "error":
            self._error_count += 1
        self._status_channels = self._build_status_channels()
        self._write_outputs()
        self._invoke_callback(payload)
        return self._snapshot_state()

    def _submit_worker(self, envelope: Mapping[str, Any]) -> None:
        plain_envelope = dict(envelope)

        def worker() -> None:
            payload = router_http.call_openai_compatible(plain_envelope)
            self._handoff_result(payload)

        thread = threading.Thread(
            target=worker,
            name=f"ModelRouter-{plain_envelope.get('request_id', 'request')}",
            daemon=True,
        )
        thread.start()

    def _handoff_result(self, payload: Mapping[str, Any]) -> None:
        run_func = globals().get("run")
        if callable(run_func) and self.ownerComp is not None:
            try:
                run_func("args[0]._apply_result(args[1])", self, dict(payload), endFrame=True)
                return
            except Exception:
                pass
        self._apply_result(payload)

    def _read_config(self) -> Dict[str, Any]:
        return {
            "provider": self._read_param(self.PROVIDER_PARAM, router_http.DEFAULT_PROVIDER),
            "base_url": self._read_param(self.BASE_URL_PARAM, router_http.DEFAULT_BASE_URL),
            "model": self._read_param(self.MODEL_PARAM, router_http.DEFAULT_MODEL),
            "timeout": self._read_param(
                self.TIMEOUT_PARAM, router_http.DEFAULT_TIMEOUT_SECONDS
            ),
            "prompt_dat": self._read_param(self.PROMPT_DAT_PARAM, ""),
            "callback_target": self._read_param(self.CALLBACK_TARGET_PARAM, ""),
            "callback_method": self._read_param(
                self.CALLBACK_METHOD_PARAM, "onRouterResult"
            ),
            "api_key_source": self._read_param(self.API_KEY_SOURCE_PARAM, ""),
        }

    def _read_param(self, name: str, default: Any) -> Any:
        par_collection = getattr(self.ownerComp, "par", None)
        param = getattr(par_collection, name, None) if par_collection is not None else None
        if param is None:
            return default
        return getattr(param, "eval", lambda: getattr(param, "val", default))()

    def _read_prompt_dat(self, prompt_dat_ref: Any) -> str:
        if not prompt_dat_ref:
            return ""
        if hasattr(prompt_dat_ref, "text"):
            return str(prompt_dat_ref.text)
        if isinstance(prompt_dat_ref, str):
            op_obj = self._lookup_output_op(prompt_dat_ref)
            if op_obj is not None and hasattr(op_obj, "text"):
                return str(op_obj.text)
        return str(prompt_dat_ref)

    def _mark_running(self, envelope: Mapping[str, Any]) -> None:
        self._state = "running"
        self._active_request_id = int(envelope["request_id"])
        self._last_envelope = dict(envelope)
        self._last_result = None
        self._response_text = ""
        self._error_text = ""
        self._status_channels = self._build_status_channels()

    def _snapshot_state(self) -> Dict[str, Any]:
        return {
            "state": self._state,
            "running": self._state == "running",
            "done": self._state == "complete",
            "error": self._state == "error",
            "request_id": self._active_request_id or 0,
            "complete_count": self._complete_count,
            "error_count": self._error_count,
            "retry_count": self._retry_count,
            "response_text": self._response_text,
            "error_text": self._error_text,
            "status_channels": dict(self._status_channels),
            "last_result": dict(self._last_result) if self._last_result else None,
        }

    def _build_status_channels(self) -> Dict[str, int]:
        request_id = int(self._active_request_id or 0)
        return {
            "running": int(self._state == "running"),
            "done": int(self._state == "complete"),
            "error": int(self._state == "error"),
            "request_id": request_id,
            "complete_count": self._complete_count,
            "error_count": self._error_count,
            "retry_count": self._retry_count,
        }

    def _write_outputs(self) -> None:
        """Write Router state into conventional demo DAT outputs when present."""
        snapshot = self._snapshot_state()
        self._write_text_dat("response_text", self._response_text)
        self._write_text_dat("error_text", self._error_text)
        self._write_text_dat("status_json", json.dumps(snapshot, indent=2, default=str))

    def _write_text_dat(self, name: str, text: str) -> None:
        dat = self._lookup_output_op(name)
        if dat is not None and hasattr(dat, "text"):
            dat.text = text

    def _lookup_output_op(self, name_or_path: str) -> Any:
        if not self.ownerComp:
            return None

        if "/" in name_or_path:
            op_lookup = getattr(self.ownerComp, "op", None)
            if callable(op_lookup):
                result = op_lookup(name_or_path)
                if result is not None:
                    return result

        parent = getattr(self.ownerComp, "parent", None)
        parent_obj = parent() if callable(parent) else parent
        if parent_obj is not None:
            op_lookup = getattr(parent_obj, "op", None)
            if callable(op_lookup):
                result = op_lookup(name_or_path)
                if result is not None:
                    return result

        op_lookup = getattr(self.ownerComp, "op", None)
        if callable(op_lookup):
            return op_lookup(name_or_path)
        return None

    def _invoke_callback(self, payload: Mapping[str, Any]) -> None:
        envelope = self._last_envelope or {}
        target_ref = envelope.get("callback_target")
        if not target_ref:
            return

        method_name = str(envelope.get("callback_method", "onRouterResult"))
        target = target_ref
        if isinstance(target_ref, str) and self.ownerComp is not None:
            op_lookup = getattr(self.ownerComp, "op", None)
            if callable(op_lookup):
                target = op_lookup(target_ref)

        callback = getattr(target, method_name, None)
        if callable(callback):
            callback(dict(payload))

    @property
    def state(self) -> Dict[str, Any]:
        return self._snapshot_state()
