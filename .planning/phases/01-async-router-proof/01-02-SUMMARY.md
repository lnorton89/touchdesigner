# Plan 02 Summary: Async Worker And Handoff

**Status:** Complete
**Completed:** 2026-06-30

## Built

- Added `call_openai_compatible(envelope)` in `router_http.py` using Python stdlib `urllib.request` for direct non-streaming `/chat/completions` calls.
- Normalized adapter results into plain payload dictionaries with `request_id`, `status`, `response_text`, `error_text`, `error_kind`, `elapsed_ms`, `trigger_source`, `provider`, `base_url`, and `model`.
- Extended `ModelRouter` with background raw-thread submission, TD-side handoff scheduling when `run(..., endFrame=True)` is available, and direct fallback application for normal Python tests.
- Added `_apply_result(payload)` as the single result-application boundary for state, callback invocation, response/error fields, status channel values, and counters.
- Added stale-result protection so older request payloads cannot overwrite newer active state.
- Added `.gitignore` entries for Python bytecode and cache directories.

## Dependency Decision

Phase 1 uses the stdlib HTTP path instead of adopting `httpx==0.28.1`. This keeps the distributable proof dependency-light and leaves third-party dependency hardening for the packaging phase.

## Verification

```powershell
python -m unittest tests.test_router_payloads -v
```

Result: 13 tests passed.

## Notes For Plan 03

- Manual pulse, DAT/table-change, reset, and retry helpers already route to the central Router API.
- The demo wave should expose these helpers in an example component layout and document the visible status/response/error outputs.
- Full TouchDesigner frame-loop proof still requires opening the installed `2022.25370` build and running the manual smoke checks.
