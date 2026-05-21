"""
20_PATH_PLANNING — ADAS Path Planning Algorithms
A* grid search, polynomial trajectory generation, and MPC-ready path output.
"""

from __future__ import annotations
import numpy as np
import heapq
from typing import List, Tuple, Optional
from dataclasses import dataclass


# ============================================================================
# 1. DATA TYPES
# ============================================================================

@dataclass
class Pose2D:
    """2D vehicle pose in world coordinates."""
    x:   float    # Metres
    y:   float    # Metres
    yaw: float    # Radians

@dataclass
class PathPoint:
    """Single point on a planned path."""
    x:     float
    y:     float
    yaw:   float
    speed: float   # Target speed at this point (m/s)
    curvature: float  # 1/R (1/m)

# ============================================================================
# 2. OCCUPANCY GRID
# ============================================================================

class OccupancyGrid:
    """2D occupancy grid map for path planning.
    Resolution: 0.1m per cell, 100×100 cells = 10×10m (parking) or
                200×200 cells @ 0.2m = 40×40m (urban)."""
    
    def __init__(self, width_m: float = 40.0, height_m: float = 40.0,
                 resolution_m: float = 0.2):
        self.res  = resolution_m
        self.W    = int(width_m  / resolution_m)
        self.H    = int(height_m / resolution_m)
        self.grid = np.zeros((self.H, self.W), dtype=np.float32)   # 0=free, 1=occupied
        self.origin_x = -width_m  / 2   # World position of (0,0) cell
        self.origin_y = -height_m / 2
    
    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """World (m) → grid (col, row)."""
        col = int((x - self.origin_x) / self.res)
        row = int((y - self.origin_y) / self.res)
        return col, row
    
    def grid_to_world(self, col: int, row: int) -> Tuple[float, float]:
        """Grid (col, row) → world (m)."""
        x = col * self.res + self.origin_x + self.res/2
        y = row * self.res + self.origin_y + self.res/2
        return x, y
    
    def mark_occupied(self, x: float, y: float, radius_m: float = 0.5):
        """Mark a circular region as occupied (from object detection)."""
        col, row = self.world_to_grid(x, y)
        r = int(radius_m / self.res)
        for dc in range(-r, r+1):
            for dr in range(-r, r+1):
                if dc**2 + dr**2 <= r**2:
                    cc, rr = col+dc, row+dr
                    if 0 <= cc < self.W and 0 <= rr < self.H:
                        self.grid[rr, cc] = 1.0
    
    def inflate(self, inflation_m: float = 0.3):
        """Inflate obstacles by vehicle half-width for path safety."""
        import cv2
        kernel_size = int(inflation_m / self.res) * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                           (kernel_size, kernel_size))
        self.grid = cv2.dilate(self.grid, kernel).astype(np.float32)
    
    def is_free(self, col: int, row: int) -> bool:
        if not (0 <= col < self.W and 0 <= row < self.H):
            return False
        return self.grid[row, col] < 0.5

# ============================================================================
# 3. A* PATH PLANNER
# ============================================================================

def heuristic(a: Tuple[int,int], b: Tuple[int,int]) -> float:
    """Euclidean heuristic for A*."""
    return np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def astar(grid: OccupancyGrid,
          start_world: Tuple[float, float],
          goal_world:  Tuple[float, float]) -> Optional[List[Tuple[float, float]]]:
    """A* search on occupancy grid.
    
    Returns list of world (x,y) waypoints from start to goal,
    or None if no path found."""
    start = grid.world_to_grid(*start_world)
    goal  = grid.world_to_grid(*goal_world)
    
    if not grid.is_free(*start) or not grid.is_free(*goal):
        return None
    
    # Priority queue: (f_score, node)
    open_set: list = [(0.0, start)]
    came_from: dict = {}
    g_score: dict = {start: 0.0}
    
    # 8-connected neighbours
    neighbours = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    
    while open_set:
        _, current = heapq.heappop(open_set)
        
        if current == goal:
            # Reconstruct path
            path = [grid.grid_to_world(*current)]
            while current in came_from:
                current = came_from[current]
                path.append(grid.grid_to_world(*current))
            path.reverse()
            return path
        
        for dc, dr in neighbours:
            nb = (current[0]+dc, current[1]+dr)
            if not grid.is_free(*nb):
                continue
            move_cost = np.sqrt(dc**2 + dr**2) * grid.res
            new_g = g_score[current] + move_cost
            
            if new_g < g_score.get(nb, float('inf')):
                g_score[nb]  = new_g
                came_from[nb] = current
                f = new_g + heuristic(nb, goal) * grid.res
                heapq.heappush(open_set, (f, nb))
    
    return None  # No path found

# ============================================================================
# 4. POLYNOMIAL TRAJECTORY GENERATION (Highway)
# ============================================================================

def quintic_polynomial(start_state: np.ndarray,
                        end_state:   np.ndarray,
                        T: float) -> callable:
    """5th-order polynomial trajectory.
    State = [position, velocity, acceleration] at start and end.
    
    Used for: smooth lane change trajectory over time T.
    Returns: callable x(t) for 0 <= t <= T."""
    x0, v0, a0 = start_state
    xT, vT, aT = end_state
    
    # Solve 6×6 linear system for polynomial coefficients
    A = np.array([
        [1,  0,  0,  0,   0,    0],
        [0,  1,  0,  0,   0,    0],
        [0,  0,  2,  0,   0,    0],
        [1,  T,  T**2,  T**3,   T**4,    T**5],
        [0,  1,  2*T,   3*T**2, 4*T**3,  5*T**4],
        [0,  0,  2,  6*T,   12*T**2, 20*T**3]
    ])
    b = np.array([x0, v0, a0, xT, vT, aT])
    
    try:
        coeffs = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        # Degenerate case (T=0), return constant
        return lambda t: x0
    
    def poly(t: float) -> float:
        t_vec = np.array([1, t, t**2, t**3, t**4, t**5])
        return float(np.dot(coeffs, t_vec))
    
    return poly

def generate_lane_change_path(current_y: float,
                               target_y: float,
                               velocity_mps: float = 30.0,
                               lane_change_time: float = 3.0,
                               dt: float = 0.1) -> List[PathPoint]:
    """Generate smooth lane change trajectory using quintic polynomial.
    
    current_y: current lateral position (m)
    target_y: target lateral position (m), typical lane width ~3.5m
    velocity_mps: constant longitudinal speed during lane change
    
    Returns list of PathPoints."""
    # Lateral trajectory: start at current_y, end at target_y, zero vel/acc at ends
    lat_traj = quintic_polynomial(
        np.array([current_y, 0.0, 0.0]),    # start: pos, vel, acc
        np.array([target_y,  0.0, 0.0]),    # end: pos, vel, acc (smooth)
        lane_change_time
    )
    
    points = []
    for step in range(int(lane_change_time / dt) + 1):
        t = step * dt
        x = velocity_mps * t
        y = lat_traj(t)
        
        # Yaw: approximate from lateral slope dy/dt / vx
        if step < int(lane_change_time / dt):
            y_next = lat_traj(min(t + dt, lane_change_time))
            dy = (y_next - y) / dt  # lateral velocity at this step
        else:
            dy = 0.0
        yaw = np.arctan2(dy, velocity_mps)
        
        points.append(PathPoint(x=x, y=y, yaw=yaw,
                                speed=velocity_mps, curvature=0.0))
    return points

# ============================================================================
# 5. IDM (INTELLIGENT DRIVER MODEL) — Longitudinal
# ============================================================================

class IDM:
    """Intelligent Driver Model (Treiber, 2000).
    Smooth car-following model for ACC / autonomous following.
    
    Parameters tuned for highway comfort (ADAS-typical)."""
    
    def __init__(self, v_desired_mps: float = 33.3,   # 120kph
                 T_headway:   float = 1.5,              # s
                 a_max:       float = 2.0,              # m/s²
                 b_comfort:   float = 2.5,              # m/s² (comfortable decel)
                 s0_min_gap:  float = 2.0,              # m (min gap to leader)
                 delta:       float = 4.0):             # acceleration exponent
        self.v_des   = v_desired_mps
        self.T       = T_headway
        self.a_max   = a_max
        self.b       = b_comfort
        self.s0      = s0_min_gap
        self.delta   = delta
    
    def acceleration(self, v_ego: float, s_gap: float, 
                      dv: float) -> float:
        """Compute IDM acceleration command.
        
        v_ego: current ego speed (m/s)
        s_gap: gap to leading vehicle (m) — net gap (front bumper to rear bumper)
        dv:    approach speed (v_ego - v_leader), positive = approaching
        
        Returns: acceleration (m/s²), negative = deceleration."""
        # Desired minimum gap
        s_star = self.s0 + v_ego * self.T + v_ego * dv / (2 * np.sqrt(self.a_max * self.b))
        
        # IDM equation
        a = self.a_max * (1 - (v_ego/self.v_des)**self.delta - (s_star/max(s_gap, 0.1))**2)
        return float(np.clip(a, -8.0, self.a_max))  # Physical limits

# ============================================================================
# 6. DEMO
# ============================================================================

if __name__ == "__main__":
    print("=== Path Planning Demo ===\n")
    
    # 1. A* on 20×20m occupancy grid
    occ = OccupancyGrid(width_m=20.0, height_m=20.0, resolution_m=0.2)
    # Add obstacle at (5m, 5m)
    occ.mark_occupied(5.0, 3.0, radius_m=1.0)
    occ.mark_occupied(5.0, 0.0, radius_m=0.5)
    
    path = astar(occ, start_world=(-8.0, 0.0), goal_world=(8.0, 0.0))
    if path:
        print(f"A* found path: {len(path)} waypoints")
        print(f"  Start: {path[0]}, End: {path[-1]}")
    else:
        print("A*: No path found (goal blocked)")
    
    # 2. Quintic lane change (30 m/s, 3.5m to left)
    print("\nLane change trajectory (30 m/s, +3.5m lateral):")
    lc_path = generate_lane_change_path(
        current_y=0.0, target_y=3.5, velocity_mps=30.0, lane_change_time=3.0)
    print(f"  {len(lc_path)} path points over 3s")
    print(f"  Start: x={lc_path[0].x:.1f}m y={lc_path[0].y:.2f}m yaw={np.degrees(lc_path[0].yaw):.1f}°")
    print(f"  End:   x={lc_path[-1].x:.1f}m y={lc_path[-1].y:.2f}m yaw={np.degrees(lc_path[-1].yaw):.1f}°")
    
    # 3. IDM car-following
    print("\nIDM Car-Following (120kph desired, leader 80m ahead at 80kph):")
    idm = IDM(v_desired_mps=33.3)
    v_ego   = 33.3   # 120kph
    s_gap   = 80.0   # 80m gap
    v_lead  = 22.2   # 80kph leader
    dv      = v_ego - v_lead  # Approach speed
    
    for step in range(5):
        a = idm.acceleration(v_ego, s_gap, dv)
        v_ego  = max(0, v_ego + a * 0.1)
        s_gap  = max(0, s_gap - dv * 0.1)
        dv     = v_ego - v_lead
        print(f"  Step {step}: v={v_ego*3.6:.1f}kph gap={s_gap:.1f}m a={a:.2f}m/s²")
