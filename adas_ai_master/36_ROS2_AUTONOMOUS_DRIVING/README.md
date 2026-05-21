# 36 — ROS2 for Autonomous Driving

## Overview
ROS2 (Robot Operating System 2) is the standard middleware for AD research and prototyping. Covers ROS2 Humble architecture, sensor topic design, QoS policies, multi-node AD stack, and integration with CARLA/RViz.

---

## 1. ROS2 Humble Node Architecture for ADAS

```
/camera/image_raw ────────────────────────────────────────────────────────────────┐
/radar/scan ──────────────────────────────────────────────────────────────────────┤
/lidar/points ────────────────────────────────────────────────────────────────────┤
/gps/fix ─────────────────────────────────────────────────────────────────────────┤
/imu/data ────────────────────────────────────────────────────────────────────────┘
                                                                                   │
                         ┌────────────────────────────────────────────────────────┐
                         │             AdasSensorFusionNode                        │
                         │   Subscribes to sensor topics                           │
                         │   Runs AI inference + EKF fusion                        │
                         │   Publishes: /perception/fused_objects                  │
                         └──────────────────────────────────────────────────────┬─┘
                                                                                │
         /perception/fused_objects ─────────────────────────────────────────────┤
                                                                                │
                         ┌──────────────────────────────────────────────────────┘
                         │           PlanningNode                               │
                         │   Subscribes: fused objects + map                    │
                         │   Publishes: /planning/trajectory                    │
                         └────────────────────────────────────────────────────┐
                                                                              │
                         ┌────────────────────────────────────────────────────┘
                         │           ControlNode                              │
                         │   Subscribes: trajectory + vehicle state           │
                         │   Publishes: /vehicle/cmd_vel + /vehicle/steering  │
                         └────────────────────────────────────────────────────
```

---

## 2. Key ROS2 Topics for ADAS

| Topic | Message Type | Hz | Description |
|-------|------------|-----|------------|
| `/camera/image_raw` | `sensor_msgs/Image` | 30 | Uncompressed BGR frame |
| `/camera/image_compressed` | `sensor_msgs/CompressedImage` | 30 | JPEG/H264 compressed |
| `/radar/scan` | `sensor_msgs/LaserScan` | 20 | 2D radar scan (simplified) |
| `/lidar/points` | `sensor_msgs/PointCloud2` | 10 | 3D point cloud |
| `/gps/fix` | `sensor_msgs/NavSatFix` | 10 | GNSS lat/lon/alt |
| `/imu/data` | `sensor_msgs/Imu` | 200 | Acceleration + gyro |
| `/perception/objects` | `vision_msgs/Detection3DArray` | 30 | Fused object list |
| `/planning/trajectory` | `nav_msgs/Path` | 10 | Planned trajectory |

---

## 3. QoS Policy Configuration

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

# For sensor data (occasional loss acceptable)
sensor_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=5
)

# For safety-critical commands (must arrive, queue small)
cmd_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1    # Only most recent command matters
)

# For diagnostic data (must persist for late subscribers)
diag_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    depth=10
)
```

---

## 4. Launch File (Python)

```python
# adas_perception_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='camera_driver',
            executable='camera_node',
            name='front_camera',
            parameters=[{
                'fps': 30,
                'resolution': '1920x1080',
                'camera_id': 0,
            }]
        ),
        Node(
            package='radar_driver',
            executable='radar_node',
            name='front_radar',
            parameters=[{'can_channel': 'can0'}]
        ),
        Node(
            package='adas_perception',
            executable='sensor_fusion_node',
            name='fusion',
            remappings=[
                ('/camera/image_raw', '/front_camera/image_raw'),
            ]
        ),
        Node(
            package='adas_planning',
            executable='planning_node',
            name='planner',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', 'adas_viz.rviz']
        ),
    ])
```

---

## 5. Timestamp Synchronisation (ApproximateTime Policy)

```python
import message_filters

class SynchronisedFusionNode(Node):
    """Subscribe to camera + radar with approximate time synchronisation."""
    
    def __init__(self):
        super().__init__('sync_fusion')
        
        self._camera_sub = message_filters.Subscriber(
            self, Image, '/camera/image_raw')
        self._radar_sub  = message_filters.Subscriber(
            self, PointCloud2, '/radar/points')
        
        # Allow 50ms time difference between messages
        sync = message_filters.ApproximateTimeSynchronizer(
            [self._camera_sub, self._radar_sub],
            queue_size=10,
            slop=0.05
        )
        sync.registerCallback(self._synced_callback)
    
    def _synced_callback(self, camera_msg: Image, radar_msg: PointCloud2):
        """Called with time-aligned camera + radar pair."""
        dt_ms = abs(camera_msg.header.stamp.nanosec -
                     radar_msg.header.stamp.nanosec) / 1e6
        self.get_logger().debug(f'Sync dt = {dt_ms:.2f}ms')
        
        # Run fusion here
```

---

## 6. RViz2 Visualisation Markers

```python
from visualization_msgs.msg import Marker, MarkerArray

def create_detection_marker(det, frame_id: str = 'map') -> Marker:
    """Create RViz2 bounding box marker for a 3D detection."""
    m = Marker()
    m.header.frame_id = frame_id
    m.type   = Marker.CUBE
    m.action = Marker.ADD
    m.id     = det.track_id
    
    m.pose.position.x = det.x
    m.pose.position.y = det.y
    m.pose.position.z = det.z + det.h / 2
    m.pose.orientation.w = 1.0
    
    m.scale.x = det.l    # Length
    m.scale.y = det.w    # Width
    m.scale.z = det.h    # Height
    
    # Colour by class
    colours = {
        'vehicle':    (0.0, 0.0, 1.0),  # Blue
        'pedestrian': (1.0, 0.0, 0.0),  # Red
        'cyclist':    (0.0, 1.0, 0.0),  # Green
    }
    r, g, b = colours.get(det.obj_class, (1.0, 1.0, 0.0))
    m.color.r = r; m.color.g = g; m.color.b = b; m.color.a = 0.7
    
    m.lifetime.sec = 0; m.lifetime.nanosec = 100_000_000  # 100ms
    
    return m
```

---

## 7. Interview Q&A

### L1
**Q: What is the role of ROS2 in autonomous driving development?**  
A: ROS2 is a middleware and toolset for robotics and autonomous systems: (1) Node/topic architecture — modular sensor drivers, perception, planning, control nodes communicate via publish/subscribe; (2) Standard message types — `sensor_msgs/Image`, `PointCloud2`, etc. enable reuse across projects; (3) Launch system — configure and start entire AD stacks with a single Python launch file; (4) Simulation integration — standard interfaces for CARLA, Gazebo, and custom simulators; (5) Bag files — `ros2 bag record` captures all topics to disk for later replay and debugging. Production: ROS2 is the de facto standard in L4 AD research (Waymo prototype stack, Argo, Cruise use ROS2 or closely related DDS-based systems). Production vehicles use AUTOSAR Adaptive (not ROS2) for safety-critical deployment.

### L2
**Q: How do you handle timestamp synchronisation between camera (30Hz) and radar (20Hz) in ROS2?**  
A: Cameras produce at 30Hz (33ms) and radar at 20Hz (50ms) — they are asynchronous and their frames don't naturally align. Solutions: (1) `message_filters.ApproximateTimeSynchronizer` — queues messages from both topics and fires callback when messages arrive within `slop` milliseconds (typically 25-50ms); (2) Timestamp tracking: each sensor message carries hardware timestamp; fusion node computes dt and propagates stale measurements via KF prediction step; (3) Interpolation: if radar track at t=0ms and t=50ms are available, interpolate position for camera frame at t=33ms (linear for constant velocity); (4) Temporal alignment threshold: if timestamp difference > 100ms → do not fuse (too much error from dead reckoning); (5) Production: hardware trigger synchronisation — camera strobe triggers radar acquisition — eliminates sync issue at hardware level.

### L3
**Q: Design a complete ROS2 perception stack for an L4 urban AD vehicle.**  
A: (1) Sensor drivers: camera_driver (MIPI CSI-2 → ROS2 Image); radar_driver (CAN → ARS5xx protocol → RadarTracks); lidar_driver (Velodyne/Ouster Ethernet → PointCloud2); GPS-IMU driver (NovAtel → NavSatFix + Imu). (2) Perception layer: detection_node (subscribes Image, runs YOLO TRT, publishes Detection3DArray); lidar_object_node (subscribes PointCloud2, runs PointPillars TRT, publishes Detection3DArray). (3) Fusion node (AdasSensorFusionNode): time-aligns camera + radar + LiDAR via ApproximateTimeSynchronizer; runs EKF track management; publishes FusedObjectsArray at 30Hz. (4) Localisation node: subscribes GPS + IMU + LiDAR; NDT matching against HD map; publishes Odometry + TF. (5) Planning node: A* on global map + local lattice planner; subscribes FusedObjects + Odometry; publishes Path. (6) Control node: Stanley/MPC controller; publishes Twist (v, omega) → vehicle CAN interface. (7) Diagnostics: `/diagnostics` topic; each node publishes health; `rqt_runtime_monitor` displays faults. (8) Deployment: Docker container per node; docker-compose for full stack; log all topics to rosbag for post-drive analysis.

---

## Files
- [ros2_sensor_fusion.py](ros2_sensor_fusion.py) — AdasSensorFusionNode, FusedPerceptionMsg, detection fusion
