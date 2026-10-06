import subprocess,socket,time,json,os
from pathlib import Path
out=Path(r'E:\the_harness\records\rpc_four_worker_20261004')
bin=Path(r'E:\the_harness\records\build_cpu_rpc\bin')
ports=[50072,50073,50074,50075]
workers=[]; handles=[]
result={'qualification':'CPU_ONLY_NOT_GPU_QUALIFICATION','ports':ports,'workers':[],'status':'FAIL'}
started=time.monotonic()
def can_bind(port):
 s=socket.socket()
 try: s.bind(('127.0.0.1',port)); return True
 except OSError: return False
 finally: s.close()
try:
 if not all(can_bind(port) for port in ports): raise RuntimeError('Requested loopback port occupied; no workers launched')
 for port in ports:
  stdout=open(out/f'worker_{port}_stdout.log','w'); stderr=open(out/f'worker_{port}_stderr.log','w'); handles += [stdout,stderr]
  command=[str(bin/'ggml-rpc-server.exe'),'--host','127.0.0.1','--port',str(port),'--device','CPU','--threads','1']
  p=subprocess.Popen(command,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
  workers.append(p); result['workers'].append({'pid':p.pid,'port':port,'command':command})
 (out/'worker_processes.json').write_text(json.dumps(result['workers'],indent=2))
 deadline=time.monotonic()+15
 while time.monotonic()<deadline:
  if any(p.poll() is not None for p in workers): raise RuntimeError('RPC worker exited during startup')
  if all(not can_bind(port) for port in ports): break
  time.sleep(.05)
 else: raise TimeoutError('RPC startup exceeded15seconds')
 command=[str(bin/'rpc_four_worker_smoke.exe')]+[f'127.0.0.1:{p}' for p in ports]
 budget=max(1,60-(time.monotonic()-started))
 client=subprocess.run(command,capture_output=True,text=True,timeout=budget,creationflags=subprocess.CREATE_NO_WINDOW)
 (out/'client_stdout.log').write_text(client.stdout); (out/'client_stderr.log').write_text(client.stderr)
 result.update(client_exit=client.returncode,client_stdout=client.stdout,client_stderr=client.stderr)
 if client.returncode: raise RuntimeError('Four-worker client failed')
 values=json.loads(client.stdout)
 if values.get('values') != [136,312,184,424] or values.get('computed_stages')!=4 or values.get('interworker_tensor_transfers')!=3: raise RuntimeError('Unexpected client results')
 result['status']='PASS'
except Exception as e:
 result.update(error_type=type(e).__name__,error=str(e))
finally:
 for p in workers:
  if p.poll() is None: p.terminate()
 for p in workers:
  try: p.wait(timeout=5)
  except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=5)
 for handle in handles: handle.close()
 result['cleanup']={'owned_workers_closed':all(p.poll() is not None for p in workers), 'worker_exit_codes':[p.returncode for p in workers], 'ports_bindable':{str(port):can_bind(port) for port in ports}}
 if not result['cleanup']['owned_workers_closed'] or not all(result['cleanup']['ports_bindable'].values()): result['status']='FAIL'
 result['wall_seconds']=time.monotonic()-started
 (out/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['status']=='PASS' else 1)
