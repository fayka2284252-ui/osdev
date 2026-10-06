from __future__ import annotations
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Tool:
    key: str
    name: str
    binary: str
    version_args: list[str]
    required: bool = True
    hint: str = ""


TOOLS: list[Tool] = [
    Tool("zig",   "Zig (cc + ld.lld)", "zig",  ["version"],
         hint="osdev setup скачает автоматически"),
    Tool("nasm",  "NASM",              "nasm", ["-v"],
         hint="osdev setup скачает автоматически"),
    Tool("qemu",  "QEMU (i686)",       "qemu-system-i386", ["--version"],
         hint="winget install SoftwareFreedomConservancy.QEMU"),
    Tool("gdb",   "GDB",               "gdb",  ["--version"],
         required=False,
         hint="нужен только для osdev debug"),
]


def _find_in_osdev_home(binary: str) -> str | None:
    tools = Path.home() / ".osdev" / "tools"
    if not tools.exists():
        return None
    candidates = [binary]
    if sys.platform == "win32" and not binary.lower().endswith(".exe"):
        candidates.append(binary + ".exe")
    for name in candidates:
        for p in tools.rglob(name):
            if p.is_file():
                return str(p)
    return None


def _find_in_known_windows_dirs(binary: str) -> str | None:
    if sys.platform != "win32":
        return None
    name = binary if binary.lower().endswith(".exe") else binary + ".exe"
    roots = [
        Path(r"C:\Program Files\qemu"),
        Path(r"C:\Program Files (x86)\qemu"),
    ]
    for root in roots:
        candidate = root / name
        if candidate.is_file():
            return str(candidate)
    return None
def probe(tool: Tool) -> tuple[bool, str]:
    path = (
        _find_in_osdev_home(tool.binary)
        or _find_in_known_windows_dirs(tool.binary)
        or shutil.which(tool.binary)
    )
    if not path:
        return False, ""
    try:
        out = subprocess.run(
            [path, *tool.version_args],
            capture_output=True, text=True, timeout=5,
        )
        first = (out.stdout or out.stderr).strip().splitlines()
        return True, first[0] if first else ""
    except Exception as e:
        return False, f"ошибка запуска: {e}"