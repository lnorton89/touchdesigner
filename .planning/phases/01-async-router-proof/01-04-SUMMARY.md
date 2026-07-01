# Plan 04 Summary: Generated Router Demo Surface

**Status:** Complete; Phase 1 UAT ready to resume
**Completed:** 2026-06-30

## Built

- Added owner-relative DAT output writing in `ModelRouterExt.py` so Router state appears in `response_text`, `error_text`, and `status_json`.
- Added bridge response handling for clients that disconnect early, preventing repeated `ConnectionAbortedError` Textport traces.
- Added tests proving Router output mutation and prompt DAT lookup work with a fake TD owner/parent operator structure.
- Updated the generated `demo.toe` startup smoke so TouchDesigner starts the MCP bridge, instantiates `ModelRouter`, applies a deterministic startup completion, and writes visible Router evidence.
- Kept the Execute DAT source below the observed clipping threshold.
- Regenerated `demo/demo.toe`.

## Verification

```powershell
python -m pytest -q
```

Result: 29 tests passed.

Live TouchDesigner smoke:

1. Closed stale TouchDesigner test processes.
2. Launched `demo/demo.toe` in TouchDesigner `2022.25370`.
3. Waited 20 seconds.
4. Confirmed port `9876` was owned by the new TouchDesigner process.
5. Read these DATs through the MCP bridge:
   - `/project1/base_llm_demo/test_results` -> `Bridge started`, `Router smoke complete`
   - `/project1/base_llm_demo/response_text` -> `Router demo ready`
   - `/project1/base_llm_demo/status_json` -> `state: complete`, `done: true`, `request_id: 1`, `complete_count: 1`
6. Listed `/project1/base_llm_demo` children through the bridge.
7. Confirmed TouchDesigner stayed running/responding after the probe.

Follow-up UAT action probe:

- `router_demo_action?action=pulse` wrote `trigger_source: pulse`.
- `router_demo_action?action=dat_change` wrote `trigger_source: dat_table_change`.
- `router_demo_action?action=slow` left Router state `running: true` while the bridge stayed responsive.
- `router_demo_action?action=error` wrote a recoverable error state.
- `router_demo_action?action=reset` cleared runtime state.
- `router_demo_action?action=retry` wrote `retry_count: 1`.
- `router_demo_action?action=local_endpoint` called local llama.cpp on `127.0.0.1:8080` off the TD main thread; `collect` applied a complete payload with non-empty response text.
- An intentionally aborted raw socket request did not close TouchDesigner; the bridge answered the next normal request.

## Remaining Manual UAT

The full Phase 1 checklist passed and is recorded in `01-UAT.md`.

## Next

Proceed to Phase 2: Agent Conversation Loop.
