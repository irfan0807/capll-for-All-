# 04 — Machine Learning for ADAS

## Overview
Classical machine learning algorithms applied to automotive perception, prediction, and diagnostics. These are fast, interpretable, and deployable on low-power ECUs (ARM Cortex-A53) where CNNs are too expensive.

**When to use classical ML vs Deep Learning:**

| Scenario | Classical ML | Deep Learning |
|----------|-------------|---------------|
| Feature-engineered sensors (IMU, CAN) | ✅ Preferred | Overkill |
| Small dataset (<10k samples) | ✅ Better | Risk of overfitting |
| Inference on ARM M-series (no GPU) | ✅ ~0.1ms | Not feasible |
| Raw image/point-cloud input | Not effective | ✅ Required |
| Explainability needed (safety audit) | ✅ Feature importance | Hard to explain |
| High-dimensional sensor fusion | Possible | ✅ Better |

---

## 1. Regression — Lane Offset Prediction

**Problem:** Predict lateral offset (cm) from lane centre using polynomial coefficients and vehicle state.

**Feature engineering:**
- Left/right lane polynomial coefficients (from classical CV)
- Yaw rate, steering angle, vehicle speed
- Lane width estimate

**Algorithm:** Ridge Regression (L2 regularisation prevents coefficient blow-up)

```python
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

model = Pipeline([
    ('scaler', StandardScaler()),   # Essential: lane coefficients have very different scales
    ('reg', Ridge(alpha=1.0))
])
model.fit(X_train, y_offset)
# MAE < 3cm is production-acceptable
```

**Production deployment on ECU:**
1. Export with `joblib.dump(model, 'lane_offset.pkl')`
2. Convert to ONNX: `sklearn-onnx` converts most scikit-learn pipelines
3. Run with ONNX Runtime C++ on ARM (0.05ms inference)

---

## 2. Classification — Road Surface Type

**Problem:** Classify road as dry / wet / snow / gravel for ABS calibration and traction control.

**Sensors:** 3-axis IMU (vibration frequency), radar reflectivity, wheel speed sensors.

**Algorithm:** Random Forest
- 100 trees, max_depth=8 (limits model size to ~50KB)
- `class_weight='balanced'` — snow/gravel events are rare in training data

**Why not SVM or neural network?**
- Random Forest: naturally handles mixed feature scales, no normalisation needed at inference
- Feature importance: tells safety team which sensor drives each decision
- Parallel tree evaluation: all 100 trees run independently → parallelisable on multicore ARM

**Automotive note:** Road surface estimate must switch from 'dry' to 'wet' within 200ms of first water contact (safety requirement from Bosch ESP controller spec).

---

## 3. Anomaly Detection — Sensor Fault Detection

**Problem:** Detect sensor faults (stuck-at-value, intermittent, drift) without labelled fault data.

**Algorithm:** Isolation Forest
- Trains only on normal data (no fault labels required)
- Anomaly = data point that is isolated by fewer random partitions
- `contamination=0.01` means we accept 1% false positive rate

**Fault types detected:**
| Fault Type | Signal Pattern | Score |
|-----------|----------------|-------|
| Stuck-at | All features constant | -0.8 to -1.0 |
| Bias/drift | One feature offset | -0.4 to -0.7 |
| High noise | Large variance spike | -0.5 to -0.8 |
| Normal | Within learned distribution | +0.1 to +0.2 |

**ISO 26262 connection:** ASIL-B sensors require fault detection coverage > 90%. Isolation Forest + threshold tuning achieves this on IMU + radar + camera feature vectors.

---

## 4. SVM — Radar Object Classification

**Problem:** Classify radar detections into car / truck / motorcycle / stationary using cluster features.

**Features per detection cluster:**
- RCS (Radar Cross Section) in dBsm: cars ~10, trucks ~20, motorcycles ~3
- Range and velocity spread within cluster
- Azimuth angular span
- Number of detection points in cluster

**Algorithm:** SVM with RBF kernel
- Best for: small-to-medium datasets (< 50k samples), non-linear boundaries
- `probability=True`: outputs class probabilities for sensor fusion
- Inference: ~0.5ms for 1 sample on ARM A53 (acceptable for 20Hz radar cycle)

---

## 5. Model Deployment Pipeline (Embedded)

```
Training (GPU Server)         ECU Runtime
─────────────────────         ─────────────
scikit-learn Pipeline         ONNX Runtime C++ or
        │                     custom decision forest
        ▼                              ▲
   sklearn-onnx                        │
   convert_sklearn()                   │
        │                              │
        ▼                              │
   model.onnx ──────────────────────────
   (validated + quantised)
```

### Export scikit-learn to ONNX:
```python
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

initial_type = [('input', FloatTensorType([None, 8]))]  # 8 features
onnx_model = convert_sklearn(road_surface_clf, initial_types=initial_type,
                              target_opset=15)
with open("road_surface.onnx", "wb") as f:
    f.write(onnx_model.SerializeToString())
```

---

## 6. Interview Q&A

### L1
**Q: What is the difference between Ridge and Lasso regression?**  
A: Both add regularisation to linear regression. Ridge (L2) penalises the sum of squared coefficients — all features contribute but with reduced magnitude. Lasso (L1) penalises the sum of absolute values — drives irrelevant feature coefficients to exactly zero (feature selection). For ADAS with many correlated sensor features, Ridge is more stable.

**Q: Why normalise features before SVM?**  
A: SVM with RBF kernel computes Euclidean distance in feature space. Without normalisation, features with large scales (e.g., range_m in hundreds) dominate over features with small scales (e.g., yaw_rate in 0-5 deg/s), making the kernel distances meaningless.

### L2
**Q: How does Isolation Forest work without labelled fault data?**  
A: It builds random binary trees by randomly selecting a feature and a split value. Anomalies require fewer splits to isolate (shorter path length) because they differ from the majority. Average path length across all trees gives the anomaly score. No labels needed — it learns from the structure of normal data.

**Q: What is feature importance in Random Forest?**  
A: Each tree uses Gini impurity reduction at each split. A feature's importance = sum of weighted Gini decreases across all trees where that feature is used. Higher = more discriminative. In road surface classification, radar reflectivity and accelerometer Z-axis (vertical vibration) typically have highest importance.

### L3
**Q: How would you handle the class imbalance in ADAS sensor fault detection? (99% normal, 1% faults)**  
A: Four strategies: (1) Undersampling normal class (loses information); (2) SMOTE oversampling of fault class (generates synthetic fault examples — risky if fault distribution is multi-modal); (3) Anomaly detection (Isolation Forest / One-Class SVM) trained on normal data only; (4) Cost-sensitive learning (`class_weight={'fault': 100}`) to heavily penalise missing a fault. In production I prefer (3) for ISO 26262 compliance since we cannot guarantee exhaustive fault coverage in training data.

---

## Files
- [ml_adas_examples.py](ml_adas_examples.py) — Regression, classification, anomaly detection
