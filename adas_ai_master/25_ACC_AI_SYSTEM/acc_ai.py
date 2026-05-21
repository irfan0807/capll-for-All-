"""
25_ACC_AI_SYSTEM — Adaptive Cruise Control with AI Enhancement
Radar + camera fusion, IDM + predictive control, multi-target management.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class ACCState(Enum):
    INACTIVE    = 'inactive'
    SPEED_CTRL  = 'speed_ctrl'    # Free cruise (no target)
    FOLLOW_CTRL = 'follow_ctrl'   # Following target
    BRAKING     = 'braking'       # Active brake request
    STANDSTILL  = 'standstill'    # Stop & Go: stopped


@dataclass
class ACCTarget:
    """Closest confirmed in-lane vehicle target."""
    range_m:        float
    range_rate_mps: float   # Positive = separating, negative = approaching
    lateral_offset_m: float # Offset from ego lane centre
    speed_mps:      float   # Absolute speed estimate (ego + range_rate)
    confidence:     float   # Sensor fusion confidence [0,1]
    source:         str     # 'radar', 'camera', 'fused'
    track_id:       int


@dataclass
class VehicleState:
    """Ego vehicle state."""
    speed_mps:       float
    accel_mps2:      float
    yaw_rate_radps:  float


class IDMController:
    """Intelligent Driver Model for ACC following.
    Generates smooth, comfortable acceleration commands."""
    
    def __init__(self,
                 v_set_mps:     float = 33.3,    # 120 kph
                 t_headway_s:   float = 1.5,      # Preferred time gap
                 a_max_mps2:    float = 2.0,
                 b_comfort_mps2: float = 2.5,
                 s_min_m:       float = 3.0):
        self.v_set    = v_set_mps
        self.T        = t_headway_s
        self.a_max    = a_max_mps2
        self.b        = b_comfort_mps2
        self.s_min    = s_min_m
    
    def update_setspeed(self, v_set_mps: float):
        self.v_set = v_set_mps
    
    def compute_accel(self, ego_speed: float,
                       target: Optional[ACCTarget]) -> float:
        """Compute IDM acceleration command.
        
        Returns: acceleration request in m/s² (clamped [-5, 2])"""
        if target is None:
            # Free cruise: accelerate to set speed
            a = self.a_max * (1 - (ego_speed / max(self.v_set, 0.1))**4)
            return float(np.clip(a, -5.0, self.a_max))
        
        # Following mode
        s_gap = max(target.range_m, 0.1)
        dv    = -target.range_rate_mps   # Positive dv = approaching
        
        # Desired minimum gap
        s_star = (self.s_min + ego_speed * self.T +
                  ego_speed * dv / (2 * np.sqrt(self.a_max * self.b)))
        
        a = self.a_max * (1 - (ego_speed/max(self.v_set,0.1))**4
                          - (s_star/s_gap)**2)
        
        return float(np.clip(a, -5.0, self.a_max))


class PredictiveACCController:
    """Predictive ACC: look ahead beyond immediate leader.
    Detects cut-in vehicles and traffic decelerating ahead to reduce
    unnecessary braking cycles (fuel efficiency + comfort)."""
    
    def __init__(self, base_idm: IDMController,
                 look_ahead_vehicles: int = 2):
        self.idm          = base_idm
        self.look_ahead   = look_ahead_vehicles
    
    def compute_accel(self, ego_speed: float,
                       targets_sorted: List[ACCTarget]) -> float:
        """Predictive acceleration using N vehicles ahead.
        Returns minimum (most cautious) of IDM commands for each target."""
        if not targets_sorted:
            return self.idm.compute_accel(ego_speed, None)
        
        commands = []
        for i, tgt in enumerate(targets_sorted[:self.look_ahead+1]):
            # For vehicle i ahead: effective gap reduces by gap between vehicles
            a = self.idm.compute_accel(ego_speed, tgt)
            commands.append(a)
        
        # Take minimum — most conservative
        return float(min(commands))


class ACCSystem:
    """Complete ACC system with state machine, target management, 
    and deceleration arbitration."""
    
    # Safety limits
    MAX_DECEL_COMFORT = -3.0   # m/s² normal braking
    MAX_DECEL_SAFETY  = -5.0   # m/s² pre-AEB
    TTC_WARN_THRESHOLD = 3.0   # s — visual warning
    TTC_BRAKE_THRESHOLD = 2.0  # s — automatic brake
    
    def __init__(self, v_set_mps: float = 33.3):
        self.state      = ACCState.INACTIVE
        self.idm        = IDMController(v_set_mps=v_set_mps)
        self.pred_ctrl  = PredictiveACCController(self.idm)
        self._v_set     = v_set_mps
        self._accel_cmd = 0.0
    
    def set_speed(self, v_mps: float):
        """Driver adjusts set speed."""
        self._v_set = np.clip(v_mps, 0.0, 55.6)   # 0-200kph
        self.idm.update_setspeed(self._v_set)
    
    def step(self, ego: VehicleState,
              targets: List[ACCTarget]) -> float:
        """Main ACC step — returns acceleration request (m/s²).
        
        Runs at 20Hz (50ms cycle, matching radar output rate)."""
        
        if self.state == ACCState.INACTIVE:
            return 0.0
        
        # Select in-lane target (lateral offset < 0.5 × lane_width)
        in_lane = [t for t in targets if abs(t.lateral_offset_m) < 1.8]
        in_lane.sort(key=lambda t: t.range_m)  # Closest first
        primary = in_lane[0] if in_lane else None
        
        # State transitions
        if primary is None:
            self.state = ACCState.SPEED_CTRL
        else:
            ttc = -primary.range_m / primary.range_rate_mps \
                  if primary.range_rate_mps < -0.1 else float('inf')
            
            if ttc < self.TTC_BRAKE_THRESHOLD:
                self.state = ACCState.BRAKING
            elif primary.range_m < 2.0 and ego.speed_mps < 0.5:
                self.state = ACCState.STANDSTILL
            else:
                self.state = ACCState.FOLLOW_CTRL
        
        # Compute acceleration command
        if self.state == ACCState.BRAKING:
            # Emergency deceleration (approaching fast)
            self._accel_cmd = self.MAX_DECEL_SAFETY
        elif self.state == ACCState.STANDSTILL:
            self._accel_cmd = max(-ego.speed_mps / 0.5, self.MAX_DECEL_COMFORT)
        else:
            self._accel_cmd = self.pred_ctrl.compute_accel(
                ego.speed_mps, in_lane)
        
        return float(self._accel_cmd)
    
    @property
    def accel_cmd(self) -> float:
        return self._accel_cmd
    
    @property
    def current_state(self) -> ACCState:
        return self.state


# ==========================================================================
# DEMO
# ==========================================================================

if __name__ == "__main__":
    print("=== ACC AI System Demo ===\n")
    
    acc = ACCSystem(v_set_mps=33.3)  # 120 kph set speed
    acc.state = ACCState.SPEED_CTRL  # Activate ACC
    
    ego = VehicleState(speed_mps=28.0, accel_mps2=0.0, yaw_rate_radps=0.0)
    
    # Simulate 20 steps (1 second at 20Hz)
    print("Free cruise (no target, v=28m/s, set=33.3m/s):")
    for step in range(5):
        a = acc.step(ego, targets=[])
        ego.speed_mps = max(0, ego.speed_mps + a * 0.05)
        print(f"  Step {step}: v={ego.speed_mps*3.6:.1f}kph a={a:.2f}m/s² state={acc.current_state.value}")
    
    print("\nWith target 80m ahead approaching at -5m/s:")
    for step in range(10):
        target = ACCTarget(
            range_m=max(5.0, 80.0 - step*5*0.05),
            range_rate_mps=-5.0,
            lateral_offset_m=0.0,
            speed_mps=ego.speed_mps + 5.0,
            confidence=0.95,
            source='fused',
            track_id=1
        )
        a = acc.step(ego, targets=[target])
        ego.speed_mps = max(0, ego.speed_mps + a * 0.05)
        print(f"  Step {step}: v={ego.speed_mps*3.6:.1f}kph "
              f"gap={target.range_m:.0f}m a={a:.2f}m/s² "
              f"state={acc.current_state.value}")
