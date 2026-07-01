"""Tool discovery and execution helpers for TouchDesigner Agent tools."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, Mapping, Optional


class ToolRegistry:
    """Registry for TD-native tools exposed to Agent/model calls."""

    def __init__(self, ownerComp: Any = None):
        self.ownerComp = ownerComp
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        description: str = "",
        parameters: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        tool_name = self._normalize_name(name)
        if not callable(handler):
            raise ValueError(f"tool handler for {tool_name} is not callable")

        descriptor = {
            "name": tool_name,
            "description": str(description or ""),
            "parameters": dict(parameters or {"type": "object", "properties": {}}),
            "handler": handler,
        }
        self._tools[tool_name] = descriptor
        return self.describe_tool(tool_name)

    def register_from_operator(self, op_obj: Any) -> Optional[Dict[str, Any]]:
        getter = getattr(op_obj, "GetTool", None)
        if not callable(getter):
            ext = getattr(op_obj, "ext", None)
            getter = getattr(ext, "GetTool", None) if ext is not None else None
        if not callable(getter):
            return None

        descriptor = dict(getter())
        name = self._normalize_name(descriptor.get("name", getattr(op_obj, "name", "")))
        method_name = str(descriptor.get("method", "RunTool"))
        handler = getattr(op_obj, method_name, None)
        if not callable(handler):
            ext = getattr(op_obj, "ext", None)
            handler = getattr(ext, method_name, None) if ext is not None else None
        if not callable(handler):
            raise ValueError(f"tool {name} method {method_name} is not callable")

        return self.register_tool(
            name,
            handler,
            description=str(descriptor.get("description", "")),
            parameters=descriptor.get("parameters", {}),
        )

    def discover_tools(self, root: Any = None) -> list[Dict[str, Any]]:
        root_obj = root or self.ownerComp
        children = getattr(root_obj, "children", [])
        discovered = []
        for child in children:
            descriptor = self.register_from_operator(child)
            if descriptor is not None:
                discovered.append(descriptor)
        return discovered

    def list_tools(self) -> list[Dict[str, Any]]:
        return [self.describe_tool(name) for name in sorted(self._tools)]

    def provider_tools(self) -> list[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in self.list_tools()
        ]

    def execute_tool_call(self, call: Mapping[str, Any]) -> Dict[str, Any]:
        parsed = self.parse_tool_call(call)
        tool = self._tools.get(parsed["name"])
        if tool is None:
            return self._tool_error(parsed, f"unknown tool: {parsed['name']}")

        try:
            result = tool["handler"](**parsed["arguments"])
            content = json.dumps({"status": "ok", "result": result}, default=str)
            return {
                "status": "ok",
                "role": "tool",
                "tool_call_id": parsed["id"],
                "name": parsed["name"],
                "content": content,
                "result": result,
            }
        except Exception as exc:
            return self._tool_error(parsed, str(exc))

    def parse_tool_call(self, call: Mapping[str, Any]) -> Dict[str, Any]:
        function = call.get("function", call)
        name = self._normalize_name(function.get("name", call.get("name", "")))
        raw_arguments = function.get("arguments", call.get("arguments", {}))
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments or "{}")
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid tool arguments JSON for {name}") from exc
        else:
            arguments = dict(raw_arguments or {})

        if not isinstance(arguments, dict):
            raise ValueError(f"tool arguments for {name} must be an object")

        return {
            "id": str(call.get("id", name)),
            "name": name,
            "arguments": arguments,
        }

    def describe_tool(self, name: str) -> Dict[str, Any]:
        tool = self._tools[self._normalize_name(name)]
        return {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": dict(tool["parameters"]),
        }

    @staticmethod
    def _normalize_name(name: Any) -> str:
        value = str(name or "").strip()
        if not value:
            raise ValueError("tool name is required")
        return value

    @staticmethod
    def _tool_error(parsed: Mapping[str, Any], message: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "role": "tool",
            "tool_call_id": parsed.get("id", parsed.get("name", "")),
            "name": parsed.get("name", ""),
            "content": json.dumps({"status": "error", "error": message}),
            "error_text": message,
        }


def execute_tool_calls(
    registry: ToolRegistry, tool_calls: Iterable[Mapping[str, Any]]
) -> list[Dict[str, Any]]:
    """Execute provider-style tool calls and return tool result messages."""
    results = []
    for call in tool_calls:
        try:
            results.append(registry.execute_tool_call(call))
        except Exception as exc:
            name = ""
            try:
                name = str(call.get("function", call).get("name", ""))
            except Exception:
                pass
            results.append(
                {
                    "status": "error",
                    "role": "tool",
                    "tool_call_id": str(call.get("id", name)) if isinstance(call, Mapping) else name,
                    "name": name,
                    "content": json.dumps({"status": "error", "error": str(exc)}),
                    "error_text": str(exc),
                }
            )
    return results

