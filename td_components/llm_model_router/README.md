# LLM Model Router

Phase 1 targets the newest TouchDesigner build installed on this system:

- TouchDesigner: `2022.25370`
- Install path: `C:\Program Files\Derivative\TouchDesigner.2022.25370`
- Embedded Python observed from installed DLLs: Python `3.9`
- Thread Manager status: not assumed by this scaffold; the worker plan must support a raw Python thread plus TD-side handoff fallback until this is confirmed inside TouchDesigner.

## Component Contract

Use a COMP named `llm_model_router` with a source-exported extension class named `ModelRouter`.

Custom parameter names are stable for later `.tox` packaging:

- `Provider`: default `openai_compatible`
- `Baseurl`: default `http://localhost:11434/v1`
- `Model`: default `llama3.2`
- `Timeout`: default `30`
- `Promptdat`: optional DAT prompt source
- `Callbacktarget`: optional TD operator receiving async results
- `Callbackmethod`: default `onRouterResult`
- `Apikeysource`: placeholder for a TD/environment secret source, never a saved key value
- `Trigger`: manual request pulse
- `Reset`: runtime-state reset pulse
- `Retry`: resend the last request with a new request id
- `Statusdisplay`: optional display target

Both parameter pulse and DAT/table-change triggers call the same central `ModelRouter.request(...)` API. Reset and retry call `ModelRouter.reset()` and `ModelRouter.retry()` respectively.

## Distribution Notes

This scaffold uses localhost defaults and contains no private filesystem paths in runtime config, no embedded credentials, and no hard dependency on machine-specific TouchDesigner state. Phase 4 packaging should re-check extension reload/source-export behavior inside the target TouchDesigner build before exporting a distributable `.tox`.
