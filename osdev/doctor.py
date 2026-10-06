from rich.console import Console
from rich.table import Table
from .detect import TOOLS, probe

console = Console()


def run_doctor() -> int:
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

    if missing_required:
        console.print(
            f"\n[yellow]Не хватает {missing_required} обязательных инструментов.[/yellow]"
            "\nЗапусти: [bold]osdev setup[/bold]"
        )
        return 1

    console.print("\n[green]Всё готово. Можно создавать проект: osdev new myos[/green]")
    return 0
