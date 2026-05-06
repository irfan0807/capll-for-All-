# API Reference

## adapters.can_adapter

### `CanFrame`

```python
@dataclass
class CanFrame:
    id:          int
    data:        bytes = b""
    dlc:         int   = 0          # auto-set from len(data) if 0
    is_extended: bool  = False
    is_remote:   bool  = False
    timestamp_us: float = 0.0
```

### `CanFilter`

```python
@dataclass
class CanFilter:
    mask: int = 0x00000000   # 0 = accept all
    id:   int = 0x00000000

    @staticmethod
    def accept_all() -> "CanFilter": ...
    @staticmethod
    def exact_id(id: int, extended: bool = False) -> "CanFilter": ...
```

### `CanAdapter`

```python
class CanAdapter(BaseAdapter):
    def __init__(
        self,
        interface: str = "loopback",   # "loopback" | "socketcan" | "python-can"
        channel:   str = "vcan0",
        bitrate:   int = BITRATE_500K,
    ) -> None: ...

    def open(self)  -> None: ...
    def close(self) -> None: ...

    def transmit(self, frame: CanFrame) -> None: ...
    def transmit_burst(self, frames: Sequence[CanFrame]) -> None: ...
    def receive(self, timeout_ms: int = 1000) -> Optional[CanFrame]: ...
    def on_receive(self, callback: Callable[[CanFrame], None]) -> None: ...
    def flush_rx_queue(self) -> None: ...
    def set_bitrate(self, bitrate: int) -> None: ...
    def set_filter(self, f: CanFilter) -> None: ...
    def stats(self) -> AdapterStats: ...
    def reset_stats(self) -> None: ...
```

Bitrate constants: `BITRATE_125K`, `BITRATE_250K`, `BITRATE_500K`, `BITRATE_1M`

---

## adapters.uds_adapter

### `UdsService` (IntEnum)

`DIAGNOSTIC_SESSION_CONTROL` (0x10), `ECU_RESET` (0x11), `CLEAR_DTC` (0x14),
`READ_DTC` (0x19), `READ_DID` (0x22), `READ_MEMORY` (0x23),
`SECURITY_ACCESS` (0x27), `COMM_CONTROL` (0x28), `WRITE_DID` (0x2E),
`IO_CONTROL` (0x2F), `ROUTINE_CONTROL` (0x31), `REQUEST_DOWNLOAD` (0x34),
`TRANSFER_DATA` (0x36), `REQUEST_TRANSFER_EXIT` (0x37)

### `UdsSession` (IntEnum)

`DEFAULT` (0x01), `PROGRAMMING` (0x02), `EXTENDED_DIAGNOSTIC` (0x03)

### `UdsNrc` (IntEnum)

Common values: `CONDITIONS_NOT_CORRECT` (0x22), `REQUEST_SEQUENCE_ERROR` (0x24),
`REQUEST_OUT_OF_RANGE` (0x31), `SECURITY_ACCESS_DENIED` (0x33),
`INVALID_KEY` (0x35), `RESPONSE_PENDING` (0x78)

### `UdsResponse`

```python
@dataclass
class UdsResponse:
    positive:    bool
    service_id:  int
    nrc:         UdsNrc
    payload:     bytes
    elapsed_us:  float

    def u8_at(self,  offset: int) -> int: ...
    def u16_at(self, offset: int) -> int: ...   # big-endian
    def u32_at(self, offset: int) -> int: ...   # big-endian
```

### `DtcRecord`

```python
@dataclass
class DtcRecord:
    code:         int
    status_byte:  int
    confirmed:    bool
    pending:      bool
    test_failed:  bool

    def hex(self) -> str: ...    # e.g. "D0100"
```

### `IsoTpConfig`

```python
@dataclass
class IsoTpConfig:
    tx_id:       int   = 0x7DF
    rx_id:       int   = 0x7E8
    block_size:  int   = 0          # 0 = no block size limit
    st_min_ms:   int   = 0          # separation time between CF
    timeout_ms:  int   = 1000       # request timeout
    timeout_ext_ms: int = 5000      # extended timeout after 0x78
```

### `UdsAdapter`

```python
class UdsAdapter(BaseAdapter):
    def __init__(self, can: CanAdapter, config: IsoTpConfig) -> None: ...

    def open(self)  -> None: ...
    def close(self) -> None: ...

    def session_control(self, session: UdsSession) -> UdsResponse: ...
    def ecu_reset(self, reset_type: int = 0x01) -> UdsResponse: ...
    def clear_dtcs(self, group: int = 0xFFFFFF) -> UdsResponse: ...
    def read_dtcs(self, status_mask: int = 0x08) -> List[DtcRecord]: ...
    def read_did(self, did: int) -> UdsResponse: ...
    def write_did(self, did: int, data: bytes) -> UdsResponse: ...
    def read_memory(self, address: int, length: int) -> UdsResponse: ...
    def security_access(
        self,
        level: int,
        seed_to_key_fn: Callable[[bytes], bytes],
    ) -> UdsResponse: ...
    def io_control(
        self,
        did: int,
        param: int,
        state: Optional[bytes] = None,
    ) -> UdsResponse: ...
    def routine_control(
        self,
        routine_id: int,
        sub_fn: int = 0x01,
        data: bytes = b"",
    ) -> UdsResponse: ...
    def request_download(
        self,
        memory_address: int,
        memory_size: int,
        compression: int = 0x00,
        encrypting: int = 0x00,
    ) -> UdsResponse: ...
    def transfer_data(self, block_num: int, data: bytes) -> UdsResponse: ...
    def transfer_exit(self) -> UdsResponse: ...
```

---

## framework.test_case

### `TestStatus` (Enum)

`NOT_RUN`, `PASS`, `FAIL`, `ERROR`, `SKIP`, `BLOCKED`

### `TestResult`

```python
@dataclass
class TestResult:
    test_id:       str
    test_name:     str
    status:        TestStatus
    steps:         List[StepResult]
    duration_ms:   float
    error_message: str
    tb:            str
    metadata:      Dict[str, Any]

    passed:  bool   # property
    failed:  bool   # property
    def summary(self) -> str: ...
```

### `TestCase`

```python
class TestCase:
    # Override in subclass
    test_id:     str = "TC-UNSET"
    test_name:   str = "Unnamed Test"
    feature:     str = ""
    requirement: str = ""
    author:      str = ""
    priority:    str = "P3"
    tags:        List[str] = []

    def setup(self) -> None: ...           # override: prepare hardware
    def test_body(self) -> None: ...       # REQUIRED override
    def teardown(self) -> None: ...        # override: restore state

    def run(self) -> TestResult: ...       # called by TestRunner

    # Step context manager
    def step(self, number: int, description: str) -> ContextManager: ...

    # Assertion helpers
    def assert_true(self, condition: bool, msg: str = "") -> None: ...
    def assert_false(self, condition: bool, msg: str = "") -> None: ...
    def assert_equal(self, actual, expected, msg: str = "") -> None: ...
    def assert_not_equal(self, actual, expected, msg: str = "") -> None: ...
    def assert_in_range(self, actual: float, lo: float, hi: float, msg: str = "") -> None: ...
    def assert_within(self, actual: float, expected: float, tolerance: float, msg: str = "") -> None: ...
    def assert_latency(self, actual_ms: float, max_ms: float, label: str = "") -> None: ...
    def assert_dtcs_clear(self, dtcs: list, msg: str = "") -> None: ...
    def skip(self, reason: str = "") -> None: ...
```

---

## framework.test_runner

### `RunConfig`

```python
@dataclass
class RunConfig:
    parallel:           bool = False
    max_workers:        int  = 4
    stop_on_first_fail: bool = False
    retry_on_fail:      bool = False
    max_retries:        int  = 1
    include_tags:  List[str] = []
    exclude_tags:  List[str] = []
    include_ids:   List[str] = []
    test_timeout_s: float = 120.0
    verbose:        bool = True
    log_to_file:    str  = ""
```

### `SuiteResult`

```python
@dataclass
class SuiteResult:
    suite_name: str
    results:    List[TestResult]
    start_time: float
    end_time:   float

    total:      int    # property
    passed:     int    # property
    failed:     int    # property
    errors:     int    # property
    skipped:    int    # property
    duration_ms: float # property
    all_passed: bool   # property

    def print_summary(self, stream=sys.stdout) -> None: ...
```

### `TestRunner`

```python
class TestRunner:
    def __init__(self, config: RunConfig = RunConfig()) -> None: ...

    def add_hook(self, hook: Callable[[TestResult], None]) -> None: ...

    def run_suite(
        self,
        suite_name: str,
        test_classes: Sequence[Type[TestCase]],
    ) -> SuiteResult: ...

    def run_test(self, test_class: Type[TestCase]) -> TestResult: ...
```

---

## observability

### `TestMetricsCollector`

```python
class TestMetricsCollector:
    def on_result(self, result: TestResult) -> None: ...   # use as hook
    def finalise(self) -> None: ...                        # call after run
    def to_dict(self) -> dict: ...
    def to_json(self, indent: int = 2) -> str: ...
    def to_prometheus(self) -> str: ...
```

### `DiagnosticsCollector`

```python
class DiagnosticsCollector:
    def __init__(
        self,
        can=None,
        uds=None,
        can_trace_depth: int = 50,
        auto_capture_dtcs: bool = True,
    ) -> None: ...

    def on_result(self, result: TestResult) -> None: ...   # use as hook
    def capture(...) -> DiagnosticsCapture: ...
    def all_captures(self) -> List[DiagnosticsCapture]: ...
    def save_all(self, path: str) -> None: ...
```

### `get_logger`

```python
def get_logger(
    name:     str = "hw_test_framework",
    level:    int = logging.DEBUG,
    log_file: Optional[str] = None,
) -> logging.Logger: ...
```

---

## reporting

### `write_junit`

```python
def write_junit(suite_results: List[SuiteResult], output_path: str) -> None: ...
```

Writes JUnit XML compatible with Jenkins, GitHub Actions, GitLab CI.

### `write_html`

```python
def write_html(
    suite_results: List[SuiteResult],
    output_path: str,
    title: str = "HW Test Framework — Report",
) -> None: ...
```

Writes a self-contained HTML report (no external dependencies).
