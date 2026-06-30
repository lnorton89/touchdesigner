"""
MCP Server Sketch — TouchDesigner Capability Exposure.

This script is a proof-of-concept for exposing TouchDesigner operator
capabilities as MCP (Model Context Protocol) tools. It uses the mcp
Python SDK (v2 alpha API) to create a minimal server with three mock
tools that mirror real TD API calls.

In a production integration, each tool's mock implementation would be
replaced with actual calls to TouchDesigner's embedded Python API
(e.g., td.op(), td.par, td.mod()). The server would run as a companion
process alongside TD, communicating over localhost HTTP.

Transport:    streamable-http on 127.0.0.1:8765
SDK API:      MCPServer from mcp.server.mcpserver (v2)
Python:       3.11+ (matches TD 2022's embedded Python)

── Verification ──────────────────────────────────────────────────────

After installing the mcp package and starting the server:

    python mcp_td_sketch.py

Then from another terminal:

    # Health check via MCP protocol (JSON-RPC)
    curl -X POST http://127.0.0.1:8765/mcp \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

    # Or use the MCP Inspector:
    npx @modelcontextprotocol/inspector http://127.0.0.1:8765/mcp

── Dependencies ──────────────────────────────────────────────────────

    pip install "mcp>=1.27,<2"

The sketch uses the v2 API (MCPServer) for forward-compatibility.
If mcp v2 is not available, the sketch can be adapted to use FastMCP
(v1 stable API) by swapping the import and class.

── Production Tool Mapping ───────────────────────────────────────────

| Sketch Tool          | TD Equivalent                           |
|----------------------|-----------------------------------------|
| td_get_parameter     | op(operator_path).par[parameter_name].eval() |
| td_get_dat_text      | op(operator_path).text                  |
| td_pulse_trigger     | op(operator_path).par[pulse_name].pulse()   |

Each tool returns realistic mock data matching the shape that a
production implementation would produce when connected to a live
TouchDesigner session.
"""

from __future__ import annotations

from typing import Any, Dict

# ── MCP Server Setup ─────────────────────────────────────────────────
# In production, this import loads from the external venv's site-packages
# via TD's startup path injection (see scripts/setup-td-path.py).
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    # Fallback for environments where mcp is not installed — the sketch
    # still compiles and serves as an API reference.
    MCPServer = None  # type: ignore[assignment]

# ── Server Configuration ─────────────────────────────────────────────

SERVER_NAME = "TD-MCP-Gateway"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8765

# ── Mock Data ────────────────────────────────────────────────────────
# These simulate what a real TD session would return through td.op().

_MOCK_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "base_comp/constant1.value0v": {
        "type": "float",
        "value": 0.5,
    },
    "base_comp/constant1.value1v": {
        "type": "float",
        "value": -0.25,
    },
    "base_comp/text_dat.text": {
        "type": "str",
        "value": "Hello from TouchDesigner",
    },
    "base_comp/movie_in.file": {
        "type": "str",
        "value": "C:/media/video.mp4",
    },
}

_MOCK_DAT_TEXTS: Dict[str, str] = {
    "base_comp/table1": "Row1,Value1\r\nRow2,Value2\r\nRow3,Value3",
    "base_comp/text1": "This is a sample Text DAT.\nIt has multiple lines.\nLine three.",
    "base_comp/script1": "# TouchDesigner Python script\nprint('hello')",
}

_DEFAULT_DAT_TEXT = "Row1,Value1\r\nRow2,Value2"


def _build_server() -> MCPServer:  # type: ignore[valid-type]
    """Create and return a configured MCP server with all TD tools registered."""

    if MCPServer is None:
        raise ImportError(
            "The 'mcp' package is not installed. "
            "Install it with: pip install 'mcp>=1.27,<2'"
        )

    mcp = MCPServer(SERVER_NAME)

    # ── Tools ────────────────────────────────────────────────────────

    @mcp.tool()
    def td_get_parameter(operator_path: str, parameter_name: str) -> dict:
        """Read the current value of a TouchDesigner operator parameter.

        Real TD equivalent:
            value = op(operator_path).par[parameter_name].eval()
            return {"value": value, "type": type(value).__name__}

        This mock returns a pre-configured value for known operators or
        a sensible default for unknown ones.

        Args:
            operator_path: TD-style path to the operator (e.g., "base_comp/constant1").
            parameter_name: Name of the parameter to read (e.g., "value0v").

        Returns:
            A dict with keys: operator, parameter, value, type.
        """
        key = f"{operator_path}.{parameter_name}"
        if key in _MOCK_PARAMETERS:
            entry = _MOCK_PARAMETERS[key]
        else:
            entry = {"type": "float", "value": 0.0}

        return {
            "operator": operator_path,
            "parameter": parameter_name,
            "value": entry["value"],
            "type": entry["type"],
        }

    @mcp.tool()
    def td_get_dat_text(operator_path: str) -> str:
        """Read the full text content of a TouchDesigner Text or Table DAT.

        Real TD equivalent:
            return op(operator_path).text

        For Table DATs, the text is tab-separated rows. For Text DATs,
        it is the literal text content.

        Args:
            operator_path: TD-style path to the DAT operator (e.g., "base_comp/table1").

        Returns:
            The full text content of the DAT as a single string.
        """
        return _MOCK_DAT_TEXTS.get(operator_path, _DEFAULT_DAT_TEXT)

    @mcp.tool()
    def td_pulse_trigger(operator_path: str, pulse_name: str) -> dict:
        """Trigger a pulse parameter on a TouchDesigner operator.

        Real TD equivalent:
            op(operator_path).par[pulse_name].pulse()
            # Pulse parameters are momentary — they fire once and return to 0.

        Pulses are commonly used in TD to trigger one-shot actions like
        resetting, cooking, or executing scripts.

        Args:
            operator_path: TD-style path to the operator (e.g., "base_comp/button1").
            pulse_name: Name of the pulse parameter (e.g., "Resetpulse").

        Returns:
            A dict with keys: operator, pulse, triggered, frame.
        """
        return {
            "operator": operator_path,
            "pulse": pulse_name,
            "triggered": True,
            "frame": 0,  # In production, this would be td.frame or absTime.frame
        }

    return mcp


# ── Entry Point ──────────────────────────────────────────────────────

def main() -> None:
    """Start the MCP server on the configured host/port."""

    mcp = _build_server()

    print(f"MCP Server '{SERVER_NAME}' starting on {SERVER_HOST}:{SERVER_PORT}")
    print(f"Transport: streamable-http (endpoint: /mcp)")
    print(f"Tools registered: td_get_parameter, td_get_dat_text, td_pulse_trigger")
    print()
    print("Verification commands:")
    print(f"  curl -X POST http://{SERVER_HOST}:{SERVER_PORT}/mcp \\")
    print( "    -H 'Content-Type: application/json' \\")
    print( "    -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}'")
    print()

    # In production companion-process mode, this call blocks and the server
    # handles requests until the process is terminated. Do not call this
    # from inside TD's main thread.
    mcp.run(
        transport="streamable-http",
        host=SERVER_HOST,
        port=SERVER_PORT,
    )


if __name__ == "__main__":
    main()
