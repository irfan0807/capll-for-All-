# Cluster Python Automation Suite

## Overview
30 Python automation scripts for validating Instrument Cluster ECUs using `python-can`, `cantools`, and `pytest`. Covers speedometer, RPM gauge, fuel, coolant temp, MIL, warning lamps, TPMS, EV SOC, odometer, self-test sequences, and full E2E regression.

## Environment Setup
```bash
pip install python-can cantools pytest pytest-html
```

## CAN Interface Configuration
```python
import can
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan', bitrate=500000)
```

## Signal Reference

| CAN ID | Signal Name       | Encoding                                                      |
|--------|-------------------|---------------------------------------------------------------|
| 0x100  | VehicleSpeed      | byte0-1 = speed*10 (uint16 big-endian)                       |
| 0x101  | EngineRPM         | byte0-1 = rpm*4 (uint16 big-endian)                          |
| 0x500  | FuelLevel         | byte0 = 0–255 mapped to 0–100%                               |
| 0x501  | CoolantTemp       | byte0 = temp + 40 (offset, °C)                               |
| 0x502  | GearPosition      | byte0: 0=P 1=R 2=N 3=D 4=M 5=S                              |
| 0x503  | OilPressure       | byte0-1 = kPa (uint16); 0xFFFF = sensor invalid              |
| 0x504  | ClusterPower      | byte0: 0=Sleep 1=Standby 2=On                                |
| 0x505  | WarningLamps      | byte0 bitmask: bit0=MIL,bit1=Oil,bit2=Belt,bit3=ParkBrake,bit4=Batt,bit5=Temp,bit6=Fuel,bit7=Tyre |
| 0x506  | TPMS_Status       | byte0=FL,byte1=FR,byte2=RL,byte3=RR (kPa); byte4=alertBitmask |
| 0x507  | EV_SOC            | byte0 = 0–100%                                               |
| 0x508  | Cluster_DTC       | byte0=dtcCount; byte1-3=dtcCode                              |
| 0x509  | Brightness        | byte0 = 0–255; 0xFE = AUTO                                   |
| 0x550  | ClusterStatus     | byte0=lampState; byte1=displayValue; byte2=faultStatus        |

## Suite Structure

| Script | Feature Under Test |
|--------|-------------------|
| 01_speedometer_accuracy.py | Speed 0→30→60→90→120→160 km/h, ±2% tolerance |
| 02_rpm_gauge.py | RPM sweep 800/2000/4000/6000/7000, redline detection |
| 03_fuel_gauge.py | Fuel 0/10/25/50/75/100%, low fuel warning <10% |
| 04_coolant_temp_gauge.py | Temp ramp 20°C→90°C→120°C, overheat >110°C |
| 05_mil_check_engine.py | DTC inject→MIL ON; DTC clear→MIL OFF |
| 06_warning_lamps.py | Bit-walk all 8 lamps, cluster response verify |
| 07_odometer_tripmeter.py | Trip A/B reset, daily distance accumulation |
| 08_trip_computer.py | Avg speed, fuel consumption, range display |
| 09_turn_signal_indicator.py | Left/right flash 120 BPM, hazard mode |
| 10_park_brake_indicator.py | Park brake set/release, lamp response |
| 11_oil_pressure_warning.py | Normal kPa, below threshold, sensor invalid |
| 12_seatbelt_reminder.py | Belt unfastened + speed >20 km/h → warning |
| 13_cluster_brightness.py | Dimmer 0/64/128/192/255, AUTO mode |
| 14_cluster_dtc.py | UDS 0x19 01 0F on 0x744→0x74C |
| 15_cluster_power_mode.py | IGN off→sleep, IGN on→wake timing |
| 16_cluster_can_monitor.py | Cycle time all signals, timeout detection |
| 17_gear_indicator.py | P/R/N/D/M/S, invalid byte fault |
| 18_range_display.py | Fuel rate × level = range, warn <50 km |
| 19_speed_limit_display.py | ISA sign injection, overspeed flag |
| 20_adas_icons_cluster.py | ACC/LKA/AEB/BSD bitmask → cluster icons |
| 21_door_ajar_display.py | Each door open, cluster animation bit |
| 22_tpms_display.py | All-OK → one tyre low 180 kPa → alert |
| 23_instrument_self_test.py | IGN ON: all lamps ON 3s then clear |
| 24_cluster_language.py | EN/DE/FR, km→miles, °C→°F |
| 25_cluster_animation.py | Welcome animation time <2s |
| 26_ev_battery_display.py | SOC 100→20→5%, charging/regen state |
| 27_service_interval_display.py | Service countdown, due-now, tech reset |
| 28_night_mode_cluster.py | Ambient → auto night; forced day/night |
| 29_cluster_regression.py | Sequential runner for all features |
| 30_cluster_e2e_test.py | IGN ON→self-test→drive→warnings→gears→OFF |

## Pass/Fail Criteria
- All timing checks report delta_ms vs threshold
- PASS: assertion passes without exception
- FAIL: `AssertionError` or `TimeoutError` caught and logged
- HTML report via `pytest --html=cluster_report.html`

## Running
```bash
pytest cluster_python_suite/ -v --html=cluster_report.html
```
