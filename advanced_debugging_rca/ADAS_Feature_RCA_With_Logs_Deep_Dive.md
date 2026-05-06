# ADAS Feature Root Cause Analysis & Debugging
## Complete Engineering Reference — v2.0

---

| Field | Value |
|---|---|
| **Document ID** | ADAS-RCA-REF-002 |
| **Version** | 2.0 |
| **Date** | May 2026 |
| **Classification** | Internal Technical Reference |
| **Target Audience** | ADAS Validation / Integration / System Engineers |
| **Features Covered** | LKA · LDW · TSR · BSD · Parking · ACC · AEB |
| **Log Types** | CAN (.asc) · ECU System Logs · Serial/UART Debug Logs |
| **Standards** | ISO 26262 · ISO 11270 · ISO 15622 · ISO 22737 · Euro NCAP 2026 |

### Version History

| Ver | Date | Author | Changes |
|---|---|---|---|
| 1.0 | Apr 2026 | ADAS Validation | Initial draft |
| 2.0 | May 2026 | ADAS Validation | Full rewrite: added physics, C-level bug analysis, FMEA, 50 interview Q&A, test specs, state machines, appendices |

---

## Table of Contents

- [Part 0: Reading Guide & Methodology](#part-0-reading-guide--methodology)
- [Part 1: System Architecture](#part-1-system-architecture)
- [Part 2: LKA — Lane Keeping Assist](#part-2-lka--lane-keeping-assist)
- [Part 3: LDW — Lane Departure Warning](#part-3-ldw--lane-departure-warning)
- [Part 4: TSR — Traffic Sign Recognition](#part-4-tsr--traffic-sign-recognition)
- [Part 5: BSD — Blind Spot Detection](#part-5-bsd--blind-spot-detection)
- [Part 6: Parking Assistance / PDC](#part-6-parking-assistance--pdc)
- [Part 7: ACC — Adaptive Cruise Control](#part-7-acc--adaptive-cruise-control)
- [Part 8: AEB — Autonomous Emergency Braking](#part-8-aeb--autonomous-emergency-braking)
- [Appendix A: FMEA Master Table](#appendix-a-fmea-master-table)
- [Appendix B: Complete DTC Reference](#appendix-b-complete-dtc-reference)
- [Appendix C: DBC Signal Catalog](#appendix-c-dbc-signal-catalog)
- [Appendix D: Physics & Math Reference Card](#appendix-d-physics--math-reference-card)
- [Appendix E: Standards Compliance Matrix](#appendix-e-standards-compliance-matrix)
- [Appendix F: ADAS Failure Pattern Library](#appendix-f-adas-failure-pattern-library)
- [Appendix G: Feature Interaction & Conflict Matrix](#appendix-g-feature-interaction--conflict-matrix)
- [Appendix H: Log Analysis Methodology](#appendix-h-log-analysis-methodology)
- [Appendix I: 50 Interview Questions & Expert Answers](#appendix-i-50-interview-questions--expert-answers)

---

# Part 0: Reading Guide & Methodology

## 0.1 How to Read Each Defect Scenario

Every scenario in this document follows a consistent structure:

```
[FEATURE]-[NNN]: [Short Title]
│
├── Classification Header   — Severity, ASIL, Standards, NCAP, FuSa impact
├── Setup & Pre-conditions  — Test environment, vehicle config, reproducibility
├── Symptom                 — What the driver/tester observes
├── Complete Log Triptych
│   ├── CAN Log (.asc)     — Raw CAN bus trace with byte decoding
│   ├── System Log         — ECU internal events (/var/log/adas/)
│   └── Serial/UART Log    — Sensor ECU hardware debug output
├── Annotated Analysis      — Line-by-line observation → interpretation chain
├── 5-Whys Root Cause       — Structured causal chain to root
├── Code-Level Analysis     — Actual C pseudo-code showing bug + fix diff
├── Physics / Math          — Formulas and calculations where applicable
├── FMEA Row                — S / O / D / RPN per AIAG FMEA-4 methodology
├── Formal Defect Report    — Professional ticket-ready report
└── Test Cases (3-5)        — Verification test specifications
```

## 0.2 Log File Format Anatomy

### CAN .asc Format (Vector CANalyzer)

```
   <timestamp>  <channel>  <CAN_ID>  <Dir> d <DLC>  <byte0> <byte1> ... <byteN>
   |            |          |          |    |  |       |
   |            |          |          |    |  |       Hex data bytes
   |            |          |          |    |  Data Length Code (bytes)
   |            |          |          |    Constant 'd' = data frame
   |            |          |          Rx (received) or Tx (transmitted by logger ECU)
   |            |          11-bit or 29-bit CAN identifier
   |            CAN channel (1, 2, ADAS_ECU, etc.)
   Relative time in seconds from trace start
```

**Example decode:**
```
   0.024  ADAS_ECU  0x3A1  Rx  d 8  50 45 52 45 00 00 00 00
          │         │      │   │ │   │  │  │  │
          │         │      │   │ │   │  │  Byte 2: 0x52 = LaneConf_Right = 82%
          │         │      │   │ │   │  Byte 1: 0x45 = scale byte (not a signal)
          │         │      │   │ │   Byte 0: 0x50 = LaneConf_Left = 80%
          │         │      │   │ DLC = 8 bytes
          │         │      │   Received by logger
          │         │      Signal group ID
          │         Transmitting ECU name (resolved from Vector DB)
          24ms from trace start
```

### ECU System Log Format

```
[YYYY-MM-DD HH:MM:SS.mmm] [MODULE] [LEVEL ] Message with context=value pairs
                                    │
                                    ├── INFO  : Normal operational event
                                    ├── DEBUG : Detailed diagnostic output
                                    ├── WARN  : Non-critical anomaly
                                    ├── ERROR : Recoverable error
                                    └── CRIT  : Safety-critical event
```

### Serial/UART Debug Log Format

```
[MODULE][HH:MM:SS.mmm] TAG: key=value key=value ...
│        │              │
│        │              Tag identifies the sub-function (LANE_TRACK, PID, FUSION...)
│        Timestamp from hardware RTC or boot counter
Sensor ECU module name (CAM, RADAR_L, RADAR_F, US_CTRL, EPS...)
```

## 0.3 FMEA Scoring Guide (AIAG FMEA-4)

**Severity (S) — Effect on customer/safety:**

| S | Criteria |
|---|---|
| 10 | Hazardous without warning. Safety-critical. ASIL D. |
| 9  | Hazardous with warning. Loss of primary control. ASIL C/D. |
| 8  | Very high. System inoperable, driver must act urgently. |
| 7  | High. System degraded, primary function impaired. |
| 6  | Moderate. Some loss of comfort/convenience features. |
| 5  | Low. Partial function loss, workaround available. |
| ≤4 | Minor/None. Cosmetic or no customer impact. |

**Occurrence (O) — Likelihood of cause occurring:**

| O | Rate |
|---|---|
| 10 | Inevitable — failure almost certain |
| 8-9 | High — failures likely in certain conditions |
| 5-7 | Moderate — occasional failures |
| 3-4 | Low — few failures in vehicle lifetime |
| 1-2 | Remote — failure unlikely |

**Detection (D) — Likelihood of detecting before customer impact:**

| D | Criteria |
|---|---|
| 10 | No control — cannot detect |
| 8-9 | Very remote chance of detection |
| 5-7 | Moderate chance of detection by existing test |
| 3-4 | High chance of detection |
| 1-2 | Almost certain detection |

**RPN = S × O × D** (Range: 1–1000)
- RPN > 200: **Immediate action required**
- RPN 125–200: **High priority — plan within sprint**
- RPN 50–124: **Medium priority — plan within release**
- RPN < 50: **Low priority — track for future**

## 0.4 RCA Methodology — 5 Whys Template

```
SYMPTOM: [What was observed]

WHY 1: Why did the symptom occur?
  → [Immediate observable cause]
WHY 2: Why did that cause occur?
  → [System behavior that enabled WHY 1]
WHY 3: Why did that system behavior occur?
  → [Design/implementation decision behind WHY 2]
WHY 4: Why was that design decision made?
  → [Process/specification gap behind WHY 3]
WHY 5: Why did that process gap exist?
  → [ROOT CAUSE: systemic / organizational / requirement gap]

ROOT CAUSE CATEGORY:
  [ ] Software Bug (logic error)      [ ] Configuration Error
  [ ] Specification Gap               [ ] Interface Contract Missing
  [ ] Timing Race Condition           [ ] Calibration Error
  [ ] Hardware Limitation             [ ] Sensor Physics Limitation
```

---

# Part 1: System Architecture

## 1.1 ADAS ECU Network Topology (CAN Bus)

```
 ┌────────────────────────────────────────────────────────────────────────────┐
 │                        ADAS CAN BUS TOPOLOGY (500 kbps)                    │
 ├────────────────────────────────────────────────────────────────────────────┤
 │                                                                             │
 │   SENSORS                  ╔═══════════════╗            ACTUATORS          │
 │                            ║               ║                               │
 │  ┌──────────────┐          ║               ║         ┌──────────────────┐  │
 │  │ FRONT CAMERA │──0x3A0──►║               ║──0x2B0─►│   EPS ECU        │  │
 │  │ (ADAS_CAM)   │──0x3A1──►║               ║         │  Torque control  │  │
 │  │ Lane + TSR   │──0x3A2──►║               ║◄0x180───│  Status feedback │  │
 │  │              │──0x3A3──►║               ║         └──────────────────┘  │
 │  └──────────────┘          ║               ║                               │
 │                            ║   ADAS MAIN   ║         ┌──────────────────┐  │
 │  ┌──────────────┐          ║     ECU       ║──0x7C0─►│   BRAKE ECU      │  │
 │  │ FRONT RADAR  │──0x7B0──►║               ║──0x7C1─►│  Throttle+Brake  │  │
 │  │ (ADAS_RAD_F) │──0x7B1──►║               ║──0x8B0─►│  AEB brake req   │  │
 │  │ ACC + AEB    │──0x7B2──►║               ║         └──────────────────┘  │
 │  └──────────────┘          ║               ║                               │
 │                            ║               ║         ┌──────────────────┐  │
 │  ┌──────────────┐          ║               ║──0x3B0─►│   HMI / CLUSTER  │  │
 │  │ REAR/SIDE    │──0x5B0──►║               ║──0x4A2─►│  Warning display │  │
 │  │ RADAR (BSD)  │──0x5A0──►║               ║──0x5A1─►│  BSD indicators  │  │
 │  └──────────────┘          ║               ║──0x6A2─►│  PDC display     │  │
 │                            ║               ║         └──────────────────┘  │
 │  ┌──────────────┐          ║               ║                               │
 │  │ ULTRASONIC   │──0x6A0──►║               ║         ┌──────────────────┐  │
 │  │ PDC (8x)     │──0x6A1──►║               ║──0x3B1─►│   AUDIO ECU      │  │
 │  └──────────────┘          ║               ║         │  Chimes + alerts │  │
 │                            ║               ║         └──────────────────┘  │
 │  ┌──────────────┐          ║               ║                               │
 │  │ STEERING     │──0x100──►║               ║         ┌──────────────────┐  │
 │  │ ANGLE SENSOR │          ║               ║──0x8A0─►│   GATEWAY ECU    │  │
 │  └──────────────┘          ╚═══════════════╝         │  OBD2 / DTC log  │  │
 │                                                       └──────────────────┘  │
 │  CHASSIS CAN: 0x020 (VehicleSpeed), 0x050 (Indicator), 0x0B0 (Gear)        │
 └────────────────────────────────────────────────────────────────────────────┘

 CAN Bus Loads (nominal):
   ADAS_CAM frames:    8 msgs/10ms  → ~15% bus load
   ADAS_RAD_F frames:  4 msgs/20ms  → ~8%  bus load
   Chassis CAN:       12 msgs/10ms  → ~22% bus load
   TOTAL NOMINAL:     ~55% bus load (safe headroom)
   PEAK (all features active): ~78-85% (leaves little margin)
```

## 1.2 Feature Priority Hierarchy

When features conflict for the same actuator (EPS, Brakes, HMI), the following priority table applies. **Higher number = higher priority = overrides lower.**

```
 ACTUATOR: EPS (Electric Power Steering)
 ──────────────────────────────────────────────────────────
 Priority  Feature              Condition                  
 ──────────────────────────────────────────────────────────
    1      Driver Override      Torque > 3.5 Nm            
    2      AEB (steering evasion) TTC < 1.0s (future feature)
    3      Parking Assist       Gear=R or AutoPark active   
    4      LKA                  Normal operation            
    5      LDW                  Advisory only (no EPS use)  
 ──────────────────────────────────────────────────────────
 Rule: Lower priority feature MUST yield AND alert driver.
 Bug class: Lower priority continues silently = LKA-002 type.

 ACTUATOR: Brakes
 ──────────────────────────────────────────────────────────
 Priority  Feature              Max Decel
 ──────────────────────────────────────────────────────────
    1      Driver (pedal)       Full (10 m/s²)
    2      AEB (full brake)     10 m/s² (1.02g)
    3      AEB (pre-brake)       3 m/s² (0.31g)
    4      ACC (following)       4 m/s² (0.41g)
    5      PDC (auto park)       2 m/s² (0.20g)
 ──────────────────────────────────────────────────────────
 
 ACTUATOR: HMI / Cluster Warning Icons
 ──────────────────────────────────────────────────────────
 Priority  Alert                Color     Sound
 ──────────────────────────────────────────────────────────
    1      AEB activating       RED       3-tone urgent
    2      AEB pre-warning      AMBER     2-tone urgent  
    3      PDC Critical         RED       Continuous tone
    4      FCW                  RED       2-tone warning
    5      LKA/LDW Warning      AMBER     1-tone chime
    6      TSR speed display    WHITE     None
    7      Feature unavailable  GREY      1-tone soft
 ──────────────────────────────────────────────────────────
```

## 1.3 ADAS Feature Activation Matrix

```
 ┌─────────────┬─────────┬─────────┬────────┬──────────┬──────────┬────────┐
 │ Feature     │ Min Spd │ Max Spd │ Camera │  Radar   │  Ultrasn │ ASIL   │
 ├─────────────┼─────────┼─────────┼────────┼──────────┼──────────┼────────┤
 │ LKA         │  60kph  │ 180kph  │ MUST   │ Optional │ None     │ ASIL B │
 │ LDW         │  60kph  │ 200kph  │ MUST   │ Optional │ None     │ ASIL A │
 │ TSR         │   0kph  │ 200kph  │ MUST   │ None     │ None     │ QM     │
 │ BSD         │  15kph  │ 200kph  │ Opt    │ MUST     │ None     │ ASIL A │
 │ Parking PDC │   0kph  │  15kph  │ Opt    │ None     │ MUST     │ ASIL A │
 │ AutoPark    │   0kph  │   8kph  │ MUST   │ None     │ MUST     │ ASIL B │
 │ ACC         │  30kph  │ 200kph  │ Opt    │ MUST     │ None     │ ASIL C │
 │ FCW         │  15kph  │ 200kph  │ Opt    │ MUST     │ None     │ ASIL C │
 │ AEB         │   5kph  │ 130kph  │ Opt    │ MUST     │ None     │ ASIL D │
 └─────────────┴─────────┴─────────┴────────┴──────────┴──────────┴────────┘
```

## 1.4 Common ECU State Machine Patterns & Failure Modes

```
 Pattern A: Missing Hysteresis (→ LKA-001, AEB-003 type)
 ─────────────────────────────────────────────────────────
 INCORRECT:                        CORRECT:
 if (conf >= 70) state=ACTIVE       if (conf >= 75 && state==STANDBY) state=ACTIVE
 if (conf <  70) state=INACTIVE     if (conf <  60 && state==ACTIVE)  state=INACTIVE
                                    ↑ 15% hysteresis band prevents chattering

 Pattern B: Silent Actuator Failure (→ LKA-002 type)
 ─────────────────────────────────────────────────────
 INCORRECT:                         CORRECT:
 send_torque_request(val);           send_torque_request(val);
 // no feedback check                if (torque_applied < torque_requested * 0.5) {
                                       after 50ms, degrade_gracefully();
                                       set_hmi_status(UNAVAILABLE);
                                     }

 Pattern C: Fixed Threshold Regardless of Speed (→ AEB-001 type)
 ─────────────────────────────────────────────────────────────────
 INCORRECT:                          CORRECT:
 #define TTC_WARN_THRESHOLD 1.8f      float ttc_threshold(float v_ms) {
 if (ttc < TTC_WARN_THRESHOLD)          return REACT_TIME + v_ms / (2.0f * A_MAX);
   warn();                            }
                                      if (ttc < ttc_threshold(ego_speed)) warn();

 Pattern D: Startup Timing Race (→ AEB-003 type)
 ─────────────────────────────────────────────────
 INCORRECT:                          CORRECT:
 at T+150ms: if (!radar_ready)         Wait T+300ms OR until radar_ack received
   set_fault_dtc();                    timeout = max(sensor_init_time) + 50ms margin
   latch_fault();                      non-latch: if radar recovers → clear DTC

 Pattern E: Stale Signal Use (→ TSR-001, BSD-003 type)
 ─────────────────────────────────────────────────────
 INCORRECT:                          CORRECT:
 display(last_sign_limit);            if (sign_age > context_aware_timeout()) {
                                        prefer_map_data();
                                        flag_sign_as_stale();
                                      }
```

---

# Part 2: LKA — Lane Keeping Assist

## 2.1 Functional Architecture

### LKA State Machine

```
                    ╔═══════════════════════════════════════════╗
                    ║           LKA STATE MACHINE v2            ║
                    ╚═══════════════════════════════════════════╝

  [Ignition ON] ─────────────────────────────────────────────────────────►
                                                                          │
                                                                          ▼
                                                             ┌────────────────────┐
                                                             │      INACTIVE      │
                                                             │  (speed < 60kph)   │◄───────┐
                                                             └─────────┬──────────┘        │
                                                                       │                   │
                                           speed ≥ 60kph               │           speed < 55kph
                                           cam status = OK             │           OR ignition off
                                           hands-on wheel              │                   │
                                                                       ▼                   │
                                                             ┌────────────────────┐        │
                              ┌──────────────────────────── │      STANDBY       │ ────►  │
                              │   lane conf < 50%           │  (waiting for lane)│        │
                              │   cam blocked               └─────────┬──────────┘        │
                              │   EPS fault                           │                   │
                              │                       conf ≥ 75% for 500ms               │
                              │                       no driver override                  │
                              │                                       ▼                   │
                              │                          ┌────────────────────┐           │
                              └─────────────────────────►│     SUSPENDED      │           │
                                                         │  (transient loss)  │           │
                              ┌──────────────────────────►    hold 3s max     │           │
                              │   conf ≥ 75%             └─────────┬──────────┘           │
                              │   re-acquire                       │ conf ≥ 75%            │
                              │                                    │ OR 3s timeout         │
                              │                                    ▼                       │
                              │                          ┌────────────────────┐           │
                              └──────────────────────────┤       ACTIVE       │ ──────────┘
         driver torque > 3.5Nm ─────────────────────────┤   (correcting)     │ EPS fault / DTC set
         EPS rejects request ───────────────────────────┤  torque_req → EPS  │
         lane conf < 60% for 200ms ─────────────────────└────────────────────┘
```

### LKA Signal Timing — Normal Operation (ASCII Waveform)

```
 TIME ──────────────────────────────────────────────────────────────────►
        T=0          T=1s          T=2s          T=3s
 LaneConf_L  ─────────85──────────82──────────78──────────80──────────
 LaneConf_R  ─────────83──────────81──────────76──────────82──────────
 LatOffset   ──────── 0.0 ────── +0.1 ──────+0.25 ──────+0.15 ──────
 TorqueReq   ─────────0Nm ────── 0Nm ───── -0.6Nm ─── -0.4Nm ──────
 LKA_Status  ═══ACTIVE══════════ACTIVE══════ACTIVE═══════ACTIVE══════
             │                               │
             Nominal cruising                Drift detected → correction applied
```

### DBC Signal Definitions for LKA

```
[SIGNAL DEFINITIONS — LKA related, CAN 500kbps]

BO_ 928 ADAS_CAMERA_STATUS: 1 ADAS_CAM
  SG_ CamStatus M : 0|2@1+ (1,0) [0|3] "" ADAS_ECU
    0 = "OK"
    1 = "DEGRADED"
    2 = "BLOCKED"
    3 = "ERROR"

BO_ 929 ADAS_LANE_CONF: 8 ADAS_CAM
  SG_ LaneConf_Left  : 0|8@1+ (1,0) [0|100] "%" ADAS_ECU
  SG_ LaneConf_Right : 16|8@1+ (1,0) [0|100] "%" ADAS_ECU

BO_ 930 ADAS_LATERAL_OFFSET: 4 ADAS_CAM
  SG_ LateralOffset  : 0|16@1+ (0.01,-3.0) [-3.0|3.0] "m" ADAS_ECU
  -- Encoding: raw_value * 0.01 - 3.0 = physical value
  -- Example: 0x0312 = 786 * 0.01 - 3.0 = +4.86m (capped in practice at ±1.5m)
  -- Normal offset: byte pair 0x0012 = 18 * 0.01 - 3.0 = -2.82 → NO, offset=+0.0618m

BO_ 931 ADAS_LATERAL_VEL: 2 ADAS_CAM
  SG_ LateralVelocity: 0|16@1+ (0.01,-10.0) [-10.0|10.0] "m/s" ADAS_ECU

BO_ 688 LKA_TORQUE_REQUEST: 4 ADAS_ECU
  SG_ LKA_TorqueReq  : 0|16@1+ (0.01,-50.0) [-5.0|5.0] "Nm" EPS_ECU
  SG_ LKA_Active     : 16|1@1+ (1,0) [0|1] "" EPS_ECU
  -- Positive = steer right, Negative = steer left
  -- Example: 0xFFD8 0x01 = (-40 * 0.01 - 50.0)... 
  -- Actual encoding: 0x0200 = 512 * 0.01 - 50 = -44.88 → simplified for examples

BO_ 384 EPS_STATUS: 2 EPS_ECU
  SG_ EPS_Status     : 0|2@1+ (1,0) [0|3] "" ADAS_ECU
    0 = "READY"
    1 = "BUSY"
    2 = "FAULT"
    3 = "OVERRIDE"
  SG_ EPS_TorqueApplied: 2|14@1+ (0.01,-50.0) [-5.0|5.0] "Nm" ADAS_ECU

BO_ 256 STEERING_TORQUE: 4 STEERING_SENSOR
  SG_ SteeringTorque : 0|16@1+ (0.01,-50.0) [-10.0|10.0] "Nm" ADAS_ECU
```

---

## 2.2 LKA-001: Threshold Chattering in Sunlight — Hysteresis Missing

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : LKA-001                                                      ║
║ Title     : LKA activates/deactivates cyclically — no hysteresis         ║
║ Severity  : HIGH                  ASIL Impact: ASIL B (§4.3.2)          ║
║ Standards : ISO 11270:2014 §6.3.2 — State transition requirements       ║
║ NCAP      : Yes — NCAP LKA lane-centering comfort test                   ║
║ FuSa      : Yes — unintended steering torque cycling (safety concern)    ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Setup & Pre-conditions

| Parameter | Value |
|---|---|
| Vehicle speed | 90 km/h |
| Road type | Straight motorway, white solid lane markings |
| Weather | Clear, low morning sun (sun angle 20–30° above horizon) |
| Camera FW | v2.4.7 |
| ADAS ECU SW | v5.1.0 |
| Reproducibility | 8/10 runs in direct morning sunlight (07:30–09:30) |
| Test Environment | Vehicle (also reproducible on HIL with camera sensor replay) |

### Symptom

Driver complaint: "LKA icon on cluster flickers between active (green) and warning (amber) at roughly 10 Hz. Steering wheel oscillates with small jerks synchronised to the icon. Happens only when driving toward the sun."

### Complete Log Triptych

**CAN Log (Vector CANalyzer .asc):**

```
-- ADAS Feature Log
-- CAN channel 2 (ADAS CAN), 500 kbps
-- Date 2026-05-06 09:14:22
-- Signal database: ADAS_v5.1.dbc

   0.000  ADAS_ECU    LKA_Status = ACTIVE
   0.012  0x3A1  Rx  d 8  48 45 48 45 00 00 00 00
                          ^^ ^^    -- LaneConf_Left=0x48=72%, LaneConf_Right=0x48=72%
   0.024  0x3A2  Rx  d 4  00 12 00 00
                          -- LateralOffset raw=0x0012=18 → 18*0.01-3.0+3.18=+0.18m (right)
   0.036  0x2B0  Tx  d 4  FF D8 00 01
                          -- LKA_TorqueReq: raw=0xFFD8 → signed=-40 → -40*0.01=-0.40Nm (left)
                          -- LKA_Active=0x01 (active)
   0.048  0x100  Rx  d 4  00 08 00 00
                          -- SteeringTorque=+0.08Nm (driver marginal hands-on)
   0.060  0x3A1  Rx  d 8  48 45 48 45 00 00 00 00   -- Conf=72%/72% STABLE
   0.072  0x3A1  Rx  d 8  3F 45 44 45 00 00 00 00   -- Conf drops: 63%/68%  ⚠
   0.084  0x3A1  Rx  d 8  24 45 29 45 00 00 00 00   -- Conf DROPS: 36%/41%  ← BELOW 70% ✗
   0.096  0x2B0  Tx  d 4  00 00 00 00               -- LKA_TorqueReq=0Nm (DEACTIVATED)
   0.096  ADAS_ECU    LKA_Status = SUSPENDED (LaneConf < deact_threshold=70%)
   0.108  0x3A1  Rx  d 8  47 45 47 45 00 00 00 00   -- Conf recovers: 71%/71%  ← ABOVE 70% ✓
   0.120  0x2B0  Tx  d 4  FF D8 00 01               -- LKA_TorqueReq=-0.40Nm (RE-ACTIVATED!)
   0.120  ADAS_ECU    LKA_Status = ACTIVE            ← IMMEDIATE re-activation!
   0.132  0x3A1  Rx  d 8  22 45 24 45 00 00 00 00   -- Conf drops again: 34%/36%  ← BELOW ✗
   0.144  0x2B0  Tx  d 4  00 00 00 00               -- Deactivated again
   0.144  ADAS_ECU    LKA_Status = SUSPENDED
   0.156  0x3A1  Rx  d 8  47 45 48 45 00 00 00 00   -- Conf 71%/72% → RE-ACTIVATE
   0.168  ADAS_ECU    LKA_Status = ACTIVE
   -- [Pattern repeats at ~96ms interval = ~10.4 Hz chatter rate]
```

**ECU System Log** (`/var/log/adas/lka.log`):

```
[2026-05-06 09:14:22.001] [LKA] [INFO ] State=ACTIVE LatOff=+0.18m ConfL=72 ConfR=72 TorqReq=-0.40Nm
[2026-05-06 09:14:22.073] [LKA] [INFO ] State=ACTIVE LatOff=+0.16m ConfL=63 ConfR=68 TorqReq=-0.32Nm
[2026-05-06 09:14:22.085] [LKA] [WARN ] ConfL=36 ConfR=41 BELOW deact_threshold=70. StateChg: ACTIVE→SUSPENDED
[2026-05-06 09:14:22.097] [LKA] [INFO ] State=SUSPENDED. TorqReq=0Nm. HMI: AMBER icon.
[2026-05-06 09:14:22.109] [LKA] [INFO ] ConfL=71 ConfR=71 ABOVE act_threshold=70. StateChg: SUSPENDED→ACTIVE
[2026-05-06 09:14:22.110] [LKA] [INFO ] State=ACTIVE. TorqReq=-0.40Nm. HMI: GREEN icon.
[2026-05-06 09:14:22.134] [LKA] [WARN ] ConfL=34 ConfR=36 BELOW deact_threshold=70. StateChg: ACTIVE→SUSPENDED
[2026-05-06 09:14:22.146] [LKA] [INFO ] State=SUSPENDED. TorqReq=0Nm.
[2026-05-06 09:14:22.158] [LKA] [INFO ] ConfL=71 ConfR=71. StateChg: SUSPENDED→ACTIVE
[2026-05-06 09:14:22.159] [LKA] [INFO ] State=ACTIVE.
-- [12 state transitions in next 1.2 seconds]
[2026-05-06 09:14:22.500] [LKA] [CRIT ] Chatter_count=12 in 500ms. SAFETY_LOG: excessive state cycling.
```

**Serial/UART Log** (Camera ECU, 115200 baud, `/dev/ttyUSB0`):

```
[CAM][09:14:22.068] LANE_TRACK: L_conf=72 R_conf=72 qual=STABLE frames_since_loss=847
[CAM][09:14:22.080] LANE_PROC : exposure_mode=AUTO gain_dB=+4.2 sunflare_detect=FALSE
[CAM][09:14:22.084] LANE_PROC : sunflare_detect=TRUE! AEC_trigger: gain +18dB in 1 frame
[CAM][09:14:22.085] LANE_TRACK: L_conf=36 R_conf=41 qual=DEGRADED reason=GLARE_SATURATION
[CAM][09:14:22.085] AEC_ADAPT : new_gain=+22.2dB target_ev=-1.2 settling_frames=3
[CAM][09:14:22.097] LANE_TRACK: L_conf=71 R_conf=71 qual=RECOVERING (AEC settling frame 1/3)
[CAM][09:14:22.109] LANE_PROC : sunflare_detect=TRUE! AEC_trigger: gain +18dB in 1 frame
[CAM][09:14:22.110] LANE_TRACK: L_conf=34 R_conf=36 qual=DEGRADED reason=GLARE_SATURATION
[CAM][09:14:22.122] LANE_TRACK: L_conf=72 R_conf=72 qual=RECOVERING
[CAM][09:14:22.134] LANE_PROC : sunflare_detect=TRUE! [cycle continues]
```

### Annotated Analysis

```
OBSERVATION 1 — CAN trace, t=0.072–0.084:
  LaneConf drops from 72% to 36% in TWO consecutive CAN frames (12ms each).
  A physical 36-point confidence drop in 24ms is impossible for real lane geometry
  change. Confirms this is sensor artifact, not actual lane loss.
  → Source: Camera AEC step-change causing image noise spike.

OBSERVATION 2 — Camera serial, t=09:14:22.084:
  "sunflare_detect=TRUE! AEC_trigger: gain +18dB in 1 frame"
  The Auto Exposure Control (AEC) responds to sunflare by increasing gain +18dB
  IN A SINGLE FRAME. At +18dB gain, image sensor noise floor rises significantly.
  The lane edge detector's SNR falls below threshold → confidence collapses.
  → This is a known camera AEC tuning defect (CAM-JIRA-2241).

OBSERVATION 3 — The core software bug (System log):
  act_threshold   = 70%
  deact_threshold = 70%   ← SAME VALUE! No hysteresis!
  
  When conf oscillates between 68% and 72% (AEC settling):
    68% < 70% → SUSPEND
    72% > 70% → ACTIVATE
    68% < 70% → SUSPEND  [repeat at 10Hz]

OBSERVATION 4 — Effect on actuator (CAN trace):
  TorqueReq toggles: 0 → -0.40Nm → 0 → -0.40Nm every 96ms.
  This jitter is transmitted directly to EPS motor → driver feels micro-jerks.
  Each state change also triggers HMI icon flash → visual distraction.

OBSERVATION 5 — Chatter frequency calculation:
  Camera cycle = 12ms (83 Hz camera)
  Glare/recover cycle observed = 2–3 camera frames = 24–36ms
  LKA state check = every 12ms
  Chatter rate = 1 / 96ms ≈ 10.4 Hz ← matches driver "flickering" perception
```

### Root Cause Chain (5 Whys)

```
WHY 1: LKA activates and deactivates repeatedly at ~10Hz.
  → Because the LKA state machine transitions between ACTIVE and SUSPENDED
    whenever LaneConf crosses the 70% threshold.

WHY 2: Why does LaneConf oscillate through the 70% threshold?
  → Because the camera AEC applies a +18dB gain step when detecting sunflare,
    causing a lane confidence collapse for 1-2 frames, then partial recovery.

WHY 3: Why does a single +18dB AEC step cause such a large confidence drop?
  → Because the lane edge detector is tuned for nominal gain levels (±6dB).
    At +18dB step-change, noise floor spikes above the Canny edge threshold,
    erasing lane markings from the processed image for 2-3 frames.

WHY 4: Why does LKA not tolerate 2-3 frames of low confidence?
  → Because there is NO HYSTERESIS in the LKA state machine.
    Activation threshold = Deactivation threshold = 70%.
    Any confidence value ≥70% re-activates; any value <70% deactivates.

WHY 5: Why was hysteresis not specified in the implementation?
  → The SRS (LKA-SRS-§4.2.1) specifies minimum confidence threshold = 70%
    but does NOT specify separate activation vs deactivation values.
    The SRS gap allowed the implementor to use a single threshold.

ROOT CAUSE: SRS specification gap + missing hysteresis in state machine.
CATEGORY  : Specification Gap + Software Implementation Error
```

### Code-Level Analysis

**Location:** `src/lka_state_machine.c`, function `lka_eval_state()`, line ~142

```c
/* ===== BUGGY CODE (v5.1.0) ===== */
#define LKA_CONF_THRESHOLD  70u   /* single threshold, no hysteresis */

static void lka_eval_state(LkaContext_t *ctx) {
    uint8_t conf = min(ctx->lane_conf_left, ctx->lane_conf_right);

    if (ctx->state == LKA_STATE_ACTIVE) {
        if (conf < LKA_CONF_THRESHOLD) {          /* BUG: same threshold as activation */
            lka_set_state(ctx, LKA_STATE_SUSPENDED);
            lka_set_torque(ctx, 0.0f);
        }
    }
    else if (ctx->state == LKA_STATE_SUSPENDED) {
        if (conf >= LKA_CONF_THRESHOLD) {         /* BUG: immediately re-activates */
            lka_set_state(ctx, LKA_STATE_ACTIVE);
        }
    }
}
```

```c
/* ===== FIXED CODE (v5.2.0) ===== */
#define LKA_CONF_ACT_THRESHOLD    75u   /* higher bar to activate */
#define LKA_CONF_DEACT_THRESHOLD  60u   /* lower bar to deactivate (15% hysteresis) */
#define LKA_CONF_ACT_HOLD_MS     500u   /* must hold for 500ms before activating */
#define LKA_CONF_DEACT_HOLD_MS   200u   /* must hold low for 200ms before deactivating */

static void lka_eval_state(LkaContext_t *ctx) {
    uint8_t conf = min(ctx->lane_conf_left, ctx->lane_conf_right);
    uint32_t now_ms = get_sys_time_ms();

    if (ctx->state == LKA_STATE_ACTIVE) {
        if (conf < LKA_CONF_DEACT_THRESHOLD) {
            if (ctx->low_conf_start_ms == 0u) {
                ctx->low_conf_start_ms = now_ms;  /* start deact timer */
            } else if ((now_ms - ctx->low_conf_start_ms) >= LKA_CONF_DEACT_HOLD_MS) {
                lka_set_state(ctx, LKA_STATE_SUSPENDED);
                lka_set_torque(ctx, 0.0f);
                ctx->low_conf_start_ms = 0u;
            }
        } else {
            ctx->low_conf_start_ms = 0u;  /* reset timer if conf recovers */
        }
    }
    else if (ctx->state == LKA_STATE_SUSPENDED || ctx->state == LKA_STATE_STANDBY) {
        if (conf >= LKA_CONF_ACT_THRESHOLD) {
            if (ctx->high_conf_start_ms == 0u) {
                ctx->high_conf_start_ms = now_ms;  /* start activation timer */
            } else if ((now_ms - ctx->high_conf_start_ms) >= LKA_CONF_ACT_HOLD_MS) {
                lka_set_state(ctx, LKA_STATE_ACTIVE);
                ctx->high_conf_start_ms = 0u;
            }
        } else {
            ctx->high_conf_start_ms = 0u;
        }
    }
}
```

**Unified Diff:**
```diff
--- a/src/lka_state_machine.c  (v5.1.0)
+++ b/src/lka_state_machine.c  (v5.2.0)
@@ -138,12 +138,24 @@
-#define LKA_CONF_THRESHOLD  70u
+#define LKA_CONF_ACT_THRESHOLD    75u
+#define LKA_CONF_DEACT_THRESHOLD  60u
+#define LKA_CONF_ACT_HOLD_MS     500u
+#define LKA_CONF_DEACT_HOLD_MS   200u

 static void lka_eval_state(LkaContext_t *ctx) {
     uint8_t conf = min(ctx->lane_conf_left, ctx->lane_conf_right);
+    uint32_t now_ms = get_sys_time_ms();

     if (ctx->state == LKA_STATE_ACTIVE) {
-        if (conf < LKA_CONF_THRESHOLD) {
-            lka_set_state(ctx, LKA_STATE_SUSPENDED);
-            lka_set_torque(ctx, 0.0f);
+        if (conf < LKA_CONF_DEACT_THRESHOLD) {
+            if (ctx->low_conf_start_ms == 0u) {
+                ctx->low_conf_start_ms = now_ms;
+            } else if ((now_ms - ctx->low_conf_start_ms) >= LKA_CONF_DEACT_HOLD_MS) {
+                lka_set_state(ctx, LKA_STATE_SUSPENDED);
+                lka_set_torque(ctx, 0.0f);
+                ctx->low_conf_start_ms = 0u;
+            }
+        } else {
+            ctx->low_conf_start_ms = 0u;
         }
     }
```

### FMEA Analysis

| Item | Failure Mode | Effect on Customer | S | Root Cause | O | Current Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| LKA Conf threshold | Single threshold (no hysteresis) → state chattering | Steering micro-jerk at 10Hz, HMI flicker, driver distraction | 8 | SRS missing hysteresis spec | 6 | Manual test (but only clear conditions) | 7 | **336** |

**RPN = 336 → IMMEDIATE ACTION REQUIRED**

Reduction after fix: S=8, O=2, D=3 → RPN = **48** (acceptable)

### Formal Defect Report

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT REPORT: LKA-001                                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║ Title     : LKA chatters ON/OFF in sunlight (no confidence hysteresis)   ║
║ Priority  : P1 — HIGH                                                    ║
║ Severity  : HIGH (safety-related unintended steering torque)             ║
║ Component : src/lka_state_machine.c — lka_eval_state()                  ║
║ SW Build  : ADAS-ECU-5.1.0                                               ║
║ FuSa      : Unintended LKA intervention — requires ASIL B analysis       ║
╠══════════════════════════════════════════════════════════════════════════╣
║ DESCRIPTION:                                                             ║
║ When driving toward low-angle morning sun, camera AEC overcompensates   ║
║ causing lane confidence to oscillate through a single 70% threshold.    ║
║ LKA chatters ACTIVE↔SUSPENDED at ~10Hz, causing steering jitter.        ║
╠══════════════════════════════════════════════════════════════════════════╣
║ REPRODUCTION:                                                            ║
║ 1. Drive at 80–100 km/h on marked motorway                              ║
║ 2. Orient toward sun at elevation 20–35° (7:30–9:30 AM or 3–5 PM)      ║
║ 3. Enable LKA — observe within 2 minutes                                ║
║ Rate: 8/10 runs reproduce issue                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║ EVIDENCE:                                                                ║
║ CAN: LKA_TorqueReq toggles 0↔-0.40Nm at 96ms intervals                 ║
║ SYS: 12 state transitions in 500ms — CRIT log generated                 ║
║ CAM: sunflare_detect=TRUE + AEC +18dB at each confidence collapse        ║
╠══════════════════════════════════════════════════════════════════════════╣
║ ROOT CAUSE: act_threshold == deact_threshold == 70% (no hysteresis)     ║
╠══════════════════════════════════════════════════════════════════════════╣
║ FIX:                                                                     ║
║ SHORT: Act≥75% (500ms hold), Deact<60% (200ms hold). See code diff.     ║
║ LONG : Camera AEC — tune gain transition over 5 frames, not 1 frame.    ║
║        Camera JIRA: CAM-2241 (assigned to camera supplier).             ║
╠══════════════════════════════════════════════════════════════════════════╣
║ SRS UPDATE REQUIRED:                                                     ║
║ LKA-SRS-§4.2.1: Add: "Activation threshold shall be ≥ deactivation      ║
║ threshold + 15%. Activation requires threshold hold for ≥ 500ms."       ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Test Cases for LKA-001 Fix Verification

**TC-LKA-001-01: Hysteresis Band Verification**
```
Pre-conditions : LKA enabled, speed=90kph, straight road
Stimuli        : Inject camera confidence stepping: 80%→65%→72%→65%→80%
Expected       : LKA does NOT suspend at 65% alone; suspends only if 65%
                 is held for ≥ 200ms. Does not re-activate until ≥75% held ≥500ms.
Pass criterion : Zero state transitions when conf oscillates between 65-72%
Automation     : HIL — camera signal injection via CANoe
```

**TC-LKA-001-02: Morning Sun Reproducibility**
```
Pre-conditions : Same as defect reproduction
Expected       : After fix, zero chatter events in 30-minute sunrise drive
Pass criterion : Chatter_count = 0 in syslog; TorqueReq transitions < 2/minute
Automation     : Vehicle test (regression, not SIL-automatable)
```

**TC-LKA-001-03: Deactivation Timing**
```
Pre-conditions : LKA active, conf=80%
Stimuli        : Inject conf=55% (below deact threshold)
Expected       : LKA suspends after exactly 200ms ± 20ms
Pass criterion : State change timestamp = conf_drop_time + 200ms ± 20ms
Automation     : SIL + HIL
```

**TC-LKA-001-04: No False Keep-Alive**
```
Pre-conditions : LKA active, conf=80%
Stimuli        : Inject sustained conf=55% for 1000ms
Expected       : LKA suspends at 200ms and STAYS suspended
Pass criterion : No re-activation during 1000ms low-conf period
Automation     : SIL
```

**TC-LKA-001-05: Regression — Normal Activation**
```
Pre-conditions : LKA in STANDBY, conf=78%, straight road
Expected       : LKA activates after exactly 500ms hold above 75%
Pass criterion : State change at T+500ms ± 50ms
Automation     : SIL + HIL
```

---

## 2.3 LKA-002: Silent EPS Rejection with False "ACTIVE" HMI State

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : LKA-002                                                      ║
║ Title     : LKA HMI shows ACTIVE while EPS silently rejects all requests ║
║ Severity  : CRITICAL            ASIL Impact: ASIL B §4.4 — False state  ║
║ Standards : ISO 11270:2014 §7.1 — HMI shall correctly reflect state     ║
║             ISO 26262-6 §8.4.2 — No misleading information to driver    ║
║ NCAP      : Potential LKA effectiveness test failure                     ║
║ FuSa      : SAFETY GOAL VIOLATION — misleading safety feature indication ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Setup & Pre-conditions

| Parameter | Value |
|---|---|
| Vehicle speed | 80 km/h on marked lane |
| PDC Status | ACTIVE (parking assist was briefly triggered and is still executing) |
| EPS Priority | PARKING_ASSIST > LKA (correct per EPS arbitration spec) |
| Reproducibility | 10/10 when PDC active and driver enables LKA simultaneously |

### Symptom

LKA green icon shown on cluster. No steering corrections happen even when vehicle visibly drifts 0.4–0.8m from lane centre. Driver reports car "doesn't listen to LKA." Discovered during validation — field incident risk: driver may trust LKA while it provides zero assistance.

### Complete Log Triptych

**CAN Log:**

```
   0.000  0x3A0  Rx  d 1  00                    -- CamStatus = OK
   0.002  0x3A1  Rx  d 8  50 45 52 45 00 00 00 00  -- ConfL=80%, ConfR=82%
   0.004  0x3A2  Rx  d 4  00 2A 00 00            -- LateralOffset = +0.42m RIGHT
   0.006  0x2B0  Tx  d 4  FF B0 00 01            -- LKA_TorqueReq = -1.25Nm (strong left)
   0.006  0x180  Rx  d 2  01 00                  -- EPS_Status = BUSY (1) ← !!
   0.006  0x180  Rx  d 2  00 00                  -- EPS_TorqueApplied = 0.00Nm ← nothing applied
   0.008  0x2B0  Tx  d 4  FF B0 00 01            -- LKA retries -1.25Nm
   0.008  0x180  Rx  d 2  01 00                  -- EPS still BUSY
   0.010  0x2B0  Tx  d 4  FF B0 00 01            -- LKA retries (attempt 3)
   0.012  0x2B0  Tx  d 4  FF B0 00 01            -- attempt 4
   0.014  0x2B0  Tx  d 4  FF B0 00 01            -- attempt 5
   0.014  0x2B0  Tx  d 4  00 00 00 01            -- TORQUE DROPPED (0Nm), LKA_Active still=1
   0.014  ADAS_ECU  [internal] retry_count=5 exceeded. TorqueRequest dropped.
   -- NOTE: LKA_Active bit remains 1 = LKA still reporting ACTIVE to HMI!
   0.200  0x3A2  Rx  d 4  00 58 00 00            -- LateralOffset = +0.88m (vehicle drifting!)
   0.400  0x3A2  Rx  d 4  00 70 00 00            -- LateralOffset = +1.12m (near lane boundary)
   0.620  [HMI]: LKA icon = GREEN (ACTIVE) ← driver sees this, trusts LKA
   0.620  [ACTUAL]: TorqueApplied = 0.00Nm ← reality
   0.700  DTC SET: C1A42 — EPS_NotResponding_LKA_Request
   0.700  ADAS_ECU  LKA_Status = FAULT (only set 700ms after problem started!)
```

**ECU System Log:**

```
[2026-05-06 11:32:10.006] [LKA    ] [INFO ] TorqReq=-1.25Nm LatOff=+0.42m State=ACTIVE
[2026-05-06 11:32:10.006] [EPS_IF ] [WARN ] EPS_Status=BUSY. Queuing request.
[2026-05-06 11:32:10.008] [EPS_IF ] [WARN ] EPS_Status=BUSY. Retry 2/5.
[2026-05-06 11:32:10.010] [EPS_IF ] [WARN ] EPS_Status=BUSY. Retry 3/5.
[2026-05-06 11:32:10.012] [EPS_IF ] [WARN ] EPS_Status=BUSY. Retry 4/5.
[2026-05-06 11:32:10.014] [EPS_IF ] [ERROR] EPS_Status=BUSY. Retry 5/5 FAILED.
[2026-05-06 11:32:10.014] [EPS_IF ] [ERROR] Dropping torque request. TorqReq→0.
[2026-05-06 11:32:10.014] [LKA    ] [ERROR] Torque request dropped. Applying 0Nm.
[2026-05-06 11:32:10.014] [LKA    ] [INFO ] State remains=ACTIVE (NO STATE CHANGE!)  ← BUG
[2026-05-06 11:32:10.014] [HMI_IF ] [INFO ] LKA_HMI_Status=ACTIVE (sending to cluster)  ← BUG
[2026-05-06 11:32:10.200] [LKA    ] [WARN ] LatOff=+0.88m but TorqApplied=0. Gap growing.
[2026-05-06 11:32:10.700] [DTC    ] [ERROR] C1A42 set: EPS_not_responding. LKA→FAULT (at 700ms)
[2026-05-06 11:32:10.700] [HMI_IF ] [WARN ] LKA_HMI_Status=FAULT. Amber icon. (late!)
```

**Serial Log (EPS ECU UART, 115200 baud):**

```
[EPS][11:32:09.800] GRANT: PARKING_ASSIST request accepted. Mode=PARKING. Priority=HIGH.
[EPS][11:32:09.805] STATUS: mode=PARKING_ASSIST torq_req=+1.80Nm remaining_est=12s
[EPS][11:32:10.006] RECV: LKA_torque_request=-1.25Nm from 0x2B0
[EPS][11:32:10.006] ARBITRATE: Current=PARKING_ASSIST(prio=3) > LKA(prio=4). REJECT LKA.
[EPS][11:32:10.006] STATUS: BUSY=TRUE mode=PARKING_ASSIST. LKA_rejected=TRUE.
[EPS][11:32:10.006] NOTE: No LKA_rejection signal sent to ADAS ECU (not in ICD v4.2)
[EPS][11:32:10.008] RECV: LKA_torque_request=-1.25Nm (retry). Still PARKING mode. REJECT.
[EPS][11:32:10.010] RECV: LKA retry 3. REJECT.
[EPS][11:32:10.012] RECV: LKA retry 4. REJECT.
[EPS][11:32:10.014] RECV: LKA retry 5. REJECT. LKA request dropped by originator.
[EPS][11:32:10.602] PDC maneuver complete. mode→READY.
[EPS][11:32:10.602] NOTE: ADAS ECU still not informed of completion. Status polling only.
```

### Root Cause Chain (5 Whys)

```
WHY 1: Driver sees "LKA ACTIVE" but car does not steer.
  → LKA state remains ACTIVE even though TorqueApplied=0Nm.

WHY 2: Why does LKA state remain ACTIVE with zero torque applied?
  → After 5 failed EPS retries, LKA drops the torque request BUT does not
    transition state. The SRS has no requirement for this failure mode handling.

WHY 3: Why are 5 EPS retries the maximum, with no recovery path?
  → The EPS interface module was designed for transient EPS unavailability
    (e.g., brief ESP intervention). PARKING_ASSIST for 12 seconds exceeds the
    retry design assumption. No "long-term EPS busy" handler exists.

WHY 4: Why is there no LKA_Rejection feedback signal from EPS?
  → The EPS-ADAS Interface Control Document (ICD v4.2) does not include a
    "rejection reason" signal. EPS only provides EPS_Status (BUSY/READY/FAULT).
    ADAS ECU cannot distinguish "busy for 12ms" from "rejected for 12 seconds."

WHY 5: Why was the EPS ICD not updated to include rejection feedback?
  → The LKA-EPS integration test scenarios did not include simultaneous
    PARKING_ASSIST + LKA operation as a test case. The interface contract gap
    was not discovered until vehicle integration testing.

ROOT CAUSE: Missing interface contract — EPS provides no rejection reason
signal. ADAS ECU has no graceful degradation path for extended EPS unavailability.
CATEGORY  : Interface Contract Missing + Software Implementation Gap
SAFETY    : ASIL B safety goal violation (ISO 26262-4 §7.4.8)
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* src/lka_eps_interface.c */
static void lka_eps_send_torque(LkaContext_t *ctx, float torque_nm) {
    for (int retry = 0; retry < MAX_EPS_RETRIES; retry++) {     /* MAX=5 */
        if (eps_send_torque_request(torque_nm) == EPS_OK) {
            return;   /* sent successfully */
        }
        wait_ms(2);
    }
    /* BUG 1: silently drops request, does not notify LKA state machine */
    /* BUG 2: ctx->state and HMI status NOT updated — remains ACTIVE     */
    log_error("EPS torque request dropped after %d retries", MAX_EPS_RETRIES);
}
```

```c
/* ===== FIXED CODE ===== */
/* src/lka_eps_interface.c */
#define EPS_BUSY_DEGRADE_MS  50u    /* if EPS busy >50ms, degrade LKA */

static void lka_eps_send_torque(LkaContext_t *ctx, float torque_nm) {
    static uint32_t eps_busy_since_ms = 0u;
    uint32_t now_ms = get_sys_time_ms();

    EpsStatus_t eps_status = eps_get_status();

    if (eps_status == EPS_READY) {
        eps_busy_since_ms = 0u;
        eps_send_torque_request(torque_nm);
        lka_update_torque_applied_feedback(ctx);   /* read back EPS_TorqueApplied */

    } else if (eps_status == EPS_BUSY) {
        if (eps_busy_since_ms == 0u) {
            eps_busy_since_ms = now_ms;
        }
        if ((now_ms - eps_busy_since_ms) >= EPS_BUSY_DEGRADE_MS) {
            /* EPS unavailable too long — degrade gracefully */
            lka_set_state(ctx, LKA_STATE_UNAVAILABLE);  /* NEW state */
            lka_set_hmi_status(HMI_LKA_UNAVAILABLE);    /* amber icon + reason */
            lka_set_torque(ctx, 0.0f);
            log_warn("[LKA] EPS busy >%ums. Transitioning to UNAVAILABLE. HMI updated.",
                     EPS_BUSY_DEGRADE_MS);
        }
    } else { /* EPS_FAULT */
        lka_set_state(ctx, LKA_STATE_FAULT);
        set_dtc(DTC_C1A42_EPS_NOT_RESPONDING);
    }
}
```

**Additionally — New CAN signal required in EPS ICD:**
```
BO_ 385 EPS_LKA_FEEDBACK: 2 EPS_ECU      /* NEW frame v4.3 */
  SG_ EPS_LKA_Rejection_Reason : 0|4@1+ (1,0) [0|15] "" ADAS_ECU
    0 = "NONE"
    1 = "PRIORITY_CONFLICT_PARKING"
    2 = "PRIORITY_CONFLICT_ESP"
    3 = "HARDWARE_FAULT"
    4 = "THERMAL_LIMIT"
  SG_ EPS_LKA_TorqueGranted : 4|1@1+ (1,0) [0|1] "" ADAS_ECU
```

### FMEA Analysis

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| LKA-EPS interface | Torque rejected silently, HMI shows ACTIVE | Driver trusts LKA, no correction, lane departure | **9** | No rejection signal in EPS ICD | 5 | Integration test (not covering this combo) | 8 | **360** |

**RPN = 360 → CRITICAL — Block release**

---

## 2.4 LKA-003: Steering Overshoot — PID Clamp Sign Inversion Bug

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : LKA-003                                                      ║
║ Title     : LKA overshoot to opposite lane — PID output clamp inverts    ║
║ Severity  : CRITICAL            ASIL: ASIL B — unintended max torque     ║
║ Standards : ISO 11270:2014 §5.2 — Lateral control performance           ║
║ FuSa      : Maximum torque applied in wrong direction                    ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### PID Controller Theory & Mathematics

The LKA lateral offset controller uses a discrete PID:

```
Torque(k) = Kp × e(k) + Ki × Ts × Σe(j) + Kd/Ts × [e(k) - e(k-1)]

Where:
  e(k)  = 0 - lateral_offset(k)   [error = target - actual, target=0=lane centre]
  Ts    = 12ms                     [sample period = camera frame rate]
  Kp    = proportional gain
  Ki    = integral gain
  Kd    = derivative gain

Clamping: output = clamp(Torque(k), -TORQUE_MAX, +TORQUE_MAX)
  TORQUE_MAX = 2.50 Nm
  Positive torque = steer RIGHT
  Negative torque = steer LEFT (toward lane centre when drifting right)
```

**Current Gains Analysis:**
```
Kp = 10.4,  Ki = 0.0,  Kd = 0.0  (pure P controller)

PROBLEM 1 — Saturation:
  At offset = 0.24m:  P_term = 10.4 × 0.24 = 2.50Nm → AT saturation limit
  Any offset ≥ 0.24m immediately saturates output.
  The controller cannot apply proportional response for offsets > 0.24m.

PROBLEM 2 — No Damping:
  Kd = 0 → no derivative term → no damping of oscillation.
  Without damping, a P controller on a second-order system oscillates.
  
PROBLEM 3 — Clamp Bug (THE CRITICAL BUG):
  When vehicle overshoots lane centre (offset goes negative):
    e.g., offset = -0.12m → P_term = 10.4 × 0.12 = +1.25Nm (correct, steer right)
  But clamp function has sign inversion bug...
```

### Complete Log Triptych

**CAN Log:**

```
   0.000  0x3A2  Rx  d 4  00 18 00 00    -- LateralOffset = +0.24m (drifting RIGHT)
   0.000  0x100  Rx  d 4  00 05 00 00    -- SteeringTorque = +0.05Nm (passive driver)
   0.012  0x2B0  Tx  d 4  FF 60 00 01    -- LKA_TorqueReq = -2.50Nm (MAX LEFT steer)
   0.024  0x3A2  Rx  d 4  00 0C 00 00    -- Offset reducing: +0.12m ← correction working
   0.036  0x2B0  Tx  d 4  FF 60 00 01    -- Still -2.50Nm (saturated)
   0.048  0x3A2  Rx  d 4  FF F4 00 00    -- Offset = -0.12m! ← OVERSHOT to LEFT!
   0.060  0x2B0  Tx  d 4  FF 60 00 01    -- TorqueReq STILL -2.50Nm! Should be +1.25Nm!
                                          -- Vehicle steering FURTHER LEFT when should go right!
   0.072  0x3A2  Rx  d 4  FF D4 00 00    -- Offset = -0.44m ← approaching LEFT boundary!
   0.072  0x100  Rx  d 4  00 38 00 00    -- SteeringTorque=+0.56Nm (driver overcorrecting right)
   0.084  0x100  Rx  d 4  00 64 00 00    -- SteeringTorque=+1.00Nm (driver fighting hard)
   0.096  0x100  Rx  d 4  00 B4 00 00    -- SteeringTorque=+1.80Nm (near override threshold!)
   0.108  0x100  Rx  d 4  01 1C 00 00    -- SteeringTorque=+2.84Nm
   0.120  ADAS_ECU  LKA_Status=SUSPENDED (DriverOverride torque=2.84Nm < 3.5Nm threshold)
                    -- NOTE: override at 3.5Nm is also too high — see secondary finding
```

**ECU System Log:**

```
[2026-05-06 13:05:01.000] [PID] Kp=10.4 Ki=0.0 Kd=0.0 error=+0.24 P=+2.50(clamped) output=-2.50Nm
[2026-05-06 13:05:01.012] [PID] error=+0.12 P=+1.25 output=-2.50Nm (STILL clamped? P<max!)
[2026-05-06 13:05:01.012] [PID_CLAMP] raw=+1.25 limit=2.50 CLAMP_LOGIC_BUG output=-2.50Nm ← BUG
[2026-05-06 13:05:01.024] [PID] error=-0.12 P=+1.25 output=-2.50Nm WRONG DIRECTION
[2026-05-06 13:05:01.036] [PID] error=-0.44 P=+4.58 output=-2.50Nm
[2026-05-06 13:05:01.036] [LKA] LatOff=-0.44m approaching LEFT boundary (limit=-0.60m)
[2026-05-06 13:05:01.048] [LKA] DriverOverride=TRUE torq=+2.84Nm. Suspending.
```

**Serial Log (PID debug UART):**

```
[PID][13:05:01.000] CTRL: target=0.000m actual=+0.240m error=+0.240 P_out=+2.496
[PID][13:05:01.000] CLAMP: raw_out=+2.496 limit=2.50 → no_clamp expected → output=+2.496Nm?
[PID][13:05:01.000] CLAMP_BUG: entered wrong branch: (raw_out > limit)? NO but applying -limit!
[PID][13:05:01.000] CLAMP_ACTUAL: output=-2.496Nm [SIGN INVERTED by bug]
[PID][13:05:01.012] CTRL: error=+0.120 P_out=+1.248
[PID][13:05:01.012] CLAMP_BUG: (1.248 > -2.50)? YES! → applying -(2.50)=-2.50 ← WRONG
[PID][13:05:01.024] CTRL: error=-0.120 P_out=+1.248 [offset now on wrong side]
[PID][13:05:01.024] CLAMP_BUG: output=-2.50Nm instead of +1.25Nm [now actively wrong direction]
```

### Root Cause Chain (5 Whys)

```
WHY 1: LKA applies -2.50Nm (LEFT) when vehicle has already overshot LEFT.
  → P_term = +1.25Nm (correct direction = RIGHT) but output = -2.50Nm (wrong)

WHY 2: Why is +1.25Nm inverted to -2.50Nm?
  → The output clamping function has a sign inversion bug.
    When P_term = +1.25Nm, the clamp function incorrectly applies -TORQUE_MAX.

WHY 3: Why does the clamp function invert the sign?
  → See code analysis below: the comparison uses wrong sign convention,
    causing the positive-output branch to apply negative maximum.

WHY 4: Why was this bug not caught in testing?
  → Unit tests only checked saturation cases (offset ≥ 0.24m, always clamped anyway).
    The bug only manifests when P_term is positive AND within the clamp range
    (0 < P_term < TORQUE_MAX). This combination (overshoot zone) was not in unit tests.

WHY 5: Why was the overshoot scenario not in unit tests?
  → PID unit tests were designed from the "approaching" direction only.
    "Post-overshoot" correction was assumed correct by the implementor.

ROOT CAUSE: Sign error in clamp_output() + insufficient unit test coverage
            for post-overshoot (positive P_term within range) scenario.
CATEGORY  : Software Bug (logic error) + Test Coverage Gap
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* src/lka_pid_controller.c */
#define TORQUE_MAX  2.50f

static float clamp_output(float torque_raw) {
    if (torque_raw > TORQUE_MAX) {
        return -TORQUE_MAX;   /* BUG: should return +TORQUE_MAX */
    }
    if (torque_raw < -TORQUE_MAX) {
        return -TORQUE_MAX;   /* correct for negative saturation */
    }
    return torque_raw;
}

/* Analysis of bug behavior:
 * torque_raw = +2.60 (positive saturation): → returns -2.50 WRONG (should be +2.50)
 * torque_raw = +1.25 (within range):        → +1.25 > +2.50? NO → falls to next check
 *                                             +1.25 < -2.50? NO → returns +1.25 (correct!)
 *                                             WAIT — this case works?
 *
 * Re-analysis with actual values from log:
 * torque_raw = +1.248, TORQUE_MAX = 2.50
 *   1.248 > 2.50? NO → skip
 *   1.248 < -2.50? NO → return 1.248... but log shows -2.50!
 *
 * The REAL bug is in the SIGN of the TORQUE:
 * The system applies: output = -P_term (inverted sign convention in caller)
 * So caller computes: torque = -clamp_output(P_term)
 * clamp_output(+2.50) returns -2.50 → caller: -(-2.50) = +2.50... still wrong sign
 *
 * ACTUAL BUG LOCATION: The sign is correct in the PID but the error signal
 * itself is signed incorrectly after overshoot:
 * error = target - actual = 0 - (-0.12) = +0.12 (correct)
 * P_term = Kp * error = 10.4 * 0.12 = +1.248Nm
 * torque_cmd = -P_term = -1.248Nm (should steer LEFT? NO — offset is LEFT, need RIGHT)
 *
 * THE ACTUAL BUG: error sign is correct, but torque direction mapping is inverted.
 * When offset is NEGATIVE (left of centre), error is POSITIVE,
 * P_term is POSITIVE, torque should be POSITIVE (steer RIGHT).
 * But code applies: torque_cmd = -clamp_output(P_term) → NEGATIVE.
 */
```

```c
/* ===== FIXED CODE ===== */
/* src/lka_pid_controller.c */

/* PID gains — new values per HIL tuning session */
#define LKA_KP   4.0f    /* was 10.4 — reduced to prevent saturation */
#define LKA_KI   0.5f    /* was 0.0  — integral to eliminate steady-state */
#define LKA_KD   1.2f    /* was 0.0  — derivative for damping */
#define TORQUE_MAX 2.50f
#define TS_S     0.012f  /* 12ms sample period */

static float clamp_output_fixed(float val, float limit) {
    if (val >  limit) return  limit;   /* FIXED: return +limit for positive saturation */
    if (val < -limit) return -limit;
    return val;
}

static float lka_pid_compute(LkaPidState_t *pid, float lateral_offset) {
    float error    = 0.0f - lateral_offset;  /* target = lane centre = 0 */
    float p_term   = LKA_KP * error;
    pid->integrator = clamp_output_fixed(pid->integrator + LKA_KI * TS_S * error,
                                         TORQUE_MAX);    /* integrator anti-windup */
    float d_term   = LKA_KD / TS_S * (error - pid->prev_error);
    pid->prev_error = error;

    float output   = p_term + pid->integrator + d_term;
    /* Positive output = steer RIGHT (positive torque on right-hand steering system) */
    return clamp_output_fixed(output, TORQUE_MAX);
}
```

### PID Gain Tuning (Ziegler-Nichols Method)

```
ZIEGLER-NICHOLS ULTIMATE GAIN METHOD (HIL measurement):

Step 1: Set Ki=0, Kd=0. Increase Kp until sustained oscillation observed.
  Critical Gain (Ku): Kp = 22.0 produces sustained ±0.15m oscillation at 80kph
  Critical Period (Tu): 0.18 seconds (measured from HIL oscilloscope)

Step 2: Calculate recommended gains:
  Z-N PID recommendation:
    Kp = 0.6 × Ku = 0.6 × 22.0 = 13.2
    Ti = Tu / 2   = 0.18 / 2   = 0.09s
    Td = Tu / 8   = 0.18 / 8   = 0.0225s
    Ki = Kp / Ti  = 13.2 / 0.09 = 146.7  ← way too aggressive for safety
    Kd = Kp × Td  = 13.2 × 0.0225 = 0.30

Step 3: Conservative de-rate for safety application (ISO 11270 comfort):
  Apply safety factor 0.3 to Z-N values:
    Kp = 13.2 × 0.3 = 4.0    ← FINAL
    Ki = 146.7 × 0.003 = 0.5  ← FINAL (heavily reduced — avoid windup)
    Kd = 0.30 × 4.0 = 1.2    ← FINAL

Step 4: Validate on track:
  Scenario: 100kph, gradual drift to 0.30m → correct to centre
  KPI: overshoot < 0.05m, settling time < 2.0s, no oscillation
  RESULT with new gains: overshoot = 0.02m, settling = 1.4s ✓
```

### FMEA Analysis

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| LKA PID clamp | Sign inversion: max torque applied in wrong direction | Vehicle steers into adjacent lane, driver must override | **9** | Logic error in clamp function, wrong sign convention | 4 | Code review missed; Z-N tests didn't cover overshoot | 7 | **252** |

---


---

# Part 3: LDW — Lane Departure Warning

## 3.1 Functional Architecture

```
LDW Decision Logic:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Input signals:
  LateralOffset, LateralVelocity, LaneConf, CamStatus,
  TurnIndicator, VehicleSpeed

Decision tree:
  IF speed < 60kph          → NO WARNING (below activation speed)
  IF CamStatus == ERROR      → NO WARNING (camera fault)
  IF LaneConf < 70% AND LatVel < 0.45 m/s
                             → NO WARNING (low confidence, not urgent)
  IF TurnIndicator active
     in departure direction  → SUPPRESS WARNING
  IF LaneConf < 70% AND LatVel ≥ 0.45 m/s
                             → IMMINENT DEPARTURE OVERRIDE → WARNING
                               (SRS §3.1.7 — NOT IMPLEMENTED in v5.1)
  IF LaneConf ≥ 70% AND LatVel > 0.35 m/s AND approaching boundary
                             → WARNING
  IF boundary crossed        → WARNING (with 80ms debounce — too slow)

Output: LDW_Warning (0x3B0), LDW_AudioTrig (0x3B1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Key DBC Signals:**

```
BO_ 944 LDW_WARNING: 1 ADAS_ECU
  SG_ LDW_Warning : 0|2@1+ (1,0) [0|3] "" HMI_ECU,AUDIO_ECU
    0 = "NONE"
    1 = "LEFT_WARN"
    2 = "RIGHT_WARN"
    3 = "BOTH_WARN"

BO_ 80  TURN_INDICATOR: 1 BODY_ECU
  SG_ TurnIndicator : 0|2@1+ (1,0) [0|3] "" ADAS_ECU
    0 = "OFF"
    1 = "LEFT"
    2 = "RIGHT"     ← Note: RIGHT = 0x02, NOT 0x01
    3 = "HAZARD"
```

---

## 3.2 LDW-001: False Warning When Indicator Active — DBC Value Swap

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : LDW-001                                                      ║
║ Title     : LDW warns when correct indicator active — suppression broken ║
║ Severity  : MEDIUM              ASIL: QM (annoyance, not safety)         ║
║ Standards : ISO 11270:2014 §6.2.1 — Indicator suppression required      ║
║ NCAP      : LDW false positive test                                      ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Setup & Pre-conditions

| Parameter | Value |
|---|---|
| Scenario | Roundabout navigation, tight right curve |
| Indicator | RIGHT indicator active (driver signaling turn) |
| Speed | 45 km/h (LDW active > 40kph adjusted threshold) |
| Reproducibility | 10/10 when right indicator active with right lateral velocity |

### Complete Log Triptych

**CAN Log:**

```
   0.000  0x050  Rx  d 1  02              -- TurnIndicator = 0x02 = RIGHT (indicator ON)
   0.002  0x3A1  Rx  d 8  40 00 40 00    -- LaneConf_L=64%, R=64%
   0.004  0x3A3  Rx  d 2  00 28          -- LateralVelocity = +0.40 m/s (toward RIGHT)
   0.006  0x3B0  Tx  d 1  02             -- LDW_Warning = 0x02 = RIGHT_WARN ← FALSE WARNING!
   0.006  0x3B1  Tx  d 1  01             -- Audio chime triggered
   0.008  0x050  Rx  d 1  02             -- Indicator still RIGHT
   0.010  0x3B0  Tx  d 1  02             -- Warning fires AGAIN (continuous)
   0.010  0x3B1  Tx  d 1  01             -- Chime again!
   -- [false chime fires every 20ms while indicator active]
```

**ECU System Log:**

```
[2026-05-06 14:20:05.000] [LDW] [INFO ] LateralVel=+0.40 m/s Conf=64 approaching RIGHT boundary
[2026-05-06 14:20:05.006] [LDW] [INFO ] IndicatorCheck: raw=0x02 checking suppress_right...
[2026-05-06 14:20:05.006] [LDW] [DEBUG] suppress_right_check: (indicator_val==TURN_RIGHT_CODE)?
[2026-05-06 14:20:05.006] [LDW] [DEBUG] TURN_RIGHT_CODE defined as: 0x01
[2026-05-06 14:20:05.006] [LDW] [DEBUG] indicator_val=0x02 != 0x01 → suppress_right=FALSE
[2026-05-06 14:20:05.006] [LDW] [WARN ] Suppression=FALSE. LDW_Warning=RIGHT issued.
[2026-05-06 14:20:05.006] [LDW] [DEBUG] NOTE: DBC defines RIGHT=0x02, but code uses 0x01
```

**Serial Log (ADAS ECU software debug):**

```
[LDW_SUPP][14:20:05.006] TurnIndicator raw byte = 0x02
[LDW_SUPP][14:20:05.006] Decode: LEFT_CODE=0x02, RIGHT_CODE=0x01 (SWAPPED in header!)
[LDW_SUPP][14:20:05.006] Result: indicator=LEFT (WRONG! actual=RIGHT)
[LDW_SUPP][14:20:05.006] suppress_left=TRUE, suppress_right=FALSE
[LDW_SUPP][14:20:05.006] LDW direction=RIGHT, suppress_right=FALSE → WARNING FIRES
[LDW_SUPP][14:20:05.006] ALSO: When LEFT indicator active (0x01), code reads as RIGHT
[LDW_SUPP][14:20:05.006]       → suppress_right=TRUE incorrectly, LEFT warnings suppressed
```

### Root Cause Chain (5 Whys)

```
WHY 1: LDW warns when RIGHT indicator is correctly active.
  → Indicator suppression returns FALSE for RIGHT indicator.

WHY 2: Why does suppression return FALSE for RIGHT?
  → Code checks indicator_val against TURN_RIGHT_CODE=0x01 but raw value is 0x02.

WHY 3: Why is TURN_RIGHT_CODE=0x01 when DBC defines RIGHT=0x02?
  → The header file `ldw_signals.h` defines the constants with LEFT and RIGHT swapped.
    The DBC file was updated from an older protocol where 1=Right, 2=Left,
    but the header file was not updated to match.

WHY 4: Why was the header not updated when the DBC changed?
  → There is no automated verification that C header signal constants match DBC values.
    DBC changes go through a separate change process (DBC tool) without triggering
    a source code dependency check.

WHY 5: Why is there no DBC→Code consistency check?
  → The DBC toolchain and the build system are managed by different teams (Systems vs SW).
    No CI/CD check validates that signal enum values match DBC definitions.

ROOT CAUSE: DBC constant values swapped (LEFT↔RIGHT) in ldw_signals.h header.
            No automated DBC→code consistency gate in CI pipeline.
CATEGORY  : Configuration Error + Process Gap (no DBC-to-code validation)
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* include/ldw_signals.h */
/* WRONG — swapped from previous protocol version */
#define TURN_INDICATOR_OFF    0x00u
#define TURN_INDICATOR_LEFT   0x02u   /* BUG: should be 0x01 */
#define TURN_INDICATOR_RIGHT  0x01u   /* BUG: should be 0x02 */
#define TURN_INDICATOR_HAZARD 0x03u

/* src/ldw_suppression.c */
static bool ldw_should_suppress(uint8_t indicator_val, LdwDirection_t warn_dir) {
    if (warn_dir == LDW_DIR_LEFT) {
        return (indicator_val == TURN_INDICATOR_LEFT);   /* matches 0x02 when raw=0x01 — WRONG */
    } else {
        return (indicator_val == TURN_INDICATOR_RIGHT);  /* matches 0x01 when raw=0x02 — WRONG */
    }
}
```

```c
/* ===== FIXED CODE ===== */
/* include/ldw_signals.h */
/* Corrected to match BODY_ECU DBC v3.4, signal TurnIndicator */
#define TURN_INDICATOR_OFF    0x00u
#define TURN_INDICATOR_LEFT   0x01u   /* FIXED */
#define TURN_INDICATOR_RIGHT  0x02u   /* FIXED */
#define TURN_INDICATOR_HAZARD 0x03u

/* PROCESS FIX: Add to CMakeLists.txt — DBC validation step */
/* cmake/dbc_validate.cmake:
 * add_test(NAME dbc_signal_constants_check
 *   COMMAND python3 scripts/validate_dbc_constants.py
 *             --dbc   ${DBC_FILE}
 *             --header include/ldw_signals.h
 *             --signal TurnIndicator
 * )
 */
```

### FMEA Analysis

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| Indicator suppression | Wrong constant → suppress fails | False LDW warning → driver annoyance, trust erosion | 5 | DBC↔header constant swap | 8 | Manual review only | 8 | **320** |
| Indicator suppression | Wrong constant → suppresses WRONG direction | LDW misses warning on genuine departure | 7 | Same constant swap | 8 | Not tested with both directions | 7 | **392** |

**Secondary finding RPN=392 is more dangerous — LDW suppresses real warnings!**

### Test Cases

**TC-LDW-001-01: Right indicator + right departure → NO warning**
```
Stimuli  : LateralVelocity=+0.45m/s, TurnIndicator=0x02 (RIGHT)
Expected : LDW_Warning=0x00 (NONE)
```
**TC-LDW-001-02: Left indicator + left departure → NO warning**
```
Stimuli  : LateralVelocity=-0.45m/s, TurnIndicator=0x01 (LEFT)
Expected : LDW_Warning=0x00 (NONE)
```
**TC-LDW-001-03: Right indicator + LEFT departure → WARNING (genuine unintended)**
```
Stimuli  : LateralVelocity=-0.45m/s, TurnIndicator=0x02 (RIGHT)
Expected : LDW_Warning=0x01 (LEFT_WARN)
```
**TC-LDW-001-04: Left indicator + RIGHT departure → WARNING (genuine unintended)**
```
Stimuli  : LateralVelocity=+0.45m/s, TurnIndicator=0x01 (LEFT)
Expected : LDW_Warning=0x02 (RIGHT_WARN)
```
**TC-LDW-001-05: Hazard lights → NO warning in either direction**
```
Stimuli  : LateralVelocity=±0.45m/s, TurnIndicator=0x03 (HAZARD)
Expected : LDW_Warning=0x00 (NONE) — hazard = intentional slow/stop
```

---

## 3.3 LDW-002: Missing Warning in Wet/Night — Imminent Departure Override Not Implemented

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : LDW-002                                                      ║
║ Title     : LDW no warning on wet motorway at night — conf below 70%    ║
║ Severity  : CRITICAL            SRS Ref: LDW-SRS-§3.1.7 (not impl.)    ║
║ Standards : ISO 11270:2014 §6.2.3 — Degraded conditions performance    ║
║ FuSa      : Safety-critical missed warning                               ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log (key frames):**
```
   0.000  0x3A0  Rx  d 1  01              -- CamStatus = DEGRADED (not ERROR)
   0.002  0x3A1  Rx  d 8  28 00 28 00    -- LaneConf_L=40%, R=40%
   0.004  0x3A3  Rx  d 2  00 32          -- LateralVelocity = +0.50 m/s  ← IMMINENT
   0.006  0x3B0  Tx  d 1  00             -- LDW_Warning = NONE ← MISSED WARNING!
   0.500  [VEHICLE CROSSES LANE BOUNDARY — no warning ever issued]
```

**System Log:**
```
[LDW] CamStatus=DEGRADED(1). LaneConf=40 < min_conf=70. Warning suppressed.
[LDW] SRS §3.1.7 OVERRIDE: LateralVelocity=0.50 > 0.45 AND CamStatus != ERROR
      → Should issue warning regardless of confidence. NOT IMPLEMENTED.
[LDW] Vehicle crossed boundary. LDW_Missed_Warning event logged.
```

**Serial Log:**
```
[CAM] NIGHT_MODE: gain=+22dB, retroreflection=LOW (wet surface)
[CAM] LANE_DETECT: geometry visible, paint_contrast < edge_threshold
[CAM] LANE_CONF: L=40 R=40 (geometric detection, low photometric confidence)
[CAM] NOTE: markings ARE physically present — low confidence is AEC limitation
```

**Root Cause:**
```
SRS §3.1.7 specifies:
  "If LateralVelocity > 0.45 m/s AND CamStatus ≠ ERROR AND vehicle approaching
   lane boundary, LDW shall issue warning REGARDLESS of LaneConf value."

This "imminent departure override" path is not implemented in the code.
The code uses a single gate: if (conf < 70%) → NO WARNING, always.
This ignores the emergency override rule for high-velocity departures.

WHY NOT IMPLEMENTED:
  The SRS was written after the initial implementation was frozen.
  §3.1.7 was added in SRS revision 2.1 but the change was not propagated
  to the software requirements traceability matrix or the developer.
```

**Code Fix:**
```c
/* Add BEFORE the confidence gate in ldw_decision.c */

/* SRS §3.1.7 — Imminent departure override */
static bool ldw_imminent_departure_override(const LdwInputs_t *in, LdwDirection_t *dir) {
    float abs_vel = fabsf(in->lateral_velocity_ms);

    if (in->cam_status == CAM_STATUS_ERROR) return false;   /* camera fully failed */
    if (abs_vel < LDW_IMMINENT_VEL_THRESHOLD) return false; /* 0.45 m/s */
    if (!ldw_approaching_boundary(in)) return false;

    *dir = (in->lateral_velocity_ms > 0.0f) ? LDW_DIR_RIGHT : LDW_DIR_LEFT;
    log_warn("[LDW] IMMINENT_DEPARTURE_OVERRIDE: vel=%.2f conf=%d cam=%d",
             abs_vel, in->lane_conf, in->cam_status);
    return true;
}

/* In main decision function — check override FIRST */
LdwDirection_t warn_dir;
if (ldw_imminent_departure_override(&inputs, &warn_dir)) {
    ldw_issue_warning(warn_dir);
    return;
}
/* then proceed with normal confidence-gated path */
```

### FMEA

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| LDW imminent override | SRS §3.1.7 not implemented | No warning at night/wet when vehicle departing lane | **9** | SRS change not propagated to SW team | 6 | Only clear-day tests in regression | 8 | **432** |

**RPN = 432 → CRITICAL — IMMEDIATE FIX REQUIRED**

---

## 3.4 LDW-003: Warning Too Late — Reactive vs Predictive Logic

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : LDW-003                                                      ║
║ Title     : LDW warning 298ms after boundary crossing — fails SRS 150ms ║
║ Severity  : HIGH                SRS Ref: LDW-SRS-§3.2.1 latency req     ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log:**
```
   0.200  0x3A2  Rx  d 4  00 3C 00 00    -- LateralOffset = 0.60m (AT boundary)
   0.200  [LDW] Boundary crossing detected. Starting 80ms debounce timer.
   0.280  0x3B0  Tx  d 1  02             -- LDW_Warning = RIGHT (80ms AFTER crossing!)
   0.280  0x3B1  Tx  d 1  01             -- Audio command sent to HMI-ECU
   0.298  [SPEAKER] Chime starts (18ms audio path)
   -- Total latency: 298ms from crossing. SRS requires ≤150ms.
```

**Timing breakdown:**
```
 Boundary crossing ────────────────────────────────────────────► TIME
   T=0       T=80ms       T=98ms      T=280ms     T=298ms
   │          │            │           │           │
   Crossing   Debounce     LDW_Warning CAN frame   Chime
   detected   starts       issued      arrives HMI plays
                                                   
   [  80ms debounce  ][  200ms additional delay?  ][ 18ms audio ]
   
   PROBLEM: 80ms debounce STARTS AFTER crossing (should filter before)
   PROBLEM: Additional processing/queuing adds 200ms unexplained latency
```

**Root Cause:**
```
Two issues compound:

1. REACTIVE warning: fires after boundary is crossed, not before.
   Correct approach: PREDICTIVE — compute time-to-boundary and warn in advance.
   
   time_to_boundary = (boundary - current_offset) / lateral_velocity
   At T = boundary - 800ms (configurable lead time) → issue warning
   This gives driver reaction time before crossing, not after.

2. 80ms post-crossing debounce: intended to filter brief camera noise that
   causes false boundary-crossing detection. But placed AFTER warning, not before.
   Correct: apply debounce to the confidence/velocity inputs, not to the output.
```

**Code Fix:**
```c
/* BEFORE (reactive, post-crossing): */
if (boundary_crossed) {
    start_debounce_timer(80);       /* wrong: timer AFTER crossing */
    if (debounce_expired) issue_warning();
}

/* AFTER (predictive, pre-crossing): */
float dist_to_boundary = fabsf(boundary - lateral_offset);
float time_to_boundary = dist_to_boundary / fabsf(lateral_velocity);

if (time_to_boundary < LDW_WARN_TTC_THRESHOLD &&  /* 800ms threshold */
    lateral_velocity_sustained_ms > 100 &&          /* velocity confirmed for 100ms — debounce */
    fabsf(lateral_velocity) > LDW_MIN_VEL) {
    issue_warning(direction);
}
/* Expected latency with fix: ~30-50ms from threshold crossing */
```

### FMEA

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| LDW warning timing | 298ms total latency vs 150ms SRS | Warning too late for driver reaction | 7 | Reactive (not predictive) + debounce placement | 7 | SRS latency tested but debounce not counted | 5 | **245** |

---

# Part 4: TSR — Traffic Sign Recognition

## 4.1 Functional Architecture

```
TSR SIGNAL FUSION LOGIC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Camera (CNN classifier) ──┐
                             ├──► FUSION ENGINE ──► Display (0x4A2)
  Map Database (RDBMS)    ──┘         │
                                      │  Fusion rules:
  NORMAL:  if cam_conf ≥ 70%:         │    winner = CAMERA
           elif map available:        │    winner = MAP
           else:                      │    winner = LAST_KNOWN
                                      │
  CONFLICT: |cam_speed - map_speed| > 20kph
            if cam_conf ≥ 70% AND cam_sign_age < freshness_s:
              winner = CAMERA (potential bug when sign is stale!)
            else:
              winner = MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Key DBC Signals:
  0x4A0: TSR_SpeedLimit    (0=invalid, 5..130 km/h displayed values)
  0x4A1: TSR_Confidence    (0-100%)
  0x4A2: TSR_Display       (0=Off, 1=Show)
  0x4A3: TSR_Source        (0=Camera, 1=Map, 2=Fused, 3=LastKnown)
  0x4B0: MapSpeedLimit     (from HD map ECU or navigation head unit)
```

---

## 4.2 TSR-001: Stale Motorway Sign Displayed After Road Type Change

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : TSR-001                                                      ║
║ Title     : TSR shows 120kph on 80kph road for 60+ seconds after exit   ║
║ Severity  : HIGH                ASIL: QM (driver information quality)   ║
║ Standards : ISO 11270 Annex B — TSR fusion and display quality          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log:**
```
   0.000  0x4A0  Rx  d 1  78    -- TSR camera = 120 km/h (motorway sign, aged 0s)
   0.000  0x4B0  Rx  d 1  50    -- Map = 80 km/h (local road — correct, road type changed)
   0.002  0x4A3  Tx  d 1  00    -- TSR_Source = CAMERA (camera wins conflict)
   0.002  0x4A2  Tx  d 1  01    -- Display = ON, showing 120
   60.000 0x4A0  Rx  d 1  50    -- New camera sign: 80 km/h (finally passed a sign)
   60.002 0x4A3  Tx  d 1  02    -- TSR_Source = FUSED (agree)
   60.002 0x4A2  Tx  d 1  01    -- Display: 80 ← 60 seconds too late!
```

**System Log:**
```
[TSR] Conflict: cam=120 map=80. Freshness check: cam_sign_age=0s < staleness_threshold=120s
[TSR] Camera wins (conf=90%, age within 120s window). Display=120.
[TSR] Road class change detected: MOTORWAY→LOCAL (from map). Action: NONE.
[TSR] [60s later] New camera sign: 80. Conflict resolved. Display=80.
[TSR] MISSED_OPPORTUNITY: road class change at T=0 should have reset cam sign trust.
```

**Root Cause:**
```
TSR camera sign staleness window = 120 seconds.
On motorways, 120s is reasonable (long stretches between signs).
On local roads after exit: new sign may be 60s away — 120s too long.

Missing logic: "road class change" event should trigger:
  1. Immediate reduction of cam_sign staleness window to 10-15s
  2. Switch fusion to MAP_PRIORITY until new camera sign acquired

WHY: TSR staleness timeout is a single global constant.
     No context-aware dynamic timeout.
     No road class change event handler.
```

**Code Fix:**
```c
/* src/tsr_fusion.c */

/* New function: adjust staleness based on road type transition */
static uint32_t tsr_get_staleness_window_ms(MapRoadClass_t current_class,
                                             MapRoadClass_t prev_class) {
    bool road_class_changed = (current_class != prev_class);
    
    if (road_class_changed) {
        /* Road type transition — old sign is likely from previous road type */
        switch (current_class) {
            case ROAD_CLASS_MOTORWAY:  return 120000u;  /* 120s on motorway */
            case ROAD_CLASS_NATIONAL:  return 30000u;   /* 30s on A-road */
            case ROAD_CLASS_URBAN:     return 10000u;   /* 10s in urban */
            default:                   return 15000u;
        }
    }
    return 120000u;  /* no transition: use full window */
}

static TsrSource_t tsr_fuse(TsrState_t *s, uint8_t cam_speed, uint8_t map_speed,
                             uint8_t cam_conf, uint32_t sign_age_ms) {
    uint32_t staleness_ms = tsr_get_staleness_window_ms(s->curr_road_class,
                                                         s->prev_road_class);
    bool sign_stale = (sign_age_ms > staleness_ms);
    bool conflict   = (abs((int)cam_speed - (int)map_speed) > 20);
    
    if (conflict && (sign_stale || cam_conf < 70u)) {
        s->display_speed = map_speed;
        return TSR_SOURCE_MAP;   /* prefer fresh map over stale/low-conf camera */
    }
    if (cam_conf >= 70u && !sign_stale) {
        s->display_speed = cam_speed;
        return TSR_SOURCE_CAMERA;
    }
    if (map_speed > 0u) {
        s->display_speed = map_speed;
        return TSR_SOURCE_MAP;
    }
    return TSR_SOURCE_LAST_KNOWN;
}
```

**FMEA:**

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| TSR fusion staleness | Fixed 120s window ignores road type | Wrong speed displayed 60s — driver may over-speed | 6 | No context-aware timeout | 7 | Road type change not in TSR test matrix | 7 | **294** |

---

## 4.3 TSR-002: Temporary Roadworks Sign Overrides Permanent Map Limit

**CAN Log:**
```
   0.000  0x4A0  Rx  d 1  32    -- Camera: 50 km/h (roadworks LED matrix board)
   0.000  0x4B0  Rx  d 1  64    -- Map: 100 km/h (correct permanent speed)
   0.002  0x4A1  Rx  d 1  5A    -- TSR_Confidence = 90%
   0.002  0x4A2  Tx  d 1  01    -- Display: 50 km/h (camera wins)
   -- No HMI distinction between permanent (circle) and variable (matrix board)
```

**System Log:**
```
[TSR] Camera: speed=50 type=VARIABLE_SIGN blink_rate=2Hz conf=90%
[TSR] Map: speed=100 road_class=NATIONAL_ROAD
[TSR] FUSION: conf=90%>70% → camera wins. Display=50.
[TSR] BUG: sign_type field (STATIC/VARIABLE) NOT read in fusion path.
[TSR] SRS §5.4.2: variable signs shall be distinguished and displayed with amber border.
```

**Root Cause:**
```
Camera CNN classifies sign as VARIABLE (LED matrix, blinking border detected).
This sign_type=VARIABLE flag is set in TSR_SignType signal (0x4A4) but fusion
engine does not read sign_type. It only reads speed value and confidence.

SRS §5.4.2: "Variable message signs shall be displayed with amber border indicator
and shall not override static map speed limits in fusion when conflict exists."

Fix: Read sign_type in fusion. If VARIABLE_SIGN AND conflict_with_map:
  - Display camera speed WITH amber VMS indicator
  - Reduce camera confidence weight in fusion by 40%
  - Do not suppress map data entirely
```

**Code Fix:**
```c
/* Additional DBC signal needed: */
/* BO_ 1188 TSR_SIGN_TYPE: 1 ADAS_CAM
 *   SG_ TSR_SignType : 0|2@1+
 *     0 = "STATIC_CIRCLE"    (permanent regulatory sign)
 *     1 = "VARIABLE_MATRIX"  (electronic variable speed sign)
 *     2 = "TEMPORARY_BOARD"  (roadworks board)
 *     3 = "UNKNOWN"
 */

if (sign_type == TSR_SIGN_VARIABLE || sign_type == TSR_SIGN_TEMPORARY) {
    cam_conf_adjusted = cam_conf * 0.6f;  /* reduce trust for variable signs */
    hmi_show_amber_vms_border = true;
}
```

---

## 4.4 TSR-003: Zero km/h Displayed After Tunnel — Display Flag Not Cleared

**CAN Log:**
```
   [Vehicle enters tunnel]
   0.000  0x3A0  Rx  d 1  02    -- CamStatus = BLOCKED (2) — dark tunnel
   0.002  0x4A0  Rx  d 1  00    -- TSR_SpeedLimit = 0 (no sign in tunnel)
   0.002  0x4A1  Rx  d 1  00    -- Confidence = 0%
   0.002  0x4A2  Tx  d 1  01    -- TSR_Display = ON ← BUG! Should be OFF when speed=0
   -- Cluster shows "0" as speed limit. Confusing/alarming to driver.
```

**System Log:**
```
[TSR] Tunnel entry detected. SpeedLimit=0 Conf=0.
[TSR] DisplayGating: conf=0 < min_conf=30 → display should be=FALSE.
[TSR] BUG: display_enable flag not cleared. Previous value (TRUE) persists.
[TSR] Sending TSR_Display=1 to HMI with SpeedLimit=0 → shows "0 km/h"
```

**Root Cause & Fix:**
```c
/* BUGGY: display_enable not cleared on conf drop */
if (tsr_conf >= MIN_DISPLAY_CONF) {
    display_enable = true;
    tsr_display_speed(speed);
}
/* else: nothing! display_enable stays true from previous frame */

/* FIXED: explicit else-clear */
if (tsr_conf >= MIN_DISPLAY_CONF && speed > 0u && cam_status != CAM_BLOCKED) {
    display_enable = true;
    tsr_display_speed(speed);
} else {
    display_enable = false;   /* explicitly blank the TSR display */
    tsr_blank_display();
}
```

**Test Cases:**
```
TC-TSR-003-01: Tunnel entry → display goes blank within 1 camera frame
TC-TSR-003-02: Underground car park → no "0 km/h" shown
TC-TSR-003-03: Heavy rain (camera blocked) → display blanked, not frozen
TC-TSR-003-04: Night no sign → display blank, not 0
TC-TSR-003-05: Post-tunnel exit → display resumes with first valid sign
```

---

# Part 5: BSD — Blind Spot Detection

## 5.1 Radar Physics Background

Understanding radar physics is essential for debugging BSD detection failures:

```
RADAR CROSS SECTION (RCS) FUNDAMENTALS
═══════════════════════════════════════════════════════════════
RCS (σ) is the effective area of an object as seen by radar.
Measured in square metres or decibels per square metre (dBsm).

  σ_dBsm = 10 × log₁₀(σ_m²)

Typical values:
  Object                   σ_m²        σ_dBsm
  ──────────────────────────────────────────
  Pedestrian              0.1 – 3       -10 to +5
  Bicycle / e-scooter     0.5 – 2        -3 to +3
  Motorcycle              1.3 – 5        +1 to +7
  Passenger car           10 – 316      +10 to +25
  SUV / MPV               20 – 500      +13 to +27
  Lorry / HGV            100 – 3162     +20 to +35

Radar range equation (simplified):
  SNR = (P_tx × G_tx × G_rx × λ² × σ) / ((4π)³ × R⁴ × k × T × B × NF)

  Where:
    P_tx = transmit power (~100mW at 77GHz)
    G    = antenna gain (~25dBi)
    λ    = wavelength (3.9mm at 77GHz)
    R    = range (m)
    σ    = target RCS (m²)
    k    = Boltzmann constant
    B    = bandwidth (~200MHz for 0.75m range resolution)

Detection threshold: SNR > SNR_min (typically 12dB)

BSD RCS FILTER ANALYSIS:
  Current threshold: σ_min = 10 m² (10 dBsm) — designed for passenger cars
  Motorcycle σ at worst case: 1.3 m² (1.1 dBsm) — BELOW threshold by 9dB!
  Even best-case motorcycle 5m² (7dBsm) — STILL below 10dBsm by 3dB.
  → ALL motorcycles are systematically excluded.
```

## 5.2 BSD-001: Motorcycle in Blind Spot Not Detected — RCS Threshold Too High

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : BSD-001                                                      ║
║ Title     : BSD fails to detect motorcycles — RCS threshold excludes VRU║
║ Severity  : CRITICAL            ASIL: ASIL A violation                   ║
║ Standards : Euro NCAP 2026 — BSD motorcycle detection requirement        ║
║ FuSa      : Safety goal: "Warn driver of vehicles in blind spot zone"    ║
║             Motorcycle is a vehicle — safety goal breach                 ║
║ Regulatory: Potential type approval failure                               ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Complete Log Triptych

**CAN Log:**
```
   0.000  0x020  Rx  d 2  00 64    -- VehicleSpeed = 100 km/h
   0.000  0x5B0  Rx  d 8  00 00 00 00 00 00 00 00  -- Left radar: NO OBJECT
   0.002  0x5A0  Rx  d 2  00 00    -- BSD_ObjLeft=0, BSD_ObjRight=0
   0.050  0x050  Rx  d 1  01       -- TurnIndicator = LEFT
   0.052  0x5A1  Tx  d 2  00 00    -- BSD_WarnLeft=0 (no warning → driver merges left)
   0.150  [NEAR_COLLISION] Motorcycle in left blind spot — dashcam confirms
```

**ECU System Log:**
```
[BSD][10:22:05.000] Left radar scan: no objects above RCS threshold.
[BSD][10:22:05.001] RCS filter: threshold=10.0dBsm. Objects below threshold: 1 (rejected)
[BSD][10:22:05.001] Rejected object: range=4.2m rcs=3.2dBsm width_est=0.6m vel_rel=-2.0m/s
[BSD][10:22:05.001] CLASSIFICATION: below_min_rcs → IGNORED. No BSD warning.
[BSD][10:22:05.050] TurnIndicator=LEFT. BSD_ObjLeft=FALSE. No warning issued.
[BSD][10:22:05.050] SAFETY EVENT: lane change without BSD warning. Motorcycle at 4.2m.
```

**Serial Log (Radar ECU UART):**
```
[RADAR_L][10:22:05.000] FMCW_SCAN: range_bins=0-10m, azimuth=-15°+15°
[RADAR_L][10:22:05.001] DETECTION: cfar_threshold_exceeded at range=4.15m
[RADAR_L][10:22:05.001] POINT_TARGET: range=4.15m azim=+6.2° vel_doppler=-2.0m/s
[RADAR_L][10:22:05.001] RCS_ESTIMATE: 3.2dBsm (confidence=HIGH from 4 range bins)
[RADAR_L][10:22:05.001] TARGET_WIDTH: 0.58m (from azimuth spread, consistent with motorcycle)
[RADAR_L][10:22:05.001] TARGET_HEIGHT: not measured (no elevation estimation in this radar)
[RADAR_L][10:22:05.001] OBJECT_FILTER: rcs=3.2 < rcs_threshold=10.0 → REJECTED
[RADAR_L][10:22:05.001] OUTPUT: no_object_in_zone (despite physical detection!)
[RADAR_L][10:22:05.001] NOTE: target_velocity=-2.0m/s relative (approaching from rear)
[RADAR_L][10:22:05.001] NOTE: target_width=0.58m → motorcycle/bicycle class
```

### Root Cause Chain (5 Whys)

```
WHY 1: BSD does not warn about motorcycle at 4.2m.
  → BSD object present flag = FALSE. No object reported to ADAS ECU.

WHY 2: Why is BSD_ObjLeft = FALSE when radar detects an object?
  → Radar CFAR detector finds the object but the RCS filter rejects it.
    3.2dBsm < 10.0dBsm threshold → object classified as clutter → rejected.

WHY 3: Why is the RCS threshold 10.0dBsm?
  → The threshold was set during radar supplier integration in 2024.
    Calibration used passenger car test targets only (σ = 15-20dBsm).
    The 10dBsm threshold was chosen as a safety margin below car RCS.
    Motorcycle scenarios were not in the calibration test matrix.

WHY 4: Why were motorcycles not in the calibration matrix?
  → The BSD system requirement specification (BSD-SRS-§2.1) only listed
    "vehicles" as detection targets without defining minimum RCS for
    different vehicle classes. Motorcycle was implicitly assumed covered.

WHY 5: Why was motorcycle RCS not specified in SRS?
  → The original SRS was based on Euro NCAP 2020 which did not have
    motorcycle BSD scoring. NCAP 2026 added motorcycle BSD tests but
    the SRS was not updated when NCAP 2026 requirements were published.

ROOT CAUSE: SRS does not specify VRU (Vulnerable Road User) minimum RCS.
            Radar RCS filter calibrated for cars only. NCAP 2026 compliance gap.
CATEGORY  : Specification Gap + Calibration Error + Process Gap (NCAP watch)
SAFETY    : Safety goal for BSD covers all vehicles in blind spot zone.
            Motorcycle exclusion is a safety goal breach.
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* src/bsd_radar_filter.c */
#define BSD_RCS_MIN_DBSM     10.0f   /* minimum RCS for detection — cars only */

static bool bsd_object_valid(const RadarObject_t *obj) {
    if (obj->rcs_dbsm < BSD_RCS_MIN_DBSM) {
        return false;   /* rejects motorcycles, bicycles, pedestrians */
    }
    if (obj->range_m > BSD_ZONE_RANGE_M) {
        return false;
    }
    return true;
}
```

```c
/* ===== FIXED CODE ===== */
/* src/bsd_radar_filter.c */

/* VRU detection: use multi-feature classification, not single RCS threshold */
#define BSD_RCS_MIN_CAR_DBSM      10.0f   /* passenger car minimum */
#define BSD_RCS_MIN_VRU_DBSM       2.0f   /* motorcycle/bicycle minimum */
#define BSD_WIDTH_VRU_MAX_M        1.2f   /* max width for VRU classification */
#define BSD_WIDTH_CAR_MIN_M        1.4f   /* min width for car classification */
#define BSD_VEL_MOVING_MIN_MS      0.5f   /* min velocity to confirm moving object */

typedef enum {
    BSD_CLASS_UNKNOWN    = 0,
    BSD_CLASS_PASSENGER  = 1,
    BSD_CLASS_VRU        = 2,    /* motorcycle, bicycle, pedestrian */
    BSD_CLASS_STATIC     = 3,    /* guardrail, sign — to be filtered */
} BsdObjectClass_t;

static BsdObjectClass_t bsd_classify_object(const RadarObject_t *obj) {
    float abs_vel = fabsf(obj->velocity_relative_ms);
    
    /* Static objects: near-zero velocity relative to ground */
    float ground_vel = fabsf(obj->velocity_relative_ms + ego_speed_ms);
    if (ground_vel < 2.0f) {
        return BSD_CLASS_STATIC;   /* guardrail, road sign */
    }
    
    /* VRU: small width, low RCS, but moving */
    if (obj->width_est_m <= BSD_WIDTH_VRU_MAX_M &&
        obj->rcs_dbsm    >= BSD_RCS_MIN_VRU_DBSM &&
        abs_vel          >= BSD_VEL_MOVING_MIN_MS) {
        return BSD_CLASS_VRU;
    }
    
    /* Passenger car / vehicle */
    if (obj->rcs_dbsm    >= BSD_RCS_MIN_CAR_DBSM &&
        obj->width_est_m >= BSD_WIDTH_CAR_MIN_M) {
        return BSD_CLASS_PASSENGER;
    }
    
    return BSD_CLASS_UNKNOWN;
}

static bool bsd_object_valid(const RadarObject_t *obj) {
    BsdObjectClass_t cls = bsd_classify_object(obj);
    
    if (cls == BSD_CLASS_STATIC)  return false;   /* infrastructure */
    if (cls == BSD_CLASS_UNKNOWN) return false;   /* below all thresholds */
    if (obj->range_m > BSD_ZONE_RANGE_M) return false;
    
    /* Both VRU and PASSENGER classes are valid BSD targets */
    return (cls == BSD_CLASS_VRU || cls == BSD_CLASS_PASSENGER);
}
```

### FMEA Analysis

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| BSD RCS filter | Motorcycle RCS below threshold → not detected | Driver merges into motorcycle, serious collision risk | **10** | RCS threshold calibrated for cars only | 8 | No motorcycle test in regression | 9 | **720** |

**RPN = 720 → MAXIMUM CRITICALITY — Stop delivery, immediate patch**

### Test Cases

**TC-BSD-001-01: Motorcycle RCS Detection — Right Side**
```
Setup    : Radar signal injection: range=4.0m, rcs=3.2dBsm, width=0.6m, vel_rel=-2.0m/s
Expected : BSD_ObjRight=1, BSD_WarnRight=1 when TurnIndicator=RIGHT
Automation: HIL (radar ECU signal injection)
```
**TC-BSD-001-02: Bicycle Detection**
```
Setup    : range=3.5m, rcs=1.5dBsm, width=0.5m, vel_rel=-1.5m/s
Expected : BSD_ObjLeft=1
```
**TC-BSD-001-03: Guardrail NOT detected (false positive prevention)**
```
Setup    : range=3.0m, rcs=8.0dBsm, width=50m, vel_rel=0 (ground_vel≈0)
Expected : BSD_ObjRight=0 (static infrastructure filtered)
```
**TC-BSD-001-04: Motorcycle + car simultaneously**
```
Setup    : Left: motorcycle (rcs=3dBsm). Right: car (rcs=15dBsm).
Expected : BSD_ObjLeft=1, BSD_ObjRight=1 (both detected)
```
**TC-BSD-001-05: NCAP motorcycle BSD test protocol**
```
Setup    : Per Euro NCAP 2026 §3.4.1 — motorcycle approach at 10kph diff, 3m lateral
Expected : BSD warning ≥ 95% of runs. Zero misses ≤ 3m range.
Automation: Vehicle test (NCAP homologation run)
```

---

## 5.3 BSD-002: Guardrail False Positive — Static Object Filter Disabled

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : BSD-002                                                      ║
║ Title     : BSD warns on curved road guardrail — static filter disabled  ║
║ Severity  : MEDIUM              ASIL: QM (false positive annoyance)      ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log:**
```
   0.000  0x5B0  Rx  d 8  00 05 00 00 00 00 00 00  -- Right obj: range=5.2m
   0.002  0x5A0  Rx  d 2  00 01    -- BSD_ObjRight = TRUE
   0.002  0x050  Rx  d 1  02       -- TurnIndicator = RIGHT
   0.004  0x5A1  Tx  d 2  00 01    -- BSD_WarnRight = TRUE ← false warning!
   -- Guardrail on curved motorway. No vehicle present.
```

**System Log:**
```
[BSD] Right: range=5.2m rcs=12dBsm width=40m vel_rel=-27.8m/s (ego speed component)
[BSD] Ground velocity: vel_rel + ego_speed = -27.8 + 27.8 = 0 m/s → STATIONARY
[BSD] StaticFilter: DISABLED (config flag static_filter_enabled=0 in calib file!)
[BSD] Object classified as PRESENT. BSD_WarnRight=1.
[BSD] CONFIG ERROR: static_filter_enabled should be TRUE for production.
```

**Root Cause:**
```
BSD calibration file (bsd_calib.json) has:
  "static_filter_enabled": false   ← engineering debug mode left in production build!

The static object filter was disabled during radar bring-up debugging.
It was never re-enabled before the calibration file was locked for production.
No build validation check confirms static_filter_enabled=true for production builds.

Fix:
  1. Immediate: Set static_filter_enabled=true in production calibration file.
  2. Process: Add CI check: if (build_type==RELEASE && static_filter_enabled==false) → FAIL.
  3. Add log warning at startup: if static_filter_enabled==false → log CRIT + set DTC.
```

---

## 5.4 BSD-003: Mirror LED Stays On 2s After Vehicle Overtakes — Timeout Too Long

**CAN Log:**
```
   0.000  0x5B0  Rx  d 8  00 04 00 00 00 00 00 00  -- Right: object 4m
   0.002  0x5A0  Rx  d 2  00 01    -- BSD_ObjRight = TRUE (mirror LED on)
   0.500  0x5B0  Rx  d 8  00 00 00 00 00 00 00 00  -- Object GONE
   0.502  0x5A0  Rx  d 2  00 01    -- BSD_ObjRight STILL TRUE (clearance timer)
   2.000  0x5A0  Rx  d 2  00 00    -- Finally FALSE (2.0s after object left)
   -- SRS §6.2.4: indicator shall extinguish within 500ms of object leaving zone
```

**Root Cause & Fix:**
```
clearance_timeout = 2000ms (global constant).
SRS §6.2.4 requires: ≤500ms.

Improved fix — velocity-adaptive timeout:
  float vel_relative = get_object_relative_velocity();
  
  if (fabsf(vel_relative) > 5.0f) {
      clearance_ms = 150u;   /* fast overtake — clear quickly */
  } else if (fabsf(vel_relative) > 2.0f) {
      clearance_ms = 350u;   /* moderate overtake */
  } else {
      clearance_ms = 500u;   /* slow parallel — longest allowed by SRS */
  }
  /* All values ≤ SRS maximum of 500ms */
```

---

# Part 6: Parking Assistance / PDC

## 6.1 Ultrasonic Sensor Physics

```
ULTRASONIC TRANSDUCER OPERATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frequency: 40–48 kHz (Bosch USS5, Valeo 18xx, etc.)
Burst duration: 300μs
Speed of sound: c = 343 m/s at 20°C

Distance calculation:
  d = (c × echo_time) / 2
  At 25cm: echo_time = 2 × 0.25 / 343 = 1.46ms
  At 250cm: echo_time = 14.6ms
  Max measurable range: ~300cm (echo_time = 17.5ms, before next burst)

BLOCKED SENSOR DIAGNOSIS:
  Normal (open space): burst → propagates → echo_time = travel_time
  Blocked (solid contact): burst → absorbed by obstruction → no echo
  
  Both "open beyond range" and "blocked" produce echo_time = 0.
  CANNOT DISTINGUISH by echo time alone!
  
  Methods to detect obstruction:
  1. Cross-echo: sensor A bursts, sensor B listens for cross-echo.
     Expected cross-echo time: ~1.5ms for 25cm sensor spacing.
     If cross-echo absent → A or B is blocked.
  2. Membrane resonance: measure ring-down frequency after burst.
     Blocked membrane: altered damping → frequency shift detected.
  3. Statistical: >3 consecutive zero-echo bursts while in Reverse →
     high probability obstruction (not just "large empty space").
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 6.2 PDC-001: No Alert — Sensor Blocked by Tow Hitch Cover

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : PDC-001                                                      ║
║ Title     : PDC no rear alert — sensor obstructed, blockage not detected ║
║ Severity  : HIGH                SRS Ref: PDC-SRS-§7.1.8 (not impl.)     ║
║ Standards : UN ECE Regulation 58 — parking sensor performance            ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log:**
```
   0.000  0x0B0  Rx  d 1  02    -- Gear = REVERSE
   0.002  0x6A1  Rx  d 4  00 00 00 00  -- PDC_Rear_Dist = 0cm (all 4 rear sensors = 0)
   0.004  0x6A3  Rx  d 1  00    -- PDC_SensorFault = 0x00 (no fault!) ← PROBLEM
   0.006  0x6A2  Tx  d 1  00    -- PDC_Alert = OFF
   2.000  [COLLISION with bollard at 20cm]
```

**System Log:**
```
[PDC] Gear=REVERSE. Activating rear PDC.
[PDC] Rear_L=0 Rear_ML=0 Rear_MR=0 Rear_R=0 (all zero — no echo received)
[PDC] DistanceFilter: all_zero → interpreted as NO_OBJECT_IN_RANGE (250cm max)
[PDC] SensorHealth: voltage=3.2V OK, temp=25°C OK, burst_driven=TRUE, echo_received=FALSE
[PDC] SensorFault logic: no electrical fault detected → fault_flag=FALSE
[PDC] PDC_Alert=OFF. No warning issued.
[PDC] SRS §7.1.8: "PDC shall detect sensor obstruction and set PDC_SensorFault."
[PDC] SRS §7.1.8: NOT IMPLEMENTED — no acoustic self-test performed.
```

**Serial Log (PDC ECU ultrasonic controller):**
```
[US_CTRL][15:30:00.001] TRIGGER: Rear burst generated. All 4 rear sensors triggered.
[US_CTRL][15:30:00.002] ECHO_WAIT: timeout=25ms. Waiting for echo...
[US_CTRL][15:30:00.027] ECHO_TIMEOUT: No echo received on any rear sensor.
[US_CTRL][15:30:00.027] DISTANCE_DECODE: echo_time=0 → distance=0 (zero code = max range)
[US_CTRL][15:30:00.027] ELECTRICAL_CHECK: transducer_drive_current=18mA (normal)
                         transducer_voltage=3.2V (normal)
[US_CTRL][15:30:00.027] NOTE: No acoustic cross-test. Cannot detect tow hitch cover.
[US_CTRL][15:30:00.027] REPORTING: fault=FALSE (electrical test passed)
[US_CTRL][15:30:00.027] REPORTING: distance=0 (no echo = open space interpretation)
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* No acoustic self-test exists. Fault is only electrical. */
static bool pdc_sensor_healthy(uint8_t sensor_id) {
    return (pdc_get_voltage(sensor_id) > 2.5f) &&   /* electrical only */
           (pdc_get_temp(sensor_id) < 85.0f);
    /* MISSING: acoustic test! */
}

static uint16_t pdc_read_distance_cm(uint8_t sensor_id) {
    uint32_t echo_us = pdc_get_echo_time_us(sensor_id);
    if (echo_us == 0u) {
        return PDC_DIST_NO_OBJECT;   /* 0 = no echo = no object. WRONG: could be blocked! */
    }
    return (uint16_t)((echo_us * 343u) / (2u * 10000u));  /* cm */
}
```

```c
/* ===== FIXED CODE ===== */

#define PDC_CONSECUTIVE_ZERO_LIMIT  3u      /* 3+ zero-echo = suspect blocked */
#define PDC_CROSS_ECHO_TIMEOUT_US   3000u   /* 3ms = ~50cm cross-echo path */

typedef struct {
    uint8_t  consecutive_zero_count;
    bool     cross_echo_received;
    bool     obstruction_suspected;
} PdcSensorState_t;

/* Method 1: Statistical — consecutive zero detection */
static void pdc_update_sensor_state(PdcSensorState_t *s, uint32_t echo_us) {
    if (echo_us == 0u) {
        s->consecutive_zero_count++;
        if (s->consecutive_zero_count >= PDC_CONSECUTIVE_ZERO_LIMIT) {
            s->obstruction_suspected = true;
        }
    } else {
        s->consecutive_zero_count = 0u;
        s->obstruction_suspected  = false;
    }
}

/* Method 2: Cross-echo validation (requires radar HW cross-listening) */
static bool pdc_cross_echo_test(uint8_t tx_sensor, uint8_t rx_neighbor) {
    pdc_trigger_single(tx_sensor);
    uint32_t cross_echo_us = pdc_wait_echo(rx_neighbor, PDC_CROSS_ECHO_TIMEOUT_US);
    return (cross_echo_us > 0u && cross_echo_us < PDC_CROSS_ECHO_TIMEOUT_US);
}

static uint16_t pdc_read_distance_cm(uint8_t sensor_id, PdcSensorState_t *state) {
    uint32_t echo_us = pdc_get_echo_time_us(sensor_id);
    pdc_update_sensor_state(state, echo_us);
    
    if (state->obstruction_suspected) {
        pdc_set_sensor_fault(sensor_id, PDC_FAULT_ACOUSTIC_OBSTRUCTION);
        hmi_display_message("PDC: Check rear sensors");
        return PDC_DIST_SENSOR_FAULT;   /* distinct from NO_OBJECT */
    }
    if (echo_us == 0u) {
        return PDC_DIST_NO_OBJECT;    /* clear of range, no obstruction suspected */
    }
    return (uint16_t)((echo_us * 343u) / (2u * 10000u));
}
```

**FMEA:**

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| PDC acoustic health | No obstruction detection | No warning when sensor blocked → collision | **8** | No acoustic self-test implemented | 5 | No test for blocked sensor | 8 | **320** |

---

## 6.3 PDC-002: AutoPark Overshoot — Tire Size Mismatch in Odometry

**CAN Log:**
```
   [AutoPark executing parallel park — target: flush with kerb, 0-5cm gap]
   0.000  0x6B0  Tx  d 4  00 50 00 02   -- Target=+80cm, maneuver=REVERSE_IN
   1.500  0x6B0  Tx  d 4  00 00 00 03   -- COMPLETE (0cm remaining by odometry)
   1.500  0x6A1  Rx  d 4  00 28 00 00   -- PDC_Rear = 40cm ← actual position!
```

**Physics / Math:**

```
ODOMETRY ERROR CALCULATION
══════════════════════════════════════════════════════════════
Wheel odometry calculates distance from wheel pulse counter:

  distance = pulse_count × (circumference / pulses_per_revolution)

Default config (225/55R17):
  circumference = π × overall_diameter
  overall_diameter = rim_diameter + 2 × sidewall
  rim_diameter = 17 × 25.4 = 431.8mm
  sidewall = section_width × aspect_ratio = 225 × 0.55 = 123.75mm
  overall_diameter = 431.8 + 2 × 123.75 = 679.3mm
  circumference_default = π × 679.3 = 2133.8mm  [WRONG for this vehicle!]

Actual fitted tire (225/60R17):
  sidewall = 225 × 0.60 = 135mm
  overall_diameter = 431.8 + 2 × 135 = 701.8mm
  circumference_actual = π × 701.8 = 2204.6mm

Odometry error per revolution:
  error = 2204.6 - 2133.8 = 70.8mm/rev = +3.3% over-distance

For 80cm AutoPark maneuver:
  actual_moved = 80cm × (2204.6 / 2133.8) = 80 × 1.033 = 82.6cm
  → Vehicle moves 2.6cm MORE than odometry expects per 80cm segment
  
For 3.0m total parking maneuver (multiple segments):
  total_error = 300 × 0.033 = 9.9cm — but this scenario had additional
  steering angle limit issue causing early stop at ~40cm gap.

REAL ISSUE: Odometry signals end-of-maneuver at calculated_displacement=80cm,
but actual_displacement=82.6cm. For kerb flush target, the final PDC
proximity check should have been the true stop criterion.
```

**Code Fix:**
```c
/* src/autopark_controller.c */

/* BEFORE: odometry-only stop criterion */
if (odometry_displacement_cm >= target_displacement_cm) {
    autopark_complete();
}

/* AFTER: PDC-fused final approach */
#define AUTOPARK_PDC_OVERRIDE_DIST_CM  30u   /* switch to PDC below 30cm */
#define AUTOPARK_TARGET_PDC_GAP_CM      3u   /* target: 3cm from kerb */

if (pdc_rear_dist_cm <= AUTOPARK_PDC_OVERRIDE_DIST_CM) {
    /* Final approach: use PDC as primary stop criterion */
    if (pdc_rear_dist_cm <= AUTOPARK_TARGET_PDC_GAP_CM) {
        autopark_complete();   /* flush with kerb */
    }
    autopark_set_speed_limit(0.3f);   /* slow down in final approach */
} else {
    /* Normal phase: odometry-guided with PDC safety monitor */
    if (odometry_displacement_cm >= target_displacement_cm) {
        autopark_complete();
    }
}

/* ALSO: Read tire size from variant coding / VIN decode */
/* src/vehicle_config.c */
float odometry_get_circumference_mm(void) {
    TireSize_t tire = vehicle_config_get_tire_size();
    float sidewall_mm = tire.section_width_mm * (tire.aspect_ratio / 100.0f);
    float od_mm = (tire.rim_diameter_inch * 25.4f) + (2.0f * sidewall_mm);
    return M_PI * od_mm;
}
```

---

## 6.4 PDC-003: Critical Alert Audio 62ms Latency — CAN Bus Congestion

**Physics Analysis:**

```
PDC CRITICAL ALERT TIMING BUDGET
══════════════════════════════════════════════════════════════
Vehicle reversing at max PDC speed (8 km/h = 2.22 m/s):
Distance traveled during alert latency:
  at 62ms: 2.22 × 0.062 = 0.14m = 14cm additional movement toward obstacle!

If obstacle is at 20cm when critical alert triggered:
  By the time chime plays, vehicle is at 20-14 = 6cm → near collision!
  SRS requires ≤20ms: distance = 2.22 × 0.020 = 0.044m = 4.4cm (still safe)

CAN MESSAGE TIMING ANALYSIS:
  PDC_Alert CAN ID: 0x6A2 (6 × 256 + 162 = decimal 1698)
  Lower CAN ID = higher priority. 0x6A2 is in the LOW-priority range.
  
  CAN arbitration: all ECUs transmit simultaneously.
  Highest priority (lowest ID) wins immediately.
  0x6A2 must wait for 0x0xx–0x5xx traffic to clear.
  
  At 87% bus load, CAN bit-stuffing and retransmits add:
  Expected worst-case delay: frame_size_bits × (1 / 500kbps) × retransmit_count
    = 110 bits × 2μs × ~40 retransmit_equivalents ≈ 8.8ms per frame
  Multiple queued high-priority frames → cascading delay to ~45ms observed.
```

**Code Fix:**
```c
/* SOLUTION 1: Change CAN ID to high-priority range */
/* Old: 0x6A2 (priority=6)  → New: 0x0A2 (priority=0, highest group) */
/* Requires DBC change and integration test of all ECUs */

/* SOLUTION 2: Pre-load audio buffer on Reverse engagement */
/* src/hmi_audio_manager.c */
void hmi_on_gear_reverse(void) {
    /* Pre-load PDC chimes to local audio buffer for zero-latency playback */
    audio_preload(AUDIO_PDC_WARN);
    audio_preload(AUDIO_PDC_CRITICAL);
    audio_preload(AUDIO_PDC_STOP);
    log_info("[HMI] PDC audio pre-loaded. Zero-latency PDC alerts ready.");
}

void hmi_on_pdc_alert(PdcAlertLevel_t level) {
    if (level == PDC_ALERT_CRITICAL) {
        audio_play_from_buffer(AUDIO_PDC_CRITICAL);  /* local buffer → no CAN round-trip */
        /* Still send CAN for logging/display — but audio doesn't wait for it */
    }
}

/* SOLUTION 3: Direct GPIO to buzzer for PDC_CRITICAL */
/* Hardware-level: ADAS ECU GPIO pin connected directly to PDC warning buzzer.
 * GPIO set in ISR triggered by PDC_Alert CAN reception → bypasses audio ECU.
 * Latency: ~2ms (GPIO toggle + buzzer response) << 20ms requirement */
```

**FMEA:**

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| PDC alert latency | 62ms > 20ms SRS | 14cm extra reverse travel at max speed before warning plays | 7 | Low CAN ID priority + 87% bus load | 5 | Latency test in isolation (not under bus load) | 6 | **210** |


---

# Part 7: ACC — Adaptive Cruise Control

## 7.1 Functional Architecture

```
ACC CONTROL LOOP (simplified):
═══════════════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────────────────┐
  │                      ACC CONTROL ARCHITECTURE                       │
  └─────────────────────────────────────────────────────────────────────┘

  INPUT PROCESSING:
    Radar (0x7B0/7B1) ──► Target Selection ──► Active Target
    Camera (0x3A2)    ──► Fusion           ──► (confirm radar)

  DISTANCE CONTROLLER (outer loop):
    SetDistance = FollowTime × EgoSpeed    [e.g., 2.0s × 100kph = 55.6m]
    DistError = SetDistance - ActualDistance
    SpeedAdjust = f(DistError, RelVel)     [PID or model-based]

  SPEED CONTROLLER (inner loop):
    SpeedError = min(DriverSetSpeed, FollowSpeed) - ActualSpeed
    Throttle/BrakeDemand = PID(SpeedError)

  OUTPUT:
    ACC_ThrottleReq (0x7C0) ──► Throttle ECU
    ACC_BrakeReq (0x7C1)    ──► Brake ECU

  STATE MACHINE:
    OFF → STANDBY → ACTIVE → OVERRIDE → FAULT
         [30kph]  [driver                [DTC]
                   released]
```

**Key DBC Signals:**
```
BO_ 1952 ACC_CONTROL: 4 ADAS_ECU
  SG_ ACC_ThrottleReq : 0|8@1+ (0.4,0) [0|100] "%" THROTTLE_ECU
  SG_ ACC_BrakeReq    : 8|8@1+ (0.1,0) [0|25]  "bar" BRAKE_ECU
  SG_ ACC_Status      : 16|3@1+ (1,0) [0|7] "" HMI_ECU
    0="OFF" 1="ACTIVE" 2="OVERRIDE" 3="FAULT" 4="STANDBY"

BO_ 1968 ACC_TARGET: 4 RADAR_F
  SG_ RadarTarget_Dist   : 0|16@1+ (0.01,0) [0|655.35] "m" ADAS_ECU
  SG_ RadarTarget_RelVel : 16|16@1+ (0.01,-327.67) [-50|50] "m/s" ADAS_ECU
```

---

## 7.2 ACC-001: No Braking for Cut-In Vehicle — New Target Lockout

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : ACC-001                                                      ║
║ Title     : ACC ignores cut-in vehicle for 500ms — no braking           ║
║ Severity  : CRITICAL            ASIL: ASIL C — ACC is ASIL C rated      ║
║ Standards : ISO 15622:2018 §5.4.3 — Response to cut-in scenario         ║
║ FuSa      : Safety goal: "ACC shall reduce speed when following gap     ║
║             decreases below minimum" — NOT met for cut-in targets        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Cut-In Kinematics

```
CUT-IN SCENARIO PHYSICS ANALYSIS
══════════════════════════════════════════════════════════════════
Setup:
  Ego vehicle:  120 km/h = 33.3 m/s  (ACC active)
  Cut-in vehicle: 88 km/h = 24.4 m/s (slower, merging)
  Relative velocity at appearance: v_rel = 33.3 - 24.4 = -8.9 m/s (closing)

Distance traveled DURING 500ms lockout:
  gap_change = v_rel × t = 8.9 × 0.500 = 4.45m gap CLOSED
  Ego also accelerating (ACC maintaining speed with throttle):
    additional_closure ≈ 0.3 m/s² × 0.5² / 2 = 0.04m
  Total gap closed: ~4.5m

If cut-in vehicle appears at 30m gap:
  After 500ms lockout: gap = 30 - 4.5 = 25.5m
  Time to reach 2.0s following gap at 33.3m/s: need 66.6m → already behind!
  ACC then suddenly needs to brake hard to reach set following distance.

If cut-in vehicle appears at 20m gap:
  After 500ms: gap = 15.5m
  TTC = 15.5 / 8.9 = 1.74s → AEB may activate!
  
CONCLUSION: 500ms lockout is acceptable only for far targets (> 80m).
For close cut-ins (< 40m), it creates a safety gap.
```

### Complete Log Triptych

**CAN Log:**
```
   0.000  0x7B0  Rx  d 4  00 00 00 00   -- No radar target
   0.000  0x7A1  Rx  d 1  01            -- ACC_Status=ACTIVE, throttle maintaining 120kph
   0.020  0x7B0  Rx  d 4  00 1E 00 00  -- NEW TARGET: distance = 30m
   0.020  0x7B1  Rx  d 4  FF D8 00 00  -- RelVel = -0.40Nm... wait: d 4 FF D8 = raw
                                         -- RelVel raw = 0xFFD8 = -0.40? No:
                                         -- signed 16-bit: 0xFFD8 = -40 → -40*0.01 = -0.40 m/s?
                                         -- Actual: 0xFC00+... let's use d 4 FC 18 = -8.9m/s
   0.020  0x7B1  Rx  d 4  FC 18 00 00  -- RelVel = raw 0xFC18 = signed = -1000 → -1000*0.01 = -10m/s
   0.020  ADAS_ECU [internal] NEW_TARGET detected. Engaging NEW_TARGET_LOCKOUT = 500ms.
   0.040  0x7C0  Tx  d 1  28           -- ThrottleReq = 40% ← still maintaining speed!
   0.040  0x7C1  Tx  d 1  00           -- BrakeReq = 0 bar ← NO braking!
   0.040  ADAS_ECU [internal] Lockout: 460ms remaining. Target ignored.
   0.060  0x7B0  Rx  d 4  00 14 00 00  -- Target now at 20m (closed 10m in 40ms!)
   0.060  0x7C1  Tx  d 1  00           -- STILL NO BRAKING
   0.080  0x7B0  Rx  d 4  00 08 00 00  -- Target at 8m! TTC = 0.8s
   0.080  0x8A0  Tx  d 1  03           -- AEB_FullBrake ACTIVATES
   0.080  0x8B0  Tx  d 2  00 C8        -- 200 bar emergency brake
```

**ECU System Log:**
```
[ACC ][T=0ms  ] No target. SetSpeed=120kph. ThrottleReq=40%.
[ACC ][T=20ms ] NEW_TARGET: dist=30m relVel=-8.9m/s conf=0.93 class=PASSENGER_CAR
[ACC ][T=20ms ] Target state: history=0 frames. NEW_TARGET_LOCKOUT activated (500ms).
[ACC ][T=20ms ] ACC_LOGIC: lockout_active=TRUE. Target ignored. ThrottleReq unchanged.
[ACC ][T=40ms ] Target: dist=20m relVel=-8.9m/s TTC=2.25s. LOCKOUT: 460ms remain.
[ACC ][T=60ms ] Target: dist=10m relVel=-8.9m/s TTC=1.12s. LOCKOUT: 440ms remain.
[AEB ][T=80ms ] TTC=0.9s < AEB_threshold=1.5s. AEB_FullBrake ACTIVATED.
[ACC ][T=80ms ] LOCKOUT still active but AEB overrides ACC control.
[ACC ][T=80ms ] SAFETY NOTE: AEB activated because ACC failed to respond to cut-in.
                This is NOT the intended architecture. ACC should handle cut-in first.
```

**Serial Log (Radar ECU):**
```
[RADAR_F][T=18ms] NEW OBJECT: id=52 range=30.4m vel_rel=-8.87m/s rcs=18.5dBsm class=CAR
[RADAR_F][T=18ms] Track history: 0 frames (brand new). Forwarding to ADAS ECU.
[RADAR_F][T=20ms] ADAS_ECU response: NEW_TARGET_LOCKOUT. Object id=52 not yet accepted.
[RADAR_F][T=20ms] Confidence already at 0.93 (excellent — multi-range-bin detection)
[RADAR_F][T=38ms] id=52: range=21.5m vel=-8.9m/s conf=0.97 (track age=2 frames, high conf)
[RADAR_F][T=56ms] id=52: range=12.8m vel=-8.7m/s conf=0.99 (track age=3 frames)
[RADAR_F][T=74ms] id=52: range=4.5m vel=-8.5m/s conf=0.99 AEB_ZONE entered
```

### Root Cause Chain (5 Whys)

```
WHY 1: ACC does not brake when cut-in vehicle appears at 30m.
  → NEW_TARGET_LOCKOUT is active. ACC ignores all new targets for 500ms.

WHY 2: Why is there a 500ms new target lockout?
  → Ghost targets and multipath reflections can appear briefly on radar.
    Without lockout, ACC would brake hard for radar phantoms.
    The lockout filters out objects that appear and disappear within 500ms.

WHY 3: Why does the lockout not have an exception for urgent targets?
  → The lockout was designed before ISO 15622:2018 revision which added
    cut-in scenario requirements. The cut-in urgency exception in ISO 15622
    §5.4.3 was not reflected in the ACC functional requirements.

WHY 4: Why was ISO 15622:2018 §5.4.3 not implemented?
  → Standards compliance review was done at SRS level, not code level.
    The SRS correctly references ISO 15622 §5.4.3 but the implementation
    team interpreted the lockout as an acceptable safety trade-off.
    No formal traceability check from ISO clause → code was done.

WHY 5: Why was there no formal traceability from standard to code?
  → Requirements traceability matrix only goes from SRS to code.
    External standard (ISO) → SRS traceability is done manually, once,
    at project start. Mid-project standard revisions are not auto-tracked.

ROOT CAUSE: ISO 15622:2018 §5.4.3 cut-in requirement not reflected in ACC
            new-target-lockout exception logic. Process gap in standard revision tracking.
CATEGORY  : Specification Gap (standard revision) + Implementation Error
SAFETY    : ASIL C safety requirement violation
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* src/acc_target_manager.c */
#define NEW_TARGET_LOCKOUT_MS  500u

static bool acc_accept_target(const RadarTarget_t *target,
                               const AccState_t *acc) {
    /* Simple age check — no urgency exception */
    if (target->track_age_frames == 0u) {
        acc_start_lockout_timer(acc, NEW_TARGET_LOCKOUT_MS);
        return false;   /* always reject new target for 500ms */
    }
    if (acc_lockout_active(acc)) {
        return false;   /* still in lockout */
    }
    return true;
}
```

```c
/* ===== FIXED CODE ===== */
/* src/acc_target_manager.c */
/* Per ISO 15622:2018 §5.4.3 — Cut-in scenario response */

#define NEW_TARGET_LOCKOUT_MS        500u   /* default lockout for unverified targets */
#define NEW_TARGET_LOCKOUT_URGENT_MS   0u   /* bypass for urgent confirmed targets */
#define CUTIN_CONF_MIN               0.88f  /* minimum confidence to bypass lockout */
#define CUTIN_RELVEL_THRESHOLD_MS   -4.0f   /* m/s: fast closure = cut-in */
#define CUTIN_TTC_THRESHOLD_S        4.0f   /* TTC threshold: must respond urgently */
#define CUTIN_WIDTH_MIN_M            1.4f   /* width: vehicle-sized (not debris) */

static bool acc_is_urgent_cutin(const RadarTarget_t *target) {
    if (target->confidence     < CUTIN_CONF_MIN)           return false;
    if (target->rel_vel_ms     >= CUTIN_RELVEL_THRESHOLD_MS) return false; /* not closing fast */
    if (target->ttc_s          > CUTIN_TTC_THRESHOLD_S)    return false;
    if (target->width_est_m    < CUTIN_WIDTH_MIN_M)        return false;  /* not vehicle-sized */
    return true;   /* confirmed: high-confidence, fast-closing vehicle-sized target */
}

static bool acc_accept_target(const RadarTarget_t *target,
                               AccState_t *acc) {
    if (target->track_age_frames == 0u) {
        if (acc_is_urgent_cutin(target)) {
            /* ISO 15622 §5.4.3: cut-in override — bypass lockout */
            log_warn("[ACC] CUTIN_OVERRIDE: new target accepted immediately. "
                     "conf=%.2f relVel=%.2f TTC=%.2f width=%.2f",
                     target->confidence, target->rel_vel_ms,
                     target->ttc_s, target->width_est_m);
            acc->cutin_override_active = true;
            return true;   /* accept immediately */
        }
        /* Normal new target: start lockout */
        uint32_t lockout_ms = (target->confidence > 0.85f) ?
                               200u :       /* high confidence: reduced lockout */
                               NEW_TARGET_LOCKOUT_MS;  /* low confidence: full lockout */
        acc_start_lockout_timer(acc, lockout_ms);
        return false;
    }
    return !acc_lockout_active(acc);
}
```

**Unified Diff:**
```diff
--- a/src/acc_target_manager.c  (v5.1.0)
+++ b/src/acc_target_manager.c  (v5.2.0)
@@ -45,10 +45,35 @@
+#define CUTIN_CONF_MIN               0.88f
+#define CUTIN_RELVEL_THRESHOLD_MS   -4.0f
+#define CUTIN_TTC_THRESHOLD_S        4.0f
+#define CUTIN_WIDTH_MIN_M            1.4f
+
+static bool acc_is_urgent_cutin(const RadarTarget_t *target) {
+    return (target->confidence   >= CUTIN_CONF_MIN)         &&
+           (target->rel_vel_ms   <  CUTIN_RELVEL_THRESHOLD_MS) &&
+           (target->ttc_s        <= CUTIN_TTC_THRESHOLD_S)  &&
+           (target->width_est_m  >= CUTIN_WIDTH_MIN_M);
+}
+
 static bool acc_accept_target(const RadarTarget_t *target,
-                               const AccState_t *acc) {
+                               AccState_t *acc) {
     if (target->track_age_frames == 0u) {
-        acc_start_lockout_timer(acc, NEW_TARGET_LOCKOUT_MS);
-        return false;
+        if (acc_is_urgent_cutin(target)) {
+            acc->cutin_override_active = true;
+            return true;
+        }
+        uint32_t lockout = (target->confidence > 0.85f) ? 200u : 500u;
+        acc_start_lockout_timer(acc, lockout);
+        return false;
     }
     return !acc_lockout_active(acc);
```

### FMEA Analysis

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| ACC new-target lockout | 500ms lockout with no urgency exception | No braking for cut-in vehicle, AEB forced to intervene | **9** | ISO 15622 §5.4.3 not implemented | 6 | Cut-in not in ACC test matrix | 7 | **378** |

### Test Cases

**TC-ACC-001-01: Cut-in at 30m — immediate braking**
```
Setup    : Ego=120kph ACC active, inject radar: new target 30m 0conf=0.95 relVel=-8.9m/s
Expected : ACC engages deceleration within 100ms (not 500ms)
KPI      : ThrottleReq→0 AND BrakeReq>0 at T+100ms max. AEB must NOT activate.
```
**TC-ACC-001-02: Cut-in at 50m — immediate braking**
```
Setup    : Same as above, target at 50m relVel=-5m/s
Expected : ACC decelerates within 100ms. Smooth deceleration (no harsh brake).
```
**TC-ACC-001-03: Ghost target — lockout still applies**
```
Setup    : Low-confidence target (conf=0.50) appears 1 frame then disappears
Expected : ACC does NOT decelerate (lockout correctly applied for low-conf)
```
**TC-ACC-001-04: Stationary cut-in (queue traffic)**
```
Setup    : New target at 20m relVel=-33m/s (ego at 120kph, target stopped)
Expected : CUTIN_OVERRIDE engaged. AEB must NOT be the first brake.
           ACC applies progressive brake starting at T+50ms.
```

---

## 7.3 ACC-002: Speed Hunting — P-Only PID Oscillation

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : ACC-002                                                      ║
║ Title     : ACC speed oscillates ±2-3 km/h — P-only controller          ║
║ Severity  : MEDIUM              ASIL: QM (comfort, not safety)           ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**Speed hunting waveform:**
```
 Vehicle Speed (kph)
 ───────────────────────────────────────────────────────────►  Time
 103 |         *                 *                 *
 102 |        * *               * *               * *
 101 |       *   *             *   *             *   *
 100 |──────*─────*───────────*─────*───────────*─────*──── SET SPEED
  99 |     *       *         *       *         *       *
  98 |    *         *       *         *       *         *
  97 |   *           *     *           *     *
     |──────────────────────────────────────────────────────
      T=0  0.2  0.4  0.6  0.8  1.0  1.2  1.4  1.6  1.8s
                    oscillation period ≈ 0.3s

ACC Throttle:  ▌▌▌▌░░▌▌▌▌░░▌▌▌▌░░  (on/off at ~3Hz)
ACC Brake:     ░░░░▌▌░░░░▌▌░░░░▌▌  (brief brake pulses)
```

**Root Cause & PID Math:**
```
Kp=18, Ki=0, Kd=0 (P-only):

Gain analysis with engine/driveline model:
  Engine time constant τ ≈ 0.15s (throttle to wheel torque)
  Vehicle mass effect: time from torque to speed ≈ 0.2s
  Combined plant delay: ~0.35s

For P-only at Kp=18:
  Phase margin at crossover frequency: ≈ 12° (needs >45° for stability)
  Gain margin: ≈ 3.5dB (needs >6dB for stability)
  → MARGINALLY UNSTABLE → oscillation observed

With PID Kp=5, Ki=0.8, Kd=2.5:
  Phase margin: ≈ 52° ✓
  Gain margin:  ≈ 12dB ✓
  Settling time: ≈ 0.8s ✓

Dead band implementation:
  if (|speed_error| < 1.0 kph): hold current throttle/brake
  → eliminates micro-corrections below perceptible threshold
```

**Code Fix:**
```c
/* src/acc_speed_controller.c */

/* NEW GAINS — validated on test track at 80/100/120/140kph */
#define ACC_KP   5.0f
#define ACC_KI   0.8f
#define ACC_KD   2.5f
#define ACC_DEAD_BAND_KPH  1.0f
#define ACC_THROTTLE_RATE_LIMIT  15.0f   /* %/100ms max throttle change */

static void acc_speed_pid(AccPidState_t *pid, float set_kph, float actual_kph) {
    float error = set_kph - actual_kph;
    
    /* Dead band: no action for small errors */
    if (fabsf(error) < ACC_DEAD_BAND_KPH) {
        pid->integrator *= 0.95f;  /* slow integrator wind-down */
        return;
    }
    
    float p_term = ACC_KP * error;
    pid->integrator = clamp(pid->integrator + ACC_KI * TS * error, -20.0f, 20.0f);
    float d_term = ACC_KD / TS * (error - pid->prev_error);
    pid->prev_error = error;
    
    float raw_output = p_term + pid->integrator + d_term;
    float output = clamp(raw_output, -25.0f, 100.0f);  /* brake or throttle range */
    
    /* Rate limiter: prevent step-changes in throttle */
    float max_delta = ACC_THROTTLE_RATE_LIMIT;
    output = clamp(output, pid->prev_output - max_delta, pid->prev_output + max_delta);
    pid->prev_output = output;
    
    if (output >= 0.0f) {
        acc_set_throttle(output);
        acc_set_brake(0.0f);
    } else {
        acc_set_throttle(0.0f);
        acc_set_brake(-output * 0.1f);  /* scale: % to bar */
    }
}
```

---

## 7.4 ACC-003: Radar Interference Causes Spurious ACC Disengagement

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : ACC-003                                                      ║
║ Title     : ACC disengages on motorway — radar RFI from oncoming vehicle ║
║ Severity  : MEDIUM              Annoyance + re-engagement needed         ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log:**
```
   0.000  0x7A1  Rx  d 1  01         -- ACC_Status = ACTIVE
   0.000  0x7B0  Rx  d 4  00 3C 00 00  -- Target: 60m
   0.020  0x7B0  Rx  d 4  FF FF 00 00  -- RadarTarget_Dist = 0xFFFF = INVALID
   0.040  0x7B0  Rx  d 4  00 50 00 00  -- Target: 80m (new or recovered?)
   0.040  0x7B0  Rx  d 4  FF FF 00 00  -- INVALID again
   0.060  0x7A1  Rx  d 1  03           -- ACC_Status = FAULT
   0.060  DTC: C1B55 — RadarSignal_Intermittent
```

**System Log:**
```
[ACC] Radar invalid frames: 2 consecutive. Limit=2. Declaring FAULT.
[ACC] DTC C1B55 set. ACC disengaged.
[RADAR] INTERFERENCE: RFI detected at 76.5GHz. Source: oncoming vehicle radar.
[RADAR] Frequency: own=76.5GHz opponent=76.5GHz. Same carrier → mutual interference.
[RADAR] Duration: 3 frames (~60ms). Cleared when vehicles pass.
[ACC] Fault latched. Must restart ACC manually.
```

**Root Cause & Fix:**
```
Issue: Fault threshold = 2 consecutive invalid frames = too strict.
       2 frames × 20ms = 40ms. Transient RFI lasts 60ms → fault declared.

ISO 15622 §5.4.2: ACC shall maintain state through temporary sensor loss
using "dead reckoning" (kinematic prediction) for ≤ 500ms.

Fix 1: Increase fault threshold from 2 → 10 consecutive frames (200ms).
Fix 2: Implement kinematic prediction for target loss < 200ms:
  predicted_dist = last_dist + last_relvel × dt
  
Fix 3: FHSS (Frequency-Hopping Spread Spectrum) — radar supplier feature.
  Modern 77GHz radars use FHSS to avoid inter-vehicle interference.
  Request supplier firmware update to enable FHSS mode.
```

```c
/* src/acc_target_manager.c — kinematic prediction */

typedef struct {
    float last_dist_m;
    float last_relvel_ms;
    uint32_t loss_start_ms;
    bool prediction_active;
} AccTargetKinematics_t;

static float acc_predict_distance(AccTargetKinematics_t *k, uint32_t now_ms) {
    float dt = (now_ms - k->loss_start_ms) / 1000.0f;
    return k->last_dist_m + k->last_relvel_ms * dt;
}

/* In main target processing loop: */
if (radar_target_valid) {
    kinematics.last_dist_m  = target->dist_m;
    kinematics.last_relvel_ms = target->relvel_ms;
    kinematics.loss_start_ms = 0u;
    kinematics.prediction_active = false;
    acc_use_target(target);
} else {
    if (!kinematics.prediction_active) {
        kinematics.loss_start_ms = now_ms;
        kinematics.prediction_active = true;
    }
    uint32_t loss_duration = now_ms - kinematics.loss_start_ms;
    if (loss_duration < 200u) {   /* ISO 15622: up to 500ms prediction */
        float pred_dist = acc_predict_distance(&kinematics, now_ms);
        acc_use_predicted_target(pred_dist, kinematics.last_relvel_ms);
        log_debug("[ACC] Target predicted: dist=%.1fm (loss_dur=%ums)", pred_dist, loss_duration);
    } else {
        acc_set_fault(DTC_C1B55);  /* genuine loss after 200ms */
    }
}
```

**FMEA:**

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| Radar intermittent | 2-frame threshold → ACC disengages on RFI | Driver annoyance; must re-engage ACC | 5 | Strict fault threshold without prediction | 8 | No RFI scenario in test | 6 | **240** |

---

# Part 8: AEB — Autonomous Emergency Braking

## 8.1 Functional Architecture & Safety Classification

```
AEB is the HIGHEST-PRIORITY safety feature in the vehicle.
ASIL D (highest functional safety level per ISO 26262).
Any bug in AEB has the highest possible safety impact.

AEB STATE MACHINE:
═══════════════════════════════════════════════════════════
  [Ignition] ──► INIT ──► ARMED ─────────────────────────┐
                           │                              │
                    TTC < FCW_thresh                      │ fault/DTC
                           │                              │
                           ▼                              │
                        FCW_ACTIVE ──────────────────────►│
                           │                              │
                    TTC < PREBRAKE_thresh                 ▼
                           │                          FAULT
                           ▼                              ▲
                        PREBRAKE (0.3g) ─────────────────►│
                           │                              │
                    TTC < FULLBRAKE_thresh                 │
                           │                              │
                           ▼                              │
                        FULLBRAKE (1.0g) ─────────────────┘
                           │
                    v < 3kph OR driver brake > 5bar
                           │
                           ▼
                        COMPLETE → ARMED

Default thresholds (INCORRECT at high speed — see AEB-001):
  FCW     : TTC < 1.8s   ← FIXED VALUE, SPEED-INDEPENDENT BUG
  PreBrake: TTC < 1.5s
  FullBrake: TTC < 1.2s
```

---

## 8.2 AEB-001: Fixed TTC Threshold — Insufficient at High Speeds

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : AEB-001                                                      ║
║ SAFETY    : ██████████ MAXIMUM SEVERITY — ASIL D VIOLATION ████████████ ║
║ Title     : AEB FCW threshold fixed at 1.8s — fails at speed > 80kph   ║
║ Severity  : 10/10 — Safety of life                                       ║
║ Standards : ISO 22737:2021 §5.3 — AEB performance requirements          ║
║             Euro NCAP AEB 2026 — Statutory test                         ║
║ FuSa      : Safety Goal SG-AEB-01 violated: "Prevent or mitigate        ║
║             front collision with adequate advance warning"               ║
║ Action    : STOP DELIVERY. IMMEDIATE PATCH. FuSa NCR required.          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Complete Physics Analysis

```
MINIMUM SAFE TTC DERIVATION
═══════════════════════════════════════════════════════════════════════════

Scenario: ego vehicle approaches stationary obstacle.

PHASE 1 — Driver reaction (from FCW warning to foot on brake):
  t_reaction = 1.5s (NHTSA standard human reaction time)
  d_reaction = v₀ × t_reaction

PHASE 2 — Brake application (foot pressure builds):
  t_brake_build = 0.2s (typical for alert driver)
  d_brake_build = v₀ × t_brake_build - 0.5 × a_partial × t_brake_build²

PHASE 3 — Full braking to stop (from v₀ with a = 9.81 m/s²):
  d_stop = v₀² / (2 × a_max)   where a_max = 9.81 m/s² = 1.0g

TOTAL REQUIRED DISTANCE:
  d_total ≈ v₀ × (t_reaction + t_brake_build) + v₀² / (2 × a_max)
           = v₀ × 1.7 + v₀² / 19.62

MINIMUM SAFE TTC FOR FCW:
  TTC_fcw_min = d_total / v₀ = 1.7 + v₀ / (2 × a_max)
                              = 1.7 + v₀ / 19.62

SPEED-BY-SPEED ANALYSIS:
  ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
  │Speed     │ d_react  │ d_brake  │ d_total  │TTC_req   │Current  │
  │ (kph)    │   (m)    │   (m)    │   (m)    │  (s)     │TTC (s)  │
  ├──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
  │  50kph   │  23.6    │  9.9     │  33.5    │  2.4s    │  1.8s ✗ │
  │  60kph   │  28.3    │  14.3    │  42.6    │  2.6s    │  1.8s ✗ │
  │  80kph   │  37.8    │  25.3    │  63.1    │  2.8s    │  1.8s ✗ │
  │ 100kph   │  47.2    │  39.6    │  86.8    │  3.1s    │  1.8s ✗ │
  │ 120kph   │  56.7    │  57.0    │ 113.7    │  3.4s    │  1.8s ✗ │
  │ 130kph   │  61.4    │  66.9    │ 128.3    │  3.6s    │  1.8s ✗ │
  └──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
  
  CONCLUSION: Current 1.8s fixed TTC is UNSAFE at ALL speeds above 50kph.
              At 120kph: deficit = 3.4 - 1.8 = 1.6s = 14.8m stopping margin MISSING.
```

### Complete Log Triptych

**CAN Log:**
```
   0.000  0x7B0  Rx  d 4  00 C8 00 00   -- Target at 200m (stationary lorry, motorway queue)
   0.000  0x020  Rx  d 2  00 78          -- Ego speed = 120 km/h = 33.3 m/s
   0.000  0x8A0  Tx  d 1  01             -- AEB_Status = ARMED
   0.000  0x8A1  Tx  d 2  18 00          -- TTC = 6000ms (200m / 33.3m/s = 6.0s)
   0.000  0x8A2  Tx  d 1  00             -- FCW NOT active (6.0s > 1.8s)
   1.000  0x7B0  Rx  d 4  00 64 00 00   -- Target at 100m (1s of closing)
   1.000  0x8A1  Tx  d 2  0B B8          -- TTC = 3000ms
   1.000  0x8A2  Tx  d 1  00             -- FCW STILL OFF (3.0s > 1.8s)  ← UNSAFE at 120kph!
   1.500  0x7B0  Rx  d 4  00 32 00 00   -- Target at 50m
   1.500  0x8A1  Tx  d 2  05 DC          -- TTC = 1500ms
   1.500  0x8A2  Tx  d 1  01             -- FCW NOW ACTIVE (1.5s < 1.8s)  ← ONLY 50m away!
   1.700  0x8A0  Tx  d 1  02             -- AEB_PreBrake (200ms after FCW — driver has 0 time)
   1.900  0x8A0  Tx  d 1  03             -- AEB_FullBrake
   2.000  0x8B0  Tx  d 2  00 C8          -- Brake 200 bar
   2.100  [IMPACT at low speed ~15kph — collision mitigated but NOT avoided]
```

**ECU System Log:**
```
[AEB][T=0.000] TTC=6.00s. State=ARMED. FCW_threshold=1.8s (FIXED). Status: monitoring.
[AEB][T=1.000] TTC=3.00s. State=ARMED. FCW not triggered (3.0 > 1.8).
[AEB][T=1.000] PHYSICS_CHECK: At 120kph, required TTC_fcw = 3.4s. DEFICIT = 0.4s. [NOT LOGGED normally]
[AEB][T=1.500] TTC=1.50s. FCW_TRIGGERED. Distance=50m.
[AEB][T=1.500] Available stopping distance: 50m. Required: 113.7m. DEFICIT: 63.7m!
[AEB][T=1.700] TTC=1.30s. AEB_PREBRAKE. 0.3g.
[AEB][T=1.900] TTC=0.90s. AEB_FULLBRAKE. 1.0g.
[AEB][T=2.000] Deceleration: 33.3m/s → ~4m/s in 0.1s at 1.0g. 18cm gap remaining.
[AEB][T=2.100] IMPACT at 4m/s (~14kph). Collision mitigated, not avoided.
[AEB][DIAG   ] ROOT_CAUSE: FCW_TTC_threshold=1.8s is not speed-adaptive.
               Required at 120kph: 3.4s. Missing 1.6s = 53m of warning distance.
```

**Serial Log (AEB algorithm debug):**
```
[AEB_ALG][T=0.000] v_ego=33.3m/s. Computing FCW threshold...
[AEB_ALG][T=0.000] FCW_THRESHOLD = 1.8f; (HARDCODED CONSTANT — bug here)
[AEB_ALG][T=0.000] Required (physics): 1.7 + 33.3/19.62 = 1.7 + 1.70 = 3.4s
[AEB_ALG][T=0.000] Using hardcoded 1.8s instead of 3.4s — 1.6s deficit at this speed!
[AEB_ALG][T=1.000] dist=100m TTC=3.0s. 3.0 > 1.8 → no FCW. (Should warn at TTC<3.4s = dist<113m)
[AEB_ALG][T=1.500] dist=50m TTC=1.5s. 1.5 < 1.8 → FCW active. (50m available, 113m needed)
[AEB_ALG][T=1.500] COMPUTED_STOPPING_DIST_FROM_FCW = 50m. REQUIRED = 113.7m. MISS = 63.7m.
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* src/aeb_controller.c */

/* CRITICAL BUG: Fixed TTC thresholds regardless of vehicle speed */
#define AEB_TTC_FCW_S        1.8f   /* UNSAFE: should be speed-adaptive */
#define AEB_TTC_PREBRAKE_S   1.5f
#define AEB_TTC_FULLBRAKE_S  1.2f

static AebState_t aeb_evaluate(float ttc_s, float ego_speed_ms,
                                float collision_prob) {
    if (ttc_s < AEB_TTC_FULLBRAKE_S && collision_prob > 0.8f) {
        return AEB_STATE_FULLBRAKE;
    }
    if (ttc_s < AEB_TTC_PREBRAKE_S && collision_prob > 0.7f) {
        return AEB_STATE_PREBRAKE;
    }
    if (ttc_s < AEB_TTC_FCW_S && collision_prob > 0.6f) {   /* BUG: 1.8s fixed */
        return AEB_STATE_FCW;
    }
    return AEB_STATE_ARMED;
}
```

```c
/* ===== FIXED CODE ===== */
/* src/aeb_controller.c */

/* AEB WARNING THRESHOLDS — speed-adaptive per ISO 22737:2021 §5.3 */

/* Constants based on human factors study (NHTSA + Euro NCAP) */
#define AEB_REACTION_TIME_S    1.70f   /* reaction + brake build-up: 1.5 + 0.2s */
#define AEB_MAX_DECEL_MS2      9.81f   /* 1.0g maximum braking */

/* Speed-adaptive FCW threshold: TTC_fcw(v) = reaction_time + v / (2 × a_max) */
static float aeb_fcw_ttc_threshold(float ego_speed_ms) {
    float ttc_min = AEB_REACTION_TIME_S + ego_speed_ms / (2.0f * AEB_MAX_DECEL_MS2);
    /* Clamp to sensible range: min 1.8s (low speed), max 4.5s (very high speed) */
    return clampf(ttc_min, 1.8f, 4.5f);
}

/* Pre-brake: give 0.3s for FCW to reach driver before AEB intervenes */
static float aeb_prebrake_ttc_threshold(float ego_speed_ms) {
    return aeb_fcw_ttc_threshold(ego_speed_ms) - 0.3f;
}

/* Full brake: another 0.2s after pre-brake */
static float aeb_fullbrake_ttc_threshold(float ego_speed_ms) {
    return aeb_prebrake_ttc_threshold(ego_speed_ms) - 0.2f;
}

static AebState_t aeb_evaluate(float ttc_s, float ego_speed_ms,
                                float collision_prob) {
    float ttc_fcw      = aeb_fcw_ttc_threshold(ego_speed_ms);
    float ttc_prebrake = aeb_prebrake_ttc_threshold(ego_speed_ms);
    float ttc_fullbrk  = aeb_fullbrake_ttc_threshold(ego_speed_ms);

    if (ttc_s < ttc_fullbrk && collision_prob > 0.80f) {
        return AEB_STATE_FULLBRAKE;
    }
    if (ttc_s < ttc_prebrake && collision_prob > 0.70f) {
        return AEB_STATE_PREBRAKE;
    }
    if (ttc_s < ttc_fcw && collision_prob > 0.60f) {
        log_info("[AEB] FCW triggered: TTC=%.2f threshold=%.2f speed=%.1fkph",
                 ttc_s, ttc_fcw, ego_speed_ms * 3.6f);
        return AEB_STATE_FCW;
    }
    return AEB_STATE_ARMED;
}
```

**Unified Diff:**
```diff
--- a/src/aeb_controller.c (v5.1.0 — CRITICAL BUG)
+++ b/src/aeb_controller.c (v5.2.0 — FIXED)
@@ -28,14 +28,32 @@
-#define AEB_TTC_FCW_S      1.8f   /* UNSAFE: fixed value */
-#define AEB_TTC_PREBRAKE_S 1.5f
-#define AEB_TTC_FULLBRAKE_S 1.2f
+#define AEB_REACTION_TIME_S  1.70f
+#define AEB_MAX_DECEL_MS2    9.81f
+
+static float aeb_fcw_ttc_threshold(float v_ms) {
+    return clampf(AEB_REACTION_TIME_S + v_ms / (2.0f * AEB_MAX_DECEL_MS2),
+                  1.8f, 4.5f);
+}
+static float aeb_prebrake_ttc_threshold(float v_ms) {
+    return aeb_fcw_ttc_threshold(v_ms) - 0.3f;
+}
+static float aeb_fullbrake_ttc_threshold(float v_ms) {
+    return aeb_prebrake_ttc_threshold(v_ms) - 0.2f;
+}

 static AebState_t aeb_evaluate(float ttc_s, float ego_speed_ms,
                                 float collision_prob) {
-    if (ttc_s < AEB_TTC_FULLBRAKE_S  && collision_prob > 0.8f) return AEB_STATE_FULLBRAKE;
-    if (ttc_s < AEB_TTC_PREBRAKE_S   && collision_prob > 0.7f) return AEB_STATE_PREBRAKE;
-    if (ttc_s < AEB_TTC_FCW_S        && collision_prob > 0.6f) return AEB_STATE_FCW;
+    if (ttc_s < aeb_fullbrake_ttc_threshold(ego_speed_ms) && collision_prob > 0.8f) return AEB_STATE_FULLBRAKE;
+    if (ttc_s < aeb_prebrake_ttc_threshold(ego_speed_ms)  && collision_prob > 0.7f) return AEB_STATE_PREBRAKE;
+    if (ttc_s < aeb_fcw_ttc_threshold(ego_speed_ms)       && collision_prob > 0.6f) return AEB_STATE_FCW;
     return AEB_STATE_ARMED;
 }
```

### FMEA Analysis

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| AEB FCW threshold | Fixed 1.8s TTC at all speeds | FCW fires too late at high speed; collision not avoidable | **10** | Hardcoded constant, no physics model | 7 | Only low-speed AEB tests in regression | 9 | **630** |

**RPN = 630 → STOP DELIVERY. Safety Non-Conformance Report mandatory.**

### Test Cases

**TC-AEB-001-01: Speed-adaptive FCW timing at 60kph**
```
Setup    : Ego=60kph, stationary target at 200m
Expected : FCW activates at TTC≤2.6s (dist≤43m). Not at 1.8s (30m).
KPI      : FCW_dist ≥ 42m. AEB must avoid collision.
Automation: SIL + HIL + Vehicle (mandatory for NCAP submission)
```
**TC-AEB-001-02: Speed-adaptive FCW at 120kph**
```
Setup    : Ego=120kph, stationary target at 300m
Expected : FCW activates at TTC≤3.4s (dist≤113m)
KPI      : FCW_dist ≥ 110m. Full stop before target. AEB_FullBrake not needed.
```
**TC-AEB-001-03: NCAP car-to-stationary protocol (mandatory)**
```
Protocol : Euro NCAP AEB 2026 §3.1.1 — C2S test
Speeds   : 20, 40, 60, 80kph
Expected : Collision avoided at ALL speeds with speed-adaptive thresholds
Pass     : 100% avoidance rate at all test speeds
```
**TC-AEB-001-04: No false positive at low speed**
```
Setup    : 30kph, stationary parked car at 15m (parking scenario)
Expected : FCW triggers (2.6s needed, 1.8s absolute minimum — apply 1.8s floor)
           But NOT AEB_FullBrake for a normal parking approach
```

---

## 8.3 AEB-002: False Braking on Overhead Gantry — Elevation Filter Missing

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : AEB-002                                                      ║
║ Title     : AEB full brake on motorway — overhead sign gantry           ║
║ Severity  : HIGH                False positive — rear-end collision risk ║
║ Standards : Euro NCAP AEB false positive protocol                        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log:**
```
   0.000  0x7B0  Rx  d 4  00 32 00 00   -- Target at 50m
   0.000  0x7B2  Rx  d 4  00 0C 00 00   -- Radar elevation: +12° (raw=0x000C=12 degrees)
   0.000  0x8A3  Rx  d 1  60            -- CollisionProbability = 96%
   0.000  0x8A1  Tx  d 2  00 C8          -- TTC = 200ms (VERY short — stationary, ego moving fast)
   0.002  0x8A0  Tx  d 1  03             -- AEB_FULLBRAKE (no FCW first — straight to full!)
   0.002  0x8B0  Tx  d 2  00 C8          -- 200 bar emergency brake at 110kph!
   0.040  0x7B0  Rx  d 4  00 00 00 00   -- Target gone (passed under gantry)
   0.040  0x8A0  Tx  d 1  01             -- AEB releases (too late — severe deceleration occurred)
```

**System Log:**
```
[AEB] Target: dist=50m rcs=35dBsm elevation=+12° relVel=-33.3m/s (ego speed, target stationary)
[AEB] TTC = 50/33.3 = 1.5s. Threshold at 110kph = 3.3s → WELL ABOVE threshold.
[AEB] CollisionProb=96%. AEB_FULLBRAKE triggered.
[AEB] ELEVATION_CHECK: elevation=+12°. Object_height_est = 50×tan(12°) = 10.6m
[AEB] ELEVATION_FILTER: DISABLED IN AEB PATH (only in ACC path)
[AEB] BUG: elevation check exists in ACC target filter but not AEB. Code paths diverged.
[CAM] Object classification: OVERHEAD_INFRASTRUCTURE (CNN classifier, conf=0.97)
[FUSION] Camera: OVERHEAD. Radar: COLLISION_OBJECT. AEB uses RADAR_ONLY path.
[FUSION] BUG: Camera classification not consulted in AEB trigger.
```

**Root Cause:**
```
Two independent bugs:

BUG 1: Radar elevation filter not in AEB trigger path.
  ACC target filter has elevation check: if (elevation > 5°) → likely overhead.
  But AEB trigger path does NOT call the elevation filter.
  Both call radar_get_target() but via different code paths — ACC version includes
  elevation filter, AEB version does not.

BUG 2: Camera sensor fusion not consulted in AEB trigger.
  Camera correctly classifies as OVERHEAD_INFRASTRUCTURE (CNN trained on gantries).
  AEB decision engine reads: if (radar_collision_prob > threshold) → brake.
  It does not check camera object_class before triggering.

Root: AEB and ACC share radar but have separate processing pipelines.
      A feature (elevation check) was added to ACC but not backported to AEB.
      Lack of shared target classification layer between ACC and AEB.
```

**Code Fix:**
```c
/* SHARED TARGET CLASSIFICATION LAYER — new abstraction */
/* src/adas_target_classifier.c */

typedef enum {
    TARGET_CLASS_UNKNOWN    = 0,
    TARGET_CLASS_VEHICLE    = 1,   /* car, truck, motorcycle */
    TARGET_CLASS_VRU        = 2,   /* pedestrian, cyclist */
    TARGET_CLASS_OVERHEAD   = 3,   /* sign, bridge — NOT in collision path */
    TARGET_CLASS_STATIC     = 4,   /* guardrail, parked (may be collision risk) */
} TargetClass_t;

TargetClass_t classify_target(const RadarTarget_t *radar,
                               const CameraTarget_t *cam) {
    /* Priority 1: Camera says overhead — override radar */
    if (cam != NULL && cam->object_class == CAM_CLASS_OVERHEAD_INFRA) {
        return TARGET_CLASS_OVERHEAD;
    }
    /* Priority 2: Radar elevation check */
    float height_est = radar->range_m * tanf(DEG_TO_RAD(radar->elevation_deg));
    if (radar->elevation_deg > 5.0f && height_est > 3.5f) {
        return TARGET_CLASS_OVERHEAD;  /* above vehicle height */
    }
    /* Priority 3: Static filter */
    if (fabsf(radar->ground_velocity_ms) < 2.0f && radar->range_m > 5.0f) {
        return TARGET_CLASS_STATIC;
    }
    return TARGET_CLASS_VEHICLE;
}

/* AEB trigger — now uses shared classifier */
static AebState_t aeb_evaluate(...) {
    TargetClass_t tgt_class = classify_target(radar_target, camera_target);
    
    if (tgt_class == TARGET_CLASS_OVERHEAD) {
        return AEB_STATE_ARMED;   /* do NOT brake for overhead infrastructure */
    }
    /* ... proceed with TTC evaluation ... */
}
```

**FMEA:**

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| AEB elevation filter | Missing in AEB path → false brake on gantry | Emergency brake at 110kph → rear collision risk | 8 | ACC filter not shared with AEB | 5 | No gantry test in AEB suite | 7 | **280** |

---

## 8.4 AEB-003: AEB Disabled by Startup Timing Race — ECU Initialization

```
╔══════════════════════════════════════════════════════════════════════════╗
║ DEFECT ID : AEB-003                                                      ║
║ Title     : AEB disabled for entire drive cycle — startup timing race   ║
║ Severity  : HIGH                AEB unavailable = safety loss            ║
║ Standards : ISO 26262-5 §8 — HW/SW startup timing requirements          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**CAN Log:**
```
   [IGNITION ON — T=0]
   0.150  0x8A0  Tx  d 1  04             -- AEB_Status = FAULT (150ms after ignition!)
   0.150  DTC: C1C88 — AEB_RadarComm_Fault stored + latched
   0.152  0x8A0  Tx  d 1  00             -- AEB_Status = OFF (disabled for drive cycle)
   0.200  0x7B0  Rx  d 4  00 00 00 00   -- First valid radar frame (at T=180ms)
   0.200  ADAS_ECU: Radar comm now established. But AEB already latched as FAULT.
   -- AEB unavailable for entire trip until ignition cycle.
```

**System Log:**
```
[AEB_INIT][T=0ms  ] Startup self-test initiated. Checking all subsystems.
[AEB_INIT][T=150ms] RADAR_COMM_CHECK: timeout at 150ms. No valid frame received.
[AEB_INIT][T=150ms] DTC C1C88 SET: AEB_RadarComm_Fault (latched, non-volatile).
[AEB_INIT][T=150ms] AEB_Status = FAULT. AEB disabled for this drive cycle.
[RADAR   ][T=180ms] INIT_COMPLETE: First valid CAN frame transmitted. (30ms LATE)
[AEB_INIT][T=200ms] Radar comm received. But fault already latched.
[AEB_INIT][T=200ms] NOTE: DTC C1C88 latched. AEB cannot re-enable without power cycle.
[AEB_INIT][NOTE   ] Timing check: radar_init=180ms, aeb_check_at=150ms. GAP=30ms.
```

**Serial Log (Radar ECU boot debug):**
```
[RADAR_HW][T=0ms  ] Power applied. MCU boot started.
[RADAR_HW][T=50ms ] MCU ROM + RAM init complete.
[RADAR_HW][T=80ms ] RTOS scheduler started. Application loading.
[RADAR_HW][T=120ms] CAN peripheral initialized. Node address set.
[RADAR_HW][T=150ms] FMCW signal chain calibration. Chirp parameters loading.
[RADAR_HW][T=180ms] READY. Sending startup announcement on CAN 0x7B0.
[RADAR_HW][T=180ms] AEB_INIT check window already expired 30ms ago!
```

### Root Cause Chain (5 Whys)

```
WHY 1: AEB disabled at startup.
  → DTC C1C88 (Radar not responding) set during startup and latched.

WHY 2: Why is DTC C1C88 set?
  → AEB checks for radar communication at T=150ms after ignition.
    Radar is not ready until T=180ms. Check fires 30ms too early.

WHY 3: Why does AEB check at 150ms when radar needs 180ms?
  → The AEB startup check timeout (150ms) was derived from an older radar module
    specification (Bosch SRR-1, init time 120ms). The current radar (Bosch SRR-3,
    init time 180ms) was introduced in a hardware revision without updating AEB timing.

WHY 4: Why was AEB timing not updated with the hardware change?
  → Hardware ECR (Engineering Change Request) for radar upgrade did not include
    a software impact analysis. The timing dependency was not documented in the
    Interface Control Document — it was an implicit assumption.

WHY 5: Why is the timing dependency not in the ICD?
  → The ICD documents CAN signal formats but not boot timing requirements.
    Boot sequencing is treated as a hardware integration concern,
    not a software interface requirement.

ROOT CAUSE: Radar hardware upgrade (SRR-1 → SRR-3) increased init time 120ms→180ms.
            AEB check timeout not updated. Boot timing dependency not in ICD.
CATEGORY  : Timing Race Condition + Process Gap (HW ECR without SW impact analysis)
```

### Code-Level Analysis

```c
/* ===== BUGGY CODE ===== */
/* src/aeb_startup.c */
#define AEB_RADAR_COMM_TIMEOUT_MS  150u    /* STALE: set for old radar (120ms + margin) */
#define AEB_FAULT_LATCH_POLICY     FAULT_LATCH_PERMANENT   /* never recovers! */

static void aeb_startup_check(void) {
    uint32_t start_ms = get_sys_time_ms();
    while ((get_sys_time_ms() - start_ms) < AEB_RADAR_COMM_TIMEOUT_MS) {
        if (radar_comm_valid()) {
            return;   /* OK */
        }
        task_delay_ms(5);
    }
    /* Timeout — set fault */
    set_dtc_latched(DTC_C1C88);   /* BUG: latched! */
    aeb_set_state(AEB_STATE_FAULT);
    aeb_disable_for_drive_cycle();
}
```

```c
/* ===== FIXED CODE ===== */
/* src/aeb_startup.c */

/* Radar init time is documented per module variant in vehicle config */
#define AEB_RADAR_COMM_TIMEOUT_MARGIN_MS   100u    /* 100ms margin above radar init */
#define AEB_STARTUP_WINDOW_MS             1000u    /* re-check within 1s startup window */

static void aeb_startup_check(void) {
    uint32_t radar_init_time_ms = vehicle_config_get_radar_init_time_ms();
    uint32_t check_timeout_ms   = radar_init_time_ms + AEB_RADAR_COMM_TIMEOUT_MARGIN_MS;
    /* For SRR-3: 180 + 100 = 280ms. For SRR-1: 120 + 100 = 220ms. */
    
    uint32_t start_ms = get_sys_time_ms();
    while ((get_sys_time_ms() - start_ms) < check_timeout_ms) {
        if (radar_comm_valid()) {
            log_info("[AEB] Radar comm established at T+%ums. AEB ARMED.",
                     get_sys_time_ms() - start_ms);
            aeb_set_state(AEB_STATE_ARMED);
            return;
        }
        task_delay_ms(5);
    }
    
    /* Fault — but use NON-LATCH for startup window */
    /* Re-evaluate if radar comm establishes within 1s of ignition */
    set_dtc_non_latch(DTC_C1C88);
    aeb_set_state(AEB_STATE_FAULT);
    
    /* Schedule re-check: if radar comes up late, recover */
    aeb_schedule_recovery_check(AEB_STARTUP_WINDOW_MS);
}

static void aeb_recovery_check(void) {
    /* Called at T+1000ms if fault was set during startup */
    if (radar_comm_valid() && dtc_get_age_ms(DTC_C1C88) < AEB_STARTUP_WINDOW_MS) {
        log_info("[AEB] Startup fault recovered: radar comm now valid. Clearing C1C88.");
        clear_dtc(DTC_C1C88);
        aeb_set_state(AEB_STATE_ARMED);
    }
}
```

**FMEA:**

| Item | Failure Mode | Effect | S | Cause | O | Controls | D | **RPN** |
|---|---|---|---|---|---|---|---|---|
| AEB startup timing | False DTC at startup → AEB disabled all drive | Safety feature unavailable without driver knowing | 8 | HW upgrade not reflected in SW timing | 6 | AEB readiness not checked in production EOL | 7 | **336** |

### Test Cases

**TC-AEB-003-01: Cold start — AEB ARMED within 5s**
```
Setup    : Cold ignition (ECU off > 30min)
Expected : AEB_Status = ARMED within 5s of ignition
KPI      : AEB_Status ≠ FAULT after T+5s in ANY ignition cycle
Automation: Automated power-cycle test (10 cycles minimum)
```
**TC-AEB-003-02: Power-cycle regression (20 cycles)**
```
Setup    : Power cycle 20 times consecutively
Expected : AEB ARMED in all 20 cycles. Zero FAULT latches.
KPI      : 0 faults in 20 power cycles
```
**TC-AEB-003-03: Late radar init simulation**
```
Setup    : Simulate radar delayed to 250ms (via hardware test adapter)
Expected : AEB waits until T+280ms, then ARMED (not FAULT)
```


---

# APPENDICES

---

## Appendix A: FMEA Master Table — All Defects Ranked by RPN

### Complete RPN Ranking (All 21 Defects)

| Rank | ID | Feature | Failure Mode Summary | S | O | D | **RPN** | Action |
|---|---|---|---|---|---|---|---|---|
| 1 | BSD-001 | BSD | Motorcycle not detected (RCS < threshold) | 10 | 8 | 9 | **720** | STOP DELIVERY |
| 2 | AEB-001 | AEB | Fixed TTC threshold — unsafe at high speed | 10 | 7 | 9 | **630** | STOP DELIVERY |
| 3 | LDW-002 | LDW | SRS §3.1.7 imminent override not implemented | 9 | 6 | 8 | **432** | Immediate fix |
| 4 | LDW-001 | LDW | DBC constant swap → suppresses wrong direction | 7 | 8 | 7 | **392** | Immediate fix |
| 5 | ACC-001 | ACC | 500ms lockout no cut-in exception | 9 | 6 | 7 | **378** | Immediate fix |
| 6 | AEB-003 | AEB | Startup timing race → AEB disabled (latched) | 8 | 6 | 7 | **336** | High priority |
| 7 | LKA-001 | LKA | Hysteresis chattering at threshold | 8 | 6 | 7 | **336** | High priority |
| 8 | LKA-002 | LKA | EPS rejection undetected for 50ms | 9 | 5 | 8 | **360** | High priority |
| 9 | PDC-001 | PDC | Blocked sensor not detected | 8 | 5 | 8 | **320** | High priority |
| 10 | BSD-002 | BSD | Static filter disabled in production | 6 | 8 | 6 | **288** | Medium priority |
| 11 | AEB-002 | AEB | False brake on overhead gantry | 8 | 5 | 7 | **280** | Medium priority |
| 12 | TSR-001 | TSR | Stale sign 60s after road type change | 6 | 7 | 7 | **294** | Medium priority |
| 13 | ACC-003 | ACC | Radar RFI → ACC disengages every encounter | 5 | 8 | 6 | **240** | Normal sprint |
| 14 | LKA-003 | LKA | PID overshoot clamp sign inversion | 7 | 6 | 6 | **252** | Normal sprint |
| 15 | LDW-003 | LDW | 298ms latency vs 150ms SRS | 7 | 7 | 5 | **245** | Normal sprint |
| 16 | TSR-002 | TSR | Variable sign overrides map limit | 5 | 7 | 6 | **210** | Normal sprint |
| 17 | ACC-002 | ACC | Speed hunting P-only PID | 5 | 7 | 6 | **210** | Normal sprint |
| 18 | PDC-003 | PDC | 62ms alert latency (20ms SRS) | 7 | 5 | 6 | **210** | Normal sprint |
| 19 | PDC-002 | PDC | Tire size odometry overshoot | 5 | 5 | 6 | **150** | Normal sprint |
| 20 | TSR-003 | TSR | Zero km/h shown in tunnel | 4 | 6 | 5 | **120** | Normal sprint |
| 21 | BSD-003 | BSD | 2s mirror LED timeout vs 500ms SRS | 4 | 7 | 4 | **112** | Normal sprint |

### Immediate Action Required (RPN > 400 or Severity = 10)

**BSD-001 (RPN=720) — Safety NCR Required:**
- VRU detection below minimum RCS threshold
- Euro NCAP 2026 motorcycle BSD test failure
- Action: Implement multi-feature classifier (width + velocity + RCS)
- Owner: BSD SW team + Radar supplier alignment on threshold
- Target: 2 sprints

**AEB-001 (RPN=630) — Safety NCR Required:**
- Fixed TTC threshold is unsafe at all speeds > 50kph
- ISO 22737 and NCAP AEB test failure
- Action: Implement speed-adaptive TTC formula
- Owner: AEB Safety SW team (ASIL D qualified engineers only)
- Target: 1 sprint (critical)

**LDW-002 (RPN=432) — Immediate Fix:**
- SRS §3.1.7 imminent override unimplemented
- Action: Implement `ldw_imminent_departure_override()`
- Target: This sprint

**LDW-001 (RPN=392) — Immediate Fix:**
- DBC constant swap causes BOTH false warnings AND missed warnings
- Action: Correct constants + add CI DBC validation
- Target: This sprint

---

## Appendix B: Complete DTC Reference

| DTC Code | Description | Feature | Fault Type | Latch Policy | Clear Condition |
|---|---|---|---|---|---|
| C1A42 | EPS_NotResponding_LKA | LKA | Communication | Non-latch | EPS responds within 500ms |
| C1A43 | LKA_TorqueExceeded | LKA | Mechanical limit | Latch | Ignition cycle + no recurrence |
| C1A44 | LKA_CamStatus_Error | LKA | Sensor | Non-latch | Camera recovers for 5 consecutive frames |
| C1B50 | LDW_LaneConf_LowPermanent | LDW | Sensor quality | Non-latch | Confidence > 70% for 10s |
| C1B51 | LDW_Latency_Exceeded | LDW | Performance | Non-latch | Latency < 150ms for 50 consecutive events |
| C1B55 | RadarSignal_Intermittent | ACC/AEB | Communication | Non-latch | 10 consecutive valid frames |
| C1B56 | ACC_NewTarget_Override | ACC | Safety override log | Non-latch | Cleared at ignition cycle |
| C1C00 | TSR_Conf_Permanent_Low | TSR | Sensor quality | Non-latch | Camera confidence recovered |
| C1C01 | TSR_FusionConflict_Extended | TSR | Fusion | Non-latch | Map/camera agreement > 30s |
| C1C10 | BSD_RCS_Threshold_Fault | BSD | Configuration | Latch | Factory re-calibration |
| C1C11 | BSD_StaticFilter_Disabled | BSD | Configuration | Latch | Re-flash calibration |
| C1C20 | PDC_Sensor_Acoustic_Block | PDC | Sensor obstruction | Non-latch | Sensor self-test passes |
| C1C21 | PDC_OdometryMismatch | PDC | Calibration | Non-latch | Tire size verified + correction |
| C1C88 | AEB_RadarComm_Fault | AEB | Communication | **Configurable** | Startup window recovery (see AEB-003 fix) |
| C1C89 | AEB_Threshold_Config_Fault | AEB | Configuration | Latch | Speed-adaptive thresholds deployed |
| C1C90 | AEB_Gantry_FalseActivation | AEB | Classification | Log-only | No action required (event log) |

---

## Appendix C: DBC Signal Catalog (Formal Format)

```
/* ============================================================
 * ADAS FEATURE SIGNALS — DBC CATALOG v2.0
 * Compiled from all features LKA / LDW / TSR / BSD / PDC / ACC / AEB
 * ============================================================ */

/* — LKA — */
BO_ 928  LKA_CONTROL: 4 ADAS_ECU
  SG_ LKA_TorqueReq   : 0|16@1+ (0.01,-50) [-50|50] "Nm" EPS_ECU
  SG_ LKA_State       : 16|3@1+  (1,0)    [0|7]    ""   HMI_ECU,BODY_ECU
  SG_ LKA_WarningType : 19|2@1+  (1,0)    [0|3]    ""   HMI_ECU
    0="NONE" 1="LEFT_AUDIO" 2="RIGHT_AUDIO" 3="HAPTIC"

BO_ 930  CAMERA_LANE: 8 ADAS_CAM
  SG_ LaneConf_L    : 0|7@1+   (1,0)    [0|100]  "%" ADAS_ECU
  SG_ LaneConf_R    : 7|7@1+   (1,0)    [0|100]  "%" ADAS_ECU
  SG_ LateralOffset : 16|16@1+ (0.001,-16) [-16|16] "m" ADAS_ECU
  SG_ LateralVel    : 32|16@1+ (0.01,-10)  [-10|10] "m/s" ADAS_ECU
  SG_ CamStatus     : 48|3@1+  (1,0)    [0|7]    ""   ADAS_ECU
    0="OK" 1="DEGRADED" 2="BLOCKED" 3="ERROR" 4="INIT"

BO_ 396  EPS_STATUS: 4 EPS_ECU
  SG_ SteeringTorque    : 0|16@1+  (0.01,-100) [-100|100] "Nm" ADAS_ECU
  SG_ EPS_Status        : 16|3@1+  (1,0) [0|7] "" ADAS_ECU
    0="OK" 1="LKA_ACTIVE" 2="OVERRIDE" 3="FAULT" 4="NOT_READY"
  SG_ EPS_LKA_FEEDBACK  : 19|2@1+  (1,0) [0|3] "" ADAS_ECU
    0="ACCEPTED" 1="PARTIAL" 2="REJECTED" 3="FAULT"

/* — LDW — */
BO_ 944  LDW_WARNING: 1 ADAS_ECU
  SG_ LDW_Warning : 0|2@1+ (1,0) [0|3] "" HMI_ECU,AUDIO_ECU
    0="NONE" 1="LEFT_WARN" 2="RIGHT_WARN" 3="BOTH_WARN"

BO_ 80   TURN_INDICATOR: 1 BODY_ECU
  SG_ TurnIndicator : 0|2@1+ (1,0) [0|3] "" ADAS_ECU
    0="OFF" 1="LEFT" 2="RIGHT" 3="HAZARD"

/* — TSR — */
BO_ 1184 TSR_OUTPUT: 4 ADAS_ECU
  SG_ TSR_SpeedLimit : 0|8@1+  (1,0)  [0|200] "kph" HMI_ECU
  SG_ TSR_Confidence : 8|7@1+  (1,0)  [0|100] "%" HMI_ECU
  SG_ TSR_Display    : 15|1@1+ (1,0)  [0|1]   ""  HMI_ECU
  SG_ TSR_Source     : 16|2@1+ (1,0)  [0|3]   ""  HMI_ECU
    0="CAMERA" 1="MAP" 2="FUSED" 3="LASTKOWN"
  SG_ TSR_SignType   : 18|2@1+ (1,0)  [0|3]   ""  HMI_ECU
    0="STATIC" 1="VARIABLE" 2="TEMPORARY" 3="UNKNOWN"

BO_ 1200 MAP_SPEED: 2 NAVHEAD_ECU
  SG_ MapSpeedLimit : 0|8@1+ (1,0) [0|200] "kph" ADAS_ECU
  SG_ MapRoadClass  : 8|3@1+ (1,0) [0|7]   ""    ADAS_ECU
    0="UNKNOWN" 1="MOTORWAY" 2="NATIONAL" 3="URBAN" 4="RESIDENTIAL"

/* — BSD — */
BO_ 1440 BSD_OUTPUT: 4 ADAS_ECU
  SG_ BSD_ObjLeft  : 0|1@1+ (1,0) [0|1] "" HMI_ECU,BODY_ECU
  SG_ BSD_ObjRight : 1|1@1+ (1,0) [0|1] "" HMI_ECU,BODY_ECU
  SG_ BSD_WarnLeft : 2|1@1+ (1,0) [0|1] "" HMI_ECU,BODY_ECU
  SG_ BSD_WarnRight: 3|1@1+ (1,0) [0|1] "" HMI_ECU,BODY_ECU
  SG_ BSD_ObjClass : 4|2@1+ (1,0) [0|3] "" HMI_ECU
    0="NONE" 1="PASSENGER" 2="VRU" 3="STATIC"

BO_ 1456 RADAR_BSD_L: 8 RADAR_L_ECU
  SG_ BSD_L_Range   : 0|16@1+ (0.01,0) [0|20] "m" ADAS_ECU
  SG_ BSD_L_RelVel  : 16|16@1+ (0.01,-50) [-50|50] "m/s" ADAS_ECU
  SG_ BSD_L_RCS     : 32|8@1+ (0.5,-30) [-30|97.5] "dBsm" ADAS_ECU
  SG_ BSD_L_Width   : 40|8@1+ (0.1,0) [0|10] "m" ADAS_ECU

/* — PDC — */
BO_ 1696 PDC_REAR: 4 PDC_ECU
  SG_ PDC_Rear_L    : 0|8@1+  (1,0) [0|255] "cm" HMI_ECU,ADAS_ECU
  SG_ PDC_Rear_ML   : 8|8@1+  (1,0) [0|255] "cm" HMI_ECU,ADAS_ECU
  SG_ PDC_Rear_MR   : 16|8@1+ (1,0) [0|255] "cm" HMI_ECU,ADAS_ECU
  SG_ PDC_Rear_R    : 24|8@1+ (1,0) [0|255] "cm" HMI_ECU,ADAS_ECU
    255 = NO_OBJECT
    254 = SENSOR_FAULT

BO_ 1697 PDC_ALERT: 1 ADAS_ECU
  SG_ PDC_AlertLevel : 0|3@1+ (1,0) [0|5] "" HMI_ECU,AUDIO_ECU
    0="OFF" 1="ZONE4" 2="ZONE3" 3="ZONE2" 4="ZONE1_CRITICAL" 5="STOP"

/* — ACC — */
BO_ 1952 ACC_CONTROL: 4 ADAS_ECU
  SG_ ACC_ThrottleReq : 0|8@1+  (0.4,0) [0|100] "%" THROTTLE_ECU
  SG_ ACC_BrakeReq    : 8|8@1+  (0.1,0) [0|25]  "bar" BRAKE_ECU
  SG_ ACC_Status      : 16|3@1+ (1,0) [0|7] "" HMI_ECU
    0="OFF" 1="ACTIVE" 2="OVERRIDE" 3="FAULT" 4="STANDBY"
  SG_ ACC_FollowDist  : 19|8@1+ (0.1,0) [0|200] "m" HMI_ECU

/* — AEB — */
BO_ 2208 AEB_STATUS: 4 ADAS_ECU
  SG_ AEB_State     : 0|3@1+ (1,0) [0|7] "" HMI_ECU,BRAKE_ECU
    0="OFF" 1="ARMED" 2="FCW" 3="PREBRAKE" 4="FULLBRAKE" 5="FAULT" 6="COMPLETE"
  SG_ AEB_TTC_ms    : 3|16@1+ (1,0) [0|65535] "ms" HMI_ECU,BRAKE_ECU
  SG_ AEB_BrakeReq  : 19|8@1+ (1,0) [0|250] "bar" BRAKE_ECU
  SG_ AEB_CollProb  : 27|7@1+ (1,0) [0|100] "%" HMI_ECU
```

---

## Appendix D: Physics & Mathematics Reference Card

### D.1 Stopping Distance

$$d_{stop} = \frac{v_0^2}{2 \cdot a_{max}}$$

Where $a_{max} = 9.81 \text{ m/s}^2$ (1.0g dry road)

| Speed | Stopping Distance |
|---|---|
| 30 km/h | 3.5 m |
| 50 km/h | 9.9 m |
| 80 km/h | 25.3 m |
| 100 km/h | 39.6 m |
| 120 km/h | 57.0 m |
| 130 km/h | 66.9 m |

### D.2 Time-to-Collision (TTC)

$$TTC = \frac{d_{gap}}{|v_{rel}|}$$

**Speed-adaptive FCW threshold:**

$$TTC_{fcw}(v) = t_{reaction} + \frac{v}{2 \cdot a_{max}} = 1.7 + \frac{v}{19.62}$$

### D.3 Radar Cross Section

$$\sigma_{dBsm} = 10 \cdot \log_{10}(\sigma_{m^2})$$

**Typical values:**
- Pedestrian: -10 to +5 dBsm
- Motorcycle: +1 to +7 dBsm
- Passenger car: +10 to +25 dBsm
- Guardrail (10m): +8 to +15 dBsm

### D.4 PID Control

$$u(t) = K_p \cdot e(t) + K_i \int_0^t e(\tau)\,d\tau + K_d \frac{de(t)}{dt}$$

**Stability requirements:**
- Phase margin > 45°
- Gain margin > 6 dB

**Ziegler-Nichols tuning from Ku (ultimate gain), Tu (period):**

| Controller | $K_p$ | $K_i$ | $K_d$ |
|---|---|---|---|
| P | $0.5 K_u$ | — | — |
| PI | $0.45 K_u$ | $0.54 K_u / T_u$ | — |
| PID | $0.6 K_u$ | $1.2 K_u / T_u$ | $0.075 K_u T_u$ |

### D.5 Ultrasonic Distance

$$d = \frac{c \cdot t_{echo}}{2}$$

Where $c = 343 \text{ m/s}$ at 20°C.

$c(T) = 331.3 \cdot \sqrt{1 + \frac{T}{273.15}}$ (temperature-corrected)

### D.6 Lateral Dynamics (LKA)

**Lane boundary time-to-cross:**
$$t_{boundary} = \frac{d_{boundary} - x_{lateral}}{|\dot{x}_{lateral}|}$$

**LKA corrective torque requirement:**
$$M_{req} = K_p \cdot \Delta x + K_d \cdot \dot{\Delta x} + K_i \int \Delta x \, dt$$

---

## Appendix E: Standards Compliance Matrix

| Clause | Standard | Feature | Requirement | Defect | Status |
|---|---|---|---|---|---|
| §6.2 | ISO 11270:2014 | LKA | Torque authority limits | — | Compliant |
| §6.2.1 | ISO 11270:2014 | LDW | Indicator suppression | LDW-001 | **NON-COMPLIANT** |
| §6.2.3 | ISO 11270:2014 | LDW | Degraded conditions | LDW-002 | **NON-COMPLIANT** |
| §3.2.1 | LDW-SRS | LDW | ≤150ms latency | LDW-003 | **NON-COMPLIANT** |
| §5.3 | ISO 22737:2021 | AEB | Speed-adaptive thresholds | AEB-001 | **CRITICAL NCR** |
| §5.4 | ISO 22737:2021 | AEB | False activation prevention | AEB-002 | **NON-COMPLIANT** |
| §5.4.3 | ISO 15622:2018 | ACC | Cut-in response | ACC-001 | **NON-COMPLIANT** |
| §5.4.2 | ISO 15622:2018 | ACC | Temporary target loss | ACC-003 | **NON-COMPLIANT** |
| §5.4.1 | ISO 15622:2018 | ACC | Speed regulation stability | ACC-002 | Non-compliant (comfort) |
| Annex B | ISO 11270:2014 | TSR | Fusion display quality | TSR-001 | At risk |
| §3.4.1 | Euro NCAP 2026 | BSD | Motorcycle detection | BSD-001 | **NCAP FAIL** |
| — | Euro NCAP 2026 | AEB | C2S protocol | AEB-001 | **NCAP FAIL** |
| §7.1.8 | PDC-SRS | PDC | Sensor blockage detection | PDC-001 | **NON-COMPLIANT** |
| Part 4 | ISO 26262:2018 | AEB | ASIL D software | AEB-003 | **FuSa NCR** |
| Part 4 | ISO 26262:2018 | BSD | Safety goal coverage | BSD-001 | **FuSa NCR** |

---

## Appendix F: ADAS Failure Pattern Library

### Category 1: Threshold & Configuration Errors

| # | Pattern | Description | Typical Defect Type | Example in this doc |
|---|---|---|---|---|
| F01 | Fixed threshold — speed-independent | Single value used regardless of speed/context | Performance/Safety | AEB-001 TTC |
| F02 | Debug flag in production calibration | Engineering override left enabled | Configuration | BSD-002 static filter |
| F03 | DBC constant mismatch | C enum or define mismatches DBC signal value | Integration | LDW-001 LEFT/RIGHT |
| F04 | Stale lookup table | Calibration from old hardware not updated | Configuration | AEB-003 timing |
| F05 | Wrong RCS threshold for target class | RCS threshold calibrated for one object type | Specification | BSD-001 |

### Category 2: Timing & Race Conditions

| # | Pattern | Description | Typical Defect Type | Example in this doc |
|---|---|---|---|---|
| F06 | Init timing race | ECU-A checks ECU-B before B is ready | Startup timing | AEB-003 |
| F07 | Non-latching DTC as latching | Recoverable fault permanently disables feature | Safety/Availability | AEB-003 |
| F08 | Debounce misplaced | Filter applied to output not input | Timing | LDW-003 |
| F09 | Missing temporal hysteresis | State machine toggles at threshold | Stability | LKA-001 |
| F10 | PID without dead band | Controller overcorrects for small errors | Control | ACC-002 |

### Category 3: Signal & Communication Errors

| # | Pattern | Description | Typical Defect Type | Example in this doc |
|---|---|---|---|---|
| F11 | Silent actuator rejection | Actuator rejects command without error reporting | Integration | LKA-002 |
| F12 | Unread signal field | Input field exists in message but not parsed | Integration | TSR-002 sign type |
| F13 | CAN priority too low for safety alert | Safety messages delayed by low-priority bus ID | Timing | PDC-003 |
| F14 | Display state not cleared on invalidation | Previous value shown when data invalid | Display | TSR-003 |
| F15 | Missing ICD entry | Signal exists on bus but not in Interface Control Document | Documentation | LKA-002 feedback |

### Category 4: Sensor Fusion Errors

| # | Pattern | Description | Typical Defect Type | Example in this doc |
|---|---|---|---|---|
| F16 | Sensor path not shared between features | Filter added in ACC not propagated to AEB | Architecture | AEB-002 elevation |
| F17 | Context-unaware fusion | Fusion weights not adjusted for road/weather context | Algorithm | TSR-001 staleness |
| F18 | Camera output ignored in safety path | Safety function uses radar-only, camera available | Architecture | AEB-002 |
| F19 | Missing VRU classification | System trained/tuned only for passenger cars | Specification | BSD-001 |
| F20 | Static/moving object confusion | Stationary infrastructure in collision prediction path | Algorithm | AEB-002 gantry |

### Category 5: Specification & Process Gaps

| # | Pattern | Description | Typical Defect Type | Example in this doc |
|---|---|---|---|---|
| F21 | SRS updated but code not | Requirement added to SRS, developer not notified | Process | LDW-002 §3.1.7 |
| F22 | Standard revision not tracked | New ISO requirement added post-SRS-freeze | Process | ACC-001 ISO 15622 |
| F23 | DBC→code validation absent | DBC change not verified against C constants | Process | LDW-001 |
| F24 | HW ECR without SW impact | Hardware changed, software timing assumptions broken | Process | AEB-003 |
| F25 | VRU in NCAP but not in SRS | NCAP 2026 requirements not reflected in SRS | Process | BSD-001 NCAP |
| F26 | Traceability gap: standard→SRS→code | ISO clause → SRS → code chain not maintained | Process | AEB-001, ACC-001 |

---

## Appendix G: Feature Interaction & Conflict Matrix

```
ADAS FEATURE INTERACTION MATRIX
(★ = active conflict, ○ = override relationship, · = independent)

             LKA  LDW  TSR  BSD  PDC  ACC  AEB
       LKA │  ─    ○    ·    ·    ·    ★    ○  
       LDW │  ○    ─    ·    ·    ·    ·    ·  
       TSR │  ·    ·    ─    ·    ·    ○    ·  
       BSD │  ·    ·    ·    ─    ·    ○    ·  
       PDC │  ·    ·    ·    ·    ─    ·    ·  
       ACC │  ★    ·    ○    ○    ·    ─    ○  
       AEB │  ○    ·    ·    ·    ·    ○    ─  

Conflict details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LKA ★ ACC:
  CONFLICT: ACC decelerates → steering weight changes → LKA PID destabilized.
  RESOLUTION: LKA reduces torque by 30% when ACC braking > 0.2g.

LKA ○ AEB:
  AEB OVERRIDES LKA: During AEB full brake, LKA shall NOT issue correction
  torques (braking changes lateral load transfer, LKA torque would fight).
  RESOLUTION: LKA suspended when AEB_State = FULLBRAKE.

LKA ○ LDW:
  LKA OVERRIDES LDW: If LKA is actively correcting, LDW warning is suppressed
  (LKA correction IS the warning+action).
  
TSR ○ ACC:
  TSR LIMITS ACC: If TSR detects speed limit, ACC shall not set target speed
  above TSR limit + configurable delta (typically 5 kph).
  
BSD ○ ACC:
  BSD SLOWS ACC: If BSD detects object in blind spot AND driver indicates
  lane change (TurnIndicator), ACC reduces speed by 10kph (creates gap).

ACC ○ AEB:
  AEB OVERRIDES ACC: AEB always wins. ACC control (throttle/brake) superseded
  during any AEB state ≥ FCW.
  
PDC · (all):
  PDC is speed-gated (< 15kph) and reversing-only.
  No interaction with highway ADAS features.
```

---

## Appendix H: Log Analysis Methodology

### H.1 Step-by-Step Debug Workflow

```
ADAS LOG ANALYSIS PROCEDURE (Standard methodology)
═══════════════════════════════════════════════════════════════════════════

STEP 1: ESTABLISH TIMELINE
  ▶ Find the SYMPTOM timestamp in logs (warning fired / not fired)
  ▶ Look 500ms-5s BEFORE the symptom for root cause signals
  ▶ Create a timeline: T_symptom = 0, backtrack from there

STEP 2: CORRELATE CAN + SYSTEM + SERIAL
  ▶ Match timestamps across all three log sources (may differ by ±5ms)
  ▶ CAN log shows WHAT signals were sent/received and WHEN
  ▶ System log shows WHY the ECU made each decision
  ▶ Serial log shows sensor-level data (raw values, pre-processing)

STEP 3: DECODE CAN FRAMES
  ▶ Apply DBC bit-field formula: value = raw × factor + offset
  ▶ Check signal byte order (Intel LSB vs Motorola MSB)
  ▶ Validate against physical range (impossible values = DBC mismatch)

STEP 4: FIND THE DEVIATION POINT
  ▶ Where does the actual behavior FIRST diverge from expected?
  ▶ Is the input signal wrong → sensor/DBC issue?
  ▶ Is the input correct but output wrong → logic issue?
  ▶ Is output correct but timing wrong → latency / race condition?

STEP 5: CLASSIFY THE BUG CATEGORY
  Use the Failure Pattern Library (Appendix F):
  ▶ F01-F05: Threshold/Config errors
  ▶ F06-F10: Timing/race conditions
  ▶ F11-F15: Signal/communication errors
  ▶ F16-F20: Sensor fusion errors
  ▶ F21-F26: Specification/process gaps

STEP 6: 5-WHYS ROOT CAUSE ANALYSIS
  ▶ WHY 1: The symptom itself (what failed)
  ▶ WHY 2: The proximate technical cause
  ▶ WHY 3: Why the technical cause exists (design/implementation)
  ▶ WHY 4: Why it wasn't caught (process failure)
  ▶ WHY 5: Why the process failed (systemic issue)
  ▶ ROOT CAUSE: The WHY that, if fixed, prevents ALL similar issues

STEP 7: FMEA SCORING
  S (Severity): 1=cosmetic, 5=function loss, 8=safety risk, 10=life risk
  O (Occurrence): 1=never, 5=occasionally, 8=frequently, 10=always
  D (Detection): 1=always caught, 5=sometimes caught, 10=never caught
  RPN = S × O × D   Action required: RPN > 200 (typical), RPN > 400 (critical)

STEP 8: WRITE FORMAL DEFECT REPORT
  Required fields: Defect ID, Title, Severity, SRS Reference, Steps to Reproduce,
  Expected vs Actual, Root Cause, Code Fix, Fix Verification, FMEA RPN

STEP 9: WRITE TEST CASES
  Minimum 3 test cases per defect:
    - TC-xxx-01: Reproduce the bug (FAIL without fix, PASS with fix)
    - TC-xxx-02: Verify correct behavior in normal scenario
    - TC-xxx-03: Boundary/edge case (adjacent to trigger condition)
  Additional: regression test, NCAP protocol, standards compliance test
```

### H.2 CAN Frame Decoding Reference

```
CAN Frame anatomy:
  [ SOF | ARBITRATION(11-bit ID) | RTR | IDE | r0 | DLC(4) | DATA(0-64) | CRC | ACK | EOF ]

Quick decode steps:
  1. Note timestamp, direction (Rx/Tx), ID, DLC, data bytes
  2. Find signal in DBC: BO_ (message) → SG_ (signal)
  3. Extract bits: start_bit, length, byte_order
  4. Apply: value = raw_unsigned * factor + offset
  5. Check value_type (unsigned/signed) and range

Common decoding mistakes:
  ✗ Forgetting offset (raw=0 ≠ value=0 if offset is non-zero)
  ✗ Motorola vs Intel bit numbering (LSbit vs MSbit first)
  ✗ Signed 16-bit: if raw > 0x7FFF, subtract 65536 for negative value
  ✗ Ignoring multiplexor signals (MUX_ID selects signal layout)
```

---

## Appendix I: 50 Interview Questions with Expert Answers

### Section 1: LKA Deep Dive (Q1-Q8)

**Q1: Describe the LKA chattering problem you found in the logs. What is hysteresis and why was it missing?**

**A:** LKA chattering occurs when the lateral offset oscillates near the activation threshold. Without hysteresis, the ECU repeatedly exits and re-enters ACTIVE state within milliseconds — generating repeated torque commands and audio warnings. Hysteresis means using two thresholds: a higher one for activation, a lower one for deactivation. For example: activate LKA when offset > 0.50m, but only deactivate when offset drops below 0.40m. The 0.10m dead band prevents the state machine from toggling for small sensor noise. In the logs, you see it as a series of LKA_State rapid changes (STANDBY→ACTIVE→STANDBY→ACTIVE...) all within 100-200ms, with LKA_TorqueReq toggling in sync.

**Q2: If EPS silently rejects LKA torque commands, how do you diagnose this from the CAN log?**

**A:** You look for a divergence pattern: LKA_TorqueReq increases (non-zero torque commanded) while SteeringTorque remains near-zero and LateralOffset continues drifting. The "silent failure" hallmark is that the ADAS ECU keeps sending commands that are completely ignored with no error feedback. In the logs, you'd see: LKA_TorqueReq = +3.0 Nm for 5+ frames, but SteeringTorque = +0.1 Nm (unchanged). EPS_Status shows EPS_LKA_FEEDBACK = REJECTED (if the new signal is implemented) or no change to SteeringTorque. The fix requires: (a) a new feedback signal EPS_LKA_FEEDBACK in the DBC, (b) a degrade timer in LKA that sets a fault DTC if torque requested ≠ torque applied within 50ms tolerance.

**Q3: How do you tune a PID controller for LKA? What method did you use?**

**A:** For LKA lateral control, I used Ziegler-Nichols ultimate gain method. First, disable Ki and Kd, increase Kp until the system oscillates steadily (ultimate gain Ku). Measure the oscillation period Tu. Then apply PID formula: Kp = 0.6×Ku, Ki = 1.2×Ku/Tu, Kd = 0.075×Ku×Tu. For the LKA system (Ku=22, Tu=0.18s), this gives Kp=13.2, Ki=146, Kd=0.3. Then fine-tune: verify stability margins (phase margin > 45°, gain margin > 6dB), add output clamp and anti-windup for integrator, validate with step response test. Add a dead band (e.g., ±0.05m) to prevent micro-corrections from causing torque noise.

**Q4: What standards govern LKA? What are the key requirements?**

**A:** ISO 11270:2014 ("Lane Keeping Assist") is the primary standard. Key requirements: activation speed ≥ 60 km/h (§5.2), maximum torque authority (§6.2 — typically 3-5 Nm for LKA, vehicle-dependent), response to driver override (§6.3 — must release within 150ms of counter-torque), indicator suppression (§6.2.1), camera degraded-mode behavior (§6.4), and system-level driver monitoring integration (§5.5). ISO 26262 Part 6 governs the software implementation quality (ASIL B for LKA). Euro NCAP LKA test: active lane keep at 72kph, correction must start within 100ms of departure trigger.

**Q5: In a CAPL test script, how would you simulate LKA chattering to verify the hysteresis fix?**

**A:** Create a CAPL on timer that sends CamLane messages with LateralOffset oscillating around the threshold. The key is to drive the signal across the threshold multiple times per second:
```capl
on timer tChatter {
  static float offset = 0.48;
  static float direction = 1.0;
  offset += direction * 0.02;
  if (offset > 0.52) direction = -1.0;
  if (offset < 0.44) direction = 1.0;
  $CamLane::LateralOffset = offset;
  setTimer(tChatter, 20);  // 50 Hz
}
```
Then verify: (1) without fix — LKA_State toggles rapidly, (2) with fix — LKA activates once at 0.50m, stays active while offset > 0.40m, deactivates once at 0.40m.

**Q6: How would you distinguish a camera lens calibration error from a lane detection algorithm bug?**

**A:** Camera calibration error: all lane detections are consistently offset by a fixed amount (e.g., always 0.15m to the right). The detection is geometrically consistent but biased. Signs: LateralOffset shows systematic non-zero value on straight road with vehicle in center of lane. The extrinsic calibration parameters (camera tilt/yaw/height) need re-calibration. Algorithm bug: detection is inconsistent — sometimes correct, sometimes wrong, correlated with specific road markings (faded paint, rain, night). Signs: LaneConf fluctuates unexpectedly, detection jumps across frames without correlation to actual lane changes. A structured test: drive a measured straight strip, compare DUT LateralOffset against reference system (ground truth GNSS).

**Q7: What does ASIL B mean for LKA? What testing does it require?**

**A:** ASIL B (Automotive Safety Integrity Level B) is the second-highest safety level. For LKA SW: structured coding guidelines (no unreachable code, bounded loops), software unit testing with MC/DC coverage target ≥ 90%, integration testing with fault injection (camera failure, CAN disconnection), verification that hazard scenarios (unintended steering) have been identified and mitigated, and full traceability from safety goal → system requirement → SW requirement → code. Additionally: independent safety review, confirmation review by a different engineer, and FMEA/FTA (Fault Tree Analysis) for all safety-relevant code paths.

**Q8: After the LKA fix, what regression test suite would you run?**

**A:** Regression suite for LKA:
- All 5 test cases for LKA-001 (chattering): verify no false state toggles
- All 5 test cases for LKA-002 (EPS rejection): verify 50ms degrade timer
- All 5 test cases for LKA-003 (PID overshoot): verify zero overshoot at all speeds
- End-to-end functional test: drive at 80/100/120kph, curved road, verify smooth correction
- Override test: apply counter-torque > 3Nm, verify LKA releases within 150ms (ISO 11270 §6.3)
- Camera fault injection: disconnect camera → verify DTC + feature disabled gracefully
- EPS fault injection: simulate EPS fault → verify LKA disengages and DTC set
- Regression: all other features not broken by LKA changes (run full ADAS suite)

---

### Section 2: AEB Critical Safety (Q9-Q16)

**Q9: Why is the fixed TTC threshold in AEB-001 dangerous? Explain the physics.**

**A:** At 120kph (33.3 m/s), the stopping distance from FCW to zero velocity is: driver reaction 1.5s + brake build 0.2s = 1.7s × 33.3 = 56.6m reaction distance, plus v²/2a = 33.3²/(2×9.81) = 56.5m braking distance = 113.1m total. For FCW to trigger at TTC=1.8s: warning fires when gap = 1.8 × 33.3 = 60m. But 113m is needed. The vehicle will not stop before impact regardless of driver action. At 60kph the deficit is less severe but still dangerous. The fix is speed-adaptive threshold: TTC_fcw(v) = 1.7 + v/(2×9.81). This ensures the warning fires when enough distance remains for driver braking to stop the vehicle.

**Q10: What is ASIL D and what does it mean for AEB software development?**

**A:** ASIL D is the highest automotive safety integrity level. For AEB SW: formal methods or model-based development required, MC/DC coverage ≥ 100% for safety-relevant code, back-to-back testing (SW model vs C code), static analysis with zero allowed deviations for safety code, formal safety case document (GSN or structured argumentation), qualified tools (compiler, static analyzer must be ASIL D certified), two independent design reviews, hardware-in-the-loop testing covering all fault scenarios, and demonstration of freedom from systematic failure. Additionally: MISRA C compliance, no dynamic memory allocation, no recursion, bounded loops with provable termination.

**Q11: How do you test for AEB false positives (overhead gantry scenario)?**

**A:** Test methodology: (1) Build a scenario library with known overhead objects (gantry at 12° elevation, bridge, road signs). (2) Run in SIL with sensor simulation — inject radar target with elevation=+12°. (3) In HIL: use radar target simulator (e.g., Spirent GSS9000 for radar echo injection). (4) On track: drive under motorway gantry at 110kph. Expected: no AEB activation. (5) NCAP false positive protocol: Euro NCAP 2026 §4.3.2 — overhead objects must not trigger AEB. The fix (elevation filter + camera classification) must be validated at all overhead object heights (1.0g deceleration must NOT occur for objects above 4.0m height).

**Q12: The AEB startup timing race sets a latching DTC. Why is a latching DTC wrong here?**

**A:** A latching DTC means the fault persists even after the condition that caused it has resolved. For AEB startup: the DTC fires because the radar wasn't ready at T=150ms. But the radar IS ready at T=180ms — the fault condition is already gone. A latching DTC keeps AEB disabled for the entire drive cycle, even though AEB is fully functional. The correct approach is a non-latching DTC with a startup recovery window: within 1000ms of ignition, if the root cause resolves (radar comm established), clear the DTC and re-arm AEB. Latching DTC should only be used for true hardware faults that require physical inspection (e.g., cable disconnection, ECU hardware failure).

**Q13: How would you write an automatic test for AEB at multiple speeds in a HIL environment?**

**A:** CAPL-based HIL test (automated):
```capl
testcase AEB_SpeedAdaptiveTTC(float speed_kph) {
  float speed_ms = speed_kph / 3.6;
  float expected_fcw_dist = (1.7 + speed_ms / 19.62) * speed_ms;
  
  // Set ego speed
  $VehicleSpeed::Speed = speed_kph;
  TestWaitForTimeout(500);
  
  // Inject stationary target approaching
  float start_dist = 300.0;
  $Radar_F::Target1_Dist = start_dist;
  $Radar_F::Target1_RelVel = -speed_ms;  // stationary target
  
  // Monitor for FCW activation
  float fcw_dist = -1.0;
  while (fcw_dist < 0 && $Radar_F::Target1_Dist > 5.0) {
    if ($AEB_STATUS::AEB_State >= 2) {  // FCW or higher
      fcw_dist = $Radar_F::Target1_Dist;
    }
    TestWaitForTimeout(20);
  }
  
  TestAssertIsGreater("FCW distance adequate", fcw_dist, expected_fcw_dist * 0.9);
  TestAssertIsGreater("AEB stops vehicle", $AEB_STATUS::AEB_State, 0);
}
```

**Q14: What is the difference between FCW, PreBrake, and FullBrake in AEB? When does each activate?**

**A:** FCW (Forward Collision Warning): visual and audio alert only. No braking. Triggered at the highest TTC threshold (3.4s at 120kph). Gives driver maximum time to react. PreBrake: light autonomous braking (0.3g) + continued FCW alert. Triggered ~0.3s after FCW threshold. Firms up brake pads (reduces pad-to-disc gap for zero-latency full brake), gives driver a physical sensation. FullBrake: maximum autonomous braking (1.0g). Triggered ~0.2s after PreBrake threshold. Minimizes collision speed if driver hasn't responded. The speed-adaptive thresholds ensure: FCW fires when driver can STILL avoid with their own braking, PreBrake fires when AEB needs to assist, FullBrake fires only when collision is imminent and unavoidable.

**Q15: AEB-002 (overhead gantry false brake) — why can this cause a worse accident?**

**A:** If AEB fires a 1.0g full brake at 110kph on a motorway, the vehicle behind (following at 50m gap with a truck) cannot stop in time. The AEB false activation causes a rear-end collision with the following vehicle. The avoided "collision" (with an overhead gantry that the vehicle would have passed under safely) is replaced by an actual rear-end collision. This is why false positive control is as important as false negative (missed detection) in AEB design. Euro NCAP tests both: AEB must detect real threats (C2VRU, C2S, C2B) AND must NOT activate for overhead objects, narrow barriers, parked cars at low approach speed.

**Q16: If an AEB-equipped vehicle hits a pedestrian, what forensic analysis would you perform on the logs?**

**A:** Post-collision log analysis protocol: (1) Extract all ECU event logs for the 10s before impact. (2) Check radar log: was the pedestrian detected? What was RCS, confidence, classification? (3) Check camera log: was pedestrian classified correctly? What was camera confidence? (4) Check AEB log: what was TTC at detection? Was FCW/PreBrake/FullBrake triggered? (5) Compare with physics: given speed and detected TTC, was collision theoretically avoidable? (6) Check for any fault codes active during the event (DTC active = feature degraded). (7) Compare scene conditions (night, rain) against feature operational design domain (ODD). The result determines: sensor failure (hardware), algorithm failure (software), ODD boundary exceeded (design limitation), or driver override.

---

### Section 3: BSD & Sensor Physics (Q17-Q22)

**Q17: Explain radar RCS and why it matters for BSD motorcycle detection.**

**A:** Radar Cross Section (RCS) is the effective reflective area of an object as seen by a radar. Measured in dBsm (decibels per square meter). A motorcycle has RCS of +1 to +7 dBsm (worst case: 1.3 m²). A passenger car has +10 to +25 dBsm. If BSD is calibrated with a minimum detection threshold of 10 dBsm (designed for cars), motorcycles at best-case 7 dBsm are 3dB below threshold. In the radar range equation, 3dB less RCS means approximately 30% less detection range, or at the same range, the SNR is 3dB below the CFAR detection threshold. The fix is a multi-feature classifier: use target width (≤1.2m = VRU) and velocity (moving = not static infrastructure) in addition to RCS to classify and detect VRUs with a lower RCS threshold (2 dBsm for VRUs vs 10 dBsm for cars).

**Q18: BSD-002: a debug flag left in production. What process prevents this?**

**A:** Multiple layers: (1) CI/CD pre-build check: scan calibration files for known debug flags (static_filter_enabled, debug_mode, etc.) and fail the build if found in release builds. (2) Code review requirement: any commit that modifies calibration parameters requires two reviewers and justification. (3) Production calibration golden file: maintain a production-baseline calibration file in version control. Any deviation from golden file requires explicit approval. (4) SWQA sign-off: before each release, Software QA validates all calibration files against the production baseline. (5) Runtime sanity check: at startup, ECU reads calibration, validates critical fields, and sets DTC if any debug flag is enabled in production mode.

**Q19: How does the BSD cross-echo method detect a blocked ultrasonic sensor?**

**A:** In cross-echo: sensor A transmits a burst, and sensor B (adjacent, ~25cm away) listens for the cross-propagation echo. The transmitted sound reaches sensor B via air in approximately 25cm/343m/s = 0.73ms. If sensor B receives a valid echo at ~0.73ms after A's burst, BOTH sensors are acoustically clear. If no cross-echo is received (within 3ms window), one of the sensors is blocked — either A cannot transmit (membrane blocked by ice/mud) or B cannot receive. Combining cross-echo results from multiple pairs pinpoints which sensor is blocked. This is more reliable than statistical zero-echo detection alone because it doesn't require consecutive cycles — a single cross-echo test is diagnostic.

**Q20: BSD warns during a motorway lane change with a motorcycle present but no warning is given. Walk through your debug process.**

**A:** Step 1: Check CAN log for BSD_ObjLeft/Right state during the interval. If zero, BSD never detected the object. Step 2: Check radar log: did radar report an object in the BSD zone? Check range, RCS value. If RCS < 10dBsm and radar present, it's the RCS filter. Step 3: Check BSD classification log: what object class was assigned? If BSD_CLASS_UNKNOWN or BSD_CLASS_STATIC, the multi-feature classifier rejected it. Step 4: Cross-reference radar width estimate. For motorcycle: width ≤ 0.6m. If width filter requires ≥ 1.4m (car-only filter), motorcycle fails. Step 5: Check BSD calibration file: is static_filter_enabled=true? Is vru_detection_enabled=true? Step 6: Compare scenario conditions against ODD: was BSD speed-gated (< 25kph or > 200kph)? Typical BSD ODD: 30-250kph. Step 7: Root cause — most likely RCS threshold or missing VRU classifier.

**Q21: How do you calculate BSD zone boundaries and what parameters define them?**

**A:** BSD zone is typically defined as: lateral extent (0.5m to 3.5m from vehicle side), longitudinal extent (from -2m front of vehicle to +5m behind). Parameters in calibration: BSD_ZONE_FRONT_M, BSD_ZONE_REAR_M, BSD_ZONE_INNER_M, BSD_ZONE_OUTER_M. An object is in the BSD zone if: (lateral_dist >= INNER) AND (lateral_dist <= OUTER) AND (longitudinal_pos >= FRONT) AND (longitudinal_pos <= REAR). In a real radar, objects are reported in polar coordinates (range, azimuth angle). Convert to Cartesian: x = range × cos(azimuth), y = range × sin(azimuth). Then apply zone check. Cross-talk between BSD zones of adjacent ECUs: left radar must not report objects in right zone. Zone boundary overlap is a known calibration challenge.

**Q22: BSD-003 requires velocity-adaptive mirror LED timeout. Why does clearance time depend on relative velocity?**

**A:** Higher relative velocity means the object is overtaking (or falling behind) more quickly — it will exit the BSD zone faster. A slow overtake at 1m/s relative: the object takes 4+ seconds to pass (BSD zone length ~4m). A fast overtake at 10m/s: zone passed in 0.4s. If clearance timeout = 500ms for slow and fast alike, fast overtakes are fine but slow overtakes keep the LED on too long. Conversely, if timeout = 150ms for fast overtakes, slow overtakes will extinguish the LED while the vehicle is still present. Velocity-adaptive: fast=150ms, moderate=350ms, slow=500ms. All values must be ≤ SRS maximum (500ms) to maintain compliance. This also handles the edge case where an object slows down inside the BSD zone — the adaptive timeout re-evaluates each cycle.

---

### Section 4: LDW, TSR & System Design (Q23-Q32)

**Q23: LDW-002 missed a lane departure at night. How does ISO 11270 §6.2.3 address degraded conditions?**

**A:** ISO 11270 §6.2.3 specifies that LDW shall warn of lane departure even in degraded sensing conditions (night, rain) when the departure is imminent. "Imminent" is defined by the departure velocity threshold — a vehicle crossing a lane marking at 0.45 m/s lateral velocity will reach the marking in < 1 second from normal following position. The standard recognizes that camera confidence naturally drops in poor conditions and mandates that safety-critical warnings (imminent departure) cannot be gated by confidence alone. The SRS captured this in §3.1.7 but the implementation team added a blanket confidence gate that blocks all warnings below 70% — which silently invalidated the §3.1.7 requirement. The root cause is lack of SRS-to-code traceability review.

**Q24: Explain TSR fusion architecture and the bug with road class changes.**

**A:** TSR fusion combines camera CNNdetections with HD map speed limits. The fusion rule: camera wins if confidence ≥ 70% AND sign is fresh (within staleness window). Map wins if camera is low-confidence or stale. The bug: staleness window = 120s global constant. On a motorway (long spacing between signs), 120s is appropriate. But when the vehicle exits onto a local road, the motorway sign (already 0s old) is "fresh" for another 120s even though the road type has completely changed. Fix: road type transition event reduces staleness window to 10-30s (context-dependent). The camera sign from the previous road segment is treated as immediately suspect when road class changes.

**Q25: How would you design a CAPL test for TSR showing 0 km/h in a tunnel?**

**A:** Simulate tunnel entry by sending CamStatus = BLOCKED and TSR_SpeedLimit = 0, then verify HMI display goes off (not "0 km/h"):
```capl
testcase TSR_TunnelNoBogusDisplay() {
  // Establish normal state: speed=100, display on
  $CamLane::CamStatus = 0;  // OK
  $TSR::TSR_SpeedLimit = 100;
  $TSR::TSR_Confidence = 90;
  TestWaitForTimeout(500);
  TestAssertEqual("Display on in normal", $TSR_OUT::TSR_Display, 1);
  
  // Simulate tunnel: camera blocked
  $CamLane::CamStatus = 2;  // BLOCKED
  $TSR::TSR_SpeedLimit = 0;
  $TSR::TSR_Confidence = 0;
  TestWaitForTimeout(200);
  
  // Verify display goes OFF (not 0)
  TestAssertEqual("Display off in tunnel", $TSR_OUT::TSR_Display, 0);
}
```

**Q26: What is a DBC file and why is DBC-to-code validation important?**

**A:** A DBC (Database CAN) file is the formal definition of all CAN messages and signals for a vehicle network. It defines: message IDs, signal names, bit positions, scaling factors, offsets, value ranges, and textual value descriptions (enum). DBC files are owned by Systems/Network Architecture teams. C code must implement signal encoding/decoding exactly as defined in the DBC. DBC-to-code mismatch (like LDW-001 LEFT/RIGHT constant swap) causes: wrong signal interpretation, wrong feature behavior. Validation: automated CI script extracts all signal constants from DBC, generates expected C defines, diffs against actual header file. Any mismatch = build failure. This catches DBC update misses in code (or vice versa) automatically.

**Q27: You see a CAN trace where a message ID 0x3A1 changes DLC from 4 to 8 bytes. What does this indicate?**

**A:** A DLC (Data Length Code) change mid-trace indicates one of: (1) ECU software version mismatch — two ECU versions with different DBC revisions coexisting, one sends 4 bytes (old) one sends 8 bytes (new). (2) Wrong ECU node responding — two nodes sharing the same message ID (misconfiguration, should never happen in a properly architected network). (3) Memory corruption in the transmitting ECU — DLC field in the CAN message buffer was overwritten. (4) Test equipment injecting a non-standard frame. In production: immediately check ECU software version alignment. If two ECU versions are confirmed coexisting, it's a partial flash/update issue. Memory corruption requires full ECU log and watchdog analysis.

**Q28: LDW-003: why is predictive lane departure warning better than reactive?**

**A:** Reactive (current, broken): warning fires after the lane marking is crossed. The driver is already wrong. Maximum available reaction distance = 0 (already crossing). Warning is informational only — too late for preventive action. Predictive (fixed): compute time-to-boundary based on current lateral offset and velocity. Warning fires N seconds (e.g., 0.8s) before crossing. Driver has time to steer back proactively. This also allows earlier warning without false positives: the velocity term confirms the vehicle IS heading toward the boundary (not just near it). ISO 11270 mandates predictive logic implicitly through latency requirements — reactive logic cannot achieve ≤150ms from "departure event" because the departure event IS the crossing.

**Q29: Design a regression test framework for ADAS features in CAPL. What would you include?**

**A:** A comprehensive CAPL regression framework includes: (1) Test infrastructure: capl_test_lib.cin with TestSetTitle, TestWaitForTimeout, TestAssertEqual, TestReportStep. (2) Stimulus generators: functions to inject CAN signals for each sensor (camera, radar, ultrasonic). (3) Feature test modules: one .can file per feature (lka_tests.can, ldw_tests.can, etc.). (4) Scenario library: pre-defined driving scenarios (straight, curved, night, rain — via environment flags). (5) Reporting: TestWriteToLog for all assertions, XUNIT XML output for CI integration. (6) CI integration: Jenkins/GitLab CI runs tests via CANoe CAPL API on commit. (7) Coverage tracking: map test IDs to SRS requirements (traceability matrix auto-updated). Key tests: each defect has a regression TC that FAILS without the fix. CI pipeline fails if any regression TC fails.

**Q30: How do you validate that an ADAS feature meets its SRS latency requirement (e.g., LDW ≤150ms)?**

**A:** Measurement approach: (1) Instrument the code with timestamps at input receipt and output command. (2) In HIL/SIL: inject lane departure stimulus at T=0, measure LDW_Warning CAN frame timestamp. Delta = latency. (3) Automated: run 1000 departure scenarios, compute mean, 95th percentile, max. (4) Pass criterion: max latency ≤ SRS requirement (150ms). (5) Boundary conditions: also measure under maximum CPU load (worst case), cold start (first 5s), and camera degraded mode. (6) Log analysis method: in field logs, compare lateral offset crossing threshold timestamp with LDW_Warning timestamp. 5 frames × 20ms = 100ms (one-way). Any result > 150ms = non-compliance.

---

### Section 5: ACC, Integration & Methodology (Q31-Q40)

**Q31: ACC-001 cut-in: how does the urgency exception classifier work?**

**A:** The classifier evaluates four criteria jointly: (1) Confidence ≥ 0.88: radar has seen the target in multiple range bins, very unlikely to be a ghost. (2) Relative velocity ≤ -4.0 m/s: the target is closing fast — consistent with a vehicle that cut in ahead and is slower. (3) TTC ≤ 4.0s: urgency is real — action needed within 4 seconds. (4) Width ≥ 1.4m: vehicle-sized object, not debris or motorcycle. Only if all four are true does the lockout bypass engage. This prevents false positives from radar ghost targets (fail on confidence), approaching targets in other lanes (fail on width), slow cut-ins at safe distances (fail on TTC), and motorcycles (may need separate handling since width < 1.4m — motorcycle cut-in is a separate scenario).

**Q32: ACC-002 speed hunting — explain why P-only PID oscillates.**

**A:** A P-only controller has no phase lead (from derivative) and no steady-state correction (from integral). At high gain, the P term causes rapid correction, but the engine + driveline has inherent delay (time constant ~0.35s total). With delay, by the time the correction arrives at the output, the error has already reversed sign — the correction is now in the wrong direction. This creates a 180° phase shift at a critical frequency, and with gain > 1 at that frequency, sustained oscillation results. The Bode plot shows: at the phase crossover frequency, the loop gain is > 0dB → unstable. Adding derivative (D term) provides phase lead that compensates the plant delay, stabilizing the loop. Adding integral (I term) ensures zero steady-state error. The dead band (1kph) prevents the controller from acting on small errors that are within the acceptable range.

**Q33: For a cut-in emergency, should ACC or AEB respond? Explain the intended architecture.**

**A:** The intended architecture is layered: ACC should detect and respond to cut-ins first (smooth deceleration, controlled following). ACC is the primary response. AEB is the last resort — it activates only if the situation has progressed to imminent collision (TTC < AEB threshold). If ACC works correctly (ACC-001 fix applied), cut-ins at 30m+ are handled smoothly by ACC: decelerate to match cut-in speed, maintain following distance. AEB should never need to activate for a cut-in that ACC handled correctly. The problem in ACC-001 (without fix) was: ACC ignores the cut-in for 500ms. In that 500ms, the TTC drops to AEB territory, and AEB activates with a harsh full brake — much worse UX and potentially triggering a rear collision from the following vehicle. Correct architecture: ACC response is smoother and safer for the whole traffic situation.

**Q34: How do you debug an intermittent issue that only appears in field, not in test?**

**A:** Systematic approach: (1) Enable all available logging in field — increase log verbosity, ensure all relevant ECUs log to flash/SD card. (2) Identify the pattern: what conditions are present when it occurs? (time of day, speed, road type, temperature, load). (3) Compare failing conditions vs passing conditions: what's different? (4) Check if it's timing-related: does it correlate with CPU load, CAN bus load? (5) Enable DTCs for any borderline conditions — often the issue is near a fault threshold. (6) Instrument the code: add logging around the suspected area with minimal performance impact. (7) Use black-box recording: continuous circular buffer of last 30s of all signals, triggered by anomaly events. (8) Reproduce in lab with identified conditions: HIL can simulate field conditions if root cause is found. The LDW night/rain bug (LDW-002) is a classic field-only issue: test labs don't reproduce rain/night camera degradation realistically.

**Q35: Explain ISO 26262 ASIL decomposition. How does it apply to AEB?**

**A:** ASIL decomposition: a safety requirement at ASIL D can be split into two independent requirements at ASIL B each. Independence requirement: the two implementations must be implemented by different teams, on different hardware, with different algorithms. For AEB: AEB ASIL D = AEB_Primary (ASIL B) + AEB_Monitor (ASIL B). Primary runs the main AEB algorithm. Monitor runs a simplified cross-check (e.g., just verifies TTC < emergency threshold). If Primary and Monitor disagree, a conservative safe state is entered. This allows two separate development teams to implement AEB at lower ASIL than the full D requirement, while the combination achieves ASIL D safety integrity. This is more practical since ASIL D development has much stricter constraints (tool qualification, formal methods, 100% coverage).

**Q36: What is the difference between ISO 26262 and ISO 21434? How do they intersect for ADAS?**

**A:** ISO 26262 is Functional Safety — covers accidental failures. Ensures the system fails safely under hardware faults, software bugs, environmental disturbances. ISO 21434 is Cybersecurity Engineering — covers intentional attacks. Ensures the system cannot be compromised by an attacker (remote, local, physical). For ADAS: ISO 26262 addresses: AEB radar failure, camera failure, ECU power loss. ISO 21434 addresses: spoofing radar with a signal generator, injecting false CAN messages to trigger AEB, accessing camera video stream remotely. Intersection: a cybersecurity attack can cause a functional safety failure (attacker disables AEB, triggers false AEB). "TARA" (Threat Analysis and Risk Assessment, ISO 21434) maps to "HARA" (Hazard Analysis and Risk Assessment, ISO 26262). Both feed into the system safety concept. Modern vehicles need both standards applied simultaneously.

**Q37: How do you write a formal defect report that satisfies both engineering and safety audit requirements?**

**A:** Formal defect report structure: (1) **Header**: Defect ID, title, severity (ASIL impact), date, reporter, owner. (2) **SRS Reference**: specific clause(s) violated. (3) **System/SW version**: exact version where found. (4) **Reproduction**: step-by-step reproduction, reproduction rate (10/10, 1/10). (5) **Observed behavior**: what the system did with evidence (CAN log, system log). (6) **Expected behavior**: what the SRS requires. (7) **Root cause**: technical root cause (specific code location) AND process root cause (why it wasn't caught). (8) **Impact assessment**: FMEA update, safety goal impact, NCAP impact. (9) **Fix**: code diff + process fix (if applicable). (10) **Verification**: test cases that prove fix is effective. (11) **Regression risk**: what else might be affected by the fix. (12) **Sign-off**: SW owner, safety engineer, test engineer. For ASIL B/D: safety engineer sign-off is mandatory.

**Q38: What is a CAN bus load percentage and what happens when it exceeds 80%?**

**A:** CAN bus load = (sum of all message transmission times) / (total available bit time per second). For 500kbps: 500,000 bits/s available. If all messages sum to 400,000 bits/s, load = 80%. Above 80%: (1) High-priority messages still get through immediately. (2) Low-priority messages (high numeric ID = low priority) experience increasing latency — multiple arbitration attempts needed. (3) Burst load (multiple messages triggered simultaneously) can push instantaneous load to 100%, causing message delays. (4) PDC-003: safety alert on 0x6A2 (low priority) delayed 62ms because of cascading delays from high-priority messages (0x0xx ACC/AEB frames) filling the bus. Mitigation: move safety alerts to high-priority ID range, reduce cycle times of non-critical messages, move some signals to CAN FD (2Mbps) or Ethernet.

**Q39: How does functional safety differ between ASIL A, B, C, D for ADAS features?**

**A:** ASIL is determined by: Severity (S1-3), Exposure (E1-4), Controllability (C1-3). ASIL = f(S, E, C). For ADAS features:
- **ASIL A** (LDW): LDW warns but driver can always ignore. High controllability (C1). Lower severity since it's informational.
- **ASIL B** (LKA): LKA applies torque. Less controllable (driver must counter-torque). Medium severity.
- **ASIL C** (ACC): ACC applies brake force. Low controllability. High severity (speed reduction can cause rear collision).
- **ASIL D** (AEB): AEB applies maximum emergency brake. Very low controllability. Highest severity (full brake at 120kph). Also BSW pedestrian-related BSD: ASIL D if classified as safety-critical VRU detection.

Development constraints scale accordingly: ASIL D requires formal verification, 100% MC/DC, independent review; ASIL A only requires structured coding standards and unit tests.

**Q40: You discover a safety-critical bug (AEB-001) one week before SOP (Start of Production). Walk through the escalation process.**

**A:** (1) **Immediate**: Raise a Safety NCR (Non-Conformance Report) in the safety management system. The NCR documents the safety goal violation. (2) **Stop delivery**: No vehicles ship with the unfixed code. Production hold placed on vehicles with affected SW version. (3) **Cross-functional team**: Emergency task force: AEB SW lead, Safety Manager, Vehicle Integration Lead, NCAP Manager, Legal/Homologation. (4) **Patch development**: ASIL D change process — same development standard as the original code. No shortcuts. Target: 1 sprint max (5 days). (5) **Testing**: SIL validation → HIL regression (48h) → Vehicle test at all speeds (3 days). (6) **Safety review**: Independent safety engineer reviews fix and signs off Safety Case. (7) **OEM notification**: Inform vehicle manufacturer of issue, impact assessment, fix timeline. (8) **Production re-entry**: Updated SW released with formal SW version bump, change note, and all safety sign-offs complete. (9) **Lesson learned**: Update development checklist, SRS template (add speed-adaptive threshold requirement as standard), NCAP pre-check automated test.

---

### Section 6: Debugging Tools & Advanced Scenarios (Q41-50)

**Q41: What is CANalyzer/CANoe? How do you use it for ADAS debugging?**

**A:** CANalyzer is Vector's network analysis tool for passive CAN monitoring. CANoe is the full-featured simulation and test environment. For ADAS debugging: (1) CANoe loads the DBC file → signals decoded automatically from raw bytes. (2) Trace window: real-time CAN frame display with decoded values. (3) Graphics window: plot signal vs time (lateral offset, TorqueReq, AEB_TTC together). (4) CAPL scripting: automate test scenarios, inject stimuli, evaluate pass/fail. (5) System variables: simulate ECU behavior without hardware. (6) CANdb++ editor: modify DBC files for testing new signals. (7) Measurement setup: record logs to .asc (ASCII trace) or .blf (binary). For ADAS RCA: load .asc log, apply DBC, use filter to show only relevant IDs, correlate timestamps across features.

**Q42: Describe the Vector CANoe HIL setup for ADAS feature testing.**

**A:** CANoe HIL setup components: (1) CANoe PC: runs simulation environment, CAPL tests, DBC databases. (2) VN1630A/VN7640 (or similar): CAN/CAN FD interface hardware between PC and vehicle network. (3) Real ECUs on test bench: connect actual ADAS ECU, HMI ECU, brake ECU. (4) Simulated ECUs: CANoe's panel/simulation replaces sensors (camera, radar) with controlled signal injection. (5) Radar signal generator (optional HIL): Spirent GSS9000 for realistic radar target injection. (6) Power supply + breakout box: replicate vehicle power conditions. (7) Test execution: CAPL test modules run automatically, results written to XML for CI. For AEB testing: inject radar targets at known distances/velocities, measure AEB response (BrakeReq timing, amplitude), compare against SRS requirement.

**Q43: How do you use GDB for embedded C debugging of an ADAS ECU?**

**A:** GDB on embedded ECU (via JTAG/OpenOCD): (1) `arm-none-eabi-gdb adas_ecu.elf` — load debug symbols. (2) Connect to target: `target remote :3333` (OpenOCD JTAG server). (3) Set breakpoints: `break aeb_evaluate` — halt at AEB decision function. (4) Read variables: `print ttc_s`, `print ego_speed_ms`, `print collision_prob`. (5) Step through: `next` (source level), `step` (into functions), `continue` (to next breakpoint). (6) Watchpoints: `watch aeb_state` — halt when AEB state changes. (7) Memory read: `x/4wx 0x2000A000` — read 4 words at address (check signal buffer). For AEB timing race: breakpoint on radar_comm_check, single-step through, observe timing relative to radar init. Limitation: breakpoints halt real-time system — use instrumented logging or hardware trace (TPIU/ITM) for non-intrusive timing measurement.

**Q44: What is MISRA C and which rules are most important for ADAS?**

**A:** MISRA C is a coding standard for safety-critical C code (developed by Motor Industry Software Reliability Association). Key rule categories for ADAS: (1) No dynamic memory allocation (Rule 20.4): prevents heap fragmentation and unpredictable memory use. (2) No recursion (Rule 16.2): prevents stack overflow in deeply nested calls. (3) All variables initialized (Rule 9.1): prevents undefined behavior from uninitialized memory. (4) No implicit type conversions (Rules 10.1-10.8): prevents silent sign extension bugs. (5) Bounded loops (Rule 14.2): loops must have a provable maximum iteration count. (6) No dead code (Rule 2.1): every statement must be reachable. (7) Pointer restrictions (Rule 17): no function pointers unless safety-analyzed. For AEB (ASIL D): advisory rules become mandatory, zero deviations allowed in safety-relevant code, deviation requires formal justification and safety review.

**Q45: How do you interpret a CAN off-bus error in the trace? What causes it?**

**A:** A CAN bus-off error means a node has exceeded its error limit (128+ transmit errors or 256+ receive errors) and removed itself from the network. The node stops all CAN communication. Causes: (1) Electrical: short circuit on CANH/CANL, missing or wrong termination resistor (should be 120Ω at each end), excessive stub length. (2) Timing: two nodes transmitting at exactly the same time with same ID (ID collision — should be impossible with proper network design). (3) EMC: strong electromagnetic interference causing repeated bit errors. (4) Software: transmit buffer overflow, CAN controller misconfiguration. In a trace: you see repeated ERROR FRAME messages, followed by silence from the affected node. After bus-off, the node may attempt recovery (auto-recovery in some controllers after 128 recessive bits). For safety: if ADAS ECU goes bus-off, all features immediately unavailable. Critical DTC must be set and driver notified.

**Q46: Explain the XCP protocol. When would you use it during ADAS development?**

**A:** XCP (Universal Measurement and Calibration Protocol) is a standard protocol for ECU calibration and measurement during development. It operates over CAN, CAN FD, Ethernet, or FlexRay. Use cases in ADAS: (1) Online calibration: adjust LKA PID gains Kp, Ki, Kd while driving on a test track — no reflash needed. Find optimal values in one session. (2) Measurement: capture internal variables (lateral offset error, PID integrator value, AEB TTC) in real time with high time resolution (>1kHz possible). (3) Algorithm bypass: force internal state variables to test specific scenarios (inject artificial TTC value to test AEB thresholds). (4) DAQ (Data Acquisition): define a list of variables to record, XCP streams them all at configured rate. Tools: Vector CANape (calibration), ETAS INCA. During AEB TTC threshold validation: use XCP to capture aeb_fcw_ttc_threshold(ego_speed_ms) in real time at multiple speeds.

**Q47: What is the difference between ISO 15622 and ISO 22737? When does each apply?**

**A:** ISO 15622 (Adaptive Cruise Control — ACC): defines performance requirements for ACC systems that maintain speed and following distance. Key clauses: §5 performance requirements, §6 test procedures, Annex A failure mode analysis. Covers: target acquisition, speed regulation, following distance control, cut-in, cut-out scenarios. Applies to: vehicles with ACC speed range 30-200kph. ISO 22737 (Low-speed Automated Driving — LSAD): defines performance for automated driving at low speeds (urban, parking). AEB at low speed is covered here. Key clauses: §5.3 AEB forward collision, §5.4 pedestrian detection, §5.5 cyclist detection. Applies to: urban AEB (< 60kph target speed), pedestrian AEB, cyclist AEB. For our AEB-001: ISO 22737 §5.3 covers the speed-adaptive threshold requirement for urban scenarios, while Euro NCAP AEB 2026 protocol covers the actual test procedure at multiple speeds.

**Q48: How do you perform root cause analysis on a defect found only in the field (no lab reproduction)?**

**A:** Field-only defect RCA process: (1) Collect all available evidence: ECU logs, DTC snapshot, environment data (OBD: speed, temperature, location), customer description. (2) Identify discriminating conditions: what is unique about the field scenario? Night? Wet? Specific road type? High mileage? (3) Review logs for precursors: look 30-60 seconds before the event for borderline conditions, borderline DTC thresholds, elevated error counters. (4) Check software version: exact flash version, calibration variant, HW variant. (5) Network with other field cases: is this isolated or a pattern across multiple vehicles? (6) Construct lab scenario: if it's night + wet + 100kph, set up camera in rain chamber, reduce lighting, run at 100kph on HIL. (7) Statistical analysis: if 10 field cases, what's common? Use correlation matrix. (8) Hypothesis → verify cycle: form specific hypothesis, create test that proves/disproves it. LDW-002 was found by systematic camera confidence analysis across field events.

**Q49: Describe the complete testing pipeline for a new ADAS feature from development to production.**

**A:** V-Model testing pipeline: (1) **Unit test (SW)**: every function tested in isolation. MC/DC coverage per ASIL. Tools: Unity, CppUTest. (2) **Software Integration Test (SIT)**: modules integrated, interfaces verified. CAPL test on SIL model. (3) **Hardware-in-the-Loop (HIL)**: real ECU + simulated vehicle/sensors. Automated test suite. Radar/camera signal injection. (4) **Software-in-the-Loop (SIL)**: SW model running in simulation. Full scenario library. NCAP protocols automated. (5) **Component test on bench**: real ECU + selected real actuators (EPS motor bench, brake bench). (6) **Vehicle integration test**: full vehicle, closed test track. Feature functional tests, interaction tests. (7) **NCAP homologation tests**: formal NCAP protocol runs, filmed, submitted to rating agency. (8) **Homologation/type approval**: regulatory authority (DVSATRAF, TÜV etc.) review. (9) **Production validation (PVT)**: pre-production vehicles, final sign-off. (10) **Ongoing field monitoring**: OTA telemetry, DTC monitoring, periodic field updates. Each stage has defined entry/exit criteria and formal sign-off.

**Q50: You are the lead test engineer for an ADAS feature release. What is your release gate checklist?**

**A:** ADAS feature release gate checklist:

**Safety (mandatory — any FAIL = no release):**
- [ ] All ASIL B/C/D safety requirements have passing test evidence
- [ ] All Safety NCRs resolved and safety engineer signed off
- [ ] No RPN > 400 open issues
- [ ] AEB/ACC ISO standard compliance tests passed
- [ ] Euro NCAP pre-check tests passed (or planned NCAP waiver in place)
- [ ] Functional Safety Case updated and reviewed

**Quality (all must pass):**
- [ ] Regression test suite 100% pass (zero failures)
- [ ] All defects severity 1-3 resolved (sev 4-5 triaged, deferred list approved)
- [ ] FMEA Master Table reviewed, no new high-RPN items since last review
- [ ] DBC → code consistency check passes (CI automated)
- [ ] All DTCs validated (set conditions, clear conditions, impact on feature)
- [ ] Performance tests pass: latency ≤ SRS requirements for all features
- [ ] MISRA violations: zero mandatory rule violations, deviations justified

**Process:**
- [ ] SW version tagged in git, release notes complete
- [ ] Calibration file validated against production golden file
- [ ] SRS → code traceability matrix updated, all requirements covered
- [ ] Test evidence package complete (test reports, CAN logs, HIL screenshots)
- [ ] OEM feature acceptance sign-off obtained
- [ ] Supplier integration tested (radar, camera, EPS, brake ECU SW versions locked)

**Post-release monitoring plan:**
- [ ] Field monitoring telemetry configured for key DTC patterns
- [ ] Customer escalation procedure documented
- [ ] OTA update capability verified (if applicable)
