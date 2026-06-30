# Research: Architecture

## Recommended Shape

Build a single top-level Base COMP `.tox` containing a small operator family:

1. `llm_model_router` owns provider config, dependency status, API key lookup, and request dispatch.
2. `llm_agent` owns prompts, messages, history, tool call orchestration, and outputs.
3. `llm_tool_registry` discovers TD operators that expose a tool descriptor.
4. `llm_tool_example_chop` proves a simple TD-native read/set operation.
5. Utility COMPs come later: structured parser, retrieval, voice.

## Threading Boundary

The Python worker layer should treat TD objects as unsafe to touch directly from worker threads. Worker code should do HTTP and pure-Python parsing only. Result delivery back into TD should be marshalled to the main TD context through a callback/run mechanism and then update DAT/CHOP output operators.

## Request Lifecycle

1. Agent receives a trigger and reads input DAT/CHOP values on TD's main thread.
2. Agent builds a provider-neutral request envelope.
3. Router submits the envelope to an async worker or thread worker.
4. Worker sends HTTP request and parses provider response.
5. Main-thread callback writes response/error state to output DAT/CHOP.
6. If tool calls are present, Agent validates them, invokes matching TD tools safely, appends tool result messages, and submits the follow-up request.

## Provider Strategy

Phase 1 should support:

- Ollama native `/api/chat` or OpenAI-compatible `/v1/chat/completions` at `http://localhost:11434`.
- Generic OpenAI-compatible endpoint with base URL and API key.

Cloud-specific adapters can come after the local path works. LiteLLM can reduce provider branching, but direct endpoint calls are clearer for the first TD integration proof.

## Packaging Strategy

Derivative documents `.tox` as the TouchDesigner component file for reusable components. Top-level custom parameters should expose configuration, status, dependency installer controls, and examples. A `.tox` can be saved from a Component and reused across projects.

## Sources

- Derivative Python docs: https://docs.derivative.ca/Python
- Derivative Component docs: https://docs.derivative.ca/Component
- Derivative External `.tox` behavior: https://docs.derivative.ca/Handle_COMP
- Ollama OpenAI compatibility docs: https://docs.ollama.com/api/openai-compatibility
