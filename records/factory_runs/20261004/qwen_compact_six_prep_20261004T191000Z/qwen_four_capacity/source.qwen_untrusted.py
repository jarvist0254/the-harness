import math
ART=('model_hash','workload_hash','source_hash','exe_hash','context_hash','quant')
class _E(Exception):
    def __init__(s,st,m):
        super().__init__(m); s.st=st; s.m=m
def _i(x): return isinstance(x,int) and not isinstance(x,bool)
def _n(x): return not isinstance(x,bool) and (isinstance(x,int) or (isinstance(x,float) and math.isfinite(x)))
def _s(x): return isinstance(x,str) and x.strip()!=''
def _l(x): return x.strip().lower()
def _ret(st,m):
    c=0 if st=='PASS' else (1 if st=='FAIL' else 2)
    return {'status':st,'exit_code':c,'errors':[] if st=='PASS' else [m],'scope':'four discrete GPU VRAM capacity receipt; GPU-free strict validator'}
def validate_capacity(evidence,*,trusted):
    try:
        if trusted is not True: raise _E('NOT_CHECKED','untrusted')
        if not isinstance(evidence,dict): raise _E('NOT_CHECKED','evidence')
        for k in ART+('artifact_source','cpu_reference_hash'):
            if not _s(evidence.get(k)): raise _E('NOT_CHECKED','artifact:'+k)
        if not _i(evidence.get('observed_at_ns')): raise _E('NOT_CHECKED','observed_at_ns')
        mb=evidence.get('model_bytes')
        if not _i(mb) or mb<=0: raise _E('NOT_CHECKED','model_bytes')
        tol=evidence.get('logit_tol_abs')
        if not _n(tol) or tol<=0: raise _E('NOT_CHECKED','tol')
        ms=evidence.get('max_staleness_ns',10000000000)
        if not _i(ms) or ms<0: raise _E('NOT_CHECKED','staleness')
        att=evidence.get('attempts')
        if not isinstance(att,list): raise _E('NOT_CHECKED','attempts')
        by={}
        for a in att:
            if isinstance(a,dict) and _s(a.get('role')): by.setdefault(a['role'],[]).append(a)
        bind=tuple(evidence[k] for k in ART); P={}
        for r in ('single','three','four'):
            L=by.get(r,[])
            if len(L)!=1: raise _E('NOT_CHECKED','role:'+r)
            a=L[0]
            if tuple(a.get(k) for k in ART)!=bind: raise _E('FAIL','bind:'+r)
            if not _i(a.get('timestamp_ns')): raise _E('NOT_CHECKED','ts:'+r)
            if abs(a['timestamp_ns']-evidence['observed_at_ns'])>ms: raise _E('NOT_CHECKED','stale:'+r)
            c=a.get('controller')
            if not isinstance(c,dict): raise _E('NOT_CHECKED','ctrl:'+r)
            for k in ('args_valid','timeout','policy_cap'):
                if k not in c: raise _E('NOT_CHECKED','ctrl.'+k)
            if c['args_valid'] is not True: raise _E('FAIL','args:'+r)
            if c['timeout'] is not False: raise _E('FAIL','timeout:'+r)
            if c['policy_cap'] is not False: raise _E('FAIL','policy:'+r)
            if c.get('native_error') not in (None,'',False): raise _E('FAIL','native:'+r)
            ds=a.get('devices')
            if not isinstance(ds,list) or not ds: raise _E('NOT_CHECKED','devs:'+r)
            seen=set(); canon=set(); phys=0
            for d in ds:
                if not isinstance(d,dict): raise _E('NOT_CHECKED','dev:'+r)
                cid=d.get('canonical_id'); pal=d.get('physical_alias')
                if not _s(cid) or not _s(pal): raise _E('NOT_CHECKED','alias:'+r)
                al=d.get('aliases')
                if not isinstance(al,list) or not al: raise _E('NOT_CHECKED','aliases:'+r)
                nm={_l(cid),_l(pal)}
                for x in al:
                    if not _s(x): raise _E('NOT_CHECKED','alias2:'+r)
                    nm.add(_l(x))
                if 'discrete' not in d or 'form_factor' not in d: raise _E('NOT_CHECKED','form:'+r)
                if d['discrete'] is not True or d['form_factor']!='discrete_gpu': raise _E('FAIL','discrete:'+r)
                if not (nm & seen): phys+=1
                seen|=nm; canon.add(_l(cid))
            if len(canon)!=phys: raise _E('FAIL','dedup:'+r)
            al=a.get('allocator')
            if not isinstance(al,dict): raise _E('NOT_CHECKED','alloc:'+r)
            if al.get('class')!='dedicated_vram': raise _E('NOT_CHECKED','alloc_class:'+r)
            if al.get('fresh') is not True: raise _E('NOT_CHECKED','fresh:'+r)
            if not _s(al.get('source')): raise _E('NOT_CHECKED','alloc_src:'+r)
            if not _i(al.get('timestamp_ns')): raise _E('NOT_CHECKED','alloc_ts:'+r)
            if abs(al['timestamp_ns']-a['timestamp_ns'])>ms: raise _E('NOT_CHECKED','alloc_stale:'+r)
            P[r]={'a':a,'phys':phys,'canon':canon}
        if P['single']['phys']!=1: raise _E('FAIL','single_phys')
        if P['three']['phys']!=3: raise _E('FAIL','three_phys')
        if P['four']['phys']!=4: raise _E('FAIL','four_phys')
        for r in ('single','three'):
            ex=P[r]['a'].get('execution')
            if not isinstance(ex,dict): raise _E('NOT_CHECKED','exec:'+r)
            if ex.get('status')!='allocator_oom': raise _E('FAIL','oom:'+r)
            rb=ex.get('requested_bytes')
            if not _i(rb) or rb<=0: raise _E('NOT_CHECKED','req:'+r)
            if rb!=mb: raise _E('FAIL','req_mb:'+r)
        a=P['four']['a']; ex=a.get('execution')
        if not isinstance(ex,dict): raise _E('NOT_CHECKED','exec4')
        if ex.get('status')!='success': raise _E('FAIL','success4')
        rm=ex.get('rmse'); mx=ex.get('max_abs_error')
        if not _n(rm) or not _n(mx) or rm<0 or mx<0: raise _E('NOT_CHECKED','errs4')
        if rm>mx: raise _E('FAIL','rmse>maxabs')
        lg=ex.get('logits')
        if not isinstance(lg,list) or not lg: raise _E('NOT_CHECKED','logits')
        for p in lg:
            if not isinstance(p,dict): raise _E('NOT_CHECKED','logit')
            cp=p.get('cpu'); ob=p.get('observed'); lt=p.get('tol_abs')
            if not _n(cp) or not _n(ob) or not _n(lt) or lt<=0: raise _E('NOT_CHECKED','logit_tol')
            if abs(ob-cp)>lt: raise _E('FAIL','logit_tol_fail')
            if abs(lt-tol)>1e-12: raise _E('FAIL','fixed_tol')
        pk=a.get('allocator',{}).get('peak_bytes_by_device')
        if not isinstance(pk,dict): raise _E('NOT_CHECKED','peaks')
        np={}
        for k,v in pk.items():
            if not _s(k): raise _E('NOT_CHECKED','peak_key')
            if not _i(v) or v<=0: raise _E('NOT_CHECKED','peak_int')
            np[_l(k)]=v
        if set(np)!=P['four']['canon']: raise _E('NOT_CHECKED','peak_set')
        ws=a.get('weights')
        if not isinstance(ws,list) or not ws: raise _E('NOT_CHECKED','weights')
        sh=set(); tot=0
        for w in ws:
            if not isinstance(w,dict): raise _E('NOT_CHECKED','weight')
            dv=w.get('device'); h=w.get('shard_hash'); rb=w.get('resident_bytes'); bk=w.get('backing')
            if not _s(dv) or not _s(h): raise _E('NOT_CHECKED','weight_id')
            if not _i(rb) or rb<=0: raise _E('NOT_CHECKED','resident')
            if bk!='device_vram': raise _E('NOT_CHECKED','backing')
            nd=_l(dv)
            if nd not in P['four']['canon']: raise _E('FAIL','weight_dev')
            if h in sh: raise _E('FAIL','replicated_shard')
            sh.add(h)
            if np.get(nd,0)<rb: raise _E('FAIL','peak_cover')
            tot+=rb
        if len(sh)!=len(P['four']['canon']): raise _E('FAIL','shard_count')
        if tot!=mb: raise _E('FAIL','reconcile')
        return _ret('PASS','')
    except _E as e:
        return _ret(e.st,e.m)
    except Exception as e:
        return _ret('NOT_CHECKED','unexpected:'+repr(e))