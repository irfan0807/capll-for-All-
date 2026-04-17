# Section 3: Debugging & Failure Analysis
> **Role**: Senior Automotive Testing Team Lead | **Questions**: Q25–Q34

---

## Q25: How do you perform root cause analysis (RCA) for a P1 defect in production?

### Question
A customer-reported issue: Infotainment system freezes during navigation on a specific model. How do you lead the RCA process?

### Detailed Answer

**RCA Framework: 5-Why + Fishbone (Ishikawa) Diagram**

**Step 1: Reproduce the issue**
```
Steps to reproduce (from customer report):
1. Start navigation with destination 50+ km
2. Drive > 45 minutes continuous
3. Infotainment screen freezes; touchscreen unresponsive
4. Hard power cycle required to recover

Initial hypothesis: memory leak OR thermal throttling OR infinite loop in navigation app
```

**Step 2: Collect Evidence**

| Evidence Source | Collection Method | What to Look For |
|----------------|------------------|-----------------|
| ADB logcat | `adb logcat -b all > log.txt` | ANR (Application Not Responding), OOM (OutOfMemory), system_server crash |
| Tombstone (crash dump) | `/data/tombstones/` via `adb pull` | Native crash: backtrace, signal (SIGSEGV, SIGABRT) |
| ANR trace | `/data/anr/traces.txt` | Deadlocked threads; navigation thread blocked |
| Memory data | `adb shell dumpsys meminfo com.oem.navigation` | PSS memory growth over time; heap size growing = leak |
| CPU data | `adb shell top -d 1 > cpu.txt` | 100% CPU on any process |
| Thermal log | `adb shell cat /sys/class/thermal/thermal_zone*/temp` | SoC temperature > thermal throttle threshold (typically 75–85°C) |

**Step 3: Logcat Analysis**
```bash
grep -E "OutOfMemoryError|ANR|fatal|ActivityManager.*crash|navigat.*died" log.txt

# Found:
08-15 14:32:11.541 E ActivityManager: ANR in com.oem.navigation
08-15 14:32:11.542 E ActivityManager: CPU usage: navigation=98% (2 min avg)
08-15 14:32:11.543 E ANRManager: Main thread blocked for 12 s
08-15 14:32:11.600 E ActivityManager: NavigationApp has leaked ServiceConnection
```

**Step 4: 5-Why Analysis**
```
Why did the screen freeze?
  → navigationApp ANR (blocked main thread 12 s)
Why was the main thread blocked?
  → ServiceConnection leaked → main thread waiting on ghost service
Why did ServiceConnection leak?
  → Navigation onDestroy() not called when displaying turn-by-turn; Lifecycle bug
Why wasn't Lifecycle handled correctly?
  → Developer used Fragment without LifecycleOwner → onDestroy skipped
Why wasn't this caught in testing?
  → Test suite lacked 45+ min long-soak test; CI only ran 5 min navigation tests
```

**Root Cause:** Navigation activity has a ServiceConnection leak due to incorrect lifecycle management. Not caught because soak test duration was insufficient in CI.

**Step 5: Fix + Verification**
- Developer fix: bind/unbind service in onStart/onStop instead of onCreate/onDestroy.
- Verification: run 4-hour soak test with continuous navigation → no ANR, meminfo shows stable heap.

**Corrective & Preventive Actions (CAPAs):**
- Fix: NavigationActivity lifecycle fix → targeted release.
- Prevention: Add 2-hour soak test to nightly CI for navigation module.
- Prevention: Add memory leak detection (LeakCanary library) to daily build.

**Key Points ★**
- ★ ADB logcat + meminfo is your first tool for any Android infotainment freeze — never start with guesswork.
- ★ 5-Why consistently leads to the process gap (not just the code bug) — both must be addressed.
- ★ Soak tests must be in CI — bugs that only appear after 45 minutes are invisible to short test suites.

---

## Q26: How do you debug a CAN Bus-off state on an ECU?

### Question
The ADAS ECU is entering Bus-off and stopping all CAN communication. How do you diagnose and fix this?

### Detailed Answer

**CAN Bus-off Explained:**
```
CAN error counter: every ECU has TEC (Transmit Error Counter) and REC (Receive Error Counter)
  Error active: TEC/REC < 128 (normal)
  Error passive: TEC/REC ≥ 128 (transmits passive error flags)
  Bus-off: TEC ≥ 256 (ECU stops transmitting entirely; disconnects from bus)
  
Recovery: After 128 × 11 recessive bits on bus (auto recovery per CAN spec)
  OR: ECU reset
```

**Bus-off Root Causes:**

| Cause | How to Identify |
|-------|----------------|
| CAN wiring issue (short, open, termination) | Measure bus voltage; both lines at 2.5 V when idle; CAN-H 3.5 V, CAN-L 1.5 V during dominant bit |
| Wrong termination resistance | Bus should have exactly 2× 120 Ω = 60 Ω total; measure with multimeter (bus powered off) |
| Wrong baud rate | ECU configured at 500 kbps; bus is 250 kbps → framing errors immediately → Bus-off |
| Babbling idiot ECU | One ECU sending constant frames → overloads bus → other ECUs accumulate errors |
| TX timeout (AUTOSAR ComStack misconfigured) | ECU AUTOSAR Com triggers continuous CAN TX at wrong rate → self-saturates |

**Step 1: CANoe Diagnosis**
```
Open Statistics Window:
  - Channel error count: rising → errors accumulating
  - Error frames visible in trace → double-click → inspect Error Type:
      Bit Error: ECU sent 1; received 0 → wiring or voltage mismatch
      Stuff Error: >5 consecutive same bits → baud rate mismatch or synchronization error
      CRC Error: data corrupted in transit → noise, bad cable
      Form/Ack Error: framing issue → baud rate usually

Open Error Frame Analysis:
  Time of first error frame → correlate with system event (power on? software action?)
```

**Step 2: Physical Layer Check**
```bash
# Oscilloscope measurements on CAN-H/CAN-L at ECU connector:
Idle state:   CAN-H = 2.5 V, CAN-L = 2.5 V (differential = 0 V recessive)
Dominant bit: CAN-H ≈ 3.5 V, CAN-L ≈ 1.5 V (differential = 2 V)
Eye diagram:  edges clean, no ringing, no reflections
Termination:  measure R between CAN-H and CAN-L at ECU connector (no power):
              Should read: 60 Ω (2 termination resistors in parallel)
              If 120 Ω: one termination missing
              If < 60 Ω: short circuit or extra termination
```

**Step 3: Bus-off Recovery Test**
```capl
// CAPL: Monitor for Bus-off and measure recovery time
variables {
  msTimer tBusOffDetect;
  long busOffStartTime;
}

on busOff {  // CANoe built-in event
  busOffStartTime = timeNow();
  write("BUS-OFF detected on channel %d at time %d ms", this.channel, timeNow()/10000);
}

on signal ECU_Status.CAN_BusState {  // Signal indicating ECU bus state
  if (this.val == 0 && busOffStartTime > 0) {
    long recoveryTime = timeNow() - busOffStartTime;
    write("BUS-OFF recovered: recovery time = %d ms", recoveryTime/10000);
    if (recoveryTime/10000 > 500) {
      testStepFail("Bus-off recovery time exceeded 500 ms");
    } else {
      testStepPass("Bus-off recovery time within spec");
    }
    busOffStartTime = 0;
  }
}
```

**Key Points ★**
- ★ Bus-off is always caused by a physical layer issue or baud rate mismatch — start diagnostics with a scope, not software.
- ★ "Babbling idiot" protection: every production system should have a watchdog that detects excessive TX and shuts down the offending ECU.
- ★ Bus-off recovery time must be tested — for safety ECUs, recovery > 1 s is a critical defect.

---

## Q27: How do you use Wireshark to debug DoIP or Ethernet communication issues?

### Question
A diagnostic tool fails to read DIDs from the ADAS ECU over DoIP. Walk through Wireshark-based debugging.

### Detailed Answer

**Setup:**
```bash
# Connect test PC to automotive Ethernet switch or mirror port
# Capture with targeted filter:
wireshark -i eth0 -w capture.pcapng -f "tcp port 13400 or udp port 13400"

# Or open existing capture and filter:
Filter bar: doip
```

**DoIP Frame Dissection in Wireshark:**

```
Frame 47: DoIP Vehicle Announcement
  ├── Source: 192.168.1.100 (HU/Gateway)
  ├── Destination: 255.255.255.255 (broadcast)
  ├── Protocol: DoIP
  ├── DoIP Header:
  │     Protocol Version: 0x02 (ISO 13400-2:2019)
  │     Payload Type: 0x0004 (Vehicle Announcement)
  │     Payload Length: 33
  └── DoIP Payload:
        VIN: "1HGCM82633A004352"
        Logical Address: 0x0E80 (ADAS ECU)
        EID: AA:BB:CC:DD:EE:FF
        GID: 00:00:00:00:00:01

Frame 52: UDS Request (wrapped in DoIP)
  ├── DoIP: Data (payload type 0x8001)
  ├── Source Address: 0x0500 (tester)
  ├── Target Address: 0x0E80 (ADAS ECU)
  └── UDS: 22 F1 01  (ReadDataByIdentifier, DID 0xF101)

Frame 53: UDS Response (or DoIP Nack)
  → If NRC received: DoIP data 0x7F 22 XX  (NRC reason)
  → If DoIP Nack:   PayloadType 0x0003, NackCode: 0x04 (busy)
```

**Common DoIP Issues Found via Wireshark:**

| Symptom in Wireshark | Root Cause | Fix |
|---------------------|-----------|-----|
| No vehicle announcement after UDP broadcast | ECU DoIP entity not initialized | Check ECU boot state; verify DoIP entity enabled in config |
| Routing activation rejected (NackCode 0x04) | Too many simultaneous testers | Close previous tester connection first |
| TCP RST immediately after connect | ECU TCP stack overloaded or port blocked by firewall | Check ECU IP stack configuration |
| UDS request sent, no response for 2 s | ECU busy (previous request still processing) | Add P2_max timeout handling in test tool |
| Wrong UDS response data | Signal routing table error in gateway | Verify routing table: source ECU, target address, service path |
| DoIP version mismatch | Tester uses v1 (0x01), ECU expects v2 (0x02) | Align DoIP version configuration |

**Wireshark Expert Tip — Measure P2/P2* timing:**
```
Wireshark → Statistics → I/O Graph:
  Plot: DoIP request (0x8001) vs. response (0x8001)
  Measure delta: P2CLIENT = response latency
  Target: ≤ 50 ms for standard response
  P2*: long response NRC 0x78 → re-evaluate pending → full response
```

**Key Points ★**
- ★ Wireshark with the DoIP dissector is free and is the best tool for DoIP debugging — master it.
- ★ Always capture both the UDP announcement phase and the TCP diagnostic phase.
- ★ Timing issues (P2 timeout) are invisible without Wireshark — pure tool feedback often says "timeout" with no further detail.

---

## Q28: How do you analyse memory leaks in an Android Automotive infotainment system?

### Question
The infotainment HU progressively slows down over a 3-hour drive. You suspect a memory leak. How do you diagnose it?

### Detailed Answer

**Step 1: Establish a Memory Baseline**
```bash
# Capture memory snapshot at T=0 (fresh boot), T=30 min, T=60 min, T=120 min, T=180 min
adb shell dumpsys meminfo > meminfo_T0.txt
# ... wait 30 min of usage ...
adb shell dumpsys meminfo > meminfo_T30.txt
# repeat...

# Important app-level detail:
adb shell dumpsys meminfo com.oem.infotainment.launcher
```

**Reading meminfo output:**
```
Applications Memory Usage (kB):
                    Pss      Private  Private  SwapPss      Heap      Heap      Heap
                  Total    Dirty    Clean    Dirty     Size    Alloc     Free
                -------  -------  -------  -------  -------  -------  -------
  OEM Launcher:  85,420   72,100       0       0   96,000   88,200    2,400  ← growing
  Navigation:    45,200   40,100       0       0   50,000   48,100    1,000
  Media:         32,000   28,000       0       0   35,000   32,000    3,000

Analysis: OEM Launcher Heap Alloc growing from T=0 to T=180:
  T=0:    Heap Alloc = 42,000 KB
  T=60:   Heap Alloc = 65,000 KB   ← +23 MB in 60 min
  T=180:  Heap Alloc = 88,200 KB   ← +46 MB total = clear memory leak
```

**Step 2: Identify Leak Source**
```bash
# Use Android Studio Memory Profiler (if dev build):
# OR LeakCanary integration (for debug APK):
# OR hprof heap dump:
adb shell am dumpheap com.oem.infotainment.launcher /data/local/tmp/heap.hprof
adb pull /data/local/tmp/heap.hprof .

# Analyse with MAT (Eclipse Memory Analyzer Tool):
# 1. Find objects with highest retained heap
# 2. Identify GC root path → find what is holding the reference
```

**MAT Analysis Finding (example):**
```
Leak Suspects Report:
  Class: com.oem.ui.widget.MapTileCache
  Instance count: 1420 (expected: ≤ 50)
  Retained heap: 44 MB
  GC Root: static field TileManager.sCache → ArrayList → MapTile[]
  
Conclusion: MapTileCache not evicting old tiles; static reference prevents GC.
Fix: Implement LRU cache with max size; evict entries when cache exceeds 50 tiles.
```

**Step 3: Validation After Fix**
- Re-run 3-hour soak test.
- Collect meminfo at same intervals.
- Heap Alloc should be stable (± 5 MB variance) over 3 hours.
- Add automated meminfo monitoring to nightly soak test: alert if heap grows > 20 MB over 2 h.

**Key Points ★**
- ★ Memory leaks in automotive infotainment are a common, serious issue — vehicles run for 8+ hours; a 10 MB/h leak causes OOM by end of shift.
- ★ LeakCanary in debug builds is the fastest way to find Java-level leaks — make it standard for all debug APKs.
- ★ Never profile on a production APK with ProGuard enabled — obfuscated names make MAT analysis useless.

---

## Q29: How do you debug an ECU that fails to enter Programming Mode for flashing?

### Question
You are trying to flash new firmware via UDS (Service 0x34/0x36/0x37) but the ECU rejects the request. Describe your debug approach.

### Detailed Answer

**Flash Download Sequence (UDS):**
```
1. 0x10 02 → Enter Extended Diagnostic Session
2. 0x27 01 → Security Access: Request Seed
3. 0x27 02 XX XX XX XX → Security Access: Send Key
4. 0x10 03 → Enter Programming Session
5. 0x31 01 FF 00 → Erase Flash routine (if required)
6. 0x34 00 44 START_ADDR LENGTH → Request Download
7. 0x36 01 DATA... → Transfer Data (block 1)
   0x36 02 DATA... → Transfer Data (block 2)
   ...
8. 0x37 → Request Transfer Exit
9. 0x31 01 FF 01 → Checksum verification routine
10. 0x11 01 → ECU Hard Reset
```

**Common Rejection Scenarios:**

**Case 1: ECU rejects 0x10 03 (Programming Session) with NRC 0x22 (conditionsNotCorrect)**
```
Root Cause: Programming preconditions not met.
Check:
  a. Vehicle speed > 0? (flashing only allowed at standstill) → signal VehicleSpeed on CAN
  b. Battery voltage too low (often < 11.5 V)? → ADC measure or UDS read DID 0xF186
  c. Engine running? → some ECUs block flash while engine on
  d. Wrong sequence: entered Ext session? → must enter Extended before Programming

Debug: Read 0x22 DID 0xF186 (Active Diagnostic Session) → confirm current session
       Read 0x22 DID 0xF441 (Voltage status) → check precondition
```

**Case 2: Security Access (0x27) fails with NRC 0x35 (invalidKey)**
```
Root Cause: Key algorithm mismatch between tester and ECU.
Debug:
  1. Capture seed from ECU: 0x27 01 → response: 67 01 AA BB CC DD (seed bytes)
  2. Calculate expected key using documented algorithm
  3. Compare with what your tester tool is sending (Wireshark/CANoe trace)
  4. Common issues:
     - Wrong XOR mask in key algorithm
     - Seed/key byte order reversed (Intel vs. Motorola)
     - Wrong seed length expected (2 bytes vs. 4 bytes)
```

**Case 3: 0x34 (Request Download) rejected with NRC 0x31 (requestOutOfRange)**
```
Root Cause: Start address or memory length not in ECU's accepted flash region.
Debug:
  1. Verify flash region definition in ECU's boot software (FBL) configuration
  2. Check hex file memory map: confirm start address matches FBL region
  3. Common: application .hex starts at 0x00000000 but ECU FBL only accepts 0x00008000+
  Fix: correct hex file load address in build system
```

**Diagnostic Checklist Table:**

| NRC Received | Service | Likely Cause | Debug Action |
|-------------|---------|-------------|-------------|
| 0x22 | 0x10 03 | Preconditions (speed, voltage, session) | Check preconditions; verify Extended session entered first |
| 0x35 | 0x27 02 | Wrong security key | Verify key algorithm; check byte order |
| 0x36 | 0x27 01 | Attempt limit exceeded (locked out) | Wait 10 min (lockout timer); do NOT keep trying |
| 0x31 | 0x34 | Wrong memory region | Verify hex start address vs. FBL config |
| 0x70 | 0x34 | Not in programming session | Enter 0x10 03 first |

**Key Points ★**
- ★ Never brute-force Security Access — after 3 failed key attempts, the ECU locks for minutes; in some implementations, permanently requires dealer unlock.
- ★ Always document the exact UDS sequence (with raw hex bytes) in the defect report — this is reproducible evidence.
- ★ Programming preconditions are often undocumented — reverse-engineer them by reading all DTCs and active DIDs before attempting flash.

---

## Q30: How do you debug a gateway not routing signals correctly between two ECUs?

### Question
The Cluster shows incorrect engine RPM. The RPM is correct on PT-CAN but wrong when received by the Cluster on Body-CAN (after gateway conversion). How do you debug this?

### Detailed Answer

**Architecture:**
```
Engine ECU → PT-CAN → Gateway ECU → Body-CAN → Instrument Cluster
  0x316 msg               routing              0x210 msg (different ID after routing)
  RPM raw: 0x1770         table               RPM raw: 0x1770 (should be same value)
  Factor: 0.25 rpm/bit                         Factor: 0.25 rpm/bit
  Value: 1500 rpm (expected)                   Value: ??? (bug found here)
```

**Step 1: Verify source signal on PT-CAN**
```
CANoe Channel 1 (PT-CAN):
  Message 0x316, Byte 2-3: 0x17 0x70 → raw = 0x1770 = 6000
  Value: 6000 × 0.25 = 1500 RPM ✓ Correct
```

**Step 2: Verify destination signal on Body-CAN**
```
CANoe Channel 2 (Body-CAN):
  Message 0x210, Byte 0-1: 0x70 0x17 → raw = ?
  
  If gateway applied Motorola-to-Intel byte swap:
    0x70 0x17 decoded as Intel little-endian = 0x1770 = 6000 × 0.25 = 1500 ✓
    
  If gateway FORGOT byte swap:
    0x70 0x17 decoded as-is: 0x7017 = 28695 × 0.25 = 7173 RPM ✗ WRONG!
```

**Root Cause: Gateway routing table has wrong byte order configuration for RPM signal.**

**Step 3: Gateway Routing Table Check**
```
Gateway Routing Table Entry (from SW configuration):
  Source:      PT-CAN, 0x316, Bits 16-31, Factor 0.25, Intel LE
  Destination: Body-CAN, 0x210, Bits 0-15, Factor 0.25, Motorola BE ← BUG: should be Intel LE
  
Fix: Change destination byte order to Intel LE (matching source)
```

**Step 4: Automated Validation via CANoe Multi-Channel CAPL**
```capl
// Validate gateway routing: PT-CAN signal == Body-CAN signal
on message CAN1.0x316 {   // PT-CAN RPM message
  float rpm_source = (this.byte(2) | (this.byte(3) << 8)) * 0.25;
  
  on message CAN2.0x210 {   // Body-CAN RPM (after gateway)
    float rpm_dest = (this.byte(0) | (this.byte(1) << 8)) * 0.25;
    float diff = abs(rpm_source - rpm_dest);
    if (diff > 5.0) {  // tolerance: 5 RPM
      write("GATEWAY ERROR: RPM PT-CAN=%.0f Body-CAN=%.0f diff=%.0f", 
            rpm_source, rpm_dest, diff);
      testStepFail("Gateway RPM routing");
    }
  }
}
```

**Key Points ★**
- ★ Byte order (endianness) mismatch in gateway routing is the #1 cause of wrong values across protocol domains.
- ★ Always validate BOTH source and destination simultaneously — having a correct source value doesn't guarantee correct routing.
- ★ Automate gateway validation with a multi-channel CANoe setup — manually comparing hex dumps is error-prone.

---

## Q31: How do you debug a tell-tale that flickers unexpectedly?

### Question
The Check Engine (CEL) tell-tale on the Cluster flickers ON and OFF every few seconds during driving. Describe your diagnosis.

### Detailed Answer

**Possible Root Causes for Flickering Tell-Tale:**

| Cause | Likelihood | Diagnosis |
|-------|-----------|-----------|
| CAN signal toggling | High | Trace CAN message; check if MIL signal toggles at same rate as flicker |
| CAN signal timeout → default ON → signal resumes → default OFF cycle | High | Check if CAN Tx ECU is dropping frames; measure cycle time |
| Software logic: DTC clearing + re-triggering rapidly | Medium | Read DTC list — is P0300 appearing/disappearing? |
| Check Engine signal incorrectly mapped (two sources) | Medium | Verify only one ECU sends the MIL active bit |
| NVM write/read race condition | Low | Only occurs in specific engine transients |

**Step 1: CANoe — Signal Trace Analysis**
```
Filter: Message containing MIL_Active signal
Graphic window: plot MIL_Active signal over time

Observation: MIL_Active = 0, 0, 1, 0, 1, 0, 1 → toggling every 2 frames (20 ms)

→ TWO ECUs are sending the same CAN message ID 0x500 with different values:
  ECU-A sends: 0x500 byte 4 = 0x00 (MIL = 0)
  ECU-B sends: 0x500 byte 4 = 0x08 (MIL = 1)
  Both at 10 ms; alternating → Cluster receives alternating values → flicker

Root Cause: Conflicting message transmitters — ECG (Engine Control) and BCM both 
           transmitting 0x500 (DBC configuration error; BCM should have different ID).
```

**Fix:** Update BCM's CAN message assignment so it no longer transmits 0x500; BCM uses new ID 0x501 for its signals.

**Step 2: If single ECU — DTC instability**
```
Service 0x19 02 A0 (read DTCs with status: pending)
  Monitor for DTC P0300 (random misfire):
    Status: 0x09 = confirmed + pending (oscillating between pending and confirmed)
    → Engine misfire intermittent → DTC sets then clears rapidly
    → MIL logic: MIL ON when DTC confirmed; OFF when DTC cleared
    → Appears to the driver as flicker
```

**Key Points ★**
- ★ Two ECUs transmitting the same CAN message ID is a critical configuration error and will fail ASPICE audit.
- ★ Use CANoe "duplicate ID detection" feature to catch this automatically.
- ★ Always check "how many ECUs transmit this message?" before debugging software — network-level conflicts are invisible in code review.

---

## Q32: How do you analyse ECU performance issues using Lauterbach Trace32?

### Question
The ADAS ECU's sensor fusion task is reported to take 12 ms (spec: ≤ 10 ms). How do you profile CPU task execution time?

### Detailed Answer

**Lauterbach Trace32 Setup for Task Profiling:**

```
Trace32 → connect JTAG to ECU debug port (AURIX: DAP or OCDS)
         → halt CPU
         → load ELF file (with debug symbols: -g flag in build)
         → run target
```

**Method 1: RTOS Task Monitor**
```
If AUTOSAR/FreeRTOS:
  Trace32 → RTOS awareness plugin (e.g., AUTOSAR OSEK plugin)
  → sYmbol.Browse RTOS \Task
  → Shows all tasks: name, priority, state, CPU time, deadline misses

  SensorFusionTask:
    State: RUNNING
    Priority: 10
    Activation rate: 10 ms
    Last exec time: 12.3 ms ← VIOLATING 10 ms deadline
    Deadline misses: 47 (in last 1000 activations)
```

**Method 2: Cycle Count Measurement (GPIO toggle)**
```c
/* In ECU C code (debug build only): */
#define PERF_MEAS_START()  GPIO_WRITE(DEBUG_PIN_1, HIGH)
#define PERF_MEAS_END()    GPIO_WRITE(DEBUG_PIN_1, LOW)

void SensorFusionTask(void) {
  PERF_MEAS_START();
  // ... all fusion processing ...
  PERF_MEAS_END();
}

// Oscilloscope on DEBUG_PIN_1: pulse width = exact execution time
```

**Method 3: Trace32 Runtime Measurement**
```
Trace32 command:
  PERF.METHOD TASK       // profile at task level
  PERF.Reset
  PERF.Gate ON           // start measurement
  Go
  // wait 1 s
  Break
  PERF.List              // list all functions by CPU time

  Results:
    SensorFusionTask      60.2 %   (12 ms out of 20 ms slot = 60%)
    KalmanFilter_Update   35.1 %   ← hotspot
    ObjectAssociation     18.3 %   ← secondary hotspot
    ...
```

**Finding:** `KalmanFilter_Update` takes 7 ms alone — uses `cos()/sin()` from standard math library (floating-point operations).

**Fix:** Replace standard `cos()/sin()` with a lookup table or CORDIC hardware accelerator on AURIX.

**Post-fix measurement:** SensorFusionTask exec time = 8.4 ms → within 10 ms spec.

**Key Points ★**
- ★ Always profile before optimizing — the 20% of code causing 80% of execution time is almost never where you expect.
- ★ GPIO toggle measurement is the most hardware-accurate method — nanosecond precision, no JTAG overhead.
- ★ Floating-point `cos/sin` in tight real-time loops is a classic automotive performance anti-pattern — always use integer math or lookup tables.

---

## Q33: How do you debug an ECU that randomly resets (watchdog reset)?

### Question
The Infotainment ECU randomly reboots (screen blinks off and comes back) during driving. Suspected watchdog reset. How do you diagnose?

### Detailed Answer

**Watchdog Reset Mechanisms:**
1. **Hardware watchdog**: if CPU doesn't kick the WDT within the window → hardware forces reset. Prevents infinite loops/hangs.
2. **Software watchdog (AUTOSAR WdgM)**: monitors task alive signals; if a task stops reporting → WdgM triggers reset.
3. **Voltage monitor**: if VCC drops below threshold (e.g., brownout at engine crank) → power-on-reset circuit triggers.

**Step 1: Read Reset Cause from ECU**
```
UDS Service 0x22 DID 0x3001 (Reset Cause, if implemented):
  Response: 0x62 30 01 04
  0x04 = WATCHDOG_RESET (according to DID definition)
  
Also check DTCs:
  0x19 02 FF → DTC 0xD1200: WatchdogManager_Reset (Confirmed, 12 occurrences)
```

**Step 2: Read Watchdog Reset Log from NVM**
```
DID 0x3010: Last WDT reset timestamp
DID 0x3011: Last WDT expired task name (if AUTOSAR WdgM supervisor mode)
  Response: "NavRenderer" → navigation rendering thread was the stuck task
```

**Step 3: Android logcat Analysis (if infotainment)**
```bash
grep -E "watchdog|reboot|runtime_restart|system_server.*died" logcat.txt

# Common findings:
01-15 16:30:11 W Watchdog: *** WATCHDOG KILLING SYSTEM PROCESS: android.io
01-15 16:30:11 W Watchdog: android.io (android.io) blocked for 35+ seconds on:
01-15 16:30:11 W Watchdog:   at android.database.sqlite.SQLiteConnection.nativeExecute
# → SQLite database write is blocking android.io thread → system watchdog kills and reboots
```

**Root Cause:** Navigation app writes large map cache to SQLite during driving. NDK layer takes 35 s for the write → Android system watchdog kills system_server → reboot.

**Fix:** Move SQLite writes to background thread with async handler. Do not block main android.io thread.

**Step 4: Voltage Brownout Check**
```
During engine crank:
  Battery voltage dips: 14.4 V → 8.5 V (crank transient) → 14.4 V
  If HU power supply PSRR inadequate: HU VCC dips below 3.0 V → hardware reset

Test with oscilloscope: measure HU VCC rail during crank simulation
If VCC < 2.7 V: add bulk capacitor on HU power input, or improve PMIC hold-up time
```

**Key Points ★**
- ★ Before debugging software, always rule out hardware (voltage brownout) — a software fix won't solve a power supply problem.
- ★ AUTOSAR WdgM task name logging is invaluable — insist that every production ECU has WDT logging enabled.
- ★ Android system watchdog (30 s for android.io) is very strict — all I/O operations in Android infotainment must be asynchronous.

---

## Q34: How do you build and manage a defect triage process for a large test team?

### Question
You are managing a test team of 12 engineers. Every day, 20+ new defects are raised. How do you manage defect triage efficiently?

### Detailed Answer

**Defect Triage Process:**

```
Daily Triage Meeting: 30 minutes, every morning
Attendees: Test Lead + 2 Senior Testers + Dev Lead + PM (optional)
Input: All defects raised since last triage (JIRA filter: created > yesterday)

For each defect:
  1. Validity: Is it a real defect or test environment issue?
     → Test env issue: label "Test_Env"; reassign to tester for re-test on clean env
     → Duplicate: mark duplicate; link to original
     → Real defect: continue

  2. Severity classification:
     P1 (Critical): Safety, data loss, blocking all testing
     P2 (High): Major feature broken, no workaround
     P3 (Medium): Feature partially broken, workaround exists
     P4 (Low): Cosmetic, typo, minor UX

  3. Module assignment: assign to responsible developer/team
  4. Target milestone: which sprint/build will fix be in?
  5. Workaround: can testing continue? If no → flag as blocker
```

**JIRA Dashboard (Real-Time Visibility):**

| Metric | Target | Actions if Exceeded |
|--------|--------|-------------------|
| Open P1 defects | = 0 at sprint end | Daily standup escalation; Dev pair programming on P1 |
| Open P2 defects | ≤ 5 at sprint end | Prioritize in next sprint's developer workload |
| Defect arrival rate (new/day) | Monitor trend: is it declining? | If rising in regression phase: sign of inadequate fix verification |
| Average P1 fix time | ≤ 2 days | SLA tracked; escalate to Dev manager if missed |
| Defect escape rate (field bugs vs. found in test) | ≤ 5% | Root cause: missed in test → add test case |
| Defect open > 10 days (aging) | ≤ 3 | Weekly aging review; owner follow-up |

**Key Triage Rules:**
1. Never close a defect without retest by independent tester (not the reporter).
2. No defect is P1 by default — validated severity by triage committee, not by individual tester.
3. Defect in "Fixed" state without a fix commit reference is not acceptable.
4. Every P1 defect requires a documented root cause + CAPA (Corrective and Preventive Action).

**Key Points ★**
- ★ Triage must be daily during active testing — a 3-day-old P1 is exponentially more expensive to fix than same-day triage.
- ★ Defect aging metrics are more important than total open count — old defects represent debt accumulating toward SOP.
- ★ Assign every defect a clear owner and ETA at triage — unowned defects never get fixed.
