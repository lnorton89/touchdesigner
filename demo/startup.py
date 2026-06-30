"""
TouchDesigner startup script for LLM operator demo project.

Place this in a Text DAT named `startup` and set it to execute on project load
(run ON Start in the DAT's Execute page). It:

1. Injects the external venv site-packages into sys.path (if available).
2. Registers the demo callback module as an importable module so TD's
   Parameter Execute and DAT Execute scripts can reference it.
3. Verifies the Model Router extension is loadable.

To use:
  1. Create a Text DAT named `startup` in your project root.
  2. Paste this entire script into it.
  3. In the DAT's Execute page, enable "Run ON Start".
  4. Optionally: place `demo/callbacks.py` in a Text DAT named `demo_callbacks`.
"""

import sys
from pathlib import Path

# ── Inject external venv site-packages ──────────────────────────
_VENV_CANDIDATES = [
    Path(__file__).resolve().parent.parent / ".venv",
    Path.home() / ".td-llm-venv",
]

for _venv_root in _VENV_CANDIDATES:
    if _venv_root.is_dir():
        _site_packages = _venv_root / "Lib" / "site-packages"
        if _site_packages.is_dir() and str(_site_packages) not in sys.path:
            sys.path.insert(0, str(_site_packages))
            print(f"LLM toolkit: loaded venv from {_venv_root}")
        break

# ── Verify core module is importable ────────────────────────────
try:
    from td_components.llm_model_router import router_http
    print(f"LLM toolkit: router_http loaded (v{router_http.__name__})")
except ImportError:
    print(
        "LLM toolkit: td_components.llm_model_router not found. "
        "Ensure the project root is on sys.path."
    )

# ── Register callbacks module ───────────────────────────────────
# This allows TD scripts to `import demo_callbacks` after startup.
try:
    import importlib.util
    _callbacks_path = Path(__file__).resolve().parent / "callbacks.py"
    if _callbacks_path.is_file():
        _spec = importlib.util.spec_from_file_location(
            "demo.callbacks", str(_callbacks_path)
        )
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            sys.modules["demo.callbacks"] = _mod
            _spec.loader.exec_module(_mod)
            print(f"LLM toolkit: demo.callbacks loaded from {_callbacks_path}")
except Exception as e:
    print(f"LLM toolkit: demo.callbacks load warning: {e}")
