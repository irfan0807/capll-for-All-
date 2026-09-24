# Power-System Software Engineer Interview Study Guide

## Target role

This guide is designed for a Software Engineer who develops Python/Java applications around embedded devices, industrial communications, databases, analytics, testing, and power-system equipment such as IEC 61850 IEDs and HVDC systems.

## How to use this guide

For every topic, separate three kinds of learning:

- **Memorize:** definitions, comparisons, commands, formulas, and interview vocabulary.
- **Understand:** why a design works, what can fail, and how the pieces interact.
- **Practice:** write code, reproduce failures, inspect logs, and explain trade-offs aloud.

A strong interview answer usually has this shape:

1. Define the concept in one sentence.
2. Explain why it matters in this role.
3. Give a small example.
4. State one trade-off or failure mode.
5. Describe how you would test or debug it.

## Role map

```text
Requirements / Jira
        |
        v
Python or Java application
        |
        v
Domain model + validation + business logic
        |
        v
Protocol adapter: IEC 61850, TCP/IP, CAN, serial, MQTT
        |
        v
Driver / embedded device / IED / HVDC control system
        |
        +--> PostgreSQL or time-series database
        +--> analytics and anomaly detection
        +--> dashboard, alarms, reports

Tests, logs, Git, CI, code review, and traceability surround every layer.
```

---

# 1. Priority roadmap

| Priority | Learn first | Evidence of readiness |
|---|---|---|
| Must know | OOP, Python, Core Java, debugging, testing/V&V, Git, SQL, embedded basics | Explain and code without looking up syntax |
| Must know | Threads, queues, exceptions, logging, APIs, TCP/serial concepts | Diagnose a timeout and design a resilient collector |
| Should know | IEC 61850 hierarchy, MMS/GOOSE/SV, PostgreSQL, MongoDB, time-series data | Draw message flow and explain a capture/debug plan |
| Should know | Agile/Jira/Confluence, design patterns, DI, SOLID, code review | Walk through a feature from story to verified release |
| Good to know | HVDC architecture, LCC/VSC, NumPy/Pandas, ML evaluation | Connect measurements to alarms and maintenance decisions |
| Bonus | OPC UA, Modbus, RTOS scheduling, deployment, performance tuning | Compare alternatives with explicit constraints |

---

# 2. OOP fundamentals

## 2.1 Class, object, state, behavior, constructor

A **class** is a reusable type definition. An **object** is one runtime instance. Attributes represent state; methods represent behavior. A constructor establishes a valid initial state. A destructor is cleanup logic, but deterministic cleanup should normally use a context manager in Python or `try/finally` and `AutoCloseable` in Java.

Why this job needs it: a device, measurement, IEC 61850 data point, alarm, database repository, and protocol client all have state and behavior. Modeling them explicitly reduces accidental coupling.

```python
from dataclasses import dataclass

@dataclass
class Measurement:
    device_id: str
    name: str
    value: float
    timestamp_ms: int

    def is_valid(self, minimum: float, maximum: float) -> bool:
        return minimum <= self.value <= maximum

m = Measurement("IED-01", "voltage", 230.4, 1720000000000)
print(m.is_valid(200.0, 260.0))
```

```java
public final class Measurement {
    private final String deviceId;
    private final String name;
    private final double value;
    private final long timestampMs;

    public Measurement(String deviceId, String name, double value, long timestampMs) {
        this.deviceId = deviceId;
        this.name = name;
        this.value = value;
        this.timestampMs = timestampMs;
    }

    public boolean isValid(double minimum, double maximum) {
        return value >= minimum && value <= maximum;
    }
}
```

Python is dynamically typed and concise; Java makes visibility, immutability, and contracts explicit at compile time. Use either to make invalid states difficult to represent.

## 2.2 Encapsulation and abstraction

**Encapsulation** keeps state behind an API and protects invariants. **Abstraction** exposes what a client needs while hiding implementation details. A Python property can validate assignments; Java uses private fields and methods.

```python
class Device:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self, transport) -> None:
        transport.open()
        self._connected = True
```

```java
public interface DeviceClient {
    void connect() throws DeviceException;
    Measurement read(String point) throws DeviceException;
}
```

Interview point: abstraction is not adding interfaces everywhere. Add an abstraction where multiple implementations, testing seams, or changing protocols justify it.

## 2.3 Inheritance, overriding, polymorphism

Inheritance models an **is-a** relationship. Composition models a **has-a** relationship and is usually safer for changing hardware integrations. Polymorphism lets calling code use a stable interface while implementations differ.

```python
class Transport:
    def send(self, payload: bytes) -> None:
        raise NotImplementedError

class TcpTransport(Transport):
    def send(self, payload: bytes) -> None:
        print("TCP", payload)

class SerialTransport(Transport):
    def send(self, payload: bytes) -> None:
        print("SERIAL", payload)

for transport in (TcpTransport(), SerialTransport()):
    transport.send(b"status")
```

Java supports class inheritance and interface implementation; Python uses duck typing and can use `abc.ABC` for an explicit contract. Method overloading is compile-time signature selection in Java. Python does not support traditional overloading; use default arguments, `*args`, singledispatch, or separate clear methods. Method overriding replaces inherited behavior and should preserve the parent contract.

## 2.4 Composition, aggregation, association

- **Composition:** owner controls the lifetime, for example `Collector` owns its private queue.
- **Aggregation:** objects can exist independently, for example a `Substation` references independently managed `IED` objects.
- **Association:** a general relationship, for example an alarm references a measurement.

```python
class Collector:
    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def collect_once(self):
        measurement = self.client.read("MMXU1.TotW.mag.f")
        self.repository.save(measurement)
```

This is dependency injection: dependencies arrive from outside, enabling a fake client and fake repository in unit tests.

## 2.5 Interfaces, abstract classes, access, static and instance members

An interface expresses a capability. An abstract class can share state or implementation while requiring selected methods. Java has `public`, `protected`, package-private, and `private`. Python conventions use `_name` for non-public members and `__name` name mangling, but they are not Java-style enforcement.

Static members belong to the type; instance members belong to an object. Avoid mutable static state in collectors because it causes hidden coupling and test order problems.

## 2.6 SOLID

- **Single Responsibility:** a protocol client should not also own SQL schema migration.
- **Open/Closed:** add a new transport by implementing an interface, not rewriting the collector.
- **Liskov Substitution:** a fake client must honor timeout and error contracts of the real client.
- **Interface Segregation:** prefer `Readable` and `Writable` interfaces over one huge device interface.
- **Dependency Inversion:** business logic depends on `MeasurementRepository`, not a concrete PostgreSQL driver.

## 2.7 Patterns useful here

| Pattern | Use in this role | Caution |
|---|---|---|
| Adapter | Wrap IEC 61850, serial, or vendor API behind a common client | Do not hide important protocol errors |
| Factory | Build clients from configuration | Validate configuration early |
| Strategy | Select polling, subscription, or anomaly algorithm | Keep strategies independently testable |
| Observer / Publisher-subscriber | Notify alarm and dashboard consumers | Define backpressure and delivery semantics |
| Repository | Isolate database access | Avoid turning it into a business-logic dump |
| State | Model device states such as disconnected/connecting/ready/fault | Define legal transitions |
| Circuit breaker | Stop hammering an unavailable device | Add recovery and observability |
| Producer-consumer | Separate acquisition from processing and persistence | Bound the queue |

## OOP interview answers

**Q: Why prefer composition over inheritance?** A: Composition keeps dependencies replaceable and avoids fragile base-class coupling. In a monitoring system, a collector can compose a transport and repository, so TCP, serial, and fake implementations are interchangeable.

**Q: What is polymorphism?** A: Calling code targets a common contract while runtime behavior is selected by the concrete implementation. It lets the same collector work with a real IEC 61850 client and a test double.

**Q: How do you test hardware-dependent classes?** A: Separate protocol/driver code from business logic, inject an interface, use a fake or mock for deterministic tests, then run a smaller hardware-integration suite against a simulator or lab device.

### OOP progression

- Beginner: model `Device`, `Measurement`, and `Alarm`.
- Intermediate: add interfaces, validation, composition, and unit tests.
- Advanced: implement a state machine, DI, repository, retry policy, and concurrency-safe event flow.

### OOP quick revision

- Class is a type; object is an instance.
- Encapsulation protects invariants.
- Abstraction hides implementation details.
- Inheritance is not the default answer.
- Composition is ideal for replaceable transports.
- Overloading differs between Python and Java.
- Overriding must preserve behavioral contracts.
- Interfaces define capabilities.
- Static mutable state is risky.
- SOLID supports change and testing.
- DI makes hardware code testable.
- Adapter is valuable at protocol boundaries.

### OOP practice

1. Implement `DeviceState` with legal transitions.
2. Create a `MeasurementRepository` interface and in-memory implementation.
3. Add TCP and serial transport adapters.
4. Write tests using a fake device client.
5. Refactor a large `DeviceManager` into three responsibilities.

### Common mistakes

- Treating every class as an abstraction.
- Using inheritance for code reuse only.
- Exposing mutable collections directly.
- Hiding all exceptions behind `Exception`.
- Making dependencies inside constructors with `new`.
- Confusing interface with implementation.

---

# 3. Python for the job

## 3.1 Fundamentals that interviewers expect

Know the behavior and complexity of strings, lists, tuples, sets, and dictionaries. Lists are ordered and mutable; tuples are ordered and immutable; sets provide unique values; dictionaries map hashable keys to values. Average dictionary/set lookup is $O(1)$, but collisions and poor hashing matter.

```python
values = [230.1, 229.8, 231.0]
valid = [value for value in values if 200 <= value <= 260]
by_device = {"IED-01": valid}
unique_tags = {"voltage", "current", "voltage"}
```

Functions should have clear contracts. Use comprehensions for simple transformations, not dense multi-step logic. Use `pathlib`, `with open(...)`, and explicit encodings for files. Use modules and packages to separate domain, infrastructure, and entry points. Use `venv` and a pinned dependency file.

## 3.2 Exceptions, logging, configuration

Catch the narrowest expected exception, preserve context, and log identifiers and timing without secrets.

```python
import logging

logger = logging.getLogger(__name__)

try:
    measurement = client.read("MMXU1.TotW.mag.f")
except TimeoutError:
    logger.warning("device_read_timeout", extra={"device_id": device_id})
    raise
```

Use `json` for APIs and machine-readable configuration. Use YAML only with trusted input or a safe loader. Separate configuration from code and validate required fields at startup.

## 3.3 Iterators, generators, decorators, context managers, closures

An iterator produces one item at a time. A generator uses `yield`, which is useful for large telemetry streams. A decorator wraps behavior such as timing or retrying. A context manager guarantees cleanup.

```python
from contextlib import contextmanager

@contextmanager
def device_session(client):
    client.connect()
    try:
        yield client
    finally:
        client.close()

def batches(items, size):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch
```

## 3.4 Mutability, copying, namespaces, LEGB, memory

Names reference objects. Mutable objects can change through aliases; immutable objects cannot. A shallow copy copies the outer container; a deep copy recursively copies nested values. LEGB means Local, Enclosing, Global, Built-in lookup. CPython mainly uses reference counting plus cyclic garbage collection. Do not rely on destructor timing for sockets or files.

```python
original = [[1], [2]]
shallow = original.copy()
shallow[0].append(9)  # original[0] also changes
```

## 3.5 Python OOP and engineering tools

Use `dataclass` for value objects, `property` for controlled access, `abc.ABC` for explicit contracts, and dunder methods such as `__repr__`, `__eq__`, and `__enter__` intentionally. Unit-test pure logic with `pytest`; mock only at external boundaries.

```python
from unittest.mock import Mock

def test_collector_saves_measurement():
    client = Mock()
    repository = Mock()
    client.read.return_value = {"name": "voltage", "value": 230.0}
    Collector(client, repository).collect_once()
    repository.save.assert_called_once()
```

## 3.6 Concurrency and communication

- Threads suit I/O-bound work and share memory; protect shared state.
- Processes bypass the GIL for CPU-bound Python work but cost more and require serialization.
- `asyncio` suits many concurrent I/O operations when libraries are async-compatible.
- `queue.Queue` is a safe producer-consumer boundary.
- A bounded queue forces an explicit overload policy: block, drop oldest, drop newest, or alarm.

```python
from queue import Queue

queue = Queue(maxsize=1000)
queue.put(measurement, timeout=1)
item = queue.get(timeout=1)
try:
    process(item)
finally:
    queue.task_done()
```

For sockets, define framing, timeouts, reconnect behavior, partial reads, and shutdown. For serial data, define baud rate, parity, stop bits, frame delimiter, checksum, and device addressing.

## 3.7 Python coding set: 30 interview problems

Use these as a progression. The expected answer should include approach, edge cases, and complexity.

1. **Two Sum:** hash map from value to index; $O(n)$ time, $O(n)$ space.
2. **Remove duplicates:** set for unsorted values; $O(n)$ average.
3. **Valid anagram:** character frequency dictionary; $O(n)$.
4. **First non-repeating character:** two-pass count then scan; $O(n)$.
5. **Reverse string:** slicing or two pointers; $O(n)$.
6. **Palindrome ignoring punctuation:** two pointers; $O(n)$.
7. **Move zeroes:** stable write pointer; $O(n)$, $O(1)$ extra.
8. **Merge sorted arrays:** two pointers; $O(n+m)$.
9. **Best time to buy/sell stock:** track minimum and best profit; $O(n)$.
10. **Valid parentheses:** stack and matching map; $O(n)$.
11. **Min stack:** stack of `(value, current_min)`; $O(1)$ operations.
12. **Queue using two stacks:** transfer only when output stack is empty.
13. **Evaluate postfix expression:** operand stack; $O(n)$.
14. **Longest substring without repeats:** sliding-window set/map; $O(n)$.
15. **Minimum window substring:** frequency counts and shrinking window.
16. **Maximum sum subarray of size k:** rolling window; $O(n)$.
17. **Binary search:** halve sorted search interval; $O(log n)$.
18. **First/last occurrence:** two boundary searches; $O(log n)$.
19. **Search rotated array:** identify sorted half each step; $O(log n)$.
20. **Merge intervals:** sort by start and merge overlaps; $O(n log n)$.
21. **Quick sort:** partition recursively; average $O(n log n)$.
22. **Merge sort:** divide and merge; $O(n log n)$ and $O(n)$ space.
23. **Reverse linked list:** iterative previous/current pointers; $O(n)$.
24. **Detect linked-list cycle:** Floyd slow/fast pointers; $O(n)$, $O(1)$.
25. **Merge two linked lists:** dummy head and pointer walk.
26. **Binary tree level order:** BFS queue; $O(n)$.
27. **Maximum tree depth:** DFS recursion or BFS; $O(n)$.
28. **Number of islands:** DFS/BFS grid traversal; $O(rows * cols)$.
29. **Graph reachability:** adjacency list plus visited set; $O(V+E)$.
30. **Climbing stairs:** dynamic programming with two previous values; $O(n)$ time, $O(1)$ space.

Example implementation pattern:

```python
def longest_unique_window(text: str) -> int:
    left = 0
    best = 0
    last_seen = {}
    for right, character in enumerate(text):
        if character in last_seen and last_seen[character] >= left:
            left = last_seen[character] + 1
        last_seen[character] = right
        best = max(best, right - left + 1)
    return best
```

Explain that the window never moves backward, so total pointer movement is linear. Follow-ups: Unicode characters, memory limits, streaming input, and whether the caller needs the substring or just its length.

### Python interview questions

- Why are default mutable arguments dangerous?
- What is the difference between `is` and `==`?
- Explain the GIL and when threads still help.
- Generator versus list: when is each appropriate?
- Shallow versus deep copy?
- How do you mock a device client?
- How do you make retries safe?
- How do you avoid logging sensitive values?
- What does a context manager guarantee?
- How would you debug a memory increase?

### Python hands-on project

Build a telemetry collector with a fake device, bounded queue, JSON configuration, structured logs, retries with exponential backoff, pytest tests, and a PostgreSQL repository interface. Add a simulator that emits malformed frames and delayed responses.

---

# 4. Core Java

## 4.1 Runtime and language model

The JDK contains development tools and the compiler; the JRE is the runtime concept; the JVM executes bytecode. Java source compiles to bytecode, which the JVM interprets or JIT-compiles. Primitive types hold values directly; wrapper classes such as `Integer` are objects and support generics and nullability.

Use `String` for immutable text, `StringBuilder` for single-threaded mutation, and `StringBuffer` only when its legacy synchronization is specifically needed. Prefer interfaces such as `List`, `Set`, and `Map` in variable declarations.

## 4.2 OOP and collections

Know constructor chaining, `this`, `super`, `final`, `static`, interface default methods, abstract classes, overloading, overriding, and access modifiers. `HashMap` uses hash codes to select buckets and `equals` to distinguish keys. If a class overrides `equals`, it must provide a consistent `hashCode`.

```java
record Measurement(String deviceId, String point, double value, long timestampMs) {}

Map<String, Measurement> latest = new HashMap<>();
latest.put("IED-01/voltage", new Measurement("IED-01", "voltage", 230.0, 1L));
```

Know `Comparable` for natural ordering and `Comparator` for external ordering. Generics provide compile-time type safety. Streams express transformations, filters, grouping, and reductions; do not use streams when a simple loop is clearer or when side effects obscure behavior. `Optional` can represent an absent return value, but should not be used indiscriminately for fields or parameters.

## 4.3 Exceptions, threads, memory

Checked exceptions are declared/handled compile-time exceptions; unchecked exceptions extend `RuntimeException` and usually represent programming errors or invalid runtime state. Catch specific exceptions and preserve causes.

Use `ExecutorService` rather than creating unbounded raw threads. Synchronization protects shared state; locks offer more control; `BlockingQueue` is often clearer than shared mutable lists. Understand thread lifecycle, interruption, deadlock conditions, and how to take a thread dump. Java GC manages heap memory, but leaks still occur through live references, caches, listeners, and unclosed resources.

```java
try (var input = Files.newBufferedReader(Path.of("config.json"))) {
    // use input
} catch (IOException exception) {
    throw new ConfigurationException("Cannot read configuration", exception);
}
```

## 4.4 Java problems: 25+ set

1. Two Sum with `HashMap`.
2. Frequency count with `Map`.
3. Group anagrams with sorted/frequency keys.
4. Valid parentheses using `Deque<Character>`.
5. LRU cache using `LinkedHashMap`.
6. Merge intervals.
7. Binary search.
8. Top K frequent values using heap.
9. Producer-consumer using `BlockingQueue`.
10. Immutable measurement value object.
11. Sort measurements by timestamp with `Comparator`.
12. Group measurements by device using streams.
13. Find duplicate files using hashes.
14. Implement a bounded retry policy.
15. Implement a thread-safe singleton only when truly needed.
16. Detect a linked-list cycle.
17. Reverse a linked list.
18. BFS tree traversal.
19. DFS graph traversal.
20. Rate limiter using timestamps and a lock.
21. Parse a log into structured records.
22. Merge two sorted iterators.
23. Implement a repository interface and in-memory repository.
24. Design a device connection state machine.
25. Build a simple circuit breaker.
26. Find the longest unique substring.
27. Implement a timeout wrapper using `Future`.
28. Write a `Comparator` that handles null timestamps safely.

### Java versus Python

| Concern | Python | Java |
|---|---|---|
| Typing | Dynamic, optional annotations | Static, compile-time checks |
| Interfaces | Protocols/ABCs/conventions | Explicit interfaces and abstract classes |
| Concurrency | Threads, processes, asyncio; GIL affects CPU work | Threads, executors, locks, futures |
| Memory | Reference counting plus GC in CPython | JVM garbage collector |
| Packaging | venv, pip, pyproject | Maven/Gradle, JARs |
| Best fit | Automation, integration, analysis, rapid services | Large typed services, established enterprise/runtime systems |

### Java interview questions

- JDK versus JVM?
- Why must `equals` and `hashCode` agree?
- HashMap collision and resizing?
- ArrayList versus LinkedList?
- HashSet versus TreeSet?
- Checked versus unchecked exception?
- Why use `ExecutorService`?
- What causes deadlock?
- `synchronized` versus `Lock`?
- What does `volatile` guarantee and not guarantee?
- Stream versus loop trade-offs?
- How can Java leak memory despite GC?

---

# 5. Embedded software fundamentals

An embedded system is a computing system dedicated to a product or physical process, often with timing, memory, power, reliability, and safety constraints. An MCU integrates CPU, memory, and peripherals; an MPU generally relies on external memory and runs a richer OS. RAM is volatile working memory; Flash stores firmware; EEPROM or emulated EEPROM stores persistent settings; registers control peripherals and report status.

```text
Application
  -> domain logic / alarms
  -> middleware / protocol stack
  -> driver / HAL
  -> peripheral registers
  -> electrical hardware
```

Know GPIO, ADC, DAC, PWM, timers, DMA, watchdogs, bootloaders, firmware, and device drivers. Polling is simple but wastes CPU and may miss timing; interrupts react quickly but require short, non-blocking ISR code. A watchdog resets a system that fails to service it, but blindly feeding it can hide deadlocks.

## RTOS concepts

A task is a schedulable unit. A scheduler selects runnable tasks according to priority and policy. A mutex protects ownership of a shared resource; a semaphore signals availability/events; a queue transfers data. Race conditions arise from unsynchronized interleavings. Deadlock requires circular wait, hold-and-wait, mutual exclusion, and no preemption. Priority inversion occurs when a high-priority task waits behind a low-priority owner while a medium task runs; priority inheritance helps.

Python/Java usually sit above firmware: they may configure devices, receive telemetry over TCP/serial/CAN gateways, issue commands, run test automation, or provide analytics. They do not replace deterministic low-level firmware where hard timing and direct register access are required.

### Embedded interview answer

**How would a Python service interact with embedded firmware?** Define a versioned protocol and framing, use a transport adapter, validate lengths/checksums/types, configure timeouts and retries, expose metrics and structured logs, keep the service resilient to reconnects, and test with a simulator plus hardware-in-loop tests.

### Embedded practice

1. Simulate a register map in Python.
2. Write a framed serial parser with checksum validation.
3. Implement a bounded telemetry queue.
4. Add a watchdog-style heartbeat monitor.
5. Draw a task/interrupt data flow and identify shared-state hazards.

---

# 6. Hardware and industrial communication

| Protocol | Typical use | Strength | Main risk |
|---|---|---|---|
| UART | Point-to-point device/configuration | Simple and ubiquitous | Framing/noise/baud mismatch |
| SPI | Short-board sensor/display links | Fast, full duplex | More wires, master-controlled |
| I2C | Multiple low-speed board peripherals | Two wires, addressing | Bus contention and pull-ups |
| CAN | Robust vehicle/industrial control | Arbitration, error handling | Small payload and bus load |
| Ethernet/TCP | Reliable routed application data | Ordering and delivery | Latency/reconnect/head-of-line blocking |
| UDP | Low-latency streaming | No connection overhead | Loss/order must be handled |
| Modbus | Simple industrial registers | Easy interoperability | Limited semantics/security |
| MQTT | Telemetry publish/subscribe | Decoupled and lightweight | Broker/security/retained-state issues |
| OPC UA | Industrial information modeling | Rich typed secure model | More complexity |

For every communication fault, check physical link, addressing, configuration, framing, bytes on the wire, timeouts, parser, application state, and observability. A Python reader that gets no data may have the wrong port, baud rate, IP/VLAN, device mode, frame delimiter, endian order, or subscription configuration.

### Debugging sequence: no device data

1. Reproduce with timestamp and device identifier.
2. Confirm device power, link LEDs, and process state.
3. Confirm IP/port or serial port and exclusive access.
4. Capture traffic or raw bytes.
5. Compare expected framing, checksum, endian order, and schema.
6. Check timeout, retry, reconnect, and queue metrics.
7. Test with a known-good simulator/client.
8. Isolate transport, parser, and business logic.
9. Fix the root cause and add a regression test.

---

# 7. IEC 61850

IEC 61850 is a family of standards for power utility automation. It defines information models, communication services, engineering language, and faster event/sample mechanisms so equipment can interoperate beyond vendor-specific point lists.

```text
Physical Device
  -> Logical Device
      -> Logical Node
          -> Data Object
              -> Data Attribute
```

An IED is an intelligent electronic device such as a protection relay or bay controller. A physical device may host logical devices. A logical node represents a function, such as `MMXU` for measurements or `PTOC` for overcurrent protection. Data objects contain meaningful properties; data attributes hold values, quality, timestamp, and related status.

## Communication models

- **MMS:** client/server communication, commonly for supervisory control, reports, reading, writing, and configuration-oriented access over TCP/IP.
- **GOOSE:** publisher/subscriber event messages for fast peer-to-peer protection/control signaling on the station LAN. Retransmissions improve delivery confidence but do not make Ethernet deterministic by magic.
- **Sampled Values:** publisher/subscriber streams of sampled current/voltage values, typically for process-bus applications.
- **Reports:** a server sends changes to a client using a dataset and report control block. Buffered reports retain events across a temporary client disconnect; unbuffered reports do not provide the same event retention.
- **Dataset:** a configured collection of data attributes.
- **Control block:** configuration defining how a service such as reporting, GOOSE, or SV behaves.

## SCL files

- **SSD:** system specification description.
- **SCD:** substation configuration description, system-level engineering configuration.
- **ICD:** IED capability description from a vendor.
- **CID:** configured IED description delivered to a specific device.

### MMS vs GOOSE vs SV

| Feature | MMS | GOOSE | SV |
|---|---|---|---|
| Model | Client/server | Publisher/subscriber | Publisher/subscriber |
| Purpose | Monitoring, control, reports | Fast events/interlocks/protection | Periodic sampled analog values |
| Transport style | Routable TCP/IP | Layer-2 Ethernet multicast | Layer-2 Ethernet multicast |
| Timing | Supervisory, generally slower | Millisecond-class protection signaling | High-rate deterministic stream |
| Example | Read `MMXU1.TotW` | Trip signal from relay | Three-phase current samples |
| Debug focus | Session, association, service response | VLAN, multicast, APPID, dataset, retransmission | stream ID, sample rate, synchronization, loss |

### GOOSE troubleshooting

Check publisher enable state and dataset, destination MAC, VLAN ID/priority, APPID, network path and switch multicast handling, subscriber configuration, GOOSE control block state number, test/simulation flags, packet capture, and time quality. Confirm the subscriber maps the correct data attributes and that the application is not rejecting stale or invalid quality. Start with a controlled simulator and compare a known-good capture.

### Practical software integration

A Python or Java service can use a vetted IEC 61850 library to establish MMS association, browse the model, subscribe to reports, read quality/timestamps, issue authorized controls, and persist measurements. Keep the protocol library behind an adapter. Do not treat a raw numeric value as valid without checking quality, timestamp, origin, and control/security state.

### IEC interview questions

1. What problem does IEC 61850 solve?
2. Explain the object hierarchy.
3. What is an IED?
4. MMS versus GOOSE?
5. Why is GOOSE fast?
6. What are SV used for?
7. Buffered versus unbuffered reports?
8. What is a dataset?
9. What do ICD/CID/SCD mean?
10. How would you verify an IED model?
11. What is a logical node?
12. How would you debug missing GOOSE?
13. How do VLANs and multicast affect GOOSE?
14. What quality information should an application store?
15. How would you test a control command safely?

### Memorize vs understand

Memorize the hierarchy, abbreviations, and MMS/GOOSE/SV comparison. Understand why a fast event is not implemented like a database query, how engineering files configure behavior, and how packet capture proves or disproves a network hypothesis. Practice reading an SCL model and correlating a packet with a logical-node attribute.

---

# 8. HVDC

HVDC transmits power as direct current between converter stations. A typical flow is:

```text
AC grid -> transformer/rectifier or VSC -> DC link -> inverter/VSC -> AC grid
```

It is attractive for long-distance bulk transfer, submarine cables, asynchronous grid interconnection, and controllable power flow. HVAC is easier to transform and distribute, but long lines have reactive power, stability, and charging-current issues. HVDC has expensive converter stations and requires specialized DC protection.

- **LCC-HVDC:** line-commutated converter using thyristors; mature and high-power, but needs strong AC support and consumes reactive power.
- **VSC-HVDC:** voltage-source converter using controllable switches such as IGBTs; supports independent active/reactive control, weak grids, and multi-terminal concepts, but has more complex switching and losses.
- **Rectifier:** AC to DC.
- **Inverter:** DC to AC.
- **Control:** current, DC voltage, active power, reactive power, AC voltage, firing angle or modulation, and limits.
- **Protection:** detect DC faults, converter faults, insulation/overcurrent issues, and isolate or block safely.

Software engineers may build acquisition, sequence-of-events logging, alarm processing, control-room interfaces, test automation, protocol gateways, historian integration, diagnostic analytics, and simulations. Safety-critical control decisions require explicit requirements, validation, fail-safe behavior, and controlled change.

### HVDC interview answer

**How does software contribute if the power electronics are hardware-controlled?** It can implement supervisory control and data acquisition, setpoints and interlocks at an approved control layer, data quality checks, alarm prioritization, event recording, communication gateways, test simulators, and predictive diagnostics. The software boundary and timing/safety requirements must be explicit.

---

# 9. Databases and telemetry

## PostgreSQL essentials

Relational tables enforce structure with primary keys, foreign keys, `NOT NULL`, `CHECK`, and `UNIQUE` constraints. Normalize transactional data to avoid anomalies; denormalize selectively for measured read performance. Index columns used by selective filters, joins, and ordering, but remember every index adds write/storage cost.

```sql
CREATE TABLE measurement (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    point_name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    quality TEXT NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    UNIQUE (device_id, point_name, measured_at)
);

CREATE INDEX measurement_device_time_idx
ON measurement (device_id, measured_at DESC);

SELECT device_id, point_name, AVG(value) AS average_value
FROM measurement
WHERE measured_at >= now() - interval '1 hour'
GROUP BY device_id, point_name
HAVING COUNT(*) >= 10;
```

Know joins, transactions, ACID, isolation, CTEs, subqueries, views, window functions, query plans, and parameterized queries. Use `EXPLAIN (ANALYZE, BUFFERS)` for slow queries. Never concatenate user input into SQL.

## MongoDB

MongoDB stores BSON documents in collections. Use CRUD, indexes, and aggregation pipelines. Embed data when it is bounded and read together; reference when it grows independently or has many-to-many relationships. Flexible schema is not an excuse to omit validation, indexes, or versioning.

## Time-series design

A measurement normally has a timestamp, measurement name, tags such as device/site, and fields such as value/quality. Time-series systems support retention, downsampling, and time-window aggregation efficiently. They are useful for voltage, current, temperature, frequency, power, alarms, and device status because time is the dominant query dimension.

```text
raw samples -> validation -> durable write -> hourly aggregates -> retention/archive
```

### Database comparison

| Need | PostgreSQL | MongoDB | Time-series DB |
|---|---|---|---|
| Strong relational constraints | Excellent | Application/schema validation | Varies |
| Flexible nested documents | Possible but not primary | Excellent | Usually limited model |
| High-rate timestamp queries | Partitioning/extensions help | Possible with schema/indexes | Primary strength |
| Complex joins/transactions | Strong | More limited/careful | Usually not the main use |

### SQL practice

1. Find latest valid measurement per device using `ROW_NUMBER()`.
2. Find devices with no data in 10 minutes.
3. Compute hourly averages and standard deviation.
4. Join alarms to device metadata.
5. Use a CTE to find voltage excursions and group contiguous events.
6. Inspect and improve a slow query with `EXPLAIN ANALYZE`.
7. Demonstrate a transaction that inserts a measurement and alarm atomically.

---

# 10. Data science and machine learning

Use NumPy for arrays and vectorized math, Pandas for tabular/time-indexed data, and plotting libraries for visual diagnosis. Before modeling: define the unit of observation, align timestamps, remove duplicates, handle missing values, inspect quality flags, identify outliers, and prevent future data from leaking into training.

```python
import pandas as pd

frame = pd.read_csv("measurements.csv", parse_dates=["measured_at"])
frame = frame.sort_values("measured_at")
frame["voltage_rolling_mean"] = (
    frame.set_index("measured_at")["voltage"]
         .rolling("5min")
         .mean()
         .to_numpy()
)
```

Relevant statistics: mean, median, variance, standard deviation, correlation, quantiles, and robust outlier rules. Correlation is not causation. For time series, use time-ordered train/validation/test splits.

Relevant models:

- Linear regression for continuous estimates.
- Logistic regression for interpretable binary fault classification.
- Decision tree/random forest for nonlinear tabular features and feature importance.
- SVM/KNN for smaller scaled datasets.
- K-means for exploratory clustering.
- PCA for dimensionality reduction.
- Anomaly detection using thresholds, isolation methods, clustering distance, or reconstruction error.

For rare faults, accuracy can mislead. Report precision, recall, F1, confusion matrix, false alarm rate, missed detection rate, and operational cost. A model is not production-ready until data quality, drift, thresholds, explainability, fallback behavior, and monitoring are defined.

### Practical ML exercise

Create features from voltage/current windows: mean, standard deviation, slope, min/max, frequency deviation, and quality count. Train on earlier time periods, validate on later periods, compare a threshold rule with logistic regression, and explain false positives to an engineer.

---

# 11. SDLC, Agile, Jira, and Confluence

## SDLC and V&V

```text
Requirement -> design -> implementation -> unit test -> integration test
-> system test -> verification -> validation -> release -> maintenance
```

**Verification:** did we build the product according to specified requirements? Example: a parser accepts every valid frame defined by the protocol requirement. **Validation:** did we build the right product for the operational need? Example: the monitoring operator receives a timely, understandable alarm when a protection measurement becomes invalid.

Requirements should be testable, traceable, and versioned. Definition of Done can include implementation, review, automated tests, documentation, traceability, and successful integration results.

Agile terms: epic, story, task, bug, sub-task, backlog, sprint, story points, priority, acceptance criteria, stand-up, planning, review, retrospective. A useful Jira flow is:

```text
Requirement -> Story -> Development -> Code review -> Test -> Bug fix
-> Verification -> Done
```

Confluence should hold architecture decisions, interfaces, runbooks, test procedures, and troubleshooting records with owners, versions, and links to requirements and tickets.

### Interview answer

**How do you work in a sprint?** Clarify acceptance criteria, break work into implementation and test tasks, identify hardware or protocol dependencies early, commit small reviewed changes, update Jira with evidence and blockers, demo behavior, and use the retrospective to improve the process.

---

# 12. Git and SVN

Git concepts: repository, working tree, index/staging area, commit, branch, remote, fetch, pull, push, merge, rebase, stash, cherry-pick, tag, revert, and reset. Prefer small commits with one reason for change.

```bash
git status
git switch -c feature/telemetry-quality
git add src/ tests/
git commit -m "Validate telemetry quality before persistence"
git fetch origin
git rebase origin/main
git push -u origin feature/telemetry-quality
```

- Wrong branch: create the correct branch from the commit, then restore the original branch as required; avoid rewriting shared history.
- Conflict: understand both changes, edit intentionally, run tests, `git add`, and continue merge/rebase.
- Undo shared commit: `git revert <commit>`.
- Recover deleted work: inspect `git reflog` and dangling commits.
- Move one change: `git cherry-pick <commit>`.

SVN is centralized with a repository and working copies; Git is distributed with local history and branching. SVN still appears in legacy industrial environments, so know checkout/update/commit/revert and repository locking at a high level.

---

# 13. Testing, code review, and debugging

## Testing levels

- Unit: one function/class with dependencies isolated.
- Integration: components such as parser plus repository or client plus protocol stack.
- System: end-to-end behavior with realistic devices/simulators.
- Regression: previously working behavior after a change.
- Smoke: basic build/deploy/startup health.
- Sanity: focused confidence after a narrow change.
- Performance/reliability: throughput, latency, soak, recovery, and resource behavior.
- Negative/boundary/fault injection: malformed frames, missing fields, timeouts, maximum values, device resets, database loss.

Trace each requirement to test case, execution evidence, result, defect, fix, and regression result. A test failure is evidence, not a verdict on which component is guilty.

## Professional code review checklist

Check correctness, boundaries, error handling, security, resource cleanup, concurrency, performance, naming, architecture, test quality, logs, documentation, and backward compatibility. A useful review comment names the risk and proposes a concrete improvement: “Could this timeout be bounded and covered by a test? An unavailable IED would otherwise block the worker indefinitely.”

## Debugging method

1. Reproduce with an exact version and input.
2. Record expected and actual behavior.
3. Collect logs, metrics, traces, packet captures, and environment details.
4. Form the smallest falsifiable hypothesis.
5. Isolate layers: device, transport, parser, domain, database, UI.
6. Change one variable at a time.
7. Identify root cause, not merely the symptom.
8. Fix, add a regression test, and rerun adjacent tests.

### 15 realistic scenarios

1. **Random application crash:** capture stack trace/core dump, correlate input and version, inspect unsafe resource handling, reproduce with the same frame, add a regression test.
2. **Device stops responding:** check power/link, heartbeat, packet capture, timeout/reconnect state, device logs, and whether the client is blocked on a shared lock.
3. **Communication timeout:** distinguish no packet, delayed packet, rejected request, and client timeout; inspect route/VLAN/firewall and timing.
4. **Incorrect sensor value:** verify raw bytes, scale/offset, endian order, unit, timestamp, quality, and calibration; compare a trusted instrument.
5. **Missing database data:** inspect queue depth, transaction errors, connection pool, constraints, clock, retention, and whether writes are acknowledged.
6. **Memory increasing:** measure heap/object growth, check unbounded queues/caches/listeners, reproduce under soak, and verify cleanup.
7. **CPU unexpectedly high:** profile, inspect tight retry loops, excessive logging, polling interval, parsing, and lock contention.
8. **GOOSE missing:** inspect publisher/subscriber configuration, multicast/VLAN/APPID, packet capture, control block state, and mapping.
9. **TCP drops:** inspect keepalive, idle timeout, peer resets, partial reads, reconnect backoff, and message framing.
10. **Thread deadlock:** capture thread dump, draw lock wait graph, enforce lock order or replace shared locks with queues.
11. **Race condition:** make timing observable, use thread sanitizer/tools where available, define ownership, and add deterministic synchronization tests.
12. **Wrong SQL result:** reduce query, inspect joins/cardinality/null behavior/time zones, add fixture tests, and use constraints.
13. **Java heap pressure:** inspect GC logs/heap dump, retained references, caches, and object creation; do not simply increase heap.
14. **Regression after update:** compare changed interfaces/config/schema, bisect commits, run traceability tests, and roll back safely if needed.
15. **Alarm storm:** check duplicate event handling, debounce/hysteresis, clock/time quality, recovery semantics, and rate-limited notifications.

---

# 14. Architecture and practical project

## Power System Monitoring and Fault Detection Platform

### Requirements

Collect measurements and quality from simulated or real IEDs, preserve timestamps, detect threshold and statistical anomalies, expose current status and alarms, survive device/database outages, and provide auditable logs.

### Architecture

```text
IED / simulator
   -> IEC 61850 adapter (MMS reports; optional GOOSE listener)
   -> validation + normalization
   -> bounded queue
   -> persistence worker -> PostgreSQL/time-series storage
   -> feature worker -> anomaly detector
   -> REST API -> dashboard/alert adapter

Java service: optional typed control/enterprise integration component
Cross-cutting: configuration, auth, metrics, logging, tests, Git/CI
```

### Suggested schema

- `device(device_id, name, site, protocol, enabled)`
- `measurement(device_id, point, value, quality, measured_at)`
- `alarm(alarm_id, device_id, rule, severity, state, opened_at, closed_at)`
- `model_version(model_id, feature_schema, trained_at, metrics)`
- `event(event_id, device_id, event_type, payload, occurred_at)`

### Python package layout

```text
power_monitor/
  domain/measurement.py alarm.py
  protocols/iec61850.py transport.py
  services/collector.py anomaly.py
  repositories/postgres.py
  api/routes.py
  config.py logging_setup.py
  tests/
```

### Implementation roadmap

1. Define requirements, quality semantics, and message schema.
2. Build a simulator and domain value objects.
3. Implement adapter and parser with timeout/reconnect behavior.
4. Add validation and bounded queue.
5. Persist measurements with constraints and indexes.
6. Add REST read API and health endpoints.
7. Add rules-based alarms before ML.
8. Add feature extraction and offline model evaluation.
9. Add integration, fault-injection, soak, and recovery tests.
10. Document deployment, rollback, operations, and known limitations.

### Failure design

Use idempotent writes, sequence numbers where available, quality flags, dead-letter storage for malformed messages, bounded retries, circuit breakers, clock synchronization checks, and explicit stale-data alarms. Never silently convert missing data into zero.

### Java component option

Use a Java service when the surrounding platform requires JVM deployment or strong typed integration. Define a shared schema, expose a repository/client interface, use `ExecutorService` and bounded queues, and keep protocol-specific logic isolated behind an adapter.

---

# 15. Interview question bank

The following compact bank is intended for spoken practice. For each question, answer in one minute first, then expand with an example, trade-off, and test.

## Round 1: programming, 30

1. Explain value versus reference behavior.
2. What is algorithmic complexity?
3. Array versus linked list?
4. Stack versus queue?
5. Hash table collision?
6. Why are boundary cases important?
7. Recursion risks?
8. Stable sort?
9. BFS versus DFS?
10. What makes a function testable?
11. How do you validate input?
12. What is idempotency?
13. What is a race condition?
14. What is a deadlock?
15. What is a timeout?
16. How do you handle partial data?
17. How do you reason from logs?
18. What is a contract?
19. What is a finite state machine?
20. Why bound a queue?
21. What is backpressure?
22. How do you choose a data structure?
23. What is defensive programming?
24. What is a regression?
25. What is a checksum?
26. Why version a protocol?
27. What is a resource leak?
28. What is deterministic testing?
29. What makes a good error message?
30. How do you explain a technical issue to an operator?

## Round 2: Python, 30

1. `is` versus `==`.
2. Mutable default argument.
3. LEGB.
4. Generator use case.
5. Decorator use case.
6. Context manager.
7. Shallow/deep copy.
8. GIL.
9. Thread versus process.
10. Asyncio use case.
11. Mock boundary.
12. pytest fixture.
13. Logging best practice.
14. JSON versus YAML.
15. Exception chaining.
16. Property versus public attribute.
17. Dataclass benefits.
18. Hashable object.
19. Dictionary complexity.
20. Memory increase diagnosis.
21. Queue shutdown.
22. Socket partial read.
23. Serial framing.
24. Retry safety.
25. Virtual environment.
26. Package layout.
27. Type hints value.
28. Pandas time index.
29. NumPy vectorization.
30. Python service health check.

## Round 3: Java, 30

1. JDK/JVM/JRE.
2. Bytecode and JIT.
3. Primitive versus wrapper.
4. String immutability.
5. StringBuilder.
6. Interface versus abstract class.
7. `final`.
8. `static`.
9. `this` and `super`.
10. Overload versus override.
11. `equals` and `hashCode`.
12. HashMap internals.
13. List/Set/Map.
14. Comparable/Comparator.
15. Checked exception.
16. Try-with-resources.
17. Generic type erasure.
18. Stream trade-off.
19. Optional.
20. ExecutorService.
21. synchronized.
22. Lock.
23. volatile.
24. Deadlock.
25. Thread interruption.
26. BlockingQueue.
27. GC leak.
28. Heap dump.
29. Immutable class.
30. Java service shutdown.

## Round 4: OOP, 25

1. Encapsulation.
2. Abstraction.
3. Polymorphism.
4. Composition.
5. Aggregation.
6. SOLID.
7. Dependency inversion.
8. Dependency injection.
9. Adapter.
10. Factory.
11. Strategy.
12. Observer.
13. Repository.
14. State pattern.
15. Interface segregation.
16. Liskov violation.
17. Static state risk.
18. Overloading in Python.
19. Abstract class use.
20. Hardware abstraction.
21. Test double.
22. Mock versus fake.
23. Domain object.
24. Cohesion/coupling.
25. Refactoring approach.

## Round 5: embedded, 25

1. Embedded versus application software.
2. MCU versus MPU.
3. RAM/Flash/EEPROM.
4. Register.
5. GPIO.
6. ADC/DAC.
7. PWM.
8. Interrupt.
9. ISR rule.
10. Polling versus interrupt.
11. DMA.
12. Watchdog.
13. Bootloader.
14. Driver/HAL.
15. RTOS task.
16. Mutex/semaphore.
17. Queue.
18. Priority inversion.
19. Real-time deadline.
20. Firmware update risk.
21. Python-to-device boundary.
22. Hardware-in-loop.
23. Fault injection.
24. Heartbeat.
25. Safe failure.

## Round 6: databases, 25

1. Primary/foreign key.
2. Index trade-off.
3. Join types.
4. ACID.
5. Isolation.
6. Normalization.
7. GROUP BY/HAVING.
8. CTE.
9. Window function.
10. Query plan.
11. SQL injection.
12. Transaction boundary.
13. PostgreSQL versus MongoDB.
14. BSON.
15. Embed versus reference.
16. Time-series schema.
17. Retention.
18. Downsampling.
19. Latest row per device.
20. Missing telemetry query.
21. Duplicate write protection.
22. Time zones.
23. Connection pool.
24. Migration.
25. Backup/recovery.

## Round 7: data science/ML, 20

1. Mean versus median.
2. Variance.
3. Correlation.
4. Outlier.
5. Missing data.
6. Feature.
7. Label.
8. Train/validation/test.
9. Leakage.
10. Overfitting.
11. Bias/variance.
12. Precision/recall.
13. Confusion matrix.
14. F1.
15. Threshold tuning.
16. Random forest.
17. K-means.
18. PCA.
19. Time split.
20. Model monitoring.

## Round 8: IEC 61850, 25

1. Purpose.
2. IED.
3. Physical/logical device.
4. Logical node.
5. Data object/attribute.
6. MMS.
7. GOOSE.
8. SV.
9. Report.
10. Buffered report.
11. Dataset.
12. Control block.
13. SCL.
14. ICD.
15. CID.
16. SCD.
17. GOOSE speed.
18. GOOSE troubleshooting.
19. Quality/timestamp.
20. VLAN/multicast.
21. MMS session.
22. Safe control command.
23. Simulator test.
24. Subscriber mapping.
25. Packet capture evidence.

## Round 9: HVDC, 20

1. Why HVDC?
2. HVAC comparison.
3. Converter station.
4. Rectifier/inverter.
5. DC link.
6. LCC.
7. VSC.
8. Thyristor.
9. IGBT.
10. Active power control.
11. DC voltage control.
12. Reactive control.
13. DC fault.
14. Converter fault.
15. Protection.
16. Monitoring.
17. Control boundary.
18. Test automation.
19. Alarm design.
20. Software failure handling.

## Round 10: Git/Agile/Jira, 20

1. Working tree/index.
2. Commit.
3. Merge/rebase.
4. Fetch/pull.
5. Revert/reset.
6. Reflog.
7. Cherry-pick.
8. Conflict resolution.
9. Pull request.
10. SVN comparison.
11. Epic/story/task/bug.
12. Acceptance criteria.
13. Story points.
14. Sprint planning.
15. Stand-up.
16. Review.
17. Retrospective.
18. Definition of Done.
19. Confluence page quality.
20. Handling a blocked hardware dependency.

## Round 11: testing/V&V, 25

1. Verification versus validation.
2. Unit test.
3. Integration test.
4. System test.
5. Regression.
6. Smoke/sanity.
7. Boundary test.
8. Negative test.
9. Fault injection.
10. Requirements traceability.
11. Test oracle.
12. Mock versus simulator.
13. Hardware-in-loop.
14. Reliability test.
15. Performance test.
16. Test evidence.
17. Failed test triage.
18. Flaky test.
19. Coverage limitation.
20. Release gate.
21. Data quality test.
22. Protocol conformance test.
23. Recovery test.
24. Security test.
25. Regression after schema change.

## Round 12: debugging/scenarios, 30

1. Device stops transmitting.
2. Wrong sensor scaling.
3. TCP reconnect loop.
4. Serial parser desynchronizes.
5. Missing database rows.
6. Slow query.
7. Memory growth.
8. CPU spike.
9. Deadlock.
10. Race condition.
11. GOOSE missing.
12. Alarm storm.
13. Stale timestamps.
14. Java heap pressure.
15. Python exception swallowed.
16. Configuration mismatch.
17. Firmware/software version mismatch.
18. Update regression.
19. Queue overload.
20. Lost messages.
21. Duplicate messages.
22. Model false alarms.
23. Dashboard stale data.
24. Clock drift.
25. Database outage.
26. Partial packet.
27. Invalid quality flag.
28. Unauthorized control.
29. Intermittent lab failure.
30. Production incident communication.

For every scenario, a strong answer starts with reproduction and evidence, narrows the layer, states hypotheses, changes one variable, fixes the root cause, and adds a regression test. Do not claim certainty before observing the system.

---

# 16. Coding-round patterns

Use these patterns aloud: hash map for complement/count, set for membership, stack for nested state, queue for FIFO/BFS, two pointers for ordered sequences, sliding window for contiguous constraints, binary search for monotonic answer spaces, DFS/BFS for graphs, and dynamic programming for overlapping subproblems.

For each coding problem, state:

- Input assumptions and edge cases.
- Brute-force idea and why it is too slow.
- Invariant maintained by the optimized algorithm.
- Time and space complexity.
- Test cases: empty, one element, duplicates, maximum/boundary, malformed input if applicable.
- Production adaptation: validation, logging, cancellation, memory limits.

A useful OOP coding prompt is: “Design a device client that supports TCP and serial transports, bounded retries, a circuit breaker, and test doubles.” Start with interfaces, injected dependencies, explicit states, and tests for timeout, reconnect, and shutdown.

---

# 17. 30-day plan, 3-4 hours per day

| Day | Study | Coding/practice | Interview/revision |
|---|---|---|---|
| 1 | OOP class/object/encapsulation | Device and measurement classes | 10 OOP questions |
| 2 | Inheritance/polymorphism/composition | Transport adapters | Explain composition |
| 3 | SOLID/DI/patterns | Repository with fake | Code review your design |
| 4 | Python data types/functions | Two Sum, anagram, palindrome | Python fundamentals |
| 5 | Exceptions/files/modules/venv | JSON config loader | Error-handling answers |
| 6 | Iterators/generators/decorators | Streaming batches | Explain lazy evaluation |
| 7 | Copying/scope/memory | Mutability exercises | Weekly revision |
| 8 | Python OOP/dataclasses | pytest and mocks | Mock boundary question |
| 9 | Threads/processes/queues | Producer-consumer | GIL and race conditions |
| 10 | Async/sockets/serial | Framed parser | Timeout/reconnect scenario |
| 11 | Java runtime/OOP | Immutable Measurement | JVM questions |
| 12 | Collections/generics | HashMap and sorting problems | equals/hashCode |
| 13 | Exceptions/streams/Optional | Log parser | Java/Python comparison |
| 14 | Java concurrency/GC | Executor + queue | Deadlock/heap questions |
| 15 | Embedded hardware basics | Register/peripheral simulator | MCU/MPU, ISR |
| 16 | RTOS/synchronization | State machine/heartbeat | Mutex/semaphore |
| 17 | UART/SPI/I2C/CAN | Protocol comparison notes | Debug no-data case |
| 18 | Ethernet/TCP/UDP/Modbus/MQTT | Socket client | Capture-based reasoning |
| 19 | PostgreSQL schema/SQL | Create measurement tables | Joins/constraints |
| 20 | Transactions/indexes/window SQL | Slow-query exercise | ACID/query plan |
| 21 | MongoDB/time-series | Telemetry schema | Database comparison |
| 22 | NumPy/Pandas/statistics | Clean and plot sample data | Mean/outlier questions |
| 23 | ML models/metrics | Threshold vs classifier | Precision/recall |
| 24 | IEC hierarchy/MMS | Draw model and client flow | 15 IEC questions |
| 25 | GOOSE/SV/SCL | Troubleshooting checklist | Packet-capture explanation |
| 26 | HVDC/LCC/VSC | Draw power flow | 10 HVDC questions |
| 27 | SDLC/Agile/Git/Jira | Branch/conflict/revert drill | Tell sprint story |
| 28 | Testing/V&V/code review | Fault-injection tests | Traceability answer |
| 29 | Practical project integration | Build collector slice | Full mock interview |
| 30 | Debugging and final review | Solve 5 timed problems | Cheat sheet and STAR stories |

Daily rhythm: 60-75 minutes concept study, 60 minutes coding, 45 minutes hands-on project/debugging, 30 minutes spoken interview answers, and 15 minutes revision notes.

---

# 18. Final interview cheat sheet

## Definitions

- OOP: state and behavior grouped behind contracts.
- Encapsulation protects invariants; abstraction hides implementation.
- Composition is usually safer than inheritance for integrations.
- DI makes hardware and database dependencies replaceable.
- Verification checks conformance to requirements; validation checks operational fitness.
- A bounded queue makes overload visible and controllable.
- A timeout is a correctness boundary, not merely a performance setting.

## Python

- Use `with` for cleanup, `logging` for evidence, `pytest` for tests, and mocks at external boundaries.
- Threads help I/O; processes help CPU-bound Python; asyncio needs async-compatible I/O.
- Never swallow exceptions or use mutable default arguments.
- Validate protocol framing, length, checksum, units, timestamp, and quality.

## Java

- JDK develops, JVM executes bytecode.
- `equals` and `hashCode` must agree.
- Prefer interfaces, immutable values, `ExecutorService`, `BlockingQueue`, and try-with-resources.
- GC does not prevent leaks from live caches/listeners.

## Embedded and protocols

- ISR: short, deterministic, no blocking.
- Mutex protects ownership; semaphore signals; queue transfers.
- UART point-to-point, SPI fast board bus, I2C addressed two-wire bus, CAN robust arbitration, TCP ordered reliable, UDP lightweight/loss-tolerant.
- Always separate transport, parser, domain logic, and persistence.

## IEC 61850

```text
Physical Device -> Logical Device -> Logical Node -> Data Object -> Data Attribute
```

- MMS: client/server supervisory access.
- GOOSE: fast Layer-2 event signaling.
- SV: high-rate sampled measurement stream.
- Dataset + control block configure reports/GOOSE/SV behavior.
- ICD describes capability; CID configures one IED; SCD describes the system.
- Missing GOOSE: verify publisher, subscriber mapping, multicast/VLAN/APPID, control-block state, network capture, and quality/test flags.

## HVDC

- AC-to-DC converter, DC link, DC-to-AC converter.
- LCC uses thyristors and needs a strong grid; VSC uses controllable switches such as IGBTs and supports independent control.
- Software surrounds power conversion with monitoring, control interfaces, alarms, diagnostics, event logs, testing, and communications.

## Databases

- PostgreSQL for relational integrity and transactions; MongoDB for document-shaped flexible data; time-series databases for timestamp-heavy telemetry.
- Use constraints, parameterized SQL, appropriate indexes, transactions, retention, and downsampling.
- Diagnose slow SQL with `EXPLAIN (ANALYZE, BUFFERS)`.

## Debugging answer template

“First I reproduce it and record expected versus actual behavior, version, timestamps, and identifiers. I collect logs, metrics, and a packet/raw-data capture. I isolate device, transport, parser, domain, and persistence layers, then test the smallest hypothesis one variable at a time. After identifying the root cause, I implement the narrow fix, add a regression test, run adjacent integration tests, and document the operational impact.”

## Commands

```bash
git status
git switch -c feature/name
git add .
git commit -m "Describe one change"
git fetch origin
git rebase origin/main
git revert <commit>
git reflog
python -m venv .venv
python -m pytest
```

## Final practice standard

Before the interview, be able to draw the monitoring architecture, explain one Python and one Java design, solve five coding problems under time pressure, write a useful SQL query, troubleshoot a missing GOOSE message, explain HVDC at block-diagram level, describe verification versus validation, and tell one concise story about debugging a difficult failure.

---

# 19. Major-section practice cards

These cards make the same study loop explicit for each major area: revise, answer, practice, and avoid the common traps.

## Python card

**Quick revision:** data structures; mutability; LEGB; exceptions; context managers; generators; decorators; OOP; logging; pytest; mocks; queues; threads/processes/asyncio; sockets; configuration.

**Interview questions:** Explain the GIL. When is a generator better than a list? How do you mock a device? How do you prevent a retry storm? What happens on a partial socket read? How do you diagnose memory growth? How do you shut down a worker? Why use a bounded queue? How do you validate JSON/YAML? What belongs in a fixture? How do you make logs useful?

**Hands-on:** build a framed parser, a retry decorator, a producer-consumer collector, a pytest fake-device suite, and a Pandas telemetry cleaner.

**Common mistakes:** broad exception catches; mutable defaults; unbounded queues; blocking the event loop; logging secrets; relying on destructor timing; mocking the code under test instead of the external boundary.

## Java card

**Quick revision:** JVM/JDK; bytecode; immutability; collections; generics; interfaces; exceptions; equals/hashCode; streams; Optional; executors; locks; interruption; deadlock; GC.

**Interview questions:** Why is HashMap lookup usually constant time? Why must equals and hashCode agree? What is checked versus unchecked? How do you stop an ExecutorService? What does volatile guarantee? How do you investigate heap growth? When is a stream less readable than a loop? How do you make a value object immutable? What causes deadlock? How do you handle interrupted threads?

**Hands-on:** implement an immutable measurement, a bounded executor collector, a blocking producer-consumer queue, a circuit breaker, and a heap-growth test.

**Common mistakes:** catching Exception and continuing; ignoring interruption; using raw threads without shutdown; mutable keys in HashMap; assuming GC prevents leaks; parallel streams for I/O without measuring.

## Embedded and communication card

**Quick revision:** MCU/MPU; memory; registers; GPIO/ADC/PWM; ISR; polling; DMA; watchdog; bootloader; driver/HAL; RTOS tasks; mutex/semaphore/queue; UART/SPI/I2C/CAN/TCP/UDP.

**Interview questions:** What must an ISR avoid? When do interrupts beat polling? What is priority inversion? How does a watchdog help? How would Python interact with firmware? How do you detect a framing error? Why can TCP still lose an application message? How do you handle device reset? What is backpressure? How do you test hardware without the hardware?

**Hands-on:** implement a checksum parser, heartbeat monitor, simulated register map, bounded queue, and reconnecting TCP client.

**Common mistakes:** blocking in an ISR; unbounded retries; treating TCP reads as message boundaries; ignoring endianness; feeding a watchdog blindly; sharing state without ownership; confusing mutexes and semaphores.

## IEC 61850 card

**Quick revision:** IED; hierarchy; logical nodes; data objects/attributes; quality/time; MMS; reports; datasets; control blocks; GOOSE; SV; SCL; ICD/CID/SCD.

**Interview questions:** Why was IEC 61850 created? MMS versus GOOSE? Why is GOOSE fast? When is SV used? What does a buffered report provide? How do SCL files differ? What is the GOOSE troubleshooting order? Which values must be persisted besides the measurement? How would you test a control command? How would you prove a network issue?

**Hands-on:** browse a sample model, map a point to a database row, draw publisher/subscriber flow, compare packet capture with configuration, and simulate stale quality.

**Common mistakes:** treating GOOSE as TCP; ignoring multicast/VLAN/APPID; trusting a value with bad quality; confusing ICD and CID; omitting timestamps; testing controls without authorization/interlocks.

## HVDC card

**Quick revision:** AC/DC flow; converter stations; rectifier/inverter; DC link; LCC/thyristor; VSC/IGBT; active/reactive/DC-voltage control; faults; protection; monitoring.

**Interview questions:** Why use HVDC? LCC versus VSC? What does a converter station do? Why does LCC need a strong grid? What can software monitor? How would you handle stale measurements? What is an alarm versus a trip? How do you test a supervisory control interface? What is a safe failure? How do you correlate a fault with sequence-of-events data?

**Hands-on:** draw a complete power-flow diagram, model a converter state machine, create alarm priorities, build a measurement simulator, and write a fault timeline query.

**Common mistakes:** presenting supervisory software as the power-electronic control loop; confusing rectifier and inverter; ignoring reactive power; omitting interlocks; designing alarms without hysteresis or acknowledgment semantics.

## Database and analytics card

**Quick revision:** keys; constraints; joins; indexes; ACID; isolation; transactions; query plans; MongoDB documents; time-series tags/fields; retention; Pandas cleaning; train/test split; precision/recall.

**Interview questions:** How do you find the latest row per device? Why did an index not help? PostgreSQL versus MongoDB? Embed or reference? How do you prevent duplicate telemetry? What is time-series downsampling? Why is accuracy misleading for rare faults? What is leakage? How do you handle missing data? How do you monitor model drift?

**Hands-on:** design the measurement schema, run an EXPLAIN, write a latest-value window query, aggregate hourly data, and compare a threshold detector with a classifier.

**Common mistakes:** concatenating SQL; indexing every column; storing timestamps without time zones; treating missing as zero; random-splitting time series; reporting accuracy alone; training on future information.

## SDLC, Git, and Agile card

**Quick revision:** requirement; design; implementation; test; release; maintenance; verification/validation; story; acceptance criteria; sprint; review; DoD; branch; commit; merge/rebase; revert.

**Interview questions:** Describe your sprint workflow. What makes a requirement testable? Verification versus validation? Merge versus rebase? How do you recover deleted work? How do you handle a blocked hardware dependency? What belongs in a pull request? What makes good acceptance criteria? What belongs in Confluence? When do you revert rather than reset?

**Hands-on:** turn a device requirement into a story and tests, create a feature branch, resolve a conflict, perform a safe revert, and write an architecture decision record.

**Common mistakes:** vague stories; no acceptance criteria; giant commits; rewriting shared history; resolving conflicts without tests; treating documentation as an afterthought; hiding blockers until sprint end.

## Testing, V&V, review, and debugging card

**Quick revision:** unit/integration/system; smoke/sanity; regression; performance/reliability; negative/boundary/fault injection; traceability; logs; metrics; reproduction; root cause; regression test.

**Interview questions:** What is verification versus validation? What is your first debugging step? How do you triage a failed test? How do you test a timeout? What is a flaky test? How do you review concurrency code? What evidence proves a fix? How do you test device loss? What is the value and limit of coverage? How do you communicate an incident?

**Hands-on:** inject malformed frames, stop the database, delay the device, fill the queue, create a deadlock in a test fixture, and trace each failure to a requirement.

**Common mistakes:** changing many variables at once; fixing symptoms; testing only the happy path; relying on coverage percentage; ignoring test environment/version; logging without correlation IDs; closing a defect without regression evidence.

## Architecture and project card

**Quick revision:** layered architecture; separation of concerns; adapter; repository; producer-consumer; event-driven flow; API; persistence; observability; configuration; deployment; rollback.

**Interview questions:** Where should protocol code live? Why use a queue? How do you handle overload? How do you make writes idempotent? What happens during database outage? How do you version messages? Where do alarms run? How do you test the complete system? What are the first operational metrics? What would you improve in version two?

**Hands-on:** implement the simulator-to-database slice, add health/readiness endpoints, add correlation IDs, write a failure-mode table, and present the design in five minutes.

**Common mistakes:** one giant service class; coupling domain logic to a vendor library; no shutdown path; no bounded resources; missing schema/version strategy; no observability; calling a prototype production-ready without recovery testing.
