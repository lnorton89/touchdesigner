---
status: resolved
trigger: "opencode bridge script closes generated demo.toe / cannot talk to reopened TouchDesigner project"
created: 2026-06-30
updated: 2026-06-30
---

# Debug Session: demo-toe-bridge-closes

## Symptoms

- Expected behavior: generated `demo.toe` opens in TouchDesigner and a bridge can communicate with the project without closing it.
- Actual behavior: previous script at `C:\Users\Lawrence\AppData\Local\Temp\opencode\test_bridge2.py` kept making the project close.
- Error messages: not yet known.
- Timeline: current state after opencode attempts; user reopened the project for this session.
- Reproduction: run bridge/test script against the open generated demo project.

## Current Focus

- hypothesis: unknown
- test: inspect bridge/demo generation, then test the least invasive read-only bridge calls
- expecting: either a reachable TD bridge endpoint or evidence that the project-side bridge is not running / crashes on a specific route
- next_action: resolved
- reasoning_checkpoint:
- tdd_checkpoint:

## Evidence

- timestamp: 2026-06-30
  observation: Direct `op()` calls from the bridge HTTP thread could close TouchDesigner when the external probe listed network children.
- timestamp: 2026-06-30
  observation: The generated Execute DAT initially had a clipped/incomplete callback body, then later a stale `onFrameStart` callback toggle; both prevented a clean bridge startup.
- timestamp: 2026-06-30
  observation: Final regenerated `demo.toe` starts the bridge, returns `status: ok` for `list_network_children` and `get_dat_text`, and TouchDesigner remains running/responding afterward.
- timestamp: 2026-06-30
  observation: User-provided Textport paste showed repeated `ConnectionAbortedError: [WinError 10053]` traces from `_respond_json` when a client closed before the bridge finished writing a response.
- timestamp: 2026-06-30
  observation: Fresh live run opened `demo/demo.toe`, waited 20s, confirmed process stayed alive, sent an intentionally aborted raw socket request, and confirmed the bridge answered the next request.

## Eliminated

## Resolution

- root_cause: TD operator access was happening from the bridge HTTP thread instead of TouchDesigner's main thread, the generated demo Execute DAT did not reliably pump queued work from TD, and aborted client sockets were being treated as route failures after the response path had already started.
- fix: Queue bridge requests from the HTTP thread, drain them from a TD-side self-scheduling pump, shorten the generated Execute DAT, swallow normal broken-pipe/client-abort response writes, and regenerate `demo/demo.toe`.
- verification: `python -m pytest -q` passed with 29 tests; launched regenerated `demo.toe`, waited 20s, received ok bridge responses, sent an aborted raw socket request, then confirmed TouchDesigner process stayed running/responding.
- files_changed: `td_components/mcp_bridge/MCPBridgeExt.py`, `scripts/toe_builder.py`, `tests/test_mcp_bridge.py`, `demo/demo.toe`
