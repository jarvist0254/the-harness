"""Independent exact-file synthetic QA. No embedded implementation or provider tests."""
import ast, builtins, copy, hashlib, importlib.util, json, math, os, pathlib, sys, time

SOURCE = pathlib.Path(r'E:\the_harness\records\factory_runs\20261004\grok_capacity_repair_prep_20261004T203621Z\grok_capacity_high\source.grok_untrusted.py')
PIN = '4a27892638447b0913aa2faffa8b4c6c1615011ddc8fde54550fceb9f1190211'
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == PIN
tree = ast.parse(raw)
for node in tree.body:
    assert isinstance(node, (ast.Import, ast.Assign, ast.FunctionDef, ast.ClassDef))
    if isinstance(node, ast.Import):
        assert all(n.name in {'hashlib', 'math'} for n in node.names)
    if isinstance(node, ast.Assign):
        ast.literal_eval(node.value)
    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        assert not node.decorator_list
    if isinstance(node, ast.FunctionDef):
        assert not node.args.defaults and not any(node.args.kw_defaults)

TRAPS = []
class ImportFence:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'ctypes', '_winapi', 'socket', 'subprocess', 'multiprocessing', 'urllib', 'http', 'requests', 'winreg', 'torch', 'cupy', 'pyopencl'}:
            TRAPS.append('import:' + fullname)
            raise AssertionError('Denied native/process/network/GPU import')
        return None

finder = ImportFence()
sys.meta_path.insert(0, finder)
def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'ctypes.dlopen', 'ctypes.dlsym'} or event.startswith('socket.'):
        TRAPS.append(event)
        raise AssertionError('Denied side effect')
sys.addaudithook(audit)
def denied(*args, **kwargs):
    TRAPS.append('filesystem/process function')
    raise AssertionError('Denied side effect')
originals = (builtins.open, os.open, os.system, os.popen)
builtins.open = os.open = os.system = os.popen = denied
try:
    spec = importlib.util.spec_from_file_location('exact_grok_capacity_under_test', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Old RED fixture identities are upgraded to exact named registry bindings.
    # Its single pair CPU1 / GPU1.05 is retained; baseline metrics now actually
    # match the pair so unrelated metric refusal cannot mask the four controls.
    CPU_BYTES = json.dumps([1.0], separators=(',', ':')).encode()
    BYTES = {'model_hash': b'independent-model', 'workload_hash': b'independent-workload',
             'source_hash': b'independent-source', 'exe_hash': b'independent-executable',
             'context_hash': b'independent-context', 'cpu_reference_hash': CPU_BYTES}
    PINS = {key: hashlib.sha256(value).hexdigest() for key, value in BYTES.items()}
    ART = ('model_hash', 'workload_hash', 'source_hash', 'exe_hash', 'context_hash', 'quant')
    def registry():
        return dict(BYTES, artifact_source='owned-synthetic-registry', quant='q8_0')
    def dev(i):
        return {'canonical_id': f'pci:0000:{i:02x}.0', 'physical_alias': f'phys:{i}',
                'aliases': [f'root:{i}', f'sub:{i}:0'], 'discrete': True, 'form_factor': 'discrete_gpu'}
    def attempt(role, count):
        a = {'role': role, 'timestamp_ns': 1000,
             'controller': {'args_valid': True, 'timeout': False, 'policy_cap': False, 'native_error': None},
             'devices': [dev(i) for i in range(count)],
             'allocator': {'class': 'dedicated_vram', 'fresh': True, 'source': 'owned-allocator-fixture', 'timestamp_ns': 1000}}
        a.update({key: PINS[key] for key in ART if key != 'quant'}); a['quant'] = 'q8_0'
        if role != 'four':
            a['execution'] = {'status': 'allocator_oom', 'requested_bytes': 4000}
        else:
            d = abs(1.05 - 1.0)
            a['execution'] = {'status': 'success', 'rmse': d, 'max_abs_error': d,
                              'logits': [{'cpu': 1.0, 'observed': 1.05, 'tol_abs': 0.1}]}
            a['weights'] = [{'device': f'pci:0000:{i:02x}.0', 'shard_hash': hashlib.sha256(f'shard-{i}'.encode()).hexdigest(),
                             'resident_bytes': 1000, 'backing': 'device_vram'} for i in range(4)]
            a['allocator']['peak_bytes_by_device'] = {f'pci:0000:{i:02x}.0': 1000 for i in range(4)}
        return a
    def evidence():
        return dict(PINS, quant='q8_0', artifact_source='owned-synthetic-registry', observed_at_ns=1000,
                    model_bytes=4000, logit_tol_abs=0.1,
                    attempts=[attempt('single', 1), attempt('three', 3), attempt('four', 4)])
    results = []
    def case(name, mutate=None, expected='REFUSE', trust_mutate=None, note='', original_red=False, trusted_override=None):
        e, trusted = evidence(), registry()
        if mutate: mutate(e)
        if trust_mutate: trust_mutate(trusted)
        if trusted_override is not None: trusted = trusted_override
        before = copy.deepcopy((e, trusted))
        try:
            result = module.validate_capacity(e, trusted=trusted)
            valid = isinstance(result, dict) and result.get('status') in {'PASS', 'FAIL', 'NOT_CHECKED'}
            observed = result.get('status') if valid else 'INVALID_RESULT'
            outcome = observed == 'PASS' if expected == 'PASS' else valid and observed != 'PASS'
            exception = None
        except Exception as error:
            result, outcome, exception = None, False, repr(error)
        unchanged = (e, trusted) == before
        results.append({'case': name, 'expected': expected, 'passed': outcome and unchanged,
                        'candidate_result': result, 'uncaught_exception': exception,
                        'inputs_unchanged': unchanged, 'original_measured_red': original_red, 'note': note})
    def four(e): return e['attempts'][2]
    def ex(e): return four(e)['execution']
    def all_on_one(e):
        for w in four(e)['weights']: w['device'] = 'pci:0000:00.0'
        four(e)['allocator']['peak_bytes_by_device']['pci:0000:00.0'] = 4000
    def old_cumulative(e):
        four(e)['weights'][1]['device'] = 'pci:0000:00.0'
    def nonhex(e):
        for key in PINS:
            e[key] = 'not-a-hash'
            if key in ART:
                for a in e['attempts']: a[key] = e[key]
    case('legal_four_device_baseline', expected='PASS')
    case('original_red_all_shards_only_device0', all_on_one, original_red=True)
    case('original_red_sum_shards_exceeds_peak', old_cumulative, original_red=True,
         note='Original mutation retained: also removes device1 shard ownership; separate cumulative-only discriminator below.')
    case('original_red_nonhex_artifact_identifiers', nonhex, original_red=True)
    case('original_red_metrics_contradict_logits', lambda e: ex(e).update(rmse=0.0, max_abs_error=0.0), original_red=True)
    case('legal_repeated_root_enumeration', lambda e: four(e)['devices'].append(copy.deepcopy(four(e)['devices'][0])), expected='PASS')
    def legal_subdevice(e):
        d = copy.deepcopy(four(e)['devices'][0]); d['aliases'].append('sub:0:1')
        four(e)['devices'].append(d)
    case('legal_subdevice_same_canonical_root', legal_subdevice, expected='PASS', note='Physical root canonical ID remains stable; additional runtime subdevice alias is not a new physical card.')
    case('five_distinct_physical_cards', lambda e: four(e)['devices'].append(dev(4)))
    case('three_physical_cards_only', lambda e: four(e).update(devices=four(e)['devices'][:3]))
    case('alias_collision_between_distinct_canonical_ids', lambda e: four(e)['devices'][1]['aliases'].append('root:0'))
    case('missing_card_weights', lambda e: four(e)['weights'].pop())
    def cumulative_only(e):
        four(e)['weights'].append(dict(four(e)['weights'][0], shard_hash=hashlib.sha256(b'extra').hexdigest(), resident_bytes=1))
        four(e)['weights'][1]['resident_bytes'] = 999
    case('cumulative_peak_with_all_cards_covered_and_total_reconciled', cumulative_only)
    def legal_multi(e):
        w = four(e)['weights'][0]; w['resident_bytes'] = 500
        four(e)['weights'].append(dict(w, shard_hash=hashlib.sha256(b'split').hexdigest()))
    case('legal_multiple_shards_per_card', legal_multi, expected='PASS')
    case('replicated_shard', lambda e: four(e)['weights'][1].update(shard_hash=four(e)['weights'][0]['shard_hash']))
    case('registry_digest_mismatch', trust_mutate=lambda t: t.update(workload_hash=b'other'))
    case('registry_invalid_hash', trust_mutate=lambda t: t.update(exe_hash='invalid'))
    case('registry_missing_source', trust_mutate=lambda t: t.pop('source_hash'))
    case('registry_boolean_not_authority', trusted_override=True)
    case('observed_logit_outside_CPU_tolerance', lambda e: ex(e)['logits'][0].update(observed=1.2))
    case('metric_rounding_within_1e12_bound', lambda e: ex(e).update(rmse=ex(e)['rmse']+5e-13, max_abs_error=ex(e)['max_abs_error']+5e-13), expected='PASS')
    case('metric_rounding_beyond_1e12_bound', lambda e: ex(e).update(rmse=ex(e)['rmse']+2e-12, max_abs_error=ex(e)['max_abs_error']+2e-12))
    case('per_logit_tolerance_widened', lambda e: ex(e)['logits'][0].update(tol_abs=0.11))
    case('shared_iGPU_participant', lambda e: four(e)['devices'][3].update(discrete=False, form_factor='integrated_gpu'))
    case('shared_allocator', lambda e: four(e)['allocator'].update(**{'class': 'shared'}))
    case('host_staged_weight_backing', lambda e: four(e)['weights'][0].update(backing='host_staged'))
    case('unknown_weight_backing', lambda e: four(e)['weights'][0].pop('backing'))
    for field in ['model_bytes', 'observed_at_ns']:
        for bad in [True, 4000.0]:
            case(f'{field}_{type(bad).__name__}_refusal', lambda e, f=field, x=bad: e.update({f: x}))
    for bad in [True, 1000.0]:
        case(f'resident_bytes_{type(bad).__name__}_refusal', lambda e, x=bad: four(e)['weights'][0].update(resident_bytes=x))
        case(f'peak_bytes_{type(bad).__name__}_refusal', lambda e, x=bad: four(e)['allocator']['peak_bytes_by_device'].update({'pci:0000:00.0': x}))
        case(f'OOM_requested_bytes_{type(bad).__name__}_refusal', lambda e, x=bad: e['attempts'][0]['execution'].update(requested_bytes=x))
    for bad in [True, float('nan'), float('inf'), '1', 1 << 2000]:
        case(f'invalid_logit_{type(bad).__name__}_{str(bad)[:8]}', lambda e, x=bad: ex(e)['logits'][0].update(observed=x))
    case('stale_allocator', lambda e: four(e)['allocator'].update(timestamp_ns=10**12))
    case('policy_cap_not_allocator_OOM', lambda e: e['attempts'][0]['controller'].update(policy_cap=True))
    case('timeout_not_allocator_OOM', lambda e: e['attempts'][1]['controller'].update(timeout=True))
    # New trust-binding discriminators: alter actual payload/population only.
    def changed_cpu(e):
        ex(e)['logits'][0].update(cpu=2.0, observed=2.05)
        d = abs(2.05-2.0); ex(e).update(rmse=d, max_abs_error=d)
    case('CPU_payload_disagrees_with_registered_reference_bytes', changed_cpu,
         note='Trusted CPU reference is canonical JSON bytes [1.0], whose digest stays pinned; supplied CPU changes to2.0. No particular serialization is parsed by candidate: this measures missing payload-binding contract.')
    case('single_attempt_foreign_physical_population', lambda e: e['attempts'][0].update(devices=[dev(7)]),
         note='Same-workload OOM comparison must use a subset of the qualified four physical participants, not unrelated hardware.')
    case('three_attempt_foreign_physical_population', lambda e: e['attempts'][1].update(devices=[dev(5), dev(6), dev(7)]))
    # Ambiguous canonical-root mapping is observed separately, not scored as a bug.
    e = evidence(); d = copy.deepcopy(four(e)['devices'][0]); d['canonical_id']='runtime-subdevice-0'; four(e)['devices'].append(d)
    observation = module.validate_capacity(e, trusted=registry())
finally:
    builtins.open, os.open, os.system, os.popen = originals
    sys.meta_path.remove(finder)

after = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
assert after == PIN
assert not TRAPS
passed = sum(r['passed'] for r in results)
print(json.dumps({'scope': 'INDEPENDENT_PURE_SYNTHETIC_VALIDATOR_QA_NOT_HARDWARE_CAPACITY',
                  'source_sha256_before': PIN, 'source_sha256_after': after,
                  'counts': {'total': len(results), 'passed': passed, 'failed': len(results)-passed},
                  'original_four_red_fixed': all(r['passed'] for r in results if r['original_measured_red']),
                  'cases': results, 'audit_denied_events': TRAPS,
                  'canonical_mapping_ambiguity_observation': observation,
                  'provider_tests_executed': False}, indent=2))
sys.exit(0 if passed == len(results) else 1)
