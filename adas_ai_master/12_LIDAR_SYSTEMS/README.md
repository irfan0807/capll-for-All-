# 12 — LiDAR Systems for ADAS

## Overview
LiDAR (Light Detection And Ranging) point cloud processing for 3D object detection and mapping. Covers mechanical vs solid-state LiDAR, point cloud representation, and deep learning on 3D data.

---

## 1. LiDAR Types in Automotive

| Type | Mechanism | Range | Angular Res | Cost | Status |
|------|-----------|-------|------------|------|--------|
| Mechanical spinning | Rotating mirror array | 100-300m | 0.1-0.33° | $$$$ | Waymo, Uber legacy |
| MEMs (solid-state) | Micro mirror MEMS | 30-100m | Medium | $$ | Innoviz, Continental |
| Flash LiDAR | Full-field flash | 10-50m | Low | $ | Near-range only |
| FMCW LiDAR | Coherent frequency-mod | 200-500m | Very high | $$$$$ | Aeva, Luminar |

**Automotive grade LiDARs:**
- Velodyne VLP-32C: 32 channels, 200m, 360° (mechanical)
- Luminar Iris: 250m, 1550nm (eye-safe), solid-state-like
- Innoviz Pro: MEMS, 200m, front-only
- Valeo Scala: 145m, 145° FOV (first mass-produced AV LiDAR)

---

## 2. Point Cloud Structure

```python
import numpy as np
from dataclasses import dataclass

@dataclass
class PointCloud:
    """LiDAR point cloud — N points with attributes."""
    xyz:       np.ndarray  # (N, 3) float32: [x, y, z] metres
    intensity: np.ndarray  # (N,)   float32: [0, 1] reflectivity
    ring:      np.ndarray  # (N,)   int16:   laser ring/channel index
    timestamp: np.ndarray  # (N,)   float64: per-point timestamp (µs)
    
    @property
    def N(self) -> int:
        return len(self.xyz)
    
    def range_filter(self, min_r: float = 1.0, max_r: float = 100.0) -> 'PointCloud':
        """Remove points outside range envelope."""
        r = np.linalg.norm(self.xyz, axis=1)
        mask = (r >= min_r) & (r <= max_r)
        return PointCloud(self.xyz[mask], self.intensity[mask],
                          self.ring[mask], self.timestamp[mask])
    
    def ground_removal(self, z_threshold: float = -1.5) -> 'PointCloud':
        """Simple height-based ground removal (ECU-grade, no RANSAC)."""
        mask = self.xyz[:, 2] > z_threshold
        return PointCloud(self.xyz[mask], self.intensity[mask],
                          self.ring[mask], self.timestamp[mask])
    
    def voxel_downsample(self, voxel_size: float = 0.1) -> np.ndarray:
        """Voxel grid downsampling: reduce point density for inference.
        Returns downsampled xyz."""
        voxel_idx = np.floor(self.xyz / voxel_size).astype(np.int32)
        _, unique = np.unique(voxel_idx, axis=0, return_index=True)
        return self.xyz[unique]
```

---

## 3. 3D Object Detection Methods

### Method 1: PointPillars (Fastest, ECU-deployable)

```
Point cloud
     │
     ▼
Pillar Feature Net (per-pillar PointNet)
     │ Pseudo-image: (C, H, W) BEV grid
     ▼
2D Backbone (lightweight CNN)
     │
     ▼
Single-Shot Detection Head (class + bbox + rotation)
     │
     ▼
Oriented 3D boxes
```

**Key insight:** PointPillars avoids 3D convolutions by pillarising the point cloud into a 2D BEV image, then applying fast 2D CNN. Inference: ~2ms on GPU vs 10ms for 3D convolution methods.

### Method 2: VoxelNet / Second (More accurate)
- Voxelise 3D space (0.05m voxels)
- Sparse 3D convolutions (only non-empty voxels)
- 3D RPN head

---

## 4. Point Cloud Preprocessing for NN

```python
def preprocess_for_pointpillars(xyz: np.ndarray,
                                  intensity: np.ndarray,
                                  voxel_size: float = 0.16,
                                  x_range=(-70.4, 70.4),
                                  y_range=(-40.0, 40.0),
                                  z_range=(-3.0, 1.0),
                                  max_points_per_pillar: int = 100,
                                  max_pillars: int = 12000) -> dict:
    """PointPillars preprocessing: voxelise point cloud into pillars.
    Based on Lang et al., 2019 (original PointPillars paper)."""
    
    # Filter to detection range
    mask = ((xyz[:, 0] >= x_range[0]) & (xyz[:, 0] < x_range[1]) &
            (xyz[:, 1] >= y_range[0]) & (xyz[:, 1] < y_range[1]) &
            (xyz[:, 2] >= z_range[0]) & (xyz[:, 2] < z_range[1]))
    xyz, intensity = xyz[mask], intensity[mask]
    
    # Compute pillar indices
    px = ((xyz[:, 0] - x_range[0]) / voxel_size).astype(np.int32)
    py = ((xyz[:, 1] - y_range[0]) / voxel_size).astype(np.int32)
    
    # Group points into pillars (simplified — no tensor shuffle)
    pillars: dict = {}
    for i, (x_i, y_i) in enumerate(zip(px, py)):
        key = (x_i, y_i)
        if key not in pillars:
            pillars[key] = []
        if len(pillars[key]) < max_points_per_pillar:
            pillars[key].append(np.array([xyz[i, 0], xyz[i, 1], xyz[i, 2],
                                           intensity[i]]))
    
    return {
        'pillars': pillars,
        'num_pillars': min(len(pillars), max_pillars),
        'voxel_size': voxel_size,
        'x_range': x_range,
        'y_range': y_range
    }
```

---

## 5. LiDAR Calibration

**LiDAR-Camera extrinsic calibration:**
- Use a calibration board (checkerboard or AprilTag) visible in both sensors
- Minimise reprojection error: $T_{LC}$ transforms LiDAR points to camera frame

```python
def project_lidar_to_camera(xyz_lidar: np.ndarray, T_lidar_to_cam: np.ndarray,
                              K: np.ndarray, dist: np.ndarray) -> np.ndarray:
    """Project LiDAR points onto camera image for calibration verification.
    
    T_lidar_to_cam: 4×4 extrinsic matrix [R|t]
    K: 3×3 camera intrinsics
    Returns: (N, 2) image coordinates of projected LiDAR points"""
    import cv2
    N = len(xyz_lidar)
    xyz_h = np.hstack([xyz_lidar, np.ones((N, 1))])   # (N, 4) homogeneous
    xyz_cam = (T_lidar_to_cam @ xyz_h.T).T             # (N, 4) camera frame
    
    # Keep only points in front of camera
    mask = xyz_cam[:, 2] > 0.1
    pts_cam = xyz_cam[mask, :3]
    
    img_pts, _ = cv2.projectPoints(pts_cam, np.zeros(3), np.zeros(3), K, dist)
    return img_pts.reshape(-1, 2)
```

---

## 6. LiDAR Data Formats

| Format | File | Use |
|--------|------|-----|
| KITTI binary | `.bin` float32 (x,y,z,intensity) | Training, benchmarks |
| NuScenes | JSON + `.pcd.bin` | Industry standard |
| Waymo TFRecord | Protocol Buffer | Waymo Open Dataset |
| ROS2 | `sensor_msgs/PointCloud2` | Real-time systems |
| PCD | ASCII/binary | Open3D, PCL |

---

## 7. Performance vs Radar/Camera

| Metric | Camera | Radar | LiDAR |
|--------|--------|-------|-------|
| 3D Position accuracy | Low (mono) / Medium (stereo) | Medium | Very high |
| Point density | N/A | Low (cluster) | High (64-channel: ~70k pts/frame) |
| Weather robustness | Poor | Excellent | Good (less than radar) |
| Velocity | No direct | Doppler | No direct (frame diff) |
| Detection range | 200m+ | 250m | 100-250m |
| Cost (production 2024) | $10-50 | $50-200 | $200-2000 |

---

## 8. Safety Considerations (ISO 26262 / SOTIF)

- LiDAR safe operating test (BIST): laser power monitoring, temperature limits (-40°C to +85°C)
- Window contamination: mud/snow on radome → degraded detection → DTC + ODD restriction
- Retroreflective targets (road signs): return extremely strong signal → saturation/overload mitigation required
- SOTIF: LiDAR alone cannot detect black ice, unmarked pedestrians at night at long range

---

## 9. Interview Q&A

### L1
**Q: What is the difference between time-of-flight (ToF) and FMCW LiDAR?**  
A: ToF LiDAR sends short pulses and measures round-trip time (range = c × t / 2). FMCW LiDAR uses frequency-modulated continuous waves — same principle as FMCW radar. FMCW advantages: (1) Direct velocity measurement (Doppler — same as radar); (2) Higher SNR from coherent detection; (3) Immunity to other LiDAR interference. ToF is simpler and dominant in current mass-production (Velodyne, Luminar).

### L2
**Q: How does PointPillars achieve real-time performance compared to voxel-based methods?**  
A: PointPillars pillarises the irregular 3D point cloud into a regular 2D BEV grid (birds-eye view pseudo-image). Points within each pillar (vertical column) are aggregated by a lightweight PointNet MLP. The resulting 2D pseudo-image uses standard 2D convolutions — GPU-efficient, highly optimised, deployable with TensorRT. Voxel-based methods (VoxelNet) use sparse 3D convolutions — more expressive but 5-10× slower. PointPillars: 115fps on RTX 2080; VoxelNet: ~4fps. For real-time ECU deployment, PointPillars is the standard.

### L3
**Q: Design a LiDAR-Camera fusion pipeline for 3D object detection meeting ASIL-B requirements.**  
A: (1) Temporal sync: LiDAR 10Hz, Camera 30Hz — align to LiDAR frame timestamp using rolling buffer; warp camera features with ego-motion compensation using IMU. (2) Frustum PointNets approach: (a) Camera 2D detection provides bounding box + class; (b) Frustum extruded to 3D isolates LiDAR points belonging to that detection; (c) PointNet refines 3D box within frustum. Alternative: (a) Project LiDAR to BEV; (b) Paint LiDAR points with camera semantic features (CameraNet features projected onto LiDAR via T_cam_lidar); (c) PointPillars on painted cloud (achieves 2-3% mAP improvement). ASIL-B: both sensors' outputs must be validated independently before fusion; DTC for extrinsic calibration error (reprojection > 5px); degraded mode when sensor unavailable.
