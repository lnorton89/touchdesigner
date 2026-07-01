---
status: complete
phase: 03-td-tool-calling
plan: 03-01
updated: "2026-06-30T23:58:00.000Z"
---

# Plan 03-01 Summary: Tool Registry And Model Tool Call Slice

## Built

- Added `td_components/llm_tool_registry/ToolRegistryExt.py`.
- Tools can be registered directly or discovered from TD-style operator descriptors via `GetTool()`.
- Tool schemas are emitted in OpenAI-compatible `tools` format.
- Tool calls parse provider-style `function.name` and JSON `function.arguments`.
- Invalid tool-call JSON returns a structured error message instead of crashing.
- `LLMAgent.apply_tool_calls(...)` executes tool calls and appends `role: tool` messages into history.
- Generated demo now includes `llm_tool_registry`, `tool_value`, and `tool_result` operators.
- MCP bridge now exposes `tool_demo_action` for list/execute/invalid/model-start/model-collect UAT.

## Verification

```powershell
python -m pytest -q
```

Result: 45 tests passed.

Live deterministic tool UAT:

- `tool_demo_action?action=list` returned OpenAI-compatible schema for `set_demo_value`.
- `tool_demo_action?action=execute` wrote `Tool call wrote this from TD` into `tool_value`.
- Agent history appended a `role: tool` result message.

Live model-requested tool UAT:

- Local llama.cpp emitted `finish_reason: tool_calls` with `set_demo_value`.
- `tool_demo_action?action=model_collect` executed the model-requested tool call.
- `tool_value` became `model requested tool call`.
- `agent_history` recorded the tool call result.
- TouchDesigner stayed alive/responding.

Invalid tool UAT:

- `tool_demo_action?action=invalid` produced `invalid tool arguments JSON for set_demo_value`.
- Agent state became `error`, `agent_error` contained the clear message, and TouchDesigner stayed alive.

CHOP tool UAT:

- `tool_demo_action?action=chop` executed `set_demo_chop`.
- Agent history recorded a `role: tool` result for `/project1/base_llm_demo/tool_chop`.
- Bridge `get_parameter` confirmed `tool_chop.par.value0` was `7.5`.
