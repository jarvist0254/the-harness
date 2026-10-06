// Minimal HIP crash localizer (diagnostic, three-vendor arm).
#include <hip/hip_runtime.h>
#include <cstdio>

int main(void) {
    fprintf(stderr, "step: enter\n"); fflush(stderr);
    int count = -1;
    hipError_t err = hipGetDeviceCount(&count);
    fprintf(stderr, "step: count=%d err=%d (%s)\n", count, (int)err,
            hipGetErrorString(err)); fflush(stderr);
    if (err != hipSuccess || count < 1) return 2;
    hipDeviceProp_t prop;
    err = hipGetDeviceProperties(&prop, 0);
    fprintf(stderr, "step: props err=%d\n", (int)err); fflush(stderr);
    if (err != hipSuccess) return 1;
    fprintf(stderr, "step: name=%.64s arch=%.32s\n", prop.name,
            prop.gcnArchName); fflush(stderr);
    return 0;
}
