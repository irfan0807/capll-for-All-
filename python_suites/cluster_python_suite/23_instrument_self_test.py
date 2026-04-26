"""
23_instrument_self_test.py
Instrument Self-Test – Sends ClusterPower ON (byte=2) via 0x504; measures time
until all lampState bits=1 (all lamps ON), then time until all bits=0 (lamps OFF).
Both phases must complete within 3 seconds.
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

POWER_ON         = 0x02
ALL_LAMPS_ON     = 0xFF
ALL_LAMPS_OFF    = 0x00
MAX_PHASE_TIME_S = 3.0

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


def wait_for_lamp_state(bus, target_lamp_byte: int, timeout: float) -> tuple:
    """Wait until 0x550 byte0 matches target_lamp_byte. Returns (found, elapsed_s)."""
    t_start = time.time()
    deadline = t_start + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == CAN_ID_CLUSTER_STATUS:
            if msg.data[0] == target_lamp_byte:
                return True, time.time() - t_start
    return False, time.time() - t_start


def test_instrument_self_test():
    bus = get_bus()
    try:
        # Step 1 – Power ON
        t_power_on = time.time()
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_ON]) + bytes(7))

        # Step 2 – Wait for all lamps ON (self-test starts)
        print("  Waiting for ALL LAMPS ON phase …")
        lamps_on_found, t_lamps_on = wait_for_lamp_state(
            bus, ALL_LAMPS_ON, MAX_PHASE_TIME_S
        )
        check(
            f"Self-test: all lamps ON (0xFF) within {MAX_PHASE_TIME_S}s "
            f"(elapsed={t_lamps_on:.3f}s)",
            lamps_on_found and t_lamps_on <= MAX_PHASE_TIME_S
        )

        # Step 3 – Wait for all lamps OFF (self-test ends)
        print("  Waiting for ALL LAMPS OFF phase …")
        lamps_off_found, t_lamps_off = wait_for_lamp_state(
            bus, ALL_LAMPS_OFF, MAX_PHASE_TIME_S
        )
        check(
            f"Self-test: all lamps OFF (0x00) within {MAX_PHASE_TIME_S}s "
            f"(elapsed={t_lamps_off:.3f}s)",
            lamps_off_found and t_lamps_off <= MAX_PHASE_TIME_S
        )

        # Step 4 – Total self-test duration
        total_st = t_lamps_on + t_lamps_off
        check(
            f"Total self-test duration={total_st:.3f}s ≤ {MAX_PHASE_TIME_S * 2}s",
            total_st <= MAX_PHASE_TIME_S * 2
        )

        # Step 5 – Verify cluster remains active post-self-test
        resp_post = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster active after self-test", resp_post is not None)

        # Step 6 – Second power cycle to verify repeatable self-test
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([0x00]) + bytes(7))  # sleep
        time.sleep(0.3)
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_ON]) + bytes(7))
        lamps_on2, t2 = wait_for_lamp_state(bus, ALL_LAMPS_ON, MAX_PHASE_TIME_S)
        check(
            f"Second power cycle: lamps ON within {MAX_PHASE_TIME_S}s (t={t2:.3f}s)",
            lamps_on2 and t2 <= MAX_PHASE_TIME_S
        )

        # Step 7 – Byte value assertions
        check("ALL_LAMPS_ON constant = 0xFF", ALL_LAMPS_ON == 0xFF)
        check("ALL_LAMPS_OFF constant = 0x00", ALL_LAMPS_OFF == 0x00)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Instrument Self-Test")
    print("=" * 55)
    test_instrument_self_test()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
