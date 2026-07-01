# .tox Component Structure

The generated demo can be exported as a `.tox`, but there are two useful export shapes:

- **Demo tox**: export `base_llm_demo` with docs, smoke runners, Router, Agent, Tool Registry, and demo outputs.
- **Production Router tox**: export only `llm_model_router` plus its source DATs and expected output conventions.

## Demo Tox

Export `base_llm_demo` when you want the complete teachable project.

### Required Children

| Node | Keep? | Why |
|---|---|---|
| `llm_model_router` | yes | Async model request component. |
| `llm_agent` | yes | Conversation/history demo. |
| `llm_tool_registry` | yes | Tool schema/execution demo. |
| `prompt_input`, `response_text`, `error_text`, `status_json`, `status_channels` | yes | Router input/output surface. |
| `agent_message`, `agent_response`, `agent_response_json`, `agent_error`, `agent_status_json`, `agent_history` | yes | Agent input/output surface. |
| `tool_value`, `tool_chop`, `tool_result` | yes | Tool-call demo targets and results. |
| `callback_target`, `callback_payload` | yes | Router callback example. |
| `startup`, `demo_panel_helper` | yes | Runtime path/bootstrap and best-effort custom controls. |
| `demo_process`, `node_reference` | optional | In-tox documentation. Keep for teaching, remove for minimal packaging. |
| `test_runner`, `agent_runner`, `test_results` | optional | Startup smoke tests. Keep for demo, remove for production. |
| `frame_counter` | optional | Visual nonblocking proof. |

### Main Component Controls

`demo_panel_helper` creates an `LLM Demo` Custom parameter page on `base_llm_demo` at startup when the TD Python API allows runtime custom parameters. It adds:

| Control | Purpose |
|---|---|
| `Provider`, `Baseurl`, `Model`, `Timeout` | Editable model endpoint defaults. |
| `Prompt` | Prompt text to sync into `prompt_input`. |
| `Agentmessage` | Message text to sync into `agent_message`. |
| `Routerpulse`, `Routerretry`, `Routerreset` | Router action pulses. |
| `Agentpulse`, `Agentclear` | Agent action pulses. |
| `Toollist`, `Toolexecute`, `Toolchop` | Tool demo pulses. |

The helper uses TouchDesigner's own runtime API instead of writing expanded `.toe` panel internals by hand. The named action pulses are exposed on the component, but the route-backed MCP demo actions remain the canonical working controls until a dedicated Parameter Execute DAT is added to bind those custom pulses.

## Production Router Tox

Export `llm_model_router` when you only need the Router operator.

### Custom Parameters

| Name | Type | Default | Label |
|---|---|---|---|
| `Provider` | Menu | `openai_compatible` | Provider |
| `Baseurl` | String | `http://localhost:11434/v1` | Base URL |
| `Model` | String | `llama3.2` | Model |
| `Timeout` | Float | `30` | Timeout |
| `Promptdat` | DAT Reference | empty | Prompt DAT |
| `Callbacktarget` | COMP/DAT Reference | empty | Callback Target |
| `Callbackmethod` | String | `onRouterResult` | Callback Method |
| `Apikeysource` | String | `LLM_API_KEY` | API Key Source |
| `Trigger` | Pulse | empty | Trigger |
| `Reset` | Pulse | empty | Reset |
| `Retry` | Pulse | empty | Retry |
| `Statusdisplay` | DAT Reference | empty | Status Display |

Provider menu options: `openai_compatible`, `ollama`, `llama.cpp`.

### Required Source DATs

| DAT | Contents |
|---|---|
| `router_http` | `td_components/llm_model_router/router_http.py` |
| `router_callbacks` | `td_components/llm_model_router/router_callbacks.py` |
| `ModelRouterExt` or extension source DAT | `td_components/llm_model_router/ModelRouterExt.py` |

Set the COMP's Extension to `source_router_ext.ModelRouter` or the equivalent DAT/module path used in the exported component.

### Expected Outputs

The extension writes conventional sibling outputs when present:

| Output | Purpose |
|---|---|
| `response_text` | LLM response text |
| `error_text` | Error text |
| `status_json` | Full state snapshot |
| `status_channels` | Lifecycle channels: `running`, `done`, `error`, `request_id`, `complete_count`, `error_count`, `retry_count` |

## Startup And Dependencies

Use an external venv instead of installing packages into TouchDesigner's embedded Python:

```powershell
.\scripts\bootstrap-venv.ps1
```

The demo `startup` DAT injects the venv and project root into `sys.path`. For a production tox, include an equivalent startup script or document that the host project must run `scripts/setup-td-path.py`.

## Export

Right-click the target COMP, choose **Export Component...**, and save the `.tox`.

Before sharing, reopen the exported tox in a clean TD project and verify:

- Router pulse does not freeze the timeline.
- `response_text`, `error_text`, and `status_json` update.
- Agent history writes to `agent_history` if exporting the full demo.
- Tool execution mutates `tool_value` or `tool_chop` if exporting the full demo.
- No API key values are saved into the `.toe` or `.tox`.
