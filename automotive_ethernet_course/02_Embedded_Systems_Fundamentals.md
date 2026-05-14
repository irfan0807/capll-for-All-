# SECTION 2 — EMBEDDED SYSTEMS FUNDAMENTALS
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## 2.1 ECU ARCHITECTURE

### What Is an ECU?

An **ECU (Electronic Control Unit)** is a specialized embedded computer inside a vehicle that reads sensor inputs, executes algorithms, and controls actuators. Modern vehicles have 70–150+ ECUs; SDV platforms consolidate to 3–5 HPC (High-Performance Computers).

### Physical ECU Hardware Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ECU HARDWARE BLOCK DIAGRAM                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌──────────────────────────────────────────┐   │
│  │  Power      │    │           MCU / SoC                      │   │
│  │  Supply     │───►│  ┌──────────┐  ┌──────────┐  ┌────────┐ │   │
│  │  (PMIC)     │    │  │   CPU    │  │   DSP    │  │  GPU   │ │   │
│  └─────────────┘    │  │ Core(s)  │  │ (Signal) │  │(ADAS)  │ │   │
│                     │  └────┬─────┘  └──────────┘  └────────┘ │   │
│  ┌─────────────┐    │       │                                  │   │
│  │  CAN/LIN/   │    │  ┌────▼──────────────────────────────┐  │   │
│  │  Ethernet   │◄──►│  │         Internal Bus (AXI/AHB)    │  │   │
│  │  PHY Chip   │    │  └───┬──────┬──────┬──────┬──────────┘  │   │
│  └─────────────┘    │  ┌───▼┐ ┌───▼┐ ┌───▼┐ ┌───▼┐           │   │
│                     │  │RAM │ │FLASH│ │EEPROM│ │ADC │           │   │
│  ┌─────────────┐    │  │DRAM│ │ NOR │ │     │ │    │           │   │
│  │  Debug      │    │  └────┘ └─────┘ └──────┘ └────┘          │   │
│  │  JTAG/TRACE │◄──►│                                          │   │
│  └─────────────┘    │  Peripherals: SPI, I2C, UART, PWM, DIO  │   │
│                     └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Common Automotive MCUs

| MCU Family | Vendor | Cores | Use Case |
|-----------|--------|-------|---------|
| Aurix TC3xx | Infineon | TriCore + lockstep | Safety ECU, Powertrain, ADAS |
| S32K3xx | NXP | ARM Cortex-M7 | Body, Gateway, Mid-range |
| S32G3 | NXP | ARM Cortex-A55 + M7 | Central Gateway, ADAS |
| RH850 | Renesas | RH850/P1x-C | Chassis, Powertrain |
| TDA4VM | Texas Instruments | ARM + C7x DSP | ADAS Vision Processing |
| R-Car | Renesas | ARM Cortex-A + R | IVI, ADAS |

### Real ECU Example: Continental MFC (Multi-Function Camera ECU)

```
Continental MFC720 — Forward Camera ECU
├── SoC: TI TDA4VM (8× ARM Cortex-A72 + DSPs)
├── RAM: 8 GB LPDDR4X
├── Flash: 64 GB eMMC (for ML models)
├── Ethernet: 1× 1000BASE-T1 (to ADAS domain ECU)
├── CAN: 2× CAN FD (legacy vehicle bus)
├── Power: 5V/3.3V (multi-rail PMIC)
└── OS: QNX Neutrino RTOS + AUTOSAR Adaptive
```

---

## 2.2 MICROCONTROLLERS — DEEP DIVE

### MCU vs SoC vs MPU

| Type | Memory | OS | Example | Automotive Use |
|------|--------|-----|---------|---------------|
| MCU | On-chip Flash + RAM | Bare-metal / RTOS | Infineon TC397 | Safety ECU, Body |
| SoC | External DRAM + Flash | Linux / QNX | NXP S32G3 | Gateway, ADAS |
| MPU | External only | Full OS | Renesas R-Car H3 | IVI, Cluster |

### Infineon AURIX TC397 — Safety MCU Architecture

```
AURIX TC397 (ISO 26262 ASIL-D Ready)
├── CPU0: TriCore 300MHz (Main Application)
├── CPU1: TriCore 300MHz (Safety Monitor) — Lockstep with CPU0
├── CPU2–CPU5: Additional processing cores
├── PFLASH: 16 MB (Program memory)
├── DFLASH: 2 MB (Data / EEPROM emulation)
├── PSRAM: 3 MB (Scratch-pad RAM)
├── Peripherals:
│   ├── CAN: 4× CAN FD controllers
│   ├── Ethernet: 1× 100BASE-T1 (gPTP support)
│   ├── SPI: 6× QSPI (for external flash)
│   ├── LIN: 8× LIN controllers
│   └── ADC: 8× 12-bit ADC channels
├── Safety Features:
│   ├── ECC on all memories
│   ├── SMU (Safety Management Unit)
│   ├── CPU Lockstep (ASIL-D)
│   └── Watchdog timers
```

---

## 2.3 RTOS — REAL-TIME OPERATING SYSTEM

### What Is an RTOS and Why Automotive Needs It?

A standard OS (Windows/Linux) uses a best-effort scheduler — tasks run when the OS decides. An **RTOS** guarantees that a task runs within a defined time window. Automotive safety requires **determinism**.

### RTOS Timing Concepts

```
TASK TIMING DIAGRAM:
────────────────────────────────────────────────────────────────────
Time:    0ms      1ms      2ms      3ms      4ms      5ms
         │        │        │        │        │        │
Task A   ████     ████     ████     ████     ████     ████
(1ms period, WCET 0.5ms) — Critical: ABS control

Task B   ░░░░░░░░░████     ░░░░░░░░░████     ░░░░░░░░░████
(2ms period, WCET 0.8ms) — ADAS: FCW calculation

Task C   ░░░░░░░░░░░░░░░░░░░░░░░░░░░████     ░░░░░░░░░░░░
(5ms period, WCET 1ms) — COM: CAN/Ethernet transmit
────────────────────────────────────────────────────────────────────

Key Terms:
• WCET  = Worst Case Execution Time (must fit in period)
• Period = How often task runs (1ms, 5ms, 10ms, 100ms)
• Deadline = When task must finish (= period for hard real-time)
• Jitter = Variation in actual start time vs scheduled start time
```

### AUTOSAR OS — Rate Monotonic Scheduling

```c
/* AUTOSAR OS Task Definition — OsTaskForAEB */
TASK(OsTask_AEB_10ms)
{
    /* This task runs every 10ms with priority 50 */
    AEB_MainFunction();       /* AEB algorithm */
    TerminateTask();
}

ALARM(OsAlarm_AEB_10ms) {
    TASK: OsTask_AEB_10ms,
    CYCLE: 10ms,
    START: 0ms,
    ACTION: ActivateTask
}
```

### RTOS Types in Automotive

| RTOS | Vendor | Standard | Use |
|------|--------|---------|-----|
| AUTOSAR OS | AUTOSAR | OSEK | Classic AUTOSAR ECU |
| QNX Neutrino | BlackBerry | POSIX | Safety gateway, IVI |
| FreeRTOS | AWS | None | Low-end MCUs |
| PikeOS | Sysgo | POSIX + ARINC | Mixed-criticality |
| Zephyr | Linux Foundation | None | IoT, edge nodes |

---

## 2.4 INTERRUPTS

### What Is an Interrupt?

An interrupt is a hardware signal that pauses the CPU's current task, saves context, executes an ISR (Interrupt Service Routine), then resumes.

```
INTERRUPT FLOW IN AN AUTOMOTIVE ECU:

Normal Execution          Interrupt Occurs       ISR Executes       Resume
─────────────────────────────────────────────────────────────────────────
Main_10ms Task running...
                          ←── CAN Frame Received ───
                          CPU saves PC, registers
                                                    ISR_CAN_Rx():
                                                    buffer[idx++] = frame;
                                                    Set event flag;
                                                    Return from interrupt;
                          CPU restores registers
Main_10ms Task continues...
```

### Interrupt Priority — Automotive Example

```c
/* NXP S32K3 NVIC Priority Assignment */
/* Lower number = Higher priority in ARM Cortex-M */

IRQ_ETH_FRAME_RECEIVED   = Priority 0  /* Highest — time critical */
IRQ_CAN_RX_COMPLETE      = Priority 1
IRQ_TIMER_10MS           = Priority 2
IRQ_SPI_TRANSFER_DONE    = Priority 5
IRQ_UART_BYTE_RECEIVED   = Priority 10 /* Lowest priority shown */
```

### Critical Interrupt Concepts for Interviews

```c
/* Nested Interrupt — Ethernet ISR preempts CAN ISR */
void ISR_CAN_Rx(void) {
    /* Priority 1 ISR — can be preempted by Priority 0 */
    NVIC_EnableIRQ(ETH_IRQn);  /* Allow nesting */
    process_can_frame();
    clear_interrupt_flag();
}

void ISR_ETH_Rx(void) {
    /* Priority 0 — highest, cannot be preempted */
    copy_eth_frame_to_buffer();
    set_rx_event_flag();
    clear_interrupt_flag();
}

/* IMPORTANT: ISRs must be SHORT. Never call blocking functions! */
/* Bad practice: calling printf(), malloc(), delay() in ISR */
```

---

## 2.5 MEMORY ARCHITECTURE

### ECU Memory Types and Their Roles

```
┌──────────────────────────────────────────────────────────────────────┐
│                    ECU MEMORY ARCHITECTURE                           │
├────────────────────────────────────────────────────────────────────┤
│  TYPE        │ SIZE      │ VOLATILE? │ PURPOSE                     │
├────────────────────────────────────────────────────────────────────┤
│  PFLASH      │ 2–16 MB   │ No        │ Program code (read-only)    │
│  DFLASH      │ 64K–2MB   │ No        │ Calibration, NvM storage    │
│  PSRAM       │ 256K–8MB  │ Yes       │ Stack, heap, runtime data   │
│  EEPROM      │ 4K–64K    │ No        │ Non-volatile config data    │
│  DRAM (ext)  │ 1–8 GB    │ Yes       │ SoC: OS, large buffers      │
│  eMMC (ext)  │ 8–64 GB   │ No        │ SoC: bootloader, OS image  │
└────────────────────────────────────────────────────────────────────┘
```

### Memory Map — Infineon AURIX TC397

```
0x00000000 ─── PFLASH Start (Program Flash - 16MB)
0x00FFFFFF ─── PFLASH End
0x10000000 ─── PSRAM0 (Program Scratch-Pad RAM - 96KB)
0x60000000 ─── DFLASH0 (Data Flash - 2MB, NvM/Calibration)
0x70100000 ─── DFLASH1 (UCB - User Configuration Block)
0x70000000 ─── DFLASH EEPROM Emulation region
0xF0000000 ─── SFR Region (Special Function Registers)
0xF8800000 ─── CPU0 DSPR (Data Scratch-Pad RAM - 240KB)
0xF8880000 ─── CPU1 DSPR
```

### Stack vs Heap — Critical for Interviews

```
RAM LAYOUT DURING RUNTIME:
┌─────────────────────────────────────────────────────┐
│  HIGH ADDRESS (0x80000000)                          │
├─────────────────────────────────────────────────────┤
│  STACK (grows downward ▼)                           │
│  ├── Task A stack frame                             │
│  ├── ISR stack frame                                │
│  └── Function call chain (activation records)      │
├─────────────────────────────────────────────────────┤
│  FREE RAM SPACE (decreases as both grow)            │
├─────────────────────────────────────────────────────┤
│  HEAP (grows upward ▲)                              │
│  ├── malloc() / new operator allocations           │
│  └── Dynamic memory (avoid in safety SW!)          │
├─────────────────────────────────────────────────────┤
│  BSS SEGMENT (.bss)                                 │
│  └── Uninitialized global variables (zeroed)       │
├─────────────────────────────────────────────────────┤
│  DATA SEGMENT (.data)                               │
│  └── Initialized global/static variables           │
├─────────────────────────────────────────────────────┤
│  LOW ADDRESS (0x10000000)                           │
└─────────────────────────────────────────────────────┘

AUTOMOTIVE RULE: MISRA-C forbids dynamic memory (malloc/free)
                 in safety-critical code → stack only!
```

---

## 2.6 FLASH, RAM, EEPROM — AUTOMOTIVE SPECIFICS

### Flash Write Considerations

```c
/* Flash programming is slow — typical AUTOSAR NvM use */

/* WRONG: Write flash in ISR or real-time task */
void ISR_CAN_Rx(void) {
    Fls_Write(address, &data, 4);  /* BLOCKS for 1-2ms! WRONG! */
}

/* CORRECT: Queue the write, process in background task */
void TASK_NvM_1000ms(void) {
    NvM_WriteBlock(NvM_BLOCK_ODOMETER, &odomData);
    /* NvM handles queuing and background flash write */
}
```

### EEPROM Emulation in AUTOSAR

```
AUTOSAR FEE (Flash EEPROM Emulation) Stack:
Application ──► NvM ──► MemIf ──► FEE ──► Fls ──► Flash HW
               (NvM:WriteBlock)    (Fee:Write)  (Fls:Write)

FEE uses Data Flash in bank-switching mode:
• Active Bank: Current valid data
• Shadow Bank: Next write target (copy-on-write)
• After full bank: Garbage collection copies valid pages
```

---

## 2.7 BOOTLOADER

### Automotive ECU Bootloader Architecture

```
ECU POWER ON
     │
     ▼
┌─────────────────────────────────────────────┐
│           PRIMARY BOOTLOADER (PBL)          │
│  • Stored in protected flash                │
│  • Checks if valid application exists       │
│  • Checks update flags                      │
│  • Hardware init (clock, PLL, RAM)          │
└──────────────────┬──────────────────────────┘
                   │
          ┌────────▼──────────┐
          │  Valid App?       │
          │  Update Requested?│
          └────────┬──────────┘
         No update │                     Update Requested
                   │                           │
         ┌─────────▼──────────┐    ┌───────────▼───────────────┐
         │  Application       │    │  Secondary Bootloader (SBL)│
         │  Software          │    │  • Activate DiagSession 0x02│
         │  (AUTOSAR Stack +  │    │  • Receive UDS 0x34 (Request│
         │   Application)     │    │    Download)               │
         └────────────────────┘    │  • Receive 0x36 (Transfer  │
                                   │    Data blocks via Ethernet)│
                                   │  • Erase + Program Flash   │
                                   │  • Verify CRC/Hash         │
                                   │  • Set valid flag → Reset  │
                                   └───────────────────────────┘
```

### UDS Flashing Sequence (DoIP over Ethernet)

```
Tester (CANoe)                    ECU Bootloader
    │                                   │
    │── 0x10 02 (Prog Session) ────────►│
    │◄── 0x50 02 (Positive Response) ───│
    │                                   │
    │── 0x27 01 (Security Access Seed) ►│
    │◄── 0x67 01 <seed bytes> ──────────│
    │                                   │
    │── 0x27 02 <key bytes> ───────────►│
    │◄── 0x67 02 (Access Granted) ──────│
    │                                   │
    │── 0x34 (Request Download)         │
    │   [dataFormat, memAddress, size] ►│
    │◄── 0x74 [blockLen = 0x1000] ──────│
    │                                   │
    │── 0x36 01 [4096 bytes block 1] ──►│
    │◄── 0x76 01 (Transfer OK) ─────────│
    │   ... (repeat for all blocks)     │
    │                                   │
    │── 0x37 (Transfer Exit) ──────────►│
    │◄── 0x77 (OK) ─────────────────────│
    │                                   │
    │── 0x31 FF 01 (Check Memory) ─────►│
    │◄── 0x71 FF 01 (Valid) ────────────│
    │                                   │
    │── 0x11 01 (ECU Reset) ───────────►│
    │◄── ECU reboots to Application ────│
```

---

## 2.8 EMBEDDED C BASICS — AUTOMOTIVE CONTEXT

### Data Types and Sizes (AUTOSAR Standard Types)

```c
/* AUTOSAR Standard Type Definitions (Std_Types.h) */
#include "Std_Types.h"

typedef unsigned char   uint8;   /* 0 to 255          */
typedef unsigned short  uint16;  /* 0 to 65535         */
typedef unsigned long   uint32;  /* 0 to 4,294,967,295 */
typedef unsigned long long uint64; /* 64-bit unsigned  */
typedef signed char     sint8;   /* -128 to 127        */
typedef signed short    sint16;
typedef signed long     sint32;
typedef float           float32;
typedef double          float64;
typedef unsigned char   boolean; /* TRUE/FALSE         */

/* AUTOSAR Standard Return Type */
typedef uint8 Std_ReturnType;
#define E_OK     ((Std_ReturnType)0x00U)
#define E_NOT_OK ((Std_ReturnType)0x01U)
```

### Real Automotive Embedded C Example — CAN Tx Function

```c
/* Send ADAS Object Data over CAN */
Std_ReturnType ADAS_SendObjectData(const AdasObject_t* pObject)
{
    Std_ReturnType ret = E_NOT_OK;
    uint8 canBuffer[8];
    PduInfoType pduInfo;

    /* Validate input */
    if (pObject == NULL_PTR) {
        return E_NOT_OK;
    }

    /* Pack signal: Object distance [15:0] = 0.1m resolution */
    uint16 distanceRaw = (uint16)(pObject->distanceMeters * 10.0f);
    canBuffer[0] = (uint8)(distanceRaw >> 8);    /* High byte */
    canBuffer[1] = (uint8)(distanceRaw & 0xFF);  /* Low byte */

    /* Pack signal: Object speed [31:16] = 0.1 km/h resolution */
    uint16 speedRaw = (uint16)(pObject->speedKmh * 10.0f);
    canBuffer[2] = (uint8)(speedRaw >> 8);
    canBuffer[3] = (uint8)(speedRaw & 0xFF);

    /* Pack signal: TTC (Time-To-Collision) [39:32] = 0.1s resolution */
    canBuffer[4] = (uint8)(pObject->ttcSeconds * 10.0f);

    /* Pack flags in byte 5 */
    canBuffer[5] = 0x00U;
    if (pObject->isValid)  canBuffer[5] |= 0x01U;
    if (pObject->isMoving) canBuffer[5] |= 0x02U;

    canBuffer[6] = 0x00U;
    canBuffer[7] = 0x00U;

    /* Send via AUTOSAR PDUR */
    pduInfo.SduDataPtr = canBuffer;
    pduInfo.SduLength  = 8U;

    ret = Com_SendSignalGroup(ADAS_OBJECT_PDU_ID, &pduInfo);

    return ret;
}
```

---

## 2.9 BITWISE OPERATIONS — AUTOMOTIVE SIGNAL PACKING

### Why Bit Manipulation Matters

In automotive ECUs, signals are packed into bytes in CAN/Ethernet frames using specific bit positions defined by the DBC/ARXML signal layout.

```c
/* Example: Extracting signals from a raw CAN frame */
/* CAN ID: 0x200 — ABS Status Frame */
/* Byte 0: ABS_Active[7], Traction_Control[6], ESP_Active[5] */
/* Byte 1-2: Wheel_Speed_FL [15:0] — Intel byte order, factor 0.01 km/h */

void ABS_ParseFrame(const uint8* rawData, ABS_Status_t* pStatus)
{
    /* Extract single-bit flags from byte 0 */
    pStatus->absActive         = (rawData[0] >> 7) & 0x01U;
    pStatus->tractionControl   = (rawData[0] >> 6) & 0x01U;
    pStatus->espActive         = (rawData[0] >> 5) & 0x01U;

    /* Extract 16-bit wheel speed (Intel byte order = little-endian) */
    uint16 rawSpeed = ((uint16)rawData[2] << 8) | rawData[1];
    pStatus->wheelSpeedFL_kmh = (float32)rawSpeed * 0.01f;

    /* Extract 4-bit fault code from bits [3:0] of byte 0 */
    pStatus->faultCode = rawData[0] & 0x0FU;
}

/* Signal Packing — Setting individual bits */
void ABS_BuildFrame(const ABS_Status_t* pStatus, uint8* rawData)
{
    rawData[0] = 0x00U;

    /* Set ABS_Active at bit 7 */
    if (pStatus->absActive)
        rawData[0] |= (1U << 7);

    /* Set multiple bits using OR mask */
    rawData[0] |= ((pStatus->faultCode & 0x0FU));  /* bits 3:0 */

    /* Wheel speed packing — Intel byte order */
    uint16 rawSpeed = (uint16)(pStatus->wheelSpeedFL_kmh / 0.01f);
    rawData[1] = (uint8)(rawSpeed & 0xFFU);         /* Low byte first */
    rawData[2] = (uint8)((rawSpeed >> 8) & 0xFFU);  /* High byte */
}
```

### Bit Manipulation Cheat Sheet

```c
/* Common bit operations */

/* Set bit N */
value |= (1U << N);

/* Clear bit N */
value &= ~(1U << N);

/* Toggle bit N */
value ^= (1U << N);

/* Check if bit N is set */
if (value & (1U << N)) { /* bit is set */ }

/* Extract bits [hi:lo] from value */
uint8 extract_bits(uint32 value, uint8 hi, uint8 lo) {
    uint32 mask = (1U << (hi - lo + 1)) - 1U;
    return (uint8)((value >> lo) & mask);
}

/* Example: Extract bits [5:3] from 0xAB = 1010 1011 */
/* Bits [5:3] = 010 = 0x02 */
uint8 result = extract_bits(0xABU, 5, 3);  /* result = 2 */
```

---

## 2.10 POINTERS — AUTOMOTIVE C

```c
/* Function pointer — used heavily in AUTOSAR BSW callbacks */
typedef void (*CallbackFunc_t)(void);

/* Register callback for Ethernet Rx notification */
static CallbackFunc_t EthRx_Callback = NULL_PTR;

void Eth_RegisterRxCallback(CallbackFunc_t callback) {
    EthRx_Callback = callback;
}

/* Called from Eth driver ISR */
void ISR_Eth_FrameReceived(void) {
    if (EthRx_Callback != NULL_PTR) {
        EthRx_Callback();
    }
}

/* Pointer to structure — ECU data access */
typedef struct {
    uint8  frameId;
    uint16 length;
    uint8  payload[1518];
} EthFrame_t;

void processFrame(EthFrame_t* pFrame) {
    if (pFrame == NULL_PTR) return;
    /* Access struct members via pointer */
    pFrame->frameId = 0x01U;
    pFrame->length  = 64U;
    /* Array access via pointer arithmetic */
    *(pFrame->payload + 0) = 0xFFU; /* Broadcast destination */
}

/* Double pointer — output parameter pattern (AUTOSAR style) */
Std_ReturnType Eth_GetTxBuffer(uint8** ppBuffer, uint16* pLength) {
    static uint8 txBuf[1518];
    *ppBuffer = txBuf;        /* Return pointer to buffer */
    *pLength  = sizeof(txBuf);
    return E_OK;
}
```

---

## 2.11 VOLATILE KEYWORD

### Why Volatile Is Critical in Embedded Systems

```c
/* WITHOUT volatile — compiler optimizes away reads */
uint32 registerValue = PERIPHERAL_STATUS_REG;  /* Read once */
while (registerValue == 0) {                    /* Loop forever! */
    /* Compiler sees no change — optimizes to infinite loop */
    /* Does NOT re-read register — BUG! */
}

/* WITH volatile — forces re-read every iteration */
volatile uint32* pStatusReg = (volatile uint32*)0xF0010000;
while (*pStatusReg == 0) {
    /* Forces actual memory read each iteration — CORRECT */
}

/* Common volatile uses in automotive */
volatile uint32 g_systemTick;          /* Updated by OS timer ISR */
volatile uint8  g_ethFrameReceived;    /* Set by Ethernet ISR */
volatile uint8* CAN_STATUS_REG;        /* Hardware register */

/* Example: CAN status register polling */
#define CAN0_SR   (*((volatile uint32*)0xF0208000UL))

void waitForCanTxComplete(void) {
    uint32 timeout = 10000U;
    while ((CAN0_SR & 0x04U) == 0U && timeout > 0U) {
        timeout--;  /* Polls actual register each time */
    }
}
```

---

## 2.12 STATIC KEYWORD — AUTOMOTIVE C

```c
/* static local variable — persists across calls (no re-init) */
void ADAS_UpdateFrameCounter(void) {
    static uint32 frameCount = 0U;  /* Initialized ONCE at startup */
    frameCount++;
    /* frameCount retains value between calls */
    if (frameCount >= 100U) {
        triggerDiagReport();
        frameCount = 0U;
    }
}

/* static global — visible only within this .c file (encapsulation) */
static uint8 ethRxBuffer[1518];        /* Private to Eth_Driver.c */
static EthConfig_t ethConfig;          /* Module-private config */

/* static function — cannot be called from other modules */
static void Eth_InternalFlushBuffer(void) {
    /* Helper function, not part of public API */
    (void)memset(ethRxBuffer, 0, sizeof(ethRxBuffer));
}

/* Public API function (no static keyword) */
Std_ReturnType Eth_Receive(uint8* pBuffer, uint16* pLength) {
    Eth_InternalFlushBuffer();  /* Can call private function */
    /* ... */
    return E_OK;
}
```

---

## 2.13 MEMORY DIAGRAMS — INTERVIEW READY

### Complete RAM Layout for an AUTOSAR ECU Task

```
TASK Stack Frame for ADAS_Task_10ms():
┌─────────────────────────────────┐ ← Top of Stack (before call)
│  Saved LR (Link Register)       │
│  Saved R4-R11 (callee-saved)    │
├─────────────────────────────────┤
│  Local: AdasObject_t obj[10]    │ ← 10 × 20 bytes = 200 bytes
│  Local: uint32 loopCounter = 0  │ ← 4 bytes
│  Local: float32 ttc = 0.0       │ ← 4 bytes
├─────────────────────────────────┤ ← Frame Pointer (FP)
│  Argument: pConfig (pointer)    │ ← 4 bytes (32-bit ptr)
└─────────────────────────────────┘ ← Stack Pointer (SP) after alloc
```

### AUTOSAR Memory Sections

```c
/* AUTOSAR memory section placement pragmas */

/* Code in fast execution memory (ITCM) */
#define ADAS_START_SEC_CODE_FAST
#include "MemMap.h"
void ADAS_CriticalFunction(void) { /* ... */ }
#define ADAS_STOP_SEC_CODE_FAST
#include "MemMap.h"

/* 8-bit variables initialized to 0 (BSS) */
#define ADAS_START_SEC_VAR_INIT_8BIT
#include "MemMap.h"
static uint8 adas_state = ADAS_STATE_INIT;
#define ADAS_STOP_SEC_VAR_INIT_8BIT
#include "MemMap.h"

/* Calibration data — in Data Flash (read-only at runtime) */
#define ADAS_START_SEC_CONST_32BIT
#include "MemMap.h"
const uint32 ADAS_WARNING_DISTANCE_MM = 5000U;  /* 5 meters */
#define ADAS_STOP_SEC_CONST_32BIT
#include "MemMap.h"
```

---

## 2.14 INTERVIEW QUESTIONS — SECTION 2

**Q1: What is the difference between stack and heap in an embedded system?**

> Stack is statically allocated, LIFO (Last In First Out), used for local variables and function call frames. It grows downward. Heap is dynamically allocated using `malloc()`/`free()`. In MISRA-C and ISO 26262 safety-critical code, dynamic heap allocation is forbidden because it can cause fragmentation, non-deterministic allocation time, and dangling pointer bugs. All memory in safety ECUs is stack or statically allocated global arrays.

**Q2: Why is the `volatile` keyword important in embedded systems?**

> The `volatile` qualifier tells the compiler to always re-read the variable from actual memory rather than using a cached register value. This is critical for hardware registers (CAN, Ethernet status registers), variables shared between an ISR and main code, and DMA-filled buffers. Without `volatile`, the compiler's optimizer may eliminate reads it considers "redundant," causing bugs that only appear in release builds.

**Q3: What is the role of an RTOS in an automotive ECU?**

> An RTOS provides deterministic task scheduling, ensuring safety-critical tasks (e.g., ABS control at 1ms) always complete within their deadline. AUTOSAR OS uses rate monotonic scheduling (RMS) where higher-frequency tasks have higher priority. The OS handles task activation via alarms (timers), manages ISR nesting, and provides inter-task communication primitives (events, resources/mutexes).

**Q4: Explain the AUTOSAR NvM stack and why direct flash writes should be avoided in tasks.**

> Flash write operations can take 1–5ms per page, which would violate real-time task deadlines. AUTOSAR NvM provides a write queue: application calls `NvM_WriteBlock()`, which queues the request. The NvM background task (typically 10ms or 1s cycle) processes queued writes asynchronously via the MemIf → FEE → Fls stack. This keeps application tasks deterministic while ensuring data persistence.

**Q5: What is a function pointer and where is it used in AUTOSAR?**

> A function pointer is a variable that holds the address of a function, enabling runtime-configurable callbacks. In AUTOSAR, function pointers are used extensively: CAN receive indication callbacks (`CanIf_RxIndication`), Ethernet frame receive notifications, diagnostic request callbacks in DCM, and initialization callbacks in the BSW module initialization sequence. They enable the modular, vendor-independent AUTOSAR architecture.

**Q6: Explain memory sections in AUTOSAR and why they matter.**

> AUTOSAR uses linker sections to place code and data in specific memory regions. For example, fast-executing ISR code is placed in ITCM (Instruction Tightly Coupled Memory) for single-cycle fetch. Calibration constants go to data flash so they survive power cycles. NvM variables are placed in sections that map to DFLASH. The `MemMap.h` include mechanism and `#pragma` section switches are used to achieve this placement without touching the linker script for each module.

---

*Next Section → [Section 3: Automotive Communication Protocols](03_Communication_Protocols.md)*
