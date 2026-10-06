from __future__ import annotations

from rich.console import Console

console = Console()


# Правила: (подстрока в выводе, короткий заголовок, объяснение и фикс)
RULES: list[tuple[str, str, str]] = [
    (
        "undefined reference to `printf'",
        "Нет stdlib: printf",
        "В bare-metal ядре нет стандартной библиотеки C. Напиши свою функцию "
        "вывода в VGA (пример: puts_at в шаблоне i686-c-mbr) или подключи "
        "freestanding-реализацию printf.",
    ),
    (
        "undefined reference to `puts'",
        "Нет stdlib: puts",
        "Стандартный puts отсутствует в bare-metal. Используй свой вывод в VGA.",
    ),
    (
        "undefined reference to `malloc'",
        "Нет stdlib: malloc",
        "В ядре нет кучи по умолчанию. Реализуй свой аллокатор или используй "
        "статически выделенные буферы.",
    ),
    (
        "undefined reference to `free'",
        "Нет stdlib: free",
        "Парная к malloc проблема. Реализуй свой аллокатор (например, bump allocator).",
    ),
    (
        "undefined reference to `memcpy'",
        "Нет stdlib: memcpy",
        "Clang иногда генерирует вызовы memcpy/memset автоматически. Реализуй их "
        "сам в kernel.c или добавь флаг -fno-builtin в build.py.",
    ),
    (
        "undefined reference to `memset'",
        "Нет stdlib: memset",
        "См. memcpy. Реализуй сам или используй -fno-builtin.",
    ),
    (
        "undefined reference to `__stack_chk_fail'",
        "Не отключён stack protector",
        "Добавь флаг -fno-stack-protector в команду компиляции (см. build.py).",
    ),
    (
        "cannot find entry symbol _start",
        "Не задана точка входа",
        "Линкер не знает, с какой функции начинать. В linker.ld должна быть "
        "строка ENTRY(kernel_main), а в build.py — флаг -Wl,-e,kernel_main.",
    ),
    (
        "relocation R_386_16 against",
        "Смещение не влезает в 16 бит",
        "В 16-битном коде адрес не помещается в 16-битный регистр. Проверь, "
        "что bootloader — BITS 16 и ORG 0x7C00.",
    ),
    (
        "undefined symbol",
        "Неизвестный символ",
        "Возможно, забыт extern или опечатка в имени функции. Проверь заголовки "
        "и сигнатуры.",
    ),
    (
        "file format not recognized",
        "Неверный формат файла",
        "Проверь, что boot.asm ассемблируется через nasm -f bin, а kernel.c "
        "компилируется, а не ассемблируется.",
    ),
    (
        "No such file or directory",
        "Не найден файл",
        "Проверь пути в osdev.toml: asm, sources, linker. Они относительны "
        "папки проекта.",
    ),
    (
        "error: unsupported linker arg: --oformat",
        "lld не поддерживает --oformat",
        "Используй ELF + извлечение секций через elf_to_binary "
        "(уже реализовано в build.py).",
    ),
    (
        "boot.bin должен быть 512 байт",
        "Загрузчик больше 512 байт",
        "MBR ограничен 512 байтами. Убери лишний код из boot.asm или перенеси "
        "его в ядро.",
    ),
    (
        "multiple definition of",
        "Двойное определение символа",
        "Один и тот же символ объявлен в нескольких .c файлах. Используй extern "
        "в заголовке и определение только в одном месте.",
    ),
    (
        "error: unknown target triple",
        "Неизвестная целевая архитектура",
        "Проверь поле arch в osdev.toml. Для i686 используется "
        "x86-freestanding-none.",
    ),
]


def explain(text: str) -> list[tuple[str, str]]:
    """Возвращает список (заголовок, объяснение) для найденных проблем."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for needle, title, fix in RULES:
        if needle in text and title not in seen:
            out.append((title, fix))
            seen.add(title)
    return out


def print_hints(text: str) -> None:
    hints = explain(text)
    if not hints:
        return
    console.print()
    console.print("[yellow]Подсказки:[/yellow]")
    for title, fix in hints:
        console.print(f"  [bold]{title}[/bold]")
        console.print(f"    {fix}")