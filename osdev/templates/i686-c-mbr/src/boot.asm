; boot.asm — MBR-загрузчик для i686
; Читает KERNEL_SECTORS секторов ядра по адресу 0x10000, по одному сектору
; за раз через INT 13h AH=42h (Extended Read, LBA).
;
; KERNEL_SECTORS передаётся из build.py через nasm -d KERNEL_SECTORS=<N>

BITS 16
ORG 0x7C00

%ifndef KERNEL_SECTORS
%define KERNEL_SECTORS 32
%endif

KERNEL_LINEAR equ 0x10000
KERNEL_SEG    equ (KERNEL_LINEAR >> 4)      ; 0x1000

start:
    cli
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7C00
    mov [boot_drive], dl

    mov word [remaining], KERNEL_SECTORS
    mov word [cur_seg], KERNEL_SEG
    mov dword [dap_lba], 1
    mov dword [dap_lba+4], 0

read_loop:
    mov ax, [remaining]
    test ax, ax
    jz read_done

    ; каждый раз обновляем DAP
    mov word [dap_count], 1
    mov bx, [cur_seg]
    mov [dap_seg], bx
    mov word [dap_off], 0

    mov si, dap
    mov dl, [boot_drive]
    mov ah, 0x42
    int 0x13
    jc disk_error

    dec word [remaining]
    add word [cur_seg], 32          ; 512 байт = 32 параграфа
    add dword [dap_lba], 1          ; <-- ЭТО БЫЛО ПРОПУЩЕНО
    jmp read_loop

read_done:
    in al, 0x92
    or al, 2
    out 0x92, al

    lgdt [gdt_descriptor]
    mov eax, cr0
    or eax, 1
    mov cr0, eax
    jmp 0x08:protected_mode

disk_error:
    mov si, err_msg
    call print
    jmp $
print:
    lodsb
    or al, al
    jz .done
    mov ah, 0x0E
    int 0x10
    jmp print
.done:
    ret

boot_drive db 0
remaining  dw 0
cur_seg    dw 0
err_msg    db "disk error", 0

align 4
dap:
    db 0x10
    db 0
dap_count: dw 1
dap_off:   dw 0
dap_seg:   dw 0
dap_lba:   dq 0

gdt_start:
    dq 0
gdt_code:
    dw 0xFFFF, 0x0000
    db 0x00, 10011010b, 11001111b, 0x00
gdt_data:
    dw 0xFFFF, 0x0000
    db 0x00, 10010010b, 11001111b, 0x00
gdt_end:
gdt_descriptor:
    dw gdt_end - gdt_start - 1
    dd gdt_start

BITS 32
protected_mode:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov esp, 0x90000
    jmp KERNEL_LINEAR

times 510-($-$$) db 0
dw 0xAA55