import unittest
import tempfile
import os
import json
import struct
import hashlib
import importlib.util
import sys
import math

CANDIDATE_PATH = os.environ.get('CANDIDATE_PATH', '/opt/comparator/compare_artifacts.py')

def _load_candidate():
    spec = importlib.util.spec_from_file_location('candidate_module', CANDIDATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f'Cannot load candidate from {CANDIDATE_PATH}')
    mod = importlib.util.module_from_spec(spec)
    sys.modules['candidate_module'] = mod
    spec.loader.exec_module(mod)
    return mod.compare_artifacts, mod.CaptureError

def _sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def _make_tensor_f32(dims, val=1.0):
    total = 1
    for d in dims:
        total *= d
    return struct.pack(f'<{total}f', *([val] * total))

def _base_origin(role='CPU_REFERENCE', devices=None, model_sha='9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031', model_bytes=639446688, vulkan_disable_f16=False, vulkan_disable_fusion=False):
    if devices is None:
        devices = [] if role == 'CPU_REFERENCE' else ['Vulkan0']
    return {
        'pinned_commit': '0faee5004297c3bcfa40b7bf11750127b8c1fd7d',
        'source_sha256': 'a' * 64,
        'executable_sha256': 'b' * 64,
        'model_sha256': model_sha,
        'model_bytes': model_bytes,
        'workload_sha256': 'c' * 64,
        'role': role,
        'devices': devices,
        'tokens': list(range(16)),
        'n_ctx_requested': 128,
        'n_ctx_actual': 256,
        'n_batch': 32,
        'n_ubatch': 32,
        'n_threads': 4,
        'kv_type_k': 'F32',
        'kv_type_v': 'F32',
        'flash_attention': False,
        'vulkan_disable_f16': vulkan_disable_f16,
        'vulkan_disable_fusion': vulkan_disable_fusion
    }

def _base_node(ordinal=0, name='attn_norm-0', op='RMS_NORM', dims=None, val=1.0, fname=None):
    if dims is None:
        dims = [1, 2, 3, 4]
    data = _make_tensor_f32(dims, val)
    sha = _sha256_bytes(data)
    d0, d1, d2, d3 = dims
    strides = [4, 4*d0, 4*d0*d1, 4*d0*d1*d2]
    if fname is None:
        fname = f'node_{ordinal}.bin'
    return {
        'ordinal': ordinal,
        'name': name,
        'op': op,
        'dtype': 'F32_LE',
        'dims': dims,
        'strides': strides,
        'nbytes': len(data),
        'sha256': sha,
        'file': fname
    }, data

def _write_root(path, manifest_dict, tensors_dict):
    with open(os.path.join(path, 'manifest.json'), 'w') as f:
        json.dump(manifest_dict, f)
    for fname, data in tensors_dict.items():
        with open(os.path.join(path, fname), 'wb') as f:
            f.write(data)

def _build_valid_pair(cpu_val=1.0, gpu_val=1.0):
    cpu_node, cpu_data = _base_node(val=cpu_val)
    gpu_node, gpu_data = _base_node(val=gpu_val)
    cpu_manifest = {
        'schema': 'LLAMA_CAPTURE_V1',
        'status': 'COMPLETE',
        'diagnostic_intrusive': True,
        'qualification': 'DIAGNOSTIC_ONLY',
        'origin': _base_origin('CPU_REFERENCE', []),
        'captures': [cpu_node]
    }
    gpu_manifest = {
        'schema': 'LLAMA_CAPTURE_V1',
        'status': 'COMPLETE',
        'diagnostic_intrusive': True,
        'qualification': 'DIAGNOSTIC_ONLY',
        'origin': _base_origin('VULKAN_DIAGNOSTIC', ['Vulkan0'], vulkan_disable_f16=True, vulkan_disable_fusion=True),
        'captures': [gpu_node]
    }
    expected = {
        'source_sha256': 'a' * 64,
        'executable_sha256': 'b' * 64,
        'model_sha256': '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031',
        'model_bytes': 639446688,
        'workload_sha256': 'c' * 64,
        'devices': ['Vulkan0']
    }
    return cpu_manifest, {'node_0.bin': cpu_data}, gpu_manifest, {'node_0.bin': gpu_data}, expected

class TestContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compare, cls.CaptureError = _load_candidate()

    def _run(self, cpu_m, cpu_t, gpu_m, gpu_t, exp):
        with tempfile.TemporaryDirectory() as td:
            cpu_root = os.path.join(td, 'cpu')
            gpu_root = os.path.join(td, 'gpu')
            os.makedirs(cpu_root)
            os.makedirs(gpu_root)
            _write_root(cpu_root, cpu_m, cpu_t)
            _write_root(gpu_root, gpu_m, gpu_t)
            return self.compare(cpu_root, gpu_root, None, exp, atol=0.01, rtol=0.01)

    def test_01_match(self):
        cm, ct, gm, gt, exp = _build_valid_pair(1.0, 1.0)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res['result'], 'DIAGNOSTIC_MATCH')

    def test_02_divergence(self):
        cm, ct, gm, gt, exp = _build_valid_pair(1.0, 2.0)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res['result'], 'DIAGNOSTIC_DIVERGENCE')

    def test_03_duplicate_json_keys(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        raw = json.dumps(cm)
        raw = raw.replace('"schema":', '"schema": "X", "schema":', 1)
        with tempfile.TemporaryDirectory() as td:
            cpu_root = os.path.join(td, 'cpu')
            gpu_root = os.path.join(td, 'gpu')
            os.makedirs(cpu_root); os.makedirs(gpu_root)
            with open(os.path.join(cpu_root, 'manifest.json'), 'w') as f: f.write(raw)
            _write_root(gpu_root, gm, gt)
            for fname, data in ct.items():
                with open(os.path.join(cpu_root, fname), 'wb') as f: f.write(data)
            with self.assertRaises(self.CaptureError):
                self.compare(cpu_root, gpu_root, None, exp, atol=0.01, rtol=0.01)

    def test_04_schema_unknown(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['schema'] = 'UNKNOWN'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_05_bool_ordinal(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['captures'][0]['ordinal'] = True
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_06_empty_captures(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['captures'] = []
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_07_truncated_data(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        ct['node_0.bin'] = ct['node_0.bin'][:-4]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_08_wrong_byte_hash(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['captures'][0]['sha256'] = '0' * 64
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_09_nonfinite_nan(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        bad = bytearray(ct['node_0.bin'])
        struct.pack_into('<f', bad, 0, float('nan'))
        ct['node_0.bin'] = bytes(bad)
        cm['captures'][0]['sha256'] = _sha256_bytes(ct['node_0.bin'])
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_10_mismatched_name(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm['captures'][0]['name'] = 'ffn_inp-0'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_11_wrong_source(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        exp['source_sha256'] = 'z' * 64
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_12_ready_status(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['status'] = 'READY'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_13_cpu_role_device_false_control(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['origin']['role'] = 'VULKAN_DIAGNOSTIC'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_14_symlink_escape(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        try:
            with tempfile.TemporaryDirectory() as td:
                cpu_root = os.path.join(td, 'cpu')
                gpu_root = os.path.join(td, 'gpu')
                os.makedirs(cpu_root); os.makedirs(gpu_root)
                _write_root(gpu_root, gm, gt)
                with open(os.path.join(cpu_root, 'manifest.json'), 'w') as f: json.dump(cm, f)
                target = os.path.join(td, 'escape.bin')
                with open(target, 'wb') as f: f.write(ct['node_0.bin'])
                link_path = os.path.join(cpu_root, 'node_0.bin')
                os.symlink(target, link_path)
                with self.assertRaises(self.CaptureError):
                    self.compare(cpu_root, gpu_root, None, exp, atol=0.01, rtol=0.01)
        except OSError:
            self.skipTest('Symlink unsupported on this platform/permissions')

    def test_15_oversize_file(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        ct['node_0.bin'] = b'\x00' * (16777216 + 1)
        cm['captures'][0]['nbytes'] = len(ct['node_0.bin'])
        cm['captures'][0]['sha256'] = _sha256_bytes(ct['node_0.bin'])
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_16_per_element_rtol_not_global(self):
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_val=1000.0, gpu_val=1005.0)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res['result'], 'DIAGNOSTIC_MATCH')

    def test_17_perturb_updated_hash_divergence(self):
        cm, ct, gm, gt, exp = _build_valid_pair(1.0, 1.0)
        bad = bytearray(gt['node_0.bin'])
        struct.pack_into('<f', bad, 0, 999.0)
        gt['node_0.bin'] = bytes(bad)
        gm['captures'][0]['sha256'] = _sha256_bytes(gt['node_0.bin'])
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res['result'], 'DIAGNOSTIC_DIVERGENCE')

    def test_18_corrupt_byte_unchanged_hash_fails_metadata(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        bad = bytearray(gt['node_0.bin'])
        bad[0] = (bad[0] + 1) % 256
        gt['node_0.bin'] = bytes(bad)
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_19_wrong_dtype(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm['captures'][0]['dtype'] = 'F16_LE'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_20_wrong_dims(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm['captures'][0]['dims'] = [1, 2, 3, 5]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_21_duplicate_node(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        n2, d2 = _base_node(ordinal=1, name='attn_norm-0')
        gm['captures'].append(n2)
        gt[n2['file']] = d2
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_22_out_of_order(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        n1, d1 = _base_node(ordinal=0, name='attn_norm-0')
        n2, d2 = _base_node(ordinal=1, name='attn_norm-1')
        gm['captures'] = [n2, n1]
        gt = {n1['file']: d1, n2['file']: d2}
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_23_bool_numeric_dim(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm['captures'][0]['dims'] = [True, 2, 3, 4]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_24_bytes_limit_exceeded(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['captures'][0]['nbytes'] = 67108865
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_25_fake_ready(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm['status'] = 'READY'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_26_kv_wrong(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm['origin']['kv_type_k'] = 'F16'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_27_expected_wrong_model(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        exp['model_sha256'] = '0' * 64
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_28_mismatched_model_context(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm['origin']['n_ctx_actual'] = 512
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_29_device_mismatch(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        exp['devices'] = ['Vulkan1']
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_30_huge_ref_does_not_cover_low_value(self):
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_val=1e6, gpu_val=1e6)
        n2, d2 = _base_node(ordinal=1, name='attn_norm-1', val=1.0)
        cm['captures'].append(n2)
        ct[n2['file']] = d2
        n2g, d2g = _base_node(ordinal=1, name='attn_norm-1', val=2.0)
        gm['captures'].append(n2g)
        gt[n2g['file']] = d2g
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res['result'], 'DIAGNOSTIC_DIVERGENCE')

    def test_31_diagnostic_intrusive_false(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['diagnostic_intrusive'] = False
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_32_qualification_wrong(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm['qualification'] = 'PRODUCTION'
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

if __name__ == '__main__':
    unittest.main()

