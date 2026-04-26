# Telematics Python Automation Suite

## Overview
30 Python automation scripts for validating Telematics Control Units (TCU) using `python-can`, `cantools`, and `pytest`. Covers TCU connectivity, GPS, remote services (lock/unlock/engine start), OTA, cellular RSSI, eCall, V2X, geo-fencing, power modes, and full E2E regression.

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

| CAN ID | Signal Name       | Encoding                                                          |
|--------|-------------------|-------------------------------------------------------------------|
| 0x600  | TCU_Status        | byte0: 0=Offline 1=Online 2=Connecting; byte1=signalQuality(0-100) |
| 0x601  | GPS_Validity      | byte0: 0=Invalid 1=Valid 2=Poor; byte1=satellites                 |
| 0x602  | GPS_Latitude      | byte0-3 = lat×1e6 (int32 big-endian)                              |
| 0x603  | GPS_Longitude     | byte0-3 = lon×1e6 (int32 big-endian)                              |
| 0x604  | RemoteCmd         | byte0: 0x01=Lock 0x02=Unlock 0x03=EngStart 0x04=EngStop 0x05=Horn 0x06=Lights; byte1=authToken |
| 0x605  | RemoteAck         | byte0=cmdEcho; byte1: 0=Idle 1=Processing 2=Done 3=Error; byte2=faultCode |
| 0x606  | OTA_Status        | byte0: 0=Idle 1=Downloading 2=Installing 3=Complete 4=Failed; byte1=progress(%) |
| 0x607  | Cellular_RSSI     | byte0=bars(0-5); byte1=tech(0=2G,1=3G,2=4G,3=5G); byte2=packetLoss(%) |
| 0x608  | eCall_Status      | byte0: 0=Idle 1=Activated 2=Sent 3=Connected 4=Completed; byte1=crashSeverity |
| 0x609  | TCU_PowerMode     | byte0: 0=Sleep 1=Standby 2=Active; byte1=wakeupReason             |
| 0x610  | V2X_BSM           | byte0=role(0=Off,1=Recv,2=TX); byte1=nearbyVehicles; byte2=hazardFlag |
| 0x611  | GeoFence_Event    | byte0: 0=Inside 1=Exit 2=Enter; byte1=fenceId; byte2=speedAtEvent |
| 0x650  | TCU_Response      | byte0=ackType; byte1=result; byte2=data                           |

## Suite Structure

| Script | Feature Under Test |
|--------|-------------------|
| 01_tcu_connection_status.py | TCU offline→connecting→online, timing <30s |
| 02_gps_fix_validation.py | GPS valid, sats ≥4, position plausibility |
| 03_remote_door_lock.py | Lock cmd 0x01, ACK done within 5s |
| 04_remote_door_unlock.py | Unlock cmd 0x02, duplicate protection |
| 05_remote_engine_start.py | Engine start + 10s timeout guard |
| 06_remote_engine_stop.py | Engine stop, dual auth token validation |
| 07_remote_horn_lights.py | Horn 0x05 then lights 0x06, sequential ACK |
| 08_ota_download_progress.py | OTA poll 0→50→100%, 120s timeout |
| 09_ota_install_verify.py | Post-download install, complete status |
| 10_ota_failure_recovery.py | Force fail via packetLoss=100%, rollback |
| 11_cellular_signal_quality.py | RSSI bars 0→5, 2G/3G/4G/5G handoff |
| 12_cellular_data_session.py | Data idle→active→idle, loss <5% |
| 13_ecall_trigger.py | Crash severity=200 → activated→sent→connected |
| 14_ecall_manual.py | Manual button press, same state sequence |
| 15_ecall_cancel.py | Cancel within 5s → idle |
| 16_v2x_receive_mode.py | V2X recv, vehicle count, no false hazard |
| 17_v2x_transmit_mode.py | TX BSM 100ms interval, neighbour seen |
| 18_v2x_hazard_broadcast.py | Hazard flag=1 broadcast, ack on 0x650 |
| 19_geofence_entry_event.py | fence_id=1 enter, alert and log |
| 20_geofence_exit_event.py | fence_id=1 exit, speed captured |
| 21_geofence_speed_alert.py | Exit at 90 km/h >80 limit, overspeed |
| 22_tcu_power_sleep_wake.py | IGN off→sleep, CAN wakeup→active |
| 23_tcu_standby_mode.py | Parking standby, heartbeat every 2s |
| 24_gps_position_accuracy.py | Lat/lon ±0.0001° tolerance |
| 25_gps_lost_recovery.py | GPS invalid 10s → recovery, DR flag |
| 26_remote_cmd_auth_fail.py | Wrong token → faultCode=0x01 |
| 27_remote_cmd_timeout.py | No ACK in 10s → retry → abort |
| 28_telematics_dtc_check.py | UDS 0x19 01 0F on 0x744→0x74C |
| 29_telematics_regression.py | Sequential regression all 6 areas |
| 30_telematics_e2e_test.py | Boot→GPS→Lock→OTA→eCall→Sleep |

## Pass/Fail Criteria
- All timing checks report delta_ms vs threshold
- PASS: assertion passes without exception
- FAIL: `AssertionError` or `TimeoutError` caught and logged
- HTML report via `pytest --html=telematics_report.html`

## Running
```bash
pytest telematics_python_suite/ -v --html=telematics_report.html
```
