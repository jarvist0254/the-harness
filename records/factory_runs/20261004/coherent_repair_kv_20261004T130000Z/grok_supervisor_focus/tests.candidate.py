import shutil
import tempfile
import threading
from pathlib import Path

import supervisor_coherent as sup


def test_broken_pipe_109_is_clean_eof():
    slot = {}
    closed = []

    def read_file(handle, size):
        raise OSError(22, "broken pipe", None, 109)

    def close_handle(handle):
        closed.append(handle)

    sup._read_pipe(7, 100, slot, read_file, close_handle, threading.Event())
    assert slot["bad_read"] is False
    assert slot["closed"] is True
    assert slot["close_uncertain"] is False
    assert slot["data"] == b""
    assert closed == [7]


def test_winerror_5_is_bad_read():
    slot = {}

    def read_file(handle, size):
        raise OSError(13, "access denied", None, 5)

    sup._read_pipe(7, 100, slot, read_file, lambda h: None, threading.Event())
    assert slot["bad_read"] is True
    assert slot["closed"] is True
    assert slot["close_uncertain"] is False


def test_malformed_and_unexpected_err_are_bad():
    def run(record):
        slot = {}
        sup._read_pipe(1, 100, slot, lambda h, n: record, lambda h: None, threading.Event())
        return slot

    assert run((b"x",))["bad_read"] is True
    assert run(b"nope")["bad_read"] is True
    assert run((b"x", True))["bad_read"] is True
    assert run((b"x", 5))["bad_read"] is True
    good = run((b"abc", 0))
    assert good["bad_read"] is False and good["data"] == b"abc" and good["closed"] is True


def test_close_failure_is_not_closed_and_uncertain():
    slot = {}

    def close_handle(handle):
        raise RuntimeError("close blew up")

    sup._read_pipe(3, 10, slot, lambda h, n: (b"", 0), close_handle, threading.Event())
    assert slot["closed"] is False
    assert slot["close_uncertain"] is True
    assert slot["bad_read"] is True


def test_close_quiet_attempts_every_handle():
    seen = []

    def close_handle(handle):
        seen.append(handle)
        if handle == 2:
            raise RuntimeError("unexpected")

    handles = [1, 2, 3]
    assert sup._close_quiet(close_handle, handles) is False
    assert seen == [3, 2, 1]
    assert handles == []


def test_close_owned_attempts_remaining_handles():
    seen = []

    class Wapi:
        def CloseHandle(self, handle):
            seen.append(handle)
            if handle == "bad":
                raise RuntimeError("unexpected")

    owned = [{"th": "bad", "ph": "p1"}, {"th": "t2", "ph": "p2"}]
    assert sup._close_owned(Wapi(), owned) is False
    assert seen == ["bad", "p1", "t2", "p2"]
    assert owned[0]["th"] == "bad" and owned[0]["ph"] is None
    assert owned[1]["th"] is None and owned[1]["ph"] is None
    assert owned[0]["close_uncertain"] is True


def test_second_thread_start_closes_one_remaining_read():
    created = {"n": 0}
    read_closes = []

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=None):
            created["n"] += 1
            self.target = target
            self.args = args
            self.daemon = daemon

        def start(self):
            if created["n"] >= 2:
                raise RuntimeError("second start failed")

        def is_alive(self):
            return False

    class Wapi:
        def __init__(self):
            self.dups = 0
            self.pipes = 0

        def GetCurrentProcess(self):
            return "cur"

        def DuplicateHandle(self, *args):
            self.dups += 1
            return "D%d" % self.dups

        def CreatePipe(self, attrs, size):
            idx = self.pipes
            self.pipes += 1
            return ("R%d" % idx, "W%d" % idx)

        def CreateProcess(self, *args):
            return ("ph", "th", 9, 8)

        def CloseHandle(self, handle):
            if isinstance(handle, str) and handle.startswith("R"):
                read_closes.append(handle)

        def TerminateProcess(self, *args):
            raise AssertionError("owned process must not be terminated after transfer")

        def WaitForSingleObject(self, *args):
            raise AssertionError("owned process must not be waited after transfer")

    class Kernel:
        def AssignProcessToJobObject(self, job, ph):
            return True

        def ResumeThread(self, th):
            return 1

    class Ctypes:
        def get_last_error(self):
            return 0

    owned, threads, slots = [], [], []
    original = sup.threading.Thread
    sup.threading.Thread = FakeThread
    try:
        try:
            sup._spawn(
                {"_winapi": Wapi(), "subprocess": sup._imports.__wrapped__ if False else __import__("subprocess"), "msvcrt": __import__("msvcrt"), "ctypes": Ctypes()},
                Kernel(),
                "job",
                {"env": {}, "log_limit": 64},
                {"argv": ["C:\\worker.exe"], "cwd": "C:\\", "worker_id": "w1"},
                owned,
                threads,
                slots,
                threading.Event(),
            )
        except RuntimeError as exc:
            assert str(exc) == "second start failed"
        else:
            raise AssertionError("second start should fail")
    finally:
        sup.threading.Thread = original
    assert read_closes == ["R1"]
    assert len(threads) == 1
    assert len(owned) == 1 and owned[0]["ph"] == "ph" and owned[0]["th"] == "th"


def _patch_run(launch, journal, emit):
    root = Path(tempfile.mkdtemp())
    saved = {}
    names = ["_windows", "_validate", "_imports", "_kernel", "_open_job", "_launch_and_wait", "_shutdown", "_journal", "_emit", "_join"]
    for name in names:
        saved[name] = getattr(sup, name)

    def _validate(manifest, output_root):
        return {"run_id": "rid", "policy": "explicit", "output": root / "out"}

    class Kernel:
        def CloseHandle(self, handle):
            return None

    sup._windows = lambda: True
    sup._validate = _validate
    sup._imports = lambda: {"_winapi": object()}
    sup._kernel = lambda deps: Kernel()
    sup._open_job = lambda deps, kernel, run_id: "job"
    sup._launch_and_wait = launch
    sup._shutdown = lambda *args, **kwargs: (None, "CLEANUP")
    sup._journal = journal
    sup._emit = emit
    sup._join = lambda threads, timeout: None
    return root, saved


def _restore(saved):
    for name, value in saved.items():
        setattr(sup, name, value)


def test_receipt_failure_is_not_process_completed():
    def launch(*args, **kwargs):
        return "PROCESS_COMPLETED", None

    def journal(*args, **kwargs):
        return None

    def emit(*args, **kwargs):
        raise OSError("receipt write failed")

    root, saved = _patch_run(launch, journal, emit)
    try:
        result = sup.run_workers({"workers": []}, root)
    finally:
        _restore(saved)
        shutil.rmtree(root, ignore_errors=True)
    assert result["status"] == "FAILED"
    assert result["failure_reason"] == "UNKNOWN_DURABILITY"
    assert result["durability"] == "UNKNOWN_DURABILITY"
    assert result["status"] != "PROCESS_COMPLETED"


def test_receipt_failure_preserves_cancelled():
    def launch(*args, **kwargs):
        return "CANCELLED", "cancel"

    def emit(*args, **kwargs):
        raise OSError("receipt write failed")

    root, saved = _patch_run(launch, lambda *a, **k: None, emit)
    try:
        result = sup.run_workers({"workers": []}, root)
    finally:
        _restore(saved)
        shutil.rmtree(root, ignore_errors=True)
    assert result["status"] == "CANCELLED"
    assert result["failure_reason"] == "cancel"
    assert result["durability"] == "UNKNOWN_DURABILITY"


def test_journal_failure_is_unknown_durability_and_does_not_launch():
    launched = {}

    def launch(*args, **kwargs):
        launched["yes"] = True
        return "PROCESS_COMPLETED", None

    def journal(*args, **kwargs):
        raise OSError("journal write failed")

    def emit(spec, status, reason, owned, slots, active, drain):
        return {"status": status, "failure_reason": reason, "drain_proof": drain}

    root, saved = _patch_run(launch, journal, emit)
    try:
        result = sup.run_workers({"workers": []}, root)
    finally:
        _restore(saved)
        shutil.rmtree(root, ignore_errors=True)
    assert launched == {}
    assert result["status"] == "FAILED"
    assert result["failure_reason"] == "UNKNOWN_DURABILITY"


def main():
    test_broken_pipe_109_is_clean_eof()
    test_winerror_5_is_bad_read()
    test_malformed_and_unexpected_err_are_bad()
    test_close_failure_is_not_closed_and_uncertain()
    test_close_quiet_attempts_every_handle()
    test_close_owned_attempts_remaining_handles()
    test_second_thread_start_closes_one_remaining_read()
    test_receipt_failure_is_not_process_completed()
    test_receipt_failure_preserves_cancelled()
    test_journal_failure_is_unknown_durability_and_does_not_launch()


if __name__ == "__main__":
    main()

