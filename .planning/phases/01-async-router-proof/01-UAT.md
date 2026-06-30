---
status: blocked
phase: 01-async-router-proof
source:
  - 01-VERIFICATION.md
started: "2026-06-30T05:15:00.000Z"
updated: "2026-06-30T22:17:00.000Z"
---

# Phase 1 UAT: TouchDesigner Runtime Smoke

## Current Test

[testing complete — blocked pending Phase 4 packaging]

## Tests

### 1. Router Parameter Surface

expected: Custom parameters match the Phase 1 Router contract without saved API key values.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

### 2. Pulse Trigger

expected: Pulsing `Trigger` starts a request and status becomes running immediately.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

### 3. Nonblocking Proof

expected: A visible frame counter or FPS indicator continues updating during a slow request.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

### 4. DAT Table-Change Trigger

expected: Editing `prompt_input` triggers the same central Router request path with `trigger_source=dat_table_change`.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

### 5. Local Endpoint Success

expected: Local Ollama or another OpenAI-compatible endpoint writes response text into the response DAT.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

### 6. Recoverable Error

expected: Unreachable endpoint or short timeout writes error status/text without crashing or silently failing.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

### 7. Callback Payload

expected: Callback target receives `request_id`, `status`, `response_text`, `error_text`, `elapsed_ms`, and `trigger_source`.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

### 8. Reset And Retry

expected: Reset clears runtime state while preserving configuration; retry resends the previous request with visible request id or retry count change.
result: blocked
blocked_by: prior-phase
reason: "Requires .tox packaging (Phase 4) before the COMP can be placed in TD"

## Summary

total: 8
passed: 0
issues: 0
pending: 0
skipped: 0
blocked: 8

## Gaps

None recorded yet.
