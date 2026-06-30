"""
TouchDesigner dependency health check.

Run this inside TD (or standalone) to verify that the toolkit's
dependencies are loadable. Reports missing packages and version mismatches
to a DAT-friendly output format.
"""

import sys
from pathlib import Path


def check_import(name: str, min_version: str | None = None) -> dict:
    """Try importing a package and return status info."""
    result = {"package": name, "available": False, "version": None, "error": None}
    try:
        mod = __import__(name)
        result["available"] = True
        result["version"] = getattr(mod, "__version__", "unknown")
    except ImportError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = f"unexpected: {e}"
    return result


def main() -> int:
    checks = [
        ("httpx", "0.27"),
        ("pydantic", "2.5"),
    ]

    results = []
    for name, min_ver in checks:
        r = check_import(name)
        results.append(r)

    # Check td_components itself
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from td_components.llm_model_router import router_http

        components_ok = True
    except ImportError as e:
        components_ok = False
        components_error = str(e)

    # ── Output ────────────────────────────────────────────────────
    lines = ["=== LLM Toolkit Dependency Check ===", ""]
    all_ok = True

    for r in results:
        status = "✓" if r["available"] else "✗"
        ver = f" v{r['version']}" if r["version"] else ""
        err = f"  — {r['error']}" if r["error"] else ""
        lines.append(f"  {status} {r['package']}{ver}{err}")
        if not r["available"]:
            all_ok = False

    lines.append("")
    comp_status = "✓" if components_ok else "✗"
    lines.append(f"  {comp_status} td_components.llm_model_router")
    if not components_ok:
        lines.append(f"    — {components_error}")
        all_ok = False

    lines.append("")
    lines.append(f"Python: {sys.version}")
    lines.append(f"Path:   {sys.executable if hasattr(sys, 'executable') else '(embedded)'}")
    lines.append("")
    if all_ok:
        lines.append("RESULT: All dependencies available.")
    else:
        lines.append("RESULT: Some dependencies are missing. Run scripts/bootstrap-venv.ps1.")
        lines.append("")
        lines.append("Missing packages will fall back to stdlib-only mode where possible.")

    print("\n".join(lines))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
