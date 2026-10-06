import hashlib, json, os, subprocess, tempfile, threading, unittest
from pathlib import Path
import contained_supervisor as cs

if cs.ROOT_STATIC_ADMISSION is not True:
    raise RuntimeError("source owner root static admission required before tests")

_FIXTURES = os.name == "nt" and os.environ.get("RUN_CONTAINMENT_FIXTURES") == "1" and cs.ROOT_STATIC_ADMISSION is True

def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def _manifest(tmp, seconds=5, limit=4096, n=1, policy="explicit_terminate"):
    exe = sys_exe()
    cwd = Path(tmp)
    workers = []
    for i in range(n):
        workers.append({"worker_id": f"w{i+1}", "argv": [exe, "-c", "import time; time.sleep(0.05)"], "executable_sha256": _sha(exe), "cwd": str(cwd)})
    return {"version": 1, "run_id": "run1", "workers": workers, "deadline_seconds": seconds if seconds > 0 else 1, "startup_seconds": 5, "log_limit_bytes": limit, "containment_policy": policy}

def sys_exe():
    import sys
    return sys.executable

class CTypesProxy:
    def __init__(self, kern):
        import ctypes
        from ctypes import wintypes
        self._c = ctypes
        self._w = wintypes
        self.kern = kern
    def __getattr__(self, name):
        if name == "wintypes":
            return self._w
        return getattr(self._c, name)
    def get_last_error(self):
        return self.kern.last
    def set_last_error(self, value):
        self.kern.last = value

class FakeKernel:
    def __init__(self):
        self.calls = []
        self.last = 0
        self.fail_assign_on = None
        self.resume_code = 1
        self.collide = False
        self.flags = 0
        self.query_ok = True
        self.set_ok = True
        self.active = 0
    def CreateJobObjectW(self, _sa, name):
        self.calls.append(("create_job", name))
        self.last = 183 if self.collide else 0
        return 11
    def CloseHandle(self, handle):
        self.calls.append(("close_job", handle))
        return 1
    def AssignProcessToJobObject(self, _j, proc):
        self.calls.append(("assign", proc))
        if self.fail_assign_on is not None and sum(1 for c in self.calls if c[0] == "assign") >= self.fail_assign_on:
            self.last = 5
            return 0
        return 1
    def ResumeThread(self, thread):
        self.calls.append(("resume", thread))
        return self.resume_code
    def TerminateJobObject(self, _j, code):
        self.calls.append(("terminate_job", code))
        return 1
    def SetInformationJobObject(self, _h, cls, ptr, size):
        flags = int(ptr._obj.BasicLimitInformation.LimitFlags)
        self.calls.append(("set", cls, int(size), flags))
        self.flags = flags
        return 1 if self.set_ok else 0
    def QueryInformationJobObject(self, _h, cls, ptr, _size, _ret):
        self.calls.append(("query", cls))
        if cls == 9:
            ptr._obj.BasicLimitInformation.LimitFlags = self.flags
            return 1
        if cls == 1:
            if not self.query_ok:
                return 0
            ptr._obj.active = self.active
            ptr._obj.total = 1
            return 1
        return 0

class FakeAPI:
    def __init__(self, reads=None):
        self.calls = []
        self.proc = 100
        self.reads = list(reads or [(b"", 109)])
    def GetCurrentProcess(self):
        return 1
    def DuplicateHandle(self, *args):
        self.calls.append(("dup", args[4]))
        return 50 + len(self.calls)
    def CreatePipe(self, _sec, _size):
        self.calls.append(("pipe",))
        n = 70 + len(self.calls)
        return (n, n + 1)
    def CreateProcess(self, app, _cmd, _pa, _ta, inherit, flags, env, cwd, si):
        self.calls.append(("create", flags, list(si.lpAttributeList["handle_list"]), bool(inherit), app, dict(env), cwd))
        self.proc += 1
        return (self.proc, self.proc + 1000, 4000 + self.proc, 1)
    def CloseHandle(self, handle):
        self.calls.append(("close", handle))
        return 1
    def ReadFile(self, _h, _n):
        if self.reads:
            return self.reads.pop(0)
        return (b"", 109)
    def WaitForSingleObject(self, handle, ms):
        self.calls.append(("wait", handle, ms))
        return 0
    def GetExitCodeProcess(self, _h):
        return 0
    def TerminateProcess(self, handle, code):
        self.calls.append(("terminate_process", handle, code))
        return 1

class MV:
    def get_osfhandle(self, _fd):
        return 3

class Pure(unittest.TestCase):
    def _run(self, manifest, kern, api, cancel=None):
        import ctypes
        from ctypes import wintypes
        proxy = CTypesProxy(kern)
        deps = {"_winapi": api, "ctypes": proxy, "wintypes": wintypes, "msvcrt": MV(), "subprocess": subprocess}
        orig = (cs._imports, cs._kernel)
        cs._imports = lambda: deps
        cs._kernel = lambda _deps: kern
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = str(Path(tmp) / "out")
                return cs.run_workers(manifest, out, cancel_event=cancel), kern, api
        finally:
            cs._imports, cs._kernel = orig

    def test_admission_and_no_native_import(self):
        text = Path(cs.__file__).read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("def ") or line.startswith("class "):
                break
            self.assertNotIn("import _winapi", line)
            self.assertNotIn("WinDLL", line)
        self.assertTrue(cs.ROOT_STATIC_ADMISSION)
        self.assertTrue(callable(cs.run_workers))
        self.assertTrue(callable(cs.restart_receipt))

    def test_not_implemented_guard(self):
        orig = cs._windows
        cs._windows = lambda: False
        try:
            with self.assertRaises(NotImplementedError):
                cs.run_workers({}, "x")
            with self.assertRaises(NotImplementedError):
                cs.restart_receipt("x", "run1")
        finally:
            cs._windows = orig

    def test_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = _manifest(tmp)
            m["version"] = True
            with self.assertRaises(ValueError):
                cs._validate(m, str(Path(tmp) / "missing"))
            m = _manifest(tmp)
            m["deadline_seconds"] = True
            with self.assertRaises(ValueError):
                cs._validate(m, str(Path(tmp) / "missing"))
            m = _manifest(tmp)
            m["run_id"] = "bad id"
            with self.assertRaises(ValueError):
                cs._validate(m, str(Path(tmp) / "missing"))
            m = _manifest(tmp, n=1)
            m["workers"].append(dict(m["workers"][0]))
            with self.assertRaises(ValueError):
                cs._validate(m, str(Path(tmp) / "missing"))
            m = _manifest(tmp)
            m["workers"][0]["cwd"] = str(Path(tmp) / ".." / "evil")
            with self.assertRaises(ValueError):
                cs._validate(m, str(Path(tmp) / "missing"))
            m = _manifest(tmp)
            m["workers"][0]["executable_sha256"] = "ab" * 32
            with self.assertRaises(ValueError):
                cs._validate(m, str(Path(tmp) / "missing"))
            with self.assertRaises(ValueError):
                cs._validate(_manifest(tmp), tmp)

    def test_assign_before_resume_and_handles(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, kern, api = self._run(_manifest(tmp), FakeKernel(), FakeAPI())
        names = [c[0] for c in kern.calls]
        self.assertLess(names.index("assign"), names.index("resume"))
        created = [c for c in api.calls if c[0] == "create"][0]
        self.assertEqual(created[1], 0x00000004 | 0x08000000)
        self.assertEqual(len(created[2]), 3)
        self.assertTrue(created[3])
        self.assertNotIn("set", names)
        self.assertEqual(result["status"], "PROCESS_COMPLETED")
        self.assertTrue(result["workers"][0]["assigned"])
        self.assertTrue(result["workers"][0]["resumed"])
        self.assertEqual(result["workers"][0]["exit_code"], 0)
        self.assertFalse(result["whole_tree_certificate"])
        self.assertEqual(result["drain_proof"], "CLEANUP")

    def test_failed_assign_kills_exact_process_not_resume(self):
        kern = FakeKernel()
        kern.fail_assign_on = 1
        with tempfile.TemporaryDirectory() as tmp:
            result, kern, api = self._run(_manifest(tmp), kern, FakeAPI())
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["failure_reason"], "ASSIGN_FAILED")
        self.assertFalse(any(c[0] == "resume" for c in kern.calls))
        self.assertTrue(any(c[0] == "terminate_process" for c in api.calls))
        self.assertTrue(any(c[0] == "terminate_job" for c in kern.calls))

    def test_second_assign_failure_kills_prior_job(self):
        kern = FakeKernel()
        kern.fail_assign_on = 2
        with tempfile.TemporaryDirectory() as tmp:
            result, kern, api = self._run(_manifest(tmp, n=2), kern, FakeAPI())
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(sum(1 for c in kern.calls if c[0] == "resume"), 1)
        self.assertGreaterEqual(sum(1 for c in api.calls if c[0] == "terminate_process"), 2)
        self.assertTrue(any(c[0] == "terminate_job" for c in kern.calls))

    def test_resume_failure(self):
        kern = FakeKernel()
        kern.resume_code = 0xFFFFFFFF
        with tempfile.TemporaryDirectory() as tmp:
            result, kern, _api = self._run(_manifest(tmp), kern, FakeAPI())
        self.assertEqual(result["failure_reason"], "RESUME_FAILED")
        self.assertTrue(any(c[0] == "terminate_job" for c in kern.calls))

    def test_job_collision(self):
        kern = FakeKernel()
        kern.collide = True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(cs.WindowsJobError) as ctx:
                self._run(_manifest(tmp), kern, FakeAPI())
        self.assertEqual(ctx.exception.code, "JOB_COLLISION")
        self.assertEqual(ctx.exception.winerror, 183)
        self.assertTrue(any(c[0] == "close_job" for c in kern.calls))

    def test_kill_on_close_sets_extended_limits(self):
        import ctypes
        basic, extended = cs.job_limit_structs()
        self.assertEqual(basic.LimitFlags.offset, 16)
        self.assertEqual(basic.Affinity.size, ctypes.sizeof(ctypes.c_size_t))
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            self.assertEqual(ctypes.sizeof(basic), 64)
            self.assertEqual(basic.MinimumWorkingSetSize.offset, 24)
            self.assertEqual(basic.Affinity.offset, 48)
        self.assertGreater(ctypes.sizeof(extended), ctypes.sizeof(basic))
        with tempfile.TemporaryDirectory() as tmp:
            _result, kern, _api = self._run(_manifest(tmp, policy="kill_on_close"), FakeKernel(), FakeAPI())
        sets = [c for c in kern.calls if c[0] == "set"]
        self.assertEqual(sets[0][1], 9)
        self.assertEqual(sets[0][2], ctypes.sizeof(extended))
        self.assertEqual(sets[0][3], 0x2000)
        self.assertTrue(any(c[0] == "query" and c[1] == 9 for c in kern.calls))

    def test_query_failure_is_unknown_not_zero(self):
        kern = FakeKernel()
        kern.query_ok = False
        with tempfile.TemporaryDirectory() as tmp:
            result, _k, _a = self._run(_manifest(tmp), kern, FakeAPI())
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["job_active_count"])
        self.assertNotEqual(result["status"], "PROCESS_COMPLETED")

    def test_cancel_preserved_and_startup_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev = threading.Event(); ev.set()
            result, kern, api = self._run(_manifest(tmp), FakeKernel(), FakeAPI(), cancel=ev)
        self.assertEqual(result["status"], "CANCELLED")
        self.assertFalse(any(c[0] == "create" for c in api.calls))
        seq = iter((0, 50))
        orig = cs._monotonic
        cs._monotonic = lambda: next(seq)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                result, _k, api = self._run(_manifest(tmp), FakeKernel(), FakeAPI())
        finally:
            cs._monotonic = orig
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertEqual(result["failure_reason"], "startup_budget")
        self.assertFalse(any(c[0] == "create" for c in api.calls))

    def test_readfile_tuple_cap_and_single_close(self):
        closed = []
        ev = threading.Event()
        slot = {}
        cs._read_pipe(7, 120, slot, lambda h, n: (b"A" * 100, 0) if not closed else (b"B" * 50, 0), lambda h: closed.append(h) or True, ev)
        # first call happens before close; re-run explicit script
        calls = {"n": 0}
        def read_file(_h, _n):
            calls["n"] += 1
            if calls["n"] == 1:
                return (b"A" * 100, 0)
            if calls["n"] == 2:
                return (b"B" * 50, 0)
            return (b"", 109)
        closed.clear(); ev = threading.Event(); slot = {}
        cs._read_pipe(7, 120, slot, read_file, lambda h: closed.append(h), ev)
        self.assertTrue(slot["overflow"])
        self.assertEqual(len(slot["data"]), 120)
        self.assertEqual(closed, [7])
        self.assertTrue(ev.is_set())
        slot = {}
        cs._read_pipe(3, 100, slot, lambda _h, _n: (b"abc", 0), lambda h: closed.append(h), threading.Event())
        self.assertEqual(slot["data"], b"abc")
        self.assertFalse(slot["overflow"])

    def test_overflow_fails_and_receipt_restart(self):
        api = FakeAPI(reads=[(b"Z" * 2000, 0)])
        with tempfile.TemporaryDirectory() as tmp:
            m = _manifest(tmp, limit=1024)
            result, _k, _a = self._run(m, FakeKernel(), api)
            self.assertEqual(result["status"], "FAILED")
            self.assertEqual(result["failure_reason"], "LOG_LIMIT")
            self.assertLessEqual(result["logs"]["w1"]["stdout_bytes"], 1024)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run1.journal").write_text('{"event":"start"}\n', encoding="utf-8")
            inflight = cs.restart_receipt(str(root), "run1")
            self.assertEqual(inflight["status"], "UNKNOWN_INTERRUPTED")
            self.assertFalse(inflight["reattach"])
            self.assertFalse(inflight["replay"])
            cs._atomic_write(root / "run1_receipt.json", json.dumps({"version": 1, "run_id": "run1", "status": "PROCESS_COMPLETED"}).encode())
            done = cs.restart_receipt(str(root), "run1")
            self.assertEqual(done["status"], "PROCESS_COMPLETED")
            self.assertFalse(done["replay"])

@unittest.skipUnless(_FIXTURES, "OPT-IN Windows process fixtures")
class Fixtures(unittest.TestCase):
    def _m(self, tmp, code, deadline=5, limit=4096):
        import sys
        exe = sys.executable
        return {"version": 1, "run_id": "fx", "workers": [{"worker_id": "w1", "argv": [exe, "-c", code], "executable_sha256": _sha(exe), "cwd": tmp}], "deadline_seconds": deadline, "startup_seconds": 5, "log_limit_bytes": limit, "containment_policy": "explicit_terminate"}

    def test_cancel_timeout_nonzero_overflow_grandchild(self):
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            ev = threading.Event()
            threading.Timer(0.3, ev.set).start()
            cancelled = cs.run_workers(self._m(tmp, "import time; time.sleep(30)", deadline=10), str(Path(tmp)/"c"), cancel_event=ev)
            self.assertEqual(cancelled["status"], "CANCELLED")
            timed = cs.run_workers(self._m(tmp, "import time; time.sleep(30)", deadline=1), str(Path(tmp)/"t"))
            self.assertEqual(timed["status"], "TIMEOUT")
            failed = cs.run_workers(self._m(tmp, "import sys; sys.exit(3)"), str(Path(tmp)/"n"))
            self.assertEqual(failed["status"], "FAILED")
            self.assertEqual(failed["workers"][0]["exit_code"], 3)
            flooded = cs.run_workers(self._m(tmp, "import sys; sys.stdout.write('A'*5000); sys.stdout.flush()", limit=1024), str(Path(tmp)/"o"))
            self.assertEqual(flooded["status"], "FAILED")
            self.assertEqual(flooded["failure_reason"], "LOG_LIMIT")
            self.assertLessEqual(flooded["logs"]["w1"]["stdout_bytes"], 1024)
            child = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); time.sleep(0.2)"
            grand = cs.run_workers(self._m(tmp, child, deadline=2), str(Path(tmp)/"g"))
            self.assertNotEqual(grand["status"], "PROCESS_COMPLETED")
            self.assertIn(grand["status"], ("TIMEOUT", "FAILED", "UNKNOWN"))
            self.assertFalse(grand["whole_tree_certificate"])

if __name__ == "__main__":
    unittest.main()

