import hashlib
import importlib.util
import json
import os
import struct
import sys
import tempfile
import unittest

CANDIDATE_PATH = os.path.abspath(os.environ["CANDIDATE_PATH"])
if not CANDIDATE_PATH.lower().endswith(".py"):
    raise ImportError("CANDIDATE_PATH must be an absolute .py path from the environment")

def _load_candidate():
    name = "candidate_" + hashlib.sha256(CANDIDATE_PATH.encode("utf-8")).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, CANDIDATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load candidate from " + CANDIDATE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.compare_artifacts, module.CaptureError

def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def _make_tensor_f32(dims, val=1.0):
    total = 1
    for dim in dims:
        total *= dim
    return struct.pack("<%df" % total, *([val] * total))

def _tensor_values(values):
    return struct.pack("<%df" % len(values), *values)

def _base_origin(role="CPU_REFERENCE", devices=None, model_sha="9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031", model_bytes=639446688, vulkan_disable_f16=False, vulkan_disable_fusion=False):
    if devices is None:
        devices = [] if role == "CPU_REFERENCE" else ["Vulkan0"]
    return {
        "pinned_commit": "0faee5004297c3bcfa40b7bf11750127b8c1fd7d",
        "source_sha256": "a" * 64,
        "executable_sha256": "b" * 64,
        "model_sha256": model_sha,
        "model_bytes": model_bytes,
        "workload_sha256": "c" * 64,
        "role": role,
        "devices": devices,
        "tokens": list(range(16)),
        "n_ctx_requested": 128,
        "n_ctx_actual": 256,
        "n_batch": 32,
        "n_ubatch": 32,
        "n_threads": 4,
        "kv_type_k": "F32",
        "kv_type_v": "F32",
        "flash_attention": False,
        "vulkan_disable_f16": vulkan_disable_f16,
        "vulkan_disable_fusion": vulkan_disable_fusion,
    }

def _base_node(ordinal=0, name="attn_norm-0", op="RMS_NORM", dims=None, val=1.0, fname=None, values=None):
    if dims is None:
        dims = [1, 2, 3, 4]
    data = _tensor_values(values) if values is not None else _make_tensor_f32(dims, val)
    d0, d1, d2, d3 = dims
    if fname is None:
        fname = "node_%d.bin" % ordinal
    node = {
        "ordinal": ordinal,
        "name": name,
        "op": op,
        "dtype": "F32_LE",
        "dims": dims,
        "strides": [4, 4 * d0, 4 * d0 * d1, 4 * d0 * d1 * d2],
        "nbytes": len(data),
        "sha256": _sha256_bytes(data),
        "file": fname,
    }
    return node, data

def _write_root(path, manifest_dict, tensors_dict):
    with open(os.path.join(path, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest_dict, handle)
    for fname, data in tensors_dict.items():
        with open(os.path.join(path, fname), "wb") as handle:
            handle.write(data)

def _manifest(origin, nodes):
    return {
        "schema": "LLAMA_CAPTURE_V1",
        "status": "COMPLETE",
        "diagnostic_intrusive": True,
        "qualification": "DIAGNOSTIC_ONLY",
        "origin": origin,
        "captures": nodes,
    }

def _build_valid_pair(cpu_val=1.0, gpu_val=1.0, cpu_values=None, gpu_values=None, dims=None):
    cpu_node, cpu_data = _base_node(val=cpu_val, values=cpu_values, dims=dims)
    gpu_node, gpu_data = _base_node(val=gpu_val, values=gpu_values, dims=dims)
    cpu_manifest = _manifest(_base_origin("CPU_REFERENCE", []), [cpu_node])
    gpu_manifest = _manifest(_base_origin("VULKAN_DIAGNOSTIC", ["Vulkan0"], vulkan_disable_f16=True, vulkan_disable_fusion=True), [gpu_node])
    expected = {
        "source_sha256": "a" * 64,
        "executable_sha256": "b" * 64,
        "model_sha256": "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031",
        "model_bytes": 639446688,
        "workload_sha256": "c" * 64,
        "devices": ["Vulkan0"],
    }
    return cpu_manifest, {"node_0.bin": cpu_data}, gpu_manifest, {"node_0.bin": gpu_data}, expected

class TestContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compare, cls.CaptureError = _load_candidate()

    def _run(self, cpu_m, cpu_t, gpu_m, gpu_t, exp, atol=0.01, rtol=0.01):
        with tempfile.TemporaryDirectory() as td:
            cpu_root = os.path.join(td, "cpu")
            gpu_root = os.path.join(td, "gpu")
            os.makedirs(cpu_root)
            os.makedirs(gpu_root)
            _write_root(cpu_root, cpu_m, cpu_t)
            _write_root(gpu_root, gpu_m, gpu_t)
            return self.compare(cpu_root, gpu_root, expected=exp, atol=atol, rtol=rtol)

    def test_01_match(self):
        cm, ct, gm, gt, exp = _build_valid_pair(1.0, 1.0)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_MATCH")
        self.assertEqual(res["comparator"], "COMPARATOR_ONLY")
        self.assertEqual(len(res["nodes"]), 1)
        self.assertEqual(res["nodes"][0]["exact_mismatch_count"], 0)
        self.assertIsNone(res["first_noise"])
        self.assertIsNone(res["first_threshold_violation"])

    def test_02_divergence(self):
        cm, ct, gm, gt, exp = _build_valid_pair(1.0, 2.0)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_DIVERGENCE")
        self.assertEqual(res["first_divergent_ordinal"], 0)
        self.assertGreater(res["stats"]["failed_count"], 0)
        self.assertLessEqual(len(res["stats"]["samples"]), 8)

    def test_03_duplicate_json_keys(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        raw = json.dumps(cm).replace('"schema":', '"schema": "X", "schema":', 1)
        with tempfile.TemporaryDirectory() as td:
            cpu_root = os.path.join(td, "cpu")
            gpu_root = os.path.join(td, "gpu")
            os.makedirs(cpu_root)
            os.makedirs(gpu_root)
            with open(os.path.join(cpu_root, "manifest.json"), "w", encoding="utf-8") as handle:
                handle.write(raw)
            _write_root(gpu_root, gm, gt)
            for fname, data in ct.items():
                with open(os.path.join(cpu_root, fname), "wb") as handle:
                    handle.write(data)
            with self.assertRaises(self.CaptureError):
                self.compare(cpu_root, gpu_root, expected=exp, atol=0.01, rtol=0.01)

    def test_04_schema_unknown(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["schema"] = "UNKNOWN"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_05_bool_ordinal(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["ordinal"] = True
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_06_empty_captures(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"] = []
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_07_truncated_data(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        ct["node_0.bin"] = ct["node_0.bin"][:-4]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_08_wrong_byte_hash(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["sha256"] = "0" * 64
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_09_nonfinite_nan(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        bad = bytearray(ct["node_0.bin"])
        struct.pack_into("<f", bad, 0, float("nan"))
        ct["node_0.bin"] = bytes(bad)
        cm["captures"][0]["sha256"] = _sha256_bytes(ct["node_0.bin"])
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_10_mismatched_name(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["captures"][0]["name"] = "ffn_inp-0"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_11_wrong_source(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        exp["source_sha256"] = "d" * 64
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_12_ready_status(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["status"] = "READY"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_13_cpu_role_device_false_control(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["role"] = "VULKAN_DIAGNOSTIC"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_14_symlink_escape(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        try:
            with tempfile.TemporaryDirectory() as td:
                cpu_root = os.path.join(td, "cpu")
                gpu_root = os.path.join(td, "gpu")
                os.makedirs(cpu_root)
                os.makedirs(gpu_root)
                _write_root(gpu_root, gm, gt)
                with open(os.path.join(cpu_root, "manifest.json"), "w", encoding="utf-8") as handle:
                    json.dump(cm, handle)
                target = os.path.join(td, "escape.bin")
                with open(target, "wb") as handle:
                    handle.write(ct["node_0.bin"])
                os.symlink(target, os.path.join(cpu_root, "node_0.bin"))
                with self.assertRaises(self.CaptureError):
                    self.compare(cpu_root, gpu_root, expected=exp, atol=0.01, rtol=0.01)
        except OSError:
            self.skipTest("Symlink unsupported on this platform/permissions")

    def test_15_oversize_file(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        ct["node_0.bin"] = b"\x00" * (16777216 + 1)
        cm["captures"][0]["nbytes"] = len(ct["node_0.bin"])
        cm["captures"][0]["sha256"] = _sha256_bytes(ct["node_0.bin"])
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_16_per_element_rtol_not_global(self):
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_val=1000.0, gpu_val=1005.0)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_MATCH")
        self.assertGreater(res["nodes"][0]["exact_mismatch_count"], 0)
        self.assertEqual(res["nodes"][0]["failed_count"], 0)
        self.assertIsNotNone(res["first_noise"])
        self.assertIsNone(res["first_threshold_violation"])

    def test_17_perturb_updated_hash_divergence(self):
        cm, ct, gm, gt, exp = _build_valid_pair(1.0, 1.0)
        bad = bytearray(gt["node_0.bin"])
        struct.pack_into("<f", bad, 0, 999.0)
        gt["node_0.bin"] = bytes(bad)
        gm["captures"][0]["sha256"] = _sha256_bytes(gt["node_0.bin"])
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_DIVERGENCE")
        self.assertNotIn("PASS", res["result"])

    def test_18_corrupt_byte_unchanged_hash_fails_metadata(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        bad = bytearray(gt["node_0.bin"])
        bad[0] = (bad[0] + 1) % 256
        gt["node_0.bin"] = bytes(bad)
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_19_wrong_dtype(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["captures"][0]["dtype"] = "F16_LE"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_20_wrong_dims(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["captures"][0]["dims"] = [1, 2, 3, 5]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_21_duplicate_node(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        n2, d2 = _base_node(ordinal=1, name="attn_norm-0")
        gm["captures"].append(n2)
        gt[n2["file"]] = d2
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_22_out_of_order(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        n1, d1 = _base_node(ordinal=0, name="attn_norm-0")
        n2, d2 = _base_node(ordinal=1, name="attn_norm-1")
        gm["captures"] = [n2, n1]
        gt = {n1["file"]: d1, n2["file"]: d2}
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_23_bool_numeric_dim(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["captures"][0]["dims"] = [True, 2, 3, 4]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_24_bytes_limit_exceeded(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["nbytes"] = 67108865
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_25_fake_ready(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["status"] = "READY"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_26_kv_wrong(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["origin"]["kv_type_k"] = "F16"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_27_expected_wrong_model(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        exp["model_sha256"] = "0" * 64
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_28_mismatched_model_context(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["origin"]["n_ctx_actual"] = 512
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_29_device_mismatch(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        exp["devices"] = ["Vulkan1"]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_30_huge_ref_does_not_cover_low_value(self):
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_val=1e6, gpu_val=1e6)
        n2, d2 = _base_node(ordinal=1, name="attn_norm-1", val=1.0)
        cm["captures"].append(n2)
        ct[n2["file"]] = d2
        n2g, d2g = _base_node(ordinal=1, name="attn_norm-1", val=2.0)
        gm["captures"].append(n2g)
        gt[n2g["file"]] = d2g
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_DIVERGENCE")
        self.assertEqual(res["first_divergent_ordinal"], 1)
        self.assertEqual(len(res["nodes"]), 2)
        self.assertEqual(res["nodes"][0]["failed_count"], 0)

    def test_31_diagnostic_intrusive_false(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["diagnostic_intrusive"] = False
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_32_qualification_wrong(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["qualification"] = "PRODUCTION"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_33_keyword_and_missing_pins(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        with tempfile.TemporaryDirectory() as td:
            cpu_root = os.path.join(td, "cpu")
            gpu_root = os.path.join(td, "gpu")
            os.makedirs(cpu_root)
            os.makedirs(gpu_root)
            _write_root(cpu_root, cm, ct)
            _write_root(gpu_root, gm, gt)
            with self.assertRaises(TypeError):
                self.compare(cpu_root, gpu_root)
            with self.assertRaises(TypeError):
                self.compare(cpu_root, gpu_root, exp)
            with self.assertRaises(self.CaptureError):
                self.compare(cpu_root, gpu_root, expected={})
            short = dict(exp)
            del short["workload_sha256"]
            with self.assertRaises(self.CaptureError):
                self.compare(cpu_root, gpu_root, expected=short)
            extra = dict(exp)
            extra["native_proof"] = True
            with self.assertRaises(self.CaptureError):
                self.compare(cpu_root, gpu_root, expected=extra)

    def test_34_tokens_short_reverse_and_bool(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["tokens"] = list(range(15))
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["tokens"] = list(range(15, -1, -1))
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["tokens"] = [True] + list(range(1, 16))
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_35_float_integers_and_uppercase_hex(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["model_bytes"] = float(cm["origin"]["model_bytes"])
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["n_ctx_actual"] = 256.0
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["ordinal"] = 0.0
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["strides"] = [float(x) for x in cm["captures"][0]["strides"]]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["nbytes"] = float(cm["captures"][0]["nbytes"])
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["source_sha256"] = "A" * 64
        exp["source_sha256"] = "A" * 64
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_36_canonical_alias_and_authority_extras(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["name"] = "attn_norm-00"
        gm["captures"][0]["name"] = "attn_norm-00"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["native_pass"] = True
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["origin"]["production_qualified"] = True
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"][0]["trusted"] = True
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_37_tolerance_both_directions_and_bool(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp, atol=0.05, rtol=0.01)
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp, atol=0.01, rtol=0.001)
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp, atol=True, rtol=0.01)

    def test_38_root_and_parent_symlink(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        try:
            with tempfile.TemporaryDirectory() as td:
                real_parent = os.path.join(td, "real_parent")
                cpu_real = os.path.join(real_parent, "cpu")
                gpu_root = os.path.join(td, "gpu")
                os.makedirs(cpu_real)
                os.makedirs(gpu_root)
                _write_root(cpu_real, cm, ct)
                _write_root(gpu_root, gm, gt)
                root_link = os.path.join(td, "cpu_link")
                os.symlink(cpu_real, root_link, target_is_directory=True)
                with self.assertRaises(self.CaptureError):
                    self.compare(root_link, gpu_root, expected=exp)
                parent_link = os.path.join(td, "parent_link")
                os.symlink(real_parent, parent_link, target_is_directory=True)
                via_parent = os.path.join(parent_link, "cpu")
                with self.assertRaises(self.CaptureError):
                    self.compare(via_parent, gpu_root, expected=exp)
        except OSError:
            self.skipTest("Symlink unsupported on this platform/permissions")

    def test_39_noise_before_threshold_all_nodes(self):
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_val=1.0, gpu_val=1.001)
        n2, d2 = _base_node(ordinal=1, name="attn_norm-1", val=1.0)
        cm["captures"].append(n2)
        ct[n2["file"]] = d2
        n2g, d2g = _base_node(ordinal=1, name="attn_norm-1", val=1.5)
        gm["captures"].append(n2g)
        gt[n2g["file"]] = d2g
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_DIVERGENCE")
        self.assertEqual(res["first_noise"], {"ordinal": 0, "name": "attn_norm-0"})
        self.assertEqual(res["first_threshold_violation"], {"ordinal": 1, "name": "attn_norm-1"})
        self.assertEqual(res["first_divergent_ordinal"], 1)
        self.assertEqual(len(res["nodes"]), 2)
        self.assertEqual(res["nodes"][0]["failed_count"], 0)
        self.assertGreater(res["nodes"][0]["exact_mismatch_count"], 0)
        self.assertGreater(res["nodes"][1]["failed_count"], 0)
        self.assertLessEqual(len(res["stats"]["samples"]), 8)

    def test_40_structural_shape_and_op_not_numeric(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        node, data = _base_node(ordinal=0, name="attn_norm-0", dims=[1, 1, 1, 1], val=1.0)
        gm["captures"] = [node]
        gt = {node["file"]: data}
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["captures"][0]["op"] = "OTHER_OP"
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)

    def test_41_small_element_not_hidden_by_large_reference(self):
        dims = [3, 1, 1, 1]
        cpu_values = [1000.0, 1.0, 1.0]
        gpu_values = [1005.0, 1.02, 1.03]
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_values=cpu_values, gpu_values=gpu_values, dims=dims)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_DIVERGENCE")
        self.assertEqual(res["nodes"][0]["failed_count"], 1)
        self.assertEqual(res["stats"]["samples"][0]["index"], 2)
        gpu_values = [1005.0, 1.02, 1.02]
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_values=cpu_values, gpu_values=gpu_values, dims=dims)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_MATCH")
        self.assertEqual(res["nodes"][0]["failed_count"], 0)

    def test_42_device_order_and_pass_budget_before_read(self):
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["origin"]["devices"] = ["Vulkan0", "Vulkan1"]
        exp["devices"] = ["Vulkan1", "Vulkan0"]
        with self.assertRaises(self.CaptureError):
            self._run(cm, ct, gm, gt, exp)
        cm, ct, gm, gt, exp = _build_valid_pair()
        gm["origin"]["devices"] = ["Vulkan0", "Vulkan1"]
        exp["devices"] = ["Vulkan0", "Vulkan1"]
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["result"], "DIAGNOSTIC_MATCH")
        cm, ct, gm, gt, exp = _build_valid_pair()
        cm["captures"] = []
        ct = {}
        dims = [4194304, 1, 1, 1]
        for ordinal in range(5):
            node = {
                "ordinal": ordinal,
                "name": "attn_norm-%d" % ordinal,
                "op": "RMS_NORM",
                "dtype": "F32_LE",
                "dims": dims,
                "strides": [4, 4 * dims[0], 4 * dims[0] * dims[1], 4 * dims[0] * dims[1] * dims[2]],
                "nbytes": 16777216,
                "sha256": "ab" * 32,
                "file": "big_%d.bin" % ordinal,
            }
            cm["captures"].append(node)
            ct[node["file"]] = b"\x00"
        with self.assertRaises(self.CaptureError) as ctx:
            self._run(cm, ct, gm, gt, exp)
        self.assertIn("Pass too large", str(ctx.exception))

    def test_43_samples_capped_at_eight(self):
        dims = [12, 1, 1, 1]
        cm, ct, gm, gt, exp = _build_valid_pair(cpu_val=1.0, gpu_val=2.0, dims=dims)
        res = self._run(cm, ct, gm, gt, exp)
        self.assertEqual(res["nodes"][0]["exact_mismatch_count"], 12)
        self.assertEqual(res["nodes"][0]["failed_count"], 12)
        self.assertEqual(len(res["stats"]["samples"]), 8)

if __name__ == "__main__":
    unittest.main()
