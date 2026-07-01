# Native LLM Operators for TouchDesigner

Call local and cloud LLMs directly from the TouchDesigner node graph through reusable, async-native operators.

Drop in a `.tox`, configure a model endpoint, send prompts from DATs/CHOPs, and receive structured output without freezing the network or running an external wrapper.

## Project Status

Phase 1 (Async Router Proof), the Agent conversation layer, the Tool Registry, and the MCP Gateway are implemented in the generated demo project. TouchDesigner runtime verification is still in progress.

| Phase | Status |
|---|---|
| 1 - Async Router Proof | UAT pending |
| MCP Gateway | Implemented |
| 2 - Agent Conversation Loop | Implemented |
| 3 - TD Tool Calling | Implemented |
| 4 - Packaging & Dependency Bootstrap | Pending |

## Architecture

The toolkit is built as a TouchDesigner COMP family with Python extension classes:

- **Model Router** - Configures provider, endpoint, model, and timeout. Central `request()` dispatches non-blocking LLM calls on a worker thread and delivers results back through TD-safe callback paths. DAT/CHOP outputs expose request lifecycle state.
- **Agent** - Conversation loop with system prompt, message history, Router delegation, and configurable model override per request.
- **Tool Registry** - Convention for exposing TD operators as callable tools with provider-compatible schemas and applying tool-call results back into Agent history.
- **MCP Gateway** - Exposes TD operator capabilities as MCP tools so AI clients can read parameters, pulse triggers, inspect DATs, and explore the node graph. A companion FastMCP server (`:8765`) communicates with a stdlib HTTP bridge (`:9876`) running inside TD using the `td.run()` pattern for safe main-thread operator access.

## Quick Start

### 1. Start An LLM Server

Using **llama.cpp**:

```powershell
.\scripts\start-llama-server.ps1
```

Or use **Ollama**:

```powershell
ollama pull llama3.2
ollama serve
```

### 2. Place The Model Router

Add an `llm_model_router` COMP to your network. Configure:

| Parameter | Value |
|---|---|
| Provider | `llama.cpp`, `ollama`, or `openai_compatible` |
| Base URL | Auto-resolves per provider; override for custom endpoints |
| Model | Model name, such as `qwen3-coder-a3b-30b` or `llama3.2` |

### 3. Send A Prompt

- Pulse the `Trigger` parameter.
- Or wire a DAT to `Promptdat`; changes can fire automatically through the callback helper.

The response arrives in the output DAT and lifecycle CHOP.

### 4. Open The End-To-End Demo

Open `demo/demo.toe` to see the Router, Agent, Tool Registry, and MCP Bridge together. The demo contains `demo_process` and `node_reference` DATs inside `base_llm_demo`; those travel with the `.toe` and explain each node in place.

See [demo/README.md](demo/README.md) for the full walkthrough.

## MCP Gateway

The MCP Gateway lets AI clients interact with a live TouchDesigner project through the Model Context Protocol.

```text
MCP Client -> companion MCP server (:8765) -> TD bridge (:9876) -> td.op()
```

The MCP server runs as a companion process in the external virtual environment. The TD-side bridge is stdlib-only and dispatches TouchDesigner API access onto the main thread.

### Available Tools

| Tool | Description |
|---|---|
| `td_get_parameter` | Read an operator parameter value and type |
| `td_set_parameter` | Set an operator parameter to a new value |
| `td_get_dat_text` | Read full text content of a DAT operator |
| `td_pulse_trigger` | Fire a pulse parameter |
| `td_list_network_children` | List child operators |
| `td_read_chop_channel` | Read CHOP channel samples |

### Setup

```powershell
# 1. Bootstrap the external venv with MCP dependencies
.\scripts\bootstrap-venv.ps1

# 2. Start the companion MCP server
.\.venv\Scripts\python.exe td_mcp_server.py

# 3. In TouchDesigner, start the bridge extension
op('mcp_bridge1').ext.MCPBridge.start()
```

Point MCP-compatible clients at `http://127.0.0.1:8765/mcp`.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TD_MCP_PORT` | `8765` | MCP server listen port |
| `TD_BRIDGE_URL` | `http://127.0.0.1:9876` | TD bridge base URL |

## Providers

| Provider | Default Endpoint | Notes |
|---|---|---|
| `openai_compatible` | `http://localhost:11434/v1` | Generic OpenAI-compatible API |
| `ollama` | `http://localhost:11434/v1` | Ollama local server |
| `llama.cpp` | `http://127.0.0.1:8080/v1` | llama.cpp server via companion project |

## Project Layout

```text
touchdesigner/
+-- td_mcp_server.py
+-- td_components/
|   +-- llm_model_router/
|   +-- llm_agent/
|   +-- llm_tool_registry/
|   +-- mcp_bridge/
+-- scripts/
+-- demo/
+-- tests/
+-- .planning/
```

## Development

```powershell
python -m unittest discover -s tests -v
```

The Router, TD-side bridge, Agent, and Tool Registry use Python stdlib in TouchDesigner. The companion MCP server uses dependencies from `requirements.txt` in the external venv.

## Roadmap

- Phase 1: Async Router Proof complete
- MCP Gateway: Companion server + TD bridge complete
- Phase 2: Agent conversation loop with history management complete
- Phase 3: TD-native tool calling round trip complete
- Phase 4: Reusable `.tox` packaging with dependency bootstrap

## License

MIT
