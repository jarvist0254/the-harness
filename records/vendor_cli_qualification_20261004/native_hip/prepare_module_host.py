from pathlib import Path
root = Path(__file__).resolve().parent
source = (root / 'hip_vector.cpp').read_text()
source = source.replace('#include <hip/hip_runtime.h>', '#include <hip/hip_runtime_api.h>')
begin = source.index('__global__ void affine(')
end = source.index('int main(', begin)
source = source[:begin] + source[end:]
source = source.replace('  HIP_CHECK(hipSetDevice(selected));', '  HIP_CHECK(hipSetDevice(selected));\n  hipModule_t module = nullptr;\n  hipFunction_t function = nullptr;\n  HIP_CHECK(hipModuleLoad(&module, "affine_gfx1036.hsaco"));\n  HIP_CHECK(hipModuleGetFunction(&function, module, "affine"));')
source = source.replace('  hipLaunchKernelGGL(affine, dim3((count + 255) / 256), dim3(256), 0, 0, device, count);\n  error = hipGetLastError();', '  int kernel_count = count;\n  void* arguments[] = {&device, &kernel_count};\n  error = hipModuleLaunchKernel(function, (count + 255) / 256, 1, 1, 256, 1, 1, 0, nullptr, arguments, nullptr);')
source = source.replace('  if (corrupt) host[12345]', '  HIP_CHECK(hipModuleUnload(module));\n  if (corrupt) host[12345]')
(root / 'hip_module_host.cpp').write_text(source)
