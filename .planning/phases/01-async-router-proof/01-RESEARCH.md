# Phase 1: Async Router Proof - Research

**Researched:** 2026-06-30
**Domain:** TouchDesigner Python threading, OpenAI-compatible local LLM HTTP routing, TD DAT/CHOP outputs
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

## Implementation Decisions

### Request Trigger
- **D-01:** The primary manual trigger should be a visible Router custom parameter pulse. This gives the clearest first proof and the simplest repeatable test surface inside TD.
- **D-02:** The Phase 1 demo must also include a DAT/table-change trigger path. This should prove graph-native use inspired by the video transcript's feedback-loop/table-change pattern, but it can be demo-scoped rather than the only production trigger.
- **D-03:** Both trigger paths should route through the same central Router request function so future operators do not duplicate provider-call logic.

### Callback Handoff
- **D-04:** The Router should expose an explicit callback handoff surface. Prefer a callback DAT/operator target that receives structured result payloads, with room for an operator path + method name style if that fits TD extension patterns better during implementation.
- **D-05:** The callback payload should include enough data for downstream TD logic to react without inspecting internal worker state: request id, status, response text, error text, timing, and trigger source.
- **D-06:** Callback handoff is part of the proof, not a hidden implementation detail. The demo should make it visible that worker results re-enter TD through a safe callback/run boundary.

### Router Surface
- **D-07:** The first Router COMP should feel like a real TD operator with explicit custom parameters, not a script box. Required visible params: provider type, base URL, model, timeout, prompt/input DAT reference, callback target, trigger pulse, reset pulse, retry pulse, and optional request id/status display.
- **D-08:** Required outputs: response DAT, status/error DAT, and status CHOP channels for at least `running`, `done`, `error`, and a monotonically changing `request_id` or `complete_count`.
- **D-09:** Keep the surface intentionally small. API key persistence/secrets handling remains Phase 4, but Phase 1 should leave a visible API key source placeholder or disabled field so the eventual flow has a home.

### Distribution Readiness
- **D-16:** Phase 1 is still a proof, but it should be shaped as a future distributable component: stable operator names, predictable custom parameter names, and no machine-specific paths in saved examples.
- **D-17:** Demo defaults should be safe to share. Local defaults like `http://localhost:11434` are acceptable; private filesystem paths, API keys, or user-specific TD project paths are not.
- **D-18:** Any setup assumptions discovered during Phase 1 should be documented for Phase 4 packaging rather than hidden in ad hoc local state.

### Proof of Nonblocking
- **D-10:** The nonblocking proof should be explicit. Include a deliberately slow request or simulated delay case so a user can see TD continue running while the request is in flight.
- **D-11:** The proof should expose frame-safety through status outputs rather than requiring external profiling. A simple FPS/no-freeze visual or counter in the demo is acceptable if easy.
- **D-12:** Failure cases should be first-class: unreachable endpoint, timeout, and malformed response should surface as recoverable data in DAT/CHOP outputs.

### Reset and Retry
- **D-13:** Reset should clear runtime state: current status, last response, last error, running flag, and counters where appropriate.
- **D-14:** Reset should preserve user configuration and prompt/input DAT references. Users should not have to rebuild the network after a reset.
- **D-15:** Retry should resend the last built request using current Router configuration and make the retry visible via request id/count.

### the agent's Discretion
- The user said "use best judgement" for the Phase 1 discussion. The planner may choose exact TD operator internals, worker implementation strategy, and callback mechanics as long as the decisions above remain true.
- The planner may decide whether the low-level HTTP path is direct `httpx`, TD-native web client behavior, or another compatible approach after research, but the user-facing result must remain the same: nonblocking local LLM request with safe TD handoff.

### Deferred Ideas (OUT OF SCOPE)

## Deferred Ideas

- Conversation/chat table with role/message/ID/timestamp columns belongs in Phase 2.
- Hold-chat behavior by message or token threshold belongs after Agent history exists.
- Agent parameter control, table editing, and text editing belong in Phase 3 tool calling.
- GLSL repair loop, RAG over TD docs, TOP captioning, multimodal input, and poster/design parameter demos remain later-phase or backlog examples.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROUT-01 | User can configure a Model Router COMP with provider type, base URL, model name, timeout, and API key source. | Use a Base COMP extension and custom parameters for provider, base URL, model, timeout, prompt DAT, callback target, trigger/reset/retry pulses, and API key source placeholder. [CITED: https://docs.derivative.ca/Custom_Parameters] |
| ROUT-02 | User can send a prompt through the Router to a local Ollama or OpenAI-compatible endpoint and receive plain-text output in a DAT. | Use Ollama's OpenAI-compatible `/v1/chat/completions` route for the first local path and write `choices[0].message.content` into a response DAT. [CITED: https://docs.ollama.com/openai] |
| ROUT-03 | User can see request lifecycle state from the Router, including idle, running, complete, and error. | Maintain a Router-owned state envelope and mirror it to status/error DAT plus Script CHOP channels. [CITED: https://docs.derivative.ca/Script_CHOP] |
| ROUT-05 | User can call one central Router request function from future LLM operators instead of duplicating provider-call logic. | Put all request construction and dispatch behind `ModelRouter.request(prompt=None, messages=None, trigger_source='...')`; pulse and DAT triggers call the same function. [VERIFIED: codebase grep] |
| ROUT-06 | User can configure an optional callback operator/function target that receives async request results. | Use callback target custom parameters and invoke callback only during the TD-side handoff, not from worker code. [CITED: https://docs.derivative.ca/Run_Command_Examples] |
| RUNT-01 | User can trigger an LLM request without blocking TouchDesigner's main thread. | Derivative documents main-thread blocking as frame-drop/hang/crash risk; use Thread Manager or a background Python thread for network work. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| RUNT-02 | User can receive worker results back in TD through a safe callback or run mechanism that updates output operators on the TD side. | Worker returns plain Python data; TD update is scheduled through Thread Manager callbacks or `run(..., endFrame=True)`. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] [CITED: https://docs.derivative.ca/Run_Command_Examples] |
| RUNT-03 | User can see recoverable errors in DAT/CHOP outputs instead of the network crashing or silently failing. | Catch `httpx.RequestError`, `httpx.TimeoutException`, `httpx.HTTPStatusError`, and JSON/content-shape errors and write a normalized error payload. [CITED: https://www.python-httpx.org/exceptions] |
| EXMP-01 | User can run a demo that sends a DAT message to a local Ollama model and receives a response DAT. | Demo should include prompt input DAT, response DAT, status/error DAT, and status CHOP. [VERIFIED: codebase grep] |
| EXMP-03 | User can run a Phase 1 demo from either a parameter pulse or a DAT/table-change trigger. | Use parameter pulse callback and a DAT Execute DAT `onTableChange` path; both call the same central request function. [CITED: https://docs.derivative.ca/DAT_Execute_DAT] |
| EXMP-04 | User can reset or retry the demo request state without rebuilding the network. | Reset clears runtime state only; retry resubmits the last built request under current Router configuration. [VERIFIED: codebase grep] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Do not depend on pip installing into TouchDesigner itself; TD embedded Python is version-pinned. [VERIFIED: AGENTS.md]
- Network calls must not block the main TD thread because frame stalls are project-breaking. [VERIFIED: AGENTS.md]
- Deliverable direction is a reusable `.tox` component that travels between TD projects. [VERIFIED: AGENTS.md]
- Target Windows first while avoiding hard-coded Windows-only paths where reasonable. [VERIFIED: AGENTS.md]
- API keys should be stored locally and not embedded into saved `.toe` project files. [VERIFIED: AGENTS.md]
- Ollama or another local OpenAI-compatible endpoint must work without cloud dependency. [VERIFIED: AGENTS.md]
- Use GSD workflow artifacts for planning/execution context; do not make direct repo edits outside GSD unless explicitly bypassed. [VERIFIED: AGENTS.md]

## Summary

Phase 1 should implement a single distributable-shaped `llm_model_router` Base COMP with a Python extension, not a scattered script demo. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md] The Router should read TD inputs and custom parameters on the TD side, submit a plain Python request envelope to a worker, perform only HTTP and pure-Python parsing in that worker, then marshal a structured result payload back to TD outputs and optional callback target. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]

The safest first provider path is direct OpenAI-compatible HTTP against Ollama at `http://localhost:11434/v1/chat/completions`, because Ollama officially documents OpenAI API compatibility and this avoids provider-abstraction complexity during the TD threading proof. [CITED: https://docs.ollama.com/openai] Use `httpx` for the HTTP call if adding an external dependency is acceptable after a human checkpoint; otherwise use a standard-library fallback for the first proof and document that Phase 4 should install/pin `httpx`. [CITED: https://www.python-httpx.org/quickstart]

**Primary recommendation:** Build a Router extension around `request() -> worker HTTP -> TD-side `_apply_result()` -> DAT/CHOP/callback`, with all triggers and retries routed through `request()` and all TD object writes confined to `_apply_result()`. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Custom parameter configuration | TouchDesigner COMP/UI | Router extension | TD custom parameters are the user-facing operator surface; extension code reads/evaluates them. [CITED: https://docs.derivative.ca/Custom_Parameters] |
| Prompt capture from DAT | TouchDesigner DAT layer | Router extension | Prompt DAT values are TD objects and should be read on the TD side before worker dispatch. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| Nonblocking HTTP call | Worker Python thread/task | `httpx` client | Network waiting belongs outside the TD main thread. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| Provider request/response normalization | Worker pure Python | Router extension | JSON payload shaping is pure Python and can be done off the TD thread. [CITED: https://www.python-httpx.org/quickstart] |
| DAT/CHOP output mutation | TouchDesigner main thread | Router extension | Worker threads should avoid reading/writing TD objects. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| Callback target invocation | TouchDesigner main thread | Callback DAT/operator | Callback payload should be visible and TD-native, but invoked after worker completion re-enters TD. [CITED: https://docs.derivative.ca/Run_Command_Examples] |
| Reset/retry state | Router extension | Output DAT/CHOP | Runtime state is owned by the Router; reset/retry mirror state visibly to outputs. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md] |

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| TouchDesigner Base COMP + Python extension | Installed TD build | Router operator shell and callable API | Base COMP custom parameters and extension methods match TD-native component patterns. [CITED: https://docs.derivative.ca/Component] |
| TouchDesigner Thread Manager | TD 2023.31500+ feature | Nonblocking task execution | Derivative documents it as the built-in threading/task helper for Python developers. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| TouchDesigner `run()` | Installed TD build | TD-side delayed/end-frame handoff | Derivative documents callable scheduling, `delayFrames`, and `endFrame`; use it for final TD-side updates if Thread Manager callbacks need explicit scheduling. [CITED: https://docs.derivative.ca/Run_Command_Examples] |
| `httpx` [WARNING: flagged as suspicious by GSD seam because downloads were unavailable; verify before installing.] | 0.28.1 | HTTP client for OpenAI-compatible requests | Official docs cover sync/async APIs, timeouts, request exceptions, and status exceptions. [CITED: https://www.python-httpx.org/quickstart] [VERIFIED: PyPI] |
| Ollama OpenAI compatibility | Ollama CLI 0.30.11 installed locally | Local `/v1/chat/completions` endpoint | Official Ollama docs describe partial OpenAI API compatibility for local models. [CITED: https://docs.ollama.com/openai] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| Python stdlib `asyncio` | Python 3.11 docs | Thread-safe loop scheduling if an event loop is used | Use `run_coroutine_threadsafe` or `call_soon_threadsafe` only if the Router owns a separate asyncio loop. [CITED: https://docs.python.org/3.11/library/asyncio-task.html] |
| Python stdlib `urllib.request` | Python 3.11 docs | No-install HTTP fallback | Use only if Phase 1 must avoid external dependency install before Phase 4. [ASSUMED] |
| DAT Execute DAT | Installed TD build | Table-change demo trigger | Use `onTableChange` to call the same Router request function as the pulse trigger. [CITED: https://docs.derivative.ca/DAT_Execute_DAT] |
| Script CHOP | Installed TD build | Status channels | Use for `running`, `done`, `error`, `request_id`, and `complete_count` output channels. [CITED: https://docs.derivative.ca/Script_CHOP] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TouchDesigner Thread Manager | Raw `threading.Thread` plus a queue polled from Execute DAT | More control, but more lifecycle and cleanup code; Thread Manager is the documented current TD helper. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| Direct `httpx` call | LiteLLM | LiteLLM is useful later, but Phase 1 needs a small, inspectable local path. [VERIFIED: .planning/research/STACK.md] |
| Ollama OpenAI `/v1` route | Ollama native `/api/chat` route | Native route is viable, but `/v1/chat/completions` proves generic OpenAI-compatible routing from the start. [CITED: https://docs.ollama.com/openai] |
| Script CHOP status | Constant CHOP with exported parameters | Script CHOP can publish request counters and booleans from Router state in one place. [CITED: https://docs.derivative.ca/Script_CHOP] |

**Installation:**
```bash
python -m pip install httpx==0.28.1
```

**Version verification:** `python -m pip index versions httpx` returned latest `0.28.1`; PyPI JSON reports upload time `2024-12-06T15:37:21.509172Z` and `Requires-Python >=3.8`. [VERIFIED: PyPI]

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `httpx` | PyPI | Latest release uploaded 2024-12-06 | Unknown to GSD seam | https://github.com/encode/httpx | SUS | Flagged; planner must add `checkpoint:human-verify` before install. [VERIFIED: PyPI] |

**Packages removed due to [SLOP] verdict:** none. [VERIFIED: package-legitimacy seam]
**Packages flagged as suspicious [SUS]:** `httpx`, because the legitimacy seam could not obtain download counts even though Context7 and PyPI identify the official project. [VERIFIED: package-legitimacy seam]

*Packages discovered via WebSearch or training data that have not been verified against an authoritative source are tagged `[ASSUMED]` and the planner must gate each install behind a `checkpoint:human-verify` task.* [VERIFIED: package-legitimacy protocol]

## Architecture Patterns

### System Architecture Diagram

```text
Parameter pulse / DAT table change
        |
        v
Router extension request(prompt/messages, trigger_source)
        |
        |-- TD side: read custom parameters, prompt DAT, request_id
        |-- TD side: set state=running, update status DAT/CHOP
        v
Plain Python request envelope
        |
        v
Thread Manager task or worker thread
        |
        |-- HTTP POST /v1/chat/completions
        |-- parse JSON
        |-- normalize success/error payload
        v
TD handoff via Thread Manager callback or run(..., endFrame=True)
        |
        v
Router _apply_result(payload)
        |
        |-- response DAT
        |-- status/error DAT
        |-- status CHOP
        |-- optional callback DAT/operator target
        v
Downstream TD network reacts to DAT/CHOP/callback
```

### Recommended Project Structure

```text
td_components/
├── llm_model_router/       # Router COMP source-exported scripts and docs
│   ├── ModelRouterExt.py   # Router extension; central request API and TD output writes
│   ├── router_callbacks.py # Parameter callbacks and DAT Execute callback helpers
│   └── README.md           # Setup/demo notes for Phase 1
examples/
└── phase1_async_router/    # Demo network notes/exported helper scripts
tests/
└── test_router_payloads.py # Pure-Python tests for request/response normalization
```

This repo currently has no implementation source files, tests, `pyproject.toml`, `.tox`, or `.toe`; the structure above is a first implementation recommendation, not an existing layout. [VERIFIED: codebase grep]

### Pattern 1: Central Router API

**What:** Expose one Router method, for example `request(prompt=None, messages=None, trigger_source='pulse')`, and route pulse, DAT trigger, retry, and future operators through it. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md]

**When to use:** Every time TD wants an LLM completion in Phase 1 or future phases. [VERIFIED: .planning/ROADMAP.md]

**Example:**
```python
# Source: Phase 1 context + Derivative custom parameter patterns.
def request(self, prompt=None, messages=None, trigger_source='pulse'):
    config = self._read_config_from_pars()
    envelope = self._build_request_envelope(config, prompt, messages, trigger_source)
    self._mark_running(envelope)
    self._submit_worker(envelope)
    return envelope['request_id']
```

### Pattern 2: Worker Boundary With Plain Data

**What:** Worker receives a dict and returns a dict; no `op()`, `me`, DAT, CHOP, Par, or COMP access in the worker. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]

**When to use:** All HTTP work and JSON parsing. [CITED: https://www.python-httpx.org/quickstart]

**Example:**
```python
# Source: HTTPX official docs + TD threading docs.
def worker_call_openai_compatible(envelope):
    import httpx

    url = envelope['base_url'].rstrip('/') + '/chat/completions'
    try:
        with httpx.Client(timeout=envelope['timeout']) as client:
            response = client.post(url, json={
                'model': envelope['model'],
                'messages': envelope['messages'],
                'stream': False,
            })
            response.raise_for_status()
            data = response.json()
        return normalize_success(envelope, data)
    except Exception as exc:
        return normalize_error(envelope, exc)
```

### Pattern 3: TD-Side Result Application

**What:** Apply results in one method that owns response DAT, status/error DAT, status CHOP state, counters, and callback target invocation. [CITED: https://docs.derivative.ca/Run_Command_Examples]

**When to use:** Worker completion, timeout, failed endpoint, malformed response, reset, and retry completion. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md]

**Example:**
```python
# Source: Derivative run command docs.
def on_worker_done(self, payload):
    run(self._apply_result, payload, endFrame=True)

def _apply_result(self, payload):
    self._state.update(payload)
    self._write_response_dat(payload)
    self._write_status_dat(payload)
    self._update_status_chop_state(payload)
    self._invoke_callback_target(payload)
```

### Anti-Patterns to Avoid

- **Network call in `onCook` or a parameter callback:** This blocks TD's main thread and risks dropped frames, hangs, or crashes. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
- **Worker thread touches TD objects:** Derivative recommends avoiding TD object access from other threads; pass strings, numbers, dicts, and lists instead. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
- **Separate code paths for pulse, DAT trigger, and retry:** This will duplicate provider logic and break ROUT-05; all paths must call central `request()`. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md]
- **Saving API key values in custom parameters:** Phase 1 can include an API key source placeholder, but secret persistence is Phase 4. [VERIFIED: .planning/REQUIREMENTS.md]
- **Hard-coded user paths in example networks:** Later distribution requires relative/operator paths and safe defaults. [VERIFIED: .planning/PROJECT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread/task lifecycle | Custom scheduler with ad hoc thread registry | TouchDesigner Thread Manager or a minimal worker wrapper | TD now documents Thread Manager for Python threading/task handling. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| HTTP client behavior | Raw socket client | `httpx` after checkpoint, or stdlib fallback only if dependency-free proof is required | Timeouts, request errors, and HTTP status errors are already modeled. [CITED: https://www.python-httpx.org/exceptions] |
| Provider abstraction | A broad multi-provider SDK clone | Direct OpenAI-compatible request envelope | Phase 1 only needs Ollama/generic OpenAI-compatible local proof. [VERIFIED: .planning/ROADMAP.md] |
| TD callback/event bus | Hidden global variables | Explicit callback target parameter and structured payload | Phase context requires callback handoff to be visible and inspectable. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md] |
| Secret storage | Custom encrypted config or saved parameter values | Placeholder only in Phase 1; Phase 4 handles env/local settings/credential storage | ROUT-04 is explicitly Phase 4. [VERIFIED: .planning/REQUIREMENTS.md] |

**Key insight:** The hard part is not JSON over HTTP; it is the TD runtime boundary. Use proven TD threading/handoff primitives and keep the Router's API small. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]

## Recommended Implementation Sequence

1. Create a source-exportable `llm_model_router` component skeleton with `ModelRouterExt.py`, callback DAT scripts, response/status DATs, and status Script CHOP. [VERIFIED: codebase grep]
2. Add custom parameters for provider, base URL, model, timeout, prompt DAT, callback target, trigger pulse, reset pulse, retry pulse, and API key source placeholder. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md]
3. Implement pure-Python request envelope construction and unit tests before touching TD worker execution. [ASSUMED]
4. Implement direct non-streaming `POST {base_url}/chat/completions` where default `base_url` is `http://localhost:11434/v1`. [CITED: https://docs.ollama.com/openai]
5. Add worker submission with Thread Manager first; use raw thread plus queue only if Thread Manager integration is blocked in the installed TD build. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
6. Implement `_apply_result(payload)` as the only place that mutates DAT/CHOP outputs and invokes callback target. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
7. Add DAT Execute DAT `onTableChange` and parameter pulse callbacks, both calling `request()`. [CITED: https://docs.derivative.ca/DAT_Execute_DAT]
8. Add reset and retry using preserved config and last request envelope; retry increments request id/count. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md]
9. Add demo failure cases: unreachable base URL, short timeout, malformed local response simulation, and slow prompt/simulated worker delay. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md]
10. Document local setup assumptions for Phase 4 packaging instead of encoding private paths or secrets in the network. [VERIFIED: .planning/PROJECT.md]

## Common Pitfalls

### Pitfall 1: Blocking the TD Frame Loop

**What goes wrong:** TouchDesigner drops frames, hangs, or crashes while waiting for the model response. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
**Why it happens:** Synchronous network work runs in callbacks, `onCook`, or other main-thread TD execution paths. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
**How to avoid:** Submit a worker task and immediately return to TD; update status outputs to `running`. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
**Warning signs:** UI freezes during request, FPS counter stalls, or parameter pulse does not return immediately. [ASSUMED]

### Pitfall 2: TD Object Access From Worker

**What goes wrong:** Random failures, race conditions, or crashes when worker code calls `op()`, reads DATs, or writes CHOPs. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
**Why it happens:** TD objects are main-thread runtime objects, not plain Python data. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
**How to avoid:** Read all TD input before dispatch and write all TD output after handoff. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
**Warning signs:** Worker helper imports `td`, calls `op()`, or accepts OP/Par objects instead of strings/dicts. [ASSUMED]

### Pitfall 3: Dependency Path Drift

**What goes wrong:** Code works on one machine but not after packaging or in another TD project. [VERIFIED: .planning/PROJECT.md]
**Why it happens:** External Python site-packages path is private or dependency versions conflict with TD-shipped packages. [CITED: https://docs.derivative.ca/Python]
**How to avoid:** Keep Phase 1 dependency list tiny, avoid hard-coded user paths, and surface missing `httpx` as a setup/status error. [VERIFIED: .planning/PROJECT.md]
**Warning signs:** Saved `.toe` or `.tox` includes `C:\Users\Lawrence\...` paths or imports fail only inside TD. [VERIFIED: .planning/PROJECT.md]

### Pitfall 4: Stale Results Overwriting Newer Requests

**What goes wrong:** A slow first request completes after a retry and overwrites the newer response. [ASSUMED]
**Why it happens:** Result payloads are applied without comparing request ids. [ASSUMED]
**How to avoid:** Include `request_id` in every envelope and payload; `_apply_result()` should ignore stale payloads unless a debug flag says otherwise. [ASSUMED]
**Warning signs:** Response DAT content does not match current `request_id`. [ASSUMED]

### Pitfall 5: Treating Ollama as Always Running

**What goes wrong:** Demo appears broken when Ollama CLI is installed but service/model is unavailable. [VERIFIED: local environment probe]
**Why it happens:** Local daemon availability and model pulls are runtime state, not package state. [ASSUMED]
**How to avoid:** Make unreachable endpoint a recoverable status/error output and document the local service check. [CITED: https://docs.ollama.com/openai]
**Warning signs:** `ollama --version` warns it cannot connect to a running instance. [VERIFIED: local environment probe]

## Code Examples

### OpenAI-Compatible Request Normalization

```python
# Source: Ollama OpenAI compatibility docs + HTTPX docs.
def build_openai_compatible_payload(model, prompt):
    return {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False,
    }

def parse_chat_text(data):
    return data['choices'][0]['message']['content']
```

### HTTP Error Classification

```python
# Source: https://www.python-httpx.org/exceptions
def normalize_error(envelope, exc):
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        kind = 'timeout'
    elif isinstance(exc, httpx.HTTPStatusError):
        kind = 'http_status'
    elif isinstance(exc, httpx.RequestError):
        kind = 'request_error'
    else:
        kind = 'parse_or_internal_error'

    return {
        'request_id': envelope['request_id'],
        'status': 'error',
        'error_kind': kind,
        'error_text': str(exc),
        'response_text': '',
        'trigger_source': envelope['trigger_source'],
    }
```

### DAT Trigger Callback

```python
# Source: DAT Execute DAT docs.
def onTableChange(dat):
    router = op('../llm_model_router')
    router.ext.ModelRouter.request(trigger_source='dat_table_change')
    return
```

### TD-Side Output Application

```python
# Source: Derivative run command docs and TD threading docs.
def _schedule_apply_result(self, payload):
    run(self._apply_result, payload, endFrame=True)

def _apply_result(self, payload):
    # Only this method mutates TouchDesigner operators.
    self._write_status_dat(payload)
    self._write_response_dat(payload.get('response_text', ''))
    self._set_status_channels(payload)
    self._call_callback_target(payload)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw Python threads plus Execute DAT polling | TouchDesigner Thread Manager / Thread Manager Client | TD 2023.31500+ per Derivative docs | Prefer built-in task/callback helper for Phase 1, fallback only if installed TD build lacks it. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| Provider-specific Ollama native route only | OpenAI-compatible `/v1` local route | Ollama official docs current as fetched 2026-06-30 | Lets Phase 1 prove generic OpenAI-compatible routing with local Ollama default. [CITED: https://docs.ollama.com/openai] |
| Installing packages into TD Python | Parallel Python 3.11 package path | Derivative Python docs current as fetched 2026-06-30 | Keep external dependencies isolated and document path injection for Phase 4. [CITED: https://docs.derivative.ca/Python] |

**Deprecated/outdated:**
- Direct package installation into TouchDesigner's embedded Python is out of scope for this project and conflicts with project constraints. [VERIFIED: .planning/REQUIREMENTS.md]
- Broad provider abstraction in Phase 1 is premature; local OpenAI-compatible proof is the roadmap target. [VERIFIED: .planning/ROADMAP.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python stdlib `urllib.request` can serve as a no-install fallback for the first proof. | Standard Stack | Planner may overestimate ease of timeout/error handling without `httpx`. |
| A2 | Pure-Python request/response normalization tests should be written before TD worker integration. | Recommended Implementation Sequence | Test sequence could be adjusted if TD-only development is required. |
| A3 | FPS stalls and mismatched request ids are useful warning signs. | Common Pitfalls | Verification might need TD-specific instrumentation instead. |
| A4 | Stale async results can overwrite newer requests unless request ids are checked. | Common Pitfalls | If the router serializes requests and disallows overlap, this risk is reduced. |
| A5 | Ollama daemon/model availability is runtime state that should be handled as recoverable error output. | Common Pitfalls | If installer automation becomes Phase 1 scope, handling may move earlier. |

## Open Questions (RESOLVED)

1. **Which exact TouchDesigner build will implementation target?**
   - What we know: Derivative docs say Thread Manager exists in TouchDesigner 2023.31500+. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
   - What's unclear: The installed TD build was not probed from this shell session. [VERIFIED: local environment probe]
   - Resolution: Plan 01 now includes a blocking TD runtime checkpoint before implementation tasks. Execution must verify the installed TD build, embedded Python version, Thread Manager availability, and extension reload behavior. If Thread Manager is unavailable, execution must document the fallback path before continuing. [ASSUMED]

2. **Should Phase 1 install `httpx` or use a no-install fallback?**
   - What we know: `httpx` is officially documented and PyPI latest is `0.28.1`; GSD seam flags it SUS only due to unknown downloads. [CITED: https://www.python-httpx.org/quickstart] [VERIFIED: PyPI]
   - What's unclear: Whether the user wants external dependency setup before Phase 4 packaging. [VERIFIED: .planning/ROADMAP.md]
   - Resolution: Plan 02 keeps this as an intentional blocking human checkpoint. If `httpx==0.28.1` is approved, execution may use it in the external Python environment. If not approved, execution must keep a stdlib `urllib.request` fallback active for Phase 1 and defer dependency hardening to Phase 4. [ASSUMED]

3. **How should callback target be represented in TD?**
   - What we know: Context prefers callback DAT/operator target, with room for operator path plus method name. [VERIFIED: .planning/phases/01-async-router-proof/01-CONTEXT.md]
   - What's unclear: Which convention feels best once implemented in TD. [ASSUMED]
   - Resolution: Use a `Callbacktarget` OP parameter plus optional `Callbackmethod` string defaulting to `onRouterResult(payload)`. If the target is a DAT callback script, the helper should call/write a structured payload there; if the target is an operator extension, invoke the configured method during TD-side result handoff only. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Pure-Python tests and dependency checks | yes | `python` 3.12.0, `py` 3.13.5 | Install/use Python 3.11 matching TD for venv work. [VERIFIED: local environment probe] |
| Node.js | GSD tooling | yes | v22.18.0 | none needed. [VERIFIED: local environment probe] |
| npm | Package/version tooling | yes | 10.9.3 | none needed. [VERIFIED: local environment probe] |
| Ollama CLI | Local demo endpoint | partial | CLI 0.30.11 installed; service not connected | Show recoverable endpoint error; user starts Ollama service/model. [VERIFIED: local environment probe] |
| TouchDesigner | Implementation/runtime verification | not probed from shell | unknown | Planner must add manual/TD-side Wave 0 check. [VERIFIED: local environment probe] |
| `httpx` | HTTP client | yes in shell Python | 0.28.1 installed in shell Python | Use stdlib fallback or external TD-compatible venv setup. [VERIFIED: PyPI] |

**Missing dependencies with no fallback:**
- TouchDesigner runtime availability/version cannot be verified from this shell; implementation requires TD-side confirmation. [VERIFIED: local environment probe]

**Missing dependencies with fallback:**
- Ollama service is not currently connected; fallback is a visible Router error state and/or generic OpenAI-compatible endpoint configuration. [VERIFIED: local environment probe]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None detected; recommend `pytest` for pure-Python payload/error normalization tests. [VERIFIED: codebase grep] |
| Config file | none; no `pyproject.toml` or `pytest.ini` exists. [VERIFIED: codebase grep] |
| Quick run command | `python -m pytest tests/test_router_payloads.py -q` after framework setup. [ASSUMED] |
| Full suite command | `python -m pytest -q` after framework setup. [ASSUMED] |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ROUT-01 | Custom parameter names and defaults exist | TD manual/smoke | Manual TD inspection; optionally exported script assertion | no; Wave 0 gap. [VERIFIED: codebase grep] |
| ROUT-02 | OpenAI-compatible response text is parsed into DAT payload | unit + TD smoke | `python -m pytest tests/test_router_payloads.py::test_parse_chat_text -q` | no; Wave 0 gap. [VERIFIED: codebase grep] |
| ROUT-03 | State transitions idle/running/complete/error normalize correctly | unit | `python -m pytest tests/test_router_payloads.py::test_state_transitions -q` | no; Wave 0 gap. [VERIFIED: codebase grep] |
| ROUT-05 | Pulse, DAT trigger, and retry call central `request()` | TD smoke | Manual TD callback inspection or exported callback script test | no; Wave 0 gap. [VERIFIED: codebase grep] |
| ROUT-06 | Callback target receives structured payload | TD smoke | Manual TD test with callback DAT/operator | no; Wave 0 gap. [VERIFIED: codebase grep] |
| RUNT-01 | Slow request does not freeze frame loop | TD manual/smoke | Manual TD FPS/counter observation | no; Wave 0 gap. [VERIFIED: codebase grep] |
| RUNT-02 | Worker result enters TD through safe handoff | TD smoke | Manual TD status/callback observation | no; Wave 0 gap. [VERIFIED: codebase grep] |
| RUNT-03 | Timeout/unreachable/malformed errors are visible | unit + TD smoke | `python -m pytest tests/test_router_payloads.py::test_error_payloads -q` | no; Wave 0 gap. [VERIFIED: codebase grep] |
| EXMP-01 | DAT prompt to Ollama returns response DAT | TD manual | Manual local Ollama demo | no; Wave 0 gap. [VERIFIED: codebase grep] |
| EXMP-03 | Pulse and table-change triggers both work | TD manual | Manual TD trigger demo | no; Wave 0 gap. [VERIFIED: codebase grep] |
| EXMP-04 | Reset/retry preserve config and update counters | unit + TD smoke | `python -m pytest tests/test_router_payloads.py::test_retry_preserves_request -q` | no; Wave 0 gap. [VERIFIED: codebase grep] |

### Sampling Rate

- **Per task commit:** Run pure-Python tests once they exist: `python -m pytest tests/test_router_payloads.py -q`. [ASSUMED]
- **Per wave merge:** Run `python -m pytest -q` plus TD manual smoke for pulse, DAT trigger, timeout, reset, and retry. [ASSUMED]
- **Phase gate:** Full pure-Python suite green and TD demo evidence captured before `$gsd-verify-work`. [VERIFIED: .planning/config.json]

### Wave 0 Gaps

- [ ] `tests/test_router_payloads.py` - covers request envelope, OpenAI-compatible parse, error normalization, retry state. [VERIFIED: codebase grep]
- [ ] `pytest` setup decision - no test framework config exists. [VERIFIED: codebase grep]
- [ ] TD-side smoke checklist - confirm Thread Manager availability, Python version, output DAT/CHOP updates, and nonblocking slow request. [ASSUMED]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no for Phase 1 | API key persistence is Phase 4; Phase 1 may expose source placeholder only. [VERIFIED: .planning/REQUIREMENTS.md] |
| V3 Session Management | no | No user sessions in Phase 1. [VERIFIED: .planning/ROADMAP.md] |
| V4 Access Control | no | Local TD component has no multi-user authorization boundary in Phase 1. [ASSUMED] |
| V5 Input Validation | yes | Validate URL scheme/timeout/model/prompt presence before worker dispatch; normalize malformed provider response. [CITED: https://www.python-httpx.org/exceptions] |
| V6 Cryptography | no for Phase 1 | Do not hand-roll secret encryption; defer secret storage to Phase 4. [VERIFIED: .planning/REQUIREMENTS.md] |

### Known Threat Patterns for TouchDesigner Local LLM Router

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key saved into `.toe`/`.tox` | Information Disclosure | Do not store API key values in Phase 1; use placeholder/source reference only. [VERIFIED: .planning/PROJECT.md] |
| Callback target executes unintended operator/method | Elevation of Privilege | Require explicit callback target parameter and fixed method/payload convention; never evaluate arbitrary callback text. [ASSUMED] |
| Unbounded timeout or hanging local endpoint | Denial of Service | Require finite timeout and recoverable timeout error payload. [CITED: https://www.python-httpx.org/exceptions] |
| Worker mutates TD objects | Denial of Service / Tampering | Keep TD object access on TD side only. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner] |
| Private path embedded in distributable examples | Information Disclosure / Portability failure | Use relative TD operator paths and document setup assumptions instead of saved local paths. [VERIFIED: .planning/PROJECT.md] |

## Sources

### Primary (MEDIUM confidence)

- Context7 `/websites/python-httpx` - HTTPX quickstart, timeout, and exception handling. [CITED: https://www.python-httpx.org/quickstart]
- Context7 `/python/cpython/v3.11.14` - `asyncio.run_coroutine_threadsafe` and `loop.call_soon_threadsafe`. [CITED: https://docs.python.org/3.11/library/asyncio-task.html]
- Derivative Python docs - TD Python 3.11 family, external package path loading, dependency conflict warning, and Python gotchas. [CITED: https://docs.derivative.ca/Python]
- Derivative Python threading docs - main thread risk, worker object access boundary, Thread Manager availability. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
- Derivative Run Command Examples - callable `run()`, `delayFrames`, `endFrame`, and single-update pattern. [CITED: https://docs.derivative.ca/Run_Command_Examples]
- Ollama OpenAI compatibility docs - `/v1/chat/completions` local OpenAI-compatible endpoint. [CITED: https://docs.ollama.com/openai]

### Secondary (MEDIUM confidence)

- PyPI JSON and `pip index versions httpx` - `httpx` version `0.28.1`, release upload time, requires-python. [VERIFIED: PyPI]
- GSD package-legitimacy seam - `httpx` flagged `SUS` due to unknown downloads. [VERIFIED: package-legitimacy seam]
- Local environment probes - Python, Node, npm, Ollama CLI availability and Ollama service warning. [VERIFIED: local environment probe]

### Tertiary (LOW confidence)

- Assumptions about stdlib fallback, callback method naming, stale-result handling, and exact TD smoke instrumentation. [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - TD/Ollama/HTTPX/Python claims were checked against official docs or registry data, but installed TD runtime was not probed. [CITED: https://docs.derivative.ca/Python]
- Architecture: MEDIUM - TD threading boundary is official, but exact Thread Manager callback implementation should be verified in the target TD build. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]
- Pitfalls: MEDIUM - main-thread blocking and TD object thread boundary are official; stale-result and UX warning signs are implementation assumptions. [CITED: https://docs.derivative.ca/Python_threading_in_TouchDesigner]

**Research date:** 2026-06-30
**Valid until:** 2026-07-30 for TD threading and HTTPX basics; re-check Ollama OpenAI compatibility within 14 days if provider behavior changes during implementation. [ASSUMED]
