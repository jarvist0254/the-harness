# CMake generated Testfile for 
# Source directory: E:/the_harness/repos/llama.cpp/examples/eval-callback
# Build directory: E:/the_harness/records/build_cpu_rpc/examples/eval-callback
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test([=[test-eval-callback-download-model]=] "C:/Users/thoma/AppData/Local/Programs/Python/Python310/Lib/site-packages/cmake/data/bin/cmake.exe" "-DDEST=E:/the_harness/records/build_cpu_rpc/tinyllamas/stories15M-q4_0.gguf" "-DNAME=tinyllamas/stories15M-q4_0.gguf" "-DHASH=SHA256=66967fbece6dbe97886593fdbb73589584927e29119ec31f08090732d1861739" "-P" "E:/the_harness/repos/llama.cpp/cmake/download-models.cmake")
set_tests_properties([=[test-eval-callback-download-model]=] PROPERTIES  FIXTURES_SETUP "test-eval-callback-download-model" _BACKTRACE_TRIPLES "E:/the_harness/repos/llama.cpp/examples/eval-callback/CMakeLists.txt;17;add_test;E:/the_harness/repos/llama.cpp/examples/eval-callback/CMakeLists.txt;0;")
add_test([=[test-eval-callback]=] "E:/the_harness/records/build_cpu_rpc/bin/llama-eval-callback.exe" "-m" "E:/the_harness/records/build_cpu_rpc/tinyllamas/stories15M-q4_0.gguf" "--prompt" "hello" "--seed" "42" "-ngl" "0")
set_tests_properties([=[test-eval-callback]=] PROPERTIES  FIXTURES_REQUIRED "test-eval-callback-download-model" _BACKTRACE_TRIPLES "E:/the_harness/repos/llama.cpp/examples/eval-callback/CMakeLists.txt;24;add_test;E:/the_harness/repos/llama.cpp/examples/eval-callback/CMakeLists.txt;0;")
