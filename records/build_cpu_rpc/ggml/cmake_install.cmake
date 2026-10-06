# Install script for directory: E:/the_harness/repos/llama.cpp/ggml

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "C:/Program Files (x86)/llama.cpp")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("E:/the_harness/records/build_cpu_rpc/ggml/src/cmake_install.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY OPTIONAL FILES "E:/the_harness/records/build_cpu_rpc/ggml/src/ggml.lib")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/bin" TYPE SHARED_LIBRARY FILES "E:/the_harness/records/build_cpu_rpc/bin/ggml.dll")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include" TYPE FILE FILES
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-cpu.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-alloc.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-backend.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-blas.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-cann.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-cpp.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-cuda.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-opt.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-metal.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-rpc.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-virtgpu.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-sycl.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-vulkan.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-webgpu.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-zendnn.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/ggml-openvino.h"
    "E:/the_harness/repos/llama.cpp/ggml/include/gguf.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY OPTIONAL FILES "E:/the_harness/records/build_cpu_rpc/ggml/src/ggml-base.lib")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/bin" TYPE SHARED_LIBRARY FILES "E:/the_harness/records/build_cpu_rpc/bin/ggml-base.dll")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/ggml" TYPE FILE FILES
    "E:/the_harness/records/build_cpu_rpc/ggml/ggml-config.cmake"
    "E:/the_harness/records/build_cpu_rpc/ggml/ggml-config-version.cmake"
    )
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "E:/the_harness/records/build_cpu_rpc/ggml/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
