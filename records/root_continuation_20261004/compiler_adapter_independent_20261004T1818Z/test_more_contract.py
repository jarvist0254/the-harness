import importlib.util
from pathlib import Path
import types
import unittest

spec = importlib.util.spec_from_file_location("root_base_controls", Path(__file__).with_name("test_post_query_guards.py"))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


class ContractTests(base.AdapterTests):
    def test_wait_exception(self):
        def fail():
            raise OSError("injected wait error")
        self.on_wait = fail
        self.assertEqual(self.run_hook()[0], "UNKNOWN")

    def test_exit_exception(self):
        def fail():
            raise OSError("injected query error")
        self.on_exit = fail
        self.assertEqual(self.run_hook()[0], "UNKNOWN")

    def test_unexpected_wait(self):
        self.wait_result = 0xffffffff
        self.assertEqual(self.run_hook()[0], "UNKNOWN")

    def test_multiple_workers(self):
        self.spec["workers"] = [{}, {}]
        self.assertEqual(self.run_hook()[0], "UNKNOWN")
        self.assertEqual(self.calls, [])

    def test_assigned_integer_not_boolean(self):
        self.rec["assigned"] = 1
        self.assertEqual(self.run_hook()[0], "UNKNOWN")
        self.assertEqual(self.calls, [])

    def test_resumed_integer_not_boolean(self):
        self.rec["resumed"] = 1
        self.assertEqual(self.run_hook()[0], "UNKNOWN")
        self.assertEqual(self.calls, [])

    def test_guard_bad_read_before_wait(self):
        self.slots[0]["bad_read"] = True
        self.assertEqual(self.run_hook()[0], "UNKNOWN")
        self.assertEqual(self.calls, [])

    def test_guard_overflow_before_wait(self):
        self.overflow.value = True
        self.assertEqual(self.run_hook()[0], "FAILED")
        self.assertEqual(self.calls, [])

    def test_guard_deadline_before_wait(self):
        self.now = 1.0
        self.assertEqual(self.run_hook()[0], "TIMEOUT")
        self.assertEqual(self.calls, [])

    def test_uses_private_supervisor_clock(self):
        def forbidden(*args):
            raise AssertionError("ad hoc dependency clock used")
        native = types.SimpleNamespace(WaitForSingleObject=self.wait, GetExitCodeProcess=self.query)
        deps = {"_winapi": native, "monotonic": forbidden, "sleep": forbidden}
        result = self.base._wait_run(deps, object(), object(), self.spec, [self.rec], [], self.slots,
                                    self.overflow, self.cancel, 1.0)
        self.assertEqual(result[0], base.SUCCESS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
