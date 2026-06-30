# Native LLM Operators for TouchDesigner

Call local and cloud LLMs directly from the TouchDesigner node graph through reusable, async-native operators.

Drop in a `.tox`, configure a model endpoint, send prompts from DATs/CHOPs, and receive structured output without freezing the network or running an external wrapper.

---

## Project Status

Phase 1 (Async Router Proof) implementation is complete. MCP Gateway (companion server + TD bridge) is implemented. TouchDesigner runtime verification is in progress.

| Phase | Status |
|-------|--------|
| 1 — Async Router Proof | UAT pending |
| MCP Gateway | Implemented |
| 2 — Agent Conversation Loop | Pending |
| 3 — TD Tool Calling | Pending |
| 4 — Packaging & Dependency Bootstrap | Pending |

---

## Architecture

The toolkit is built as a TouchDesigner COMP family with Python extension classes:

- **Model Router** — Configures provider, endpoint, model, and timeout. Central `request()` dispatches non-blocking LLM calls on a worker thread and delivers results back through TD-safe callback paths. DAT/CHOP outputs expose request lifecycle state (idle, running, complete, error).
- **MCP Gateway** — Exposes TD operator capabilities as MCP (Model Context Protocol) tools so AI clients like Claude can read parameters, pulse triggers, inspect DATs, and explore the node graph. A companion FastMCP server (`:8765`) communicates with a stdlib HTTP bridge (`:9876`) running inside TD using the `td.run()` pattern for safe main-thread operator access.
- **Agent** *(planned)* — Conversation loop with system prompt, message history, and configurable model override per request.
- **Tool Registry** *(planned)* — Convention for exposing TD operators as callable tools with provider-compatible schemas.

---

## Quick Start

### 1. Start an LLM server

Using **llama.cpp** (recommended for local inference):

```powershell
.\scripts\start-llama-server.ps1
```

Or use **Ollama**:

```powershell
ollama pull llama3.2
```

### 2. Place the Model Router

Add an `llm_model_router` COMP to your network. Configure:

| Parameter | Value |
|-----------|-------|
| Provider | `llama.cpp`, `ollama`, or `openai_compatible` |
| Base URL | Auto-resolves per provider — override for custom endpoints |
| Model | Model name (e.g. `qwen3-coder-a3b-30b` or `llama3.2`) |

### 3. Send a prompt

- **Pulse** the Trigger parameter
- Or wire a DAT to `Promptdat` — changes fire automatically

The response arrives in the output DAT and lifecycle CHOP.

---

## MCP Gateway

The MCP Gateway lets AI clients (Claude Desktop, Cursor, custom tools) interact with a live TouchDesigner project through the Model Context Protocol.

### Architecture

```
MCP Client ──► companion MCP server (:8765) ──► TD bridge (:9876) ──► td.op()
  (Claude)        (FastMCP, external venv)        (stdlib HTTP, inside TD)
```

The MCP server runs as a **companion process** in the external virtual environment — completely separate from TD. This avoids ASGI event-loop conflicts and provides crash isolation. A lightweight stdlib HTTP bridge inside TD receives tool execution requests and dispatches them to `td.op()` on the main thread using the same `td.run()` pattern as the Model Router.

### Available Tools

| Tool | Description |
|------|-------------|
| `td_get_parameter` | Read an operator parameter value and type |
| `td_set_parameter` | Set an operator parameter to a new value |
| `td_get_dat_text` | Read full text content of a DAT operator |
| `td_pulse_trigger` | Fire a pulse parameter (one-shot trigger) |
| `td_list_network_children` | List child operators (filterable by type) |
| `td_read_chop_channel` | Read CHOP channel samples (sliceable) |

### Setup

```powershell
# 1. Bootstrap the external venv with MCP dependencies
.\scripts\bootstrap-venv.ps1

# 2. Start the companion MCP server (runs until killed)
.\.venv\Scripts\python.exe td_mcp_server.py

# 3. In TouchDesigner: drop a COMP, set its extension to mcp_bridge, call start()
#    op('mcp_bridge1').ext.MCPBridge.start()
```

### Connecting an MCP Client

Point any MCP-compatible client at `http://127.0.0.1:8765/mcp`:

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "touchdesigner": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

**Verification with curl:**
```powershell
curl -X POST http://127.0.0.1:8765/mcp `
  -H "Content-Type: application/json" `
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TD_MCP_PORT` | `8765` | MCP server listen port |
| `TD_BRIDGE_URL` | `http://127.0.0.1:9876` | TD bridge base URL |

---

## Providers

| Provider | Default Endpoint | Notes |
|----------|-----------------|-------|
| `openai_compatible` | `http://localhost:11434/v1` | Generic OpenAI-compatible API |
| `ollama` | `http://localhost:11434/v1` | Ollama local server |
| `llama.cpp` | `http://127.0.0.1:8080/v1` | llama.cpp server via companion project |

---

## Project Layout

```
touchdesigner/
├── td_mcp_server.py                    # Companion MCP server (FastMCP)
├── td_components/
│   ├── llm_model_router/               # Model Router COMP extension
│   │   ├── ModelRouterExt.py           # TouchDesigner extension class
│   │   ├── router_http.py              # HTTP request/response layer
│   │   ├── router_callbacks.py         # Parameter and DAT callback handlers
│   │   └── README.md                   # Component docs
│   └── mcp_bridge/                     # MCP Bridge COMP extension
│       ├── MCPBridgeExt.py             # TD-side HTTP bridge (stdlib)
│       ├── MCPBridge_config.py         # Bridge configuration
│       └── __init__.py                 # Package init
├── scripts/
│   ├── bootstrap-venv.ps1              # External venv setup
│   ├── start-llama-server.ps1          # llama.cpp server launcher
│   ├── setup-td-path.py                # TD sys.path injection
│   └── check-deps.py                   # Dependency health check
├── demo/                               # TD demo project files
├── tests/
│   └── test_router_payloads.py         # Unit tests
└── .planning/                          # Project planning and phase artifacts
```

---

## Development

```powershell
# Run tests
python -m unittest tests.test_router_payloads -v
```

### Dependencies

The Model Router uses only Python stdlib (`urllib.request`, `threading`). No external dependencies are required at runtime for Phase 1.

The MCP Gateway requires `mcp>=1.27` and `httpx>=0.27` (installed into the external venv via `pip install -r requirements.txt`). The TD-side bridge is stdlib-only.

## Roadmap

- Phase 1: Async Router Proof ✅
- MCP Gateway: Companion server + TD bridge ✅
- Phase 2: Agent conversation loop with history management
- Phase 3: TD-native tool calling round trip
- Phase 4: Reusable `.tox` packaging with dependency bootstrap

---

## License

MIT
