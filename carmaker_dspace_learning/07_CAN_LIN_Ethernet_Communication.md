# 07 — CAN / LIN / Ethernet Communication on dSPACE

> **Boards**: DS1552 (CAN FD), DS4330 (Automotive Ethernet)  
> **Prerequisite**: ConfigurationDesk (05), ECU Signal Mapping (06)  
> **Outcome**: Configure and test all three bus types; inject errors; monitor bus load

---

## 1. Protocol Overview

```
Bus Protocol Comparison:
──────────────────────────────────────────────────────────────────────
Protocol   Speed          Topology       Typical Use in Car
──────────────────────────────────────────────────────────────────────
CAN 2.0    1 Mbit/s       Bus            Powertrain, chassis, body
CAN FD     8 Mbit/s data  Bus            ADAS, gateway, domain ctrl
LIN        20 kbit/s      Single-master  Window, seat, simple sensors
FlexRay    10 Mbit/s      Bus/star       Safety-critical (BBW, EPS)
100BASE-T1 100 Mbit/s     Point-to-point ADAS cameras, DoIP
1000BASE-T1 1 Gbit/s      Point-to-point Backbone, autonomous
──────────────────────────────────────────────────────────────────────
```

---

## 2. CAN FD on dSPACE (DS1552)

### CAN FD Frame Format
```
CAN FD Frame:
────────────────────────────────────────────────────────────────
SOF │ ID (11/29b) │ EDL│BRS│ DLC │    Data (0–64 bytes)    │ CRC │EOF
                   1   1         Variable length
                   │   └── Bit Rate Switch (nominal→data rate)
                   └── Extended Data Length flag

Nominal phase: 500 kbit/s (arbitration, fixed)
Data phase:    2–8 Mbit/s (after BRS bit, variable)
────────────────────────────────────────────────────────────────
```

### DS1552 CAN FD Configuration (ConfigurationDesk)
```
Channel 1 settings:
  Nominal baud rate:  500 kbit/s
  Data baud rate:     2000 kbit/s
  Sample point:       75% (nominal), 80% (data)
  Termination:        120 Ω (enable if bus end)
  Protocol:           CAN FD (ISO 11898-7)
  Listen-only mode:   OFF (active node)

Bus timing (500 kbit/s):
  Time quanta = 80 ns (at 50 MHz clock)
  Total TQ per bit = 25
  Sync_seg = 1 TQ
  Prop_seg = 13 TQ
  Phase_seg1 = 7 TQ
  Phase_seg2 = 4 TQ
  SJW = 4 TQ
```

### CAN DBC Import and Signal Access
```
DBC import workflow:
1. ConfigurationDesk: CAN Channel → Import DBC
   Select: Vehicle_Network_v2.3.dbc

2. DBC auto-generates:
   Tx PDUs (HIL sends these):  VehicleSpeed, EngineStatus, WheelSpeeds
   Rx PDUs (HIL receives):     AEB_BrakeCmd, ACCTargetSpeed, LKA_Steer

3. Map to application:
   AEB_BrakeCmd.BrakePressure → Simulink inport "ECU_BrakeCmd"

4. In ControlDesk: create instrument panel
   Variable: "CAN_Rx.AEB_BrakeCmd.BrakePressure"
   Display: Numeric + time plot
```

### CAN Bus Load Monitoring
```python
# Monitor CAN bus load via ControlDesk variable
# Typical: < 40% = healthy, > 70% = risk of delays

import controldesk  # dSPACE Python API

def monitor_bus_load(duration_s=10, threshold_pct=70):
    """Monitor CAN bus load and alert if above threshold."""
    samples = []
    for _ in range(duration_s * 10):
        load = controldesk.get("DS1552.CAN1.BusLoad_pct")
        samples.append(load)
        if load > threshold_pct:
            print(f"WARNING: Bus load {load:.1f}% > {threshold_pct}%")
        time.sleep(0.1)

    print(f"Average bus load: {sum(samples)/len(samples):.1f}%")
    print(f"Peak bus load:    {max(samples):.1f}%")
```

### CAN Error Frame Injection
```python
def inject_can_error(channel="CAN1", frame_id=0x100):
    """Inject a CAN error frame (dominant bit stuffing violation)."""
    # DS1552 supports hardware error injection
    controldesk.set(f"DS1552.{channel}.ErrorInjection.FrameID", frame_id)
    controldesk.set(f"DS1552.{channel}.ErrorInjection.ErrorType", 1)  # Bit error
    controldesk.set(f"DS1552.{channel}.ErrorInjection.Enable", 1)
    time.sleep(0.01)
    controldesk.set(f"DS1552.{channel}.ErrorInjection.Enable", 0)

    # Check ECU response
    error_counter = controldesk.get("ECU.CAN_ErrorCounter")
    print(f"ECU CAN error counter after injection: {error_counter}")
```

---

## 3. LIN Bus on dSPACE

LIN (Local Interconnect Network) is a cheap, single-wire bus for simple actuators and sensors:

```
LIN Frame Structure:
────────────────────────────────────────────────────────
Break │ Sync │ PID │ Data (1–8 bytes) │ Checksum
 14+ │  0x55 │  1b │   variable       │   1 byte
──────────────────────────────────────────────────────── 
  
LIN Master/Slave:
  Master sends schedule table → slaves respond in their slot
  HIL typically = LIN master (sends break + schedule)
  ECU (SUT) = LIN slave on some buses, master on others
```

### LIN Master Simulation (ConfigurationDesk)
```
LIN Channel Configuration:
  Board: DS1552 (has LIN channels)
  Baud rate: 19200 bit/s (standard LIN)
  Import LDF file: SunSensor.ldf

LDF File defines:
  Master task: 10 ms schedule
  Frame: SunSensor_Status (0x10, 4 bytes)
    Signal: Sun_Intensity    (bits 0–9,  0–1000 lux)
    Signal: Sun_Azimuth_deg  (bits 10–18, 0–359°)

ConfigurationDesk auto-generates:
  LIN Tx (HIL sends): SunSensor_Status frame
  Mapped to: Simulink/Sun model outputs
```

---

## 4. Automotive Ethernet on dSPACE (DS4330)

### 100BASE-T1 Physical Layer
```
100BASE-T1 (OPEN Alliance BroadR-Reach):
  Cable: Single unshielded twisted pair
  Speed: 100 Mbit/s full-duplex
  Distance: up to 15 m
  Topology: Point-to-point (star via switch)
  Standard: IEEE 802.3bw

vs. Standard Ethernet (100BASE-TX):
  Standard uses 2 pairs, car uses 1 pair
  Lower EMI, lighter weight
  Connectors: H-MTD or MATEnet (automotive grade)
```

### DS4330 Ethernet Configuration
```
Channel 1 settings:
  Physical layer: 100BASE-T1
  MAC address: 00:1A:2B:3C:4D:01 (configurable)
  IP address:  192.168.100.10
  VLAN:        Enabled, VID=10 (if needed)
  gPTP:        Enabled (time synchronization)
  Protocol:    SOME/IP or DoIP (via upper layer config)
```

### DoIP Connection on DS4330
```python
# DoIP routing activation via dSPACE Ethernet (100BASE-T1)
import socket
import struct

DOIP_HEADER_FMT = ">BBHI"   # proto_ver, inv_ver, payload_type, length
DOIP_PROTO_VER  = 0x02
ROUTING_ACTIVATION_REQ = 0x0005

def send_routing_activation(sock, source_addr=0x0E00):
    """Send DoIP Routing Activation Request."""
    payload = struct.pack(">HBL", source_addr, 0x00, 0x00000000)
    header  = struct.pack(DOIP_HEADER_FMT,
                          DOIP_PROTO_VER,
                          ~DOIP_PROTO_VER & 0xFF,
                          ROUTING_ACTIVATION_REQ,
                          len(payload))
    sock.send(header + payload)
    resp = sock.recv(256)
    return resp

# Connect to ECU via DS4330 (target IP = ECU's Ethernet IP)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(("192.168.100.20", 13400))  # ECU DoIP port
    resp = send_routing_activation(s)
    print(f"Routing activation response: {resp.hex()}")
```

### SOME/IP Service Discovery
```
SOME/IP-SD flow on DS4330:
──────────────────────────────────────────────────────────────
HIL (Service Consumer)           ECU (Service Provider)
──────────────────────────────────────────────────────────────
  FIND [ServiceID=0x1234]  ─────►
                           ◄─────  OFFER [ServiceID=0x1234,
                                         Port=30491]
  SUBSCRIBE [EventGroup]   ─────►
                           ◄─────  SUBSCRIBE_ACK
                           ◄─────  EVENT notification (periodic)
──────────────────────────────────────────────────────────────
```

---

## 5. Bus Comparison for HIL Test Design

| Scenario | Recommended Bus | Why |
|----------|----------------|-----|
| Speed/RPM to ECU | CAN FD | Standard powertrain bus |
| OTA firmware update | Automotive Ethernet (DoIP) | Large payload needed |
| ADAS object list | CAN FD or Ethernet | Depends on ECU |
| Climate control | LIN | Low-speed, cheap |
| Radar sensor data | CAN FD (object list) or Ethernet (raw) | Bandwidth-dependent |
| DiagnosticSession | CAN (ISO 15765) or Ethernet (DoIP) | ECU-specific |

---

## 6. Message Scheduling

```
CAN message scheduling in restbus:
──────────────────────────────────────────────────────────────
Message         CycleTime   Priority    Notes
──────────────────────────────────────────────────────────────
WheelSpeeds     10 ms       High        ABS/AEB time-critical
EngineStatus    20 ms       Medium      Fuel/power management
BodyStatus      100 ms      Low         Door/seat/window
Diagnostics     On request  Highest     ISO 15765-2 transport
──────────────────────────────────────────────────────────────

Scheduling in ConfigurationDesk (DBC-based):
  Each message has "GenMsgCycleTime" attribute in DBC
  ConfigurationDesk reads this and schedules accordingly
  Manual override: set per-message cycle time in CDX
```

---

## 7. Interview Q&A

**Q1: What is the difference between CAN and CAN FD?**  
CAN FD adds two features to classic CAN: the EDL bit flags extended data length (up to 64 bytes vs 8 bytes), and the BRS bit switches to a faster bit rate for the data phase only. Arbitration still happens at the slower nominal rate (e.g., 500 kbit/s) for bus access, then the data phase runs at up to 8 Mbit/s.

**Q2: What is restbus simulation and how do you configure it on dSPACE?**  
Restbus simulation makes the HIL send all CAN messages that real vehicle ECUs would normally send, so the SUT sees a realistic network. In ConfigurationDesk, you import a DBC file, and it automatically creates Tx PDUs for all messages. You map the signal values from the simulation model (e.g., CarMaker vehicle speed → WheelSpeeds CAN message).

**Q3: What is LIN's master-slave architecture?**  
LIN has exactly one master that owns the schedule table. The master sends a break + sync + PID (protected identifier) to tell slaves which frame slot is active. The addressed slave then transmits its data. The HIL usually acts as LIN master, sending the schedule and simulating slave responses.

**Q4: Why does automotive use 100BASE-T1 instead of standard Ethernet?**  
100BASE-T1 uses a single unshielded twisted pair (vs two pairs for 100BASE-TX), reducing weight, cost, and cable complexity. Automotive connectors (H-MTD, MATEnet) are more vibration-resistant than RJ45. EMI performance is acceptable for automotive EMC requirements.

**Q5: How do you measure CAN bus load in dSPACE?**  
The DS1552 board continuously calculates the percentage of bit times occupied by frames and gaps on each channel. This is exposed as a ControlDesk variable `DS1552.CANx.BusLoad_pct`. Best practice: keep load below 40% for normal operation to allow headroom for retransmissions and priority messages.
