"""Unit tests for device_inventory. Imports the actual module."""
import unittest
from datetime import datetime, timedelta, timezone

import device_inventory
from device_inventory import (
    _normalize_pci,
    _parse_bytes_value,
    _parse_mib_value,
    _parse_utc,
    get_admission_snapshot,
    normalize_inventory,
)

NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
MAX_AGE = 5
HEADER = 'pci.bus_id,name,memory.total,memory.free,memory.used,uuid\n'


def _nv(body, when=None, **extra):
    sample = {
        'vendor': 'nvidia',
        'tool': 'nvidia-smi',
        'tool_version': '550.0',
        'sampled_at_utc': (when or NOW).isoformat(),
        'exit_code': 0,
        'format': 'csv',
        'stdout': HEADER + body,
        'memory_kind': 'DEDICATED',
    }
    sample.update(extra)
    return sample


class TestNormalizeInventory(unittest.TestCase):
    def test_nvidia_csv_valid(self):
        csv_out = HEADER + '0000:01:00.0,RTX 5070 Ti,16384 MiB,12000 MiB,4384 MiB,GPU-abc123\n'
        sample = {
            'vendor': 'nvidia', 'tool': 'nvidia-smi', 'tool_version': '550.0',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'csv',
            'stdout': csv_out, 'memory_kind': 'DEDICATED',
        }
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(result['devices']), 1)
        d = result['devices'][0]
        self.assertEqual(d['physical_id'], '0000:01:00.0')
        self.assertEqual(d['vendor_key'], 'nvidia')
        self.assertEqual(d['memory_kind'], 'DEDICATED')
        self.assertEqual(d['advertised_total_bytes'], 16384 * 1048576)
        self.assertEqual(d['observed_free_bytes'], 12000 * 1048576)
        self.assertEqual(d['freshness_status'], 'FRESH')
        self.assertIn('nv-uuid:GPU-abc123', d['aliases'])
        self.assertEqual(result['conflicts'], [])
        self.assertEqual(result['refusals'], [])

    def test_nvidia_na_memory(self):
        sample = _nv('0000:02:00.0,Quadro,N/A,N/A,N/A,GPU-def\n')
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        d = result['devices'][0]
        self.assertIsNone(d['advertised_total_bytes'])
        self.assertIsNone(d['observed_free_bytes'])

    def test_stale_sample(self):
        old_ts = datetime(2026, 10, 4, 11, 59, 50, tzinfo=timezone.utc)
        sample = _nv('0000:01:00.0,X,1000 MiB,500 MiB,500 MiB,U\n', when=old_ts)
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(result['devices'][0]['freshness_status'], 'STALE')

    def test_amd_json_dedicated(self):
        json_out = '[{"pci_bdf":"0000:03:00.0","vendor_name":"AMD","device_name":"RX 7900","dedicated_memory_bytes":17179869184}]'
        sample = {
            'vendor': 'amd', 'tool': 'amd-smi', 'tool_version': '1.0',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'stdout': json_out, 'schema_selector': 'amd-smi-v1',
        }
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        d = result['devices'][0]
        self.assertEqual(d['vendor_key'], 'amd')
        self.assertEqual(d['memory_kind'], 'DEDICATED')
        self.assertEqual(d['advertised_total_bytes'], 17179869184)
        self.assertIsNone(d['observed_free_bytes'])

    def test_amd_shared_not_vram(self):
        json_out = '[{"pci_bdf":"0000:04:00.0","vendor_name":"AMD","device_name":"iGPU","shared_memory_bytes":8589934592}]'
        sample = {
            'vendor': 'amd', 'tool': 'amd-smi', 'tool_version': '1.0',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'stdout': json_out, 'schema_selector': 'amd-smi-v1',
        }
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(result['devices'][0]['memory_kind'], 'SHARED_HOST')

    def test_amd_unsupported_schema_rejected(self):
        json_out = '[{"pci_bdf":"0000:05:00.0","vendor_name":"AMD","device_name":"X","dedicated_memory_bytes":1}]'
        sample = {
            'vendor': 'amd', 'tool': 'amd-smi', 'tool_version': '1.0',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'stdout': json_out, 'schema_selector': 'amd-smi-v99',
        }
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(result['devices']), 0)
        self.assertTrue(any('unsupported schema' in c.lower() for c in result['conflicts']))

    def test_intel_json_valid(self):
        json_out = '[{"pci_bdf":"0000:06:00.0","device_name":"Arc A770","memory_size":17179869184,"driver_version":"31.0"}]'
        sample = {
            'vendor': 'intel', 'tool': 'xpu-smi', 'tool_version': '1.0',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'stdout': json_out, 'schema_selector': 'xpu-smi-v1',
            'memory_kind': 'DEDICATED',
        }
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        d = result['devices'][0]
        self.assertEqual(d['vendor_key'], 'intel')
        self.assertEqual(d['memory_kind'], 'DEDICATED')
        self.assertEqual(d['advertised_total_bytes'], 17179869184)

    def test_missing_pci_unqualified(self):
        sample = _nv(',NoName,1000 MiB,500 MiB,500 MiB,U\n')
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(result['devices']), 1)
        self.assertIsNone(result['devices'][0]['physical_id'])

    def test_vendor_contradiction_conflict(self):
        s1 = _nv('0000:07:00.0,NV,1000 MiB,500 MiB,500 MiB,U1\n')
        json2 = '[{"pci_bdf":"0000:07:00.0","vendor_name":"AMD","device_name":"AMD","dedicated_memory_bytes":1048576000}]'
        s2 = {
            'vendor': 'amd', 'tool': 'amd-smi', 'tool_version': '1',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'stdout': json2, 'schema_selector': 'amd-smi-v1',
        }
        result = normalize_inventory([s1, s2], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(result['devices']), 0)
        self.assertTrue(any('contradiction' in c.lower() for c in result['conflicts']))

    def test_nonzero_exit_refusal(self):
        sample = {
            'vendor': 'nvidia', 'tool': 'nvidia-smi', 'tool_version': '1',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 1, 'format': 'csv', 'stdout': '',
        }
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(result['refusals']), 1)
        self.assertEqual(result['refusals'][0]['reason'], 'nonzero_exit')

    def test_invalid_bool_memory(self):
        sample = _nv('0000:08:00.0,X,true,500 MiB,500 MiB,U\n')
        result = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertIsNone(result['devices'][0]['advertised_total_bytes'])


class TestAdmissionSnapshot(unittest.TestCase):
    def setUp(self):
        csv_out = HEADER + (
            '0000:01:00.0,A,16384 MiB,12000 MiB,4384 MiB,U1\n'
            '0000:02:00.0,B,8192 MiB,0 MiB,8192 MiB,U2\n'
        )
        self.sample = {
            'vendor': 'nvidia', 'tool': 'nvidia-smi', 'tool_version': '1',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'csv',
            'stdout': csv_out, 'memory_kind': 'DEDICATED',
        }
        self.inv = normalize_inventory([self.sample], now_utc=NOW, max_age_seconds=MAX_AGE)

    def test_eligible_and_refused(self):
        snap = get_admission_snapshot(self.inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(snap['eligible']), 1)
        self.assertEqual(snap['eligible'][0]['physical_id'], '0000:01:00.0')
        self.assertEqual(len(snap['refused']), 1)
        self.assertEqual(snap['refused'][0]['reason'], 'no_free_capacity')

    def test_shared_refused_for_dedicated(self):
        json_out = '[{"pci_bdf":"0000:03:00.0","vendor_name":"AMD","device_name":"iGPU","shared_memory_bytes":8589934592}]'
        s = {
            'vendor': 'amd', 'tool': 'amd-smi', 'tool_version': '1',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'stdout': json_out, 'schema_selector': 'amd-smi-v1',
        }
        inv = normalize_inventory([s], now_utc=NOW, max_age_seconds=MAX_AGE)
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(snap['eligible']), 0)
        self.assertEqual(snap['refused'][0]['reason'], 'not_dedicated')

    def test_unknown_free_not_allocatable(self):
        s = _nv('0000:04:00.0,X,1000 MiB,N/A,500 MiB,U\n')
        inv = normalize_inventory([s], now_utc=NOW, max_age_seconds=MAX_AGE)
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(snap['eligible']), 0)
        self.assertEqual(snap['refused'][0]['reason'], 'unknown_free')


class TestAdmissionIdentityDefects(unittest.TestCase):
    def test_future_timestamp_not_admitted(self):
        sample = _nv(
            '0000:01:00.0,A,16384 MiB,12000 MiB,4384 MiB,U\n',
            when=NOW + timedelta(seconds=30),
        )
        inv = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(inv['devices'][0]['freshness_status'], 'STALE')
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(snap['eligible'], [])
        self.assertEqual(snap['refused'][0]['reason'], 'future_timestamp')

    def test_admission_rechecks_stale_at_later_now(self):
        sample = _nv('0000:01:00.0,A,16384 MiB,12000 MiB,4384 MiB,U\n')
        inv = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        fresh = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(fresh['eligible']), 1)
        later = get_admission_snapshot(
            inv, now_utc=NOW + timedelta(seconds=30), max_age_seconds=MAX_AGE,
        )
        self.assertEqual(later['eligible'], [])
        self.assertEqual(later['refused'][0]['reason'], 'stale')

    def test_missing_physical_id_refused(self):
        inv = normalize_inventory(
            [_nv(',NoName,1000 MiB,500 MiB,500 MiB,U\n')],
            now_utc=NOW, max_age_seconds=MAX_AGE,
        )
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(snap['eligible'], [])
        self.assertEqual(snap['refused'][0]['reason'], 'missing_physical_id')

    def test_8hex_nvidia_canonical_4hex_and_dedup(self):
        early = _nv(
            '00000000:01:00.0,NV Eight,1000 MiB,100 MiB,900 MiB,U-8\n',
            when=NOW - timedelta(seconds=3),
        )
        later = _nv(
            '0000:01:00.0,NV Four,1000 MiB,200 MiB,800 MiB,U-4\n',
            when=NOW - timedelta(seconds=1),
        )
        inv = normalize_inventory([early, later], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(inv['devices']), 1)
        d = inv['devices'][0]
        self.assertEqual(d['physical_id'], '0000:01:00.0')
        self.assertEqual(d['observed_free_bytes'], 200 * 1048576)
        self.assertIn('nv-uuid:U-8', d['aliases'])
        self.assertIn('nv-uuid:U-4', d['aliases'])
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual([x['physical_id'] for x in snap['eligible']], ['0000:01:00.0'])

    def test_8hex_nv_and_4hex_amd_same_identity_no_resurrection(self):
        nv = _nv('00000000:09:00.0,NV,1000 MiB,500 MiB,500 MiB,U\n')
        amd = {
            'vendor': 'amd', 'tool': 'amd-smi', 'tool_version': '1',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'schema_selector': 'amd-smi-v1',
            'stdout': '[{"pci_bdf":"0000:09:00.0","device_name":"AMD","dedicated_memory_bytes":1048576000}]',
        }
        again = _nv('0000:09:00.0,NV again,1000 MiB,500 MiB,500 MiB,U2\n0000:0a:00.0,Survivor,1000 MiB,500 MiB,500 MiB,Us\n')
        inv = normalize_inventory([nv, amd, again], now_utc=NOW, max_age_seconds=MAX_AGE)
        ids = [d['physical_id'] for d in inv['devices']]
        self.assertNotIn('0000:09:00.0', ids)
        self.assertIn('0000:0a:00.0', ids)
        self.assertTrue(any('contradiction' in c.lower() for c in inv['conflicts']))

    def test_segment_above_ffff_and_device_32_rejected(self):
        self.assertIsNone(_normalize_pci('00010000:01:00.0'))
        self.assertIsNone(_normalize_pci('0000:01:20.0'))
        self.assertIsNone(_normalize_pci('0000:01:00.8'))
        self.assertIsNone(_normalize_pci('01:00.0'))
        self.assertEqual(_normalize_pci('0000000A:01:1F.7'), '000a:01:1f.7')
        sample = _nv('00010000:01:00.0,BadSeg,1000 MiB,500 MiB,500 MiB,U\n0000:01:20.0,BadDev,1000 MiB,500 MiB,500 MiB,U2\n')
        inv = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertTrue(all(d['physical_id'] is None for d in inv['devices']))
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(snap['eligible'], [])

    def test_naive_timestamp_and_naive_now_refused(self):
        self.assertIsNone(_parse_utc('2026-10-04T12:00:00'))
        naive_now = datetime(2026, 10, 4, 12, 0, 0)
        sample = _nv('0000:01:00.0,A,1000 MiB,500 MiB,500 MiB,U\n')
        with self.assertRaises(ValueError):
            normalize_inventory([sample], now_utc=naive_now, max_age_seconds=MAX_AGE)
        with self.assertRaises(ValueError):
            get_admission_snapshot({'devices': []}, now_utc=naive_now, max_age_seconds=True)
        naive_sample = _nv(
            '0000:01:00.0,A,1000 MiB,500 MiB,500 MiB,U\n',
            sampled_at_utc='2026-10-04T12:00:00',
        )
        inv = normalize_inventory([naive_sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(snap['eligible'], [])
        self.assertEqual(snap['refused'][0]['reason'], 'unknown_timestamp')

    def test_kind_and_total_contradiction_tombstone(self):
        a = _nv('0000:0e:00.0,A,1000 MiB,500 MiB,500 MiB,U1\n', memory_kind='DEDICATED')
        b = _nv('0000:0e:00.0,A,2000 MiB,500 MiB,1500 MiB,U2\n', memory_kind='SHARED_HOST')
        c = _nv('0000:0e:00.0,A,1000 MiB,500 MiB,500 MiB,U3\n', memory_kind='DEDICATED')
        inv = normalize_inventory([a, b, c], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(inv['devices'], [])
        self.assertTrue(inv['conflicts'])

    def test_same_name_does_not_dedup(self):
        sample = _nv(
            '0000:11:00.0,Same,1000 MiB,500 MiB,500 MiB,U1\n'
            '0000:12:00.0,Same,1000 MiB,400 MiB,600 MiB,U2\n'
        )
        inv = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(inv['devices']), 2)

    def test_unknown_classification_fail_closed(self):
        missing = _nv('0000:13:00.0,A,1000 MiB,500 MiB,500 MiB,U\n', memory_kind=None)
        invalid = _nv('0000:14:00.0,A,1000 MiB,500 MiB,500 MiB,U\n', memory_kind='HBM')
        intel = {
            'vendor': 'intel', 'tool': 'xpu-smi', 'tool_version': '1',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'schema_selector': 'xpu-smi-v1',
            'stdout': '[{"pci_bdf":"0000:15:00.0","device_name":"Arc","memory_size":1024}]',
        }
        intel_bad = dict(intel, memory_kind='shared', stdout='[{"pci_bdf":"0000:16:00.0","device_name":"Arc","memory_size":1024}]')
        inv = normalize_inventory([missing, invalid, intel, intel_bad], now_utc=NOW, max_age_seconds=MAX_AGE)
        kinds = {d['physical_id']: d['memory_kind'] for d in inv['devices']}
        self.assertEqual(kinds['0000:13:00.0'], 'UNKNOWN')
        self.assertEqual(kinds['0000:14:00.0'], 'UNKNOWN')
        self.assertEqual(kinds['0000:15:00.0'], 'UNKNOWN')
        self.assertEqual(kinds['0000:16:00.0'], 'UNKNOWN')
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(snap['eligible'], [])
        self.assertTrue(all(r['reason'] == 'not_dedicated' for r in snap['refused']))

    def test_nonintegral_floats_rejected(self):
        self.assertIsNone(_parse_bytes_value(1.5))
        self.assertIsNone(_parse_bytes_value(float('nan')))
        self.assertIsNone(_parse_bytes_value(float('inf')))
        self.assertIsNone(_parse_bytes_value(True))
        self.assertIsNone(_parse_bytes_value(-4))
        self.assertIsNone(_parse_mib_value('1.5'))
        self.assertIsNone(_parse_mib_value(True))
        self.assertEqual(_parse_bytes_value(2.0), 2)
        amd = {
            'vendor': 'amd', 'tool': 'amd-smi', 'tool_version': '1',
            'sampled_at_utc': NOW.isoformat(), 'exit_code': 0, 'format': 'json',
            'schema_selector': 'amd-smi-v1',
            'stdout': '[{"pci_bdf":"0000:0b:00.0","device_name":"F","dedicated_memory_bytes":1.5}]',
        }
        inv = normalize_inventory([amd], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(inv['devices'][0]['memory_kind'], 'DEDICATED')
        self.assertIsNone(inv['devices'][0]['advertised_total_bytes'])
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(snap['refused'][0]['reason'], 'invalid_total')

    def test_quoted_csv_name_and_declared_header(self):
        sample = _nv('0000:0c:00.0,"RTX 5070 Ti, FE",16384 MiB,1000 MiB,15384 MiB,GPU-q\n')
        inv = normalize_inventory([sample], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(inv['devices'][0]['physical_id'], '0000:0c:00.0')
        self.assertIn('nv-name:RTX 5070 Ti, FE', inv['devices'][0]['aliases'])
        snap = get_admission_snapshot(inv, now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(len(snap['eligible']), 1)
        headless = _nv('0000:0c:00.0,RTX,16384 MiB,1000 MiB,1 MiB,U\n')
        headless['stdout'] = '0000:0c:00.0,RTX,16384 MiB,1000 MiB,1 MiB,U\n'
        bare = normalize_inventory([headless], now_utc=NOW, max_age_seconds=MAX_AGE)
        self.assertEqual(bare['devices'], [])


if __name__ == '__main__':
    unittest.main()

