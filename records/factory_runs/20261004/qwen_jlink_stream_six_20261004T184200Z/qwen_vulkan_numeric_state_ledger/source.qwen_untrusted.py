import hashlib
import json
import math

MODEL_WHITELIST = {
    'original_q8': {'sha256': '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031', 'size': 639446688, 'quant': 'q8_0'},
    'derived_f32': {'sha256': 'bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80', 'size': 2390150816, 'quant': 'f32'},
}
SOURCE_COMMIT = '0faee5004297c3bcfa40b7bf11750127b8c1fd7d'
REQUESTED_CTX = 128
ACTUAL_CTX = 256
PINNED_GGML_PAD = 256
N_BATCH = 32
N_UBATCH = 32
EXACT_TOKENS = tuple(range(16))
VOCAB_COUNT = 151936
ATOL = 0.01
RTOL = 0.01
DLL_COUNT = 5
ALLOWED_STATES = ('PENDING', 'RUNNING', 'FAILED_NUMERIC', 'FAILED_RUNTIME', 'NOT_CHECKED', 'DIAGNOSTIC_ONLY')
TRANSITIONS = {
    'PENDING': ('RUNNING', 'NOT_CHECKED', 'FAILED_RUNTIME'),
    'RUNNING': ('FAILED_NUMERIC', 'FAILED_RUNTIME', 'NOT_CHECKED', 'DIAGNOSTIC_ONLY'),
    'FAILED_NUMERIC': (),
    'FAILED_RUNTIME': (),
    'NOT_CHECKED': (),
    'DIAGNOSTIC_ONLY': (),
}
PLAN_BOUND_DEFAULT = 4096
HEX_DIGITS = '0123456789abcdef'

def is_strict_int(value):
    return isinstance(value, int) and not isinstance(value, bool)

def is_strict_number(value):
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))

def _hex64(value):
    if not isinstance(value, str) or len(value) != 64:
        return False
    for ch in value:
        if ch not in HEX_DIGITS:
            return False
    return True

def transition_allowed(old_state, new_state):
    if new_state not in ALLOWED_STATES:
        return False
    if old_state is None:
        return True
    return new_state in TRANSITIONS.get(old_state, ())

def validate_tokens(tokens):
    if not isinstance(tokens, list) or len(tokens) != len(EXACT_TOKENS):
        return False
    for idx, value in enumerate(tokens):
        if not is_strict_int(value) or value != idx:
            return False
    return True

def validate_model_metadata(meta):
    if not isinstance(meta, dict):
        return False
    entry = MODEL_WHITELIST.get(meta.get('model_key'))
    if entry is None:
        return False
    if meta.get('sha256') != entry['sha256']:
        return False
    if meta.get('size') != entry['size']:
        return False
    if meta.get('quant') != entry['quant']:
        return False
    if meta.get('source_commit') != SOURCE_COMMIT:
        return False
    return True

def validate_runtime_metadata(meta):
    if not isinstance(meta, dict):
        return False
    if meta.get('requested_ctx') != REQUESTED_CTX:
        return False
    if meta.get('actual_ctx') != ACTUAL_CTX:
        return False
    if meta.get('pinned_ggml_pad') != PINNED_GGML_PAD:
        return False
    if meta.get('n_batch') != N_BATCH:
        return False
    if meta.get('n_ubatch') != N_UBATCH:
        return False
    if not validate_tokens(meta.get('tokens')):
        return False
    dlls = meta.get('dll_hashes')
    if not isinstance(dlls, list) or len(dlls) != DLL_COUNT:
        return False
    for item in dlls:
        if not _hex64(item):
            return False
    devices = meta.get('device_order')
    if not isinstance(devices, list) or len(devices) == 0:
        return False
    for item in devices:
        if not isinstance(item, str) or item == '':
            return False
    origins = meta.get('cpu_vs_gpu_origins')
    if not isinstance(origins, dict):
        return False
    if not isinstance(origins.get('cpu'), str) or origins.get('cpu') == '':
        return False
    if not isinstance(origins.get('gpu'), str) or origins.get('gpu') == '':
        return False
    if not isinstance(meta.get('build_id'), str) or meta.get('build_id') == '':
        return False
    if not _hex64(meta.get('exe_sha256')):
        return False
    if not is_strict_int(meta.get('requested_kv')) or meta.get('requested_kv') <= 0:
        return False
    if not is_strict_int(meta.get('actual_kv')) or meta.get('actual_kv') <= 0:
        return False
    if meta.get('requested_kv') != meta.get('actual_kv'):
        return False
    for key in ('child_f16_disabled', 'fusion_disabled', 'coopmat_disabled', 'coopmat2_disabled'):
        if meta.get(key) is not True:
            return False
    return True

def validate_capture_metadata(meta):
    if not isinstance(meta, dict):
        return False
    if meta.get('native_capture_claimed') is not False:
        return False
    if not isinstance(meta.get('callback_intrusiveness_declared'), bool):
        return False
    if meta.get('unsupported_dtype_fail_closed') is not True:
        return False
    for key in ('name_op_dim_canonical', 'node_order_declared', 'common_intended_device_workload_separate_cpu_origin'):
        if not isinstance(meta.get(key), bool):
            return False
    return True

def validate_logit_list(values):
    if not isinstance(values, list) or len(values) != VOCAB_COUNT:
        return 'structural'
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 'structural'
        if not math.isfinite(float(value)):
            return 'nonfinite'
    return 'ok'

def canonical_payload_bytes(cpu_logits, gpu_logits):
    obj = {'cpu': cpu_logits, 'gpu': gpu_logits}
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def _close_metadata_number(actual, expected):
    if not is_strict_number(actual) or not is_strict_number(expected):
        return False
    return abs(float(actual) - float(expected)) <= 1e-12

def compare_logits(cpu_logits, gpu_logits, payload_sha256, max_abs_err, rmse, count, control_kind='baseline_clean'):
    if control_kind not in ('baseline_clean', 'perturbed_negative'):
        return {'state': 'NOT_CHECKED', 'reason': 'control_kind_malformed'}
    if count != VOCAB_COUNT:
        return {'state': 'NOT_CHECKED', 'reason': 'count_malformed'}
    left = validate_logit_list(cpu_logits)
    right = validate_logit_list(gpu_logits)
    if left == 'structural' or right == 'structural':
        return {'state': 'NOT_CHECKED', 'reason': 'logit_type_or_length_malformed'}
    if left == 'nonfinite' or right == 'nonfinite':
        return {'state': 'FAILED_RUNTIME', 'reason': 'logit_nonfinite'}
    try:
        computed_sha = hashlib.sha256(canonical_payload_bytes(cpu_logits, gpu_logits)).hexdigest()
    except Exception:
        return {'state': 'NOT_CHECKED', 'reason': 'payload_canonicalization_failed'}
    if not _hex64(payload_sha256) or payload_sha256 != computed_sha:
        return {'state': 'NOT_CHECKED', 'reason': 'payload_sha_mismatch'}
    fail_indices = []
    max_err = 0.0
    sum_sq = 0.0
    for idx in range(VOCAB_COUNT):
        a = float(cpu_logits[idx])
        b = float(gpu_logits[idx])
        err = abs(a - b)
        if err > max_err:
            max_err = err
        sum_sq += err * err
        if err > (ATOL + RTOL * abs(b)):
            fail_indices.append(idx)
    measured_rmse = math.sqrt(sum_sq / float(VOCAB_COUNT))
    if not _close_metadata_number(max_abs_err, max_err):
        return {'state': 'NOT_CHECKED', 'reason': 'max_abs_err_not_bound'}
    if not _close_metadata_number(rmse, measured_rmse):
        return {'state': 'NOT_CHECKED', 'reason': 'rmse_not_bound'}
    result = {
        'state': 'DIAGNOSTIC_ONLY',
        'reason': 'numerical_diagnostic_complete',
        'control_kind': control_kind,
        'count': VOCAB_COUNT,
        'fail_count': len(fail_indices),
        'fail_indices_sample': fail_indices[:16],
        'measured_max_abs_err': max_err,
        'measured_rmse': measured_rmse,
        'payload_sha256': computed_sha,
        'atol': ATOL,
        'rtol': RTOL,
        'transport_corruption_proof': False,
        'model_pass': False,
    }
    if control_kind == 'baseline_clean' and fail_indices:
        result['state'] = 'FAILED_NUMERIC'
        result['reason'] = 'strict_logit_tolerance_failed'
    if control_kind == 'perturbed_negative':
        result['reason'] = 'perturbed_negative_comparison_only'
        result['transport_corruption_proof'] = False
    return result

def evaluate_experiment(record):
    if not isinstance(record, dict):
        return {'state': 'NOT_CHECKED', 'reason': 'record_malformed'}
    experiment_id = record.get('experiment_id')
    if not isinstance(experiment_id, str) or experiment_id == '':
        return {'state': 'NOT_CHECKED', 'reason': 'experiment_id_malformed'}
    if not validate_model_metadata(record.get('model_metadata')):
        return {'state': 'NOT_CHECKED', 'reason': 'model_metadata_malformed', 'experiment_id': experiment_id}
    if not validate_runtime_metadata(record.get('runtime_metadata')):
        return {'state': 'NOT_CHECKED', 'reason': 'runtime_metadata_malformed', 'experiment_id': experiment_id}
    if not validate_capture_metadata(record.get('capture_metadata')):
        return {'state': 'NOT_CHECKED', 'reason': 'capture_metadata_malformed', 'experiment_id': experiment_id}
    required = ('cpu_logits', 'gpu_logits', 'payload_sha256', 'max_abs_err', 'rmse', 'count')
    for key in required:
        if key not in record:
            return {'state': 'NOT_CHECKED', 'reason': 'payload_field_missing', 'experiment_id': experiment_id}
    control_kind = record.get('control_kind', 'baseline_clean')
    outcome = compare_logits(record['cpu_logits'], record['gpu_logits'], record['payload_sha256'], record['max_abs_err'], record['rmse'], record['count'], control_kind)
    outcome['experiment_id'] = experiment_id
    outcome['model_key'] = record.get('model_metadata', {}).get('model_key')
    outcome['superseded'] = False
    return outcome

class StateLedger:
    def __init__(self, records=(), plan_bound=PLAN_BOUND_DEFAULT):
        if not is_strict_int(plan_bound) or plan_bound <= 0:
            raise ValueError('plan_bound_malformed')
        self._records = tuple(records)
        self._plan_bound = plan_bound

    def records(self):
        return self._records

    def append(self, record):
        if not isinstance(record, dict):
            raise ValueError('record_malformed')
        if record.get('state') not in ALLOWED_STATES:
            raise ValueError('state_malformed')
        if not isinstance(record.get('experiment_id'), str) or record.get('experiment_id') == '':
            raise ValueError('experiment_id_malformed')
        if record.get('supersede') is True or 'supersedes' in record:
            raise ValueError('supersession_forbidden')
        prior = record.get('prior_state')
        if prior is not None and not transition_allowed(prior, record.get('state')):
            raise ValueError('transition_forbidden')
        frozen = dict(record)
        frozen['seq'] = len(self._records)
        frozen['model_pass'] = False
        return StateLedger(self._records + (frozen,), self._plan_bound)

    def candidate_plan(self):
        bounded = self._records[-self._plan_bound:]
        plan = {
            'schema': 'state-ledger-candidate-plan',
            'version': 1,
            'source_commit': SOURCE_COMMIT,
            'bounded': True,
            'plan_bound': self._plan_bound,
            'record_count': len(self._records),
            'included_count': len(bounded),
            'records': list(bounded),
            'no_pass': True,
        }
        payload = json.dumps(plan, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        digest = hashlib.sha256(payload).hexdigest()
        plan['digest'] = digest
        return json.dumps(plan, sort_keys=True, separators=(',', ':'), allow_nan=False)

    def durable_commit_representation(self):
        plan = self.candidate_plan()
        return {'kind': 'in_memory_atomic_candidate_plan', 'sha256': hashlib.sha256(plan.encode('utf-8')).hexdigest(), 'writes_performed': False}

def refusal_record(reason):
    if not isinstance(reason, str) or reason == '':
        reason = 'refused'
    return {'state': 'NOT_CHECKED', 'reason': reason, 'experiment_id': 'refusal', 'model_pass': False}
