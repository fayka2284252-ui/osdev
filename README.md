# osdev

Инструмент для разработки операционных систем на Windows — без WSL, без MSYS2, без кросс-компилятора.

Одна команда — и у тебя есть весь тулчейн: компилятор C/C++ для bare-metal, ассемблер, линкер, эмулятор и отладчик. Всё нативно под Windows.

## Зачем

Классический путь OSDev на Windows выглядит так:

- поставить WSL или MSYS2,
- собрать `i686-elf-gcc` (полдня),
- разобраться с `xorriso`, `grub-mkrescue`, `mtools`,
- писать Makefile,
- ловить странные ошибки путей.

`osdev` убирает всё это. Ты пишешь `kernel.c`, нажимаешь `osdev run` и видишь своё ядро в QEMU через 5 секунд.

## Быстрый старт

```cmd
:: 0. установить инструмент
pip install python-osdev

:: 1. поставить тулчейн (один раз)
osdev setup

:: 2. проверить, что всё на месте
osdev doctor

:: 3. создать проект
osdev new myos
cd myos

:: 4. собрать и запустить
osdev run
```

В окне QEMU появится:

```
Hello from osdev!
i686, protected mode, C kernel.
```

## Команды

| Команда | Что делает |
|---|---|
| `osdev doctor` | Проверить, что установлено (Zig, NASM, QEMU, GDB) |
| `osdev setup` | Скачать и распаковать тулчейн в `~/.osdev/tools/` |
| `osdev new <name>` | Создать новый проект ОС из шаблона |
| `osdev add <file.c>` | Добавить `.c` в `[build].sources` в `osdev.toml` |
| `osdev build` | Собрать образ (`build/<name>.img`) |
| `osdev run` | Собрать и запустить в QEMU |
| `osdev debug` | Собрать и запустить под GDB (с брейкпоинтом на `kernel_main`) |
| `osdev --version` | Показать версию пакета |

### `osdev debug` — что попробовать в GDB

```
(gdb) info registers        # состояние регистров
(gdb) x/10i $pc             # дизассемблер вокруг текущей инструкции
(gdb) si                    # шаг
(gdb) c                     # продолжить
(gdb) q                     # выход
```

## Требования

- **Windows 10/11**
- **Python 3.10+**

Больше ничего. Zig, NASM и QEMU `osdev setup` поставит сам.
GDB нужен только для `osdev debug` (можно взять из mingw-w64).

## VS Code: IntelliSense ругается на `__asm__`

Если открыть файлы ядра в VS Code, расширение **C/C++** (Microsoft)
может подчёркивать красным:

```
identifier "__asm__" is undefined
expected a ";"
```

**Это не ошибки сборки.** IntelliSense не знает про GNU-расширения
(`__asm__`, `__attribute__`, `__builtin_*`) и по умолчанию настроен
под MSVC. Настоящий компилятор — `zig cc` — собирает этот же код
без проблем.

**Правило:** смотри на вывод `osdev build` в терминале, а не на панель
Problems в VS Code.

Чтобы убрать подчёркивания, создай в корне проекта `.vscode/settings.json`:

```json
{
  "C_Cpp.errorSquiggles": "disabled"
}
```

Это отключит подсветку ошибок от IntelliSense, оставив автодополнение
и подсветку синтаксиса.

## Что внутри

```
osdev/
├── cli.py            # команды Typer
├── detect.py         # поиск тулчейна в ~/.osdev/tools и в системе
├── doctor.py         # вывод таблицы
├── setup.py          # скачивание NASM, Zig
├── build.py          # сборка ядра: nasm → zig cc → ld.lld → .img
├── errors.py         # человеческие подсказки к ошибкам компилятора
└── templates/
    ├── i686-c-mbr/   # шаблон: свой bootloader + C-ядро
    └── i686-cpp-mbr/ # то же на C++
```

## Что делает `osdev build`

1. `nasm -f bin src/boot.asm -o build/boot.bin` — 512-байтный MBR.
2. `zig cc -target x86-freestanding-none -c src/kernel.c` — объектник.
3. `zig cc ... -fuse-ld=lld -T src/linker.ld` — линковка в ELF.
4. Python извлекает загружаемые секции → `kernel.bin`.
5. Склеивает `boot.bin + kernel.bin` → `build/<name>.img` (1.44 MB).

## Стек тулчейна

| Задача | Инструмент | Почему |
|---|---|---|
| C/C++ компилятор | **Zig (`zig cc`)** | Один бинарник, включает clang + lld + freestanding headers. Не нужен кросс-gcc. |
| Ассемблер | **NASM** | Стандарт для OSDev, 16-bit + 32-bit + 64-bit. |
| Линкер | **ld.lld** | Внутри Zig. |
| Эмулятор | **QEMU** | i386, x86_64, ARM — всё в одном пакете. |
| Отладчик | **GDB** | Подключается к QEMU через `-gdb tcp::1234`. |

## Roadmap

- [x] CLI + `doctor` + `setup` (NASM, Zig)
- [x] `new` + `build` + `run` + `debug` + `add`
- [x] Шаблон `i686-c-mbr`
- [x] Шаблон `i686-cpp-mbr`
- [x] Человеческие подсказки к ошибкам (`errors.py`)
- [x] Флаг `--version`
- [ ] Шаблон `i686-c-printf` (своя мини-реализация `printf`)
- [ ] Multiboot / GRUB (`boot = "multiboot"` в `osdev.toml`)
- [ ] Шаблон `x86_64-c-mbr` (long mode, page tables)
- [ ] ARM (`aarch64`)
- [ ] GUI поверх CLI

> **Про IDT, PIC, PIT и клавиатуру.** python-osdev — это старт, а не
> конструктор ОС. Мы даём базовый шаблон с загрузчиком и VGA-выводом,
> а прерывания, таймер и драйверы ты пишешь сам — в этом и есть OSDev.

## Два режима загрузки

`osdev new` по умолчанию создаёт MBR-проект (`boot = "mbr"`) — свой
загрузчик, свой `boot.asm`, ядро на `0x10000`. Это учебный путь: ты
сам пишешь всё, включая загрузчик.

Для проектов, где не хочется возиться с `int 13h` и геометрией диска,
есть второй режим — Multiboot:

```cmd
osdev new myos -t i686-c-multiboot
cd myos
osdev build        # собирает kernel.elf (ELF, не .img)
osdev run          # qemu -kernel build/kernel.elf

## Два режима загрузки

`osdev new` по умолчанию создаёт MBR-проект (`boot = "mbr"`) — свой
загрузчик, свой `boot.asm`, ядро на `0x10000`. Это учебный путь: ты
сам пишешь всё, включая загрузчик.

Для проектов, где не хочется возиться с `int 13h` и геометрией диска,
есть второй режим — Multiboot:

```cmd
osdev new myos -t i686-c-multiboot
cd myos
osdev build        # собирает kernel.elf (ELF, не .img)
osdev run          # qemu -kernel build/kernel.elf
```

**Почему Multiboot.** QEMU (и любой GRUB) сам читает ELF по заголовку
`0x1BADB002`, грузит ядро на `0x100000`, обнуляет BSS и передаёт
указатель на `multiboot_info_t` в `EBX`. Никакого `int 13h`, никакой
геометрии диска, никаких retry при чтении секторов.

**Что теряется.** Ты больше не пишешь загрузчик сам — это уже готовый
кусок. Если цель — учебный OSDev с нуля, начни с `i686-c-mbr`.

### Конфиг `osdev.toml`

```toml
[project]
name = "myos"
arch = "i686"
lang = "c"
boot = "mbr"          # или "multiboot", или "grub"

[build]
asm = ["src/boot/multiboot.asm"]
sources = ["src/kernel/kernel.c", "src/drivers/vga.c"]
include = ["src"]
linker = "src/linker.ld"
```

Режимы:
- `boot = "mbr"` — nasm `-f bin` + MBR + плоский `.img` 1.44 МБ
- `boot = "multiboot"` — nasm `-f elf32` + `qemu -kernel`
- `boot = "grub"` — multiboot + `grub-mkrescue` (нужен WSL или grub-mkrescue в PATH)

## `osdev disasm`

Дизассемблирует ядро (или загрузчик) в `build/*.dis`:

```cmd
osdev disasm                    # всё ядро (objdump -M intel)
osdev disasm --func kernel_main # только одна функция
osdev disasm --boot             # boot.bin, 16-бит (только MBR)
```

Требует `objdump` в PATH (можно взять из mingw-w64) — или возьмёт
`ndisasm` из комплекта NASM как запасной вариант.

## Roadmap

- [x] CLI + `doctor` + `setup`
- [x] `new` + `build` + `run` + `debug` + `add` + `upgrade` + `disasm`
- [x] Шаблон `i686-c-mbr` (C, свой MBR)
- [x] Шаблон `i686-cpp-mbr` (C++)
- [x] Множественные asm-файлы
- [x] `--version`, `doctor --verbose`
- [x] Multiboot: `boot = "multiboot"` / `"grub"`, шаблон `i686-c-multiboot`
- [ ] Шаблон `x86_64-c-mbr` (long mode, page tables)
- [ ] ARM (`aarch64`)
- [ ] GUI поверх CLI

> **Про IDT, PIC, PIT и клавиатуру.** python-osdev — это старт, а не
> конструктор ОС. Мы даём базовый шаблон с загрузчиком и VGA-выводом,
> а прерывания, таймер и драйверы ты пишешь сам — в этом и есть OSDev.

## Лицензия

MIT.