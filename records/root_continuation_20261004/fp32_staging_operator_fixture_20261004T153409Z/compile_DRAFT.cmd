@echo off
rem Draft build command. Not executed. First argument must be NEW admitted derived build root.
if "%~1"=="" exit /b 2
set "PROBE_DERIVED_BUILD=%~f1"
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /O2 /MD /I"E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source\ggml\include" /Fo"%~dp0fp32_staging_operator.obj" /Fe"%~dp0fp32_staging_operator.exe" "%~dp0fp32_staging_operator.cpp" /link /LIBPATH:"%PROBE_DERIVED_BUILD%\ggml\src" /LIBPATH:"%PROBE_DERIVED_BUILD%\ggml\src\ggml-rpc" /LIBPATH:"%PROBE_DERIVED_BUILD%\ggml\src\ggml-vulkan" /LIBPATH:"E:\the_harness\records\build_vulkan_real\toolchain\sdk\Lib" ggml.lib ggml-cpu.lib ggml-rpc.lib ggml-vulkan.lib ggml-base.lib vulkan-1.lib bcrypt.lib kernel32.lib user32.lib gdi32.lib winspool.lib shell32.lib ole32.lib oleaut32.lib uuid.lib comdlg32.lib advapi32.lib
exit /b %errorlevel%
