#include <stdint.h>

#define VGA ((volatile uint16_t *)0xB8000)
#define WHITE_ON_BLACK 0x0F

static void clear_screen(void) {
    for (int i = 0; i < 80 * 25; i++)
        VGA[i] = (WHITE_ON_BLACK << 8) | ' ';
}

static void puts_at(int row, int col, const char *s) {
    int i = row * 80 + col;
    while (*s)
        VGA[i++] = (WHITE_ON_BLACK << 8) | (uint8_t)*s++;
}

void kernel_main(void) {
    clear_screen();
    puts_at(0, 0, "Hello from osdev!");
    puts_at(2, 0, "i686, protected mode, C kernel.");
    for (;;) __asm__ volatile("hlt");
}