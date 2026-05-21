"""
15_OBJECT_TRACKING — ADAS Multi-Object Tracking Pipeline
ByteTrack-inspired tracker with DeepSORT re-ID features, plus Kalman state.
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
import time


# ============================================================================
# 1. TRACK LIFECYCLE
# ============================================================================

class TrackState(Enum):
    TENTATIVE  = 'tentative'    # New track, not yet confirmed
    CONFIRMED  = 'confirmed'    # Stable track, output to ADAS
    COASTED    = 'coasted'      # Recently missed, Kalman coasting
    DELETED    = 'deleted'      # Too many misses → delete

@dataclass
class Track:
    """Multi-object track with Kalman state."""
    track_id:    int
    state:       np.ndarray      # [x, y, w, h, vx, vy, vw, vh] 8-DOF
    P:           np.ndarray      # 8×8 covariance
    track_state: TrackState
    hits:        int = 1
    misses:      int = 0
    age:         int = 1
    cls_id:      int = 0
    cls_name:    str = ''
    feature:     Optional[np.ndarray] = None  # ReID embedding (512-dim)

# ============================================================================
# 2. KALMAN FILTER — 8-STATE (SORT-style)
# ============================================================================

class KalmanBoxTracker:
    """Kalman filter for single bounding box tracking.
    State: [cx, cy, w, h, vcx, vcy, vw, vh] — centre, size, velocity."""
    
    COUNT = 0
    
    def __init__(self, bbox: np.ndarray, cls_id: int = 0, cls_name: str = ''):
        """Initialise from [x1, y1, x2, y2] bbox."""
        KalmanBoxTracker.COUNT += 1
        self.id       = KalmanBoxTracker.COUNT
        self.cls_id   = cls_id
        self.cls_name = cls_name
        self.hits     = 1
        self.misses   = 0
        self.age      = 1
        
        # Convert to centre format
        cx = (bbox[0]+bbox[2])/2; cy = (bbox[1]+bbox[3])/2
        w  = bbox[2]-bbox[0];     h  = bbox[3]-bbox[1]
        
        # State: [cx, cy, w, h, vcx, vcy, vw, vh]
        self.x = np.array([cx, cy, w, h, 0.0, 0.0, 0.0, 0.0])
        
        # State transition: Constant Velocity
        dt = 1.0
        self.F = np.eye(8)
        self.F[0,4] = self.F[1,5] = self.F[2,6] = self.F[3,7] = dt
        
        # Measurement matrix (observe [cx, cy, w, h])
        self.H = np.eye(4, 8)
        
        # Process noise
        self.Q = np.diag([1.0, 1.0, 1.0, 1.0, 0.1, 0.1, 0.1, 0.1]) * 0.01
        
        # Measurement noise
        self.R = np.diag([1.0, 1.0, 10.0, 10.0])
        
        # Initial covariance
        self.P = np.diag([10.0, 10.0, 10.0, 10.0, 100.0, 100.0, 100.0, 100.0])
    
    def predict(self) -> np.ndarray:
        """Predict state forward one step."""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        self.age += 1
        return self._to_xyxy()
    
    def update(self, bbox: np.ndarray):
        """Update state with new detection [x1, y1, x2, y2]."""
        cx = (bbox[0]+bbox[2])/2; cy = (bbox[1]+bbox[3])/2
        w  = bbox[2]-bbox[0];     h  = bbox[3]-bbox[1]
        z = np.array([cx, cy, w, h])
        
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(8) - K @ self.H) @ self.P
        
        self.hits  += 1
        self.misses = 0
    
    def _to_xyxy(self) -> np.ndarray:
        """Convert state to [x1, y1, x2, y2]."""
        cx, cy, w, h = self.x[:4]
        return np.array([cx-w/2, cy-h/2, cx+w/2, cy+h/2])

# ============================================================================
# 3. IoU AND COST MATRIX
# ============================================================================

def iou_batch(tracks_xyxy: np.ndarray, dets_xyxy: np.ndarray) -> np.ndarray:
    """Compute IoU between all track-detection pairs.
    Returns (M, N) IoU matrix."""
    M, N = len(tracks_xyxy), len(dets_xyxy)
    iou_mat = np.zeros((M, N))
    
    for ti in range(M):
        t = tracks_xyxy[ti]
        for di in range(N):
            d = dets_xyxy[di]
            ix1, ix2 = max(t[0],d[0]), min(t[2],d[2])
            iy1, iy2 = max(t[1],d[1]), min(t[3],d[3])
            inter = max(0,ix2-ix1) * max(0,iy2-iy1)
            area_t = (t[2]-t[0]) * (t[3]-t[1])
            area_d = (d[2]-d[0]) * (d[3]-d[1])
            iou_mat[ti,di] = inter / (area_t + area_d - inter + 1e-6)
    return iou_mat

def cosine_similarity(feat1: np.ndarray, feat2: np.ndarray) -> float:
    """Cosine similarity for ReID feature comparison."""
    norm1 = np.linalg.norm(feat1) + 1e-8
    norm2 = np.linalg.norm(feat2) + 1e-8
    return float(np.dot(feat1, feat2) / (norm1 * norm2))

def greedy_assignment(cost_matrix: np.ndarray, 
                       threshold: float) -> Tuple[List[Tuple[int,int]], List[int], List[int]]:
    """Greedy assignment: maximise cost (use for IoU/similarity).
    Returns: (matched pairs, unmatched track indices, unmatched det indices)"""
    M, N = cost_matrix.shape
    assigned_t = set(); assigned_d = set()
    matches = []
    
    cost_copy = cost_matrix.copy()
    while True:
        idx = np.argmax(cost_copy)
        ti, di = np.unravel_index(idx, cost_copy.shape)
        if cost_copy[ti, di] < threshold:
            break
        matches.append((int(ti), int(di)))
        assigned_t.add(int(ti)); assigned_d.add(int(di))
        cost_copy[ti, :] = -1; cost_copy[:, di] = -1
    
    unmatched_t = [i for i in range(M) if i not in assigned_t]
    unmatched_d = [i for i in range(N) if i not in assigned_d]
    return matches, unmatched_t, unmatched_d

# ============================================================================
# 4. ByteTrack-Inspired MULTI-OBJECT TRACKER
# ============================================================================

class ByteTracker:
    """ByteTrack-style multi-object tracker for ADAS.
    
    Key innovation vs SORT: uses HIGH-confidence detections first,
    then tries to match remaining tracks with LOW-confidence detections
    (ByteTrack, Zhang et al. 2022) — significantly improves recall in
    crowded scenes and during occlusions.
    
    ADAS benefit: recovers partially occluded pedestrians/vehicles
    that only produce low-confidence detections."""
    
    def __init__(self,
                 high_thresh: float = 0.6,
                 low_thresh:  float = 0.1,
                 iou_thresh:  float = 0.3,
                 max_misses:  int   = 30,  # ~1s at 30fps
                 min_hits:    int   = 3):
        self.high_thresh = high_thresh
        self.low_thresh  = low_thresh
        self.iou_thresh  = iou_thresh
        self.max_misses  = max_misses
        self.min_hits    = min_hits
        self._trackers: List[KalmanBoxTracker] = []
        self.frame_id = 0
    
    def update(self, detections: np.ndarray) -> np.ndarray:
        """Process new detections.
        
        detections: (N, 6) [x1, y1, x2, y2, score, cls_id]
        Returns: (M, 7) [x1, y1, x2, y2, track_id, cls_id, age]"""
        self.frame_id += 1
        
        if len(detections) == 0:
            # Coast all trackers
            for trk in self._trackers:
                trk.predict()
                trk.misses += 1
            self._cleanup()
            return self._get_active_tracks()
        
        scores = detections[:, 4]
        
        # Split detections by confidence
        high_mask  = scores >= self.high_thresh
        low_mask   = (scores >= self.low_thresh) & ~high_mask
        high_dets  = detections[high_mask]
        low_dets   = detections[low_mask]
        
        # Predict all existing trackers
        pred_boxes = np.array([t.predict() for t in self._trackers]) \
                     if self._trackers else np.zeros((0, 4))
        
        # === STEP 1: Match high-confidence dets to all tracks ===
        if len(pred_boxes) > 0 and len(high_dets) > 0:
            iou_mat = iou_batch(pred_boxes, high_dets[:, :4])
            matches1, unmatched_t, unmatched_d_high = \
                greedy_assignment(iou_mat, self.iou_thresh)
        else:
            matches1       = []
            unmatched_t    = list(range(len(self._trackers)))
            unmatched_d_high = list(range(len(high_dets)))
        
        for ti, di in matches1:
            self._trackers[ti].update(high_dets[di, :4])
        
        # === STEP 2: Match low-confidence dets to remaining tracks ===
        remaining_track_idx = [i for i in unmatched_t if self._trackers[i].misses == 0]
        if len(remaining_track_idx) > 0 and len(low_dets) > 0:
            rem_boxes = pred_boxes[remaining_track_idx]
            iou_mat2  = iou_batch(rem_boxes, low_dets[:, :4])
            matches2, unmatched_rem, _ = greedy_assignment(iou_mat2, self.iou_thresh)
            for local_ti, di in matches2:
                ti = remaining_track_idx[local_ti]
                self._trackers[ti].update(low_dets[di, :4])
        else:
            unmatched_rem = list(range(len(remaining_track_idx)))
        
        # === STEP 3: Missed tracks ===
        for ti in unmatched_t:
            self._trackers[ti].misses += 1
        
        # === STEP 4: New tracks from unmatched high-conf dets ===
        for di in unmatched_d_high:
            det = high_dets[di]
            new_trk = KalmanBoxTracker(det[:4], int(det[5]), '')
            self._trackers.append(new_trk)
        
        self._cleanup()
        return self._get_active_tracks()
    
    def _cleanup(self):
        self._trackers = [t for t in self._trackers if t.misses <= self.max_misses]
    
    def _get_active_tracks(self) -> np.ndarray:
        """Return confirmed track boxes [x1,y1,x2,y2,id,cls,age]."""
        result = []
        for t in self._trackers:
            if t.hits >= self.min_hits:
                box = t._to_xyxy()
                result.append([*box, t.id, t.cls_id, t.age])
        return np.array(result) if result else np.zeros((0, 7))

# ============================================================================
# 5. RE-ID APPEARANCE MATCHING (DeepSORT component)
# ============================================================================

class AppearanceTracker:
    """Augment IoU-based tracker with ReID appearance features.
    Used for re-association after long occlusions (>30 frames)."""
    
    def __init__(self, feature_dim: int = 128, max_cosine_dist: float = 0.3):
        self.feature_dim    = feature_dim
        self.max_cosine_dist = max_cosine_dist
        self._gallery: Dict[int, np.ndarray] = {}  # track_id → feature EMA
        self._ema_alpha = 0.9  # Exponential moving average for gallery update
    
    def update_gallery(self, track_id: int, feature: np.ndarray):
        """Update appearance gallery for a confirmed track."""
        if track_id in self._gallery:
            self._gallery[track_id] = (self._ema_alpha * self._gallery[track_id] +
                                        (1-self._ema_alpha) * feature)
        else:
            self._gallery[track_id] = feature.copy()
    
    def compute_cost_matrix(self, lost_track_ids: List[int],
                              det_features: List[np.ndarray]) -> np.ndarray:
        """Cosine distance matrix for ReID matching.
        Returns (M_lost, N_dets) — use for second-stage association."""
        M, N = len(lost_track_ids), len(det_features)
        cost = np.ones((M, N))
        for i, tid in enumerate(lost_track_ids):
            if tid in self._gallery:
                for j, feat in enumerate(det_features):
                    cost[i,j] = 1.0 - cosine_similarity(self._gallery[tid], feat)
        return cost

# ============================================================================
# 6. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== ByteTracker ADAS Demo ===\n")
    
    KalmanBoxTracker.COUNT = 0
    tracker = ByteTracker(high_thresh=0.6, low_thresh=0.1,
                           iou_thresh=0.3, min_hits=2)
    
    # Simulate 10 frames with a moving car
    np.random.seed(42)
    for frame_idx in range(10):
        # Car moving from left to right
        x1 = 100 + frame_idx * 8
        detections = np.array([
            [x1, 200, x1+80, 260, 0.9, 0],    # Car (high conf)
            [400, 150, 450, 200, 0.35, 1],     # Pedestrian (low conf)
        ], dtype=np.float32)
        
        tracks = tracker.update(detections)
        
        n_conf = len(tracks)
        print(f"Frame {frame_idx:2d}: {n_conf} confirmed tracks", end='')
        for t in tracks:
            print(f" | ID={int(t[4])} cls={int(t[5])} age={int(t[6])} "
                  f"x=[{t[0]:.0f},{t[2]:.0f}]", end='')
        print()
    
    # Test occlusion — miss frame 10-12
    print("\nSimulating occlusion (3 frames no detection)...")
    for frame_idx in range(10, 13):
        tracks = tracker.update(np.zeros((0,6)))
        print(f"Frame {frame_idx}: {len(tracks)} confirmed tracks (coasting)")
    
    # Re-appear
    x1 = 100 + 13 * 8
    tracks = tracker.update(np.array([[x1, 200, x1+80, 260, 0.88, 0]], dtype=np.float32))
    print(f"\nFrame 13 (reappear): {len(tracks)} tracks, IDs: {[int(t[4]) for t in tracks]}")
