"""
TouchDesigner MCP Gateway — Companion Process Server.

This module runs as a standalone Python process in the external virtual
environment, separate from TouchDesigner. It exposes TD operator
capabilities as MCP (Model Context Protocol) tools that AI clients
such as Claude can call.

Architecture:
  MCP client → streamable-http :8765 → td_mcp_server.py
    → httpx → HTTP :9876 → MCPBridge COMP (inside TD) → td.op()

The MCP server never touches the TD API directly. All operator calls
go through the lightweight stdlib HTTP bridge running inside TD.
This provides complete crash isolation and avoids event-loop conflicts
between uvicorn (ASGI) and TD's main thread.

Transport:    streamable-http on 127.0.0.1:8765 (configurable)
SDK:          FastMCP from mcp.server.fastmcp (v1 stable API)
Python:       3.10+ (matches TD 2022's embedded Python 3.11)

Environment Variables:
  TD_MCP_PORT   — MCP server listen port (default: 8765)
  TD_BRIDGE_URL — TD bridge base URL (default: http://127.0.0.1:9876)

Usage:
  python td_mcp_server.py

Verification:
  curl -X POST http://127.0.0.1:8765/mcp \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

# ── Server Configuration ─────────────────────────────────────────────

SERVER_NAME = "TD-MCP-Gateway"
SERVER_HOST = "127.0.0.1"


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back to *default*."""
    value = os.environ.get(name, "")
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: str) -> str:
    """Read a string environment variable, falling back to *default*."""
    return os.environ.get(name, default)


SERVER_PORT = _env_int("TD_MCP_PORT", 8765)
BRIDGE_URL = _env_str("TD_BRIDGE_URL", "http://127.0.0.1:9876")

# ── Bridge HTTP Client ───────────────────────────────────────────────

# Reusable sync HTTP client with a short timeout — MCP tool calls are
# expected to complete quickly over localhost.
_http = httpx.Client(
    base_url=BRIDGE_URL,
    timeout=httpx.Timeout(5.0, connect=2.0),
)


def _bridge_get(path: str, params: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """GET a TD bridge endpoint and return the JSON response dict.

    Args:
        path: Bridge route path (e.g. ``get_parameter``).
        params: Query parameters to encode on the URL.

    Returns:
        The parsed JSON response from the bridge.

    Raises:
        httpx.HTTPError: On connectivity or timeout errors — the caller
            should catch these and return a user-friendly error dict.
    """
    url = f"/td/{path}"
    response = _http.get(url, params=params)
    response.raise_for_status()
    return response.json()


def _bridge_error(path: str, exc: Exception) -> dict[str, Any]:
    """Build a structured error dict for bridge failures."""
    return {
        "status": "error",
        "error": "bridge_unreachable",
        "message": (
            f"TouchDesigner bridge not reachable at {BRIDGE_URL}. "
            f"Is the MCPBridge COMP running? Details: {exc}"
        ),
        "path": path,
    }


# ── Server Builder ───────────────────────────────────────────────────

def _build_server() -> Any:
    """Create and return a configured FastMCP server with all TD tools."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(SERVER_NAME, host=SERVER_HOST, port=SERVER_PORT)

    # ── Tools ──────────────────────────────────────────────────

    @mcp.tool()
    def td_get_parameter(operator_path: str, parameter_name: str) -> dict[str, Any]:
        """Read the current value of a TouchDesigner operator parameter.

        Real TD equivalent:
            value = op(operator_path).par[parameter_name].eval()

        Args:
            operator_path: TD-style path to the operator
                (e.g. ``base_comp/constant1``).
            parameter_name: Name of the parameter to read
                (e.g. ``value0v``, ``file``, ``text``).

        Returns:
            A dict with keys ``operator``, ``parameter``, ``value``,
            and ``type``. If the bridge is unreachable a dict with
            ``status: error`` is returned instead.
        """
        try:
            return _bridge_get(
                "get_parameter",
                {"operator_path": operator_path, "parameter_name": parameter_name},
            )
        except httpx.HTTPError as exc:
            return _bridge_error("get_parameter", exc)

    @mcp.tool()
    def td_get_dat_text(operator_path: str) -> str:
        """Read the full text content of a TouchDesigner Text or Table DAT.

        Real TD equivalent:
            return op(operator_path).text

        For Table DATs the text is tab-separated rows. For Text DATs
        it is the literal text content.

        Args:
            operator_path: TD-style path to the DAT operator
                (e.g. ``base_comp/table1``, ``project1/text1``).

        Returns:
            The full text content of the DAT as a single string.
            Returns an error message string if the bridge is unreachable.
        """
        try:
            result = _bridge_get(
                "get_dat_text",
                {"operator_path": operator_path},
            )
            return str(result.get("text", ""))
        except httpx.HTTPError as exc:
            return f"Error: bridge unreachable — {exc}"

    @mcp.tool()
    def td_pulse_trigger(operator_path: str, pulse_name: str) -> dict[str, Any]:
        """Trigger a pulse parameter on a TouchDesigner operator.

        Real TD equivalent:
            op(operator_path).par[pulse_name].pulse()

        Pulse parameters are momentary — they fire once and return to 0.
        Commonly used for one-shot actions like resetting, cooking,
        or executing scripts.

        Args:
            operator_path: TD-style path to the operator
                (e.g. ``base_comp/button1``).
            pulse_name: Name of the pulse parameter
                (e.g. ``Resetpulse``, ``Cook``).

        Returns:
            A dict with keys ``operator``, ``pulse``, ``triggered``,
            and optionally ``frame``. Returns an error dict if the
            bridge is unreachable.
        """
        try:
            return _bridge_get(
                "pulse_trigger",
                {"operator_path": operator_path, "pulse_name": pulse_name},
            )
        except httpx.HTTPError as exc:
            return _bridge_error("pulse_trigger", exc)

    @mcp.tool()
    def td_list_network_children(
        operator_path: str, type_filter: str = ""
    ) -> list[dict[str, Any]]:
        """List child operators inside a TouchDesigner network component.

        Real TD equivalent:
            children = op(operator_path).children
            # optionally filtered by type

        Args:
            operator_path: TD-style path to a COMP or network
                (e.g. ``base_comp``, ``project1``).
            type_filter: Optional operator type to filter by
                (e.g. ``constant``, ``text``, ``null``).
                Pass an empty string to return all children.

        Returns:
            A dict with keys ``operator``, ``children`` (list of dicts
            with ``name``, ``type``, and ``path``), and ``count``.
            Returns an error list if the bridge is unreachable.
        """
        try:
            result = _bridge_get(
                "list_network_children",
                {"operator_path": operator_path, "type_filter": type_filter},
            )
            return result
        except httpx.HTTPError as exc:
            return [{"status": "error", "message": str(exc)}]

    @mcp.tool()
    def td_set_parameter(
        operator_path: str, parameter_name: str, value: str
    ) -> dict[str, Any]:
        """Set the value of a TouchDesigner operator parameter.

        Real TD equivalent:
            op(operator_path).par[parameter_name] = value

        The bridge coerces the ``value`` string (tries float first,
        then falls back to string) before assigning.

        Args:
            operator_path: TD-style path to the operator
                (e.g. ``base_comp/constant1``).
            parameter_name: Name of the parameter to set
                (e.g. ``value0v``).
            value: The value to assign, sent as a string. The bridge
                will attempt numeric coercion.

        Returns:
            A dict with ``operator``, ``parameter``,
            ``previous_value``, and ``new_value``. Returns an error
            dict if the bridge is unreachable.
        """
        try:
            return _bridge_get(
                "set_parameter",
                {
                    "operator_path": operator_path,
                    "parameter_name": parameter_name,
                    "value": value,
                },
            )
        except httpx.HTTPError as exc:
            return _bridge_error("set_parameter", exc)

    @mcp.tool()
    def td_read_chop_channel(
        operator_path: str,
        channel_name: str,
        start: int = 0,
        count: int = 100,
    ) -> dict[str, Any]:
        """Read sample values from a CHOP channel.

        Real TD equivalent:
            chan = op(operator_path).chan(channel_name)
            samples = [chan[i] for i in range(start, start + count)]

        Args:
            operator_path: TD-style path to the CHOP operator
                (e.g. ``base_comp/constant1``).
            channel_name: Name of the channel to read
                (e.g. ``chan1``).
            start: Sample index to start reading from (default: 0).
            count: Maximum number of samples to return (default: 100).

        Returns:
            A dict with ``operator``, ``channel``, ``samples`` (list of
            float values), and ``length`` (total channel length).
            Returns an error dict if the bridge is unreachable.
        """
        try:
            return _bridge_get(
                "read_chop_channel",
                {
                    "operator_path": operator_path,
                    "channel_name": channel_name,
                    "start": str(start),
                    "count": str(count),
                },
            )
        except httpx.HTTPError as exc:
            return _bridge_error("read_chop_channel", exc)

    return mcp


# ── Entry Point ──────────────────────────────────────────────────────

def main() -> None:
    """Start the MCP server on the configured host and port."""
    mcp = _build_server()

    print(f"MCP Server '{SERVER_NAME}' starting on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Transport:  streamable-http (endpoint: /mcp)")
    print(f"Bridge URL: {BRIDGE_URL}")
    print()
    print("Registered tools (6):")
    print("  - td_get_parameter")
    print("  - td_get_dat_text")
    print("  - td_pulse_trigger")
    print("  - td_list_network_children")
    print("  - td_set_parameter")
    print("  - td_read_chop_channel")
    print()
    print("Verification:")
    print(
        f"  curl -X POST http://{SERVER_HOST}:{SERVER_PORT}/mcp"
        ' -H "Content-Type: application/json"'
        ' -d \'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\''
    )
    print()

    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
