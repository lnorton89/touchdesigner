---
status: complete
phase: 03-td-tool-calling
source:
  - 03-01-SUMMARY.md
updated: "2026-06-30T23:58:00.000Z"
---

# Phase 3 UAT: TD Tool Calling

## Tests

### 1. Tool Declaration Convention

expected: Tool authors can expose a callable TD operator using a documented method, tag, or custom parameter convention.
result: pass
evidence: `ToolRegistry.register_from_operator(...)` discovers TD-style `GetTool()` descriptors and method handlers.

### 2. Tool Discovery

expected: Agent or registry discovers available tools from a configured registry/input/path.
result: pass
evidence: `ToolRegistry.discover_tools(...)` and live `tool_demo_action?action=list` expose `set_demo_value`.

### 3. Provider Schema

expected: Tool parameter schemas serialize into provider-compatible tool definitions.
result: pass
evidence: Live `tool_demo_action?action=list` returned OpenAI-style `{"type":"function","function":...}` schema.

### 4. Model-Requested Tool Round Trip

expected: Model requests a TD-native tool, TD executes it, and result returns to conversation.
result: pass
evidence: Local llama.cpp emitted `set_demo_value` tool call; `model_collect` executed it, wrote `tool_value: model requested tool call`, and appended a `role: tool` Agent history message.

### 5. Invalid Tool Call Error

expected: Invalid or unsupported tool-call output appears as a clear recoverable error.
result: pass
evidence: `tool_demo_action?action=invalid` set Agent error state and `agent_error: invalid tool arguments JSON for set_demo_value`.

### 6. CHOP Tool Example

expected: Demo tool reads or sets a CHOP value.
result: pass
evidence: `tool_demo_action?action=chop` executed `set_demo_chop`, Agent history recorded a `role: tool` result for `/project1/base_llm_demo/tool_chop`, and bridge `get_parameter` confirmed `tool_chop.par.value0` was `7.5`.

## Summary

total: 6
passed: 6
pending: 0
issues: 0
