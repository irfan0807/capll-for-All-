# UDS Diagnostics — Complete Study Material
## All UDS Services | STAR Scenarios: ADAS · Telematics · Cluster · Infotainment

---

## Folder Structure

| File | Description | Scenarios |
|------|-------------|-----------|
| [01_uds_complete_guide.md](01_uds_complete_guide.md) | All UDS services theory, frame formats, session types, error codes | Theory |
| [02_adas_star_scenarios.md](02_adas_star_scenarios.md) | 100 STAR scenarios — ADAS (AEB, ACC, LDW, BSD, Park Assist) | 100 |
| [03_telematics_star_scenarios.md](03_telematics_star_scenarios.md) | 100 STAR scenarios — Telematics (TCU, OTA, GPS, eCall, Remote) | 100 |
| [04_cluster_star_scenarios.md](04_cluster_star_scenarios.md) | 100 STAR scenarios — Instrument Cluster (speedo, warnings, NVM) | 100 |
| [05_infotainment_star_scenarios.md](05_infotainment_star_scenarios.md) | 100 STAR scenarios — Infotainment (HMI, audio, nav, BT, CarPlay) | 100 |

---

## UDS Quick Reference Card

```
Session Types:       01=Default  02=Programming  03=Extended  04=Safety
Security Access:     27 01 → seed  27 02 → key
Read DTC:            19 02 [status mask]   e.g. 19 02 09
Clear DTC:           14 FF FF FF
Read Data by ID:     22 [ID high] [ID low]
Write Data by ID:    2E [ID high] [ID low] [data]
ECU Reset:           11 01=hard  11 02=key-off  11 03=soft
Comm Control:        28 00=enable  28 01=disable non-diag
ECU Programming:     34 (RequestDownload) → 36 (TransferData) → 37 (TransferExit)
Routine Control:     31 01=start  31 02=stop  31 03=result
Tester Present:      3E 00 (suppress response: 3E 80)
DTC Status Byte:     bit0=testFailed  bit3=confirmed  bit5=testNotComplete
```

---

## Addresses Quick Reference

| ECU | Typical Request ID | Response ID |
|-----|--------------------|-------------|
| ADAS ECU | 0x7A0 | 0x7A8 |
| TCU (Telematics) | 0x7B0 | 0x7B8 |
| Instrument Cluster | 0x720 | 0x728 |
| Head Unit (HU) | 0x730 | 0x738 |
| Body Control (BCM) | 0x760 | 0x768 |
| Gateway | 0x600 | 0x608 |

---

*Total: 400+ real interview scenarios across 4 domains | April 2026*
