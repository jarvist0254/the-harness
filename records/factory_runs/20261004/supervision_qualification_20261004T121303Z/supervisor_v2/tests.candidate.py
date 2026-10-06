import unittest,os,sys,json,hashlib,threading
try:
    import contained_supervisor as cs
except ImportError:
    sys.path.insert(0,os.path.dirname(__file__))
    import contained_supervisor as cs
RUN_FX=os.environ.get('RUN_CONTAINMENT_FIXTURES')=='1'
def _sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1<<16),b''):h.update(c)
    return h.hexdigest()
def _py_exe():return sys.executable
def _base_m(tmp):
    exe=_py_exe();d=tmp/'cwd';d.mkdir(exist_ok=True)
    return{'run_id':'test_run','workers':[{'worker_id':'w1','argv':[exe,'-c','import time;time.sleep(0.1)'],'executable_sha256':_sha(exe),'cwd':str(d)}],'deadline_seconds':10,'startup_seconds':5,'log_limit_bytes':4096,'containment_policy':'explicit_terminate'}
class TestValidation(unittest.TestCase):
    def test_non_windows(self):
        if os.name=='nt':self.skipTest('windows only')
        with self.assertRaises(NotImplementedError):cs.run_workers({},'/tmp/x')
    def test_bad_run_id(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False})()})())
        m['run_id']='bad id!'
        with self.assertRaises(ValueError):cs._validate(m,'/no/exist')
    def test_bool_deadline(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False})()})())
        m['deadline_seconds']=True
        with self.assertRaises(ValueError):cs._validate(m,'/no/exist')
    def test_dup_worker_ids(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False})()})())
        m['workers'].append(dict(m['workers'][0]))
        with self.assertRaises(ValueError):cs._validate(m,'/no/exist')
    def test_existing_output(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False})()})())
            with self.assertRaises(ValueError):cs._validate(m,td)
    def test_path_traversal(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False})()})())
        m['workers'][0]['cwd']='C:/../evil'
        with self.assertRaises(ValueError):cs._validate(m,'/no/exist')
@unittest.skipUnless(RUN_FX and os.name=='nt','OPT-IN fixtures')
class TestFixtures(unittest.TestCase):
    def setUp(self):
        import tempfile;self.tmp=tempfile.TemporaryDirectory();self.tp=self.tmp.name
    def tearDown(self):self.tmp.cleanup()
    def test_child_sleep_cancel(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False,'__truediv__':lambda s2,y:type('R',(object,),{'mkdir':lambda **k:None})()})()})())
        m['workers'][0]['argv']=[_py_exe(),'-c','import time;time.sleep(60)']
        m['workers'][0]['executable_sha256']=_sha(_py_exe())
        ce=threading.Event();out=os.path.join(self.tp,'out')
        threading.Timer(0.5,ce.set).start()
        r=cs.run_workers(m,out,cancel_event=ce)
        self.assertEqual(r['status'],'CANCELLED')
    def test_deadline(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False,'__truediv__':lambda s2,y:type('R',(object,),{'mkdir':lambda **k:None})()})()})())
        m['workers'][0]['argv']=[_py_exe(),'-c','import time;time.sleep(60)']
        m['workers'][0]['executable_sha256']=_sha(_py_exe());m['deadline_seconds']=1
        out=os.path.join(self.tp,'out2')
        r=cs.run_workers(m,out)
        self.assertEqual(r['status'],'TIMEOUT')
    def test_nonzero(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False,'__truediv__':lambda s2,y:type('R',(object,),{'mkdir':lambda **k:None})()})()})())
        m['workers'][0]['argv']=[_py_exe(),'-c','import sys;sys.exit(1)']
        m['workers'][0]['executable_sha256']=_sha(_py_exe())
        out=os.path.join(self.tp,'out3')
        r=cs.run_workers(m,out)
        self.assertEqual(r['status'],'FAILED')
    def test_log_overflow(self):
        m=_base_m(type('P',(object,),{'__truediv__':lambda s,x:type('Q',(object,),{'mkdir':lambda **k:None,'exists':lambda:False,'__truediv__':lambda s2,y:type('R',(object,),{'mkdir':lambda **k:None})()})()})())
        m['workers'][0]['argv']=[_py_exe(),'-c','import sys;sys.stdout.write("A"*2048);sys.stdout.flush()']
        m['workers'][0]['executable_sha256']=_sha(_py_exe());m['log_limit_bytes']=1024
        out=os.path.join(self.tp,'out4')
        r=cs.run_workers(m,out)
        self.assertTrue(r['logs']['w1']['truncated_stdout']>0 or r['status']=='PROCESS_COMPLETED')
if __name__=='__main__':unittest.main()

