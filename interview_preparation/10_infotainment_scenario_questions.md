# 10 — Infotainment System Scenario-Based Interview Questions
## Automotive Test Validation Engineer — Interview Preparation

---

## What Is an Infotainment System?

An **In-Vehicle Infotainment (IVI)** system combines entertainment, navigation, connectivity, and vehicle information into a single HMI unit. Modern IVI systems are among the most complex ECUs in a vehicle — running full Linux/Android OS, managing multiple CAN/LIN/Ethernet networks, and interfacing with nearly every vehicle system.

**Key subsystems tested:**
- Head Unit (HU) — central display & processing
- Instrument Cluster (IC) — driver information display
- Rear Seat Entertainment (RSE)
- Telematics Control Unit (TCU)
- Bluetooth / USB / Wi-Fi / Apple CarPlay / Android Auto
- Navigation / GPS
- Voice Recognition (ASR)
- HVAC display integration
- Vehicle CAN signal display (speed, RPM, fuel, warnings)
- OTA (Over-The-Air) software updates

---

## SECTION 1 — CAN Signal Display & Cluster Integration

---

### Scenario 1.1 — Speed Not Displayed on Cluster

> **Interviewer:** "During testing, the driver's instrument cluster shows 0 km/h even though the vehicle is moving at 60 km/h. How do you approach this?"

**Strong Answer:**

"I would approach this systematically rather than jumping to a conclusion.

**Step 1 — Isolate the source:**
First, I open CANoe and check whether the VehicleSpeed CAN message is present on the bus. If the message is there and the value is correct (60 km/h), the problem is in the cluster side — either signal decoding, DBC mismatch, or display logic. If the message is missing or showing 0, the problem is in the sender ECU (ABS/WBS module).

**Step 2 — Check the CAN trace:**
```
- Message: VehicleSpeed_BC (0x3B0)
- Signal: VehicleSpeed — check raw value vs physical value
- Scaling mismatch? e.g., raw=600, scale=0.1 should give 60.0 km/h
- Check cycle time — is the message arriving every 10ms as specified?
- Check if message stopped after a certain time (timeout?)
```

**Step 3 — UDS diagnostic check:**
I send UDS 0x22 0xF40D to read the Vehicle Speed DID from the cluster ECU. If it returns 0 while CAN shows 60, the cluster is not reading the signal correctly. If it returns 60, the problem is in the display rendering layer.

**Step 4 — DTC check:**
0x19 02 08 — if a CAN signal timeout DTC is present on the cluster, the cluster may be in a fallback/limp mode showing 0 instead of the live value.

**Root cause possibilities:**
- Wrong DBC file loaded in cluster (scaling issue)
- CAN message ID changed in recent SW build (filter mismatch)
- Signal mux ID mismatch — speed is inside a multiplexed message
- Display SW bug — value received but not rendered"

---

### Scenario 1.2 — RPM Gauge Jumps Erratically

> **Interviewer:** "The RPM gauge on the instrument cluster jumps between 800 and 2500 rpm randomly while the engine is idling at a steady 850 rpm. What do you investigate?"

**Strong Answer:**

"This pattern — a steady physical value with erratic display — points to a signal integrity or filtering problem.

**Investigation path:**

1. **Confirm the engine is actually steady:** Check ECM output via OBD-II (0x22 0x0C = Engine RPM). If ECM reports steady 850, the problem is between ECM and cluster.

2. **Check CAN bus for noise:**
   - In CANoe, enable error frame logging
   - Look for CRC errors, stuff errors on the RPM message
   - A noisy CAN bus causes bit errors that flip signal values

3. **Check message cycle time consistency:**
   - RPM message should arrive every 10ms
   - If some frames arrive late (20ms gap) then burst (5ms gap) due to bus load, some IVI systems misinterpret this

4. **Check if it's a different source:**
   - Some clusters receive RPM from both ECM (CAN) and a direct tacho signal
   - Signal source arbitration logic could be switching between them

5. **CAPL test to reproduce and isolate:**
```capl
// Inject controlled RPM signal and observe cluster behaviour
variables {
  message EngineStatus_BC msgEng;
  msTimer tmrRPM;
  int gRpmValue = 850;
  int gNoise = 0;
}

on start {
  setTimer(tmrRPM, 10);
}

on timer tmrRPM {
  // Inject clean steady 850 RPM — does cluster still jump?
  msgEng.Engine_RPM = gRpmValue;
  output(msgEng);
  setTimer(tmrRPM, 10);
}

// Press 'N' to inject noise burst (simulate CAN error recovery)
on key 'N' {
  msgEng.Engine_RPM = 2500;  // spike
  output(msgEng);
  delay(5);
  msgEng.Engine_RPM = 850;   // back to normal
  output(msgEng);
  write("Noise burst injected");
}
```

If the cluster jumps when we inject a single spike, the cluster lacks signal filtering — a SW defect. If it doesn't jump with clean injection, the problem is on the CAN bus (noise, errors)."

---

### Scenario 1.3 — Fuel Bar Shows Wrong Level

> **Interviewer:** "Customer reports that the fuel bar shows Full even after driving 200km. Fuel sensor is confirmed working. Where is the fault?"

**Strong Answer:**

"This is a classic signal path problem. The fuel sensor works but the display is wrong — so the fault is somewhere in the chain between sensor and display.

**Signal path:**
```
Fuel Tank Sensor (resistive)
    → BCM/FMS (Fuel Monitoring System) — converts resistance to litres
    → CAN message: FuelLevel_BC (0x3C0), signal: FuelLevel_Litres
    → Cluster ECU — receives CAN, maps to bar display
    → Display rendering
```

**Investigation:**

1. **Read fuel level via UDS from BCM:**
   - `0x22 0x2F03` → if BCM reports correct 30L (not full), fault is after BCM

2. **Check CAN message:**
   - Is `FuelLevel_BC` being sent with correct value?
   - What is the signal scaling? `raw × 0.1 = litres` — if scale is `raw × 1.0`, 300 raw would show as 300L (out of range → clamped to full)

3. **Check cluster's DID for fuel:**
   - `0x22 0xF43C` → what does cluster think the fuel level is?

4. **Common root causes in IVI/cluster:**
   - Scaling mismatch after SW update (BCM changed unit from 0.5L steps to 0.1L steps)
   - Cluster has `if fuel > max_tank → display = Full` logic — wrong max_tank calibration value
   - Signal offset wrong: `FuelLevel = raw_value + offset` — if offset = +200, always reads full

5. **Test case I would write:**
```
TC_FUEL_DISPLAY_001:
  Inject FuelLevel_BC with value = 30L (30% of 80L tank)
  Expected: Cluster shows ~37% bar (3/8 segments)
  Actual: Monitor cluster display signal via UDS 0x22

TC_FUEL_DISPLAY_002:
  Inject FuelLevel_BC with value = 0L (empty)
  Expected: Empty bar + low fuel warning icon
  Actual: Observe and compare
```"

---

## SECTION 2 — Multimedia & Connectivity

---

### Scenario 2.1 — Bluetooth Audio Cuts Out at Highway Speed

> **Interviewer:** "Customer reports Bluetooth audio cuts out intermittently while driving on the highway at 100+ km/h. It works fine in the city. What could cause this and how do you test it?"

**Strong Answer:**

"Speed-dependent Bluetooth dropout is a well-known pattern. The speed itself doesn't affect Bluetooth (2.4GHz RF), but several vehicle-speed-correlated factors do.

**Hypotheses ranked by likelihood:**

1. **Antenna placement / interference from rotating parts:**
   - At highway speed, frequency inverters in the motor (EVs/hybrids) generate high-frequency EMI
   - EMI at 2.4GHz band can interfere with Bluetooth
   - Test: use a spectrum analyser at 2.4GHz while driving — look for interference spikes correlated with motor RPM

2. **Active Noise Cancellation (ANC) conflicting with A2DP audio:**
   - At highway speed, the infotainment activates ANC — some HU SW bugs cause the ANC DSP to corrupt the Bluetooth audio buffer
   - Test: disable ANC feature flag via UDS 0x2E, repeat highway test

3. **MOST/Ethernet bus load at speed:**
   - Navigation map rendering at high speed (frequent tile updates) may saturate the internal bus
   - IVI SW may drop audio frames when bus load > threshold
   - Test: disable navigation display while driving, check if dropout stops

4. **CAN signal-triggered bug:**
   - Some IVI systems enter a different audio mode when speed > 80 km/h (e.g., speed-compensated volume)
   - If the speed-compensated volume feature has a SW bug, it could corrupt audio stream
   - Test: inject CAN speed = 110 km/h in a static lab bench — reproduce dropout without physically driving

**CAPL test to reproduce in lab:**
```capl
// Simulate highway speed to trigger speed-dependent IVI behaviour
variables {
  message VehicleSpeed_BC msgSpeed;
  msTimer tmrRamp;
  float gSpeed = 0;
}

on start {
  setTimer(tmrRamp, 100);
}

on timer tmrRamp {
  gSpeed += 5.0;
  if (gSpeed > 140) gSpeed = 0;  // cycle 0-140 km/h

  msgSpeed.VehicleSpeed = gSpeed;
  output(msgSpeed);

  if (gSpeed >= 100) {
    write("Highway speed active: %.0f km/h — observe Bluetooth audio", gSpeed);
  }
  setTimer(tmrRamp, 500);
}
```

If the audio drops in the lab at the simulated speed signal, the fault is purely software — no need to road test."

---

### Scenario 2.2 — Apple CarPlay Disconnects When Charging

> **Interviewer:** "Apple CarPlay disconnects every time the user plugs in their phone to charge via the USB port. It works fine without charging. What is the issue?"

**Strong Answer:**

"This is a classic USB power / data conflict scenario.

**Root cause analysis:**

The USB port in a vehicle handles both:
- **Data:** USB 2.0/3.0 data lines for CarPlay communication
- **Power:** 5V/2A or 5V/3A for charging

When a phone draws high charging current, it can cause:

1. **Voltage droop on VBUS:** If the USB power supply (DC-DC converter) is underpowered, charging current causes VBUS to drop below 4.75V — USB data connection drops (USB spec minimum is 4.75V)

2. **USB hub chip thermal throttling:** Some IVI USB hubs reduce data bandwidth when power draw increases — CarPlay requires minimum USB 2.0 bandwidth

3. **D+/D− line noise from charging circuitry:** Fast charger protocols (Qualcomm QC, PD) negotiate voltage by putting signals on D+/D− lines — this can momentarily interrupt CarPlay data signalling

4. **IVI SW power management:** Some IVI systems detect high current draw and software-switch the USB port to "charge only" mode — intentional but badly implemented

**Test steps:**

| Test | Method | Expected |
|------|--------|----------|
| Measure VBUS voltage | Oscilloscope on USB VBUS pin during charging | Should stay > 4.75V |
| Check USB data lines | Logic analyser on D+/D− during connect+charge | Should remain stable |
| Try USB isolator | Insert USB data+power isolator in line | If CarPlay stays stable, confirms charge noise on data lines |
| Disable fast charging | Force 5V/500mA (standard charge) via USB PD | Does CarPlay stay connected? |
| UDS 0x22 on IVI | Read USB port mode DID | Is IVI switching port to charge-only mode? |

**Defect classification:** Likely a power design deficiency (VBUS drop) or IVI SW bug (incorrect port mode switch). Log with oscilloscope screenshots of VBUS droop as evidence."

---

### Scenario 2.3 — Android Auto Screen is Black After SW Update

> **Interviewer:** "After a software update to the head unit, Android Auto connects (phone shows connected status) but the IVI screen stays black. Previous SW version worked fine. What do you do?"

**Strong Answer:**

"This is a regression introduced by the SW update — the connection handshake completes but video projection fails.

**Diagnosis path:**

1. **Confirm it's a regression:** Check `git diff` or SW release notes for changes in the USB/Android Auto stack. Did the update change: USB HAL, Android Auto protocol version, screen mirroring codec?

2. **Differentiate connection vs rendering:**
   - Phone shows 'Connected' = USB data link and protocol handshake OK
   - Black screen = video frame not rendered — problem in IVI display pipeline

3. **Check IVI logs (Android logcat if IVI runs Android):**
```bash
adb connect <IVI_IP>:5555          # connect via ADB over Ethernet
adb logcat | grep -i "carlife\|androidauto\|projection\|surface\|display"
# Look for: SurfaceFlinger errors, codec init failure, display mode mismatch
```

4. **Common causes after SW update:**
   - Display resolution/format changed: new SW sends 1920×720 but Android Auto still negotiating for 1280×720 — black screen while resolution mismatch
   - Video codec not initialised: if H.264 hardware decoder init fails silently, no video
   - Permission regression: new Android/Linux kernel update revoked a permission used by the projection app

5. **Workaround test:** Force restart of projection service via ADB:
```bash
adb shell am force-stop com.google.android.projection.gearhead
adb shell am start -n com.google.android.projection.gearhead/.MainActivity
```

6. **Test case for regression suite:**
```
TC_AA_001:
  Precondition: IVI SW v2.3 flashed, phone paired
  Steps:
    1. Connect phone via USB
    2. Android Auto launches (phone side)
    3. Observe IVI screen within 10 seconds
  Expected: Android Auto home screen visible on IVI
  Pass/Fail: Screenshot comparison vs baseline
  Must run: After EVERY head unit SW update (P0 regression)
```"

---

## SECTION 3 — Navigation & GPS

---

### Scenario 3.1 — Navigation Map Freezes at Tunnel Entry

> **Interviewer:** "Customer reports the navigation map freezes and stops updating position when the car enters a long tunnel. After exiting the tunnel it takes 3–5 minutes to recover. How do you investigate?"

**Strong Answer:**

"This is a GPS signal loss handling problem — the system should seamlessly use dead reckoning (DR) inside the tunnel and recover quickly on exit.

**Expected system behaviour (per spec):**
- GPS signal lost → Navigation uses Dead Reckoning (wheel speed + gyroscope + last known heading) to estimate position inside tunnel
- GPS signal acquired → Snap position to GPS, resume tracking

**Observed vs Expected:**
- Map freezes (stuck on last known position) → Dead Reckoning not working or not implemented
- 3–5 min recovery → GPS re-acquisition taking too long → possibly a cold start instead of hot start

**Investigation:**

1. **Check if Dead Reckoning is enabled:**
   - UDS 0x22 DID for Navigation mode — does it show DR_Active when GPS drops?
   - Check whether wheel speed CAN signal is connected to the navigation module

2. **Check GPS receiver behaviour:**
   - Inject GPS dropout in lab: connect RF signal generator, cut GPS signal, observe
   - Does IVI switch to DR mode within 2 seconds of GPS loss?

3. **Recovery time test:**
   - After GPS signal restored, how long until position lock?
   - Hot start (almanac valid) should be < 5 seconds
   - If taking 3–5 minutes, the GPS receiver is doing a cold start (almanac wiped)
   - Root cause: SW update cleared GPS almanac/ephemeris data in NVM

4. **CAN signal check:**
```capl
// Monitor GPS status and DR status during simulated tunnel
on signal Navigation::GPS_FixStatus {
  write("GPS Fix: %d (0=no fix, 1=fix, 2=DR)", this.value);
}

on signal Navigation::DR_Active {
  if (this.value == 1)
    write("Dead Reckoning ACTIVE — using wheel speed + gyro");
  else
    write("WARNING: DR not active despite GPS loss");
}
```

5. **Test cases:**
```
TC_NAV_001: GPS signal present → fix within 5s of ignition ON (hot start)
TC_NAV_002: GPS deliberately blocked → DR activates within 2s
TC_NAV_003: GPS restored after 60s blackout → position lock within 5s (hot re-acquire)
TC_NAV_004: Position accuracy in DR mode — drift < 50m over 500m travel
```"

---

### Scenario 3.2 — ETA Calculation Wrong on Motorway

> **Interviewer:** "Navigation ETA shows 45 minutes but it should be 25 minutes. Speed limit is 120 km/h and car is doing 110 km/h. The route is correct. What's wrong with the ETA?"

**Strong Answer:**

"ETA = remaining distance ÷ estimated average speed. If distance and route are correct, the issue is in the speed assumption.

**Hypotheses:**

1. **Navigation using wrong speed for calculation:**
   - Some navigation systems use legal speed limit from map data rather than actual vehicle speed
   - If map data has wrong speed limit (60 km/h instead of 120 km/h) → double the ETA
   - Test: What speed limit is shown on screen for the current road segment?

2. **Traffic data integration:**
   - Live traffic module may be injecting artificial congestion delay
   - If the connected services are showing congestion that doesn't exist, ETA inflates
   - Test: Disable live traffic → does ETA correct to 25 min?

3. **Speed source for ETA calculation:**
   - Navigation module may be reading speed from a different source than dashboard
   - If navigation reads from GPS speed (which can vary due to satellite geometry) vs CAN VehicleSpeed
   - At 110 km/h, GPS speed noise of ±5 km/h can meaningfully affect ETA over 30km

4. **Road type classification error:**
   - Navigation classified a motorway segment as an A-road (speed limit 70mph/113 km/h)
   - ETA calculated using 70 mph average instead of 120 km/h
   - Test: Zoom into map at current segment — what road type is shown?

5. **Test to reproduce:**
```
Drive conditions: Motorway A34, 50km remaining, no traffic
Step 1: Record displayed ETA
Step 2: Read map speed limit for current segment via diagnostic DID
Step 3: Read GPS speed vs CAN speed on CANoe
Step 4: Manually calculate: 50km ÷ 110km/h = 27 min (accounting for 2 traffic lights)
Step 5: Compare — where does the 45min come from?
```

**Most likely root cause:** Map database has outdated or incorrect speed limit for that road segment — a map data defect, not a SW defect. Raise with map data team (HERE, TomTom) with the specific road coordinates."

---

## SECTION 4 — HVAC & Vehicle Integration

---

### Scenario 4.1 — Climate Display Shows Wrong Temperature

> **Interviewer:** "The climate control panel on the infotainment screen shows 18°C but the actual cabin feels like 24°C. The HVAC ECU is physically setting the correct temperature. Where is the mismatch?"

**Strong Answer:**

"Classic display-vs-reality mismatch — the HVAC ECU is doing the right thing but the IVI is showing wrong information.

**Signal path:**
```
User input on IVI touchscreen
    → IVI sends CAN: HVAC_SetTemp_Req = 18°C
    → HVAC ECU receives request, sets actual temperature
    → HVAC ECU sends CAN: HVAC_ActualTemp_Cabin = 24°C (actual current cabin temp)
    → IVI receives HVAC_ActualTemp_Cabin, displays it
```

**The bug:** IVI is displaying `HVAC_SetTemp` (the setpoint, 18°C) instead of `HVAC_ActualTemp_Cabin` (the actual reading, 24°C).

This is extremely common after SW updates where signal routing is changed.

**Verification:**

1. UDS 0x22 on HVAC ECU: read actual cabin temperature DID → expect 24°C
2. CANoe trace: check `HVAC_ActualTemp_Cabin` CAN signal value → expect 24°C
3. IVI showing 18°C = it's displaying the setpoint, not the actual temperature

**Other possible causes:**
- Temperature unit conversion bug: Fahrenheit/Celsius conversion applied twice → 18°C × 1.8 + 32 = 64°F, confused as °C
- HVAC_ActualTemp_Cabin signal offset wrong: `physical = raw × 0.5 - 40` but IVI using `raw × 1.0` → wrong reading
- Wrong signal mapped in IVI DBC after update

**Test cases:**
```
TC_HVAC_001: Set temperature to 22°C → IVI displays setpoint = 22°C ✓
             After 10 min stabilisation → IVI displays actual cabin temp (should approach 22°C)
TC_HVAC_002: Set temperature to 16°C in 30°C ambient
             IVI should show setpoint = 16°C AND actual temp countdown from 30°C → 16°C
TC_HVAC_003: Compare IVI displayed temp vs physical thermometer in cabin — delta < 1°C
```"

---

### Scenario 4.2 — AC Does Not Turn Off via IVI Button

> **Interviewer:** "Pressing the AC OFF button on the infotainment screen does nothing. The button highlights as pressed but the AC continues running. What do you investigate?"

**Strong Answer:**

"The touch event is registered (button highlights) but the command is not reaching or being executed by the HVAC ECU.

**Three-layer investigation:**

**Layer 1 — Touch → IVI SW:**
The button highlight means the HMI layer received the touch. So the touchscreen hardware and the display rendering are fine.

**Layer 2 — IVI SW → CAN:**
The IVI SW should send a CAN message when AC button pressed.
- Open CANoe, filter for HVAC-related messages
- Press AC OFF button on IVI
- Check: is `HVAC_AC_OnOff_Req` message sent with value = 0?
- If no message appears → IVI SW bug (event handler not wiring button to CAN output)

```capl
// Monitor HVAC command messages
on message HVAC_Request_BC {
  write("HVAC Request: AC_OnOff=%d  Temp_Set=%.1f  Fan=%d",
        this.HVAC_AC_OnOff_Req,
        this.HVAC_SetTemp_Driver,
        this.HVAC_FanSpeed_Req);
}
```

**Layer 3 — CAN → HVAC ECU:**
- If CAN message IS sent with AC=0
- Check: does HVAC ECU execute AC OFF?
- UDS 0x22 on HVAC: read AC status DID → if still shows ON, HVAC ECU ignoring command
- Possible causes:
  - HVAC ECU in a mode where it ignores AC OFF (e.g., defrost active overrides AC off command)
  - Message authentication: some systems require a rolling counter / AUTOSAR SecOC on HVAC commands — counter mismatch = ignored
  - Arbitration: physical button on HVAC panel sends AC=1 simultaneously, overriding IVI command

**Most common root cause in IVI:** The IVI SW button click handler calls a UI update function but forgets to also call the CAN output function — a classic copy-paste SW bug."

---

## SECTION 5 — OTA (Over-The-Air) Software Updates

---

### Scenario 5.1 — OTA Update Fails Midway

> **Interviewer:** "An OTA software update for the head unit starts downloading but fails at 67% every time. How do you debug this?"

**Strong Answer:**

"67% consistent failure suggests a deterministic issue — not random network dropout.

**Investigation:**

1. **Check TCU/IVI logs:**
   - What error code is logged at 67%?
   - Is it a network error (timeout, TCP reset) or a local storage error (write failed, checksum mismatch)?

2. **Calculate what 67% represents:**
   - If update file is 3GB, 67% = ~2GB downloaded
   - Check available storage on IVI: `df -h` via ADB
   - Is the IVI running out of storage at exactly this point?

3. **Network layer:**
   - TCU logs: is the cellular connection dropping at a specific location/time?
   - Is 67% correlating with a specific update segment/chunk that may be corrupted on the server?

4. **Checksum validation:**
   - Some OTA systems validate chunk-by-chunk: if chunk 67 has a hash mismatch on the server, every client will fail at that chunk
   - Test: try from a different server region or re-upload the update package server-side

5. **Vehicle condition check:**
   - OTA updates typically require: ignition ON + battery > 20% + parking brake engaged
   - If battery drops slightly mid-download (engine off), update may abort at 67%
   - Monitor battery voltage during download

6. **Test methodology:**
```
TC_OTA_001: Full download in workshop (stable WiFi, charger connected) — does it complete?
TC_OTA_002: Download interrupted at 50% → resume → does it continue from 50% or restart?
TC_OTA_003: Monitor IVI storage (df -h) every 10% of download progress
TC_OTA_004: Simulate low battery at 60% download → does system abort cleanly or corrupt?
TC_OTA_005: Server-side: validate SHA-256 hash of each update chunk
```

**Investigation decision tree:**
```
67% failure every time
    ├── Same error code? → Deterministic bug
    │       ├── Storage full?  → Increase IVI partition or reduce update size
    │       ├── Checksum fail? → Re-upload clean package to server
    │       └── Network timeout at specific chunk? → CDN/server issue
    └── Different error codes? → Environmental (network/battery)
```"

---

### Scenario 5.2 — Vehicle Functions Lost After OTA Update

> **Interviewer:** "After an OTA update, the reverse camera no longer appears when the car is put in reverse. Everything else works. The camera hardware is fine. How do you find the root cause?"

**Strong Answer:**

"Post-OTA regression on a specific feature. The camera hardware works — confirmed. So the OTA update broke something in the software chain.

**The camera activation chain:**
```
Gear → Reverse (CAN signal: GearPosition = 4)
    → IVI receives CAN signal
    → IVI switches video input to Camera channel
    → Camera ECU sends video over LVDS/MOST/Ethernet
    → IVI renders video on screen
```

**Step 1 — Check CAN signal reception:**
Does the IVI still receive `GearPosition = 4` correctly?
UDS 0x22 on IVI: read GearPosition DID → is it showing Reverse when gear engaged?

```capl
on signal Powertrain::GearPosition {
  write("Gear = %d (4=Reverse)", this.value);
  if (this.value == 4)
    write("Reverse detected — IVI should switch to camera view");
}
```

**Step 2 — Check if event triggers IVI switch:**
- ADB logcat on IVI (if Android-based):
```bash
adb logcat | grep -i "gear\|reverse\|camera\|video\|RVC"
```
- Look for: "GearReverse event received" → "Switching to RVC input" → "Video surface created"
- If "GearReverse event received" is missing → CAN signal no longer mapped to camera trigger (config regression)
- If event received but "Switching to RVC" missing → SW handler removed or commented out in new build

**Step 3 — Check camera input selection:**
- IVI has a video multiplexer — inputs: Front camera, Rear camera, HDMI, etc.
- OTA may have changed the input index: Rear camera was Input_2, new build maps it to Input_3
- UDS 0x22: read active video input DID

**Step 4 — Git diff / changelog:**
- Request SW diff from Reverse Camera feature module between old and new SW version
- Common regressions: `#ifdef RVC_ENABLED` compile flag accidentally set to 0, or configuration file (JSON/XML) camera input mapping changed

**CAPL automated regression test (this should be P0 regression after every OTA):**
```capl
// RVC Activation Regression Test
variables {
  message GearStatus_BC msgGear;
  msTimer tmrCheck;
  int gPass = 0, gFail = 0;
}

on start {
  write("=== RVC Regression Test ===");
  // Put car in Reverse
  msgGear.GearPosition = 4;
  output(msgGear);
  setTimer(tmrCheck, 1000);   // wait 1 second for camera to activate
}

on timer tmrCheck {
  int cameraActive = getValue(IVI_ECU::RVC_Display_Active);
  if (cameraActive == 1) {
    write("PASS — Reverse camera activated within 1 second");
    gPass++;
  } else {
    write("FAIL — Reverse camera NOT activated after Reverse gear");
    gFail++;
  }
  // Return to Park
  msgGear.GearPosition = 0;
  output(msgGear);
  write("=== RVC Test: PASS=%d FAIL=%d ===", gPass, gFail);
}
```"

---

## SECTION 6 — Voice Recognition & HMI

---

### Scenario 6.1 — Voice Command Works in English, Not in Hindi/Urdu

> **Interviewer:** "Voice recognition works perfectly in English but fails to recognise Hindi commands correctly. How would you test this?"

**Strong Answer:**

"This is a localisation and ASR (Automatic Speech Recognition) model quality issue.

**Test strategy:**

1. **Define test cases per language:**
   - Core commands: 'Call home', 'Navigate to airport', 'Play music'
   - Create a test script with 20 standard commands in Hindi
   - Record each command 5 times by 3 different speakers (male/female/accented)
   - Calculate Word Error Rate (WER): WER = (substitutions + deletions + insertions) / total words

2. **Acceptance criteria:**
   - English WER < 5% (industry standard for English)
   - Hindi WER should be < 10% per spec (confirm with requirement)

3. **Noise-condition testing:**
   - Test at: cabin quiet, 80 km/h wind noise, music playing at 50% volume
   - A2DP audio affects microphone feed in some IVI implementations

4. **Check ASR model version:**
   - UDS 0x22 language pack DID → which Hindi ASR model version is loaded?
   - If v1.0 while English is v3.2, the Hindi model is undertrained

5. **Microphone far-field position test:**
   - Test with microphone at different distances (driver = 40cm, passenger = 60cm)
   - Hindi has different phoneme characteristics — front-end audio processing (beamforming) tuned for English affects Hindi differently

6. **Test matrix:**

| Command | English | Hindi | Pass/Fail |
|---------|---------|-------|-----------|
| 'Call home' / 'Ghar par call karo' | PASS | FAIL | ❌ |
| 'Navigate home' / 'Ghar le chalo' | PASS | FAIL | ❌ |
| 'Play music' / 'Gaana bajao' | PASS | PASS | ✅ |

**Defect report:** Language model version mismatch, or phoneme dictionary incomplete for Hindi. Raise with ASR vendor (Nuance / SoundHound / custom model)."

---

### Scenario 6.2 — Touchscreen Unresponsive in Cold Weather

> **Interviewer:** "Several customers report the infotainment touchscreen is unresponsive when the car is cold — below -10°C. After 10 minutes of heating it works fine. How do you approach this?"

**Strong Answer:**

"Temperature-dependent hardware behaviour — classic cold soak test failure.

**Root cause analysis:**

1. **Touchscreen technology:**
   - Capacitive touchscreen response slows significantly below -10°C
   - The dielectric constant of the touch sensor changes with temperature → lower sensitivity
   - Some capacitive controllers have a minimum temperature threshold below which they report no touch

2. **IVI boot time vs touchscreen ready time:**
   - At cold temperature, the IVI processor (SoC) may boot and display the UI before the touchscreen driver is fully initialised
   - The screen shows an image but touches are not registered — user thinks it's unresponsive
   - Check: does tapping trigger any event at all? (even misregistered)

3. **Display glass thermal expansion:**
   - In some assemblies, the glass panel and frame have different thermal expansion coefficients
   - At -10°C, mechanical stress on the flex cable connecting touchscreen to controller can cause intermittent connection

4. **Test plan:**

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Cold soak boot | Park overnight at -20°C, start car, measure time to first touch response | < 30 seconds |
| Touch sensitivity calibration | Check if touchscreen auto-recalibrates at temp change | Recalibration within 5s of temp crossing threshold |
| Touchscreen driver log | ADB logcat at cold start — any timeout/error messages from touch HAL? | No errors |
| Flex cable continuity | Temperature chamber + continuity tester on touch cable | No resistance change > 5% at -20°C |

5. **Short-term fix options:**
   - Increase touch sensitivity threshold in cold mode (software config change)
   - Add a minimum startup delay: display shows "Warming up" for 5 seconds before enabling touch (user expectation management)
   - Hardware: add a resistive heater strip to the rear of touchscreen panel (like rear windscreen heater)"

---

## SECTION 7 — Diagnostics & End-of-Line Testing

---

### Scenario 7.1 — IVI Fails End-of-Line (EOL) Test at Factory

> **Interviewer:** "The IVI unit passes all bench tests but fails the End-of-Line test at the factory line — specifically the 'Display Brightness Verification' step. What are the possible causes?"

**Strong Answer:**

"Bench passes, EOL fails — the difference between the two environments is key.

**Bench vs EOL environment differences:**

| Factor | Bench | Factory EOL |
|--------|-------|-------------|
| Power supply | Lab PSU (stable 13.5V) | Factory power (may vary 12–14V) |
| CAN network | Bench harness | Full vehicle harness |
| Software | Same SW | Same SW |
| Test tool | Engineer's CANoe | EOL tester (different tool) |
| Ambient light | Controlled lab | Factory floor (high ambient light) |
| Measurement method | Visual / screen capture | Photometer probe at fixed position |

**Hypothesis 1 — Photometer positioning:**
EOL photometer may be positioned at a slightly different angle or distance than the spec diagram. Brightness reading is cosine-dependent — a 10° angle error can cause 15% brightness reading error.

**Hypothesis 2 — Ambient light calibration:**
Adaptive brightness: if the IVI has ambient light sensor → it auto-adjusts brightness. Factory floor has different lighting than spec reference. If auto-brightness is active during EOL test → photometer reads wrong value.
Fix: Disable auto-brightness (set fixed brightness mode) during EOL test via UDS 0x2E DID.

**Hypothesis 3 — Display warm-up time:**
Cold IVI display (just powered on) may have lower initial brightness. EOL test runs immediately after power-on — display not yet at operating temperature.
Fix: Add 60-second warm-up delay in EOL sequence before brightness measurement.

**Hypothesis 4 — EOL tester pass/fail threshold wrong:**
Check if the EOL tester threshold was updated correctly after a display change. If spec is 500 nits but EOL tester still programmed for old spec of 400 nits → false failure on good units.

**Test to confirm root cause:**
1. Run EOL test with photometer in exact spec position → record result
2. Immediately after EOL fail, manually measure brightness with handheld photometer → compare values
3. Check IVI ambient light sensor reading during EOL test → is auto-brightness active?"

---

### Scenario 7.2 — DTC Stored on New IVI Unit Before First Drive

> **Interviewer:** "A freshly assembled vehicle shows a DTC on the IVI ECU before the customer has driven it even once. DTC is: U0101 — Lost Communication with TCM. How do you investigate?"

**Strong Answer:**

"U0101 on a brand new vehicle is almost certainly a build/assembly issue, not a component fault.

**U0101 = Lost Communication with Transmission Control Module (TCM)**

This DTC is set when the IVI (or the ECU that monitors TCM communication) does not receive a CAN message from TCM within the expected cycle time.

**Investigation:**

1. **Is the TCM physically connected?**
   - Check CAN bus network topology — is TCM node present on the bus?
   - CANoe: do we see any CAN messages from TCM's expected message IDs?
   - If no TCM messages → wiring harness not connected at assembly, or TCM not programmed

2. **Is this an assembly sequence issue?**
   - In some vehicles, IVI powers up before TCM during first ignition cycle
   - IVI monitors CAN within first 500ms → TCM hasn't started yet → IVI logs U0101 as spurious
   - After second ignition cycle: TCM is up → no more DTC
   - Test: clear DTC, cycle ignition, check if DTC returns

3. **Is TCM programmed?**
   - New TCM from factory may not have the correct calibration flashed
   - If TCM is awaiting programming (virgin state), it may not transmit CAN messages
   - EOL programming station should have flashed TCM before vehicle left the line

4. **Network scan:**
```
UDS 0x10 03 → extended diagnostic session on IVI
UDS 0x19 02 FF → read all DTCs with any status
Compare against: expected DTCs = none for brand new unit
```

5. **Resolution path:**
   - If TCM physically disconnected: assembly line quality escape → fix harness
   - If first-ignition timing issue: IVI SW debounce window needs increasing (from 500ms to 2s)
   - If TCM not programmed: EOL process defect → reprogram TCM on line

**Key lesson:** U0101 on new vehicles is a very common EOL and assembly quality indicator. Having a test case that specifically checks for U0101 absence on first ignition is a P0 test in any production validation suite."

---

## Quick Reference — Common Infotainment DTCs

| DTC | Meaning | Most Common Cause |
|-----|---------|------------------|
| U0100 | Lost comm with ECM/PCM | CAN bus not connected, ECM not powered |
| U0101 | Lost comm with TCM | TCM not programmed / harness issue |
| U0155 | Lost comm with Instrument Cluster | IC not on CAN network yet or DBC mismatch |
| U0164 | Lost comm with HVAC Control Module | HVAC on different CAN segment, gateway issue |
| U0184 | Lost comm with Radio | IVI internal module failure or harness |
| B1000 | ECU internal fault | SW corruption, RAM error — usually after bad flash |
| B2610 | Touchscreen calibration lost | NVM data erased after power loss during update |
| C0035 | Front wheel speed sensor — left | Usually not IVI — but displayed via cluster |
| P0600 | Serial communication link | Internal IVI bus fault |

---

## Interview Tips — Infotainment Specific

| Do | Don't |
|----|-------|
| Always check CAN trace first before touching hardware | Don't assume hardware fault without CAN evidence |
| Use UDS 0x19 before and after every test | Don't ignore DTCs that "might not be relevant" |
| Reference signal path: sensor → ECU → CAN → IVI → display | Don't just say "it's a software bug" without isolating the layer |
| Mention both lab reproduction AND real-vehicle validation | Don't assume bench result = vehicle result |
| Propose regression test for every bug found | Don't fix without leaving a permanent test case |
| Know Android/Linux basics if applying to modern IVI roles | Don't pretend ADB / logcat knowledge you don't have |

---

*File: 10_infotainment_scenario_questions.md | Updated: April 2026*
