# Phase 1 Walking Skeleton

## Story

As a TouchDesigner builder, I want a Model Router COMP to send a local LLM prompt without freezing the network, so that downstream DAT/CHOP operators can react to the response or error in real time.

## Skeleton Shape

- `td_components/llm_model_router/ModelRouterExt.py`: TD-facing Router extension, custom parameter contract, central `request`, reset, retry, status snapshots, worker submission, and TD-side `_apply_result`.
- `td_components/llm_model_router/router_http.py`: pure-Python OpenAI-compatible request/response and error normalization. No TouchDesigner object access.
- `td_components/llm_model_router/router_callbacks.py`: pulse, reset, retry, and DAT/table-change callback helpers that call the Router API.
- `examples/phase1_async_router/`: reproducible local Ollama demo instructions and callback payload display helpers.
- `tests/test_router_payloads.py`: stdlib `unittest` coverage for envelopes, parsing, errors, state, reset, retry, and stale-result handling.

## Runtime Boundaries

- TD side reads custom parameters and DAT input, updates DAT/CHOP outputs, and invokes callback targets.
- Worker side performs HTTP and pure-Python parsing only.
- Result handoff returns a structured payload with `request_id`, `status`, `response_text`, `error_text`, `elapsed_ms`, and `trigger_source`.

## Distribution Rules

- Use stable names: `llm_model_router`, `ModelRouterExt`, `request`, `reset`, `retry`.
- Safe defaults: `http://localhost:11434/v1`, no API key value, no private filesystem paths.
- Record dependency and setup assumptions for Phase 4 packaging rather than encoding them in saved examples.
