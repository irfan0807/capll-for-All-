# Vehicle Cluster Scenarios — Scenario-Based Questions (Q1–Q15)

> **Domain**: Groups of vehicles traveling closely together on the road and how ADAS (ACC, BSD, AEB, FCW, LKA) handles the resulting multi-target complexity.

---

## Q1: ACC Following a Convoy — Target Selection in a 5-Vehicle Convoy

### Scenario
A 5-vehicle convoy (military trucks, 8 m spacing) is traveling at 80 km/h on a dual carriageway. The ego vehicle approaches from behind at 120 km/h with ACC active at a 2.5 s set gap. Which vehicle should ACC select as its target, and does the selection change as the ego vehicle closes in?

### Expected Behavior
ACC should always track the **nearest in-lane vehicle** (the last vehicle in the convoy, i.e., the tail vehicle). It should NOT attempt to select a vehicle deeper in the convoy.

### Detailed Explanation
- ACC's primary target selection rule: nearest confirmed in-lane vehicle.
- The tail vehicle (V5, closest) provides the immediately relevant closing information.
- Other convoy vehicles (V1–V4) are detected but filtered out as "farther targets" — they are irrelevant until V5 is no longer present.
- Multi-target radar maintains tracks on all 5 vehicles but the ACC target arbitration layer selects V5.
- As the ego vehicle decelerates to match the convoy speed, the radar tracks V5 stably.
- Risk scenario: if V5 exits the lane (takes an exit), ACC must immediately reacquire V4 — the new tail vehicle.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| V5 brakes suddenly while ego is still closing at 40 km/h relative | Short TTC; AEB escalates after FCW warning |
| V5 exits the motorway; V4 becomes the new tail | Target handoff within 1 sensor cycle (50 ms); no acceleration surge |
| Convoy speeds up together (all 5 accelerate simultaneously) | Range to V5 increases; ACC accelerates back to set speed smoothly |
| Convoy decelerates together (chain braking) | Closing speed on V5 increases rapidly; FCW → AEB cascade required |
| Gap between V4 and V5 opens (V5 slows independently) | V5 still nearest; ACC adjusts to V5's new speed |
| Convoy passes through tunnel: radar multi-path | Tunnel walls create ghost tracks; multi-target tracker must reject wall reflections |

### Validation Approach
- Convoy test at proving ground: 5 pre-programmed target vehicles in convoy
- Verify via CAN: ACC target ID remains the V5 track ID throughout approach
- Target handoff test: V5 programmatically changes lane; confirm V4 reacquisition within 100 ms

### Acceptance Criteria
- ACC always selects minimum-range in-lane vehicle
- Target handoff latency ≤ 100 ms when tail vehicle exits lane
- No acceleration surge (> 1.5 m/s²) following target handoff

---

## Q2: AEB Chain Braking in a Vehicle Cluster

### Scenario
A cluster of 6 vehicles is traveling at 100 km/h at 15 m spacing. Vehicle V1 (front of cluster) brakes at 10 m/s² due to a sudden obstacle. This triggers V2 to brake, which triggers V3, and so on — a chain brake event. The ego vehicle is following V6 (tail) at a 2.5 s time gap. AEB must respond.

### Expected Behavior
AEB monitors the ego-to-V6 TTC only. As V6 brakes, the ego's AEB activates based on V6's deceleration detected via:
1. **Direct radar measurement**: V6's relative velocity increases (closing speed grows).
2. **Brake light detection** (camera-based): V6's brake lights illuminate.
3. **V2X C2C message** (if equipped): V6 broadcasts its brake event.

### Detailed Explanation
- Human reaction time in a chain brake: ~0.8–1.2 s per vehicle.
- By V6, the chain brake wave has been delayed by ~5–6 s from V1's initial brake.
- V6's deceleration may be sharper than V1's due to compressed chain reaction.
- The ego vehicle must not rely on human perception — AEB provides sub-100 ms response.
- Brake light detection via camera supplements radar: camera detects V6's brake lights before significant deceleration is measured by radar → earlier warning.
- Pre-fill: brake hydraulic pre-fill at brake light detection stage reduces AEB latency by ~80 ms.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| V6 brakes hard but briefly (false alarm: pothole) | AEB activates then quickly releases; residual deceleration handled gracefully |
| V6 rear lights not working (brake light camera useless) | Radar deceleration measurement only; slightly later warning |
| Chain braking at night: camera brake light detection impaired | Radar primary; no HMI degradation expected (brake light detection is enhancement only) |
| Ego vehicle also traveling in a convoy (vehicles behind the ego vehicle) | AEB fires; vehicles behind the ego must react independently; V2X helps propagate warning |
| Chain braking on downhill gradient: much shorter stopping distances | Lower friction + gravity worsens scenario; AEB must achieve maximum possible deceleration |

### Acceptance Criteria
- AEB activates within 150 ms of V6's deceleration exceeding 4 m/s²
- Brake light camera pre-warning issued at brake light detection, before radar deceleration threshold
- Stopping distance on dry road: full stop or speed reduction to ≤ 10 km/h from 100 km/h following at 2.5 s gap

---

## Q3: FCW in Platoon with Very Short Time Gap (Cooperative Adaptive Cruise Control)

### Scenario
A CACC (Cooperative ACC) platoon is operating with a 0.5 s time gap between vehicles at 90 km/h. At 0.5 s gap, the inter-vehicle distance is only 12.5 m. Standard FCW TTC threshold (2.5 s) would permanently fire in this platoon. How should FCW be adapted for CACC platooning?

### Expected Behavior
In CACC mode, FCW thresholds must be adjusted:
- Standard FCW TTC threshold (2.5 s) **suppressed or overridden** within the platoon.
- A CACC-specific "intra-platoon" FCW threshold is applied: e.g., alert only if actual TTC drops below 0.8 s (below the designed safe limit).
- FCW is still needed for sudden out-of-ordinary events (vehicle cutting in, V2V comms loss).

### Detailed Explanation
- CACC relies on V2X (V2V) communications for deceleration/acceleration coordination.
- The platoon vehicles share intent data: if V1 reports an emergency brake, all following vehicles react proactively before their own sensors detect V2's deceleration.
- Human FCW is not useful within a CACC platoon — the automation handles response.
- FCW must remain active for: external cut-in vehicles, V2V link failure, non-platoon objects.
- System mode: "CACC platoon mode" — FCW reconfigured with platoon-specific thresholds.
- When a vehicle leaves the platoon (communication drop), FCW immediately reverts to standard thresholds.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| V2V communication lost for 500 ms (network congestion) | CACC falls back to sensor-only ACC; FCW standard thresholds restored immediately |
| Non-platoon vehicle cuts in to platoon at 10 m gap | FCW detects cut-in (no V2V signal from new vehicle); standard FCW threshold applies immediately |
| Platoon vehicle executes emergency stop at 0.5 s gap | AEB activates at sub-100 ms latency (V2X pre-warning if available) |
| Platoon leader exits motorway: platoon splits | Platoon reformat; FCW adapts as gaps temporarily increase |

### Acceptance Criteria
- No intra-platoon FCW nuisance alerts during stable CACC operation at 0.5 s time gap
- FCW standard thresholds restored within 100 ms of V2V link loss
- External cut-in FCW alerts fire with standard thresholds regardless of platoon mode

---

## Q4: BSD with Vehicle Cluster in Adjacent Lane — Indicator Persistence

### Scenario
*(This extends Q41 in the BSD file.)* A 5-vehicle cluster passes the ego vehicle in the adjacent lane, each vehicle entering and exiting the BSD zone in sequence. The inter-vehicle gap is 8 m. At 10 km/h relative speed, each vehicle takes 2.8 s to pass through a 28 m BSD zone. The 8 m gap between vehicles takes 2.9 s to pass. Is this gap long enough to extinguish the BSD indicator?

### Expected Behavior
The 8 m gap takes 2.9 s to traverse. If the BSD persistence timer is set to 3 s (a common value), the indicator remains ON — barely — through the gap. If persistence is 2 s, the indicator will briefly extinguish and re-illuminate (flickering). Persistence should be ≥ 3 s for 10 km/h relative speed scenarios.

### Detailed Explanation
- BSD persistence timer purpose: prevent annoying indicator flicker during realistic inter-vehicle gaps.
- Gap transit time = gap_distance / relative_speed = 8 m / 2.78 m/s = 2.88 s.
- Persistence timer must be calibrated for the worst-case realistic convoy gap speeds:
  - At 5 km/h relative speed: 8 m gap = 5.76 s → need > 5.8 s persistence (too long; may cause missed-clear errors).
  - At 30 km/h relative speed: 8 m gap = 0.96 s → 1 s persistence sufficient.
- Solution: **speed-adaptive persistence timer** — longer persistence at low relative speeds, shorter at high relative speeds.
- Adaptive formula: `persistence_time = min(gap_m / (relative_speed_ms + 0.1), 3.0)` (capped at 3 s).

### Speed-Adaptive Persistence Table

| Relative Speed | 8 m Gap Transit Time | Recommended Persistence |
|----------------|---------------------|------------------------|
| 5 km/h (1.4 m/s) | 5.7 s | 3.0 s (cap; accept brief flicker) |
| 10 km/h (2.8 m/s) | 2.9 s | 3.0 s (just covers) |
| 20 km/h (5.6 m/s) | 1.4 s | 1.5 s |
| 30 km/h (8.3 m/s) | 0.97 s | 1.0 s |
| 50 km/h (13.9 m/s) | 0.58 s | 0.6 s |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cluster at exactly the same speed as ego (0 relative speed) | Cluster permanently occupies BSD zone; indicator permanently ON; no persistence concern |
| Cluster gap is 20 m (loose convoy) | Gap transit at 10 km/h = 7.2 s; persistence timer expires; indicator correctly extinguishes in gap |
| Turn signal activated during gap (indicator briefly OFF) | Even if indicator momentarily off, if auditory logic persists due to pending zone entry, turn-signal-activated warning fires |

### Acceptance Criteria
- BSD indicator persists through inter-vehicle gaps up to 3 s transit time without flickering
- Speed-adaptive persistence implemented; validated at relative speeds 10, 20, 30 km/h with convoys

---

## Q5: LKA Behavior When Flanked by a Vehicle Cluster on Both Sides Simultaneously

### Scenario
The ego vehicle is in the center lane of a 3-lane motorway. A cluster of 3 trucks occupies the right lane alongside the ego vehicle (lateral distance 0.9 m to truck sides). Another cluster of 2 cars occupies the left lane simultaneously. LKA is active. Should LKA offset the ego vehicle away from the trucks?

### Expected Behavior
**Advanced LKA** (with lateral offset based on adjacent object proximity) should apply a gentle left offset to increase clearance from the trucks, BUT:
- The left side is also occupied → the available offset space is limited.
- LKA must calculate whether sufficient space remains within the ego lane to safely offset.
- If no clearance margin is available (both sides occupied tightly), LKA stays at lane center and warns the driver.

### Detailed Explanation
- Lateral offset algorithm steps:
  1. Measure clearance to right cluster: 0.9 m (below comfort threshold of 1.2 m).
  2. Measure clearance to left cluster: 1.1 m (marginally acceptable).
  3. Maximum left offset within own lane: lane_width/2 − ego_width/2 − min_margin = 1.75 m − 1.0 m − 0.3 m = 0.45 m available.
  4. Desired offset: min(discomfort reduction, available space) = min(0.3 m, 0.45 m) = 0.3 m left.
  5. Apply 0.3 m left offset; new right clearance = 1.2 m (comfortable); left clearance = 0.8 m (marginal).
- When both sides are occupied beyond offset capacity: HMI message "Change lanes not recommended."

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Right cluster is a semi-trailer (extra-wide, 2.5 m): truck side very close | Greater discomfort; larger offset desired; may be limited by left lane vehicles |
| Cluster on right changes lane toward ego vehicle (encroaching) | ESA (Emergency Steering Assist) takes over; LKA offset alone insufficient |
| Ego vehicle in leftmost lane: trucks on right, wall on left | Offset toward wall not possible; LKA centers; driver warning |
| Both clusters suddenly decelerate (cluster braking event) | LKA offset irrelevant; FCW/AEB priority |

### Acceptance Criteria
- LKA offset applied within 1 s of adjacent cluster detection below comfort threshold
- Offset correctly limited to available lane space; no LKA correcting toward occupied zone
- HMI advisory issued when both sides occupied with < 1.0 m clearance each

---

## Q6: FCW/AEB when Lead Vehicle Cluster Suddenly Contracts (Accordion Effect)

### Scenario
A 4-vehicle cluster is traveling at 90 km/h with 20 m spacing. An accordion effect occurs: V1 brakes hard (7 m/s²), causing V2–V4 to bunch up rapidly. The cluster contracts from 60 m total length to 20 m within 3 s. The ego vehicle following V4 at 90 km/h suddenly has far less clear road ahead.

### Expected Behavior
FCW should detect V4's rapid deceleration and issue a warning. AEB activates if TTC drops below threshold. The challenge is: the cluster contraction itself causes a sudden and unexpected TTC reduction.

### Detailed Explanation
- Accordion effect: each vehicle brakes progressively harder to compensate for reaction lag.
- V4's deceleration may be sharper than V1's (6–8 m/s² by the time the reaction reaches V4).
- At 90 km/h following V4 at 45 m (2.0 s gap), if V4 brakes at 8 m/s²: TTC drops to 1.5 s within 0.6 s.
- FCW must warn immediately; AEB may have less than 1 s to intervene.
- Camera brake light detection is critical here: V4's brake lights give < 200 ms pre-warning.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cluster contraction causes a collision within the cluster (V3 hits V2) | Debris in road; AEB and FCW now dealing with stationary cluster wreckage |
| V4 swerves to avoid collision within cluster: sudden lateral maneuver | AEB may release; ESA activates; complex simultaneous activation |
| Ego following distance was set to 1.0 s (aggressive user setting) | Very short time to react; FCW fires much sooner; may be already inside AEB threshold |

### Acceptance Criteria
- FCW warning within 300 ms of V4 deceleration rate exceeding 4 m/s²
- AEB activates if TTC to V4 < 1.5 s with no driver braking action

---

## Q7: ACC in Dense Fog — Vehicle Cluster Invisible to Camera, Radar Only

### Scenario
Dense fog (visibility 30 m) on a motorway where a loose vehicle cluster of 4 vehicles is traveling at 60 km/h (fog speed limit). The ego vehicle has ACC active with camera + radar fusion. Camera visibility is near zero. Radar detects the cluster vehicles but with reduced confidence.

### Expected Behavior
ACC should operate in radar-only mode and maintain safe following distance. Camera lane assignment is unavailable — ACC must use radar track continuity and road curvature to infer in-lane status.

### Detailed Explanation
- Radar operating range in fog: nominally unaffected (77 GHz penetrates fog/water droplets).
- Camera: near-total loss in dense fog (visual range < 30 m; lane markings invisible).
- ACC fallback to radar-only: reduced confidence in lane assignment.
- Fog-mode ACC: increase following time gap from 2.0 s to 3.0 s automatically (conservative gap).
- Lane assignment without camera: use radar bearing continuity (target remains at near-zero lateral offset over time) as a proxy for in-lane status.
- HMI: "ACC — reduced visibility mode" displayed.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| A vehicle from the cluster changes lane in fog (no camera confirmation) | Radar detects lateral movement; lane assignment uncertain; ACC holds last valid target |
| New vehicle enters from a fog-obscured junction | Sudden radar contact; confirm in-lane before ACC target selection |
| Fog suddenly clears: camera resumes | Camera reacquires lane markings; fusion weights update; ACC returns to standard mode |
| ACC set speed (80 km/h) exceeds fog speed limit (60 km/h) | ISA must enforce fog speed limit if variable message sign is detected or driver manually sets 60 km/h |

### Acceptance Criteria
- ACC remains functional in radar-only mode with camera confidence < 20%
- Fog-mode following gap ≥ 3.0 s (auto-increase from driver set gap when in fog mode)
- HMI fog degradation indicator displayed within 2 s of camera confidence drop below 20%

---

## Q8: V2X-Enabled Cluster Warning — Cooperative Perception

### Scenario
A cluster of 5 vehicles ahead is equipped with V2V (Vehicle-to-Vehicle, DSRC/C-V2X). The front vehicle V1 detects a road hazard and broadcasts an emergency brake event message. The ego vehicle (1.2 km behind the cluster, cannot see the cluster yet) receives the V2X hazard message. How should ADAS respond?

### Expected Behavior
The ego vehicle should:
1. Display a "Hazard ahead" HMI warning immediately on receiving the V2X message.
2. ACC reduces set speed proactively (pre-conditioning).
3. AEB/FCW are pre-armed to lower their TTC threshold for faster response when the cluster comes into sensor range.

### Detailed Explanation
- V2X message types: ETSI ITS (EU standard) — DENM (Decentralized Environmental Notification Message) for hazards.
- Message latency: C-V2X (PC5) communication latency < 20 ms.
- Range: C-V2X up to 500 m–1 km direct line-of-sight; DSRC up to 300 m.
- At 1.2 km distance: V2X range exceeded for direct C2C; but RSU (roadside unit) relay can extend range.
- Pre-arm AEB: lower AEB activation TTC threshold from 1.5 s to 2.0 s for the next 30 s.
- Pre-arm means: AEB will fire 500 ms earlier than normal when a target is detected.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| V2X message is malformed or unauthenticated | Reject message; no hazard pre-arm; rely on onboard sensors only |
| V2X false alarm (triggered by sensor glitch in lead vehicle) | ADAS pre-arm is a conservative action (earlier warning); no false AEB from V2X alone |
| V2X message describes a hazard in a different lane | Lane ID included in DENM; ADAS filters for ego lane relevant messages |
| No V2X infrastructure: cluster not equipped | Ego relies solely on onboard sensors; standard FCW/AEB thresholds |

### Acceptance Criteria
- V2X hazard message displayed on HMI within 200 ms of authenticated receipt
- AEB pre-arm active within 500 ms of hazard message for ego lane ID match
- No false AEB or ACC interventions from V2X message alone (always requires sensor confirmation)

---

## Q9: ADAS Behavior When Ego Vehicle Is Inside a Cluster (Surrounded)

### Scenario
The ego vehicle is in the center of a cluster: one vehicle 20 m ahead (V_front), one 15 m behind (V_rear), one alongside on the right (BSD occupied), and one alongside on the left (BSD occupied). All vehicles are traveling at 100 km/h. This is typical dense traffic. What does the complete ADAS picture look like?

### Expected Behavior
All ADAS functions are simultaneously active and must coordinate without conflict:
- **ACC**: following V_front at set gap.
- **BSD left + right**: both illuminated.
- **LKA**: active but no lateral offset available (both sides occupied).
- **FCW**: monitoring V_front.
- **Rear collision warning** (if equipped): monitoring V_rear.

### Detailed Explanation
- This is one of the highest sensor load scenarios for an ADAS system.
- All ≥6 radar tracks active simultaneously; all camera lanes occupied; surround view all busy.
- ECU load test: this scenario must be part of worst-case CPU load validation.
- Actuator conflicts: LKA (steering), ACC (longitudinal) must not conflict.
- Prioritization: if V_front brakes hard → FCW/AEB takes precedence over LKA corrections.
- Inter-system messaging latency: all ADAS ECUs must respond independently (one failure should not cascade).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Simultaneous BSD escalation + FCW warning | Both fire independently; driver receives both alerts simultaneously; HMI must be legible |
| V_front brakes AND right-side vehicle cuts into lane | Compound event: AEB fires for V_front; BSD escalation provides contextual warning |
| One ADAS ECU overloads and slows: latency spike | ECU watchdog detects latency; safety-critical functions (AEB) given OS priority; LKA may be degraded |

### Acceptance Criteria
- All simultaneous ADAS functions active without inter-function interference in cluster scenario
- AEB E2E latency < 500 ms even in 6-target simultaneous tracking scenario (CPU worst case)
- HMI displays all concurrent ADAS warnings without overlapping or masking safety-critical alerts

---

## Q10: Emergency Vehicle Passing Through a Vehicle Cluster

### Scenario
An ambulance with lights and sirens active needs to pass through a cluster of 6 vehicles on a 2-lane road. The ambulance is coming from behind and must overtake the cluster. The ego vehicle is 3rd in the cluster. How should ADAS assist the driver in making way for the emergency vehicle?

### Expected Behavior
- **BSD**: detects the ambulance approaching rapidly from behind in the adjacent lane.
- **ECW (Emergency Corridor Warning — EU mandate)**: if applicable, ADAS guides the driver to move left to create an emergency corridor.
- **ACC**: may reduce speed to allow a gap to form ahead of the ego vehicle for lane change.

### Detailed Explanation
- EU Emergency Corridor: by law (several EU countries), vehicles in lane 1 move left; lane 2 move right; creating a central corridor.
- ADAS Emergency Corridor Assist: detects siren via microphone + visual flashing lights via camera → proposes a target lane to the driver.
- BSD + LKA: after driver initiates lane change, LKA assists the steering toward the emergency corridor position.
- Siren detection: audio classification (CNN on microphone signal); detects 300–3,000 Hz siren frequency pattern.
- Flash detection: camera classifies blue/red high-frequency light pulses.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Ambulance approach detected but adjacent lane occupied | ADAS delays corridor guidance until adjacent lane is confirmed clear |
| Emergency vehicle is directly behind ego (rear-end risk during deceleration) | AEB RCW (Rear Collision Warning) + forward gap management |
| False siren detection from road construction alarm | Audio classification must discriminate vehicle sirens from industrial alarms |
| Multiple emergency vehicles passing simultaneously | Corridor formation still required; ADAS tracks all EVs |

### Acceptance Criteria
- Siren + flashing light detection from ≥ 100 m behind the ego vehicle
- Emergency corridor guidance displayed on HMI within 3 s of EV detection
- ACC reduces speed to create a 5 m gap ahead for lane change into corridor

---

## Q11: Cluster Entry and Exit — ACC Gap Management at Motorway Merge

### Scenario
The ego vehicle is merging from an on-ramp onto a motorway where a 6-vehicle cluster is traveling at 110 km/h in lane 1. There is a 25 m gap between vehicles V3 and V4 in the cluster. ACC must identify this as a viable merge gap and adjust speed to slot in.

### Expected Behavior
ACC does not automatically steer into gaps (that requires L2+ pilot). However, ACC can assist by: adjusting speed to align with the merge gap timing and providing the driver with a gap indicator ("safe gap ahead").

### Detailed Explanation
- ACC merge assist: if a forward cluster gap is detected, ACC suggests or assists matching speed to the target gap speed.
- Merge gap viability: 25 m gap at 110 km/h → 25/30.6 = 0.82 s gap — very tight; minimum recommended is 1.5 s gap.
- HMI: "Gap available — adjust speed to merge safely."
- At L2+: automatic speed adjustment to enter the gap + lane centering if in LCA mode.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cluster closes the gap as ego accelerates to merge | ACC detects gap shrinking; cancels merge assist |
| Multiple gaps available: driver selects preferred one | HMI shows multiple gap options; driver selects |
| On-ramp ends (no more merge space): ego vehicle must stop | ACC reduces to stop at ramp end; driver takes control |

### Acceptance Criteria
- Merge gap detected and displayed when cluster gap ≥ 1.5 s time gap at cluster speed
- ACC speed adjustment ≤ 2 m/s² for merge gap alignment

---

## Q12: Post-Cluster Clearance — Resuming Normal ACC After Passing Through Dense Traffic

### Scenario
After 8 minutes of stop-and-go travel through a dense vehicle cluster (queue), the queue clears suddenly. The ego vehicle has ACC set at 120 km/h. What is the correct ACC behavior on cluster exit?

### Expected Behavior
ACC should accelerate back to set speed smoothly (max 1.5–2.0 m/s²) when no target is detected after cluster exit. The transition from queue mode (0–30 km/h) to highway mode (120 km/h) should be seamless.

### Detailed Explanation
- ACC mode transition: stop-and-go / low-speed follow → free-speed highway cruise.
- The driver must confirm resumption if the vehicle was stopped for > 3 s (per standard ACC policy).
- Since the ego was in motion throughout (slow crawl), auto-resume at free speed is allowed.
- Speed increase ramp: 1.5 m/s² is Euro NCAP recommended max comfort acceleration for ACC.
- ISA check: ACC must not accelerate beyond the road's current speed limit (ISA integration).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cluster clears but immediately followed by road works (speed limit 60 km/h) | ACC caps at 60 km/h; does not accelerate to set speed of 120 km/h |
| Cluster exit into a curve | ACC reduces speed for curvature in navigation-integrated ACC |
| Driver was impatient and set ACC to 130 km/h in 120 km/h zone | ISA caps at 120 km/h if ISA-ACC integrated |

### Acceptance Criteria
- ACC resumes from cluster queue to free-speed without driver input (continuous motion scenario)
- Acceleration ramp ≤ 2.0 m/s² on cluster exit
- Speed limited to current road speed limit (ISA integration)

---

## Q13: Cluster Detection in Roundabout — ADAS Suppression

### Scenario
The ego vehicle enters a busy roundabout where a cluster of 4 vehicles is circulating ahead. ACC attempts to follow the cluster but they are on a circular arc path. LKA detects no straight-ahead lane markings. What is the correct behavior?

### Expected Behavior
- **ACC**: deactivates or enters manual standby mode (roundabout is outside ACC ODD on most systems).
- **LKA**: deactivates on radius < 200 m (roundabout radius typically 10–50 m).
- **AEB-C/P**: remains active for safety.
- **USS/Surround view**: takes over guidance for close-proximity maneuvers.

### Detailed Explanation
- Roundabouts are explicitly excluded from ACC and LKA ODD.
- The driver must take full control in roundabouts.
- AEB and FCW remain active: stationary vehicle, pedestrian, or cyclist in exit lane are valid threats.
- Map-based ODD detection: if roundabout is in HD/standard map, ACC auto-deactivates on entry.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Roundabout exit was lane-marked (unusual large roundabout) | LKA re-engages if detected lane is straight enough (radius > 200 m) |
| ADAS deactivated on roundabout entry; driver forgets to re-engage ACC | Reminder prompt after roundabout: "ACC available — press enable" |

### Acceptance Criteria
- ACC and LKA auto-deactivate on roundabout entry (map or curvature detection)
- AEB/FCW remain active throughout roundabout traversal

---

## Q14: Cluster Vulnerable Road Users (Mixed Vehicle + Cyclist + Pedestrian)

### Scenario
At a festival exit, a mixed cluster exits the venue: 3 cars, 10 cyclists, and 20 pedestrians simultaneously moving toward the road. The ADAS multi-class detector must classify and prioritize all objects correctly.

### Expected Behavior
ADAS must:
1. Classify each object correctly: car vs. cyclist vs. pedestrian.
2. Prioritize pedestrian and cyclist (higher vulnerability) for AEB-P and AEB-C activation thresholds.
3. Provide the driver with a clear HMI overview (surround view with color-coded  VRU icons).

### Detailed Explanation
- Multi-class object detection DNN: simultaneously classifies all object types in the scene.
- Priority scheme for AEB activation:
  1. **Pedestrian** — highest: AEB activates at TTC < 2.0 s.
  2. **Cyclist** — high: AEB activates at TTC < 1.8 s.
  3. **Vehicle** — standard: AEB activates at TTC < 1.5 s.
- Cluster density: with 33 objects, the object tracker must maintain 33 simultaneous tracks.
- DNN inference time must not increase proportionally with object count — batch processing required.
- Rare scenario: high object count may exceed tracker capacity; maximum track count must be specified and tested.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Tracker capacity exceeded (> 30 objects): nearest objects prioritized | Must NOT drop nearest/most dangerous objects for far objects |
| Mixed cluster at night | NIR + thermal camera supplement to maintain classification in low light |
| Objects moving in unpredictable directions (festival crowd) | Trajectory prediction must handle multi-modal (non-road) motion |

### Acceptance Criteria
- Minimum 20 simultaneous object tracks maintained with full classification at 10 Hz
- Pedestrian/cyclist TTC thresholds correctly applied over vehicle thresholds in mixed cluster
- DNN inference time: ≤ 50 ms per frame regardless of object count (up to 30 objects)

---

## Q15: ADAS Data Logging During Cluster Scenarios — Edge Case Capture Strategy

### Scenario
During validation on a public road, the ego vehicle encounters an unexpected vehicle cluster event (sudden queue at motorway end). No ADAS activation occurred. However, the data science team wants to capture this cluster scenario for offline analysis and DNN retraining. What is the data capture strategy?

### Expected Behavior
An **intelligent data capture trigger** should record the cluster scenario even when no ADAS activation occurred, using a pre/post-event ring buffer.

### Detailed Explanation
- Trigger conditions for passive data capture (beyond ADAS activation):
  - Object count in scene > 5 simultaneously.
  - Sudden TTC drop > 50% within 1 s.
  - Multiple objects within 30 m simultaneously.
  - Unusual object class detected (animal, oversized vehicle, crowd).
- Ring buffer: continuous recording of last 30 s; on trigger, the 30 s pre-event + 10 s post-event is saved.
- Data stored: radar raw FIFO, camera raw frames (compressed), CAN log, GPS, ADAS object list.
- Upload: via OTA data pipeline when vehicle next connects to Wi-Fi.
- Privacy: GPS data anonymized; no driver-identifiable data without consent.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Storage full during extended cluster scenario | Prioritize most recent data; overwrite oldest non-triggered data |
| Cluster scenario triggers false DTC (sensor spike) | Ensure data capture trigger does not interfere with DTC logic |
| Data capture trigger fires too frequently on busy motorway | Rate-limit trigger: max 3 captures per 10 km |

### Acceptance Criteria
- Cluster scenario data captured (pre-event 30 s buffer) for ≥ 95% of qualifying trigger events
- Data capture does not increase ADAS ECU CPU load by > 5%
- Anonymized data pipeline compliant with GDPR (ISO/IEC 27701)
