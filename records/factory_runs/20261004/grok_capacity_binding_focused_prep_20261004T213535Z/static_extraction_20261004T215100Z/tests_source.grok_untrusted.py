import copy,hashlib,importlib.util,math,os
# Binding tests only. Synthetic inputs are not hardware, P2P, or capacity proof.

def load():
    path=os.environ.get('CANDIDATE_PATH')
    if not isinstance(path,str) or path.strip()=='':
        raise AssertionError('CANDIDATE_PATH')
    spec=importlib.util.spec_from_file_location('capacity_candidate',path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn=getattr(mod,'validate_capacity',None)
    if not callable(fn):
        raise AssertionError('validate_capacity')
    return fn

def sha(b):
    return hashlib.sha256(b).hexdigest()

def dev(i,extra=None,discrete=True,form='discrete_gpu'):
    cid=str(i)
    als=[cid,'phys:'+cid,'alias:'+cid]
    if extra:
        als=als+list(extra)
    return {'canonical_id':cid,'physical_alias':'phys:'+cid,'aliases':als,'discrete':discrete,'form_factor':form}

def weights(mode='ok'):
    rows=[
        {'device':'0','shard_hash':'s0a','resident_bytes':4,'backing':'device_vram'},
        {'device':'0','shard_hash':'s0b','resident_bytes':6,'backing':'device_vram'},
        {'device':'1','shard_hash':'s1','resident_bytes':10,'backing':'device_vram'},
        {'device':'2','shard_hash':'s2','resident_bytes':10,'backing':'device_vram'},
        {'device':'3','shard_hash':'s3','resident_bytes':10,'backing':'device_vram'},
    ]
    if mode=='replicated':
        rows[1]['shard_hash']='s0a'
    elif mode=='uncovered':
        rows=[r for r in rows if r['device']!='3']
        rows[0]['resident_bytes']=14
    elif mode=='reconcile':
        rows[0]['resident_bytes']=3
    elif mode=='backing':
        rows[0]['backing']='host_ram'
    return rows

PINS={
    'model_hash':b'model-bytes',
    'workload_hash':b'workload-bytes',
    'source_hash':b'source-bytes',
    'exe_hash':b'exe-bytes',
    'context_hash':b'context-bytes',
}

def metrics(cpus,obs):
    ss=0.0
    mx=None
    for c,o in zip(cpus,obs):
        e=abs(float(o)-float(c))
        ss+=e*e
        if mx is None or e>mx:
            mx=e
    return math.sqrt(ss/len(cpus)),mx

def make(cpus=None,obs=None,single=(0,),three=(0,1,2),four=(0,1,2,3),single_rows=None,three_rows=None,four_rows=None,payload=None,digest_only=False,cpu_bytes='OMIT',omit_bytes=False,tol=0.1,logit_tol=None,rmse=None,mx=None,weight_mode='ok',requested=None,mismatch_role=None,native=None,timeout=False,policy=False,args_valid=True):
    if cpus is None:
        cpus=[1.0]
    if obs is None:
        obs=[float(c)+0.05 for c in cpus]
    if payload is None:
        payload=b'[1.0]'
    ts=1000000000000
    art={}
    trusted={}
    for k,v in PINS.items():
        art[k]=sha(v)
        trusted[k]=v
    art['quant']='q4'
    trusted['quant']='q4'
    trusted['artifact_source']='unit-artifact'
    if digest_only:
        trusted['cpu_reference_hash']=sha(payload)
        if not omit_bytes:
            trusted['cpu_reference_bytes']=payload if cpu_bytes=='OMIT' else cpu_bytes
    else:
        trusted['cpu_reference_hash']=payload if cpu_bytes=='OMIT' else cpu_bytes
    rm,mm=metrics(cpus,obs)
    if rmse is None:
        rmse=rm
    if mx is None:
        mx=mm
    if logit_tol is None:
        logit_tol=tol
    if requested is None:
        requested=40
    peaks={'0':10,'1':10,'2':10,'3':10}
    if weight_mode=='peak':
        peaks['0']=9
    logits=[{'cpu':c,'observed':o,'tol_abs':logit_tol} for c,o in zip(cpus,obs)]
    def rows(ids,custom):
        if custom is not None:
            return custom
        return [dev(i) for i in ids]
    def one(role,ds,execution,with_w=False):
        al={'class':'dedicated_vram','fresh':True,'source':'dedicated-allocator','timestamp_ns':ts}
        if with_w:
            al['peak_bytes_by_device']=dict(peaks)
        ctrl={'args_valid':args_valid,'timeout':timeout,'policy_cap':policy,'native_error':native}
        a={'role':role,'timestamp_ns':ts,'devices':ds,'controller':ctrl,'allocator':al,'execution':execution}
        pin=dict(art)
        if mismatch_role==role:
            pin['workload_hash']=sha(b'other-workload')
        a.update(pin)
        if with_w:
            a['weights']=weights(weight_mode)
        return a
    ev={
        'observed_at_ns':ts,
        'model_bytes':40,
        'logit_tol_abs':tol,
        'artifact_source':'unit-artifact',
        'cpu_reference_hash':sha(payload),
        'attempts':[
            one('single',rows(single,single_rows),{'status':'allocator_oom','requested_bytes':requested}),
            one('three',rows(three,three_rows),{'status':'allocator_oom','requested_bytes':40}),
            one('four',rows(four,four_rows),{'status':'success','rmse':rmse,'max_abs_error':mx,'logits':logits},True),
        ],
    }
    ev.update(art)
    return ev,trusted

def _ids(x,acc):
    if isinstance(x,dict):
        acc.append(id(x))
        for k in x:
            _ids(x[k],acc)
    elif isinstance(x,list):
        acc.append(id(x))
        for v in x:
            _ids(v,acc)
    elif isinstance(x,bytearray):
        acc.append(id(x))
        acc.append(bytes(x))

def call(fn,ev,tr):
    ev_s=copy.deepcopy(ev)
    tr_s=copy.deepcopy(tr)
    ie=[]; it=[]
    _ids(ev,ie); _ids(tr,it)
    out=fn(ev,trusted=tr)
    je=[]; jt=[]
    _ids(ev,je); _ids(tr,jt)
    if ev!=ev_s or tr!=tr_s or ie!=je or it!=jt:
        raise AssertionError('mutated')
    return out

def expect(fn,status,code,fragment,ev,tr,name):
    out=call(fn,ev,tr)
    errs=out.get('errors')
    ok=out.get('status')==status and out.get('exit_code')==code and 'GPU-free' in str(out.get('scope'))
    if status=='PASS':
        ok=ok and errs==[]
    else:
        ok=ok and isinstance(errs,list) and len(errs)==1 and fragment in errs[0]
    if not ok:
        raise AssertionError(name+' '+str(out.get('status'))+' '+str(errs))
    return out

def test_bindings():
    fn=load()
    ev,tr=make()
    expect(fn,'PASS',0,'',ev,tr,'legal-bytes-1.0')
    ev,tr=make(cpus=[1])
    expect(fn,'PASS',0,'',ev,tr,'int-cpu-exact')
    ev,tr=make(cpus=[2.0],payload=b'[2.0]')
    expect(fn,'PASS',0,'',ev,tr,'coherent-other-payload')
    ev,tr=make(cpus=[1.0,2.0],payload=b'[1.0,2.0]')
    expect(fn,'PASS',0,'',ev,tr,'ordered-multi')
    ev,tr=make(single=(3,),three=(1,2,3))
    expect(fn,'PASS',0,'',ev,tr,'other-subset')
    ev,tr=make(single=(0,0),three=(0,0,1,2),four=(0,0,1,2,3))
    expect(fn,'PASS',0,'',ev,tr,'repeated-root')
    ev,tr=make(single_rows=[dev(0),dev(0,['sub:0'])],three_rows=[dev(0),dev(0,['sub:0']),dev(1),dev(2)],four_rows=[dev(0),dev(0,['sub:0']),dev(1),dev(2),dev(3)])
    expect(fn,'PASS',0,'',ev,tr,'subdevice-same-root')
    ev,tr=make(digest_only=True)
    buf=bytearray(b'[1.0]')
    tr['cpu_reference_bytes']=buf
    expect(fn,'PASS',0,'',ev,tr,'digest-plus-bytes')
    if bytes(buf)!=b'[1.0]' or not isinstance(buf,bytearray):
        raise AssertionError('digest-buf')
    ev,tr=make()
    for k in PINS:
        tr[k]=bytearray(tr[k])
    slot=bytearray(b'[1.0]')
    tr['cpu_reference_hash']=slot
    expect(fn,'PASS',0,'',ev,tr,'bytearray-slots')
    if bytes(slot)!=b'[1.0]':
        raise AssertionError('slot-buf')
    rm,mm=metrics([1.0],[1.05])
    ev,tr=make(mx=mm+1e-15)
    expect(fn,'PASS',0,'',ev,tr,'metric-1e-15-still-fits')
    ev,tr=make(cpus=[2.0],obs=[2.05],payload=b'[1.0]')
    slot=bytearray(b'[1.0]')
    tr['cpu_reference_hash']=slot
    expect(fn,'FAIL',1,'cpu_ref_mismatch',ev,tr,'cpu-measured-2.0')
    if bytes(slot)!=b'[1.0]':
        raise AssertionError('measured-buf')
    ev,tr=make(cpus=[1.0],obs=[1.0],payload=b'[1.0000000000001]')
    expect(fn,'FAIL',1,'cpu_ref_mismatch',ev,tr,'cpu-no-1e-12-tolerance')
    ev,tr=make(payload=b'[1.0,2.0]')
    expect(fn,'FAIL',1,'cpu_ref_count',ev,tr,'cpu-count')
    ev,tr=make(cpus=[1.0,2.0],payload=b'[2.0,1.0]')
    expect(fn,'FAIL',1,'cpu_ref_mismatch',ev,tr,'cpu-order')
    ev,tr=make(single=(7,))
    expect(fn,'FAIL',1,'owner_subset:single',ev,tr,'single-foreign-7')
    ev,tr=make(three=(5,6,7))
    expect(fn,'FAIL',1,'owner_subset:three',ev,tr,'three-foreign-567')
    ev,tr=make(three=(0,1,7))
    expect(fn,'FAIL',1,'owner_subset:three',ev,tr,'three-partial-foreign')
    ev,tr=make(single_rows=[dev(0,['alias:1'])])
    expect(fn,'FAIL',1,'owner_subset:single',ev,tr,'single-ambiguous-alias')
    foreign=dev(7)
    foreign['index']=0
    foreign['vendor']='nvidia'
    foreign['name']='0'
    ev,tr=make(single_rows=[foreign])
    expect(fn,'FAIL',1,'owner_subset:single',ev,tr,'no-vendor-index-name-fallback')
    ev,tr=make(four=(0,1,2,3,4))
    expect(fn,'FAIL',1,'four_phys',ev,tr,'five-cards')
    ev,tr=make(digest_only=True,omit_bytes=True)
    expect(fn,'NOT_CHECKED',2,'cpu_payload_missing',ev,tr,'digest-without-bytes')
    ev,tr=make(digest_only=True,cpu_bytes=b'[2.0]')
    expect(fn,'FAIL',1,'cpu_payload_hash',ev,tr,'digest-bytes-mismatch')
    ev,tr=make(digest_only=True,cpu_bytes='[1.0]')
    expect(fn,'NOT_CHECKED',2,'cpu_payload_type',ev,tr,'payload-not-bytes')
    q=bytes([34])
    schema=[
        (b'','cpu_payload_bounds'),
        (b'[]','cpu_payload_shape'),
        (b'{}','cpu_payload_shape'),
        (b'null','cpu_payload_shape'),
        (b'true','cpu_payload_shape'),
        (q+b'1.0'+q,'cpu_payload_shape'),
        (b'[true]','cpu_payload_shape'),
        (b'['+q+b'1.0'+q+b']','cpu_payload_shape'),
        (b'[[1.0]]','cpu_payload_shape'),
        (b'[1.0, null]','cpu_payload_shape'),
        (b'[','cpu_payload_json'),
        (b'[NaN]','cpu_payload_json'),
        (b'[Infinity]','cpu_payload_json'),
        (b'[-Infinity]','cpu_payload_json'),
        (b'[1e309]','cpu_payload_json'),
        (b'[9007199254740993]','cpu_payload_json'),
        (b'['+(b'9'*400)+b']','cpu_payload_json'),
        (bytes([255,254,0]),'cpu_payload_utf8'),
        (b'0'*16777217,'cpu_payload_bounds'),
        (b'['+b','.join([b'0']*1048577)+b']','cpu_payload_shape'),
    ]
    for i,(payload,fragment) in enumerate(schema):
        ev,tr=make(payload=payload)
        expect(fn,'NOT_CHECKED',2,fragment,ev,tr,'schema-'+str(i))
    ev,tr=make(logit_tol=0.1+1e-9)
    expect(fn,'FAIL',1,'fixed_tol',ev,tr,'fixed-tol-1e-12')
    ev,tr=make(mx=mm+1e-9)
    expect(fn,'FAIL',1,'metric_recompute',ev,tr,'metric-no-widen')
    ev,tr=make(obs=[float('inf')])
    expect(fn,'NOT_CHECKED',2,'logit_tol',ev,tr,'nonfinite')
    ev,tr=make(mismatch_role='single')
    expect(fn,'FAIL',1,'bind:single',ev,tr,'oom-pin')
    ev,tr=make(requested=41)
    expect(fn,'FAIL',1,'req_mb:single',ev,tr,'oom-bytes')
    ev,tr=make(policy=True)
    expect(fn,'FAIL',1,'policy:single',ev,tr,'policy')
    ev,tr=make(timeout=True)
    expect(fn,'FAIL',1,'timeout:single',ev,tr,'timeout')
    ev,tr=make(args_valid=False)
    expect(fn,'FAIL',1,'args:single',ev,tr,'args')
    ev,tr=make(native='err')
    expect(fn,'FAIL',1,'native:single',ev,tr,'native')
    shared=dev(0)
    shared['form_factor']='shared'
    ev,tr=make(single_rows=[shared])
    expect(fn,'FAIL',1,'discrete:single',ev,tr,'shared-form')
    off=dev(0,discrete=False)
    ev,tr=make(single_rows=[off])
    expect(fn,'FAIL',1,'discrete:single',ev,tr,'not-discrete')
    ev,tr=make(weight_mode='backing')
    expect(fn,'NOT_CHECKED',2,'backing',ev,tr,'backing')
    ev,tr=make(weight_mode='replicated')
    expect(fn,'FAIL',1,'replicated_shard',ev,tr,'replicated')
    ev,tr=make(weight_mode='uncovered')
    expect(fn,'FAIL',1,'shard_coverage',ev,tr,'coverage')
    ev,tr=make(weight_mode='peak')
    expect(fn,'FAIL',1,'peak_cover',ev,tr,'peak')
    ev,tr=make(weight_mode='reconcile')
    expect(fn,'FAIL',1,'reconcile',ev,tr,'reconcile')
    ev,tr=make()
    ev['attempts']=[]
    expect(fn,'NOT_CHECKED',2,'role:single',ev,tr,'role-missing')

if __name__=='__main__':
    test_bindings()
