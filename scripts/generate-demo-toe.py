"""Generate the demo .toe file for the LLM operator project.

Usage:
    python scripts/generate-demo-toe.py

Requires TouchDesigner 2022.25370 to be installed (for toeexpand/toecollapse utilities).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from toe_builder import generate_demo

if __name__ == "__main__":
    output = Path(__file__).resolve().parent.parent / "demo" / "demo.toe"
    result = generate_demo(str(output))
    print(f"Generated: {result}")
    print(f"Size: {result.stat().st_size} bytes")
