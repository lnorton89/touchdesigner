"""Demo callback and utility functions for TouchDesigner LLM operator networks.

Place this module in a Text DAT named `demo_callbacks` inside your TD project.
Wire callbacks to parameter pulses, DAT table-change events, and the Model
Router's Callbacktarget to see live request/response data flow through the
network.

All functions are TD runtime-aware: they use the implicit `me` reference
(available in DAT Execute and Parameter Execute scripts) to locate operators
by relative name.
"""

from __future__ import annotations


def onRouterResult(payload):
    """TouchDesigner callback target for ModelRouter result payloads.

    Wires to Callbacktarget on the llm_model_router component.
    Writes structured fields into a Text DAT named `callback_payload`.
    """
    target = getattr(me, "op", lambda name: None)("callback_payload")
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
    """Replace prompt text with a message that triggers a measurable delay."""
    prompt = getattr(me, "op", lambda name: None)("prompt_input")
    if prompt is not None and hasattr(prompt, "text"):
        prompt.text = (
            "Answer briefly after thinking for a moment: "
            "say the router stayed responsive."
        )


def simulateEndpointError(router_comp):
    """Set the router's Baseurl to an unreachable port to trigger a connection error."""
    if hasattr(router_comp, "par"):
        router_comp.par.Baseurl = "http://localhost:9/v1"
