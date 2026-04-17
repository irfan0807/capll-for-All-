# Lane Departure Warning & Lane Keep Assist (LDW/LKA) — Scenario-Based Questions (Q21–Q30)

---

## Q21: LDW Activation Without Turn Signal — Standard Departure

### Scenario
The ego vehicle is traveling at 90 km/h on a two-lane national road with clearly visible white lane markings. The vehicle drifts 0.3 m across the left lane marking without the driver activating the turn signal. The road is straight and dry.

### Expected Behavior
LDW should issue a visual + auditory warning (and optionally haptic seat/steering vibration) when the vehicle crosses the lane marking without turn signal activation.

### Detailed Explanation
- LDW uses the front camera to detect lane markings and compute lateral offset from lane center.
- Warning trigger: when the vehicle's tire edge crosses (or is about to cross) the lane marking without turn signal.
- The warning threshold is typically at the marking boundary ± a small tolerance (0–10 cm)
- LDW is a warning-only function; it does not steer.
- Turn signal suppression: if the driver has activated the turn indicator, LDW is suppressed for the indicated direction.
- Warning is canceled once the vehicle has returned to within the lane.
- Speed threshold: LDW typically operates > 60–70 km/h to avoid nuisance in city driving.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver corrects before fully crossing line | LDW fires briefly; cancels when trajectory returns inward |
| Driver intentionally changes lane slowly without signal | LDW fires; driver is expected to use signal for intentional lane changes |
| One lane marking worn/invisible (rural road) | One-side LDW only; opposite side still functional |
| Merging lane ends (lane disappears) | Camera must detect lane merge and suspend LDW for merging side |
| Road with rumble strips at lane edge | Haptic wheel vibration from road surface may interfere with LDW haptic feedback |
| Vehicle on banked road (camber) | Natural lateral drift; LDW threshold adjusted for road camber |

### Validation Approach
- Lane marking detection in varying road surface conditions
- Daytime + night-time testing with varying illumination
- Camera degradation tests (dirty camera, sun glare)

### Acceptance Criteria
- LDW warning issued within 300 ms of tire reaching lane marking
- False positive rate < 0.3 per 100 km on well-marked highways

---

## Q22: LKA Intervention — Steering Torque Override

### Scenario
Lane Keep Assist (LKA) is active at 110 km/h. The ego vehicle drifts toward the right lane boundary due to a strong crosswind. LKA applies a left-steering torque correction. The driver feels resistance on the steering wheel. What is the correct torque magnitude and override behavior?

### Expected Behavior
LKA applies a gentle corrective torque (typically 2–5 Nm) to bring the vehicle back toward lane center. If the driver deliberately counters with higher torque, LKA releases authority (driver override).

### Detailed Explanation
- LKA is active above ~60–70 km/h and uses the EPS (Electric Power Steering) to apply corrective torque.
- Torque magnitude is calibrated to be noticeable but not jarring: 2–5 Nm depending on speed.
- Driver hands-on detection: LKA should monitor for hands-on steering via torque sensor (hands-off detection triggers warning).
- Driver override threshold: if driver applies > 8–10 Nm (effort exceeding LKA), LKA releases.
- LKA does NOT prevent lane change — it only gently discourages unintentional drift.
- In EU regulations, LKA must include "hands-off" monitoring (GSR — General Safety Regulation 2022).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Strong sustained crosswind causing continuous drift | LKA applies continuous torque up to its limit; warns driver if unable to maintain lane |
| Driver falls asleep (hands off wheel for > 10 s) | LKA issues escalating Driver Attention Warning + prepares to slow vehicle |
| LKA and driver both steer same direction (agreement) | Combined action; LKA torque supplements driver |
| Narrow lane (construction): correct lateral position unavailable | LKA deactivates; warns driver of inability to keep lane |
| LKA fighting against driver intentional lane change | LKA senses sustained driver counter-torque, releases after 1–2 s |

### Acceptance Criteria
- LKA corrective torque: 2–5 Nm at 110 km/h
- Driver override achieved with < 10 Nm counter-input
- LKA deactivates within 500 ms of driver override

---

## Q23: LDW in Poor Lane Marking Conditions (Faded Markings)

### Scenario
The ego vehicle is driving on an old rural road where lane markings are partially visible — approximately 40% of the dashes are visible, with many segments worn away. The camera's lane detection confidence is reported at 45%. Should LDW activate?

### Expected Behavior
LDW should enter a "low confidence" mode, displaying a degradation HMI notice. Warning should only be issued against the detected segments with sufficient confidence. LDW should NOT completely deactivate, but reliability is reduced.

### Detailed Explanation
- Lane detection algorithms classify each lane marking segment independently and compute an overall confidence score.
- Industry threshold: LDW requires ≥ 60–70% lane confidence to fire warnings; below this, warnings are suppressed.
- At 45% confidence, a degradation indicator ("LDW Limited" icon) is displayed.
- Alternative inputs: road edge detection (curb, roadside vegetation), radar lateral occupancy, and HD map can supplement faded line data.
- Night-time and rain compound the problem; camera algorithms must weight these factors.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Freshly repainted road with double markings (old + new) | Camera may detect two line candidates; must select correct (outermost, or newest) |
| Snow-covered lane markings | Lane markings invisible; LDW deactivates fully; road edge detection backup |
| Water reflections on wet road mimicking lane markings | False lane detection; Kalman filter temporal consistency check required |
| Road under construction with temporary orange markings | Orange markings are valid; camera must handle non-white/yellow markings |
| Dashed vs. solid center line crossing (opposite lane entry) | Solid line crossing is critical; warning priority higher than dashed |

### Acceptance Criteria
- LDW degrades gracefully at < 60% marking confidence with HMI notification
- Zero false LDW activations from road reflections or shadow patterns

---

## Q24: LDW/LKA Deactivation Scenarios

### Scenario
During a software validation test, the tester notes that LKA is still active while the vehicle is driving on a roundabout. The constant steering corrections for the circular path conflict with LKA lane centering. This is incorrect behavior.

### Expected Behavior
LKA should deactivate or suppress corrections on roundabouts and sharp curves where the road curvature exceeds LKA's steering authority limit.

### Detailed Explanation
- LKA operates within a curvature range: typically radius > 300–500 m on highways. Sharper curves exceed LKA's capability.
- Roundabouts (radius 10–50 m) are well beyond LKA's design domain.
- Navigation or HD map data can identify roundabouts for pre-emptive LKA deactivation.
- Camera-based curvature estimation: if detected curve radius < 200 m, LKA suspends automatically.
- The HMI should display "LKA temporarily unavailable" during roundabout navigation.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Roundabout entry without map confirmation | Camera curvature triggers suspension |
| Long sweeping curve (radius 250 m at 70 km/h) | Borderline case; LKA applies gentle correction only |
| Highway on-ramp spiral | LKA suspends during tightest section, reactivates on highway |
| Driver bypasses roundabout detection (uncommon road geometry) | Manual LKA deactivation button available to driver |

### Acceptance Criteria
- LKA automatically deactivates detected when road radius < 200 m
- No nuisance LKA corrections on roundabouts in 100% of test passes

---

## Q25: LKA Hands-Off Detection and Driver Responsibility

### Scenario
EU General Safety Regulation (GSR 2022) mandates that LKA-equipped vehicles must monitor driver hands-on status. During testing, the driver holds the wheel with only fingertip contact (< 0.1 Nm grip). The system reports "hands off." Is this correct?

### Expected Behavior
Hands-off detection calibration must be sensitive enough to distinguish light fingertip contact from genuinely absent hands. A threshold of ~0.3–0.5 Nm is typical for "hands-on" confirmation.

### Detailed Explanation
- Hands-on detection uses capacitive steering sensor (preferred, more reliable) or torque-based detection.
- Capacitive sensor detects hand presence without requiring force.
- Torque-based detection has false negative risk for relaxed hand grip.
- GSR 2022 mandates: within 15 s of hands-off, escalating warning; within 30 s, additional actions (speed reduction, hazard lights, pull-over).
- Level 2 ADAS: driver must remain engaged; Level 3 allows hands-off in ODD.
- Fingertip contact < 0.1 Nm is ambiguous — capacitive is preferred to handle this case.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver wearing thick gloves (low capacitance) | Capacitive sensor may fail; torque-based fallback required |
| Wet hands reducing capacitance | Calibration must handle high humidity / sweating |
| Driver leans arm on wheel without gripping | Weight-based signal vs grip detection difference |
| Sleeping driver with hands resting on wheel | DMS (Driver Monitoring) + hands-on detection combined |

### Acceptance Criteria
- Hands-off correctly detected within 500 ms of actual hand removal
- 0.5 Nm grip consistently classified as hands-on
- False negative rate (hands-on incorrectly reported as off) < 0.1%

---

## Q26: LDW in Construction Zones with Modified Lane Markings

### Scenario
The ego vehicle enters a motorway construction zone. The original white lane markings are crossed out with yellow X marks and new temporary yellow lane markings are painted. The camera detects both old and new markings simultaneously.

### Expected Behavior
LDW/LKA must follow the temporary yellow markings (active lanes) and ignore the crossed-out white markings.

### Detailed Explanation
- In construction zones, both old (white) and new (yellow) markings are simultaneously present.
- Camera algorithms must prioritize: newer yellow markings over old white markings where both are visible.
- Color discrimination models in the lane detection CNN must handle yellow vs. white classification.
- Old white markings that are not crossed-out but adjacent to yellow may create ambiguity.
- The safest approach: driver notification of construction zone (via TSR or map), LDW moves to advisory-only mode.
- Map updates via V2X (C-ITS) construction zone messages can instruct ADAS to use temporary markings.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Yellow markings partially overlapping white markings | Vision-based segmentation with color filter |
| Construction zone has neither old nor new markings visible | LDW fully deactivated; warn driver |
| Temporary barriers (jersey barriers) at marking edge | Road edge detection from barriers; supplemental LDW input |
| Lane narrowed from 3.5 m to 2.0 m | LKA must adjust lane center estimate for narrow lane width |

### Acceptance Criteria
- Correct lane tracking in construction zone in ≥ 90% of test trials
- LDW follows yellow temporary markings when clearly visible

---

## Q27: LKA Interaction with Active Navigation Route Change

### Scenario
The driver is following GPS navigation on a 3-lane highway. The navigation system instructs the driver to take a right exit in 500 m, requiring a lane change from lane 1 (leftmost) to lane 3 (rightmost). LKA is active. What happens?

### Expected Behavior
LKA should be aware of the planned route and suppress lane departure warnings for the intended lane changes if the driver activates the turn signal. Navigation integration should prevent LKA from fighting the driver during a planned lane change.

### Detailed Explanation
- Navigation-integrated LKA: the navigation route includes lane recommendation.
- When navigation indicates an exit in < 600 m, LKA switches to "guide mode" — neutral centering, ready to follow driver's turn signal.
- Turn-signal activated lane change: LKA fully suppresses for the signaled direction and holds correction after the lane change is complete.
- Without navigation integration, LKA would resist each lane marking crossing — very poor user experience.
- Euro NCAP requires LKA not to interfere with clearly signaled intentional lane changes.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver changes lane without signal despite navigation instruction | LDW fires (no signal detected) |
| Navigation reroutes live: exit no longer needed | LKA resumes normal centering immediately |
| Driver takes a different route than navigation (overrides GPS) | Navigation intent cancelled; LKA reverts to standard mode |

### Acceptance Criteria
- Zero LDW/LKA nuisance activations for turn-signal-accompanied lane changes
- LKA resumes lane centering within 2 s of completing a signaled lane change

---

## Q28: LDW Camera Blockage in Sunlight Conditions

### Scenario
The ego vehicle is driving east at sunrise. Direct low-angle sunlight causes camera saturation. The lane detection processor reports "low confidence" for 12 continuous seconds. Should the driver be warned?

### Expected Behavior
LDW should display a "camera blocked / sunlight" degradation indicator immediately when confidence drops below threshold. If blockage persists > 3 s, LKA should deactivate and a warning tone should sound.

### Detailed Explanation
- Low sun angle (< 20° above horizon) is a known failure mode for forward-facing cameras.
- Auto high-beam and auto-dimming cameras can help but may not fully resolve the issue.
- HDR (High Dynamic Range) camera systems handle a wider luminance range.
- When the sun moves above the camera's sensitivity range (typically after 10–15 min post-sunrise), the system recovers.
- ISO 21448 (SOTIF) requires this as a known operational design domain (ODD) limitation.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Sun visor partially blocks sunlight (driver adjusts) | Partial improvement; camera confidence may recover if sunlight bouncing not excessive |
| Tunnel exit into bright sunlight | Sudden exposure; temporary LDW degradation expected & accepted |
| Snow reflection (white ground) causing overexposure | Different wavelength but similar overexposure effect |
| Camera with P-polarization filter reducing glare | Extended functional range in sunlight; update ODD accordingly |

### Acceptance Criteria
- LDW degradation HMI shown within 1 s of < 30% lane confidence
- LKA deactivated within 3 s of sustained low confidence
- Auto-recovery when confidence returns to > 70%

---

## Q29: LDW System Calibration After Windshield Replacement

### Scenario
The ego vehicle's windshield is replaced after stone chip damage. The LDW camera (mounted at top center of windshield) is now mounted 3 mm lower and 2° rotated. Post-replacement, LDW issues premature warnings even when the vehicle is perfectly centered.

### Expected Behavior
Camera re-calibration must be performed after windshield replacement. Until calibrated, LDW should display "calibration required" and operate only with reduced sensitivity or remain deactivated.

### Detailed Explanation
- The camera mounting angle (pitch, roll, yaw) directly affects lane marking position estimation.
- A 2° pitch error at 20 m range causes a ~70 cm height error (relevant for AEB, not LDW).
- A 2° yaw error causes ~70 cm lateral error at 20 m — highly relevant for LDW.
- Modern ADAS cameras include intrinsic + extrinsic calibration stored in ECU EEPROM.
- Post-windshield replacement: static calibration target required at service workshop.
- Some vehicles support in-motion self-calibration (online calibration) using lane markings as reference targets.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Customer re-installs same camera without correct mount position | Online calibration correction limited to small angles; out-of-range → service required |
| Aftermarket windshield with slightly different curvature | Refraction characteristics differ; may affect camera field of view |
| Camera mounting bolt loose (rotates slightly during drive) | Intermittent calibration drift; detected by online consistency monitoring |

### Acceptance Criteria
- LDW deactivated and "calibration required" displayed if extrinsic calibration data is absent/invalidated
- Post-calibration: LDW false positive rate returns to < 0.3 per 100 km

---

## Q30: LKA at Lane Level — Multi-Lane Road Priority Handling

### Scenario
The ego vehicle is on a 4-lane highway. LKA is active and keeping the vehicle centered in lane 2. A large truck in lane 1 comes close to the lane boundary, and the LKA attempts to shift the ego vehicle toward the lane 2/3 boundary to create lateral clearance. Is this correct behavior?

### Expected Behavior
Standard LKA should center the vehicle in its own lane. "Comfort LKA" or "Safety Distance Offset" feature may shift the vehicle away from close large obstacles, but this is a more advanced feature requiring explicit activation and multi-lane object awareness.

### Detailed Explanation
- Basic LKA operates only within the ego vehicle's lane.
- Advanced LKA variants (LCA — Lane Centering Assist) include lateral offset based on adjacent vehicle proximity.
- The lateral offset behavior requires: adjacent object detection, size estimation (truck width), and available space calculation.
- Risk: shifting toward lane 3 boundary without confirming lane 3 clearance could be dangerous.
- Correct behavior: only shift within the own lane's clearance, after confirming space is available.
- ODD for offset: only when adjacent vehicle is confirmed (high confidence) and sufficient lateral space in the own lane exists.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Truck drifting into ego lane | LKA should not fight an ongoing collision; AEB/ESA takes priority |
| Ego vehicle in leftmost lane with truck on right | Offset left not available (road boundary); LKA centers without offset |
| Multiple trucks on both sides | No lateral offset possible; centered lane position maintained |
| Offset requested when already near opposite lane boundary | Offset suppressed if result would place vehicle within 20 cm of opposite lane marking |

### Acceptance Criteria
- Basic LKA: vehicle stays within ±20 cm of lane center
- Advanced offset: only activates with high-confidence adjacent object AND ≥ 40 cm lateral margin available in own lane
