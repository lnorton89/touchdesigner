import json
import unittest

from td_components.llm_agent.AgentExt import LLMAgent
from td_components.llm_tool_registry.ToolRegistryExt import ToolRegistry, execute_tool_calls


class ToolRegistryTests(unittest.TestCase):
    def test_register_tool_exposes_openai_provider_schema(self):
        registry = ToolRegistry()
        registry.register_tool(
            "read_value",
            lambda path: f"value at {path}",
            description="Read a TD value",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        )

        self.assertEqual(
            registry.provider_tools(),
            [
                {
                    "type": "function",
                    "function": {
                        "name": "read_value",
                        "description": "Read a TD value",
                        "parameters": {
                            "type": "object",
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"],
                        },
                    },
                }
            ],
        )

    def test_execute_openai_style_tool_call(self):
        registry = ToolRegistry()
        registry.register_tool("set_value", lambda path, value: {"path": path, "value": value})

        result = registry.execute_tool_call(
            {
                "id": "call_1",
                "function": {
                    "name": "set_value",
                    "arguments": json.dumps({"path": "/project1/value", "value": 7}),
                },
            }
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["tool_call_id"], "call_1")
        self.assertEqual(result["result"], {"path": "/project1/value", "value": 7})

    def test_invalid_tool_call_returns_error_message(self):
        registry = ToolRegistry()

        result = execute_tool_calls(
            registry,
            [{"id": "bad", "function": {"name": "missing", "arguments": "not json"}}],
        )[0]

        self.assertEqual(result["status"], "error")
        self.assertIn("invalid tool arguments JSON", result["content"])

    def test_discover_tool_from_operator_descriptor(self):
        class ToolOp:
            name = "value_tool"

            def GetTool(self):
                return {
                    "name": "value_tool",
                    "description": "Read demo value",
                    "method": "RunTool",
                    "parameters": {"type": "object", "properties": {}},
                }

            def RunTool(self):
                return "42"

        class Root:
            children = [ToolOp()]

        registry = ToolRegistry()

        discovered = registry.discover_tools(Root())
        result = registry.execute_tool_call({"name": "value_tool", "arguments": {}})

        self.assertEqual(discovered[0]["name"], "value_tool")
        self.assertEqual(result["result"], "42")

    def test_agent_applies_tool_results_to_history(self):
        registry = ToolRegistry()
        registry.register_tool("read_demo", lambda: {"value": 3})
        agent = LLMAgent()

        state = agent.apply_tool_calls([{"name": "read_demo", "arguments": {}}], registry)

        self.assertEqual(state["state"], "complete")
        self.assertEqual(state["history"][-1]["role"], "tool")
        self.assertIn('"value": 3', state["history"][-1]["content"])


if __name__ == "__main__":
    unittest.main()

