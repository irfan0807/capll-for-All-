# 25 — Adaptive Cruise Control (ACC) with AI

## Overview
ACC maintains a driver-set speed while automatically following a lead vehicle at a safe distance. Covers radar+camera fusion, IDM controller, predictive ACC, stop-and-go, and ISO 15622 compliance.

---

## 1. ACC System Architecture

```
Camera Detection ──┐
                   ├─► Sensor Fusion ──► Target Selection ──► ACC Controller ──► Torque/Brake Request
Radar Detection  ──┘    (EKF)            (in-lane, closest)      (IDM/MPC)          │
                                                                                     ▼
GPS/Map Speed   ──────────────────────────────────────────────────────────────► Speed Limiter
Limit                                                                            (TSR-informed)
```

---

## 2. ISO 15622 — ACC Performance Requirements

| Parameter | Standard Requirement |
|-----------|-------------------|
| Speed range | 30-200 kph (highway profile) |
| Time gap | User-selectable: 1.0-2.2s (typically 4 levels) |
| Maximum deceleration (system) | 3.5 m/s² (comfort), 5.0 m/s² (safety) |
| Maximum acceleration | 2.0 m/s² |
| Reaction time to target cut-in | < 600ms |
| System fault detection | DTC within one ignition cycle |

---

## 3. Target Selection Logic

```
All radar/camera tracks (N objects)
          │
          │ Lateral filter: |offset| < 1.8m (ego lane width/2)
          │
  In-lane candidates
          │
          │ Sort by range (closest first)
          │
  Primary target → IDM controller
  
  Secondary targets → Predictive ACC (look-ahead)
```

**Cut-in handling:** New vehicle entering lane from side (lane change into ego lane). ACCSystem detects when lateral_offset transitions from >1.8m to <1.8m in < 3 frames → immediate target update with caution deceleration.

---

## 4. Stop and Go (City ACC)

Required for traffic jam assist. When target stops → ego must also stop at minimum gap (3m bumper-to-bumper).

```python
def stop_and_go_control(ego_speed: float, gap_m: float,
                          target_speed: float, t_headway: float = 1.5) -> float:
    """Smooth control for stop-and-go including standing start."""
    if gap_m < 2.0 and ego_speed < 0.5:
        return 0.0   # Stationary hold
    
    if target_speed < 0.5 and gap_m < 5.0:
        # Target stopped — decelerate smoothly to stop
        return -min(2.0 * ego_speed, 3.0)   # Proportional deceleration
    
    # IDM in low-speed mode (reduce desired speed to target speed)
    v_des_adjusted = max(target_speed, 0.0)
    a = 2.0 * (1 - (ego_speed/max(v_des_adjusted,0.5))**4
               - ((t_headway * ego_speed)/max(gap_m,0.1))**2)
    return float(max(a, -3.5))
```

---

## 5. Predictive ACC

Standard ACC only reacts to the immediate leader. Predictive ACC observes the vehicle 2 ahead:

- If vehicle-2-ahead brakes heavily → ACC reduces speed proactively before vehicle-1-ahead brakes
- Result: 30% reduction in unnecessary brake-accelerate cycles → fuel efficiency improvement
- Tesla cites this as key benefit of camera-based multi-vehicle sensing

---

## 6. Safety Monitor

```python
def acc_safety_monitor(ego_speed: float, gap_m: float,
                         accel_cmd: float,
                         max_safe_decel: float = -5.0) -> float:
    """Safety override: clamp acceleration command to physical limits.
    
    Prevents ACC from requesting acceleration when gap is critically small."""
    # TTC at current closing speed
    # If gap < emergency threshold → full deceleration regardless of IDM
    emergency_gap = max(2.0, ego_speed * 0.5)  # 0.5s gap minimum
    
    if gap_m < emergency_gap:
        return max_safe_decel   # Override with emergency decel
    
    return float(np.clip(accel_cmd, max_safe_decel, 2.0))
```

---

## 7. Interview Q&A

### L1
**Q: What is time headway in ACC and what are the typical selectable values?**  
A: Time headway (T) is the time for the ego vehicle to travel the current gap distance at current speed: T = gap / v_ego. ACC maintains a constant time headway, meaning the gap increases proportionally with speed (at 120kph, 1.5s = 50m gap). Typical selectable values: 1.0s (sporty), 1.3s, 1.6s, 2.0s (comfortable). Shorter headway: less gap → feels more responsive. Longer headway: safer, more comfortable, better fuel efficiency from reduced oscillation.

### L2
**Q: How does ACC handle a target cut-in (vehicle cuts into the ego lane)?**  
A: (1) Detection: camera tracking detects object lateral position transitioning from >1.8m to <1.8m offset within 150ms. Radar confirms by detecting an object at shorter range than previous lead. (2) Target update: ACC immediately switches primary target to the new vehicle. (3) Response: if new target's TTC < 3s → pre-brake deceleration (1.5 m/s²) without waiting for IDM to respond; IDM takes over once steady following distance established. (4) Hysteresis: 0.5s timer before allowing target switch back (prevents oscillation if vehicle straddles lane boundary). ISO 15622: system must respond to cut-in within 600ms — validated on test track with 5 repetitions at 80kph.

### L3
**Q: Design a predictive ACC system that reduces brake-accelerate oscillation in urban traffic jams.**  
A: (1) Multi-target awareness: track top-3 in-lane vehicles; compute IDM command for each with cascaded effective gaps. (2) Stop-and-go prediction: if vehicle-2-ahead decelerates > 1.5 m/s² → pre-decelerate 0.3s earlier than standard IDM reaction. (3) Traffic signal V2X: receive SPaT (signal phase and timing) via C-V2X; if red light 200m ahead → begin smooth deceleration 150m ahead to avoid late hard braking. (4) Eco mode: coast with engine braking toward known red light → restart timing just before green (eliminates stop-and-go energy loss). (5) Safety override: all predictive elements reduce deceleration only (never reduce below IDM computed value); safety monitor ensures minimum gap maintained.

---

## Files
- [acc_ai.py](acc_ai.py) — IDMController, PredictiveACCController, ACCSystem, stop-and-go
