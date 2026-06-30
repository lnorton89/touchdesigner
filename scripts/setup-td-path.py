"""
TouchDesigner startup path injection script.

Run this inside TD via execute DAT or startup script to add the external
virtual environment's site-packages to sys.path before importing toolkit modules.

Usage:
    python scripts/setup-td-path.py -VenvPath C:/path/to/.venv

Or in TD as a startup Text DAT:
    import sys
    sys.path.insert(0, r'C:\path\to\.venv\Lib\site-packages')
    import td_components.llm_model_router.router_http

The script auto-detects the venv path relative to the project root when
no explicit path is given.
"""

import argparse
import sys
from pathlib import Path


def find_venv_paths(venv_root: Path) -> list[Path]:
    """Return site-packages directories for the given venv root."""
    if not venv_root.exists():
        return []

    candidates = [
        venv_root / "Lib" / "site-packages",          # Windows
        venv_root / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",  # macOS/Linux
    ]
    return [p for p in candidates if p.is_dir()]


def resolve_venv() -> Path:
    """Walk up from this script's location to find .venv."""
    here = Path(__file__).resolve().parent
    for parent in [here, here.parent, here.parent.parent]:
        candidate = parent / ".venv"
        if candidate.is_dir():
            return candidate
    return here.parent / ".venv"


def main():
    parser = argparse.ArgumentParser(description="Add venv site-packages to sys.path for TD")
    parser.add_argument(
        "-VenvPath",
        default=None,
        help="Path to the virtual environment root (default: auto-detect .venv)",
    )
    args = parser.parse_args()

    if args.VenvPath:
        venv_root = Path(args.VenvPath).resolve()
    else:
        venv_root = resolve_venv()

    paths = find_venv_paths(venv_root)
    if not paths:
        print(f"WARNING: No site-packages found at {venv_root}", file=sys.stderr)
        print("Run scripts/bootstrap-venv.ps1 first.", file=sys.stderr)
        return 1

    for p in paths:
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)
            print(f"Added: {sp}")
        else:
            print(f"Already on path: {sp}")

    print(f"Venv active: {venv_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
