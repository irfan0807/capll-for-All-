# Sensor Fusion & System Integration — Scenario-Based Questions (Q91–Q100)

---

## Q91: Sensor Fusion Architecture — Kalman Filter Track Divergence

### Scenario
The camera-based object tracker reports a pedestrian at range 35 m, moving at 1.2 m/s laterally. The radar tracker places the same target at 32 m, 1.5 m/s laterally. An Extended Kalman Filter fuses both inputs. The fused estimate diverges significantly from both inputs after 3 s. What is wrong?

### Expected Behavior
The EKF fused estimate should converge between sensor inputs due to model weighting. Divergence indicates:
1. Incorrect process noise model (Q matrix too low, not allowing state updates).
2. Incorrect sensor measurement noise model (R matrix — sensor trust too high for one sensor).
3. Data association failure (tracking different objects).

### Detailed Explanation
- EKF state vector: [x, y, vx, vy] for each tracked object.
- Prediction step: x_{k|k-1} = F * x_{k-1} + noise, where F is the state transition matrix.
- Update step: K = P * H^T * (H * P * H^T + R)^{-1} (Kalman Gain).
- If R (radar noise) is set very low, the filter over-trusts radar → camera is ignored → diverges from reality if radar has bias.
- Data association: if camera and radar are tracking different objects (e.g., partially occluded), the fused track is a meaningless merge of two different objects.
- Gating test: Mahalanobis distance check before association. Objects > 3σ apart should NOT be fused.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| One sensor updates asynchronously (different cycle times: camera 30 Hz, radar 20 Hz) | Time-stamped asynchronous EKF update (predict to current time, then update) |
| Target disappears from one sensor (occlusion) | Use coasting: propagate track without measurement update; increase uncertainty |
| Non-linear motion (pedestrian turning suddenly) | Unscented KF or IMM (Interacting Multiple Model) for non-linear motion |
| Sensor biases different after temperature change | Online bias estimation using known static targets for compensation |
| Ghost track (false detection from one sensor) | Mahalanobis gating + track confirmation (N/M logic: confirm after N detections in M cycles) |

### Validation Approach
- SIL/HIL: inject known ground-truth trajectories; compare fused track error vs. ground truth.
- RMSE (Root Mean Square Error) analysis per track

### Acceptance Criteria
- Fused track RMSE ≤ min(individual sensor RMSE) in steady-state following
- Track divergence detected by covariance inflation monitor; re-initialization triggered

---

## Q92: ADAS Feature Arbitration — AEB vs. ESC Conflict

### Scenario
The vehicle is on an icy road and AEB activates at 60 km/h (applying 9 m/s² deceleration). The ESC (Electronic Stability Control) simultaneously detects wheel lockup and reduces brake pressure to prevent skid. These two systems are in conflict. Who wins?

### Expected Behavior
ESC and AEB must NOT fight each other. The correct architecture: AEB requests deceleration; the brake controller (integrating ESC) arbitrates the actual brake pressure applied. ESC modulates the requested pressure to prevent lockup — AEB's request is respected as a target, but ESC prevents a physically unsafe realization.

### Detailed Explanation
- The brake system hierarchy:
  - AEB → requests deceleration target (9 m/s²) to the Brake ECU/ESC.
  - ESC → manages actual brake pressure distribution per wheel to prevent lockup/instability.
  - ABS → modulates pressure at each wheel to maintain slip ratio in optimal grip range.
- The "conflict" is by design: ESC will never allow AEB to cause wheel lockup because unsafe wheel lockup reduces actual deceleration.
- On ice (μ = 0.1–0.2), maximum achievable deceleration is ~1.0–2.0 m/s² regardless of AEB's 9 m/s² request.
- AEB does not "fight" ESC — it just requests the maximum desired deceleration; the brake system delivers what physics allows.
- Net result: shorter stopping distance than no AEB, even on ice.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Black ice (μ < 0.1): almost no grip at all | Only ~0.5–1.0 m/s² achievable; AEB activates still (better than nothing) |
| AEB requests 9 m/s² but ESC limits to 3 m/s² on ice | ADAS arbitration correctly delegates to ESC; no system conflict |
| AEB active AND vehicle in sideways drift (ESC active) | ESC corrects yaw stability; AEB rear channel modulated; complex multi-axis arbitration |
| AEB false positive on ice: unnecessary hard braking causes skid | False positive risk increases on ice; confidence threshold for AEB may be raised in low-μ mode |

### Acceptance Criteria
- AEB + ESC joint activation: no wheel lockup, stable vehicle trajectory maintained
- AEB deceleration request never bypasses ABS/ESC controller
- On low-μ surface: AEB still reduces pre-impact speed by ≥ 30% vs. no AEB baseline

---

## Q93: Sensor Fusion with GPS/GNSS — Map-Matched Object Positioning

### Scenario
The ego vehicle's GPS reports its position with ±5 m accuracy (standard GPS, no RTK). The radar detected a stationary vehicle at 50 m ahead. The ADAS system attempts to use map data to classify if the vehicle is in a tunnel (permanent obstacle) or on-road. With ±5 m GPS error, can map-based classification be trusted?

### Expected Behavior
With ±5 m GPS error, map-based classification is unreliable for confirming exact lane-level object position. The system should use sensor-detected position as primary and map data as soft context only.

### Detailed Explanation
- Standard GPS accuracy: ±3–5 m (95% circular error probability — CEP).
- For lane-level operations (lane width ~3.5 m), ±5 m GPS is insufficient.
- ADAS requiring lane-level accuracy needs:
  1. RTK-GNSS (±2 cm): highest accuracy but expensive, requires reference station.
  2. Dead reckoning + wheel speed: short-term accuracy; drifts over time.
  3. Camera lane matching: localizes vehicle within the lane using lane markings → lane-level accuracy.
- HD map + camera fusion provides sufficient accuracy for lane classification without RTK.
- The stationary vehicle classification should rely on radar + camera, NOT GPS-map match.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Tunnel portal (GPS signal lost inside tunnel) | Dead reckoning + map matching + odometry for position estimation in tunnel |
| GPS multipath in urban canyon | Accuracy degrades to ±20 m; disable GPS-dependent ADAS functions in urban canyons |
| RTK correction link lost (SIM card no data) | Fall back to standard GPS + lane detection accuracy |
| Map data shift: road newly built, map outdated | Camera lane detection overrides outdated map; lane-level position via camera |

### Acceptance Criteria
- Lane-level localization achieved via camera marking matching with ≤ 0.3 m accuracy in mapped areas
- GPS-based object classification not used alone when GPS accuracy ≥ 3 m

---

## Q94: CAN Bus Signal Integrity — Sensor Data Corruption in ADAS

### Scenario
A single-event upset (EMC radiation in an industrial zone) corrupts a radar object speed signal on the CAN bus. The radar reports a leading vehicle speed as 300 km/h (corrupt value) instead of 80 km/h. The ACC controller performs an aggressive deceleration based on the corrupt data.

### Expected Behavior
ADAS must include signal plausibility checks:
- Radar reported object speed > realistic vehicle speed (e.g., > 250 km/h) → REJECT as invalid.
- CRC error on the CAN message → REJECT and use last valid value.
- Consecutive invalid readings → set DTC; deactivate ACC.

### Detailed Explanation
- CAN bus message protection: CRC-8 or CRC-15 provides single-bit error detection.
- Signal plausibility gates: each ADAS ECU applies sanity checks on incoming signals.
  - Speed: absolute value check (physical maximum ≤ 300 km/h for target vehicle class).
  - Acceleration: ≤ 15 m/s² for realistic vehicle.
  - Range: 0–250 m for mid-range radar.
- AUTOSAR COM layer provides signal timeout monitoring (missing message detection).
- ISO 26262: E2E protection (End-to-End Protocol) for safety-critical CAN signals.
- E2E wrappers add sequence counter + CRC per message — verified at the receiver.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Legitimate emergency braking: object goes from 80 to 0 km/h in 2 s | Plausibility check: 40 m/s² deceleration — exceeds normal; accept as emergency stop |
| EMC event corrupts multiple consecutive messages | N consecutive invalid → function deactivated; DTC stored |
| CAN bus overload: messages delayed > timeout | Timeout fault; signal treated as invalid |
| Sensor output gradually drifts (subtle corruption) | Harder to detect; outlier detection using track history plausibility |

### Acceptance Criteria
- Implausible signal values reject rate: 100% for values exceeding physical bounds
- E2E CRC error rejection rate: 100% (no corrupt messages processed as valid)
- DTC stored and ADAS deactivated after 3 consecutive invalid signal frames

---

## Q95: Over-the-Air (OTA) Update — ADAS Feature Regression Test

### Scenario
A critical OTA update for the AEB software is released. After the OTA update is applied overnight, the customer starts the vehicle and drives normally. How does the system validate that AEB is still functional post-OTA, and what automated regression test is run?

### Expected Behavior
Post-OTA validation sequence:
1. Software version hash verification (compare ECU flash CRC vs. released binary hash).
2. Self-test: radar initialization, camera initialization, AEB parameter check.
3. Short functional readiness test: ECU performs an internal plausibility test sequence.
4. HMI confirms "ADAS systems ready" on first drive if all checks pass.
5. Backend analytics monitor fleet behavior over next 1,000 km for anomalies.

### Detailed Explanation
- OTA process: SOTA (Software Over-The-Air) downloads to a secondary memory partition; validates before flashing.
- Safe OTA: if validation fails, rollback to previous version automatically.
- Post-OTA self-test: radar CRC check, camera lens check, AEB parameter read-back (UDS 0x22).
- Fleet monitoring: the OEM backend compares AEB activation rates before/after update across the fleet.
- Regression testing in cloud/SIL: before OTA is released to customer, full regression test suite is executed on a simulation environment mirror.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| OTA interrupted mid-flash (power loss) | Secondary partition untouched; rollback to primary |
| OTA applies wrong variant (BMW 3-series calibration applied to BMW 5-series) | Variant mismatch check via ECU part number vs. VIN → reject OTA before flash |
| Post-OTA: AEB calibration parameter corrupted by bit flip | ECU startup CRC check on NvM parameters fails; restore to default; customer notified |
| OTA modifies AEB TTC threshold unintentionally | Regression test in SIL catches this before fleet deployment |

### Acceptance Criteria
- OTA rollback success rate: 100% on power interruption during flash
- Post-OTA AEB self-test: pass within 10 s of ignition
- Fleet anomaly detection: AEB false positive rate change > 20% triggers automatic triage

---

## Q96: Multi-Sensor Object Fusion — LiDAR + Camera + Radar

### Scenario
A level 2+ vehicle is equipped with 1x LiDAR, 6x cameras, and 5x radars. A cyclist is at 40 m. The camera classifies it as "person." The LiDAR provides a 3D point cloud showing a cluster 0.6 m wide and 1.7 m tall. The radar reports a slow-moving target at 40 m. Describe the optimal fusion strategy.

### Expected Behavior
The fusion strategy should combine:
- **LiDAR**: 3D geometry (size, shape, position) → most reliable for size estimation
- **Camera**: semantic classification (cyclist/pedestrian) → highest classification accuracy
- **Radar**: velocity vector and range → most reliable for speed and range

### Detailed Explanation
- Deep fusion architecture: raw sensor data fused in a common environment model.
- Object state vector: [x, y, z, vx, vy, vz, class, confidence].
- LiDAR point cloud segmentation: cluster the cyclist point cloud → bounding box [0.6 m × 0.6 m × 1.7 m].
- Camera semantic output: "cyclist" at bounding box (u, v, w, h) in image plane.
- Projection: LiDAR 3D bounding box projected into camera image space → associated with camera bounding box.
- Radar association: nearest radar track within Mahalanobis gate to LiDAR/camera fused object.
- Final fused object: class = cyclist | confidence = 0.92 | position = [40.2, 0.1, 0.0] m | velocity = [0, 1.3, 0] m/s.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| LiDAR blocked by rain (returns degraded) | Camera + radar maintain tracking; LiDAR weight reduced |
| Camera occluded; LiDAR detects cyclist | Geometry from LiDAR; classification uncertain; conservative class = "VRU" |
| All three sensors see different objects (cross-miss-association) | Data association algorithm uses temporal consistency, object model, spatial prior |
| LiDAR scan rate 10 Hz vs. camera 30 Hz | Interpolate LiDAR to camera frame time; time-stamped fusion |

### Acceptance Criteria
- Fused object position error ≤ 0.3 m RMSE vs. RTK ground truth at 40 m range
- Classification accuracy ≥ 98% for cyclist vs. pedestrian vs. vehicle at 40 m

---

## Q97: System Integration Test — Hardware-in-Loop (HIL) for ADAS

### Scenario
The HIL test bench for ADAS validation needs to simulate a pedestrian crossing scenario for AEB-P. Describe the HIL setup requirements and the test execution flow.

### Expected Behavior
A complete HIL test for ADAS involves:
1. ADAS ECU connected to HIL rack.
2. Sensor Simulation Unit generating synthetic radar/camera outputs.
3. Vehicle dynamics model running in real-time.
4. CAN/Ethernet simulation providing bus traffic.
5. Test automation controlling the scenario and measuring outcomes.

### HIL Architecture

```
[Test PC (CANoe/vTESTstudio)]
        |
        v
[CAN/Ethernet HIL Bus] <---> [ADAS ECU Under Test]
        |
[dSPACE / NI VeriStand HIL Platform]
        |
[Radar Model] [Camera Model] [USS Model]
        |
[Vehicle Dynamics (CarMaker/IPG)]
        |
[Scenario Engine (pedestrian trajectory injection)]
```

### Test Execution Flow
1. Scenario loaded: pedestrian crossing at T+5 s.
2. HIL injects sensor data to ADAS ECU via CAN/Ethernet.
3. ADAS ECU processes data, outputs AEB command.
4. HIL measures AEB command timing + brake pressure request.
5. Vehicle dynamics model updates vehicle speed.
6. Test automation compares results to acceptance criteria.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| HIL simulation latency > real-world latency | Validate that HIL latency does not mask real ADAS latency issues |
| Sensor model fidelity insufficient (simplified radar model) | Validate with real sensor data replay alongside HIL simulation |
| Test automation timeout: ECU hangs | ECU watchdog triggers; test framework logs the hang; DUT power cycled |
| CAN bus overload in HIL (test script flood) | Throttle test script; ensure ADAS message priority maintained |

### Acceptance Criteria
- HIL test execution rate: > 500 scenarios/day (automated)
- HIL correlation with track test results: ≥ 95% pass/fail agreement
- All acceptance criteria from track testing replicated in HIL with ≤ 5% metric deviation

---

## Q98: ADAS System Cybersecurity — Sensor Data Spoofing Attack

### Scenario
A security researcher demonstrates they can spoof GPS and radar signals to inject a phantom vehicle ahead of the ego vehicle, causing ACC to decelerate. How should ADAS cope with sensor spoofing?

### Expected Behavior
ADAS must implement cyber-resilience measures:
1. **Sensor plausibility cross-check**: GPS phantom vehicle must also appear in radar AND camera.
2. **Anomaly detection**: sudden appearance of a vehicle with implausible dynamics (zero history) flagged.
3. **Signed sensor data**: future radar/camera systems will use cryptographic signing of sensor outputs (ISO/SAE 21434).

### Detailed Explanation
- GPS spoofing: attacker broadcasts a stronger GPS signal overriding legitimate signal.
- Radar spoofing: attacker broadcasts at radar frequency with false object range/velocity encoding.
- Camera spoofing: adversarial patches or projectors can fool camera DNN classifiers.
- Multi-sensor fusion defense: if a spoofed object appears in GPS only (not radar + camera), it is rejected.
- Track history validation: a real vehicle has a multi-frame track history; a spoofed phantom appears suddenly (track age = 0 cycles).
- ECU comms security: AUTOSAR SecOC (Secure Onboard Communication) provides message authentication for safety-critical signals.
- ISO/SAE 21434: cybersecurity by design; threat modeling (TARA) for sensor inputs.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Sophisticated attacker spoofs all three sensors simultaneously | Extremely difficult in practice; physical constraints make simultaneous spoofing challenging |
| Legitimate emergency vehicle appearing suddenly (valid "sudden appearance") | Track validation uses probability model; police car in an emergency stop is valid |
| Attacker replays previously captured sensor data | Timestamp + counter validation; replay attacks detected by sequence gaps |

### Acceptance Criteria
- Single-sensor phantom object (not confirmed by 2+ sensors) rejected as invalid target
- Zero ACC/AEB activations from single-sensor spoofed objects in penetration testing

---

## Q99: ADAS Functional Safety ASIL Decomposition — AEB Example

### Scenario
The AEB function has been assigned ASIL-B at system level. The architecture uses a camera ECU and a radar ECU feeding into a central ADAS fusion ECU. How is ASIL decomposed across this architecture?

### Expected Behavior
ASIL decomposition allows the system-level ASIL-B to be split into two independent paths, each of which can be ASIL-A or even QM, provided the independence requirements are met.

### Detailed Explanation
- ISO 26262 ASIL decomposition: ASIL-B = ASIL-A + ASIL-A (if full independence between paths).
- Path 1 (Camera): camera detects obstacle → AEB activation request → ASIL-A for this path.
- Path 2 (Radar): radar detects obstacle → AEB activation request → ASIL-A for this path.
- Independence: the two paths must have no common cause failures (different hardware, software, tools).
- The fusion ECU combining both: ASIL-B (safety manager function).
- Common cause prevention: separate power supplies, separate CAN buses, independent software development teams.
- Hardware safety requirement: each sensor ECU meets SPFM (Single Point Fault Metric) for ASIL-A.

### ASIL Assignment Table

| Component | ASIL | Rationale |
|-----------|------|-----------|
| Radar ECU | ASIL-A | Decomposed from ASIL-B (one of two redundant paths) |
| Camera ECU | ASIL-A | Decomposed from ASIL-B (one of two redundant paths) |
| Fusion ECU (ADAS Domain Controller) | ASIL-B | System-level safety manager |
| AEB Brake Actuator Command | ASIL-B | Direct actuation; no redundant path at actuator level |
| HMI Warning Output | ASIL-A | Warning only (no actuation) |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| OEM uses one ECU for both camera and radar processing | Decomposition independence compromised; must maintain ASIL-B for the single ECU |
| Shared power supply for both sensor ECUs | Common cause failure → ASIL decomposition not valid; redesign required |
| Common software library used in both paths | If the library has an error, both paths fail → not independent; library must be independently verified |

### Acceptance Criteria
- ASIL decomposition documented in Safety Architecture (SA) as per ISO 26262 Part 4
- Independence of paths confirmed via CCF (Common Cause Failure) analysis
- Each component meets its assigned ASIL hardware safety metrics

---

## Q100: End-to-End ADAS System Validation Strategy — Release Gate Criteria

### Scenario
The ADAS software for a new vehicle is about to be released for production. The validation manager asks: "What is the complete release gate criterion?" Describe the comprehensive validation strategy from SIL to field validation.

### Expected Behavior
A complete ADAS release validation strategy covers:

### Validation V-Cycle Levels

| Level | Activity | Tools | Pass Criteria |
|-------|----------|-------|---------------|
| Unit Test | Function-level code testing | pytest, gtest | 100% coverage of safety requirements |
| SIL | Software-in-Loop simulation | CarMaker, CARLA, MATLAB/Simulink | All functional requirements met in simulation |
| HIL | HW ECU + sensor simulation | dSPACE, Vector HIL | Timing, safety, and fault injection passing |
| Integration Test | ECU-to-ECU communication test | CANoe, CANalyzer | All CAN/Ethernet signals validated |
| Closed-Track Test | Physical proving ground scenarios | Target vehicles, soft targets | Euro NCAP scenarios pass ≥ OEM threshold |
| Open Road Test | Defined test routes | Instrumented fleet vehicles | False positive / false negative rates within spec |
| Field Validation | Early customer fleet | Data logging backend | No critical safety events; anomaly monitoring |

### Quantitative Release Criteria

| Metric | Target |
|--------|--------|
| AEB false positive rate | < 0.5 per 10,000 km |
| AEB miss rate (confirmed scenarios) | < 1% |
| FCW false positive rate | < 1 per 1,000 km |
| LDW false positive rate | < 0.3 per 100 km |
| ACC target selection accuracy | > 99.9% |
| DMS drowsiness detection accuracy | > 95% |
| TSR recognition accuracy | > 97% (standard signs) |
| System E2E latency (P99) | < 500 ms (all ADAS features) |
| DTC coverage | 100% of specified failure modes |
| Requirements coverage | 100% of functional safety requirements traced to test |

### Edge Cases in Validation Planning
| Challenge | Mitigation |
|-----------|------------|
| Rare scenario coverage (< 1 occurrence per 1M km) | Simulation-based rare event injection |
| Multi-country regulatory validation (EU, US, China) | Market-specific sign databases + NCAP protocols per region |
| Weather diversity (snow, fog, rain) | Controlled environmental chamber + field testing in relevant climates |
| Long-term performance validation (5-year vehicle life) | Accelerated aging test + sensor degradation simulation |
| Edge case discovery during field operation | Continuous data collection pipelines + VSC (Vehicle Safety Commissioning) |

### Release Gate
- All unit, SIL, HIL, integration tests: 100% pass (no open safety-critical defects)
- Closed track: Euro NCAP primary scenarios achieved at target star rating
- Open road: 100,000+ km validation miles completed per configuration
- Functional safety: ISO 26262 Phase 4 (Production Release) sign-off by Safety Manager
- Cybersecurity: ISO/SAE 21434 TARA completed; no open HIGH/CRITICAL cybersecurity risks
- SOTIF: ISO 21448 SOTIF Case documented; residual risk accepted by Chief Safety Engineer

### Acceptance Criteria (Final)
- All above quantitative metrics achieved before Job 1 (start of production)
- Safety concept signed off by Functional Safety Manager
- Type approval obtained for all target markets
