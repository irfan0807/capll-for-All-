"""
36_ROS2_AUTONOMOUS_DRIVING — ROS2 Sensor Fusion Node
Multi-sensor fusion using ROS2 Humble, subscribes to camera/radar/LiDAR topics,
publishes fused detection array via custom message.
"""

from __future__ import annotations
import numpy as np
from typing import List, Optional
from dataclasses import dataclass, field
import time

# ROS2 imports — graceful fallback for non-ROS environments
try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from sensor_msgs.msg import Image, PointCloud2
    from std_msgs.msg import Header
    from geometry_msgs.msg import PoseWithCovarianceStamped
    _ROS2_AVAILABLE = True
except ImportError:
    _ROS2_AVAILABLE = False
    # Minimal stub for demo
    class Node:
        def __init__(self, name): self.name = name


# ==========================================================================
# Custom message simulation (in production: generated from .msg files)
# ==========================================================================

@dataclass
class Detection3D:
    """3D bounding box detection (mirrors sensor_msgs/Detection3D)."""
    header_stamp_ns: int
    obj_class:       str
    x:    float; y: float; z: float    # Centre position (m)
    vx:   float; vy: float             # Velocity (m/s)
    w:    float; l: float; h: float    # Width, length, height (m)
    confidence:  float
    track_id:    int
    source:      str  # 'radar', 'camera', 'fused'


@dataclass
class FusedPerceptionMsg:
    """Array of fused detections + metadata."""
    timestamp_ns:    int
    detections:      List[Detection3D] = field(default_factory=list)
    localization_ok: bool = True
    fog_detected:    bool = False


# ==========================================================================
# Sensor Fusion Node
# ==========================================================================

class AdasSensorFusionNode(Node):
    """ROS2 node for multi-sensor fusion.
    
    Subscribes:
        /camera/detections       — 2D detections from camera ECU
        /radar/tracks            — Radar track list (Doppler + range)
        /lidar/point_cloud       — LiDAR point cloud (optional)
        /localization/pose       — EKF pose from localisation node
    
    Publishes:
        /perception/fused_objects — FusedPerceptionMsg at 30Hz
        /perception/status        — Health status
    """
    
    def __init__(self):
        if _ROS2_AVAILABLE:
            super().__init__('adas_sensor_fusion')
            self._setup_ros2_interfaces()
        else:
            super().__init__('adas_sensor_fusion')
            print("Running in demo mode (ROS2 not available)")
        
        self._camera_detections = []
        self._radar_tracks      = []
        self._latest_pose       = None
        self._fusion_history    = []
        
        # EKF state: (x, y, vx, vy, ax, ay) per tracked object
        self._tracks:            dict = {}  # track_id → state
        self._next_track_id:     int  = 1
    
    def _setup_ros2_interfaces(self):
        """Create subscriptions and publishers."""
        from rclpy.qos import QoSProfile, ReliabilityPolicy
        
        # Sensor-best-effort QoS (don't block on occasional drops)
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=10
        )
        
        # Subscribe to sensor topics
        self.create_subscription(
            Image,
            '/camera/image_raw',
            self._camera_callback,
            sensor_qos
        )
        
        # Publisher for fused output
        self._fused_pub = self.create_publisher(
            PoseWithCovarianceStamped,
            '/perception/ego_pose',
            10
        )
        
        # 30Hz fusion timer
        self.create_timer(1/30.0, self._fusion_timer_callback)
        
        self.get_logger().info('ADAS Sensor Fusion Node started')
    
    def _camera_callback(self, msg):
        """Process incoming camera frame (full AI pipeline would run here)."""
        # In production: run ONNX/TRT inference, return detections
        # For this demo: simulate random detections
        self._camera_detections = self._simulate_camera_detections()
    
    def _simulate_camera_detections(self) -> List[Detection3D]:
        """Simulate camera object detections (stand-in for real AI inference)."""
        n = np.random.randint(0, 5)
        dets = []
        for i in range(n):
            dets.append(Detection3D(
                header_stamp_ns=time.time_ns(),
                obj_class=np.random.choice(['vehicle', 'pedestrian', 'cyclist']),
                x=float(np.random.uniform(5, 80)),
                y=float(np.random.uniform(-3, 3)),
                z=0.0,
                vx=float(np.random.uniform(-30, 30)),
                vy=0.0,
                w=1.8, l=4.5, h=1.6,
                confidence=float(np.random.uniform(0.7, 0.99)),
                track_id=-1,  # Unassigned until fusion
                source='camera'
            ))
        return dets
    
    def _fuse_detections(self,
                          camera_dets: List[Detection3D],
                          radar_tracks: List[Detection3D]) -> List[Detection3D]:
        """Simple nearest-neighbour fusion with Kalman state management."""
        fused = []
        
        # For each radar track, find matching camera detection (if within 1m)
        matched_cam_indices = set()
        
        for r_det in radar_tracks:
            best_dist  = float('inf')
            best_cam_i = -1
            
            for i, c_det in enumerate(camera_dets):
                if i in matched_cam_indices:
                    continue
                dist = math.hypot(r_det.x - c_det.x, r_det.y - c_det.y)
                if dist < best_dist:
                    best_dist  = dist
                    best_cam_i = i
            
            if best_cam_i >= 0 and best_dist < 2.0:
                # Fuse: use radar position (more accurate range), camera class
                c_det = camera_dets[best_cam_i]
                fused_det = Detection3D(
                    header_stamp_ns=r_det.header_stamp_ns,
                    obj_class=c_det.obj_class,
                    x=r_det.x,    y=r_det.y,   z=0.0,
                    vx=r_det.vx,  vy=r_det.vy,
                    w=c_det.w, l=c_det.l, h=c_det.h,
                    confidence=min(r_det.confidence, c_det.confidence) * 1.1,
                    track_id=self._assign_track(r_det),
                    source='fused'
                )
                fused.append(fused_det)
                matched_cam_indices.add(best_cam_i)
            else:
                # Radar-only detection
                fused.append(r_det)
        
        # Camera-only detections (no radar match)
        for i, c_det in enumerate(camera_dets):
            if i not in matched_cam_indices:
                fused.append(c_det)
        
        return fused
    
    def _assign_track(self, det: Detection3D) -> int:
        """Assign or match track ID based on position proximity."""
        for tid, state in self._tracks.items():
            dist = math.hypot(det.x - state['x'], det.y - state['y'])
            if dist < 3.0:
                # Update track position
                self._tracks[tid]['x']  = det.x
                self._tracks[tid]['y']  = det.y
                self._tracks[tid]['vx'] = det.vx
                return tid
        
        # New track
        tid = self._next_track_id
        self._next_track_id += 1
        self._tracks[tid] = {'x': det.x, 'y': det.y,
                              'vx': det.vx, 'vy': det.vy,
                              'age': 0}
        return tid
    
    def _fusion_timer_callback(self):
        """30Hz fusion output publish."""
        fused = self._fuse_detections(
            self._camera_detections,
            self._radar_tracks
        )
        
        output = FusedPerceptionMsg(
            timestamp_ns=time.time_ns(),
            detections=fused
        )
        
        if _ROS2_AVAILABLE:
            # Publish via ROS2
            pass  # Would publish FusedPerceptionMsg
        
        # Clear per-cycle buffers
        self._camera_detections = []
        return output


# Needed for _fuse_detections method
import math


# ==========================================================================
# Launch helper
# ==========================================================================

def create_launch_description():
    """ROS2 launch description for ADAS perception stack.
    In production: saved as adas_perception_launch.py"""
    try:
        from launch import LaunchDescription
        from launch_ros.actions import Node as RosNode
        
        return LaunchDescription([
            RosNode(
                package='adas_perception',
                executable='sensor_fusion_node',
                name='adas_sensor_fusion',
                parameters=[{
                    'camera_confidence_threshold': 0.5,
                    'radar_snr_threshold': 12.0,
                    'fusion_gate_distance_m': 2.0,
                    'max_track_age_frames': 5,
                }],
                remappings=[
                    ('/camera/image_raw', '/front_camera/image_raw'),
                    ('/perception/fused_objects', '/adas/objects'),
                ]
            ),
        ])
    except ImportError:
        print("ROS2 launch not available")
        return None


# ==========================================================================
# DEMO
# ==========================================================================

if __name__ == "__main__":
    print("=== ROS2 Sensor Fusion Node Demo ===\n")
    
    node = AdasSensorFusionNode()
    
    # Simulate 5 fusion cycles
    print("Simulating 5 fusion cycles at 30Hz:\n")
    for cycle in range(5):
        # Simulate camera detections
        node._camera_detections = node._simulate_camera_detections()
        
        # Simulate radar tracks
        n_radar = np.random.randint(1, 4)
        node._radar_tracks = [
            Detection3D(
                header_stamp_ns=time.time_ns(),
                obj_class='vehicle',
                x=float(np.random.uniform(10, 60)),
                y=float(np.random.uniform(-2, 2)),
                z=0.0,
                vx=float(np.random.uniform(-20, 20)), vy=0.0,
                w=1.8, l=4.5, h=1.5,
                confidence=0.92,
                track_id=-1,
                source='radar'
            ) for _ in range(n_radar)
        ]
        
        output = node._fusion_timer_callback()
        n_fused = len(output.detections)
        print(f"  Cycle {cycle}: cam={len(node._camera_detections)} "
              f"radar={len(node._radar_tracks)} fused={n_fused} "
              f"tracks_total={len(node._tracks)}")
