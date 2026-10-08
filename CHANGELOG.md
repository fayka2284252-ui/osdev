# Changelog

Все значимые изменения проекта. Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

## [Unreleased]

## [0.4.0] — 2026-10-08

### Added
- Multiboot: `boot = "multiboot"` в `osdev.toml` — сборка `kernel.elf`, запуск через `qemu -kernel`
- GRUB: `boot = "grub"` — генерация ISO через `grub-mkrescue` (PATH или WSL)
- Шаблон `i686-c-multiboot` — структура `src/boot/`, `src/kernel/`, `src/drivers/`
- `osdev disasm` — дизассемблер через objdump (`--func`) или ndisasm (`--boot`)
- `osdev run` / `osdev debug` понимают три режима загрузки
- Рекурсивный `-I` — все подпапки `src/` добавляются автоматически
- Рекурсивный auto-scan `src/**/*.c` для предупреждения о забытых файлах

### Changed
- `osdev/build.py` разбит на три ветки по `boot` (mbr / multiboot / grub)

## [0.3.3] — 2026-10-08

## [0.3.3] — 2026-10-08

### Added
- `osdev doctor --verbose` — окружение, пути к тулчейну, editable-статус
- `osdev upgrade` — проверка и обновление с PyPI (`--check` для проверки без установки)

### Fixed
- `publish.yml`: очистка `dist/` перед сборкой, чтобы старые артефакты не попадали в upload
- `dist/` убран из репозитория

## [Unreleased]

## [0.3.2] — 2026-10-07

### Added
- Флаг `--version` / `-V` в CLI — показывает версию пакета

## [0.3.1] — 2026-10-07

### Fixed
- **CI**: `UnicodeEncodeError` на Windows — принудительный UTF-8 в `cli.py`
  и env `PYTHONUTF8=1` в workflow
- **Publish**: дубль `osdev/templates/...` в wheel — убран лишний
  `force-include`, `packages` уже включает всё рекурсивно

## [0.3.0] — 2026-10-07

### Added
- `osdev add <file.c>` — добавляет файл в `[build].sources` в `osdev.toml`
- `kernel_sectors` в `osdev.toml` (по умолчанию 32 сектора = 16 КБ)
- Множественные asm-файлы (asm[0] — MBR, остальные — elf32-объектники)
- Автопроверка `src/*.c`: build предупреждает о файлах, не включённых в sources
- Флаги `-O2 -fno-sanitize=undefined -fwrapv` (отключают UBSan и уменьшают ядро вдвое)
- Раздел README про IntelliSense в VS Code

### Changed
- Ядро линкуется на `0x10000` (было `0x1000`). Раньше ядро >15 КБ затирало загрузчик.
- Загрузчик читает через INT 13h AH=42h (LBA), по одному сектору за раз

### Fixed
- Не инкрементировался `dap_lba` — QEMU висел на "Booting from Hard Disk..."
- `asm_src is not defined` в build.py
- Rich некорректно отображал `[build]` в предупреждениях

## [0.1.1] — 2026-10-06

### Added
- Trusted Publishing: релизы на GitHub автоматически публикуются на PyPI
- `dist/` добавлен в `.gitignore`

### Changed
- Версия пакета: 0.1.0 → 0.1.1

## [0.1.0] — 2026-10-06

### Added
- CLI на Typer + Rich: `doctor`, `setup`, `new`, `build`, `run`, `debug`
- Менеджер тулчейна: скачивание NASM 2.16.03 и Zig 0.13.0 в `~/.osdev/tools/`
- Автопоиск тулчейна в `~/.osdev/tools/`, `C:\Program Files\qemu`, PATH
- Шаблон `i686-c-mbr`: MBR + C-ядро + линкер-скрипт
- `elf_to_binary` — извлечение загружаемых секций из ELF в плоский бинарник
- `errors.py` — подсказки к типовым ошибкам компилятора и линкера
- `README.md`, `.gitignore`

### Fixed
- BOM в `pyproject.toml`, мешавший `pip install -e .`
- Поиск `nasm.exe` на Windows
- `_find_in_osdev_home` возвращал директорию вместо файла
- QEMU: `-s` и `-gdb` дублировали друг друга
- GDB: `-ex "target remote ..."` не работал на Windows — заменён на `-x <script>`
- QEMU raw-образ предупреждал о формате — явный `-drive format=raw,file=...`
- Линкер: явный `-Wl,-e,kernel_main`
- `_run` в `build.py` перехватывает stdout/stderr и вызывает `errors.print_hints`