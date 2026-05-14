# RADAR & LIDAR — STAR INTERVIEW STORIES
## Module 6 of 7 | 6 Ready-to-Use STAR Answers

---

## STAR-1: Diagnosing Ghost Objects from Metal Bridge Structure

**Situation:**
During highway validation drives, AEB was triggering nuisance braking under a specific steel-girder bridge on the A9 autobahn at 130 km/h. The trigger occurred on 40% of passes, with no preceding vehicle present. Three near-miss incidents were reported by test drivers.

**Task:**
Identify the radar phenomenon causing the ghost detection and propose an algorithm fix without reducing genuine AEB performance.

**Action:**
1. Replayed radar logs from the bridge passes in the radar visualization tool: at 80m before the bridge, a stationary object appeared at range 30m, azimuth 0° — exactly in the path.
2. Analyzed RCS: 42 dBsm — far higher than any car or truck (typically 10–30 dBsm). This was clearly a metal structure.
3. Identified the mechanism: the steel bridge girder was reflecting a multipath return — radar beam bounced off road surface, then up to the girder, then back. This created a mirror image of the bridge at the apparent range of 30m.
4. Proposed fix: if object RCS > 35 dBsm AND object is stationary AND approaching at ego speed (consistent with a fixed overhead structure), classify as "infrastructure ghost" and remove from AEB threat list.
5. Validated: tested the filter against the bridge (ghost removed), then tested with a genuine 30 dBsm stationary GVT target (still detected correctly — RCS was 28 dBsm, below the 35 dBsm filter threshold).

**Result:**
Bridge false positive: 0% after filter. GVT detection: 100% (unchanged). Test driver safety concern resolved. Fix deployed in production software 3 weeks later. Same RCS filter pattern was applied to 2 other overhead structures (motorway gantries) that had similar signatures.

---

## STAR-2: Radar Calibration Drift After Road Vibration

**Situation:**
After extended testing on rough roads (cobblestone test sections at Papenburg), several test vehicles showed ACC following a vehicle that was actually in the adjacent lane — causing unnecessary deceleration and driver confusion.

**Task:**
Determine whether the root cause was algorithm or hardware, and whether calibration had drifted due to road vibration.

**Action:**
1. Compared radar calibration values (DID 0xF1A1) before and after the rough road test section: azimuth offset had changed from +0.02° to +0.72° — a 0.7° drift.
2. At 100m range, 0.7° azimuth error = 1.22m lateral error → enough to move a target from the adjacent lane into the ego lane.
3. Physical inspection: the radar mounting bracket had a worn anti-vibration bushing. After ~50km of cobblestone, the bracket had shifted.
4. Short-term fix: recalibrated the radar using the calibration routine (RoutineControl 0xFF10) on all affected vehicles.
5. Long-term fix: engineering change request to the hardware team for stiffer radar mounting bracket with higher vibration resistance specification. Added a calibration health monitor: if the yaw angle deviates from nominal by > 0.3° between two calibration runs, raise a DTC (RADAR_CALIBRATION_DRIFT) and inhibit ACC.

**Result:**
All 8 affected vehicles recalibrated. Hardware bracket redesign completed for production. The calibration drift DTC caught 2 further bracket failures in subsequent testing before they affected vehicle behavior.

---

## STAR-3: Building a LiDAR Point Cloud Calibration Validator

**Situation:**
After LiDAR integration on a new prototype, the perception engineer reported that fused camera-LiDAR object positions were inconsistent — objects appeared at slightly different positions depending on which sensor detected them first. Manual calibration verification was taking 3 hours per vehicle on a dedicated calibration track.

**Task:**
Build an automated calibration validation tool to verify LiDAR extrinsic calibration in < 15 minutes per vehicle without requiring the dedicated calibration track.

**Action:**
1. Identified that we could use parking lane markings as calibration reference: lane markings are at a known height (0m) and have sharp LiDAR intensity discontinuity.
2. Built a Python tool that: captured 10 seconds of LiDAR data while the vehicle was parked next to a lane marking, extracted the marking centroid from the point cloud, compared it to the expected position (known from vehicle GPS + HD map).
3. Computed the calibration residual: difference between LiDAR-measured marking position and HD map marking position → gave extrinsic calibration accuracy estimate.
4. If residual > 5cm in any axis, tool flagged the vehicle for full calibration track procedure.
5. Tool ran in the parking lot in 12 minutes vs. 3 hours on track.

**Result:**
Calibration check time reduced from 3 hours to 12 minutes for 80% of vehicles (those with < 5cm residual). Tool identified 2 vehicles with mounting shift > 10cm that required track recalibration. Adopted as standard pre-test check for all prototype vehicles on the program.

---

## STAR-4: Pedestrian Detection Rate Improvement in Low Light

**Situation:**
Night-time AEB pedestrian testing showed a 65% detection rate — well below the 90% requirement and the Euro NCAP 5-star threshold. LiDAR was providing good 3D geometry, but the camera-based classification was failing in low-light conditions.

**Task:**
Increase pedestrian detection rate from 65% to ≥ 90% in night-time conditions without hardware changes.

**Action:**
1. Analyzed false negative cases: LiDAR was successfully creating a bounding box for the pedestrian dummy in 92% of cases — but camera classification was returning "unknown" instead of "pedestrian" in 48% of night cases.
2. Camera classification failure mode: the night-time image was too dark for the RGB classifier — the model was trained primarily on daytime images.
3. Since I was in a validation (not development) role, I couldn't retrain the neural network. Instead, I proposed: in low-light conditions (ambient light sensor < 5 lux), fall back to LiDAR-primary classification — if LiDAR bounding box aspect ratio is consistent with pedestrian (height 1.5–2.0m, width 0.4–0.8m), classify as pedestrian without camera confirmation.
4. Worked with the perception team to implement this fallback: cost 2 engineer-days.
5. Validated: night AEB pedestrian detection rate went from 65% to 91%.

**Result:**
Euro NCAP night pedestrian component: 4.8/5.0 (above the 90% requirement). The LiDAR-primary fallback pattern was documented in the sensor fusion specification as a standard degraded-mode operation.

---

## STAR-5: Radar Object List Validation Against Ground Truth

**Situation:**
A new 77 GHz radar ECU was being integrated from a new supplier. The supplier provided test reports showing 250m range and ±0.1m accuracy. Before accepting the supplier's data, we needed to independently validate the radar in our vehicle configuration.

**Task:**
Design and execute an independent validation test for the new radar's object detection performance and compare to specification claims.

**Action:**
1. Designed a test matrix: corner reflector tests at 10m, 25m, 50m, 100m, 200m; moving GVT tests at 30, 60, 100, 130 km/h; rain chamber tests at 25 and 50mm/hr.
2. Reference: used a calibrated GPS/IMU on the GVT vehicle (accuracy ±2cm) as ground truth for position and velocity.
3. Built a Python analysis script: correlated radar object list timestamps to GPS timestamps, computed range error, azimuth error, and velocity error at each test point.
4. Results: range accuracy at 100m = ±0.35m (slightly worse than ±0.1m claim, which was measured in an anechoic chamber). Velocity accuracy = ±0.2 m/s (met claim). In 50mm/hr rain: range reduced to 140m (30% degradation) — supplier had claimed "< 20% degradation."

**Result:**
Delivered a test report showing 3 deviations from supplier claims. Supplier accepted the data — the rain degradation was a known issue in their lab-to-vehicle integration. They provided a software update (better range extension algorithm in rain) that brought rain range to 180m (10% degradation). Supplier acceptance criteria updated for future programs.

---

## STAR-6: Explaining 4D Radar to a Customer

**Situation:**
During a customer technical review, the ADAS product manager from the OEM asked: "Our competitor is announcing '4D radar' — what is it, and should we be worried that our current radar is obsolete?"

**Task:**
Provide a clear technical explanation of 4D radar vs. 3D radar and give an honest assessment of whether an upgrade was needed for our current ADAS system.

**Action:**
1. Explained 3D vs 4D: traditional FMCW radar gives range (R), velocity (v), azimuth (az) = 3 dimensions. 4D radar adds elevation (el) as the 4th dimension — enabling height measurement. Some also call "FMCW LiDAR" or velocity-per-point radar "4D."
2. The key upgrade: with elevation measurement, the radar can distinguish overhead bridges (high elevation) from stationary cars (low elevation) — directly solving our bridge ghost false-positive problem, and enabling pedestrian height classification.
3. Honest assessment: our current ACC and AEB requirements were being met by 3D radar with software filtering. 4D would improve edge cases (bridge false positives, pedestrian classification) but was not needed for current Euro NCAP 5-star score.
4. Recommendation: evaluate 4D radar for the next platform (3-year roadmap) — it would reduce algorithm complexity and improve robustness. For the current platform, the software filter approach was sufficient.

**Result:**
Customer appreciated the honest, evidence-based analysis vs. a competitive fear response. Decision: current radar approved for production; 4D radar added to next-generation ADAS sensor roadmap with a target integration date. I was invited to present at the next technical steering committee.

---

*Next: [03_Mini_Projects.md](03_Mini_Projects.md)*
