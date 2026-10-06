"""Read-only diagnostic; no native API or filesystem operation at import.
Counts/control remain solely the original supervisor's authority.
"""
import json
import os
import pathlib
import time

CAP = 131072
MAX_PIDS = 64

def query_members(ctypes, wt, kernel, job):
    class Members(ctypes.Structure):
        _fields_ = [('assigned', wt.DWORD), ('returned', wt.DWORD), ('pids', ctypes.c_size_t * MAX_PIDS)]
    data = Members()
    length = wt.DWORD()
    ok = kernel.QueryInformationJobObject(job, 3, ctypes.byref(data), ctypes.sizeof(data), ctypes.byref(length))
    if not ok:
        return {'status': 'QUERY_UNKNOWN', 'winerror': ctypes.get_last_error()}
    assigned, returned = int(data.assigned), int(data.returned)
    needed = Members.pids.offset + returned * ctypes.sizeof(ctypes.c_size_t)
    if assigned > MAX_PIDS or returned > MAX_PIDS or assigned != returned or length.value < needed or length.value > ctypes.sizeof(data):
        return {'status': 'QUERY_UNKNOWN', 'reason': 'partial_or_invalid_list', 'assigned': assigned, 'returned': returned, 'returned_bytes': int(length.value)}
    images = []
    for i in range(returned):
        pid = int(data.pids[i])
        row = {'pid': pid, 'status': 'IDENTITY_UNKNOWN'}
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            row['winerror'] = ctypes.get_last_error()
            images.append(row)
            continue
        try:
            member = wt.BOOL()
            if not kernel.IsProcessInJob(handle, job, ctypes.byref(member)):
                row['winerror'] = ctypes.get_last_error()
            elif not member.value:
                row['reason'] = 'not_member_of_owned_job_at_query'
            else:
                size = wt.DWORD(32768)
                image = ctypes.create_unicode_buffer(size.value)
                if kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
                    row.update(status='IMAGE_OBSERVED', image=image.value)
                else:
                    row['winerror'] = ctypes.get_last_error()
        except Exception as exc:
            row['exception'] = type(exc).__name__
        finally:
            try:
                if not kernel.CloseHandle(handle):
                    row['close_status'] = 'UNKNOWN'
                    row['close_winerror'] = ctypes.get_last_error()
            except Exception as exc:
                row['close_status'] = 'UNKNOWN'
                row['close_exception'] = type(exc).__name__
        images.append(row)
    return {'status': 'LIST_OBSERVED', 'assigned': assigned, 'returned': returned, 'members': images, 'scope': 'Read-only sampled membership and names; races may invalidate identity'}

def native_observe(job):
    import ctypes
    from ctypes import wintypes as wt
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.QueryInformationJobObject.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
    kernel.QueryInformationJobObject.restype = wt.BOOL
    kernel.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    kernel.OpenProcess.restype = wt.HANDLE
    kernel.IsProcessInJob.argtypes = [wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.BOOL)]
    kernel.IsProcessInJob.restype = wt.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wt.BOOL
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    kernel.CloseHandle.restype = wt.BOOL
    return query_members(ctypes, wt, kernel, job)

class Trace:
    def __init__(self, path, observe=None, clock=None):
        self.path = pathlib.Path(path)
        self.observe = observe or native_observe
        self.clock = clock or time.monotonic
        self.last = None
        self.metadata = {'samples': 0, 'failures': 0, 'capped': False, 'last_error': None, 'scope': 'Diagnostic only; does not change accounting or cleanup'}
    def sample(self, job, counts):
        try:
            now = self.clock()
            if counts is None or counts[0] <= 0 or self.metadata['capped'] or (self.last is not None and now-self.last < 5):
                return
            self.last = now
            row = {'monotonic': now, 'original_counts': list(counts), 'observation': self.observe(job)}
            data = (json.dumps(row, ensure_ascii=True, separators=(',', ':')) + '\n').encode()
            with self.path.open('ab') as f:
                size = f.tell()
                if size + len(data) > CAP:
                    self.metadata['capped'] = True
                    return
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            self.metadata['samples'] += 1
        except Exception as exc:
            self.metadata['failures'] += 1
            self.metadata['last_error'] = type(exc).__name__ + ': ' + str(exc)[:256]

def install(module, folder, *, observe=None, clock=None):
    original = module._accounting
    tracer = Trace(pathlib.Path(folder)/'job_members.jsonl', observe=observe, clock=clock)
    def wrapped(deps, kernel, job):
        result = original(deps, kernel, job)
        tracer.sample(job, result)
        return result
    module._accounting = wrapped
    return tracer
