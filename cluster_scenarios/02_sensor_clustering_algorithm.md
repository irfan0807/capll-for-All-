# Sensor / Radar Clustering Algorithm — Scenario-Based Questions (Q16–Q30)

> **Domain**: How raw radar/LiDAR/USS detections are grouped (clustered) into tracked objects, the algorithms involved, and the failure modes that occur in ADAS.

---

## Q16: What Is Radar Detection Clustering and Why Is It Needed?

### Scenario
A radar ECU reports 200+ individual raw "detections" (range-Doppler cells above noise threshold) per scan cycle when there are only ~5 real objects in front of the vehicle. How does the ADAS system reduce 200 detections to 5 tracked objects?

### Expected Behavior
The clustering algorithm groups spatially and/or velocity-close detections into a single object cluster, then a tracker maintains the object hypothesis over time.

### Detailed Explanation
**ADAS Radar Signal Processing Pipeline:**

```
RF Echo → ADC → Range-Doppler FFT → CFAR Detection → Clustering → Object Hypothesis → Tracker → Object List
```

1. **CFAR (Constant False Alarm Rate)**: identifies range-Doppler cells above a noise-relative threshold. Produces raw detections (range, azimuth, Doppler, amplitude).
2. **Clustering**: groups detections that belong to the same physical object.
   - A car at 50 m may produce 10–20 detections from different surface reflection points (roof, bonnet, mirrors, bumper).
   - A truck at 50 m may produce 40–60 detections (large radar cross section).
3. **Object Hypothesis**: one cluster → one object candidate, with centroid position, velocity, class estimate.
4. **Tracker (Kalman Filter)**: maintains objects across multiple scan cycles; handles missed detections (coasting) and new object initialization.

### Clustering Algorithms Used in ADAS Radar

| Algorithm | Description | Advantage | Disadvantage |
|-----------|-------------|-----------|--------------|
| Distance Threshold | Group detections within d_range, d_azimuth, d_Doppler of each other | Simple, fast | Fails when two close objects touch spatially |
| DBSCAN | Density-Based Spatial Clustering of Applications with Noise; groups high-density regions | Handles arbitrary shapes; identifies noise points | Computationally heavier; ε and MinPts tuning required |
| Grid-based | Map detections onto range-azimuth cells; occupied cells form clusters | Very fast; hardware-friendly | Resolution limited by cell size |
| K-means | Partition detections into K clusters; minimize intra-cluster distance | Useful when K is known | Requires known K; poor for variable object count |

### Acceptance Criteria
- 200 raw detections from 5 objects → 5 clustered object hypotheses in ≤ 10 ms processing time
- Cluster centroid accuracy: ≤ 0.5 m RMSE vs. ground-truth object center at 50 m

---

## Q17: Cluster Split — Two Closely Spaced Vehicles Detected as One Object

### Scenario
Two vehicles (V1 and V2) are traveling 4 m apart at 80 m from the radar. The radar's range resolution is 0.8 m (bandwidth = 187.5 MHz). The clustering algorithm merges both vehicles into one wide cluster. ACC then follows this merged cluster as a single wide vehicle, with incorrect range and velocity estimates.

### Expected Behavior
The clustering algorithm should separate V1 and V2 into two distinct clusters when their detection clusters are separable in range, azimuth, or Doppler. With 4 m spacing at 80 m range, the range delta is potentially resolvable if radar bandwidth is sufficient.

### Detailed Explanation
- Range resolution: Δr = c / (2 × B) = 3×10⁸ / (2 × 187.5×10⁶) = **0.8 m**.
- Two vehicles at 4 m apart at 80 m range: the detections should be separated by ~4 range bins (4 m / 0.8 m).
- However, strong reflections from V1 may spill into adjacent range bins (range sidelobes) — contaminating V2's detections.
- Clustering distance threshold: if set too loosely (> 4 m), V1 and V2 are merged.
- Solution: tighten the range clustering distance threshold to ≤ 2 m; accept some split cost on single objects.
- Trade-off: too tight → single vehicles with multiple bright reflections split into 2 false objects.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Two vehicles at 2 m spacing: inseparable at 0.8 m range resolution | Merged into one cluster; tracker must handle the merged object gracefully |
| Motorcycle directly behind a car (same range, very small angular separation) | Merged; track width estimate helps distinguish after lane change |
| Truck with trailer: continuous detection cloud over 15 m | May appear as 2 clusters (cab + trailer); tracker should associate as one vehicle |
| Two pedestrians standing 1 m apart | Very hard to separate; PCD must flag as "2 VRUs or wider single VRU" |

### Acceptance Criteria
- Vehicles ≥ 4 m apart at ≤ 80 m correctly split into 2 clusters in ≥ 90% of scan cycles
- Cluster centroid error for merged two-vehicle object: ≤ 1.5 m vs. individual vehicle centers

---

## Q18: Cluster Merge — One Vehicle Detected as Two Separate Objects

### Scenario
A large SUV has a radar-bright front bumper and a radar-bright rear bumper reflector. The radar resolves two distinct bright detections 4.5 m apart (front and rear of the vehicle). The clustering algorithm splits the SUV into TWO objects — front half and rear half. ACC then follows the "front half ghost" and ignores the real leading edge.

### Expected Behavior
The clustering must detect that the two bright detections are part of the same vehicle and merge them into one cluster representative of the entire vehicle.

### Detailed Explanation
- Multiple bright reflectors on one vehicle: common for large vehicles with retroreflectors, mirrors, towbars.
- The vehicle's own velocity is consistent across both reflection points: both detections have the same Doppler velocity.
- Merge condition: if two clusters have the same or very similar Doppler velocity AND are within vehicle-width lateral extent AND within plausible vehicle-length range extent → merge into one object.
- Velocity consistency check is the key disambiguator: independent objects have independent velocities; parts of the same vehicle share velocity.

### Algorithm Decision Logic

```
FOR each pair of clusters (A, B):
    IF |Doppler_A − Doppler_B| < v_thresh (e.g., 0.5 m/s)
    AND lateral_separation(A, B) < max_vehicle_width (e.g., 2.5 m)
    AND range_separation(A, B) < max_vehicle_length (e.g., 6.0 m)
    THEN merge(A, B) → single object
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Two vehicles at exact same speed (same Doppler): merging risk | Range separation > 6 m → they cannot be the same vehicle; do not merge |
| Articulated truck: cab + trailer at slightly different speeds (trailer lag) | 0.3–0.5 m/s Doppler difference; careful: same v_thresh may merge them; use geometric check |
| Vehicle with spinning radar-visible wheel: different Doppler component from wheel | Extended Kalman Filter with object model that handles multi-Doppler-component objects |
| Vehicle opening its trunk (lid moves with different Doppler momentarily) | Momentary Doppler split; tracker keeps object alive due to history; does not split permanently |

### Acceptance Criteria
- SUV (single vehicle with two bright reflectors 4 m apart) correctly merged into one object in ≥ 95% of scan cycles
- No ghost "half-vehicle" objects appear in steady-state tracking for known vehicle types

---

## Q19: DBSCAN Clustering — Parameter Tuning (ε and MinPts)

### Scenario
The radar clustering uses DBSCAN. At highway speeds, small ε (neighborhood radius = 1.0 m) correctly separates two vehicles. In stop-and-go traffic, the same ε causes a shopping trolley next to a pedestrian (0.8 m separation) to be merged with the pedestrian. How should ε be tuned?

### Expected Behavior
DBSCAN ε should be **speed-context-adaptive**:
- **Highway mode**: smaller ε acceptable (vehicles well separated in range).
- **Urban/low-speed mode**: smaller ε required for fine discrimination of close objects (VRUs, cyclists, pedestrians).

### Detailed Explanation
- DBSCAN parameters: ε (neighborhood radius), MinPts (minimum neighbors to form a core point).
- At highway speed (100 km/h): vehicles are typically ≥ 20 m apart; ε = 2 m easily separates vehicles.
- In car parks / low speed: objects can be 0.5–1 m apart; ε = 1 m merges adjacent objects.
- Context-adaptive ε: switch based on ego speed, road type (map), or object density.
- Alternative: **HDBSCAN** (hierarchical DBSCAN) — automatically adapts to varying density; ideal for ADAS.

| Scenario | Recommended ε | MinPts |
|----------|--------------|--------|
| Highway vehicle tracking | 2.0 m | 3 |
| Urban vehicle tracking | 1.0 m | 2 |
| Parking (USS + radar) | 0.5 m | 2 |
| Pedestrian/cyclist detection | 0.3–0.5 m | 2 |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Dense rain returns (many noise CFAR detections) | DBSCAN noise rejection: MinPts > 1 filters isolated rain droplets |
| Building corner reflecting radar: large structural cluster | Object size filter: reject cluster width > 4 m AND height < 0.5 m (structure profile) |
| Cyclist inside a cluster of pedestrians | Low ε: may correctly split; high ε: merged; use velocity as secondary discriminator |
| Two motorcycles riding in formation (0.5 m side by side) | Velocity identical; lateral separation < 0.5 m; will merge; acknowledge as limitation for current radar |

### Acceptance Criteria
- DBSCAN correctly separates pedestrian from shopping trolley (0.8 m apart) with ε ≤ 0.5 m in parking mode
- Highway mode: all vehicles ≥ 5 m apart correctly separated in 100% of scan cycles
- Rain noise rejection: ≥ 95% of isolated rain detections filtered by MinPts criteria

---

## Q20: Clustering in Doppler-Velocity Space — Relative Speed Disambiguation

### Scenario
Three vehicles are at the same range (40 m) simultaneously: one stationary (relative velocity = −ego_speed), one moving at 80 km/h same direction (relative velocity ≈ 0), and one oncoming at 120 km/h (relative velocity = −(100+120/3.6)). All three are at 40 m on the radar sweep. How does clustering separate them?

### Expected Behavior
The clustering algorithm must use the **Doppler velocity dimension** (in addition to range and azimuth) to disambiguate the three objects that are at the same range.

### Detailed Explanation
- Range resolution alone: 3 objects at 40 m ± 0.8 m (range resolution) → will appear in overlapping range bins.
- Doppler separation:
  - Stationary: Doppler ≈ −28 m/s (ego at 100 km/h).
  - Same-speed vehicle: Doppler ≈ 0 m/s.
  - Oncoming: Doppler ≈ +33 m/s (100 + 120 km/h closing at 61 m/s relative).
- The Doppler velocity dimension clearly separates all three despite same range.
- Clustering must occur in **4D space**: range × azimuth × elevation × Doppler.
- Range-Doppler FFT (the 2D FFT in radar signal processing) already provides range-Doppler joint cells; clustering in this 2D space directly preserves Doppler separation.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Two vehicles at same range AND same speed (traveling in parallel lanes) | Azimuth (bearing) must separate them; if in same lane: same-vehicle merging logic (not applicable) |
| Doppler aliasing: very fast object wraps around Doppler spectrum | Extended range Doppler ambiguity resolver; 77 GHz radar typically resolves up to ±100 m/s |
| Stationary object at 0 km/h road speed (parked car): Doppler = −ego_speed | Filtered from ACC target list (stationary); FCW assesses if in path |

### Acceptance Criteria
- Three objects at same range but different Doppler correctly resolved into 3 distinct clusters in 100% of test frames
- Doppler dimension used as a mandatory clustering axis (not post-hoc disambiguation)

---

## Q21: Cluster Centroid Estimation — Impact on ACC Following Distance Accuracy

### Scenario
A cluster of radar detections for a minivan produces a centroid that is computed as the mean of all detection positions. Because the radar returns are biased toward the rear of the minivan (strong reflection from rear bumper), the centroid is 1.5 m behind the true rear edge of the vehicle. ACC then sets a following distance 1.5 m shorter than commanded.

### Expected Behavior
The cluster centroid should represent the **leading edge** (nearest point of the object to the radar), not the mean of all detections.

### Detailed Explanation
- Mean centroid: simple but biased toward strong reflectors (never equals the nearest edge for acc use).
- **Nearest-point extraction**: the minimum range detection in the cluster represents the closest surface.
- For ACC following distance: use the minimum-range detection as the object's range estimate.
- For AEB TTC: use the minimum-range, maximum-closing-rate detection.
- Object width / extent estimation: use the full cluster extent (min to max detection positions).
- The tracker should maintain both: centroid (for motion model) AND nearest point (for distance control).

| Measurement | Use Case |
|-------------|----------|
| Cluster centroid | Object velocity estimation (motion model) |
| Nearest range detection | ACC distance control, AEB TTC |
| Cluster extent (width × length) | Object size classification |
| Detection count | RCS / object type confidence |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Only 1 detection in cluster (single echo): centroid = nearest point | No special handling needed |
| Very wide object (truck, 8 m wide): many detections spread widely | Nearest point extracts the correct leading edge despite wide spread |
| Object rotating (turning vehicle): nearest edge changes dynamically | Tracker must use nearest-point estimate dynamically per frame |

### Acceptance Criteria
- ACC range estimate based on nearest-point of object cluster: error ≤ 0.3 m from true rear edge
- AEB TTC derived from nearest-point range: no systematic underestimate due to centroid bias

---

## Q22: Ghost Clusters From Multi-Path Reflections

### Scenario
The ego vehicle is in an urban area with glass-fronted buildings. Radar signals reflect off the building, creating a ghost object at range 60 m (the actual object is at 30 m). The clustering algorithm creates a valid cluster from the reflected detections, generating a false tracked object. ACC decelerates for this ghost.

### Expected Behavior
Multi-path ghost clusters should be detected and rejected before being tracked. A ghost-rejection algorithm must identify reflection-symmetric ghost objects.

### Detailed Explanation
- Multi-path geometry: radar transmits → reflects off building → hits real object → reflects back via building → received by radar. Total path = 2 × building distance + 2 × object-building distance.
- The ghost appears at the wrong range (typically 2× the reflector range from the real object).
- Ghost disambiguation strategies:
  1. **Velocity consistency**: ghost objects appear with incorrect Doppler (reflection geometry changes the apparent Doppler). Ghost Doppler ≠ real object Doppler (except for edge cases).
  2. **Azimuth**: ghost appears slightly off-axis compared to the real object.
  3. **Trajectory plausibility**: ghost objects often move laterally in a manner inconsistent with road physics (can appear to travel through walls).
  4. **RCS symmetry**: real object + ghost often appear symmetrically about the reflecting surface.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Ghost appears in the driving lane and has a realistic velocity | Hard case; requires camera confirmation as mandatory gate for ACC target selection |
| Multi-path from wet road surface (mirror image below road level) | Negative elevation ghost; elevation filter suppresses (objects below road cannot be real on-road vehicles) |
| Ghost cluster appears for only 1 scan frame (transient reflection) | N/M track confirmation: object must appear in ≥ 3/5 consecutive frames before becoming a valid track |

### Acceptance Criteria
- Ghost cluster from static building multi-path rejected before generating a tracked object in ≥ 95% of cases
- N/M confirmation logic: objects < 3 detections in 5 frames not promoted to ACC targets

---

## Q23: LiDAR Point Cloud Clustering — Euclidean vs. Voxel Methods

### Scenario
A LiDAR sensor produces 300,000 points per scan. The clustering algorithm must segment these into objects (vehicles, pedestrians, cyclists, road surface) within the 100 ms scan cycle. Euclidean clustering takes 250 ms — too slow. What is the solution?

### Expected Behavior
Use a faster clustering approach: voxel-grid-based downsampling + DBSCAN on voxel centroids, OR deep learning-based semantic segmentation (PointNet, PointPillars) that simultaneously clusters and classifies.

### Detailed Explanation
- Naive Euclidean clustering on 300k points: O(N²) in worst case → too slow for real-time.
- Solutions:

| Method | Speed | Pros | Cons |
|--------|-------|------|------|
| Voxel grid + DBSCAN | 20–30 ms | Fast; reduces to ~5,000 voxels | Loses fine resolution |
| KD-tree nearest neighbor | 10–50 ms | Good for sparse scenes | Buildup time for large K |
| PointPillars (DNN) | 15–25 ms (GPU) | Simultaneous cluster + class | Requires GPU; training data needed |
| Cylindrical grid (range image) | 5–15 ms | Radar-like fast processing on cylindrical data | Less accurate at long range |

- Production ADAS LiDAR (Waymo, Mobileye) uses GPU-accelerated semantic voxelization with deep learning.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Very dense urban scene (1,000+ objects): clustering time spikes | GPU load monitored; object count cap with distance-based prioritization |
| Vehicle lying on its side (crashed car): unusual point cloud shape | DNN classification may fail; classifies as unknown large obstacle → AEB treats conservatively |
| LiDAR partially occluded by rain: inconsistent point cloud | Process available returns; mark object confidence as reduced |

### Acceptance Criteria
- LiDAR clustering pipeline: ≤ 50 ms per scan cycle for up to 300k points
- Object detection recall ≥ 98% for vehicles at ≤ 60 m range using GPU-based clustering

---

## Q24: Radar Cluster Track Initialization — New Object Confirmation Logic

### Scenario
A new vehicle enters the radar field of view (a car emerges from behind a building at an intersection). The radar detects a cluster at frame T=0. How many frames should the tracker wait before promoting this cluster to a confirmed "tracked object" that can trigger AEB/FCW?

### Expected Behavior
A balance must be struck:
- Too few frames (1 frame): ghost detections and noise clusters trigger false alarms.
- Too many frames (5+): new vehicles are not tracked quickly enough for safety reactions.
- Standard: **3/5 rule** — confirm after 3 positive detections in 5 consecutive frames (~150 ms at 20 Hz radar).

### Detailed Explanation
- Track initialization states:

```
[TENTATIVE] → (3/5 frames positive) → [CONFIRMED] → (FCW/AEB eligible)
     ↓ (2/5 frames, then no returns)
[DELETED]
```

- For intersection emergence (high-risk scenario): may use 2/3 rule (confirm faster) to respond to suddenly appearing objects.
- For highway following (low-risk emergence rate): 4/6 rule prevents false tracks from radar noise.
- Track confirmation should also be context-adaptive: in urban environments, faster confirmation required.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Object appears for exactly 3 frames then drives behind building again | Confirmed then immediately coasted; if no re-detection in 5 frames, deleted |
| Object appears very quickly (high closing speed: 200 km/h motorcyclist) | Object may cross 30 m zone in < 10 frames; must confirm in 2/3 for high-speed threats |
| Rain burst creates a cluster for 2 frames | 3/5 rule prevents promotion to confirmed track |

### Acceptance Criteria
- Confirmation latency: 3/5 rule → max 250 ms (5 frames at 20 Hz)
- High-speed object (> 150 km/h closing): 2/3 rule → max 100 ms confirmation
- Zero false track confirmations from rain/noise clusters in 1,000 km validation drive

---

## Q25: Cluster Deletion — Track Coasting and Object Disappearance

### Scenario
The ACC lead vehicle enters a tunnel (appears briefly, then camera + radar detections drop to zero due to tunnel geometry). The ACC cluster disappears. How long should the tracker coast the object before deleting the track?

### Expected Behavior
- **Coasting**: the tracker propagates the last known state (position + velocity) forward in time without new measurements.
- Coasting duration: typically 0.5–2.0 s for ACC targets before the track is deleted.
- For safety-critical coasting: the uncertainty (Kalman covariance) grows during coasting, reducing confidence.
- ACC target loss triggers smooth speed resumption to set speed.

### Detailed Explanation
- Coasting period: the tracker uses the object's velocity model to predict its future position.
- Uncertainty growth: σ_position grows at σ_velocity × Δt per frame. After 1 s of coasting, positional uncertainty may be ±2–5 m.
- When uncertainty > threshold: track is deleted (insufficient basis to control ACC or AEB).
- For tunnel entry: the driver is presumably still in the same lane; map context keeps track alive slightly longer.

| Coasting Duration | Track State | ACC Action |
|-------------------|-------------|------------|
| 0 – 300 ms | Valid; continue following | Maintain gap |
| 300 ms – 1 s | Coasting; low confidence | Hold speed; begin prep to increase speed |
| 1 s – 2 s | Extended coast | Gradually increase to set speed |
| > 2 s | Track deleted | Full free-speed resume |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Lead vehicle exits motorway: track legitimately disappears | Correct deletion; ACC resumes free speed |
| Track lost due to sensor occlusion (ADV vehicle shadow): reappears at different lateral position | Re-initialize track when object re-detected; check if it's the same object |
| Coasting track used by AEB: ghost AEB activation from coasted track | AEB must require CONFIRMED (non-coasted) detection; coasted tracks not eligible for AEB activation |

### Acceptance Criteria
- ACC coasting period: 1.0–2.0 s before free-speed resumption
- AEB requires confirmed (not coasted) track — never triggers from coasted-only target
- Covariance grows correctly during coasting; track deleted at position uncertainty > 3 m

---

## Q26: Sensor Fusion Clustering — Radar + Camera Bounding Box Alignment

### Scenario
The radar cluster centroid of a pedestrian is at (x=25.3, y=0.2) in vehicle coordinates. The camera bounding box centroid back-projected to vehicle coordinates is at (x=24.5, y=0.4). Should these be associated as the same object?

### Expected Behavior
Yes — the two measurements should be associated if within a **Mahalanobis distance gate**. The Mahalanobis distance accounts for each sensor's uncertainty (covariance), not just Euclidean distance.

### Detailed Explanation
- Euclidean distance: sqrt((25.3−24.5)² + (0.2−0.4)²) = sqrt(0.64 + 0.04) ≈ **0.82 m**.
- This is outside a naive 0.5 m gate but within the sensor uncertainty for camera back-projection at 25 m.
- Mahalanobis distance: d_M = sqrt((Δx, Δy) × Σ⁻¹ × (Δx, Δy)ᵀ), where Σ is the combined covariance.
- Camera depth uncertainty at 25 m: σ_depth ≈ 2–3 m → a 0.82 m range difference is < 1σ for camera.
- Mahalanobis gate at 3σ: association accepted.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Camera back-projection error large at night (less confident depth estimate) | Larger covariance → wider gate → more liberal association (risk of wrong associations) |
| Radar detects pedestrian; camera detects cyclist at similar position | Class mismatch: lower association score; flag ambiguity; use Doppler to decide |
| Two pedestrians 1.5 m apart: both camera and radar have two tracks each | Hungarian algorithm (cost matrix minimization) assigns camera-to-radar pairings optimally |

### Acceptance Criteria
- Radar-camera association uses Mahalanobis distance (not Euclidean) as primary metric
- Association gate: 3 standard deviations for each sensor modality
- Hungarian matching used for multi-object association in cluttered scenes

---

## Q27: Clustering Failure Mode — Road Debris Clustered as a Vehicle

### Scenario
A piece of metal debris (fallen part of a truck) is on the motorway. It has a high radar cross-section (metal at 0°) and produces a tight cluster. The clustering and classification pipeline classifies it as a "small stopped vehicle" and AEB activates. This is a false positive.

### Expected Behavior
Debris should be classified differently from a stopped vehicle:
- **Size filter**: debris cluster is smaller (< 0.5 m width typical vs. 1.5 m vehicle width).
- **Height filter**: debris is flat (< 5 cm height) vs. a vehicle (> 50 cm).
- **Track history**: a stopped vehicle would have a track history; debris appears suddenly with no track history.
- **Camera classification**: camera must confirm the object class is "vehicle" before AEB activates.

### Detailed Explanation
- The root cause is often: radar alone classifies by cluster RCS, not by geometry.
- LiDAR can resolve the flat-vs-tall ambiguity effectively (point cloud height slice).
- Camera for classification (stopped-vehicle vs. debris): CNNs trained on debris vs. vehicle images.
- AEB should not activate on radar-only classification of a stopped small object — camera confirmation mandatory.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Large debris (entire truck tyre, 1 m diameter): high RCS, potentially dangerous | Camera confirms it is large debris in the lane; AEB should activate (genuine hazard) |
| Debris off to the side (shoulder): not in ego lane | Lateral position filter: outside lane → no AEB |
| Debris at night: camera classification uncertain | Lower confidence; FCW fires; AEB requires higher confidence — may not activate for debris alone |

### Acceptance Criteria
- Debris < 0.3 m height: NOT classified as vehicle; AEB not activated (false positive prevention)
- Large debris (> 0.3 m height) in ego lane: classified conservatively as obstacle; AEB eligible
- Camera confirmation required before AEB activation on any stopped/stationary cluster

---

## Q28: Clustering with USS (Ultrasonic Sensors) — Parking Environment

### Scenario
In a parking scenario, 6 ultrasonic sensors fire simultaneously. Multiple sensors may detect the same object (a wall 0.5 m away). How is the USS data clustered into a single wall object rather than 6 separate detections?

### Expected Behavior
USS detections from different sensors are clustered using a spatial + temporal association:
- If multiple sensors report objects at the same range (within angular overlap), it is a single object.
- The cluster is mapped as an arc in the sensor's coordinate system.

### Detailed Explanation
- USS provides limited information: range only (no azimuth natively); azimuth inferred from sensor position + field of view.
- Cross-sensor correlation: sensor A (front-left) and sensor B (front-center) both see an object at ~0.5 m → same wall.
- USS spatial clustering: each sensor's detection mapped to a vehicle-coordinate position estimate; positions within 20 cm of each other = same object.
- Temporal consistency: stable detection over 3+ frames = confirmed stationary object.
- The wall is represented as an occupancy grid segment, not a point cluster.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| One USS sensor reports 0.4 m, adjacent sensor reports 0.7 m for same wall (angle mismatch) | Average within sensor geometry; the angular extent of each USS beam causes range variation on flat wall |
| Corner: two walls creating a concave corner detected by 3 sensors | Both wall segments detected; APA trajectory must avoid both |
| Moving pedestrian in parking lot: all 6 USS fire detections on different parts of them | Temporal inconsistency vs. walls; moving object hypothesis; APA halts |

### Acceptance Criteria
- Multi-USS wall detection cluster: single object with correct geometry in ≤ 3 sensor cycles (150 ms for 20 Hz USS)
- No duplicate objects generated for the same wall detected by multiple USS sensors
- Moving pedestrian distinguished from stationary wall via temporal consistency filter

---

## Q29: Cluster Data Association — Hungarian Algorithm vs. Nearest Neighbor

### Scenario
At T=0, there are 4 tracked objects (T1–T4). At T=1, the radar produces 4 new clusters (C1–C4). The naive "nearest neighbor" algorithm incorrectly assigns C2 to T3 (a closer raw-distance match) while the correct assignment is C2 → T2. This causes a track swap. Describe the correct assignment.

### Expected Behavior
The **Hungarian algorithm (Munkres algorithm)** solves the optimal assignment problem, minimizing the total cost across all assignments — preventing the local-optimal mistake of nearest neighbor.

### Detailed Explanation
- Nearest-neighbor: assigns each cluster to the nearest unassigned track. Fast but suboptimal.
- Hungarian algorithm:
  1. Build cost matrix: cost[i][j] = Mahalanobis distance(track_i, cluster_j).
  2. Find the assignment that minimizes total cost.
  3. Complexity: O(N³) for N×N matrix — feasible for N ≤ 30 objects.

**Example cost matrix:**

```
           C1   C2   C3   C4
Track T1 [0.5, 3.2, 5.1, 8.3]
Track T2 [4.1, 0.8, 3.6, 7.2]   ← C2 → T2 is optimal here
Track T3 [3.3, 1.1, 0.9, 6.5]   ← Nearest neighbor greedily assigns C2 to T3 (1.1 < 1.1)
Track T4 [7.5, 6.0, 4.2, 0.7]   ← C4 → T4 optimal
```

- Hungarian optimal total cost: 0.5 + 0.8 + 0.9 + 0.7 = **2.9** vs. nearest-neighbor cost: 3.5 (suboptimal).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| More clusters than tracks (new object appeared) | Cost matrix is non-square; unmatched cluster → tentative new track |
| More tracks than clusters (object disappeared / missed detection) | Unmatched track → coasting |
| Very high cost everywhere (large scene change): all assignments uncertain | Use Mahalanobis gate; if cost > gate threshold, do not associate — create new track instead |

### Acceptance Criteria
- Hungarian assignment yields optimal total assignment cost vs. nearest-neighbor in ≥ 95% of multi-object scenarios
- Track swap events (incorrect association persist > 3 frames) < 0.01 per 1,000 km of validation data

---

## Q30: Clustering Performance KPIs and HIL Cluster Evaluation

### Scenario
A new clustering algorithm is proposed to improve pedestrian separation in dense crowds. Define the full KPI framework for evaluating the new algorithm against the baseline.

### KPI Framework

| KPI | Definition | Target |
|-----|-----------|--------|
| **Detection Rate (DR)** | % of ground-truth objects with ≥ 1 cluster associated | ≥ 98% per class |
| **False Positive Rate (FPR)** | # clusters not associated to any ground truth object / total clusters | ≤ 2% |
| **Cluster Centroid RMSE** | RMS position error of cluster centroid vs. true object center | ≤ 0.5 m at 30 m range |
| **Cluster Split Rate** | % of single ground-truth objects resolved as 2+ clusters | ≤ 5% |
| **Cluster Merge Rate** | % of distinct ground-truth objects merged into 1 cluster | ≤ 3% |
| **Processing Latency** | Time from raw detection input to object list output | ≤ 15 ms |
| **Track Swap Rate** | # incorrect track-cluster associations per 1000 frames | ≤ 1 |
| **Convergence Time** | Frames to stable cluster after object enters FOV | ≤ 3 frames (150 ms at 20 Hz) |

### Test Dataset Requirements
- ≥ 10,000 annotated radar/LiDAR frames
- Include: highway convoy, urban crowd, parking lot, adverse weather
- Ground truth: RTK-GPS + manual annotation for object bounding boxes

### Acceptance Criteria
- All KPIs met simultaneously before algorithm promotion to production
- Regression: new algorithm must not worsen any KPI vs. baseline by > 5% in any test scenario category
