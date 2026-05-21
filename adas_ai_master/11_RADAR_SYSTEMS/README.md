# 11 — Radar Systems for ADAS

## Overview
FMCW automotive radar: range, velocity, and azimuth estimation. 77GHz long-range radar (LRR), medium-range radar (MRR), and short-range radar (SRR) for ACC, AEB, BSD, cross-traffic alert, and parking.

---

## 1. Radar Variants in Automotive

| Type | Frequency | Range | Use Case |
|------|-----------|-------|---------|
| LRR (Long-range) | 77GHz | 10-250m | ACC, AEB, highway |
| MRR (Medium-range) | 77GHz | 1-100m | LCA, cross-traffic |
| SRR (Short-range) | 77GHz | 0.1-30m | Parking, blind spot |
| 79GHz Ultra-wideband | 79GHz | 0.1-10m | Pedestrian hands, parking |

---

## 2. FMCW Radar Principle

**Frequency Modulated Continuous Wave (FMCW):**

Transmit a chirp: frequency ramps linearly from $f_0$ to $f_0 + B$ over time $T_c$:

$$f_{TX}(t) = f_0 + \frac{B}{T_c} t$$

Echo from target at range $R$ arrives with delay $\tau = 2R/c$.

**Beat frequency** (mix TX with RX):
$$f_{beat} = \frac{B}{T_c} \cdot \frac{2R}{c} \quad \Rightarrow \quad R = \frac{f_{beat} \cdot c \cdot T_c}{2B}$$

**Range resolution** (minimum separation to distinguish two targets):
$$\Delta R = \frac{c}{2B}$$
- 77GHz with B = 4GHz: $\Delta R = 0.037$m = 3.7cm
- 77GHz with B = 500MHz: $\Delta R = 0.3$m

---

## 3. Velocity Measurement (Doppler)

A moving target produces a **Doppler shift** — phase change between successive chirps:

$$\Delta\phi = \frac{4\pi f_0 v_r}{c} T_{chirp}$$

$$v_r = \frac{\Delta\phi \cdot c}{4\pi f_0 T_{chirp}}$$

where $v_r$ = radial velocity (range-rate), $f_0$ = carrier frequency.

**Velocity resolution:**
$$\Delta v = \frac{\lambda}{2 T_{frame}} = \frac{c}{2 f_0 N_{chirp} T_{chirp}}$$

Example: 77GHz, N=128 chirps, $T_{chirp}$=50µs: $\Delta v = 0.16$ m/s

---

## 4. Azimuth (Angular) Measurement

Physical antenna aperture limits azimuth resolution:
$$\Delta\theta \approx \frac{\lambda}{d_{aperture}}$$

**Virtual MIMO aperture:** Radar with $N_{TX}$ transmitters and $N_{RX}$ receivers creates $N_{TX} \times N_{RX}$ virtual elements → larger aperture → better azimuth.

Example: 3TX × 4RX = 12 virtual elements
- Aperture: 12 × $\lambda/2$ = 6λ
- Azimuth resolution: $\lambda/(6\lambda) \approx 9.5°$

**High-resolution algorithms:**
- MUSIC, ESPRIT → pseudo-spectrum, super-resolution
- Used in premium radar modules (ZF, Aptiv Gen5)

---

## 5. Radar Point Cloud Processing

```python
import numpy as np
from dataclasses import dataclass
from typing import List

@dataclass
class RadarPoint:
    range_m:       float
    azimuth_deg:   float
    elevation_deg: float
    doppler_mps:   float   # Radial velocity
    rcs_dbsm:      float   # Radar cross-section (dBsm)
    snr_db:        float   # Signal-to-noise ratio

def polar_to_cartesian(pts: List[RadarPoint]) -> np.ndarray:
    """Convert radar detections from polar to Cartesian (vehicle frame).
    X: forward, Y: left, Z: up
    
    Returns (N, 4) array: [x, y, z, doppler]"""
    result = []
    for p in pts:
        az_rad = np.radians(p.azimuth_deg)
        el_rad = np.radians(p.elevation_deg)
        x = p.range_m * np.cos(el_rad) * np.cos(az_rad)  # Forward
        y = p.range_m * np.cos(el_rad) * np.sin(az_rad)  # Left
        z = p.range_m * np.sin(el_rad)                    # Up
        result.append([x, y, z, p.doppler_mps])
    return np.array(result) if result else np.zeros((0, 4))

def filter_by_snr(pts: List[RadarPoint], min_snr_db: float = 10.0) -> List[RadarPoint]:
    """Remove low-quality detections (ground clutter, reflections)."""
    return [p for p in pts if p.snr_db >= min_snr_db]

def cluster_detections(points_xy: np.ndarray, 
                       eps: float = 1.0, 
                       min_samples: int = 2) -> np.ndarray:
    """DBSCAN clustering to group points belonging to same physical object.
    
    eps: max distance between neighbours (1.0m for typical vehicles)
    Returns cluster labels (-1 = noise)"""
    from sklearn.cluster import DBSCAN
    if len(points_xy) < min_samples:
        return np.full(len(points_xy), -1)
    db = DBSCAN(eps=eps, min_samples=min_samples)
    return db.fit_predict(points_xy[:, :2])
```

---

## 6. Radar vs Camera Complementarity

| Scenario | Camera | Radar |
|---------|--------|-------|
| Night driving | Poor | Excellent |
| Heavy rain | Degraded | Good |
| Fog | Poor | Good |
| Snow/ice | Poor | Fair |
| Distance to object | Mono: no; Stereo: <50m | Excellent (<250m) |
| Velocity of object | Frame difference only | Direct Doppler |
| Object classification | Excellent (visual features) | Poor (RCS only) |
| Lateral precision | Sub-pixel (cm at short range) | ±0.5-1° azimuth (cm-m) |

**Fusion benefit**: camera classifies + localises; radar measures velocity + confirms presence in bad weather.

---

## 7. Radar CFAR (Constant False Alarm Rate)

CFAR threshold sets detection threshold dynamically to maintain constant false alarm rate:

```python
def cfar_os_1d(signal: np.ndarray, guard: int = 4,
               training: int = 16, k_rank: int = 12, 
               scale: float = 1.2) -> np.ndarray:
    """OS-CFAR (Ordered Statistics) detector.
    For each cell under test (CUT): take k-th ordered statistic of 
    training cells as threshold estimate.
    
    Returns boolean mask: True = detection"""
    N = len(signal)
    detections = np.zeros(N, dtype=bool)
    win = guard + training
    
    for i in range(win, N - win):
        left  = signal[i-win : i-guard]
        right = signal[i+guard+1 : i+win+1]
        cells = np.concatenate([left, right])
        cells_sorted = np.sort(cells)
        threshold = scale * cells_sorted[k_rank - 1]
        detections[i] = signal[i] > threshold
    return detections
```

---

## 8. Safety Considerations

**Mutual interference**: With many 77GHz radars on road (millions of cars), signals can interfere. Mitigation: random chirp timing per sensor, MIMO orthogonal waveforms.

**False detections from bridges/guard rails**: Metal structures → strong radar returns. Mitigation: velocity gate (stationary objects filtered for ACC), elevation filtering.

**ISO 26262**: Radar typically provides ASIL-B redundancy input. Radar MCU runs diagnostic self-test (loopback) at startup + periodic online BIST.

---

## 9. Interview Q&A

### L1
**Q: What is Doppler velocity and how does radar measure it?**  
A: Doppler velocity is the rate of change of distance (range-rate) between radar and target. Radar measures it from the phase shift between consecutive chirps: a moving target shifts the phase of the returned signal. At 77GHz, 1m/s velocity causes ~1kHz Doppler shift. Phase change between two chirps separated by $T_{chirp}$: $\Delta\phi = 4\pi f_0 v_r T_{chirp}/c$. In ACC, this gives direct measurement of closing speed — fundamentally more reliable than camera-based velocity from optical flow.

### L2
**Q: Why does radar struggle with pedestrian classification compared to camera?**  
A: Radar sees only radar cross-section (RCS) — a few dBsm for a pedestrian. A pedestrian's RCS is similar to a bicycle, shopping cart, or small metal sign. The micro-Doppler signature (limb movement) can help classify pedestrians but requires high-range-rate resolution. Camera sees visual appearance (shape, colour, motion pattern), making classification trivial. In production, radar detects the presence/velocity; camera confirms class. This is why AEB relies on camera confirmation before triggering.

### L3
**Q: Describe the data processing chain in a 77GHz FMCW radar from ADC samples to object list.**  
A: (1) ADC sampling: raw I/Q samples from mixer at ~10-50 Msps. (2) Range FFT per chirp: each chirp's samples → 1D FFT → range profile (peaks at beat frequencies = target ranges). (3) Doppler FFT: stack N chirps → 2D FFT along slow-time axis → range-Doppler map with velocity dimension. (4) Angle FFT / beamforming: stack Rx channels → spatial FFT → azimuth-range-velocity cube. (5) CFAR detection: apply OS-CFAR across range-Doppler cells → point detections. (6) Clustering: DBSCAN on detections → group multi-point clusters belonging to same extended target. (7) Object list generation: centroid, velocity vector, estimated RCS, cluster spread → output via CAN/CAN-FD to fusion ECU. Total latency budget: <10ms for radar processing cycle at 20Hz.
