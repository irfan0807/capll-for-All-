# CAN Bus & ECU Troubleshooting Guide

## 1. Systematic Diagnosis Approach

```
Symptom Reported
       │
       ▼
   1. Reproduce the issue in test environment
       │
       ▼
   2. Capture bus traffic (CANalyzer / CANoe / python-can)
       │
       ▼
   3. Identify the layer: Physical? Data Link? Application (UDS)?
       │
       ▼
   4. Isolate the failing node
       │
       ▼
   5. Root Cause Analysis (5-Why / Fishbone)
       │
       ▼
   6. Fix → Regression Test → Close
```

---

## 2. Physical Layer Issues

### Problem: No CAN communication at all

#### Checklist
| Check | Tool | Expected |
|-------|------|---------|
| CAN_H to GND | Multimeter | 2.5V (recessive) |
| CAN_L to GND | Multimeter | 2.5V (recessive) |
| CAN_H – CAN_L differential | Oscilloscope | ~2V (dominant) ~0V (recessive) |
| Termination resistance | Multimeter (bus off) | 60Ω between CAN_H and CAN_L |
| Bus short circuit | Multimeter | No short CAN_H↔CAN_L |

#### Root Causes
```
No Communication
├── Physical
│   ├── Missing termination (should be 120Ω at each end → 60Ω total)
│   ├── Wire harness break (CAN_H or CAN_L open circuit)
│   ├── Short CAN_H to CAN_L → dominant stuck
│   ├── Short CAN_L to GND → differential stuck low
│   ├── Short CAN_H to Vbat → differential stuck high
│   └── Faulty CAN transceiver (TJA1050, MCP2551, etc.)
│
└── Configuration
    ├── Baud rate mismatch (e.g., 250 vs 500 kbps)
    ├── CAN controller not initialized / clock mismatch
    └── Node in Bus-Off state (recover via ECU reset)
```

#### Oscilloscope Waveform – Healthy CAN
```
CAN_H: ─────╮    ╭─────╮    ╭──────
             ╰────╯     ╰────╯
CAN_L: ─────╯    ╰─────╯    ╰──────
  3.5V│      │         │
  2.5V│──────┤─────────┤──────
  1.5V│      │         │
      Dominant   Recessive
```

---

## 3. Data Link Layer Issues

### Problem: Intermittent message loss / high error count

```
Diagnostics:
  CANalyzer → Statistics → Error Frames tab
  Expected: <0.1% error frame rate

Common Causes:
  ┌─────────────────────────────────────────────────────┐
  │  Error Frame  │ Root Cause                          │
  ├───────────────┼─────────────────────────────────────┤
  │ Stuff Error   │ EMI / signal integrity issue         │
  │ CRC Error     │ Wire routing near ignition coils     │
  │ Form Error    │ Ground loop / common-mode noise      │
  │ ACK Error     │ No receiver / transceiver fault      │
  └───────────────┴─────────────────────────────────────┘
```

#### Signal Integrity Checklist
- [ ] Twisted pair wire (30 twists per meter minimum)
- [ ] Shield connected at one end only
- [ ] CAN stub length < 30cm
- [ ] Bus length vs baudrate compliance:
  ```
  1 Mbit/s  → max 25m bus
  500 kbit/s → max 100m bus
  250 kbit/s → max 250m bus
  125 kbit/s → max 500m bus
  ```

### Problem: Bus Off State

```
Diagnosis:
  CANalyzer → Node → Error State = Bus Off
  OR: ECU logs DTC for CAN Bus Off (e.g., P0590)

Recovery:
  Option 1: ECU Reset (UDS 0x11 01 – Hard Reset)
  Option 2: Power cycle (ignition off/on)
  Option 3: Software: wait 128 × 11 recessive bits (auto-recovery)

Root Cause:
  - Defective ECU transmitting garbage continuously
  - Wrong baud rate configuration
  - Short circuit during transmission
  - Flash programming interrupted → corrupted CAN driver config
```

---

## 4. Application Layer – UDS Issues

### Problem: ECU responds with 0x7F (Negative Response Code)

```
Decode NRC:
  Response bytes: 7F [SID] [NRC]
  
  0x7F 0x22 0x31 → ReadDataByIdentifier, DID out of range
  0x7F 0x27 0x35 → SecurityAccess, Invalid Key
  0x7F 0x10 0x7F → DiagSessionControl, not supported in session
  0x7F 0x3E 0x78 → TesterPresent, response pending (ECU still busy)

NRC Troubleshooting Table:
  0x10 generalReject           → Check SID support, ECU-specific limitation
  0x11 serviceNotSupported     → Service not implemented in this ECU variant
  0x12 subFunctionNotSupported → Check sub-function byte value
  0x13 incorrectMsgLength      → Count request bytes carefully
  0x22 conditionsNotCorrect    → ECU not in correct state (e.g., engine running)
  0x24 requestSequenceError    → Multi-step service out of order
  0x31 requestOutOfRange       → DID / memory address not valid
  0x33 securityAccessDenied    → Need SecurityAccess first
  0x35 invalidKey              → Wrong key calculation / algorithm
  0x36 exceededAttempts        → Wait 10 seconds (lockout timer)
  0x7E subfunctionNotInSession → Need extended or programming session first
  0x7F serviceNotInSession     → Switch to correct session before calling
```

### Problem: Security Access keeps failing (NRC 0x35 / 0x36)

```
Debug Steps:
  1. Verify seed received correctly (print raw bytes)
  2. Verify key calculation algorithm matches ECU:
     - Common: XOR, shifted XOR, CMAC-AES, vendor-specific
     - Ask Tier-1 supplier for algorithm or test EKM
  3. Check for seed=0 (already unlocked) → key should be 0
  4. Check lockout state (NRC 0x37) – wait P4 timer (10s default)
  5. Check if session is correct (Extended/Programming required)
  
Key Algorithm Debugging:
  # Python helper to brute-check common algorithms
  seed = 0xA3F211C4
  
  attempt1 = seed ^ 0x5A5A5A5A          # Simple XOR
  attempt2 = (~seed) & 0xFFFFFFFF        # Bitwise NOT
  attempt3 = (seed >> 4) | (seed << 28) # Rotate right 4
  attempt4 = seed + 0x1234              # Add constant
  
  # Send each and see if ECU accepts
```

### Problem: UDS Session Times Out (ECU returns to Default)

```
Cause: No TesterPresent (0x3E) sent during session
       ECU P3 timeout = 5000ms (typical)

Fix: Send 0x3E 80 (suppress positive response) every 2s
     # CAPL:
     setTimer(keepAliveTimer, 2000);
     on timer keepAliveTimer {
       byte req[2] = {0x3E, 0x80};  // 0x80 = suppress response
       UDS_SendSingleFrame(TESTER_PHYS_ID, req, 2);
       setTimer(keepAliveTimer, 2000);
     }
```

### Problem: ISO-TP Multi-Frame Response Truncated

```
Symptoms: Only first 7 bytes arrive, rest missing

Cause: Tester not sending Flow Control frame
       OR: Flow Control BS (Block Size) = non-zero without re-FC

Debug:
  Capture raw CAN:
  ECU → 0x7E8: 10 xx FF ... (First Frame, length=0xXXFF)
  Tester needs to respond:
  0x7E0: 30 00 00    (FC: ContinueToSend, BS=0, STmin=0ms)
  
CAPL fix:
  on message 0x7E8 {
    if ((this.byte(0) & 0xF0) == 0x10) {  // First Frame detected
      // Send Flow Control
      byte fc[3] = {0x30, 0x00, 0x00};
      UDS_SendSingleFrame(TESTER_PHYS_ID, fc, 3);
    }
  }
```

---

## 5. ECU-Specific Diagnostics

### Problem: ECU DTC Keeps Returning after Clear

```
Root Cause Analysis:
  1. Fault condition still present (sensor/wiring)
  2. DTC confirmation threshold not meeting healing criteria
  3. Two-trip or single-trip DTC setting
  4. Monitoring not reaching completed state (drive cycle incomplete)

Steps:
  1. Read DTC Extended Data (0x19 06) → check occurrence counter & healing counter
  2. Check if monitoring is running: readDTCByStatusMask(0x40) = not completed this cycle
  3. Perform complete drive cycle including:
     - Cold start
     - Idle for 2 minutes
     - Various speed/load points
     - Hot shutdown
  4. Verify sensor in-range: ReadDID for sensor value, check against spec
```

### Problem: ECU Not Responding to UDS Requests

```
Diagnostic Tree:
  
  Send 0x7DF 02 10 01 (default session, functional)
       │
       ├── No response on 0x7E8
       │       │
       │       ├── Check CAN physical layer (section 2)
       │       ├── Check baud rate
       │       └── Check ECU power supply (min 9V)
       │
       └── Response: 0x7E8 06 50 01 00 19 01 F4
               ECU is alive! Continue diagnosis.
  
  Common dead ECU causes:
  - Supply voltage < 9V (brown-out)
  - Watchdog reset loop (check DTC P0601 internal fault)
  - Flash corrupted (unlocked ECU damaged during power interruption)
  - CAN transceiver in fault mode (TXD dominant stuck)
```

---

## 6. CANalyzer / Python-CAN Quick Reference

### CANalyzer Key Windows
| Window | Purpose |
|--------|---------|
| Trace | Raw frame capture with timestamps |
| Statistics | Error rates, bus load, frame counts |
| State Tracker | ECU state (Error Active/Passive/Bus Off) |
| Diagnostics | UDS request/response wizard |
| Symbol Explorer | DBC signal decode |

### Python-CAN Quick Diagnostic Script

```python
import can
import time

BUS = can.interface.Bus(bustype='socketcan', channel='vcan0', bitrate=500000)

def send_uds(arbitration_id: int, data: bytes) -> None:
    """Send ISO-TP Single Frame UDS request."""
    frame = bytes([len(data)]) + data  # SF: length byte + payload
    msg = can.Message(arbitration_id=arbitration_id,
                      data=frame, is_extended_id=False)
    BUS.send(msg)
    print(f"TX: CAN_ID=0x{arbitration_id:03X} Data={frame.hex(' ').upper()}")

def recv_uds(timeout: float = 0.5):
    """Wait for UDS response on 0x7E8."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = BUS.recv(timeout=0.01)
        if msg and msg.arbitration_id == 0x7E8:
            print(f"RX: {msg.data.hex(' ').upper()}")
            return msg
    print("TIMEOUT: No response")
    return None

# Example: Enter Extended Diagnostic Session
send_uds(0x7E0, bytes([0x10, 0x03]))
resp = recv_uds()

# Read VIN
time.sleep(0.1)
send_uds(0x7E0, bytes([0x22, 0xF1, 0x90]))
resp = recv_uds()
if resp:
    vin = resp.data[3:20].decode('ascii', errors='replace')
    print(f"VIN: {vin}")

BUS.shutdown()
```

---

## 7. Root Cause Analysis Template

When filing a defect report, include:

```
Title: [ECU Name] [System] – [Brief symptom]

Environment:
  - ECU SW version:
  - HW version:
  - DBC version:
  - Test tool (CANalyzer/CANoe version):
  - Baud rate:

Symptom:
  - What: [exact behavior observed]
  - When: [conditions, reproducibility %]
  - Impact: [safety impact? customer visible?]

Evidence:
  - CANalyzer trace (attach .blf file)
  - Screenshots
  - Relevant DTCs

Timeline:
  T=0ms   [preconditions]
  T=Xms   [trigger event]
  T=Yms   [failure observed]

Root Cause (5-Why):
  Why 1: [immediate cause]
  Why 2: [...]
  Why 3: [...]
  Why 4: [...]
  Why 5: [root cause]

Fix:
  - Immediate workaround:
  - Permanent fix:
  - Regression tests required:

Affected:
  - Other ECUs using same component: [Y/N, which?]
  - Field vehicles: [VIN range if known]
```
