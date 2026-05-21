"""
26_LKA_AI_SYSTEM — Lane Keeping Assist AI
Lateral control using lane detection, EKF-based state estimation,
and PID/MPC steering controller.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum


class LKAState(Enum):
    INACTIVE      = 'inactive'
    MONITORING    = 'monitoring'   # Lane detected, hands-on-wheel
    ACTIVE        = 'active'       # Applying steering correction
    INTERVENTION  = 'intervention' # Stronger correction (close to lane departure)
    WARNING       = 'warning'      # Vibration + audio (hands required)


@dataclass
class LaneState:
    """Lane state from camera lane detection."""
    lateral_offset_m:   float   # + = too far right, - = too far left
    heading_error_rad:  float   # Vehicle heading vs lane heading
    curvature_inv_m:    float   # 1/R (1/m), positive = turning left
    left_detected:      bool
    right_detected:     bool
    confidence:         float   # 0-1


@dataclass
class VehicleState:
    speed_mps:       float
    yaw_rate_radps:  float
    steering_deg:    float
    hands_on_wheel:  bool   # From DMS / capacitive steering detection


class LKAPIDController:
    """PD controller for lane keeping.
    Classic, computationally light, ISO 26262 certifiable.
    
    Steering correction: 
      δ_cmd = Kp × e_lat + Kd × ė_lat + Kff × κ
    where e_lat = lateral offset, κ = curvature feedforward"""
    
    def __init__(self, Kp: float = 0.5, Kd: float = 0.2,
                 Kff: float = 15.0, wheelbase_m: float = 2.7):
        self.Kp  = Kp
        self.Kd  = Kd
        self.Kff = Kff
        self.L   = wheelbase_m
        
        self._prev_err  = 0.0
        self._dt        = 0.033   # 30Hz camera input
    
    def compute(self, lane: LaneState,
                 vehicle_speed: float) -> float:
        """Returns steering angle correction (degrees).
        Positive = steer right."""
        err = lane.lateral_offset_m
        
        # Derivative
        d_err = (err - self._prev_err) / self._dt
        self._prev_err = err
        
        # Feedforward: Ackermann curvature to steering
        steer_ff = np.degrees(np.arctan(self.L * lane.curvature_inv_m))
        
        # Speed-dependent gain scaling (reduce at low speed)
        speed_gain = min(vehicle_speed / 10.0, 1.0)
        
        steer_cmd = speed_gain * (self.Kp * err + self.Kd * d_err) + steer_ff
        
        return float(np.clip(steer_cmd, -10.0, 10.0))   # Max ±10° correction


class LKAMPCController:
    """Model Predictive Control for lane keeping.
    Optimises steering over N-step horizon.
    Simplified 1D lateral MPC for demonstration."""
    
    def __init__(self, N: int = 20, dt: float = 0.033,
                 wheelbase_m: float = 2.7,
                 max_steer_deg: float = 8.0):
        self.N    = N
        self.dt   = dt
        self.L    = wheelbase_m
        self.max_steer = np.radians(max_steer_deg)
    
    def compute(self, lane: LaneState, speed_mps: float) -> float:
        """Simplified MPC: compute optimal steering for N-step ahead.
        Returns steering angle in degrees."""
        # State: [lateral_error, heading_error]
        x = np.array([lane.lateral_offset_m, lane.heading_error_rad])
        
        # Simple LQR-like state feedback at each horizon step
        Q = np.diag([1.0, 0.5])   # Cost on [lateral_err, heading_err]
        R_steer = 0.1              # Cost on steering input
        
        # Bicycle model linearised
        # d(e_lat)/dt   = v * ψ_err
        # d(ψ_err)/dt   = v/L * tan(δ) ≈ v/L * δ (small angle)
        A = np.array([[0, speed_mps],
                      [0, 0]])
        B = np.array([[0], [speed_mps/self.L]])
        
        # Discrete approximation
        Ad = np.eye(2) + A * self.dt
        Bd = B * self.dt
        
        # Optimal gain K from Riccati equation (simplified as P=Q for demo)
        P = Q.copy()
        for _ in range(100):
            P = Ad.T @ P @ Ad - Ad.T @ P @ Bd @ \
                np.linalg.inv(R_steer + Bd.T @ P @ Bd) @ Bd.T @ P @ Ad + Q
        
        K = np.linalg.inv(R_steer + Bd.T @ P @ Bd) @ Bd.T @ P @ Ad
        
        steer_rad = float(-(K @ x))
        steer_rad = np.clip(steer_rad, -self.max_steer, self.max_steer)
        return float(np.degrees(steer_rad))


class LKASystem:
    """Complete LKA system with state machine, safety monitor,
    and driver hands-on detection."""
    
    # Safety parameters
    MAX_CORRECTION_DEG = 8.0       # Maximum LKA steering correction
    DEPARTURE_WARN_M   = 0.3       # m to lane edge before warning
    MIN_SPEED_MPS      = 5.6       # 20kph minimum activation speed
    MAX_SPEED_MPS      = 50.0      # 180kph maximum (highway only)
    HANDS_TIMEOUT_S    = 15.0      # Hands-off timeout before escalation
    
    def __init__(self, use_mpc: bool = False):
        self.state    = LKAState.INACTIVE
        self.pid_ctrl = LKAPIDController()
        self.mpc_ctrl = LKAMPCController() if use_mpc else None
        self._controller = self.mpc_ctrl if use_mpc else self.pid_ctrl
        
        self._hands_off_timer = 0.0
        self._steer_cmd = 0.0
    
    def activate(self):
        self.state = LKAState.MONITORING
    
    def deactivate(self):
        self.state = LKAState.INACTIVE
        self._steer_cmd = 0.0
    
    def step(self, lane: LaneState, vehicle: VehicleState,
              dt: float = 0.033) -> Tuple[float, LKAState]:
        """Main LKA step.
        Returns: (steering_correction_deg, new_state)"""
        
        if self.state == LKAState.INACTIVE:
            return 0.0, self.state
        
        # Speed gates
        if vehicle.speed_mps < self.MIN_SPEED_MPS:
            self.state = LKAState.MONITORING
            return 0.0, self.state
        
        # Lane confidence gate
        if lane.confidence < 0.5 or (not lane.left_detected and not lane.right_detected):
            self.state = LKAState.MONITORING
            return 0.0, self.state
        
        # Hands-off monitoring (for L2: require hands on wheel)
        if not vehicle.hands_on_wheel:
            self._hands_off_timer += dt
        else:
            self._hands_off_timer = 0.0
        
        if self._hands_off_timer > self.HANDS_TIMEOUT_S:
            self.state = LKAState.WARNING
            return 0.0, self.state  # Do not apply correction — require driver to take over
        
        # Compute steering correction
        if self.mpc_ctrl:
            steer_corr = self.mpc_ctrl.compute(lane, vehicle.speed_mps)
        else:
            steer_corr = self.pid_ctrl.compute(lane, vehicle.speed_mps)
        
        steer_corr = float(np.clip(steer_corr,
                                    -self.MAX_CORRECTION_DEG,
                                    self.MAX_CORRECTION_DEG))
        
        self._steer_cmd = steer_corr
        
        # Determine state
        if abs(lane.lateral_offset_m) > self.DEPARTURE_WARN_M:
            self.state = LKAState.INTERVENTION
        else:
            self.state = LKAState.ACTIVE
        
        return steer_corr, self.state


# ==========================================================================
# DEMO
# ==========================================================================

if __name__ == "__main__":
    print("=== LKA System Demo ===\n")
    
    lka_pid = LKASystem(use_mpc=False)
    lka_pid.activate()
    
    vehicle = VehicleState(speed_mps=30.0, yaw_rate_radps=0.0,
                            steering_deg=0.0, hands_on_wheel=True)
    
    # Simulate drift from lane centre
    print("PID LKA — vehicle drifting 0.5m right:")
    lateral_err = 0.5
    for step in range(8):
        lane = LaneState(
            lateral_offset_m=lateral_err,
            heading_error_rad=0.05,
            curvature_inv_m=0.001,
            left_detected=True, right_detected=True,
            confidence=0.92
        )
        steer, state = lka_pid.step(lane, vehicle)
        # Simulate correction effect
        lateral_err = max(0.0, lateral_err - abs(steer) * 0.02)
        print(f"  Step {step}: lat_err={lateral_err:.3f}m "
              f"steer={steer:.2f}° state={state.value}")
    
    print("\nMPC LKA — same scenario:")
    lka_mpc = LKASystem(use_mpc=True)
    lka_mpc.activate()
    lateral_err = 0.5
    for step in range(8):
        lane = LaneState(
            lateral_offset_m=lateral_err,
            heading_error_rad=0.05,
            curvature_inv_m=0.001,
            left_detected=True, right_detected=True,
            confidence=0.92
        )
        steer, state = lka_mpc.step(lane, vehicle)
        lateral_err = max(0.0, lateral_err - abs(steer) * 0.02)
        print(f"  Step {step}: lat_err={lateral_err:.3f}m "
              f"steer={steer:.2f}° state={state.value}")
