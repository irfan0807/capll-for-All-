# Night Vision & Driver Monitoring System (DMS) — Scenario-Based Questions (Q81–Q90)

---

## Q81: Night Vision System — Detecting Unlit Pedestrian on Country Road

### Scenario
The ego vehicle is traveling at 90 km/h on an unlit country road at 2 AM. A pedestrian in dark clothing is walking along the road edge at 80 m distance. Standard headlight range (dipped beam) covers approximately 40 m. The night vision system (NIR — Near Infrared) must detect the pedestrian beyond the headlight range.

### Expected Behavior
The NIR night vision system should detect the pedestrian at 60–80 m and provide an alert to the driver — either via HUD projection showing the pedestrian outline or an auditory alert.

### Detailed Explanation
- NIR night vision systems use an infrared illuminator ( ~850 nm) and an NIR-sensitive camera.
- NIR illuminators can project detection range to 100–150 m regardless of headlight range.
- Person detection in NIR imagery uses a dedicated DNN trained on NIR images (different from visible-light DNN).
- NIR wavelength: human body reflects ~30% of NIR vs. ~10% for dark clothing in visible light → better contrast.
- Alert system: detected pedestrian highlighted on HUD or instrument cluster; voice advisory.
- AEB-P integration: if pedestrian is in collision path, AEB-P can also use night vision as a sensor input.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Pedestrian with retroreflective vest (high NIR reflection) | Excellent detection; easy classification |
| Animal (fox/deer): similar NIR profile to human | Animals have different gait and body aspect ratio; classification must distinguish |
| Road sign retroreflection flooding NIR camera | Retroreflective signs are very bright in NIR; may cause blooming; exposure control required |
| NIR illuminator blocked by dirt/ice | Illuminator blockage detected; alert driver of reduced night vision range |
| Rain droplets on NIR camera lens | Scatter from rain; classification degrades; known SOTIF limitation |

### Validation Approach
- Night-time closed-track tests with human stand-in targets
- NIR camera sensitivity test: 0.01 lux measurement in calibration lab
- Comparison with standard camera detection range (baseline)

### Acceptance Criteria
- NIR detection of unlit pedestrian at ≥ 60 m in complete darkness
- HUD alert displayed within 1 s of pedestrian classification
- False positive rate (wrong animal/object classified as pedestrian) < 1 per 50 km on country roads at night

---

## Q82: Adaptive Driving Beam (ADB) — Anti-Dazzle for Oncoming Traffic

### Scenario
The ego vehicle's ADB (Matrix LED headlights) should illuminate the full road at full-beam while creating a "shadow zone" around an oncoming vehicle to prevent blinding the other driver. During testing, the shadow zone is 500 ms late, causing dazzle to the oncoming driver.

### Expected Behavior
ADB shadow zone must be applied within 100 ms of detecting an oncoming vehicle. 500 ms latency is unacceptable.

### Detailed Explanation
- ADB uses individual LED segments (or pixel headlights) controllable independently.
- A camera detects oncoming headlights and triggers the shadow zone for the relevant angular sectors.
- System latency breakdown: camera frame (33 ms) + DNN detection (20 ms) + LED ECU command (10 ms) + LED slew (10 ms) = ~73 ms typical.
- 500 ms suggests: detection algorithm delay, or incorrect ECU frame processing order.
- At 90 km/h closing speed (two 90 km/h vehicles), 500 ms = ~25 m of unshielded illumination.
- Regulation requirement (UN ECE R48 / R123): Adaptive front lighting systems must react within a defined response time.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Oncoming vehicle on a curve: headlights appear from the side | ADB algorithm must predict oncoming vehicle's angular position change |
| Poorly maintained vehicle with one headlight out | ADB detects one headlight; still creates shadow zone for the single source |
| Multiple oncoming vehicles simultaneously | ADB creates multiple shadow zones; LED matrix must support parallel masking |
| Bicycle with a single front LED | Small, single-point light source; ADB should still reduce brightness in that sector |
| ADB malfunction (LED segment failure) | System detects failed LED via monitoring; falls back to static dipped beam |

### Acceptance Criteria
- ADB shadow zone applied within 100 ms of oncoming vehicle detection
- Shadow zone covers oncoming vehicle within ±2° angular accuracy
- Automatic fallback to dipped beam on any ADB component failure

---

## Q83: Driver Monitoring System (DMS) — Drowsiness Detection

### Scenario
The driver has been driving for 3 hours without a break on a motorway. DMS (using an IR camera inside the cabin monitoring driver's face) detects slowing blink rate, drooping eyelids, and head nodding. What should the system do?

### Expected Behavior
DMS should progress through a tiered warning system:
1. **Level 1 (early)**: soft advisory message "Consider taking a break" + coffee cup icon on HMI.
2. **Level 2 (moderate)**: auditory chime + visual alert + vibrating seat.
3. **Level 3 (severe)**: escalated alarm, ACC speed reduction, preparation for controlled stop if no response.

### Detailed Explanation
- Drowsiness indicators tracked by DMS:
  - PERCLOS (Percentage Eye Closure): eye closure > 80% for > 500 ms per 30 s measured.
  - Blink rate change: normal ~15–20 blinks/min; drowsy < 8–10.
  - Head pose: forward head drop (pitch angle change).
  - Steering behavior: reduced steering micro-corrections (lane drift correlation).
- ISO 11664 and EU GSR 2022 mandate drowsiness detection.
- DMS must be robust to glasses, sunglasses, face masks.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver wears sunglasses (eye state invisible) | DMS falls back to steering behavior analysis; reduced confidence; earlier warning threshold |
| Driver is watching road attentively but has naturally droopy eyelids | Baseline calibration per driver profile; DMS adapts to individual |
| Overnight driver (physiologically different from post-lunch) | Circadian rhythm model; stricter thresholds at midnight–5 AM |
| Driver reading map on passenger seat (distraction, not drowsy) | Gaze direction indicates distraction, not drowsiness; different warning strategy |
| Driver in bright direct sunlight (DMS IR performance degraded) | HMI notification: "DMS monitoring limited"; steering behavior fallback |

### Acceptance Criteria
- Drowsiness Level 1 warning issued when PERCLOS > 15% over 60 s window
- Drowsiness Level 2 when PERCLOS > 25% or head nod detected
- DMS alert canceled when driver acknowledges (button press or gaze return)

---

## Q84: DMS — Attention and Distraction Detection

### Scenario
The driver takes their eyes off the road to look at a navigation screen mounted low on the dashboard for 4 continuous seconds at 100 km/h. DMS detects gaze deviation from road-relevant range (15° downward). The vehicle travels 111 m with driver not looking at road.

### Expected Behavior
DMS should issue a distraction warning at > 2 s of sustained off-road gaze. A visual and auditory alert returns driver attention to the road.

### Detailed Explanation
- Gaze classification: DMS tracks pupil and iris position to estimate gaze direction.
- Road-relevant gaze zone: ±30° horizontal, ±15° vertical from straight-ahead.
- Distraction threshold: > 2 s sustained off-road gaze at > 60 km/h (per NHTSA and Euro NCAP 2025).
- At 100 km/h, 2 s = 55 m without visual input — significant safety risk.
- Escalation: if driver does not return gaze in 1 additional second, a stronger alert sounds.
- Integration: DMS alert can trigger ACC to reduce speed and increase following gap as a precaution.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver looks at rearview mirror (valid glance) | Short glances within ±30° horizontal are not triggers; only sustained downward gaze |
| Driver checks side mirror for 3 s (acceptable action) | Side mirror glance is road-relevant; DMS should classify as valid gaze |
| Driver handles emergency (child crying in back seat) | DMS cannot differentiate; alerts at 2 s regardless; driver must manage |
| Voice interaction (driver looking up, talking to vehicle) | Normal HMI use; DMS should not penalize brief expected interactions |

### Acceptance Criteria
- Gaze direction accuracy: ±5° in normal driving conditions
- Distraction alert at 2 s off-road gaze with < 200 ms alert latency
- Alert correctly suppressed for glances ≤ 1.5 s

---

## Q85: DMS — Seatbelt and Occupant Detection Integration

### Scenario
DMS detects that the driver is physically in the seat and engaged. However, the seatbelt sensor on the CAN reports "unbuckled." DMS must verify if the detected person is indeed the driver and is wearing a seatbelt.

### Expected Behavior
DMS cameras + seatbelt sensor fusion: the system should display a reminder alert. DMS should correlate "occupant detected in driver seat" with "seatbelt unbuckled" and issue a reminder. This is NOT an ADAS function per se but is part of the occupant safety system.

### Detailed Explanation
- Modern DMS can visually detect seatbelt presence (camera can see the diagonal strap across shoulder).
- Cross-validation: if CAN seatbelt sensor = unbuckled AND DMS visually confirms no strap = definitive.
- Conflict: seatbelt sensor = buckled but DMS does not see strap (dark clothing, strap below frame) → trust buckle sensor as primary.
- This function helps detect seatbelt misuse (clip put in buckle without wearing the belt).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver wears belt under arm (incorrectly) | Sensor reports buckled; DMS may detect incorrect routing; advisory |
| Seat occupied by object (bag) triggering seat sensor | Pressure sensor weight < 20 kg → classify as non-occupant; DMS confirms no face detected |
| Child seat installed: child cannot be tracked by DMS | CPRD (Child Presence Detection) is a separate function |

### Acceptance Criteria
- Seatbelt non-use detected with ≥ 99% accuracy (camera + CAN fusion)
- No false alert for buckled seatbelt in ≥ 5,000 test cycles

---

## Q86: DMS in Fully Automated L3 Driving — Hands-Free Monitoring

### Scenario
The vehicle is operating in L3 autonomous mode (Conditional Automation) on a designated highway. The driver is allowed to watch a movie on the center screen. DMS must monitor that the driver is ready to take back control within 10 s when notified. How should DMS operate at L3?

### Expected Behavior
At L3, DMS role shifts from distraction warning to "takeover readiness monitoring":
- Driver can engage in secondary activities (watching video, reading).
- DMS monitors: is the driver in the seat? Is the driver conscious? Is the driver able to respond?
- When a Takeover Request (TOR) is issued, DMS verifies driver readiness within the TOR grace period (10 s).

### Detailed Explanation
- L3 system issues TOR with a countdown: 10 s to takeover.
- DMS must assess: driver alert/awake? Driver hands reachable to steering?
- If driver asleep or incapacitated: L3 executes Minimal Risk Condition (MRC) — hazard lights, gradual stop in lane.
- ISO 21448 SOTIF: the transition to L3 and the takeover request are major safety scenarios.
- DMS at L3 operates continuously (not just when driver should be looking at road).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver asleep during L3 (deeply sleeping, 3+ hours) | No response to TOR after 10 s: MRC initiated |
| Driver reading newspaper blocking DMS camera view | Newspaper blocks gaze measurement; assume not monitoring road |
| Passenger assumed control (wrong occupant driving) | DMS must track driver seat occupant specifically |
| TOR in tunnel: sudden manual driving challenge | High-speed TOR in low-visibility conditions; reduce speed as part of TOR handover |

### Acceptance Criteria
- DMS takeover readiness assessment within 3 s of TOR issuance
- MRC initiated if no driver response within 10 s + escalation period
- DMS continuously monitors driver state throughout L3 operation

---

## Q87: DMS Robustness — Glasses, Beard, Face Mask

### Scenario
A driver wearing large-frame tinted glasses, a beard, and a COVID-style face mask enters the vehicle. The DMS fails to track the driver's face and defaults to "driver not detected." The vehicle activates enhanced monitoring alerts continuously.

### Expected Behavior
DMS should robustly handle common face occlusions: glasses, beard, visors, and face masks. DMS must gracefully degrade — reducing confidence but maintaining some monitoring function.

### Detailed Explanation
- Face detection DNN: must be trained with diverse driver population data including glasses, facial hair, face coverings.
- Fallback behavior: when face tracking fails, DMS can use:
  1. Eye tracking from partial face (glasses with transparent lenses — eyes still visible).
  2. Head pose estimation from facial structure visible around the mask.
  3. Steering behavior monitoring as a supplementary input.
- DMS must NOT permanently disable itself because of face occlusion.
- Regulatory context: some countries may require mask wearing; DMS must function.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Fully opaque balaclava (face fully covered) | Pure head pose + steering behavior; camera alone insufficient; regulatory note |
| IR reflective glasses (some photochromic lenses) | Calibrate IR illuminator wavelength to minimize reflection interference |
| Motorcycle helmet inside vehicle (briefly) | Robust face detection ignores helmet shape; no classification until face visible |

### Acceptance Criteria
- Eye gaze tracking maintained with glasses (non-tinted) in 95% of cases
- Head pose estimation maintained with face mask in 90% of cases
- Steering behavior fallback active within 1 s of face tracking loss

---

## Q88: DMS Baseline Driver Profile Calibration

### Scenario
A new driver uses the vehicle for the first time. DMS does not have a baseline profile for this driver's normal PERCLOS and blink rate. How should DMS calibrate itself to avoid false drowsiness alerts for drivers with naturally slow blink rates?

### Expected Behavior
DMS should support per-driver profile calibration:
- Phase 1 (first 5 min of driving): observation mode — record baseline PERCLOS, blink rate, gaze behavior.
- Phase 2: learned baseline used for comparative drowsiness detection.
- Multiple driver profiles stored (up to 5 drivers typical in family vehicles).

### Detailed Explanation
- Baseline PERCLOS varies: alert driver 5–10%, drowsy driver > 20%.
- A driver with a naturally slower blink rate or slightly droopy eyelids would be incorrectly flagged without calibration.
- Driver profile recognition: can be linked to seat position, key fob ID, or smartphone association.
- Privacy: driver biometric data (face gaze profile) must comply with GDPR; user consent required for profile storage.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Guest driver (unknown profile) | Use population-average baseline; slightly more conservative thresholds |
| Driver's baseline changes (illness, medication affecting blink rate) | DMS should re-learn over time or allow manual reset |
| Driver uses vehicle only at night (different baseline) | Profile stores time-of-day context; night baseline may differ |

### Acceptance Criteria
- Baseline calibration complete within 3–5 min of new driver session
- False positive drowsiness alerts < 0.1 per 60 min during calibration-complete alert driving session

---

## Q89: DMS Failure Mode and Safe State

### Scenario
The DMS IR camera malfunctions (image output frozen at the last valid frame). The system does not detect the failure and continues to report "driver alert" based on the frozen frame. This is a safety-critical failure.

### Expected Behavior
DMS must include watchdog mechanisms to detect frozen or invalid camera output:
- Frame counter monotonicity check: if frame counter stops incrementing, camera is frozen.
- Image entropy check: statistically flat image entropy indicates frozen frame.
- Actuator output (LED illuminator) feedback cross-check.

### Detailed Explanation
- A frozen frame is more dangerous than a detected failure: system reports false "all OK."
- Safe state on camera failure: deactivate DMS function, display "DMS unavailable," store DTC.
- ISO 26262: latent fault in a safety function — fault detection must occur before the system is needed.
- Watchdog timer on DMS ECU: if camera data not refreshed within 200 ms, fault declared.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Camera intermittently freezing (thermal issue) | Intermittent fault: DTC stored; warning presented; driver notified |
| Camera going black (lens fogged vs. truly failed) | Distinguish: detect lens fogging pattern vs. hard failure |
| DMS ECU reboot mid-drive | Temporary DMS unavailability expected; restore in < 5 s |

### Acceptance Criteria
- Frozen frame detection within 200 ms (frame counter check)
- DTC set immediately on confirmed DMS camera failure
- "DMS unavailable" HMI displayed within 500 ms of fault detection

---

## Q90: Night Vision + DMS Combined Operation — Power and Thermal Management

### Scenario
The NIR headlights and DMS IR cabin camera both operate simultaneously. In hot weather, the ADAS domain ECU thermal sensor reports 85°C (threshold 90°C). How should the system manage thermal load to prevent shutdown?

### Expected Behavior
The ADAS ECU thermal management should:
1. Throttle non-critical processing first (HMI rendering quality, map storage operations).
2. Reduce NIR illuminator duty cycle slightly (minor impact on night vision range).
3. Maintain DMS as highest-priority function since it is safety-critical at L2/L3.
4. Alert driver if thermal situation cannot be resolved.

### Detailed Explanation
- ADAS ECUs (e.g., Mobileye EyeQ, Nvidia Orin) have thermal throttling behavior.
- Priority-based thermal management: safety-critical functions (DMS, AEB inputs) have highest priority.
- Comfort and infotainment functions are throttled first.
- HDC (Hardware Health Controller) monitors junction temperature and triggers graduated cooling/throttling.
- Forced ventilation enhancement: some vehicles increase blower speed for ECU compartment cooling.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| ECU reaches 90°C hard shutdown threshold | ALL ADAS deactivated; prominent warning to driver to take over |
| Night drive in desert at 45°C ambient | Pre-trip ECU temperature assessment; alert if route increases thermal risk |
| ECU thermal paste degraded (long-life vehicle) | Thermal resistance increase; earlier throttling at lower temperature |

### Acceptance Criteria
- ADAS ECU operates at full performance at junction temperature ≤ 85°C
- Graduated throttling begins at 85°C; safety functions maintained until 95°C
- System safe shutdown at ≥ 100°C junction temperature with driver alert
