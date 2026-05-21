# 27 — Automatic Emergency Braking (AEB)

## Overview
AEB automatically applies the brakes to prevent or mitigate collisions. Covers TTC computation, ASIL-B safety chain, Euro NCAP AEB test scenarios, and multi-sensor fusion for AEB decisions.

---

## 1. AEB Variants (Euro NCAP 2023)

| Variant | Target | Min Speed | Test Protocol |
|---------|--------|----------|--------------|
| AEB CCRs | Car-to-Car Rear Stationary | 10kph | GVT stationary target |
| AEB CCRm | Car-to-Car Rear Moving | 10kph | GVT moving at 20kph |
| AEB CCRb | Car-to-Car Rear Braking | 10kph | GVT brakes at 6 m/s² |
| AEB-PED_CPFA | Pedestrian Crossing Far Ahead | 10kph | TA dummy crossing |
| AEB-PED_CBNA | Pedestrian on dark background | 10kph | Night scenario |
| AEB-CYC_CPTA | Cyclist parallel | 10kph | Cycling dummy |

---

## 2. TTC (Time To Collision)

$$\text{TTC} = \frac{d}{|\dot{d}|} \quad \text{when } \dot{d} < 0$$

Where $d$ = range, $\dot{d}$ = range rate (negative = closing).

**Limitations of simple TTC:**
- Assumes constant velocity → underestimates risk if target is decelerating
- Extended TTC (eTTC) uses target deceleration:

$$\text{eTTC} = \frac{\dot{d} + \sqrt{\dot{d}^2 + 2 \cdot \Delta a \cdot d}}{\Delta a}$$

---

## 3. AEB Decision Thresholds

```
TTC > 2.7s   → MONITORING    (no action)
TTC = 2.7s   → WARNING       (visual + audio alert)
TTC = 2.0s   → PREFILL       (hydraulic line pressurised, no brake feel)
TTC = 1.6s   → PARTIAL BRAKE (0.3-0.5g)
TTC < 1.2s   → FULL BRAKE    (0.9g = 8.83 m/s²)
```

**Path overlap filter:** Only trigger if obstacle is in ego vehicle path.  
`overlap = clamp(ego_half_width + obj_half_width - lateral_distance, 0, 1)`

---

## 4. ASIL Decomposition

AEB is ASIL-B. Two independent paths reduce risk:

```
Radar path:  ASIL-A  ──┐
                        ├─► AND gate ──► Brake actuator (ASIL-B)
Camera path: ASIL-A  ──┘

Safety monitor (E2E protection, watchdog, brake plausibility)
```

**Single point failures (must be detected):**
- Radar failure → DTC, audio warning, AEB degraded
- Camera failure → DTC, AEB limited to radar-only mode (reduced TTC thresholds)
- Both failed → AEB unavailable + persistent warning

---

## 5. False Positive Prevention (Critical for Production)

| FP Scenario | Mitigation |
|------------|-----------|
| Overhead bridge | Camera detects no object on road; radar altitude filter |
| Parked car on roadside | Lateral overlap < 0.1 → no trigger |
| Manhole cover | Camera: not classified as obstacle; radar: no Doppler separation |
| Emergency brake of lead vehicle | Both radar + camera required for full brake trigger |
| Guardrail | Stationary clutter filter; no detection in high lateral zone |
| Rain/snow | Confidence gate: both sensors must agree (confidence > 0.7) |

---

## 6. Euro NCAP AEB Performance Score (2023)

```
Score = (Impact Speed Reduction ISR) / (Test Speed) × 100%

ISR = v_ego_at_impact_without_AEB - v_ego_at_impact_with_AEB

Full points: ISR ≥ 100% (collision avoided)
Partial: ISR = 50-99%
No points: ISR < 50%
```

**OEM target:** 5 stars requires AEB-PED score > 75% across all scenarios.

---

## 7. Interview Q&A

### L1
**Q: What is the difference between AEB warning, partial brake, and full brake phases?**  
A: AEB has a staged response ladder: (1) Warning phase (TTC~2.7s): acoustic tone + visual icon — alerts driver to brake voluntarily — most collisions avoidable by driver at this point. (2) Prefill phase (TTC~2.0s): hydraulic brake lines pressurised to remove dead time — driver steering/braking responsiveness improved — no deceleration perceived. (3) Partial brake (~1.6s): 0.3-0.5g deceleration — urges driver to take over — reduces impact energy if collision still occurs. (4) Full brake (<1.2s): 0.9g = max comfortable brake — collision avoidance attempt or severity mitigation — triggers even without driver input.

### L2
**Q: How does AEB distinguish between an overhead bridge and a real obstacle?**  
A: Multiple filter layers: (1) Camera semantic segmentation: classifies pixels as road/barrier/bridge structure — overhead bridge pixels are in 'structure' class not 'vehicle/pedestrian'; (2) Height estimation: radar + camera fusion estimates obstacle height above road; bridges are > 3m above road → filtered as non-collision objects; (3) LiDAR (if available): 3D bounding box height immediately distinguishes overhead structures; (4) Map-aided: HD map marks bridge locations — AEB suppressed in map-bridge zones; (5) Plausibility: if radar detects stationary object but camera shows no obstacle in road plane → radar clutter classification (no AEB). Production: multi-year tuning of bridge filter required — early AEB systems had significant false alarms on tunnels and bridges (notably Euro NCAP fail cases 2015-2018).

### L3
**Q: Design the ASIL-B safety chain for AEB from sensor to brake actuator.**  
A: (1) Sensor layer: radar (ASIL-A) + camera (ASIL-A) independently compute threat assessments; each implements end-to-end protection (E2E CRC on CAN messages). (2) AEB fusion ECU: receives radar + camera CAN messages; AND logic — both must agree for full brake (OR for partial brake); implements 1-out-of-2 voting; monitors E2E errors, timestamps, message counters. (3) Brake ECU (ESP): receives brake request; validates source (trusted SRC flag); watchdog timer resets brake to 0 if message lost > 100ms; implements brake pressure ramp (not step) to prevent wheel lock without ABS. (4) Diagnostics: PTT (Permanent Trigger Test) on startup — simulates ghost object, verifies brakes respond; sensor health DTCs logged to extended memory; FMEA verified for: radar stuck-at-zero, camera stuck frame, ECU processor fault (watchdog), CAN bus fault (E2E). (5) Limitations: AEB must never activate above 200kph (exceeds braking ability); must not activate when driver is braking harder than AEB threshold (driver-intent detection).

---

## Files
- [aeb_system.py](aeb_system.py) — AEBThreatAssessor, AEBSystem, TTC, path overlap, NCAP scenarios
