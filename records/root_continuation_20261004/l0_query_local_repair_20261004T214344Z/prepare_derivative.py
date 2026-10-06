"""Root-authorized local derivative; sequential source-only change snapshots."""
import difflib,hashlib,json,pathlib
R=pathlib.Path(__file__).parent
OLD=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z')
raw=(OLD/'source.original_untrusted.cpp').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='9f2635be587804c88c2988066142ef4c307d98adc0afc4649422a39ac880b694'
s=raw.decode(); edits=[]
def action(label,pairs):
    global s
    before=s
    for find,replace in pairs:
        assert s.count(find)==1,(label,find,s.count(find))
        s=s.replace(find,replace,1)
    name='revision'+str(len(edits)+1)+'_'+label+'.cpp'
    (R/name).write_bytes(s.encode())
    diff=''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='before',tofile=name))
    (R/(name+'.diff')).write_text(diff)
    edits.append({'revision':name,'scope':'SOURCE_ONLY_INTERMEDIATE_NOT_EXECUTED','sha256':hashlib.sha256(s.encode()).hexdigest(),'actions':len(pairs)})
action('json_hex', [('static void lzq_hex32(LzqW& w,uint32_t v){ lzq_ch(w,\'0\'); lzq_ch(w,\'x\'); lzq_hex8(w,v,8); }','static void lzq_hex32(LzqW& w,uint32_t v){ lzq_u64(w,uint64_t(v)); }')])
action('actual_external_query', [
 ('bool ext_ok; uint64_t ext_import;', 'bool ext_ok; ze_result_t ext_r; uint64_t ext_import;'),
 ('#if defined(ZE_STRUCTURE_TYPE_DEVICE_EXTERNAL_MEMORY_PROPERTIES)\n',''),
 ('r=zeDeviceGetExternalMemoryProperties(h,&ep); if(r==ZE_RESULT_SUCCESS)', 'r=zeDeviceGetExternalMemoryProperties(h,&ep); n.ext_r=r; if(r==ZE_RESULT_SUCCESS)'),
 ('#endif\n ++lzq_nodeCount;',' ++lzq_nodeCount;'),
 ('else lzq_str(w,Q(null)); lzq_comma(w,f); lzq_field(w,Q(queue_groups));','else lzq_str(w,Q(null)); lzq_comma(w,f); lzq_field(w,Q(external_memory_result_code)); lzq_u64(w,uint64_t(n.ext_r)); lzq_comma(w,f); lzq_field(w,Q(queue_groups));')])
before=s
for find,replace in [('Q(NOT_CHECKED2)','Q(NOT_CHECKED)'),('Q(FAIL1)','Q(FAIL)'),('Q(OK)','Q(PASS)'),('Q(REFUSED)','Q(FAIL)'),('Q(duplicate_json),2','Q(duplicate_json),1'),('Q(bad_arguments),2','Q(bad_arguments),1'),('return 2; } json=true','return 1; } json=true'),('return 2; } } static char out','return 1; } } static char out')]:
    assert find in s; s=s.replace(find,replace)
find='if(r!=ZE_RESULT_SUCCESS) return lzq_emit_simple(w,Q(NOT_CHECKED),Q(zeInit),r,Q(init_missing),2);'
assert s.count(find)==1
s=s.replace(find,'if(r!=ZE_RESULT_SUCCESS){ bool missing=r==ZE_RESULT_ERROR_UNINITIALIZED || r==ZE_RESULT_ERROR_DEPENDENCY_UNAVAILABLE || r==ZE_RESULT_ERROR_UNSUPPORTED_FEATURE; return lzq_emit_simple(w,missing?Q(NOT_CHECKED):Q(FAIL),Q(zeInit),r,missing?Q(init_missing):Q(init_failed),missing?2:1); }')
# Query observations explicitly cannot qualify transport. Both ordinary and early
# receipts carry this field; no context/allocator/transfer behavior is introduced.
find='lzq_field(w,Q(cleanup_uncertainty));'
assert s.count(find)==2
s=s.replace(find,'lzq_field(w,Q(direct_transport_qualified)); lzq_bool(w,false); lzq_ch(w,\',\'); lzq_field(w,Q(cleanup_uncertainty));')
name='revision3_status_and_scope.cpp'; (R/name).write_bytes(s.encode()); (R/(name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='revision2',tofile=name)))
edits.append({'revision':name,'scope':'SOURCE_ONLY_INTERMEDIATE_NOT_EXECUTED','sha256':hashlib.sha256(s.encode()).hexdigest(),'actions':'exact status/error classification and explicit transport refusal'})
action('root_alias_dedup',[
 ('if(r!=ZE_RESULT_SUCCESS) return r; n.uuid=p.uuid;', 'if(r!=ZE_RESULT_SUCCESS) return r; if(!isSub){ for(uint32_t k=0;k<lzq_nodeCount;++k){ const LzqNode& prior=lzq_nodes[k]; if(!prior.is_sub && (prior.h==h || memcmp(prior.uuid.id,p.uuid.id,sizeof(p.uuid.id))==0)) return ZE_RESULT_SUCCESS; } } n.uuid=p.uuid;'),
 ('for(uint32_t ri=0;ri<got;++ri){ int rootNode=(int)lzq_nodeCount;', 'for(uint32_t ri=0;ri<got;++ri){ bool repeated=false; for(uint32_t k=0;k<lzq_nodeCount;++k){ if(!lzq_nodes[k].is_sub && lzq_nodes[k].h==roots[ri]){repeated=true;break;} } if(repeated)continue; uint32_t beforeRoot=lzq_nodeCount; int rootNode=(int)lzq_nodeCount;'),
 ('r,Q(query_failed),1); ++lzq_rootCount;', 'r,Q(query_failed),1); if(lzq_nodeCount==beforeRoot)continue; ++lzq_rootCount;')])
final=R/'source.local_derivative.cpp'; final.write_bytes(s.encode())
stub=(OLD/'actual_header_stub_DRAFT.cpp').read_bytes()
assert hashlib.sha256(stub).hexdigest()=='b551a78647c0deb835edefaab04368e15abf0650998a9d1f657f6c13d7af8427'
stub=stub.replace(b'#include "source.original_untrusted.cpp"',b'#include "source.local_derivative.cpp"')
(R/'actual_header_stub_local.cpp').write_bytes(stub)
receipt={'scope':'ROOT_AUTHORIZED_LOCAL_EXPERIMENTAL_COLLECTOR_DERIVATIVE_PENDING_PROMOTION','original_source_sha256':hashlib.sha256(raw).hexdigest(),'edits_in_order':edits,'final_source_sha256':hashlib.sha256(s.encode()).hexdigest(),'stub_only_include_changed':True,'stub_sha256':hashlib.sha256(stub).hexdigest(),'initial_test_RED':'7 tests,6 failures,1 pass','source_execution':False,'native_GPU_loader_or_API_execution':False}
(R/'derivation_receipt.json').write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt,indent=2))
