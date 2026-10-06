"""ROOT-admitted fixed-fixture runner. SOURCE ONLY until separately admitted.

No numerical adjudication, discovery, model conversion, source edits or retry.
The admission is a local ROOT trust boundary, not cryptographic authentication.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time

ROOT = Path('E:/the_harness')
PHASE = ROOT / 'records/root_continuation_20261004'
DLL_NAMES = {'ggml-base.dll', 'ggml-cpu.dll', 'ggml-rpc.dll', 'ggml-vulkan.dll', 'ggml.dll'}
FLAGS = {name: '1' for name in ('GGML_VK_DISABLE_F16', 'GGML_VK_DISABLE_FUSION',
                              'GGML_VK_DISABLE_COOPMAT', 'GGML_VK_DISABLE_COOPMAT2')}
PINS = {
    'operator': ('ad449a153447080836e25a5ca264ebd4b3afa5b14dbb239b11a5bad5be117b5b',
                 'f89510925babac35ef98154b14a27040cf81db35d11bebc888c9b0a97da1ca59', 30),
    'model': ('d9034fe8011c6792110c066e9c4e3d92931960d4e48eec64aeca2c1534bf44c4',
              '2aff3925329a8ca6ca4834f665a8ed07acb1d3e341f73908dfecb3989057c371', 60),
}
MODEL_PIN = ('bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80', 2390150816)
LIMIT = 2 * 1024 * 1024


def unique_object(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate JSON key')
        result[k] = v
    return result


def load_json(text):
    return json.loads(text, object_pairs_hook=unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def confined(value, base=ROOT, exists=True):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('invalid path')
    p = Path(value)
    if not p.is_absolute():
        raise ValueError('absolute path required')
    p = p.resolve(strict=exists)
    p.relative_to(base.resolve())
    return p


def check_pin(pin, system_loader=False):
    if not isinstance(pin, dict) or set(pin) != {'path', 'sha256', 'bytes'}:
        raise ValueError('invalid file pin')
    if type(pin['bytes']) is not int or pin['bytes'] <= 0:
        raise ValueError('invalid file size')
    if not isinstance(pin['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', pin['sha256']):
        raise ValueError('invalid SHA256')
    if system_loader:
        p = Path(pin['path']).resolve(strict=True)
        if str(p).casefold() != 'c:\\windows\\system32\\vulkan-1.dll':
            raise ValueError('system loader path mismatch')
    else:
        p = confined(pin['path'])
    if not p.is_file() or p.stat().st_size != pin['bytes'] or digest(p) != pin['sha256']:
        raise ValueError('file pin mismatch: ' + p.name)
    return p


def relevant_environment():
    names = {'VULKAN_SDK', 'VK_DRIVER_FILES', 'VK_ICD_FILENAMES', 'VK_LAYER_PATH',
             'VK_INSTANCE_LAYERS', 'VK_ADD_DRIVER_FILES', 'GGML_BACKEND_PATH', 'GGML_BACKEND_DL_PATH'}
    names.update(k for k in os.environ if k.startswith('GGML_VK_'))
    names.update(FLAGS)
    return {k: os.environ.get(k) for k in sorted(names)}


def atomic_json(path, value):
    data = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(data) > 512 * 1024:
        raise ValueError('receipt exceeds bounded budget')
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


class Capture:
    def __init__(self, pipe):
        self.pipe = pipe
        self.data = bytearray()
        self.observed = 0
        self.overflow = False
        self.error = None
        self.started = False
        self.thread = threading.Thread(target=self.read, daemon=True)

    def read(self):
        try:
            while True:
                block = self.pipe.read(4096)
                if not block:
                    break
                self.observed += len(block)
                room = LIMIT - len(self.data)
                self.data.extend(block[:max(0, room)])
                if len(block) > room:
                    self.overflow = True
        except Exception as exc:
            self.error = type(exc).__name__
        finally:
            try:
                self.pipe.close()
            except Exception as exc:
                self.error = self.error or type(exc).__name__


class Modules:
    def __init__(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.enum = kernel.K32EnumProcessModules
        self.enum.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                              wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        self.enum.restype = wintypes.BOOL
        self.name = kernel.K32GetModuleFileNameExW
        self.name.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
        self.name.restype = wintypes.DWORD

    def paths(self, owned_process):
        entries = (wintypes.HMODULE * 2048)()
        needed = wintypes.DWORD()
        handle = wintypes.HANDLE(int(owned_process._handle))
        if not self.enum(handle, entries, ctypes.sizeof(entries), ctypes.byref(needed)):
            raise ctypes.WinError(ctypes.get_last_error())
        if needed.value > ctypes.sizeof(entries):
            raise ValueError('module array overflow')
        result = []
        for entry in entries[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
            buf = ctypes.create_unicode_buffer(32768)
            n = self.name(handle, entry, buf, len(buf))
            if n == 0:
                raise ctypes.WinError(ctypes.get_last_error())
            if n >= len(buf):
                raise ValueError('module filename unavailable/truncated')
            result.append(Path(buf.value).resolve(strict=True))
        return result


def run(admission_path, admission_sha256):
    admission_path = confined(str(admission_path), PHASE)
    if not isinstance(admission_sha256, str) or not re.fullmatch('[0-9a-f]{64}', admission_sha256):
        raise ValueError('external ROOT admission SHA256 required')
    if digest(admission_path) != admission_sha256:
        raise ValueError('external admission pin mismatch before JSON read')
    if admission_path.stat().st_size > 128 * 1024:
        raise ValueError('admission too large')
    a = load_json(admission_path.read_text(encoding='utf-8-sig'))
    required = {'schema', 'adjudicator', 'launch', 'fixture', 'helper', 'python', 'source',
                'executable', 'dlls', 'supporting_dlls', 'system_loader', 'model', 'runtime_dir', 'arguments',
                'timeout_seconds', 'stream_limit_bytes', 'child_flags', 'parent_runtime_environment'}
    if not isinstance(a, dict) or set(a) != required or type(a['schema']) is not int or a['schema'] != 1:
        raise ValueError('exact admission schema required')
    if a['adjudicator'] != 'ROOT' or a['launch'] is not True or a['fixture'] not in PINS:
        raise ValueError('ROOT launch admission absent')
    exe_hash, source_hash, timeout = PINS[a['fixture']]
    if type(a['timeout_seconds']) is not int or a['timeout_seconds'] != timeout:
        raise ValueError('fixed timeout required')
    if type(a['stream_limit_bytes']) is not int or a['stream_limit_bytes'] != LIMIT:
        raise ValueError('fixed stream budget required')
    if a['child_flags'] != FLAGS or a['parent_runtime_environment'] != relevant_environment():
        raise ValueError('runtime environment binding mismatch')
    helper = check_pin(a['helper'])
    if helper != Path(__file__).resolve():
        raise ValueError('helper pin not this file')
    # Python lives outside the harness; admission must pin the actual existing executable.
    py = a['python']
    if not isinstance(py, dict) or set(py) != {'path', 'sha256', 'bytes'}:
        raise ValueError('Python pin schema')
    pyp = Path(py['path']).resolve(strict=True)
    if pyp != Path(sys.executable).resolve() or type(py['bytes']) is not int or pyp.stat().st_size != py['bytes'] or digest(pyp) != py['sha256']:
        raise ValueError('Python executable mismatch')
    source = check_pin(a['source']); exe = check_pin(a['executable'])
    if a['source']['sha256'] != source_hash or a['executable']['sha256'] != exe_hash:
        raise ValueError('fixture immutable source/executable mismatch')
    if not isinstance(a['dlls'], list) or len(a['dlls']) != 5:
        raise ValueError('exact five DLL pins required')
    dlls = [check_pin(p) for p in a['dlls']]
    if {p.name for p in dlls} != DLL_NAMES or len({str(p).casefold() for p in dlls}) != 5:
        raise ValueError('DLL name/identity mismatch')
    if len({p.parent for p in dlls}) != 1:
        raise ValueError('five ggml DLLs must share one ROOT-admitted fresh build folder')
    supporting = a['supporting_dlls']
    if not isinstance(supporting, list):
        raise ValueError('supporting DLL pin list required')
    if a['fixture'] == 'operator':
        if supporting:
            raise ValueError('operator supporting DLL list must be empty')
    elif len(supporting) != 1:
        raise ValueError('model requires exact one pinned llama.dll')
    supporting_paths = [check_pin(p) for p in supporting]
    if a['fixture'] == 'model' and supporting_paths[0].name != 'llama.dll':
        raise ValueError('model supporting DLL must be llama.dll')
    loader = check_pin(a['system_loader'], True)
    if a['fixture'] == 'model':
        model = check_pin(a['model'])
        if (a['model']['sha256'], a['model']['bytes']) != MODEL_PIN:
            raise ValueError('derived F32 model required')
    elif a['model'] is not None:
        raise ValueError('operator must not bind a model')
    args = a['arguments']
    if not isinstance(args, list) or not args or len(args) > 32 or any(type(x) is not str or not x or '\x00' in x or len(x) > 4096 for x in args):
        raise ValueError('bounded exact argv required')
    runtime = confined(a['runtime_dir'], PHASE, False)
    if runtime.exists():
        raise FileExistsError('fresh runtime folder mandatory')
    runtime.mkdir(parents=False)
    parent_before = relevant_environment()
    expected_modules = {}
    admission_pin = {'path': str(admission_path), 'bytes': admission_path.stat().st_size,
                     'sha256': admission_sha256}
    pins = [a['helper'], a['python'], admission_pin, a['source'], a['executable'],
            *a['dlls'], *supporting, a['system_loader']]
    if a['model'] is not None:
        pins.append(a['model'])
    receipt = {'schema': 1, 'admission': str(admission_path), 'admission_sha256': admission_sha256,
               'input_pins_before': pins,
               'fixture': a['fixture'], 'numerical_adjudication': 'NOT_PERFORMED',
               'status': 'UNKNOWN', 'command': [], 'module_observations': [], 'errors': []}
    proc = None
    captures = []
    copies = []
    seen = set()
    start = None
    try:
        for origin in [exe, *dlls, *supporting_paths]:
            target = runtime / origin.name
            shutil.copyfile(origin, target)
            original_hash = digest(origin)
            if digest(target) != original_hash:
                raise ValueError('copy hash mismatch')
            copies.append({'source': str(origin), 'copy': str(target), 'sha256': original_hash})
            if origin.name in DLL_NAMES or origin.name == 'llama.dll':
                expected_modules[origin.name.casefold()] = (target.resolve(), original_hash)
        expected_modules['vulkan-1.dll'] = (loader, a['system_loader']['sha256'])
        env = os.environ.copy(); env.update(FLAGS)
        observer = Modules()
        command = [str(runtime / exe.name), *args]
        receipt['command'] = command
        start = time.monotonic()
        proc = subprocess.Popen(command, cwd=runtime, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        receipt['pid'] = proc.pid
        for pipe in (proc.stdout, proc.stderr):
            capture = Capture(pipe)
            captures.append(capture)
            capture.thread.start()
            capture.started = True
        deadline = start + timeout
        while proc.poll() is None:
            if time.monotonic() >= deadline or any(c.overflow or c.error for c in captures):
                receipt['errors'].append('deadline_or_stream_failure')
                proc.kill()  # retained Popen owned handle; never reopen a PID
                break
            try:
                paths = observer.paths(proc)
                for path in paths:
                    key = path.name.casefold()
                    if ((key.startswith('ggml') and key.endswith('.dll')) or key == 'llama.dll') and key not in expected_modules:
                        raise ValueError('unexpected ggml module')
                    if key not in expected_modules or str(path).casefold() in seen:
                        continue
                    wanted, h = expected_modules[key]
                    actual = digest(path)
                    entry = {'path': str(path), 'sha256': actual, 'elapsed_seconds': time.monotonic()-start}
                    receipt['module_observations'].append(entry)
                    if path != wanted or actual != h:
                        raise ValueError('actual module binding mismatch')
                    seen.add(str(path).casefold())
            except OSError:
                # Startup/exit module races may yield no observation; never invent one.
                pass
            time.sleep(0.005)
        proc.wait(timeout=5)
        receipt['exit_code'] = proc.returncode
    except Exception as exc:
        receipt['errors'].append(type(exc).__name__ + ': ' + str(exc)[:512])
    finally:
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=5)
                receipt['owned_process_reaped'] = True
                receipt['pid_absent_through_owned_handle'] = proc.poll() is not None
            except Exception as exc:
                receipt['owned_process_reaped'] = False
                receipt['errors'].append('owned_reap_' + type(exc).__name__)
        drain_deadline = time.monotonic() + 5
        for capture in captures:
            try:
                if capture.started:
                    capture.thread.join(max(0, drain_deadline-time.monotonic()))
                else:
                    capture.pipe.close()
            except Exception as exc:
                receipt['errors'].append('reader_join_' + type(exc).__name__)
        if proc is not None and receipt.get('owned_process_reaped'):
            try:
                proc._handle.Close()
                receipt['owned_process_handle_closed'] = True
            except Exception as exc:
                receipt['owned_process_handle_closed'] = False
                receipt['errors'].append('owned_handle_close_' + type(exc).__name__)
        stream_metadata = {}
        for label, capture in zip(('stdout', 'stderr'), captures):
            live = capture.thread.is_alive()
            if live or capture.error or capture.overflow:
                receipt['errors'].append(label + '_drain_unknown_or_failed')
            data = bytes(capture.data)
            (runtime / (label + '.raw.log')).write_bytes(data)
            stream_metadata[label] = {'captured_bytes': len(data), 'observed_bytes': capture.observed,
                                      'sha256': hashlib.sha256(data).hexdigest(), 'reader_alive': live,
                                      'error': capture.error, 'truncated': capture.overflow}
        receipt['streams'] = stream_metadata
        receipt['copies'] = copies
        receipt['elapsed_seconds'] = None if start is None else time.monotonic()-start
        receipt['pin_checks_after'] = []
        for pin in pins:
            try:
                path = Path(pin['path'])
                good = path.stat().st_size == pin['bytes'] and digest(path) == pin['sha256']
                receipt['pin_checks_after'].append({'path': str(path), 'unchanged': good})
                if not good:
                    receipt['errors'].append('input_pin_changed')
            except Exception as exc:
                receipt['errors'].append('after_pin_' + type(exc).__name__)
        for copy in copies:
            try:
                if digest(Path(copy['copy'])) != copy['sha256']:
                    receipt['errors'].append('copy_pin_changed')
            except Exception as exc:
                receipt['errors'].append('copy_pin_' + type(exc).__name__)
        receipt['parent_runtime_environment_unchanged'] = relevant_environment() == parent_before
        if not receipt['parent_runtime_environment_unchanged']:
            receipt['errors'].append('parent_environment_changed')
        observed = {Path(x['path']).name.casefold() for x in receipt['module_observations']}
        receipt['all_five_local_ggml_modules_observed'] = DLL_NAMES <= observed
        if not DLL_NAMES <= observed:
            receipt['errors'].append('actual_five_module_binding_not_observed')
        receipt['supporting_modules_observed'] = {p.name for p in supporting_paths} <= observed
        if not receipt['supporting_modules_observed']:
            receipt['errors'].append('actual_supporting_module_binding_not_observed')
        if captures and not any(c.thread.is_alive() for c in captures):
            try:
                output = load_json(bytes(captures[0].data).decode('utf-8'))
                if not isinstance(output, dict):
                    raise ValueError('JSON object required')
                receipt['full_stdout_json'] = True
            except Exception as exc:
                receipt['full_stdout_json'] = False
                receipt['errors'].append('stdout_json_' + type(exc).__name__)
        receipt['status'] = 'EXECUTION_RECORDED_NO_NUMERICAL_ADJUDICATION' if not receipt['errors'] else 'INTEGRITY_REFUSED_OR_UNKNOWN'
        atomic_json(runtime / 'run_receipt.json', receipt)
    return 0 if not receipt['errors'] else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--admission', required=True, type=Path)
    parser.add_argument('--admission-sha256', required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.admission, args.admission_sha256))
