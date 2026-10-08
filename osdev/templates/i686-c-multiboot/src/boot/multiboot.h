#ifndef MULTIBOOT_H
#define MULTIBOOT_H

#include <stdint.h>

typedef struct {
    uint32_t flags;
    uint32_t mem_lower;
    uint32_t mem_upper;
    uint32_t boot_device;
    uint32_t cmdline;
    uint32_t mods_count;
    uint32_t mods_addr;
    uint32_t syms[4];
    uint32_t mmap_length;
    uint32_t mmap_addr;
} multiboot_info_t;

#define MB_INFO_MEMORY   (1u << 0)
#define MB_INFO_BOOTDEV  (1u << 1)
#define MB_INFO_CMDLINE  (1u << 2)
#define MB_INFO_MODS     (1u << 3)
#define MB_INFO_MMAP     (1u << 6)

#endif