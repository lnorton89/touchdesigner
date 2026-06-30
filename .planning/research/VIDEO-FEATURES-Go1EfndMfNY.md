# Video Feature Extraction: Go1EfndMfNY

**Source:** https://www.youtube.com/watch?v=Go1EfndMfNY
**Captured:** 2026-06-30
**Transcript:** English auto-generated captions, parsed for product/phase implications.

## Phase 1-Relevant Feature Signals

- **Central chat/API operator:** The speaker describes a behind-the-scenes `chat TD` operator with an exposed custom API call used by every LLM operator. For this project, Phase 1 should make the Model Router the single callable request gateway instead of letting each future operator implement provider calls.
- **Callback function and callback operator:** The same segment describes a custom API call with a callback and callback operator. This reinforces Phase 1's need to prove async result delivery through an explicit callback target, not just a background thread returning data invisibly.
- **Parameter-dialog-style operator surface:** The talk mentions top operator-menu entries opening small parameter dialogs. Phase 1 should keep the Router's custom parameter surface explicit and TD-native: endpoint/model/timeout/input/output/callback controls visible on the COMP.
- **DAT/table-change trigger path:** The feedback-loop description uses a table/null change as the moment that pulls data back into the loop. Phase 1 should include a simple DAT/table-trigger demo in addition to a parameter pulse so the first proof feels like a node-graph workflow, not only a button test.
- **Reset/retry controls:** The feedback operator includes reset pulse/toggle behavior. Phase 1 should include reset/retry controls for request state and output clearing so failure/iteration demos are easy to repeat.

## Later-Phase / Backlog Signals

- **Conversation/chat table:** Role/message/ID/timestamp chat tables belong with Phase 2 Agent history.
- **Hold chat by message or token threshold:** Useful for Agent feedback loops after the router is proven.
- **Agent controls custom parameters:** Belongs with Phase 3 tool calling.
- **Agent builds/edits tables and text:** Tooling/useful operator family feature after Agent tools exist.
- **GLSL creator with iterative error repair:** Strong future demo, but it depends on Agent/tool feedback and should not be Phase 1.
- **RAG over local TouchDesigner documentation:** Already captured as v2 retrieval.
- **TOP captioning/multimodal input:** Future provider/operator extension, not part of the first router proof.
- **Poster/design parameter control demos:** Good future examples for parameter-control tools.

## Phase 1 Additions

Add the following to Phase 1 scope:

- Router exposes one central callable request function that future LLM operators can use.
- Router supports a callback operator/function parameter for async result delivery.
- Demo includes both a parameter pulse and a DAT/table-change trigger path.
- Demo includes reset/retry controls to clear state and repeat slow/error cases.
