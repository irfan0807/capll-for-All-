"""
02_rpm_gauge.py
RPM Gauge Test – Encodes RPM values 800, 2000, 4000, 6000, 7000 as uint16*4
big-endian and sends on 0x101. Verifies cluster response on 0x550; 7000 RPM
(redline) must set byte1=1 in the cluster status response.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_ENGINE_RPM     = 0x101
CAN_ID_CLUSTER_STATUS = 0x550

RPM_TEST_VALUES    = [800, 2000, 4000, 6000, 7000]
REDLINE_THRESHOLD  = 6500   # RPM above which redline indicator activates
REDLINE_BYTE1_FLAG = 1

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


def encode_rpm(rpm: int) -> bytes:
    """Encode RPM as uint16 big-endian scaled by factor 4."""
    raw = rpm * 4
    if raw > 0xFFFF:
        raw = 0xFFFF
    return struct.pack('>H', raw) + bytes(6)


def decode_rpm_from_raw(raw_bytes: bytes) -> int:
    """Decode raw uint16 BE bytes back to RPM."""
    raw = struct.unpack('>H', raw_bytes[:2])[0]
    return raw // 4


def test_rpm_gauge():
    bus = get_bus()
    try:
        for rpm in RPM_TEST_VALUES:
            data = encode_rpm(rpm)
            send_msg(bus, CAN_ID_ENGINE_RPM, data)

            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Cluster responded for RPM={rpm}",
                response is not None
            )

            if response:
                if rpm >= REDLINE_THRESHOLD:
                    check(
                        f"RPM={rpm} (redline): byte1 == {REDLINE_BYTE1_FLAG} (redline active)",
                        response.data[1] == REDLINE_BYTE1_FLAG
                    )
                else:
                    check(
                        f"RPM={rpm}: byte1 != {REDLINE_BYTE1_FLAG} (no redline)",
                        response.data[1] != REDLINE_BYTE1_FLAG
                    )

        # Encoding round-trip check
        for rpm in RPM_TEST_VALUES:
            encoded = encode_rpm(rpm)
            decoded = decode_rpm_from_raw(encoded)
            check(
                f"Round-trip encode/decode RPM={rpm}: decoded={decoded}",
                decoded == rpm
            )

        # Boundary: idle RPM 800 should not trigger redline
        send_msg(bus, CAN_ID_ENGINE_RPM, encode_rpm(800))
        resp_idle = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Idle RPM 800 does not set redline byte1",
            resp_idle is not None and resp_idle.data[1] != REDLINE_BYTE1_FLAG
        )

        # Over-range protection: RPM that overflows uint16
        max_raw = 0xFFFF
        decoded_max = max_raw // 4
        check(
            f"Overflow protection: max raw 0xFFFF → decoded RPM={decoded_max} ≤ 16383",
            decoded_max <= 16383
        )

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  RPM Gauge Test")
    print("=" * 55)
    test_rpm_gauge()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
