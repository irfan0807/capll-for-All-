# ADAS Python Automation Suite

## Overview
30 Python automation scripts for validating Advanced Driver Assistance Systems (ADAS) ECUs using `python-can`, `cantools`, and `pytest`. Covers FCW, AEB, ACC, LKA, LDW, BSD, RCTA, parking sensors, radar, camera fusion, DMS, and full E2E regression.

## Environment Setup
```bash
pip install python-can cantools pytest pytest-html
```

## CAN Interface Configuration
```python
import can
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan', bitrate=500000)
# or for virtual testing:
bus = can.interface.Bus(channel='vcan0', bustype='socketcan')
```

## Signal Reference

| CAN ID | Signal Name         | Encoding                                      |
|--------|---------------------|-----------------------------------------------|
| 0x200  | ADAS_FCW            | byte0=status(0=Off,1=Warn1,2=Warn2,3=Emerg)  |
| 0x201  | ADAS_AEB            | byte0=state(0=Off,1=Ready,2=Triggered)        |
| 0x202  | ADAS_ACC            | byte0=state; byte1-2=setSpeed*10; byte3=gap   |
| 0x203  | ADAS_LKA            | byte0=active; byte1=laneOffset(signed,cm)     |
| 0x204  | ADAS_LDW            | byte0=status(0=OK,1=LeftDep,2=RightDep)       |
| 0x205  | ADAS_BSD            | byte0=leftZone; byte1=rightZone               |
| 0x206  | ADAS_RCTA           | byte0=left; byte1=right                       |
| 0x207  | VehicleSpeed        | byte0-1 = speed*10 (uint16)                   |
| 0x208  | RadarTarget         | byte0-1=dist_cm; byte2=relVelocity; byte3=RCS |
| 0x209  | CameraLane          | byte0=quality; byte1=offset_signed; byte2=curvature |
| 0x210  | ADAS_DTC            | byte0=dtcCount; byte1-3=dtcCode               |
| 0x211  | ADAS_PowerMode      | byte0=mode(0=Sleep,1=Standby,2=Active)        |
| 0x212  | ADAS_SensorHealth   | byte0=radarOK; byte1=cameraOK; byte2=ultraOK  |
| 0x213  | ADAS_CalibStatus    | byte0=radar; byte1=camera; byte2=overall      |
| 0x214  | FrontObjectDist     | byte0-1=dist_cm; byte2=objectClass            |
| 0x215  | ADAS_Gateway        | byte0=routingStatus; byte1=latencyMs          |
| 0x250  | ADAS_ECU_Response   | byte0=ackCmd; byte1=result; byte2=data        |

## Suite Structure

| Script | Feature Under Test |
|--------|-------------------|
| 01_fcw_validation.py | FCW warning level thresholds & timing |
| 02_aeb_test.py | AEB trigger, braking response time |
| 03_acc_state_machine.py | ACC state transitions, set speed, gap |
| 04_lka_validation.py | Lane-keep torque, offset threshold |
| 05_ldw_test.py | Lane departure alert, indicator suppression |
| 06_bsd_validation.py | Blind spot zone entry/exit |
| 07_rcta_test.py | Rear cross-traffic detection, speed inhibit |
| 08_parking_sensor.py | Zone proximity stages 1–4 |
| 09_radar_target_sim.py | Radar object injection, RCS variation |
| 10_camera_fusion.py | Lane quality, offset fusion |
| 11_adas_can_monitor.py | Cycle time monitoring, bus error detection |
| 12_speed_limit_recognition.py | Sign recognition, overspeed logic |
| 13_pedestrian_detection.py | Pedestrian class object, AEB link |
| 14_dms_validation.py | Driver monitoring state & alert |
| 15_highway_pilot.py | Highway pilot engage/disengage sequence |
| 16_adas_dtc_management.py | DTC injection, UDS read, verify & clear |
| 17_sensor_calibration_check.py | Calibration byte validation |
| 18_adas_power_mode.py | Sleep/wake transitions |
| 19_adas_fault_injection.py | Sensor fault, degraded mode logic |
| 20_object_distance_monitor.py | Distance threshold alerts |
| 21_adas_gateway_routing.py | Routing latency check |
| 22_ncap_automation.py | Euro NCAP AEB pass/fail |
| 23_adas_logging.py | CSV/JSON trace data logging |
| 24_adas_wake_sleep.py | CAN wakeup pattern |
| 25_sensor_health_monitor.py | All sensor health bits |
| 26_adas_regression_suite.py | Sequential regression runner |
| 27_adas_uds_diagnostics.py | UDS 0x22/0x19 on ADAS ECU |
| 28_emergency_brake_light.py | EBL trigger check |
| 29_tsr_validation.py | Traffic sign recognition |
| 30_adas_e2e_test.py | Full ADAS lifecycle E2E test |

## Pass/Fail Criteria
- All timing checks report delta_ms vs threshold
- PASS: assertion passes without exception
- FAIL: `AssertionError` or `TimeoutError` caught and logged
- HTML report generated via `pytest --html=report.html`

## Running
```bash
pytest adas_python_suite/ -v --html=adas_report.html
```
