import os,sys,json,time,hashlib,tempfile,threading
from pathlib import Path
from contextlib import ExitStack
if os.name!='nt':
    def run_workers(*a,**k):raise NotImplementedError('NOT_IMPLEMENTED')
else:
    import _winapi,ctypes,subprocess,msvcrt
    from ctypes import wintypes
    class WindowsJobError(RuntimeError):
        def __init__(s,c,w=None):s.code,s.winerror=c,w;super().__init__(f"{c}: {w}" if w else c)
    def _kernel():
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        for n,a,r in[("CreateJobObjectW",[ctypes.c_void_p,wintypes.LPCWSTR],wintypes.HANDLE),("AssignProcessToJobObject",[wintypes.HANDLE,wintypes.HANDLE],wintypes.BOOL),("TerminateJobObject",[wintypes.HANDLE,wintypes.UINT],wintypes.BOOL),("QueryInformationJobObject",[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.c_void_p],wintypes.BOOL),("CloseHandle",[wintypes.HANDLE],wintypes.BOOL),("ResumeThread",[wintypes.HANDLE],wintypes.DWORD)]:
            f=getattr(k,n);f.argtypes,f.restype=a,r
        return k
    def _sha(p):
        h=hashlib.sha256()
        with open(p,'rb') as f:
            for c in iter(lambda:f.read(1<<16),b''):h.update(c)
        return h.hexdigest()
    def _validate(m,o):
        if not isinstance(m,dict):raise TypeError('manifest')
        r=m.get('run_id')
        if not isinstance(r,str)or not r.isidentifier()or'\x00'in r:raise ValueError('run_id')
        ws=m.get('workers');
        if not isinstance(ws,list)or not(1<=len(ws)<=4):raise ValueError('workers count')
        dl=m.get('deadline_seconds');
        if not isinstance(dl,int)or isinstance(dl,bool)or not(1<=dl<=60):raise ValueError('deadline')
        su=m.get('startup_seconds');
        if not isinstance(su,int)or isinstance(su,bool)or not(1<=su<=10):raise ValueError('startup')
        ll=m.get('log_limit_bytes');
        if not isinstance(ll,int)or isinstance(ll,bool)or not(1024<=ll<=131072):raise ValueError('log_limit')
        cp=m.get('containment_policy','explicit_terminate')
        if cp not in('explicit_terminate','kill_on_close'):raise ValueError('policy')
        ids=set();out=[]
        for w in ws:
            if not isinstance(w,dict):raise TypeError('worker')
            wid=w.get('worker_id')
            if not isinstance(wid,str)or not wid.isidentifier()or'\x00'in wid or wid in ids:raise ValueError('wid')
            ids.add(wid);av=w.get('argv')
            if not isinstance(av,list)or not av:raise ValueError('argv')
            if any(not isinstance(a,str)or'\x00'in a for a in av):raise ValueError('argv nul')
            exe=Path(av[0])
            if not exe.is_absolute()or not exe.is_file():raise ValueError('exe path')
            if'..'in exe.parts:raise ValueError('traversal')
            hs=w.get('executable_sha256')
            if not isinstance(hs,str)or len(hs)!=64:raise ValueError('sha fmt')
            if _sha(exe)!=hs.lower():raise ValueError('sha mismatch')
            cw=w.get('cwd')
            if not isinstance(cw,str)or'\x00'in cw:raise ValueError('cwd')
            cp2=Path(cw)
            if not cp2.is_absolute()or not cp2.is_dir()or'..'in cp2.parts:raise ValueError('cwd path')
            out.append({'worker_id':wid,'argv':av,'cwd':cw})
        op=Path(o)
        if not op.is_absolute()or'..'in op.parts:raise ValueError('output_root')
        if op.exists():raise ValueError('output exists')
        return r,out,dl,su,ll,cp,op
    def _env():
        e={}
        for k in('SystemRoot','SYSTEMDRIVE','COMSPEC','PATH','TEMP','TMP'):
            v=os.environ.get(k)
            if v:e[k]=v
        return e
    def _pipe_rdr(ph,lim,cap,ev):
        b=bytearray();tr=0
        while not ev.is_set():
            try:ok,d=_winapi.ReadFile(ph,4096)
            except OSError:break
            if not ok and not d:break
            if len(b)+len(d)>lim:tr+=1;cap['overflow']=True;cap['truncations']=tr;break
            b.extend(d)
        cap['data']=bytes(b);cap['truncations']=tr
    def _receipt(op,rid,payload):
        op.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(payload).encode()
        if len(raw)>131072:raise ValueError('receipt too large')
        fd,tp=tempfile.mkstemp(dir=str(op),suffix='.tmp')
        try:
            os.write(fd,raw);os.fsync(fd);os.close(fd)
            fp=op/f'{rid}_receipt.json';os.replace(tp,str(fp));tp=None
        finally:
            if tp:os.close(fd);os.unlink(tp)
    def run_workers(manifest,output_root,*,cancel_event=None):
        if os.name!='nt':raise NotImplementedError('NOT_IMPLEMENTED')
        if cancel_event is None:cancel_event=threading.Event()
        rid,ws,dl,su,ll,cp,op=_validate(manifest,output_root)
        krn=_kernel();jn=f'CS_{rid}_{os.getpid()}_{time.monotonic_ns()}'
        jh=krn.CreateJobObjectW(None,jn)
        if not jh:
            e=ctypes.get_last_error()
            if e==183:raise WindowsJobError('JOB_COLLISION',183)
            raise WindowsJobError('CREATE_JOB_FAILED',e)
        if cp=='kill_on_close':
            class ELI(ctypes.Structure):_fields_=[('LimitFlags',wintypes.DWORD)]
            eli=ELI();eli.LimitFlags=0x00002000
            if not krn.QueryInformationJobObject(jh,9,ctypes.byref(eli),ctypes.sizeof(eli),None):
                class JELI(ctypes.Structure):_fields_=[('Basic',ELI),('PerProcessUserTime',ctypes.c_int64),('PerJobUserTime',ctypes.c_int64),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
                jeli=JELI();jeli.Basic.LimitFlags=0x00002000
                krn.QueryInformationJobObject(jh,9,ctypes.byref(jeli),ctypes.sizeof(jeli),None)
        phs,ths,lrs=[],[],[];status='PROCESS_COMPLETED';fail_r=''
        try:
            with ExitStack() as stk:
                env=_env()
                for w in ws:
                    si=subprocess.STARTUPINFO();si.dwFlags|=subprocess.STARTF_USESTDHANDLES
                    cur=_winapi.GetCurrentProcess()
                    nh=stk.enter_context(open(os.devnull,'rb'))
                    sh=_winapi.DuplicateHandle(cur,msvcrt.get_osfhandle(nh.fileno()),cur,0,True,2)
                    stk.callback(_winapi.CloseHandle,sh)
                    prd,pwr=_winapi.CreatePipe(None,0);stk.callback(_winapi.CloseHandle,pwr)
                    erd,ewr=_winapi.CreatePipe(None,0);stk.callback(_winapi.CloseHandle,ewr)
                    oh=_winapi.DuplicateHandle(cur,pwr,cur,0,True,2);stk.callback(_winapi.CloseHandle,oh)
                    eh=_winapi.DuplicateHandle(cur,ewr,cur,0,True,2);stk.callback(_winapi.CloseHandle,eh)
                    si.hStdInput,si.hStdOutput,si.hStdError=sh,oh,eh
                    si.lpAttributeList={'handle_list':[sh,oh,eh]}
                    cl=subprocess.list2cmdline(w['argv'])
                    ph,th,pid,_=_winapi.CreateProcess(w['argv'][0],cl,None,None,True,0x00000004|0x08000000,env,w['cwd'],si)
                    phs.append(ph);ths.append(th)
                    if not krn.AssignProcessToJobObject(jh,ph):
                        ae=ctypes.get_last_error();_winapi.TerminateProcess(ph,1);_winapi.WaitForSingleObject(ph,5000)
                        raise WindowsJobError('ASSIGN_FAILED',ae)
                    sc={};ev=threading.Event();lrs.append((sc,ev))
                    t=threading.Thread(target=_pipe_rdr,args=(prd,ll,sc,ev),daemon=True);t.start()
                    ec={};ev2=threading.Event();lrs.append((ec,ev2))
                    t2=threading.Thread(target=_pipe_rdr,args=(erd,ll,ec,ev2),daemon=True);t2.start()
                dead=time.monotonic()+dl;started=time.monotonic()
                for th in ths:
                    if _winapi.ResumeThread(th)==0xFFFFFFFF:raise WindowsJobError('RESUME_FAILED')
                while time.monotonic()<dead and not cancel_event.is_set():
                    done=True
                    for ph in phs:
                        if _winapi.WaitForSingleObject(ph,0)==258:done=False;break
                    if done:break
                    time.sleep(0.02)
                if cancel_event.is_set():status,fail_r='CANCELLED','cancelled'
                elif time.monotonic()>=dead:status,fail_r='TIMEOUT','deadline'
                else:
                    class AI(ctypes.Structure):_fields_=[('t',ctypes.c_longlong*4),('pf',wintypes.DWORD),('tot',wintypes.DWORD),('act',wintypes.DWORD),('term',wintypes.DWORD)]
                    ai=AI();krn.QueryInformationJobObject(jh,1,ctypes.byref(ai),ctypes.sizeof(ai),None)
                    if ai.act>0:status,fail_r='FAIL','active_children'
                    else:
                        for ph in phs:
                            if _winapi.GetExitCodeProcess(ph)!=0:status,fail_r='FAILED','nonzero_exit';break
                for sc,ev in lrs:ev.set()
                if status!='PROCESS_COMPLETED':krn.TerminateJobObject(jh,1)
                for ph in phs:_winapi.WaitForSingleObject(ph,5000)
        finally:
            for th in ths:_winapi.CloseHandle(th)
            for ph in phs:_winapi.CloseHandle(ph)
            krn.CloseHandle(jh)
        logs={}
        for i,w in enumerate(ws):
            sc=lrs[i*2][0];ec=lrs[i*2+1][0]
            logs[w['worker_id']]={'stdout':sc.get('data',b'').decode(errors='replace'),'stderr':ec.get('data',b'').decode(errors='replace'),'truncated_stdout':sc.get('truncations',0),'truncated_stderr':ec.get('truncations',0)}
        res={'run_id':rid,'status':status,'failure_reason':fail_r,'logs':logs}
        _receipt(op,rid,res);return res

