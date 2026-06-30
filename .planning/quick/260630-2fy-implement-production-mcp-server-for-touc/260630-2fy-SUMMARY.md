---
phase: quick-260630-2fy
plan: 01
subsystem: mcp-server
tags: [mcp, touchdesigner, fastmcp, companion-process, tool-calling]
requires: []
provides: [mcp-server, td-bridge]
affects: [requirements.txt, check-deps.py]
tech-stack:
  added: [mcp, FastMCP, httpx, http.server]
  patterns: [companion-process, daemon-thread-http, td.run-wrapping]
key-files:
  created:
    - td_mcp_server.py
    - td_components/mcp_bridge/__init__.py
    - td_components/mcp_bridge/MCPBridgeExt.py
    - td_components/mcp_bridge/MCPBridge_config.py
  modified:
    - requirements.txt
    - scripts/check-deps.py
decisions:
  - "Companion-process architecture (separate MCP server + stdlib HTTP bridge inside TD)"
  - "FastMCP v1 stable API (not v2 alpha) for production reliability"
  - "Stdlib-only TD bridge (http.server) — zero additional dependencies inside TD's embedded Python"
  - "httpx sync client in companion server (tool handlers are sync by default in FastMCP)"
metrics:
  duration: ~4m
  completed_date: 2026-06-30
status: complete
---

# Quick 260630-2fy: Implement Production MCP Server for TouchDesigner

Companion-process MCP server exposing 6 TouchDesigner operator capabilities as MCP tools, with a stdlib HTTP bridge inside TD for safe main-thread operator execution.

## Tasks Executed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create companion MCP server | `ab640ac` | `td_mcp_server.py` |
| 2 | Create TD-side MCP bridge | `fe3b4c4` | `td_components/mcp_bridge/__init__.py`, `MCPBridgeExt.py`, `MCPBridge_config.py` |
| 3 | Update dependency config | `53713e4` | `requirements.txt`, `scripts/check-deps.py` |

## What Was Built

### td_mcp_server.py — Companion MCP Server

Standalone Python process running in the external venv, separate from TouchDesigner. Uses `FastMCP` (v1 stable API from `mcp.server.fastmcp`) with streamable-http transport on `127.0.0.1:8765`.

**Registered tools (6):**
- `td_get_parameter` — read operator parameter values via bridge
- `td_get_dat_text` — read full text from Text or Table DATs
- `td_pulse_trigger` — fire pulse parameters on TD operators
- `td_list_network_children` — enumerate child operators in a network
- `td_set_parameter` — set operator parameter values with coercion
- `td_read_chop_channel` — read sample values from CHOP channels

Each tool calls the TD bridge over `httpx` (sync client, 5s timeout) and returns structured JSON. Bridge connectivity errors return user-friendly error dicts instead of crashing the server.

### td_components/mcp_bridge/ — TD-Side Bridge Extension

Three-file package intended to be loaded as a TD COMP extension:

- **`MCPBridge_config.py`** — constants: `BRIDGE_HOST=127.0.0.1`, `BRIDGE_PORT=9876`, route-to-handler mapping
- **`MCPBridgeExt.py`** — `MCPBridge` class managing a daemon-thread `http.server.HTTPServer`, with 6 handler methods that each use `td.run()` for safe main-thread TD API access
- **`__init__.py`** — package docstring

The bridge uses the same `td.run()` pattern as `ModelRouterExt` (`_run_on_main` with `threading.Event` timeout). The `_BridgeRequestHandler` dispatches `/td/{route_name}?params` to handler methods, returning JSON with appropriate HTTP status codes.

### Dependency Updates

- **`requirements.txt`**: `pydantic>=2.5` → `>=2.11`, `pydantic-settings>=2.1` → `>=2.5.2`, added `mcp>=1.27,<2`
- **`check-deps.py`**: Added `("mcp", "1.27")` and `("pydantic", "2.11")` to the dependency checks list

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All 6 tools have complete implementations routed through the bridge, and all 6 bridge handlers implement full `td.op()` calls. No mock data, no placeholder handlers.

## Threat Flags

None. All threat model mitigations from the plan were implemented:
- **T-quick-01 (tampering)**: Bridge coerces values (float/int/str) and validates operator_path
- **T-quick-02 (info disclosure)**: Bridge binds to 127.0.0.1 only
- **T-quick-05 (elevation)**: `td_execute_script` deliberately excluded

## Verification Results

| Check | Result |
|-------|--------|
| `td_mcp_server.py` AST parse | PASS |
| `td_mcp_server.py` py_compile | PASS |
| `MCPBridge_config.py` py_compile | PASS |
| `MCPBridgeExt.py` py_compile | PASS |
| All bridge files AST parse (utf-8) | PASS |
| `requirements.txt` mcp present | PASS |
| `requirements.txt` pydantic bumped | PASS |
| `check-deps.py` AST parse | PASS |
| `check-deps.py` mcp in checks list | PASS |

## Self-Check: PASSED

- `td_mcp_server.py` exists and compiles
- `td_components/mcp_bridge/__init__.py` exists
- `td_components/mcp_bridge/MCPBridgeExt.py` exists and compiles
- `td_components/mcp_bridge/MCPBridge_config.py` exists and compiles
- `requirements.txt` contains `mcp>=1.27,<2`, `pydantic>=2.11,<3`, `pydantic-settings>=2.5.2,<3`
- `scripts/check-deps.py` contains `("mcp", "1.27")` and `("pydantic", "2.11")`
- All 3 commits verified in git log: `ab640ac`, `fe3b4c4`, `53713e4`
