import difflib,hashlib,json,pathlib
A=pathlib.Path(__file__).parent
OLD=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\l0_query_replacement_audit_20261004T211418Z\stub_build_20261004T213121Z')
R=A/'build_20261004T214702Z';R.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=(A/'source.local_derivative.cpp').read_text()
before=s
find='else lzq_str(w,Q(null)); lzq_comma(w,pf); lzq_field(w,Q(props_flags));'
assert s.count(find)==1
s=s.replace(find,'else lzq_str(w,Q(null)); lzq_comma(w,pf); lzq_field(w,Q(can_result_code)); if(p.self) lzq_str(w,Q(null)); else lzq_u64(w,uint64_t(p.can_r)); lzq_comma(w,pf); lzq_field(w,Q(props_flags));')
find='if(p.props_valid) lzq_u64(w,p.props_flags); else lzq_str(w,Q(null)); lzq_ch(w,\'}\');'
assert s.count(find)==1
s=s.replace(find,'if(p.props_valid) lzq_u64(w,p.props_flags); else lzq_str(w,Q(null)); lzq_comma(w,pf); lzq_field(w,Q(props_result_code)); if(p.can_valid&&p.can) lzq_u64(w,uint64_t(p.props_r)); else lzq_str(w,Q(null)); lzq_ch(w,\'}\');')
source=A/'source.local_derivative_revision2.cpp';source.write_text(s)
(A/'query_result_receipt.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='four_measured_fixes',tofile=source.name)))
stub=(A/'actual_header_stub_local.cpp').read_text().replace('source.local_derivative.cpp',source.name)
stub_path=A/'actual_header_stub_local_revision2.cpp';stub_path.write_text(stub)
for name in ['run_owned_compile.py','tool_pin.json']:(R/name).write_bytes((OLD/name).read_bytes())
controller=(OLD/'compile_controller.py').read_text().replace("source=R.parent/'source.original_untrusted.cpp'", "source=R.parent/'source.local_derivative_revision2.cpp'").replace('9f2635be587804c88c2988066142ef4c307d98adc0afc4649422a39ac880b694',sha(source)).replace("stub=R.parent/'actual_header_stub_DRAFT.cpp'","stub=R.parent/'actual_header_stub_local_revision2.cpp'").replace('b551a78647c0deb835edefaab04368e15abf0650998a9d1f657f6c13d7af8427',sha(stub_path))
(R/'compile_controller.py').write_text(controller)
cmd=(OLD/'compile_only.cmd').read_text().replace(str(OLD),str(R)).replace(str(OLD.parent/'actual_header_stub_DRAFT.cpp'),str(stub_path))
(R/'compile_only.cmd').write_bytes(cmd.replace('\n','\r\n').encode())
runner=(OLD/'run_stub_cases.py').read_text().replace("A/'source.original_untrusted.cpp'","A/'source.local_derivative_revision2.cpp'").replace('9f2635be587804c88c2988066142ef4c307d98adc0afc4649422a39ac880b694',sha(source)).replace("A/'actual_header_stub_DRAFT.cpp'","A/'actual_header_stub_local_revision2.cpp'").replace('b551a78647c0deb835edefaab04368e15abf0650998a9d1f657f6c13d7af8427',sha(stub_path))
(R/'run_stub_cases.py').write_text(runner)
(R/'run_owned_stub.py').write_bytes((OLD/'run_owned_stub.py').read_bytes())
(A/'final_source_and_stub_pins.json').write_text(json.dumps({'source':{'path':str(source),'sha256':sha(source)},'stub':{'path':str(stub_path),'sha256':sha(stub_path)},'originals_preserved':True,'intermediate_snapshots_not_executed':True,'status':'ROOT_AUTHORIZED_CPU_STUB_QA_NOT_PROMOTED'},indent=2))
print(json.dumps({'source':sha(source),'stub':sha(stub_path),'build':str(R)},indent=2))
