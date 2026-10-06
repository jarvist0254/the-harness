"""Fixed command, retained child handle, concurrent bounded capture, no children."""
import hashlib
import json
import pathlib
import subprocess
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent
PYTHON = pathlib.Path(r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe')
assert hashlib.sha256(PYTHON.read_bytes()).hexdigest() == '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260'
SOURCE = pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\qwen_transfer_four_prep_20261004T202539Z\qwen_directed_receipt_repair\source.SCHEMA_REFUSED_UNTRUSTED_REVIEW_ONLY.txt')
FILES = [SOURCE, ROOT / 'test_independent_directed_v2.py', pathlib.Path(__file__), PYTHON]
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
assert before[str(SOURCE)] == 'fc73cb96c60a4df88815d670f3d6682ff71c3a1cbcaf9dc06942bc780768dc29'
state = {'bytes': {}, 'overflow': [], 'errors': []}
start = time.monotonic()
p = subprocess.Popen([str(PYTHON), '-B', str(ROOT / 'test_independent_directed_v2.py')], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
threads = []
def capture(stream, name):
    count = 0
    try:
        with (ROOT / name).open('xb') as f:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                f.write(chunk[:max(0, 262144 - count)])
                count += len(chunk)
                if count > 262144:
                    state['overflow'].append(name)
    except Exception as exc:
        state['errors'].append(type(exc).__name__)
    finally:
        state['bytes'][name] = count
        stream.close()
for stream, name in ((p.stdout, 'stdout.raw.json'), (p.stderr, 'stderr.raw.log')):
    t = threading.Thread(target=capture, args=(stream, name), daemon=True)
    t.start()
    threads.append(t)
timed_out = False
while p.poll() is None:
    if time.monotonic() - start >= 10 or state['overflow']:
        timed_out = True
        p.kill()
        break
    time.sleep(.02)
p.wait(timeout=3)
for t in threads:
    t.join(timeout=2)
after = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in FILES}
receipt = {'scope': 'ROOT_ADMITTED_SYNTHETIC_DIRECTED_RECEIPT_ONLY', 'owned_pid': p.pid, 'exit_code': p.returncode, 'reaped': p.poll() is not None, 'timeout': timed_out, 'seconds': time.monotonic() - start, 'capture': state, 'readers_joined': not any(t.is_alive() for t in threads), 'pins_before': before, 'pins_after': after, 'pins_unchanged': before == after, 'gpu_execution': False}
(ROOT / 'execution_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print(json.dumps(receipt, indent=2))
raise SystemExit(0 if p.returncode == 0 and not timed_out and not state['overflow'] and not state['errors'] and receipt['readers_joined'] and before == after else 1)
