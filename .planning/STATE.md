---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: uat_pending
stopped_at: Phase 1 demo.toe now opens, UAT can proceed
last_updated: "2026-06-30T07:52:09.000Z"
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 3
  completed_plans: 3
  percent: 18
---

# State: Native LLM Operators for TouchDesigner

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-30)

**Core value:** TouchDesigner projects can talk to LLMs asynchronously through reusable native-looking operators without freezing the network or requiring an external app/server wrapper.
**Current focus:** Phase 1 - Async Router Proof

## Roadmap Status

| Phase | Status | Progress |
|-------|--------|----------|
| 1 - Async Router Proof | UAT pending | 80% |
| 2 - Agent Conversation Loop | Pending | 0% |
| 3 - TD Tool Calling | Pending | 0% |
| 4 - Packaging and Dependency Bootstrap | Pending | 0% |

## Current Phase

Phase 1 implementation plans are complete. demo.toe now opens in TD (was hanging on load due to .toe file format bugs in toe_builder.py). UAT can proceed.

## Notes

- Phase 1 shell-verifiable implementation is complete.
- Automated tests pass with `python -m unittest tests.test_router_payloads -v`.
- Manual TouchDesigner smoke verification is tracked in `.planning/phases/01-async-router-proof/01-UAT.md`.
- `.toe` file format constraints documented in AGENTS.md (CONVENTIONS section) and toe_builder.py header.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 250629-001 | Add llama.cpp provider support with default endpoint and launcher script | 2026-06-29 | c5142e9 | [250629-001-llama-cpp-provider](./quick/250629-001-llama-cpp-provider/) |
| 250630-001 | Fix demo.toe hang — trailing \n, LF-only, empty .text, TOC ordering | 2026-06-30 | — | [toe_builder.py](./scripts/toe_builder.py) |
| 260630-137 | MCP server feasibility research and sketch — confirmed SDK compat, recommended companion process | 2026-06-30 | de8b513, 9d2bb71 | [260630-137-look-into-creating-an-mcp-server-for-tou](./quick/260630-137-look-into-creating-an-mcp-server-for-tou/) |

### Discovered .toe Format Constraints

These were learned through debugging the demo.toe hang and are now captured in AGENTS.md CONVENTIONS:

1. Trailing `\n` required on all `.n` and `.parm` files
2. LF-only line endings (no CRLF)
3. Empty `.text` files (1 empty row) cause TD to hang
4. TOC entry order must follow template conventions
5. `.build` version should match source TD version

## Session

**Last session:** 2026-06-30T07:52:09.000Z
**Stopped at:** Completed MCP server feasibility research and sketch (260630-137). Next: Phase 1 UAT or Phase 2 Agent.
**Resume file:** .planning/quick/260630-137-look-into-creating-an-mcp-server-for-tou/260630-137-SUMMARY.md
