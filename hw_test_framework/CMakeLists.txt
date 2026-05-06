cmake_minimum_required(VERSION 3.18)
project(hw_test_framework VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Options ───────────────────────────────────────────────────────────────────
option(BUILD_PYTHON_BINDINGS "Build pybind11 Python extension"       ON)
option(BUILD_TESTS           "Build C++ unit tests via CTest"         ON)
option(USE_SOCKETCAN         "Use SocketCAN backend (Linux default)"  ON)
option(USE_VECTOR_XL         "Use Vector XL Driver backend"          OFF)

# ── Core C++ library ──────────────────────────────────────────────────────────
add_library(hw_adapter_core STATIC
    cpp/src/can_adapter.cpp
    cpp/src/uds_adapter.cpp
)

target_include_directories(hw_adapter_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/cpp/include>
        $<INSTALL_INTERFACE:include>
)

if(USE_SOCKETCAN)
    target_compile_definitions(hw_adapter_core PUBLIC USE_SOCKETCAN)
endif()

if(USE_VECTOR_XL)
    target_compile_definitions(hw_adapter_core PUBLIC USE_VECTOR_XL)
    # Find Vector XL library — adjust path to your installation
    find_library(XL_LIB vxlapi HINTS "$ENV{VECTOR_XL_DIR}/bin")
    if(XL_LIB)
        target_link_libraries(hw_adapter_core PUBLIC ${XL_LIB})
    else()
        message(WARNING "Vector XL library not found — stub will be used")
    endif()
endif()

target_compile_options(hw_adapter_core PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
)

# ── pybind11 Python bindings ──────────────────────────────────────────────────
if(BUILD_PYTHON_BINDINGS)
    find_package(pybind11 CONFIG REQUIRED)
    pybind11_add_module(hw_adapter_cpp bindings/bindings.cpp)
    target_link_libraries(hw_adapter_cpp PRIVATE hw_adapter_core)
    set_target_properties(hw_adapter_cpp PROPERTIES
        CXX_VISIBILITY_PRESET hidden
        INTERPROCEDURAL_OPTIMIZATION OFF
    )
endif()

# ── Tests ─────────────────────────────────────────────────────────────────────
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(cpp/tests EXCLUDE_FROM_ALL)
endif()

# ── Install ───────────────────────────────────────────────────────────────────
install(TARGETS hw_adapter_core
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)
install(DIRECTORY cpp/include/ DESTINATION include)

if(BUILD_PYTHON_BINDINGS)
    install(TARGETS hw_adapter_cpp
        LIBRARY DESTINATION ${Python_SITEARCH}
    )
endif()
