// HIP enumeration + peer-query probe (three-vendor arm, 2026-10-05).
//
// Enumerates HIP devices, prints props, evaluates the directed
// hipDeviceCanAccessPeer matrix (each direction independent), and runs a
// 64 MiB checksum memcpy on device 0. Discrete-GPU peer pairs need two
// discrete cards; an iGPU HIP target exercises the full code path but is
// SHARED host memory, so it NEVER unlocks a peer tier -- selection stays
// HOST_STAGING/PINNED and says why.
//
// Build (ROCm 6.4 Windows, HIP_PATH set):
//   hipcc -O2 -o hip_enum.exe hip_enum.cpp
// Exit: 0 receipt (pairs may be NOT_CHECKED), 1 FAIL, 2 no HIP devices.
#include <hip/hip_runtime.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

#define CHECK(call, stage)                                                \
    do {                                                                  \
        hipError_t _e = (call);                                            \
        if (_e != hipSuccess) {                                            \
            printf("{\"status\":\"FAIL\",\"stage\":\"%s\",\"hip_error\":\"%s\"}\n", \
                   stage, hipGetErrorString(_e));                         \
            return 1;                                                     \
        }                                                                 \
    } while (0)

static const uint32_t kPattern = 0x4A17C0DEu;
static const size_t kBytes = 64u << 20;

int main(void) {
    int count = 0;
    hipError_t err = hipGetDeviceCount(&count);
    if (err != hipSuccess || count < 1) {
        printf("{\"status\":\"NOT_CHECKED\",\"devices\":0,"
               "\"reason\":\"no HIP devices enumerated\"}\n");
        return 2;
    }
    printf("{\"status\":\"MEASURED\",\"evidence\":\"PROVEN\","
           "\"hip_device_count\":%d,\"devices\":[",
           count);
    for (int d = 0; d < count; ++d) {
        hipDeviceProp_t prop;
        CHECK(hipGetDeviceProperties(&prop, d), "props");
        printf("%s{\"ordinal\":%d,\"name\":\"%s\",\"gcnArchName\":\"%s\","
               "\"totalGlobalMem\":%.0f,\"multiProcessorCount\":%d,"
               "\"pci\":\"%04x:%02x:%02x\",\"unifiedAddressing\":%d}",
               d ? "," : "", d, prop.name, prop.gcnArchName,
               (double)prop.totalGlobalMem, prop.multiProcessorCount,
               prop.pciDomainID, prop.pciBusID, prop.pciDeviceID,
               prop.unifiedAddressing);
    }
    printf("],\"peer_matrix\":[");
    int first = 1;
    for (int s = 0; s < count; ++s) {
        for (int t = 0; t < count; ++t) {
            if (s == t) continue;
            int access = 0;
            err = hipDeviceCanAccessPeer(&access, s, t);
            printf("%s{\"src\":%d,\"dst\":%d,\"can_access\":%d,"
                   "\"query_ok\":%s}",
                   first ? "" : ",", s, t, access,
                   err == hipSuccess ? "true" : "false");
            first = 0;
        }
    }
    printf("]");
    if (count == 1)
        printf(",\"peer_note\":\"single device: no peer pair constructible\"");

    // Checksum memcpy on device 0 (correctness of the path, not a peer).
    CHECK(hipSetDevice(0), "set_device");
    void* d_buf = NULL;
    CHECK(hipMalloc(&d_buf, kBytes), "device_alloc");
    std::vector<uint32_t> host(kBytes / sizeof(uint32_t), kPattern);
    CHECK(hipMemcpy(d_buf, host.data(), kBytes, hipMemcpyHostToDevice),
          "h2d");
    CHECK(hipMemset(d_buf, 0, kBytes), "clear_guard");
    CHECK(hipMemcpy(d_buf, host.data(), kBytes, hipMemcpyHostToDevice),
          "h2d_verify");
    std::vector<uint32_t> back(kBytes / sizeof(uint32_t), 0);
    CHECK(hipMemcpy(back.data(), d_buf, kBytes, hipMemcpyDeviceToHost),
          "d2h");
    size_t mismatches = 0;
    for (size_t i = 0; i < back.size(); ++i)
        if (back[i] != kPattern && ++mismatches < 4)
            printf(",\"mismatch\":{\"word\":%llu,\"got\":\"0x%08X\"}",
                   (unsigned long long)i, back[i]);
    CHECK(hipFree(d_buf), "free");
    printf(",\"checksum_64MiB_ok\":%s}\n", mismatches == 0 ? "true" : "false");
    return mismatches == 0 ? 0 : 1;
}
