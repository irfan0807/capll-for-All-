# STAR Interview Scenarios — BYD Sealion 7 Cluster Lead Experience
### Marelli / LTTS Interview Context — EV Cluster | UDS Diagnostics | CAN FD

> **Role Context:** Cluster Lead on BYD Sealion 7 (e-Platform 3.0) validation programme
> **Format:** Situation → Task → Action → Result
> **Coverage:** EV cluster signals, UDS diagnostics, CAN FD, SOC/range display, READY lamp,
>               charging animation, telltale validation, team lead, OEM communication

---

## STAR 1 — SOC Gauge Accuracy Defect Found Before SOP (Critical Discovery)

### Situation
During final-phase cluster validation on the BYD Sealion 7 EV platform, I was running a parametrised SOC gauge accuracy sweep — injecting BMS_Status.SOC_pct from 100% to 0% in 5% steps via CAN FD and verifying the cluster needle position. At 20% SOC injection, the cluster needle was showing 15% — a 5% under-read. This mattered because the cluster SRS specified a maximum ±2% display tolerance for the SOC gauge (tighter than fuel gauge specs because SOC directly drives customer range anxiety decisions).

The BYD OEM had a hard SOP (Start of Production) lock date — 6 weeks away. The instrument cluster SW was already in its final candidate build.

### Task
Confirm the defect was not a bench setup error, characterise the fault across the full SOC range, root-cause it, write a P1 defect with sufficient evidence for the SW team to fix it, and get it verified closed before SOP.

### Action

**Step 1 — Rule out bench error (Day 1, 2 hours):**
```capl
/* SOC injection and readback — verify signal round-trip */
on timer txBMS {
    message BMS_Status msg;
    msg.SOC_pct = inject_soc;    /* controlled variable */
    output(msg);
    setTimer(txBMS, 10);
}
/* Read back via UDS DID 0xF430 — cluster's internally read SOC */
void verify_soc_readback(float inject) {
    diagRequest ClusterDiag.ReadDataByIdentifier req;
    req.dataIdentifier = 0xF430;   /* cluster internal SOC register */
    req.SendRequest();
    float cluster_soc = req.GetDataByte(0) * 0.5;   /* Factor 0.5 per DID spec */
    float delta = inject - cluster_soc;
    write("Inject=%.1f%% | Cluster_DID=%.1f%% | Delta=%.1f%%", inject, cluster_soc, delta);
}
```
Result: Cluster internal DID 0xF430 returned the correct SOC value matching inject → cluster was receiving the right data. The problem was in the *display layer*, not signal reception.

**Step 2 — Full sweep characterisation (Day 1 afternoon):**
Ran sweep at 5% increments. Results:

| Injected SOC | Cluster Display | Delta | SRS Limit |
|---|---|---|---|
| 100% | 100% | 0% | ±2% ✅ |
| 80% | 79% | -1% | ±2% ✅ |
| 60% | 58% | -2% | ±2% ✅ |
| 40% | 38% | -2% | ±2% ✅ |
| 20% | 15% | **-5%** | ±2% ❌ |
| 10% | 6% | **-4%** | ±2% ❌ |
| 5% | 2% | **-3%** | ±2% ❌ |

Clear pattern: error concentrates at the low end (≤20% SOC). Hypothesis: non-linear display curve has wrong breakpoint at the low SOC end.

**Step 3 — Root cause hypothesis:**
The SOC gauge uses a non-linear needle mapping table (10 entries in cluster SW) to compensate for non-linear needle mechanics. The entry at the 20% breakpoint had an incorrect needle angle value — the interpolation between 25% and 15% caused the 5% under-read.

Extracted the display mapping table via UDS DID 0xF431 (calibration array DID):
```
Breakpoint[4] = {SOC: 20.0%, NeedleAngle: 42.5°}
Expected by SRS: {SOC: 20.0%, NeedleAngle: 47.0°} ← 4.5° off
```

**Step 4 — Defect report (BYD-CLU-2201):**
- Severity: S1 (SOC under-read at 20% = customer believes car has less range than actual = trust issue + BYD SRS IC_GAUGE_REQ_034 violation)
- Root cause: Display map table Breakpoint[4] needle angle calibration error (42.5° vs required 47.0°)
- Evidence: Full sweep table, UDS DID 0xF431 extract, comparison against SRS calibration sheet Rev D
- Fix recommendation: Update Breakpoint[4] to 47.0° in cluster SW calibration data

**Step 5 — Fix verification:**
```capl
/* Regression verify after SW patch IC_SW_v2.3.1 */
float verify_soc_sweep[] = {100.0, 60.0, 20.0, 10.0, 5.0};
int i;
for (i = 0; i < elcount(verify_soc_sweep); i++) {
    inject_soc = verify_soc_sweep[i];
    TestWaitForTimeout(500);
    float display_soc = read_soc_from_uds();
    float delta = abs(verify_soc_sweep[i] - display_soc);
    if (delta <= 2.0)
        write("PASS | SOC=%.0f%% | Display=%.1f%% | Delta=%.1f%% ≤ 2%%",
              verify_soc_sweep[i], display_soc, delta);
    else
        write("FAIL | SOC=%.0f%% | Delta=%.1f%% > 2%%", verify_soc_sweep[i], delta);
}
```

### Result
- BYD-CLU-2201 fixed in IC_SW_v2.3.1 (calibration breakpoint corrected): all 5 verify points passed ≤1% delta
- Found 6 weeks before SOP — zero cost to fix at this stage. If caught post-SOP: recall risk on SOC display affecting customer trust in range accuracy
- SW team confirmed the root cause: calibration data had been transposed from an older ICE gauge map (fuel gauge breakpoints used for SOC gauge by mistake during porting)
- I added a SOC gauge calibration cross-check step to the build acceptance criteria — checked at every SW release
- OEM cluster lead commended the UDS-assisted root cause method as "the most technically thorough defect report received on this project"

---

## STAR 2 — UDS DTC Read Revealed 3 Latent Defects Invisible to Manual Test

### Situation
Manual cluster validation on the BYD Sealion 7 had been running for 6 weeks. The bench tests all appeared clean — all telltales showing correctly, no visible faults. Before closing the validation phase, I ran a full UDS DTC read (Service 0x19, SubFunction 0x02 — reportDTCByStatusMask, mask 0xFF) as part of my closure checklist. The read returned 3 unexpected DTCs not matching any currently active bench fault:

```
DTC 0xC11200 — CAN BUS OFF event (stored, not confirmed, not active)
DTC 0xB10045 — SOC signal range violation (confirmed, not active)
DTC 0xB10047 — VCU_Status signal checksum error (stored, not confirmed)
```

None of these were visible in any telltale or DIS warning during manual testing.

### Task
Investigate all 3 DTCs, determine whether they were genuine defects, bench artefacts, or legacy data — and decide whether they needed to be raised as defects before gateway sign-off.

### Action

**DTC 0xC11200 — CAN BUS OFF:**
- Queried the DTC snapshot data via UDS service 0x19 SubFunc 0x06 (reportDTCSnapshotRecordByDTCNumber):
```capl
diagRequest ClusterDiag.ReadDTCSnapshotByDTCNumber req;
req.dtcGroup = 0xC11200;
req.snapshotRecordNumber = 0xFF;   /* all records */
req.SendRequest();
/* Returns: OdometerAtFault, VehicleSpeedAtFault, TimeAtFault */
```
- Snapshot showed: VehicleSpeed = 0, Odometer = 0.0 km → occurred at very first bench power-on
- Root cause: bench CAN FD bus termination resistor was missing during initial setup — caused BUS OFF on first boot. Bench engineering error → not a vehicle defect. Cleared DTC, re-ran cycle, DTC did not return.
- **Verdict: Bench artefact. Clear and document.**

**DTC 0xB10045 — SOC signal range violation:**
- This was suspicious — "confirmed, not active" means it triggered at some point during testing
- Reviewed CANoe logging for SOC_pct signal over last 3 bench sessions:
```python
# Python: find all BMS_Status frames where SOC_pct > 100 or < 0
import can
log = can.BLFReader("bench_session_14.blf")
for msg in log:
    if msg.arbitration_id == 0x3A2:
        soc = (msg.data[0] << 8 | msg.data[1]) * 0.5
        if soc > 100.0 or soc < 0.0:
            print(f"t={msg.timestamp:.3f}s  SOC={soc:.1f}%")
```
Output: `t=4821.330s  SOC=102.5%` — one frame with 0x3A2 data = 0x00CD = 205 raw × 0.5 = 102.5%

During a CAPL script test, an engineer had set `msg.SOC_pct = 105.0` (testing over-range reaction) — this exceeded the cluster SRS range (0–100%) and triggered the DTC. Genuine artefact from test design — but revealed the cluster was monitoring out-of-range correctly.

- **Verdict: Expected DTC from deliberate out-of-range test. Log the trigger, clear DTC, add test cleanup step to the out-of-range TC.**

**DTC 0xB10047 — VCU_Status checksum error:**
- Snapshot: VehicleSpeed = 60 km/h, Odometer = 127.4 km → occurred during real test execution
- Reviewed CANoe trace at that timestamp: bench PC had a brief CPU spike (logging software stalled) — VCU_Status message 0x3A3 was sent with stale counter (rolling counter did not increment for 3 frames)
- Cluster detected the static rolling counter → logged a checksum/counter violation DTC
- This was actually **correct cluster behaviour** — the cluster correctly detected a bad message sequence
- However, revealed that the bench simulation node was not correctly incrementing the rolling counter — a bench tool gap
```capl
/* Fixed in simulation node: */
on timer txVCU {
    vcu_msg.RollingCounter = (vcu_msg.RollingCounter + 1) & 0x0F;   /* 4-bit counter */
    output(vcu_msg);
    setTimer(txVCU, 10);
}
```
- **Verdict: Correct cluster behaviour, bench simulation bug. Fix simulation node, add rolling counter verification to bench acceptance criteria.**

### Result
- 3 DTCs investigated — 0 actual cluster defects, but 3 bench process improvements identified:
  1. CAN FD termination verification checklist added to bench setup SOP
  2. Out-of-range test cases must clear DTCs in teardown (added to all relevant TCs)
  3. Simulation node rolling counter verified at start of every session
- DTC closure report submitted to OEM — all 3 formally documented as "artefact with corrective action"
- OEM system architect called this "a rigorous closure approach — most teams ignore stored DTCs as noise"
- Process adopted: DTC read added as mandatory step in every cluster sprint closure checklist
- One genuine near-miss: if DTC 0xB10047 had reached production, any CAN glitch would have triggered a stored DTC visible in dealer diagnostics — potential warranty claim

---

## STAR 3 — READY Lamp Timing Defect (Safety-Relevant Cluster Signal)

### Situation
On the BYD Sealion 7, the cluster READY lamp (green lamp, ISO 2575 — EV specific) must illuminate only after high-voltage pre-charge is complete and the vehicle is safe to drive. The VCU sends `VCU_Status.ReadySignal = 1` on CAN FD when this condition is met.

During power mode testing, I observed that the READY lamp was illuminating approximately 1.2 seconds before the VCU was actually transmitting `ReadySignal = 1`. This meant the cluster was showing the vehicle as ready to drive before the VCU had confirmed the HV pre-charge sequence was complete.

This was a potential safety issue — a driver could engage Drive before HV system was ready.

### Task
Confirm the defect with precise timing evidence, determine whether the root cause was in the cluster (jumped the gun) or the VCU (sent the signal early), assess the safety implications, and escalate to the correct level.

### Action

**Step 1 — Precise timing measurement with CANoe:**
```capl
/* Measure: VCU ReadySignal=1 timestamp vs READY telltale activation */
variables {
    double ts_ready_signal;
    double ts_telltale_on;
}

on signal VCU_Status::ReadySignal {
    if (this == 1) {
        ts_ready_signal = timeNow() / 1e5;    /* ms */
        write("VCU ReadySignal=1 at T=%.2f ms", ts_ready_signal);
    }
}

on message 0x64A {    /* Cluster telltale status broadcast */
    if (this.byte(0) & 0x40) {   /* bit 6 = READY lamp */
        if (ts_telltale_on == 0) {
            ts_telltale_on = timeNow() / 1e5;
            write("READY lamp ON at T=%.2f ms", ts_telltale_on);
            write("DELTA: READY lamp appeared %.2f ms before/after VCU signal",
                  ts_telltale_on - ts_ready_signal);
        }
    }
}
```

Results over 10 cycles:
| Cycle | READY lamp ON (ms) | VCU ReadySignal=1 (ms) | Delta |
|---|---|---|---|
| 1 | 3842 | 5021 | **-1179 ms** (lamp early) |
| 2 | 4011 | 5198 | **-1187 ms** |
| 3 | 3899 | 5087 | **-1188 ms** |
| Average | — | — | **-1185 ms** |

READY lamp was consistently activating 1185ms *before* the VCU sent ReadySignal=1.

**Step 2 — Rule out signal decode error:**
- Verified VCU_Status DBC — ReadySignal: Byte 0, Bit 6, Factor 1, no offset. Correct.
- Verified cluster telltale broadcast frame 0x64A — confirmed READY lamp bit position with OEM ICD Rev E.

**Step 3 — Trace the full HV pre-charge sequence:**
```
T=0ms      — KL15 ON (BCM_Status.IgnitionStatus = 1)
T=200ms    — VCU wakes up, starts HV pre-charge
T=3840ms   — Cluster activates READY lamp ← **too early**
T=5020ms   — HV pre-charge complete, VCU sends ReadySignal=1
T=5020ms   — Cluster should activate READY lamp (correct moment)
```
Found: Cluster was using a fixed **3800ms timer** from KL15 ON to activate READY lamp — a hardcoded startup assumption. This was functional on bench because pre-charge normally completed around 5 seconds. But if pre-charge was slow (cold battery, -10°C scenario), the lamp would appear even earlier — gap could be 3+ seconds.

**Step 4 — Safety impact assessment:**
- ASIL level: VCU ReadySignal path = ASIL B (per BYD HARA)
- Cluster READY lamp driven by timer = ASIL-unrated implementation (wrong)
- ISO 26262 Part 6: Safety-related function (READY display) cannot use a time-based assumption — must use the actual safety state signal
- Filed as BYD-CLU-2198: **S1, Safety-Relevant, ISO 26262 non-compliance**

**Step 5 — Escalation:**
- Escalated to LTTS Safety Lead and BYD Cluster System Architect same day
- Did not wait for root cause confirmation — notification is mandatory for suspected ISO 26262 violations

### Result
- SW team confirmed the root cause: READY lamp had been implemented with a timer-based workaround during early development (VCU was not available on bench then), and the workaround was never reverted
- Fix: Cluster SW updated to drive READY lamp only from `VCU_Status.ReadySignal = 1` — no timer logic
- Fix verified: Delta across 10 cycles post-fix = 0ms to +50ms (lamp activates within 1 CAN frame of VCU signal)
- BYD HARA updated to formally document READY lamp as a safety-relevant display function requiring ASIL B compliance
- My escalation prevented a potential ISO 26262 gap from reaching production — BYD system lead acknowledged this in writing as "critical finding"
- Defect BYD-CLU-2198 referenced in the final Functional Safety Assessment report

---

## STAR 4 — Managing BYD OEM Directly During Build Instability (Delivery Under Pressure)

### Situation
In the final 4 weeks of the BYD Sealion 7 cluster validation programme, the cluster SW team released 4 builds in 12 days — an unusually high frequency caused by cascading fixes from the VCU integration team (VCU signals kept changing). Each new build invalidated portions of existing test results, requiring partial regression. My team of 5 engineers was stretched thin. Two builds introduced new regressions that the SW team had not anticipated.

The BYD OEM validation manager attended our weekly status call and asked directly: "Your defect count is increasing with each build. Are you in control of this project?"

### Task
Restore OEM confidence with a data-driven, honest response and stabilise the validation process so that defect trends moved in the right direction before the gateway.

### Action
1. **Answered the OEM question directly — no deflection:**
   - "Defect count has increased because we are finding genuine regressions in each new build — which means our regression coverage is working. The issue is build stability from the VCU integration side, not test quality. Here is the trend data:"

   | Build | New Defects | Regressions | Fixed & Verified |
   |---|---|---|---|
   | IC_v2.1.0 | 8 | 0 | 0 |
   | IC_v2.1.1 | 5 | 3 | 6 |
   | IC_v2.1.2 | 7 | 5 | 9 |
   | IC_v2.2.0 | 4 | 2 | 14 |

   "Build v2.2.0 shows the first reduction in new defects. Verified count is accelerating — we are on the right side of the curve."

2. **Introduced a build acceptance gate:**
   - Proposed to OEM: "No build should reach cluster validation before passing a 20-TC smoke test from the VCU integration team."
   - OEM accepted — introduced a 2-hour integration smoke test before each cluster build handoff
   - This prevented 2 subsequent unstable builds from reaching our regression bench

3. **Parallel regression execution:**
   - Automated 45 critical-path TCs ran overnight (nightly execution already in place from Sprint 05)
   - New builds loaded at 22:00 → regression results by 06:00 → engineers reviewed at 09:00 and started strategic testing by 09:30
   - Freed daytime hours for new defect investigation

4. **Weekly trend report (simple, visual):**
   Created a 1-page dashboard shared with OEM every Monday:
   - Open P1/P2 trend line (must decline)
   - Verified closed trend line (must increase)
   - Build stability indicator (regression rate per build)

5. **Over-communicated to OEM on P1 items:**
   - Every P1 defect had a same-day email to OEM: root cause hypothesis, expected fix ETA, retest commitment

### Result
- IC_v2.3.0 (gateway candidate): 0 new P1 defects, 2 P2 pending, regression rate = 0
- Gateway delivered on schedule — OEM validation manager opened the gateway call with: "The trend data from the last 3 weeks gave us confidence — you clearly stabilised the programme."
- Build acceptance gate proposal was adopted by BYD as a standard process for all ECU–ECU integration checkpoints
- My "right side of the curve" framing was referenced by the PM in the project closure report as an example of confident stakeholder communication

---

## STAR 5 — Cluster UDS Security Access for Variant Coding (Extended Session Workflow)

### Situation
The BYD Sealion 7 cluster supports 4 software variants from one HW platform:
- Standard (km/h, kWh/100km, Chinese market)
- Long Range (km/h, extended range algorithm)
- Performance (km/h, sport-style gauge animation)
- Export EU (km/h, WLTP display format)

Variant selection is written to the cluster via UDS `WriteDataByIdentifier` (0x2E) on DID 0xF100 — but this requires an Extended Diagnostic Session (0x10 03) and Level 2 Security Access (0x27 03/04).

During variant validation, the SW team had not provided the Security Access algorithm (seed-key calculation) to our team — they sent it 2 days before the variant validation sprint. I had to implement the seed-key algorithm in CAPL and validate all 4 variants within 1 sprint.

### Task
Implement the UDS Security Access seed-key algorithm in CAPL, validate the full UDS session workflow, write variant code to the cluster for all 4 variants, and verify each variant's cluster behaviour.

### Action

**Step 1 — Security Access implementation in CAPL:**
```capl
/*
 * UDS Security Access Level 2 — BYD Cluster
 * Algorithm: Key = ~(Seed XOR 0xA5B6) & 0xFFFF
 *            (provided by BYD SW team in SecAccess_BYD_Rev_C.pdf)
 */
variables {
    word received_seed = 0;
    word calculated_key = 0;
}

void uds_security_access_level2() {
    /* Step 1: Open Extended Session */
    diagRequest ClusterDiag.ExtendedSession ext_req;
    ext_req.SendRequest();
    TestWaitForTimeout(200);
    write("[UDS] Extended session opened (0x10 03)");

    /* Step 2: Request Seed */
    diagRequest ClusterDiag.SecurityAccessRequestSeed seed_req;
    seed_req.subFunction = 0x03;   /* Level 2 request seed */
    seed_req.SendRequest();
}

on diagResponse ClusterDiag.SecurityAccessRequestSeed {
    if (this.positive) {
        received_seed = (this.GetDataByte(0) << 8) | this.GetDataByte(1);
        write("[UDS] Seed received: 0x%04X", received_seed);

        /* Step 3: Calculate Key */
        calculated_key = (~(received_seed ^ 0xA5B6)) & 0xFFFF;
        write("[UDS] Calculated Key: 0x%04X", calculated_key);

        /* Step 4: Send Key */
        diagRequest ClusterDiag.SecurityAccessSendKey key_req;
        key_req.subFunction = 0x04;
        key_req.SetDataBytes({(calculated_key >> 8) & 0xFF,
                              calculated_key & 0xFF}, 0, 2);
        key_req.SendRequest();
    } else {
        write("[UDS] Seed request failed — NRC 0x%02X", this.nrc);
    }
}

on diagResponse ClusterDiag.SecurityAccessSendKey {
    if (this.positive) {
        write("[UDS] Security Access Level 2 GRANTED");
        write_variant_code();   /* proceed with DID write */
    } else {
        write("[UDS] Key rejected — NRC 0x%02X", this.nrc);
        if (this.nrc == 0x35) write("  >> Invalid key — check algorithm");
        if (this.nrc == 0x36) write("  >> Exceeded attempt counter — wait 10s");
    }
}
```

**Step 2 — Variant write and read-back:**
```capl
typedef struct {
    byte variant_code;
    char variant_name[30];
    char expected_unit[10];
    float expected_range_factor;
} ClusterVariant_t;

ClusterVariant_t variants[4] = {
    {0x01, "Standard_CN",   "kWh/100km", 1.0 },
    {0x02, "LongRange_CN",  "kWh/100km", 1.15},
    {0x03, "Performance_CN","kWh/100km", 1.0 },
    {0x04, "Export_EU",     "kWh/100km", 1.0 }
};

void write_variant_code() {
    diagRequest ClusterDiag.WriteDataByIdentifier write_req;
    write_req.dataIdentifier = 0xF100;
    write_req.SetDataByte(0, current_variant.variant_code);
    write_req.SendRequest();
}

on diagResponse ClusterDiag.WriteDataByIdentifier {
    if (this.positive) {
        write("[UDS] Variant written: %s (0x%02X)",
              current_variant.variant_name, current_variant.variant_code);
        /* Perform KL15 cycle to activate variant */
        simulate_kl15_off();
        TestWaitForTimeout(3000);
        simulate_kl15_on();
        TestWaitForTimeout(4000);
        /* Read back to confirm */
        verify_variant_active();
    } else {
        write("[UDS] Variant write FAILED — NRC 0x%02X", this.nrc);
    }
}
```

**Step 3 — Variant verification:**
For each variant, verified:
1. Economy unit displayed correctly (kWh/100km vs L/100km on ICE — EV variants always kWh)
2. Range algorithm active (inject identical SOC and driving style signal — Long Range variant should show 15% more range)
3. Gauge animation style (Performance variant has faster needle sweep at KL15 ON)
4. DID read-back matches written code

### Result
- All 4 variants written, KL15-cycled, and verified within Sprint (3 days)
- Security Access algorithm verified — no NRC 0x35 (key mismatch) in any attempt
- Variant code persistence confirmed across KL15 cycle (DID 0xF100 read-back = written value)
- Found one defect: Performance variant gauge sweep animation triggered even after KL15 ON with SOC < 15% — was suppressing animation in standard mode correctly, not in Performance mode (BYD-CLU-2211, P2)
- CAPL Security Access implementation donated to project library — reused by other engineers for DTC clearing and calibration tasks
- UDS variant workflow documented as a step-by-step test procedure for the BYD project test SOP

---

## STAR 6 — Cluster Charging Animation Defect Found via CAN FD Log Analysis

### Situation
The BYD Sealion 7 cluster shows three distinct charging animations:
- AC slow charge (< 11kW) — slow fill animation, estimated time to full on DIS
- DC fast charge (> 50kW) — fast fill animation, power kW displayed on DIS
- Regen (vehicle decelerating) — arc animation in power meter area

During customer preview testing (internal BYD review with marketing team, not OEM), one of the reviewers reported: "The fast charge animation and slow charge animation look the same." My team hadn't noticed because our verification had only checked whether the animation was ON or OFF — not the animation speed between types.

I was asked to investigate immediately — the review was the next day.

### Task
Reproduce the issue, identify whether it was a genuine defect or display similarity by design, provide evidence either way to the BYD cluster system lead within 4 hours.

### Action

**Step 1 — Reproduce in 30 minutes:**
- Injected AC charge: `BMS_Status.ChargingState = 1` (AC), `BMS_Status.ChargingPower_kW = 7.4`
- Injected DC charge: `BMS_Status.ChargingState = 2` (DC), `BMS_Status.ChargingPower_kW = 80.0`
- Observed: visually the animations were different — but barely. The DC animation fill speed was approx 15% faster, not the 3× faster specified in the cluster SRS Appendix D.

**Step 2 — Quantify with frame capture:**
Used CANoe measurement to capture cluster's own animation status broadcast (0x64B — cluster DIS output frame):
```capl
on message 0x64B {    /* Cluster DIS animation state */
    byte anim_type  = this.byte(0);   /* 0=off, 1=AC, 2=DC, 3=Regen */
    byte anim_frame = this.byte(1);   /* animation frame counter 0–255 */
    write("AnimType=%d FrameCounter=%d", anim_type, anim_frame);
}
```

Measured frame counter increment rate:
- AC charge: frame counter increments every **480ms** → full cycle ~120 seconds ✅ matches SRS Annex D: "AC animation completes in 120s"
- DC charge: frame counter increments every **420ms** → full cycle ~107 seconds ❌ SRS Annex D: "DC animation shall complete in 40s maximum"

DC animation was running at 107s cycle time instead of 40s — an SW bug in the animation speed calculation for DC mode.

**Step 3 — Root cause hypothesis:**
Checked BMS_Status DBC: `ChargingPower_kW` signal — Factor 0.5, Offset 0. At 80kW inject, DBC encode = 160.

Checked cluster internal charging power DID via UDS (DID 0xF440):
```capl
diagRequest ClusterDiag.ReadDataByIdentifier req;
req.dataIdentifier = 0xF440;
req.SendRequest();
/* Result: 40 → 40 × 0.5 = 20 kW — cluster reading 20 kW instead of 80 kW! */
```

**Found it:** Cluster was decoding ChargingPower_kW with the wrong factor — using Factor 0.25 instead of 0.5. At 80kW true power, cluster read 40 raw × 0.25 = 10 kW — still in "slow charge territory" → played AC-speed animation.

Provided to BYD system lead within 2.5 hours: root cause (wrong DBC factor in cluster FW), defect report BYD-CLU-2217, fix recommendation.

### Result
- Fix deployed in IC_SW_v2.3.2 (ChargingPower factor corrected in cluster FW DBC decode table)
- DC animation verified: frame counter increments every 156ms → full cycle 39.8s ≤ 40s ✅
- Customer preview the next day went without the animation issue — no comment from reviewers
- My UDS-assisted diagnosis (checking cluster's internal read vs injected value) was highlighted as a "best practice" in the BYD project quality report
- DBC factor verification added to the project's new build acceptance test list

---

## STAR 7 — Leading the Cluster Team During BYD OEM Audit (Governance Under Scrutiny)

### Situation
BYD's internal audit team conducted an unannounced validation quality audit on our cluster project. The audit team (3 BYD engineers) arrived at our bench lab and asked to review:
1. Test traceability — can every SRS requirement be traced to a test case?
2. Defect management — how are P1 defects tracked from raise to closure?
3. Tool version control — are the CANoe config, DBC, and SW versions locked and traceable?
4. Team competency — can the engineers explain what they are testing and why?

My manager was in a different city. I was the only lead on site. I had 30 minutes' notice (a message from the PM: "BYD audit team is on the way").

### Task
Host the audit professionally, provide credible answers to all 4 audit areas with evidence, and pass the audit without a major finding — while keeping the team calm and focused.

### Action

**30-minute preparation:**
- Quick team briefing: "BYD audit in 30 minutes. Stay calm. If you don't know an answer — say 'let me check and confirm' — never guess."
- Pulled up the traceability matrix (Google Sheet), the defect register (Jira), and the tool version log on the main screen
- Confirmed every engineer knew which TCs they owned and could explain them

**Audit Area 1 — Traceability:**
- Opened the traceability matrix: 320 TCs, each linked to SRS requirement number and Rev
- Outstanding gap: 8 requirements had TCs in DRAFT status (not yet executed)
- I stated proactively: "We have 8 TCs in draft — these are for features in build IC_v2.3.0 not yet released. They are planned for Sprint 12. Here is the sprint plan."
- Auditor: "If those features were released today, would you catch a defect?" → I ran a live CANoe demonstration of the CAPL telltale test on the bench in 5 minutes.

**Audit Area 2 — Defect management:**
- Opened Jira, filtered P1 defects (open + closed): 7 total, all closed or in retest
- Walked through BYD-CLU-2198 (READY lamp timing) from raise → root cause → fix → verify: complete lifecycle visible in Jira
- Auditor asked about the gap time for BYD-CLU-2201 (SOC defect): "Root cause was confirmed 6 hours after raise — because we had UDS DID evidence in the defect report. SW team didn't need to reproduce."

**Audit Area 3 — Tool version control:**
- CANoe version: 17 SP3 (logged in bench setup SOC)
- DBC version: Powertrain_v3.1.dbc + EV_BMS_v1.5.dbc — Git hash shown
- IC SW under test: IC_v2.2.0 — build manifest file on shared drive shown with SHA256 hash
- Every bench session start log records tool + DBC + SW versions (auto-generated by a startup CAPL script)

**Audit Area 4 — Team competency:**
- Auditor spoke directly to Priya: "What are you testing right now?" → She walked through her TC (DIS Eco Score display), explained the BMS signal source, and described pass/fail criteria — clearly and correctly
- Auditor spoke to Anjali (the fresher, now mid-level): "How do you raise a defect?" → She demonstrated live in Jira including filling in the reproduction steps field

### Result
- **Audit passed — zero major findings**
- 2 minor observations: (1) bench setup SOP needed a photograph of termination resistor placement; (2) defect template missing "OEM SRS reference" field → both corrected within 48 hours
- BYD audit lead wrote: "Team demonstrated strong process discipline and technical depth. Traceability and defect quality above expectations for a supplier team."
- My manager received an email from BYD citing the audit outcome as a positive example
- I created a 1-page "audit readiness checklist" after this — 15 items, covering traceability, tool locks, defect quality — shared with all LTTS IC projects

---

## STAR 8 — Range Display Accuracy Cross-Validation with BMS and VCU (System Integration)

### Situation
The BYD Sealion 7 DIS (Driver Information System) shows the estimated range in km. This value is computed by the VCU (Vehicle Control Unit) from the BMS's reported SOC, the vehicle's current driving pattern, and a learned efficiency model. The cluster simply displays what the VCU sends in `VCU_Status.DriveRange_km`.

During integration testing, a customer preview driver reported: "The range jumps suddenly by 15 km when I accelerate." My team hadn't tested dynamic range behaviour — only static injection at fixed SOC.

### Task
Investigate the range jump, reproduce it with controlled inputs, determine whether the root cause was in the VCU (range calculation algorithm), the cluster (display filter), or the BMS (SOC signal stability), and deliver a technical position within 48 hours.

### Action

**Step 1 — Dynamic signal injection test:**
```capl
/* Simulate: steady cruise → sudden acceleration → range jump */
variables {
    float soc_pct         = 50.0;
    float range_km        = 175.0;
    float driving_regen   = 0.0;    /* kWh regen input — 0 = no regen */
    msTimer txBMS;
    msTimer txVCU;
    msTimer testSeq;
    int seq = 0;
}

on timer testSeq {
    seq++;
    switch (seq) {
    case 1:    /* Steady state cruise */
        range_km = 175.0;
        write("[T+0s] Steady cruise | Range = %.0f km", range_km);
        setTimer(testSeq, 5000);
        break;
    case 2:    /* Sudden acceleration — VCU adjusts range estimate down */
        range_km = 158.0;   /* VCU recalculated based on high power demand */
        write("[T+5s] Acceleration | Range drops to %.0f km (delta=-17)", range_km);
        setTimer(testSeq, 3000);
        break;
    case 3:    /* Return to cruise */
        range_km = 167.0;
        write("[T+8s] Back to cruise | Range recovers to %.0f km", range_km);
        break;
    }
}
```

Reproduced: range dropped 17km in one CAN frame update — instant jump on cluster display.

**Step 2 — Isolate root cause:**

3 possible sources:
- **VCU:** sends large step change in DriveRange_km → cluster just displays it
- **Cluster:** should have a display smoothing filter to prevent visual jump
- **BMS:** SOC jitter causing VCU to produce an unstable range estimate

Checked via UDS:
```capl
/* Compare VCU's raw range value vs cluster's displayed range */
/* DID 0xF450 = cluster's raw received DriveRange (unfiltered) */
/* DID 0xF451 = cluster's displayed range (after filter, if any) */
float raw   = read_uds_did(0xF450) * 0.1;
float disp  = read_uds_did(0xF451) * 0.1;
write("VCU raw range = %.1f km | Cluster display = %.1f km", raw, disp);
```
Result: `raw = 158.0 km | display = 158.0 km` — cluster was displaying raw VCU value with no filtering.

Cluster SRS Appendix F: *"Drive Range display shall apply a 5-second damping filter to prevent visible step changes > 5 km."* — cluster SW had no filter implemented. **Cluster defect.**

**Step 3 — Characterise the VCU contribution:**
Separately logged `VCU_Status.DriveRange_km` over a 60-second drive cycle. VCU did produce legitimate step changes (range recalculation on acceleration). These were algorithmically correct — VCU was not at fault. The cluster filter was the missing piece.

Raised BYD-CLU-2219: *"Range display has no 5-second damping filter. Cluster SRS Appendix F requirement not implemented. Visible 15–20 km step changes on acceleration."*

### Result
- SW team confirmed: the display filter was in the design spec but the developer assumed the VCU would smooth the signal (responsibility gap between VCU and cluster SW teams)
- Fix: 5-second rolling average filter implemented in cluster display layer for DriveRange_km signal
- Verified: maximum visible step change post-fix = 3.2 km/5s — within the 5 km limit
- BYD-CLU-2219 closed before gateway — no range jump visible in final preview drive
- Cross-ECU responsibility gap (who applies the filter — VCU or cluster?) was formally resolved in the ICD with a new clause: "Display smoothing is the cluster's responsibility unless VCU SRS explicitly states otherwise"
- Found by my team before production — equivalent fix cost post-SOP: estimated tooling change + OTA push to all units

---

## STAR 9 — CAN FD Error Frame Injection Revealed Cluster Network Resilience Gap

### Situation
During system integration testing on the BYD Sealion 7 HIL bench, the integration team ran a CAN FD bus stress test — deliberately injecting error frames to simulate a degraded network (e.g., damaged wiring harness). After 10 seconds of intermittent error frame injection on the powertrain CAN FD bus, the cluster ECU went into a locked state: all gauges blank, no telltales, no response to KL15 OFF command. Recovery required a KL30 power cycle — unacceptable for a production vehicle.

### Task
Root-cause the cluster's locked state under CAN FD error conditions, characterise the exact error threshold that triggered the hang, and propose a software fix before the gateway.

### Action

**Step 1 — Reproduce with controlled error injection:**
```capl
/*
 * CAN FD error frame injection — trigger via CANoe Fault Injection node
 * Inject 5 error frames per second on bus segment POWERTRAIN_CANFD
 */
variables {
    int   error_rate_per_sec = 5;
    msTimer errorTimer;
}

on start {
    write("[ERROR INJECT] Starting controlled CAN FD error injection");
    setTimer(errorTimer, 1000 / error_rate_per_sec);
}

on timer errorTimer {
    CANoeAPI_CanFdErrorInject(1,       /* channel 1 = POWERTRAIN_CANFD */
                              0x3A2,   /* BMS_Status ID */
                              CAPL_CANFD_ERROR_STUFFING);
    setTimer(errorTimer, 1000 / error_rate_per_sec);
}

on errorFrame {
    double ts = timeNow() / 1e5;
    write("ErrorFrame at T=%.2f ms | Channel=%d | ECC=0x%02X",
          ts, this.channel, this.errorCode);
}
```

Results:
- 1 error/sec for 60s → no cluster hang (cluster recovers each frame)
- 5 errors/sec for 12s → cluster hangs (all displays blank, no CAN TX from cluster)
- 3 errors/sec for 30s → cluster hangs after 27s

**Step 2 — Identify the trigger — TEC/REC monitoring:**
```capl
/* Monitor cluster's CAN FD Transmit Error Counter via UDS */
void monitor_can_error_counters() {
    diagRequest ClusterDiag.ReadDataByIdentifier req;
    req.dataIdentifier = 0xF460;   /* DID = CAN FD TEC/REC registers */
    req.SendRequest();
    /* Returns: Byte 0 = TEC, Byte 1 = REC */
}

on diagResponse ClusterDiag.ReadDataByIdentifier {
    if (this.dataIdentifier == 0xF460) {
        byte tec = this.GetDataByte(0);
        byte rec = this.GetDataByte(1);
        write("TEC=%d REC=%d", tec, rec);
        if (tec >= 128) write("  >> CLUSTER IN ERROR PASSIVE STATE");
        if (tec == 255) write("  >> CLUSTER BUS-OFF — CLUSTER WILL NOT RECOVER AUTO");
    }
}
```

At hang point: TEC = 255 → cluster CAN FD controller entered Bus-Off state. By default, the cluster SW had **auto Bus-Off recovery disabled** — once Bus-Off, the CAN FD controller needed a software reset which the cluster application layer did not implement.

**Step 3 — Fix recommendation:**
Raised BYD-CLU-2225: Cluster CAN FD controller must implement ISO 11898-1 compliant Bus-Off recovery (128 × 11 recessive bits after Bus-Off before re-integration). Fix: enable the auto Bus-Off recovery in the CAN FD driver interrupt handler + add a health watchdog that detects Bus-Off and triggers recovery within 500ms.

**Step 4 — Verified fix:**
```capl
/* Verify auto Bus-Off recovery after fix IC_SW_v2.4.0 */
void verify_busoff_recovery() {
    write("[TEST] Injecting error flood → Bus-Off condition for 3 seconds...");
    start_error_injection(20);   /* 20 errors/sec = guaranteed Bus-Off */
    TestWaitForTimeout(3000);
    stop_error_injection();
    TestWaitForTimeout(1000);    /* wait for recovery */
    /* Read cluster gauges — should recover without KL30 cycle */
    float displayed_soc = read_soc_from_uds();
    if (displayed_soc > 0) {
        write("PASS: Cluster recovered from Bus-Off — SOC=%0.f%%", displayed_soc);
    } else {
        write("FAIL: Cluster still hung after Bus-Off — KL30 cycle needed");
    }
}
```

### Result
- Fix verified: cluster now auto-recovers from Bus-Off within 650ms — no KL30 cycle required
- BYD-CLU-2225 closed before gateway
- Recovery time (650ms) formally added to cluster SRS as a requirements: "IC shall recover from CAN Bus-Off within 1000ms without operator intervention" — requirement didn't exist before this test
- Error injection test added to the nightly regression suite
- Integration team highlighted this as the highest-value find from the HIL stress test week

---

## STAR 10 — Telltale Localisation Defect for EU Export Variant (Wrong Symbol, Wrong Standard)

### Situation
BYD Sealion 7 Export EU variant requires telltale symbols to conform to UN ECE Regulation 121 and ISO 2575 (EU). The Standard_CN variant uses MIIT (Ministry of Industry and Information Technology) compliant symbols — visually identical for most, but different for 4 telltales: the High Beam symbol, Seatbelt symbol, TPMS warning, and the EV-specific "charging complete" indicator.

During export variant validation, I was running a visual telltale symbol check against the EU variant SRS. I found that the High Beam symbol on the EU cluster was displaying the Chinese MIIT variant (horizontal rays) instead of the EU ISO 2575 symbol (tilted diagonal rays). This was a localisation defect — the wrong graphic asset was mapped to the EU variant in the cluster SW.

### Task
Identify all telltale symbol mismatches between the CN and EU variants, raise correctly, and drive closure before export homologation submission — which was 3 weeks away.

### Action

**Step 1 — Systematic telltale symbol audit:**
Built a comparison table using the EU SRS Annex G (telltale symbol definitions) vs CN SRS Annex H:

| Telltale | ISO 2575 EU Symbol | MIIT CN Symbol | Match? |
|---|---|---|---|
| High Beam | Tilted beams (⊕ style) | Horizontal beams | ❌ |
| Seatbelt | Diagonal belt across torso | Upright belt figure | ❌ |
| TPMS | Tyre cross-section with ! | Flat tyre outline | ❌ |
| Charge Complete | Lightning bolt in circle | Chinese character variant | ❌ |
| ABS | ABS text, circle | ABS text, circle | ✅ |
| SRS | Airbag + person | Airbag + person | ✅ |

4 of 18 telltales had wrong symbols on EU export variant.

**Step 2 — Verify via variant code + UDS:**
```capl
/* Confirm EU export variant is active */
diagRequest ClusterDiag.ReadDataByIdentifier req;
req.dataIdentifier = 0xF100;   /* Variant code DID */
req.SendRequest();
byte variant = req.GetDataByte(0);
write("Active variant: 0x%02X", variant);
/* Expected: 0x04 = Export_EU */
/* Result:   0x04 ✅ — correct variant active, symbols still wrong */
```

Confirmed: variant code was correct (0x04 = EU). SW team was serving the EU variant correctly but the graphic asset mapping table in flash was pointing to the CN asset bank for those 4 symbols.

**Step 3 — Root cause:**
The EU variant graphic asset table (stored in cluster flash memory, DID 0xF500 asset manifest) had 4 entries still pointing to CN asset addresses. The asset table had not been fully updated when the EU variant was ported from the CN baseline.

```
Asset[HIGH_BEAM_EU] → address 0x0A1230 (CN asset bank) ← wrong
Asset[HIGH_BEAM_EU] → address 0x1F0440 (EU asset bank) ← correct
```

Raised BYD-CLU-2231 (P1 — regulatory compliance, export homologation risk) with exact asset addresses.

**Step 4 — Verification CAPL after fix:**
```capl
/* Automated telltale symbol check using CANoe simulation + camera output */
/* On HIL bench with camera capture — reads pixel cluster from telltale area */
/* Without camera: UDS asset manifest DID check as proxy */
void verify_eu_asset_mapping() {
    int i;
    long eu_telltale_dids[4] = {0xF501, 0xF502, 0xF503, 0xF504};
    long eu_expected_addr[4] = {0x1F0440, 0x1F0520, 0x1F0610, 0x1F0700};

    for (i = 0; i < 4; i++) {
        diagRequest ClusterDiag.ReadDataByIdentifier req;
        req.dataIdentifier = eu_telltale_dids[i];
        req.SendRequest();
        long addr = req.GetDataLong(0);
        if (addr == eu_expected_addr[i]) {
            write("PASS: Telltale[%d] asset address 0x%06X correct", i, addr);
        } else {
            write("FAIL: Telltale[%d] = 0x%06X (expected 0x%06X)", i, addr, eu_expected_addr[i]);
        }
    }
}
```

### Result
- All 4 asset addresses corrected in IC_SW_v2.4.1 — UDS asset DID verification passed ✅
- Visual confirmation on bench: all 4 EU telltale symbols match ISO 2575 specification
- Homologation submission not delayed — defect found 3 weeks before submission deadline
- Added telltale symbol checklist to the variant validation entry criteria: "Visual symbol audit mandatory for each new export variant build before execution"
- BYD homologation engineer acknowledged: "This find was critical — a wrong symbol in a type-approval submission would require a re-submission, delaying market entry by 6–8 weeks"

---

## STAR 11 — Odometer NVM Retention Test Under Cold Temperature (-10°C Soak)

### Situation
Standard odometer NVM retention testing on the BYD Sealion 7 bench was done at room temperature (25°C). During a design review, the BYD thermal engineer flagged that NVM write time for the cluster's EEPROM increases significantly at low temperatures — and asked whether we had validated NVM retention under cold soak conditions. We had not. Regulation (ISO 16844) requires odometer retention under all operating conditions including extreme temperature.

I proposed and led a cold soak NVM test — our first temperature-controlled cluster validation on this project.

### Task
Design a cold soak odometer retention test procedure, execute it using the environmental chamber on the HIL bench, and confirm whether the cluster met the ISO 16844 NVM retention requirement at -10°C.

### Action

**Step 1 — Test design:**
- Identified the EEPROM write specification: NVM write completion guaranteed ≤ 3ms at 25°C, ≤ 12ms at -10°C (from cluster HW spec)
- KL15 OFF to KL30 OFF minimum hold time (room temp bench): 2.5s (from STAR 3 NVM study)
- At -10°C: NVM write up to 12ms → still well within the 2.5s hold window
- BUT: BYD thermal data showed the cluster microcontroller clock speed derated by 15% at -10°C — risk that KL15 OFF detection software was slower than expected

**Step 2 — Procedure:**
```
1. Soak cluster (real ECU) in thermal chamber at -10°C for 2 hours (thermal stabilisation)
2. Mount ECU in HIL bench via extension harness through chamber wall
3. KL15 ON → inject 100 km/h for 60s (= 1.666 km) via CAN FD from bench
4. UDS read: ODO before = X km
5. KL15 OFF (chamber at -10°C, ECU cold)
6. Wait 3s (standard hold) → KL30 OFF
7. Wait 10s → KL30 ON → KL15 ON
8. UDS read: ODO after = Y km
9. Expected: Y - X = 1.666 km ± 0.1
10. Repeat 5 times
```

**Step 3 — CAPL test script adapted for cold test:**
```capl
/* Cold soak odometer test — identical to room temp NVM test but with
   extended settle times to accommodate slower MCU clock at -10°C */
variables {
    float odo_before[5];
    float odo_after[5];
    int   cycle = 0;
    msTimer seqTimer;
}

on timer seqTimer {
    cycle++;
    switch (cycle % 4) {
    case 1:    /* Record ODO before drive */
        odo_before[(cycle-1)/4] = read_odometer_uds() * 0.1;
        write("[Cycle %d Cold] ODO_before = %.1f km", (cycle-1)/4 + 1,
              odo_before[(cycle-1)/4]);
        inject_speed(100.0);          /* 100 km/h */
        setTimer(seqTimer, 60000);    /* drive 60 seconds */
        break;
    case 2:    /* Stop drive, KL15 OFF */
        inject_speed(0.0);
        TestWaitForTimeout(500);
        simulate_kl15_off();
        setTimer(seqTimer, 4000);     /* 4s hold — extra 1.5s for cold MCU */
        break;
    case 3:    /* KL30 cycle */
        simulate_kl30_off();
        setTimer(seqTimer, 10000);
        break;
    case 0:    /* Power restored — read ODO */
        simulate_kl30_on();
        simulate_kl15_on();
        TestWaitForTimeout(5000);     /* cluster boot at cold = slower */
        int idx = cycle/4 - 1;
        odo_after[idx] = read_odometer_uds() * 0.1;
        float delta = odo_after[idx] - odo_before[idx];
        write("[Cycle %d Cold] ODO_after=%.1f | Delta=%.3f | Expected 1.666",
              idx + 1, odo_after[idx], delta);
        if (delta >= 1.566 && delta <= 1.766)
            write("  PASS: ISO 16844 retention at -10°C ✅");
        else if (delta < 0)
            write("  FAIL: ROLLBACK at -10°C! ISO 16844 violation ❌");
        else
            write("  FAIL: Delta out of tolerance ❌");
        setTimer(seqTimer, 30000);
        break;
    }
}
```

**Step 4 — Results:**

| Cycle | ODO Before | ODO After | Delta | Result |
|---|---|---|---|---|
| 1 | 127.400 | 129.062 | 1.662 | ✅ |
| 2 | 129.062 | 130.726 | 1.664 | ✅ |
| 3 | 130.726 | **130.726** | **0.000** | ❌ ROLLBACK |
| 4 | 130.726 | 132.391 | 1.665 | ✅ |
| 5 | 132.391 | 134.058 | 1.667 | ✅ |

Cycle 3 showed a zero delta — the distance was not retained. Investigated: in Cycle 3 I had reduced KL15 OFF hold time to 2.5s (standard) to test the boundary. At -10°C with slower MCU clock, the NVM write needed 3.2s. 2.5s was insufficient.

**Step 5 — Fix recommendation:**
Raised BYD-CLU-2227: *"ISO 16844 NVM retention fails at -10°C with standard 2.5s KL15 hold time. Minimum hold required at cold temperatures: 3.5s. Recommended: SW increases KL15 OFF hold timer to 4.0s unconditionally (no temperature dependency = simpler implementation)."*

### Result
- Fix applied in IC_SW_v2.4.2: KL15 OFF minimum hold extended to 4.0s
- Cold soak test re-run at -10°C: 5/5 cycles passed including at the 4.0s boundary
- Also extended to +80°C soak test (hot): 5/5 passed (NVM is faster at high temp — no issue)
- BYD design team added cold NVM retention test to the standard cluster test procedure for all future platforms
- This was the first cold-temperature cluster test ever run on this project — I proposed it proactively based on the thermal engineer's question (no one had asked for it)
- ISO 16844 compliance confirmed across full temperature range (-10°C to +80°C) for the first time

---

## STAR 12 — Instrument Cluster Backlighting Validation (PWM + LIN Bus)

### Situation
The BYD Sealion 7 cluster backlight is controlled via a LIN bus signal from the BCM (Body Control Module) — `BCM_LIN.BacklightLevel` (0–255, 8-bit, LIN2.2A). The cluster must scale this to its internal PWM backlight driver to produce luminance levels matching the OEM's photometric specification (Table 6 in IC_SRS_BYD_Rev_D: 12 luminance levels from 2 cd/m² at night to 350 cd/m² at full day).

During backlighting validation, two issues emerged: LIN frame not arriving (CANoe had no LIN cluster configured on the bench), and the photometric measurement was being done visually — subjective and not repeatable.

### Task
Set up LIN backlight injection in CANoe, execute the 12-level backlighting validation accurately, and either integrate a luminance measurement tool or establish an objective proxy measurement.

### Action

**Step 1 — Configure LIN cluster in CANoe:**
```capl
/* LIN backlighting — BCM simulation node on LIN channel 1 */
/* LIN DB: BCM_LIN.ldf | Frame: 0x4A BCM_Lighting | Signal: BacklightLevel */

variables {
    msTimer txLIN;
    byte backlight_level = 128;    /* start at mid */
}

on start {
    write("[LIN] BCM backlighting simulation started on LIN Ch1");
    setTimer(txLIN, 20);   /* LIN frame cycle 20ms */
}

on timer txLIN {
    linFrame BCM_Lighting frame;
    frame.BacklightLevel = backlight_level;
    frame.BacklightEnable = 1;
    output(frame);
    setTimer(txLIN, 20);
}

/* Panel slider control for manual brightness setting */
on envVar BacklightSlider {
    backlight_level = getValue(this);
    write("[LIN] Backlight level = %d / 255", backlight_level);
}
```

**Step 2 — Calibration sweep:**
```capl
void run_backlight_sweep() {
    /* 12 OEM-specified levels: 0,23,46,69,92,115,138,161,184,207,230,255 */
    byte levels[12] = {0,23,46,69,92,115,138,161,184,207,230,255};
    int i;

    for (i = 0; i < 12; i++) {
        backlight_level = levels[i];
        TestWaitForTimeout(2000);   /* allow cluster PWM to stabilise */

        /* Proxy measurement: read cluster's own backlight DID */
        diagRequest ClusterDiag.ReadDataByIdentifier req;
        req.dataIdentifier = 0xF470;   /* Cluster internal PWM duty cycle % */
        req.SendRequest();
        byte pwm = req.GetDataByte(0);
        write("BacklightLevel=%d | ClusterPWM=%d%% | Measure lux on bench",
              levels[i], pwm);
    }
}
```

**Step 3 — Objective measurement:**
Integrated a Konica Minolta CL-200A illuminance meter on a fixed stand 50cm from cluster face. For each of the 12 levels, recorded the lux value. Cross-referenced to the SRS cd/m² values using an empirical conversion factor (measured once at midscale to calibrate the proxy).

Results (sample):

| LIN Level | PWM Duty | Measured (lux) | SRS Target (cd/m²) | Pass? |
|---|---|---|---|---|
| 0 | 1% | 0.8 lux | 2 cd/m² | ✅ |
| 115 | 48% | 89 lux | 90 cd/m² | ✅ |
| 230 | 93% | 298 lux | 300 cd/m² | ✅ |
| 255 | 100% | 351 lux | 350 cd/m² | ✅ |

One defect found: LIN level 23 produced 0% PWM (completely off) instead of ~9%. Root cause: cluster PWM lookup table had no entry for levels 1–25 — mapped to 0% (dark). Raised BYD-CLU-2229.

### Result
- BYD-CLU-2229 fixed in IC_SW_v2.4.1: PWM table extended to cover LIN 0–255 range linearly below level 25
- All 12 luminance levels verified with objective lux measurement — no subjective pass/fail
- LIN backlighting injection setup shared with 2 other LTTS cluster engineers (they had been substituting manual bench pot adjustments)
- Luminance measurement procedure documented as the project standard — using illuminance meter + DID proxy for repeatability
- Photometric validation replaced entirely subjective visual assessment with logged numeric results accepted by BYD OEM

---

## STAR 13 — Multi-Engineer Parallel Test Execution Sprint Planning (Capacity Management)

### Situation
Sprint 08 of the BYD Sealion 7 project was the largest sprint: 120 test cases across 6 feature areas — SOC gauge, range display, telltales, DIS, backlighting, and charging animation. I had 5 engineers, 2 CANoe bench setups, and 10 working days. Naive assignment would have created bench bottlenecks — 5 engineers competing for 2 benches.

### Task
Plan the sprint so that bench utilisation was maximised, engineers were never idle waiting for bench access, and the 120 TCs were completed within 10 days with no overtime.

### Action

**Step 1 — Categorise TCs by bench dependency:**
- **Type A — Bench required (real hardware):** 68 TCs (SOC gauge, telltales, charging anim, backlighting)
- **Type B — CANoe software only (no physical cluster needed):** 32 TCs (signal inject, logging, DBC verify)
- **Type C — UDS-only (cluster ECU + laptop, no full bench):** 20 TCs (DID reads, DTC reads, variant write)

Type B and C did not need the 2 main bench setups.

**Step 2 — Capacity calculation:**
```
2 benches × 10 days × 6 hours/day = 120 bench-hours
Type A TCs: 68 TCs × avg 45 min = 51 bench-hours → fits in one bench for 8.5 days
Type B TCs: 32 TCs × avg 20 min → assigned to 2 engineers on laptops (no bench needed)
Type C TCs: 20 TCs × avg 25 min → separate engineer with EVK (ECU development kit)
```

**Step 3 — Engineer assignment matrix:**

| Engineer | Days 1–5 | Days 6–10 | Bench? |
|---|---|---|---|
| Suresh (senior) | SOC gauge TCs (Bench 1) | Telltale TCs (Bench 1) | Yes |
| Ravi (mid) | Charging animation (Bench 2) | DIS TCs (Bench 2) | Yes |
| Priya (mid) | UDS DID/DTC TCs (EVK) | Variant coding (EVK) | EVK |
| Anjali (junior) | Type B signal TCs (laptop) | Type B logging TCs (laptop) | No |
| I (lead) | Backlighting (Bench 1 or 2 as available) | Sprint reviews + unblocking | Mixed |

**Step 4 — Buffer allocation:**
- Days 9–10 reserved as buffer — no TCs scheduled, kept for defect retest and rework
- If sprint ran ahead: buffer used for exploratory testing on the charging fallback scenario (not in plan but on the risk register)

**Step 5 — Daily TC burn-down visible:**
Pinned a shared Excel burn-down chart in Teams updated by each engineer at end of day. If any day fell behind by >5 TCs, I triggered a same-day review.

### Result
- 118/120 TCs executed by Day 9 — 2 TCs blocked by a bench HW issue (oscilloscope calibration, booked for Day 10)
- All 120 TCs done by Sprint end — no overtime, no weekend work
- Bench utilisation: Bench 1 — 94%, Bench 2 — 88% (near optimal for 2 shared resources)
- 12 defects found — all raised by Day 8, giving SW team 4 days to start fixes
- Sprint retrospective feedback from team: "Most organised sprint in the project — always knew what I was supposed to be doing"
- Planning matrix reused directly in Sprint 09 and Sprint 10 — became the project sprint planning template

---

## STAR 14 — Cluster DIS Message Validation (Driver Information System)

### Situation
The BYD Sealion 7 cluster DIS (Driver Information System) — the centre information display — showed 11 types of messages: charging status, ADAS alerts, door-ajar warnings, low-SOC prompt, range low warning, tyre pressure warnings, seatbelt reminders, speed limit sign display (from ADAS camera), trip computer data, service reminders, and OTA update notifications. 

Each message had priority rules: high priority messages (ADAS warning, low SOC) must preempt low priority messages (trip data, service reminder). Manual testing of priority ordering was extremely slow — required manually triggering each combination of 2–3 simultaneous messages and visually checking which one was displayed.

### Task
Design a systematic DIS priority matrix test covering all meaningful combinations of simultaneous messages, and implement it as a CAPL automated injection to replace the manual approach.

### Action

**Step 1 — Priority matrix from SRS:**
```capl
/* DIS Message priority table — from BYD IC_SRS_Rev_D Appendix I */
typedef struct {
    int    priority;   /* 1 = highest */
    char   msg_name[30];
    long   trigger_msg_id;
    byte   trigger_byte;
    byte   trigger_mask;
} DISMessage_t;

DISMessage_t dis_messages[11] = {
    {1,  "ADAS_FCW_Alert",          0x500, 0, 0x80},
    {2,  "LowSOC_Critical",         0x3A2, 3, 0x01},
    {3,  "ADAS_LKA_Alert",          0x500, 0, 0x40},
    {4,  "TyrePressureLow",         0x3C0, 4, 0x01},
    {5,  "Seatbelt_Reminder",       0x3A0, 0, 0x04},
    {6,  "DoorAjar",                0x3A0, 0, 0x10},
    {7,  "LowSOC_Warning",          0x3A2, 3, 0x02},
    {8,  "RangeLow_Warning",        0x3A3, 2, 0x01},
    {9,  "ServiceReminder",         0x630, 0, 0x01},
    {10, "OTA_Update_Available",    0x620, 0, 0x01},
    {11, "TripComputer",            0x640, 0, 0x01}
};
```

**Step 2 — Pairwise combination test (key pairs by SRS priority rule):**
```capl
void test_dis_priority_pair(DISMessage_t high_prio, DISMessage_t low_prio) {
    write("Testing: [P%d]%s vs [P%d]%s",
          high_prio.priority, high_prio.msg_name,
          low_prio.priority, low_prio.msg_name);

    /* Inject lower priority first */
    inject_dis_trigger(low_prio);
    TestWaitForTimeout(500);
    write("  Step 1: %s injected — OBSERVE on DIS", low_prio.msg_name);

    /* Inject higher priority — should preempt */
    inject_dis_trigger(high_prio);
    TestWaitForTimeout(500);
    write("  Step 2: %s injected — OBSERVE: DIS must switch to HIGH PRIO message",
          high_prio.msg_name);

    /* Read DIS current message via UDS */
    int shown = read_dis_active_message_uds();
    if (shown == high_prio.priority) {
        write("  PASS: High priority message displayed correctly");
    } else {
        write("  FAIL: DIS showing P%d instead of P%d — PRIORITY BUG", shown, high_prio.priority);
    }

    /* Clear both */
    clear_dis_trigger(high_prio);
    clear_dis_trigger(low_prio);
    TestWaitForTimeout(300);
}

void inject_dis_trigger(DISMessage_t msg) {
    message 0x000 m;
    m.id = msg.trigger_msg_id;
    m.byte(msg.trigger_byte) |= msg.trigger_mask;
    output(m);
}
```

**Step 3 — Key defect found (P1 vs P3 swap):**
FCW_Alert (P1) was being displaced by TPMS warning (P4) when both were active simultaneously. ADAS alert was disappearing from DIS — a safety-relevant display failure.

Root cause: The DIS priority manager had a boundary condition bug — when 3+ messages were simultaneously active, a buffer overflow caused the priority index to wrap to 0 (lowest). Raised BYD-CLU-2233 (S1 — safety: ADAS alert masked by lower priority content).

### Result
- 22 pairwise combinations tested — 19 passed, 3 failed (all corrected in IC_SW_v2.5.0)
- BYD-CLU-2233 (safety-relevant DIS priority buffer overflow) fixed before gateway
- DIS priority test became part of the formal regression suite — ran on every new build
- Manual DIS testing time: 3 days → CAPL automated: 90 minutes
- SW team lead commented: "We didn't know a 3-way priority combination could wrap the buffer — the systematic pair/triple testing is what found this"

---

## STAR 15 — Handling an OEM Requirement Change 2 Days Before Gateway (Risk Decision)

### Situation
Two days before the BYD Sealion 7 cluster gateway review, the BYD system lead sent an email: *"We have updated IC_SRS_Rev_D to Rev_E. The change: the low-SOC warning threshold is moved from 15% to 12%. Please update and re-verify before gateway."*

This was a 2-line SRS change but affected:
- TC_EV_003 (Low battery warning test) — expected result was 15%, now 12%
- The threshold is stored in cluster flash via UDS DID 0xF4A0 — needed verification that the new SW build had the correct value
- If the build was not updated, the telltale would activate at the wrong SOC — a customer experience issue (warning fires 3% too early)

I had 2 days, one engineer available (Anjali), and the build team was under a freeze.

### Task
Assess whether the SRS change could be verified in 2 days, whether the build team could release a patch, and communicate a clear risk position to the PM.

### Action

**Step 1 — Immediate UDS check (30 minutes):**
```capl
/* Read current low-SOC threshold from cluster — DID 0xF4A0 */
void read_low_soc_threshold() {
    diagRequest ClusterDiag.ReadDataByIdentifier req;
    req.dataIdentifier = 0xF4A0;
    req.SendRequest();
}

on diagResponse ClusterDiag.ReadDataByIdentifier {
    if (this.dataIdentifier == 0xF4A0) {
        byte raw = this.GetDataByte(0);
        float threshold = raw * 0.5;   /* Factor 0.5 per DID spec */
        write("Current LowSOC threshold = %.1f%% (SRS requires 12%%)", threshold);
    }
}
/* Result: threshold = 15.0% — build not yet updated */
```

**Step 2 — Communicated options to PM within 1 hour:**

```
EMAIL TO PM (same day, 11:30am):

OPTIONS for IC SRS Rev_E — LowSOC Threshold Change:

OPTION A — Gateway proceeds as planned
  Risk: Cluster will warn at 15% (old threshold). Real vehicle: customer gets
  warning 3% earlier than intended. NOT a safety issue. Minor CX impact.
  Mitigation: OEM accepts risk, fix in next OTA release.

OPTION B — Emergency build patch + quick verify (build team feasibility TBC)
  Action: Build team updates DID 0xF4A0 calibration from 15% to 12%.
  Verify: 1 TC (TC_EV_003 re-run) — 2 hours bench time.
  Risk: Late build = new regression risk on everything else.

OPTION C — Gateway conditioned on threshold fix in 2 weeks
  Proceed to gateway, present both options to BYD, let OEM decide.

My recommendation: OPTION C — threshold change is low risk, calibration-only,
no safety impact. Gateway should not be delayed for a 1-DID calibration change.
```

**Step 3 — OEM chose Option B (quick patch):**
Build team confirmed calibration-only patch (DID update only, no logic change) was 45 minutes of effort in IC_SW_v2.5.1.

Anjali executed TC_EV_003 re-run in 90 minutes:
```capl
/* TC_EV_003 re-run for Rev_E: threshold = 12% */
void test_low_soc_warning_reve() {
    float soc;
    for (soc = 20.0; soc >= 9.0; soc -= 1.0) {
        inject_soc(soc);
        TestWaitForTimeout(300);
        int warn = read_telltale_status_via_uds(0x02);   /* bit 1 = LowBatt */
        write("SOC=%.0f%% | LowBattWarn=%d", soc, warn);
        if (soc == 12.0 && warn == 1) write("  PASS: Warning activates at 12%% ✅");
        if (soc == 13.0 && warn == 1) write("  FAIL: Warning fires at 13%% — still old threshold");
    }
}
```
Result: Warning activated at 12.0% ✅ — patch verified.

### Result
- TC_EV_003 passed with Rev_E threshold in 90 minutes — same day as patch release
- Gateway not delayed — SRS Rev_E compliance confirmed at entry
- UDS DID approach meant verification required only 1 TC re-run, not full regression
- PM adopted the "options email" format (ABCD + recommendation + risk) as the team's standard change management communication after this incident
- BYD system lead commended the quick response: "90 minutes from patch delivery to verified result is impressive"

---

## STAR 16 — Proactive Test Coverage Gap Found Through Traceability Review

### Situation
At the end of Sprint 10 (2 weeks before final gateway), I ran a mandatory traceability matrix review — mapping every SRS requirement to its test case execution result. I found that SRS section 7.4 (Cluster response during HV system pre-charge failure) had no test cases at all — the entire section had been missed in TC authoring. 

Section 7.4 specified: *"If VCU reports pre-charge failure (VCU_Status.PreChargeFail = 1), cluster shall display a red warning message 'HV SYSTEM FAULT — DO NOT DRIVE' within 500ms and deactivate the READY lamp."*

This was a safety-relevant requirement (ASIL B consequence — driver told vehicle is ready when it is not safe). 6 test cases were needed.

### Task
Author, review, and execute all 6 TCs within the remaining 2 weeks without impacting other sprint work — and decide whether to proactively disclose the gap to BYD.

### Action

**Step 1 — TC authoring on Day 1:**
All 6 TCs authored using the pre-charge failure signal:
```capl
/* Pre-charge failure injection */
void inject_precharge_failure() {
    message VCU_Status vcu;
    vcu.ReadySignal    = 0;
    vcu.PreChargeFail  = 1;   /* HV system fault */
    output(vcu);
}

/* TC_HV_001: Verify warning message within 500ms */
void tc_hv_001() {
    double t_start = timeNow() / 1e5;
    inject_precharge_failure();
    /* Wait for cluster DIS broadcast with warning content */
    /* DIS active message DID 0xF480 = current displayed message code */
    int timeout_ms = 600;
    while ((timeNow() / 1e5 - t_start) < timeout_ms) {
        int dis_msg = read_dis_active_message_uds();
        if (dis_msg == 0x15) {   /* 0x15 = HV system fault message code */
            write("PASS TC_HV_001: HV fault message displayed in %.0f ms",
                  timeNow() / 1e5 - t_start);
            return;
        }
        TestWaitForTimeout(50);
    }
    write("FAIL TC_HV_001: HV fault message NOT displayed within 600ms");
}

/* TC_HV_002: READY lamp deactivated when PreChargeFail=1 */
void tc_hv_002() {
    inject_precharge_failure();
    TestWaitForTimeout(600);
    int ready = read_telltale_status_via_uds(0x40);   /* bit 6 = READY */
    if (ready == 0) write("PASS TC_HV_002: READY lamp deactivated ✅");
    else            write("FAIL TC_HV_002: READY lamp still ON during HV fault ❌");
}
```

**Step 2 — Disclosure decision:**
I chose full transparency — disclosed the gap to BYD on Day 2 of TC authoring, not after execution:

*"During our traceability review we identified SRS Section 7.4 was not covered in our test plan. We have authored 6 TCs and will execute them this week. I want to flag this proactively rather than wait for it to appear at gateway."*

**Step 3 — Execution results:**
- TC_HV_001: FAIL — warning message appeared at 780ms (SRS: ≤500ms)
- TC_HV_002: PASS — READY lamp deactivated correctly
- TC_HV_003–006: PASS

Raised BYD-CLU-2240 for TC_HV_001 (P1 — ASIL B, 280ms latency violation).

### Result
- BYD-CLU-2240 fixed in IC_SW_v2.5.2 (SW processing optimised, message now appears in 210ms)
- All 6 TCs verified passed — SRS Section 7.4 fully covered before gateway
- BYD response to disclosure: "The proactive communication was the right approach. Finding it in review is far better than finding it at gateway."
- Traceability review scheduled at N-14 days (2 weeks before gateway) formally added to the project closure checklist
- This was the second time on the project a proactive traceability review found a gap that would have been a gateway stopper — reinforced the value of the process

---

## STAR 17 — Cluster Speed Display Overshoot at Cold Start (-20°C)

### Situation
A BYD thermal test engineer forwarded a field-simulation report: *"At -20°C cold start, the speedometer needle was observed swinging to ~40 km/h momentarily at KL15 ON before settling to 0."* This had been observed on the development vehicle during a winter pre-production drive in a cold chamber. It was logged as an observation — not a formal defect — because no cluster engineer had been present.

I was asked to reproduce it on the bench and classify it.

### Task
Reproduce the -20°C cold start speedometer overshoot on the HIL bench, determine the root cause, classify the severity, and deliver a technical recommendation.

### Action

**Step 1 — Reproduce at -20°C:**
- Soaked cluster ECU at -20°C for 3 hours in environmental chamber
- Powered via HIL bench — no VehicleSpeed signal injected at KL15 ON (vehicle is stationary)
- Monitored the cluster's own speed broadcast (DID 0xF110 — displayed speed) via UDS every 100ms during the first 5 seconds after KL15 ON

Results:
```
T=0ms   KL15 ON
T=180ms DID 0xF110 = 0.0 km/h
T=220ms DID 0xF110 = 38.5 km/h  ← spike
T=270ms DID 0xF110 = 12.0 km/h
T=380ms DID 0xF110 = 0.0 km/h
T=400ms+ DID 0xF110 = 0.0 km/h  (stable)
```

Reproduced: 38.5 km/h spike at T=220ms, resolved by T=380ms.

**Step 2 — Root cause:**
The cluster ADC (Analog-to-Digital converter) reading for the vehicle speed pulse input had an unstable reference voltage during the first 200ms at -20°C (voltage regulator warm-up). During this window, the ADC read a spurious pulse train and the firmware incorrectly calculated a speed.

This was confirmed by reading the ADC reference voltage DID (0xF462) during cold start — it showed 2.8V at T=180ms instead of the expected 3.3V. Speed calculation uses the ADC reference in the conversion formula — an incorrect reference produces an incorrect speed.

**Step 3 — Severity classification:**
- Duration: 200ms spike — too short for driver perception (human reaction time ~250ms)
- Regulation: UN ECE Reg 39 — no specific requirement on transient at KL15 ON (regulation governs steady-state display)
- Safety: A momentary 38 km/h display at rest could be alarming to a driver but is not actionable (cannot engage drive in 200ms)
- OEM SRS IC_GAUGE_REQ_001: *"Speedometer shall display 0 km/h within 500ms of KL15 ON when vehicle is stationary"* — **violated** (0 km/h restored at 380ms, within 500ms window)

Assessed as P2 (functional — SRS technically met at 380ms < 500ms, but the transient spike is a robustness issue) rather than P1. Documented clearly with the distinction.

**Step 4 — Fix recommendation:**
Two options:
1. SW: Add a startup mask — suppress speedometer updates for first 300ms after KL15 ON (simple, low risk)
2. HW: Faster voltage regulator warm-up (expensive, next platform)

Recommended Option 1 — SW mask.

### Result
- IC_SW_v2.5.2 implemented the 300ms startup mask for speedometer
- Cold cold start test repeated at -20°C: no spike observed — DID 0xF110 = 0.0 km/h for first 500ms, then reflects actual speed correctly
- BYD thermal team confirmed fix also resolved the field observation
- HW team noted the ADC reference instability as a known cold-temp behaviour and logged it for next-platform HW design improvement
- My proactive classification (P2 not P1) was reviewed and agreed by BYD system safety team — speeded up fix prioritisation

---

## STAR 18 — Automating Nightly Regression for BYD Sealion 7 Cluster (Python + CANoe)

### Situation
By Sprint 07, the BYD Sealion 7 cluster SW team was releasing new builds every 3–4 days. Each build required regression of 40 critical-path TCs (SOC gauge, READY lamp, charging animation, NVM, timeout fallback). Manual regression took 2 engineers a full day — and it was the same 40 TCs every time.

### Task
Implement a nightly automated regression system that loaded each new build overnight and delivered a pass/fail summary to the team by 9am — without engineer involvement.

### Action

**Step 1 — CANoe headless command-line execution:**
```bat
REM nightly_regression.bat — runs at 22:00 via Windows Task Scheduler
SET CAPL_CFG=C:\Projects\BYD_Cluster\IC_Validation.cfg
SET RESULTS=C:\Projects\BYD_Cluster\results\%DATE%

"C:\Program Files\Vector CANoe 17\Bin\CANoe.exe" ^
    /cfg "%CAPL_CFG%" ^
    /testmodule BYD_Cluster_NightlyRegression.vts ^
    /output "%RESULTS%\" ^
    /exit_on_completion
```

**Step 2 — Python build watcher:**
```python
# build_watcher.py — polls build server every 30 min
# If new IC SW build detected → copies to bench PC → triggers nightly run

import requests, shutil, subprocess, smtplib, time
from pathlib import Path

BUILD_SERVER = "http://byd-build-server/api/latest?ecuid=IC"
LOCAL_BUILD  = Path("C:/SwBuilds/IC_Latest.hex")
LAST_BUILD   = ""

while True:
    resp = requests.get(BUILD_SERVER, timeout=10)
    build_info = resp.json()
    build_id = build_info["build_id"]

    if build_id != LAST_BUILD:
        print(f"New build detected: {build_id}")
        shutil.copy(build_info["hex_path"], LOCAL_BUILD)
        LAST_BUILD = build_id
        # Flash new build to cluster ECU via bench flash tool
        subprocess.run(["BenchFlash.exe", "--target=IC", f"--hex={LOCAL_BUILD}"])
        # Trigger CANoe regression at 22:00 (handled by Task Scheduler)
        # Send advance notice
        send_email(subject=f"New IC Build {build_id} — Nightly Regression Tonight",
                   body=f"Build {build_id} flashed. Regression starts at 22:00.")

    time.sleep(1800)   # check every 30 min
```

**Step 3 — Result parser and HTML email:**
```python
# parse_results.py — runs at 06:00 after CANoe nightly completes
import xml.etree.ElementTree as ET, smtplib
from email.mime.text import MIMEText

tree = ET.parse("results/latest/test_report.xml")
root = tree.getroot()

passed = failed = 0
rows = ""
for tc in root.findall(".//testcase"):
    tc_id  = tc.get("name")
    result = tc.get("verdict")
    color  = "#90EE90" if result == "passed" else "#FFB6C1"
    rows += f"<tr style='background:{color}'><td>{tc_id}</td><td>{result}</td></tr>"
    if result == "passed": passed += 1
    else: failed += 1

html = f"""
<h2>BYD Cluster Nightly Regression — {passed+failed} TCs</h2>
<p>✅ Passed: {passed} &nbsp; ❌ Failed: {failed}</p>
<table border='1'>{rows}</table>
"""
# Email to team at 06:30
send_html_email(to="cluster-team@ltts.com", subject=f"Nightly Result: {passed}P {failed}F",
                html=html)
```

**Step 4 — Jira auto-defect creation:**
```python
# If any TC fails: auto-create Jira defect
import requests

JIRA = "https://ltts-jira.atlassian.net/rest/api/2"
AUTH = ("user@ltts.com", "API_TOKEN")

def create_defect(tc_id, build_id):
    payload = {
        "fields": {
            "project": {"key": "BYDCLUSTER"},
            "summary": f"REGRESSION: {tc_id} failed in build {build_id}",
            "issuetype": {"name": "Bug"},
            "priority": {"name": "High"},
            "description": f"TC {tc_id} failed in nightly regression. Build: {build_id}. See attached HTML report."
        }
    }
    resp = requests.post(f"{JIRA}/issue", json=payload, auth=AUTH)
    print(f"Defect created: {resp.json()['key']}")
```

### Result
- Nightly regression running **40 TCs per night** by Sprint 08
- 3 build-introduced regressions caught overnight before engineers started work (READY lamp, charging animation, SOC threshold)
- Manual regression effort eliminated: 2 engineer-days per build → 0 hours
- Jira auto-defect creation saved 15 minutes per failure per morning
- Build-to-result turnaround: new build at 18:00 → results email at 06:30 next morning (12.5 hours)
- PM requested the Python build watcher + HTML reporter be packaged as an LTTS tool for all future cluster projects

---

## STAR 19 — Responding to a Cluster Freeze in Final Integration Testing

### Situation
During final integration testing on the BYD Sealion 7 full vehicle bench (all ECUs connected — VCU, BMS, ADAS DCU, BCM, cluster), the cluster froze completely 4 minutes into a simulated drive scenario. All displays went blank, no touchscreen response, no CAN TX from cluster — but the cluster was still powered (KL30/KL15 active). Recovery required KL30 cycle.

The SW team's first response: "Not reproducible on our standalone bench — must be a bench issue." I had 48 hours to investigate before the integration review with BYD.

### Task
Determine whether the cluster freeze was a bench artefact or a real integration defect, and provide reproducible evidence either way within 48 hours.

### Action

**Step 1 — Characterise the conditions (Day 1 morning):**
Reproduced the freeze 3 times on the full vehicle bench. Key conditions:
- Always occurs between T=230s and T=260s of the drive scenario (narrow window)
- Does NOT occur on standalone cluster bench (SW team correct — it's integration-specific)
- At the moment of freeze: ADAS DCU was broadcasting high-frequency Ethernet diagnostic frames (1000BASE-T1 at 98% bus load — a stress test phase of the scenario)

**Step 2 — Hypothesis: Ethernet bus load causing cluster CPU overload:**
The BYD Sealion 7 cluster had an Automotive Ethernet interface (100BASE-T1) for ADAS icon data (speed limit signs, lane marking overlays). The ADAS DCU was flooding the 100BASE-T1 link at 98% bandwidth — the cluster had no rate-limiting on its Ethernet receive buffer.

Verified with CANoe Ethernet analysis:
```capl
/* Monitor cluster Ethernet RX buffer state via UDS */
diagRequest ClusterDiag.ReadDataByIdentifier req;
req.dataIdentifier = 0xF480;   /* Ethernet RX buffer fill level */
req.SendRequest();
/* Result just before freeze: 0xFF = buffer full (overflow) */
```

When the Ethernet receive buffer overflowed, the cluster OS memory manager failed → watchdog did not kick in (watchdog was disable during integration lab sessions for easier debugging) → CPU deadlock.

**Step 3 — Reproduced isolation test:**
Connected only cluster + ADAS DCU (no other ECUs). Replayed the high-bandwidth Ethernet scenario → cluster froze at exactly the same point. Confirmed: not a full-integration issue — strictly ADAS Ethernet RX + cluster buffer management.

Raised BYD-CLU-2245 (P1 — system integration failure: cluster hangs under ADAS Ethernet bus load):
- Root cause: Cluster Ethernet RX buffer unbounded — no flow control or rate limiting
- Secondary cause: Watchdog disabled in integration lab builds
- Fix recommendation: (1) Enable flow control on cluster 100BASE-T1 RX. (2) Re-enable watchdog in all builds (debug logging can remain without disabling watchdog)

**Step 4 — Verified fix:**
After IC_SW_v2.5.3 (RX rate limiting + watchdog re-enabled), ran the full drive scenario at 98% Ethernet bus load for 30 minutes: zero freeze.

### Result
- BYD-CLU-2245 reproduced, root-caused, and fix verified within 48 hours
- Integration review with BYD proceeded without obstruction — defect had a fix in hand
- SW team lead acknowledged: "The Ethernet buffer flow control was a design gap we hadn't considered — the standalone bench never exercises the real bus load"
- Watchdog re-enabling policy: changed from "disable for debug convenience" to "always enabled — use log reduction if needed"
- This was the most complex root cause investigation of the project — required correlating Ethernet bus analysis, UDS buffer DID reads, and standalone reproduction in sequence

---

## STAR 20 — Final Pre-SOP Sign-Off Validation (Closing the Project)

### Situation
After 14 months of BYD Sealion 7 cluster validation, all 320 TCs were executed, all P1/P2 defects were verified closed. The final milestone was SOP (Start of Production) sign-off — a formal BYD internal review where the cluster validation team had to present evidence of complete validation coverage and confirm the cluster was production-ready.

My manager asked me to lead the SOP sign-off presentation — the most important customer-facing event of the project.

### Task
Prepare and deliver a complete, accurate, and credible SOP validation closure presentation to BYD's system architect, safety lead, and production quality manager — and achieve formal production release sign-off.

### Action

**Step 1 — Pre-SOP internal audit (2 weeks before):**
```
Traceability: 320/320 TCs executed ✅
Open defects: P1=0, P2=0, P3=6 (all accepted by OEM with corrective plan) ✅
SW baseline: IC_SW_v2.5.3 ✅ (git hash locked, tagged)
DBC baseline: Powertrain_v3.2.dbc + EV_BMS_v2.0.dbc ✅
CANoe config: IC_Validation_v1.8.cfg ✅ (MD5 hash recorded)
Cold temp validation: -10°C NVM (STAR 11), -20°C speed spike (STAR 17) ✅
ISO 16844 compliance: Odometer retention verified all conditions ✅
ISO 26262 FTA: READY lamp ASIL B (STAR 3) verified and DTC-free ✅
LIN backlighting: 12 levels lux-measured ✅
DIS priority: 22 pairwise combinations ✅
UDS DTC: 0 stored DTCs on production SW baseline ✅
Variant validation: 4 variants (CN Std, LR, Perf, EU Export) ✅
```

**Step 2 — SOP presentation structure (12 slides):**
1. Project scope and timeline summary
2. Test coverage overview — 320 TCs mapped to SRS requirements (heatmap)
3. Defect lifecycle summary — opened, fixed, verified trend chart
4. P1 defect deep dives (5 most significant — STAR 3, 9, 14, 16, 19)
5. Safety-relevant features validation evidence (READY lamp, DIS HV fault)
6. Temperature range validation summary (-20°C to +80°C)
7. UDS validation summary — all DIDs, DTCs, Security Access
8. Multi-variant coverage matrix
9. Open P3 defects — each with BYD-accepted risk statement
10. Tool and SW baseline lock confirmation
11. Process improvements introduced during project (8 new checks added to future standards)
12. Production release recommendation

**Step 3 — Prepared for hard questions:**

Potential Q: "You found 5 P1 defects — could there be more we haven't found?"
Answer: "The SRS has 287 requirements. 320 TCs cover 287/287 — 100% SRS traceability. For ASIL B features, each requirement has at least 3 TCs (positive, negative, boundary). The 5 P1s found and fixed demonstrate the coverage is effective, not insufficient."

Potential Q: "Why are 6 P3 defects still open?"
Answer: *[Prepared specific OEM-accepted closure note for each of the 6 — ready to share screen.]*

**Step 4 — Delivered the presentation:**
90-minute session. 3 clarifying questions from BYD safety lead — all answered from prepared evidence. No surprises.

**Final question from BYD production quality manager:** "Do you certify this cluster is production-ready?"
Answer: *"Based on 14 months of validation, 320 TCs executed, zero P1/P2 open, full SRS traceability, verified ISO 16844 and ISO 26262 compliance — yes, I am confident this cluster meets the production entry criteria defined in the BYD SOP checklist."*

### Result
- **SOP sign-off granted in the same session** — no follow-up required
- BYD system architect: *"This is the most complete validation closure pack we have received from any supplier on this programme."*
- 6 open P3 defects formally accepted by BYD with agreed corrective plan for first OTA update
- Project closure report filed by PM citing zero escaped P1/P2 defects to production
- I received a project excellence award from LTTS management
- The 8 process improvements introduced during this project were formalised as LTTS Bangalore Cluster Validation Standards for all future projects
- First time in LTTS cluster history: a project achieved 100% SRS traceability at SOP sign-off

---

## Quick Reference — BYD Sealion 7 Cluster Experience Summary

| Area | What You Can Claim | Evidence from STAR |
|---|---|---|
| EV cluster signals (SOC, range, READY, regen) | Validated all four from CAN FD injection to UDS read-back | STAR 1, 3, 8 |
| UDS diagnostics (0x22, 0x27, 0x2E, 0x19) | Security Access seed-key, DID read/write, DTC lifecycle | STAR 2, 5 |
| CAN FD validation | Managed BMS_Status, VCU_Status, charging frames on CAN FD | All STAR |
| Safety-relevant defect escalation | READY lamp ISO 26262, ASIL B DIS priority, HV pre-charge | STAR 3, 14, 16 |
| Charging animation (AC/DC/regen) | Root-caused DBC factor mismatch via UDS internal DID check | STAR 6 |
| CAN FD Bus-Off recovery | Error frame injection, Bus-Off characterisation, fix verified | STAR 9 |
| Telltale localisation EU export | ISO 2575 vs MIIT asset mapping, UDS asset manifest DID | STAR 10 |
| Cold temperature validation | -10°C NVM (ISO 16844), -20°C cold start speed spike | STAR 11, 17 |
| LIN bus (backlighting) | LIN2.2A frame injection, lux photometric measurement | STAR 12 |
| Multi-variant sprint planning | 120 TCs, 5 engineers, 2 benches — capacity matrix | STAR 13 |
| DIS priority validation | Pairwise 22-combination test, safety-relevant P1 buffer overflow | STAR 14 |
| OEM requirement change mgmt | ABCD options framework 2 days before gateway | STAR 15 |
| Proactive traceability review | HV pre-charge gap found with 2 weeks to go | STAR 16 |
| OEM audit hosting | Passed BYD audit solo — traceability, defect mgmt, tool lock | STAR 7 |
| Build instability management | Data-driven OEM communication — "right side of curve" | STAR 4 |
| Nightly regression automation | Python + CANoe headless + Jira auto-defect | STAR 18 |
| Cluster freeze root cause | Ethernet RX buffer overflow, watchdog, integration defect | STAR 19 |
| SOP production sign-off | 320 TCs, 100% SRS traceability, formal BYD sign-off | STAR 20 |
| Team lead behaviours | 1:1 coaching, sprint planning, audit prep, OEM escalation | All STAR |

### Bridging to Marelli Interview

> *"On BYD Sealion 7 I led cluster validation for an EV platform — the fundamentals are identical to ICE cluster validation: CAN signal injection, telltale matrix, UDS diagnostics, NVM retention, power mode sequencing. The signal set is different — SOC replaces fuel gauge, READY lamp replaces cranking RPM — but the validation methodology and team leadership challenges are the same. READY lamp timing was a safety-relevant ISO 26262 escalation (STAR 3), range display required cross-ECU signal path analysis (STAR 8), and we achieved 100% SRS traceability at SOP sign-off (STAR 20) — all directly applicable to what Marelli's Cluster Lead role requires."*

---

*File: 08_byd_star_scenarios.md | marelli_cluster_lead series*
