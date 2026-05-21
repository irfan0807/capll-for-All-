"""
27_AEB_SYSTEM — Automatic Emergency Braking
TTC computation, multi-sensor fusion, ASIL-B safety chain,
Euro NCAP AEB scenarios.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum


class AEBState(Enum):
    INACTIVE    = 'inactive'
    MONITORING  = 'monitoring'
    WARNING     = 'warning'       # Visual + audio warning to driver
    PREFILL     = 'prefill'       # Brake hydraulic prefill (no deceleration)
    PARTIAL     = 'partial'       # Partial brake (0.3-0.5g)
    FULL        = 'full'          # Full autonomous brake (0.9g)


@dataclass
class ObstacleCandidate:
    """Detected obstacle for AEB evaluation."""
    track_id:       int
    range_m:        float
    range_rate_mps: float  # Negative = approaching
    lateral_m:      float  # Lateral offset from ego path
    obj_type:       str    # 'vehicle', 'pedestrian', 'cyclist', 'barrier'
    confidence:     float  # Sensor fusion confidence
    source:         str    # 'radar', 'camera', 'fused'


def compute_ttc(range_m: float, range_rate_mps: float) -> float:
    """Time-To-Collision in seconds.
    
    Returns inf if closing rate is not approaching."""
    if range_rate_mps >= 0.0:   # Not approaching
        return float('inf')
    return float(range_m / (-range_rate_mps))


def compute_path_overlap(obstacle_lateral_m: float,
                          obj_width_m: float = 0.5,
                          ego_width_m: float = 1.9) -> float:
    """Estimate overlap ratio between ego vehicle path and obstacle.
    Returns 0 (no overlap) to 1 (full overlap)."""
    half_ego  = ego_width_m / 2
    half_obj  = obj_width_m / 2
    
    # Distance between centres
    dist = abs(obstacle_lateral_m)
    
    # Overlap width
    overlap = (half_ego + half_obj) - dist
    overlap  = max(0.0, overlap)
    
    return float(min(overlap / half_obj, 1.0))


class AEBThreatAssessor:
    """Computes threat level and required brake intervention.
    
    Uses TTC + path overlap to classify AEB trigger level."""
    
    # Thresholds (ISO 22737 / Euro NCAP AEB requirements)
    WARNING_TTC_S  = 2.7
    PREFILL_TTC_S  = 2.0
    PARTIAL_TTC_S  = 1.6
    FULL_TTC_S     = 1.2
    
    MIN_CONFIDENCE = 0.6
    MIN_OVERLAP    = 0.1
    MIN_SPEED_MPS  = 2.8   # 10kph minimum — no AEB at parking speeds
    
    def assess(self, obstacle: ObstacleCandidate,
                ego_speed_mps: float) -> Tuple[AEBState, float]:
        """Assess threat level from one obstacle candidate.
        
        Returns: (recommended AEB state, required deceleration m/s²)"""
        
        if ego_speed_mps < self.MIN_SPEED_MPS:
            return AEBState.MONITORING, 0.0
        
        if obstacle.confidence < self.MIN_CONFIDENCE:
            return AEBState.MONITORING, 0.0
        
        obj_widths = {'vehicle': 1.8, 'pedestrian': 0.5,
                       'cyclist': 0.6, 'barrier': 0.1}
        obj_w = obj_widths.get(obstacle.obj_type, 1.0)
        
        overlap = compute_path_overlap(obstacle.lateral_m, obj_w)
        if overlap < self.MIN_OVERLAP:
            return AEBState.MONITORING, 0.0
        
        ttc = compute_ttc(obstacle.range_m, obstacle.range_rate_mps)
        
        if ttc > self.WARNING_TTC_S:
            return AEBState.MONITORING, 0.0
        elif ttc > self.PREFILL_TTC_S:
            return AEBState.WARNING, 0.0
        elif ttc > self.PARTIAL_TTC_S:
            return AEBState.PREFILL, 0.0
        elif ttc > self.FULL_TTC_S:
            # Partial brake: compute required deceleration to avoid collision
            decel = self._required_decel(ego_speed_mps, obstacle, partial=True)
            return AEBState.PARTIAL, decel
        else:
            decel = self._required_decel(ego_speed_mps, obstacle, partial=False)
            return AEBState.FULL, decel
    
    def _required_decel(self, ego_speed: float,
                          obs: ObstacleCandidate,
                          partial: bool) -> float:
        """Minimum deceleration to stop before obstacle.
        v² = 2 * a * s  →  a = v²/2s"""
        s_safe = max(obs.range_m - 2.0, 0.5)   # 2m safety margin
        a_required = -(ego_speed**2) / (2 * s_safe)
        
        if partial:
            return float(max(a_required, -4.0))   # Cap at 0.4g partial
        else:
            return float(max(a_required, -8.83))  # 0.9g full brake


class AEBSystem:
    """Complete AEB safety chain.
    ASIL-B: Single-point failure must be detected; system degrades gracefully."""
    
    MAX_FULL_DECEL   = -8.83    # m/s² (0.9g) — peak AEB
    MAX_PARTIAL_DECEL = -4.0   # m/s² (partial intervention)
    
    def __init__(self):
        self.assessor    = AEBThreatAssessor()
        self.state       = AEBState.INACTIVE
        self._brake_cmd  = 0.0
        self._active_track: Optional[int] = None
        
        # Diagnostic flags (ASIL-B: monitored by safety supervisor)
        self.radar_healthy  = True
        self.camera_healthy = True
    
    def activate(self):
        self.state = AEBState.MONITORING
    
    def deactivate(self):
        self.state = AEBState.INACTIVE
        self._brake_cmd = 0.0
    
    def step(self, obstacles: List[ObstacleCandidate],
              ego_speed_mps: float) -> Tuple[float, AEBState]:
        """Main AEB step at 20Hz.
        Returns (brake_pressure_percent, new_state)"""
        
        if self.state == AEBState.INACTIVE:
            return 0.0, self.state
        
        # ASIL-B: require at least one healthy sensor
        if not self.radar_healthy and not self.camera_healthy:
            self.deactivate()
            return 0.0, AEBState.INACTIVE
        
        # Assess all obstacles, take worst (highest threat)
        worst_state  = AEBState.MONITORING
        worst_decel  = 0.0
        worst_track  = None
        
        for obs in obstacles:
            state_req, decel_req = self.assessor.assess(obs, ego_speed_mps)
            if state_req.value > worst_state.value:
                worst_state  = state_req
                worst_decel  = decel_req
                worst_track  = obs.track_id
        
        self.state          = worst_state
        self._brake_cmd     = worst_decel
        self._active_track  = worst_track
        
        # Convert to brake pressure % (0-100%)
        brake_pct = 0.0
        if worst_state == AEBState.PREFILL:
            brake_pct = 5.0    # Hydraulic prefill, no deceleration felt
        elif worst_state == AEBState.PARTIAL:
            brake_pct = abs(worst_decel / self.MAX_FULL_DECEL) * 100
        elif worst_state == AEBState.FULL:
            brake_pct = 100.0
        
        return float(np.clip(brake_pct, 0.0, 100.0)), self.state
    
    @property
    def brake_cmd_mps2(self) -> float:
        return self._brake_cmd


# ==========================================================================
# DEMO — Euro NCAP AEB scenarios
# ==========================================================================

if __name__ == "__main__":
    print("=== AEB System Demo — Euro NCAP Scenarios ===\n")
    
    aeb = AEBSystem()
    aeb.activate()
    
    # Scenario 1: Car-to-Car Rear (CCRs) — stationary vehicle ahead
    print("Scenario 1: CCRs — 50kph ego, stationary vehicle 40m ahead")
    ego_speed = 50 / 3.6  # 50kph
    
    for t_step in range(20):
        t = t_step * 0.05   # 20Hz → 50ms
        range_m = max(0.5, 40.0 - ego_speed * t)
        range_rate = -ego_speed  # Stationary target
        
        obs = ObstacleCandidate(
            track_id=1,
            range_m=range_m,
            range_rate_mps=range_rate,
            lateral_m=0.0,
            obj_type='vehicle',
            confidence=0.95,
            source='fused'
        )
        
        brake_pct, state = aeb.step([obs], ego_speed)
        ttc = compute_ttc(range_m, range_rate)
        
        print(f"  t={t:.2f}s: range={range_m:.1f}m TTC={ttc:.2f}s "
              f"brake={brake_pct:.0f}% state={state.value}")
        
        # Apply braking
        if brake_pct > 0:
            decel = -(brake_pct / 100) * 8.83
            ego_speed = max(0.0, ego_speed + decel * 0.05)
        
        if ego_speed < 0.1:
            print(f"  >>> Vehicle stopped at t={t:.2f}s, range={range_m:.1f}m")
            break
    
    print("\nScenario 2: Pedestrian crossing (AEB-PED)")
    ego_speed = 30 / 3.6
    aeb2 = AEBSystem()
    aeb2.activate()
    
    for t_step in range(15):
        range_m = max(0.5, 25.0 - ego_speed * (t_step * 0.05))
        obs_ped = ObstacleCandidate(
            track_id=2, range_m=range_m, range_rate_mps=-ego_speed,
            lateral_m=0.3, obj_type='pedestrian', confidence=0.82, source='camera'
        )
        brake_pct, state = aeb2.step([obs_ped], ego_speed)
        print(f"  range={range_m:.1f}m brake={brake_pct:.0f}% state={state.value}")
        if brake_pct > 0:
            ego_speed = max(0.0, ego_speed - (brake_pct/100)*8.83*0.05)
        if ego_speed < 0.1:
            print(f"  >>> Stopped safely at range={range_m:.1f}m")
            break
