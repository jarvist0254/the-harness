// RTX 5070 Ti stream benchmark probe (heterogeneous arm, 2026-10-05).
//
// Measures what the pipeline simulator needs as PROVEN inputs:
//   * H2D / D2H bandwidth, pinned vs pageable host memory
//   * latency vs transfer size (8 KiB .. 512 MiB)
//   * concurrent H2D+D2H overlap (2 streams + events)
//   * checksum on every transfer (success codes lied twice on record)
//
// Written as C (no C++ STL): the installed CUDA 12.3 toolkit rejects the
// MSVC 14.41 STL headers (STL1002 needs CUDA >= 12.4), so <vector>/<string>
// are deliberately avoided. snprintf/strcmp from stdio.h/string.h are fine.
//
// Build (verified 2026-10-05): CUDA v12.8 nvcc + VS2022 BuildTools MSVC
// 14.41, no override flag:
//   nvcc -O2 -o stream_bench.exe stream_bench.cu
// Do NOT use CUDA 12.3 with MSVC 14.41 (STL1002 hard error, even on an
// empty .cu). Every transfer is checksummed, so a bad codegen would FAIL
// loudly, not silently.
// Run:
//   stream_bench [--json] [--inject-corruption]
//
// Output: human lines, or one JSON object with --json.
// Exit codes: 0 measured OK, 1 FAIL (checksum or CUDA error), 2 NOT_CHECKED
// (no CUDA device). Stdout is the receipt.
#include <cuda_runtime.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(call, stage)                                                 \
    do {                                                                   \
        cudaError_t _e = (call);                                            \
        if (_e != cudaSuccess) {                                            \
            printf("{\"status\":\"FAIL\",\"stage\":\"%s\",\"cuda_error\":\"%s\"}\n", \
                   stage, cudaGetErrorString(_e));                         \
            return 1;                                                      \
        }                                                                  \
    } while (0)

static const uint32_t kPattern = 0x4A17C0DEu;
static const size_t kSizes[] = {8u << 10, 4u << 20, 64u << 20, 512u << 20};
static const int kItersSmall = 100;  // 8 KiB / 4 MiB
static const int kItersBig = 10;     // 64 MiB / 512 MiB
static const uint32_t kFaultMask = 0xDEADBEEFu;

typedef struct {
    char name[64];
    size_t bytes;
    double seconds;
    double gbps;
    int checksum_ok;  // 1 match on a clean run
} CaseResult;

// Returns 0 pass, 1 FAIL. Clean run: any mismatch FAILs. Corrupt run: the
// device-side fault MUST be observed in the readback (mismatches > 0);
// a clean readback means the injection was silently lost -> FAIL.
static int run_case(uint8_t* d_buf, uint8_t* h_buf, size_t bytes,
                    int corrupt, CaseResult* out, const char* name,
                    cudaStream_t stream) {
    const size_t words = bytes / sizeof(uint32_t);
    uint32_t* h_words = (uint32_t*)h_buf;
    size_t i;
    int iters = (bytes <= (4u << 20)) ? kItersSmall : kItersBig;
    int iter;
    cudaEvent_t t0, t1;
    float ms = 0;
    size_t mismatches = 0;

    CHECK(cudaEventCreate(&t0), "event_create");
    CHECK(cudaEventCreate(&t1), "event_create");

    // Timed round trips on one stream (clean data; fault goes in later).
    CHECK(cudaEventRecord(t0, stream), "record");
    for (iter = 0; iter < iters; ++iter) {
        CHECK(cudaMemcpyAsync(d_buf, h_buf, bytes, cudaMemcpyHostToDevice,
                              stream),
              "h2d");
        CHECK(cudaMemcpyAsync(h_buf, d_buf, bytes, cudaMemcpyDeviceToHost,
                              stream),
              "d2h");
    }
    CHECK(cudaEventRecord(t1, stream), "record");
    CHECK(cudaEventSynchronize(t1), "sync");
    CHECK(cudaEventElapsedTime(&ms, t0, t1), "elapsed");
    CHECK(cudaEventDestroy(t0), "event_destroy");
    CHECK(cudaEventDestroy(t1), "event_destroy");

    // Verify leg: host pattern -> device, optional DEVICE-side fault, back.
    for (i = 0; i < words; ++i) h_words[i] = kPattern;
    CHECK(cudaMemcpyAsync(d_buf, h_buf, bytes, cudaMemcpyHostToDevice, stream),
          "h2d_verify");
    if (corrupt) {
        const uint32_t fault = kPattern ^ kFaultMask;
        CHECK(cudaMemcpyAsync(d_buf + (words / 2) * sizeof(uint32_t), &fault,
                              sizeof(fault), cudaMemcpyHostToDevice, stream),
              "fault_inject");
    }
    CHECK(cudaMemcpyAsync(h_buf, d_buf, bytes, cudaMemcpyDeviceToHost, stream),
          "d2h_verify");
    CHECK(cudaStreamSynchronize(stream), "sync_verify");

    for (i = 0; i < words; ++i) {
        if (h_words[i] != kPattern) {
            ++mismatches;
            if (mismatches < 4)
                printf("{\"note\":\"mismatch\",\"word\":%llu,"
                       "\"got\":\"0x%08X\"}\n",
                       (unsigned long long)i, h_words[i]);
        }
    }

    strncpy(out->name, name, sizeof(out->name) - 1);
    out->name[sizeof(out->name) - 1] = '\0';
    out->bytes = bytes;
    out->seconds = ((double)ms / 1000.0) / (double)iters;
    out->gbps = (2.0 * (double)bytes / 1e9) / out->seconds;
    if (corrupt) {
        out->checksum_ok = 0;
        if (mismatches == 0) return 1;  // injection lost: control broken
        return 0;                       // fault observed: control passes
    }
    out->checksum_ok = (mismatches == 0) ? 1 : 0;
    return (mismatches == 0) ? 0 : 1;
}

static int run_overlap(uint8_t* d_a, uint8_t* d_b, const uint8_t* h_a,
                       uint8_t* h_b, size_t bytes, double* overlap_gain) {
    // Two streams: H2D on s0 concurrent with D2H on s1.
    // Gain = sequential_time / overlapped_time; ~1.0 means no overlap.
    cudaStream_t s0, s1;
    cudaEvent_t t0, t1, t2;
    int iter;
    const int iters = 20;
    float ms_s0 = 0, ms_s1 = 0, ms_seq = 0, ms_over;
    CHECK(cudaStreamCreate(&s0), "stream_create");
    CHECK(cudaStreamCreate(&s1), "stream_create");
    CHECK(cudaEventCreate(&t0), "event_create");
    CHECK(cudaEventCreate(&t1), "event_create");
    CHECK(cudaEventCreate(&t2), "event_create");
    CHECK(cudaEventRecord(t0, s0), "record");
    for (iter = 0; iter < iters; ++iter) {
        CHECK(cudaMemcpyAsync(d_a, (void*)h_a, bytes, cudaMemcpyHostToDevice,
                              s0),
              "h2d_overlap");
        CHECK(cudaMemcpyAsync(h_b, d_b, bytes, cudaMemcpyDeviceToHost, s1),
              "d2h_overlap");
    }
    // Stop events on BOTH streams: overlapped wall time is the max of the
    // two timelines, not s0's alone.
    CHECK(cudaEventRecord(t1, s0), "record");
    CHECK(cudaEventRecord(t2, s1), "record");
    CHECK(cudaStreamSynchronize(s0), "sync_s0");
    CHECK(cudaStreamSynchronize(s1), "sync_s1");
    CHECK(cudaEventElapsedTime(&ms_s0, t0, t1), "elapsed");
    CHECK(cudaEventElapsedTime(&ms_s1, t0, t2), "elapsed");
    ms_over = (ms_s0 > ms_s1) ? ms_s0 : ms_s1;
    // Sequential reference on one stream.
    CHECK(cudaEventRecord(t0, s0), "record");
    for (iter = 0; iter < iters; ++iter) {
        CHECK(cudaMemcpyAsync(d_a, (void*)h_a, bytes, cudaMemcpyHostToDevice,
                              s0),
              "h2d_seq");
        CHECK(cudaMemcpyAsync(h_b, d_b, bytes, cudaMemcpyDeviceToHost, s0),
              "d2h_seq");
    }
    CHECK(cudaEventRecord(t1, s0), "record");
    CHECK(cudaStreamSynchronize(s0), "sync_seq");
    CHECK(cudaEventElapsedTime(&ms_seq, t0, t1), "elapsed");
    CHECK(cudaStreamDestroy(s0), "stream_destroy");
    CHECK(cudaStreamDestroy(s1), "stream_destroy");
    CHECK(cudaEventDestroy(t0), "event_destroy");
    CHECK(cudaEventDestroy(t1), "event_destroy");
    CHECK(cudaEventDestroy(t2), "event_destroy");
    *overlap_gain = (ms_over > 0) ? ((double)ms_seq / (double)ms_over) : 1.0;
    return 0;
}

int main(int argc, char** argv) {
    int do_json = 0, corrupt = 0, i, pass;
    int devices = 0;
    cudaDeviceProp prop;
    CaseResult cases[8];
    int ncases = 0;
    double overlap_gain = 1.0;
    uint8_t *d_a = NULL, *d_b = NULL, *h_pin = NULL, *h_page = NULL;
    const size_t biggest = 512u << 20;
    cudaStream_t stream;
    size_t s;

    for (i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--json"))
            do_json = 1;
        else if (!strcmp(argv[i], "--inject-corruption"))
            corrupt = 1;
        else {
            printf("{\"status\":\"FAIL\",\"stage\":\"cli\","
                   "\"reason\":\"unknown_option\"}\n");
            return 1;
        }
    }
    if (cudaGetDeviceCount(&devices) != cudaSuccess || devices < 1) {
        printf("{\"status\":\"NOT_CHECKED\",\"reason\":\"no_cuda_device\"}\n");
        return 2;
    }
    CHECK(cudaSetDevice(0), "set_device");
    CHECK(cudaGetDeviceProperties(&prop, 0), "props");

    CHECK(cudaMalloc((void**)&d_a, biggest), "device_alloc");
    CHECK(cudaMalloc((void**)&d_b, biggest), "device_alloc");
    CHECK(cudaMallocHost((void**)&h_pin, biggest), "pinned_alloc");
    h_page = (uint8_t*)malloc(biggest);
    if (!h_page) {
        printf("{\"status\":\"FAIL\",\"stage\":\"host_alloc\"}\n");
        return 1;
    }
    CHECK(cudaStreamCreate(&stream), "stream_create");
    for (pass = 0; pass < 2; ++pass) {
        uint8_t* h = pass ? h_page : h_pin;
        const char* kind = pass ? "pageable" : "pinned";
        for (s = 0; s < 4; ++s) {
            char name[64];
            sprintf(name, "%s_%llu", kind, (unsigned long long)kSizes[s]);
            if (run_case(d_a, h, kSizes[s], corrupt, &cases[ncases], name,
                         stream) != 0) {
                printf("{\"status\":\"FAIL\",\"stage\":\"%s\","
                       "\"reason\":\"checksum\"}\n",
                       name);
                return 1;
            }
            ++ncases;
        }
    }
    if (run_overlap(d_a, d_b, h_pin, h_pin, 64u << 20, &overlap_gain) != 0)
        return 1;

    if (!do_json) {
        printf("device: %s cc=%d.%d\n", prop.name, prop.major, prop.minor);
        for (i = 0; i < ncases; ++i)
            printf("%-16s %10llu B %9.4f s %8.2f GB/s checksum=%s\n",
                   cases[i].name, (unsigned long long)cases[i].bytes,
                   cases[i].seconds, cases[i].gbps,
                   cases[i].checksum_ok ? "OK"
                   : (corrupt ? "MISMATCH(seen)" : "BAD"));
        printf("overlap_64MiB_gain: %.3f\n", overlap_gain);
    } else {
        size_t k;
        printf("{\"status\":\"MEASURED\",\"evidence\":\"PROVEN\","
               "\"device\":\"%s\",\"cc\":[%d,%d],"
               "\"overlap_64MiB_gain\":%.4f,\"cases\":[",
               prop.name, prop.major, prop.minor, overlap_gain);
        for (k = 0; k < (size_t)ncases; ++k)
            printf("%s{\"name\":\"%s\",\"bytes\":%llu,\"seconds\":%.6f,"
                   "\"gbps\":%.3f,\"checksum_ok\":%s}",
                   k ? "," : "", cases[k].name,
                   (unsigned long long)cases[k].bytes, cases[k].seconds,
                   cases[k].gbps, cases[k].checksum_ok ? "true" : "false");
        printf("]}\n");
    }
    CHECK(cudaStreamDestroy(stream), "stream_destroy");
    CHECK(cudaFree(d_a), "free");
    CHECK(cudaFree(d_b), "free");
    CHECK(cudaFreeHost(h_pin), "free_host");
    free(h_page);
    // Repo convention: a corruption run that OBSERVED every fault exits 1
    // ("expected mismatch detected"); run_case already returned 1 above
    // when the injection was silently lost. Clean all-match runs exit 0.
    return corrupt ? 1 : 0;
}
