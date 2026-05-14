# SOME/IP — STAR INTERVIEW STORIES
## Module 2 of 7 | 7 Ready-to-Use STAR Answers

---

## STAR-1: Debugging a SOME/IP Service ID Mismatch

**Situation:**
During integration testing of an ADAS system with 3 ECUs, the domain controller was not receiving speed data from the Body Control Module (BCM). All ECUs were powered on and SOME/IP-SD was showing OfferService messages in Wireshark. But the domain controller's SWC received E_UNKNOWN_SERVICE errors instead of speed values.

**Task:**
Root-cause why the domain controller was rejecting the speed service despite OfferService being visible.

**Action:**
1. Captured Wireshark on domain controller's port. Applied filter: `someip`.
2. Found the domain controller was sending REQUEST frames with Service ID `0x0201` — but the BCM was offering Service ID `0x0200`.
3. Traced both ARXML files: the domain controller's ARXML `<SERVICE-INTERFACE-REF>` had been updated from `0x0200` to `0x0201` by a developer who was aligning it with a "new specification" document — but the BCM's ARXML was still on `0x0200`.
4. Found the root cause: two specification documents were in circulation — a draft with `0x0201` and the approved baseline with `0x0200`. Developer had used the wrong document.
5. Fixed both ARXMLs to `0x0200`, recompiled BSW on both ECUs, retested.

**Result:**
Service communication restored. Speed data flowing correctly. I proposed and implemented a specification control process: all ARXML-referenced service IDs must trace to an approved, version-controlled SOME/IP service design document. This prevented 2 similar mismatches in the same project.

---

## STAR-2: Event Period Violation Detection Tool

**Situation:**
Our SOME/IP speed event was specified at a 20ms cycle time, but occasionally the ADAS algorithm was receiving stale data (same value for 100+ms) without any error flag. This caused the AEB function to use old velocity data, resulting in incorrect braking distance calculation — a safety-critical issue.

**Task:**
Determine if the issue was in the SOME/IP event period or in the SWC's data handling, and provide a reproducible test.

**Action:**
1. Used CANoe's Symbol Explorer to monitor the SOME/IP event's arrival timestamps. Found: events arrived at 19–21ms under normal load — within spec. But under high CPU load on the BCM, events stretched to 80–120ms.
2. The BCM's AUTOSAR OS had the SOME/IP event generation task at a lower priority than a CPU-intensive diagnosis routine. Under diagnostic load, the event task was starved.
3. Wrote a Python SOME/IP event monitor (using pyshark) that logged inter-arrival times, flagged any gap > 25ms, and generated a report.
4. Escalated to the BCM software team with timestamp evidence: "At t=234.5s, event gap = 95ms. CPU load log shows DiagnosticTask at 98% at same moment."
5. BCM team raised the AUTOSAR OS priority of the speed event task from 8 to 12 (below safety tasks but above diagnostics).

**Result:**
Maximum event gap reduced from 120ms to 22ms. My Python monitoring tool was adopted as a standard test in the Ethernet regression suite. Safety analysis updated to document worst-case event latency.

---

## STAR-3: SOME/IP Subscription Loop Debugging

**Situation:**
On a test bench after an ECU software update, Wireshark showed the client ECU sending SubscribeEventgroup messages continuously — every 500ms — in an infinite loop. The server was responding with SubscribeEventgroupAck each time. Events were being received, but the network was flooded with SD traffic.

**Task:**
Determine why the client was resubscribing every 500ms and stop the flooding.

**Action:**
1. Captured SD traffic: `someip-sd && someip-sd.type == 6`. Found SubscribeEventgroup with TTL = 1 (1 second). Resubscription at 500ms was correct per specification (subscribe at T/2 before TTL expiry).
2. Checked the ARXML TTL configuration on the client: `<TTL>1</TTL>`. The previous software version had `<TTL>0xFFFFFF</TTL>` (infinite). A developer had changed it to 1 during a "cleanup" without understanding the impact.
3. Infinite TTL = subscribe once and never resubscribe. TTL=1 = resubscribe every 500ms = 2 extra SD messages per second per subscription × 8 subscribers = 16 extra packets/second.
4. Changed `<TTL>` back to `0xFFFFFF` in the client ARXML. Rebuilt BSW.
5. Added the TTL value to the pre-release ARXML review checklist.

**Result:**
SD flood eliminated. Network utilization dropped from 3% to 0.2% for service discovery traffic. Code review checklist updated with: "Verify SD TTL values — TTL=0xFFFFFF for production, short TTL only for specific test scenarios."

---

## STAR-4: SOME/IP Security — Replay Attack Demonstration

**Situation:**
During a cybersecurity review of our SOME/IP implementation (ISO 21434 compliance), the security architect asked me to demonstrate whether replay attacks were possible on our SOME/IP interface — and assess the actual risk.

**Task:**
Demonstrate a replay attack on a SOME/IP service and evaluate whether it represented a real security risk in our system.

**Action:**
1. Used Scapy to capture a legitimate SOME/IP REQUEST frame for the "UnlockDoor" method (Service 0x0300, Method 0x0001).
2. Wrote a simple Python script to replay that exact captured frame 10 seconds later. The server received and processed it — the door unlock command was replayed successfully.
3. Root cause: SOME/IP Session ID increments per client, but the server does not validate that Session ID is higher than the last received (no monotonic check).
4. Proposed fix: implement SOME/IP Session ID monotonic validation in SoAd or a security module — reject any request with Session ID ≤ last accepted from same Client ID.
5. For safety-critical methods (locks, actuators), recommended adding AUTOSAR SecOC (Secure On-board Communication) MAC authentication on top of SOME/IP.

**Result:**
Security team updated the threat model: replay attack classified as HIGH risk for actuator services. SecOC was added to the ADAS actuator services (AEB, steering). Session ID validation was implemented in SoAd. Finding reported to product security team and tracked in security backlog.

---

## STAR-5: Justifying SOME/IP Over CAN to Hardware Team

**Situation:**
During an architecture review meeting for a new powertrain controller, a senior hardware engineer argued that SOME/IP over Ethernet was "overkill" for powertrain signals and that CAN FD was sufficient. This threatened to remove the Ethernet interface from the ECU design, eliminating future OTA capability and remote diagnostics.

**Task:**
Build a technical and business case for SOME/IP over Ethernet on the powertrain ECU.

**Action:**
1. Prepared a comparison matrix: CAN FD (8 Mbps, 64 bytes, no IP stack, no service discovery) vs Automotive Ethernet + SOME/IP (100 Mbps, 1500 bytes, full IP, service-oriented).
2. Calculated the data required by next-generation powertrain (engine + transmission + battery): 47 signals at 10ms cycle = ~470 bytes/cycle × 100Hz = 47 kbps. "CAN FD can handle this today — but in 3 years you add predictive maintenance telemetry, OTA calibration updates (100MB), and remote diagnostics. CAN FD cannot do OTA."
3. Calculated ROI: adding Ethernet port to the ECU hardware = +€2 (TJA1100 cost). Removing it = €15/vehicle for a physical service port to enable OTA later. Fleet of 500,000 vehicles × €15 = €7.5 million saved.
4. Showed AUTOSAR configurability: SOME/IP stack adds ~50KB flash, well within the MCU budget.
5. Proposed hybrid: keep CAN FD for real-time safety signals, add Ethernet purely for diagnostics + OTA.

**Result:**
Hardware team approved the Ethernet interface. The hybrid architecture became the standard for all powertrain ECUs in the program. OTA capability was delivered as planned in the next software release.

---

## STAR-6: Mentoring a Junior Engineer on SOME/IP Debugging

**Situation:**
A junior engineer on the team had been struggling for 3 days to debug why the SOME/IP service discovery was not working on a new bench setup. He had concluded "the SOME/IP stack is broken" and was about to escalate to the software vendor.

**Task:**
Help the junior engineer identify the root cause without taking over — I wanted to teach him the debugging methodology.

**Action:**
1. Sat with him and asked: "What evidence do you have that SD is broken?" He had no Wireshark capture — only CANoe output window logs.
2. First step: capture raw Wireshark on the multicast address. I showed him the filter: `ip.dst == 224.224.224.245`. OfferService messages were present — but the client ECU's port was different from 30490.
3. Asked him: "What port should SD use?" He checked ARXML — the client had SD port configured as 30491 instead of 30490. A one-digit typo.
4. Fixed the port in ARXML. Service discovery worked immediately.
5. I then walked him through the 5-step SOME/IP debug methodology: (1) Check SD multicast visible; (2) Check OfferService received; (3) Check SubscribeAck received; (4) Check event notifications flowing; (5) Check payload decoding.

**Result:**
Junior engineer resolved the issue himself (with guidance). He wrote up the 5-step debug methodology as a team wiki page that became the standard onboarding reference. The next 3 SOME/IP issues he debugged independently. His ramp-up time was cut by an estimated 2 weeks.

---

## STAR-7: Automated SOME/IP Regression Test Suite

**Situation:**
Our project had 38 SOME/IP service interfaces across 8 ECUs. Each software release required manual verification of all interfaces — 2 engineers spending 3 days per release. With bi-weekly releases, this was consuming 6 engineer-days per month.

**Task:**
Build an automated SOME/IP regression test suite that could verify all 38 service interfaces in under 1 hour.

**Action:**
1. Analyzed the 38 interfaces: 24 were pure events (subscription + event reception), 10 were request/response methods, and 4 were fire-and-forget.
2. Built a Python framework: `someip_tester.py` that read service definitions from YAML, used Scapy to construct SOME/IP frames, and pyshark to validate responses.
3. For events: send SubscribeEventgroup, validate SubscribeAck, measure event arrival rate for 5 seconds, compare to configured cycle time ± 10%.
4. For methods: send REQUEST with known input, capture RESPONSE, validate Session ID match, validate Return Code = 0x00, validate payload deserialization.
5. Integrated into Jenkins: triggered on every ECU firmware merge. Report saved as HTML artifact.

**Result:**
All 38 interfaces validated in 42 minutes (down from 3 days). First run caught a broken SD port assignment that had been introduced by a merge conflict. Monthly testing effort reduced from 6 engineer-days to 0 (fully automated). Suite ran 47 consecutive weekly builds without false positives.

---

*Next: [03_Mini_Projects.md](03_Mini_Projects.md)*
