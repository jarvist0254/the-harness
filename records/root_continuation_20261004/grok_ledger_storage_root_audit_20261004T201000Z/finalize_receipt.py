import hashlib,json,pathlib
r=pathlib.Path(r'E:\the_harness\records\root_continuation_20261004\grok_ledger_storage_root_audit_20261004T201000Z')
receipt=json.loads((r/'execution_receipt.json').read_text())
assert receipt['hashes_unchanged'] and all(x['exit_code']==0 and x['reaped'] and x['readers_joined'] and not x['timeout'] and not x['capture']['overflow'] and not x['capture']['errors'] and not x['native_fence']['audit_denied_events'] for x in receipt['runs'])
out={'verdict':'PURE_QA_20_PASS_0_FAIL_0_ERROR_NOT_PROMOTED','same17':{'tests':17,'failures':0,'errors':0},'storage_and_legal3':{'tests':3,'failures':0,'errors':0},'source_sha256':'e44e86db99225b95cb9c9b63a41987d978e692eb0efc3f431741e2adf28833df','report_sha256':hashlib.sha256((r/'AUDIT_EXECUTED.md').read_bytes()).hexdigest(),'execution_receipt_sha256':hashlib.sha256((r/'execution_receipt.json').read_bytes()).hexdigest(),'provider_tests_executed':False,'promotion':False,'hardware_qualification':'NOT_CHECKED','prior_red_preserved':True}
(r/'adjudication_executed.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
