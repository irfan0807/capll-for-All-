# Advanced Debugging and Root Cause Analysis in Automotive ECU Testing

**Document Classification:** Technical Reference — Validation Engineering  
**Audience:** Automotive Validation Engineers, ADAS Test Engineers, HIL Engineers, Cybersecurity Validation  
**Applicable Standards:** ISO 26262, ISO 14229, ISO 21434, AUTOSAR Classic 4.x, SOME/IP TR_SOMEIP  
**Applicable Platforms:** Bosch, Continental, Aptiv, Magna Tier-1 ECU Development

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [End-to-End Debugging Methodology](#2-end-to-end-debugging-methodology)
3. [Protocol-Level Debugging](#3-protocol-level-debugging)
4. [AUTOSAR Debugging](#4-autosar-debugging)
5. [ADAS Debugging](#5-adas-debugging)
6. [Automotive Cybersecurity Debugging](#6-automotive-cybersecurity-debugging)
7. [HIL Debugging](#7-hil-debugging)
8. [STAR Format Scenarios](#8-star-format-scenarios)
9. [CAPL Scripts for Debugging](#9-capl-scripts-for-debugging)
10. [Python Scripts for Debugging](#10-python-scripts-for-debugging)
11. [Best Practices and Checklist](#11-best-practices-and-checklist)

---

## 1. Introduction

### 1.1 Importance of Debugging in Safety-Critical Automotive Systems

Modern vehicles contain between 70 and 100+ Electronic Control Units (ECUs), communicating over multi-protocol networks including CAN, CAN FD, LIN, FlexRay, and Automotive Ethernet. A single undetected defect in an ADAS system — a brake controller that does not respond, a lane-keep torque that saturates, or an authentication failure that blocks a diagnostic session — can escalate from a software anomaly to a field recall, a product liability claim, or a safety incident classified under ISO 26262 ASIL-D.

Debugging in a Tier-1 automotive context is therefore not a reactive fire-fighting exercise. It is a **structured, evidence-based process** governed by the same engineering rigour that defines the design phase. Key pressure points driving the need for expert debugging include:

- **Functional Safety (ISO 26262):** Any confirmed failure tied to a safety goal must trace to a FMEA line and an approved RCA report before software can be re-released.
- **Homologation deadlines:** OEM program gates do not move. A defect found in System Integration Testing (SIT) that surfaces in a gate review typically means the team has 48–72 hours to characterise and classify, not weeks.
- **Multi-ECU interaction:** ADAS features such as Automatic Emergency Braking (AEB) and Highway Pilot span radar ECU, camera ECU, fusion ECU, brake controller, and gateway simultaneously. The failure mode in one ECU is often a symptom of a defect in an upstream node.
- **Regression risk:** An uncontrolled fix — patching a CAN message timing without re-running the full regression suite — creates a second defect invisible in deterministic tests.

### 1.2 Role of RCA in the ECU Validation Lifecycle

Root Cause Analysis (RCA) is the formal process of identifying the **fundamental cause** of an anomaly, not merely its observable symptom. In the ECU validation lifecycle, RCA is triggered:

| Trigger | RCA Scope |
|---|---|
| Test case FAIL | Single-ECU function |
| Integration test FAIL | Multi-ECU interaction |
| Field incident | Full system, potentially hardware + software |
| Audit finding | Process gap |

**The 5-Why method** is the minimum baseline. For safety-critical failures, a structured Ishikawa (fishbone) diagram combined with a Fault Tree Analysis (FTA) extract is expected in the RCA closure report.

RCA deliverables in a Tier-1 project typically include:

1. Failure description with reproducibility evidence (log file, snapshot)
2. Timeline of failure observation
3. Isolation of the root cause to a specific software module, configuration value, or interface contract violation
4. Corrective action with change reference (JIRA ID, door ID)
5. Verification evidence (re-test result, regression evidence)
6. Lesson learned registered in the project knowledge base

---

## 2. End-to-End Debugging Methodology

### 2.1 The Debugging Funnel

Automotive ECU debugging follows a **top-down funnel model** — start at the observable symptom and progressively narrow the scope until the defect is isolated to the smallest possible change unit.

```
OBSERVABLE SYMPTOM
        │
        ▼
  ┌─────────────┐
  │  Network    │  ← CAN/ETH traffic: signal missing? wrong value? timing?
  │  Layer      │
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │   ECU I/O   │  ← ECU inputs correct? Outputs match spec?
  │   Layer     │
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  SW Layer   │  ← AUTOSAR SWC? RTE? BSW? OS task?
  │  (internal) │
  └──────┬──────┘
         │
         ▼
  ROOT CAUSE
```

### 2.2 Step-by-Step Real-World Debugging Workflow

#### Step 1 — Signal Verification

Before opening any code, verify the input signals arriving at the ECU under test (EUT). A wrong value at the source propagates everywhere downstream and wastes hours.

**Questions to answer:**
- Is the CAN message present? Is the cycle time within tolerance (±10%)?
- Is the signal raw value plausible? Has the physical value been checked using factor/offset from the DBC?
- Are any signal counters or checksums failing?

**Tool:** CANalyzer / CANoe — open a trace window filtered on the relevant message IDs.

```
Example: VehicleSpeed (0x100) expected at 10ms ±1ms
Observation: 23ms inter-frame gap in trace
→ Suspect network load or sender timing issue, not the ADAS ECU
```

#### Step 2 — Log Correlation

Match the timestamp in the CANoe trace to the ECU internal log (if accessible via XCP or DLT).

- FIBEX/ARXML database must be loaded so signals are decoded, not raw hex.
- Enable DLT logging on the Ethernet backbone if running a multi-ECU bench.
- Export the trace to CSV / MF4 for Python-based post-processing (see Section 10).

**Tool:** CANoe Measurement, dSPACE ControlDesk, DLT Viewer (GENIVI)

#### Step 3 — ECU Stimulus Isolation

If the signal appears correct on the bus but the ECU still misbehaves:

1. Use XCP or UDS ReadDataByIdentifier to read the ECU's internal variable for the processed signal value.
2. Compare the raw CAN value to the ECU's internal representation — look for endianness bugs, scaling errors, or wrong IPDU mapping in the ARXML.
3. If XCP is available, set a measurement raster and capture the internal state variable alongside the CAN signal in the same time base.

**Tool:** CANoe XCP plugin, CANape (for calibration and measurement)

#### Step 4 — Network Analysis

For multi-ECU failures (especially ADAS):

- Check the **E2E (End-to-End) protection** status: are CRC or counter errors reported in the communication stack?
- Verify the **gateway routing table** — is the signal being correctly forwarded between bus segments?
- For Automotive Ethernet: use Wireshark with the SOME/IP dissector to verify service discovery and payload decoding.

**Tool:** CANoe Ethernet plugin, Wireshark + SOME/IP dissector plugin, Vector Logger Configurator

#### Step 5 — Software Investigation

Armed with the evidence from Steps 1–4:

- Review the AUTOSAR RTE configuration for the failing port
- Check OS task assignment — is the runnable in the correct period?
- Read the DTC memory (UDS 0x19) — confirmed fault codes may reveal internal fault monitors that fired before the observed symptom
- If code coverage is instrumented, identify un-executed branches

**Tool:** TRACE32 (Lauterbach) for live ECU debugging, DaVinci Configurator Pro (AUTOSAR config review), CANoe DiagTester for UDS

#### Step 6 — Root Cause Statement

A valid root cause statement answers **three questions**:

1. What failed? (Observable: brake torque demand = 0 N·m when AEB should have fired)
2. Why did it fail? (Mechanism: E2E CRC check failed on radar message, SWC input read stale value)
3. Why was it not detected earlier? (Process gap: E2E error injection not in the test case for this operating mode)

### 2.3 Tool Summary

| Tool | Used For |
|---|---|
| **CANoe** | Bus simulation, CAPL scripting, test automation, DTC readout, Ethernet capture |
| **CANalyzer** | Read-only bus analysis, signal decoding, timing measurements |
| **dSPACE ControlDesk** | Parameter modification, HIL I/O stimulation, bypass support |
| **Wireshark** | Packet-level Ethernet / SOME/IP analysis |
| **CANape** | XCP measurement, calibration, offline analysis |
| **TRACE32** | JTAG live debugging, stack trace, memory inspection |
| **DLT Viewer** | Linux-based DLT log viewing (used in AUTOSAR Adaptive) |
| **Python (cantools / asammdf)** | Log parsing, batch analysis, CI integration |

---

## 3. Protocol-Level Debugging

### 3.1 CAN / CAN FD Debugging

#### 3.1.1 CAN Frame Anatomy and Failure Modes

```
CAN Frame (Standard 11-bit):
 SOF | Arbitration ID (11-bit) | RTR | IDE | r0 | DLC (4-bit) | Data (0-64 bytes) | CRC | ACK | EOF

CAN FD addition: BRS (Bit Rate Switch), ESI (Error State Indicator)
```

**Common failure modes and how to identify them:**

| Failure Mode | Symptom in CANoe | Investigation Step |
|---|---|---|
| Frame not transmitted | Missing ID in trace | Check sender node status (Bus-Off?) |
| Wrong cycle time | Gap between frames > tolerated | Measure cycle time statistic (F11 → Statistics) |
| Signal wrong value | Physical value out of range | Verify DBC factor/offset, check sender |
| Counter wrap-around fault | Rapid toggling of signal valid flag | Verify E2E counter rollover handling |
| Bus-Off (TX error > 255) | No traffic from sender | Check termination, check error frames |
| CRC failure (CAN FD) | Error frames in trace | Transceiver config, BRS mode mismatch |

#### 3.1.2 Error Frame Detection

Error frames appear in CANalyzer/CANoe as red markers. A healthy bus should have zero error frames during normal operation. Any error frame must be investigated.

**Error frame sources:**
- Bit error: a node transmitted a dominant bit but read a recessive bit
- Stuff error: more than 5 consecutive bits of the same polarity
- Form error: fixed-form field violates format
- ACK error: no node acknowledged the frame

In CANoe CAPL, you can detect error frames programmatically:

```c
on errorFrame {
  write("Error frame detected at timestamp: %.4f ms, Error type: %d",
        timeNow() / 100000.0, this.errorType);
}
```

#### 3.1.3 Signal Timing Analysis

```
Spec: VehicleSpeed (0x100) cycle time = 10ms ± 1ms

Measurement checklist:
1. Capture > 1000 frames (1 minute at 10ms = 6000 frames min)
2. Use CANoe Statistics window: min/max/mean cycle time
3. Acceptance: all frames within [9.0ms, 11.0ms]
4. If jitter > 2ms: check OS timer resolution on sender ECU
                     check bus load (>70% load can cause arbitration delay)
```

### 3.2 UDS (ISO 14229) Diagnostics Debugging

#### 3.2.1 UDS Service Flow

```
Tester (CANoe/Python)          ECU
      │                          │
      │── 0x10 01 ──────────────►│  DiagnosticSessionControl: DefaultSession
      │◄── 0x50 01 ──────────────│  Positive Response
      │                          │
      │── 0x10 02 ──────────────►│  DiagnosticSessionControl: ProgrammingSession
      │◄── 0x50 02 ──────────────│  Positive Response
      │                          │
      │── 0x27 01 ──────────────►│  SecurityAccess: RequestSeed
      │◄── 0x67 01 <seed> ───────│  Positive Response (seed)
      │                          │
      │── 0x27 02 <key> ────────►│  SecurityAccess: SendKey
      │◄── 0x67 02 ──────────────│  Positive Response (access granted)
      │                          │
      │── 0x22 F1 90 ───────────►│  ReadDataByIdentifier: VIN
      │◄── 0x62 F1 90 <VIN> ─────│  Positive Response
      │                          │
      │── 0x19 02 CF ───────────►│  ReadDTCInformation: reportDTCByStatusMask
      │◄── 0x59 02 <DTC list> ───│  Positive Response
```

#### 3.2.2 Negative Response Code (NRC) Lookup

When an ECU returns a negative response (0x7F), the NRC byte explains why:

| NRC | Hex | Meaning | Common Cause |
|---|---|---|---|
| serviceNotSupported | 0x11 | Service not implemented | Wrong session, old SW |
| subFunctionNotSupported | 0x12 | Sub-function not recognised | Wrong byte order |
| incorrectMessageLengthOrInvalidFormat | 0x13 | Payload length wrong | DLC mismatch |
| conditionsNotCorrect | 0x22 | Precondition not met | Wrong session, engine running |
| requestSequenceError | 0x24 | Step skipped in sequence | Missed session/security unlock |
| requestOutOfRange | 0x31 | DID not known | Wrong DID, wrong ECU variant |
| securityAccessDenied | 0x33 | Key incorrect | Wrong algorithm, wrong seed |
| uploadDownloadNotAccepted | 0x70 | Flash memory busy | Re-flash pending |

**Debugging NRC 0x22 (conditionsNotCorrect):**

This is the most common NRC encountered in ADAS ECU testing. The usual causes:

1. ECU is in an incompatible operating mode (e.g., ignition off, ASIL monitor active)
2. A required service was not called first (e.g., session control before ReadDataByIdentifier)
3. A DTC is latched that blocks the service (check 0x19 first)

#### 3.2.3 TP (Transport Protocol ISO 15765-2) Debugging

For UDS payloads > 7 bytes, the CAN TP layer fragments the message into First Frame (FF) + Consecutive Frames (CF). Common TP failures:

```
Failure: ECU sends FF but never completes CFs

Root cause checklist:
1. Tester did not send Flow Control (FC) frame within timeout N_Bs (1000ms default)
2. FC block size = 0 (infinite) but tester implementation sends FS=0x00 then waits
3. N_Cs separation time min not respected (tester sending CFs too fast)
4. Incorrect padding (classic 0xCC padding not matching ECU expectation)
```

### 3.3 Automotive Ethernet (SOME/IP, DoIP)

#### 3.3.1 SOME/IP Service Discovery Debugging

SOME/IP SD (0xFFFF service ID) uses multicast UDP to announce and find services. When a client does not discover a service:

```
Wireshark filter: udp.port == 30490

Key packet types:
  - OfferService:   Server announcing availability
  - FindService:    Client searching for service
  - SubscribeEventGroup: Client subscribing for events
  - SubscribeEventGroupAck: Server acknowledging

Failure: FindService sent but no OfferService received

Debugging steps:
1. Is the server ECU sending OfferService? (Filter: someip.sd.type == 0x01)
2. Is the multicast address correct? (239.x.x.x) -- check ARXML vs actual config
3. TTL (time-to-live) in OfferService: if TTL=0, service is being withdrawn
4. Check IP addressing: server and client in same VLAN/subnet?
5. Check firewall / VLAN tagging on the Ethernet switch (common on bench setups)
```

#### 3.3.2 DoIP (Diagnostic over IP) Debugging

DoIP runs on TCP port 13400. Failure to establish a diagnostic session via DoIP:

```
Wireshark filter: tcp.port == 13400

DoIP message types:
  0x0001 - Vehicle Identification Request
  0x0004 - Vehicle Identification Response
  0x0005 - Routing Activation Request
  0x0006 - Routing Activation Response

Failure: Routing Activation Response with NACK

NACK codes:
  0x00 - Denied (unknown source address)
  0x01 - Denied (max sockets reached)
  0x02 - Denied (source IP unknown)
  0x03 - Denied (authentication required)
  0x04 - Confirmed (routing activation accepted)

Most common in lab: 0x01 (max sockets) — another DoIP client left a stale session
Fix: Restart ECU or send explicit connection close on previous session
```

---

## 4. AUTOSAR Debugging

### 4.1 RTE / SWC Communication Issues

#### 4.1.1 AUTOSAR Communication Model

```
    [Camera SWC] ──Sender Port──► [RTE] ──Receiver Port──► [Fusion SWC]
                     (S/R           │           (S/R
                    interface)      │          interface)
                                    │
                    [RTE]──────────►│────────────[COM]──► CAN bus
                              (IPDU mapping)
```

**Common RTE communication failures:**

| Failure | Root Cause | How to Detect |
|---|---|---|
| Stale data in receiver | Sender runnable not scheduled | Read `Rte_IStatus_<port>` — returns `RTE_E_MAX_AGE_EXCEEDED` |
| Wrong value | ARXML IPDU mapping error (byte order, bit position) | Compare DBC signal position vs ARXML signal definition |
| No update at all | RTE port not connected (unlinked) | DaVinci Configurator: check port connector |
| E2E CRC failure | Receiver E2E config does not match sender | Compare E2E profile (P01 vs P02 vs P07) in both SWCs |

#### 4.1.2 Reading RTE Return Values

Every `Rte_Read_<port>()` call returns a `Std_ReturnType`. Engineers often ignore this return value, which hides communication failures.

```c
/* Bad — return value ignored */
Rte_Read_ReceiverPort_VehicleSpeed(&speed);

/* Correct — always check return value */
Std_ReturnType ret;
VehicleSpeed_t speed;
ret = Rte_Read_ReceiverPort_VehicleSpeed(&speed);

if (ret == RTE_E_MAX_AGE_EXCEEDED) {
    /* Data is stale — sender timeout */
    speed = DEFAULT_SPEED_KPH;
    Dem_ReportErrorStatus(DEM_EVENT_SPEED_SIGNAL_LOST, DEM_EVENT_STATUS_FAILED);
}
else if (ret == RTE_E_NEVER_RECEIVED) {
    /* No data received since ECU start */
    speed = 0.0f;
}
else if (ret != RTE_E_OK) {
    /* Other RTE error — log and use safe default */
    Dem_ReportErrorStatus(DEM_EVENT_RTE_ERROR, DEM_EVENT_STATUS_FAILED);
}
```

### 4.2 Task Scheduling Issues

#### 4.2.1 OS Task Timing Verification

In AUTOSAR OS (OSEK), tasks run in priority-driven preemptive order. Timing issues arise when:

- A high-priority task runs over its deadline (deadline overrun)
- A lower-priority task is starved because a higher-priority task holds a resource too long
- A runnable is assigned to the wrong task (wrong period → wrong control loop update rate)

**Tool for OS timing analysis:** TRACE32 OS-Aware Debugging, Vector MICROSAR OS trace logging

```
OS Trace output (typical format):
[t=1000.020ms] Task_10ms_Control: ACTIVATE
[t=1000.021ms] Task_10ms_Control: RUNNING
[t=1000.028ms] Task_10ms_Control: TERMINATED  (exec time = 8ms, budget = 5ms → OVERRUN)
[t=1000.028ms] ProtectionHook called: E_OS_PROTECTION_TIME
```

#### 4.2.2 Stack Overflow Detection

Stack overflow corrupts adjacent memory and causes non-deterministic failures — the hardest bugs to find.

```c
/* AUTOSAR OS stack monitoring pattern */
/* At startup, fill task stack with known pattern */
#define STACK_FILL_PATTERN  0xDEADBEEFu

void Os_InitTaskStack(uint8_t *stack_base, uint32_t stack_size) {
    uint32_t *ptr = (uint32_t *)stack_base;
    uint32_t words = stack_size / sizeof(uint32_t);
    for (uint32_t i = 0u; i < words; i++) {
        ptr[i] = STACK_FILL_PATTERN;
    }
}

/* At runtime or in background task, check high-water mark */
uint32_t Os_GetStackUsage(uint8_t *stack_base, uint32_t stack_size) {
    uint32_t *ptr = (uint32_t *)stack_base;
    uint32_t unused = 0u;
    for (uint32_t i = 0u; i < stack_size / sizeof(uint32_t); i++) {
        if (ptr[i] == STACK_FILL_PATTERN) { unused++; }
        else { break; }
    }
    return stack_size - (unused * sizeof(uint32_t));
}
/* Alert if usage > 80% of allocated stack */
```

### 4.3 Memory Debugging

| Error Class | Symptom | Detection Method |
|---|---|---|
| Stack overflow | Random crashes, corrupted variables | Stack fill pattern + high-water mark |
| Heap fragmentation | Progressive memory exhaustion | No heap in AUTOSAR Classic — if present, ban dynamic allocation |
| Uninitialized memory | Non-reproducible errors at startup | Prefill RAM with 0xAA before init, check with TRACE32 |
| MPU violation | Immediate reset / exception | AUTOSAR OS MemoryProtectionHook — read the faulting address |
| Bit-flip (radiation / EMI) | Single-event upset | CRC on NVM data, ECC on RAM |

---

## 5. ADAS Debugging

### 5.1 Sensor Fusion Challenges

ADAS features like AEB, ACC, and highway pilot fuse data from multiple sensors (radar, camera, LiDAR, ultrasonic) into a single world model. Debugging sensor fusion failures is complex because:

1. Each sensor has its own coordinate system, mounting offset, and latency
2. Fusion algorithms (Kalman filter, object association) have internal state that accumulates errors
3. A sensor dropout (even 200ms) can cause object loss and a safety-relevant non-activation

#### 5.1.1 Coordinate System Validation

```
Vehicle coordinate system (SAE convention):
  X — forward (positive)
  Y — left (positive)
  Z — up (positive)

Camera: typically in camera frame (height above ground, optical axis)
Radar:  typically in radar frame (azimuth angle, elevation)
LiDAR:  in sensor frame (point cloud, meters)

Common fusion bug:
  Camera returns object at Y = +0.8m (0.8m left of camera optical axis)
  Radar returns same object at azimuth = -2° (=right of radar centre)
  After frame transformation, they do NOT associate → ghost object / missed detection

Debugging step:
  1. Read raw sensor data BEFORE coordinate transformation
  2. Manually transform using known mounting offset (from ARXML or calibration file)
  3. Plot both in vehicle frame — do they overlap within 0.5m tolerance?
```

#### 5.1.2 Sensor-Specific Debugging

**Radar:**

| Symptom | Investigation |
|---|---|
| Object appears then disappears | Check radar SNR (Signal-to-Noise Ratio) threshold — too high filters valid targets |
| Stationary object not reported | Check "static object" filter in CAN message — many radars filter stationary by default |
| Ghost objects at FoV edge | Multipath reflection — check beam pattern vs physical environment |
| Wrong velocity | Check radar reference speed input — if VehicleSpeed is wrong, ego compensation fails |

**Camera:**

| Symptom | Investigation |
|---|---|
| Lane not detected | Check illumination level (lux) — camera has minimum illumination spec |
| Object misclassified | Check camera calibration — intrinsic/extrinsic parameters |
| High latency | Check camera pipeline latency — some cameras add 80–120ms processing delay |
| Wrong lane offset | Check road curvature estimate — camera may use predicted path, not lane centre |

**LiDAR:**

| Symptom | Investigation |
|---|---|
| Point cloud density too low | Check rotation rate (Hz) and angular resolution setting |
| Missing sectors | Check occlusion (e.g., water, snow) — LiDAR degrades with particulates |
| Wrong range | Check return mode — strongest return vs last return affects range |

### 5.2 ADAS State Machine Debugging

ADAS features (ACC, AEB, LKA) are governed by state machines with complex activation conditions. A non-activation or false activation is almost always a state transition issue.

```
ACC State Machine (simplified):
OFF → STANDBY (driver presses SET, speed > 30 km/h)
STANDBY → ACTIVE (set speed confirmed, no brake override)
ACTIVE → OVERRIDE (driver brakes or accelerates beyond threshold)
ACTIVE → FAULT (radar comm loss > 500ms, or internal monitor fires)

Debugging a non-activation:
1. Which state is the ECU currently in? (UDS 0x22 or XCP measurement)
2. Which condition is blocking the transition? (Activation conditions checklist)
3. Is the blocking condition a valid sensor measurement or a comm fault?
```

---

## 6. Automotive Cybersecurity Debugging

### 6.1 Secure Boot Failures

Secure boot verifies the cryptographic signature of firmware at startup. Failure means the ECU will not start or will start in a degraded mode.

```
Secure Boot flow (typical):
1. ROM bootloader reads public key hash from OTP (One-Time Programmable) memory
2. Bootloader computes SHA-256 hash of application firmware
3. Verifies ECDSA signature using stored public key
4. If signature invalid → ECU enters BIST (Built-In Self Test) fail mode
5. Diagnostic DTC 0x100001 latched: BOOT_SIGNATURE_INVALID

Debugging secure boot failure:
Step 1: Read DTC over UDS 0x19 02 FF → get DTC 0x100001
Step 2: Read ECU programming date and software version (0x22 F189, F195)
Step 3: Compare software binary SHA-256 with expected hash in calibration database
Step 4: Check if OTP key was correctly provisioned (factory process audit)
Step 5: If emergency recovery needed: enter backdoor boot mode via bootloader pin

Root causes seen in practice:
- Binary modified by flashing tool without re-signing
- Wrong key version (ECU has key v2, binary signed with key v1)
- Endianness error in signature bytes during OTP write
- Partial flash (power loss during programming) → incomplete firmware
```

### 6.2 Authentication Failures (UDS SecurityAccess)

```
SecurityAccess 0x27 flow:
  1. Client sends RequestSeed (0x27 01)
  2. ECU returns 4-byte seed
  3. Client computes: key = HMAC-SHA256(seed, secret_key)[0:4]
  4. Client sends SendKey (0x27 02, key)
  5. ECU verifies — if mismatch → NRC 0x35 (invalidKey) + attempt counter++
  6. After 3 failed attempts → 10s delay (0x37 requiredTimeDelayNotExpired)

Debugging authentication failure:
Step 1: Capture seed in CANoe trace
Step 2: Compute expected key in Python using known algorithm (Section 10)
Step 3: Compare byte-by-byte with transmitted key
Step 4: If seed is correct but key wrong → check HMAC implementation (byte order?)
Step 5: If seed is always 0x00000000 → ECU in programming mode without prior seed generation

Common bugs:
- Secret key bytes reversed (big-endian vs little-endian mismatch)
- Wrong HMAC key length (truncated to 16 bytes instead of 32)
- Seed expires too quickly (ECU timer shorter than tester compute time)
```

### 6.3 Intrusion Detection System (IDS) Debugging

Automotive IDS monitors for network anomalies (unexpected message IDs, rate violations, payload anomalies). During testing, IDS rules often generate false positives.

```
IDS rule example: "Alert if VehicleSpeed (0x100) cycle time < 5ms"
False positive scenario:
  During HIL injection test, CAPL script sends 0x100 at 1ms → IDS fires
  IDS logs event to security log (via UDS or proprietary interface)
  ECU enters restricted mode

Debugging IDS false positive:
1. Read IDS event log: UDS 0x19 0A (reportSupportedDTCs) or proprietary service
2. Identify rule that fired (rule ID in log)
3. Review rule thresholds in IDS configuration (ARXML or proprietary config)
4. Adjust test stimulus to stay within IDS tolerance
5. Report to cybersecurity team if rule threshold is too tight for normal operation

ISO 21434 alignment:
- All IDS rule changes must be assessed for impact on TARA (Threat Analysis and Risk Assessment)
- False positive reduction must not compromise true positive detection rate
- Documented in cybersecurity work product CAL-MONITOR-001 or equivalent
```

### 6.4 ISO 21434 Debugging Checklist

| Activity | Standard Reference | Validation Check |
|---|---|---|
| Secure boot verification | ISO 21434 §10.4.2 | Boot signature test, tampered binary test |
| Key provisioning | ISO 21434 §11.4.3 | OTP write verification, key lifecycle test |
| Diagnostic authentication | ISO 21434 §11.4.5 | Brute-force attempt counter, lockout test |
| IDS monitoring | ISO 21434 §11.4.8 | Rate anomaly injection, unknown ID injection |
| Secure over-the-air (OTA) | ISO 21434 §12 | Tampered package rejection, rollback block |

---

## 7. HIL Debugging

### 7.1 HIL Bench Architecture for ADAS ECU

```
                        ┌───────────────────────────────────────┐
                        │         dSPACE HIL System              │
                        │  ┌────────────┐  ┌────────────────┐   │
                        │  │ Real-Time  │  │  I/O Board     │   │
                        │  │ Processor  │  │ (PWM, ADC, CAN)│   │
                        │  └────────────┘  └────────────────┘   │
                        └───────────────────────────────────────┘
                                          │
                          ┌───────────────┼──────────────────┐
                          │               │                  │
                    CAN FD Bus      Automotive ETH         LIN Bus
                          │               │                  │
                    ┌──────────┐   ┌──────────┐       ┌──────────┐
                    │ Radar ECU│   │Camera ECU│       │  BCM ECU │
                    └──────────┘   └──────────┘       └──────────┘
                          │                                  │
                          └─────────────────────────────────┘
                                          │
                                   ┌──────────┐
                                   │ ADAS ECU │  ← EUT (ECU Under Test)
                                   │(Fusion+  │
                                   │Control)  │
                                   └──────────┘
```

### 7.2 Fault Injection Testing

Fault injection verifies how the ECU behaves under abnormal conditions — a mandatory activity for ISO 26262 safety validation.

**Types of fault injections on HIL:**

| Fault Type | Implementation | What to Verify |
|---|---|---|
| Open circuit (signal loss) | dSPACE I/O board disconnect relay | ECU enters safe state, DTC stored |
| Short to ground | HIL wiring fault insertion | No ECU damage, limp-home mode |
| CAN message loss | CAPL: stop sending message | ECU detects timeout, fallback behaviour |
| Wrong signal value | CAPL: inject bad value | ECU validation monitor fires |
| Bus-Off | CAPL: inject error frames until bus-off | Automatic recovery within spec (100ms) |
| Power supply dip | HIL power supply: voltage drop to 6V for 100ms | ECU reset or survive per spec |
| Clock manipulation | HIL RTC: inject wrong timestamp | Secure session timestamp validation |

### 7.3 Signal Manipulation Using CANoe / dSPACE

Signal manipulation is used for:
- Stimulating the ADAS ECU with sensor data beyond the physical limits
- Verifying saturation and limiting behaviour
- Reproducing field incidents by replaying recorded bus traffic

```
CANoe Environment Variable method:
  An environment variable (EnvVar) is linked to a CAPL script
  The script modulates the CAN signal value on each transmit

dSPACE ControlDesk method:
  A variable (mapped to Simulink model) overrides the sensor simulation output
  Ramp, step, and noise generators available as built-in signal sources
  
For combined CANoe + dSPACE:
  Use CAPL DLL or COM API to send commands to dSPACE from CANoe test module
  This allows coordinated stimulation: inject fault at exactly the moment
  the ADAS ECU is in a specific state (e.g., AEB active)
```

---

## 8. STAR Format Scenarios

---

### Scenario 1 — ADAS: Adaptive Cruise Control Not Braking (AEB Failure)

**S — Situation:**

During system integration testing on a Level 2 highway assist ECU (AUTOSAR-based, ARM Cortex-M7, 500 kbps CAN FD), the AEB function repeatedly failed to apply braking during a front-collision scenario. The scenario used a stationary target at 20m with host vehicle speed of 60 km/h. The EuroNCAP AEB test requires braking engagement within 600ms of threat detection. The ECU was not applying any braking torque demand. Test log showed TTC = 1.1s (below 1.5s threshold) but BrakeReq = 0 N·m. Failure was reproducible 7/10 test runs. Not reproducible in SIL.

**T — Task:**

Identify why the AEB function was not generating a brake torque demand when TTC < 1.5s, prevent recurrence, and re-validate the AEB function within 3 working days.

**A — Actions:**

1. **First: Read DTC memory.**
   Connected CANoe DiagTester, sent UDS `0x19 02 CF` (all active DTCs).
   Result: `DTC 0xC19801 — RADAR_E2E_CRC_FAILURE — CONFIRMED`
   This revealed the fusion ECU was rejecting incoming radar messages due to E2E CRC failures.

2. **Isolated the E2E failure.**
   Opened CANoe trace filtered on `0x200` (RadarObject message).
   Used a DBC with E2E counter/CRC signals mapped. Observed:
   - CRC field value: `0xA3` (transmitted by radar ECU)
   - CRC expected by fusion ECU: `0x74`
   - Frame valid flag in fusion SWC: `FALSE` every frame

3. **Compared E2E configurations.**
   Opened ARXML for radar ECU and fusion ECU in DaVinci Configurator Pro.
   Found: Radar ECU configured with **E2E Profile P04** (CRC-32), Fusion ECU configured with **E2E Profile P01** (CRC-8).
   Configuration mismatch introduced during an ARXML merge in the previous sprint.

4. **Verified hypothesis via CAPL injection.**
   Wrote a CAPL script (Section 9.3) to transmit `0x200` with a manually computed P01-compatible CRC.
   With correct CRC: fusion SWC accepted all frames, AEB activated in 7/7 test runs.

5. **Traced change cause.**
   Git blame on the ARXML showed the wrong profile was committed during E2E profile upgrade — reviewer did not check the fusion ECU receiver configuration was updated to match the sender.

**R — Result:**

- **Root cause:** E2E Profile mismatch between RadarObject sender (P04) and receiver (P01) — ARXML merge error.
- **Fix:** Aligned E2E profile to P07 (AUTOSAR 4.3 recommended for CAN FD) in both sender and receiver ARXML. Configuration reviewed in DaVinci, re-generated SWC code.
- **Validated:** AEB activated in 10/10 runs. DTC no longer set. E2E error counter confirmed zero.
- **Process fix:** Added ARXML diff review checklist item for E2E profile consistency to PR review template. Added CAPL test case for E2E CRC injection to smoke test suite.

---

### Scenario 2 — CAN Communication: Missing VehicleSpeed Signal Causing LKA Deactivation

**S — Situation:**

During continuous regression on a lane-keeping assist (LKA) ECU at 25°C ambient (HIL bench), LKA function was intermittently deactivating and displaying DTC `0xD00501 — VEHICLE_SPEED_SIGNAL_TIMEOUT`. The deactivation lasted 2–3 seconds then LKA re-engaged. Test engineers initially blamed the HIL network simulation. The issue occurred approximately once per hour and was not reproducible on request. IDs involved: `VehicleSpeed (0x100)` sourced from ABS ECU simulation.

**T — Task:**

Identify the root cause of intermittent VehicleSpeed signal loss, determine if the cause is in the HIL simulation, the network, or the ECU, and implement a fix that eliminates the deactivation.

**A — Actions:**

1. **Enabled global CANoe bus statistics logging.**
   Added a background CAPL script to log cycle time for `0x100` continuously with microsecond-resolution timestamps.
   After 3 hours: captured 4 occurrences of `0x100` cycle time = 312ms (spec = 10ms ± 1ms).

2. **Correlated with HIL system load.**
   Cross-referenced with dSPACE ControlDesk performance counter log.
   At each occurrence: HIL CPU load = 98.7%. Normal load = 45%.
   Pattern: a 1-second sensor model update (LIDAR point cloud processing) was scheduled in the same task as the ABS speed sender.

3. **Read HIL task timing configuration.**
   Opened dSPACE experiment configuration. Found: `VehicleSpeed_Send_Task` allocated to the **2ms real-time task**. A newly added LIDAR simulation block was also placed in the **2ms task** (previous engineer assumed it was lightweight — it was not, 15ms computation).

4. **Verified with task execution time measurement.**
   Added execution time measurement block in Simulink HIL model. Confirmed: LIDAR block took 14ms in worst case, causing the 2ms task to overrun, delaying VehicleSpeed transmission.

5. **Additionally confirmed ECU behaviour was correct.**
   The LKA ECU was correctly detecting the 312ms gap (timeout threshold = 200ms per spec).
   LKA deactivation was the expected safe-state response — ECU behaviour was correct.

**R — Result:**

- **Root cause:** LIDAR simulation block incorrectly placed in the 2ms HIL real-time task, causing task overrun and VehicleSpeed CAN transmission delay > 200ms timeout.
- **Fix:** Moved LIDAR block to 50ms task. VehicleSpeed sender isolated in 2ms task with execution budget monitoring.
- **Validated:** 72-hour soak test, zero LKA deactivations. Cycle time monitoring confirmed VehicleSpeed within 9.8–10.2ms for entire run.
- **Process fix:** HIL model review checklist updated: all newly added simulation blocks must declare their measured worst-case execution time and confirm task budget before merge.

---

### Scenario 3 — AUTOSAR: RTE Signal Not Updating in Receiver SWC

**S — Situation:**

In a new AUTOSAR Classic platform (Infineon AURIX TC397, 200 MHz), the ComfortTorqueControl SWC (receiver) was reading a constant `SteeringTorqueRequest = 0.0f` from the RTE, despite the sending SWC (LKASteering SWC) demonstrably writing non-zero values. The LKA function was active (confirmed via DTC absence and state machine XCP measurement). The bug was project-critical — the LKA system was 2 weeks from gate freeze.

**T — Task:**

Determine why the receiver SWC was reading zero torque demand despite the sender SWC writing non-zero values, and fix it without redesigning the interface.

**A — Actions:**

1. **Instrumented the sender and receiver SWCs.**
   Added XCP measurement variables via CANape:
   - `LKASteering_SteeringTorqueRequest_out` (sender)
   - `ComfortTorque_SteeringTorqueRequest_in` (receiver)
   XCP raster: 10ms.
   Result: sender writing `+2.3 Nm`, receiver reading `0.0f` simultaneously.

2. **Checked RTE connection.**
   In DaVinci Developer: verified port connector between `LKASteering/SteeringTorquePort` and `ComfortTorque/SteeringTorquePort`. Connection existed and showed no errors.

3. **Examined IPDU routing.**
   The signal was routed through COM (the interface was client–server, not direct sender–receiver — this was the first clue).
   Checked `ComSignal_SteeringTorqueRequest` in ARXML — found `ComUpdateBit` enabled with update bit position = bit 63 of the IPDU.

4. **Checked update bit behaviour.**
   The LKASteering SWC was writing `SteeringTorqueRequest` via `Rte_Write` but **not** calling `Com_SendSignalWithMetaData` to set the update bit.
   COM layer was configured to only forward the signal to the receiver when the update bit was set. The receiver was therefore always reading the initial value = 0.0f.

5. **Confirmed with a direct workaround.**
   Temporarily disabled `ComUpdateBit` in the COM ARXML → receiver immediately read correct values.
   This confirmed the root cause.

**R — Result:**

- **Root cause:** `ComUpdateBit` was enabled for the `SteeringTorqueRequest` signal in COM configuration. The sender SWC was using `Rte_Write` (which does not set the update bit) instead of the correct COM notification pattern.
- **Fix:** Modified the sender SWC to call `Com_SendSignal` after `Rte_Write`, which sets the update bit, triggering COM forwarding to the receiver.
- **Alternative fix applied (approved by SWC owner):** Disabled `ComUpdateBit` for this signal — it was enabled by copy-paste from a different signal's config and was not required.
- **Validated:** XCP measurement confirmed `ComfortTorque_SteeringTorqueRequest_in` now tracks sender within one task cycle. LKA steering test passed.

---

### Scenario 4 — Automotive Ethernet: SOME/IP Service Not Discovered

**S — Situation:**

On a domain gateway ECU (NXP S32G, running AUTOSAR Adaptive on Linux QNX), the ADAS Fusion service (publishing `FusionObjectList` over SOME/IP on service ID `0x0501`, instance ID `0x0001`) was not discovered by the consuming ADAS Planning ECU. As a result, the planning ECU could not subscribe to `FusionObjectList` events and all path-planning outputs were suppressed. The SOME/IP SD multicast address was `239.1.0.1:30490`. The bench used a managed Ethernet switch (100BASE-T1 + 1000BASE-T1).

**T — Task:**

Identify why SOME/IP service discovery was failing between the Fusion ECU and Planning ECU, and restore the service subscription.

**A — Actions:**

1. **Captured SOME/IP traffic with Wireshark.**
   Filter: `udp.port == 30490`
   Observation: Fusion ECU was sending `OfferService` packets every 500ms (TTL=5s).
   Planning ECU was sending `FindService` packets every 1000ms.
   BUT: `FindService` packets were NOT reaching the Fusion ECU subnet — confirmed by capture at both ports of the switch.

2. **Investigated VLAN configuration.**
   The managed switch had a VLAN config pushed by the network team the previous day.
   VLAN 10: Fusion ECU, VLAN 20: Planning ECU.
   The `239.1.0.1` multicast address was **not** in the VLAN multicast group membership table (IGMP snooping was enabled on the switch, and neither ECU had sent an IGMP join for `239.1.0.1`).

3. **Verified IGMP join behaviour.**
   Wireshark filter: `igmp`
   Fusion ECU was not sending IGMP Membership Reports (required for IGMP snooping).
   Root cause: AUTOSAR Adaptive SoAD (Socket Adapter) module was configured with multicast join = FALSE in the `SoAdSocketConnection` ARXML.

4. **Verified with temporary fix.**
   Disabled IGMP snooping on the switch → SOME/IP SD multicast forwarded to all ports → Planning ECU discovered service immediately.

5. **Implemented correct fix.**
   Set `SoAdMulticastLocalAddress` and `SoAdSocketConnectionGroup MulticastJoin = TRUE` in the SoAD ARXML for the Fusion ECU.
   Regenerated the AUTOSAR Adaptive middleware configuration.

**R — Result:**

- **Root cause:** AUTOSAR Adaptive SoAD not configured to send IGMP Membership Report for the SOME/IP SD multicast group. IGMP snooping on the bench switch silently dropped multicast traffic not associated with a known IGMP membership.
- **Fix:** Enabled multicast join in SoAD for `239.1.0.1`. IGMP snooping left enabled (correct behaviour for production network).
- **Validated:** Wireshark confirmed IGMP join sent within 100ms of ECU startup. `OfferService` forwarded correctly. Planning ECU subscribed within 2s of FusionECU boot.

---

### Scenario 5 — Cybersecurity: ECU Rejecting Diagnostic Session (Authentication Failure)

**S — Situation:**

During end-of-line (EOL) programming at the supplier's manufacturing facility, 12% of ECUs on the production line were rejecting the `SecurityAccess 0x27 02` (SendKey) request with NRC `0x35 (invalidKey)`. ECUs were entering the 10-second lockout state. The algorithm used PRNG-seeded HMAC-SHA256 with a 4-byte key. The issue was blocking production throughput. ECU hardware was a brand-new batch (different PCB revision from the development units).

**T — Task:**

Identify why the new ECU hardware batch was producing SecurityAccess NRC 0x35 failures, determine if the issue was in the ECU firmware, the hardware, or the tester-side algorithm, and provide a production-safe fix within 24 hours.

**A — Actions:**

1. **Captured seed-key exchange in CANoe.**
   Installed CANoe on the production tester laptop. Captured 50 seed-key pairs from failing ECUs.
   Observation: Seed values from failing ECUs were always 4-byte sequences where **byte 0 = byte 2** and **byte 1 = byte 3** (palindrome pattern).

2. **Analysed the PRNG source.**
   The PRNG seed in the firmware used the HSM (Hardware Security Module) TRNG (True Random Number Generator) peripheral.
   Requested schematic comparison between old and new PCB revision.
   Found: new PCB revision used a different HSM vendor (Renesas RSIP-E51A vs old ST SafeZone). The TRNG output format was different — new HSM returns two 32-bit words, but the firmware was reading only the first word, which had an internal mirroring quirk in the Renesas implementation.

3. **Reproduced on bench.**
   Obtained a new-revision ECU for bench debugging.
   Connected TRACE32, read TRNG register directly:
   ```
   TRNG_OUTPUT_REG[0] = 0xA3F1A3F1   ← palindrome (mirrored word)
   TRNG_OUTPUT_REG[1] = 0x72C948A1   ← would have been correct
   ```
   Confirmed: firmware was reading `TRNG_OUTPUT_REG[0]` only. Old HSM did not have mirroring quirk.

4. **Computed correct key from palindrome seed.**
   The palindrome seed caused the HMAC output to collide with only 2^16 possible values instead of 2^32.
   Some seeds had been seen by the tester before → key computed correctly → these ECUs passed.
   But the collision space meant 12% of seeds were rare enough that the tester lookup table did not contain the mapping → NRC 0x35.

5. **Implemented fix.**
   Changed firmware to read `TRNG_OUTPUT_REG[0] XOR TRNG_OUTPUT_REG[1]` for the seed.
   Verified with TRACE32: new seeds were uniformly distributed, no palindrome pattern.
   Applied fix as a security hotfix patch (fast-lane JIRA process per SOPs).

**R — Result:**

- **Root cause:** New HSM hardware revision (Renesas RSIP-E51A) had a TRNG register mirroring behaviour not present in the previous ST HSM. Firmware reading only the first TRNG word produced low-entropy seeds, causing HMAC key space collapse and intermittent NRC 0x35 failures.
- **Fix:** Updated firmware to XOR both TRNG words for seed generation. Entropy confirmed via NIST SP 800-22 randomness test on 10,000 samples.
- **Production impact:** Zero failures after fix deployment. Line re-validated.
- **Process fix:** HSM peripheral driver porting checklist created. TRNG entropy validation added to EOL functional test. Cybersecurity regression test for SecurityAccess added to CI pipeline.

---

## 9. CAPL Scripts for Debugging

### 9.1 CAN Message Simulation and Fault Injection

```c
/*
 * Script: ADAS_Sensor_Simulation.can
 * Purpose: Simulate radar and camera inputs to ADAS Fusion ECU
 * Signals:
 *   0x200 - RadarObject (dist, rel_vel, valid, obj_type)
 *   0x201 - CameraLane  (left_offset, right_offset, quality)
 *   0x100 - VehicleSpeed
 *
 * Scenario: Closing target from 120m to 8m at 60km/h host speed
 *           Expected: AEB activates when TTC < 1.5s
 */

variables {
  msTimer  tmrRadar;
  msTimer  tmrCamera;
  msTimer  tmrSpeed;
  msTimer  tmrScenario;

  message 0x200 gRadarObject;   /* RadarObject */
  message 0x201 gCameraLane;    /* CameraLane  */
  message 0x100 gVehicleSpeed;  /* VehicleSpeed */

  float   gTargetDist   = 120.0;  /* metres */
  float   gTargetRelVel = -15.0;  /* m/s (closing) */
  float   gHostSpeed    = 60.0;   /* km/h */

  int     gFaultMode    = 0;      /* 0=normal, 1=drop radar, 2=bad CRC */
  int     gScenarioStep = 0;
}

on start {
  setTimer(tmrRadar,    20);   /* 20ms — CAN FD radar cycle */
  setTimer(tmrCamera,   20);   /* 20ms */
  setTimer(tmrSpeed,    10);   /* 10ms */
  setTimer(tmrScenario, 100);  /* scenario step every 100ms */
  write("ADAS Sensor Simulation started");
}

/* ── Radar simulation ────────────────────────────────────────────── */
on timer tmrRadar {
  if (gFaultMode == 1) {
    /* Fault mode 1: drop radar frames — simulates sensor comm loss */
    write("[FAULT] Radar frame dropped at t=%.1f ms", timeNow()/10.0);
    setTimer(tmrRadar, 20);
    return;
  }

  float ttc;
  if (gTargetRelVel < -0.1) {
    ttc = -gTargetDist / gTargetRelVel;  /* positive TTC in seconds */
  } else {
    ttc = 99.0;
  }

  /* Encode signals: factor=0.01 for distance and velocity */
  gRadarObject.byte(0) = (word)(gTargetDist / 0.01) & 0xFF;
  gRadarObject.byte(1) = ((word)(gTargetDist / 0.01) >> 8) & 0xFF;

  /* Relative velocity: signed, factor=0.01, offset=0 */
  long rawVel = (long)(gTargetRelVel / 0.01);
  gRadarObject.byte(2) = rawVel & 0xFF;
  gRadarObject.byte(3) = (rawVel >> 8) & 0xFF;

  /* Validity and object type */
  gRadarObject.byte(4) = (gTargetDist < 150.0) ? 0x01 : 0x00;
  gRadarObject.byte(5) = 0x01;  /* RADAR_OBJ_CAR */

  /* TTC field: factor=0.1 */
  gRadarObject.byte(6) = (byte)min(ttc / 0.1, 255);

  if (gFaultMode == 2) {
    /* Fault mode 2: corrupt CRC byte (E2E fault injection) */
    gRadarObject.byte(7) = 0xFF;  /* incorrect CRC */
    write("[FAULT] Injecting bad CRC in RadarObject at t=%.1f ms TTC=%.2fs",
          timeNow()/10.0, ttc);
  } else {
    /* Correct CRC — simplified P01 CRC-8 */
    gRadarObject.byte(7) = computeCRC8(gRadarObject);
  }

  output(gRadarObject);

  /* Alert when AEB threshold reached */
  if (ttc < 1.5 && ttc > 0) {
    write("[ALERT] AEB threshold: TTC=%.2fs, Dist=%.1fm — checking ECU response",
          ttc, gTargetDist);
  }

  setTimer(tmrRadar, 20);
}

/* ── Camera lane simulation ──────────────────────────────────────── */
on timer tmrCamera {
  /* Good lane quality, slight right drift */
  gCameraLane.byte(0) = 0x03;  /* left_quality = 3 */
  gCameraLane.byte(1) = 0x03;  /* right_quality = 3 */

  /* Left offset: +0.05m drift to right → need left correction */
  word rawLO = (word)(0.05 / 0.001);
  gCameraLane.byte(2) = rawLO & 0xFF;
  gCameraLane.byte(3) = (rawLO >> 8) & 0xFF;

  /* Right offset: -0.05m */
  word rawRO = (word)((-0.05 + 32.768) / 0.001);
  gCameraLane.byte(4) = rawRO & 0xFF;
  gCameraLane.byte(5) = (rawRO >> 8) & 0xFF;

  output(gCameraLane);
  setTimer(tmrCamera, 20);
}

/* ── VehicleSpeed ────────────────────────────────────────────────── */
on timer tmrSpeed {
  word rawSpeed = (word)(gHostSpeed / 0.01);
  gVehicleSpeed.byte(0) = rawSpeed & 0xFF;
  gVehicleSpeed.byte(1) = (rawSpeed >> 8) & 0xFF;
  gVehicleSpeed.byte(2) = 0x01;  /* valid */
  gVehicleSpeed.byte(3) = 0x00;  /* forward */
  output(gVehicleSpeed);
  setTimer(tmrSpeed, 10);
}

/* ── Scenario progression ────────────────────────────────────────── */
on timer tmrScenario {
  gScenarioStep++;

  if (gScenarioStep < 30) {
    /* Phase 1: approach target at current speed */
    gTargetDist = gTargetDist + gTargetRelVel * 0.1;
    if (gTargetDist < 2.0) { gTargetDist = 2.0; }
  }
  else if (gScenarioStep == 30) {
    /* Phase 2: inject E2E fault */
    gFaultMode = 2;
    write("[SCENARIO] Step 30: E2E CRC fault injection active");
  }
  else if (gScenarioStep == 40) {
    /* Phase 3: restore normal */
    gFaultMode = 0;
    write("[SCENARIO] Step 40: fault injection stopped");
  }
  else if (gScenarioStep == 50) {
    /* Phase 4: drop radar */
    gFaultMode = 1;
    write("[SCENARIO] Step 50: radar dropout active");
  }
  else if (gScenarioStep == 65) {
    gFaultMode = 0;
    write("[SCENARIO] Step 65: scenario complete — check DTC and AEB log");
  }

  setTimer(tmrScenario, 100);
}

/* ── CRC helper (simplified CRC-8 for debugging) ────────────────── */
byte computeCRC8(message msg) {
  byte crc = 0xFF;
  int i;
  for (i = 0; i < 7; i++) {
    crc = crc ^ msg.byte(i);
    int b;
    for (b = 0; b < 8; b++) {
      if (crc & 0x80) { crc = (crc << 1) ^ 0x1D; }
      else            { crc = (crc << 1); }
    }
  }
  return crc;
}
```

### 9.2 UDS Diagnostic Automation — CAPL

```c
/*
 * Script: UDS_Diagnostic_Suite.can
 * Purpose: Full UDS diagnostic sequence:
 *          1. Open extended diagnostic session
 *          2. SecurityAccess unlock
 *          3. Read all ADAS DTCs
 *          4. Clear DTCs
 *          5. Read VehicleSpeed live data
 *
 * ECU: ADAS Fusion ECU
 * Transport: CAN ID 0x744 (Tester → ECU), 0x74C (ECU → Tester)
 * Standard: ISO 14229-1
 */

variables {
  msTimer     tmrUDS;
  message 0x744 gUDSRequest;   /* Tester → ECU            */
  byte         gRxBuf[256];    /* Response buffer          */
  int          gUDSStep = 0;   /* Step in diagnostic flow  */

  /* Security algorithm constants (demonstration — use HSM in production) */
  long gSeed;
  long gKey;
}

on start {
  setTimer(tmrUDS, 500);  /* Start UDS sequence after 500ms */
  write("UDS Diagnostic Suite — ADAS ECU (0x744/0x74C)");
}

on timer tmrUDS {
  switch (gUDSStep) {

    case 0:  /* DiagnosticSessionControl — Extended Diagnostic Session */
      write("[UDS Step 0] Opening Extended Diagnostic Session (0x10 03)");
      sendUDS(2, 0x10, 0x03);
      break;

    case 1:  /* SecurityAccess — Request Seed */
      write("[UDS Step 1] SecurityAccess — RequestSeed (0x27 01)");
      sendUDS(2, 0x27, 0x01);
      break;

    case 2:  /* SecurityAccess — Send Key (computed in on message handler) */
      write("[UDS Step 2] SecurityAccess — SendKey (0x27 02, key=0x%08X)", gKey);
      gUDSRequest.dlc  = 6;
      gUDSRequest.byte(0) = 0x05;  /* Length */
      gUDSRequest.byte(1) = 0x27;  /* Service */
      gUDSRequest.byte(2) = 0x02;  /* Sub-function: SendKey */
      gUDSRequest.byte(3) = (gKey >> 24) & 0xFF;
      gUDSRequest.byte(4) = (gKey >> 16) & 0xFF;
      gUDSRequest.byte(5) = (gKey >>  8) & 0xFF;
      gUDSRequest.byte(6) = (gKey >>  0) & 0xFF;
      output(gUDSRequest);
      break;

    case 3:  /* ReadDTCInformation — All active DTCs (0x19 02 CF) */
      write("[UDS Step 3] ReadDTCInformation — Active DTCs (0x19 02 CF)");
      sendUDS(3, 0x19, 0x02, 0xCF);
      break;

    case 4:  /* ClearDTCInformation — Clear All (0x14 FF FF FF) */
      write("[UDS Step 4] ClearDTCInformation (0x14 FF FF FF)");
      gUDSRequest.dlc  = 4;
      gUDSRequest.byte(0) = 0x03;
      gUDSRequest.byte(1) = 0x14;
      gUDSRequest.byte(2) = 0xFF;
      gUDSRequest.byte(3) = 0xFF;
      gUDSRequest.byte(4) = 0xFF;
      output(gUDSRequest);
      break;

    case 5:  /* ReadDataByIdentifier — VehicleSpeed live data (0x22 F1 01) */
      write("[UDS Step 5] ReadDataByIdentifier — VehicleSpeed (0x22 F1 01)");
      sendUDS(3, 0x22, 0xF1, 0x01);
      break;

    case 6:
      write("[UDS] Sequence complete");
      break;
  }

  setTimer(tmrUDS, 300);  /* Next step after P2 timeout */
}

/* ── UDS Response Handler ────────────────────────────────────────── */
on message 0x74C {
  byte service = this.byte(1);
  byte subFunc = this.byte(2);

  /* Negative Response */
  if (service == 0x7F) {
    byte reqSvc = this.byte(2);
    byte nrc    = this.byte(3);
    write("[UDS ERROR] NRC=0x%02X for service 0x%02X → %s",
          nrc, reqSvc, nrcToString(nrc));
    return;
  }

  switch (service) {
    case 0x50:  /* SessionControl positive response */
      write("[UDS] Session opened: type=0x%02X  P2=%.0f ms",
            subFunc, ((this.byte(3) << 8) | this.byte(4)) * 0.25);
      gUDSStep = 1;
      break;

    case 0x67:  /* SecurityAccess positive response */
      if (subFunc == 0x01) {
        /* Extract seed and compute key */
        gSeed = ((long)this.byte(3) << 24) | ((long)this.byte(4) << 16)
              | ((long)this.byte(5) <<  8) |  (long)this.byte(6);
        gKey  = computeSecurityKey(gSeed);
        write("[UDS] Seed received: 0x%08X, Computed key: 0x%08X", gSeed, gKey);
        gUDSStep = 2;
      } else if (subFunc == 0x02) {
        write("[UDS] Security access GRANTED");
        gUDSStep = 3;
      }
      break;

    case 0x59:  /* ReadDTCInformation positive response */
      parseDTCResponse(this);
      gUDSStep = 4;
      break;

    case 0x54:  /* ClearDTCInformation positive response */
      write("[UDS] DTCs cleared successfully");
      gUDSStep = 5;
      break;

    case 0x62:  /* ReadDataByIdentifier positive response */
      parseRDBIResponse(this);
      gUDSStep = 6;
      break;
  }
}

/* ── DTC Response Parser ─────────────────────────────────────────── */
void parseDTCResponse(message msg) {
  int i = 3;  /* Skip service byte, sub-function, status availability */
  int dtcCount = 0;
  int totalLen = msg.byte(0) + 1;

  write("[UDS] DTC List:");
  while (i + 3 < totalLen) {
    long dtcId = ((long)msg.byte(i) << 16)
               | ((long)msg.byte(i+1) << 8)
               |  (long)msg.byte(i+2);
    byte status = msg.byte(i+3);
    write("  DTC 0x%06X  Status=0x%02X  [%s%s%s]",
          dtcId, status,
          (status & 0x01) ? "FAILED " : "",
          (status & 0x04) ? "PENDING " : "",
          (status & 0x08) ? "CONFIRMED" : "");
    i += 4;
    dtcCount++;
  }
  if (dtcCount == 0) {
    write("  No active DTCs");
  }
}

/* ── Live Data Parser ───────────────────────────────────────────── */
void parseRDBIResponse(message msg) {
  word did  = ((word)msg.byte(2) << 8) | msg.byte(3);
  if (did == 0xF101) {
    /* VehicleSpeed: factor=0.01, 2 bytes */
    word rawSpeed = ((word)msg.byte(4) << 8) | msg.byte(5);
    float physSpeed = rawSpeed * 0.01;
    write("[UDS] VehicleSpeed (0xF101) = %.2f km/h (raw=0x%04X)",
          physSpeed, rawSpeed);
  }
}

/* ── Security key algorithm (demonstration — DO NOT use in production) ── */
long computeSecurityKey(long seed) {
  /* Simplified HMAC-like XOR for demonstration */
  long mask = 0xA5A5A5A5;
  long key  = seed ^ mask;
  key = ((key << 3) | (key >> 29)) ^ 0x12345678;
  return key;
}

/* ── Helper: send variable-length UDS request ───────────────────── */
void sendUDS(int dataLen, byte b0, byte b1, byte b2) {
  gUDSRequest.dlc  = dataLen + 1;
  gUDSRequest.byte(0) = dataLen;
  gUDSRequest.byte(1) = b0;
  if (dataLen > 1) { gUDSRequest.byte(2) = b1; }
  if (dataLen > 2) { gUDSRequest.byte(3) = b2; }
  output(gUDSRequest);
}

/* ── NRC to string ──────────────────────────────────────────────── */
char nrcToString(byte nrc)[] {
  switch (nrc) {
    case 0x10: return "generalReject";
    case 0x11: return "serviceNotSupported";
    case 0x12: return "subFunctionNotSupported";
    case 0x13: return "incorrectMessageLength";
    case 0x22: return "conditionsNotCorrect";
    case 0x24: return "requestSequenceError";
    case 0x31: return "requestOutOfRange";
    case 0x33: return "securityAccessDenied";
    case 0x35: return "invalidKey";
    case 0x36: return "exceededNumberOfAttempts";
    case 0x37: return "requiredTimeDelayNotExpired";
    case 0x70: return "uploadDownloadNotAccepted";
    case 0x78: return "requestCorrectlyReceivedResponsePending";
    default:   return "unknownNRC";
  }
}
```

### 9.3 E2E CRC Fault Injection Script

```c
/*
 * Script: E2E_Fault_Injection.can
 * Purpose: Test ECU response to E2E CRC failures on RadarObject message
 *          Used to verify DTC storage and safe-state transitions
 *
 * Expected behaviour:
 *   - After 3 consecutive CRC failures: DTC 0xC19801 CONFIRMED
 *   - ACC/AEB: enter safe state (brake demand = 0, ACC deactivated)
 *   - After CRC restored: DTC moves to PENDING (not immediately cleared)
 */

variables {
  msTimer  tmrE2ETest;
  message 0x200 gRadarMsg;

  int  gTestPhase      = 0;
  int  gFaultFrameCount = 0;
  int  gGoodFrameCount  = 0;
  BOOL gFaultActive    = FALSE;
}

on start {
  setTimer(tmrE2ETest, 20);
  write("E2E Fault Injection Test — RadarObject (0x200)");
  write("Phase 0: Good frames for 1s baseline");
}

on timer tmrE2ETest {
  gTestPhase == 0 → check below via counter

  if (!gFaultActive) {
    gGoodFrameCount++;
    sendRadarMessage(FALSE);  /* Good CRC */

    if (gGoodFrameCount == 50) {   /* 50 × 20ms = 1000ms */
      write("Phase 1: Injecting 10 bad CRC frames");
      gFaultActive = TRUE;
      gFaultFrameCount = 0;
    }
  }
  else {
    gFaultFrameCount++;
    sendRadarMessage(TRUE);   /* Bad CRC */

    if (gFaultFrameCount == 10) {  /* 10 × 20ms = 200ms */
      write("Phase 2: CRC faults done — checking DTC via UDS next cycle");
      gFaultActive = FALSE;
      gGoodFrameCount = 0;
      /* Trigger UDS DTC read — implemented in UDS_Diagnostic_Suite.can */
    }
  }

  setTimer(tmrE2ETest, 20);
}

void sendRadarMessage(BOOL injectFault) {
  float dist    = 45.0;   /* 45m target */
  float relVel  = -8.0;   /* closing */
  float ttc     = dist / 8.0;

  word rawDist = (word)(dist / 0.01);
  gRadarMsg.byte(0) = rawDist & 0xFF;
  gRadarMsg.byte(1) = (rawDist >> 8) & 0xFF;

  long rawVel = (long)(relVel / 0.01);
  gRadarMsg.byte(2) = rawVel & 0xFF;
  gRadarMsg.byte(3) = (rawVel >> 8) & 0xFF;

  gRadarMsg.byte(4) = 0x01;  /* valid */
  gRadarMsg.byte(5) = 0x01;  /* CAR */
  gRadarMsg.byte(6) = (byte)(ttc / 0.1);

  if (injectFault) {
    gRadarMsg.byte(7) = 0xFF;  /* Intentionally wrong CRC */
    write("[FAULT] Frame %d: injected bad CRC=0xFF at t=%.1fms",
          gFaultFrameCount, timeNow()/10.0);
  } else {
    gRadarMsg.byte(7) = computeCRC8(gRadarMsg);
  }

  output(gRadarMsg);
}
```

---

## 10. Python Scripts for Debugging

### 10.1 CAN Log Parser and Signal Extractor

```python
"""
can_log_parser.py
-----------------
Parses a CANoe .asc or .blf log file and extracts decoded signals
using a DBC file. Identifies timing violations, stuck signals, and
anomalies.

Dependencies: cantools, python-can, pandas, matplotlib
Install:      pip install cantools python-can pandas matplotlib
"""

import cantools
import can
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import statistics


@dataclass
class SignalStats:
    """Statistics for a single CAN signal over the log duration."""
    signal_name:     str
    message_id:      int
    values:          List[float]     = field(default_factory=list)
    timestamps:      List[float]     = field(default_factory=list)
    cycle_times_ms:  List[float]     = field(default_factory=list)

    @property
    def min_value(self)  -> float: return min(self.values) if self.values else 0.0
    @property
    def max_value(self)  -> float: return max(self.values) if self.values else 0.0
    @property
    def mean_value(self) -> float: return statistics.mean(self.values) if self.values else 0.0
    @property
    def min_cycle_ms(self)  -> float: return min(self.cycle_times_ms) if self.cycle_times_ms else 0.0
    @property
    def max_cycle_ms(self)  -> float: return max(self.cycle_times_ms) if self.cycle_times_ms else 0.0
    @property
    def mean_cycle_ms(self) -> float: return statistics.mean(self.cycle_times_ms) if self.cycle_times_ms else 0.0


class CANLogAnalyser:
    """
    Parses CAN log files, decodes signals via DBC, and reports anomalies.

    Usage:
        analyser = CANLogAnalyser("vehicle.dbc")
        analyser.load_log("test_run_001.blf")
        analyser.analyse(message_ids=[0x100, 0x200, 0x201, 0x300])
        analyser.print_report()
        analyser.plot_signal("RadarObject", "distance_m")
    """

    TIMING_TOLERANCE_PCT = 0.10  # ±10% cycle time tolerance

    def __init__(self, dbc_path: str):
        print(f"Loading DBC: {dbc_path}")
        self.db = cantools.database.load_file(dbc_path)
        self.frames:       List[can.Message] = []
        self.signal_stats: Dict[str, SignalStats] = {}

    def load_log(self, log_path: str):
        """Load a .blf or .asc file."""
        path = Path(log_path)
        print(f"Loading log: {path} ({path.stat().st_size / 1024:.1f} KB)")

        with can.LogReader(log_path) as reader:
            self.frames = list(reader)

        print(f"Loaded {len(self.frames)} frames")

    def analyse(self, message_ids: Optional[List[int]] = None):
        """Decode frames and build per-signal statistics."""
        last_ts: Dict[int, float] = {}

        for frame in self.frames:
            msg_id = frame.arbitration_id

            # Filter by requested IDs if specified
            if message_ids and msg_id not in message_ids:
                continue

            # Try to decode using DBC
            try:
                dbc_msg = self.db.get_message_by_frame_id(msg_id)
            except KeyError:
                continue  # Unknown message — skip

            try:
                decoded = dbc_msg.decode(frame.data)
            except Exception as e:
                print(f"  [WARN] Decode error for 0x{msg_id:03X}: {e}")
                continue

            # Compute cycle time
            ts_sec = frame.timestamp
            if msg_id in last_ts:
                cycle_ms = (ts_sec - last_ts[msg_id]) * 1000.0
            else:
                cycle_ms = None
            last_ts[msg_id] = ts_sec

            # Store per-signal
            for sig_name, value in decoded.items():
                key = f"0x{msg_id:03X}_{sig_name}"
                if key not in self.signal_stats:
                    self.signal_stats[key] = SignalStats(
                        signal_name=sig_name,
                        message_id=msg_id
                    )
                s = self.signal_stats[key]
                s.values.append(float(value))
                s.timestamps.append(ts_sec)
                if cycle_ms is not None:
                    s.cycle_times_ms.append(cycle_ms)

    def check_timing_violations(self, expected_cycles_ms: Dict[int, float]):
        """
        Report messages whose cycle time deviates beyond tolerance.

        Args:
            expected_cycles_ms: {message_id: expected_cycle_time_ms}

        Returns:
            List of violation strings
        """
        violations = []
        for msg_id, expected_ms in expected_cycles_ms.items():
            tolerance = expected_ms * self.TIMING_TOLERANCE_PCT
            lo = expected_ms - tolerance
            hi = expected_ms + tolerance

            for key, stats in self.signal_stats.items():
                if stats.message_id != msg_id:
                    continue
                if not stats.cycle_times_ms:
                    continue

                bad = [c for c in stats.cycle_times_ms if c < lo or c > hi]
                if bad:
                    pct_bad = len(bad) / len(stats.cycle_times_ms) * 100
                    violations.append(
                        f"  0x{msg_id:03X} {stats.signal_name}: "
                        f"{len(bad)}/{len(stats.cycle_times_ms)} cycles "
                        f"out of [{lo:.1f}, {hi:.1f}] ms "
                        f"(worst: min={min(bad):.2f}ms max={max(bad):.2f}ms "
                        f"→ {pct_bad:.1f}% violation rate)"
                    )
                break  # One report per message
        return violations

    def check_stuck_signal(self, threshold_count: int = 100) -> List[str]:
        """Detect signals that have the same value for N consecutive samples."""
        stuck = []
        for key, stats in self.signal_stats.items():
            if len(stats.values) < threshold_count:
                continue
            if all(v == stats.values[0] for v in stats.values[-threshold_count:]):
                stuck.append(
                    f"  {key}: stuck at {stats.values[-1]:.4f} "
                    f"for last {threshold_count} samples"
                )
        return stuck

    def print_report(self):
        """Print a complete signal analysis report."""
        print("\n" + "="*60)
        print("  CAN LOG ANALYSIS REPORT")
        print("="*60)
        print(f"  Signals decoded: {len(self.signal_stats)}")
        print()

        for key, s in sorted(self.signal_stats.items()):
            print(f"  Signal: {s.signal_name}  (0x{s.message_id:03X})")
            print(f"    Samples:    {len(s.values)}")
            print(f"    Value:      min={s.min_value:.3f}  "
                  f"max={s.max_value:.3f}  "
                  f"mean={s.mean_value:.3f}")
            if s.cycle_times_ms:
                print(f"    Cycle (ms): min={s.min_cycle_ms:.2f}  "
                      f"max={s.max_cycle_ms:.2f}  "
                      f"mean={s.mean_cycle_ms:.2f}")
            print()

    def plot_signal(self, signal_name_fragment: str):
        """Plot signal value over time."""
        matched = [(k, s) for k, s in self.signal_stats.items()
                   if signal_name_fragment.lower() in s.signal_name.lower()]
        if not matched:
            print(f"Signal '{signal_name_fragment}' not found in log")
            return

        fig, axes = plt.subplots(len(matched), 1,
                                 figsize=(14, 4 * len(matched)))
        if len(matched) == 1:
            axes = [axes]

        for ax, (key, s) in zip(axes, matched):
            ax.plot(s.timestamps, s.values, linewidth=0.8)
            ax.set_title(f"{s.signal_name}  (0x{s.message_id:03X})")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.4)

        plt.tight_layout()
        plt.savefig(f"signal_plot_{signal_name_fragment}.png", dpi=150)
        plt.show()
        print(f"Plot saved: signal_plot_{signal_name_fragment}.png")


# ── Usage Example ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    analyser = CANLogAnalyser("adas_vehicle.dbc")
    analyser.load_log("test_AEB_run_001.blf")
    analyser.analyse(message_ids=[0x100, 0x200, 0x201, 0x300, 0x301])

    print("\n── Timing Violations ──")
    violations = analyser.check_timing_violations({
        0x100: 10.0,   # VehicleSpeed: 10ms
        0x200: 20.0,   # RadarObject:  20ms
        0x300: 20.0,   # ACC_Status:   20ms
    })
    if violations:
        for v in violations:
            print(v)
    else:
        print("  No timing violations detected")

    print("\n── Stuck Signals ──")
    stuck = analyser.check_stuck_signal(threshold_count=50)
    if stuck:
        for s in stuck:
            print(s)
    else:
        print("  No stuck signals detected")

    analyser.print_report()
    analyser.plot_signal("distance_m")

"""
Expected console output (example):
Loading DBC: adas_vehicle.dbc
Loading log: test_AEB_run_001.blf (2847.3 KB)
Loaded 142319 frames

── Timing Violations ──
  0x200 distance_m: 12/6200 cycles out of [18.0, 22.0] ms (worst: min=8.31ms max=31.44ms → 0.2% violation rate)

── Stuck Signals ──
  No stuck signals detected

══════════════════════════════════════════════
  CAN LOG ANALYSIS REPORT
══════════════════════════════════════════════
  Signals decoded: 34

  Signal: speed_kph  (0x100)
    Samples:    61000
    Value:      min=0.000  max=98.430  mean=52.340
    Cycle (ms): min=9.71   max=10.38   mean=10.00

  Signal: distance_m  (0x200)
    Samples:    31000
    Value:      min=2.150  max=149.980  mean=67.430
    Cycle (ms): min=8.31   max=31.44    mean=20.01
"""
```

### 10.2 UDS ECU Response Validator

```python
"""
uds_validator.py
----------------
Sends UDS requests to an ECU via CANoe COM API or python-can,
validates responses, and reports pass/fail results.

Supports:
  - DiagnosticSessionControl
  - SecurityAccess with HMAC-SHA256 key computation
  - ReadDataByIdentifier with value range validation
  - ReadDTCInformation with DTC whitelist validation

Dependencies: python-can, pycryptodome
Install:      pip install python-can pycryptodome
"""

import can
import time
import struct
import hmac
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ── UDS Constants ──────────────────────────────────────────────────────────────
UDS_REQ_ID   = 0x744   # Tester → ECU
UDS_RESP_ID  = 0x74C   # ECU → Tester
UDS_TIMEOUT  = 2.0     # seconds (P2 client timeout)
TP_PADDING   = 0xCC    # ISO 15765-2 padding byte


# ── NRC definitions ────────────────────────────────────────────────────────────
NRC_MAP = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLength",
    0x22: "conditionsNotCorrect",
    0x24: "requestSequenceError",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x35: "invalidKey",
    0x36: "exceededNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired",
    0x70: "uploadDownloadNotAccepted",
    0x78: "requestCorrectlyReceivedResponsePending",
}


@dataclass
class TestResult:
    test_name: str
    passed:    bool
    detail:    str
    nrc:       Optional[int] = None

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        nrc_str = f" [NRC=0x{self.nrc:02X} {NRC_MAP.get(self.nrc, '?')}]" if self.nrc else ""
        return f"  [{status}] {self.test_name}: {self.detail}{nrc_str}"


class UDSValidator:
    """
    High-level UDS validation helper over python-can.

    Usage:
        with can.Bus(interface='vector', channel=0, bitrate=500000) as bus:
            v = UDSValidator(bus)
            v.open_extended_session()
            v.security_access_unlock()
            v.validate_rdbi(0xF101, "VehicleSpeed", min_val=0.0, max_val=330.0)
            v.validate_dtc_memory(allowed_dtcs=[])
            v.print_results()
    """

    # Security algorithm — replace with project-specific key in production
    SECURITY_SECRET_KEY = bytes.fromhex("0102030405060708090A0B0C0D0E0F10")

    def __init__(self, bus: can.Bus):
        self.bus     = bus
        self.results: List[TestResult] = []
        self.reader  = can.BufferedReader()
        notifier     = can.Notifier(bus, [self.reader])

    def _send(self, payload: bytes) -> None:
        """Send a UDS request using ISO 15765-2 single-frame or multi-frame."""
        data = bytearray(8)
        if len(payload) <= 7:
            # Single frame
            data[0] = len(payload)
            data[1:1+len(payload)] = payload
            # Pad with 0xCC
            for i in range(1+len(payload), 8):
                data[i] = TP_PADDING
        else:
            # First frame (simplified — full TP implementation needed for > 7 bytes)
            data[0] = 0x10 | ((len(payload) >> 8) & 0x0F)
            data[1] = len(payload) & 0xFF
            data[2:8] = payload[:6]
        msg = can.Message(arbitration_id=UDS_REQ_ID, data=data, is_extended_id=False)
        self.bus.send(msg)

    def _receive(self) -> Optional[bytes]:
        """Wait for a UDS response with timeout."""
        deadline = time.time() + UDS_TIMEOUT
        accumulated = bytearray()

        while time.time() < deadline:
            msg = self.reader.get_message(timeout=0.1)
            if msg is None:
                continue
            if msg.arbitration_id != UDS_RESP_ID:
                continue

            pci = msg.data[0]
            pci_type = (pci >> 4) & 0x0F

            if pci_type == 0x0:   # Single frame
                length = pci & 0x0F
                return bytes(msg.data[1:1+length])

            elif pci_type == 0x1:  # First frame
                length = ((pci & 0x0F) << 8) | msg.data[1]
                accumulated.extend(msg.data[2:])
                # Send flow control
                fc = can.Message(
                    arbitration_id=UDS_REQ_ID,
                    data=[0x30, 0x00, 0x00, TP_PADDING, TP_PADDING,
                          TP_PADDING, TP_PADDING, TP_PADDING],
                    is_extended_id=False
                )
                self.bus.send(fc)

            elif pci_type == 0x2:  # Consecutive frame
                accumulated.extend(msg.data[1:])
                if len(accumulated) >= length:
                    return bytes(accumulated[:length])

        return None  # Timeout

    def _is_positive_response(self, service_id: int, response: bytes) -> bool:
        return len(response) > 0 and response[0] == service_id + 0x40

    def _get_nrc(self, response: bytes) -> Optional[int]:
        if len(response) >= 3 and response[0] == 0x7F:
            return response[2]
        return None

    # ── UDS Services ──────────────────────────────────────────────────────────

    def open_extended_session(self) -> TestResult:
        """Open Extended Diagnostic Session (0x10 03)."""
        self._send(bytes([0x10, 0x03]))
        resp = self._receive()

        if resp and self._is_positive_response(0x10, resp):
            result = TestResult("ExtendedDiagnosticSession", True,
                                f"Session opened, P2={resp[3]*0.25:.0f}ms")
        else:
            nrc = self._get_nrc(resp) if resp else None
            result = TestResult("ExtendedDiagnosticSession", False,
                                "No positive response", nrc=nrc)

        self.results.append(result)
        print(result)
        return result

    def security_access_unlock(self) -> TestResult:
        """Perform SecurityAccess with HMAC-SHA256 key computation."""
        # Step 1: Request seed
        self._send(bytes([0x27, 0x01]))
        resp = self._receive()

        if not resp or not self._is_positive_response(0x27, resp):
            nrc = self._get_nrc(resp) if resp else None
            r = TestResult("SecurityAccess_RequestSeed", False,
                           "Failed to get seed", nrc=nrc)
            self.results.append(r)
            print(r)
            return r

        seed = resp[2:6]  # 4-byte seed
        print(f"    Seed received: {seed.hex().upper()}")

        # Step 2: Compute key using HMAC-SHA256 (truncated to 4 bytes)
        key_full = hmac.new(
            self.SECURITY_SECRET_KEY,
            seed,
            hashlib.sha256
        ).digest()
        key = key_full[:4]
        print(f"    Computed key:  {key.hex().upper()}")

        # Step 3: Send key
        self._send(bytes([0x27, 0x02]) + key)
        resp = self._receive()

        if resp and self._is_positive_response(0x27, resp):
            result = TestResult("SecurityAccess_Unlock", True,
                                f"Access granted (key={key.hex().upper()})")
        else:
            nrc = self._get_nrc(resp) if resp else None
            result = TestResult("SecurityAccess_Unlock", False,
                                "Key rejected", nrc=nrc)

        self.results.append(result)
        print(result)
        return result

    def validate_rdbi(self, did: int, description: str,
                       min_val: float, max_val: float,
                       factor: float = 1.0, offset: float = 0.0) -> TestResult:
        """
        Read a DID, decode the value, and range-check it.

        Args:
            did:         Data Identifier (e.g., 0xF101)
            description: Human-readable signal name
            min_val:     Minimum acceptable physical value
            max_val:     Maximum acceptable physical value
            factor:      Scale factor (raw → physical)
            offset:      Offset (raw → physical = raw*factor + offset)
        """
        did_bytes = struct.pack(">H", did)
        self._send(bytes([0x22]) + did_bytes)
        resp = self._receive()

        if not resp or not self._is_positive_response(0x22, resp):
            nrc = self._get_nrc(resp) if resp else None
            r = TestResult(f"RDBI_0x{did:04X}_{description}", False,
                           "No positive response", nrc=nrc)
            self.results.append(r)
            print(r)
            return r

        # Decode raw value (2 bytes, big-endian assumed)
        raw = struct.unpack(">H", resp[3:5])[0]
        physical = raw * factor + offset
        passed   = min_val <= physical <= max_val

        r = TestResult(
            f"RDBI_0x{did:04X}_{description}",
            passed,
            f"raw=0x{raw:04X} physical={physical:.3f} "
            f"range=[{min_val},{max_val}]"
        )
        self.results.append(r)
        print(r)
        return r

    def validate_dtc_memory(self, allowed_dtcs: List[int]) -> TestResult:
        """
        Read confirmed DTCs (0x19 02 08) and verify against an allowed list.
        An empty allowed_dtcs means NO DTC should be active.
        """
        self._send(bytes([0x19, 0x02, 0x08]))  # 0x08 = confirmed DTC mask
        resp = self._receive()

        if not resp or not self._is_positive_response(0x19, resp):
            nrc = self._get_nrc(resp) if resp else None
            r = TestResult("ReadDTCMemory", False, "No response", nrc=nrc)
            self.results.append(r)
            print(r)
            return r

        # Parse DTC list (4 bytes per DTC: 3-byte ID + 1-byte status)
        dtcs_found = []
        i = 3
        while i + 3 < len(resp):
            dtc_id = (resp[i] << 16) | (resp[i+1] << 8) | resp[i+2]
            status  = resp[i+3]
            dtcs_found.append((dtc_id, status))
            i += 4

        unexpected = [(did, st) for did, st in dtcs_found
                      if did not in allowed_dtcs]

        if not unexpected:
            r = TestResult("ReadDTCMemory", True,
                           f"{len(dtcs_found)} DTCs, all expected")
        else:
            dtc_list = ", ".join(
                f"0x{d:06X}(status=0x{s:02X})" for d, s in unexpected
            )
            r = TestResult("ReadDTCMemory", False,
                           f"Unexpected DTCs: {dtc_list}")

        self.results.append(r)
        print(r)
        return r

    def print_results(self):
        """Print final test summary."""
        passed = sum(1 for r in self.results if r.passed)
        total  = len(self.results)
        print()
        print("="*60)
        print(f"  UDS VALIDATION SUMMARY: {passed}/{total} PASSED")
        print("="*60)
        for r in self.results:
            print(r)
        print()
        return passed == total


# ── Usage example ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # CANoe Vector XL interface — change channel/bitrate for your bench
    bus = can.interface.Bus(
        bustype='vector',
        channel=0,
        bitrate=500000,
        app_name="UDS_Validator"
    )

    try:
        v = UDSValidator(bus)
        print("Starting UDS Validation Sequence")
        print("-"*40)

        v.open_extended_session()
        time.sleep(0.1)

        v.security_access_unlock()
        time.sleep(0.1)

        # Validate live signals
        v.validate_rdbi(0xF101, "VehicleSpeed",
                        min_val=0.0, max_val=330.0,
                        factor=0.01, offset=0.0)
        v.validate_rdbi(0xF110, "EngineSpeed",
                        min_val=0.0, max_val=8000.0,
                        factor=0.125, offset=0.0)
        v.validate_rdbi(0xF191, "SoftwareVersion",
                        min_val=0, max_val=65535, factor=1.0)

        # DTC memory check (expect zero active DTCs after clean start)
        v.validate_dtc_memory(allowed_dtcs=[])

        passed = v.print_results()
        exit(0 if passed else 1)

    finally:
        bus.shutdown()

"""
Expected Output:
Starting UDS Validation Sequence
----------------------------------------
    Seed received: A3F172C9
    Computed key:  5D2B44E1
  [PASS] ExtendedDiagnosticSession: Session opened, P2=250ms
  [PASS] SecurityAccess_Unlock: Access granted (key=5D2B44E1)
  [PASS] RDBI_0xF101_VehicleSpeed: raw=0x1388 physical=50.000 range=[0.0,330.0]
  [PASS] RDBI_0xF110_EngineSpeed: raw=0x07D0 physical=250.000 range=[0.0,8000.0]
  [FAIL] ReadDTCMemory: Unexpected DTCs: 0xC19801(status=0x08)

════════════════════════════════════════
  UDS VALIDATION SUMMARY: 4/5 PASSED
════════════════════════════════════════
"""
```

### 10.3 SOME/IP Log Analyser

```python
"""
someip_analyser.py
------------------
Parses Wireshark PCAP files and validates SOME/IP service discovery events,
subscription states, and event payload timing.

Dependencies: scapy, pyshark
Install:      pip install scapy pyshark
"""

import pyshark
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict
import time


SOMEIP_SD_PORT   = 30490
SOMEIP_SD_SVC_ID = 0xFFFF


@dataclass
class ServiceEvent:
    service_id:    int
    instance_id:   int
    event_type:    str    # "OfferService", "FindService", "StopOffer", "Subscribe", "SubscribeAck"
    timestamp:     float
    source_ip:     str


@dataclass
class ServiceState:
    service_id:   int
    instance_id:  int
    offers:       List[float] = field(default_factory=list)
    finds:        List[float] = field(default_factory=list)
    subscribes:   List[float] = field(default_factory=list)
    ack_times:    List[float] = field(default_factory=list)  # subscribe → ack latency

    def is_discovered(self) -> bool:
        """True if at least one OfferService seen."""
        return len(self.offers) > 0

    def subscription_latency_ms(self) -> Optional[float]:
        """Latest subscribe-to-ack latency in ms."""
        if self.subscribes and self.ack_times:
            return (self.ack_times[-1] - self.subscribes[-1]) * 1000.0
        return None


class SOMEIPAnalyser:
    """
    Analyses SOME/IP Service Discovery in a Wireshark PCAP file.

    Usage:
        a = SOMEIPAnalyser()
        a.load_pcap("bench_capture.pcapng")
        a.analyse()
        a.check_service_discovered(0x0501, 0x0001, max_delay_ms=5000)
        a.print_report()
    """

    def __init__(self):
        self.events: List[ServiceEvent] = []
        self.states: Dict[tuple, ServiceState] = {}

    def load_pcap(self, pcap_path: str):
        """Load PCAP and extract SOME/IP SD events."""
        print(f"Loading PCAP: {pcap_path}")
        cap = pyshark.FileCapture(
            pcap_path,
            display_filter=f"someip and udp.port == {SOMEIP_SD_PORT}",
            use_json=True
        )

        count = 0
        for pkt in cap:
            try:
                self._parse_packet(pkt)
                count += 1
            except Exception:
                continue

        cap.close()
        print(f"Parsed {count} SOME/IP SD packets, "
              f"{len(self.events)} service events")

    def _parse_packet(self, pkt):
        """Extract SD entry from a SOME/IP SD packet."""
        ts        = float(pkt.sniff_timestamp)
        src_ip    = pkt.ip.src

        # pyshark SOME/IP SD layer field access
        if not hasattr(pkt, 'someip'):
            return

        layer = pkt.someip
        # SD entry type: 0x00=FindService, 0x01=OfferService, 0x81=StopOfferService
        # 0x06=Subscribe, 0x07=SubscribeAck (event group entries)

        try:
            entry_type = int(layer.sd_entry_type, 16)
            svc_id     = int(layer.sd_entry_srv_id, 16)
            inst_id    = int(layer.sd_entry_inst_id, 16)
        except AttributeError:
            return

        type_map = {
            0x00: "FindService",
            0x01: "OfferService",
            0x81: "StopOffer",
            0x06: "Subscribe",
            0x07: "SubscribeAck"
        }
        evt_type = type_map.get(entry_type, f"Unknown_0x{entry_type:02X}")

        event = ServiceEvent(service_id=svc_id, instance_id=inst_id,
                             event_type=evt_type, timestamp=ts, source_ip=src_ip)
        self.events.append(event)

        key = (svc_id, inst_id)
        if key not in self.states:
            self.states[key] = ServiceState(service_id=svc_id, instance_id=inst_id)
        s = self.states[key]

        if evt_type == "OfferService":      s.offers.append(ts)
        elif evt_type == "FindService":     s.finds.append(ts)
        elif evt_type == "Subscribe":       s.subscribes.append(ts)
        elif evt_type == "SubscribeAck":    s.ack_times.append(ts)

    def check_service_discovered(self, service_id: int, instance_id: int,
                                   max_delay_ms: float = 5000.0) -> bool:
        """
        Verify a specific service was offered within max_delay_ms of first FindService.
        """
        key   = (service_id, instance_id)
        state = self.states.get(key)

        if not state:
            print(f"  [FAIL] Service 0x{service_id:04X}/0x{instance_id:04X}: "
                  f"Not seen in capture")
            return False

        if not state.is_discovered():
            print(f"  [FAIL] Service 0x{service_id:04X}/0x{instance_id:04X}: "
                  f"FindService sent {len(state.finds)}x but no OfferService received")
            return False

        if state.finds:
            delay_ms = (state.offers[0] - state.finds[0]) * 1000.0
            if delay_ms > max_delay_ms:
                print(f"  [FAIL] Service 0x{service_id:04X}/0x{instance_id:04X}: "
                      f"Discovered but delay={delay_ms:.0f}ms > {max_delay_ms:.0f}ms")
                return False
            print(f"  [PASS] Service 0x{service_id:04X}/0x{instance_id:04X}: "
                  f"Discovered in {delay_ms:.0f}ms")
        else:
            print(f"  [PASS] Service 0x{service_id:04X}/0x{instance_id:04X}: "
                  f"OfferService seen (no FindService in capture — server-initiated)")

        lat = state.subscription_latency_ms()
        if lat is not None:
            print(f"         Subscribe→Ack latency: {lat:.1f}ms")

        return True

    def print_report(self):
        """Print all discovered services."""
        print()
        print("="*60)
        print("  SOME/IP SERVICE DISCOVERY REPORT")
        print("="*60)
        for (svc, inst), s in sorted(self.states.items()):
            print(f"  Service 0x{svc:04X} / Instance 0x{inst:04X}")
            print(f"    OfferService:  {len(s.offers)} times")
            print(f"    FindService:   {len(s.finds)} times")
            print(f"    Subscribe:     {len(s.subscribes)} times")
            print(f"    SubscribeAck:  {len(s.ack_times)} times")
            lat = s.subscription_latency_ms()
            if lat:
                print(f"    Sub→Ack lat:   {lat:.1f} ms")
            print()


if __name__ == "__main__":
    a = SOMEIPAnalyser()
    a.load_pcap("bench_someip_capture.pcapng")
    a.analyse()

    # Check the Fusion Object List service
    a.check_service_discovered(0x0501, 0x0001, max_delay_ms=3000.0)
    # Check the Ego Motion service
    a.check_service_discovered(0x0502, 0x0001, max_delay_ms=3000.0)

    a.print_report()
```

---

## 11. Best Practices and Checklist

### 11.1 Debugging Checklist

#### Pre-Debug Setup
```
□ CANoe database loaded and decoding correctly (verify 2–3 known signals)
□ DBC / ARXML version matches ECU software version (check sw version DID)
□ HIL model version matches test specification
□ Logging started BEFORE test execution (do not miss pre-conditions)
□ System date/time synchronised (critical for multi-ECU correlation)
□ ECU wakeup condition verified (ignition, network management)
□ Termination resistors on CAN bus segments verified (60Ω each end)
□ Power supply voltage confirmed (13.5V nominal for 12V system)
```

#### During Investigation
```
□ Capture raw + decoded (never delete raw — decoding bugs exist in tools too)
□ Timestamp all observations accurately (elapsed time, not wall clock)
□ Record what did NOT change — eliminating possibilities is as valuable as finding them
□ Reproduce before fixing — minimum 3 consistent reproductions
□ One change at a time — changing multiple things simultaneously destroys RCA validity
□ Read DTCs before and after every test (not just at failure — track DTC changes)
□ Photograph / screenshot the bench configuration (cable routing, switch config)
□ Write down the hypothesis before testing it — prevents confirmation bias
```

#### Root Cause Validation
```
□ Fix applied and tested on the same bench/ECU that showed the failure
□ Regression run to confirm no regression introduced (minimum smoke test)
□ JIRA/DOORS ticket updated with evidence and linked to fix
□ Peer review of fix completed
□ Re-test log retained and referenced in RCA closure report
```

### 11.2 Most Common Engineer Mistakes

| Mistake | Consequence | Corrective Action |
|---|---|---|
| Changing multiple variables simultaneously | Cannot identify which change fixed the issue → RCA invalid | One change at a time + baseline snapshot |
| Trusting the stimulus without verifying it | Spending 4h debugging the ECU when the problem was the HIL model | Always verify inputs first — measurement before assumption |
| Not reading DTCs immediately after failure | Losing fault context that would have pointed directly to root cause | DTCs are your first clue — always read them first |
| Treating intermittent bugs as "flaky" | Problem is found in the field instead of the lab | Intermittent = reproduce rate < 100% — instrument, capture, characterise |
| Ignoring NRC 0x78 (response pending) | Assuming ECU is not responding when it's just slow | Implement P2* (extended timeout) in UDS tester |
| Fixing symptoms not root cause | Bug returns in a different form later | 5-Why every defect regardless of schedule pressure |
| Signal name confusion (factor/offset) | Wrong physical value used in analysis | Always verify factor/offset from DBC for every signal |
| Forking the SW base for debugging | Production build looks different from debug build | Use software variants / conditional compilation — never fork main |
| No version control for test scripts | Cannot reproduce results from 6 months ago | CAPL and Python scripts in Git, same standards as production code |
| Not archiving log files | Cannot perform retrospective analysis | Mandatory: store .blf + .asc + dSPACE logs for all gate-level tests |

### 11.3 Reducing Debugging Time in Projects

#### Invest Up-Front in Observability
The most expensive debugging time is spent recovering information that could have been trivially available had it been logged from the start:
- Instrument every state machine state change with a DLT/UDS event
- Map all critical internal variables to XCP measurement — define the A2L file during software design, not during debug
- Assign DTC codes to every monitored function at design time, not after the first failure

#### Automate Regression Analysis
Manual log inspection at 1000 frames/page is not scalable:
- All regression logs should be processed by a Python script that checks timing, value range, DTC content, and state transitions automatically
- A regression run that passes should take the engineer zero minutes to review — automation does it

#### Maintain a Failure Library
Every confirmed root cause should be recorded in a searchable database:
- Symptom → Root cause → Fix → How to avoid
- Before starting any new investigation, search the library — >40% of bugs are re-occurrences of patterns already seen

#### Use Traceability During Design
If every requirement has a test ID, every test ID has a CAPL/Python script, and every script validates a measurable signal, the debugging path when a test fails is immediate:
- Test failed → look at spec → look at signal → look at log → look at code

This traceability shortens the mean-time-to-root-cause from days to hours.

---

## Document Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-04-24 | Senior ADAS Validation Engineer | Initial release |

---

*This document is prepared based on real-world experience in ADAS ECU validation at Tier-1 level. All ECU addresses, DTC codes, and scenario details are representative examples suitable for training and interview preparation. Proprietary algorithms and customer-specific data have been replaced with generic equivalents.*
