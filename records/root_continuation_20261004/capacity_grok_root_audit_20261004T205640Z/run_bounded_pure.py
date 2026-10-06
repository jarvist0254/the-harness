"""Owned, bounded derivative of the previously qualified pure QA controller."""
import hashlib, json, pathlib, subprocess, sys, threading, time
R = pathlib.Path(__file__).resolve().parent
C = pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_capacity_repair_prep_20261004T203621Z\grok_capacity_high')
PY = pathlib.Path(r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
files = [C/'source.grok_untrusted.py', C/'tests_source.grok_untrusted.txt', R/'test_independent_capacity.py', pathlib.Path(__file__), PY]
before = {str(path): sha(path) for path in files}
assert before[str(files[0])] == '4a27892638447b0913aa2faffa8b4c6c1615011ddc8fde54550fceb9f1190211'
assert before[str(files[1])] == '1a885582f610a0144479a90be787d049f8afedadd86da8d7810c2b85c428b114'
assert before[str(PY)] == '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
start = time.monotonic()
p = subprocess.Popen([str(PY), '-B', str(R/'test_independent_capacity.py')], cwd=R, stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
state = {'bytes': {}, 'overflow': [], 'errors': []}; threads = []
def capture(pipe, name):
    total = 0
    try:
        with (R/name).open('xb') as output:
            while True:
                data = pipe.read(8192)
                if not data: break
                keep = max(0, min(len(data), 2*1024*1024-total)); output.write(data[:keep]); total += len(data)
                if total > 2*1024*1024: state['overflow'].append(name); break
    except Exception as error: state['errors'].append(repr(error))
    finally: pipe.close(); state['bytes'][name] = total
for stream, name in [(p.stdout, 'stdout.raw.json'), (p.stderr, 'stderr.raw.log')]:
    thread = threading.Thread(target=capture, args=(stream, name), daemon=True); thread.start(); threads.append(thread)
timeout = False
try:
    while p.poll() is None:
        if time.monotonic()-start >= 30 or state['overflow']:
            timeout = True; p.kill(); break
        time.sleep(.01)
    p.wait(timeout=3)
finally:
    if p.poll() is None: p.kill(); p.wait(timeout=3)
for thread in threads: thread.join(timeout=2)
after = {str(path): sha(path) for path in files}
receipt = {'scope': 'ROOT_ADMITTED_EXACT_SOURCE_INDEPENDENT_PURE_QA', 'pid': p.pid, 'exit_code': p.returncode,
           'reaped': p.poll() is not None, 'owned_process_handle_signaled': p.poll() is not None,
           'pid_absent_at_owned_handle_observation': p.poll() is not None,
           'seconds': time.monotonic()-start, 'timeout_seconds': 30, 'timeout': timeout,
           'stream_cap_bytes': 2*1024*1024, 'capture': state, 'readers_joined': not any(t.is_alive() for t in threads),
           'pins_before': before, 'pins_after': after, 'hashes_unchanged': before == after,
           'provider_tests_executed': False, 'native_gpu_provider_calls': False,
           'process_identity_scope': 'Retained owned process handle only; no arbitrary PID control or descendant fixture.'}
with (R/'execution_receipt.json').open('x', encoding='utf-8') as output: json.dump(receipt, output, indent=2)
print(json.dumps(receipt, indent=2))
sys.exit(0 if not timeout and before == after and receipt['readers_joined'] and not state['errors'] else 2)
