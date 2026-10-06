"""ROOT controls against the immutable, schema-refused receipt repair.

Fixtures are synthetic named digest registries, not GPU observations.
"""
import ast
import builtins
import copy
import hashlib
import importlib.machinery
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\qwen_transfer_four_prep_20261004T202539Z\qwen_directed_receipt_repair\source.SCHEMA_REFUSED_UNTRUSTED_REVIEW_ONLY.txt')
PIN = 'fc73cb96c60a4df88815d670f3d6682ff71c3a1cbcaf9dc06942bc780768dc29'
source_bytes = SOURCE.read_bytes()
assert hashlib.sha256(source_bytes).hexdigest() == PIN
tree = ast.parse(source_bytes)
# The complete candidate was reviewed before this admission. Restrict its
# evaluated top level as a second check, rather than trusting file extension.
for node in tree.body:
    assert isinstance(node, (ast.Import, ast.Assign, ast.ClassDef, ast.FunctionDef))
    if isinstance(node, ast.Import):
        assert [a.name for a in node.names] == ['re']
    if isinstance(node, ast.FunctionDef):
        assert not node.decorator_list
        assert all(isinstance(d, ast.Constant) for d in node.args.defaults)
        assert all(d is None or isinstance(d, ast.Constant) for d in node.args.kw_defaults)
    if isinstance(node, ast.ClassDef):
        assert node.name == 'Missing' and len(node.bases) == 1
        assert isinstance(node.bases[0], ast.Name) and node.bases[0].id == 'Exception'
        assert not node.decorator_list and all(isinstance(x, ast.Pass) for x in node.body)
for node in ast.walk(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        assert isinstance(node, ast.Import) and [a.name for a in node.names] == ['re']
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        assert node.func.id not in {'open', 'eval', 'exec', '__import__', 'compile'}

TRAPS = []
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name.split('.')[0] in {'ctypes', '_winapi', 'subprocess', 'multiprocessing', 'socket', 'pyopencl', 'numpy', 'torch', 'cupy'}:
        TRAPS.append('import:' + name)
        raise AssertionError('native/network/process/GPU import denied')
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'ctypes.dlopen', 'ctypes.dlsym'} or event.startswith('socket.'):
        TRAPS.append(event)
        raise AssertionError('native/network/process action denied')
sys.addaudithook(audit)
loader = importlib.machinery.SourceFileLoader('actual_directed_receipt_v2', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
candidate = importlib.util.module_from_spec(spec)
loader.exec_module(candidate)

def h(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def devref(device):
    return {k: device[k] for k in ('vendor', 'uuid', 'pci', 'allocation_id')}

def fixture(reverse=False):
    nv = {'vendor': 'nvidia', 'uuid': '00000000-0000-0000-0000-000000000001', 'pci': '0000:01:00.0', 'allocation_id': h('nv-allocation'), 'api': 'CUDA_SYNTHETIC', 'path': 'cuMemGetHandleForAddressRange', 'kind': 'device'}
    intel = {'vendor': 'intel', 'uuid': '00000000-0000-0000-0000-000000000002', 'pci': '0000:03:00.0', 'allocation_id': h('intel-allocation'), 'api': 'L0_SYNTHETIC', 'path': 'ze_external_memory_import_fd', 'kind': 'device'}
    source, target = (intel, nv) if reverse else (nv, intel)
    direction = 'intel_write_to_nv_device_allocation_cuda_read' if reverse else 'nv_device_dmabuf_export_to_intel_imported_view'
    artifacts = {k: h(k) for k in ('source_executable', 'target_executable', 'build', 'payload', 'controller', 'baseline', 'model', 'workload')}
    registry = {
        'clean_baseline_hashes': [artifacts['baseline']],
        'corruption_control_hashes': [h('corrupt')],
        'consumer_result_hashes': [h('corrupt')],
        'parity_hashes': [h('corrupt')],
        'sync_event_hashes': [h('producer'), h('consumer')],
        'residency_measurement_hashes': [h('measurement')],
        'resource_provenance_hashes': [h('os-provenance')],
        'reverse_visibility_hashes': [h('reverse-visibility')],
    }
    trusted = {'schema': 'p2p.trusted/v2', 'authorities': [{'id': h('authority'), 'name': 'ROOT_SYNTHETIC'}], 'artifacts': copy.deepcopy(artifacts), 'devices': [copy.deepcopy(source), copy.deepcopy(target)], 'evaluation_unix': 1000000, 'max_staleness_seconds': 300, 'transfer': {'direction': direction, 'source_device': devref(source), 'target_device': devref(target), 'payload_bytes': 4096, 'controller': artifacts['controller']}, 'registries': registry}
    receipt = {'schema': 'p2p.transfer.receipt/v2', 'direction': direction, 'source': source, 'target': target, 'artifacts': artifacts, 'sync': {'producer_event_hash': h('producer'), 'consumer_event_hash': h('consumer')}, 'controls': {'cpu_staging': False, 'host_pointer_equality_only': False, 'clean_baseline_hash': artifacts['baseline'], 'producer_corruption_before_copy_hash': h('corrupt')}, 'payload': {'bytes': 4096, 'baseline_hash': artifacts['baseline'], 'consumer_result_hash': h('corrupt'), 'parity_hash': h('corrupt')}, 'residency': {'source_device_resident': True, 'target_device_resident': True, 'measurement_hash': h('measurement'), 'timestamp_unix': 1000000}}
    if reverse:
        receipt.update(write={'allocation_id': nv['allocation_id'], 'pattern_hash': h('corrupt'), 'bytes': 4096, 'provenance_hash': h('os-provenance')}, read={'allocation_id': nv['allocation_id'], 'cuda_read_hash': h('corrupt'), 'bytes': 4096, 'provenance_hash': h('os-provenance')}, reverse_visibility={'method': 'SYNTHETIC_ONLY', 'evidence_hash': h('reverse-visibility')})
    else:
        receipt.update(export={'fd_hash': h('fd-resource'), 'backing_allocation_id': nv['allocation_id'], 'bytes': 4096, 'os_provenance_hash': h('os-provenance')}, import_={})
        del receipt['import_']
        receipt['import'] = {'external_type': 'ZE_EXTERNAL_MEMORY_TYPE_FLAG_DMA_BUF', 'imported_fd_hash': h('fd-resource'), 'allocation_id': intel['allocation_id'], 'bytes': 4096, 'os_provenance_hash': h('os-provenance')}
    return receipt, trusted

outcomes = []
def run(label, mutate=None, expected='refuse', reverse=False, malformed_observation=False):
    receipt, trusted = fixture(reverse)
    if mutate:
        mutate(receipt, trusted)
    original = copy.deepcopy((receipt, trusted))
    try:
        result = candidate.validate(receipt, trusted=trusted)
        error = None
    except Exception as exc:
        result = None
        error = {'type': type(exc).__name__, 'message': str(exc)}
    unchanged = (receipt, trusted) == original
    if malformed_observation:
        verdict = 'OBSERVATION'
    elif error:
        verdict = 'ERROR'
    else:
        consistent = result.get('status') == 'EVIDENCE_CONSISTENT'
        ok = consistent if expected == 'consistent' else not consistent
        if expected == 'host':
            ok = consistent and result.get('classification') == 'HOST_BACKED'
        ok = ok and result.get('transport_accepted') is False and unchanged
        verdict = 'PASS' if ok else 'RED'
    outcomes.append({'case': label, 'verdict': verdict, 'expected': expected, 'result': result, 'exception': error, 'inputs_unchanged': unchanged})

run('legal_forward_declarations', expected='consistent')
run('legal_reverse_declarations', expected='consistent', reverse=True)
def baseline_unbound(r, t):
    r['controls']['clean_baseline_hash'] = r['payload']['baseline_hash'] = h('unrelated')
run('original_baseline_unbound', baseline_unbound)
def same_physical(r, t):
    r['target']['uuid'] = r['source']['uuid']
    r['target']['pci'] = r['source']['pci']
    t['devices'][1] = copy.deepcopy(r['target'])
    t['transfer']['target_device'] = devref(r['target'])
run('original_same_physical_alias', same_physical)
run('original_unregistered_residency', lambda r, t: t['registries'].pop('residency_measurement_hashes'))
run('unregistered_measurement_digest', lambda r, t: r['residency'].update(measurement_hash=h('not-registered')))
run('unregistered_corruption', lambda r, t: t['registries'].update(corruption_control_hashes=[h('other-control')]))
run('unregistered_producer_event', lambda r, t: r['sync'].update(producer_event_hash=h('not-registered')))
run('identical_producer_consumer_events', lambda r, t: r['sync'].update(consumer_event_hash=r['sync']['producer_event_hash']))
run('artifact_model_mismatch', lambda r, t: r['artifacts'].update(model=h('other-model')))
run('payload_size_mismatch', lambda r, t: r['payload'].update(bytes=8192))
run('FD_resource_mismatch', lambda r, t: r['import'].update(imported_fd_hash=h('other-fd')))
run('FD_provenance_mismatch', lambda r, t: r['import'].update(os_provenance_hash=h('other-provenance')))
run('unregistered_resource_provenance', lambda r, t: t['registries'].pop('resource_provenance_hashes'))
run('export_wrong_backing', lambda r, t: r['export'].update(backing_allocation_id=h('other-backing')))
run('target_api_path_mismatch', lambda r, t: r['target'].update(api='other-api'))
run('stale_residency', lambda r, t: r['residency'].update(timestamp_unix=999699))
run('far_future_residency', lambda r, t: r['residency'].update(timestamp_unix=1000301))
run('source_not_resident', lambda r, t: r['residency'].update(source_device_resident=False))
run('untrusted_registry', lambda r, t: t.update(schema='untrusted'))
run('reverse_visibility_unregistered', lambda r, t: t['registries'].pop('reverse_visibility_hashes'), reverse=True)
run('reverse_written_allocation_wrong', lambda r, t: r['write'].update(allocation_id=r['source']['allocation_id']), reverse=True)
run('reverse_pattern_mismatch', lambda r, t: r['read'].update(cuda_read_hash=h('other-pattern')), reverse=True)
run('host_staging_classification', lambda r, t: r['controls'].update(cpu_staging=True), expected='host')
# Malformed-input exceptions are measured separately: this candidate API
# explicitly raises ValueError for some malformed shapes. Do not convert these
# observations into new unstated false-P2P requirements.
run('malformed_bool_payload_size', lambda r, t: r['payload'].update(bytes=True), malformed_observation=True)
run('malformed_unknown_top_field', lambda r, t: r.update(extra=True), malformed_observation=True)
run('malformed_sync_object', lambda r, t: r.update(sync=[]), malformed_observation=True)

scored = [x for x in outcomes if x['verdict'] != 'OBSERVATION']
result = {'scope': 'SYNTHETIC_NAMED_DIGEST_REGISTRY_ONLY_NO_GPU_OR_CRYPTOGRAPHIC_AUTHENTICATION', 'source_sha256': PIN, 'scored': len(scored), 'pass': sum(x['verdict'] == 'PASS' for x in scored), 'red': sum(x['verdict'] == 'RED' for x in scored), 'errors': sum(x['verdict'] == 'ERROR' for x in scored), 'observations': len(outcomes) - len(scored), 'traps': TRAPS, 'outcomes': outcomes, 'source_unchanged': hashlib.sha256(SOURCE.read_bytes()).hexdigest() == PIN}
print(json.dumps(result, indent=2, allow_nan=False))
raise SystemExit(0 if result['red'] == 0 and result['errors'] == 0 and not TRAPS and result['source_unchanged'] else 1)
