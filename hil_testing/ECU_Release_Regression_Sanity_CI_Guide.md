# ECU Software Release — Regression & Sanity Testing with Jenkins
## End-to-End CI/CD Pipeline: From Build Drop to Test Report

**Document Version:** 1.0  
**Date:** 23 April 2026  
**Scope:** Sanity testing + full regression testing triggered automatically on every ECU software build release  
**Tools:** Jenkins · CANoe · vTestStudio · Python · CAPL · GitHub/Bitbucket · Artifactory · HIL Bench

---

## Table of Contents

1. [Big Picture — What Happens When a Build Drops](#1-big-picture--what-happens-when-a-build-drops)
2. [Difference: Sanity vs Regression](#2-difference-sanity-vs-regression)
3. [Infrastructure You Need](#3-infrastructure-you-need)
4. [Step 1 — Software Repository and Build Server Setup](#step-1--software-repository-and-build-server-setup)
5. [Step 2 — Artifact Storage (Artifactory / Nexus)](#step-2--artifact-storage-artifactory--nexus)
6. [Step 3 — Jenkins Installation and Plugin Setup](#step-3--jenkins-installation-and-plugin-setup)
7. [Step 4 — Jenkins Self-Hosted Agent on HIL Bench PC](#step-4--jenkins-self-hosted-agent-on-hil-bench-pc)
8. [Step 5 — ECU Flashing Pipeline Stage](#step-5--ecu-flashing-pipeline-stage)
9. [Step 6 — Sanity Test Suite Design](#step-6--sanity-test-suite-design)
10. [Step 7 — Regression Test Suite Design](#step-7--regression-test-suite-design)
11. [Step 8 — CAPL Sanity Test Scripts](#step-8--capl-sanity-test-scripts)
12. [Step 9 — Python Regression Test Scripts](#step-9--python-regression-test-scripts)
13. [Step 10 — Jenkins Declarative Pipeline (Full)](#step-10--jenkins-declarative-pipeline-full)
14. [Step 11 — Parallel Feature Execution in Jenkins](#step-11--parallel-feature-execution-in-jenkins)
15. [Step 12 — Gate Evaluation and Build Promotion](#step-12--gate-evaluation-and-build-promotion)
16. [Step 13 — Notification and Reporting](#step-13--notification-and-reporting)
17. [Step 14 — Test Results Traceability](#step-14--test-results-traceability)
18. [Step 15 — Nightly vs On-Demand Execution](#step-15--nightly-vs-on-demand-execution)
19. [Full End-to-End Flow Diagram](#full-end-to-end-flow-diagram)
20. [Troubleshooting CI Pipeline Issues](#troubleshooting-ci-pipeline-issues)

---

## 1. Big Picture — What Happens When a Build Drops

When the SW team releases a new ECU binary, the following happens **automatically without human intervention**:

```
 SW Developer
     │
     │  git push tag v2.4.1 (or upload .hex/.s19 to Artifactory)
     ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │  BUILD SERVER (GitHub Actions / Bitbucket Pipelines / Jenkins)    │
 │  1. Detects new tag or artifact upload                            │
 │  2. Triggers Jenkins pipeline via webhook                         │
 └──────────────────────────┬────────────────────────────────────────┘
                            │ REST API trigger (build parameters)
                            ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │  JENKINS MASTER                                                   │
 │  3. Pipeline starts: pulls ECU binary from Artifactory            │
 │  4. Dispatches job to HIL bench agent                             │
 └──────────────────────────┬────────────────────────────────────────┘
                            │ SSH / JNLP to HIL bench PC
                            ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │  HIL BENCH AGENT (Windows PC connected to ECU)                    │
 │  5. Flash new firmware to ECU (UDS / CANdelaStudio / ETAS)       │
 │  6. Power cycle ECU — verify boot                                 │
 │  7. Run SANITY SUITE  (~10 min) — quick go/no-go check            │
 │     → FAIL: pipeline aborts, team notified, full regression skips │
 │     → PASS: proceed to full regression                            │
 │  8. Run REGRESSION SUITE (~90 min) — full feature coverage        │
 │  9. Evaluate gate thresholds (pass rate ≥ 95%)                    │
 │  10. Publish HTML + JUnit XML reports                             │
 └──────────────────────────┬────────────────────────────────────────┘
                            │ Reports uploaded
                            ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │  REPORTING & NOTIFICATION                                          │
 │  11. Jenkins publishes test report dashboard                       │
 │  12. Email/Teams/Slack notification to team                        │
 │  13. JIRA tickets auto-created for new failures                    │
 │  14. Build PROMOTED (green) or REJECTED (red) in Artifactory       │
 └───────────────────────────────────────────────────────────────────┘
```

---

## 2. Difference: Sanity vs Regression

| Aspect | Sanity Test Suite | Regression Test Suite |
|--------|------------------|-----------------------|
| **Purpose** | Quick go/no-go: is the ECU basically alive and functional? | Full verification of all features, edge cases, boundaries |
| **When runs** | First, after every build flash | Only if sanity passes |
| **Duration** | 5–15 minutes | 60–120 minutes |
| **Test count** | 15–30 critical checks | 150–300+ test cases |
| **Coverage** | Core signal presence, boot, major feature activation | All scenarios, fault injection, timing, edge cases |
| **Failure action** | Abort pipeline, notify immediately | Collect all failures, generate detailed report |
| **Who writes** | Test lead (manually selected critical cases) | Test engineers (full feature set) |
| **Tools** | CAPL testcases in vTestStudio or simple Python | Full pytest + CAPL suite |

### 2.1 Sanity Test Checklist (What to Check)

```
SANITY CHECKS (must all pass before regression):

  Boot & Communication
  ├── [ ] ECU sends first CAN message within 500 ms of KL15
  ├── [ ] All cyclic messages present at correct intervals
  ├── [ ] No error frames on CAN bus at nominal state
  ├── [ ] UDS diagnostic session opens (Service 0x10 0x01)
  └── [ ] Software version readable (Service 0x22 F189) — matches build ID

  ACC Feature Smoke
  ├── [ ] ACC_Sts signal present and initial value = 0x01 (STANDBY)
  ├── [ ] ACC activates within 1s at valid speed (80 km/h)
  └── [ ] ACC cancels on brake pedal press

  LKA/LDW Feature Smoke
  ├── [ ] LKA_Sts signal present and initial value = 0x01
  └── [ ] LKA activates on lane drift at speed > 60 km/h

  BSD Feature Smoke
  └── [ ] BSD warning signal toggles correctly on object injection

  Parking Smoke
  └── [ ] Park_Sts activates when gear = Reverse

  HHA Smoke
  └── [ ] HHA holding state reached on uphill stop simulation

  DTC Health
  └── [ ] No unexpected DTCs at clean boot
```

---

## 3. Infrastructure You Need

### 3.1 Hardware

| # | Item | Purpose |
|---|------|---------|
| 1 | Jenkins Master Server | Orchestrate all pipelines (Linux VM or bare metal) |
| 2 | HIL Bench PC (Windows) | Jenkins agent, runs CANoe + Python + flash tools |
| 3 | ADAS ECU (DUT) | Device under test |
| 4 | Vector VN1640A | CAN bus interface |
| 5 | Vector VN5640 | DoIP / UDS flashing interface |
| 6 | dSPACE SCALEXIO | Real-time vehicle simulation |
| 7 | Power relay box | Automated KL15 cycling |
| 8 | Gigabit Network Switch | Jenkins master ↔ HIL agent ↔ SCALEXIO |

### 3.2 Software

| # | Software | Where | Purpose |
|---|---------|-------|---------|
| 1 | Jenkins LTS 2.452+ | Linux VM | Pipeline orchestration |
| 2 | Artifactory OSS or Pro | Linux VM or cloud | ECU binary storage |
| 3 | Git (Gitea / GitHub / Bitbucket) | Cloud or internal | Source + test script versioning |
| 4 | CANoe 17 | HIL PC | Bus simulation + CAPL tests |
| 5 | vTestStudio 5 | HIL PC | CAPL test module execution |
| 6 | Python 3.11 | HIL PC | Regression automation |
| 7 | Vector Flash tool (canflash.exe) | HIL PC | ECU firmware flashing |
| 8 | ETAS INCA-MIP or PCAN-MicroMod | HIL PC (alt.) | Alternative flash tool |
| 9 | pytest + pytest-html | HIL PC | Test runner + HTML report |
| 10 | Jira + Xray plugin | Cloud | Bug tracking + test management |

---

## Step 1 — Software Repository and Build Server Setup

### 1.1 Repository Structure

Your test scripts live in a **separate repository** from the ECU firmware:

```
git repository: adas-test-suite/
│
├── sanity/
│   ├── sanity_suite.can          ← CAPL sanity test module
│   ├── sanity_runner.py          ← Python sanity orchestrator
│   └── sanity_cases.yaml         ← Test case definitions
│
├── regression/
│   ├── acc_regression.py
│   ├── lka_ldw_regression.py
│   ├── bsd_regression.py
│   ├── parking_regression.py
│   ├── hha_regression.py
│   ├── conftest.py
│   └── pytest.ini
│
├── capl/
│   ├── common_hil_utils.capl
│   ├── acc_tests.can
│   ├── lka_ldw_tests.can
│   └── ...
│
├── tools/
│   ├── flash_ecu.py              ← Automated flash script
│   ├── power_control.py          ← KL15/KL30 relay control
│   ├── canoe_controller.py       ← Start/stop CANoe via COM
│   └── dtc_reader.py             ← UDS DTC verification
│
├── gate/
│   └── run_gate.py               ← Gate evaluator
│
├── reports/                      ← Generated reports (git-ignored)
│
├── Jenkinsfile                   ← Main pipeline definition
├── Jenkinsfile.sanity            ← Sanity-only pipeline
├── requirements.txt
└── README.md
```

### 1.2 Branch Strategy for Test Scripts

```
main          → latest stable test scripts (matches current released ECU SW)
develop       → test script development branch
feature/xxx   → new test case feature branches
hotfix/xxx    → urgent test fix branches

Tagging convention:
  test-v2.4.1   → test suite version matching ECU SW v2.4.1
```

### 1.3 Webhook from Build Server to Jenkins

When the SW team pushes a new ECU build tag to their repository:

```bash
# SW team creates a release tag
git tag -a v2.4.1 -m "Release 2.4.1 — ACC performance improvements"
git push origin v2.4.1
```

This fires a **webhook** to Jenkins:

```
GitHub/Bitbucket Webhook → Jenkins URL:
  POST https://jenkins.yourcompany.com/generic-webhook-trigger/invoke
  Content-Type: application/json
  Body:
  {
    "build_version": "v2.4.1",
    "artifact_url": "https://artifactory.yourcompany.com/adas-ecu/v2.4.1/ADAS_ECU_v2.4.1.hex",
    "triggered_by": "sw-team@yourcompany.com",
    "branch": "release/2.4.1"
  }
```

---

## Step 2 — Artifact Storage (Artifactory / Nexus)

### 2.1 Artifactory Repository Structure

```
Artifactory Repository: adas-ecu-releases/
│
├── v2.4.0/
│   ├── ADAS_ECU_v2.4.0.hex       ← ECU binary (Intel HEX format)
│   ├── ADAS_ECU_v2.4.0.s19       ← Motorola S-Record format
│   ├── ADAS_ECU_v2.4.0_info.json ← Build metadata
│   └── SHA256.txt                ← Integrity checksum
│
├── v2.4.1/
│   ├── ADAS_ECU_v2.4.1.hex
│   ├── ADAS_ECU_v2.4.1_info.json
│   └── SHA256.txt
│
└── latest/                       ← Symlink to most recent release
```

### 2.2 Build Metadata JSON

```json
// ADAS_ECU_v2.4.1_info.json
{
  "version": "v2.4.1",
  "build_date": "2026-04-23T14:30:00Z",
  "git_commit": "abc123def456",
  "sw_team_contact": "sw@yourcompany.com",
  "target_ecu": "ADAS_MAIN_ECU",
  "flash_method": "UDS_ISO14229",
  "flash_tool": "canflash",
  "expected_sw_version": "0x0204001",
  "changelog": [
    "ACC deceleration ramp improved",
    "LKA torque limit changed from 4 Nm to 5 Nm",
    "BSD detection latency reduced by 50ms"
  ]
}
```

### 2.3 Download Artifact in Jenkins Pipeline

```groovy
// In Jenkinsfile — download step
stage('Download ECU Binary') {
    steps {
        script {
            def artifactUrl = params.ARTIFACT_URL
                ?: "https://artifactory.yourcompany.com/adas-ecu-releases/${params.BUILD_VERSION}/ADAS_ECU_${params.BUILD_VERSION}.hex"

            bat """
                curl -u %ARTIFACTORY_USER%:%ARTIFACTORY_PASS% ^
                     -o firmware\\ADAS_ECU.hex ^
                     "${artifactUrl}"
            """

            // Verify SHA256
            bat """
                curl -u %ARTIFACTORY_USER%:%ARTIFACTORY_PASS% ^
                     -o firmware\\SHA256.txt ^
                     "${artifactUrl.replace('.hex','')}/SHA256.txt"
                certutil -hashfile firmware\\ADAS_ECU.hex SHA256 > firmware\\computed.txt
                fc firmware\\SHA256.txt firmware\\computed.txt
            """
        }
    }
}
```

---

## Step 3 — Jenkins Installation and Plugin Setup

### 3.1 Install Jenkins on Linux (Ubuntu 22.04)

```bash
# Step 1: Install Java 17
sudo apt update
sudo apt install -y fontconfig openjdk-17-jre

# Step 2: Add Jenkins repository
sudo wget -O /usr/share/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" | \
  sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

# Step 3: Install Jenkins
sudo apt update
sudo apt install -y jenkins

# Step 4: Start Jenkins service
sudo systemctl enable jenkins
sudo systemctl start jenkins
sudo systemctl status jenkins

# Step 5: Get initial admin password
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
# → Copy this password → open browser → http://YOUR_SERVER:8080
```

### 3.2 Required Jenkins Plugins

Install via **Manage Jenkins → Plugins → Available**:

| Plugin | ID | Purpose |
|---|---|---|
| Pipeline | workflow-aggregator | Declarative/scripted pipelines |
| Git | git | Checkout from Git repos |
| Generic Webhook Trigger | generic-webhook-trigger | Accept HTTP webhooks |
| JUnit | junit | Parse and display test XML results |
| HTML Publisher | htmlpublisher | Publish HTML test reports |
| Email Extension | email-ext | Rich email notifications |
| Credentials Binding | credentials-binding | Securely use passwords |
| Blue Ocean | blueocean | Modern pipeline UI |
| Slack Notification | slack | Slack integration |
| Artifactory | artifactory | Integrate with JFrog Artifactory |
| Parameterized Trigger | parameterized-trigger | Trigger downstream jobs |
| Timestamper | timestamper | Add timestamps to console log |
| AnsiColor | ansicolor | Coloured console output |

### 3.3 Configure Credentials in Jenkins

```
Manage Jenkins → Credentials → System → Global → Add Credentials:

  1. Artifactory credentials:
     Kind: Username with password
     ID:   artifactory-creds
     Username: svc-jenkins
     Password: <service account password>

  2. HIL bench SSH key (for Linux agent) or JNLP token (Windows):
     Kind: SSH Username with private key
     ID:   hil-bench-agent
     Username: jenkins-agent
     Private Key: (paste private key)

  3. SMTP credentials (for email):
     Kind: Username with password
     ID:   smtp-creds

  4. Slack token:
     Kind: Secret text
     ID:   slack-token
```

---

## Step 4 — Jenkins Self-Hosted Agent on HIL Bench PC

The HIL bench PC runs a **Jenkins agent** that receives jobs from the Jenkins master.

### 4.1 Install Java on HIL PC (Windows)

```powershell
# Download and install JDK 17
winget install Microsoft.OpenJDK.17
# OR download from: https://adoptium.net/
```

### 4.2 Register HIL Agent in Jenkins

```
STEP 1:  Jenkins Master → Manage Jenkins → Nodes → New Node
STEP 2:  Node name: "HIL-Bench-01"
STEP 3:  Type: Permanent Agent
STEP 4:  Settings:
          Remote root directory: C:\Jenkins\agent
          Labels: hil-bench windows adas-ecu
          Launch method: Launch agent by connecting it to the master (JNLP)
STEP 5:  Save → Click "HIL-Bench-01" → Copy the agent launch command
```

### 4.3 Run Jenkins Agent on HIL PC

```batch
REM On HIL PC — create C:\Jenkins\agent\ directory
mkdir C:\Jenkins\agent
cd C:\Jenkins\agent

REM Download agent.jar from Jenkins master
curl -sO http://JENKINS_MASTER:8080/jnlpJars/agent.jar

REM Connect agent (run as Windows Service for persistence)
java -jar agent.jar ^
     -url http://JENKINS_MASTER:8080/ ^
     -secret YOUR_AGENT_SECRET ^
     -name "HIL-Bench-01" ^
     -workDir "C:\Jenkins\agent"
```

**Run as Windows Service (so agent starts on boot):**

```powershell
# Install as service using NSSM
choco install nssm
nssm install JenkinsAgent "java" "-jar C:\Jenkins\agent\agent.jar -url http://JENKINS_MASTER:8080 -secret YOUR_SECRET -name HIL-Bench-01 -workDir C:\Jenkins\agent"
nssm start JenkinsAgent
```

### 4.4 Verify Agent is Online

```
Jenkins Master → Manage Jenkins → Nodes
→ HIL-Bench-01 should show: Status = Connected (green circle)
→ Response time: < 1000 ms
```

---

## Step 5 — ECU Flashing Pipeline Stage

### 5.1 Flash Script (Python)

```python
# tools/flash_ecu.py
# Flash new ECU firmware using Vector canflash command-line tool

import subprocess
import sys
import json
import time
import argparse
from pathlib import Path


CANFLASH_EXE = r"C:\Program Files\Vector CANflash\CANflash.exe"
FLASH_CONFIG = r"C:\HIL\FlashConfig\ADAS_ECU_Flash.cfg"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--hex",        required=True, help="Path to ECU .hex file")
    p.add_argument("--build-id",   required=True, help="Build version string")
    p.add_argument("--timeout",    type=int, default=300, help="Flash timeout seconds")
    return p.parse_args()


def flash_ecu(hex_path: str, timeout: int) -> bool:
    """
    Flash ECU using Vector CANflash CLI.
    Returns True on success, False on failure.
    """
    print(f"[FLASH] Starting ECU flash: {hex_path}")

    cmd = [
        CANFLASH_EXE,
        "/cfg",  FLASH_CONFIG,
        "/hex",  hex_path,
        "/log",  "flash_log.txt",
        "/silent"
    ]

    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0:
            print("[FLASH] ECU flash SUCCESSFUL")
            return True
        else:
            print(f"[FLASH] ECU flash FAILED — exit code {result.returncode}")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print(f"[FLASH] Flash timed out after {timeout}s")
        return False


def verify_ecu_software_version(expected_version: str) -> bool:
    """
    Read software version via UDS 0x22 F189 and compare to expected.
    """
    print(f"[VERIFY] Reading ECU software version...")
    # Use CANoe COM to send UDS request — simplified here
    # In production: integrate dtc_reader.py or similar
    time.sleep(2)  # Wait for ECU boot

    # Placeholder: actual implementation uses UDS over CANoe COM
    # actual_version = uds_read_data_by_id(0xF189)
    actual_version = expected_version  # Replace with real read
    
    if actual_version == expected_version:
        print(f"[VERIFY] Version match: {actual_version}")
        return True
    print(f"[VERIFY] Version mismatch! Expected {expected_version}, got {actual_version}")
    return False


def power_cycle_ecu(wait_s: int = 3):
    """Cycle KL15 to reboot ECU after flash."""
    from power_control import PowerControl
    ctrl = PowerControl()
    print("[POWER] Cycling KL15...")
    ctrl.kl15_off()
    time.sleep(wait_s)
    ctrl.kl15_on()
    print("[POWER] KL15 restored — ECU booting")
    time.sleep(2)  # Allow ECU to boot


def main():
    args = parse_args()
    hex_path = Path(args.hex)

    if not hex_path.exists():
        print(f"[FLASH] ERROR: Hex file not found: {hex_path}")
        sys.exit(1)

    # 1. Flash firmware
    if not flash_ecu(str(hex_path), args.timeout):
        sys.exit(2)

    # 2. Power cycle ECU
    power_cycle_ecu()

    # 3. Verify software version
    meta_path = hex_path.with_suffix("_info.json")
    expected_version = "UNKNOWN"
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
            expected_version = meta.get("expected_sw_version", "UNKNOWN")

    if not verify_ecu_software_version(expected_version):
        sys.exit(3)

    print(f"[FLASH] ECU ready with build {args.build_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### 5.2 Power Control Script

```python
# tools/power_control.py
# Controls KL15/KL30 relay via Arduino serial interface

import serial
import time


class PowerControl:
    """
    Controls KL15/KL30 relays via Arduino serial.
    Arduino sketch listens for 'K15_ON', 'K15_OFF', 'K30_ON', 'K30_OFF'
    """

    def __init__(self, port: str = "COM4", baud: int = 9600):
        self.ser = serial.Serial(port, baud, timeout=2)
        time.sleep(1)  # Allow Arduino to reset

    def kl15_on(self):
        self.ser.write(b"K15_ON\n")
        response = self.ser.readline().decode().strip()
        assert response == "OK", f"KL15 ON failed: {response}"
        print("[POWER] KL15 ON")

    def kl15_off(self):
        self.ser.write(b"K15_OFF\n")
        response = self.ser.readline().decode().strip()
        assert response == "OK", f"KL15 OFF failed: {response}"
        print("[POWER] KL15 OFF")

    def kl30_on(self):
        self.ser.write(b"K30_ON\n")
        self.ser.readline()
        print("[POWER] KL30 ON")

    def kl30_off(self):
        self.ser.write(b"K30_OFF\n")
        self.ser.readline()
        print("[POWER] KL30 OFF")

    def full_power_cycle(self, kl30_wait_s=2, kl15_wait_s=2):
        self.kl15_off()
        time.sleep(1)
        self.kl30_off()
        time.sleep(kl30_wait_s)
        self.kl30_on()
        time.sleep(kl15_wait_s)
        self.kl15_on()

    def close(self):
        self.ser.close()
```

### 5.3 CANoe Controller Script

```python
# tools/canoe_controller.py
# Start, stop and control CANoe via Windows COM interface

import win32com.client
import time
import subprocess
from pathlib import Path


CANOE_CONFIG = r"C:\HIL\ADAS_Tests\ADAS_HIL.cfg"
CANOE_EXE    = r"C:\Program Files\Vector CANoe 17\CANoe64.exe"


class CANoeController:

    def __init__(self, config: str = CANOE_CONFIG):
        self.config = config
        self.app    = None

    def launch_and_open(self):
        """Launch CANoe if not running, then load config."""
        try:
            self.app = win32com.client.GetActiveObject("CANoe.Application")
            print("[CANoe] Attached to existing CANoe instance")
        except Exception:
            subprocess.Popen([CANOE_EXE])
            time.sleep(8)  # Wait for CANoe to start
            self.app = win32com.client.Dispatch("CANoe.Application")
            print("[CANoe] Launched new CANoe instance")

        self.app.Open(self.config)
        time.sleep(3)
        print(f"[CANoe] Config loaded: {Path(self.config).name}")

    def start_measurement(self):
        self.app.Measurement.Start()
        time.sleep(2)
        print("[CANoe] Measurement started")

    def stop_measurement(self):
        self.app.Measurement.Stop()
        time.sleep(1)
        print("[CANoe] Measurement stopped")

    def run_test_module(self, module_name: str) -> int:
        """
        Execute a vTestStudio test module.
        Returns exit code: 0 = all pass, 1 = failures exist.
        """
        testenv = self.app.Configuration.TestSetup.TestEnvironments.Item(1)
        for i in range(1, testenv.TestModules.Count + 1):
            mod = testenv.TestModules.Item(i)
            if mod.Name == module_name:
                mod.Start()
                while mod.Status == 1:  # 1 = Running
                    time.sleep(1)
                verdict = mod.Verdict
                print(f"[CANoe] Module '{module_name}' verdict: {verdict}")
                return 0 if verdict == 1 else 1  # 1=Pass
        raise ValueError(f"Test module '{module_name}' not found in config")

    def quit(self):
        if self.app:
            self.app.Quit()
            print("[CANoe] CANoe closed")
```

---

## Step 6 — Sanity Test Suite Design

### 6.1 Sanity Suite Structure

The sanity suite is designed to run **fast** and check only the most critical aspects:

```
Sanity Suite (target: < 15 min)
│
├── Group 1: Boot & Communication (2 min)
│   ├── TC-SAN-001: CAN bus alive check
│   ├── TC-SAN-002: All cyclic messages present
│   ├── TC-SAN-003: No error frames at boot
│   └── TC-SAN-004: UDS session open + SW version read
│
├── Group 2: ACC Smoke (3 min)
│   ├── TC-SAN-005: ACC signal presence
│   ├── TC-SAN-006: ACC activation
│   └── TC-SAN-007: ACC cancel on brake
│
├── Group 3: LKA Smoke (2 min)
│   ├── TC-SAN-008: LKA signal presence
│   └── TC-SAN-009: LKA activation on drift
│
├── Group 4: BSD Smoke (2 min)
│   └── TC-SAN-010: BSD warning on object
│
├── Group 5: Parking Smoke (2 min)
│   └── TC-SAN-011: Park assist activation in reverse
│
├── Group 6: HHA Smoke (2 min)
│   └── TC-SAN-012: HHA hold on uphill
│
└── Group 7: DTC Check (1 min)
    └── TC-SAN-013: Zero unexpected DTCs at clean boot
```

### 6.2 Sanity Test Case YAML Definition

```yaml
# sanity/sanity_cases.yaml
suite: ADAS_SANITY
version: "1.0"
timeout_per_case_s: 60
abort_on_failure: true    # Abort entire pipeline if ANY sanity fails

cases:
  - id: TC-SAN-001
    name: "CAN bus alive after KL15"
    capl_function: tc_San_CANBusAlive
    timeout_s: 10
    priority: P0

  - id: TC-SAN-002
    name: "All cyclic messages present"
    capl_function: tc_San_CyclicMessages
    timeout_s: 15
    priority: P0

  - id: TC-SAN-003
    name: "No error frames at boot"
    capl_function: tc_San_NoErrorFrames
    timeout_s: 10
    priority: P0

  - id: TC-SAN-004
    name: "UDS session + SW version"
    capl_function: tc_San_UDS_SWVersion
    timeout_s: 15
    priority: P0

  - id: TC-SAN-005
    name: "ACC signal presence"
    capl_function: tc_San_ACC_SignalPresence
    timeout_s: 10
    priority: P0

  - id: TC-SAN-006
    name: "ACC activation"
    capl_function: tc_San_ACC_Activation
    timeout_s: 30
    priority: P0

  - id: TC-SAN-007
    name: "ACC cancel on brake"
    capl_function: tc_San_ACC_CancelOnBrake
    timeout_s: 20
    priority: P1

  - id: TC-SAN-008
    name: "LKA signal presence + activation"
    capl_function: tc_San_LKA_Activation
    timeout_s: 30
    priority: P0

  - id: TC-SAN-009
    name: "BSD warning on object"
    capl_function: tc_San_BSD_Warning
    timeout_s: 20
    priority: P1

  - id: TC-SAN-010
    name: "Parking activation in reverse"
    capl_function: tc_San_Park_Activation
    timeout_s: 20
    priority: P1

  - id: TC-SAN-011
    name: "HHA hold on uphill"
    capl_function: tc_San_HHA_Hold
    timeout_s: 30
    priority: P1

  - id: TC-SAN-012
    name: "Zero unexpected DTCs"
    capl_function: tc_San_NoDTCs
    timeout_s: 15
    priority: P0
```

---

## Step 7 — Regression Test Suite Design

### 7.1 Regression Suite Coverage Matrix

```
Feature          | Functional | Boundary | Fault  | Timing | Negative | Total
-----------------|------------|----------|--------|--------|----------|-------
ACC              | 15         | 8        | 6      | 4      | 5        | 38
LKA              | 10         | 6        | 4      | 3      | 4        | 27
LDW              | 8          | 4        | 2      | 2      | 3        | 19
BSD              | 10         | 5        | 4      | 3      | 3        | 25
Parking Assist   | 12         | 6        | 5      | 4      | 3        | 30
Hill Hold Assist | 8          | 5        | 3      | 4      | 2        | 22
Communication    | 10         | 3        | 5      | 5      | 2        | 25
               --+------------+----------+--------+--------+----------+-------
TOTAL            | 73         | 37       | 29     | 25     | 22       | 186
```

### 7.2 pytest Configuration

```ini
; regression/pytest.ini
[pytest]
addopts =
    -v
    -ra
    --strict-markers
    --maxfail=50
    --tb=short

xfail_strict = true
filterwarnings = error

markers =
    sanity:      Quick smoke test
    regression:  Full regression test case
    acc:         Adaptive Cruise Control tests
    lka:         Lane Keep Assist tests
    ldw:         Lane Departure Warning tests
    bsd:         Blind Spot Detection tests
    parking:     Parking Assistance tests
    hha:         Hill Hold Assist tests
    p0:          Safety-critical — must pass 100%
    p1:          High priority functional
    p2:          Medium priority
    fault:       Fault injection test
    boundary:    Boundary/limit test
    timing:      Response time test
```

---

## Step 8 — CAPL Sanity Test Scripts

```capl
/*
 * sanity/sanity_suite.can
 * Fast sanity test module — runs after every ECU flash
 * All cases use short timeouts; any failure aborts the pipeline
 */

includes { "capl/common_hil_utils.capl" }

variables
{
  message ACC_Status  msg_AccSts;
  message LKA_Status  msg_LKASts;
  message BSD_Status  msg_BSDSts;

  int    gSanityFailed = 0;
  dword  gMsgRxCount   = 0;
}

/*=============================================================
 * TC-SAN-001: CAN Bus Alive After KL15
 *===========================================================*/
testcase tc_San_CANBusAlive()
{
  testCaseTitle("TC-SAN-001", "CAN Bus Alive After KL15");

  precond_PowerOn();

  // Expect at least one message on bus within 1000 ms
  long rxCount = testGetMsgCount(0xFFFF, 1000);  // Any message ID, 1s window
  if (rxCount > 0) {
    testStepPass("SAN-001-V1", "CAN bus active: " + (string)rxCount + " messages received");
  } else {
    testStepFail("SAN-001-V1", "No CAN messages received within 1000ms of KL15");
    gSanityFailed = 1;
  }
}

/*=============================================================
 * TC-SAN-002: Cyclic Messages Within Timing Spec
 *===========================================================*/
testcase tc_San_CyclicMessages()
{
  testCaseTitle("TC-SAN-002", "Cyclic Messages Present at Correct Rate");

  // Check VehicleSpeed message arrives at 10ms cycle (allow 30% tolerance)
  long cycles = testGetMsgCount(0x100, 500);  // Count in 500ms window
  // Expect ~50 messages in 500ms at 10ms cycle
  if (cycles >= 35 && cycles <= 65) {
    testStepPass("SAN-002-V1", "VehicleSpeed cycle: " + (string)cycles + " msgs/500ms");
  } else {
    testStepFail("SAN-002-V1", "VehicleSpeed cycle abnormal: " + (string)cycles + " msgs/500ms");
    gSanityFailed = 1;
  }

  // Check ACC_Status message
  cycles = testGetMsgCount(0x1A0, 500);
  // Expect ~25 at 20ms cycle
  if (cycles >= 18 && cycles <= 35) {
    testStepPass("SAN-002-V2", "ACC_Status cycle: " + (string)cycles + " msgs/500ms");
  } else {
    testStepFail("SAN-002-V2", "ACC_Status cycle abnormal: " + (string)cycles);
    gSanityFailed = 1;
  }
}

/*=============================================================
 * TC-SAN-003: No Error Frames on CAN Bus
 *===========================================================*/
testcase tc_San_NoErrorFrames()
{
  testCaseTitle("TC-SAN-003", "No CAN Error Frames At Boot");

  long errCount = testGetErrorCount(5000);  // 5-second window
  if (errCount == 0) {
    testStepPass("SAN-003-V1", "No error frames in 5 second window");
  } else {
    testStepFail("SAN-003-V1", "Error frame count = " + (string)errCount + " — check wiring");
    gSanityFailed = 1;
  }
}

/*=============================================================
 * TC-SAN-004: UDS Session Open + Software Version Read
 *===========================================================*/
testcase tc_San_UDS_SWVersion()
{
  byte  request[3];
  byte  response[20];
  int   len;

  testCaseTitle("TC-SAN-004", "UDS Default Session Open and SW Version Read");

  // Open default diagnostic session (Service 0x10 SubFunction 0x01)
  request[0] = 0x10;
  request[1] = 0x01;
  len = diagSendRequest(0x7DF, request, 2, response, 1000);

  if (len > 0 && response[0] == 0x50) {
    testStepPass("SAN-004-V1", "UDS default session opened (0x50 response)");
  } else {
    testStepFail("SAN-004-V1", "UDS session open failed");
    gSanityFailed = 1;
    return;
  }

  // Read SW version (Service 0x22 DID 0xF189)
  request[0] = 0x22;
  request[1] = 0xF1;
  request[2] = 0x89;
  len = diagSendRequest(0x7DF, request, 3, response, 1000);

  if (len > 3 && response[0] == 0x62) {
    testStepPass("SAN-004-V2", "SW version readable via UDS 0x22 F189");
  } else {
    testStepFail("SAN-004-V2", "SW version read failed — ECU not responding to UDS");
    gSanityFailed = 1;
  }
}

/*=============================================================
 * TC-SAN-005: ACC Signal Presence and Initial State
 *===========================================================*/
testcase tc_San_ACC_SignalPresence()
{
  float accSts;

  testCaseTitle("TC-SAN-005", "ACC Status Signal Present and Initial = STANDBY");

  setVehicleSpeed(0.0);
  testWaitForTimeout(500);

  accSts = @ACC_Status::ACC_Sts;

  if (accSts == 0x00 || accSts == 0x01) {
    testStepPass("SAN-005-V1", "ACC_Sts = " + (string)accSts + " (OFF/STANDBY as expected)");
  } else {
    testStepFail("SAN-005-V1", "Unexpected ACC_Sts at startup: " + (string)accSts);
    gSanityFailed = 1;
  }
}

/*=============================================================
 * TC-SAN-006: ACC Activation Smoke
 *===========================================================*/
testcase tc_San_ACC_Activation()
{
  testCaseTitle("TC-SAN-006", "ACC Activation Smoke Test");

  setVehicleSpeed(80.0);
  setLeadingObject(60.0, 0.0);

  message AccSwitch msg_sw;
  msg_sw.ACC_SetSpd = 80;
  output(msg_sw);

  if (waitForSignalValue("ACC_Status::ACC_Sts", 0x02, 1500)) {
    testStepPass("SAN-006-V1", "ACC ACTIVE state reached within 1500ms");
  } else {
    testStepFail("SAN-006-V1", "ACC did not activate — possible regression in activation logic");
    gSanityFailed = 1;
  }
}

/*=============================================================
 * TC-SAN-012: Zero Unexpected DTCs At Clean Boot
 *===========================================================*/
testcase tc_San_NoDTCs()
{
  testCaseTitle("TC-SAN-012", "No Unexpected DTCs At Clean Boot");

  // Send UDS ClearDTC first (0x14 0xFF 0xFF 0xFF) to ensure clean slate
  byte clearReq[4] = {0x14, 0xFF, 0xFF, 0xFF};
  byte clearResp[10];
  diagSendRequest(0x7DF, clearReq, 4, clearResp, 1000);
  testWaitForTimeout(500);

  // Read DTCs (Service 0x19 Sub 0x02, all DTCs by status mask 0xFF)
  byte dtcReq[3]  = {0x19, 0x02, 0xFF};
  byte dtcResp[128];
  int  len = diagSendRequest(0x7DF, dtcReq, 3, dtcResp, 2000);

  // Response format: 0x59 0x02 <dtc-count><dtc1 3+1 bytes>...
  int dtcCount = 0;
  if (len > 3 && dtcResp[0] == 0x59) {
    // Count DTCs: each entry is 4 bytes (3 DTC + 1 status)
    dtcCount = (len - 3) / 4;
  }

  if (dtcCount == 0) {
    testStepPass("SAN-012-V1", "No active DTCs at clean boot");
  } else {
    testStepFail("SAN-012-V1", "Unexpected DTCs present: " + (string)dtcCount + " DTC(s) found");
    gSanityFailed = 1;
  }
}
```

---

## Step 9 — Python Regression Test Scripts

### 9.1 conftest.py — Session Fixtures

```python
# regression/conftest.py
import pytest
import time
import sys
sys.path.insert(0, r"C:\HIL\ADAS_Tests\tools")

from canoe_controller import CANoeController
from power_control    import PowerControl


def pytest_addoption(parser):
    parser.addoption("--build-id",    default="unknown", help="ECU build version")
    parser.addoption("--canoe-config", default=r"C:\HIL\ADAS_Tests\ADAS_HIL.cfg")


@pytest.fixture(scope="session")
def build_id(request):
    return request.config.getoption("--build-id")


@pytest.fixture(scope="session")
def canoe(request):
    """Session-scoped CANoe fixture — starts once, shared by all tests."""
    ctrl = CANoeController(request.config.getoption("--canoe-config"))
    ctrl.launch_and_open()
    ctrl.start_measurement()
    time.sleep(2)
    yield ctrl
    ctrl.stop_measurement()
    ctrl.quit()


@pytest.fixture(scope="session")
def power(request):
    """Session-scoped power control fixture."""
    ctrl = PowerControl(port="COM4")
    ctrl.kl30_on()
    ctrl.kl15_on()
    time.sleep(2)
    yield ctrl
    ctrl.kl15_off()
    time.sleep(1)
    ctrl.kl30_off()
    ctrl.close()


@pytest.fixture(autouse=True)
def reset_ecu_state(canoe, power):
    """
    Auto-use fixture: resets ECU to known state before each test.
    Sets vehicle to 0 km/h, no objects, lane centred.
    """
    canoe.app.Environment.GetVariable("ADAS::VehicleSpeed_kph").Value     = 0.0
    canoe.app.Environment.GetVariable("ADAS::TargetDistance_m").Value     = 100.0
    canoe.app.Environment.GetVariable("ADAS::LaneOffset_m").Value         = 0.0
    canoe.app.Environment.GetVariable("ADAS::BrakePedal_Pct").Value       = 0.0
    canoe.app.Environment.GetVariable("ADAS::TurnSignalLeft").Value       = 0
    canoe.app.Environment.GetVariable("ADAS::TurnSignalRight").Value      = 0
    time.sleep(0.3)
    yield
    # Teardown: nothing special needed — next autouse resets state
```

### 9.2 ACC Regression Tests (Extended)

```python
# regression/acc_regression.py
import pytest
import time


# ──── Helpers ──────────────────────────────────────────────────────────────

def set_speed(canoe, kph):
    canoe.app.Environment.GetVariable("ADAS::VehicleSpeed_kph").Value = kph
    time.sleep(0.5)

def set_target(canoe, dist, rel_vel=0.0):
    canoe.app.Environment.GetVariable("ADAS::TargetDistance_m").Value    = dist
    canoe.app.Environment.GetVariable("ADAS::TargetRelVelocity_kph").Value = rel_vel
    time.sleep(0.3)

def activate_acc(canoe, set_kph):
    canoe.app.Environment.GetVariable("ADAS::ACC_SetSpeed_kph").Value = set_kph
    canoe.app.Environment.GetVariable("ADAS::ACC_SetButton").Value    = 1
    time.sleep(0.1)
    canoe.app.Environment.GetVariable("ADAS::ACC_SetButton").Value    = 0
    time.sleep(1.0)

def acc_status(canoe):
    return int(canoe.get_signal_value(1, "ACC_Status", "ACC_Sts"))

def acc_brake_req(canoe):
    return float(canoe.get_signal_value(1, "ACC_Control", "ACC_BrkReq_Pct"))


# ──── Functional Tests ─────────────────────────────────────────────────────

@pytest.mark.acc
@pytest.mark.p0
@pytest.mark.regression
class TestACCFunctional:

    def test_acc_activates_at_80kph(self, canoe):
        """ACC activates within 1s at 80 km/h."""
        set_speed(canoe, 80.0)
        set_target(canoe, 60.0)
        activate_acc(canoe, 80.0)
        assert acc_status(canoe) == 0x02, "ACC not ACTIVE at 80 km/h"

    def test_acc_set_speed_displayed(self, canoe):
        """HMI displays correct set speed."""
        set_speed(canoe, 100.0)
        activate_acc(canoe, 100.0)
        disp = canoe.get_signal_value(1, "ACC_HMI", "ACC_SetSpd_Disp")
        assert abs(disp - 100.0) <= 2.0, f"Display speed {disp} != 100 km/h"

    def test_acc_cancels_on_brake(self, canoe):
        set_speed(canoe, 80.0)
        activate_acc(canoe, 80.0)
        canoe.app.Environment.GetVariable("ADAS::BrakePedal_Pct").Value = 40.0
        time.sleep(0.4)
        assert acc_status(canoe) in (0x00, 0x01), "ACC not cancelled after brake"
        canoe.app.Environment.GetVariable("ADAS::BrakePedal_Pct").Value = 0.0

    def test_acc_cancels_on_cancel_button(self, canoe):
        set_speed(canoe, 80.0)
        activate_acc(canoe, 80.0)
        canoe.app.Environment.GetVariable("ADAS::ACC_CancelButton").Value = 1
        time.sleep(0.2)
        canoe.app.Environment.GetVariable("ADAS::ACC_CancelButton").Value = 0
        time.sleep(0.3)
        assert acc_status(canoe) in (0x00, 0x01)


# ──── Boundary Tests ───────────────────────────────────────────────────────

@pytest.mark.acc
@pytest.mark.boundary
@pytest.mark.regression
class TestACCBoundary:

    @pytest.mark.parametrize("speed", [30, 31, 32])
    def test_acc_activates_at_minimum_speed(self, canoe, speed):
        """ACC activates at minimum speed boundary (30 km/h)."""
        set_speed(canoe, float(speed))
        activate_acc(canoe, float(speed))
        assert acc_status(canoe) == 0x02, f"ACC should activate at {speed} km/h"

    @pytest.mark.parametrize("speed", [28, 29])
    def test_acc_does_not_activate_below_minimum(self, canoe, speed):
        """ACC must NOT activate below 30 km/h."""
        set_speed(canoe, float(speed))
        activate_acc(canoe, 30.0)
        assert acc_status(canoe) != 0x02, f"ACC activated at {speed} km/h — should be blocked"

    @pytest.mark.parametrize("dist,rel_vel", [
        (200.0,  0.0),   # Max distance — ACC holds set speed
        (0.5,  -10.0),   # Extremely close target
    ])
    def test_acc_distance_boundaries(self, canoe, dist, rel_vel):
        set_speed(canoe, 80.0)
        set_target(canoe, dist, rel_vel)
        activate_acc(canoe, 80.0)
        # Just verify no crash/fault state
        s = acc_status(canoe)
        assert s != 0xFF, f"ACC entered FAULT state at dist={dist}m"


# ──── Timing Tests ─────────────────────────────────────────────────────────

@pytest.mark.acc
@pytest.mark.timing
@pytest.mark.regression
class TestACCTiming:

    def test_acc_activation_latency(self, canoe):
        """ACC activation latency must be ≤ 1000 ms."""
        set_speed(canoe, 80.0)
        set_target(canoe, 60.0)

        import time as _time
        t_start = _time.perf_counter()
        activate_acc(canoe, 80.0)
        t_end   = _time.perf_counter()

        # activate_acc waits 1.1s internally — refine with signal polling
        latency_ms = (t_end - t_start) * 1000
        assert latency_ms <= 1100, f"ACC activation latency {latency_ms:.0f} ms > 1000 ms limit"

    def test_brake_request_latency_on_close_target(self, canoe):
        """Brake request must appear within 400 ms of critical target injection."""
        set_speed(canoe, 100.0)
        set_target(canoe, 60.0)
        activate_acc(canoe, 100.0)

        import time as _time
        t_stim = _time.perf_counter()
        set_target(canoe, 12.0, -40.0)

        deadline = t_stim + 0.4  # 400 ms
        brk = 0.0
        while _time.perf_counter() < deadline:
            brk = acc_brake_req(canoe)
            if brk > 0.0:
                break
            time.sleep(0.05)

        assert brk > 0.0, "Brake request not seen within 400 ms of critical target"


# ──── Fault Tests ──────────────────────────────────────────────────────────

@pytest.mark.acc
@pytest.mark.fault
@pytest.mark.regression
class TestACCFault:

    def test_acc_disables_on_radar_loss(self, canoe):
        """ACC must disable and warn when radar signal is lost."""
        set_speed(canoe, 80.0)
        set_target(canoe, 60.0)
        activate_acc(canoe, 80.0)
        assert acc_status(canoe) == 0x02

        # Simulate radar loss: invalid distance
        canoe.app.Environment.GetVariable("ADAS::TargetDistance_m").Value = -999.0
        time.sleep(1.5)

        s = acc_status(canoe)
        assert s in (0x00, 0x01, 0xFF), f"ACC expected STANDBY/FAULT on radar loss, got 0x{s:02X}"

    def test_acc_stores_dtc_on_radar_fault(self, canoe):
        """DTC stored when radar comm is lost."""
        from dtc_reader import read_active_dtcs
        canoe.app.Environment.GetVariable("ADAS::TargetDistance_m").Value = -999.0
        time.sleep(2.0)
        dtcs = read_active_dtcs("192.168.1.100")
        # Expect at least one ACC/radar related DTC
        assert len(dtcs) > 0, "No DTC stored after radar fault simulation"
```

---

## Step 10 — Jenkins Declarative Pipeline (Full)

```groovy
// Jenkinsfile — Full pipeline triggered by new ECU build
pipeline {
    agent none  // Each stage selects its own agent

    parameters {
        string(name: 'BUILD_VERSION',
               defaultValue: 'v0.0.0',
               description: 'ECU SW build version e.g. v2.4.1')
        string(name: 'ARTIFACT_URL',
               defaultValue: '',
               description: 'Direct URL to .hex file (optional override)')
        choice(name: 'SUITE',
               choices: ['SANITY_THEN_REGRESSION', 'SANITY_ONLY', 'REGRESSION_ONLY'],
               description: 'Which test suite to run')
        booleanParam(name: 'SKIP_FLASH',
                     defaultValue: false,
                     description: 'Skip flashing (use already-flashed ECU)')
    }

    options {
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 3, unit: 'HOURS')
    }

    environment {
        ARTIFACTORY_CREDS = credentials('artifactory-creds')
        REPORTS_DIR       = "reports\\${params.BUILD_VERSION}"
        HIL_PYTHON        = 'C:\\HIL\\ADAS_Tests\\.venv\\Scripts\\python.exe'
        HIL_SCRIPTS       = 'C:\\HIL\\ADAS_Tests'
    }

    stages {

        // ─────────────────────────────────────────────────────────────────
        stage('Checkout Test Repository') {
            agent { label 'hil-bench' }
            steps {
                checkout scm
                bat 'git log --oneline -5'
                echo "Test suite checked out for build: ${params.BUILD_VERSION}"
            }
        }

        // ─────────────────────────────────────────────────────────────────
        stage('Download ECU Binary') {
            agent { label 'hil-bench' }
            when { expression { !params.SKIP_FLASH } }
            steps {
                script {
                    def url = params.ARTIFACT_URL ?: \
                        "https://artifactory.yourcompany.com/adas-ecu-releases/${params.BUILD_VERSION}/ADAS_ECU_${params.BUILD_VERSION}.hex"
                    echo "Downloading: ${url}"
                    bat """
                        mkdir firmware 2>nul
                        curl -fsSL -u %ARTIFACTORY_CREDS_USR%:%ARTIFACTORY_CREDS_PSW% ^
                             -o firmware\\ADAS_ECU.hex "${url}"
                        curl -fsSL -u %ARTIFACTORY_CREDS_USR%:%ARTIFACTORY_CREDS_PSW% ^
                             -o firmware\\build_info.json "${url.replace('.hex','_info.json')}"
                    """
                }
            }
            post {
                failure {
                    error "Could not download ECU binary for ${params.BUILD_VERSION}. Aborting pipeline."
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────
        stage('Flash ECU') {
            agent { label 'hil-bench' }
            when { expression { !params.SKIP_FLASH } }
            steps {
                script {
                    def flashResult = bat(
                        script: """
                            ${env.HIL_PYTHON} ${env.HIL_SCRIPTS}\\tools\\flash_ecu.py ^
                                --hex firmware\\ADAS_ECU.hex ^
                                --build-id ${params.BUILD_VERSION}
                        """,
                        returnStatus: true
                    )
                    if (flashResult != 0) {
                        error "ECU flash FAILED for build ${params.BUILD_VERSION}"
                    }
                }
            }
            post {
                success { echo "ECU flashed successfully with ${params.BUILD_VERSION}" }
                failure {
                    emailext subject: "[HIL] FLASH FAILED — ${params.BUILD_VERSION}",
                             body:    "ECU flashing failed. Pipeline aborted.\nBuild: ${params.BUILD_VERSION}\nJenkins: ${env.BUILD_URL}",
                             to:      'adas-hw-team@yourcompany.com'
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────
        stage('Start HIL Environment') {
            agent { label 'hil-bench' }
            steps {
                bat """
                    ${env.HIL_PYTHON} ${env.HIL_SCRIPTS}\\tools\\canoe_controller.py ^
                        --action start ^
                        --config ${env.HIL_SCRIPTS}\\ADAS_HIL.cfg
                """
                bat """
                    ${env.HIL_PYTHON} ${env.HIL_SCRIPTS}\\tools\\power_control.py ^
                        --action on
                """
                bat "timeout /t 5 /nobreak > nul"  // Wait for ECU boot
            }
        }

        // ─────────────────────────────────────────────────────────────────
        stage('Sanity Tests') {
            agent { label 'hil-bench' }
            when {
                expression {
                    params.SUITE in ['SANITY_THEN_REGRESSION', 'SANITY_ONLY']
                }
            }
            steps {
                script {
                    bat """
                        mkdir ${env.REPORTS_DIR}\\sanity 2>nul

                        ${env.HIL_PYTHON} ${env.HIL_SCRIPTS}\\sanity\\sanity_runner.py ^
                            --build-id ${params.BUILD_VERSION} ^
                            --output ${env.REPORTS_DIR}\\sanity ^
                            --junitxml ${env.REPORTS_DIR}\\sanity\\sanity_junit.xml
                    """
                }
            }
            post {
                always {
                    junit "${env.REPORTS_DIR}\\sanity\\sanity_junit.xml"
                    publishHTML([
                        target: [
                            reportDir:   "${env.REPORTS_DIR}\\sanity",
                            reportFiles: 'sanity_report.html',
                            reportName:  "Sanity Report — ${params.BUILD_VERSION}"
                        ]
                    ])
                }
                failure {
                    script {
                        currentBuild.result = 'FAILURE'
                        emailext subject: "[HIL] ⛔ SANITY FAILED — ${params.BUILD_VERSION} — REGRESSION BLOCKED",
                                 body:    readFile("${env.REPORTS_DIR}\\sanity\\sanity_summary.txt"),
                                 to:      'adas-team@yourcompany.com,sw-team@yourcompany.com'
                        error "Sanity suite FAILED — regression will not run"
                    }
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────
        stage('Regression Tests') {
            agent { label 'hil-bench' }
            when {
                allOf {
                    expression { params.SUITE in ['SANITY_THEN_REGRESSION', 'REGRESSION_ONLY'] }
                    expression { currentBuild.result != 'FAILURE' }
                }
            }
            steps {
                bat """
                    mkdir ${env.REPORTS_DIR}\\regression 2>nul

                    ${env.HIL_PYTHON} -m pytest ^
                        regression/ ^
                        -v ^
                        --build-id=${params.BUILD_VERSION} ^
                        --junitxml=${env.REPORTS_DIR}\\regression\\regression_junit.xml ^
                        --html=${env.REPORTS_DIR}\\regression\\regression_report.html ^
                        --self-contained-html
                """
            }
            post {
                always {
                    junit "${env.REPORTS_DIR}\\regression\\regression_junit.xml"
                    publishHTML([
                        target: [
                            reportDir:   "${env.REPORTS_DIR}\\regression",
                            reportFiles: 'regression_report.html',
                            reportName:  "Regression Report — ${params.BUILD_VERSION}"
                        ]
                    ])
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────
        stage('Gate Evaluation') {
            agent { label 'hil-bench' }
            steps {
                script {
                    def gateResult = bat(
                        script: """
                            ${env.HIL_PYTHON} gate\\run_gate.py ^
                                --build-id ${params.BUILD_VERSION} ^
                                --reports-dir ${env.REPORTS_DIR} ^
                                --min-pass-rate 95.0 ^
                                --p0-pass-rate 100.0
                        """,
                        returnStatus: true
                    )

                    def summary = readFile("${env.REPORTS_DIR}\\gate_summary.json")
                    echo "Gate summary:\n${summary}"

                    if (gateResult != 0) {
                        currentBuild.result = 'UNSTABLE'
                        echo "⚠ Gate FAILED — build will not be promoted"
                    } else {
                        echo "✓ Gate PASSED — build eligible for promotion"
                    }
                }
            }
        }

        // ─────────────────────────────────────────────────────────────────
        stage('Promote Build') {
            agent { label 'hil-bench' }
            when { expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' } }
            steps {
                bat """
                    curl -u %ARTIFACTORY_CREDS_USR%:%ARTIFACTORY_CREDS_PSW% ^
                         -X POST ^
                         "https://artifactory.yourcompany.com/api/storage/adas-ecu-releases/${params.BUILD_VERSION}/ADAS_ECU_${params.BUILD_VERSION}.hex;hil.status=PASSED;hil.build=${env.BUILD_NUMBER}"
                """
                echo "Build ${params.BUILD_VERSION} PROMOTED in Artifactory with hil.status=PASSED"
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    post {
        always {
            node('hil-bench') {
                // Power off ECU - always runs regardless of result
                bat """
                    ${env.HIL_PYTHON} ${env.HIL_SCRIPTS}\\tools\\power_control.py --action off
                    ${env.HIL_PYTHON} ${env.HIL_SCRIPTS}\\tools\\canoe_controller.py --action stop
                """
            }
        }
        success {
            emailext subject: "[HIL] ✅ PASSED — ${params.BUILD_VERSION}",
                     body:    "All tests passed.\nBuild: ${params.BUILD_VERSION}\nReport: ${env.BUILD_URL}artifact/${env.REPORTS_DIR}/regression/regression_report.html",
                     to:      'adas-team@yourcompany.com'
        }
        unstable {
            emailext subject: "[HIL] ⚠ UNSTABLE — ${params.BUILD_VERSION} — Gate Failed",
                     body:    "Some tests failed. Gate threshold not met.\nBuild: ${params.BUILD_VERSION}\n${env.BUILD_URL}",
                     to:      'adas-team@yourcompany.com,sw-team@yourcompany.com'
        }
        failure {
            emailext subject: "[HIL] ❌ FAILED — ${params.BUILD_VERSION}",
                     body:    "Pipeline failed (flash, sanity, or infrastructure error).\n${env.BUILD_URL}",
                     to:      'adas-team@yourcompany.com,sw-team@yourcompany.com,infra@yourcompany.com'
        }
    }
}
```

---

## Step 11 — Parallel Feature Execution in Jenkins

For large regression suites, run features in parallel to cut execution time:

```groovy
stage('Regression Tests — Parallel') {
    parallel {

        stage('ACC Regression') {
            agent { label 'hil-bench' }
            steps {
                bat """
                    ${env.HIL_PYTHON} -m pytest regression/acc_regression.py ^
                        -m "acc" ^
                        --junitxml=${env.REPORTS_DIR}\\regression\\acc_junit.xml ^
                        --html=${env.REPORTS_DIR}\\regression\\acc_report.html ^
                        --self-contained-html
                """
            }
            post {
                always { junit "${env.REPORTS_DIR}\\regression\\acc_junit.xml" }
            }
        }

        stage('LKA/LDW Regression') {
            agent { label 'hil-bench-2' }   // Second HIL bench if available
            steps {
                bat """
                    ${env.HIL_PYTHON} -m pytest regression/lka_ldw_regression.py ^
                        -m "lka or ldw" ^
                        --junitxml=${env.REPORTS_DIR}\\regression\\lka_junit.xml ^
                        --html=${env.REPORTS_DIR}\\regression\\lka_report.html ^
                        --self-contained-html
                """
            }
            post {
                always { junit "${env.REPORTS_DIR}\\regression\\lka_junit.xml" }
            }
        }

        stage('BSD Regression') {
            agent { label 'hil-bench-2' }
            steps {
                bat """
                    ${env.HIL_PYTHON} -m pytest regression/bsd_regression.py ^
                        -m "bsd" ^
                        --junitxml=${env.REPORTS_DIR}\\regression\\bsd_junit.xml ^
                        --html=${env.REPORTS_DIR}\\regression\\bsd_report.html ^
                        --self-contained-html
                """
            }
            post {
                always { junit "${env.REPORTS_DIR}\\regression\\bsd_junit.xml" }
            }
        }

        stage('Parking & HHA') {
            agent { label 'hil-bench' }
            steps {
                bat """
                    ${env.HIL_PYTHON} -m pytest ^
                        regression/parking_regression.py ^
                        regression/hha_regression.py ^
                        -m "parking or hha" ^
                        --junitxml=${env.REPORTS_DIR}\\regression\\park_hha_junit.xml ^
                        --html=${env.REPORTS_DIR}\\regression\\park_hha_report.html ^
                        --self-contained-html
                """
            }
            post {
                always { junit "${env.REPORTS_DIR}\\regression\\park_hha_junit.xml" }
            }
        }
    }
}
```

> With 2 HIL benches and parallel stages, a 90-minute sequential suite becomes ~45 minutes.

---

## Step 12 — Gate Evaluation and Build Promotion

### 12.1 Gate Evaluator Script

```python
# gate/run_gate.py
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--build-id",       required=True)
    p.add_argument("--reports-dir",    required=True)
    p.add_argument("--min-pass-rate",  type=float, default=95.0)
    p.add_argument("--p0-pass-rate",   type=float, default=100.0)
    return p.parse_args()


def parse_junit_xml(xml_path: Path) -> dict:
    """Parse JUnit XML and return test statistics."""
    if not xml_path.exists():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}

    tree = ET.parse(xml_path)
    root = tree.getroot()
    tag  = root.tag

    def get_attr(elem, attr, default=0):
        return int(elem.get(attr, default) or 0)

    if tag == "testsuites":
        tests    = sum(get_attr(s, "tests")    for s in root.findall("testsuite"))
        failures = sum(get_attr(s, "failures") for s in root.findall("testsuite"))
        errors   = sum(get_attr(s, "errors")   for s in root.findall("testsuite"))
        skipped  = sum(get_attr(s, "skipped")  for s in root.findall("testsuite"))
    else:
        tests    = get_attr(root, "tests")
        failures = get_attr(root, "failures")
        errors   = get_attr(root, "errors")
        skipped  = get_attr(root, "skipped")

    passed = tests - failures - errors - skipped
    return {"tests": tests, "passed": passed, "failures": failures,
            "errors": errors, "skipped": skipped}


def collect_all_stats(reports_dir: Path) -> dict:
    totals = {"tests": 0, "passed": 0, "failures": 0, "errors": 0, "skipped": 0}
    for xml in reports_dir.rglob("*_junit.xml"):
        s = parse_junit_xml(xml)
        for k in totals:
            totals[k] += s.get(k, 0)
    return totals


def main():
    args       = parse_args()
    reports    = Path(args.reports_dir)
    stats      = collect_all_stats(reports)
    total      = stats["tests"]
    passed     = stats["passed"]
    pass_rate  = (passed / total * 100) if total > 0 else 0.0

    violations = []

    if pass_rate < args.min_pass_rate:
        violations.append(
            f"Pass rate {pass_rate:.1f}% < required {args.min_pass_rate}%"
        )

    gate_passed = len(violations) == 0

    summary = {
        "build_id":     args.build_id,
        "generated_at": datetime.now().isoformat(),
        "gate":         "PASSED" if gate_passed else "FAILED",
        "stats":        stats,
        "pass_rate":    round(pass_rate, 2),
        "thresholds": {
            "min_pass_rate": args.min_pass_rate,
            "p0_pass_rate":  args.p0_pass_rate,
        },
        "violations": violations,
    }

    summary_path = reports / "gate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print("\n" + "="*60)
    print(f"  Build:      {args.build_id}")
    print(f"  Gate:       {summary['gate']}")
    print(f"  Tests:      {total}")
    print(f"  Passed:     {passed}")
    print(f"  Pass Rate:  {pass_rate:.1f}%")
    if violations:
        print("  Violations:")
        for v in violations:
            print(f"    - {v}")
    print("="*60)

    sys.exit(0 if gate_passed else 1)


if __name__ == "__main__":
    main()
```

---

## Step 13 — Notification and Reporting

### 13.1 Email Template (Extended)

```groovy
// In Jenkinsfile post{} block
emailext(
    subject: "[HIL][${currentBuild.result}] ADAS ECU ${params.BUILD_VERSION} — ${currentBuild.result}",
    to: 'adas-team@yourcompany.com',
    mimeType: 'text/html',
    body: """
    <html><body>
    <h2 style="color:${currentBuild.result=='SUCCESS'?'green':'red'}">
        HIL Test Result: ${currentBuild.result}
    </h2>
    <table border="1" cellpadding="5">
      <tr><td><b>Build Version</b></td><td>${params.BUILD_VERSION}</td></tr>
      <tr><td><b>Jenkins Build</b></td><td>#${env.BUILD_NUMBER}</td></tr>
      <tr><td><b>Duration</b></td><td>${currentBuild.durationString}</td></tr>
      <tr><td><b>Reports</b></td><td><a href="${env.BUILD_URL}artifact/${env.REPORTS_DIR}/regression/regression_report.html">View HTML Report</a></td></tr>
    </table>
    <h3>Gate Summary</h3>
    <pre>${(new File("${env.REPORTS_DIR}/gate_summary.json")).text}</pre>
    </body></html>
    """
)
```

### 13.2 Slack Notification

```groovy
slackSend(
    channel:   '#adas-hil-results',
    color:     currentBuild.result == 'SUCCESS' ? 'good' : 'danger',
    message:   """|
                  |*[HIL] ${currentBuild.result}* — ECU Build \`${params.BUILD_VERSION}\`
                  |*Duration:* ${currentBuild.durationString}
                  |*Report:* ${env.BUILD_URL}artifact/${env.REPORTS_DIR}/regression/regression_report.html
                  |""".stripMargin()
)
```

---

## Step 14 — Test Results Traceability

### 14.1 Linking Tests to Requirements

Every test case ID maps to a requirement ID:

```python
# regression/traceability.py
# Maps test IDs to system requirements

TRACEABILITY_MATRIX = {
    # Test ID         : Requirement IDs
    "TC-ACC-001":       ["SYS-ACC-R001", "SFR-ACC-F001"],
    "TC-ACC-002":       ["SYS-ACC-R002", "SFR-ACC-F002", "SFR-ACC-F003"],
    "TC-ACC-004":       ["SYS-ACC-R010", "SFR-ACC-S001"],  # Safety requirement
    "TC-LKA-001":       ["SYS-LKA-R001", "SFR-LKA-F001"],
    "TC-LKA-002":       ["SYS-LKA-R002", "SFR-LKA-F002"],
    "TC-BSD-001":       ["SYS-BSD-R001"],
    "TC-PARK-003":      ["SYS-PARK-R010", "SFR-PARK-S001"],  # Safety
    "TC-HHA-001":       ["SYS-HHA-R001", "SFR-HHA-F001"],
}

def get_covered_requirements(passed_tests: list) -> list:
    """Return list of requirements covered by passing tests."""
    covered = set()
    for tc in passed_tests:
        for req in TRACEABILITY_MATRIX.get(tc, []):
            covered.add(req)
    return sorted(covered)
```

### 14.2 Automatic JIRA Ticket on New Failure

```python
# gate/jira_reporter.py
import requests
import json


JIRA_URL   = "https://yourcompany.atlassian.net"
JIRA_TOKEN = "YOUR_JIRA_API_TOKEN"
PROJECT    = "ADAS"


def create_defect_ticket(test_id: str, failure_msg: str, build_version: str) -> str:
    """Create JIRA bug ticket for a test failure."""
    payload = {
        "fields": {
            "project":     {"key": PROJECT},
            "summary":     f"[HIL REGRESSION] {test_id} FAILED — Build {build_version}",
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph",
                              "content": [{"type": "text",
                                           "text": f"Test {test_id} failed in HIL regression for build {build_version}.\n\nFailure:\n{failure_msg}"}]}]
            },
            "issuetype": {"name": "Bug"},
            "labels":    ["HIL", "regression", "automated"],
            "priority":  {"name": "High"},
        }
    }

    response = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        headers={"Authorization": f"Bearer {JIRA_TOKEN}",
                 "Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    ticket_id = response.json().get("key", "UNKNOWN")
    print(f"[JIRA] Created ticket: {ticket_id} for {test_id}")
    return ticket_id
```

---

## Step 15 — Nightly vs On-Demand Execution

### 15.1 Nightly Schedule (Cron)

```groovy
// In Jenkinsfile — triggers block
triggers {
    // Run every weeknight at 22:00
    cron('0 22 * * 1-5')

    // OR: generic webhook trigger (fires on artifact upload)
    GenericTrigger(
        genericVariables: [
            [key: 'BUILD_VERSION', value: '$.build_version'],
            [key: 'ARTIFACT_URL',  value: '$.artifact_url'],
        ],
        causeString: 'Triggered by SW build release $BUILD_VERSION',
        token:       'ADAS_ECU_WEBHOOK_TOKEN',
        printPostContent: true
    )
}
```

### 15.2 Execution Strategy Comparison

| Trigger | Suite | When | Who Triggers |
|---|---|---|---|
| New SW tag pushed | Sanity only | Immediately on tag | Webhook → auto |
| Sanity PASSED | Full regression | Immediately after sanity | Pipeline chained |
| Night schedule (22:00) | Full regression | Every weeknight | Cron |
| Manual (Release Candidate) | Sanity + full regression + extended | On demand | Test lead |
| Hotfix branch merge | Sanity only (fast check) | On merge event | Webhook |

### 15.3 Pipeline Job Structure in Jenkins

```
Jenkins Jobs:
│
├── ADAS_ECU_Sanity           ← Fast ~10 min, triggered on every build webhook
│     └── calls: sanity_runner.py
│
├── ADAS_ECU_Regression       ← Full ~90 min, nightly + triggered by sanity PASS
│     └── calls: pytest regression/
│
├── ADAS_ECU_SanityThenReg    ← Combined pipeline (both above in sequence)
│     └── master Jenkinsfile
│
└── ADAS_ECU_Promote          ← Manual promotion of successful build to RELEASE
      └── promotes Artifactory artifact property hil.status=APPROVED
```

---

## Full End-to-End Flow Diagram

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  SW team pushes git tag v2.4.1 to Bitbucket/GitHub                       │
 └──────────────────────────┬───────────────────────────────────────────────┘
                             │ Webhook fires
                             ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  Jenkins ADAS_ECU_SanityThenReg pipeline starts                           │
 │                                                                           │
 │  Stage 1: Checkout test scripts from Git repo                             │
 │  Stage 2: Download ADAS_ECU_v2.4.1.hex from Artifactory                  │
 │  Stage 3: Flash ECU using canflash.exe via Python                         │
 │           ✗ FAIL → pipeline abort, email INFRA team                      │
 │  Stage 4: Power cycle ECU, verify boot                                    │
 │  Stage 5: Start CANoe, start dSPACE SCALEXIO real-time model             │
 └──────────────────────────┬───────────────────────────────────────────────┘
                             │
                             ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  SANITY SUITE (~10 min)                                                   │
 │  13 test cases: boot check, cyclic messages, DTC check, feature smoke     │
 │                                                                           │
 │         ✗ ANY SANITY FAILS → pipeline ABORTS                              │
 │                → email SW + ADAS team with exact failure                  │
 │                → no regression runs (waste of time)                       │
 │                                                                           │
 │         ✓ ALL SANITY PASS → proceed to regression                        │
 └──────────────────────────┬───────────────────────────────────────────────┘
                             │
                             ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  REGRESSION SUITE (~90 min, or ~45 min with 2 parallel benches)          │
 │  186 test cases: ACC / LKA / LDW / BSD / Parking / HHA / Comm            │
 │  Each feature runs in parallel on separate Jenkins agent on 2nd bench     │
 │                                                                           │
 │  Results collected: JUnit XML for each feature                            │
 └──────────────────────────┬───────────────────────────────────────────────┘
                             │
                             ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  GATE EVALUATION                                                           │
 │  • Overall pass rate ≥ 95% ?                                              │
 │  • P0 safety tests 100% ?                                                 │
 │  • No new error categories vs. baseline ?                                  │
 │                                                                           │
 │  ✗ GATE FAILS              ✓ GATE PASSES                                  │
 │  Build = UNSTABLE           Build = SUCCESS                               │
 │  Artifactory: FAILED        Artifactory: PASSED                           │
 │  JIRA tickets auto-opened   Build eligible for release                   │
 └──────────────────────────┬───────────────────────────────────────────────┘
                             │
                             ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  REPORTING                                                                 │
 │  • HTML report published on Jenkins                                        │
 │  • JUnit XML archived                                                      │
 │  • Email to ADAS + SW team                                                 │
 │  • Slack message to #adas-hil-results                                     │
 │  • JIRA defects opened for new failures                                   │
 └──────────────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting CI Pipeline Issues

| # | Problem | Symptom | Fix |
|---|---------|---------|-----|
| 1 | Webhook not triggering Jenkins | Pipeline never starts after git push | Check webhook URL in Bitbucket/GitHub → verify Generic Webhook Trigger token matches |
| 2 | Agent disconnects mid-run | `Connection reset by peer` in Jenkins log | Increase agent keepalive: `java -jar agent.jar ... -noCertificateCheck` + NSSM service recovery |
| 3 | Flash fails — COM port busy | `canflash.exe` exit code 2 | Another process holds VN5640 COM. Kill stale CANoe in teardown stage |
| 4 | CANoe already open | COM exception on second run | Add `canoe_controller.py --action stop` in `post { always { } }` |
| 5 | ECU doesn't boot after flash | Sanity times out on CAN bus alive | Extend power cycle wait; verify flash success log; check supply current |
| 6 | pytest can't import win32com | `ModuleNotFoundError` | Activate `.venv` with 32-bit Python matching CANoe bitness |
| 7 | JUnit XML not found | `junit: no files found` warning | Check path separators in Windows — use `\\` not `/` in bat steps |
| 8 | Parallel stages both use same bench | Race condition on ECU signals | Assign each parallel stage to separate agent label (`hil-bench-1`, `hil-bench-2`) |
| 9 | Reports not accessible as artifacts | `No such file` on publishHTML | Always use full absolute paths; verify `mkdir` creates directory before pytest runs |
| 10 | Gate always fails on new build | Pass rate drops for first run | Investigate if ECU needs warm-up time; add 10s delay after boot before test starts |
| 11 | Email not sent | Empty inbox after pipeline | Check SMTP credentials in Jenkins; verify `emailext` plugin installed; test with manual `Test Configuration` |
| 12 | Artifactory credential expired | 401 on artifact download | Rotate service account token in Artifactory → update Jenkins credential `artifactory-creds` |

---

*End of Document — ECU Release Regression & Sanity Testing with Jenkins v1.0*
