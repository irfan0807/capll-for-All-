# DoIP — MINI PROJECTS
## Module 3 of 7 | 4 GitHub-Ready Projects

---

## PROJECT 1: Python DoIP Client Library

**Problem:** Commercial DoIP tools cost €8,000/seat. Teams need a free, scriptable client for automated testing.

**Architecture:**
```
doip_client/
├── doip_client.py      ← Core DoIP client class
├── uds_services.py     ← UDS service wrappers
├── discovery.py        ← UDP vehicle discovery
├── exceptions.py       ← DoIP-specific exceptions
├── tests/
│   ├── test_client.py
│   └── test_uds.py
├── examples/
│   ├── basic_session.py
│   └── flash_ecu.py
└── README.md
```

**Full Implementation:**
```python
# doip_client.py
"""
DoIP Client — ISO 13400-2 implementation.
Supports: Vehicle Discovery, Routing Activation, Diagnostic Messages.
"""
import socket
import struct
import threading
import time
import logging
from enum import IntEnum
from typing import Optional, Tuple


logger = logging.getLogger("doip")


class DoIPPayloadType(IntEnum):
    GENERIC_NEG_ACK    = 0x0000
    VEHICLE_ID_REQ     = 0x0001
    VEHICLE_ID_EID     = 0x0002
    VEHICLE_ID_VIN     = 0x0003
    VEHICLE_ANNOUNCE   = 0x0004
    ROUTING_ACT_REQ    = 0x0005
    ROUTING_ACT_RESP   = 0x0006
    ALIVE_CHECK_REQ    = 0x0007
    ALIVE_CHECK_RESP   = 0x0008
    DIAG_MSG           = 0x8001
    DIAG_MSG_POS_ACK   = 0x8002
    DIAG_MSG_NEG_ACK   = 0x8003


class RoutingActivationCode(IntEnum):
    SUCCESS           = 0x10
    DENIED_UNKNOWN    = 0x00
    DENIED_NOT_REG    = 0x06
    DENIED_MAX_CONN   = 0x04


class DoIPConnectionError(Exception):
    pass


class DoIPRoutingError(Exception):
    pass


class DoIPTimeoutError(Exception):
    pass


def build_header(payload_type: int, payload: bytes) -> bytes:
    """Build DoIP generic header."""
    return struct.pack(">BBHI", 0x02, 0xFD, payload_type, len(payload)) + payload


def parse_header(data: bytes) -> Tuple[int, int, bytes]:
    """Parse DoIP header. Returns (version, payload_type, payload)."""
    if len(data) < 8:
        raise ValueError("DoIP header too short")
    version, inv_version, payload_type, length = struct.unpack_from(">BBHI", data)
    payload = data[8:8 + length]
    return version, payload_type, payload


class DoIPClient:
    """
    DoIP client for ECU diagnostics.
    
    Usage:
        client = DoIPClient("192.168.20.10")
        with client:
            client.routing_activation(tester_addr=0x0E01)
            response = client.send_diagnostic(
                target_addr=0x0010,
                uds_payload=bytes([0x10, 0x03])
            )
    """

    DOIP_PORT = 13400
    DOIP_UDP_PORT = 13400
    DISCOVERY_BROADCAST = "255.255.255.255"

    def __init__(self, gateway_ip: str, timeout: float = 5.0):
        self.gateway_ip = gateway_ip
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._tester_addr: Optional[int] = None
        self._lock = threading.Lock()
        self._activated = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()

    def connect(self):
        """Establish TCP connection to DoIP gateway."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        try:
            self._sock.connect((self.gateway_ip, self.DOIP_PORT))
            logger.info(f"Connected to {self.gateway_ip}:{self.DOIP_PORT}")
        except (OSError, socket.timeout) as e:
            raise DoIPConnectionError(f"Cannot connect to {self.gateway_ip}: {e}")

    def close(self):
        """Close TCP connection."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._activated = False

    def routing_activation(self, tester_addr: int = 0x0E01,
                           activation_type: int = 0x00):
        """
        Send Routing Activation Request.
        Raises DoIPRoutingError if activation denied.
        """
        # Build RoutingActivationRequest payload
        payload = struct.pack(">HHI", tester_addr, activation_type, 0x00000000)
        frame = build_header(DoIPPayloadType.ROUTING_ACT_REQ, payload)
        self._send(frame)

        response = self._recv()
        _, resp_type, resp_payload = parse_header(response)

        if resp_type != DoIPPayloadType.ROUTING_ACT_RESP:
            raise DoIPRoutingError(f"Unexpected response type: 0x{resp_type:04X}")

        tester_addr_r, gw_addr, resp_code = struct.unpack_from(">HHB", resp_payload)
        if resp_code != RoutingActivationCode.SUCCESS:
            raise DoIPRoutingError(
                f"Routing activation denied: code=0x{resp_code:02X}"
            )

        self._tester_addr = tester_addr
        self._activated = True
        logger.info(f"Routing activated: tester=0x{tester_addr:04X}, "
                    f"gateway=0x{gw_addr:04X}")

    def send_diagnostic(self, target_addr: int, uds_payload: bytes,
                        response_timeout: float = 5.0) -> bytes:
        """
        Send a UDS request via DoIP and receive the response.
        Returns UDS response payload (without DoIP header).
        Raises DoIPTimeoutError if no response.
        """
        if not self._activated:
            raise DoIPRoutingError("Routing activation required before diagnostics")

        # Build DiagnosticMessage
        diag_payload = struct.pack(">HH", self._tester_addr, target_addr) + uds_payload
        frame = build_header(DoIPPayloadType.DIAG_MSG, diag_payload)

        with self._lock:
            self._send(frame)

            # Expect DiagMsgPositiveAck first
            ack = self._recv()
            _, ack_type, ack_payload = parse_header(ack)

            if ack_type == DoIPPayloadType.DIAG_MSG_NEG_ACK:
                nack_code = ack_payload[4] if len(ack_payload) > 4 else 0xFF
                raise DoIPConnectionError(f"DiagMsgNegAck: code=0x{nack_code:02X}")

            if ack_type != DoIPPayloadType.DIAG_MSG_POS_ACK:
                raise DoIPConnectionError(f"Expected PosAck, got 0x{ack_type:04X}")

            # Now receive the actual UDS response (may come after some delay for NRC 0x78)
            old_timeout = self._sock.gettimeout()
            self._sock.settimeout(response_timeout)
            try:
                resp = self._recv()
            finally:
                self._sock.settimeout(old_timeout)

            _, resp_type, resp_payload = parse_header(resp)
            if resp_type != DoIPPayloadType.DIAG_MSG:
                raise DoIPConnectionError(f"Expected DiagMsg response, got 0x{resp_type:04X}")

            # resp_payload: [SrcAddr 2B][DstAddr 2B][UDS payload...]
            uds_response = resp_payload[4:]

            # Handle NRC 0x78 (requestCorrectlyReceived-ResponsePending)
            if (len(uds_response) >= 3 and
                    uds_response[0] == 0x7F and uds_response[2] == 0x78):
                logger.info("NRC 0x78 received — waiting for final response")
                self._sock.settimeout(P2_STAR_TIMEOUT := 5.0)
                try:
                    resp2 = self._recv()
                    _, _, resp2_payload = parse_header(resp2)
                    uds_response = resp2_payload[4:]
                finally:
                    self._sock.settimeout(old_timeout)

            return uds_response

    def _send(self, data: bytes):
        total = 0
        while total < len(data):
            sent = self._sock.send(data[total:])
            if sent == 0:
                raise DoIPConnectionError("Socket closed during send")
            total += sent

    def _recv(self, bufsize: int = 65536) -> bytes:
        try:
            data = self._sock.recv(bufsize)
            if not data:
                raise DoIPConnectionError("Socket closed by remote")
            return data
        except socket.timeout:
            raise DoIPTimeoutError("No DoIP response received")

    @classmethod
    def discover(cls, timeout: float = 2.0) -> list:
        """
        Send VehicleIdentificationRequest (UDP broadcast).
        Returns list of discovered gateways: [{ip, vin, eid, gid}]
        """
        results = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        req = build_header(DoIPPayloadType.VEHICLE_ID_REQ, b"")
        sock.sendto(req, (cls.DISCOVERY_BROADCAST, cls.DOIP_UDP_PORT))

        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            try:
                data, addr = sock.recvfrom(65535)
                _, payload_type, payload = parse_header(data)
                if payload_type == DoIPPayloadType.VEHICLE_ANNOUNCE:
                    vin = payload[0:17].decode("ascii", errors="replace")
                    eid = ":".join(f"{b:02X}" for b in payload[17:23])
                    results.append({"ip": addr[0], "vin": vin, "eid": eid})
                    logger.info(f"Discovered: {addr[0]} VIN={vin} EID={eid}")
            except socket.timeout:
                break

        sock.close()
        return results
```

```python
# examples/basic_session.py
"""Basic DoIP diagnostic session example."""
from doip_client import DoIPClient

# Discover gateway
gateways = DoIPClient.discover(timeout=2.0)
if not gateways:
    print("No DoIP gateway found")
    exit(1)

gw_ip = gateways[0]["ip"]
print(f"Gateway: {gw_ip}, VIN: {gateways[0]['vin']}")

with DoIPClient(gw_ip) as client:
    client.routing_activation(tester_addr=0x0E01)

    # Read VIN from BCM (DID F190)
    response = client.send_diagnostic(
        target_addr=0x0010,
        uds_payload=bytes([0x22, 0xF1, 0x90])
    )
    print(f"BCM VIN response: {response.hex()}")

    # Enter Extended Diagnostic Session
    response = client.send_diagnostic(
        target_addr=0x0010,
        uds_payload=bytes([0x10, 0x03])
    )
    print(f"Session response: {response.hex()}")
```

**Technologies:** Python 3, socket, struct, threading, pytest

**Resume Description:**
> "Implemented open-source Python DoIP client (ISO 13400-2) with TCP state machine, Vehicle Discovery, Routing Activation, and diagnostic message handling with NRC 0x78 support. Used to automate 120 UDS test cases across 5 ECUs. Replaced €40,000 commercial tool licenses."

---

## PROJECT 2: DoIP Traffic Analyzer (Wireshark Add-on)

**Problem:** Analyzing DoIP captures in Wireshark requires manually calculating addresses and decoding payload types. This Python tool adds ECU name resolution and UDS service annotation.

**Key Implementation:**
```python
# doip_analyzer.py
"""Analyze DoIP packet captures and annotate with ECU names."""
import pyshark
from dataclasses import dataclass
from typing import List, Dict

ECU_NAMES = {
    0x0010: "BCM", 0x0020: "ADAS_DC", 0x0030: "Camera",
    0x0040: "Radar", 0x0E00: "Gateway", 0x0E01: "Tester"
}

UDS_SERVICES = {
    0x10: "DiagSessionControl", 0x11: "ECUReset",
    0x14: "ClearDTC", 0x19: "ReadDTCInfo",
    0x22: "ReadDID", 0x27: "SecurityAccess",
    0x2E: "WriteDID", 0x31: "RoutineControl",
    0x34: "RequestDownload", 0x36: "TransferData",
    0x37: "RequestTransferExit", 0x3E: "TesterPresent",
    0x7F: "NegativeResponse"
}


@dataclass
class DoIPTransaction:
    timestamp: float
    src_addr: int
    dst_addr: int
    uds_service: int
    uds_service_name: str
    is_response: bool
    raw_uds: str

    def __str__(self):
        src = ECU_NAMES.get(self.src_addr, f"0x{self.src_addr:04X}")
        dst = ECU_NAMES.get(self.dst_addr, f"0x{self.dst_addr:04X}")
        arrow = "◄" if self.is_response else "►"
        return (f"t={self.timestamp:.3f}s {src} {arrow} {dst}: "
                f"{self.uds_service_name} [{self.raw_uds[:20]}]")


def analyze_doip_pcap(pcap_file: str) -> List[DoIPTransaction]:
    import struct
    cap = pyshark.FileCapture(pcap_file, display_filter="doip")
    transactions = []

    for pkt in cap:
        try:
            if not hasattr(pkt, 'doip'):
                continue
            payload_type = int(pkt.doip.payload_type, 16)
            if payload_type != 0x8001:  # DiagMsg only
                continue

            # Extract addresses from DoIP payload
            raw = bytes.fromhex(pkt.tcp.payload.replace(':', ''))
            src_addr, dst_addr = struct.unpack_from(">HH", raw, 8)
            uds = raw[12:]  # UDS payload starts at offset 12

            if len(uds) < 1:
                continue

            service_id = uds[0]
            is_response = (service_id & 0x40) != 0  # response SIDs are +0x40
            base_service = service_id & ~0x40 if is_response else service_id
            service_name = UDS_SERVICES.get(base_service, f"0x{service_id:02X}")
            if service_id == 0x7F:
                service_name = f"NegResp(0x{uds[1]:02X})" if len(uds) > 1 else "NegResp"

            transactions.append(DoIPTransaction(
                timestamp=float(pkt.sniff_timestamp),
                src_addr=src_addr, dst_addr=dst_addr,
                uds_service=service_id, uds_service_name=service_name,
                is_response=is_response, raw_uds=uds.hex()
            ))
        except Exception:
            continue

    return transactions


if __name__ == "__main__":
    import sys
    txns = analyze_doip_pcap(sys.argv[1])
    for t in txns:
        print(t)
```

**Technologies:** Python, pyshark, struct

---

*Next Module: [../04_Diagnostics/01_Theory_Deep_Dive.md](../04_Diagnostics/01_Theory_Deep_Dive.md)*
