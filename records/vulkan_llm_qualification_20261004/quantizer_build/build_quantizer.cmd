@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
"C:\Users\thoma\AppData\Local\Programs\Python\Python310\Scripts\cmake.exe" --build "E:\the_harness\records\build_vulkan_real\build" --target llama-quantize --parallel 4
exit /b %errorlevel%
