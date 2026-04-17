# Traffic Sign Recognition (TSR) — Scenario-Based Questions (Q61–Q70)

---

## Q61: TSR Speed Limit Recognition Accuracy — Multiple Sign Types

### Scenario
The camera-based TSR system reads a speed limit sign "50" correctly. 500 m later, a supplementary sign below says "except HGV" (Heavy Goods Vehicles). The ego vehicle is a passenger car. Should the 50 km/h limit apply to the ego vehicle?

### Expected Behavior
TSR must recognize not only the main sign but also supplementary signs. Since "except HGV" means the 50 km/h limit does NOT apply to passenger cars, TSR should either suppress the 50 km/h reading or qualify it as "not applicable to this vehicle."

### Detailed Explanation
- Speed limit signs vary by country: different shapes, supplementary panels, conditional signs.
- TSR classification requires multi-sign parsing: main sign + supplementary sign semantic interpretation.
- Vehicle type awareness: the TSR system must know the ego vehicle's class (M1 — passenger car, N2 — HGV, etc.) to apply correct sign exceptions.
- This requires a semantic reasoning layer beyond simple sign recognition.
- Without supplementary sign parsing, TSR would incorrectly suggest 50 km/h to the passenger car driver.
- Reference: Vienna Convention on Road Signs and Signals defines supplementary panel standards.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Temporary sign covering permanent sign | Camera must read whichever sign is topmost/visible |
| Sign partially damaged (number unclear, e.g. "8_" could be 80 or 80) | Low confidence → no speed displayed or parent map value used |
| Two speed limit signs contradicting (road works reducing limit only partially applied) | Conservative: use lower limit; display uncertainty indicator |
| Variable message sign showing different speed at different times | Real-time recognition required; map-based static speed only a fallback |
| Night-time, retroreflective sign at oblique angle | Camera angle of incidence must still read sign; test at ±45° approach angle |
| Sign in another language (cross-border EU driving) | Sign shape (circle, red border) is universal; numeric value read regardless of language |

### Validation Approach
- NCAP TSR test protocol with approved sign set
- Static recognition at distances 10–80 m
- Dynamic recognition at 80 km/h approach speed

### Acceptance Criteria
- Standard numeric speed limit sign recognition accuracy ≥ 97% under validated conditions
- Supplementary sign reduction (suppression logic) validated in ≥ 90% of applicable test cases

---

## Q62: TSR False Positive From Advertising Billboard With Speed-Like Numbers

### Scenario
A billboard advertisement shows "60" as part of a "60% OFF SALE" advert. The TSR system displays "60 km/h" on the cluster. The actual road limit is 100 km/h. This is a false positive.

### Expected Behavior
TSR should distinguish regulatory speed limit signs (circular, red border, white background) from advertisement boards, which do not conform to the standard sign template.

### Detailed Explanation
- Legitimate speed limit signs: circular, white background, red border, black numerals, standard size (Vienna Convention).
- Billboard: rectangular, various colors, branding elements, larger than standard signs, numbers in non-standard fonts.
- DNN-based TSR: trained to recognize sign shapes + context. Rectangular objects at non-standard mounting heights should not be classified as speed signs.
- Map-based fusion: if map indicates 100 km/h on this road segment, and camera detects "60" on a billboard, map context reduces confidence in camera reading.
- Geographic context: billboards are typically above or beside the road, not at sign post height.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Store sign shaped like a speed limit circle (round yellow sign with number) | Shape matches; context + location metadata must distinguish |
| Sticker of a speed limit put on a truck (non-regulatory, humorous) | Non-standard mounting; vehicle body, not post-mounted — filter on mounting context |
| School sports score display visible from road | Non-circular shape; filtered |
| Distance sign in similar color scheme (white circle with distance in km) | Must distinguish distance markers from speed markers |

### Acceptance Criteria
- False positive rate from non-regulatory signs: < 1 per 1,000 km of regular driving
- Map fusion reduces false display of billboard speeds in 100% of validated cases

---

## Q63: TSR Sign Persistence — End of Speed Limit Zone

### Scenario
The ego vehicle passes a "50 km/h" sign entering a village. 800 m later, the village ends and there is no explicit "end of restriction" sign. The TSR continues showing "50 km/h." Is this behavior correct?

### Expected Behavior
TSR should remove the 50 km/h display once the vehicle exits the restricted zone. Without an explicit "end" sign, TSR must use map data (zone boundary in HD/standard map) to determine when the limit expires.

### Detailed Explanation
- Some countries place explicit de-restriction signs (grey/white circle, or national speed limit sign).
- Some rely on the driver knowing the default speed limit at town end.
- TSR + map fusion: the map contains zone boundaries (town limits, school zones, etc.).
- When the vehicle exits the zone boundary in the map, TSR updates the displayed limit to the national/road-type default.
- Camera may also detect the "town exit" boundary sign (if present) and trigger limit update.
- Without map: TSR cannot resolve this scenario accurately — map integration is mandatory for zone-based persistence.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Map zone boundary incorrect (village expanded beyond map boundary) | Map is wrong; camera must find de-restriction sign |
| Intermittent 30 km/h zone inside a 50 km/h zone | Nested zones; push 30 km/h on entry, restore 50 km/h on zone exit |
| Temporary school zone (only active 7–9 AM, 3–5 PM) | Time-aware zone logic; map time-of-day attribute applied |
| Driver drives round-trip through same sign multiple times | Sign recognized each pass; speed updated each time |

### Acceptance Criteria
- Speed limit removed from display within 500 m of zone exit (with map data)
- Nested zone correctly restores outer zone limit on exit of inner zone

---

## Q64: TSR Recognition of No-Overtaking Signs

### Scenario
The vehicle is equipped with TSR that also recongizes no-overtaking signs. The driver uses the lane change indicator in a no-overtaking zone. Should the TSR system warn the driver?

### Expected Behavior
TSR should recognize and display the no-overtaking sign. If the driver activates the right indicator, an auditory/visual warning should advise that overtaking is prohibited.

### Detailed Explanation
- No overtaking signs: circular, two vehicles icon (black and red) or white/red circle with number.
- TSR extension: beyond speed limits; includes no-overtaking, stop, yield, one-way.
- Lane indicator + no-overtaking = warn. This is a Level 1 advisory function.
- The system cannot physically prevent lane changes but provides information.
- In some L2 systems: LCA (Lane Change Assist) can refuse to initiate lane change in mapped no-overtaking zones.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| No-overtaking sign visible on the right side (not standard left mounting) | Must read regardless of mounting side |
| No-overtaking of trucks only (red car + truck sign) | Passenger car exempt; no warning should fire for M1 vehicle |
| No overtaking based on time of day (supplementary panel) | Time-of-day logic required |
| Driver changes lane for a side road (not overtaking) | Indicator intent ambiguous; warning may be overly conservative |

### Acceptance Criteria
- No-overtaking sign detected with ≥ 95% accuracy at ≥ 50 m distance
- Driver warning issued within 1 s of indicator activation in no-overtaking zone

---

## Q65: TSR and Map Fusion — Conflict Resolution

### Scenario
TSR camera reads "130 km/h" on a motorway sign. The HD map for this segment says "110 km/h" (due to a recent permanent road works reduction). Which source should the ISA/ACC system trust?

### Expected Behavior
When camera and map conflict, a confidence-weighted fusion must resolve the discrepancy. In general:
- Camera: real-time, accurate for current conditions.
- Map: may be outdated, but provides context.
- Resolution: prefer camera when confidence ≥ threshold; prefer map when camera confidence is low. Display discrepancy indicator to driver.

### Detailed Explanation
- The map may lag behind physical sign changes if map data is not updated.
- Camera is real-time but can make mistakes (occlusion, distance, weather).
- Fusion algorithm:
  1. If camera confidence ≥ 85% AND sign is valid: use camera reading.
  2. If camera confidence < 50%: use map value.
  3. If camera and map disagree by > 30 km/h: display "!" indicator; use conservative (lower) value.
- OTA map updates are critical for frequently changed zones (road works).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Map is completely missing for a new road | Camera-only; no fusion possible; lower confidence |
| Camera reads sign correctly but map shows different limit | Fusion chooses camera if confidence high |
| Both map and camera are wrong (very rare but possible) | System cannot self-detect this; relies on driver authority and regular updates |

### Acceptance Criteria
- Fusion correctly resolves camera vs. map conflict in ≥ 95% of test cases with known ground truth
- Driver notified of discrepancy when camera and map differ by ≥ 20 km/h

---

## Q66: TSR in Tunnels and Low-Light Environments

### Scenario
The vehicle enters a long tunnel. Inside, speed limit signs (60 km/h) are mounted on the wall. The camera is adapting from outdoor brightness (60,000 lux) to tunnel brightness (200 lux). For the first 3 seconds inside the tunnel, TSR fails to read signs.

### Expected Behavior
TSR should recover from the tunnel brightness transition within 1–2 s using camera auto-exposure. During the transition, the current displayed speed limit should be held (not reset to zero).

### Detailed Explanation
- Camera auto-exposure adapts from outdoor to indoor brightness in 0.5–2 s depending on camera ISP.
- During this transition, image quality is poor (overexposed then quickly normalizing).
- TSR should not clear the last confirmed speed limit during temporary camera blind intervals.
- Limit persistence logic: hold last confirmed speed for up to 10 s during blind intervals.
- Tunnel entry sign (before the tunnel portal) should be read first while outdoor visibility is still good.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Tunnel exit: sudden bright sunlight | Opposite direction exposure transition; same persistence logic |
| Very long tunnel with multiple speed limit changes inside | Multiple sign reads in static tunnel lighting; standard recognition |
| Tunnel in a country using different sign format | Country-specific TSR model required |
| Tunnel smoke/haze (emergency): sign not visible | TSR holds last known limit; system may flag degraded sensing |

### Acceptance Criteria
- TSR reading maintained during brightness transition (no reset of displayed speed)
- Speed limit sign inside tunnel recognized within 2 s of camera stabilization

---

## Q67: TSR for Temporary Speed Signs (Construction Zone)

### Scenario
A motorway construction zone uses portable, battery-powered LED variable message signs showing "60 km/h." These signs are different in appearance from standard static signs. TSR should still recognize them.

### Expected Behavior
TSR must recognize both static and LED/variable message signs. LED signs may flicker at refresh rates conflicting with the camera frame rate, causing missed reads.

### Detailed Explanation
- LED variable message signs (VMS) typically refresh at 50–100 Hz.
- Camera frame rate 30–60 fps: if not synchronized, partial LED activation in one frame may cause misread.
- Modern LED panels typically have persistence that allows detection even at mismatched frame rates.
- TSR DNN must be trained on both static and LED-type sign images.
- Construction zone: orange/amber signs (some countries) vs. standard white/red signs.
- Map data: traffic management center updates map with temporary speed limits via DATEX II/C-ITS.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Portable sign slightly angled (wind moved it) | Detect sign at off-axis angle; test at ±30° |
| LED sign blank (displaying nothing) | No speed limit displayed; TSR detects no sign; holds next available sign value |
| Multiple LED signs showing different speeds in quick succession (zone transition) | Update displayed speed for each new sign read |
| Worker holding a "stop/slow" paddle sign | Detect stop/slow paddle (different from speed limit); flag for driver attention |

### Acceptance Criteria
- LED variable message signs recognized with ≥ 90% accuracy under normal lighting
- No systematic misread due to LED flicker at standard camera frame rates

---

## Q68: TSR Occlusion — Sign Blocked by Truck

### Scenario
A speed limit sign is partially blocked by a large truck making a delivery. Only 40% of the sign is visible around the truck's body. Can TSR still recognize the sign?

### Expected Behavior
TSR should attempt to recognize partially occluded signs. With 40% visible and the registration containing the key discriminating feature (the numeral), TSR may still succeed. If confidence is low, the last confirmed sign should be held.

### Detailed Explanation
- Partial occlusion is one of the hardest challenges for sign recognition.
- Deep learning models trained with augmented occlusion data handle this better.
- Key features: the numeral is the most important; if the numeral is in the visible 40%, recognition is feasible.
- Confidence thresholding: if partial recognition confidence < 70%, do not update; hold current value.
- Context from map: if map says the limit in this zone is "50," and partial recognition shows "5_" → confirm 50.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Sign visible for < 0.5 s before being blocked | Brief confident read possible at highway speeds; test at 120 km/h approach |
| Sign behind reflective wet lorry side: ghost image | Ghost / mirror image not a valid sign; confidence check prevents false update |
| Sign on gantry above lanes (partially obstructed by overhead beam) | Gantry signs often partially visible; TSR must handle gantry sign aspect ratios |

### Acceptance Criteria
- TSR successfully reads a speed sign with ≥ 50% visible area at ≥ 80% confidence
- No erroneous speed update from < 30% visible sign

---

## Q69: TSR Sign Transition During High-Speed Driving

### Scenario
At 180 km/h on an unrestricted Autobahn, the vehicle approaches an "80 km/h" zone sign at a toll plaza. The sign is first visible at 60 m. At 180 km/h (50 m/s), the vehicle reaches the sign in 1.2 s. Can TSR read and process the sign in time?

### Expected Behavior
TSR should read the sign at maximum available range (60 m) and immediately update the ISA display. At 50 m/s, 1.2 s is sufficient for camera image processing latency (< 200 ms) to capture and classify the sign.

### Detailed Explanation
- TSR processing latency: camera frame capture (33 ms) + ISP processing (16 ms) + DNN inference (30–50 ms) + CAN transmission (10 ms) = ~100 ms.
- At 50 m/s, the vehicle travels 5 m during this 100 ms = sign must be detectable from > 65 m.
- Camera recognition range for standard signs: 50–100 m depending on sign size and camera resolution.
- Large motorway signs are designed for legibility at speed; larger numerals → higher recognition range.
- Pre-sign warning: ADAS should issue a speed advisory ("reduce to 80 km/h") as soon as sign is read.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Dirty camera at 180 km/h: mud splatter from truck | Camera degraded; TSR range reduced; may miss sign |
| Sign visible only 30 m before threshold (obstacle blocking) | Insufficient time for practical driver action; warn urgently |
| Multiple signs in rapid succession (toll complex) | Process each sign frame; prioritize most recently detected |

### Acceptance Criteria
- TSR reads standard motorway speed sign from ≥ 60 m
- Processing latency from sign center-in-frame to HMI update: < 200 ms

---

## Q70: TSR System Integration With ACC Speed Cap

### Scenario
TSR detects a 90 km/h sign. ACC set speed is 110 km/h. With ISA-ACC integration active, ACC should cap at 90 km/h. However, the driver needs to overtake a cyclist safely and momentarily wishes to exceed 90 km/h. What happens?

### Expected Behavior
ACC ISA cap is a soft advisory, not a hard enforcement. The driver can override by pressing the accelerator beyond the ACC speed: this temporarily overrides the speed cap, allowing the overtake. On releasing the accelerator, ACC returns to 90 km/h.

### Detailed Explanation
- Regulation EU 2019/2144: ISA must be a non-overridable warning by default, but should allow driver override by "deliberate and sustained action."
- ISA-integrated ACC: driver accelerator override unlocks the speed cap temporarily.
- Override conditions: driver holds accelerator firmly for > 500 ms → override lasts for defined period OR until driver releases.
- After override: ACC returns to TSR-advised speed when driver eases off accelerator.
- This is critically important: ISA must NOT prevent genuine safety-motivated speed increases (emergency maneuvers, overtaking).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver bypasses ISA repeatedly (frequent speeder) | ISA provides escalating reminders; cannot permanently lock driver out |
| ISA speed cap set too conservatively (sign misread lower) | Driver override available; then correct TSR reading restores correct cap |
| Emergency acceleration (swerving from obstacle) | SOTIF defines this as legitimate override; no delay in override recognition |
| Speed limit changes to higher value ahead: TSR updates cap | ACC naturally allowed to increase back to set speed or new limit, whichever is lower |

### Acceptance Criteria
- ISA speed cap override acknowledged within 300 ms of deliberate accelerator input
- ACC returns to TSR cap within 5 s of driver releasing accelerator
- Override does not permanently deactivate ISA; reactivates for next speed zone
