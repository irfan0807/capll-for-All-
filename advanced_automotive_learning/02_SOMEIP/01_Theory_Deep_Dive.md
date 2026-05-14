# SOME/IP — DEEP DIVE
## Module 2 of 7 | advanced_automotive_learning

---

## 1. WHAT IS SOME/IP?

**SOME/IP** = Scalable service-Oriented MiddlewarE over IP.

It is the **AUTOSAR middleware protocol** that enables ECUs to communicate as service providers and consumers over IP (TCP/UDP). Think of it as a lightweight RPC (Remote Procedure Call) system designed for real-time embedded systems.

```
WITHOUT SOME/IP:            WITH SOME/IP:
ECU-A hard-wires to ECU-B   ECU-A offers a "service"
Direct CAN message ID       ECU-B subscribes when needed
Manual subscription mgmt    Automatic discovery (SOME/IP-SD)
No service versioning       Versioned interfaces
No error handling           Return codes per call
```

### SOME/IP vs REST API Analogy

| SOME/IP Concept | Web API Equivalent |
|----------------|-------------------|
| Service | REST API endpoint |
| Method | HTTP GET/POST |
| Event | Server-Sent Event / WebSocket |
| Service ID | Domain / port |
| Client ID | Session token |
| SOME/IP-SD | Service Registry (like Consul/Zookeeper) |

---

## 2. SOME/IP HEADER — BYTE-BY-BYTE

```
SOME/IP MESSAGE FORMAT (minimum 16 bytes):
 
  Byte:  0    1    2    3    4    5    6    7
       ┌────┬────┬────┬────┬────┬────┬────┬────┐
       │      Service ID   │     Method ID      │
       │    (2 bytes)      │    (2 bytes)       │
       └────┴────┴────┴────┴────┴────┴────┴────┘
  Byte:  8    9   10   11   12   13   14   15
       ┌────┬────┬────┬────┬────┬────┬────┬────┐
       │           Length (4 bytes)             │
       │  (counts from byte 8 to end of msg)    │
       └────┴────┴────┴────┴────┴────┴────┴────┘
  Byte: 16   17   18   19   20   21   22   23
       ┌────┬────┬────┬────┬────┬────┬────┬────┐
       │  Client ID  │ Session ID │ Proto│IFace│
       │  (2 bytes)  │ (2 bytes)  │ Ver  │ Ver │
       └────┴────┴────┴────┴────┴────┴────┴────┘
  Byte: 24   25
       ┌────┬────┐
       │MsgT│RCod│   ...Payload...
       └────┴────┘

FIELD MEANINGS:
  Service ID:   Identifies the service (e.g., 0x1234 = SpeedService)
  Method ID:    Identifies the method/event within the service
                0x0001–0x7FFF = Methods (request/response)
                0x8000–0x8FFF = Events (notification)
  Length:       Bytes from byte 8 to end (excludes first 8 bytes)
  Client ID:    Identifies the calling client (tester/ECU)
  Session ID:   Incremented per request (for matching responses)
  Proto Ver:    Always 0x01 (SOME/IP protocol version 1)
  IFace Ver:    Service interface version (from ARXML)
  Msg Type:     0x00=REQUEST, 0x01=RESPONSE, 0x02=ERROR,
                0x40=REQ_NO_RETURN, 0x80=NOTIFICATION
  Return Code:  0x00=E_OK, 0x01=E_NOT_OK, 0x0D=Unknown Service,
                0x0E=Unknown Method
```

### Worked Example: Decoding a SOME/IP Frame

```
Raw bytes (hex):
  12 34 80 05 00 00 00 0C 01 00 00 01 01 01 80 00 01 02 03 04 05 06 07 08

Decode:
  Service ID:  0x1234  → SpeedService
  Method ID:   0x8005  → SpeedEvent (0x8000+ = event)
  Length:      0x0000000C = 12 → payload = 12 - 8 = 4 bytes (header after byte 8)
               Wait: Length counts from byte 8, so payload is after byte 24
               Payload = 0x01020304 05060708 (actual remaining bytes)
  Client ID:   0x0100
  Session ID:  0x0001
  Proto Ver:   0x01
  IFace Ver:   0x01
  Msg Type:    0x80  → NOTIFICATION (event)
  Return Code: 0x00  → E_OK
  Payload:     05 06 07 08 → 4 bytes of vehicle speed data
```

---

## 3. SOME/IP COMMUNICATION PATTERNS

### 3.1 Request / Response (Method Call)

```
CLIENT                              SERVER
  │                                   │
  │─── REQUEST (MsgType=0x00) ───────►│
  │    Service=0x1234, Method=0x0001  │
  │    Client=0x0100, Session=0x0001  │
  │    Payload: [input parameters]    │
  │                                   │  Process
  │                                   │  request
  │◄── RESPONSE (MsgType=0x01) ───────│
  │    Service=0x1234, Method=0x0001  │
  │    Client=0x0100, Session=0x0001  │  SAME session ID!
  │    Payload: [return values]       │
  │    ReturnCode=0x00 (E_OK)         │

Timeout: If no response within T_Request (configured in ARXML),
         SOME/IP client returns E_TIMEOUT to SWC
```

### 3.2 Fire and Forget (Request, No Return)

```
CLIENT                              SERVER
  │                                   │
  │─── REQUEST_NO_RETURN (0x40) ─────►│
  │    Payload: [parameters]          │
  │    (No response expected)         │
  │                                   │

Use case: "Set headlight ON" — no need to wait for confirmation.
MsgType: 0x40 instead of 0x00
```

### 3.3 Events / Notifications (Pub-Sub)

```
PUBLISHER (Server)          SUBSCRIBER (Client)
  │                               │
  │   (After subscription)        │
  │── NOTIFICATION (0x80) ───────►│  Cyclic or on-change
  │── NOTIFICATION (0x80) ───────►│
  │── NOTIFICATION (0x80) ───────►│  Every 20ms (cyclic)
  │── NOTIFICATION (0x80) ───────►│
  │                               │

Method ID range: 0x8000–0x8FFF
Key difference from CAN: subscriber must explicitly subscribe via SD
                         (not just listen on message ID)
```

---

## 4. SOME/IP-SD — SERVICE DISCOVERY

SOME/IP-SD is how services **announce** themselves and clients **subscribe** to events.

**Default multicast address: `224.224.224.245:30490` (UDP)**

### 4.1 Full Subscribe Flow

```
SERVICE PROVIDER               SERVICE CONSUMER
(e.g., RadarECU)              (e.g., ADAS Controller)
        │                              │
        │  Power on...                 │
        │──OfferService (SD) ─────────►│  "I provide SpeedService v1"
        │  Service ID = 0x1234         │
        │  Instance ID = 0x0001        │
        │  TTL = 0xFFFFFF (forever)    │
        │                              │
        │◄─FindService (SD)────────────│  "Is SpeedService available?"
        │                              │  (Optional — if provider missed OfferService)
        │──OfferService ──────────────►│  Provider responds again
        │                              │
        │◄─SubscribeEventgroup ────────│  "Subscribe me to SpeedEvent"
        │  Eventgroup ID = 0x0001      │
        │  TTL = 5 (resubscribe in 5s) │
        │                              │
        │── SubscribeAck ─────────────►│  "Subscription confirmed"
        │                              │
        │── NOTIFICATION ─────────────►│  Events now flowing
        │── NOTIFICATION ─────────────►│  Every cycle (20ms)
        │── NOTIFICATION ─────────────►│
```

### 4.2 SD Entry Format

```
SOME/IP-SD ENTRY (4 bytes type + 12 bytes body = 16 bytes per entry):
  Type:         0x00 = FindService
                0x01 = OfferService
                0x06 = SubscribeEventgroup
                0x07 = SubscribeEventgroupAck
  Index1/2:     Points to optional array (endpoints)
  Service ID:   2 bytes
  Instance ID:  2 bytes
  Major Version: 1 byte (must match provider)
  TTL:          3 bytes (0xFFFFFF = until stop offer)
  Minor Version: 4 bytes (OfferService only)
  Eventgroup ID: 2 bytes (SubscribeEventgroup only)
```

### 4.3 TTL and Resubscription

```
TTL IN SOME/IP-SD:
  OfferService TTL:       How long offer is valid (usually 0xFFFFFF = infinite)
  Subscribe TTL:          How long subscription is valid before renewal
  
  If Subscribe TTL = 5 seconds:
    t=0:  Subscribe(TTL=5)
    t=4:  Subscribe(TTL=5)  ← Client resubscribes before expiry
    t=8:  Subscribe(TTL=5)  ← Continuous resubscription
    
  If resubscription missed (e.g., ECU reboot):
    Provider stops sending events to that subscriber
    Consumer must detect missed events and resubscribe
    
COMMON BUG: Consumer ECU reboots, loses subscription.
            Provider keeps sending to stale subscriber list? No.
            Provider must detect TCP disconnect or TTL expiry.
```

---

## 5. SOME/IP SERIALIZATION

SOME/IP carries **structured data** as a byte array. Serialization is how the structure is packed into bytes.

```c
/* C structure to serialize */
typedef struct {
    uint32_t vehicle_speed_mm_s;   /* 4 bytes, big-endian */
    uint8_t  speed_validity;       /* 1 byte */
    uint16_t wheel_speed_front_L;  /* 2 bytes, big-endian */
    uint16_t wheel_speed_front_R;  /* 2 bytes, big-endian */
} SpeedData_t;

/* SOME/IP serialized bytes (big-endian, no padding):
   [0x00][0x01][0x86][0xA0]  = 100000 mm/s = 100 m/s = 360 km/h
   [0x01]                    = valid
   [0x00][0xC8]              = 200 (0.1 km/h units → 20 km/h)
   [0x00][0xC9]              = 201 (20.1 km/h) */

/* AUTOSAR SOME/IP Transformer (SomeIpXf) does this automatically */
/* Manual serialization in Python for testing: */
import struct
data = struct.pack(">IBhh", 100000, 1, 200, 201)
# > = big-endian, I = uint32, B = uint8, h = int16 (use H for uint16)
```

**Key serialization rules:**
- Default byte order: **Big-endian** (can be configured)
- No padding/alignment by default (unlike C structs)
- Arrays: prepend 4-byte length field
- Strings: prepend 4-byte length + UTF-8 bytes + null terminator
- Optionals (TLV): SOME/IP TP extension

---

## 6. AUTOSAR SOME/IP MODULES

```
AUTOSAR STACK FOR SOME/IP:

SWC (application):
  Rte_Write_SpeedPort_SpeedValue(speed_data)
  Rte_Read_AccelerationPort_AccelValue(&accel_data)
         │
RTE (generated):
  Routes writes/reads to/from Com or SomeIpXf
         │
SomeIpXf (SOME/IP Transformer):
  Serializes struct → bytes (TX)
  Deserializes bytes → struct (RX)
  Applies byte order, length prefixes
         │
SomeIpSd (Service Discovery):
  Manages OfferService, FindService, Subscribe, Unsubscribe
  Handles TTL timers, resubscription
         │
SoAd (Socket Adapter):
  Opens/closes UDP/TCP sockets
  Routes PDUs to correct sockets
  Manages socket connection states
         │
TcpIp:   IPv4/UDP/TCP implementation
EthIf:   VLAN tagging, frame routing
Eth:     DMA descriptors, MAC
```

---

## 7. SOME/IP TEST CASES

### TC-SIIP-001: Service Discovery — OfferService Received
```
Objective: Verify SOME/IP server sends OfferService on startup
Steps:
  1. Power on server ECU
  2. Capture on SOME/IP-SD multicast (224.224.224.245:30490)
  3. Filter: someip-sd && someip-sd.type == 1
Expected: OfferService with correct Service ID and Instance ID
         received within 500ms of ECU power-on
Wireshark filter: someip-sd
```

### TC-SIIP-002: Event Subscription and Reception
```
Objective: Verify client receives SOME/IP events after subscription
Steps:
  1. Power on server ECU (offers SpeedService)
  2. Power on client ECU
  3. Client subscribes to SpeedEvent (eventgroup 0x0001)
  4. Monitor event reception for 5 seconds
Expected: Events received at configured cycle time (±10%)
          Method ID = 0x8001 (event range)
          Return Code = 0x00 (E_OK)
```

### TC-SIIP-003: Request/Response Timing
```
Objective: Verify method call response received within 100ms
Steps:
  1. Client sends REQUEST (MsgType=0x00) to GetVehicleInfo method
  2. Start timer at REQUEST timestamp
  3. Capture RESPONSE (MsgType=0x01) with same Session ID
Expected: Response received within 100ms
          Session ID matches
          Return Code = 0x00
Wireshark filter: someip.sessionid == 0x0001
```

### TC-SIIP-004: Session ID Incrementing
```
Objective: Verify Session ID increments per request (no replay)
Steps:
  1. Send 10 consecutive requests to same method
  2. Capture all requests
  3. Verify Session IDs: 0x0001, 0x0002, ..., 0x000A
Expected: Strictly monotonic Session ID increment
SECURITY NOTE: Non-incrementing session IDs risk replay attacks
```

### TC-SIIP-005: Service Not Found Behavior
```
Objective: Verify client behavior when server is unavailable
Steps:
  1. Keep server ECU powered OFF
  2. Client attempts to FindService and subscribe
  3. Wait for FindService retry timeout (per ARXML config)
Expected: Client reports E_TIMEOUT or E_UNKNOWN_SERVICE to SWC
          Client retries FindService at configured interval
          DEM error logged: SOMEIP_SERVICE_UNAVAILABLE
```

---

## 8. COMMON BUGS

```
BUG 1: Service ID / Method ID mismatch
  Server ARXML: Service ID = 0x1234, Method ID = 0x0001
  Client ARXML: Service ID = 0x1234, Method ID = 0x0002
  Symptom: Client sends REQUEST, server returns NRC 0x0E (Unknown Method)
  Fix: Align Method IDs in ARXML on both server and client

BUG 2: Interface version mismatch
  Server offers InterfaceVersion = 2
  Client expects InterfaceVersion = 1
  Symptom: Subscription rejected (SubscribeEventgroupNAck sent)
  Fix: Align Major version in ARXML. Minor version differences are OK.

BUG 3: Wrong data type serialization
  Server serializes speed as float32 (4 bytes)
  Client deserializes speed as uint32 (4 bytes)
  Symptom: Client gets garbage speed values (NaN interpreted as 4 billion)
  Fix: Strict type checking in ARXML SomeIpXf configuration

BUG 4: SD multicast not reaching client
  Symptom: FindService never gets OfferService response
  Root cause: VLAN firewall blocking multicast 224.224.224.245
  Fix: Add multicast pass-through rule to switch ACL

BUG 5: Event storm after reconnect
  Symptom: After client ECU reboot, events stop arriving permanently
  Root cause: Server's internal subscription table still marks client
              as subscribed (stale entry), so no new Ack sent; client
              never re-subscribes because it got no Ack
  Fix: Implement proper TCP connection-loss detection; clear stale entries
```

---

## 9. INTERVIEW Q&A

**Q1: What is the difference between SOME/IP Request, Fire&Forget, and Notification?**
> Request (0x00): client sends, expects Response (0x01) with same Session ID. Fire&Forget (0x40): client sends, no response expected — used for commands. Notification (0x80): server sends unsolicited events to subscribed clients. Key difference: Request is synchronous-like (wait for reply), Notification is asynchronous pub-sub.

**Q2: How does SOME/IP-SD work? Walk me through a subscription.**
> 1. Server powers on and sends OfferService to multicast 224.224.224.245:30490 with Service ID, Instance ID, TTL. 2. Client sees OfferService, sends SubscribeEventgroup back to server unicast, with Eventgroup ID and TTL. 3. Server sends SubscribeAck back to client. 4. Server starts sending NOTIFICATION events to client's unicast address. Client resubscribes before TTL expires.

**Q3: How is SOME/IP serialization done?**
> SomeIpXf (SOME/IP Transformer) in AUTOSAR serializes SWC data types to byte arrays. Default: Big-endian byte order, no padding (unlike C structs which may have alignment padding). Arrays get a 4-byte length prefix. Strings are length-prefixed + UTF-8 + null terminator. The serialization format is defined in the ARXML data type mappings.

**Q4: What is SOME/IP Method ID range for events?**
> 0x8000–0x8FFF. Events have method IDs in this range. Methods (request/response) use 0x0001–0x7FFF. This makes it easy to distinguish: if Method ID high bit is set, it's an event/notification.

**Q5: What happens if a SOME/IP server and client have different interface versions?**
> If Major versions differ, the subscription is rejected with SubscribeEventgroupNAck. The SOME/IP spec treats major version differences as incompatible interfaces (breaking change). Minor version differences are allowed — minor = backward-compatible additions. Always align Major version between server (in OfferService) and client (in ARXML requirement).

---

*Next: [02_STAR_Answers.md](02_STAR_Answers.md)*
