# 39 — ADAS AI Interview Preparation (500+ Q&A)

## Overview
Comprehensive interview preparation for ADAS/AD AI roles at Tesla, NVIDIA, Waymo, Mobileye, Bosch, Continental, Aptiv, Qualcomm, Zoox, Cruise, Argo AI. Covers AI/ML, embedded systems, safety, architecture, and behavioural questions.

---

## PART 1: Machine Learning Fundamentals (L1/L2)

**Q1: What is the bias-variance tradeoff in the context of ADAS perception?**  
A: High bias: model underfits → misses pedestrians in complex scenes → dangerous false negatives. High variance: model overfits training distribution → fails on OOD data (new country roads, unusual weather) → dangerous in production. Solution: regularisation (dropout, weight decay), diverse training data, cross-validation. Production ADAS: validate on held-out regional data to ensure generalisation.

**Q2: Explain precision, recall, and F1 for ADAS object detection.**  
A: Precision = TP/(TP+FP) — of all detections, how many are real objects? Low precision = ghost objects → false braking. Recall = TP/(TP+FN) — of all real objects, how many did we detect? Low recall = missed pedestrians → injury. For AEB: recall is critical (never miss a pedestrian). Trade-off: lower confidence threshold → higher recall, lower precision → more false alarms. Production threshold tuned to maximise recall while keeping FP rate below OEM specification.

**Q3: What is anchor-free vs anchor-based object detection?**  
A: Anchor-based (YOLOv3-5, SSD): pre-define anchor boxes of various scales/ratios; predict offset from anchors. Pros: mature, well-understood. Cons: hyperparameter tuning of anchors, fails for unusual aspect ratios (small pedestrians at range). Anchor-free (CenterNet, FCOS, RT-DETR): predict object centres directly, no anchor boxes. Pros: no anchor engineering, better at unusual scales, cleaner architecture. Mobileye Eagle Eye (proprietary) and Tesla FSD use anchor-free approaches for production.

**Q4: How does YOLOv8 differ from YOLOv5 for automotive applications?**  
A: YOLOv8 improvements: (1) Decoupled head (separate cls/reg branches) → better class/location accuracy; (2) Anchor-free detection head → no anchor tuning; (3) CIoU loss → better bounding box regression; (4) C2f bottleneck (attention-like) → better feature learning with same FLOPs; (5) Native instance segmentation support (YOLOv8-Seg). Automotive: YOLOv8n is the standard baseline for real-time ADAS; 4ms INT8 on Jetson Orin NX.

**Q5: What is IoU and how is it used in NMS and mAP?**  
A: IoU = area of intersection / area of union. NMS: suppress duplicate boxes with IoU > 0.5 (keep highest confidence). mAP: compare predicted box with GT; count as TP if IoU > threshold (usually 0.5). ADAS: mAP@0.5 for coarse validation; mAP@0.5:0.95 (COCO-style) for comprehensive evaluation. Pedestrian: use lower IoU threshold (0.4) due to thin bounding boxes.

---

## PART 2: Deep Learning Architecture (L2/L3)

**Q6: Explain the FPN (Feature Pyramid Network) and its importance in ADAS.**  
A: FPN combines features from multiple backbone scales: P3 (small/detail) + P4 + P5 (large/semantic) via top-down pathway with lateral connections. Result: rich features at all scales without multiple passes. ADAS: critical for detecting pedestrians at 100m (small, 20px) and trucks at 5m (large, 400px) in same frame. Without FPN: small object detection degrades significantly (< 30% AP for <32px objects).

**Q7: How does attention mechanism (Transformer) help in autonomous driving?**  
A: Self-attention: each spatial location attends to all other locations → captures long-range dependencies. In ADAS: models relationship between distant objects (pedestrian at intersection + oncoming car) without needing large receptive field. BEVFormer (Waymo-style): uses deformable attention to build BEV (Bird's Eye View) feature map from multi-camera images — enables 360° perception without LiDAR. Cross-attention in DETR: queries attend to image features → direct set prediction (no NMS needed).

**Q8: What is PointPillars and why is it preferred for automotive LiDAR over PointNet?**  
A: PointPillars (Lang et al. 2019): discretise LiDAR point cloud into vertical pillars (columns in BEV); encode each pillar's points with PointNet-style MLP; create pseudo-image (BEV feature map); apply standard 2D CNN detector (SSD/YOLO head). Speed: 62Hz on GPU vs PointNet++ 5Hz. ADAS fit: (1) BEV output matches radar coordinate system → easy fusion; (2) CNN backbone reuses ADAS camera networks; (3) Fixed memory footprint (fixed grid size). Alternative: VoxelNet (3D convolutions) — higher accuracy but 10× slower — not feasible for real-time production.

**Q9: Explain knowledge distillation in the context of compressing a perception model for ECU deployment.**  
A: Teacher: YOLOv8l (43M params, 93% mAP, runs on GPU server). Student: YOLOv8n (3M params, need 88% mAP, must run on Jetson at 4ms). Distillation: train student to mimic teacher's soft output probability distribution (temperature = 4.0) + hard ground truth labels. Feature distillation: also match FPN intermediate features (requires adapter layers). Result: student achieves 91% mAP (vs 83% trained only on hard labels) — 8% improvement "for free".

**Q10: What is batch normalisation and why is it problematic for ADAS deployment?**  
A: BatchNorm normalises activations using batch mean/variance during training. During inference: uses running statistics computed during training. Problem: if test distribution (night, rain) differs from training distribution → running stats are wrong → detection quality drops. Solution: (1) LayerNorm (Transformer) — uses instance statistics, no batch dependency; (2) InstanceNorm for style-sensitive features; (3) Test-time BatchNorm: update running stats briefly on recent frames (online adaptation); (4) Ensure training data diversity to match deployment distribution.

---

## PART 3: Sensor Fusion (L2/L3)

**Q11: Explain the difference between early, mid, and late fusion in ADAS.**  
A: Early (raw) fusion: combine raw sensor signals before any processing → preserves information but computationally expensive, hard to handle different resolutions/rates. Mid (feature) fusion: each sensor extracts features independently, features fused before detection head → balance of flexibility and performance (BEVFusion, DeepFusion). Late (output) fusion: each sensor has independent detector, fuse at detection output level → easiest to implement, works even if one sensor fails. Production: mostly late/mid fusion; BEVFusion (mid) for L3+ where accuracy critical.

**Q12: How does a Kalman Filter handle sensor dropout in ADAS?**  
A: KF has two phases: predict (propagates state using motion model — no sensor needed) + update (uses sensor measurement when available). During sensor dropout: only predict phase runs; covariance grows (uncertainty increases); track continues with predicted position. After 3-5 frames dropout: covariance too large → track enters "coasted" state; position estimate used with reduced confidence; if radar returns → update immediately reduces covariance. ISO 26262: if radar fails > 100ms → DTC + warning; ACC/AEB enter degraded mode (camera-only with tighter TTC thresholds).

**Q13: What is covariance intersection and when is it used?**  
A: CI safely fuses estimates with unknown correlations (prevents overconfident fusion). Standard KF fusion assumes independence: if two sensors share information (e.g., both use map data), correlated errors → artificially overconfident result. CI: fused covariance ≥ each individual covariance (conservative but consistent). Used when: map-based localisation + camera lane — both use map → correlated. Production: distributed fusion across multiple ECUs where correlation unknown.

---

## PART 4: Automotive-Specific AI (L2/L3)

**Q14: How does Tesla's occupancy network differ from traditional object detection for FSD?**  
A: Traditional: detect individual objects (car, pedestrian) → bounding boxes; fails for unusual objects (shopping carts, debris). Tesla occupancy network (presented 2023 AI Day): predicts 3D occupancy voxel grid from 8 cameras; no predefined classes → detects "anything solid"; temporal fusion over multiple frames → densifies sparse estimates. Advantages: handles long-tail objects (construction barriers, bicycles with trailers); provides true free-space information. Limitations: harder to extract per-object velocity for ACC/AEB (needs additional flow estimation).

**Q15: What is BEVFusion and why is it relevant for production ADAS?**  
A: BEVFusion (MIT 2022): unifies camera and LiDAR in Bird's Eye View feature space. Steps: (1) Camera: BEV encoder (BEVDet-style with perspective transform); (2) LiDAR: voxelisation + sparse 3D CNN; (3) Fuse BEV features (concat + conv); (4) Detection head (CenterPoint). Outperforms camera-only and LiDAR-only in most conditions. Production relevance: Waymo and NVIDIA Drive platform use variants; provides natural coordinate space for planning; camera fills LiDAR gaps (between beams); LiDAR provides accurate range for camera.

**Q16: Explain TTC (Time to Collision) and its limitations in AEB systems.**  
A: TTC = range / closing_speed. Simple, low latency, works with radar alone. Limitations: (1) Constant velocity assumption — underestimates risk if target decelerates; (2) Doesn't account for path curvature — straight-line TTC wrong for curved road; (3) Fails when closing speed ≈ 0 (car just turned ahead, initial approach speed = 0); (4) Range accuracy dependent on target geometry (large trucks → range reads front, small bikes → range reads centre). Enhanced TTC: use predicted trajectory (from IMU + map) + target velocity estimation. Production: TTC + path overlap + object class probability all contribute to AEB trigger.

---

## PART 5: Safety and Standards (L2/L3)

**Q17: What is SOTIF and how does it differ from ISO 26262 for AI systems?**  
A: See module 33 for full treatment. Key point: ISO 26262 = random hardware/SW faults; SOTIF = performance limitations of correct hardware causing harm. AI-specific SOTIF concerns: model fails on OOD data (fog, unusual objects), model sensitive to adversarial inputs (unusual lighting), confidence calibration mismatch (model says 95% confident but wrong 20% of time).

**Q18: What is ASIL-B decomposition in the context of camera perception?**  
A: ASIL-B AEB system: if full ASIL-B required for camera perception — very expensive and difficult to certify neural network to ASIL-B. Solution: ASIL decomposition → split into two independent ASIL-A paths (camera + radar); each implemented independently to ASIL-A; combined safety = ASIL-B. Camera perception ASIL-A: E2E CRC on CAN messages, runtime watchdog (inference latency monitor), sensor health diagnostics, plausibility checks.

**Q19: How do you validate an AI model for ISO 26262 compliance?**  
A: No formal NN verification tool yet (active research area). Accepted industry practices: (1) Requirements-based testing: comprehensive test dataset covering all specified scenarios; (2) Back-to-back testing: compare neural network output vs verified reference (classical algorithm for simpler scenarios); (3) Coverage metrics: scenario coverage matrix (not code coverage); (4) Statistical validation: demonstrate statistically significant performance on test set (confidence intervals); (5) Robustness testing: adversarial inputs, input perturbation; (6) Traceability: every test trace to requirement; requirement traces to safety goal; audit trail for product liability.

---

## PART 6: System Design (L3)

**Q20: Design a perception system for a Level 3 highway pilot from scratch.**  
A: (1) Sensors: 3× LRR radar (front 200m + rear corners) + 3× cameras (front 120°, front long 30°, rear 120°) + front LiDAR (optional, premium). (2) ECU: NVIDIA Orin NX 16GB as perception domain controller; 100BASE-T1 Ethernet from each sensor. (3) Perception pipeline: Camera YOLOv8s INT8 (30Hz, 8ms) → 3D position lift → BEV; Radar CAN FD 20Hz → track association; KF fusion → stable tracks at 30Hz. (4) Sensor fusion: temporal alignment ±50ms; EKF per track; gated nearest-neighbour association. (5) Output: FusedObjectsList via SOME/IP to Planning ECU. (6) Safety: ASIL-B decomposition (camera ASIL-A + radar ASIL-A); E2E on all CAN; watchdog 50ms; DTC on any sensor timeout. (7) Validation: 1000+ test scenarios in CARLA + 100 physical track tests; Euro NCAP AEB test suite; mAP gates: pedestrian AP > 85%, car AP > 95%.

**Q21: How would you handle the sim-to-real gap when training on CARLA data?**  
A: (1) Domain randomisation: randomise CARLA textures, lighting, weather, sensor noise → model doesn't overfit to specific visual style; (2) Style transfer: CycleGAN or UNIT to convert CARLA frames to real-camera style; (3) Mixed training: 70% CARLA + 30% real data (manually labelled); (4) Feature-level adaptation: domain adaptation loss in training (minimise distribution distance between CARLA and real features); (5) Confidence calibration: model calibrated on real data even if trained on CARLA; (6) Validation: always evaluate final model on real-world test set → CARLA-only validation insufficient for production approval.

---

## PART 7: Coding Challenges (Python / C++)

**Q22: Implement NMS (Non-Maximum Suppression) from scratch.**
```python
def nms(boxes, scores, iou_threshold=0.5):
    """Greedy NMS. boxes: (N,4) [x1,y1,x2,y2], scores: (N,)"""
    x1,y1,x2,y2 = boxes[:,0],boxes[:,1],boxes[:,2],boxes[:,3]
    areas = (x2-x1)*(y2-y1)
    order = scores.argsort()[::-1]
    keep  = []
    while order.size > 0:
        i = order[0]; keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        inter = np.maximum(0, xx2-xx1) * np.maximum(0, yy2-yy1)
        iou   = inter / (areas[i] + areas[order[1:]] - inter)
        order = order[1:][iou < iou_threshold]
    return keep
```

**Q23: Implement IoU calculation for 3D bounding boxes.**
```python
def iou_3d_bev(box1, box2):
    """BEV IoU for 3D boxes. box: [cx, cy, w, l] (no rotation for simplicity)"""
    def get_corners(box):
        cx,cy,w,l = box
        return [cx-w/2, cy-l/2, cx+w/2, cy+l/2]
    
    b1 = get_corners(box1); b2 = get_corners(box2)
    ix1 = max(b1[0],b2[0]); iy1 = max(b1[1],b2[1])
    ix2 = min(b1[2],b2[2]); iy2 = min(b1[3],b2[3])
    inter = max(0,ix2-ix1) * max(0,iy2-iy1)
    a1 = box1[2]*box1[3]; a2 = box2[2]*box2[3]
    return inter / (a1 + a2 - inter + 1e-7)
```

**Q24: Implement Kalman Filter predict/update cycle.**
```python
def kf_predict(x, P, F, Q):
    """x: state (n,), P: covariance (n,n), F: transition, Q: process noise"""
    x_pred = F @ x
    P_pred = F @ P @ F.T + Q
    return x_pred, P_pred

def kf_update(x, P, z, H, R):
    """z: measurement, H: obs matrix, R: measurement noise"""
    S = H @ P @ H.T + R
    K = P @ H.T @ np.linalg.inv(S)         # Kalman gain
    x_upd = x + K @ (z - H @ x)
    P_upd = (np.eye(len(x)) - K @ H) @ P
    return x_upd, P_upd
```

---

## PART 8: Behavioural Questions (All Levels)

**Q25: "Tell me about a time you debugged a hard AI performance issue in production."**  
Key points to cover: (1) Specific metric that regressed (pedestrian AP dropped 8%); (2) Structured investigation: data analysis first, not guessing; (3) Root cause: distribution shift (new region added to deployment with different signage/road markings); (4) Solution: targeted data collection + fine-tuning on new region; (5) Process improvement: added per-region holdout test set to catch future regressions.

**Q26: "How do you prioritise safety vs feature development speed?"**  
Key points: (1) Never ship without passing safety gates (ASIL analysis, test suite); (2) Incremental deployment: new features behind feature flag, shadow mode first; (3) Data-driven escalation: phased rollout with monitoring — if anomaly detected → immediate rollback; (4) Team process: weekly safety review, clear definition of "must-pass" criteria before any OTA push.

---

## 39 Chapters — By Company Focus

| Company | Key Topics | Modules |
|---------|----------|---------|
| Tesla | Occupancy networks, FSD, no LiDAR, dataset scale | 05,06,14,29,38 |
| NVIDIA | Drive platform, TensorRT, BEVFusion | 29,31,36 |
| Waymo | Lidar-first, safety, fleet scale | 12,15,33,40 |
| Mobileye | EyeQ chip, RSS safety, edge AI | 29,33,44 |
| Bosch | AEB, ACC, radar, ISO 26262 | 25,26,27,32,33 |
| Qualcomm | Snapdragon Ride, power efficiency | 29,30,44 |
| Aptiv | Sensor integration, ADAS platform | 08,14,15 |

---

*See also: Module-specific Q&A at the end of each module (01-45).*
