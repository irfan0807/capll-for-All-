# SECTION 6 — VECTOR TOOLS: CANoe, CANalyzer, vTESTstudio & CAPL
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## 6.1 CANoe OVERVIEW

### What Is CANoe?

CANoe (Controller Area Network open environment) by Vector Informatik is the industry-standard tool for automotive ECU testing, network simulation, and diagnostics. It supports CAN, CAN FD, LIN, FlexRay, Ethernet, MOST, and more.

### CANoe Architecture

```
CANoe INTERNAL ARCHITECTURE:
┌────────────────────────────────────────────────────────────────┐
│  CANoe Measurement & Simulation Environment                    │
├────────────────────────────────────────────────────────────────┤
│  PANELS / HMI              │  TEST MODULES                     │
│  • Signal display panels   │  • vTESTstudio test cases         │
│  • Gauge, graph, LED       │  • CAPL test nodes               │
│  • Interactive controls    │  • XML test cases                 │
├────────────────────────────────────────────────────────────────┤
│  SIMULATION NODES           │  ANALYSIS WINDOWS                │
│  • CAPL simulation nodes   │  • Trace window (all frames)     │
│  • FunctionBus simulation  │  • Statistics window             │
│  • ECU simulation (.vcdl)  │  • Data window                   │
│  • REST API nodes          │  • System Console (log)          │
├────────────────────────────────────────────────────────────────┤
│  DATABASE LAYER                                                │
│  • .DBC files (CAN signal definitions)                        │
│  • .ARXML files (AUTOSAR SOME/IP definitions)                 │
│  • .LDF files (LIN definitions)                               │
│  • .FIB files (FlexRay definitions)                           │
├────────────────────────────────────────────────────────────────┤
│  HARDWARE INTERFACE LAYER                                      │
│  • VN1640A (CAN FD interface)                                 │
│  • VN5640 (Ethernet + CAN interface)                          │
│  • VN8900 (multi-bus: Eth + CAN + LIN + FR)                  │
│  • VH6501 (CAN disturbance — fault injection)                 │
└────────────────────────────────────────────────────────────────┘
```

### Key CANoe Windows

```
1. MEASUREMENT SETUP WINDOW:
   • Shows all nodes (CAPL, simulation, test)
   • Connects to databases (.dbc, .arxml)
   • Configure network channels

2. TRACE WINDOW:
   • Real-time frame display (all protocols)
   • Timestamp, direction, ID, data
   • Filter and search capabilities
   • Export to .asc, .blf, .pcap format

3. SIGNAL GRAPH WINDOW:
   • Plots signal values over time
   • Compare multiple signals
   • Measure slope, frequency, amplitude

4. ETHERNET STATISTICS:
   • Frame rate, error count per port
   • PHY link status, speed, duplex
   • TSN gate statistics

5. DIAGNOSTIC CONSOLE:
   • UDS request builder
   • DTC reader/clearer
   • ECU identifier reader

6. SYMBOL EXPLORER:
   • Browse all signals from loaded databases
   • Drag and drop to panels, test nodes
```

---

## 6.2 CAPL — COMPLETE PROGRAMMING GUIDE

### CAPL Language Fundamentals

CAPL (Communication Access Programming Language) is an event-driven language syntactically similar to C, used exclusively in Vector tools (CANoe, CANalyzer).

### CAPL Program Structure

```c
/*============================================================
  FILE: ADAS_Ethernet_Test.can
  DESCRIPTION: ADAS ECU Ethernet Testing
  AUTHOR: Test Engineer
  TOOL: CANoe 15.x
  ============================================================*/

/* Variables — declared outside event handlers */
variables {
    /* Test control */
    int    testResult = 0;
    int    eventCount = 0;
    float  lastEventTime = 0.0;
    float  eventInterval = 0.0;
    
    /* Timers */
    msTimer  t_WatchdogTimer;
    msTimer  t_WaitForResponse;
    
    /* Ethernet frame buffer */
    byte   ethernetPayload[1518];
    long   payloadLength = 0;
    
    /* SOME/IP test data */
    word   expectedServiceId = 0x0001;
    word   expectedMethodId  = 0x8001;
    
    /* DTC tracking */
    long dtcCode = 0;
    
    /* Configuration */
    const float SOME_IP_PERIOD_MS      = 20.0;
    const float SOME_IP_TOLERANCE_MS   = 2.0;
    const int   REQUIRED_EVENT_COUNT   = 100;
}
```

### CAPL Event Handlers

```c
/*============================================================
  EVENT: on start — runs when CANoe measurement starts
  ============================================================*/
on start {
    write("=== ADAS Ethernet Test Suite Starting ===");
    
    /* Initialize test */
    testResult   = 0;
    eventCount   = 0;
    lastEventTime = 0.0;
    
    /* Start watchdog timer — test must complete in 30s */
    setTimer(t_WatchdogTimer, 30000);
    
    write("Waiting for SOME/IP OfferService from ADAS ECU...");
}

/*============================================================
  EVENT: on stopMeasurement — runs when CANoe stops
  ============================================================*/
on stopMeasurement {
    write("=== Test Complete ===");
    write("Events received: %d", eventCount);
    write("Result: %s", (testResult == 1) ? "PASS" : "FAIL");
}

/*============================================================
  EVENT: on timer — fires when timer expires
  ============================================================*/
on timer t_WatchdogTimer {
    write("[ERROR] Watchdog expired — test not completed in 30s!");
    testStepFail("Watchdog timeout — insufficient events received");
    stopMeasurement();
}

on timer t_WaitForResponse {
    write("[FAIL] No SOME/IP response within timeout");
    testStepFail("Response timeout");
}
```

### CAPL Ethernet Event Handler

```c
/*============================================================
  EVENT: on ethernetPacket — fires for every Ethernet frame
  ============================================================*/
on ethernetPacket {
    long   serviceId;
    long   methodId;
    long   msgType;
    float  currentTime;
    float  delta;
    
    /* Check if this is a SOME/IP frame (UDP port 30490) */
    if (this.UDP.DestPort != 30490)
        return;
    
    /* Parse SOME/IP header (first 8 bytes of UDP payload) */
    serviceId = (long)(this.byte(8) << 8) | this.byte(9);   /* offset 8-9 */
    methodId  = (long)(this.byte(10) << 8) | this.byte(11); /* offset 10-11 */
    msgType   = this.byte(18);                               /* offset 18 */
    
    /* Check if this is our expected RADAR event */
    if (serviceId != expectedServiceId) return;
    if (methodId  != expectedMethodId)  return;
    if (msgType   != 0x02)             return; /* 0x02 = NOTIFICATION */
    
    /* Measure inter-event interval */
    currentTime = timeNow() / 100000.0; /* Convert to ms */
    
    if (lastEventTime > 0.0) {
        delta = currentTime - lastEventTime;
        
        /* Validate period */
        if (delta < (SOME_IP_PERIOD_MS - SOME_IP_TOLERANCE_MS) ||
            delta > (SOME_IP_PERIOD_MS + SOME_IP_TOLERANCE_MS)) {
            write("[WARN] Event period out of range: %.2f ms (expected: %.1f ± %.1f ms)",
                  delta, SOME_IP_PERIOD_MS, SOME_IP_TOLERANCE_MS);
        }
    }
    
    lastEventTime = currentTime;
    eventCount++;
    
    /* Check if we have enough events */
    if (eventCount >= REQUIRED_EVENT_COUNT) {
        cancelTimer(t_WatchdogTimer);
        testResult = 1;
        testStepPass("SOME/IP event rate validated: 100 events at correct period");
        write("All %d events received successfully", REQUIRED_EVENT_COUNT);
    }
}
```

### CAPL — Sending Ethernet Frames

```c
/*============================================================
  FUNCTION: SendDoIPRequest — sends a UDS request via DoIP
  ============================================================*/
void SendDoIPRequest(byte udsService, long logicalAddr)
{
    /* DoIP header: 8 bytes */
    /* Payload type 0x8001 = DiagnosticMessage */
    
    ethernetPayload[0] = 0x02;  /* Protocol version */
    ethernetPayload[1] = 0xFD;  /* Inverse protocol version */
    ethernetPayload[2] = 0x80;  /* Payload type HIGH: DiagnosticMessage */
    ethernetPayload[3] = 0x01;  /* Payload type LOW */
    
    /* Length (4 bytes) = 2 (source addr) + 2 (target addr) + UDS length */
    long totalLength = 4 + 1; /* 4 addr bytes + 1 UDS service byte */
    ethernetPayload[4] = (byte)((totalLength >> 24) & 0xFF);
    ethernetPayload[5] = (byte)((totalLength >> 16) & 0xFF);
    ethernetPayload[6] = (byte)((totalLength >> 8) & 0xFF);
    ethernetPayload[7] = (byte)(totalLength & 0xFF);
    
    /* Source address (tester = 0xE000) */
    ethernetPayload[8]  = 0xE0;
    ethernetPayload[9]  = 0x00;
    
    /* Target address (ADAS ECU = 0x0010) */
    ethernetPayload[10] = (byte)((logicalAddr >> 8) & 0xFF);
    ethernetPayload[11] = (byte)(logicalAddr & 0xFF);
    
    /* UDS service */
    ethernetPayload[12] = udsService;
    
    /* Send over TCP socket (DoIP uses TCP port 13400) */
    /* In CANoe, use SoAd/socket API or diagnostic window */
    
    payloadLength = 13;
    write("[TX] DoIP DiagnosticMessage to 0x%04X: SID=0x%02X", logicalAddr, udsService);
}
```

---

## 6.3 CAPL — ADVANCED PATTERNS

### CAPL Timer-Based State Machine

```c
variables {
    /* Test state machine */
    int testState = 0;
    const int STATE_IDLE            = 0;
    const int STATE_WAIT_LINK       = 1;
    const int STATE_SEND_REQUEST    = 2;
    const int STATE_WAIT_RESPONSE   = 3;
    const int STATE_VALIDATE        = 4;
    const int STATE_DONE            = 5;
    
    msTimer t_StateTimer;
    
    /* Response storage */
    byte responseBuffer[256];
    int  responseLen = 0;
    int  responseReceived = 0;
}

on start {
    testState = STATE_WAIT_LINK;
    setTimer(t_StateTimer, 500);  /* Poll for link every 500ms */
}

on timer t_StateTimer {
    switch (testState) {
        
        case STATE_WAIT_LINK:
            /* Check if Ethernet link is up */
            if (getEthernetLinkState("ETH1") == 1) {
                write("[OK] Ethernet link is UP");
                testState = STATE_SEND_REQUEST;
                setTimer(t_StateTimer, 100);  /* Wait 100ms before sending */
            } else {
                write("[WAIT] Ethernet link not yet up, retrying...");
                setTimer(t_StateTimer, 500);
            }
            break;
            
        case STATE_SEND_REQUEST:
            write("[TX] Sending SOME/IP FindService...");
            /* Trigger SOME/IP SD FindService (via CANoe SD node) */
            callSomeIpSdFindService(0x0001, 0x01); /* Service 0x0001, version 1 */
            testState = STATE_WAIT_RESPONSE;
            setTimer(t_StateTimer, 2000);  /* Wait 2s for OfferService */
            break;
            
        case STATE_WAIT_RESPONSE:
            if (responseReceived) {
                testState = STATE_VALIDATE;
                setTimer(t_StateTimer, 10);
            } else {
                write("[FAIL] No OfferService received in 2s");
                testStepFail("SOME/IP Service Discovery failed");
                testState = STATE_DONE;
            }
            break;
            
        case STATE_VALIDATE:
            /* Validate the response */
            if (validateOfferService()) {
                testStepPass("SOME/IP Service Discovery validated");
                testResult = 1;
            } else {
                testStepFail("OfferService content invalid");
            }
            testState = STATE_DONE;
            break;
    }
}
```

### CAPL — CAN Signal Monitoring

```c
/*============================================================
  Monitor CAN signal: FCW_Active (Forward Collision Warning)
  Message: 0x200, Byte 0, Bit 7
  ============================================================*/
on message 0x200 {
    byte fcwActive;
    float vehicleSpeed;
    
    /* Extract FCW_Active bit from byte 0 */
    fcwActive = (this.byte(0) >> 7) & 0x01;
    
    /* Extract vehicle speed from bytes 1-2 (uint16, factor 0.01 km/h) */
    vehicleSpeed = ((float)((this.byte(1) << 8) | this.byte(2))) * 0.01;
    
    if (fcwActive == 1) {
        write("[EVENT] FCW Active! Speed: %.1f km/h", vehicleSpeed);
        
        /* Log to environment variable for panel display */
        putValue(EnvFCW_Active, 1);
        putValue(EnvVehicleSpeed, vehicleSpeed);
        
        /* Start timing measurement */
        setTimer(t_WaitForResponse, 200);  /* Expect AEB within 200ms */
    }
}

/* Check AEB activation after FCW */
on message 0x201 {
    byte aebActive;
    aebActive = this.byte(0) & 0x01;
    
    if (aebActive == 1) {
        cancelTimer(t_WaitForResponse);
        write("[OK] AEB activated within timing spec");
        testStepPass("AEB response time within 200ms of FCW");
    }
}
```

### CAPL — SOME/IP Simulation Node (Server)

```c
/*============================================================
  SIMULATE RADAR ECU as SOME/IP Server in CANoe
  Sends RadarObject events at 20ms via SOME/IP
  ============================================================*/
variables {
    msTimer t_RadarEventTimer;
    int     sessionId       = 1;
    float   objectDistance  = 10.0;  /* meters */
    float   objectSpeed     = 80.0;  /* km/h */
    byte    isObjectValid   = 1;
}

on start {
    /* Start radar simulation */
    write("[SIM] RADAR ECU simulation started");
    setTimer(t_RadarEventTimer, 20);  /* Send every 20ms */
}

on timer t_RadarEventTimer {
    byte someipFrame[256];
    int  offset = 0;
    
    /* Build SOME/IP header */
    someipFrame[offset++] = 0x00; someipFrame[offset++] = 0x01; /* Service ID */
    someipFrame[offset++] = 0x80; someipFrame[offset++] = 0x01; /* Method ID (notification) */
    
    /* Length placeholder — fill after payload */
    int lengthOffset = offset;
    offset += 4;
    
    /* Client ID = 0x0000 for notifications */
    someipFrame[offset++] = 0x00; someipFrame[offset++] = 0x00;
    
    /* Session ID — increment per message */
    someipFrame[offset++] = (byte)(sessionId >> 8);
    someipFrame[offset++] = (byte)(sessionId & 0xFF);
    sessionId++;
    
    someipFrame[offset++] = 0x01; /* Protocol version */
    someipFrame[offset++] = 0x01; /* Interface version */
    someipFrame[offset++] = 0x02; /* Message type: NOTIFICATION */
    someipFrame[offset++] = 0x00; /* Return code: E_OK */
    
    /* Payload: RadarObject (distance + speed + valid flag) */
    long rawDist  = (long)(objectDistance * 10.0);  /* 0.1m resolution */
    long rawSpeed = (long)(objectSpeed    * 10.0);  /* 0.1 km/h resolution */
    
    someipFrame[offset++] = (byte)(rawDist >> 8);
    someipFrame[offset++] = (byte)(rawDist & 0xFF);
    someipFrame[offset++] = (byte)(rawSpeed >> 8);
    someipFrame[offset++] = (byte)(rawSpeed & 0xFF);
    someipFrame[offset++] = isObjectValid;
    
    /* Fill in length field */
    long payLen = offset - lengthOffset - 4; /* Remaining after header */
    someipFrame[lengthOffset]   = (byte)((payLen >> 24) & 0xFF);
    someipFrame[lengthOffset+1] = (byte)((payLen >> 16) & 0xFF);
    someipFrame[lengthOffset+2] = (byte)((payLen >>  8) & 0xFF);
    someipFrame[lengthOffset+3] = (byte)(payLen         & 0xFF);
    
    /* Send UDP packet via CANoe Ethernet socket */
    udpSend("ETH1", "239.255.0.1", 30490, someipFrame, offset);
    
    /* Simulate slow-approaching object */
    objectDistance -= 0.1;
    if (objectDistance < 0.0) objectDistance = 10.0; /* Reset */
    
    setTimer(t_RadarEventTimer, 20);
}
```

---

## 6.4 CANalyzer

### CANalyzer vs CANoe

| Feature | CANalyzer | CANoe |
|---------|-----------|-------|
| Purpose | Analysis only | Analysis + Simulation |
| CAPL | Read-only monitoring | Full read/write simulation |
| Test automation | No | Yes (vTESTstudio) |
| Simulation nodes | No | Yes |
| Cost | Lower | Higher |
| Typical Use | Field debugging | Lab development/testing |

### CANalyzer for Quick Ethernet Debugging

```
USE CASES FOR CANalyzer IN AUTOMOTIVE ETHERNET:

1. FIELD DEBUG — Vehicle ethernet capture
   ├── Connect VN5640 to OBD Ethernet port
   ├── Open CANalyzer, load .arxml SOME/IP database
   ├── Trace window shows decoded SOME/IP service calls
   └── Filter on specific service ID to find anomaly

2. SIGNAL MONITORING
   ├── Load .dbc database
   ├── Data window: real-time CAN signal values
   └── Export signal log for offline analysis

3. STATISTICS
   ├── Frame rate per protocol
   ├── Error frame count
   └── Bus load calculation
```

---

## 6.5 vTESTstudio — TEST AUTOMATION FRAMEWORK

### vTESTstudio Overview

vTESTstudio is Vector's IDE for automated test case development. It runs test cases within CANoe and generates reports conforming to automotive standards (ISO 26262, ASPICE).

### Test Module Structure

```
vTESTstudio TEST PROJECT STRUCTURE:
├── TestSuite_Ethernet.vtestunit
│   ├── TestGroup_SOME_IP/
│   │   ├── TC_SOMEIP_001_ServiceDiscovery.vtest
│   │   ├── TC_SOMEIP_002_EventRate.vtest
│   │   ├── TC_SOMEIP_003_MethodCall.vtest
│   │   └── TC_SOMEIP_004_ErrorHandling.vtest
│   ├── TestGroup_DoIP/
│   │   ├── TC_DOIP_001_RoutingActivation.vtest
│   │   ├── TC_DOIP_002_DiagnosticMessage.vtest
│   │   └── TC_DOIP_003_FlashSequence.vtest
│   └── TestGroup_TSN/
│       ├── TC_TSN_001_ClockSync.vtest
│       └── TC_TSN_002_TASCompliance.vtest
```

### vTESTstudio Test Case — Example

```python
# vTESTstudio uses a Python-like syntax (CAPL or Python)

test case TC_SOMEIP_001_ServiceDiscovery:
    
    # Test metadata
    title = "SOME/IP Service Discovery - OfferService"
    version = "1.0"
    requirement = "REQ-ETH-SOMEIP-001"
    
    setup:
        # Reset DUT
        send_can_signal("ECU_Reset", 1)
        wait(2000)  # Wait 2 seconds for ECU startup
    
    body:
        # Wait for OfferService packet
        result = wait_for_someip_sd_offer(
            service_id = 0x0001,
            timeout_ms = 3000
        )
        
        if result.received:
            check(result.service_id == 0x0001, "Service ID correct")
            check(result.instance_id == 0x0001, "Instance ID correct")
            check(result.major_version == 1, "Major version correct")
            check(result.ttl > 0, "TTL is valid")
            test_step_pass("OfferService received and validated")
        else:
            test_step_fail("No OfferService within 3 seconds")
    
    teardown:
        # No teardown needed
        pass
```

### CAPL Test Functions in vTESTstudio

```c
/* CAPL test case in vTESTstudio */
testcase TC_SOMEIP_002_EventRate()
{
    int     eventCount     = 0;
    float   firstEventTime = 0.0;
    float   lastEventTime  = 0.0;
    float   avgPeriod      = 0.0;
    float   tolerance      = 2.0; /* ms */
    int     targetEvents   = 50;
    
    /* Start test */
    testCaseTitle("TC_SOMEIP_002", "SOME/IP Event Rate Validation");
    testAddRequirement("REQ-ETH-SOMEIP-002");
    
    testWaitForTimeout(200); /* Settle time */
    
    /* Enable SOME/IP event capture */
    enableSomeIpEventCapture(0x0001, 0x8001);
    
    /* Collect events for 2 seconds */
    testWaitForTimeout(2000);
    
    /* Analyze results */
    eventCount = getSomeIpEventCount(0x0001, 0x8001);
    avgPeriod  = getSomeIpEventAvgPeriod(0x0001, 0x8001);
    
    testStep("Event Count", 
             "Expected: >= %d, Actual: %d", targetEvents, eventCount);
    
    if (eventCount >= targetEvents) {
        testStepPass("Sufficient events received");
    } else {
        testStepFail("Insufficient events");
    }
    
    testStep("Event Period",
             "Expected: 20ms ± %.1fms, Actual: %.2fms", tolerance, avgPeriod);
    
    if (avgPeriod >= (20.0 - tolerance) && avgPeriod <= (20.0 + tolerance)) {
        testStepPass("Event period within tolerance");
    } else {
        testStepFail("Event period out of tolerance");
    }
}
```

---

## 6.6 COMPLETE CANoe ETHERNET TEST SETUP

### Hardware Connections — CANoe with VN5640

```
TEST BENCH SETUP FOR ETHERNET ECU TESTING:

PC (CANoe 15.x)
├── USB 3.0 → VN5640 (Vector hardware interface)
│   ├── Ethernet CH1 ──── 100BASE-T1 ──── ADAS ECU (DUT)
│   ├── Ethernet CH2 ──── 100BASE-T1 ──── Ethernet Switch
│   ├── CAN CH1 ─────── CAN FD ─────── Gateway ECU
│   └── LIN CH1 ────── LIN ──────────── Body ECU
│
├── Wireshark ← SPAN port on Ethernet Switch
└── Power Supply (12V, 10A) → ECU power rails
```

### CANoe Configuration Steps for SOME/IP Testing

```
STEP-BY-STEP CANoe CONFIGURATION:

1. HARDWARE SETUP:
   File → Options → Measurement Setup → Add VN5640 
   Assign Ethernet channel to "ETH1"

2. DATABASE IMPORT:
   File → Open → Add database
   Import: adas_system.arxml (contains SOME/IP service definitions)
   Import: vehicle_signals.dbc (CAN signals)

3. SIMULATION NETWORK:
   Add CAPL node: "RADAR_SIM" (simulates RADAR ECU)
   Add CAPL node: "TEST_NODE" (test script)
   Connect ETH1 to both nodes

4. ETHERNET SETTINGS:
   ETH1 → Properties:
   ├── Speed: 100 Mbps
   ├── Duplex: Full
   ├── VLAN: enabled, default VID = 10
   └── Promiscuous: enabled (captures all frames)

5. TRACE WINDOW:
   Analysis → Trace → Add column: SOME/IP Service ID
   Filter: UDP.Port == 30490 (SOME/IP only)

6. START MEASUREMENT: F9 (or Start button)
```

---

## 6.7 DIAGNOSTIC TESTING WITH CANoe

### CANoe Diagnostic Console — DoIP Testing

```
STEP-BY-STEP DoIP DIAGNOSTIC SESSION IN CANoe:

1. Configure DoIP Transport:
   Diagnostics → Diagnostic/ISO TP → DoIP
   Enter: ECU IP address, Logical Address = 0x0010
   Transport: TCP, Port = 13400

2. Open Diagnostic Window:
   Diagnostics → New Diagnostic Request
   Select: ECU = ADAS_ECU
   Service: DiagnosticSessionControl
   Parameters: sessionType = programmingSession

3. Execute Request:
   Click "Send" → CANoe builds UDS frame
   DoIP wraps UDS in TCP → sends to ECU IP

4. View Response:
   Response window shows: 0x50 0x02 (positive response)
   If negative: 0x7F 0x10 0x22 (conditions not correct)

5. Read DTC (0x19 02):
   DTC tab → "Read all confirmed DTCs"
   Shows: DTC list with status bytes
   
6. Security Access via CANoe:
   Security Access → SecurityAccessPlugin (.dll)
   Plugin calculates KEY from SEED automatically
   Tests entire Security Access sequence
```

### CAPL Diagnostic Script — Full UDS Sequence

```c
/* Automated UDS diagnostic sequence in CAPL */
variables {
    msTimer t_DiagTimer;
    int diagState = 0;
    byte seed[4];
    byte key[4];
}

on start {
    diagState = 0;
    setTimer(t_DiagTimer, 500);  /* Start after 500ms */
}

on timer t_DiagTimer {
    switch(diagState) {
        
        case 0: /* Send DiagnosticSessionControl → ExtendedDiagnostic */
            diagRequest ADAS_ECU.DiagnosticSessionControl(0x03);
            diagState = 1;
            setTimer(t_DiagTimer, 500);
            break;
            
        case 1: /* Send SecurityAccess → RequestSeed */
            diagRequest ADAS_ECU.SecurityAccess(0x01);  /* Seed request */
            diagState = 2;
            setTimer(t_DiagTimer, 500);
            break;
            
        case 2: /* Compute key and send SecurityAccess → SendKey */
            /* Received seed from ECU, compute key */
            seed[0] = diagResponse.Seed[0];
            seed[1] = diagResponse.Seed[1];
            seed[2] = diagResponse.Seed[2];
            seed[3] = diagResponse.Seed[3];
            
            /* Simple XOR key algorithm (example) */
            key[0] = seed[0] ^ 0xA5;
            key[1] = seed[1] ^ 0xB6;
            key[2] = seed[2] ^ 0xC7;
            key[3] = seed[3] ^ 0xD8;
            
            diagRequest ADAS_ECU.SecurityAccess(0x02, key);
            diagState = 3;
            setTimer(t_DiagTimer, 500);
            break;
            
        case 3: /* Read ECU software version via ReadDataByIdentifier */
            diagRequest ADAS_ECU.ReadDataByIdentifier(0xF189); /* SW version */
            diagState = 4;
            setTimer(t_DiagTimer, 500);
            break;
            
        case 4: /* Done — log result */
            write("[OK] Diagnostic sequence completed successfully");
            write("[OK] SW Version: %s", diagResponse.SWVersion);
            testStepPass("Full diagnostic sequence passed");
            break;
    }
}

on diagResponse ADAS_ECU.DiagnosticSessionControl {
    if (diagResponse.NRC != 0x00) {
        write("[FAIL] DiagSessionControl NRC: 0x%02X", diagResponse.NRC);
        testStepFail("Session control failed");
    }
}
```

---

## 6.8 CAPL INTERVIEW QUESTIONS — 30 Q&A

**Q1: What is CAPL and what are its key features?**
> CAPL is an event-driven, C-like scripting language used in Vector CANoe/CANalyzer. Key features: event handlers (on message, on timer, on key, on ethernetPacket), built-in automotive protocol functions (diagRequest, udpSend), direct access to frames via `this` keyword, and integration with vTESTstudio for automated testing.

**Q2: What is the difference between `on message` and `on ethernetPacket`?**
> `on message <ID>` fires for CAN frames matching a specific CAN ID. `on ethernetPacket` fires for every Ethernet frame received by the CAPL node. Within `on ethernetPacket`, you can filter by EtherType, IP protocol, UDP/TCP port, and payload content.

**Q3: How do you measure message period in CAPL?**
> Use `timeNow()` to get the current timestamp. Store it in a `lastTime` variable on first event. On subsequent events, calculate `delta = timeNow() - lastTime; lastTime = timeNow();`. Assert delta is within expected period ± tolerance. Use `timeNow() / 100000.0` to convert from 100ns ticks to milliseconds.

**Q4: Explain how timers work in CAPL.**
> Declare `msTimer myTimer;` in variables block. Start with `setTimer(myTimer, delayMs)`. Handle expiry with `on timer myTimer { }`. Cancel with `cancelTimer(myTimer)`. Timers are one-shot by default — call `setTimer()` again inside the handler for periodic behavior. Never call blocking functions inside timer handlers.

**Q5: How do you send a UDS diagnostic request using CAPL?**
> Use `diagRequest ECU_Name.ServiceName(params)` for database-configured services, or manually build frames using `output()` with a `diagRequest` object. Set service ID, subfunction, and parameters. Monitor response with `on diagResponse ECU_Name.ServiceName` handler.

**Q6: What is `output()` in CAPL?**
> `output(message)` transmits a CAN/LIN/Ethernet frame or diagnostic message. For CAN: `message 0x200 msg; msg.byte(0) = 0x01; output(msg);`. This sends a CAN frame with ID 0x200.

---

*Next Section → [Section 7: Diagnostics UDS/DoIP](07_Diagnostics_UDS_DoIP.md)*
