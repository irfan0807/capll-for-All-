# Automatic Emergency Braking (AEB) — Scenario-Based Questions (Q11–Q20)

---

## Q11: AEB Activation Threshold — Car-to-Car Rear Stationary (CCRs)

### Scenario
The ego vehicle is traveling at 80 km/h. A stationary vehicle is ahead at 30 m on a dry road. The FCW has already issued a warning but the driver has not reacted. The AEB system must decide to intervene.

### Expected Behavior
AEB should activate with full braking (up to ~9 m/s²) to reduce or eliminate collision speed.
- Required stopping distance from 80 km/h with 9 m/s² deceleration = 27.4 m.
- At 30 m, full AEB braking can achieve a complete stop. AEB should fire immediately.

### Detailed Explanation
- AEB uses the same radar + camera fusion as FCW but has its own threat assessment layer.
- Activation conditions: TTC < 1.5 s AND no driver braking action detected AND confidence ≥ threshold.
- AEB cannot wait for FCW; it monitors independently with its own TTC/TTC-derivative metric.
- The braking profile is typically a ramp: 0 → full deceleration in ~100–150 ms to avoid passenger discomfort and wheel lockup.
- ABS (Anti-lock Braking System) coordinates with AEB to prevent wheel lockup during emergency stop.
- Pre-fill: brake hydraulic system pre-pressurizes at FCW stage for faster AEB response.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Stationary vehicle is a parked car half-on pavement | Camera must confirm object is in ego lane; radar provides range |
| Vehicle ahead is a trailer without a towing vehicle (stationary trailer) | Low radar cross-section at rear; must use camera to confirm obstacle |
| Ego vehicle is on ice (low mu road) | AEB activates but ABS limits effective deceleration; residual impact speed higher |
| Driver steers at the last moment | AEB should detect steering input and release braking to avoid counteracting avoidance maneuver |
| Stationary vehicle is at the crest of a hill (appears suddenly) | Reduced preview time; AEB must act with < 1 s TTC |

### Validation Approach
- Euro NCAP AEB CCRs protocol (10, 20, 30, 40, 50, 60, 70, 80 km/h test speeds)
- Soft target (deformable vehicle target) at proving ground
- HIL simulation for calibration parameter sweep

### Acceptance Criteria
- Collision avoided or speed reduced to < 10 km/h for ≥ 80% of Euro NCAP CCRs test cases
- No AEB false activation in 10,000 km normal driving

---

## Q12: AEB with Pedestrian — Adult Pedestrian Crossing Scenario

### Scenario
The ego vehicle is traveling at 40 km/h. An adult pedestrian steps off the pavement and walks across the road at a perpendicular angle (90°). The pedestrian is at 12 m distance. The driver does not react.

### Expected Behavior
AEB-Pedestrian (AEB-P) should detect the pedestrian and activate emergency braking to avoid or reduce collision impact.

### Detailed Explanation
- AEB-P is a separate function from AEB-Car, with pedestrian-specific detection algorithms.
- Pedestrians are detected using camera (primary) + radar (secondary, due to low radar cross-section of humans).
- Pedestrian classification: using deep learning CNN on camera frames.
- Key challenge: distinguishing walking pedestrian from cyclist, child, or adult in different poses.
- At 40 km/h crossing scenario with 12 m, TTC ≈ 1.08 s — AEB-P must activate immediately.
- The pedestrian's trajectory (perpendicular crossing) means collision probability is high if no braking.
- AEB-P checks that the pedestrian is in collision path using predicted trajectory intersection.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Pedestrian stops midway (hesitates) | Predicted trajectory becomes uncertain; AEB holds braking conservatively |
| Pedestrian wearing dark clothing at night | Camera sensitivity drops; NIR illumination or thermal camera used if equipped |
| Two pedestrians walking together (occlusion) | Track nearest pedestrian; maintain tracking during brief occlusion |
| Child pedestrian (smaller bounding box) | Child detection model must handle sub-1.2 m height targets |
| Pedestrian stepping back onto pavement | Trajectory reversal; AEB releases braking if collision path no longer predicted |
| Jogger running at 4 m/s (faster than walking) | Velocity estimate must be accurate; AEB activates earlier due to higher crossing speed |
| Pedestrian in costume / unusual silhouette | Robust feature extraction needed; test with holiday/event clothing |

### Validation Approach
- Euro NCAP AEB Pedestrian protocol (VRU — Vulnerable Road User)
- Test dummy pedestrian target (Humanetics Adult Male)
- Night testing with varying luminance levels

### Acceptance Criteria
- Collision avoidance or significant speed reduction (≥ 20 km/h reduction) in NCAP test cases
- No AEB-P false positives from traffic cones, bollards, or road furniture

---

## Q13: AEB False Activation on a Speed Bump

### Scenario
The ego vehicle is driving at 30 km/h in a car park. The forward radar detects the raised profile of a speed bump at 8 m distance. The AEB system activates emergency braking, startling the driver. This is a false positive.

### Expected Behavior
AEB should NOT activate for speed bumps, road humps, or road markings on the road surface.

### Detailed Explanation
- Speed bumps are detected by radar as a low-height, extended stationary target across the full lane width.
- The challenge: at close range, radar may classify a speed bump with characteristics similar to a stopped vehicle.
- Mitigation strategies:
  1. **Height estimation**: radar + camera can estimate object height; speed bumps are < 10 cm, vehicles are > 50 cm.
  2. **Semantic camera classification**: camera must label speed bump as road infrastructure.
  3. **Map-based annotation**: HD map marks speed bump locations.
  4. **Pattern matching**: extended radar return across lane width is characteristic of speed bump (vs. vehicle which has narrower lateral extent).
- AEB suppression for height-filtered objects should NOT suppress genuine low-profile obstacles (fallen luggage, road debris).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Large speed bump (aggressive hump, 15 cm height) | Camera + radar still classify correctly; no AEB |
| Temporary speed cushions (rubber, different profile) | Must be classified similarly to permanent humps |
| Speed bump at night with spray paint worn off | Camera lacks visual cue; must rely on radar height classification |
| Collapsed road surface (pothole/sinkhole emerging) | AEB should NOT suppress; genuine road hazard |
| Road debris at similar height as speed bump | If in path and not classifiable as road surface element, maintain AEB sensitivity |

### Acceptance Criteria
- Zero AEB false activations for speed bumps in dedicated test protocol (50 passes)
- Speed bump correctly suppressed at speeds 5–50 km/h

---

## Q14: AEB Interaction with Manual Override (Drive-by-Wire)

### Scenario
AEB activates at 60 km/h due to a genuine obstacle. The driver simultaneously applies full throttle (panic reaction). In a by-wire system, both AEB brake command and driver throttle command arrive at the same time. What is the correct system behavior?

### Expected Behavior
AEB braking must take priority over driver throttle input during active emergency braking. The throttle request is suppressed for the duration of AEB activation.

### Detailed Explanation
- This is addressed by ISO 26262 as an ASIL conflict resolution scenario.
- The braking ECU (ESC/AEB controller) overrides the powertrain throttle request via coordinated control.
- Most modern architectures implement a "brake priority" state machine in the chassis domain controller.
- Torque arbitration: powertrain torque request is zeroed when brake pressure > N bar AND AEB flag = active.
- The driver is notified via haptic (brake pedal feedback) and visual HMI.
- After AEB release, throttle control returns to driver seamlessly.
- This scenario is classified as a misuse case in SOTIF analysis (ISO 21448).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver applies brake AND throttle simultaneously (left-foot braking) | Brake priority maintained; throttle suppressed for AEB duration only |
| Driver demands reverse gear during AEB forward braking | Transmission controller must queue reverse until vehicle is stationary |
| AEB activates, driver turns steering wheel sharply | AEB releases if avoidance maneuver is detected (steering > threshold deg/s) |
| By-wire system latency 50 ms vs. AEB command 20 ms | Timing analysis required; AEB must have highest OS task priority |

### Acceptance Criteria
- Throttle override suppressed within 10 ms of AEB brake command
- Vehicle decelerates at commanded 9 m/s² regardless of throttle input during AEB

---

## Q15: AEB on Curved Road — Object in Predicted Path

### Scenario
The ego vehicle is navigating a sharp curve (radius = 80 m) at 60 km/h (at the limit of comfortable cornering). A stationary vehicle is parked at the exit of the curve, 25 m ahead in the predicted forward path. The radar is pointing mostly straight, not along the curve.

### Expected Behavior
AEB must account for the curvature of the road and predict the future path of the ego vehicle correctly to determine if the parked vehicle is a genuine threat.

### Detailed Explanation
- Path prediction uses: yaw rate sensor, steering angle, camera lane markings, and HD map curvature.
- Radar tracks provide range and bearing relative to the ego vehicle's current heading.
- The AEB threat assessment must project the ego vehicle's future path along the curve, not straight ahead.
- At 60 km/h with 80 m radius, the vehicle turns ~43° per second.
- Without curvature compensation, the straight-line radar reading places the parked car 25 m ahead but outside the predicted path — AEB doesn't fire. This is a safety-critical bug.
- Curvature compensation algorithm fuses yaw rate + steering angle for path prediction up to 2–3 s ahead.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Tight hairpin (radius < 30 m) | Camera lane markings take over path prediction; radar range limited |
| Road camber changes path prediction | Inertial sensor fusion must account for road banking angle |
| Curve with adverse camber (outward banking) | Vehicle dynamics model used for more accurate path prediction |
| Object exits curve shadow (appears suddenly) | Short preview time; AEB must have sub-1 s reaction |

### Acceptance Criteria
- AEB activates for in-path objects on curves with radius ≥ 50 m at speeds 20–80 km/h
- No false activation for roadside objects on the outside of curves

---

## Q16: AEB Activation Speed Range and Minimum Speed Limit

### Scenario
The AEB system is calibrated to activate at speeds > 10 km/h to avoid very-low-speed false activations in car parks. A customer reports that AEB did not activate at 8 km/h when reversing into a bollard. What should the specification say?

### Expected Behavior
AEB should have distinct forward and reverse speed ranges:
- Forward AEB: 10–200 km/h (or as per NCAP requirements)
- Reverse AEB (AEB-R): 2–15 km/h (car park maneuvering)

### Detailed Explanation
- UN ECE R152 mandates AEB activation up to 60 km/h (minimum requirement).
- Euro NCAP tests AEB at 10–80 km/h.
- Very low speed (<10 km/h) AEB for car parks is a separate function using USS (ultrasonic sensors).
- Reverse AEB uses rear USS array with closing velocity estimation.
- The customer scenario involves Reverse AEB, which should have a lower minimum speed threshold of 2–3 km/h.
- Reverse AEB can tolerate slightly higher false positive rate since it is a low-energy intervention.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle rolling forward at 2 km/h in parking lot | Forward Low-Speed AEB from USS should activate |
| High speed reverse maneuver (drivethrough reversal) | Reverse AEB at > 15 km/h; system may suppress to prevent harsh braking when driver intends fast reverse |
| AEB at 200+ km/h (derestricted autobahn) | AEB must remain functional; stopping distance calculations adjusted |

### Acceptance Criteria
- Reverse AEB activates at 2–15 km/h for objects ≥ 10 cm height behind vehicle
- Forward AEB activates at 10–150+ km/h per UN ECE R152

---

## Q17: AEB with Animal Detection (Large Animal Crossing)

### Scenario
A deer (large animal, ~80 kg) crosses the road in front of the ego vehicle at 70 km/h in a rural area at night. The front camera has limited range due to headlight illumination range (50 m in dipped mode). Should AEB activate?

### Expected Behavior
AEB should detect and classify large animals as obstacles in the ego path and issue a warning. Full AEB activation should occur if collision is predicted.

### Detailed Explanation
- Animal detection is an emerging ADAS requirement; Euro NCAP 2026 roadmap includes VRU-large animal scenarios.
- Camera-based animal classification uses CNN trained on deer, moose, cattle, horse silhouettes.
- Challenges: animal posture varies widely (head down, running, standing); night-time thermal imaging provides better contrast.
- Radar provides range but animal radar cross-section is low and inconsistent.
- At 70 km/h with 50 m detection range, TTC = 2.6 s — sufficient for FCW but marginal for AEB.
- ADB (Adaptive Driving Beam) headlights increase illumination range, giving more time for detection.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Deer partially on road (head in beam, body on shoulder) | Predicted path intersection partial; warn driver, prepare AEB |
| Moose (tall animal, body invisible to radar at distance) | Radar may detect legs only; camera provides body classification |
| Flock of birds flying low over road | Small, fast-moving; not classified as collision threat; suppress to avoid false AEB |
| Livestock on unfenced road (developing country scenario) | Multiple animals; track densest obstacle cluster |

### Acceptance Criteria
- Large animal (> 30 kg, > 0.5 m height) detected at ≥ 40 m in night-time conditions
- FCW issued; AEB activates if TTC < 1.5 s and driver has not reacted

---

## Q18: AEB Multi-Target Prioritization

### Scenario
At an intersection, three objects are simultaneously detected: a pedestrian crossing from the left (TTC = 2.1 s), a cyclist crossing from the right (TTC = 1.8 s), and a stopped car directly ahead (TTC = 3.5 s). Which target does AEB prioritize?

### Expected Behavior
AEB should prioritize by:
1. **Minimum TTC** (cyclist at 1.8 s → highest urgency)
2. **Collision probability** (which target is in the most likely ego path)
3. **Object vulnerability** (pedestrian > cyclist > vehicle in case of equal TTC)

### Detailed Explanation
- AEB threat model runs for each detected object simultaneously.
- Priority arbitration selects the most critical threat for braking command generation.
- For the cyclist at 1.8 s: AEB activation threshold is typically 1.5 s → AEB prepares but does not yet fire.
- The braking command must be optimized: braking hard for the cyclist may bring the ego vehicle into conflict with the stopped car — threat graph analysis needed.
- In complex intersection scenarios, AEB may apply partial braking to create time for re-assessment.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Two objects in collision path simultaneously | Apply braking for nearest-TTC threat; second threat may auto-resolve |
| Stationary object appears behind moving pedestrian (occlusion) | After pedestrian clears, re-assess stationary object |
| One object is a false detection (ghost) | Ghost suppression filters; act on verified targets only |

### Acceptance Criteria
- AEB selects and responds to minimum-TTC confirmed object within one sensor cycle (40–66 ms)
- No simultaneous conflicting brake commands generated

---

## Q19: AEB System Self-Test and Readiness Monitoring

### Scenario
After vehicle startup, the AEB system performs a self-test. The radar reports a calibration drift (azimuth angle 1.5° off). Should AEB remain available?

### Expected Behavior
A 1.5° azimuth drift reduces AEB accuracy but may not require full deactivation, depending on severity analysis. The system should:
- Set a DTC for radar miscalibration
- Reduce AEB effective range / confidence
- Display a degradation warning to driver
- Fully deactivate above 3° drift threshold

### Detailed Explanation
- Radar miscalibration can occur after body repair, front impact, or thermal expansion.
- 1.5° azimuth error at 60 m range introduces ~1.6 m lateral error in object position — may cause missed detections at lane edges.
- Calibration monitoring uses: static guardrail perpendicularity check, moving vehicle trajectory consistency, and online self-calibration algorithms.
- Online calibration update can correct small drifts (< 1°) automatically.
- Above 1° but below 3°: degrade function with notification.
- Above 3°: deactivate AEB and request workshop calibration.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Calibration drift appears suddenly during drive (impact to front) | Immediate recalibration attempt; if fails, deactivate |
| Both camera and radar suggest different object positions | Fusion inconsistency detected; alert driver |
| Self-test fails at cold start (-30°C) but passes after warm-up | Temperature-dependent component behavior; allow warm-up period before re-test |

### Acceptance Criteria
- DTC set for azimuth error > 1°
- AEB deactivated for azimuth error > 3°
- Self-test complete within 5 s of ignition-on

---

## Q20: AEB in Evasive Steering Assist (ESA) Integration

### Scenario
AEB activates at 50 km/h for a pedestrian ahead. Simultaneously, the Evasive Steering Assist (ESA) calculates that steering around the pedestrian is feasible (adjacent lane is clear). Should AEB brake or ESA steer, or both?

### Expected Behavior
AEB and ESA can act simultaneously as a combined collision mitigation strategy:
- AEB reduces approach speed
- ESA steers around the obstacle if lane space is available

### Detailed Explanation
- ESA is available in Euro NCAP test protocols from 2023 onwards.
- The combined AEB + ESA response is more effective than either alone.
- Threat assessment must evaluate: is evasion feasible? (adjacent lane clear, road width sufficient, speed < 90 km/h)
- If evasion is feasible: ESA activates; AEB applies moderate braking to reduce speed, not full stop.
- If evasion is not feasible (oncoming traffic in adjacent lane): AEB alone activates at full deceleration.
- The actuator arbitration: steering and braking can physically conflict (strong braking while steering causes understeer).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Adjacent lane occupied by another vehicle | ESA suppressed; AEB full activation |
| Narrow road: no room to evade | AEB only |
| Driver takes over steering during ESA | ESA releases steering authority; AEB continues braking |
| Pedestrian is in adjacent lane too (family crossing together) | No evasion path; AEB maximum braking |
| ESA steers toward oncoming traffic (incorrect adjacent lane assessment) | ESA must have forward-facing sensor confirmation of adjacent lane clearance |

### Acceptance Criteria
- ESA activates only when adjacent lane confirmed clear with > 95% confidence
- Combined AEB+ESA reduces collision speed by ≥ 30% more than AEB alone in NCAP test scenarios
