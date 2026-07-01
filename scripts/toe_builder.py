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
    """Encode multi-line text into TD's .text file format.

    Header (27 bytes fixed):
      "2\\n" + \\x2a\\x00\\x00\\x00 + col_count(4)=1 + field1(4)=1
      + field2(4)=1 + field3(4)=1 + content_hdr(4)=\\x02\\x00\\x00\\x03
      + marker(1)=\\x29
    Then: raw UTF-8 text content to end of file.
    """
    text = "\n".join(rows).encode("utf-8")

    buf = bytearray()
    buf.extend(b"2\n")                      # row count (fixed)
    buf.extend(b"\x2a\x00\x00\x00")         # magic constant 42
    buf.extend(struct.pack("<I", 1))         # column count
    buf.extend(struct.pack("<I", 1))         # field 1
    buf.extend(struct.pack("<I", 1))         # field 2
    buf.extend(struct.pack("<I", 1))         # field 3
    buf.extend(b"\x02\x00\x00\x03")         # content header
    buf.extend(b"\x29")                      # marker
    buf.extend(text)                         # text content
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


def _read_source(path: str, component: str = "llm_model_router") -> str:
    """Read a Python source file from the td_components directory."""
    full = Path(__file__).resolve().parent.parent / "td_components" / component / path
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
        children=[
            Node(name="router_http", optype="DAT", subtype="text",
                 x=165, y=140, w=130, h=90,
                 text_content=_read_source("router_http.py")),
            Node(name="router_callbacks", optype="DAT", subtype="text",
                 x=305, y=140, w=130, h=90,
                 text_content=_read_source("router_callbacks.py")),
        ],
    )
    demo.children.append(router)

    agent = Node(
        name="llm_agent", optype="COMP", subtype="base",
        x=25, y=-125, w=150, h=100,
        children=[
            Node(name="AgentExt", optype="DAT", subtype="text",
                 x=165, y=0, w=130, h=90,
                 text_content=_read_source("AgentExt.py", "llm_agent")),
        ],
    )
    demo.children.append(agent)

    tool_registry = Node(
        name="llm_tool_registry", optype="COMP", subtype="base",
        x=25, y=-375, w=150, h=100,
        children=[
            Node(name="ToolRegistryExt", optype="DAT", subtype="text",
                 x=165, y=0, w=130, h=90,
                 text_content=_read_source("ToolRegistryExt.py", "llm_tool_registry")),
        ],
    )
    demo.children.append(tool_registry)

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

    router_config = Node(name="router_config", optype="DAT", subtype="text",
                         x=25, y=150, w=200, h=90,
                         text_content=_ROUTER_CONFIG_TEXT)
    demo.children.append(router_config)

    agent_config = Node(name="agent_config", optype="DAT", subtype="text",
                        x=25, y=-250, w=220, h=90,
                        text_content=_AGENT_CONFIG_TEXT)
    demo.children.append(agent_config)

    agent_message = Node(name="agent_message", optype="DAT", subtype="text",
                         x=250, y=-250, w=160, h=90,
                         text_content="Say hello from the Agent.")
    demo.children.append(agent_message)

    agent_response = Node(name="agent_response", optype="DAT", subtype="text",
                          x=430, y=-250, w=160, h=90)
    demo.children.append(agent_response)

    agent_status_json = Node(name="agent_status_json", optype="DAT", subtype="text",
                             x=610, y=-250, w=160, h=90)
    demo.children.append(agent_status_json)

    agent_history = Node(name="agent_history", optype="DAT", subtype="text",
                         x=430, y=-125, w=160, h=90)
    demo.children.append(agent_history)

    agent_error = Node(name="agent_error", optype="DAT", subtype="text",
                       x=610, y=-125, w=160, h=90)
    demo.children.append(agent_error)

    agent_response_json = Node(name="agent_response_json", optype="DAT", subtype="text",
                               x=790, y=-250, w=160, h=90)
    demo.children.append(agent_response_json)

    tool_value = Node(name="tool_value", optype="DAT", subtype="text",
                      x=250, y=-375, w=160, h=90,
                      text_content="Tool value not set yet.")
    demo.children.append(tool_value)

    tool_result = Node(name="tool_result", optype="DAT", subtype="text",
                       x=430, y=-375, w=220, h=90)
    demo.children.append(tool_result)

    tool_chop = Node(
        name="tool_chop", optype="CHOP", subtype="constant",
        x=670, y=-375, w=120, h=80,
        params={"name0": "toolvalue", "value0": "0"},
        parm_types={"name0": 17},
    )
    demo.children.append(tool_chop)

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

    demo_process = Node(name="demo_process", optype="DAT", subtype="text",
                        x=970, y=25, w=280, h=180,
                        text_content=_DEMO_PROCESS_TEXT)
    demo.children.append(demo_process)

    node_reference = Node(name="node_reference", optype="DAT", subtype="text",
                          x=970, y=-180, w=360, h=320,
                          text_content=_NODE_REFERENCE_TEXT)
    demo.children.append(node_reference)

    panel_helper = Node(name="demo_panel_helper", optype="DAT", subtype="text",
                        x=970, y=-525, w=360, h=220,
                        text_content=_PANEL_HELPER_SOURCE)
    demo.children.append(panel_helper)

    # Test runner Execute DAT — runs onStart when file opens
    test_runner = Node(
        name="test_runner", optype="DAT", subtype="execute",
        x=600, y=25, w=300, h=200,
        flags="activate on parlanguage 0 viewer 1",
        text_content=_TEST_RUNNER_SOURCE,
        params={
            "start": "on",
            "language": "python",
            "extension": "languageext",
        },
    )
    demo.children.append(test_runner)

    agent_runner = Node(
        name="agent_runner", optype="DAT", subtype="execute",
        x=790, y=-125, w=220, h=120,
        flags="activate on parlanguage 0 viewer 1",
        text_content=_AGENT_RUNNER_SOURCE,
        params={
            "start": "on",
            "language": "python",
            "extension": "languageext",
        },
    )
    demo.children.append(agent_runner)

    # Test results output DAT
    test_results = Node(name="test_results", optype="DAT", subtype="text",
                        x=600, y=250, w=300, h=200,
                        flags="viewer 1 parlanguage 0",
                        text_content=" ")  # non-empty so .text file is created
    demo.children.append(test_results)

    return builder.build(output_path)


_CALLBACK_SOURCE = '''"""Router demo callbacks."""
def onRouterResult(payload):
    target = op("callback_payload")
    if target is not None:
        target.text = "\\n".join(f"{k}: {v}" for k, v in payload.items())
    return payload
'''


_ROUTER_CONFIG_TEXT = '''provider: openai_compatible
base_url: http://localhost:11434/v1
model: llama3.2
timeout: 30
prompt_dat: prompt_input
callback_target: callback_payload
trigger_pulse: Trigger
reset_pulse: Reset
retry_pulse: Retry
status_display: status_json
api_key_source: LLM_API_KEY_PLACEHOLDER
api_key_value_saved: false
'''


_AGENT_CONFIG_TEXT = '''system_prompt: You are a concise TouchDesigner assistant.
message_dat: agent_message
router_path: llm_model_router
output_dat: agent_response
json_output_dat: agent_response_json
error_dat: agent_error
status_dat: agent_status_json
history_dat: agent_history
model_override: optional
base_url_override: optional
'''


_DEMO_PROCESS_TEXT = '''LLM Operator Demo - end-to-end process

1. Start a local OpenAI-compatible endpoint.
   - Ollama: ollama pull llama3.2; ollama serve
   - llama.cpp: scripts/start-llama-server.ps1

2. Open demo/demo.toe.
   startup and test_runner initialize the bridge, router smoke test, and agent smoke test.

3. Router path.
   Edit prompt_input, then use the Router controls or MCP route:
   /td/router_demo_action?action=pulse
   Outputs: response_text, error_text, status_json, callback_payload, status_channels.

4. Agent path.
   Edit agent_message, then use:
   /td/agent_demo_action?action=pulse
   Outputs: agent_response, agent_error, agent_status_json, agent_history, agent_response_json.

5. Tool path.
   Use /td/tool_demo_action?action=list, execute, chop, invalid, model_start, model_collect.
   Outputs: tool_value, tool_chop, tool_result, and agent_history.

6. MCP/live TD path.
   Start the companion server with .venv/Scripts/python.exe td_mcp_server.py.
   Connect an MCP client to http://127.0.0.1:8765/mcp.

7. Nonblocking proof.
   During router or agent requests, frame_counter should keep cooking.
'''


_NODE_REFERENCE_TEXT = '''base_llm_demo node reference

User-facing nodes
- demo_process: end-to-end walkthrough kept inside the .toe.
- node_reference: this node inventory.
- prompt_input: user prompt for direct router requests.
- response_text: latest router response text.
- error_text: latest router error text.
- status_json: full router state snapshot as JSON.
- status_channels: router lifecycle channels for CHOP-driven networks.
- callback_payload: flattened router callback payload for quick inspection.
- agent_message: user message for the conversational Agent.
- agent_response: latest Agent assistant text.
- agent_response_json: raw Agent result payload JSON.
- agent_error: latest Agent error text.
- agent_status_json: full Agent state snapshot.
- agent_history: JSON message history.
- tool_value: Text DAT changed by the set_demo_value tool.
- tool_chop: Constant CHOP changed by the set_demo_chop tool.
- tool_result: latest tool-list or tool-execution result.
- test_results: startup smoke-test log.

Operator components
- llm_model_router: async OpenAI-compatible request router.
- llm_agent: conversation/history wrapper that delegates to the router.
- llm_tool_registry: registry source for TD-callable tool schemas.

Configuration/source nodes
- router_config: readable router defaults used by the demo documentation.
- agent_config: readable agent defaults used by the demo documentation.
- callback_target: onRouterResult callback source.
- startup: sys.path/bootstrap script for TD load.
- demo_panel_helper: best-effort custom parameter installer for base_llm_demo.

Internal smoke-test nodes
- test_runner: starts the TD bridge pump and router smoke path on project load.
- agent_runner: runs the Agent smoke path after startup.
- frame_counter: visual proof that TD keeps cooking during async work.

These internal nodes are intentionally kept because they make the generated
project self-testing. They can be deleted after exporting a clean production tox.
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


_TEST_RUNNER_SOURCE = '''# me
import sys;sys.path.append(r"C:\\Users\\Lawrence\\Documents\\Dev\\touchdesigner")
B = None

def onStart():
    global B
    from td_components.mcp_bridge.MCPBridgeExt import MCPBridge as M
    from td_components.llm_model_router.ModelRouterExt import ModelRouter as R
    p=parent();B=M(td_op=op,td_run=run);B.start();run("args[0]()", pump, delayFrames=1);r=R(p.op("llm_model_router"));p.store("router",r)
    h=p.op("demo_panel_helper")
    if h is not None:
        ns={}
        exec(h.text, ns)
        ns.get("install_demo_panel", lambda *a, **k: None)(p, B)
    i=r.request(prompt=p.op("prompt_input").text,trigger_source="startup",dispatch=False)
    r.apply_result(dict(request_id=i,status="complete",response_text="Router demo ready",error_text=""))
    p.op("test_results").text = "Bridge started\\nRouter smoke complete"
    return

def pump():
    if B: B._drain_pending_calls()
    run("args[0]()", pump, delayFrames=1)
'''


_AGENT_RUNNER_SOURCE = '''# me
import sys;sys.path.append(r"C:\\Users\\Lawrence\\Documents\\Dev\\touchdesigner")

def onStart():
    run("args[0]()", go, delayFrames=2)
    return

def go():
    from td_components.llm_model_router.ModelRouterExt import ModelRouter as R
    from td_components.llm_agent.AgentExt import LLMAgent as A
    p=parent();r=R();a=A(p.op("llm_agent"),r);p.store("agent",a)
    m=p.op("agent_message").text.split("\\n4",1)[0]
    j=a.send(m,dispatch=False)
    a.apply_result(dict(request_id=j,status="complete",response_text="Agent demo ready",error_text=""))
    t=p.op("test_results");t.text=(t.text+"\\nAgent smoke complete").strip()
    return
'''


_PANEL_HELPER_SOURCE = '''"""Best-effort controls for the generated demo component.

TouchDesigner stores custom parameter UI in project internals that are safer to
create with TD's own Python API than to hand-author in expanded .toe files.
test_runner calls install_demo_panel(parent(), bridge) on startup.
"""

_PARAM_SPECS = [
    ("str", "Provider", "Provider", "openai_compatible"),
    ("str", "Baseurl", "Base URL", "http://localhost:11434/v1"),
    ("str", "Model", "Model", "llama3.2"),
    ("float", "Timeout", "Timeout", 30),
    ("str", "Prompt", "Prompt", "What is the capital of France?"),
    ("str", "Agentmessage", "Agent Message", "Say hello from the Agent."),
    ("pulse", "Routerpulse", "Router Pulse", None),
    ("pulse", "Routerretry", "Router Retry", None),
    ("pulse", "Routerreset", "Router Reset", None),
    ("pulse", "Agentpulse", "Agent Pulse", None),
    ("pulse", "Agentclear", "Agent Clear", None),
    ("pulse", "Toollist", "Tool List", None),
    ("pulse", "Toolexecute", "Tool Execute", None),
    ("pulse", "Toolchop", "Tool CHOP", None),
]


def install_demo_panel(base, bridge=None):
    """Add a Custom parameter page to base_llm_demo when the TD API allows it."""
    if base is None or not hasattr(base, "appendCustomPage"):
        return False
    try:
        page = base.appendCustomPage("LLM Demo")
    except Exception:
        return False

    for kind, name, label, default in _PARAM_SPECS:
        if getattr(getattr(base, "par", None), name, None) is not None:
            continue
        try:
            if kind == "pulse":
                page.appendPulse(name, label=label)
            elif kind == "float":
                pars = page.appendFloat(name, label=label)
                pars[0].default = float(default)
                pars[0].val = float(default)
            else:
                pars = page.appendStr(name, label=label)
                pars[0].default = str(default)
                pars[0].val = str(default)
        except Exception:
            pass

    try:
        base.store("demo_panel_bridge", bridge)
    except Exception:
        pass
    return True


def sync_panel_to_demo(base):
    """Copy editable panel values into the demo DATs/config where possible."""
    if base is None:
        return False
    try:
        prompt = base.op("prompt_input")
        if prompt is not None and hasattr(prompt, "text"):
            prompt.text = str(base.par.Prompt.eval())
        message = base.op("agent_message")
        if message is not None and hasattr(message, "text"):
            message.text = str(base.par.Agentmessage.eval())
    except Exception:
        return False
    return True
'''

_TEST_RUNNER_SOURCE = _TEST_RUNNER_SOURCE.rstrip() + "\n#"
_AGENT_RUNNER_SOURCE = _AGENT_RUNNER_SOURCE.rstrip() + "\n#"

def _read_startup() -> str:
    return _STARTUP_SOURCE


if __name__ == "__main__":
    out = generate_demo()
    print(f"Demo .toe generated: {out}")
    print(f"Size: {out.stat().st_size} bytes")
