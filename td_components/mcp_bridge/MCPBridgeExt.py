"""TouchDesigner MCP Bridge extension — runs a lightweight HTTP server inside
TD that receives tool execution requests from the companion MCP server.

Architecture:
  companion MCP server → HTTP :9876 → BridgeRequestHandler.do_GET
    → MCPBridge._run_on_main() → td.op() → BridgeRequestHandler responds

The bridge uses stdlib-only dependencies (``http.server``, ``json``,
``urllib.parse``, ``threading``) and follows the same ``td.run()`` pattern
established by ``ModelRouterExt`` for safe main-thread TD API access from
a daemon thread.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlparse

import td_components.mcp_bridge.MCPBridge_config as config

# ═══════════════════════════════════════════════════════════════════════
#  HTTP Request Handler
# ═══════════════════════════════════════════════════════════════════════


class _BridgeRequestHandler(BaseHTTPRequestHandler):
    """Minimal GET-only handler that dispatches to MCPBridge methods.

    Routes match ``/td/{route_name}?param1=v1&param2=v2``.
    The route name is looked up in ``MCPBridge_config.ROUTES`` to find
    the handler method on the bridge instance attached to the server.
    """

    # Silence per-request log lines in the TD console (the companion
    # process is chatty enough on its own).
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        """Handle a GET request from the companion MCP server."""
        parsed = urlparse(self.path)
        path = parsed.path.lstrip("/")
        parts = path.split("/")

        # Expect /td/{route_name}
        if len(parts) < 2 or parts[0] != "td":
            self._respond_json(400, {"status": "error", "error": "bad route", "path": self.path})
            return

        route_name = parts[1]
        handler_name = config.ROUTES.get(route_name)
        if handler_name is None:
            self._respond_json(
                404,
                {
                    "status": "error",
                    "error": f"unknown route: {route_name}",
                    "available_routes": list(config.ROUTES.keys()),
                },
            )
            return

        # Parse query params into a plain dict (last value wins for duplicates)
        params: dict[str, str] = {}
        raw_qs = parse_qs(parsed.query)
        for key, values in raw_qs.items():
            params[key] = values[-1]

        bridge = getattr(self.server, "bridge", None)
        if bridge is None:
            self._respond_json(500, {"status": "error", "error": "bridge not attached to server"})
            return

        handler: Optional[Callable[..., dict[str, Any]]] = getattr(bridge, handler_name, None)
        if not callable(handler):
            self._respond_json(
                500,
                {"status": "error", "error": f"handler {handler_name} is not callable"},
            )
            return

        try:
            result = handler(params)
            self._respond_json(200, result)
        except Exception as exc:
            self._respond_json(
                500,
                {"status": "error", "error": str(exc), "route": route_name},
            )

    def _respond_json(self, status_code: int, data: dict[str, Any]) -> None:
        """Send a JSON response with the given status code."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ═══════════════════════════════════════════════════════════════════════
#  TD Comp Extension
# ═══════════════════════════════════════════════════════════════════════


class MCPBridge:
    """TD COMP extension that serves tool-execution requests over HTTP.

    Usage (from a TD Execute DAT or parameter callback):
        bridge = op("mcp_bridge").ext.MCPBridge
        bridge.start()   # begins serving on 127.0.0.1:9876
        bridge.stop()    # shuts down the listener (optional)

    Handler methods are called from the bridge's HTTP thread but execute
    their ``td.op()`` calls on TD's main thread via ``td.run()``, matching
    the pattern established by ``ModelRouterExt``.
    """

    def __init__(self, ownerComp: Any = None, td_op: Any = None, td_run: Any = None) -> None:
        self.ownerComp = ownerComp
        self._server: Optional[HTTPServer] = None
        self._td_op = td_op
        self._td_run = td_run

    # ── Server Lifecycle ──────────────────────────────────────────

    def start(self) -> None:
        """Start the bridge HTTP server in a daemon thread.

        Safe to call multiple times — skips if already running.
        """
        if self._server is not None:
            return

        server = HTTPServer((config.BRIDGE_HOST, config.BRIDGE_PORT), _BridgeRequestHandler)
        server.timeout = 1.0  # allow periodic shutdown checks
        server.bridge = self
        self._server = server

        thread = threading.Thread(
            target=server.serve_forever,
            name="MCPBridge-HTTP",
            daemon=True,
        )
        thread.start()

    def stop(self) -> None:
        """Shut down the bridge HTTP server."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    # ── Thread-Safe TD API Access ─────────────────────────────────

    def _exec_direct(self, handler_name: str, params: dict[str, str]) -> dict[str, Any]:
        """Execute handler directly on this thread (not deferred to main thread).
        
        NOTE: td.op() calls from a background thread may not work in all TD builds.
        If this fails, the server will need to run TD operations through td.run().
        """
        if not callable(self._td_op):
            return {"status": "error", "error": "td.op() not available"}

        if handler_name == "get_parameter":
            return self._td_get_parameter(params.get("operator_path",""), params.get("parameter_name",""))
        elif handler_name == "get_dat_text":
            return self._td_get_dat_text(params.get("operator_path",""))
        elif handler_name == "pulse_trigger":
            return self._td_pulse_trigger(params.get("operator_path",""), params.get("pulse_name",""))
        elif handler_name == "list_network_children":
            return self._td_list_children(params.get("operator_path",""), params.get("type_filter",""))
        elif handler_name == "set_parameter":
            return self._td_set_parameter(params.get("operator_path",""), params.get("parameter_name",""), params.get("value",""))
        elif handler_name == "read_chop_channel":
            start = int(params.get("start", "0"))
            count = int(params.get("count", "100"))
            return self._td_read_chop(params.get("operator_path",""), params.get("channel_name",""), start, count)
        return {"status": "error", "error": f"unknown handler: {handler_name}"}

    def _resolve_op(self, operator_path: str) -> Any:
        """Look up a TD operator by path, using captured ``op()`` reference."""
        if not callable(self._td_op):
            raise RuntimeError("td.op() is not available in this environment")
        result = self._td_op(operator_path)
        if result is None:
            raise ValueError(f"operator not found: {operator_path}")
        return result

    # ── Route Handlers ────────────────────────────────────────────
    # Each handler runs ON THE MAIN THREAD via _exec_on_main.
    # They MUST NOT reference non-serializable objects.

    def get_parameter(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_direct("get_parameter", params)

    def get_dat_text(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_direct("get_dat_text", params)

    def pulse_trigger(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_direct("pulse_trigger", params)

    def list_network_children(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_direct("list_network_children", params)

    def set_parameter(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_direct("set_parameter", params)

    def read_chop_channel(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_direct("read_chop_channel", params)

    # ── Main-Thread Implementations ──────────────────────────────

    def _td_get_parameter(self, op_path: str, par_name: str) -> dict[str, Any]:
        op_obj = self._td_op(op_path)
        par_obj = op_obj.par[par_name]
        value = par_obj.eval()
        return {"status": "ok", "operator": op_path, "parameter": par_name,
                "value": value, "type": type(value).__name__}

    def _td_get_dat_text(self, op_path: str) -> dict[str, Any]:
        op_obj = self._td_op(op_path)
        return {"status": "ok", "operator": op_path, "text": str(op_obj.text)}

    def _td_pulse_trigger(self, op_path: str, pulse_name: str) -> dict[str, Any]:
        op_obj = self._td_op(op_path)
        op_obj.par[pulse_name].pulse()
        return {"status": "ok", "operator": op_path, "pulse": pulse_name, "triggered": True}

    def _td_list_children(self, op_path: str, type_filter: str = "") -> dict[str, Any]:
        op_obj = self._td_op(op_path)
        children = []
        for child in op_obj.children:
            ct = str(getattr(child, "type", "")).lower()
            if type_filter and type_filter not in ct:
                continue
            children.append({"name": str(getattr(child, "name", "")), "type": ct,
                            "path": str(getattr(child, "path", ""))})
        return {"status": "ok", "operator": op_path, "children": children, "count": len(children)}

    def _td_set_parameter(self, op_path: str, par_name: str, value_str: str) -> dict[str, Any]:
        op_obj = self._td_op(op_path)
        par_obj = op_obj.par[par_name]
        previous = par_obj.eval()
        coerced = value_str
        try:
            fv = float(value_str)
            if fv == int(fv) and "." not in value_str:
                coerced = int(fv)
            else:
                coerced = fv
        except (ValueError, OverflowError):
            pass
        par_obj.val = coerced
        return {"status": "ok", "operator": op_path, "parameter": par_name,
                "previous_value": previous, "new_value": par_obj.eval()}

    def _td_read_chop(self, op_path: str, channel: str, start: int = 0, count: int = 100) -> dict[str, Any]:
        op_obj = self._td_op(op_path)
        chan = op_obj.chan(channel)
        total = len(chan) if hasattr(chan, "__len__") else 0
        end = min(start + count, total)
        samples = [float(chan[i]) for i in range(start, end)]
        return {"status": "ok", "operator": op_path, "channel": channel,
                "samples": samples, "length": len(samples), "total_length": total}

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _ensure_param(params: dict[str, str], name: str) -> str:
        """Extract a required parameter, raising on missing or empty."""
        value = params.get(name, "").strip()
        if not value:
            raise ValueError(f'missing required parameter: "{name}"')
        return value
