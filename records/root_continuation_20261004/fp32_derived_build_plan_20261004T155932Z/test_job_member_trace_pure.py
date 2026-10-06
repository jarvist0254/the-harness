"""Independent pure controls: no Win32 APIs or native process fixture."""
import ctypes
from ctypes import wintypes as wt
import importlib.util
import pathlib
import tempfile
import types
import unittest
import subprocess
import os

ROOT = pathlib.Path(__file__).resolve().parent
TRAPS = []
def denied(*args, **kwargs):
    TRAPS.append('native_or_process')
    raise AssertionError('Native/process APIs forbidden in these tests')
ctypes.WinDLL = denied
subprocess.Popen = denied
os.system = denied
spec = importlib.util.spec_from_file_location('diagnostic_actual', ROOT/'job_member_trace.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
proxy = types.SimpleNamespace(**{k:getattr(ctypes,k) for k in dir(ctypes) if not k.startswith('__')})
proxy.get_last_error = lambda: 5
class Buffer(ctypes.Structure):
    _fields_ = [('assigned',wt.DWORD),('returned',wt.DWORD),('pids',ctypes.c_size_t*64)]
class Kernel:
    def __init__(self, assigned=1, returned=1, query_ok=True, member=True, image_ok=True, close_ok=True):
        self.assigned,self.returned,self.query_ok,self.member,self.image_ok,self.close_ok=assigned,returned,query_ok,member,image_ok,close_ok
        self.calls=[]
    def QueryInformationJobObject(self, job, kind, ptr, size, length):
        self.calls.append(('query',job,kind,size))
        self.asserted_size=size
        buf=ctypes.cast(ptr,ctypes.POINTER(Buffer)).contents
        buf.assigned=self.assigned;buf.returned=self.returned;buf.pids[0]=123
        ctypes.cast(length,ctypes.POINTER(wt.DWORD)).contents.value=ctypes.sizeof(Buffer)
        return self.query_ok
    def OpenProcess(self, access, inherit, pid):
        self.calls.append(('open',access,inherit,pid));return 555
    def IsProcessInJob(self, handle, job, ptr):
        self.calls.append(('member',handle,job));ctypes.cast(ptr,ctypes.POINTER(wt.BOOL)).contents.value=self.member;return 1
    def QueryFullProcessImageNameW(self, handle, flags, image, size):
        self.calls.append(('image',handle));image.value='C:\Compiler\cl.exe';return self.image_ok
    def CloseHandle(self, handle):self.calls.append(('close',handle));return self.close_ok
class Cases(unittest.TestCase):
    def test_typed_query_owned_job_and_image(self):
        k=Kernel();r=helper.query_members(proxy,wt,k,999)
        self.assertEqual(r['status'],'LIST_OBSERVED');self.assertEqual(r['members'][0]['status'],'IMAGE_OBSERVED')
        self.assertEqual(k.calls[0],('query',999,3,ctypes.sizeof(Buffer)))
        self.assertEqual(k.calls[1],('open',0x1000,False,123));self.assertIn(('member',555,999),k.calls);self.assertEqual(k.calls[-1],('close',555))
    def test_query_false_unknown(self):
        k=Kernel(query_ok=False);self.assertEqual(helper.query_members(proxy,wt,k,999)['status'],'QUERY_UNKNOWN');self.assertEqual(len(k.calls),1)
    def test_partial_list_unknown(self):
        k=Kernel(assigned=2,returned=1);self.assertEqual(helper.query_members(proxy,wt,k,999)['status'],'QUERY_UNKNOWN');self.assertEqual(len(k.calls),1)
    def test_over64_unknown(self):
        k=Kernel(assigned=65,returned=65);self.assertEqual(helper.query_members(proxy,wt,k,999)['status'],'QUERY_UNKNOWN');self.assertEqual(len(k.calls),1)
    def test_nonmember_no_image_still_close(self):
        k=Kernel(member=False);r=helper.query_members(proxy,wt,k,999);self.assertEqual(r['members'][0]['status'],'IDENTITY_UNKNOWN');self.assertNotIn(('image',555),k.calls);self.assertEqual(k.calls[-1],('close',555))
    def test_close_false_recorded(self):
        self.assertEqual(helper.query_members(proxy,wt,Kernel(close_ok=False),999)['members'][0]['close_status'],'UNKNOWN')
    def check_counts(self, counts):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            calls=[];m=types.SimpleNamespace(_accounting=lambda *args:counts)
            t=helper.install(m,folder,observe=lambda job:calls.append(job) or {'status':'QUERY_UNKNOWN'},clock=lambda:0)
            self.assertIs(m._accounting(None,None,999),counts)
            self.assertEqual(calls,[] if counts is None or counts[0]==0 else [999])
    def test_original_zero_identity(self):self.check_counts((0,4,1))
    def test_original_positive_identity(self):self.check_counts((1,4,1))
    def test_original_none_identity(self):self.check_counts(None)
    def test_original_exception_identity(self):
        err=ValueError('original');m=types.SimpleNamespace(_accounting=lambda *args:(_ for _ in ()).throw(err));helper.install(m,ROOT,observe=denied)
        try:m._accounting(None,None,999)
        except ValueError as got:self.assertIs(got,err)
        else:self.fail('original exception swallowed')
    def test_rate_five_seconds(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            now=[0];m=types.SimpleNamespace(_accounting=lambda *args:(1,2,0));t=helper.install(m,folder,observe=lambda job:{},clock=lambda:now[0])
            for tick in (0,1,4.99,5):now[0]=tick;m._accounting(None,None,999)
            self.assertEqual(t.metadata['samples'],2)
    def test_cap_without_accounting_change(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            f=pathlib.Path(folder)/'job_members.jsonl';f.write_bytes(b'X'*helper.CAP);counts=(1,2,0);m=types.SimpleNamespace(_accounting=lambda *args:counts);t=helper.install(m,folder,observe=lambda job:{},clock=lambda:0)
            self.assertIs(m._accounting(None,None,999),counts);self.assertTrue(t.metadata['capped']);self.assertEqual(f.stat().st_size,helper.CAP)
    def test_observation_exception_diagnostic_only(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            counts=(1,2,0);m=types.SimpleNamespace(_accounting=lambda *args:counts);t=helper.install(m,folder,observe=lambda job:(_ for _ in ()).throw(OSError('probe')),clock=lambda:0)
            self.assertIs(m._accounting(None,None,999),counts);self.assertEqual(t.metadata['failures'],1)
    def test_no_native_trap_invoked(self):self.assertEqual(TRAPS,[])
if __name__=='__main__':unittest.main(verbosity=2)
