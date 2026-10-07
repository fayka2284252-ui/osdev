from __future__ import annotations
import json
import platform
import shutil
import sys
from importlib.metadata import (
    version as _pkg_version,
    distribution,
    PackageNotFoundError,
)
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .detect import (
    TOOLS,
    probe,
    _find_in_osdev_home,
    _find_in_known_windows_dirs,
)
from .paths import OSDEV_HOME, TOOLS_DIR

console = Console()


def _pkg_ver() -> str:
    try:
        return _pkg_version("python-osdev")
    except PackageNotFoundError:
        return "unknown"


def _is_editable() -> bool:
    try:
        dist = distribution("python-osdev")
        du = dist.read_text("direct_url.json")
        if du:
            data = json.loads(du)
            return "dir_info" in data
    except Exception:
        pass
    return False


def _full_path(binary: str) -> str:
    p = _find_in_osdev_home(binary) or _find_in_known_windows_dirs(binary)
    if not p:
        p = shutil.which(binary)
    return p or "—"


def run_doctor(verbose: bool = False) -> int:
    table = Table(title="osdev doctor", show_lines=False)
    table.add_column("Инструмент", style="bold")
    table.add_column("Статус")
    table.add_column("Версия / путь")
    table.add_column("Подсказка", style="dim")

    missing_required = 0
    for tool in TOOLS:
        ok, info = probe(tool)
        if ok:
            table.add_row(tool.name, "[green]OK[/green]", info, "")
        else:
            status = "[red]НЕТ[/red]" if tool.required else "[yellow]нет (опц.)[/yellow]"
            if tool.required:
                missing_required += 1
            table.add_row(tool.name, status, "—", tool.hint)

    console.print(table)

    if verbose:
        console.print()
        env = Table(title="Окружение", show_lines=False)
        env.add_column("Параметр", style="bold")
        env.add_column("Значение")

        ver = _pkg_ver()
        if _is_editable():
            ver += " [yellow](editable)[/yellow]"
        env.add_row("python-osdev", ver)
        env.add_row("Python", f"{sys.version.split()[0]} ({platform.python_implementation()})")
        env.add_row("Python exe", sys.executable)
        env.add_row("ОС", f"{platform.system()} {platform.release()}")
        env.add_row("cwd", str(Path.cwd()))
        env.add_row("OSDEV_HOME", str(OSDEV_HOME))
        env.add_row(
            "TOOLS_DIR",
            str(TOOLS_DIR) + ("" if TOOLS_DIR.exists() else " [dim](нет)[/dim]"),
        )
        console.print(env)

        console.print()
        paths = Table(title="Пути к инструментам", show_lines=False)
        paths.add_column("Инструмент", style="bold")
        paths.add_column("Путь", style="dim")
        for tool in TOOLS:
            paths.add_row(tool.name, _full_path(tool.binary))
        console.print(paths)

    if missing_required:
        console.print(
            f"\n[yellow]Не хватает {missing_required} обязательных инструментов.[/yellow]"
            "\nЗапусти: [bold]osdev setup[/bold]"
        )
        return 1

    console.print("\n[green]Всё готово. Можно создавать проект: osdev new myos[/green]")
    return 0