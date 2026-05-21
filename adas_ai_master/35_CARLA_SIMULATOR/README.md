# 35 — CARLA Simulator for ADAS Testing

## Overview
CARLA is the leading open-source autonomous driving simulator. Used for scenario-based ADAS validation, sensor data generation, edge case testing, and AI model training data augmentation.

---

## 1. CARLA vs Other ADAS Simulators

| Simulator | Strength | Use Case |
|---------|---------|---------|
| CARLA 0.9.15 | Open-source, Python API, sensor diversity | Research, SIL validation, training data |
| IPG CarMaker | Real-time, OEM certified | HIL testing, dynamics validation |
| dSPACE AURELION | GPU-based, realistic sensors | Sensor model validation |
| NVIDIA DRIVE Sim | Digital twin, Omniverse | L4 fleet simulation |
| PreScan (Siemens) | MATLAB integration | Safety analysis simulation |
| AVL VSM | Vehicle dynamics | Powertrain + ADAS dynamics |

---

## 2. CARLA Architecture

```
CARLA Server (Unreal Engine 4/5)
      │ TCP socket
      ▼
CARLA Python API / C++ Client
      │
      ├── World management (load map, spawn actors)
      ├── Traffic manager (NPC vehicle AI)
      ├── Sensor management (camera, radar, LiDAR, GPS, IMU)
      └── Spectator / data recording (CARLA recorder)
```

---

## 3. Available Maps and Scenarios

```python
# Load specific map
world = client.load_world('Town05')  # Urban intersection-heavy

# Available maps:
# Town01-07: rural, urban, highway
# Town10HD: detailed urban (photorealistic)
# Town12, Town13: dense city grid
# CARLA Challenge maps: adversarial scenarios
```

---

## 4. Sensor Configuration for ADAS

```python
import carla

# Front camera (8MP equivalent)
cam_bp = blueprint_library.find('sensor.camera.rgb')
cam_bp.set_attribute('image_size_x', '1920')
cam_bp.set_attribute('image_size_y', '1080')
cam_bp.set_attribute('fov', '70')         # Match real camera FOV
cam_bp.set_attribute('sensor_tick', '0.033')  # 30Hz

# Radar (77GHz FMCW equivalent)
radar_bp = blueprint_library.find('sensor.other.radar')
radar_bp.set_attribute('range', '100')
radar_bp.set_attribute('horizontal_fov', '35')
radar_bp.set_attribute('vertical_fov', '10')
radar_bp.set_attribute('points_per_second', '2000')

# LiDAR (64-beam equivalent)
lidar_bp = blueprint_library.find('sensor.lidar.ray_cast')
lidar_bp.set_attribute('channels', '64')
lidar_bp.set_attribute('range', '120')
lidar_bp.set_attribute('rotation_frequency', '20')
lidar_bp.set_attribute('points_per_second', '640000')

# Semantic segmentation camera (ground truth labels)
seg_bp = blueprint_library.find('sensor.camera.semantic_segmentation')
seg_bp.set_attribute('image_size_x', '1920')
seg_bp.set_attribute('image_size_y', '1080')
```

---

## 5. Euro NCAP Scenario Automation

```python
def run_ccrs_aeb_test(client, ego_speed_kph: float = 50.0,
                       initial_gap_m: float = 40.0) -> float:
    """Run Car-to-Car Rear Stationary (CCRs) AEB test.
    Returns impact speed reduction percentage."""
    
    world = client.get_world()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 0.05  # 20Hz simulation
    world.apply_settings(settings)
    
    # Spawn stationary target vehicle
    bp_lib  = world.get_blueprint_library()
    target_bp = bp_lib.find('vehicle.audi.etron')
    spawn_pts = world.get_map().get_spawn_points()
    
    # Target: 40m ahead on straight road
    target_transform = spawn_pts[0]
    target = world.spawn_actor(target_bp, target_transform)
    target.set_simulate_physics(True)
    
    # Spawn ego at initial_gap_m behind target
    ego_bp = bp_lib.find('vehicle.tesla.model3')
    ego_transform = carla.Transform(
        carla.Location(x=target_transform.location.x - initial_gap_m,
                        y=target_transform.location.y,
                        z=target_transform.location.z + 0.1))
    ego = world.spawn_actor(ego_bp, ego_transform)
    
    # Set ego to target speed
    ego_speed_mps = ego_speed_kph / 3.6
    ego.set_target_velocity(
        carla.Vector3D(ego_speed_mps, 0, 0))
    
    # Run simulation until impact or ego stops
    initial_speed = ego_speed_mps
    impact_speed  = 0.0
    
    for tick in range(400):   # 20 seconds max
        world.tick()
        
        ego_vel   = ego.get_velocity()
        ego_loc   = ego.get_location()
        tgt_loc   = target.get_location()
        gap       = ego_loc.distance(tgt_loc)
        ego_speed = math.sqrt(ego_vel.x**2 + ego_vel.y**2)
        
        if gap < 2.0:  # Impact threshold
            impact_speed = ego_speed
            break
        
        if ego_speed < 0.1:  # Stopped before impact
            impact_speed = 0.0
            break
    
    # Cleanup
    ego.destroy()
    target.destroy()
    
    isr = (initial_speed - impact_speed) / initial_speed * 100
    print(f"CCRs test: initial={ego_speed_kph}kph, "
           f"impact={impact_speed*3.6:.1f}kph, ISR={isr:.1f}%")
    return isr
```

---

## 6. Training Data Collection Pipeline

```
CARLA World (Random weather + lighting)
         │
         │ 10,000 frames per condition
         │
    Camera frames (RGB) ──────────────────────────────────────────┐
    Semantic segmentation (auto-labeled) ─────────────────────────┤
    Depth camera (ground truth depth) ────────────────────────────┤ KITTI-format
    LiDAR point clouds ───────────────────────────────────────────┤ export
    Radar detections ─────────────────────────────────────────────┤
    Ground truth 3D bounding boxes (from CARLA actor positions) ──┘
         │
         ▼
    Training dataset
    (10× cheaper than real-world data collection)
```

---

## 7. Sim-to-Real Gap

Key challenges when training on CARLA data and deploying to real world:

| Gap Type | Cause | Mitigation |
|---------|-------|---------|
| Visual fidelity | UE4 textures vs real cameras | Domain randomisation, GAN-based style transfer |
| Sensor noise | CARLA camera = perfect, real = noise | Add camera noise model in CARLA |
| Radar clutter | CARLA radar = ideal, real = multipath | Use CARLA radar with noise + clutter injection |
| Pedestrian behaviour | Random walk, not realistic gait | CARLA 0.9.15 improved pedestrian animation |
| Weather | Good but not photorealistic rain | Mix with real rainy data |

---

## 8. Interview Q&A

### L1
**Q: What is CARLA and what can you test with it for ADAS?**  
A: CARLA (Car Learning to Act) is an open-source simulator built on Unreal Engine, developed by Intel/Toyota research teams. Provides realistic urban/highway environments with configurable weather, lighting, and traffic. ADAS testing: (1) Sensor simulation: camera, LiDAR, radar, GPS, IMU — use Python API to subscribe to sensor data; (2) Scenario testing: spawn pedestrians, vehicles, cyclists; test AEB CCRs/CCRm/AEB-PED; (3) Training data: semantic segmentation, depth, and object bounding boxes generated automatically; (4) Scenario recording/replay: record + replay exact scenarios for regression testing; (5) Fault injection: disable sensors to test degraded mode behavior. Not suitable for: formal functional safety evidence (not ISO 26262 certified), dynamics validation (limited vehicle dynamics model vs CarMaker).

### L2
**Q: How do you use CARLA to generate training data for a pedestrian detector?**  
A: (1) Map selection: Town10HD (dense urban) — good pedestrian density, varied backgrounds; (2) Weather randomisation: iterate over all CARLA weather presets (CloudyNoon, RainyNight, etc.) to cover domain; (3) Spawn pedestrians: 50-200 walkers with random.walk AI enabled; (4) Camera: attach 4 cameras (front, rear, left, right) to ego vehicle; 30fps capture; (5) Auto-labelling: use CARLA's semantic segmentation camera (class ID = 4 for pedestrian) to get pixel-accurate labels; generate bounding boxes from label masks; (6) Depth-based distance: depth camera provides GT distance to each pedestrian — annotate with range information; (7) Output: save as KITTI format (image + .txt label file per frame); (8) Quality filter: remove frames with < 20px pedestrian boxes (too small); blur detection; (9) Scale: ~50,000 frames/day on a single 4090 GPU server running CARLA. Used to pre-train, then fine-tune on real OEM data.

### L3
**Q: Design an automated scenario testing framework using CARLA for AEB validation.**  
A: (1) Scenario library: define 50+ AEB test scenarios in JSON (speed, gap, target type, weather, lighting) covering Euro NCAP + OEM-specific edge cases; (2) Orchestrator: Python script iterates all scenarios, spawns actors via CARLA client, runs in synchronous mode (deterministic replay); (3) AEB plugin: inject ADAS AI model into loop (CARLA subscriptions feed real model); compare AEB activation timing vs ground truth (when would physics-based collision occur); (4) Metrics: compute ISR (Impact Speed Reduction) for each scenario; aggregate by scenario type; (5) CI integration: trigger overnight on every model commit; if AEB-PED ISR drops > 5% → block merge, notify AI team; (6) Failures: scenarios where AEB doesn't meet threshold — automatically extract video + sensor log → add to regression dataset for retraining; (7) Statistical coverage: target 200+ scenario variants per Euro NCAP category (speed sweep, gap sweep, weather sweep); (8) Sim-to-real calibration: re-run 20 physical test track scenarios with ADAS model; validate that CARLA ISR correlates with real ISR within ±10%.

---

## Files
- [carla_adas_sim.py](carla_adas_sim.py) — CarlaADASSimulation class, sensor attachment, NCAP scenarios, pedestrian spawning
