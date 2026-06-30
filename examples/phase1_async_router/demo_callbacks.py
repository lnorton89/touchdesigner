"""Demo callback helpers for the Phase 1 async Router proof."""

from __future__ import annotations


def onRouterResult(payload):
    """TouchDesigner callback target for ModelRouter result payloads."""

    target = getattr(me, "op", lambda name: None)("callback_payload")  # type: ignore[name-defined]
    if target is not None and hasattr(target, "text"):
        lines = [
            f"request_id: {payload.get('request_id', '')}",
            f"status: {payload.get('status', '')}",
            f"trigger_source: {payload.get('trigger_source', '')}",
            f"elapsed_ms: {payload.get('elapsed_ms', '')}",
            f"response_text: {payload.get('response_text', '')}",
            f"error_text: {payload.get('error_text', '')}",
        ]
        target.text = "\n".join(lines)
    return payload


def simulateSlowPrompt():
    prompt = getattr(me, "op", lambda name: None)("prompt_input")  # type: ignore[name-defined]
    if prompt is not None and hasattr(prompt, "text"):
        prompt.text = "Answer briefly after thinking for a moment: say the router stayed responsive."


def simulateEndpointError(router_comp):
    if hasattr(router_comp, "par"):
        router_comp.par.Baseurl = "http://localhost:9/v1"
