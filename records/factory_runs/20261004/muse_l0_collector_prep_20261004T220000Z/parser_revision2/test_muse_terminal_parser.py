"""Independent JSONL-shape regression. Never calls run() or a provider."""
import importlib.util
import json
import pathlib
import sys
import unittest
import hashlib

wrapper = pathlib.Path(sys.argv.pop(1)).resolve()
spec = importlib.util.spec_from_file_location("review_wrapper_under_test", wrapper)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
GOOD = {"verdict": "REQUEST_CHANGES", "findings": [], "safety_checks": ["Scoped source review only."]}

def event(text=None, **changes):
    e = {"schema_version": 1, "payload_schema_version": 1, "payload_type": "run.terminal.completed",
         "record_type": "event", "payload": {"kind": "run_terminal", "terminal": "completed", "text": json.dumps(GOOD)}}
    if text is not None:
        e["payload"]["text"] = text
    e.update(changes)
    return e

def rows(*a):
    return ("\n".join(json.dumps(x) for x in a)+"\n").encode()

class ParserTests(unittest.TestCase):
    def accepted(self, raw):
        r = m.parse_jsonl(raw)
        self.assertEqual(r["status"], "STRUCTURED_RESULT_PARSED")
        self.assertEqual(r["result"]["verdict"], "REQUEST_CHANGES")
        return r
    def refused(self, raw):
        r = m.parse_jsonl(raw)
        self.assertNotEqual(r["status"], "STRUCTURED_RESULT_PARSED")
        self.assertIsNone(r["result"])
    def test_actual_prior_muse_terminal_json_text(self):
        p = pathlib.Path(r"E:\the_harness\records\factory_runs\20261004\muse_combined_dma_prep_20261004T205950Z\run_output\stdout.raw.jsonl")
        data = p.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), "12f31325e99fc1168298e18292f793bd49a64d9995dd782bc51ea3d0a90d4566")
        r = self.accepted(data)
        self.assertEqual(len(r["result"]["findings"]), 16)
    def test_minimal_terminal_text(self):
        self.accepted(rows(event()))
    def test_nonterminal_structured_review_is_not_terminal(self):
        self.refused(rows({"payload_type": "run.output.delta", "payload": GOOD}))
    def test_nonterminal_text_is_not_terminal(self):
        self.refused(rows({"payload_type": "run.output.delta", "payload": {"text": json.dumps(GOOD)}}))
    def test_failed_terminal_does_not_supply_accepted_review(self):
        e=event(payload_type="run.terminal.failed");e["payload"]["terminal"]="failed"
        self.refused(rows(e))
    def test_wrong_payload_kind(self):
        e=event();e["payload"]["kind"]="output_delta";self.refused(rows(e))
    def test_wrong_terminal_value(self):
        e=event();e["payload"]["terminal"]="failed";self.refused(rows(e))
    def test_boolean_schema_version(self):
        self.refused(rows(event(schema_version=True)))
    def test_wrong_payload_schema_version(self):
        self.refused(rows(event(payload_schema_version=2)))
    def test_two_terminal_records_are_ambiguous(self):
        self.refused(rows(event(),event()))
    def test_completed_then_failed_is_ambiguous(self):
        self.refused(rows(event(),event(payload_type="run.terminal.failed")))
    def test_record_after_terminal_is_not_complete_stream(self):
        self.refused(rows(event(),{"payload_type":"run.output.delta","payload":{"text":"later"}}))
    def test_duplicate_review_key(self):
        text='{"verdict":"REQUEST_CHANGES","verdict":"SUPPORT_WITH_LIMITS","findings":[],"safety_checks":["scope"]}'
        self.refused(rows(event(text)))
    def test_malformed_review_json(self):
        self.refused(rows(event("{bad}")))
    def test_dict_instead_of_review_text(self):
        e=event();e["payload"]["text"]=GOOD;self.refused(rows(e))
    def test_missing_final_newline(self):
        self.refused(rows(event()).rstrip(b"\n"))
    def test_invalid_review_schema(self):
        self.refused(rows(event(json.dumps({"verdict":"REQUEST_CHANGES","findings":[],"safety_checks":[]}))))
    def test_duplicate_outer_json_key(self):
        self.refused(b'{"payload_type":"run.terminal.completed","payload_type":"run.terminal.failed"}\n')

if __name__ == "__main__":
    unittest.main(verbosity=2)
