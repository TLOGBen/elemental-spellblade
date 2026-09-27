cmake_minimum_required(VERSION 3.24)
project(ElementsSpellblade VERSION 0.27.1 LANGUAGES CXX)
if(NOT MSVC OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "MSVC x64 is required")
endif()
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
set(SPDLOG_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(SPDLOG_BUILD_EXAMPLE OFF CACHE BOOL "" FORCE)
set(SPDLOG_FMT_EXTERNAL OFF CACHE BOOL "" FORCE)
set(SPDLOG_INSTALL ON CACHE BOOL "" FORCE)
add_subdirectory(deps/spdlog EXCLUDE_FROM_ALL)
set(spdlog_DIR "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
set(RAPIDCSV_INCLUDE_DIRS "${CMAKE_CURRENT_SOURCE_DIR}/deps/rapidcsv/src" CACHE PATH "" FORCE)
set(ENABLE_SKYRIM_SE ON CACHE BOOL "" FORCE)
set(ENABLE_SKYRIM_AE OFF CACHE BOOL "" FORCE)
set(ENABLE_SKYRIM_VR OFF CACHE BOOL "" FORCE)
set(SKSE_SUPPORT_XBYAK OFF CACHE BOOL "" FORCE)
set(BUILD_TESTS OFF CACHE BOOL "" FORCE)
add_subdirectory(deps/CommonLibSSE-NG EXCLUDE_FROM_ALL)
add_library(ElementsSpellblade SHARED src/Plugin.cpp)
target_include_directories(ElementsSpellblade PRIVATE include deps/json/single_include)
target_link_libraries(ElementsSpellblade PRIVATE CommonLibSSE::CommonLibSSE bcrypt version)
target_compile_options(ElementsSpellblade PRIVATE /W4 /we4717 /EHsc /utf-8)
target_precompile_headers(ElementsSpellblade PRIVATE <RE/Skyrim.h> <SKSE/SKSE.h>)
enable_testing()
add_executable(hit_pipeline_test tests/hit_pipeline_test.cpp)
target_include_directories(hit_pipeline_test PRIVATE include deps/json/single_include)
target_compile_options(hit_pipeline_test PRIVATE /W4 /WX /EHsc /utf-8)
add_test(NAME hit_pipeline COMMAND hit_pipeline_test "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix20-magnitude-table.json" "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix20-wiring.json")
# Round 22 (N3): the status layer against build/fix22_reference.py and the generator's record identities.
add_executable(status_test tests/status_test.cpp)
target_include_directories(status_test PRIVATE include deps/json/single_include)
target_compile_options(status_test PRIVATE /W4 /WX /EHsc /utf-8)
add_test(NAME status_layer COMMAND status_test "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix22-status-table.json" "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix22-wiring.json")
# Round 22 review fix 6: the engine side (StatusEngine.h) against a fake effect list and caster.
add_executable(engine_test tests/engine_test.cpp)
target_include_directories(engine_test PRIVATE include deps/json/single_include)
target_compile_options(engine_test PRIVATE /W4 /WX /EHsc /utf-8)
add_test(NAME status_engine COMMAND engine_test)
# Round 23 (N4): your resources and the hits you take (SelfLayer.h, Hurt.h) against build/fix23_reference.py and the
# generator's round-23 record identities.
add_executable(self_test tests/self_test.cpp)
target_include_directories(self_test PRIVATE include deps/json/single_include)
target_compile_options(self_test PRIVATE /W4 /WX /EHsc /utf-8)
add_test(NAME self_layer COMMAND self_test "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix23-self-table.json" "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix23-wiring.json")
# Round 24 (N5): the reaction bodies, the fusion, the death handling and the range scans (Reactions.h) against
# build/fix24_reference.py and the generator's round-24 record identities.
add_executable(reaction_test tests/reaction_test.cpp)
target_include_directories(reaction_test PRIVATE include deps/json/single_include)
target_compile_options(reaction_test PRIVATE /W4 /WX /EHsc /utf-8 /bigobj)
add_test(NAME reaction_bodies COMMAND reaction_test "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix24-body-table.json" "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix24-wiring.json")
# Round 25 (N6): the per-second work, the domains' DLL halves and the hotkey decisions (Timer.h) against
# build/fix25_reference.py and the generator's round-25 record identities.
add_executable(timer_test tests/timer_test.cpp)
target_include_directories(timer_test PRIVATE include deps/json/single_include)
target_compile_options(timer_test PRIVATE /W4 /WX /EHsc /utf-8 /bigobj)
add_test(NAME timer_domains_hotkeys COMMAND timer_test "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix25-timer-table.json" "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix25-wiring.json")
# Round 25 hotfix: the DLL's data-load resolution (Load.h, what Plugin.cpp LoadManifest runs) on the written ESP and
# manifest. Its input is read back from the ESP build_v03.py writes, so build/fix25_verify.py runs it (not CTest).
add_executable(load_test tests/load_test.cpp)
target_include_directories(load_test PRIVATE include deps/json/single_include)
target_compile_options(load_test PRIVATE /W4 /WX /EHsc /utf-8 /bigobj)
# Round 26: the probe log (Trace.h) -- the line formats against build/fix26-trace-format.json (the patterns
# build/probe-judge.py reads with), the buffer, the recording random source, the engine hooks; it writes the offline
# sample log build/probe-judge.py is tested on.
add_executable(trace_test tests/trace_test.cpp)
target_include_directories(trace_test PRIVATE include deps/json/single_include)
target_compile_options(trace_test PRIVATE /W4 /WX /EHsc /utf-8 /bigobj)
add_test(NAME probe_log COMMAND trace_test "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix26-trace-format.json" "${CMAKE_CURRENT_SOURCE_DIR}/../build/fix26-trace-sample.log")
# Round 27: the engine glue without the engine (Runtime.h, Registry.h) -- task scopes, the session and the new-game path, the
# log and Query, the SEH verdict, the input gate, the ModEvent text, the effect registry (two threads), the hurt queue.
add_executable(runtime_test tests/runtime_test.cpp)
target_include_directories(runtime_test PRIVATE include deps/json/single_include)
target_compile_options(runtime_test PRIVATE /W4 /WX /EHsc /utf-8 /bigobj)
add_test(NAME runtime COMMAND runtime_test)
# Round 27: hand anchors for the damage sums at level 100 / 節點倍率 5 / every line (G1), the open's counts (G3), 熔斷's
# formless fuse (G4) and a 24-target burst (B-small), on the real planners.
add_executable(anchor_test tests/anchor_test.cpp)
target_include_directories(anchor_test PRIVATE include deps/json/single_include)
target_compile_options(anchor_test PRIVATE /W4 /WX /EHsc /utf-8 /bigobj)
add_test(NAME anchors COMMAND anchor_test)
