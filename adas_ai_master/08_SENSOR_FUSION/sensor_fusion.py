"""
08_SENSOR_FUSION — Extended Kalman Filter + Deep Fusion
Camera + Radar + LiDAR fusion for ADAS object tracking
"""

import numpy as np
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum

# ============================================================================
# DATA TYPES
# ============================================================================

class SensorType(Enum):
    CAMERA = "camera"
    RADAR  = "radar"
    LIDAR  = "lidar"

@dataclass
class Detection:
    sensor:    SensorType
    x:         float    # Longitudinal position (m)
    y:         float    # Lateral position (m)
    vx:        float    # Longitudinal velocity (m/s)
    vy:        float    # Lateral velocity (m/s)
    width:     float    # Object width (m)
    length:    float    # Object length (m)
    confidence: float  # Detection confidence [0, 1]
    cls:       str      # Object class ('car', 'pedestrian', etc.)
    timestamp_ms: float

@dataclass
class TrackedObject:
    track_id:  int
    state:     np.ndarray  # [x, y, vx, vy] — 4-state vector
    P:         np.ndarray  # 4×4 covariance matrix
    age_frames: int
    hits:       int
    misses:     int
    cls:        str
    last_update_ms: float
    source_sensors: List[SensorType] = field(default_factory=list)

# ============================================================================
# 1. STANDARD KALMAN FILTER (Linear — Radar range + range_rate)
# ============================================================================

class RadarKalmanFilter:
    """1D Kalman filter for radar range tracking.
    State: [range_m, range_rate_mps]
    Measurement: range_m only (from single-beam radar)
    
    Used in ACC: smooth radar range measurements for setpoint control."""
    
    def __init__(self, dt: float = 0.05):
        self.dt = dt
        
        # State transition: x_k+1 = F * x_k
        self.F = np.array([[1, dt],
                           [0,  1]], dtype=np.float64)
        
        # Measurement model: z = H * x (only range observed)
        self.H = np.array([[1, 0]], dtype=np.float64)
        
        # Process noise (tune for vehicle dynamics)
        sigma_a = 2.0  # ±2 m/s² acceleration uncertainty
        self.Q = sigma_a**2 * np.array([[dt**4/4, dt**3/2],
                                         [dt**3/2, dt**2]])
        
        # Measurement noise: radar range std ~0.1m
        self.R = np.array([[0.01]])  # 0.1m std → 0.01 variance
        
        # Initial state
        self.x = np.zeros((2, 1))
        self.P = np.eye(2) * 100.0   # Large initial uncertainty

    def init(self, range_m: float, range_rate_mps: float = 0.0):
        self.x = np.array([[range_m], [range_rate_mps]])
        self.P = np.diag([1.0, 4.0])  # Initial uncertainty: ±1m, ±2m/s

    def predict(self):
        """Predict next state."""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return float(self.x[0])

    def update(self, z_range: float):
        """Update with new measurement."""
        z = np.array([[z_range]])
        y = z - self.H @ self.x                           # Innovation
        S = self.H @ self.P @ self.H.T + self.R           # Innovation covariance
        K = self.P @ self.H.T @ np.linalg.inv(S)         # Kalman gain
        self.x = self.x + K @ y
        self.P = (np.eye(2) - K @ self.H) @ self.P
        return float(self.x[0]), float(self.x[1])          # (range, range_rate)

    @property
    def range_m(self) -> float:     return float(self.x[0])
    @property
    def range_rate_mps(self) -> float: return float(self.x[1])

# ============================================================================
# 2. EXTENDED KALMAN FILTER (Nonlinear — Camera + Radar fusion)
# ============================================================================

class ExtendedKalmanFilter:
    """EKF for camera + radar fusion.
    State: [x, y, vx, vy] — 2D position + velocity in vehicle frame
    
    Camera: provides [x, y] (bearing/position, no velocity)
    Radar:  provides [range, bearing, range_rate] (polar coordinates)
    
    The radar measurement is nonlinear → requires Jacobian linearisation (EKF)."""
    
    def __init__(self, dt: float = 0.05):
        self.dt  = dt
        self.dim = 4
        
        # State transition (CV model: Constant Velocity)
        self.F = np.array([
            [1, 0, dt, 0],
            [0, 1,  0, dt],
            [0, 0,  1,  0],
            [0, 0,  0,  1]
        ], dtype=np.float64)
        
        # Process noise (tune: higher = trust measurements more)
        sigma_ax, sigma_ay = 1.5, 1.0  # m/s² std
        dt2 = dt**2; dt3 = dt**3; dt4 = dt**4
        self.Q = np.array([
            [dt4/4*sigma_ax**2, 0, dt3/2*sigma_ax**2, 0],
            [0, dt4/4*sigma_ay**2, 0, dt3/2*sigma_ay**2],
            [dt3/2*sigma_ax**2, 0, dt2*sigma_ax**2, 0],
            [0, dt3/2*sigma_ay**2, 0, dt2*sigma_ay**2]
        ])
        
        # Camera measurement noise: [x, y] std = 0.3m
        self.R_camera = np.diag([0.09, 0.09])
        
        # Radar measurement noise: [range, bearing, range_rate] std
        self.R_radar = np.diag([0.09, 0.0003, 0.09])  # ~0.3m, ~1deg, ~0.3m/s
        
        self.x = np.zeros(4)
        self.P = np.eye(4) * 10.0
    
    def init(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0):
        self.x = np.array([x, y, vx, vy])
        self.P = np.diag([1.0, 1.0, 4.0, 4.0])
    
    def predict(self):
        """Linear prediction step (CV model)."""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
    
    def update_camera(self, z: np.ndarray):
        """Update with camera [x, y] measurement."""
        H = np.array([[1,0,0,0],[0,1,0,0]], dtype=np.float64)  # Linear
        self._update(z, H, self.R_camera)
    
    def update_radar(self, z: np.ndarray):
        """Update with radar [range, bearing, range_rate] measurement.
        Requires Jacobian of nonlinear h(x) = [range, atan2, range_rate]."""
        px, py, vx, vy = self.x
        rho = np.sqrt(px**2 + py**2)
        
        if rho < 0.001:
            return   # Avoid division by zero at origin
        
        # Predicted radar measurement h(x)
        h_x = np.array([
            rho,
            np.arctan2(py, px),
            (px*vx + py*vy) / rho
        ])
        
        # Jacobian of h(x) — linearise around current state
        H = np.array([
            [px/rho,          py/rho,          0,      0],
            [-py/rho**2,      px/rho**2,       0,      0],
            [py*(vx*py-vy*px)/rho**3, px*(vy*px-vx*py)/rho**3, px/rho, py/rho]
        ])
        
        # Innovation — normalise angle difference to [-π, π]
        y = z - h_x
        y[1] = (y[1] + np.pi) % (2*np.pi) - np.pi
        
        self._update(y, H, self.R_radar, pre_computed_innovation=True)
    
    def _update(self, z_or_y, H, R, pre_computed_innovation=False):
        """Standard Kalman update step."""
        y = z_or_y if pre_computed_innovation else z_or_y - H @ self.x
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(self.dim) - K @ H) @ self.P
    
    @property
    def position(self) -> Tuple[float, float]:
        return float(self.x[0]), float(self.x[1])
    @property
    def velocity(self) -> Tuple[float, float]:
        return float(self.x[2]), float(self.x[3])

# ============================================================================
# 3. MULTI-OBJECT TRACKER (SORT-style: IoU + Kalman)
# ============================================================================

def iou_2d(box1: np.ndarray, box2: np.ndarray) -> float:
    """IoU between two [x_centre, y_centre, w, h] boxes."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    ax1, ax2 = x1 - w1/2, x1 + w1/2
    ay1, ay2 = y1 - h1/2, y1 + h1/2
    bx1, bx2 = x2 - w2/2, x2 + w2/2
    by1, by2 = y2 - h2/2, y2 + h2/2
    
    ix1, ix2 = max(ax1, bx1), min(ax2, bx2)
    iy1, iy2 = max(ay1, by1), min(ay2, by2)
    inter = max(0, ix2-ix1) * max(0, iy2-iy1)
    union = w1*h1 + w2*h2 - inter
    return inter / (union + 1e-6)

class MultiObjectTracker:
    """SORT (Simple Online and Realtime Tracking) with Kalman Filter.
    Used for: object tracking between detection frames.
    
    Flow:
    1. New detections arrive (from CNN)
    2. Match detections to existing tracks via IoU
    3. Update matched tracks with EKF
    4. Kill tracks with too many missed detections
    5. Create new tracks for unmatched detections
    """
    
    def __init__(self, max_misses: int = 3, min_hits: int = 3,
                 iou_threshold: float = 0.3):
        self.max_misses    = max_misses
        self.min_hits      = min_hits
        self.iou_threshold = iou_threshold
        self._tracks:  List[TrackedObject] = []
        self._next_id  = 0
        self.dt        = 0.05
    
    def update(self, detections: List[Detection],
               timestamp_ms: float) -> List[TrackedObject]:
        """
        Main update: associate detections to tracks, return confirmed tracks.
        Returns only tracks with hits >= min_hits (confirmed objects).
        """
        # Predict all tracks forward
        for track in self._tracks:
            # Simple constant-velocity predict
            track.state[0] += track.state[2] * self.dt
            track.state[1] += track.state[3] * self.dt
            track.age_frames += 1
        
        # Build cost matrix (1 - IoU)
        n_tracks = len(self._tracks)
        n_dets   = len(detections)
        
        assigned_tracks = set()
        assigned_dets   = set()
        
        if n_tracks > 0 and n_dets > 0:
            # IoU matrix
            iou_mat = np.zeros((n_tracks, n_dets))
            for ti, track in enumerate(self._tracks):
                for di, det in enumerate(detections):
                    t_box = np.array([track.state[0], track.state[1], 3.0, 1.5])
                    d_box = np.array([det.x, det.y, det.length, det.width])
                    iou_mat[ti, di] = iou_2d(t_box, d_box)
            
            # Greedy matching (Hungarian algorithm for production)
            while True:
                idx = np.argmax(iou_mat)
                ti, di = np.unravel_index(idx, iou_mat.shape)
                if iou_mat[ti, di] < self.iou_threshold:
                    break
                det = detections[di]
                self._tracks[ti].state[0] = det.x
                self._tracks[ti].state[1] = det.y
                self._tracks[ti].state[2] = det.vx
                self._tracks[ti].state[3] = det.vy
                self._tracks[ti].hits   += 1
                self._tracks[ti].misses  = 0
                self._tracks[ti].last_update_ms = timestamp_ms
                assigned_tracks.add(ti)
                assigned_dets.add(di)
                iou_mat[ti, :] = -1
                iou_mat[:, di] = -1
        
        # Unmatched detections → new tracks
        for di, det in enumerate(detections):
            if di not in assigned_dets:
                new_track = TrackedObject(
                    track_id=self._next_id,
                    state=np.array([det.x, det.y, det.vx, det.vy]),
                    P=np.eye(4) * 10.0,
                    age_frames=0, hits=1, misses=0,
                    cls=det.cls,
                    last_update_ms=timestamp_ms,
                    source_sensors=[det.sensor]
                )
                self._tracks.append(new_track)
                self._next_id += 1
        
        # Unmatched tracks → increment miss counter
        for ti in range(n_tracks):
            if ti not in assigned_tracks:
                self._tracks[ti].misses += 1
        
        # Remove dead tracks
        self._tracks = [t for t in self._tracks if t.misses <= self.max_misses]
        
        # Return confirmed tracks only
        return [t for t in self._tracks if t.hits >= self.min_hits]

# ============================================================================
# 4. COVARIANCE INTERSECTION — Safe fusion without cross-correlation
# ============================================================================

def covariance_intersection(states: List[np.ndarray],
                             covariances: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    """Covariance Intersection fusion: consistent (conservative) fusion when 
    cross-correlations between sensor estimates are unknown.
    
    Used when camera and radar are not time-synchronised, or when
    a centralised fusion architecture is replaced by distributed sensors.
    
    Finds optimal weights w ∈ [0,1] minimising |P_fused|."""
    n = len(states)
    assert n >= 2
    
    best_w = None
    best_trace = float('inf')
    
    # Grid search for optimal w (2-sensor case)
    for w in np.linspace(0, 1, 101):
        try:
            P_inv = w * np.linalg.inv(covariances[0]) + \
                    (1-w) * np.linalg.inv(covariances[1])
            P = np.linalg.inv(P_inv)
            tr = np.trace(P)
            if tr < best_trace:
                best_trace = tr
                best_w = w
        except np.linalg.LinAlgError:
            continue
    
    w = best_w if best_w is not None else 0.5
    P_inv  = w * np.linalg.inv(covariances[0]) + (1-w) * np.linalg.inv(covariances[1])
    P_fused = np.linalg.inv(P_inv)
    x_fused = P_fused @ (w * np.linalg.inv(covariances[0]) @ states[0] +
                          (1-w) * np.linalg.inv(covariances[1]) @ states[1])
    return x_fused, P_fused

# ============================================================================
# 5. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== Sensor Fusion Demo ===\n")
    
    # 1. Radar KF (1D range tracking)
    kf = RadarKalmanFilter(dt=0.05)
    kf.init(range_m=50.0, range_rate_mps=-10.0)
    
    true_range = 50.0
    print("Radar KF (range tracking, -10 m/s approach):")
    for step in range(5):
        true_range += -10.0 * 0.05  # Vehicle approaching at -10 m/s
        noisy_meas  = true_range + np.random.normal(0, 0.1)
        pred_range  = kf.predict()
        filt_range, filt_rate = kf.update(noisy_meas)
        print(f"  Step {step}: true={true_range:.2f}m | meas={noisy_meas:.2f}m | "
              f"KF={filt_range:.2f}m | rate={filt_rate:.2f}m/s")
    
    # 2. EKF camera + radar fusion
    print("\nEKF Camera+Radar Fusion:")
    ekf = ExtendedKalmanFilter(dt=0.05)
    ekf.init(x=30.0, y=1.5, vx=-8.0, vy=0.0)
    
    for step in range(3):
        ekf.predict()
        # Camera update (2D position)
        cam_meas = np.array([ekf.x[0] + np.random.normal(0, 0.3),
                             ekf.x[1] + np.random.normal(0, 0.3)])
        ekf.update_camera(cam_meas)
        # Radar update (range, bearing, range_rate)
        px, py, vx, vy = ekf.x
        rho = np.sqrt(px**2 + py**2)
        radar_meas = np.array([rho + np.random.normal(0, 0.1),
                               np.arctan2(py, px) + np.random.normal(0, 0.01),
                               (px*vx + py*vy)/rho + np.random.normal(0, 0.1)])
        ekf.update_radar(radar_meas)
        pos = ekf.position
        vel = ekf.velocity
        print(f"  Step {step}: pos=({pos[0]:.2f},{pos[1]:.2f})m "
              f"vel=({vel[0]:.2f},{vel[1]:.2f})m/s")
    
    # 3. Multi-object tracker
    print("\nMulti-Object Tracker:")
    tracker = MultiObjectTracker(max_misses=3, min_hits=2)
    
    timestamp = 0.0
    for frame_idx in range(6):
        dets = [
            Detection(SensorType.CAMERA, x=30.0-frame_idx*0.5, y=1.5,
                      vx=-10.0, vy=0.0, width=1.8, length=4.5,
                      confidence=0.92, cls='car', timestamp_ms=timestamp),
        ]
        confirmed = tracker.update(dets, timestamp)
        print(f"  Frame {frame_idx}: {len(confirmed)} confirmed tracks")
        timestamp += 50.0
