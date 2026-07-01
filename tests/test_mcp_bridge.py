import unittest
from unittest.mock import patch
import threading

from td_components.mcp_bridge import MCPBridge_config
from td_components.mcp_bridge.MCPBridgeExt import MCPBridge, _BridgeRequestHandler


class MCPBridgeThreadingTests(unittest.TestCase):
    def test_aborted_client_response_does_not_escape_handler(self):
        handler = object.__new__(_BridgeRequestHandler)
        calls = []

        handler.send_response = lambda status: calls.append(("status", status))
        handler.send_header = lambda key, value: calls.append(("header", key, value))
        handler.end_headers = lambda: calls.append(("end",))

        class AbortedWriter:
            def write(self, body):
                raise ConnectionAbortedError(10053, "client closed")

        handler.wfile = AbortedWriter()

        handler._respond_json(200, {"status": "ok"})

        self.assertEqual(calls[0], ("status", 200))

    def test_dat_text_request_is_queued_until_td_frame_drains_it(self):
        state = {"inside_td_run": False, "td_run_called": False}

        class FakeDat:
            text = "Bridge started"

        def fake_op(path):
            if not state["inside_td_run"]:
                raise AssertionError("td.op() called outside scheduled TD run")
            self.assertEqual(path, "/project1/base_llm_demo/test_results")
            return FakeDat()

        bridge = MCPBridge(td_op=fake_op)
        result_holder = {}

        def request_from_http_thread():
            result_holder["result"] = bridge.get_dat_text(
                {"operator_path": "/project1/base_llm_demo/test_results"}
            )

        thread = threading.Thread(target=request_from_http_thread)
        thread.start()

        self.assertTrue(thread.is_alive())
        state["inside_td_run"] = True
        try:
            bridge._drain_pending_calls()
        finally:
            state["inside_td_run"] = False
        thread.join(timeout=1)

        self.assertFalse(thread.is_alive())
        self.assertEqual(
            result_holder["result"],
            {
                "status": "ok",
                "operator": "/project1/base_llm_demo/test_results",
                "text": "Bridge started",
            },
        )

    def test_main_thread_timeout_returns_structured_error(self):
        bridge = MCPBridge(td_op=lambda path: None)
        result_holder = {}

        with patch.object(MCPBridge_config, "REQUEST_TIMEOUT", 0.01):
            thread = threading.Thread(
                target=lambda: result_holder.setdefault(
                    "result",
                    bridge._exec_on_main("get_dat_text", {"operator_path": "/missing"}),
                )
            )
            thread.start()
            thread.join(timeout=1)

        result = result_holder["result"]
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["error"])

    def test_direct_path_remains_available_for_standalone_tests(self):
        class FakeNetwork:
            children = []

        bridge = MCPBridge(td_op=lambda path: FakeNetwork())

        result = bridge.list_network_children({"operator_path": "/project1"})

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["operator"], "/project1")
        self.assertEqual(result["count"], 0)

    def test_router_demo_action_drives_stored_router(self):
        class FakeDat:
            def __init__(self, text=""):
                self.text = text

        class FakePar:
            value0 = 0

        class FakeChop:
            def __init__(self):
                self.par = FakePar()

        class FakeRouter:
            def __init__(self):
                self._last_envelope = None
                self.state = {}

            def request(self, prompt="", trigger_source="pulse", dispatch=False):
                self._last_envelope = {"prompt": prompt, "trigger_source": trigger_source}
                self.state = {"state": "running", "trigger_source": trigger_source}
                return 7

            def apply_result(self, payload):
                self.state = {"state": payload["status"], "payload": payload}
                return self.state

            def reset(self):
                self.state = {"state": "idle"}
                return self.state

            def retry(self, dispatch=False):
                self.state = {"state": "running", "trigger_source": "retry"}
                return 8

        class FakeBase:
            def __init__(self):
                self.router = FakeRouter()
                self.ops = {
                    "prompt_input": FakeDat("hello"),
                    "callback_payload": FakeDat(),
                }

            def fetch(self, key, default=None):
                return self.router if key == "router" else default

            def op(self, name):
                return self.ops[name]

        base = FakeBase()
        bridge = MCPBridge(td_op=lambda path: base)

        result = bridge._td_router_demo_action("dat_change")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["payload"]["trigger_source"], "dat_table_change")
        self.assertIn("status: complete", base.ops["callback_payload"].text)

    def test_agent_demo_action_drives_stored_agent(self):
        class FakeDat:
            text = "agent hello"

        class FakeAgent:
            def __init__(self):
                self.state = {"state": "idle"}
                self.calls = []

            def send(self, message, dispatch=False, config_overrides=None):
                self.calls.append((message, dispatch, config_overrides))
                self.state = {"state": "running", "message": message}
                return 11

            def apply_result(self, payload):
                self.state = {"state": payload["status"], "payload": payload}
                return self.state

            def clear_history(self):
                self.state = {"state": "idle", "history": []}
                return self.state

        class FakeBase:
            def __init__(self):
                self.agent = FakeAgent()
                self.ops = {"agent_message": FakeDat()}

            def fetch(self, key, default=None):
                return self.agent if key == "agent" else default

            def op(self, name):
                return self.ops[name]

        base = FakeBase()
        bridge = MCPBridge(td_op=lambda path: base)

        result = bridge._td_agent_demo_action("pulse")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(base.agent.calls[0], ("agent hello", False, None))
        self.assertEqual(result["state"]["payload"]["response_text"], "Agent pulse demo ready")

        with bridge._agent_payload_lock:
            bridge._agent_payload = {
                "request_id": 12,
                "status": "complete",
                "response_text": "real local response",
                "error_text": "",
            }

        collected = bridge._td_agent_demo_action("collect")

        self.assertEqual(collected["status"], "ok")
        self.assertEqual(collected["state"]["payload"]["response_text"], "real local response")

    def test_agent_demo_action_public_route_uses_main_thread_queue(self):
        bridge = MCPBridge(td_op=lambda path: None)

        with patch.object(bridge, "_exec_on_main") as exec_on_main:
            exec_on_main.return_value = {"status": "ok"}
            result = bridge.agent_demo_action({"action": "pulse"})

        self.assertEqual(result, {"status": "ok"})
        exec_on_main.assert_called_once_with("agent_demo_action", {"action": "pulse"})

    def test_tool_demo_action_executes_tool_and_updates_agent_history(self):
        class FakeDat:
            def __init__(self, text=""):
                self.text = text

        class FakePar:
            value0 = 0

        class FakeChop:
            def __init__(self):
                self.par = FakePar()

        class FakeAgent:
            def __init__(self):
                self.state = {"history": []}

            def apply_tool_calls(self, tool_calls, registry):
                result = registry.execute_tool_call(tool_calls[0])
                self.state = {
                    "history": [
                        {
                            "role": result["role"],
                            "name": result["name"],
                            "content": result["content"],
                        }
                    ]
                }
                return self.state

        class FakeBase:
            def __init__(self):
                self.agent = FakeAgent()
                self.ops = {
                    "tool_value": FakeDat(),
                    "tool_result": FakeDat(),
                    "tool_chop": FakeChop(),
                }

            def fetch(self, key, default=None):
                return self.agent if key == "agent" else default

            def op(self, name):
                return self.ops[name]

        base = FakeBase()
        bridge = MCPBridge(td_op=lambda path: base)

        result = bridge._td_tool_demo_action("execute")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(base.ops["tool_value"].text, "Tool call wrote this from TD")
        self.assertIn("set_demo_value", base.ops["tool_result"].text)

        with bridge._tool_payload_lock:
            bridge._tool_payload = {
                "status": "ok",
                "tool_calls": [
                    {
                        "id": "call_model",
                        "function": {
                            "name": "set_demo_value",
                            "arguments": '{"value":"model wrote this"}',
                        },
                    }
                ],
            }

        collected = bridge._td_tool_demo_action("model_collect")

        self.assertEqual(collected["status"], "ok")
        self.assertEqual(base.ops["tool_value"].text, "model wrote this")

        chop_result = bridge._td_tool_demo_action("chop")

        self.assertEqual(chop_result["status"], "ok")
        self.assertEqual(base.ops["tool_chop"].par.value0, 7.5)

    def test_tool_demo_action_public_route_uses_main_thread_queue(self):
        bridge = MCPBridge(td_op=lambda path: None)

        with patch.object(bridge, "_exec_on_main") as exec_on_main:
            exec_on_main.return_value = {"status": "ok"}
            result = bridge.tool_demo_action({"action": "execute"})

        self.assertEqual(result, {"status": "ok"})
        exec_on_main.assert_called_once_with("tool_demo_action", {"action": "execute"})

    def test_create_simple_comp_public_route_uses_main_thread_queue(self):
        bridge = MCPBridge(td_op=lambda path: None)

        with patch.object(bridge, "_exec_on_main") as exec_on_main:
            exec_on_main.return_value = {"status": "ok"}
            result = bridge.create_simple_comp({"name": "generated_simple_comp"})

        self.assertEqual(result, {"status": "ok"})
        exec_on_main.assert_called_once_with(
            "create_simple_comp", {"name": "generated_simple_comp"}
        )

    def test_create_simple_comp_builds_expected_children(self):
        class FakePar:
            name0 = ""
            value0 = 0

        class FakeOp:
            def __init__(self, name):
                self.name = name
                self.children = {}
                self.par = FakePar()
                self.text = ""
                self.inputs = []

            def create(self, op_type, name):
                child = FakeOp(name)
                child.op_type = op_type
                self.children[name] = child
                return child

            def op(self, name):
                return self.children.get(name)

            def setInput(self, index, source):
                self.inputs.append((index, source.name))

        parent = FakeOp("base_llm_demo")
        bridge = MCPBridge(td_op=lambda path: parent)

        with patch.object(bridge, "_td_op_type", side_effect=lambda name: name):
            result = bridge._td_create_simple_comp(
                {"name": "generated_simple_comp", "value": "6.25"}
            )

        comp = parent.children["generated_simple_comp"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(set(comp.children), {"readme", "value_constant", "value_out"})
        self.assertIn("Generated live", comp.children["readme"].text)
        self.assertEqual(comp.children["value_constant"].par.value0, 6.25)
        self.assertEqual(comp.children["value_out"].inputs, [(0, "value_constant")])

    def test_create_dmx_controller_builds_dmx_network(self):
        class Param:
            def __init__(self):
                self.val = None

            def eval(self):
                return self.val

        class FakePar:
            def __getattr__(self, name):
                param = Param()
                setattr(self, name, param)
                return param

        class FakeOp:
            def __init__(self, name):
                self.name = name
                self.children = {}
                self.par = FakePar()
                self.text = ""
                self.inputs = []

            def create(self, op_type, name):
                child = FakeOp(name)
                child.op_type = op_type
                self.children[name] = child
                return child

            def op(self, name):
                return self.children.get(name)

            def setInput(self, index, source):
                self.inputs.append((index, source.name))

        parent = FakeOp("base_llm_demo")
        bridge = MCPBridge(td_op=lambda path: parent)

        with patch.object(bridge, "_td_op_type", side_effect=lambda name: name):
            result = bridge._td_create_dmx_controller({"name": "simple_dmx_controller"})

        comp = parent.children["simple_dmx_controller"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            set(comp.children),
            {"readme", "fixture_patch", "dmx_preview", "dmx_levels", "dmx_output"},
        )
        self.assertIn("Simple DMX Controller", comp.children["readme"].text)
        self.assertIn("1,ch001_dimmer,255", comp.children["fixture_patch"].text)
        self.assertEqual(comp.children["dmx_levels"].par.name0.eval(), "ch001_dimmer")
        self.assertEqual(comp.children["dmx_levels"].par.value0.eval(), 255)
        self.assertEqual(comp.children["dmx_output"].inputs, [(0, "dmx_levels")])


if __name__ == "__main__":
    unittest.main()
