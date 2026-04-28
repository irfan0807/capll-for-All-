# Path Planning and Vehicle Control

## 1. Planning Hierarchy

```
Global Route Planning (HD Map + Graph Search)
        │  Target destination, roads to take
        ▼
Behavioral Planning (Scene Understanding + Rules)
        │  Lane changes, yields, turns, merges
        ▼
Local Trajectory Planning (Motion Planning)
        │  Smooth drivable path with velocity profile
        ▼
Control (PID / MPC)
        │  Throttle, brake, steering commands
        ▼
  Vehicle Actuators
```

---

## 2. Global Route Planning – Dijkstra / A*

### Graph Representation (HD Map)

```
Nodes:   Lane segments (each ~5m long), intersections
Edges:   Adjacency (drivable transitions), cost = travel time

Edge cost:
  cost = length/speed_limit + turn_penalty + traffic_penalty

Dijkstra's Algorithm:
  1. Priority queue Q, dist[start] = 0, all others = ∞
  2. Pop minimum-cost node u from Q
  3. For each neighbour v of u:
       new_cost = dist[u] + cost(u,v)
       if new_cost < dist[v]:
           dist[v] = new_cost
           parent[v] = u
           push v to Q
  4. Reconstruct path from start to goal via parent[]

A* improvement:
  f(n) = g(n) + h(n)
  g(n) = cost from start to n
  h(n) = heuristic (Euclidean distance to goal)
  → Faster convergence for L2 heuristic-admissible domains
```

---

## 3. Behavioral Planning – Finite State Machine

```
States:
  LANE_FOLLOWING   → Normal driving in current lane
  LANE_CHANGE_LEFT → Executing left lane change
  LANE_CHANGE_RIGHT→ Executing right lane change
  TURN_LEFT        → At intersection, turning left
  TURN_RIGHT       → At intersection, turning right
  YIELD            → Yielding at junction/sign
  FOLLOW_VEHICLE   → ACC follow mode
  EMERGENCY_STOP   → AEB triggered

Transitions (LANE_FOLLOWING → LANE_CHANGE_LEFT):
  prereq: LEFT_LANE_FREE = true (> 4s gap, LiDAR + Radar confirm)
  prereq: ROUTE says change left within 200m
  prereq: EGO_SPEED > 30 km/h (no lane change at slow speed)
  
Output per cycle:
  BehaviorDecision {
    target_lane_id,
    target_speed_mps,
    follow_object_id,
    must_stop,
    yield_to_objects[]
  }
```

---

## 4. Local Trajectory Planning – Frenet Frame

### Why Frenet Frame?

```
Instead of (x, y) Cartesian:
  s = longitudinal distance along reference path (m)
  d = lateral offset from reference path (m)

Benefits:
  - Lane keeping = keep d ≈ 0
  - Lane change = vary d from 0 to lane_width
  - Speed = ds/dt
  - Lateral comfort = limit d''
```

### Jerk-Minimal Polynomial Trajectory

```
For smooth lateral motion (d(t)):
  d(t) = a0 + a1·t + a2·t² + a3·t³ + a4·t⁴ + a5·t⁵

Boundary conditions (6 unknowns → 6 equations):
  At t=0:      d(0) = d_i,   d'(0) = d'_i,   d''(0) = d''_i
  At t=T_f:    d(T) = d_f,   d'(T) = d'_f,   d''(T) = d''_f

Solve: [a0..a5] = A^(-1) · b  (matrix inversion of Vandermonde-like system)

For longitudinal motion (s(t)):
  s(t) = b0 + b1·t + b2·t² + b3·t³  (quartic, jerk-minimum)

Cost function for trajectory candidate selection:
  J = w_safe · d_collision
    + w_legal · v_over_limit
    + w_comfort · ∫jerk²dt
    + w_efficiency · (v_target - v_actual)²
```

### Trajectory Candidates

```
Generate N×M candidate trajectories:
  N = 5 lateral targets (d = -1.5m, -0.75m, 0, +0.75m, +1.5m)
  M = 3 time horizons (T = 2s, 3s, 5s)
  → 15 trajectories per cycle

For each candidate:
  1. Generate 5th-order polynomial
  2. Check collision with predicted object paths
  3. Check comfort limits: |lateral_accel| < 3 m/s²
  4. Evaluate cost function
  5. Select minimum cost non-colliding trajectory
```

---

## 5. PID Controller (Longitudinal)

### Velocity Control

```
Error: e(t) = v_target - v_actual

PID control law:
  u(t) = Kp·e + Ki·∫e·dt + Kd·de/dt

Automotive parameters (typical highway, tuned):
  Kp = 0.5  (fast response)
  Ki = 0.1  (eliminate steady-state error)
  Kd = 0.05 (damping, reduce overshoot)

Output mapping:
  u > 0 → throttle = clip(u, 0, 100%)
  u < 0 → brake = clip(-u * brake_gain, 0, 100%)

Anti-windup:
  If actuator saturated: stop integral accumulation
  if (throttle == 100% && e > 0) integral unchanged;
```

### Adaptive Cruise Control (ACC) – Safe Following Distance

```
Desired following distance:
  d_safe = d_min + v_ego · THW  (time-headway, THW = 1.5s for L4)
  d_min = 3.0m (absolute minimum)

ACC modes:
  GAP_CONTROL: follow lead vehicle at d_safe
    v_target = v_lead + k_gap · (d_actual - d_safe)
  SPEED_CONTROL: no lead vehicle, cruise at v_set
    v_target = v_set

Speed source priority:
  1. AEB override (minimum speed)
  2. Traffic sign speed limit
  3. ACC set speed
  4. Route curvature-consistent speed
```

---

## 6. Stanley Controller (Lateral)

### Algorithm

```
Used for: path tracking at low-to-medium speeds

δ(t) = ψ_e + arctan(k · e_fa / v)

Where:
  ψ_e  = heading error (angle between ego and path tangent, rad)
  e_fa = cross-track error at front axle (m, + = left of path)
  v    = forward speed (m/s)
  k    = gain (tunable, typically 0.5-2.0)
  δ    = steering angle command (rad)

Properties:
  - Proven Lyapunov stability for positive k
  - Simple to implement
  - Limitations: poor at high speed (use MPC above ~80 km/h)
```

---

## 7. Model Predictive Control (MPC) – High-Speed Lateral

### Problem Formulation

```
State: x = [x_pos, y_pos, yaw, v, steering_angle]
Input: u = [steering_rate, acceleration]

Minimise over horizon N:
  J = Σ_{k=0}^{N-1} [ (x_k - x_ref_k)^T Q (x_k - x_ref_k)
                      + u_k^T R u_k ]
    + (x_N - x_ref_N)^T Q_f (x_N - x_ref_N)

Subject to:
  x_{k+1} = f(x_k, u_k)           (vehicle model)
  |steering_angle| ≤ 0.436 rad      (25°)
  |steering_rate|  ≤ 0.175 rad/s    (10°/s)
  |acceleration| ≤ 3.0 m/s²
  |lateral_accel| ≤ 4.0 m/s²       (comfort)

Solver: Quadratic Programming (OSQP, ~1ms on automotive-grade CPU)
Prediction horizon N = 20 steps @ 0.1s = 2s ahead
```

---

## 8. Brake Distribution

```
Total braking force requirement: F_brake = m_vehicle · a_decel

Distribution:
  Front axle: 70% (primary braking, better traction load)
  Rear axle:  30%

Emergency braking (AEB):
  Target deceleration: -0.8g = -7.84 m/s²
  Brake pressure: P = F / (2 × caliper_area × brake_factor)
  Typical: ~120 bar on all corners
  ABS active: modulate at 10-20 Hz per wheel to prevent lockup
```

---

## 9. CAN Actuator Interface

```
Output CAN message 0x2A0 (vehicle command, 10Hz):
  Byte 0:   Target speed high byte
  Byte 1:   Target speed low byte      (raw = speed_kph / 0.1, offset 0)
  Byte 2:   Steering angle high byte
  Byte 3:   Steering angle low byte    (raw = angle_deg / 0.1 + 2048, signed)
  Byte 4:   Brake pressure             (raw = pressure_bar / 0.5)
  Byte 5:   Throttle position          (raw = throttle_pct / 0.4)
  Byte 6:   Gear: D=1, N=2, R=3, P=4
  Byte 7:   Control mode: 0=manual, 1=ACC, 2=L4, 3=override
```
