"""Pure captured-output adapter; no GPU imports or subprocess at import.

NVIDIA MiB CSV headers are live-qualified on this host. AMD/Intel named JSON
schemas are synthetic fixture contracts, not verified native CLI schemas; their
free capacity remains unknown and cannot enter dedicated-memory admission.
"""
import csv
import io
import json
import math
import re
from datetime import datetime, timezone

PCI_RE = re.compile(
    r'^([0-9a-fA-F]{4}|[0-9a-fA-F]{8}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])$'
)
_KINDS = ('DEDICATED', 'SHARED_HOST', 'UNKNOWN')
_VENDOR_TOOL = {'nvidia': 'nvidia-smi', 'amd': 'amd-smi', 'intel': 'xpu-smi'}
MIB_RE = re.compile(r'^(\d+)\s*[Mm][Ii][Bb]$')
GIB_RE = re.compile(r'^(\d+)\s*[Gg][Ii][Bb]$')

SUPPORTED_TOOLS = {
    'nvidia-smi': {'csv'},
    'amd-smi': {'json'},
    'xpu-smi': {'json'},
}


def _parse_utc(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return None
    return dt.astimezone(timezone.utc)


def _require_clock(now_utc, max_age_seconds):
    if (
        not isinstance(now_utc, datetime)
        or now_utc.tzinfo is None
        or now_utc.tzinfo.utcoffset(now_utc) is None
    ):
        raise ValueError('now_utc must be an aware datetime')
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, (int, float)):
        raise ValueError('max_age_seconds must be a finite positive number')
    if not math.isfinite(float(max_age_seconds)) or max_age_seconds <= 0:
        raise ValueError('max_age_seconds must be a finite positive number')
    return now_utc.astimezone(timezone.utc), float(max_age_seconds)


def _explicit_kind(sample):
    kind = sample.get('memory_kind') if isinstance(sample, dict) else None
    return kind if kind in _KINDS else 'UNKNOWN'


def _normalize_pci(raw):
    if not isinstance(raw, str):
        return None
    m = PCI_RE.match(raw.strip())
    if not m:
        return None
    dom_s, bus, dev_s, fn = m.groups()
    dom = int(dom_s, 16)
    dev = int(dev_s, 16)
    if dom > 0xFFFF or dev > 0x1F:
        return None
    return f"{dom:04x}:{bus.lower()}:{dev_s.lower()}.{fn}"


def _finite_whole(raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    if isinstance(raw, float) and (not math.isfinite(raw) or not raw.is_integer()):
        return None
    if raw < 0:
        return None
    return int(raw)


def _stamp(sample, now_utc, max_age):
    ts = _parse_utc(sample.get('sampled_at_utc'))
    fresh = 'STALE'
    if ts is not None and 0 <= (now_utc - ts).total_seconds() <= max_age:
        fresh = 'FRESH'
    return ts, fresh


def _parse_mib_value(raw):
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        if raw < 0:
            return None
        return raw * 1048576
    whole = _finite_whole(raw)
    if isinstance(raw, float) or isinstance(raw, int):
        return None if whole is None else whole * 1048576
    if isinstance(raw, str):
        s = raw.strip()
        if s.upper() == 'N/A' or s == '':
            return None
        m = MIB_RE.match(s)
        if m:
            v = int(m.group(1))
            return v * 1048576 if v >= 0 else None
        m = GIB_RE.match(s)
        if m:
            v = int(m.group(1))
            return v * 1073741824 if v >= 0 else None
        try:
            v = int(s)
            return v * 1048576 if v >= 0 else None
        except ValueError:
            return None
    return None


def _parse_bytes_value(raw):
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return _finite_whole(raw)
    if isinstance(raw, str):
        s = raw.strip()
        if s.upper() == 'N/A' or s == '':
            return None
        try:
            v = int(s)
            return v if v >= 0 else None
        except ValueError:
            return None
    return None


def _parse_csv(stdout):
    if not isinstance(stdout, str) or not stdout.strip():
        return []
    rows_in = [
        row for row in csv.reader(io.StringIO(stdout))
        if any(cell.strip() for cell in row)
    ]
    if len(rows_in) < 2:
        return []
    # Only these exact known NVIDIA MiB header fields carry convertible units.
    known_headers = {
        'memory.total [mib]': 'memory.total',
        'memory.free [mib]': 'memory.free',
        'memory.used [mib]': 'memory.used',
    }
    header = [known_headers.get(h.strip().lower(), h.strip().lower())
              for h in rows_in[0]]
    if len(header) != len(set(header)):
        return []
    if 'pci.bus_id' not in header and 'pci_bus_id' not in header:
        return []
    width = len(header)
    rows = []
    for vals in rows_in[1:]:
        if len(vals) != width:
            continue
        rows.append({header[i]: vals[i].strip() for i in range(width)})
    return rows


def _extract_nvidia(records, sample, now_utc, max_age):
    devices = []
    for row in records:
        pci_raw = row.get('pci.bus_id') or row.get('pci_bus_id')
        name = row.get('name')
        uuid = row.get('uuid')
        total_mib = _parse_mib_value(row.get('memory.total') or row.get('memory_total'))
        free_mib = _parse_mib_value(row.get('memory.free') or row.get('memory_free'))
        phys_id = _normalize_pci(pci_raw) if pci_raw else None
        ts, fresh = _stamp(sample, now_utc, max_age)
        mem_kind = _explicit_kind(sample)
        aliases = set()
        if phys_id:
            aliases.add(phys_id)
        if uuid:
            aliases.add(f"nv-uuid:{uuid.strip()}")
        if name:
            aliases.add(f"nv-name:{name.strip()}")
        devices.append({
            'physical_id': phys_id,
            'vendor_key': 'nvidia',
            'aliases': sorted(aliases),
            'memory_kind': mem_kind,
            'advertised_total_bytes': total_mib,
            'observed_free_bytes': free_mib,
            'sample_timestamp': ts.isoformat() if ts else None,
            'freshness_status': fresh,
            'source': {'tool': 'nvidia-smi', 'exit_code': sample.get('exit_code'), 'uuid': uuid},
        })
    return devices


def _extract_amd(records, sample, now_utc, max_age):
    devices = []
    schema = sample.get('schema_selector')
    if schema not in ('amd-smi-v1', 'amd-smi-v2'):
        return [], ['AMD unsupported schema']
    for rec in records:
        if not isinstance(rec, dict):
            continue
        bdf = rec.get('pci_bdf') or rec.get('bdf') or rec.get('pci_address')
        vendor = rec.get('vendor_name') or rec.get('vendor')
        name = rec.get('device_name') or rec.get('name')
        has_d = rec.get('dedicated_memory_bytes') is not None
        has_s = rec.get('shared_memory_bytes') is not None
        if has_d and has_s:
            return [], ['AMD contradictory memory fields']
        if not has_d and not has_s:
            continue
        if has_d:
            mem_kind = 'DEDICATED'
            total = _parse_bytes_value(rec.get('dedicated_memory_bytes'))
        else:
            mem_kind = 'SHARED_HOST'
            total = _parse_bytes_value(rec.get('shared_memory_bytes'))
        phys_id = _normalize_pci(bdf) if bdf else None
        ts, fresh = _stamp(sample, now_utc, max_age)
        aliases = set()
        if phys_id:
            aliases.add(phys_id)
        if name:
            aliases.add(f"amd-name:{name.strip()}")
        devices.append({
            'physical_id': phys_id,
            'vendor_key': 'amd',
            'aliases': sorted(aliases),
            'memory_kind': mem_kind,
            'advertised_total_bytes': total,
            'observed_free_bytes': None,
            'sample_timestamp': ts.isoformat() if ts else None,
            'freshness_status': fresh,
            'source': {'tool': 'amd-smi', 'exit_code': sample.get('exit_code'), 'schema': schema},
        })
    return devices, []


def _extract_intel(records, sample, now_utc, max_age):
    devices = []
    schema = sample.get('schema_selector')
    if schema not in ('xpu-smi-v1',):
        return [], ['Intel unsupported schema']
    for rec in records:
        if not isinstance(rec, dict):
            continue
        bdf = rec.get('pci_bdf') or rec.get('bdf')
        name = rec.get('device_name')
        mem_size = rec.get('memory_size')
        driver = rec.get('driver_version')
        total = _parse_bytes_value(mem_size)
        phys_id = _normalize_pci(bdf) if bdf else None
        ts, fresh = _stamp(sample, now_utc, max_age)
        aliases = set()
        if phys_id:
            aliases.add(phys_id)
        if name:
            aliases.add(f"intel-name:{name.strip()}")
        devices.append({
            'physical_id': phys_id,
            'vendor_key': 'intel',
            'aliases': sorted(aliases),
            'memory_kind': _explicit_kind(sample),
            'advertised_total_bytes': total,
            'observed_free_bytes': None,
            'sample_timestamp': ts.isoformat() if ts else None,
            'freshness_status': fresh,
            'source': {'tool': 'xpu-smi', 'exit_code': sample.get('exit_code'), 'driver': driver},
        })
    return devices, []


def _contradicts(a, b):
    return (
        a['vendor_key'] != b['vendor_key']
        or a['advertised_total_bytes'] != b['advertised_total_bytes']
        or a['memory_kind'] != b['memory_kind']
    )


def _prefer(existing, new):
    ts_e = _parse_utc(existing.get('sample_timestamp'))
    ts_n = _parse_utc(new.get('sample_timestamp'))
    chosen = dict(new if ts_n is not None and (ts_e is None or ts_n >= ts_e) else existing)
    chosen['aliases'] = sorted(set(existing['aliases']) | set(new['aliases']))
    return chosen


def normalize_inventory(samples, *, now_utc, max_age_seconds=5):
    now_utc, max_age_seconds = _require_clock(now_utc, max_age_seconds)
    all_devices = []
    conflicts = []
    refusals = []
    for sample in samples:
        tool = sample.get('tool')
        fmt = sample.get('format')
        exit_code = sample.get('exit_code')
        stdout = sample.get('stdout', '')
        if tool not in SUPPORTED_TOOLS:
            refusals.append({'reason': 'unsupported_tool', 'tool': tool})
            continue
        if fmt not in SUPPORTED_TOOLS[tool]:
            refusals.append({'reason': 'unsupported_format', 'tool': tool, 'format': fmt})
            continue
        if type(exit_code) is not int or exit_code != 0:
            refusals.append({'reason': 'nonzero_exit', 'tool': tool, 'exit_code': exit_code})
            continue
        try:
            if fmt == 'csv':
                records = _parse_csv(stdout)
            else:
                parsed = json.loads(stdout)
                records = parsed if isinstance(parsed, list) else parsed.get('devices', [])
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            refusals.append({'reason': 'parse_error', 'tool': tool, 'detail': str(e)})
            continue
        if tool == 'nvidia-smi':
            devs = _extract_nvidia(records, sample, now_utc, max_age_seconds)
            all_devices.extend(devs)
        elif tool == 'amd-smi':
            devs, errs = _extract_amd(records, sample, now_utc, max_age_seconds)
            all_devices.extend(devs)
            conflicts.extend(errs)
        elif tool == 'xpu-smi':
            devs, errs = _extract_intel(records, sample, now_utc, max_age_seconds)
            all_devices.extend(devs)
            conflicts.extend(errs)
    by_phys = {}
    tombstones = set()
    unqualified = []
    for d in all_devices:
        pid = d['physical_id']
        if not pid:
            unqualified.append(d)
            continue
        if pid in tombstones:
            continue
        if pid not in by_phys:
            by_phys[pid] = d
            continue
        existing = by_phys[pid]
        if _contradicts(existing, d):
            conflicts.append(
                f"Contradiction on {pid}: {existing['vendor_key']}/{existing['memory_kind']} vs {d['vendor_key']}/{d['memory_kind']}"
            )
            tombstones.add(pid)
            del by_phys[pid]
            continue
        by_phys[pid] = _prefer(existing, d)
    return {'devices': list(by_phys.values()) + unqualified, 'conflicts': conflicts, 'refusals': refusals}


def get_admission_snapshot(inventory_result, *, now_utc, max_age_seconds=5):
    now_utc, max_age_seconds = _require_clock(now_utc, max_age_seconds)
    eligible = []
    refused = []
    for d in inventory_result.get('devices', []):
        pid = d.get('physical_id')
        if not isinstance(pid, str) or _normalize_pci(pid) != pid:
            refused.append({'device': pid, 'reason': 'missing_physical_id'})
            continue
        ts = _parse_utc(d.get('sample_timestamp'))
        if ts is None:
            refused.append({'device': pid, 'reason': 'unknown_timestamp'})
            continue
        age = (now_utc - ts).total_seconds()
        if age < 0:
            refused.append({'device': pid, 'reason': 'future_timestamp'})
            continue
        if age > max_age_seconds:
            refused.append({'device': pid, 'reason': 'stale'})
            continue
        if d.get('memory_kind') != 'DEDICATED':
            refused.append({'device': pid, 'reason': 'not_dedicated'})
            continue
        total = d.get('advertised_total_bytes')
        free = d.get('observed_free_bytes')
        if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
            refused.append({'device': pid, 'reason': 'invalid_total'})
            continue
        if isinstance(free, bool) or not isinstance(free, int):
            refused.append({'device': pid, 'reason': 'unknown_free'})
            continue
        if free <= 0:
            refused.append({'device': pid, 'reason': 'no_free_capacity'})
            continue
        if free > total:
            refused.append({'device': pid, 'reason': 'free_exceeds_total'})
            continue
        src = d.get('source')
        if not isinstance(src, dict) or _VENDOR_TOOL.get(d.get('vendor_key')) != src.get('tool'):
            refused.append({'device': pid, 'reason': 'invalid_source'})
            continue
        eligible.append(d)
    return {'eligible': eligible, 'refused': refused}
