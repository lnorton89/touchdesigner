# MCP Server for TouchDesigner: Feasibility Research

**Date:** 2026-06-30
**Status:** Complete
**Purpose:** Validate that an MCP server exposing TD capabilities is architecturally feasible and compatible with the project's existing dependency and threading strategy.

---

## SDK Compatibility

### Version and Python Support

| Property | Value |
|----------|-------|
| Package | `mcp` (PyPI: modelcontextprotocol/python-sdk) |
| Stable line | v1.x (production-ready, maintenance mode) |
| Alpha line | v2.0.0a3 (pre-release, not selected by default) |
| `requires-python` | `>=3.10` |
| TD 2022 Python | 3.11.x (exact micro depends on TD build) |
| Compatibility | **Confirmed ✓** — Python 3.11 is within the supported range |

The `mcp` package classifiers explicitly list Python 3.10, 3.11, 3.12, 3.13, and 3.14. TD 2022's shipped Python 3.11 is fully in the support window.

### Dependency Tree

The `mcp` package (v1.x stable) installs these transitive dependencies:

| Dependency | MCP Requires | Project Requires | Collision? |
|------------|-------------|------------------|------------|
| `anyio` | `>=4.5` | — | New dep |
| `httpx` | `>=0.27.1,<1.0.0` | `>=0.27,<1` | **Compatible ✓** |
| `httpx-sse` | `>=0.4` | — | New dep |
| `pydantic` | `>=2.11.0,<3.0.0` | `>=2.5,<3` | **Need bump** (2.5→2.11.0 lower bound) |
| `pydantic-settings` | `>=2.5.2` | `>=2.1,<3` | **Need bump** (2.1→2.5.2 lower bound) |
| `starlette` | `>=0.27` | — | New dep |
| `uvicorn` | `>=0.31.1` | — | New dep |
| `sse-starlette` | `>=1.6.1` | — | New dep |
| `jsonschema` | `>=4.20.0` | — | New dep |
| `pyjwt[crypto]` | `>=2.10.1` | — | New dep |
| `python-multipart` | `>=0.0.9` | — | New dep |
| `typing-extensions` | `>=4.9.0` | — | New dep |
| `typing-inspection` | `>=0.4.1` | — | New dep |
| `pywin32` | `>=310` (Windows only) | — | New dep |

### Collision Analysis

1. **httpx**: Both project and MCP constrain `<1`. MCP's lower bound (`0.27.1`) is slightly above the project's (`0.27`). No conflict — pip resolves to the highest compatible version.

2. **pydantic**: The project's lower bound (`2.5`) is below MCP's (`2.11.0`). If a user has pydantic 2.5–2.10 installed alongside mcp, `pip install mcp` will upgrade pydantic to >=2.11.0. The project's `requirements.txt` lower bound should be bumped to `>=2.11.0` to avoid confusion.

3. **pydantic-settings**: Same pattern — project's `>=2.1` below MCP's `>=2.5.2`. Bump needed.

4. **New dependencies** (uvicorn, starlette, sse-starlette, jsonschema, pyjwt, python-multipart, anyio): None conflict with existing project deps. They are server-side dependencies that only matter if the MCP server runs in-process.

**Bottom line:** The SDK is Python 3.11 compatible. Dependencies are compatible with the existing external-venv strategy, with minor lower-bound bumps needed for `pydantic` and `pydantic-settings`.

---

## Transport Analysis

Three hosting patterns were evaluated for running an MCP server alongside TouchDesigner:

### Pattern Comparison

| Criterion | Embedded Thread + HTTP | Companion Process | stdio (Rejected) |
|-----------|----------------------|-------------------|------------------|
| **Transport** | streamable-http on localhost | streamable-http on localhost | stdin/stdout |
| **Process** | Daemon thread inside TD's Python | Standalone Python in external venv | TD's own process |
| **ASGI conflict risk** | **High** — uvicorn event loop vs TD main thread | **None** — separate process, separate event loop | **N/A** — incompatible |
| **Frame interference** | **Medium** — ASGI I/O may contend with TD's frame deadline | **None** — separate process | **N/A** |
| **TD API access** | Direct — `td.op()`, `td.par`, etc. available | Requires IPC bridge (HTTP/socket to TD) | Direct |
| **Crash isolation** | **Poor** — server crash kills TD session | **Good** — server crash leaves TD running | **N/A** |
| **Startup complexity** | Simple — single TD startup script | Moderate — need process lifecycle management | Simple |
| **Deployment** | Everything in one `.tox` | Companion script + `.tox` component | Non-viable |
| **Security boundary** | Weak — MCP tools run in TD process | Strong — separate process, tool calls go through IPC | N/A |
| **Match with existing patterns** | Mirrors ModelRouter threading | Mirrors external-venv philosophy | N/A |

### 1. Embedded Thread + streamable-http (Risky)

The MCP server runs as a daemon thread inside TD's embedded Python interpreter, with uvicorn serving HTTP on localhost.

**How it would work:**
```python
# Inside a TD extension or startup script
def start_mcp_server():
    mcp = MCPServer("TD-MCP-Gateway")
    # register tools using td.op() etc.
    threading.Thread(target=lambda: mcp.run(transport="streamable-http",
                                             host="127.0.0.1", port=8765),
                    daemon=True).start()
```

**Risks:**
- uvicorn/starlette use `asyncio` event loops. TD's `run()` callback doesn't play well with competing event loops. The ASGI server's `await` calls could block or deadlock.
- Even in a daemon thread, uvicorn's I/O may contend with TD's frame deadline (16.6ms at 60fps).
- If the ASGI server crashes, it takes the entire TD session down.
- On Windows, `pywin32` is required — this is the COM automation library and may interact unexpectedly with TD's own COM usage.

**Verdict:** Technically possible but fragile. The ModelRouter already uses daemon threads for HTTP calls, but those are one-shot `urllib` requests, not a persistent ASGI server. Running a full ASGI server inside TD is a much more aggressive integration.

### 2. Companion Process (Recommended)

The MCP server runs as a standalone Python process in the external venv, separate from TouchDesigner entirely. It exposes TD operator capabilities through an HTTP bridge or a lightweight TD-side client component.

**How it would work:**
- A `td_mcp_server.py` script runs in the external venv, started independently of TD.
- The `.tox` component includes a lightweight MCP *client* that connects to the companion server over localhost HTTP.
- When an MCP tool needs TD data (e.g., read a DAT), the companion server calls back to TD through a simple HTTP API exposed by the `.tox` component.
- The `.tox` component uses TD's `webServer DAT` or a minimal HTTP endpoint to receive tool-execution requests.

**Advantages:**
- Complete crash isolation — MCP server can restart without affecting TD.
- No event loop conflict — uvicorn runs in its own process.
- Clean security boundary — MCP tools can't directly mutate TD state; they go through a controlled API.
- Matches the existing external-venv philosophy.
- Enables headless/CICD testing of the MCP server without TD.

**Disadvantages:**
- Two-process coordination adds complexity.
- Need a lifecycle manager (start server before TD, stop on exit).
- TD API calls require a bridge (additional latency, but acceptable for MCP use cases).

### 3. stdio Transport (Rejected)

The MCP stdio transport requires the server process to own stdin/stdout exclusively. TouchDesigner's embedded Python does not provide this:
- In GUI mode, TD owns the process's stdin/stdout for its own console/logger.
- Embedded Python's `sys.stdin` and `sys.stdout` are redirected or unavailable.
- Even if they were available, TD's main loop would conflict with blocking stdin reads.
- MCP clients like Claude Desktop expect to spawn the server process and communicate over its stdin/stdout — TD is not spawnable this way.

**Verdict:** Fundamentally incompatible with TD's execution model. Documented here for completeness and to prevent future exploration of this dead end.

---

## TD Capability Mapping

TouchDesigner operators and concepts can be mapped to MCP primitives as follows:

### Tools (Callable Functions)

| MCP Tool | TD Equivalent | Arguments | Returns |
|----------|--------------|-----------|---------|
| `td_get_parameter` | `op(path).par[name].eval()` | `operator_path: str`, `parameter_name: str` | `{value, type, is_expression}` |
| `td_set_parameter` | `op(path).par[name] = val` | `operator_path: str`, `parameter_name: str`, `value: Any` | `{success, previous_value}` |
| `td_get_dat_text` | `op(path).text` | `operator_path: str` | `str` (full DAT text) |
| `td_get_dat_rows` | `op(path).rows()` | `operator_path: str`, `start: int`, `count: int` | `list[list[str]]` |
| `td_read_chop_channel` | `op(path).chan(name)` | `operator_path: str`, `channel_name: str` | `list[float]` (sample values) |
| `td_pulse_trigger` | `op(path).par[pulse_name].pulse()` | `operator_path: str`, `pulse_name: str` | `{triggered: bool}` |
| `td_list_network_children` | `op(path).children` | `operator_path: str`, `type_filter: str` | `list[{name, type, path}]` |
| `td_cook_operator` | `op(path).cook(force=True)` | `operator_path: str` | `{cook_time_ms, frame}` |
| `td_get_current_frame` | `td.frame` (or `absTime.frame`) | — | `{frame: int, fps: float}` |
| `td_execute_script` | `exec()` in TD context | `script: str` | `{output, error}` (sandboxed) |

### Resources (Readable Data)

| MCP Resource | TD Equivalent | URI Pattern |
|-------------|--------------|-------------|
| Parameter snapshot | All params of an operator | `td://{operator_path}/parameters` |
| DAT content | Text content of any DAT | `td://{operator_path}/text` |
| CHOP data as JSON | All channels + samples | `td://{operator_path}/data` |
| Node graph topology | Full network tree | `td://{root_path}/graph` |
| Current frame/time | `absTime.frame`, `absTime.seconds` | `td://time/current` |
| Project info | `project.name`, `project.folder` | `td://project/info` |

### Prompts (LLM Prompt Templates)

These are secondary to tools and resources but valuable for AI-assisted TD workflows:

| Prompt | Description |
|--------|-------------|
| `td_summarize_network` | "Here is a TD network. Explain what it does and how components connect." |
| `td_debug_operator` | "Operator {name} is {state}. Investigate why and suggest fixes." |
| `td_suggest_operators` | "I want to achieve {goal} in TD. What operators and connections should I use?" |
| `td_explain_error` | "TouchDesigner reported error: {error_text}. What does this mean and how to fix it?" |

### Mapping Priority

1. **Phase 1 (MVP):** `td_get_parameter`, `td_get_dat_text`, `td_pulse_trigger` — simple, low-risk read/trigger operations.
2. **Phase 2:** `td_set_parameter`, `td_read_chop_channel`, `td_list_network_children` — mutation and structured data.
3. **Phase 3:** Resources (parameter snapshots, CHOP data), prompts — data exposure and AI-assisted workflows.

---

## Dependency Strategy

### How `mcp` Fits into the External Venv

The MCP Python SDK integrates cleanly into the project's existing external-venv approach:

```
.venv/
  Lib/site-packages/
    mcp/                      ← new
    mcp.server/               ← new
    anyio/                    ← new
    starlette/                ← new
    uvicorn/                  ← new
    sse_starlette/            ← new
    jsonschema/               ← new
    jwt/                      ← new
    httpx/                    ← already present
    pydantic/                 ← already present (needs version bump)
    pydantic_settings/        ← already present (needs version bump)
```

**Loading in TD:** Same pattern as existing deps — the `setup-td-path.py` script adds `.venv/Lib/site-packages` to `sys.path`. The MCP server code (companion process or embedded) is importable.

### Required Changes to `requirements.txt`

```diff
- pydantic>=2.5,<3
+ pydantic>=2.11,<3
- pydantic-settings>=2.1,<3
+ pydantic-settings>=2.5.2,<3
+ # MCP server support
+ mcp>=1.27,<2
```

The `httpx` constraint (`>=0.27,<1`) is already compatible and needs no change.

### `mcp[cli]` Extra

The `[cli]` extra adds `typer` and `python-dotenv`. It enables the `mcp dev` command for testing servers during development. Not needed for production but useful for local verification:

```bash
pip install "mcp[cli]>=1.27,<2"
```

### Package Legitimacy Audit

The `mcp` package on PyPI is published by Anthropic, PBC. (verified via PyPI author field). It is the official Python SDK for the Model Context Protocol specification, maintained at `github.com/modelcontextprotocol/python-sdk`. The package has:

- High source reputation
- 1044+ code snippets in documentation
- 82.88 benchmark score
- MIT license
- Active maintenance (v1.x stable, v2 alpha)

**Recommendation:** Include `mcp` in the external-venv dependency set once the companion-process architecture is committed to. The package does not need to be loaded inside TD's embedded Python (unless the embedded-thread pattern is pursued, which is not recommended).

---

## Recommendation

### Hosting Pattern: Companion Process

Run the MCP server as a standalone Python process in the external virtual environment, separate from TouchDesigner. The `.tox` component includes a lightweight MCP client that bridges TD operators to the companion server.

### Transport: streamable-http (localhost only)

- Bind to `127.0.0.1` on a configurable port (default: `8765`).
- Use `streamable-http` transport — simpler than SSE, sufficient for local development.
- No external network exposure.
- MCP clients (Claude Desktop, custom CLI) connect to `http://localhost:8765/mcp`.

### Minimum Viable MCP Server

1. **`td_mcp_server.py`** — Standalone script in external venv:
   - `MCPServer` (v2 API) or `FastMCP` (v1 stable API)
   - Tools: `td_get_parameter`, `td_get_dat_text`, `td_pulse_trigger` (mock implementations in initial sketch, real TD calls in production)
   - streamable-http transport on `127.0.0.1:8765`

2. **TD-side bridge** (future phase):
   - A COMP in the `.tox` that connects to the companion server
   - Exposes a simple HTTP API that the companion server calls for TD-native operations
   - Uses TD's `webServer DAT` or a custom threaded HTTP listener (inspired by existing ModelRouter pattern)

3. **Lifecycle management** (future phase):
   - Bootstrap script: start companion server before TD, stop on exit
   - Or: TD startup script spawns the companion process via `subprocess.Popen`

### Phase-Level Integration Plan

The MCP server aligns with Phase 1 (Async Router Proof) concepts and would be a natural Phase 5 addition:

| Phase | MCP Integration Work |
|-------|---------------------|
| **Now (sketch)** | RESEARCH.md + mcp_td_sketch.py — prove the concept compiles and the API is sound |
| **Phase 1 (Router)** | Already complete. The ModelRouter's threaded HTTP pattern establishes precedent for async I/O from TD. |
| **Phase 2 (Agent)** | Agent COMP could become an MCP-aware component — receive MCP tool calls as conversation context. |
| **Phase 3 (Tools)** | The TD tool registry concept directly maps to MCP tool registration. The same tool schemas can serve both TD-native and MCP-external consumers. |
| **Phase 4 (Packaging)** | MCP server included in the `.tox` package. Bootstrap script manages companion process lifecycle. |
| **Phase 5 (MCP Gateway)** | Full MCP server with real TD API calls, comprehensive tool set, resource exposure, and prompt templates. |

### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| ASGI/TD event loop conflict | Avoided entirely by using companion process |
| Two-process coordination complexity | Start simple: HTTP bridge, no persistent connections. Evolve later. |
| TD API access latency | Localhost HTTP is sub-millisecond. MCP tool calls are tens of ms anyway. |
| `pywin32` dependency on Windows | Isolated to companion process. Not loaded in TD's Python interpreter. |
| MCP v2 API instability | Use v1.x stable API (`FastMCP`) for production; sketch uses v2 API for future-proofing. |

### Next Steps

1. ✅ Complete this research document
2. ✅ Create `mcp_td_sketch.py` — minimal MCP server with mock TD tools
3. 🔲 Install `mcp` in external venv and verify the sketch runs
4. 🔲 Connect Claude Desktop or MCP Inspector to validate tool invocation
5. 🔲 Design the TD-side bridge API (Phase 5 plan)
6. 🔲 Implement real TD API calls in tools (Phase 5 execution)
