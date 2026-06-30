# LLM Operator Demo Project

A complete TouchDesigner demo network demonstrating non-blocking LLM calls
through the Model Router component.

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

### 0. Open the demo project

Double-click `demo/demo.toe` to open the pre-built TouchDesigner project,
or run `File → Open` in TD. The network contains a `base_llm_demo` container
with all operators pre-placed.

To regenerate the `.toe` from source (requires TouchDesigner installed):

```powershell
python scripts/generate-demo-toe.py
```

### 1. Start an LLM server

```powershell
.\scripts\start-llama-server.ps1
```

Or use Ollama:

```powershell
ollama pull llama3.2
ollama serve
```

### 2. Create a new TD project

Open TouchDesigner and create a new project file (File → New).

### 3. Add startup script

- Create a Text DAT named `startup`
- Copy `demo/startup.py` into it
- In the DAT's Execute page: enable **Run ON Start**
- The startup script injects the external venv (if `bootstrap-venv.ps1` was run)
  and registers the demo module

### 4. Build the network

- Create a Text DAT named `build`
- Copy `demo/build_network.py` into it
- Click **Run Script** (or pulse the DAT Execute)

This creates a `base_llm_demo` container with all operators wired up.

### 5. Add callback source

- Create a Text DAT named `callback_target`
- Copy `demo/callbacks.py` into it
- Set `Callbacktarget` on the router to point to this DAT

### 6. Wire source modules

Create Text DATs inside the router for the three source modules:

| DAT Name | Source File |
|----------|-------------|
| `source_router_http` | `td_components/llm_model_router/router_http.py` |
| `source_router_ext` | `td_components/llm_model_router/ModelRouterExt.py` |
| `source_router_callbacks` | `td_components/llm_model_router/router_callbacks.py` |

Set the router's Extension to `source_router_ext.ModelRouter` and enable
**Python 3** and **Extension is My Class**.

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
