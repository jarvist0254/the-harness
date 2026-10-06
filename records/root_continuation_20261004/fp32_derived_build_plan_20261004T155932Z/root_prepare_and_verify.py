"""ROOT admission of three bounded source edits and filesystem-only preparation."""
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PY = Path(r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe')
SOURCE = Path(r'E:\the_harness\records\build_vulkan_real\toolchain\llama_clean_source\ggml\src\ggml-vulkan\ggml-vulkan.cpp')
PATCH = Path(r'E:\the_harness\records\factory_runs\20261004\fp32_staging_repair_20261004T153127Z\grok_fp32_patch\patch.pending_root_qa.json')
PINS = {
    PY: '3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260',
    SOURCE: '86c7d9251ecddff54f6a53956cfd22c94ef9090064789b7a362d56cb1b3cadef',
    PATCH: '4d90acfb1f9f004e3a0dced9b2d02eb7fb8f731bdfa64e1b840f9d0db09cb203',
    HERE / 'ggml-vulkan.grok_candidate_PENDING_ROOT.cpp': '4bf60b8a6c2a4b2b9a6d8c2e6ed6e09904f9f047abfcddcc0917626f1ca015cd',
    HERE / 'prepare_derived.py': '52edeb8ba8d0338e870ca3521364fc9b3c7da306ca1d4ec3c97ad3c57b72710a',
    HERE / 'CONTRACT.json': '048ccef119d51d95ae094d775175f4c9352ff8c3cdc5ee53a33ded4f6650c951',
    HERE / 'toolchain_pins_preparation.json': 'a3f9109ccaa063ab936f386d84e9f1fba03f1d3d6d0d76869098eba715b3c9d9',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if Path(sys.executable).resolve() != PY or sys.flags.optimize:
        raise ValueError('expected pinned interpreter without optimized assertions')
    before = {str(p): sha(p) for p in PINS}
    if any(before[str(p)] != h for p, h in PINS.items()):
        raise ValueError('input pin changed')
    old = SOURCE.read_bytes()
    lines = old.splitlines(keepends=True)
    prefix, body, suffix = b''.join(lines[:6269]), b''.join(lines[6269:6552]), b''.join(lines[6552:])
    patch = json.loads(PATCH.read_text())
    if set(patch) != {'changes', 'rationale', 'safety_checks'} or len(patch['changes']) != 3:
        raise ValueError('patch schema')
    for change in patch['changes']:
        if set(change) != {'search', 'replace'}:
            raise ValueError('replacement schema')
        search = change['search'].replace('\n', '\r\n').encode()
        replacement = change['replace'].replace('\n', '\r\n').encode()
        if body.count(search) != 1:
            raise ValueError('expected exactly one function-local search')
        body = body.replace(search, replacement, 1)
    candidate = prefix + body + suffix
    target = HERE / 'ggml-vulkan.grok_candidate_PENDING_ROOT.cpp'
    if candidate != target.read_bytes() or sha(target) != PINS[target]:
        raise ValueError('independent reconstruction mismatch')
    newlines = candidate.splitlines(keepends=True)
    regions = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, lines, newlines, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        regions.append({'tag': tag, 'old_first_line': i + 1, 'old_end_exclusive_line': j + 1,
                        'new_first_line': k + 1, 'new_end_exclusive_line': l + 1,
                        'old_bytes_sha256': hashlib.sha256(b''.join(lines[i:j])).hexdigest(),
                        'new_bytes_sha256': hashlib.sha256(b''.join(newlines[k:l])).hexdigest()})
    admission = json.loads((HERE / 'candidate_admission_PENDING_ROOT_revision2.json').read_text())
    if admission['exact_regions'] != regions or len(regions) != 2:
        raise ValueError('merged diff region mismatch')
    admission['authorization'] = 'ROOT_BUILD_PREPARATION_ADMITTED'
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt_dir = HERE / ('root_preparation_' + stamp)
    receipt_dir.mkdir()
    record = receipt_dir / 'admission.json'
    record.write_text(json.dumps(admission, indent=2))
    cmd = [str(PY), '-B', str(HERE / 'prepare_derived.py'), '--admission', str(record), '--admission-sha256', sha(record)]
    start = time.monotonic()
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=str(HERE), shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
    timed_out = False
    try:
        out, err = proc.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        out, err = proc.communicate(timeout=8)
    (receipt_dir / 'stdout.log').write_bytes(out[:1048576])
    (receipt_dir / 'stderr.log').write_bytes(err[:1048576])
    after = {str(p): sha(p) for p in PINS}
    ok = not timed_out and proc.returncode == 0 and before == after and len(out) <= 1048576 and len(err) <= 1048576
    result = {'scope': 'FILESYSTEM_PREPARATION_ONLY_NO_COMPILER_GPU_OR_PROVIDER', 'status': 'PASS' if ok else 'FAIL',
              'pid': proc.pid, 'reaped': proc.poll() is not None, 'exit_code': proc.returncode, 'timeout': timed_out,
              'elapsed_seconds': time.monotonic() - start, 'inputs_before': before, 'inputs_after': after,
              'three_replacements_independently_reconstructed': True, 'two_merged_diff_regions': regions,
              'command': cmd, 'admission_sha256': sha(record)}
    (receipt_dir / 'receipt.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({'status': result['status'], 'receipt': str(receipt_dir / 'receipt.json'), 'elapsed_seconds': result['elapsed_seconds']}))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
