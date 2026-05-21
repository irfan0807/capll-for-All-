# 34 — Automotive Ethernet for ADAS

## Overview
Automotive Ethernet provides the high-bandwidth backbone required for ADAS sensor data (cameras, LiDAR), AI model updates, and real-time ECU communication. Covers 100BASE-T1, 1000BASE-T1, SOME/IP, AVB/TSN, and CAN-to-Ethernet gateway.

---

## 1. Why Automotive Ethernet for ADAS?

| Technology | Bandwidth | Use Case |
|-----------|---------|---------|
| CAN 2.0 | 1 Mbit/s | Legacy ECUs, ADAS basic signals |
| CAN FD | 8 Mbit/s | Body control, sensor status |
| LIN | 20 kbit/s | Mirror motors, simple sensors |
| FlexRay | 20 Mbit/s | Active suspension (legacy) |
| 100BASE-T1 | 100 Mbit/s | Camera ECU, radar ECU to fusion |
| 1000BASE-T1 | 1 Gbit/s | Domain controller backbone |
| 10GBASE-T1 (developing) | 10 Gbit/s | Lidar to AD stack |

**1 uncompressed 8MP camera frame:** 8MP × 3 bytes = 24MB; at 30fps = 720MB/s. **Ethernet is mandatory for camera streaming.**

---

## 2. SOME/IP — Scalable service-Oriented MiddlewarE over IP

SOME/IP is the primary middleware for AUTOSAR Adaptive ECU communication:

```
SOME/IP Message Structure:
  ┌──────────────────────────────────┐
  │ Service ID (2B)                  │
  │ Method/Event ID (2B)             │
  │ Message Length (4B)              │
  │ Client ID (2B)                   │
  │ Session ID (2B)                  │
  │ Protocol Version (1B)            │
  │ Interface Version (1B)           │
  │ Message Type (1B): REQUEST/EVENT │
  │ Return Code (1B)                 │
  │ Payload (variable)               │
  └──────────────────────────────────┘
  
SOME/IP-SD (Service Discovery):
  - Find service: broadcast UDP "Who provides RadarService v2?"
  - Offer service: unicast "I provide RadarService v2 at 192.168.1.11:30502"
```

---

## 3. Time-Sensitive Networking (TSN) for ADAS

TSN extensions to IEEE 802.1 enable deterministic real-time communication:

```
IEEE 802.1AS  — Precision Time Protocol (gPTP): sub-µs sync across ECUs
IEEE 802.1Qbv — Scheduled traffic: time-gated queues, WCET guarantee
IEEE 802.1Qav — Credit-Based Shaper: bandwidth reservation for streams
IEEE 802.1CB  — Frame Replication: redundancy for critical messages

ADAS timing requirement:
  AEB brake command: max 10ms latency, 99.999% reliability
  Camera frame delivery: < 5ms, throughput 250MB/s
  → TSN provides both guarantees on shared Ethernet backbone
```

---

## 4. ADAS Network Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Central Domain Controller (Ethernet Switch)       │
│                    NVIDIA Drive Orin / Qualcomm Snapdragon Ride      │
└──────┬──────────┬────────────┬────────────┬────────────┬────────────┘
       │1000BASE  │1000BASE    │100BASE     │100BASE     │CAN-over-Eth
       ▼          ▼            ▼            ▼            ▼
  Front Camera  LiDAR ECU  Radar (×5)  Rear Camera  CAN Gateway
  ECU (100M)   (1G)        (100M each) ECU (100M)   (to legacy ECUs)
```

---

## 5. Camera Data Transport (MIPI CSI-2 → Ethernet)

```python
# Camera ECU: capture frame, serialize to Ethernet (SOME/IP event)
import struct
import time

def serialize_camera_frame_someip(frame_data: bytes,
                                    service_id: int = 0x0101,
                                    event_id:   int = 0x8001,
                                    session_id: int = 1,
                                    timestamp_us: int = 0) -> bytes:
    """Serialise camera frame as SOME/IP event message.
    Simplified — production uses AUTOSAR-generated serialiser."""
    
    payload_len = len(frame_data) + 8   # 8 bytes header + payload
    
    header = struct.pack('!HHIHHBBBB',
        service_id,         # 2B
        event_id,           # 2B
        payload_len + 8,    # 4B message length (includes SOME/IP header)
        0x0001,             # client_id
        session_id & 0xFFFF,
        0x01,               # protocol version
        0x01,               # interface version
        0x02,               # message type: NOTIFICATION (event)
        0x00                # return code: E_OK
    )
    
    ts_bytes = struct.pack('!Q', timestamp_us)   # 8B timestamp
    
    return header + ts_bytes + frame_data


def deserialize_camera_event(raw: bytes) -> dict:
    """Parse SOME/IP camera event on fusion ECU side."""
    service_id, event_id, msg_len = struct.unpack('!HHI', raw[:8])
    timestamp_us = struct.unpack('!Q', raw[16:24])[0]
    frame_data   = raw[24:]
    
    return {
        'service_id':    service_id,
        'event_id':      event_id,
        'timestamp_us':  timestamp_us,
        'frame_bytes':   len(frame_data),
    }
```

---

## 6. E2E Protection (End-to-End)

E2E profiles protect safety-relevant messages against data corruption on Ethernet:

```
E2E Profile 7 (SOME/IP compatible):
  Header (4B):  Counter (8b) | CRC (24b) | Data ID (optional)

Sender side:    compute CRC over payload + counter
Receiver side:  recompute CRC, compare; if mismatch → E2E error → DTC

Key fields:
  Counter: increments per message; detects lost/reordered messages
  CRC-24: polynomial 0x5D6DCB; detects single-bit and multi-bit errors
  Data ID: ties message content to specific sender (prevents replay)
```

---

## 7. Interview Q&A

### L1
**Q: Why can't CAN be used for ADAS camera data transmission?**  
A: CAN 2.0 maximum bandwidth is 1 Mbit/s. A single uncompressed 1080p camera frame is ~6MB = 6,000 Kbits. At 30fps = 180,000 Kbits/s = 180 Mbit/s required. CAN can't even carry a single frame per second, let alone 30fps. CAN FD (8 Mbit/s) is still 20× too slow. Automotive Ethernet 100BASE-T1 (100 Mbit/s) can carry compressed video (H.264 at ~20Mbit/s per stream) or preprocessed detection results. For raw camera data, 1000BASE-T1 (1 Gbit/s) is standard in ADAS domain controllers.

### L2
**Q: What is SOME/IP-SD and how does it enable dynamic ADAS service discovery?**  
A: SOME/IP-SD (Service Discovery) handles service registration and subscription on the Ethernet backbone: (1) Offer Service: a camera ECU broadcasts "I provide CameraService v1.0 at 192.168.1.12:30502" on ECU startup — repeated every TTL seconds. (2) Find Service: a fusion ECU boots and broadcasts "Who provides CameraService v1.0?" (3) Subscribe Event: fusion ECU sends SubscribeEventGroup to camera ECU; camera ECU acknowledges and adds subscriber to event multicast group. (4) From this point, camera ECU sends detection events to fusion ECU at 30Hz. Benefits: ECUs don't need hardcoded IP/port configurations; new ECUs join by announcing services; failed ECUs detected by missing offers (watchdog behavior). Production: SOME/IP-SD typically runs over UDP multicast on a dedicated VLAN.

### L3
**Q: Design a TSN-based Ethernet backbone for an L3 highway pilot with guaranteed AEB latency.**  
A: (1) Physical layer: 1000BASE-T1 unshielded single-pair Ethernet (BMW group standard); star topology from central switch (Marvell 88Q5050 or similar). (2) Clock synchronisation: gPTP (IEEE 802.1AS) master clock on domain controller; all ECUs slave-sync to <1µs; enables timestamp comparison across ECUs for fusion. (3) Traffic classes: 8 queues using 802.1Qbv scheduled gates; Priority 7 (highest): AEB brake command (5ms budget, 1KB per message); Priority 6: radar detection events (20Hz); Priority 5: camera detections (30Hz); Priority 0-4: background (OTA updates, diagnostics). (4) Schedule configuration: pre-computed gate schedule (time slots) at system integration; AEB command guaranteed 2ms deterministic delivery window every 50ms cycle. (5) Redundancy: 802.1CB frame replication — AEB command sent on two physical paths (dual-ported switch); receiver takes first arriving copy; provides sub-1ms failover. (6) E2E: all safety messages use E2E Profile 7; DTC P0EXX on E2E error; degraded mode: speed limit 100kph until fault cleared.
