import hashlib,json,pathlib,subprocess,threading,time
r=pathlib.Path(__file__).resolve().parent;py=r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe'
script=r/'test_independent_directed.py';before=hashlib.sha256(script.read_bytes()).hexdigest()
p=subprocess.Popen([py,'-B',str(r/'pure_import_fence.py'),str(script),'directed3'],cwd=r,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
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
for stream,name in [(p.stdout,'controller.stdout.log'),(p.stderr,'controller.stderr.log')]:
 t=threading.Thread(target=drain,args=(stream,name),daemon=True);t.start();ts.append(t)
timeout=False
while p.poll() is None:
 if time.monotonic()-start>=30 or state['overflow']:timeout=True;p.kill();break
 time.sleep(.02)
p.wait(timeout=3)
for t in ts:t.join(timeout=2)
receipt={'owned_controller_pid':p.pid,'exit_code':p.returncode,'reaped':p.poll() is not None,'timeout':timeout,'capture':state,'readers_joined':not any(t.is_alive() for t in ts),'seconds':time.monotonic()-start,'controller_source_sha_before':before,'controller_source_sha_after':hashlib.sha256(script.read_bytes()).hexdigest(),'scope':'ROOT_ADMITTED_SYNTHETIC_DIRECTED_RECEIPT_ONLY_NATIVE_NETWORK_PROCESS_GUARDS'}
(r/'outer_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt));print((r/'controller.stdout.log').read_text());print((r/'controller.stderr.log').read_text())

