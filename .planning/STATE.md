---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: uat_pending
stopped_at: Phase 1 TouchDesigner UAT pending
last_updated: "2026-06-29T22:30:00.000Z"
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
| 1 - Async Router Proof | UAT pending | 75% |
| 2 - Agent Conversation Loop | Pending | 0% |
| 3 - TD Tool Calling | Pending | 0% |
| 4 - Packaging and Dependency Bootstrap | Pending | 0% |

## Current Phase

Phase 1 implementation plans are complete. TouchDesigner runtime UAT is pending before the phase can be marked complete.

## Notes

- Phase 1 shell-verifiable implementation is complete.
- Automated tests pass with `python -m unittest tests.test_router_payloads -v`.
- Manual TouchDesigner smoke verification is tracked in `.planning/phases/01-async-router-proof/01-UAT.md`.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 250629-001 | Add llama.cpp provider support with default endpoint and launcher script | 2026-06-29 | c5142e9 | [250629-001-llama-cpp-provider](./quick/250629-001-llama-cpp-provider/) |

## Session

**Last session:** 2026-06-29T22:30:00.000Z
**Stopped at:** Phase 1 UAT blocked (needs .tox), Phase 4 packaging structure built. Next: construct .tox in TD per tox/STRUCTURE.md, then re-run UAT.
**Resume file:** .planning/phases/01-async-router-proof/01-UAT.md
