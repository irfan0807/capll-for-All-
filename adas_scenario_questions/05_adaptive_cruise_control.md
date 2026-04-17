# Adaptive Cruise Control (ACC) — Scenario-Based Questions (Q41–Q50)

---

## Q41: ACC Target Loss — Lead Vehicle Exits Motorway

### Scenario
The ego vehicle is in ACC mode at 120 km/h following a lead vehicle at a 1.8 s time gap. The lead vehicle exits the motorway (takes an off-ramp). The ego vehicle loses its ACC target. What should happen?

### Expected Behavior
When the lead vehicle exits the lane (exits the radar/camera coverage zone), ACC should:
1. Detect target loss within 1–2 s
2. Resume set speed (120 km/h) if no new target is found
3. Accelerate smoothly (not abruptly) back to set speed
4. Display HMI change: "ACC — no vehicle detected" → free-speed mode

### Detailed Explanation
- ACC continuously tracks the lead vehicle via radar range/velocity and camera lane assignment.
- Target loss can occur due to: cut-out, exit, vehicle stopped (and ego passes it), or sensor limitation.
- On target loss, the ACC system uses a "target handoff" timer (typically 1–3 s) before switching to free-speed mode.
- Smooth acceleration: the return-to-set-speed acceleration rate is limited to ~1.5–2.0 m/s² for comfort.
- New target acquisition: if a new vehicle enters the lane ahead, ACC reacquires and adjusts gap automatically.
- Edge: an abrupt return-to-set-speed after a city exit (where lead was going very slow) could be jarring — the acceleration must be ramped.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Lead vehicle moves to right lane before exit (gradually moves away) | Smooth target handoff; ACC begins accelerating while lead is still partially tracked |
| Lead vehicle disappears behind a hill crest | Temporary target loss; ACC maintains speed for grace period before re-accelerating |
| New vehicle cut in from off-ramp entrance (joining motorway) | ACC acquires new target; adjusts gap to new vehicle |
| Lead vehicle suddenly brakes before exit | AEB covers the gap; then target exits after braking event |
| ACC set speed 120 km/h but road speed limit 100 km/h (TSR integration) | ACC should respect dynamic speed limit if TSR-integrated; max 100 km/h |

### Acceptance Criteria
- Target loss detected within 1.5 s of vehicle exit from radar coverage
- Return-to-speed acceleration ≤ 2 m/s²
- New target acquisition within 1 sensor cycle (50 ms) of new vehicle entering lane

---

## Q42: ACC in Stop-and-Go Traffic (Low-Speed ACC)

### Scenario
The ego vehicle is in Stop-and-Go ACC (also called Low-Speed Follow or Traffic Jam Assist mode) on a motorway. The lead vehicle stops. ACC brings the ego vehicle to a standstill. The lead vehicle then moves forward. How long can the ego vehicle wait before auto-resuming, and what are the safety conditions for auto-resume?

### Expected Behavior
- Auto-resume after standstill: typically allowed within 2–5 s after stop (depending on OEM policy).
- After > 3 s standstill: driver must either press resume button OR apply mild accelerator to resume.
- This reduces risk of unintended acceleration after longer stops (e.g., at traffic lights where lead car accidentally moved then stopped again).

### Detailed Explanation
- ISO/SAE Level 1 ACC: driver must remain attentive and initiate resumption after long stops.
- Level 2 IAD (Integrated Active Driving Assistance) includes hands-free stop-and-go with auto-resume.
- The 3 s threshold is a compromise: too short (< 1 s) can restart before a pedestrian clears; too long (> 5 s) requires too many manual re-activations in heavy traffic.
- In L2 systems with DMS (Driver Monitoring), hands-free auto-resume up to 30 s may be permitted if driver gaze is confirmed on road.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Lead vehicle moves forward 2 m then stops again | ACC resumes, closes gap, stops again smoothly |
| Traffic light changes to green — lead vehicle moves | Auto-resume if < 3 s stopped; driver prompted if > 3 s |
| Emergency vehicle passes → lead vehicle pulls over → front is clear | ACC target = absent; driver must re-engage for free-speed travel |
| Stop on steep hill: rollback risk | Hill hold active during ACC stop; prevents rollback before drive torque engages |
| ACC set to minimum following gap but lead vehicle stops in pedestrian crossing box | Ego vehicle should not stop in the box; conflict with traffic regulation |

### Acceptance Criteria
- Auto-resume available within 3 s of standstill without driver input
- Above 3 s: driver prompt displayed; ACC does not auto-resume
- Zero unintended accelerations from ACC in stop-and-go validation cycle

---

## Q43: ACC with Speed Limit Sign Integration (ISA — Intelligent Speed Assistance)

### Scenario
The ACC set speed is 130 km/h. The vehicle enters a 110 km/h speed limit zone (detected via camera TSR + map). Should ACC automatically reduce set speed to 110 km/h?

### Expected Behavior
EU GSR 2022 mandates Intelligent Speed Assistance (ISA) that warns the driver of speed limit exceedance. Integration with ACC creates "speed limit-respecting ACC":
- With ISA-ACC integration: ACC automatically caps at 110 km/h in 110 km/h zone.
- Without integration: ACC maintains 130 km/h; ISA provides separate audio/visual warning.

### Detailed Explanation
- Euro NCAP 2025+ evaluates ISA integration with ACC.
- The driver should remain able to override ISA if needed (e.g., overtaking maneuver).
- TSR must have high confidence before adjusting ACC speed (prevent erroneous speed limit triggers).
- Map-confirmed speed limits (here vs. camera-detected): when map and camera disagree, the lower of the two is preferred by safety-first systems.
- Temporary speed limits (construction zone, school zone time-of-day) must also be respected.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Speed limit sign damaged/misread (180 km/h on 80 km/h road) | Sanity check: if detected limit > road category max, reject; use map as fallback |
| Variable speed limit sign (electronic, between 60 and 100 km/h) | Camera must read current displayed value in real-time |
| Driver sets ACC to 120 km/h in a 130 km/h zone | ACC follows driver set speed (lower than limit); no conflict |
| Speed limit increases: 80 km/h → 120 km/h | ACC may remain at 80 km/h; driver has option to increase set speed |
| Derestricted autobahn (no speed limit sign) | ACC reverts to driver set speed; no ISA constraint |

### Acceptance Criteria
- ACC speed cap active within 3 s of confirmed speed limit zone entry
- Driver override acknowledged within 500 ms
- Zero ACC over-speed in ISA-integrated mode under valid speed limit signs

---

## Q44: ACC Target Selection in Multi-Lane Scenarios

### Scenario
The ego vehicle is in lane 2 of a 3-lane highway. A vehicle in lane 2 is at 50 m; a large truck in lane 1 is at 30 m (but in the adjacent lane). ACC selects the truck as the target (wrong selection). The ego decelerates unnecessarily.

### Expected Behavior
ACC must select only targets confirmed to be in the ego vehicle's lane. The truck in lane 1 should not be selected as the ACC target.

### Detailed Explanation
- Target selection uses camera lane assignment (which lane the object is in) + radar range/velocity.
- If only radar is used: short-range truck at 30 m in adjacent lane may receive target priority (closer target).
- Camera fusion is essential: camera confirms the truck is in lane 1, not lane 2.
- Road curvature: on a curve, the radar beam may briefly cover objects in adjacent lanes as the vehicle turns — camera must confirm lane assignment continuously.
- ACC target selection priorities: in-lane vehicle nearest to ego > cut-in vehicle > no target.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Lane line between ego lane and truck lane is worn | Camera less confident; conservative approach: may select truck if ambiguous until clean lane detected |
| Truck straddling lane markings (partial intrusion) | If > 50% truck width in ego lane, treat as in-lane target |
| Three vehicles in front at different distances | Select nearest in-lane vehicle |
| ACC on curved road: temporarily appears next-lane vehicle is in ego path | Curvature-corrected path prediction used for target lane assignment |

### Acceptance Criteria
- Adjacent lane vehicle NOT selected as ACC target in 100% of structured test cases
- In-lane target selected correctly within 1 sensor cycle (50 ms) of appearance

---

## Q45: ACC Emergency Override — Driver Brakes Harder Than ACC

### Scenario
ACC is controlling the vehicle at 100 km/h, maintaining a 2.5 s gap to the lead vehicle. A child runs into the road ahead of the lead vehicle. The driver of the lead vehicle brakes at 9 m/s². The ACC controller is responding but the driver applies additional emergency braking.

### Expected Behavior
When the driver applies braking force greater than the ACC deceleration command, the driver's braking takes priority. ACC should acknowledge the override and not resist. After the hazard, ACC should offer to resume.

### Detailed Explanation
- When driver brake pedal pressure exceeds ACC brake request pressure, ACC enters "driver override" state.
- The ESC/brake system routes driver pressure as primary command.
- ACC does not re-engage automatically after driver brake override — driver must press Resume.
- This is a critical safety design: driver must always have authority over the automation.
- Post-override: if the gap to lead is still > set gap and speed < set speed, ACC resume is prompted.
- In L2+ systems: automated resume can be offered after driver releases brakes and confirms (button or eye gaze).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver taps brakes lightly (speed adjustment, not cancellation) | Small brake event may not cancel ACC; depends on calibration (pressure threshold) |
| Driver applies brakes then immediately releases at highway cruise | ACC resumes automatically in some configurations (short-tap override) |
| Brake fade condition (overheated brakes descending mountain pass) | ACC deceleration effectiveness reduced; warn driver |

### Acceptance Criteria
- Driver brake override acknowledged within 50 ms of pedal application
- ACC deactivates or enters override hold state within 100 ms
- ACC resume button/offer presented after hazard clears

---

## Q46: ACC with Speed Humps and Aggressive Road Surface

### Scenario
The ego vehicle is in ACC mode at 60 km/h on a suburban road. It encounters a speed bump (marked at 30 km/h). ACC is not aware of the speed bump and maintains 60 km/h through it, causing impact damage.

### Expected Behavior
ACC should not automatically navigate speed humps. This is outside ACC's ODD. The driver must override ACC speed for speed humps. However, ACC + map integration (if speed bump locations are in HD map) can proactively reduce speed.

### Detailed Explanation
- Standard ACC ODD: motorways, highways, and dual carriageways above 40 km/h.
- ACC is NOT designed for residential speed hump roads.
- Use case misuse: driver using ACC in an ODD not designed for it.
- Mitigation: geofencing — ACC deactivates in residential zones below 30 km/h or on roads with speed humps in HD map.
- Road type detection via camera (road classification ML model) can also identify roads inappropriate for ACC.
- The driver's manual represents the ODD limitations; the vehicle's HMI should warn when ACC is active in inappropriate zones.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Unmapped speed humps (new development) | No map data; ACC remains active; driver must take control |
| Rumble strips on highway edge (misidentified as speed humps) | ACC continues; rumble strips are not in ego vehicle path |
| Sleeping policeman (temporary road calming measure) | Unmapped; driver responsibility |

### Acceptance Criteria
- Map-based speed hump zone: ACC displays "ACC limited zone" and limits speed to 30 km/h OR deactivates
- ACC ODD limitations documented in driver manual and HMI tooltip

---

## Q47: ACC Calibration — Time Gap Setting and Following Distance Accuracy

### Scenario
The ACC is configured for a 2.0 s time gap. At 100 km/h, the actual measured following distance in testing is 47 m instead of the expected 55.6 m (= 100/3.6 × 2.0 = 55.6 m). A 15% error is observed. What is the root cause and specification?

### Expected Behavior
ACC following distance accuracy should be within ±10% of the set time gap distance. A 15% error indicates a calibration bug, radar range bias, or a control loop gain error.

### Detailed Explanation
- The ACC controller receives: set time gap (s), ego speed (km/h), lead speed (km/h), lead range (m) from radar.
- Target following distance = set_gap × ego_speed.
- Discrepancy causes:
  1. **Radar range bias**: if radar under-reports distance by 15%, controller will follow at a shorter gap.
  2. **Control loop gain error**: the gap-closing PID/feed-forward may overshoot toward the lead.
  3. **Speed signal error**: if speed input is slightly overestimated, target gap calculation is larger but vehicle is following based on actual speed.
- Root cause analysis via data logging: compare radar reported range, actual range (GPS-based ground truth), and ego speed.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| High speed (180 km/h): gap error more safety critical | Acceptance criteria tighter at higher speeds (±5%) |
| Lead vehicle decelerating rapidly | Dynamic overshoot; ACC response latency may cause temporary shorter gap |
| Wet road (radar multi-path): range underestimation | Environmental calibration check required |

### Acceptance Criteria
- Following distance: set_gap × ego_speed ± 10% at steady state
- No systematic range bias > 5% in static radar range tests

---

## Q48: ACC with High-Speed Queue Warning Integration

### Scenario
ACC is active at 130 km/h on a motorway. A sudden traffic queue ahead (congestion wave / phantom traffic jam) reduces traffic to 30 km/h within 300 m. ACC begins decelerating but the deceleration rate (2.5 m/s²) may not be sufficient. FCW and AEB take over progressively.

### Expected Behavior
- ACC begins decelerating at its maximum comfortable rate (~3 m/s²)
- If deceleration insufficient, FCW issues warning
- AEB activates up to 9 m/s² if TTC < 1.5 s
- Smooth handover: ACC → FCW → AEB → full stop → ACC standstill mode

### Detailed Explanation
- This scenario is the most dangerous for ACC: sudden dense queue appearing.
- The ACC controller is not designed for emergency braking; it hands off to AEB.
- Coordination: the brake system must arbitrate between ACC and AEB commands without conflicting.
- Pre-fill: hydraulic pre-fill at FCW stage reduces AEB response time.
- V2X: queue warning from C-ITS (Cooperative ITS) can give 500+ m early warning of congestion.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Congestion on downhill grade | Braking effort increased due to gravity; AEB must compensate |
| Lead vehicle's AEB activates: brake lights flash rapidly | ACC detects rapid deceleration via brake light camera; increases decel rate |
| Night-time: no advance brake light warning | Radar-only detection; reaction time slightly longer |

### Acceptance Criteria
- ACC → AEB escalation seamless with no gap in vehicle deceleration
- Maximum speed change per deceleration stage within comfort limits unless emergency

---

## Q49: ACC Energy Efficiency in Electric Vehicles

### Scenario
An EV with ACC active is navigating a downhill section. The ACC tries to maintain the set speed by not accelerating. However, it is not using regenerative braking, so the vehicle overspeeds. How should ACC interact with regenerative braking?

### Expected Behavior
ACC in an EV should use regenerative braking as the primary deceleration method (for energy recovery) when following a lead vehicle or approaching a set speed limit downhill.

### Detailed Explanation
- ACC speed/gap control loop commands deceleration: in ICE vehicles = friction brakes; in EV = regenerative braking first, then friction brakes if insufficient.
- Regenerative braking limit: typically 3–4 m/s² (motor torque limited); friction brakes supplement beyond this.
- ACC regen blending: the powertrain and brake ECU arbitrate the regen + friction blend.
- Energy benefit: using regen during ACC following can recover 10–15% of energy vs. friction-only.
- In downhill scenario: regen must be used to maintain set speed and prevent overspeeding.
  
### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Battery fully charged (100% SoC): regen unavailable | Friction brakes used exclusively; ACC still functional |
| Steep downhill requiring > 4 m/s² deceleration | Hybrid regen + friction; coordinated by brake controller |
| One-pedal driving mode enabled: regen very strong | ACC must account for one-pedal regen in its control loop |
| Cold battery: regen capacity limited | Reduced regen capability flag sent to ACC; friction bias increased |

### Acceptance Criteria
- ACC uses regen as primary deceleration at available regen capacity
- No overspeed on downhill gradients ≥ 5% with ACC active
- Smooth brake blending with no vehicle pitch oscillation

---

## Q50: ACC Data Recording and Event Log for Liability

### Scenario
After a rear-end collision, the insurance company requests data: was ACC active? What was the set gap, approach speed, and when did ACC/AEB activate? The ADAS ECU must provide this data.

### Expected Behavior
The ADAS ECU should store an event data recorder (EDR) log containing:
- ACC active status and set parameters (speed, time gap)
- Radar range and relative velocity of lead vehicle
- FCW/AEB activation timestamps
- Driver override events
- 5 s pre-event and 2 s post-event data

### Detailed Explanation
- EU Regulation 2019/2144 mandates EDR (Event Data Recorder) for new vehicles from 2024.
- ADAS EDR data requirements include: vehicle speed, brake status, and ADAS active status.
- The data must be tamper-evident (CRC protected, write-once during event).
- UDS service 0x19/0x2C can be used for DTC and snapshot data retrieval by OBD tools.
- GDPR: EDR data must comply with data protection rules; personal data access restricted.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Battery disconnected after accident | EDR must have super-capacitor backup to complete write during power outage |
| Multiple events in one drive: log overwrite | Ring buffer with event priority; collision event highest priority (not overwritten) |
| Unauthorized data access via OBD port | Authentication required; diagnostic session security access needed |
| Data format dispute: raw sensor vs. interpreted data | Both raw and interpreted data logged; timestamps synchronized to UTC via GNSS |

### Acceptance Criteria
- EDR stores ≥ 5 s pre-event data at ≥ 10 Hz sample rate
- Data accessible via standard diagnostic tool within 7 s of connection
- CRC verification passes for all stored events
