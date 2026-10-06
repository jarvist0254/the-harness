import hashlib,json,pathlib
A=pathlib.Path(__file__).parent
R=A/'stub_build_20261004T213121Z'; R.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(A/'source.original_untrusted.cpp')=='9f2635be587804c88c2988066142ef4c307d98adc0afc4649422a39ac880b694'
assert sha(A/'actual_header_stub_DRAFT.cpp')=='b551a78647c0deb835edefaab04368e15abf0650998a9d1f657f6c13d7af8427'
base=(A/'compile_controller.py').read_text()
text=base.replace("source=R/'source.original_untrusted.cpp'","source=R.parent/'source.original_untrusted.cpp'")
text=text.replace("files=list(paths.values())+[source,header,pathlib.Path(__file__),R/'compile_only.cmd']", "stub=R.parent/'actual_header_stub_DRAFT.cpp'\nassert sha(stub)=='b551a78647c0deb835edefaab04368e15abf0650998a9d1f657f6c13d7af8427'\nfiles=list(paths.values())+[source,stub,header,pathlib.Path(__file__),R/'compile_only.cmd',R/'tool_pin.json']")
text=text.replace('l0_query_replacement_compile_only','l0_actual_header_stub_build')
text=text.replace('ROOT_ADMITTED_COMPILER_ONLY_NO_LINK_NO_RUNTIME','ROOT_ADMITTED_CPU_STUB_BUILD_NO_GPU_LOADER_LINK_NO_RUNTIME')
dump=pathlib.Path(r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\dumpbin.exe')
pin={'path':str(dump),'sha256':sha(dump)}
(R/'tool_pin.json').write_text(json.dumps(pin,indent=2))
text=text.replace("before={str(p):sha(p) for p in files}","dump_pin=read(R/'tool_pin.json'); dumpbin=pathlib.Path(dump_pin['path']); assert sha(dumpbin)==dump_pin['sha256']; files.append(dumpbin)\nbefore={str(p):sha(p) for p in files}")
(R/'compile_controller.py').write_text(text)
(R/'run_owned_compile.py').write_bytes((A/'run_owned_compile.py').read_bytes())
tool=r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64'
cmd='\r\n'.join(['@echo off','set "PROCESSOR_ARCHITECTURE=AMD64"','set "VSCMD_SKIP_SENDTELEMETRY=1"', 'call "C:\\Program Files\\Microsoft Visual Studio\\18\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat"','if errorlevel 1 exit /b %errorlevel%',f'"{tool}\\cl.exe" /nologo /std:c++17 /EHsc /MD /I"E:\\the_harness\\records\\toolchains\\level_zero_20261004\\sdk\\include\\level_zero" "{A / "actual_header_stub_DRAFT.cpp"}" /Fo"{R / "stub.obj"}" /Fe"{R / "stub.exe"}" /link /INCREMENTAL:NO /MAP:"{R / "stub.map"}"', 'if errorlevel 1 exit /b %errorlevel%',f'"{dump}" /imports "{R / "stub.exe"}" > "{R / "pe_imports.raw.txt"}"','exit /b %errorlevel%',''])
(R/'compile_only.cmd').write_bytes(cmd.encode())
print(json.dumps({'build_folder':str(R),'controller_sha256':sha(R/'compile_controller.py'),'cmd_sha256':sha(R/'compile_only.cmd'),'dumpbin_pin':pin},indent=2))
