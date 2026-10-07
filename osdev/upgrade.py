from __future__ import annotations
import json
import subprocess
import sys
import urllib.request
from importlib.metadata import (
    version as _pkg_version,
    distribution,
    PackageNotFoundError,
)
from pathlib import Path

from rich.console import Console

console = Console()

PKG_NAME = "python-osdev"
PYPI_JSON = f"https://pypi.org/pypi/{PKG_NAME}/json"


def _local_version() -> str:
    try:
        return _pkg_version(PKG_NAME)
    except PackageNotFoundError:
        return "0.0.0"


def _is_editable() -> bool:
    try:
        dist = distribution(PKG_NAME)
        du = dist.read_text("direct_url.json")
        if du:
            data = json.loads(du)
            return "dir_info" in data
    except Exception:
        pass
    return False


def _latest_from_pypi(timeout: int = 5) -> str | None:
    try:
        with urllib.request.urlopen(PYPI_JSON, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data["info"]["version"]
    except Exception:
        return None


def _parse(v: str) -> tuple[int, ...]:
    """'0.3.2' → (0,3,2). Некорректные куски → 0."""
    out: list[int] = []
    for part in v.split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        out.append(int(num) if num else 0)
    return tuple(out)


def _is_newer(latest: str, current: str) -> bool:
    return _parse(latest) > _parse(current)


def run_upgrade(check_only: bool = False) -> int:
    current = _local_version()
    console.print(f"Текущая версия: [bold]{current}[/bold]")

    latest = _latest_from_pypi()
    if latest is None:
        console.print("[red]Не удалось получить данные с PyPI. Проверь интернет.[/red]")
        return 1

    console.print(f"Последняя на PyPI: [bold]{latest}[/bold]")

    if not _is_newer(latest, current):
        console.print("[green]У тебя последняя версия.[/green]")
        return 0

    console.print(f"\n[yellow]Доступна новая версия: {current} → {latest}[/yellow]")

    if check_only:
        console.print("[dim]Запусти `osdev upgrade` без --check, чтобы обновить.[/dim]")
        return 0

    if _is_editable():
        console.print(
            "\n[yellow]Установлена editable-версия (pip install -e .).[/yellow]\n"
            "Автообновление отключено, иначе потеряешь свою разработку.\n"
            "[dim]Обнови вручную: git pull && pip install -e . --no-deps[/dim]"
        )
        return 0

    console.print(f"\nЗапускаю: pip install --upgrade {PKG_NAME}=={latest}")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", f"{PKG_NAME}=={latest}"],
    )
    if r.returncode != 0:
        console.print("[red]Не получилось. Попробуй вручную:[/red]")
        console.print(f"  pip install --upgrade {PKG_NAME}")
        return r.returncode

    console.print(f"\n[green]Обновлено до {latest}.[/green]")
    console.print("[dim]Перезапусти терминал, чтобы PATH обновился.[/dim]")
    return 0