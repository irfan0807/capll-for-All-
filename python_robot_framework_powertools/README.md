# Python & Robot Framework — Power Tools Test Automation
## Complete Learning Guide

> **Role**: Python & Robot Framework Developer — Power Tools Domain  
> **Target**: System, integration, and regression test automation for embedded + BLE devices  
> **Level**: Mid–Senior Automation Engineer

---

## Course Map

| # | Document | Topics Covered | Difficulty |
|---|----------|----------------|------------|
| 01 | [Python Core Skills](01_Python_Core_Skills.md) | stdlib, multithreading, file I/O, OOP, subprocess, OS interaction | Intermediate |
| 02 | [Robot Framework Fundamentals](02_Robot_Framework_Fundamentals.md) | RF architecture, keywords, libraries, resource files, listeners | Intermediate |
| 03 | [BLE, UART & Serial Communication](03_BLE_UART_Serial_Communication.md) | BLE GAP/GATT, bleak, pyserial, UART protocol testing | Advanced |
| 04 | [Pytest Advanced](04_Pytest_Advanced.md) | Fixtures, parametrize, markers, plugins, coverage, REST API | Intermediate |
| 05 | [CI/CD — Jenkins & Azure DevOps](05_CI_CD_Jenkins_Azure.md) | Jenkins pipelines, Azure DevOps, parallel execution, reporting | Advanced |
| 06 | [Framework Architecture Design](06_Framework_Architecture_Design.md) | OOP patterns, keyword-driven, data-driven, hybrid frameworks | Advanced |
| 07 | [Agile, JIRA & RCA](07_Agile_JIRA_Confluence.md) | Scrum, JIRA REST API, bug reporting, root cause analysis | Intermediate |
| 08 | [Power Tools Domain Testing](08_Power_Tools_Domain_Testing.md) | BLE device validation, measuring tools, mobile app, real-time | Advanced |

---

## Learning Path

### Week 1–2: Python & pytest Foundation
```
Day 1–3:   01_Python_Core_Skills.md
           → multithreading, file I/O, OOP, subprocess

Day 4–5:   04_Pytest_Advanced.md
           → fixtures, parametrize, markers, coverage
```

### Week 3–4: Robot Framework
```
Day 6–9:   02_Robot_Framework_Fundamentals.md
           → test suites, keyword libraries, resource files, variables

Day 10:    06_Framework_Architecture_Design.md
           → keyword-driven, data-driven, hybrid patterns
```

### Week 5–6: Communication Protocols
```
Day 11–14: 03_BLE_UART_Serial_Communication.md
           → BLE GAP/GATT, bleak, pyserial, protocol tests

Day 15:    08_Power_Tools_Domain_Testing.md
           → BLE device + measuring tool validation
```

### Week 7–8: CI/CD & Process
```
Day 16–17: 05_CI_CD_Jenkins_Azure.md
           → Jenkins pipelines, Azure DevOps, parallel execution

Day 18–19: 07_Agile_JIRA_Confluence.md
           → Scrum ceremonies, JIRA REST API, RCA methodology

Day 20:    Review all — practice interview Q&As
```

---

## Skills Map to Job Requirements

| Job Requirement | Document(s) | Key Concepts |
|-----------------|------------|--------------|
| Strong Python proficiency | 01, 04, 06 | stdlib, threading, I/O, OOP |
| Robot Framework expertise | 02, 06 | Test suites, custom keywords, libraries |
| pytest expertise | 04 | Fixtures, markers, xdist, coverage |
| BLE domain knowledge | 03, 08 | GAP, GATT, bleak, scanning, notifications |
| UART / serial interfaces | 03 | pyserial, framing, timeout handling |
| OOP & modular frameworks | 06 | Factory, Strategy, Observer patterns |
| System/integration/regression testing | 02, 04, 08 | Test pyramid, scope, strategy |
| Git version control | 05 | Branching, hooks, CI triggers |
| Agile / Scrum | 07 | Sprints, ceremonies, story points |
| Jenkins CI/CD pipelines | 05 | Jenkinsfile, agents, stages, reports |
| Azure DevOps | 05 | Pipelines, artifacts, test reporting |
| JIRA + Confluence | 07 | REST API, bug templates, RCA |
| REST API testing | 04 | requests, pytest, schema validation |
| Mentoring / leading teams | 07, 06 | Code reviews, framework documentation |
| Power tools embedded testing | 08 | Real-time validation, device lifecycle |

---

## Interview Readiness Checklist

```
□ Explain the difference between pytest and Robot Framework — when to use each
□ Write a custom Robot Framework keyword library in Python
□ Implement BLE scanning and GATT characteristic read in Python (bleak)
□ Write a pyserial UART communication class with timeout/retry
□ Design a modular test framework with Page Object / Keyword-Driven pattern
□ Describe your CI pipeline: Git push → Jenkins → test → report → notify
□ Explain how you do Root Cause Analysis on a flaky test
□ Describe how you derive test cases from requirements
□ Explain how you mentored a junior engineer on automation practices
□ Demonstrate JIRA REST API bug creation from test results
```

---

## Target Companies / Roles

- **Power tool OEMs**: Bosch, Hilti, Stanley Black & Decker, Milwaukee Tool, Makita
- **Tool connectivity**: BLE-enabled smart tools (measurements, diagnostics)
- **Mobile app integration**: iOS/Android companion apps for tools
- **Embedded test**: Factory floor test systems, production validation

---

## Key Python Packages Used in This Course

```bash
# Install all at once
pip install pytest pytest-html pytest-xdist pytest-cov
pip install robotframework robotframework-seleniumlibrary
pip install bleak pyserial
pip install requests pydantic jsonschema
pip install python-can
pip install coverage
```
