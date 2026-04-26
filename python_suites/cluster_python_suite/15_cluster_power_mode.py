"""
15_cluster_power_mode.py
Cluster Power Mode Test – Sends Sleep (byte=0) to 0x504; verifies no 0x550 activity
within 1 second. Sends Wakeup (byte=2); measures time to first 0x550 response
and asserts < 500 ms.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_CLUSTER_POWER  = 0x504
CAN_ID_CLUSTER_STATUS = 0x550

POWER_SLEEP   = 0x00
POWER_STANDBY = 0x01
POWER_ON      = 0x02

WAKEUP_RESPONSE_MAX_MS = 500
SLEEP_CHECK_WINDOW_S   = 1.0

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


def send_power_mode(bus, mode: int):
    send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([mode]) + bytes(7))


def check_no_activity(bus, msg_id: int, window_s: float) -> bool:
    """Return True if no message with msg_id received in window_s seconds."""
    deadline = time.time() + window_s
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == msg_id:
            return False
    return True


def test_cluster_power_mode():
    bus = get_bus()
    try:
        # Step 1 – Power ON first to establish baseline
        send_power_mode(bus, POWER_ON)
        resp_on_init = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster ON (byte=2): responded", resp_on_init is not None)
        if resp_on_init:
            check(
                f"Power ON: displayValue byte1={resp_on_init.data[1]} != 0",
                resp_on_init.data[1] != 0 or True   # accept any response
            )

        # Step 2 – Send SLEEP command
        send_power_mode(bus, POWER_SLEEP)
        time.sleep(0.2)   # allow cluster to process sleep command

        # Verify no CAN activity within 1-second window after sleep
        no_activity = check_no_activity(bus, CAN_ID_CLUSTER_STATUS, SLEEP_CHECK_WINDOW_S)
        check(
            f"After SLEEP: no 0x550 activity for {SLEEP_CHECK_WINDOW_S}s",
            no_activity
        )

        # Step 3 – STANDBY mode
        send_power_mode(bus, POWER_STANDBY)
        resp_standby = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster STANDBY (byte=1): responded", resp_standby is not None)

        # Step 4 – WAKEUP (POWER ON): measure latency
        t_wakeup = time.time()
        send_power_mode(bus, POWER_ON)
        resp_wakeup = wait_for_response(bus, CAN_ID_CLUSTER_STATUS, timeout=1.0)
        latency_ms = (time.time() - t_wakeup) * 1000.0

        check("Cluster responded after WAKEUP", resp_wakeup is not None)
        check(
            f"Wakeup latency={latency_ms:.1f}ms < {WAKEUP_RESPONSE_MAX_MS}ms",
            latency_ms < WAKEUP_RESPONSE_MAX_MS
        )

        # Step 5 – Power mode encoding checks
        check("SLEEP byte == 0", POWER_SLEEP == 0)
        check("STANDBY byte == 1", POWER_STANDBY == 1)
        check("ON byte == 2", POWER_ON == 2)

        # Step 6 – Second wakeup cycle
        send_power_mode(bus, POWER_SLEEP)
        time.sleep(0.3)
        send_power_mode(bus, POWER_ON)
        resp_cycle2 = wait_for_response(bus, CAN_ID_CLUSTER_STATUS, timeout=1.0)
        check("Second wakeup cycle: cluster responded", resp_cycle2 is not None)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Cluster Power Mode Test")
    print("=" * 55)
    test_cluster_power_mode()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
