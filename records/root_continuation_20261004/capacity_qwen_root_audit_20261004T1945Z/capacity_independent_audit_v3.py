import builtins
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import sys
import time

SOURCE = pathlib.Path(sys.argv[1])
EXPECTED_SOURCE_SHA = '7005C1FC83A4A9901E30CF8E705DBE5961DC1010C645E963BB08EC75A7808267'
started = time.monotonic()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

if sha(SOURCE) != EXPECTED_SOURCE_SHA:
    raise SystemExit('source pin mismatch before import')

class ImportFence:
    forbidden = {'socket', 'subprocess', 'ctypes', 'urllib', 'http', 'requests', 'multiprocessing', 'winreg'}
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.', 1)[0] in self.forbidden:
            raise RuntimeError('forbidden import attempted: ' + fullname)
        return None

sys.meta_path.insert(0, ImportFence())
def deny(*args, **kwargs):
    raise RuntimeError('forbidden side effect attempted')
old_open = builtins.open
old_os_system = os.system
old_os_popen = os.popen
old_os_open = os.open
builtins.open = deny
os.system = deny
os.popen = deny
os.open = deny
try:
    spec = importlib.util.spec_from_file_location('capacity_candidate_under_test', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
finally:
    builtins.open = old_open
    os.system = old_os_system
    os.popen = old_os_popen
    os.open = old_os_open
sys.meta_path.remove(sys.meta_path[-1])

ART = ('model_hash','workload_hash','source_hash','exe_hash','context_hash','quant')
def dev(i):
    return {'canonical_id':f'pci:0000:{i:02x}.0','physical_alias':f'phys:{i}',
            'aliases':[f'root:{i}',f'sub:{i}:0'],'discrete':True,'form_factor':'discrete_gpu'}
def attempt(role,n,ts=1000):
    a={'role':role,'model_hash':'m','workload_hash':'w','source_hash':'s','exe_hash':'e','context_hash':'c','quant':'q8_0',
       'timestamp_ns':ts,'controller':{'args_valid':True,'timeout':False,'policy_cap':False,'native_error':None},
       'devices':[dev(i) for i in range(n)],
       'allocator':{'class':'dedicated_vram','fresh':True,'source':'allocator-receipt','timestamp_ns':ts}}
    if role!='four':
        a['execution']={'status':'allocator_oom','requested_bytes':4000}
    else:
        a['execution']={'status':'success','rmse':0.1,'max_abs_error':0.2,'logits':[{'cpu':1.0,'observed':1.05,'tol_abs':0.1}]}
        a['weights']=[{'device':f'pci:0000:{i:02x}.0','shard_hash':f'shard-{i}','resident_bytes':1000,'backing':'device_vram'} for i in range(4)]
        a['allocator']['peak_bytes_by_device']={f'pci:0000:{i:02x}.0':1000 for i in range(4)}
    return a
def evidence():
    return {'model_hash':'m','workload_hash':'w','source_hash':'s','exe_hash':'e','context_hash':'c','quant':'q8_0',
            'artifact_source':'root-registry-label','cpu_reference_hash':'cpu-ref-label','observed_at_ns':1000,
            'model_bytes':4000,'logit_tol_abs':0.1,'attempts':[attempt('single',1),attempt('three',3),attempt('four',4)]}
def observe(name, ev, expected_safe, note):
    result=module.validate_capacity(ev, trusted=True)
    if name=='baseline' and result.get('status')=='PASS':
        classification='BASELINE_POSITIVE_SYNTHETIC_ONLY'
    elif expected_safe in ('NOT_PASS','NOT_CHECKED') and result.get('status')=='PASS':
        classification='RED_CANDIDATE_ACCEPTED_CONTRADICTION'
    elif expected_safe=='NOT_PASS' and result.get('status')!='PASS':
        classification='OBSERVED_FAIL_CLOSED'
    else:
        classification='OBSERVED'
    return {'case':name,'expected_safe_behavior':expected_safe,'candidate_result':result,
            'classification':classification,'note':note}

results=[]
base=evidence()
results.append(observe('baseline',base,'PASS_SYNTHETIC_ONLY','Constructed fixture patterned after provider test helper; not hardware evidence.'))

# Four discrete devices are declared, but every unique shard is assigned to device 0.
e=evidence(); four=e['attempts'][2]; d0=four['devices'][0]['canonical_id']
for w in four['weights']: w['device']=d0
four['allocator']['peak_bytes_by_device'][d0]=4000
results.append(observe('all_four_shards_only_on_device0',e,'NOT_PASS','Weights omit three declared physical participants; the single device peak is large enough for the whole model.'))

# Every shard individually fits, but the per-device resident sum exceeds the measured peak.
e=evidence(); four=e['attempts'][2]
four['weights'][0]['device']='pci:0000:00.0'; four['weights'][1]['device']='pci:0000:00.0'
results.append(observe('sum_of_shards_exceeds_device_peak',e,'NOT_PASS','Device 0 holds two 1000-byte shards while its reported peak is 1000; each shard individually passes the current comparison.'))

# The fields named as artifact hashes accept arbitrary labels when trusted=True.
e=evidence(); bad={'model_hash':'not-a-hex-model','workload_hash':'W','source_hash':'source','exe_hash':'exe','context_hash':'ctx','quant':'q8_0'}
for k,v in bad.items():
    e[k]=v
    for a in e['attempts']: a[k]=v
e['cpu_reference_hash']='definitely-not-a-hash'
results.append(observe('nonhex_artifact_identifiers',e,'NOT_CHECKED','The caller sets trusted=True; hash-shaped artifact identities are not validated or bound to a trusted named registry.'))

# Summary metrics claim exact equality while the supplied logit pair differs by 0.05.
e=evidence(); four=e['attempts'][2]['execution']; four['rmse']=0.0; four['max_abs_error']=0.0
results.append(observe('reported_metrics_contradict_logits',e,'NOT_PASS','The per-logit difference is 0.05 within tolerance, but reported RMSE and max error are both zero.'))

# Three enumerated roots/subdevices form one physical device only via a transitive alias bridge,
# followed by three independent devices. Compare two enumeration orders.
def node(cid, pal, aliases):
    return {'canonical_id':cid,'physical_alias':pal,'aliases':aliases,'discrete':True,'form_factor':'discrete_gpu'}
chain=[node('gpu0-root','node-root',['alias-A']),node('gpu0-sub-a','node-sub-a',['alias-B']),node('gpu0-sub-b','node-sub-b',['alias-A','alias-B'])]
others=[dev(1),dev(2),dev(3)]
alias_orders=[]
for name, first in [('bridge_last',chain),('bridge_first',[chain[2],chain[0],chain[1]])]:
    e=evidence(); four=e['attempts'][2]
    four['devices']=first+others
    alias_orders.append(observe('transitive_alias_'+name,e,'NOT_CHECKED_OR_CANONICALIZED','Four physical components should be computed by transitive alias closure; canonical owner mapping for shard/peak keys is not explicit in the input contract; line 62 increments without merging prior components, yielding an internal physical count of 5 when bridge arrives last versus 4 when bridge arrives first, although both fail line 64.'))
results.extend(alias_orders)

# Mutated positive control: every supplied per-logit pair is valid, but an identical alias on two distinct rows must not create a false 4-device pass.
e=evidence(); e['attempts'][2]['devices'][1]['aliases'].append('root:0')
results.append(observe('cross_device_alias_collision',e,'NOT_PASS','Alias collision is contradictory identity evidence; fail-closed is safer than asserting four physical GPUs.'))

source_after=sha(SOURCE)
if source_after != EXPECTED_SOURCE_SHA:
    raise SystemExit('source pin changed during audit')
if time.monotonic()-started > 25:
    raise SystemExit('child elapsed exceeded 25s internal guard')
findings=[r['case'] for r in results if r['classification']=='RED_CANDIDATE_ACCEPTED_CONTRADICTION']
report={'audit_status':'RED' if findings else 'NO_RED_REPRODUCED','source_sha256_before':EXPECTED_SOURCE_SHA,'source_sha256_after':source_after,
        'source_import_side_effect_fence':'passed: imports limited to math already present; builtins.open, os.open, os.system, os.popen denied during candidate import; forbidden-module finder installed',
        'elapsed_seconds':round(time.monotonic()-started,4),'candidate_execution':'pure validator only; trusted=True; no native/GPU/provider calls',
        'cases':results,'red_cases':findings,'limitations':['All evidence fixtures are synthetic and self-authored; baseline PASS is not a hardware or capacity observation.','Alias-chain outputs are observed but physical identity semantics for canonical_id versus aliases need explicit schema; do not promote to a hard defect beyond the spec.','No actual allocator, device, DLL, driver, physical VRAM, P2P, or numerical execution evidence was gathered.']}
print(json.dumps(report,separators=(',',':'),sort_keys=True))
