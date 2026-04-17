# Forward Collision Warning (FCW) — Scenario-Based Questions (Q1–Q10)

---

## Q1: FCW Activation with a Slow-Moving Vehicle at Highway Speed

### Scenario
Your ego vehicle is traveling at 130 km/h on a motorway. A truck ahead is traveling at 80 km/h in the same lane. The forward radar detects the truck at 120 m distance. The FCW system must decide whether to issue a warning.

### Expected Behavior
The FCW system should calculate Time-to-Collision (TTC) and issue a visual + auditory warning when TTC falls below the configured threshold (typically 2.5–3.5 seconds).

**TTC = Distance / Relative Speed = 120 m / (130–80 km/h) = 120 / 13.89 m/s ≈ 8.6 s**

No warning at 120 m. Warning should trigger when distance closes to ~48 m (TTC ≈ 3.5 s).

### Detailed Explanation
- FCW uses radar (primary), camera (secondary), and sometimes LiDAR for target detection.
- Relative velocity is key: if the truck is accelerating, TTC increases and warning is suppressed.
- The system classifies the target as "valid threat" only if it's in the same lane (using camera or HD map fusion).
- Warning intensity can be staged: early warning (visual only) → urgent warning (auditory + haptic/seat vibration).
- Driver override: if the driver applies brakes or steers away, the warning is canceled.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Truck suddenly decelerates from 80 to 40 km/h | TTC drops abruptly; FCW must re-trigger warning immediately |
| Truck is in adjacent lane but close to lane boundary | Camera must confirm lane occupancy; no warning if outside ego lane |
| Speed limit zone: ego decelerates from 130 to 100 km/h | Relative speed changes; TTC must be recalculated dynamically |
| Radar reflected from bridge/overpass metallic structure | Must distinguish stationary objects above road from vehicles; suppress false FCW |
| Radar low-confidence detection (heavy rain) | System should lower sensitivity threshold or display "FCW degraded" HMI message |
| Driver already braking at 0.5g | Warning suppressed since driver is acting; avoids alert fatigue |
| Night-time, truck has only one working tail light | Camera confidence drops; radar takes primary role |

### Validation Approach
- HIL simulation: replay pre-recorded radar + camera sensor data with synthetic object insertion
- Closed-track test: towing target vehicle at defined speeds
- Euro NCAP CCRs (Car-to-Car Rear stationary) protocol

### Acceptance Criteria
- Warning issued before TTC = 2.7 s in ≥ 95% of test runs
- False positive rate < 1 per 1000 km of normal driving
- Warning canceled within 500 ms of driver brake application

---

## Q2: FCW with Cut-In Vehicle Scenario

### Scenario
The ego vehicle is traveling at 100 km/h. A vehicle in the adjacent lane suddenly cuts in front of the ego vehicle at 70 km/h, inserting itself at a distance of 40 m.

### Expected Behavior
The FCW system should detect the cut-in within 300–500 ms, classify the new object as in-lane threat, and issue warning if TTC < threshold.

**TTC after cut-in = 40 m / 8.33 m/s ≈ 4.8 s** — borderline; system should monitor.

### Detailed Explanation
- Cut-in detection relies on camera tracking lateral position of the vehicle in the adjacent lane.
- The radar may already be tracking this vehicle but treating it as "out-of-lane."
- Sensor fusion must update lane assignment of the target within one sensor cycle (typically 40–100 ms for radar, 33–66 ms for camera).
- Ghost target risk: if the vehicle was not yet tracked by radar (emerging from blind spot), radar cold-start latency could delay warning.
- Lateral velocity component of the cutting vehicle should accelerate lane assignment confirmation.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cut-in at 15 m distance (emergency cut-in) | AEB may activate; FCW issues urgent warning simultaneously |
| Vehicle cuts in then immediately brakes hard | Compound scenario: cut-in + deceleration; must handle priority correctly |
| Multiple vehicles cutting in simultaneously | System must prioritize closest/most dangerous target |
| Cut-in from a motorcycle (narrow object) | Camera-radar fusion must correctly estimate lateral position for narrow targets |
| Ego vehicle in curve; cut-in vehicle on outside of curve | Curvature compensation required for correct lane assignment |

### Validation Approach
- NCAP CCRm (Car-to-Car Rear moving) test protocol
- Soft target cut-in scenarios at test track
- SIL simulation with cut-in trajectory injection

### Acceptance Criteria
- Target classified as in-lane within 400 ms of lateral incursion crossing lane marking
- No false suppression of warning due to delayed lane assignment

---

## Q3: FCW System Behavior During Adverse Weather (Heavy Rain/Fog)

### Scenario
The ego vehicle is driving in heavy rain with visibility reduced to 60 m. The forward radar detects a stationary vehicle ahead at 55 m. Camera visibility is severely degraded.

### Expected Behavior
FCW should still function using radar as primary sensor. A system degradation notice should be shown on HMI. Warning should fire if radar-detected TTC < threshold.

### Detailed Explanation
- Radar is generally weather-independent (77 GHz operates through rain/fog).
- Camera performance degrades significantly in heavy rain/fog.
- Machine learning-based camera relies on contrast; precipitation introduces noise.
- The system should transitions to "radar-only mode" with reduced confidence.
- In reduced confidence mode, FCW threshold can be relaxed (earlier warning) to compensate.
- Road spray from the truck ahead can cause radar multi-path reflections.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Snow accumulation on radar radome | Signal attenuation; radar reports degraded; FCW displays "sensor blocked" |
| Puddle spray (water) causing temporary radar blockage | Transient loss; system should buffer last valid target state for 200–500 ms |
| Dense fog: visibility < 20 m | FCW may issue preemptive warning even without confirmed target if stationary object likely |
| Camera defogging activated | Camera confidence gradually improves; fusion weights update accordingly |
| Wipers at max speed introducing vibration | Camera stabilization must compensate for wiper-induced image blur frames |

### Validation Approach
- Environmental chamber testing (rain, fog, temperature)
- Sensor blockage injection in HIL
- Field testing in wet conditions

### Acceptance Criteria
- FCW must remain functional (radar-only) in precipitation up to 50 mm/h
- HMI degradation message appears within 2 s of sensor blockage detection
- No false positive FCW during road spray events on highway

---

## Q4: FCW Interaction with ACC (Adaptive Cruise Control)

### Scenario
The ego vehicle is in ACC mode, following a lead vehicle at 3.0 s time gap at 110 km/h. The lead vehicle brakes hard at 8 m/s². The ACC control loop begins deceleration. At what point should FCW intervene?

### Expected Behavior
FCW is a warning-only system. When ACC is active and already decelerating, FCW should still monitor independently. If the ACC deceleration is insufficient to avoid collision, FCW escalates to urgent warning and triggers AEB handover.

### Detailed Explanation
- ACC provides up to ~3–4 m/s² deceleration under normal operation.
- If lead vehicle decelerates at 8 m/s², closing velocity increases rapidly.
- FCW monitors TTC independently of the ACC controller.
- At TTC < 2.0 s, FCW issues urgent warning even if ACC is active.
- At TTC < 1.5 s, AEB takes control with up to 8–10 m/s² deceleration.
- The transition ACC → FCW → AEB must be seamless without actuator conflicts.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| ACC set speed lower than current speed (downhill) | Ego may be accelerating despite ACC; FCW must use actual speed, not set speed |
| Driver cancels ACC during emergency braking | AEB must maintain braking even if ACC is disengaged |
| Lead vehicle decelerates at 12 m/s² (panic brake) | AEB activates; FCW warning serves as pre-alert for driver |
| Multiple vehicles ahead: lead vehicle collision with vehicle ahead | Chain collision scenario; FCW tracks nearest threat |

### Acceptance Criteria
- FCW warning issued before AEB activation in all test scenarios
- No actuator conflict between ACC decel and AEB activation

---

## Q5: FCW False Positive — Stationary Roadside Objects

### Scenario
The ego vehicle is traveling at 90 km/h on a national road. A metal guardrail runs along the right side of the road at 1.5 m lateral distance. The radar detects the guardrail at 0 relative velocity.

### Expected Behavior
FCW should NOT issue a warning. The guardrail is a roadside stationary object, not in the ego vehicle's path.

### Detailed Explanation
- Radar detects all objects including stationary ones that the vehicle is approaching.
- Without camera fusion, radar alone would calculate TTC with every stationary object in range.
- Camera provides lane boundary information to determine if the object is within the ego lane.
- Map-based context (HD map or low-cost map) can confirm that guardrails are expected on this road.
- The FCW object classification pipeline must apply:
  1. Lateral position filter: objects outside lane width + margin are suppressed
  2. Object type classification (road infrastructure vs. vehicle)
  3. Height filter: guardrails have low radar cross-section and consistent height

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Guardrail extends into road due to construction zone | Camera detects lane narrowing; object reclassified as potential threat |
| Fallen tree partially in lane | Irregular shape; camera + radar must classify as obstacle |
| Parked vehicles on roadside very close to lane | Lateral margin filter must distinguish parked vs. encroaching vehicle |
| Tunnel walls (narrow tunnel) | High radar reflectivity; must suppress tunnel wall false positives |
| Road sign gantry overhead | Height filter and pitch filter suppress overhead stationary objects |

### Acceptance Criteria
- Zero false positive FCW warnings due to guardrails in 10,000+ km validation drive
- Correct suppression rate ≥ 99.9% for known road infrastructure objects

---

## Q6: FCW Sensitivity Tuning for Urban vs. Highway Driving

### Scenario
The FCW system uses a fixed TTC threshold of 2.5 s. A validation team reports excessive false positives in city driving (due to stop-and-go traffic and red lights). How should the system be adapted?

### Expected Behavior
The FCW system should use context-aware thresholds:
- **Urban < 60 km/h**: Higher suppression, TTC threshold reduced to 1.8–2.0 s, with speed-dependent filtering
- **Highway > 100 km/h**: Standard threshold of 2.5–3.0 s
- **Transition zones**: Smooth hysteresis between modes

### Detailed Explanation
- In urban stop-and-go traffic, vehicles decelerate frequently and predictably at traffic lights.
- A fixed 2.5 s TTC at 50 km/h would fire warnings at ~35 m — far too sensitive for normal urban stops.
- Speed-dependent TTC calibration is standard in production systems.
- Additionally, map data can identify upcoming traffic lights (V2X or camera TSR) to pre-condition the FCW.
- Driver behavior learning (adaptive calibration) can further reduce false positives based on individual braking patterns.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Urban road with sudden pedestrian crossing | FCW must remain sensitive to pedestrians even in suppressed urban mode |
| Vehicle stops suddenly at zebra crossing | Quick deceleration without prior warning; FCW must still alert |
| Highway construction zone with reduced speed | Temporary speed-based mode change |
| School zone (20 km/h) with children near road | Maximum sensitivity required despite low speed |

### Acceptance Criteria
- False positive rate < 0.5/100 km in urban driving
- Detection rate > 99% for genuine collision threats in all speed zones

---

## Q7: FCW with Trailer Towing Configuration

### Scenario
The ego vehicle is towing a caravan at 90 km/h. The rear of the caravan extends the vehicle's braking distance by 40% due to added mass. The FCW calibration is based on the unladen vehicle's braking performance.

### Expected Behavior
FCW should adapt TTC thresholds and warning timing when trailer/caravan is detected, allowing additional stopping distance margin.

### Detailed Explanation
- Modern vehicles can detect trailer presence via the towbar electrical connector (7/13-pin trailer socket signal on CAN).
- When trailer flag = TRUE, FCW increases TTC threshold to account for longer stopping distance.
- Brake force distribution also changes, affecting AEB performance if it later activates.
- Trailer sway detection (via yaw rate sensor) can provide additional state awareness.
- Radar behind the ego vehicle may be blocked by the trailer; rear FCW/RCTA must account for this.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Trailer connector short circuit sending false trailer present signal | System must validate against vehicle mass estimation (acceleration-based) |
| Trailer with heavy load (horses, construction materials) | Mass estimation via longitudinal acceleration vs. throttle input |
| Articulated trailer (longer swing radius in curves) | FCW keeps straight-line TTC; AEB braking ramp adapted |
| Trailer detaches while driving | Loss of trailer signal; revert to normal FCW calibration |

### Acceptance Criteria
- FCW warning offset increases by ≥ 30% when trailer flag is active
- No FCW suppression failure when trailer is towed on motorway

---

## Q8: FCW System Latency and Real-Time Requirements

### Scenario
The FCW system's end-to-end latency from sensor input to warning output is measured at 350 ms under normal load. Under high ECU CPU load (multiple ADAS features active simultaneously), it spikes to 650 ms. Is this acceptable?

### Expected Behavior
FCW E2E latency must remain < 500 ms under all operational conditions. 650 ms is a functional safety violation.

### Detailed Explanation
- ISO 26262 mandates that safety-critical functions meet their timing requirements under worst-case conditions.
- FCW is typically ASIL-B (Automotive Safety Integrity Level).
- E2E latency budget typically: radar frame rate 20 ms + camera frame rate 33 ms + fusion 20 ms + threat assessment 10 ms + HMI output 5 ms = ~88 ms typical.
- Worst-case with OS scheduling, interrupt handling, and bus latency should not exceed 300–500 ms.
- CPU load monitoring must trigger ADAS feature degradation before safety thresholds are breached.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| OTA update running in background during drive | ADAS system partitioned from OTA process; QoS enforced |
| Multiple sensor dropouts simultaneously | Watchdog triggers safe state; FCW deactivates gracefully |
| CAN bus overload condition | FCW CAN messages assigned highest priority (low CAN ID number) |
| ECU thermal throttling (hot weather, steep climb) | Performance monitoring with automatic feature load-shedding |

### Acceptance Criteria
- P99 FCW latency < 500 ms in 1,000,000 simulated cycles
- Maximum latency < 600 ms; alarm at > 400 ms (diagnostic DTC set)

---

## Q9: FCW Warning Suppression Logic (Nuisance Avoidance)

### Scenario
During validation testing, the FCW system fires a warning every time the ego vehicle approaches a toll booth queue at low speed. The driver considers these as nuisance warnings and disables FCW. How should the system be improved?

### Expected Behavior
FCW should have intelligent suppression for predictable slow-speed scenarios while maintaining safety.

### Detailed Explanation
- **Map-based suppression**: Known toll locations in HD map can pre-condition FCW to apply urban mode early.
- **Speed threshold**: At < 30 km/h relative speed, FCW warning threshold is tightened to avoid nuisance.
- **Brake-already-applied suppression**: If driver is braking, warning is suppressed.
- **Queue detected pattern**: If the ego vehicle has been in stop-and-go for > 60 s, urban queue mode activates.
- **V2I (Vehicle-to-Infrastructure)**: Toll plaza speed advisory can be received via DSRC/C-V2X.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Toll booth on motorway with sudden unexpected queue | If approaching at 110 km/h with queue at 0 km/h, FCW must fire (genuine threat) |
| Driver ignores FCW and does not brake | AEB escalation must proceed regardless of nuisance suppression history |
| Construction zone mobile toll (unmapped) | No map data; rely on camera + radar target classification |

### Acceptance Criteria
- Nuisance warning rate in toll/stop-and-go: < 0.2 events per 100 km in city drive
- No suppression of genuine collision warnings in the same scenarios

---

## Q10: FCW Diagnostic and Fault Management

### Scenario
During a production vehicle field report, customers report that the FCW warning light is permanently ON and the system is inactive. The DTC log shows: `DTC 0xC1234 – FCW Radar Signal Lost`. What is the validation test for this failure mode?

### Expected Behavior
When the forward radar is disconnected or reporting invalid data, FCW must:
1. Detect the fault within 100 ms
2. Store a DTC with relevant snapshot data
3. Display FCW degraded/inactive HMI warning to driver
4. Deactivate FCW to avoid false warnings
5. Reactivate when radar fault clears on next ignition cycle after repair

### Detailed Explanation
- Fault detection is implemented via:
  - Radar hardware fault signal on private CAN/Ethernet
  - Signal quality monitoring (missed cycles, CRC errors)
  - Plausibility check: radar silent while vehicle moving > 30 km/h
- ISO 26262 fault tolerant time interval (FTTI) for FCW is typically 100–500 ms.
- DTC must capture: odometer, speed, fault timestamp, fault counter.
- HMI icon should comply with ISO 7000 symbol set.
- Limp-home mode: other ADAS features using radar (ACC, AEB) also deactivate.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Radar temporarily blocked (mud on fascia) | DTC set after 2 s of continuous blockage; clears automatically when radar recovers |
| Radar CAN timeout (bus-off condition) | ECU bus error handling; radar fault cascades only to FCW, not unrelated systems |
| Radar firmware update failure | Radar enters safe state; DTC stored; FCW deactivated |
| Intermittent fault (connector corrosion) | DTC stored as intermittent (confirmed after 3 occurrences); does not re-activate without service |

### Validation Approach
- Fault injection testing: disconnect radar CAN, power cycle, inject CRC error messages
- Verify DTC storage in non-volatile memory
- Verify HMI message timing and content

### Acceptance Criteria
- DTC set within 200 ms of radar fault onset
- FCW inactive state confirmed by absence of warning in forced collision scenario
- HMI warning visible within 1 s of DTC confirmation
