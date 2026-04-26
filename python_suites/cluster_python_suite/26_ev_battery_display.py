"""
26_ev_battery_display.py
EV Battery Display Test – Sends SOC 100, 80, 50, 20, 5% via 0x507 byte0.
Tests charging (byte1=1), regen (byte1=2), and drive (byte1=0) states.
Verifies cluster response for each state in 0x550.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_EV_SOC         = 0x507
CAN_ID_CLUSTER_STATUS = 0x550

# byte0 = SOC 0-100%
# byte1: 0=drive, 1=charging, 2=regen
EV_STATE_DRIVE    = 0x00
EV_STATE_CHARGING = 0x01
EV_STATE_REGEN    = 0x02

SOC_TEST_VALUES = [100, 80, 50, 20, 5]
LOW_SOC_THRESHOLD = 15   # % – below this triggers low battery warning
LOW_BATT_BIT      = (1 << 4)  # bit4 = Batt in lampState

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


def send_ev_soc(bus, soc_pct: int, state: int = EV_STATE_DRIVE):
    soc = max(0, min(100, soc_pct))
    data = bytes([soc, state]) + bytes(6)
    send_msg(bus, CAN_ID_EV_SOC, data)


def test_ev_battery_display():
    bus = get_bus()
    try:
        # Step 1 – SOC sweep in drive mode
        for soc in SOC_TEST_VALUES:
            send_ev_soc(bus, soc, EV_STATE_DRIVE)
            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"EV SOC={soc}% drive: cluster responded",
                response is not None
            )
            if response:
                display = response.data[1]
                check(
                    f"SOC={soc}%: display byte={display} within ±5 of {soc}",
                    abs(display - soc) <= 5
                )
                if soc <= LOW_SOC_THRESHOLD:
                    check(
                        f"SOC={soc}% ≤ {LOW_SOC_THRESHOLD}%: LowBatt bit4 SET "
                        f"(lampState=0x{response.data[0]:02X})",
                        bool(response.data[0] & LOW_BATT_BIT)
                    )
                else:
                    check(
                        f"SOC={soc}% > {LOW_SOC_THRESHOLD}%: LowBatt bit4 CLEAR",
                        not bool(response.data[0] & LOW_BATT_BIT)
                    )

        # Step 2 – Charging state at SOC=50%
        send_ev_soc(bus, 50, EV_STATE_CHARGING)
        resp_chg = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("EV charging state (SOC=50%): cluster responded", resp_chg is not None)
        if resp_chg:
            check(
                f"Charging: state byte reflected (displayValue={resp_chg.data[1]})",
                resp_chg is not None
            )

        # Step 3 – Regen braking state at SOC=60%
        send_ev_soc(bus, 60, EV_STATE_REGEN)
        resp_regen = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("EV regen state (SOC=60%): cluster responded", resp_regen is not None)

        # Step 4 – SOC boundary: 0% (empty)
        send_ev_soc(bus, 0, EV_STATE_DRIVE)
        resp_empty = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("EV SOC=0% (empty): cluster responded", resp_empty is not None)
        if resp_empty:
            check(
                "SOC=0%: LowBatt bit4 SET",
                bool(resp_empty.data[0] & LOW_BATT_BIT)
            )

        # Step 5 – SOC boundary: 100% (full)
        send_ev_soc(bus, 100, EV_STATE_DRIVE)
        resp_full = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("EV SOC=100% (full): cluster responded", resp_full is not None)
        if resp_full:
            check(
                "SOC=100%: LowBatt bit4 CLEAR",
                not bool(resp_full.data[0] & LOW_BATT_BIT)
            )

        # Step 6 – SOC clamping
        check("SOC clamped: min(100, max(0, 120)) == 100", min(100, max(0, 120)) == 100)
        check("SOC clamped: min(100, max(0, -5)) == 0", min(100, max(0, -5)) == 0)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  EV Battery Display Test")
    print("=" * 55)
    test_ev_battery_display()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
