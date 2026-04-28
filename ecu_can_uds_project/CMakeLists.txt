cmake_minimum_required(VERSION 3.14)
project(ECU_CAN_UDS_Simulation
    VERSION 1.0.0
    DESCRIPTION "Automotive ECU CAN Bus + UDS Diagnostic Simulation"
    LANGUAGES CXX
)

# ─── Compiler Settings ───────────────────────────────────────────────────────
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Automotive-style flags: no exceptions, no RTTI, strict warnings
set(AUTOMOTIVE_FLAGS
    -Wall
    -Wextra
    -Wpedantic
    -Wshadow
    -Wno-unused-parameter
    -fno-exceptions
    -fno-rtti
)

# ─── Source Groups ───────────────────────────────────────────────────────────

# CAN layer
set(CAN_SOURCES
    src/can/can_frame.cpp
    src/can/can_bus.cpp
)

# UDS layer
set(UDS_SOURCES
    src/uds/uds_server.cpp
)

# ECU core layer
set(ECU_SOURCES
    src/ecu/dtc_manager.cpp
    src/ecu/ecu_core.cpp
)

# ─── Static Library: automotive_ecu ─────────────────────────────────────────

add_library(automotive_ecu STATIC
    ${CAN_SOURCES}
    ${UDS_SOURCES}
    ${ECU_SOURCES}
)

target_include_directories(automotive_ecu
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(automotive_ecu PRIVATE ${AUTOMOTIVE_FLAGS})

# ─── Executable: ecu_simulation ─────────────────────────────────────────────

add_executable(ecu_simulation
    src/main.cpp
)

target_link_libraries(ecu_simulation PRIVATE automotive_ecu)
target_compile_options(ecu_simulation PRIVATE ${AUTOMOTIVE_FLAGS})

# ─── Test Executables ────────────────────────────────────────────────────────

add_executable(test_can_bus
    tests/test_can_bus.cpp
)
target_link_libraries(test_can_bus PRIVATE automotive_ecu)
target_compile_options(test_can_bus PRIVATE ${AUTOMOTIVE_FLAGS})

add_executable(test_dtc_manager
    tests/test_dtc_manager.cpp
)
target_link_libraries(test_dtc_manager PRIVATE automotive_ecu)
target_compile_options(test_dtc_manager PRIVATE ${AUTOMOTIVE_FLAGS})

# ─── CTest Integration ───────────────────────────────────────────────────────
enable_testing()

add_test(NAME CANBusTests   COMMAND test_can_bus)
add_test(NAME DTCManagerTests COMMAND test_dtc_manager)

# ─── Install ─────────────────────────────────────────────────────────────────
install(TARGETS ecu_simulation
    RUNTIME DESTINATION bin
)

install(TARGETS automotive_ecu
    ARCHIVE DESTINATION lib
)

install(DIRECTORY include/
    DESTINATION include
)

# ─── Print Summary ───────────────────────────────────────────────────────────
message(STATUS "")
message(STATUS "══════════════════════════════════════════════")
message(STATUS "  ECU CAN/UDS Simulation – Build Summary")
message(STATUS "══════════════════════════════════════════════")
message(STATUS "  C++ Standard  : ${CMAKE_CXX_STANDARD}")
message(STATUS "  Build type    : ${CMAKE_BUILD_TYPE}")
message(STATUS "  Compiler      : ${CMAKE_CXX_COMPILER_ID}")
message(STATUS "  Install prefix: ${CMAKE_INSTALL_PREFIX}")
message(STATUS "══════════════════════════════════════════════")
message(STATUS "")
message(STATUS "  Build targets:")
message(STATUS "    ecu_simulation   – Full ECU demo")
message(STATUS "    test_can_bus     – CAN layer unit tests")
message(STATUS "    test_dtc_manager – DTC + ECU core tests")
message(STATUS "")
message(STATUS "  Run simulation:")
message(STATUS "    cmake --build . && ./ecu_simulation")
message(STATUS "")
message(STATUS "  Run all tests:")
message(STATUS "    cmake --build . && ctest --output-on-failure")
message(STATUS "══════════════════════════════════════════════")
