"""Bounded owned controller for admitted pure ledger tests, no candidate native access."""
import hashlib,json,pathlib,subprocess,sys,threading,time
R=pathlib.Path(__file__).resolve().parent
C=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_ledger_storage_repair_20261004T195014Z\grok_ledger_storage_high')
PY=pathlib.Path(r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[C/'source.grok_untrusted.py',C/'tests_source.grok_untrusted.py',R/'test_independent_same17_adapted.py',R/'test_additional_storage_and_legal_transition.py',R/'pure_import_fence.py',pathlib.Path(__file__),PY]
before={str(p):sha(p) for p in files}
assert before[str(files[0])]=='e44e86db99225b95cb9c9b63a41987d978e692eb0efc3f431741e2adf28833df'
assert before[str(files[1])]=='938739185fe5e6e12d115639160a228a6f917a20a18bd7368bb16231ccdf7869'
assert before[str(PY)]=='3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
runs=[]
for label,script in [('same17','test_independent_same17_adapted.py'),('additional3','test_additional_storage_and_legal_transition.py')]:
 start=time.monotonic();p=subprocess.Popen([str(PY),'-B',str(R/'pure_import_fence.py'),str(R/script),label],cwd=R,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
 state={'bytes':{},'overflow':[],'errors':[]};threads=[]
 def capture(pipe,name):
  total=0
  try:
   with (R/name).open('xb') as f:
    while True:
     b=pipe.read(8192)
     if not b:break
     keep=max(0,min(len(b),2*1024*1024-total));f.write(b[:keep]);total+=len(b)
     if total>2*1024*1024:state['overflow'].append(name);break
  except Exception as ex:state['errors'].append(str(ex))
  finally:pipe.close();state['bytes'][name]=total
 for stream,name in [(p.stdout,label+'.stdout.raw.log'),(p.stderr,label+'.stderr.raw.log')]:
  t=threading.Thread(target=capture,args=(stream,name),daemon=True);t.start();threads.append(t)
 timeout=False
 while p.poll() is None:
  if time.monotonic()-start>=30 or state['overflow']:timeout=True;p.kill();break
  time.sleep(.01)
 p.wait(timeout=3)
 for t in threads:t.join(timeout=2)
 runs.append({'label':label,'pid':p.pid,'exit_code':p.returncode,'reaped':p.poll() is not None,'owned_process_handle_signaled':p.poll() is not None,'seconds':time.monotonic()-start,'timeout':timeout,'capture':state,'readers_joined':not any(t.is_alive() for t in threads),'native_fence':json.loads((R/(label+'.fence.json')).read_text()) if (R/(label+'.fence.json')).exists() else 'NOT_CHECKED'})
after={str(p):sha(p) for p in files}
receipt={'scope':'ROOT_ADMITTED_EXACT_CANDIDATE_INDEPENDENT_PURE_QA_ONLY','runs':runs,'pins_before':before,'pins_after':after,'hashes_unchanged':before==after,'provider_tests_executed':False,'native_gpu_provider_calls':False}
(R/'execution_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
