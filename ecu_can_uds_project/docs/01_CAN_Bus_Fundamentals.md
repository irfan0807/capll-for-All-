# CAN Bus Fundamentals for Automotive ECU Development

## 1. What is CAN Bus?

Controller Area Network (CAN) is a robust serial communication protocol developed by Bosch in 1983, standardized under **ISO 11898**. It allows microcontrollers and devices (ECUs) to communicate without a host computer.

```
         ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
         │  Engine ECU │     │    ABS ECU  │     │   BCM ECU   │
         └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
                │                   │                    │
    ────────────┴───────────────────┴────────────────────┴────────
                             CAN Bus (120Ω termination each end)
```

---

## 2. CAN Bus Variants

| Variant       | Speed          | Standard      | Use Case                        |
|---------------|----------------|---------------|---------------------------------|
| CAN 2.0A      | Up to 1 Mbit/s | 11-bit ID     | Classic automotive ECUs         |
| CAN 2.0B      | Up to 1 Mbit/s | 29-bit ID     | Trucks, J1939, extended address |
| CAN FD        | Up to 8 Mbit/s | 11/29-bit ID  | ADAS, high data throughput      |
| CAN XL        | Up to 10 Mbit/s| Extended      | Next-gen automotive Ethernet    |

---

## 3. CAN Frame Structure

### Standard CAN Frame (11-bit ID)

```
┌─────┬────────────┬───┬───┬──────┬───────────────────┬───┬───────────────┐
│ SOF │   ID[10:0] │RTR│IDE│  DLC │     DATA[0..7]    │CRC│  ACK  │  EOF  │
│  1b │    11 bits │1b │1b │ 4 bits│  0–8 bytes        │15b│  2b   │  7b   │
└─────┴────────────┴───┴───┴──────┴───────────────────┴───┴───────────────┘
```

| Field | Description |
|-------|-------------|
| SOF   | Start Of Frame – dominant bit marking frame start |
| ID    | Message identifier – also determines bus priority (lower = higher priority) |
| RTR   | Remote Transmission Request – 0=data frame, 1=remote frame |
| IDE   | Identifier Extension – 0=standard, 1=extended |
| DLC   | Data Length Code – number of data bytes (0–8) |
| DATA  | Payload – up to 8 bytes |
| CRC   | 15-bit Cyclic Redundancy Check |
| ACK   | Acknowledgement slot |
| EOF   | End Of Frame – 7 recessive bits |

---

## 4. CAN Bus Arbitration (CSMA/CA)

CAN uses **non-destructive bitwise arbitration**:

```
Node A sends: 0 1 1 0 1 0 1 ...
Node B sends: 0 1 0 ...         ← loses arbitration at bit 3 (recessive vs dominant)
Bus state:    0 1 0 ...         ← Node B backs off, Node A wins and continues
```

**Rule:** Dominant bit (0) always wins over recessive bit (1).
Lower CAN ID = higher priority.

---

## 5. CAN Bus Signals (Physical Layer)

| State      | CAN_H (V) | CAN_L (V) | Differential |
|------------|-----------|-----------|--------------|
| Recessive  | 2.5       | 2.5       | ~0V          |
| Dominant   | 3.5       | 1.5       | ~2V          |

**Termination resistors**: 120Ω at each end of the bus.

---

## 6. CAN Error Handling

### Error Types

| Error Type      | Cause |
|-----------------|-------|
| Bit Error       | Transmitted bit ≠ monitored bit |
| Stuff Error     | 6+ consecutive bits of same polarity |
| CRC Error       | CRC mismatch between transmitter and receiver |
| Form Error      | Fixed-form field violation |
| Acknowledgment Error | No ACK during ACK slot |

### Error States

```
                  ┌──────────────────────────────┐
                  ▼                              │
           [Error Active]  ──(>127 errors)──► [Error Passive]
                                                  │
                                         (>255 errors)
                                                  │
                                                  ▼
                                           [Bus Off]
```

- **Error Active**: Node can send Error Flags (active error flag = 6 dominant bits)
- **Error Passive**: Node sends passive error flags (6 recessive bits)
- **Bus Off**: Node disconnects; recovers after 128 × 11 recessive bits

---

## 7. CAN Message Database (DBC File)

A `.dbc` file defines messages and signals:

```dbc
VERSION ""

NS_ :

BS_:

BU_: EngineECU ABS_ECU BCM

BO_ 256 EngineStatus: 8 EngineECU
 SG_ EngineRPM : 0|16@1+ (0.25,0) [0|16383.75] "RPM" ABS_ECU,BCM
 SG_ CoolantTemp : 16|8@1+ (1,-40) [-40|215] "degC" BCM
 SG_ EngineLoad : 24|8@1+ (0.392157,0) [0|100] "%" ABS_ECU
 SG_ ThrottlePos : 32|8@1+ (0.392157,0) [0|100] "%" BCM

BO_ 512 WheelSpeeds: 8 ABS_ECU
 SG_ SpeedFL : 0|16@1+ (0.01,0) [0|655.35] "km/h" EngineECU,BCM
 SG_ SpeedFR : 16|16@1+ (0.01,0) [0|655.35] "km/h" EngineECU,BCM
 SG_ SpeedRL : 32|16@1+ (0.01,0) [0|655.35] "km/h" EngineECU,BCM
 SG_ SpeedRR : 48|16@1+ (0.01,0) [0|655.35] "km/h" EngineECU,BCM

BO_ 768 BrakeControl: 4 BCM
 SG_ BrakePressure : 0|16@1+ (0.1,0) [0|6553.5] "bar" ABS_ECU
 SG_ ABSActive : 16|1@1+ (1,0) [0|1] "" ABS_ECU
 SG_ ESPActive : 17|1@1+ (1,0) [0|1] "" ABS_ECU
```

### Signal Encoding Formula

**Physical Value** = Raw Value × Factor + Offset

Example: `EngineRPM` raw=5000 → Physical = 5000 × 0.25 + 0 = **1250 RPM**

---

## 8. CAN in Automotive Systems – Real Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    Vehicle CAN Network Topology                    │
│                                                                    │
│   Powertrain CAN (500 kbps)          Comfort CAN (125 kbps)       │
│   ┌──────────┐  ┌──────────┐         ┌──────────┐  ┌──────────┐  │
│   │Engine ECU│  │Trans ECU │         │ Door ECU │  │ Seat ECU │  │
│   └────┬─────┘  └────┬─────┘         └────┬─────┘  └────┬─────┘  │
│        └──────┬───────┘                    └──────┬───────┘       │
│               │                                   │               │
│          ┌────┴──────────────────────────────┐    │               │
│          │        Central Gateway ECU         ├────┘               │
│          └────┬──────────────────────────────┘                    │
│               │                                                    │
│   Chassis CAN (500 kbps)            Diagnostic CAN (500 kbps)     │
│   ┌──────────┐  ┌──────────┐              ┌─────────┐             │
│   │  ABS ECU │  │  ESP ECU │              │  OBD-II │             │
│   └──────────┘  └──────────┘              └─────────┘             │
└────────────────────────────────────────────────────────────────────┘
```

---

## 9. CAN Bus Troubleshooting – Common Issues & Root Causes

| Symptom | Likely Cause | Tool / Fix |
|---------|-------------|------------|
| No communication | Missing termination (120Ω) | Oscilloscope, check termination |
| Intermittent loss | Loose connector, EMI | Wiring harness inspection |
| High error rate | Speed mismatch (baud rate) | CANalyzer, match baud rates |
| Bus off state | Faulty node transmitting corrupted frames | Disconnect nodes one by one |
| Short recessive bus | Short to GND on CAN_L | Measure differential voltage |
| Dominant stuck | Failed transceiver | Replace CAN transceiver IC |

---

## 10. Hands-On: Reading CAN Frames in C++

```cpp
#include <linux/can.h>
#include <linux/can/raw.h>
#include <sys/socket.h>
#include <net/if.h>
#include <cstring>
#include <iostream>
#include <iomanip>

int main() {
    int sock = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    
    struct ifreq ifr;
    strcpy(ifr.ifr_name, "vcan0");
    ioctl(sock, SIOCGIFINDEX, &ifr);
    
    struct sockaddr_can addr{};
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    bind(sock, (struct sockaddr*)&addr, sizeof(addr));
    
    struct can_frame frame;
    while (true) {
        int nbytes = read(sock, &frame, sizeof(frame));
        if (nbytes > 0) {
            std::cout << "ID: 0x" << std::hex << std::setw(3) 
                      << std::setfill('0') << frame.can_id
                      << " DLC: " << std::dec << (int)frame.can_dlc
                      << " Data: ";
            for (int i = 0; i < frame.can_dlc; i++)
                std::cout << std::hex << std::setw(2) 
                          << std::setfill('0') << (int)frame.data[i] << " ";
            std::cout << std::endl;
        }
    }
    return 0;
}
```

---

## 11. Key Interview Questions

1. **What is the maximum number of nodes on a CAN bus?**  
   Theoretically 2032 (11-bit ID), practically limited by bus load and transceivers (~110 nodes).

2. **Why is lower CAN ID higher priority?**  
   During arbitration, a dominant (0) bit overrides recessive (1). Lower IDs have more leading zeros, so they win arbitration.

3. **What happens when a node enters Bus Off?**  
   It stops transmitting and only recovers after 128 × 11 recessive bits (hardware reset sequence).

4. **Difference between CAN and CAN FD?**  
   CAN FD supports payload up to 64 bytes (vs 8) and variable bit rate (data phase up to 8Mbit/s vs fixed 1Mbit/s).

5. **How does CAN handle simultaneous transmissions?**  
   Via CSMA/CA – bitwise arbitration, non-destructive, lower ID wins without collision or delay.
