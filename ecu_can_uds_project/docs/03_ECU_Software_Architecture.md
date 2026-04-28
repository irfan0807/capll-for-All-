# ECU Software Architecture – Real-World Design

## 1. What is an ECU?

An **Electronic Control Unit (ECU)** is a microcontroller-based embedded system that:
- Reads sensor inputs (analog, digital, CAN messages)
- Executes control algorithms
- Drives actuators (relays, motors, injectors)
- Communicates via CAN/LIN/Ethernet
- Responds to diagnostic requests (UDS)

---

## 2. ECU Hardware Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                          ECU Hardware                              │
│                                                                    │
│  ┌──────────┐   ┌──────────────────────────────────────────────┐  │
│  │  Power   │   │              Microcontroller (MCU)           │  │
│  │  Supply  │   │  ┌─────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │ (5V/3.3V)│   │  │   CPU   │ │  Flash   │ │     RAM      │  │  │
│  └──────────┘   │  │(e.g.    │ │ (Code +  │ │ (Stack/Heap) │  │  │
│                 │  │ TC397)  │ │  NVM Cal)│ │              │  │  │
│  ┌──────────┐   │  └────┬────┘ └──────────┘ └──────────────┘  │  │
│  │ Watchdog │   │       │  Buses (AHB/APB)                     │  │
│  │   IC     │   │  ┌────┴────────────────────────────────┐     │  │
│  └──────────┘   │  │ Peripherals:                        │     │  │
│                 │  │ CAN FD × 4 | ADC × 2 | PWM × 16    │     │  │
│  ┌──────────┐   │  │ LIN × 4   | SPI × 4 | I2C × 2     │     │  │
│  │  CAN     │   │  │ FlexRay × 1| ETH × 1 | SENT × 8   │     │  │
│  │Transceiver│  │  └────────────────────────────────────┘     │  │
│  └──────────┘   └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

**Common MCUs in Automotive:**
- Infineon AURIX TC3xx/TC4xx (Safety-grade, multi-core)
- Renesas RH850 series
- NXP S32K3xx
- STM32 (lower ASIL applications)

---

## 3. ECU Software Layered Architecture (AUTOSAR-inspired)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer (ASW)                      │
│         Control Algorithms | State Machines | Calibration       │
├─────────────────────────────────────────────────────────────────┤
│                    Runtime Environment (RTE)                    │
│            Port interfaces | Inter-component communication      │
├────────────────────────┬────────────────────────────────────────┤
│    Service Layer       │          ECU Abstraction Layer         │
│  OS (OSEK/AUTOSAR OS)  │    CAN Interface | NVM | Watchdog      │
│  ComStack (PduR/CanIF) │    EEPROM | ADC Abs | PWM Abs          │
├────────────────────────┴────────────────────────────────────────┤
│                   Microcontroller Abstraction Layer (MCAL)      │
│           CAN Driver | ADC Driver | PWM Driver | SPI Driver     │
├─────────────────────────────────────────────────────────────────┤
│                         Hardware (MCU)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. AUTOSAR Communication Stack

```
Application SW Component
         │
         ▼  (I-PDU)
    ┌──────────┐
    │  COM     │  Signal packing/unpacking, filtering, timeouts
    └─────┬────┘
          │ (I-PDU)
    ┌─────▼────┐
    │  PduR    │  PDU Router – routing between modules
    └─────┬────┘
          │  (L-PDU)
    ┌─────▼────┐         ┌─────────────┐
    │  CanIF   │         │   CanNm     │  Network Management
    └─────┬────┘         └─────────────┘
          │  (CAN Frame)
    ┌─────▼────┐
    │  CanDrv  │  CAN Driver (MCAL) – directly accesses CAN hardware
    └──────────┘
          │
     CAN Bus
```

---

## 5. OSEK/AUTOSAR OS – Task Scheduling

```cpp
// Task priorities and periods (typical engine ECU)

// 1ms task – high frequency, time-critical
TASK(Task_1ms) {
    CAN_RxProcessing();
    SensorRead_Fast();
    ClosedLoopControl();
    TerminateTask();
}

// 10ms task – medium frequency
TASK(Task_10ms) {
    DiagnosticsUpdate();
    SignalFiltering();
    StateMachine_Run();
    TerminateTask();
}

// 100ms task – slow background
TASK(Task_100ms) {
    NVM_Write();
    DTC_Processing();
    UDS_SessionTimerUpdate();
    TerminateTask();
}

// Background task
TASK(Task_Background) {
    while(1) {
        Watchdog_Service();
        IdleProcessing();
    }
}
```

**Task states:**

```
              ┌──────────┐
              │ Suspended│◄─── ActivateTask()
              └────┬─────┘
                   │
              ┌────▼─────┐
              │  Ready   │
              └────┬─────┘
                   │  Scheduler selects
              ┌────▼─────┐
              │ Running  │──── preempted ──► Ready
              └────┬─────┘
                   │  TerminateTask()
              ┌────▼─────┐
              │ Suspended│
              └──────────┘
```

---

## 6. NVM (Non-Volatile Memory) Management

```
┌────────────────────────────────────────────────────────┐
│                    Flash Memory Map                    │
│                                                        │
│  0x80000000 ┌──────────────────────┐                  │
│             │   Bootloader         │  64 KB           │
│  0x80010000 ├──────────────────────┤                  │
│             │   Application Code   │  512 KB          │
│  0x80090000 ├──────────────────────┤                  │
│             │   Calibration Data   │  64 KB (DFLASH)  │
│  0x800A0000 ├──────────────────────┤                  │
│             │   NVM Parameters     │  32 KB (EEPROM   │
│             │   (DTC, odometer,    │   emulated)      │
│             │    adaptations)      │                  │
│  0x800A8000 └──────────────────────┘                  │
└────────────────────────────────────────────────────────┘
```

---

## 7. State Machine Design Pattern (ECU)

```
┌──────────────────────────────────────────────────────────────┐
│                  Engine Control State Machine                │
│                                                              │
│  ┌──────────┐  IGN_ON   ┌──────────┐  CRANK   ┌──────────┐ │
│  │  POWER   │──────────►│  INIT    │──────────►│ CRANKING │ │
│  │  OFF     │           │          │           │          │ │
│  └──────────┘           └──────────┘           └────┬─────┘ │
│       ▲                                             │RPM>500 │
│       │                                        ┌────▼─────┐  │
│  IGN_OFF                                       │ RUNNING  │  │
│       │                                        └────┬─────┘  │
│  ┌────┴─────┐                                       │        │
│  │ SHUTDOWN │◄──────────────────────────── IGN_OFF  │        │
│  └──────────┘                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 8. Diagnostics Integration in ECU

```
Request arrives (CAN Rx interrupt)
         │
         ▼
    ┌──────────────────────────────────┐
    │         ISO-TP Layer             │
    │  Reassemble segmented messages   │
    └──────────────┬───────────────────┘
                   │ Complete UDS PDU
                   ▼
    ┌──────────────────────────────────┐
    │         UDS Server               │
    │  Session Manager                 │
    │  Security Manager                │
    │  Service Dispatcher              │
    └──┬──────────┬──────────┬─────────┘
       │          │          │
       ▼          ▼          ▼
   ┌───────┐ ┌───────┐ ┌──────────┐
   │ 0x22  │ │ 0x19  │ │  0x27    │
   │ RDBI  │ │ DTC   │ │ Security │
   └───────┘ └───────┘ └──────────┘
```

---

## 9. Watchdog Strategy

```
Types:
  1. Internal Watchdog (on-chip)   – processor hang detection
  2. External Watchdog (SBC/PMIC)  – power supply management
  3. Functional Watchdog (SW)      – algorithm monitoring

Servicing Pattern:
  ┌─────────────────────────────────────────────────┐
  │  TASK_1ms: Watchdog_TriggerInternal()           │
  │  TASK_10ms: Watchdog_TriggerExternal()          │
  │  TASK_1ms: Watchdog_CheckAlive_Task10ms()       │
  │            Watchdog_CheckAlive_Task100ms()      │
  └─────────────────────────────────────────────────┘

If WD expires → Reset or Safe State → Log DTC → Recovery
```

---

## 10. Real-World ECU Software Development Flow

```
Requirements (DOORS/JAMA)
         │
         ▼
Architecture Design (EA/MATLAB)
         │
         ▼
SW Design (UML, Rhapsody)
         │
         ▼
Code Generation / Manual Coding
│  AUTOSAR tools: EB Tresos, Vector DaVinci
│  Model-based: MATLAB/Simulink + Embedded Coder
│  Manual: C/C++ with MISRA compliance
         │
         ▼
Static Analysis (Polyspace, PC-lint, Klocwork)
         │
         ▼
Unit Test (VectorCAST, CAPL, GoogleTest)
         │
         ▼
Integration Test (HIL – dSPACE/NI VeriStand)
         │
         ▼
System Test (Vehicle level)
         │
         ▼
Release & Homologation
```
