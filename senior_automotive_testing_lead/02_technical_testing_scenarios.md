# Section 2: Technical Testing Scenarios
> **Role**: Senior Automotive Testing Team Lead | **Questions**: Q10–Q24

---

## Q10: How do you validate CAN signal integrity in a Cluster ECU using CANoe?

### Question
The Cluster ECU is not rendering the speedometer correctly. You suspect a CAN signal issue. Describe your complete CAN signal validation process using CANoe.

### Detailed Answer

**Step 1: Understand the signal specification (from DBC/SDS)**
```
Signal: VehicleSpeed
  Message ID: 0x3B4 (Ext: 0x1A3B4)
  Cycle Time: 10 ms
  Byte Order: Intel (Little Endian)
  Start Bit: 0
  Length: 16 bits
  Factor: 0.01 km/h/bit
  Offset: 0
  Range: 0 – 655.35 km/h
```

**Step 2: CANoe Setup**
1. Load the correct `.dbc` file for the relevant CAN bus (e.g., PT-CAN, Body-CAN).
2. Open **Trace Window** and filter on Message ID 0x3B4.
3. Open **Signal Display** or **Graphic Window** for `VehicleSpeed` signal.
4. Verify message is being transmitted: confirm message appears in trace at ~10 ms intervals.

**Step 3: Validate Each Signal Property**

| Check | Method | Expected | Actual |
|-------|--------|---------|--------|
| Message cycle time | Statistics window: delta time between 0x3B4 frames | 10 ms ± 1 ms | Verify |
| Signal value | Graphic window during 60 km/h test drive | Displays 60 km/h | Compare |
| Byte order | Manual decode: raw bytes match formula | As per DBC | Verify |
| Signal range | Stimulate with value at boundary: 0, 655.35 | No clamp/wrap issues | Test |
| Message timeout | Disconnect sender ECU: observe Cluster behavior after 500 ms | Cluster shows dashes | Test |
| Bus load | Statistics window: CAN bus load % | < 30% (target) | Measure |

**Step 4: CAPL Script for Automated Signal Validation**
```capl
variables {
  message 0x3B4 SpeedMsg;
  msTimer tTimeout;
  float lastSpeed;
  int msgReceived = 0;
}

on message 0x3B4 {
  float rawSpeed = (this.byte(0) + (this.byte(1) << 8)) * 0.01;
  if (rawSpeed < 0 || rawSpeed > 655.35) {
    write("ERROR: Speed signal out of range: %.2f km/h", rawSpeed);
    testStepFail("Speed range check");
  } else {
    testStepPass("Speed range check");
  }
  setTimer(tTimeout, 500); // reset timeout watchdog
  msgReceived = 1;
}

on timer tTimeout {
  if (msgReceived == 0) {
    write("ERROR: VehicleSpeed message timeout (>500 ms)");
    testStepFail("Speed message timeout");
  }
  msgReceived = 0;
  setTimer(tTimeout, 500);
}
```

**Step 5: Common Issues Found**
- Wrong DBC loaded: signal decoded with wrong formula → wrong display.
- Endianness error: Intel vs. Motorola byte order confusion → wildly incorrect value.
- Timeout not handled: cluster shows last value instead of dashes.
- Bus-off state: controller enters Bus-off → all signals stop; cluster goes dark.

**Key Points ★**
- ★ Always verify signal format (endianness, factor, offset) manually on at least one message before trusting DBC.
- ★ CAN message timeout testing is safety-critical for tell-tales and speed — never skip it.
- ★ Automation in CAPL saves hours on regression for large signal count ECUs (Cluster can have 200+ signals).

---

## Q11: How do you test LIN communication for cluster tell-tales?

### Question
The Cluster receives ambient light level from an LIN slave (light sensor node). The backlight is not adjusting. How do you debug and test LIN communication?

### Detailed Answer

**LIN Overview for Testers:**
- LIN (Local Interconnect Network): single-master, multi-slave, 19.2 kbps max.
- Master sends header (sync + ID); slave provides response (data bytes + checksum).
- Defined by LIN specification (2.2A); schedule table: master cyclic polls each slave.

**Debug Steps:**

**Step 1: Connect CANoe with LIN hardware (e.g., Vector VN1630A)**
- Load LIN database (.ldf file) for the ambient light sensor.
- Open Trace Window: verify LIN frames on the bus.
- Check: Is the master schedule running? Is slave responding?

**LIN Frame Trace Example:**
```
Timestamp   ID   Dir  Data Bytes          Status
0.000       0x21  TX   [Start] Header      OK
0.001       0x21  RX   [A3 00 FF 00 00]    OK  ← slave response
...
0.100       0x21  TX   [Start] Header      OK
0.101       0x21  --   [No response]       TIMEOUT ← slave not responding
```

**Step 2: Check LIN Checksum**
- LIN 2.x uses enhanced checksum (includes ID byte in checksum).
- LIN 1.x uses classic checksum (data bytes only).
- If classic slave is paired with enhanced master → checksum error every frame.
- CANoe LIN trace shows `ChecksumError` flag if mismatch.

**Step 3: LIN Schedule Monitoring**
- Open LIN Schedule Window in CANoe: verify the ambient light frame is included in the master schedule at correct rate.
- Missing entry in schedule table → slave never polled → no data.

**Step 4: Stimulate with CANoe LIN Simulation**
- Simulate LIN master in CANoe; send different light level values via scripted LIN frames.
- Observe Cluster backlight response at each simulated level.

**Common LIN Issues:**

| Issue | Symptom | Root Cause |
|-------|---------|-----------|
| Slave not in schedule | No response | Developer forgot to include frame ID in master schedule table |
| Checksum type mismatch | Checksum error every frame | Classic vs. enhanced checksum configuration |
| Wrong baud rate | Framing errors | Slave configured at 9600 bps; master at 19200 bps |
| LIN wiring fault | Intermittent errors | Pull-up resistor missing; bus voltage rail issue |
| LDF mismatch | Wrong signal decode | Outdated LDF used in CANoe |

**Key Points ★**
- ★ Always use the exact same LDF version that matches the hardware firmware — outdated LDF causes false pass/fail.
- ★ LIN bus-off is not possible (unlike CAN) — LIN slave simply stops responding; look for no-response events.
- ★ LIN schedule table is the master's job — if the master doesn't poll, the slave will never answer.

---

## Q12: Describe complete UDS diagnostics testing for an ECU — all services.

### Question
As test lead, define the full UDS diagnostics test strategy for an ADAS ECU, covering all key services and NRC handling.

### Detailed Answer

**UDS (ISO 14229) Services Test Matrix:**

| Service ID | Service Name | Key Test Scenarios |
|-----------|-------------|-------------------|
| 0x10 | Diagnostic Session Control | Enter Default/Extended/Programming session; verify ECU transitions; verify NRC 0x12 (subFunction not supported) |
| 0x11 | ECU Reset | Hard reset (0x01), Soft reset (0x03); verify boot time; verify DTC cleared on hard reset per spec |
| 0x14 | Clear DTC | Clear all DTCs; verify DTC list empty via 0x19; verify NRC 0x22 if conditions not met |
| 0x19 | Read DTC Information | Sub-functions: 0x01 (count), 0x02 (FF DTCs), 0x06 (DTC with extended data), 0x0A (all supported DTCs) |
| 0x22 | Read Data By Identifier | Read DID 0xF101 (software version), 0xF18C (ECU serial), 0xF190 (VIN); verify correct data returned |
| 0x27 | Security Access | Seed/Key exchange; verify lockout after 3 failed attempts (NRC 0x36: exceededNumberOfAttempts); correct key algorithm |
| 0x28 | Communication Control | Disable/enable Rx/Tx; verify CAN communication halted; verify NRC if wrong mode |
| 0x2E | Write Data By Identifier | Write VIN (0xF190) in programming session; verify persistence after reset |
| 0x31 | Routine Control | Start/stop/result: checksum verification (0xFF01), erase memory (0xFF00) |
| 0x34/36/37 | Flash Download (FBL) | RequestDownload → TransferData (chunks) → RequestTransferExit; verify CRC; test mid-transfer interruption |
| 0x3E | Tester Present | Verify session kept alive; verify session timeout without TesterPresent after 5 s |
| 0x85 | Control DTC Setting | On/Off; verify DTCs not stored during off state; verify they resume on On |

**NRC (Negative Response Code) Testing:**

| NRC | Code | Test Scenario |
|-----|------|--------------|
| generalReject | 0x10 | Send malformed request; verify 0x10 response |
| serviceNotSupported | 0x11 | Send service ID not implemented by ECU |
| subFunctionNotSupported | 0x12 | Send valid service ID + invalid sub-function |
| incorrectMessageLengthOrInvalidFormat | 0x13 | Send 0x22 with incomplete DID (1 byte instead of 2) |
| conditionsNotCorrect | 0x22 | Try Security Access in Default session (not allowed) |
| requestSequenceError | 0x24 | Send TransferData (0x36) without RequestDownload (0x34) first |
| requestOutOfRange | 0x31 | Request DID outside supported range |
| securityAccessDenied | 0x33 | Send valid service requiring security without unlock |
| uploadDownloadNotAccepted | 0x70 | Request flash download when ECU not in prog session |

**Key UDS Test Scenarios (ADAS ECU):**
```
Scenario: CAN Bus interrupted during UDS session
  1. Establish Extended Session (0x10 03)
  2. Send TesterPresent (0x3E) every 2 s to keep session alive
  3. Interrupt CAN bus for 6 s (> session timeout = 5 s)
  4. Restore CAN bus
  Expected: ECU reverts to Default Session; must re-enter Extended Session
  Verify: Send 0x19 02 FF → NRC 0x22 (conditionsNotCorrect) since back in Default
```

**Key Points ★**
- ★ Always test NRCs — ECUs sometimes return generic 0x10 instead of the correct specific NRC; this fails ASPICE audits.
- ★ Security Access (0x27) lockout testing is critical — wrong implementation can brick an ECU in the field.
- ★ Flash download testing: always test mid-transfer interruption — this is the most likely real-world failure scenario.

---

## Q13: How do you set up and use a HIL bench for ADAS testing?

### Question
You need to test the AEB (Automatic Emergency Braking) feature on a HIL bench. Describe the full HIL setup and test execution approach.

### Detailed Answer

**HIL Bench Architecture for ADAS:**

```
┌─────────────────────────────────────────────────────────┐
│                  HIL Test Bench                          │
│                                                          │
│  ┌────────────┐   CAN/LIN/Eth   ┌──────────────────┐    │
│  │ ADAS ECU   │◄───────────────►│ dSPACE SCALEXIO  │    │
│  │ (real HW)  │                 │ (Signal Simulator)│    │
│  └────────────┘                 │                   │    │
│       │ CAN                     │ - Vehicle model   │    │
│       │ (Brake demand)          │ - Radar target sim│    │
│  ┌────▼───────┐                 │ - Camera sim      │    │
│  │Brake ECU   │                 │ - I/O: PWM, ADC   │    │
│  │(simulated) │                 └──────────────────┘    │
│  └────────────┘                         │               │
│                                 ┌────────▼─────────┐    │
│                      Vector PC  │CANoe + Test Desk  │    │
│                                 │(Test automation)  │    │
│                                 └──────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**HIL Setup Steps:**

1. **Hardware setup**: Mount real ADAS ECU on interface board. Connect CAN/LIN/Ethernet lines to dSPACE I/O.
2. **Signal model**: Import vehicle dynamics model (Simulink) into dSPACE ControlDesk. Configure: vehicle speed, relative object speed, object distance.
3. **Radar target simulation**: Inject radar-like CAN messages simulating a target vehicle at configurable distance/speed.
4. **Test automation**: Use CANoe TestDesks (CAPL-based) or Python (via CANoe COM API) to execute test scripts.
5. **Measurement**: dSPACE ControlDesk records all signals; CANoe captures CAN trace.

**AEB Test Cases on HIL:**

| Test ID | Scenario | Stimuli | Expected ADAS Output |
|---------|---------|--------|----------------------|
| AEB-01 | Stationary target, host @ 50 km/h | Radar: target at 30 m, 0 km/h | AEB warning → partial brake → full stop |
| AEB-02 | Moving target, host @ 60 km/h | Radar: target at 40 m, 20 km/h (closing) | AEB activates, deceleration > 6 m/s² |
| AEB-03 | No target (clear road) | Radar: no target in path | No false activation |
| AEB-04 | Target detected then lost | Radar: target at 20 m disappears | AEB cancels; no residual braking |
| AEB-05 | Low-speed cut-in | Radar: target cuts in at 5 m, 10 km/h | Rapid AEB (<200 ms) |
| AEB-06 | Driver override (pressing accelerator) | During AEB: throttle override signal | AEB cancels per spec |

**Key Points ★**
- ★ Validate HIL model accuracy first — run a known-real-world scenario and compare HIL output vs. vehicle log.
- ★ False positive testing (clear road → no activation) is as important as true positive testing.
- ★ HIL allows 1000+ test runs overnight — use this to test edge cases impossible to reproduce in a real vehicle.

---

## Q14: How do you validate Android Auto and Apple CarPlay integration?

### Question
The Infotainment team reports that Android Auto frequently disconnects after 30 minutes. How do you systematically debug and validate AAuto/CarPlay?

### Detailed Answer

**Android Auto Architecture:**
```
Smartphone (Android 6.0+)
  ↕ USB (AOA 2.0 protocol) or Wi-Fi (AAuto Wireless)
Head Unit (HU: Android Automotive OS or QNX)
  ├── Android Auto App (HU side, Google-signed APK)
  ├── AA protocol: Protobuf messages over USB/Wi-Fi
  └── Services: navigation (TBT), media, phone, assistant
```

**Debug Steps for 30-Minute Disconnect:**

**Step 1: Capture ADB logs during disconnect event**
```bash
# On development HU (with adb access):
adb logcat -b all -v threadtime > aadrop_log.txt &
# Reproduce the issue (30 min wait or accelerated stress test)
# Pull log after disconnect
adb pull /data/logs/aa_crash/ .
```

**Step 2: Analyse logcat for Android Auto keywords**
```bash
grep -E "AndroidAuto|HUConnection|AOADisconnect|ProtocolError" aadrop_log.txt
```

**Common Disconnect Root Causes:**
| Root Cause | Log Indicator | Fix |
|-----------|--------------|-----|
| USB cable power drop (voltage sag) | `AOA_USB: voltage warning < 4.5V` | Check HU USB power output spec (≥ 900 mA) |
| HU memory pressure → AA service killed | `ActivityManager: kill AA, low memory` | Memory optimization; AA process given higher priority |
| Protocol watchdog timeout | `AA Heartbeat timeout: no ping 30s` | Investigate SW hang in AA service; increase watchdog only as workaround |
| Wi-Fi channel conflict (AAuto Wireless) | `Wi-Fi: frequent reassociation` | Fix HU Wi-Fi channel selection; avoid channel 6 conflict with phone hotspot |
| BT RFCOMM disconnect → AA teardown | `RFCOMM: connection closed` | BT stack stability fix |

**Step 3: Validation Test Suite for AA/CarPlay**

| Test | Description | Method |
|------|------------|--------|
| Connection stability | Connect AA, leave for 4 hours, monitor | Automated ADB health checker |
| Reconnect after sleep | HU sleep/wake; phone lock/unlock | Manual + ADB |
| Audio routing | AA audio playing; incoming call, verify HFP takeover | Manual |
| Navigation display | Maps TBT displayed on HU correctly | Manual + screenshot compare |
| CarPlay (iOS) | USB + wireless; same stability tests | Manual |
| Stress: rapid connect/disconnect | 50× connect/disconnect in 30 min | Automated ADB script |
| Protocol compliance | CPCM (CarPlay Compliance) test runner (Apple-provided tool) | Apple MFi test tool |

**Key Points ★**
- ★ AA/CarPlay disconnect issues are almost always either USB power, memory, or BT/Wi-Fi interference — check these first.
- ★ Always capture ADB logs in the background during long-soak tests — the disconnect event leaves evidence in logcat.
- ★ OEM certification requires passing CarPlay compliance test (Apple MFi) and AACM test (Google) — start these early.

---

## Q15: How do you debug Bluetooth A2DP audio quality issues?

### Question
Users report audio stuttering when playing music via Bluetooth A2DP on the Infotainment system. How do you diagnose and test this?

### Detailed Answer

**Bluetooth Audio Stack (A2DP):**
```
Phone (Source)           HU (Sink)
A2DP Source         ←→  A2DP Sink
  ↕ L2CAP             ↕ L2CAP
  ↕ ACL               ↕ ACL
    ↕
  2.4 GHz RF link
    ↕
  Physical (BT 4.2 / BT 5.0)
```

**Audio Codec Path:**
```
Phone → [SBC/AAC/aptX encoded audio] → BT RF → HU → [decoded PCM] → DSP → Speaker
```

**Diagnosis Steps:**

**Step 1: Determine codec in use**
```bash
# On rooted Android phone or engineering build:
adb shell dumpsys bluetooth_manager | grep -i codec
# Output: CODEC_TYPE: AAC, SAMPLE_RATE: 44100, BITRATE: 320kbps
```

**Step 2: Check for interference**
- 2.4 GHz contention: Wi-Fi (2.4 GHz) and Bluetooth share band.
- Test: disable Wi-Fi on HU → if audio improves, it is Wi-Fi coexistence issue.
- Fix: enable Bluetooth/Wi-Fi coexistence algorithm (separate time slots) in firmware.

**Step 3: Measure BT RSSI and packet loss**
```
CANoe BT analysis plugin (if available) or
Use BT sniffer (Ubertooth One / Ellisys analyzer):
  - Monitor ACL packet error rate
  - Target: PER (Packet Error Rate) < 0.1%
  - If PER > 1%: RF quality issue → antenna placement, coexistence
```

**Step 4: A2DP Buffer Analysis**
- Stutter occurs when audio FIFO underruns.
- Check: `adb logcat | grep "A2DP audio underrun"`.
- Underrun causes: BT scheduling delay, CPU contention on HU, incorrect jitter buffer size.
- Fix: tune jitter buffer depth in A2DP sink driver (platform-specific BSP setting).

**Validation Test Matrix:**

| Test | Pass Criterion |
|------|---------------|
| SBC audio — 30 min soak | 0 audible stutters, 0 underruns in logcat |
| AAC audio — 1 h soak | 0 audible stutters |
| Audio during Wi-Fi active | ≤ 2 stutter events per 30 min (within coexistence spec) |
| Phone call interruption → A2DP resume | Resume audio within 2 s of call end |
| Codec negotiation: AAC priority over SBC | Verify codec = AAC when both devices support it |
| AVRCP: play/pause/next from HU | Commands received and executed within 500 ms |

**Key Points ★**
- ★ A2DP stuttering is almost always caused by Wi-Fi/BT coexistence or audio buffer tuning — not a user-visible crash, but equally damaging to perception quality.
- ★ Always test with a variety of phones — codec negotiation differs between manufacturers (Samsung AAC is different from iPhone AAC behavior).
- ★ Log-based testing is essential — stutter events leave traces in logcat; don't rely on listen-only testing.

---

## Q16: How do you test OTA (Over-The-Air) update functionality for a TCU?

### Question
Describe your complete OTA update test strategy for a Telematics Control Unit including rollback and mid-update failure scenarios.

### Detailed Answer

**OTA Update Architecture:**
```
OEM Backend (OTA Server)
    ↓ HTTPS (TLS 1.3)
TCU (Telematics Control Unit)
    ↓ Internal bus (CAN/Eth)
Target ECUs (ADAS, Cluster, Infotainment)
    via AUTOSAR UCM (Update and Configuration Management)
```

**OTA Test Categories:**

**1. Happy Path Testing:**
| Test | Steps | Expected |
|------|-------|---------|
| Full ECU update | Push 50 MB update → TCU downloads → applies → reboots | Software version incremented; TCU reconnects within 2 min |
| Delta update | Push 5 MB delta patch (only changed sections) | ECU patched; version updated; 10× faster than full flash |
| Multi-ECU campaign | Update ADAS + Cluster in sequence via UCM | Both ECUs updated; sequencing: ADAS first, then Cluster per spec |

**2. Failure / Negative Testing:**

| Failure Scenario | Stimulation | Expected Behavior |
|-----------------|------------|-------------------|
| Download interrupted (60% complete) | Kill cellular connection during download | TCU resumes download from checkpoint on reconnect |
| CRC mismatch (corrupted file) | Inject 1-bit flip in downloaded image | Signature verification fails; update rejected; rollback to previous version |
| Flash interrupted (power cut during write) | Hard power cut during transfer phase | ECU boots from backup partition (A/B partition scheme); previous SW restored |
| Insufficient storage | Fill ECU flash before OTA push | OTA manager rejects campaign; reports "insufficient space" error to backend |
| Update during eCall active | Trigger OTA while simulating eCall session | OTA deferred; eCall takes priority; OTA resumes after eCall session ends |
| Wrong target ECU | Push wrong firmware (e.g., cluster FW to ADAS) | ECU compatibility check fails; NRC 0x31 (requestOutOfRange); no flash |

**3. Rollback Testing:**
```
Test Scenario:
1. Get current version: sw_v = 3.2.1
2. Push OTA update: sw_v → 3.3.0
3. After flash: verify sw_v = 3.3.0
4. Simulate update failure at 80% (or forced via backend "rollback now" command)
5. Expected: ECU rollback → sw_v = 3.2.1
6. Verify functional operation at 3.2.1 (no regression)
```

**Key Metrics:**
| KPI | Target |
|-----|-------|
| Download success rate (good network) | ≥ 99.5% |
| Update apply success rate | ≥ 99% |
| Max update time (50 MB, LTE Cat-4) | ≤ 10 min |
| Rollback success rate | 100% |
| Post-update boot time | ≤ 30 s |

**Key Points ★**
- ★ Power-cut during flash is the most catastrophic OTA failure — A/B partition + secure boot is the only safe solution.
- ★ Signature/CRC verification must be tested — an unverified skip is a major cybersecurity gap.
- ★ Always test OTA under degraded network (2G/3G, low signal) — not just ideal conditions.

---

## Q17: How do you test ADAS radar sensor calibration and functional validation?

### Question
The ADAS team reports the front radar is detecting objects 2 m ahead of actual position. How do you validate radar calibration and functionality?

### Detailed Answer

**Radar Validation Levels:**

```
Level 1: Radar Sensor Standalone (HIL/lab)
  → Raw radar data validation (azimuth, elevation, velocity)
  
Level 2: Radar + Sensor Fusion (SIL/HIL)
  → Fusion output vs. ground truth comparison
  
Level 3: Full Vehicle (Track / Public Road)
  → Functional feature test (AEB, ACC activation)
```

**Calibration Error Diagnosis:**

2 m offset in range detection suggests one of:
1. **Mounting offset**: physical bracket position differs from nominal.
2. **Calibration parameter error**: radar range bias parameter in ECU memory wrong.
3. **Signal processing bug**: range calculation formula has constant offset.
4. **Timestamp issue**: sensor data and vehicle speed combined with wrong timing → prediction error.

**Step 1: Read calibration parameters via UDS:**
```
Service 0x22 (Read Data By ID):
  DID 0x2001: Radar mounting X offset
  DID 0x2002: Radar mounting Y offset
  DID 0x2003: Radar pitch angle
  DID 0x2004: Radar yaw angle
Expected: X=0.00 m, Y=0.00 m (or per vehicle spec); if DID 0x2001 = 2.0 m → found it
```

**Step 2: Radar end-of-line calibration (workshop test)**
```
Procedure:
1. Vehicle on alignment bay, stationary.
2. Place radar reflector at precisely 10 m ahead (measured with laser).
3. Send UDS: 0x31 01 0xFF10 (start calibration routine).
4. ECU measures actual position vs. reference (10 m) → computes offset.
5. Stores corrected mounting parameters in NVM.
6. Send 0x31 01 0xFF11 (stop/save calibration).
7. Verify: re-read DID 0x2001 → new value; repeat measurement → 10 m ± 0.1 m.
```

**Step 3: On-track validation**

| Test | Scenario | Pass Criterion |
|------|---------|---------------|
| Stationary target range | Bollard at 10 m | Radar reports 10 m ± 0.2 m |
| Moving target velocity | Vehicle at 40 km/h approaching → closing rate 40 km/h | Radar Doppler ± 1 km/h |
| Azimuth accuracy | Target at 5° angle | Reported azimuth: 5° ± 0.5° |
| Detection range | Minimum/maximum spec range (e.g., 0.5–200 m) | Objects detected within spec range |
| False alarm rate | Clear road, 30 min drive | 0 false target detections |

**Key Points ★**
- ★ Always check calibration parameters via UDS before physical measurements — saves hours of physical work.
- ★ Radar calibration must be done in a controlled environment — wind, humidity, and nearby metal structures affect results.
- ★ Document ground truth measurement method (laser rangefinder accuracy) — measurement system accuracy must be better than the tolerance you're testing.

---

## Q18: How do you test Instrument Cluster boot sequence and display integrity?

### Question
The Cluster fails to complete its boot sequence after a software update. How do you diagnose and define a complete boot sequence test?

### Detailed Answer

**Cluster Boot Sequence (Typical):**
```
Power ON (IGN ON signal received on CAN or hard-wire)
    ↓ t=0 ms
[Bootloader] starts → hardware self test (RAM, ROM checksum)
    ↓ t=100 ms
[RTOS / OS kernel] loads
    ↓ t=500 ms
[Drivers initialized] CAN controller, display driver, NVM driver
    ↓ t=1000 ms
[Application starts] gauge calibration, tell-tale read from NVM, CAN Rx active
    ↓ t=2000 ms
[Gauge sweep] all gauges sweep to max → return to current value (visual self test)
    ↓ t=3000 ms
[Normal operation] speed from CAN, warning from CAN, backlight active
```

**Boot Failure Root Causes After SW Update:**
1. **NVM format change**: new SW has different NVM layout → old NVM data invalid → crash on read.
2. **Flash corruption**: OTA write incomplete → bootloader reads corrupt application → falls back to bootloader hang.
3. **Stack overflow**: new code has larger stack usage → hits guard area → reset loop.
4. **Init sequence error**: new SWC init order changed → dependent SWC starts before dependency ready → NULL pointer.

**Diagnosis Steps:**

**Step 1: Connect CANoe to CAN bus**
- Check if ECU sends NM (Network Management) frames after power: if NM active → OS is running.
- If no CAN frames at all → ECU not completing hardware init → hardware or bootloader issue.

**Step 2: UDS — Check ECU status**
```
Try: Service 0x10 01 (Default session request)
If response received: ECU is alive, application started
If no response (timeout): application not running
```

**Step 3: Check diagnostic trouble codes**
```
Service 0x19 02 FF (read all DTCs):
  - DTC 0xC0001: NVM CRC failure → confirms NVM corruption
  - DTC 0xB0010: Application watchdog reset → confirms watchdog triggered
  - DTC 0xD0020: Boot software integrity fail → confirms flash corruption
```

**Step 4: JTAG (Lauterbach Trace32)**
- Halt CPU; read stack pointer; print call stack → find exact crash location in code.
- Read NVM area: compare layout with new SW expected layout.

**Validation Test Suite for Boot Sequence:**

| Test | Expected | Measure |
|------|---------|---------|
| Normal boot (IGN ON from cold) | All gauges visible within 4 s | Stopwatch or CANoe timestamp |
| Gauge sweep present | Sweep animation plays at 2–3 s mark | Visual + video capture |
| CAN signal acquisition | Speed signal received and displayed within 500 ms of CAN active | CANoe signal trace |
| Post-sleep wakeup boot | Faster wake (< 2 s) vs. cold boot | Timestamp |
| NVM read back | Mileage, settings persisted across reset | UDS read DID after reset |
| Boot after power cut mid-flash | Boot to previous safe version | Verify current SW = previous version |

**Key Points ★**
- ★ Boot time is a customer perception KPI — OEMs specify it in the SRS; always measure it formally.
- ★ Gauge sweep is a safety requirement (visual self-test) — failure to sweep must be captured as a P1 defect.
- ★ Always run boot tests after NVM layout changes — this is a consistently underestimated regression risk.

---

## Q19: How do you validate Ethernet (DoIP) communication for an Infotainment Head Unit?

### Question
The Head Unit communicates with the external diagnostic tool over DoIP (Diagnostics over IP). Describe how you validate DoIP communication.

### Detailed Answer

**DoIP Architecture (ISO 13400):**
```
External Diagnostic Tester
    ↓ Ethernet (100BaseT or 1GbE)
    ↓ IP/UDP/TCP
DoIP Gateway (or HU with DoIP entity)
    ↓ Internal CAN/LIN/Ethernet
Target ECUs
```

**DoIP Communication Flow:**
```
Step 1: Tester → UDP vehicle announcement request (port 13400)
Step 2: DoIP entity → UDP vehicle announcement response (contains VIN + EID)
Step 3: Tester → TCP: DoIP routing activation request (logical address)
Step 4: DoIP entity → Routing activation response (0x00: success)
Step 5: Tester → UDS diagnostic request (wrapped in DoIP data message)
Step 6: DoIP → ECU → response → DoIP → tester
```

**Wireshark Capture for DoIP Validation:**
```bash
# On test PC connected to HU Ethernet:
wireshark -i eth0 -k -f "udp port 13400 or tcp port 13400"

# Filter in Wireshark:
doip
# or:
ip.addr == 192.168.1.100 && doip
```

**DoIP Negative Test Cases:**

| Test | Stimulation | Expected |
|------|------------|---------|
| Wrong logical address | Send routing activation with non-existent ECU address | Nack: unknown logical address |
| TCP connection timeout | Open TCP, no messages for 60 s | DoIP closes connection (inactivity timeout) |
| Message too large | Send diagnostic message > max DoIP PDU (4095 bytes) | DoIP fragmentation or error response |
| Multiple testers | Two PCs send simultaneous routing activation | First accepted; second: NackCode 0x04 (SA already used) |
| DoIP entity unreachable | Power off HU; send UDP announcement | Tester times out; logs "no vehicle response" |

**Key Points ★**
- ★ DoIP is replacing classical K-Line and is now standard on all new vehicles — test leads must be fluent in DoIP.
- ★ Wireshark + DoIP dissector gives you full visibility — capture during every diagnostic test session.
- ★ DoIP routing activation must complete before any UDS service — ensure this step is automated in your test setup.

---

## Q20: How do you perform SIL (Software-in-the-Loop) testing for ADAS algorithms?

### Question
You need to validate the AEB algorithm at SIL level before real hardware is available. Describe the SIL setup and test approach.

### Detailed Answer

**SIL Architecture:**
```
MATLAB/Simulink Model (ADAS Algorithm):
  ├── Object Detection Model
  ├── Sensor Fusion Model
  ├── TTC (Time-to-Collision) Calculation
  └── Brake Demand Output

Feed: Simulated radar/camera data (from scenario files)
Output: Brake demand signal
Compare: vs. expected braking profile (defined in test spec)
```

**Test Data Sources:**
1. **Synthetic**: mathematically defined scenarios (object at 20 m, closing speed 10 m/s).
2. **Recorded real vehicle data**: raw sensor data from test drives → replayed in SIL.
3. **Euro NCAP virtual testing datasets**: standard scenario library for AEB (pedestrian, car-to-car).

**SIL Test Execution (Python + MATLAB Engine):**
```python
import matlab.engine
import numpy as np

eng = matlab.engine.start_matlab()

# Load ADAS Simulink model
eng.load_system('AEBAlgorithm.slx', nargout=0)

# Define test scenario
scenario = {
    'host_speed_kmh': 50,
    'target_distance_m': 30,
    'relative_speed_ms': 13.9,  # 50 km/h closing
    'target_type': 'pedestrian'
}

# Run simulation
eng.set_param('AEBAlgorithm/HostSpeed', 'Value', str(scenario['host_speed_kmh']/3.6), nargout=0)
eng.set_param('AEBAlgorithm/TargetDist', 'Value', str(scenario['target_distance_m']), nargout=0)
eng.sim('AEBAlgorithm', nargout=0)

# Extract results
brake_demand = np.array(eng.workspace['brake_demand_output'])
ttc = np.array(eng.workspace['ttc'])

# Validate
assert max(brake_demand) >= 0.6, "AEB brake demand insufficient"
assert min(ttc) < 2.0, "AEB triggered too late"
print("PASS: AEB algorithm correct for pedestrian scenario at 50 km/h")
```

**SIL Pass Criteria for AEB:**

| Scenario | Metric | Target |
|---------|--------|-------|
| Pedestrian at 30 km/h | Brake demand issued when TTC < 2 s | ✓ |
| Car-to-car @ 50 km/h | Full stop before impact (simulated) | ✓ |
| False alarm (clear road) | 0 brake demand on 1000 random clear-road scenarios | ✓ |
| Boundary: target at just-detectable range | Algorithm handles edge of detection zone | ✓ |

**Key Points ★**
- ★ SIL must run thousands of scenarios that are impossible to test physically — automation and scenario generation are key.
- ★ SIL results directly feed ISO 26262 functional safety coverage evidence — document them systematically.
- ★ Regression: run full SIL suite on every algorithm change — a 0.1 s change in reaction time can fail Euro NCAP.

---

## Q21: How do you test Cluster tell-tales (warning lights) systematically?

### Question
Define a complete test strategy for all instrument cluster tell-tale indicators.

### Detailed Answer

**Tell-Tale Classification (ISO 2575):**
- **Red**: Immediate danger — oil pressure, engine temperature, brake failure, seatbelt
- **Amber**: Warning — check engine, ABS, ESP, low fuel
- **Green**: Information — turn signal, high beam, cruise control
- **Blue**: Information — high beam active
- **White**: Information — various

**Tell-Tale Test Approach:**

**1. CAN Signal Stimulation (CANoe/CAPL):**
```capl
// Test: Oil Pressure Warning (Red tell-tale)
// Signal: EngOilPressureWarn, CAN message 0x120, Bit 3

testCase "TC-TT-001: Oil Pressure Warning ON" {
  // Stimulate signal
  $EngOilPressureWarn = 1;
  testWaitForTimeout(500);  // 500 ms
  // Verify: read back via UDS or camera-based HMI check
  // Manual: observer confirms red oil can symbol illuminated
  testStepPass("Oil pressure warning illuminated");
}

testCase "TC-TT-002: Oil Pressure Warning OFF" {
  $EngOilPressureWarn = 0;
  testWaitForTimeout(500);
  // Manual: observer confirms oil can symbol extinguished
  testStepPass("Oil pressure warning extinguished");
}
```

**2. Tell-Tale Status Matrix:**

| Tell-Tale | Color | CAN Signal Source | Test Case Count | Verified By |
|-----------|-------|-------------------|----------------|------------|
| Seatbelt | Red | SeatBeltStatus, 0x120 | Turn ON/OFF, timing spec | CAPL + visual |
| Low Fuel | Amber | FuelLevel < threshold, 0x310 | 3 boundary values | CAPL + visual |
| ABS | Amber | ABSFaultActive, 0x300 | ON/OFF, CAN timeout | CAPL + visual |
| Check Engine | Amber | MIL active DTC, 0x500 | DTC set/clear via UDS | UDS + visual |
| Cruise Control | Green | CruiseControlActive, 0x210 | Activate/deactivate | CAPL + visual |
| High Beam | Blue | HighBeamStatus, 0x150 | Switch ON/OFF | CAPL + visual |

**3. Tell-Tale Timing Requirements:**
- Illumination delay from signal active: ≤ 200 ms
- Extinguish delay from signal inactive: ≤ 200 ms
- Measure in CANoe: `signal_active_timestamp` vs. `HMI_confirmed_timestamp` via camera sync or UDS read

**4. Multiple Simultaneous Tell-Tales:**
- Test: 5 red tell-tales active simultaneously — verify all 5 illuminate (no masking/priority override error).
- Test: priority order if cluster only shows N tell-tales when M>N are active (if limited display area).

**Key Points ★**
- ★ Tell-tale ON/OFF timing is often specified in the SRS (e.g., ≤ 200 ms) — always test and measure it explicitly.
- ★ CAN timeout behavior: all tell-tales must go to defined safe state (typically OFF or flashing) if CAN signal is lost.
- ★ ISO 2575 compliance: tell-tale symbols and colors must match the ISO standard exactly — raise defect for any deviation.

---

## Q22: How do you test gateway ECU for CAN-to-Ethernet protocol conversion?

### Question
A Gateway ECU bridges CAN messages to Ethernet (SOME/IP). Speed signal from CAN-PT needs to be available on Ethernet. Describe the gateway validation.

### Detailed Answer

**Gateway Function:**
```
CAN-PT Bus                        Automotive Ethernet (1000Base-T1)
  Msg 0x3B4                          SOME/IP Service
  VehicleSpeed = 60 km/h    →→→     Service ID: 0x0101
  Transmitted every 10 ms           Method/Event ID: 0x8001
  DBC: factor 0.01 km/h/bit        Serialization: SOME/IP-SD
                                    VehicleSpeed = 60.00 km/h (float32)
```

**Validation Steps:**

**Step 1: CAN side — confirm signal is correct**
- CANoe trace: 0x3B4 at 10 ms, value = 60 km/h (raw = 6000 → × 0.01 = 60.00)

**Step 2: Ethernet side — capture SOME/IP with Wireshark**
```
Wireshark filter: someip
  Field: Service ID = 0x0101
  Field: Method ID = 0x8001
  Field: Message Type = 0x02 (Notification/Event)
  Payload: bytes 0–3 = IEEE 754 float = 60.0 km/h
```

**Step 3: Gateway Validation Matrix:**

| Test | Check | Tool |
|------|-------|------|
| Value correctness | CAN signal = SOME/IP value (± tolerance) | CANoe + Wireshark |
| Latency | CAN frame timestamp vs. SOME/IP frame timestamp ≤ 5 ms | CANoe + Wireshark sync via PPS |
| Cycle time preservation | SOME/IP event fires every 10 ms | Wireshark statistics |
| Signal scaling | CAN raw value correctly converted using factor/offset | Manual decode check |
| Fault propagation | CAN signal timeout → SOME/IP signal = invalid/not sent | CANoe CAN bus off + Wireshark |
| Multiple signal routing | Test 10 CAN signals routed to 10 SOME/IP services | Full regression |

**Key Points ★**
- ★ Latency across gateway is often overlooked — automotive SOME/IP applications expect ≤ 5 ms CAN-to-Eth latency.
- ★ Endianness conversion (CAN Intel-endian → Ethernet Big-endian) is a common gateway bug.
- ★ Always test fault propagation — a missing signal in CAN must not silently appear as a stale value in Ethernet.

---

## Q23: How do you automate CAN signal regression using CAPL scripting?

### Question
Write a CAPL test module that automatically validates 5 key vehicle signals in a regression run.

### Detailed Answer

```capl
/*
 * CAPL Regression Test Module: Vehicle Signal Validation
 * Tests: VehicleSpeed, RPM, FuelLevel, CoolantTemp, BatteryVoltage
 * Format: CANoe TestModule (.can)
 */

variables {
  // Signal tolerance definitions
  float SPEED_TOLERANCE   = 0.5;  // km/h
  float RPM_TOLERANCE     = 50.0; // RPM
  float FUEL_TOLERANCE    = 0.5;  // L
  float TEMP_TOLERANCE    = 1.0;  // °C
  float VOLT_TOLERANCE    = 0.1;  // V
  
  // Measured values
  float g_speed, g_rpm, g_fuel, g_temp, g_batt;
  
  // Message received flags
  int g_speedRcvd, g_rpmRcvd, g_fuelRcvd, g_tempRcvd, g_battRcvd;
}

// ─── Signal Capture Handlers ─────────────────────────────────────────────

on message 0x3B4 {  // VehicleSpeed
  g_speed = (this.byte(0) | (this.byte(1) << 8)) * 0.01;
  g_speedRcvd = 1;
}

on message 0x316 {  // Engine RPM
  g_rpm = (this.byte(2) | (this.byte(3) << 8)) * 0.25;
  g_rpmRcvd = 1;
}

on message 0x310 {  // Fuel Level
  g_fuel = this.byte(0) * 0.4;  // factor 0.4 L/bit
  g_fuelRcvd = 1;
}

on message 0x40B {  // Coolant Temperature
  g_temp = this.byte(0) - 40.0;  // offset -40
  g_tempRcvd = 1;
}

on message 0x420 {  // Battery Voltage
  g_batt = (this.byte(0) | (this.byte(1) << 8)) * 0.001;  // mV to V
  g_battRcvd = 1;
}

// ─── Helper: Check single value ────────────────────────────────────────

void checkSignal(char name[], float measured, float expected, float tolerance) {
  float diff = abs(measured - expected);
  if (diff <= tolerance) {
    testStepPass(name);
    write("[PASS] %s: measured=%.2f, expected=%.2f, diff=%.2f", name, measured, expected, diff);
  } else {
    testStepFail(name);
    write("[FAIL] %s: measured=%.2f, expected=%.2f, diff=%.2f (tolerance=%.2f)",
          name, measured, expected, diff, tolerance);
  }
}

// ─── Test Cases ────────────────────────────────────────────────────────

testCase "TC-REG-01: Vehicle Speed at 60 km/h" {
  // Setup: stimulate via HIL or vehicle rollers at 60 km/h
  testStep("Setup", "Set vehicle speed reference to 60 km/h via HIL");
  g_speedRcvd = 0;
  testWaitForSignalChange("VehicleSpeed", 2000);  // wait max 2 s
  if (!g_speedRcvd) {
    testStepFail("VehicleSpeed message not received within 2 s");
    return;
  }
  checkSignal("VehicleSpeed@60kmh", g_speed, 60.0, SPEED_TOLERANCE);
}

testCase "TC-REG-02: Engine RPM at Idle (750 RPM)" {
  g_rpmRcvd = 0;
  testWaitForSignalChange("EngineRPM", 2000);
  if (!g_rpmRcvd) { testStepFail("RPM message not received"); return; }
  checkSignal("EngineRPM@idle", g_rpm, 750.0, RPM_TOLERANCE);
}

testCase "TC-REG-03: Fuel Level = 40 L" {
  g_fuelRcvd = 0;
  testWaitForSignalChange("FuelLevel", 2000);
  if (!g_fuelRcvd) { testStepFail("FuelLevel message not received"); return; }
  checkSignal("FuelLevel@40L", g_fuel, 40.0, FUEL_TOLERANCE);
}

testCase "TC-REG-04: Coolant Temperature = 90 °C" {
  g_tempRcvd = 0;
  testWaitForSignalChange("CoolantTemp", 2000);
  if (!g_tempRcvd) { testStepFail("CoolantTemp message not received"); return; }
  checkSignal("CoolantTemp@90C", g_temp, 90.0, TEMP_TOLERANCE);
}

testCase "TC-REG-05: Battery Voltage = 12.6 V" {
  g_battRcvd = 0;
  testWaitForSignalChange("BatteryVolt", 2000);
  if (!g_battRcvd) { testStepFail("BatteryVoltage message not received"); return; }
  checkSignal("BattVoltage@12.6V", g_batt, 12.6, VOLT_TOLERANCE);
}

// ─── Test Suite Entry Point ────────────────────────────────────────────

testSuite "TS-VehicleSignals-Regression" {
  testCase "TC-REG-01: Vehicle Speed at 60 km/h";
  testCase "TC-REG-02: Engine RPM at Idle (750 RPM)";
  testCase "TC-REG-03: Fuel Level = 40 L";
  testCase "TC-REG-04: Coolant Temperature = 90 °C";
  testCase "TC-REG-05: Battery Voltage = 12.6 V";
}
```

**Key Points ★**
- ★ Always use tolerance-based comparison for analog signals — exact float equality will always fail due to scaling.
- ★ Add timeout guards on every signal wait — a missing message should fail the test, not hang the suite.
- ★ Structure CAPL tests in suites that match your test management system's test case IDs for easy RTM tracing.

---

## Q24: How do you validate Sleep/Wakeup behavior for ECUs on CAN network?

### Question
The Cluster does not wake up from sleep when the door is opened. Describe your validation approach for sleep/wakeup.

### Detailed Answer

**Network Management (NM) Overview (AUTOSAR NM):**
```
Active State:
  ECU transmits NM messages (0x500 range) every 100 ms
  Keeps network awake collectively

Prepare Sleep:
  All ECUs send "Sleep Ready" bit in NM message
  If all ECUs ready → Sleep request issued

Sleep (Bus Sleep Mode):
  No CAN frames on bus; ECU enters deep sleep (microamps)

Wakeup:
  Physical wakeup: IGN ON, door pulse → wakeup line (hard-wire)
  Network wakeup: any CAN frame detected when bus sleeping
```

**Cluster Wakeup Issue Debug:**

**Step 1: Check physical wakeup line**
- Cluster has a WAKE_IGN pin from the body control module.
- Measure voltage on WAKE_IGN pin with oscilloscope when door is opened.
- Expected: 0 V → 12 V pulse (≥ 10 ms) → triggers ECU wakeup.
- If no pulse: BCM (Body Control Module) not sending wakeup → issue is BCM, not Cluster.

**Step 2: CANoe — Network Wakeup Test**
```
Procedure:
1. Let all ECUs sleep (no CAN frames for 10 s)
2. CANoe: observe bus voltage — should be 0 (bus sleep)
3. Simulate door open: send wakeup CAN frame (NM message from BCM)
4. Measure: time from first CAN frame to Cluster NM frame appearance
Expected: Cluster active (NM message visible) within 500 ms
```

**Step 3: Sleep/Wakeup Test Matrix**

| Test | Wakeup Source | Expected | Measured |
|------|-------------|---------|---------|
| SW-01 | IGN ON | All ECUs wake within 500 ms | |
| SW-02 | Door open (CAN NM) | Cluster wakes; BCM NM triggers cluster | |
| SW-03 | Remote key (RF → BCM CAN) | Cluster wakes for pre-AC or seat heating | |
| SW-04 | Bus sleep after 10 s idle | All ECUs in sleep; 0 CAN frames | |
| SW-05 | Wake during sleep mode power draw | ECU current draw < 0.5 mA in sleep | Measured with current clamp |
| SW-06 | Rapid wake/sleep cycle × 100 | No stuck-awake or stuck-sleep | Automated 100 cycle test |

**Key Points ★**
- ★ Sleep/wakeup bugs are among the most common field issues — they drain the 12 V battery if an ECU never sleeps.
- ★ Always measure current draw in sleep mode — spec typically < 1 mA for non-safety ECUs.
- ★ NM configuration errors (wrong node ID, wrong network handle) are the most common root cause of sleep/wake bugs.
