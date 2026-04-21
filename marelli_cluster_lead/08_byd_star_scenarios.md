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

## Quick Reference — BYD Sealion 7 Cluster Experience Summary

| Area | What You Can Claim | Evidence from STAR |
|---|---|---|
| EV cluster signals (SOC, range, READY, regen) | Validated all four from CAN FD injection to UDS read-back | STAR 1, 3, 8 |
| UDS diagnostics (0x22, 0x27, 0x2E, 0x19) | Security Access seed-key, DID read/write, DTC lifecycle | STAR 2, 5 |
| CAN FD validation | Managed BMS_Status, VCU_Status, charging frames on CAN FD | All STAR |
| Safety-relevant defect escalation | READY lamp ISO 26262 violation — escalated correctly | STAR 3 |
| Charging animation (AC/DC/regen) | Root-caused DBC factor mismatch via UDS internal DID check | STAR 6 |
| OEM audit hosting | Passed BYD audit solo — traceability, defect mgmt, tool lock | STAR 7 |
| Build instability management | Data-driven OEM communication — "right side of curve" framing | STAR 4 |
| System integration validation | Range display cross-validated VCU + cluster + BMS signal path | STAR 8 |
| Team lead behaviours | 1:1 coaching, sprint stabilisation, audit prep, defect triage | All STAR |

### Bridging to Marelli Interview

Use this framing when Marelli asks about your cluster lead experience:

> *"On BYD Sealion 7 I led cluster validation for an EV platform — the fundamentals are identical to ICE cluster validation: CAN signal injection, telltale matrix, UDS diagnostics, NVM retention, power mode sequencing. The signal set is different — SOC replaces fuel gauge, READY lamp replaces cranking RPM — but the validation methodology and team leadership challenges are the same. READY lamp timing was a safety-relevant finding that required ISO 26262 escalation, which is directly applicable to ASIL B telltale validation Marelli requires."*

---

*File: 08_byd_star_scenarios.md | marelli_cluster_lead series*
