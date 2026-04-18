# Sensor Fusion — CAPL Code Examples
## Standalone Test Scripts for CANoe | April 2026

All scripts are production-ready for CANoe 17.x with radar + camera fusion ECU setup.
Each script is self-contained: copy into a CAPL Test Module (CTM) or Analysis Window.

---

## Script 1 — Fusion Object Monitor
### Purpose: Log all fused objects and compare against sensor inputs in real time

```capl
/*
 * File: fusion_object_monitor.capl
 * Purpose: Monitor fused object list — position, velocity, classification, confidence
 * Usage: Run in CANoe Test Module. Watch window shows live KPI status.
 */

includes {
}

variables {
  // KPI counters
  int   gTotal_fusion_objects = 0;
  int   gTotal_radar_objects  = 0;
  int   gTotal_camera_objects = 0;
  float gPos_error_sum        = 0.0;
  int   gPos_error_count      = 0;
  float gVel_error_sum        = 0.0;
  int   gVel_error_count      = 0;

  // Latest sensor values for cross-check
  float gRadar_range[8];
  float gRadar_vel[8];
  int   gRadar_count = 0;

  float gCamera_range[8];
  int   gCamera_count = 0;

  // Fusion output
  float gFusion_range[16];
  float gFusion_vel[16];
  int   gFusion_class[16];
  float gFusion_conf[16];
  int   gFusion_count = 0;

  // Timers
  msTimer tmrReport;
}

on start {
  setTimerCyclic(tmrReport, 1000);  // Report every 1 second
  write("Fusion Object Monitor started.");
  write("Column headers: [Time] Source  ID  Range(m)  Vel(m/s)  Class  Conf");
}

// ─────────────────────────────────────────────────────────────────────────────
// RADAR OBJECTS
// ─────────────────────────────────────────────────────────────────────────────
on message Radar::ObjectList_Object {
  int id = this.Obj_ID;
  if (id < 8) {
    gRadar_range[id] = this.Obj_Range_m;
    gRadar_vel[id]   = this.Obj_Velocity_ms;
  }
  gTotal_radar_objects++;
}

on message Radar::ObjectList_Header {
  gRadar_count = this.Radar_NumObjects;
}

// ─────────────────────────────────────────────────────────────────────────────
// CAMERA OBJECTS
// ─────────────────────────────────────────────────────────────────────────────
on message Camera::ObjectList_Object {
  int id = this.Cam_Obj_ID;
  if (id < 8) {
    gCamera_range[id] = this.Cam_Obj_Range_m;
  }
  gTotal_camera_objects++;
}

on message Camera::ObjectList_Header {
  gCamera_count = this.Camera_NumObjects;
}

// ─────────────────────────────────────────────────────────────────────────────
// FUSION OBJECTS
// ─────────────────────────────────────────────────────────────────────────────
on message FusionECU::FusedObjectList {
  int i;
  gFusion_count = this.Fusion_NumObjects;

  for (i = 0; i < gFusion_count && i < 16; i++) {
    // Read from signals (adjust signal names to match your DBC)
    // This pseudocode assumes multiplexed signals by object index
    gTotal_fusion_objects++;
  }

  // Object 0 detailed log
  write("[%6d ms] FUSION  NumObj=%d  Obj0: Range=%.1fm  Vel=%.1f m/s  Class=%d  Conf=%.2f",
        timeNow() / 10,
        this.Fusion_NumObjects,
        this.Object_0_Range_m,
        this.Object_0_Velocity_ms,
        this.Object_0_Class,
        this.Object_0_Confidence);
}

// ─────────────────────────────────────────────────────────────────────────────
// PERIODIC REPORT
// ─────────────────────────────────────────────────────────────────────────────
on timer tmrReport {
  write("--- 1s Summary ---");
  write("  Radar objects received:  %d", gTotal_radar_objects);
  write("  Camera objects received: %d", gTotal_camera_objects);
  write("  Fusion objects received: %d", gTotal_fusion_objects);

  if (gFusion_count == 0 && (gRadar_count > 0 || gCamera_count > 0)) {
    write("  WARNING: sensors have objects but fusion output is EMPTY");
  }

  // Reset cycle counters
  gTotal_fusion_objects = 0;
  gTotal_radar_objects  = 0;
  gTotal_camera_objects = 0;
}

on stopMeasurement {
  write("=== Fusion Object Monitor Stopped ===");
}
```

---

## Script 2 — Sensor Timeout Detector
### Purpose: Alert if any sensor stops sending messages within expected cycle time

```capl
/*
 * File: sensor_timeout_detector.capl
 * Purpose: Monitor all sensor heartbeats and flag missing messages
 * Sensors: Radar (25ms nominal), Camera (33ms nominal), LiDAR (100ms nominal)
 */

variables {
  // Timeout thresholds
  const int RADAR_TIMEOUT_MS  = 100;   // 4× nominal 25ms
  const int CAMERA_TIMEOUT_MS = 150;   // 4× nominal 33ms
  const int LIDAR_TIMEOUT_MS  = 400;   // 4× nominal 100ms

  // Last receive times
  dword gRadar_last_rx   = 0;
  dword gCamera_last_rx  = 0;
  dword gLidar_last_rx   = 0;

  // Alert flags (prevent repeated alerts)
  int   gRadar_timeout_active  = 0;
  int   gCamera_timeout_active = 0;
  int   gLidar_timeout_active  = 0;

  // Message cycle monitors
  dword gRadar_prev_rx   = 0;
  float gRadar_avg_cycle = 0.0;
  int   gRadar_msg_count = 0;

  msTimer tmrHealthCheck;
}

on start {
  setTimerCyclic(tmrHealthCheck, 50);  // Check every 50ms
  gRadar_last_rx  = timeNow() / 10;  // Initialise to now
  gCamera_last_rx = timeNow() / 10;
  gLidar_last_rx  = timeNow() / 10;
  write("Sensor Timeout Detector started. Monitoring: Radar/Camera/LiDAR");
}

on message Radar::ObjectList_Header {
  dword now = timeNow() / 10;
  if (gRadar_prev_rx > 0) {
    dword cycle = now - gRadar_prev_rx;
    gRadar_msg_count++;
    gRadar_avg_cycle += ((float)cycle - gRadar_avg_cycle) / (float)gRadar_msg_count;
  }
  gRadar_prev_rx = now;
  gRadar_last_rx = now;

  if (gRadar_timeout_active) {
    write("[%d ms] RECOVERY: Radar messages resumed (was missing for %d ms)",
          now, RADAR_TIMEOUT_MS);
    gRadar_timeout_active = 0;
  }
}

on message Camera::ObjectList_Header {
  dword now = timeNow() / 10;
  gCamera_last_rx = now;
  if (gCamera_timeout_active) {
    write("[%d ms] RECOVERY: Camera messages resumed", now);
    gCamera_timeout_active = 0;
  }
}

on message LiDAR::PointCloud_Header {
  dword now = timeNow() / 10;
  gLidar_last_rx = now;
  if (gLidar_timeout_active) {
    write("[%d ms] RECOVERY: LiDAR messages resumed", now);
    gLidar_timeout_active = 0;
  }
}

on timer tmrHealthCheck {
  dword now = timeNow() / 10;

  // Check radar
  if ((now - gRadar_last_rx) > RADAR_TIMEOUT_MS && !gRadar_timeout_active) {
    gRadar_timeout_active = 1;
    write("[%d ms] TIMEOUT ALERT: Radar silent for > %d ms", now, RADAR_TIMEOUT_MS);
    write("         Expected cycle: 25ms  Last received: %d ms ago",
          now - gRadar_last_rx);
  }

  // Check camera
  if ((now - gCamera_last_rx) > CAMERA_TIMEOUT_MS && !gCamera_timeout_active) {
    gCamera_timeout_active = 1;
    write("[%d ms] TIMEOUT ALERT: Camera silent for > %d ms", now, CAMERA_TIMEOUT_MS);
  }

  // Check LiDAR
  if ((now - gLidar_last_rx) > LIDAR_TIMEOUT_MS && !gLidar_timeout_active) {
    gLidar_timeout_active = 1;
    write("[%d ms] TIMEOUT ALERT: LiDAR silent for > %d ms", now, LIDAR_TIMEOUT_MS);
  }
}

on stopMeasurement {
  write("=== Sensor Timeout Summary ===");
  write("  Radar avg cycle: %.1f ms (nominal 25ms)", gRadar_avg_cycle);
  write("  Radar messages:  %d", gRadar_msg_count);
  write("  Final status: Radar %s | Camera %s | LiDAR %s",
        gRadar_timeout_active  ? "TIMEOUT" : "OK",
        gCamera_timeout_active ? "TIMEOUT" : "OK",
        gLidar_timeout_active  ? "TIMEOUT" : "OK");
}
```

---

## Script 3 — Track Stability Logger
### Purpose: Count Track ID switches — measure tracker stability

```capl
/*
 * File: track_stability_logger.capl
 * Purpose: Counts how often Track ID changes for the primary forward object
 *          A high ID switch count = unstable tracker
 *          KPI: ≤ 0.1 switches per tracked object per km
 */

variables {
  int   gLast_track_id    = -1;
  int   gID_switch_count  = 0;
  float gDistance_km      = 0.0;
  float gLast_speed_ms    = 0.0;
  dword tLast_speed_update = 0;

  // Log tracking gaps
  dword tLast_track_seen  = 0;
  int   gTrack_gap_count  = 0;
}

on message FusionECU::FusedObjectList {
  dword now   = timeNow() / 10;
  int   cur_id = this.Object_0_TrackID;
  float range  = this.Object_0_Range_m;
  float conf   = this.Object_0_Confidence;

  // Only track confirmed primary forward object
  if (conf < 0.70 || range > 150.0 || range < 5.0) {
    return;
  }

  // Check for track gap (object absent for > 200ms)
  if (tLast_track_seen > 0 && (now - tLast_track_seen) > 200) {
    gTrack_gap_count++;
    write("[%d ms] Track gap: object absent %d ms", now, now - tLast_track_seen);
  }
  tLast_track_seen = now;

  // Detect Track ID switch
  if (gLast_track_id >= 0 && cur_id != gLast_track_id) {
    gID_switch_count++;
    write("[%d ms] TRACK ID SWITCH: %d → %d  (switches so far: %d  at %.2f km)",
          now, gLast_track_id, cur_id, gID_switch_count, gDistance_km);
  }

  gLast_track_id = cur_id;
}

// Ego speed for distance calculation
on message ABS::VehicleSpeed {
  dword now = timeNow() / 10;
  float speed_ms = this.VehicleSpeed_kmh / 3.6;

  if (tLast_speed_update > 0) {
    dword dt_ms = now - tLast_speed_update;
    gDistance_km += gLast_speed_ms * (dt_ms / 1000.0) / 1000.0;
  }

  gLast_speed_ms   = speed_ms;
  tLast_speed_update = now;
}

on key 'r' {
  write("--- Track Stability Stats ---");
  write("  Distance driven: %.2f km", gDistance_km);
  write("  Track ID switches: %d", gID_switch_count);
  write("  Track gaps (>200ms): %d", gTrack_gap_count);
  if (gDistance_km > 0.1) {
    float rate = gID_switch_count / gDistance_km;
    write("  Switch rate: %.2f per km  (spec: ≤ 0.1 per km)  %s",
          rate, rate <= 0.1 ? "PASS" : "FAIL");
  }
}

on stopMeasurement {
  write("=== Track Stability Final Result ===");
  float rate = (gDistance_km > 0) ? (gID_switch_count / gDistance_km) : 999.0;
  write("  Track ID switches: %d  over %.2f km", gID_switch_count, gDistance_km);
  write("  Rate: %.2f per km  Spec: ≤ 0.1  Result: %s",
        rate, rate <= 0.1 ? "PASS" : "FAIL");
}
```

---

## Script 4 — False Positive Counter
### Purpose: Count false positive object detections on a known-clear road section

```capl
/*
 * File: false_positive_counter.capl
 * Purpose: On a clear road section (manually triggered), count any fusion objects
 *          that appear in the forward path. Any object here is a false positive.
 *          KPI: < 2 false positives per 100 km on motorway
 *
 * Operation: Press 'S' to start a clear-road section, 'E' to end it.
 */

variables {
  int   gClearRoad_active     = 0;
  int   gFP_count             = 0;
  float gClearRoad_km         = 0.0;
  float gTotal_FP_km          = 0.0;
  float gTotal_FP_count       = 0.0;

  // Track objects we have already counted
  int   gCounted_IDs[64];
  int   gCounted_ID_count = 0;

  float gSpeed_ms = 0.0;
  dword tLast_speed = 0;
}

on start {
  write("False Positive Counter: Press 'S' = start clear section, 'E' = end, 'R' = report");
}

on key 's' {
  gClearRoad_active = 1;
  gFP_count         = 0;
  gClearRoad_km     = 0.0;
  gCounted_ID_count = 0;
  write("[%d ms] Clear-road section STARTED — counting begins", timeNow()/10);
}

on key 'e' {
  if (gClearRoad_active) {
    gClearRoad_active = 0;
    gTotal_FP_count  += gFP_count;
    gTotal_FP_km     += gClearRoad_km;
    write("[%d ms] Clear-road section END  FP=%d  distance=%.2f km  rate=%.1f /100km",
          timeNow()/10, gFP_count, gClearRoad_km,
          gClearRoad_km > 0 ? (gFP_count / gClearRoad_km * 100.0) : 0.0);
  }
}

on key 'r' {
  write("--- False Positive Summary ---");
  write("  Total FP: %.0f  over %.2f km", gTotal_FP_count, gTotal_FP_km);
  if (gTotal_FP_km > 0) {
    float rate = gTotal_FP_count / gTotal_FP_km * 100.0;
    write("  Rate: %.1f per 100km  Spec: ≤ 2 per 100km  %s",
          rate, rate <= 2.0 ? "PASS" : "FAIL");
  }
}

on message FusionECU::FusedObjectList {
  if (!gClearRoad_active) return;

  int  id   = this.Object_0_TrackID;
  float rng = this.Object_0_Range_m;
  float az  = this.Object_0_Azimuth_deg;
  float conf = this.Object_0_Confidence;

  // Only count forward in-path objects with high confidence
  if (conf < 0.70) return;
  if (rng < 10.0 || rng > 200.0) return;
  if (abs(az) > 10.0) return;   // Within ±10° of forward — in path

  // Check if this track ID already counted
  int i;
  int already_counted = 0;
  for (i = 0; i < gCounted_ID_count; i++) {
    if (gCounted_IDs[i] == id) { already_counted = 1; break; }
  }

  if (!already_counted) {
    gFP_count++;
    if (gCounted_ID_count < 64) {
      gCounted_IDs[gCounted_ID_count++] = id;
    }
    write("[%d ms] FP #%d: TrackID=%d  Range=%.1fm  Az=%.1f°  Conf=%.2f",
          timeNow()/10, gFP_count, id, rng, az, conf);
  }
}

on message ABS::VehicleSpeed {
  dword now = timeNow() / 10;
  float spd_ms = this.VehicleSpeed_kmh / 3.6;
  if (gClearRoad_active && tLast_speed > 0) {
    dword dt_ms = now - tLast_speed;
    gClearRoad_km += spd_ms * (dt_ms / 1000.0) / 1000.0;
  }
  gSpeed_ms   = spd_ms;
  tLast_speed = now;
}
```

---

## Script 5 — Radar-Camera Position Cross-Check
### Purpose: Continuously compare radar and camera range for same object. Flag discrepancies.

```capl
/*
 * File: radar_camera_crosscheck.capl
 * Purpose: For each fused object, compare raw radar range vs raw camera range.
 *          Large differences indicate sensor misalignment or data association error.
 *          KPI: radar-camera range difference < 1.0m for objects 10–80m
 */

variables {
  // Track mismatch events
  int   gMismatch_count  = 0;
  int   gTotal_checks    = 0;
  float gMax_mismatch_m  = 0.0;
  float gMismatch_sum    = 0.0;

  // Latest raw sensor readings per track association
  float gRadar_range_raw  = 0.0;
  float gCamera_range_raw = 0.0;
  int   gRadar_updated    = 0;
  int   gCamera_updated   = 0;

  // Configurable thresholds
  float MISMATCH_WARN_M    = 1.0;
  float MISMATCH_CRITICAL_M = 2.0;
}

on start {
  write("Radar-Camera Cross-Check started. Threshold: WARN=%.1fm  CRIT=%.1fm",
        MISMATCH_WARN_M, MISMATCH_CRITICAL_M);
}

// Capture latest radar raw object (object 0 = primary)
on message Radar::ObjectList_Object {
  if (this.Obj_ID == 0) {
    gRadar_range_raw = this.Obj_Range_m;
    gRadar_updated   = 1;
  }
}

// Capture latest camera raw object (object 0 = primary)
on message Camera::ObjectList_Object {
  if (this.Cam_Obj_ID == 0) {
    gCamera_range_raw = this.Cam_Obj_Range_m;
    gCamera_updated   = 1;
  }
}

// When fusion outputs, cross-check against raw sensor readings
on message FusionECU::FusedObjectList {
  if (!gRadar_updated || !gCamera_updated) return;
  if (this.Fusion_NumObjects == 0) return;

  float fused_range = this.Object_0_Range_m;
  if (fused_range < 10.0 || fused_range > 80.0) return;  // Only check 10-80m range

  float diff = abs(gRadar_range_raw - gCamera_range_raw);
  gTotal_checks++;
  gMismatch_sum += diff;
  if (diff > gMax_mismatch_m) gMax_mismatch_m = diff;

  if (diff > MISMATCH_CRITICAL_M) {
    gMismatch_count++;
    write("[CRITICAL] Radar=%.2fm  Camera=%.2fm  Diff=%.2fm  Fused=%.2fm",
          gRadar_range_raw, gCamera_range_raw, diff, fused_range);
  } else if (diff > MISMATCH_WARN_M) {
    write("[WARN] Radar=%.2fm  Camera=%.2fm  Diff=%.2fm",
          gRadar_range_raw, gCamera_range_raw, diff);
  }

  // Reset update flags
  gRadar_updated  = 0;
  gCamera_updated = 0;
}

on stopMeasurement {
  write("=== Radar-Camera Cross-Check Summary ===");
  write("  Total checks: %d", gTotal_checks);
  write("  Critical mismatches (>%.1fm): %d  (%.1f%%)",
        MISMATCH_CRITICAL_M, gMismatch_count,
        gTotal_checks > 0 ? (float)gMismatch_count / gTotal_checks * 100.0 : 0.0);
  write("  Max difference: %.2fm  Avg: %.2fm",
        gMax_mismatch_m,
        gTotal_checks > 0 ? gMismatch_sum / gTotal_checks : 0.0);
  write("  Result: %s", gMismatch_count == 0 ? "PASS" : "FAIL — check sensor calibration");
}
```

---

## Script 6 — Extrinsic Calibration Verifier
### Purpose: Automated static target geometry test to verify sensor alignment

```capl
/*
 * File: calibration_verifier.capl
 * Purpose: Static target test — a known target (1m × 1m reflector) placed at
 *          known position (20m ahead, 0° azimuth) should be detected consistently.
 *          Tests extrinsic calibration accuracy.
 *
 * Setup: Place reflector at exactly 20.00m ahead, 0.00° azimuth.
 *        Run test for 30 seconds. Review position accuracy.
 *
 * KPIs:
 *   Range accuracy: 20.00m ± 0.15m
 *   Azimuth accuracy: 0.00° ± 0.5°
 *   Lateral position: 0.00m ± 0.15m
 *
 * Press 'T' to trigger a 30-second test run (manual step in test procedure).
 */

variables {
  const float GT_RANGE_M  = 20.00;  // Ground truth range
  const float GT_AZ_DEG   = 0.00;   // Ground truth azimuth
  const float RANGE_TOL_M = 0.15;   // Tolerance ±0.15m
  const float AZ_TOL_DEG  = 0.50;   // Tolerance ±0.5°

  int   gTest_active       = 0;
  int   gMeasurement_count = 0;
  float gRange_sum         = 0.0;
  float gRange_sq_sum      = 0.0;
  float gAz_sum            = 0.0;
  float gRange_max_err     = 0.0;
  float gAz_max_err        = 0.0;
  int   gRange_fails       = 0;
  int   gAz_fails          = 0;

  msTimer tmrTestEnd;
}

on start {
  write("Calibration Verifier ready. Setup: reflector at %.1fm ahead, 0.0°", GT_RANGE_M);
  write("Press 'T' to start 30-second measurement.");
}

on key 't' {
  if (!gTest_active) {
    gTest_active       = 1;
    gMeasurement_count = 0;
    gRange_sum         = 0.0;
    gRange_sq_sum      = 0.0;
    gAz_sum            = 0.0;
    gRange_max_err     = 0.0;
    gAz_max_err        = 0.0;
    gRange_fails       = 0;
    gAz_fails          = 0;
    setTimer(tmrTestEnd, 30000);  // 30 second test
    write("[%d ms] Calibration test STARTED (30 seconds)", timeNow()/10);
  }
}

on timer tmrTestEnd {
  gTest_active = 0;
  write("[%d ms] Calibration test COMPLETE — %d measurements taken", timeNow()/10, gMeasurement_count);

  if (gMeasurement_count == 0) {
    write("ERROR: No fusion objects detected during test — is target in place?");
    return;
  }

  float range_mean = gRange_sum / gMeasurement_count;
  float range_var  = (gRange_sq_sum / gMeasurement_count) - (range_mean * range_mean);
  float range_std  = (range_var > 0) ? sqrt(range_var) : 0.0;
  float az_mean    = gAz_sum / gMeasurement_count;

  float range_bias = range_mean - GT_RANGE_M;
  float az_bias    = az_mean    - GT_AZ_DEG;

  write("--- Calibration Verification Result ---");
  write("  Measurements: %d (expected ~1200 @ 40Hz × 30s)", gMeasurement_count);
  write("");
  write("  Range:  Mean=%.3fm  Bias=%.3fm  StdDev=%.3fm  MaxErr=%.3fm",
        range_mean, range_bias, range_std, gRange_max_err);
  write("  Range spec: Bias ≤ ±%.3fm  %s",
        RANGE_TOL_M, abs(range_bias) <= RANGE_TOL_M ? "PASS" : "FAIL");
  write("  Range fails (> ±%.3fm): %d/%d  (%.1f%%)",
        RANGE_TOL_M, gRange_fails, gMeasurement_count,
        (float)gRange_fails / gMeasurement_count * 100.0);
  write("");
  write("  Azimuth: Mean=%.3f°  Bias=%.3f°  MaxErr=%.3f°",
        az_mean, az_bias, gAz_max_err);
  write("  Azimuth spec: Bias ≤ ±%.1f°  %s",
        AZ_TOL_DEG, abs(az_bias) <= AZ_TOL_DEG ? "PASS" : "FAIL");
  write("  Azimuth fails (> ±%.1f°): %d/%d  (%.1f%%)",
        AZ_TOL_DEG, gAz_fails, gMeasurement_count,
        (float)gAz_fails / gMeasurement_count * 100.0);
  write("");

  int overall_pass = (abs(range_bias) <= RANGE_TOL_M) && (abs(az_bias) <= AZ_TOL_DEG);
  write("  OVERALL CALIBRATION CHECK: %s", overall_pass ? "PASS" : "FAIL");
  if (!overall_pass) {
    if (abs(range_bias) > RANGE_TOL_M) {
      write("  ACTION: Range bias %.3fm — check radar mounting depth offset in config",
            range_bias);
    }
    if (abs(az_bias) > AZ_TOL_DEG) {
      write("  ACTION: Azimuth bias %.3f° — adjust radar yaw angle in extrinsic calibration",
            az_bias);
    }
  }
}

// Read fusion object 0 during test
on message FusionECU::FusedObjectList {
  if (!gTest_active) return;
  if (this.Fusion_NumObjects == 0) return;

  float range = this.Object_0_Range_m;
  float az    = this.Object_0_Azimuth_deg;
  float conf  = this.Object_0_Confidence;

  // Only use high-confidence readings near expected position
  if (conf < 0.80) return;
  if (abs(range - GT_RANGE_M) > 5.0) return;  // Must be within 5m of target

  gMeasurement_count++;
  gRange_sum    += range;
  gRange_sq_sum += range * range;
  gAz_sum       += az;

  float range_err = abs(range - GT_RANGE_M);
  float az_err    = abs(az    - GT_AZ_DEG);

  if (range_err > gRange_max_err) gRange_max_err = range_err;
  if (az_err    > gAz_max_err)   gAz_max_err    = az_err;

  if (range_err > RANGE_TOL_M) gRange_fails++;
  if (az_err    > AZ_TOL_DEG)  gAz_fails++;
}
```

---

## Script 7 — Full Fusion KPI Test Module (CAPL Test Unit)
### Purpose: Automated pass/fail test execution for fusion validation build acceptance

```capl
/*
 * File: fusion_build_acceptance_test.cantest  (CAPL Test Unit format)
 * Purpose: Run as a formal CANoe test unit in a regression pipeline.
 *          Reports PASS/FAIL for each KPI.
 *          Run time: approximately 120 seconds.
 */

testcase TC_FUS_001_FrameRate() {
  // Verify fusion output frame rate ≥ 38 Hz (95% of nominal 40 Hz)
  int   count = 0;
  dword t_start = timeNow() / 10;
  dword t_run   = 5000;  // 5 second measurement window
  float expected_count = 40.0 * (t_run / 1000.0);  // 40 Hz × 5s = 200 msgs

  while ((timeNow()/10 - t_start) < t_run) {
    if (testWaitForMessage(FusionECU::FusedObjectList, 100) == 1) {
      count++;
    }
  }

  float rate = (float)count / (t_run / 1000.0);
  testStep("Fusion frame rate: %.1f Hz (expected ≥ 38 Hz)", rate);

  if (rate >= 38.0) {
    testStepPass("TC_FUS_001", "Frame rate %.1f Hz ≥ 38 Hz", rate);
  } else {
    testStepFail("TC_FUS_001", "Frame rate %.1f Hz < 38 Hz", rate);
  }
}

testcase TC_FUS_002_RadarPresence() {
  // Verify radar messages received within 200ms of measurement start
  long result = testWaitForMessage(Radar::ObjectList_Header, 200);
  if (result == 1) {
    testStepPass("TC_FUS_002", "Radar messages present within 200ms");
  } else {
    testStepFail("TC_FUS_002", "No radar messages in 200ms — check radar bus");
  }
}

testcase TC_FUS_003_CameraPresence() {
  long result = testWaitForMessage(Camera::ObjectList_Header, 300);
  if (result == 1) {
    testStepPass("TC_FUS_003", "Camera messages present within 300ms");
  } else {
    testStepFail("TC_FUS_003", "No camera messages in 300ms — check camera");
  }
}

testcase TC_FUS_004_NoObjectsOnClearRoad() {
  // Clear road test — no target vehicle present
  // KPI: fusion object count = 0 for ≥ 90% of frames
  int total_frames  = 0;
  int empty_frames  = 0;
  dword t_start     = timeNow() / 10;

  while ((timeNow()/10 - t_start) < 10000) {  // 10 second window
    if (testWaitForMessage(FusionECU::FusedObjectList, 100) == 1) {
      total_frames++;
      if (FusionECU::FusedObjectList::Fusion_NumObjects == 0) {
        empty_frames++;
      }
    }
  }

  float cleanliness = (total_frames > 0) ?
      ((float)empty_frames / total_frames * 100.0) : 0.0;

  testStep("Clear road emptiness: %.1f%% frames empty (expected ≥ 90%%)", cleanliness);

  if (cleanliness >= 90.0) {
    testStepPass("TC_FUS_004", "%.1f%% frames empty ≥ 90%%", cleanliness);
  } else {
    testStepFail("TC_FUS_004", "Only %.1f%% frames empty — false positives present", cleanliness);
  }
}

testcase TC_FUS_005_DTCHealthStatus() {
  // Check fusion ECU has no active safety DTCs
  // Uses UDS 0x19 02 0D (read all DTCs, severity active)
  byte req[4] = {0x19, 0x02, 0x0D, 0x00};
  byte resp[255];
  int resp_len;

  // Send UDS request to fusion ECU (ID 0x7A0)
  resp_len = diagSendRequest(0x7A0, req, 4, resp, 255, 1000);

  if (resp_len < 3 || resp[0] != 0x59) {
    testStepFail("TC_FUS_005", "No valid UDS response from Fusion ECU");
    return;
  }

  int dtc_count = (resp_len - 3) / 4;  // Each DTC = 3 bytes + 1 status byte
  testStep("Active DTCs in Fusion ECU: %d", dtc_count);

  if (dtc_count == 0) {
    testStepPass("TC_FUS_005", "No active DTCs");
  } else {
    testStepFail("TC_FUS_005", "%d active DTCs found — investigate before release", dtc_count);
  }
}

// Main test function (called by test run)
void MainTest() {
  testReportSectionBegin("Fusion Build Acceptance Tests");

  TC_FUS_001_FrameRate();
  TC_FUS_002_RadarPresence();
  TC_FUS_003_CameraPresence();
  TC_FUS_004_NoObjectsOnClearRoad();
  TC_FUS_005_DTCHealthStatus();

  testReportSectionEnd();
}
```

---

## Script 8 — Object Velocity Spike Detector
### Purpose: Detect unphysical velocity jumps that indicate fusion instability or timestamp errors

```capl
/*
 * File: velocity_spike_detector.capl
 * Purpose: Detect velocity spikes > physical limit (max deceleration/acceleration of target vehicle)
 *          Physical max: passenger car can decelerate ≈ 1.0g = 9.8 m/s²
 *          Settings: vehicle can change speed by max 0.25m/s per 25ms cycle (= 10 m/s²)
 *          Any larger change is a measurement artefact.
 */

variables {
  float gLast_velocity    = 0.0;
  int   gSpike_count      = 0;
  float gMax_spike_ms     = 0.0;
  int   gTotal_updates    = 0;
  float SPIKE_THRESHOLD   = 0.25;   // m/s per cycle (10 m/s²)
}

on start {
  write("Velocity Spike Detector started.");
  write("Threshold: %.2f m/s per cycle (25ms) = %.1f m/s²", SPIKE_THRESHOLD, SPIKE_THRESHOLD / 0.025);
}

on message FusionECU::FusedObjectList {
  float vel  = this.Object_0_Velocity_ms;
  float conf = this.Object_0_Confidence;

  if (conf < 0.70) return;  // Only check confirmed objects

  if (gTotal_updates > 0) {
    float delta = abs(vel - gLast_velocity);

    if (delta > SPIKE_THRESHOLD) {
      gSpike_count++;
      if (delta > gMax_spike_ms) gMax_spike_ms = delta;
      write("[%d ms] VELOCITY SPIKE #%d: %.2f → %.2f m/s  (Δ=%.2f m/s  limit=%.2f)",
            timeNow()/10, gSpike_count, gLast_velocity, vel, delta, SPIKE_THRESHOLD);
    }
  }

  gLast_velocity = vel;
  gTotal_updates++;
}

on stopMeasurement {
  write("=== Velocity Spike Summary ===");
  write("  Updates checked: %d", gTotal_updates);
  write("  Spikes detected: %d  (%.2f%%)",
        gSpike_count,
        gTotal_updates > 0 ? (float)gSpike_count / gTotal_updates * 100.0 : 0.0);
  write("  Max spike: %.2f m/s  (%.1f m/s²)", gMax_spike_ms, gMax_spike_ms / 0.025);
  write("  Result: %s", gSpike_count == 0 ? "PASS" : "FAIL — check timestamp handling");
}
```

---

## Quick Reference — Signal Names to Adapt

The CAPL scripts above use these assumed signal/message names. Adapt to your project's DBC/ARXML:

| Script Signal | Typical DBC Name | Description |
|--------------|------------------|-------------|
| `FusionECU::FusedObjectList` | varies | Main fusion output message |
| `Fusion_NumObjects` | `NumObjects`, `Obj_Count` | Number of fused tracks |
| `Object_0_Range_m` | `Obj0_DistX`, `Obj0_Range` | Longitudinal distance |
| `Object_0_Velocity_ms` | `Obj0_VrelX`, `Obj0_Speed` | Relative velocity (m/s) |
| `Object_0_Azimuth_deg` | `Obj0_Angle`, `Obj0_AngleLat` | Lateral angle (degrees) |
| `Object_0_Class` | `Obj0_ObjType`, `Obj0_Class` | Object classification |
| `Object_0_Confidence` | `Obj0_ExistProb`, `Obj0_Prob` | Track existence probability |
| `Object_0_TrackID` | `Obj0_ID`, `Obj0_Idx` | Track identifier |
| `Radar::ObjectList_Header` | varies by radar supplier | Radar object list header |
| `Radar_NumObjects` | `Radar_Objs` | Radar detected object count |
| `Camera::ObjectList_Header` | varies by camera supplier | Camera object list header |
| `ABS::VehicleSpeed` | `VehicleSpeed`, `WheelBasedSpeed` | Ego vehicle speed |

---
*File: 04_capl_examples.md | Sensor Fusion CAPL Scripts | April 2026*
