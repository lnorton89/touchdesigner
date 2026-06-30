# Phase 1: Async Router Proof - Context

**Gathered:** 2026-06-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the first working TouchDesigner-native LLM request path: a Model Router COMP can trigger a local Ollama/OpenAI-compatible request without blocking TD's frame loop, expose visible DAT/CHOP status and response outputs, deliver results through a callback handoff, and provide a repeatable demo with both parameter-pulse and DAT/table-change triggers.

This phase does not build the full Agent, tool calling, conversation history, RAG, voice, GLSL repair, or `.tox` packaging workflow. It creates the stable request gateway those later phases will build on.

Because the project is intended for later distribution, Phase 1 should avoid throwaway assumptions that would make packaging painful: no hardcoded user-specific paths, no embedded credentials, no opaque local-only setup, and no names that would conflict with TD projects when the component is shared.

</domain>

<decisions>
## Implementation Decisions

### Request Trigger
- **D-01:** The primary manual trigger should be a visible Router custom parameter pulse. This gives the clearest first proof and the simplest repeatable test surface inside TD.
- **D-02:** The Phase 1 demo must also include a DAT/table-change trigger path. This should prove graph-native use inspired by the video transcript's feedback-loop/table-change pattern, but it can be demo-scoped rather than the only production trigger.
- **D-03:** Both trigger paths should route through the same central Router request function so future operators do not duplicate provider-call logic.

### Callback Handoff
- **D-04:** The Router should expose an explicit callback handoff surface. Prefer a callback DAT/operator target that receives structured result payloads, with room for an operator path + method name style if that fits TD extension patterns better during implementation.
- **D-05:** The callback payload should include enough data for downstream TD logic to react without inspecting internal worker state: request id, status, response text, error text, timing, and trigger source.
- **D-06:** Callback handoff is part of the proof, not a hidden implementation detail. The demo should make it visible that worker results re-enter TD through a safe callback/run boundary.

### Router Surface
- **D-07:** The first Router COMP should feel like a real TD operator with explicit custom parameters, not a script box. Required visible params: provider type, base URL, model, timeout, prompt/input DAT reference, callback target, trigger pulse, reset pulse, retry pulse, and optional request id/status display.
- **D-08:** Required outputs: response DAT, status/error DAT, and status CHOP channels for at least `running`, `done`, `error`, and a monotonically changing `request_id` or `complete_count`.
- **D-09:** Keep the surface intentionally small. API key persistence/secrets handling remains Phase 4, but Phase 1 should leave a visible API key source placeholder or disabled field so the eventual flow has a home.

### Distribution Readiness
- **D-16:** Phase 1 is still a proof, but it should be shaped as a future distributable component: stable operator names, predictable custom parameter names, and no machine-specific paths in saved examples.
- **D-17:** Demo defaults should be safe to share. Local defaults like `http://localhost:11434` are acceptable; private filesystem paths, API keys, or user-specific TD project paths are not.
- **D-18:** Any setup assumptions discovered during Phase 1 should be documented for Phase 4 packaging rather than hidden in ad hoc local state.

### Proof of Nonblocking
- **D-10:** The nonblocking proof should be explicit. Include a deliberately slow request or simulated delay case so a user can see TD continue running while the request is in flight.
- **D-11:** The proof should expose frame-safety through status outputs rather than requiring external profiling. A simple FPS/no-freeze visual or counter in the demo is acceptable if easy.
- **D-12:** Failure cases should be first-class: unreachable endpoint, timeout, and malformed response should surface as recoverable data in DAT/CHOP outputs.

### Reset and Retry
- **D-13:** Reset should clear runtime state: current status, last response, last error, running flag, and counters where appropriate.
- **D-14:** Reset should preserve user configuration and prompt/input DAT references. Users should not have to rebuild the network after a reset.
- **D-15:** Retry should resend the last built request using current Router configuration and make the retry visible via request id/count.

### the agent's Discretion
- The user said "use best judgement" for the Phase 1 discussion. The planner may choose exact TD operator internals, worker implementation strategy, and callback mechanics as long as the decisions above remain true.
- The planner may decide whether the low-level HTTP path is direct `httpx`, TD-native web client behavior, or another compatible approach after research, but the user-facing result must remain the same: nonblocking local LLM request with safe TD handoff.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Scope
- `.planning/PROJECT.md` - Project vision, core value, constraints, and project-level decisions.
- `.planning/REQUIREMENTS.md` - Phase 1 requirement IDs and v1/v2 scope boundaries.
- `.planning/ROADMAP.md` - Phase 1 success criteria and phase boundary.

### Research
- `.planning/research/SUMMARY.md` - Research summary and roadmap implications.
- `.planning/research/STACK.md` - Recommended TD/Python dependency stack.
- `.planning/research/ARCHITECTURE.md` - Recommended component and request lifecycle architecture.
- `.planning/research/PITFALLS.md` - TD threading, dependency, and local-model pitfalls.
- `.planning/research/VIDEO-FEATURES-Go1EfndMfNY.md` - Video-derived Phase 1 additions: central Router API, callback handoff, DAT/table trigger, reset/retry.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet. This is a planning-only repository with no implementation source files.

### Established Patterns
- GSD planning artifacts are committed and should remain the source of truth until implementation begins.
- `AGENTS.md` contains generated project guidance for Codex sessions.

### Integration Points
- New implementation should create the first real project source structure. No existing source modules constrain naming or layout.

</code_context>

<specifics>
## Specific Ideas

- The Router should play the role of the central `chat TD`-style gateway described in the referenced video: future LLM operators call one shared request API.
- Phase 1 should prove both a button-like pulse workflow and a DAT/table-change network workflow.
- Callback handoff should be visible enough that later Agent and tool phases can build on it confidently.
- Reset/retry ergonomics matter because Phase 1 will be used to test slow, failed, and repeated local-model calls.
- The project will be distributed later, so even early prototypes should be cleanly named, reproducible, and free of private/local-only assumptions.

</specifics>

<deferred>
## Deferred Ideas

- Conversation/chat table with role/message/ID/timestamp columns belongs in Phase 2.
- Hold-chat behavior by message or token threshold belongs after Agent history exists.
- Agent parameter control, table editing, and text editing belong in Phase 3 tool calling.
- GLSL repair loop, RAG over TD docs, TOP captioning, multimodal input, and poster/design parameter demos remain later-phase or backlog examples.

</deferred>

---

*Phase: 1-Async Router Proof*
*Context gathered: 2026-06-30*
