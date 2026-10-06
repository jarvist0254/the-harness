"""Unit tests for scripts/nightly_verify.py (target T7).

These tests never run the four real checks. They exercise the parsers on canned
output, run synthetic check specs through the real subprocess path, and drive the
CLI with --dry-run and an empty fake repo root.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import nightly_verify  # noqa: E402

NIGHTLY_SCRIPT = SCRIPTS_DIR / 'nightly_verify.py'
PY = sys.executable
STAMP_RE = re.compile(r'^\d{8}T\d{6}Z$')

# Canned outputs in the exact shapes the real tools emit.
UNITTEST_OK = (
    '................................................................................\n'
    '----------------------------------------------------------------------\n'
    'Ran 80 tests in 0.065s\n'
    '\n'
    'OK\n'
)
UNITTEST_FAILED = (
    '.....F..\n'
    '----------------------------------------------------------------------\n'
    'Ran 8 tests in 0.010s\n'
    '\n'
    'FAILED (failures=1)\n'
)
PLANNER_OK = json.dumps({
    'status': 'PLANNED_NOT_ALLOCATED', 'hypothetical': True,
    'devices': [{'id': 'NVIDIA_0'}, {'id': 'AMD_1'}],
})
MANIFEST_CLEAN = json.dumps({
    'manifest': 'E:/the_harness/records/ADAPTATION_SHA256_<some-stamp>.json',
    'checked': 219, 'failures': [], 'scope': 'integrity only',
})
MANIFEST_DRIFTED = json.dumps({
    'manifest': 'E:/the_harness/records/ADAPTATION_SHA256_<some-stamp>.json',
    'checked': 219, 'failures': ['changed: docs/00_STATUS_AND_PRECEDENCE.md'],
    'scope': 'integrity only',
})


def fake_check(name, python_code, parser='exit_code', expect=None, cmd=None):
    """A synthetic check spec that runs ``python -B -c <code>`` and nothing else."""
    return {
        'name': name,
        'cmd': cmd or [PY, '-B', '-c', python_code],
        'cwd': str(REPO_ROOT),
        'parser': parser,
        'expect': expect or {},
    }


def print_stdout(text):
    """Python source for a child that prints text to stdout and exits 0."""
    return 'import sys; sys.stdout.write(%r)' % (text,)


def print_stderr(text):
    """Python source for a child that prints text to stderr and exits 0."""
    return 'import sys; sys.stderr.write(%r)' % (text,)


class TestParseUnittest(unittest.TestCase):
    def test_ok_output_yields_count_and_verdict(self):
        parsed = nightly_verify.parse_unittest('', UNITTEST_OK, {'min_tests': 1})
        self.assertEqual(parsed['tests_ran'], 80)
        self.assertEqual(parsed['verdict'], 'OK')
        self.assertTrue(parsed['criteria_met'])

    def test_failed_output_does_not_meet_criteria(self):
        parsed = nightly_verify.parse_unittest('', UNITTEST_FAILED, {'min_tests': 1})
        self.assertEqual(parsed['tests_ran'], 8)
        self.assertEqual(parsed['verdict'], 'FAILED (failures=1)')
        self.assertFalse(parsed['criteria_met'])
        self.assertIn('verdict', parsed['reason'])

    def test_ok_on_stdout_is_also_accepted(self):
        parsed = nightly_verify.parse_unittest(UNITTEST_OK, '', {'min_tests': 1})
        self.assertTrue(parsed['criteria_met'])

    def test_missing_summary_is_not_a_pass(self):
        parsed = nightly_verify.parse_unittest('hello', 'world', {'min_tests': 1})
        self.assertIsNone(parsed['verdict'])
        self.assertFalse(parsed['criteria_met'])

    def test_min_tests_floor_is_enforced(self):
        parsed = nightly_verify.parse_unittest('', UNITTEST_OK, {'min_tests': 999})
        self.assertEqual(parsed['tests_ran'], 80)
        self.assertFalse(parsed['criteria_met'])


class TestParseJsonStatus(unittest.TestCase):
    def test_expected_status(self):
        parsed = nightly_verify.parse_json_status(
            PLANNER_OK, '', {'statuses': ['PLANNED_NOT_ALLOCATED']})
        self.assertEqual(parsed['status'], 'PLANNED_NOT_ALLOCATED')
        self.assertEqual(parsed['device_count'], 2)
        self.assertTrue(parsed['criteria_met'])

    def test_unexpected_status(self):
        payload = json.dumps({'status': 'ALLOCATED', 'devices': []})
        parsed = nightly_verify.parse_json_status(
            payload, '', {'statuses': ['PLANNED_NOT_ALLOCATED']})
        self.assertFalse(parsed['criteria_met'])

    def test_non_json_stdout(self):
        parsed = nightly_verify.parse_json_status(
            'Traceback: boom', '', {'statuses': ['PLANNED_NOT_ALLOCATED']})
        self.assertIsNone(parsed['status'])
        self.assertFalse(parsed['criteria_met'])

    def test_json_with_surrounding_noise_is_still_found(self):
        noisy = 'warning: something\n' + PLANNER_OK + '\ntrailing\n'
        parsed = nightly_verify.parse_json_status(
            noisy, '', {'statuses': ['PLANNED_NOT_ALLOCATED']})
        self.assertTrue(parsed['criteria_met'])


class TestParseManifestJson(unittest.TestCase):
    def test_clean_manifest(self):
        parsed = nightly_verify.parse_manifest_json(MANIFEST_CLEAN, '', {'min_checked': 1})
        self.assertEqual(parsed['checked'], 219)
        self.assertEqual(parsed['failures'], [])
        self.assertEqual(parsed['failure_count'], 0)
        self.assertTrue(parsed['criteria_met'])

    def test_drifted_manifest_fails_and_names_the_count(self):
        parsed = nightly_verify.parse_manifest_json(
            MANIFEST_DRIFTED, '', {'min_checked': 1})
        self.assertEqual(parsed['failure_count'], 1)
        self.assertFalse(parsed['criteria_met'])
        self.assertIn('drifted', parsed['reason'])

    def test_non_json_stdout(self):
        parsed = nightly_verify.parse_manifest_json('', 'boom', {'min_checked': 1})
        self.assertIsNone(parsed['checked'])
        self.assertFalse(parsed['criteria_met'])

    def test_zero_checked_is_not_a_pass(self):
        parsed = nightly_verify.parse_manifest_json(
            json.dumps({'checked': 0, 'failures': []}), '', {'min_checked': 1})
        self.assertFalse(parsed['criteria_met'])


class TestRunCheck(unittest.TestCase):
    def test_passing_child_is_pass_with_returncode_zero(self):
        spec = fake_check('synthetic_pass', 'print("ok")')
        result = nightly_verify.run_check(spec, timeout=120)
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue(result['passed'])
        self.assertEqual(result['returncode'], 0)
        self.assertGreaterEqual(result['duration_ms'], 0)

    def test_nonzero_child_is_fail(self):
        spec = fake_check('synthetic_fail', 'import sys; print("nope"); sys.exit(3)')
        result = nightly_verify.run_check(spec, timeout=120)
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['passed'])
        self.assertEqual(result['returncode'], 3)

    def test_parser_criteria_can_fail_even_with_zero_exit(self):
        # Exit code alone must not be trusted: this child exits 0 but its parsed
        # output does not meet expectations.
        spec = fake_check('synthetic_criteria_fail', print_stderr(UNITTEST_FAILED),
                          parser='unittest', expect={'min_tests': 1})
        result = nightly_verify.run_check(spec, timeout=120)
        self.assertEqual(result['returncode'], 0)
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(result['passed'])
        self.assertEqual(result['parsed']['tests_ran'], 8)

    def test_missing_command_is_unavailable_and_does_not_crash(self):
        spec = fake_check('synthetic_missing', '',
                          cmd=['definitely-not-a-real-command-9f3a1c', '--version'])
        result = nightly_verify.run_check(spec, timeout=120)
        self.assertEqual(result['status'], 'UNAVAILABLE')
        self.assertFalse(result['passed'])
        self.assertIsNone(result['returncode'])
        self.assertIn('FileNotFoundError', result['error'])

    def test_empty_command_spec_is_error_not_crash(self):
        result = nightly_verify.run_check({'name': 'empty', 'cmd': []}, timeout=10)
        self.assertEqual(result['status'], 'ERROR')
        self.assertFalse(result['passed'])

    def test_skip_reason_yields_unavailable_without_executing(self):
        # An unresolvable manifest must degrade to UNAVAILABLE (exit 2 territory),
        # and must not launch anything.
        spec = {
            'name': 'artifact_manifest_integrity',
            'cmd': [PY, '-B', '-c', 'raise SystemExit("must never run")'],
            'skip_reason': 'no ADAPTATION_SHA256_*.json found',
            'manifest_resolution': {'mode': 'newest_by_filename_sort',
                                    'status': 'UNAVAILABLE'},
        }
        result = nightly_verify.run_check(spec, timeout=60)
        self.assertEqual(result['status'], 'UNAVAILABLE')
        self.assertFalse(result['passed'])
        self.assertIsNone(result['returncode'])
        self.assertIn('skipped: no ADAPTATION_SHA256_*.json found', result['error'])
        self.assertEqual(result['manifest_resolution']['status'], 'UNAVAILABLE')
        self.assertEqual(result['stdout_tail'], [])

    def test_skip_reason_drives_an_incomplete_verdict(self):
        results = [
            {'name': 'a', 'status': 'PASS', 'passed': True},
            nightly_verify.run_check({'name': 'b', 'cmd': [], 'skip_reason': 'gone'},
                                     timeout=10),
        ]
        self.assertEqual(nightly_verify.verdict_from(results), ('INCOMPLETE', 2))

    def test_timeout_is_recorded_as_timeout(self):
        spec = fake_check('synthetic_timeout', 'import time; time.sleep(30)')
        result = nightly_verify.run_check(spec, timeout=1)
        self.assertEqual(result['status'], 'TIMEOUT')
        self.assertFalse(result['passed'])
        self.assertIn('timed out', result['error'])

    def test_stdout_and_stderr_tails_are_captured(self):
        code = ('import sys\n'
                'for i in range(40): sys.stdout.write("out%d\\n" % i)\n'
                'sys.stderr.write("err-line\\n")\n')
        result = nightly_verify.run_check(fake_check('synthetic_tails', code), timeout=120)
        self.assertEqual(result['stdout_tail'][-1], 'out39')
        self.assertEqual(len(result['stdout_tail']), nightly_verify.TAIL_LINES)
        self.assertEqual(result['stderr_tail'], ['err-line'])
        self.assertGreater(result['stdout_bytes'], 0)

    def test_unknown_parser_falls_back_to_returncode(self):
        spec = fake_check('synthetic_fallback', 'print("x")', parser='not-a-real-parser')
        result = nightly_verify.run_check(spec, timeout=120)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['parsed']['returncode'], 0)


class TestVerdictAndExitCodes(unittest.TestCase):
    def _rec(self, name, status, passed):
        return {'name': name, 'status': status, 'passed': passed}

    def test_all_pass_yields_zero(self):
        results = [self._rec('a', 'PASS', True), self._rec('b', 'PASS', True)]
        self.assertEqual(nightly_verify.verdict_from(results), ('PASS', 0))

    def test_single_failure_yields_one(self):
        results = [self._rec('a', 'PASS', True), self._rec('b', 'FAIL', False)]
        self.assertEqual(nightly_verify.verdict_from(results), ('FAIL', 1))

    def test_unavailable_only_yields_two(self):
        results = [self._rec('a', 'PASS', True), self._rec('b', 'UNAVAILABLE', False)]
        self.assertEqual(nightly_verify.verdict_from(results), ('INCOMPLETE', 2))

    def test_failure_outranks_unavailable(self):
        results = [self._rec('a', 'UNAVAILABLE', False), self._rec('b', 'FAIL', False)]
        self.assertEqual(nightly_verify.verdict_from(results), ('FAIL', 1))

    def test_timeout_counts_as_loud_failure(self):
        results = [self._rec('a', 'TIMEOUT', False)]
        self.assertEqual(nightly_verify.verdict_from(results), ('FAIL', 1))

    def test_empty_result_list_yields_two(self):
        self.assertEqual(nightly_verify.verdict_from([]), ('NO_CHECKS', 2))

    def test_counts_tally_every_status(self):
        results = [self._rec('a', 'PASS', True), self._rec('b', 'FAIL', False),
                   self._rec('c', 'UNAVAILABLE', False), self._rec('d', 'TIMEOUT', False),
                   self._rec('e', 'ERROR', False)]
        counts = nightly_verify.count_statuses(results)
        self.assertEqual(counts, {'total': 5, 'pass': 1, 'fail': 1, 'timeout': 1,
                                  'unavailable': 1, 'error': 1})


class TestRunAllSynthetic(unittest.TestCase):
    """End-to-end over an injected fake check list - no real check is touched."""

    def test_all_pass_run_yields_exit_zero(self):
        checks = [
            fake_check('s1', print_stderr(UNITTEST_OK), parser='unittest',
                       expect={'min_tests': 1}),
            fake_check('s2', print_stdout(PLANNER_OK), parser='json_status',
                       expect={'statuses': ['PLANNED_NOT_ALLOCATED']}),
            fake_check('s3', print_stdout(MANIFEST_CLEAN), parser='manifest_json',
                       expect={'min_checked': 1}),
        ]
        results = nightly_verify.run_all(checks, timeout=180)
        self.assertEqual([r['status'] for r in results], ['PASS', 'PASS', 'PASS'])
        self.assertEqual(nightly_verify.verdict_from(results), ('PASS', 0))

    def test_failing_check_in_a_batch_yields_exit_one(self):
        checks = [
            fake_check('good', print_stderr(UNITTEST_OK), parser='unittest',
                       expect={'min_tests': 1}),
            fake_check('bad', print_stdout(MANIFEST_DRIFTED), parser='manifest_json',
                       expect={'min_checked': 1}),
        ]
        results = nightly_verify.run_all(checks, timeout=180)
        self.assertEqual(results[0]['status'], 'PASS')
        self.assertEqual(results[1]['status'], 'FAIL')
        self.assertEqual(nightly_verify.verdict_from(results), ('FAIL', 1))

    def test_missing_command_in_a_batch_does_not_abort_the_batch(self):
        checks = [
            fake_check('ghost', '', cmd=['no-such-binary-4b7e2d']),
            fake_check('still_runs', 'print("ran")'),
        ]
        results = nightly_verify.run_all(checks, timeout=180)
        self.assertEqual(results[0]['status'], 'UNAVAILABLE')
        self.assertEqual(results[1]['status'], 'PASS')
        self.assertEqual(nightly_verify.verdict_from(results), ('INCOMPLETE', 2))


class TestReceiptWriting(unittest.TestCase):
    def _receipt(self, statuses):
        results = []
        for index, (status, passed) in enumerate(statuses):
            results.append({
                'name': 'check_%d' % index, 'command': [PY, '-B', '-c', 'pass'],
                'command_string': 'python -B -c pass', 'cwd': str(REPO_ROOT),
                'parser': 'exit_code', 'returncode': 0 if passed else 1,
                'duration_ms': 5, 'status': status, 'passed': passed,
                'parsed': {'tests_ran': 80, 'verdict': 'OK', 'criteria_met': passed},
                'error': None if passed else 'exit code 1',
                'stdout_tail': ['out-line'], 'stderr_tail': ['err-line'],
                'stdout_bytes': 9, 'stderr_bytes': 9,
            })
        pins = nightly_verify.collect_pins()
        return nightly_verify.build_receipt(
            results, pins, nightly_verify.utc_stamp(), 42, REPO_ROOT, NIGHTLY_SCRIPT,
            notes=['synthetic receipt written by test_nightly_verify'])

    def test_receipt_has_the_expected_top_level_keys(self):
        receipt = self._receipt([('PASS', True), ('PASS', True)])
        for key in ('schema_version', 'target', 'stamp', 'generated_utc',
                    'generated_iso', 'duration_ms', 'host_pins', 'checks', 'counts',
                    'overall_verdict', 'exit_code', 'exit_code_policy', 'source'):
            self.assertIn(key, receipt)
        self.assertEqual(receipt['schema_version'], nightly_verify.SCHEMA_VERSION)
        self.assertEqual(receipt['overall_verdict'], 'PASS')
        self.assertEqual(receipt['exit_code'], 0)
        self.assertEqual(len(receipt['checks']), 2)

    def test_every_check_record_carries_the_required_fields(self):
        receipt = self._receipt([('PASS', True), ('FAIL', False)])
        for check in receipt['checks']:
            for key in ('name', 'command', 'returncode', 'duration_ms', 'status',
                        'passed', 'parsed', 'stdout_tail', 'stderr_tail'):
                self.assertIn(key, check)

    def test_written_receipt_json_round_trips_from_disk(self):
        receipt = self._receipt([('PASS', True)])
        with tempfile.TemporaryDirectory() as tmp:
            receipt_path, summary_path = nightly_verify.write_receipt(
                tmp, receipt['stamp'], receipt)
            self.assertTrue(receipt_path.is_file())
            self.assertTrue(summary_path.is_file())
            self.assertEqual(receipt_path.parent.name, receipt['stamp'])
            loaded = json.loads(receipt_path.read_text(encoding='utf-8'))
        self.assertEqual(loaded['overall_verdict'], 'PASS')
        self.assertEqual(loaded['exit_code'], 0)
        self.assertEqual(loaded['counts']['total'], 1)

    def test_failing_receipt_writes_exit_one_and_summary_names_the_failure(self):
        receipt = self._receipt([('PASS', True), ('FAIL', False)])
        self.assertEqual(receipt['overall_verdict'], 'FAIL')
        self.assertEqual(receipt['exit_code'], 1)
        with tempfile.TemporaryDirectory() as tmp:
            receipt_path, summary_path = nightly_verify.write_receipt(
                tmp, receipt['stamp'], receipt)
            summary = summary_path.read_text(encoding='utf-8')
            self.assertTrue(receipt_path.is_file())
            self.assertTrue(summary_path.is_file())
        self.assertIn('**FAIL** (exit 1)', summary)
        self.assertIn('check_1', summary)
        self.assertIn('Failures requiring attention', summary)

    def test_unavailable_receipt_writes_exit_two(self):
        receipt = self._receipt([('PASS', True), ('UNAVAILABLE', False)])
        self.assertEqual(receipt['overall_verdict'], 'INCOMPLETE')
        self.assertEqual(receipt['exit_code'], 2)

    def test_summary_renders_for_a_minimal_receipt(self):
        receipt = self._receipt([('PASS', True)])
        receipt['host_pins'] = {}
        text = nightly_verify.render_summary(receipt)
        self.assertIn('# Nightly verification receipt', text)
        self.assertIn('## Verdict', text)
        self.assertTrue(text.endswith('\n'))

    def test_summary_renders_gpu_memory_despite_nvidia_smi_unit_suffix(self):
        # nvidia-smi's CSV header is "memory.total [MiB]", not "memory.total".
        receipt = self._receipt([('PASS', True)])
        receipt['host_pins'] = {
            'platform': 'Windows-10-10.0.26200-SP0',
            'os_build': {'version_string': '10.0.26200'},
            'python': {'version': '3.10.11', 'executable': PY, 'compiler': 'MSC'},
            'packages': {'numpy': '2.2.6'},
            'gpu_inventory': {
                'tool': 'nvidia-smi', 'status': 'OK', 'device_count': 1,
                'devices': [{'name': 'NVIDIA GeForce RTX 5070 Ti',
                             'driver_version': '591.86',
                             'memory.total [MiB]': '16303 MiB'}],
            },
            'tool_probes': {},
        }
        text = nightly_verify.render_summary(receipt)
        self.assertIn('16303 MiB', text)
        self.assertIn('driver 591.86', text)
        self.assertNotIn('| None', text)

    def test_summary_renders_unavailable_gpu_inventory_without_crashing(self):
        receipt = self._receipt([('PASS', True)])
        receipt['host_pins'] = {
            'gpu_inventory': {'tool': 'nvidia-smi', 'status': 'UNAVAILABLE',
                              'reason': 'nvidia-smi not found on PATH', 'devices': []},
        }
        text = nightly_verify.render_summary(receipt)
        self.assertIn('UNAVAILABLE - nvidia-smi not found on PATH', text)

    def test_stamp_format_and_monotonic_ordering(self):
        first = nightly_verify.utc_stamp()
        self.assertRegex(first, STAMP_RE)
        second = nightly_verify.utc_stamp()
        self.assertRegex(second, STAMP_RE)
        self.assertLessEqual(first, second)

    def test_stamp_is_utc_and_matches_its_datetime(self):
        when = datetime(2026, 10, 5, 3, 0, 7, tzinfo=timezone.utc)
        self.assertEqual(nightly_verify.utc_stamp(when), '20261005T030007Z')

    def test_generated_timestamps_are_not_in_the_past(self):
        before = datetime.now(timezone.utc).replace(microsecond=0)
        receipt = self._receipt([('PASS', True)])
        generated = datetime.strptime(
            receipt['generated_utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(generated, before)


class TestHostPins(unittest.TestCase):
    def test_collect_pins_never_raises_and_has_the_required_sections(self):
        pins = nightly_verify.collect_pins()
        for key in ('platform', 'system', 'os_build', 'python', 'packages',
                    'gpu_inventory', 'tool_probes'):
            self.assertIn(key, pins)
        self.assertEqual(pins['python']['executable'], PY)
        self.assertTrue(pins['python']['version'])

    def test_package_pins_are_versions_or_unavailable(self):
        packages = nightly_verify._package_pins()
        for name in nightly_verify.PINNED_PACKAGES:
            self.assertIn(name, packages)
            value = packages[name]
            self.assertTrue(value == 'UNAVAILABLE' or re.match(r'^\d', str(value)),
                            'unexpected version value for %s: %r' % (name, value))

    def test_gpu_inventory_degrades_to_unavailable_without_nvidia_smi(self):
        original = nightly_verify.shutil.which
        nightly_verify.shutil.which = lambda name: None
        try:
            inventory = nightly_verify._nvidia_smi_inventory()
        finally:
            nightly_verify.shutil.which = original
        self.assertEqual(inventory['status'], 'UNAVAILABLE')
        self.assertEqual(inventory['devices'], [])
        self.assertIn('reason', inventory)

    def test_gpu_inventory_degrades_to_unavailable_on_nonzero_exit(self):
        original = nightly_verify.shutil.which
        original_run = nightly_verify.subprocess.run

        class _Proc:
            returncode = 9
            stdout = ''
            stderr = 'driver not loaded'

        nightly_verify.shutil.which = lambda name: 'C:/fake/nvidia-smi.exe'
        nightly_verify.subprocess.run = lambda *a, **k: _Proc()
        try:
            inventory = nightly_verify._nvidia_smi_inventory()
        finally:
            nightly_verify.shutil.which = original
            nightly_verify.subprocess.run = original_run
        self.assertEqual(inventory['status'], 'UNAVAILABLE')
        self.assertEqual(inventory['reason'], 'exit code 9')

    def test_gpu_inventory_parses_csv_when_the_tool_works(self):
        original = nightly_verify.shutil.which
        original_run = nightly_verify.subprocess.run

        class _Proc:
            returncode = 0
            stdout = ('name, driver_version, memory.total [MiB]\n'
                      'NVIDIA GeForce RTX 5070 Ti, 580.1, 16303 MiB\n')
            stderr = ''

        nightly_verify.shutil.which = lambda name: 'C:/fake/nvidia-smi.exe'
        nightly_verify.subprocess.run = lambda *a, **k: _Proc()
        try:
            inventory = nightly_verify._nvidia_smi_inventory()
        finally:
            nightly_verify.shutil.which = original
            nightly_verify.subprocess.run = original_run
        self.assertEqual(inventory['status'], 'OK')
        self.assertEqual(inventory['device_count'], 1)
        self.assertEqual(inventory['devices'][0]['name'], 'NVIDIA GeForce RTX 5070 Ti')

    def test_tool_probes_record_missing_tools_as_unavailable(self):
        original = nightly_verify.shutil.which
        nightly_verify.shutil.which = lambda name: None
        try:
            probes = nightly_verify._tool_probes()
        finally:
            nightly_verify.shutil.which = original
        for tool in ('nvidia-smi', 'rocminfo', 'clinfo', 'nvcc', 'ze_loader'):
            self.assertIn(tool, probes)
            self.assertEqual(probes[tool]['status'], 'UNAVAILABLE')
        self.assertEqual(probes['nvcc']['version_status'], 'UNAVAILABLE')


class TestResolveManifest(unittest.TestCase):
    """The manifest must be picked by newest-filename, never hardcoded."""

    def _repo_with(self, names):
        tmp = tempfile.mkdtemp()
        records = Path(tmp) / 'records'
        records.mkdir()
        for name in names:
            (records / name).write_text(json.dumps({'files': [], 'scope': 'x'}),
                                        encoding='utf-8')
        return tmp

    def test_newest_by_filename_sort_wins(self):
        tmp = self._repo_with([
            'ADAPTATION_SHA256_20261004.json',
            'ADAPTATION_SHA256_20261004_2148Z.json',
            'ADAPTATION_SHA256_20261005_110208Z.json',
            'ADAPTATION_SHA256_20261005_105913Z.json',
        ])
        try:
            path, info = nightly_verify.resolve_manifest(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, 'ADAPTATION_SHA256_20261005_110208Z.json')
        self.assertEqual(info['mode'], 'newest_by_filename_sort')
        self.assertEqual(info['status'], 'OK')
        self.assertEqual(info['candidate_count'], 4)
        self.assertEqual(info['candidates'][-1], 'ADAPTATION_SHA256_20261005_110208Z.json')

    def test_untimestamped_manifest_sorts_before_the_timestamped_same_day(self):
        tmp = self._repo_with(['ADAPTATION_SHA256_20261004.json',
                               'ADAPTATION_SHA256_20261004_2148Z.json'])
        try:
            path, _ = nightly_verify.resolve_manifest(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(path.name, 'ADAPTATION_SHA256_20261004_2148Z.json')

    def test_a_newer_manifest_appearing_later_is_picked_up(self):
        tmp = self._repo_with(['ADAPTATION_SHA256_20261004_2148Z.json'])
        try:
            first, _ = nightly_verify.resolve_manifest(tmp)
            self.assertEqual(first.name, 'ADAPTATION_SHA256_20261004_2148Z.json')
            newer = Path(tmp) / 'records' / 'ADAPTATION_SHA256_20261006_000000Z.json'
            newer.write_text('{}', encoding='utf-8')
            second, _ = nightly_verify.resolve_manifest(tmp)
            self.assertEqual(second.name, 'ADAPTATION_SHA256_20261006_000000Z.json')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_no_manifest_yields_unavailable_not_an_exception(self):
        tmp = self._repo_with(['SOME_OTHER_RECORD.json'])
        try:
            path, info = nightly_verify.resolve_manifest(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIsNone(path)
        self.assertEqual(info['status'], 'UNAVAILABLE')
        self.assertIn('no ADAPTATION_SHA256_*.json found', info['reason'])

    def test_missing_records_directory_yields_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, info = nightly_verify.resolve_manifest(tmp)
        self.assertIsNone(path)
        self.assertEqual(info['status'], 'UNAVAILABLE')
        self.assertIn('records directory not found', info['reason'])

    def test_override_absolute_path_is_honoured(self):
        # Both exist; the override must beat the newest-by-filename default.
        tmp = self._repo_with(['ADAPTATION_SHA256_20261004.json',
                               'ADAPTATION_SHA256_20261005_110208Z.json'])
        try:
            older = Path(tmp) / 'records' / 'ADAPTATION_SHA256_20261004.json'
            default_path, _ = nightly_verify.resolve_manifest(tmp)
            self.assertEqual(default_path.name, 'ADAPTATION_SHA256_20261005_110208Z.json')
            path, info = nightly_verify.resolve_manifest(tmp, str(older))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(path.name, 'ADAPTATION_SHA256_20261004.json')
        self.assertEqual(info['mode'], 'override')
        self.assertEqual(info['status'], 'OK')

    def test_override_relative_path_resolves_against_repo_root(self):
        tmp = self._repo_with(['ADAPTATION_SHA256_20261005_110208Z.json'])
        try:
            path, info = nightly_verify.resolve_manifest(
                tmp, 'records/ADAPTATION_SHA256_20261005_110208Z.json')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, 'ADAPTATION_SHA256_20261005_110208Z.json')
        self.assertEqual(info['mode'], 'override')

    def test_override_pointing_nowhere_is_unavailable_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, info = nightly_verify.resolve_manifest(
                tmp, str(Path(tmp) / 'nope.json'))
        self.assertIsNone(path)
        self.assertEqual(info['status'], 'UNAVAILABLE')
        self.assertIn('--manifest path does not exist', info['reason'])

    def test_resolution_never_hardcodes_a_stamp_in_the_module_source(self):
        source = NIGHTLY_SCRIPT.read_text(encoding='utf-8')
        self.assertNotIn('ADAPTATION_SHA256_20261004_2148Z.json', source)
        self.assertIn(nightly_verify.MANIFEST_GLOB, source)
        self.assertEqual(nightly_verify.MANIFEST_GLOB, 'ADAPTATION_SHA256_*.json')


class TestBuildChecks(unittest.TestCase):
    def test_four_checks_are_defined_with_unique_names(self):
        checks = nightly_verify.build_checks(REPO_ROOT, PY)
        self.assertEqual(len(checks), 4)
        names = [c['name'] for c in checks]
        self.assertEqual(len(set(names)), 4)
        self.assertIn('artifact_manifest_integrity', names)

    def test_every_python_command_passes_dash_b_and_never_uses_a_shell(self):
        for check in nightly_verify.build_checks(REPO_ROOT, PY):
            if not check['cmd']:
                continue  # a skipped check has no command to inspect
            with self.subTest(check=check['name']):
                self.assertEqual(check['cmd'][0], PY)
                self.assertIn('-B', check['cmd'])
                self.assertIsInstance(check['cmd'], list)
                for part in check['cmd']:
                    self.assertIsInstance(part, str)

    def test_commands_reference_paths_inside_the_repo_root(self):
        for check in nightly_verify.build_checks(REPO_ROOT, PY):
            if not check['cmd']:
                continue
            with self.subTest(check=check['name']):
                joined = ' '.join(check['cmd'])
                self.assertIn(str(REPO_ROOT), joined.replace('/', os.sep))

    def test_manifest_check_uses_the_resolved_manifest_not_a_fixed_name(self):
        checks = nightly_verify.build_checks(REPO_ROOT, PY)
        check = next(c for c in checks if c['name'] == 'artifact_manifest_integrity')
        resolved, info = nightly_verify.resolve_manifest(REPO_ROOT)
        if resolved is None:
            self.assertEqual(check['cmd'], [])
            self.assertIn('skip_reason', check)
        else:
            self.assertEqual(check['cmd'][-1], str(resolved))
            self.assertEqual(info['resolved_name'], resolved.name)
        self.assertEqual(check['manifest_resolution'], info)

    def test_manifest_override_flows_into_the_command(self):
        resolved, _ = nightly_verify.resolve_manifest(REPO_ROOT)
        if resolved is None:
            self.skipTest('no manifest present on this host to override with')
        checks = nightly_verify.build_checks(REPO_ROOT, PY, manifest=str(resolved))
        check = next(c for c in checks if c['name'] == 'artifact_manifest_integrity')
        self.assertEqual(check['cmd'][-1], str(resolved))
        self.assertEqual(check['manifest_resolution']['mode'], 'override')

    def test_unresolvable_manifest_produces_a_skip_reason_and_empty_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            checks = nightly_verify.build_checks(tmp, PY)
        check = next(c for c in checks if c['name'] == 'artifact_manifest_integrity')
        self.assertEqual(check['cmd'], [])
        self.assertIn('records directory not found', check['skip_reason'])
        # The other three checks must still be fully specified.
        for other in checks:
            if other['name'] != 'artifact_manifest_integrity':
                self.assertTrue(other['cmd'])
                self.assertNotIn('skip_reason', other)

    def test_repo_root_is_derived_from_the_script_location(self):
        self.assertEqual(nightly_verify.repo_root_default(), REPO_ROOT)


class TestCliDryRun(unittest.TestCase):
    def _run_cli(self, args, cwd=None):
        return subprocess.run([PY, '-B', str(NIGHTLY_SCRIPT)] + args,
                              capture_output=True, text=True, encoding='utf-8',
                              errors='replace', cwd=cwd or str(REPO_ROOT),
                              timeout=300, shell=False)

    def test_dry_run_exits_zero_and_lists_every_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self._run_cli(['--dry-run', '--out-dir', tmp])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('DRY RUN', proc.stdout)
            for name in ('j_link_unittest_suite', 'cad_unittest_suite',
                         'j_link_planner_mixed', 'artifact_manifest_integrity'):
                self.assertIn(name, proc.stdout)
            self.assertIn('NIGHTLY VERDICT: DRY_RUN', proc.stdout)

    def test_dry_run_writes_nothing_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'nightly'
            before = set(Path(tmp).rglob('*'))
            proc = self._run_cli(['--dry-run', '--out-dir', str(out_dir)])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            after = set(Path(tmp).rglob('*'))
        self.assertEqual(before, after)
        self.assertEqual(after, set())
        self.assertFalse(out_dir.exists())

    def test_dry_run_does_not_touch_the_real_records_tree(self):
        real_nightly = REPO_ROOT / 'records' / 'nightly'
        before = sorted(p.name for p in real_nightly.iterdir()) if real_nightly.is_dir() else []
        proc = self._run_cli(['--dry-run'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        after = sorted(p.name for p in real_nightly.iterdir()) if real_nightly.is_dir() else []
        self.assertEqual(before, after)

    def test_help_exits_zero(self):
        proc = self._run_cli(['--help'])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('--dry-run', proc.stdout)
        self.assertIn('--out-dir', proc.stdout)
        self.assertIn('--manifest', proc.stdout)

    def test_dry_run_reports_how_the_manifest_was_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self._run_cli(['--dry-run', '--out-dir', tmp])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('manifest  : mode=', proc.stdout)
        resolved, _ = nightly_verify.resolve_manifest(REPO_ROOT)
        if resolved is not None:
            self.assertIn('status=OK', proc.stdout)
            self.assertIn(resolved.name, proc.stdout)
        else:
            self.assertIn('status=UNAVAILABLE', proc.stdout)
            self.assertIn('<skipped:', proc.stdout)

    def test_dry_run_honours_the_manifest_override(self):
        resolved, _ = nightly_verify.resolve_manifest(REPO_ROOT)
        if resolved is None:
            self.skipTest('no manifest present on this host')
        with tempfile.TemporaryDirectory() as tmp:
            proc = self._run_cli(['--dry-run', '--out-dir', tmp,
                                  '--manifest', str(resolved)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('mode=override', proc.stdout)
        self.assertIn(resolved.name, proc.stdout)


class TestCliSyntheticFullRun(unittest.TestCase):
    """Drive the real CLI against an empty fake repo root.

    None of the four real checks can run there, so this proves exit-code
    propagation and on-disk receipt writing without touching the real suite.
    """

    def test_broken_repo_root_fails_loud_and_still_writes_a_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_repo = Path(tmp) / 'repo'
            fake_repo.mkdir()
            out_dir = Path(tmp) / 'receipts'
            proc = subprocess.run(
                [PY, '-B', str(NIGHTLY_SCRIPT), '--repo-root', str(fake_repo),
                 '--out-dir', str(out_dir), '--timeout', '120'],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                cwd=str(REPO_ROOT), timeout=600, shell=False)
            self.assertIn(proc.returncode, (1, 2), proc.stdout + proc.stderr)
            self.assertIn('NIGHTLY VERDICT:', proc.stdout)
            self.assertIn('receipt:', proc.stdout)

            stamps = sorted(p.name for p in out_dir.iterdir())
            self.assertEqual(len(stamps), 1)
            self.assertRegex(stamps[0], STAMP_RE)
            receipt_dir = out_dir / stamps[0]
            receipt = json.loads((receipt_dir / 'receipt.json').read_text(encoding='utf-8'))
            summary_text = (receipt_dir / 'SUMMARY.md').read_text(encoding='utf-8')
            self.assertIn('## Verdict', summary_text)

        self.assertEqual(receipt['schema_version'], nightly_verify.SCHEMA_VERSION)
        self.assertEqual(len(receipt['checks']), 4)
        self.assertEqual(receipt['exit_code'], proc.returncode)
        self.assertIn(receipt['overall_verdict'], ('PASS', 'FAIL', 'INCOMPLETE', 'NO_CHECKS'))
        for check in receipt['checks']:
            # The manifest check may be skipped outright when the fake repo has no
            # records/ directory, in which case it legitimately has no command.
            if check['command']:
                self.assertIn('-B', check['command'])
            else:
                self.assertEqual(check['status'], 'UNAVAILABLE')
                self.assertTrue(check['error'])
            self.assertFalse(check['passed'])

    def test_missing_interpreter_yields_unavailable_and_exit_two(self):
        """A check command that cannot launch is recorded, never crashes the job."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'receipts'
            proc = subprocess.run(
                [PY, '-B', str(NIGHTLY_SCRIPT),
                 '--python-exe', str(Path(tmp) / 'no-such-python.exe'),
                 '--out-dir', str(out_dir), '--timeout', '60'],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                cwd=str(REPO_ROOT), timeout=600, shell=False)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertIn('NIGHTLY VERDICT: INCOMPLETE', proc.stdout)
            stamp_dirs = sorted(out_dir.iterdir())
            self.assertEqual(len(stamp_dirs), 1)
            receipt = json.loads(
                (stamp_dirs[0] / 'receipt.json').read_text(encoding='utf-8'))
            self.assertIn('## Verdict: **INCOMPLETE** (exit 2)',
                          (stamp_dirs[0] / 'SUMMARY.md').read_text(encoding='utf-8'))

        self.assertEqual([c['status'] for c in receipt['checks']], ['UNAVAILABLE'] * 4)
        self.assertEqual(receipt['overall_verdict'], 'INCOMPLETE')
        self.assertEqual(receipt['exit_code'], 2)
        self.assertEqual(receipt['counts']['pass'], 0)
        self.assertEqual(receipt['counts']['unavailable'], 4)
        for check in receipt['checks']:
            self.assertIsNone(check['returncode'])
            self.assertIn('FileNotFoundError', check['error'])

    def test_bad_manifest_override_is_recorded_unavailable_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_repo = Path(tmp) / 'repo'
            fake_repo.mkdir()
            out_dir = Path(tmp) / 'receipts'
            bogus = Path(tmp) / 'does-not-exist.json'
            proc = subprocess.run(
                [PY, '-B', str(NIGHTLY_SCRIPT), '--repo-root', str(fake_repo),
                 '--out-dir', str(out_dir), '--manifest', str(bogus), '--timeout', '60'],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                cwd=str(REPO_ROOT), timeout=600, shell=False)
            self.assertIn(proc.returncode, (1, 2), proc.stdout + proc.stderr)
            stamp_dirs = sorted(out_dir.iterdir())
            self.assertEqual(len(stamp_dirs), 1)
            receipt = json.loads(
                (stamp_dirs[0] / 'receipt.json').read_text(encoding='utf-8'))
            summary = (stamp_dirs[0] / 'SUMMARY.md').read_text(encoding='utf-8')

        check = next(c for c in receipt['checks']
                     if c['name'] == 'artifact_manifest_integrity')
        self.assertEqual(check['status'], 'UNAVAILABLE')
        self.assertFalse(check['passed'])
        self.assertIsNone(check['returncode'])
        self.assertIn('--manifest path does not exist', check['error'])
        self.assertEqual(check['manifest_resolution']['mode'], 'override')
        self.assertIn('## Artifact manifest', summary)
        self.assertIn('UNAVAILABLE', summary)
        # The receipt must name what it tried to verify, for auditability.
        self.assertTrue(any('manifest resolution' in note for note in receipt['notes']))

    def test_out_dir_override_is_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / 'custom' / 'receipts'
            fake_repo = Path(tmp) / 'repo'
            fake_repo.mkdir()
            proc = subprocess.run(
                [PY, '-B', str(NIGHTLY_SCRIPT), '--repo-root', str(fake_repo),
                 '--out-dir', str(out_dir), '--timeout', '60'],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                cwd=str(REPO_ROOT), timeout=600, shell=False)
            self.assertTrue(out_dir.is_dir(), proc.stdout + proc.stderr)
        self.assertIn('NIGHTLY VERDICT:', proc.stdout)


class TestHardRules(unittest.TestCase):
    """Guards on the project's non-negotiables for this script."""

    def test_module_source_never_uses_shell_true(self):
        source = NIGHTLY_SCRIPT.read_text(encoding='utf-8')
        self.assertNotIn('shell=True', source)

    def test_module_source_imports_only_the_standard_library(self):
        source = NIGHTLY_SCRIPT.read_text(encoding='utf-8')
        imported = set(re.findall(r'^(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)',
                                  source, re.MULTILINE))
        imported |= {'importlib'}  # imported lazily inside _package_pins
        stdlib = {'argparse', 'csv', 'io', 'json', 'os', 'platform', 're', 'shutil',
                  'subprocess', 'sys', 'time', 'datetime', 'pathlib', '__future__',
                  'importlib'}
        self.assertEqual(imported - stdlib, set(),
                         'non-stdlib import found: %s' % sorted(imported - stdlib))

    def test_no_pycache_written_next_to_the_script_by_a_dry_run(self):
        cache = SCRIPTS_DIR / '__pycache__'
        before = sorted(p.name for p in cache.iterdir()) if cache.is_dir() else []
        subprocess.run([PY, '-B', str(NIGHTLY_SCRIPT), '--dry-run'],
                       capture_output=True, text=True, cwd=str(REPO_ROOT),
                       timeout=120, shell=False)
        after = sorted(p.name for p in cache.iterdir()) if cache.is_dir() else []
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
