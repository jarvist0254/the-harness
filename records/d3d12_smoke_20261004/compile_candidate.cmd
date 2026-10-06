@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
echo WindowsSDKVersion=%WindowsSDKVersion%
cl.exe /nologo /std:c++17 /EHsc "E:\the_harness\j_link\d3d12_smoke.cpp" /Fe"E:\the_harness\records\d3d12_smoke_20261004\d3d12_smoke.exe" d3d12.lib dxgi.lib
exit /b %errorlevel%
