# Robot Framework — Complete Learning Guide
### From Zero to Automotive Test Automation Expert

---

## TABLE OF CONTENTS

1. [What is Robot Framework?](#1-what-is-robot-framework)
2. [Architecture & How It Works](#2-architecture--how-it-works)
3. [Installation & Setup](#3-installation--setup)
4. [Core Syntax — The Basics](#4-core-syntax--the-basics)
5. [Variables](#5-variables)
6. [Keywords — The Heart of Robot](#6-keywords--the-heart-of-robot)
7. [Test Suites & Test Cases](#7-test-suites--test-cases)
8. [Control Flow — Loops, Conditions, Branching](#8-control-flow--loops-conditions-branching)
9. [Built-In Libraries](#9-built-in-libraries)
10. [Standard Libraries](#10-standard-libraries)
11. [External Libraries — Selenium, Requests, SSH](#11-external-libraries--selenium-requests-ssh)
12. [Resource Files & Modular Architecture](#12-resource-files--modular-architecture)
13. [Tags, Filtering & Execution](#13-tags-filtering--execution)
14. [Setup, Teardown & Fixtures](#14-setup-teardown--fixtures)
15. [Data-Driven Testing](#15-data-driven-testing)
16. [Custom Python Libraries](#16-custom-python-libraries)
17. [Robot Framework in Automotive Testing](#17-robot-framework-in-automotive-testing)
18. [CI/CD Integration](#18-cicd-integration)
19. [Reports & Logging](#19-reports--logging)
20. [Best Practices & Common Mistakes](#20-best-practices--common-mistakes)
21. [STAR Scenarios — Real Interview Examples](#21-star-scenarios--real-interview-examples)
22. [Quick Reference Cheat Sheet](#22-quick-reference-cheat-sheet)

---

## 1. What is Robot Framework?

**Robot Framework** is an open-source, keyword-driven test automation framework written in Python. It was created by Nokia Networks and released to the public in 2008. Today it is one of the most widely used test automation frameworks globally — including in the automotive industry.

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                    ROBOT FRAMEWORK AT A GLANCE                           │
  │                                                                          │
  │  Language:      Python (but tests are written in a readable DSL)         │
  │  Test style:    Keyword-Driven / Data-Driven / BDD (Gherkin-like)        │
  │  License:       Apache License 2.0                                       │
  │  Website:       https://robotframework.org                               │
  │  PyPI:          pip install robotframework                               │
  │  File extension: .robot  or  .resource                                   │
  │                                                                          │
  │  Core philosophy:                                                        │
  │  "Test cases should be readable by non-programmers"                      │
  │  Keywords describe WHAT to do, not HOW to do it                         │
  └──────────────────────────────────────────────────────────────────────────┘
```

### Why Robot Framework Matters

| Problem | How Robot Solves It |
|---------|-------------------|
| Tests too technical, QA can't write them | Plain English keyword syntax |
| Code duplication across test cases | Reusable keyword libraries |
| Hard to scale across teams | Resource files + modular design |
| No unified reports | Built-in HTML reports + logs |
| Locked to one technology | Library plugins: Web, API, DB, SSH, CAN, etc. |
| Not readable by product owners | BDD-style Given/When/Then syntax |

### Where Robot Framework is Used in Automotive

```
  Automotive Test Scope — Robot Framework Coverage:
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │  ┌────────────────────┐   ┌──────────────────────┐                      │
  │  │  ECU HIL Testing   │   │  OTA Update Testing  │                      │
  │  │  via CAN/UDS       │   │  via REST API        │                      │
  │  └────────────────────┘   └──────────────────────┘                      │
  │                                                                          │
  │  ┌────────────────────┐   ┌──────────────────────┐                      │
  │  │  Infotainment UI   │   │  Diagnostics (UDS)   │                      │
  │  │  via Selenium/     │   │  via python-can /    │                      │
  │  │  Appium            │   │  CANoe Python API    │                      │
  │  └────────────────────┘   └──────────────────────┘                      │
  │                                                                          │
  │  ┌────────────────────┐   ┌──────────────────────┐                      │
  │  │  ADAS Validation   │   │  Regression Testing  │                      │
  │  │  via simulation    │   │  in CI/CD pipelines  │                      │
  │  │  tool APIs         │   │  (Jenkins/GitLab)    │                      │
  │  └────────────────────┘   └──────────────────────┘                      │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture & How It Works

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                    ROBOT FRAMEWORK ARCHITECTURE                        │
  ├────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  ┌─────────────────────────────────────────────────────────────┐      │
  │  │              TEST DATA LAYER (.robot files)                  │      │
  │  │   Test Suites → Test Cases → Keywords → Arguments           │      │
  │  └──────────────────────────┬──────────────────────────────────┘      │
  │                             │                                          │
  │                             ▼                                          │
  │  ┌─────────────────────────────────────────────────────────────┐      │
  │  │              ROBOT FRAMEWORK CORE                           │      │
  │  │                                                             │      │
  │  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐  │      │
  │  │  │   Parser     │  │   Executor    │  │   Reporter     │  │      │
  │  │  │  .robot →    │  │  Runs keywords│  │  output.xml →  │  │      │
  │  │  │  AST model   │  │  in order     │  │  report.html   │  │      │
  │  │  └──────────────┘  └───────────────┘  └────────────────┘  │      │
  │  └──────────────────────────┬──────────────────────────────────┘      │
  │                             │                                          │
  │                             ▼                                          │
  │  ┌─────────────────────────────────────────────────────────────┐      │
  │  │                   LIBRARY LAYER                             │      │
  │  │                                                             │      │
  │  │  Built-In    Standard      External        Custom          │      │
  │  │  BuiltIn     Collections   SeleniumLibrary YourLib.py      │      │
  │  │  String      OperatingSystem RequestsLibrary CANLibrary     │      │
  │  │  DateTime    Process       SSHLibrary      UDSKeywords     │      │
  │  └─────────────────────────────────────────────────────────────┘      │
  │                             │                                          │
  │                             ▼                                          │
  │  ┌─────────────────────────────────────────────────────────────┐      │
  │  │              SYSTEM UNDER TEST (SUT)                        │      │
  │  │  Browser / REST API / ECU / Database / OS / CAN Bus / SSH  │      │
  │  └─────────────────────────────────────────────────────────────┘      │
  └────────────────────────────────────────────────────────────────────────┘

  Execution Flow:
  ─────────────────────────────────────────────────────────────────────────
  robot my_tests.robot
       │
       ├─→ Parse .robot files into internal model
       ├─→ Resolve keyword/library references
       ├─→ Execute: Suite Setup → Test Setup → Keywords → Test Teardown → Suite Teardown
       ├─→ Write output.xml during execution
       └─→ Generate report.html + log.html from output.xml
```

### Execution Pipeline — Step by Step

```
  1. robot command invoked
         │
         ▼
  2. Argument parsing (tags, variable overrides, include/exclude filters)
         │
         ▼
  3. Test discovery (find all .robot files matching the path pattern)
         │
         ▼
  4. For each Test Suite:
     ├── Run Suite Setup keyword (if defined)
     ├── For each Test Case:
     │   ├── Run Test Setup keyword (if defined)
     │   ├── Run Test Case keywords line by line
     │   │   ├── If keyword PASSES → continue
     │   │   └── If keyword FAILS → mark test FAILED, run teardown
     │   └── Run Test Teardown keyword (if defined, runs even if test failed)
     └── Run Suite Teardown keyword (if defined)
         │
         ▼
  5. Write output.xml
         │
         ▼
  6. Generate report.html and log.html
```

---

## 3. Installation & Setup

### Install Robot Framework Core

```bash
# Robot Framework core
pip install robotframework

# Verify installation
robot --version
# Robot Framework 7.x.x (Python 3.x.x)
```

### Install Common Libraries

```bash
# Web UI testing
pip install robotframework-seleniumlibrary
pip install selenium
pip install webdrivermanager

# REST API testing
pip install robotframework-requests

# SSH / remote testing
pip install robotframework-sshlibrary

# Database testing
pip install robotframework-databaselibrary
pip install PyMySQL   # or psycopg2 for PostgreSQL

# Browser testing (Microsoft's newer alternative)
pip install robotframework-browser
rfbrowser init

# Excel / Data files
pip install robotframework-excellib
pip install openpyxl
```

### Automotive-Specific Dependencies

```bash
# CAN bus communication
pip install python-can
pip install cantools   # DBC parser

# UDS diagnostics
pip install udsoncan
pip install python-can

# CANoe Python scripting (if using Vector CANoe)
# COM API available on Windows — no pip install needed,
# import win32com.client in your library

# Pytest integration (run robot via pytest)
pip install robotframework-pytest
```

### Project Directory Structure (Recommended)

```
  my_robot_project/
  │
  ├── tests/                    ← Test Suite folders
  │   ├── smoke/
  │   │   └── login_tests.robot
  │   ├── regression/
  │   │   └── ecu_tests.robot
  │   └── diagnostics/
  │       └── uds_tests.robot
  │
  ├── resources/                ← Reusable keywords
  │   ├── common_keywords.resource
  │   ├── uds_keywords.resource
  │   └── can_keywords.resource
  │
  ├── libraries/                ← Custom Python libraries
  │   ├── CANLibrary.py
  │   ├── UDSLibrary.py
  │   └── VehicleSimulator.py
  │
  ├── variables/                ← Variable files
  │   ├── dev_env.yaml
  │   ├── test_env.yaml
  │   └── prod_env.yaml
  │
  ├── data/                     ← Test data files
  │   ├── test_data.csv
  │   └── dtc_codes.json
  │
  ├── results/                  ← Generated reports (gitignored)
  │   ├── output.xml
  │   ├── report.html
  │   └── log.html
  │
  └── robot.yaml / pabot.yaml   ← Execution configuration
```

---

## 4. Core Syntax — The Basics

### The Four Sections of a .robot File

```robot
*** Settings ***
# Metadata and imports — what libraries and resources to use

*** Variables ***
# File-level variables

*** Test Cases ***
# The actual test cases

*** Keywords ***
# Reusable keyword implementations (for this file)
```

### Your First Robot File

```robot
*** Settings ***
Library    Collections
Library    String

*** Variables ***
${BASE_URL}       https://api.example.com
${TIMEOUT}        30s
${VEHICLE_VIN}    WBA12345678901234

*** Test Cases ***

My First Test Case
    [Documentation]    This is a simple test to verify Robot syntax
    ${result}=    Evaluate    2 + 2
    Should Be Equal As Integers    ${result}    4
    Log    Calculation result: ${result}

Another Test Case
    [Tags]    smoke    sanity
    ${name}=    Set Variable    Robot Framework
    Should Contain    ${name}    Robot
    Should Not Be Empty    ${name}
    Log    Name is: ${name}    level=INFO

*** Keywords ***

My Custom Keyword
    [Arguments]    ${input_value}
    [Documentation]    Doubles the input value
    ${doubled}=    Evaluate    ${input_value} * 2
    [Return]    ${doubled}
```

### Indentation Rules

```
  Robot Framework uses SPACE (not tabs) for indentation.
  Minimum 2 spaces between keyword name and its arguments.
  Recommended: 4 spaces consistently.

  CORRECT:
  ┌──────────────────────────────────────────────────────┐
  │ My Test                                              │
  │     Log    Hello World          ← 4 spaces indent   │
  │     ${x}=    Set Variable    5  ← 4 spaces indent   │
  └──────────────────────────────────────────────────────┘

  WRONG (single space — Robot cannot distinguish keyword from argument):
  ┌──────────────────────────────────────────────────────┐
  │ My Test                                              │
  │  Log Hello World                ← looks like args   │
  └──────────────────────────────────────────────────────┘
```

---

## 5. Variables

### Variable Types

```robot
*** Variables ***

# SCALAR — single value (most common)
${NAME}           John Doe
${SPEED_KMH}      120
${IS_ACTIVE}      ${True}
${EMPTY_VALUE}    ${EMPTY}

# LIST — ordered collection
@{COLORS}         red    green    blue    yellow
@{ECU_IDS}        0x01   0x02     0x05    0x10

# DICTIONARY — key-value pairs
&{VEHICLE}        make=Toyota    model=Camry    year=2024    color=white
&{DTC_CODES}      P0100=MAF Sensor    P0200=Injector    P0300=Misfire

# ENVIRONMENT VARIABLE — from OS
${HOME_DIR}       %{HOME}
${CI_BUILD}       %{CI_BUILD_NUMBER}
```

### Scalar Variables — All Forms

```robot
*** Test Cases ***

Variable Examples
    # String
    ${msg}=    Set Variable    Hello Automotive World
    Log    ${msg}

    # Integer
    ${count}=    Set Variable    ${42}
    ${result}=    Evaluate    ${count} * 2

    # Float
    ${pi}=    Set Variable    ${3.14159}

    # Boolean
    ${flag}=    Set Variable    ${True}
    ${flag2}=    Set Variable    ${False}

    # None
    ${nothing}=    Set Variable    ${None}

    # Multiline
    ${long_text}=    Set Variable
    ...    This is a very long value
    ...    that spans multiple lines
    ...    using the continuation marker (...)
```

### List Variables

```robot
*** Test Cases ***

List Variable Examples
    # Create list
    @{fruits}=    Create List    apple    banana    cherry
    Log    ${fruits}                    # prints full list
    Log    ${fruits}[0]                 # apple (index 0)
    Log    ${fruits}[-1]                # cherry (last element)

    # Get length
    ${length}=    Get Length    ${fruits}
    Should Be Equal As Integers    ${length}    3

    # Append to list
    Append To List    ${fruits}    date
    Log    ${fruits}[3]                 # date

    # Loop over list
    FOR    ${fruit}    IN    @{fruits}
        Log    Current fruit: ${fruit}
    END

    # List from @{} notation (expands as separate arguments)
    Log Many    @{fruits}              # logs each element separately
```

### Dictionary Variables

```robot
*** Test Cases ***

Dictionary Variable Examples
    # Create dictionary
    &{car}=    Create Dictionary    make=BMW    model=3 Series    year=2024

    # Access by key
    Log    ${car}[make]                # BMW
    Log    ${car.model}                # 3 Series (dot notation)

    # Set item
    Set To Dictionary    ${car}    color    white

    # Check key exists
    Dictionary Should Contain Key    ${car}    make

    # Get all keys
    ${keys}=    Get Dictionary Keys    ${car}
    Log    ${keys}

    # Loop over dictionary
    FOR    ${key}    ${value}    IN    &{car}
        Log    ${key} = ${value}
    END
```

### Variable Scopes

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                        VARIABLE SCOPE HIERARCHY                        │
  ├────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  GLOBAL scope ── visible everywhere (set via -v flag or Set Global)   │
  │    │                                                                   │
  │    └── SUITE scope ── visible in all tests in suite (Set Suite Var)   │
  │          │                                                             │
  │          └── TEST scope ── visible in current test (Set Test Var)     │
  │                │                                                       │
  │                └── LOCAL scope ── within current keyword only         │
  │                                   (${var}= Set Variable ...)          │
  └────────────────────────────────────────────────────────────────────────┘
```

```robot
*** Test Cases ***

Variable Scope Demo
    Set Global Variable    ${GLOBAL_VAR}    I am everywhere
    Set Suite Variable     ${SUITE_VAR}     I am in this suite
    Set Test Variable      ${TEST_VAR}      I am in this test
    ${local_var}=    Set Variable           I am only here

    Log    ${GLOBAL_VAR}    # works
    Log    ${SUITE_VAR}     # works
    Log    ${TEST_VAR}      # works
    Log    ${local_var}     # works

Another Test
    Log    ${GLOBAL_VAR}    # works — global
    Log    ${SUITE_VAR}     # works — suite
    # ${TEST_VAR} would FAIL here — it was from a different test
    # ${local_var} would FAIL here — it was local
```

---

## 6. Keywords — The Heart of Robot

Keywords are the fundamental building block. Everything in Robot is a keyword.

```
  KEYWORD TYPES:
  ┌────────────────────────────────────────────────────────────────────────┐
  │                                                                        │
  │  1. BUILT-IN keywords — always available (BuiltIn library)            │
  │     Log, Should Be Equal, Set Variable, Run Keyword If, FOR...        │
  │                                                                        │
  │  2. LIBRARY keywords — from imported libraries                         │
  │     SeleniumLibrary: Open Browser, Click Element, Input Text           │
  │     RequestsLibrary: GET On Session, POST On Session                   │
  │                                                                        │
  │  3. USER DEFINED keywords — written in .robot or .resource files       │
  │     or in Python custom library classes                                │
  │                                                                        │
  │  4. EMBEDDED ARGUMENT keywords — natural language style                │
  │     "Check that ${value} is greater than ${threshold}"                 │
  └────────────────────────────────────────────────────────────────────────┘
```

### Defining Keywords

```robot
*** Keywords ***

# Keyword with no arguments
Log System Status
    [Documentation]    Logs current system timestamp and status
    ${timestamp}=    Get Time    epoch
    Log    System running. Timestamp: ${timestamp}    level=INFO

# Keyword with required arguments
Connect To ECU
    [Arguments]    ${can_interface}    ${bitrate}
    [Documentation]    Establishes CAN connection to the ECU
    Log    Connecting to ${can_interface} at ${bitrate} bps
    # ... actual connection logic here

# Keyword with default argument values
Read ECU Parameter
    [Arguments]    ${did}    ${timeout}=5000    ${session}=default
    [Documentation]    Reads a data identifier from the ECU.
    ...    timeout defaults to 5000 ms, session defaults to default
    Log    Reading DID 0x${did} in ${session} session with ${timeout}ms timeout

# Keyword that returns a value
Calculate Checksum
    [Arguments]    ${data_bytes}
    [Documentation]    Returns CRC-8 checksum of the given byte list
    ${checksum}=    Evaluate    sum(${data_bytes}) % 256
    RETURN    ${checksum}

# Keyword with *varargs (variable number of arguments)
Log All Parameters
    [Arguments]    @{params}
    FOR    ${param}    IN    @{params}
        Log    Parameter: ${param}
    END

# Keyword with **kwargs (named arguments)
Create Vehicle Profile
    [Arguments]    &{attributes}
    Log    Creating vehicle with: ${attributes}
    RETURN    ${attributes}
```

### Calling Keywords

```robot
*** Test Cases ***

Keyword Call Examples
    # Simple call
    Log System Status

    # Call with positional arguments
    Connect To ECU    vcan0    500000

    # Call with named arguments (order doesn't matter with named)
    Read ECU Parameter    did=F190    session=extended    timeout=3000

    # Capture return value
    ${crc}=    Calculate Checksum    ${[0x01, 0x02, 0x03]}

    # Call with *varargs
    Log All Parameters    wheel_speed    engine_rpm    oil_temp    fuel_level

    # Call with **kwargs
    ${profile}=    Create Vehicle Profile    make=Toyota    model=Camry    year=2024

    # Nested keyword call (pass result of one keyword into another)
    ${length}=    Get Length    ${profile}
    Should Be Equal As Integers    ${length}    3
```

### Embedded Arguments in Keywords

```robot
*** Keywords ***

# Natural-language style with embedded arguments
${value} should be between ${min} and ${max}
    [Documentation]    Asserts value is within range (inclusive)
    Should Be True    ${value} >= ${min}
    Should Be True    ${value} <= ${max}
    Log    ✓ ${value} is between ${min} and ${max}

Vehicle speed should not exceed ${limit} km/h
    ${speed}=    Get Current Vehicle Speed
    Should Be True    ${speed} <= ${limit}
    ...    msg=Speed ${speed} exceeded limit ${limit} km/h!

*** Test Cases ***

Embedded Keyword Demo
    ${temp}=    Set Variable    ${85}
    ${temp} should be between    ${60}    ${100}

    Vehicle speed should not exceed    ${130} km/h
```

---

## 7. Test Suites & Test Cases

### Test Suite Structure

```robot
*** Settings ***
Documentation      ECU Diagnostic Test Suite
...                Tests the UDS diagnostic protocol implementation
...                on the body control module (BCM)
Metadata           Version    2.3.1
Metadata           Author     Test Engineering Team
Metadata           ECU        BCM_v5.2

Library            Collections
Library            String
Library            OperatingSystem
Resource           ../../resources/uds_keywords.resource
Resource           ../../resources/can_keywords.resource
Variables          ../../variables/test_env.yaml

Suite Setup        Initialize CAN Bus Connection
Suite Teardown     Disconnect From CAN Bus
Test Setup         Reset ECU State
Test Teardown      Log Test Result And Cleanup

Default Tags       regression    uds

*** Test Cases ***

TC_001 - Verify ECU Responds To Tester Present
    [Documentation]    ECU must respond 0x7E to 0x3E 0x00 (TesterPresent)
    [Tags]    smoke    critical    uds-service-3e
    [Timeout]    10s
    Send UDS Request    3E 00
    ${response}=    Receive UDS Response    timeout=2000
    Should Be Equal    ${response}[service_id]    7E
    Should Be Equal    ${response}[sub_function]  00
    Log    ✓ TesterPresent acknowledged

TC_002 - Read ECU Software Version (DID F189)
    [Documentation]    Read VW/AUTOSAR DID F189 — ECU Software Version Number
    [Tags]    read-data    did-f189
    ${response}=    Read Data By Identifier    F189
    Should Match Regexp    ${response}[data]    ^[0-9A-F]{8}$
    Log    ECU SW Version: ${response}[data]
    Set Suite Variable    ${ECU_SW_VERSION}    ${response}[data]

TC_003 - Verify Negative Response For Invalid DID
    [Documentation]    ECU must return NRC 0x31 (requestOutOfRange) for invalid DID
    [Tags]    negative    nrc
    ${response}=    Read Data By Identifier    FFFF
    Should Be Equal    ${response}[response_type]    negative
    Should Be Equal    ${response}[nrc]              31
    Log    ✓ Correct NRC 0x31 received for invalid DID
```

### Test Case Metadata

```robot
*** Test Cases ***

Complete Test Case Example
    [Documentation]    This is the test case description.
    ...                Can span multiple lines using ...
    ...                Markdown is supported in newer versions.

    [Tags]             smoke    regression    jira-1234    priority-high

    [Setup]            Log    This runs before THIS test only

    [Teardown]         Log    This runs after THIS test (even if failed)

    [Timeout]          60s    # test fails if it takes longer than 60 seconds

    [Template]         My Template Keyword    # for data-driven tests

    # Test body
    Log    Running test...
```

---

## 8. Control Flow — Loops, Conditions, Branching

### FOR Loops

```robot
*** Test Cases ***

FOR Loop Examples

    # Basic FOR loop over list
    @{dids}=    Create List    F190    F189    F18C    0110
    FOR    ${did}    IN    @{dids}
        ${response}=    Read Data By Identifier    ${did}
        Log    DID ${did}: ${response}[data]
    END

    # FOR loop with range (like Python range())
    FOR    ${i}    IN RANGE    1    11    # 1 to 10
        Log    Iteration: ${i}
    END

    FOR    ${i}    IN RANGE    0    100    10   # 0, 10, 20...90
        Log    Step: ${i}
    END

    # FOR loop with index (enumerate)
    FOR    ${index}    ${item}    IN ENUMERATE    apple    banana    cherry
        Log    Item ${index}: ${item}     # Item 0: apple, Item 1: banana...
    END

    # FOR loop over dictionary
    &{params}=    Create Dictionary    speed=60    rpm=2000    temp=90
    FOR    ${key}    ${value}    IN    &{params}
        Log    ${key} = ${value}
    END

    # BREAK and CONTINUE
    FOR    ${i}    IN RANGE    1    20
        IF    ${i} == 5
            CONTINUE    # skip iteration 5
        END
        IF    ${i} == 10
            BREAK       # stop loop at 10
        END
        Log    Processing: ${i}
    END
```

### IF / ELSE IF / ELSE

```robot
*** Test Cases ***

Conditional Logic Examples

    ${temperature}=    Set Variable    ${95}

    # Basic IF
    IF    ${temperature} > 100
        Log    WARNING: Overheating!
    END

    # IF / ELSE
    IF    ${temperature} > 80
        Log    Temperature is HIGH: ${temperature}°C
    ELSE
        Log    Temperature is normal: ${temperature}°C
    END

    # IF / ELSE IF / ELSE
    IF    ${temperature} < 60
        Log    COLD — heater may be needed
    ELSE IF    ${temperature} < 85
        Log    NORMAL operating temperature
    ELSE IF    ${temperature} < 100
        Log    WARM — within limits but elevated
    ELSE
        Log    CRITICAL — thermal protection will activate
        Fail    Temperature exceeded safety threshold!
    END

    # Inline IF (single line, no END needed)
    Run Keyword If    ${temperature} > 90    Log    Elevated temp warning
```

### TRY / EXCEPT / FINALLY (Robot 5+ )

```robot
*** Test Cases ***

Error Handling With TRY EXCEPT

    TRY
        ${response}=    Send CAN Frame    0x123    8    01 02 03 04 05 06 07 08
        Should Be Equal    ${response}[status]    OK
    EXCEPT    CAN bus not connected
        Log    Bus not connected — using simulated response    level=WARN
        ${response}=    Get Simulated CAN Response    0x123
    EXCEPT    Timeout    type=start
        Log    Timeout waiting for CAN response    level=ERROR
        Fail    CAN communication timeout exceeded
    FINALLY
        Log    Always runs — cleanup CAN socket
        Close CAN Socket
    END

    TRY
        Connect To Database    ${DB_HOST}    ${DB_PORT}
    EXCEPT    *Connection refused*    type=glob
        Skip    Database not available — skipping DB-dependent test
    END
```

### WHILE Loops (Robot 5+)

```robot
*** Test Cases ***

WHILE Loop Examples

    # Wait until ECU is ready (poll with timeout)
    ${ecu_ready}=    Set Variable    ${False}
    WHILE    not ${ecu_ready}    limit=20    on_limit=FAIL
        ${status}=    Check ECU Boot Status
        IF    '${status}' == 'READY'
            ${ecu_ready}=    Set Variable    ${True}
        ELSE
            Sleep    500ms
        END
    END
    Log    ECU is ready — proceeding with tests

    # Count-limited WHILE
    ${retry}=    Set Variable    ${0}
    WHILE    ${retry} < 5
        ${result}=    Run Keyword And Return Status    Ping ECU
        IF    ${result}
            BREAK
        END
        ${retry}=    Evaluate    ${retry} + 1
        Sleep    1s
    END
```

---

## 9. Built-In Libraries

The `BuiltIn` library is always available — no import required.

### Most Used BuiltIn Keywords

```robot
*** Test Cases ***

BuiltIn Keywords Reference

    # ─── LOGGING ───────────────────────────────────────────────────────────
    Log           Hello World                         # INFO level
    Log           Debug message    level=DEBUG
    Log           Warning!         level=WARN
    Log           Error occurred   level=ERROR
    Log To Console    This prints to terminal (not just log)

    # ─── VARIABLES ─────────────────────────────────────────────────────────
    ${x}=    Set Variable    42
    ${y}=    Set Variable If    ${x} > 10    big    small
    @{list}=    Create List    a    b    c
    &{dict}=    Create Dictionary    key=value    name=robot

    # ─── ASSERTIONS ────────────────────────────────────────────────────────
    Should Be Equal               ${x}    ${42}
    Should Be Equal As Integers   ${x}    42
    Should Be Equal As Strings    ${x}    42
    Should Not Be Equal           ${x}    ${100}
    Should Be True                ${x} > 10
    Should Be True                '${name}' == 'Robot'
    Should Contain                Hello World    World
    Should Not Contain            Hello World    Python
    Should Start With             Hello World    Hello
    Should End With               Hello World    World
    Should Match                  Hello World    Hello*       # glob
    Should Match Regexp           ABC123         ^[A-Z]{3}\\d{3}$
    Should Be Empty               ${[]}
    Should Not Be Empty           ${[1, 2, 3]}
    Length Should Be              ${[1, 2, 3]}    3

    # ─── FAIL / PASS ───────────────────────────────────────────────────────
    Fail    This test is intentionally failed    # always fails
    Pass Execution    Skipping rest of test — condition met

    # ─── FLOW CONTROL ──────────────────────────────────────────────────────
    ${status}    ${value}=    Run Keyword And Ignore Error    Risky Keyword
    ${status}=    Run Keyword And Return Status    Risky Keyword
    Run Keyword If    ${x} > 5    Log    x is big
    Run Keywords    Log    First    AND    Log    Second

    # ─── SLEEP ─────────────────────────────────────────────────────────────
    Sleep    2s           # 2 seconds
    Sleep    500ms        # 500 milliseconds
    Sleep    1 minute     # 1 minute

    # ─── TYPE CONVERSION ───────────────────────────────────────────────────
    ${int}=    Convert To Integer    42
    ${float}=    Convert To Number    3.14
    ${str}=    Convert To String     ${42}
    ${bool}=    Convert To Boolean   true
    ${hex}=    Evaluate    hex(255)                # '0xff'
    ${dec}=    Evaluate    int('0xFF', 16)          # 255

    # ─── KEYWORD INTROSPECTION ─────────────────────────────────────────────
    Keyword Should Exist    Log
    Variable Should Exist   ${x}
```

---

## 10. Standard Libraries

Libraries that come with Robot Framework but need explicit import.

### Collections Library

```robot
*** Settings ***
Library    Collections

*** Test Cases ***

Collections Examples

    # List operations
    @{list}=    Create List    1    2    3    4    5
    Append To List       ${list}    6
    Insert Into List     ${list}    0    0         # insert at index 0
    Remove From List     ${list}    0              # remove index 0
    Remove Values From List    ${list}    3        # remove all occurrences of 3
    Reverse List         ${list}
    Sort List            ${list}
    ${idx}=    Get Index From List    ${list}    4

    List Should Contain Value    ${list}    4
    Lists Should Be Equal        ${list}    ${[0, 1, 2, 4, 5, 6]}

    # Dictionary operations
    &{car}=    Create Dictionary    make=BMW    model=M3
    Set To Dictionary           ${car}    color    blue
    Remove From Dictionary      ${car}    model
    ${has_key}=    Run Keyword And Return Status
    ...    Dictionary Should Contain Key    ${car}    make

    &{merged}=    Create Dictionary    &{car}    year=2024
    ${keys}=    Get Dictionary Keys      ${car}
    ${values}=    Get Dictionary Values  ${car}
    ${items}=    Get Dictionary Items    ${car}
```

### String Library

```robot
*** Settings ***
Library    String

*** Test Cases ***

String Library Examples

    # Case conversion
    ${upper}=    Convert To Upper Case    hello world       # HELLO WORLD
    ${lower}=    Convert To Lower Case    HELLO WORLD       # hello world
    ${title}=    Convert To Title Case    hello world       # Hello World

    # Splitting and joining
    @{parts}=    Split String    CAN:500000:vcan0    :            # [CAN, 500000, vcan0]
    ${joined}=    Catenate    SEPARATOR=,    a    b    c           # a,b,c
    ${joined}=    Catenate    a    b    c                          # a b c

    # Searching and replacing
    ${replaced}=    Replace String    Hello World    World    Robot      # Hello Robot
    ${stripped}=    Strip String    "  hello  "                          # hello
    ${stripped}=    Strip String    ###hello###    characters=#          # hello
    ${count}=    Get Line Count    line1\nline2\nline3                   # 3

    # String formatting
    ${formatted}=    Format String    ECU: {:s}, DID: 0x{:04X}    BCM    61585
    Log    ${formatted}     # ECU: BCM, DID: 0xF0B1

    # Regular expressions
    ${match}=    Get Regexp Matches    VIN: WBA12345678    [A-Z0-9]{17}
    Should Not Be Empty    ${match}
    ${groups}=    Get Regexp Matches    ECU_BCM_v2.3    (.+)_v(\\d+\\.\\d+)    1    2
```

### OperatingSystem Library

```robot
*** Settings ***
Library    OperatingSystem

*** Test Cases ***

OS Library Examples

    # File operations
    Create File         /tmp/robot_test.txt    Hello Robot!
    Append To File      /tmp/robot_test.txt    \nSecond line
    File Should Exist   /tmp/robot_test.txt
    ${content}=    Get File    /tmp/robot_test.txt
    Remove File         /tmp/robot_test.txt

    # Directory operations
    Create Directory    /tmp/robot_results
    Directory Should Exist    /tmp/robot_results
    Empty Directory     /tmp/robot_results
    Remove Directory    /tmp/robot_results    recursive=True

    # Running shell commands
    ${rc}    ${output}=    Run And Return Rc And Output    ls -la /tmp
    Should Be Equal As Integers    ${rc}    0
    Log    Directory listing: ${output}

    # Environment variables
    ${home}=    Get Environment Variable    HOME
    Set Environment Variable    MY_TEST_VAR    hello_robot
    ${val}=     Get Environment Variable    MY_TEST_VAR
```

### Process Library

```robot
*** Settings ***
Library    Process

*** Test Cases ***

Process Library Examples

    # Run a process and wait for it
    ${result}=    Run Process    python    -c    print("hello")
    Should Be Equal As Integers    ${result.rc}    0
    Should Be Equal    ${result.stdout.strip()}    hello

    # Start background process
    ${handle}=    Start Process    python    my_server.py    alias=server
    Sleep    2s    # wait for server to start
    ${result}=    Run Process    curl    http://localhost:8080/health
    Terminate Process    server

    # Run with timeout
    ${result}=    Run Process    sleep    100
    ...    timeout=5s    on_timeout=terminate
    Should Be True    ${result.rc} != 0    # terminated
```

---

## 11. External Libraries — Selenium, Requests, SSH

### SeleniumLibrary — Web UI Testing

```robot
*** Settings ***
Library    SeleniumLibrary

*** Variables ***
${BROWSER}    chrome
${BASE_URL}   https://infotainment.example.com

*** Test Cases ***

Login To Infotainment Portal
    Open Browser    ${BASE_URL}    ${BROWSER}
    Maximize Browser Window
    Set Selenium Implicit Wait    10s

    # Navigate and interact
    Wait Until Element Is Visible    id=username    timeout=15s
    Input Text    id=username    testuser
    Input Password    id=password    Password123
    Click Button    id=login-btn

    # Verify result
    Wait Until Page Contains    Dashboard    timeout=10s
    Page Should Contain Element    id=vehicle-status-panel

    # Take screenshot on assertion
    Capture Page Screenshot    login_success.png

    [Teardown]    Close Browser

Verify Navigation Menu
    Open Browser    ${BASE_URL}/dashboard    ${BROWSER}

    # Click elements
    Click Link    Settings
    Wait Until Page Contains    System Settings
    Click Element    xpath=//button[@data-id='wifi-settings']

    # Form interaction
    Select From List By Label    id=region    Europe
    Select Checkbox              id=auto-update
    Input Text                   id=server-url    https://ota.example.com
    Click Button                 xpath=//button[text()='Save']

    # Verify
    Wait Until Element Contains    id=status-msg    Saved successfully
    Element Text Should Be         id=wifi-status    Connected

    [Teardown]    Close Browser
```

### RequestsLibrary — REST API Testing

```robot
*** Settings ***
Library    RequestsLibrary
Library    Collections

*** Variables ***
${OTA_SERVER}    https://ota.vehicle.example.com
${API_KEY}       Bearer eyJhbGciOiJSUzI1NiJ9...

*** Test Cases ***

Check OTA Server Health
    Create Session    ota_api    ${OTA_SERVER}    verify=True
    ${response}=    GET On Session    ota_api    /api/v1/health
    Status Should Be    200    ${response}
    ${body}=    Set Variable    ${response.json()}
    Should Be Equal    ${body}[status]    healthy

Upload Firmware Package
    ${headers}=    Create Dictionary
    ...    Authorization=${API_KEY}
    ...    Content-Type=application/octet-stream
    Create Session    ota_api    ${OTA_SERVER}    headers=${headers}

    ${file_data}=    Get Binary File    firmware_v2.3.bin
    ${response}=    POST On Session    ota_api    /api/v1/packages
    ...    data=${file_data}
    Status Should Be    201    ${response}
    ${pkg_id}=    Set Variable    ${response.json()}[package_id]
    Log    Uploaded firmware package ID: ${pkg_id}
    RETURN    ${pkg_id}

Trigger OTA Campaign
    [Arguments]    ${package_id}    ${vin}
    ${payload}=    Create Dictionary
    ...    package_id=${package_id}
    ...    vin=${vin}
    ...    trigger_time=immediate
    ${response}=    POST On Session    ota_api    /api/v1/campaigns
    ...    json=${payload}
    Status Should Be    202    ${response}
```

### SSHLibrary — Remote Device Testing

```robot
*** Settings ***
Library    SSHLibrary

*** Variables ***
${ECU_HOST}     192.168.1.100
${ECU_USER}     root
${ECU_PASS}     password123

*** Test Cases ***

Read ECU Log Files
    Open Connection    ${ECU_HOST}    port=22    timeout=30s
    Login    ${ECU_USER}    ${ECU_PASS}

    ${stdout}    ${stderr}    ${rc}=    Execute Command
    ...    cat /var/log/ecu/diagnostic.log | tail -50    return_rc=True    return_stderr=True
    Should Be Equal As Integers    ${rc}    0
    Should Not Contain    ${stdout}    FATAL ERROR

    # Upload and download files
    Put File    local_config.json    /etc/ecu/config.json
    Get File    /var/log/ecu/errors.log    results/ecu_errors.log

    Close Connection

Restart ECU Process
    Open Connection    ${ECU_HOST}
    Login    ${ECU_USER}    ${ECU_PASS}

    Execute Command    systemctl restart ecu-main-service
    Sleep    3s

    ${stdout}=    Execute Command    systemctl is-active ecu-main-service
    Should Be Equal    ${stdout.strip()}    active
    Log    ECU main service restarted and is active

    Close Connection
```

---

## 12. Resource Files & Modular Architecture

Resource files (`.resource` extension) contain reusable keywords and variables but NO test cases.

### Resource File Example

```robot
# File: resources/uds_keywords.resource

*** Settings ***
Documentation    UDS diagnostic protocol keywords for ECU testing
Library          python-can
Library          ../../libraries/UDSLibrary.py
Variables        ../../variables/uds_config.yaml

*** Variables ***
${UDS_REQUEST_ID}     0x744
${UDS_RESPONSE_ID}    0x7EC
${P2_TIMEOUT_MS}      50
${P2_STAR_MS}         5000

*** Keywords ***

# ─── SESSION MANAGEMENT ────────────────────────────────────────────────────

Open Default Diagnostic Session
    [Documentation]    Opens default diagnostic session (SID 0x10 sub 0x01)
    ${req}=    Create List    0x02    0x10    0x01
    Send UDS Frame    ${req}
    ${resp}=    Wait For UDS Response    timeout=${P2_TIMEOUT_MS}
    Should Be Equal    ${resp}[0]    0x50     # positive response
    Should Be Equal    ${resp}[1]    0x01
    Log    Default session opened successfully

Open Extended Diagnostic Session
    [Documentation]    Opens extended diagnostic session (SID 0x10 sub 0x03)
    ${req}=    Create List    0x02    0x10    0x03
    Send UDS Frame    ${req}
    ${resp}=    Wait For UDS Response    timeout=${P2_TIMEOUT_MS}
    Should Be Equal    ${resp}[0]    0x50
    Should Be Equal    ${resp}[1]    0x03
    Log    Extended session opened

Close Diagnostic Session
    [Documentation]    Returns to default session
    ${req}=    Create List    0x02    0x10    0x01
    Send UDS Frame    ${req}
    ${resp}=    Wait For UDS Response    timeout=${P2_TIMEOUT_MS}
    Log    Session closed (returned to default)

# ─── DATA READING ──────────────────────────────────────────────────────────

Read DID
    [Arguments]    ${did_hex}
    [Documentation]    Reads a Data Identifier (DID) using SID 0x22
    ...    Returns the response data bytes as a list
    ${did_msb}=    Evaluate    (int('${did_hex}', 16) >> 8) & 0xFF
    ${did_lsb}=    Evaluate    int('${did_hex}', 16) & 0xFF
    ${req}=    Create List    0x03    0x22    ${did_msb}    ${did_lsb}
    Send UDS Frame    ${req}
    ${resp}=    Wait For UDS Response    timeout=${P2_TIMEOUT_MS}
    Should Be Equal    ${resp}[0]    0x62     # positive response to 0x22
    ${data}=    Get Slice From List    ${resp}    3
    RETURN    ${data}

Verify DID Response Is NRC
    [Arguments]    ${did_hex}    ${expected_nrc}
    [Documentation]    Asserts that reading a DID returns the expected NRC
    ${did_msb}=    Evaluate    (int('${did_hex}', 16) >> 8) & 0xFF
    ${did_lsb}=    Evaluate    int('${did_hex}', 16) & 0xFF
    ${req}=    Create List    0x03    0x22    ${did_msb}    ${did_lsb}
    Send UDS Frame    ${req}
    ${resp}=    Wait For UDS Response    timeout=${P2_TIMEOUT_MS}
    Should Be Equal    ${resp}[0]    0x7F     # negative response SID
    Should Be Equal    ${resp}[1]    0x22     # service ID echoed
    Should Be Equal    ${resp}[2]    ${expected_nrc}
    Log    ✓ Got expected NRC: 0x${expected_nrc} for DID 0x${did_hex}
```

### Using Resource Files

```robot
# File: tests/diagnostics/did_tests.robot

*** Settings ***
Resource    ../../resources/uds_keywords.resource
Resource    ../../resources/can_keywords.resource

Suite Setup    Open CAN Bus And Enter Extended Session
Suite Teardown    Close Diagnostic Session And CAN Bus

*** Keywords ***
Open CAN Bus And Enter Extended Session
    Connect To CAN Bus    ${CAN_INTERFACE}    ${CAN_BITRATE}
    Open Extended Diagnostic Session

Close Diagnostic Session And CAN Bus
    Close Diagnostic Session
    Disconnect From CAN Bus

*** Test Cases ***
Read VIN From ECU
    ${data}=    Read DID    F190
    ${vin_str}=    Convert Bytes To String    ${data}
    Should Match Regexp    ${vin_str}    ^[A-HJ-NPR-Z0-9]{17}$
    Log    VIN: ${vin_str}
```

---

## 13. Tags, Filtering & Execution

### Applying Tags

```robot
*** Settings ***
Default Tags    regression    nightly    ecu-bcm    # applied to all tests

*** Test Cases ***

Smoke Test — ECU Alive
    [Tags]    smoke    critical    P1
    ...

Extended Session Test
    [Tags]    uds    session    regression
    ...

SKIPPED Test
    [Tags]    skip    future-sprint
    Skip    Not implemented yet
```

### Running With Filters

```bash
# Run ALL tests in folder
robot tests/

# Run only SMOKE tagged tests
robot --include smoke tests/

# Run regression but EXCLUDE slow tests
robot --include regression --exclude slow tests/

# Run tests matching AND logic (both tags required)
robot --include smoke AND critical tests/

# Run by tag OR logic
robot --include smokeORregression tests/

# Run specific test case by name
robot --test "TC_001 - Verify ECU Responds To Tester Present" tests/

# Run specific suite file
robot tests/diagnostics/uds_tests.robot

# Run with variable override
robot --variable ENV:production --variable TIMEOUT:60s tests/

# Dry run (parse only, don't execute)
robot --dryrun tests/

# Output to specific directory
robot --outputdir results/ tests/

# Parallel execution with pabot
pip install robotframework-pabot
pabot --processes 4 tests/
```

### Command Line Options Reference

```
  --include (-i)     Include tests with tag
  --exclude (-e)     Exclude tests with tag
  --test (-t)        Run specific test case name
  --suite (-s)       Run specific suite name
  --variable (-v)    Override variable: -v KEY:VALUE
  --variablefile     Load variable file: --variablefile vars.yaml
  --outputdir (-d)   Output directory for results
  --output (-o)      Output XML file name
  --report (-r)      Report HTML file name
  --log (-l)         Log HTML file name
  --loglevel (-L)    Log level: DEBUG, INFO, WARN, ERROR
  --dryrun           Parse and validate without executing
  --listener         Attach listener class for custom reporting
  --randomize        Randomize test order: ALL, SUITES, TESTS
  --exitonfailure    Stop on first failure
  --skiponfailure    Mark tests as skipped instead of failed
  --rerunfailed      Rerun only previously failed tests
```

---

## 14. Setup, Teardown & Fixtures

### Test and Suite Lifecycle

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                    EXECUTION LIFECYCLE                                 │
  ├────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  ┌──────────────────────────────────────────────┐                     │
  │  │                SUITE SETUP                   │ runs once per suite │
  │  │  Connect to hardware, open DB, init state    │                     │
  │  └──────────────────────────────────────────────┘                     │
  │                          │                                             │
  │         ┌────────────────┴───────────────────┐                        │
  │         │          TEST 1                    │                        │
  │         │  ┌─────────────────────────────┐  │                        │
  │         │  │      TEST SETUP             │  │ runs before each test  │
  │         │  │  Reset ECU, clear logs      │  │                        │
  │         │  └─────────────────────────────┘  │                        │
  │         │  ┌─────────────────────────────┐  │                        │
  │         │  │   TEST BODY KEYWORDS        │  │ the actual test steps  │
  │         │  └─────────────────────────────┘  │                        │
  │         │  ┌─────────────────────────────┐  │                        │
  │         │  │     TEST TEARDOWN           │  │ ALWAYS runs (even fail)│
  │         │  │  Log result, collect data   │  │                        │
  │         │  └─────────────────────────────┘  │                        │
  │         └────────────────────────────────────┘                        │
  │                          │                                             │
  │         ┌────────────────┴──────────────────┐                         │
  │         │          TEST 2 ...               │                         │
  │         └───────────────────────────────────┘                         │
  │                          │                                             │
  │  ┌──────────────────────────────────────────────┐                     │
  │  │                SUITE TEARDOWN                │ runs once per suite │
  │  │  Disconnect, save reports, release resources │                     │
  │  └──────────────────────────────────────────────┘                     │
  └────────────────────────────────────────────────────────────────────────┘
```

```robot
*** Settings ***
Suite Setup       Open Hardware Connection And Verify
Suite Teardown    Disconnect And Archive Logs
Test Setup        Clear ECU DTCs And Reset State
Test Teardown     Collect Logs And Screenshot On Failure

*** Keywords ***

Open Hardware Connection And Verify
    Log    Initializing CAN bus...    level=INFO
    Connect To CAN Bus    vcan0    500000
    ${status}=    Check Bus Status
    Should Be True    ${status}    msg=CAN bus not available

Disconnect And Archive Logs
    Disconnect From CAN Bus
    Copy File    results/output.xml    archive/${SUITE NAME}_${TIMESTAMP}.xml
    Log    Suite complete. Logs archived.

Clear ECU DTCs And Reset State
    Open Default Diagnostic Session
    Clear All DTCs

Collect Logs And Screenshot On Failure
    Run Keyword If Test Failed    Capture ECU State Snapshot
    Run Keyword If Test Failed    Log    TEST FAILED: ${TEST NAME}    level=ERROR
    Run Keyword If Test Passed    Log    TEST PASSED: ${TEST NAME}    level=INFO
    Close Diagnostic Session
```

---

## 15. Data-Driven Testing

### Template Keyword Approach

```robot
*** Settings ***
Library    DataDriver    file=test_data/did_test_data.csv    encoding=utf-8

*** Test Cases ***
Read DID And Verify Response
    [Template]    Verify DID Response Matches Expected
    [Tags]    data-driven    did
    # data comes from CSV — rows here are overridden

*** Keywords ***
Verify DID Response Matches Expected
    [Arguments]    ${did}    ${expected_data}    ${expected_length}
    ${response}=    Read DID    ${did}
    Length Should Be    ${response}    ${expected_length}
    Should Be Equal    ${response}    ${expected_data}
    Log    ✓ DID 0x${did}: data matches expected value
```

### CSV Data File

```csv
# test_data/did_test_data.csv
did,expected_data,expected_length
F190,WBA12345678901234,17
F189,02030001,8
F18C,BCM_20240101,10
0110,01,1
0111,00,1
```

### Inline Data-Driven with Template

```robot
*** Test Cases ***
Test ECU Speed Limits
    [Template]    Check Speed Limit Response
    # speed_kmh    expected_dtc    expected_warning
    0              ${NONE}         ${False}
    50             ${NONE}         ${False}
    120            ${NONE}         ${False}
    130            P1234           ${True}
    160            P1234           ${True}
    200            P5678           ${True}

*** Keywords ***
Check Speed Limit Response
    [Arguments]    ${speed_kmh}    ${expected_dtc}    ${expected_warning}
    Set Simulated Vehicle Speed    ${speed_kmh}
    Sleep    200ms
    ${dtc}=    Get Active DTC
    ${warning_active}=    Get Overspeed Warning State
    Should Be Equal    ${dtc}           ${expected_dtc}
    Should Be Equal    ${warning_active}    ${expected_warning}
```

---

## 16. Custom Python Libraries

### Simple Python Library

```python
# File: libraries/CANLibrary.py

"""
CustomCANLibrary — Robot Framework keyword library for CAN bus interaction.
Usage in Robot: Library    libraries/CANLibrary.py
"""

import can
import time
from robot.api import logger
from robot.api.deco import keyword, library


@library(scope='GLOBAL', version='1.0.0')
class CANLibrary:
    """
    Robot Framework library for CAN bus communication.
    Uses python-can under the hood.
    """

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self._bus = None
        self._interface = None
        self._bitrate = None

    @keyword('Connect To CAN Bus')
    def connect_to_can_bus(self, interface: str, bitrate: int = 500000):
        """
        Connects to a CAN bus interface.

        Arguments:
        - ``interface``: Interface name, e.g., ``vcan0``, ``can0``, ``PCAN_USBBUS1``
        - ``bitrate``:   Bit rate in bps. Default: 500000 (500 kbps)

        Example:
        | Connect To CAN Bus | vcan0 | 500000 |
        | Connect To CAN Bus | PCAN_USBBUS1 | bitrate=1000000 |
        """
        self._interface = interface
        self._bitrate = int(bitrate)
        try:
            self._bus = can.interface.Bus(
                channel=interface,
                bustype='socketcan',
                bitrate=self._bitrate
            )
            logger.info(f"Connected to CAN bus: {interface} at {bitrate} bps")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to CAN bus '{interface}': {e}")

    @keyword('Disconnect From CAN Bus')
    def disconnect_from_can_bus(self):
        """Disconnects from the CAN bus and releases the interface."""
        if self._bus:
            self._bus.shutdown()
            self._bus = None
            logger.info("Disconnected from CAN bus")

    @keyword('Send CAN Frame')
    def send_can_frame(self, can_id: str, data: str) -> None:
        """
        Sends a CAN frame.

        Arguments:
        - ``can_id``: CAN arbitration ID as hex string, e.g., ``0x123`` or ``123``
        - ``data``:   Data bytes as space-separated hex, e.g., ``01 02 03 04``

        Example:
        | Send CAN Frame | 0x123 | 01 02 03 04 05 06 07 08 |
        """
        if not self._bus:
            raise RuntimeError("Not connected to CAN bus. Call 'Connect To CAN Bus' first.")
        arb_id = int(can_id, 16) if isinstance(can_id, str) else int(can_id)
        data_bytes = bytes([int(b, 16) for b in data.strip().split()])
        msg = can.Message(arbitration_id=arb_id, data=data_bytes, is_extended_id=False)
        self._bus.send(msg)
        logger.info(f"Sent CAN frame: ID=0x{arb_id:03X} DATA={data}")

    @keyword('Receive CAN Frame')
    def receive_can_frame(self, timeout_ms: int = 1000) -> dict:
        """
        Waits for and returns the next CAN frame.

        Arguments:
        - ``timeout_ms``: Timeout in milliseconds. Default: 1000

        Returns a dictionary with keys: ``id``, ``data``, ``dlc``, ``timestamp``

        Example:
        | ${frame}= | Receive CAN Frame | timeout_ms=500 |
        | Log | ${frame}[id] |
        """
        if not self._bus:
            raise RuntimeError("Not connected to CAN bus.")
        timeout_sec = int(timeout_ms) / 1000.0
        msg = self._bus.recv(timeout=timeout_sec)
        if msg is None:
            raise AssertionError(f"No CAN frame received within {timeout_ms}ms")
        return {
            'id': f"0x{msg.arbitration_id:03X}",
            'data': ' '.join(f"{b:02X}" for b in msg.data),
            'dlc': msg.dlc,
            'timestamp': msg.timestamp
        }

    @keyword('CAN Bus Should Be Active')
    def can_bus_should_be_active(self, expected_frame_rate_hz: int = 10) -> None:
        """
        Asserts that the CAN bus has traffic above the expected rate.
        Listens for 1 second and checks if at least ``expected_frame_rate_hz``
        frames were received.
        """
        frames_received = 0
        deadline = time.time() + 1.0
        while time.time() < deadline:
            msg = self._bus.recv(timeout=0.1)
            if msg:
                frames_received += 1
        if frames_received < expected_frame_rate_hz:
            raise AssertionError(
                f"CAN bus seems inactive: received {frames_received} frames/s, "
                f"expected at least {expected_frame_rate_hz}"
            )
        logger.info(f"CAN bus active: {frames_received} frames in 1 second")
```

### Using the Custom Library

```robot
*** Settings ***
Library    libraries/CANLibrary.py

*** Test Cases ***

Verify CAN Bus Traffic
    Connect To CAN Bus    vcan0    500000
    CAN Bus Should Be Active    expected_frame_rate_hz=5
    ${frame}=    Receive CAN Frame    timeout_ms=2000
    Log    Received: ID=${frame}[id]  DATA=${frame}[data]
    Disconnect From CAN Bus
```

---

## 17. Robot Framework in Automotive Testing

### Complete Automotive Test Suite Architecture

```
  automotive_robot_tests/
  ├── tests/
  │   ├── 01_smoke/
  │   │   └── ecu_alive_check.robot
  │   ├── 02_diagnostics/
  │   │   ├── uds_session_tests.robot
  │   │   ├── did_read_tests.robot
  │   │   ├── dtc_tests.robot
  │   │   └── security_access_tests.robot
  │   ├── 03_functional/
  │   │   ├── adas_fcw_tests.robot
  │   │   ├── speed_limiter_tests.robot
  │   │   └── lighting_tests.robot
  │   └── 04_ota/
  │       ├── package_upload_tests.robot
  │       └── campaign_trigger_tests.robot
  │
  ├── resources/
  │   ├── uds_keywords.resource
  │   ├── can_keywords.resource
  │   ├── ota_api_keywords.resource
  │   └── common_assertions.resource
  │
  └── libraries/
      ├── CANLibrary.py
      ├── UDSLibrary.py
      └── VehicleStateLibrary.py
```

### DTC (Diagnostic Trouble Code) Test Suite

```robot
# File: tests/02_diagnostics/dtc_tests.robot

*** Settings ***
Documentation      DTC (Diagnostic Trouble Code) Test Suite
...                Validates ISO 14229-1 DTC storage, reading, and clearing
Resource           ../../resources/uds_keywords.resource
Suite Setup        Open Extended Diagnostic Session
Suite Teardown     Close Diagnostic Session

*** Variables ***
${DTC_P0100}    P0100    # MAF Sensor Circuit Malfunction
${DTC_P0200}    P0200    # Injector Circuit Malfunction

*** Test Cases ***

TC_DTC_001 - No DTCs On Clean ECU
    [Documentation]    After ECU reset, DTC list should be empty
    [Tags]    dtc    smoke    critical
    Clear All DTCs
    Sleep    500ms
    ${dtc_list}=    Read All DTCs
    Should Be Empty    ${dtc_list}
    ...    msg=Unexpected DTCs found after clear: ${dtc_list}

TC_DTC_002 - DTC Stored After Fault Injection
    [Documentation]    Injecting a fault should store the corresponding DTC
    [Tags]    dtc    regression    fault-injection
    Clear All DTCs
    Inject Fault    MAF_SENSOR_OPEN_CIRCUIT
    Sleep    2s    # allow fault detection cycle
    ${dtc_list}=    Read All DTCs
    List Should Contain Value    ${dtc_list}    ${DTC_P0100}
    Log    ✓ DTC P0100 stored after MAF fault injection

TC_DTC_003 - Clear DTC Service (SID 0x14)
    [Documentation]    SID 0x14 ClearDTC must clear all stored DTCs
    [Tags]    dtc    regression    uds-service-14
    Inject Fault    MAF_SENSOR_OPEN_CIRCUIT
    Sleep    2s
    Clear All DTCs
    Sleep    500ms
    ${dtc_count}=    Get DTC Count
    Should Be Equal As Integers    ${dtc_count}    0
    ...    msg=DTCs still present after clear: ${dtc_count}

TC_DTC_004 - DTC Status Byte Verification
    [Documentation]    Verify DTC status bits: testFailed, confirmedDTC, etc.
    [Tags]    dtc    regression    status-byte
    Clear All DTCs
    Inject Fault    MAF_SENSOR_OPEN_CIRCUIT
    Sleep    2s
    ${status}=    Read DTC Status    ${DTC_P0100}
    # Bit 0 = testFailed, Bit 3 = confirmedDTC
    Should Be True    ${status} & 0x01     msg=testFailed bit not set
    Should Be True    ${status} & 0x08     msg=confirmedDTC bit not set
    Log    DTC P0100 status byte: 0x${status:02X}
```

### UDS Security Access Test

```robot
# File: tests/02_diagnostics/security_access_tests.robot

*** Settings ***
Resource    ../../resources/uds_keywords.resource

*** Test Cases ***

TC_SEC_001 - Security Access Level 01 Unlock
    [Documentation]    Verify SID 0x27 security access unlock procedure
    [Tags]    security    uds-service-27    regression
    Open Extended Diagnostic Session

    # Step 1: Request seed
    ${seed}=    Request Security Seed    level=01
    Should Not Be Equal    ${seed}    00000000    msg=Seed must not be all zeros

    # Step 2: Calculate key
    ${key}=    Calculate Security Key    ${seed}    algorithm=XOR_SHIFT_8

    # Step 3: Send key
    ${unlock_result}=    Send Security Key    level=01    key=${key}
    Should Be Equal    ${unlock_result}    UNLOCKED

    Log    ✓ Security Level 01 unlocked with seed=${seed} key=${key}
    [Teardown]    Lock Security Level    01

TC_SEC_002 - Invalid Key Returns NRC 0x35
    [Documentation]    Wrong key must return NRC 0x35 (invalidKey)
    [Tags]    security    negative    nrc
    Open Extended Diagnostic Session
    ${seed}=    Request Security Seed    level=01
    ${wrong_key}=    Set Variable    DEADBEEF    # intentionally wrong
    ${response}=    Send Security Key    level=01    key=${wrong_key}
    Should Be Equal    ${response}    NRC_0x35
    Log    ✓ Correct NRC 0x35 for invalid key
```

---

## 18. CI/CD Integration

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any

    environment {
        ROBOT_OUTPUT_DIR = "results/${env.BUILD_NUMBER}"
    }

    stages {
        stage('Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Smoke Tests') {
            steps {
                sh """
                    robot \
                      --include smoke \
                      --outputdir ${ROBOT_OUTPUT_DIR}/smoke \
                      --output output.xml \
                      tests/01_smoke/
                """
            }
            post {
                always {
                    robot(
                        outputPath: "${ROBOT_OUTPUT_DIR}/smoke",
                        outputFileName: 'output.xml',
                        reportFileName: 'report.html',
                        logFileName: 'log.html',
                        passThreshold: 100.0,
                        unstableThreshold: 90.0
                    )
                }
            }
        }

        stage('Regression Tests') {
            when {
                branch 'main'
            }
            steps {
                sh """
                    pabot \
                      --processes 4 \
                      --include regression \
                      --outputdir ${ROBOT_OUTPUT_DIR}/regression \
                      tests/
                """
            }
        }
    }

    post {
        failure {
            emailext(
                subject: "Robot Framework Tests FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Test results: ${env.BUILD_URL}",
                to: 'test-team@company.com'
            )
        }
    }
}
```

### GitHub Actions Workflow

```yaml
# .github/workflows/robot_tests.yml
name: Robot Framework Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'    # nightly at 02:00 UTC

jobs:
  robot_tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Robot Framework and libraries
        run: |
          pip install robotframework
          pip install robotframework-requests
          pip install robotframework-seleniumlibrary
          pip install python-can cantools udsoncan

      - name: Run smoke tests
        run: |
          robot \
            --include smoke \
            --outputdir results/ \
            --output output.xml \
            --report report.html \
            --log log.html \
            tests/

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: robot-results
          path: results/

      - name: Publish Robot Results
        if: always()
        uses: joonvena/robotframework-reporter-action@v2.3
        with:
          gh_access_token: ${{ secrets.GITHUB_TOKEN }}
          report_path: results/report.html
```

### requirements.txt for Robot Projects

```txt
# requirements.txt
robotframework>=7.0
robotframework-seleniumlibrary>=6.0
robotframework-requests>=0.9
robotframework-sshlibrary>=3.8
robotframework-databaselibrary>=1.4
robotframework-datadriver>=1.10
robotframework-pabot>=2.7
python-can>=4.0
cantools>=39.0
udsoncan>=1.21
PyYAML>=6.0
openpyxl>=3.1
```

---

## 19. Reports & Logging

### Understanding Robot Reports

```
  After running tests, Robot generates 3 files:

  output.xml    ─── Machine-readable XML with ALL test data
                     Used by rebot to re-generate reports
                     Input for CI systems (Robot Jenkins plugin)

  report.html   ─── HIGH-LEVEL summary
                     Test pass/fail statistics
                     Suite-level status overview
                     Good for managers and stakeholders

  log.html      ─── DETAILED execution log
                     Every keyword call, every variable value
                     Screenshots embedded (Selenium)
                     Good for debugging failures
```

### Custom Logging in Keywords

```robot
*** Keywords ***

Read ECU VIN With Full Logging
    [Arguments]    ${expected_length}=17
    Log    Starting VIN read sequence    level=INFO

    # Log with HTML formatting (shown in log.html)
    Log    <b>VIN Read Test Started</b>    level=INFO    html=True

    ${vin_data}=    Read DID    F190
    Log    Raw response bytes: ${vin_data}    level=DEBUG

    ${vin_str}=    Convert Bytes To String    ${vin_data}
    Log    Decoded VIN string: ${vin_str}    level=INFO

    # Log with timestamp
    ${ts}=    Get Time    format=%Y-%m-%d %H:%M:%S
    Log    [${ts}] VIN verified: ${vin_str}    level=INFO

    RETURN    ${vin_str}
```

### Rebot — Merge and Re-Generate Reports

```bash
# Merge results from parallel test execution
rebot --merge results/suite1/output.xml results/suite2/output.xml

# Re-generate report with filter
rebot --include smoke results/output.xml

# Generate report from multiple runs
rebot --name "Full Regression" results/*.xml

# Output combined report
rebot --outputdir merged_results/ results/output.xml
```

---

## 20. Best Practices & Common Mistakes

### Best Practices

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                         BEST PRACTICES                                 │
  ├────────────────────────────────────────────────────────────────────────┤
  │                                                                        │
  │  1. ONE ACTION PER KEYWORD                                             │
  │     Bad:  "Login And Navigate To Dashboard And Click Settings"         │
  │     Good: "Login To Application"                                       │
  │            "Navigate To Dashboard"                                     │
  │            "Click Settings Button"                                     │
  │                                                                        │
  │  2. KEYWORDS DESCRIBE BUSINESS INTENT (not implementation)             │
  │     Bad:  "Click Element    xpath=//button[@id='btn-submit']"          │
  │     Good: "Submit Login Form"                                          │
  │            └── which calls: Click Element    xpath=//...               │
  │                                                                        │
  │  3. NEVER HARD-CODE VALUES IN TEST CASES                               │
  │     Bad:  Should Be Equal    ${vin}    WBA12345678901234               │
  │     Good: Should Be Equal    ${vin}    ${EXPECTED_VIN}                 │
  │                                                                        │
  │  4. ALL SETUP/TEARDOWN IN SETTINGS SECTION                             │
  │     Use Suite Setup/Teardown for once-per-suite init                   │
  │     Use Test Setup/Teardown for per-test preconditions                 │
  │                                                                        │
  │  5. USE RESOURCE FILES — NEVER DUPLICATE KEYWORDS                      │
  │     If a keyword appears in 2 test files → move to resource file       │
  │                                                                        │
  │  6. TAG EVERY TEST CASE                                                │
  │     [Tags]    smoke    regression    jira-1234    P1                   │
  │                                                                        │
  │  7. WRITE [Documentation] FOR EVERY KEYWORD AND TEST                   │
  │     Robot generates documentation automatically from these             │
  │                                                                        │
  │  8. ALWAYS HAVE TEARDOWN FOR HARDWARE TESTS                            │
  │     If test fails mid-way — CAN bus, SSH, browser must still close     │
  │                                                                        │
  │  9. USE PYTHON FOR COMPLEX LOGIC, ROBOT FOR FLOW                       │
  │     Calculations, bit manipulation, protocol parsing → Python library  │
  │     Test orchestration, readable flow → Robot keyword syntax           │
  │                                                                        │
  │  10. SEPARATE TEST DATA FROM TEST LOGIC                                │
  │     Use variable files, CSV, YAML for test inputs                      │
  │     Never embed test data inside .robot files                          │
  └────────────────────────────────────────────────────────────────────────┘
```

### Common Mistakes

| Mistake | Wrong | Correct |
|---------|-------|---------|
| Single space separator | `Log Hello` | `Log    Hello` (4 spaces) |
| Tab instead of spaces | `\tLog    msg` | `    Log    msg` |
| Hardcoded wait | `Sleep    5s` everywhere | `Wait Until Element Is Visible` |
| No teardown | Test leaves CAN open | `Test Teardown    Disconnect From CAN Bus` |
| Assertion in wrong layer | Python raises AssertionError | `Should Be Equal` in .robot |
| Test depends on execution order | Test 2 uses data from Test 1 | Each test is independent |
| No documentation | Keyword with no [Documentation] | Always document purpose + args |
| Giant keywords | 50-line keyword doing everything | Break into 3–5 line keywords |
| Using `Run Keyword If` everywhere | Old-style conditional | Use `IF/ELSE/END` (RF 4+) |
| `FOR` without `END` | Syntax error in older RF | Always close `FOR` with `END` |

---

## 21. STAR Scenarios — Real Interview Examples

### STAR Scenario 1 — Automating ECU Regression Suite

**Situation:** Our ECU team was running 200+ manual regression tests before every release. It took 3 days for 2 testers. Delivery was delayed because testing was the bottleneck.

**Task:** Automate the ECU diagnostic regression suite using Robot Framework and integrate into CI/CD, targeting 80% automation coverage.

**Action:**
1. Mapped all 200 test cases to Robot keywords from existing manual scripts
2. Built `UDSLibrary.py` — custom Python library wrapping `python-can` and `udsoncan`
3. Created `uds_keywords.resource` with 40 reusable keywords (sessions, DTC, DID, security)
4. Organized tests into smoke/regression/nightly suites with proper tagging
5. Integrated with Jenkins using `pabot` for parallel execution (4 threads)
6. Added automatic report archiving and email notifications on failure

**Result:** 180 of 200 tests automated (90%). Regression suite runs in 45 minutes instead of 3 days. First failure detection before code merge via pull request gate. Zero escaped defects in 3 consecutive releases.

```robot
# The infrastructure that achieved this:
*** Settings ***
Resource    resources/uds_keywords.resource
Suite Setup    Open Extended Session With Security Unlock
Suite Teardown    Close Session And Archive DTC Snapshot

*** Test Cases ***

Verify BCM DID F190 — VIN
    [Tags]    regression    smoke    P1    DID
    ${vin}=    Read DID    F190
    Should Match Regexp    ${vin}    ^[A-HJ-NPR-Z0-9]{17}$

Verify No Active DTCs At Baseline
    [Tags]    regression    P1    DTC
    ${dtcs}=    Read All DTCs    status_mask=0x09    # testFailed + confirmed
    Should Be Empty    ${dtcs}    msg=Unexpected DTCs: ${dtcs}
```

---

### STAR Scenario 2 — OTA Campaign API Automation

**Situation:** The OTA team manually validated firmware campaign APIs via Postman. Each release had 15 API test cases. Results were screenshot-based and not reproducible.

**Task:** Replace manual Postman testing with Robot Framework + RequestsLibrary to create a fully automated, reproducible API test suite.

**Action:**
1. Analysed OpenAPI spec for all OTA endpoints
2. Built `ota_api_keywords.resource` with session management and JWT auth
3. Created test data YAML files for different firmware packages and campaign configs
4. Added end-to-end test: upload → create campaign → verify vehicle receives update
5. Added negative tests: invalid JWT, wrong package format, expired campaign

**Result:** 30 API tests fully automated. Runs in 3 minutes. Integrated into GitLab CI on every merge request. Caught 2 authentication regression bugs before production.

---

### STAR Scenario 3 — Infotainment UI Regression

**Situation:** Infotainment HMI testing was 100% manual. Each Android Automotive OS upgrade broke 15–20 UI elements. Discovery took 2 weeks.

**Task:** Automate the 50 most critical infotainment UI test cases using Robot Framework + Appium (via AppiumLibrary) against the Android Automotive emulator.

**Action:**
1. Set up Appium server + Android emulator in CI Docker container
2. Installed `robotframework-appiumlibrary`
3. Applied Page Object Model pattern: one `.resource` per screen (HomeScreen, SettingsScreen, NavigationScreen)
4. Used accessibility IDs (not XPath) for stable element location
5. Ran tests with `pabot --processes 2` against 2 emulator instances

**Result:** 50 tests automated. OS upgrade regressions detected within 20 minutes of merge. Test cycle reduced from 2 weeks to 2 hours.

---

## 22. Quick Reference Cheat Sheet

```
  ┌──────────────────────────────────────────────────────────────────────────┐
  │                  ROBOT FRAMEWORK QUICK REFERENCE                         │
  ├──────────────────────────────────────────────────────────────────────────┤
  │                                                                          │
  │  SECTIONS                                                                │
  │  *** Settings ***   *** Variables ***   *** Test Cases ***   *** Keywords ***
  │                                                                          │
  │  VARIABLES                                                               │
  │  ${scalar}   @{list}   &{dict}   %{ENV_VAR}                             │
  │                                                                          │
  │  CONTROL FLOW                                                            │
  │  FOR  ${x}  IN  @{list}  ...  END                                       │
  │  FOR  ${i}  IN RANGE  0  10   ...  END                                   │
  │  IF  ${x} > 5  ...  ELSE IF  ${x} > 0  ...  ELSE  ...  END             │
  │  WHILE  ${cond}  limit=10  ...  END                                      │
  │  TRY  ...  EXCEPT  err_msg  ...  FINALLY  ...  END                      │
  │  BREAK   CONTINUE   RETURN   SKIP                                        │
  │                                                                          │
  │  COMMON ASSERTIONS                                                       │
  │  Should Be Equal               Should Contain                            │
  │  Should Be Equal As Integers   Should Not Contain                        │
  │  Should Be True                Should Match Regexp                       │
  │  Should Be Empty               Length Should Be                          │
  │                                                                          │
  │  EXECUTION                                                               │
  │  robot tests/                       # all tests                          │
  │  robot --include smoke tests/       # by tag                             │
  │  robot --variable ENV:prod tests/   # override variable                  │
  │  pabot --processes 4 tests/         # parallel                           │
  │  robot --dryrun tests/              # validate syntax                    │
  │  rebot --merge *.xml                # merge results                      │
  │                                                                          │
  │  LIBRARY IMPORTS                                                         │
  │  Library    SeleniumLibrary                                              │
  │  Library    RequestsLibrary                                              │
  │  Library    libraries/MyLib.py                                           │
  │  Resource   resources/keywords.resource                                  │
  │  Variables  variables/config.yaml                                        │
  │                                                                          │
  │  TAGS                                                                    │
  │  Default Tags   smoke    # in Settings section                           │
  │  [Tags]    smoke    regression    jira-1234    # in test case            │
  │  robot --include smoke --exclude slow tests/                             │
  │                                                                          │
  │  SETUP & TEARDOWN                                                        │
  │  Suite Setup/Teardown     ← once per suite                              │
  │  Test Setup/Teardown      ← before/after EACH test (even if failed)     │
  │  [Setup]   [Teardown]     ← override for individual test                │
  │                                                                          │
  │  KEYWORD ARGUMENTS                                                       │
  │  [Arguments]  ${required}  ${optional}=default  @{varargs}  &{kwargs}  │
  │  RETURN    ${value}                                                      │
  │                                                                          │
  │  STANDARDS USED IN AUTOMOTIVE                                            │
  │  ISO 14229 (UDS)   ISO 15765 (CAN TP)   ISO 11898 (CAN)                │
  │  ISO 26262 (FuSa)  AUTOSAR              OBD-II / J1979                  │
  └──────────────────────────────────────────────────────────────────────────┘
```

---

*Document: ROBOT_Framework_Complete_Guide.md*
*Location: python_automotive_automation_testing/docs/*
*Robot Framework Version: 7.x | Python: 3.10+*
*Standards Referenced: ISO 14229, ISO 15765-2, ISO 11898-1*
