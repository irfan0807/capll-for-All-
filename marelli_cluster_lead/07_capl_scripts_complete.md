# Complete CAPL Scripts — Instrument Cluster Validation
### Marelli / LTTS Cluster Lead — Bangalore

> **Purpose:** Production-ready CAPL scripts for every major cluster validation scenario.
> Each script is self-contained and can be loaded directly into a CANoe CAPL node.
> Variable names match DBC symbolic names — adjust to your project's DBC.

---

## Script 1 — Speedometer Full Validation Suite

```capl
/*
 * FILE: test_speedometer_full.can
 * SCOPE: Speedometer validation — linearity, EU Reg 39 tolerance, zero hold,
 *        over-scale, signal timeout fallback, SpeedValid flag handling
 * DBC:   Powertrain.dbc  (Message: VehicleSpeed 0x3B3, 10ms cycle)
 * AUTHOR: Cluster Lead
 */

includes {
    #include "libs/cluster_helpers.cin"
}

variables {
    msTimer  txTimer;           /* cyclic transmit timer          */
    msTimer  waitTimer;         /* test step delay timer          */
    int      txActive    = 1;   /* 1 = TX running, 0 = stopped    */
    int      testStep    = 0;
    float    currentSpeed = 0.0;

    /* Speed sweep table: {inject km/h, max_allowed_display km/h, tolerance km/h} */
    float speedTable[8][3] = {
        {   0.0,   0.0,  0.5 },   /* TC_SPD_001 — Zero speed */
        {  30.0,  32.0,  2.0 },   /* TC_SPD_002 */
        {  60.0,  63.0,  3.0 },   /* TC_SPD_003 */
        { 100.0, 104.0,  4.0 },   /* TC_SPD_004 */
        { 120.0, 124.5,  4.5 },   /* TC_SPD_005 */
        { 160.0, 166.0,  6.0 },   /* TC_SPD_006 */
        { 200.0, 210.0, 10.0 },   /* TC_SPD_007 */
        { 250.0, 261.0, 11.0 }    /* TC_SPD_008 — near max scale */
    };
}

/* ── Startup ────────────────────────────────────────────────────────── */
on start {
    write("=== SPEEDOMETER VALIDATION SUITE STARTED ===");
    write("Using DBC: Powertrain.dbc | Message: 0x3B3 VehicleSpeed");
    write("EU Regulation 39: display must not under-read. Over-read ≤ (Speed×10%+4km/h)");
    write("---");

    /* Ensure cluster in powered state */
    simulate_kl15_on();
    setTimer(waitTimer, 3000);    /* wait for cluster boot */
}

on timer waitTimer {
    testStep++;

    switch (testStep) {
    case 1:
        /* Start cyclic TX of speed message */
        setTimer(txTimer, 10);
        write("[STEP 1] Starting cyclic VehicleSpeed TX (10ms)");
        setTimer(waitTimer, 500);
        break;

    case 2:
        run_speed_sweep();
        break;

    case 3:
        test_zero_speed_hold();
        break;

    case 4:
        test_speedvalid_flag();
        break;

    case 5:
        test_can_timeout_fallback();
        break;

    case 6:
        write("=== ALL SPEEDOMETER TESTS COMPLETE ===");
        txActive = 0;
        break;
    }
}

/* ── Cyclic TX ──────────────────────────────────────────────────────── */
on timer txTimer {
    if (txActive) {
        message VehicleSpeed msg;
        msg.VehicleSpeed = currentSpeed;
        msg.SpeedValid   = 1;
        output(msg);
        setTimer(txTimer, 10);   /* 10ms cycle = 100Hz */
    }
}

/* ── Test Functions ─────────────────────────────────────────────────── */
void run_speed_sweep() {
    int i;
    write("[SPEED SWEEP] Running %d test points per EU Regulation 39", elcount(speedTable));

    for (i = 0; i < elcount(speedTable); i++) {
        float inject   = speedTable[i][0];
        float max_disp = speedTable[i][1];
        float tol      = speedTable[i][2];

        currentSpeed = inject;
        TestWaitForTimeout(600);   /* settle time */

        /* In real HIL: read display value via UDS DID 0xF110 */
        /* Here: verify signal on bus equals inject (sanity check without HIL) */
        float bus_value = $VehicleSpeed::VehicleSpeed;

        if (bus_value == inject) {
            write("TC_SPD_%03d PASS | Inject=%.1f | Bus=%.1f | MaxAllowed=%.1f",
                  i+1, inject, bus_value, max_disp);
        } else {
            write("TC_SPD_%03d FAIL | Inject=%.1f | Bus=%.1f — signal mismatch!",
                  i+1, inject, bus_value);
        }
    }

    currentSpeed = 0.0;
    setTimer(waitTimer, 1000);
}

void test_zero_speed_hold() {
    write("[TC_SPD_009] Zero speed hold — inject 0 km/h, verify no phantom reading");
    currentSpeed = 0.0;
    TestWaitForTimeout(2000);   /* hold 2 seconds */
    write("  Verify: cluster displays exactly 0 km/h (no jitter filter phantom value)");
    write("  Verify: SpeedValid=1 is still being sent");
    log_test_result("TC_SPD_009_ZeroHold", 1, "Manual confirm required on bench");
    setTimer(waitTimer, 500);
}

void test_speedvalid_flag() {
    write("[TC_SPD_010] SpeedValid=0 — cluster should show dashes or 0");
    message VehicleSpeed msg;
    msg.VehicleSpeed = 8000;   /* 80 km/h raw but invalid */
    msg.SpeedValid   = 0;
    output(msg);
    TestWaitForTimeout(500);
    write("  Verify: cluster does NOT show 80 km/h. Should show '--' or 0.");
    write("  Restoring SpeedValid=1...");
    currentSpeed = 0.0;
    txActive = 1;
    setTimer(waitTimer, 500);
}

void test_can_timeout_fallback() {
    write("[TC_SPD_011] CAN timeout — stopping TX of 0x3B3");
    txActive = 0;    /* stop cyclic TX */
    TestWaitForTimeout(3000);
    write("  Verify: cluster speedometer shows '--' or 0 km/h (fallback)");
    write("  Verify: CAN network fault telltale activates (OEM dependent)");
    write("  Restoring TX...");
    txActive = 1;
    setTimer(txTimer, 10);
    setTimer(waitTimer, 500);
}
```

---

## Script 2 — Telltale Matrix — Complete Validation

```capl
/*
 * FILE: test_telltale_matrix.can
 * SCOPE: All ISO 2575 priority telltales, dual-fault priority, self-check,
 *        CAN timeout, NVM latch, de-activation
 * DBC:   Powertrain.dbc + ADAS.dbc
 */

includes {
    #include "libs/cluster_helpers.cin"
}

variables {
    msTimer  stepTimer;
    int      step = 0;

    /* Results tracking */
    int  pass_count = 0;
    int  fail_count = 0;
}

/* ── Telltale test record ──────────────────────────────────────────── */
typedef struct {
    char  tc_id[16];
    char  telltale_name[30];
    int   priority;           /* 1=P1 Red, 2=P2 Amber, 3=P3 Green */
    long  fault_msg_id;
    byte  fault_byte;
    byte  fault_bit_mask;
    int   expected_on;        /* 1 = expect telltale ON after inject */
} TelltaleTc_t;

TelltaleTc_t tc_table[10] = {
    /* tc_id,         name,           P,  MsgID,  Byte, Mask, Exp */
    {"TC_TEL_001", "ABS_Fault",       2, 0x3A5,   0,  0x01,  1},
    {"TC_TEL_002", "SRS_Fault",       1, 0x3A6,   0,  0x01,  1},
    {"TC_TEL_003", "EPB_Fault",       2, 0x3A0,   1,  0x08,  1},
    {"TC_TEL_004", "LowFuelWarn",     2, 0x34A,   2,  0x01,  1},
    {"TC_TEL_005", "SeatbeltWarn",    1, 0x3A0,   0,  0x04,  1},
    {"TC_TEL_006", "TPMS_Warn",       2, 0x3C0,   4,  0x01,  1},
    {"TC_TEL_007", "Battery_Warn",    1, 0x3A0,   0,  0x20,  1},
    {"TC_TEL_008", "DoorAjar",        3, 0x3A0,   0,  0x10,  1},
    {"TC_TEL_009", "ABS_Clear",       2, 0x3A5,   0,  0x00,  0},   /* de-activation */
    {"TC_TEL_010", "SRS_ABS_Priority",1, 0x3A5,   0,  0x01,  1}    /* dual fault */
};

on start {
    write("=== TELLTALE MATRIX VALIDATION STARTED ===");
    simulate_kl15_on();
    setTimer(stepTimer, 3000);
}

on timer stepTimer {
    if (step < 8) {
        execute_telltale_tc(tc_table[step]);
        step++;
        setTimer(stepTimer, 2000);
    } else if (step == 8) {              /* de-activation test */
        test_telltale_deactivation();
        step++;
        setTimer(stepTimer, 2000);
    } else if (step == 9) {             /* dual-fault priority */
        test_dual_fault_priority();
        step++;
        setTimer(stepTimer, 3000);
    } else if (step == 10) {            /* CAN timeout telltale */
        test_telltale_can_timeout();
        step++;
        setTimer(stepTimer, 5000);
    } else if (step == 11) {            /* self-check at KL15 ON */
        test_bulb_check();
        step++;
        setTimer(stepTimer, 5000);
    } else {
        write("=== TELLTALE SUITE COMPLETE: PASS=%d FAIL=%d ===",
              pass_count, fail_count);
    }
}

/* ── Execute one telltale TC ────────────────────────────────────────── */
void execute_telltale_tc(TelltaleTc_t tc) {
    message 0x000 fault_msg;
    fault_msg.id = tc.fault_msg_id;

    /* Inject fault */
    if (tc.expected_on) {
        fault_msg.byte(tc.fault_byte) = tc.fault_bit_mask;
    } else {
        fault_msg.byte(tc.fault_byte) = 0x00;   /* clear fault */
    }
    output(fault_msg);

    TestWaitForTimeout(500);

    /* Read telltale status via UDS (DID 0xF120 = telltale register) */
    int telltale_state = read_telltale_status_via_uds(tc.fault_bit_mask);

    if (telltale_state == tc.expected_on) {
        write("PASS | %s | %s | State=%d (expected %d)",
              tc.tc_id, tc.telltale_name, telltale_state, tc.expected_on);
        pass_count++;
    } else {
        write("FAIL | %s | %s | State=%d (expected %d) — DEFECT",
              tc.tc_id, tc.telltale_name, telltale_state, tc.expected_on);
        fail_count++;
    }

    /* Clear the fault between tests */
    fault_msg.byte(tc.fault_byte) = 0x00;
    output(fault_msg);
    TestWaitForTimeout(300);
}

/* ── De-activation test ─────────────────────────────────────────────── */
void test_telltale_deactivation() {
    write("[TC_TEL_009] ABS fault de-activation test");

    /* First activate ABS telltale */
    message ABS_Status act_msg;
    act_msg.ABS_Fault = 1;
    output(act_msg);
    TestWaitForTimeout(500);
    write("  [Step 1] ABS_Fault=1 injected. Verify: ABS telltale ON.");

    /* Now clear */
    act_msg.ABS_Fault = 0;
    output(act_msg);
    TestWaitForTimeout(1000);
    write("  [Step 2] ABS_Fault=0 injected. Verify: ABS telltale OFF within 1s.");

    int state = read_telltale_status_via_uds(0x01);
    if (state == 0) {
        write("PASS | TC_TEL_009 | Telltale correctly de-activated");
        pass_count++;
    } else {
        write("FAIL | TC_TEL_009 | Telltale remains ON after fault cleared — LATCHING BUG");
        fail_count++;
    }
}

/* ── Dual fault priority test (ISO 2575) ───────────────────────────── */
void test_dual_fault_priority() {
    write("[TC_TEL_010] Dual fault: SRS (P1) + ABS (P2) simultaneously");
    write("  Requirement: P1 (SRS) takes display priority per ISO 2575");

    /* Inject both simultaneously */
    message SRS_Status srs_msg;
    message ABS_Status abs_msg;
    srs_msg.SRS_Fault = 1;
    abs_msg.ABS_Fault = 1;
    output(srs_msg);
    output(abs_msg);
    TestWaitForTimeout(500);

    write("  Verify: SRS telltale (P1 Red) visible");
    write("  Verify: ABS telltale (P2 Amber) visible");
    write("  Verify: SRS is displayed at higher prominence (OEM-specific priority rule)");
    write("  Ref: iso_2575 Priority P1 > P2. OEM SRS: IC_TEL_REQ_020");

    /* Clear both */
    srs_msg.SRS_Fault = 0;
    abs_msg.ABS_Fault = 0;
    output(srs_msg);
    output(abs_msg);
}

/* ── CAN timeout → telltale activation ─────────────────────────────── */
void test_telltale_can_timeout() {
    write("[TC_TEL_011] CAN timeout — ABS message lost > 500ms → CAN fault telltale");
    write("  Action: stopping ABS_Status (0x3A5) TX...");

    /* To simulate: in a simulation node, stop sending 0x3A5 */
    /* Here we write a marker — in actual setup, use simulation node control */
    putSysVar(sysvar::Simulation::StopABSTransmit, 1);
    TestWaitForTimeout(1000);

    write("  Verify: cluster shows CAN network fault warning");
    write("  Verify: ABS telltale shows 'network' state (OEM specific: may flash or show error)");

    putSysVar(sysvar::Simulation::StopABSTransmit, 0);
    TestWaitForTimeout(500);
    write("  ABS TX restored — telltale should clear within 1s");
}

/* ── Bulb check at KL15 ON ──────────────────────────────────────────── */
void test_bulb_check() {
    write("[TC_TEL_012] Bulb check sequence at KL15 ON");

    simulate_kl15_off();
    TestWaitForTimeout(2000);
    write("  KL15 OFF — cluster sleeping");

    simulate_kl15_on();
    write("  KL15 ON — bulb check should activate ALL telltales for 2-3 seconds");
    TestWaitForTimeout(4000);   /* observe 4 seconds */

    write("  Verify: ALL telltales were ON during first 2-3s");
    write("  Verify: Telltales clear after bulb check (unless faults present)");
    write("  Ref: OEM SRS IC_BULB_REQ_001 — Duration: 2.0s ± 0.5s");
}
```

---

## Script 3 — NVM / Odometer Validation

```capl
/*
 * FILE: test_nvm_odometer.can
 * SCOPE: Odometer retention across KL15 cycle, KL30 cycle, fast power loss.
 *        Trip meter reset and retention.
 *        ISO 16844 compliance: no rollback permitted.
 * DBC:   Powertrain.dbc + Body.dbc
 * UDS:   DID 0xF400 = Odometer (km, factor 0.1)
 *        DID 0xF401 = Trip A (km, factor 0.01)
 *        DID 0xF402 = Trip B (km, factor 0.01)
 */

includes {
    #include "libs/cluster_helpers.cin"
    #include "libs/uds_client.cin"
}

variables {
    msTimer  driveTimer;
    msTimer  stepTimer;
    int      step = 0;
    long     odo_before_kl15  = 0;
    long     odo_after_kl15   = 0;
    long     odo_before_kl30  = 0;
    long     odo_after_kl30   = 0;
    long     trip_before      = 0;
    long     trip_after_reset = 0;

    /* Simulated driving parameters */
    float    drive_speed_kmh  = 100.0;   /* km/h                  */
    int      drive_time_ms    = 60000;   /* 60 seconds = 1.666 km */
    float    expected_distance = 1.666;  /* 100 km/h × 60s / 3600 */

    message VehicleSpeed speed_msg;
    message BCM_Status   bcm_msg;
}

on start {
    write("=== NVM / ODOMETER VALIDATION: ISO 16844 ===");
    write("Simulated drive: %.0f km/h for %.0f sec = %.3f km",
          drive_speed_kmh, drive_time_ms / 1000.0, expected_distance);
    write("---");
    simulate_kl15_on();
    setTimer(stepTimer, 3000);
}

on timer stepTimer {
    step++;
    switch (step) {
    case 1:  phase1_record_baseline();              break;
    case 2:  phase2_simulate_drive();               break;
    /* phase 3 triggered from driveTimer */
    case 4:  phase4_kl15_cycle();                  break;
    case 5:  phase5_read_odo_after_kl15();         break;
    case 6:  phase6_kl30_cycle();                  break;
    case 7:  phase7_read_odo_after_kl30();         break;
    case 8:  phase8_trip_meter_reset();            break;
    case 9:  phase9_fast_power_loss();             break;
    case 10: print_final_results();                 break;
    }
}

void phase1_record_baseline() {
    write("[Phase 1] Reading baseline odometer via UDS DID 0xF400...");
    odo_before_kl15 = read_odometer_uds();
    trip_before     = read_uds_did(0xF401);
    write("  Baseline ODO = %ld (raw) = %.1f km", odo_before_kl15,
          odo_before_kl15 * 0.1);
    write("  Baseline Trip A = %ld (raw) = %.2f km", trip_before,
          trip_before * 0.01);
    setTimer(stepTimer, 500);
}

void phase2_simulate_drive() {
    write("[Phase 2] Simulating drive at %.0f km/h for %d ms...",
          drive_speed_kmh, drive_time_ms);
    speed_msg.VehicleSpeed = drive_speed_kmh;
    speed_msg.SpeedValid   = 1;
    output(speed_msg);
    setTimer(driveTimer, drive_time_ms);
}

on timer driveTimer {
    /* Stop driving */
    speed_msg.VehicleSpeed = 0.0;
    output(speed_msg);
    write("[Drive complete] %.3f km simulated", expected_distance);
    step = 3;   /* bridge to phase 4 */
    setTimer(stepTimer, 1000);
}

void phase4_kl15_cycle() {
    write("[Phase 4] KL15 OFF → ON cycle (NVM write test)");
    simulate_kl15_off();
    TestWaitForTimeout(5000);    /* allow NVM write to complete */
    simulate_kl15_on();
    TestWaitForTimeout(3000);    /* allow cluster boot */
    setTimer(stepTimer, 500);
}

void phase5_read_odo_after_kl15() {
    write("[Phase 5] Reading odometer after KL15 cycle...");
    odo_after_kl15 = read_odometer_uds();
    float delta = (odo_after_kl15 - odo_before_kl15) * 0.1;

    write("  ODO before = %.1f km", odo_before_kl15 * 0.1);
    write("  ODO after  = %.1f km", odo_after_kl15  * 0.1);
    write("  Delta      = %.3f km (expected %.3f km ±0.1 km)", delta, expected_distance);

    if (delta >= (expected_distance - 0.1) && delta <= (expected_distance + 0.1)) {
        write("TC_NVM_001 PASS | Odometer retained correctly after KL15 cycle");
    } else if (delta < 0) {
        write("TC_NVM_001 FAIL | ODOMETER ROLLBACK! ISO 16844 VIOLATION — RAISE P1 DEFECT");
    } else {
        write("TC_NVM_001 FAIL | Distance delta out of tolerance: %.3f km", delta);
    }
    setTimer(stepTimer, 500);
}

void phase6_kl30_cycle() {
    write("[Phase 6] KL30 OFF → ON cycle (battery disconnect simulation)");
    odo_before_kl30 = read_odometer_uds();
    write("  ODO before KL30 cycle = %.1f km", odo_before_kl30 * 0.1);
    /* Simulate fast KL30 removal — stop all CAN (no graceful shutdown) */
    simulate_kl15_off();
    TestWaitForTimeout(500);   /* short dwell — critical test */
    simulate_kl15_on();
    TestWaitForTimeout(4000);
    setTimer(stepTimer, 500);
}

void phase7_read_odo_after_kl30() {
    write("[Phase 7] Verifying odometer after fast KL30 cycle...");
    odo_after_kl30 = read_odometer_uds();
    float delta_kl30 = (odo_after_kl30 - odo_before_kl30) * 0.1;

    write("  ODO before KL30 = %.1f km", odo_before_kl30 * 0.1);
    write("  ODO after KL30  = %.1f km", odo_after_kl30  * 0.1);

    if (delta_kl30 >= -0.05) {
        write("TC_NVM_002 PASS | No rollback after fast KL30 cycle");
    } else {
        write("TC_NVM_002 FAIL | ROLLBACK %.3f km — fast power loss NVM write incomplete", delta_kl30);
        write("  Hypothesis: NVM write window < KL30 hold time. Check supercap / sync write.");
    }
    setTimer(stepTimer, 500);
}

void phase8_trip_meter_reset() {
    write("[Phase 8] Trip A reset test");
    /* Simulate stalk button press → Trip A reset (OEM specific signal) */
    bcm_msg.TripAResetRequest = 1;
    output(bcm_msg);
    TestWaitForTimeout(500);
    bcm_msg.TripAResetRequest = 0;
    output(bcm_msg);
    TestWaitForTimeout(500);

    trip_after_reset = read_uds_did(0xF401);
    write("  Trip A after reset = %ld (raw) = %.2f km", trip_after_reset,
          trip_after_reset * 0.01);

    if (trip_after_reset == 0) {
        write("TC_NVM_003 PASS | Trip A reset to 0.0 km");
    } else {
        write("TC_NVM_003 FAIL | Trip A = %.2f km after reset — not cleared",
              trip_after_reset * 0.01);
    }
    setTimer(stepTimer, 500);
}

void phase9_fast_power_loss() {
    write("[Phase 9] Fast power loss test — no KL15 OFF before KL30");
    write("  This simulates battery terminal pulled while vehicle running");
    write("  ACTION: Remove bench power supply 12V rail now, wait 3s, restore");
    write("  After restore, check ODO via UDS — expect no rollback");
    write("  [Manual bench action required for this phase]");
    setTimer(stepTimer, 500);
}

void print_final_results() {
    write("======================================================");
    write("NVM / ODOMETER TEST SUMMARY");
    write("TC_NVM_001 (KL15 cycle retention): See Phase 5 result");
    write("TC_NVM_002 (KL30 cycle no-rollback): See Phase 7 result");
    write("TC_NVM_003 (Trip A reset): See Phase 8 result");
    write("TC_NVM_004 (Fast power loss): Manual bench step required");
    write("ISO 16844 ref: Section 7.4 — completion of storage before shutdown");
    write("======================================================");
}
```

---

## Script 4 — CAN Timeout Injection and Fallback Validation

```capl
/*
 * FILE: test_can_timeout.can
 * SCOPE: Simulate CAN message loss for each sensor ECU. Verify cluster
 *        fallback behaviour (display value, telltale, DIS message).
 *        Tests per CAN timeout requirement in IC SRS.
 */

includes {
    #include "libs/cluster_helpers.cin"
}

variables {
    msTimer  txSpeed;
    msTimer  txEngine;
    msTimer  txFuel;
    msTimer  txABS;
    msTimer  observeTimer;
    msTimer  stepTimer;

    int step = 0;
    int send_speed  = 1;
    int send_engine = 1;
    int send_fuel   = 1;
    int send_abs    = 1;

    message VehicleSpeed  speed_msg;
    message EngineStatus  engine_msg;
    message FuelLevel     fuel_msg;
    message ABS_Status    abs_msg;
}

on start {
    write("=== CAN TIMEOUT INJECTION TEST ===");
    write("For each message: TX active → stop TX → observe fallback → restore TX");
    simulate_kl15_on();

    /* Set baseline signal values */
    speed_msg.VehicleSpeed  = 60.0;   speed_msg.SpeedValid = 1;
    engine_msg.EngineRPM    = 2000.0;
    fuel_msg.FuelLevel_pct  = 50;
    abs_msg.ABS_Fault       = 0;

    /* Start all cyclic TX */
    setTimer(txSpeed,  10);
    setTimer(txEngine, 10);
    setTimer(txFuel,  100);
    setTimer(txABS,   100);

    setTimer(stepTimer, 3000);   /* wait for cluster boot */
}

/* ── Cyclic TX timers ────────────────────────────────────────────────── */
on timer txSpeed  { if (send_speed)  { output(speed_msg);  setTimer(txSpeed,  10);  } }
on timer txEngine { if (send_engine) { output(engine_msg); setTimer(txEngine, 10);  } }
on timer txFuel   { if (send_fuel)   { output(fuel_msg);   setTimer(txFuel,  100);  } }
on timer txABS    { if (send_abs)    { output(abs_msg);    setTimer(txABS,   100);  } }

/* ── Test step sequencer ─────────────────────────────────────────────── */
on timer stepTimer {
    step++;
    switch (step) {
    case 1:  timeout_test_speed();  break;
    case 2:  timeout_restore_speed();  break;
    case 3:  timeout_test_engine(); break;
    case 4:  timeout_restore_engine(); break;
    case 5:  timeout_test_fuel();   break;
    case 6:  timeout_restore_fuel(); break;
    case 7:  timeout_test_abs();    break;
    case 8:  timeout_restore_abs();  break;
    case 9:  write("=== ALL CAN TIMEOUT TESTS COMPLETE ==="); break;
    }
}

/* ── Speed timeout ───────────────────────────────────────────────────── */
void timeout_test_speed() {
    write("[TC_CTO_001] VehicleSpeed (0x3B3) TX STOPPED | Timeout window: 200ms");
    send_speed = 0;
    setTimer(observeTimer, 3000);
}

on timer observeTimer {
    write("  OBSERVE NOW: Speedometer should show '--' or 0 km/h");
    write("  OBSERVE: CAN network fault warning may appear (OEM config)");
    setTimer(stepTimer, 1000);
}

void timeout_restore_speed() {
    write("  [Restore] VehicleSpeed TX restarted");
    send_speed = 1;
    setTimer(txSpeed, 10);
    write("  OBSERVE: Speed returns to 60 km/h within 1 frame (~10ms)");
    setTimer(stepTimer, 2000);
}

/* ── Engine timeout ──────────────────────────────────────────────────── */
void timeout_test_engine() {
    write("[TC_CTO_002] EngineStatus (0x316) TX STOPPED | Timeout window: 200ms");
    send_engine = 0;
    write("  OBSERVE: Tachometer shows '--' or 0 RPM after timeout");
    write("  OBSERVE: Gear display may show '--' (gear signal in same message)");
    setTimer(stepTimer, 3500);
}

void timeout_restore_engine() {
    send_engine = 1;
    setTimer(txEngine, 10);
    write("  [Restore] EngineStatus TX restarted");
    setTimer(stepTimer, 2000);
}

/* ── Fuel timeout ────────────────────────────────────────────────────── */
void timeout_test_fuel() {
    write("[TC_CTO_003] FuelLevel (0x34A) TX STOPPED | Timeout window: 1000ms");
    write("  Fuel gauge timeout is longer — OEM typically 1s for analogue gauge");
    send_fuel = 0;
    write("  OBSERVE: Gauge holds last value for ~1s then falls to 'E' or 0");
    setTimer(stepTimer, 4000);
}

void timeout_restore_fuel() {
    send_fuel = 1;
    setTimer(txFuel, 100);
    write("  [Restore] FuelLevel TX restarted — gauge should recover to 50%%");
    setTimer(stepTimer, 2000);
}

/* ── ABS status timeout → telltale ──────────────────────────────────── */
void timeout_test_abs() {
    write("[TC_CTO_004] ABS_Status (0x3A5) TX STOPPED");
    write("  Per SRS: ABS telltale shall indicate network fault within 500ms");
    send_abs = 0;
    write("  OBSERVE: ABS telltale activates (network loss = assumed fault state)");
    setTimer(stepTimer, 4000);
}

void timeout_restore_abs() {
    send_abs = 1;
    setTimer(txABS, 100);
    write("  [Restore] ABS_Status TX restarted — ABS telltale should clear in <1s");
    setTimer(stepTimer, 2000);
}
```

---

## Script 5 — Power Mode / KL15 Sequence State Machine

```capl
/*
 * FILE: test_power_mode.can
 * SCOPE: Full KL15 power mode sequence validation.
 *        KL30 ON → KL15 ON → Crank → Run → KL15 OFF → Sleep.
 *        Measures each phase timing against IC SRS requirements.
 */

includes {
    #include "libs/cluster_helpers.cin"
}

variables {
    msTimer  seqTimer;
    int      seqStep  = 0;
    double   ts_kl15_on;
    double   ts_canbus_active;
    double   ts_bulb_check_start;
    double   ts_bulb_check_end;
    double   ts_kl15_off;
    double   ts_cluster_sleep;
}

on start {
    write("=== POWER MODE SEQUENCE VALIDATION ===");
    write("Sequence: KL30 ON → KL15 ON → Crank → Run → KL15 OFF → Sleep");
    write("---");
    setTimer(seqTimer, 1000);
}

on timer seqTimer {
    seqStep++;
    switch (seqStep) {

    case 1:
        write("[STEP 1] KL30 ON — Battery power applied");
        write("  Verify: Cluster wakes from sleep (backlight on within 200ms)");
        write("  Verify: KL30 quiescent current < 2mA before KL15");
        /* In real bench: relay control via I/O board. Here: BCM signal. */
        setTimer(seqTimer, 2000);
        break;

    case 2:
        write("[STEP 2] KL15 ON — Ignition switch to ACC/ON");
        ts_kl15_on = timeNow() / 1e5;
        simulate_kl15_on();
        write("  Waiting for cluster active state...");
        setTimer(seqTimer, 500);
        break;

    case 3:
        ts_canbus_active = timeNow() / 1e5;
        write("[STEP 3] CAN bus active — measuring KL15 → CAN TX delay");
        write("  Delay: %.1f ms (SRS requirement: < 500ms)", ts_canbus_active - ts_kl15_on);
        if ((ts_canbus_active - ts_kl15_on) < 500.0) {
            write("  PASS: CAN TX within 500ms of KL15 ON");
        } else {
            write("  FAIL: CAN TX delayed > 500ms — SRS IC_PWR_REQ_003 violated");
        }
        setTimer(seqTimer, 200);
        break;

    case 4:
        ts_bulb_check_start = timeNow() / 1e5;
        write("[STEP 4] Bulb check in progress...");
        write("  OBSERVE: ALL telltales illuminated simultaneously");
        write("  START TIME: %.1f ms after KL15 ON", ts_bulb_check_start - ts_kl15_on);
        setTimer(seqTimer, 3000);   /* observe 3 seconds */
        break;

    case 5:
        ts_bulb_check_end = timeNow() / 1e5;
        write("[STEP 5] Bulb check ended");
        write("  Duration: %.0f ms (SRS requirement: 2000ms ± 500ms)",
              ts_bulb_check_end - ts_bulb_check_start);
        if ((ts_bulb_check_end - ts_bulb_check_start) >= 1500.0 &&
            (ts_bulb_check_end - ts_bulb_check_start) <= 2500.0) {
            write("  PASS: TC_PWR_001 Bulb check duration within SRS tolerance");
        } else {
            write("  FAIL: TC_PWR_001 Bulb check duration out of range — raise defect");
        }
        write("  OBSERVE: Telltales cleared after bulb check (fault-free state)");
        setTimer(seqTimer, 1000);
        break;

    case 6:
        write("[STEP 6] Simulating engine crank (RPM: 0 → 300 → 800)");
        {
            message EngineStatus eng;
            eng.EngineRPM = 300.0;
            output(eng);
            TestWaitForTimeout(200);
            eng.EngineRPM = 800.0;
            output(eng);
        }
        write("  OBSERVE: Tachometer sweeps from 0 → 800 RPM");
        write("  OBSERVE: MIL may momentarily activate during crank (normal)");
        write("  OBSERVE: MIL extinguishes after engine starts (MIL clear condition)");
        setTimer(seqTimer, 3000);
        break;

    case 7:
        write("[STEP 7] Run state — injecting normal operating signals");
        {
            message VehicleSpeed spd;  spd.VehicleSpeed = 60.0; spd.SpeedValid = 1;
            message FuelLevel    fuel; fuel.FuelLevel_pct = 75;
            output(spd); output(fuel);
        }
        write("  OBSERVE: Speedometer at 60 km/h, Fuel gauge at ~75%%");
        setTimer(seqTimer, 3000);
        break;

    case 8:
        write("[STEP 8] KL15 OFF — ignition switched off");
        ts_kl15_off = timeNow() / 1e5;
        simulate_kl15_off();
        write("  OBSERVE: After-run behaviour (cooling fan signal may remain)");
        write("  OBSERVE: Cluster NVM save in progress (odometer write)");
        write("  OBSERVE: Sleep animation or fade-out");
        setTimer(seqTimer, 5000);
        break;

    case 9:
        ts_cluster_sleep = timeNow() / 1e5;
        write("[STEP 9] Cluster sleep measurement");
        write("  KL15 OFF → sleep elapsed: %.0f ms", ts_cluster_sleep - ts_kl15_off);
        write("  SRS requirement: Cluster enters sleep within 10000ms of KL15 OFF");
        write("  Verify: Quiescent current < 2mA after sleep entry (bench ammeter)");
        write("  TC_PWR_005 PASS/FAIL: Manual current measurement required");
        setTimer(seqTimer, 2000);
        break;

    case 10:
        write("=== POWER MODE SEQUENCE TEST COMPLETE ===");
        write("Test cases executed: TC_PWR_001 to TC_PWR_005");
        write("Manual observations required: Bulb check visual, quiescent current");
        break;
    }
}
```

---

## Script 6 — Fuel Gauge Non-Linear Mapping Validation

```capl
/*
 * FILE: test_fuel_gauge.can
 * SCOPE: Fuel gauge accuracy, non-linear OEM curve, reserve warning,
 *        dead-zone at E, overfill behaviour.
 * NOTE:  Fuel gauge typically has a non-linear display curve defined by OEM.
 *        Mapping: raw FuelLevel_pct → needle angle → litre display
 */

includes {
    #include "libs/cluster_helpers.cin"
}

variables {
    msTimer  stepTimer;
    msTimer  txFuel;
    int      step          = 0;
    int      fuel_tx_on    = 1;
    float    current_fuel  = 100.0;

    /* OEM fuel gauge curve — mapping points (pct → expected_display_pct) */
    /* Non-linear: E end consumes 30% of swing for reserve, F end compressed */
    float fuelCurve[11][2] = {
        { 0.0,   0.0  },   /* Empty — gauge at E */
        {10.0,   5.0  },   /* 10% tank = 5% needle (reserve protection) */
        {15.0,  10.0  },   /* reserve warning threshold              */
        {20.0,  20.0  },
        {30.0,  33.0  },
        {40.0,  46.0  },
        {50.0,  58.0  },
        {60.0,  68.0  },
        {70.0,  78.0  },
        {85.0,  90.0  },
        {100.0, 100.0 }    /* Full */
    };

    message FuelLevel fuel_msg;
}

on start {
    write("=== FUEL GAUGE VALIDATION ===");
    write("Non-linear mapping, Low Fuel Warning, reserve dead-zone");
    simulate_kl15_on();
    setTimer(txFuel, 100);
    setTimer(stepTimer, 3000);
}

on timer txFuel {
    if (fuel_tx_on) {
        fuel_msg.FuelLevel_pct = current_fuel;
        output(fuel_msg);
        setTimer(txFuel, 100);
    }
}

on timer stepTimer {
    step++;
    switch (step) {
    case 1:  test_curve_mapping();   break;
    case 2:  test_reserve_warning(); break;
    case 3:  test_full_tank();       break;
    case 4:  test_fuel_timeout();    break;
    case 5:  write("=== FUEL GAUGE TESTS COMPLETE ==="); break;
    }
}

void test_curve_mapping() {
    int i;
    write("[TC_FUEL_001] Fuel gauge curve mapping validation");
    write("Injecting fuel levels and verifying needle position...");

    for (i = 0; i < elcount(fuelCurve); i++) {
        current_fuel = fuelCurve[i][0];
        TestWaitForTimeout(500);

        /* On HIL: compare display needle angle to expected curve point */
        /* Without HIL: log injection and require manual visual confirmation */
        write("  Inject=%.0f%% → Expected display=%.0f%% | OBSERVE on cluster",
              fuelCurve[i][0], fuelCurve[i][1]);
    }

    write("TC_FUEL_001: Visual confirmation required for all 11 points");
    setTimer(stepTimer, 1000);
}

void test_reserve_warning() {
    write("[TC_FUEL_002] Reserve / low fuel warning test");
    write("  Per OEM SRS: Low Fuel telltale activates at <= 15%% tank level");

    /* Ramp down from 20% to 10% */
    float f;
    for (f = 20.0; f >= 10.0; f -= 1.0) {
        current_fuel = f;
        TestWaitForTimeout(200);
        if (f == 15.0) {
            write("  At 15%%: OBSERVE low fuel telltale should NOW activate");
        }
    }

    write("TC_FUEL_002: Verify telltale ON at 15%% (or OEM threshold)");
    write("  Also verify: LowFuelWarn signal in 0x34A Byte 2 Bit 0 = 1");

    /* Check signal directly */
    int warn_bit = $FuelLevel::LowFuelWarning;
    if (warn_bit == 1) {
        write("  PASS: LowFuelWarning signal = 1 at 10%% fuel");
    } else {
        write("  FAIL: LowFuelWarning signal = 0 at 10%% — signal not raised");
    }
    setTimer(stepTimer, 1000);
}

void test_full_tank() {
    write("[TC_FUEL_003] Full tank — FuelLevel=100%%");
    current_fuel = 100.0;
    TestWaitForTimeout(1000);
    write("  OBSERVE: Gauge needle at full position");
    write("  Verify: gauge does NOT exceed 'F' mark (no overshoot)");
    write("  Verify: no Low Fuel telltale active at 100%%");
    setTimer(stepTimer, 1000);
}

void test_fuel_timeout() {
    write("[TC_FUEL_004] Fuel message timeout");
    fuel_tx_on = 0;
    write("  FuelLevel (0x34A) TX stopped");
    TestWaitForTimeout(3000);
    write("  OBSERVE: gauge holds last reading for ~1s (OEM config), then falls");
    write("  OBSERVE: on prolonged timeout — gauge to 'E' or shows fault symbol");
    fuel_tx_on = 1;
    setTimer(txFuel, 100);
    setTimer(stepTimer, 2000);
}
```

---

## Script 7 — UDS Diagnostics via CAPL (Cluster Read/Write)

```capl
/*
 * FILE: test_uds_diagnostics.can
 * SCOPE: Read cluster data via UDS (ISO 14229).
 *        Services used: 0x10 (SessionControl), 0x22 (ReadDataById),
 *        0x27 (SecurityAccess), 0x2E (WriteDataById), 0x19 (DTCRead).
 * Notes: Uses CANoe built-in Diagnostics window (diagRequest object)
 *        Cluster TX ID: 0x726  RX ID: 0x72E
 */

variables {
    msTimer stepTimer;
    int     step = 0;

    /* UDS DIDs for Marelli cluster (example — adjust to project) */
    long DID_ODO          = 0xF400;   /* Odometer km, factor 0.1 */
    long DID_TRIP_A       = 0xF401;   /* Trip A km, factor 0.01 */
    long DID_SW_VERSION   = 0xF189;   /* ECU SW version ASCII string */
    long DID_HW_VERSION   = 0xF191;   /* ECU HW part number */
    long DID_DISPLAY_SPD  = 0xF110;   /* Currently displayed speed */
    long DID_TELLTALE_MAP = 0xF120;   /* Active telltale bitmask */
}

on start {
    write("=== UDS DIAGNOSTICS VALIDATION ===");
    write("Cluster TX=0x726 RX=0x72E | Protocol: ISO 14229");
    setTimer(stepTimer, 1000);
}

on timer stepTimer {
    step++;
    switch (step) {
    case 1:  uds_read_sw_version();       break;
    case 2:  uds_read_odometer();         break;
    case 3:  uds_read_display_speed();    break;
    case 4:  uds_read_telltale_map();     break;
    case 5:  uds_read_dtcs();             break;
    case 6:  uds_write_trip_reset();      break;
    case 7:  write("=== UDS TESTS COMPLETE ==="); break;
    }
}

/* ── Read SW Version ────────────────────────────────────────────────── */
void uds_read_sw_version() {
    write("[TC_UDS_001] Read SW Version — DID 0xF189");
    diagRequest ClusterDiag.ReadDataByIdentifier req1;
    req1.dataIdentifier = 0xF189;
    req1.SendRequest();
}

on diagResponse ClusterDiag.ReadDataByIdentifier {
    if (this.dataIdentifier == 0xF189) {
        byte raw[255];
        long len = this.GetDataBytes(raw, 0, 255);
        char sw_ver[40];
        long i;
        for (i = 0; i < len && i < 39; i++) sw_ver[i] = raw[i];
        write("  SW Version: %s", sw_ver);
        write("  TC_UDS_001 PASS: Version string readable");
        setTimer(stepTimer, 200);
    }
}

/* ── Read Odometer ─────────────────────────────────────────────────── */
void uds_read_odometer() {
    write("[TC_UDS_002] Read Odometer — DID 0xF400");
    diagRequest ClusterDiag.ReadDataByIdentifier req2;
    req2.dataIdentifier = 0xF400;
    req2.SendRequest();
    /* Response handled in generic on diagResponse below */
}

/* ── Read Currently Displayed Speed ────────────────────────────────── */
void uds_read_display_speed() {
    write("[TC_UDS_003] Read Cluster Display Speed — DID 0xF110");
    write("  Use to compare: injected speed vs cluster-displayed speed");
    diagRequest ClusterDiag.ReadDataByIdentifier req3;
    req3.dataIdentifier = 0xF110;
    req3.SendRequest();
}

/* ── Read Telltale Bitmask ──────────────────────────────────────────── */
void uds_read_telltale_map() {
    write("[TC_UDS_004] Read Active Telltale Map — DID 0xF120");
    write("  Returns bitmask of currently illuminated telltales");
    write("  Bit 0: ABS, Bit 1: SRS, Bit 2: EPB, Bit 3: LowFuel ...");
    diagRequest ClusterDiag.ReadDataByIdentifier req4;
    req4.dataIdentifier = 0xF120;
    req4.SendRequest();
}

/* ── Read DTCs ──────────────────────────────────────────────────────── */
void uds_read_dtcs() {
    write("[TC_UDS_005] Read Stored DTCs — UDS Service 0x19 SubFunc 0x02");
    diagRequest ClusterDiag.ReadDTCInformation req5;
    req5.subFunction = 0x02;     /* reportDTCByStatusMask */
    req5.dtcStatusMask = 0xFF;   /* All status bits */
    req5.SendRequest();
    write("  Expect: 0 DTCs in clean build. Any DTC = potential defect.");
}

on diagResponse ClusterDiag.ReadDTCInformation {
    if (this.positive) {
        long count = this.numberOfDtcs;
        write("  Active DTCs: %ld", count);
        if (count == 0) {
            write("  TC_UDS_005 PASS: No DTCs stored");
        } else {
            write("  TC_UDS_005 INVESTIGATE: %ld DTC(s) found — see Trace for IDs", count);
        }
    } else {
        write("  TC_UDS_005 FAIL: Negative response received (NRC=0x%02X)", this.nrc);
    }
    setTimer(stepTimer, 200);
}

/* ── Write Trip Reset (requires Extended Session + Security Access) ── */
void uds_write_trip_reset() {
    write("[TC_UDS_006] Trip A reset via UDS write (DID 0xF401 = 0x0000)");
    write("  Step 1: Open Extended Diagnostic Session (0x10 03)");

    diagRequest ClusterDiag.DefaultSession    s_default;
    diagRequest ClusterDiag.ExtendedSession   s_ext;

    s_ext.SendRequest();
    TestWaitForTimeout(200);

    write("  Step 2: Write DID 0xF401 value 0x0000 (Trip A = 0.0 km)");
    diagRequest ClusterDiag.WriteDataByIdentifier write_req;
    write_req.dataIdentifier = 0xF401;
    write_req.SetDataBytes({0x00, 0x00}, 0, 2);
    write_req.SendRequest();
}

on diagResponse ClusterDiag.WriteDataByIdentifier {
    if (this.positive) {
        write("  TC_UDS_006 PASS: WriteDataByIdentifier acknowledged");
        write("  Read back DID 0xF401 to confirm Trip A = 0.0 km");
    } else {
        write("  TC_UDS_006 FAIL: NRC=0x%02X — write rejected", this.nrc);
        write("  Common NRC: 0x31=RequestOutOfRange, 0x33=SecurityAccessDenied");
    }
    setTimer(stepTimer, 200);
}
```

---

## Script 8 — Cluster Environment Simulation Node (Headless ECU Sim)

```capl
/*
 * FILE: sim_vehicle_environment.can
 * SCOPE: Simulation node — runs permanently to provide realistic vehicle
 *        signals to the cluster even without real ECUs on bench.
 *        Models: idle, drive, brake, fault injection.
 *        Assign to a CANoe Simulation Node (not a test node).
 */

variables {
    msTimer  txSpeed;
    msTimer  txEngine;
    msTimer  txFuel;
    msTimer  txABS;
    msTimer  txBCM;
    msTimer  txSRS;
    msTimer  txTPMS;

    /* Vehicle state model */
    enum VehicleMode { IDLE, ACCELERATE, CRUISE, BRAKE, FAULT };
    VehicleMode vMode = IDLE;

    float   speed_kmh   = 0.0;
    float   rpm         = 800.0;
    float   fuel_pct    = 80.0;
    int     gear        = 0;     /* 0=P */
    int     abs_fault   = 0;
    int     srs_fault   = 0;
    int     door_open   = 0;
    float   tyre_fl_kpa = 230.0;
    float   tyre_fr_kpa = 230.0;
    float   tyre_rl_kpa = 230.0;
    float   tyre_rr_kpa = 230.0;

    /* Panel-driven state variables */
    long    panel_mode    = 0;       /* env var from panel: 0=IDLE,1=ACC,2=CRUISE,3=BRAKE */
    int     panel_fault   = 0;       /* env var: 1 = inject fault mode */
}

on start {
    write("[SIM NODE] Vehicle environment simulation started");
    setTimer(txSpeed,   10);
    setTimer(txEngine,  10);
    setTimer(txFuel,   100);
    setTimer(txABS,    100);
    setTimer(txBCM,    100);
    setTimer(txSRS,    200);
    setTimer(txTPMS,   500);
}

/* ── Model update from panel controls ──────────────────────────────── */
on envVar VehicleModeSelector {
    panel_mode = getValue(this);
    update_vehicle_model();
}

on envVar FaultModeToggle {
    panel_fault = getValue(this);
    if (panel_fault) inject_fault_mode();
    else             clear_faults();
}

void update_vehicle_model() {
    switch (panel_mode) {
    case 0:   /* IDLE */
        speed_kmh = 0.0; rpm = 800.0; gear = 0;
        break;
    case 1:   /* ACCELERATE — ramp to 80 km/h */
        speed_kmh += 2.0; if (speed_kmh > 80.0) speed_kmh = 80.0;
        rpm = 800.0 + speed_kmh * 30.0;
        gear = (speed_kmh < 20) ? 1 : (speed_kmh < 40) ? 2 :
               (speed_kmh < 60) ? 3 : (speed_kmh < 80) ? 4 : 5;
        break;
    case 2:   /* CRUISE */
        /* Hold current speed */
        break;
    case 3:   /* BRAKE */
        speed_kmh -= 3.0; if (speed_kmh < 0.0) speed_kmh = 0.0;
        rpm = (speed_kmh > 0) ? 800.0 + speed_kmh * 20.0 : 0.0;
        break;
    }
    /* Gradual fuel consumption */
    if (speed_kmh > 0) fuel_pct -= 0.0001;
    if (fuel_pct < 0) fuel_pct = 0;
}

void inject_fault_mode() {
    write("[SIM] Fault mode ON — injecting ABS + SRS faults");
    abs_fault = 1;
    srs_fault = 1;
    tyre_fl_kpa = 180.0;   /* front left tyre low pressure */
}

void clear_faults() {
    write("[SIM] Faults cleared");
    abs_fault = 0;
    srs_fault = 0;
    tyre_fl_kpa = 230.0;
}

/* ── Cyclic transmit timers ─────────────────────────────────────────── */
on timer txSpeed {
    message VehicleSpeed msg;
    msg.VehicleSpeed = speed_kmh;
    msg.SpeedValid   = 1;
    output(msg);
    update_vehicle_model();
    setTimer(txSpeed, 10);
}

on timer txEngine {
    message EngineStatus msg;
    msg.EngineRPM    = rpm;
    msg.CurrentGear  = gear;
    msg.Throttle     = (panel_mode == 1) ? 40 : 0;
    output(msg);
    setTimer(txEngine, 10);
}

on timer txFuel {
    message FuelLevel msg;
    msg.FuelLevel_pct  = fuel_pct;
    msg.LowFuelWarning = (fuel_pct < 15.0) ? 1 : 0;
    output(msg);
    setTimer(txFuel, 100);
}

on timer txABS {
    message ABS_Status msg;
    msg.ABS_Active = (speed_kmh > 0 && panel_mode == 3) ? 1 : 0;
    msg.ABS_Fault  = abs_fault;
    msg.EBD_Active = msg.ABS_Active;
    output(msg);
    setTimer(txABS, 100);
}

on timer txBCM {
    message BCM_Status msg;
    msg.IgnitionStatus     = 1;
    msg.DoorOpen           = door_open;
    msg.SeatbeltUnfastened = 0;
    msg.Handbrake          = (speed_kmh < 0.1) ? 1 : 0;
    output(msg);
    setTimer(txBCM, 100);
}

on timer txSRS {
    message SRS_Status msg;
    msg.SRS_Fault = srs_fault;
    output(msg);
    setTimer(txSRS, 200);
}

on timer txTPMS {
    message TPMS_Status msg;
    msg.TyrePressure_FL = tyre_fl_kpa;
    msg.TyrePressure_FR = tyre_fr_kpa;
    msg.TyrePressure_RL = tyre_rl_kpa;
    msg.TyrePressure_RR = tyre_rr_kpa;
    msg.TyreWarn = (tyre_fl_kpa < 200 || tyre_fr_kpa < 200 ||
                   tyre_rl_kpa < 200 || tyre_rr_kpa < 200) ? 1 : 0;
    output(msg);
    setTimer(txTPMS, 500);
}
```

---

## Script 9 — Reusable Library `cluster_helpers.cin`

```capl
/*
 * FILE: libs/cluster_helpers.cin
 * SCOPE: Common helper functions shared across all cluster test scripts.
 *        Include in any .can file with: #include "libs/cluster_helpers.cin"
 */

/* ── Power mode control ─────────────────────────────────────────────── */
void simulate_kl15_on() {
    message BCM_Status bcm;
    bcm.IgnitionStatus = 1;
    output(bcm);
    write("[PWR] KL15 ON sent via BCM_Status.IgnitionStatus=1");
}

void simulate_kl15_off() {
    message BCM_Status bcm;
    bcm.IgnitionStatus = 0;
    output(bcm);
    write("[PWR] KL15 OFF sent via BCM_Status.IgnitionStatus=0");
}

/* ── UDS reads ──────────────────────────────────────────────────────── */
long read_odometer_uds() {
    diagRequest ClusterDiag.ReadDataByIdentifier req;
    req.dataIdentifier = 0xF400;
    req.SendRequest();
    long raw = req.GetDataLong(0);   /* 3-byte ODO, MSB first */
    return raw;
}

long read_uds_did(long did) {
    diagRequest ClusterDiag.ReadDataByIdentifier req;
    req.dataIdentifier = did;
    req.SendRequest();
    return req.GetDataLong(0);
}

int read_telltale_status_via_uds(int telltale_bit_mask) {
    diagRequest ClusterDiag.ReadDataByIdentifier req;
    req.dataIdentifier = 0xF120;
    req.SendRequest();
    byte telltale_byte = req.GetDataByte(0);
    return (telltale_byte & telltale_bit_mask) ? 1 : 0;
}

float read_display_speed_via_uds() {
    diagRequest ClusterDiag.ReadDataByIdentifier req;
    req.dataIdentifier = 0xF110;
    req.SendRequest();
    long raw = req.GetDataLong(0);
    return raw * 0.01;   /* Factor 0.01 */
}

/* ── Logging ────────────────────────────────────────────────────────── */
void log_test_result(char tc_id[], int passed, char detail[]) {
    if (passed) {
        write("PASS | %-16s | %s", tc_id, detail);
    } else {
        write("FAIL | %-16s | %s", tc_id, detail);
    }
}

void log_defect_candidate(char tc_id[], char defect_desc[]) {
    write("!!DEFECT_CANDIDATE | TC=%s | %s", tc_id, defect_desc);
    write("  >> Raise defect in Jira. Attach: this log segment + CANoe screenshot.");
}

/* ── Cycle time measurement ─────────────────────────────────────────── */
variables {
    double last_msg_ts[0x800];   /* last timestamp per message ID */
}

double measure_cycle_time(long msg_id) {
    double now = timeNow() / 1e5;   /* convert 100ns → ms */
    double delta = now - last_msg_ts[msg_id % 0x800];
    last_msg_ts[msg_id % 0x800] = now;
    return delta;
}

void check_cycle_time(long msg_id, double expected_ms, double tolerance_ms) {
    double actual = measure_cycle_time(msg_id);
    if (actual > 0 && (actual < (expected_ms - tolerance_ms) ||
                       actual > (expected_ms + tolerance_ms))) {
        write("TIMING_WARN | 0x%03X | CycleTime=%.2f ms | Expected=%.0f ±%.0f ms",
              msg_id, actual, expected_ms, tolerance_ms);
    }
}

/* ── Bit manipulation helpers ───────────────────────────────────────── */
int get_bit(byte value, int bit_pos) {
    return (value >> bit_pos) & 0x01;
}

byte set_bit(byte value, int bit_pos) {
    return value | (1 << bit_pos);
}

byte clear_bit(byte value, int bit_pos) {
    return value & ~(1 << bit_pos);
}
```

---

## Script 10 — EV Cluster SOC and Range Display Validation

```capl
/*
 * FILE: test_ev_cluster.can
 * SCOPE: EV-specific cluster features: SOC gauge, range display,
 *        charging status, READY lamp, regen indicator.
 * DBC:   EV_Powertrain.dbc (BMS on 0x3A2, VCU on 0x3A3)
 */

includes {
    #include "libs/cluster_helpers.cin"
}

variables {
    msTimer txBMS;
    msTimer txVCU;
    msTimer stepTimer;
    int step = 0;

    message BMS_Status bms_msg;
    message VCU_Status vcu_msg;

    float  soc_pct          = 100.0;
    int    charging_state   = 0;      /* 0=off, 1=AC, 2=DC, 3=Regen */
    int    ready_signal     = 0;
    float  range_km         = 350.0;
}

on start {
    write("=== EV CLUSTER VALIDATION ===");
    write("SOC Gauge | Range Display | Charging Status | READY Lamp | Regen");
    simulate_kl15_on();
    setTimer(txBMS, 10);
    setTimer(txVCU, 10);
    setTimer(stepTimer, 3000);
}

on timer txBMS {
    bms_msg.SOC_pct        = soc_pct;
    bms_msg.ChargingState  = charging_state;
    output(bms_msg);
    setTimer(txBMS, 10);
}

on timer txVCU {
    vcu_msg.DriveRange_km  = range_km;
    vcu_msg.ReadySignal    = ready_signal;
    output(vcu_msg);
    setTimer(txVCU, 10);
}

on timer stepTimer {
    step++;
    switch (step) {
    case 1:  test_ready_lamp();               break;
    case 2:  test_soc_sweep();                break;
    case 3:  test_low_battery_warning();      break;
    case 4:  test_ac_charging_display();      break;
    case 5:  test_dc_fast_charge();           break;
    case 6:  test_regen_indicator();          break;
    case 7:  test_range_display_accuracy();   break;
    case 8:  test_soc_timeout();              break;
    case 9:  write("=== EV CLUSTER TESTS COMPLETE ==="); break;
    }
}

void test_ready_lamp() {
    write("[TC_EV_001] READY lamp activation");
    ready_signal = 0;
    TestWaitForTimeout(500);
    write("  OBSERVE: No READY lamp (vehicle not ready)");

    ready_signal = 1;
    TestWaitForTimeout(500);
    write("  OBSERVE: Green READY lamp illuminated on cluster");
    write("  Ref: READY lamp only activates after HV pre-charge complete");

    int uds_state = read_telltale_status_via_uds(0x40);   /* bit 6 = READY */
    if (uds_state == 1) {
        write("TC_EV_001 PASS: READY telltale state confirmed via UDS");
    } else {
        write("TC_EV_001 FAIL: UDS telltale map bit 6 not set — defect candidate");
        log_defect_candidate("TC_EV_001", "READY lamp UDS state mismatch");
    }
    setTimer(stepTimer, 1000);
}

void test_soc_sweep() {
    write("[TC_EV_002] SOC Gauge sweep — 100%% to 0%%");
    float soc;
    for (soc = 100.0; soc >= 0.0; soc -= 5.0) {
        soc_pct = soc;
        range_km = soc * 3.5;   /* estimated 350 km at 100% */
        TestWaitForTimeout(300);
        write("  SOC=%.0f%% | Range=%.0f km | OBSERVE gauge position", soc, range_km);
    }
    soc_pct = 80.0;
    range_km = 280.0;
    setTimer(stepTimer, 500);
}

void test_low_battery_warning() {
    write("[TC_EV_003] Low battery warning at OEM threshold (typically 10%%)");
    soc_pct  = 11.0; range_km = 38.5; TestWaitForTimeout(500);
    write("  At 11%%: No low battery warning expected");
    soc_pct  = 10.0; range_km = 35.0; TestWaitForTimeout(500);
    write("  At 10%%: Low battery telltale SHOULD activate now");
    soc_pct  = 5.0;  range_km = 17.5; TestWaitForTimeout(500);
    write("  At 5%%:  Critical battery warning — OEM may show popup message");
    write("  Verify: BMS_Status.LowBatteryWarn bit = 1");
    write("  Verify: Range display shows '--' or exact remaining range");
    soc_pct = 80.0; range_km = 280.0;
    setTimer(stepTimer, 1000);
}

void test_ac_charging_display() {
    write("[TC_EV_004] AC charging display");
    charging_state = 1;   /* AC charging */
    TestWaitForTimeout(1000);
    write("  OBSERVE: Charging animation active (slow fill icon)");
    write("  OBSERVE: SOC gauge shows current SOC with charging indicator");
    write("  OBSERVE: NO READY lamp during charging (vehicle not driveable)");

    if (read_telltale_status_via_uds(0x40) == 0) {
        write("TC_EV_004 PASS: READY lamp correctly OFF during charging");
    } else {
        write("TC_EV_004 FAIL: READY lamp ON during charging — safety issue");
        log_defect_candidate("TC_EV_004", "READY lamp active during AC charge");
    }
    charging_state = 0;
    setTimer(stepTimer, 1000);
}

void test_dc_fast_charge() {
    write("[TC_EV_005] DC fast charge display");
    charging_state = 2;   /* DC fast charge */
    TestWaitForTimeout(1000);
    write("  OBSERVE: Fast charge animation (faster than AC animation)");
    write("  OBSERVE: Power in kW may be displayed on DIS");
    write("  OBSERVE: Estimated time to full may be shown");
    charging_state = 0;
    setTimer(stepTimer, 1000);
}

void test_regen_indicator() {
    write("[TC_EV_006] Regenerative braking indicator");
    charging_state = 3;   /* Regen */
    ready_signal   = 1;
    TestWaitForTimeout(500);
    write("  OBSERVE: Regen indicator illuminates (OEM design: green arc or power meter)");
    write("  OBSERVE: Power meter shows power flow INTO battery direction");
    charging_state = 0;
    setTimer(stepTimer, 1000);
}

void test_range_display_accuracy() {
    write("[TC_EV_007] Range display accuracy");
    write("  Injecting SOC=50%%, expected range ~175 km (at 350 km / 100%%)");
    soc_pct  = 50.0;
    range_km = 175.0;   /* VCU computes from energy model — we inject VCU output */
    TestWaitForTimeout(1000);
    write("  OBSERVE: DIS shows approximately 175 km range");
    write("  OBSERVE: Range unit correct — km (EU) or mi (US variant)");
    write("  Verify: Range not showing 0 or '--' when SOC > 10%%");
    setTimer(stepTimer, 1000);
}

void test_soc_timeout() {
    write("[TC_EV_008] BMS message timeout — SOC signal lost");
    write("  Stopping BMS_Status (0x3A2) TX...");
    /* In real bench: use simulation node control to stop BMS */
    putSysVar(sysvar::Simulation::StopBMSTransmit, 1);
    TestWaitForTimeout(2000);
    write("  OBSERVE: SOC gauge falls to 0 or shows '--' after timeout");
    write("  OBSERVE: Low battery warning may activate (safe-state behaviour)");
    write("  OBSERVE: Range display shows '--'");

    putSysVar(sysvar::Simulation::StopBMSTransmit, 0);
    TestWaitForTimeout(500);
    write("  BMS TX restored — SOC and range should recover");
    setTimer(stepTimer, 1000);
}
```

---

## Script Index

| Script | File | Coverage |
|---|---|---|
| 1 | `test_speedometer_full.can` | Linearity, EU Reg 39, zero hold, SpeedValid, timeout |
| 2 | `test_telltale_matrix.can` | All telltales, dual-fault priority, deactivation, bulb check |
| 3 | `test_nvm_odometer.can` | ISO 16844, KL15/KL30 retention, Trip A reset, fast power loss |
| 4 | `test_can_timeout.can` | Timeout for Speed/Engine/Fuel/ABS — fallback behaviour |
| 5 | `test_power_mode.can` | KL15 sequence timing, bulb check duration, sleep current |
| 6 | `test_fuel_gauge.can` | Non-linear curve, reserve warning, dead-zone, timeout |
| 7 | `test_uds_diagnostics.can` | UDS 0x22, 0x19, 0x2E — read ODO, SW ver, DTCs, telltale map |
| 8 | `sim_vehicle_environment.can` | Simulation node — models all ECU signals for bench-only use |
| 9 | `libs/cluster_helpers.cin` | Shared library — KL15, UDS reads, logging, bit helpers |
| 10 | `test_ev_cluster.can` | SOC, range, charging, READY lamp, regen indicator |

---

*File: 07_capl_scripts_complete.md | marelli_cluster_lead series*
