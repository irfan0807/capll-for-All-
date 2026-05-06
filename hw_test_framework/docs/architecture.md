# Architecture

## Overview

The HW Test Framework is a five-layer stack that bridges physical hardware
protocols (CAN, UDS) to high-level Python test cases, with full observability
and CI/CD integration.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 5 — Test Cases & Suites                              │
│  TestCase subclasses (BSD, AEB, ACC…) + TestRunner          │
├─────────────────────────────────────────────────────────────┤
│  Layer 4 — Reporting & Observability                        │
│  JUnit XML, HTML report, MetricsCollector, DiagnosticsCapture│
├─────────────────────────────────────────────────────────────┤
│  Layer 3 — Python Adapter Layer                             │
│  CanAdapter, UdsAdapter (pure Python, no C++ required)      │
├─────────────────────────────────────────────────────────────┤
│  Layer 2 — pybind11 Bindings (hw_adapter_cpp)               │
│  Exposes C++ objects to Python; GIL-safe RX callbacks       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1 — C++17 Core                                       │
│  CanAdapter (pimpl), UdsAdapter (ISO-TP), SignalFilters      │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1 — C++17 Core

### Files
- `cpp/include/hw_adapter/base_adapter.hpp` — abstract base, `AdapterStatus`, `AdapterException`
- `cpp/include/hw_adapter/can_adapter.hpp`  — `CanAdapter`, `CanFrame`, `CanFilter`, `CanBitrate`
- `cpp/include/hw_adapter/uds_adapter.hpp`  — `UdsAdapter`, `IsoTpConfig`, all enums/structs
- `cpp/include/utils/signal_filter.hpp`     — `EMA`, `MovingAverage`, `MedianFilter`, `RateOfChangeGuard`
- `cpp/src/can_adapter.cpp`                 — pimpl implementation, SocketCAN backend
- `cpp/src/uds_adapter.cpp`                 — ISO-TP send/receive, UDS service encoding

### Backend selection

| Flag | Backend |
|------|---------|
| `-DUSE_SOCKETCAN` (default) | Linux SocketCAN (`AF_CAN / SOCK_RAW`) |
| `-DUSE_VECTOR_XL` | Vector XL Driver Library (`xldriver.h`) |
| *(neither)* | Stub — operations are no-ops; used for unit tests |

### CanAdapter (pimpl)

```
CanAdapter::open()
  └─ creates AF_CAN socket
  └─ binds to interface
  └─ starts rx_thread_ (rxLoop)

rxLoop()
  └─ read() from socket
  └─ apply filter
  └─ push to rx_queue_ (max 1024 frames)
  └─ call rx_callback_ (if set)
```

### UDS / ISO-TP state machine

```
sendRaw(service_id, payload)
  ├─ isoTpSend(data)
  │     ├─ len ≤ 7  → Single Frame [0x0N, ...data]
  │     └─ len > 7  → First Frame  [0x1H, 0xLL, data[0..5]]
  │                    + wait Flow Control
  │                    + Consecutive Frames [0x2N, data...]
  └─ isoTpReceive()
        ├─ Single Frame → return immediately
        └─ First Frame  → send FC, reassemble Consecutive Frames
              └─ NRC 0x78 (ResponsePending) → retry up to 10× with 5s extended timeout
```

---

## Layer 2 — pybind11 Bindings

`bindings/bindings.cpp` exposes the entire C++ API as a single Python extension
module `hw_adapter_cpp`.

**GIL safety**: RX callbacks run in a C++ thread. The binding wraps each
Python callback in `py::gil_scoped_acquire` so Python code can safely be
called from C++ threads.

**Context managers**: `CanAdapter` and `UdsAdapter` implement `__enter__`/`__exit__`
so they can be used in Python `with` statements.

---

## Layer 3 — Python Adapter Layer

Located in `python/hw_test_framework/adapters/`.

### Backend selection (CanAdapter)

```python
try:
    import hw_adapter_cpp           # C++ extension — best performance
except ImportError:
    try:
        import can                  # python-can — USB dongles
    except ImportError:
        pass                        # loopback stub — unit tests
```

The caller passes `interface="loopback"` to force the stub regardless.

### UDS Pure-Python ISO-TP

`_IsoTpTransport` in `uds_adapter.py` is a complete Python implementation
of ISO 15765-2 transport layer, used when the C++ extension is not available.
Supports: single frame, first frame, flow control (BS=0, STmin=0), consecutive
frames, and NRC 0x78 ResponsePending retries.

---

## Layer 4 — Observability

### Metrics (`observability/metrics.py`)

- `TestMetricsCollector` registers as a `TestRunner` hook via `runner.add_hook(collector.on_result)`
- Records counters by status, duration histogram, per-feature pass rates
- Export: JSON or Prometheus exposition format

### Structured Logger (`observability/logger.py`)

- `TestContextFilter` injects `test_id` and `step` into every log record
- Format: `TIMESTAMP [LEVEL] [TC-ID|step=N] logger: message`
- Propagates to both stdout and optional file handler

### Diagnostics (`observability/diagnostics.py`)

- `DiagnosticsCollector` buffers the last N CAN frames in a rolling window
- On test FAIL/ERROR → automatically captures: CAN trace, DTCs, signal snapshot, UDS reads
- Prints a structured failure summary to stdout
- Saves all captures to JSONL for post-processing

---

## Layer 5 — Test Cases

### TestCase lifecycle

```
run()
  ├─ setup()         ← prepare ECU state, open adapters
  ├─ test_body()     ← exercise feature; use step() + assert_*()
  │     └─ step(n, desc)  ← context manager; captures PASS/FAIL per step
  └─ teardown()      ← restore state (always runs, even if test failed)
```

### TestRunner execution modes

| Mode | Description |
|------|-------------|
| Sequential | Default; safe for hardware where tests share a CAN bus |
| Parallel | `parallel=True`; safe only when tests are fully independent |

### Filtering

```python
RunConfig(
    include_tags=["smoke"],         # only smoke tests
    exclude_tags=["hw-only"],       # skip hardware-specific tests
    include_ids=["TC-BSD-001"],     # run exactly this test
)
```

---

## CI/CD

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | push / PR | C++ build, Python lint, unit tests (Py 3.9–3.12), pybind11 build |
| `nightly.yml` | 02:00 UTC | Integration tests on vcan0, nightly summary, Slack alert |

---

## Extension points

| What to extend | Where |
|----------------|-------|
| New hardware protocol (LIN, FlexRay) | Subclass `BaseAdapter` in C++ + Python |
| New assertion type | Add method to `TestCase` |
| New reporter format (CSV, Allure) | Add file under `reporting/` |
| New metrics export (Grafana) | Extend `TestMetricsCollector.to_prometheus()` |
| New CI target (GitLab, Jenkins) | Add YAML under `.github/workflows/` |
