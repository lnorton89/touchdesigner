---
status: passed
phase: 03-td-tool-calling
updated: "2026-07-01T00:05:00.000Z"
automated_status: passed
human_status: passed
---

# Phase 3 Verification: TD Tool Calling

## Automated Verification

Command:

```powershell
python -m pytest -q
```

Result: passed, 45 tests.

Covered:

- Tool registration and provider schema serialization.
- TD-style operator descriptor discovery.
- OpenAI-style tool-call parsing and execution.
- Invalid tool-call error normalization.
- Agent history integration for tool result messages.
- MCP bridge tool demo route coverage.

## Live Verification

TouchDesigner `demo/demo.toe` opened, stayed alive after 20 seconds, and passed:

- Deterministic provider-style tool execution.
- Real local model-requested tool call through llama.cpp.
- Invalid tool-call recoverable error path.
- CHOP-specific tool action: `set_demo_chop` set `/project1/base_llm_demo/tool_chop.par.value0` to `7.5`.

## Decision

Phase 3 is complete. Automated tests pass and live TouchDesigner UAT covers tool declaration, discovery, provider schema serialization, model-requested TD tool execution, invalid tool-call errors, and the CHOP-specific example.
