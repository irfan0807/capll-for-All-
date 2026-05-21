"""
Module 45 — Capstone: Mini Autonomous Driving Stack
Integrates: Perception → Sensor Fusion → Path Planning → Control

Hardware target: NVIDIA Jetson Orin NX (simulation-mode runs on any CPU)
Python 3.10+  |  No external dependencies required for demo mode
"""

from __future__ import annotations

import math
import time
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# 1.  Data Structures
# ──────────────────────────────────────────────────────────────────────────────

class ObjectClass(Enum):
    UNKNOWN    = 0
    CAR        = 1
    PEDESTRIAN = 2
    CYCLIST    = 3
    BARRIER    = 4


@dataclass
class TrackedObject:
    track_id:   int
    obj_class:  ObjectClass
    x:          float          # metres, ego-centric forward
    y:          float          # metres, ego-centric left
    vx:         float = 0.0    # m/s forward velocity
    vy:         float = 0.0    # m/s lateral velocity
    width:      float = 1.8
    length:     float = 4.5
    confidence: float = 0.8
    ttc:        float = float('inf')  # Time-to-collision


@dataclass
class EgoState:
    x:           float = 0.0   # Global x position (m)
    y:           float = 0.0   # Global y position (m)
    heading_rad: float = 0.0   # Heading (radians, 0 = east)
    speed_mps:   float = 0.0   # m/s
    yaw_rate:    float = 0.0   # rad/s


@dataclass
class Waypoint:
    x:     float
    y:     float
    speed: float = 0.0


@dataclass
class VehicleCommand:
    acceleration_mps2: float = 0.0
    steering_rad:      float = 0.0
    brake_pct:         float = 0.0    # 0–1


# ──────────────────────────────────────────────────────────────────────────────
# 2.  Perception Module (camera + radar simulation)
# ──────────────────────────────────────────────────────────────────────────────

class PerceptionModule:
    """
    Simulates camera + radar fusion output.
    In production: wraps TensorRT YOLO + Kalman tracker (modules 14/15).
    """

    def detect_objects(self, ego: EgoState,
                       sim_scenario: str) -> List[TrackedObject]:
        """Return object list for given scenario."""
        if sim_scenario == 'highway_follow':
            return [
                TrackedObject(1, ObjectClass.CAR,      x=40.0, y=0.0,
                              vx=25.0, vy=0.0),
                TrackedObject(2, ObjectClass.CAR,      x=80.0, y=3.5,
                              vx=27.0, vy=0.0),
            ]
        elif sim_scenario == 'pedestrian_crossing':
            return [
                TrackedObject(3, ObjectClass.PEDESTRIAN, x=25.0, y=-2.0,
                              vx=0.0, vy=1.0, width=0.6, length=0.6),
            ]
        elif sim_scenario == 'empty_road':
            return []
        else:
            return []


# ──────────────────────────────────────────────────────────────────────────────
# 3.  Threat Assessment (TTC + path overlap)
# ──────────────────────────────────────────────────────────────────────────────

class ThreatAssessor:
    """
    Computes TTC and path overlap for each tracked object.
    Ref: Module 27 (AEB System) for full production version.
    """

    EGO_HALF_WIDTH_M = 0.9       # Half-width of ego vehicle

    def assess(self, objects: List[TrackedObject],
               ego: EgoState) -> List[TrackedObject]:
        for obj in objects:
            closing_speed = ego.speed_mps - obj.vx   # Positive = approaching
            obj.ttc = (obj.x / closing_speed
                       if closing_speed > 0.1 and obj.x > 0
                       else float('inf'))
        return objects

    def most_critical(self, objects: List[TrackedObject],
                      max_ttc: float = 10.0) -> Optional[TrackedObject]:
        """Return closest threat within corridor."""
        in_corridor = [o for o in objects
                       if abs(o.y) < (self.EGO_HALF_WIDTH_M + o.width / 2)
                       and o.x > 0]
        in_time     = [o for o in in_corridor if o.ttc < max_ttc]
        if not in_time:
            return None
        return min(in_time, key=lambda o: o.ttc)


# ──────────────────────────────────────────────────────────────────────────────
# 4.  Path Planner (simple spline-based waypoints)
# ──────────────────────────────────────────────────────────────────────────────

class PathPlanner:
    """
    Generates a path (list of waypoints) in ego-centric frame.
    Ref: Module 20 (Path Planning) for A* / Hybrid-A* version.
    """

    def plan(self, ego: EgoState,
             objects: List[TrackedObject],
             goal_speed_mps: float) -> List[Waypoint]:
        """
        Return 20 waypoints 2m apart on a straight lane-keep path.
        Slows down if threat detected ahead.
        """
        threat_range = min(
            (o.x for o in objects
             if abs(o.y) < 1.5 and o.x > 0 and o.x < 80),
            default=float('inf'))

        target_speed = goal_speed_mps
        if threat_range < 30:
            target_speed = max(0.0, goal_speed_mps * (threat_range / 40))

        waypoints: List[Waypoint] = []
        for i in range(1, 21):
            waypoints.append(Waypoint(x=float(i * 2),
                                       y=0.0,
                                       speed=target_speed))
        return waypoints


# ──────────────────────────────────────────────────────────────────────────────
# 5.  Longitudinal Controller (IDM-based, Module 25)
# ──────────────────────────────────────────────────────────────────────────────

class LongitudinalController:

    def __init__(self,
                 a_max: float = 2.5,
                 b_comfort: float = 3.0,
                 s0: float = 4.0,
                 T_gap: float = 1.5,
                 v_desired: float = 30.0):
        self.a_max     = a_max
        self.b         = b_comfort
        self.s0        = s0
        self.T_gap     = T_gap
        self.v_desired = v_desired

    def compute(self, ego_speed: float,
                lead: Optional[TrackedObject]) -> float:
        """Returns acceleration command (m/s²)."""
        v = ego_speed
        v0 = self.v_desired

        if lead is None:
            # Free-cruise IDM term
            return self.a_max * (1.0 - (v / v0) ** 4)

        s   = max(lead.x - lead.length * 0.5 - self.s0, 0.01)
        dv  = v - lead.vx
        s_star = (self.s0 +
                  v * self.T_gap +
                  v * dv / (2.0 * math.sqrt(self.a_max * self.b)))
        return self.a_max * (1.0 - (v / v0) ** 4 - (s_star / s) ** 2)


# ──────────────────────────────────────────────────────────────────────────────
# 6.  Lateral Controller (Stanley, Module 26)
# ──────────────────────────────────────────────────────────────────────────────

class LateralController:

    def __init__(self, k_gain: float = 1.0, wheel_base: float = 2.7):
        self.k  = k_gain
        self.wb = wheel_base

    def compute(self, ego: EgoState,
                waypoints: List[Waypoint]) -> float:
        """Compute steering angle (rad) using Stanley method."""
        if not waypoints:
            return 0.0

        # Cross-track error: lateral distance to nearest waypoint
        nearest = waypoints[0]
        cte     = nearest.y - ego.y   # Simplified: y of waypoint vs ego y

        # Heading error (simplified: goal is heading 0)
        heading_err = -ego.heading_rad

        speed = max(ego.speed_mps, 0.1)
        steer = heading_err + math.atan2(self.k * cte, speed)
        return max(-0.4, min(0.4, steer))  # Clamp to ±0.4 rad (~23°)


# ──────────────────────────────────────────────────────────────────────────────
# 7.  AEB Safety Override (Module 27)
# ──────────────────────────────────────────────────────────────────────────────

class AEBOverride:

    TTC_WARN_S  = 2.5
    TTC_BRAKE_S = 1.6
    TTC_FULL_S  = 1.0

    def apply(self, cmd: VehicleCommand,
              threat: Optional[TrackedObject]) -> VehicleCommand:
        if threat is None:
            return cmd

        ttc = threat.ttc
        if ttc < self.TTC_FULL_S:
            cmd.acceleration_mps2 = -8.0
            cmd.brake_pct         = 1.0
        elif ttc < self.TTC_BRAKE_S:
            cmd.acceleration_mps2 = -4.0
            cmd.brake_pct         = 0.6
        elif ttc < self.TTC_WARN_S:
            cmd.acceleration_mps2 = min(cmd.acceleration_mps2, 0.0)

        return cmd


# ──────────────────────────────────────────────────────────────────────────────
# 8.  Vehicle Model (bicycle model integration)
# ──────────────────────────────────────────────────────────────────────────────

class VehicleModel:
    """Simple kinematic bicycle model for simulation."""

    WHEEL_BASE = 2.7   # metres

    def step(self, state: EgoState,
             cmd: VehicleCommand,
             dt: float = 0.033) -> EgoState:
        v_next = state.speed_mps + cmd.acceleration_mps2 * dt
        v_next = max(0.0, v_next)   # No reversing in this demo

        beta   = math.atan(math.tan(cmd.steering_rad) * 0.5)
        x_dot  = v_next * math.cos(state.heading_rad + beta)
        y_dot  = v_next * math.sin(state.heading_rad + beta)
        psi_dot = v_next * math.sin(beta) / (self.WHEEL_BASE * 0.5)

        return EgoState(
            x           = state.x + x_dot * dt,
            y           = state.y + y_dot * dt,
            heading_rad = state.heading_rad + psi_dot * dt,
            speed_mps   = v_next,
            yaw_rate    = psi_dot,
        )


# ──────────────────────────────────────────────────────────────────────────────
# 9.  Autonomous Stack Orchestrator
# ──────────────────────────────────────────────────────────────────────────────

class MiniAutonomousStack:
    """
    30Hz control loop integrating all ADAS modules.
    Production equivalent: ROS2 node graph (Module 36).
    """

    def __init__(self, goal_speed_mps: float = 30.0):
        self.perception   = PerceptionModule()
        self.threat_assess = ThreatAssessor()
        self.planner       = PathPlanner()
        self.lon_ctrl      = LongitudinalController(v_desired=goal_speed_mps)
        self.lat_ctrl      = LateralController()
        self.aeb           = AEBOverride()
        self.vehicle       = VehicleModel()
        self.goal_speed    = goal_speed_mps

    def step(self, ego: EgoState,
             scenario: str) -> Tuple[VehicleCommand, EgoState, List[TrackedObject]]:
        """Single control cycle."""

        # 1. Perception (camera + radar fusion)
        objects = self.perception.detect_objects(ego, scenario)

        # 2. Threat assessment (TTC)
        objects = self.threat_assess.assess(objects, ego)
        threat  = self.threat_assess.most_critical(objects)

        # 3. Path planning
        path = self.planner.plan(ego, objects, self.goal_speed)

        # 4. Controllers
        # Longitudinal: IDM — find lead vehicle in ego path
        lead = next((o for o in objects
                     if abs(o.y) < 1.5 and o.x > 0), None)
        acc   = self.lon_ctrl.compute(ego.speed_mps, lead)
        steer = self.lat_ctrl.compute(ego, path)

        cmd = VehicleCommand(acceleration_mps2=acc,
                              steering_rad=steer)

        # 5. AEB safety override
        cmd = self.aeb.apply(cmd, threat)

        # 6. Integrate vehicle model (simulation only)
        next_ego = self.vehicle.step(ego, cmd, dt=1.0/30.0)

        return cmd, next_ego, objects


# ──────────────────────────────────────────────────────────────────────────────
# Demo
# ──────────────────────────────────────────────────────────────────────────────

def run_scenario(scenario: str, n_steps: int = 60,
                 initial_speed: float = 0.0) -> None:
    print(f"\n{'='*55}")
    print(f"  Scenario: {scenario}  ({n_steps} steps @ 30Hz)")
    print(f"{'='*55}")
    print(f"{'Step':>4} {'Speed':>7} {'Acc':>7} {'Steer':>7} "
          f"{'Brake':>6} {'TTC':>8} {'Objects':>8}")
    print("-" * 55)

    stack = MiniAutonomousStack(goal_speed_mps=30.0)
    ego   = EgoState(speed_mps=initial_speed)

    for step in range(n_steps):
        cmd, ego, objs = stack.step(ego, scenario)

        threat = stack.threat_assess.most_critical(objs)
        ttc_str = f"{threat.ttc:.1f}s" if threat and threat.ttc < 99 else "none"

        if step % 10 == 0:
            print(f"{step:>4} {ego.speed_mps:>6.1f}m/s "
                  f"{cmd.acceleration_mps2:>+6.1f}m/s² "
                  f"{math.degrees(cmd.steering_rad):>+6.1f}° "
                  f"{cmd.brake_pct:>5.0%} "
                  f"{ttc_str:>8}  "
                  f"{len(objs):>3} obj")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    print("=" * 55)
    print("  CAPSTONE: Mini Autonomous Driving Stack")
    print("=" * 55)

    # Scenario 1: Highway follow (should maintain safe gap via IDM)
    run_scenario('highway_follow',
                 n_steps=90,
                 initial_speed=28.0)

    # Scenario 2: Pedestrian crossing (AEB should engage)
    run_scenario('pedestrian_crossing',
                 n_steps=60,
                 initial_speed=15.0)

    # Scenario 3: Empty road (accelerate to cruise speed)
    run_scenario('empty_road',
                 n_steps=60,
                 initial_speed=0.0)

    print("\n" + "=" * 55)
    print("Stack modules integrated:")
    print("  ✓ Module 14: Object Detection")
    print("  ✓ Module 15: Object Tracking")
    print("  ✓ Module 20: Path Planning")
    print("  ✓ Module 25: ACC / IDM Controller")
    print("  ✓ Module 26: Lane Keeping (Stanley)")
    print("  ✓ Module 27: AEB Safety Override")
    print("  ✓ Module 36: ROS2-style orchestrator")
    print("=" * 55)
