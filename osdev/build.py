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


# ---------- Вспомогательные функции ----------

def _collect_include_dirs(project_dir: Path, src_dir: Path, cfg_includes: list[str]) -> list[Path]:
    """Все подпапки src/ + дополнительные include из osdev.toml."""
    dirs: list[Path] = []
    if src_dir.is_dir():
        dirs.append(src_dir)
        for d in sorted(src_dir.rglob("*")):
            if d.is_dir():
                dirs.append(d)
    for rel in cfg_includes:
        p = (project_dir / rel).resolve()
        if p not in dirs:
            dirs.append(p)
    return dirs


def _scan_unlisted_sources(project_dir: Path, src_dir: Path, sources_cfg: list[str]) -> list[Path]:
    """Все .c/.cpp/.S под src/, не попавшие в [build].sources."""
    if not src_dir.is_dir():
        return []
    declared = {(project_dir / s).resolve() for s in sources_cfg}
    unlisted: list[Path] = []
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix not in (".c", ".cpp", ".S"):
            continue
        if f.resolve() not in declared:
            unlisted.append(f)
    return unlisted


def _warn_unlisted(project_dir: Path, src_dir: Path, sources_cfg: list[str]) -> None:
    for f in _scan_unlisted_sources(project_dir, src_dir, sources_cfg):
        rel = f.relative_to(project_dir).as_posix()
        console.print(
            f"[yellow]⚠ {rel} есть в src/, но не указан в \\[build].sources "
            f"в osdev.toml — линкер может упасть с undefined symbol.[/yellow]"
        )
        console.print(
            f"[dim]  Добавь вручную: sources = [..., \"{rel}\"]"
            f"\n  Или запусти: osdev add {rel}[/dim]"
        )


# ---------- Общие шаги сборки ----------

def _compile_c(zig: str, zig_frontend: str, cxx_flags: list[str],
               project_dir: Path, build_dir: Path,
               sources_cfg: list[str], include_dirs: list[Path]) -> Path:
    if not sources_cfg:
        raise RuntimeError("В [build].sources нет ни одного файла")

    include_flags: list[str] = []
    for d in include_dirs:
        include_flags += ["-I", str(d)]

    kernel_o = build_dir / "kernel.o"
    _run([
        zig, zig_frontend,
        "-target", "x86-freestanding-none",
        "-ffreestanding", "-nostdlib",
        "-fno-stack-protector",
        "-O2",
        "-fno-sanitize=undefined",
        "-fwrapv",
        *cxx_flags,
        "-c",
        *include_flags,
        *[str(project_dir / s) for s in sources_cfg],
        "-o", str(kernel_o),
    ], project_dir)
    console.print(f"[green]kernel.o[/green] = {kernel_o.stat().st_size} байт")
    return kernel_o


def _link_elf(zig: str, zig_frontend: str, project_dir: Path, build_dir: Path,
              kernel_o: Path, extra_asm_objs: list[Path],
              linker: Path, entry: str) -> Path:
    kernel_elf = build_dir / "kernel.elf"
    _run([
        zig, zig_frontend,
        "-target", "x86-freestanding-none",
        "-nostdlib",
        "-fuse-ld=lld",
        f"-T{linker}",
        "-Wl,--build-id=none",
        f"-Wl,-e,{entry}",
        str(kernel_o),
        *[str(o) for o in extra_asm_objs],
        "-o", str(kernel_elf),
    ], project_dir)
    console.print(f"[green]kernel.elf[/green] = {kernel_elf.stat().st_size} байт")
    return kernel_elf


# ---------- Три режима сборки ----------

def _build_mbr(project_dir: Path, build_dir: Path, cfg: dict, name: str,
               nasm: str, zig: str, zig_frontend: str, cxx_flags: list[str]) -> Path:
    build_cfg = cfg["build"]

    asm_files = build_cfg.get("asm", [])
    if not asm_files:
        raise RuntimeError("В [build].asm нет ни одного файла")
    kernel_sectors = int(build_cfg.get("kernel_sectors", 32))

    boot_src = project_dir / asm_files[0]
    boot_bin = build_dir / "boot.bin"
    _run([
        nasm, "-f", "bin",
        f"-dKERNEL_SECTORS={kernel_sectors}",
        str(boot_src), "-o", str(boot_bin),
    ], project_dir)
    if boot_bin.stat().st_size != 512:
        raise RuntimeError(f"boot.bin должен быть 512 байт, получилось {boot_bin.stat().st_size}")
    console.print(f"[green]boot.bin[/green] = 512 байт")

    # дополнительные asm как elf32
    extra_asm_objs: list[Path] = []
    for rel in asm_files[1:]:
        src = project_dir / rel
        obj = build_dir / f"{src.stem}.o"
        _run([nasm, "-f", "elf32", str(src), "-o", str(obj)], project_dir)
        console.print(f"[green]{src.stem}.o[/green] = {obj.stat().st_size} байт")
        extra_asm_objs.append(obj)

    src_dir = project_dir / "src"
    include_dirs = _collect_include_dirs(project_dir, src_dir, build_cfg.get("include", []))
    kernel_o = _compile_c(zig, zig_frontend, cxx_flags, project_dir, build_dir,
                          build_cfg.get("sources", []), include_dirs)

    linker = project_dir / build_cfg["linker"]
    entry = build_cfg.get("entry", "kernel_main")
    kernel_elf = _link_elf(zig, zig_frontend, project_dir, build_dir,
                           kernel_o, extra_asm_objs, linker, entry)

    kernel_bin = build_dir / "kernel.bin"
    kernel_bin.write_bytes(elf_to_binary(kernel_elf))
    console.print(f"[green]kernel.bin[/green] = {kernel_bin.stat().st_size} байт")

    img = project_dir / build_cfg.get("output", f"build/{name}.img")
    img.parent.mkdir(parents=True, exist_ok=True)
    target = 1440 * 1024
    data = boot_bin.read_bytes() + kernel_bin.read_bytes()
    if len(data) > target:
        raise RuntimeError(f"Образ больше {target} байт: {len(data)}")
    data += b"\x00" * (target - len(data))
    img.write_bytes(data)
    console.print(f"[green]Образ[/green] {img} ({img.stat().st_size} байт)")
    return img


def _build_elf(project_dir: Path, build_dir: Path, cfg: dict, name: str,
               nasm: str, zig: str, zig_frontend: str, cxx_flags: list[str],
               make_iso: bool) -> Path:
    build_cfg = cfg["build"]

    asm_files = build_cfg.get("asm", [])
    if not asm_files:
        raise RuntimeError("В [build].asm нет ни одного файла")

    # Все asm — elf32 (multiboot.asm с заголовком и _start + опционально isr.asm)
    extra_asm_objs: list[Path] = []
    for rel in asm_files:
        src = project_dir / rel
        obj = build_dir / f"{src.stem}.o"
        _run([nasm, "-f", "elf32", str(src), "-o", str(obj)], project_dir)
        console.print(f"[green]{src.stem}.o[/green] = {obj.stat().st_size} байт")
        extra_asm_objs.append(obj)

    src_dir = project_dir / "src"
    include_dirs = _collect_include_dirs(project_dir, src_dir, build_cfg.get("include", []))
    kernel_o = _compile_c(zig, zig_frontend, cxx_flags, project_dir, build_dir,
                          build_cfg.get("sources", []), include_dirs)

    linker = project_dir / build_cfg["linker"]
    entry = build_cfg.get("entry", "_start")
    kernel_elf = _link_elf(zig, zig_frontend, project_dir, build_dir,
                           kernel_o, extra_asm_objs, linker, entry)

    if not make_iso:
        return kernel_elf

    iso = _make_iso(project_dir, build_dir, name, kernel_elf)
    console.print(f"[green]ISO[/green] {iso} ({iso.stat().st_size} байт)")
    return iso


def _make_iso(project_dir: Path, build_dir: Path, name: str, kernel_elf: Path) -> Path:
    iso_dir = build_dir / "iso"
    boot_dir = iso_dir / "boot"
    grub_dir = boot_dir / "grub"
    grub_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(kernel_elf, boot_dir / "kernel.elf")

    (grub_dir / "grub.cfg").write_text(
        "set timeout=0\n"
        "set default=0\n"
        "\n"
        f'menuentry "{name}" {{\n'
        "    multiboot /boot/kernel.elf\n"
        "    boot\n"
        "}\n",
        encoding="utf-8",
    )

    iso = build_dir / f"{name}.iso"

    # 1) grub-mkrescue в PATH
    grub = shutil.which("grub-mkrescue")
    if grub:
        _run([grub, "-o", str(iso), str(iso_dir)], project_dir)
        return iso

    # 2) через WSL
    wsl = shutil.which("wsl.exe") or shutil.which("wsl")
    if wsl:
        def to_wsl(p: Path) -> str:
            s = str(p.resolve())
            if len(s) > 1 and s[1] == ":":
                return f"/mnt/{s[0].lower()}{s[2:].replace(chr(92), '/')}"
            return s.replace("\\", "/")

        _run([wsl, "grub-mkrescue", "-o", to_wsl(iso), to_wsl(iso_dir)], project_dir)
        return iso

    raise RuntimeError(
        "Не найден grub-mkrescue. Для boot = \"grub\" он нужен в PATH или в WSL. "
        "Используй boot = \"multiboot\" и QEMU -kernel без GRUB."
    )


# ---------- Точка входа ----------

def build(project_dir: Path) -> Path:
    cfg = load_config(project_dir)
    project_cfg = cfg["project"]
    build_cfg = cfg["build"]
    name = project_cfg["name"]
    boot = project_cfg.get("boot", "mbr")

    build_dir = project_dir / "build"
    build_dir.mkdir(exist_ok=True)

    nasm = find_tool("nasm")
    zig = find_tool("zig")

    lang = project_cfg.get("lang", "c")
    zig_frontend = "c++" if lang == "cpp" else "cc"
    cxx_flags = ["-fno-exceptions", "-fno-rtti", "-std=c++20"] if lang == "cpp" else []

    src_dir = project_dir / "src"
    _warn_unlisted(project_dir, src_dir, build_cfg.get("sources", []))

    if boot == "mbr":
        return _build_mbr(project_dir, build_dir, cfg, name,
                          nasm, zig, zig_frontend, cxx_flags)
    if boot == "multiboot":
        return _build_elf(project_dir, build_dir, cfg, name,
                          nasm, zig, zig_frontend, cxx_flags, make_iso=False)
    if boot == "grub":
        return _build_elf(project_dir, build_dir, cfg, name,
                          nasm, zig, zig_frontend, cxx_flags, make_iso=True)

    raise RuntimeError(f"Неизвестный boot = \"{boot}\". Допустимо: mbr, multiboot, grub.")