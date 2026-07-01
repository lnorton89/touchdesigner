# LLM Operator Demo Project

`demo/demo.toe` is the end-to-end TouchDesigner demo for the native LLM operator family. It shows the Router, Agent, Tool Registry, and MCP Bridge working together without blocking the TD main thread.

The project is generated from `scripts/toe_builder.py`. Regenerate it after source changes with:

```powershell
python scripts/generate-demo-toe.py
```

## End-To-End Use

### 1. Install the external environment

TouchDesigner should not be used as the package install target. Install dependencies into the project venv:

```powershell
.\scripts\bootstrap-venv.ps1
```

### 2. Start a local model endpoint

Use Ollama:

```powershell
ollama pull llama3.2
ollama serve
```

Or use the llama.cpp helper:

```powershell
.\scripts\start-llama-server.ps1
```

Default demo settings use OpenAI-compatible URLs:

| Provider | URL |
|---|---|
| Ollama | `http://localhost:11434/v1` |
| llama.cpp | `http://127.0.0.1:8080/v1` |

### 3. Open the demo

Open `demo/demo.toe` in TouchDesigner. The startup smoke path should write to `test_results`:

```text
Bridge started
Router smoke complete
Agent smoke complete
```

The generated file also contains `demo_process` and `node_reference` Text DATs inside `base_llm_demo`, so the walkthrough travels with the `.toe`.

### 4. Use the Router path

1. Edit `prompt_input`.
2. Trigger a router request from the generated demo controls when the Custom parameter page is available, or through the MCP route:

```text
/td/router_demo_action?action=pulse
```

3. Read the outputs:

| Node | Output |
|---|---|
| `response_text` | latest response text |
| `error_text` | latest error |
| `status_json` | full router state |
| `status_channels` | CHOP lifecycle channels |
| `callback_payload` | flattened callback payload |

Useful route actions: `pulse`, `retry`, `reset`, `dat_change`, `slow`, `error`, `local_endpoint`, `collect`.

### 5. Use the Agent path

1. Edit `agent_message`.
2. Trigger an agent request:

```text
/td/agent_demo_action?action=pulse
```

3. Read `agent_response`, `agent_status_json`, `agent_history`, `agent_error`, and `agent_response_json`.

Useful route actions: `pulse`, `clear`, `local_endpoint`, `collect`.

### 6. Use the Tool path

The Tool Registry demo exposes two TD-side tools:

| Tool | Effect |
|---|---|
| `set_demo_value` | writes `tool_value` |
| `set_demo_chop` | writes `tool_chop.par.value0` |

Drive it through the bridge route:

```text
/td/tool_demo_action?action=list
/td/tool_demo_action?action=execute
/td/tool_demo_action?action=chop
```

Useful route actions: `list`, `execute`, `chop`, `invalid`, `model_start`, `model_collect`.

### 7. Use the MCP Bridge

Start the companion MCP server outside TouchDesigner:

```powershell
.\.venv\Scripts\python.exe td_mcp_server.py
```

Connect an MCP client to:

```text
http://127.0.0.1:8765/mcp
```

The TD-side bridge listens on `http://127.0.0.1:9876` and is started by the demo smoke runner.

## Main Component Controls

On project load, `test_runner` calls `demo_panel_helper.install_demo_panel(parent(), bridge)`. When TouchDesigner allows runtime custom parameter creation, `base_llm_demo` gets an `LLM Demo` custom parameter page with editable provider/model/prompt fields and named Router, Agent, and Tool action pulses.

The helper avoids hand-authoring fragile expanded `.toe` panel internals. The route-backed actions above remain the canonical controls until a dedicated Parameter Execute DAT is added for custom pulse callbacks. If a TD build blocks runtime custom parameters, use the visible DATs and MCP demo routes above; the demo still works.

## Node Reference

### User-Facing Nodes

| Node | Purpose |
|---|---|
| `demo_process` | In-project end-to-end walkthrough. |
| `node_reference` | In-project inventory of generated nodes. |
| `prompt_input` | Prompt for direct Router requests. |
| `response_text` | Latest Router response text. |
| `error_text` | Latest Router error text. |
| `status_json` | Full Router state JSON. |
| `status_channels` | Router lifecycle CHOP channels. |
| `callback_payload` | Flattened Router callback payload. |
| `agent_message` | User message for Agent requests. |
| `agent_response` | Latest Agent assistant text. |
| `agent_response_json` | Raw Agent result payload. |
| `agent_error` | Latest Agent error text. |
| `agent_status_json` | Full Agent state JSON. |
| `agent_history` | JSON conversation history. |
| `tool_value` | Text DAT mutated by `set_demo_value`. |
| `tool_chop` | Constant CHOP mutated by `set_demo_chop`. |
| `tool_result` | Latest tool list/execution result. |
| `test_results` | Startup smoke-test log. |

### Operator Components

| Node | Purpose |
|---|---|
| `llm_model_router` | Async OpenAI-compatible request router. |
| `llm_agent` | Conversation/history layer that delegates to the Router. |
| `llm_tool_registry` | Tool schema and execution registry source. |

### Configuration And Source Nodes

| Node | Purpose |
|---|---|
| `router_config` | Human-readable Router defaults for the demo. |
| `agent_config` | Human-readable Agent defaults for the demo. |
| `callback_target` | Router callback source. |
| `startup` | Venv/path bootstrap script. |
| `demo_panel_helper` | Runtime custom parameter installer. |

### Internal Smoke-Test Nodes

| Node | Purpose |
|---|---|
| `test_runner` | Starts the TD bridge pump and Router smoke path. |
| `agent_runner` | Runs the Agent smoke path after startup. |
| `frame_counter` | Visual nonblocking proof while requests are running. |

These internal nodes are intentionally kept because they make the generated project self-testing. For a production `.tox`, you can remove `test_runner`, `agent_runner`, `test_results`, `demo_process`, and `node_reference` after validating the exported component.

## Regeneration Notes

The `.toe` is generated through `toeexpand`/`toecollapse`. Do not hand-edit expanded files unless needed. If you do, preserve the project conventions from `AGENTS.md`: LF endings, trailing newlines for `.n`/`.parm`, no empty one-row `.text` files, and canonical TOC ordering.
