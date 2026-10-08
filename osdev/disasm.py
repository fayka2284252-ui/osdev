from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

from .build import find_tool, load_config

console = Console()


def _find_objdump() -> str | None:
    """objdump из PATH или из mingw-w64."""
    p = shutil.which("objdump")
    if p:
        return p
    for candidate in (
        r"C:\mingw64\bin\objdump.exe",
        r"C:\msys64\mingw64\bin\objdump.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def disassemble(
    project_dir: Path,
    boot_only: bool = False,
    func: str | None = None,
    out_path: Path | None = None,
) -> Path:
    cfg = load_config(project_dir)
    boot = cfg["project"].get("boot", "mbr")
    build_dir = project_dir / "build"

    # --- boot.bin (только MBR, 16-bit) ---
    if boot_only:
        if boot != "mbr":
            raise RuntimeError('--boot доступен только при boot = "mbr"')
        boot_bin = build_dir / "boot.bin"
        if not boot_bin.exists():
            raise FileNotFoundError(f"Не найден {boot_bin}. Сначала: osdev build")
        ndisasm = find_tool("ndisasm")
        out = out_path or (build_dir / "boot.dis")
        args = [ndisasm, "-b", "16", "-o", "0x7C00", str(boot_bin)]
        console.print(f"[dim]$ {' '.join(args)}[/dim]")
        r = subprocess.run(args, capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"ndisasm вернул {r.returncode}: {r.stderr}")
        out.write_text(r.stdout, encoding="utf-8")
        console.print(f"[green]{out}[/green] ({len(r.stdout.splitlines())} строк)")
        return out

    # --- kernel ---
    kernel_elf = build_dir / "kernel.elf"
    kernel_bin = build_dir / "kernel.bin"
    objdump = _find_objdump()

    # Приоритет: objdump + ELF (символы, AT&T или Intel)
    if objdump and kernel_elf.exists():
        out = out_path or (build_dir / "kernel.dis")
        args = [objdump, "-d", "-M", "intel"]
        if func:
            args += [f"--disassemble={func}"]
        args += [str(kernel_elf)]
        console.print(f"[dim]$ {' '.join(args)}[/dim]")
        r = subprocess.run(args, capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"objdump вернул {r.returncode}: {r.stderr}")
        out.write_text(r.stdout, encoding="utf-8")
        console.print(f"[green]{out}[/green] ({len(r.stdout.splitlines())} строк)")
        return out

    # Fallback: ndisasm + плоский kernel.bin
    if kernel_bin.exists():
        ndisasm = find_tool("ndisasm")
        load_addr = "0x10000" if boot == "mbr" else "0x100000"
        out = out_path or (build_dir / "kernel.dis")
        args = [ndisasm, "-b", "32", "-o", load_addr, str(kernel_bin)]
        console.print(f"[dim]$ {' '.join(args)}[/dim]")
        r = subprocess.run(args, capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            raise RuntimeError(f"ndisasm вернул {r.returncode}: {r.stderr}")
        out.write_text(r.stdout, encoding="utf-8")
        console.print(f"[green]{out}[/green] ({len(r.stdout.splitlines())} строк)")
        return out

    raise FileNotFoundError(
        f"Нет ни {kernel_elf}, ни {kernel_bin}. Сначала: osdev build"
    )