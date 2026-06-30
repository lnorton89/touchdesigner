# Phase 1: Async Router Proof - Validation

**Created:** 2026-06-30
**Status:** Ready for execution
**Scope:** Validation architecture for Phase 1 plans and requirements.

## Validation Strategy

Phase 1 mixes pure-Python behavior with TouchDesigner runtime behavior. Validation is split accordingly:

- **Automated Python checks** verify request envelopes, OpenAI-compatible response parsing, error normalization, state snapshots, reset/retry behavior, and stale-result handling without requiring TouchDesigner.
- **TouchDesigner runtime checks** verify custom parameter surface, extension reload/source-export behavior, Thread Manager or fallback availability, nonblocking frame behavior, DAT/CHOP output mutation, callback delivery, and demo trigger ergonomics.
- **Distribution checks** verify no embedded credentials, no private filesystem paths, safe localhost defaults, and stable namespacing for future `.tox` packaging.

## Requirement Coverage

| Requirement | Validation Type | Evidence Expected |
|-------------|-----------------|-------------------|
| ROUT-01 | TD runtime + doc inspection | Router COMP/README lists provider type, base URL, model, timeout, prompt DAT reference, callback target, trigger, reset, retry, status display, and API key source placeholder. |
| ROUT-02 | Automated + TD manual | Python parser test extracts `choices[0].message.content`; TD demo can POST to local Ollama/OpenAI-compatible endpoint and write response DAT. |
| ROUT-03 | Automated + TD manual | Unit tests verify idle/running/complete/error state snapshots; TD status/error DAT and status CHOP-style channels mirror these states. |
| ROUT-05 | Automated + code inspection | Pulse, DAT trigger, and retry helpers all call `ModelRouter.request` or its reset/retry siblings instead of duplicating provider logic. |
| ROUT-06 | Automated + TD manual | Callback payload includes request id, status, response text, error text, timing, and trigger source; callback target receives it only through TD-side handoff. |
| RUNT-01 | TD manual | Slow request or simulated delay proves TD continues updating while request is running. |
| RUNT-02 | Code inspection + TD manual | Worker code only handles HTTP/plain Python data; `_apply_result` or equivalent is the only DAT/CHOP/callback mutation point. |
| RUNT-03 | Automated + TD manual | Timeout, unreachable endpoint, HTTP status, malformed response, and malformed JSON become recoverable error payloads. |
| EXMP-01 | TD manual | Demo sends a DAT prompt to local Ollama/OpenAI-compatible endpoint and receives response DAT. |
| EXMP-03 | TD manual | Demo can be triggered by Router parameter pulse and by DAT/table-change path. |
| EXMP-04 | Automated + TD manual | Reset clears runtime state while preserving config/input references; retry resends last request with visible request id/count change. |

## Automated Commands

Run after each implementation plan:

```powershell
python -m unittest tests.test_router_payloads -v
```

If a test framework is later introduced, keep this stdlib command working or update this file and all affected plans together.

## Manual TouchDesigner Checks

Before TD-facing implementation:

1. Record target TouchDesigner build number.
2. Record embedded Python version.
3. Confirm Thread Manager / Thread Manager Client availability.
4. Confirm extension reload/source-export behavior for `ModelRouterExt.py`.
5. If Thread Manager is unavailable, record approved fallback before continuing.

Final Phase 1 smoke:

1. Trigger request by Router pulse.
2. Trigger request by DAT/table change.
3. Confirm response DAT updates on success.
4. Confirm status/error DAT and status CHOP-style channels update through idle/running/complete/error.
5. Run slow request or simulated delay and confirm TD continues updating.
6. Test unreachable endpoint or timeout and confirm recoverable error payload.
7. Test reset and retry; confirm config/input references survive reset.
8. Confirm callback target receives structured payload during TD-side handoff.

## Distribution Checks

- No API key value is saved in source, examples, README, `.toe`, or future `.tox` files.
- Demo defaults may use `http://localhost:11434/v1`, but must not include private paths.
- Callback target names, custom parameter names, and source files use stable `llm_model_router` / `ModelRouter` naming.
- Setup assumptions found during execution are documented for Phase 4 packaging rather than hidden in local machine state.

## Nyquist Notes

This validation plan intentionally samples each phase requirement at least once across automated tests, TD manual smoke checks, and distribution hygiene checks. Automated tests cover deterministic pure-Python behavior; TD runtime checks cover the realtime and operator-surface behavior that cannot be proven from this shell alone.
