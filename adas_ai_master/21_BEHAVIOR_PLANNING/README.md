# 21 — Behavior Planning

## Overview
Behavior planning determines high-level driving actions: lane keep, lane change, merge, yield, stop. Covers Finite State Machines (FSM), rule-based planners, MCTS, and learning-based behavior prediction.

---

## 1. Behavior Planner in the AD Stack

```
Perception  ──► Object List + Lanes + Free Space
Prediction  ──► 5s trajectory predictions for all agents
HD Map      ──► Road topology, rules, traffic lights
                          │
                          ▼
                  BEHAVIOR PLANNER
                  ┌────────────────┐
                  │  Current state │
                  │  + context     │
                  │  → Behaviour   │
                  │  decision      │
                  └────────────────┘
                          │
               ┌──────────┴──────────┐
               │                     │
         Keep Lane             Change Lane Left
         Follow ACC            (if safe and clear)
```

---

## 2. Finite State Machine (FSM)

```python
from enum import Enum, auto
from dataclasses import dataclass

class DrivingState(Enum):
    LANE_KEEP        = auto()
    LANE_CHANGE_LEFT  = auto()
    LANE_CHANGE_RIGHT = auto()
    FOLLOW_LEADER    = auto()
    EMERGENCY_STOP   = auto()
    STOPPED          = auto()

@dataclass
class BehaviorContext:
    ego_speed_mps:    float
    leader_ttc_s:     float   # Time-to-collision with leader
    left_clear:       bool    # Left lane clear for 5s
    right_clear:      bool
    lane_change_request: bool  # Navigation requires lane change
    obstacle_ahead:   bool
    current_state:    DrivingState

class BehaviorFSM:
    """Rule-based behavior FSM for highway ADAS.
    Deterministic, auditable, safety-certifiable."""
    
    MIN_TTC_FOLLOW  = 2.0   # s — minimum acceptable TTC before ACC reaction
    EMERGENCY_TTC   = 0.8   # s — AEB trigger
    
    def step(self, ctx: BehaviorContext) -> DrivingState:
        """Compute next behavior state from context."""
        # Emergency: always override
        if ctx.leader_ttc_s < self.EMERGENCY_TTC or ctx.obstacle_ahead:
            return DrivingState.EMERGENCY_STOP
        
        # Mid-lane-change: continue to completion
        if ctx.current_state in (DrivingState.LANE_CHANGE_LEFT,
                                  DrivingState.LANE_CHANGE_RIGHT):
            return ctx.current_state   # Motion planner will signal completion
        
        # Navigation-driven lane change
        if ctx.lane_change_request:
            if ctx.left_clear:
                return DrivingState.LANE_CHANGE_LEFT
            if ctx.right_clear:
                return DrivingState.LANE_CHANGE_RIGHT
        
        # Following: close gap
        if ctx.leader_ttc_s < self.MIN_TTC_FOLLOW:
            return DrivingState.FOLLOW_LEADER
        
        return DrivingState.LANE_KEEP
```

---

## 3. Prediction Integration

Before deciding to change lanes, the behavior planner checks:

```python
def is_lane_change_safe(ego: dict, target_lane_agents: list,
                         time_horizon: float = 5.0,
                         safety_gap_m: float = 10.0) -> bool:
    """Check if a lane change is safe given predicted trajectories.
    
    ego: {'x': ..., 'y': ..., 'vx': ...}
    target_lane_agents: list of predicted trajectories (each = list of (x,y,t) tuples)"""
    for agent_traj in target_lane_agents:
        for (ax, ay, at) in agent_traj:
            if at > time_horizon:
                break
            # Check if ego trajectory intersects agent position
            ego_x_at_t = ego['x'] + ego['vx'] * at  # Simple CV prediction for ego
            dist = abs(ego_x_at_t - ax)
            if dist < safety_gap_m:
                return False   # Conflict detected
    return True
```

---

## 4. Interaction-Aware Behavior with MCTS

```
Hypothetical lane change action tree:
Root (ego)
├─ Stay in lane
│    ├─ Agent follows (likely 0.7)
│    └─ Agent accelerates (likely 0.3)
└─ Change lane left
     ├─ Agent yields (likely 0.6) → reward: +5 (gap created)
     └─ Agent does not yield (likely 0.4) → reward: -100 (conflict)

Expected value:
  Stay:   0.7 × 0 + 0.3 × (-5) = -1.5
  Change: 0.6 × 5 + 0.4 × (-100) = -37 → Stay is better
```

MCTS enables planning in multi-agent settings — used in Waymo's planning stack.

---

## 5. Traffic Light Handling

```python
class TrafficLightFSM:
    """Stop-and-go behavior for traffic lights."""
    
    def decide_at_light(self, light_state: str, 
                         dist_to_stop_line: float,
                         ego_speed_mps: float,
                         decel_comfortable: float = 2.0) -> str:
        """Returns: 'stop', 'proceed', 'caution'"""
        # Distance needed to stop comfortably
        stop_dist = ego_speed_mps**2 / (2 * decel_comfortable)
        
        if light_state == 'RED':
            if dist_to_stop_line > stop_dist:
                return 'stop'  # Slow down, can stop
            else:
                return 'proceed'  # Cannot stop safely — "dilemma zone"
        
        elif light_state == 'YELLOW':
            if dist_to_stop_line > stop_dist:
                return 'stop'
            else:
                return 'proceed'  # Past point of no return
        
        return 'proceed'  # GREEN
```

---

## 6. Interview Q&A

### L1
**Q: What is a behavior planner and how does it differ from a motion planner?**  
A: Behavior planner makes discrete high-level decisions: should the vehicle keep lane, change lane, yield, or stop? These are categorical outputs (DrivingState enum). Motion planner then takes the behavior decision and generates a continuous, time-parameterised trajectory (set of x,y,v,yaw points) that executes the decision. Analogy: behavior planner decides "change lane left" (like a human deciding to indicate and change), motion planner calculates the exact steering angles and acceleration profile to execute it smoothly.

### L2
**Q: What is the "dilemma zone" at a traffic light and how does an AD system handle it?**  
A: The dilemma zone is the range of positions where a vehicle approaching on yellow cannot both safely stop (too fast / close) nor safely proceed (would still be in intersection on red). For production ADAS: compute stopping distance = v²/2b at every frame; if dist_to_stop_line < stopping_distance at yellow/red detection → "past point of no return" → proceed (emergency stop in intersection is more dangerous). In L4 AD: also models lead vehicles (rear-end risk if stopping when leader proceeds), logged as safety-critical edge case in SOTIF.

### L3
**Q: How would you design a behavior planner for a roundabout scenario for an L4 vehicle?**  
A: Roundabout requires: (1) Map-based yielding rule: vehicle in roundabout has right of way over entering vehicle (most EU/US). (2) Agent prediction: predict all circulating vehicles' exit choices (CNN trajectory predictor, multi-modal). (3) Gap acceptance model: find acceptable gap in circulating traffic. IDM-based: enter when time-headway to oncoming vehicle > 3s. (4) Creep behaviour: approach yield line at 3kph, continuously re-evaluate gap. (5) Exit planning: track current ego position in roundabout, detect correct exit via HD map topology. (6) Edge cases: pedestrians on crosswalk at roundabout entry (AEB); large vehicles (trucks) in roundabout requiring wider berth; rare reverse traffic error. All documented as SOTIF operational scenarios with test coverage requirements.
