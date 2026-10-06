"""Create one fixed fixture admission after the pinned contained build succeeds.

No fixture import, compiler launch, GPU execution or numerical adjudication.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path('E:/the_harness')
PHASE = ROOT / 'records/root_continuation_20261004'
BUILD = ROOT / 'records/build_vulkan_fp32_staging_20261004T155932Z'
EVIDENCE = BUILD / 'evidence/attempt3_skip_telemetry'
FLAGS = dict.fromkeys(('GGML_VK_DISABLE_F16', 'GGML_VK_DISABLE_FUSION',
                       'GGML_VK_DISABLE_COOPMAT', 'GGML_VK_DISABLE_COOPMAT2'), '1')
HELPER_SHA = 'dc83fadf1c59945e6b1a51f1181f522702680d9d0a564679f537392abeee4307'
CONTROLLER_SHA = '7f0af5fc2d61a1c3a52a7b4d5ef1383f7943a63bd9920621f68519381c58d52d'
ADMISSION_SHA = 'a8eec72a0e0534615c5538a11417a32b361ed88272601fd54d65bccf031fcd79'


def pin(path):
    p = Path(path).resolve(strict=True)
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': h.hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', choices=('operator', 'model'))
    parser.add_argument('devices', choices=('Vulkan0', 'Vulkan1', 'Vulkan0,Vulkan1', 'Vulkan1,Vulkan0'))
    parser.add_argument('run_name')
    parser.add_argument('--negative', action='store_true')
    args = parser.parse_args()
    if not args.run_name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_' for c in args.run_name):
        raise ValueError('fixed safe run name required')
    result = json.loads((EVIDENCE / 'controller_result.json').read_text())
    if (result['all_completed'] is not True or result['failure'] is not None
            or result['integrity_failure'] is not None
            or result['controller_sha256'] != CONTROLLER_SHA
            or result['root_admission_sha256'] != ADMISSION_SHA):
        raise ValueError('pinned build has not completed cleanly')
    if len(result['stages']) != 2:
        raise ValueError('exact configure/build stages required')
    for stage in result['stages']:
        if (stage['status'] != 'PROCESS_COMPLETED' or stage['drain_proof'] != 'CLEANUP'
                or stage['job_active_count'] != 0 or stage['failure_reason']
                or len(stage['workers']) != 1
                or stage['workers'][0]['exit_code'] != 0
                or stage['workers'][0]['assigned'] is not True
                or stage['workers'][0]['resumed'] is not True
                or any(log['stdout_overflow'] is not False or log['stderr_overflow'] is not False
                       for log in stage['logs'].values())):
            raise ValueError('compiler stage did not complete and clean up')
    dlls = json.loads((EVIDENCE / 'fresh_dll_manifest.json').read_text())
    expected_names = {'ggml.dll', 'ggml-base.dll', 'ggml-cpu.dll', 'ggml-rpc.dll', 'ggml-vulkan.dll'}
    if len(dlls) != 5 or {Path(p['path']).name for p in dlls} != expected_names:
        raise ValueError('exact five fresh DLLs required')
    for p in dlls:
        if Path(p['path']).parent.resolve() != (BUILD / 'build_attempt2/bin').resolve() or pin(p['path']) != p:
            raise ValueError('fresh DLL manifest mismatch')
    helper = pin(PHASE / 'fixture_runtime.py')
    if helper['sha256'] != HELPER_SHA:
        raise ValueError('fixed runner hash changed')
    if args.fixture == 'operator':
        if ',' in args.devices:
            raise ValueError('operator requires one explicit device')
        base = PHASE / 'fp32_staging_operator_fixture_revision2_20261004T155012Z'
        source = base / 'fp32_staging_operator.cpp'
        exe = base / 'compile_original_20261004T155012Z/fp32_staging_operator.exe'
        command = ['--device', args.devices]
        if args.negative:
            command.append('--inject-corruption')
        model = None
        supporting = []
        timeout = 30
    else:
        source = ROOT / 'records/factory_runs/20261004/coherent_repair_kv_20261004T130000Z/grok_kv_f32/llama_logits_kv_f32.cpp'
        exe = ROOT / 'records/vulkan_llm_qualification_20261004/fixture_kv_f32/llama_logits_kv_f32.exe'
        model = pin(ROOT / 'records/models/qwen3_06b_f32_derived/Qwen3-0.6B-Q8_0-dequant-F32.gguf')
        command = ['--model', model['path'], '--expected-sha256', model['sha256'],
                   '--devices', args.devices, '--kv-f32']
        if args.negative:
            command.append('--inject-logit-corruption')
        supporting = [pin(ROOT / 'records/build_vulkan_real/build/bin/llama.dll')]
        timeout = 60
    runtime = PHASE / args.run_name
    if runtime.exists():
        raise FileExistsError('new runtime folder required')
    names = {'VULKAN_SDK', 'VK_DRIVER_FILES', 'VK_ICD_FILENAMES', 'VK_LAYER_PATH',
             'VK_INSTANCE_LAYERS', 'VK_ADD_DRIVER_FILES', 'GGML_BACKEND_PATH', 'GGML_BACKEND_DL_PATH'}
    names.update(k for k in os.environ if k.startswith('GGML_VK_'))
    names.update(FLAGS)
    admission = {'schema': 1, 'adjudicator': 'ROOT', 'launch': True, 'fixture': args.fixture,
                 'helper': helper, 'python': pin(sys.executable), 'source': pin(source),
                 'executable': pin(exe), 'dlls': dlls, 'supporting_dlls': supporting,
                 'system_loader': pin('C:/Windows/System32/vulkan-1.dll'), 'model': model,
                 'runtime_dir': str(runtime), 'arguments': command, 'timeout_seconds': timeout,
                 'stream_limit_bytes': 2 * 1024 * 1024, 'child_flags': FLAGS,
                 'parent_runtime_environment': {k: os.environ.get(k) for k in sorted(names)}}
    destination = PHASE / (args.run_name + '_root_admission.json')
    with destination.open('x', encoding='utf-8') as f:
        json.dump(admission, f, indent=2)
        f.write('\n')
    print(json.dumps(pin(destination)))


if __name__ == '__main__':
    main()
