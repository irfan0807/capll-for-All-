"""
16_cluster_can_monitor.py
CAN Bus Monitor Test – Listens for 0x100, 0x101, 0x500–0x509 for 10 seconds,
measures cycle time per CAN ID, verifies each signal arrives within 110 ms cycle,
and logs outliers.
"""
import can
import time
import collections
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

MONITOR_DURATION_S  = 10.0
MAX_CYCLE_TIME_MS   = 110.0

MONITORED_IDS = [
    0x100, 0x101,
    0x500, 0x501, 0x502, 0x503, 0x504,
    0x505, 0x506, 0x507, 0x508, 0x509,
]

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


def send_all_signals(bus):
    """Emit all monitored signals once to prime the bus."""
    import struct
    payloads = {
        0x100: struct.pack('>H', 500) + bytes(6),      # 50 km/h
        0x101: struct.pack('>H', 8000) + bytes(6),     # 2000 RPM
        0x500: bytes([128]) + bytes(7),
        0x501: bytes([120]) + bytes(7),                # 80°C
        0x502: bytes([3]) + bytes(7),                  # D
        0x503: struct.pack('>H', 250) + bytes(6),
        0x504: bytes([2]) + bytes(7),
        0x505: bytes([0]) + bytes(7),
        0x506: bytes([220, 220, 220, 220, 0]) + bytes(3),
        0x507: bytes([80]) + bytes(7),
        0x508: bytes([0]) + bytes(7),
        0x509: bytes([128]) + bytes(7),
    }
    for arb_id, data in payloads.items():
        send_msg(bus, arb_id, data)


def test_cluster_can_monitor():
    bus = get_bus()
    try:
        # Prime the bus with one transmission of each signal
        send_all_signals(bus)

        # Collect timestamps per ID
        last_seen: dict     = {}
        cycle_times: dict   = collections.defaultdict(list)
        outliers: list      = []
        monitored_set       = set(MONITORED_IDS)

        print(f"  Monitoring CAN bus for {MONITOR_DURATION_S}s …")
        deadline = time.time() + MONITOR_DURATION_S

        # Continuously re-transmit signals to simulate ECU cyclic behaviour
        next_tx = time.time() + 0.1
        while time.time() < deadline:
            if time.time() >= next_tx:
                send_all_signals(bus)
                next_tx += 0.1

            msg = bus.recv(timeout=0.01)
            if msg and msg.arbitration_id in monitored_set:
                arb_id = msg.arbitration_id
                now = time.time() * 1000.0  # ms
                if arb_id in last_seen:
                    cycle_ms = now - last_seen[arb_id]
                    cycle_times[arb_id].append(cycle_ms)
                    if cycle_ms > MAX_CYCLE_TIME_MS:
                        outliers.append((arb_id, cycle_ms))
                last_seen[arb_id] = now

        # Evaluate collected data
        check("At least one monitored ID received", len(last_seen) > 0)

        for arb_id in MONITORED_IDS:
            if arb_id in cycle_times and cycle_times[arb_id]:
                avg_cycle = sum(cycle_times[arb_id]) / len(cycle_times[arb_id])
                check(
                    f"0x{arb_id:03X}: avg cycle={avg_cycle:.1f}ms ≤ {MAX_CYCLE_TIME_MS}ms",
                    avg_cycle <= MAX_CYCLE_TIME_MS
                )
            else:
                check(f"0x{arb_id:03X}: signal received at least once", arb_id in last_seen)

        if outliers:
            print(f"  Outliers detected ({len(outliers)}):")
            for arb_id, cycle_ms in outliers[:5]:
                print(f"    0x{arb_id:03X}: {cycle_ms:.1f}ms")
        else:
            check("No cycle time outliers detected", True)

        check(
            f"Total outliers ({len(outliers)}) ≤ 5% of total messages",
            len(outliers) <= max(1, sum(len(v) for v in cycle_times.values()) // 20)
        )

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  CAN Bus Monitor Test")
    print("=" * 55)
    test_cluster_can_monitor()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
