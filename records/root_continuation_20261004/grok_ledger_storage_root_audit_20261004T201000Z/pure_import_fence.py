import json,pathlib,runpy,sys
ROOT=pathlib.Path(__file__).resolve().parent
script=pathlib.Path(sys.argv[1]).resolve();label=sys.argv[2]
assert script.parent==ROOT
traps=[]
def fence(event,args):
 if event in ('subprocess.Popen','os.system','os.posix_spawn','os.spawn','ctypes.dlopen','ctypes.dlsym') or event.startswith('socket.'):
  traps.append(event);raise AssertionError('Native/process/network action denied')
sys.addaudithook(fence)
try:
 sys.argv=[str(script)];runpy.run_path(str(script),run_name='__main__')
finally:
 (ROOT/(label+'.fence.json')).write_text(json.dumps({'audit_denied_events':traps,'scope':'Pure synthetic candidate only; native dependency import guard is in independent exact17 module'}))
