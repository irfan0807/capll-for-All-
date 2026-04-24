cmake_minimum_required(VERSION 3.16)
project(adas_ecu_c C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# ── Options ────────────────────────────────────────────────────────────────────
option(BUILD_SIMULATION "Build for host simulation (Linux/macOS)" ON)
option(EMBEDDED_TARGET  "Cross-compile for ARM Cortex-M4"         OFF)
option(BUILD_TESTS      "Build unit tests with Unity"              OFF)

# ── Version ────────────────────────────────────────────────────────────────────
set(ADAS_VER_MAJOR 1)
set(ADAS_VER_MINOR 0)
set(ADAS_VER_PATCH 0)

# ── Cross-compile toolchain ────────────────────────────────────────────────────
if(EMBEDDED_TARGET)
    set(CMAKE_C_COMPILER arm-none-eabi-gcc)
    set(CMAKE_AR         arm-none-eabi-ar)
    set(CMAKE_OBJCOPY    arm-none-eabi-objcopy)
    set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")
    set(CMAKE_C_FLAGS "${MCU_FLAGS} -Os -ffunction-sections -fdata-sections -fno-common")
    set(CMAKE_EXE_LINKER_FLAGS "${MCU_FLAGS} -Wl,--gc-sections -nostartfiles")
endif()

# ── Sources ────────────────────────────────────────────────────────────────────
set(SOURCES
    src/hal/hal_timer.c
    src/drivers/can_driver.c
    src/drivers/can_messages.c
    src/rtos/scheduler.c
    src/features/sensor_fusion.c
    src/features/acc_controller.c
    src/features/lka_controller.c
    src/features/bsd_controller.c
    src/features/parking_controller.c
    src/features/hha_controller.c
    src/diagnostics/dtc_manager.c
    src/main.c
)

add_executable(adas_ecu_sim ${SOURCES})

target_include_directories(adas_ecu_sim PRIVATE include)

target_compile_definitions(adas_ecu_sim PRIVATE
    ADAS_VER_MAJOR=${ADAS_VER_MAJOR}
    ADAS_VER_MINOR=${ADAS_VER_MINOR}
    ADAS_VER_PATCH=${ADAS_VER_PATCH}
)

if(BUILD_SIMULATION)
    target_compile_definitions(adas_ecu_sim PRIVATE SIMULATION_BUILD=1)
endif()

# ── Warning flags ──────────────────────────────────────────────────────────────
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(adas_ecu_sim PRIVATE
        -Wall -Wextra -Wpedantic
        -Wno-unused-parameter
    )
endif()

# ── Tests (Unity framework) ───────────────────────────────────────────────────
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
