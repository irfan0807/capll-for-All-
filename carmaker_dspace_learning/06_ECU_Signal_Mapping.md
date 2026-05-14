# 06 — ECU Signal Mapping

> **Topic**: How to connect a real ECU to a dSPACE HIL rack  
> **Tools**: ConfigurationDesk, ControlDesk, BreakoutBox, oscilloscope  
> **Outcome**: Understand A/D-D/A mapping, PWM signals, restbus simulation, BIST bypass, fault injection

---

## 1. What Is ECU Signal Mapping?

Signal mapping means defining the **relationship between ECU hardware pins and the HIL simulation signals**. The HIL must perfectly replicate the signals the ECU expects from its real vehicle environment.

```
Real Vehicle Environment    →    HIL Simulation
───────────────────────────────────────────────────────────────
Throttle position sensor    →    DS2211 AO (0–5 V ramp)
Brake pressure sensor       →    DS2211 AO (0–5 V)
CAN restbus messages        →    DS1552 CAN Tx (DBC-driven)
Wheel speed pulses          →    DS2655 FPGA PWM output
Battery voltage 12 V        →    HIL power supply
Engine RPM signal           →    DS2655 FPGA frequency output
Radar object list           →    DS1552 CAN Tx (simulated)
Ignition (KL15)             →    DS2680 GPIO (12 V relay)
───────────────────────────────────────────────────────────────
```

---

## 2. Signal Types and Their HIL Equivalents

### Analog Signals (A/D and D/A)

```
ECU Analog Inputs (sensors the ECU reads):
  HIL must STIMULATE → use DS2211 Analog Output (D/A)
  
  Example: Throttle Position Sensor (TPS)
  ────────────────────────────────────────────────
  Sensor output range: 0.5 V – 4.5 V
  ECU reads this voltage and converts to:
    0.5 V  = 0%   throttle
    4.5 V  = 100% throttle

  HIL configuration:
    DS2211 AO Channel 1
    Scaling: y = 0.04 × throttle_pct + 0.5 [V]
    Range: 0.5 – 4.5 V
    Update rate: 1 ms (1 kHz)

ECU Analog Outputs (actuators the ECU drives):
  HIL must MEASURE → use DS2211 Analog Input (A/D)
  
  Example: EGR valve position command (0–10 V)
    DS2211 AI Channel 2
    Scaling: position_pct = (V - 0) / 10 × 100
```

### Scaling Formula for Sensor Simulation
```
Physical value → Voltage (what HIL outputs):
  V_out = (V_max - V_min) × (value - phys_min) / (phys_max - phys_min) + V_min

Example: Temperature sensor (-40°C to 150°C → 0.5 V to 4.5 V):
  V_out = (4.5 - 0.5) × (T + 40) / (150 + 40) + 0.5
  V_out = 4.0 × (T + 40) / 190 + 0.5

At T = -40°C: V_out = 0.5 V ✓
At T = 25°C:  V_out = 1.87 V
At T = 150°C: V_out = 4.5 V ✓
```

---

## 3. Digital Signals

```
Digital signal types in automotive:
───────────────────────────────────────────────────────────
Signal Type     ECU Use                  HIL Board
───────────────────────────────────────────────────────────
3.3 V logic     SPI CS, GPIO             DS2680 (3.3 V mode)
5 V logic       Legacy digital I/O       DS2680 (5 V mode)
12 V signal     KL15 (ignition), relays  DS2680 (12 V mode)
24 V signal     Truck/commercial vehicle DS2680 (24 V mode)
Open-drain      Fault flags, wake lines  DS2680 with pull-up
───────────────────────────────────────────────────────────

KL15 (ignition) simulation:
  DS2680 GPIO → relay → ECU KL15 pin
  Set HIGH = ignition on
  Set LOW  = ignition off

ECU wake-up sequence in HIL:
  1. Power ECU (12 V supply)
  2. Wait 100 ms (power stabilize)
  3. Assert KL15 (DS2680 GPIO HIGH)
  4. Wait 500 ms (ECU boot)
  5. Start bus simulation
```

---

## 4. PWM Signals

Many automotive sensors and actuators use PWM:

```
PWM signal examples:
  Wheel speed sensor:  50 – 2000 Hz square wave (speed-proportional)
  Fan speed feedback:  100 Hz, duty cycle = RPM/4000
  Fuel injector:       100–200 Hz pulse, variable width
  BLDC motor:          10–20 kHz switching

For > 1 kHz PWM → use DS2655 FPGA (not CPU):
  CPU task period = 1 ms = max 500 Hz PWM
  FPGA → generates PWM at up to 50 MHz resolution

Wheel speed simulation (FPGA):
  Target: 60 km/h, 4 pulses/revolution, tire radius 0.32 m
  
  Wheel RPM = (60/3.6) / (2π × 0.32) × 60 = 497 rpm
  Pulse frequency = 497 × 4 / 60 = 33.1 Hz per wheel

  FPGA block: DS2655 "PWM Generator"
    Frequency = Car.vx / (2 × π × 0.32) × 4 [Hz]
    Duty cycle = 50%
    Output: DS2680 GPIO Channel 0 (to ECU wheel speed pin)
```

---

## 5. CAN Restbus Simulation

**Restbus simulation** = the HIL sends all CAN messages that **real vehicle modules** would send, so the SUT ECU sees a realistic network.

```
Restbus concept:
────────────────────────────────────────────────────────
Real vehicle:                HIL restbus:
  ┌─────────┐                 ┌─────────────────────┐
  │ Engine  │──CAN───────────►│                     │
  │ ECU     │                 │  dSPACE DS1552       │
  ├─────────┤                 │  Restbus Simulator  │
  │ Brakes  │──CAN───────────►│  (replaces ALL      │
  │ ECU     │                 │   other ECUs)       │
  ├─────────┤                 │                     │
  │  SUT    │◄──CAN──────────►│                     │
  │  ECU    │                 │                     │
  └─────────┘                 └─────────────────────┘
────────────────────────────────────────────────────────
```

### Restbus Configuration Example (DBC-based)
```python
# Python example: configure CAN restbus signals
# (dSPACE AutomationDesk Python API equivalent)

restbus_signals = {
    # Message: EngineStatus (0x100, 10 ms cycle)
    "EngineStatus.EngineRPM":      lambda t: 800 + 400 * (t % 5),
    "EngineStatus.CoolantTemp":    lambda t: 90.0,
    "EngineStatus.EngineRunning":  lambda t: 1,

    # Message: WheelSpeeds (0x200, 10 ms cycle)
    "WheelSpeeds.FL_Speed_kmh":    lambda t: 50.0,
    "WheelSpeeds.FR_Speed_kmh":    lambda t: 50.0,
    "WheelSpeeds.RL_Speed_kmh":    lambda t: 50.0,
    "WheelSpeeds.RR_Speed_kmh":    lambda t: 50.0,
}
# In ConfigurationDesk: these are mapped from Simulink outputs
# In ControlDesk: can be overridden live during testing
```

---

## 6. BIST (Built-In Self Test) Bypass

Some ECUs run a BIST at startup and check for minimum signal conditions. The HIL must satisfy these before the ECU enters normal operation:

```
Typical BIST checks:
  ✓ Supply voltage: 12 V ± 10%
  ✓ Ignition present (KL15 = HIGH)
  ✓ CAN bus active within 2 s
  ✓ Wheel speed sensors alive (signals within range)
  ✓ No open-circuit faults on sensor inputs

HIL BIST bypass procedure:
  1. Apply power (12.0 V on supply)
  2. Set all analog outputs to nominal values:
     - Temp sensors: 2.0 V (25°C)
     - Pressure sensors: 2.5 V (nominal)
     - Position sensors: 2.5 V (center)
  3. Assert KL15 HIGH
  4. Wait 500 ms (ECU boot)
  5. Start restbus CAN simulation
  6. Verify ECU sends status message within 2 s
  7. ECU ready → begin test
```

---

## 7. Fault Injection

Fault injection tests how the ECU **responds to hardware failures**:

```
Fault categories:
──────────────────────────────────────────────────────────────
Fault Type          HIL Implementation         Board
──────────────────────────────────────────────────────────────
Open circuit        Remove signal (Hi-Z output) DS2211/DS2680
Short to GND        Drive output to 0 V         DS2211
Short to VCC        Drive output to 5 V         DS2211
Signal out of range Drive below/above spec       DS2211 (±10 V)
CAN bus error       Inject dominant bit error    DS1552
CAN node loss       Stop restbus message         SW (DBC)
Power brownout      Reduce supply to 9 V         Power supply
Power spike         Drive supply to 16 V briefly Power supply
──────────────────────────────────────────────────────────────
```

### Fault Injection Code (ControlDesk Python)
```python
import time

def inject_sensor_open_circuit(controldesk, channel="DS2211.AO.CH1"):
    """Simulate open-circuit fault on sensor supply."""
    original_value = controldesk.get(f"{channel}.Value")
    print(f"[FAULT] Injecting open circuit on {channel}")

    # Set output to high-impedance (open circuit simulation)
    controldesk.set(f"{channel}.Enable", 0)  # Disable output driver
    start_time = time.time()

    # Monitor ECU response
    for _ in range(20):
        dtc = controldesk.get("ECU.ActiveDTC.SensorOpenCircuit")
        if dtc == 1:
            elapsed = time.time() - start_time
            print(f"[PASS] ECU detected fault in {elapsed*1000:.1f} ms")
            break
        time.sleep(0.1)
    else:
        print("[FAIL] ECU did not detect open circuit fault")

    # Remove fault
    controldesk.set(f"{channel}.Enable", 1)
    controldesk.set(f"{channel}.Value", original_value)
    print("[FAULT] Fault removed, normal operation restored")
```

---

## 8. Signal Measurement and Verification

Always **verify the signal reaches the ECU pin** before trusting test results:

```
Verification workflow:
──────────────────────────────────────────────────────────────
1. ControlDesk: observe the HIL-side signal value
2. Oscilloscope: probe ECU connector pin directly
3. Compare: HIL output (ControlDesk) vs ECU pin (scope)
   If equal → mapping correct
   If different → check wiring, scaling, connector pinout

Common measurement points:
  - BreakoutBox: between ECU connector and HIL
  - Test clips: clip onto wire harness
  - Debug connector: special test plug on ECU housing

ControlDesk variable check:
  DS2211.AO.CH1.Value    → what HIL is outputting
  DS2211.AI.CH1.Value    → what HIL is measuring back
  (loop-back test: connect AO→AI, verify round-trip)
──────────────────────────────────────────────────────────────
```

---

## 9. Interview Q&A

**Q1: What is restbus simulation and why is it needed?**  
Restbus simulation means the HIL mimics all CAN messages that would normally come from other ECUs in the vehicle (engine ECU, brake ECU, body ECU, etc.). Without it, the SUT ECU would see an empty bus and go into error state, making testing impossible.

**Q2: How do you calculate the DS2211 output voltage for a temperature sensor?**  
You apply the linear scaling formula: V = (V_max − V_min) × (T − T_min) / (T_max − T_min) + V_min. For example, a −40 to 150°C sensor with 0.5–4.5 V output: at 25°C gives V = 4 × 65/190 + 0.5 = 1.87 V.

**Q3: Why would you use the FPGA instead of the CPU to generate a wheel speed signal?**  
Wheel speed at 120 km/h on a standard tire generates ~110 Hz, well within CPU range. But if the ECU also needs microsecond-accurate tooth timing for ABS angle detection, or if 4 independent wheel channels each need < 1 µs edge timing, the 1 ms CPU task isn't fast enough. The DS2655 FPGA generates edges at nanosecond resolution.

**Q4: What is BIST bypass in HIL testing?**  
Some ECUs run a built-in self-test at power-on, checking that all sensors are alive and within range. If the HIL doesn't provide valid signals from the start, the ECU enters a fail-safe or diagnostic mode and won't execute normal functions. BIST bypass means pre-loading all sensor stimulations with nominal values before the ECU boots.

**Q5: How do you inject a short-to-ground fault on a sensor input?**  
Using DS2211 Analog Output: set the output to 0 V (ground level) and enable the output driver. The output driver forces the bus to ground regardless of what the sensor would normally output. After the test, disable the fault by restoring the normal simulation value. For faster injection (< 1 µs), use the DS2655 FPGA with a solid-state switch output.
