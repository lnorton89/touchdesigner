"""
TouchDesigner network builder for the LLM operator demo.

Place this in a Text DAT named `build_network` and run it to auto-construct
the demo network layout. It creates operators relative to the current network
location, so run it from the root level of your project.

Usage inside TD:
    1. Create a Text DAT anywhere in your project.
    2. Copy this script into the DAT.
    3. Click the DAT's "Run Script" button (or pulse the DAT's Execute pulse).

The script creates:

    + Root COMP (base_llm_demo) containing:
        - llm_model_router  (Base COMP with ModelRouter extension)
        - prompt_input      (Text DAT)
        - response_text     (Text DAT)
        - status_json       (Text DAT)
        - error_text        (Text DAT)
        - status_channels   (CHOP)
        - callback_target   (Text DAT with demo_callbacks module)
        - callback_payload  (Text DAT)
        - frame_counter     (Constant CHOP or Counter)
        - startup           (Text DAT for project startup)

    All operators are created with relative names. The demo is self-contained
    inside the base_llm_demo container and can be exported as a .tox.

    Requires: router scripts (source_router_http, source_router_ext,
    source_router_callbacks) to exist inside the container or be importable.
"""

from __future__ import annotations


def build(parent: object = None) -> object:
    """Construct the demo LLM network under the given parent (or current network).

    Args:
        parent: Parent COMP or network. If None, uses the current network
                implied by `me.parent()` in TD context.

    Returns:
        The root container COMP (base_llm_demo).
    """
    op = getattr(parent or me, "create", None)  # noqa: F821 — 'me' in TD context
    if not op:
        # Fallback for standalone testing — create nothing, return placeholder
        return None

    # Root container
    root = op(
        "base_llm_demo",
        "COMP",
        "Base",
    )

    op = root.create

    # ── Router component ────────────────────────────────────────
    router = op("llm_model_router", "COMP", "Base")
    _set_par(router, "Extension", "source_router_ext.ModelRouter")
    _set_par(router, "Enablemyclass", True)
    _set_par(router, "Language", "Python")
    _set_par_defs(router)

    # ── Source DATs ─────────────────────────────────────────────
    _source_dat(op, "source_router_http", "td_components.llm_model_router.router_http")
    _source_dat(op, "source_router_ext", "td_components.llm_model_router.ModelRouterExt")
    _source_dat(
        op, "source_router_callbacks", "td_components.llm_model_router.router_callbacks"
    )

    # ── IO DATs ─────────────────────────────────────────────────
    op("prompt_input", "DAT", "Text")
    _set_text(op("prompt_input", "DAT", "Text"), "Type your prompt here...")

    op("response_text", "DAT", "Text")
    _set_par(op("response_text", "DAT", "Text"), "Text", "")

    op("status_json", "DAT", "Text")
    _set_par(op("status_json", "DAT", "Text"), "Text", "")

    op("error_text", "DAT", "Text")
    _set_par(op("error_text", "DAT", "Text"), "Text", "")

    output_chop = op("status_channels", "CHOP", "null")

    # ── Callback target ──────────────────────────────────────────
    cb = op("callback_target", "DAT", "Text")
    _set_text(cb, callback_source())

    op("callback_payload", "DAT", "Text")
    _set_par(op("callback_payload", "DAT", "Text"), "Text", "")

    # ── Frame counter ────────────────────────────────────────────
    op("frame_counter", "CHOP", "count")

    # ── Startup script ──────────────────────────────────────────
    startup = op("startup", "DAT", "Text")

    # ── Wire router parameters ──────────────────────────────────
    _set_par(router, "Provider", 0)  # openai_compatible
    _set_par(router, "Baseurl", "http://localhost:11434/v1")
    _set_par(router, "Model", "llama3.2")
    _set_par(router, "Timeout", 30)
    _set_par(router, "Promptdat", root.path + "/prompt_input")
    _set_par(router, "Callbacktarget", root.path + "/callback_target")
    _set_par(router, "Callbackmethod", "onRouterResult")
    _set_par(router, "Apikeysource", "LLM_API_KEY")

    return root


def _set_par(comp: object, name: str, value: object) -> None:
    """Set a parameter value on a COMP if the parameter exists."""
    par = getattr(getattr(comp, "par", None), name, None)
    if par is not None:
        par.val = value


def _set_text(dat: object, text: str) -> None:
    """Set the text content of a Text DAT."""
    if hasattr(dat, "text"):
        dat.text = text


def _set_par_defs(router: object) -> None:
    """Configure custom parameters for the router COMP."""


def callback_source() -> str:
    """Return the Python source for the callback target DAT."""
    return '''"""Router demo callbacks — paste demo/callbacks.py here."""\n
def onRouterResult(payload):
    target = op("callback_payload")
    if target is not None:
        target.text = "\\n".join(
            f"{k}: {v}" for k, v in payload.items()
        )
    return payload
'''


def _source_dat(create_fn: object, name: str, module_path: str) -> object:
    """Create a Text DAT with source from a Python module."""
    dat = create_fn(name, "DAT", "Text")
    try:
        import importlib
        mod = importlib.import_module(module_path)
        src = getattr(mod, "__source__", None) or getattr(
            mod, "__doc__", f"# {module_path}\n"
        )
        if hasattr(dat, "text"):
            dat.text = src
    except ImportError:
        if hasattr(dat, "text"):
            dat.text = f"# {module_path} — could not load at build time\n"
    return dat
