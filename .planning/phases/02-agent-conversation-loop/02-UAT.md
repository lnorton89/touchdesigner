---
status: complete
phase: 02-agent-conversation-loop
source:
  - 02-01-SUMMARY.md
updated: "2026-06-30T23:45:00.000Z"
---

# Phase 2 UAT: Agent Conversation Loop

## Tests

### 1. System Prompt And Message Input

expected: Agent accepts a system prompt and user message from DAT or parameter input.
result: pass
evidence: Unit tests verify system prompt, prior history, and user message ordering; generated demo reads `agent_message`.

### 2. History Inspect And Clear

expected: Agent can inspect, append to, and clear conversation history.
result: pass
evidence: Unit tests cover `append_history(...)`, `history`, and `clear_history()`.

### 3. Agent Output DATs

expected: Agent writes raw text and JSON response data into output DATs.
result: pass
evidence: Live demo writes `agent_response`, `agent_response_json`, and `agent_history`.

### 4. Response And Error Events

expected: Response-ready and error events are visible through CHOP-ready channels or equivalent TD triggers.
result: pass
evidence: `agent_status_json` exposes `response_ready`, `done`, `error`, `request_id`, and counters.

### 5. Router Overrides

expected: Agent can override Router endpoint/model for a specific request.
result: pass
evidence: Unit tests verify `config_overrides` are passed from Agent and reflected in Router request envelopes.

### 6. Real Local Endpoint Agent Dispatch

expected: Agent dispatches through Router to a local OpenAI-compatible endpoint and writes the real model response.
result: pass
evidence: `agent_demo_action?action=local_endpoint` started request `3`; `agent_demo_action?action=collect` applied local llama.cpp response `Hello! This is the Agent speaking. How can I assist you today?` into `agent_response`; `agent_status_json` showed `state: complete`, `response_ready: 1`, `history_length: 4`, and `error_count: 0`.

## Summary

total: 6
passed: 6
pending: 0
issues: 0
