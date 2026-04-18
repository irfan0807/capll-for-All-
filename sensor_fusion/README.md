# Sensor Fusion — Study Repository
## Automotive Validation | April 2026

---

## What Is In This Folder

| File | Content |
|------|---------|
| `01_complete_guide.md` | Full theory: what sensor fusion is, algorithms, architectures, math |
| `02_star_scenarios.md` | 10 STAR-format interview scenarios (Situation → Task → Action → Result) |
| `03_realtime_scenarios.md` | 15 real-world debugging/validation scenarios with investigation paths |
| `04_capl_examples.md` | CAPL scripts for sensor fusion testing in CANoe |

---

## Quick Definition (memorise this)

> **Sensor fusion** is the process of combining data from multiple sensors to produce a more accurate, reliable, and complete picture of the environment than any single sensor could provide alone.

---

## The Three Sensor Types in Automotive ADAS

| Sensor | Strength | Weakness |
|--------|----------|---------|
| **Radar** | Range, velocity, works in rain/fog/dark | No visual detail, poor lateral resolution |
| **Camera** | Object classification, lane marking, colour | No depth, fails in glare/fog/night |
| **LiDAR** | Precise 3D point cloud, exact geometry | Expensive, affected by rain/dust |

No single sensor solves all problems. **Fusion combines all three.**

---

## Folder Structure

```
sensor_fusion/
  README.md                    ← this file
  01_complete_guide.md         ← theory + algorithms + architecture
  02_star_scenarios.md         ← 10 STAR interview answers
  03_realtime_scenarios.md     ← 15 debugging scenarios with CAPL
  04_capl_examples.md          ← standalone CAPL test scripts
```

---
*Repository: shaikirfandev/capll | April 2026*
