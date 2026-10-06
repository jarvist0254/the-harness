#include <sycl/sycl.hpp>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <vector>

int main(int argc, char** argv) {
  const bool corrupt = argc == 2 && std::strcmp(argv[1], "--inject-corruption") == 0;
  if (argc > 1 && !corrupt) return 2;
  try {
    std::vector<sycl::device> qualified;
    for (const auto& device : sycl::device::get_devices(sycl::info::device_type::gpu)) {
      auto vendor = device.get_info<sycl::info::device::vendor>();
      if (device.get_backend() == sycl::backend::opencl &&
          (vendor.find("NVIDIA") != std::string::npos || vendor.find("AMD") != std::string::npos ||
           vendor.find("Advanced Micro Devices") != std::string::npos)) qualified.push_back(device);
    }
    if (qualified.empty()) { std::puts("{\"status\":\"NOT_CHECKED\",\"reason\":\"No allowed NVIDIA/AMD OpenCL GPU; CPU fallback forbidden\"}"); return 2; }
    constexpr size_t count = 262144;
    std::vector<float> data(count);
    for (size_t i = 0; i < count; ++i) data[i] = float(i % 1024) / 16.0f;
    sycl::queue queue(qualified.front());
    {
      sycl::buffer<float, 1> buffer(data.data(), sycl::range<1>(count));
      auto event = queue.submit([&](sycl::handler& handler) {
        auto values = buffer.get_access<sycl::access::mode::read_write>(handler);
        handler.parallel_for(sycl::range<1>(count), [=](sycl::id<1> i) { values[i] = 2.0f * values[i] + 1.0f; });
      });
      event.wait_and_throw();
      queue.wait_and_throw();
    }
    if (corrupt) data[12345] += 1.0f;
    size_t mismatches = 0;
    float maximum = 0;
    for (size_t i = 0; i < count; ++i) {
      float error = std::fabs(data[i] - (2.0f * (float(i % 1024) / 16.0f) + 1.0f));
      if (!std::isfinite(data[i]) || error != 0) ++mismatches;
      if (error > maximum) maximum = error;
    }
    std::printf("{\"status\":\"%s\",\"kernel_completed\":true,\"buffer_bytes\":1048576,\"mismatch_count\":%zu,\"max_abs_error\":%.9g,\"compiler_origin\":\"INTEL\",\"device_vendor\":\"%s\",\"intel_hardware_qualification\":false}\n", mismatches ? "FAIL" : "PASS", mismatches, double(maximum), qualified.front().get_info<sycl::info::device::vendor>().c_str());
    return mismatches ? 1 : 0;
  } catch (const sycl::exception& error) { std::fprintf(stderr, "SYCL exception: %s\n", error.what()); return 1; }
}
