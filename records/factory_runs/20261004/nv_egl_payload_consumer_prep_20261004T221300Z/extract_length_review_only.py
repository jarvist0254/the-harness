import pathlib,json,hashlib,datetime
B=pathlib.Path(__file__).parent;work=B/'qwen_nv_egl_payload_consumer';out=B/'LENGTH_POSTMORTEM_REVIEW_ONLY';out.mkdir(exist_ok=False)
parts=[]
for line in (work/'response.raw.sse').read_text().splitlines():
 if not line.startswith('data:'):continue
 text=line[5:].strip()
 if text=='[DONE]':continue
 data=json.loads(text)
 for c in data.get('choices',[]):
  value=c.get('delta',{}).get('content')
  if isinstance(value,str):parts.append(value)
content=''.join(parts);(out/'content.UNACCEPTED_PARTIAL_REVIEW_ONLY.txt').write_text(content,encoding='utf-8')
source=None;error=None
marker='"source"'
pos=content.find(marker)
if pos>=0:
 pos=content.find(':',pos+len(marker))+1
 try:source,end=json.JSONDecoder().raw_decode(content[pos:].lstrip())
 except Exception as e:error=type(e).__name__
if isinstance(source,str):(out/'source.COMPLETE_STRING_UNACCEPTED_REVIEW_ONLY.txt').write_text(source,encoding='utf-8')
terminal=json.loads((work/'terminal.json').read_text(encoding='utf-8-sig'))
r=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='LENGTH_NOT_ACCEPTED_NO_SCHEMA_PROMOTION',content_path=str(out/'content.UNACCEPTED_PARTIAL_REVIEW_ONLY.txt'),content_bytes=len(content.encode()),complete_source_string=isinstance(source,str),source_chars=len(source) if isinstance(source,str) else None,source_parse_error=error,reported_usage=terminal['usage'],request_max_tokens=16384,reasoning_effort='xhigh',enable_thinking=True,thinking_budget_absent=True,finish_reason=terminal['finish_reason'],source_executed=False,explanation='Reported completion99146 minus reasoning82758 =16388 tokens, near request max_tokens16384. Provider reports length despite DONE; service accounting semantics/inclusive differences cannot be proven from this response. No cap/deadline reached; completed source field alone does not satisfy full terminal JSON schema or acceptance.')
(out/'POSTMORTEM.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
