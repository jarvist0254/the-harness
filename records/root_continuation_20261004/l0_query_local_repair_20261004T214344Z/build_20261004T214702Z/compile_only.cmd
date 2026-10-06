@echo off
set "PROCESSOR_ARCHITECTURE=AMD64"
set "VSCMD_SKIP_SENDTELEMETRY=1"
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\cl.exe" /nologo /std:c++17 /EHsc /MD /I"E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero" "E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\actual_header_stub_local_revision2.cpp" /Fo"E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\build_20261004T214702Z\stub.obj" /Fe"E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\build_20261004T214702Z\stub.exe" /link /INCREMENTAL:NO /MAP:"E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\build_20261004T214702Z\stub.map"
if errorlevel 1 exit /b %errorlevel%
"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\dumpbin.exe" /imports "E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\build_20261004T214702Z\stub.exe" > "E:\the_harness\records\root_continuation_20261004\l0_query_local_repair_20261004T214344Z\build_20261004T214702Z\pe_imports.raw.txt"
exit /b %errorlevel%
