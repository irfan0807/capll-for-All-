# 01 — Mathematics for ADAS AI

> **Level:** Principal ADAS AI Engineer  
> **Why it matters:** Every CNN layer, Kalman filter, and SLAM algorithm is applied linear algebra + probability + calculus. Understanding the maths = debugging ability that differentiates senior from junior engineers.

---

## 01.1 Linear Algebra for Neural Networks

### Vectors and Matrices in ADAS Context

```python
import numpy as np

# === 1. Camera Projection Matrix ===
# 3D world point → 2D image pixel
# P = K @ [R | t]   (3×4 projection matrix)
# K = camera intrinsic matrix (3×3)

K = np.array([
    [800.0,   0.0, 640.0],   # fx, 0, cx
    [  0.0, 800.0, 360.0],   # 0, fy, cy
    [  0.0,   0.0,   1.0]    # homogeneous
])

# Rotation + translation (extrinsic: camera in world frame)
R = np.eye(3)           # Identity: camera aligned with world
t = np.array([0, 0, 5]) # Camera 5m in front of vehicle origin

# Project a 3D radar target (X=10m, Y=0, Z=0 in vehicle frame) to image
X_world = np.array([10.0, 0.0, 0.0, 1.0])  # homogeneous
Rt = np.hstack([R, t.reshape(3,1)])          # [R|t] 3×4
P = K @ Rt                                   # 3×4 projection matrix
x_hom = P @ X_world                          # 3-vector (homogeneous)
pixel = x_hom[:2] / x_hom[2]               # Divide by w
print(f"Target at (10m, 0, 0) projects to pixel: {pixel}")
# Output: pixel ~= [640, 760] — image centre-right area

# === 2. Homogeneous Transformation (Sensor to Sensor) ===
# T_radar_to_camera: 4×4 rigid body transform
# Used in sensor fusion to project radar detections into camera frame

def make_transform(roll=0, pitch=0, yaw=0, x=0, y=0, z=0):
    """Create 4×4 homogeneous transform from Euler angles + translation."""
    cr, sr = np.cos(roll),  np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw),   np.sin(yaw)
    
    R = np.array([
        [cy*cp,  cy*sp*sr - sy*cr,  cy*sp*cr + sy*sr],
        [sy*cp,  sy*sp*sr + cy*cr,  sy*sp*cr - cy*sr],
        [  -sp,            cp*sr,             cp*cr ]
    ])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3,  3] = [x, y, z]
    return T

# Radar is 0.5m below and 1.2m behind the camera
T_radar_to_camera = make_transform(yaw=0, x=1.2, y=0, z=0.5)
radar_point = np.array([45.0, 0.5, 0.0, 1.0])  # 45m ahead, 0.5m right
camera_point = T_radar_to_camera @ radar_point
print(f"Radar point in camera frame: {camera_point[:3]}")
```

### Eigenvalues — PCA for Point Cloud

```python
def pca_3d(points: np.ndarray):
    """PCA on 3D point cloud — finds principal axes of object shape.
    Used in LiDAR to fit oriented bounding boxes."""
    centered = points - points.mean(axis=0)
    cov = (centered.T @ centered) / len(points)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # Sort by descending eigenvalue (largest variance first)
    idx = np.argsort(eigenvalues)[::-1]
    return eigenvalues[idx], eigenvectors[:, idx]

# Simulated vehicle point cloud (elongated in X direction)
np.random.seed(42)
vehicle_points = np.random.randn(200, 3) * [2.0, 0.8, 0.6]  # 4m×1.6m×1.2m
eigenvalues, axes = pca_3d(vehicle_points)
print(f"Object extents (eigenvalue ∝ variance): {np.sqrt(eigenvalues)*2:.2f}")
```

---

## 01.2 Calculus for Neural Networks

### Backpropagation — Full Derivation

```
Neural network: loss L = f(W₁, W₂, ...)
Gradient descent update: W ← W - α × ∂L/∂W

Chain rule (the heart of backprop):
  ∂L/∂W₁ = ∂L/∂a₂ × ∂a₂/∂z₂ × ∂z₂/∂a₁ × ∂a₁/∂z₁ × ∂z₁/∂W₁

For a 2-layer network (ADAS lane offset regressor):
  z₁ = W₁ × x         → linear transform
  a₁ = ReLU(z₁)       → activation
  z₂ = W₂ × a₁
  ŷ = z₂               → lane offset prediction
  L = 0.5 × (y - ŷ)²  → MSE loss
  
  ∂L/∂W₂ = -(y - ŷ) × a₁ᵀ   ← direct, clean
  ∂L/∂W₁ = -(y - ŷ) × W₂ᵀ × ReLU'(z₁) × xᵀ  ← chain rule
```

```python
import numpy as np

def relu(x): return np.maximum(0, x)
def relu_grad(x): return (x > 0).astype(float)

def manual_backprop_demo():
    """Manual backprop for a 2-layer lane offset regressor."""
    np.random.seed(0)
    # Input: [image_feature1, image_feature2, vehicle_speed]
    x = np.array([[0.5, -0.3, 100.0/120.0]]).T  # 3×1
    y = np.array([[0.15]])                         # true lane offset = 0.15m
    
    W1 = np.random.randn(4, 3) * 0.1  # 4 hidden units
    W2 = np.random.randn(1, 4) * 0.1  # 1 output
    
    # Forward pass
    z1 = W1 @ x          # 4×1
    a1 = relu(z1)         # 4×1
    y_hat = W2 @ a1       # 1×1
    loss = 0.5 * (y - y_hat)**2
    
    # Backward pass
    dL_dz2 = -(y - y_hat)           # 1×1
    dL_dW2 = dL_dz2 @ a1.T          # 1×4
    dL_da1 = W2.T @ dL_dz2          # 4×1
    dL_dz1 = dL_da1 * relu_grad(z1) # 4×1 (element-wise, not matmul)
    dL_dW1 = dL_dz1 @ x.T           # 4×3
    
    print(f"Loss: {loss.item():.6f}")
    print(f"dL/dW2 shape: {dL_dW2.shape}, max: {dL_dW2.max():.4f}")
    print(f"dL/dW1 shape: {dL_dW1.shape}, max: {dL_dW1.max():.4f}")
    return dL_dW1, dL_dW2

manual_backprop_demo()
```

---

## 01.3 Probability & Bayesian Inference for ADAS

### Bayes Theorem — Object Classification

```
P(car | detections) = P(detections | car) × P(car) / P(detections)

Where:
  P(car | detections) = posterior: probability it IS a car given what sensors see
  P(detections | car) = likelihood: how likely are these sensor readings if it's a car
  P(car)              = prior: base rate of cars in this scene type
  P(detections)       = evidence (normalisation constant)

ADAS application: radar + camera joint detection
  P(object=car | radar_range=45m, camera_bbox=present) = 
      P(radar=45m | car) × P(bbox | car) × P(car)
    ────────────────────────────────────────────────
               P(radar=45m, bbox=present)
```

```python
def bayesian_object_classifier(radar_range_m, camera_confidence):
    """Fuse radar and camera probabilities using Bayes.
    Simplified version of what production fusion ECUs do."""
    
    # Priors from scene type (highway: lots of cars)
    P_car    = 0.60
    P_truck  = 0.20
    P_moto   = 0.10
    P_pedestrian = 0.10
    
    # Likelihoods from radar range (simplified Gaussian model)
    # Real ECU: use learned mixture models from radar characterisation data
    def radar_likelihood(range_m, obj_type):
        # Trucks are detected farther (larger RCS), pedestrians less reliably
        if obj_type == 'car':       return np.exp(-((range_m - 50)**2) / 800)
        if obj_type == 'truck':     return np.exp(-((range_m - 55)**2) / 1200) * 1.3
        if obj_type == 'moto':      return np.exp(-((range_m - 50)**2) / 800)  * 0.6
        if obj_type == 'pedestrian':return np.exp(-((range_m - 50)**2) / 800)  * 0.1
        return 0.0
    
    # Camera likelihoods from confidence score
    def camera_likelihood(conf, obj_type):
        if obj_type == 'car':       return conf * 0.95
        if obj_type == 'truck':     return conf * 0.90
        if obj_type == 'moto':      return conf * 0.70
        if obj_type == 'pedestrian':return (1-conf) * 0.85
        return 0.0
    
    posteriors = {}
    for obj, prior in [('car',P_car),('truck',P_truck),('moto',P_moto),('pedestrian',P_pedestrian)]:
        posteriors[obj] = radar_likelihood(radar_range_m, obj) * \
                          camera_likelihood(camera_confidence, obj) * prior
    
    # Normalise
    total = sum(posteriors.values())
    return {k: v/total for k, v in posteriors.items()}

result = bayesian_object_classifier(radar_range_m=48.0, camera_confidence=0.85)
for cls, prob in sorted(result.items(), key=lambda x: -x[1]):
    print(f"  {cls:12s}: {prob:.2%}")
```

---

## 01.4 Kalman Filter — The Core of Sensor Fusion

### Mathematical Derivation

```
State:       x = [range, range_rate]ᵀ   (radar tracking)
Measurement: z = [range_measured]        (noisy radar return)

System model (constant velocity):
  F = [[1, dt],   Process noise: Q = [[σ_a²×dt⁴/4, σ_a²×dt³/2],
       [0,  1]]                        [σ_a²×dt³/2, σ_a²×dt²  ]]

Measurement model:
  H = [[1, 0]]   R = σ_r² (range measurement noise variance)

Predict step:
  x̂⁻ = F × x̂
  P⁻ = F × P × Fᵀ + Q

Update step:
  K = P⁻ × Hᵀ × (H × P⁻ × Hᵀ + R)⁻¹   (Kalman gain)
  x̂ = x̂⁻ + K × (z - H × x̂⁻)           (innovation)
  P = (I - K × H) × P⁻                   (covariance update)
```

```python
class KalmanFilter2D:
    """1D Kalman Filter: state = [range, range_rate].
    Used in ACC radar tracking."""
    
    def __init__(self, dt: float = 0.05):
        self.dt = dt
        # State transition: constant velocity
        self.F = np.array([[1, dt], [0, 1]])
        # Measurement matrix: only range is observed
        self.H = np.array([[1, 0]])
        # Process noise (vehicle acceleration uncertainty σ_a = 1 m/s²)
        sa = 1.0
        self.Q = sa**2 * np.array([[dt**4/4, dt**3/2],
                                    [dt**3/2, dt**2  ]])
        # Measurement noise (radar range σ = 0.3m)
        self.R = np.array([[0.09]])
        # Initial state and covariance
        self.x = np.array([[80.0], [0.0]])  # 80m, stationary
        self.P = np.eye(2) * 10.0

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x.copy()

    def update(self, z_range: float):
        z = np.array([[z_range]])
        y  = z - self.H @ self.x                           # Innovation
        S  = self.H @ self.P @ self.H.T + self.R           # Innovation covariance
        K  = self.P @ self.H.T @ np.linalg.inv(S)          # Kalman gain
        self.x = self.x + K @ y
        self.P = (np.eye(2) - K @ self.H) @ self.P
        return self.x.copy()

# Simulation: vehicle approaching at 10 m/s
kf = KalmanFilter2D(dt=0.05)
print(f"{'t[s]':>5} {'True[m]':>8} {'Noisy[m]':>9} {'KF[m]':>7} {'Rate[m/s]':>10}")
for i in range(20):
    t = i * 0.05
    true_range = 80.0 - 10.0 * t
    noisy_meas = true_range + np.random.normal(0, 0.3)
    kf.predict()
    state = kf.update(noisy_meas)
    print(f"{t:5.2f} {true_range:8.2f} {noisy_meas:9.2f} {state[0,0]:7.2f} {state[1,0]:10.2f}")
```

---

## 01.5 Loss Functions for ADAS Neural Networks

```python
import torch
import torch.nn.functional as F

# === Focal Loss — for object detection with class imbalance ===
# ADAS problem: 1000× more background than objects in anchor-based detectors
# Standard CE: overfit to easy negatives → poor recall
# Focal: down-weights easy examples, focus on hard positives

def focal_loss(pred, target, alpha=0.25, gamma=2.0):
    """Focal loss for object detection. Used in RetinaNet, FCOS."""
    bce = F.binary_cross_entropy_with_logits(pred, target, reduction='none')
    pt = torch.exp(-bce)  # Probability of correct class
    focal = alpha * (1 - pt)**gamma * bce
    return focal.mean()

# === IoU Loss — for bounding box regression ===
def iou_loss(pred_box, target_box):
    """Generalised IoU loss. Used in YOLO, SSD for bbox regression."""
    # pred_box: [x1, y1, x2, y2]
    inter_x1 = torch.max(pred_box[0], target_box[0])
    inter_y1 = torch.max(pred_box[1], target_box[1])
    inter_x2 = torch.min(pred_box[2], target_box[2])
    inter_y2 = torch.min(pred_box[3], target_box[3])
    
    inter_area = (inter_x2 - inter_x1).clamp(0) * (inter_y2 - inter_y1).clamp(0)
    pred_area  = (pred_box[2] - pred_box[0]) * (pred_box[3] - pred_box[1])
    target_area = (target_box[2] - target_box[0]) * (target_box[3] - target_box[1])
    union = pred_area + target_area - inter_area
    iou = inter_area / (union + 1e-6)
    return 1.0 - iou  # Loss: 0 = perfect

# === Smooth L1 — robust to outliers for regression ===
# Used in: LKA lane offset prediction, ACC distance regression
# Less sensitive to large errors than L2 (important for noisy sensor data)
# For |error| < 1: 0.5×error²   (behaves like L2, smooth gradient)
# For |error| ≥ 1: |error| - 0.5  (behaves like L1, robust to outliers)
smooth_l1 = F.smooth_l1_loss
```

---

## 01.6 Interview Questions

**L1:**
1. What is the dot product and what does it represent geometrically?
2. What is an eigenvalue/eigenvector? Give an automotive example.
3. What is gradient descent and what does the learning rate control?

**L2:**
4. Derive the Kalman filter update step from Bayes theorem.
5. What is the difference between L1, L2, and Smooth L1 loss? When do you use each in ADAS?
6. Why is focal loss better than cross-entropy for object detection?
7. Explain the difference between covariance matrix P in Kalman filter before and after the update step.

**L3:**
8. A radar Kalman filter diverges after 5 seconds. What could be causing this? How do you fix it?
9. Derive the Extended Kalman Filter update for a radar that measures range and azimuth (nonlinear measurement model).
10. Explain why the process noise Q in a Kalman filter must be tuned per-platform and how you do it empirically.
