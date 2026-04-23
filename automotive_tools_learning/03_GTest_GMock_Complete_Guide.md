# Google Test (GTest) / GMock — Complete Learning Guide
## Unit Testing & Mocking Framework for C++ Automotive Embedded Software

**Classification:** Internal Training Document  
**Date:** April 2026  
**Applicable Context:** Host-based unit testing, CI/CD pipelines, AUTOSAR SWC testing, ADAS software validation

---

## 1. TOOL OVERVIEW

Google Test (GTest) is an open-source C++ unit testing framework developed by Google and widely adopted in the automotive industry, especially for host-based testing of application logic, AUTOSAR SWCs, and ADAS algorithm libraries. Google Mock (GMock) is its companion mocking library.

### Key Characteristics
| Attribute | Detail |
|---|---|
| **Language** | C++ (C++11 minimum) |
| **License** | BSD 3-Clause (free for commercial use) |
| **Integration** | CMake, Bazel, Jenkins, GitHub Actions |
| **Mocking** | GMock (included in the same repo) |
| **Reporting** | JUnit XML output, native console, custom reporters |
| **ISO 26262 Status** | Not a qualified tool — tool qualification effort required for ASIL D. Acceptable for ASIL A–C with qualification data. |

### GTest vs. Commercial Tools
| Feature | GTest/GMock | VectorCAST | LDRA |
|---|---|---|---|
| Cost | Free | Licensed | Licensed |
| On-target execution | ❌ Host only | ✅ RSP | ✅ Native |
| Auto test generation | ❌ Manual | ✅ | ✅ |
| ISO 26262 qualification | Manual effort | Pre-qualified | Pre-qualified |
| CI/CD integration | Native | Scripted | Scripted |
| C++ mocking | ✅ GMock | Limited | External |

---

## 2. ARCHITECTURE & KEY CONCEPTS

### 2.1 Test Structure Terminology
```
Test Program
  └── Test Suite (TEST_F, TEST_P)
        └── Test Case (individual TEST / TEST_F macro)
              └── Assertions (EXPECT_*, ASSERT_*)
```

### 2.2 Assertion Types
| Macro | Behaviour on Failure | When to Use |
|---|---|---|
| `ASSERT_EQ(a, b)` | Stops the test immediately | Critical checks — no point continuing if this fails |
| `EXPECT_EQ(a, b)` | Logs failure, test continues | Non-fatal checks — collect all failures |
| `ASSERT_TRUE(cond)` | Stops the test | Boolean conditions |
| `EXPECT_NEAR(a, b, abs_error)` | Logs failure | Floating-point comparisons |
| `EXPECT_THROW(fn, ExcType)` | Logs failure | Exception-expected paths |
| `EXPECT_CALL(mock, Method())` | GMock verification | Verifying mock interactions |

### 2.3 Fixture Classes (TEST_F)
Used when multiple tests share setup/teardown logic:
```cpp
class BmsControllerTest : public ::testing::Test {
protected:
    void SetUp() override {
        controller = std::make_unique<BmsController>(mock_sensor_, mock_comms_);
    }
    void TearDown() override {
        controller.reset();
    }
    MockBmsSensor mock_sensor_;
    MockBmsComms mock_comms_;
    std::unique_ptr<BmsController> controller;
};

TEST_F(BmsControllerTest, ChargeTerminationAtMaxVoltage) {
    EXPECT_CALL(mock_sensor_, GetCellVoltage()).WillRepeatedly(Return(4.2f));
    EXPECT_EQ(controller->GetChargingState(), ChargingState::TERMINATE);
}
```

### 2.4 GMock — Key Concepts
```cpp
// Define a mock class
class MockBmsSensor : public IBmsSensor {
public:
    MOCK_METHOD(float, GetCellVoltage, (), (override));
    MOCK_METHOD(float, GetTemperature, (), (override));
    MOCK_METHOD(bool,  IsFaultActive,  (), (override));
};

// Set expectations in a test
EXPECT_CALL(mock_sensor_, GetCellVoltage())
    .Times(3)
    .WillOnce(Return(3.8f))
    .WillOnce(Return(4.0f))
    .WillOnce(Return(4.2f));
```

---

## 3. STAR CASES — 20+ Real-World Scenarios

---

### STAR Case 1: Unit Testing a BMS State Machine with GMock

**Situation:** A Battery Management System state machine controlled transitions between IDLE, CHARGING, BALANCING, FAULT, and SHUTDOWN states. The state machine depended on sensor readings (voltage, temperature, current) that could not be physically reproduced reliably.

**Task:** Build a comprehensive GTest suite that tests all state transitions by injecting controlled sensor readings via GMock without real hardware.

**Action:**
- Defined an `IBmsSensor` interface and created a `MockBmsSensor` using GMock's `MOCK_METHOD`.
- Wrote test fixtures that established the controller in a known initial state using `SetUp()`.
- Wrote 34 test cases, one per state transition, using `EXPECT_CALL` to control exactly what the mock sensor returned.
- Used `EXPECT_EQ` to assert the resulting state after each transition.

**Example Test:**
```cpp
TEST_F(BmsControllerTest, TransitionToFaultOnOvertemperature) {
    EXPECT_CALL(mock_sensor_, GetTemperature())
        .WillRepeatedly(Return(65.0f));  // Overtemperature threshold: 60°C
    controller->Update();
    EXPECT_EQ(controller->GetState(), BmsState::FAULT);
}
```

**Result:**
- 34 state transition tests covering all valid and invalid transitions.
- 3 defects found: incorrect transition ordering when multiple fault conditions occurred simultaneously.
- Suite runs in 0.18 seconds. Integrated into CI. Zero state machine regression in subsequent 6 months.

---

### STAR Case 2: Testing ADAS Lane Departure Warning Algorithm

**Situation:** A lane departure warning (LDW) algorithm contained complex trigonometric and geometric computations for lane boundary estimation. Testing it in the vehicle was unsafe and expensive.

**Task:** Build a GTest suite that validates the LDW algorithm's behavior across a comprehensive input space using floating-point assertions.

**Action:**
- Mocked the camera sensor interface (MockCameraProcessor) to inject controlled lane boundary data.
- Used `EXPECT_NEAR` (not `EXPECT_EQ`) for all floating-point assertions with a tolerance of ±0.01 meters.
- Parameterized tests using `TEST_P` and `INSTANTIATE_TEST_SUITE_P` with a table of 200 road geometry scenarios (straight, curves, lane merges).
- Verified that the warning flag triggered at the correct lateral displacement threshold in all scenarios.

**Result:**
- 200 parameterized scenarios executed in 0.4 seconds.
- 8 precision defects found at tight curve geometries where floating-point accumulation exceeded tolerance.
- Algorithm reconditioned with fixed-point arithmetic in identified hotspots.

---

### STAR Case 3: Parameterized Testing with TEST_P for UDS Services

**Situation:** A UDS diagnostic handler supported 18 diagnostic service IDs. Each service had identical structural logic but different parameter sets and expected responses. Writing 18 independent test cases was repetitive and maintenance-heavy.

**Task:** Use GTest's parameterized test functionality to write a single test template exercising all 18 UDS services.

**Action:**
```cpp
struct UdsTestParam {
    uint8_t service_id;
    std::vector<uint8_t> request;
    std::vector<uint8_t> expected_response;
    bool expected_positive;
};

class UdsHandlerTest : public ::testing::TestWithParam<UdsTestParam> {};

TEST_P(UdsHandlerTest, ServiceRespondsCorrectly) {
    auto param = GetParam();
    auto response = uds_handler_.ProcessRequest(param.request);
    EXPECT_EQ(response.positive, param.expected_positive);
    EXPECT_EQ(response.data, param.expected_response);
}

INSTANTIATE_TEST_SUITE_P(AllServices, UdsHandlerTest,
    ::testing::Values(
        UdsTestParam{0x10, {0x10, 0x01}, {0x50, 0x01}, true},  // DiagnosticSessionControl
        UdsTestParam{0x11, {0x11, 0x01}, {0x51, 0x01}, true},  // ECUReset
        // ... 16 more services
    )
);
```

**Result:**
- 18 services tested with a single test body. One new service = one line added to `INSTANTIATE_TEST_SUITE_P`.
- 4 services returned incorrect NRC (Negative Response Code) — all found and fixed.
- Maintenance time per new UDS service added to the handler: reduced from 30 minutes to 2 minutes.

---

### STAR Case 4: Death Tests for Safety-Critical Abort Conditions

**Situation:** An ASIL B safety monitor function was required to call `abort()` (hard system reset) when a critical fault was detected. Standard GTest tests could not verify this because `abort()` terminates the process.

**Task:** Use GTest's `EXPECT_DEATH` macro to verify that the safety monitor correctly calls abort on critical fault injection.

**Action:**
```cpp
TEST(SafetyMonitorTest, AbortOnCriticalFaultDetected) {
    EXPECT_DEATH(
        {
            SafetyMonitor monitor;
            monitor.InjectFault(FaultType::CRITICAL_CPU_LOCKUP);
            monitor.Tick();  // Should call abort()
        },
        "CRITICAL FAULT"  // Expected stderr message before abort
    );
}
```
- Wrote 5 death tests, one for each critical fault category (CPU lockup, watchdog timeout, stack overflow, RAM parity error, power supply brownout).
- Used `EXPECT_EXIT` for non-abort shutdown paths to verify the exact exit code.

**Result:**
- All 5 critical fault paths confirmed to trigger abort correctly.
- Found 1 path (stack overflow) that logged the fault but did not actually call abort — the safety-critical reaction was missing.
- Defect fixed and verified with the death test.

---

### STAR Case 5: Testing a CAN Message Packing/Unpacking Library

**Situation:** A CAN signal packing library was used by 14 different ECU software components. Defects in the packing/unpacking logic would cause silent data corruption in all 14 components.

**Task:** Build a comprehensive GTest suite for the CAN packing library covering all signal lengths, byte orders, and signedness combinations.

**Action:**
- Defined a test matrix:
  * Signal length: 1-bit to 64-bit
  * Byte order: Intel (little-endian), Motorola (big-endian)
  * Signedness: signed, unsigned
  * Offset positions: aligned, unaligned, cross-byte, cross-word
- Used `TEST_P` with a struct defining signal parameters and expected packed/unpacked values.
- Used `EXPECT_EQ` with `std::hex` formatting in failure messages for readable binary comparison.

**Result:**
- 612 parameterized tests executed in 0.07 seconds.
- 3 defects found: incorrect bit masking for 3-bit signed signals at specific byte boundaries.
- Library certified as the single canonical CAN packing implementation for the platform.

---

### STAR Case 6: Mocking OS/RTOS API Calls (FreeRTOS Abstraction)

**Situation:** An ADAS task scheduler was tightly coupled to FreeRTOS API calls (xTaskCreate, xQueueSend, vTaskDelay). Unit testing it required a real FreeRTOS environment to be running — a huge dependency overhead.

**Task:** Introduce an abstraction interface over FreeRTOS APIs and use GMock to test the scheduler in isolation on the host.

**Action:**
- Created an `ITOS` interface wrapping all FreeRTOS calls used by the scheduler.
- Created a `MockTOS` using GMock implementing the `ITOS` interface.
- Refactored the scheduler to depend on `ITOS*` (injected via constructor).
- In tests, passed `MockTOS` and verified task creation order, priorities, and queue interactions.

```cpp
TEST_F(AdasSchedulerTest, AllTasksCreatedInCorrectOrder) {
    InSequence seq;
    EXPECT_CALL(mock_os_, CreateTask("SensorFusion", _, _)).Times(1);
    EXPECT_CALL(mock_os_, CreateTask("LaneDetection", _, _)).Times(1);
    EXPECT_CALL(mock_os_, CreateTask("CollisionAvoid", _, _)).Times(1);
    scheduler_.Init();
}
```

**Result:**
- Scheduler fully tested on host without FreeRTOS.
- 2 defects: wrong priority assigned to sensor fusion task, and no error handling if task creation failed.
- Test suite ran in 0.2 seconds. Integrated into CI immediately.

---

### STAR Case 7: GTest + lcov for Coverage Reporting in CI

**Situation:** A team was using GTest but had no coverage visibility. They didn't know if their tests were actually exercising the code paths that mattered.

**Task:** Add code coverage measurement to the GTest CI pipeline using gcov/lcov and publish HTML coverage reports.

**Action:**
```bash
# CMakeLists.txt addition
target_compile_options(bms_unit_tests PRIVATE --coverage)
target_link_libraries(bms_unit_tests PRIVATE gcov)

# CI pipeline
cmake -DCMAKE_BUILD_TYPE=Debug ..
make
./bms_unit_tests --gtest_output=xml:results.xml
lcov --capture --directory . --output-file coverage.info
genhtml coverage.info --output-directory coverage_html
```
- Configured lcov to exclude test files, third-party libs, and auto-generated code from coverage metrics.
- Published the HTML coverage report via Jenkins' HTML Publisher plugin.
- Set a CMake ctest custom command to fail the build if overall coverage fell below 80%.

**Result:**
- Coverage visibility established. First run: 43% line coverage.
- Coverage reached 82% within 3 sprints.
- Low-coverage modules immediately visible on the dashboard — focused team effort.

---

### STAR Case 8: Testing Numeric Edge Cases in Sensor Fusion Algorithm

**Situation:** A sensor fusion module combining radar and camera data for object detection had subtle precision issues when input values were near IEEE 754 float boundary conditions (NaN, Inf, subnormal).

**Task:** Build GTest tests specifically targeting IEEE 754 edge cases to verify the fusion algorithm's robustness.

**Action:**
```cpp
TEST(SensorFusionTest, HandlesNaNRadarInput) {
    float nan_range = std::numeric_limits<float>::quiet_NaN();
    fusion_.SetRadarRange(nan_range);
    auto result = fusion_.FuseObjects();
    EXPECT_FALSE(std::isnan(result.estimated_distance));
    EXPECT_EQ(result.confidence, ConfidenceLevel::LOW);
}

TEST(SensorFusionTest, HandlesInfVelocity) {
    fusion_.SetObjectVelocity(std::numeric_limits<float>::infinity());
    auto result = fusion_.FuseObjects();
    EXPECT_LE(result.estimated_velocity, MAX_VALID_VELOCITY);
}
```

**Result:**
- 5 defects found: NaN propagation through 3 computation paths, Inf input causing division-by-zero in velocity estimation, and a subnormal float causing a 30x slowdown in execution time.
- All fixed. Sensor fusion now robust against any IEEE 754 input condition.

---

### STAR Case 9: Continuous Integration with GitHub Actions for Open-Source Automotive Library

**Situation:** An automotive signal processing library was being open-sourced on GitHub. Contributors needed automated GTest validation on every pull request.

**Task:** Configure a GitHub Actions workflow to build and run GTest automatically on every PR submission.

**Action:**
```yaml
name: Unit Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: sudo apt-get install -y cmake g++ libgtest-dev
      - name: Build
        run: cmake -B build && cmake --build build
      - name: Run tests
        run: cd build && ctest --output-on-failure
```

**Result:**
- Every PR automatically tested within 2 minutes.
- 4 broken PRs caught before merge in the first month.
- Contributor confidence in the library's stability increased.

---

### STAR Case 10: AUTOSAR SWC Testing with GTest on Host

**Situation:** An AUTOSAR SWC (gear recommendation algorithm) was being developed before the AUTOSAR RTE was available. Development was blocked waiting for the full AUTOSAR environment to be configured.

**Task:** Test the SWC logic on the host using GTest by providing lightweight RTE stubs.

**Action:**
- Created a minimal host-side RTE header redefining `Rte_Read_*` and `Rte_Write_*` as simple function pointers.
- Created a GMock class implementing the RTE interface.
- Compiled the SWC source file on x86 with the mock RTE headers.
- Wrote 40 GTest cases covering all gear recommendation scenarios.

**Result:**
- SWC development and testing unblocked 8 weeks before the real AUTOSAR environment was ready.
- 6 logic defects found and fixed early, saving estimated 3 HIL rig days of debugging.

---

### STAR Case 11: Custom GTest Listener for Real-Time CI Dashboard

**Situation:** The team's Jenkins output showed only pass/fail counts. Engineers needed richer real-time output showing which specific assertions failed and what the expected vs. actual values were.

**Task:** Write a custom GTest event listener that outputs structured JSON results for ingestion by the CI dashboard.

**Action:**
```cpp
class JsonReporter : public ::testing::EmptyTestEventListener {
    void OnTestEnd(const ::testing::TestInfo& info) override {
        json output;
        output["test"] = info.name();
        output["suite"] = info.test_suite_name();
        output["passed"] = info.result()->Passed();
        output["duration_ms"] = info.result()->elapsed_time();
        std::ofstream file("results.json", std::ios::app);
        file << output.dump() << "\n";
    }
};
```

**Result:**
- Rich per-test JSON results fed to Grafana dashboard via a 20-line Python parser.
- Engineers could see exact failure details on the dashboard without opening Jenkins logs.

---

### STAR Case 12: Test-Driven Development (TDD) for a New UDS Service

**Situation:** A new UDS service (SID 0x2C — Define Data Identifier) needed to be implemented from scratch. The team adopted TDD to drive the implementation.

**Task:** Implement SID 0x2C using GTest-based TDD — write the test first, then write the minimal code to make it pass.

**Action:**
- Phase 1 (Red): Wrote 12 GTest test cases for all SID 0x2C sub-functions and error conditions. All failed (no implementation yet).
- Phase 2 (Green): Implemented the minimum SID 0x2C code to pass each test sequentially.
- Phase 3 (Refactor): Refactored for MISRA compliance and readability while keeping all tests passing.

**Result:**
- Implementation complete and fully tested simultaneously.
- Zero defects found in subsequent integration testing for this service.
- Team adopted TDD for all new UDS service implementations going forward.

---

### STAR Case 13: Memory Leak Detection in GTest with AddressSanitizer

**Situation:** An embedded C++ module running on the host test environment was suspected of memory leaks. Over time, the CI server's RAM usage during test execution was growing per run.

**Task:** Enable AddressSanitizer (ASan) with GTest to automatically detect and fail the build on memory leaks.

**Action:**
```cmake
# CMakeLists.txt
if(ENABLE_ASAN)
    target_compile_options(unit_tests PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(unit_tests PRIVATE -fsanitize=address)
endif()
```
```bash
cmake -DENABLE_ASAN=ON .. && make
./unit_tests
```
- AddressSanitizer output integrated into Jenkins failure output via a regex error parser.

**Result:**
- 3 memory leaks detected on first run — all in a factory-pattern object creation path.
- Leaks fixed. CI server RAM usage stabilized.
- ASan flag added as standard to debug builds.

---

### STAR Case 14: Verifying Thread Safety with Thread Sanitizer + GTest

**Situation:** A shared event queue used by multiple ADAS modules was suspected of having race conditions under high-frequency concurrent access.

**Task:** Use GTest with ThreadSanitizer to detect the race condition deterministically.

**Action:**
- Wrote a GTest test that spawned 10 threads simultaneously writing and reading from the event queue.
- Compiled with `-fsanitize=thread`.
- ThreadSanitizer reported a definite data race on the queue's internal head pointer.
- Fixed by adding a mutex guard and re-ran — no race conditions reported.

**Result:**
- Subtle race condition found that would only manifest in production under high CPU load.
- Fix applied before the module was integrated into the multi-core target ECU.

---

### STAR Case 15: Negative Testing — Verifying Rejection of Invalid Inputs

**Situation:** A safety function accepting pedal position (0–100%) needed to reject out-of-range values gracefully. There was no explicit test confirming this behavior.

**Task:** Write comprehensive negative GTest tests verifying all invalid input handling.

**Action:**
```cpp
class PedalSafetyTest : public ::testing::TestWithParam<float> {};

TEST_P(PedalSafetyTest, RejectsOutOfRangeInput) {
    PedalSafetyFilter filter;
    auto result = filter.Process(GetParam());
    EXPECT_EQ(result.status, InputStatus::INVALID);
    EXPECT_EQ(result.safe_value, 0.0f);  // Failsafe: zero pedal on invalid input
}

INSTANTIATE_TEST_SUITE_P(InvalidInputs, PedalSafetyTest,
    ::testing::Values(-0.01f, -100.f, 100.01f, 1000.f,
                      std::numeric_limits<float>::quiet_NaN(),
                      std::numeric_limits<float>::infinity())
);
```

**Result:**
- NaN and Infinity inputs were not being rejected — 2 defects found.
- Both fixed. Failsafe behavior verified for all 6 invalid input categories.

---

### STAR Case 16: GTest for Protocol Decoder Fuzzing

**Situation:** A DoIP (Diagnostics over IP) packet decoder needed robustness testing against malformed/unexpected packet data. Traditional test cases could not cover the full input space.

**Task:** Integrate libFuzzer with GTest to fuzz-test the DoIP decoder and find unexpected crashes.

**Action:**
```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    DoIPDecoder decoder;
    decoder.Decode(data, size);  // Must not crash for any input
    return 0;
}
```
- Ran for 30 minutes on the CI server. LibFuzzer generated over 50,000 unique inputs.
- 2 crashes reported (heap buffer overflow on packets with malformed payload length field).

**Result:**
- 2 security-relevant memory corruption defects found.
- Both fixed. Decoder now validates payload length before accessing buffer.
- Weekly fuzzing run added to the CI schedule.

---

### STAR Case 17: GTest Fixture Sharing Across Test Files

**Situation:** 6 test files all needed the same ECU initialization sequence (hardware register setup, CAN interface initialization, timer configuration). This was being copy-pasted across files.

**Task:** Refactor test code to use a shared GTest fixture reducing duplication and improving maintainability.

**Action:**
- Created a shared `EcuBaseTest` fixture in `test_fixtures/ecu_base_test.h`.
- Each test file's fixture extended `EcuBaseTest` instead of duplicating setup.
- Used `SetUpTestSuite()` (class-level) for expensive one-time initialization and `SetUp()` (per-test) for instance-specific state.

**Result:**
- Initialization code maintained in one place: 6 copies → 1 canonical fixture.
- Next time the initialization sequence changed (new board revision), only 1 file needed updating.

---

### STAR Case 18: GTest for a Model-Based Code Generation Validation

**Situation:** An ADAS function's C code was auto-generated from a Simulink model using Embedded Coder. Every time the model changed, the generated code changed. The team needed instant verification that the generated code matched the model behavior.

**Task:** Build a GTest "golden reference" test suite that compared the generated C code output against the Simulink model's expected output for every model change.

**Action:**
- Built a Python script that ran the Simulink model for N scenarios and exported expected output to CSV.
- Built a GTest suite that read the CSV as test parameters and compared them to the C-generated function output.
- Added the pair (model run → CSV export → GTest run) to the CI pipeline.

**Result:**
- Any model change that produced different C behavior was immediately caught.
- 3 Simulink model changes were found to produce incorrect C code due to Embedded Coder configuration issues before the code was integrated.

---

### STAR Case 19: Building a Test Infrastructure Package for Cross-Team Reuse

**Situation:** 5 different teams were each building their own GTest mock classes for common ECU interfaces (CAN interface, OS timer, NVM). There was inconsistency between the mocks, causing integration friction.

**Task:** Build a shared GTest mock infrastructure package as a CMake library, used by all teams.

**Action:**
- Created a `test_infrastructure` CMake library containing:
  * `MockCanInterface`, `MockNvm`, `MockTimer`, `MockLogger`
  * Common test fixtures (`EcuBaseTest`, `CanEcuTest`)
  * Custom GTest matchers for automotive types (CAN frame comparison, timestamp validation).
- Published as an internal CMake package: `find_package(AutomotiveTestInfra REQUIRED)`.

**Result:**
- 5 teams onboarded within 1 sprint.
- Mock inconsistency issues in integration testing reduced to zero.
- New mock requests submitted via the package's internal review process.

---

### STAR Case 20: GTest for Middleware API Contract Testing

**Situation:** A middleware team provided an API used by 8 upstream software components. When the middleware was updated, it was unclear whether the API contract was still fulfilled.

**Task:** Write GTest "contract tests" that verified the middleware API behavior from the consumer's perspective, run automatically on every middleware release.

**Action:**
- Defined 60 contract tests, one per API function's documented behavior specification.
- These tests were owned by the consumers (upstream teams) but run against the middleware as a verification gate.
- If the middleware updated broke a contract test, the middleware team was notified before the release was published.

**Result:**
- 2 middleware releases caught violating consumer contracts before being merged to main.
- Both regressions fixed before they could impact upstream teams.
- API contract testing adopted as the formal integration contract between teams.

---

### STAR Case 21: Measuring GTest Suite Health Over Time

**Situation:** Over 18 months, the test suite had grown to 4,200 tests but engineers reported that the suite had become "noisy" — many tests were fragile and often failing for non-defect reasons.

**Task:** Measure and improve test suite health: flakiness rate, test isolation, and execution time.

**Action:**
- Ran the full suite 50 times to identify flaky tests (passed some runs, failed others with no code change).
- Identified 27 flaky tests — all caused by time-dependent logic (`usleep`-based timing assertions) or shared global state.
- Fixed 20 by replacing time waits with event-driven synchronization.
- Marked 7 tests as `DISABLED_` pending architecture refactoring.
- Measured per-test execution time using a custom listener. Identified 3 tests taking >5 seconds each (accidentally running real network calls via non-mocked interfaces).

**Result:**
- Flakiness rate reduced from 0.64% per run to 0.02%.
- CI failure rate due to flaky tests: from 12% of builds to <1%.
- 3 slow tests reworked with proper mocking: total suite time reduced by 18%.

---

## 4. QUICK REFERENCE — GTEST CHEATSHEET

```cpp
// Basic test
TEST(SuiteName, TestName) { EXPECT_EQ(1+1, 2); }

// Fixture test
TEST_F(MyFixture, TestName) { /* uses SetUp/TearDown */ }

// Parameterized test
TEST_P(MyParamTest, Name) { auto val = GetParam(); }
INSTANTIATE_TEST_SUITE_P(Prefix, MyParamTest, ::testing::Values(1, 2, 3));

// Death test
EXPECT_DEATH(fn(), "expected message");

// Run with filter
./my_tests --gtest_filter=BmsTest.* --gtest_repeat=3
./my_tests --gtest_output=xml:results.xml  // JUnit XML for CI
```

---

## 5. INTERVIEW PREPARATION — Top Questions

1. **What is the difference between ASSERT_* and EXPECT_* in GTest?**
2. **How does GMock's EXPECT_CALL work? What happens if an unexpected call is made?**
3. **How do you test code that calls abort() or exit() in GTest?**
4. **How would you use GTest with code coverage tools (gcov/lcov)?**
5. **What is the difference between TEST, TEST_F, and TEST_P?**
6. **How do you handle flaky tests and what are their common causes?**
7. **How is GTest different from VectorCAST for automotive ISO 26262 compliance purposes?**
