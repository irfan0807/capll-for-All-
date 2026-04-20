# C++ Memory Management & RTOS for Automotive

> **Coverage:** Stack vs Heap, Static Memory, RTOS Tasks, Queues, Mutexes, Timers
> **Context:** AUTOSAR Classic OS, FreeRTOS, QNX, ISO 26262 ASIL constraints

---

## 1. Memory Layout in Embedded Systems

```
+------------------------+  High Address
|     Stack (grows ↓)    |  Per-task in RTOS
+------------------------+
|    Heap (BANNED in     |  new/delete = MISRA violation
|    AUTOSAR Classic)    |
+------------------------+
|     BSS Segment        |  Zero-initialized globals/statics
|  (uint32_t g_tick)     |
+------------------------+
|     Data Segment       |  Initialized globals
|  (uint8_t g_state = 1) |
+------------------------+
|     Text Segment       |  Code (Flash)
|  (functions, consts)   |
+------------------------+  Low Address (0x08000000 typical STM32)
```

### Stack vs Heap Rules (AUTOSAR Classic)

| Memory | Use | AUTOSAR Classic | AUTOSAR Adaptive |
|---|---|---|---|
| Stack | Local variables, function frames | Allowed | Allowed |
| Static | Global/module-level data | Required | Allowed |
| Heap | Dynamic allocation | BANNED | Restricted |
| Object pools | Fixed-size allocator | Allowed | Recommended |

---

## 2. Static Memory Pools — Replacing `new`/`delete`

```cpp
// Fixed-size object pool — no dynamic allocation
template<typename T, uint8_t CAPACITY>
class ObjectPool {
public:
    T* allocate(void) {
        for (uint8_t i = 0U; i < CAPACITY; ++i) {
            if (!used_[i]) {
                used_[i] = true;
                return reinterpret_cast<T*>(&storage_[i]);
            }
        }
        return nullptr;  // Pool exhausted
    }

    void deallocate(T* ptr) {
        for (uint8_t i = 0U; i < CAPACITY; ++i) {
            if (reinterpret_cast<T*>(&storage_[i]) == ptr) {
                ptr->~T();       // Explicit destructor
                used_[i] = false;
                return;
            }
        }
    }

private:
    alignas(T) uint8_t storage_[CAPACITY][sizeof(T)];
    bool used_[CAPACITY] = {false};
};

// Usage — CanFrame pool instead of dynamic allocation
ObjectPool<CanFrame, 32U> can_pool;

CanFrame* frame = can_pool.allocate();
if (frame != nullptr) {
    frame->id  = 0x3A1U;
    frame->dlc = 8U;
    can_bus.transmit(*frame);
    can_pool.deallocate(frame);
}
```

---

## 3. Stack Usage Analysis

```cpp
// MISRA / Safety: Avoid large stack allocations inside functions
// BAD — 1KB on stack inside ISR
void process_data_bad(void) {
    uint8_t temp_buffer[1024U];   // Stack allocated — dangerous in RTOS
    // ...
}

// GOOD — Static or module-level buffer
static uint8_t s_process_buffer[1024U];   // Zero-cost at runtime, in BSS

void process_data_good(void) {
    // Use s_process_buffer — no stack growth
}

// Stack usage calculation:
// Total stack  = local_vars + function_call_overhead + ISR_push_registers
// Stack monitor pattern (FreeRTOS)
void check_stack_watermark(void) {
    UBaseType_t hwm = uxTaskGetStackHighWaterMark(nullptr);
    if (hwm < 64U) {
        // Stack nearly exhausted — report fault
        FaultManager::report(DTC_STACK_OVERFLOW_WARNING, 2U);
    }
}
```

---

## 4. RTOS Fundamentals (FreeRTOS / AUTOSAR OS)

### Task Creation

```cpp
// FreeRTOS task
void bms_monitor_task(void* pvParameters);
void can_receive_task(void* pvParameters);
void diagnostic_task(void* pvParameters);

// Stack sizes in words (4 bytes each on ARM Cortex-M)
constexpr uint16_t BMS_TASK_STACK_WORDS = 512U;  // 2KB
constexpr uint16_t CAN_TASK_STACK_WORDS = 256U;  // 1KB
constexpr uint16_t DIAG_TASK_STACK_WORDS = 256U; // 1KB

// Task handles
static TaskHandle_t h_bms_task  = nullptr;
static TaskHandle_t h_can_task  = nullptr;
static TaskHandle_t h_diag_task = nullptr;

void create_rtos_tasks(void) {
    // Priority: Higher number = Higher priority on FreeRTOS
    xTaskCreate(bms_monitor_task, "BMS_MON",  BMS_TASK_STACK_WORDS,
                nullptr, 3U, &h_bms_task);

    xTaskCreate(can_receive_task, "CAN_RX",   CAN_TASK_STACK_WORDS,
                nullptr, 4U, &h_can_task);   // Highest priority

    xTaskCreate(diagnostic_task,  "DIAG",     DIAG_TASK_STACK_WORDS,
                nullptr, 2U, &h_diag_task);

    vTaskStartScheduler();
}

// Task implementations
void bms_monitor_task(void* /*pvParameters*/) {
    TickType_t last_wake = xTaskGetTickCount();
    for (;;) {
        bms_monitor.cyclic_10ms();
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(10U));  // Precise 10ms period
    }
}

void can_receive_task(void* /*pvParameters*/) {
    CanFrame frame;
    for (;;) {
        if (xQueueReceive(can_rx_queue, &frame, portMAX_DELAY) == pdTRUE) {
            can_dispatcher.dispatch(frame);
        }
    }
}
```

---

## 5. Queues — CAN Rx/Tx Buffering

```cpp
// Create queue for CAN frames
static QueueHandle_t can_rx_queue = nullptr;
static QueueHandle_t can_tx_queue = nullptr;

constexpr uint8_t CAN_QUEUE_DEPTH = 16U;

void init_queues(void) {
    can_rx_queue = xQueueCreate(CAN_QUEUE_DEPTH, sizeof(CanFrame));
    can_tx_queue = xQueueCreate(CAN_QUEUE_DEPTH, sizeof(CanFrame));
}

// ISR — enqueue received frame
extern "C" void CAN1_RX0_IRQHandler(void) {
    CanFrame frame;
    frame.id  = CAN1->sFIFOMailBox[0].RIR >> 21U;
    frame.dlc = CAN1->sFIFOMailBox[0].RDTR & 0x0FU;
    // ... copy data bytes

    CAN1->RF0R |= 0x20U;  // Release FIFO

    BaseType_t higher_prio_woken = pdFALSE;
    xQueueSendFromISR(can_rx_queue, &frame, &higher_prio_woken);
    portYIELD_FROM_ISR(higher_prio_woken);
}

// Worker task — dequeue and process
void can_receive_task(void* /*pvParameters*/) {
    CanFrame frame;
    for (;;) {
        if (xQueueReceive(can_rx_queue, &frame, pdMS_TO_TICKS(100U)) == pdTRUE) {
            dispatch_can_frame(frame);
        } else {
            // Timeout — check for bus-off condition
            if (is_can_bus_off()) {
                recover_can_bus();
            }
        }
    }
}
```

---

## 6. Mutexes & Critical Sections

```cpp
// Mutex — protect shared module data
static SemaphoreHandle_t bms_data_mutex = nullptr;

void init_mutex(void) {
    bms_data_mutex = xSemaphoreCreateMutex();
}

// RAII wrapper for RTOS mutex
class RtosMutexGuard {
public:
    explicit RtosMutexGuard(SemaphoreHandle_t& mtx, TickType_t timeout = portMAX_DELAY)
        : mutex_(mtx) {
        acquired_ = (xSemaphoreTake(mutex_, timeout) == pdTRUE);
    }
    ~RtosMutexGuard(void) {
        if (acquired_) xSemaphoreGive(mutex_);
    }
    bool is_acquired(void) const { return acquired_; }

private:
    SemaphoreHandle_t& mutex_;
    bool acquired_;
};

// Usage
float get_pack_voltage_thread_safe(void) {
    RtosMutexGuard guard(bms_data_mutex, pdMS_TO_TICKS(5U));
    if (!guard.is_acquired()) return -1.0f;
    return pack_voltage_v;  // Protected access
}

// Critical section (disable interrupts) — use for very short operations
static float s_cell_voltage_cache[96U];

void update_voltage_cache(uint8_t cell_id, float voltage) {
    taskENTER_CRITICAL();
    s_cell_voltage_cache[cell_id] = voltage;
    taskEXIT_CRITICAL();
}
```

---

## 7. Semaphores — Event Signaling

```cpp
// Binary semaphore — signal between ISR and task
static SemaphoreHandle_t h_tx_complete_sem = nullptr;

void init_semaphores(void) {
    h_tx_complete_sem = xSemaphoreCreateBinary();
}

// ISR signals task when CAN TX complete
extern "C" void CAN1_TX_IRQHandler(void) {
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(h_tx_complete_sem, &woken);
    portYIELD_FROM_ISR(woken);
}

// Task waits for TX complete before sending next frame
bool can_transmit_blocking(const CanFrame& frame, uint32_t timeout_ms) {
    load_hw_mailbox(frame);
    return xSemaphoreTake(h_tx_complete_sem, pdMS_TO_TICKS(timeout_ms)) == pdTRUE;
}

// Counting semaphore — track available CAN TX mailboxes (0–3)
static SemaphoreHandle_t h_mailbox_sem = nullptr;

void init_mailbox_semaphore(void) {
    h_mailbox_sem = xSemaphoreCreateCounting(3U, 3U);  // Max 3, initially 3
}
```

---

## 8. Software Timers (RTOS)

```cpp
// FreeRTOS software timer for periodic UDS tester present
static TimerHandle_t h_tester_present_timer = nullptr;

void tester_present_callback(TimerHandle_t /*timer*/) {
    static const uint8_t tp_msg[] = {0x3EU, 0x00U};
    can_transmit(UDS_FUNC_ID, tp_msg, sizeof(tp_msg));
}

void start_tester_present(void) {
    if (h_tester_present_timer == nullptr) {
        h_tester_present_timer = xTimerCreate(
            "TesterPresent",
            pdMS_TO_TICKS(2000U),   // 2s period
            pdTRUE,                  // Auto-reload
            nullptr,
            tester_present_callback
        );
    }
    xTimerStart(h_tester_present_timer, 0U);
}

void stop_tester_present(void) {
    if (h_tester_present_timer != nullptr) {
        xTimerStop(h_tester_present_timer, 0U);
    }
}
```

---

## 9. Memory Barriers & Cache — ARM Cortex-A (AUTOSAR Adaptive)

```cpp
// Data Memory Barrier — ensure writes complete before subsequent memory access
#include <atomic>

// Preferred in C++11: atomic types
std::atomic<bool>    g_fault_active{false};
std::atomic<uint32_t> g_can_rx_count{0U};

// ISR
extern "C" void CAN_IRQHandler(void) {
    g_can_rx_count.fetch_add(1U, std::memory_order_relaxed);
    g_fault_active.store(true, std::memory_order_release);
}

// Main task
void main_cycle(void) {
    if (g_fault_active.load(std::memory_order_acquire)) {
        g_fault_active.store(false, std::memory_order_release);
        handle_fault();
    }
}

// ARM DSB/DMB intrinsics (when not using std::atomic)
inline void memory_barrier(void) {
    __asm volatile("dmb sy" ::: "memory");
}
inline void data_sync_barrier(void) {
    __asm volatile("dsb sy" ::: "memory");
}
```

---

## 10. Placement New — AUTOSAR Adaptive (No Dynamic Allocation)

```cpp
// Pre-allocate storage, construct object in-place
alignas(BmsMonitor) static uint8_t bms_storage[sizeof(BmsMonitor)];
static BmsMonitor* p_bms = nullptr;

void system_init(void) {
    // Construct BmsMonitor in pre-allocated storage
    p_bms = new(bms_storage) BmsMonitor(can_drv, dtc_mgr);
    p_bms->init();
}

void system_shutdown(void) {
    if (p_bms != nullptr) {
        p_bms->~BmsMonitor();   // Explicit destructor call
        p_bms = nullptr;
    }
}
```

---

## 11. Stack Overflow Detection

```cpp
// FreeRTOS stack overflow hook
extern "C" void vApplicationStackOverflowHook(TaskHandle_t task, char* task_name) {
    // Safety reaction — enter safe state
    open_all_contactors_emergency();
    inhibit_drive_torque();
    log_critical_fault(DTC_STACK_OVERFLOW, task_name);

    // Trigger watchdog reset
    for (;;) {
        // Let watchdog expire
    }
}

// Watchdog management
class WatchdogManager {
public:
    void init(uint16_t timeout_ms) {
        IWDG->KR  = 0xCCCCU;    // Enable IWDG
        IWDG->KR  = 0x5555U;    // Unlock
        IWDG->PR  = 4U;          // Prescaler /64 → ~0.5ms resolution
        IWDG->RLR = timeout_ms * 2U;  // Reload value
        IWDG->KR  = 0xAAAAU;    // Start
    }

    void refresh(void) {
        IWDG->KR = 0xAAAAU;     // "Kick" the dog
    }
};
```

---

## 12. AUTOSAR Memory Sections

```cpp
// AUTOSAR memory section macros (from AUTOSAR Schema)
// Mapped to linker script sections

#define START_SEC_CODE
#include "MemMap.h"

void Bms_MainFunction(void) {
    // Periodic cyclic function — mapped to Flash
}

#define STOP_SEC_CODE
#include "MemMap.h"

// Calibration data — mapped to calibratable FLASH section
#define START_SEC_CONST_16BIT
#include "MemMap.h"

static const uint16_t Bms_OV2_Threshold_mV = 4250U;
static const uint16_t Bms_UV2_Threshold_mV = 2800U;

#define STOP_SEC_CONST_16BIT
#include "MemMap.h"

// NVM data — mapped to EEPROM-emulated section
#define START_SEC_VAR_NOINIT_32BIT
#include "MemMap.h"

static uint32_t Bms_CycleCount;
static uint32_t Bms_TotalChargeAh;

#define STOP_SEC_VAR_NOINIT_32BIT
#include "MemMap.h"
```

---

*File: 03_cpp_memory_rtos.md | cpp_automotive study series*
