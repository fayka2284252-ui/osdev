from __future__ import annotations
import shutil
import subprocess
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from pathlib import Path

from rich.console import Console

from .detect import _find_in_osdev_home, _find_in_known_windows_dirs

console = Console()


def find_tool(name: str) -> str:
    path = _find_in_osdev_home(name) or _find_in_known_windows_dirs(name)
    if not path:
        path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Не найден инструмент: {name}")
    return path


def load_config(project_dir: Path) -> dict:
    cfg_path = project_dir / "osdev.toml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"osdev.toml не найден в {project_dir}")
    return tomllib.loads(cfg_path.read_text(encoding="utf-8"))


def _run(cmd: list[str], cwd: Path) -> None:
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    r = subprocess.run(
        cmd, cwd=cwd,
        capture_output=True, text=True, errors="replace",
    )
    if r.stdout:
        console.print(r.stdout, end="")
    if r.stderr:
        console.print(r.stderr, end="", style="red")
    if r.returncode != 0:
        from .errors import print_hints
        print_hints((r.stdout or "") + "\n" + (r.stderr or ""))
        raise RuntimeError(f"Команда вернула код {r.returncode}")


def elf_to_binary(elf_path: Path) -> bytes:
    """Извлекает загружаемые секции из 32-битного ELF в плоский бинарь."""
    data = elf_path.read_bytes()
    if data[:4] != b"\x7fELF":
        raise RuntimeError("не ELF-файл")
    if data[4] != 1:
        raise RuntimeError("ожидаю 32-битный ELF")

    e_shoff = int.from_bytes(data[0x20:0x24], "little")
    e_shentsize = int.from_bytes(data[0x2E:0x30], "little")
    e_shnum = int.from_bytes(data[0x30:0x32], "little")

    sections: list[tuple[int, int, int]] = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh = data[off:off + e_shentsize]
        sh_type = int.from_bytes(sh[4:8], "little")
        sh_flags = int.from_bytes(sh[8:12], "little")
        sh_addr = int.from_bytes(sh[12:16], "little")
        sh_offset = int.from_bytes(sh[16:20], "little")
        sh_size = int.from_bytes(sh[20:24], "little")
        SHF_ALLOC = 0x2
        SHT_NOBITS = 8
        if (sh_flags & SHF_ALLOC) and sh_type != SHT_NOBITS and sh_size > 0:
            sections.append((sh_addr, sh_offset, sh_size))

    if not sections:
        raise RuntimeError("в ELF нет загружаемых секций")

    sections.sort()
    base = sections[0][0]
    out = bytearray()
    for addr, off, size in sections:
        while base + len(out) < addr:
            out.append(0)
        out += data[off:off + size]
    return bytes(out)


def build(project_dir: Path) -> Path:
    cfg = load_config(project_dir)
    project_cfg = cfg["project"]
    build_cfg = cfg["build"]
    name = project_cfg["name"]

    build_dir = project_dir / "build"
    build_dir.mkdir(exist_ok=True)

    nasm = find_tool("nasm")
    zig = find_tool("zig")

    # ---- 1. asm файлы ----
    asm_files = build_cfg.get("asm", [])
    if not asm_files:
        raise RuntimeError("В [build].asm нет ни одного файла")

    kernel_sectors = int(build_cfg.get("kernel_sectors", 32))

    boot_src = project_dir / asm_files[0]
    boot_bin = build_dir / "boot.bin"
    _run([
        nasm,
        "-f", "bin",
        f"-dKERNEL_SECTORS={kernel_sectors}",
        str(boot_src),
        "-o", str(boot_bin),
    ], project_dir)
    size = boot_bin.stat().st_size
    if size != 512:
        raise RuntimeError(f"boot.bin должен быть 512 байт, получилось {size}")
    console.print(f"[green]boot.bin[/green] = 512 байт")

    # дополнительные asm -> elf32 объектники
    extra_asm_objs: list[Path] = []
    for rel in asm_files[1:]:
        src = project_dir / rel
        obj = build_dir / f"{src.stem}.o"
        _run([nasm, "-f", "elf32", str(src), "-o", str(obj)], project_dir)
        console.print(f"[green]{src.stem}.o[/green] = {obj.stat().st_size} байт")
        extra_asm_objs.append(obj)

    # ---- 2. C/C++ -> объектник ----
    sources_cfg = build_cfg.get("sources", [])
    if not sources_cfg:
        raise RuntimeError("В [build].sources нет ни одного файла")

    # Bug #4: предупреждаем о файлах в src/, не включённых в sources
    src_dir = project_dir / "src"
    if src_dir.is_dir():
        declared = {(project_dir / s).resolve() for s in sources_cfg}
        for f in sorted(src_dir.iterdir()):
            if not f.is_file():
                continue
            if f.suffix not in (".c", ".cpp", ".S"):
                continue
            if f.name == "boot.asm":
                continue
            if f.resolve() not in declared:
                console.print(
                    f"[yellow]⚠ {f.name} есть в src/, но не указан в \\[build].sources "
                    f"в osdev.toml — линкер может упасть с undefined symbol.[/yellow]"
                )
                console.print(
                    f"[dim]  Добавь вручную: sources = [..., \"src/{f.name}\"]"
                    f"\n  Или запусти: osdev add {f.name}[/dim]"
                )

    sources = [str(project_dir / s) for s in sources_cfg]

    include_flags: list[str] = []
    for inc in build_cfg.get("include", []):
        include_flags += ["-I", str(project_dir / inc)]

    lang = project_cfg.get("lang", "c")
    zig_frontend = "c++" if lang == "cpp" else "cc"

    cxx_flags: list[str] = []
    if lang == "cpp":
        cxx_flags = ["-fno-exceptions", "-fno-rtti", "-std=c++20"]

    kernel_o = build_dir / "kernel.o"
    _run([
        zig, zig_frontend,
        "-target", "x86-freestanding-none",
        "-ffreestanding", "-nostdlib",
        "-fno-stack-protector",
        "-O2",                              # оптимизация + отключение UBSan
        "-fno-sanitize=undefined",          # страховка
        "-fwrapv",                          # знаковое переполнение — циклично, а не UB
        *cxx_flags,
        "-c",
        *include_flags,
        *sources,
        "-o", str(kernel_o),
    ], project_dir)
    console.print(f"[green]kernel.o[/green] = {kernel_o.stat().st_size} байт")

    # ---- 3. линковка ----
    linker = project_dir / build_cfg["linker"]
    kernel_elf = build_dir / "kernel.elf"
    _run([
        zig, zig_frontend,
        "-target", "x86-freestanding-none",
        "-nostdlib",
        "-fuse-ld=lld",
        f"-T{linker}",
        "-Wl,--build-id=none",
        "-Wl,-e,kernel_main",
        str(kernel_o),
        *[str(o) for o in extra_asm_objs],
        "-o", str(kernel_elf),
    ], project_dir)
    console.print(f"[green]kernel.elf[/green] = {kernel_elf.stat().st_size} байт")

    kernel_bin = build_dir / "kernel.bin"
    kernel_bin.write_bytes(elf_to_binary(kernel_elf))
    console.print(f"[green]kernel.bin[/green] = {kernel_bin.stat().st_size} байт")

    # ---- 4. образ ----
    img = project_dir / build_cfg.get("output", f"build/{name}.img")
    img.parent.mkdir(parents=True, exist_ok=True)

    target = 1440 * 1024  # 1.44 MB floppy
    data = boot_bin.read_bytes() + kernel_bin.read_bytes()
    if len(data) > target:
        raise RuntimeError(f"Образ больше {target} байт: {len(data)}")
    data += b"\x00" * (target - len(data))
    img.write_bytes(data)

    console.print(f"[green]Образ[/green] {img} ({img.stat().st_size} байт)")
    return img