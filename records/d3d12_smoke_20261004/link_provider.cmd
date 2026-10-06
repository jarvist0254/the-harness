@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
echo WindowsSDKVersion=%WindowsSDKVersion%
cl.exe /nologo /std:c++17 /EHsc "E:\the_harness\records\factory_runs\20261004\d3d12_pro_nonthinking_20261004T101008434Z\d3d12_crossadapter_buffer.cpp" /Fe"E:\the_harness\records\d3d12_smoke_20261004\d3d12_crossadapter_buffer.exe" d3d12.lib dxgi.lib
exit /b %errorlevel%
