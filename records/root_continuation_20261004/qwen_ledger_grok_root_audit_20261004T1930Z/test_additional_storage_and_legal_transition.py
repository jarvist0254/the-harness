"""Additional source-only controls; ROOT execution admission is still required."""
import importlib.util
import pathlib
import unittest
s=importlib.util.spec_from_file_location('independent_same17',pathlib.Path(__file__).with_name('test_independent_same17_adapted.py'))
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)
sl=m.sl
class Additional(unittest.TestCase):
    def test_returned_wrapper_storage_cannot_rewrite_history(self):
        ledger=sl.StateLedger().append({'state':'FAILED_NUMERIC','experiment_id':'old'})
        try:ledger.records()[0]._items['state']='DIAGNOSTIC_ONLY'
        except (TypeError,AttributeError):return
        self.assertEqual(ledger.records()[0]['state'],'FAILED_NUMERIC')
    def test_returned_nested_wrapper_storage_cannot_reassign(self):
        ledger=sl.StateLedger().append({'state':'PENDING','experiment_id':'x','metadata':{'pins':['original']}})
        try:ledger.records()[0]['metadata']['pins']._items=('forged',)
        except (TypeError,AttributeError):return
        self.assertEqual(ledger.records()[0]['metadata']['pins'],['original'])
    def test_actual_legal_prior_transition_does_not_require_claim(self):
        ledger=sl.StateLedger().append({'state':'PENDING','experiment_id':'x'})
        ledger=ledger.append({'state':'RUNNING','experiment_id':'x','prior_state':'PENDING'})
        terminal=ledger.append({'state':'FAILED_NUMERIC','experiment_id':'x'})
        self.assertEqual(terminal.records()[-1]['state'],'FAILED_NUMERIC')
if __name__=='__main__':unittest.main(verbosity=2)
