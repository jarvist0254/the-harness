// Separate device-only translation unit avoids host C++ standard-library headers.
#include <hip/hip_runtime.h>
extern "C" __global__ void affine(float* values, int count) {
  int i = int(blockIdx.x * blockDim.x + threadIdx.x);
  if (i < count) values[i] = 2.0f * values[i] + 1.0f;
}
