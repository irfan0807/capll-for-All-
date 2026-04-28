cmake_minimum_required(VERSION 3.14)
project(adas_l4 VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Compiler flags ──────────────────────────────────────────────────────────
if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang|AppleClang")
    add_compile_options(
        -Wall -Wextra -Wpedantic
        -Wshadow -Wcast-align
        -Wno-unused-parameter
    )
endif()

# ── Source groups ────────────────────────────────────────────────────────────
set(SENSOR_SRCS
    src/sensors/lidar_sensor.cpp
    src/sensors/radar_sensor.cpp
    src/sensors/camera_sensor.cpp
    src/sensors/imu_sensor.cpp
)

set(PERCEPTION_SRCS
    src/perception/sensor_fusion.cpp
    src/perception/lane_detector.cpp
)

set(PLANNING_SRCS
    src/planning/path_planner.cpp
    src/planning/trajectory_generator.cpp
)

set(CONTROL_SRCS
    src/control/pid_controller.cpp
    src/control/vehicle_controller.cpp
)

set(SAFETY_SRCS
    src/safety/adas_fsm.cpp
    src/safety/safety_monitor.cpp
    src/safety/emergency_handler.cpp
)

set(CAN_SRCS
    src/can/adas_can_bus.cpp
)

# ── Static library ────────────────────────────────────────────────────────────
add_library(adas_l4_lib STATIC
    ${SENSOR_SRCS}
    ${PERCEPTION_SRCS}
    ${PLANNING_SRCS}
    ${CONTROL_SRCS}
    ${SAFETY_SRCS}
    ${CAN_SRCS}
)

target_include_directories(adas_l4_lib PUBLIC
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}           # for src/main.cpp include paths
)

# ── Simulation executable ─────────────────────────────────────────────────────
add_executable(adas_l4_sim src/main.cpp)
target_include_directories(adas_l4_sim PRIVATE
    ${CMAKE_SOURCE_DIR}
)
target_link_libraries(adas_l4_sim PRIVATE adas_l4_lib)

# ── Unit tests ────────────────────────────────────────────────────────────────
enable_testing()

# Test: sensors
add_executable(test_sensors tests/test_sensors.cpp)
target_include_directories(test_sensors PRIVATE ${CMAKE_SOURCE_DIR})
target_link_libraries(test_sensors PRIVATE adas_l4_lib)
add_test(NAME test_sensors COMMAND test_sensors)

# Test: perception, planning, control, safety
add_executable(test_perception tests/test_perception.cpp)
target_include_directories(test_perception PRIVATE ${CMAKE_SOURCE_DIR})
target_link_libraries(test_perception PRIVATE adas_l4_lib)
add_test(NAME test_perception COMMAND test_perception)

# ── Summary ───────────────────────────────────────────────────────────────────
message(STATUS "ADAS L4 Project Configured")
message(STATUS "  Static library : adas_l4_lib")
message(STATUS "  Simulation     : adas_l4_sim")
message(STATUS "  Tests          : test_sensors, test_perception")
