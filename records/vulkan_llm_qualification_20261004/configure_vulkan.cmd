@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
set "VULKAN_SDK=E:\the_harness\records\build_vulkan_real\toolchain\sdk"
set "PATH=%VULKAN_SDK%\Bin;%PATH%"
"C:\Users\thoma\AppData\Local\Programs\Python\Python310\Scripts\cmake.exe" -S "E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source" -B "E:\the_harness\records\build_vulkan_real\build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_SUPPRESS_REGENERATION=ON -DGGML_NATIVE=OFF -DGGML_VULKAN=ON -DGGML_RPC=ON -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_EXAMPLES=ON -DLLAMA_BUILD_SERVER=ON -DVulkan_INCLUDE_DIR="%VULKAN_SDK%\Include" -DVulkan_LIBRARY="%VULKAN_SDK%\Lib\vulkan-1.lib" -DVulkan_GLSLC_EXECUTABLE="%VULKAN_SDK%\Bin\glslc.exe" -DSPIRV-Headers_DIR="%VULKAN_SDK%\Lib\cmake\SPIRV-Headers"
exit /b %errorlevel%

