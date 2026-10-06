from pathlib import Path
import hashlib,json,sys
p=Path(r'E:\the_harness\records\factory_runs\20261004\muse_qwen_linux_dmabuf_audit_20261004T190700Z')
files=['run_muse_job.py','prompt.txt','output_schema.json','source.snapshot.cpp','tests.snapshot.txt','spec.snapshot.txt']
meta={f:{'sha256':hashlib.sha256((p/f).read_bytes()).hexdigest().upper(),'bytes':(p/f).stat().st_size} for f in files}
for k in ['C:\\Users\\thoma\\AppData\\Local\\Programs\\muse\\muse-bin-1.4.2-R4684.1.exe','C:\\Users\\thoma\\AppData\\Local\\Programs\\Python\\Python310\\python.exe']:
 q=Path(k); meta[str(q)]={'sha256':hashlib.sha256(q.read_bytes()).hexdigest().upper(),'bytes':q.stat().st_size}
a={'authority':'ROOT-delegated source-only adversarial review of supplied Qwen Intel/DMA-BUF candidate','provider':'Muse 1.4.2 Meta','source_execution':False,'compile_or_native':False,'user_live_muse_session_touched':False,'max_deadline_seconds':300,'max_capture_bytes':2097152,'inputs':meta,'result_usage':'record provider usage only if returned; otherwise UNKNOWN'}
(p/'ROOT_MUSE_AUDIT_ADMISSION.json').write_text(json.dumps(a,indent=2),encoding='utf-8')
print(json.dumps({'folder':str(p),'admission_sha256':hashlib.sha256((p/'ROOT_MUSE_AUDIT_ADMISSION.json').read_bytes()).hexdigest().upper(),'pins':meta},indent=2))
