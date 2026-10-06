import hashlib
import json
import math

MODEL_WHITELIST = {
    'original_q8': {
        'sha256': '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031',
        'size': 639446688,
        'quant': 'q8_0',
    },
    'derived_f32': {
        'sha256': 'bb38dab890935b8dbd2cb57e68669f39c34ff54dad07ec0dcd80049071bbcf80',
        'size': 2390150816,
        'quant': 'f32',
    },
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
ALLOWED_STATES = (
    'PENDING',
    'RUNNING',
    'FAILED_NUMERIC',
    'FAILED_RUNTIME',
    'NOT_CHECKED',
    'DIAGNOSTIC_ONLY',
)
TERMINAL_STATES = (
    'FAILED_NUMERIC',
    'FAILED_RUNTIME',
    'NOT_CHECKED',
    'DIAGNOSTIC_ONLY',
)
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
EXPECTED_DLL_NAMES = (
    'ggml.dll',
    'ggml-base.dll',
    'ggml-cpu.dll',
    'ggml-rpc.dll',
    'ggml-vulkan.dll',
)
TRUSTED_DLL_REGISTRY = (
    ('ggml.dll', '56aa97d552bdb4e1893f136fa3fbeb4208e3e7aef9e1c4e6a6d45785ac6482fb', 62976),
    ('ggml-base.dll', 'beb563a47637f76e85960648d6970e1e66cadd975541e29d7dc4fd02b5461fa3', 693760),
    ('ggml-cpu.dll', 'e1253c96eb92facb17032a37ee089b185330fac5db5f75bd3c48238d9829f481', 1125888),
    ('ggml-rpc.dll', '11b5c3698fac70ec51a1d743c4bd1324e2b853aa211a0bb85994d68c242453bd', 143872),
    ('ggml-vulkan.dll', '3ed6b1e02b6e56c8fc31d01472e8be33e402f7d0562c6272890799eaa99cc085', 45299712),
)
CLOSED_FLAGS = ('model_pass', 'transport_corruption_proof', 'superseded')


class FrozenList:
    __slots__ = ('_items',)

    def __init__(self, items):
        self._items = tuple(items)

    def __getitem__(self, index):
        return self._items[index]

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __eq__(self, other):
        if isinstance(other, FrozenList):
            return self._items == other._items
        if isinstance(other, (list, tuple)):
            if len(self._items) != len(other):
                return False
            for left, right in zip(self._items, other):
                if left != right:
                    return False
            return True
        return NotImplemented


class FrozenDict:
    __slots__ = ('_items',)

    def __init__(self, pairs):
        self._items = dict(pairs)

    def __getitem__(self, key):
        return self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __contains__(self, key):
        return key in self._items

    def get(self, key, default=None):
        return self._items.get(key, default)

    def items(self):
        return self._items.items()

    def keys(self):
        return self._items.keys()

    def __eq__(self, other):
        if isinstance(other, FrozenDict):
            return self._items == other._items
        if isinstance(other, dict):
            return self._items == other
        return NotImplemented


def is_strict_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _finite_float(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError, TypeError, ArithmeticError):
        return None
    if not math.isfinite(number):
        return None
    return number


def is_strict_number(value):
    return _finite_float(value) is not None


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


def _expected_dll_table():
    if not isinstance(TRUSTED_DLL_REGISTRY, tuple) or len(TRUSTED_DLL_REGISTRY) != DLL_COUNT:
        return None
    if tuple(EXPECTED_DLL_NAMES) != tuple(row[0] for row in TRUSTED_DLL_REGISTRY):
        return None
    mapping = {}
    sizes = {}
    for row in TRUSTED_DLL_REGISTRY:
        if not isinstance(row, tuple) or len(row) != 3:
            return None
        name, digest, size = row
        if not isinstance(name, str) or name in mapping:
            return None
        if not _hex64(digest) or digest == ('0' * 64):
            return None
        if not is_strict_int(size) or size <= 0:
            return None
        mapping[name] = digest
        sizes[name] = size
    if len(set(mapping.values())) != DLL_COUNT:
        return None
    return mapping, sizes


def validate_dll_bindings(declared):
    try:
        table = _expected_dll_table()
        if table is None:
            return False
        expected, _sizes = table
        if not isinstance(declared, dict) or len(declared) != DLL_COUNT:
            return False
        if set(declared.keys()) != set(EXPECTED_DLL_NAMES):
            return False
        digests = []
        for name in EXPECTED_DLL_NAMES:
            digest = declared.get(name)
            if not _hex64(digest) or digest == ('0' * 64):
                return False
            if digest != expected[name]:
                return False
            digests.append(digest)
        return len(set(digests)) == DLL_COUNT
    except (TypeError, ValueError, OverflowError, ArithmeticError):
        return False


def _dll_bytes_ok(meta):
    if 'dll_bytes' not in meta:
        return True
    table = _expected_dll_table()
    if table is None:
        return False
    _mapping, sizes = table
    declared = meta.get('dll_bytes')
    if not isinstance(declared, dict) or set(declared.keys()) != set(EXPECTED_DLL_NAMES):
        return False
    for name in EXPECTED_DLL_NAMES:
        size = declared.get(name)
        if not is_strict_int(size) or size != sizes[name]:
            return False
    return True


def validate_tokens(tokens):
    if not isinstance(tokens, list) or len(tokens) != len(EXACT_TOKENS):
        return False
    for idx, value in enumerate(tokens):
        if not is_strict_int(value) or value != idx:
            return False
    return True


def validate_model_metadata(meta):
    try:
        if not isinstance(meta, dict):
            return False
        model_key = meta.get('model_key')
        if not isinstance(model_key, str) or model_key == '':
            return False
        entry = MODEL_WHITELIST.get(model_key)
        if entry is None:
            return False
        if meta.get('sha256') != entry['sha256']:
            return False
        size = meta.get('size')
        if not is_strict_int(size) or size != entry['size']:
            return False
        if meta.get('quant') != entry['quant']:
            return False
        if meta.get('source_commit') != SOURCE_COMMIT:
            return False
        return True
    except (TypeError, ValueError, OverflowError, ArithmeticError):
        return False


def _pinned_int(meta, key, expected):
    value = meta.get(key)
    return is_strict_int(value) and value == expected


def validate_runtime_metadata(meta):
    try:
        if not isinstance(meta, dict):
            return False
        if not _pinned_int(meta, 'requested_ctx', REQUESTED_CTX):
            return False
        if not _pinned_int(meta, 'actual_ctx', ACTUAL_CTX):
            return False
        if not _pinned_int(meta, 'pinned_ggml_pad', PINNED_GGML_PAD):
            return False
        if not _pinned_int(meta, 'n_batch', N_BATCH):
            return False
        if not _pinned_int(meta, 'n_ubatch', N_UBATCH):
            return False
        if not validate_tokens(meta.get('tokens')):
            return False
        if not validate_dll_bindings(meta.get('dll_hashes')):
            return False
        if not _dll_bytes_ok(meta):
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
    except (TypeError, ValueError, OverflowError, ArithmeticError):
        return False


def validate_capture_metadata(meta):
    try:
        if not isinstance(meta, dict):
            return False
        if meta.get('native_capture_claimed') is not False:
            return False
        if not isinstance(meta.get('callback_intrusiveness_declared'), bool):
            return False
        if meta.get('unsupported_dtype_fail_closed') is not True:
            return False
        for key in (
            'name_op_dim_canonical',
            'node_order_declared',
            'common_intended_device_workload_separate_cpu_origin',
        ):
            if not isinstance(meta.get(key), bool):
                return False
        return True
    except (TypeError, ValueError, OverflowError, ArithmeticError):
        return False


def _classify_logits(values):
    if not isinstance(values, list) or len(values) != VOCAB_COUNT:
        return 'structural'
    saw_nonfinite = False
    saw_unrepresentable = False
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 'structural'
        try:
            number = float(value)
        except (OverflowError, ValueError, TypeError, ArithmeticError):
            saw_unrepresentable = True
            continue
        if not math.isfinite(number):
            saw_nonfinite = True
    if saw_nonfinite:
        return 'nonfinite'
    if saw_unrepresentable:
        return 'unrepresentable'
    return 'ok'


def validate_logit_list(values):
    try:
        return _classify_logits(values)
    except (OverflowError, ValueError, TypeError, ArithmeticError):
        return 'unrepresentable'


def canonical_payload_bytes(cpu_logits, gpu_logits):
    obj = {'cpu': cpu_logits, 'gpu': gpu_logits}
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _close_metadata_number(actual, expected):
    actual_f = _finite_float(actual)
    expected_f = _finite_float(expected)
    if actual_f is None or expected_f is None:
        return False
    return abs(actual_f - expected_f) <= 1e-12


def _refusal(state, reason):
    return {
        'state': state,
        'reason': reason,
        'model_pass': False,
        'transport_corruption_proof': False,
    }


def _compare_logits(cpu_logits, gpu_logits, payload_sha256, max_abs_err, rmse, count, control_kind):
    if control_kind not in ('baseline_clean', 'perturbed_negative'):
        return _refusal('NOT_CHECKED', 'control_kind_malformed')
    if not is_strict_int(count) or count != VOCAB_COUNT:
        return _refusal('NOT_CHECKED', 'count_malformed')
    left = _classify_logits(cpu_logits)
    right = _classify_logits(gpu_logits)
    if left == 'structural' or right == 'structural':
        return _refusal('NOT_CHECKED', 'logit_type_or_length_malformed')
    if left == 'unrepresentable' or right == 'unrepresentable':
        return _refusal('NOT_CHECKED', 'logit_unrepresentable')
    if left == 'nonfinite' or right == 'nonfinite':
        return _refusal('FAILED_RUNTIME', 'logit_nonfinite')
    try:
        computed_sha = hashlib.sha256(canonical_payload_bytes(cpu_logits, gpu_logits)).hexdigest()
    except (TypeError, ValueError, OverflowError, ArithmeticError):
        return _refusal('NOT_CHECKED', 'payload_canonicalization_failed')
    if not _hex64(payload_sha256) or payload_sha256 != computed_sha:
        return _refusal('NOT_CHECKED', 'payload_sha_mismatch')
    fail_indices = []
    max_err = 0.0
    sum_sq = 0.0
    for idx in range(VOCAB_COUNT):
        cpu_value = float(cpu_logits[idx])
        gpu_value = float(gpu_logits[idx])
        err = abs(cpu_value - gpu_value)
        if err > max_err:
            max_err = err
        sum_sq += err * err
        limit = ATOL + (RTOL * abs(cpu_value))
        if err > limit:
            fail_indices.append(idx)
    if not math.isfinite(max_err) or not math.isfinite(sum_sq):
        return _refusal('NOT_CHECKED', 'metric_unrepresentable')
    measured_rmse = math.sqrt(sum_sq / float(VOCAB_COUNT))
    if not math.isfinite(measured_rmse):
        return _refusal('NOT_CHECKED', 'metric_unrepresentable')
    if not _close_metadata_number(max_abs_err, max_err):
        return _refusal('NOT_CHECKED', 'max_abs_err_not_bound')
    if not _close_metadata_number(rmse, measured_rmse):
        return _refusal('NOT_CHECKED', 'rmse_not_bound')
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
        result['state'] = 'DIAGNOSTIC_ONLY'
        result['reason'] = 'perturbed_negative_comparison_only'
        result['transport_corruption_proof'] = False
        result['model_pass'] = False
    return result


def compare_logits(cpu_logits, gpu_logits, payload_sha256, max_abs_err, rmse, count, control_kind='baseline_clean'):
    try:
        return _compare_logits(cpu_logits, gpu_logits, payload_sha256, max_abs_err, rmse, count, control_kind)
    except (OverflowError, TypeError, ValueError, ArithmeticError):
        return _refusal('NOT_CHECKED', 'comparison_fail_closed')


def _evaluate_experiment(record):
    if not isinstance(record, dict):
        return _refusal('NOT_CHECKED', 'record_malformed')
    experiment_id = record.get('experiment_id')
    if not isinstance(experiment_id, str) or experiment_id == '':
        return _refusal('NOT_CHECKED', 'experiment_id_malformed')
    if not validate_model_metadata(record.get('model_metadata')):
        outcome = _refusal('NOT_CHECKED', 'model_metadata_malformed')
        outcome['experiment_id'] = experiment_id
        return outcome
    if not validate_runtime_metadata(record.get('runtime_metadata')):
        outcome = _refusal('NOT_CHECKED', 'runtime_metadata_malformed')
        outcome['experiment_id'] = experiment_id
        return outcome
    if not validate_capture_metadata(record.get('capture_metadata')):
        outcome = _refusal('NOT_CHECKED', 'capture_metadata_malformed')
        outcome['experiment_id'] = experiment_id
        return outcome
    for key in ('cpu_logits', 'gpu_logits', 'payload_sha256', 'max_abs_err', 'rmse', 'count'):
        if key not in record:
            outcome = _refusal('NOT_CHECKED', 'payload_field_missing')
            outcome['experiment_id'] = experiment_id
            return outcome
    control_kind = record.get('control_kind', 'baseline_clean')
    outcome = compare_logits(
        record['cpu_logits'],
        record['gpu_logits'],
        record['payload_sha256'],
        record['max_abs_err'],
        record['rmse'],
        record['count'],
        control_kind,
    )
    outcome['experiment_id'] = experiment_id
    model_meta = record.get('model_metadata')
    if isinstance(model_meta, dict) and isinstance(model_meta.get('model_key'), str):
        outcome['model_key'] = model_meta.get('model_key')
    outcome['superseded'] = False
    outcome['model_pass'] = False
    outcome['transport_corruption_proof'] = False
    return outcome


def evaluate_experiment(record):
    try:
        return _evaluate_experiment(record)
    except (OverflowError, TypeError, ValueError, ArithmeticError):
        experiment_id = 'malformed'
        if isinstance(record, dict):
            candidate = record.get('experiment_id')
            if isinstance(candidate, str) and candidate != '':
                experiment_id = candidate
        outcome = _refusal('NOT_CHECKED', 'evaluation_fail_closed')
        outcome['experiment_id'] = experiment_id
        return outcome


def _freeze(value, stack):
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return True if value else False
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('record_nonfinite')
        return float(value)
    if isinstance(value, dict):
        if id(value) in stack:
            raise ValueError('record_cycle')
        stack.add(id(value))
        pairs = []
        try:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError('record_key_malformed')
                if key in CLOSED_FLAGS:
                    pairs.append((key, False))
                else:
                    pairs.append((key, _freeze(item, stack)))
        finally:
            stack.discard(id(value))
        return FrozenDict(pairs)
    if isinstance(value, (list, tuple)):
        if id(value) in stack:
            raise ValueError('record_cycle')
        stack.add(id(value))
        try:
            items = tuple(_freeze(item, stack) for item in value)
        finally:
            stack.discard(id(value))
        return FrozenList(items)
    raise ValueError('record_not_serializable')


def _actual_prior(existing, experiment_id):
    actual = None
    seen = False
    for rec in existing:
        if rec.get('experiment_id') == experiment_id:
            actual = rec.get('state')
            seen = True
    if not seen:
        return None
    return actual


def _accept(record, existing):
    if not isinstance(record, dict):
        raise ValueError('record_malformed')
    state = record.get('state')
    if state not in ALLOWED_STATES:
        raise ValueError('state_malformed')
    experiment_id = record.get('experiment_id')
    if not isinstance(experiment_id, str) or experiment_id == '':
        raise ValueError('experiment_id_malformed')
    if record.get('supersede') is True or 'supersedes' in record:
        raise ValueError('supersession_forbidden')
    actual_prior = _actual_prior(existing, experiment_id)
    if 'prior_state' in record and record.get('prior_state') != actual_prior:
        raise ValueError('prior_state_forged')
    if actual_prior in TERMINAL_STATES:
        raise ValueError('terminal_restart_forbidden')
    if not transition_allowed(actual_prior, state):
        raise ValueError('transition_forbidden')
    stack = set()
    stack.add(id(record))
    pairs = []
    try:
        for key, item in record.items():
            if not isinstance(key, str):
                raise ValueError('record_key_malformed')
            if key in ('model_pass', 'seq'):
                continue
            if key in CLOSED_FLAGS:
                pairs.append((key, False))
            else:
                pairs.append((key, _freeze(item, stack)))
        pairs.append(('model_pass', False))
        pairs.append(('seq', len(existing)))
    finally:
        stack.discard(id(record))
    return FrozenDict(pairs)


def _thaw(value):
    if isinstance(value, FrozenDict):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, FrozenList):
        return [_thaw(item) for item in value]
    return value


class StateLedger:
    def __init__(self, records=(), plan_bound=PLAN_BOUND_DEFAULT):
        if not is_strict_int(plan_bound) or plan_bound <= 0:
            raise ValueError('plan_bound_malformed')
        if isinstance(records, (str, bytes, dict)) or not isinstance(records, (list, tuple)):
            raise ValueError('records_malformed')
        accepted = []
        for record in records:
            accepted.append(_accept(record, accepted))
        self._plan_bound = plan_bound
        self._records = tuple(accepted)

    def records(self):
        return self._records

    def append(self, record):
        accepted = _accept(record, self._records)
        clone = StateLedger.__new__(StateLedger)
        clone._plan_bound = self._plan_bound
        clone._records = self._records + (accepted,)
        return clone

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
            'records': [_thaw(item) for item in bounded],
            'no_pass': True,
        }
        try:
            payload = json.dumps(plan, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
            plan['digest'] = hashlib.sha256(payload).hexdigest()
            return json.dumps(plan, sort_keys=True, separators=(',', ':'), allow_nan=False)
        except (TypeError, ValueError, OverflowError, ArithmeticError):
            raise ValueError('candidate_plan_not_serializable')

    def durable_commit_representation(self):
        plan = self.candidate_plan()
        return {
            'kind': 'in_memory_atomic_candidate_plan',
            'sha256': hashlib.sha256(plan.encode('utf-8')).hexdigest(),
            'writes_performed': False,
        }


def refusal_record(reason):
    if not isinstance(reason, str) or reason == '':
        reason = 'refused'
    return {
        'state': 'NOT_CHECKED',
        'reason': reason,
        'experiment_id': 'refusal',
        'model_pass': False,
        'transport_corruption_proof': False,
    }
