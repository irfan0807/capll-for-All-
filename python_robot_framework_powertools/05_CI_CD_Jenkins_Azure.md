# 05 — CI/CD: Jenkins & Azure DevOps

> **Topic**: Jenkins pipelines, Azure DevOps, parallel execution, reporting, Git integration, notifications  
> **Role relevance**: Integrate automated tests into CI gate — block bad firmware before it reaches testers  
> **Outcome**: Build production CI pipelines that flash firmware, run tests, publish reports, and file bugs automatically

---

## 1. CI/CD in Device Testing Context

```
CI/CD Pipeline for Power Tool Firmware Testing:
──────────────────────────────────────────────────────────────────────────
Developer pushes branch
        │
        ▼
Bitbucket/GitHub webhook
        │
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         CI Server (Jenkins / Azure)                   │
│                                                                        │
│  Stage 1: Code Quality     ← MISRA (cppcheck), Python lint (ruff)    │
│  Stage 2: Build Firmware   ← Cross-compile ARM Cortex-M              │
│  Stage 3: Unit Tests (SIL) ← pytest, no hardware needed              │
│  Stage 4: Flash Device     ← Flash .hex to test bench via bossac     │
│  Stage 5: Smoke Tests      ← 5-minute quick sanity                   │
│  Stage 6: Integration Tests← Full communication + measurement        │
│  Stage 7: Report           ← HTML report, JUnit XML, coverage        │
│  Stage 8: Gate             ← Pass rate check, block merge if fail    │
│  Stage 9: JIRA             ← Auto-create bugs for failures           │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
Merge approved / blocked
```

---

## 2. Jenkins — Declarative Pipeline

```groovy
// Jenkinsfile — Power Tool BLE/UART CI Pipeline

pipeline {

    agent { label 'test-bench-01' }   // Run on node with test hardware

    parameters {
        string(name: 'FW_VERSION',  defaultValue: '',
               description: 'Firmware version to test (e.g., 2.1.0-rc1)')
        choice(name: 'TEST_SUITE',  choices: ['smoke', 'regression', 'full'],
               description: 'Which test suite to run')
        booleanParam(name: 'SKIP_FLASH', defaultValue: false,
                     description: 'Skip flashing (for re-run only)')
    }

    environment {
        FW_PATH       = "${WORKSPACE}/firmware/build/powertool_fw.hex"
        REPORT_DIR    = "${WORKSPACE}/reports"
        JIRA_URL      = credentials('jira-url')
        JIRA_TOKEN    = credentials('jira-api-token')
        NEXUS_CREDS   = credentials('nexus-credentials')
        DEVICE_PORT   = '/dev/ttyACM0'       // USB CDC serial
        DEVICE_NAME   = 'PowerTool-X1'       // BLE device name
    }

    options {
        timeout(time: 2, unit: 'HOURS')
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    stages {

        stage('Setup') {
            steps {
                sh 'mkdir -p ${REPORT_DIR}'
                sh 'pip install -r requirements.txt --quiet'
            }
        }

        stage('Download Firmware') {
            when { expression { params.FW_VERSION != '' } }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'nexus-credentials',
                    usernameVariable: 'NEXUS_USER',
                    passwordVariable: 'NEXUS_PASS'
                )]) {
                    sh """
                        curl -u "${NEXUS_USER}:${NEXUS_PASS}" \
                            "${NEXUS_URL}/powertool/${params.FW_VERSION}/fw.hex" \
                            -o "${FW_PATH}"
                    """
                }
            }
        }

        stage('Flash Firmware') {
            when { expression { !params.SKIP_FLASH } }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    sh """
                        python tools/flash_device.py \
                            --firmware "${FW_PATH}" \
                            --port "${DEVICE_PORT}" \
                            --verify
                    """
                }
            }
            post {
                failure {
                    error "Firmware flash FAILED — aborting pipeline"
                }
            }
        }

        stage('Smoke Tests') {
            steps {
                sh """
                    pytest tests/ -m smoke \
                        --html="${REPORT_DIR}/smoke_report.html" \
                        --self-contained-html \
                        --junit-xml="${REPORT_DIR}/smoke_junit.xml" \
                        --timeout=60 \
                        -v
                """
            }
            post {
                always {
                    junit "${REPORT_DIR}/smoke_junit.xml"
                }
                failure {
                    error "Smoke tests FAILED — skipping full suite"
                }
            }
        }

        stage('Integration Tests') {
            when { expression { params.TEST_SUITE != 'smoke' } }
            steps {
                sh """
                    pytest tests/ -m "${params.TEST_SUITE}" \
                        --html="${REPORT_DIR}/report.html" \
                        --self-contained-html \
                        --junit-xml="${REPORT_DIR}/junit.xml" \
                        --cov=libraries \
                        --cov-report=html:"${REPORT_DIR}/coverage" \
                        --timeout=120 \
                        -v --tb=short
                """
            }
        }

        stage('Robot Framework Tests') {
            steps {
                sh """
                    robot \
                        --outputdir "${REPORT_DIR}/robot" \
                        --loglevel INFO \
                        --variable DEVICE_NAME:"${DEVICE_NAME}" \
                        tests/robot/
                """
            }
            post {
                always {
                    // Archive RF report
                    publishHTML(target: [
                        reportDir:   "${REPORT_DIR}/robot",
                        reportFiles: 'report.html',
                        reportName:  'Robot Framework Report',
                        keepAll:     true,
                    ])
                }
            }
        }

        stage('Release Gate') {
            steps {
                sh """
                    python tools/release_gate.py \
                        --reports-dir "${REPORT_DIR}" \
                        --min-pass-rate 0.95
                """
            }
        }

        stage('Publish Reports') {
            always {
                steps {
                    junit "${REPORT_DIR}/junit.xml"
                    publishHTML(target: [
                        reportDir:   "${REPORT_DIR}",
                        reportFiles: 'report.html',
                        reportName:  'Test Report',
                        keepAll:     true,
                    ])
                    publishHTML(target: [
                        reportDir:   "${REPORT_DIR}/coverage",
                        reportFiles: 'index.html',
                        reportName:  'Coverage Report',
                        keepAll:     true,
                    ])
                    archiveArtifacts artifacts: 'reports/**', fingerprint: true
                }
            }
        }

        stage('Create JIRA Bugs') {
            when { expression { currentBuild.result == 'FAILURE' } }
            steps {
                sh """
                    python tools/jira_bug_creator.py \
                        --junit "${REPORT_DIR}/junit.xml" \
                        --fw-version "${params.FW_VERSION}" \
                        --jira-url "${JIRA_URL}" \
                        --jira-token "${JIRA_TOKEN}"
                """
            }
        }
    }

    post {
        success {
            slackSend(
                channel: '#power-tool-ci',
                color: 'good',
                message: ":white_check_mark: ${params.TEST_SUITE} PASSED | " +
                         "FW: ${params.FW_VERSION} | ${BUILD_URL}"
            )
        }
        failure {
            slackSend(
                channel: '#power-tool-ci',
                color: 'danger',
                message: ":x: ${params.TEST_SUITE} FAILED | " +
                         "FW: ${params.FW_VERSION} | ${BUILD_URL}"
            )
            emailext(
                subject: "BUILD FAILED: ${JOB_NAME} #${BUILD_NUMBER}",
                body: "See: ${BUILD_URL}",
                to: 'test-team@company.com',
            )
        }
        always {
            cleanWs(patterns: [[pattern: 'reports/**', type: 'EXCLUDE']])
        }
    }
}
```

---

## 3. Azure DevOps Pipeline

```yaml
# azure-pipelines.yml — Power Tool Test Automation Pipeline

trigger:
  branches:
    include:
      - main
      - develop
      - release/*
  paths:
    include:
      - firmware/**
      - tests/**

pr:
  branches:
    include:
      - main
      - develop

pool:
  name: 'SelfHosted-TestBench'    # Agent pool with physical test hardware
  demands:
    - PowerToolBench -equals true  # Only agents with this capability

variables:
  - group: PowerTool-Secrets      # Variable group (API keys, device configs)
  - name: FW_PATH
    value: '$(Build.ArtifactStagingDirectory)/firmware.hex'
  - name: REPORT_DIR
    value: '$(Build.ArtifactStagingDirectory)/reports'
  - name: PYTHON_VERSION
    value: '3.11'

stages:

  # ── Stage 1: Build and unit tests (no hardware needed) ──────────────────
  - stage: BuildAndUnitTest
    displayName: 'Build & Unit Tests'
    jobs:
      - job: UnitTests
        displayName: 'Python Unit Tests (no hardware)'
        pool:
          vmImage: 'ubuntu-latest'      # Hosted agent, no hardware
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: $(PYTHON_VERSION)

          - script: pip install -r requirements.txt
            displayName: 'Install dependencies'

          - script: |
              pytest tests/unit/ \
                -m "not hardware" \
                --junit-xml=$(REPORT_DIR)/unit_junit.xml \
                --cov=libraries \
                --cov-report=xml:$(REPORT_DIR)/coverage.xml \
                -v
            displayName: 'Run unit tests'

          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '$(REPORT_DIR)/unit_junit.xml'
              testRunTitle: 'Unit Tests'
            condition: always()

          - task: PublishCodeCoverageResults@1
            inputs:
              codeCoverageTool: 'Cobertura'
              summaryFileLocation: '$(REPORT_DIR)/coverage.xml'

  # ── Stage 2: Hardware integration tests ─────────────────────────────────
  - stage: HardwareTests
    displayName: 'Hardware Integration Tests'
    dependsOn: BuildAndUnitTest
    condition: succeeded()
    jobs:

      - job: FlashAndSmoke
        displayName: 'Flash Firmware + Smoke Tests'
        timeoutInMinutes: 30
        steps:
          - download: current
            artifact: firmware

          - task: UsePythonVersion@0
            inputs:
              versionSpec: $(PYTHON_VERSION)

          - script: pip install -r requirements.txt
            displayName: 'Install dependencies'

          - script: |
              python tools/flash_device.py \
                --firmware $(Pipeline.Workspace)/firmware/powertool.hex \
                --port $(DEVICE_PORT) \
                --verify
            displayName: 'Flash firmware to device'
            env:
              DEVICE_PORT: $(DeviceSerialPort)   # From variable group

          - script: |
              pytest tests/ -m smoke \
                --junit-xml=$(REPORT_DIR)/smoke_junit.xml \
                --html=$(REPORT_DIR)/smoke_report.html \
                --self-contained-html \
                --timeout=60 -v
            displayName: 'Smoke tests'

          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '$(REPORT_DIR)/smoke_junit.xml'
              testRunTitle: 'Smoke Tests'
            condition: always()

      - job: RegressionTests
        displayName: 'Full Regression Suite'
        dependsOn: FlashAndSmoke
        timeoutInMinutes: 120
        steps:
          - script: |
              pytest tests/ -m "regression and not slow" \
                --junit-xml=$(REPORT_DIR)/regression_junit.xml \
                --html=$(REPORT_DIR)/regression_report.html \
                --self-contained-html \
                --timeout=300 -v --tb=short
            displayName: 'Regression tests'

          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '$(REPORT_DIR)/regression_junit.xml'
              testRunTitle: 'Regression Tests'
            condition: always()

          - task: PublishBuildArtifacts@1
            inputs:
              pathToPublish: '$(REPORT_DIR)'
              artifactName: 'TestReports'
            condition: always()

      - job: RobotFrameworkTests
        displayName: 'Robot Framework Integration'
        dependsOn: FlashAndSmoke
        timeoutInMinutes: 60
        steps:
          - script: |
              robot \
                --outputdir $(REPORT_DIR)/robot \
                --loglevel INFO \
                --variable DEVICE_NAME:$(DeviceName) \
                --xunit $(REPORT_DIR)/robot_xunit.xml \
                tests/robot/
            displayName: 'Robot Framework tests'

          - task: PublishTestResults@2
            inputs:
              testResultsFormat: 'JUnit'
              testResultsFiles: '$(REPORT_DIR)/robot_xunit.xml'
              testRunTitle: 'Robot Framework'
            condition: always()
```

---

## 4. Parallel Execution Across Multiple Bench Nodes

```groovy
// Jenkinsfile — Parallel execution on multiple hardware nodes

pipeline {
    agent none   // No default agent — each stage declares its own

    stages {
        stage('Parallel Hardware Tests') {
            parallel {

                stage('BLE Tests — Bench 01') {
                    agent { label 'bench-01' }
                    steps {
                        sh """
                            pytest tests/ -m ble \
                                --junit-xml=reports/ble_bench01.xml \
                                -v
                        """
                    }
                    post {
                        always {
                            stash name: 'ble-results', includes: 'reports/*.xml'
                        }
                    }
                }

                stage('UART Tests — Bench 02') {
                    agent { label 'bench-02' }
                    steps {
                        sh """
                            pytest tests/ -m uart \
                                --junit-xml=reports/uart_bench02.xml \
                                -v
                        """
                    }
                    post {
                        always {
                            stash name: 'uart-results', includes: 'reports/*.xml'
                        }
                    }
                }

                stage('Accuracy Tests — Bench 03') {
                    agent { label 'bench-03' }
                    steps {
                        sh """
                            pytest tests/ -m accuracy \
                                --junit-xml=reports/accuracy_bench03.xml \
                                -v
                        """
                    }
                    post {
                        always {
                            stash name: 'accuracy-results', includes: 'reports/*.xml'
                        }
                    }
                }
            }
        }

        stage('Merge Reports') {
            agent { label 'main' }
            steps {
                unstash 'ble-results'
                unstash 'uart-results'
                unstash 'accuracy-results'
                sh """
                    python tools/merge_junit.py \
                        reports/ble_bench01.xml \
                        reports/uart_bench02.xml \
                        reports/accuracy_bench03.xml \
                        --output reports/combined_junit.xml
                """
                junit 'reports/combined_junit.xml'
            }
        }
    }
}
```

---

## 5. Release Gate Script

```python
"""
tools/release_gate.py — Automated release gate enforcement.
Called by Jenkins/Azure — exits non-zero if criteria not met.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass

@dataclass
class SuiteResult:
    name:    str
    total:   int
    passed:  int
    failed:  int
    errors:  int

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def skipped(self) -> int:
        return self.total - self.passed - self.failed - self.errors


def parse_junit(path: Path) -> SuiteResult:
    tree = ET.parse(path)
    root = tree.getroot()
    # Handle both <testsuite> root and <testsuites> wrapper
    if root.tag == "testsuites":
        suites = root.findall("testsuite")
        total   = sum(int(s.get("tests",    0)) for s in suites)
        failed  = sum(int(s.get("failures", 0)) for s in suites)
        errors  = sum(int(s.get("errors",   0)) for s in suites)
    else:
        total  = int(root.get("tests",    0))
        failed = int(root.get("failures", 0))
        errors = int(root.get("errors",   0))

    return SuiteResult(
        name=path.stem,
        total=total,
        passed=total - failed - errors,
        failed=failed,
        errors=errors,
    )


GATE_CRITERIA = {
    # file_stem:      (min_pass_rate, is_blocking)
    "smoke_junit":    (1.00, True),    # 100% mandatory
    "regression_junit": (0.95, True),  # 95% mandatory
    "robot_xunit":    (0.90, True),    # 90% mandatory
}

def main():
    parser = argparse.ArgumentParser(description="Release gate evaluation")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--min-pass-rate", type=float, default=0.95)
    parser.add_argument("--output-json", default="reports/gate_result.json")
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    all_pass = True
    results = []

    print("=" * 65)
    print("  RELEASE GATE EVALUATION")
    print("=" * 65)

    for stem, (threshold, blocking) in GATE_CRITERIA.items():
        xml_path = reports_dir / f"{stem}.xml"
        if not xml_path.exists():
            marker = "MISSING"
            if blocking:
                all_pass = False
                print(f"  [MISSING] {stem} — required result file not found")
            else:
                print(f"  [SKIP]    {stem} — optional, not found")
            continue

        suite = parse_junit(xml_path)
        ok = suite.pass_rate >= threshold
        if not ok and blocking:
            all_pass = False

        marker = "PASS" if ok else "FAIL"
        note   = "" if blocking else " (non-blocking)"
        print(f"  [{marker}] {suite.name}: "
              f"{suite.passed}/{suite.total} "
              f"({suite.pass_rate*100:.1f}% >= {threshold*100:.0f}%){note}")
        results.append({
            "suite":      suite.name,
            "pass_rate":  suite.pass_rate,
            "threshold":  threshold,
            "passed":     ok,
            "blocking":   blocking,
        })

    print("=" * 65)
    verdict = "PASSED" if all_pass else "FAILED"
    print(f"  GATE: {verdict}")
    print("=" * 65)

    gate_output = {
        "verdict": verdict,
        "all_pass": all_pass,
        "suites": results,
    }
    Path(args.output_json).write_text(json.dumps(gate_output, indent=2))

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
```

---

## 6. Git Hooks for Pre-commit Quality

```bash
#!/bin/sh
# .git/hooks/pre-commit — Run quality checks before every commit
# Install: chmod +x .git/hooks/pre-commit

echo "Running pre-commit checks..."

# 1. Run linter (ruff is faster than flake8)
ruff check libraries/ tests/ tools/
if [ $? -ne 0 ]; then
    echo "Lint errors found. Fix before committing."
    exit 1
fi

# 2. Run unit tests (fast, no hardware)
pytest tests/unit/ -m "not hardware" -q --timeout=30
if [ $? -ne 0 ]; then
    echo "Unit tests failed. Fix before committing."
    exit 1
fi

echo "Pre-commit checks passed."
exit 0
```

---

## 7. Interview Q&A

**Q1: What is the difference between a Jenkins Declarative and Scripted pipeline?**  
Declarative pipeline uses a structured `pipeline {}` block with predefined sections (`stages`, `steps`, `post`) — easier to read, has built-in validation, and is the modern recommended approach. Scripted pipeline is pure Groovy (`node {}`) with full programming flexibility but harder to read and no structural validation. I use Declarative for standard CI pipelines (build, test, report) and only drop to Scripted blocks inside `script {}` when I need dynamic logic like conditional stage creation or complex loops.

**Q2: How do you prevent a flashing failure from running tests on stale firmware?**  
Add a `post { failure { error "Flash FAILED" } }` block after the flash stage. The `error` step aborts the pipeline immediately. Combine this with `when { expression { currentBuild.result != 'FAILURE' } }` on subsequent stages. In Azure DevOps, use `dependsOn` with `condition: succeeded()`. The key principle: if you can't trust the device state, running tests wastes time and produces misleading results.

**Q3: How do you run tests in parallel across multiple hardware benches in Jenkins?**  
Use the `parallel` block in Declarative pipeline with each branch targeting a specific agent via `agent { label 'bench-01' }`. Tests are split by marker (`-m ble`, `-m uart`, `-m accuracy`). After parallel completion, a `Merge Reports` stage runs on the main agent, uses `unstash` to collect all JUnit XMLs, and generates a combined report. This scales linearly: 4 benches = 4× speed with no code changes to the tests themselves.

**Q4: What is an Azure DevOps variable group and why use it instead of hardcoding?**  
A variable group is a named set of key-value pairs stored in Azure DevOps that can be marked secret (encrypted) and referenced in pipelines. Benefits: (1) Secrets (API keys, passwords) are never in source code; (2) Environment-specific values (device port, server URL) vary between staging and production — use different variable groups per environment; (3) One change to the variable group updates all pipelines that use it, no code change needed. Reference it in YAML with `- group: MyVariableGroup` under `variables:`.

**Q5: How do you handle a pipeline that tests across different OS (Windows for BLE + Linux for embedded)?**  
In Jenkins: use `matrix` or `parallel` with different `agent { label }` per OS. In Azure DevOps: use a matrix strategy or parallel jobs with different `pool.vmImage` values (`windows-latest` vs `ubuntu-latest`). For BLE testing specifically, COM port names differ (`COM5` on Windows, `/dev/ttyUSB0` on Linux) — abstract this via environment variables set per-agent or stored in the variable group. The test code uses `config["uart"]["port"]` loaded from a YAML that differs per node.
