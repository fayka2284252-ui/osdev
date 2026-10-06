from __future__ import annotations
import io
import shutil
import urllib.request
import zipfile
from pathlib import Path

from rich.console import Console

from .paths import TOOLS_DIR

console = Console()

NASM_VERSION = "2.16.03"
NASM_URL = (
    f"https://www.nasm.us/pub/nasm/releasebuilds/"
    f"{NASM_VERSION}/win64/nasm-{NASM_VERSION}-win64.zip"
)


def install_nasm(force: bool = False) -> Path:
    target = TOOLS_DIR / "nasm" / NASM_VERSION
    exe = target / "nasm.exe"

    if exe.exists() and not force:
        console.print(f"[green]NASM {NASM_VERSION} уже установлен:[/green] {exe}")
        return exe

    target.mkdir(parents=True, exist_ok=True)
    console.print(f"Скачиваю NASM {NASM_VERSION}...")

    try:
        with urllib.request.urlopen(NASM_URL, timeout=120) as r:
            data = r.read()
    except Exception as e:
        console.print(f"[red]Не удалось скачать:[/red] {e}")
        raise

    console.print(f"  получено {len(data) // 1024} KiB, распаковываю...")

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.namelist():
            name = Path(member).name
            if name in {"nasm.exe", "ndisasm.exe"} or name.lower().endswith(".dll"):
                with z.open(member) as src, open(target / name, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    if not exe.exists():
        raise RuntimeError("nasm.exe не найден внутри архива")

    console.print(f"[green]Готово:[/green] {exe}")
    return exe


ZIG_VERSION = "0.13.0"
ZIG_URL = (
    f"https://ziglang.org/download/{ZIG_VERSION}/"
    f"zig-windows-x86_64-{ZIG_VERSION}.zip"
)


def install_zig(force: bool = False) -> Path:
    target = TOOLS_DIR / "zig" / ZIG_VERSION
    exe = target / "zig.exe"

    if exe.exists() and not force:
        console.print(f"[green]Zig {ZIG_VERSION} уже установлен:[/green] {exe}")
        return exe

    target.mkdir(parents=True, exist_ok=True)
    console.print(f"Скачиваю Zig {ZIG_VERSION} (~80 MiB)...")

    try:
        with urllib.request.urlopen(ZIG_URL, timeout=300) as r:
            data = r.read()
    except Exception as e:
        console.print(f"[red]Не удалось скачать:[/red] {e}")
        raise

    console.print(f"  получено {len(data) // (1024 * 1024)} MiB, распаковываю...")

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for member in z.namelist():
            rel = Path(member)
            if len(rel.parts) < 2:
                continue
            # внутри zip всё лежит в zig-windows-x86_64-0.13.0/...
            rel_to_zig = Path(*rel.parts[1:])
            dst = target / rel_to_zig
            if member.endswith("/"):
                dst.mkdir(parents=True, exist_ok=True)
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(dst, "wb") as out:
                shutil.copyfileobj(src, out)

    if not exe.exists():
        raise RuntimeError("zig.exe не найден внутри архива")

    console.print(f"[green]Готово:[/green] {exe}")
    return exe