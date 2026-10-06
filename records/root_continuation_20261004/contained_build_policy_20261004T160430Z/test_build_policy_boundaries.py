"""Pure validation tests for the isolated build-only supervisor policy copy."""
import builtins
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
BASELINE_PATH = Path(
    r"E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor_revision2.py"
)
CANDIDATE_PATH = HERE / "contained_build_supervisor.py"
BASELINE_SHA256 = "3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c"
CANDIDATE_SHA256 = "fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3"
DENIED_IMPORTS = {"_winapi", "ctypes", "msvcrt", "subprocess"}
FORBIDDEN_IMPORT_ATTEMPTS = []


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".", 1)[0] in DENIED_IMPORTS:
        FORBIDDEN_IMPORT_ATTEMPTS.append(name)
        raise AssertionError(f"native/process import forbidden in validation test: {name}")
    return _REAL_IMPORT(name, globals, locals, fromlist, level)


_REAL_IMPORT = builtins.__import__


def _load_pinned_module(path, module_name, expected_sha256):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise AssertionError(f"source pin mismatch: {path}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.object(builtins, "__import__", _guarded_import):
        spec.loader.exec_module(module)
    return module


class BuildPolicyBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = _load_pinned_module(
            BASELINE_PATH, "contained_supervisor_baseline_pure_tests", BASELINE_SHA256
        )
        cls.candidate = _load_pinned_module(
            CANDIDATE_PATH, "contained_build_supervisor_pure_tests", CANDIDATE_SHA256
        )
        cls.executable = Path(sys.executable).resolve()
        cls.executable_sha256 = hashlib.sha256(cls.executable.read_bytes()).hexdigest()

    def _validate(self, module, *, deadline=60, log_limit=1024):
        with tempfile.TemporaryDirectory(prefix="build_policy_pure_") as temp:
            root = Path(temp)
            output = root / "fresh_output"
            manifest = {
                "version": 1,
                "run_id": "pure_boundary",
                "workers": [{
                    "worker_id": "validation_only",
                    "argv": [str(self.executable), "-c", "pass"],
                    "executable_sha256": self.executable_sha256,
                    "cwd": str(root),
                }],
                "deadline_seconds": deadline,
                "startup_seconds": 5,
                "log_limit_bytes": log_limit,
                "containment_policy": "kill_on_close",
            }
            return module._validate(manifest, output)

    def test_candidate_is_exactly_one_literal_change(self):
        baseline = BASELINE_PATH.read_bytes()
        candidate = CANDIDATE_PATH.read_bytes()
        old = b'_int(manifest.get("deadline_seconds"), 1, 60, "deadline")'
        new = b'_int(manifest.get("deadline_seconds"), 1, 600, "deadline")'
        self.assertEqual(hashlib.sha256(baseline).hexdigest(), BASELINE_SHA256)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), CANDIDATE_SHA256)
        self.assertEqual(baseline.count(old), 1)
        self.assertEqual(candidate, baseline.replace(old, new, 1))

    def test_old_supervisor_keeps_original_deadline_boundary(self):
        self.assertEqual(self._validate(self.baseline, deadline=60)["deadline"], 60)
        for value in (61, 600):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self._validate(self.baseline, deadline=value)

    def test_build_policy_accepts_only_integer_deadlines_through_600(self):
        for value in (1, 60, 61, 600):
            with self.subTest(value=value):
                self.assertEqual(self._validate(self.candidate, deadline=value)["deadline"], value)
        for value in (0, 601, True, 1.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self._validate(self.candidate, deadline=value)

    def test_log_limit_stays_capped_at_131072(self):
        self.assertEqual(self._validate(self.candidate, log_limit=131072)["log_limit"], 131072)
        with self.assertRaises(ValueError):
            self._validate(self.candidate, log_limit=133000)

    def test_import_and_validation_never_request_native_or_process_modules(self):
        self._validate(self.candidate, deadline=1, log_limit=1024)
        self.assertEqual(FORBIDDEN_IMPORT_ATTEMPTS, [])


if __name__ == "__main__":
    unittest.main()
