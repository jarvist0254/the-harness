import importlib.util, sys, pathlib, types, unittest, json, io
from datetime import datetime, timezone, timedelta
root=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('inventory_adapter',root/'inventory/device_inventory.py')
mod=importlib.util.module_from_spec(spec);sys.modules['inventory_adapter']=mod;spec.loader.exec_module(mod)
testmod=types.ModuleType('provider_inventory_tests')
exec(compile((root/'inventory/tests.candidate.txt').read_text(encoding='utf-8-sig'),'provider_inventory_tests','exec'),testmod.__dict__)
stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromModule(testmod)
result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
now=datetime(2026,10,4,12,tzinfo=timezone.utc)
def sample(pci='0000:01:00.0',delta=0):
 return {'vendor':'nvidia','tool':'nvidia-smi','tool_version':'fixture','sampled_at_utc':(now+timedelta(seconds=delta)).isoformat(),'exit_code':0,'format':'csv','memory_kind':'DEDICATED','stdout':f'pci.bus_id,name,memory.total,memory.free,memory.used,uuid\n{pci},fixture,8192,4096,4096,GPU-fixture\n'}
cases=[]
for name,s,admission_now in [('future',sample(delta=60),now),('missing_physical_id',sample(pci='N/A'),now),('admission_recheck_stale',sample(),now+timedelta(seconds=60)),('nvidia_8hex_domain',sample(pci='00000000:01:00.0'),now)]:
 inv=mod.normalize_inventory([s],now_utc=now)
 admission=mod.get_admission_snapshot(inv,now_utc=admission_now)
 cases.append({'case':name,'physical_ids':[d['physical_id'] for d in inv['devices']],'eligible_count':len(admission['eligible']),'expected_eligible_count':1 if name=='nvidia_8hex_domain' else 0,'gate_pass':len(admission['eligible'])==(1 if name=='nvidia_8hex_domain' else 0) and (name!='nvidia_8hex_domain' or admission['eligible'][0]['physical_id']=='0000:01:00.0')})
receipt={'provider_tests_run':result.testsRun,'provider_failures':len(result.failures),'provider_errors':len(result.errors),'provider_log':stream.getvalue(),'independent_discriminators':cases,'runtime_execution':False,'hardware_qualification':False}
(root/'inventory_gate_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k!='provider_log'},indent=2))
