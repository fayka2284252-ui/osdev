from __future__ import annotations
import subprocess
import shutil
from pathlib import Path

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


if __name__ == "__main__":
    app()