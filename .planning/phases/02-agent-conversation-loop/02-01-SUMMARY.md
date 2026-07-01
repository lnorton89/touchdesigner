---
status: complete
phase: 02-agent-conversation-loop
plan: 02-01
updated: "2026-06-30T23:45:00.000Z"
---

# Plan 02-01 Summary: Agent Conversation MVP

## Built

- Added `td_components/llm_agent/AgentExt.py` with `LLMAgent`.
- Agent builds messages from optional system prompt, conversation history, and DAT/parameter input.
- Agent delegates requests to `ModelRouter.request(messages=..., trigger_source="agent")`.
- Agent maintains inspectable history and supports `append_history(...)` plus `clear_history()`.
- Agent writes TD-visible DAT outputs: `agent_response`, `agent_response_json`, `agent_error`, `agent_status_json`, and `agent_history`.
- Agent status exposes CHOP-ready fields including `running`, `done`, `error`, `response_ready`, `request_id`, `history_length`, `complete_count`, and `error_count`.
- `ModelRouter.request(...)` now accepts `config_overrides` for Agent-specific provider, base URL, model, timeout, and API key source overrides.
- `ModelRouter.build_request_envelope(...)` lets the Agent reuse Router validation/config without forcing Router-owned output state.
- Agent real-dispatch path now owns its worker and applies model results back to Agent outputs.
- Generated demo now includes an `llm_agent` COMP, Agent config/message/output DATs, and a compact delayed `agent_runner` Execute DAT.

## Verification

```powershell
python -m pytest -q
```

Result: 36 tests passed.

Live TouchDesigner smoke:

1. Regenerated `demo/demo.toe`.
2. Closed stale TouchDesigner test processes.
3. Launched `demo/demo.toe` in TouchDesigner `2022.25370`.
4. Waited 20 seconds.
5. Confirmed TouchDesigner stayed alive.
6. Queried the MCP bridge:
   - `test_results` -> `Bridge started`, `Router smoke complete`, `Agent smoke complete`
   - `response_text` -> `Router demo ready`
   - `status_json` -> Router `state: complete`
   - `agent_response` -> `Agent demo ready`
   - `agent_status_json` -> Agent `state: complete`, `response_ready: 1`, `history_length: 2`
   - `agent_history` -> user message plus assistant response
   - `agent_error` -> empty

Real local endpoint UAT:

- `agent_demo_action?action=local_endpoint` started a real Agent request inside TouchDesigner.
- Local llama.cpp at `http://127.0.0.1:8080/v1/chat/completions` returned `Hello! This is the Agent speaking. How can I assist you today?`
- `agent_demo_action?action=collect` applied the payload on TouchDesigner's main thread.
- `agent_response`, `agent_status_json`, and `agent_history` reflected the real model response.
- TouchDesigner stayed alive/responding.

## Notes

- The generated Text DAT encoder still appends small artifact text to some DAT contents. Execute DATs now end with a comment sentinel so artifacts do not become Python syntax errors. The Agent demo runner sanitizes the generated canned message before sending it.
- Phase 2 UAT is complete. Next phase is TD Tool Calling.
