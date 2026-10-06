import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("run_muse_job.py")
spec = importlib.util.spec_from_file_location("muse_audit_runner_under_test", MODULE_PATH)
runner = importlib.util.module_from_spec(spec)
with patch("ctypes.WinDLL", side_effect=AssertionError("Win32 import-time call")), patch("subprocess.Popen", side_effect=AssertionError("process import-time call")):
    spec.loader.exec_module(runner)


def good_result():
    return {
        "verdict": "NEEDS_DISCUSSION",
        "findings": [],
        "safety_checks": ["No provider call has been observed in this fixture."],
    }


class JsonlParserTests(unittest.TestCase):
    def test_single_valid_schema_result(self):
        raw = (json.dumps({"type": "final", "payload": good_result()}) + "\n").encode()
        parsed = runner.parse_jsonl(raw)
        self.assertEqual(parsed["status"], "STRUCTURED_RESULT_PARSED")
        self.assertEqual(parsed["result"], good_result())
        self.assertEqual(parsed["usage"], "UNKNOWN")

    def test_duplicate_final_results_are_ambiguous(self):
        event = {"type": "final", "payload": good_result()}
        raw = (json.dumps(event) + "\n" + json.dumps(event) + "\n").encode()
        self.assertEqual(runner.parse_jsonl(raw)["status"], "AMBIGUOUS_RESULT")

    def test_truncated_terminal_jsonl_is_not_accepted(self):
        raw = json.dumps({"type": "final", "payload": good_result()}).encode()
        self.assertEqual(runner.parse_jsonl(raw)["status"], "TRUNCATED_JSONL")

    def test_unknown_secret_error_is_not_a_result_and_is_redacted(self):
        raw = b'{"type":"error","code":"AUTH_REJECTED","authorization":"Bearer unit-test-secret","url":"https://private.example/path?token=unit-test-secret"}\n'
        parsed = runner.parse_jsonl(raw)
        self.assertEqual(parsed["status"], "UNKNOWN_RESULT_SHAPE")
        scrubbed = runner.redact_jsonl(raw).decode()
        self.assertNotIn("unit-test-secret", scrubbed)
        self.assertIn("[REDACTED]", scrubbed)

    def test_duplicate_json_keys_are_rejected(self):
        raw = b'{"type":"final","type":"error"}\n'
        self.assertEqual(runner.parse_jsonl(raw)["status"], "INVALID_JSONL")

    def test_output_cap_fails_closed(self):
        raw = b" " * (runner.MAX_CAPTURE + 1)
        self.assertEqual(runner.parse_jsonl(raw)["status"], "OUTPUT_LIMIT")


if __name__ == "__main__":
    unittest.main()
