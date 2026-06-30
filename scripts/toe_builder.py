"""Generate TouchDesigner .toe files via toeexpand/toecollapse utilities.

CRITICAL FORMAT RULES (TD hangs if violated):
  1. Every .n and .parm file must end with \\n (0x0A) — TD parser needs it
  2. Use LF-only line endings — Python write_text() on Windows adds CRLF
  3. Never write .text with 1 empty row (0-length content) — omit instead
  4. TOC order: .build, .start, .grps, project1.*, project1/ depth-first,
     perform.*, .application last
  5. See CONVENTIONS.md for the full reference

Usage:
    from toe_builder import ToeBuilder, TextDat, Node, Params

    builder = ToeBuilder("demo")
    builder.add_container("base_llm_demo", x=200, y=100, w=400, h=244)
    builder.add_text_dat("prompt_input", text="Hello, LLM!")
    builder.collapse("output.toe")
"""

from __future__ import annotations

import datetime
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ── TOEC build number ──────────────────────────────────────────────
TOUCHDESIGNER_BUILD = "2022.25370"
TEMPLATE_TOE: Optional[Path] = None


def _find_toe_bin() -> Optional[Path]:
    """Locate TouchDesigner bin directory."""
    candidates = [
        Path(f"C:/Program Files/Derivative/TouchDesigner.{TOUCHDESIGNER_BUILD}/bin"),
        Path("C:/Program Files/Derivative/TouchDesigner/bin"),
    ]
    for p in candidates:
        if (p / "toeexpand.exe").is_file():
            return p
    return None


def _find_template_toe() -> Optional[Path]:
    """Find a minimal template .toe file.

    Always uses the system-provided blank project from Samples to ensure
    a clean, unmodified base.
    """
    td_bin = _find_toe_bin()
    if not td_bin:
        return None

    for candidate in [
        td_bin.parent / "Samples" / "Setup" / "Example" / "NewProject.toe",
        td_bin.parent / "Samples" / "Setup" / "Base" / "NewProject.toe",
        td_bin.parent / "Samples" / "Learn" / "PythonExamples.toe",
    ]:
        if candidate.is_file():
            return candidate
    return None


# ── Data structures ────────────────────────────────────────────────


@dataclass
class Node:
    """A TouchDesigner operator."""

    name: str
    optype: str       # "COMP", "DAT", "CHOP", "SOP", "TOP", etc.
    subtype: str      # "base", "text", "null", "count", "constant", "container", etc.
    x: int = 200
    y: int = 100
    w: int = 100
    h: int = 80
    flags: str = "parlanguage 0"
    color: str = "0.55 0.55 0.55"
    children: List[Node] = field(default_factory=list)
    params: Dict[str, str] = field(default_factory=dict)
    parm_types: Dict[str, int] = field(default_factory=dict)
    text_content: Optional[str] = None
    table_content: Optional[List[List[str]]] = None


# ── Expand/collapse helpers ────────────────────────────────────────


def expand_toe(toe_path: Path) -> Path:
    """Expand a .toe file into a directory. Returns the directory path."""
    td_bin = _find_toe_bin()
    if not td_bin:
        raise RuntimeError("TouchDesigner bin not found")

    result = subprocess.run(
        [str(td_bin / "toeexpand.exe"), str(toe_path)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"toeexpand failed: {result.stderr.strip() or result.stdout.strip()}")

    # toecollapse writes output alongside the input
    expanded_dir = toe_path.with_suffix(".toe.dir")
    if not expanded_dir.is_dir():
        raise RuntimeError(f"toeexpand did not create {expanded_dir}")
    return expanded_dir


def collapse_toc(toc_path: Path, output_path: Optional[Path] = None) -> None:
    """Collapse a .toc file back into a .toe file."""
    td_bin = _find_toe_bin()
    if not td_bin:
        raise RuntimeError("TouchDesigner bin not found")

    cmd = [str(td_bin / "toecollapse.exe"), str(toc_path)]
    if output_path:
        cmd.append(str(output_path))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"toecollapse failed: {result.stderr.strip() or result.stdout.strip()}")


# ── File generators ────────────────────────────────────────────────


def encode_text_dat(rows: List[str]) -> bytes:
    """Encode multi-line text into TD's binary cell format.

    Format (reverse-engineered from TD examples):
      "2\\n"                          = row count (always 2 in TNFile format)
      row_length(4 LE)                = total for row header + cell content
      column_count(4) = 1
      field1(4) = 1
      field2(4) = 1
      field3(4) = 1
      content_header(4) = 0x03000002  (= 02 00 00 03 in memory)
      marker(1)                       = varies by content type (0x29 for most scripts)
      text_content(N)                 = raw UTF-8 text
    """
    text = "\n".join(rows)
    text_bytes = text.encode("utf-8")

    buf = bytearray()
    buf.extend(b"2\n")                          # row count
    row_header_size = 4 + 4 + 4 + 4 + 4 + 4 + 1  # total before text
    row_total = row_header_size + len(text_bytes)
    buf.extend(struct.pack("<I", row_total))    # row length
    buf.extend(struct.pack("<I", 1))            # column count
    buf.extend(struct.pack("<I", 1))            # field 1
    buf.extend(struct.pack("<I", 1))            # field 2
    buf.extend(struct.pack("<I", 1))            # field 3
    buf.extend(b"\x02\x00\x00\x03")            # content header (0x03000002 LE)
    buf.extend(b"\x23")                         # marker byte = '#'
    buf.extend(text_bytes)                      # text content

    return bytes(buf)


def encode_table_dat(table: List[List[str]]) -> bytes:
    """Encode a table as TD's binary table format.

    Format: row count + '\\n', col count + '\\n', then cell data.
    Cell data: for each cell, length-prefixed binary.
    """
    num_rows = len(table)
    num_cols = max(len(r) for r in table) if table else 0

    buf = bytearray()
    buf.extend(f"{num_rows}\n".encode("ascii"))
    buf.extend(f"{num_cols}\n".encode("ascii"))

    buffer = bytearray()
    for _ in range(num_rows * num_cols):
        buffer.extend(b"\x00\x00\x00\x00")  # null lengths

    # Write the col-first data
    row_data = bytearray()
    for r in range(num_rows):
        for c in range(num_cols):
            cell = table[r][c] if c < len(table[r]) else ""
            cell_bytes = cell.encode("utf-8")
            flags = struct.pack("<H", 0x0000)
            payload = flags + cell_bytes
            row_data.extend(struct.pack("<I", len(payload)))
            row_data.extend(payload)

    # Prepend row/col count data before row data
    buf.extend(row_data)
    return bytes(buf)


def make_node_n(node: Node, parent_path: str = "") -> str:
    """Generate the .n file content for an operator."""
    type_str = f"{node.optype.upper()}:{node.subtype}"
    lines = [type_str]
    lines.append(f"tile {node.x} {node.y} {node.w} {node.h}")
    # Containers need viewer 1 to show their contents
    if node.optype == "COMP":
        flags = "viewer 1 current on " + node.flags if "viewer" not in node.flags else node.flags
    else:
        flags = node.flags
    lines.append(f"flags =  {flags}")
    lines.append(f"color {node.color}")
    lines.append("end")
    return "\n".join(lines) + "\n"


def make_node_parms(node: Node) -> str:
    """Generate the .parm file content for an operator.

    Uses node.params (name -> str value) as int/float params (type 0).
    Uses node.parm_types (name -> type_code) to override type for specific params.
    """
    if not node.params:
        return "?\n?\n"

    lines = ["?"]
    for name, value in node.params.items():
        ptype = node.parm_types.get(name, 0)
        if ptype == 17:
            lines.append(f'{name} {ptype} "{value}"')
        else:
            lines.append(f"{name} {ptype} {value}")
    lines.append("?")
    return "\n".join(lines) + "\n"


def make_node_network(children: List[Node]) -> str:
    """Generate .network wiring file."""
    lines = ["connections", "end"]
    return "\n".join(lines)


# ── Builder ────────────────────────────────────────────────────────


class ToeBuilder:
    """Build a .toe project from a template, adding operators programmatically."""

    def __init__(self, template_path: Optional[Path] = None):
        td_bin = _find_toe_bin()
        if not td_bin:
            raise RuntimeError(
                "TouchDesigner bin not found. "
                f"Expected at: C:/Program Files/Derivative/TouchDesigner.{TOUCHDESIGNER_BUILD}/bin"
            )
        self._td_bin = td_bin

        # Use the user's template or a system blank
        if template_path is None:
            template_path = _find_template_toe()
        if template_path is None or not template_path.is_file():
            raise RuntimeError(
                "No .toe template found. Provide a template_path or install TouchDesigner."
            )

        self._template_path = template_path.resolve()
        self._template_copy: Optional[Path] = None
        self._work_dir: Optional[Path] = None
        self._expanded_dir: Optional[Path] = None
        self._toc_path: Optional[Path] = None
        self._project_dir_name = "project1"
        self._nodes: List[Node] = []

    def add_node(self, node: Node) -> Node:
        """Add an operator node to the project."""
        self._nodes.append(node)
        return node

    def add_text_dat(self, name: str, text: str = "",
                     parent: Optional[Node] = None,
                     x: int = 0, y: int = 0) -> Node:
        """Add a Text DAT."""
        node = Node(name=name, optype="DAT", subtype="text",
                    x=x, y=y, w=130, h=90, text_content=text)
        if parent:
            parent.children.append(node)
        else:
            self._nodes.append(node)
        return node

    def add_chop_null(self, name: str, parent: Optional[Node] = None,
                      x: int = 0, y: int = 0) -> Node:
        """Add a Null CHOP."""
        node = Node(name=name, optype="CHOP", subtype="null",
                    x=x, y=y, w=100, h=80)
        if parent:
            parent.children.append(node)
        else:
            self._nodes.append(node)
        return node

    def add_container(self, name: str, x: int = 200, y: int = 100,
                      w: int = 400, h: int = 244) -> Node:
        """Add a Base COMP container."""
        node = Node(name=name, optype="COMP", subtype="base",
                    x=x, y=y, w=w, h=h)
        self._nodes.append(node)
        return node

    def _write_node_files(self, base_path: Path, node: Node, parent_prefix: str = "") -> None:
        """Write .n, .parm, and optional data files for a node.

        Children are written into a subdirectory named after the parent node.
        """
        # Write .n file (use write_bytes to preserve LF-only line endings)
        n_content = make_node_n(node)
        (base_path / f"{node.name}.n").write_bytes(n_content.encode("utf-8"))

        # Write .parm file (use write_bytes to preserve LF-only line endings)
        parm_content = make_node_parms(node)
        (base_path / f"{node.name}.parm").write_bytes(parm_content.encode("utf-8"))

        # Write .text file for text DATs (skip if empty — TD creates empty text on its own)
        if node.text_content is not None and node.text_content != "":
            rows = node.text_content.split("\n")
            # TD hangs on 1-row .text files — ensure at least 2 rows
            if len(rows) == 1:
                rows.append("")
            encoded = encode_text_dat(rows)
            (base_path / f"{node.name}.text").write_bytes(encoded)

        # Write .table file for table DATs
        if node.table_content is not None:
            encoded = encode_table_dat(node.table_content)
            (base_path / f"{node.name}.table").write_bytes(encoded)

        # Write children into a subdirectory named after this node
        for child in node.children:
            child_dir = base_path / node.name
            child_dir.mkdir(parents=True, exist_ok=True)
            self._write_node_files(child_dir, child)

    def _write_toc(self, base_path: Path) -> Path:
        """Write the .toc file listing all expanded files."""
        toc_path = self._template_path.with_suffix(".toe.toc")
        if self._work_dir:
            toc_path = self._work_dir.parent / f"{self._work_dir.name}.toc"

        files = []
        for f in sorted(base_path.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(base_path.parent))
                # toecollapse expects paths relative to the expanded dir, forward slashes
                rel = rel.replace("\\", "/")
                # Remove the expanded dir prefix
                expanded_dir_name = base_path.name
                if rel.startswith(expanded_dir_name + "/"):
                    rel = rel[len(expanded_dir_name) + 1:]
                files.append(rel)

        toc_path.write_text("\n".join(files) + "\n", encoding="utf-8")
        return toc_path

    def _expand_template(self) -> Path:
        """Copy template to a writable temp dir and expand it, return expanded dir."""
        # Copy template to writable temp location
        self._template_copy = Path(tempfile.mktemp(suffix=".toe"))
        shutil.copy2(self._template_path, self._template_copy)

        expanded_dir = self._template_copy.with_suffix(".toe.dir")
        if expanded_dir.is_dir():
            return expanded_dir

        # Expand using toeexpand (note: toeexpand may return non-zero on success)
        result = subprocess.run(
            [str(self._td_bin / "toeexpand.exe"), str(self._template_copy)],
            capture_output=True, text=True, timeout=30,
        )
        if not expanded_dir.is_dir():
            raise RuntimeError(
                f"toeexpand failed for {self._template_copy}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return expanded_dir

    def build(self, output_path: str) -> Path:
        """Build the .toe file at the given path."""
        output = Path(output_path).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)

        # Expand template
        template_dir = self._expand_template()

        # Create work directory from template
        self._work_dir = Path(tempfile.mkdtemp(prefix="toe_build_"))
        self._expanded_dir = self._work_dir / f"{output.stem}.toe.dir"

        # Copy template files to work dir
        shutil.copytree(template_dir, self._expanded_dir, symlinks=True)

        # Update .build file to match installed TD version
        build_path = self._expanded_dir / ".build"
        now = datetime.datetime.now()
        build_path.write_bytes(
            f"version 099\n"
            f"build {TOUCHDESIGNER_BUILD}\n"
            f"time {now.strftime('%a %b %d %H:%M:%S %Y')}\n"
            f"osname Windows\n"
            f"osversion 10\n".encode("ascii")
        )

        # Clean existing operators from project directory, then write our nodes
        project_dir = self._expanded_dir / self._project_dir_name
        if project_dir.is_dir():
            shutil.rmtree(project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

        for node in self._nodes:
            self._write_node_files(project_dir, node)

        # Generate TOC with correct order: root files, project1/ children, .application last
        toc_lines = []
        # Root files in template-canonical order (.build, .start, .grps, then project1.*)
        for name in [".build", ".start", ".grps", "project1.n", "project1.parm", "project1.panel"]:
            if (self._expanded_dir / name).is_file():
                toc_lines.append(name)
        # project1/ children — sort by depth first (parents before children),
        # then alphabetically within each depth level
        project_dir = self._expanded_dir / "project1"
        if project_dir.is_dir():
            files = [f for f in project_dir.rglob("*") if f.is_file()]
            files.sort(key=lambda p: (len(p.relative_to(project_dir).parts), str(p)))
            for f in files:
                rel = "project1/" + str(f.relative_to(project_dir)).replace("\\", "/")
                toc_lines.append(rel)
        # Perform/window files come after project1 content
        for name in ["perform.n", "perform.parm"]:
            if (self._expanded_dir / name).is_file():
                toc_lines.append(name)
        # Application last
        if (self._expanded_dir / ".application").is_file():
            toc_lines.append(".application")

        self._toc_path = self._work_dir / f"{output.stem}.toe.toc"
        self._toc_path.write_bytes(("\n".join(toc_lines) + "\n").encode("ascii"))

        # Collapse to .toe (toecollapse only takes the .toc file, outputs alongside it)
        result = subprocess.run(
            [str(self._td_bin / "toecollapse.exe"), str(self._toc_path)],
            capture_output=True, text=True, timeout=60,
        )

        # The output .toe will be in the same dir as the .toc file, with .toe extension
        source_toe = self._toc_path.with_suffix("")
        if source_toe.is_file():
            shutil.move(str(source_toe), str(output))
        else:
            # toecollapse may have created a .bkpx backup; find the actual output
            candidates = sorted(self._toc_path.parent.glob("*.toe*"))
            found = False
            for c in candidates:
                if c.is_file() and ".bkp" not in c.suffix:
                    shutil.move(str(c), str(output))
                    found = True
                    break
            if not found:
                raise RuntimeError(
                    f"toecollapse produced no output: {result.stderr.strip() or result.stdout.strip()}"
                )

        # Cleanup template copy
        if self._template_copy and self._template_copy.is_file():
            self._template_copy.unlink()
        template_dir = self._template_copy.with_suffix(".toe.dir") if self._template_copy else None
        if template_dir and template_dir.is_dir():
            shutil.rmtree(template_dir)
        toc_path = self._template_copy.with_suffix(".toe.toc") if self._template_copy else None
        if toc_path and toc_path.is_file():
            toc_path.unlink()

        return output

    def _write_minimal_template(self, expanded_dir: Path) -> None:
        """Write a minimal working template if none exists."""
        (expanded_dir / ".build").write_text(
            f"version 099\nbuild {TOUCHDESIGNER_BUILD}\ntime Mon Jan 1 00:00:00 2024\nosname Windows\nosversion 10\n",
            encoding="utf-8",
        )
        (expanded_dir / ".application").write_text(
            "desk -c * \ndesk -n pane1 *\ndesk -p /project1 pane1\ndesk -t neteditor pane1\ndesk -k 0 pane1\n"
            "neteditor -c 0 -e 0 -G 0.75 -o 0 -r 1 -P 0.8 -s 0 -w 0 -x 0 -t 1 -d 1 -g 0 -p pane1\n"
            "browser on\n"
            "winplacement ontop=0 mode=auto posx=0 posy=0 sizex=1024 sizey=768 enable=1 perform.path=/perform perform.start=0\n",
            encoding="utf-8",
        )
        (expanded_dir / ".root").write_text("end\n", encoding="utf-8")
        (expanded_dir / ".grps").write_text("")
        (expanded_dir / ".parm").write_text("")
        (expanded_dir / ".start").write_text("0")

        # Minimal project1 root
        proj = expanded_dir / "project1"
        proj.mkdir(exist_ok=True)
        (proj.with_suffix(".n")).write_text(
            "COMP:container\ntile 200 100 400 244\nflags =  parlanguage 0\ncolor 0.56 0.56 0.56\nend\n",
            encoding="utf-8",
        )
        (proj.with_suffix(".parm")).write_text("?\nw 0 1280\nh 0 720\n?\n", encoding="utf-8")

        # Minimal perform
        perf = expanded_dir / "perform.n"
        perf.write_text(
            "COMP:container\ntile 200 100 400 244\nflags =  parlanguage 0\ncolor 0.56 0.56 0.56\nend\n",
            encoding="utf-8",
        )
        (expanded_dir / "perform.parm").write_text("?\n?\n", encoding="utf-8")

        # Minimal local
        (expanded_dir / "local.n").write_text(
            "COMP:container\ntile 200 100 400 244\nflags =  parlanguage 0\ncolor 0.56 0.56 0.56\nend\n",
            encoding="utf-8",
        )
        (expanded_dir / "local.parm").write_text("?\n?\n", encoding="utf-8")


# ── Script entry point ─────────────────────────────────────────────


def _read_source(path: str) -> str:
    """Read a Python source file from the td_components directory."""
    full = Path(__file__).resolve().parent.parent / "td_components" / "llm_model_router" / path
    if full.is_file():
        return full.read_text(encoding="utf-8")
    return f"# {path} — file not found\n"


def generate_demo(output_path: str = "demo/demo.toe") -> Path:
    """Generate the demo TouchDesigner project with pre-populated source code."""
    builder = ToeBuilder()

    # Main container
    demo = builder.add_container("base_llm_demo", x=200, y=100, w=600, h=400)

    # Router component with Extension configured and source DATs populated
    router = Node(
        name="llm_model_router", optype="COMP", subtype="base",
        x=25, y=25, w=150, h=100,
        params={
            "extension1": 'me.op("ext_code").mod.__dict__["Extension"](me)',
            "extname1": "ModelRouter",
            "promoteextension1": "on",
        },
        parm_types={
            "extension1": 256,
            "extname1": 256,
            "promoteextension1": 256,
        },
        children=[
            Node(name="ext_code", optype="DAT", subtype="text",
                 x=25, y=140, w=130, h=90,
                 text_content="class Extension:\n    def __init__(self, ownerComp):\n        self.ownerComp = ownerComp\nExtension(me)"),
            Node(name="router_http", optype="DAT", subtype="text",
                 x=165, y=140, w=130, h=90,
                 text_content=_read_source("router_http.py")),
            Node(name="router_callbacks", optype="DAT", subtype="text",
                 x=305, y=140, w=130, h=90,
                 text_content=_read_source("router_callbacks.py")),
        ],
    )
    demo.children.append(router)

    # IO DATs (inside demo)
    prompt = Node(name="prompt_input", optype="DAT", subtype="text",
                  x=250, y=25, w=130, h=90,
                  text_content="What is the capital of France?")
    demo.children.append(prompt)

    response_dat = Node(name="response_text", optype="DAT", subtype="text",
                        x=400, y=25, w=130, h=90)
    demo.children.append(response_dat)

    error_dat = Node(name="error_text", optype="DAT", subtype="text",
                     x=250, y=150, w=130, h=90)
    demo.children.append(error_dat)

    status_json = Node(name="status_json", optype="DAT", subtype="text",
                       x=400, y=150, w=130, h=90)
    demo.children.append(status_json)

    callback_target = Node(name="callback_target", optype="DAT", subtype="text",
                           x=25, y=280, w=200, h=90, text_content=_CALLBACK_SOURCE)
    demo.children.append(callback_target)

    callback_payload = Node(name="callback_payload", optype="DAT", subtype="text",
                            x=250, y=280, w=200, h=90)
    demo.children.append(callback_payload)

    # CHOPs
    status_chop = Node(name="status_channels", optype="CHOP", subtype="null",
                       x=475, y=280, w=100, h=80)
    demo.children.append(status_chop)

    frame_counter = Node(name="frame_counter", optype="CHOP", subtype="count",
                         x=475, y=25, w=100, h=80)
    demo.children.append(frame_counter)

    # Startup script DAT (placed at root of base_llm_demo for visibility)
    startup = Node(name="startup", optype="DAT", subtype="text",
                   x=25, y=25, w=300, h=90,
                   text_content=_read_startup())
    demo.children.insert(0, startup)

    # Test runner Execute DAT — runs onStart when file opens
    test_runner = Node(
        name="test_runner", optype="DAT", subtype="execute",
        x=600, y=25, w=300, h=200,
        flags="activate on parlanguage 0 viewer 1",
        text_content=_TEST_RUNNER_SOURCE,
        params={
            "create": "on",
            "language": "python",
            "extension": "languageext",
        },
    )
    demo.children.append(test_runner)

    # Test results output DAT
    test_results = Node(name="test_results", optype="DAT", subtype="text",
                        x=600, y=250, w=300, h=200,
                        flags="viewer 1 parlanguage 0")
    demo.children.append(test_results)

    return builder.build(output_path)


_CALLBACK_SOURCE = '''"""Router demo callbacks."""
def onRouterResult(payload):
    target = op("callback_payload")
    if target is not None:
        target.text = "\\n".join(f"{k}: {v}" for k, v in payload.items())
    return payload
'''


_STARTUP_SOURCE = '''"""TouchDesigner startup for LLM operator demo.
Injects external venv and registers td_components on sys.path.
Place this in a Text DAT named startup with Run ON Start enabled.
"""
import sys
from pathlib import Path

_venv_candidates = [
    Path(__file__).resolve().parent.parent / ".venv",
    Path.home() / ".td-llm-venv",
]
for _venv_root in _venv_candidates:
    if _venv_root.is_dir():
        _site_packages = _venv_root / "Lib" / "site-packages"
        if _site_packages.is_dir() and str(_site_packages) not in sys.path:
            sys.path.insert(0, str(_site_packages))
        break

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from td_components.llm_model_router import router_http  # noqa: F811
except ImportError:
    pass
'''


_TEST_RUNNER_SOURCE = '''# me - this DAT
# Runs on create. Direct execution, no deferral.

def onCreate():
    msg = ""
    msg += "=== Model Router Tests ===\\n"

    try:
        p = parent()
        msg += "PASS: parent=" + str(p) + "\\n"
    except Exception as e:
        msg += "FAIL: parent=" + str(e) + "\\n"

    try:
        r = p.op("llm_model_router")
        msg += "PASS: router=" + str(r) + "\\n"
    except Exception as e:
        msg += "FAIL: router=" + str(e) + "\\n"

    try:
        ext = r.ext.ModelRouter
        s = ext.state
        msg += "PASS: ext state=" + str(s.get("state", "?")) + "\\n"
    except Exception as e:
        msg += "FAIL: ext=" + str(e) + "\\n"

    try:
        sc = p.op("status_channels")
        msg += "PASS: status_channels=" + str(sc) + "\\n"
    except Exception as e:
        msg += "FAIL: status_channels=" + str(e) + "\\n"

    msg += "=== Tests Complete ===\\n"
    
    # Write to test_results directly
    try:
        t = p.op("test_results")
        if t:
            t.text = msg
    except:
        pass
'''

def _read_startup() -> str:
    return _STARTUP_SOURCE


if __name__ == "__main__":
    out = generate_demo()
    print(f"Demo .toe generated: {out}")
    print(f"Size: {out.stat().st_size} bytes")
