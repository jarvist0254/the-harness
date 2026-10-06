"""Independent synthetic controls; run only through the root-admitted controller."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest


def load_candidate():
    path = os.environ.get("PROTOCOL_ADAPTER_CANDIDATE", "")
    if not path or not os.path.isfile(path):
        raise AssertionError("pinned candidate path missing")
    spec = importlib.util.spec_from_file_location("pinned_protocol_adapter", path)
    if spec is None or spec.loader is None:
        raise AssertionError("candidate loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class IndependentAdapterContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_candidate()

    def setUp(self):
        self._observed_adapters = []

    def tearDown(self):
        observed = []
        for adapter, calls in self._observed_adapters:
            report = adapter.report()
            observed.append({
                "callback_names": [name for name, args in calls],
                "egl_import_fds": [args[0].fd for name, args in calls if name == "egl_import_sync_file"],
                "result": report["result"],
                "producer_completion_proven": report["producer_completion_proven"],
                "consumer_completion_proven": report["consumer_completion_proven"],
                "cleanup_state": report["cleanup_state"],
            })
        print(json.dumps({"test": self.id(), "actual_synthetic_observations": observed}, allow_nan=False))

    def binding(self):
        return self.m.Binding(
            "device-uuid-0", "driver-build-0", "source-commit-0", "operation-0",
            "payload-0", "controller-0", "single-word-corruption", "cpu-reference-0",
        )

    def prerequisites(self, **changes):
        values = dict(
            root_admission=True,
            pinned_source_receipt=True,
            independent_native_admission=True,
            kernel_syncobj_to_sync_file_abi="review-token-kernel",
            nvidia_egl_native_fence_import="review-token-egl",
            cache_visibility_contract="review-token-cache",
            producer_completion_receipt="producer-receipt-0",
            consumer_completion_proof="consumer-receipt-0",
            outer_worker_owned=True,
        )
        values.update(changes)
        return self.m.Prerequisites(**values)

    def callbacks(self, calls, overrides=None):
        m = self.m
        overrides = overrides or {}

        def make(name, outcome=None):
            def callback(*args):
                calls.append((name, args))
                if name in overrides:
                    return overrides[name](*args)
                return outcome or m.NativeOutcome(ok=True, observed_fd_consumed=True, payload_visible=True)
            return callback

        return m.Callbacks(
            memory_import=make("memory_import"),
            semaphore_import=make("semaphore_import"),
            producer_completion_wait=make("producer_completion_wait"),
            syncobj_host_signal=make("syncobj_host_signal"),
            syncobj_export_sync_file=make("syncobj_export_sync_file"),
            egl_import_sync_file=make("egl_import_sync_file"),
            consumer_completion_wait=make("consumer_completion_wait"),
            readback=make("readback"),
            cleanup_drain=make("cleanup_drain"),
        )

    def adapter(self, calls, overrides=None, prereqs=None, clock=None):
        adapter = self.m.ProtocolAdapter(
            self.binding(), prereqs or self.prerequisites(), self.callbacks(calls, overrides),
            clock=clock or (lambda: 0.0),
        )
        self._observed_adapters.append((adapter, calls))
        return adapter

    def tokens(self):
        return (
            self.m.FdToken(41, self.m.FdKind.MEMORY_DMA_BUF, "shared-memory-owner"),
            self.m.FdToken(42, self.m.FdKind.SEMAPHORE_SYNCOBJ, "kernel-syncobj-owner"),
        )

    def test_host_relay_order_is_observable_without_claiming_ready(self):
        calls = []
        adapter = self.adapter(calls)
        memory_fd, semaphore_fd = self.tokens()
        report = adapter.run(10.0, memory_fd, semaphore_fd)
        names = [name for name, _ in calls]
        self.assertIn("producer_completion_wait", names)
        self.assertIn("syncobj_host_signal", names)
        self.assertLess(names.index("producer_completion_wait"), names.index("syncobj_host_signal"))
        self.assertFalse(report["direct_transport_qualified"])
        self.assertNotIn("egl_import_sync_file", names)
        self.assertNotEqual(report["result"], self.m.RESULT_READY)

    def test_export_must_produce_a_usable_sync_file_fd(self):
        calls = []
        seen = []

        def import_egl(token, remaining):
            seen.append(token)
            calls.append(("egl_import_sync_file", (token, remaining)))
            return self.m.NativeOutcome(ok=True, observed_fd_consumed=True)

        adapter = self.adapter(calls, {"egl_import_sync_file": import_egl})
        memory_fd, semaphore_fd = self.tokens()
        report = adapter.run(10.0, memory_fd, semaphore_fd)
        self.assertEqual(seen, [], "invalid/missing export must stop before EGL import")
        self.assertNotEqual(report["result"], self.m.RESULT_READY)

    def test_egl_fd_retention_on_success_is_not_reported_as_ready(self):
        calls = []

        def import_egl(token, remaining):
            calls.append(("egl_import_sync_file", (token, remaining)))
            return self.m.NativeOutcome(ok=True, observed_fd_consumed=False)

        adapter = self.adapter(calls, {"egl_import_sync_file": import_egl})
        memory_fd, semaphore_fd = self.tokens()
        report = adapter.run(10.0, memory_fd, semaphore_fd)
        self.assertNotEqual(report["result"], self.m.RESULT_READY)

    def test_infinite_or_nan_deadline_is_rejected_before_callbacks(self):
        import math
        for deadline in (math.inf, math.nan):
            with self.subTest(deadline=deadline):
                calls = []
                adapter = self.adapter(calls)
                memory_fd, semaphore_fd = self.tokens()
                report = adapter.run(deadline, memory_fd, semaphore_fd)
                self.assertNotEqual(report["result"], self.m.RESULT_READY)
                self.assertEqual(calls, [])

    def test_false_text_does_not_satisfy_boolean_admission(self):
        calls = []
        prereqs = self.prerequisites(root_admission="false", outer_worker_owned="false")
        adapter = self.adapter(calls, prereqs=prereqs)
        memory_fd, semaphore_fd = self.tokens()
        report = adapter.run(10.0, memory_fd, semaphore_fd)
        self.assertNotEqual(report["result"], self.m.RESULT_READY)
        self.assertEqual(calls, [])

    def test_false_text_outcome_does_not_prove_completion(self):
        calls = []

        def false_completion(*args):
            calls.append(("producer_completion_wait", args))
            return self.m.NativeOutcome(ok="false", payload_visible="false")

        adapter = self.adapter(calls, {"producer_completion_wait": false_completion})
        memory_fd, semaphore_fd = self.tokens()
        report = adapter.run(10.0, memory_fd, semaphore_fd)
        self.assertNotEqual(report["result"], self.m.RESULT_READY)
        self.assertNotIn("syncobj_host_signal", [name for name, _ in calls])

    def test_callback_exception_is_recorded_and_cleanup_is_attempted(self):
        calls = []

        def broken_wait(*args):
            calls.append(("producer_completion_wait", args))
            raise RuntimeError("synthetic callback failure")

        adapter = self.adapter(calls, {"producer_completion_wait": broken_wait})
        memory_fd, semaphore_fd = self.tokens()
        report = adapter.run(10.0, memory_fd, semaphore_fd)
        self.assertNotEqual(report["result"], self.m.RESULT_READY)
        self.assertIn("cleanup_drain", [name for name, _ in calls])

    def test_second_run_after_timeout_does_not_claim_new_completion(self):
        calls = []
        adapter = self.adapter(calls)
        memory_fd, semaphore_fd = self.tokens()
        first = adapter.run(0.0, memory_fd, semaphore_fd)
        self.assertNotEqual(first["result"], self.m.RESULT_READY)

        def new_operation_timeout(*args):
            calls.append(("producer_completion_wait", args))
            return self.m.NativeOutcome(ok=False, timed_out=True, unknown_inflight=True)

        adapter.callbacks.producer_completion_wait = new_operation_timeout
        second_memory_fd, second_semaphore_fd = self.tokens()
        second = adapter.run(10.0, second_memory_fd, second_semaphore_fd)
        self.assertNotEqual(second["result"], self.m.RESULT_READY)
        self.assertFalse(second["producer_completion_proven"])
        self.assertFalse(second["consumer_completion_proven"])

    def test_completion_state_cannot_be_asserted_without_callback_evidence(self):
        calls = []
        adapter = self.adapter(calls)
        adapter.observe_completion("producer")
        adapter.signal_syncobj(10.0)
        self.assertNotIn("syncobj_host_signal", [name for name, _ in calls])

    def test_report_cannot_mutate_the_internal_event_ledger(self):
        calls = []
        def fail_memory(*args):
            calls.append(("memory_import", args))
            return self.m.NativeOutcome(ok=False, message="synthetic stop")

        adapter = self.adapter(calls, {"memory_import": fail_memory})
        memory_fd, semaphore_fd = self.tokens()
        adapter.run(10.0, memory_fd, semaphore_fd)
        public_report = adapter.report()
        events = adapter.report()["events"]
        self.assertTrue(events, "control must have an observed partial ledger")
        before = events[0]["event"]
        public_report["events"][0]["event"] = "caller-mutated-history"
        self.assertEqual(adapter.report()["events"][0]["event"], before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
