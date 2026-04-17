# Pedestrian & Cyclist Detection (PCD) — Scenario-Based Questions (Q71–Q80)

---

## Q71: Pedestrian Detection at Unsignalized Midblock Crossing

### Scenario
A pedestrian steps off the pavement at a mid-block (no traffic light, no marked zebra) onto a 60 km/h road. The ego vehicle is approaching at 55 km/h. Distance to pedestrian is 22 m. No driver reaction.

### Expected Behavior
AEB-Pedestrian detects the pedestrian, predicts the collision trajectory, and activates emergency braking. At 55 km/h with 22 m, TTC ≈ 1.44 s — AEB must activate immediately.

### Detailed Explanation
- Pedestrian detection uses camera (primary, deep CNN) + radar (supplemental for range).
- The system must predict the pedestrian's trajectory: perpendicular road crossing most dangerous.
- Stopping distance at 55 km/h with 9 m/s² braking = 13.8 m → collision avoidance is possible at 22 m.
- AEB-P must classify walking direction and speed before activating to avoid braking for pedestrians not in the vehicle's path.
- Lateral prediction: a pedestrian stepping off the pavement has an initial lateral velocity (toward the road) — this is the key detection cue.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Pedestrian stops at road edge (does not step off) | No lateral velocity detected; no AEB activation |
| Pedestrian crosses rapidly (running — 4 m/s) | Faster crossing rate; AEB must account for updated predicted crossing time |
| Multiple pedestrians at road edge | Track each independently; activate AEB for the closest/most dangerous trajectory |
| Pedestrian obscured by parked van, emerges suddenly | Late detection due to occlusion; AEB may have < 1 s TTC; partial mitigation |
| Pedestrian in mobility scooter (non-standard silhouette) | PCD must generalize to powered mobility devices |
| Pedestrian crossing against red light (unexpected) | AEB does not judge legality; activates based on trajectory, not traffic light state |

### Acceptance Criteria
- AEB-P activates for perpendicular adult crossing from ≥ 30 km/h impact speed in 100 km/h ODD
- Collision speed reduction ≥ 20 km/h vs. no-braking baseline in NCAP VRU tests

---

## Q72: Cyclist Detection — Parallel Riding Along Road Edge

### Scenario
A cyclist is riding along the right edge of a 1-lane road at 15 km/h. The ego vehicle is overtaking at 60 km/h with a 1.0 m lateral clearance. No collision; cyclist stays in lane. Should any ADAS function activate?

### Expected Behavior
- AEB/PCD: should NOT activate (no collision trajectory — cyclist is parallel, not crossing).
- LCA (Lane Change Assist): if the overtake required a lane change, LCA should confirm no oncoming traffic.
- The system should monitor the cyclist in case of sudden swerve.

### Detailed Explanation
- A cyclist riding parallel at constant velocity is NOT in a collision path with the overtaking vehicle.
- Prediction model: cyclist velocity vector is parallel to road → predicted position does not intersect ego vehicle path.
- However, cyclists can swerve to avoid potholes, open drains, or parked cars — sudden lateral movement risk.
- The lateral safety monitoring can maintain a "watch" state for the cyclist during the overtake window.
- Camera tracking: cyclist bounding box tracked through the overtake; if lateral velocity increases, AEB prepares.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cyclist swerves left (avoiding pothole) during overtake | Sudden lateral velocity: AEB-Cyclist activates immediately |
| Cyclist signals a turn (arm gesture) | Camera gesture recognition may not detect arm signal; conservative watch state maintained |
| Cyclist in very narrow road: 0.3 m clearance | APA clearance warning; LKA correction applied |
| Night-time cyclist with no lights | Low-visibility detection; NIR headlights help; reduced detection range |
| Cyclist with trailer (child trailer behind bicycle) | The trailer increases cyclist width; detection model must include trailer |

### Acceptance Criteria
- No AEB activation for parallel-moving cyclist with constant trajectory
- AEB activates within 400 ms of cyclist lateral swerve > 0.5 m/s toward ego vehicle at < 3 s TTC

---

## Q73: Pedestrian Detection — Group Dynamics and Occlusion

### Scenario
A group of 5 school children is crossing the road as a cluster. The front camera detects the group but tracks it as a single wide bounding box. One child at the edge may be poorly tracked. Does this create a safety gap?

### Expected Behavior
The pedestrian detection should ideally resolve individual pedestrians in a dense group or at minimum treat the cluster as a wide obstacle. The AEB target width should cover the full group extent.

### Detailed Explanation
- Dense pedestrian groups: instance segmentation is preferred over simple bounding box detection.
- In practice, many production systems use a combined-group bounding box: the outer dimensions of the group are used for AEB target extent.
- AEB will brake based on the nearest edge of the bounding box.
- Error case: child at the edge of the group is outside the group bounding box (straggler) — undetected until they emerge.
- Best practice: AEB should use a conservative (expanded) bounding box with ± 0.5 m margins for pedestrian targets.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Child runs ahead of the group (splits from group) | New individual detection; dual-track: group + new individual |
| Group partially on road, partially on pavement | Collision path analysis for road-side members only |
| Adult with child (height difference) | Both classified independently if detectable |
| Group in uniforms (school uniform, similar appearance) | Not a DNN performance concern; visual feature diversity in training data is key |

### Acceptance Criteria
- Group AEB bounding box covers 100% of pedestrian cluster extent in test scenarios
- Straggler pedestrian (0.5 m outside group box) detected or bounding box expansion accounts for it

---

## Q74: Cyclist Detection in Low-Light and High-Speed Scenarios

### Scenario
At dusk (luminance ~5 lux), a cyclist in dark clothing exits a parking lot at 20 km/h and crosses the road. The ego vehicle is at 70 km/h with 15 m distance to collision point.

### Expected Behavior
At 70 km/h with TTC ≈ 0.77 s, AEB-Cyclist must detect and activate almost instantly. At 5 lux, camera sensitivity is critical. Radar may detect the bicycle frame (if it returns sufficient signal).

### Detailed Explanation
- 5 lux is near the lower limit of standard camera performance.
- The bicycle has metallic components with moderate radar cross-section but the cyclist's body is low RCS.
- NIR headlights or dynamic high-beam illumination can increase effective detection range.
- Low angle sun at dusk creates long shadows and variable illumination — camera performance varies.
- ADB (Adaptive Driving Beam): at dusk, vehicle switches to high beam with ADB centering; this increases detection range to 40–60 m even in such conditions.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cyclist without reflector or lights (road law violation) | AEB relies on camera/radar passively; no guarantee at very low RCS |
| Bicycle with full lights (front and rear): better detectability | Lights dramatically increase camera detection range |
| Puddle reflection of cyclist — ghost ahead | Ghost rejection via 3D radar + camera fusion |
| Cyclist runs red light and crosses at high speed | Trajectory prediction must adjust for faster-than-expected crossing |

### Acceptance Criteria
- AEB-Cyclist activates for crossing cyclist at ≥ 20 m detection range at 5 lux ambient with ADB active
- Overall system response time (detection → brake command) ≤ 150 ms

---

## Q75: Child Pedestrian Detection — Size and Behavior Differences

### Scenario
A child (1.1 m tall, 4 years old) runs into the road chasing a ball between two parked cars. The ego vehicle is at 30 km/h, 10 m ahead. Can the PCD system detect and respond?

### Expected Behavior
AEB-P must detect children (shorter, smaller bounding box than adults) and activate even at very short TTC. At 30 km/h, 10 m gives TTC = 1.2 s — the system must act immediately.

### Detailed Explanation
- Child pedestrian detection: DNN must be trained with child-sized bounding boxes.
- NCAP VRU child tests (CPNA: Child Pedestrian Near-side Adult) at 20 and 30 km/h.
- The 1.1 m height child has different camera pixel density than an adult at the same range.
- Occlusion by parked cars: child emerges suddenly → first visible frame is at very short distance.
- The biggest challenge: pre-emergence prediction (predicting a child behind parked cars based on movement pattern or ball).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Child crouching to pick something up (not moving into road) | Low or zero lateral velocity; no AEB |
| Child running vs. walking (higher velocity heading to road) | Running child reaches road faster; AEB must account for velocity |
| Child on bicycle (cyclist profile, child height) | Combined classification |
| Child partially occluded: only legs visible | Lower body detectors (feet/legs visible under parked car) can preemptively identify pedestrian |

### Acceptance Criteria
- Child pedestrian (1.0–1.4 m height) detected from ≥ 15 m at 30 km/h in NCAP test scenario
- AEB-P activates for CPNA scenario at 20 and 30 km/h per Euro NCAP 2025 protocol

---

## Q76: Pedestrian in Night with Umbrella — Category Mismatch

### Scenario
A person holding a large open umbrella crosses the road at night. The umbrella obscures the normal human silhouette. The camera-based PCD classifies the object as "non-pedestrian" and no warning is issued.

### Expected Behavior
PCD should still detect the object as a likely pedestrian based on the lower body (legs visible below umbrella) and human-like movement, even if the silhouette is atypical.

### Detailed Explanation
- Umbrella-carrying pedestrian: camera DNN sees an unusual top contour but normal legs and gait.
- Motion-based classification: gait analysis (leg motion frequency) can confirm pedestrian even if overall shape is unusual.
- Radar: detects a moving object with pedestrian-like micro-Doppler signature (limb movement).
- Sensor fusion: camera + radar combined classification reduces misclassification risk.
- Training data for DNN must include umbrella-carrying pedestrians.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Person in rain poncho (covers body shape) | Leg motion still visible; motion-based classification |
| Statue or scarecrow in road (static humanoid) | Static object; no micro-Doppler; AEB not activated |
| Moving mannequin or robot (delivery robot) | Novel object category; classify conservatively as pedestrian |
| Person in mascot costume (full body suit) | Non-standard shape; motion-based classification fallback |

### Acceptance Criteria
- Umbrella-carrying pedestrian detected with ≥ 85% confidence at standard NCAP evaluation distances
- No false negative for night-time umbrella scenario in dedicated test protocol

---

## Q77: Ghost Pedestrian — False Positive from Shadow

### Scenario
At sunrise, the long shadow of a fence post moves across the road as the vehicle travels. The camera classifies the moving shadow as a pedestrian and AEB activates. This is a dangerous false positive.

### Expected Behavior
AEB must not activate for shadows, road markings, or non-solid objects. The lack of radar return for a shadow should prevent false AEB activation.

### Detailed Explanation
- The camera sees a dark, moving, human-like elongated shadow → classification ambiguity.
- The radar does NOT detect shadows (no physical object → no radar return).
- In sensor fusion: camera classification alone is insufficient for AEB activation.
- AEB requires camera object detection + radar range confirmation as a safety gate.
- Shadow false positive is a known SOTIF trigger scenario (ISO 21448).
- Training data augmentation: camera DNN should be trained to not classify shadows as pedestrians.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Shadow cast by tree (blowing in wind, dynamic) | Dynamic shadow with no radar return; correctly suppressed |
| Smoke drifting across road | Camera sees movement; no radar detection; suppressed |
| Drifting leaves (fast-moving cluster) | Camera may see movement; radar does not return for leaves; suppressed |
| Real pedestrian in deep shadow (dark area): camera misses | Opposite problem: genuine pedestrian in shadow not detected → radar takes over |

### Acceptance Criteria
- Zero AEB activations for shadows or non-solid visual artifacts in shadow-test protocol
- AEB requires confirmed radar return as mandatory gate for activation (not camera-only)

---

## Q78: Pedestrian Facing Away — Back Detection

### Scenario
A pedestrian is standing with their back to traffic at a bus stop that is adjacent to the road. They might step backward into the road. Can PCD detect pedestrians facing away?

### Expected Behavior
PCD should detect pedestrians regardless of their facing direction. The rear silhouette of a human body is still a valid training class for deep learning detectors.

### Detailed Explanation
- Camera DNN classification: pedestrian class should generalize to all orientations (front, back, side).
- Radar micro-Doppler: even a stationary pedestrian has some micro-Doppler from breathing or micro-movements.
- The system should monitor the pedestrian's position and velocity — as long as they remain stationary, no threat.
- If the pedestrian begins moving backward (toward the road), lateral velocity appears → threat assessment begins.
- This scenario is also relevant for road workers with backs to traffic.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Pedestrian looking at phone (distracted): sudden step backward | Reaction time 0; AEB must cover for pedestrian's lack of road awareness |
| Pedestrian at bus stop in dark clothing (rear-facing at night) | NIR camera + radar combo |
| Multiple pedestrians at bus stop (occlusion) | Track each independently |

### Acceptance Criteria
- Pedestrian classified correctly regardless of orientation (front/back/side aspect) in 95% of cases
- Back-facing stationary pedestrian near road: no AEB, but tracked as potential threat

---

## Q79: Pedestrian Detection in Intersection Conflict Zones

### Scenario
The ego vehicle is making a right turn at a signalized intersection. The pedestrian crossing on the right is currently green (pedestrians walking). The ego vehicle's turn path conflicts with the crossing pedestrians. Should AEB-P activate?

### Expected Behavior
Yes — pedestrians in the intersection crossing zone who are in the ego vehicle's turning path are a genuine collision threat. AEB-P should detect them and if a collision is predicted (TTC < threshold), activate braking.

### Detailed Explanation
- Turn + pedestrian conflict: one of the most common urban accident causes.
- The camera must scan the full turning arc (not just straight ahead) during a turn.
- Wide-angle or corner cameras can supplement the front camera's view during turns.
- At low turning speed (< 20 km/h), AEB-P has more time to react but must still be sensitive.
- V2X: if the intersection has smart traffic infrastructure, it can provide pedestrian presence signals.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Pedestrian already crossed — only rear portion still in path | Head-rear bounding box; confirm if rear still in ego path |
| Ego vehicle turns onto large junction; pedestrian far across | Distance estimation critical; no False AEB for distant non-threat |
| Multiple pedestrians crossing: one stops, one continues | Track each; AEB for continuing pedestrian on collision path |
| Intersection with partial occlusion by a stopped bus | Late detection; AEB must compensate |

### Acceptance Criteria
- AEB-P detects and activates for right/left turn conflict with crossing pedestrian at speeds 10–30 km/h
- No false AEB for pedestrians confirmed outside the turning arc

---

## Q80: Pedestrian Detection System Validation Framework

### Scenario
The validation team asks: "What is the complete test plan for validating AEB-Pedestrian per Euro NCAP 2025?" Define the key scenarios, metrics, and acceptance criteria.

### Expected Behavior
A complete AEB-P validation framework includes structured test scenarios, simulation, and closed-track testing.

### Test Scenarios (Euro NCAP VRU 2025)
| ID | Scenario | Ego Speed | Description |
|----|----------|-----------|-------------|
| CPNA | Child Near-Side Adult | 20, 30 km/h | Child from between parked cars |
| CPFA | Child Far-Side Adult | 20, 30 km/h | Child from far side of opposing adult |
| PPNA | Pedestrian Near-Side adjacent | 20–60 km/h | Adult crossing in near lane |
| PPFA | Pedestrian Far-Side | 20–60 km/h | Adult crossing from far side |
| CPNC | Child near-side cyclist | 20, 30 km/h | Child from near side cyclist |
| PTP | Pedestrian Turn Path | 10–20 km/h | Pedestrian in turning path |

### Validation Metrics
- **Detection Rate**: % of test runs where pedestrian was detected
- **Warning Rate**: % of runs with FCW warning before AEB
- **AEB Activation Rate**: % of runs AEB activated correctly
- **False Positive Rate**: AEB activations per 1,000 km normal driving
- **Speed Reduction at Impact**: mean and worst-case speed at point of impact

### Acceptance Criteria
- Detection rate ≥ 99% in all Euro NCAP scenarios
- AEB activation rate ≥ 95% for scenarios with TTC ≤ 1.5 s at detection point
- False positive rate ≤ 0.5 per 10,000 km in approved test routes
- Speed reduction ≥ 20 km/h vs. baseline in all Euro NCAP pass conditions
