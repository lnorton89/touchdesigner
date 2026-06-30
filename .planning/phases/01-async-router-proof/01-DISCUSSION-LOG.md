# Phase 1: Async Router Proof - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-06-30
**Phase:** 1-Async Router Proof
**Areas discussed:** Request trigger, Callback handoff, Router surface, Proof of nonblocking, Reset/error loop

---

## Request Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Parameter pulse primary | Use a visible Router pulse as the main manual test trigger. | yes |
| DAT/table-change primary | Treat DAT/table changes as the primary request trigger. | |
| Both equally primary | Require both to be equally complete in Phase 1. | |

**User's choice:** Use best judgement.
**Notes:** Selected parameter pulse as the clearest primary manual proof, with DAT/table-change included as a required graph-native demo path.

---

## Callback Handoff

| Option | Description | Selected |
|--------|-------------|----------|
| Callback DAT/operator target | Expose callback target visibly in TD and write structured result payloads. | yes |
| Operator path + method name | Route into a configured operator extension method. | partial |
| Internal callback only | Keep callback mechanics hidden behind Router internals. | |

**User's choice:** Use best judgement.
**Notes:** Selected visible callback handoff. Planner may choose exact TD mechanics, but the callback/result boundary must be demonstrable.

---

## Router Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal script-box surface | Few parameters, mostly internal wiring. | |
| TD-native Router COMP | Custom params plus DAT/CHOP outputs for status, response, and errors. | yes |
| Full future-proof provider panel | Broad provider/secrets surface in Phase 1. | |

**User's choice:** Use best judgement.
**Notes:** Selected a small but real TD-native surface. Secrets persistence stays Phase 4.

---

## Proof of Nonblocking

| Option | Description | Selected |
|--------|-------------|----------|
| Subtle status channels | Trust running/done/error outputs as enough proof. | |
| Deliberate slow-request demo | Include slow/simulated delay case to show TD does not freeze. | yes |
| External profiling only | Rely on developer profiling outside TD. | |

**User's choice:** Use best judgement.
**Notes:** Selected an explicit slow-request or simulated delay proof with visible status output.

---

## Reset/Error Loop

| Option | Description | Selected |
|--------|-------------|----------|
| Clear everything | Reset config, input, outputs, and runtime state. | |
| Clear runtime only | Clear status/output/error while preserving config and input references. | yes |
| Preserve all history | Reset only the running flag and preserve prior outputs. | |

**User's choice:** Use best judgement.
**Notes:** Selected reset/retry ergonomics that support repeated local-model testing without rebuilding the network.

---

## the agent's Discretion

- User delegated Phase 1 discussion decisions with "use best judgement."
- Exact implementation strategy for worker execution and TD callback mechanics is left to research/planning, constrained by the captured behavior decisions.

## Deferred Ideas

- Conversation/chat table, hold-chat thresholds, Agent parameter control, table/text editing, GLSL repair, RAG, TOP captioning, multimodal input, and poster/design demos are deferred to later phases/backlog.
