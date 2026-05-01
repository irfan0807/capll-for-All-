# CAN vs CAN FD vs CAN TP — When to Use, Why & Error Handling
### Detailed Technical Guide with Protocol Diagrams and STAR Scenarios

---

## TABLE OF CONTENTS

1. [Protocol Overview](#1-protocol-overview)
2. [Classical CAN — When to Use](#2-classical-can--when-to-use)
3. [CAN FD — When to Use](#3-can-fd-flexible-data-rate--when-to-use)
4. [CAN TP — When to Use](#4-can-tp-iso-15765-2--when-to-use)
5. [Decision Framework](#5-decision-framework--which-protocol-to-choose)
6. [STAR Scenarios](#6-star-scenarios)
7. [Quick Reference Summary](#7-quick-reference-summary)
8. [Common Mistakes to Avoid](#8-common-mistakes-to-avoid)
9. [Error Handling — CAN / CAN FD / CAN TP](#9-error-handling--can--can-fd--can-tp)
   - 9.1 [Classical CAN Error Types](#91-classical-can-error-types)
   - 9.2 [CAN FD Error Differences](#92-can-fd-error-differences)
   - 9.3 [Error Confinement — TEC / REC State Machine](#93-error-confinement--tec--rec-state-machine)
   - 9.4 [CAN TP Transport-Layer Errors](#94-can-tp-transport-layer-errors)
   - 9.5 [Error Comparison Table](#95-error-comparison-table)
   - 9.6 [Error Propagation Diagram](#96-error-propagation-diagram)
   - 9.7 [CAPL Error Detection Snippets](#97-capl-error-detection-snippets)

---

## 1. Protocol Overview

| Feature | CAN (Classical) | CAN FD | CAN TP (ISO 15765-2) |
|---------|----------------|--------|----------------------|
| Standard | ISO 11898-1 (2003) | ISO 11898-1 (2015) | ISO 15765-2 |
| Max Data | 8 bytes/frame | 64 bytes/frame | Up to 4095 bytes (segmented) |
| Nominal Bit Rate | Up to 1 Mbit/s | Up to 1 Mbit/s | Same as underlying CAN/CAN FD |
| Data Phase Rate | N/A (single rate) | Up to 8 Mbit/s | N/A (transport layer) |
| Arbitration | CSMA/CA | CSMA/CA | Same as underlying bus |
| Real-Time | Yes | Yes (better) | Not real-time (connection overhead) |
| Layer | Data Link Layer (L2) | Data Link Layer (L2) | Transport Layer (L4) |
| Use Case | Periodic signals, control | High-bandwidth signals, calibration | Diagnostics, UDS, large data transfer |
| Error Detection | CRC-15 | CRC-17 or CRC-21 | Uses underlying CAN CRC |

---

## 2. Classical CAN — When to Use

### 2.1 Technical Characteristics
- **Frame formats:** Base Frame (11-bit ID) and Extended Frame (29-bit ID)
- **Max payload:** 8 bytes per frame
- **Bit rate:** Up to 1 Mbit/s (typical: 125 kbit/s, 250 kbit/s, 500 kbit/s)
- **Arbitration:** Non-destructive bitwise CSMA/CA (dominant bit wins)
- **Error detection:** Bit stuffing, CRC-15, Frame check, ACK check
- **Bus topology:** Multi-master, differential two-wire (CAN_H / CAN_L)

### 2.2 When to Use Classical CAN

**Use Classical CAN when:**

| Condition | Reason |
|-----------|--------|
| Data fits in ≤8 bytes | No segmentation needed, low overhead |
| Real-time, periodic signals (≤50ms cycle) | Deterministic latency |
| Safety-critical control signals | Well-proven, ISO 26262 certified implementations widespread |
| Low-cost ECU budget | CAN controllers are cheap, widely available |
| Network data rate ≤500 kbit/s | No bandwidth bottleneck |
| Legacy systems integration | Full backward compatibility |
| Body control, lighting, HVAC | Low data volume, simple I/O |

### 2.3 Typical Signals on Classical CAN

```
Engine RPM           → 2 bytes  (16-bit integer)
Vehicle Speed        → 2 bytes  (uint16 × 0.01 km/h)
Throttle Position    → 1 byte   (0–100%)
Door Status          → 1 byte   (bitmask)
Warning Lamps        → 1 byte   (bitmask)
Gear Position        → 1 byte   (enum)
Fuel Level           → 1 byte   (0–255 = 0–100%)
Coolant Temperature  → 1 byte   (offset +40°C)
```

All fit comfortably in 8-byte frames — no transport protocol required.

### 2.4 Frame Structure

```
┌──────────┬─────┬──────┬───────────────┬───────┬─────┬─────┐
│  SOF (1) │ ID  │ DLC  │  Data (0-8 B) │ CRC15 │ ACK │ EOF │
│          │11/29│ (4b) │               │       │(2b) │(7b) │
└──────────┴─────┴──────┴───────────────┴───────┴─────┴─────┘
```

---

## 3. CAN FD (Flexible Data-Rate) — When to Use

### 3.1 Technical Characteristics
- **Introduced:** Bosch, 2012; standardized ISO 11898-1:2015
- **Two bit-rate phases:**
  - **Nominal phase** (arbitration): Same as Classical CAN, up to 1 Mbit/s
  - **Data phase**: Up to 8 Mbit/s (typically 2–5 Mbit/s in production)
- **Max payload:** 64 bytes per frame (DLC 0–8 map same; DLC 9–15 map 12,16,20,24,32,48,64)
- **CRC:** CRC-17 for ≤16 bytes, CRC-21 for >16 bytes (stronger than CAN's CRC-15)
- **No remote frames:** CAN FD drops RTR (Remote Transmission Request)
- **Bit Rate Switch (BRS):** Control bit enables switching to faster data rate mid-frame
- **Error State Indicator (ESI):** Node indicates its error state in the frame

### 3.2 When to Use CAN FD

**Use CAN FD when:**

| Condition | Reason |
|-----------|--------|
| Data payload between 9–64 bytes per frame | Eliminates multi-frame workarounds |
| High sample rate sensor data (camera, radar, lidar) | More bytes per frame at higher speed |
| ADAS ECUs requiring <5ms cycle for large signals | Data phase up to 8 Mbit/s |
| OTA firmware download over CAN | 64-byte frames reduce frame count for large blocks |
| Calibration data (XCP over CAN FD) | Faster memory read/write |
| Modern powertrain (EV battery cell data, motor control) | BMS requires many cell voltages per cycle |
| Replacing CAN where bandwidth is a bottleneck | Same 2-wire physical layer, software upgrade |
| Reducing bus load on existing 500 kbit/s networks | Higher data rate = more data in same time window |

### 3.3 CAN FD vs Classical CAN — Bandwidth Comparison

Sending 64 bytes of sensor data every 10 ms:

**Classical CAN (500 kbit/s):**
- Need 8 frames (8 × 8 = 64 bytes)
- Each frame ~130 bits → 8 × 130 = 1040 bits
- At 500 kbit/s → 2.08 ms per batch
- Bus load contribution: ~20.8%

**CAN FD (500 kbit/s nominal / 2 Mbit/s data):**
- 1 frame (64 bytes)
- ~600 bits at mixed rate → ~0.4 ms per batch
- Bus load contribution: ~4%
- **Result: ~5× less bus load**

### 3.4 CAN FD Frame Structure

```
┌────┬────────┬─────┬─────┬─────┬──────────────────┬────────┬─────┬─────┐
│SOF │ ID     │ FDF │ BRS │ ESI │ Data (up to 64 B)│CRC17/21│ ACK │ EOF │
│    │ 11/29b │ =1  │     │     │                  │        │     │     │
└────┴────────┴─────┴─────┴─────┴──────────────────┴────────┴─────┴─────┘
     ←— Nominal bit rate ——→←————— Data bit rate (if BRS=1) ————→
```

- **FDF (FD Frame):** = 1 identifies CAN FD frame
- **BRS (Bit Rate Switch):** = 1 switches to higher data rate for payload
- **ESI (Error State Indicator):** = 0 Error Active, = 1 Error Passive

### 3.5 DLC to Byte Count Mapping (CAN FD)

| DLC | Bytes |
|-----|-------|
| 0–8 | 0–8 (same as CAN) |
| 9 | 12 |
| 10 | 16 |
| 11 | 20 |
| 12 | 24 |
| 13 | 32 |
| 14 | 48 |
| 15 | 64 |

---

## 4. CAN TP (ISO 15765-2) — When to Use

### 4.1 What is CAN TP?
CAN TP (Transport Protocol) is **not a physical protocol** — it is a **transport layer** built on top of Classical CAN or CAN FD. Defined in ISO 15765-2, it enables transmission of payloads **larger than 8 bytes** (CAN) or **64 bytes** (CAN FD) by segmenting data into multiple frames with flow control.

### 4.2 Why CAN TP is Needed
UDS (ISO 14229) diagnostic messages often carry:
- VIN numbers (17 bytes)
- ECU software versions (variable length)
- DTC records (multiple DTCs × multiple bytes each)
- Flash programming data blocks (kilobytes to megabytes)

None of these fit in a single classical CAN frame. CAN TP provides the segmentation, reassembly, and flow control to make this work reliably.

### 4.3 CAN TP Frame Types

| Frame Type | PCI Byte | Description |
|-----------|---------|-------------|
| **SF (Single Frame)** | byte0[7:4] = 0x0 | Entire PDU in one frame (≤7 bytes on CAN, ≤62 on CAN FD) |
| **FF (First Frame)** | byte0[7:4] = 0x1 | First segment of multi-frame message; includes total length |
| **CF (Consecutive Frame)** | byte0[7:4] = 0x2 | Subsequent segments; sequence number byte0[3:0] = 1–15 |
| **FC (Flow Control)** | byte0[7:4] = 0x3 | Receiver controls sender: ContinueToSend / Wait / Overflow |

### 4.4 Flow Control Parameters

```
FC Frame:
  byte0 = 0x30 (FS=0: ContinueToSend) / 0x31 (FS=1: Wait) / 0x32 (FS=2: Overflow)
  byte1 = BlockSize (BS): Number of CF frames before next FC (0 = send all)
  byte2 = STmin: Minimum separation time between CF frames
          0x00–0x7F = 0–127 ms
          0xF1–0xF9 = 100–900 µs
```

### 4.5 CAN TP Message Flow Example (UDS ReadDTCInfo)

```
Tester (0x744) → ECU (0x7E0)          ECU (0x7EC) → Tester (0x74C)

FF: [10 1A 19 02 09]  ← Send 26 bytes  FF: [10 2E 59 02 09 ...]  ← ECU responds with 46 bytes
                                         SF(sent by tester):
FC: [30 00 00]        ← ContinueToSend  CF: [21 xx xx xx xx xx xx]
                                         CF: [22 xx xx xx xx xx xx]
                                         CF: [23 xx xx xx xx xx xx]
                                         CF: [24 xx xx xx xx xx xx]
                                         CF: [25 xx xx xx xx xx xx]
                                         CF: [26 xx xx xx xx xx xx]
```

### 4.6 When to Use CAN TP

**Use CAN TP when:**

| Condition | Reason |
|-----------|--------|
| Single UDS service (0x22, 0x27, 0x2E, 0x31, 0x34, 0x36) | All UDS is mandatory over ISO 15765-2 |
| Reading DTC records (0x19) | Multiple DTCs → response > 8 bytes |
| ECU flash programming (0x34/0x36/0x37) | Block sizes from 256 bytes to multiple MB |
| Reading ECU VIN, software version (0x22 F190, F189) | Multiple bytes of ASCII data |
| OBD-II communication (SAE J1979 / ISO 15031) | Mandated by regulation |
| Key programming, coding, adaptation | Dealer tool sessions use UDS over CAN TP |
| End-of-line (EOL) flashing at factory | All ECU programming uses CAN TP |
| Telematics remote diagnostics | Off-board server uses UDS over CAN TP tunneled via IP |

**Do NOT use CAN TP for:**
- Real-time periodic signals (use raw CAN or CAN FD instead)
- Safety-critical control loops (CAN TP has variable latency)
- Signals that change faster than 20 ms (CAN TP overhead is too high)

---

## 5. Decision Framework — Which Protocol to Choose?

```
                    ┌─────────────────────────────────┐
                    │ What is the data size?           │
                    └────────────┬────────────────────┘
                                 │
               ┌─────────────────┼──────────────────┐
               ▼                 ▼                   ▼
          ≤ 8 bytes          9–64 bytes         > 64 bytes
               │                 │                   │
               ▼                 ▼                   ▼
    ┌──────────────────┐ ┌───────────────┐ ┌─────────────────────┐
    │ Is it real-time? │ │ Is bandwidth  │ │ Is it diagnostic?   │
    └────────┬─────────┘ │ critical?     │ └──────────┬──────────┘
             │           └───────┬───────┘            │
      Yes    │ No        Yes     │ No            Yes  │ No
      │      │           │       │               │    │
      ▼      ▼           ▼       ▼               ▼    ▼
  Classic  Classic    CAN FD  CAN FD +      CAN TP   Not a good
  CAN      CAN        Native  CAN TP        over CAN   fit for
  (raw     + CAN TP            (transport)  or CAN FD  CAN bus
  frame)   if needed                                  (use ETH)
```

---

## 6. STAR Scenarios

---

### STAR Scenario 1 — Using Classical CAN for Real-Time Powertrain Control

**Situation:**
You are an automotive test engineer at a Tier 1 supplier working on a 6-speed automatic transmission ECU (TCU) integration. The TCU must exchange gear position, engine torque request, and turbine speed data with the Engine Control Module (ECM) every 10ms. The vehicle network is a legacy 500 kbit/s CAN network used in a mid-range sedan project (2024 model year, no CAN FD requirement in the spec).

**Task:**
Select the correct CAN variant and frame strategy for TCU–ECM real-time communication. Justify the choice and design the message layout within the constraints of the existing network.

**Action:**
1. Reviewed the signal list:
   - `TCU_GearPosition` → 1 byte (enum: P/R/N/1–6)
   - `TCU_TorqueRequest` → 2 bytes (uint16, Nm × 4)
   - `TCU_TurbineSpeed` → 2 bytes (uint16, RPM × 1)
   - `ECM_EngineSpeed` → 2 bytes (already broadcast by ECM)
   - `ECM_AcceleratorPedal` → 1 byte (0–100%)
   - Total: 6 bytes of TCU data, fits in a single 8-byte CAN frame with 2 bytes spare

2. Chose **Classical CAN** at 500 kbit/s because:
   - All signals fit in 8 bytes (no segmentation needed)
   - 10ms cycle time is feasible — a single frame at 500 kbit/s takes ~0.22ms
   - Legacy network with classical CAN controllers in all ECUs
   - AUTOSAR COM layer configured for PDU with 10ms cyclic trigger

3. Designed CAN frame 0x320 (`TCU_PowertrainData`):
   ```
   Byte 0: GearPosition (enum 0=P,1=R,2=N,3=1,4=2,5=3,6=4,7=5,8=6)
   Byte 1-2: TorqueRequest (uint16 BE, Nm×4)
   Byte 3-4: TurbineSpeed (uint16 BE, RPM)
   Byte 5: ShiftStatus (0=idle,1=shifting,2=complete)
   Byte 6: TCC_Status (Torque Converter Clutch: 0=open,1=slip,2=locked)
   Byte 7: Checksum (XOR bytes 0-6)
   ```

4. Validated cycle timing with CANalyzer: confirmed 10ms ±2ms jitter within spec.

**Result:**
The TCU–ECM interface passed all HIL timing tests. Bus load contribution was 2.3% (well within the 30% target). No retransmissions were observed. Classical CAN proved entirely adequate — using CAN FD would have added unnecessary cost and complexity to a legacy system without measurable benefit.

**Key Lesson:** *Classical CAN is the right choice when data is ≤8 bytes, timing requirements are ≥5ms, and the network is within bandwidth limits. Avoid over-engineering with CAN FD purely because it exists.*

---

### STAR Scenario 2 — Using CAN FD for ADAS Radar Object List

**Situation:**
You are a validation engineer on an ADAS project for a front radar sensor (77 GHz, ISO 26262 ASIL-B). The radar ECU must transmit an object list containing up to 8 tracked objects every 50ms. Each object carries: object ID (1B), distance X/Y (2+2B), velocity X/Y (2+2B), RCS value (1B), confidence level (1B) — totalling 11 bytes per object. With 8 objects: 88 bytes per cycle. The existing powertrain CAN runs at 500 kbit/s classical CAN. The ADAS gateway connects to a dedicated ADAS CAN network.

**Task:**
Determine whether Classical CAN, CAN FD, or Automotive Ethernet is appropriate for the radar object list transmission, and define a protocol strategy that achieves the 50ms cycle constraint with acceptable bus load.

**Action:**
1. Calculated bandwidth requirements:
   - Classical CAN: 88 bytes = 11 frames × ~130 bits = 1430 bits every 50ms at 500 kbit/s → 1430/25000 = **5.72% bus load** (feasible but uses 11 CAN IDs)
   - CAN FD: 88 bytes fits in **2 CAN FD frames** (64+24 bytes) at 2 Mbit/s data phase → 2 × ~500 bits at mixed rate ≈ 0.1ms → **~0.2% bus load**

2. Chose **CAN FD** at 1 Mbit/s nominal / 2 Mbit/s data because:
   - 88 bytes in 2 frames vs 11 frames on classical CAN
   - Reduces message IDs — simpler DBC/ARXML management
   - ADAS gateway ECU (NXP S32G) supports CAN FD natively
   - ISO 26262 ASIL-B: CAN FD CRC-17/21 provides stronger error detection than CRC-15
   - Future-proof: lidar point-cloud data (next year's program) won't fit on classical CAN

3. Designed two CAN FD frames:
   - `0x300` (64 bytes): Objects 1–5 packed (11B each + 9B header with timestamp, object count)
   - `0x301` (36 bytes, DLC=32): Objects 6–8 packed + 8B CRC safety wrapper (AUTOSAR E2E Profile 4)

4. Added E2E protection (AUTOSAR E2E Profile 4) because the sensor data is ASIL-B — CRC32 + counter in header bytes.

5. Validated with CAPL test script: measured actual bus latency from radar sensor trigger to gateway reception = 1.2ms (well within 50ms requirement).

**Result:**
The CAN FD solution reduced the ADAS CAN bus load from a projected 34% (11 classical CAN frames × 3 sensors) to under 6% (2 CAN FD frames × 3 sensors). ASIL-B E2E protection requirements were met. The gateway routing latency of 1.2ms met the ADAS system requirement of ≤5ms. Architecture was approved and entered series production.

**Key Lesson:** *Use CAN FD when large payloads (>8 bytes) are sent at high frequency, especially in ADAS where multiple sensors broadcast object lists simultaneously. CAN FD is also mandatory when E2E Profile 4 (CRC-32 in header) is required for ASIL-B/C signals, as it needs more header space than 8 bytes allows.*

---

### STAR Scenario 3 — Using CAN TP for UDS ECU Diagnostics

**Situation:**
You are a diagnostic test engineer performing end-of-line (EOL) validation at a manufacturing plant for a new Body Control Module (BCM). The EOL tester must: (1) read the ECU VIN (17 bytes), (2) read the ECU software fingerprint (40 bytes), (3) run a self-test routine that returns a 120-byte result, and (4) clear all DTCs. All communication is over the vehicle's 500 kbit/s CAN network using UDS (ISO 14229). The BCM responds on CAN ID 0x7CC (physical), functional address 0x7DF.

**Task:**
Design the complete diagnostic communication strategy using the correct protocol layers. Explain why raw CAN or CAN FD alone cannot fulfil these requirements, and implement a working tester flow using CAN TP (ISO 15765-2).

**Action:**
1. Identified why raw CAN alone fails:
   - VIN = 17 bytes → exceeds 8-byte classical CAN limit. Cannot fit in single frame.
   - Software fingerprint = 40 bytes → requires 5+ classical CAN frames with no protocol to sequence them.
   - Self-test result = 120 bytes → 15 classical CAN frames with no flow control = data loss risk.
   - Without transport protocol: no acknowledgement, no segmentation, no receiver buffer management.

2. Confirmed CAN TP (ISO 15765-2) is mandatory:
   - UDS (ISO 14229) **requires** ISO 15765-2 as the transport layer on CAN
   - CAN TP provides: SF/FF/CF/FC frame types, flow control, sequence numbers, timeout handling (N_As, N_Bs, N_Cs, N_Ar, N_Br, N_Cr timers)

3. Designed the EOL tester flow:

   **Step 1 — Enter Extended Diagnostic Session:**
   ```
   TX (0x744 → 0x7CC): SF [02 10 03] (UDS 0x10, subfunction 0x03 = extendedDiagnosticSession)
   RX (0x7CC → 0x74C): SF [02 50 03] (positive response)
   ```

   **Step 2 — Read VIN (0x22 F190):**
   ```
   TX: SF [03 22 F1 90]
   RX: FF [00 14 62 F1 90 56 49 4E]  ← len=20, response SID=0x62, DID=F190, first 5 VIN bytes
       TX: FC [30 00 00]              ← ContinueToSend, BlockSize=0, STmin=0
       CF [21 xx xx xx xx xx xx xx]  ← VIN bytes 6–12
       CF [22 xx xx xx xx xx]        ← VIN bytes 13–17 + padding
   ```

   **Step 3 — Read Software Fingerprint (0x22 F18B):**
   ```
   TX: SF [03 22 F1 8B]
   RX: FF [00 2B 62 F1 8B xx xx xx]  ← len=43 (3 header + 40 data)
       TX: FC [30 00 00]
       CF [21..] CF [22..] CF [23..] CF [24..] CF [25..]  ← 5 consecutive frames
   ```

   **Step 4 — Execute Self-Test Routine (0x31 0101 + read result 0x31 0301):**
   ```
   TX: SF [04 31 01 01 01]           ← Start Routine 0x0101
   RX: SF [04 71 01 01 01]           ← Positive response
   (wait 500ms)
   TX: SF [04 31 03 01 01]           ← Request routine results
   RX: FF [00 7B 71 03 01 01 xx xx]  ← len=123, multi-frame response
       TX: FC [30 00 00]
       CF [21..] through CF [2F..]   ← 15 consecutive frames for 120-byte result
   ```

   **Step 5 — Clear DTCs (0x14 FF FF FF):**
   ```
   TX: SF [04 14 FF FF FF]           ← ClearDiagnosticInformation, all DTCs
   RX: SF [01 54]                    ← Positive response
   ```

4. Implemented in Python using `python-can` with manual ISO-TP:
   ```python
   def send_isotp_sf(bus, tx_id, data):
       """Send Single Frame UDS message via CAN TP"""
       pci = [len(data)]  # SF: N_PCI byte = length (0-7)
       frame = pci + list(data) + [0xCC] * (7 - len(data))  # pad to 8
       msg = can.Message(arbitration_id=tx_id, data=frame, is_extended_id=False)
       bus.send(msg)
   ```

5. Added N_Cr timeout (150ms) handling to abort and retry if consecutive frame is delayed.

**Result:**
All five EOL diagnostic steps completed reliably in under 3 seconds total. VIN readback matched the programmed value. Self-test result (120 bytes) was received correctly with zero frame drops across 500 test cycles. DTC clear confirmed at end of run. The CAN TP protocol provided the necessary segmentation and flow control that raw CAN could never provide, with zero modifications needed to the ECU — it already implemented ISO 15765-2 as part of its UDS stack.

**Key Lesson:** *CAN TP (ISO 15765-2) is not optional for UDS communication — it is the transport layer mandated by ISO 14229. Any diagnostic data larger than 7 bytes (classical CAN) or 62 bytes (CAN FD SF) automatically requires multi-frame CAN TP. Never attempt to bypass CAN TP for diagnostics — sequence numbers, flow control, and timeout handling are essential to reliable large-payload transfer.*

---

### STAR Scenario 4 — Choosing Between CAN FD and Classical CAN + CAN TP for OTA Flash

**Situation:**
You are a systems architect on a next-generation EV platform. The software team estimates the BMS ECU firmware is 512 KB and must be updatable Over-The-Air (OTA) without taking the vehicle to a dealer. The OTA manager ECU receives the firmware block from the telematics unit via internal Ethernet and must re-flash the BMS over CAN. The BMS ECU is connected on a dedicated battery CAN network. You must compare: (A) Classical CAN 500 kbit/s + CAN TP, vs (B) CAN FD 2 Mbit/s + CAN TP. Both use UDS flashing (0x34 RequestDownload, 0x36 TransferData, 0x37 RequestTransferExit).

**Task:**
Calculate the theoretical flash time for both options, identify the performance-limiting factors, and recommend the correct architecture with justification.

**Action:**
1. Calculated net data throughput for each option:

   **Option A — Classical CAN 500 kbit/s + CAN TP:**
   - TransferData (0x36) block: CAN TP max usable payload = 4095 bytes per ISO-TP PDU
   - Each classical CAN frame carries 7 bytes (1 byte PCI overhead): net 7 B/frame
   - Frame duration at 500 kbit/s: ~130 bits ≈ 0.26ms → 3846 frames/second
   - Net throughput: 7 × 3846 = **26.9 KB/s**
   - 512 KB ÷ 26.9 KB/s = **~19 seconds** (ideal, no STmin, BS=0)
   - With STmin=1ms (typical ECU requirement): 3846 → 1000 frames/s → 7 KB/s → **73 seconds**

   **Option B — CAN FD 2 Mbit/s data phase + CAN TP:**
   - TransferData: CAN FD TP (ISO 15765-2, extended addressing) max SF = 62 bytes
   - Each CAN FD CF carries 63 bytes (1 byte PCI): net 63 B/frame
   - Frame duration (64-byte CAN FD at 2 Mbit/s data, 500 kbit nominal): ~380 bits total ≈ **0.52ms** at nominal + ~0.25ms data phase → ~0.35ms per frame
   - At STmin=1ms: 1000 frames/s × 63 bytes = **63 KB/s**
   - 512 KB ÷ 63 KB/s = **~8.1 seconds**
   - 9× faster than classical CAN with same STmin

2. Identified limiting factors:
   - **ECU flash write speed**: BMS internal NVM typically 50–100 KB/s → real bottleneck
   - **STmin**: Set by BMS ECU to give time for flash write per block. CAN FD helps here because more bytes arrive per frame.
   - **P2 server timeout (UDS)**: Max response time for 0x36. Longer if ECU is erasing/writing.

3. Recommended **Option B (CAN FD + CAN TP)**:
   - Even if ECU NVM limits to 50 KB/s, CAN FD removes the *network* as the bottleneck
   - Fewer frames → less interrupt overhead on BMS microcontroller → faster write
   - Larger blocks (up to 4095 bytes per ISO-TP PDU, fitting in ~65 CAN FD frames) reduce protocol overhead
   - Future sensor data requirements (cell voltage every 10ms × 96 cells = 192 bytes) will need CAN FD anyway

4. Validated architecture in CAPL HIL simulation: CAN FD OTA flashed a 512 KB binary in **11.3 seconds** actual (vs 68 seconds on classical CAN in the same simulation), with flash NVM being the real bottleneck at ~45 KB/s.

**Result:**
The CAN FD OTA architecture was selected for the BMS network. Production flash time of 11–15 seconds enabled OTA to complete within the 30-second regulatory window for safety firmware updates (UNECE WP.29 regulation). The classical CAN option was rejected as it could not guarantee completion within the window under worst-case STmin and NVM conditions.

**Key Lesson:** *CAN TP is required for any firmware flash operation — no alternative. The choice between Classical CAN and CAN FD affects the speed and reliability of that flashing. For large payloads (>10 KB) or time-constrained OTA scenarios, CAN FD + CAN TP is architecturally superior. Classical CAN + CAN TP is sufficient for small ECUs with infrequent updates.*

---

### STAR Scenario 5 — Wrong Protocol Choice and Root Cause Analysis

**Situation:**
During system integration testing for a cluster ECU project, the test team reports that the instrument cluster intermittently misses speed updates, causing the speedometer to freeze for 200–500ms. The CAN network is 500 kbit/s Classical CAN. A previous engineer had implemented vehicle speed as part of a UDS-style multi-frame message (CAN TP) to bundle speed, RPM, fuel, and temperature together (total 32 bytes). The logic was "32 bytes doesn't fit in one frame, so let's use CAN TP."

**Task:**
Diagnose why this approach is technically incorrect, explain the root cause of the freezing, and redesign the interface using the appropriate protocol strategy.

**Action:**
1. Retrieved the CANalyzer trace and found:
   - Speed data was sent as CAN TP FF → CF sequence with STmin=5ms
   - Under normal conditions: FF + 4 CFs arrived fine → cluster updates
   - Under high bus load: FC (Flow Control) frame from cluster was delayed → sender waited up to N_Bs timeout (1000ms) before aborting → cluster received nothing for up to 1 second

2. Identified root cause: **CAN TP was used for real-time periodic data — a fundamental protocol misuse:**
   - CAN TP introduces flow control dependency (sender must wait for FC frame)
   - FC delays under bus load cause multi-second data gaps
   - Periodic real-time signals must never depend on request-response handshaking
   - FC timeout (N_Bs = 1000ms by default) caused 1-second blackouts of speed data

3. Redesigned the interface:
   - Split 32 bytes across **4 standard CAN frames** (8 bytes each), each broadcast independently:
     ```
     0x100: VehicleSpeed + EngineRPM (4 bytes)
     0x500: FuelLevel + CoolantTemp + GearPosition + OilPressure (5 bytes)
     0x505: WarningLamps + TPMS (2 bytes)
     0x507: EV_SOC + Brightness (2 bytes)
     ```
   - All frames broadcast at 10ms cycle, no flow control, no sequencing
   - Cluster receives each independently — partial loss of one frame doesn't block others

4. Retained CAN TP **only for UDS diagnostic communication** over separate IDs (0x744 / 0x74C).

**Result:**
The speedometer freeze was eliminated completely. Post-fix testing over 72 hours of continuous HIL simulation recorded zero occurrences of speed freeze events (vs 847 events in 72 hours pre-fix). Bus load actually decreased from 8.4% (CAN TP overhead) to 4.1% (4 direct frames) because CAN TP header bytes and FC frames were eliminated.

**Key Lesson:** *CAN TP is for diagnostic, configuration, and large one-shot transfers — NEVER for periodic real-time signals. If a real-time signal exceeds 8 bytes, the correct solution is to split it across multiple CAN frames (or upgrade to CAN FD), not to wrap it in CAN TP. Using CAN TP for real-time data creates latency, flow-control dependency, and system reliability risks.*

---

## 7. Quick Reference Summary

| Decision | Classical CAN | CAN FD | CAN TP |
|----------|--------------|--------|--------|
| Data size per message | ≤8 bytes | 9–64 bytes native | Any size (segmented) |
| Real-time periodic? | Yes | Yes | No — adds latency |
| Diagnostics (UDS)? | Only if payload ≤7 bytes | Only if payload ≤62 bytes | Yes — mandatory |
| ECU flashing (OTA)? | Only with CAN TP | Only with CAN TP | Required layer |
| Calibration (XCP)? | XCP over CAN (≤8B) | XCP over CAN FD (≤64B) | Not needed |
| Safety (E2E protection)? | Yes (E2E Profile 2) | Yes (E2E Profile 4) | Not applicable |
| Bit rate | Up to 1 Mbit/s | Up to 8 Mbit/s | Protocol layer |
| Legacy ECU compatibility | Universal | Requires FD-capable controller | Requires ISO-TP stack |
| Cost | Low | Medium (newer silicon) | Software only |

---

## 8. Common Mistakes to Avoid

| Mistake | Consequence | Correct Approach |
|---------|-------------|------------------|
| Using CAN TP for periodic speed/RPM signals | Flow control delays → data freeze | Use raw CAN frames at fixed cycle |
| Using Classical CAN for 50-byte ADAS object list | 6+ frame IDs, complex DBC, high bus load | Upgrade to CAN FD |
| Not implementing STmin correctly in CAN TP | ECU buffer overflow → data loss, frame drops | Always honour STmin from FC frame |
| Using CAN FD without E2E on ASIL-B signals | Safety violation — weaker protection than required | Add AUTOSAR E2E Profile 4 |
| Mixing CAN and CAN FD nodes without FD-tolerant transceivers | Bus errors — CAN FD frames corrupt classical CAN nodes | Use FD-passive transceivers or separate networks |
| Ignoring N_Cr timeout in CAN TP receiver | Silent failure if CF is lost mid-transmission | Implement N_Cr timer and abort/retry logic |

---

---

## 9. Error Handling — CAN / CAN FD / CAN TP

Error handling exists at two completely different layers depending on the protocol:
- **CAN / CAN FD**: Hardware-level errors detected at the physical and data-link layer (ISO 11898-1)
- **CAN TP**: Software-level errors — timeout, sequence, and flow-control failures at the transport layer (ISO 15765-2)

---

### 9.1 Classical CAN Error Types

Classical CAN defines **5 independent error detection mechanisms**. Each is detected by different nodes at different points in the frame.

```
 CAN 2.0 Standard Frame — Error Detection Points
 ─────────────────────────────────────────────────────────────────────────────

  ┌────┬────────────┬───┬───┬────┬──────┬──────────────────┬───────┬──┬───┬─────┐
  │SOF │  ID[10:0]  │RTR│IDE│ r0 │ DLC  │  DATA (0–8 B)    │ CRC15 │CD│ACK│ EOF │
  └────┴────────────┴───┴───┴────┴──────┴──────────────────┴───────┴──┴───┴─────┘
    │   │←── Arbitration ──→│         │←──── Stuffed ─────→│       │  │   │
    │   │                   │         │                     │       │  │   │
    ▼   ▼                   ▼         ▼                     ▼       ▼  ▼   ▼
  [A]  [B]                [B]        [C]                  [D]    [E] [E] [E]

  Error Types:
  [A] = BIT ERROR        — TX node: sent bit ≠ read-back bit (outside arbitration)
  [B] = BIT ERROR        — TX node: dominant sent but recessive read (corrupted)
  [C] = STUFF ERROR      — All nodes: 6+ consecutive same-polarity bits detected
  [D] = CRC ERROR        — Receiver: recalculated CRC ≠ CRC field in frame
  [E] = FORM ERROR       — All nodes: fixed field (CD/ACK_DEL/EOF) has wrong value
        ACK ERROR        — TX node only: ACK slot remained recessive (no receiver ACK'd)
```

#### Bit Error — Detection Logic

```
  Transmitting node monitors bus simultaneously while sending:

  ┌───────────────────────────────────────────────────────────┐
  │                  TX bit vs RX read-back                   │
  │                                                           │
  │  TX=0 (dominant), RX=0           → OK (expected)         │
  │  TX=1 (recessive), RX=1          → OK (expected)         │
  │                                                           │
  │  TX=1 (recessive), RX=0 (dominant)                       │
  │    ├─ During ID field?  → Arbitration LOST — stop, recv  │
  │    ├─ During ACK slot?  → OK (receiver is writing 0)     │
  │    └─ Anywhere else?    → BIT ERROR → Error Frame!       │
  │                                                           │
  │  TX=0 (dominant), RX=1 (recessive)                       │
  │    └─ Anywhere?        → BIT ERROR → Error Frame!        │
  └───────────────────────────────────────────────────────────┘

  On BIT ERROR detected:
  ──────────────────────
  Node immediately aborts frame
        ↓
  Transmits Active Error Flag (6× dominant bits)
        ↓
  TEC += 8
        ↓
  Retransmit after IFS
```

#### Stuff Error — Bit Stuffing Rule

```
  Transmitter inserts a complementary bit after 5 consecutive same-polarity bits:

  Original data:  1  1  1  1  1  │0│  0  0  0  0  0  │1│  1  0  1
                  ←─ 5 same ──→  ↑  ←──── 5 same ────→  ↑
                             stuff bit=0            stuff bit=1
                             (inserted)             (inserted)

  Receiver counts consecutive bits:
  After 5 same → expects OPPOSITE next bit (stuff bit) → discards it
  If bit 6 is SAME polarity:

  Expected:  1  1  1  1  1  [0]  ← stuff bit should be 0
  Received:  1  1  1  1  1   1   ← still 1 → STUFF ERROR!

  Stuff Error detected by: ALL nodes (both transmitter and receivers)
  TEC change:  Transmitter TEC += 8  |  Receiver REC += 1
```

#### Form Error — Fixed-Field Violations

```
  Fields that MUST have fixed values (no bit stuffing, exact polarity):

  Field              Required    If violated
  ─────────────────────────────────────────────────────
  CRC Delimiter      1 (recess)  Form Error — all nodes
  ACK Delimiter      1 (recess)  Form Error — all nodes
  EOF bit 1–7        1 (recess)  Form Error — all nodes
  Intermission 1–3   1 (recess)  Form Error / misinterpret

  Example: EOF violation

  ┌───────────────────────────────────────────────┐
  │  ...CRC│CD=1│ACK=0│ACK_DEL=1│ E O F         │
  │        │    │     │          │ 1 1 1 1 1 1 1 │ ← all must be recessive
  │                              │ 1 1 0 ← noise │ ← dominant in EOF!
  │                                  ↑            │
  │                             FORM ERROR here   │
  └───────────────────────────────────────────────┘
```

#### ACK Error — Acknowledgement Mechanism

```
  Transmitter sends ACK slot as recessive (1) — "leaving it blank for receivers"

  Transmitter:  ...CRC│CRC_DEL=1│ ACK=1 │ACK_DEL=1│EOF...
  Receiver(s):              writes:│ ACK=0 │  ← dominant = "I received it OK"
  Bus result:                      │ ACK=0 │  ← dominant wins

  Transmitter reads bus:
    Sent 1, read 0 in ACK slot → OK (this is expected receiver write)
    Sent 1, read 1 in ACK slot → ACK ERROR (nobody confirmed!)

  Common Causes:
  ┌──────────────────────────────────────────────────────┐
  │  • Only one node on bus (bench/development setup)    │
  │  • All receivers entered Bus Off state               │
  │  • Wrong baud rate — receivers cannot decode frame   │
  │  • CAN_H or CAN_L open circuit — receivers don't     │
  │    see the frame at all                              │
  │  • Receiver's CRC mismatch → it won't ACK            │
  └──────────────────────────────────────────────────────┘

  TEC change: Transmitter TEC += 8
```

#### CRC Error — Frame Integrity Check

```
  CAN CRC-15 Polynomial: x¹⁵+x¹⁴+x¹⁰+x⁸+x⁷+x⁴+x³+1
  Covers: SOF + Arbitration + Control + Data fields

  Transmitter:  CRC = f(SOF, ID, DLC, DATA)
  Receiver:     CRC' = f(received bits)

  If CRC ≠ CRC':
    → CRC ERROR detected by receiver
    → Receiver also suppresses ACK (won't write dominant to ACK slot)
    → Transmitter sees no ACK → ACK ERROR too
    → Both errors raised simultaneously by different nodes

  Example:
  Frame sent:     DATA=[0x2F 0x00] → CRC=0x4A12 (example)
  Frame received: DATA=[0x2F 0x08] ← bit 3 flipped by noise
                                   → CRC'=0x7C31 ≠ 0x4A12 → CRC ERROR

  REC change: Receiver REC += 1
```

#### Error Frame Structure

```
  Active Error Frame (TEC/REC < 128):

  ┌──────────────────────┬────────────────────────────────────────┐
  │  Active Error Flag   │         Error Delimiter                │
  │  6× DOMINANT bits    │         8× RECESSIVE bits              │
  │  0  0  0  0  0  0   │         1  1  1  1  1  1  1  1         │
  └──────────────────────┴────────────────────────────────────────┘

  Passive Error Frame (TEC ≥ 128 or REC ≥ 128):

  ┌──────────────────────┬────────────────────────────────────────┐
  │  Passive Error Flag  │         Error Delimiter                │
  │  6× RECESSIVE bits   │         8× RECESSIVE bits              │
  │  1  1  1  1  1  1   │         1  1  1  1  1  1  1  1         │
  └──────────────────────┴────────────────────────────────────────┘
  Note: Passive Error Flag is invisible on bus (recessive = released)
        Error Passive nodes cannot force other nodes to detect the error

  Error Echo Mechanism (Active Error Frame propagation):

  Node A detects error mid-frame
       ↓ sends 6 dominant bits (Active Error Flag)
       ↓
  Bus shows 6 consecutive dominant bits
       ↓
  All other nodes were receiving a frame
  → 6 consecutive dominant violates bit stuffing rule
  → All other nodes also raise Active Error Flag
       ↓
  Bus: up to 12 dominant bits (6+6 echo) + 8 recessive delimiter
       ↓
  All nodes discard the in-progress frame
  Transmitter will retry after IFS
```

---

### 9.2 CAN FD Error Differences

CAN FD inherits the same 5 error types as Classical CAN but adds important differences:

```
 CAN FD Frame — Error Detection Points
 ─────────────────────────────────────────────────────────────────────────────────

              │←── Nominal bit rate ───→│←── Data bit rate (if BRS=1) ──────────→│
              │                         │                                         │
  ┌────┬──────┬─────┬──────┬─────┬─────┬──────────────────────┬──────────┬──┬───┐
  │SOF │ ID   │ FDF │ RES  │ BRS │ ESI │  Data (up to 64 B)   │ CRC17/21 │CD│ACK│
  └────┴──────┴─────┴──────┴─────┴─────┴──────────────────────┴──────────┴──┴───┘
    │    │                   │     │              │                  │
    ▼    ▼                   ▼     ▼              ▼                  ▼
  [Bit] [Arb               [Bit] [Flag:       [Stuff+            [CRC-17 or
  error] loss]             error] Error       Bit errors]         CRC-21]
                                  State

  Key differences vs Classical CAN:
  ┌─────────────────────────────────────────────────────────────────┐
  │                                                                 │
  │  1. ESI bit (Error State Indicator)                            │
  │     ESI=0 → transmitting node is Error Active                  │
  │     ESI=1 → transmitting node is Error Passive                 │
  │     Receivers can see the sender's error state in every frame  │
  │                                                                 │
  │  2. Stronger CRC                                               │
  │     CAN FD ≤16 bytes → CRC-17 (131071 polynomial)             │
  │     CAN FD >16 bytes → CRC-21 (2097151 polynomial)            │
  │     Classical CAN    → CRC-15  (32767 polynomial)             │
  │     CRC-21 detects all errors up to 5 bits in 4096-bit frame  │
  │                                                                 │
  │  3. Stuff Bit Counter (fixed-position stuff bits)              │
  │     CAN FD adds a modulo-8 counter embedded in the CRC field   │
  │     CRC field itself contains fixed-position stuff bits at     │
  │     every 5th position (not data-dependent)                    │
  │     Counter mismatch → Stuff Count Error (new in CAN FD)      │
  │                                                                 │
  │  4. No Remote Frames                                           │
  │     CAN FD removed RTR — RTR bit error type does not apply     │
  │                                                                 │
  │  5. Bit rate switch error                                      │
  │     If a CAN FD transmitter switches to data phase (BRS=1)     │
  │     but a Classical CAN node is on the same bus:               │
  │     The classical node cannot decode the faster data phase     │
  │     → Sees form/stuff errors → raises error frames             │
  │     → Disrupts the entire bus                                  │
  │     Solution: Separate CAN FD nodes from Classical CAN nodes,  │
  │     or use FD-tolerant (FD-passive) classical transceivers     │
  │                                                                 │
  └─────────────────────────────────────────────────────────────────┘
```

#### CAN vs CAN FD CRC Polynomial Comparison

```
  ┌────────────────┬─────────────────────────┬──────────────────────────────┐
  │ Protocol       │ CRC Polynomial          │ Hamming Distance / Coverage  │
  ├────────────────┼─────────────────────────┼──────────────────────────────┤
  │ Classical CAN  │ CRC-15 (x¹⁵+x¹⁴+...)   │ HD=6 up to 114 data bits     │
  │ CAN FD ≤16 B   │ CRC-17 (x¹⁷+x¹⁶+...)   │ HD=6 up to 4096 data bits    │
  │ CAN FD >16 B   │ CRC-21 (x²¹+x²⁰+...)   │ HD=6 up to 4096 data bits    │
  └────────────────┴─────────────────────────┴──────────────────────────────┘
  HD=6 means: detects ALL combinations of up to 5 bit errors in the frame
```

---

### 9.3 Error Confinement — TEC / REC State Machine

Every CAN node (Classical or FD) maintains two hardware counters that track its error history:

```
  TEC = Transmit Error Counter   (incremented on transmit errors)
  REC = Receive Error Counter    (incremented on receive errors)

  Counter change rules:
  ─────────────────────────────────────────────────
  Event                          TEC change  REC change
  ─────────────────────────────────────────────────
  Transmitter detects error         +8          —
  Receiver detects error             —          +1
  Successful frame transmitted      -1          —
  Successful frame received          —          -1 (min 0)
  Bus Off recovery attempt           —          —  (internal reset)


  Node State Machine:

       Power On
          │
          ▼
  ┌───────────────┐
  │  ERROR ACTIVE │  TEC < 128 AND REC < 128
  │               │  • Sends ACTIVE Error Flag (6 dominant)
  │               │  • Fully participates in bus
  └───────┬───────┘
          │
          │  TEC ≥ 128 OR REC ≥ 128
          ▼
  ┌───────────────┐
  │ ERROR PASSIVE │  128 ≤ TEC ≤ 255  or  128 ≤ REC ≤ 255
  │               │  • Sends PASSIVE Error Flag (6 recessive)
  │               │    → invisible on bus, cannot destroy frames
  │               │  • Still receives frames
  │               │  • Must wait extra (Suspend Transmission = 8 bits)
  │               │    before retransmitting after error
  │               │  • ESI=1 in transmitted CAN FD frames
  └───────┬───────┘
          │
          │  TEC > 255
          ▼
  ┌───────────────┐
  │   BUS OFF     │  TEC > 255
  │               │  • Node disconnects from bus COMPLETELY
  │               │  • Does NOT transmit or receive anything
  │               │  • Does NOT send error frames
  │               │  • Cannot self-recover automatically
  │               │  • Recovery: 128 × 11 recessive bits observed
  │               │    (128 consecutive idle sequences)
  └───────┬───────┘
          │
          │  After 128 × 11 recessive bits (hardware)
          │  OR MCU reset / power cycle
          ▼
  ┌───────────────┐
  │  ERROR ACTIVE │  ← Returns to active state, TEC/REC reset to 0
  └───────────────┘


  TEC escalation example — babbling idiot scenario:
  ──────────────────────────────────────────────────
  Frame 1 fails:  TEC = 0 + 8 = 8    → still Error Active
  Frame 2 fails:  TEC = 8 + 8 = 16   → still Error Active
  ...
  Frame 16 fails: TEC = 128          → transitions to Error Passive
  ...
  Frame 32 fails: TEC = 256          → BUS OFF

  At 500 kbit/s with 1ms cycle frame,
  a node reaches BUS OFF in approximately 32ms of continuous errors.
```

---

### 9.4 CAN TP Transport-Layer Errors

CAN TP (ISO 15765-2) does not use hardware error counters. Instead it defines **timeout timers** (N_* timers). When a timer expires, the transmission is aborted and must be restarted from the beginning.

```
  CAN TP Timer Definitions (ISO 15765-2 Table 1):

  Timer   Direction        Event that STARTS timer    Event that STOPS timer     Default max
  ──────────────────────────────────────────────────────────────────────────────────────────
  N_As    Sender → Recvr   Start of SF or FF TX       Confirmation of TX         25 ms
  N_Bs    Sender waits     After FF sent              Receipt of FC frame        ≥1000 ms
  N_Cs    Sender → Recvr   After FC received          Start of CF TX             ≤25 ms
  N_Ar    Recvr → Sender   Start of FC TX             Confirmation of FC TX     25 ms
  N_Br    Recvr waits      After FF received          Start of FC TX            ≥25 ms (impl)
  N_Cr    Recvr waits      After FC sent (or prev CF) Receipt of next CF        150 ms
```

#### CAN TP Multi-Frame Message Flow with Error Points

```
  SENDER (Tester / ECU A)              RECEIVER (ECU B)
  ─────────────────────────────────────────────────────────────────────

  [1] Sends FIRST FRAME (FF)
      FF [10 xx SID DID ...]  ──────────────────────►
                                                       ↓ N_Br timer starts
                                                         (time to prepare FC)
      ◄── N_Bs timer starts ──
      (waiting for FC)

  [2] Receiver sends FLOW CONTROL (FC)
                              ◄──────────────────────  FC [30 BS STmin]
      N_Bs timer STOPS ───────┘                        N_Br timer STOPS
      N_Cs timer starts
      (time between FC and CF1)

  [3] Sender sends CONSECUTIVE FRAMES (CF)
      CF1 [21 ...] ─────────────────────────────────►
      N_Cs timer restarts                              N_Cr timer starts
                                                         (waiting for CF2)
      CF2 [22 ...] ─────────────────────────────────►
      N_Cs timer restarts                              N_Cr timer restarts

      CF3 [23 ...] ─────────────────────────────────►
                                                       N_Cr timer STOPS
                                                       Message complete ✓


  ERROR SCENARIO A — N_Bs timeout (FC never arrives):
  ─────────────────────────────────────────────────────
  Sender:  FF sent
           N_Bs timer starts (1000 ms)
           ....1000 ms passes....
           N_Bs EXPIRES — FC never received

           ACTION: Abort transmission, report N_TIMEOUT_Bs to upper layer
           STATUS: ISO-TP session fails, UDS layer raises NRC 0x25 (ResponsePending)
                   or 0x78 timeout

  ERROR SCENARIO B — N_Cr timeout (CF not received in time):
  ───────────────────────────────────────────────────────────
  Receiver: FF received, FC sent
            CF1 received OK
            N_Cr timer starts (150 ms)
            ....CF2 delayed or lost on bus....
            N_Cr EXPIRES after 150 ms

            ACTION: Abort reception, discard reassembly buffer
            STATUS: ISO-TP session fails at receiver
                    Sender may be still sending (doesn't know yet)
                    Receiver must send new FC with FS=2 (Overflow) or just discard

  ERROR SCENARIO C — FC with FS=2 Overflow:
  ──────────────────────────────────────────
  Receiver: FF received but buffer already full
            Sends FC [32 00 00]  ← FS=2 = Overflow!

  Sender:   Receives FC with FS=2
            → Immediately aborts transmission
            → Reports buffer overflow to upper layer
            → No retransmit until new request

  ERROR SCENARIO D — FC with FS=1 Wait (WAIT state):
  ─────────────────────────────────────────────────────
  Receiver: FF received, not yet ready (busy)
            Sends FC [31 00 00]  ← FS=1 = Wait

  Sender:   Receives FC with FS=1 (Wait)
            → Resets N_Bs timer, keeps waiting
            → If WAIT count exceeds limit → abort (implementation defined)
            → When ready, receiver sends FC [30 BS STmin] → transmission continues

  ERROR SCENARIO E — Wrong Sequence Number (SN mismatch):
  ─────────────────────────────────────────────────────────
  Expected sequence:  CF1=[21] CF2=[22] CF3=[23]
  Received:           CF1=[21] CF2=[23] ← SN jumped from 1 to 3!

  Receiver: Detects SN out-of-sequence
            → Aborts reassembly
            → Does NOT send error frame to sender (ISO 15765-2 is not bidirectional)
            → Upper layer diagnosis required

  Common cause: dropped CF2 on bus due to high bus load or bit error + no retransmit
                by the underlying CAN layer (the CAN frame itself was corrected
                by CAN error handling and retransmitted, but ISO-TP timer expired)
```

#### STmin — Separation Time Between Consecutive Frames

```
  STmin byte (3rd byte of FC frame):

  Value range     Meaning
  ──────────────────────────────────────────────────
  0x00            No minimum separation required (send as fast as possible)
  0x01–0x7F       1 ms to 127 ms (1 ms resolution)
  0x80–0xF0       Reserved (do not use)
  0xF1–0xF9       100 µs to 900 µs (100 µs resolution)
  0xFA–0xFF       Reserved (do not use)

  Example FC: [30  03  0A]
               │   │   └── STmin = 0x0A = 10 ms between each CF
               │   └────── BlockSize = 3 (send 3 CFs before next FC)
               └────────── FS = 0x0 = ContinueToSend

  Impact of STmin on throughput:
  ──────────────────────────────
  Payload: 100 bytes, Classical CAN (7 bytes/CF net)
  Required CFs: ⌈(100-6)/7⌉ = 14 CFs

  STmin = 0ms:  14 × 0.26ms ≈  3.6ms total transfer time
  STmin = 1ms:  14 × 1.00ms ≈ 14.0ms total transfer time
  STmin = 10ms: 14 × 10.0ms ≈ 140ms total transfer time

  ← STmin is set by the RECEIVER to protect its internal buffer.
     Always honour STmin. Sending faster than STmin causes buffer overflow
     (receiver sends FC FS=2 Overflow).
```

---

### 9.5 Error Comparison Table

| Error Type | Protocol | Detected By | Counter Impact | Recovery |
|-----------|---------|------------|---------------|----------|
| Bit Error | CAN / CAN FD | Transmitter | TEC +8 | Auto-retransmit |
| Stuff Error | CAN / CAN FD | All nodes | TX: TEC+8 / RX: REC+1 | Auto-retransmit |
| Form Error | CAN / CAN FD | All nodes | TX: TEC+8 / RX: REC+1 | Auto-retransmit |
| ACK Error | CAN / CAN FD | Transmitter | TEC +8 | Auto-retransmit |
| CRC Error | CAN / CAN FD | Receiver | REC +1 | Transmitter retransmits after no-ACK |
| Stuff Count Error | CAN FD only | Receiver | REC +1 | Transmitter retransmits |
| N_Bs Timeout | CAN TP | Sender | Software abort | Application must retry |
| N_Cr Timeout | CAN TP | Receiver | Software abort | Application must restart |
| FC Overflow (FS=2) | CAN TP | Sender (on FC) | Software abort | Wait, retry later |
| SN Mismatch | CAN TP | Receiver | Software abort | Application must restart |
| N_As / N_Ar Timeout | CAN TP | Sender/Recv | Software abort | Application must retry |

---

### 9.6 Error Propagation Diagram

This diagram shows how a single bit error on the bus cascades through all three protocol layers:

```
                        PHYSICAL LAYER
  ┌─────────────────────────────────────────────────────────────────┐
  │  CAN_H ─────────────────── noise spike ──────────────────────  │
  │  CAN_L ─────────────────────────────────────────────────────── │
  │                                 ↑                               │
  │                         Bit flipped (0→1)                      │
  └─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        DATA LINK LAYER (CAN)
  ┌─────────────────────────────────────────────────────────────────┐
  │  Receiver detects CRC mismatch → REC += 1                       │
  │  Receiver withholds ACK                                         │
  │  Transmitter sees no ACK → TEC += 8                             │
  │  Transmitter sends Active Error Flag (6 dominant bits)          │
  │  All nodes echo error flag → frame destroyed                    │
  │  CAN hardware retransmits frame automatically                   │
  │  If retransmit succeeds → TEC -= 1, REC stays                  │
  │  If errors persist → TEC climbs toward 128 (Error Passive)      │
  │                    → TEC climbs toward 255 (Bus Off)            │
  └─────────────────────────────────────────────────────────────────┘
                                    │
                        (if using CAN TP)
                                    ▼
                        TRANSPORT LAYER (CAN TP)
  ┌─────────────────────────────────────────────────────────────────┐
  │  CAN hardware retransmits the corrupted CAN frame               │
  │  Retransmit takes time → N_Cr or N_Bs timer may expire          │
  │  If timer expires:                                              │
  │    → CAN TP session aborted                                     │
  │    → Reassembly buffer discarded at receiver                    │
  │    → Upper layer (UDS) gets timeout indication                  │
  └─────────────────────────────────────────────────────────────────┘
                                    │
                        (if using UDS over CAN TP)
                                    ▼
                        APPLICATION LAYER (UDS)
  ┌─────────────────────────────────────────────────────────────────┐
  │  UDS service (e.g., 0x22 ReadDataByIdentifier) receives         │
  │  timeout indication                                             │
  │  Tester tool sees: NRC 0x25 (ResponsePending) or timeout        │
  │  Tester must re-send the UDS request from the beginning         │
  └─────────────────────────────────────────────────────────────────┘

  Key insight: CAN hardware error recovery (retransmit) is automatic.
  CAN TP or UDS layer failures require the APPLICATION to retry.
  The two error recovery mechanisms are completely independent.
```

#### Protocol Stack — Which Layer Handles What

```
  ┌──────────────────────────────────────────────────────────────────┐
  │  APPLICATION (UDS ISO 14229)                                     │
  │  • Negative Response Codes (NRC): 0x10–0x7F                     │
  │  • P2 / P2* server response timing                              │
  │  • Session management (default / extended / programming)        │
  ├──────────────────────────────────────────────────────────────────┤
  │  TRANSPORT (CAN TP ISO 15765-2)                                  │
  │  • Segmentation / reassembly (SF, FF, CF, FC)                   │
  │  • Flow control (BlockSize, STmin)                              │
  │  • Timeout monitoring (N_As, N_Bs, N_Cs, N_Ar, N_Br, N_Cr)     │
  │  • Sequence number checking                                     │
  ├──────────────────────────────────────────────────────────────────┤
  │  DATA LINK (CAN / CAN FD ISO 11898-1)                           │
  │  • Bit Error, Stuff Error, Form Error, ACK Error, CRC Error     │
  │  • Active / Passive Error Flag transmission                     │
  │  • TEC / REC counters                                           │
  │  • Error Active / Error Passive / Bus Off state machine         │
  │  • Automatic frame retransmission (hardware)                    │
  ├──────────────────────────────────────────────────────────────────┤
  │  PHYSICAL (ISO 11898-2 / -5)                                    │
  │  • CAN_H / CAN_L differential signalling                        │
  │  • Dominant / Recessive voltage levels                          │
  │  • Termination (120Ω × 2)                                       │
  │  • Transceiver TX/RX                                            │
  └──────────────────────────────────────────────────────────────────┘
```

---

### 9.7 CAPL Error Detection Snippets

#### Detect CAN Bus Errors in CANalyzer / CANoe

```capl
// ─────────────────────────────────────────────────────────────────
// CAPL: Detect and log any CAN error frame on the bus
// ─────────────────────────────────────────────────────────────────
variables {
  int    g_bitErrors    = 0;
  int    g_stuffErrors  = 0;
  int    g_formErrors   = 0;
  int    g_ackErrors    = 0;
  int    g_crcErrors    = 0;
  int    g_totalErrors  = 0;
}

on errorFrame {
  g_totalErrors++;

  if (this.errorType == 1) {
    g_bitErrors++;
    write("[ERROR] BIT ERROR  at t=%.3f ms | Frame ID: 0x%X | TEC: %d",
          timeNow() / 100000.0, this.id, this.errorTec);

  } else if (this.errorType == 2) {
    g_stuffErrors++;
    write("[ERROR] STUFF ERROR at t=%.3f ms | Frame ID: 0x%X",
          timeNow() / 100000.0, this.id);

  } else if (this.errorType == 3) {
    g_formErrors++;
    write("[ERROR] FORM ERROR at t=%.3f ms | Frame ID: 0x%X",
          timeNow() / 100000.0, this.id);

  } else if (this.errorType == 4) {
    g_ackErrors++;
    write("[ERROR] ACK ERROR at t=%.3f ms | Frame ID: 0x%X (no receiver?)",
          timeNow() / 100000.0, this.id);

  } else if (this.errorType == 5) {
    g_crcErrors++;
    write("[ERROR] CRC ERROR at t=%.3f ms | Frame ID: 0x%X",
          timeNow() / 100000.0, this.id);
  }
}

// ─────────────────────────────────────────────────────────────────
// CAPL: Detect CAN TP N_Cr timeout — monitor for missing CF frames
// ─────────────────────────────────────────────────────────────────
variables {
  msTimer g_nCrTimer;
  int     g_expectingSN       = 0;   // next expected sequence number
  int     g_isotpActive       = 0;   // 1 = multi-frame session in progress
  int     N_CR_TIMEOUT_MS     = 150; // ISO 15765-2 default
}

// Called when FF is received — start tracking CF sequence
on message 0x7EC {                  // ECU response CAN ID
  byte pci = this.byte(0) & 0xF0;

  if (pci == 0x10) {               // First Frame
    g_isotpActive  = 1;
    g_expectingSN  = 1;
    setTimer(g_nCrTimer, N_CR_TIMEOUT_MS);
    write("[CANTP] FF received — starting N_Cr timer (%d ms)", N_CR_TIMEOUT_MS);

  } else if (pci == 0x20) {        // Consecutive Frame
    byte sn = this.byte(0) & 0x0F;
    cancelTimer(g_nCrTimer);

    if (sn != g_expectingSN) {
      write("[CANTP ERROR] SN MISMATCH — expected %d, got %d — session aborted!",
            g_expectingSN, sn);
      g_isotpActive = 0;
    } else {
      g_expectingSN = (g_expectingSN + 1) % 16;
      if (g_isotpActive)
        setTimer(g_nCrTimer, N_CR_TIMEOUT_MS); // restart for next CF
    }
  }
}

on timer g_nCrTimer {
  write("[CANTP ERROR] N_Cr TIMEOUT — CF not received in %d ms — session aborted!",
        N_CR_TIMEOUT_MS);
  g_isotpActive = 0;
  g_expectingSN = 0;
}

// ─────────────────────────────────────────────────────────────────
// CAPL: Monitor TEC / REC via UDS ReadDataByIdentifier (0x22)
// Read ECU internal error counters at test start and end
// ─────────────────────────────────────────────────────────────────
variables {
  byte g_udsTecReq[4] = {0x03, 0x22, 0xF1, 0xA0}; // DID 0xF1A0 = TEC (example)
  byte g_udsRecReq[4] = {0x03, 0x22, 0xF1, 0xA1}; // DID 0xF1A1 = REC (example)
}

void readErrorCounters() {
  message 0x744 testerReq;
  testerReq.dlc  = 8;
  testerReq.byte(0) = g_udsTecReq[0];  // length
  testerReq.byte(1) = g_udsTecReq[1];  // SID
  testerReq.byte(2) = g_udsTecReq[2];  // DID MSB
  testerReq.byte(3) = g_udsTecReq[3];  // DID LSB
  testerReq.byte(4) = 0xCC;
  testerReq.byte(5) = 0xCC;
  testerReq.byte(6) = 0xCC;
  testerReq.byte(7) = 0xCC;
  output(testerReq);
  write("[UDS] Requesting TEC/REC counters from ECU...");
}

on start { readErrorCounters(); }
on stopMeasurement {
  write("=== Error Summary ===");
  write("  Bit Errors:   %d", g_bitErrors);
  write("  Stuff Errors: %d", g_stuffErrors);
  write("  Form Errors:  %d", g_formErrors);
  write("  ACK Errors:   %d", g_ackErrors);
  write("  CRC Errors:   %d", g_crcErrors);
  write("  Total:        %d", g_totalErrors);
}
```

---

*Document: CAN_CANFD_CANTP_When_To_Use_STAR.md*
*Location: protocol_study_material/*
*Standards: ISO 11898-1, ISO 15765-2, ISO 14229, AUTOSAR E2E Library*
