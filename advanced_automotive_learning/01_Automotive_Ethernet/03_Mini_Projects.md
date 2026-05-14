# AUTOMOTIVE ETHERNET — MINI PROJECTS
## Module 1 of 7 | 4 GitHub-Ready Projects

---

## PROJECT 1: Automotive Ethernet Link Quality Monitor

**Problem:** When bring-up a new ECU, verifying PHY link state, link-up time, and packet loss requires manual MDIO reads and Wireshark sessions — tedious and error-prone.

**What it does:** Automated tool that monitors Ethernet link health, measures link-up time after power cycle, detects link drops, reports packet loss rate.

**Architecture:**
```
eth_link_monitor/
├── monitor.py          ← Main monitoring loop
├── mdio_reader.py      ← MDIO register reader (via USB-to-SPI adapter)
├── packet_capture.py   ← pyshark-based packet counter
├── report.py           ← HTML report generator
├── config.yaml         ← PHY addresses, thresholds
├── tests/
│   └── test_monitor.py ← Unit tests
└── README.md
```

**Full Implementation:**
```python
# monitor.py
"""
Automotive Ethernet Link Quality Monitor
Monitors PHY link state, measures link-up time, detects drops.
"""
import time
import subprocess
import statistics
from dataclasses import dataclass, field
from typing import List, Optional
import pyshark
import yaml
import threading


@dataclass
class LinkEvent:
    timestamp: float
    event_type: str  # "LINK_UP" | "LINK_DOWN"
    duration_ms: Optional[float] = None  # for LINK_UP: time to establish


@dataclass
class LinkStats:
    link_up_times_ms: List[float] = field(default_factory=list)
    link_drops: int = 0
    total_packets_rx: int = 0
    total_packets_expected: int = 0
    events: List[LinkEvent] = field(default_factory=list)

    def packet_loss_percent(self) -> float:
        if self.total_packets_expected == 0:
            return 0.0
        return 100.0 * (1.0 - self.total_packets_rx / self.total_packets_expected)

    def avg_link_up_time_ms(self) -> float:
        if not self.link_up_times_ms:
            return 0.0
        return statistics.mean(self.link_up_times_ms)


class EthernetLinkMonitor:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)
        self.interface = self.cfg["interface"]  # e.g. "eth0"
        self.link_up_threshold_ms = self.cfg["thresholds"]["link_up_ms"]
        self.stats = LinkStats()
        self._running = False

    def _is_link_up(self) -> bool:
        """Read link state via ethtool (proxy for MDIO LINK_STATUS bit)."""
        try:
            result = subprocess.run(
                ["ethtool", self.interface],
                capture_output=True, text=True, timeout=2
            )
            return "Link detected: yes" in result.stdout
        except Exception:
            return False

    def measure_link_up_time(self) -> float:
        """
        Simulate power cycle: bring interface down, then up.
        Measure time until link is detected.
        Returns: link-up time in ms
        """
        # Bring link down
        subprocess.run(["ip", "link", "set", self.interface, "down"])
        time.sleep(0.5)

        # Bring link up and start timer
        t_start = time.monotonic()
        subprocess.run(["ip", "link", "set", self.interface, "up"])

        # Poll for link
        while time.monotonic() - t_start < 2.0:
            if self._is_link_up():
                elapsed_ms = (time.monotonic() - t_start) * 1000.0
                self.stats.link_up_times_ms.append(elapsed_ms)
                event = LinkEvent(
                    timestamp=t_start,
                    event_type="LINK_UP",
                    duration_ms=elapsed_ms
                )
                self.stats.events.append(event)
                return elapsed_ms
            time.sleep(0.01)  # 10ms poll

        return -1.0  # link never came up

    def monitor_continuous(self, duration_s: int = 60):
        """Monitor link drops for specified duration."""
        self._running = True
        t_end = time.monotonic() + duration_s
        last_state = self._is_link_up()

        print(f"[Monitor] Starting {duration_s}s link monitoring on {self.interface}")

        while time.monotonic() < t_end and self._running:
            current_state = self._is_link_up()

            if last_state and not current_state:
                # Link went DOWN
                self.stats.link_drops += 1
                self.stats.events.append(
                    LinkEvent(timestamp=time.monotonic(), event_type="LINK_DOWN")
                )
                print(f"[Monitor] LINK DOWN at {time.monotonic():.3f}s (drop #{self.stats.link_drops})")

            elif not last_state and current_state:
                # Link came BACK UP
                self.stats.events.append(
                    LinkEvent(timestamp=time.monotonic(), event_type="LINK_UP")
                )
                print(f"[Monitor] LINK UP at {time.monotonic():.3f}s")

            last_state = current_state
            time.sleep(0.05)  # 50ms poll

    def run_link_up_test(self, iterations: int = 10) -> dict:
        """Run multiple link-up time measurements."""
        print(f"\n[Test] Measuring link-up time over {iterations} power cycles...")

        for i in range(iterations):
            t = self.measure_link_up_time()
            status = "PASS" if 0 < t <= self.link_up_threshold_ms else "FAIL"
            print(f"  Cycle {i+1:02d}: {t:.1f}ms [{status}] (threshold={self.link_up_threshold_ms}ms)")
            time.sleep(1.0)  # Recovery between cycles

        avg = self.stats.avg_link_up_time_ms()
        max_t = max(self.stats.link_up_times_ms) if self.stats.link_up_times_ms else 0
        failures = sum(1 for t in self.stats.link_up_times_ms if t > self.link_up_threshold_ms)

        return {
            "iterations": iterations,
            "avg_ms": round(avg, 2),
            "max_ms": round(max_t, 2),
            "failures": failures,
            "pass_rate": f"{(iterations - failures) / iterations * 100:.0f}%"
        }

    def generate_report(self, results: dict) -> str:
        """Generate HTML test report."""
        html = f"""<!DOCTYPE html>
<html><head><title>Ethernet Link Quality Report</title>
<style>body{{font-family:monospace;margin:40px;}}
.pass{{color:green;font-weight:bold;}} .fail{{color:red;font-weight:bold;}}
table{{border-collapse:collapse;width:100%;}}
td,th{{border:1px solid #ccc;padding:8px;}}
</style></head><body>
<h1>Automotive Ethernet Link Quality Report</h1>
<h2>Interface: {self.interface}</h2>
<table>
<tr><th>Metric</th><th>Value</th><th>Threshold</th><th>Status</th></tr>
<tr><td>Avg Link-Up Time</td><td>{results['avg_ms']}ms</td>
    <td>{self.link_up_threshold_ms}ms</td>
    <td class="{'pass' if results['avg_ms'] < self.link_up_threshold_ms else 'fail'}">
    {'PASS' if results['avg_ms'] < self.link_up_threshold_ms else 'FAIL'}</td></tr>
<tr><td>Max Link-Up Time</td><td>{results['max_ms']}ms</td>
    <td>{self.link_up_threshold_ms}ms</td>
    <td class="{'pass' if results['max_ms'] < self.link_up_threshold_ms else 'fail'}">
    {'PASS' if results['max_ms'] < self.link_up_threshold_ms else 'FAIL'}</td></tr>
<tr><td>Pass Rate</td><td colspan="2">{results['pass_rate']}</td>
    <td class="{'pass' if results['failures'] == 0 else 'fail'}">
    {'PASS' if results['failures'] == 0 else 'FAIL'}</td></tr>
<tr><td>Link Drops (continuous)</td><td colspan="2">{self.stats.link_drops}</td>
    <td class="{'pass' if self.stats.link_drops == 0 else 'fail'}">
    {'PASS' if self.stats.link_drops == 0 else 'FAIL'}</td></tr>
</table>
</body></html>"""
        with open("eth_link_report.html", "w") as f:
            f.write(html)
        return "eth_link_report.html"


if __name__ == "__main__":
    monitor = EthernetLinkMonitor("config.yaml")
    results = monitor.run_link_up_test(iterations=10)
    report = monitor.generate_report(results)
    print(f"\n[Report] Generated: {report}")
    print(f"Results: {results}")
```

```yaml
# config.yaml
interface: "eth0"
thresholds:
  link_up_ms: 300
  packet_loss_percent: 0.1
  link_drops_per_hour: 0
```

**Technologies:** Python, pyshark, Scapy, subprocess (ethtool/ip), pytest, HTML reporting

**Resume Description:**
> "Built Automotive Ethernet link quality monitor (Python) that automated PHY link-up time measurement over 10 power cycles, packet loss detection via pyshark, and link drop monitoring — reducing manual Ethernet bring-up testing from 3 hours to 18 minutes. Used on 4 ECU bring-up projects."

---

## PROJECT 2: VLAN Segmentation Validator

**Problem:** Misconfigured VLAN isolation in Ethernet switches causes safety-critical traffic to leak into wrong domains. Manual verification is slow and incomplete.

**What it does:** Automatically injects tagged Ethernet frames on one VLAN and verifies they do NOT appear on other VLAN ports. Generates a pass/fail report.

**Architecture:**
```
vlan_validator/
├── injector.py        ← Scapy frame injection
├── capturer.py        ← pyshark frame capture per port
├── validator.py       ← Compare inject vs capture, assert isolation
├── report.py          ← Test report
├── config.yaml        ← VLAN map, interface names
└── README.md
```

**Key Implementation:**
```python
# validator.py
from scapy.all import Ether, Dot1Q, IP, UDP, sendp
import pyshark
import time
import threading


def inject_vlan_frame(src_iface: str, vlan_id: int, dst_ip: str, marker: int):
    """Send a uniquely identifiable frame on specified VLAN."""
    pkt = (
        Ether(dst="ff:ff:ff:ff:ff:ff") /
        Dot1Q(vlan=vlan_id, prio=7) /
        IP(dst=dst_ip, id=marker) /
        UDP(dport=9999) /
        bytes([marker & 0xFF, (marker >> 8) & 0xFF])
    )
    sendp(pkt, iface=src_iface, verbose=False)


def capture_vlan_frames(iface: str, timeout: int = 3) -> list:
    """Capture all frames on interface, return list of VLAN IDs seen."""
    seen_vlans = []
    cap = pyshark.LiveCapture(
        interface=iface,
        display_filter="vlan"
    )
    cap.sniff(timeout=timeout)
    for pkt in cap:
        if hasattr(pkt, 'vlan'):
            seen_vlans.append(int(pkt.vlan.id))
    return seen_vlans


def test_vlan_isolation(src_iface: str, src_vlan: int,
                        monitor_iface: str, forbidden_vlan: int) -> bool:
    """
    Returns True if src_vlan traffic does NOT appear on monitor_iface.
    """
    # Start capture in background
    seen = []
    def capture():
        seen.extend(capture_vlan_frames(monitor_iface, timeout=4))
    t = threading.Thread(target=capture)
    t.start()

    time.sleep(0.5)  # Allow capture to start
    inject_vlan_frame(src_iface, src_vlan, "192.168.1.255", marker=0xABCD)
    t.join()

    leaked = forbidden_vlan in seen
    if leaked:
        print(f"FAIL: VLAN {forbidden_vlan} traffic LEAKED onto {monitor_iface}")
    else:
        print(f"PASS: VLAN {forbidden_vlan} correctly isolated on {monitor_iface}")
    return not leaked


# Test: ADAS VLAN 10 must not reach Infotainment port
result = test_vlan_isolation(
    src_iface="eth1",   src_vlan=10,
    monitor_iface="eth2", forbidden_vlan=10
)
```

**Technologies:** Python, Scapy, pyshark, pytest

---

## PROJECT 3: gPTP Sync Accuracy Analyzer

**Problem:** Verifying gPTP synchronization accuracy requires manually parsing Wireshark captures — slow and impractical for CI pipelines.

**What it does:** Parses live or recorded PTP traffic, extracts sync offset from Follow_Up correction fields, calculates accuracy statistics, generates time-series plot.

**Key Implementation:**
```python
# gptp_analyzer.py
import pyshark
import matplotlib.pyplot as plt
import statistics
from dataclasses import dataclass
from typing import List


@dataclass
class SyncMeasurement:
    time_s: float
    offset_ns: float
    src_mac: str


def analyze_gptp(pcap_file: str = None, interface: str = None,
                 duration_s: int = 30) -> List[SyncMeasurement]:
    """
    Capture or read gPTP sync frames, extract correction field.
    correction field in Follow_Up = path delay correction in nanoseconds.
    """
    measurements = []

    if pcap_file:
        cap = pyshark.FileCapture(pcap_file, display_filter="ptp")
    else:
        cap = pyshark.LiveCapture(interface=interface, display_filter="ptp")
        cap.sniff(timeout=duration_s)

    for pkt in cap:
        try:
            # Only process Follow_Up messages (message type 8)
            if not hasattr(pkt, 'ptp'):
                continue
            if int(pkt.ptp.v2_messageid, 16) != 0x8:  # Follow_Up
                continue

            # correction field is in nanoseconds * 2^16 (fixed-point)
            correction_raw = int(pkt.ptp.v2_correctionns, 16)
            correction_ns = correction_raw / (2**16)

            m = SyncMeasurement(
                time_s=float(pkt.sniff_timestamp),
                offset_ns=correction_ns,
                src_mac=str(pkt.eth.src)
            )
            measurements.append(m)
        except Exception:
            continue

    return measurements


def report_accuracy(measurements: List[SyncMeasurement],
                    threshold_ns: float = 1000.0):
    """Report gPTP sync accuracy statistics."""
    if not measurements:
        print("No gPTP measurements found.")
        return

    offsets = [abs(m.offset_ns) for m in measurements]
    mean_ns = statistics.mean(offsets)
    max_ns = max(offsets)
    violations = sum(1 for o in offsets if o > threshold_ns)

    print(f"\ngPTP Sync Accuracy Report")
    print(f"{'─'*40}")
    print(f"Samples:          {len(measurements)}")
    print(f"Mean offset:      {mean_ns:.1f} ns")
    print(f"Max offset:       {max_ns:.1f} ns")
    print(f"Threshold:        {threshold_ns:.0f} ns (1µs)")
    print(f"Violations:       {violations}")
    result = "PASS" if violations == 0 else "FAIL"
    print(f"Overall result:   {result}")

    # Plot time series
    times = [m.time_s - measurements[0].time_s for m in measurements]
    plt.figure(figsize=(12, 4))
    plt.plot(times, offsets, 'b-', linewidth=0.8)
    plt.axhline(y=threshold_ns, color='r', linestyle='--', label='1µs threshold')
    plt.xlabel("Time (s)"); plt.ylabel("Sync Offset (ns)")
    plt.title("gPTP Synchronization Accuracy")
    plt.legend(); plt.tight_layout()
    plt.savefig("gptp_accuracy.png", dpi=150)
    print(f"Plot saved: gptp_accuracy.png")


if __name__ == "__main__":
    data = analyze_gptp(pcap_file="capture.pcap")
    report_accuracy(data, threshold_ns=1000.0)
```

**Technologies:** Python, pyshark, matplotlib, pytest

**Resume Description:**
> "Developed gPTP synchronization accuracy analyzer (Python/pyshark) that auto-parsed PTP Follow_Up correction fields, computed mean/max offset, and generated time-series accuracy plots — replaced 2-hour manual Wireshark analysis with 5-minute automated report."

---

## PROJECT 4: Automotive Ethernet Topology Visualizer

**Problem:** Large Ethernet networks with 10+ ECUs and multiple VLANs are hard to visualize. Network topology documentation is always out of date.

**What it does:** Sniffs LLDP (Link Layer Discovery Protocol) and ARP traffic, auto-discovers ECU connections, VLAN memberships, and generates an interactive topology diagram.

**Architecture:**
```
eth_topology/
├── discoverer.py      ← LLDP + ARP sniffer
├── topology.py        ← Graph model
├── visualizer.py      ← HTML/SVG diagram generator (vis.js)
├── requirements.txt
└── README.md
```

**Key Implementation:**
```python
# discoverer.py
from scapy.all import sniff, Ether, ARP, Dot1Q
from collections import defaultdict
import json


class TopologyDiscoverer:
    def __init__(self):
        self.nodes = {}    # mac → {ip, vlan, hostname}
        self.edges = []    # (mac_a, mac_b, vlan)

    def process_pkt(self, pkt):
        if ARP in pkt:
            src_mac = pkt[Ether].src
            src_ip  = pkt[ARP].psrc
            vlan_id = pkt[Dot1Q].vlan if Dot1Q in pkt else 0

            if src_mac not in self.nodes:
                self.nodes[src_mac] = {"ip": src_ip, "vlan": vlan_id}
                print(f"  Discovered: {src_mac} → {src_ip} (VLAN {vlan_id})")

    def discover(self, interface: str = "eth0", duration: int = 30):
        print(f"[Discovery] Listening on {interface} for {duration}s...")
        sniff(iface=interface, prn=self.process_pkt, timeout=duration)

    def export_json(self, path: str = "topology.json"):
        data = {"nodes": self.nodes, "edges": self.edges}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[Export] Topology saved to {path}")


if __name__ == "__main__":
    d = TopologyDiscoverer()
    d.discover(interface="eth0", duration=30)
    d.export_json()
```

**Technologies:** Python, Scapy, pyshark, vis.js (HTML visualization), JSON

**Resume Description:**
> "Built Automotive Ethernet topology auto-discoverer that sniffs LLDP/ARP traffic and generates interactive HTML topology diagrams — eliminated manual topology documentation for a 12-ECU test bench, saving 1 day of documentation work per project phase."

---

*Next Module: [../02_SOMEIP/01_Theory_Deep_Dive.md](../02_SOMEIP/01_Theory_Deep_Dive.md)*
