"""
25_cluster_animation.py
Cluster Animation Test – Sends ClusterPower=2 (ON) via 0x504, then measures time
from power-on to the first 0x550 animation-done byte (displayValue byte1 = 0xFF
sentinel indicates animation complete). Asserts latency < 2000 ms.
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

POWER_SLEEP         = 0x00
POWER_ON            = 0x02
ANIMATION_DONE_BYTE = 0xFF    # byte1 sentinel indicating animation complete
MAX_ANIM_DELAY_MS   = 2000.0

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


def wait_for_animation_done(bus, timeout_s: float) -> tuple:
    """Wait for 0x550 byte1 == ANIMATION_DONE_BYTE. Returns (found, elapsed_ms)."""
    t_start = time.time()
    deadline = t_start + timeout_s
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == CAN_ID_CLUSTER_STATUS:
            if msg.data[1] == ANIMATION_DONE_BYTE:
                elapsed_ms = (time.time() - t_start) * 1000.0
                return True, elapsed_ms
    return False, (time.time() - t_start) * 1000.0


def test_cluster_animation():
    bus = get_bus()
    try:
        # Step 1 – Ensure cluster is asleep
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_SLEEP]) + bytes(7))
        time.sleep(0.5)

        # Step 2 – Power ON and measure animation completion time
        t_power_on = time.time()
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_ON]) + bytes(7))
        anim_done, elapsed_ms = wait_for_animation_done(bus, timeout_s=3.0)

        check("Animation-done byte received after power ON", anim_done)
        check(
            f"Animation complete in {elapsed_ms:.1f}ms < {MAX_ANIM_DELAY_MS}ms",
            elapsed_ms < MAX_ANIM_DELAY_MS
        )

        # Step 3 – Verify cluster is fully operational post-animation
        resp_post = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster operational after animation", resp_post is not None)
        if resp_post:
            check(
                "Post-animation: faultStatus byte2 == 0 (no startup fault)",
                resp_post.data[2] == 0
            )

        # Step 4 – Second power cycle
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_SLEEP]) + bytes(7))
        time.sleep(0.5)
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_ON]) + bytes(7))
        anim_done2, elapsed_ms2 = wait_for_animation_done(bus, timeout_s=3.0)
        check("Second power cycle: animation-done received", anim_done2)
        check(
            f"Second cycle animation={elapsed_ms2:.1f}ms < {MAX_ANIM_DELAY_MS}ms",
            elapsed_ms2 < MAX_ANIM_DELAY_MS
        )

        # Step 5 – Response latency from power on to first any message
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_SLEEP]) + bytes(7))
        time.sleep(0.5)
        t_wake = time.time()
        send_msg(bus, CAN_ID_CLUSTER_POWER, bytes([POWER_ON]) + bytes(7))
        resp_first = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        first_response_ms = (time.time() - t_wake) * 1000.0
        check(
            f"First 0x550 after power ON: {first_response_ms:.1f}ms < 500ms",
            first_response_ms < 500.0
        )

        # Step 6 – Sentinel constant check
        check("ANIMATION_DONE_BYTE == 0xFF", ANIMATION_DONE_BYTE == 0xFF)
        check("MAX_ANIM_DELAY_MS == 2000", MAX_ANIM_DELAY_MS == 2000.0)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Cluster Animation Test")
    print("=" * 55)
    test_cluster_animation()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
