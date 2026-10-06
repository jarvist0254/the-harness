"""SOURCE ONLY: bounded CPU fixture. Native execution needs separate ROOT admission."""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent

def emit(role, mode, **fields):
    row = {'fixture': 'COMPILER_COMPLETION_CPU_V1', 'role': role, 'mode': mode, 'pid': os.getpid()}
    row.update(fields)
    for stream, label in ((sys.stdout, 'stdout'), (sys.stderr, 'stderr')):
        print(json.dumps(dict(row, stream=label), separators=(',', ':')), file=stream, flush=True)

def ready(folder, role, mode):
    path = folder/(role+'_ready.json')
    if path.exists():
        raise ValueError('fresh readiness marker required')
    temporary = path.with_suffix('.part')
    with temporary.open('x', encoding='utf-8') as f:
        json.dump({'role':role,'mode':mode,'pid':os.getpid()}, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=('success', 'resident_success', 'resident_failure', 'timeout', 'cancel', 'resident_child'))
    parser.add_argument('--case-dir', required=True)
    args = parser.parse_args()
    folder = pathlib.Path(args.case_dir).resolve(strict=True)
    runs = (HERE/'native_runs').resolve()
    if runs not in folder.parents or not folder.is_dir():
        raise ValueError('case directory must be a fresh caller-owned native_runs child')
    if os.name != 'nt':
        raise RuntimeError('Windows native fixture requires a separate admitted Windows run')
    if args.mode == 'resident_child':
        # These explicitly inherited live root pipes stay open after the root exits.
        emit('child', args.mode, hold_seconds=60)
        ready(folder, 'child', args.mode)
        time.sleep(60)
        return 0
    if args.mode in ('resident_success', 'resident_failure'):
        child = subprocess.Popen([sys.executable, '-B', str(pathlib.Path(__file__).resolve()), '--mode', 'resident_child', '--case-dir', str(folder)], stdin=subprocess.DEVNULL, stdout=sys.stdout, stderr=sys.stderr, close_fds=True, creationflags=subprocess.CREATE_NO_WINDOW)
        # No breakaway flag. Windows automatically places this child in the owned root Job.
        # The retained Popen handle belongs to this root; no reopening or PID-based control.
        end = time.monotonic()+2
        marker = folder/'child_ready.json'
        while not marker.exists():
            if child.poll() is not None or time.monotonic() >= end:
                raise RuntimeError('owned child did not establish inherited-pipe readiness')
            time.sleep(.01)
        row = json.loads(marker.read_text())
        if row != {'role':'child','mode':'resident_child','pid':child.pid}:
            raise RuntimeError('owned child readiness mismatch')
        emit('root', args.mode, owned_child_pid=child.pid, requested_exit=3 if args.mode=='resident_failure' else 0)
        ready(folder, 'root', args.mode)
        # Deliberately do not wait/terminate: the admitted supervisor owns Job cleanup.
        return 3 if args.mode=='resident_failure' else 0
    emit('root', args.mode, requested_exit=0 if args.mode=='success' else None)
    ready(folder, 'root', args.mode)
    if args.mode in ('timeout','cancel'):
        time.sleep(60)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
