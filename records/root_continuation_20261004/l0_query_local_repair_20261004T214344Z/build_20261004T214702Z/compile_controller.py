import hashlib,importlib.util,json,pathlib,sys
R=pathlib.Path(__file__).resolve().parent
T=pathlib.Path(r'E:\the_harness\records\toolchains\level_zero_20261004\runtime_source')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
tools=read(T/'toolchain_policy_pins.json')
assert sha(T/'toolchain_policy_pins.json')=='0cd166bb42856517d9a5cdb1557ff1b01f8ade6f3c273a1face8eb83b1443c20'
paths={k:pathlib.Path(v['path']) for k,v in tools.items()}
for k,p in paths.items():assert sha(p)==tools[k]['sha256']
source=R.parent/'source.local_derivative_revision2.cpp';header=pathlib.Path(r'E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h')
assert sha(source)=='5e8c32b98c1fec8fa708435fc7c039828b1ed1326fca269a0e1bb75fcd3edbd6'
assert sha(header)=='c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de'
assert sha(sys.executable)==tools['python']['sha256']
stub=R.parent/'actual_header_stub_local_revision2.cpp'
assert sha(stub)=='78250c8d9e780295e3385cf5d5dc88a6c4028064e7383658aaaa00f6f5c7f91d'
files=list(paths.values())+[source,stub,header,pathlib.Path(__file__),R/'compile_only.cmd',R/'tool_pin.json']
dump_pin=read(R/'tool_pin.json'); dumpbin=pathlib.Path(dump_pin['path']); assert sha(dumpbin)==dump_pin['sha256']; files.append(dumpbin)
before={str(p):sha(p) for p in files}
suite=read(paths['native5receipt']);assert suite['status']=='FIVE_CPU_FIXTURES_PASS' and suite['pins_before']==suite['pins_after']
driver=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\native_driver.py');assert sha(driver)=='e4327908e0da6f668ba7ae51cf92fb641bb7c4e02dde019722a863b8217c3c1d'
d=load(driver,'private_compile_native_evidence_validator')
assert [c['case'] for c in suite['cases']]==list(d.CASES)
for c in suite['cases']:
 assert c['controller_exit']==0 and c['outer_timeout'] is False and c['reader_joined'] is True and c['controller_pid_check']['absent'] is True
 assert not c['capture']['overflow'] and not c['capture']['errors']
 d.validate_result(c['case'],c['actual']['result'],c['actual']['restart'],'compiler_root_exited_zero')
m=load(paths['supervisor'],'private_peer_compile_supervisor');load(paths['compiler_adapter'],'private_peer_compile_adapter').install(m)
manifest={'version':1,'run_id':'l0_actual_header_stub_build','workers':[{'worker_id':'compile','argv':[str(paths['cmd']),'/d','/c',str(R/'compile_only.cmd')],'executable_sha256':tools['cmd']['sha256'],'cwd':str(R)}],'deadline_seconds':60,'startup_seconds':10,'log_limit_bytes':131072,'containment_policy':'kill_on_close'}
result=m.run_workers(manifest,str(R/'contained_compile'))
restart=m.restart_receipt(str(R/'contained_compile'),manifest['run_id'])
after={str(p):sha(p) for p in files}
worker=result.get('workers',[{}])[0]
clean=result.get('drain_proof')=='CLEANUP' and type(result.get('job_active_count')) is int and result['job_active_count']==0 and result.get('whole_tree_certificate') is False and result.get('replay') is False and result.get('reattach') is False and worker.get('assigned') is True and worker.get('resumed') is True and type(worker.get('exit_code')) is int and result==restart and before==after
for log in result.get('logs',{}).values():
 for stream in ('stdout','stderr'):
  p=R/'contained_compile'/log[stream+'_path'];data=p.read_bytes()
  clean=clean and log[stream+'_overflow'] is False and len(data)==log[stream+'_bytes'] and data.decode('utf-8',errors='replace')==log[stream]
receipt={'scope':'ROOT_ADMITTED_CPU_STUB_BUILD_NO_GPU_LOADER_LINK_NO_RUNTIME','status':'COMPILE_REFUSED' if result['status']=='FAILED' and clean else 'COMPILE_SUCCEEDED' if result['status'] in ('PROCESS_COMPLETED','COMPILER_ROOT_EXITED_CLEANUP_REQUIRED') and clean and worker['exit_code']==0 else 'CLEANUP_OR_STAGE_REFUSED','result':result,'restart':restart,'cleanup_verified':clean,'pins_before':before,'pins_after':after,'hashes_unchanged':before==after,'provider_tests_executed':False,'candidate_runtime_executed':False}
(R/'compile_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({'status':receipt['status'],'cleanup_verified':clean,'worker':worker,'job_active_count':result.get('job_active_count'),'drain':result.get('drain_proof'),'hashes_unchanged':before==after}))

