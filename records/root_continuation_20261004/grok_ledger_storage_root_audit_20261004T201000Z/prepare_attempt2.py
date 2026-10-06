import ast,difflib,hashlib,json,pathlib
r=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\grok_ledger_storage_root_audit_20261004T201000Z');assert r.is_dir()
c=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_ledger_storage_repair_20261004T195014Z\grok_ledger_storage_high')
old=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\qwen_ledger_grok_root_audit_20261004T1930Z')
pins={'source.grok_untrusted.py':'e44e86db99225b95cb9c9b63a41987d978e692eb0efc3f431741e2adf28833df','tests_source.grok_untrusted.py':'938739185fe5e6e12d115639160a228a6f917a20a18bd7368bb16231ccdf7869'}
for n,h in pins.items():
 b=(c/n).read_bytes();assert hashlib.sha256(b).hexdigest()==h
 tree=ast.parse(b)
 (r/(n+'.numbered.txt')).write_text('\n'.join(f'{i}: {line}' for i,line in enumerate(b.decode().splitlines(),1)),encoding='utf-8')
 if n.startswith('source.'):
  for node in tree.body:
   assert isinstance(node,(ast.Import,ast.Assign,ast.FunctionDef,ast.ClassDef))
   if isinstance(node,ast.Import):assert all(x.name in ('hashlib','json','math') for x in node.names)
   if isinstance(node,ast.Assign):
    if ast.unparse(node.value)=='tuple(range(16))': pass
    else: ast.literal_eval(node.value)
  for node in ast.walk(tree):
   if isinstance(node,(ast.FunctionDef,ast.ClassDef)):assert not node.decorator_list
text=(old/'test_independent_same17_adapted.py').read_text()
new=text.replace(str(pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_numeric_ledger_correction_20261004T191800Z\grok_numeric_ledger_high\source.grok_untrusted.py')),str(c/'source.grok_untrusted.py')).replace('d73ebcd2570d955fd81732e706803e701159a040d4bd3326f2377af6a9bbae6a',pins['source.grok_untrusted.py'])
assert new!=text
(r/'test_independent_same17_adapted.py').write_text(new,encoding='utf-8')
(r/'test_additional_storage_and_legal_transition.py').write_bytes((old/'test_additional_storage_and_legal_transition.py').read_bytes())
(r/'test_adapter.diff').write_text(''.join(difflib.unified_diff(text.splitlines(True),new.splitlines(True),fromfile='prior_exact17',tofile='storage_repair_exact17')),encoding='utf-8')
receipt={'status':'STATIC_SAFE_FOR_ROOT_ADMITTED_PURE_QA','source_pins':pins,'source_top_level':'Only stdlib imports, literal constants, undecorated functions/classes; no execution/import-time API calls','adaptation':'Only source path and SHA in original17; additional3 exact byte copy; no candidate duplicate implementation','provider_tests':'Fully read, NOT_EXECUTED; imports state_ledger rather than exact delivered path, so not independent acceptance'}
(r/'static_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))

