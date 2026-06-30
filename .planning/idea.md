# Project Brief: Native LLM Operator Family for TouchDesigner

## Goal

Build a custom operator family for TouchDesigner that lets a project call out to LLMs (cloud or local) natively from within the network — no external server, no separate app window. The end result should feel like a first-class TD operator family: drop a component in, wire it to other operators, get structured output back as CHOPs/DATs/TOPs that the rest of the network can react to in real time.

Treat this as an alternative implementation of the same problem space as dotsimulate's "LOPs" (Language Operators) — agent-style LLM access wired directly into TD's node graph — but designed from scratch, not as a port. Use your own architecture, naming, and implementation choices.

## Hard constraints from the TD environment

- TouchDesigner ships its own embedded Python (version pinned per TD build) with a limited stdlib and no pip access from inside the app by default. Any external packages (an LLM SDK, an async HTTP client, etc.) need to live in a separate virtual environment that gets added to `sys.path`, not installed into TD's interpreter directly.
- Network calls must never block TD's main thread or the frame will stall. All LLM calls need to run async or on a worker thread, with results delivered back into the network via a callback, a Run() script, or a CHOP/DAT execute mechanism — not a synchronous blocking call in `onCook`.
- The deliverable should be packaged as a `.tox` component so it can be dragged into any project, versioned, and updated independently of the project file.
- Target Windows first (most TD users are on Windows + NVIDIA), but don't hard-code Windows-only paths if avoidable — macOS support is a stretch goal.

## Core architecture

Design four or five logical layers, implemented as TD Component (COMP) operators with custom parameters and a Python extension class behind each:

1. **Model Router** — a single settings component that owns provider configuration: which backend (OpenAI-compatible cloud API, Anthropic, local Ollama/LM Studio server, or a custom `/v1` endpoint), API keys (stored locally, never embedded in the saved `.toe`), and a default model. Every other operator should be able to either inherit this default or override it locally. Consider routing all providers through a single abstraction layer (e.g. `litellm`) so adding a new backend is a config change, not new code per-provider.

2. **Agent operator** — the core conversational/tool-calling unit. Takes a system prompt, a message (from a DAT, a CHOP value, voice transcript, etc.), maintains conversation history, and can call back out to other TD operators as "tools" mid-conversation (function calling). Output should land in a DAT (raw text/JSON) and optionally a CHOP (for triggering downstream logic on response-ready events).

3. **Tool exposition pattern** — define a simple convention (e.g. any operator with a `GetTool()` method, or a tagged custom parameter) that lets *any* operator in the project register itself as a callable function for the Agent. The Agent should auto-discover tools wired into a designated input/operator family slot, build the function-calling schema from each tool's declared parameters, and route the LLM's tool calls back to the right operator's Python method, then feed the result back into the conversation.

4. **Pipeline/utility operators** (build after the core loop works) — structured output parsing (force JSON schema, route fields to separate CHOP channels), a RAG/retrieval operator (embed + search a local doc set), and optionally STT/TTS if you want voice in/out. These can be thin wrappers since they're mostly "call API, reshape result for TD."

5. **Local-model path** — explicitly support pointing the Model Router at `http://localhost:11434` (Ollama) or another local OpenAI-compatible server with zero cloud dependency, since that's the actual day-to-day target. Test tool-calling support against your local models early — not every local model reliably emits structured function calls, so the Agent operator's parser needs to fail gracefully and surface "model didn't return a valid tool call" rather than crashing the network.

## Dependency management

Bundle or build a small in-app installer flow: pick/verify an external Python 3.11+ interpreter, create an isolated venv for the toolkit's dependencies (httpx or aiohttp, your model-routing lib, maybe pydantic for schema validation), and add it to `sys.path` from a `onStart` extension hook so it persists across project reloads without polluting TD's base interpreter.

## Suggested build order

1. Model Router component with a hardcoded local Ollama call, returning plain text to a DAT. Prove the async-call-without-blocking-TD pattern works first — this is the riskiest technical piece.
2. Agent operator with conversation history and a working request/response loop against the Router.
3. Tool exposition convention + one working tool (e.g. an operator that lets the Agent read/set a CHOP value in the project) to prove function calling round-trips correctly.
4. Settings/packaging: turn the working network into a reusable `.tox`, add the venv installer flow, and add a second tool to confirm the discovery pattern generalizes.
5. Only after that loop is solid: layer in RAG, structured output, or voice if still wanted.

## What "done" looks like for v0.1

A `.tox` you can drag into any TD project that gives you: a configured local-or-cloud model endpoint, an Agent component you can message from a DAT and get a response back in another DAT, and at least one working example of the Agent calling a TD-native tool mid-conversation.