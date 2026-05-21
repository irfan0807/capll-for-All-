# 33 — Functional Safety for AI-Based ADAS (ISO 26262 + SOTIF)

## Overview
Applying ISO 26262 (hardware/software functional safety) and ISO 21448 SOTIF (intended functionality safety) to AI perception and decision systems in ADAS. Covers ASIL decomposition, uncertainty quantification, and ODD management.

---

## 1. ISO 26262 vs SOTIF (ISO 21448)

| Standard | Covers | AI Relevance |
|---------|--------|-------------|
| ISO 26262 | Random hardware failures, systematic software faults | ECU hardware diagnostics, SW lifecycle, FMEA |
| SOTIF (ISO 21448) | Foreseeable misuse, intended function limitations | AI model ODD limits, sensor degradation, corner cases |
| ISO 5083 (draft) | AI/ML safety specifically | Data quality, model drift, uncertainty estimation |

**Key distinction:** A perception miss that causes AEB not to fire is a SOTIF issue (model performance limit), not an ISO 26262 issue (no hardware failed).

---

## 2. ASIL Levels for ADAS Functions

| ADAS Function | ASIL | Rationale |
|-------------|------|---------|
| AEB brake actuator | ASIL-B | Direct injury prevention |
| Pedestrian detection | ASIL-A | Input to ASIL-B system |
| Lane centering steering | ASIL-B | Steering torque — injury risk |
| ACC speed control | QM/ASIL-A | Low speed, comfort feature |
| DMS driver monitoring | ASIL-A | Alert function, not direct control |
| AD L3 trajectory output | ASIL-B/C | High-speed control, automated |

---

## 3. AI-Specific Safety Challenges

```
Standard Software Safety Issue:        AI Safety Issue:
   Code bug → deterministic fault          Model weakness → probabilistic failure
   FMEA covers all branches                No exhaustive test for all inputs
   Unit test 100% branch coverage          Coverage metric undefined
   Static analysis (MISRA)                 Neural network not statically analysable
```

---

## 4. Uncertainty Quantification (UQ)

AI models should output not just predictions but **uncertainty estimates**:

```python
import numpy as np

def mc_dropout_uncertainty(model, input_tensor, n_samples: int = 50):
    """Monte Carlo Dropout: estimate prediction uncertainty.
    Run N forward passes with dropout ACTIVE (eval mode, but dropout ON).
    
    High variance across passes = high uncertainty = reduced confidence in output."""
    predictions = []
    for _ in range(n_samples):
        pred = model(input_tensor)   # Dropout active → different per pass
        predictions.append(pred.detach().numpy())
    
    preds = np.stack(predictions, axis=0)  # (N, B, C)
    mean  = preds.mean(axis=0)             # (B, C)
    std   = preds.std(axis=0)              # (B, C) — uncertainty
    
    return mean, std

def is_in_distribution(uncertainty_std: float,
                         threshold: float = 0.15) -> bool:
    """Determine if input is within training distribution.
    If not → flag perception as unreliable, escalate to driver."""
    return uncertainty_std < threshold
```

---

## 5. ODD (Operational Design Domain)

SOTIF requires explicit ODD definition for every ADAS function:

```yaml
# Example ODD for Highway Pilot (L3)
name: Highway Pilot
oad_type: [highway, motorway]
speed_range_kph: [60, 130]
weather: [clear, light_rain, light_snow]
lighting: [day, night_with_streetlights]
lane_markings: [solid_white, dashed_white, solid_yellow]
max_lane_curvature: 0.005   # 1/m — no tight ramps
country: [DE, AT, CH, NL, BE, FR, IT, ES]

# ODD Exit Triggers:
exit_triggers:
  - speed_outside_range
  - heavy_rain_detected
  - roadworks_sign
  - no_lane_markings_300m
  - mountain_pass_detected
  - non_highway_road_type
```

---

## 6. Safety Monitor Architecture (Runtime)

```python
class AdasSafetyMonitor:
    """Runtime safety supervision for AI perception.
    Monitors: sensor health, model confidence, ODD compliance.
    
    SOTIF-relevant: flags performance degradation before it causes harm."""
    
    def __init__(self, conf_threshold: float = 0.6,
                  min_lane_conf: float = 0.7):
        self._conf_threshold  = conf_threshold
        self._min_lane_conf   = min_lane_conf
        self._rain_detected   = False
        self._camera_healthy  = True
        self._radar_healthy   = True
    
    def update_sensor_health(self, camera_ok: bool, radar_ok: bool):
        self._camera_healthy = camera_ok
        self._radar_healthy  = radar_ok
    
    def check_perception_quality(self,
                                   mean_detection_conf: float,
                                   lane_confidence: float,
                                   current_speed_kph: float) -> str:
        """Check if ADAS can operate safely.
        
        Returns: 'nominal', 'degraded', 'unavailable'"""
        
        if not self._camera_healthy and not self._radar_healthy:
            return 'unavailable'
        
        if mean_detection_conf < self._conf_threshold * 0.8:
            return 'degraded'    # High uncertainty — limit ADAS
        
        if lane_confidence < self._min_lane_conf and current_speed_kph > 100:
            return 'degraded'
        
        if self._rain_detected and not self._radar_healthy:
            return 'degraded'    # Rain + no radar → camera-only, reduced confidence
        
        return 'nominal'
    
    def evaluate_odd_compliance(self, speed_kph: float,
                                   road_type: str,
                                   lane_markings_visible: bool) -> bool:
        """Check if current conditions are within ODD."""
        if road_type not in ('highway', 'motorway'):
            return False
        if not (60 <= speed_kph <= 130):
            return False
        if not lane_markings_visible:
            return False
        return True
```

---

## 7. V&V for AI Systems (Verification and Validation)

| Phase | Activity | SOTIF Requirement |
|-------|---------|-----------------|
| Design | Hazard analysis, HARA on AI failures | Identify triggering conditions |
| Training | Dataset quality audit, bias analysis | Cover ODD scenarios |
| Test | Scenario-based testing (simulation) | Known unsafe scenarios resolved |
| Integration | HIL testing on ECU | Performance within ODD |
| Validation | Road testing, fleet data | Residual risk acceptable |
| Production | Monitoring, OTA safety updates | Continuous improvement |

---

## 8. Interview Q&A

### L1
**Q: What is the difference between ISO 26262 and SOTIF and why are both needed for ADAS?**  
A: ISO 26262 covers random hardware failures (sensor fails, ECU CPU error) and systematic software bugs — addressed by hardware redundancy, E2E protection, watchdogs, and deterministic software lifecycle (code reviews, MISRA). SOTIF covers "the system works as designed but the design is insufficient for the situation" — e.g., ADAS camera cannot detect pedestrian in heavy fog because camera performance was not specified for fog. SOTIF requires ODD definition, scenario testing, and performance monitoring. Both needed: ISO 26262 prevents the system from failing randomly; SOTIF prevents the system from performing correctly but causing harm due to design limits.

### L2
**Q: How do you test a neural network to satisfy ISO 26262 ASIL-B requirements?**  
A: ISO 26262 Part 6 requires: (1) Unit testing — test network at function level (preprocessing, postprocessing layers); (2) Integration testing — test inference pipeline end-to-end; (3) Back-to-back testing — compare production model against verified golden reference model; (4) MC/DC coverage — not applicable to neural networks; ISO 26262 supplements allow "requirements-based testing" instead; (5) Data-driven testing: curated test dataset covering all ASIL-relevant scenarios (pedestrian at 80kph night, cyclist with parked cars); (6) Independence: test engineer separate from training team; (7) Configuration management: model version hash stored in ECU, traceable to training dataset, test results, and safety analysis (FMEA). Note: full ASIL-D NN is not currently achievable — ASIL-B requires ASIL decomposition into multiple simpler components.

### L3
**Q: An ADAS feature fails to detect a pedestrian in a snowy/blizzard condition, resulting in an accident. Walk through a complete SOTIF-based root cause analysis.**  
A: (1) Triggering condition: heavy snow → camera image dominated by white noise, low contrast. Not a hardware failure — camera is functioning. (2) SOTIF: Clause 8 — this is a "hazardous situation due to performance limitation of the intended functionality." (3) ODD review: was heavy snow in the ODD? If yes → SOTIF violation (should have been detected in scenario testing). If no → was ODD clearly communicated to driver? ODD exit condition must display warning. (4) Scenario analysis: test dataset — what percentage of training images contain snow? If <5% → model under-trained for snow. Action: augment dataset, retrain, validate. (5) Sensor fusion gap: was radar also operating? Camera+radar fusion should detect pedestrian even with degraded camera. Was radar path healthy? (6) Fallback function: when camera confidence drops below threshold → AEB should fall back to radar-only mode; if radar had detected the pedestrian, AEB should have triggered regardless of camera. (7) Safety concept update: add "snow/weather detection" algorithm → if detected → increase radar weight in fusion, reduce set speed, issue driver alert. (8) Long-term: V2X pedestrian-worn device (eMBB) as additional input in severe weather.
