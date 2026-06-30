# LLM Operator Demo Project

A complete TouchDesigner demo network demonstrating non-blocking LLM calls
through the Model Router component. Pre-configured for llama.cpp by default.

## Project Layout

```
demo/
├── README.md               ← this file
├── callbacks.py            ← Callback and utility functions for TD
├── build_network.py        ← TD script that auto-constructs the network
├── startup.py              ← Startup script for venv injection + module registration
└── demo.toe                ← Auto-generated TouchDesigner project (open this)
```

## Quick Start

### 0. Start an LLM server (one time)

```powershell
.\scripts\start-llama-server.ps1
```

Or use Ollama (change Provider to `ollama` on the router):

```powershell
ollama pull llama3.2
ollama serve
```

### 1. Open the demo project

Double-click `demo/demo.toe` to open the pre-built TouchDesigner project.
The network self-configures — source DATs are pre-populated, Extension is
set, and the startup script runs on load.

Default configuration:
- **Provider**: `llama.cpp` (auto-resolves to `http://127.0.0.1:8080/v1`)
- **Model**: `gemma-2-2b-it`

To regenerate the `.toe` from source:

```powershell
python scripts/generate-demo-toe.py
```

### 2. Install dependencies (first time only)

```powershell
.\scripts\bootstrap-venv.ps1
```

This creates a `.venv` in the project root with required packages.
The startup DAT inside the `.toe` injects this venv at runtime.

### 3. Use it

1. Type a prompt in **prompt_input** (Text DAT)
2. Pulse **Trigger** on the router — status becomes `running`
3. **Frame counter** keeps ticking (nonblocking proof)
4. Response appears in **response_text**
5. Errors appear in **error_text**

## Manual Setup (for reference)

If building the network by hand instead of using the pre-built `.toe`:

## Network Layout

```
base_llm_demo (Base COMP)
├── llm_model_router          ← Model Router (extension: ModelRouter)
│   ├── source_router_http    ← HTTP layer (Text DAT)
│   ├── source_router_ext     ← Extension class (Text DAT)
│   └── source_router_callbacks ← Callbacks (Text DAT)
├── prompt_input              ← Your prompt goes here (Text DAT)
├── response_text             ← LLM response appears here (Text DAT)
├── status_json               ← Status snapshot as JSON (Text DAT)
├── error_text                ← Error details (Text DAT)
├── status_channels           ← Lifecycle CHOP channels (CHOP)
├── callback_target           ← demo_callbacks module (Text DAT)
├── callback_payload          ← Raw callback payload (Text DAT)
├── frame_counter             ← FPS counter for nonblocking proof (CHOP)
└── startup                   ← Startup script (Text DAT)
```

## Verifying It Works

1. **Pulse Trigger** — status becomes `running`
2. **Frame counter** keeps ticking during the request (nonblocking proof)
3. **Response** appears in `response_text`
4. **Edit prompt_input** — triggers a request via `dat_table_change`
5. **Set Baseurl to `http://localhost:9/v1`** — error appears in `error_text`
6. **Pulse Reset** — runtime state clears
7. **Pulse Retry** — resends last request with incremented retry count

## Export as .tox

Once the network works, right-click `base_llm_demo` → Export Component → Save
as `LLM-Router-Demo.tox`. This single `.tox` contains everything needed to
drop the demo into any TD project.

See `tox/STRUCTURE.md` for detailed export instructions.
