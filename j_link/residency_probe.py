#!/usr/bin/env python3
"""Control R: dedicated-vs-shared residency measurement for one transfer.

Doc 11 section 5 makes residency evidence mandatory: a byte comparison that
passes cannot distinguish a direct peer path from a host bounce, because two
real incidents returned success on payloads that never touched dedicated VRAM.
This module samples every memory counter that can actually be obtained for an
OpenCL device on this host, then decides what those counters prove.

The decision is deliberately conservative.  A pass verdict requires an
identity-bound dedicated counter on BOTH endpoints, proof that each counter
tracks a known allocation, resolution fine enough to see the payload, and a
shared-memory counter that stayed flat.  Anything less is
UNMEASURABLE_ON_THIS_PLATFORM -- never a pass.

Measured limits of this host, recorded so no reader mistakes them for a pass:
  * one discrete GPU (NVIDIA RTX 5070 Ti) and one integrated AMD on shared
    host memory, so zero directed pairs are constructible;
  * nvidia-smi memory.used is a per-context indicator here, not a per-buffer
    byte counter.  With an OpenCL context already created it moved 0 bytes for
    256 MiB, 1024 MiB and 2048 MiB allocations and 0 bytes for their release,
    while context creation and destruction moved it by +221 MiB and -221 MiB.
    The Windows PDH counter "\\GPU Adapter Memory(*)\\Dedicated Usage" behaved
    the same way.  Neither can attribute bytes to a specific transfer;
  * pyopencl 2025.2.6 answers an unrecognized device_info parameter with a
    bogus scalar instead of raising (0x4008 returned int 1), so raw-hex
    vendor free-memory queries are refused by policy rather than reported;
  * the pinned opencl_executor exposes no forward_boundary callable -- it
    forwards each context boundary inline inside _execute_gpu -- so
    measure_boundary resolves and records that absence instead of wrapping a
    symbol that does not exist.

Exit codes follow the project convention: 0 PASS, 1 FAIL, 2 REFUSED or
NOT_CHECKED.  Exit 2 is not an error; on this single-GPU host it is the
correct, expected result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

MIB = 1024 * 1024
KIB = 1024

UNAVAILABLE = 'UNAVAILABLE'
NOT_CHECKED = 'NOT_CHECKED'
SAMPLED = 'SAMPLED'
PASS = 'PASS'
FAIL = 'FAIL'

DEDICATED_TO_DEDICATED = 'DEDICATED_TO_DEDICATED'
INVOLVED_SHARED_HOST_MEMORY = 'INVOLVED_SHARED_HOST_MEMORY'
NO_MEASURABLE_DELTA = 'NO_MEASURABLE_DELTA'
UNMEASURABLE_ON_THIS_PLATFORM = 'UNMEASURABLE_ON_THIS_PLATFORM'
VERDICTS = (
    DEDICATED_TO_DEDICATED,
    INVOLVED_SHARED_HOST_MEMORY,
    NO_MEASURABLE_DELTA,
    UNMEASURABLE_ON_THIS_PLATFORM,
)

RESULT_LABELS = [
    'CONTROL_R_RESIDENCY_MEASUREMENT_ONLY',
    'NOT_A_PEER_ACCESS_OR_BANDWIDTH_PROOF',
    'A_PASS_REQUIRES_TWO_IDENTITY_BOUND_DEDICATED_COUNTERS',
]

# The boundary forwarder this module was asked to wrap.  It does not exist in
# the pinned opencl_executor, which forwards boundaries inline inside
# _execute_gpu; resolution is recorded rather than faked.
BOUNDARY_FORWARDER_CANDIDATES = ('forward_boundary',)

DEFAULT_SELF_TEST_MIB = 64
MAX_RESULT_BYTES = 256 * 1024
SUBPROCESS_TIMEOUT_SECONDS = 30

DEVICE_LOCAL = 'DEVICE_LOCAL_MEMORY_REPORTED'
SHARED_HOST = 'SHARED_HOST_MEMORY_NOT_DEDICATED_VRAM'

_BDF_RE = re.compile(r'^([0-9a-fA-F]{4}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])$')
_PERF_COUNTER_RE = re.compile(
    r'GPU Adapter Memory\((?P<instance>[^)]*)\)\\(?P<kind>Dedicated|Shared) Usage')


class ResidencyUnavailable(RuntimeError):
    """No OpenCL runtime or no device could be sampled at all."""


class ResidencyRefused(RuntimeError):
    """The requested measurement is invalid or unconstructible."""


def _now_utc():
    return datetime.now(timezone.utc)


def _positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ResidencyRefused(f'{name} must be a positive integer')
    return value


def _subprocess_run(command, timeout=SUBPROCESS_TIMEOUT_SECONDS):
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                          creationflags=creationflags)


def _tool_result(tool, argv, *, timeout=SUBPROCESS_TIMEOUT_SECONDS):
    """Run one vendor/OS tool, recording refusal instead of inventing a value."""
    resolved = shutil.which(tool)
    if not resolved:
        return {'status': UNAVAILABLE, 'tool': tool, 'argv': list(argv),
                'reason': 'REFUSED_TOOL_NOT_FOUND', 'exit_code': None, 'stdout': None}
    try:
        proc = _subprocess_run([resolved] + list(argv), timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return {'status': UNAVAILABLE, 'tool': tool, 'argv': list(argv), 'tool_path': resolved,
                'reason': f'REFUSED_TOOL_EXECUTION_FAILED: {type(exc).__name__}: {exc}',
                'exit_code': None, 'stdout': None}
    if proc.returncode != 0:
        return {'status': UNAVAILABLE, 'tool': tool, 'argv': list(argv), 'tool_path': resolved,
                'reason': 'REFUSED_NONZERO_EXIT', 'exit_code': proc.returncode,
                'stderr': proc.stderr[-2048:], 'stdout': None}
    return {'status': SAMPLED, 'tool': tool, 'argv': list(argv), 'tool_path': resolved,
            'reason': None, 'exit_code': 0, 'stdout': proc.stdout[:4096],
            'stderr': proc.stderr[-512:]}


def _normalize_bdf(raw):
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    # nvidia-smi prints an eight hex digit domain; the canonical form has four.
    head, separator, rest = text.partition(':')
    if separator and len(head) == 8 and all(c in '0123456789abcdefABCDEF' for c in head):
        text = head[4:] + separator + rest
    match = _BDF_RE.match(text)
    if not match:
        return None
    domain, bus, device, function = match.groups()
    return f'{int(domain, 16):04x}:{bus.lower()}:{device.lower()}.{function}'


def _parse_counter_float(raw):
    """Parse one PDH CSV cell, refusing rather than guessing a separator."""
    if not isinstance(raw, str):
        return None, 'REFUSED_NON_STRING_COUNTER_VALUE'
    text = raw.strip().strip('"')
    if not text or text.upper() in ('N/A', '-1.#IND00'):
        return None, 'REFUSED_COUNTER_VALUE_NOT_NUMERIC'
    try:
        value = float(text)
    except ValueError:
        if text.count(',') == 1 and '.' not in text:
            try:
                value = float(text.replace(',', '.'))
            except ValueError:
                return None, 'REFUSED_COUNTER_VALUE_NOT_NUMERIC'
        else:
            return None, 'REFUSED_COUNTER_VALUE_NOT_NUMERIC'
    if value != value or value in (float('inf'), float('-inf')):
        return None, 'REFUSED_COUNTER_VALUE_NOT_FINITE'
    if value < 0:
        return None, 'REFUSED_COUNTER_VALUE_NEGATIVE'
    return int(value), None


def _executor_module():
    """Import the existing executor without modifying it; refuse on failure."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import opencl_executor
    except Exception as exc:
        raise ResidencyUnavailable(
            f'REFUSED_EXECUTOR_IMPORT_FAILED: {type(exc).__name__}: {exc}') from exc
    return opencl_executor


def _load_opencl():
    try:
        import pyopencl as cl
    except Exception as exc:
        raise ResidencyUnavailable(f'REFUSED_PYOPENCL_UNAVAILABLE: {exc}') from exc
    return cl


# --------------------------------------------------------------------------
# snapshots
# --------------------------------------------------------------------------

def _device_view(device):
    """Accept an executor record, a bare cl.Device, or metadata-only dict."""
    if isinstance(device, dict):
        handle = device.get('device')
        return {
            'handle': handle,
            'runtime_id': device.get('runtime_id') or device.get('id'),
            'physical_id': device.get('physical_id'),
            'identity_confidence': device.get('identity_confidence'),
            'vendor': device.get('vendor'),
            'vendor_key': device.get('vendor_key'),
            'platform': device.get('platform'),
            'name': device.get('name'),
            'memory_classification': device.get('memory_classification'),
        }
    return {'handle': device, 'runtime_id': None, 'physical_id': None,
            'identity_confidence': None, 'vendor': None, 'vendor_key': None,
            'platform': None, 'name': None, 'memory_classification': None}


def _unavailable(reason):
    return {'status': UNAVAILABLE, 'reason': reason, 'value': None}


def _query(handle, attribute, reason):
    """One real OpenCL query; any failure is recorded, never substituted."""
    if handle is None:
        return _unavailable('REFUSED_NO_DEVICE_HANDLE')
    try:
        return {'status': SAMPLED, 'reason': None, 'value': getattr(handle, attribute)}
    except Exception as exc:
        return _unavailable(f'{reason}: {type(exc).__name__}')


def _sample_amd_free_memory(handle, cl):
    """CL_DEVICE_GLOBAL_FREE_MEMORY_AMD via pyopencl's typed name only."""
    info = getattr(cl, 'device_info', None)
    parameter = getattr(info, 'GLOBAL_FREE_MEMORY_AMD', None) if info else None
    if parameter is None:
        return _unavailable('REFUSED_TYPED_AMD_FREE_MEMORY_QUERY_ABSENT')
    if handle is None:
        return _unavailable('REFUSED_NO_DEVICE_HANDLE')
    try:
        raw = handle.get_info(parameter)
    except Exception as exc:
        return _unavailable(f'REFUSED_AMD_FREE_MEMORY_QUERY_FAILED: {type(exc).__name__}')
    if not isinstance(raw, (list, tuple)) or not raw:
        return {'status': UNAVAILABLE, 'reason': 'REFUSED_AMD_FREE_MEMORY_SHAPE_UNEXPECTED',
                'value': None, 'raw': repr(raw)[:200]}
    values = [int(item) for item in raw]
    return {'status': SAMPLED, 'reason': None, 'value': values[0] * KIB,
            'raw_kib': values, 'documented_element_count': 2,
            'observed_element_count': len(values),
            'contract': ('MATCHED' if len(values) == 2 else 'DEGRADED_SINGLE_ELEMENT'),
            'semantics': 'free bytes derived from reported free KiB'}


def _refuse_raw_hex_vendor_queries():
    """Policy: never report a number from an untyped device_info parameter."""
    return _unavailable(
        'REFUSED_UNTYPED_VENDOR_QUERY: pyopencl 2025.2.6 returns a bogus scalar '
        'for an unrecognized device_info parameter (0x4008 measured as int 1) '
        'instead of raising, so a raw-hex free-memory query cannot be trusted')


def _sample_nvidia_smi(view, population_hint=None):
    """Per-PCI-BDF dedicated counter from nvidia-smi, bound by verified identity."""
    argv = ['--query-gpu=pci.bus_id,name,memory.used,memory.free',
            '--format=csv,noheader,nounits']
    result = _tool_result('nvidia-smi', argv)
    if result['status'] != SAMPLED:
        return result | {'counter_kind': 'DEDICATED_USED_AND_FREE_MIB',
                         'binding_method': None, 'dedicated_used_bytes': None,
                         'dedicated_free_bytes': None, 'resolution_bytes': MIB}
    rows = []
    for line in result['stdout'].splitlines():
        cells = next(csv.reader(io.StringIO(line)), None)
        if not cells or len(cells) < 4:
            continue
        rows.append({'pci_bus_id': cells[0].strip(), 'name': cells[1].strip(),
                     'used_mib': cells[2].strip(), 'free_mib': cells[3].strip()})
    if not rows:
        return result | {'status': UNAVAILABLE, 'reason': 'REFUSED_NO_NVIDIA_SMI_ROWS',
                         'counter_kind': 'DEDICATED_USED_AND_FREE_MIB', 'binding_method': None,
                         'dedicated_used_bytes': None, 'dedicated_free_bytes': None,
                         'resolution_bytes': MIB}

    binding_method, bound = None, None
    raw_identity = view.get('physical_id')
    if isinstance(raw_identity, str) and raw_identity.startswith('pci:'):
        raw_identity = raw_identity[len('pci:'):]
    target_bdf = _normalize_bdf(raw_identity)
    if target_bdf:
        matches = [row for row in rows if _normalize_bdf(row['pci_bus_id']) == target_bdf]
        if len(matches) == 1:
            binding_method, bound = 'EXACT_PCI_BDF', matches[0]
        elif len(matches) > 1:
            binding_method = 'REFUSED_AMBIGUOUS_PCI_BDF'
    if bound is None and binding_method is None:
        nvidia_rows = len(rows)
        nvidia_devices = population_hint or {}
        if nvidia_rows == 1 and nvidia_devices.get('nvidia_opencl_devices') == 1:
            binding_method, bound = 'UNIQUE_VENDOR_POPULATION', rows[0]
        elif nvidia_rows > 1:
            binding_method = 'REFUSED_AMBIGUOUS_NVIDIA_POPULATION'
        else:
            binding_method = 'REFUSED_NO_BINDING_EVIDENCE'

    base = {'counter_kind': 'DEDICATED_USED_AND_FREE_MIB', 'rows': rows,
            'binding_method': binding_method, 'resolution_bytes': MIB,
            'dedicated_used_bytes': None, 'dedicated_free_bytes': None}
    if bound is None:
        return result | base | {'status': UNAVAILABLE,
                                'reason': f'REFUSED_NVIDIA_SMI_BINDING: {binding_method}'}
    used, used_reason = _parse_counter_float(bound['used_mib'])
    free, free_reason = _parse_counter_float(bound['free_mib'])
    if used is None or free is None:
        return result | base | {'status': UNAVAILABLE,
                                'reason': used_reason or free_reason,
                                'bound_row': bound}
    return result | base | {'status': SAMPLED, 'reason': None, 'bound_row': bound,
                            'pci_bus_id_normalized': _normalize_bdf(bound['pci_bus_id']),
                            'dedicated_used_bytes': used * MIB,
                            'dedicated_free_bytes': free * MIB}


def _sample_windows_adapter_memory():
    """PDH dedicated-vs-shared per adapter; identity is NOT bindable from here."""
    argv = [r'\GPU Adapter Memory(*)\Dedicated Usage',
            r'\GPU Adapter Memory(*)\Shared Usage', '-sc', '1', '-y']
    result = _tool_result('typeperf', argv)
    base = {'counter_kind': 'DEDICATED_AND_SHARED_USAGE_BYTES_PER_ADAPTER',
            'adapters': {}, 'resolution_bytes': 1,
            'identity_binding': 'UNBOUND_NO_DXGI_LUID_QUERY',
            'binding_note': ('Adapter instances are keyed by LUID. A LUID to PCI '
                             'binding needs DXGI, which is outside stdlib plus '
                             'pyopencl, so these counters cannot be attributed to '
                             'a specific OpenCL device and cannot support a verdict.')}
    if result['status'] != SAMPLED:
        return result | base
    lines = [line for line in result['stdout'].splitlines() if line.startswith('"')]
    if len(lines) < 2:
        return result | base | {'status': UNAVAILABLE,
                                'reason': 'REFUSED_TYPEPERF_OUTPUT_UNPARSEABLE'}
    try:
        table = list(csv.reader(io.StringIO('\n'.join(lines))))
    except csv.Error as exc:
        return result | base | {'status': UNAVAILABLE,
                                'reason': f'REFUSED_TYPEPERF_CSV_ERROR: {exc}'}
    header, values = table[0], table[1]
    adapters, refusals = {}, []
    for name, value in zip(header[1:], values[1:]):
        match = _PERF_COUNTER_RE.search(name)
        if not match:
            refusals.append({'counter': name, 'reason': 'REFUSED_COUNTER_NAME_NOT_RECOGNIZED'})
            continue
        parsed, reason = _parse_counter_float(value)
        entry = adapters.setdefault(match.group('instance'), {})
        if parsed is None:
            entry[match.group('kind').lower() + '_bytes'] = None
            refusals.append({'counter': name, 'reason': reason})
        else:
            entry[match.group('kind').lower() + '_bytes'] = parsed
    if not adapters:
        return result | base | {'status': UNAVAILABLE, 'refusals': refusals,
                                'reason': 'REFUSED_NO_RECOGNIZED_ADAPTER_COUNTERS'}
    return result | base | {'status': SAMPLED, 'reason': None, 'adapters': adapters,
                            'refusals': refusals}


def sample_memory(device, *, population_hint=None, host_counters=True):
    """Sample every memory counter obtainable for one OpenCL device.

    Static capacities (global size, max allocation, host_unified) are real but
    cannot move, so they are recorded and explicitly excluded from any delta.
    Usage counters are attempted and recorded as UNAVAILABLE on failure.
    """
    view = _device_view(device)
    handle = view['handle']
    cl = None
    if handle is not None:
        try:
            cl = _load_opencl()
        except ResidencyUnavailable:
            cl = None

    global_mem = _query(handle, 'global_mem_size', 'REFUSED_GLOBAL_MEM_QUERY_FAILED')
    max_alloc = _query(handle, 'max_mem_alloc_size', 'REFUSED_MAX_ALLOC_QUERY_FAILED')
    unified = _query(handle, 'host_unified_memory', 'REFUSED_HOST_UNIFIED_QUERY_FAILED')
    if handle is not None:
        for attribute, reason in (('name', 'REFUSED_NAME_QUERY_FAILED'),
                                  ('vendor', 'REFUSED_VENDOR_QUERY_FAILED')):
            if not view.get(attribute) or view[attribute] == 'None':
                queried = _query(handle, attribute, reason)
                if queried['status'] == SAMPLED:
                    view[attribute] = str(queried['value'])
        if view.get('platform') is None:
            try:
                view['platform'] = str(handle.platform.name)
            except Exception:
                view['platform'] = None

    unified_value = (bool(unified['value']) if unified['status'] == SAMPLED else None)
    classification = view.get('memory_classification')
    if not classification:
        classification = (SHARED_HOST if unified_value is True
                          else DEVICE_LOCAL if unified_value is False else 'UNKNOWN')
    vendor_key = view.get('vendor_key')
    if not vendor_key and view.get('vendor'):
        text = str(view['vendor']).lower()
        vendor_key = ('NVIDIA' if 'nvidia' in text else
                      'AMD' if ('amd' in text or 'advanced micro' in text) else
                      'Intel' if 'intel' in text else None)

    amd_free = _unavailable('REFUSED_NOT_ATTEMPTED_NO_HANDLE') if handle is None \
        else (_sample_amd_free_memory(handle, cl) if cl is not None
              else _unavailable('REFUSED_PYOPENCL_UNAVAILABLE'))
    vendor_free_refusal = _refuse_raw_hex_vendor_queries()

    opencl_block = {
        'global_mem_bytes': global_mem['value'] if global_mem['status'] == SAMPLED else None,
        'global_mem_query': global_mem,
        'max_mem_alloc_bytes': max_alloc['value'] if max_alloc['status'] == SAMPLED else None,
        'max_mem_alloc_query': max_alloc,
        'host_unified_memory': unified_value,
        'host_unified_query': unified,
        'memory_classification': classification,
        'vendor_free_memory_amd': amd_free,
        'vendor_free_memory_raw_hex': vendor_free_refusal,
        'static_only_note': ('global_mem_size, max_mem_alloc_size and host_unified '
                             'are fixed device properties; they cannot move during '
                             'a transfer and therefore carry no residency signal'),
    }

    host_block = {'status': NOT_CHECKED, 'reason': 'REFUSED_HOST_COUNTERS_DISABLED',
                  'nvidia_smi': None, 'windows_gpu_adapter_memory': None}
    if host_counters:
        nvidia_smi = (_sample_nvidia_smi(view, population_hint)
                      if vendor_key == 'NVIDIA'
                      else {'status': NOT_CHECKED, 'reason': 'REFUSED_NOT_AN_NVIDIA_DEVICE',
                            'counter_kind': 'DEDICATED_USED_AND_FREE_MIB',
                            'dedicated_used_bytes': None, 'dedicated_free_bytes': None,
                            'resolution_bytes': MIB, 'binding_method': None})
        adapter = _sample_windows_adapter_memory()
        sampled = any(item.get('status') == SAMPLED for item in (nvidia_smi, adapter))
        host_block = {'status': SAMPLED if sampled else UNAVAILABLE,
                      'reason': None if sampled else 'REFUSED_NO_HOST_COUNTER_SAMPLED',
                      'nvidia_smi': nvidia_smi, 'windows_gpu_adapter_memory': adapter}

    return {
        'sampled_at_utc': _now_utc().isoformat(),
        'device_identity': {
            'runtime_id': view.get('runtime_id'), 'physical_id': view.get('physical_id'),
            'identity_confidence': view.get('identity_confidence'),
            'vendor': view.get('vendor'), 'vendor_key': vendor_key,
            'name': view.get('name'), 'platform': view.get('platform'),
        },
        'opencl': opencl_block,
        'host_counters': host_block,
    }


# --------------------------------------------------------------------------
# decision
# --------------------------------------------------------------------------

def _counter(entry, key):
    if not isinstance(entry, dict):
        return None
    value = entry.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _endpoint_view(snapshot):
    """Normalize one snapshot into the dedicated/shared observations used below."""
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    identity = snapshot.get('device_identity') or {}
    opencl = snapshot.get('opencl') or {}
    host = snapshot.get('host_counters') or {}
    smi = host.get('nvidia_smi') or {}
    classification = opencl.get('memory_classification')

    dedicated = {'status': UNAVAILABLE, 'reason': 'REFUSED_NO_DEDICATED_USAGE_COUNTER',
                 'used_bytes': None, 'resolution_bytes': None, 'source': None}
    shared = {'status': UNAVAILABLE, 'reason': 'REFUSED_NO_SHARED_USAGE_COUNTER',
              'used_bytes': None, 'resolution_bytes': None, 'source': None}

    smi_used = _counter(smi, 'dedicated_used_bytes')
    if smi.get('status') == SAMPLED and smi_used is not None:
        dedicated = {'status': SAMPLED, 'reason': None, 'used_bytes': smi_used,
                     'resolution_bytes': _counter(smi, 'resolution_bytes') or MIB,
                     'source': f"nvidia-smi:{smi.get('binding_method')}"}
    elif smi.get('status') == SAMPLED:
        dedicated['reason'] = 'REFUSED_NVIDIA_SMI_COUNTER_NOT_NUMERIC'
    elif isinstance(smi.get('reason'), str):
        dedicated['reason'] = smi['reason']

    if classification == SHARED_HOST:
        # An integrated device on unified memory has no dedicated VRAM at all;
        # its free-memory query describes host memory, so it lands in `shared`.
        dedicated = {'status': UNAVAILABLE, 'used_bytes': None, 'resolution_bytes': None,
                     'source': None, 'reason': f'REFUSED_{SHARED_HOST}'}
        amd = opencl.get('vendor_free_memory_amd') or {}
        free = _counter(amd, 'value')
        total = _counter(opencl, 'global_mem_bytes')
        if amd.get('status') == SAMPLED and free is not None and total is not None:
            shared = {'status': SAMPLED, 'reason': None, 'used_bytes': max(total - free, 0),
                      'resolution_bytes': KIB, 'source': 'CL_DEVICE_GLOBAL_FREE_MEMORY_AMD',
                      'derivation': 'global_mem_bytes minus reported free bytes',
                      'contract': amd.get('contract')}
        elif amd.get('status') == SAMPLED:
            shared['reason'] = 'REFUSED_SHARED_DERIVATION_INCOMPLETE'
        elif isinstance(amd.get('reason'), str):
            shared['reason'] = amd['reason']
    elif classification == DEVICE_LOCAL:
        amd = opencl.get('vendor_free_memory_amd') or {}
        free = _counter(amd, 'value')
        total = _counter(opencl, 'global_mem_bytes')
        if dedicated['status'] != SAMPLED and amd.get('status') == SAMPLED \
                and free is not None and total is not None:
            dedicated = {'status': SAMPLED, 'reason': None, 'used_bytes': max(total - free, 0),
                         'resolution_bytes': KIB,
                         'source': 'CL_DEVICE_GLOBAL_FREE_MEMORY_AMD',
                         'derivation': 'global_mem_bytes minus reported free bytes',
                         'contract': amd.get('contract')}
    else:
        if dedicated['status'] != SAMPLED:
            dedicated['reason'] = 'REFUSED_MEMORY_CLASSIFICATION_UNKNOWN'

    adapter = host.get('windows_gpu_adapter_memory') or {}
    windows_evidence = {
        'status': adapter.get('status', NOT_CHECKED),
        'identity_binding': adapter.get('identity_binding'),
        'adapters': adapter.get('adapters') or {},
        'reason': adapter.get('reason'),
        'excluded_from_verdict': True,
        'exclusion_reason': ('LUID-keyed instances cannot be bound to an OpenCL '
                             'device without DXGI, so attributing bytes to an '
                             'endpoint would be fabricated'),
    }

    # A shared-memory counter is required before any pass verdict, because
    # without one a host bounce cannot be excluded.  Only an explicitly
    # identity-bound counter qualifies; PDH adapter instances do not.
    supplied = host.get('shared_usage') or {}
    binding = supplied.get('identity_binding')
    bound = isinstance(binding, str) and binding and not binding.startswith('UNBOUND')
    if shared['status'] != SAMPLED and supplied.get('status') == SAMPLED:
        used = _counter(supplied, 'used_bytes')
        if used is not None and bound:
            shared = {'status': SAMPLED, 'reason': None, 'used_bytes': used,
                      'resolution_bytes': _counter(supplied, 'resolution_bytes') or 1,
                      'source': supplied.get('source') or 'CALLER_SUPPLIED_SHARED_USAGE',
                      'identity_binding': binding}
        elif used is None:
            shared['reason'] = 'REFUSED_SHARED_USAGE_COUNTER_NOT_NUMERIC'
        else:
            shared['reason'] = 'REFUSED_SHARED_USAGE_COUNTER_IDENTITY_UNBOUND'
    return {
        'identity': {'physical_id': identity.get('physical_id'),
                     'identity_confidence': identity.get('identity_confidence'),
                     'vendor_key': identity.get('vendor_key'),
                     'runtime_id': identity.get('runtime_id')},
        'dedicated': dedicated, 'shared': shared,
        'windows_adapter_memory': windows_evidence,
        'static': {'global_mem_bytes': _counter(opencl, 'global_mem_bytes'),
                   'max_mem_alloc_bytes': _counter(opencl, 'max_mem_alloc_bytes'),
                   'host_unified_memory': opencl.get('host_unified_memory'),
                   'memory_classification': classification},
    }


class ResidencyDelta:
    """One Control R decision, with the evidence that produced it."""

    def __init__(self, verdict, reason, *, refusal=None, evidence=None, transfer_bytes=None):
        if verdict not in VERDICTS:
            raise ResidencyRefused(f'Unknown residency verdict: {verdict}')
        self.verdict = verdict
        self.reason = reason
        self.refusal = refusal
        self.transfer_bytes = transfer_bytes
        self.evidence = evidence or {}

    @property
    def measured(self):
        return self.verdict in (DEDICATED_TO_DEDICATED, INVOLVED_SHARED_HOST_MEMORY)

    def as_dict(self):
        return {
            'control': 'R_RESIDENCY',
            'verdict': self.verdict,
            'reason': self.reason,
            'refusal': self.refusal,
            'transfer_bytes': self.transfer_bytes,
            'pass_claimed': self.verdict == DEDICATED_TO_DEDICATED,
            'evidence': self.evidence,
        }


DEFAULT_TOLERANCE = {'noise_floor_bytes': 2 * MIB, 'fraction_of_transfer': 0.02,
                     'resolution_multiplier': 2}


def _tolerance_bytes(transfer_bytes, resolution_bytes, tolerance):
    floor = tolerance.get('noise_floor_bytes', 0)
    fraction = tolerance.get('fraction_of_transfer', 0.0) * transfer_bytes
    resolution = (tolerance.get('resolution_multiplier', 0) * resolution_bytes
                  if isinstance(resolution_bytes, int) else 0)
    return int(max(floor, fraction, resolution))


def _calibration_status(snapshot, calibration):
    """Per-endpoint proof that the counter tracks a known allocation."""
    if isinstance(calibration, dict):
        for key in ('source', 'destination'):
            entry = calibration.get(key)
            if isinstance(entry, dict) and entry.get('physical_id') == (
                    (snapshot.get('device_identity') or {}).get('physical_id')):
                return entry.get('status', NOT_CHECKED), entry
    block = (snapshot.get('calibration') or {}) if isinstance(snapshot, dict) else {}
    return block.get('status', NOT_CHECKED), block


def compute_residency_delta(source_before, source_after, destination_before,
                            destination_after, transfer_bytes, *,
                            calibration=None, tolerance=None):
    """Decide what the before/after counters prove about one transfer.

    Every gate below fails toward UNMEASURABLE_ON_THIS_PLATFORM.  A pass needs
    two distinct identity-bound endpoints, a dedicated counter on each that was
    calibrated against a known allocation, resolution fine enough to see the
    payload, the source dedicated usage falling by the payload size, the
    destination dedicated usage rising by it, and both shared counters flat.
    """
    tolerance = dict(DEFAULT_TOLERANCE, **(tolerance or {}))
    evidence = {'tolerance': tolerance, 'source': None, 'destination': None,
                'gates': []}

    def refuse(reason, refusal, verdict=UNMEASURABLE_ON_THIS_PLATFORM):
        evidence['gates'].append({'gate': refusal, 'outcome': 'FAILED', 'detail': reason})
        return ResidencyDelta(verdict, reason, refusal=refusal, evidence=evidence,
                              transfer_bytes=transfer_bytes if isinstance(transfer_bytes, int)
                              and not isinstance(transfer_bytes, bool) else None)

    def gate(name, ok, detail):
        evidence['gates'].append({'gate': name, 'outcome': 'PASSED' if ok else 'FAILED',
                                  'detail': detail})
        return ok

    if isinstance(transfer_bytes, bool) or not isinstance(transfer_bytes, int) \
            or transfer_bytes <= 0:
        return refuse(f'transfer_bytes must be a positive integer, got {transfer_bytes!r}',
                      'REFUSED_INVALID_TRANSFER_BYTES')
    for label, snapshot in (('source_before', source_before), ('source_after', source_after),
                            ('destination_before', destination_before),
                            ('destination_after', destination_after)):
        if not isinstance(snapshot, dict):
            return refuse(f'{label} must be a snapshot dict, got {type(snapshot).__name__}',
                          'REFUSED_INVALID_SNAPSHOT')

    src = (_endpoint_view(source_before), _endpoint_view(source_after))
    dst = (_endpoint_view(destination_before), _endpoint_view(destination_after))
    evidence['source'] = {'before': src[0], 'after': src[1]}
    evidence['destination'] = {'before': dst[0], 'after': dst[1]}

    src_id = src[0]['identity']['physical_id']
    dst_id = dst[0]['identity']['physical_id']
    if not isinstance(src_id, str) or not isinstance(dst_id, str):
        return refuse('An endpoint has no reported physical identity, so its counters '
                      'cannot be attributed to a device', 'REFUSED_UNBOUND_ENDPOINT_IDENTITY')
    if not gate('DISTINCT_PHYSICAL_ENDPOINTS', src_id != dst_id,
                {'source': src_id, 'destination': dst_id}):
        return refuse(f'Both endpoints are the same physical device {src_id}; a self-copy '
                      'cannot demonstrate cross-device residency',
                      'REFUSED_SINGLE_PHYSICAL_ENDPOINT')
    for label, endpoint in (('source', src[0]), ('destination', dst[0])):
        confidence = endpoint['identity']['identity_confidence']
        if confidence == 'EPHEMERAL_RUNTIME_ID':
            return refuse(f'{label} identity is an ephemeral runtime id, not a physical '
                          'device identity', 'REFUSED_EPHEMERAL_ENDPOINT_IDENTITY')

    for label, endpoint in (('source', src[0]), ('destination', dst[0])):
        if not gate(f'{label.upper()}_DEDICATED_COUNTER_SAMPLED',
                    endpoint['dedicated']['status'] == SAMPLED
                    and endpoint['dedicated']['used_bytes'] is not None,
                    endpoint['dedicated']):
            return refuse(f'{label} has no sampled dedicated-VRAM usage counter: '
                          f"{endpoint['dedicated']['reason']}",
                          'REFUSED_NO_DEDICATED_USAGE_COUNTER')

    for label, endpoint, snapshots in (('source', src[0], source_after),
                                       ('destination', dst[0], destination_after)):
        status, block = _calibration_status(snapshots, calibration)
        if not gate(f'{label.upper()}_COUNTER_CALIBRATED', status == 'TRACKED',
                    {'status': status, 'calibration': block}):
            reason = block.get('reason') if isinstance(block, dict) else None
            return refuse(f'{label} dedicated counter was never shown to track a known '
                          f'allocation (calibration status {status}'
                          + (f': {reason}' if reason else '') + ')',
                          'REFUSED_COUNTER_RESPONSIVENESS_NOT_CALIBRATED')

    for label, endpoint in (('source', src[0]), ('destination', dst[0])):
        resolution = endpoint['dedicated']['resolution_bytes']
        if not isinstance(resolution, int) or resolution * 2 > transfer_bytes:
            return refuse(f'{label} counter resolution {resolution} bytes cannot resolve a '
                          f'{transfer_bytes} byte payload', 'REFUSED_COUNTER_RESOLUTION_TOO_COARSE')

    def delta(pair, kind):
        before, after = pair[0][kind]['used_bytes'], pair[1][kind]['used_bytes']
        if before is None or after is None:
            return None
        return after - before

    src_dedicated = delta(src, 'dedicated')
    dst_dedicated = delta(dst, 'dedicated')
    src_shared = delta(src, 'shared')
    dst_shared = delta(dst, 'shared')
    observed = {'transfer_bytes': transfer_bytes,
                'source_dedicated_delta_bytes': src_dedicated,
                'destination_dedicated_delta_bytes': dst_dedicated,
                'source_shared_delta_bytes': src_shared,
                'destination_shared_delta_bytes': dst_shared}
    evidence['observed'] = observed

    src_tol = _tolerance_bytes(transfer_bytes, src[0]['dedicated']['resolution_bytes'], tolerance)
    dst_tol = _tolerance_bytes(transfer_bytes, dst[0]['dedicated']['resolution_bytes'], tolerance)
    shared_tol = max(_tolerance_bytes(0, None, tolerance), src_tol, dst_tol)
    evidence['tolerance_bytes'] = {'source_dedicated': src_tol,
                                   'destination_dedicated': dst_tol,
                                   'shared': shared_tol}

    shared_growth = [(name, value) for name, value in
                     (('source', src_shared), ('destination', dst_shared))
                     if value is not None and value > shared_tol]
    dedicated_moved = any(value is not None and abs(value) > shared_tol
                          for value in (src_dedicated, dst_dedicated))
    if shared_growth:
        detail = ', '.join(f'{name} shared +{value} bytes' for name, value in shared_growth)
        gate('SHARED_MEMORY_FLAT', False, detail)
        return ResidencyDelta(
            INVOLVED_SHARED_HOST_MEMORY,
            f'Host shared memory grew during the transfer ({detail}), so system memory '
            'was in the data path', refusal=None, evidence=evidence,
            transfer_bytes=transfer_bytes)
    gate('SHARED_MEMORY_FLAT', True,
         {'source_shared_delta_bytes': src_shared,
          'destination_shared_delta_bytes': dst_shared, 'tolerance_bytes': shared_tol})

    if src_dedicated is None or dst_dedicated is None:
        return refuse('A dedicated counter disappeared between the before and after '
                      'snapshots, so no delta exists', 'REFUSED_COUNTER_LOST_BETWEEN_SAMPLES')
    if not dedicated_moved:
        gate('DEDICATED_DELTA_PRESENT', False, observed)
        return ResidencyDelta(
            NO_MEASURABLE_DELTA,
            f'Neither endpoint dedicated counter moved by more than {shared_tol} bytes '
            f'for a {transfer_bytes} byte transfer', refusal=None, evidence=evidence,
            transfer_bytes=transfer_bytes)

    src_ok = -(transfer_bytes + src_tol) <= src_dedicated <= -(transfer_bytes - src_tol)
    dst_ok = (transfer_bytes - dst_tol) <= dst_dedicated <= (transfer_bytes + dst_tol)
    if src_ok and dst_ok:
        for label, endpoint, snapshots in (('source', src[0], source_after),
                                           ('destination', dst[0], destination_after)):
            if _endpoint_view(snapshots)['shared']['status'] != SAMPLED:
                gate('SHARED_COUNTER_PRESENT_FOR_PASS', False, label)
                return ResidencyDelta(
                    NO_MEASURABLE_DELTA,
                    f'Dedicated deltas matched the payload but the {label} shared-memory '
                    'counter is unavailable, so a host bounce cannot be excluded',
                    refusal='REFUSED_SHARED_COUNTER_UNAVAILABLE_FOR_PASS',
                    evidence=evidence, transfer_bytes=transfer_bytes)
        gate('DEDICATED_DELTA_MATCHES_PAYLOAD', True, observed)
        return ResidencyDelta(
            DEDICATED_TO_DEDICATED,
            f'Source dedicated VRAM fell by {-src_dedicated} bytes and destination '
            f'dedicated VRAM rose by {dst_dedicated} bytes for a {transfer_bytes} byte '
            'transfer, with both shared counters flat',
            refusal=None, evidence=evidence, transfer_bytes=transfer_bytes)

    gate('DEDICATED_DELTA_MATCHES_PAYLOAD', False,
         dict(observed, source_matched=src_ok, destination_matched=dst_ok,
              source_tolerance_bytes=src_tol, destination_tolerance_bytes=dst_tol))
    return ResidencyDelta(
        NO_MEASURABLE_DELTA,
        f'Dedicated counters moved (source {src_dedicated:+d}, destination {dst_dedicated:+d}) '
        f'but not by the {transfer_bytes} byte payload within tolerance, so the counters do '
        'not account for this transfer', refusal=None, evidence=evidence,
        transfer_bytes=transfer_bytes)


# --------------------------------------------------------------------------
# payload integrity
# --------------------------------------------------------------------------

def verify_payload(expected, actual):
    """Checksum plus element comparison; a success code is never a certificate."""
    def as_bytes(value):
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        if hasattr(value, 'tobytes'):
            return value.tobytes()
        raise ResidencyRefused('Payload must be bytes or a numpy array')

    expected_bytes, actual_bytes = as_bytes(expected), as_bytes(actual)
    expected_hash = hashlib.sha256(expected_bytes).hexdigest()
    actual_hash = hashlib.sha256(actual_bytes).hexdigest()
    mismatched = 0
    first_index = None
    if len(expected_bytes) == len(actual_bytes):
        for index, (left, right) in enumerate(zip(expected_bytes, actual_bytes)):
            if left != right:
                mismatched += 1
                if first_index is None:
                    first_index = index
    else:
        mismatched = max(len(expected_bytes), len(actual_bytes))
    return {
        'status': PASS if (expected_hash == actual_hash and mismatched == 0
                           and len(expected_bytes) == len(actual_bytes)) else FAIL,
        'expected_sha256': expected_hash, 'actual_sha256': actual_hash,
        'byte_length': len(actual_bytes), 'expected_byte_length': len(expected_bytes),
        'mismatched_bytes': mismatched, 'first_mismatch_byte_index': first_index,
        'hash_match': expected_hash == actual_hash,
    }


# --------------------------------------------------------------------------
# calibration and self test
# --------------------------------------------------------------------------

_TOUCH_KERNEL = r"""
__kernel void residency_touch(__global unsigned int *payload, const unsigned int count) {
    const unsigned int index = get_global_id(0);
    if (index < count) {
        payload[index] = payload[index] ^ 0x5A5A5A5Au;
    }
}
"""


def _calibrate_counter(before, during, released, expected_bytes, view):
    """Did the identity-bound dedicated counter track a known-size allocation?

    TRACKED needs all three of: the counter rose by the payload size within
    tolerance, it did not rise by materially more, and it returned to baseline
    when the allocation was released.  A counter that only moves on context
    creation, or that never returns, cannot attribute bytes to a transfer.
    """
    endpoints = [_endpoint_view(snapshot)['dedicated'] for snapshot in (before, during, released)]
    base = {'physical_id': view['identity']['physical_id'], 'expected_bytes': expected_bytes,
            'counter_source': endpoints[0].get('source')}
    if any(item.get('status') != SAMPLED or item.get('used_bytes') is None
           for item in endpoints):
        return base | {'status': NOT_CHECKED, 'observed_bytes': None,
                       'release_delta_bytes': None, 'returned_to_baseline': None,
                       'reason': 'REFUSED_DEDICATED_COUNTER_NOT_SAMPLED'}
    resolution = endpoints[0].get('resolution_bytes') or 0
    tolerance = max(resolution * 2, 2 * MIB, int(0.02 * expected_bytes))
    observed = endpoints[1]['used_bytes'] - endpoints[0]['used_bytes']
    release_delta = endpoints[2]['used_bytes'] - endpoints[0]['used_bytes']
    failures = []
    if observed < expected_bytes - tolerance:
        failures.append(f'UNDERRAN_PAYLOAD: rose {observed} bytes for {expected_bytes}')
    if observed > expected_bytes + tolerance:
        failures.append(f'OVERRAN_PAYLOAD: rose {observed} bytes for {expected_bytes}')
    if abs(release_delta) > tolerance:
        failures.append(f'DID_NOT_RETURN_TO_BASELINE: {release_delta:+d} bytes after release')
    tracked = not failures
    return base | {'status': 'TRACKED' if tracked else 'NOT_TRACKED',
                   'observed_bytes': observed, 'release_delta_bytes': release_delta,
                   'returned_to_baseline': bool(abs(release_delta) <= tolerance),
                   'resolution_bytes': resolution, 'tolerance_bytes': tolerance,
                   'failed_conditions': failures,
                   'reason': None if tracked else '; '.join(failures)}


def _enumerate(executor):
    try:
        records = executor.enumerate_opencl_devices()
    except executor.RuntimeUnavailable as exc:
        raise ResidencyUnavailable(str(exc)) from exc
    except Exception as exc:
        raise ResidencyUnavailable(
            f'REFUSED_ENUMERATION_FAILED: {type(exc).__name__}: {exc}') from exc
    if not isinstance(records, list) or not records:
        raise ResidencyUnavailable('REFUSED_NO_QUALIFIED_OPENCL_GPU_DEVICES')
    return records


def _population_hint(records):
    counts = {}
    for record in records:
        counts[record.get('vendor_key')] = counts.get(record.get('vendor_key'), 0) + 1
    return {'nvidia_opencl_devices': counts.get('NVIDIA', 0),
            'amd_opencl_devices': counts.get('AMD', 0),
            'intel_opencl_devices': counts.get('Intel', 0),
            'total_opencl_devices': len(records)}


def _discrete(records):
    return [record for record in records
            if record.get('memory_classification') == DEVICE_LOCAL]


def _receipt(status, reason, verdict, **extra):
    receipt = {
        'control': 'R_RESIDENCY',
        'status': status,
        'reason': reason,
        'verdict': verdict,
        'pass_claimed': False,
        'labels': list(RESULT_LABELS),
        'timestamp_utc': _now_utc().isoformat(),
        'python': sys.version.split()[0],
        'platform': sys.platform,
    }
    receipt.update(extra)
    return receipt


def _calibrate_device(record, size_bytes, hint, host_counters):
    """Prove one device's dedicated counter tracks a known-size allocation.

    The context and queue are created first so that per-context driver overhead
    sits outside the measurement window; only the payload buffer is allocated,
    sampled and released inside it.
    """
    cl = _load_opencl()
    context = cl.Context([record['device']])
    queue = cl.CommandQueue(context)
    try:
        queue.finish()
        before = sample_memory(record, population_hint=hint, host_counters=host_counters)
        buffer = cl.Buffer(context, cl.mem_flags.READ_WRITE, size=size_bytes)
        queue.finish()
        during = sample_memory(record, population_hint=hint, host_counters=host_counters)
        buffer.release()
        queue.finish()
        released = sample_memory(record, population_hint=hint, host_counters=host_counters)
    finally:
        for resource in (queue, context):
            try:
                resource.release()
            except Exception:
                pass
    return _calibrate_counter(before, during, released, size_bytes, _endpoint_view(before))


def _self_test_cross_device(discrete, transport, transport_kwargs, size_bytes, hint,
                            host_counters):
    """Two or more discrete devices plus a caller-supplied transport: measure it."""
    source, destination = discrete[0], discrete[1]
    source_calibration = _calibrate_device(source, size_bytes, hint, host_counters)
    destination_calibration = _calibrate_device(destination, size_bytes, hint, host_counters)
    receipt, code = measure_boundary(
        transport, source_device=source, destination_device=destination,
        transfer_bytes=size_bytes, host_counters=host_counters,
        forward_kwargs=transport_kwargs,
        calibration={'source': source_calibration, 'destination': destination_calibration})
    receipt['mode'] = 'CROSS_DEVICE_SELF_TEST'
    receipt['population'] = hint
    receipt['requested_bytes'] = size_bytes
    receipt['device_count'] = hint.get('total_opencl_devices')
    receipt['discrete_device_count'] = len(discrete)
    receipt['calibration'] = {'source': source_calibration,
                              'destination': destination_calibration}
    receipt['transport'] = 'CALLER_SUPPLIED'
    if receipt['status'] == PASS and receipt['verdict'] != DEDICATED_TO_DEDICATED:
        receipt['status'] = FAIL
        receipt['reason'] = 'A pass status was set without a dedicated-to-dedicated verdict'
        code = 1
    return receipt, code


def self_test(*, size_mib=DEFAULT_SELF_TEST_MIB, host_counters=True, executor=None,
              transport=None, transport_kwargs=None):
    """Prove the measurement apparatus on the installed devices, honestly.

    Allocates a device buffer, writes a known pattern, touches it with a real
    kernel, reads it back and verifies the checksum, then samples memory
    before, during and after.  A single discrete GPU cannot produce a directed
    pair, so the residency verdict here is UNMEASURABLE_ON_THIS_PLATFORM and
    the receipt says so rather than reporting a pass.

    `transport` is the only route to a measured verdict: it must be a callable
    that moves `size_mib` from one discrete device to another.  With two or
    more discrete devices and a supplied transport, both endpoints are
    calibrated and the real cross-device delta is computed.
    """
    size_bytes = _positive_int(size_mib, 'size_mib') * MIB
    executor = executor or _executor_module()
    records = _enumerate(executor)
    hint = _population_hint(records)
    discrete = _discrete(records)

    receipt = _receipt(NOT_CHECKED, 'Not evaluated', UNMEASURABLE_ON_THIS_PLATFORM,
                       population=hint, requested_bytes=size_bytes,
                       device_count=len(records), discrete_device_count=len(discrete))
    if not discrete:
        receipt['status'] = 'REFUSED'
        receipt['reason'] = ('REFUSED_NO_DISCRETE_DEVICE_WITH_DEDICATED_VRAM: every '
                             'enumerated GPU reports host_unified memory')
        receipt['devices'] = [{k: v for k, v in record.items() if k != 'device'}
                              for record in records]
        return receipt, 2
    if len(discrete) < 2:
        receipt['reason'] = ('SINGLE_DISCRETE_DEVICE_CANNOT_DEMONSTRATE_CROSS_DEVICE_'
                             'RESIDENCY: zero directed pairs constructible')
    elif transport is not None:
        return _self_test_cross_device(discrete, transport, transport_kwargs or {},
                                       size_bytes, hint, host_counters)

    target = discrete[0]
    view = _device_view(target)
    cl = _load_opencl()
    try:
        import numpy as np
    except Exception as exc:
        raise ResidencyUnavailable(f'REFUSED_NUMPY_UNAVAILABLE: {exc}') from exc

    count = size_bytes // 4
    payload = np.ascontiguousarray(
        (np.arange(count, dtype=np.uint64) * np.uint64(2654435761)
         % np.uint64(2**32)).astype(np.uint32))
    device_execution = {'status': NOT_CHECKED, 'reason': None}
    # The context and queue are created before the first sample so that
    # per-context driver overhead is outside the calibration window.
    context = cl.Context([target['device']])
    queue = cl.CommandQueue(context)
    resources = []
    try:
        queue.finish()
        before = sample_memory(target, population_hint=hint, host_counters=host_counters)
        buffer = cl.Buffer(context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR,
                           hostbuf=payload)
        queue.finish()
        during = sample_memory(target, population_hint=hint, host_counters=host_counters)

        expected = payload ^ np.uint32(0x5A5A5A5A)
        try:
            program = cl.Program(context, _TOUCH_KERNEL).build()
            resources.append(program)
            program.residency_touch(queue, (count,), None, buffer, np.uint32(count)).wait()
            queue.finish()
            device_execution = {'status': PASS, 'reason': None,
                                'kernel': 'residency_touch', 'elements': int(count)}
        except Exception as exc:
            device_execution = {'status': NOT_CHECKED,
                                'reason': f'REFUSED_KERNEL_EXECUTION_FAILED: '
                                          f'{type(exc).__name__}: {exc}'}
            expected = payload

        readback = np.empty(count, dtype=np.uint32)
        cl.enqueue_copy(queue, readback, buffer).wait()
        queue.finish()
        checksum = verify_payload(expected, readback)
        checksum['device_execution'] = device_execution

        buffer.release()
        queue.finish()
        after_release = sample_memory(target, population_hint=hint,
                                      host_counters=host_counters)
    finally:
        for resource in reversed(resources):
            try:
                resource.release()
            except Exception:
                pass
        for resource in (queue, context):
            try:
                resource.release()
            except Exception:
                pass

    calibration = _calibrate_counter(before, during, after_release, size_bytes,
                                     _endpoint_view(before))

    endpoint = _endpoint_view(before)
    if checksum['status'] != PASS:
        return _receipt(FAIL, 'Device buffer round trip did not reproduce the written '
                              'pattern, so no residency claim is possible',
                        UNMEASURABLE_ON_THIS_PLATFORM, population=hint,
                        requested_bytes=size_bytes, device_count=len(records),
                        discrete_device_count=len(discrete), checksum=checksum,
                        calibration={'source': calibration},
                        samples={'before': before, 'during': during,
                                 'after_release': after_release},
                        endpoint_view=endpoint), 1

    residency = compute_residency_delta(before, during, before, during, size_bytes,
                                        calibration={'source': calibration})
    reasons = []
    if len(discrete) < 2:
        reasons.append('SINGLE_DISCRETE_DEVICE: this host has one GPU with dedicated '
                       'VRAM, so no directed pair and no cross-device residency delta '
                       'exists to measure')
    else:
        reasons.append('NO_PEER_TRANSPORT_SUPPLIED: two or more discrete devices were '
                       'enumerated, but self_test only exercises one device at a time; a '
                       'cross-device verdict needs a peer transport passed to '
                       'measure_boundary, and none was supplied')
    if residency.verdict == UNMEASURABLE_ON_THIS_PLATFORM:
        reasons.append(residency.reason)
    if calibration['status'] != 'TRACKED':
        reasons.append(f"COUNTER_NOT_CALIBRATED: the dedicated counter moved "
                       f"{calibration.get('observed_bytes')} bytes for a {size_bytes} byte "
                       f"allocation ({calibration['status']})")
    reasons.append('Checksum PASS proves the payload round tripped; it is NOT residency '
                   'evidence and is not a peer-access result')

    status = {DEDICATED_TO_DEDICATED: PASS,
              INVOLVED_SHARED_HOST_MEMORY: FAIL,
              NO_MEASURABLE_DELTA: NOT_CHECKED,
              UNMEASURABLE_ON_THIS_PLATFORM: NOT_CHECKED}[residency.verdict]
    if status == PASS:
        # Unreachable by construction: the source and destination below are one
        # device.  Held as a guard so a future edit cannot turn a self-copy
        # into a residency pass.
        status = FAIL
        reasons.append('REFUSED_SELF_COPY_REPORTED_AS_CROSS_DEVICE: source and '
                       'destination were the same physical device')
    code = {PASS: 0, FAIL: 1}.get(status, 2)
    return _receipt(status, '; '.join(reasons), residency.verdict,
                    mode='SINGLE_DEVICE_SELF_TEST',
                    population=hint, requested_bytes=size_bytes,
                    device_count=len(records), discrete_device_count=len(discrete),
                    device={'runtime_id': view.get('runtime_id'),
                            'physical_id': view.get('physical_id'),
                            'identity_confidence': view.get('identity_confidence'),
                            'vendor_key': view.get('vendor_key'), 'name': view.get('name'),
                            'memory_classification': view.get('memory_classification')},
                    checksum=checksum, calibration={'source': calibration},
                    residency=residency.as_dict(),
                    samples={'before': before, 'during': during, 'after_release': after_release},
                    endpoint_view=endpoint,
                    what_this_proves=[
                        'The device accepted a real allocation, executed a kernel over it '
                        'and returned the exact bytes written',
                        'Every memory counter obtainable for this device was sampled and '
                        'recorded, with unsupported ones marked UNAVAILABLE',
                        'The residency decision logic ran against real before/after counters',
                    ],
                    what_this_does_not_prove=[
                        'Direct peer access between two physical GPUs',
                        'That any payload resided in dedicated VRAM rather than host memory',
                        'Bandwidth, capacity aggregation, or any performance claim',
                    ]), code


# --------------------------------------------------------------------------
# boundary hook
# --------------------------------------------------------------------------

def resolve_boundary_forwarder(executor=None):
    """Locate the executor's boundary forwarder without inventing one."""
    executor = executor or _executor_module()
    for name in BOUNDARY_FORWARDER_CANDIDATES:
        candidate = getattr(executor, name, None)
        if callable(candidate):
            return candidate, f'opencl_executor.{name}', None
    observed = sorted(name for name in dir(executor) if 'boundary' in name.lower())
    return None, None, {
        'reason': 'REFUSED_MISSING_FORWARD_BOUNDARY',
        'detail': ('The pinned opencl_executor exposes no forward_boundary callable; it '
                   'forwards each context boundary inline inside _execute_gpu. Supply a '
                   'forwarder explicitly rather than wrapping a symbol that does not exist.'),
        'candidates_searched': list(BOUNDARY_FORWARDER_CANDIDATES),
        'boundary_symbols_observed': observed,
        'executor_entry_points_observed': sorted(
            name for name in ('main', '_main', '_child_main', '_execute_gpu',
                              'enumerate_opencl_devices', 'select_devices')
            if callable(getattr(executor, name, None))),
    }


def measure_boundary(forward_fn=None, *, source_device=None, destination_device=None,
                     transfer_bytes=None, calibration=None, executor=None,
                     host_counters=True, forward_kwargs=None, tolerance=None):
    """Sample residency around one boundary forward and return both results together.

    The residency delta is returned alongside whatever the executor's forwarder
    returned, so the two are recorded as one receipt.  Nothing is claimed when
    the forwarder, the endpoints or the transfer size are missing.
    """
    forward_kwargs = dict(forward_kwargs or {})
    executor_result = None
    resolved_name = None
    try:
        if forward_fn is None:
            forward_fn, resolved_name, refusal = resolve_boundary_forwarder(executor)
            if forward_fn is None:
                return _receipt(NOT_CHECKED, refusal['detail'],
                                UNMEASURABLE_ON_THIS_PLATFORM,
                                refusal=refusal['reason'], forwarder=None,
                                forwarder_resolution=refusal,
                                residency=ResidencyDelta(
                                    UNMEASURABLE_ON_THIS_PLATFORM, refusal['detail'],
                                    refusal=refusal['reason']).as_dict()), 2
        else:
            resolved_name = 'caller_supplied'
        if source_device is None or destination_device is None:
            raise ResidencyRefused('REFUSED_ENDPOINTS_NOT_SUPPLIED: both a source and a '
                                   'destination device record are required')
        transfer_bytes = _positive_int(transfer_bytes, 'transfer_bytes')

        hint = None
        source_before = sample_memory(source_device, population_hint=hint,
                                      host_counters=host_counters)
        destination_before = sample_memory(destination_device, population_hint=hint,
                                           host_counters=host_counters)
        executor_result = forward_fn(**forward_kwargs)
        source_after = sample_memory(source_device, population_hint=hint,
                                     host_counters=host_counters)
        destination_after = sample_memory(destination_device, population_hint=hint,
                                          host_counters=host_counters)
    except ResidencyRefused as exc:
        return _receipt('REFUSED', str(exc), UNMEASURABLE_ON_THIS_PLATFORM,
                        forwarder=resolved_name if forward_fn else None,
                        executor_result=executor_result), 2
    except ResidencyUnavailable as exc:
        return _receipt(NOT_CHECKED, str(exc), UNMEASURABLE_ON_THIS_PLATFORM,
                        forwarder=resolved_name if forward_fn else None,
                        executor_result=executor_result), 2
    except Exception as exc:
        return _receipt(FAIL, f'Boundary forwarder raised {type(exc).__name__}: {exc}',
                        UNMEASURABLE_ON_THIS_PLATFORM,
                        forwarder=resolved_name if forward_fn else None,
                        executor_result=executor_result), 1

    residency = compute_residency_delta(
        source_before, source_after, destination_before, destination_after,
        transfer_bytes, calibration=calibration, tolerance=tolerance)
    status = {DEDICATED_TO_DEDICATED: PASS,
              INVOLVED_SHARED_HOST_MEMORY: FAIL,
              NO_MEASURABLE_DELTA: NOT_CHECKED,
              UNMEASURABLE_ON_THIS_PLATFORM: NOT_CHECKED}[residency.verdict]
    code = {PASS: 0, FAIL: 1}.get(status, 2)
    return _receipt(status, residency.reason, residency.verdict,
                    pass_claimed=residency.verdict == DEDICATED_TO_DEDICATED,
                    forwarder=resolved_name, transfer_bytes=transfer_bytes,
                    executor_result=executor_result, residency=residency.as_dict(),
                    samples={'source_before': source_before, 'source_after': source_after,
                             'destination_before': destination_before,
                             'destination_after': destination_after}), code


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _emit(receipt, code, output_path=None):
    try:
        serialized = json.dumps(receipt, indent=2, allow_nan=False, default=str) + '\n'
    except (TypeError, ValueError) as exc:
        code = 1
        serialized = json.dumps(_receipt(FAIL, f'Receipt serialization failed: {exc}',
                                         UNMEASURABLE_ON_THIS_PLATFORM)) + '\n'
    if len(serialized.encode('utf-8')) > MAX_RESULT_BYTES:
        code = 1
        serialized = json.dumps(_receipt(
            FAIL, 'Receipt exceeds the 256 KiB output bound',
            UNMEASURABLE_ON_THIS_PLATFORM)) + '\n'
    if output_path:
        target = Path(output_path)
        try:
            executor = _executor_module()
            executor.atomic_write_json(target, serialized)
        except ResidencyUnavailable:
            try:
                if not target.parent.exists():
                    raise OSError(f'Output directory does not exist: {target.parent}')
                target.write_text(serialized, encoding='utf-8')
            except OSError as exc:
                code = 1
                serialized = json.dumps(_receipt(FAIL, f'Receipt write failed: {exc}',
                                                 UNMEASURABLE_ON_THIS_PLATFORM)) + '\n'
        except OSError as exc:
            code = 1
            serialized = json.dumps(_receipt(FAIL, f'Receipt write failed: {exc}',
                                             UNMEASURABLE_ON_THIS_PLATFORM)) + '\n'
    sys.stdout.write(serialized)
    return code


def _main(argv=None):
    parser = argparse.ArgumentParser(
        description='Control R residency measurement (doc 11 section 5)',
        epilog='Exit 0 means a clean self-test. Exit 2 means this platform cannot '
               'support the measurement, which is the expected honest result on a '
               'single-GPU host and is NOT an error. Exit 1 means a real failure.')
    parser.add_argument('--self-test', action='store_true',
                        help='Allocate, touch, verify and sample memory on the installed GPU')
    parser.add_argument('--json', type=Path, default=None,
                        help='Atomically write the bounded JSON receipt to this path')
    parser.add_argument('--size-mib', type=int, default=DEFAULT_SELF_TEST_MIB,
                        help=f'Self-test payload size in MiB (default {DEFAULT_SELF_TEST_MIB})')
    parser.add_argument('--no-host-counters', action='store_true',
                        help='Skip nvidia-smi and Windows PDH sampling (recorded as NOT_CHECKED)')
    parser.add_argument('--measure-boundary', action='store_true',
                        help='Attempt to wrap the executor boundary forwarder')
    args = parser.parse_args(argv)

    if not args.self_test and not args.measure_boundary:
        return _emit(_receipt(
            'REFUSED',
            'REFUSED_NO_MODE_SELECTED: pass --self-test or --measure-boundary',
            UNMEASURABLE_ON_THIS_PLATFORM), 2, args.json)

    try:
        if args.measure_boundary:
            receipt, code = measure_boundary(host_counters=not args.no_host_counters)
            return _emit(receipt, code, args.json)
        receipt, code = self_test(size_mib=args.size_mib,
                                  host_counters=not args.no_host_counters)
        return _emit(receipt, code, args.json)
    except ResidencyRefused as exc:
        return _emit(_receipt('REFUSED', str(exc), UNMEASURABLE_ON_THIS_PLATFORM), 2, args.json)
    except ResidencyUnavailable as exc:
        return _emit(_receipt(NOT_CHECKED, str(exc), UNMEASURABLE_ON_THIS_PLATFORM), 2, args.json)
    except Exception as exc:
        return _emit(_receipt(FAIL, f'{type(exc).__name__}: {exc}',
                              UNMEASURABLE_ON_THIS_PLATFORM), 1, args.json)


def main(argv=None):
    return _main(argv)


if __name__ == '__main__':
    raise SystemExit(main())
