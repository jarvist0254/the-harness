import importlib.util
import unittest
from types import SimpleNamespace

CANDIDATE = r"E:\the_harness\records\factory_runs\20261004\coherent_repair_kv_20261004T130000Z\grok_supervisor_focus\contained_supervisor.grok_corrected.py"

def load_candidate():
    spec = importlib.util.spec_from_file_location("contained_supervisor_candidate", CANDIDATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class ShutdownCloseTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_candidate()
        self._accounting = self.mod._accounting
        self.mod._accounting = lambda deps, kernel, job: (0, 0)

    def tearDown(self):
        self.mod._accounting = self._accounting

    def _api(self, log, term_job):
        def terminate_process(handle, code):
            log.append(("tp", handle))
            return True
        def wait(handle, timeout):
            log.append(("wait", handle))
            return 0
        def query(handle):
            log.append(("query", handle))
            return 0
        wapi = SimpleNamespace(TerminateProcess=terminate_process, WaitForSingleObject=wait, GetExitCodeProcess=query, CloseHandle=lambda h: True)
        kernel = SimpleNamespace(TerminateJobObject=term_job, CloseHandle=lambda h: True)
        return {"_winapi": wapi}, kernel

    def test_termjob_false_still_waits_and_queries_all_roots(self):
        log = []
        def term_job(job, code):
            log.append(("tj",))
            return False
        deps, kernel = self._api(log, term_job)
        owned = [{"ph": 11}, {"ph": 22}]
        active, drain = self.mod._shutdown(deps, kernel, object(), owned, True)
        self.assertEqual(active, 0)
        self.assertEqual(drain, "UNKNOWN_DRAIN")
        self.assertEqual(log, [("tp", 11), ("tp", 22), ("tj",), ("wait", 11), ("query", 11), ("wait", 22), ("query", 22)])
        self.assertEqual(owned[0]["exit_code"], 0)
        self.assertEqual(owned[1]["exit_code"], 0)

    def test_termjob_exception_still_waits_and_queries_all_roots(self):
        log = []
        def term_job(job, code):
            log.append(("tj",))
            raise OSError("terminate")
        deps, kernel = self._api(log, term_job)
        owned = [{"ph": 11}, {"ph": 22}]
        active, drain = self.mod._shutdown(deps, kernel, object(), owned, True)
        self.assertEqual((active, drain), (0, "UNKNOWN_DRAIN"))
        self.assertEqual(log, [("tp", 11), ("tp", 22), ("tj",), ("wait", 11), ("query", 11), ("wait", 22), ("query", 22)])

    def test_failed_wait_still_waits_remaining_roots(self):
        log = []
        def term_job(job, code):
            log.append(("tj",))
            return True
        deps, kernel = self._api(log, term_job)
        def wait(handle, timeout):
            log.append(("wait", handle))
            if handle == 11:
                return 258
            return 0
        deps["_winapi"].WaitForSingleObject = wait
        owned = [{"ph": 11}, {"ph": None}, {"ph": 22}]
        active, drain = self.mod._shutdown(deps, kernel, object(), owned, True)
        self.assertEqual(drain, "UNKNOWN_DRAIN")
        self.assertEqual(active, 0)
        self.assertEqual([item for item in log if item[0] in ("wait", "query")], [("wait", 11), ("wait", 22), ("query", 22)])
        self.assertNotIn("exit_code", owned[0])
        self.assertEqual(owned[2]["exit_code"], 0)

    def test_wait_exception_then_other_root_wait_and_query(self):
        log = []
        deps, kernel = self._api(log, lambda job, code: True)
        def wait(handle, timeout):
            log.append(("wait", handle))
            if handle == 11:
                raise OSError("wait")
            return 0
        deps["_winapi"].WaitForSingleObject = wait
        owned = [{"ph": 11}, {"ph": 22}]
        active, drain = self.mod._shutdown(deps, kernel, object(), owned, True)
        self.assertEqual(drain, "UNKNOWN_DRAIN")
        self.assertIsNone(owned[0]["wait"])
        self.assertEqual([item for item in log if item[0] in ("wait", "query")], [("wait", 11), ("wait", 22), ("query", 22)])

    def test_clean_without_terminate_when_idle(self):
        log = []
        def term_job(job, code):
            raise AssertionError("terminate")
        deps, kernel = self._api(log, term_job)
        owned = [{"ph": 11}, {"ph": 22}]
        active, drain = self.mod._shutdown(deps, kernel, object(), owned, False)
        self.assertEqual((active, drain), (0, "CLEANUP"))
        self.assertEqual(log, [("wait", 11), ("query", 11), ("wait", 22), ("query", 22)])

    def test_each_close_false_or_exception_continues(self):
        log = []
        def close(handle):
            log.append(handle)
            if handle == "th1":
                return False
            if handle == "ph1":
                raise OSError("close")
            if handle == "th2":
                return False
            return True
        owned = [{"th": "th1", "ph": "ph1"}, {"th": "th2", "ph": "ph2"}]
        self.assertIs(self.mod._close_owned(SimpleNamespace(CloseHandle=close), owned), False)
        self.assertEqual(log, ["th1", "ph1", "th2", "ph2"])
        self.assertEqual(owned[0]["th"], "th1")
        self.assertEqual(owned[0]["ph"], "ph1")
        self.assertEqual(owned[1]["th"], "th2")
        self.assertIsNone(owned[1]["ph"])
        self.assertTrue(all(rec.get("close_uncertain") is True for rec in owned))

    def test_close_quiet_false_and_exception_drain_rest(self):
        log = []
        def close(handle):
            log.append(handle)
            if handle == 2:
                return False
            if handle == 1:
                raise OSError("close")
            return True
        handles = [1, 2, 3]
        self.assertIs(self.mod._close_quiet(close, handles), False)
        self.assertEqual(log, [3, 2, 1])
        self.assertEqual(handles, [])

    def test_close_owned_false_flows_into_run_workers_drain(self):
        mod = self.mod
        log = []
        class Output:
            def mkdir(self):
                return None
            def is_dir(self):
                return True
        spec = {"run_id": "r", "policy": "explicit", "output": Output()}
        def launch(deps, kernel, job, spec, owned, threads, slots, overflow, cancel):
            owned.append({"ph": 11, "th": 12})
            return "PROCESS_COMPLETED", "ok"
        def close(handle):
            log.append(handle)
            return False
        def emit(spec, status, reason, owned, slots, active, drain):
            return {"status": status, "failure_reason": reason, "drain_proof": drain, "active": active}
        saved = (mod._windows, mod._validate, mod._imports, mod._kernel, mod._open_job, mod._journal, mod._launch_and_wait, mod._join, mod._emit)
        wapi = SimpleNamespace(
            TerminateProcess=lambda handle, code: True,
            WaitForSingleObject=lambda handle, timeout: 0,
            GetExitCodeProcess=lambda handle: 0,
            CloseHandle=close,
        )
        kernel = SimpleNamespace(TerminateJobObject=lambda job, code: True, CloseHandle=lambda handle: True)
        try:
            mod._windows = lambda: True
            mod._validate = lambda manifest, output_root: spec
            mod._imports = lambda: {"_winapi": wapi}
            mod._kernel = lambda deps: kernel
            mod._open_job = lambda deps, kernel, run_id: object()
            mod._journal = lambda spec, event: None
            mod._launch_and_wait = launch
            mod._join = lambda threads, timeout: None
            mod._emit = emit
            result = mod.run_workers({}, "unused")
        finally:
            (mod._windows, mod._validate, mod._imports, mod._kernel, mod._open_job, mod._journal, mod._launch_and_wait, mod._join, mod._emit) = saved
        self.assertEqual(log, [12, 11])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["failure_reason"], "close_uncertain")
        self.assertEqual(result["drain_proof"], "UNKNOWN_DRAIN")

    def test_timeout_stays_terminal_when_termjob_false(self):
        mod = self.mod
        class Output:
            def mkdir(self):
                return None
            def is_dir(self):
                return True
        spec = {"run_id": "r", "policy": "explicit", "output": Output()}
        def launch(deps, kernel, job, spec, owned, threads, slots, overflow, cancel):
            owned.append({"ph": 11})
            return "TIMEOUT", "budget"
        def emit(spec, status, reason, owned, slots, active, drain):
            return {"status": status, "failure_reason": reason, "drain_proof": drain}
        saved = (mod._windows, mod._validate, mod._imports, mod._kernel, mod._open_job, mod._journal, mod._launch_and_wait, mod._join, mod._emit)
        wapi = SimpleNamespace(
            TerminateProcess=lambda handle, code: True,
            WaitForSingleObject=lambda handle, timeout: 0,
            GetExitCodeProcess=lambda handle: 1,
            CloseHandle=lambda handle: True,
        )
        kernel = SimpleNamespace(TerminateJobObject=lambda job, code: False, CloseHandle=lambda handle: True)
        try:
            mod._windows = lambda: True
            mod._validate = lambda manifest, output_root: spec
            mod._imports = lambda: {"_winapi": wapi}
            mod._kernel = lambda deps: kernel
            mod._open_job = lambda deps, kernel, run_id: object()
            mod._journal = lambda spec, event: None
            mod._launch_and_wait = launch
            mod._join = lambda threads, timeout: None
            mod._emit = emit
            result = mod.run_workers({}, "unused")
        finally:
            (mod._windows, mod._validate, mod._imports, mod._kernel, mod._open_job, mod._journal, mod._launch_and_wait, mod._join, mod._emit) = saved
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertEqual(result["failure_reason"], "budget")
        self.assertEqual(result["drain_proof"], "UNKNOWN_DRAIN")

if __name__ == "__main__":
    unittest.main()

