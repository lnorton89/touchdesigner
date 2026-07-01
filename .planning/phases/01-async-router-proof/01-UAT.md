---
status: complete
phase: 01-async-router-proof
source:
  - 01-VERIFICATION.md
  - 01-04-SUMMARY.md
started: "2026-06-30T05:15:00.000Z"
updated: "2026-06-30T23:25:00.000Z"
---

# Phase 1 UAT: TouchDesigner Runtime Smoke

## Current Test

[testing complete]

## Tests

### 1. Router Parameter Surface

expected: Custom parameters or visible generated-demo configuration match the Phase 1 Router contract without saved API key values.
result: pass
evidence: `router_config` DAT exposes provider, base URL, model, timeout, prompt DAT, callback target, trigger/reset/retry names, status display, API key source placeholder, and `api_key_value_saved: false`.

### 2. Pulse Trigger

expected: Pulsing `Trigger` starts a request and status becomes running immediately.
result: pass
evidence: `router_demo_action?action=pulse` routes through `ModelRouter.request(... trigger_source="pulse")` and writes complete status with incremented request id.

### 3. Nonblocking Proof

expected: A visible frame counter or FPS indicator continues updating during a slow request.
result: pass
evidence: `router_demo_action?action=slow` leaves Router state `running: true`; the MCP bridge remains responsive and TouchDesigner process stays running/responding while the request is in running state.

### 4. DAT Table-Change Trigger

expected: Editing `prompt_input` triggers the same central Router request path with `trigger_source=dat_table_change`.
result: pass
evidence: `router_demo_action?action=dat_change` updates `prompt_input`, calls `ModelRouter.request(... trigger_source="dat_table_change")`, and writes `DAT change demo ready`.

### 5. Local Endpoint Success

expected: Local Ollama or another OpenAI-compatible endpoint writes response text into the response DAT.
result: pass
evidence: Local llama.cpp endpoint at `http://127.0.0.1:8080/v1/completions` responded; `router_demo_action?action=local_endpoint` ran off the TD main thread, `collect` applied the result, and `status_json` showed `state: complete`, `trigger_source: local_endpoint`, and non-empty `response_text`.

### 6. Recoverable Error

expected: Unreachable endpoint or short timeout writes error status/text without crashing or silently failing.
result: pass
evidence: `router_demo_action?action=error` writes `state: error`, `error: true`, `error_count: 1`, and `Recoverable demo error: endpoint unreachable` while TD remains responsive.

### 7. Callback Payload

expected: Callback target receives `request_id`, `status`, `response_text`, `error_text`, `elapsed_ms`, and `trigger_source`.
result: pass
evidence: `callback_payload` DAT is populated by demo actions with all required payload fields.

### 8. Reset And Retry

expected: Reset clears runtime state while preserving configuration; retry resends the previous request with visible request id or retry count change.
result: pass
evidence: `router_demo_action?action=reset` returns idle state with cleared counters/output; `router_demo_action?action=retry` returns complete state with `retry_count: 1` and a new request id.

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None recorded.
