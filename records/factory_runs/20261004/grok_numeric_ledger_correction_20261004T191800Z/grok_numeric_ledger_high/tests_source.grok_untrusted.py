import hashlib
import json
import math
import unittest

import state_ledger as sl

EXPECTED_DLLS = (
    ('ggml.dll', '56aa97d552bdb4e1893f136fa3fbeb4208e3e7aef9e1c4e6a6d45785ac6482fb', 62976),
    ('ggml-base.dll', 'beb563a47637f76e85960648d6970e1e66cadd975541e29d7dc4fd02b5461fa3', 693760),
    ('ggml-cpu.dll', 'e1253c96eb92facb17032a37ee089b185330fac5db5f75bd3c48238d9829f481', 1125888),
    ('ggml-rpc.dll', '11b5c3698fac70ec51a1d743c4bd1324e2b853aa211a0bb85994d68c242453bd', 143872),
    ('ggml-vulkan.dll', '3ed6b1e02b6e56c8fc31d01472e8be33e402f7d0562c6272890799eaa99cc085', 45299712),
)


def dll_map():
    return {name: digest for name, digest, _size in EXPECTED_DLLS}


def dll_sizes():
    return {name: size for name, _digest, size in EXPECTED_DLLS}


def fresh_zeros():
    return [0.0] * sl.VOCAB_COUNT


def make_payload(cpu, gpu):
    data = sl.canonical_payload_bytes(cpu, gpu)
    digest = hashlib.sha256(data).hexdigest()
    max_err = 0.0
    sum_sq = 0.0
    for left, right in zip(cpu, gpu):
        err = abs(float(left) - float(right))
        if err > max_err:
            max_err = err
        sum_sq += err * err
    rmse = math.sqrt(sum_sq / float(sl.VOCAB_COUNT))
    return digest, max_err, rmse


def model_meta(key='original_q8'):
    entry = sl.MODEL_WHITELIST[key]
    return {
        'model_key': key,
        'sha256': entry['sha256'],
        'size': entry['size'],
        'quant': entry['quant'],
        'source_commit': sl.SOURCE_COMMIT,
    }


def runtime_meta():
    return {
        'requested_ctx': sl.REQUESTED_CTX,
        'actual_ctx': sl.ACTUAL_CTX,
        'pinned_ggml_pad': sl.PINNED_GGML_PAD,
        'n_batch': sl.N_BATCH,
        'n_ubatch': sl.N_UBATCH,
        'tokens': list(sl.EXACT_TOKENS),
        'dll_hashes': dll_map(),
        'device_order': ['Vulkan0', 'Vulkan1'],
        'cpu_vs_gpu_origins': {'cpu': 'CPU_REFERENCE', 'gpu': 'VULKAN_GPU_GRAPH'},
        'build_id': 'declared-synthetic-build',
        'exe_sha256': 'ab' * 32,
        'requested_kv': 256,
        'actual_kv': 256,
        'child_f16_disabled': True,
        'fusion_disabled': True,
        'coopmat_disabled': True,
        'coopmat2_disabled': True,
    }


def capture_meta():
    return {
        'native_capture_claimed': False,
        'callback_intrusiveness_declared': True,
        'unsupported_dtype_fail_closed': True,
        'name_op_dim_canonical': True,
        'node_order_declared': True,
        'common_intended_device_workload_separate_cpu_origin': True,
    }


def make_record(cpu, gpu, sha, max_err, rmse, control_kind='baseline_clean', model_key='original_q8'):
    return {
        'experiment_id': 'exp-' + model_key,
        'model_metadata': model_meta(model_key),
        'runtime_metadata': runtime_meta(),
        'capture_metadata': capture_meta(),
        'cpu_logits': cpu,
        'gpu_logits': gpu,
        'payload_sha256': sha,
        'max_abs_err': max_err,
        'rmse': rmse,
        'count': sl.VOCAB_COUNT,
        'control_kind': control_kind,
    }


class StaticConstraints(unittest.TestCase):
    def test_registry_and_tolerance_pins(self):
        self.assertEqual(sl.TRUSTED_DLL_REGISTRY, EXPECTED_DLLS)
        self.assertEqual(sl.EXPECTED_DLL_NAMES, tuple(name for name, _digest, _size in EXPECTED_DLLS))
        self.assertEqual(sl.ATOL, 0.01)
        self.assertEqual(sl.RTOL, 0.01)
        self.assertEqual(sl.VOCAB_COUNT, 151936)
        self.assertNotIn('READY', sl.ALLOWED_STATES)
        self.assertNotIn('PASS', sl.ALLOWED_STATES)
        self.assertIn('DIAGNOSTIC_ONLY', sl.TERMINAL_STATES)

    def test_both_models_and_rejects_float_or_bool_size(self):
        self.assertTrue(sl.validate_model_metadata(model_meta('original_q8')))
        self.assertTrue(sl.validate_model_metadata(model_meta('derived_f32')))
        bad = model_meta('original_q8')
        bad['sha256'] = '0' * 64
        self.assertFalse(sl.validate_model_metadata(bad))
        floated = model_meta('original_q8')
        floated['size'] = float(floated['size'])
        self.assertFalse(sl.validate_model_metadata(floated))
        flagged = model_meta('original_q8')
        flagged['size'] = True
        self.assertFalse(sl.validate_model_metadata(flagged))
        drifted = model_meta('derived_f32')
        drifted['source_commit'] = '0' * 40
        self.assertFalse(sl.validate_model_metadata(drifted))

    def test_unhashable_model_key_fail_closed(self):
        self.assertFalse(sl.validate_model_metadata({'model_key': []}))
        out = sl.evaluate_experiment({'experiment_id': 'x', 'model_metadata': {'model_key': []}})
        self.assertEqual(out['state'], 'NOT_CHECKED')
        self.assertFalse(out['model_pass'])

    def test_tokens_exact_strict_int(self):
        self.assertTrue(sl.validate_tokens(list(range(16))))
        bad = list(range(16))
        bad[3] = 4
        self.assertFalse(sl.validate_tokens(bad))
        floated = list(range(16))
        floated[0] = 0.0
        self.assertFalse(sl.validate_tokens(floated))

    def test_named_dll_registry_accepts_exact_binding(self):
        meta = runtime_meta()
        self.assertTrue(sl.validate_dll_bindings(dll_map()))
        self.assertTrue(sl.validate_runtime_metadata(meta))
        with_bytes = runtime_meta()
        with_bytes['dll_bytes'] = dll_sizes()
        self.assertTrue(sl.validate_runtime_metadata(with_bytes))

    def test_anonymous_duplicate_zero_and_unknown_dlls_rejected(self):
        meta = runtime_meta()
        meta['dll_hashes'] = ['0' * 64] * sl.DLL_COUNT
        self.assertFalse(sl.validate_runtime_metadata(meta))
        meta['dll_hashes'] = [format(i, '064x') for i in range(1, 6)]
        self.assertFalse(sl.validate_runtime_metadata(meta))
        meta['dll_hashes'] = [digest for _name, digest, _size in EXPECTED_DLLS]
        self.assertFalse(sl.validate_runtime_metadata(meta))
        named = dll_map()
        named['ggml.dll'] = '0' * 64
        self.assertFalse(sl.validate_dll_bindings(named))
        copied = dll_map()
        copied['ggml.dll'] = copied['ggml-base.dll']
        self.assertFalse(sl.validate_dll_bindings(copied))
        unknown = dll_map()
        unknown['not-a-ggml.dll'] = unknown.pop('ggml.dll')
        self.assertFalse(sl.validate_dll_bindings(unknown))
        missing = dll_map()
        del missing['ggml-vulkan.dll']
        self.assertFalse(sl.validate_dll_bindings(missing))
        wrong = dll_map()
        wrong['ggml-cpu.dll'] = 'f' * 64
        self.assertFalse(sl.validate_dll_bindings(wrong))
        self.assertFalse(sl.validate_runtime_metadata({}))

    def test_wrong_declared_dll_bytes_rejected(self):
        meta = runtime_meta()
        sizes = dll_sizes()
        sizes['ggml.dll'] = sizes['ggml.dll'] + 1
        meta['dll_bytes'] = sizes
        self.assertFalse(sl.validate_runtime_metadata(meta))
        meta['dll_bytes'] = {'ggml.dll': 62976}
        self.assertFalse(sl.validate_runtime_metadata(meta))

    def test_strict_context_batch_and_flags(self):
        good = runtime_meta()
        self.assertTrue(sl.validate_runtime_metadata(good))
        floated = runtime_meta()
        floated['requested_ctx'] = 128.0
        self.assertFalse(sl.validate_runtime_metadata(floated))
        flagged = runtime_meta()
        flagged['actual_ctx'] = True
        self.assertFalse(sl.validate_runtime_metadata(flagged))
        batch = runtime_meta()
        batch['n_batch'] = 32.0
        self.assertFalse(sl.validate_runtime_metadata(batch))
        pad = runtime_meta()
        pad['pinned_ggml_pad'] = 256.0
        self.assertFalse(sl.validate_runtime_metadata(pad))
        kv = runtime_meta()
        kv['actual_kv'] = 255
        self.assertFalse(sl.validate_runtime_metadata(kv))
        child = runtime_meta()
        child['child_f16_disabled'] = False
        self.assertFalse(sl.validate_runtime_metadata(child))

    def test_runtime_shape_pins(self):
        meta = runtime_meta()
        meta['dll_hashes'] = dll_map()
        meta['exe_sha256'] = 'zzz'
        self.assertFalse(sl.validate_runtime_metadata(meta))
        meta = runtime_meta()
        meta['device_order'] = []
        self.assertFalse(sl.validate_runtime_metadata(meta))
        meta = runtime_meta()
        meta['tokens'] = list(range(15))
        self.assertFalse(sl.validate_runtime_metadata(meta))

    def test_capture_native_claim_rejected(self):
        cap = capture_meta()
        self.assertTrue(sl.validate_capture_metadata(cap))
        cap['native_capture_claimed'] = True
        self.assertFalse(sl.validate_capture_metadata(cap))

    def test_metadata_rounding_and_huge_metric_number(self):
        self.assertTrue(sl._close_metadata_number(0.01, 0.0100000000000001))
        self.assertFalse(sl._close_metadata_number(0.01, 0.0100000001))
        self.assertFalse(sl._close_metadata_number(True, 1))
        self.assertFalse(sl.is_strict_number(10 ** 400))
        self.assertFalse(sl._close_metadata_number(10 ** 400, 10 ** 400))
        self.assertFalse(sl.is_strict_int(True))
        self.assertFalse(sl.is_strict_int(1.0))
        self.assertTrue(sl.is_strict_int(1))


class NumericDiagnostic(unittest.TestCase):
    def test_clean_baseline_is_diagnostic_not_pass(self):
        cpu = fresh_zeros()
        gpu = fresh_zeros()
        sha, max_err, rmse = make_payload(cpu, gpu)
        out = sl.evaluate_experiment(make_record(cpu, gpu, sha, max_err, rmse))
        self.assertEqual(out['state'], 'DIAGNOSTIC_ONLY')
        self.assertEqual(out['fail_count'], 0)
        self.assertFalse(out['model_pass'])
        self.assertFalse(out['transport_corruption_proof'])
        self.assertFalse(out['superseded'])

    def test_cpu_zero_gpu_001005_fails(self):
        cpu = fresh_zeros()
        gpu = fresh_zeros()
        gpu[0] = 0.01005
        sha, max_err, rmse = make_payload(cpu, gpu)
        out = sl.evaluate_experiment(make_record(cpu, gpu, sha, max_err, rmse))
        self.assertEqual(out['state'], 'FAILED_NUMERIC')
        self.assertEqual(out['fail_count'], 1)
        self.assertFalse(out['model_pass'])

    def test_cpu_001005_gpu_zero_is_diagnostic(self):
        cpu = fresh_zeros()
        gpu = fresh_zeros()
        cpu[0] = 0.01005
        sha, max_err, rmse = make_payload(cpu, gpu)
        out = sl.compare_logits(cpu, gpu, sha, max_err, rmse, sl.VOCAB_COUNT)
        self.assertEqual(out['state'], 'DIAGNOSTIC_ONLY')
        self.assertEqual(out['fail_count'], 0)
        self.assertFalse(out['model_pass'])

    def test_synthetic_three_residual_baseline_is_failed_numeric(self):
        cpu = fresh_zeros()
        gpu = fresh_zeros()
        cpu[10] = 1.0
        cpu[20] = 1.0
        cpu[30] = 1.0
        sha, max_err, rmse = make_payload(cpu, gpu)
        out = sl.evaluate_experiment(make_record(cpu, gpu, sha, max_err, rmse))
        self.assertEqual(out['state'], 'FAILED_NUMERIC')
        self.assertEqual(out['fail_count'], 3)
        self.assertEqual(out['count'], sl.VOCAB_COUNT)

    def test_perturbed_gpu_logit_is_comparison_only(self):
        cpu = fresh_zeros()
        gpu = fresh_zeros()
        gpu[7] = 1.0
        sha, max_err, rmse = make_payload(cpu, gpu)
        out = sl.evaluate_experiment(
            make_record(cpu, gpu, sha, max_err, rmse, control_kind='perturbed_negative', model_key='derived_f32')
        )
        self.assertEqual(out['state'], 'DIAGNOSTIC_ONLY')
        self.assertEqual(out['reason'], 'perturbed_negative_comparison_only')
        self.assertEqual(out['fail_count'], 1)
        self.assertEqual(out['model_key'], 'derived_f32')
        self.assertFalse(out['transport_corruption_proof'])
        self.assertFalse(out['model_pass'])
        baseline = sl.evaluate_experiment(
            make_record(cpu, gpu, sha, max_err, rmse, control_kind='baseline_clean', model_key='derived_f32')
        )
        self.assertEqual(baseline['state'], 'FAILED_NUMERIC')

    def test_bad_arg2_control_is_not_checked(self):
        cpu = fresh_zeros()
        sha, max_err, rmse = make_payload(cpu, cpu)
        out = sl.compare_logits(cpu, cpu, sha, max_err, rmse, sl.VOCAB_COUNT, 'bad_arg2')
        self.assertEqual(out['state'], 'NOT_CHECKED')
        self.assertFalse(out['model_pass'])

    def test_nan_and_inf_are_runtime(self):
        cpu = fresh_zeros()
        cpu[5] = float('nan')
        out = sl.compare_logits(cpu, fresh_zeros(), '0' * 64, 0.0, 0.0, sl.VOCAB_COUNT)
        self.assertEqual(out['state'], 'FAILED_RUNTIME')
        inf_cpu = fresh_zeros()
        inf_cpu[1] = float('inf')
        out = sl.compare_logits(inf_cpu, fresh_zeros(), '0' * 64, 0.0, 0.0, sl.VOCAB_COUNT)
        self.assertEqual(out['state'], 'FAILED_RUNTIME')

    def test_count_sha_and_metric_binding(self):
        cpu = fresh_zeros()
        sha, max_err, rmse = make_payload(cpu, cpu)
        mismatched = sl.compare_logits(cpu, cpu, '0' * 64, max_err, rmse, sl.VOCAB_COUNT)
        self.assertEqual(mismatched['state'], 'NOT_CHECKED')
        floated = sl.compare_logits(cpu, cpu, sha, max_err, rmse, float(sl.VOCAB_COUNT))
        self.assertEqual(floated['state'], 'NOT_CHECKED')
        flagged = sl.compare_logits(cpu, cpu, sha, max_err, rmse, True)
        self.assertEqual(flagged['state'], 'NOT_CHECKED')
        unbound = sl.compare_logits(cpu, cpu, sha, max_err + 1.0, rmse, sl.VOCAB_COUNT)
        self.assertEqual(unbound['state'], 'NOT_CHECKED')
        rmse_bad = sl.compare_logits(cpu, cpu, sha, max_err, rmse + 1.0, sl.VOCAB_COUNT)
        self.assertEqual(rmse_bad['state'], 'NOT_CHECKED')

    def test_huge_conversions_fail_closed(self):
        cpu = fresh_zeros()
        cpu[0] = 10 ** 400
        out = sl.compare_logits(cpu, fresh_zeros(), '0' * 64, 0.0, 0.0, sl.VOCAB_COUNT)
        self.assertIn(out['state'], ('NOT_CHECKED', 'FAILED_RUNTIME'))
        self.assertFalse(out['model_pass'])
        clean = fresh_zeros()
        sha, _max_err, rmse = make_payload(clean, clean)
        metric = sl.compare_logits(clean, clean, sha, 10 ** 400, rmse, sl.VOCAB_COUNT)
        self.assertEqual(metric['state'], 'NOT_CHECKED')
        self.assertEqual(sl.validate_logit_list(cpu), 'unrepresentable')

    def test_bool_logit_is_structural(self):
        cpu = fresh_zeros()
        cpu[2] = True
        out = sl.compare_logits(cpu, fresh_zeros(), '0' * 64, 0.0, 0.0, sl.VOCAB_COUNT)
        self.assertEqual(out['state'], 'NOT_CHECKED')


class LedgerTests(unittest.TestCase):
    def test_append_freezes_and_rejects_ready_or_supersede(self):
        base = sl.StateLedger()
        rec = {'state': 'PENDING', 'experiment_id': 'x', 'model_pass': True, 'metadata': {'pins': ['original'], 'model_pass': True}}
        nxt = base.append(rec)
        self.assertEqual(len(base.records()), 0)
        self.assertEqual(len(nxt.records()), 1)
        self.assertFalse(nxt.records()[0]['model_pass'])
        self.assertFalse(nxt.records()[0]['metadata']['model_pass'])
        rec['metadata']['pins'][0] = 'forged'
        self.assertEqual(nxt.records()[0]['metadata']['pins'], ['original'])
        with self.assertRaises(TypeError):
            nxt.records()[0]['state'] = 'DIAGNOSTIC_ONLY'
        with self.assertRaises(TypeError):
            nxt.records()[0]['metadata']['pins'][0] = 'forged'
        with self.assertRaises(ValueError):
            nxt.append({'state': 'READY', 'experiment_id': 'y'})
        with self.assertRaises(ValueError):
            nxt.append({'state': 'PENDING', 'experiment_id': 'y', 'supersede': True})
        plan = json.loads(nxt.candidate_plan())
        self.assertFalse(plan['records'][0]['model_pass'])
        self.assertEqual(plan['records'][0]['metadata']['pins'], ['original'])

    def test_constructor_validates_and_detaches(self):
        with self.assertRaises(ValueError):
            sl.StateLedger(records=[{'state': 'READY', 'experiment_id': 'x', 'model_pass': True}])
        raw = {'state': 'PENDING', 'experiment_id': 'x', 'metadata': {'pins': ['original']}}
        ledger = sl.StateLedger(records=[raw])
        raw['metadata']['pins'][0] = 'forged'
        self.assertEqual(ledger.records()[0]['metadata']['pins'], ['original'])
        with self.assertRaises(ValueError):
            sl.StateLedger(records=[
                {'state': 'FAILED_NUMERIC', 'experiment_id': 'x'},
                {'state': 'RUNNING', 'experiment_id': 'x', 'prior_state': 'PENDING'},
            ])
        with self.assertRaises(ValueError):
            sl.StateLedger(plan_bound=True)
        with self.assertRaises(ValueError):
            sl.StateLedger(plan_bound=1.0)

    def test_actual_prior_binds_forged_and_omitted(self):
        ledger = sl.StateLedger()
        ledger = ledger.append({'state': 'PENDING', 'experiment_id': 'x'})
        ledger = ledger.append({'state': 'RUNNING', 'experiment_id': 'x', 'prior_state': 'PENDING'})
        with self.assertRaises(ValueError):
            ledger.append({'state': 'RUNNING', 'experiment_id': 'x', 'prior_state': 'FAILED_NUMERIC'})
        with self.assertRaises(ValueError):
            ledger.append({'state': 'FAILED_NUMERIC', 'experiment_id': 'x'})
        with self.assertRaises(ValueError):
            sl.StateLedger().append({'state': 'RUNNING', 'experiment_id': 'fresh', 'prior_state': 'PENDING'})
        ledger = ledger.append({'state': 'DIAGNOSTIC_ONLY', 'experiment_id': 'x', 'prior_state': 'RUNNING'})
        with self.assertRaises(ValueError):
            ledger.append({'state': 'RUNNING', 'experiment_id': 'x'})
        with self.assertRaises(ValueError):
            ledger.append({'state': 'RUNNING', 'experiment_id': 'x', 'prior_state': 'PENDING'})
        with self.assertRaises(ValueError):
            ledger.append({'state': 'DIAGNOSTIC_ONLY', 'experiment_id': 'x', 'prior_state': 'RUNNING', 'supersedes': 'old'})

    def test_historical_failure_stays_beside_later_diagnostic(self):
        ledger = sl.StateLedger()
        ledger = ledger.append({'state': 'FAILED_NUMERIC', 'experiment_id': 'historical_q8_workload'})
        ledger = ledger.append({'state': 'PENDING', 'experiment_id': 'attempt5_derived_f32'})
        ledger = ledger.append({'state': 'RUNNING', 'experiment_id': 'attempt5_derived_f32'})
        ledger = ledger.append({'state': 'DIAGNOSTIC_ONLY', 'experiment_id': 'attempt5_derived_f32', 'prior_state': 'RUNNING'})
        self.assertEqual(ledger.records()[0]['state'], 'FAILED_NUMERIC')
        self.assertEqual(ledger.records()[0]['experiment_id'], 'historical_q8_workload')
        self.assertEqual(ledger.records()[-1]['state'], 'DIAGNOSTIC_ONLY')
        self.assertFalse(ledger.records()[-1]['model_pass'])
        with self.assertRaises(ValueError):
            ledger.append({'state': 'DIAGNOSTIC_ONLY', 'experiment_id': 'historical_q8_workload', 'supersede': True})

    def test_candidate_plan_is_bounded_and_no_pass(self):
        ledger = sl.StateLedger(plan_bound=2)
        for i in range(3):
            ledger = ledger.append({'state': 'PENDING', 'experiment_id': 'e' + str(i)})
        text = ledger.candidate_plan()
        self.assertEqual(text, ledger.candidate_plan())
        plan = json.loads(text)
        self.assertEqual(plan['included_count'], 2)
        self.assertEqual(plan['record_count'], 3)
        self.assertEqual(plan['records'][0]['experiment_id'], 'e1')
        self.assertEqual(plan['records'][1]['experiment_id'], 'e2')
        self.assertTrue(plan['bounded'])
        self.assertTrue(plan['no_pass'])
        self.assertFalse(plan['records'][0]['model_pass'])
        self.assertEqual(len(plan['digest']), 64)

    def test_durable_commit_representation_has_no_writes(self):
        ledger = sl.StateLedger().append({'state': 'PENDING', 'experiment_id': 'x'})
        rep = ledger.durable_commit_representation()
        self.assertFalse(rep['writes_performed'])
        self.assertEqual(rep['kind'], 'in_memory_atomic_candidate_plan')
        self.assertEqual(len(rep['sha256']), 64)

    def test_refusal_and_nonserializable_record(self):
        rec = sl.refusal_record('not_admitted')
        self.assertEqual(rec['state'], 'NOT_CHECKED')
        self.assertFalse(rec['model_pass'])
        self.assertEqual(sl.refusal_record('')['reason'], 'refused')
        with self.assertRaises(ValueError):
            sl.StateLedger().append({'state': 'PENDING', 'experiment_id': 'x', 'score': float('nan')})
        with self.assertRaises(ValueError):
            sl.StateLedger().append({'state': 'PENDING', 'experiment_id': 'x', 'blob': set([1])})
        self.assertEqual(sl.evaluate_experiment([])['state'], 'NOT_CHECKED')


if __name__ == '__main__':
    unittest.main()
