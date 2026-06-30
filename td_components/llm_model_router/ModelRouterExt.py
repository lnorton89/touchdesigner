"""TouchDesigner extension scaffold for the LLM Model Router."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

try:
    from . import router_http
except ImportError:  # TouchDesigner source DAT imports may not be package-relative.
    import router_http  # type: ignore


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
        self._complete_count = 0
        self._error_count = 0

    def request(
        self,
        prompt: Optional[str] = None,
        messages: Optional[list[Mapping[str, Any]]] = None,
        trigger_source: str = "pulse",
    ) -> int:
        config = self._read_config()
        if prompt is None and messages is None:
            prompt = self._read_prompt_dat(config.get("prompt_dat"))

        envelope = router_http.build_request_envelope(
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
        self._mark_running(envelope)
        self._write_outputs()
        return int(envelope["request_id"])

    def reset(self) -> Dict[str, Any]:
        self._state = "idle"
        self._active_request_id = None
        self._last_result = None
        self._write_outputs()
        return self._snapshot_state()

    def retry(self) -> int:
        if not self._last_envelope:
            raise RuntimeError("no previous request to retry")
        envelope = router_http.rebuild_retry_envelope(self._last_envelope)
        self._mark_running(envelope)
        self._write_outputs()
        return int(envelope["request_id"])

    def apply_result(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        self._last_result = dict(payload)
        self._active_request_id = int(payload.get("request_id", 0) or 0)
        self._state = str(payload.get("status", "error"))
        if self._state == "complete":
            self._complete_count += 1
        elif self._state == "error":
            self._error_count += 1
        self._write_outputs()
        return self._snapshot_state()

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
        return str(prompt_dat_ref)

    def _mark_running(self, envelope: Mapping[str, Any]) -> None:
        self._state = "running"
        self._active_request_id = int(envelope["request_id"])
        self._last_envelope = dict(envelope)
        self._last_result = None

    def _snapshot_state(self) -> Dict[str, Any]:
        return {
            "state": self._state,
            "running": self._state == "running",
            "done": self._state == "complete",
            "error": self._state == "error",
            "request_id": self._active_request_id or 0,
            "complete_count": self._complete_count,
            "error_count": self._error_count,
            "last_result": dict(self._last_result) if self._last_result else None,
        }

    def _write_outputs(self) -> None:
        """Plan 02 writes DAT/CHOP outputs on the TouchDesigner side."""

    @property
    def state(self) -> Dict[str, Any]:
        return self._snapshot_state()
