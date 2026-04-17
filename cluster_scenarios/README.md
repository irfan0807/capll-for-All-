# ADAS Cluster Scenario Questions

## Overview

This folder contains **scenario-based interview questions** on three distinct meanings of "Cluster" in ADAS engineering:

| # | File | Domain | Questions |
|---|------|--------|-----------|
| 1 | [01_vehicle_cluster_scenarios.md](01_vehicle_cluster_scenarios.md) | **Vehicle Cluster** — Groups of vehicles traveling together; how ACC, BSD, AEB, FCW handle convoy/cluster dynamics | Q1 – Q15 |
| 2 | [02_sensor_clustering_algorithm.md](02_sensor_clustering_algorithm.md) | **Sensor/Radar Clustering Algorithm** — How radar/LiDAR raw detections are clustered into tracked objects | Q16 – Q30 |
| 3 | [03_instrument_cluster_hmi.md](03_instrument_cluster_hmi.md) | **Instrument Cluster / HMI** — Dashboard display, ADAS warning icons, driver feedback, HMI state machine | Q31 – Q45 |

---

## Cluster Domain Map

```
ADAS "Cluster" — Three Meanings
│
├── 1. Vehicle Cluster (Traffic)
│      └── A group of vehicles close together on the road
│          - How does ACC handle a convoy ahead?
│          - How does BSD handle 5 cars in the blind spot simultaneously?
│          - How does AEB prioritize in a chain-braking cluster?
│
├── 2. Sensor Clustering (Signal Processing)
│      └── Raw radar/LiDAR detections → grouped into a single tracked object
│          - DBSCAN, grid-based, distance-threshold clustering
│          - Cluster split/merge during dynamic scenes
│          - Ghost clusters from multi-path reflections
│
└── 3. Instrument Cluster (HMI)
       └── The driver's dashboard screen and warning indicators
           - ADAS status icons and their behavior
           - Warning escalation sequences
           - Failure-mode display requirements
```

---

## Standards Referenced

- **ISO 15623** — Forward vehicle interval warning systems
- **ISO 26262** — Functional Safety
- **ISO 21448 (SOTIF)** — Safety of the Intended Functionality
- **Euro NCAP** — ADAS HMI evaluation criteria
- **EU GSR 2022** — ISA, LKA, BSD, DMS HMI mandates
- **SAE J2802** — Blind Spot Monitoring System Performance
- **UNECE R48** — Lighting and signalling (instrument cluster requirements)
- **ISO 15008** — Ergonomic requirements for in-vehicle visual systems

---

*Total Questions: 45 | Level: Intermediate to Advanced*
