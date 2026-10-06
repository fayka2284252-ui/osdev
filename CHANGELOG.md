# Changelog

Все значимые изменения проекта. Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

## [Unreleased]

## [0.1.0] — 2026-10-06

### Added

- CLI на Typer + Rich с командами:
  - `doctor` — таблица состояния тулчейна
  - `setup` — установка NASM 2.16.03 и Zig 0.13.0
  - `new` — создание проекта из шаблона
  - `build` — сборка образа
  - `run` — запуск в QEMU
  - `debug` — QEMU + GDB с брейкпоинтом на `kernel_main`
- Менеджер тулчейна: скачивание и распаковка в `~/.osdev/tools/`
- Автопоиск тулчейна в `~/.osdev/tools/`, в стандартных каталогах Windows
  (`C:\Program Files\qemu`) и в `PATH`
- Шаблон проекта `i686-c-mbr`:
  - MBR-загрузчик на NASM (16-bit → protected mode → C)
  - C-ядро с выводом в VGA текст
  - Линкер-скрипт для плоского бинарника
- `elf_to_binary` — извлечение загружаемых секций из ELF в плоский бинарник
  (замена неподдерживаемому `ld.lld --oformat=binary`)
- `errors.py` — человеческие подсказки к типовым ошибкам компилятора и линкера
- `README.md` — быстрый старт, список команд, описание пайплайна
- `.gitignore` для Python + артефактов сборки

### Fixed

- BOM в `pyproject.toml`, мешавший `pip install -e .`
- Поиск `nasm.exe` на Windows (добавлен `.exe`-суффикс)
- `_find_in_osdev_home` возвращал директорию вместо файла
- QEMU: `-s` и `-gdb` дублировали друг друга
- GDB: `-ex "target remote ..."` не работал на Windows — заменён на `-x <script>`
- QEMU raw-образ предупреждал о формате — явный `-drive format=raw,file=...`
- Линкер: явный `-Wl,-e,kernel_main`, иначе `ld.lld` не находил точку входа
- `_run` в `build.py` перехватывает stdout/stderr и вызывает `errors.print_hints`