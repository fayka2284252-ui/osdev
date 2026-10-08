#include <stdint.h>
#include "vga.h"
#include "multiboot.h"

static void print_dec(uint32_t v) {
    char buf[12];
    int i = 0;
    if (v == 0) { vga_putc('0'); return; }
    while (v) { buf[i++] = (char)('0' + (v % 10)); v /= 10; }
    while (i--) vga_putc(buf[i]);
}

void kernel_main(multiboot_info_t *mb) {
    vga_init();

    vga_set_color(VGA_LIGHT_GREEN, VGA_BLACK);
    vga_puts("Welcome to your OS!\n");
    vga_puts("Booted via Multiboot (no MBR, no int 13h).\n\n");

    vga_set_color(VGA_LIGHT_GREY, VGA_BLACK);

    if (mb->flags & MB_INFO_MEMORY) {
        vga_puts("mem_lower: ");
        print_dec(mb->mem_lower);
        vga_puts(" KiB\n");
        vga_puts("mem_upper: ");
        print_dec(mb->mem_upper);
        vga_puts(" KiB\n");
    } else {
        vga_puts("Multiboot did not provide memory info.\n");
    }

    vga_puts("\nKernel is running. Edit src/kernel/kernel.c to continue.\n");

    for (;;) __asm__ volatile("hlt");
}