"""GPU-free contracts for the bounded OpenCL child supervisor."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

J_LINK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(J_LINK))
import opencl_executor as executor


class FakeProcess:
    def __init__(self, *, pid=12345, returncode=0, outputs=None):
        self.pid = pid
        self.returncode = returncode
        self.outputs = list(outputs or [])
        self.communicate_calls = 0
        self.kill_calls = 0

    def communicate(self, *args, **kwargs):
        self.communicate_calls += 1
        result = self.outputs.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def kill(self):
        self.kill_calls += 1


def child_json(status, *, reason="test result"):
    return json.dumps({"status": status, "reason": reason})


class ChildSupervisorContracts(unittest.TestCase):
    def launch_with(self, process):
        with mock.patch.object(executor.subprocess, "Popen", return_value=process) as popen:
            result, code = executor._child_process({"width": 512}, timeout_seconds=0.01)
        return result, code, popen

    def test_timeout_kills_and_reaps_only_owned_child(self):
        process = FakeProcess(
            pid=81001,
            outputs=[subprocess_timeout(), ("", "child cleanup complete")],
        )
        result, code, popen = self.launch_with(process)
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("60-second deadline", result["reason"])
        self.assertEqual(result["child_pid"], 81001)
        self.assertEqual(process.kill_calls, 1)
        self.assertEqual(process.communicate_calls, 2)
        popen.assert_called_once()

    def test_nonzero_native_exit_cannot_be_accepted_as_json_pass(self):
        process = FakeProcess(pid=81002, returncode=1,
                              outputs=[(child_json("PASS"), "")])
        result, code, _ = self.launch_with(process)
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["child_exit_code"], 1)

    def test_exit_two_not_checked_and_refused_are_preserved(self):
        for status in ("NOT_CHECKED", "REFUSED"):
            with self.subTest(status=status):
                process = FakeProcess(pid=81003, returncode=2,
                                      outputs=[(child_json(status), "")])
                result, code, _ = self.launch_with(process)
                self.assertEqual(code, 2)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["child_exit_code"], 2)

    def test_malformed_child_output_is_fail_closed(self):
        process = FakeProcess(pid=81004, returncode=0,
                              outputs=[("{not-json", "")])
        result, code, _ = self.launch_with(process)
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("invalid JSON", result["reason"])

    def test_oversized_child_output_is_fail_closed(self):
        process = FakeProcess(pid=81005, returncode=0,
                              outputs=[("x" * (executor.MAX_RESULT_BYTES + 1), "")])
        result, code, _ = self.launch_with(process)
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("exceeds 128 KiB", result["reason"])

    def test_atomic_result_write_error_overrides_earlier_pass(self):
        output = io.StringIO()
        missing_parent = (Path(__file__).resolve().parents[2] / "records" /
                          "opencl_executor_20261004" / "does_not_exist" / "result.json")
        with mock.patch.object(executor.sys, "stdout", output):
            code = executor._emit_json({"status": "PASS", "reason": "pre-write"},
                                       0, missing_parent)
        self.assertEqual(code, 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("Atomic result write failed", result["reason"])


def subprocess_timeout():
    import subprocess
    return subprocess.TimeoutExpired(cmd="owned-child", timeout=0.01)


if __name__ == "__main__":
    unittest.main()
