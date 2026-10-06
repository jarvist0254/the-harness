"""Independent receipt checks. Executes no C++ or Level Zero APIs."""
import json,os,pathlib,re,unittest
R=pathlib.Path(os.environ['PEER_CASE_ROOT'])
def read(name,stream):
 p=next(R.glob('*_'+name+'.'+stream+'.bin'));return p.read_text(encoding='utf-8')
def doc(name): return json.loads(read(name,'stdout'))
class Gates(unittest.TestCase):
 def test_clean_full_parity(self):
  d=doc('clean');self.assertEqual((d['exit_code'],d['bytes'],d['words'],d['mismatch_count']),(0,65536,16384,0));self.assertFalse(d['direct_transport_qualified'])
 def test_corruption_exact_word(self):
  d=doc('corrupt');self.assertEqual((d['exit_code'],d['mismatch_count'],d['first_bad_index'],d['fault_index']),(1,1,8192,8192))
 def test_timeout_exact_api(self): self.assertEqual(doc('fence_timeout')['api'],'zeFenceHostSynchronize')
 def test_timeout_no_pending_destruction(self): self.assertNotIn('teardown_while_pending',read('fence_timeout','stderr'))
 def test_timeout_quarantine_no_cleanup_claim(self):
  d=doc('fence_timeout');self.assertEqual(d['status'],'FAIL');self.assertTrue(d.get('destruction_skipped'));self.assertIs(d.get('cleanup_verified'),False);self.assertEqual(d.get('resource_state'),'TERMINAL_QUARANTINE')
 def test_surplus_cli_refused(self):
  d=doc('surplus_cli');self.assertEqual((d['status'],d['exit_code']),('FAIL',1))
 def test_surplus_cli_zero_API_calls(self): self.assertRegex(read('surplus_cli','stderr'),r'api_calls=0(?: |$)')
 def test_peer_unavailable(self): self.assertEqual((doc('peer_unavailable')['status'],doc('peer_unavailable')['exit_code']),('NOT_CHECKED',2))
 def test_cleanup_failure_not_success(self): self.assertEqual((doc('cleanup_failure')['status'],doc('cleanup_failure')['exit_code']),('FAIL',1))
if __name__=='__main__':unittest.main()
