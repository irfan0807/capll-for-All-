# Sensor Fusion — Real-Time Debugging Scenarios
## 15 Investigation Scenarios with CAPL Code | April 2026

Each scenario: Problem → Background → Investigation Steps → CAPL Code → Test Cases → Root Cause

---

## Scenario 1 — Fusion Object List Empty After Sensor ECU SW Update

> **Problem:** After a radar ECU software update, the fusion ECU's fused object list is empty. The radar ECU appears to be running (green on diagnostic tool). Camera objects are visible. What is wrong?

**Background:**
The fusion ECU receives object lists from sensors via CAN or Ethernet. If the radar SW update changed the CAN message format, signal encoding, or message ID, the fusion ECU may no longer parse radar data correctly.

**Investigation Steps:**

*Step 1 — Verify CAN traffic from radar:*
```capl
variables {
  int gRadarMsgCount  = 0;
  int gCameraMsgCount = 0;
  dword tLast_radar   = 0;
}

on message Radar::ObjectList_Header {
  gRadarMsgCount++;
  dword now = timeNow() / 10;
  write("[%d ms] Radar header: NumObjects=%d  VersionID=%d",
        now,
        this.Radar_NumObjects,
        this.Radar_SW_Version);
  tLast_radar = now;
}

on message Camera::ObjectList_Header {
  gCameraMsgCount++;
  write("[%d ms] Camera header: NumObjects=%d", timeNow()/10, this.Camera_NumObjects);
}

on key 's' {
  write("Radar msgs received: %d  Camera msgs: %d", gRadarMsgCount, gCameraMsgCount);
  if (gRadarMsgCount == 0) {
    write("FAIL — Radar messages not reaching fusion ECU — check CAN ID or bus routing");
  }
}
```

*Step 2 — Check for message format change:*
Compare old vs new radar DBC files:
- Did RadarObjectList message ID change? (e.g., 0x201 → 0x211)
- Did signal encoding change? (Intel → Motorola byte order, or signal length changed)
- Did cycle time change? (25ms → 20ms — fusion may have a receive timeout)

*Step 3 — Fusion diagnostic DTC:*
```
UDS 0x19 02 08 on Fusion ECU → any confirmed DTCs?
Expected DTC if radar message absent: U0076 Lost Communication with Radar Sensor
```

**Test Cases:**
```
TC_F_001: Radar ECU running → fusion object list contains radar-derived objects within 500ms
TC_F_002: Radar SW update → verify DBC/ARXML version matches fusion ECU configuration
TC_F_003: Disconnect radar CAN → fusion sets U0076 DTC within 500ms
TC_F_004: Radar message ID change → fusion reports parse error, does not silently show zero objects
TC_F_005: After reconnect → fusion object list recovers within 3 message cycles
```

**Root Cause:** Radar SW update changed the `ObjectList_Header` message ID from 0x201 to 0x211. The fusion ECU's signal database was not updated. Fusion ECU received no objects on 0x201 → empty list. Fix: update fusion ECU signal database (ARXML/DBC) to match new radar message ID and redeploy.

---

## Scenario 2 — Fused Object Position Jumps 3m Every 10 Seconds

> **Problem:** A confirmed fused track (target vehicle ahead at 50m) has its position periodically jumping 3m forward and back approximately every 10 seconds. Speed measurement is correct. Only position has the discontinuity.

**Background:**
Periodic position jumps on a specific interval suggest a timer or update cycle event is causing a reset or re-initialisation of the tracking state.

**Investigation Steps:**

*Step 1 — Capture position over time:*
```capl
variables {
  float gLastPos    = 0.0;
  float gPosDelta   = 0.0;
  int   gJumpCount  = 0;
}

on message FusionECU::FusedObjectList {
  // Read first object position
  float pos = this.Object_0_Range_m;
  gPosDelta = pos - gLastPos;

  // Flag jumps > 2m that are NOT due to actual vehicle motion
  float expectedMotion = this.Object_0_Velocity_ms * 0.025;   // 25ms cycle × velocity
  float anomaly = abs(gPosDelta) - abs(expectedMotion);

  if (anomaly > 2.0) {
    gJumpCount++;
    write("[JUMP #%d] Position: %.2f → %.2f  (Δ=%.2fm  expected=%.2fm)",
          gJumpCount, gLastPos, pos, gPosDelta, expectedMotion);
  }

  gLastPos = pos;
}

on stopMeasurement {
  write("Total position jumps: %d", gJumpCount);
}
```

*Step 2 — Correlate with any 10-second event:*
- Does any ECU send a periodic message every 10 seconds? (NVM save, watchdog kick, diagnostic keepalive?)
- Does the radar have a 10-second re-alignment or internal calibration cycle?
- Does the fusion ECU perform a track database cleanup every 10 seconds?

*Step 3 — Track state inspection:*
```capl
on message FusionECU::TrackState {
  // 0=tracking  1=coasted  2=initialising  3=re-initiating
  if (this.Track_0_State == 3) {
    write("[%d ms] Track re-initiating! Age=%d ms", timeNow()/10, this.Track_0_Age_ms);
  }
}
```

**Test Cases:**
```
TC_JUMP_001: Follow target for 5 minutes → position RMSE < 0.5m → no jumps > 2m
TC_JUMP_002: Monitor track state → no re-initiation events for confirmed track
TC_JUMP_003: Radar 10s recalibration: track must not be disturbed (position held from Kalman prediction)
TC_JUMP_004: 1000 track updates → no position discontinuities > 2× expected motion per cycle
```

**Root Cause:** Radar ECU performed an internal antenna gain calibration every 10 seconds, briefly changing its range output by ±3m during the ~80ms calibration cycle. Fusion was not compensating for this known calibration event. Fix: fusion ECU subscribes to `Radar_Calibration_Active` signal — when active, use Kalman prediction only (do not update from radar measurements for the calibration duration).

---

## Scenario 3 — Two Vehicles Detected as One at Highway Merge Point

> **Problem:** On a motorway merge, when a car drives parallel to the test vehicle in the merging lane (2.5m lateral offset, same speed), the fusion system creates a single track centred between the two vehicles instead of two separate tracks. Risk: collision assessment sees one "wide" object instead of two separate vehicles.

**Background:**
Track merging occurs when the data association algorithm assigns two detections from different real objects to the same track. This happens when the gate distance used in association is too large.

**Investigation Steps:**

*Step 1 — Measure the gate distance in use:*
```capl
on message FusionECU::FusedObjectList {
  write("NumObjects=%d", this.Fusion_NumObjects);
  // If parallel vehicles create 1 object instead of 2: track merge
  if (this.Fusion_NumObjects == 1) {
    write("Only 1 fused object — check if two real vehicles present");
    write("  Object 0: range=%.1f az=%.2f width=%.1f",
          this.Object_0_Range_m,
          this.Object_0_Azimuth_deg,
          this.Object_0_Width_m);
    if (this.Object_0_Width_m > 4.0) {
      write("  SUSPECT MERGE: object width %.1fm > 4m suggests two merged objects",
            this.Object_0_Width_m);
    }
  }
}
```

*Step 2 — Raw radar object list (pre-fusion):*
```capl
on message Radar::ObjectList_Object {
  write("Radar raw: ID=%d  Range=%.1fm  Az=%.2f°  Vel=%.1fm/s",
        this.Obj_ID,
        this.Obj_Range_m,
        this.Obj_Azimuth_deg,
        this.Obj_Velocity_ms);
}
```
- Does radar see 2 separate objects? If yes → merge is in fusion, not radar
- Does radar see 1 object? If yes → radar angular resolution insufficient to separate at 2.5m lateral at 50m range

*Step 3 — Angular resolution check:*
```
At 50m range, 2.5m lateral separation = atan(2.5/50) = 2.86° separation
Radar angular resolution (3dB beamwidth / 2): typically ±5° → cannot resolve 2.86° sep
At 100m: 2.5m = 1.43° → definitely cannot separate
```
This is a fundamental radar limitation at this geometry.

*Step 4 — Camera can resolve:*
Camera angular resolution: < 0.2° → can easily separate 2.86° objects.
If camera sees 2 objects, fusion should create 2 tracks.
Check: is the camera object association feeding correctly into fusion for this geometry?

**Test Cases:**
```
TC_MERGE_001: Two vehicles 3m lateral, 40m range → fusion creates 2 separate tracks
TC_MERGE_002: Two vehicles 1.5m lateral, 40m range → document minimum separation for dual tracking
TC_MERGE_003: Track merge event → width monitor flags width > 4m → diagnostic alert raised
TC_MERGE_004: After vehicles separate → fusion correctly maintains 2 independent tracks
```

**Root Cause:** At the specific geometry (2.5m lateral, 50m range), radar angular resolution was insufficient to separate the vehicles. Camera correctly detected 2 objects but the camera-to-fusion data association had a 3m gate (too large) — both camera detections associated to one radar object. Fix: reduce camera association gate from 3m to 1.5m for close-proximity lateral objects; also flag track width > 4m as potential merge event.

---

## Scenario 4 — Fusion Track Velocity 15 km/h Higher Than Actual

> **Problem:** Vehicle on ETK (engineering test vehicle) following a target at 80 km/h shows fused object velocity = 95 km/h consistently. The test vehicle's own speed sensor is correct. The target vehicle's GPS (via V2X) confirms it is exactly 80 km/h. Where is the 15 km/h error coming from?

**Investigation Steps:**

*Step 1 — Check ego-motion compensation:*
Fused object velocity is relative velocity + ego vehicle velocity.
If ego velocity is wrong: fused absolute velocity will be wrong.
```capl
on key 'v' {
  float ego_speed_wheel = getValue(ABS::VehicleSpeed_kmh);  // from wheel sensors
  float ego_speed_fusion = getValue(FusionECU::EgoVelocity_kmh);  // what fusion uses

  write("Ego speed: Wheel=%.1f km/h   Fusion=%.1f km/h", ego_speed_wheel, ego_speed_fusion);

  if (abs(ego_speed_wheel - ego_speed_fusion) > 2.0) {
    write("FAIL — Fusion using incorrect ego speed! Delta=%.1f km/h",
          abs(ego_speed_wheel - ego_speed_fusion));
  }
}
```

*Step 2 — Check unit conversion:*
Radar outputs relative velocity in m/s.
Fusion converts to km/h for display/output.
```
Radar: relative velocity = 0 m/s (both at same speed)
Fusion absolute velocity = ego + relative = 80 + 0 = 80 km/h ← correct

But if unit conversion wrong:
  Fusion absolute velocity = 80 + 0 × (3.6 error) ← only matters if relative ≠ 0

What if ego speed is being reported in m/s but fusion thinks it's km/h?
  22.2 m/s (80 km/h) interpreted as 22.2 km/h → absolute = 22.2 + 72.8 (radar) or similar
```
Check all unit conventions in fusion ECU CAN signal definitions.

*Step 3 — Radar Doppler calibration:*
If radar has systematic velocity bias (ADC offset, antenna issue): all velocities offset.
Check: measure stationary target (parked car) → relative velocity should be −80 km/h (approaching at test vehicle speed). If it reads −65 km/h → radar is under-reading by 15 km/h → absolute velocity over-reads by 15 km/h.

**Test Cases:**
```
TC_VEL_001: Stationary target ahead → relative velocity = −(ego speed) ± 1 km/h
TC_VEL_002: Target at exact same speed → relative velocity = 0 ± 0.5 km/h
TC_VEL_003: Target accelerating → fusion velocity increases proportionally
TC_VEL_004: Ego speed signal source: verify fusion reads from same source as instrument cluster
```

**Root Cause:** The ABS speed message had a scale factor of 0.05625 km/h per bit in a recent signal database update. The fusion ECU's local copy still had the old scale of 0.05 km/h per bit. At 80 km/h: `80 / 0.05 × 0.05625 = 90 km/h` was the ego speed the fusion used. Absolute velocity = 90 + (−15 approx for any slight relative speed) → appears as 15 km/h high. Fix: sync DBC/ARXML between ABS and fusion ECU. NEVER hand-copy signal scaling — always use the shared database.

---

## Scenario 5 — Fusion Loses Track in Stationary Traffic (Stop-and-Go Scenario)

> **Problem:** In stop-and-go motorway traffic, the fusion system loses the target vehicle track every time the traffic stops completely. After 2–3 seconds stopped, the track is deleted. When traffic moves again, a new track is created with a latency of 500ms, causing brief ACC disengagement and uncomfortable behaviour.

**Investigation Steps:**

*Step 1 — Track coasting configuration:*
```capl
on message FusionECU::TrackState {
  if (this.Track_0_State == 1) {   // 1 = coasting
    write("[%d ms] Track coasting (no measurement update)  CoastAge=%d ms",
          timeNow()/10, this.Track_0_CoastAge_ms);
  }
  if (this.Track_0_State == 4) {   // 4 = deleted
    write("[%d ms] TRACK DELETED after %.0f ms coasting", timeNow()/10,
          (float)this.Track_0_CoastAge_ms);
  }
}
```

*Step 2 — Why does radar lose a stationary vehicle?*
At very low relative velocity (both stopped):
- Radar Doppler = 0 m/s
- Radar cannot separate a stationary vehicle from stationary clutter (road surface, barriers) by velocity alone
- The radar's clutter filter suppresses low-Doppler returns → vehicle return suppressed

*Step 3 — Camera maintaining track when stopped:*
Camera detects the vehicle visually regardless of velocity. Check: does camera still detect the stationary vehicle?
```capl
on message Camera::ObjectList_Object {
  if (abs(this.Camera_Obj_Velocity_ms) < 0.5) {   // object is near-stationary
    write("Camera detects stationary object at %.1fm  Class=%d",
          this.Camera_Obj_Range_m, this.Camera_Obj_Class);
  }
}
```

*Step 4 — Fusion must keep track alive from camera alone:*
When radar loses object (Doppler = 0), camera still detects → fusion should continue track from camera.
If fusion requires both radar AND camera for track maintenance → track dies when radar drops out.
Fix: allow camera-only track maintenance in stationary condition (explicitly handle v_relative = 0 case).

**Test Cases:**
```
TC_STOPGO_001: Target stops → fusion track maintained for ≥ 30 seconds while stopped
TC_STOPGO_002: Track coasting time while stopped: camera input must prevent deletion
TC_STOPGO_003: Traffic stops → ACC stays engaged, no re-acquisition latency when traffic moves
TC_STOPGO_004: Genuine object departure (vehicle drives away) → track deleted within 5 seconds
TC_STOPGO_005: Night + fog + stationary: define minimum conditions for track persistence
```

**Root Cause:** Fusion track deletion was triggered after 2 seconds of no radar update, regardless of camera state. The camera-only track maintenance mode was implemented but gated behind `CameraConfidence > 0.7`. At night, camera confidence was 0.65 → gate not met → camera couldn't prevent deletion. Fix: lower camera confidence threshold for track maintenance to 0.5 (less strict than for new track creation).

---

## Scenario 6 — NCAP AEB Test Failure: Braking 0.3 Seconds Late

> **Problem:** AEB test CCRs (Car-to-Car Rear stationary) at 50 km/h: test vehicle should begin braking at TTC (Time to Collision) = 2.7 seconds. It is braking at TTC = 2.4 seconds — 0.3 seconds late. The vehicle stops before hitting the target, but the NCAP score is reduced due to late activation.

**Investigation Steps:**

*Step 1 — Trace AEB trigger chain:*
```
Fusion ECU outputs object → AEB function reads object → calculates TTC → commands braking

TTC = range / closing_speed

Spec: brake when TTC ≤ 2.7s
Actual brake: TTC = 2.4s

Either: object was detected too late (short range), or TTC calc is wrong, or brake command delayed
```

*Step 2 — Measure object appearance range:*
```capl
variables {
  float gTarget_first_range = 0.0;
  int   gTargetSeen = 0;
}

on message FusionECU::FusedObjectList {
  if (this.Object_0_Confidence > 0.80 && !gTargetSeen) {
    gTargetSeen = 1;
    gTarget_first_range = this.Object_0_Range_m;
    float speed_ms = getValue(ABS::VehicleSpeed_kmh) / 3.6;
    float ttc = gTarget_first_range / speed_ms;
    write("Target first confirmed at range=%.1fm  speed=%.1fm/s  TTC=%.2fs",
          gTarget_first_range, speed_ms, ttc);
    write(ttc > 3.5 ? "Range OK for 2.7s AEB trigger" : "Range TOO SHORT — late detection!");
  }
}
```

*Step 3 — Track confirmation latency:*
Check: how many cycles does fusion take to confirm a new track (tentative → confirmed)?
Default: 3 consecutive detections × 25ms = 75ms latency.
At 50 km/h: 75ms = 1.04m range loss.
At AEB threshold range of 37.5m (50km/h × 2.7s), object must be detected at 38.5m to allow 3-cycle confirmation.

*Step 4 — Confidence threshold:*
AEB reads objects with confidence > 0.80.
If target appears at 45m but confidence only reaches 0.80 at 38m due to slow confidence build-up → late trigger.
Tune confidence build-up rate for this approach geometry.

**Test Cases:**
```
TC_AEB_001: CCRs at 50 km/h → AEB triggers at TTC ≥ 2.7s ± 0.1s
TC_AEB_002: Object detection range: target confirmed (confidence > 0.80) at range ≥ 45m at 50 km/h
TC_AEB_003: Track confirmation latency ≤ 75ms (3 × 25ms cycles)
TC_AEB_004: 10× repeated CCRs tests → AEB trigger time standard deviation < 0.05s (consistent)
TC_AEB_005: AEB trigger to first brake pressure: ≤ 150ms (actuator latency separate from fusion)
```

**Root Cause:** Track confirmation required confidence > 0.80 sustained for 3 consecutive cycles. The stationary target had a lower-than-expected RCS at the approach angle (flat rear of vehicle). Confidence only reached 0.80 at 38m, not 45m. The 7m difference at 50 km/h = 0.50 seconds → 2.7 − 0.50 = 2.2s actual TTC at trigger. Fix: for stationary targets with zero Doppler (confirmed stationary by camera), confidence threshold for ACC/AEB reduced to 0.70 (lower confidence required when object class is confirmed stationary vehicle, not potential clutter).

---

## Scenario 7 — Fusion Output Message Rate Drops From 40 Hz to 5 Hz Under Load

> **Problem:** Under normal conditions fusion outputs at 40 Hz (25ms cycle). On test routes with many simultaneous objects (city driving, 15+ vehicles around) the output rate drops to 5 Hz (200ms cycle). AEB and ACC performance degrades significantly.

**Background:**
Frame rate drops indicate CPU saturation. The fusion algorithm is computationally bounded — too many objects causes it to run slower than the desired cycle time.

**Investigation Steps:**

*Step 1 — Monitor output frame rate:*
```capl
variables {
  dword tLast_fusion    = 0;
  int   gCycleCount     = 0;
  float gAvgCycle_ms    = 0.0;
  float gMaxCycle_ms    = 0.0;
}

on message FusionECU::FusedObjectList {
  dword now = timeNow() / 10;
  dword cycle_ms = now - tLast_fusion;

  gCycleCount++;
  gAvgCycle_ms += (cycle_ms - gAvgCycle_ms) / gCycleCount;
  if ((float)cycle_ms > gMaxCycle_ms) gMaxCycle_ms = (float)cycle_ms;

  if (cycle_ms > 50) {
    write("[LATE FRAME #%d] cycle=%d ms (nominal=25ms)  Objects=%d",
          gCycleCount, cycle_ms, this.Fusion_NumObjects);
  }

  tLast_fusion = now;
}

on stopMeasurement {
  write("Fusion cycle: avg=%.1f ms  max=%.0f ms  count=%d", gAvgCycle_ms, gMaxCycle_ms, gCycleCount);
}
```

*Step 2 — Complexity scaling:*
Hungarian algorithm (data association) is O(n³) where n = number of objects.
At n=5 objects: 125 operations
At n=15 objects: 3375 operations → 27× more computation
If ECU budgeted for max 8 objects and city driving has 15+: CPU overloaded.

*Step 3 — Profiling:*
Request CPU profiling from fusion ECU (if instrumented build available):
```
Function             CPU%    Calls/cycle
Hungarian_Solver     78%     1
KalmanFilter_Update  12%     N_tracks
Message_Decode        5%     3 sensors
Output_Encode         3%     1
```
Hungarian = bottleneck.

*Step 4 — Mitigation:*
1. Cap maximum tracked objects (drop oldest lowest-confidence tracks first when limit reached)
2. Use a faster assignment algorithm (auction algorithm O(n²) or greedy for high-object scenarios)
3. Prioritise in-path objects: only run full KF update on objects within 3m of vehicle path, others run coarser update

**Test Cases:**
```
TC_RATE_001: 5 objects around vehicle → output rate 40 Hz ± 2 Hz
TC_RATE_002: 15 objects around vehicle → output rate ≥ 25 Hz (1 drop allowed per second)
TC_RATE_003: 20 objects → define graceful degradation: which objects are dropped first
TC_RATE_004: CPU load: fusion must not exceed 80% CPU at design maximum object count
TC_RATE_005: AEB path objects: never dropped regardless of total object count
```

**Root Cause:** Hungarian algorithm O(n³) ran on all objects including irrelevant ones (vehicles 200m behind from rear radar, parked cars to side). Fix: pre-filter objects to only run full association on objects within AEB/ACC relevant zone (forward 150m, ±40° lateral). Objects outside this zone use a simple nearest-neighbour (O(n)) association. CPU at 15 objects reduced from 95% to 52%.

---

## Scenario 8 — Night-Time Pedestrian Detection Rate Drops to 40%

> **Problem:** Daytime pedestrian detection rate (fusion confirmed tracks for pedestrians in path): 96%. Night-time rate for same scenario: 40%. The radar detects pedestrians at a similar rate day/night. The camera detects pedestrians poorly at night. What is the fusion failure?

**Investigation Steps:**

*Step 1 — Separate sensor performance from fusion performance:*
```capl
variables {
  int gPed_radar    = 0;   // pedestrians detected by radar alone
  int gPed_camera   = 0;   // pedestrians detected by camera
  int gPed_fusion   = 0;   // pedestrians confirmed by fusion
}

on message Radar::ObjectList_Object {
  if (this.Obj_Class == 2) { gPed_radar++; }   // 2 = pedestrian class
}
on message Camera::ObjectList_Object {
  if (this.Cam_Class == 2) { gPed_camera++; }
}
on message FusionECU::FusedObjectList {
  if (this.Object_0_Class == 2 && this.Object_0_Confidence > 0.70) { gPed_fusion++; }
}

on stopMeasurement {
  write("Detections: Radar=%d  Camera=%d  Fusion=%d", gPed_radar, gPed_camera, gPed_fusion);
  write("Fusion/Radar ratio: %.0f%%", (float)gPed_fusion / (gPed_radar + 0.001) * 100.0);
}
```

*Step 2 — Fusion weight analysis by time of day:*
If radar detects pedestrian: confidence from radar alone = 0.35 (pedestrian is hard for radar to classify)
Camera needed to raise confidence to > 0.70 threshold.
At night: camera confidence for pedestrian = 0.20 (very poor at night without IR)
Fused: 0.35 + 0.20 = 0.55 → below 0.70 → not confirmed → missed detection

During day: camera confidence = 0.75 → fused = 0.35 + 0.75 = 1.0 capped at 0.95 → above threshold

*Step 3 — Night-mode adaptation:*
Solution options:
1. Lower pedestrian fusion threshold at night (0.70 → 0.55) — increase false positive risk
2. Use radar class confidence boost for slow-moving objects (walking speed = 1.2–1.8 m/s) — radar velocity is reliable even at night
3. Infrared/thermal camera integration for pedestrian detection at night (system-level solution)
4. Use V2P (Vehicle to Pedestrian) communication if available

**Test Cases:**
```
TC_NIGHT_001: Daytime pedestrian crossing at 8 km/h: detection rate ≥ 95%
TC_NIGHT_002: Night pedestrian crossing: detection rate ≥ 75% (defined separately in spec)
TC_NIGHT_003: Night false positive rate: ≤ 0.5 per km (lower threshold must not over-trigger)
TC_NIGHT_004: Headlights on: camera performance characterised with and without headlight illumination
TC_NIGHT_005: Euro NCAP AEB pedestrian night test: pass with defined test score
```

**Root Cause:** Fusion confidence model was designed for daytime conditions (camera provides high confidence boost). At night, camera contribution collapsed but the fusion threshold was not adjusted. The threshold 0.70 was a single fixed value not considering lighting context. Fix: add a lighting condition context flag from the camera (day/dusk/night) and apply different fusion confidence thresholds: day=0.70, dusk=0.60, night=0.55 (with corresponding false positive analysis for each).

---

## Scenario 9 — Fused Object Class Switches Between Car and Truck Rapidly

> **Problem:** A large van is being followed by ACC at 100m. The fused object class alternates every 2–3 seconds between `Class=2 (Car)` and `Class=3 (Truck)`. The ACC response doesn't change visibly (it still follows) but the cluster ADAS display icon flickers between car and truck icons — confusing and unprofessional.

**Investigation Steps:**

*Step 1 — Observe classification confidence:*
```capl
on message FusionECU::FusedObjectList {
  byte cls  = this.Object_0_Class;
  float cnf = this.Object_0_Class_Confidence;

  write("[%d ms] Class=%d  Confidence=%.2f", timeNow()/10, cls, cnf);

  if (cnf < 0.60) {
    write("LOW confidence classification — suspect borderline object");
  }
}
```

*Step 2 — Camera classification input:*
At 100m, a large van is borderline between car and truck classifiers.
Camera neural network may produce: class_car=0.52, class_truck=0.48 (nearly equal).
With such close probabilities: minor image variations (motion blur, aspect angle) flip the classification each frame.

*Step 3 — Temporal hysteresis:*
Fix: once a class is assigned to a confirmed track, require a minimum confidence margin before changing.
```
Current class: Car (confidence 0.52)
New observation: Truck (confidence 0.53)
Rule: only change class if new class confidence > current class confidence + 0.15
Result: 0.53 < 0.52 + 0.15 → keep Car class → no flicker
```

*Step 4 — Classification smoothing:*
Apply a temporal filter: class = argmax of rolling average confidence over last 5 frames.
```
Frame 1: Car=0.52, Truck=0.48
Frame 2: Car=0.48, Truck=0.52
Frame 3: Car=0.55, Truck=0.45
Average: Car=0.517, Truck=0.483 → Class = Car (stable)
```

**Test Cases:**
```
TC_CLASS_001: Definite car (< 2m width) → Class=Car stable, confidence > 0.85
TC_CLASS_002: Definite truck (> 3m width) → Class=Truck stable
TC_CLASS_003: Large van (borderline): class must not toggle faster than 1× per 5 seconds
TC_CLASS_004: Class change from Car to Truck: require 5 consecutive Truck classifications before updating
TC_CLASS_005: Wrong class ACC response: car-following distance vs truck-following distance (gap must be appropriate for actual object size regardless of class)
```

**Root Cause:** Camera classifier confidence on a large van at 100m was consistently near 0.50 for both car and truck class. The fusion object class was updated every cycle from the latest camera output, with no hysteresis. Fix: (1) apply 0.15 confidence margin hysteresis for class change, (2) smooth class confidence over 5 frames. Cluster ADAS display icon flicker eliminated.

---

## Scenario 10 — Fusion Works on Test Track But Fails on Public Road

> **Problem:** Sensor fusion AEB performance is validated and PASS on the OEM test track. The same vehicle on a public motorway shows noticeably higher false positive rate (unnecessary light decelerations). Nothing was changed between test track and public road testing.

**Background:**
Test tracks are controlled environments. Public roads have more diverse objects, reflections, road furniture, and lane geometry variations that the test track does not represent.

**Investigation Steps:**

*Step 1 — Categorise the false positives:*
```capl
variables {
  int gFP_bridge      = 0;
  int gFP_metal_sign  = 0;
  int gFP_drain_cover = 0;
  int gFP_other       = 0;
}

// Log every light braking event
on signal BrakingController::AEB_Decel_Active {
  if (this.value == 1) {
    float obj_range  = getValue(FusionECU::Object_0_Range_m);
    float obj_rcs    = getValue(FusionECU::Object_0_RadarRCS_dBsm);
    float obj_height = getValue(FusionECU::Object_0_Height_m);
    float obj_az     = getValue(FusionECU::Object_0_Azimuth_deg);

    write("AEB event: range=%.1f  RCS=%.1f  height=%.1f  az=%.1f",
          obj_range, obj_rcs, obj_height, obj_az);
    // Classify false positive type (post-analysis)
  }
}
```

*Step 2 — Identify test track vs public road differences:*
Test track typically lacks:
- Highway gantry signs (large metal structures over road — cause large RCS stationary returns)
- Emergency phones (metal pillars every 1.5km on EU highways)
- Overhead electric cables (tram routes)
- Cat's eyes / road marker studs (cause small radar returns at low angle)

*Step 3 — Target coverage gap:*
The suppression filters were tuned on the test track. Public road has objects not in the test set.
Fix: collect 100km of public road logs → extract all false positive objects → extend suppression filter to cover new object types.

**Test Cases:**
```
TC_PUBLIC_001: Drive 100km motorway → false positive deceleration rate < 2 per 100km
TC_PUBLIC_002: Drive under 10 motorway gantries → no AEB events
TC_PUBLIC_003: Drive past 5 roadside emergency phones → no AEB events
TC_PUBLIC_004: Any new false positive class identified → suppression filter updated within same sprint
TC_PUBLIC_005: After filter update → rerun test track tests to verify no regression
```

**Root Cause:** The OEM test track has no overhead gantry signs. Public motorway has gantry signs every 2–5km. At 120 km/h approach, the gantry sign appears as a large stationary object with RCS +30 dBsm at road centre. Camera correctly ignores it (sees it as infrastructure from geometry). The existing suppression filter covered bridges (width > 10m, height > 4m) but gantry signs are narrower (width 2m, height 5m) — outside the filter. Fix: extend the geometry filter to include narrow overhead structures: height > 4m AND width 1–3m → suppress.

---

## Scenario 11 — Sensor Sync Loss During Vehicle CAN Bus Overload

> **Problem:** During a maximum-load CAN bus test (90% bus load), the fusion outputs start showing objects with stale timestamps — some objects are 150ms old. This causes incorrect TTC calculations and ACCs deceleration response.

**Investigation Steps:**

*Step 1 — Measure message latency under load:*
```capl
variables {
  dword gRadar_tx_time   = 0;   // timestamp in radar message
  msTimer tmrBusLoadTest;
}

on message Radar::ObjectList_Header {
  dword rx_time = timeNow() / 10;
  dword tx_time = this.Radar_Timestamp_ms;   // timestamp inside message
  long latency  = (long)rx_time - (long)tx_time;

  if (latency > 50) {
    write("HIGH LATENCY: Radar msg delayed %d ms (rx=%d tx=%d)",
          latency, rx_time, tx_time);
  }
}
```

*Step 2 — Bus prioritisation:*
CAN uses priority-based arbitration. Lower CAN ID = higher priority.
If radar messages (ID 0x201) have lower priority than diagnostic messages (ID 0x7E0 tester present every 2s): at 90% load, radar messages are delayed.
Check CAN ID priorities across all messages.

*Step 3 — Fusion timestamp compensation:*
Even if messages arrive late, fusion must compensate:
```capl
// Fusion must extrapolate all sensor data to a common fusion tick timestamp
// Object at (x,y) with velocity (vx,vy), delayed by dt:
// Compensated position: x_comp = x + vx × dt
//                        y_comp = y + vy × dt

on message FusionECU::FusedObjectList {
  float dt_s = this.Object_0_DataAge_ms / 1000.0;
  if (dt_s > 0.050) {   // > 50ms age
    write("Object data age: %.0f ms — TTC may be inaccurate", dt_s * 1000.0);
  }
}
```

**Test Cases:**
```
TC_SYNC_001: Normal bus load (< 40%) → fusion output object age ≤ 30ms
TC_SYNC_002: High bus load (80%) → fusion output object age ≤ 60ms
TC_SYNC_003: Critical safety messages (AEB object, distance) have CAN ID ≤ 0x100 (highest priority)
TC_SYNC_004: At 90% bus load → TTC accuracy within ±0.15s of ground truth (vs ±0.05s at normal load)
TC_SYNC_005: Tester present messages (0x7E0) must not compete with safety-critical sensor messages
```

**Root Cause:** CAN network architects had assigned the fusion sensor messages at IDs 0x300–0x380 (medium priority). During test, a diagnostic logging tool was connected and sending `0x3E 80` (Tester Present) from multiple virtual nodes, filling the bus. Radar message at 0x300 was delayed by up to 180ms. Fix: (1) sensor messages reassigned to IDs < 0x100 for safety-critical object data, (2) diagnostic tool limited to one tester present source per session.

---

## Scenario 12 — Fusion Incorrectly Inherits Wrong Object Class After Track Handover

> **Problem:** A motorcycle is initially detected at long range (150m) as `Class=Unknown`. As it gets closer, it is reclassified as `Class=Motorcycle`. However, if a car-class object track was deleted just before the motorcycle appeared at close range, the motorcycle inherits the deleted car track and keeps `Class=Car` even at close range.

**Investigation Steps:**

*Step 1 — Monitor track lifecycle:*
```capl
on message FusionECU::TrackEvent {
  // Track event types: 1=created 2=updated 3=deleted 4=class_changed 5=merged
  write("[%d ms] Track ID=%d  Event=%d  Class=%d  Confidence=%.2f  Range=%.1f",
        timeNow()/10,
        this.Track_ID,
        this.Track_Event_Type,
        this.Track_Class,
        this.Track_Confidence,
        this.Track_Range_m);

  if (this.Track_Event_Type == 5) {   // merge
    write("  MERGE: Track %d absorbed into %d", this.Track_Source_ID, this.Track_ID);
  }
}
```

*Step 2 — Track re-use policy:*
After a track is deleted, its ID should not be immediately reused for a new detections.
If ID is reused immediately: new track inherits state of old track including class label.
Fix: enforce minimum 500ms "cooling period" before a Track ID can be reused.

*Step 3 — Class re-evaluation on new detection:*
When a new detection is associated with an existing (inherited) track:
- If the new detection has class information → override the inherited class
- Never carry a stale class from a previous deleted track

**Test Cases:**
```
TC_CLASS_INH_001: Deleted car track followed by motorcycle → motorcycle gets correct class
TC_CLASS_INH_002: Track ID recycling → minimum 500ms before ID reuse
TC_CLASS_INH_003: Class confidence: newly created track has class confidence = sensor-provided value, not inherited
TC_CLASS_INH_004: Track merge: merged track class = class with higher confidence (not first-come)
```

**Root Cause:** Track ID was immediately recycled after deletion. The new detection for the motorcycle was associated to the recycled track and inherited `Class=Car` and its associated state (width=1.8m). Camera data providing `Class=Motorcycle` was read but the fusion update rule said "only change class if confidence > current" — the inherited car class had confidence 0.72 from the deleted track's history, and the motorcycle camera confidence was 0.69 → class not updated. Fix: on track creation (even from recycled ID), reset class to Unknown and build class from scratch from first detection.

---

## Scenario 13 — Occasional 10ms Jitter in Radar Object Position Causes AEB Flicker

> **Problem:** Instrumentation shows radar object position has occasional 10ms jitter — every 15–20 seconds, a single cycle has a 10ms timestamp gap instead of the normal 25ms cycle. This causes a spike in the calculated velocity derivative (jerk) which briefly triggers the AEB pre-arming logic.

**Investigation Steps:**

*Step 1 — Capture timestamp jitter:*
```capl
variables {
  dword tLast = 0;
  float gJitter_max = 0.0;
  int   gJitter_count = 0;
}

on message Radar::ObjectList_Header {
  dword now = timeNow() / 10;
  dword cycle = now - tLast;
  float jitter = abs((float)cycle - 25.0);

  if (jitter > 3.0) {   // > 3ms from nominal 25ms
    gJitter_count++;
    if (jitter > gJitter_max) gJitter_max = jitter;
    write("[JITTER #%d] Cycle=%d ms (nominal 25ms)  Jitter=%.1f ms",
          gJitter_count, cycle, jitter);
  }

  tLast = now;
}
```

*Step 2 — CAN gateway jitter injection:*
If radar is on a separate CAN bus to fusion ECU, the gateway forwards the message.
Gateway processing time varies (0–5ms) depending on bus load.
With 10ms jitter in gateway forwarding:
- Radar sends at t=0ms → gateway receives at t=0.5ms → forwards when its own CAN cycle fires
- If gateway CAN cycle is 10ms → worst-case forward delay = 10ms → jitter at fusion = 10ms

*Step 3 — AEB jerk threshold:*
```capl
// AEB pre-arm check: if object appears to suddenly close rapidly (jerk spike)
on message FusionECU::FusedObjectList {
  float vel = this.Object_0_Velocity_ms;
  // Calculate jerk from velocity change
  // If jerk > threshold → pre-arm AEB
  // A 10ms jitter with 100m/s velocity = 100 × 0.010 = 1m position error → 1m / 0.025s = 40m/s velocity spike
}
```
A 10ms timestamp error with even a 20 m/s object creates `20 × 0.010 / 0.025 = 8 m/s` velocity jitter → significant AEB flicker.

**Test Cases:**
```
TC_JITTER_001: Radar timestamp jitter < 3ms in 99% of cycles
TC_JITTER_002: Gateway forwarding latency < 5ms peak
TC_JITTER_003: 10ms jitter injected: AEB pre-arm must NOT trigger from timestamp jitter alone
TC_JITTER_004: AEB uses actual timestamps from sensor message (not reception time) for velocity calculation
```

**Root Cause:** Fusion ECU was using the CAN message reception time for velocity calculation, not the timestamp embedded in the radar message. When the gateway introduced variable delay, the reception time jittered but the radar's internal timestamp was stable. Fix: fusion velocity calculation uses `Radar_Timestamp_ms` field from within the message, not `can_RxTime`. This eliminated position jitter from gateway delay variation.

---

## Scenario 14 — Sensor Fusion Validation: How to Set Up a Full Regression Test

> **Scenario:** You join a new project and are asked to set up a fusion regression test suite. The project has 50+ MDF4 logs from past vehicle testing. How do you build the regression framework?

**Step-by-Step Approach:**

*Step 1 — Define what to test:*
```
Regression test KPIs:
  1. Object detection rate (per class)
  2. False positive rate (per km)
  3. Position RMSE (vs ground truth where available)
  4. Velocity RMSE
  5. Track latency (appearance to confirmed)
  6. Track stability (ID switches per object)
  7. Classification accuracy (% correct class)
```

*Step 2 — Select representative logs:*
```
From 50 logs, select:
  5 × highway following (ACC primary use case)
  5 × city driving (high object count)
  5 × night driving (camera degraded)
  5 × rain (all sensors degraded)
  5 × NCAP test scenarios (AEB critical)
  5 × edge cases (tunnel, bridge, gantry)
= 30 canonical regression logs
```

*Step 3 — Python processing pipeline:*
```python
import asammdf
import numpy as np
from scipy.optimize import linear_sum_assignment

def load_fusion_objects(mdf_path):
    mdf = asammdf.MDF(mdf_path)
    timestamps     = mdf.get("FusionECU.Object_0_Timestamp_s").samples
    ranges         = mdf.get("FusionECU.Object_0_Range_m").samples
    velocities     = mdf.get("FusionECU.Object_0_Velocity_ms").samples
    confidences    = mdf.get("FusionECU.Object_0_Confidence").samples
    return timestamps, ranges, velocities, confidences

def rmse(predictions, ground_truth):
    return np.sqrt(np.mean((predictions - ground_truth) ** 2))

def hungarian_association(pred_positions, gt_positions, gate=2.0):
    """Match fusion objects to ground truth objects."""
    n_pred = len(pred_positions)
    n_gt   = len(gt_positions)
    cost   = np.full((n_pred, n_gt), 9999.0)

    for i in range(n_pred):
        for j in range(n_gt):
            dist = abs(pred_positions[i] - gt_positions[j])
            if dist < gate:
                cost[i][j] = dist

    row_ind, col_ind = linear_sum_assignment(cost)
    return [(row_ind[k], col_ind[k]) for k in range(len(row_ind)) if cost[row_ind[k], col_ind[k]] < gate]

def evaluate_log(mdf_path, gt_path):
    # Load fusion and ground truth data
    ts, ranges, vels, confs = load_fusion_objects(mdf_path)
    gt_ranges, gt_vels      = load_ground_truth(gt_path)

    # Associate and compute metrics
    associations = hungarian_association(ranges, gt_ranges)
    detected     = len(associations)
    total_gt     = len(gt_ranges)
    detection_rate = detected / total_gt

    pos_errors = [abs(ranges[i] - gt_ranges[j]) for i, j in associations]
    vel_errors = [abs(vels[i]   - gt_vels[j])   for i, j in associations]

    return {
        "detection_rate": detection_rate,
        "position_rmse":  np.sqrt(np.mean(np.array(pos_errors)**2)),
        "velocity_rmse":  np.sqrt(np.mean(np.array(vel_errors)**2)),
        "false_positives": len(ranges) - detected
    }
```

*Step 4 — Thresholds and CI integration:*
```python
THRESHOLDS = {
    "detection_rate":  0.95,    # ≥ 95%
    "position_rmse":   0.30,    # ≤ 0.3m
    "velocity_rmse":   0.50,    # ≤ 0.5 m/s
    "false_positives": 2.0      # ≤ 2 per 10 km
}

# In CI pipeline (Jenkins/GitLab):
# 1. New fusion SW build triggers
# 2. Pipeline replays 30 canonical logs
# 3. Metrics computed vs thresholds
# 4. If any metric regresses > 5% → FAIL build → email team
```

**Result of this approach:** Systematic regression detection. Any SW change that degrades fusion performance is caught before release, not after customer delivery.

---

## Scenario 15 — Building a Sensor Fusion Test Specification From Scratch

> **Scenario:** Your manager asks you to write the sensor fusion validation test specification for a new ADAS programme. What does a complete test specification include?

**Answer — Test Spec Structure:**

```
SENSOR FUSION VALIDATION TEST SPECIFICATION
Version 1.0 | Programme: XYZ | System: Radar-Camera Fusion

1. SCOPE
   1.1 System under test: Radar-Camera fusion ECU (FUS_ECU_v2.x)
   1.2 Functions covered: Object detection, tracking, classification, output to ADAS
   1.3 In scope sensors: Front LRR, Front camera
   1.4 Not in scope: Side radars (separate spec), LiDAR (future)

2. REFERENCES
   2.1 ISO 26262 — Functional Safety
   2.2 ISO 21448 (SOTIF) — Safety of the Intended Functionality
   2.3 Euro NCAP 2025 Protocol
   2.4 System Requirement Spec SRS_FUS_v1.4

3. TEST ENVIRONMENT
   3.1 Vehicle: ETK (Engineering Test Vehicle) with standard sensor configuration
   3.2 CAN logger: CANoe 17.x with MDF4 logging
   3.3 Ground truth: RTK GPS on ego and target vehicles, Vicon (lab)
   3.4 Test track: [Name] + Public roads (defined routes)

4. OBJECT LIST TESTS
   4.1 Position accuracy: RMSE < 0.30m at 10/20/50/100m range
   4.2 Velocity accuracy: RMSE < 0.50 m/s at all closing speeds
   4.3 Detection rate: ≥ 95% for cars, ≥ 85% for pedestrians, ≥ 90% for cyclists
   4.4 False positive rate: < 2 per 100km on motorway, < 5 per 100km city
   4.5 Track latency: ≤ 500ms from object appearance to confirmed track
   4.6 Track stability: ≤ 0.1 ID switches per tracked object per km

5. CLASSIFICATION TESTS
   5.1 Car, Truck, Pedestrian, Cyclist: accuracy ≥ 90% for each class
   5.2 Class stability: class must not switch faster than once per 5 seconds

6. FUSION LOGIC TESTS
   6.1 Sensor failure: disconnect radar → fusion degrades gracefully
   6.2 Sensor failure: disconnect camera → fusion degrades gracefully
   6.3 Sensor mismatch: if sensor outputs differ > 2m → DTC raised
   6.4 Time synchronisation: all sensors aligned to ≤ 10ms common timestamp

7. NEGATIVE TESTS
   7.1 Ghost target (multi-path) → must not create confirmed track
   7.2 Multi-path suppression: bridge, tunnel entrance → no AEB trigger
   7.3 Stationary clutter (roadside objects > 3° off path) → no track creation

8. STRESS / ROBUSTNESS TESTS
   8.1 Maximum object count (20 simultaneous) → output rate ≥ 25 Hz
   8.2 CAN bus load 80% → object position age ≤ 60ms
   8.3 Sensor cold-start: fusion output within 2 seconds of vehicle start
   8.4 Temperature range: −40°C to +85°C full functional performance

9. PASS/FAIL CRITERIA
   Each test: PASS / FAIL / CONDITIONAL PASS (with known limitation documented)

10. REGRESSION POLICY
    All 30 canonical tests must pass before each SW release
    Any metric regression > 5% from baseline → automatic FAIL
```

---
*File: 03_realtime_scenarios.md | Sensor Fusion Real-Time Debugging | April 2026*
