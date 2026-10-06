@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
set "VULKAN_SDK=E:\the_harness\records\build_vulkan_real\toolchain\sdk"
set "PATH=%VULKAN_SDK%\Bin;%PATH%"
"C:\Users\thoma\AppData\Local\Programs\Python\Python310\Scripts\cmake.exe" --build "E:\the_harness\records\build_vulkan_real\build" --target llama-cli test-backend-ops ggml-rpc-server -- -j8
exit /b %errorlevel%
