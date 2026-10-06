import hashlib,math,json
ART=('model_hash','workload_hash','source_hash','exe_hash','context_hash','quant')
HASH=('model_hash','workload_hash','source_hash','exe_hash','context_hash','cpu_reference_hash')
_FIX=1e-12  # retained tolerance contract; |claimed-actual| <= _FIX*max(1,|claimed|,|actual|)
class _E(Exception):
    def __init__(s,st,m):
        super().__init__(m); s.st=st; s.m=m
def _i(x):
    return isinstance(x,int) and not isinstance(x,bool)
def _n(x):
    return (not isinstance(x,bool)) and (isinstance(x,int) or (isinstance(x,float) and math.isfinite(x)))
def _s(x):
    return isinstance(x,str) and x.strip()!=''
def _l(x):
    return x.strip().lower()
def _hex64(x):
    return isinstance(x,str) and len(x)==64 and all(c in '0123456789abcdef' for c in x)
def _ret(st,m):
    c=0 if st=='PASS' else (1 if st=='FAIL' else 2)
    return {'status':st,'exit_code':c,'errors':[] if st=='PASS' else [m],'scope':'four discrete GPU VRAM capacity receipt; GPU-free strict validator'}
def _bind(evidence,trusted):
    if not isinstance(trusted,dict):
        raise _E('NOT_CHECKED','untrusted')
    for k in HASH:
        ev=evidence.get(k)
        if not _hex64(ev):
            raise _E('NOT_CHECKED','hash:'+k)
        pin=trusted.get(k,None)
        if isinstance(pin,(bytes,bytearray)):
            digest=hashlib.sha256(bytes(pin)).hexdigest()
        elif _hex64(pin):
            digest=pin
        elif pin is None:
            raise _E('NOT_CHECKED','registry:'+k)
        else:
            raise _E('NOT_CHECKED','registry_type:'+k)
        if digest!=ev:
            raise _E('FAIL','registry_mismatch:'+k)
    for k in ('artifact_source','quant'):
        ev=evidence.get(k); pin=trusted.get(k,None)
        if not _s(ev) or not _s(pin):
            raise _E('NOT_CHECKED','registry:'+k)
        if pin!=ev:
            raise _E('FAIL','registry_mismatch:'+k)
def _consistent(claimed,actual):
    if not _n(claimed) or not _n(actual):
        return False
    try:
        fc=float(claimed); fa=float(actual)
        diff=abs(fc-fa); scale=max(1.0,abs(fc),abs(fa))
    except (OverflowError,ValueError):
        return False
    return math.isfinite(diff) and math.isfinite(scale) and diff<=_FIX*scale
def _as_float(x):
    if isinstance(x,float):
        if not math.isfinite(x):
            raise _E('NOT_CHECKED','logit_range')
        return x
    if not _i(x):
        raise _E('NOT_CHECKED','logit_tol')
    try:
        f=float(x)
        ok=math.isfinite(f) and int(f)==x
    except (OverflowError,ValueError):
        ok=False
    if not ok:
        raise _E('NOT_CHECKED','logit_range')
    return f
def _pair_err(ob,cp):
    if not _n(ob) or not _n(cp):
        raise _E('NOT_CHECKED','logit_tol')
    d=abs(_as_float(ob)-_as_float(cp))
    if (not math.isfinite(d)) or d>1e150:
        raise _E('NOT_CHECKED','logit_range')
    return d
def _exact_cpu(x):
    if isinstance(x,bool) or not _n(x):
        raise _E('NOT_CHECKED','cpu_ref_num')
    if isinstance(x,float):
        return x
    try:
        f=float(x)
        ok=math.isfinite(f) and int(f)==x
    except (OverflowError,ValueError):
        ok=False
    if not ok:
        raise _E('NOT_CHECKED','cpu_ref_num')
    return f
def _cpu_raw(trusted,ev_hash):
    pin=trusted.get('cpu_reference_hash',None)
    if isinstance(pin,(bytes,bytearray)):
        raw=bytes(pin)
    elif _hex64(pin):
        alt=trusted.get('cpu_reference_bytes',None)
        if alt is None:
            raise _E('NOT_CHECKED','cpu_payload_missing')
        if not isinstance(alt,(bytes,bytearray)):
            raise _E('NOT_CHECKED','cpu_payload_type')
        raw=bytes(alt)
        d=hashlib.sha256(raw).hexdigest()
        if d!=pin or d!=ev_hash:
            raise _E('FAIL','cpu_payload_hash')
    else:
        raise _E('NOT_CHECKED','cpu_payload_type')
    d=hashlib.sha256(raw).hexdigest()
    if d!=ev_hash:
        raise _E('FAIL','cpu_payload_hash')
    return raw
def _cpu_numbers(raw):
    if len(raw)==0 or len(raw)>16777216:
        raise _E('NOT_CHECKED','cpu_payload_bounds')
    try:
        text=raw.decode('utf-8')
    except UnicodeDecodeError:
        raise _E('NOT_CHECKED','cpu_payload_utf8')
    def pf(s):
        try:
            v=float(s)
        except (ValueError,OverflowError):
            raise ValueError('float')
        if not math.isfinite(v):
            raise ValueError('nonfinite')
        return v
    def pi(s):
        t=s[1:] if s[:1]=='-' else s
        if len(t)>309 or not t.isdigit():
            raise ValueError('int')
        try:
            v=int(s)
            f=float(v)
            ok=math.isfinite(f) and int(f)==v
        except (ValueError,OverflowError):
            ok=False
        if not ok:
            raise ValueError('int')
        return v
    def pc(_s):
        raise ValueError('const')
    try:
        data=json.loads(text,parse_float=pf,parse_int=pi,parse_constant=pc)
    except _E:
        raise
    except Exception:
        raise _E('NOT_CHECKED','cpu_payload_json')
    if not isinstance(data,list) or not data or len(data)>1048576:
        raise _E('NOT_CHECKED','cpu_payload_shape')
    out=[]
    for v in data:
        if isinstance(v,bool) or not isinstance(v,(int,float)):
            raise _E('NOT_CHECKED','cpu_payload_shape')
        out.append(_exact_cpu(v))
    return out
def _bind_cpu(evidence,trusted,logits):
    raw=_cpu_raw(trusted,evidence.get('cpu_reference_hash'))
    ref=_cpu_numbers(raw)
    if len(ref)!=len(logits):
        raise _E('FAIL','cpu_ref_count')
    for p,want in zip(logits,ref):
        if _exact_cpu(p.get('cpu'))!=want:
            raise _E('FAIL','cpu_ref_mismatch')
def _dev_names(d):
    cid=_l(d.get('canonical_id'))
    nm={cid,_l(d.get('physical_alias'))}
    for x in d.get('aliases') or []:
        if _s(x):
            nm.add(_l(x))
    return cid,nm
def _index_owners(ds):
    owners={}
    for d in ds:
        cid,nm=_dev_names(d)
        if cid in owners:
            owners[cid]|=nm
            merged=owners[cid]
            for oc,on in owners.items():
                if oc!=cid and merged&on:
                    return None
        else:
            for on in owners.values():
                if nm&on:
                    return None
            owners[cid]=set(nm)
    return owners
def _map_subset(ds,owners,need):
    local=_index_owners(ds)
    if not isinstance(local,dict) or len(local)!=need:
        return False
    hits=[]
    for nm in local.values():
        matched=[oc for oc,on in owners.items() if nm&on]
        if len(matched)!=1:
            return False
        hits.append(matched[0])
    return len(set(hits))==need
def _bind_owners(P):
    owners=_index_owners(P['four']['a']['devices'])
    if not isinstance(owners,dict) or len(owners)!=4:
        raise _E('FAIL','owner_population')
    if not _map_subset(P['single']['a']['devices'],owners,1):
        raise _E('FAIL','owner_subset:single')
    if not _map_subset(P['three']['a']['devices'],owners,3):
        raise _E('FAIL','owner_subset:three')
def validate_capacity(evidence,*,trusted):
    try:
        if not isinstance(evidence,dict):
            raise _E('NOT_CHECKED','evidence')
        _bind(evidence,trusted)
        if not _i(evidence.get('observed_at_ns')):
            raise _E('NOT_CHECKED','observed_at_ns')
        mb=evidence.get('model_bytes')
        if not _i(mb) or mb<=0:
            raise _E('NOT_CHECKED','model_bytes')
        tol=evidence.get('logit_tol_abs')
        if not _n(tol) or tol<=0:
            raise _E('NOT_CHECKED','tol')
        ms=evidence.get('max_staleness_ns',10000000000)
        if not _i(ms) or ms<0:
            raise _E('NOT_CHECKED','staleness')
        att=evidence.get('attempts')
        if not isinstance(att,list):
            raise _E('NOT_CHECKED','attempts')
        by={}
        for a in att:
            if isinstance(a,dict) and _s(a.get('role')):
                by.setdefault(a['role'],[]).append(a)
        bind=tuple(evidence[k] for k in ART)
        P={}
        for r in ('single','three','four'):
            L=by.get(r,[])
            if len(L)!=1:
                raise _E('NOT_CHECKED','role:'+r)
            a=L[0]
            if tuple(a.get(k) for k in ART)!=bind:
                raise _E('FAIL','bind:'+r)
            if not _i(a.get('timestamp_ns')):
                raise _E('NOT_CHECKED','ts:'+r)
            if abs(a['timestamp_ns']-evidence['observed_at_ns'])>ms:
                raise _E('NOT_CHECKED','stale:'+r)
            c=a.get('controller')
            if not isinstance(c,dict):
                raise _E('NOT_CHECKED','ctrl:'+r)
            for k in ('args_valid','timeout','policy_cap'):
                if k not in c:
                    raise _E('NOT_CHECKED','ctrl.'+k)
            if c['args_valid'] is not True:
                raise _E('FAIL','args:'+r)
            if c['timeout'] is not False:
                raise _E('FAIL','timeout:'+r)
            if c['policy_cap'] is not False:
                raise _E('FAIL','policy:'+r)
            if c.get('native_error') not in (None,'',False):
                raise _E('FAIL','native:'+r)
            ds=a.get('devices')
            if not isinstance(ds,list) or not ds:
                raise _E('NOT_CHECKED','devs:'+r)
            seen=set(); canon=set(); phys=0
            for d in ds:
                if not isinstance(d,dict):
                    raise _E('NOT_CHECKED','dev:'+r)
                cid=d.get('canonical_id'); pal=d.get('physical_alias')
                if not _s(cid) or not _s(pal):
                    raise _E('NOT_CHECKED','alias:'+r)
                al=d.get('aliases')
                if not isinstance(al,list) or not al:
                    raise _E('NOT_CHECKED','aliases:'+r)
                nm={_l(cid),_l(pal)}
                for x in al:
                    if not _s(x):
                        raise _E('NOT_CHECKED','alias2:'+r)
                    nm.add(_l(x))
                if 'discrete' not in d or 'form_factor' not in d:
                    raise _E('NOT_CHECKED','form:'+r)
                if d['discrete'] is not True or d['form_factor']!='discrete_gpu':
                    raise _E('FAIL','discrete:'+r)
                if not (nm & seen):
                    phys+=1
                seen|=nm; canon.add(_l(cid))
            if len(canon)!=phys:
                raise _E('FAIL','dedup:'+r)
            al=a.get('allocator')
            if not isinstance(al,dict):
                raise _E('NOT_CHECKED','alloc:'+r)
            if al.get('class')!='dedicated_vram':
                raise _E('NOT_CHECKED','alloc_class:'+r)
            if al.get('fresh') is not True:
                raise _E('NOT_CHECKED','fresh:'+r)
            if not _s(al.get('source')):
                raise _E('NOT_CHECKED','alloc_src:'+r)
            if not _i(al.get('timestamp_ns')):
                raise _E('NOT_CHECKED','alloc_ts:'+r)
            if abs(al['timestamp_ns']-a['timestamp_ns'])>ms:
                raise _E('NOT_CHECKED','alloc_stale:'+r)
            P[r]={'a':a,'phys':phys,'canon':canon}
        if P['single']['phys']!=1:
            raise _E('FAIL','single_phys')
        if P['three']['phys']!=3:
            raise _E('FAIL','three_phys')
        if P['four']['phys']!=4:
            raise _E('FAIL','four_phys')
        for r in ('single','three'):
            ex=P[r]['a'].get('execution')
            if not isinstance(ex,dict):
                raise _E('NOT_CHECKED','exec:'+r)
            if ex.get('status')!='allocator_oom':
                raise _E('FAIL','oom:'+r)
            rb=ex.get('requested_bytes')
            if not _i(rb) or rb<=0:
                raise _E('NOT_CHECKED','req:'+r)
            if rb!=mb:
                raise _E('FAIL','req_mb:'+r)
        a=P['four']['a']; ex=a.get('execution')
        if not isinstance(ex,dict):
            raise _E('NOT_CHECKED','exec4')
        if ex.get('status')!='success':
            raise _E('FAIL','success4')
        rm=ex.get('rmse'); mx=ex.get('max_abs_error')
        if not _n(rm) or not _n(mx) or rm<0 or mx<0:
            raise _E('NOT_CHECKED','errs4')
        lg=ex.get('logits')
        if not isinstance(lg,list) or not lg:
            raise _E('NOT_CHECKED','logits')
        errs=[]
        for p in lg:
            if not isinstance(p,dict):
                raise _E('NOT_CHECKED','logit')
            cp=p.get('cpu'); ob=p.get('observed'); lt=p.get('tol_abs')
            if not _n(lt) or lt<=0:
                raise _E('NOT_CHECKED','logit_tol')
            if abs(lt-tol)>_FIX:
                raise _E('FAIL','fixed_tol')
            e=_pair_err(ob,cp)
            if e>lt:
                raise _E('FAIL','logit_tol_fail')
            errs.append(e)
        act_max=errs[0]; ss=0.0
        for e in errs:
            if e>act_max:
                act_max=e
            ss+=e*e
            if not math.isfinite(ss):
                raise _E('NOT_CHECKED','logit_range')
        act_rmse=math.sqrt(ss/len(errs))
        if not math.isfinite(act_rmse):
            raise _E('NOT_CHECKED','logit_range')
        if not _consistent(mx,act_max) or not _consistent(rm,act_rmse):
            raise _E('FAIL','metric_recompute')
        if rm>mx:
            raise _E('FAIL','rmse>maxabs')
        pk=a.get('allocator',{}).get('peak_bytes_by_device')
        if not isinstance(pk,dict):
            raise _E('NOT_CHECKED','peaks')
        npk={}
        for k,v in pk.items():
            if not _s(k):
                raise _E('NOT_CHECKED','peak_key')
            if not _i(v) or v<=0:
                raise _E('NOT_CHECKED','peak_int')
            lk=_l(k)
            if lk in npk and npk[lk]!=v:
                raise _E('FAIL','peak_dup')
            npk[lk]=v
        if set(npk)!=P['four']['canon']:
            raise _E('NOT_CHECKED','peak_set')
        ws=a.get('weights')
        if not isinstance(ws,list) or not ws:
            raise _E('NOT_CHECKED','weights')
        sh=set(); tot=0
        owned={c:0 for c in P['four']['canon']}
        summed={c:0 for c in P['four']['canon']}
        for w in ws:
            if not isinstance(w,dict):
                raise _E('NOT_CHECKED','weight')
            dv=w.get('device'); h=w.get('shard_hash'); rb=w.get('resident_bytes'); bk=w.get('backing')
            if not _s(dv) or not _s(h):
                raise _E('NOT_CHECKED','weight_id')
            if not _i(rb) or rb<=0:
                raise _E('NOT_CHECKED','resident')
            if bk!='device_vram':
                raise _E('NOT_CHECKED','backing')
            nd=_l(dv)
            if nd not in owned:
                raise _E('FAIL','weight_dev')
            if h in sh:
                raise _E('FAIL','replicated_shard')
            sh.add(h); owned[nd]+=1; summed[nd]+=rb; tot+=rb
        for c in owned:
            if owned[c]<1:
                raise _E('FAIL','shard_coverage')
            if summed[c]>npk[c]:
                raise _E('FAIL','peak_cover')
        if tot!=mb:
            raise _E('FAIL','reconcile')
        _bind_owners(P)
        _bind_cpu(evidence,trusted,lg)
        return _ret('PASS','')
    except _E as e:
        return _ret(e.st,e.m)
    except Exception as e:
        return _ret('NOT_CHECKED','unexpected:'+repr(e))
