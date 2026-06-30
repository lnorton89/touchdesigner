# Phase 1 Async Router Demo

This demo proves that `llm_model_router` can send an OpenAI-compatible local request without freezing TouchDesigner, then return a structured result through visible status, response, error, and callback outputs.

## Target Runtime

- TouchDesigner build: `2022.25370` on this system
- Embedded Python: Python `3.9` inferred from the installed TouchDesigner binaries
- HTTP adapter: stdlib `urllib.request`
- Default endpoint: `http://localhost:11434/v1`
- Default model: `llama3.2`

## Network Layout

Create or assemble these operators with relative names:

- `llm_model_router`: Base COMP with `ModelRouterExt.py` as the `ModelRouter` extension
- `prompt_input`: Text DAT containing the prompt
- `response_text`: Text DAT for response text
- `status_text`: Text DAT for the status snapshot
- `error_text`: Text DAT for recoverable error details
- `status_channels`: Script CHOP or equivalent channel display for `running`, `done`, `error`, `request_id`, `complete_count`, `error_count`, and `retry_count`
- `callback_target`: DAT/operator with `demo_callbacks.py` and an `onRouterResult(payload)` callback
- `callback_payload`: Text DAT showing the most recent callback payload
- `frame_counter`: any visible counter/FPS indicator that keeps changing while a request is running
- DAT Execute on `prompt_input` that calls `router_callbacks.onPromptTableChange(dat)`

## Router Parameters

Use these shareable defaults:

- `Provider`: `openai_compatible`
- `Baseurl`: `http://localhost:11434/v1`
- `Model`: `llama3.2`
- `Timeout`: `30`
- `Promptdat`: `prompt_input`
- `Callbacktarget`: `callback_target`
- `Callbackmethod`: `onRouterResult`
- `Apikeysource`: blank

Do not save API key values in the network, README, `.toe`, or future `.tox`.

## Verification Checklist

1. Pulse `Trigger` on `llm_model_router`; confirm status becomes running immediately.
2. Confirm `frame_counter` continues changing while the request is running.
3. With Ollama or another OpenAI-compatible endpoint available, confirm response text appears in `response_text`.
4. Edit `prompt_input`; confirm the DAT Execute path triggers a request with `trigger_source` of `dat_table_change`.
5. Confirm `callback_payload` shows `request_id`, `status`, `response_text`, `error_text`, `elapsed_ms`, and `trigger_source`.
6. Change `Baseurl` to `http://localhost:9/v1`; pulse `Trigger`; confirm `error_text` and status show a recoverable connection error.
7. Set a very short timeout or use a slow local model prompt; confirm timeout/error state is recoverable and the frame counter continues.
8. Pulse `Reset`; confirm runtime status, response text, error text, and counters clear while provider, endpoint, model, prompt DAT, and callback target remain configured.
9. Pulse `Retry`; confirm the previous request is resent with a new request id and visible retry count change.

Record any failed step in `.planning/phases/01-async-router-proof/01-03-SUMMARY.md` before treating Phase 1 as complete.
