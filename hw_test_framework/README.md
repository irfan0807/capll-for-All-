# HW Test Framework

A production-quality, multi-layer hardware validation framework for ADAS/automotive ECU testing.
Combines a high-performance C++17 core with a Python adapter layer, structured test lifecycle,
observability, and CI/CD integration.

---

## Stack overview

```
┌─────────────────────────────────────────────────────┐
│  Test Cases / Test Suites  (Python)                 │
├─────────────────────────────────────────────────────┤
│  TestRunner + Reporters    (Python)                 │
├─────────────────────────────────────────────────────┤
│  Observability             (metrics / logs / diag)  │
├─────────────────────────────────────────────────────┤
│  Python Adapter Layer      (can_adapter, uds_adapter│
├─────────────────────────────────────────────────────┤
│  pybind11 Bindings         (hw_adapter_cpp)         │
├─────────────────────────────────────────────────────┤
│  C++17 Core                (SocketCAN / Vector XL)  │
└─────────────────────────────────────────────────────┘
```

---

## Quick start

### 1 — Install Python dependencies

```bash
cd hw_test_framework
pip install -r requirements.txt
```

### 2 — (Optional) Build C++ extension

Requires CMake ≥ 3.18, a C++17 compiler, and pybind11.

```bash
pip install pybind11
cmake -B build -DBUILD_PYTHON_BINDINGS=ON \
      -Dpybind11_DIR=$(python -c "import pybind11; print(pybind11.get_cmake_dir())")
cmake --build build --parallel $(nproc)
export PYTHONPATH=$PWD/build:$PYTHONPATH
```

Without the C++ extension the Python adapters fall back to `python-can` (USB dongles)
or an in-process loopback stub for unit tests.

### 3 — Run unit tests

```bash
pytest tests/unit/ -v
```

### 4 — Run integration tests (requires vcan0)

```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0
pytest tests/integration/ -v
```

### 5 — Run system tests (requires real hardware)

```bash
pytest tests/system/ -v --hw
```

---

## Writing a test case

```python
from hw_test_framework.framework.test_case import TestCase
from hw_test_framework.adapters.can_adapter import CanAdapter, CanFrame, BITRATE_500K

class BsdWarningTest(TestCase):
    test_id     = "TC-BSD-001"
    test_name   = "BSD activates within 300 ms"
    feature     = "BSD"
    requirement = "REQ-BSD-001"
    priority    = "P1"
    tags        = ["smoke", "bsd"]

    def setup(self):
        self.can = CanAdapter(interface="socketcan", channel="vcan0")
        self.can.open()

    def test_body(self):
        with self.step(1, "Inject radar target at 280 cm"):
            self.can.transmit(CanFrame(id=0x3B0, data=bytes([0x01,0x18,0x01,0x00,...]))

        with self.step(2, "Warning activates within 300 ms"):
            activated = wait_for_warning(self.can, timeout_ms=300)
            self.assert_true(activated, "Warning not raised in time")

    def teardown(self):
        self.can.close()
```

---

## Running suites

```python
from hw_test_framework.framework.test_runner import TestRunner, RunConfig
from hw_test_framework.observability import TestMetricsCollector
from hw_test_framework.reporting import write_junit, write_html

metrics = TestMetricsCollector()
runner  = TestRunner(RunConfig(parallel=True, max_workers=4))
runner.add_hook(metrics.on_result)

suite = runner.run_suite("BSD Tests", [BsdWarningTest, BsdFalsePositiveTest])
metrics.finalise()

write_junit([suite], "reports/junit.xml")
write_html([suite],  "reports/report.html")
print(metrics.to_json())
```

---

## Project structure

```
hw_test_framework/
├── cpp/
│   ├── include/hw_adapter/        # C++17 headers (base, CAN, UDS)
│   ├── include/utils/             # Header-only signal filters
│   └── src/                       # SocketCAN/stub implementations
├── bindings/
│   └── bindings.cpp               # pybind11 Python↔C++ bridge
├── python/
│   └── hw_test_framework/
│       ├── adapters/              # can_adapter.py, uds_adapter.py
│       ├── framework/             # test_case.py, test_runner.py
│       ├── observability/         # metrics.py, logger.py, diagnostics.py
│       └── reporting/             # junit_reporter.py, html_reporter.py
├── tests/
│   ├── unit/                      # pytest, no hardware required
│   ├── integration/               # requires vcan0
│   └── system/                    # requires real hardware (--hw)
├── .github/workflows/
│   ├── ci.yml                     # PR/push: build + lint + unit tests
│   └── nightly.yml                # Nightly: integration + summary
├── CMakeLists.txt
├── pyproject.toml
└── requirements.txt
```

---

## Configuration reference

| `RunConfig` field      | Default | Description |
|------------------------|---------|-------------|
| `parallel`             | False   | Run tests concurrently |
| `max_workers`          | 4       | Thread pool size |
| `stop_on_first_fail`   | False   | Abort suite on first FAIL |
| `retry_on_fail`        | False   | Retry failed tests |
| `max_retries`          | 1       | Retry limit |
| `include_tags`         | []      | Only run tests with these tags |
| `exclude_tags`         | []      | Skip tests with these tags |
| `include_ids`          | []      | Run only specific test IDs |
| `test_timeout_s`       | 120     | Per-test wall-clock limit |
| `verbose`              | True    | Print live results |

---

## Supported protocols

| Protocol | Backend | Notes |
|----------|---------|-------|
| CAN 2.0A/B | SocketCAN (Linux) | `-DUSE_SOCKETCAN` |
| CAN 2.0A/B | Vector XL Driver  | `-DUSE_VECTOR_XL` |
| CAN 2.0A/B | python-can        | USB dongles, auto-selected |
| CAN 2.0A/B | Loopback stub     | Unit tests, no hardware |
| UDS (ISO 14229) | ISO-TP over CAN | 0x10/11/14/19/22/23/27/28/2E/2F/31/34/36/37 |

---

## License

Internal use — not for redistribution.
