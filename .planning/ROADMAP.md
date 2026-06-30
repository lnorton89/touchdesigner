# Roadmap: Native LLM Operators for TouchDesigner

**Created:** 2026-06-30
**Mode:** MVP
**Granularity:** Coarse

## Overview

This roadmap prioritizes the riskiest technical proof first: a nonblocking local LLM call from inside TouchDesigner. Later phases add Agent behavior, tool calling, and reusable `.tox` packaging only after the realtime integration path is proven.

| Phase | Name | Goal | Requirements |
|-------|------|------|--------------|
| 1 | Async Router Proof | Prove nonblocking local model calls from TD into DAT/CHOP outputs | ROUT-01, ROUT-02, ROUT-03, RUNT-01, RUNT-02, RUNT-03, EXMP-01 |
| 2 | Agent Conversation Loop | Add prompt/history behavior and Agent-native outputs | AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05 |
| 3 | TD Tool Calling | Prove model-requested TD-native tool execution | TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05, EXMP-02 |
| 4 | Packaging and Dependency Bootstrap | Package the working family as a reusable `.tox` with external dependency loading and secret hygiene | ROUT-04, PACK-01, PACK-02, PACK-03, PACK-04 |

## Phases

### Phase 1: Async Router Proof

**Goal:** A TD project can send a prompt to local Ollama or a generic OpenAI-compatible endpoint without blocking the frame loop, then receive output back in DAT/CHOP form.
**Mode:** mvp
**Requirements:** ROUT-01, ROUT-02, ROUT-03, RUNT-01, RUNT-02, RUNT-03, EXMP-01

**Success Criteria:**
1. A Model Router COMP exposes provider, base URL, model, timeout, and API key source parameters.
2. A local Ollama prompt can be triggered from TD and returns plain text into a DAT.
3. Router status visibly transitions through idle, running, complete, and error states.
4. A deliberately slow or failed request does not freeze TouchDesigner's main thread.
5. The included demo sends a DAT message and receives a response DAT.

### Phase 2: Agent Conversation Loop

**Goal:** A dedicated Agent COMP can inherit or override Router settings, maintain conversation history, and emit TD-native response events.
**Mode:** mvp
**Requirements:** AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05

**Success Criteria:**
1. Agent accepts system prompt and message input from a DAT or custom parameter.
2. Agent can inspect, append to, and clear conversation history.
3. Agent writes raw text or JSON response data into an output DAT.
4. Response-ready and error events are visible through CHOP channels or equivalent TD triggers.
5. Agent can override the Router's default endpoint or model for a specific request.

### Phase 3: TD Tool Calling

**Goal:** The Agent can discover a TD-native tool, pass its schema to a supported model, execute the tool safely, and feed the result back into the conversation.
**Mode:** mvp
**Requirements:** TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05, EXMP-02

**Success Criteria:**
1. Tool authors can expose a callable TD operator using a documented method, tag, or custom parameter convention.
2. Agent discovers available tools from the configured registry/input/path.
3. Tool parameter schemas are serialized into provider-compatible tool definitions.
4. A demo Agent reads or sets a CHOP value through a model-requested tool call.
5. Invalid or unsupported tool-call output from a local model appears as a clear recoverable error.

### Phase 4: Packaging and Dependency Bootstrap

**Goal:** The working operator family can be reused across TD projects as a `.tox` with external dependency loading, clean setup checks, and local secret handling.
**Mode:** mvp
**Requirements:** ROUT-04, PACK-01, PACK-02, PACK-03, PACK-04

**Success Criteria:**
1. The operator family can be saved as and loaded from a reusable `.tox`.
2. A clean TD project can drag in the `.tox` and run the local-model demo.
3. Toolkit dependencies load from a configured external Python 3.11-compatible venv.
4. Missing or incompatible dependencies are reported inside TD with setup guidance.
5. API key values are not embedded directly into saved `.toe` or `.tox` files.

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| ROUT-01 | Phase 1 | Pending |
| ROUT-02 | Phase 1 | Pending |
| ROUT-03 | Phase 1 | Pending |
| ROUT-04 | Phase 4 | Pending |
| RUNT-01 | Phase 1 | Pending |
| RUNT-02 | Phase 1 | Pending |
| RUNT-03 | Phase 1 | Pending |
| AGNT-01 | Phase 2 | Pending |
| AGNT-02 | Phase 2 | Pending |
| AGNT-03 | Phase 2 | Pending |
| AGNT-04 | Phase 2 | Pending |
| AGNT-05 | Phase 2 | Pending |
| TOOL-01 | Phase 3 | Pending |
| TOOL-02 | Phase 3 | Pending |
| TOOL-03 | Phase 3 | Pending |
| TOOL-04 | Phase 3 | Pending |
| TOOL-05 | Phase 3 | Pending |
| PACK-01 | Phase 4 | Pending |
| PACK-02 | Phase 4 | Pending |
| PACK-03 | Phase 4 | Pending |
| PACK-04 | Phase 4 | Pending |
| EXMP-01 | Phase 1 | Pending |
| EXMP-02 | Phase 3 | Pending |

**Coverage:** 23 of 23 v1 requirements mapped.
