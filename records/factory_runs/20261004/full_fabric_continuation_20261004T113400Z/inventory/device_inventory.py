"""Pure stdlib GPU inventory adapter. No native execution, no subprocess at import."""
import json
import math
import re
from datetime import datetime, timezone

PCI_RE = re.compile(r'^([0-9a-fA-F]{4}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])$')
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
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _normalize_pci(raw):
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    m = PCI_RE.match(s)
    if not m:
        return None
    dom, bus, dev, fn = m.groups()
    return f"{dom.zfill(4)}:{bus}:{dev}.{fn}"


def _parse_mib_value(raw):
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        if raw < 0:
            return None
        return raw * 1048576
    if isinstance(raw, float):
        if math.isnan(raw) or math.isinf(raw) or raw < 0:
            return None
        return int(raw) * 1048576
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
    if isinstance(raw, int):
        return raw if raw >= 0 else None
    if isinstance(raw, float):
        if math.isnan(raw) or math.isinf(raw) or raw < 0:
            return None
        return int(raw)
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
    lines = [l for l in stdout.splitlines() if l.strip()]
    if len(lines) < 2:
        return []
    header = [h.strip().lower() for h in lines[0].split(',')]
    rows = []
    for line in lines[1:]:
        vals = [v.strip() for v in line.split(',')]
        if len(vals) != len(header):
            continue
        rows.append(dict(zip(header, vals)))
    return rows


def _extract_nvidia(records, sample, now_utc, max_age):
    devices = []
    for row in records:
        pci_raw = row.get('pci.bus_id') or row.get('pci_bus_id')
        name = row.get('name')
        uuid = row.get('uuid')
        total_mib = _parse_mib_value(row.get('memory.total') or row.get('memory_total'))
        free_mib = _parse_mib_value(row.get('memory.free') or row.get('memory_free'))
        used_mib = _parse_mib_value(row.get('memory.used') or row.get('memory_used'))
        phys_id = _normalize_pci(pci_raw) if pci_raw else None
        ts = _parse_utc(sample.get('sampled_at_utc'))
        fresh = 'FRESH' if ts and (now_utc - ts).total_seconds() <= max_age else 'STALE'
        mem_kind = sample.get('memory_kind', 'DEDICATED')
        if mem_kind not in ('DEDICATED', 'SHARED_HOST', 'UNKNOWN'):
            mem_kind = 'DEDICATED'
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
        dedicated = rec.get('dedicated_memory_bytes')
        shared = rec.get('shared_memory_bytes')
        if dedicated is None and shared is None:
            continue
        d_bytes = _parse_bytes_value(dedicated)
        s_bytes = _parse_bytes_value(shared)
        if d_bytes is not None and s_bytes is not None:
            return [], ['AMD contradictory memory fields']
        mem_kind = 'DEDICATED' if d_bytes is not None else 'SHARED_HOST'
        total = d_bytes if d_bytes is not None else s_bytes
        phys_id = _normalize_pci(bdf) if bdf else None
        ts = _parse_utc(sample.get('sampled_at_utc'))
        fresh = 'FRESH' if ts and (now_utc - ts).total_seconds() <= max_age else 'STALE'
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
        ts = _parse_utc(sample.get('sampled_at_utc'))
        fresh = 'FRESH' if ts and (now_utc - ts).total_seconds() <= max_age else 'STALE'
        aliases = set()
        if phys_id:
            aliases.add(phys_id)
        if name:
            aliases.add(f"intel-name:{name.strip()}")
        devices.append({
            'physical_id': phys_id,
            'vendor_key': 'intel',
            'aliases': sorted(aliases),
            'memory_kind': 'DEDICATED',
            'advertised_total_bytes': total,
            'observed_free_bytes': None,
            'sample_timestamp': ts.isoformat() if ts else None,
            'freshness_status': fresh,
            'source': {'tool': 'xpu-smi', 'exit_code': sample.get('exit_code'), 'driver': driver},
        })
    return devices, []


def normalize_inventory(samples, *, now_utc, max_age_seconds=5):
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
        if exit_code != 0:
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
    # Dedup by physical_id; detect contradictions
    by_phys = {}
    unqualified = []
    for d in all_devices:
        pid = d['physical_id']
        if not pid:
            unqualified.append(d)
            continue
        if pid in by_phys:
            existing = by_phys[pid]
            if existing['vendor_key'] != d['vendor_key']:
                conflicts.append(f"Vendor contradiction on {pid}: {existing['vendor_key']} vs {d['vendor_key']}")
                del by_phys[pid]
                continue
            if existing['advertised_total_bytes'] != d['advertised_total_bytes']:
                conflicts.append(f"Total contradiction on {pid}")
                del by_phys[pid]
                continue
            merged_aliases = set(existing['aliases']) | set(d['aliases'])
            existing['aliases'] = sorted(merged_aliases)
        else:
            by_phys[pid] = d
    qualified = list(by_phys.values())
    return {'devices': qualified + unqualified, 'conflicts': conflicts, 'refusals': refusals}


def get_admission_snapshot(inventory_result, *, now_utc, max_age_seconds=5):
    eligible = []
    refused = []
    for d in inventory_result.get('devices', []):
        if d['freshness_status'] != 'FRESH':
            refused.append({'device': d['physical_id'], 'reason': 'stale'})
            continue
        if d['memory_kind'] != 'DEDICATED':
            refused.append({'device': d['physical_id'], 'reason': 'not_dedicated'})
            continue
        if d['observed_free_bytes'] is None:
            refused.append({'device': d['physical_id'], 'reason': 'unknown_free'})
            continue
        if d['observed_free_bytes'] <= 0:
            refused.append({'device': d['physical_id'], 'reason': 'no_free_capacity'})
            continue
        eligible.append(d)
    return {'eligible': eligible, 'refused': refused}
