import unittest
from test_receipt_requirements import Gates,doc,read
class Extended(Gates):
 def test_duplicate_flag_no_API(self):
  d=doc('duplicate_flag_cli');self.assertEqual((d['status'],d['exit_code']),('FAIL',1));self.assertRegex(read('duplicate_flag_cli','stderr'),r'api_calls=0(?: |$)')
 def test_each_submitted_stage_timeout_quarantines(self):
  for name in ['fence_timeout_copy','fence_timeout_readback','fence_timeout_corrupt']:
   with self.subTest(stage=name):
    d=doc(name);self.assertEqual(d['api'],'zeFenceHostSynchronize');self.assertEqual(d['resource_state'],'TERMINAL_QUARANTINE');self.assertIs(d['cleanup_verified'],False);self.assertTrue(d['destruction_skipped']);e=read(name,'stderr');calls=[s for s in e.splitlines() if s.startswith('FAKE_CALL ')];self.assertEqual(calls[-1],'FAKE_CALL zeFenceHostSynchronize');self.assertNotIn('teardown_while_pending',e);self.assertRegex(e,r'FAKE_PENDING .*pending=1 .*frees=0 ')
if __name__=='__main__':unittest.main()
