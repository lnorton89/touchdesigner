---
status: passed
phase: 01-async-router-proof
updated: "2026-06-30T23:25:00.000Z"
automated_status: passed
human_status: passed
---

# Phase 1 Verification: Async Router Proof

## Automated Verification

Command:

```powershell
python -m unittest tests.test_router_payloads -v
```

Result: passed, 15 tests.

Covered:

- OpenAI-compatible response parsing.
- HTTP status, malformed JSON, malformed response, timeout, and connection error normalization.
- Central `ModelRouter.request(...)` entry point.
- Reset and retry runtime semantics.
- Status snapshot and CHOP-ready channel fields.
- Callback payload application.
- Stale-result protection.
- Pulse, reset, retry, and DAT table-change callback routing.

## Human Verification Required

The following behavior must be verified inside TouchDesigner `2022.25370` before Phase 1 can be marked complete:

1. Router custom parameter surface exists with provider type, base URL, model, timeout, prompt DAT, callback target, trigger, reset, retry, status display, and API key source placeholder.
2. Parameter pulse trigger starts a request and status becomes running immediately.
3. A visible frame counter or FPS indicator continues updating while a slow request is running.
4. DAT/table-change trigger starts a request through the same central Router path with `trigger_source=dat_table_change`.
5. Local Ollama or another OpenAI-compatible endpoint returns response text to the response DAT.
6. Unreachable endpoint or short timeout writes recoverable error text/status.
7. Callback target receives `request_id`, `status`, `response_text`, `error_text`, `elapsed_ms`, and `trigger_source`.
8. Reset clears runtime state but preserves configuration; retry resends the prior request with a visible request id or retry count change.

## Gap Closure

Plan 01-04 added a generated Router demo smoke surface. The MCP bridge can read `test_results`, `response_text`, and `status_json`; the Router startup smoke reports `state: complete`, `done: true`, and `complete_count: 1`.

Follow-up Textport evidence showed client-abort socket traces from the bridge response writer. `MCPBridgeExt.py` now treats broken-pipe, connection-aborted, and connection-reset writes as normal disconnects. Regression coverage was added, and `python -m pytest -q` now passes with 29 tests.

## Decision

Phase 1 is complete. Automated tests pass and the TouchDesigner runtime UAT checklist passed against the generated `demo.toe`.
