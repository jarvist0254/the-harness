import ast,hashlib,json,pathlib
r=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\l0_peer_original_compile_20261004T202500Z');r.mkdir()
a=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\qwen_l0_peer_copy\answer.raw.txt')
def pairs(items):
 d={}
 for k,v in items:
  if k in d:raise ValueError('duplicate JSON key')
  d[k]=v
 return d
raw=a.read_bytes();obj=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs)
assert obj['status']=='PROPOSED' and isinstance(obj['source'],str)
b=obj['source'].encode('utf-8');(r/'source.original_untrusted.cpp').write_bytes(b)
(r/'source_with_line_numbers.txt').write_text('\n'.join(f'{i}: {l}' for i,l in enumerate(obj['source'].splitlines(),1)),encoding='utf-8')
header=pathlib.Path(r'E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h')
receipt={'intake_original_status':'REFUSED','provider_declared_status':obj['status'],'source_bytes':len(b),'source_chars':len(obj['source']),'source_sha256':hashlib.sha256(b).hexdigest(),'raw_answer_sha256':hashlib.sha256(raw).hexdigest(),'header_path':str(header),'header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'extraction':'Exact UTF8 source string, no trimming/newline conversion or edits','runtime_linking':'NOT_RUN'}
(r/'extraction_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
