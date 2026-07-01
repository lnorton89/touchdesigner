---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: phase_complete
stopped_at: Phase 3 TD Tool Calling passed; ready for Phase 4 Packaging and Dependency Bootstrap
last_updated: "2026-07-01T15:48:55.035Z"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
  percent: 75
---

# State: Native LLM Operators for TouchDesigner

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-30)

**Core value:** TouchDesigner projects can talk to LLMs asynchronously through reusable native-looking operators without freezing the network or requiring an external app/server wrapper.
**Current focus:** Phase 2 - Agent Conversation Loop

## Roadmap Status

| Phase | Status | Progress |
|-------|--------|----------|
| 1 - Async Router Proof | Complete | 100% |
| 2 - Agent Conversation Loop | Complete | 100% |
| 3 - TD Tool Calling | Complete | 100% |
| 4 - Packaging and Dependency Bootstrap | Pending | 0% |

## Current Phase

Phase 3 is complete. `demo.toe` opens, the MCP bridge smoke passes, local llama.cpp emits a model-requested `set_demo_value` tool call, TouchDesigner executes it, Agent history records the `role: tool` result, invalid tool-call errors surface cleanly, and the CHOP example sets `tool_chop.par.value0`. Next focus is Phase 4 Packaging and Dependency Bootstrap.

## Notes

- Phase 1 shell-verifiable implementation is complete.
- Phase 2 Agent implementation is complete; deterministic and real local endpoint TD smoke both pass.
- Phase 3 TD Tool Calling is complete; deterministic, model-requested, invalid tool-call, and CHOP tool TD smoke pass.
- Automated tests pass with `python -m pytest -q` (45 tests).
- Manual TouchDesigner smoke verification is tracked in `.planning/phases/01-async-router-proof/01-UAT.md`.
- `.toe` file format constraints documented in AGENTS.md (CONVENTIONS section) and toe_builder.py header.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 250629-001 | Add llama.cpp provider support with default endpoint and launcher script | 2026-06-29 | c5142e9 | [250629-001-llama-cpp-provider](./quick/250629-001-llama-cpp-provider/) |
| 250630-001 | Fix demo.toe hang — trailing \n, LF-only, empty .text, TOC ordering | 2026-06-30 | — | [toe_builder.py](./scripts/toe_builder.py) |
| 260630-137 | MCP server feasibility research and sketch — confirmed SDK compat, recommended companion process | 2026-06-30 | de8b513, 9d2bb71 | [260630-137-look-into-creating-an-mcp-server-for-tou](./quick/260630-137-look-into-creating-an-mcp-server-for-tou/) |
| 260630-2fy | Implement production MCP server: companion FastMCP server, TD-side bridge extension, updated deps | 2026-06-30 | ab640ac, fe3b4c4, 53713e4 | [260630-2fy-implement-production-mcp-server-for-touc](./quick/260630-2fy-implement-production-mcp-server-for-touc/) |
| 260701-c8r | Create end-to-end documentation for the demo process and nodes; add best-effort main comp controls | 2026-07-01 | uncommitted | [260701-c8r-create-end-to-end-documentation-for-demo](./quick/260701-c8r-create-end-to-end-documentation-for-demo/) |

### Discovered .toe Format Constraints

These were learned through debugging the demo.toe hang and are now captured in AGENTS.md CONVENTIONS:

1. Trailing `\n` required on all `.n` and `.parm` files
2. LF-only line endings (no CRLF)
3. Empty `.text` files (1 empty row) cause TD to hang
4. TOC entry order must follow template conventions
5. `.build` version should match source TD version

## Session

**Last session:** 2026-06-30T07:52:09.000Z
**Stopped at:** Completed production MCP server implementation (260630-2fy): companion FastMCP server + TD-side bridge extension. Next: Phase 1 UAT or Phase 2 Agent.
**Resume file:** .planning/quick/260630-2fy-implement-production-mcp-server-for-touc/260630-2fy-SUMMARY.md
