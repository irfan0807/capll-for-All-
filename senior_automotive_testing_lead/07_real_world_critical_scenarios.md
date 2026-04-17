# Section 7: Real-World Critical Failure Scenarios
> **Role**: Senior Automotive Testing Team Lead | **Questions**: Q59–Q64

---

## Q59: ADAS AEB triggers a false alarm at 80 km/h — How do you investigate?

### Scenario
**Customer report:** Vehicle brakes hard (AEB activation) on a highway with no obstacle present. Driver narrowly avoids rear-end collision from following car. High-severity field issue. Your team leads the investigation.

### Detailed Investigation Approach

**Immediate Data Collection:**

```
Data needed from affected vehicle:
  1. EDR (Event Data Recorder) / DSSAD (Data Storage for ADAS):
     - Host speed at time of event
     - AEB activation flag: ON
     - Radar object list at T-2 to T+2 seconds
     - Camera detection output at T-2 to T+2 seconds
     
  2. CANoe trace (if data logger installed):
     - Radar raw object data
     - Sensor fusion output (fused object list)
     - AEB algorithm input/output
     
  3. Metadata:
     - Weather: was it raining? (radar multipath reflections)
     - Road: was there a metal bridge overhead? (radar false echo)
     - Other vehicles: large truck in adjacent lane? (radar side-lobe leakage)
```

**Root Cause Categories for False AEB:**

| Category | Root Cause | Test to Confirm |
|---------|-----------|----------------|
| Radar false target | Metal bridge, overhead sign, guard rail detected as vehicle | Replay with known false-target scenario on HIL |
| Low-speed filter misfire | Filter designed to remove stationary objects failed for slow-moving vehicle (stopped truck) | Test: stationary target at 0 km/h on HIL |
| Sensor fusion error | Camera and radar disagreed; fusion incorrectly validated radar false target | SIL: inject conflicting sensor data |
| Calibration error | Radar pointing down (pot-hole damage) → detects road surface as approaching target | Re-calibrate; UDS DID read mounting parameters |
| SW regression | Threshold tuning changed in latest release | Compare algorithm parameters between last-known-good and affected version |

**Reproduction on HIL:**
```
Scenario replayed on dSPACE SCALEXIO:
  T=0:   Host speed = 80 km/h; clear road
  T=0.2: Inject radar ghost target: 30 m ahead, 0 km/h (simulating metal bridge)
  T=0.4: AEB algorithm receives ghost target; TTC = 30m / (80/3.6) = 1.35 s
  T=0.6: AEB activates → braking output
  
Confirmed: same sequence as field event ← root cause confirmed
```

**Fix:**
- Radar algorithm: add stationary object filter for objects with zero Doppler velocity (not moving) at speeds > 60 km/h on motorway.
- Camera cross-validation mandatory: AEB only activates if camera ALSO confirms object (current version: camera optional for confirmation).
- Regression test: 1000 scenarios on SIL with stationary-object scenarios at various speeds.

**Key Points ★**
- ★ False AEB activations are a safety critical failure (can cause rear-end collision) — treat them as ASIL violation until proven otherwise.
- ★ EDR/DSSAD data is the most reliable evidence — always request it before forming any hypothesis.
- ★ The fix must not over-correct: increasing false-negative rate (missing real obstacles) while reducing false-positive is equally dangerous.

---

## Q60: Infotainment crashes during active navigation — How do you handle?

### Scenario
**Customer report:** Navigation app crashes randomly during active turn-by-turn guidance. The display goes black for 8 seconds, then reboots. Reported by 15 customers.

### Detailed Investigation

**Step 1: Collect crash evidence**
```bash
# Pull tombstone (native crash dump):
adb pull /data/tombstones/tombstone_00 .
adb pull /data/tombstones/tombstone_01 .

# Check tombstone content:
cat tombstone_00
```

```
*** *** *** *** *** *** *** *** *** *** *** *** ***
Build: OEM_IHU_v4.1.1 / Qualcomm SA8155P
pid: 4321, tid: 4356, name: GLThread  >>> com.oem.navigation <<<
signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x00000000 ← NULL pointer

backtrace:
  #00 pc 00234ab0  /system/lib64/libmapengine.so (MapRenderer::renderTile+0x234)
  #01 pc 00876fdc  /system/lib64/libmapengine.so (TileCache::getOrLoadTile+0x158)
  #02 pc 00123dc4  /data/app/com.oem.navigation/lib/arm64/libnavapp.so (NavigationView::onDraw+0x88)
  #03 pc 004512a0  /system/lib64/libandroid.so (android::Surface::perform+0x44)
```

**Root Cause from Tombstone:**
- `MapRenderer::renderTile` crashes with SIGSEGV fault address 0x0 → NULL pointer dereference.
- `TileCache::getOrLoadTile` returned null tile; caller did not check for null before use.
- Crash occurs on GL rendering thread (GLThread) during active map draw.

**When does this happen?**
- Navigate for > 20 min → tile cache eviction starts.
- New tile loaded → simultaneous: current tile being rendered.
- Race condition: tile evicted from cache while render thread still has a pointer to it → null deref.

**Fix:** Add null-check + mutex lock in `TileCache::getOrLoadTile`: ensure tile not evicted while rendering thread holds a reference.

**Validation Test:**
```python
# Automated stress test: trigger rapid tile loading/unloading
# via ADB and navigation simulation
import subprocess, time

def stress_nav_tiles():
    # Simulate rapid route changes (forces tile invalidation)
    subprocess.run(['adb', 'shell', 'am', 'start', '-n', 'com.oem.navigation/.MainActivity',
                    '--es', 'destination', 'A'])
    time.sleep(5)
    subprocess.run(['adb', 'shell', 'am', 'start', '-n', 'com.oem.navigation/.MainActivity',
                    '--es', 'destination', 'B'])
    time.sleep(5)
    # check for crashes
    result = subprocess.run(['adb', 'shell', 'ls', '/data/tombstones/'], capture_output=True)
    return 'tombstone' in result.stdout.decode()

for i in range(50):
    if stress_nav_tiles():
        print(f"CRASH at iteration {i}")
        break
else:
    print("PASS: 50 iterations without crash")
```

**Key Points ★**
- ★ Every native crash in Android automotive infotainment leaves a tombstone — always pull it before any analysis.
- ★ Thread-safety bugs (race conditions) in tile rendering are very common and only manifest under memory pressure — soak testing is essential.
- ★ The race condition fix must be validated with multithreaded stress testing, not just happy-path test.

---

## Q61: Cluster displaying wrong vehicle speed — Safety-critical investigation

### Scenario
**Field report:** 5 vehicles showing incorrect speed on the cluster — speedometer reads 120 km/h when actual speed is 60 km/h.

### Investigation

**Hypothesis 1: CAN signal factor error**
```
CAN DBC defines VehicleSpeed:
  Factor: 0.01 km/h/bit → 60 km/h = raw 6000
  
Bug scenario: cluster using Factor 0.02 (double) → 6000 × 0.02 = 120 km/h (exactly 2×)
  THIS matches the field report: reading is exactly 2× correct value
```

**Evidence collection:**
```
CANoe on affected vehicle:
  Message 0x3B4 at 60 km/h:
    Raw byte: 0x17 0x70 → Intel LE: 6000
    Expected decoded: 6000 × 0.01 = 60.0 km/h ← correct
  
  Simultaneously: display shows 120 km/h

  → CAN signal is correct (60 km/h); Cluster display is wrong (120 km/h)
  → Issue is in Cluster SW (not CAN source)
```

**Root Cause:**
```
Cluster EWS (Engine Wheel Speed) integration:
  Previous SW (v3.0): used VehicleSpeed signal (0x01 = 0.01 km/h)
  New SW (v3.1):      changed to use WheelSpeedRear signal (0x01 = 0.02 km/h — different DBC, different factor)
  But: gauge display code NOT updated for new factor → still divides by 100 (not 50)
  
Result: WheelSpeedRear raw × 0.02 × display_scale_100 = 2× over-read
```

**Root Cause: DBC integration change not fully propagated to display rendering code. Code review missed display layer update.**

**Fix:** Update Cluster display rendering formula for WheelSpeedRear signal factor (0.02 → 100 display units per km/h).

**Preventive Actions:**
- Add automated regression: every build, test speed at 5 known exact values (10, 30, 60, 100, 120 km/h) and verify ±1 km/h accuracy.
- DBC change control: any DBC signal factor change triggers notification to all ECU teams using that signal.

**Key Points ★**
- ★ "Exactly 2× wrong" immediately suggests a factor/scaling error — use the mathematical relationship to narrow the hypothesis quickly.
- ★ Measuring CAN signal (correct) vs. display (wrong) independently is the key diagnostic step that proven the issue is in the Cluster SW.
- ★ DBC changes without full impact analysis are one of the most common root causes of automotive field defects.

---

## Q62: TCU does not send eCall (emergency call) in accident scenario

### Scenario
**Safety audit finding:** In a controlled crash test, the eCall was not initiated within the required 2 seconds. The vehicle passed the Euro NCAP star assessment criteria test previously.

### Investigation

**eCall Activation Flow:**
```
Crash event (airbag deployment / acceleration threshold)
    ↓ <100 ms
Crash sensor sends CAN: 0x440 CrashSeverity = HIGH_FRONT
    ↓
TCU receives CAN event → eCall activation logic triggered
    ↓ <200 ms
TCU dials 112 (E-UTRAN, VoLTE)
    ↓ <3 s total from crash
PSAP (Public Safety Answering Point) answers → MSD transmitted
```

**Step 1: CAN trace at time of crash test**
```
CANoe trace: 0x440 transmitted at T=0.000
  CrashSeverity = HIGH_FRONT = 0x03

TCU CAN Rx: 0x440 received at T=0.002 ✓
  Expected: eCall trigger at T=0.002
  Actual: No eCall trigger visible in trace
  
UDS diagnostics on TCU:
  DTC 0xE0001: eCall_trigger_timeout — confirmed
```

**Step 2: TCU eCall logic investigation**
```
eCall trigger condition in TCU SW (from code review):
  if (CrashSeverity >= THRESHOLD_HIGH && GNSSValid == TRUE && BatteryVolt > 10.5V) {
    initiateECall();
  }

Issue found:
  Crash test: conducted in underground facility → GNSS signal unavailable (GNSS_Valid = FALSE)
  
  BUT: EN 15722 (eCall standard) and the vehicle's SRS say:
       "eCall shall be initiated regardless of GNSS validity. GNSS is used for MSD; 
        if unavailable, last known position is used."
  
  Bug: Developer incorrectly added GNSSValid as a mandatory prerequisite for eCall.
  Previous Euro NCAP test: conducted outdoors → GNSS valid → test passed
  Audit test: underground → GNSS invalid → eCall blocked
```

**Fix:** Remove `GNSSValid` as mandatory condition. Retain last-known GPS coordinates for MSD; if unavailable, MSD transmitted with CouldBeInaccurate flag set.

**Critical Lesson:**
This is a safety-critical defect: ISO 26262 ASIL-B violation (eCall non-activation = potential loss of life).
- Triggers formal safety incident report.
- Root cause shared with entire team.
- Test coverage update: eCall tests replayed in GNSS-denied environment.

**Key Points ★**
- ★ eCall must function in environments where the crash is likely to occur — including tunnels, parking structures, and areas with no GNSS. Always test in GNSS-denied conditions.
- ★ A P1 safety defect that passed in one environment (Euro NCAP) but fails in another is the most dangerous type of gap — test environment coverage is critical.
- ★ Every safety requirement precondition must be justified in the Safety Concept — any precondition that can prevent a safety function must be explicitly threat-analyzed.

---

## Q63: OTA update bricks an ECU — Response and recovery

### Scenario
**Field event:** 200 vehicles received an OTA update for the ADAS ECU. After update, 12 vehicles have unresponsive ADAS ECU (no CAN traffic, no UDS response). The ADAS system warning is ON in all 12 vehicles. Production escalation.

### Response

**Immediate Actions (within 1 hour):**
1. **Halt OTA campaign**: suspend further rollout immediately via OEM OTA backend.
2. **Protect remaining 188 vehicles**: mark campaign as suspended; vehicles do not attempt download.
3. **Assess affected vehicles**: 12 vehicles with bricked ECU.

**Step 1: Determine bricking mechanism**
```
Possible causes:
  A. Flash corruption: write interrupted; application code corrupt → ECU boots to FBL, 
     FBL cannot jump to app → ECU stuck in bootloader
  B. Wrong image: incompatible firmware flashed to hardware variant B (there are 2 HW variants)
  C. Power loss during flash: vehicle's 12V dropped during write → incomplete write
  D. Memory map conflict: new SW's memory layout overlaps with FBL reserved area → overwrite FBL
```

**Step 2: UDS attempt on affected ECU**
```
Try: 0x10 01 (default session) on ADAS CAN address 0x7E0
  If no response → ECU not running application (bricked or stuck in FBL)

Try: 0x10 01 on FBL address (if separate address, e.g., 0x640)
  Response received! → ECU is alive in FBL mode
  
  Read: 0x22 F1 86 (active session): response: 02 (FBL mode) ← confirmed FBL active
  Read: 0x22 F1 01 (SW version): "FBL v2.1 — App: NOT VALID" ← confirms app image invalid
```

**Root Cause: Wrong memory map checksum block (cause D):**
```
New SW v4.2.0 linker script error: application start address = FBL_END - 0x100
  Overwrote last 256 bytes of FBL area during flash
  FBL self-integrity check on next boot failed → FBL refuses to start application
  ECU stuck in FBL loop
```

**Recovery:**
```
Recovery Procedure (per affected vehicle):
  1. Connect via DoIP/CAN diagnostic tool (tester)
  2. Enter FBL programming session: 0x10 03 (FBL address 0x640)
  3. Security Access 0x27 01/02 (FBL security key)
  4. Re-flash ENTIRE ECU with known-good image v4.1.0 (previous version):
     0x31 01 FF 00 (erase flash)
     0x34 / 0x36 / 0x37 (download v4.1.0)
     0x11 01 (reset)
  5. Verify: ECU boots to application v4.1.0; CAN traffic visible; ADAS functional
  6. Issue corrected OTA campaign (v4.2.1 with linker fix) to all 200 vehicles
```

**Prevention:**
- Add memory map overlap validation to OTA pre-check: before flashing, verify: new image start address ≥ FBL_END address.
- OTA canary deployment: deploy first to 10 vehicles; verify all recover within 10 minutes; proceed with full fleet.
- Linker script review: ASIL process review for all safety ECU linker scripts before SW sign-off.

**Key Points ★**
- ★ A/B partition (dual bank) flash would have prevented this entirely — the bricked bank would have been backup only; vehicle boots from known-good bank.
- ★ Canary deployment is mandatory for any OTA campaign: test on 10 vehicles, wait 1 hour, then roll out to fleet.
- ★ FBL recovery capability is a safety net that must always be preserved — the #1 rule of automotive flash: never overwrite the FBL.
