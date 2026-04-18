# CAPL Complete Language Overview
## Communication Access Programming Language – Detailed Reference

---

## What is CAPL?

**CAPL** (Communication Access Programming Language) is a C-like scripting language developed by **Vector Informatik** for use in **CANoe** and **CANalyzer** tools. It is specifically designed for:

- Simulating ECU nodes on CAN/LIN/FlexRay/Ethernet networks
- Sending and receiving CAN/LIN messages
- Writing automated test cases
- Monitoring and validating bus signals
- Implementing state machines and diagnostic sequences

CAPL files use the `.capl` extension and are compiled inside the CANoe/CANalyzer environment.

---

## 1. Program Structure

A CAPL script is organized into four main blocks:

```
includes        { }    ← include other .capl files
variables       { }    ← global variable declarations
                       ← function definitions (outside any block)
on <event>      { }    ← event handler blocks (the main execution units)
```

### Minimal CAPL Script
```capl
includes { }

variables
{
  msTimer myTimer;
  int gCounter = 0;
}

on start
{
  write("Script started");
  setTimer(myTimer, 1000);
}

on timer myTimer
{
  gCounter++;
  write("Tick %d", gCounter);
  setTimer(myTimer, 1000);
}

on stopMeasurement
{
  write("Script stopped after %d ticks", gCounter);
}
```

---

## 2. Data Types

### 2.1 Integer Types

| Type | Size | Range | Notes |
|---|---|---|---|
| `byte` | 8-bit | 0 … 255 | Unsigned |
| `word` | 16-bit | 0 … 65535 | Unsigned |
| `dword` | 32-bit | 0 … 4,294,967,295 | Unsigned |
| `qword` | 64-bit | 0 … 2^64−1 | Unsigned |
| `int` | 32-bit | −2,147,483,648 … 2,147,483,647 | Signed |
| `long` | 32-bit | −2,147,483,648 … 2,147,483,647 | Signed (alias for int) |
| `int64` | 64-bit | −2^63 … 2^63−1 | Signed 64-bit |

```capl
byte  b  = 0xFF;
word  w  = 0x1A2B;
dword d  = 0xDEADBEEF;
int   i  = -1024;
long  l  = 99999;
int64 big = 1234567890123;
```

### 2.2 Floating-Point Types

| Type | Size | Precision | Notes |
|---|---|---|---|
| `float` | 32-bit | ~7 decimal digits | IEEE 754 single |
| `double` | 64-bit | ~15 decimal digits | IEEE 754 double |

```capl
float  speed    = 120.5;
double pi       = 3.14159265358979;
float  factor   = 0.1;
float  result   = 3600.0 * factor;
```

### 2.3 Character and String Types

| Type | Description |
|---|---|
| `char` | Single character (8-bit ASCII) |
| `char[]` | Character array = string (null-terminated) |

```capl
char   c         = 'A';
char   name[32]  = "EngineECU";
char   buf[128];
```

### 2.4 Boolean (No Native Type)
CAPL has no boolean keyword. Use `int` with 0/1:
```capl
int gActive = 0;   // 0 = false
int gFault  = 1;   // 1 = true

// Any non-zero integer is truthy
if (gActive)
  write("Active");
```

### 2.5 Special Timer Types

| Type | Resolution | Description |
|---|---|---|
| `msTimer` | 1 millisecond | Millisecond timer |
| `timer` | 1 second | Second-resolution timer |

```capl
msTimer fastTimer;   // ms resolution
timer   slowTimer;   // second resolution

setTimer(fastTimer, 100);  // fire in 100 ms
setTimer(slowTimer, 5);    // fire in 5 seconds
cancelTimer(fastTimer);    // cancel before firing
```

### 2.6 Message Type

Represents a CAN/LIN message to send or receive:
```capl
// Declare by numeric ID
message 0x100        txMsg;

// Declare by symbolic DBC name
message EngineData   engMsg;

// Fields
txMsg.id       = 0x100;
txMsg.dlc      = 8;
txMsg.byte(0)  = 0xAB;
txMsg.byte(1)  = 0xCD;
txMsg.dir      = TX;        // RX or TX
txMsg.channel  = 1;

output(txMsg);              // transmit
```

### 2.7 Type Summary Table

```
Type       Bytes  Signed   Typical Use
─────────  ─────  ───────  ──────────────────────────────
byte       1      No       CAN data bytes, status flags
word       2      No       16-bit raw signal values
dword      4      No       32-bit addresses, file handles
qword      8      No       64-bit counters
int        4      Yes      Loop counters, signed values
long       4      Yes      DTC codes, timestamps
int64      8      Yes      Large signed values
float      4      —        Signal physical values
double     8      —        High-precision calculations
char       1      —        Single characters
char[]     N      —        Strings (null-terminated)
msTimer    —      —        Millisecond timer
timer      —      —        Second timer
message    —      —        CAN/LIN frame (send/receive)
```

---

## 3. Variables

### 3.1 Global Variables (in `variables { }` block)
- Persist for the entire measurement session
- Accessible from all event handlers and functions
- Prefix convention: `g` for global

```capl
variables
{
  int     gCounter    = 0;
  float   gSpeed      = 0.0;
  byte    gTxData[8]  = {0,0,0,0,0,0,0,0};
  msTimer gCycleTimer;
  message 0x200 gVehicleMsg;

  // Constants (use const keyword)
  const int MAX_RPM   = 8000;
  const float FACTOR  = 0.25;
}
```

### 3.2 Local Variables
- Declared inside functions or event handlers
- Exist only for the duration of that call
- Must be declared at the **top** of the block (C89 style)

```capl
on start
{
  int i;          // ← declare at top
  float avg;
  char buf[64];

  avg = 123.4;
  snprintf(buf, elCount(buf), "Average: %.2f", avg);
  write(buf);
}
```

### 3.3 Static Variables
Retain value between calls (like C static):
```capl
void CountCalls()
{
  static int callCount = 0;
  callCount++;
  write("Called %d times", callCount);
}
```

### 3.4 Environment Variables
Special variables bridging CAPL with CANoe panels:
```capl
// Read env var (panel slider/button)
float speed = @EnvVehicleSpeed;

// Write env var (update panel display)
@EnvVehicleSpeed = 120.0;

// React to env var change
on envVar EnvVehicleSpeed
{
  write("Speed changed to: %.1f", this.value);
}
```

### 3.5 System Variables (Namespaced)
```capl
@sysvar::Powertrain::EngineRPM = 3000.0;
float rpm = @sysvar::Powertrain::EngineRPM;
```

---

## 4. Operators

### 4.1 Arithmetic Operators
| Operator | Description | Example |
|---|---|---|
| `+` | Addition | `a + b` |
| `-` | Subtraction | `a - b` |
| `*` | Multiplication | `a * b` |
| `/` | Division | `a / b` |
| `%` | Modulo (integers) | `a % b` |
| `++` | Increment | `i++` or `++i` |
| `--` | Decrement | `i--` or `--i` |

### 4.2 Comparison Operators
| Operator | Description |
|---|---|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `>` | Greater than |
| `<=` | Less than or equal |
| `>=` | Greater than or equal |

### 4.3 Logical Operators
| Operator | Description | Example |
|---|---|---|
| `&&` | Logical AND | `a > 0 && b < 10` |
| `\|\|` | Logical OR | `a == 1 \|\| b == 2` |
| `!` | Logical NOT | `!gActive` |

### 4.4 Bitwise Operators
| Operator | Description | Example |
|---|---|---|
| `&` | Bitwise AND | `0xFF & 0x0F` → `0x0F` |
| `\|` | Bitwise OR | `0xF0 \| 0x0F` → `0xFF` |
| `^` | Bitwise XOR | `0xFF ^ 0xF0` → `0x0F` |
| `~` | Bitwise NOT | `~0x00` → `0xFF` |
| `<<` | Left shift | `1 << 4` → `0x10` |
| `>>` | Right shift | `0x80 >> 4` → `0x08` |

### 4.5 Assignment Operators
```capl
a  = 5;     a += 3;    a -= 2;
a *= 4;     a /= 2;    a %= 3;
a &= 0x0F;  a |= 0x80; a ^= 0xFF;
a <<= 2;    a >>= 1;
```

---

## 5. Control Flow

### 5.1 if / else if / else
```capl
if (gSpeed > 180.0)
  write("OVERSPEED");
else if (gSpeed > 120.0)
  write("High speed");
else
  write("Normal speed");
```

### 5.2 switch / case
```capl
switch (gGear)
{
  case 0:  write("Park");    break;
  case 1:  write("1st");     break;
  case 7:  write("Reverse"); break;
  default: write("Unknown"); break;
}
```

### 5.3 for Loop
```capl
int i;
for (i = 0; i < 8; i++)
  write("byte[%d] = 0x%02X", i, gTxData[i]);
```

### 5.4 while Loop
```capl
int count = 0;
while (count < 10)
{
  count++;
}
```

### 5.5 do-while Loop
```capl
int attempts = 0;
do
{
  attempts++;
} while (attempts < 3);
```

### 5.6 break / continue
```capl
for (i = 0; i < 100; i++)
{
  if (i == 50) break;      // exit loop
  if (i % 2 == 0) continue; // skip even
  write("%d", i);
}
```

---

## 6. Functions

### 6.1 Function Syntax
```capl
returnType FunctionName(type param1, type param2)
{
  // body
  return value;  // if not void
}
```

### 6.2 Void Function
```capl
void PrintStatus(int status)
{
  write("Status: %d", status);
}
```

### 6.3 Return Value Function
```capl
float CalcPhysical(int raw, float factor, float offset)
{
  return (raw * factor) + offset;
}

// Usage
float rpm = CalcPhysical(24000, 0.25, 0.0);
write("RPM: %.1f", rpm);
```

### 6.4 Passing Arrays
Arrays are passed by reference (pointer-like):
```capl
void FillPayload(byte data[], int len, byte value)
{
  int i;
  for (i = 0; i < len; i++)
    data[i] = value;
}

// Usage
byte buf[8];
FillPayload(buf, 8, 0xCC);
```

### 6.5 Passing Structs
Structs are passed by value (copy):
```capl
void PrintDTC(struct DTCRecord rec)
{
  write("DTC: 0x%06X | %s", rec.dtcCode, rec.description);
}
```

### 6.6 Return a String (char pointer)
```capl
char* GetStateName(int state)
{
  switch(state)
  {
    case 0: return "OFF";
    case 1: return "ACTIVE";
    default: return "UNKNOWN";
  }
}
```

### 6.7 Forward Declaration
Not required in CAPL — functions can be defined in any order.

---

## 7. Event Handlers

Event handlers are the **core execution mechanism** of CAPL. They are triggered by bus events, timers, keys, and system events.

### 7.1 Measurement Events
```capl
on start             { /* called when measurement starts */ }
on stopMeasurement   { /* called when measurement stops */ }
on preStart          { /* called just before start */ }
```

### 7.2 CAN Message Events
```capl
// Specific message by ID
on message 0x100 { write("Received 0x100"); }

// Specific message by DBC name
on message EngineData { write("RPM = %.1f", this.EngineSpeed); }

// All messages on channel 1
on message * { write("ID=0x%X", this.id); }

// All messages on specific channel
on message CAN1.* { }

// Message fields available inside handler:
//   this.id         → frame ID
//   this.dlc        → data length
//   this.byte(n)    → nth data byte
//   this.dir        → RX or TX
//   this.channel    → bus channel number
//   this.time       → timestamp (100ns units)
//   this.SignalName → decoded signal value (if DBC loaded)
```

### 7.3 Timer Events
```capl
on timer myTimer    { /* second-resolution */ }
on timer myMsTimer  { /* millisecond-resolution (msTimer) */ }
```

### 7.4 Keyboard Events
```capl
on key 'a'         { write("Key A pressed"); }
on key 's'         { sendStatus(); }
on key F1          { write("F1 pressed"); }
on key ctrlF1      { write("Ctrl+F1"); }
```

### 7.5 Error Frame Events
```capl
on errorFrame
{
  write("Error frame at %.3f s", timeNow() / 100000.0);
  write("Bit position: %d", this.bitPosition);
}
```

### 7.6 Bus State Events
```capl
on busOff    { write("BUS OFF on channel %d", this.channel); }
on errorActive { write("Node returned to error active"); }
```

### 7.7 Environment Variable Events
```capl
on envVar EnvVehicleSpeed
{
  write("Speed changed: %.1f km/h", getValue(this));
}
```

### 7.8 Signal Events
```capl
on signal EngineData::EngineSpeed
{
  write("EngineSpeed changed: %.1f RPM", this.value);
}

on signal change EngineData::GearPosition
{
  write("Gear changed to: %d", this.value);
}
```

### 7.9 Diagnostic Events
```capl
on diagRequest  Engine_ECU.* { }
on diagResponse Engine_ECU.ReadDTCInformation_ReportAllDTCByStatusMask
{
  write("DTC count: %d", this.GetDTCCount());
}
```

---

## 8. Data Structures

### 8.1 One-Dimensional Arrays
```capl
byte  buf[8]     = {0x10, 0x03, 0x00, 0x00, 0xCC, 0xCC, 0xCC, 0xCC};
int   values[5]  = {100, 200, 300, 400, 500};
float temps[4]   = {25.5, 37.0, -10.0, 100.0};
char  label[32]  = "ECU_Node";

// Size at compile time
write("Length: %d", elCount(buf));  // → 8
```

### 8.2 Two-Dimensional Arrays
```capl
byte gMatrix[3][4];

// Fill
int r, c;
for (r = 0; r < 3; r++)
  for (c = 0; c < 4; c++)
    gMatrix[r][c] = (r * 4) + c;
```

### 8.3 Structs (CANoe 10+)
```capl
struct DTCRecord
{
  long  dtcCode;
  byte  statusByte;
  float odometerKm;
  char  description[64];
};

struct DTCRecord gDTC;
gDTC.dtcCode    = 0xC0200;
gDTC.statusByte = 0x09;
gDTC.odometerKm = 12500.0;
strncpy(gDTC.description, "Engine Speed Sensor", 63);

// Array of structs
struct DTCRecord gDTCList[10];
gDTCList[0].dtcCode = 0xC0200;
```

### 8.4 Associative Arrays (CAPL-Unique Key-Value Map)
```capl
// Declaration: type name[key_type]
int   gDTCCount[long];   // key=DTC code, value=occurrence count
float gSignal[char];     // key=signal name, value=float

// Write
gDTCCount[0xC0200] = 3;
gSignal["VehicleSpeed"] = 120.5;

// Read
write("Speed: %.1f", gSignal["VehicleSpeed"]);

// Check if key exists
if (isvalid(gDTCCount[0xC0200]))
  write("Key exists");

// Delete a key
del(gSignal["VehicleSpeed"]);

// Count entries
write("Total: %d", elCount(gSignal));
```

### 8.5 Simulated Enumerations
```capl
const int STATE_OFF     = 0;
const int STATE_STANDBY = 1;
const int STATE_ACTIVE  = 2;
const int STATE_FAULT   = 3;

int gState = STATE_OFF;
```

---

## 9. Built-In Functions Reference

### 9.1 Output & Messaging
| Function | Description |
|---|---|
| `write(fmt, ...)` | Print to Write window |
| `writeEx(channel, severity, fmt, ...)` | Print with severity level |
| `output(msg)` | Transmit CAN message on bus |

### 9.2 Timer Functions
| Function | Description |
|---|---|
| `setTimer(t, ms)` | Start/restart timer (ms for msTimer, s for timer) |
| `cancelTimer(t)` | Cancel a running timer |
| `isTimerActive(t)` | Returns 1 if timer is running |

### 9.3 Time Functions
| Function | Description | Return |
|---|---|---|
| `timeNow()` | Current measurement time | 100ns units |
| `timeNowFloat()` | Current time in seconds | float |
| `timeNowNs()` | Current time in nanoseconds | int64 |

```capl
float seconds = timeNow() / 100000.0;   // 100ns → seconds
write("Time: %.3f s", seconds);
```

### 9.4 Signal & Database Access
| Function | Description |
|---|---|
| `getValue(signal)` | Get current signal value |
| `setValue(signal, val)` | Set a signal value |
| `putValue(envVar, val)` | Write to environment variable |
| `getSignal(name)` | Get signal by name string |

### 9.5 Math Functions
| Function | Description |
|---|---|
| `abs(x)` | Absolute value |
| `sqrt(x)` | Square root |
| `pow(base, exp)` | Power |
| `sin(x)` / `cos(x)` / `tan(x)` | Trig (radians) |
| `log(x)` / `log10(x)` | Natural / base-10 log |
| `floor(x)` / `ceil(x)` | Round down / up |
| `round(x)` | Round to nearest integer |
| `min(a,b)` / `max(a,b)` | Minimum / maximum |
| `random(n)` | Random integer 0 .. n-1 |

### 9.6 String Functions
| Function | Description |
|---|---|
| `strlen(s)` | String length |
| `strcpy(dst, src)` | Copy string |
| `strncpy(dst, src, n)` | Copy max n chars |
| `strcat(dst, src)` | Concatenate |
| `strcmp(a, b)` | Compare (0=equal) |
| `strncmp(a, b, n)` | Compare first n chars |
| `strtol(s, base)` | String to long |
| `atoi(s)` / `atof(s)` | String to int / float |
| `snprintf(dst, n, fmt, ...)` | Formatted string into buffer |
| `str_replace(dst, src, old, new)` | Replace substring |

### 9.7 Bitwise Utility Functions
| Function | Description |
|---|---|
| `getbyte(val, n)` | Extract nth byte |
| `setbyte(val, n, b)` | Set nth byte |
| `getbit(val, n)` | Extract nth bit |
| `setbit(val, n)` | Set nth bit to 1 |
| `clearbit(val, n)` | Clear nth bit to 0 |

```capl
byte high = getbyte(0x1234, 1);   // → 0x12  (byte 1 = high byte)
byte low  = getbyte(0x1234, 0);   // → 0x34  (byte 0 = low byte)

word val  = 0x0000;
setbit(val, 7);   // → 0x0080
clearbit(val, 7); // → 0x0000
```

### 9.8 File I/O
| Function | Description |
|---|---|
| `openFileWrite(path, mode)` | Open file for writing (0=overwrite, 1=append) |
| `openFileRead(path)` | Open file for reading |
| `fileClose(handle)` | Close file |
| `filePutString(str, len, handle)` | Write string to file |
| `fileGetString(buf, len, handle)` | Read line from file |

```capl
dword fh = openFileWrite("C:\\log.csv", 0);
filePutString("Timestamp,ID,Data\n", 20, fh);
fileClose(fh);
```

### 9.9 Array Functions
| Function | Description |
|---|---|
| `elCount(arr)` | Compile-time element count of array |
| `elCount(assocArr)` | Runtime entry count of associative array |
| `isvalid(assocArr[key])` | Check if key exists → 0 or 1 |
| `del(assocArr[key])` | Delete key from associative array |

### 9.10 Diagnostic (UDS) Functions
| Function | Description |
|---|---|
| `DiagSetTarget(name)` | Set active diagnostic ECU |
| `DiagCreateRequest(sid)` | Create UDS request |
| `DiagSendRequest(req)` | Send the request |
| `DiagGetLastError()` | Get last error code |
| `DiagGetPrimitive(req, field)` | Get parameter from request |
| `DiagSetPrimitive(req, field, val)` | Set parameter in request |

### 9.11 Test Functions (vTESTstudio)
| Function | Description |
|---|---|
| `testStep(desc)` | Log a test step |
| `testStepPass(desc)` | Log pass verdict |
| `testStepFail(desc)` | Log fail verdict |
| `testWaitForSignal(sig, val, timeout)` | Block until signal = val |
| `testWaitForMessage(id, timeout)` | Block until message received |
| `testWaitForTimeout(ms)` | Wait for duration |
| `testGetVerdictLastTestCase()` | Get current TC verdict |

---

## 10. Preprocessor Directives

```capl
// Include another CAPL file
includes
{
  #include "helpers.capl"
  #include "constants.capl"
}

// Conditional compilation
#ifdef DEBUG_MODE
  write("Debug mode active");
#endif

// Define a constant
#define MAX_NODES  8
#define VERSION    "2.1.0"
```

---

## 11. Formatting with write()

`write()` uses printf-style format specifiers:

| Specifier | Type | Example Output |
|---|---|---|
| `%d` | int (decimal) | `write("%d", 42)` → `42` |
| `%i` | int (decimal) | Same as `%d` |
| `%u` | unsigned int | `write("%u", 255)` → `255` |
| `%o` | Octal | `write("%o", 8)` → `10` |
| `%x` | Hex lowercase | `write("0x%x", 255)` → `0xff` |
| `%X` | Hex uppercase | `write("0x%X", 255)` → `0xFF` |
| `%02X` | Hex, 2-wide, zero-padded | `write("%02X", 5)` → `05` |
| `%f` | float | `write("%.2f", 3.14)` → `3.14` |
| `%e` | Scientific | `write("%e", 12345.6)` → `1.23e+04` |
| `%s` | String | `write("%s", "hello")` → `hello` |
| `%c` | Character | `write("%c", 'A')` → `A` |
| `%ld` | long | `write("%ld", 99999L)` |

---

## 12. Common Patterns

### 12.1 Periodic Message Transmission
```capl
variables
{
  msTimer txTimer;
  message 0x100 txMsg;
  byte gSeq = 0;
}

on start
{
  txMsg.dlc = 8;
  setTimer(txTimer, 100);   // 10 Hz
}

on timer txTimer
{
  txMsg.byte(0) = gSeq++;
  output(txMsg);
  setTimer(txTimer, 100);
}
```

### 12.2 Message Timeout Watchdog
```capl
variables { msTimer wdTimer; }

on message 0x200
{
  cancelTimer(wdTimer);
  setTimer(wdTimer, 500);   // reset 500ms timeout
}

on timer wdTimer
{
  write("!! Message 0x200 timeout!");
}

on start { setTimer(wdTimer, 500); }
```

### 12.3 Signal Range Validation
```capl
on message EngineData
{
  float rpm = this.EngineSpeed;
  if (rpm < 0.0 || rpm > 8000.0)
    write("!! EngineSpeed out of range: %.1f", rpm);
}
```

### 12.4 State Machine
```capl
variables
{
  const int S_IDLE    = 0;
  const int S_ACTIVE  = 1;
  const int S_FAULT   = 2;
  int gState = 0;
}

void GoTo(int newState)
{
  write("State %d → %d", gState, newState);
  gState = newState;
}

on message 0x100
{
  if (this.byte(0) == 0x01) GoTo(S_ACTIVE);
  if (this.byte(0) == 0xFF) GoTo(S_FAULT);
}
```

### 12.5 Byte Extraction (Signal Decoding)
```capl
on message 0x100
{
  // Intel byte order, factor=0.25, offset=0
  word raw  = this.byte(0) | (this.byte(1) << 8);
  float rpm = raw * 0.25;
  write("RPM: %.1f", rpm);

  // Motorola byte order
  word rawM = (this.byte(0) << 8) | this.byte(1);

  // Extract bits [4..7] from byte 2
  byte nibble = (this.byte(2) >> 4) & 0x0F;
}
```

---

## 13. CAPL vs C – Key Differences

| Aspect | CAPL | C |
|---|---|---|
| Compiled? | Yes (inside CANoe) | Yes (standalone) |
| Main entry point | Event handlers (`on start`, etc.) | `main()` function |
| Memory allocation | Static only (no malloc/free) | Static + dynamic |
| Pointers | ❌ Not supported | ✅ Full support |
| Structs | ✅ (CANoe 10+) | ✅ |
| Unions | ❌ Not supported | ✅ |
| Typedefs | ❌ Limited | ✅ |
| Bus access | Native (`output()`, `on message`) | Via library |
| Prototypes | Not required | Required |
| Header files | `.capl` includes only | `.h` files |
| Associative arrays | ✅ Built-in | ❌ (need library) |
| Environment vars | ✅ Built-in | ❌ |
| Test functions | ✅ Built-in (vTESTstudio) | ❌ |

---

## 14. CAPL Execution Model

CAPL runs in an **event-driven** model, not a sequential top-to-bottom program:

```
CANoe Measurement Running
         │
         ├── Bus Event (CAN message)    → on message 0x100 { }
         ├── Timer fires               → on timer myTimer { }
         ├── Key pressed               → on key 'a' { }
         ├── Signal changes            → on signal ... { }
         ├── Error frame detected      → on errorFrame { }
         └── Measurement stops         → on stopMeasurement { }
```

**Important rules:**
1. CAPL is **single-threaded** — events are processed one at a time
2. Event handlers should be **short** — long blocking code delays other events
3. `testWaitFor*` functions block only in **test modules**, not in simulation nodes
4. Global variables are **shared** between all handlers — be careful with state

---

## 15. Quick Reference Card

```
DATA TYPES          SPECIAL TYPES        EVENT HANDLERS
───────────         ─────────────        ──────────────────
byte   (1 byte)     msTimer              on start
word   (2 byte)     timer                on stopMeasurement
dword  (4 byte)     message              on message <id>
int    (4 byte)     struct (CANoe 10+)   on message *
float  (4 byte)                          on timer <name>
double (8 byte)     DATA STRUCTURES      on key '<char>'
char   (1 byte)     ─────────────────    on errorFrame
char[] (string)     Arrays (1D/2D)       on busOff
int64  (8 byte)     Structs              on envVar <name>
                    Assoc Arrays         on signal <name>
                    const int (enum)

KEY FUNCTIONS
─────────────────────────────────────────────────────
output(msg)              → send CAN message
setTimer(t, val)         → start timer
cancelTimer(t)           → stop timer
timeNow()                → current time (100ns units)
write(fmt, ...)          → print to Write window
strlen/strcpy/strcat/strcmp/snprintf → string ops
abs/sqrt/pow/sin/cos     → math
elCount(arr)             → array element count
isvalid(map[key])        → assoc array key check
del(map[key])            → remove assoc array key
getValue / setValue      → signal read/write
testStepPass/Fail        → test verdict
```
