# Native LLM Operators for TouchDesigner

## What This Is

This project builds a custom TouchDesigner operator family that lets TD networks call local or cloud LLMs natively from inside the node graph. The toolkit should feel like a first-class TD component set: drop in a `.tox`, configure a model endpoint, send messages from DATs/CHOPs, and receive structured DAT/CHOP/TOP-friendly output that downstream operators can react to in real time.

The project occupies the same broad problem space as dotsimulate's Language Operators, but it is designed from scratch with its own architecture, names, dependency strategy, and implementation choices.

## Core Value

TouchDesigner projects can talk to LLMs asynchronously through reusable native-looking operators without freezing the network or requiring an external app/server wrapper.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] Model Router component can configure local or cloud model providers and expose defaults to other operators.
- [ ] Agent component can take prompts/messages from TD operators, maintain conversation history, and write responses back into DAT/CHOP outputs.
- [ ] All LLM calls run without blocking TouchDesigner's main thread.
- [ ] Tool exposition convention lets TD operators register callable functions for agent tool use.
- [ ] At least one TD-native tool can be discovered, called by the Agent, executed in TD, and fed back into the model conversation.
- [ ] Toolkit can be packaged as a reusable `.tox` component that can be dragged into other TD projects.
- [ ] External Python dependencies can be installed into and loaded from an isolated virtual environment instead of TD's embedded Python.
- [ ] Local OpenAI-compatible endpoints, especially Ollama at `http://localhost:11434`, are supported as a first-class daily workflow.

### Out of Scope

- Full feature parity with dotsimulate's Language Operators - this is a fresh implementation, not a port.
- RAG, structured-output routing, STT, and TTS in the first working loop - useful later, but secondary to proving the async agent/tool path.
- macOS as a v0.1 target - support should not be intentionally blocked, but Windows is first.
- Installing packages directly into TouchDesigner's embedded Python - dependencies must live outside TD's base interpreter.

## Context

TouchDesigner ships an embedded Python runtime whose version is pinned per TD build. External packages such as LLM SDKs, async HTTP clients, model routing libraries, and schema validators should be installed into a separate Python 3.11+ virtual environment and added to `sys.path` from a startup hook.

The riskiest technical problem is preserving TD's realtime execution model. Network requests must never happen synchronously in `onCook`; LLM calls need to run async or on worker threads, then deliver results back through safe TD callback/run mechanisms and output operators.

The intended operator family has four to five layers:

- Model Router: provider configuration, API keys, endpoint/model defaults, local and cloud routing.
- Agent: conversational request/response loop, history, tool calling, DAT/CHOP outputs.
- Tool exposition: convention for project operators to declare callable methods and schemas.
- Pipeline utilities: structured output parsing, RAG/retrieval, and optional voice in/out after the core loop is stable.
- Local model path: Ollama/LM Studio/custom OpenAI-compatible endpoint support with graceful handling of weak or invalid tool-call output.

## Constraints

- **Runtime**: TouchDesigner embedded Python is limited and version-pinned - do not depend on pip installing into TD itself.
- **Performance**: Network calls must not block the main TD thread - frame stalls are project-breaking.
- **Packaging**: Deliverable must be a reusable `.tox` component - the operator family should travel between TD projects.
- **Platform**: Target Windows first - most target users are Windows/NVIDIA TD users.
- **Portability**: Avoid hard-coded Windows-only paths where reasonable - macOS support remains a stretch goal.
- **Security**: API keys should be stored locally and not embedded into saved `.toe` project files.
- **Local-first**: Ollama or another local OpenAI-compatible endpoint must work without cloud dependency.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build as a TouchDesigner `.tox` operator family | Enables drag-in reuse, versioning, and TD-native ergonomics | Pending |
| Prove async Model Router before broader features | Main-thread blocking is the highest-risk TD integration issue | Pending |
| Use an external Python virtual environment for dependencies | Keeps TD's embedded Python clean and avoids unsupported package installs | Pending |
| Treat local OpenAI-compatible endpoints as first-class | Day-to-day target is local model use, especially Ollama | Pending |
| Start with one working tool-call round trip | Demonstrates the agent/tool architecture before expanding utilities | Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? Move to Out of Scope with reason
2. Requirements validated? Move to Validated with phase reference
3. New requirements emerged? Add to Active
4. Decisions to log? Add to Key Decisions
5. "What This Is" still accurate? Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check: still the right priority?
3. Business Context check: add only if the project becomes monetized or customer-facing
4. Audit Out of Scope: reasons still valid?
5. Update Context with current implementation state, feedback, and known issues

---
*Last updated: 2026-06-30 after initialization*
