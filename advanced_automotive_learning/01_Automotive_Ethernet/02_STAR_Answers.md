# AUTOMOTIVE ETHERNET — STAR INTERVIEW STORIES
## Module 1 of 7 | 7 Ready-to-Use STAR Answers

---

> **STAR Format:** Situation → Task → Action → Result
> **Rule:** Every Result must have a metric (%, time saved, severity avoided, etc.)
> **Practice:** Say each answer aloud 3 times. Target: 2–3 minutes per answer.

---

## STAR-1: PHY Link Not Coming Up

**Context:** Hardware bring-up issue during board validation

**Situation:**
During the hardware bring-up phase of an ADAS domain controller project, the Automotive Ethernet link between the domain controller and the RADAR ECU refused to establish. The link LED never turned on, and LINK_STATUS register via MDIO was permanently 0. This was discovered 48 hours before a critical customer demo to the OEM.

**Task:**
I was assigned as the sole validation engineer to root-cause the link failure and provide a fix or workaround within 24 hours.

**Action:**
1. First I verified cables — physically confirmed twisted pair connection and continuity with a multimeter.
2. Checked TJA1100 register 0x00 (Basic Control) via MDIO read — both PHYs returned the same value for the master/slave bit: both were set to Master mode (bit 14 = 1 in extended register 0x17).
3. Cross-referenced with the ARXML startup configuration — found that a developer had copied the master ECU config to the slave ECU config file and never changed the MDIO master/slave parameter.
4. Changed one ECU's ARXML `<MASTER-SLAVE-MODE>SLAVE</MASTER-SLAVE-MODE>` entry and recompiled the BSW configuration.
5. Wrote a test script that reads both PHY MDIO register 0x17 at startup and reports master/slave assignment — added to the bring-up checklist.

**Result:**
Link established within 2 minutes of the fix. Customer demo went ahead on schedule. The MDIO read test was added to the permanent hardware bring-up checklist, preventing recurrence on 3 subsequent ECU variants.

---

## STAR-2: Intermittent Ethernet Link Drop on Vehicle Test

**Context:** Vehicle-level testing on a prototype

**Situation:**
During vehicle-level validation testing on a highway test track, the ADAS domain controller was losing its Ethernet link to the front camera ECU intermittently — approximately once every 45 minutes of driving. The link recovered within 2 seconds each time, but during that window, the AEB function became unavailable, which is a safety-critical failure.

**Task:**
Root-cause the intermittent link loss, which had resisted 3 weeks of investigation by the team before I was brought in.

**Action:**
1. Attached a Wireshark capture laptop via port mirroring on the SJA1110 switch and drove 3 laps of the test track.
2. Identified correlation: link drops occurred exclusively when the vehicle drove over a specific rough section of road — a series of speed bumps in the parking lot.
3. Compared vibration frequency profile (from the vehicle IMU log) with the timing of link drops — matched at 18–22 Hz resonance band.
4. Inspected the physical wire harness — found that the twisted pair between the camera and domain controller passed over a bracket with a sharp metal edge. Vibration at 18–22 Hz caused the cable to rub and momentarily short.
5. Worked with the harness team to reroute the cable 8cm away from the bracket with a clip. Proposed additional strain relief near the ECU connector.

**Result:**
Zero link drops in 200 subsequent kilometers of test track driving. The root cause was documented in a lessons-learned report. Cable routing guidelines for Automotive Ethernet links were added to the harness design checklist used by the hardware team.

---

## STAR-3: VLAN Misconfiguration Blocking Diagnostic Access

**Context:** System integration testing

**Situation:**
During system integration testing at an OEM facility, the diagnostic tester (using a VN5640 + CANoe) could not establish a DoIP connection to any ECU through the central Ethernet switch. The vehicle had been delivered with freshly flashed ECUs and this was the first diagnostic session attempt.

**Task:**
Investigate and resolve the DoIP connectivity issue within one day so the OEM could begin their diagnostic acceptance tests.

**Action:**
1. Opened Wireshark on the diagnostic tester's Ethernet port. Sent a DoIP Vehicle Identification Request (UDP broadcast to 255.255.255.255:13400). Received no response.
2. Applied filter `doip || udp.port == 13400` — tester's request packets were visible on TX but no response on RX.
3. Added a second Wireshark instance on the switch mirror port. Confirmed the tester's UDP broadcast was arriving at the switch, but the DoIP gateway ECU was not responding.
4. Checked the switch port VLAN table on the SJA1110 via SPI configuration dump. Found: tester port was on VLAN 30 (powertrain) but the DoIP gateway was on VLAN 20 (diagnostics). Switch had strict VLAN isolation — no inter-VLAN routing for UDP broadcasts.
5. Corrected the tester port VLAN assignment in the switch configuration from VLAN 30 to VLAN 20. Reloaded switch configuration.

**Result:**
DoIP connection established immediately after the fix. OEM began diagnostic tests on schedule. I documented the VLAN assignment verification as a mandatory pre-test checklist item for all system integration starts. This same issue was caught proactively on two later vehicle programs before delivery.

---

## STAR-4: Automating Ethernet Link Quality Tests

**Context:** Regression testing bottleneck

**Situation:**
Our team was spending 6 hours per week manually executing Ethernet link quality tests on each software build — checking PHY link establishment time, link drop recovery time, VLAN filtering correctness, and gPTP sync accuracy. This was repetitive and error-prone; two regression bugs had been missed because the manual test was skipped under schedule pressure.

**Task:**
Design and implement an automated Ethernet test suite that could run on our CI pipeline without manual intervention.

**Action:**
1. Mapped all 18 manual Ethernet test cases to automation requirements — identified which could be automated via Python + pyshark vs. which needed CANoe scripting.
2. For PHY link timing: wrote Python script that power-cycled the ECU via relay control, timestamped UDP packet arrival at link restoration, and compared against 300ms threshold.
3. For VLAN filtering: wrote script that injected VLAN-tagged frames using Scapy, captured on the target port, verified absence of wrong-VLAN frames.
4. For gPTP: parsed ptp dissector output from pyshark, extracted sync offset over 30 seconds, computed mean and max offset.
5. Integrated all 18 tests into Jenkins pipeline — triggered on every software merge to main branch.

**Result:**
Automated suite ran in 22 minutes (vs 6 hours manual). First run caught a gPTP regression where a config change had bumped grandmaster priority causing offset to exceed 5µs. Bug was fixed before reaching integration branch. Zero Ethernet regression bugs reached the OEM in subsequent 6 months.

---

## STAR-5: Explaining TSN to a Non-Technical Project Manager

**Context:** Project planning meeting

**Situation:**
The project manager for our ADAS Ethernet backbone program had approved a schedule that did not include time for TSN validation. When I raised this in a planning meeting, the PM pushed back: "TSN is just a protocol — we test protocols in the protocol suite. Why does it need its own track?" I needed to justify an additional 3-week test slot without overwhelming a non-technical audience.

**Task:**
Convince the PM to allocate time for TSN-specific testing, with a clear business case.

**Action:**
1. Avoided protocol jargon — used an analogy: "Imagine the Ethernet switch is a highway. Without TSN, all cars (data packets) share lanes with no traffic rules. A heavy truck (OTA update) can block an ambulance (AEB brake command). TSN gives the ambulance a dedicated lane, guaranteed to be clear."
2. Presented a one-page risk analysis: camera-to-controller latency without TSN = 0–15ms variable; with TSN = guaranteed < 2ms. AEB requires < 5ms. Without TSN, latency spike of 15ms means AEB fires 10ms too late.
3. Calculated cost of finding this in a vehicle test vs in HIL: vehicle test = 2 days + test track booking + engineer travel = ~€15,000. HIL test = 3 hours, €200.
4. Proposed a structured 3-week TSN test track on HIL bench only — no vehicle time needed.

**Result:**
PM approved the 3-week TSN validation track. We found and fixed a TAS gate scheduling error that would have caused 12ms periodic ADAS latency spikes. ISO 26262 safety analysis was updated accordingly.

---

## STAR-6: Root-Causing a gPTP Sync Failure

**Context:** Bench integration testing

**Situation:**
During integration testing of an ADAS domain controller with 4 sensor ECUs, the gPTP synchronization was working correctly for 3 ECUs but one camera ECU consistently showed a sync offset of 8–12ms (well above the 1µs target). This was causing timestamp misalignment between the camera and radar data fusion algorithm, producing phantom object detections.

**Task:**
Identify why one camera ECU had incorrect gPTP synchronization and provide a fix.

**Action:**
1. Captured Wireshark on all 5 ECUs simultaneously using port mirroring. Applied filter `ptp.v2.messageid == 0` (Sync frames).
2. Compared Follow_Up correction field values. The problematic camera ECU had a correction field of 0 in all received Follow_Up messages. The other ECUs had non-zero correction fields reflecting physical propagation delay.
3. Traced the signal path — the camera ECU was connected through an additional unmanaged switch (added temporarily during bench setup) that was not gPTP-aware. This switch was not forwarding the correction field (transparent clock function) and stripping timing correction.
4. Replaced the unmanaged switch with a gPTP-aware transparent clock (using a second SJA1110 configured in transparent clock mode).
5. Verified: after replacement, camera ECU sync offset dropped to 180ns.

**Result:**
Phantom detections disappeared. Camera-radar fusion accuracy improved to within spec. Root cause documented: all Ethernet switches in gPTP network must be gPTP-aware transparent or boundary clocks. This became a hardware selection requirement for all future projects.

---

## STAR-7: Identifying a Safety-Critical Latency Bug Under Load

**Context:** Load and stress testing

**Situation:**
During stress testing of the ADAS Ethernet backbone (generating maximum SOME/IP traffic from all 8 ECUs simultaneously), the AEB control loop was exhibiting 18–25ms end-to-end latency instead of the required < 5ms. This was only visible under full load — at normal load, latency was fine.

**Task:**
Identify the cause of latency increase under load and whether it represented a real-world safety risk.

**Action:**
1. Captured Wireshark under both normal and full-load conditions. Applied filter `someip.serviceid == 0x0101` (AEB command service).
2. Compared packet timestamps — normal load: < 2ms; full load: 18–25ms. The delay was in the Ethernet switch, not in the ECU processing.
3. Inspected TSN TAS configuration: the gate schedule period was 2ms, with ADAS queue (Q7) assigned only 100µs out of 2000µs (5%). At full load, the ADAS queue was starved — it had to wait multiple cycles before its gate opened.
4. Calculated correct ADAS bandwidth allocation: AEB sends 200-byte frames at 200Hz = 40 kbps. At 100 Mbps, this needs 0.04% of bandwidth — not 5%. The issue was other ADAS sub-services also mapped to Q7, consuming the 100µs window.
5. Restructured queue allocation: AEB command = Q7 (safety-critical), other ADAS monitoring = Q5. Increased Q7 gate window to 300µs.

**Result:**
AEB latency under full load: 1.8ms (within spec). Safety case was updated to document the tested worst-case latency. The TAS queue mapping was added to the ADAS platform standard, preventing recurrence on 4 future ECU variants.

---

*Next: [03_Mini_Projects.md](03_Mini_Projects.md)*
