"""Unit tests for j_link.residency_witness (R+2 host-activity witness)."""
import json
import subprocess
import sys
import unittest


def _run_witness(*args):
    return subprocess.run(
        [sys.executable, "-B", "j_link/residency_witness.py", "--", *args],
        capture_output=True, text=True, timeout=120)


class WitnessTest(unittest.TestCase):
    def test_noop_command_witnessed(self):
        proc = _run_witness(sys.executable, "-B", "-c", "pass")
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        receipt = json.loads(proc.stdout)
        self.assertIn(receipt["verdict"],
                      ("WITNESSED_NO_ANOMALY",
                       "HOST_GROWTH_OBSERVED_INVESTIGATE",
                       "UNMEASURABLE_ON_THIS_PLATFORM"))

    def test_exit_propagates(self):
        proc = _run_witness(sys.executable, "-B", "-c",
                            "raise SystemExit(3)")
        self.assertEqual(proc.returncode, 1)
        receipt = json.loads(proc.stdout)
        self.assertEqual(receipt["cmd_exit"], 3)

    def test_missing_command_refused(self):
        proc = subprocess.run(
            [sys.executable, "-B", "j_link/residency_witness.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
