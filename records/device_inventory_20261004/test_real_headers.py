import csv
import io
import json
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone
from device_inventory import normalize_inventory, get_admission_snapshot

ROOT = Path(__file__).resolve().parent
NOW = datetime(2026, 10, 4, 12, 12, 13, 500000, tzinfo=timezone.utc)

class CapturedNvidiaTests(unittest.TestCase):
    def captured(self):
        return json.loads((ROOT / 'nvidia_capture.json').read_text())

    def test_actual_captured_unit_headers_and_identity(self):
        sample = self.captured()
        inventory = normalize_inventory([sample], now_utc=NOW)
        device = inventory['devices'][0]
        self.assertEqual(device['physical_id'], '0000:01:00.0')
        self.assertEqual(device['advertised_total_bytes'], 16303 * 1048576)
        self.assertEqual(device['observed_free_bytes'], 14682 * 1048576)
        self.assertEqual(device['freshness_status'], 'FRESH')
        self.assertEqual(len(get_admission_snapshot(inventory, now_utc=NOW)['eligible']), 1)

    def test_arbitrary_total_unit_is_not_stripped(self):
        sample = self.captured()
        sample['stdout'] = sample['stdout'].replace('memory.total [MiB]', 'memory.total [GiB]')
        inventory = normalize_inventory([sample], now_utc=NOW)
        self.assertIsNone(inventory['devices'][0]['advertised_total_bytes'])
        self.assertEqual(get_admission_snapshot(inventory, now_utc=NOW)['refused'][0]['reason'], 'invalid_total')

    def test_free_unknown_unit_is_not_stripped(self):
        sample = self.captured()
        sample['stdout'] = sample['stdout'].replace('memory.free [MiB]', 'memory.free [bytes]')
        inventory = normalize_inventory([sample], now_utc=NOW)
        self.assertEqual(get_admission_snapshot(inventory, now_utc=NOW)['refused'][0]['reason'], 'unknown_free')

    def test_duplicate_canonical_header_refused(self):
        sample = self.captured()
        rows = list(csv.reader(io.StringIO(sample['stdout'])))
        rows[0].append('memory.total')
        rows[1].append('99999')
        stream = io.StringIO()
        csv.writer(stream).writerows(rows)
        sample['stdout'] = stream.getvalue()
        self.assertEqual(normalize_inventory([sample], now_utc=NOW)['devices'], [])

    def test_live_fixture_age_is_rechecked(self):
        inventory = normalize_inventory([self.captured()], now_utc=NOW)
        snapshot = get_admission_snapshot(inventory, now_utc=NOW + timedelta(seconds=6))
        self.assertEqual(snapshot['eligible'], [])
        self.assertEqual(snapshot['refused'][0]['reason'], 'stale')

if __name__ == '__main__':
    unittest.main()
