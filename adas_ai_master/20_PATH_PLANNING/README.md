# 20 — Path Planning for ADAS / Autonomous Driving

## Overview
Path planning bridges perception/prediction and vehicle control. Generates collision-free, comfortable, kinematically feasible trajectories from current pose to goal. Covers A*, polynomial trajectory generation, IDM car-following, and MPC.

---

## 1. Planning Stack Decomposition

```
Route Planner  (A* on road network graph)   → Sequence of road segments
      │
Behaviour Planner  (FSM / MCTS)            → Lane change decision, merging
      │
Motion Planner  (Lattice / MPC / Polynomial)→ Trajectory {x,y,yaw,v}(t)
      │
Controller  (PID / LQR / MPC)              → Steering angle, throttle, brake
```

---

## 2. Occupancy Grid + A*

A* on a 2D occupancy grid is the baseline path planner for parking and low-speed manoeuvres:

**A* algorithm:**
$$f(n) = g(n) + h(n)$$

- $g(n)$: cost from start to node n (cumulative path cost)
- $h(n)$: admissible heuristic to goal (Euclidean distance)
- Optimal if h is admissible (never overestimates)

**Occupancy grid inflation:** Inflate obstacles by vehicle half-width (0.3m) before planning — ensures path is clear for the full vehicle body.

---

## 3. Quintic Polynomial Trajectory

For lane changes and smooth target point reaching:

$$x(t) = c_0 + c_1 t + c_2 t^2 + c_3 t^3 + c_4 t^4 + c_5 t^5$$

Boundary conditions (6 equations for 6 unknowns):
- Position, velocity, acceleration at $t=0$ and $t=T$

**Why quintic?** Ensures zero acceleration at start and end → comfortable, no jerk discontinuity. Cubic (3rd order) polynomial creates jerk steps — fails passenger comfort and vehicle dynamics tests.

---

## 4. IDM (Intelligent Driver Model)

$$a_{IDM} = a_{max}\left[1 - \left(\frac{v}{v_0}\right)^\delta - \left(\frac{s^*(v, \Delta v)}{s}\right)^2\right]$$

$$s^*(v, \Delta v) = s_0 + vT + \frac{v\Delta v}{2\sqrt{a_{max}b}}$$

| Parameter | Typical Value | Effect |
|-----------|--------------|--------|
| $v_0$ | 33.3 m/s (120kph) | Desired speed |
| $T$ | 1.5s | Time headway (safe gap) |
| $s_0$ | 2.0m | Minimum standstill gap |
| $a_{max}$ | 2.0 m/s² | Max acceleration |
| $b$ | 2.5 m/s² | Comfortable deceleration |

---

## 5. Model Predictive Control (MPC) for Path Tracking

MPC optimises over a receding horizon $N$ steps:

$$\min_{u_0,...,u_{N-1}} \sum_{k=0}^{N-1} \|x_k - x_{ref,k}\|^2_Q + \|u_k\|^2_R + \|u_k - u_{k-1}\|^2_{R_\Delta}$$

Subject to:
- Vehicle kinematic model (bicycle model)
- Steering limits: $|\delta| \leq 30°$
- Jerk limits: $|\dot{\delta}| \leq 0.5$ rad/s

**Bicycle model (linearised):**
$$\begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\psi} \end{bmatrix} = \begin{bmatrix} v\cos\psi \\ v\sin\psi \\ v\tan\delta / L \end{bmatrix}$$

where $L$ = wheelbase (~2.7m), $\delta$ = steering angle, $\psi$ = heading.

---

## 6. Cost Function Design

```python
def trajectory_cost(path_points: list, obstacles: list,
                     v_ref: float = 30.0) -> float:
    """Weighted cost function for trajectory evaluation.
    Used in lattice planner to select best trajectory candidate."""
    
    WEIGHT_SMOOTHNESS   = 1.0
    WEIGHT_COMFORT      = 0.5
    WEIGHT_OBSTACLE     = 100.0
    WEIGHT_SPEED        = 0.3
    
    cost = 0.0
    
    for i, pt in enumerate(path_points):
        # Smoothness: penalise high curvature (lateral discomfort)
        cost += WEIGHT_SMOOTHNESS * pt.curvature**2
        
        # Speed deviation
        cost += WEIGHT_SPEED * (pt.speed - v_ref)**2
        
        # Obstacle proximity
        for obs in obstacles:
            dist = ((pt.x - obs[0])**2 + (pt.y - obs[1])**2)**0.5
            if dist < 2.0:  # Danger zone < 2m
                cost += WEIGHT_OBSTACLE / (dist + 0.1)
    
    return cost
```

---

## 7. Interview Q&A

### L1
**Q: What is the difference between global planning (route) and local planning (trajectory)?**  
A: Global route planning uses a road network graph (navigation map) to find the sequence of road segments from origin to destination — typically A* or Dijkstra on a map graph. This produces a route (set of road IDs) but no time or dynamic constraints. Local trajectory planning generates the time-parameterised path $(x, y, v)(t)$ over the next 3-10 seconds, respecting vehicle dynamics, traffic rules, and detected obstacles. Route planning: seconds, metres precision; Trajectory planning: milliseconds, centimetre precision.

### L2
**Q: Why is the quintic polynomial preferred over cubic for lane change trajectory generation?**  
A: A cubic polynomial (4 coefficients) can match start/end position and velocity — but leaves acceleration discontinuous at the boundary. Discontinuous acceleration → jerk step → passenger discomfort and potential ECU torque limit triggering. A quintic polynomial (6 coefficients) matches position, velocity, AND acceleration at both endpoints — guarantees a smooth profile with zero acceleration at start/end. This is critical for lane change approval in ISO 17361 (LCA) and passenger comfort ratings.

### L3
**Q: Compare lattice planner vs MPC for highway autonomous driving at 130kph.**  
A: Lattice planner: pre-generates a set of candidate trajectories (sampling lateral offsets and speeds), evaluates each by cost function, selects minimum cost. Advantages: handles multi-modal scenarios (multiple trajectories), simple to add constraints. Disadvantages: discrete sampling may miss optimal trajectory; scales poorly with state space. MPC: continuously optimises over a receding horizon using the full vehicle model. Advantages: guaranteed optimality within model, handles constraints natively (steering limits, jerk). Disadvantages: requires fast QP solver (OSQP ~1ms), model mismatch causes tracking error. At 130kph: MPC preferred for smooth tracking accuracy; lattice for lane change decision because it naturally evaluates multiple lane options simultaneously.

---

## Files
- [path_planner.py](path_planner.py) — OccupancyGrid, A*, quintic polynomial, IDM, cost function
