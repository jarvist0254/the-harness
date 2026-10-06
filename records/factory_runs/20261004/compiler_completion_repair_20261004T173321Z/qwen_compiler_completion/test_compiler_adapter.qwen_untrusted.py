import sys
import types
import threading
import unittest

ADAPTER_SRC = '''import threading

_COMPILER_ROOT_EXITED_CLEANUP_REQUIRED = "COMPILER_ROOT_EXITED_CLEANUP_REQUIRED"
_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 258
_SLEEP_SECONDS = 0.02

def _compiler_wait_run(deps, kernel, job, spec, owned, threads, slots, overflow_event, cancel_event, dead_by):
    wapi = deps["_winapi"]
    mono_fn = deps.get("monotonic")
    sleep_fn = deps.get("sleep")
    if mono_fn is None:
        import time
        mono_fn = time.monotonic
    if sleep_fn is None:
        import time
        sleep_fn = time.sleep
    if spec.get("policy") != "kill_on_close":
        return "UNKNOWN", "policy_mismatch"
    workers = spec.get("workers", [])
    if len(workers) != 1 or len(owned) != 1:
        return "UNKNOWN", "worker_count_mismatch"
    rec = owned[0]
    if not rec.get("assigned") or not rec.get("resumed"):
        return "UNKNOWN", "not_assigned_resumed"
    root_ph = rec.get("ph")
    if root_ph is None:
        return "UNKNOWN", "no_root_handle"
    while True:
        if cancel_event.is_set():
            return "CANCELLED", "cancelled"
        if overflow_event.is_set() or any(slot.get("overflow") for slot in slots):
            return "FAILED", "LOG_LIMIT"
        if any(slot.get("bad_read") for slot in slots):
            return "UNKNOWN", "bad_read"
        now = mono_fn()
        if now >= dead_by:
            return "TIMEOUT", "deadline"
        try:
            waited = wapi.WaitForSingleObject(root_ph, 0)
        except Exception:
            return "UNKNOWN", "wait_exception"
        rec["wait"] = waited
        if waited == _WAIT_OBJECT_0:
            break
        elif waited == _WAIT_TIMEOUT:
            sleep_fn(_SLEEP_SECONDS)
            continue
        else:
            return "UNKNOWN", "unexpected_wait_status"
    if cancel_event.is_set():
        return "CANCELLED", "cancelled"
    if overflow_event.is_set() or any(slot.get("overflow") for slot in slots):
        return "FAILED", "LOG_LIMIT"
    if any(slot.get("bad_read") for slot in slots):
        return "UNKNOWN", "bad_read"
    now = mono_fn()
    if now >= dead_by:
        return "TIMEOUT", "deadline"
    try:
        exit_code = wapi.GetExitCodeProcess(root_ph)
    except Exception:
        return "UNKNOWN", "exit_query_exception"
    rec["exit_code"] = exit_code
    if exit_code != 0:
        return "FAILED", "nonzero_exit"
    return _COMPILER_ROOT_EXITED_CLEANUP_REQUIRED, "compiler_root_zero_auxiliaries_possible"

def install(private_module):
    private_module._wait_run = _compiler_wait_run
'''

def _load_adapter():
    mod = types.ModuleType("compiler_adapter_test_copy")
    exec(ADAPTER_SRC, mod.__dict__)
    return mod

class FakeWapi:
    def __init__(self, wait_seq=None, exit_code=0, wait_exc=False, exit_exc=False):
        self.wait_seq = list(wait_seq) if wait_seq else [0]
        self.exit_code = exit_code
        self.wait_exc = wait_exc
        self.exit_exc = exit_exc
        self.wait_calls = 0
        self.exit_calls = 0
    def WaitForSingleObject(self, handle, timeout):
        self.wait_calls += 1
        if self.wait_exc:
            raise RuntimeError("fake_wait_exc")
        idx = min(self.wait_calls - 1, len(self.wait_seq) - 1)
        return self.wait_seq[idx]
    def GetExitCodeProcess(self, handle):
        self.exit_calls += 1
        if self.exit_exc:
            raise RuntimeError("fake_exit_exc")
        return self.exit_code

class FakeClock:
    def __init__(self, values):
        self.values = list(values)
        self.idx = 0
    def monotonic(self):
        v = self.values[min(self.idx, len(self.values)-1)]
        self.idx += 1
        return v

class TestCompilerAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = _load_adapter()
        self.cancel = threading.Event()
        self.overflow = threading.Event()
    def _make_env(self, wapi, clock_vals, exit_code=0, policy="kill_on_close", assigned=True, resumed=True, workers_count=1, owned_count=1, ph=1234):
        clk = FakeClock(clock_vals)
        deps = {"_winapi": wapi, "monotonic": clk.monotonic, "sleep": lambda s: None}
        spec = {"policy": policy, "workers": [{"worker_id": "w"}] * workers_count}
        owned = []
        for i in range(owned_count):
            owned.append({"ph": ph if i==0 else None, "assigned": assigned, "resumed": resumed, "worker_id": f"w{i}"})
        return deps, None, None, spec, owned, [], [{}], self.overflow, self.cancel, 100.0
    def test_root_zero_requests_cleanup(self):
        wapi = FakeWapi([0], 0)
        args = self._make_env(wapi, [0.0, 1.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "COMPILER_ROOT_EXITED_CLEANUP_REQUIRED")
        self.assertEqual(reason, "compiler_root_zero_auxiliaries_possible")
        self.assertEqual(args[4][0]["exit_code"], 0)
        self.assertEqual(args[4][0]["wait"], 0)
        self.assertEqual(wapi.exit_calls, 1)
    def test_root_nonzero_failed(self):
        wapi = FakeWapi([0], 1)
        args = self._make_env(wapi, [0.0, 1.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "FAILED")
        self.assertEqual(reason, "nonzero_exit")
    def test_deadline_before_wait(self):
        wapi = FakeWapi([258])
        args = self._make_env(wapi, [200.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "TIMEOUT")
        self.assertEqual(reason, "deadline")
    def test_deadline_after_wait(self):
        wapi = FakeWapi([0])
        args = self._make_env(wapi, [0.0, 200.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "TIMEOUT")
    def test_cancel_before_wait(self):
        wapi = FakeWapi([0])
        self.cancel.set()
        args = self._make_env(wapi, [0.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "CANCELLED")
    def test_cancel_after_wait(self):
        wapi = FakeWapi([258, 0])
        args = self._make_env(wapi, [0.0, 1.0, 2.0])
        def set_cancel(s):
            self.cancel.set()
        args[0]["sleep"] = set_cancel
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "CANCELLED")
    def test_overflow_before_wait(self):
        wapi = FakeWapi([0])
        self.overflow.set()
        args = self._make_env(wapi, [0.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "FAILED")
        self.assertEqual(reason, "LOG_LIMIT")
    def test_bad_read_before_wait(self):
        wapi = FakeWapi([0])
        args = self._make_env(wapi, [0.0])
        args[7] = [{"bad_read": True}]
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(reason, "bad_read")
    def test_overflow_after_wait(self):
        wapi = FakeWapi([0])
        args = self._make_env(wapi, [0.0, 1.0])
        self.overflow.set()
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "FAILED")
    def test_bad_read_after_wait(self):
        wapi = FakeWapi([0])
        args = self._make_env(wapi, [0.0, 1.0])
        args[7] = [{"bad_read": True}]
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
    def test_wait_exception(self):
        wapi = FakeWapi(wait_exc=True)
        args = self._make_env(wapi, [0.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(reason, "wait_exception")
    def test_exit_exception(self):
        wapi = FakeWapi([0], exit_exc=True)
        args = self._make_env(wapi, [0.0, 1.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(reason, "exit_query_exception")
    def test_unexpected_wait_status(self):
        wapi = FakeWapi([99])
        args = self._make_env(wapi, [0.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(reason, "unexpected_wait_status")
    def test_policy_mismatch(self):
        wapi = FakeWapi([0])
        args = self._make_env(wapi, [0.0], policy="explicit_terminate")
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(reason, "policy_mismatch")
    def test_worker_count_mismatch(self):
        wapi = FakeWapi([0])
        args = self._make_env(wapi, [0.0], workers_count=2, owned_count=2)
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(reason, "worker_count_mismatch")
    def test_not_assigned(self):
        wapi = FakeWapi([0])
        args = self._make_env(wapi, [0.0], assigned=False)
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "UNKNOWN")
        self.assertEqual(reason, "not_assigned_resumed")
    def test_no_side_effects_on_import(self):
        mod = types.ModuleType("side_effect_check")
        exec(ADAPTER_SRC, mod.__dict__)
        self.assertTrue(hasattr(mod, "install"))
        self.assertTrue(hasattr(mod, "_compiler_wait_run"))
    def test_install_replaces_wait_run(self):
        pm = types.ModuleType("private_mod")
        pm._wait_run = lambda: "original"
        self.adapter.install(pm)
        self.assertIs(pm._wait_run, self.adapter._compiler_wait_run)
    def test_timeout_loop(self):
        wapi = FakeWapi([258, 258, 0])
        args = self._make_env(wapi, [0.0, 1.0, 2.0, 3.0])
        status, reason = self.adapter._compiler_wait_run(*args)
        self.assertEqual(status, "COMPILER_ROOT_EXITED_CLEANUP_REQUIRED")
        self.assertEqual(wapi.wait_calls, 3)

if __name__ == "__main__":
    unittest.main()
