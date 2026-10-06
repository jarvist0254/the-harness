import hashlib, importlib.util, json, os, pathlib, sys, tempfile, threading, types, unittest
from unittest.mock import patch

CANDIDATE_PATH = os.environ.get('CANDIDATE_PATH', str(pathlib.Path(__file__).resolve().parent / 'contained_supervisor.py'))
EXPECTED_HASH = '603916f8b0f21'

spec = importlib.util.spec_from_file_location('cs', CANDIDATE_PATH)
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

def _verify_hash():
    h = hashlib.sha256(pathlib.Path(CANDIDATE_PATH).read_bytes()).hexdigest()
    assert h.startswith(EXPECTED_HASH.split('...')[0]) or EXPECTED_HASH in h, f'Hash mismatch: {h}'

class FakeClock:
    def __init__(self, budget=8.0):
        self.t = 0.0
        self.budget = budget
    def mono(self):
        self.t += 0.01
        return self.t
    def sleep(self, s):
        self.t += s

class FakeAPI:
    def __init__(self, term_ret=None, close_ret=None, wait_ret=0, exit_ret=0, read_mode='EOF'):
        self.term_ret = term_ret
        self.close_ret = close_ret
        self.wait_ret = wait_ret
        self.exit_ret = exit_ret
        self.read_mode = read_mode
        self.calls = []
    def GetCurrentProcess(self): return 1
    def DuplicateHandle(self, *a): return 10
    def CreatePipe(self, *a): return 20, 21
    def CreateProcess(self, *a): return 30, 31, 1000, 1
    def CloseHandle(self, h):
        self.calls.append(('CloseHandle', h))
        if self.close_ret is not None: return self.close_ret
        return None
    def ReadFile(self, h, n):
        if self.read_mode == 'EOF': raise OSError(winerror=109)
        if self.read_mode == 'ERR5':
            e = OSError('err'); e.winerror = 5; raise e
        if self.read_mode == 'BAD': return 'notbytes', 0
        return b'', 109
    def TerminateProcess(self, h, c):
        self.calls.append(('TerminateProcess', h))
        return self.term_ret
    def WaitForSingleObject(self, h, t):
        self.calls.append(('WaitForSingleObject', h, t))
        return self.wait_ret
    def GetExitCodeProcess(self, h): return self.exit_ret

class FakeKernel:
    def __init__(self, term_ret=1, close_ret=1):
        self.term_ret = term_ret
        self.close_ret = close_ret
        self.calls = []
    def TerminateJobObject(self, j, c):
        self.calls.append(('TerminateJobObject', j))
        return self.term_ret
    def CloseHandle(self, h):
        self.calls.append(('CloseHandle', h))
        return self.close_ret
    def QueryInformationJobObject(self, *a): return 1
    def AssignProcessToJobObject(self, *a): return 1
    def ResumeThread(self, *a): return 1
    def CreateJobObjectW(self, *a): return 99
    def SetInformationJobObject(self, *a): return 1

class TestDefects(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.tmp = tempfile.mkdtemp()
        self.out = pathlib.Path(self.tmp) / 'out'
    def tearDown(self):
        import shutil; shutil.rmtree(self.tmp, ignore_errors=True)
    def _spec(self):
        return {'run_id':'r','workers':[{'worker_id':'w1','argv':['C:\\x.exe'],'cwd':self.tmp}],'deadline':4,'startup':2,'log_limit':1024,'policy':'explicit_terminate','output':self.out,'env':{},'seq':1}
    def test_termjob_int_zero_is_failure(self):
        k = FakeKernel(term_ret=0)
        api = FakeAPI(term_ret=None, close_ret=None, wait_ret=0)
        deps = {'_winapi':api,'ctypes':types.SimpleNamespace(get_last_error=lambda:0,set_last_error=lambda x:None,byref=lambda x:x,sizeof=lambda x:0,c_void_p=int,c_int=int,c_int64=int,c_size_t=int,c_ulonglong=int,WinDLL=lambda *a,**k:None),'wintypes':types.SimpleNamespace(HANDLE=int,BOOL=int,DWORD=int,LPCWSTR=str,UINT=int),'msvcrt':types.SimpleNamespace(get_osfhandle=lambda x:1),'subprocess':types.SimpleNamespace(STARTUPINFO=lambda:types.SimpleNamespace(dwFlags=0,hStdInput=0,hStdOutput=0,hStdError=0,lpAttributeList={}),STARTF_USESTDHANDLES=1,list2cmdline=lambda x:'')}
        owned = [{'worker_id':'w1','ph':30,'th':31,'pid':1000,'assigned':True,'resumed':True,'exit_code':None,'wait':None}]
        active, drain = cs._shutdown(deps, k, 99, owned, True, self.clock.mono()+8)
        self.assertEqual(drain, 'UNKNOWN_DRAIN')
    def test_termjob_int_one_is_success(self):
        k = FakeKernel(term_ret=1)
        api = FakeAPI(term_ret=None, close_ret=None, wait_ret=0)
        deps = {'_winapi':api,'ctypes':types.SimpleNamespace(get_last_error=lambda:0,set_last_error=lambda x:None,byref=lambda x:x,sizeof=lambda x:0,c_void_p=int,c_int=int,c_int64=int,c_size_t=int,c_ulonglong=int,WinDLL=lambda *a,**k:None),'wintypes':types.SimpleNamespace(HANDLE=int,BOOL=int,DWORD=int,LPCWSTR=str,UINT=int),'msvcrt':types.SimpleNamespace(get_osfhandle=lambda x:1),'subprocess':types.SimpleNamespace(STARTUPINFO=lambda:types.SimpleNamespace(dwFlags=0,hStdInput=0,hStdOutput=0,hStdError=0,lpAttributeList={}),STARTF_USESTDHANDLES=1,list2cmdline=lambda x:'')}
        owned = [{'worker_id':'w1','ph':30,'th':31,'pid':1000,'assigned':True,'resumed':True,'exit_code':None,'wait':None}]
        with patch.object(cs,'_accounting',return_value=(0,1)):
            active, drain = cs._shutdown(deps, k, 99, owned, True, self.clock.mono()+8)
        self.assertEqual(drain, 'CLEANUP')
    def test_winapi_terminate_none_is_success(self):
        api = FakeAPI(term_ret=None, close_ret=None, wait_ret=0)
        k = FakeKernel(term_ret=1)
        deps = {'_winapi':api,'ctypes':types.SimpleNamespace(get_last_error=lambda:0,set_last_error=lambda x:None,byref=lambda x:x,sizeof=lambda x:0,c_void_p=int,c_int=int,c_int64=int,c_size_t=int,c_ulonglong=int,WinDLL=lambda *a,**k:None),'wintypes':types.SimpleNamespace(HANDLE=int,BOOL=int,DWORD=int,LPCWSTR=str,UINT=int),'msvcrt':types.SimpleNamespace(get_osfhandle=lambda x:1),'subprocess':types.SimpleNamespace(STARTUPINFO=lambda:types.SimpleNamespace(dwFlags=0,hStdInput=0,hStdOutput=0,hStdError=0,lpAttributeList={}),STARTF_USESTDHANDLES=1,list2cmdline=lambda x:'')}
        owned = [{'worker_id':'w1','ph':30,'th':31,'pid':1000,'assigned':True,'resumed':True,'exit_code':None,'wait':None}]
        with patch.object(cs,'_accounting',return_value=(0,1)):
            active, drain = cs._shutdown(deps, k, 99, owned, True, self.clock.mono()+8)
        self.assertEqual(drain, 'CLEANUP')
    def test_reader_close_false_uncertain(self):
        slot = {'data':b'','overflow':False,'bytes':0,'closed':False,'close_uncertain':False,'stream':'stdout','worker_id':'w1','bad_read':False}
        def cf(h): return False
        cs._read_pipe(20, 1024, slot, lambda h,n:(b'',109), cf, threading.Event())
        self.assertTrue(slot['close_uncertain'])
        self.assertFalse(slot['closed'])
    def test_reader_close_zero_uncertain(self):
        slot = {'data':b'','overflow':False,'bytes':0,'closed':False,'close_uncertain':False,'stream':'stdout','worker_id':'w1','bad_read':False}
        cs._read_pipe(20, 1024, slot, lambda h,n:(b'',109), lambda h:0, threading.Event())
        self.assertTrue(slot['close_uncertain'])
        self.assertFalse(slot['closed'])
    def test_reader_eof_109_good(self):
        slot = {'data':b'','overflow':False,'bytes':0,'closed':False,'close_uncertain':False,'stream':'stdout','worker_id':'w1','bad_read':False}
        def rf(h,n):
            e=OSError('eof');e.winerror=109;raise e
        cs._read_pipe(20, 1024, slot, rf, lambda h:None, threading.Event())
        self.assertFalse(slot['bad_read'])
        self.assertTrue(slot['closed'])
    def test_reader_err5_bad(self):
        slot = {'data':b'','overflow':False,'bytes':0,'closed':False,'close_uncertain':False,'stream':'stdout','worker_id':'w1','bad_read':False}
        def rf(h,n):
            e=OSError('err');e.winerror=5;raise e
        cs._read_pipe(20, 1024, slot, rf, lambda h:None, threading.Event())
        self.assertTrue(slot['bad_read'])
    def test_job_close_zero_no_completed(self):
        k = FakeKernel(close_ret=0)
        sp = self._spec()
        with patch.object(cs,'_validate',return_value=sp),patch.object(cs,'_imports',return_value={'_winapi':FakeAPI(),'ctypes':types.SimpleNamespace(get_last_error=lambda:0,set_last_error=lambda x:None,byref=lambda x:x,sizeof=lambda x:0,c_void_p=int,c_int=int,c_int64=int,c_size_t=int,c_ulonglong=int,WinDLL=lambda *a,**k:k),'wintypes':types.SimpleNamespace(HANDLE=int,BOOL=int,DWORD=int,LPCWSTR=str,UINT=int),'msvcrt':types.SimpleNamespace(get_osfhandle=lambda x:1),'subprocess':types.SimpleNamespace(STARTUPINFO=lambda:types.SimpleNamespace(dwFlags=0,hStdInput=0,hStdOutput=0,hStdError=0,lpAttributeList={}),STARTF_USESTDHANDLES=1,list2cmdline=lambda x:'')}),patch.object(cs,'_kernel',return_value=k),patch.object(cs,'_monotonic',side_effect=self.clock.mono),patch.object(cs,'_sleep',side_effect=self.clock.sleep),patch.object(cs,'_open_job',return_value=99),patch.object(cs,'_launch_and_wait',return_value=('PROCESS_COMPLETED','')),patch.object(cs,'_accounting',return_value=(0,1)),patch.object(cs.threading,'Thread',lambda **kw:types.SimpleNamespace(start=lambda:None,is_alive=lambda:False,join=lambda t:None)):
            r = cs.run_workers({},str(sp['output']))
        self.assertNotEqual(r['status'],'PROCESS_COMPLETED')
    def test_shared_deadline_not_multiplied(self):
        clock = FakeClock()
        threads = [types.SimpleNamespace(is_alive=lambda:True, join=lambda t: setattr(clock,'t',clock.t+t)) for _ in range(8)]
        dl = clock.mono() + 8.0
        with patch.object(cs,'_monotonic',side_effect=lambda:clock.t):
            cs._join(threads, 2, dl)
        self.assertLessEqual(clock.t, dl + 0.1)
    def test_later_close_attempts_continue(self):
        api = FakeAPI(close_ret=None)
        owned = [{'th':1,'ph':2},{'th':3,'ph':4}]
        calls = []
        orig = api.CloseHandle
        def track(h):
            calls.append(h)
            if h == 1: return False
            return orig(h)
        api.CloseHandle = track
        cs._close_owned(api, owned)
        self.assertIn(3, calls)
        self.assertIn(4, calls)

if __name__=='__main__':
    unittest.main()

