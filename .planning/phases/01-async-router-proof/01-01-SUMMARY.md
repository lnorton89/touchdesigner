# Plan 01 Summary: Router Scaffold

**Status:** Complete
**Completed:** 2026-06-30

## Built

- Added `td_components/llm_model_router/router_http.py` with pure-Python request envelopes, OpenAI-compatible chat payload construction, response extraction, error normalization, exception classification, endpoint composition, and retry rebuilding.
- Added `td_components/llm_model_router/ModelRouterExt.py` with the central `ModelRouter.request(...)` API, reset/retry state behavior, guarded imports for normal Python tests, stable TouchDesigner custom parameter names, and output stubs for Plan 02.
- Added `td_components/llm_model_router/router_callbacks.py` with trigger, reset, retry, and DAT/table-change helper functions that route through the central Router API.
- Added `td_components/llm_model_router/README.md` with the installed target TouchDesigner build, Python version inferred from install DLLs, shareable defaults, distribution notes, and Thread Manager fallback posture.
- Added `tests/test_router_payloads.py` with stdlib unit tests for payload parsing, error normalization, retry identity, Router config surface, and runtime state snapshots.

## Runtime Decision

The newest installed TouchDesigner build on this system is `2022.25370`, installed at `C:\Program Files\Derivative\TouchDesigner.2022.25370`. The installed binaries include `python39.dll`, so Phase 1 targets TouchDesigner Python 3.9 behavior. Thread Manager remains unconfirmed from inside TouchDesigner, so the implementation continues with a conservative fallback requirement: Plan 02 must not hard-require Thread Manager and must support raw Python worker threads with TD-side result application.

## Verification

```powershell
python -m unittest tests.test_router_payloads -v
```

Result: 9 tests passed.

Automated checkpoint assertion for `.planning/phases/01-async-router-proof/01-VALIDATION.md` also passed.

## Notes For Plan 02

- Worker code must keep TouchDesigner object mutation on the TD side only.
- `ModelRouter._write_outputs()` is intentionally a stub until DAT/CHOP-style output mutation is added.
- Callback delivery should use `callback_target` and `callback_method` from the request envelope, defaulting to `onRouterResult(payload)`.
