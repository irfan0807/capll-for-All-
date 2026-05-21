# 26 — Lane Keeping Assist (LKA) AI

## Overview
LKA detects unintentional lane departures and applies corrective steering. Covers lane detection → lateral state estimation → PID/MPC controller → ISO 11270 compliance.

---

## 1. LKA Variants

| System | Capability | Standards |
|--------|----------|---------|
| LDW (Lane Departure Warning) | Warning only, no correction | ISO 17361 |
| LKA (Lane Keeping Assist) | Gentle steering correction | ISO 11270 |
| LCA (Lane Centering Assist) | Continuous lane centering | UNECE R79 |
| ELC (Emergency Lane Keeping) | Prevents off-road crash | Euro NCAP 2025 |

---

## 2. Lateral Error Model (Bicycle Model)

For small steering angles and constant speed $v$:

$$\dot{e}_{lat} = v \cdot \psi_{err}$$
$$\dot{\psi}_{err} = \frac{v}{L} \delta + v \cdot \kappa_{road}$$

Where:
- $e_{lat}$ = lateral error from lane centre (m)
- $\psi_{err}$ = heading error vs lane tangent (rad)
- $L$ = wheelbase (m)
- $\delta$ = steering angle (rad) — control input
- $\kappa_{road}$ = road curvature (1/m) — feedforward term

---

## 3. PD Control with Curvature Feedforward

$$\delta_{cmd} = K_p \cdot e_{lat} + K_d \cdot \dot{e}_{lat} + K_{ff} \cdot \arctan(L \cdot \kappa)$$

Curvature feedforward eliminates steady-state error on curves — vehicle must steer even when $e_{lat} = 0$ if road is curving.

---

## 4. MPC Formulation

Minimise over horizon N:
$$J = \sum_{k=0}^{N-1} \left( e_{lat,k}^2 \cdot q_1 + \psi_{err,k}^2 \cdot q_2 + \delta_k^2 \cdot r \right)$$

Subject to: $|δ_k| \leq 8°$

Advantages of MPC over PID:
- Naturally handles constraints (max steering angle)
- Previews road curvature ahead (if HD map provides it)
- Guarantees stability over horizon

---

## 5. ISO 11270 — LKA Requirements

| Parameter | Requirement |
|-----------|------------|
| Speed range | 65-200 kph |
| Lateral correction limit | ≤ 3 Nm additional steering torque |
| Driver override capability | Any steering input > 2 Nm overrides |
| Hands-off timer | ≤ 15s without warning |
| Lane marking requirement | Solid or dashed lines both sides |
| Deactivation | Turn signal input → LKA suspended for 7s |

---

## 6. Lane Confidence Degradation Handling

```python
FALLBACK_STRATEGY = {
    'both_lanes_detected':   'lka_active',       # Full LKA
    'only_left_detected':    'lka_active_low_gain',  # 50% gain
    'only_right_detected':   'lka_active_low_gain',
    'no_lanes_detected':     'lka_monitoring',   # No correction
    'confidence_below_0.5':  'lka_monitoring'
}
```

---

## 7. Interview Q&A

### L1
**Q: What is the difference between LDW, LKA, and LCA?**  
A: LDW (Lane Departure Warning): detects when vehicle is about to cross lane marking, issues visual/audio/haptic warning to driver — no steering correction. LKA (Lane Keeping Assist): applies gentle corrective steering torque to keep vehicle from crossing lane boundary — activates only at departure, not continuous. LCA (Lane Centering Assist): continuously steers vehicle to maintain lane centre — actively used for long highway drives (Tesla Autopilot uses this continuously). ISO 11270 covers LKA; LCA is covered by UNECE R79 which sets tighter requirements.

### L2
**Q: How does LKA handle a curve — does it need more than lateral error feedback?**  
A: Yes — PD feedback alone has steady-state error on curves because the vehicle must maintain a steering angle even at lane centre. This requires curvature feedforward: δ_ff = arctan(L × κ_road). Sources of curvature estimate: (1) camera lane polynomial (2nd order coefficient gives curvature directly); (2) HD map: pre-stored curvature for each road segment, updated per GPS position; (3) yaw rate / speed: κ = ω/v (from IMU). Production systems use HD map as primary feedforward + camera refinement. Without feedforward: 0.3-0.5m steady-state error on 100m radius curve (unacceptable for L2+).

### L3
**Q: Design an Emergency Lane Keeping (ELK) system that prevents unintentional road departure at 120kph.**  
A: (1) Trigger conditions: vehicle approaching edge of road surface (not just lane marking) + no turn signal + no driver override. Use road edge detection from camera segmentation + radar guardrail detection. (2) Response: 3-stage escalation: stage 1 (0.5m to edge) → LKA correction + visual warning; stage 2 (0.25m) → maximum LKA torque (8 Nm) + audio alarm; stage 3 (0.1m or prediction: crossing in < 0.3s) → integrated brake intervention (one-sided braking creates yaw moment). (3) At 120kph, time available from 0.5m to crossing at 2m/s lateral drift: 0.25s — system must detect and respond within 100ms. (4) Override: > 5 Nm driver torque always overrides (Euro NCAP ELK requirement). (5) False activation prevention: dual confirmation from camera + radar; road edge confidence > 0.9; turn signal active → suspend for 10s.

---

## Files
- [lka_ai.py](lka_ai.py) — LKAPIDController, LKAMPCController, LKASystem state machine
