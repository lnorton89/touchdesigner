# Requirements: Native LLM Operators for TouchDesigner

**Defined:** 2026-06-30
**Core Value:** TouchDesigner projects can talk to LLMs asynchronously through reusable native-looking operators without freezing the network or requiring an external app/server wrapper.

## v1 Requirements

### Router

- [ ] **ROUT-01**: User can configure a Model Router COMP with provider type, base URL, model name, timeout, and API key source.
- [ ] **ROUT-02**: User can send a prompt through the Router to a local Ollama or OpenAI-compatible endpoint and receive plain-text output in a DAT.
- [ ] **ROUT-03**: User can see request lifecycle state from the Router, including idle, running, complete, and error.
- [ ] **ROUT-04**: User can keep API keys out of saved `.toe` and `.tox` files by referencing local environment or settings sources.

### Runtime

- [ ] **RUNT-01**: User can trigger an LLM request without blocking TouchDesigner's main thread.
- [ ] **RUNT-02**: User can receive worker results back in TD through a safe callback or run mechanism that updates output operators on the TD side.
- [ ] **RUNT-03**: User can see recoverable errors in DAT/CHOP outputs instead of the network crashing or silently failing.

### Agent

- [ ] **AGNT-01**: User can configure an Agent COMP with a system prompt and a message input from a DAT or parameter.
- [ ] **AGNT-02**: User can maintain, inspect, and clear conversation history for an Agent.
- [ ] **AGNT-03**: User can receive Agent responses as raw text or JSON in an output DAT.
- [ ] **AGNT-04**: User can receive response-ready and error events as CHOP channels or equivalent TD-native triggers.
- [ ] **AGNT-05**: User can override Router defaults on an Agent when a specific model or endpoint is needed.

### Tools

- [ ] **TOOL-01**: User can expose a TD operator as an Agent-callable tool using a documented convention.
- [ ] **TOOL-02**: User can have the Agent discover tools from a configured input, COMP path, tag, or registry component.
- [ ] **TOOL-03**: User can declare tool parameters in a schema that can be sent to supported model providers.
- [ ] **TOOL-04**: User can complete one full tool-call round trip where the model requests a TD-native tool, TD executes it, and the result returns to the conversation.
- [ ] **TOOL-05**: User can see a clear error when a local model returns an invalid or unsupported tool call.

### Packaging

- [ ] **PACK-01**: User can save and load the operator family as a reusable `.tox`.
- [ ] **PACK-02**: User can verify or configure an external Python 3.11-compatible virtual environment for toolkit dependencies.
- [ ] **PACK-03**: User can load toolkit dependencies from the external virtual environment without installing packages into TouchDesigner's embedded Python.
- [ ] **PACK-04**: User can drag the packaged `.tox` into a clean TD project and run the included local-model demo.

### Examples

- [ ] **EXMP-01**: User can run a demo that sends a DAT message to a local Ollama model and receives a response DAT.
- [ ] **EXMP-02**: User can run a demo tool that reads or sets a CHOP value through an Agent tool call.

## v2 Requirements

### Structured Output

- **STRU-01**: User can provide a JSON schema and route validated fields to DAT columns.
- **STRU-02**: User can route numeric JSON fields to CHOP channels.

### Retrieval

- **RAG-01**: User can index a local document set for retrieval-augmented prompts.
- **RAG-02**: User can inspect retrieved snippets used in an Agent response.

### Voice

- **VOIC-01**: User can send speech-to-text transcripts into an Agent.
- **VOIC-02**: User can convert Agent responses to speech output.

### Providers

- **PROV-01**: User can configure Anthropic-specific cloud models through the Router.
- **PROV-02**: User can configure fallback routing across multiple providers.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full clone or port of dotsimulate LOPs | Project should define its own architecture and names. |
| RAG in v0.1 | Retrieval is useful only after the basic async Agent/tool loop is stable. |
| STT/TTS in v0.1 | Voice adds provider and UX complexity outside the core proof. |
| Direct package installation into TD Python | Unsupported and risks breaking TD's embedded environment. |
| macOS-first packaging | Windows is the primary target; portability should be preserved where practical. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

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

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-06-30*
*Last updated: 2026-06-30 after roadmap creation*
