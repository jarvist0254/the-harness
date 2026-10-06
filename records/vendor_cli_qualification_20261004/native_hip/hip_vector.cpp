#include <hip/hip_runtime.h>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

#define HIP_CHECK(call) do { hipError_t status = (call); if (status != hipSuccess) { \
  std::fprintf(stderr, "%s failed: %s (%d)\n", #call, hipGetErrorString(status), int(status)); return 1; } } while (0)

__global__ void affine(float* values, int count) {
  int i = int(blockIdx.x * blockDim.x + threadIdx.x);
  if (i < count) values[i] = 2.0f * values[i] + 1.0f;
}

int main(int argc, char** argv) {
  bool corrupt = argc == 2 && std::strcmp(argv[1], "--inject-corruption") == 0;
  if (argc > 1 && !corrupt) return 2;
  int devices = 0, selected = -1;
  hipDeviceProp_t props{};
  HIP_CHECK(hipGetDeviceCount(&devices));
  for (int i = 0; i < devices; ++i) {
    hipDeviceProp_t candidate{};
    HIP_CHECK(hipGetDeviceProperties(&candidate, i));
    if (std::strcmp(candidate.gcnArchName, "gfx1036") == 0) { selected = i; props = candidate; break; }
  }
  if (selected < 0) { std::fprintf(stderr, "NOT_CHECKED: gfx1036 not enumerated\n"); return 2; }
  HIP_CHECK(hipSetDevice(selected));
  constexpr int count = 262144;
  constexpr size_t bytes = count * sizeof(float);
  std::vector<float> host(count);
  for (int i = 0; i < count; ++i) host[i] = float(i % 1024) / 16.0f;
  float* device = nullptr;
  HIP_CHECK(hipMalloc(&device, bytes));
  hipError_t error = hipMemcpy(device, host.data(), bytes, hipMemcpyHostToDevice);
  if (error != hipSuccess) { hipError_t cleanup = hipFree(device); std::fprintf(stderr, "upload: %s; free: %s\n", hipGetErrorString(error), hipGetErrorString(cleanup)); return 1; }
  hipLaunchKernelGGL(affine, dim3((count + 255) / 256), dim3(256), 0, 0, device, count);
  error = hipGetLastError();
  if (error == hipSuccess) error = hipDeviceSynchronize();
  if (error == hipSuccess) error = hipMemcpy(host.data(), device, bytes, hipMemcpyDeviceToHost);
  hipError_t cleanup = hipFree(device);
  if (error != hipSuccess || cleanup != hipSuccess) { std::fprintf(stderr, "kernel/readback: %s; free: %s\n", hipGetErrorString(error), hipGetErrorString(cleanup)); return 1; }
  if (corrupt) host[12345] += 1.0f;
  int mismatches = 0;
  float maximum = 0.0f;
  for (int i = 0; i < count; ++i) {
    float expected = 2.0f * (float(i % 1024) / 16.0f) + 1.0f;
    float difference = std::fabs(host[i] - expected);
    if (!std::isfinite(host[i]) || difference != 0.0f) ++mismatches;
    if (difference > maximum) maximum = difference;
  }
  std::printf("{\"status\":\"%s\",\"arch\":\"%s\",\"device_index\":%d,\"integrated\":%d,\"pci_bus\":%d,\"buffer_bytes\":%zu,\"kernel_completed\":true,\"mismatch_count\":%d,\"max_abs_error\":%.9g,\"corruption_applied\":%s}\n", mismatches ? "FAIL" : "PASS", props.gcnArchName, selected, props.integrated, props.pciBusID, bytes, mismatches, double(maximum), corrupt ? "true" : "false");
  return mismatches ? 1 : 0;
}
