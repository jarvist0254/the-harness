"""Independent controls loading the delivered adapter, with no native APIs."""
import builtins
import importlib.util
import os
import sys
import types
import unittest

ADAPTER = os.environ.get("JLINK_ADAPTER_TEST_PATH")
SUCCESS = "COMPILER_ROOT_EXITED_CLEANUP_REQUIRED"


class Event:
    def __init__(self):
        self.value = False

    def is_set(self):
        return self.value


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.cancel = Event()
        self.overflow = Event()
        self.slots = [{"overflow": False, "bad_read": False}]
        self.wait_result = 0
        self.exit_result = 0
        self.on_wait = lambda: None
        self.on_exit = lambda: None
        self.calls = []
        self.rec = {"ph": object(), "assigned": True, "resumed": True}
        self.spec = {"policy": "kill_on_close", "workers": [{}]}
        self.base = types.SimpleNamespace(
            _monotonic=lambda: self.now,
            _sleep=self.sleep,
            _wait_run=object(),
        )
        def deny_import(name, *args, **kwargs):
            if name.split(".")[0] in {"_winapi", "ctypes", "subprocess", "multiprocessing"}:
                raise AssertionError("native/process import at adapter import/install")
            return original_import(name, *args, **kwargs)
        original_import = builtins.__import__
        builtins.__import__ = deny_import
        try:
            spec = importlib.util.spec_from_file_location("adapter_under_test", ADAPTER)
            self.adapter = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.adapter)
            before = dict(vars(self.base))
            self.adapter.install(self.base)
            self.assertEqual(set(vars(self.base)), set(before))
            for key in before:
                if key != "_wait_run":
                    self.assertIs(getattr(self.base, key), before[key])
        finally:
            builtins.__import__ = original_import

    def sleep(self, seconds):
        self.now += seconds

    def wait(self, handle, timeout):
        self.assertIs(handle, self.rec["ph"])
        self.assertEqual(timeout, 0)
        self.calls.append("wait")
        self.on_wait()
        return self.wait_result

    def query(self, handle):
        self.assertIs(handle, self.rec["ph"])
        self.calls.append("query")
        self.on_exit()
        return self.exit_result

    def run_hook(self):
        native = types.SimpleNamespace(WaitForSingleObject=self.wait, GetExitCodeProcess=self.query)
        deps = {"_winapi": native, "monotonic": lambda: self.now, "sleep": self.sleep}
        return self.base._wait_run(deps, object(), object(), self.spec, [self.rec], [], self.slots,
                                   self.overflow, self.cancel, 1.0)

    def test_success_requests_cleanup(self):
        self.assertEqual(self.run_hook()[0], SUCCESS)
        self.assertEqual(self.calls, ["wait", "query"])

    def test_nonzero_exit_refused(self):
        self.exit_result = 3
        self.assertEqual(self.run_hook()[0], "FAILED")

    def test_cancel_from_exit_query(self):
        self.on_exit = lambda: setattr(self.cancel, "value", True)
        self.assertEqual(self.run_hook()[0], "CANCELLED")

    def test_overflow_from_exit_query(self):
        self.on_exit = lambda: setattr(self.overflow, "value", True)
        self.assertEqual(self.run_hook()[0], "FAILED")

    def test_bad_read_from_exit_query(self):
        self.on_exit = lambda: self.slots[0].update(bad_read=True)
        self.assertEqual(self.run_hook()[0], "UNKNOWN")

    def test_deadline_from_exit_query(self):
        self.on_exit = lambda: setattr(self, "now", 1.0)
        self.assertEqual(self.run_hook()[0], "TIMEOUT")

    def test_cancel_from_wait_signal(self):
        self.on_wait = lambda: setattr(self.cancel, "value", True)
        self.assertEqual(self.run_hook()[0], "CANCELLED")

    def test_bad_read_from_wait_signal(self):
        self.on_wait = lambda: self.slots[0].update(bad_read=True)
        self.assertEqual(self.run_hook()[0], "UNKNOWN")

    def test_timeout(self):
        self.wait_result = 258
        self.assertEqual(self.run_hook()[0], "TIMEOUT")

    def test_bool_wait_refused(self):
        self.wait_result = False
        self.assertEqual(self.run_hook()[0], "UNKNOWN")

    def test_bool_exit_refused(self):
        self.exit_result = False
        self.assertEqual(self.run_hook()[0], "UNKNOWN")

    def test_wrong_policy_refused(self):
        self.spec["policy"] = "explicit_terminate"
        self.assertEqual(self.run_hook()[0], "UNKNOWN")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    if not ADAPTER:
        raise SystemExit("JLINK_ADAPTER_TEST_PATH is required")
    unittest.main(verbosity=2)
