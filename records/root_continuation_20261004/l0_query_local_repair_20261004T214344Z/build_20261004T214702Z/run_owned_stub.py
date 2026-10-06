import hashlib,json,pathlib,subprocess,threading,time
r=pathlib.Path(__file__).resolve().parent;py=r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe'
script=r/'run_stub_cases.py';before=hashlib.sha256(script.read_bytes()).hexdigest()
p=subprocess.Popen([py,'-B',str(script)],cwd=r,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
state={'bytes':{},'overflow':[],'errors':[]};ts=[];start=time.monotonic()
def drain(pipe,name):
 count=0
 try:
  with (r/name).open('xb') as f:
   while True:
    b=pipe.read(8192)
    if not b:break
    keep=max(0,min(len(b),262144-count));f.write(b[:keep]);count+=len(b)
    if count>262144:state['overflow'].append(name)
 except Exception as ex:state['errors'].append(str(ex))
 finally:pipe.close();state['bytes'][name]=count
for stream,name in [(p.stdout,'runtime_controller.stdout.log'),(p.stderr,'runtime_controller.stderr.log')]:
 t=threading.Thread(target=drain,args=(stream,name),daemon=True);t.start();ts.append(t)
timeout=False
while p.poll() is None:
 if time.monotonic()-start>=60 or state['overflow']:timeout=True;p.kill();break
 time.sleep(.02)
p.wait(timeout=3)
for t in ts:t.join(timeout=2)
receipt={'owned_controller_pid':p.pid,'exit_code':p.returncode,'reaped':p.poll() is not None,'timeout':timeout,'capture':state,'readers_joined':not any(t.is_alive() for t in ts),'seconds':time.monotonic()-start,'controller_source_sha_before':before,'controller_source_sha_after':hashlib.sha256(script.read_bytes()).hexdigest(),'scope':'Root-admitted CPU-only local actual-header stub cases, no real Level Zero/GPU loader or API calls'}
(r/'runtime_outer_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt));print((r/'runtime_controller.stdout.log').read_text());print((r/'runtime_controller.stderr.log').read_text())
