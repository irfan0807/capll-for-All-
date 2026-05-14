# RADAR & LIDAR — MINI PROJECTS
## Module 6 of 7 | 4 GitHub-Ready Projects

---

## PROJECT 1: FMCW Radar Simulator (Python)

**Problem:** Understand and verify FMCW radar range/velocity calculations without hardware, using a software simulation.

**Architecture:**
```
fmcw_simulator/
├── fmcw_radar.py         ← Chirp generation + FFT processing
├── scenario.py           ← Target placement + reflection model
├── plotter.py            ← Range-Doppler map visualization
├── tests/
│   └── test_fmcw.py      ← Physics math unit tests
└── README.md
```

**Full Implementation:**
```python
# fmcw_radar.py
"""
FMCW radar simulator.
Models: chirp generation, beat signal, range FFT, Doppler FFT.
"""
import numpy as np
from typing import List, Tuple


class FMCWRadar:
    """
    FMCW Radar parameters matching typical 77 GHz automotive radar.
    
    Usage:
        radar = FMCWRadar()
        targets = [RadarTarget(range_m=50, velocity_mps=10.0, rcs_dBsm=15)]
        range_doppler_map = radar.process_frame(targets)
    """
    def __init__(self,
                 f_carrier: float = 77e9,    # Hz
                 bandwidth: float = 4e9,      # Hz (76-80 GHz)
                 chirp_duration: float = 100e-6,  # seconds
                 n_chirps: int = 128,         # chirps per frame
                 n_samples: int = 256,        # samples per chirp
                 fs: float = 10e6):           # ADC sample rate Hz
        self.f_c = f_carrier
        self.BW = bandwidth
        self.T = chirp_duration
        self.N_chirps = n_chirps
        self.N_samples = n_samples
        self.fs = fs
        self.c = 3e8  # speed of light

        # Derived parameters
        self.slope = bandwidth / chirp_duration   # Hz/s
        self.range_resolution = self.c / (2 * bandwidth)
        self.max_range = (n_samples * fs * self.c) / (2 * bandwidth * 2)
        # Unambiguous velocity: ±λ/(4T)
        self.lambda_m = self.c / f_carrier
        self.max_velocity = self.lambda_m / (4 * chirp_duration)
        self.velocity_resolution = self.lambda_m / (2 * n_chirps * chirp_duration)

    def range_from_beat_freq(self, f_beat: float) -> float:
        """Convert beat frequency to range in meters."""
        return f_beat * self.c * self.T / (2 * self.BW)

    def velocity_from_doppler(self, f_doppler: float) -> float:
        """Convert Doppler frequency to velocity in m/s."""
        return f_doppler * self.c / (2 * self.f_c)

    def process_frame(self, targets: List) -> np.ndarray:
        """
        Process one radar frame with given targets.
        Returns range-Doppler map (power in dB).
        """
        # Build IF signal matrix [N_chirps × N_samples]
        t_samples = np.linspace(0, self.T, self.N_samples)
        if_matrix = np.zeros((self.N_chirps, self.N_samples), dtype=complex)

        for chirp_idx in range(self.N_chirps):
            t_chirp_start = chirp_idx * self.T
            for target in targets:
                delay = 2 * target.range_m / self.c
                # Doppler phase shift per chirp
                phase_doppler = 2 * np.pi * (2 * target.velocity_mps / self.lambda_m) * t_chirp_start
                # Beat signal for this target
                f_beat = self.slope * delay
                amplitude = 10 ** (target.rcs_dBsm / 20.0)
                beat = amplitude * np.exp(1j * (2 * np.pi * f_beat * t_samples + phase_doppler))
                if_matrix[chirp_idx] += beat

        # Add noise
        noise_power = 1e-4
        if_matrix += (np.random.randn(*if_matrix.shape) +
                      1j * np.random.randn(*if_matrix.shape)) * np.sqrt(noise_power / 2)

        # 2D FFT: range FFT across samples, Doppler FFT across chirps
        range_fft = np.fft.fft(if_matrix, axis=1)
        range_doppler = np.fft.fftshift(np.fft.fft(range_fft, axis=0), axes=0)
        return 20 * np.log10(np.abs(range_doppler) + 1e-10)

    def print_specs(self):
        print(f"Range resolution:  {self.range_resolution:.3f} m")
        print(f"Max range:         {self.max_range:.1f} m")
        print(f"Velocity resolution: {self.velocity_resolution:.3f} m/s")
        print(f"Max velocity:      {self.max_velocity:.1f} m/s (±)")


class RadarTarget:
    def __init__(self, range_m: float, velocity_mps: float, rcs_dBsm: float = 10.0):
        self.range_m = range_m
        self.velocity_mps = velocity_mps
        self.rcs_dBsm = rcs_dBsm

    def __repr__(self):
        return f"Target(R={self.range_m}m, v={self.velocity_mps}m/s, RCS={self.rcs_dBsm}dBsm)"
```

```python
# plotter.py
"""Visualize range-Doppler map."""
import numpy as np
import matplotlib.pyplot as plt
from fmcw_radar import FMCWRadar, RadarTarget


def plot_range_doppler(radar: FMCWRadar, targets: list):
    rd_map = radar.process_frame(targets)
    
    # Axes
    range_axis = np.linspace(0, radar.max_range, radar.N_samples // 2)
    vel_axis = np.linspace(-radar.max_velocity, radar.max_velocity, radar.N_chirps)

    plt.figure(figsize=(10, 6))
    plt.imshow(rd_map[:, :radar.N_samples // 2], aspect='auto',
               extent=[0, radar.max_range, -radar.max_velocity, radar.max_velocity],
               cmap='hot', vmin=-60, vmax=0)
    plt.colorbar(label='Power (dB)')
    plt.xlabel('Range (m)')
    plt.ylabel('Velocity (m/s)')
    plt.title('Range-Doppler Map')
    for t in targets:
        plt.plot(t.range_m, t.velocity_mps, 'b+', markersize=15, label=str(t))
    plt.legend()
    plt.tight_layout()
    plt.savefig("range_doppler_map.png", dpi=150)
    plt.show()
    print("Saved: range_doppler_map.png")


if __name__ == "__main__":
    radar = FMCWRadar()
    radar.print_specs()
    targets = [
        RadarTarget(range_m=50.0,  velocity_mps=0.0,   rcs_dBsm=20),
        RadarTarget(range_m=120.0, velocity_mps=-15.0,  rcs_dBsm=15),
        RadarTarget(range_m=30.0,  velocity_mps=5.0,   rcs_dBsm=5),
    ]
    plot_range_doppler(radar, targets)
```

```python
# tests/test_fmcw.py
"""Unit tests for FMCW physics calculations."""
import pytest
import math
from fmcw_radar import FMCWRadar, RadarTarget


@pytest.fixture
def radar():
    return FMCWRadar()


def test_range_resolution(radar):
    """Range resolution = c / (2 × BW)."""
    expected = 3e8 / (2 * 4e9)
    assert abs(radar.range_resolution - expected) < 0.001


def test_beat_freq_to_range(radar):
    """Known beat frequency → correct range."""
    # R = 50m → f_beat = R × 2BW / (c × T)
    # = 50 × 2 × 4e9 / (3e8 × 100e-6) = 400e9 / 3e10 ≈ 13.33 kHz
    f_beat = 50 * 2 * radar.BW / (radar.c * radar.T)
    r = radar.range_from_beat_freq(f_beat)
    assert abs(r - 50.0) < 0.1, f"Expected 50m, got {r:.2f}m"


def test_doppler_to_velocity(radar):
    """Known Doppler frequency → correct velocity."""
    # v = 30 m/s → f_doppler = 2 × v × fc / c
    # = 2 × 30 × 77e9 / 3e8 = 15400 Hz
    v_test = 30.0
    f_dop = 2 * v_test * radar.f_c / radar.c
    v_calc = radar.velocity_from_doppler(f_dop)
    assert abs(v_calc - v_test) < 0.01, f"Expected {v_test}m/s, got {v_calc:.3f}m/s"


def test_velocity_resolution(radar):
    """Velocity resolution = λ / (2 × N_chirps × T)."""
    expected = radar.lambda_m / (2 * radar.N_chirps * radar.T)
    assert abs(radar.velocity_resolution - expected) < 0.001
```

**Technologies:** Python 3, NumPy, matplotlib, pytest

**Resume Description:**
> "Built FMCW radar simulator from first principles: chirp generation, beat signal modelling, 2D FFT range-Doppler map, multi-target scenarios. Physics equations validated with pytest (range, velocity, resolution). Used for teaching radar algorithm concepts to 4 junior engineers."

---

## PROJECT 2: LiDAR Point Cloud Viewer (Open3D)

```python
# lidar_viewer.py
"""Load and visualize LiDAR point cloud from PCD or binary file."""
import numpy as np
import open3d as o3d
import sys


def load_velodyne_binary(filepath: str) -> np.ndarray:
    """Load Velodyne binary point cloud (x, y, z, intensity)."""
    points = np.fromfile(filepath, dtype=np.float32).reshape(-1, 4)
    return points


def load_pcd(filepath: str) -> np.ndarray:
    """Load PCD format point cloud."""
    pcd = o3d.io.read_point_cloud(filepath)
    return np.asarray(pcd.points)


def visualize_cloud(points: np.ndarray, title: str = "Point Cloud"):
    """Display point cloud with intensity-based coloring."""
    pcd = o3d.geometry.PointCloud()
    xyz = points[:, :3]
    pcd.points = o3d.utility.Vector3dVector(xyz)

    if points.shape[1] >= 4:
        intensity = points[:, 3]
        # Map intensity to color (cool → hot)
        colors = np.zeros((len(intensity), 3))
        intensity_norm = (intensity - intensity.min()) / (intensity.max() - intensity.min() + 1e-8)
        colors[:, 0] = intensity_norm        # red = high intensity
        colors[:, 2] = 1 - intensity_norm    # blue = low intensity
        pcd.colors = o3d.utility.Vector3dVector(colors)

    # Add ground plane (z ≈ 0)
    bbox = o3d.geometry.AxisAlignedBoundingBox(
        min_bound=np.array([-100, -50, -0.5]),
        max_bound=np.array([200, 50, 5.0])
    )

    print(f"{title}: {len(xyz)} points")
    print(f"  X range: {xyz[:,0].min():.1f} to {xyz[:,0].max():.1f} m")
    print(f"  Y range: {xyz[:,1].min():.1f} to {xyz[:,1].max():.1f} m")
    print(f"  Z range: {xyz[:,2].min():.1f} to {xyz[:,2].max():.1f} m")

    o3d.visualization.draw_geometries(
        [pcd, o3d.geometry.TriangleMesh.create_coordinate_frame(size=1.0)],
        window_name=title
    )


def simple_ground_removal(points: np.ndarray,
                           ground_z_threshold: float = -1.5) -> np.ndarray:
    """Remove ground plane points (z below threshold)."""
    mask = points[:, 2] > ground_z_threshold
    print(f"Ground removal: {points.shape[0]} → {mask.sum()} points")
    return points[mask]


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "sample.bin"
    
    if filepath.endswith(".bin"):
        pts = load_velodyne_binary(filepath)
    else:
        pts = load_pcd(filepath)

    pts_no_ground = simple_ground_removal(pts)
    visualize_cloud(pts_no_ground, title=f"LiDAR: {filepath}")
```

**Technologies:** Python 3, Open3D, NumPy

**Resume Description:**
> "Built LiDAR point cloud viewer loading Velodyne binary/PCD format, with intensity-based coloring and ground plane removal. Used for visual validation of LiDAR calibration and sensor characterization during prototype testing."

---

## PROJECT 3: Radar Object List Validator (CAN)

```python
# radar_validator.py
"""
Validate radar object list from CAN against reference GPS truth.
Computes range error, azimuth error, and velocity error per detection.
"""
import can
import csv
import struct
import math
import time
from dataclasses import dataclass
from typing import List, Optional

# CAN message IDs for radar object list (example, OEM-specific)
RADAR_MSG_BASE = 0x300   # Object 0x300 = object 0, 0x301 = object 1 ...
MAX_OBJECTS = 64

@dataclass
class RadarObject:
    obj_id: int
    range_m: float
    azimuth_deg: float
    velocity_mps: float
    rcs_dBsm: float
    timestamp: float


@dataclass
class ValidationResult:
    obj_id: int
    range_error_m: float
    azimuth_error_deg: float
    velocity_error_mps: float


def decode_radar_msg(msg: can.Message) -> Optional[RadarObject]:
    """Decode one radar object CAN message."""
    obj_id = msg.arbitration_id - RADAR_MSG_BASE
    if obj_id < 0 or obj_id >= MAX_OBJECTS:
        return None
    if len(msg.data) < 8:
        return None

    # Example decode (OEM-specific bit layout):
    raw = struct.unpack(">HhHh", msg.data[:8])
    range_m     = raw[0] * 0.1            # 0.1m resolution
    azimuth_deg = raw[1] * 0.01           # 0.01° resolution
    velocity    = raw[2] * 0.1 - 327.68   # offset encoded
    rcs         = raw[3] * 0.5 - 50.0     # 0.5 dBsm, -50 offset

    return RadarObject(
        obj_id=obj_id, range_m=range_m, azimuth_deg=azimuth_deg,
        velocity_mps=velocity, rcs_dBsm=rcs,
        timestamp=msg.timestamp
    )


def validate_vs_reference(radar_objects: List[RadarObject],
                           ref_range_m: float,
                           ref_azimuth_deg: float,
                           ref_velocity_mps: float,
                           tolerance_range: float = 0.5,
                           tolerance_azimuth: float = 1.0,
                           tolerance_velocity: float = 0.5) -> dict:
    """Compare radar detections to reference. Returns statistics."""
    results = []
    for obj in radar_objects:
        r_err = abs(obj.range_m - ref_range_m)
        az_err = abs(obj.azimuth_deg - ref_azimuth_deg)
        v_err = abs(obj.velocity_mps - ref_velocity_mps)
        results.append({
            "range_error": r_err,
            "azimuth_error": az_err,
            "velocity_error": v_err,
            "range_pass": r_err <= tolerance_range,
            "azimuth_pass": az_err <= tolerance_azimuth,
            "velocity_pass": v_err <= tolerance_velocity,
        })

    n = len(results)
    if n == 0:
        return {"detection_rate": 0, "samples": 0}

    return {
        "samples": n,
        "detection_rate": 100.0,
        "range_rmse": math.sqrt(sum(r["range_error"]**2 for r in results) / n),
        "range_pass_rate": sum(1 for r in results if r["range_pass"]) / n * 100,
        "azimuth_rmse": math.sqrt(sum(r["azimuth_error"]**2 for r in results) / n),
        "velocity_rmse": math.sqrt(sum(r["velocity_error"]**2 for r in results) / n),
    }


if __name__ == "__main__":
    print("Radar Object Validator")
    print("Reference: corner reflector at 50.0m, 0.0°, stationary")
    # Simulated data for demonstration
    objects = [
        RadarObject(0, 50.2, 0.1, 0.05, 20.0, time.time()),
        RadarObject(0, 49.8, -0.1, -0.05, 20.0, time.time() + 0.02),
        RadarObject(0, 50.4, 0.0, 0.0, 21.0, time.time() + 0.04),
    ]
    stats = validate_vs_reference(objects, 50.0, 0.0, 0.0)
    print(f"Samples:         {stats['samples']}")
    print(f"Range RMSE:      {stats['range_rmse']:.3f} m")
    print(f"Range pass rate: {stats['range_pass_rate']:.1f}%")
    print(f"Azimuth RMSE:    {stats['azimuth_rmse']:.3f} °")
    print(f"Velocity RMSE:   {stats['velocity_rmse']:.3f} m/s")
```

**Resume Description:**
> "Built radar object list CAN validator: decodes OEM radar CAN messages, computes range/azimuth/velocity RMSE vs. GPS ground truth, generates pass/fail report. Used for independent supplier radar acceptance testing across 3 range/velocity combinations."

---

## PROJECT 4: Sensor Fusion Demonstrator (Camera + Radar Late Fusion)

```python
# late_fusion.py
"""
Simple late fusion: merge radar object list with camera object list.
Demonstrates track-to-track association using IoU / distance matching.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RadarObj:
    id: int; x: float; y: float; vx: float; vy: float


@dataclass
class CameraObj:
    id: int; x: float; y: float; width: float; height: float; class_name: str


@dataclass
class FusedObject:
    fused_id: int
    x: float; y: float
    vx: float; vy: float
    classification: str
    confidence: float
    sources: List[str] = field(default_factory=list)


def euclidean_distance(r: RadarObj, c: CameraObj) -> float:
    return math.sqrt((r.x - c.x)**2 + (r.y - c.y)**2)


def late_fusion(radar_objects: List[RadarObj],
                camera_objects: List[CameraObj],
                association_threshold: float = 2.0) -> List[FusedObject]:
    """Associate radar and camera objects by nearest-neighbor matching."""
    fused = []
    fused_id = 0
    camera_used = set()

    for r in radar_objects:
        best_cam: Optional[CameraObj] = None
        best_dist = association_threshold + 1

        for c in camera_objects:
            if c.id in camera_used:
                continue
            d = euclidean_distance(r, c)
            if d < best_dist:
                best_dist = d
                best_cam = c

        if best_cam and best_dist <= association_threshold:
            # Fused: radar position + velocity + camera classification
            fused.append(FusedObject(
                fused_id=fused_id,
                x=(r.x + best_cam.x) / 2,  # simple average
                y=(r.y + best_cam.y) / 2,
                vx=r.vx, vy=r.vy,
                classification=best_cam.class_name,
                confidence=0.95,
                sources=["radar", "camera"]
            ))
            camera_used.add(best_cam.id)
        else:
            # Radar-only object (no camera match)
            fused.append(FusedObject(
                fused_id=fused_id,
                x=r.x, y=r.y, vx=r.vx, vy=r.vy,
                classification="unknown",
                confidence=0.6,
                sources=["radar"]
            ))
        fused_id += 1

    # Camera-only objects (no radar match)
    for c in camera_objects:
        if c.id not in camera_used:
            fused.append(FusedObject(
                fused_id=fused_id,
                x=c.x, y=c.y, vx=0.0, vy=0.0,
                classification=c.class_name,
                confidence=0.5,
                sources=["camera"]
            ))
            fused_id += 1

    return fused


if __name__ == "__main__":
    radar_objs = [
        RadarObj(id=0, x=50.0, y=0.3, vx=-15.0, vy=0.0),  # car ahead
        RadarObj(id=1, x=25.0, y=-2.5, vx=-5.0, vy=0.5),   # pedestrian left
    ]
    camera_objs = [
        CameraObj(id=0, x=49.8, y=0.2, width=2.0, height=1.5, class_name="car"),
        CameraObj(id=1, x=25.5, y=-2.4, width=0.5, height=1.8, class_name="pedestrian"),
    ]

    result = late_fusion(radar_objs, camera_objs)
    for obj in result:
        print(f"Fused[{obj.fused_id}]: {obj.classification} at ({obj.x:.1f}, {obj.y:.1f})"
              f" v=({obj.vx:.1f}, {obj.vy:.1f}) confidence={obj.confidence:.2f}"
              f" sources={obj.sources}")
```

**Resume Description:**
> "Implemented late-fusion algorithm: nearest-neighbor track association between radar object list and camera bounding boxes, producing fused object list with classification and velocity. Demonstrated camera-radar complementarity (camera = class, radar = velocity). Concept validated with simulated data."

---

*Next Module: [../07_CarMaker_dSPACE/01_Theory_Deep_Dive.md](../07_CarMaker_dSPACE/01_Theory_Deep_Dive.md)*
