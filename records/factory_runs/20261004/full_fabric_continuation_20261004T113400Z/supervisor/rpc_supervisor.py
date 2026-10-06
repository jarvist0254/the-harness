import os,sys,json,hashlib,time,socket,tempfile,signal,subprocess,ctypes,ctypes.wintypes,re,unittest
from enum import Enum
from pathlib import Path
from typing import List,Dict,Optional,Callable

VERSION="1"
MAX_LOG_BYTES=128*1024
SAFE_DEV=re.compile(r'^[A-Za-z0-9_:\-\.]+$')

class State(Enum):
    NEW="NEW";STARTING="STARTING";READY="READY";FAILED="FAILED";CANCELLED="CANCELLED";COMPLETED="COMPLETED"

def sha256_file(p:str)->str:
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(65536),b''):h.update(c)
    return h.hexdigest()

def validate_manifest(m:dict,output_root:str)->None:
    if m.get('version')!=VERSION:raise ValueError('bad version')
    w=m.get('workers',[])
    if len(w)!=4:raise ValueError('need 4 workers')
    pids=set();ports=set();dl=m.get('deadline_seconds',0);su=m.get('startup_seconds',0)
    if not(1<=dl<=300):raise ValueError('deadline OOB')
    if not(1<=su<=30):raise ValueError('startup OOB')
    orp=Path(output_root).resolve()
    if not orp.is_dir():raise ValueError('output_root missing')
    for wk in w:
        pid=wk.get('physical_id');prt=wk.get('port');bp=wk.get('binary_absolute_path');bh=wk.get('binary_sha256');dv=wk.get('backend_device')
        if pid in pids:raise ValueError('dup phys')
        pids.add(pid)
        if prt in ports:raise ValueError('dup port')
        ports.add(prt)
        if not(1024<=prt<=65535):raise ValueError('port OOB')
        if not os.path.isfile(bp):raise ValueError('bin missing')
        if sha256_file(bp)!=bh:raise ValueError('hash mismatch')
        if not SAFE_DEV.match(str(dv)):raise ValueError('unsafe dev chars')
    op=Path(m.get('output_root','')).resolve()
    try:op.relative_to(orp)
    except ValueError:raise ValueError('output outside root')

def tcp_ready(port:int)->bool:
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(1.0)
        r=s.connect_ex(('127.0.0.1',port));s.close();return r==0
    except:return False

def atomic_json(path:Path,data:dict)->None:
    raw=json.dumps(data).encode('utf-8')
    if len(raw)>MAX_LOG_BYTES:raise ValueError('payload >128KiB')
    fd,tmp=tempfile.mkstemp(dir=str(path.parent))
    try:
        os.write(fd,raw);os.fsync(fd);os.close(fd)
        os.replace(tmp,str(path))
    except:
        os.close(fd) if not os.get_inheritable(fd) else None
        try:os.unlink(tmp)
        except:pass
        raise

class Journal:
    def __init__(self,p:Path):self.p=p;self.f=open(p,'a')
    def commit(self,ev:dict):ev['ts']=time.time();self.f.write(json.dumps(ev)+'\n');self.f.flush();os.fsync(self.f.fileno())
    def close(self):self.f.close()

class Containment:
    def assign(self,pid:int)->bool:raise NotImplementedError
    def teardown(self)->None:raise NotImplementedError

if sys.platform=='win32':
    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_=[('BasicLimitInformation',ctypes.c_byte*48),('IoInfo',ctypes.c_byte*48),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
    class WinContainment(Containment):
        def __init__(self):
            self.job=None
            kernel32=ctypes.windll.kernel32
            self.CreateJobObjectW=kernel32.CreateJobObjectW;self.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p];self.CreateJobObjectW.restype=ctypes.wintypes.HANDLE
            self.SetInformationJobObject=kernel32.SetInformationJobObject;self.SetInformationJobObject.argtypes=[ctypes.wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,ctypes.wintypes.DWORD];self.SetInformationJobObject.restype=ctypes.wintypes.BOOL
            self.AssignProcessToJobObject=kernel32.AssignProcessToJobObject;self.AssignProcessToJobObject.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.HANDLE];self.AssignProcessToJobObject.restype=ctypes.wintypes.BOOL
            self.CloseHandle=kernel32.CloseHandle;self.CloseHandle.argtypes=[ctypes.wintypes.HANDLE];self.CloseHandle.restype=ctypes.wintypes.BOOL
            self.job=self.CreateJobObjectW(None,None)
            if not self.job:raise RuntimeError('CreateJobObjectW failed')
            info=JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            ctypes.memset(ctypes.byref(info),0,ctypes.sizeof(info))
            ctypes.cast(ctypes.byref(info),ctypes.POINTER(ctypes.c_uint32))[0]=0x2000
            if not self.SetInformationJobObject(self.job,9,ctypes.byref(info),ctypes.sizeof(info)):
                self.CloseHandle(self.job);raise RuntimeError('SetInformationJobObject failed')
        def assign(self,pid:int)->bool:
            PROCESS_ALL_ACCESS=0x1F0FFF;ph=ctypes.windll.kernel32.OpenProcess(PROCESS_ALL_ACCESS,False,pid)
            if not ph:return False
            ok=self.AssignProcessToJobObject(self.job,ph);ctypes.windll.kernel32.CloseHandle(ph);return bool(ok)
        def teardown(self):
            if self.job:self.CloseHandle(self.job);self.job=None
else:
    class PosixContainment(Containment):
        def __init__(self):self.pgid:Optional[int]=None
        def assign(self,pid:int)->bool:self.pgid=pid;return True
        def teardown(self):
            if self.pgid:
                try:os.killpg(self.pgid,signal.SIGKILL)
                except ProcessLookupError:pass
                self.pgid=None

class FakeLauncher:
    def __init__(self,fail_ports:set=None,hang_ports:set=None):self.fail=fail_ports or set();self.hang=hang_ports or set();self.procs=[]
    def launch(self,args,log_path,new_session)->object:
        port=int(args[args.index('--port')+1])
        if port in self.fail:raise OSError('fake fail')
        code='import time,socket,sys\n'
        if port not in self.hang:
            code+='s=socket.socket();s.bind((\'127.0.0.1\','+str(port)+'));s.listen(1)\n'
        code+='while True:\n try:time.sleep(0.1)\n except:break\n'
        p=subprocess.Popen([sys.executable,'-c',code],stdout=open(log_path,'wb'),stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0) if new_session else 0)
        self.procs.append(p);return p

class Supervisor:
    def __init__(self,manifest:dict,output_root:str,launcher:Callable=None):
        self.manifest=manifest;self.output_root=Path(output_root).resolve()
        self.run_id=manifest.get('run_id',hex(int(time.time()*1000)))
        self.deadline=manifest['deadline_seconds'];self.startup=manifest['startup_seconds']
        self.state=State.NEW;self.workers=[];self.containment=Containment.__new__(WinContainment if sys.platform=='win32' else PosixContainment)
        if isinstance(self.containment,WinContainment):self.containment.__init__()
        elif isinstance(self.containment,PosixContainment):self.containment.__init__()
        self.journal=Journal(self.output_root/'journal.jsonl')
        self.launcher=launcher;self.start_time=0.0
    def run(self)->State:
        rd=self.output_root/self.run_id
        if rd.exists():raise FileExistsError('run dir exists')
        rd.mkdir(parents=True);self.run_dir=rd
        self.journal.commit({'event':'start','run_id':self.run_id})
        self.state=State.STARTING;self.start_time=time.monotonic()
        try:
            for wk in self.manifest['workers']:
                lp=rd/f"worker_{wk['id']}.log"
                args=[wk['binary_absolute_path'],'--host','127.0.0.1','--port',str(wk['port']),'--device',wk['backend_device']]
                lf=self.launcher if self.launcher else subprocess
                ns=sys.platform!='win32'
                try:p=lf.launch(args,str(lp),ns) if self.launcher else lf.Popen(args,stdout=open(lp,'wb'),stderr=subprocess.STDOUT,start_new_session=ns)
                except Exception as e:self._fail_all();self.state=State.FAILED;return self.state
                if not self.containment.assign(p.pid):p.kill();self._fail_all();self.state=State.FAILED;return self.state
                self.workers.append({'proc':p,'port':wk['port'],'id':wk['id']})
            deadline_t=self.start_time+self.startup
            while time.monotonic()<deadline_t:
                if all(w['proc'].poll() is None and tcp_ready(w['port']) for w in self.workers):
                    self.state=State.READY;break
                time.sleep(0.05)
            if self.state!=State.READY:self._fail_all();self.state=State.FAILED;return self.state
            self.journal.commit({'event':'ready'})
            while time.monotonic()-self.start_time<self.deadline:
                if any(w['proc'].poll() is not None for w in self.workers):self._fail_all();self.state=State.FAILED;return self.state
                time.sleep(0.1)
            self.state=State.COMPLETED
        except Exception:self._fail_all();self.state=State.FAILED
        finally:self.teardown();self.journal.commit({'event':'end','state':self.state.value});self.journal.close()
        return self.state
    def cancel(self):self.state=State.CANCELLED;self.teardown()
    def _fail_all(self):
        for w in self.workers:
            if w['proc'].poll() is None:
                try:w['proc'].kill()
                except:pass
    def teardown(self):
        self._fail_all();self.containment.teardown()
    def restart_receipt(self)->dict:
        return {'run_id':self.run_id,'previous_state':'UNKNOWN_INTERRUPTED','note':'no reattach by stale PID'}

class TestSupervisor(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp();self.root=Path(self.tmp)/'out';self.root.mkdir()
        self.bin=Path(self.tmp)/'fake_worker.exe'
        with open(self.bin,'wb') as f:f.write(b'fakebinarycontent')
        self.bhash=sha256_file(str(self.bin))
        self.base={'version':VERSION,'run_id':'test-run','deadline_seconds':5,'startup_seconds':3,'output_root':str(self.root),'workers':[
            {'id':i,'physical_id':f'phys{i}','binary_absolute_path':str(self.bin),'binary_sha256':self.bhash,'backend_device':f'DEV{i}','port':10000+i} for i in range(4)]}
    def tearDown(self):
        import shutil;shutil.rmtree(self.tmp,ignore_errors=True)
    def test_valid_manifest(self):validate_manifest(self.base,str(self.root))
    def test_dup_physical(self):
        m=json.loads(json.dumps(self.base));m['workers'][1]['physical_id']='phys0'
        with self.assertRaises(ValueError):validate_manifest(m,str(self.root))
    def test_dup_port(self):
        m=json.loads(json.dumps(self.base));m['workers'][1]['port']=10000
        with self.assertRaises(ValueError):validate_manifest(m,str(self.root))
    def test_remote_port(self):
        m=json.loads(json.dumps(self.base));m['workers'][0]['port']=80
        with self.assertRaises(ValueError):validate_manifest(m,str(self.root))
    def test_bad_hash(self):
        m=json.loads(json.dumps(self.base));m['workers'][0]['binary_sha256']='0'*64
        with self.assertRaises(ValueError):validate_manifest(m,str(self.root))
    def test_unsafe_device(self):
        m=json.loads(json.dumps(self.base));m['workers'][0]['backend_device']='DEV;rm -rf /'
        with self.assertRaises(ValueError):validate_manifest(m,str(self.root))
    def test_output_outside_root(self):
        m=json.loads(json.dumps(self.base));m['output_root']='/tmp/other'
        with self.assertRaises(ValueError):validate_manifest(m,str(self.root))
    def test_stale_pid_restart(self):
        s=Supervisor(self.base,str(self.root),FakeLauncher());r=s.restart_receipt()
        self.assertEqual(r['previous_state'],'UNKNOWN_INTERRUPTED')
    def test_atomic_receipt(self):
        p=self.root/'receipt.json';atomic_json(p,{'ok':True});self.assertTrue(p.exists())
        big={'x':'A'*(129*1024)}
        with self.assertRaises(ValueError):atomic_json(self.root/'big.json',big)
    def test_cancel(self):
        fl=FakeLauncher(hang_ports={10000});s=Supervisor(self.base,str(self.root),fl)
        import threading;t=threading.Thread(target=s.run);t.start();time.sleep(0.5);s.cancel();t.join(timeout=3)
        self.assertEqual(s.state,State.CANCELLED)
    def test_failure_inject(self):
        fl=FakeLauncher(fail_ports={10001});s=Supervisor(self.base,str(self.root),fl);res=s.run()
        self.assertEqual(res,State.FAILED)
    def test_success_fake(self):
        fl=FakeLauncher();s=Supervisor(self.base,str(self.root),fl);res=s.run()
        self.assertIn(res,(State.READY,State.COMPLETED))

if __name__=='__main__':unittest.main()

