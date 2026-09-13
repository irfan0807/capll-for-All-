# PART 1 — AUTOMOTIVE ECU SOFTWARE EXPLAINED
## From Sensor to Actuator — Complete Understanding

**Learning Time:** 3 hours  
**Difficulty:** Beginner (but explained at expert depth)  
**Interview Frequency:** 100% (Asked in every interview)

---

## TABLE OF CONTENTS

1. [What is an ECU?](#what-is-an-ecu)
2. [Real-World Example: Sensor → ECU → Actuator](#real-world-example)
3. [Microcontroller Fundamentals](#microcontroller-fundamentals)
4. [ECU Software Layers](#ecu-software-layers)
5. [Boot Sequence](#boot-sequence)
6. [Application Software](#application-software)
7. [Communication Basics](#communication-basics)
8. [Key Concepts Summary](#key-concepts-summary)
9. [Interview Q&A](#interview-qa)

---

## WHAT IS AN ECU?

### Simple Definition
An ECU (Electronic Control Unit) is a **specialized computer inside a car** that:
- Reads sensor signals (temperature, pressure, speed, etc.)
- Makes decisions based on software logic
- Controls actuators (motors, valves, lights, etc.)
- Communicates with other ECUs over a car network

### Example: ABS (Anti-Lock Braking) ECU
```
Wheel Speed Sensors (Input)
    ↓
ABS ECU (Decision Logic)
    ↓
Brake Valve Control (Output)
    ↓
Prevent wheel lockup ✓
```

### Technical Definition
An ECU is a **specialized embedded computer** consisting of:
- **Microcontroller (CPU)**
- **Memory (ROM, RAM, Flash, EEPROM)**
- **Power supply and voltage regulation**
- **Communication interfaces (CAN, LIN, Ethernet)**
- **Analog-to-Digital Converters (ADC)**
- **Digital-to-Analog Converters (DAC)**
- **Watchdog timer**
- **I/O ports for sensors/actuators**

### Why ECUs Matter
Modern vehicles have **50-100+ ECUs**:
- Engine Control Module (ECM) - Controls engine
- Transmission Control Module (TCM) - Controls gearbox
- ABS Module - Prevents wheel lockup
- Airbag Module - Deploys airbags
- Body Control Module (BCM) - Doors, lights, windows
- Infotainment Module - Audio, navigation
- ... and many more

**The Test Analyst's Job:** Verify all ECUs work correctly and communicate properly.

---

## REAL-WORLD EXAMPLE: SENSOR → ECU → ACTUATOR

### Example 1: Electronic Parking Brake (EPB)

```
┌─────────────────────────────────────────────────────────┐
│  EPB ECU WORKFLOW                                        │
└─────────────────────────────────────────────────────────┘

INPUT (Sensors):
  • Driver presses EPB button
  • Vehicle speed sensor
  • Brake pressure sensor
  • Temperature sensor
  • Position feedback sensor (brake status)

INPUT (Communication):
  • CAN message from Body Control Module
  • UDS diagnostic request from tester

ECU LOGIC (Software):
  IF (driver_pressed_button AND vehicle_speed < 3 km/h) THEN
    IF (brake_pressure > MIN_PRESSURE) THEN
      Activate brake motor
    ELSE
      Set fault code P2587
    END IF
  END IF

OUTPUT (Actuators):
  • Motor control signal → Brake actuator
  • LED indicator → Dashboard (via CAN)
  • Cooling fan → Thermal management

OUTPUT (Communication):
  • CAN message: "Brake status ENGAGED"
  • CAN message: "Brake temperature 65°C"
  • Set diagnostic trouble code (DTC)
```

### How Test Analyst Tests This

**Test Case: EPB Engagement**
```
Objective:  Verify parking brake engages when button pressed
Preconditions: Vehicle at standstill, engine running
Test Steps:
  1. Monitor CAN signal: Vehicle_Speed
  2. Send: EPB_Button = PRESSED (via CAN or physical)
  3. Monitor: Brake_Motor_Command (should be ON)
  4. Monitor: Brake_Position_Feedback (should move)
  5. Monitor: EPB_Status message on CAN (should be ENGAGED)
Expected:   Brake motor activates, position changes, status on CAN
Logs:       CAN trace, ADC readings, motor current
```

### Example 2: Engine Temperature Monitoring

```
INPUT (Sensor - Coolant Temperature):
  • Thermistor reads -40°C to +125°C
  • Analog voltage sent to ECU ADC (0-5V)
  • ADC converts to digital value (0-4095)
  • Software converts to temperature (-40 to +125°C)

ECU LOGIC:
  IF (coolant_temp > 100°C) THEN
    Fan_speed = HIGH
    Activate_cooling_pump = TRUE
  ELSE IF (coolant_temp < 95°C) THEN
    Fan_speed = LOW
  END IF
  
  IF (coolant_temp > 115°C) THEN
    Set_DTC_Engine_Overtemp = TRUE
    Request_reduced_power_mode = TRUE
  END IF

OUTPUT (Actuators):
  • Fan PWM signal (0-100%)
  • Cooling pump relay
  
OUTPUT (Communication):
  • CAN message "Engine_Temperature: 98°C"
  • Set trouble code P0128
```

### Key Learning: Feedback Loops

Modern ECUs use **negative feedback loops**:
```
Temperature rises
    ↓
ECU detects via sensor
    ↓
ECU increases fan speed
    ↓
Coolant cools down
    ↓
Sensor reading decreases
    ↓
ECU decreases fan speed
    ↓
System stabilizes ✓
```

This is **cruise control**, **traction control**, **temperature management**, etc.

---

## MICROCONTROLLER FUNDAMENTALS

### What is a Microcontroller?

A microcontroller is a **complete computer on a single chip**:

```
┌──────────────────────────────────┐
│   MICROCONTROLLER (MCU)          │
│                                  │
│  ┌──────────────┐                │
│  │  CPU Core    │ 32-bit, 64-bit │
│  └──────────────┘                │
│                                  │
│  ┌──────────────┐                │
│  │  Flash ROM   │ Program storage│
│  │  (256K-2M)   │ Permanent      │
│  └──────────────┘                │
│                                  │
│  ┌──────────────┐                │
│  │  RAM         │ Working memory │
│  │  (64K-512K)  │ Temporary      │
│  └──────────────┘                │
│                                  │
│  ┌──────────────┐                │
│  │  EEPROM      │ Configurable   │
│  │  (4K-64K)    │ Storage        │
│  └──────────────┘                │
│                                  │
│  ┌──────────────┐                │
│  │  Peripherals │ CAN, LIN, SPI  │
│  │  (Timers,    │ UART, I2C      │
│  │  ADC, PWM)   │ ADC, DAC, GPIO │
│  └──────────────┘                │
│                                  │
│  ┌──────────────┐                │
│  │  Watchdog    │ Monitors CPU   │
│  │  Timer       │ Detects hangs  │
│  └──────────────┘                │
│                                  │
│  ┌──────────────┐                │
│  │  Oscillator  │ Clock signal   │
│  │  (16-200MHz) │ Timing         │
│  └──────────────┘                │
│                                  │
└──────────────────────────────────┘
```

### Popular Automotive Microcontrollers

| MCU Family | Manufacturer | Used In | Speed | RAM |
|------------|--------------|---------|-------|-----|
| **STM32** | STMicroelectronics | Body, Lighting, Door control | 32-200 MHz | 32K-384K |
| **MPC5** | NXP | Engine, Transmission, Powertrain | 120-200 MHz | 64K-1M |
| **RH850** | Renesas | Engine, Safety-critical | 80-200 MHz | 128K-2M |
| **Aurix** | Infineon | Powertrain, ADAS | 200+ MHz | 256K-2M |
| **TC397** | Infineon | Advanced ADAS, Autonomous | 300 MHz | 2M |

### Memory Types Explained

**Flash ROM (Permanent Storage)**
- Stores the ECU program (firmware)
- Survives power-off
- Cannot be quickly rewritten (takes minutes to erase/write)
- Updated during ECU flashing/programming
- Typical size: 256K - 2M bytes

**RAM (Working Memory)**
- Used during program execution
- Lost when powered off
- Fast read/write (nanoseconds)
- Stores variables, sensor data, CAN messages
- Typical size: 64K - 512K bytes

**EEPROM (Configurable Storage)**
- Stores calibration data and configuration
- Can be rewritten during runtime
- Slower than RAM, faster than Flash
- Survives power-off
- Typical size: 4K - 64K bytes

### Real Example: Memory Map
```
┌──────────────────────────────────┐
│  Flash (512K)                    │
├──────────────────────────────────┤
│ 0x00000000: Boot code            │
│ 0x00002000: Kernel               │
│ 0x00010000: Application software │
│ 0x00050000: Calibration data     │
│ 0x00070000: Spare area           │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  RAM (256K)                      │
├──────────────────────────────────┤
│ 0x20000000: Stack                │
│ 0x20001000: Global variables     │
│ 0x20010000: CAN message buffers  │
│ 0x20020000: Sensor data cache    │
│ 0x20030000: Heap                 │
└──────────────────────────────────┘
```

---

## ECU SOFTWARE LAYERS

### Layered Architecture (AUTOSAR Concept)

```
┌─────────────────────────────────────────────────────┐
│  APPLICATION LAYER                                  │
│  (Your software - engine control, brake logic, etc) │
└─────────────────────────────────────────────────────┘
              ↑           ↓           ↑           ↓
┌─────────────────────────────────────────────────────┐
│  RUNTIME ENVIRONMENT (RTE)                          │
│  (Manages communication between components)         │
└─────────────────────────────────────────────────────┘
              ↑           ↓           ↑           ↓
┌─────────────────────────────────────────────────────┐
│  BASIC SOFTWARE (BSW) LAYERS                        │
│  ├── Communication stack (CAN, LIN, Ethernet)      │
│  ├── Diagnostic stack (UDS)                         │
│  ├── NVM (non-volatile memory)                      │
│  ├── ECU Abstraction (hardware independence)       │
│  └── MCAL (microcontroller abstraction layer)      │
└─────────────────────────────────────────────────────┘
              ↑           ↓           ↑           ↓
┌─────────────────────────────────────────────────────┐
│  MICROCONTROLLER HARDWARE                           │
│  (CPU, RAM, Flash, CAN, ADC, PWM, GPIO)            │
└─────────────────────────────────────────────────────┘
```

### Layer Explanation

**APPLICATION LAYER**
- Your business logic
- Engine control algorithms
- Brake logic
- Safety mechanisms
- What test engineers care about MOST

Example code:
```c
// Application layer - Engine control
void Engine_Control_Task(void) {
    uint16_t engine_speed = Get_Engine_Speed();
    uint16_t throttle_position = Get_Throttle_Position();
    uint8_t fuel_injection_time;
    
    if (engine_speed > 6000) {
        fuel_injection_time = Calculate_Fuel_Cut_off();
    } else {
        fuel_injection_time = Calculate_Normal_Fuel(throttle_position);
    }
    
    Set_Fuel_Injector(fuel_injection_time);
}
```

**RUNTIME ENVIRONMENT (RTE)**
- Handles communication between application components
- Software components don't talk directly
- RTE ensures safe inter-task communication
- Based on AUTOSAR standards

**BASIC SOFTWARE (BSW)**

*Communication Stack*
- Sends/receives CAN messages
- Sends/receives LIN messages
- Handles Ethernet frames
- Buffers messages
- Example: A sensor value from another ECU comes here first

*Diagnostic Stack*
- Handles UDS requests
- Reads/writes DTCs
- Performs security access
- Example: Tester sends "Read DTC" → Diagnostic stack processes it

*NVM Manager*
- Stores/loads configuration from EEPROM
- Ensures data integrity
- Example: EPB calibration data is stored/loaded here

*ECU Abstraction*
- Abstracts hardware differences
- Same application code works on different MCUs
- Test engineers don't need to know this layer

**MCAL (Microcontroller Abstraction Layer)**
- Controls actual hardware
- Sets/clears GPIO pins
- Reads ADC values
- Transmits CAN frames
- Enables/disables interrupts
- Test engineers care about this for debugging

**HARDWARE**
- The actual microcontroller
- Sensors and actuators
- Power supply
- Oscillator (clock)

### Test Engineer's Perspective

**You care most about:**
1. ✅ Application layer (What does it do?)
2. ✅ Communication layer (How do ECUs talk?)
3. ✅ Diagnostic layer (How do we read faults?)
4. ⚠️ MCAL (For hardware-specific debugging)
5. ❌ RTE internals (Not your responsibility)

---

## BOOT SEQUENCE

### What Happens When You Start the Car?

```
┌─────────────────────────────────┐
│  KEY TURNED ON (Power Applied)  │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│  BOOTLOADER EXECUTION            │
│  • Initialize oscillator         │
│  • Configure PLL (clock)         │
│  • Check Flash integrity (CRC)   │
│  • Initialize SRAM               │
│  • Load application from Flash   │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│  HARDWARE INITIALIZATION         │
│  • Enable watchdog               │
│  • Configure I/O ports           │
│  • Initialize CAN controller     │
│  • Initialize UART               │
│  • Setup ADC, timers             │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│  OS / RTOS STARTUP               │
│  • Initialize scheduler          │
│  • Start periodic tasks          │
│  • Enable interrupts             │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│  APPLICATION INITIALIZATION      │
│  • Load calibration data         │
│  • Initialize modules            │
│  • Read first sensor values      │
│  • Set initial actuator states   │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│  COMMUNICATE WITH OTHER ECUs     │
│  • Send "I am online" message    │
│  • Receive network status        │
│  • Synchronize with other ECUs   │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│  RUN SELF-CHECKS                 │
│  • Check sensor plausibility     │
│  • Check communication alive     │
│  • Check memory integrity        │
│  • Check watchdog functioning    │
│  • ALL CHECKS PASS? Yes ✓        │
└──────────────────────────────────┘
         ↓
┌──────────────────────────────────┐
│  ECU READY FOR OPERATION         │
│  Ready to receive commands       │
└──────────────────────────────────┘
```

### Critical: What Happens if Boot Fails?

```
IF Flash CRC check FAILS:
  → ECU doesn't start
  → Stay in bootloader
  → Wait for reprogramming

IF Hardware init FAILS:
  → Cannot start OS
  → Set system fault
  → Activates safe state

IF Application init FAILS:
  → OS running but app not responding
  → Watchdog will detect hang
  → Force ECU reset

IF Self-checks FAIL:
  → Don't start engine
  → Set diagnostic trouble code
  → Show error on dashboard
```

### Test Implications

**Tests for boot sequence:**
- Does ECU start within spec time (e.g., 500ms)?
- Do all modules initialize correctly?
- Are all CAN messages sent after boot?
- Is watchdog active?
- Can ECU recover from power loss?

---

## APPLICATION SOFTWARE

### What Application Software Does

Application software is **YOUR software** - the actual control logic.

### Example: Electronic Power Steering (EPS)

```
┌─────────────────────────────────────────────────────┐
│  APPLICATION LAYER - EPS Logic                      │
└─────────────────────────────────────────────────────┘

INPUT:
  • Steering wheel angle (sensor input)
  • Steering wheel speed (how fast turning)
  • Vehicle speed (from CAN)
  • Yaw rate (from IMU/CAN)
  • Motor current (feedback)

PROCESS:
  steering_assist = Calculate_Assist_Torque(
    steering_angle,
    steering_speed,
    vehicle_speed,
    yaw_rate
  );
  
  IF (steering_assist > MAX_ASSIST) THEN
    steering_assist = MAX_ASSIST;  // Clamp it
    Set_Fault_Code(EPS_LIMIT_REACHED);
  END IF;
  
  IF (motor_current > MOTOR_MAX_CURRENT) THEN
    steering_assist = Reduce_By_50%;
    Set_Fault_Code(MOTOR_OVERCURRENT);
  END IF;

OUTPUT:
  • Motor control signal (PWM)
  • Assist torque CAN message
  • Fault codes
  • System status indicator
```

### Real Test Case for EPS

```
Test Case: EPS Assist at Various Speeds

Preconditions:
  • Vehicle speed = 0 km/h
  • Engine running
  • EPS module online

Test Steps:
  1. Rotate steering wheel 45° to right
  2. Measure motor assist current
  3. Measure steering wheel torque resistance
  4. Record in CAN: EPS_Assist_Torque
  
  5. Increase vehicle speed to 60 km/h (via CAN simulation)
  6. Rotate steering wheel 45° to right (same angle)
  7. Measure motor assist current (should be LOWER at higher speed)
  8. Record in CAN: EPS_Assist_Torque (should be lower)
  
  9. Increase vehicle speed to 120 km/h
  10. Repeat: Assist should be even lower

Expected Results:
  • At 0 km/h:   Motor current = 15A, CAN torque = 5 Nm
  • At 60 km/h:  Motor current = 8A,  CAN torque = 2.7 Nm
  • At 120 km/h: Motor current = 3A,  CAN torque = 1 Nm
  
Logs Required:
  • CAN trace showing EPS_Assist_Torque decreasing
  • Motor current measurements
  • Timing: Latency from steering input to motor response < 50ms
```

---

## COMMUNICATION BASICS

### Why Do ECUs Need to Communicate?

```
Modern vehicle ECU network:

Engine ECU ←→ (CAN) ←→ Transmission ECU
    ↓                        ↓
    ├─→ (CAN) ←─────→ Body Control Module
    ├─→ (CAN) ←─────→ ABS Module
    ├─→ (CAN) ←─────→ Dashboard
    ├─→ (LIN) ←─────→ Door Lock Module (slower messages)
    └─→ (Ethernet) ←→ Infotainment (high bandwidth)

Why?
  • Engine needs transmission status: "What gear requested?"
  • ABS needs wheel speeds: "Which wheel is locked?"
  • Dashboard needs all data: "Show speed, fuel, faults"
  • Transmission needs engine status: "Is engine ready?"
  • Door module needs battery voltage: "Is power OK?"
```

### CAN Bus Explained (Simple)

```
CAN Bus: A shared "conversation wire" all ECUs listen to

Every ECU sends messages like:
  "Here's the engine speed: 2500 RPM"
  "Here's the vehicle speed: 60 km/h"
  "I have a fault: Engine overtemp"

Every ECU that needs this data listens and uses it.

Message Example:
  ID:   0x123 (Unique message identifier)
  DLC:  8 (8 bytes of data)
  Data: 0x0A 0xC8 0xFF 0x00 0x00 0x00 0x00 0x00
        (Engine Speed = 2760 RPM encoded in these bytes)

All ECUs connected to same CAN bus get this message simultaneously.
```

### Communication Example: Vehicle Speed

```
Step 1: Speed Sensor reads actual speed
  Wheel encoder → 1500 pulses per second
  ABS ECU calculates: 1500 pulses/sec → 60 km/h

Step 2: ABS ECU sends CAN message
  Message ID: 0x220 (ABS_Status)
  Data: [0x00, 0xF0, ...] 
  (First 2 bytes = 0x00F0 = 240 decimal = 60 km/h)

Step 3: Other ECUs receive message
  Engine ECU: Uses speed for shift logic
  Dashboard: Shows speed on speedometer
  EPS ECU: Uses speed for steering assist
  Infotainment: Uses speed for adaptive audio

All receive at same time! (~10ms)
```

### Test Engineer's Role

**Communication testing:**
- ✅ Does ECU send correct message?
- ✅ Does ECU receive messages correctly?
- ✅ What happens if message is missing?
- ✅ What happens if message is delayed?
- ✅ What happens if message has wrong data?
- ✅ Do all ECUs synchronize on critical signals?

---

## KEY CONCEPTS SUMMARY

### ECU Definition
```
ECU = Microcontroller + Software + Sensors/Actuators + Communication
```

### Execution Model
```
Continuous loop (every 10ms typically):
  1. Read sensor inputs
  2. Execute application logic
  3. Calculate actuator outputs
  4. Send CAN/LIN messages
  5. Go back to step 1
```

### Key Responsibilities
```
ECU must:
  ✓ Read inputs accurately
  ✓ Process logic correctly
  ✓ Output correct actuator signals
  ✓ Communicate on schedule
  ✓ Monitor itself (watchdog)
  ✓ Detect and report faults
  ✓ Enter safe state if critical fault
  ✓ Allow diagnostics (UDS)
```

### Test Focus Areas
```
1. Sensor input validation
   - Correct values read?
   - Plausibility checks?
   - Range violations detected?

2. Logic correctness
   - Algorithm correct?
   - State transitions correct?
   - Edge cases handled?

3. Output correctness
   - Correct PWM signals?
   - Correct CAN messages?
   - Correct timing?

4. Communication
   - Messages sent on schedule?
   - Messages received?
   - Response to CAN timeouts?

5. Safety and diagnostics
   - Fault detection working?
   - Safe state activation?
   - DTC codes correct?
   - UDS responses correct?
```

---

## INTERVIEW Q&A

### Q1: "What is an ECU? Explain in 30 seconds."
**Good Answer:**
"An ECU is a specialized embedded computer that reads sensor signals, executes control logic, and drives actuators. Multiple ECUs in a vehicle communicate over CAN/LIN networks. My job is to verify the ECU correctly reads inputs, executes logic, produces correct outputs, and communicates properly with other ECUs."

### Q2: "Explain the flow from sensor to actuator."
**Good Answer:**
"Sensor sends analog signal → ECU's ADC converts to digital → Software reads value → Logic processes it → Software calculates output → PWM/CAN message sent → Actuator responds. The ECU also monitors feedback to ensure actuator moved correctly, creating a closed-loop system."

### Q3: "What happens when an ECU starts?"
**Good Answer:**
"On power-on: Bootloader initializes hardware, checks Flash CRC, loads application. Then RTOS starts, application initializes modules, loads calibration data. ECU runs self-checks (watchdog, memory, sensors). Only after all checks pass does ECU become fully operational. If any check fails, ECU enters safe state or waits for reprogramming."

### Q4: "Why do ECUs communicate?"
**Good Answer:**
"Modern vehicles need coordination between systems. Engine ECU needs transmission status to optimize shifting. ABS ECU needs wheel speeds to prevent lockup. Dashboard needs data from all ECUs. This requires a shared communication bus (CAN), where each ECU sends relevant data and receives data it needs, all simultaneously."

### Q5: "What do you test in an ECU?"
**Good Answer:**
"I verify: (1) Sensor input handling - correct values read, plausibility checks, (2) Application logic - algorithms execute correctly, (3) Actuator control - correct outputs, (4) Communication - messages sent/received on schedule, fault response, (5) Safety - fault detection, safe state activation, (6) Diagnostics - DTC codes, UDS responses."

### Q6: "What is the difference between Flash, RAM, and EEPROM?"
**Good Answer:**
"Flash stores the ECU firmware permanently but is slow to erase/write (programming). RAM is fast working memory lost on power-off. EEPROM stores configuration and can be rewritten during runtime. Application code runs from RAM after being loaded from Flash on startup."

### Q7: "What is a watchdog timer?"
**Good Answer:**
"A watchdog is a hardware timer that resets the ECU if not 'kicked' (reset) periodically by software. If software hangs (infinite loop, crash), it can't kick the watchdog, so watchdog triggers a reset. This provides automatic recovery from software faults."

### Q8: "Describe an example ECU: Electronic Power Steering."
**Good Answer:**
"EPS ECU reads steering wheel angle and speed from sensors, receives vehicle speed and yaw rate from CAN, calculates required assist torque based on speed and angle, drives motor with PWM signal. Motor current is monitored for overcurrent faults. System provides more assist at low speeds (parking) and less at high speeds (highway). Faults are logged as DTC codes."

---

## KEY TAKEAWAYS

✅ **ECU = Computer + Software + Sensors + Communication**  
✅ **Execution: Read sensors → Execute logic → Control actuators (cyclically)**  
✅ **Communication: Multiple ECUs talk via CAN, coordinating vehicle operation**  
✅ **Boot: Firmware loads, hardware initializes, self-checks pass, then ready**  
✅ **Test Focus: Sensor validation, logic correctness, output accuracy, communication**  

---

## NEXT STEPS

→ **Read [Part 2: ECU Architecture](./02_ecu_architecture.md)** (Microcontroller, Memory, Bootloader)  
→ **Read [Part 3: Test Levels](./03_test_levels_comprehensive.md)** (How to test ECUs systematically)  
→ **Read [Part 6: CAN Protocol](./06_can_complete_guide.md)** (Deep dive into communication)  

---

**Last Updated:** 2025-09-01  
**Status:** Ready for study  
**Difficulty:** Beginner-Intermediate  
**Interview Priority:** 100% (Every interview)

---
