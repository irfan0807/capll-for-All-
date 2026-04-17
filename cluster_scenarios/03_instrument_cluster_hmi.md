# Instrument Cluster / HMI Scenarios — Scenario-Based Questions (Q31–Q45)

> **Domain**: How ADAS warnings, status icons, and system states are communicated to the driver via the instrument cluster (IC) display, head-up display (HUD), and multi-modal alerts. Covers ISO 7000 symbols, EU GSR 2022 mandates, HMI state machines, warning prioritization, and validation.

---

## Q31: ADAS Status Icon — Active / Standby / Degraded / Fault State Machine

### Scenario
The LKA system can be in one of four states: STANDBY, ACTIVE, DEGRADED, or FAULT. The driver expects to see a clear visual indicator of each state on the instrument cluster. Describe the complete HMI state machine and the required icon behavior.

### Expected Behavior
Each state must have a distinct, unambiguous display behavior per ISO 15008 (human factors for in-vehicle displays) and UN ECE R79 / GSR 2022 mandates.

### HMI State Machine

```
        [STANDBY] ──────── driver engages ──────────→ [ACTIVE]
            ↑                                              │
            │ driver disengages or speed ODD exit         │ sensor degradation
            └──────────────────────────────────────────   │
                                                  ↓
                                           [DEGRADED]
                                                  │ critical fault
                                                  ↓
                                             [FAULT]
                                          (DTC stored)
```

### State-to-Display Mapping

| State | Icon Color | Icon Behavior | Auditory | Haptic |
|-------|-----------|--------------|----------|--------|
| STANDBY | White/Grey | Static icon; low brightness | None | None |
| ACTIVE | Green | Static icon; normal brightness | Short confirmation tone (if first activation) | Optional brief wheel vibration (LKA) |
| DEGRADED | Yellow/Amber | Slow blink (1 Hz); text "Limited" | Single mid-tone chime | None |
| FAULT | Red | Fast blink (2 Hz) or static red; text message | Continuous chime until acknowledged | None |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Transition DEGRADED → ACTIVE (sensor clears): how fast? | Icon transition within 1 scan cycle (≤ 100 ms) |
| Multiple systems degrade simultaneously (LKA + TSR + ACC) | Multi-icon display; prioritization tier governs foreground icon |
| FAULT state ignored by driver > 10 s | Escalate to repeated chimes + text "System Fault: Check Vehicle" |
| Ignition cycle: FAULT icon persists after key-off and key-on | Yes — DTC stored; FAULT displayed until diagnosed and cleared |

### Acceptance Criteria
- State transitions reflected on IC within ≤ 100 ms of system state change
- ACTIVE: always green; FAULT: always red (ISO 6727 / SAE J578 color compliance)
- FAULT icon triggers before the faulty system issues a command (no "silent fail")

---

## Q32: Warning Escalation Sequence — Visual → Auditory → Haptic

### Scenario
The FCW system detects a potential collision. Describe the full multi-modal escalation sequence from first warning through AEB activation, specifying timing, modality, and driver override conditions.

### Expected Behavior
A tiered escalation must provide sufficient warning for the driver to react while not desensitizing the driver with excessive alerts for non-threatening events.

### Escalation Sequence

| Level | TTC Threshold | Modality | Visual | Audio | Haptic |
|-------|-------------|---------|--------|-------|--------|
| Level 1 — Pre-warn | TTC = 2.7 s | Visual only | Yellow FCW icon + red color bar in HUD | None | None |
| Level 2 — Warning | TTC = 2.0 s | Visual + Audio | Red FCW icon blinks 4 Hz; full-width red HUD flash | 2-tone urgent chime (85 dB at headrest) | Seat belt pretension (10 N) |
| Level 3 — Imminent | TTC = 1.3 s | All modalities | Continuous red; "BRAKE!" text | Continuous rapid beep | Brake jolt (0.3 g for 100 ms) + belt tightening |
| AEB Activation | TTC = 0.8 s | System action | "AEB ACTIVE" on IC | Long warning tone | Full braking felt by driver |

### Driver Override Conditions
- Full brake pedal input at any level: FCW/AEB deactivates; driver has taken control.
- Steering input > 45°/s during Level 2/3: ESC + ESA take over; FCW deactivated.
- If driver dismisses Level 1 via UI button: system notes dismissal; does not re-warn for same event.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Audio system off (music paused): chime still plays via separate channel | Yes — safety chimes routed through a dedicated safety audio path, independent of entertainment audio |
| Driver already braking (AEB not needed): suppress Level 3 jolt | Brake demand monitoring: if driver braking ≥ 0.5 g, suppress physical brake jolt |
| Warning fires in parking lot (low-speed, no FCW ODD): suppress entirely | FCW activates above minimum speed threshold (typically > 10 km/h); parking scenarios use USS warnings instead |
| Warning fires for oncoming vehicle in opposite lane | Lateral lane filter: FCW only for objects in ego lane; alerts suppressed for adjacent lane |

### Acceptance Criteria
- Level 1 → Level 3 escalation completed in ≤ 1.4 s (TTC 2.7 s to TTC 1.3 s at closing speed 17 m/s)
- All audio warnings ≥ 65 dB at driver headrest (ISO 15007 measurability)
- Zero false escalations to Level 3 at ≤ 0.1 events / 1,000 km

---

## Q33: ISO 7000 / ISO 6727 Symbol Compliance for ADAS Icons

### Scenario
A new TSR icon design showing a camera + speed sign combination is proposed. The OEM design team needs to validate that this icon meets ISO 7000 and regulatory requirements. What is the validation process?

### Expected Behavior
All ADAS icons must conform to ISO 7000 (graphical symbols for use on equipment), ISO 6727 (colors for pilot lights), and national/regional regulations (e.g., EU type approval).

### Validation Process

| Validation Step | Standard | Test Method |
|----------------|---------|------------|
| Symbol legibility at minimum IC character size | ISO 15008 | Viewing distance test: legible at 1.0 m, 15° viewing angle |
| Color correctness | ISO 6727 | Colorimetry: green within CIE x=0.285–0.395, y=0.454–0.515 |
| Symbol comprehensibility survey | ISO 9186 | ≥ 67% of test subjects correctly identify symbol meaning |
| Flicker-free dynamic display | ISO 15008 | No flicker at refresh rates ≥ 60 Hz |
| Symbol size vs. IC screen resolution | ISO 15008 | Minimum visual angle: 0.4° for warning symbols |
| Night/Day brightness adaptation | ISO 15008 | Luminance ratio day:night = 10:1; auto-dimming at LUX sensor |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Icon only visible to driver in right-hand-drive vs. left-hand-drive variants | Position must be mirrored in some markets; type approval per market |
| Color-blind driver: red/green distinction | ISO 15008: safety-critical icons must be distinguishable without color alone; shape + label differentiate |
| Localization: text part of icon (e.g., "LKA" text) | Must be translated for relevant markets; ideally text-free using universal graphical symbols |

### Acceptance Criteria
- ISO 9186 comprehension test: ≥ 67% recognition in target user population
- All icon colors within ISO 6727 chromaticity gamut (measured with spectrophotometer)
- Day/night brightness ratio ≥ 5:1 and ≤ 20:1

---

## Q34: EU GSR 2022 Mandatory HMI Requirements

### Scenario
A new vehicle is being homologated for sale in the EU under General Safety Regulation 2022 (EU 2019/2144). What ADAS HMI elements are now mandatory by law, and how are they validated during type approval?

### GSR 2022 Mandatory ADAS Systems and Their HMI

| System | GSR Ref | Mandatory HMI Element |
|--------|---------|----------------------|
| ISA (Intelligent Speed Assistance) | UN ECE R151 / GSR Art.6 | Driver-visible speed limit display; override indicator |
| AEB (Autonomous Emergency Braking) | UN ECE R152 | AEB activation indicator; system readiness indicator |
| LDW (Lane Departure Warning) | UN ECE R130 | LDW warning modality (audio/haptic); steering wheel vibration for LKA |
| Driver Drowsiness & Attention Warning (DDAW) | GSR Art.6 | Alert to driver when drowsiness detected; driver acknowledgment mechanism |
| Reversing Detection | GSR Art.6(1)(p) | Auditory/visual warning for detected objects behind vehicle |
| Advanced Driver Distraction Warning (ADDW) | GSR Art.6 | Visual/audio alert for phone use, secondary distraction |
| Event Data Recorder (EDR) | GSR Art.6 | No HMI required, but driver info in manual |
| Alcohol Interlock (future) | GSR Art.6 | Interlock status display |

### Type Approval Validation
- Functional verification: each alert fires at the prescribed stimulus.
- False positive test: ≥ 200 km real-world driving with ≤ N false alerts per system (per UN ECE regulation).
- ISO 15007: driver response timing → must not distract during non-safety critical moments.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| ISA override by driver: how to display? | ISA override indicator must remain on for the duration of the override (not just momentary) |
| DDAW fires false positive (driver alert due to vibration, not drowsiness) | Annoyance threshold concern; calibration test with ≥ 2,000 drivers |
| LKA haptic (wheel vibration) in conflict with power steering active-assist | Haptic controlled at steering ECU level; coordinate to avoid conflicts |

### Acceptance Criteria
- All GSR 2022 mandatory HMI elements present and functional at type approval
- ISA override indicator: ON within 200 ms of driver override action
- All UN ECE regulation tests passed with zero critical non-compliances

---

## Q35: Multi-Warning Simultaneous Display — Priority Matrix

### Scenario
During a complex urban scenario, the following five warnings trigger simultaneously:
1. FCW (collision imminent)
2. LDW (lane drift)
3. TSR (speed exceeded by 15 km/h)
4. TPMS (tyre pressure low)
5. Fuel low

How does the instrument cluster prioritize which warning is shown prominently, and in which order?

### Expected Behavior
A warning priority matrix governs which warning is displayed in the primary display zone. Safety-critical warnings always preempt comfort/maintenance warnings.

### Priority Matrix

| Priority Tier | Warning Type | Display Position | Example |
|--------------|-------------|-----------------|---------|
| Tier 1 — Critical Safety | Active collision avoidance (AEB/FCW) | Full-screen / HUD overlay | FCW: "BRAKE!" |
| Tier 2 — Safety Alert | LDW, BSD, ACC target loss | Top IC area; HUD | LDW, BSD host icon |
| Tier 3 — Speed/Regulatory | TSR/ISA speed violation | Secondary display band | Speed limit + delta |
| Tier 4 — Driver State | DDAW drowsiness alert | Left IC panel | Coffee cup icon |
| Tier 5 — Maintenance | TPMS, fuel, service | Bottom notification bar | TPMS amber icon |

### In This Scenario
- FCW (Tier 1): takes full-screen priority; all other icons suppressed in main zone.
- LDW (Tier 2): shown as a small persistent icon in the corner.
- TSR (Tier 3): audio muted during FCW active (noise conflict avoidance); icon persistent.
- TPMS (Tier 5): queued for display when Tier 1/2 warnings clear.
- Fuel low (Tier 5): same — queued.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Two Tier 1 warnings simultaneously (e.g., AEB + airbag deployment) | Airbag deployment supersedes AEB (post-event state); display transitions to airbag/SRS indicator sequence |
| FCW dismisses; TPMS immediately appears | TPMS queued; appears ≤ 2 s after Tier 1 dismissal |
| Tier 1 warning during night mode (low IC brightness) | Tier 1 warning forces maximum brightness regardless of night mode setting |
| Distressed driver silences all warnings (panic button): is this allowed? | No: Tier 1 safety warnings cannot be silenced by driver action — regulatory requirement |

### Acceptance Criteria
- Tier 1 warning displayed in primary zone within ≤ 100 ms of trigger
- No two Tier 1 warnings compete for the same IC zone simultaneously (architectural guarantee)
- Tier 4 / Tier 5 warnings always visually present as persistent icons even when deprioritized in main zone

---

## Q36: HMI During Sensor Degradation — Rain / Fog / Dirt on Camera

### Scenario
The front camera is partially occluded by mud (30% of sensor area). This causes LKA and TSR to degrade. How should the instrument cluster communicate sensor degradation to the driver so they understand their current ADAS status?

### Expected Behavior
System must inform the driver:
1. Which systems are affected.
2. Why they are affected.
3. What action the driver should take.

### Display Behavior

| Sensor State | IC Display | Audio | Driver Action Text |
|-------------|-----------|-------|--------------------|
| Clean camera | Normal ACTIVE icons | None | None |
| Partially obscured (30%) | LKA + TSR icons turn amber; "Camera: Clean Sensor" | Single chime | "Camera blocked. Clean windshield." |
| Fully obscured (> 70%) | LKA + TSR icons turn red; systems deactivated | Urgent chime | "LKA/TSR unavailable. Camera blocked." |
| Sensor self-diagnoses temporary blockage (rain) | Yellow icon with rain symbol | None during driving | "Sensor temporarily limited." |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Both radar AND camera degrade simultaneously | All dependent systems (ACC, AEB, LKA, TSR) removed; large warning: "ADAS Systems Unavailable" |
| Camera degrades during active AEB event | Ongoing AEB maintains braking (was committed); post-event: AEB system flags degraded |
| Driver cleans camera; system restores: must it require manual re-engagement? | No — system autonomously restores to STANDBY (driver must re-engage ACTIVE if desired) |
| Sensor failure at night: driver may not see dirt cause | IC text message always explains cause, not just effect |

### Acceptance Criteria
- Sensor degradation reflected on HMI within 3 scan cycles (≤ 150 ms)
- Clear actionable text displayed: symptom + cause + action
- System does not silently degrade — every degradation must have an HMI indicator

---

## Q37: Night Mode and Day Mode Adaptation of ADAS Icons

### Scenario
A driver transitions from daylight into a tunnel and then into full night driving. How should the instrument cluster adapt ADAS icon brightness to ensure readability without causing visual distraction or night blindness?

### Expected Behavior
Auto-brightness dimming based on ambient light sensor (LUX sensor) + headlamp status. ADAS icons maintain their state color meaning while adapting brightness level.

### Brightness Adaptation Logic

```
IF ambient_light > 1000 LUX:
    IC_brightness = 100% (full daylight mode)
ELIF ambient_light > 100 LUX:
    IC_brightness = 60% (overcast/dawn)
ELIF ambient_light > 10 LUX:
    IC_brightness = 30% (dusk)
ELSE:  # < 10 LUX
    IC_brightness = 10−15% (full night mode)
```

- Safety warning override: Tier 1 / Tier 2 warnings always force IC to ≥ 70% brightness temporarily.
- Color preservation: icon colors remain distinguishable (green, amber, red) at all brightness levels.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver manually overrides auto-brightness to 5% at night: FCW fires | FCW forces minimum 60% brightness for duration of FCW event |
| Rapidly changing brightness (strobe lights at events) | Low-pass filter on LUX sensor: adapt over ≥ 2 s window to prevent rapid flicker |
| Tunnel (ambient → 0 LUX rapidly): IC readjusts too fast | LUX → IC brightness lag: 500 ms transition time prevents abrupt change |
| Driver wears polarized sunglasses: IC visible? | IC uses anti-glare coating + IPS panel; tested with polarized glasses |

### Acceptance Criteria
- IC brightness adapts within 1 s of sustained ambient light change
- Icon colors meet ISO 6727 chromaticity requirements at ≤ 15% IC brightness in night mode
- Tier 1 safety warnings override driver brightness setting and reach ≥ 60% brightness

---

## Q38: DTC-to-HMI Correlation — Translating Fault Codes into Driver Messages

### Scenario
A radar sensor develops a fault (DTC: U0100 — Lost Communication with ECU). The IC must show the appropriate icon and message. How is the DTC mapped to a specific HMI message, and what UDS services are used in validation?

### Expected Behavior
Each DTC must map to:
1. A specific IC icon (which system is affected).
2. A severity level (warning / informational).
3. A driver-facing text message.
4. A persistent storage flag (remains after restart until cleared).

### DTC-to-HMI Mapping Table (Examples)

| DTC | System | IC Icon | Severity | Driver Message |
|-----|--------|---------|----------|---------------|
| U0100 | Radar ECU comm loss | ACC/AEB red icon | WARNING | "Collision System Unavailable. Service Required." |
| U0164 | Camera ECU comm loss | LKA/TSR red icon | WARNING | "Lane & Sign Systems Off. Service Required." |
| C0035 | ABS wheel speed sensor | ABS amber icon | CAUTION | "ABS Fault. Normal Braking Available." |
| P0573 | Brake switch signal | AEB amber icon | CAUTION | "Check Brake System." |
| B0083 | DMS camera fault | DMS amber icon | INFO | "Driver Monitor Limited." |

### UDS Validation
- **SID 0x19 (Read DTC Information)**: read all stored DTCs and confirm DTC matches.
- **SID 0x85 (Control DTC Setting)**: temporarily disable DTC setting for test purposes.
- **SID 0x14 (Clear Diagnostic Information)**: clear all DTCs; verify IC icons return to normal.
- **SID 0x27 (Security Access)**: required to clear safety-critical DTCs.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| DTC stored but IC message never shown (silent fault) | Not permitted: every DTC with impact on driver-assessable system must have an IC indication |
| DTC cleared by ECU self-heal (transient fault): IC clears with it | Yes — if DTC auto-heals, IC reverts; driver informed "System Restored" for 3 s |
| Multiple DTCs same system: IC shows one or all? | Show highest severity DTC; all accessible via info menu |
| DTC affects safety but driver cannot tell from IC message | IC message language must be human-readable; no raw code shown to driver |

### Acceptance Criteria
- 100% of DTC codes mapped to an IC message (no silent faults for active safety systems)
- IC message appears within 2 ignition cycles of DTC first detection
- UDS SID 0x14 DTC clear → IC icon clears within 1 ignition cycle

---

## Q39: Speed Limit Display and ISA Integration with the Instrument Cluster

### Scenario
The vehicle has ISA (Intelligent Speed Assistance) using both TSR (camera-based sign recognition) and HD map speed data. When TSR detects a 60 km/h sign but the HD map says 80 km/h, what does the IC display?

### Expected Behavior
The IC should display the TSR-detected speed limit with a visual indication of the source. If there is a conflict, the lower (more conservative) speed limit is shown per typical OEM strategy (or the TSR value supersedes map for real-time signs).

### IC Display Logic

```
IF TSR_value AND map_value agree:
    Display: TSR_value in white circle (standard sign symbol)
    ISA: warn at TSR_value

ELIF TSR_value < map_value:
    Display: TSR_value (TSR reading takes precedence — real sign is current)
    ISA: warn at TSR_value
    Adjacent info: map speed shown in smaller text if desired

ELIF TSR_value > map_value:
    Display: map_value (map is more conservative — may be a missed lower sign)
    Flag for TSR re-query

ELSE (no TSR reading, map available):
    Display: map_value with "M" indicator (map source)
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Variable speed limit sign (LED): TSR reads correct value; map has static value | TSR dynamic value shown; map static value labelled "(Map: 80)" |
| Temporary construction zone (TSR reads 30): OEM set map shows 100 | TSR wins (lower); 30 displayed; ISA warns at 30 |
| TSR fails (night + dirty camera): only map available | Map value displayed; badge "Map" shown to inform driver of source |
| No zone start sign seen yet: what is displayed? | Last confirmed speed retained; grey when uncertain |

### Acceptance Criteria
- Speed limit displayed within 300 ms of TSR detection or map lookup
- When TSR and map conflict: the lower value always displayed (conservative)
- Driver can see the source of the speed limit (TSR camera icon vs. map icon)

---

## Q40: Hands-Off Detection Warning — LKA / GSR 2022 HMI Sequence

### Scenario
Under GSR 2022, LKA must detect hands-off-wheel and warn the driver via a three-stage escalation. Describe the test sequence and expected HMI behavior for each stage.

### GSR 2022 LKA Hands-Off Warning Sequence

| Stage | Time Without Hands on Wheel | HMI | Action |
|-------|---------------------------|-----|--------|
| Stage 1 | 15 s | Amber LKA icon blinks + mild chime | None: driver still has time |
| Stage 2 | 30 s | Amber icon rapid blink + repeated chime + "Place Hands on Wheel" text | Begins preparing to deactivate |
| Stage 3 | 45 s | Red icon + continuous urgent chime + text escalates | LKA deactivates; vehicle follows lane briefly then requests driver action |
| Override | Driver touches wheel at any stage | All warnings clear; timer resets | LKA remains ACTIVE |

### Test Procedure
1. Set LKA ACTIVE on a lane-marked straight road.
2. Driver removes hands from wheel; start timer.
3. Verify Stage 1 at exactly 15 s ± 2 s.
4. Verify Stage 2 at 30 s ± 2 s.
5. Verify Stage 3 and LKA deactivation at 45 s ± 2 s.
6. Driver touches wheel at each stage; verify reset.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver places hands back momentarily for 1 s, then releases: does timer reset? | Depends on OEM calibration: typically yes (contact-based reset); prevents gaming if threshold is > 1 s sustained |
| High-grip gloves (ski gloves): capacitive steering wheel does not detect | Resistive fallback or torque-based hands detection |
| Hands-off during AEB: should Stage 2 fire? | No — during AEB event, hands-off warning is suppressed (system is in control); resumes after AEB |
| Driver is diabetic or incapacitated: no hands response at all | Stage 3 fires; LKA deactivates; vehicle slowly drifts (no auto-pull-over in standard L1/L2) |

### Acceptance Criteria
- Stage 1 fires at 15 s ± 2 s hands-off in 100% of test runs
- Stage 3 LKA deactivation occurs at 45 s ± 3 s
- Timer reset confirmed within 1 scan cycle (≤ 100 ms) of hand contact detection

---

## Q41: Reversing Aid HMI — Visual + Audio Integration with Rear USS

### Scenario
A vehicle reverses toward an obstacle. Six rear USS sensors fire detections. Describe the full IC + audio integration: what is displayed, how audio tone frequency changes with distance, and what the failure mode display looks like.

### Expected Behavior
Distance-proportional audio frequency and visual arc display give precise spatial awareness of obstacle proximity and direction.

### Distance-to-Audio Mapping

| Distance to Obstacle | Audio Tone | IC Visual |
|----------------------|-----------|-----------|
| > 1.5 m | Intermittent slow beep (0.5 Hz) | Yellow partial arc, rear zone |
| 1.0–1.5 m | Intermittent medium beep (1 Hz) | Orange wider arc |
| 0.5–1.0 m | Rapid beep (2 Hz) | Red arc, animated close |
| < 0.5 m | Continuous tone | Full red fill + "STOP" text |
| Obstacle contact | Never reached — system stops vehicle if APA active | N/A |

### Spatial Indication
- The IC (or Center Information Display) shows a bird's-eye graphic of the vehicle.
- USS sensors that detect objects illuminate their corresponding arc segment:
  - Rear-left corner: bottom-left arc illuminated.
  - Rear-center: bottom-center arc illuminated.
  - Rear-right: bottom-right arc illuminated.
- Object distance shown as color (yellow → orange → red) in each arc segment.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| One USS sensor faulty: arc segment shows grey (not black) with "Sensor Limited"  | Yes — grey indicates "sensor not contributing" vs. "no object"; driver not misled |
| Obstacle only visible to one side sensor: asymmetric arc display | Show only the active arc; audio pans slightly to relevant speaker channel |
| High wind causing vehicle to oscillate: USS shows false close object | Temporal filter: ≥ 3 consecutive frames within same range before audio escalation |
| Driver mutes reversing audio (preference): minimum warning still fires | Critical close range (< 0.3 m): audio cannot be muted via user preference — regulatory requirement |

### Acceptance Criteria
- Audio transitions from 0.5 Hz to continuous within distance-band as specified; no step jumps
- Arc display updated within 100 ms of USS detection change
- Sensor fault: grey arc within 1 scan cycle; "Sensor Limited" text persists

---

## Q42: DMS (Driver Monitoring System) State Display

### Scenario
The DMS continuously monitors the driver's gaze, head pose, and eyelid closure rate. How does the IC communicate driver state to the driver without being overly intrusive?

### Expected Behavior
DMS state must remain mostly silent during normal operation. Alerts escalate only when a genuine drowsiness or distraction event is detected.

### DMS State Display Schema

| DMS State | Display | Audio | Condition |
|-----------|---------|-------|-----------|
| Normal monitoring | No icon (or small eye icon in info bar — optional) | Silent | Eyes open, gaze on road |
| First distraction alert | Amber eye icon blinks + "Eyes on Road" text | Single chime | Eyes off road > 3 s |
| Drowsiness warning Level 1 | Coffee cup icon amber | Soft chime | PERCLOS > 0.15 for 30 s |
| Drowsiness warning Level 2 | Coffee cup icon red + animated ZZZ | Repeated chimes + "Rest Advised" | PERCLOS > 0.35 for 60 s |
| Drowsiness emergency | Red icon + full-screen text + continuous chime | "Pull Over Safely" | PERCLOS > 0.5 for 90 s |

**PERCLOS**: Percentage of Eye Closure — the portion of a time window where the eyelid covers ≥ 80% of the eye.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver wearing sunglasses: DMS cannot see eyes | DMS unavailable state; advisory icon: "DMS Limited — Remove Sunglasses" |
| Driver glances at navigation screen (permitted): treated as distraction? | ≤ 2 s glance to IC area = permitted; off-road gaze timer starts after 2 s |
| Right-hand-drive vs. left-hand-drive: DMS camera position changes | DMS camera behind steering column; calibration changes per hand drive variant |
| DMS fires false drowsiness on a long blink: single blink ≠ drowsiness | PERCLOS threshold requires extended high eyelid closure — single blink ignored |

### Acceptance Criteria
- PERCLOS level 1 alert fires at PERCLOS > 0.15 sustained over ≥ 30 s (not single blink)
- DMS alert clears within 5 s of driver demonstrating attentive state
- Zero false drowsiness alerts during normal alert-driving in well-lit conditions

---

## Q43: HMI Validation Using ISO 15007 and Eye-Tracking Studies

### Scenario
During HMI validation, the engineering team needs to verify that the driver can perceive and comprehend the new ADAS dashboard layout without excessive head-down time. Describe the full ISO 15007 validation protocol.

### ISO 15007 Test Protocol

| Metric | Definition | Target |
|--------|-----------|--------|
| **Glance Duration** | Duration of a single gaze toward a display element | ≤ 2.0 s per glance |
| **Total Eyes-Off-Road Time (TEORT)** | Sum of all off-road glances during a task | ≤ 12 s per 15 s window |
| **Task Completion Time** | Time to perceive + comprehend a new ADAS warning | ≤ 2.5 s |
| **Error Rate** | % of participants who misidentify the ADAS warning meaning | ≤ 5% |
| **Number of Glances to Complete Task** | Count of distinct glances needed | ≤ 4 glances |

### Test Setup
- Participants: ≥ 20 drivers (mix of age, experience).
- Vehicle or HiL simulator with representative IC hardware.
- Eye-tracking system (Tobii or equivalent): gaze point mapped to IC regions.
- Scenario: pre-scripted ADAS warning events while driving on closed course or driving simulator.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Elderly participants (> 70 y/o): slower reading speed | Separate analysis subgroup; may require larger icon sizes or longer text duration |
| Participants unfamiliar with ADAS: may not understand icon meaning | Training session prior to test; or test novice users specifically for comprehension |
| Warning occurs simultaneously with a driving demand event (junction): glance suppressed | Glance suppression is expected; warning must persist and repeat until acknowledged |

### Acceptance Criteria
- Mean glance duration to ADAS warning icons: ≤ 1.5 s (design target)
- TEORT during new warning event: ≤ 12 s per 15 s measurement window
- ≥ 95% of participants correctly identify ADAS icon meaning on first exposure (post-ISO-9186 training)

---

## Q44: Cluster Instrument HMI — ACC Target Display (Following Distance Visualization)

### Scenario
While ACC is active, the driver requests a HMI that shows the current following distance, the lead vehicle (as an icon), and the selected time gap. How should this be displayed, and what are the dynamic behaviors during target acquisition and target loss?

### Expected Behavior
ACC HMI provides real-time situational awareness of the ACC target without demanding unnatural levels of driver attention.

### ACC HMI Elements

| Element | Description | Location |
|---------|-------------|----------|
| ACC active green icon | Shows ACC is engaged | IC left cluster |
| Lead vehicle icon | Animated car icon in front of ego | IC center / HUD |
| Following distance bars | 3–5 bars representing current gap setting | IC center |
| Target distance readout | Actual distance to lead vehicle (e.g., "28 m") | Sub-display or HUD |
| Set speed | Current ACC target speed | IC speedometer |

### Dynamic Behaviors

| Scenario | HMI Behavior |
|---------|-------------|
| Target acquired | Lead vehicle icon appears; distance bars populate; sub-display shows distance |
| Target accelerates away (gap widening) | Bars animate to show wider gap; distance readout increases |
| Target brakes hard | Bars animate compress; color shifts amber → red if following close |
| Target lost (cut-out) | Lead vehicle icon fades out; bars disappear; ACC maintains set speed |
| ACC deceleration braking | Brake indicator at bottom of IC illuminates; optional "ACC Braking" text |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| New target acquired at very close range (sudden cut-in): HMI jerks | Smooth animation with ≤ 500 ms transition; distance bars should animate, not jump |
| Driver changes time gap setting (button): bars change immediately | Immediate visual feedback; set gap indicator updates in ≤ 100 ms |
| Lead vehicle detected by radar but not camera: show with lower confidence visual? | Optional: grey-dashed lead vehicle icon instead of solid — indicates sensor caveat |

### Acceptance Criteria
- Target acquisition: lead vehicle icon appears within 200 ms of ACC target lock
- Target loss: icon fades in ≤ 300 ms; ACC smoothly resumes set speed
- Distance readout updates at ≥ 10 Hz (matching ACC control loop rate)

---

## Q45: Full HMI System Integration Test — Scenario-Based IC Validation Matrix

### Scenario
A system integration test must validate the complete IC behavior across all ADAS systems. Describe the test scenario matrix for the final IC validation sprint.

### Test Matrix

| Test ID | Scenario | Expected IC Behavior | Pass Criteria |
|---------|---------|----------------------|--------------|
| HMI-001 | Cold start: all systems ready | All icons in STANDBY (white/grey) | Correct icons within 5 s of ignition on |
| HMI-002 | Driver engages ACC, LKA | ACC green + LKA green within 2 s | No amber or red icons |
| HMI-003 | Camera blocked by mud | LKA/TSR amber; "Clean Camera" text | Within 3 s of degradation |
| HMI-004 | FCW fires (simulated TTC = 2.0 s) | Red FCW icon + chime escalation | Level 2 within 2.0 s TTC |
| HMI-005 | DTC U0100 injected via CAN | ACC/AEB red icon + "Service Required" | Within 2 ignition cycles |
| HMI-006 | Hands-off for 45 s | LKA warning escalation to Stage 3 | All 3 stages fire at correct times |
| HMI-007 | Reversing with obstacle at 0.5 m | Red arc + continuous tone | Tone continuous < 0.5 m |
| HMI-008 | Driver drowsiness (PERCLOS > 0.35) | Coffee cup red icon + "Rest Advised" | Within 60 s of threshold met |
| HMI-009 | 5 simultaneous warnings | Priority matrix governs display | Tier 1 (FCW) in primary zone |
| HMI-010 | Night mode transition | Auto-brightness dims to ≤ 15% | Transition ≤ 1 s at < 10 LUX |
| HMI-011 | ISA: camera reads 60, map says 80 | Display: 60 km/h (TSR value) | ≤ 300 ms after sign detection |
| HMI-012 | ACC target lost (cut-out) | Lead vehicle icon fades; free speed | Within 300 ms |
| HMI-013 | DTC cleared via UDS SID 0x14 | IC icons return to normal | Within 1 ignition cycle |
| HMI-014 | GSR LKA hands-off Stage 2 | Repeated chime + "Place Hands" text | At 30 s ± 2 s |
| HMI-015 | All systems fault simultaneously | "Multiple ADAS Faults — Service" | Highest Tier displayed first |

### Regression Requirement
- All 15 test IDs must pass after any IC software update.
- Automated HIL: CAN message injection → IC video capture → image recognition validation (automated pass/fail per reference screenshot).
- Manual spot check: 3 human evaluators confirm subjective quality (brightness, legibility, tone loudness at headrest).

### Final Acceptance Gate
- 100% HMI test matrix pass before software lock for production.
- Zero Tier 1 warning failures (any miss = automatic stop-ship).
- ≤ 2 Tier 4/5 cosmetic issues acceptable at software lock (must be traced and scheduled for next release).
