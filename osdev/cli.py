from __future__ import annotations
import subprocess
import shutil
from pathlib import Path
import os
import tempfile

import typer
from rich.console import Console

from .doctor import run_doctor
from .setup import install_nasm, install_zig
from .build import build as build_project, load_config, find_tool

app = typer.Typer(
    help="OSDev toolkit для Windows — без WSL, без боли.",
    no_args_is_help=True,
)
console = Console()

TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.command()
def doctor() -> None:
    """Проверить, что установлено в системе."""
    raise typer.Exit(code=run_doctor())


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

    shutil.copytree(src, dst)

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
        img = build_project(Path.cwd())
    except Exception as e:
        console.print(f"[red]Ошибка:[/red] {e}")
        raise typer.Exit(1)
    typer.echo(f"\nГотово: {img}")
    typer.echo("Запусти: osdev run")


@app.command()
def run(
    mem: str = typer.Option("128M", "--mem", "-m", help="Объём RAM"),
    no_build: bool = typer.Option(False, "--no-build", help="Не пересобирать"),
) -> None:
    """Собрать и запустить образ в QEMU."""
    project_dir = Path.cwd()
    cfg = load_config(project_dir)
    name = cfg["project"]["name"]
    output_rel = cfg["build"].get("output", f"build/{name}.img")
    img = project_dir / output_rel

    if not no_build:
        build_project(project_dir)

    if not img.exists():
        console.print(f"[red]Образ не найден:[/red] {img}")
        raise typer.Exit(1)

    qemu = find_tool("qemu-system-i386")
    console.print(f"[green]QEMU[/green]: {qemu}")
    console.print("[dim]Закрой окно QEMU или нажми Ctrl+C для выхода.[/dim]")
    subprocess.run([
        qemu,
        "-drive", f"format=raw,file={img}",
        "-m", mem,
    ])

@app.command()
def debug(
    mem: str = typer.Option("128M", "--mem", "-m", help="Объём RAM"),
    no_build: bool = typer.Option(False, "--no-build", help="Не пересобирать"),
    port: int = typer.Option(1234, "--port", help="Порт GDB-сервера QEMU"),
) -> None:
    """Собрать и запустить QEMU под GDB (пошаговая отладка ядра)."""
    project_dir = Path.cwd()
    cfg = load_config(project_dir)
    name = cfg["project"]["name"]
    output_rel = cfg["build"].get("output", f"build/{name}.img")
    img = project_dir / output_rel
    kernel_elf = project_dir / "build" / "kernel.elf"

    if not no_build:
        build_project(project_dir)

    if not img.exists():
        console.print(f"[red]Образ не найден:[/red] {img}")
        raise typer.Exit(1)
    if not kernel_elf.exists():
        console.print(f"[red]kernel.elf не найден:[/red] {kernel_elf}")
        raise typer.Exit(1)

    qemu = find_tool("qemu-system-i386")
    gdb = find_tool("gdb")

    console.print(f"[green]QEMU[/green]: {qemu} (GDB :{port}, пауза)")
    qemu_proc = subprocess.Popen([
        qemu,
        "-drive", f"format=raw,file={img}",
        "-m", mem,
        "-S",
        "-gdb", f"tcp::{port}",
    ])

    # пишем команды GDB в файл — надёжнее, чем -ex на Windows
    cmds = "\n".join([
        f"target remote localhost:{port}",
        f"symbol-file {kernel_elf.as_posix()}",
        "break kernel_main",
        "continue",
    ]) + "\n"

    fd, gdb_script = tempfile.mkstemp(suffix=".gdb")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(cmds)

    try:
        console.print(f"[green]GDB[/green]: {gdb}")
        console.print("[dim]Команды: c (continue), si (step), b <symbol>, info registers, x/10i $pc, q (quit)[/dim]")
        subprocess.run([gdb, "-x", gdb_script, str(kernel_elf)])
    finally:
        try:
            os.unlink(gdb_script)
        except OSError:
            pass
        if qemu_proc.poll() is None:
            qemu_proc.terminate()
            console.print("[dim]QEMU остановлен.[/dim]")

if __name__ == "__main__":
    app()

