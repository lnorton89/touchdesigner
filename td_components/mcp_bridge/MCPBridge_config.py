"""Configuration constants for the TouchDesigner MCP Bridge component."""

from __future__ import annotations

# ── Network ───────────────────────────────────────────────────────────

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 9876
REQUEST_TIMEOUT = 5.0

# ── Route Dispatch ────────────────────────────────────────────────────
# Maps URL path segments to handler method names on the MCPBridge class.

ROUTES: dict[str, str] = {
    "get_parameter": "get_parameter",
    "get_dat_text": "get_dat_text",
    "pulse_trigger": "pulse_trigger",
    "list_network_children": "list_network_children",
    "set_parameter": "set_parameter",
    "read_chop_channel": "read_chop_channel",
    "router_demo_action": "router_demo_action",
    "agent_demo_action": "agent_demo_action",
    "tool_demo_action": "tool_demo_action",
    "create_simple_comp": "create_simple_comp",
    "create_dmx_controller": "create_dmx_controller",
}
