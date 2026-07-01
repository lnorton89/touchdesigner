"""TouchDesigner MCP Bridge extension — runs a lightweight HTTP server inside
TD that receives tool execution requests from the companion MCP server.

Architecture:
  companion MCP server → HTTP :9876 → BridgeRequestHandler.do_GET
    → MCPBridge._exec_on_main() → td.op() → BridgeRequestHandler responds

The bridge uses stdlib-only dependencies (``http.server``, ``json``,
``urllib.parse``, ``threading``) and follows the same ``td.run()`` pattern
established by ``ModelRouterExt`` for safe main-thread TD API access from
a daemon thread.
"""

from __future__ import annotations

import json
import socket
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
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, socket.timeout):
            return
        except OSError as exc:
            if getattr(exc, "winerror", None) in {10053, 10054}:
                return
            raise


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
        self._pending_lock = threading.Lock()
        self._pending_calls: list[dict[str, Any]] = []
        self._demo_payload_lock = threading.Lock()
        self._demo_payload: Optional[dict[str, Any]] = None
        self._agent_payload_lock = threading.Lock()
        self._agent_payload: Optional[dict[str, Any]] = None
        self._tool_payload_lock = threading.Lock()
        self._tool_payload: Optional[dict[str, Any]] = None

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

    def _exec_on_main(self, handler_name: str, params: dict[str, str]) -> dict[str, Any]:
        """Execute a TD API handler on TouchDesigner's main thread.

        The HTTP server runs in a daemon thread, but TouchDesigner operator APIs
        such as ``op()`` are only safe from TD's main thread. A TD-side frame
        callback should call ``_drain_pending_calls``; this HTTP thread only
        queues work and waits for the main thread to populate the result.
        """
        if threading.current_thread() is threading.main_thread() and not callable(self._td_run):
            return self._exec_direct(handler_name, params)

        event = threading.Event()
        call_state = {
            "handler_name": handler_name,
            "params": dict(params),
            "event": event,
            "result": None,
            "error": None,
        }

        with self._pending_lock:
            self._pending_calls.append(call_state)

        if not event.wait(config.REQUEST_TIMEOUT):
            with self._pending_lock:
                if call_state in self._pending_calls:
                    self._pending_calls.remove(call_state)
            return {
                "status": "error",
                "error": "timed out waiting for TouchDesigner main thread",
            }

        if call_state["error"] is not None:
            return {"status": "error", "error": str(call_state["error"])}
        return call_state["result"] or {"status": "error", "error": "empty handler result"}

    def _drain_pending_calls(self) -> None:
        """Run queued bridge calls from TouchDesigner's main thread."""
        with self._pending_lock:
            calls = list(self._pending_calls)
            self._pending_calls.clear()

        for call_state in calls:
            try:
                call_state["result"] = self._exec_direct(
                    call_state["handler_name"],
                    call_state["params"],
                )
            except Exception as exc:
                call_state["error"] = exc
            finally:
                call_state["event"].set()

    def _exec_direct(self, handler_name: str, params: dict[str, str]) -> dict[str, Any]:
        """Execute a handler on the current thread.

        This is safe only when called from TouchDesigner's main thread, or during
        standalone tests where a fake ``td.op`` is supplied.
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
        elif handler_name == "router_demo_action":
            return self._td_router_demo_action(params.get("action", "pulse"))
        elif handler_name == "agent_demo_action":
            return self._td_agent_demo_action(params.get("action", "pulse"))
        elif handler_name == "tool_demo_action":
            return self._td_tool_demo_action(params.get("action", "execute"))
        elif handler_name == "create_simple_comp":
            return self._td_create_simple_comp(params)
        elif handler_name == "create_dmx_controller":
            return self._td_create_dmx_controller(params)
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
        return self._exec_on_main("get_parameter", params)

    def get_dat_text(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("get_dat_text", params)

    def pulse_trigger(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("pulse_trigger", params)

    def list_network_children(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("list_network_children", params)

    def set_parameter(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("set_parameter", params)

    def read_chop_channel(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("read_chop_channel", params)

    def router_demo_action(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("router_demo_action", params)

    def agent_demo_action(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("agent_demo_action", params)

    def tool_demo_action(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("tool_demo_action", params)

    def create_simple_comp(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("create_simple_comp", params)

    def create_dmx_controller(self, params: dict[str, str]) -> dict[str, Any]:
        return self._exec_on_main("create_dmx_controller", params)

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

    def _td_router_demo_action(self, action: str) -> dict[str, Any]:
        """Drive the generated Phase 1 Router demo without exposing eval."""
        base = self._td_op("/project1/base_llm_demo")
        router = base.fetch("router", None) if hasattr(base, "fetch") else None
        if router is None:
            return {"status": "error", "error": "router demo instance not found"}

        prompt_dat = base.op("prompt_input")
        callback_dat = base.op("callback_payload")
        action = (action or "pulse").strip().lower()

        if action == "collect":
            with self._demo_payload_lock:
                payload = self._demo_payload
                self._demo_payload = None
            if payload is None:
                return {"status": "pending", "action": action}
            state = router.apply_result(payload)
            callback_dat.text = "\n".join(f"{key}: {value}" for key, value in payload.items())
            return {"status": "ok", "action": action, "payload": payload, "state": state}

        if action == "reset":
            state = router.reset()
            callback_dat.text = "action: reset"
            return {"status": "ok", "action": action, "state": state}

        if action == "retry":
            if not getattr(router, "_last_envelope", None):
                router.request(prompt=prompt_dat.text, trigger_source="pulse", dispatch=False)
            request_id = router.retry(dispatch=False)
            trigger_source = "retry"
            response_text = "Retry demo ready"
            error_text = ""
            status = "complete"
        elif action == "dat_change":
            prompt_dat.text = "Prompt changed by DAT table-change demo"
            request_id = router.request(
                prompt=prompt_dat.text,
                trigger_source="dat_table_change",
                dispatch=False,
            )
            trigger_source = "dat_table_change"
            response_text = "DAT change demo ready"
            error_text = ""
            status = "complete"
        elif action == "slow":
            request_id = router.request(
                prompt=prompt_dat.text,
                trigger_source="slow_demo",
                dispatch=False,
            )
            callback_dat.text = f"request_id: {request_id}\nstatus: running\ntrigger_source: slow_demo"
            return {"status": "ok", "action": action, "request_id": request_id, "state": router.state}
        elif action == "local_endpoint":
            request_id = router.request(
                prompt=prompt_dat.text,
                trigger_source="local_endpoint",
                dispatch=False,
            )
            callback_dat.text = f"request_id: {request_id}\nstatus: running\ntrigger_source: local_endpoint"
            self._submit_local_completion(request_id, prompt_dat.text)
            return {"status": "ok", "action": action, "request_id": request_id, "state": router.state}
        elif action == "error":
            request_id = router.request(
                prompt=prompt_dat.text,
                trigger_source="error_demo",
                dispatch=False,
            )
            trigger_source = "error_demo"
            response_text = ""
            error_text = "Recoverable demo error: endpoint unreachable"
            status = "error"
        else:
            request_id = router.request(
                prompt=prompt_dat.text,
                trigger_source="pulse",
                dispatch=False,
            )
            trigger_source = "pulse"
            response_text = "Pulse demo ready"
            error_text = ""
            status = "complete"

        payload = {
            "request_id": request_id,
            "status": status,
            "response_text": response_text,
            "error_text": error_text,
            "elapsed_ms": 1,
            "trigger_source": trigger_source,
        }
        state = router.apply_result(payload)
        callback_dat.text = "\n".join(f"{key}: {value}" for key, value in payload.items())
        return {"status": "ok", "action": action, "payload": payload, "state": state}

    def _submit_local_completion(self, request_id: int, prompt: str) -> None:
        """Call the local llama.cpp OpenAI-compatible completions endpoint."""
        def worker() -> None:
            import urllib.request

            payload: dict[str, Any]
            try:
                body = json.dumps(
                    {
                        "model": "qwen3-coder-a3b-30b-q4_k_m.gguf",
                        "prompt": prompt or "Reply with: Router local endpoint ready",
                        "max_tokens": 16,
                        "temperature": 0,
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    "http://127.0.0.1:8080/v1/completions",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                text = str(data.get("choices", [{}])[0].get("text", "")).strip()
                payload = {
                    "request_id": request_id,
                    "status": "complete",
                    "response_text": text,
                    "error_text": "",
                    "elapsed_ms": 0,
                    "trigger_source": "local_endpoint",
                }
            except Exception as exc:
                payload = {
                    "request_id": request_id,
                    "status": "error",
                    "response_text": "",
                    "error_text": str(exc),
                    "elapsed_ms": 0,
                    "trigger_source": "local_endpoint",
                }
            with self._demo_payload_lock:
                self._demo_payload = payload

        threading.Thread(target=worker, name="RouterDemo-LocalEndpoint", daemon=True).start()

    def _td_agent_demo_action(self, action: str) -> dict[str, Any]:
        """Drive the generated Phase 2 Agent demo without exposing eval."""
        base = self._td_op("/project1/base_llm_demo")
        agent = base.fetch("agent", None) if hasattr(base, "fetch") else None
        if agent is None:
            return {"status": "error", "error": "agent demo instance not found"}

        action = (action or "pulse").strip().lower()
        if action == "collect":
            with self._agent_payload_lock:
                payload = self._agent_payload
                self._agent_payload = None
            if payload is None:
                return {"status": "pending", "action": action, "state": agent.state}
            state = agent.apply_result(payload)
            return {"status": "ok", "action": action, "payload": payload, "state": state}

        if action == "clear":
            state = agent.clear_history()
            return {"status": "ok", "action": action, "state": state}

        message_dat = base.op("agent_message")
        message = str(getattr(message_dat, "text", "")).split("\n4", 1)[0]
        if action == "local_endpoint":
            request_id = agent.send(
                message,
                dispatch=False,
                config_overrides={
                    "base_url": "http://127.0.0.1:8080/v1",
                    "model": "qwen3-coder-a3b-30b-q4_k_m.gguf",
                    "timeout": 30,
                },
            )
            self._submit_agent_local_chat(request_id, agent._build_messages(system_prompt=None, user_message=message))
            return {"status": "ok", "action": action, "request_id": request_id, "state": agent.state}

        request_id = agent.send(message, dispatch=False)
        payload = {
            "request_id": request_id,
            "status": "complete",
            "response_text": "Agent pulse demo ready",
            "error_text": "",
            "elapsed_ms": 1,
            "trigger_source": "agent",
        }
        state = agent.apply_result(payload)
        return {"status": "ok", "action": action, "payload": payload, "state": state}

    def _submit_agent_local_chat(self, request_id: int, messages: list[dict[str, str]]) -> None:
        """Call local llama.cpp chat completions for the Agent UAT path."""
        def worker() -> None:
            import urllib.request

            payload: dict[str, Any]
            try:
                body = json.dumps(
                    {
                        "model": "qwen3-coder-a3b-30b-q4_k_m.gguf",
                        "messages": messages,
                        "max_tokens": 32,
                        "temperature": 0,
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    "http://127.0.0.1:8080/v1/chat/completions",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                text = str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
                payload = {
                    "request_id": request_id,
                    "status": "complete",
                    "response_text": text,
                    "error_text": "",
                    "elapsed_ms": 0,
                    "trigger_source": "agent_local_endpoint",
                }
            except Exception as exc:
                payload = {
                    "request_id": request_id,
                    "status": "error",
                    "response_text": "",
                    "error_text": str(exc),
                    "elapsed_ms": 0,
                    "trigger_source": "agent_local_endpoint",
                }
            with self._agent_payload_lock:
                self._agent_payload = payload

        threading.Thread(target=worker, name="AgentDemo-LocalEndpoint", daemon=True).start()

    def _td_tool_demo_action(self, action: str) -> dict[str, Any]:
        """Drive the generated Phase 3 tool-call demo."""
        from td_components.llm_tool_registry.ToolRegistryExt import ToolRegistry

        base = self._td_op("/project1/base_llm_demo")
        agent = base.fetch("agent", None) if hasattr(base, "fetch") else None
        if agent is None:
            return {"status": "error", "error": "agent demo instance not found"}

        value_dat = base.op("tool_value")
        result_dat = base.op("tool_result")
        registry = ToolRegistry()

        def set_demo_value(value: str) -> dict[str, str]:
            value_dat.text = str(value)
            return {"operator": "/project1/base_llm_demo/tool_value", "value": value_dat.text}

        def set_demo_chop(value: str) -> dict[str, Any]:
            chop = base.op("tool_chop")
            numeric_value = float(value)
            chop.par.value0 = numeric_value
            return {"operator": "/project1/base_llm_demo/tool_chop", "channel": "toolvalue", "value": numeric_value}

        registry.register_tool(
            "set_demo_value",
            set_demo_value,
            description="Set the generated demo tool_value DAT.",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        )
        registry.register_tool(
            "set_demo_chop",
            set_demo_chop,
            description="Set the generated demo tool_chop Constant CHOP value.",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "number"}},
                "required": ["value"],
            },
        )

        action = (action or "execute").strip().lower()
        if action == "list":
            tools = registry.provider_tools()
            result_dat.text = json.dumps(tools, indent=2)
            return {"status": "ok", "action": action, "tools": tools}

        if action == "model_start":
            tools = registry.provider_tools()
            result_dat.text = "model tool call: running"
            self._submit_model_tool_call(tools)
            return {"status": "ok", "action": action, "state": "running", "tools": tools}

        if action == "model_collect":
            with self._tool_payload_lock:
                payload = self._tool_payload
                self._tool_payload = None
            if payload is None:
                return {"status": "pending", "action": action}
            if payload.get("status") != "ok":
                result_dat.text = json.dumps(payload, indent=2)
                return {"status": "ok", "action": action, "payload": payload}
            tool_calls = payload.get("tool_calls", [])
            state = agent.apply_tool_calls(tool_calls, registry)
            result_dat.text = json.dumps(state["history"][-1], indent=2, default=str)
            return {
                "status": "ok",
                "action": action,
                "tool_calls": tool_calls,
                "tool_value": getattr(value_dat, "text", ""),
                "state": state,
            }

        if action == "invalid":
            tool_calls = [
                {
                    "id": "call_invalid",
                    "function": {"name": "set_demo_value", "arguments": "not json"},
                }
            ]
        elif action == "chop":
            tool_calls = [
                {
                    "id": "call_demo_chop",
                    "function": {
                        "name": "set_demo_chop",
                        "arguments": json.dumps({"value": 7.5}),
                    },
                }
            ]
        else:
            tool_calls = [
                {
                    "id": "call_demo_value",
                    "function": {
                        "name": "set_demo_value",
                        "arguments": json.dumps({"value": "Tool call wrote this from TD"}),
                    },
                }
            ]

        state = agent.apply_tool_calls(tool_calls, registry)
        result_dat.text = json.dumps(state["history"][-1], indent=2, default=str)
        return {
            "status": "ok",
            "action": action,
            "tool_value": getattr(value_dat, "text", ""),
            "state": state,
        }

    def _td_create_simple_comp(self, params: dict[str, str]) -> dict[str, Any]:
        """Create a small generated COMP with a DAT and CHOP network inside."""
        parent_path = params.get("parent_path", "/project1/base_llm_demo")
        requested_name = params.get("name", "generated_simple_comp")
        parent = self._td_op(parent_path)

        comp_name = self._fresh_child_name(parent, requested_name)
        comp = parent.create(self._td_op_type("baseCOMP"), comp_name)
        comp.nodeX = int(params.get("x", "970"))
        comp.nodeY = int(params.get("y", "-375"))
        comp.nodeWidth = 190
        comp.nodeHeight = 120

        readme = comp.create(self._td_op_type("textDAT"), "readme")
        readme.nodeX = 0
        readme.nodeY = 120
        readme.text = (
            "Generated live by the MCP bridge.\n"
            "Network: value_constant -> value_out\n"
            "Try changing value_constant.par.value0."
        )

        constant = comp.create(self._td_op_type("constantCHOP"), "value_constant")
        constant.nodeX = 0
        constant.nodeY = 0
        try:
            constant.par.name0 = "generated"
        except Exception:
            pass
        try:
            constant.par.value0 = float(params.get("value", "3.14"))
        except Exception:
            pass

        output = comp.create(self._td_op_type("nullCHOP"), "value_out")
        output.nodeX = 180
        output.nodeY = 0
        self._connect_ops(constant, output)

        return {
            "status": "ok",
            "parent": parent_path,
            "operator": f"{parent_path.rstrip('/')}/{comp_name}",
            "children": ["readme", "value_constant", "value_out"],
            "value": self._safe_param_value(constant, "value0"),
        }

    def _td_create_dmx_controller(self, params: dict[str, str]) -> dict[str, Any]:
        """Create a simple DMX controller COMP with editable channel levels."""
        parent_path = params.get("parent_path", "/project1/base_llm_demo")
        requested_name = params.get("name", "simple_dmx_controller")
        parent = self._td_op(parent_path)

        comp_name = self._fresh_child_name(parent, requested_name)
        comp = parent.create(self._td_op_type("baseCOMP"), comp_name)
        comp.nodeX = int(params.get("x", "970"))
        comp.nodeY = int(params.get("y", "-160"))
        comp.nodeWidth = 230
        comp.nodeHeight = 150

        patch = [
            ("ch001_dimmer", 255),
            ("ch002_red", 255),
            ("ch003_green", 80),
            ("ch004_blue", 20),
            ("ch005_white", 0),
            ("ch006_strobe", 0),
            ("ch007_pan", 127),
            ("ch008_tilt", 127),
        ]

        readme = comp.create(self._td_op_type("textDAT"), "readme")
        readme.nodeX = 0
        readme.nodeY = 180
        readme.text = (
            "Simple DMX Controller\n"
            "Network: dmx_levels -> dmx_output\n"
            "Values are 0-255 style DMX levels in a Constant CHOP.\n"
            "Wire dmx_output into a real DMX Out / Art-Net / sACN workflow when ready."
        )

        patch_dat = comp.create(self._td_op_type("textDAT"), "fixture_patch")
        patch_dat.nodeX = 180
        patch_dat.nodeY = 180
        patch_dat.text = "\n".join(
            ["channel,name,default"]
            + [f"{index + 1},{name},{value}" for index, (name, value) in enumerate(patch)]
        )

        preview = comp.create(self._td_op_type("textDAT"), "dmx_preview")
        preview.nodeX = 360
        preview.nodeY = 180
        preview.text = "\n".join(f"{name}: {value}" for name, value in patch)

        levels = comp.create(self._td_op_type("constantCHOP"), "dmx_levels")
        levels.nodeX = 0
        levels.nodeY = 0
        for index, (channel_name, value) in enumerate(patch):
            self._set_param_if_present(levels, f"name{index}", channel_name)
            self._set_param_if_present(levels, f"value{index}", value)

        output = comp.create(self._td_op_type("nullCHOP"), "dmx_output")
        output.nodeX = 210
        output.nodeY = 0
        self._connect_ops(levels, output)

        return {
            "status": "ok",
            "parent": parent_path,
            "operator": f"{parent_path.rstrip('/')}/{comp_name}",
            "children": ["readme", "fixture_patch", "dmx_preview", "dmx_levels", "dmx_output"],
            "channels": [{"name": name, "value": value} for name, value in patch],
        }

    def _submit_model_tool_call(self, tools: list[dict[str, Any]]) -> None:
        """Ask the local model to emit a tool call for the Phase 3 demo."""
        def worker() -> None:
            import urllib.request

            payload: dict[str, Any]
            try:
                body = json.dumps(
                    {
                        "model": "qwen3-coder-a3b-30b-q4_k_m.gguf",
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "Use the set_demo_value tool to set the value to "
                                    "model requested tool call. Do not answer normally."
                                ),
                            }
                        ],
                        "tools": tools,
                        "tool_choice": "auto",
                        "temperature": 0,
                        "max_tokens": 64,
                    }
                ).encode("utf-8")
                req = urllib.request.Request(
                    "http://127.0.0.1:8080/v1/chat/completions",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=45) as response:
                    data = json.loads(response.read().decode("utf-8"))
                tool_calls = data.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
                payload = {"status": "ok", "tool_calls": tool_calls, "raw": data}
            except Exception as exc:
                payload = {"status": "error", "error_text": str(exc)}
            with self._tool_payload_lock:
                self._tool_payload = payload

        threading.Thread(target=worker, name="ToolDemo-ModelToolCall", daemon=True).start()

    def _td_op_type(self, name: str) -> Any:
        """Resolve TouchDesigner operator type objects from TD's Python globals."""
        import builtins

        op_type = globals().get(name, None)
        if op_type is None:
            op_type = getattr(builtins, name, None)
        if op_type is None:
            try:
                import td

                op_type = getattr(td, name, None)
            except Exception:
                op_type = None
        if op_type is None:
            raise RuntimeError(f"TouchDesigner operator type not available: {name}")
        return op_type

    @staticmethod
    def _fresh_child_name(parent: Any, requested_name: str) -> str:
        base_name = "".join(ch for ch in str(requested_name or "generated_simple_comp") if ch.isalnum() or ch == "_")
        if not base_name:
            base_name = "generated_simple_comp"
        name = base_name
        index = 2
        while parent.op(name) is not None:
            name = f"{base_name}_{index}"
            index += 1
        return name

    @staticmethod
    def _connect_ops(source: Any, target: Any) -> None:
        setter = getattr(target, "setInput", None)
        if callable(setter):
            setter(0, source)
            return
        try:
            source.outputConnectors[0].connect(target.inputConnectors[0])
        except Exception as exc:
            raise RuntimeError(f"could not connect generated operators: {exc}") from exc

    @staticmethod
    def _safe_param_value(op_obj: Any, name: str) -> Any:
        par = getattr(getattr(op_obj, "par", None), name, None)
        if par is None:
            return None
        return getattr(par, "eval", lambda: getattr(par, "val", None))()

    @staticmethod
    def _set_param_if_present(op_obj: Any, name: str, value: Any) -> bool:
        par = getattr(getattr(op_obj, "par", None), name, None)
        if par is None:
            return False
        par.val = value
        return True

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _ensure_param(params: dict[str, str], name: str) -> str:
        """Extract a required parameter, raising on missing or empty."""
        value = params.get(name, "").strip()
        if not value:
            raise ValueError(f'missing required parameter: "{name}"')
        return value
