# 09 — HIL Debugging

> **Skills**: Diagnosing overruns, signal tracing, XCP DAQ, task profiling, network debugging  
> **Tools**: ControlDesk, dSPACE Profiler, oscilloscope, Wireshark, Trace32  
> **Outcome**: Systematically debug any HIL failure — timing, signal, bus, or algorithm

---

## 1. The HIL Debugging Mindset

```
When a test fails on HIL, ask in order:
─────────────────────────────────────────────────────────────────
1. Is it a setup problem?   → Wiring, power, wrong .sdf loaded
2. Is it a timing problem?  → Overrun, jitter, wrong cycle time
3. Is it a signal problem?  → Wrong scaling, floating input, noise
4. Is it a bus problem?     → Missing CAN message, wrong baud rate
5. Is it an algorithm bug?  → Logic error in Simulink model/ECU SW
─────────────────────────────────────────────────────────────────
Always verify the physical layer before blaming the algorithm.
```

---

## 2. Overrun Analysis

An overrun is the #1 most common HIL issue:

### Step 1: Detect
```
ControlDesk variables to check:
  TaskInfo.BaseRate.OverrunCounter         → Total overruns since start
  TaskInfo.BaseRate.ExecutionTime_us       → Current step execution time
  TaskInfo.BaseRate.ExecutionTimeMax_us    → Worst case ever recorded
  TaskInfo.BaseRate.ExecutionTimeMean_us   → Average execution time

Alarm: ExecutionTime_us > 750 µs (for 1 ms base rate)
```

### Step 2: Locate
```
dSPACE Profiler → Task Execution Timeline:
─────────────────────────────────────────────────────────────────
t=0       t=0.5ms    t=1ms     t=1.5ms   t=2ms
  │─────────────────────│◄────────────overrun──────────►│
  │                     │                               │
  [CAN Rx ISR: 50µs]    [Algorithm: 680µs]  [DAC: 50µs]  Total=780µs

Profiler shows: which Simulink subsystem took longest
→ Identify the bottleneck block
─────────────────────────────────────────────────────────────────
```

### Step 3: Fix
```
Overrun fix strategies:
──────────────────────────────────────────────────────────────────
Cause                     Fix
──────────────────────────────────────────────────────────────────
Complex Simulink model    Move non-critical blocks to 10 ms task
Lookup table too large    Reduce table size or use polynomial fit
Matrix operations         Use fixed-point instead of floating-point
Too many DVA signals      Reduce logged quantities or lower sample rate
Memory cache cold         Add warm-up phase before measurement
CAN ISR overload          Reduce CAN message rate or use hardware filter
──────────────────────────────────────────────────────────────────
```

---

## 3. XCP DAQ — High-Speed Data Acquisition

XCP (Universal Measurement and Calibration Protocol) is used to measure and calibrate variables in a **running** real-time application without stopping it:

```
XCP over Ethernet (dSPACE SCALEXIO):
─────────────────────────────────────────────────────────────────
Host PC (ControlDesk)          DS6001 (Running Application)
─────────────────────────────────────────────────────────────────
GET_STATUS ───────────────────────────────────────────────────►
◄─────────────────────────────────────────────── STATUS_OK

SET_DAQ_PTR [list_id=0, odt=0] ──────────────────────────────►
◄──────────────────────────────────────────────── OK

WRITE_DAQ [addr=AEB.BrakeActive] ────────────────────────────►
◄──────────────────────────────────────────────── OK

START_STOP_DAQ [mode=START, cycle=1ms] ──────────────────────►
◄──────────────────────────────────────────────── OK

── DAQ packets stream at 1 kHz ────────────────────────────────
◄─ DAQ_DATA [AEB.BrakeActive=0.0] ─────────────────────────────
◄─ DAQ_DATA [AEB.BrakeActive=0.0] ─────────────────────────────
◄─ DAQ_DATA [AEB.BrakeActive=1.0] ← Brake fires! ──────────────
─────────────────────────────────────────────────────────────────
```

### XCP Calibration (Writing to ECU)
```python
# XCP calibration via ControlDesk Python API
# Change a calibration parameter live (without stopping ECU)

def calibrate_aeb_ttc_threshold(bench, new_threshold_s: float):
    """
    Change AEB TTC threshold on live ECU.
    Old value: 1.8 s → new value: new_threshold_s
    """
    current = bench.get_variable("ECU.AEB.TTC_Threshold")
    print(f"TTC threshold: {current:.2f} s → {new_threshold_s:.2f} s")

    bench.set_variable("ECU.AEB.TTC_Threshold", new_threshold_s)
    time.sleep(0.01)  # Allow propagation

    # Verify write
    readback = bench.get_variable("ECU.AEB.TTC_Threshold")
    if abs(readback - new_threshold_s) > 0.001:
        raise RuntimeError(f"Calibration write failed: readback={readback}")
    print("Calibration confirmed")
```

---

## 4. Signal Debugging

### Signal Tracing Checklist
```
Signal not reaching ECU:
─────────────────────────────────────────────────────────────
1. ControlDesk: Verify DS2211.AO.CH1.Value shows expected value
2. Oscilloscope: Probe ECU connector pin
   Mismatch → check wiring/connector
3. ControlDesk: Check DS2211.AO.CH1.Enable == 1
   If 0 → output driver disabled (look for fault injection active)
4. Multimeter: Check resistance of wire → high resistance = bad crimp
5. ConfigurationDesk: Verify channel mapping → correct physical channel?

Signal noisy / oscillating:
─────────────────────────────────────────────────────────────
1. Oscilloscope: Is noise 50 Hz? → Power supply interference
2. Is noise above 1 kHz? → Switching noise from DS2655 FPGA PWM
3. Is it quantization noise? → DAC resolution issue (use 16-bit)
4. Remove HIL: measure ECU pin in real car → if clean, HIL is noisy
5. Add RC filter: 100 Ω + 100 nF low-pass on HIL output
```

### Analog Loopback Test
```
Before testing ECU, verify HIL analog I/O is correct:

1. Connect DS2211 AO CH1 → DS2211 AI CH1 (loopback wire)
2. Set AO CH1 to known voltage: 2.500 V
3. Read AI CH1 value in ControlDesk
4. Expect: AI CH1 = 2.500 V ± 0.005 V (16-bit accuracy)
5. If fails → board fault or ADC calibration needed
```

---

## 5. CAN Bus Debugging

```
CAN debugging workflow:
─────────────────────────────────────────────────────────────────
Issue: ECU not responding to AEB brake command

Step 1: Verify CAN physical
  Oscilloscope on CANH/CANL:
  - Normal CAN signal: dominant 0 V, recessive 2.5 V
  - No signal → check termination (both ends need 120 Ω)
  - Stuck dominant → node in bus-off state

Step 2: Check DS1552 Tx
  ControlDesk: DS1552.CAN1.TxFrameCount → increasing?
  If 0 → restbus not sending → check DBC mapping

Step 3: Capture with CANalyzer or Wireshark (canif)
  Look for: error frames, wrong IDs, wrong baud rate

Step 4: Check ECU Rx counter
  ControlDesk: CAN_Rx.WheelSpeeds.RxCount → increasing?
  If not → ECU rejecting frames (check filter, ID match)

Step 5: Protocol decode
  ControlDesk: raw frame bytes → decode manually with DBC
─────────────────────────────────────────────────────────────────
```

### CAN Bus Error State Machine
```
CAN error states:
  Active   → TEC/REC < 128    Normal operation
  Warning  → TEC/REC > 96    Errors increasing, watch it
  Passive  → TEC/REC > 127   Node won't send error frames
  Bus-Off  → TEC > 255       Node disconnects, requires reset

Monitor in ControlDesk:
  DS1552.CAN1.TxErrorCounter   → TEC
  DS1552.CAN1.RxErrorCounter   → REC
  DS1552.CAN1.BusOffFlag       → 0/1
```

---

## 6. Ethernet Debugging on dSPACE

```
DoIP/SOME/IP debugging:
─────────────────────────────────────────────────────────────────
Tool: Wireshark with SOME/IP + DoIP dissector plugins

Capture setup:
  1. Configure port mirror on DS4330 (clone traffic to host PC)
  2. Wireshark → select SCALEXIO Ethernet interface
  3. Filter: "someip" or "doip"

Common issues:
─────────────────────────────────────────────────────────────────
Issue                         Symptom                  Fix
─────────────────────────────────────────────────────────────────
Wrong IP address              No connection             Check CDx IP config
gPTP offset > ±500 ns         Timestamping wrong        Check DS4330 gPTP config
SOME/IP SD timeout            Service not found         Check offer timing
Routing activation rejected   DoIP NRC 0x01             Check source address
VLAN mismatch                 No packets visible        Add VLAN tag in DS4330
─────────────────────────────────────────────────────────────────
```

---

## 7. Task Timing Analysis

```python
# Script to detect and log task timing anomalies during a test run
import time

def monitor_timing(bench, duration_s=30, period_ms=1.0):
    """
    Monitor HIL task timing for overruns and jitter.
    Reports statistics and any violation.
    """
    exec_times = []
    overrun_start = bench.get_variable("TaskInfo.BaseRate.OverrunCounter")

    t_start = time.time()
    while time.time() - t_start < duration_s:
        et = bench.get_variable("TaskInfo.BaseRate.ExecutionTime_us")
        exec_times.append(et)
        if et > period_ms * 1000 * 0.75:  # > 75% budget
            print(f"[WARN] Execution time {et:.0f} µs at t={time.time()-t_start:.2f}s")
        time.sleep(period_ms / 1000)

    overrun_end = bench.get_variable("TaskInfo.BaseRate.OverrunCounter")

    import statistics
    print(f"\n=== Task Timing Report ({duration_s}s) ===")
    print(f"  Mean exec time:  {statistics.mean(exec_times):.1f} µs")
    print(f"  Max exec time:   {max(exec_times):.1f} µs")
    print(f"  Stdev (jitter):  {statistics.stdev(exec_times):.1f} µs")
    print(f"  Budget (75%):    {period_ms * 1000 * 0.75:.0f} µs")
    print(f"  Overruns:        {overrun_end - overrun_start}")

    if overrun_end - overrun_start > 0:
        print("  *** OVERRUNS DETECTED — test results are INVALID ***")
```

---

## 8. Common Debugging Scenarios

| Symptom | First Check | Likely Cause |
|---------|------------|--------------|
| ECU not booting | KL15 signal present? | HIL not asserting ignition |
| AEB never fires | Radar distance signal correct? | Wrong sensor scaling |
| CAN Rx count = 0 | Baud rate match? | Wrong baud rate in ConfigurationDesk |
| All tests timeout | OverrunCounter > 0? | Model overrunning, bad timing |
| Sporadic failures | Jitter > 100 µs? | Background process stealing CPU |
| Signal oscillates | Shield grounded? | EMI from power supply |
| Wrong DTC stored | Restbus signals nominal? | Sensor out-of-range in BIST |
| HIL app crashes | Task stack overflow? | Recursive function in model |

---

## 9. Interview Q&A

**Q1: How do you debug a sporadic overrun on a dSPACE HIL system?**  
First, monitor `TaskInfo.BaseRate.ExecutionTimeMax_us` over a long run (30+ min) to confirm it's a real overrun. Then use dSPACE Profiler to get a task execution timeline showing which Simulink subsystem caused the spike. Common causes: lookup table cache miss on first call, CAN ISR burst, or a non-deterministic algorithm path. Fix by moving the heavy block to a slower task or replacing it with an FPGA implementation.

**Q2: What is XCP and how do you use it during HIL debugging?**  
XCP (Universal Measurement and Calibration Protocol) provides live read/write access to any variable in the running real-time application over Ethernet. In ControlDesk, you add variables to a DAQ list and they stream at the configured rate. For debugging, you can also write calibration parameters on-the-fly without rebuilding — for example, changing an AEB TTC threshold to reproduce a failure condition.

**Q3: A CAN signal from the ECU is missing. Walk me through your debugging steps.**  
1. Verify the DS1552 Rx counter for that CAN channel is zero (confirm no frames arriving). 2. Use an oscilloscope on CANH/CANL to check physical layer. 3. Verify baud rate matches between HIL and ECU. 4. Capture with CANalyzer/Wireshark to see if ECU is transmitting at all. 5. Check if ECU is in bus-off state (TEC > 255) due to an earlier error injection test. 6. If ECU is in safe state, check the restbus messages it needs before it starts transmitting.

**Q4: How do you verify that a DS2211 analog output is correctly reaching an ECU sensor pin?**  
Connect DS2211 AO → DS2211 AI (loopback) first to verify the board hardware is working. Then connect to the ECU and probe the pin with an oscilloscope. Compare the ControlDesk-displayed value with the scope measurement. Any difference indicates a wiring, connector, or impedance matching issue.

**Q5: What does it mean if a test passes in SIL but fails in HIL?**  
This indicates a timing-related or hardware-related discrepancy. Common causes: (1) The ECU has a slower CAN message cycle than the SIL assumed; (2) Real-world signal noise on analog inputs triggers edge cases not present in clean simulation; (3) The SIL model had no I/O latency, but HIL has 1–2 ms CAN cycle delay; (4) The generated ECU code has a bug not present in the Simulink model (SIL vs MIL mismatch). The SIL→HIL delta is always investigated with signal logging comparison.
