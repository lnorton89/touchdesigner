---
status: testing
phase: 01-async-router-proof
source:
  - 01-VERIFICATION.md
started: "2026-06-30T05:15:00.000Z"
updated: "2026-06-30T05:15:00.000Z"
---

# Phase 1 UAT: TouchDesigner Runtime Smoke

## Current Test

number: 1
name: Router parameter surface
expected: |
  The `llm_model_router` component exposes provider type, base URL, model, timeout, prompt DAT, callback target, trigger, reset, retry, status display, and API key source placeholder.
awaiting: user response

## Tests

### 1. Router Parameter Surface

expected: Custom parameters match the Phase 1 Router contract without saved API key values.
result: pending

### 2. Pulse Trigger

expected: Pulsing `Trigger` starts a request and status becomes running immediately.
result: pending

### 3. Nonblocking Proof

expected: A visible frame counter or FPS indicator continues updating during a slow request.
result: pending

### 4. DAT Table-Change Trigger

expected: Editing `prompt_input` triggers the same central Router request path with `trigger_source=dat_table_change`.
result: pending

### 5. Local Endpoint Success

expected: Local Ollama or another OpenAI-compatible endpoint writes response text into the response DAT.
result: pending

### 6. Recoverable Error

expected: Unreachable endpoint or short timeout writes error status/text without crashing or silently failing.
result: pending

### 7. Callback Payload

expected: Callback target receives `request_id`, `status`, `response_text`, `error_text`, `elapsed_ms`, and `trigger_source`.
result: pending

### 8. Reset And Retry

expected: Reset clears runtime state while preserving configuration; retry resends the previous request with visible request id or retry count change.
result: pending

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0
blocked: 0

## Gaps

None recorded yet.
