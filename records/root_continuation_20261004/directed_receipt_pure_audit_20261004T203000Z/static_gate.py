import ast,hashlib,json,pathlib
r=pathlib.Path(__file__).resolve().parent;c=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\qwen_directed_receipt');p=c/'source.OVER_BUDGET_UNTRUSTED_REVIEW_ONLY.txt'
b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='671c3706c5064aae55811020ec845402b1cfa010a224338ca78b42038261b56f'
t=ast.parse(b)
for node in t.body:
 assert isinstance(node,(ast.Import,ast.Assign,ast.ClassDef,ast.FunctionDef))
 if isinstance(node,ast.Import):assert [a.name for a in node.names]==['re']
 if isinstance(node,(ast.FunctionDef,ast.ClassDef)):assert not node.decorator_list
(r/'source_numbered.txt').write_text('\n'.join(f'{i}: {l}' for i,l in enumerate(b.decode().splitlines(),1)))
(r/'static_receipt.json').write_text(json.dumps({'status':'SAFE_FOR_ROOT_ADMITTED_PURE_QA','source_sha256':hashlib.sha256(b).hexdigest(),'provider_test_sha256':hashlib.sha256((c/'tests_source.OVER_BUDGET_UNTRUSTED_REVIEW_ONLY.txt').read_bytes()).hexdigest(),'top_level':'Only re import, literal constants/pure re.compile, undecorated class/function definitions','intake_status':'REFUSED_PRESERVED','provider_tests_executed':False},indent=2))
