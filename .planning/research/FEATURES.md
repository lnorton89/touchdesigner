# Research: Features

## Table Stakes for v0.1

### Model Routing

- Configure provider type: Ollama, OpenAI-compatible endpoint, Anthropic/cloud adapter later.
- Configure base URL, model name, timeout, streaming mode, and API key reference.
- Keep secrets local and avoid embedding raw API keys in `.toe`/`.tox` saves.
- Allow Agent operators to inherit defaults or override provider/model locally.

### Async Request Loop

- Send messages without blocking TouchDesigner's main thread.
- Surface request lifecycle state: idle, running, complete, error.
- Write final response to DAT output and emit CHOP trigger/counter channels.
- Capture errors as data, not crashes.
- Expose a single central Router request function that future LLM operators can call.
- Allow async results to be routed through a callback operator/function target.
- Support a DAT/table-change trigger path in the first proof, not only a parameter pulse.
- Include reset/retry controls for repeatable slow/error request testing.

### Agent

- System prompt and user-message inputs.
- Conversation history with reset/clear controls.
- Raw response DAT output.
- Optional JSON response parsing when schema is supplied.

### Tool Calling

- Tool declaration convention for TD operators.
- Auto-discovery from a configured COMP path, input, or tag.
- JSON-schema-like parameter declaration.
- Tool call execution routed back to TD-safe callbacks.
- Tool result fed into the next model turn.

### Packaging and Install

- Save as reusable `.tox`.
- Provide dependency status and installer/locator controls.
- Support external `.tox` update workflows.

## Differentiators After the Core Loop

- Structured output router that maps JSON fields to DAT columns or CHOP channels.
- RAG/retrieval operator for local project docs.
- STT/TTS operators for voice-driven TD networks.
- Model capability probe for local models, especially tool-call support quality.
- Optional Engine COMP process isolation experiments for heavy work.
- Hold-chat behavior based on message count or token threshold.
- GLSL repair loop that feeds compile errors back to an Agent.
- TOP captioning through multimodal models.
- Parameter-control demos for poster/design or art-playback workflows.

## Sources

- Derivative `.tox` docs: https://docs.derivative.ca/.tox
- Derivative Component docs: https://docs.derivative.ca/Component
- Derivative File Types docs: https://docs.derivative.ca/File_Types
- Ollama tool-calling docs: https://docs.ollama.com/capabilities/tool-calling
