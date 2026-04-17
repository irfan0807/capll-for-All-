# Parking Assistance & Surround View — Scenario-Based Questions (Q51–Q60)

---

## Q51: Automated Parallel Parking — Narrow Space Detection

### Scenario
The ego vehicle is searching for a parallel parking space. The available space is 5.8 m long, and the vehicle is 4.5 m long. The system requires a minimum space of 5.5 m (requiring 1.3 m extra). Should the system offer to park here?

### Expected Behavior
Yes — the 5.8 m space exceeds the 5.5 m minimum. The APA (Automated Parking Assist) should detect and offer the space. The system should calculate a feasible parking trajectory and execute it.

### Detailed Explanation
- APA uses USS (ultrasonic sensors) arrays along the vehicle's sides to scan for parking spaces as the vehicle drives past.
- Space length estimation accuracy: ±15 cm typical for USS-based scanning.
- Minimum space formula: vehicle_length + 1.0–1.5 m buffer (depends on OEM algorithm).
- Trajectory planning: typically a 2–3 Bezier curve arc path for parallel parking.
- The car must also fit laterally —the space width must allow the vehicle to fully enter between curb and adjacent vehicle.
- APA controls steering automatically while the driver manages throttle/brake (L1) OR full A-to-B automated (L2 parking).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Space measured while moving at 20 km/h (too fast for accurate USS scan) | APA instructs driver to scan at < 15 km/h; reject space measurement if scan speed is too high |
| Pedestrian enters the space mid-maneuver | APA detects obstacle via USS, pauses maneuver, waits for clearance |
| Space at angle (non-parallel curb) | Trajectory adapted for angled curb entry; wheel-touch warning if curb detected |
| Puddle in parking space reflecting USS (false detection) | USS frequency and gate timing calibrated to minimize ground reflection false positives |
| No rear USS on vehicle: limited reversing coverage | APA uses side USS + rear camera for reverse phase |
| Adjacent vehicle has door open (consuming extra space) | Camera + USS detect door; space assessed dynamically |

### Acceptance Criteria
- APA detects valid spaces with ≥ 95% accuracy at 10 km/h scan speed
- Parking maneuver completes with final position within ±15 cm of ideal position
- Zero contact with curb, adjacent vehicles, or obstacles during maneuver

---

## Q52: Perpendicular Parking — Object in Path After Maneuver Start

### Scenario
The ego vehicle begins a perpendicular parking maneuver (entering a space between two parked cars). A shopping cart rolls into the parking space from the rear during the maneuver. The vehicle is reversing at 4 km/h.

### Expected Behavior
The APA system should detect the shopping cart via rear USS and halt the maneuver immediately. An auditory warning should sound and the driver should be prompted to take control or confirm clearance.

### Detailed Explanation
- Rear USS continuously monitors during the entire parking maneuver.
- USS detection range: typically 0.25–3 m for parking sensors.
- Shopping cart: low RCS object (~0.3–0.5 m width, ~1 m height) — USS can detect if within range.
- Action on detection: immediate halt (if reverse AEB equipped, brakes apply automatically).
- APA operating principle: if obstacle detected mid-maneuver, the system must not continue blindly.
- Alert escalation: CSS distance gauge turns red → auditory alert → stop.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cart enters right at USS dead zone (close range, < 25 cm) | Last USS reading before dead zone used; vehicle already stopped |
| Parked car behind reverses into space (double-reverse conflict) | APA halts; surround view camera shows the approaching vehicle |
| Child runs into the space | Camera (surround view) detects child; USS may also detect; immediate halt |
| APA maneuver in heavy rain (USS range reduced) | System warns of degraded sensing; manual parking recommended |
| Final alignment phase: rear gets very close to rear wall | USS beeps continuously at < 30 cm; APA auto-stops at 15 cm |

### Acceptance Criteria
- APA halts within 300 ms of rear obstacle entry into detection zone
- Minimum stopping distance from obstacle: 15 cm (tunable parameter)
- Resumption only after driver confirms space clear

---

## Q53: Surround View 360° Camera — Stitching Artifacts at Curb Corner

### Scenario
During a surround view display validation, the validation engineer notices a phantom "gap" in the stitched 360° image at the front-left corner. Objects near this zone appear distorted — a curb partially vanishes. The driver may misjudge clearance.

### Expected Behavior
The 360° surround view image stitching must produce seamless visual continuity with < 5 cm positional error for objects in the stitching zone.

### Detailed Explanation
- Surround view uses 4 fisheye cameras (front, rear, left, right) stitched into a bird's eye view.
- Stitching zones are the overlapping regions between adjacent camera images.
- Calibration requirements: cameras must have consistent extrinsic calibration (position + orientation).
- A 2 mm camera mounting misalignment can produce visible stitching artifacts.
- Stitching algorithm applies homographic transformation and alpha-blending in the overlap zones.
- Calibration patterns (checkerboard targets on the ground) are used at end-of-line to calibrate stitching.
- Online re-calibration can correct minor drift during vehicle life.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Camera lens dirty (one of the four) | Affect one quadrant; system warns "camera dirty" |
| One camera failed: only 3 cameras available | Missing quadrant displayed with hatching or "camera unavailable" overlay |
| After body repair, camera remounted slightly off | Requires re-calibration at workshop; online calibration handles small offset |
| Night-time: one camera with different IR response | Color balance differences at night; acceptable within ±10% brightness |
| Moving object in stitching zone | Object may appear duplicated or split; known limitation; warning label in HMI |

### Acceptance Criteria
- Ground object positional accuracy in stitching zones: ≤ 5 cm at 1 m distance
- Stitching seam not visible under normal illumination conditions

---

## Q54: Remote/Summon Parking — Safety During Unmanned Operation

### Scenario
A premium vehicle offers a Remote Park Assist function where the driver stands outside and controls the vehicle remotely via a smartphone/key fob while it parks itself. During testing the vehicle begins moving while the app shows "paused." This is a safety-critical failure.

### Expected Behavior
When the remote parking session is paused (driver not actively commanding), the vehicle must come to a complete stop and remain stationary. Unintended motion during pause is a functional safety violation.

### Detailed Explanation
- Remote Park Assist operates under ISO 22737 (Low-Speed Automated Driving System) and ISO 26262.
- The remote device (smartphone) sends keep-alive heartbeats; if heartbeat stops, vehicle stops within 1 s.
- ASIL-D parking brake engagement required once the vehicle is stationary in a paused state.
- The failure observed (vehicle moving during pause): possible causes:
  1. Race condition in pause state machine — motion command not fully canceled.
  2. Communication packet loss causing stale motion command to continue executing.
  3. Park by Wire actuator not receiving brake command.
- Root cause must be found via event log + CAN trace.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Bluetooth connection drops mid-maneuver | Vehicle halts immediately on comm loss; does not resume without explicit command |
| Pedestrian steps in front of vehicle during remote maneuver | All-round USS + camera collision avoidance remains active |
| Remote app spoofed by attacker (cybersecurity) | ISO/SAE 21434: authentication (signed commands), replay attack prevention |
| Driver drops key fob: heartbeat lost | Vehicle stops within 1 s; park brake applied |

### Acceptance Criteria
- Vehicle stops within 500 ms of pause command or comm loss
- Vehicle remains stationary (park brake engaged) during pause state
- Zero unintended motion events in 1,000 remote park test cycles

---

## Q55: APA Garage Exit Assist (Forward and Reverse)

### Scenario
The garage has a pillar on the right at 0.3 m clearance and a wall on the left at 0.4 m clearance when reversing out. The APA exit assist should reverse the vehicle out carefully. Visibility from the driver's seat is very limited.

### Expected Behavior
APA Exit Assist uses the reverse trajectory from the last stored parking maneuver (or computed from current position) to safely exit with continuous USS monitoring and guidance.

### Detailed Explanation
- Garage exit is tighter than open-road parking: USS sensors must work at close range (0.15–0.5 m).
- Side USS sensors provide left and right clearance distance in real-time.
- APA exit: reverses along a stored exit path, adjusting if obstacles detected.
- If stored path is not available: compute geometry from current position and surround view.
- Rear cross traffic alert (RCTA) activates as vehicle emerges onto the driveway/road.
- Exit Assist at very slow speed (< 3 km/h) for maximum control.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Garage wall moved / new obstacle since last park | Re-compute path from current sensor data |
| Pet or child in garage at exit path | Camera + USS detects; halts immediately |
| Icy garage floor (low tire grip) | Wheel speed sensor detects slip; warn driver |
| Narrow door: door mirror may clip doorframe | USS near door mirror required; warning if < 10 cm clearance |

### Acceptance Criteria
- Garage exit without contact with walls/pillars in 100% of structured test passes (< 0.3 m clearance scenarios)
- RCTA activates when vehicle nose/rear emerges from garage into traffic zone

---

## Q56: Parking Sensor False Positives From Ground Reflections

### Scenario
During rear parking, the USS beeps continuously even when the car park is empty. Investigation reveals the system is detecting reflections from the flat concrete floor of the car park during wet conditions.

### Expected Behavior
USS must filter out ground reflections. Ground is a known planar surface at the vehicle's underside — signals from the expected "ground return" angle should be suppressed.

### Detailed Explanation
- USS pulses transmit at ~40 kHz. On flat wet surfaces, the pulse reflects upward and is received by the transducer.
- Ground reflection occurs at angles corresponding to direct downward reflection (nadir angle).
- Firmware filtering: time-gating (expected ground return time at known mounting height) and angle-of-incidence filtering suppresses ground reflection.
- Wet conditions: water film increases reflectivity of ground return.
- Calibration: the USS mounting height and angle stored in configuration must be accurate for correct gating.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Parking on inclined surface (ramp) | Ground angle changes; adaptive gating required |
| Gravel car park (non-uniform surface) | Diffuse ground return; lower amplitude; reduces false trigger risk |
| USS mounted at incorrect height after bumper repair | Gating misconfigured; re-calibration needed |
| Speed bump detected as obstacle just behind vehicle | Below height threshold; filtered out |

### Acceptance Criteria
- Zero false parking sensor alerts in empty wet car park (flat concrete) at walking speed
- Ground reflection suppression validated in 50 pass/fail tests in wet flat car park

---

## Q57: Automatic Parking Brake After Park Assist Completes

### Scenario
APA completes a perpendicular bay park. The transmission is automatically shifted to Park. However, the electronic parking brake (EPB) is not applied. Two minutes later, the vehicle rolls forward and contacts the wall ahead. This is a functional safety failure.

### Expected Behavior
APA must ensure the vehicle is fully secured after completing the maneuver:
1. Shift to Park (automatic transmission) OR apply EPB (manual/electric gear)
2. Apply EPB as a secondary hold
3. Display "Parking complete — vehicle secured"
4. Exit APA active state only after vehicle is confirmed stationary with EPB applied

### Detailed Explanation
- Transmission Park (P) engages a mechanical park pawl — sufficient on flat surfaces.
- EPB provides additional security, especially on inclined surfaces.
- APA completion sequence: trajectory complete → vehicle stopped → transmission to P → EPB apply → system status = inactive.
- Failure mode: EPB command not sent OR EPB actuator did not engage (sensor not confirming closed).
- ISO 26262 requires confirmation of safety-relevant actuators (EPB status feedback).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| EPB actuator fault: cannot apply | APA must notify driver; not complete the parking session without EPB confirmation |
| Parked on steep hill: Park pawl not sufficient alone | EPB mandatory; transmit urgent warning if EPB unavailable |
| Driver immediately opens door after APA completes | Prompt: "Vehicle secured" before door lock release |

### Acceptance Criteria
- EPB applied in 100% of APA completion cycles
- APA displays error if EPB status not confirmed within 2 s after command

---

## Q58: Parking Detection — Motorcycle Parked in Bay Slot

### Scenario
The APA scanning function sees a bay slot between two parked cars. One of the "cars" is actually a motorcycle occupying only 30% of the bay width. APA misidentifies this as a full empty space.

### Expected Behavior
APA should accurately measure the available width in a bay and detect that the motorcycle reduces the usable width of the bay. If usable width < vehicle width + minimum margin (e.g., 2.5 m for a 2.0 m wide vehicle), the bay should not be offered.

### Detailed Explanation
- USS scanning measures space length but may have limited width discrimination.
- Camera-based space classification (bird's eye view or forward-facing) can detect a motorcycle's narrow profile.
- A camera-trained object detection can classify "motorcycle" and estimate its width.
- Width of remaining usable space = bay width – motorcycle width.
- Surround view camera at 360° provides a top-down view that is very effective for detecting partial occupancy.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Motorcycle parked at back of bay (not detectable by USS during scan) | No USS detection; camera must scan the bay as the vehicle aligns |
| Bicycle chained to parking bay bollard | Very narrow obstruction; must be detected and flagged |
| Partial bay partially blocked by loading box | Camera detects box shape; evaluates clearance |
| APA already started maneuver before motorcycle detected | Maneuver pauses; driver alerted |

### Acceptance Criteria
- Bay with motorcycle correctly classified as "partially occupied" in 95% of test cases
- No collision with motorcycle in APA maneuver for described scenario

---

## Q59: 3D Surround View for Elevated Obstacles

### Scenario
While maneuvering in a height-restricted car park (2.0 m height bar), the standard 2D surround view does not show the height restriction bar. The vehicle's roof antenna (1.85 m height) barely clears but the unaware driver does not reduce speed and the antenna clips the barrier.

### Expected Behavior
Advanced surround view / parking assist should warn of overhead height restrictions. 3D surround view or a height warning from a map/barrier sensor is required.

### Detailed Explanation
- Standard surround view (4 fisheye cameras) provides a top-down 2D view — excellent for lateral obstacles but blind to overhead ones.
- Overhead clearance detection requires:
  1. Ultrasonic height sensor (some vehicles have roof-mounted USS)
  2. Camera-based overhead detection (front wide-angle camera looking up slightly)
  3. HD map height restriction data (if car park is mapped)
- The most effective solution: front camera height bar detection (using camera detecting the bar's visual marker) + DCA (Driver Clearance Alert).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Roof rack installed (increasing vehicle height) | Driver manually enters modified height in vehicle settings |
| Retractable antenna (telescoping) | If antenna retracted, clearance check adjusted |
| Underground car park ramp with lowering ceiling | 3D clearance must be checked along entire trajectory, not just entry |
| Tree branch hanging over parking space | Camera detects branch; warn driver |

### Acceptance Criteria
- Height restriction bar detected from ≥ 5 m distance with camera
- Alert issued if remaining clearance ≤ 10 cm above vehicle's maximum height point

---

## Q60: Parking Assist Night-Time Performance

### Scenario
In a poorly lit underground car park at night, the 360° surround view camera images are very dark and noisy. The APA function is not detecting a kerb clearly. What are the requirements for low-light surround view performance?

### Expected Behavior
Surround view cameras should be equipped with Sony STARVIS or equivalent low-light CMOS sensors supporting ≥ 0.1 lux sensitivity. APA must function in illuminance down to 1 lux.

### Detailed Explanation
- Standard CMOS cameras degrade significantly below 10 lux.
- Low-light camera requirements for parking: ≥ 0.1 lux sensitivity, adequate SNR.
- IR illuminators (near-infrared LEDs) can supplement ambient light around the vehicle.
- Image processing: sensor ISP applies noise reduction (NR) and HDR algorithms.
- USS is light-independent — APA's USS-based collision avoidance remains fully functional.
- The visual display (surround view image) is for driver awareness; the safety-critical stop logic relies on USS.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Bright headlights of another car directly into rear camera | HDR suppresses overexposure; some saturation acceptable |
| Flickering fluorescent lights at 50 Hz (vs 60 Hz camera) | Camera frame rate not synchronized; banding possible; fix in ISP settings |
| Camera lens condensation in cold underground car park | Heated camera lens or warning displayed |
| Complete darkness (power outage in car park) | USS continues; camera shows all-black; APA guided by USS only |

### Acceptance Criteria
- Surround view image usable (kerb detectable by camera) at ≥ 1 lux ambient lighting
- APA USS-based collision avoidance functions independently of camera quality at all illumination levels
