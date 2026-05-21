# 28 — Autonomous Parking

## Overview
Automated parking covers parking slot detection, path planning through tight spaces, and end-to-end reverse parking manoeuvres. Covers surround-view cameras, ultrasonic sensors, occupancy grid, and Reeds-Shepp paths.

---

## 1. Parking System Modes

| Mode | Description | Sensors Required |
|------|------------|----------------|
| APA (Auto Park Assist) | Driver controls speed, system steers | Camera + USS |
| HPA (Home Park Assist) | Fully autonomous at learnt home location | Camera + USS + IMU |
| RAP (Remote Auto Park) | Via smartphone while driver outside | Camera + USS + Redundancy |
| RPA-V2X | Valet parking in smart garage | Camera + GPS + C-V2X |

---

## 2. Parking Slot Detection (Camera AI)

```python
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
import torch
import torch.nn as nn

@dataclass
class ParkingSlot:
    """Detected parking slot geometry."""
    slot_id:     int
    corners:     np.ndarray   # (4, 2) — corners in BEV (m)
    angle_deg:   float        # Slot orientation
    slot_type:   str          # 'perpendicular', 'parallel', 'angled'
    occupancy:   str          # 'empty', 'occupied', 'unknown'
    confidence:  float

class BEVParkingDetector(nn.Module):
    """Bird's Eye View parking slot detector from 4-camera surround view.
    
    Input: (4, 3, H, W) surround camera images → BEV stitched grid
    Output: parking slot masks + keypoints (corner markers)"""
    
    def __init__(self, bev_size: int = 512, num_slots: int = 20):
        super().__init__()
        self.bev_size  = bev_size
        self.num_slots = num_slots
        
        # BEV feature extractor (EfficientNet-B2 backbone)
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d((16, 16))
        )
        
        # Heads
        self.slot_heatmap = nn.Sequential(
            nn.Linear(128*16*16, 256), nn.ReLU(),
            nn.Linear(256, bev_size*bev_size)  # Slot centre heatmap
        )
        
    def forward(self, x: torch.Tensor) -> dict:
        feat = self.backbone(x).flatten(1)
        heatmap = self.slot_heatmap(feat).view(-1, 1, self.bev_size, self.bev_size)
        return {'heatmap': torch.sigmoid(heatmap)}
```

---

## 3. Ultrasonic Sensor Occupancy Grid

```python
class ParkingOccupancyGrid:
    """2D occupancy grid built from ultrasonic sensors during slot scan.
    Resolution: 5cm/cell, 6m × 4m region around vehicle."""
    
    def __init__(self, resolution_m: float = 0.05,
                  size_m: Tuple[float,float] = (8.0, 6.0)):
        self.res    = resolution_m
        self.w_cells = int(size_m[0] / resolution_m)
        self.h_cells = int(size_m[1] / resolution_m)
        self.grid   = np.full((self.h_cells, self.w_cells), 0.5)  # Log-odds init
        
    def update_sonar(self, dist_m: float, angle_deg: float,
                      max_range_m: float = 3.0):
        """Update occupancy from single USS reading (inverse sensor model)."""
        angle_rad = np.radians(angle_deg)
        cx = self.w_cells // 2
        cy = self.h_cells // 2
        
        # Mark cells along beam as free (below detected distance)
        n_free = int(dist_m / self.res) - 1
        for i in range(1, max(1, n_free)):
            x = int(cx + i * np.sin(angle_rad))
            y = int(cy + i * np.cos(angle_rad))
            if 0 <= x < self.w_cells and 0 <= y < self.h_cells:
                self.grid[y,x] = max(0.05, self.grid[y,x] - 0.1)  # Free
        
        # Mark detected cell as occupied
        if dist_m < max_range_m:
            x = int(cx + dist_m/self.res * np.sin(angle_rad))
            y = int(cy + dist_m/self.res * np.cos(angle_rad))
            if 0 <= x < self.w_cells and 0 <= y < self.h_cells:
                self.grid[y,x] = min(0.95, self.grid[y,x] + 0.3)  # Occupied
    
    def is_slot_free(self, slot_corners: np.ndarray,
                      threshold: float = 0.4) -> bool:
        """Check if parking slot area is free (occupancy < threshold)."""
        cx = self.w_cells // 2
        cy = self.h_cells // 2
        
        for corner in slot_corners:
            xi = int(cx + corner[0] / self.res)
            yi = int(cy + corner[1] / self.res)
            if 0 <= xi < self.w_cells and 0 <= yi < self.h_cells:
                if self.grid[yi, xi] > threshold:
                    return False
        return True
```

---

## 4. Reeds-Shepp Path Planning

For parallel and reverse parking manoeuvres, the vehicle must navigate backwards through curved paths. Reeds-Shepp (RS) paths provide minimum-length paths for vehicles with both forward and reverse motion.

```python
def simple_3point_reverse_park(
        slot_centre: Tuple[float,float],
        slot_angle_deg: float,
        vehicle_turning_radius: float = 5.2) -> List[Tuple[float,float,float]]:
    """3-point reverse parking path for perpendicular slot.
    
    Returns list of (x, y, heading_deg) waypoints."""
    
    x0, y0 = slot_centre
    angle = np.radians(slot_angle_deg)
    R = vehicle_turning_radius
    
    # Approach point: 1.5 × turning radius ahead of slot
    approach_x = x0 + 1.5 * R * np.cos(angle + np.pi/2)
    approach_y = y0 + 1.5 * R * np.sin(angle + np.pi/2)
    
    # Turn point: vehicle turns toward slot
    turn_x = x0 + 0.5 * R * np.cos(angle + np.pi/4)
    turn_y = y0 + 0.5 * R * np.sin(angle + np.pi/4)
    
    # Final slot position
    final_x = x0
    final_y = y0
    
    return [
        (approach_x, approach_y, np.degrees(angle)),
        (turn_x, turn_y, np.degrees(angle) + 45),
        (final_x, final_y, np.degrees(angle) + 90),
    ]
```

---

## 5. Parking Control System

```
Driver initiates parking
         │
         ▼
Slot scan: drive slowly 10kph, USS scan both sides
         │
         ▼
Slot detected? → Camera BEV confirms empty
         │
         ▼
Path planned (Reeds-Shepp or 3-point arc)
         │
         ▼
Execute: speed control (creep ~3kph) + steering control
         │
         ▼
Position feedback: USS (distance to walls) + camera surround view
         │
         ▼
Park complete: hand brake, report slot ID to vehicle memory
```

---

## 6. Safety Requirements for Automated Parking

| Requirement | Specification |
|------------|-------------|
| Max speed in autonomous parking | 6 kph (RAP), 10 kph (APA scan) |
| Emergency stop trigger | USS < 20cm (any direction) |
| Remote Parking (RAP) | Continuous button hold required (ISO 22737) |
| Driver re-entry confirmation | Driver must be present for drive-away |
| Obstacle detection | 360° USS coverage, 10cm resolution |
| Fire/emergency override | Manual override at any time, ≤ 200ms |

---

## 7. Interview Q&A

### L1
**Q: What sensors does an automated parking system use and why?**  
A: (1) Ultrasonic sensors (USS): 8-12 sensors around vehicle perimeter, 10cm resolution within 3m — primary obstacle detection for close-range parking; cheap, robust to rain and dust. (2) Surround view cameras (4×): fisheye at each corner — provides BEV stitched image of area around vehicle; used for parking slot line detection and gap measurement. (3) Wheel encoder + steering angle: dead reckoning for precise position tracking during manoeuvre (IMU optional for higher accuracy). (4) Rear camera: high-res reverse camera for driver information and final alignment. Radar not typically used (cost, resolution not needed at parking speeds).

### L2
**Q: How does a vehicle detect a suitable parking slot size while driving past?**  
A: Drive-by scan at ~10kph: (1) USS lateral sensors scan continuously; measure distance to roadside objects (other vehicles, walls) at each timestep. (2) Gap detection algorithm: when lateral distance increases beyond ego_width + safety_margin (typically > 2.5m for perpendicular, > 6.5m for parallel), start measuring gap length. (3) Length measurement: vehicle travel distance × cosine(heading change) gives gap length estimate. (4) Confirmation: gap length > required_length (perpendicular: 2.7m, parallel: 6.5m for 5m car) → valid slot found. (5) Camera validation: surround-view camera detects slot corner markers (white lines) → confirms it is a marked slot. Result: slot detected within ~150ms of passing the opening.

### L3
**Q: Design a robotic valet parking system for a smart city parking garage.**  
A: (1) Infrastructure: garage fitted with 5cm resolution HD map (pre-scanned by mapping vehicle); each floor has WiFi 6 / UWB anchor grid for sub-10cm positioning. (2) Vehicle side: customer drives to drop-off zone; vehicle switches to RAP mode; downloads garage map + assigned slot location. (3) Navigation: A* on pre-built occupancy graph of parking lanes; velocity = 5kph; 360° USS + camera for dynamic obstacle avoidance (pedestrians, other vehicles). (4) Slot execution: Reeds-Shepp path from aisle to slot; final alignment using camera corner detection + ultrasonic pinch detection; successful park confirmed by wheel encoder + camera. (5) Retrieval: owner requests via app; system navigates vehicle from slot to drop-off, stopping for any obstacle >0 on path. (6) Fleet management: cloud assigns slots to minimise retrieval time; priority slots near exits for EVs below 20% charge.

---

## Files
- Python code embedded in README above
- `BEVParkingDetector`, `ParkingOccupancyGrid`, `simple_3point_reverse_park` as reference implementations
