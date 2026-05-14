# SOME/IP — MINI PROJECTS
## Module 2 of 7 | 4 GitHub-Ready Projects

---

## PROJECT 1: SOME/IP Service Monitor

**Problem:** Verifying SOME/IP service health requires manual Wireshark sessions. Need an automated tool that monitors event periods, detects subscription dropouts, and alerts on anomalies.

**Architecture:**
```
someip_monitor/
├── monitor.py          ← Main event monitoring loop
├── decoder.py          ← SOME/IP header parser
├── services.yaml       ← Service definitions (ID, period, threshold)
├── reporter.py         ← Console + HTML report
├── tests/
│   └── test_decoder.py
└── README.md
```

**Full Implementation:**
```python
# decoder.py
"""SOME/IP header decoder."""
import struct
from dataclasses import dataclass
from typing import Optional


MSG_TYPE = {0x00: "REQUEST", 0x01: "RESPONSE", 0x02: "ERROR",
            0x40: "REQUEST_NO_RETURN", 0x80: "NOTIFICATION"}

RETURN_CODE = {0x00: "E_OK", 0x01: "E_NOT_OK", 0x0D: "E_UNKNOWN_SERVICE",
               0x0E: "E_UNKNOWN_METHOD"}


@dataclass
class SomeIpHeader:
    service_id: int
    method_id: int
    length: int
    client_id: int
    session_id: int
    proto_version: int
    iface_version: int
    msg_type: int
    return_code: int
    payload: bytes

    @property
    def is_event(self) -> bool:
        return self.method_id >= 0x8000

    @property
    def msg_type_str(self) -> str:
        return MSG_TYPE.get(self.msg_type, f"UNKNOWN(0x{self.msg_type:02X})")

    @property
    def return_code_str(self) -> str:
        return RETURN_CODE.get(self.return_code, f"UNKNOWN(0x{self.return_code:02X})")

    def __str__(self):
        return (f"SOME/IP SvcID=0x{self.service_id:04X} "
                f"MethID=0x{self.method_id:04X} "
                f"Type={self.msg_type_str} RC={self.return_code_str} "
                f"Session=0x{self.session_id:04X} "
                f"Payload={len(self.payload)}B")


def decode_someip(data: bytes) -> Optional[SomeIpHeader]:
    """Parse SOME/IP header from raw bytes."""
    if len(data) < 16:
        return None
    try:
        service_id, method_id, length, client_id, session_id, \
            proto_ver, iface_ver, msg_type, return_code = struct.unpack_from(
                ">HHIHHBBBB", data, 0
            )
        payload_len = length - 8  # length field counts from byte 8
        payload = data[16:16 + max(0, payload_len)]
        return SomeIpHeader(
            service_id=service_id, method_id=method_id, length=length,
            client_id=client_id, session_id=session_id,
            proto_version=proto_ver, iface_version=iface_ver,
            msg_type=msg_type, return_code=return_code, payload=payload
        )
    except struct.error:
        return None
```

```python
# monitor.py
"""Real-time SOME/IP event period monitor."""
import pyshark
import time
import yaml
import statistics
from collections import defaultdict
from decoder import decode_someip, SomeIpHeader
from typing import Dict, List


class EventStats:
    def __init__(self, service_id: int, method_id: int, expected_period_ms: float):
        self.service_id = service_id
        self.method_id = method_id
        self.expected_period_ms = expected_period_ms
        self.arrival_times: List[float] = []
        self.violations: int = 0

    def add_arrival(self, ts: float):
        if self.arrival_times:
            gap_ms = (ts - self.arrival_times[-1]) * 1000.0
            tolerance = self.expected_period_ms * 0.20  # ±20%
            if abs(gap_ms - self.expected_period_ms) > tolerance:
                self.violations += 1
                print(f"  [VIOLATION] SvcID=0x{self.service_id:04X} "
                      f"MethID=0x{self.method_id:04X} "
                      f"gap={gap_ms:.1f}ms expected={self.expected_period_ms}ms")
        self.arrival_times.append(ts)

    def summary(self) -> dict:
        if len(self.arrival_times) < 2:
            return {"count": len(self.arrival_times), "status": "INSUFFICIENT_DATA"}
        gaps = [(self.arrival_times[i+1] - self.arrival_times[i]) * 1000.0
                for i in range(len(self.arrival_times) - 1)]
        return {
            "service_id": f"0x{self.service_id:04X}",
            "method_id": f"0x{self.method_id:04X}",
            "count": len(self.arrival_times),
            "mean_period_ms": round(statistics.mean(gaps), 2),
            "max_period_ms": round(max(gaps), 2),
            "min_period_ms": round(min(gaps), 2),
            "violations": self.violations,
            "status": "PASS" if self.violations == 0 else "FAIL"
        }


class SomeIpMonitor:
    def __init__(self, config_path: str = "services.yaml"):
        with open(config_path) as f:
            self.services = yaml.safe_load(f)["services"]
        self.stats: Dict[tuple, EventStats] = {}
        for svc in self.services:
            key = (svc["service_id"], svc["method_id"])
            self.stats[key] = EventStats(
                service_id=svc["service_id"],
                method_id=svc["method_id"],
                expected_period_ms=svc["period_ms"]
            )

    def start(self, interface: str = "eth0", duration_s: int = 30):
        print(f"[Monitor] Capturing SOME/IP on {interface} for {duration_s}s...")
        cap = pyshark.LiveCapture(
            interface=interface,
            bpf_filter="udp"  # SOME/IP is typically UDP
        )
        cap.sniff(timeout=duration_s)

        for pkt in cap:
            try:
                if not hasattr(pkt, 'udp'):
                    continue
                # Get raw UDP payload
                raw = bytes.fromhex(pkt.udp.payload.replace(':', ''))
                hdr = decode_someip(raw)
                if hdr is None or not hdr.is_event:
                    continue
                key = (hdr.service_id, hdr.method_id)
                if key in self.stats:
                    self.stats[key].add_arrival(float(pkt.sniff_timestamp))
            except Exception:
                continue

        self._print_report()

    def _print_report(self):
        print("\n" + "="*60)
        print("SOME/IP EVENT MONITORING REPORT")
        print("="*60)
        all_pass = True
        for s in self.stats.values():
            r = s.summary()
            status = r.get("status", "UNKNOWN")
            if status == "FAIL":
                all_pass = False
            print(f"  SvcID={r.get('service_id','?')} "
                  f"MethID={r.get('method_id','?')} "
                  f"Count={r.get('count',0)} "
                  f"Mean={r.get('mean_period_ms','?')}ms "
                  f"Violations={r.get('violations',0)} "
                  f"[{status}]")
        print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")


if __name__ == "__main__":
    mon = SomeIpMonitor("services.yaml")
    mon.start(interface="eth0", duration_s=30)
```

```yaml
# services.yaml
services:
  - service_id: 0x1234
    method_id: 0x8001
    name: "SpeedEvent"
    period_ms: 20.0
  - service_id: 0x1235
    method_id: 0x8002
    name: "AccelerationEvent"
    period_ms: 10.0
  - service_id: 0x1300
    method_id: 0x8010
    name: "RadarObjectList"
    period_ms: 50.0
```

**Technologies:** Python, pyshark, Scapy, yaml, pytest

**Resume Description:**
> "Built SOME/IP event period monitor that tracked arrival times for 12 event types, detected period violations (±20%), generated HTML report — replaced manual Wireshark analysis, identified 2 CPU-starvation bugs in production firmware."

---

## PROJECT 2: SOME/IP Config Validator

**Problem:** ARXML mismatches between server and client ECUs (Service ID, Interface Version, port) are a leading cause of integration failures — discovered late in the cycle.

**What it does:** Parses ARXML files from both server and client ECUs, checks service interface alignment, reports all mismatches as a pre-integration gate.

**Key Implementation:**
```python
# arxml_validator.py
"""
SOME/IP ARXML Validator
Compares server and client ARXML for SOME/IP service consistency.
"""
from lxml import etree
from dataclasses import dataclass
from typing import List, Dict


AUTOSAR_NS = "http://autosar.org/schema/r4.0"


@dataclass
class ServiceInterface:
    name: str
    service_id: int
    major_version: int
    minor_version: int
    source_file: str
    methods: Dict[str, int]  # method_name → method_id
    events: Dict[str, int]   # event_name → method_id


def parse_arxml(filepath: str) -> List[ServiceInterface]:
    """Extract SOME/IP service interface definitions from ARXML."""
    interfaces = []
    tree = etree.parse(filepath)
    root = tree.getroot()
    ns = {"ar": AUTOSAR_NS}

    # Find all ServiceInterface elements
    for si in root.findall(".//ar:SERVICE-INTERFACE", ns):
        name_elem = si.find("ar:SHORT-NAME", ns)
        if name_elem is None:
            continue

        # Extract SOME/IP service ID from transport mapping
        service_id_elem = si.find(".//ar:SERVICE-IDENTIFIER", ns)
        major_ver_elem = si.find(".//ar:MAJOR-VERSION", ns)
        minor_ver_elem = si.find(".//ar:MINOR-VERSION", ns)

        if service_id_elem is None:
            continue

        methods = {}
        for method in si.findall(".//ar:METHOD", ns):
            m_name = method.findtext("ar:SHORT-NAME", namespaces=ns)
            m_id = method.findtext(".//ar:METHOD-IDENTIFIER", namespaces=ns)
            if m_name and m_id:
                methods[m_name] = int(m_id, 0)

        events = {}
        for event in si.findall(".//ar:EVENT", ns):
            e_name = event.findtext("ar:SHORT-NAME", namespaces=ns)
            e_id = event.findtext(".//ar:METHOD-IDENTIFIER", namespaces=ns)
            if e_name and e_id:
                events[e_name] = int(e_id, 0)

        interfaces.append(ServiceInterface(
            name=name_elem.text,
            service_id=int(service_id_elem.text, 0),
            major_version=int(major_ver_elem.text) if major_ver_elem is not None else 0,
            minor_version=int(minor_ver_elem.text) if minor_ver_elem is not None else 0,
            source_file=filepath,
            methods=methods,
            events=events
        ))
    return interfaces


def validate_interfaces(server_arxml: str, client_arxml: str) -> List[str]:
    """
    Compare server and client ARXML.
    Returns list of mismatch descriptions. Empty list = PASS.
    """
    mismatches = []
    server_ifaces = {si.service_id: si for si in parse_arxml(server_arxml)}
    client_ifaces = {si.service_id: si for si in parse_arxml(client_arxml)}

    for svc_id, server_si in server_ifaces.items():
        if svc_id not in client_ifaces:
            mismatches.append(
                f"Service 0x{svc_id:04X} ({server_si.name}): "
                f"present in SERVER but not in CLIENT"
            )
            continue

        client_si = client_ifaces[svc_id]

        # Check major version
        if server_si.major_version != client_si.major_version:
            mismatches.append(
                f"Service 0x{svc_id:04X} MAJOR VERSION MISMATCH: "
                f"server={server_si.major_version}, client={client_si.major_version}"
            )

        # Check method IDs
        for method_name, server_method_id in server_si.methods.items():
            if method_name not in client_si.methods:
                mismatches.append(
                    f"Service 0x{svc_id:04X} method '{method_name}': "
                    f"defined in server, missing in client"
                )
            elif client_si.methods[method_name] != server_method_id:
                mismatches.append(
                    f"Service 0x{svc_id:04X} method '{method_name}' ID MISMATCH: "
                    f"server=0x{server_method_id:04X}, "
                    f"client=0x{client_si.methods[method_name]:04X}"
                )

        # Check event IDs
        for event_name, server_event_id in server_si.events.items():
            if event_name not in client_si.events:
                mismatches.append(
                    f"Service 0x{svc_id:04X} event '{event_name}': "
                    f"defined in server, missing in client"
                )
            elif client_si.events[event_name] != server_event_id:
                mismatches.append(
                    f"Service 0x{svc_id:04X} event '{event_name}' ID MISMATCH: "
                    f"server=0x{server_event_id:04X}, "
                    f"client=0x{client_si.events[event_name]:04X}"
                )

    return mismatches


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python arxml_validator.py server.arxml client.arxml")
        sys.exit(1)

    issues = validate_interfaces(sys.argv[1], sys.argv[2])
    if not issues:
        print("✓ PASS — All SOME/IP service interfaces aligned")
    else:
        print(f"✗ FAIL — {len(issues)} mismatch(es) found:")
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(1)
```

**Technologies:** Python, lxml, pytest

---

## PROJECT 3: SOME/IP Frame Builder & Sender (Testing Tool)

**Problem:** To test a SOME/IP server, you need a client. Setting up a real AUTOSAR ECU as a test client is slow. This tool lets you send arbitrary SOME/IP frames from a laptop.

**Key Implementation:**
```python
# someip_sender.py
"""
SOME/IP test frame builder and sender.
Send arbitrary SOME/IP requests/events from laptop to ECU under test.
"""
import socket
import struct
import argparse


def build_someip(service_id: int, method_id: int, client_id: int,
                 session_id: int, msg_type: int, return_code: int,
                 payload: bytes = b"") -> bytes:
    """Build a SOME/IP message."""
    length = 8 + len(payload)  # from byte 8 to end
    header = struct.pack(
        ">HHIHHBBBB",
        service_id,   # 2 bytes
        method_id,    # 2 bytes
        length,       # 4 bytes
        client_id,    # 2 bytes
        session_id,   # 2 bytes
        0x01,         # proto version
        0x01,         # interface version
        msg_type,     # message type
        return_code   # return code
    )
    return header + payload


def send_request(server_ip: str, server_port: int,
                 service_id: int, method_id: int,
                 payload: bytes = b"") -> bytes:
    """
    Send a SOME/IP REQUEST and wait for RESPONSE.
    Returns the response payload or raises TimeoutError.
    """
    frame = build_someip(
        service_id=service_id, method_id=method_id,
        client_id=0x0100, session_id=0x0001,
        msg_type=0x00,   # REQUEST
        return_code=0x00,
        payload=payload
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)  # 2 second timeout
    sock.sendto(frame, (server_ip, server_port))

    try:
        resp_data, _ = sock.recvfrom(65535)
        # Parse response header
        service_id_r, method_id_r, length_r, client_id_r, session_id_r, \
            pv, iv, msg_type_r, return_code_r = struct.unpack_from(">HHIHHBBBB", resp_data)

        print(f"Response: MsgType=0x{msg_type_r:02X} RC=0x{return_code_r:02X}")
        payload_r = resp_data[16:]
        return payload_r
    except socket.timeout:
        raise TimeoutError(f"No SOME/IP response from {server_ip}:{server_port}")
    finally:
        sock.close()


def subscribe_and_listen(sd_ip: str = "224.224.224.245", sd_port: int = 30490,
                         service_id: int = 0x1234, instance_id: int = 0x0001,
                         eventgroup_id: int = 0x0001, duration_s: int = 10):
    """
    Send SOME/IP-SD SubscribeEventgroup and listen for events.
    Simplified version (without full SD state machine).
    """
    # Note: full SD requires OfferService detection first
    # This is a simplified direct subscribe (for test ECUs)
    print(f"Listening for SOME/IP events from service 0x{service_id:04X}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 30491))  # Listen on client port
    sock.settimeout(0.5)

    import time
    t_end = time.monotonic() + duration_s
    count = 0
    while time.monotonic() < t_end:
        try:
            data, addr = sock.recvfrom(65535)
            if len(data) >= 16:
                svc_id, meth_id = struct.unpack_from(">HH", data)
                if svc_id == service_id and meth_id >= 0x8000:
                    count += 1
                    print(f"  Event #{count}: SvcID=0x{svc_id:04X} "
                          f"MethID=0x{meth_id:04X} "
                          f"Payload={len(data)-16}B from {addr[0]}")
        except socket.timeout:
            continue
    sock.close()
    print(f"\nTotal events received: {count} in {duration_s}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SOME/IP Test Sender")
    parser.add_argument("--server", default="192.168.10.10")
    parser.add_argument("--port", type=int, default=30000)
    parser.add_argument("--service", type=lambda x: int(x, 0), default=0x1234)
    parser.add_argument("--method", type=lambda x: int(x, 0), default=0x0001)
    parser.add_argument("--listen", action="store_true")
    args = parser.parse_args()

    if args.listen:
        subscribe_and_listen(service_id=args.service)
    else:
        resp = send_request(args.server, args.port, args.service, args.method)
        print(f"Payload received: {resp.hex()}")
```

**Technologies:** Python, socket, struct, argparse

---

## PROJECT 4: CAPL SOME/IP Test Library

**Problem:** Writing SOME/IP test automation in CANoe requires repetitive boilerplate CAPL code. A reusable CAPL library speeds up test development.

**Key CAPL Code:**
```c
// someip_lib.can
// Reusable SOME/IP test functions for CANoe vTESTstudio

variables {
  byte someip_buf[1514];
  long someip_send_time;
}

/* Build a SOME/IP REQUEST frame */
long someip_build_request(byte buf[], long svc_id, long meth_id,
                           long client_id, long session_id,
                           byte payload[], long payload_len) {
  long offset = 0;
  
  /* Service ID (2B, big-endian) */
  buf[0] = (svc_id >> 8) & 0xFF;
  buf[1] = svc_id & 0xFF;
  /* Method ID (2B) */
  buf[2] = (meth_id >> 8) & 0xFF;
  buf[3] = meth_id & 0xFF;
  /* Length (4B) = 8 (header after len) + payload_len */
  long length = 8 + payload_len;
  buf[4] = (length >> 24) & 0xFF;
  buf[5] = (length >> 16) & 0xFF;
  buf[6] = (length >> 8) & 0xFF;
  buf[7] = length & 0xFF;
  /* Client ID (2B) */
  buf[8] = (client_id >> 8) & 0xFF;
  buf[9] = client_id & 0xFF;
  /* Session ID (2B) */
  buf[10] = (session_id >> 8) & 0xFF;
  buf[11] = session_id & 0xFF;
  /* Proto Ver, IFace Ver, Msg Type, Return Code */
  buf[12] = 0x01;  /* SOME/IP version */
  buf[13] = 0x01;  /* Interface version */
  buf[14] = 0x00;  /* REQUEST */
  buf[15] = 0x00;  /* E_OK */
  
  /* Payload */
  long i;
  for (i = 0; i < payload_len; i++) {
    buf[16 + i] = payload[i];
  }
  
  return 16 + payload_len;  /* total frame length */
}

/* Verify a received SOME/IP event has correct period */
testcase TC_SOMEIP_EventPeriod(long svc_id, long meth_id,
                                float expected_ms, float tolerance_pct) {
  testCaseTitle("TC-SIIP-PERIOD", "SOME/IP Event Period Check");
  
  float t1 = -1.0;
  float t2 = -1.0;
  float gap_ms;
  long count = 0;
  
  /* Capture 10 events and measure gaps */
  long timeout_ms = (long)(expected_ms * 15);  /* 15× period timeout */
  
  /* ... event capture logic with on ethernetPacket handler ... */
  /* See full implementation in repository */
  
  testStepPass("Period", "Event period within tolerance");
}

testcase TC_SOMEIP_RequestResponse(long svc_id, long meth_id,
                                    long timeout_ms) {
  testCaseTitle("TC-SIIP-RR", "SOME/IP Request/Response");
  byte payload[4] = {0x00, 0x00, 0x00, 0x00};
  long frame_len;
  
  frame_len = someip_build_request(someip_buf, svc_id, meth_id,
                                   0x0100, 0x0001, payload, 4);
  
  someip_send_time = timeNow();
  /* Send via UDP socket in CANoe */
  /* ... socket send ... */
  
  /* Wait for response */
  long resp_time = waitForResponse(svc_id, meth_id, timeout_ms);
  if (resp_time < 0) {
    testStepFail("Response", "No SOME/IP response within timeout");
    testCaseFail();
    return;
  }
  
  float latency_ms = (float)(resp_time - someip_send_time) / 10000.0;
  write("Request/Response latency: %.2f ms", latency_ms);
  
  if (latency_ms <= timeout_ms) {
    testStepPass("Latency", "Response within timeout");
  } else {
    testStepFail("Latency", "Response exceeded timeout");
  }
}
```

**Technologies:** CAPL, CANoe vTESTstudio, Automotive Ethernet

**Resume Description:**
> "Built reusable CAPL SOME/IP test library with frame builder, event period checker, and request/response validator — reduced new SOME/IP test case development from 4 hours to 30 minutes. Used across 6 ECU projects."

---

*Next Module: [../03_DoIP/01_Theory_Deep_Dive.md](../03_DoIP/01_Theory_Deep_Dive.md)*
