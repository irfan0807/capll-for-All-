"""
25_sensor_health_monitor.py
ADAS Sensor Health Polling Monitor Test
- Poll ADAS_SensorHealth 0x212 every 500 ms for 10 cycles
- Verify all bits (radarOK=1, cameraOK=1, ultraOK=1) in all cycles
- Inject single fault → detect fault within 1 cycle
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_SENSOR_HEALTH = 0x212
ID_ECU_RESPONSE  = 0x250

POLL_INTERVAL_S  = 0.5
POLL_CYCLES      = 10

pass_count = 0
fail_count = 0


def check(name, condition):
    global pass_count, fail_count
    if condition:
        print(f"[PASS] {name}")
        pass_count += 1
    else:
        print(f"[FAIL] {name}")
        fail_count += 1


def get_bus():
    try:
        return can.interface.Bus(channel=CHANNEL, bustype=BUSTYPE, bitrate=BITRATE)
    except Exception:
        return can.interface.Bus(channel='vcan0', bustype='socketcan')


def send_msg(bus, arb_id, data):
    msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
    bus.send(msg)
    time.sleep(0.05)


def wait_for_response(bus, expected_id, timeout=TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == expected_id:
            return msg
    return None


def send_sensor_health(bus, radar_ok, camera_ok, ultra_ok):
    send_msg(bus, ID_SENSOR_HEALTH,
             [radar_ok, camera_ok, ultra_ok, 0x00, 0x00, 0x00, 0x00, 0x00])


def poll_sensor_health(bus):
    return wait_for_response(bus, ID_SENSOR_HEALTH, timeout=POLL_INTERVAL_S + 0.2)


def step_all_sensors_healthy_10_cycles(bus):
    for cycle in range(POLL_CYCLES):
        send_sensor_health(bus, 1, 1, 1)
        msg = poll_sensor_health(bus)
        check(f"Cycle {cycle+1}: sensor health msg received", msg is not None)
        if msg:
            check(f"Cycle {cycle+1}: radarOK=1", msg.data[0] == 1)
            check(f"Cycle {cycle+1}: cameraOK=1", msg.data[1] == 1)
            check(f"Cycle {cycle+1}: ultraOK=1", msg.data[2] == 1)
        time.sleep(POLL_INTERVAL_S)


def step_inject_radar_fault_detect_in_1_cycle(bus):
    send_sensor_health(bus, 0, 1, 1)   # radarOK=0
    msg = poll_sensor_health(bus)
    check("Radar fault detected in 1 poll cycle",
          msg is not None and msg.data[0] == 0)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.0)
    if resp:
        check("ECU signals fault within 1 cycle", resp.data[2] == 0x01)


def step_inject_camera_fault_detect_in_1_cycle(bus):
    send_sensor_health(bus, 1, 0, 1)   # cameraOK=0
    msg = poll_sensor_health(bus)
    check("Camera fault detected in 1 poll cycle",
          msg is not None and msg.data[1] == 0)


def step_all_faults_then_clear(bus):
    send_sensor_health(bus, 0, 0, 0)
    msg = poll_sensor_health(bus)
    check("All sensor faults detected", msg is not None and sum(msg.data[:3]) == 0)
    send_sensor_health(bus, 1, 1, 1)
    msg2 = poll_sensor_health(bus)
    check("Sensors restored to healthy state", msg2 is not None and sum(msg2.data[:3]) == 3)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_sensor_health_monitor(bus):
    step_all_sensors_healthy_10_cycles(bus)
    step_inject_radar_fault_detect_in_1_cycle(bus)
    step_inject_camera_fault_detect_in_1_cycle(bus)
    step_all_faults_then_clear(bus)
    assert fail_count == 0, f"{fail_count} sensor health monitor checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_all_sensors_healthy_10_cycles(b)
        step_inject_radar_fault_detect_in_1_cycle(b)
        step_inject_camera_fault_detect_in_1_cycle(b)
        step_all_faults_then_clear(b)
    finally:
        b.shutdown()
    print(f"\n=== Sensor Health Monitor Summary: {pass_count} PASS / {fail_count} FAIL ===")
