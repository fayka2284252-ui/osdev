from __future__ import annotations
import os
import subprocess
import shutil as _shutil
import sys
import tempfile
from pathlib import Path

import typer
from rich.console import Console

from .doctor import run_doctor
from .setup import install_nasm, install_zig
from .build import build as build_project, load_config, find_tool
from .upgrade import run_upgrade
from .disasm import disassemble

# Принудительный UTF-8: на Windows CI консоль в cp1252 и падает на русских буквах
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from importlib.metadata import version as _pkg_version, PackageNotFoundError

try:
    __version__ = _pkg_version("python-osdev")
except PackageNotFoundError:
    __version__ = "unknown"


app = typer.Typer(
    help="OSDev toolkit для Windows — без WSL, без боли.",
    no_args_is_help=True,
)
console = Console()

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"osdev {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False, "--version", "-V",
        callback=_version_callback,
        is_eager=True,
        help="Показать версию и выйти",
    ),
) -> None:
    """OSDev toolkit для Windows — без WSL, без боли."""


@app.command()
def doctor(
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Показать окружение, пути к тулчейну, editable-статус",
    ),
) -> None:
    """Проверить, что установлено в системе."""
    raise typer.Exit(code=run_doctor(verbose=verbose))


@app.command()
def setup(
    nasm: bool = typer.Option(True, "--nasm/--no-nasm", help="Установить NASM"),
    zig: bool = typer.Option(True, "--zig/--no-zig", help="Установить Zig"),
    force: bool = typer.Option(False, "--force", help="Переустановить"),
) -> None:
    """Установить тулчейн."""
    if nasm:
        install_nasm(force=force)
    if zig:
        install_zig(force=force)
    typer.echo("\nГотово. Проверь: osdev doctor")


@app.command()
def new(
    name: str,
    template: str = typer.Option("i686-c-mbr", "--template", "-t"),
) -> None:
    """Создать новый проект ОС."""
    src = TEMPLATES_DIR / template
    if not src.exists():
        typer.echo(f"Шаблон не найден: {src}")
        raise typer.Exit(1)

    dst = Path.cwd() / name
    if dst.exists():
        typer.echo(f"Папка уже существует: {dst}")
        raise typer.Exit(1)

    _shutil.copytree(src, dst)

    toml_path = dst / "osdev.toml"
    if toml_path.exists():
        text = toml_path.read_text(encoding="utf-8").replace("{{name}}", name)
        toml_path.write_text(text, encoding="utf-8")

    typer.echo(f"Создан проект: {dst}")
    typer.echo(f"Дальше: cd {name} && osdev build")


@app.command()
def build() -> None:
    """Собрать образ ОС (ищет osdev.toml в текущей папке)."""
    try:
        out = build_project(Path.cwd())
    except Exception as e:
        console.print(f"[red]Ошибка:[/red] {e}")
        raise typer.Exit(1)
    typer.echo(f"\nГотово: {out}")
    typer.echo("Запусти: osdev run")


@app.command()
def run(
    mem: str = typer.Option("128M", "--mem", "-m", help="Объём RAM"),
    no_build: bool = typer.Option(False, "--no-build", help="Не пересобирать"),
) -> None:
    """Собрать и запустить в QEMU. Учитывает boot = mbr / multiboot / grub."""
    project_dir = Path.cwd()
    cfg = load_config(project_dir)
    boot = cfg["project"].get("boot", "mbr")
    name = cfg["project"]["name"]
    build_cfg = cfg["build"]

    if not no_build:
        build_project(project_dir)

    qemu = find_tool("qemu-system-i386")

    if boot == "mbr":
        output_rel = build_cfg.get("output", f"build/{name}.img")
        img = project_dir / output_rel
        if not img.exists():
            console.print(f"[red]Образ не найден:[/red] {img}")
            raise typer.Exit(1)
        args = [qemu, "-drive", f"format=raw,file={img}", "-m", mem]
    elif boot == "multiboot":
        elf = project_dir / "build" / "kernel.elf"
        if not elf.exists():
            console.print(f"[red]ELF не найден:[/red] {elf}")
            raise typer.Exit(1)
        args = [qemu, "-kernel", str(elf), "-m", mem]
    elif boot == "grub":
        iso = project_dir / "build" / f"{name}.iso"
        if not iso.exists():
            console.print(f"[red]ISO не найден:[/red] {iso}")
            raise typer.Exit(1)
        args = [qemu, "-cdrom", str(iso), "-m", mem]
    else:
        console.print(f"[red]Неизвестный boot = \"{boot}\"[/red]")
        raise typer.Exit(1)

    console.print(f"[green]QEMU[/green]: {qemu}")
    console.print("[dim]Закрой окно QEMU или нажми Ctrl+C для выхода.[/dim]")
    subprocess.run(args)


@app.command()
def debug(
    mem: str = typer.Option("128M", "--mem", "-m", help="Объём RAM"),
    no_build: bool = typer.Option(False, "--no-build", help="Не пересобирать"),
    port: int = typer.Option(1234, "--port", help="Порт GDB-сервера QEMU"),
) -> None:
    """Собрать и запустить QEMU под GDB (пошаговая отладка ядра)."""
    project_dir = Path.cwd()
    cfg = load_config(project_dir)
    boot = cfg["project"].get("boot", "mbr")
    name = cfg["project"]["name"]
    build_cfg = cfg["build"]

    if not no_build:
        build_project(project_dir)

    qemu = find_tool("qemu-system-i386")
    gdb = find_tool("gdb")

    kernel_elf = project_dir / "build" / "kernel.elf"
    if not kernel_elf.exists():
        console.print(f"[red]kernel.elf не найден:[/red] {kernel_elf}")
        raise typer.Exit(1)

    if boot == "mbr":
        output_rel = build_cfg.get("output", f"build/{name}.img")
        img = project_dir / output_rel
        if not img.exists():
            console.print(f"[red]Образ не найден:[/red] {img}")
            raise typer.Exit(1)
        qemu_args = [qemu, "-drive", f"format=raw,file={img}", "-m", mem,
                     "-S", "-gdb", f"tcp::{port}"]
    elif boot == "multiboot":
        qemu_args = [qemu, "-kernel", str(kernel_elf), "-m", mem,
                     "-S", "-gdb", f"tcp::{port}"]
    elif boot == "grub":
        iso = project_dir / "build" / f"{name}.iso"
        if not iso.exists():
            console.print(f"[red]ISO не найден:[/red] {iso}")
            raise typer.Exit(1)
        qemu_args = [qemu, "-cdrom", str(iso), "-m", mem,
                     "-S", "-gdb", f"tcp::{port}"]
    else:
        console.print(f"[red]Неизвестный boot = \"{boot}\"[/red]")
        raise typer.Exit(1)

    console.print(f"[green]QEMU[/green]: {qemu} (GDB :{port}, пауза)")
    qemu_proc = subprocess.Popen(qemu_args)

    entry = "_start" if boot in ("multiboot", "grub") else build_cfg.get("entry", "kernel_main")

    cmds = "\n".join([
        f"target remote localhost:{port}",
        f"symbol-file {kernel_elf.as_posix()}",
        f"break {entry}",
        "continue",
    ]) + "\n"

    fd, gdb_script = tempfile.mkstemp(suffix=".gdb")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(cmds)

    try:
        console.print(f"[green]GDB[/green]: {gdb}")
        console.print("[dim]Команды: c (continue), si (step), info registers, x/10i $pc, q (quit)[/dim]")
        subprocess.run([gdb, "-x", gdb_script, str(kernel_elf)])
    finally:
        try:
            os.unlink(gdb_script)
        except OSError:
            pass
        if qemu_proc.poll() is None:
            qemu_proc.terminate()
            console.print("[dim]QEMU остановлен.[/dim]")


@app.command()
def add(
    filename: str = typer.Argument(..., help="Имя файла (например, vga.c или src/vga.c)"),
) -> None:
    """Добавить файл в [build].sources в osdev.toml."""
    import re

    project_dir = Path.cwd()
    toml_path = project_dir / "osdev.toml"
    if not toml_path.exists():
        console.print(f"[red]osdev.toml не найден в {project_dir}[/red]")
        raise typer.Exit(1)

    if not filename.startswith("src/"):
        rel = f"src/{filename}"
    else:
        rel = filename

    target = project_dir / rel
    if not target.exists():
        console.print(f"[red]Файл не найден:[/red] {target}")
        raise typer.Exit(1)

    text = toml_path.read_text(encoding="utf-8")

    if rel in text:
        console.print(f"[yellow]Файл уже в sources:[/yellow] {rel}")
        return

    pattern = re.compile(r"(sources\s*=\s*\[)([^\]]*)(\])", re.MULTILINE)

    def repl(m: re.Match) -> str:
        inner = m.group(2).strip()
        if inner and not inner.endswith(","):
            inner += ","
        return f'{m.group(1)}{inner} "{rel}"{m.group(3)}'

    new_text, n = pattern.subn(repl, text, count=1)
    if n == 0:
        console.print("[red]Не нашёл массив sources = [...] в osdev.toml[/red]")
        raise typer.Exit(1)

    toml_path.write_text(new_text, encoding="utf-8")
    console.print(f"[green]Добавлено в sources:[/green] {rel}")


@app.command()
def upgrade(
    check: bool = typer.Option(
        False, "--check", "-c",
        help="Только проверить, не обновлять",
    ),
) -> None:
    """Проверить и обновить python-osdev с PyPI."""
    raise typer.Exit(code=run_upgrade(check_only=check))


@app.command()
def disasm(
    boot: bool = typer.Option(False, "--boot", help="Дизассемблировать boot.bin (только MBR)"),
    func: str = typer.Option(None, "--func", help="Только одна функция (objdump)"),
    out: Path = typer.Option(None, "--out", "-o", help="Путь для .dis файла"),
) -> None:
    """Дизассемблировать ядро (или загрузчик) в build/*.dis."""
    try:
        result = disassemble(Path.cwd(), boot_only=boot, func=func, out_path=out)
    except Exception as e:
        console.print(f"[red]Ошибка:[/red] {e}")
        raise typer.Exit(1)
    typer.echo(f"Открой: {result}")


if __name__ == "__main__":
    app()