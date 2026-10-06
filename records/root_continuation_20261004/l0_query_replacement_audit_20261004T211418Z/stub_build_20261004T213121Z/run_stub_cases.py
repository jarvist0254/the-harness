"""Root-admitted CPU-only actual-header fixture, no loader/GPU libraries."""
import hashlib, importlib.util, json, pathlib, re, sys
R=pathlib.Path(__file__).resolve().parent
A=R.parent
T=pathlib.Path(r'E:\the_harness\records\toolchains\level_zero_20261004\runtime_source')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def load(p,name):
    spec=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
assert sha(A/'source.original_untrusted.cpp')=='9f2635be587804c88c2988066142ef4c307d98adc0afc4649422a39ac880b694'
assert sha(A/'actual_header_stub_DRAFT.cpp')=='b551a78647c0deb835edefaab04368e15abf0650998a9d1f657f6c13d7af8427'
assert sha(T/'toolchain_policy_pins.json')=='0cd166bb42856517d9a5cdb1557ff1b01f8ade6f3c273a1face8eb83b1443c20'
tools=read(T/'toolchain_policy_pins.json'); paths={k:pathlib.Path(v['path']) for k,v in tools.items()}
for key,p in paths.items(): assert sha(p)==tools[key]['sha256']
header=pathlib.Path(r'E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h')
assert sha(header)=='c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de'
assert sha(pathlib.Path(sys.executable))==tools['python']['sha256']
build=read(R/'compile_receipt.json'); assert build['status']=='COMPILE_SUCCEEDED' and build['cleanup_verified'] and build['hashes_unchanged']
imports=(R/'pe_imports.raw.txt').read_text()
dlls=re.findall(r'^\s+([A-Za-z0-9_.-]+\.dll)\s*$',imports,re.M)
assert dlls and all(d.lower() in {'kernel32.dll','vcruntime140.dll'} or d.lower().startswith('api-ms-win-crt-') for d in dlls),dlls
assert not re.search(r'LoadLibrary|GetProcAddress|ze_loader|cuda|vulkan|OpenCL|nvcuda',imports,re.I)
exe=R/'stub.exe'
driver=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\compiler_completion_driver_prepare_20261004T181731Z\native_driver.py')
assert sha(driver)=='e4327908e0da6f668ba7ae51cf92fb641bb7c4e02dde019722a863b8217c3c1d'
suite=read(paths['native5receipt']); assert suite['status']=='FIVE_CPU_FIXTURES_PASS' and suite['pins_before']==suite['pins_after']
d=load(driver,'private_stub_native_receipt_validator')
assert [c['case'] for c in suite['cases']]==list(d.CASES)
for c in suite['cases']:
    assert c['controller_exit']==0 and not c['outer_timeout'] and c['reader_joined'] and c['controller_pid_check']['absent']
    assert not c['capture']['overflow'] and not c['capture']['errors']
    d.validate_result(c['case'],c['actual']['result'],c['actual']['restart'],'compiler_root_exited_zero')
files=list(paths.values())+[header,driver,exe,A/'source.original_untrusted.cpp',A/'actual_header_stub_DRAFT.cpp',R/'pe_imports.raw.txt',R/'compile_receipt.json',pathlib.Path(__file__)]
before={str(p):sha(p) for p in files}
m=load(paths['supervisor'],'private_l0_cpu_stub_supervisor'); load(paths['compiler_adapter'],'private_l0_cpu_stub_adapter').install(m)
def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('duplicate key')
        result[key]=value
    return result
cases=[]
for label,args in [('normal',[]),('init_error',['init_error']),('duplicate_root',['duplicate_root'])]:
    out=R/('runtime_'+label)
    manifest={'version':1,'run_id':'l0_cpu_stub_'+label,'workers':[{'worker_id':'stub','argv':[str(exe)]+args,'executable_sha256':sha(exe),'cwd':str(R)}],
              'deadline_seconds':10,'startup_seconds':2,'log_limit_bytes':131072,'containment_policy':'kill_on_close'}
    result=m.run_workers(manifest,str(out)); restart=m.restart_receipt(str(out),manifest['run_id'])
    worker=result.get('workers',[{}])[0]; logs=result.get('logs',{}).get('stub',{})
    clean=result==restart and result.get('drain_proof')=='CLEANUP' and type(result.get('job_active_count')) is int and result['job_active_count']==0
    clean=clean and worker.get('assigned') is True and worker.get('resumed') is True and type(worker.get('exit_code')) is int
    raw={}
    for stream in ['stdout','stderr']:
        p=out/logs[stream+'_path']; data=p.read_bytes(); raw[stream]=data.decode('utf-8',errors='strict')
        clean=clean and not logs[stream+'_overflow'] and logs[stream+'_bytes']==len(data) and raw[stream]==logs[stream]
    try:
        parsed=json.loads(raw['stdout'],object_pairs_hook=unique,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite '+x)))
        parse={'valid':True,'value':parsed}
    except (ValueError,UnicodeError) as error:
        parse={'valid':False,'exception':str(error)}
    counters=json.loads(raw['stderr'],object_pairs_hook=unique)
    cases.append({'case':label,'result':result,'restart':restart,'cleanup_verified':clean,'strict_stdout_json':parse,'independent_stub_counters':counters,
                  'raw_stdout_sha256':hashlib.sha256(raw['stdout'].encode()).hexdigest(),'raw_stderr_sha256':hashlib.sha256(raw['stderr'].encode()).hexdigest()})
after={str(p):sha(p) for p in files}
report={'scope':'ACTUAL_HEADER_LOCAL_CPU_STUB_NOT_HARDWARE','PE_imports_inspected_before_execution':dlls,'pins_before':before,'pins_after':after,
        'hashes_unchanged':before==after,'all_cases_cleanup_verified':all(c['cleanup_verified'] for c in cases),'cases':cases,
        'provider_tests_executed':False,'real_LevelZero_or_GPU_driver_calls':False,'source_edited':False}
with (R/'runtime_receipt.json').open('x',encoding='utf-8') as output:json.dump(report,output,indent=2)
print(json.dumps({'hashes_unchanged':before==after,'cleanup_verified':report['all_cases_cleanup_verified'],'cases':[{'case':c['case'],'pid':c['result']['workers'][0]['pid'],'exit_code':c['result']['workers'][0]['exit_code'],'strict_json_valid':c['strict_stdout_json']['valid'],'counters':c['independent_stub_counters']} for c in cases]},indent=2))
assert report['hashes_unchanged'] and report['all_cases_cleanup_verified']
