"""
27_service_interval_display.py
Service Interval Display Test – Sends service distance counter (10000 km) via
0x508 byte1-2 as uint16. Decrements to 500 km → service_soon flag. 0 km →
service_due_now flag. Reset byte clears counter.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_CLUSTER_DTC    = 0x508   # reused for service interval in byte1-2
CAN_ID_CLUSTER_STATUS = 0x550

SERVICE_SOON_KM     = 500
SERVICE_DUE_KM      = 0
SERVICE_SOON_BIT    = (1 << 4)   # bit4 in lampState
SERVICE_DUE_BIT     = (1 << 5)   # bit5 in lampState

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


def build_service_msg(remaining_km: int, reset: bool = False) -> bytes:
    """Build service interval message.
    byte0 = 0x00 (no DTC), byte1-2 = remaining_km uint16 BE, byte3 = reset flag.
    """
    km_bytes = struct.pack('>H', max(0, min(65535, remaining_km)))
    reset_byte = 0xFF if reset else 0x00
    return bytes([0x00]) + km_bytes + bytes([reset_byte]) + bytes(4)


def test_service_interval_display():
    bus = get_bus()
    try:
        # Step 1 – Full service interval (10000 km)
        send_msg(bus, CAN_ID_CLUSTER_DTC, build_service_msg(10000))
        resp_full = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Service interval=10000 km: cluster responded", resp_full is not None)
        if resp_full:
            check(
                f"10000 km: service_soon bit CLEAR (lampState=0x{resp_full.data[0]:02X})",
                not bool(resp_full.data[0] & SERVICE_SOON_BIT)
            )

        # Step 2 – Mid-interval (2500 km)
        send_msg(bus, CAN_ID_CLUSTER_DTC, build_service_msg(2500))
        resp_mid = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Service interval=2500 km: cluster responded", resp_mid is not None)

        # Step 3 – Service soon (500 km remaining)
        send_msg(bus, CAN_ID_CLUSTER_DTC, build_service_msg(500))
        resp_soon = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Service interval=500 km: cluster responded", resp_soon is not None)
        if resp_soon:
            check(
                f"500 km: service_soon bit SET (lampState=0x{resp_soon.data[0]:02X})",
                bool(resp_soon.data[0] & SERVICE_SOON_BIT)
            )

        # Step 4 – Service due now (0 km)
        send_msg(bus, CAN_ID_CLUSTER_DTC, build_service_msg(0))
        resp_due = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Service interval=0 km: cluster responded", resp_due is not None)
        if resp_due:
            check(
                f"0 km: service_due bit SET (lampState=0x{resp_due.data[0]:02X})",
                bool(resp_due.data[0] & SERVICE_DUE_BIT)
            )

        # Step 5 – Reset service counter
        send_msg(bus, CAN_ID_CLUSTER_DTC, build_service_msg(10000, reset=True))
        resp_reset = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Service reset (10000 km, reset=True): cluster responded",
              resp_reset is not None)
        if resp_reset:
            check(
                "After reset: service_due bit CLEARED",
                not bool(resp_reset.data[0] & SERVICE_DUE_BIT)
            )

        # Step 6 – Message encoding checks
        msg_10k = build_service_msg(10000)
        km_decoded = struct.unpack('>H', msg_10k[1:3])[0]
        check(f"10000 km encodes to uint16 BE and decodes back: {km_decoded}", km_decoded == 10000)
        check("Service message is 8 bytes", len(build_service_msg(5000)) == 8)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Service Interval Display Test")
    print("=" * 55)
    test_service_interval_display()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
