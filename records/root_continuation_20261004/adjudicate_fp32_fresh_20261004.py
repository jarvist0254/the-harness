"""ROOT read-only receipt validation plus exclusive new report; no native execution."""
import hashlib
import json
import math
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r'E:\the_harness\records\root_continuation_20261004')
BUILD = Path(r'E:\the_harness\records\build_vulkan_fp32_staging_20261004T155932Z\evidence\attempt5_compiler_root_cleanup')
PAIRS = {
    ('Vulkan0', 'Vulkan1'): '3257aba03bc8b11a99c84399f8dc7c8e15b99cdeff8bf13dad3113a803fd3187',
    ('Vulkan1', 'Vulkan0'): 'a5d6000a250e782f668df0770fd8a271de51b16c5c6cbfddba9091db66dd0d25',
}
RUNS = [
    ('operator_candidate_nv2_20261004T1843Z', 'operator', False),
    ('operator_candidate_amd_20261004T1843Z', 'operator', False),
    ('operator_candidate_nv_corrupt_20261004T1845Z', 'operator', True),
    ('operator_candidate_amd_corrupt_20261004T1845Z', 'operator', True),
    ('model_candidate_mixed_20261004T1845Z', 'model', False),
    ('model_candidate_reverse_20261004T1847Z', 'model', False),
    ('model_candidate_corrupt_fixed_20261004T1902Z', 'model', True),
    ('model_candidate_reverse_corrupt_fixed_20261004T1905Z', 'model', True),
]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def main():
    controller = read(BUILD / 'controller_result.json')
    assert controller['all_completed'] is True and controller['failure'] is None and controller['integrity_failure'] is None
    assert len(controller['stages']) == 2
    for stage in controller['stages']:
        assert stage['status'] == 'COMPILER_ROOT_EXITED_CLEANUP_REQUIRED' and stage['drain_proof'] == 'CLEANUP' and stage['job_active_count'] == 0
        assert len(stage['workers']) == 1 and stage['workers'][0]['exit_code'] == 0 and stage['workers'][0]['assigned'] is True and stage['workers'][0]['resumed'] is True
    manifest = read(BUILD / 'fresh_dll_manifest.json')
    expected = {Path(p['path']).name: p['sha256'] for p in manifest}
    assert set(expected) == {'ggml.dll', 'ggml-base.dll', 'ggml-cpu.dll', 'ggml-rpc.dll', 'ggml-vulkan.dll'}
    for p in manifest:
        assert Path(p['path']).stat().st_size == p['bytes'] and digest(Path(p['path'])) == p['sha256']
    results = []
    for name, fixture, control in RUNS:
        folder = BASE / name
        receipt_path, stdout_path = folder / 'run_receipt.json', folder / 'stdout.raw.log'
        r, o = read(receipt_path), read(stdout_path)
        assert r['status'] == 'EXECUTION_RECORDED_NO_NUMERICAL_ADJUDICATION' and r['errors'] == [] and r['fixture'] == fixture
        for key in ('owned_process_reaped', 'pid_absent_through_owned_handle', 'owned_process_handle_closed', 'parent_runtime_environment_unchanged', 'all_five_local_ggml_modules_observed', 'supporting_modules_observed', 'full_stdout_json'):
            assert r[key] is True, (name, key)
        assert len(r['pin_checks_after']) == len(r['input_pins_before']) and all(p['unchanged'] is True for p in r['pin_checks_after'])
        for label in ('stdout', 'stderr'):
            raw, metadata = folder / (label + '.raw.log'), r['streams'][label]
            assert digest(raw) == metadata['sha256'] and raw.stat().st_size == metadata['captured_bytes'] == metadata['observed_bytes']
            assert metadata['reader_alive'] is False and metadata['truncated'] is False and metadata['error'] is None
        admission_path = Path(r['admission'])
        assert digest(admission_path) == r['admission_sha256']
        admission = read(admission_path)
        observed = {Path(p['path']).name: (Path(p['path']), p['sha256']) for p in r['module_observations']}
        assert {Path(p['path']).name: p['sha256'] for p in admission['dlls']} == expected
        for lib, pin in expected.items():
            assert observed[lib] == (folder / lib, pin) and digest(folder / lib) == pin
        assert r['exit_code'] == (1 if control else 0)
        result = dict(run=name, scope=fixture, control=control, receipt=str(receipt_path), receipt_sha256=digest(receipt_path), stdout=str(stdout_path), stdout_sha256=digest(stdout_path), admission_sha256=r['admission_sha256'], child_exit_code=r['exit_code'])
        if fixture == 'operator':
            assert len(o['cases']) == 6 and math.isclose(o['atol'], 2e-5, rel_tol=0, abs_tol=1e-20) and math.isclose(o['rtol'], 2e-6, rel_tol=0, abs_tol=1e-20)
            assert all(x['outputs'] == x['finite_count'] == 2048 and x['shape_checked'] is True and x['buffer_owner_checked'] is True and x['graph_status'] == 'SUCCESS' for x in o['cases'])
            fails = sum(x['fail_count'] for x in o['cases'])
            assert fails == (1 if control else 0) and sum(x['corruption_injected'] for x in o['cases']) == (1 if control else 0)
            assert o['status'] == ('OPERATOR_PARITY_FAIL' if control else 'OPERATOR_PARITY_PASS')
            result.update(comparisons=12288, fail_count=fails, device=o['device'], description=o['description'], verdict='COMPARATOR_READBACK_CONTROL_DETECTED' if control else 'OPERATOR_PARITY_PASS')
        else:
            pair = tuple(o['devices'])
            assert pair in PAIRS and o['workload_sha256'] == PAIRS[pair]
            assert o['n_vocab'] == 151936 and o['n_layer'] == 28 and o['tokens'] == list(range(16)) and o['kv_actual_k'] == o['kv_actual_v'] == 'f32'
            assert o['n_ctx_actual'] == 256 and o['n_batch_actual'] == o['n_ubatch_actual'] == 32
            assert o['sha256'] == 'bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80' and o['file_size'] == 2390150816
            assert o['all_finite_cpu'] is True and o['all_finite_gpu'] is True and o['fail_count'] == (1 if control else 0) and o['inject_corruption'] is control and o['exit_code'] == r['exit_code']
            assert o['status'] == ('NUMERIC_PARITY_FAIL' if control else 'NUMERIC_PARITY_PASS') and o['error'] == ('inject_corruption' if control else None)
            assert all(type(o[k]) in (int, float) and math.isfinite(o[k]) for k in ('max_abs', 'rmse'))
            assert observed['llama.dll'][0] == folder / 'llama.dll'
            assert ('--inject-logit-corruption' in admission['arguments']) is control
            result.update(comparisons=151936, fail_count=o['fail_count'], max_abs=o['max_abs'], rmse=o['rmse'], devices=o['devices'], workload_sha256=o['workload_sha256'], verdict='COMPARATOR_LOGIT_CONTROL_DETECTED' if control else 'FIXED_DERIVED_F32_MODEL_PARITY_PASS')
        results.append(result)
    report = dict(schema=1, adjudicator='ROOT', utc=datetime.now(timezone.utc).isoformat(), verdict='SCOPED_FP32_SOFTWARE_CRITICAL_PATH_PASS', scope='Exact attempt5 ggml build and unchanged fixed fixtures; NVIDIA5070Ti +AMD integrated only', adjudication_script_sha256=digest(Path(__file__)), build_receipt=str(BUILD / 'controller_result.json'), build_receipt_sha256=digest(BUILD / 'controller_result.json'), fresh_dll_manifest=manifest, results=results, limits=['NOT Intel execution or Intel/Intel or Intel/NVIDIA direct P2P', 'NOT four cards, 8GB capacity, physical residency or pooled VRAM', 'NOT original Q8 model qualification or arbitrary-model accuracy', 'Controls mutate GPU readback/logits on host; NOT GPU-internal or P2P-boundary fault injection', 'No whole-tree natural completion certificate', 'Prior failures and uncertain receipts remain unchanged'], excluded_runs=['operator_candidate_nv_20261004T1840Z: uncertain original collector', 'model_candidate_corrupt_20261004T1849Z: bad_arg before model execution'])
    destination = BASE / 'FP32_FRESH_NUMERICAL_ACCEPTANCE_20261004T1910Z.json'
    with destination.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps(dict(report=str(destination), sha256=digest(destination), verdict=report['verdict'], accepted_scoped_runs=len(results), expected_corruption_controls=4, full_goal='INCOMPLETE')))

if __name__ == '__main__':
    main()
