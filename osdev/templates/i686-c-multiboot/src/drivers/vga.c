#include "vga.h"

#define VGA_WIDTH  80
#define VGA_HEIGHT 25
#define VGA_MEM    ((volatile uint16_t *)0xB8000)

static int cursor_row = 0;
static int cursor_col = 0;
static uint8_t current_color = 0x07;

static uint16_t entry(char c, uint8_t color) {
    return (uint16_t)((uint16_t)color << 8 | (uint8_t)c);
}

static void scroll(void) {
    for (int i = 0; i < (VGA_HEIGHT - 1) * VGA_WIDTH; i++)
        VGA_MEM[i] = VGA_MEM[i + VGA_WIDTH];
    for (int i = (VGA_HEIGHT - 1) * VGA_WIDTH; i < VGA_HEIGHT * VGA_WIDTH; i++)
        VGA_MEM[i] = entry(' ', current_color);
    cursor_row = VGA_HEIGHT - 1;
}

void vga_init(void) {
    cursor_row = 0;
    cursor_col = 0;
    current_color = 0x07;
    vga_clear();
}

void vga_clear(void) {
    for (int i = 0; i < VGA_WIDTH * VGA_HEIGHT; i++)
        VGA_MEM[i] = entry(' ', current_color);
    cursor_row = 0;
    cursor_col = 0;
}

void vga_set_color(uint8_t fg, uint8_t bg) {
    current_color = (uint8_t)((bg << 4) | (fg & 0x0F));
}

void vga_putc(char c) {
    if (c == '\n') {
        cursor_col = 0;
        cursor_row++;
    } else if (c == '\r') {
        cursor_col = 0;
    } else if (c == '\t') {
        cursor_col = (cursor_col + 4) & ~3;
        if (cursor_col >= VGA_WIDTH) { cursor_col = 0; cursor_row++; }
    } else if (c == '\b') {
        if (cursor_col > 0) cursor_col--;
        else if (cursor_row > 0) { cursor_row--; cursor_col = VGA_WIDTH - 1; }
        VGA_MEM[cursor_row * VGA_WIDTH + cursor_col] = entry(' ', current_color);
    } else {
        VGA_MEM[cursor_row * VGA_WIDTH + cursor_col] = entry(c, current_color);
        cursor_col++;
        if (cursor_col >= VGA_WIDTH) { cursor_col = 0; cursor_row++; }
    }
    if (cursor_row >= VGA_HEIGHT) scroll();
}

void vga_puts(const char *s) {
    while (*s) vga_putc(*s++);
}