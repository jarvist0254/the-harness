import hashlib,json,pathlib
r=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\directed_receipt_pure_audit_20261004T203000Z'); c=pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\qwen_compact_six_prep_20261004T191000Z\qwen_directed_receipt')
before=json.loads((r/'static_receipt.json').read_text()); after=hashlib.sha256((c/'source.OVER_BUDGET_UNTRUSTED_REVIEW_ONLY.txt').read_bytes()).hexdigest();pt=hashlib.sha256((c/'tests_source.OVER_BUDGET_UNTRUSTED_REVIEW_ONLY.txt').read_bytes()).hexdigest()
assert after==before['source_sha256'] and pt==before['provider_test_sha256']
result=json.loads((r/'actual_results.json').read_text());assert result['tests']==3 and len(result['failures'])==3 and not result['errors']
files=[r/'test_independent_directed.py',r/'pure_import_fence.py',r/'run_bounded_pure.py',pathlib.Path(r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe')]
(r/'final_pin_receipt.json').write_text(json.dumps({'source_sha_before':before['source_sha256'],'source_sha_after':after,'provider_tests_sha_before':before['provider_test_sha256'],'provider_tests_sha_after':pt,'source_and_provider_tests_unchanged':True,'scripts_python_pins':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'verdict':'PURE_RED_3_FAIL_0_ERROR','provider_tests_executed':False,'native_hardware_qualification':'NOT_CHECKED'},indent=2))
