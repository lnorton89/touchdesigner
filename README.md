# Native LLM Operators for TouchDesigner

Call local and cloud LLMs directly from the TouchDesigner node graph through reusable, async-native operators.

Drop in a `.tox`, configure a model endpoint, send prompts from DATs/CHOPs, and receive structured output without freezing the network or running an external wrapper.

---

## Project Status

Phase 1 (Async Router Proof) implementation is complete. TouchDesigner runtime verification is in progress.

| Phase | Status |
|-------|--------|
| 1 — Async Router Proof | UAT pending |
| 2 — Agent Conversation Loop | Pending |
| 3 — TD Tool Calling | Pending |
| 4 — Packaging & Dependency Bootstrap | Pending |

---

## Architecture

The toolkit is built as a TouchDesigner COMP family with Python extension classes:

- **Model Router** — Configures provider, endpoint, model, and timeout. Central `request()` dispatches non-blocking LLM calls on a worker thread and delivers results back through TD-safe callback paths. DAT/CHOP outputs expose request lifecycle state (idle, running, complete, error).
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
├── td_components/llm_model_router/   # Model Router COMP extension
│   ├── ModelRouterExt.py             # TouchDesigner extension class
│   ├── router_http.py                # HTTP request/response layer
│   ├── router_callbacks.py           # Parameter and DAT callback handlers
│   └── README.md                     # Component docs
├── scripts/
│   ├── bootstrap-venv.ps1            # External venv setup
│   ├── start-llama-server.ps1        # llama.cpp server launcher
│   ├── setup-td-path.py              # TD sys.path injection
│   └── check-deps.py                 # Dependency health check
├── demo/                             # TD demo project files
├── tox/                              # .tox component build guide
├── tests/
│   └── test_router_payloads.py       # Unit tests
└── .planning/                        # Project planning and phase artifacts
```

---

## Development

```powershell
# Run tests
python -m unittest tests.test_router_payloads -v
```

The Model Router uses only Python stdlib (`urllib.request`, `threading`). No external
dependencies are required at runtime. Phase 4 will add an external virtual environment
for optional dependencies (httpx, pydantic, LiteLLM).

---

## Roadmap

- Phase 1: Async Router Proof ✅
- Phase 2: Agent conversation loop with history management
- Phase 3: TD-native tool calling round trip
- Phase 4: Reusable `.tox` packaging with dependency bootstrap

---

## License

MIT
