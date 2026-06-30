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

from . import MCPBridge_config as config

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

    def __init__(self, ownerComp: Any = None) -> None:
        self.ownerComp = ownerComp
        self._server: Optional[HTTPServer] = None

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

    def _run_on_main(self, func: Callable[..., Any], *args: Any, timeout: float = 5.0) -> Any:
        """Execute *func* on TD's main thread via ``td.run()`` and wait for the result.

        Args:
            func: The function to execute on the main thread.
            *args: Positional arguments forwarded to *func*.
            timeout: Maximum seconds to wait for execution (default: 5.0).

        Returns:
            The return value of *func*.

        Raises:
            TimeoutError: If ``td.run()`` does not deliver the result
                within *timeout* seconds.
            RuntimeError: If *func* raises an exception on the main
                thread.
        """
        result_holder: dict[str, Any] = {}
        error_holder: dict[str, str] = {}
        event = threading.Event()

        def wrapper() -> None:
            try:
                result_holder["data"] = func(*args)
            except Exception as exc:
                error_holder["error"] = str(exc)
            finally:
                event.set()

        try:
            run_func = globals().get("run")
            if callable(run_func):
                run_func("args[0]()", wrapper, endFrame=True, delayFrames=0)
            else:
                wrapper()  # fallback: execute directly (testing outside TD)
        except Exception as exc:
            error_holder["error"] = str(exc)
            event.set()

        if not event.wait(timeout=timeout):
            raise TimeoutError(f"td.run() did not complete within {timeout:d}s")

        if "error" in error_holder:
            raise RuntimeError(error_holder["error"])

        return result_holder.get("data")

    def _resolve_op(self, operator_path: str) -> Any:
        """Look up a TD operator by path, raising on failure.

        Inside TD the ``op()`` function is available as a global.
        Fall back to ``td.op()`` if a ``td`` module is present.
        """
        td_op = globals().get("op")

        if not callable(td_op):
            td_mod = globals().get("td")
            if td_mod is not None:
                td_op = getattr(td_mod, "op", None)
            if not callable(td_op):
                raise RuntimeError("td.op() is not available in this environment")

        result = td_op(operator_path)
        if result is None:
            raise ValueError(f"operator not found: {operator_path}")
        return result

    # ── Route Handlers ────────────────────────────────────────────
    # Each handler receives a dict of query parameters (as strings) and
    # returns a dict suitable for JSON serialization.

    def get_parameter(self, params: dict[str, str]) -> dict[str, Any]:
        """Read the current value of a TD operator parameter.

        ``td.op(operator_path).par[parameter_name].eval()``
        """
        operator_path = self._ensure_param(params, "operator_path")
        parameter_name = self._ensure_param(params, "parameter_name")

        def _impl() -> dict[str, Any]:
            op_obj = self._resolve_op(operator_path)
            par_obj = op_obj.par[parameter_name]
            value = par_obj.eval()
            return {
                "status": "ok",
                "operator": operator_path,
                "parameter": parameter_name,
                "value": value,
                "type": type(value).__name__,
            }

        return self._run_on_main(_impl, timeout=config.REQUEST_TIMEOUT)

    def get_dat_text(self, params: dict[str, str]) -> dict[str, Any]:
        """Read the full text content of a Text or Table DAT.

        ``td.op(operator_path).text``
        """
        operator_path = self._ensure_param(params, "operator_path")

        def _impl() -> dict[str, Any]:
            op_obj = self._resolve_op(operator_path)
            text = op_obj.text
            return {
                "status": "ok",
                "operator": operator_path,
                "text": str(text),
            }

        return self._run_on_main(_impl, timeout=config.REQUEST_TIMEOUT)

    def pulse_trigger(self, params: dict[str, str]) -> dict[str, Any]:
        """Trigger a pulse parameter on a TD operator.

        ``td.op(operator_path).par[pulse_name].pulse()``
        """
        operator_path = self._ensure_param(params, "operator_path")
        pulse_name = self._ensure_param(params, "pulse_name")

        def _impl() -> dict[str, Any]:
            op_obj = self._resolve_op(operator_path)
            op_obj.par[pulse_name].pulse()
            return {
                "status": "ok",
                "operator": operator_path,
                "pulse": pulse_name,
                "triggered": True,
            }

        return self._run_on_main(_impl, timeout=config.REQUEST_TIMEOUT)

    def list_network_children(self, params: dict[str, str]) -> dict[str, Any]:
        """List child operators inside a network component.

        ``td.op(operator_path).children``, optionally filtered by type.
        """
        operator_path = self._ensure_param(params, "operator_path")
        type_filter = params.get("type_filter", "").strip().lower()

        def _impl() -> dict[str, Any]:
            op_obj = self._resolve_op(operator_path)
            children: list[dict[str, str]] = []
            for child in op_obj.children:
                child_type = str(getattr(child, "type", "")).lower()
                if type_filter and type_filter not in child_type:
                    continue
                children.append(
                    {
                        "name": str(getattr(child, "name", "")),
                        "type": child_type,
                        "path": str(getattr(child, "path", str(getattr(child, "name", "")))),
                    }
                )
            return {
                "status": "ok",
                "operator": operator_path,
                "children": children,
                "count": len(children),
            }

        return self._run_on_main(_impl, timeout=config.REQUEST_TIMEOUT)

    def set_parameter(self, params: dict[str, str]) -> dict[str, Any]:
        """Set the value of a TD operator parameter.

        ``td.op(operator_path).par[parameter_name] = coerce(value)``

        The bridge attempts to coerce the string *value*: float first,
        then int (from float), then plain string.
        """
        operator_path = self._ensure_param(params, "operator_path")
        parameter_name = self._ensure_param(params, "parameter_name")
        value_str = self._ensure_param(params, "value")

        # Coerce the string value
        coerced: Any = value_str
        try:
            float_val = float(value_str)
            # If it looks like an integer, keep it as int
            if float_val == int(float_val) and "." not in value_str:
                coerced = int(float_val)
            else:
                coerced = float_val
        except (ValueError, OverflowError):
            coerced = value_str

        def _impl() -> dict[str, Any]:
            op_obj = self._resolve_op(operator_path)
            par_obj = op_obj.par[parameter_name]
            previous = par_obj.eval()
            par_obj.val = coerced
            return {
                "status": "ok",
                "operator": operator_path,
                "parameter": parameter_name,
                "previous_value": previous,
                "new_value": par_obj.eval(),
            }

        return self._run_on_main(_impl, timeout=config.REQUEST_TIMEOUT)

    def read_chop_channel(self, params: dict[str, str]) -> dict[str, Any]:
        """Read sample values from a CHOP channel.

        ``td.op(operator_path).chan(channel_name)``, sliced by start/count.
        """
        operator_path = self._ensure_param(params, "operator_path")
        channel_name = self._ensure_param(params, "channel_name")

        try:
            start = int(params.get("start", "0"))
        except (ValueError, TypeError):
            start = 0

        try:
            count = int(params.get("count", "100"))
        except (ValueError, TypeError):
            count = 100

        def _impl() -> dict[str, Any]:
            op_obj = self._resolve_op(operator_path)
            chan = op_obj.chan(channel_name)
            total = len(chan) if hasattr(chan, "__len__") else 0
            end = min(start + count, total)
            samples: list[float] = []
            for i in range(start, end):
                samples.append(float(chan[i]))
            return {
                "status": "ok",
                "operator": operator_path,
                "channel": channel_name,
                "samples": samples,
                "length": len(samples),
                "total_length": total,
            }

        return self._run_on_main(_impl, timeout=config.REQUEST_TIMEOUT)

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _ensure_param(params: dict[str, str], name: str) -> str:
        """Extract a required parameter, raising on missing or empty."""
        value = params.get(name, "").strip()
        if not value:
            raise ValueError(f'missing required parameter: "{name}"')
        return value
