"""
21_adas_gateway_routing.py
ADAS Gateway Routing and Latency Test
- Send ADAS command via gateway
- Verify routing status byte and latency byte ≤ 10 ms
- Misrouted message → verify fault response
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_GATEWAY  = 0x215
ID_ECU_RESPONSE  = 0x250

ROUTING_OK    = 0x01
ROUTING_FAULT = 0x00
MAX_LATENCY_MS = 10

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


def send_gateway_cmd(bus, routing_status, latency_ms):
    send_msg(bus, ID_ADAS_GATEWAY,
             [routing_status, latency_ms & 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def step_normal_routing_ok(bus):
    send_gateway_cmd(bus, ROUTING_OK, latency_ms=5)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU response on normal routing", resp is not None)
    if resp:
        check("ECU routing status = OK", resp.data[0] == ROUTING_OK)


def step_latency_within_limit(bus):
    send_gateway_cmd(bus, ROUTING_OK, latency_ms=8)
    gw_msg = wait_for_response(bus, ID_ADAS_GATEWAY, timeout=1.5)
    if gw_msg:
        latency = gw_msg.data[1]
        check(f"Gateway latency {latency} ms ≤ {MAX_LATENCY_MS} ms",
              latency <= MAX_LATENCY_MS)


def step_latency_exceeds_limit(bus):
    send_gateway_cmd(bus, ROUTING_OK, latency_ms=15)   # over limit
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("ECU flags latency fault when > 10 ms",
              resp.data[2] == 0x01)


def step_misrouted_message_fault(bus):
    send_gateway_cmd(bus, ROUTING_FAULT, latency_ms=0)  # routingStatus=0x00 = fault
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU fault response on misrouted message",
          resp is not None and resp.data[1] != 0x01)


def step_gateway_recovery(bus):
    send_gateway_cmd(bus, ROUTING_OK, latency_ms=3)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Gateway recovers to normal routing",
          resp is not None and resp.data[0] == ROUTING_OK)


def step_multiple_commands_sequential(bus):
    for latency in [2, 5, 9, 10]:
        send_gateway_cmd(bus, ROUTING_OK, latency_ms=latency)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU handles multiple sequential gateway commands", resp is not None)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_gateway_routing(bus):
    step_normal_routing_ok(bus)
    step_latency_within_limit(bus)
    step_latency_exceeds_limit(bus)
    step_misrouted_message_fault(bus)
    step_gateway_recovery(bus)
    step_multiple_commands_sequential(bus)
    assert fail_count == 0, f"{fail_count} gateway routing checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_normal_routing_ok(b)
        step_latency_within_limit(b)
        step_latency_exceeds_limit(b)
        step_misrouted_message_fault(b)
        step_gateway_recovery(b)
        step_multiple_commands_sequential(b)
    finally:
        b.shutdown()
    print(f"\n=== Gateway Routing Summary: {pass_count} PASS / {fail_count} FAIL ===")
