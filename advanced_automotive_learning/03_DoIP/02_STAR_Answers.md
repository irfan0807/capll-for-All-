# DoIP — STAR INTERVIEW STORIES
## Module 3 of 7 | 6 Ready-to-Use STAR Answers

---

## STAR-1: DoIP Gateway Routing Table Misconfiguration

**Situation:**
During system integration testing at an OEM facility, the diagnostic tester could reach the gateway ECU but could not access any internal ECUs. Every DiagnosticMessage returned DiagMsgNegativeAck with code 0x03 (Unknown Target Address).

**Task:**
Diagnose why the gateway was returning 0x03 for all internal ECU logical addresses and restore diagnostic access.

**Action:**
1. Verified TCP connection and Routing Activation were working (code 0x10 = success). The gateway itself was reachable.
2. Tried physical address 0x0010 (BCM), 0x0020 (ADAS), 0x0030 (Instrument). All returned NACK 0x03.
3. Requested the gateway's routing table via EntityStatusRequest. Found only one entry: 0x0E00 (gateway itself).
4. Root cause: the gateway's ARXML had been regenerated during a BSW update, but the `<DOIP-ROUTING-TABLE>` section was left empty — the developer had forgotten to re-import the ECU routing assignments from the system ARXML.
5. Re-imported the routing table ARXML and rebuilt gateway BSW. 12 ECU entries populated correctly.

**Result:**
All internal ECUs accessible within 20 minutes. OEM diagnostic session resumed. Routing table re-import was added as a mandatory step to the BSW regeneration checklist, preventing recurrence on 5 future releases.

---

## STAR-2: Race Condition in DoIP During ECU Power Cycle

**Situation:**
During end-of-line (EOL) testing in the production plant, the OTA flash sequence was failing with a ~15% failure rate. The failure always occurred at the same step: after ECUReset, the tester attempted to reconnect and begin the next flash block, but received no response for 30 seconds (timeout).

**Task:**
Root-cause the intermittent 15% failure rate and eliminate it before job 1 production start, which was 2 weeks away.

**Action:**
1. Captured Wireshark on the OTA workstation for 50 consecutive flash attempts. Isolated all 8 failures.
2. Pattern: after ECUReset, the gateway sent TCP RST within 100ms. The tester then attempted TCP reconnect. But the tester's retry timer was 30 seconds — and the gateway was ready in 2 seconds.
3. The tester's DoIP library was configured with `T_TCP_Reconnect = 30s` (default). Changed to `T_TCP_Reconnect = 3s`.
4. Root cause for the RST: the gateway was rebooting after reset and sending RST to clear all open TCP connections — expected behavior. The tester needed to reconnect immediately after the RST, not wait 30 seconds.
5. However: with `T_TCP_Reconnect = 3s`, gateway wasn't ready yet (boot time ~2.5s). Added `T_Boot_Grace = 2500ms` delay before reconnect.

**Result:**
0% failure rate in 200 subsequent flash attempts. EOL test cycle time reduced from average 4.5 min (with retries) to 2.1 min. Reconnect timing parameters documented in the DoIP integration guide.

---

## STAR-3: Building a Python DoIP Client for Automated Testing

**Situation:**
Our team was using a commercial diagnostic tool for all DoIP testing. The license cost was €8,000/seat, and we needed 6 simultaneous test setups. The procurement process would take 3 months. The test campaign started in 4 weeks.

**Task:**
Build a Python DoIP client that could replace the commercial tool for automated functional testing (not manual use).

**Action:**
1. Read ISO 13400-2 specification for DoIP header format, payload types, and connection states.
2. Implemented Python `DoIPClient` class: socket management, Vehicle Discovery (UDP), RoutingActivation (TCP), DiagnosticMessage send/receive, AliveCheck responder.
3. Built connection state machine: IDLE → CONNECTING → ACTIVATING → ACTIVE → CLOSING.
4. Added timeout handling, reconnect logic, error logging.
5. Wrote pytest test fixtures that used the DoIP client to execute 90 UDS test cases against the BCM — session control, security access, read/write DID, DTC management, and flashing.

**Result:**
Python DoIP client fully operational in 10 days. Replaced commercial tool for 90% of automated tests. Tool open-sourced internally, adopted by 3 other project teams. Estimated €40,000 license cost avoided. Test campaign started on schedule.

---

## STAR-4: Security Vulnerability in DoIP — Unauthenticated Tester

**Situation:**
During a cybersecurity assessment (ISO 21434 compliance review), I was tasked with testing whether the DoIP gateway properly rejected unauthorized testers. The specification said: "Only testers with IP addresses 192.168.1.0/24 shall be granted routing activation."

**Task:**
Verify the gateway correctly enforced tester IP whitelisting, and attempt to bypass it.

**Action:**
1. From a whitelist IP (192.168.1.100): RoutingActivation → code 0x10 (success). Expected.
2. From a non-whitelist IP (192.168.2.100): RoutingActivation → code 0x10 (success!). NOT expected — this was a security vulnerability.
3. Root cause: the gateway's ARXML `<CLIENT-IP-ADDRESS-FILTER>` was configured as `0.0.0.0/0` (allow all) instead of `192.168.1.0/24`. The IP filter had been disabled during development for convenience and never re-enabled.
4. Demonstrated the impact: from the non-whitelisted IP, sent DiagMsg [10 02] (enter programming session), then [11 01] (ECUReset) to the BCM. ECU reset successfully — an unauthorized client had full diagnostic access.
5. Fixed the ARXML filter. Wrote automated test: "From IP outside whitelist, RoutingActivation must return code 0x06 (denied)." Added to security test suite.

**Result:**
Vulnerability patched before production. Security test added to CI pipeline — catches the filter regression on any future ARXML regeneration. Finding classified as HIGH severity in the ISO 21434 threat model; fix documented in cybersecurity case.

---

## STAR-5: Diagnosing Flaky OBD-II Readiness Over DoIP

**Situation:**
A government emissions test station reported that 3% of vehicles failed OBD-II readiness checks via DoIP-based OBD tester. The OBD status service (0x01 PID 0x41) returned "readiness incomplete" for catalyst monitor — but only on vehicles with mileage under 50 km.

**Task:**
Determine why low-mileage vehicles failed OBD readiness and whether it was a calibration issue or a diagnostic implementation bug.

**Action:**
1. Tested a fresh vehicle (< 50 km): 0x01/0x41 returned catalyst monitor incomplete. Same vehicle at 100 km: complete.
2. This was expected behavior: catalyst readiness requires a warm-up drive cycle. Not a bug.
3. But the issue was that the DoIP OBD tester was interpreting any "incomplete" flag as a failure — not distinguishing "not yet run" from "failed."
4. Root cause: the DoIP tester software was comparing byte 0x41 PID result against a bitmask that treated "incomplete=1" as a pass for all monitors. The catalyst monitor bit was inverted in the tester's interpretation code.
5. Provided the tester vendor with the OBD-II standard (ISO 15031-5) bitmask definition. They issued a firmware update.

**Result:**
False failure rate dropped from 3% to 0.1% (legitimate incompleteness on new vehicles). Tester vendor update deployed to all emission test stations in the program. Technical bulletin issued to OEM service network.

---

## STAR-6: DoIP Parallel Diagnostics Performance Test

**Situation:**
The vehicle program required that 5 ECUs could be flashed simultaneously during OTA to reduce total update time from 45 minutes (sequential) to under 15 minutes. The DoIP gateway vendor claimed "parallel diagnostics is supported" — but no performance test had been done.

**Task:**
Design and execute a parallel DoIP diagnostics performance test to validate the OTA time requirement.

**Action:**
1. Set up 5 ECU simulators (Python scripts acting as DoIP nodes on a test bench Ethernet switch).
2. Wrote a Python OTA coordinator that opened 5 simultaneous TCP connections, each performing Routing Activation, then transferring a 50MB firmware image in parallel.
3. Measured per-ECU throughput and gateway CPU load (via ETH statistics on the SJA1110 switch).
4. First run: sequential time = 44 min. Parallel time = 28 min (not 15). Gateway was throttling connections to avoid CPU overload — it was serializing flash write operations internally.
5. Found: the gateway's internal routing serialized all downstream CAN TP frames — 5 simultaneous ECU flashes over CAN TP were queued, not truly parallel. ECUs on the Ethernet backbone could be fully parallel.
6. Revised architecture: move all OTA ECUs to Ethernet backbone (direct DoIP), keep CAN only for safety-critical functions.

**Result:**
After architecture change: 5 simultaneous Ethernet ECU flashes completed in 11 minutes (below 15-minute target). Gateway CPU load: 32% peak. Findings documented; CAN TP serialization limitation added to future architecture constraints. OTA requirement PASS.

---

*Next: [03_Mini_Projects.md](03_Mini_Projects.md)*
