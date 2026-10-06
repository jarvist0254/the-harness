import unittest
import tempfile
import os
import sys
import json
import hashlib
import struct
import importlib.util

CANDIDATE_PATH = os.environ.get('CANDIDATE_PATH', os.path.join(os.path.dirname(__file__), 'capture.py'))
spec = importlib.util.spec_from_file_location('capture_mod', CANDIDATE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
compare_artifacts = mod.compare_artifacts
CaptureError = mod.CaptureError

def mk_manifest(origin, nodes):
    return {
        'schema': 'LLAMA_CAPTURE_V1',
        'status': 'COMPLETE',
        'diagnostic_intrusive': True,
        'qualification': 'DIAGNOSTIC_ONLY',
        'origin': origin,
        'captures': nodes
    }

def mk_origin(role, devices, model_hash='9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031', model_bytes=639446688):
    return {
        'pinned_commit': '0faee5004297c3bcfa40b7bf11750127b8c1fd7d',
        'source_sha256': 'a'*64,
        'executable_sha256': 'b'*64,
        'model_sha256': model_hash,
        'model_bytes': model_bytes,
        'workload_sha256': 'c'*64,
        'role': role,
        'devices': devices,
        'tokens': [0, 1, 2],
        'n_ctx_requested': 128,
        'n_ctx_actual': 256,
        'n_batch': 32,
        'n_ubatch': 32,
        'n_threads': 4,
        'kv_type_k': 'F32',
        'kv_type_v': 'F32',
        'flash_attention': False,
        'vulkan_disable_f16': False if role == 'CPU_REFERENCE' else True,
        'vulkan_disable_fusion': False if role == 'CPU_REFERENCE' else True
    }

def mk_node(idx, name, vals):
    data = struct.pack(f'<{len(vals)}f', *vals)
    h = hashlib.sha256(data).hexdigest()
    d0 = len(vals)
    return {
        'ordinal': idx,
        'name': name,
        'op': 'RMS_NORM',
        'dtype': 'F32_LE',
        'dims': [d0, 1, 1, 1],
        'strides': [4, 4*d0, 4*d0, 4*d0],
        'nbytes': d0*4,
        'sha256': h,
        'file': f'n{idx}.bin'
    }, data

def setup_root(tmpdir, role, devices, nodes_data):
    nodes = []
    for i, (name, vals) in enumerate(nodes_data):
        n, d = mk_node(i, name, vals)
        nodes.append(n)
        with open(os.path.join(tmpdir, f'n{i}.bin'), 'wb') as f:
            f.write(d)
    o = mk_origin(role, devices)
    m = mk_manifest(o, nodes)
    with open(os.path.join(tmpdir, 'manifest.json'), 'w') as f:
        json.dump(m, f)
    return o

class TestCompare(unittest.TestCase):
    def test_match(self):
        with tempfile.TemporaryDirectory() as cpu_d, tempfile.TemporaryDirectory() as gpu_d:
            nd = [('attn_norm-0', [1.0, 2.0, 3.0, 4.0])]
            co = setup_root(cpu_d, 'CPU_REFERENCE', [], nd)
            go = setup_root(gpu_d, 'VULKAN_DIAGNOSTIC', ['Vulkan0'], nd)
            exp = {'source_sha256': co['source_sha256'], 'executable_sha256': co['executable_sha256'],
                   'model_sha256': co['model_sha256'], 'model_bytes': co['model_bytes'],
                   'workload_sha256': co['workload_sha256'], 'devices': go['devices']}
            res = compare_artifacts(cpu_d, gpu_d, expected=exp)
            self.assertEqual(res['result'], 'DIAGNOSTIC_MATCH')

    def test_divergence(self):
        with tempfile.TemporaryDirectory() as cpu_d, tempfile.TemporaryDirectory() as gpu_d:
            cpu_nd = [('attn_norm-0', [1.0, 2.0, 3.0, 4.0])]
            gpu_nd = [('attn_norm-0', [1.0, 2.0, 3.0, 5.0])]
            co = setup_root(cpu_d, 'CPU_REFERENCE', [], cpu_nd)
            go = setup_root(gpu_d, 'VULKAN_DIAGNOSTIC', ['Vulkan0'], gpu_nd)
            exp = {'source_sha256': co['source_sha256'], 'executable_sha256': co['executable_sha256'],
                   'model_sha256': co['model_sha256'], 'model_bytes': co['model_bytes'],
                   'workload_sha256': co['workload_sha256'], 'devices': go['devices']}
            res = compare_artifacts(cpu_d, gpu_d, expected=exp)
            self.assertEqual(res['result'], 'DIAGNOSTIC_DIVERGENCE')
            self.assertEqual(res['first_divergent_ordinal'], 0)
            self.assertIn('stats', res)

    def test_duplicate_key_reject(self):
        with tempfile.TemporaryDirectory() as cpu_d, tempfile.TemporaryDirectory() as gpu_d:
            nd = [('attn_norm-0', [1.0, 2.0, 3.0, 4.0])]
            co = setup_root(cpu_d, 'CPU_REFERENCE', [], nd)
            go = setup_root(gpu_d, 'VULKAN_DIAGNOSTIC', ['Vulkan0'], nd)
            bad = '{"schema":"LLAMA_CAPTURE_V1","schema":"X"}'
            with open(os.path.join(cpu_d, 'manifest.json'), 'w') as f:
                f.write(bad)
            exp = {'source_sha256': co['source_sha256'], 'executable_sha256': co['executable_sha256'],
                   'model_sha256': co['model_sha256'], 'model_bytes': co['model_bytes'],
                   'workload_sha256': co['workload_sha256'], 'devices': go['devices']}
            with self.assertRaises(CaptureError):
                compare_artifacts(cpu_d, gpu_d, expected=exp)

    def test_bool_tolerance_reject(self):
        with tempfile.TemporaryDirectory() as cpu_d, tempfile.TemporaryDirectory() as gpu_d:
            nd = [('attn_norm-0', [1.0, 2.0, 3.0, 4.0])]
            co = setup_root(cpu_d, 'CPU_REFERENCE', [], nd)
            go = setup_root(gpu_d, 'VULKAN_DIAGNOSTIC', ['Vulkan0'], nd)
            exp = {'source_sha256': co['source_sha256'], 'executable_sha256': co['executable_sha256'],
                   'model_sha256': co['model_sha256'], 'model_bytes': co['model_bytes'],
                   'workload_sha256': co['workload_sha256'], 'devices': go['devices']}
            with self.assertRaises(CaptureError):
                compare_artifacts(cpu_d, gpu_d, expected=exp, atol=True, rtol=0.01)

    def test_nonfinite_reject(self):
        with tempfile.TemporaryDirectory() as cpu_d, tempfile.TemporaryDirectory() as gpu_d:
            nd = [('attn_norm-0', [float('nan'), 2.0, 3.0, 4.0])]
            co = setup_root(cpu_d, 'CPU_REFERENCE', [], nd)
            go = setup_root(gpu_d, 'VULKAN_DIAGNOSTIC', ['Vulkan0'], nd)
            exp = {'source_sha256': co['source_sha256'], 'executable_sha256': co['executable_sha256'],
                   'model_sha256': co['model_sha256'], 'model_bytes': co['model_bytes'],
                   'workload_sha256': co['workload_sha256'], 'devices': go['devices']}
            with self.assertRaises(CaptureError):
                compare_artifacts(cpu_d, gpu_d, expected=exp)

if __name__ == '__main__':
    unittest.main()

