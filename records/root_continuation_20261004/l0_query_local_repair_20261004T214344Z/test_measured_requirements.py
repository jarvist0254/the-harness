"""Receipt-based independent requirements; actual candidate runs supply data."""
import json, os, pathlib, re, unittest
ROOT=pathlib.Path(os.environ['LZQ_RECEIPT_ROOT'])
REPORT=json.loads((ROOT/'runtime_receipt.json').read_text())
CASES={c['case']:c for c in REPORT['cases']}
class MeasuredRequirements(unittest.TestCase):
    def test_normal_full_artifact_is_strict_JSON(self):
        self.assertTrue(CASES['normal']['strict_stdout_json']['valid'])
    def test_normal_queries_actual_external_properties(self):
        self.assertEqual(CASES['normal']['independent_stub_counters']['external_queries'],2)
    def test_duplicate_root_queries_two_physical_owners_only(self):
        self.assertEqual(CASES['duplicate_root']['independent_stub_counters']['external_queries'],2)
        raw=(ROOT/'runtime_duplicate_root'/'stub.stdout.log').read_text()
        # Scalar observation only; this never repairs invalid collector JSON.
        self.assertEqual(int(re.search(r'"physical_root_devices":(\d+)',raw).group(1)),2)
    def test_device_lost_is_attempted_failure(self):
        parsed=CASES['init_error']['strict_stdout_json']
        self.assertTrue(parsed['valid'])
        self.assertEqual(parsed['value']['status'],'FAIL')
        self.assertEqual(CASES['init_error']['result']['workers'][0]['exit_code'],1)
        self.assertEqual(parsed['value']['result_code'],1879048193)
    def test_no_transport_qualification_from_queries(self):
        for case in CASES.values():
            self.assertTrue(case['strict_stdout_json']['valid'])
            self.assertIs(case['strict_stdout_json']['value'].get('direct_transport_qualified'),False)
    def test_directed_relation_preserved(self):
        self.assertTrue(CASES['normal']['strict_stdout_json']['valid'])
        value=CASES['normal']['strict_stdout_json']['value']
        self.assertEqual(value['p2p']['can_matrix'],[-1,1,0,-1])
        self.assertEqual(value['p2p']['node_count'],2)
        self.assertEqual(CASES['normal']['independent_stub_counters']['peer_queries'],2)
    def test_all_owned_cleanup_proofs_are_complete(self):
        self.assertTrue(REPORT['hashes_unchanged'])
        self.assertTrue(REPORT['all_cases_cleanup_verified'])
if __name__=='__main__':unittest.main(verbosity=2)
