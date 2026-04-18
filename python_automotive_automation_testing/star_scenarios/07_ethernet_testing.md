# Python Automotive Testing – Automotive Ethernet (100BASE-T1 / SOME/IP / DoIP)
## STAR Format Scenarios (Situation → Task → Action → Result)

---

## Overview

Automotive Ethernet (IEEE 100BASE-T1, BroadR-Reach) is used for high-bandwidth applications: camera streams, radar data, OTA, diagnostics over IP (DoIP), and SOME/IP service discovery. Testing covers network connectivity, DoIP routing, SOME/IP service availability, latency, and bandwidth.

**Python Tools Used:**
- `scapy` — Custom Ethernet/IP packet crafting
- `doipclient` — DoIP (ISO 13400) client library
- `socket` + `struct` — TCP/UDP SOME/IP messaging
- `speedtest-cli` / `iperf3` — Bandwidth measurement
- `pytest` — Test framework

---

## STAR Scenario 1 – DoIP Routing Activation and UDS over Ethernet

### Situation
A high-voltage battery management ECU (BMS) was migrated from CAN diagnostics to DoIP (ISO 13400) over Automotive Ethernet. The test team needed to validate DoIP routing activation, confirm UDS sessions worked over TCP, and verify the ECU responded correctly to `0x10 03` (extendedDiagnostic session).

### Task
Automate DoIP routing activation handshake, send UDS `DiagnosticSessionControl` (0x10 03) over TCP, and validate the positive response. Test invalid logical address rejection (NRC 0x10 routingActivationDenied).

### Action
```python
import socket
import struct
import time

# DoIP constants (ISO 13400)
DOIP_VERSION        = 0x02
DOIP_ROUTING_ACT_REQ        = 0x0005
DOIP_ROUTING_ACT_RESP       = 0x0006
DOIP_UDS_MSG                = 0x8001
DOIP_UDS_RESP               = 0x8001

TARGET_ECU_LOGICAL_ADDR     = 0x0E80   # BMS ECU
TESTER_LOGICAL_ADDR         = 0x0E00

BMS_IP   = "192.168.10.20"
BMS_PORT = 13400

def build_doip_header(payload_type, payload):
    length = len(payload)
    return struct.pack(">BBHI", DOIP_VERSION, (~DOIP_VERSION) & 0xFF, payload_type, length) + payload

def build_routing_activation(src_addr, activation_type=0x00):
    return struct.pack(">HBxxxxxx", src_addr, activation_type)

def build_uds_request(src, target, uds_data: bytes):
    return struct.pack(">HH", src, target) + uds_data

def parse_doip_response(data):
    ver, inv_ver, ptype, length = struct.unpack_from(">BBHI", data, 0)
    payload = data[8:8+length]
    return ptype, payload

def test_doip_routing_and_uds():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((BMS_IP, BMS_PORT))

    # Step 1: Send Routing Activation Request
    ra_payload = build_routing_activation(TESTER_LOGICAL_ADDR)
    ra_msg     = build_doip_header(DOIP_ROUTING_ACT_REQ, ra_payload)
    sock.send(ra_msg)

    resp = sock.recv(4096)
    ptype, payload = parse_doip_response(resp)
    assert ptype == DOIP_ROUTING_ACT_RESP, f"Expected routing activation response, got 0x{ptype:04X}"
    routing_result = payload[2]  # Response code
    assert routing_result == 0x10, f"Routing activation failed: code=0x{routing_result:02X}"
    print(f"  Routing Activation: PASS (code=0x{routing_result:02X})")

    # Step 2: Send UDS DiagnosticSessionControl 0x10 03 (extendedDiagnostic)
    uds_data   = bytes([0x10, 0x03])
    uds_payload = build_uds_request(TESTER_LOGICAL_ADDR, TARGET_ECU_LOGICAL_ADDR, uds_data)
    uds_msg    = build_doip_header(DOIP_UDS_MSG, uds_payload)
    sock.send(uds_msg)

    resp2 = sock.recv(4096)
    ptype2, payload2 = parse_doip_response(resp2)
    # UDS payload starts at byte 4 (after src+target logical addr)
    uds_resp = payload2[4:]
    print(f"  UDS Response: {uds_resp.hex()}")

    assert uds_resp[0] == 0x50, f"Expected positive response 0x50, got 0x{uds_resp[0]:02X}"
    assert uds_resp[1] == 0x03, f"Expected echo of session 0x03, got 0x{uds_resp[1]:02X}"
    print("  UDS DiagnosticSessionControl ExtendedDiag: PASS")

    sock.close()

def test_doip_invalid_logical_address():
    """Routing activation with an unregistered source address should be denied."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((BMS_IP, BMS_PORT))

    ra_payload = build_routing_activation(0xDEAD)   # Unregistered address
    ra_msg     = build_doip_header(DOIP_ROUTING_ACT_REQ, ra_payload)
    sock.send(ra_msg)

    resp = sock.recv(4096)
    ptype, payload = parse_doip_response(resp)
    routing_result = payload[2]
    assert routing_result in (0x00, 0x01, 0x02), \
        f"Expected routing denied, got code=0x{routing_result:02X}"
    print(f"  Invalid address routing denial: PASS (code=0x{routing_result:02X})")
    sock.close()

if __name__ == "__main__":
    test_doip_routing_and_uds()
    test_doip_invalid_logical_address()
```

### Result
- Routing activation: PASS (code=0x10 — successfully activated) ✓
- UDS DiagnosticSessionControl: PASS ✓
- Invalid address: returned code=0x00 (denied) ✓
- Discovered: TCP connection remained open after test completion even when socket closed on tester side — BMS did not handle FIN/ACK properly
- Defect `BMS-067` – DoIP server does not close TCP session on client disconnect; resource leak under stress
- Fix: BMS added TCP keepalive + session timeout; 100-connection stress test showed no resource leak.

---

## STAR Scenario 2 – SOME/IP Service Discovery (SD) and Method Call

### Situation
A camera ECU (surround view) offers a `GetCameraFrame` service over SOME/IP. After a domain controller software update, the surround view camera service was not discovered by the HMI. The SOME/IP SD multicast was believed to be the issue.

### Task
Automate SOME/IP SD subscription to the camera service, validate service offer message received within 3 seconds, then call `GetCameraFrame` method and verify a valid response.

### Action
```python
import socket
import struct
import time

SOMEIP_SD_PORT       = 30490
SOMEIP_SD_MULTICAST  = "239.192.255.251"
SOMEIP_SERVICE_ID    = 0x0201   # Camera service
SOMEIP_METHOD_ID     = 0x0001   # GetCameraFrame
CAMERA_ECU_IP        = "192.168.20.30"
CAMERA_ECU_PORT      = 30501

def parse_someip_header(data):
    service_id, method_id, length = struct.unpack_from(">HHI", data, 0)
    client_id, session_id, proto_ver, iface_ver, msg_type, ret_code = struct.unpack_from(">HHBBBB", data, 8)
    payload = data[16:16 + length - 8]
    return {
        'service_id': service_id, 'method_id': method_id,
        'msg_type': msg_type, 'ret_code': ret_code, 'payload': payload
    }

def listen_for_sd_offer(timeout=5.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', SOMEIP_SD_PORT))
    # Join SOME/IP SD multicast group
    mreq = struct.pack("4sL", socket.inet_aton(SOMEIP_SD_MULTICAST), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(timeout)
    try:
        data, addr = sock.recvfrom(4096)
        hdr = parse_someip_header(data)
        sock.close()
        return hdr, addr
    except socket.timeout:
        sock.close()
        return None, None

def call_someip_method(service_id, method_id, payload=b''):
    """Send a SOME/IP method call (Request/Response)."""
    length = 8 + len(payload)
    header = struct.pack(">HHIHHBBBB",
        service_id, method_id, length,
        0x0001,  # client_id
        0x0001,  # session_id
        0x01,    # protocol version
        0x01,    # interface version
        0x00,    # message type: REQUEST
        0x00     # return code: E_OK
    )
    request = header + payload
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((CAMERA_ECU_IP, CAMERA_ECU_PORT))
    sock.send(request)
    resp = sock.recv(4096)
    sock.close()
    return parse_someip_header(resp)

def test_someip_service_discovery():
    print("Waiting for SOME/IP SD service offer...")
    hdr, addr = listen_for_sd_offer(timeout=5.0)
    assert hdr is not None, "SOME/IP SD: No service offer received within 5 seconds"
    print(f"  Service offer received from {addr[0]}: service=0x{hdr['service_id']:04X}")

def test_someip_method_call():
    test_someip_service_discovery()
    print("Calling GetCameraFrame method...")
    resp = call_someip_method(SOMEIP_SERVICE_ID, SOMEIP_METHOD_ID)
    assert resp['msg_type'] == 0x80, f"Expected RESPONSE (0x80), got 0x{resp['msg_type']:02X}"
    assert resp['ret_code'] == 0x00, f"SOME/IP error: ret_code=0x{resp['ret_code']:02X}"
    assert len(resp['payload']) > 0, "Camera frame payload is empty"
    print(f"  PASS: Camera frame received ({len(resp['payload'])} bytes)")

if __name__ == "__main__":
    test_someip_method_call()
```

### Result
- After domain controller update: SOME/IP SD offer not received (timeout) ✓ (confirmed bug)
- Root cause: IGMP multicast group rejoin not implemented after network interface reset
- Defect `CAM-211` – SOME/IP SD multicast not re-joined after ETH interface reset
- Fix: Added IGMP re-join on `ETH_LINK_UP` event
- Test passed within 0.8s service discovery time post-fix.

---

## STAR Scenario 3 – Ethernet Bandwidth and Latency Baseline

### Situation
A new SoC running the domain controller had automotive Ethernet 1000BASE-T1 (1Gbps). The integration team needed baseline latency and throughput measurements to validate QoS settings before deploying camera + radar + LiDAR streams simultaneously.

### Task
Measure round-trip latency (ICMP ping), TCP throughput (iperf3 Python binding), and UDP jitter between tester PC and domain controller.

### Action
```python
import subprocess
import json
import socket
import time
import statistics
import struct

DC_IP = "192.168.10.100"

def measure_icmp_latency(host, count=100):
    """Run ping and parse RTT statistics."""
    result = subprocess.run(
        ["ping", "-c", str(count), "-i", "0.01", host],
        capture_output=True, text=True
    )
    rtts = []
    for line in result.stdout.splitlines():
        if "time=" in line:
            rtt = float(line.split("time=")[1].split(" ")[0])
            rtts.append(rtt)
    return rtts

def measure_tcp_throughput():
    """Run iperf3 client and return Mbps."""
    result = subprocess.run(
        ["iperf3", "-c", DC_IP, "-t", "10", "-J"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    mbps = data['end']['sum_received']['bits_per_second'] / 1e6
    return mbps

def measure_udp_jitter(host, port=5005, packets=500, interval_ms=10):
    """Send UDP packets and measure inter-arrival jitter."""
    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_sock.bind(('', port + 1))
    rx_sock.settimeout(0.1)

    tx_timestamps = []
    rx_timestamps = []

    for seq in range(packets):
        ts = time.perf_counter()
        payload = struct.pack(">Id", seq, ts)
        tx_sock.sendto(payload, (host, port))
        tx_timestamps.append(ts)
        time.sleep(interval_ms / 1000.0)

    # Collect received packets
    rx_sock.settimeout(2.0)
    while True:
        try:
            data, _ = rx_sock.recvfrom(1024)
            rx_ts = time.perf_counter()
            rx_timestamps.append(rx_ts)
        except socket.timeout:
            break

    tx_sock.close()
    rx_sock.close()

    intervals = [rx_timestamps[i] - rx_timestamps[i-1] for i in range(1, len(rx_timestamps))]
    expected  = interval_ms / 1000.0
    jitter_ms = statistics.stdev([(x - expected)*1000 for x in intervals])
    return jitter_ms

def test_ethernet_baseline():
    print("Measuring ICMP latency (100 pings)...")
    rtts = measure_icmp_latency(DC_IP, count=100)
    assert rtts, "No ICMP responses"
    print(f"  Min: {min(rtts):.2f}ms  Max: {max(rtts):.2f}ms  Mean: {statistics.mean(rtts):.2f}ms")
    assert max(rtts) < 2.0, f"Max RTT {max(rtts):.2f}ms exceeds 2ms limit"

    print("Measuring TCP throughput (10s iperf3)...")
    mbps = measure_tcp_throughput()
    print(f"  Throughput: {mbps:.1f} Mbps")
    assert mbps >= 900, f"TCP throughput {mbps:.1f} Mbps below 900 Mbps threshold"

    print("Measuring UDP jitter...")
    jitter = measure_udp_jitter(DC_IP)
    print(f"  UDP Jitter: {jitter:.3f} ms")
    assert jitter < 0.5, f"UDP jitter {jitter:.3f}ms exceeds 0.5ms limit"

    print("PASS: Ethernet baseline within spec")

if __name__ == "__main__":
    test_ethernet_baseline()
```

### Result
- ICMP latency: min=0.18ms, max=0.63ms, mean=0.31ms ✓ (limit: 2ms)
- TCP throughput: 952 Mbps ✓ (limit: 900 Mbps)
- UDP jitter: 0.08ms ✓ (limit: 0.5ms)
- All baseline metrics within spec; results saved as release exit criteria for QoS sign-off.

---

## Summary Table

| Scenario | Protocol | Python Approach | Defect Found |
|---|---|---|---|
| 1 – DoIP routing + UDS | DoIP / TCP | Raw socket + struct packet builder | BMS TCP session not closed on FIN |
| 2 – SOME/IP SD + method call | SOME/IP / UDP | Multicast listener + TCP method call | IGMP re-join missing after reset |
| 3 – Bandwidth & latency | TCP/UDP/ICMP | ping + iperf3 + UDP jitter | Baseline documented for QoS sign-off |
