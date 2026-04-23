cmake_minimum_required(VERSION 3.16)
project(AutomotiveGTestExamples CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── GoogleTest via FetchContent ──────────────────────────────────────────────
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()

# ── Production source library ────────────────────────────────────────────────
add_library(automotive_lib
    src/bms_controller.cpp
    src/uds_handler.cpp
    src/can_packer.cpp
    src/pedal_safety.cpp
    src/sensor_fusion.cpp
    src/safety_monitor.cpp
    src/doip_decoder.cpp
    src/gear_recommender.cpp
)
target_include_directories(automotive_lib PUBLIC include)

# ── Unit test executable ─────────────────────────────────────────────────────
add_executable(automotive_tests
    tests/test_bms_controller.cpp
    tests/test_uds_handler.cpp
    tests/test_can_packer.cpp
    tests/test_pedal_safety.cpp
    tests/test_sensor_fusion.cpp
    tests/test_safety_monitor.cpp
    tests/test_doip_decoder.cpp
    tests/test_gear_recommender.cpp
    tests/test_main.cpp
)
target_include_directories(automotive_tests PRIVATE include tests/mocks)
target_link_libraries(automotive_tests
    PRIVATE
        automotive_lib
        GTest::gtest
        GTest::gmock
        GTest::gtest_main
)

# ── Optional AddressSanitizer build ─────────────────────────────────────────
option(ENABLE_ASAN "Build with AddressSanitizer" OFF)
if(ENABLE_ASAN)
    target_compile_options(automotive_tests PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(automotive_tests PRIVATE -fsanitize=address)
endif()

# ── Optional ThreadSanitizer build ──────────────────────────────────────────
option(ENABLE_TSAN "Build with ThreadSanitizer" OFF)
if(ENABLE_TSAN)
    target_compile_options(automotive_tests PRIVATE -fsanitize=thread)
    target_link_options(automotive_tests PRIVATE -fsanitize=thread)
endif()

include(GoogleTest)
gtest_discover_tests(automotive_tests)
