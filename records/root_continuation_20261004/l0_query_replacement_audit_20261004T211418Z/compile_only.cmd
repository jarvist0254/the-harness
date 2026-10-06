@echo off
set "PROCESSOR_ARCHITECTURE=AMD64"
set "VSCMD_SKIP_SENDTELEMETRY=1"
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b %errorlevel%
"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\cl.exe" /nologo /std:c++17 /EHsc /c /TP /I"E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero" "E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\source.original_untrusted.cpp" /Fo"E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\source.original_untrusted.obj"
exit /b %errorlevel%

