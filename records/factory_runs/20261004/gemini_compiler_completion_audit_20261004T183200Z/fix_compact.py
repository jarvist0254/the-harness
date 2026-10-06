from pathlib import Path
p=Path(r'E:\the_harness\records\factory_runs\20261004\gemini_compiler_completion_audit_20261004T183200Z\prepare_compact_review.py')
s=p.read_text(encoding='utf-8')
s=s.replace("reason[:220]","reason[:120]").replace("fix[:140]","fix[:100]")
s=s.replace("sup=(lines(supervisor,681,784))","sup=(lines(supervisor,701,762))")
s=s.replace("post=(base/r'records\\root_continuation_20261004\\compiler_adapter_independent_20261004T1818Z\\test_post_query_guards.py').read_text(encoding='utf-8')\nmore=(base/r'records\\root_continuation_20261004\\compiler_adapter_independent_20261004T1818Z\\test_more_contract.py').read_text(encoding='utf-8')","post_names='success cleanup; post-query cancel/overflow/bad-read/deadline; unexpected wait/exit types; timeout; wrong policy'\nmore_names='22 cases covering type guards, pre/post wait and query guards, exceptions, multiworker rejection, and cleanup request'")
s=s.replace("proof_test=(proofdir/'test_actual_cleanup_demotions.py').read_text(encoding='utf-8')\n","")
start=s.index('FOUR-CASE TEST SOURCE:\\n{proof_test}')
end=s.index('22-TEST PURE GREEN LOG:',start)
s=s[:start]+"FOUR-CASE TEST CASES: job close, owned-handle close, reader state, and shutdown failure. Each pure mock returned custom status with UNKNOWN_DRAIN, and actual native_driver.validate_result refused it. No native process calls.\\nPOST-QUERY TEST CASES: {post_names}\\nADDITIONAL CONTRACT TEST SUMMARY: {more_names}\\n"+s[end:]
p.write_text(s,encoding='utf-8')
