# osdev

**Инструмент для разработки операционных систем на Windows — без WSL, без MSYS2, без кросс-компилятора.**

Одна команда — и у тебя есть весь тулчейн: компилятор C/C++ для bare-metal,
ассемблер, линкер, эмулятор и отладчик. Всё нативно под Windows.

## Зачем

Классический путь OSDev на Windows выглядит так:

- поставить WSL или MSYS2,
- собрать `i686-elf-gcc` (полдня),
- разобраться с `xorriso`, `grub-mkrescue`, `mtools`,
- писать Makefile,
- ловить странные ошибки путей.

`osdev` убирает всё это. Ты пишешь `kernel.c`, нажимаешь `osdev run` и видишь
своё ядро в QEMU через 5 секунд.

## Быстрый старт

```cmd
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
| `osdev build` | Собрать образ (`build/<name>.img`) |
| `osdev run` | Собрать и запустить в QEMU |
| `osdev debug` | Собрать и запустить под GDB (с брейкпоинтом на `kernel_main`) |

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
    └── i686-c-mbr/   # шаблон: свой bootloader + C-ядро
```

### Что делает `osdev build`

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
- [x] `new` + `build` + `run` + `debug`
- [x] Шаблон `i686-c-mbr`
- [x] Человеческие подсказки к ошибкам (`errors.py`)
- [ ] Шаблон `i686-cpp-mbr`
- [ ] Шаблон `i686-c-printf` (своя мини-реализация printf)
- [ ] Шаблон `x86_64-c-mbr` (long mode, page tables)
- [ ] Обработка прерываний (IDT, PIC, клавиатура)
- [ ] ARM (`aarch64`)
- [ ] GUI поверх CLI

## Лицензия

MIT.