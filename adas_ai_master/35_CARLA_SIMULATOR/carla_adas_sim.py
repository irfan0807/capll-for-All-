"""
35_CARLA_SIMULATOR — CARLA ADAS Simulation
Spawn sensors, collect data, run AI inference in CARLA 0.9.15
"""

from __future__ import annotations
import numpy as np
import math
import time
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class SensorReading:
    timestamp: float
    data: np.ndarray
    sensor_type: str


class CarlaADASSimulation:
    """CARLA 0.9.15 simulation runner for ADAS testing.
    
    Spawns ego vehicle + sensors, runs AI inference pipeline,
    logs scenarios for replay and regression testing.
    
    Requires: pip install carla==0.9.15
              CARLA 0.9.15 server running on localhost:2000
    """
    
    def __init__(self, host: str = 'localhost', port: int = 2000,
                  timeout_s: float = 10.0):
        self._connected = False
        try:
            import carla
            self.client = carla.Client(host, port)
            self.client.set_timeout(timeout_s)
            self.world  = self.client.get_world()
            self._carla = carla
            self._connected = True
            print(f"Connected to CARLA: {self.world.get_map().name}")
        except (ImportError, Exception) as e:
            print(f"CARLA not available (demo mode): {e}")
        
        self.ego_vehicle = None
        self.sensors:     List = []
        self._camera_queue = deque(maxlen=5)
        self._radar_queue  = deque(maxlen=10)
    
    def spawn_ego_vehicle(self, blueprint: str = 'vehicle.tesla.model3',
                           spawn_index: int = 0) -> bool:
        """Spawn ego vehicle with Tesla Model 3 blueprint."""
        if not self._connected:
            print("CARLA not connected — demo mode")
            return False
        
        bp_lib = self.world.get_blueprint_library()
        vehicle_bp = bp_lib.find(blueprint)
        
        spawn_points = self.world.get_map().get_spawn_points()
        if spawn_index >= len(spawn_points):
            spawn_index = 0
        
        self.ego_vehicle = self.world.spawn_actor(
            vehicle_bp, spawn_points[spawn_index])
        print(f"Spawned: {blueprint} at spawn {spawn_index}")
        return True
    
    def attach_camera(self, image_size: Tuple[int,int] = (1280, 720),
                       fov: float = 90.0,
                       position_xyz: Tuple = (2.5, 0.0, 1.2)) -> bool:
        """Attach RGB front camera to ego vehicle."""
        if not self._connected or self.ego_vehicle is None:
            return False
        
        bp_lib = self.world.get_blueprint_library()
        cam_bp = bp_lib.find('sensor.camera.rgb')
        cam_bp.set_attribute('image_size_x', str(image_size[0]))
        cam_bp.set_attribute('image_size_y', str(image_size[1]))
        cam_bp.set_attribute('fov', str(fov))
        
        x, y, z = position_xyz
        transform = self._carla.Transform(
            self._carla.Location(x=x, y=y, z=z))
        
        camera = self.world.spawn_actor(cam_bp, transform,
                                         attach_to=self.ego_vehicle)
        camera.listen(self._on_camera_frame)
        self.sensors.append(camera)
        return True
    
    def _on_camera_frame(self, image):
        """Callback for each camera frame."""
        array = np.frombuffer(image.raw_data, dtype=np.uint8)
        array = array.reshape((image.height, image.width, 4))  # BGRA
        bgr   = array[:, :, :3]
        self._camera_queue.append(
            SensorReading(float(image.timestamp), bgr, 'camera'))
    
    def attach_radar(self, range_m: float = 100.0,
                      horizontal_fov_deg: float = 35.0) -> bool:
        """Attach FMCW radar sensor."""
        if not self._connected or self.ego_vehicle is None:
            return False
        
        bp_lib = self.world.get_blueprint_library()
        radar_bp = bp_lib.find('sensor.other.radar')
        radar_bp.set_attribute('range', str(range_m))
        radar_bp.set_attribute('horizontal_fov', str(horizontal_fov_deg))
        radar_bp.set_attribute('points_per_second', '1500')
        
        transform = self._carla.Transform(
            self._carla.Location(x=2.5, y=0.0, z=0.8))
        
        radar = self.world.spawn_actor(radar_bp, transform,
                                        attach_to=self.ego_vehicle)
        radar.listen(self._on_radar_measurement)
        self.sensors.append(radar)
        return True
    
    def _on_radar_measurement(self, data):
        """Callback for radar measurements."""
        points = []
        for det in data:
            points.append([
                det.depth,           # Range (m)
                det.azimuth,         # Azimuth (rad)
                det.altitude,        # Altitude (rad)
                det.velocity,        # Radial velocity (m/s)
            ])
        
        if points:
            arr = np.array(points, dtype=np.float32)
            self._radar_queue.append(
                SensorReading(float(data.timestamp), arr, 'radar'))
    
    def set_autopilot(self, enabled: bool = True):
        """Toggle CARLA autopilot (for traffic vehicle AI control)."""
        if self.ego_vehicle:
            self.ego_vehicle.set_autopilot(enabled)
    
    def get_latest_camera_frame(self) -> Optional[SensorReading]:
        if self._camera_queue:
            return self._camera_queue[-1]
        return None
    
    def get_latest_radar_data(self) -> Optional[SensorReading]:
        if self._radar_queue:
            return self._radar_queue[-1]
        return None
    
    def spawn_pedestrians(self, count: int = 10,
                           allow_random_walk: bool = True) -> List:
        """Spawn pedestrians at random spawn points for AEB testing."""
        if not self._connected:
            return []
        
        ped_bp_lib = self.world.get_blueprint_library().filter('walker.pedestrian.*')
        spawned = []
        
        spawn_points = [
            self._carla.Transform(
                self._carla.Location(x=np.random.uniform(-50, 50),
                                      y=np.random.uniform(-50, 50),
                                      z=0.5))
            for _ in range(count)
        ]
        
        for i, (sp, bp) in enumerate(zip(spawn_points,
                                          np.random.choice(list(ped_bp_lib), count))):
            try:
                ped = self.world.spawn_actor(bp, sp)
                if allow_random_walk:
                    ai_controller_bp = self.world.get_blueprint_library().find(
                        'controller.ai.walker')
                    controller = self.world.spawn_actor(ai_controller_bp,
                                                         self._carla.Transform(),
                                                         attach_to=ped)
                    controller.start()
                    controller.go_to_location(
                        self.world.get_random_location_from_navigation())
                spawned.append(ped)
            except Exception:
                pass
        
        print(f"Spawned {len(spawned)} pedestrians")
        return spawned
    
    def cleanup(self):
        """Destroy all spawned actors."""
        for sensor in self.sensors:
            if sensor.is_alive:
                sensor.destroy()
        if self.ego_vehicle and self.ego_vehicle.is_alive:
            self.ego_vehicle.destroy()
        self.sensors.clear()
        print("CARLA cleanup done")


def generate_ncap_scenario_cmds(scenario: str = 'CCRs',
                                  ego_speed_kph: float = 50.0,
                                  target_gap_m: float = 40.0) -> dict:
    """Generate CARLA actor command configuration for Euro NCAP scenario.
    
    Scenarios: 'CCRs' (stationary), 'CCRm' (moving), 'AEB-PED'"""
    
    configs = {
        'CCRs': {
            'target_speed_kph': 0.0,
            'initial_gap_m': target_gap_m,
            'ego_speed_kph': ego_speed_kph,
            'scenario_name': 'Car-to-Car Rear Stationary',
            'expected_outcome': 'AEB reduces speed by >= 80%'
        },
        'CCRm': {
            'target_speed_kph': 20.0,
            'initial_gap_m': target_gap_m,
            'ego_speed_kph': ego_speed_kph,
            'scenario_name': 'Car-to-Car Rear Moving',
            'expected_outcome': 'AEB reduces impact speed or avoids'
        },
        'AEB-PED': {
            'pedestrian_speed_kph': 5.0,
            'pedestrian_dir': 'perpendicular',
            'ego_speed_kph': 30.0,
            'scenario_name': 'AEB Pedestrian Crossing',
            'expected_outcome': 'AEB stops vehicle before pedestrian path'
        }
    }
    
    return configs.get(scenario, configs['CCRs'])


# ==========================================================================
# DEMO
# ==========================================================================

if __name__ == "__main__":
    print("=== CARLA ADAS Simulation Demo ===\n")
    
    # Instantiate simulation (will run in demo mode if CARLA not available)
    sim = CarlaADASSimulation()
    
    # Show NCAP scenario configurations
    print("Euro NCAP Scenario Configurations:")
    for scenario in ['CCRs', 'CCRm', 'AEB-PED']:
        cfg = generate_ncap_scenario_cmds(scenario)
        print(f"\n  Scenario: {cfg['scenario_name']}")
        print(f"  Ego speed: {cfg['ego_speed_kph']} kph")
        print(f"  Expected: {cfg['expected_outcome']}")
    
    # Simulate sensor reading (demo)
    print("\n\nSimulated sensor data (demo mode):")
    for frame in range(5):
        # Simulate camera frame
        camera_data = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        radar_data  = np.random.rand(10, 4).astype(np.float32)
        radar_data[:, 0] *= 100    # Range 0-100m
        radar_data[:, 3] -= 20     # Velocity -20 to 20 m/s
        
        print(f"  Frame {frame}: camera={camera_data.shape} "
              f"radar_points={len(radar_data)} "
              f"closest={radar_data[:,0].min():.1f}m")
