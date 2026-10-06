"""Root-reviewed inspection-only runner. No fake executable or real GPU API execution."""
import argparse,ast,hashlib,importlib.util,json,pathlib,re,sys
from datetime import datetime,timezone
ROOT=pathlib.Path(r"E:\the_harness\records\root_continuation_20261004\l0_peer_timeout_local_repair_20261004T221307Z")
PINS={'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\cpu_stub_controller_phase_pinned.py': '5e9b5964bf0805fd9d91a48ff65f23e84d85c63b96d4ba1293a9a8bd63ee3c4d', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\SYMBOL_INSPECTION_PROPOSAL.json': 'cc7b9f0145f1f289bed41fe08dcfb442a95ba2f86a3529422fdbc10bed0ab883', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\peer_copy_local.cpp': '284e6109f1d32db945ab7719bb77d9a1fc734887c9ebe5068bebc4ac0eef9f59', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\fake_level_zero_local.cpp': '96e2f0df7108f1ce31a540c18ae3f50f09b97fa54c5628f8556b86873cbe62d2', 'E:\\the_harness\\records\\toolchains\\level_zero_20261004\\sdk\\include\\level_zero\\ze_api.h': 'c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\peer_copy_local.o': '888754880338f9752254dab8a6173239cff630f366716e11f8a4c7705efa6b80', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\fake_level_zero_local.o': 'ab9ec1703fe507cb8f043b51646f79a92f640f02e02627cbe4f8b0d786eac1f1', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\peer_copy_cpu_fake': '1b889f1f11884b8b9d0cd92fb7badd3c6468035cdea8a3a4ac358f6535e27c40', 'C:\\Users\\thoma\\AppData\\Local\\Programs\\Python\\Python310\\python.exe': '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260', 'C:\\Windows\\System32\\wsl.exe': '7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\stub_build_20261004T222818Z\\04_no_level_zero_dependency.stdout.bin': '15f323280163b4b3921b29156ec771181cfda37847227784adf20b605ddaf7e5', 'E:\\the_harness\\records\\root_continuation_20261004\\l0_peer_timeout_local_repair_20261004T221307Z\\stub_build_20261004T222818Z\\04_no_level_zero_dependency.receipt.json': '140dc0b7ee3670d927b9bb275e1c5e047d7dad87c1c8b006807730a0187a70eb'}
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate JSON key')
  d[k]=v
 return d
def parse(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--admission',required=True);ap.add_argument('--admission-sha256',required=True);args=ap.parse_args()
 admission=pathlib.Path(args.admission).resolve(strict=True)
 if admission.parent!=ROOT.resolve(strict=True) or not re.fullmatch('[0-9a-f]{64}',args.admission_sha256) or sha(admission)!=args.admission_sha256:raise SystemExit('refuse admission confinement/hash')
 a=parse(admission)
 if a.get('scope')!='CPU_FAKE_SYMBOL_INSPECTION_ONLY' or a.get('admitted') is not True or a.get('runner_sha256')!=sha(__file__) or a.get('input_pins')!=PINS:raise SystemExit('refuse admission bindings')
 before={p:sha(p) for p in PINS}
 if before!=PINS:raise SystemExit('refuse input pin mismatch')
 helper_path=ROOT/'cpu_stub_controller_phase_pinned.py';tree=ast.parse(helper_path.read_bytes())
 if any(not isinstance(x,(ast.Import,ast.ImportFrom,ast.Assign,ast.FunctionDef,ast.If)) for x in tree.body):raise SystemExit('refuse helper top-level changed')
 spec=importlib.util.spec_from_file_location('private_pinned_inspection_capture',helper_path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 proposal=parse(ROOT/'SYMBOL_INSPECTION_PROPOSAL.json')
 if proposal.get('stream_cap_bytes')!=131072 or proposal.get('outer_seconds')!=12 or helper.CAP!=131072:raise SystemExit('refuse capture policy')
 # Bind retained actual dynamic receipt/raw stream, not a descriptive claim.
 dynrec=parse(ROOT/'stub_build_20261004T222818Z/04_no_level_zero_dependency.receipt.json')
 dynpath=ROOT/'stub_build_20261004T222818Z/04_no_level_zero_dependency.stdout.bin'
 if dynrec.get('returncode')!=0 or not helper.capture_complete(dynrec) or dynrec.get('stdout_sha256')!=sha(dynpath):raise SystemExit('refuse dynamic inspection receipt')
 needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',dynpath.read_text(encoding='utf-8'))
 if not needed or set(needed)-{'libstdc++.so.6','libgcc_s.so.1','libc.so.6','libm.so.6'}:raise SystemExit('refuse dynamic dependencies')
 folder=ROOT/('symbol_inspection_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));folder.mkdir(exist_ok=False)
 result=None;failure=None;symbol_result=None
 try:
  result=helper.run('filtered_symbols',proposal['argv'],12,folder,1)
  if result['returncode']!=0 or not helper.capture_complete(result):raise ValueError('refused capture/exit')
  text=pathlib.Path(result['stdout_path']).read_text(encoding='utf-8',errors='strict')
  called=set(re.findall(r'\b(ze[A-Z][A-Za-z0-9_]*)\s*\(', (ROOT/'peer_copy_local.cpp').read_text(encoding='utf-8')))
  if not called:raise ValueError('empty called API set')
  defined=set();bad=[]
  for line in text.splitlines():
   fields=line.split()
   if len(fields)<8 or not fields[0].endswith(':'):continue
   name=fields[7].split('@')[0];ndx=fields[6]
   if ndx!='UND' and name in called:defined.add(name)
   if ndx=='UND' and (name.startswith('ze') or name in {'dlopen','dlsym','dlmopen'}):bad.append(name)
  rows=re.findall(r'^FULL_TABLE_ROWS ([0-9]+)$',text,re.MULTILINE)
  if len(rows)!=1 or int(rows[0])<=0 or called-defined or bad:raise ValueError('refused symbol completeness/imports')
  symbol_result={'called_level_zero':sorted(called),'internally_defined':sorted(defined),'forbidden_undefined':bad,'dynamic_dependencies':needed,'full_row_count_diagnostic_only':int(rows[0])}
 except BaseException as error:failure=type(error).__name__+': '+str(error)
 after={p:sha(p) for p in PINS}
 if after!=before:failure=failure or 'input pins changed'
 if sha(admission)!=args.admission_sha256 or sha(__file__)!=a['runner_sha256']:failure=failure or 'admission/runner pin changed'
 receipt={'scope':'CPU_FAKE_SYMBOL_INSPECTION_ONLY','status':'PASS' if failure is None else 'REFUSED','failure':failure,'result':result,'symbols':symbol_result,'pins_before':before,'pins_after':after,'runner_sha256':sha(__file__),'admission_sha256':args.admission_sha256,'executable_executed':False,'physical_transfer_qualified':False,'old_overflow_refusal_preserved':True}
 (folder/'INSPECTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps({'folder':str(folder),'status':receipt['status'],'failure':failure,'symbol_result':symbol_result,'process':result},indent=2));return 0 if failure is None else 1
if __name__=='__main__':raise SystemExit(main())
