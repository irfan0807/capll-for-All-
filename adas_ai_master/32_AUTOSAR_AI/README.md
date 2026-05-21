# 32 — AUTOSAR Adaptive for AI-Based ADAS

## Overview
AUTOSAR Adaptive (AP) R21-11 is the runtime framework for compute-intensive automotive ECUs running ADAS/AD workloads. Covers: Execution Management, Communication Management, Update & Config Management, and AI model lifecycle management.

---

## 1. AUTOSAR Classic vs Adaptive

| Feature | AUTOSAR Classic | AUTOSAR Adaptive |
|---------|---------------|----------------|
| OS | AUTOSAR OS (OSEK derivative) | POSIX (QNX, Linux) |
| Scheduling | Static (OSEK tasks) | Dynamic (POSIX processes) |
| Communication | COM/PDU, AUTOSAR COM | SOME/IP, DDS |
| Memory | Static allocation | Dynamic heap allowed |
| AI inference | Not suitable | Native support |
| Typical hardware | Microcontrollers (R5F, Cortex-M) | Cortex-A, GPU, DSP SoC |
| OTA | Batch DCM | UCM (Update & Config Mgmt) |

---

## 2. AP Service Architecture

```
Adaptive Application (AA)
     │
     │ ara::com (SOME/IP / binding)
     ▼
Service Interface (skeleton / proxy)
     │
Middleware (ara::com, ara::exec, ara::log, ara::diag)
     │
Adaptive Execution Management (AEM)
     │
POSIX OS (QNX Neutrino / AUTOSAR Linux)
     │
Hardware (Jetson Drive Orin, S32G, TDA4VM)
```

---

## 3. ARA (AUTOSAR Runtime for Adaptive Applications) Key APIs

```cpp
// ara::com — SOME/IP service communication
#include "ara/com/sample_ara_com_app.h"
#include "generated/radar_service_proxy.h"  // Generated from ARXML

// Subscribe to RadarService
auto proxy = radar::proxy::RadarServiceProxy::FindService(
    ara::com::InstanceIdentifier("RadarECU_1"));

proxy.Detections.Subscribe(10, [](auto& detections) {
    // Called when new radar detections arrive (SOME/IP event)
    for (const auto& d : detections.GetSample()) {
        process_detection(d);
    }
});
```

```cpp
// ara::exec — Application lifecycle
#include "ara/exec/application_client.h"

int main() {
    ara::exec::ApplicationClient app_client;
    
    // Notify EM that application has initialised successfully
    app_client.ReportApplicationState(
        ara::exec::ApplicationState::kRunning);
    
    // Main loop
    while (!shutdown_requested) {
        run_ai_inference_cycle();
    }
    
    app_client.ReportApplicationState(
        ara::exec::ApplicationState::kTerminating);
    return 0;
}
```

---

## 4. AI Model Update via UCM (Update & Config Management)

```
OEM Cloud ──────────────────────────────────────────────────────────────────┐
                                                                             │
  New YOLOv8 model binary (signed) ─► OTA download package (.vehupd)       │
                                                                             ▼
Vehicle UCM (Update Client)                                         ECU Partition B
  1. Receive download package                                      ──────────────
  2. Verify OEM signature (HSM public key)                        | Model v2.1  |
  3. Write to Partition B                                          ──────────────
  4. Request activation (AEM)
     └─ AEM: stop AI SWC, swap active partition, restart SWC
  5. Run self-test (inference on golden test vectors)
     └─ Pass → activate; Fail → rollback to Partition A + DTC
```

---

## 5. AI SWC (Software Component) Manifest

```xml
<!-- AUTOSAR Adaptive Manifest (simplified) -->
<ADAPTIVE-APPLICATION>
  <SHORT-NAME>AiDetectionSWC</SHORT-NAME>
  <EXECUTABLE>
    <SHORT-NAME>AiDetectionExe</SHORT-NAME>
    <PROCESS>
      <SHORT-NAME>AiDetectionProc</SHORT-NAME>
      <SCHEDULING-POLICY>FIFO</SCHEDULING-POLICY>
      <PRIORITY>60</PRIORITY>   <!-- POSIX RT priority -->
    </PROCESS>
  </EXECUTABLE>
  <REQUIRED-SERVICE-INSTANCE>
    <SHORT-NAME>CameraFeedProxy</SHORT-NAME>
    <SERVICE-INTERFACE>CameraServiceInterface/v1_0</SERVICE-INTERFACE>
  </REQUIRED-SERVICE-INSTANCE>
  <PROVIDED-SERVICE-INSTANCE>
    <SHORT-NAME>DetectionSkeleton</SHORT-NAME>
    <SERVICE-INTERFACE>DetectionServiceInterface/v1_0</SERVICE-INTERFACE>
  </PROVIDED-SERVICE-INSTANCE>
</ADAPTIVE-APPLICATION>
```

---

## 6. Health Monitoring in AP

```cpp
// ara::phm — Platform Health Management for AI SWC watchdog
#include "ara/phm/supervised_entity.h"

class AiInferenceHealthMonitor {
    ara::phm::SupervisedEntity entity_{"AiInference_SE"};
    
public:
    void report_alive() {
        // Must be called every inference cycle (20Hz = 50ms)
        // If missed for > 3 cycles → PHM triggers recovery action
        entity_.ReportCheckpoint(
            ara::phm::CheckpointId{1});  // Checkpoint 1: alive
    }
    
    void report_inference_complete() {
        entity_.ReportCheckpoint(
            ara::phm::CheckpointId{2});  // Checkpoint 2: result ready
    }
};
```

---

## 7. Interview Q&A

### L1
**Q: Why does L3+ ADAS use AUTOSAR Adaptive instead of Classic?**  
A: AUTOSAR Classic is designed for microcontrollers with static scheduling — it cannot manage dynamic AI workloads, POSIX threads, or large memory allocations needed for neural network inference. Classic ECUs run safety-critical control (ABS, airbag). AUTOSAR Adaptive runs on application-grade SoCs (Cortex-A72, GPU) with POSIX OS — supports dynamic processes, SOME/IP communication, OTA model updates, and service-oriented architecture. In practice: AEB brake actuator = Classic ECU (ASIL-D, deterministic); camera perception ECU = Adaptive ECU (ASIL-B, runs AI model).

### L2
**Q: How does AUTOSAR Adaptive handle OTA model updates without compromising safety?**  
A: UCM (Update and Configuration Management) orchestrates the update: (1) Signed package delivery — model binary signed by OEM CA; UCM verifies before installation; (2) A/B partitioning — model installed to inactive partition; no disruption to running inference; (3) Activation handshake — AEM (Execution Management) stops AI process, swaps active partition, restarts process; vehicle speed must be zero OR update deferred to next key-off; (4) Self-test: after restart, AI SWC runs inference on stored calibration vectors; passes if outputs match golden reference ±5%; (5) PHM (Platform Health Management) — if self-test fails → rollback to previous partition + log DTC; (6) Traceability: UCM logs model version hash, installation timestamp, and activation result in persistent storage.

### L3
**Q: Design the SOME/IP communication architecture for a multi-ECU ADAS perception stack.**  
A: (1) Camera ECUs (×4): each runs AUTOSAR Adaptive AP; provides `CameraDetectionService` (SOME/IP event at 30Hz); event data: Detection[] array (bounding boxes, class, confidence). (2) Radar ECU: provides `RadarTrackService` (20Hz); event data: Track[] (range, speed, angle, covariance). (3) Fusion ECU (domain controller): subscribes to Camera×4 + Radar events; temporal alignment (timestamps); runs EKF sensor fusion; provides `FusedPerceptionService` (30Hz). (4) Planning ECU: subscribes to FusedPerceptionService; produces trajectory (10Hz) → ActuatorService. (5) Service discovery: SOME/IP SD broadcast on Ethernet backbone (100BASE-T1 or 1000BASE-T1); each ECU advertises services at boot; consumers bind dynamically. (6) QoS: Camera detection events use UDP multicast (low latency, tolerable loss); Trajectory commands use TCP (reliable delivery). (7) Diagnostics: each SOME/IP message includes E2E profile 4 CRC + sequence counter; detected errors → DTC + error recovery (re-request service or fallback mode).
