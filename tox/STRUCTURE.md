# .tox Component Structure

The `.tox` file is a TouchDesigner component exported from a Base COMP. This
document describes how to construct it inside TD for export.

---

## Creating the Component

### 1. Create a Base COMP

- **Add** a Base COMP to your network
- **Name** it `llm_model_router` (or however you want it to appear in TD)
- This will be the root of the `.tox` export

### 2. Add Custom Parameters

Select the Base COMP and open the **Parameters** window.
Click the **+** button (or right-click the parameter list) and add:

| Name | Type | Default | Label |
|------|------|---------|-------|
| `Provider` | Menu | `openai_compatible` | Provider |
| `Baseurl` | String | `http://localhost:11434/v1` | Base URL |
| `Model` | String | `llama3.2` | Model |
| `Timeout` | Float | `30` | Timeout |
| `Promptdat` | DAT Reference | (none) | Prompt DAT |
| `Callbacktarget` | COMP Reference | (none) | Callback Target |
| `Callbackmethod` | String | `onRouterResult` | Callback Method |
| `Apikeysource` | String | `LLM_API_KEY` | API Key Source |
| `Trigger` | Pulse | — | Trigger |
| `Reset` | Pulse | — | Reset |
| `Retry` | Pulse | — | Retry |
| `Statusdisplay` | DAT Reference | (none) | Status Display |

**Provider menu options:** `openai_compatible`, `ollama`, `llama.cpp`

### 3. Add Source DATs

Inside the Base COMP, create the following DATs:

#### `source_router_http` (Text DAT)

Contents of `td_components/llm_model_router/router_http.py` — the HTTP
request/response layer.

#### `source_router_callbacks` (Text DAT)

Contents of `td_components/llm_model_router/router_callbacks.py` — parameter
pulse and DAT table-change callback handlers.

#### `source_router_ext` (Text DAT)

Contents of `td_components/llm_model_router/ModelRouterExt.py` — the
ModelRouter extension class.

> **Note:** When the `.tox` is loaded in a new project, TD needs to find the
> `ModelRouter` extension class. Set the COMP's **Extension** field (in the
> `Extensions` page of the Base COMP parameters) to point to
> `source_router_ext.ModelRouter`.

### 4. Add Output DATs

#### `response_text` (Text DAT)

Will receive the LLM response text. Leave empty — the extension writes to it.

#### `error_text` (Text DAT)

Will receive error messages. Leave empty — the extension writes to it.

#### `status_json` (Text DAT)

Will receive the full status snapshot as JSON. Leave empty.

### 5. Add Output CHOP

#### `status_channels` (CHOP)

Will receive channels for: `running`, `done`, `error`, `request_id`,
`complete_count`, `error_count`, `retry_count`.

### 6. Configure Callbacks

Wire the `Trigger` pulse to call `source_router_callbacks.onTriggerPulse`.
Wire the `Reset` pulse to `source_router_callbacks.onResetPulse`.
Wire the `Retry` pulse to `source_router_callbacks.onRetryPulse`.

Wire the `Promptdat` table change to `source_router_callbacks.onPromptTableChange`.

### 7. Set Extension Class

In the Base COMP's **Extensions** page:
- **Extension:** `source_router_ext.ModelRouter`
- Enable **Extension is My Class** and **Python 3**

### 8. Export as .tox

Right-click the Base COMP → **Export Component...** → Save as `LLM-Router.tox`

---

## Startup Script

Add a startup script to your TD project (or the `.tox` itself) that injects
the external venv's site-packages into `sys.path`:

```python
import sys
sys.path.insert(0, r'C:\path\to\.venv\Lib\site-packages')
```

Or use the included `scripts/setup-td-path.py` for auto-detection
(place its contents in a Text DAT and execute on startup).

---

## Dependency Bootstrapping

Before loading the `.tox` in a clean project:

```powershell
.\scripts\bootstrap-venv.ps1
```

Run the health check inside TD to verify everything is loadable:

```python
exec(open(r'C:\path\to\scripts\check-deps.py').read())
```
