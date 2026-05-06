# Silicon Validation & Embedded C — Complete Learning Guide
## From Zero to Production-Ready Engineer

---

## How to Use This Guide

This guide is structured as a **progressive learning path**. Each chapter builds on the previous one. Work through it in order if you are new to the domain. If you have experience, use the table of contents to jump to specific topics.

Each chapter contains:
- **Concept explanation** — the theory behind the topic
- **Worked examples** — real code or diagrams
- **Practice exercises** — problems to solve on your own
- **Interview questions** — typical questions at L4–L7 level
- **Common mistakes** — errors that beginners make and how to avoid them

---

## Table of Contents

### Part A — Foundations
1. [How a Chip Goes from Idea to Silicon](#chapter-1-how-a-chip-goes-from-idea-to-silicon)
2. [Digital Logic and RTL Fundamentals](#chapter-2-digital-logic-and-rtl-fundamentals)
3. [C Language Deep Dive for Embedded Engineers](#chapter-3-c-language-deep-dive-for-embedded-engineers)
4. [Memory Architecture in Embedded Systems](#chapter-4-memory-architecture-in-embedded-systems)
5. [Interrupts, Exceptions, and the NVIC](#chapter-5-interrupts-exceptions-and-the-nvic)

### Part B — Pre-Silicon Validation
6. [SystemVerilog and UVM Testbench Architecture](#chapter-6-systemverilog-and-uvm-testbench-architecture)
7. [Coverage Methodology — Code and Functional](#chapter-7-coverage-methodology--code-and-functional)
8. [Assertion-Based Verification with SVA](#chapter-8-assertion-based-verification-with-sva)
9. [Formal Verification Fundamentals](#chapter-9-formal-verification-fundamentals)
10. [Emulation Platform Deep Dive](#chapter-10-emulation-platform-deep-dive)

### Part C — IP Test Engineering
11. [Writing Test Plans for Hardware IPs](#chapter-11-writing-test-plans-for-hardware-ips)
12. [CAN / CAN-FD Protocol and Validation](#chapter-12-can--can-fd-protocol-and-validation)
13. [Serial Protocol IPs — SPI, I2C, UART](#chapter-13-serial-protocol-ips--spi-i2c-uart)
14. [High-Speed Interfaces — USB, PCIe, Ethernet](#chapter-14-high-speed-interfaces--usb-pcie-ethernet)
15. [Memory Controller Validation — DDR/LPDDR](#chapter-15-memory-controller-validation--ddrlpddr)

### Part D — Post-Silicon Validation
16. [Silicon Bring-Up Methodology](#chapter-16-silicon-bring-up-methodology)
17. [Debug Techniques on Physical Silicon](#chapter-17-debug-techniques-on-physical-silicon)
18. [Characterisation and PVT Testing](#chapter-18-characterisation-and-pvt-testing)
19. [Compliance and Certification Testing](#chapter-19-compliance-and-certification-testing)

### Part E — Embedded C Mastery
20. [Embedded C Patterns and Idioms](#chapter-20-embedded-c-patterns-and-idioms)
21. [Writing Hardware Abstraction Layers (HAL)](#chapter-21-writing-hardware-abstraction-layers-hal)
22. [RTOS Fundamentals — FreeRTOS](#chapter-22-rtos-fundamentals--freertos)
23. [MISRA C:2012 — Rules, Rationale, and Tools](#chapter-23-misra-c2012--rules-rationale-and-tools)
24. [Unit Testing Embedded Code on Host](#chapter-24-unit-testing-embedded-code-on-host)

### Part F — Professional Skills
25. [Requirements Engineering for Embedded Projects](#chapter-25-requirements-engineering-for-embedded-projects)
26. [Bug Management and Root Cause Analysis](#chapter-26-bug-management-and-root-cause-analysis)
27. [CI/CD for Embedded and Silicon Projects](#chapter-27-cicd-for-embedded-and-silicon-projects)
28. [Interview Preparation — 60 Q&A](#chapter-28-interview-preparation--60-qa)

---

## PART A — FOUNDATIONS

---

## Chapter 1: How a Chip Goes from Idea to Silicon

### 1.1 The VLSI Design and Verification Flow

Understanding where your work fits in the larger picture is essential before diving into any specific skill.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  SPECIFICATION PHASE                                                     │
│    Architecture definition → micro-architecture spec → register map      │
│    Output: Architecture Specification Document (ASD)                     │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  DESIGN PHASE (RTL)                                                      │
│    VHDL / SystemVerilog RTL coding                                       │
│    RTL Lint (SpyGlass) — coding errors, latches, multi-driver nets       │
│    CDC (Clock Domain Crossing) analysis                                  │
│    Output: Clean RTL, lint-free, CDC-clean                               │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  VERIFICATION PHASE                                                      │
│    Testbench development (UVM / directed C/C++)                          │
│    Simulation (VCS, Xcelium, Questasim)                                  │
│    Formal verification (JasperGold, VC Formal)                           │
│    Emulation / FPGA prototyping                                          │
│    Coverage closure → sign-off                                           │
│    Output: Verification Closure Report (VCR)                             │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  SYNTHESIS & IMPLEMENTATION                                              │
│    Logic synthesis (Design Compiler, Genus)                              │
│    Gate-level simulation (GLS)                                           │
│    Place and route (ICC2, Innovus)                                       │
│    Static Timing Analysis — STA (PrimeTime, Tempus)                      │
│    DRC / LVS physical verification                                       │
│    Output: GDSII (the chip "blueprint" sent to fab)                      │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  TAPE-OUT  →  FAB (TSMC, Samsung, GlobalFoundries)                       │
│    Wafer fabrication: 4–12 weeks                                         │
│    Wafer probe: electrical test on wafer                                 │
│    Dicing, packaging, final test                                         │
│    Output: Engineering Sample (ES0) silicon                              │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────┐
│  POST-SILICON VALIDATION                                                 │
│    Silicon bring-up → IP validation → system test                        │
│    Characterisation (PVT corners)                                        │
│    Compliance (CAN, USB, PCIe…)                                          │
│    AEC-Q100 qualification (automotive)                                   │
│    Output: Product Qualification Report (PQR), production release        │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Roles and What They Do

| Role | Phase | Daily Work |
|---|---|---|
| RTL Design Engineer | Design | Write synthesisable SystemVerilog/VHDL; peer review RTL |
| DV Engineer | Verification | UVM testbenches, coverage closure, formal properties |
| Silicon Validation Engineer | Post-silicon | Bring-up scripts, lab debug, compliance test execution |
| Embedded SW Engineer | All phases | Firmware/driver for IP validation, RTOS bringup |
| Physical Design Engineer | Implementation | Floorplan, P&R, timing closure |
| DFT Engineer | Design/Test | Scan insertion, ATPG, MBIST |

### 1.3 Practice Exercise

> Draw the flow for a hypothetical CAN controller IP, naming the artifacts produced at each stage. Who is responsible for each artifact?

### 1.4 Interview Questions

**Q1**: What is the difference between DV (Design Verification) and SiVal (Silicon Validation)?
> DV works on RTL/simulation before tape-out — controllability and observability are unlimited. SiVal works on physical silicon — stimuli must go through real interfaces and observation is limited to test pins, JTAG, and trace buffers.

**Q2**: Why is a bug found post-silicon more expensive than one found in simulation?
> A post-silicon bug may require a chip re-spin (mask changes) costing $500k–$5M and 3–6 months of delay. A simulation bug is fixed with an RTL edit in minutes.

---

## Chapter 2: Digital Logic and RTL Fundamentals

### 2.1 Combinational vs Sequential Logic

**Combinational logic**: output depends only on current inputs — no memory.

```
Inputs → [Logic Gates] → Output
AND, OR, NOT, XOR, MUX, decoder, encoder, priority encoder
```

**Sequential logic**: output depends on current inputs AND past state — has memory (flip-flops, registers).

```
        ┌─────────┐
D ─────►│  D FF   │─────► Q
        │         │
CLK ───►│  edge   │
        │triggered│
RST ───►│         │
        └─────────┘
```

### 2.2 Synchronous Design Rules

Every professional digital design follows these rules:

```
Rule 1: All flip-flops clocked by the same clock (or synchronised clocks).
Rule 2: No combinational feedback loops.
Rule 3: Reset is synchronous (preferred) or asynchronous with synchronous release.
Rule 4: Signals crossing clock domains must use synchronisers.
Rule 5: All outputs registered — no glitchy combinational outputs to chip pins.
```

### 2.3 Clock Domain Crossing (CDC)

CDC is one of the most common sources of silicon bugs. When a signal produced in clock domain A is sampled in clock domain B:

```
Domain A (100 MHz)              Domain B (50 MHz)
    ┌─────┐                         ┌─────┐
    │ FF  │──── UNSYNCHRONISED ────►│ FF  │  ← METASTABILITY RISK!
    └─────┘                         └─────┘

CORRECT — use a 2-stage synchroniser:
    ┌─────┐      ┌─────┐      ┌─────┐
    │ FF  │────► │ FF  │────► │ FF  │  ← stable output
    └─────┘      └─────┘      └─────┘
    Dom A         Dom B         Dom B
```

**Metastability**: when a flip-flop's setup or hold time is violated, its output can settle to an indeterminate voltage level between 0 and 1. The two-stage synchroniser gives the metastable signal time to resolve before being used.

### 2.4 Finite State Machine (FSM) Design

The CAN bus protocol is best understood as a layered set of FSMs. Here is the error state machine from ISO 11898-1:

```
          ┌─────────────────────────────────────────────┐
          │                                             │
          ▼                                             │
  ┌──────────────┐   TEC > 127 OR         ┌──────────────┐
  │   ERROR      │   REC > 127            │   ERROR      │
  │   ACTIVE     │──────────────────────► │  PASSIVE     │
  │  (TEC≤127,   │                        │  (TEC>127 OR │
  │   REC≤127)   │ ◄────────────────────  │   REC>127)   │
  └──────────────┘  TEC≤127, REC≤127      └──────┬───────┘
                                                  │
                                           TEC > 255
                                                  │
                                          ┌───────▼──────┐
                                          │   BUS-OFF    │
                                          │  (TEC > 255) │
                                          └───────┬──────┘
                                                  │
                                     128 × 11 recessive bits
                                                  │
                                          back to ERROR ACTIVE
```

### 2.5 Practice Exercise

> Implement the CAN error state machine in C using an enum and a state transition function. Write a unit test using Unity to verify: (a) TEC > 127 causes transition to ERROR PASSIVE, (b) TEC > 255 causes BUS-OFF.

---

## Chapter 3: C Language Deep Dive for Embedded Engineers

### 3.1 Why C Dominates Embedded Systems

C is used in embedded systems because:
- **Predictable memory layout** — no garbage collector, known stack/heap usage
- **Direct hardware access** — pointer arithmetic maps to physical addresses
- **Deterministic execution** — no JIT compilation, no dynamic dispatch overhead
- **Portability** — runs on any architecture with a C compiler
- **Tool chain maturity** — GCC/Clang/IAR/ARMCC all support C99/C11

### 3.2 Data Types and Sizes — The Trap

```c
/* DO NOT DO THIS in embedded code — sizes are platform-dependent */
int    x;       /* 16-bit on AVR, 32-bit on ARM Cortex-M */
long   y;       /* 32-bit on most 32-bit MCUs, 64-bit on 64-bit Linux */
char   c;       /* signed or unsigned? implementation-defined! */

/* ALWAYS DO THIS — from <stdint.h> */
#include <stdint.h>

uint8_t   a;    /* exactly 8 bits, unsigned,  always */
int8_t    b;    /* exactly 8 bits, signed,    always */
uint16_t  c;    /* exactly 16 bits, unsigned, always */
int16_t   d;    /* exactly 16 bits, signed,   always */
uint32_t  e;    /* exactly 32 bits, unsigned, always */
uint64_t  f;    /* exactly 64 bits, unsigned, always */
```

### 3.3 Pointers — The Core of Embedded C

A pointer stores the **memory address** of another variable.

```c
uint32_t value = 0xDEADBEEF;
uint32_t *ptr  = &value;       /* ptr holds the address of value */

printf("Address : %p\n", (void *)ptr);       /* 0x2000_0010 (example) */
printf("Value   : 0x%08X\n", *ptr);          /* 0xDEADBEEF */

*ptr = 0xCAFEBABE;             /* write through pointer */
printf("Now     : 0x%08X\n", value);         /* 0xCAFEBABE */
```

**Hardware register access using pointer**:

```c
/* Access a hardware register at a fixed address */
#define GPIOA_ODR   (*((volatile uint32_t *)0x48000014UL))

/* Set bit 5 (LED on PA5) */
GPIOA_ODR |= (1UL << 5);

/* Clear bit 5 */
GPIOA_ODR &= ~(1UL << 5);
```

The `volatile` keyword is critical — without it, the compiler may:
- Cache the value in a register and never re-read from hardware
- Optimise away writes it thinks have no effect
- Reorder memory accesses

### 3.4 Structs for Hardware Register Maps

Rather than individual `#define` macros for every register, use a struct that mirrors the hardware memory layout:

```c
/* Hardware register struct — fields at exact byte offsets */
typedef struct {
    volatile uint32_t MODER;    /* 0x00 — Mode register */
    volatile uint32_t OTYPER;   /* 0x04 — Output type register */
    volatile uint32_t OSPEEDR;  /* 0x08 — Output speed register */
    volatile uint32_t PUPDR;    /* 0x0C — Pull-up/pull-down register */
    volatile uint32_t IDR;      /* 0x10 — Input data register (read-only) */
    volatile uint32_t ODR;      /* 0x14 — Output data register */
    volatile uint32_t BSRR;     /* 0x18 — Bit set/reset register */
    volatile uint32_t LCKR;     /* 0x1C — Configuration lock register */
    volatile uint32_t AFR[2];   /* 0x20 — Alternate function registers */
} GPIO_TypeDef;

/* Map struct to hardware base address */
#define GPIOA   ((GPIO_TypeDef *)0x48000000UL)
#define GPIOB   ((GPIO_TypeDef *)0x48000400UL)
#define GPIOC   ((GPIO_TypeDef *)0x48000800UL)

/* Set PA5 as output (MODER bits [11:10] = 01) */
GPIOA->MODER &= ~(3UL << (5U * 2U));   /* clear bits */
GPIOA->MODER |=  (1UL << (5U * 2U));   /* set output mode */

/* Toggle PA5 using atomic BSRR register */
GPIOA->BSRR = (1UL << 5U);             /* set */
GPIOA->BSRR = (1UL << (5U + 16U));     /* reset (bits [31:16]) */
```

### 3.5 Bit-Fields in Structs

```c
/* Describe a CAN message buffer using a bit-field struct */
typedef struct {
    uint32_t RTR      : 1;   /* Remote Transmission Request */
    uint32_t IDE      : 1;   /* Identifier Extension */
    uint32_t EXID     : 18;  /* Extended Identifier [17:0] */
    uint32_t STID     : 11;  /* Standard Identifier */
    uint32_t TXRQ     : 1;   /* Transmit Request */
} CAN_TxMailBox_IR_t;

/* WARNING: bit-field layout is implementation-defined in C standard.
   For portability, prefer explicit shift/mask macros for hardware registers.
   Use bit-fields for in-memory data structures only. */
```

### 3.6 Function Pointers and Callbacks

Callbacks are how embedded drivers notify application code of events without the driver knowing anything about the application:

```c
/* Define a callback type */
typedef void (*UART_RxCallback_t)(uint8_t byte, void *user_data);

/* Driver stores the callback */
static UART_RxCallback_t g_rx_cb   = NULL;
static void             *g_rx_user = NULL;

/* Registration function */
void UART_RegisterRxCallback(UART_RxCallback_t cb, void *user_data) {
    g_rx_cb   = cb;
    g_rx_user = user_data;
}

/* Called from ISR when byte received */
void UART1_IRQHandler(void) {
    uint8_t byte = UART1->RDR & 0xFFU;
    if (g_rx_cb != NULL) {
        g_rx_cb(byte, g_rx_user);   /* invoke application callback */
    }
}

/* Application code */
static char g_rx_buffer[64];
static uint32_t g_rx_count = 0;

static void my_rx_handler(uint8_t byte, void *user_data) {
    char *buf = (char *)user_data;
    buf[g_rx_count++] = (char)byte;
}

int main(void) {
    UART_Init(1U, 115200U);
    UART_RegisterRxCallback(my_rx_handler, g_rx_buffer);
    /* ... */
}
```

### 3.7 Stack vs Heap — Embedded Rules

```
┌─────────────────────────────────────────────────────────┐
│  Embedded Memory Model (ARM Cortex-M)                   │
│                                                         │
│  0x2001_FFFF  ┌─────────────┐  ← Stack top             │
│               │    Stack    │  grows downward           │
│               │  (local     │                           │
│               │  variables, │                           │
│               │  func args) │                           │
│               ├─────────────┤  ← Stack pointer         │
│               │    FREE     │                           │
│               ├─────────────┤  ← Heap end              │
│               │    Heap     │  grows upward             │
│               │  (malloc,   │  ← AVOID in production   │
│               │  calloc)    │                           │
│               ├─────────────┤  ← Heap start            │
│               │    BSS      │  zero-initialised globals │
│               ├─────────────┤                           │
│               │    Data     │  initialised globals      │
│  0x2000_0000  └─────────────┘                           │
│                                                         │
│  0x0800_0000  ┌─────────────┐                           │
│               │    Text     │  code (Flash)             │
│               │  (code +    │                           │
│               │  rodata)    │                           │
│  0x0800_0000  └─────────────┘                           │
└─────────────────────────────────────────────────────────┘

Rules for safety-critical embedded code:
  1. Never use malloc/free in production — use static pools
  2. Know your stack depth — use worst-case analysis or RTOS watermarking
  3. Globals must be initialised explicitly (do not rely on zero-init in BSS for hardware-backed memory)
  4. Avoid recursion — depth is not deterministic
```

### 3.8 Common C Mistakes in Embedded Code

```c
/* MISTAKE 1: Integer overflow */
uint8_t count = 255U;
count++;           /* wraps to 0, not 256 — silent overflow */

/* FIX: check before incrementing */
if (count < 255U) { count++; }

/* MISTAKE 2: Signed/unsigned comparison */
int8_t  temp   = -5;
uint8_t sensor = 10U;
if (temp < sensor) { ... }   /* WRONG: temp is promoted to uint8, -5 wraps to 251 */

/* FIX: cast explicitly */
if ((int16_t)temp < (int16_t)sensor) { ... }

/* MISTAKE 3: Missing volatile on ISR-shared variable */
static bool g_flag = false;   /* WRONG */
void ISR(void) { g_flag = true; }
while (!g_flag) { ... }       /* compiler may cache g_flag, never re-reads */

/* FIX: */
static volatile bool g_flag = false;

/* MISTAKE 4: Reading-modifying-writing a hardware register non-atomically */
/* Between the read and the write, an interrupt could change the register */
GPIOA->ODR |= (1UL << 5U);   /* not atomic on multi-core / with interrupts */

/* FIX: use set/reset register (atomic in hardware) */
GPIOA->BSRR = (1UL << 5U);   /* atomic set — single write, no RMW */

/* MISTAKE 5: Array out-of-bounds (undefined behaviour) */
uint8_t buf[8];
for (uint8_t i = 0U; i <= 8U; i++) {   /* BUG: i reaches 8, buf[8] is OOB */
    buf[i] = 0U;
}

/* FIX: */
for (uint8_t i = 0U; i < 8U; i++) {
    buf[i] = 0U;
}
```

### 3.9 Practice Exercises

1. Write a function `uint32_t read_field(uint32_t reg, uint8_t pos, uint8_t width)` that extracts a bit field from a register value.
2. Write a function `void write_field(volatile uint32_t *reg, uint8_t pos, uint8_t width, uint32_t val)` that writes a field into a register.
3. Explain why `(1 << 31)` is undefined behaviour in C99 and how to fix it.

---

## Chapter 4: Memory Architecture in Embedded Systems

### 4.1 ARM Cortex-M Memory Map

```
Address Range         Region                      Description
─────────────────────────────────────────────────────────────
0xFFFF_FFFF           ┐
  to                  │  Vendor specific          External / custom
0xE010_0000           ┘
─────────────────────────────────────────────────────────────
0xE000_0000           ┐
  to                  │  Private Peripheral Bus   NVIC, SysTick, ITM, DWT
0xE000_0FFF           ┘
─────────────────────────────────────────────────────────────
0xA000_0000           ┐
  to                  │  External Device          External peripherals
0x9FFF_FFFF           ┘
─────────────────────────────────────────────────────────────
0x6000_0000           ┐
  to                  │  External RAM             Off-chip SRAM/SDRAM
0x5FFF_FFFF           ┘
─────────────────────────────────────────────────────────────
0x4000_0000           ┐
  to                  │  Peripheral               On-chip peripherals (AHB/APB)
0x3FFF_FFFF           ┘  (device memory — no caching, no reordering)
─────────────────────────────────────────────────────────────
0x2000_0000           ┐
  to                  │  SRAM                     On-chip SRAM (bit-band alias too)
0x1FFF_FFFF           ┘
─────────────────────────────────────────────────────────────
0x0000_0000           ┐
  to                  │  Code                     Flash / ROM (execute-in-place)
0x1FFF_FFFF           ┘
─────────────────────────────────────────────────────────────
```

### 4.2 Cache Coherency Issues

When a DMA engine writes to DRAM, the CPU cache may serve stale data:

```
DMA writes 1024 bytes to 0x2000_0000
          ↓
DRAM is updated
          ↓
CPU reads from 0x2000_0000
          ↓
Cache returns old data! ← BUG

Fix 1: Invalidate cache before CPU reads DMA output
    SCB_InvalidateDCache_by_Addr((uint32_t *)buf, 1024);

Fix 2: Use non-cacheable memory region for DMA buffers
    __attribute__((section(".dma_buffers"))) 
    __attribute__((aligned(32)))
    static uint8_t dma_buf[1024];
    /* linker script maps .dma_buffers to non-cacheable MPU region */

Fix 3: Mark DMA destination as volatile
    volatile uint8_t dma_buf[1024];
```

### 4.3 Memory Protection Unit (MPU)

The MPU enforces access permissions at runtime, preventing stack overflow from corrupting code, and ISR stacks from accessing application data:

```c
/* Configure MPU region for read-only Flash */
MPU->RNR  = 0U;                                /* region 0 */
MPU->RBAR = 0x08000000UL;                      /* Flash base */
MPU->RASR = MPU_RASR_ENABLE_Msk
          | (0x1BUL << MPU_RASR_SIZE_Pos)      /* 512 KB */
          | (0x06UL << MPU_RASR_AP_Pos)        /* RO from priv+unpriv */
          | MPU_RASR_C_Msk                     /* cacheable */
          | MPU_RASR_B_Msk;                    /* bufferable */

MPU->CTRL = MPU_CTRL_ENABLE_Msk | MPU_CTRL_PRIVDEFENA_Msk;
__DSB(); __ISB();   /* force memory barrier before MPU is active */
```

---

## Chapter 5: Interrupts, Exceptions, and the NVIC

### 5.1 ARM Cortex-M Exception Model

```
Priority   Exception                      Vector Table Offset
────────   ────────────────────────────   ───────────────────
-3         Reset                          0x04
-2         NMI (Non-Maskable Interrupt)   0x08
-1         HardFault                      0x0C
 0         MemManage (MPU fault)          0x10
 1         BusFault                       0x14
 2         UsageFault                     0x18
3–15       Reserved                       0x1C–0x2C
16         SysTick                        0x3C
17–...     External IRQs (NVIC)           0x40+
```

Lower number = higher priority (Cortex-M uses lower value = higher priority).

### 5.2 Writing an Interrupt Service Routine

```c
/* CAN1 TX complete ISR — linked from vector table */
void CAN1_TX_IRQHandler(void) {
    /* Clear the interrupt flag FIRST to prevent re-entry */
    CAN1->TSR |= CAN_TSR_RQCP0_Msk;  /* clear request complete flag */

    /* Read status — was it successful? */
    if ((CAN1->TSR & CAN_TSR_TXOK0_Msk) != 0U) {
        g_tx_complete_count++;
        /* Signal semaphore to unblock waiting task (FreeRTOS) */
        BaseType_t higher_prio_woken = pdFALSE;
        xSemaphoreGiveFromISR(g_tx_sem, &higher_prio_woken);
        portYIELD_FROM_ISR(higher_prio_woken);
    } else {
        g_tx_error_count++;
    }
}

/* ISR rules:
   1. Keep it SHORT — defer processing to task/thread
   2. Never block inside an ISR
   3. Use only ISR-safe RTOS APIs (_FromISR suffix in FreeRTOS)
   4. Clear interrupt flags before processing (prevents re-triggering)
   5. No printf / malloc / floating point in ISR
*/
```

### 5.3 Interrupt Latency Measurement

```c
/* Measure ISR entry latency using DWT cycle counter */
static uint32_t g_irq_entry_cycles;
static uint32_t g_irq_exit_cycles;

void GPIO_IRQHandler(void) {
    g_irq_entry_cycles = DWT->CYCCNT;  /* capture entry time */
    
    /* process */
    GPIOA->ODR ^= (1UL << 5U);        /* toggle LED */
    
    g_irq_exit_cycles = DWT->CYCCNT;
    /* latency = (g_irq_entry_cycles - trigger_cycles) / CPU_freq_Hz */
}

/* Expected latency on Cortex-M4 at 168 MHz: ~12 cycles = ~71 ns */
```

---

## PART B — PRE-SILICON VALIDATION

---

## Chapter 6: SystemVerilog and UVM Testbench Architecture

### 6.1 SystemVerilog for Verification — Key Constructs

```systemverilog
// ── Randomisation ─────────────────────────────────────────────────────────
class CAN_Transaction extends uvm_sequence_item;
    `uvm_object_utils(CAN_Transaction)

    rand bit [28:0] id;         // 29-bit CAN ID (extended)
    rand bit [7:0]  data[];     // variable-length data
    rand bit [3:0]  dlc;        // Data Length Code 0-8
    rand bit        is_ext;     // extended frame flag
    rand bit        is_remote;  // remote frame flag

    // Constraints
    constraint c_dlc_data_size {
        dlc inside {[0:8]};
        data.size() == dlc;
    }
    constraint c_std_id_range {
        if (!is_ext) { id inside {[0:11'h7FF]}; }
    }
    constraint c_no_remote_fd {
        !(is_remote && dlc > 8);
    }
endclass
```

### 6.2 Complete UVM Agent

```systemverilog
// ── Interface ─────────────────────────────────────────────────────────────
interface can_if (input logic clk, rst_n);
    logic        txd;
    logic        rxd;
    logic        tx_en;
    logic [28:0] tx_id;
    logic [7:0]  tx_data [0:7];
    logic [3:0]  tx_dlc;
    logic        tx_valid;
    logic        tx_ready;
    logic        rx_valid;
    logic [28:0] rx_id;
    logic [7:0]  rx_data [0:7];
    logic [3:0]  rx_dlc;

    clocking driver_cb @(posedge clk);
        default input #1 output #1;
        output tx_id, tx_data, tx_dlc, tx_valid;
        input  tx_ready;
    endclocking

    clocking monitor_cb @(posedge clk);
        default input #1;
        input rx_valid, rx_id, rx_data, rx_dlc;
    endclocking
endinterface

// ── Sequencer ─────────────────────────────────────────────────────────────
class CAN_Sequencer extends uvm_sequencer #(CAN_Transaction);
    `uvm_component_utils(CAN_Sequencer)
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
endclass

// ── Driver ────────────────────────────────────────────────────────────────
class CAN_Driver extends uvm_driver #(CAN_Transaction);
    `uvm_component_utils(CAN_Driver)
    virtual can_if vif;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    task run_phase(uvm_phase phase);
        CAN_Transaction tx;
        forever begin
            seq_item_port.get_next_item(tx);
            drive_transaction(tx);
            seq_item_port.item_done();
        end
    endtask

    task drive_transaction(CAN_Transaction tx);
        @(vif.driver_cb);
        vif.driver_cb.tx_id    <= tx.id;
        vif.driver_cb.tx_dlc   <= tx.dlc;
        foreach(tx.data[i]) vif.driver_cb.tx_data[i] <= tx.data[i];
        vif.driver_cb.tx_valid <= 1'b1;
        // Wait for handshake
        do @(vif.driver_cb); while (!vif.driver_cb.tx_ready);
        vif.driver_cb.tx_valid <= 1'b0;
        `uvm_info("CAN_DRV", $sformatf("Sent ID=0x%0X DLC=%0d", tx.id, tx.dlc), UVM_HIGH)
    endtask
endclass

// ── Monitor ───────────────────────────────────────────────────────────────
class CAN_Monitor extends uvm_monitor;
    `uvm_component_utils(CAN_Monitor)
    virtual can_if vif;
    uvm_analysis_port #(CAN_Transaction) ap;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        ap = new("ap", this);
    endfunction

    task run_phase(uvm_phase phase);
        CAN_Transaction rx;
        forever begin
            @(vif.monitor_cb);
            if (vif.monitor_cb.rx_valid) begin
                rx = CAN_Transaction::type_id::create("rx");
                rx.id  = vif.monitor_cb.rx_id;
                rx.dlc = vif.monitor_cb.rx_dlc;
                foreach(rx.data[i]) rx.data[i] = vif.monitor_cb.rx_data[i];
                ap.write(rx);
            end
        end
    endtask
endclass
```

### 6.3 Scoreboard Pattern

```systemverilog
class CAN_Scoreboard extends uvm_scoreboard;
    `uvm_component_utils(CAN_Scoreboard)

    uvm_analysis_imp #(CAN_Transaction, CAN_Scoreboard) exp_port; // expected
    uvm_analysis_imp #(CAN_Transaction, CAN_Scoreboard) got_port; // actual

    CAN_Transaction exp_q[$];
    int pass_count = 0;
    int fail_count = 0;

    function void write_exp(CAN_Transaction t);
        exp_q.push_back(t);
    endfunction

    function void write_got(CAN_Transaction t);
        CAN_Transaction exp;
        if (exp_q.size() == 0) begin
            `uvm_error("SCB", "Unexpected transaction received from DUT")
            fail_count++;
            return;
        end
        exp = exp_q.pop_front();
        if (exp.id !== t.id || exp.dlc !== t.dlc) begin
            `uvm_error("SCB", $sformatf("MISMATCH: exp ID=%0X got ID=%0X", exp.id, t.id))
            fail_count++;
        end else begin
            pass_count++;
        end
    endfunction

    function void report_phase(uvm_phase phase);
        `uvm_info("SCB", $sformatf("PASS=%0d  FAIL=%0d", pass_count, fail_count), UVM_NONE)
        if (fail_count > 0) `uvm_fatal("SCB", "SCOREBOARD FAILURES — TEST FAILED")
    endfunction
endclass
```

### 6.4 UVM Sequences

```systemverilog
// ── Base sequence ─────────────────────────────────────────────────────────
class CAN_BaseSequence extends uvm_sequence #(CAN_Transaction);
    `uvm_object_utils(CAN_BaseSequence)
    int unsigned num_frames;

    function new(string name = "CAN_BaseSequence");
        super.new(name);
        num_frames = 10;
    endfunction

    task body();
        CAN_Transaction tx;
        repeat(num_frames) begin
            tx = CAN_Transaction::type_id::create("tx");
            start_item(tx);
            if (!tx.randomize())
                `uvm_fatal("SEQ", "Randomisation failed")
            finish_item(tx);
        end
    endtask
endclass

// ── Error injection sequence ───────────────────────────────────────────────
class CAN_ErrorInjectSequence extends CAN_BaseSequence;
    `uvm_object_utils(CAN_ErrorInjectSequence)

    task body();
        CAN_Transaction tx;
        // First, send a good frame
        tx = CAN_Transaction::type_id::create("tx");
        start_item(tx);
        void'(tx.randomize() with { dlc == 8; });
        finish_item(tx);
        // Inject a bit error on next frame (via interface force)
        // In practice: use a backdoor or error-injection interface
        `uvm_info("SEQ", "Error injection complete", UVM_MEDIUM)
    endtask
endclass
```

### 6.5 Practice Exercises

1. Write a UVM sequence that sends exactly 100 frames: 50 standard, 50 extended, all with random data.
2. Extend the scoreboard to check data byte correctness, not just ID and DLC.
3. Write a constraint that generates only frames with DLC ∈ {1, 2, 4, 8} (powers of two and 1).

---

## Chapter 7: Coverage Methodology — Code and Functional

### 7.1 Code Coverage Types Explained

```
// Example RTL module — CAN acceptance filter
module can_filter (
    input  logic [28:0] rx_id,
    input  logic        rx_ide,
    input  logic [28:0] filter_id,
    input  logic [28:0] filter_mask,
    input  logic        filter_ide,
    output logic        match
);

    // Line coverage: each line must be executed at least once
    // Branch coverage: each condition must be true AND false at least once
    // Toggle coverage: each net must toggle 0→1 and 1→0

    assign match = (filter_ide == rx_ide) &&         // Branch 1
                   ((rx_id & filter_mask) ==          // Branch 2
                    (filter_id & filter_mask));
endmodule
```

### 7.2 Functional Coverage with Covergroups

```systemverilog
// Functional coverage — designer-defined what matters
covergroup CAN_FrameCoverage @(posedge clk);
    // Cover all DLC values
    cp_dlc: coverpoint tx_dlc {
        bins zero  = {0};
        bins one   = {1};
        bins mid[] = {[2:6]};
        bins seven = {7};
        bins eight = {8};
    }

    // Cover both frame types
    cp_ide: coverpoint tx_ide {
        bins standard = {0};
        bins extended = {1};
    }

    // Cross coverage: every DLC × every frame type
    cx_dlc_ide: cross cp_dlc, cp_ide;

    // Cover all error types
    cp_error: coverpoint error_type {
        bins bit_error  = {3'h1};
        bins stuff_err  = {3'h2};
        bins crc_err    = {3'h3};
        bins form_err   = {3'h4};
        bins ack_err    = {3'h5};
        illegal_bins no_error = {3'h0};  // this should never be "covered"
    }
endgroup
```

### 7.3 Coverage-Driven Test Closure

```
1. Run 1000 random tests
2. Measure coverage: 78% functional, 82% code
3. Generate coverage report — identify uncovered bins:
       - cp_dlc: 'zero' bin (DLC=0) — not hit once!
       - cp_error: 'ack_err' bin — never triggered
4. Write directed tests:
       test_dlc_zero: force DLC=0, observe behaviour
       test_ack_error: disable ACK, expect ack_err frame
5. Re-run: 100% functional, 96% code coverage
6. Sign off
```

---

## Chapter 8: Assertion-Based Verification with SVA

### 8.1 Immediate Assertions

```systemverilog
// Checked every time control reaches this line
always @(posedge clk) begin
    // FIFO must not overflow
    assert (!(fifo_full && wr_en))
        else $error("[%0t] FIFO write when full!", $time);

    // DLC must be legal
    assert (dlc <= 4'h8)
        else $fatal(2, "[%0t] Illegal DLC=%0d", $time, dlc);
end
```

### 8.2 Concurrent Assertions

```systemverilog
// ── Property: request must be followed by ack within 1–4 cycles ──────────
property req_ack_handshake;
    @(posedge clk) disable iff (!rst_n)
    req |-> ##[1:4] ack;
endproperty

// Assertion — failure is an error
assert property (req_ack_handshake)
    else $error("[%0t] ACK not received within 4 cycles of REQ", $time);

// Cover — checks if property was ever exercised
cover property (req_ack_handshake);

// ── Property: no write to full FIFO ──────────────────────────────────────
property no_write_when_full;
    @(posedge clk) disable iff (!rst_n)
    fifo_full |-> !wr_en;
endproperty
assert property (no_write_when_full);

// ── Property: bus-off recovery takes exactly 128 × 11 recessive bits ─────
property bus_off_recovery;
    @(posedge clk) disable iff (!rst_n)
    $rose(bus_off) |-> ##[128*11 : 128*11+10] $fell(bus_off);
endproperty
assert property (bus_off_recovery);
```

### 8.3 Common SVA Operators Quick Reference

| Operator | Meaning | Example |
|---|---|---|
| `\|->` | Overlapping implication | `a \|-> b` — if a then b in same cycle |
| `\|=>` | Non-overlapping implication | `a \|=> b` — if a then b in next cycle |
| `##N` | Delay N cycles | `a ##3 b` — b must be true 3 cycles after a |
| `##[M:N]` | Delay M to N cycles | `a ##[1:4] b` — b within 1 to 4 cycles |
| `[*N]` | Repeat exactly N times | `a[*3]` — a is true for 3 consecutive cycles |
| `[*M:N]` | Repeat M to N times | `a[*1:5]` — a true for 1 to 5 cycles |
| `first_match` | First occurrence of repetition | `first_match(a ##[1:$] b)` |
| `$rose` | Signal went 0→1 | `$rose(req)` |
| `$fell` | Signal went 1→0 | `$fell(ack)` |
| `$stable` | Signal did not change | `$stable(data)` |
| `not` | Negation of property | `not (a ##1 b)` |
| `and` | Both sequences match | `seq1 and seq2` |

---

## Chapter 9: Formal Verification Fundamentals

### 9.1 What Formal Verification Does

Formal verification **mathematically proves** that a property holds for **all possible inputs**, for **all reachable states**. No test vectors needed.

```
Simulation: check property for test A, test B, test C ...
            → incomplete, can miss bugs in untested scenarios

Formal:     prove property holds for ALL inputs, ALL states
            → complete, but computationally harder (state explosion)
```

### 9.2 Formal vs Simulation Comparison

| | Simulation | Formal |
|---|---|---|
| Input coverage | Sampled (random or directed) | Exhaustive |
| State space | Explored subset | All reachable states |
| Depth | Unbounded | Bounded (BMC) or unbounded (k-induction) |
| Runtime | Hours for large designs | Minutes for small blocks, hours/days for large |
| Bug type | Functional, timing | Protocol violations, invariant violations, deadlock |
| Tool | VCS, Xcelium | JasperGold, VC Formal, Questa Formal |

### 9.3 Formal App: Connectivity Check

```
// Prove that a write to register X is always readable back
property rw_consistency;
    logic [31:0] data;
    @(posedge clk) disable iff (!rst_n)
    (wr_en, data = wr_data) |=> (rd_data == data);
endproperty
```

### 9.4 Formal App: Deadlock Freedom

```
// Prove that the FSM never gets stuck (always exits IDLE within N cycles)
property no_deadlock;
    @(posedge clk) disable iff (!rst_n)
    (state == IDLE) && trigger |-> ##[1:MAX_CYCLES] (state != IDLE);
endproperty
```

---

## Chapter 10: Emulation Platform Deep Dive

### 10.1 Why Emulation is Needed

```
Test: Boot Android on a new SoC
 → Android boot takes ~30 billion CPU cycles
 → At 1 MHz simulation speed: 30,000 seconds = 8+ hours per test
 → At 10 MHz emulation speed: 3,000 seconds ≈ 50 minutes
 → On real silicon at 1 GHz: 30 seconds

For CAN FD at 5 Mbps: 1 frame per ~10 µs → 1 million frames per 10 seconds
 → Simulation: 1 million × 10 µs = 10 seconds of simulated time
    at 100 kHz sim speed = 100 seconds real time
 → Emulation: 1 second real time
```

### 10.2 Emulation Setup — Step by Step

**Step 1: RTL compile**
```bash
# Cadence Palladium — compile design
xrun -elaborate -access rw \
     -f design_filelist.f    \
     -top soc_top            \
     -lib_suffix .sv         \
     -xmlibdir ./xcelium.d
```

**Step 2: Emulator compile**
```bash
# Cadence iCE (Intelligent Coverage Engine) compile for Palladium
emcompile -top soc_top \
          -f design_filelist.f \
          -techlib palladium_z2.tlib \
          -o soc.emu
```

**Step 3: Connect test bench via SCE-MI**
```c
/* SCE-MI C test bench — runs on host, talks to emulator via PCIe */
#include "scemi.h"

SceMiMessageInPortProxy  *tx_port;
SceMiMessageOutPortProxy *rx_port;

int main() {
    SceMiParameters params("scemi.params");
    SceMi *scemi = SceMi::Init(SceMi::Version(2), &params);

    tx_port = SceMiMessageInPortProxy::Create("soc_top.tb.can_tx_proxy", scemi);
    rx_port = SceMiMessageOutPortProxy::Create("soc_top.tb.can_rx_proxy", scemi);

    /* Send a CAN frame transaction */
    SceMiMessageData tx_msg(8);
    tx_msg.Set(0, 0x123);  /* CAN ID */
    tx_msg.Set(1, 0x8);    /* DLC */
    tx_port->Send(tx_msg);

    /* Receive response */
    SceMiMessageData rx_msg(8);
    rx_port->Receive(rx_msg);
    printf("Received CAN ID: 0x%X\n", rx_msg.Get(0));

    SceMi::Shutdown(scemi);
    return 0;
}
```

**Step 4: Run and debug**
```bash
emrun -cfg soc.cfg \
      -test test_can_basic \
      -waves can_top.waves.shm \
      -timeout 3600
```

### 10.3 Debugging on Emulator

```
Emulator debug flow:
1. Assertion fires or test hangs
2. Load waveform: xrun -gui -waves can_top.waves.shm
3. Time-travel debug: jump to any cycle and inspect any signal
4. Assertion replay: re-run failing test with all assertions enabled
5. Coverage gap analysis: which test vectors to add?
```

---

## PART C — IP TEST ENGINEERING

---

## Chapter 11: Writing Test Plans for Hardware IPs

### 11.1 The 5 Questions a Test Plan Must Answer

1. **What** is being tested? (feature list, out-of-scope items)
2. **How** will it be tested? (methodology: simulation, emulation, HW)
3. **When** is it done? (exit criteria: coverage %, bug counts)
4. **Who** is responsible? (owners for each IP, schedule)
5. **Why** specific tests? (traceability to requirements/spec)

### 11.2 Risk-Based Test Prioritisation

```
Risk Score = Probability(bug exists) × Impact(if bug ships to customer)

High Risk (test first, deeply):
  - New IP not previously taped out
  - Features changed from last revision
  - Complex interactions between IPs (DMA + CAN + power management)
  - Features with safety implications (ISO 26262 ASIL-B/D)

Medium Risk (test thoroughly):
  - IP reused from previous chip with register map changes
  - Minor feature additions

Low Risk (smoke test only):
  - Unchanged, verified IP blocks
  - Features with extensive pre-silicon coverage history
```

### 11.3 Test Case Writing Template

```
Test Case ID  : TC-[IP]-[NUMBER]
Feature       : [Feature ID from feature table]
Title         : One-line description of what is tested
Priority      : P1 / P2 / P3
Type          : Directed / Random / Corner / Regression
Preconditions : System state required before test executes
Test Steps    :
  1. [Action 1]
  2. [Action 2]
  3. [Observe/verify]
Expected Result: Exact expected output
Pass Criteria : Measurable, unambiguous — pass or fail, no "probably"
Notes         : Known limitations, related bugs, platform notes
```

### 11.4 Example — Filling the Template

```
Test Case ID  : TC-CAN-013
Feature       : F7 — Bus-off entry and recovery
Title         : TEC > 255 causes bus-off state; auto-recovery restores normal operation
Priority      : P1
Type          : Directed
Preconditions :
  - CAN controller initialised at 500 kbps
  - Auto-recovery enabled (cfg.auto_recovery = true)
  - No other node on bus (errors guaranteed)
Test Steps    :
  1. Transmit a frame with no ACK (TEC increments by 8 per attempt)
  2. Verify TEC reaches 128: controller enters Error Passive state
     - Expected: CAN_SR.EPASS = 1, TEC ≥ 128
  3. Continue transmitting; verify TEC reaches 255+
     - Expected: CAN_SR.BOFF = 1, CAN_CR.INIT = 1 (controller halted)
  4. Wait for 128 × 11 recessive bits (auto-recovery timer)
     - Expected: CAN_SR.BOFF = 0, controller resumes operation
  5. Transmit a frame; verify successful transmission with ACK
     - Expected: CAN_TSR.TXOK = 1
Expected Result:
  Bus-off entry confirmed by BOFF=1 when TEC>255
  Auto-recovery confirmed by BOFF=0 after 128×11 recessive bits
  Subsequent TX succeeds
Pass Criteria : All 5 steps produce expected result with zero deviations
Notes         : On real hardware, requires CAN bus with no other ACKing node
                OR use CANalyzer to suppress ACKs
```

---

## Chapter 12: CAN / CAN-FD Protocol and Validation

### 12.1 CAN Frame Structure — Standard (2.0A)

```
Start  Arbitration  Control   Data     CRC    ACK   End
 of      Field      Field    Field    Field  Field   of
Frame                                               Frame
  │    ┌──────────┐ ┌──────┐ ┌──────┐ ┌───┐ ┌──┐    │
  │    │  11-bit  │ │ IDE  │ │ DLC  │ │0-8│ │  │    │
  │    │   ID     │ │  r0  │ │ 4-bit│ │bytes│ │  │    │
  1    └──────────┘ └──────┘ └──────┘ └───┘ └──┘   7
  bit     11 bits    2 bits   4 bits  0-64   2 bits  bits
                                      bits
Total: 47 + 8×DLC bits (+ stuffing bits, up to ~135 bits for DLC=8)
```

### 12.2 CAN-FD Frame Structure

```
CAN-FD adds:
  FDF bit    — distinguishes CAN-FD from CAN 2.0
  BRS bit    — Bit Rate Switch (data phase at higher rate)
  ESI bit    — Error State Indicator
  DLC 9–15  — maps to 12, 16, 20, 24, 32, 48, 64 bytes
  CRC field  — 17-bit or 21-bit (longer than CAN 2.0's 15-bit)

Bit rate:
  Arbitration phase: up to 1 Mbps (same as CAN 2.0)
  Data phase       : up to 8 Mbps (with BRS=1)
```

### 12.3 Bit Timing Deep Dive

```
One bit period = Sync_Seg + Prop_Seg + Phase_Seg1 + Phase_Seg2
               = 1 TQ    + (1..8 TQ) + (1..8 TQ)  + (1..8 TQ)

TQ = Time Quantum = 1 / (fclk / (BRP+1))

Example: fclk = 80 MHz, BRP = 1, TSEG1 = 13, TSEG2 = 2
  TQ         = 1 / (80 MHz / 2) = 25 ns
  Bit period = (1 + 13 + 2) × 25 ns = 400 ns = 2.5 Mbps

Sample point = (Sync_Seg + Prop_Seg + Phase_Seg1) / total
             = (1 + 13) / 16 = 87.5%  ← typical for automotive (75–87.5%)
```

### 12.4 CAN Error Handling — Detailed Rules

```c
/* TEC (Transmit Error Counter) rules per ISO 11898-1 */

/* Increase TEC by 8 when: */
//  - A transmitter sends an error flag
//  - A transmitter detects a dominant ACK delimiter
//  - A transmitter sends an overload flag (dominant bits in intermission)

/* Decrease TEC by 1 (min 0) when: */
//  - A successfully transmitted message (no error)

/* REC (Receive Error Counter) rules: */

/* Increase REC by 1 when: */
//  - Receiver detects an error

/* Increase REC by 8 when: */
//  - Receiver detects a dominant bit after an active error flag

/* Decrease REC by 1 (min 0) when: */
//  - Successful reception (ACK sent)

/* State transitions: */
//  TEC ≤ 127 AND REC ≤ 127  → Error Active
//  TEC > 127 OR  REC > 127  → Error Passive
//  TEC > 255                → Bus-Off
```

### 12.5 Validation Checklist for CAN IP

```
□ Loopback test — transmit and receive same frame, compare byte-by-byte
□ External node test — two real transceivers on bus
□ All DLC values 0–8 (CAN 2.0) and 9–15 (CAN-FD)
□ All bit rates in spec
□ Standard frame (IDE=0) and Extended frame (IDE=1)
□ Remote frame (RTR=1)
□ Acceptance filter — pass matching, reject non-matching
□ Filter mask — partial match
□ All 5 error types injected: bit, stuff, CRC, form, ACK
□ TEC/REC counters verified at each increment/decrement event
□ Error Active → Error Passive at TEC=128
□ Error Passive → Bus-Off at TEC=256
□ Bus-Off recovery after 128×11 recessive bits
□ Interrupt on TX done — latency measured
□ Interrupt on RX ready — latency measured
□ Interrupt on error — all error types generate interrupt
□ Interrupt masking — masked interrupt not visible to CPU
□ DMA: 16, 64, 256 frames without CPU poll
□ Sleep / wake-up by CAN activity
□ Bit timing at all PVT corners
```

---

## Chapter 13: Serial Protocol IPs — SPI, I2C, UART

### 13.1 SPI — How it Works

```
Master            Slave
  │                 │
  │─── SCLK ──────►│   Clock (master generates)
  │─── MOSI ──────►│   Master Out Slave In
  │◄── MISO ───────│   Master In Slave Out
  │─── CS_n ──────►│   Chip Select (active low)

Data shifted on SCLK edges — CPOL/CPHA define polarity and phase:
  Mode 0: CPOL=0, CPHA=0 — clock idle low, sample on rising edge
  Mode 1: CPOL=0, CPHA=1 — clock idle low, sample on falling edge
  Mode 2: CPOL=1, CPHA=0 — clock idle high, sample on falling edge
  Mode 3: CPOL=1, CPHA=1 — clock idle high, sample on rising edge
```

### 13.2 I2C — How it Works

```
SDA: ──────────┐    ┌───────────────┐    ┌──────
               └────┘               └────┘
SCL: ─────────────────────────────────────────

Start condition: SDA falls while SCL is high
Stop  condition: SDA rises while SCL is high
ACK: receiver pulls SDA low on 9th clock pulse
NACK: receiver leaves SDA high on 9th pulse

7-bit address + R/W bit + ACK + 8 data bits + ACK + ... + Stop

Clock stretching: slave holds SCL low to pause master (slave not ready)
Arbitration: if two masters drive simultaneously, the one driving 0 wins
```

### 13.3 UART — Frame Format

```
Idle: ────────────────────────────────────
                ┌──┬──┬──┬──┬──┬──┬──┬──┬────
Start bit       │D0│D1│D2│D3│D4│D5│D6│D7│ P │Stop
(logic 0): ─────┘  └──┴──┴──┴──┴──┴──┴──┘   └────

8N1 = 8 data bits, No parity, 1 stop bit
Total: 10 bits per byte → at 115200 baud: 11,520 bytes/second

Baud rate = bits per second (including start/stop/parity)
Data rate < baud rate because of framing overhead
```

### 13.4 Key Test Scenarios for Each Protocol

**SPI critical tests**:
```
1. All 4 modes (CPOL/CPHA combinations) — mode mismatch is common hw bug
2. CS de-asserted and re-asserted mid-transaction — partial frame handling
3. Maximum clock frequency — setup/hold time violation detection
4. 16-bit and 32-bit word modes — not just 8-bit
5. DMA burst: transmit 4096 bytes, verify last byte received correctly
```

**I2C critical tests**:
```
1. 10-bit addressing — less common but required for compliance
2. Clock stretching — master must wait when slave stretches
3. Bus lockup recovery — SCL stuck low: generate 9 clock pulses to release
4. Repeated START (Sr) — write followed by read without Stop
5. Arbitration loss — two masters start simultaneously; loser backs off
```

**UART critical tests**:
```
1. Baud rate tolerance — ±2% is UART spec; test at +2% and -2%
2. Break detection — line held low > 1 frame duration
3. FIFO overflow — send data faster than software reads it
4. Loopback: connect TX to RX, send 64KB, compare at both ends
5. Noise immunity — inject a single glitch on RXD line
```

---

## PART D — POST-SILICON VALIDATION

---

## Chapter 16: Silicon Bring-Up Methodology

### 16.1 The First Power-On Checklist

Before you power on any new silicon, complete this checklist:

```
PRE-POWER-ON CHECKLIST
□ PCB inspected for shorts (use DMM between all power rails and GND)
□ Decoupling capacitors present on all power pins
□ PMIC output voltages verified before connecting to chip
□ Power sequencing verified (VDD_CORE before VDD_IO)
□ JTAG connection verified (check pin 1, orientation)
□ Bench current limit set (start at 200 mA, raise if needed)
□ ESD strap on wrist, anti-static mat on bench
□ Lab notebook open, ready to log observations

POWER-ON SEQUENCE
1. Apply 3.3V IO supply first — monitor current on bench supply
2. If current normal (<100 mA), apply 1.1V core supply
3. If current normal, release reset (de-assert RESET_N)
4. Connect JTAG, run jtag_scan.py — expect valid IDCODE
5. If IDCODE correct: *** CHIP IS ALIVE ***
```

### 16.2 Reading the IDCODE via JTAG

```python
# Python script using pyOCD / python-jtag
import pyocd
from pyocd.core.helpers import ConnectHelper

session = ConnectHelper.session_with_chosen_probe()
target = session.target

# Read the IDCODE register from JTAG TAP
idcode = target.read_idcode()
print(f"IDCODE: 0x{idcode:08X}")

# Expected: 0x5BA0_0477 (Cortex-M4, ARM Coresight)
# Compare against datasheet: bits [31:28]=version, [27:12]=part_number,
# [11:1]=JEDEC_mfr_id, [0]=always_1
version    = (idcode >> 28) & 0xF
part_num   = (idcode >> 12) & 0xFFFF
mfr_id     = (idcode >>  1) & 0x7FF
print(f"Version={version}, Part=0x{part_num:04X}, Mfr=0x{mfr_id:03X}")
```

### 16.3 Memory Bring-Up — MBIST

```c
/* Software MBIST for embedded SRAM — run before any other code uses RAM */
typedef enum {
    MBIST_PASS = 0,
    MBIST_FAIL_MARCH_C = 1,
    MBIST_FAIL_CHECKERBOARD = 2
} MBIST_Result_t;

MBIST_Result_t MBIST_Run(uint32_t *base, uint32_t size_words)
{
    /* March C- algorithm */
    /* Step 1: Write 0 to all cells */
    for (uint32_t i = 0; i < size_words; i++) {
        base[i] = 0x00000000UL;
    }
    /* Step 2: Read 0, write 1 ascending */
    for (uint32_t i = 0; i < size_words; i++) {
        if (base[i] != 0x00000000UL) return MBIST_FAIL_MARCH_C;
        base[i] = 0xFFFFFFFFUL;
    }
    /* Step 3: Read 1, write 0 ascending */
    for (uint32_t i = 0; i < size_words; i++) {
        if (base[i] != 0xFFFFFFFFUL) return MBIST_FAIL_MARCH_C;
        base[i] = 0x00000000UL;
    }
    /* Step 4: Read 0, write 1 descending */
    for (int32_t i = (int32_t)size_words - 1; i >= 0; i--) {
        if (base[i] != 0x00000000UL) return MBIST_FAIL_MARCH_C;
        base[(uint32_t)i] = 0xFFFFFFFFUL;
    }
    /* Step 5: Read 1, write 0 descending */
    for (int32_t i = (int32_t)size_words - 1; i >= 0; i--) {
        if (base[i] != 0xFFFFFFFFUL) return MBIST_FAIL_MARCH_C;
        base[(uint32_t)i] = 0x00000000UL;
    }
    /* Step 6: Read 0 — final check */
    for (uint32_t i = 0; i < size_words; i++) {
        if (base[i] != 0x00000000UL) return MBIST_FAIL_MARCH_C;
    }
    return MBIST_PASS;
}
```

### 16.4 Post-Silicon Debug Decision Tree

```
Chip does not respond to JTAG
          │
          ├── Is JTAG connector correct (pin 1, orientation)? → Fix connector
          │
          ├── Is RESET_N held low? → Release reset
          │
          ├── Is TCK frequency too high? → Try 1 MHz
          │
          ├── Is VDD present? → Check power supplies
          │
          └── Is TRST_N asserted? → Check TRST_N state

Chip responds to JTAG but IDCODE wrong
          │
          ├── Is it reading 0xFFFF_FFFF? → TDO line not connected / floating
          │
          ├── Is it reading 0x0000_0000? → TDO shorted to GND
          │
          └── Wrong but non-trivial value → Silicon rev mismatch, check rev bits

JTAG OK, CPU not booting
          │
          ├── PC stuck at 0x0? → Reset vector in Flash not programmed
          │
          ├── PC stuck in fault handler? → HardFault — check stack pointer init
          │
          └── PC looping in ROM? → Secure boot failing: check keys/cert chain
```

---

## PART E — EMBEDDED C MASTERY

---

## Chapter 20: Embedded C Patterns and Idioms

### 20.1 State Machine Pattern

```c
/* Clean, table-driven FSM for CAN error state machine */
typedef enum {
    CAN_STATE_ERROR_ACTIVE  = 0,
    CAN_STATE_ERROR_PASSIVE = 1,
    CAN_STATE_BUS_OFF       = 2,
    CAN_STATE_COUNT
} CAN_ErrorState_t;

typedef enum {
    CAN_EVENT_TEC_GT_127  = 0,
    CAN_EVENT_TEC_GT_255  = 1,
    CAN_EVENT_TEC_LE_127  = 2,
    CAN_EVENT_RECOVERY    = 3,
    CAN_EVENT_COUNT
} CAN_Event_t;

/* Transition table [current_state][event] = next_state */
static const CAN_ErrorState_t s_transitions[CAN_STATE_COUNT][CAN_EVENT_COUNT] = {
    /* ERROR_ACTIVE  */ { CAN_STATE_ERROR_PASSIVE, CAN_STATE_BUS_OFF,       CAN_STATE_ERROR_ACTIVE,  CAN_STATE_ERROR_ACTIVE  },
    /* ERROR_PASSIVE */ { CAN_STATE_ERROR_PASSIVE, CAN_STATE_BUS_OFF,       CAN_STATE_ERROR_ACTIVE,  CAN_STATE_ERROR_PASSIVE },
    /* BUS_OFF       */ { CAN_STATE_BUS_OFF,       CAN_STATE_BUS_OFF,       CAN_STATE_BUS_OFF,       CAN_STATE_ERROR_ACTIVE  },
};

/* Action functions */
static void on_enter_error_passive(void) { /* Set EPASS flag, suppress TX */ }
static void on_enter_bus_off(void)       { /* Halt TX/RX, start recovery timer */ }
static void on_enter_error_active(void)  { /* Clear flags, enable TX/RX */ }

typedef void (*StateEntryFn_t)(void);
static const StateEntryFn_t s_entry_actions[CAN_STATE_COUNT] = {
    on_enter_error_active,
    on_enter_error_passive,
    on_enter_bus_off,
};

/* Process event */
void CAN_FSM_ProcessEvent(CAN_ErrorState_t *state, CAN_Event_t event)
{
    CAN_ErrorState_t next = s_transitions[*state][event];
    if (next != *state) {
        *state = next;
        if (s_entry_actions[next] != NULL) {
            s_entry_actions[next]();
        }
    }
}
```

### 20.2 Ring Buffer (Circular Buffer) Pattern

Used in UART/CAN receive drivers to decouple ISR from application:

```c
#define RING_BUF_SIZE  (256U)   /* must be power of 2 */
#define RING_BUF_MASK  (RING_BUF_SIZE - 1U)

typedef struct {
    volatile uint8_t  buf[RING_BUF_SIZE];
    volatile uint32_t head;   /* written by producer (ISR) */
    volatile uint32_t tail;   /* read by consumer (task) */
} RingBuf_t;

/* Called from ISR — must be fast */
bool RingBuf_Push(RingBuf_t *rb, uint8_t byte)
{
    uint32_t next_head = (rb->head + 1U) & RING_BUF_MASK;
    if (next_head == rb->tail) {
        return false;   /* buffer full — drop byte */
    }
    rb->buf[rb->head] = byte;
    rb->head = next_head;   /* atomic write — single uint32 on ARM */
    return true;
}

/* Called from task — may be slow */
bool RingBuf_Pop(RingBuf_t *rb, uint8_t *byte)
{
    if (rb->tail == rb->head) {
        return false;   /* buffer empty */
    }
    *byte = rb->buf[rb->tail];
    rb->tail = (rb->tail + 1U) & RING_BUF_MASK;
    return true;
}

uint32_t RingBuf_Available(const RingBuf_t *rb)
{
    return (rb->head - rb->tail) & RING_BUF_MASK;
}
```

### 20.3 Memory Pool Pattern (No malloc)

```c
/* Fixed-size memory pool — deterministic allocation, no fragmentation */
#define POOL_BLOCK_SIZE   (sizeof(CAN_Frame_t))
#define POOL_BLOCK_COUNT  (32U)

typedef struct PoolBlock {
    struct PoolBlock *next;                 /* free list pointer */
    uint8_t           data[POOL_BLOCK_SIZE];
} PoolBlock_t;

static PoolBlock_t  s_pool_storage[POOL_BLOCK_COUNT];
static PoolBlock_t *s_free_list = NULL;

void Pool_Init(void)
{
    s_free_list = NULL;
    for (uint32_t i = 0U; i < POOL_BLOCK_COUNT; i++) {
        s_pool_storage[i].next = s_free_list;
        s_free_list = &s_pool_storage[i];
    }
}

CAN_Frame_t *Pool_Alloc(void)
{
    if (s_free_list == NULL) { return NULL; }
    PoolBlock_t *block = s_free_list;
    s_free_list = block->next;
    return (CAN_Frame_t *)block->data;
}

void Pool_Free(CAN_Frame_t *frame)
{
    PoolBlock_t *block = (PoolBlock_t *)((uint8_t *)frame - offsetof(PoolBlock_t, data));
    block->next = s_free_list;
    s_free_list = block;
}
```

---

## Chapter 22: RTOS Fundamentals — FreeRTOS

### 22.1 FreeRTOS Core Concepts

```
┌─────────────────────────────────────────────────────────┐
│  FreeRTOS Scheduler                                     │
│                                                         │
│  Priority 5 ── CAN_RxTask  ──── Blocked (waiting sem)  │
│  Priority 4 ── UDS_Task    ──── Running                 │
│  Priority 3 ── Diag_Task   ──── Ready                   │
│  Priority 2 ── Logger_Task ──── Blocked (waiting queue) │
│  Priority 1 ── Idle_Task   ──── Blocked                 │
│                                                         │
│  SysTick ISR fires every 1 ms → context switch if needed│
└─────────────────────────────────────────────────────────┘
```

### 22.2 Task Creation and Synchronisation

```c
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"
#include "queue.h"

/* Shared resources */
static SemaphoreHandle_t g_can_rx_sem;
static QueueHandle_t     g_can_rx_queue;

/* CAN RX task — woken by ISR */
static void CAN_RxTask(void *params)
{
    CAN_Frame_t frame;
    (void)params;

    for (;;) {
        /* Block until ISR signals a frame is ready */
        if (xSemaphoreTake(g_can_rx_sem, pdMS_TO_TICKS(100)) == pdTRUE) {
            if (CAN_Receive(0U, &frame, 0U) == CAN_STATUS_OK) {
                /* Send to processing queue */
                xQueueSend(g_can_rx_queue, &frame, 0U);
            }
        }
    }
}

/* UDS processing task */
static void UDS_ProcessTask(void *params)
{
    CAN_Frame_t frame;
    (void)params;

    for (;;) {
        if (xQueueReceive(g_can_rx_queue, &frame, portMAX_DELAY) == pdTRUE) {
            UDS_ProcessFrame(&frame);
        }
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();

    g_can_rx_sem   = xSemaphoreCreateBinary();
    g_can_rx_queue = xQueueCreate(16U, sizeof(CAN_Frame_t));

    xTaskCreate(CAN_RxTask,     "CAN_RX",  256U, NULL, 5U, NULL);
    xTaskCreate(UDS_ProcessTask,"UDS_PROC",512U, NULL, 4U, NULL);

    vTaskStartScheduler();
    /* Never reached */
    for (;;) {}
}

/* ISR — signals task without context switch overhead */
void CAN1_RX0_IRQHandler(void)
{
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(g_can_rx_sem, &woken);
    portYIELD_FROM_ISR(woken);
}
```

---

## Chapter 23: MISRA C:2012 — Rules, Rationale, and Tools

### 23.1 The 10 Most Important MISRA Rules for Silicon/Embedded Work

```c
/* MISRA Rule 7.2: A "u" or "U" suffix shall be applied to all integer constants */
#define CAN_MAX_DLC  8U     /* CORRECT */
#define BAD_MAX      8      /* MISRA violation */

/* MISRA Rule 10.4: Both operands of an operator shall be the same essential type */
uint8_t  a = 10U;
uint32_t b = a + 5U;   /* MISRA violation: 8-bit + int = int arithmetic */
uint32_t c = (uint32_t)a + 5UL;   /* CORRECT */

/* MISRA Rule 11.3: A cast shall not be performed between pointer and integer type */
/* Exception: hardware register access is explicitly allowed with a comment */
/*lint -e923 */   /* suppress in certain tools */
#define GPIOA_ODR  (*((volatile uint32_t *)0x48000014UL))  /* MISRA Rule 11.4 exception */

/* MISRA Rule 14.4: The controlling expression of an if/while/do shall be boolean */
uint8_t flag = CAN_IsBusOff(0U) ? 1U : 0U;
if (flag != 0U) { ... }   /* CORRECT */
if (flag) { ... }          /* MISRA violation — not boolean */

/* MISRA Rule 15.5: A function should have a single exit point */
/* MISRA Rule 17.7: Return value of non-void function shall be used */
(void)memcpy(dst, src, len);   /* CORRECT — explicit discard */
memcpy(dst, src, len);          /* MISRA violation */

/* MISRA Rule 21.3: Dynamic memory allocation shall not be used */
void *p = malloc(100);   /* MISRA violation — forbidden in safety code */
/* Use static pools instead */
```

### 23.2 Static Analysis Tool Setup

```yaml
# spyglass_misra.tcl — SpyGlass MISRA C analysis script
set_option enable_policy_checker true
read_file { src/can_driver.c src/can_driver_irq.c } -type c
set_option guideline { MISRA_C_2012 }
set_option severity { error warning }
compile_design
check_design -goal MISRA_C_2012
write_report -output reports/misra_report.html
```

---

## Chapter 24: Unit Testing Embedded Code on Host

### 24.1 The Test Pyramid for Embedded

```
        /\
       /  \   System tests (on hardware) — few, slow, expensive
      /    \
     /      \  Integration tests (on FPGA/emulator) — medium count
    /        \
   /──────────\ Unit tests (on host PC) — many, fast, cheap
  /____________\
  Compile tests  — even more, instant

Goal: push most verification to the bottom of the pyramid
```

### 24.2 Hardware Abstraction for Testability

```c
/* Bad — untestable on host (hardware register access) */
void LED_On(void) {
    GPIOA->BSRR = (1UL << 5U);
}

/* Good — abstracted, testable on host */
typedef void (*GPIO_SetFn_t)(uint32_t pin, uint8_t state);

static GPIO_SetFn_t g_gpio_set = NULL;

void LED_SetGpioHook(GPIO_SetFn_t fn) {
    g_gpio_set = fn;
}

void LED_On(void) {
    if (g_gpio_set != NULL) {
        g_gpio_set(5U, 1U);
    }
}

/* In unit test: */
static uint32_t g_last_pin;
static uint8_t  g_last_state;

static void mock_gpio_set(uint32_t pin, uint8_t state) {
    g_last_pin   = pin;
    g_last_state = state;
}

void test_LED_On_drives_pin5_high(void) {
    LED_SetGpioHook(mock_gpio_set);
    LED_On();
    TEST_ASSERT_EQUAL_UINT32(5U, g_last_pin);
    TEST_ASSERT_EQUAL_UINT8(1U, g_last_state);
}
```

---

## PART F — PROFESSIONAL SKILLS

---

## Chapter 25: Requirements Engineering for Embedded Projects

### 25.1 SMART Requirements

Every requirement must be:

```
Specific   — "The driver shall transmit a CAN frame within 1 ms"
             NOT "The driver shall be fast"

Measurable — "< 1 ms" — can be measured with a scope/logic analyser
             NOT "acceptable latency"

Achievable — technically feasible with the target hardware
             NOT "transmit at 100 Gbps" on a 1 Mbps CAN bus

Relevant   — traces to a customer need or safety goal
             NOT arbitrary constraints added by habit

Time-bound — when is this verified? "at pre-silicon sim and post-silicon HW test"
             NOT "eventually"
```

### 25.2 Requirement Smells (Bad Patterns)

```
SMELL 1: Ambiguous    "The CAN driver shall handle errors gracefully"
FIX:                  "The CAN driver shall set TEC to 0 and clear BOFF flag
                       within 5 ms of receiving 128×11 consecutive recessive bits
                       after bus-off entry"

SMELL 2: Compound     "The driver shall transmit frames AND support DMA AND
                       handle interrupts"
FIX:                  Split into 3 separate requirements (one thing per req)

SMELL 3: Untestable   "The driver shall be robust"
FIX:                  "The driver shall return CAN_STATUS_ERROR and not enter
                       undefined state when CAN_Transmit() is called before
                       CAN_Init()"

SMELL 4: Implementation "The driver shall use a lookup table for bit timing"
FIX:                  "The driver shall support bit rates of 125k, 250k, 500k,
                       1000k bit/s" — leave HOW to the designer

SMELL 5: Missing units "The driver shall be fast and use little memory"
FIX:                  "CAN_Transmit() execution time shall not exceed 10 µs.
                       Driver code size shall not exceed 4 KB (Flash).
                       Driver RAM usage shall not exceed 256 bytes."
```

---

## Chapter 26: Bug Management and Root Cause Analysis

### 26.1 Bug Report Template

```
Bug ID    : BUG-CAN-0047
Title     : CAN TEC counter does not increment on ACK error
Severity  : P1 — Blocker (required for compliance)
Found in  : Pre-silicon simulation, test TC-CAN-016
Date      : 2026-05-05
Found by  : Validation Engineer

ENVIRONMENT
  Simulator : Xcelium 23.09
  RTL tag   : can_ctrl_v2.3.1
  Test      : TC-CAN-016 (ACK error injection)

DESCRIPTION
  When the CAN controller transmits a frame with no ACK response (simulated
  by suppressing the ACK bit in the test bench), the TEC counter is expected
  to increment by 8 per ISO 11898-1 Section 11.4.
  Observed: TEC remains 0 after 10 consecutive ACK errors.
  Expected: TEC = 80 (10 × 8) after 10 ACK errors.

REPRODUCTION STEPS
  1. Configure CAN at 500 kbps, loopback disabled
  2. Transmit a standard CAN frame (ID=0x123, DLC=1, data=0xAA)
  3. In test bench: prevent ACK bit from being driven low
  4. Read ECR register: ECR[15:8] = TEC field
  Expected: TEC = 8 after first error
  Actual:   TEC = 0

IMPACT
  Bus-off protection will not work correctly. Controller will not enter
  error passive or bus-off states. ISO 11898-1 compliance failure.
  Safety implication: ASIL-A violation if part of error detection chain.

ATTACHMENTS
  - Waveform: can_ack_error_tec_bug.fsdb
  - Screenshot: tec_counter_stuck_zero.png
```

### 26.2 Root Cause Analysis — 5 Whys

```
Bug: TEC does not increment on ACK error

Why 1: Why is TEC not incrementing?
  → The error_counter_increment signal is not asserted on ACK error

Why 2: Why is error_counter_increment not asserted?
  → The ACK error condition (ack_err) is not being raised

Why 3: Why is ack_err not being raised?
  → The ACK slot monitoring logic checks rxd_sync, but rxd_sync
    is not updated because the RX clock enable (rx_clk_en) is
    de-asserted during the ACK bit period

Why 4: Why is rx_clk_en de-asserted during ACK?
  → A recent commit (git blame: commit a3f7b2c) changed the
    rx_clk_en gating condition to disable RX during TX — intended
    to fix a different issue (false RX during TX data phase)

Why 5: Why did this regression not get caught?
  → Regression suite for error counters was not updated after
    the commit; the specific ACK error test was not in baseline

ROOT CAUSE: RTL change to rx_clk_en gating incorrectly disabled
reception during the ACK slot, preventing ACK error detection.

FIX: Gate rx_clk_en only during DATA phase bits, not during ACK slot.
    if ((bit_position >= DATA_START) && (bit_position < ACK_SLOT))
        rx_clk_en = ~tx_active;
    else
        rx_clk_en = 1'b1;   // always enabled for ACK, EOF, IFS

PREVENTION: Add test TC-CAN-016 to regression suite; add SVA assertion
    that ack_err fires when ACK bit is dominant after transmission.
```

---

## Chapter 27: CI/CD for Embedded and Silicon Projects

### 27.1 GitHub Actions Pipeline for Embedded C

```yaml
# .github/workflows/embedded_ci.yml
name: Embedded C CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc cmake ninja-build cppcheck \
                                  gcovr python3-pip
          pip3 install junit-xml

      - name: Configure (CMake)
        run: cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTS=ON

      - name: Build
        run: cmake --build build --parallel

      - name: Run unit tests
        run: |
          cd build
          ctest --output-on-failure --no-compress-output -T Test

      - name: Upload test results (JUnit)
        uses: dorny/test-reporter@v1
        if: always()
        with:
          name: Unit Tests
          path: build/Testing/*/Test.xml
          reporter: ctest-xml

      - name: MISRA / static analysis (cppcheck)
        run: |
          cppcheck --enable=all --error-exitcode=1 \
                   --suppress=missingIncludeSystem \
                   --xml --xml-version=2 \
                   src/ 2> cppcheck_report.xml
          python3 tools/cppcheck_to_junit.py cppcheck_report.xml > cppcheck_junit.xml

      - name: Code coverage
        run: |
          cd build
          cmake --build . --target coverage
          gcovr --xml coverage.xml --html-details coverage.html
          python3 ../tools/check_coverage.py coverage.xml --min-line=85

      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: build/coverage.html
```

---

## Chapter 28: Interview Preparation — 60 Q&A

### Pre-Silicon / Verification

**Q1**: What is the difference between `assert` and `cover` in SVA?
> `assert` declares that a property MUST always be true — a failure is a bug. `cover` tracks whether a property was EVER exercised — used for functional coverage. A `cover` failure (never triggered) means a test scenario was not exercised, not that the design is wrong.

**Q2**: A simulation runs for 10 million cycles and your covergroup shows 60% functional coverage. What do you do?
> Analyse the uncovered bins — which scenarios were never hit? Write directed tests for the missing bins. Then re-run and check if the gap closes. If random tests cannot reach a corner case (e.g., bus-off), write a directed test that forces TEC > 255 explicitly.

**Q3**: What is the difference between CDC and RDC?
> CDC (Clock Domain Crossing) — signals crossing between different clock domains (e.g., 100 MHz to 50 MHz). RDC (Reset Domain Crossing) — signals crossing between circuits that de-assert reset at different times. Both need synchronisers; missing CDC synchronisers cause metastability; missing RDC handling causes reset domain violations where one block comes out of reset before its interface is stable.

**Q4**: What is formal verification and when would you use it instead of simulation?
> Formal verification uses mathematical proof to check that a property holds for ALL possible inputs and ALL reachable states. Use it when: (a) exhaustive stimulus coverage is needed but cannot be achieved with random, (b) proving safety properties (e.g., "FIFO will never overflow"), (c) protocol invariants (e.g., "after req, ack always comes within 4 cycles"), (d) after RTL changes — regression proof faster than re-running full sim.

**Q5**: What is a race condition in RTL and how do you detect it?
> A race condition occurs when two processes update the same signal in the same simulation time step, and the result depends on evaluation order. Symptom: simulation gives correct results with one simulator but fails with another. Detection: enable compilation warnings for multiple drivers; use linting tools (SpyGlass); use `always_ff` and `always_comb` (SystemVerilog) which enforce proper procedural usage.

**Q6**: Explain the difference between blocking (`=`) and non-blocking (`<=`) assignments in SystemVerilog.
> Blocking (`=`): executes immediately, like C assignment. `a = b; c = a;` — c gets the new value of a. Used in combinational always blocks (`always_comb`). Non-blocking (`<=`): schedules the assignment to happen at end of time step. `a <= b; c <= a;` — c gets the OLD value of a (before b was assigned). Used in clocked sequential logic (`always_ff`). Mixing them in sequential logic is a common RTL bug that causes simulation/synthesis mismatch.

**Q7**: What is UVM factory and why is it useful?
> The UVM factory allows test benches to substitute any class with a derived class at runtime, without changing the test bench source code. Useful for: (a) error injection — substitute a standard sequence with an error-injecting sequence for specific tests, (b) component replacement — swap out a real physical model for a simpler behavioural model, (c) test specialisation — derived test overrides only a specific component's behaviour.

### Post-Silicon

**Q8**: What is the first thing you do when silicon arrives and does not respond to JTAG?
> Check: (1) power supply voltages present and within spec, (2) RESET_N released (not held low), (3) JTAG connector pin 1 orientation, (4) TCK frequency (try 1 MHz if using higher), (5) TDO net continuity with DMM, (6) oscilloscope on TCK to confirm signal is reaching the chip pad.

**Q9**: How do you measure interrupt latency on a real chip?
> Toggle a GPIO in the ISR entry, trigger an interrupt, measure time between trigger and GPIO toggle with an oscilloscope. More precisely: read DWT->CYCCNT at ISR entry, save it; the interrupt trigger timestamp is captured by the triggering event (e.g., another GPIO toggle at IRQ assert). Difference × (1/CPU_freq) = latency. Expected: ~12–20 cycles for Cortex-M4 with FPU context push.

**Q10**: What is metastability and how does it manifest in silicon?
> Metastability occurs when a flip-flop's setup or hold time is violated — the output oscillates between 0 and 1 and may settle to either, unpredictably. In silicon, it manifests as: random bit errors in data crossing clock domains, intermittent failures at specific frequencies or temperatures (MTBF degrades at higher clock rates), lock-up of FSMs that receive a corrupted control signal. Prevention: two-stage synchroniser for single-bit signals; FIFO with grey-coded pointers for multi-bit signals.

**Q11**: What is characterisation testing and what do you measure?
> Characterisation testing measures the actual electrical performance of silicon across Process-Voltage-Temperature (PVT) corners: (a) F-V (frequency vs voltage) sweep — find minimum VDD at each target frequency, (b) power: dynamic current at max activity, leakage at each power state, (c) timing margins: setup/hold slack distribution across PVT, (d) I/O: output drive strength, slew rate, input threshold at each corner, (e) PLL: lock time, jitter, pull range. Results feed back into datasheet limits and production test limits.

### Embedded C

**Q12**: Why must hardware register pointers be declared as volatile?
> Without `volatile`, the compiler may cache the register value in a CPU register and never re-read it from memory — because it assumes no other code can change a variable between reads. Hardware registers change independently of software (e.g., a status bit set by hardware on completion). `volatile` forces the compiler to always generate a load instruction from the actual memory address.

**Q13**: What is the difference between `const` and `volatile const` in embedded C?
> `const` — software promises not to write this; compiler may cache reads. `volatile const` — software promises not to write this, BUT the value can still change (hardware can update it). Use `volatile const` for read-only hardware status registers.

**Q14**: What are the MISRA C rules about dynamic memory allocation and why?
> MISRA Rule 21.3 forbids `malloc`, `calloc`, `realloc`, `free` in production safety-critical code. Reasons: (1) fragmentation — repeated alloc/free fragments heap, leading to unpredictable allocation failures, (2) non-deterministic timing — `malloc` may take variable time, violating real-time requirements, (3) heap corruption — buffer overflow can corrupt heap metadata, causing silent data corruption, (4) difficult to analyse — static analysis tools cannot determine heap usage at compile time. Alternative: static allocation, fixed-size memory pools.

**Q15**: Explain the difference between a semaphore and a mutex in FreeRTOS.
> Mutex (Mutual Exclusion Semaphore): owned by a task; only the task that took it can give it. Has priority inheritance — if a low-priority task holds it, it temporarily inherits the priority of the waiting high-priority task to prevent priority inversion. Use for protecting shared resources. Semaphore: not owned; any task or ISR can give it. No priority inheritance. Use for signalling (ISR signals task that data is ready). Binary semaphore = signalling; counting semaphore = counting available resources.

**Q16**: What is a cache coherency issue and how do you solve it in an embedded DMA driver?
> When DMA writes to DRAM, the CPU's cache may contain stale (old) data for those addresses. When CPU reads, it gets the cached stale value, not the DMA-updated value. Solutions: (a) use non-cacheable memory region (MPU attribute) for DMA buffers — slower but simple, (b) invalidate (discard) CPU cache lines covering the buffer before CPU reads DMA result: `SCB_InvalidateDCache_by_Addr()`, (c) use coherent DMA (hardware-managed on some SoCs with cache coherent interconnect, e.g., ARM CCI-400).

**Q17**: You have a production firmware that randomly crashes every 48 hours. How do you debug it?
> (1) Enable a watchdog reset and log the crash reason to NVM before reset; (2) enable HardFault handler to capture PC, LR, PSP/MSP stack frame to NVM; (3) add a memory guard pattern (canary value) at stack end — check in scheduler tick; (4) enable MPU stack guard region — catches stack overflow with precise fault; (5) analyse crash dumps — check if PC points to a valid code region or if it's corrupted (stack overflow destroying return address); (6) check for heap corruption if malloc is used; (7) review all shared globals accessed from ISR — ensure volatile and atomic access.

---

## Learning Path Summary

```
MONTH 1 — Foundations
  Week 1-2: Chapters 1-2  (Chip flow, digital logic, FSMs)
  Week 3-4: Chapters 3-4  (C deep dive, memory architecture)

MONTH 2 — Verification Core
  Week 5-6: Chapters 6-7  (UVM, coverage)
  Week 7-8: Chapters 8-9  (SVA, formal)

MONTH 3 — IP Test Engineering
  Week 9-10:  Chapter 11-12 (test plans, CAN/CAN-FD)
  Week 11-12: Chapter 13-14 (SPI/I2C/UART, USB/PCIe)

MONTH 4 — Post-Silicon and Advanced C
  Week 13-14: Chapters 16-17 (bring-up, debug)
  Week 15-16: Chapters 20-22 (C patterns, RTOS)

MONTH 5 — Professional
  Week 17-18: Chapters 23-24 (MISRA, host unit tests)
  Week 19-20: Chapters 25-28 (requirements, CI/CD, interview prep)

PROJECTS (do these alongside reading):
  Project 1: Write a CAN driver in C with Unity unit tests (Months 1-2)
  Project 2: Write a UVM testbench for a simple UART model (Month 2-3)
  Project 3: Write a complete test plan for an I2C IP (Month 3)
  Project 4: Set up GitHub Actions CI for your CAN driver (Month 4-5)
```

---

*Document: Silicon Validation & Embedded C Learning Guide | Version 1.0 | Date: 2026-05-05*
