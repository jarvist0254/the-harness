#!/usr/bin/env python3
"""Nightly verification job for The Harness / J-Link (achievement target T7).

Runs the four standing checks as subprocesses, parses the meaningful result out of
each, records a version pin block, and publishes a dated receipt:

    records/nightly/<UTC yyyyMMddTHHmmssZ>/receipt.json
    records/nightly/<UTC yyyyMMddTHHmmssZ>/SUMMARY.md

Exit codes
----------
    0  every check PASSed
    1  one or more checks FAILED (loud regression signal, T7 criterion 3)
    2  the job itself could not fully run (a check command was missing, a probe
       errored, or the receipt could not be written)

Precedence: a FAIL outranks an UNAVAILABLE, because a real regression is the more
actionable signal. If nothing failed but something could not run, the exit code is
2 so a broken job is never mistaken for a healthy one.

Stdlib only. No pip, no third-party imports. Every Python subprocess is run with
``-B`` so no bytecode caches are written into the repository.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = '1.0'
TARGET = 'T7'
TAIL_LINES = 20
DEFAULT_TIMEOUT_SECONDS = 1800
PROBE_TIMEOUT_SECONDS = 60

# Packages whose pinned version matters to the compute stack. Recorded via
# importlib.metadata; a missing distribution is 'UNAVAILABLE', never an exception.
PINNED_PACKAGES = ('numpy', 'pyopencl', 'pytest')

# Statuses and how they map onto an exit code.
REGRESSION_STATUSES = frozenset({'FAIL', 'TIMEOUT'})
INFRA_STATUSES = frozenset({'UNAVAILABLE', 'ERROR'})


# --------------------------------------------------------------------------- #
# Check definitions
# --------------------------------------------------------------------------- #

def repo_root_default() -> Path:
    """Repository root, derived from this file's location (scripts/ -> repo)."""
    return Path(__file__).resolve().parents[1]


# Project convention: earlier manifests stay immutable and each re-pin adds a new
# records/ADAPTATION_SHA256_<UTC>.json that chains prior_manifest. The newest
# manifest is therefore the last one by filename sort, which is also chronological
# because the stamp is yyyyMMdd[_HHmmssZ].
MANIFEST_GLOB = 'ADAPTATION_SHA256_*.json'


def resolve_manifest(repo_root, override: str | None = None) -> tuple[Path | None, dict]:
    """Pick the artifact manifest to verify.

    Returns ``(path_or_None, info)``. A missing manifest is never an exception: the
    caller records ``info['reason']`` and the check becomes UNAVAILABLE (exit 2),
    because a nightly that silently skipped its integrity gate would be worse than
    one that reports itself broken.
    """
    repo_root = Path(repo_root)
    records = repo_root / 'records'

    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = (repo_root / candidate).resolve()
        info = {'mode': 'override', 'requested': str(override), 'candidate': str(candidate)}
        if candidate.is_file():
            info.update({'status': 'OK', 'resolved': str(candidate),
                         'resolved_name': candidate.name})
            return candidate, info
        info.update({'status': 'UNAVAILABLE',
                     'reason': '--manifest path does not exist: %s' % candidate})
        return None, info

    info = {'mode': 'newest_by_filename_sort',
            'search': '%s%s%s' % (records, os.sep, MANIFEST_GLOB)}
    if not records.is_dir():
        info.update({'status': 'UNAVAILABLE',
                     'reason': 'records directory not found: %s' % records})
        return None, info
    candidates = sorted((p for p in records.glob(MANIFEST_GLOB) if p.is_file()),
                        key=lambda p: p.name)
    info['candidate_count'] = len(candidates)
    info['candidates'] = [p.name for p in candidates]
    if not candidates:
        info.update({'status': 'UNAVAILABLE',
                     'reason': 'no %s found under %s' % (MANIFEST_GLOB, records)})
        return None, info
    chosen = candidates[-1]
    info.update({'status': 'OK', 'resolved': str(chosen), 'resolved_name': chosen.name})
    return chosen, info


def build_checks(repo_root: Path, python_exe: str,
                 manifest: str | None = None) -> list[dict]:
    """The four standing T7 checks. Pure data, so tests can inject fakes."""
    repo_root = Path(repo_root)
    py = str(python_exe)
    manifest_path, manifest_info = resolve_manifest(repo_root, manifest)

    manifest_check = {
        'name': 'artifact_manifest_integrity',
        'cmd': [],
        'cwd': str(repo_root),
        'parser': 'manifest_json',
        'expect': {'min_checked': 1},
        'manifest_resolution': manifest_info,
    }
    if manifest_path is None:
        manifest_check['skip_reason'] = manifest_info.get('reason', 'manifest unresolved')
    else:
        manifest_check['cmd'] = [py, '-B',
                                 str(repo_root / 'scripts' / 'verify_adaptation.py'),
                                 str(manifest_path)]

    return [
        {
            'name': 'j_link_unittest_suite',
            'cmd': [py, '-B', '-m', 'unittest', 'discover',
                    '-s', str(repo_root / 'j_link' / 'tests')],
            'cwd': str(repo_root),
            'parser': 'unittest',
            'expect': {'min_tests': 1},
        },
        {
            'name': 'cad_unittest_suite',
            'cmd': [py, '-B', '-m', 'unittest', 'discover',
                    '-s', str(repo_root / 'cad' / 'tests')],
            'cwd': str(repo_root),
            'parser': 'unittest',
            'expect': {'min_tests': 1},
        },
        {
            'name': 'j_link_planner_mixed',
            'cmd': [py, '-B', str(repo_root / 'j_link' / 'planner.py'),
                    str(repo_root / 'j_link' / 'examples' / 'mixed.json')],
            'cwd': str(repo_root),
            'parser': 'json_status',
            'expect': {'statuses': ['PLANNED_NOT_ALLOCATED']},
        },
        manifest_check,
    ]


# --------------------------------------------------------------------------- #
# Output parsing
# --------------------------------------------------------------------------- #

_RAN_RE = re.compile(r'^Ran (\d+) tests?\b', re.MULTILINE)


def _tail(text: str, lines: int = TAIL_LINES) -> list[str]:
    """Last ``lines`` non-empty-preserving lines of text."""
    if not text:
        return []
    parts = text.splitlines()
    return parts[-lines:]


def _extract_json(text: str):
    """Parse a JSON object out of text, tolerating leading/trailing noise."""
    if not text:
        return None
    text = text.lstrip('\ufeff').strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    start = text.find('{')
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(text[start:])
        return obj
    except (ValueError, TypeError):
        return None


def parse_unittest(stdout: str, stderr: str, expect: dict) -> dict:
    """Pull the test count and OK/FAILED verdict out of unittest output.

    unittest writes its summary to stderr, but some harnesses redirect it, so both
    streams are searched.
    """
    blob = (stderr or '') + '\n' + (stdout or '')
    counts = [int(m.group(1)) for m in _RAN_RE.finditer(blob)]
    ran = counts[-1] if counts else None
    verdict = None
    for raw in blob.splitlines():
        line = raw.strip()
        if line == 'OK' or line.startswith('OK ('):
            verdict = 'OK'
        elif line.startswith('FAILED'):
            verdict = line
    min_tests = int(expect.get('min_tests', 1))
    parsed = {
        'tests_ran': ran,
        'verdict': verdict,
        'expected_verdict': 'OK',
        'min_tests': min_tests,
    }
    ok = (verdict == 'OK' and ran is not None and ran >= min_tests)
    parsed['criteria_met'] = ok
    if not ok:
        if verdict is None:
            parsed['reason'] = 'no OK/FAILED summary line found in output'
        elif ran is None:
            parsed['reason'] = 'no "Ran N tests" line found in output'
        else:
            parsed['reason'] = 'verdict was %r' % (verdict,)
    return parsed


def parse_json_status(stdout: str, stderr: str, expect: dict) -> dict:
    """Pull the JSON ``status`` field out of the planner's stdout."""
    payload = _extract_json(stdout)
    statuses = list(expect.get('statuses') or [])
    if not isinstance(payload, dict):
        return {
            'status': None, 'expected_statuses': statuses,
            'criteria_met': False, 'reason': 'stdout was not parseable JSON',
        }
    status = payload.get('status')
    parsed = {
        'status': status,
        'expected_statuses': statuses,
        'hypothetical': payload.get('hypothetical'),
        'device_count': len(payload.get('devices') or []),
    }
    ok = bool(statuses) and status in statuses
    parsed['criteria_met'] = ok
    if not ok:
        parsed['reason'] = 'status %r not in %r' % (status, statuses)
    return parsed


def parse_manifest_json(stdout: str, stderr: str, expect: dict) -> dict:
    """Pull ``checked`` / ``failures`` out of the artifact manifest verifier."""
    payload = _extract_json(stdout)
    min_checked = int(expect.get('min_checked', 1))
    if not isinstance(payload, dict):
        return {
            'checked': None, 'failures': None, 'failure_count': None,
            'min_checked': min_checked, 'criteria_met': False,
            'reason': 'stdout was not parseable JSON',
        }
    checked = payload.get('checked')
    failures = payload.get('failures')
    if not isinstance(failures, list):
        failures = None
    parsed = {
        'checked': checked,
        'failure_count': (len(failures) if failures is not None else None),
        'failures': failures,
        'manifest': payload.get('manifest'),
        'min_checked': min_checked,
    }
    ok = (failures == [] and isinstance(checked, int) and checked >= min_checked)
    parsed['criteria_met'] = ok
    if not ok:
        if failures is None:
            parsed['reason'] = 'no "failures" list in verifier output'
        elif failures:
            parsed['reason'] = '%d pinned artifact(s) drifted' % len(failures)
        else:
            parsed['reason'] = 'checked=%r below min_checked=%d' % (checked, min_checked)
    return parsed


PARSERS = {
    'unittest': parse_unittest,
    'json_status': parse_json_status,
    'manifest_json': parse_manifest_json,
}


# --------------------------------------------------------------------------- #
# Check execution
# --------------------------------------------------------------------------- #

def _child_env() -> dict:
    """Environment for check subprocesses: bytecode writing disabled twice over."""
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def run_check(spec: dict, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    """Run one check spec and return its result record. Never raises for a
    missing executable or a timeout: those become statuses, not crashes."""
    name = spec.get('name', 'unnamed')
    cmd = list(spec.get('cmd') or [])
    parser_name = spec.get('parser', 'exit_code')
    expect = dict(spec.get('expect') or {})
    started = time.monotonic()
    record = {
        'name': name,
        'command': cmd,
        'command_string': subprocess.list2cmdline(cmd),
        'cwd': spec.get('cwd'),
        'parser': parser_name,
        'returncode': None,
        'duration_ms': 0,
        'status': 'ERROR',
        'passed': False,
        'parsed': None,
        'error': None,
        'stdout_tail': [],
        'stderr_tail': [],
        'stdout_bytes': 0,
        'stderr_bytes': 0,
    }
    if spec.get('manifest_resolution'):
        record['manifest_resolution'] = spec['manifest_resolution']

    skip_reason = spec.get('skip_reason')
    if skip_reason:
        # The check could not be constructed (e.g. no manifest to verify). That is an
        # infrastructure fault, not a component regression: UNAVAILABLE -> exit 2.
        record['status'] = 'UNAVAILABLE'
        record['error'] = 'skipped: %s' % skip_reason
        record['duration_ms'] = int((time.monotonic() - started) * 1000)
        return record

    if not cmd:
        record['error'] = 'check spec has no command'
        record['duration_ms'] = int((time.monotonic() - started) * 1000)
        return record

    try:
        proc = subprocess.run(
            cmd,
            cwd=spec.get('cwd') or None,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            env=_child_env(),
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        record['status'] = 'TIMEOUT'
        record['error'] = 'timed out after %ss' % (timeout,)
        record['stdout_tail'] = _tail(exc.stdout if isinstance(exc.stdout, str) else '')
        record['stderr_tail'] = _tail(exc.stderr if isinstance(exc.stderr, str) else '')
        record['duration_ms'] = int((time.monotonic() - started) * 1000)
        return record
    except OSError as exc:
        # Missing executable, bad path, permission denied: infrastructure, not a
        # regression. Recorded as UNAVAILABLE so the run continues.
        record['status'] = 'UNAVAILABLE'
        record['error'] = '%s: %s' % (type(exc).__name__, exc)
        record['duration_ms'] = int((time.monotonic() - started) * 1000)
        return record

    stdout = proc.stdout or ''
    stderr = proc.stderr or ''
    record['returncode'] = proc.returncode
    record['stdout_tail'] = _tail(stdout)
    record['stderr_tail'] = _tail(stderr)
    record['stdout_bytes'] = len(stdout.encode('utf-8', 'replace'))
    record['stderr_bytes'] = len(stderr.encode('utf-8', 'replace'))
    record['duration_ms'] = int((time.monotonic() - started) * 1000)

    parser = PARSERS.get(parser_name)
    if parser is None:
        parsed = {
            'criteria_met': proc.returncode == 0,
            'returncode': proc.returncode,
        }
    else:
        try:
            parsed = parser(stdout, stderr, expect)
        except Exception as exc:  # a broken parser is an infra fault, not a regression
            record['status'] = 'ERROR'
            record['error'] = 'parser %s raised %s: %s' % (
                parser_name, type(exc).__name__, exc)
            return record

    record['parsed'] = parsed
    criteria_met = bool(parsed.get('criteria_met'))
    record['passed'] = bool(criteria_met and proc.returncode == 0)
    record['status'] = 'PASS' if record['passed'] else 'FAIL'
    if not record['passed'] and proc.returncode != 0:
        record['error'] = 'exit code %d' % (proc.returncode,)
    return record


def run_all(checks: list[dict], timeout: int = DEFAULT_TIMEOUT_SECONDS) -> list[dict]:
    """Run every check spec in order, collecting result records."""
    return [run_check(spec, timeout=timeout) for spec in checks]


# --------------------------------------------------------------------------- #
# Verdict
# --------------------------------------------------------------------------- #

def verdict_from(results: list[dict]) -> tuple[str, int]:
    """Return (overall_verdict, exit_code) for a list of result records."""
    if not results:
        return 'NO_CHECKS', 2
    statuses = [r.get('status') for r in results]
    if any(s in REGRESSION_STATUSES for s in statuses):
        return 'FAIL', 1
    if any(s in INFRA_STATUSES for s in statuses):
        return 'INCOMPLETE', 2
    if all(r.get('passed') for r in results):
        return 'PASS', 0
    return 'FAIL', 1


def count_statuses(results: list[dict]) -> dict:
    counts = {'total': len(results), 'pass': 0, 'fail': 0, 'timeout': 0,
              'unavailable': 0, 'error': 0}
    for r in results:
        status = (r.get('status') or '').lower()
        if status in counts:
            counts[status] += 1
    return counts


# --------------------------------------------------------------------------- #
# Version pins (T7 criterion 2)
# --------------------------------------------------------------------------- #

def _windows_version() -> dict:
    getter = getattr(sys, 'getwindowsversion', None)
    if getter is None:
        return {'status': 'UNAVAILABLE', 'reason': 'not a Windows host'}
    try:
        wv = getter()
        return {
            'status': 'OK',
            'major': wv.major,
            'minor': wv.minor,
            'build': wv.build,
            'platform': wv.platform,
            'service_pack': wv.service_pack,
            'version_string': '%d.%d.%d' % (wv.major, wv.minor, wv.build),
        }
    except Exception as exc:
        return {'status': 'UNAVAILABLE', 'reason': '%s: %s' % (type(exc).__name__, exc)}


def _package_pins() -> dict:
    """Installed versions of the packages that matter, via importlib.metadata."""
    try:
        from importlib import metadata as importlib_metadata
    except ImportError as exc:  # pragma: no cover - Python 3.8+ always has it
        return {name: 'UNAVAILABLE' for name in PINNED_PACKAGES} | {'_error': str(exc)}
    pins = {}
    for name in PINNED_PACKAGES:
        try:
            pins[name] = importlib_metadata.version(name)
        except Exception:
            pins[name] = 'UNAVAILABLE'
    return pins


def _nvidia_smi_inventory() -> dict:
    """GPU inventory from nvidia-smi CSV. Absent tool -> UNAVAILABLE, never a crash."""
    exe = shutil.which('nvidia-smi')
    if not exe:
        return {
            'tool': 'nvidia-smi', 'status': 'UNAVAILABLE',
            'reason': 'nvidia-smi not found on PATH', 'devices': [],
        }
    cmd = [exe, '--query-gpu=name,driver_version,memory.total', '--format=csv']
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=PROBE_TIMEOUT_SECONDS,
                              shell=False)
    except subprocess.TimeoutExpired:
        return {'tool': 'nvidia-smi', 'status': 'UNAVAILABLE',
                'reason': 'timed out after %ss' % PROBE_TIMEOUT_SECONDS, 'devices': []}
    except OSError as exc:
        return {'tool': 'nvidia-smi', 'status': 'UNAVAILABLE',
                'reason': '%s: %s' % (type(exc).__name__, exc), 'devices': []}
    if proc.returncode != 0:
        return {'tool': 'nvidia-smi', 'status': 'UNAVAILABLE',
                'reason': 'exit code %d' % proc.returncode,
                'stderr_tail': _tail(proc.stderr or '', 5), 'devices': []}
    devices = []
    try:
        reader = csv.reader(io.StringIO(proc.stdout or ''))
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
        if rows:
            header = [cell.strip() for cell in rows[0]]
            for row in rows[1:]:
                devices.append({header[i]: row[i].strip()
                                for i in range(min(len(header), len(row)))})
    except Exception as exc:
        return {'tool': 'nvidia-smi', 'status': 'UNAVAILABLE',
                'reason': 'CSV parse error %s: %s' % (type(exc).__name__, exc),
                'devices': []}
    return {'tool': 'nvidia-smi', 'status': 'OK', 'executable': exe,
            'device_count': len(devices), 'devices': devices,
            'raw_stdout_tail': _tail(proc.stdout or '', 8)}


def _tool_probes() -> dict:
    """Cheap presence/version probes for the accelerator stacks named in T7.

    Recording that Level Zero is *absent* is as valuable as recording a version:
    that absence is exactly what silently invalidates the Intel arm.
    """
    probes = {}

    def which(name: str) -> dict:
        path = shutil.which(name)
        return {'status': 'OK' if path else 'UNAVAILABLE', 'path': path or 'UNAVAILABLE'}

    for tool in ('nvidia-smi', 'rocminfo', 'clinfo', 'nvcc', 'ze_loader'):
        probes[tool] = which(tool)

    # Level Zero loader is a DLL, not an exe on PATH: probe the known path too.
    system_root = os.environ.get('SystemRoot', r'C:\Windows')
    ze_path = Path(system_root) / 'System32' / 'ze_loader.dll'
    probes['ze_loader']['dll_path'] = str(ze_path)
    probes['ze_loader']['dll_present'] = bool(ze_path.is_file())
    if not (ze_path.is_file() or probes['ze_loader']['path'] != 'UNAVAILABLE'):
        probes['ze_loader']['status'] = 'UNAVAILABLE'

    nvcc = probes['nvcc']
    if nvcc['status'] == 'OK':
        try:
            proc = subprocess.run([nvcc['path'], '--version'], capture_output=True,
                                  text=True, encoding='utf-8', errors='replace',
                                  timeout=PROBE_TIMEOUT_SECONDS, shell=False)
            nvcc['version_tail'] = _tail(proc.stdout or '', 4)
            nvcc['version_status'] = 'OK' if proc.returncode == 0 else 'UNAVAILABLE'
        except (OSError, subprocess.TimeoutExpired) as exc:
            nvcc['version_tail'] = []
            nvcc['version_status'] = 'UNAVAILABLE'
            nvcc['version_error'] = '%s: %s' % (type(exc).__name__, exc)
    else:
        nvcc['version_status'] = 'UNAVAILABLE'

    return probes


def collect_pins() -> dict:
    """The full version pin block. Every probe is individually failure-proofed."""
    def safe(fn, fallback):
        try:
            return fn()
        except Exception as exc:
            return {'status': 'UNAVAILABLE',
                    'reason': '%s: %s' % (type(exc).__name__, exc)} if isinstance(fallback, dict) else fallback

    return {
        'platform': platform.platform(),
        'system': platform.system(),
        'release': platform.release(),
        'machine': platform.machine(),
        'processor': platform.processor() or 'UNAVAILABLE',
        'os_build': safe(_windows_version, {}),
        'python': {
            'version': platform.python_version(),
            'version_full': sys.version.replace('\n', ' '),
            'implementation': platform.python_implementation(),
            'executable': sys.executable,
            'compiler': platform.python_compiler(),
            'bytecode_writing_disabled': bool(sys.dont_write_bytecode),
        },
        'packages': safe(_package_pins, {}),
        'gpu_inventory': safe(_nvidia_smi_inventory, {}),
        'tool_probes': safe(_tool_probes, {}),
    }


# --------------------------------------------------------------------------- #
# Receipt assembly and rendering
# --------------------------------------------------------------------------- #

def utc_stamp(when: datetime | None = None) -> str:
    """Receipt directory name: UTC yyyyMMddTHHmmssZ."""
    when = when or datetime.now(timezone.utc)
    return when.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def build_receipt(results: list[dict], pins: dict, stamp: str,
                  duration_ms: int, repo_root: Path, script_path: Path,
                  notes: list[str] | None = None) -> dict:
    """Assemble the receipt document from already-collected parts."""
    verdict, exit_code = verdict_from(results)
    generated = datetime.now(timezone.utc)
    return {
        'schema_version': SCHEMA_VERSION,
        'target': TARGET,
        'target_definition': ('unattended nightly job that builds every component, '
                              'runs every test, verifies the artifact manifest, and '
                              'publishes a dated receipt'),
        'stamp': stamp,
        'generated_utc': generated.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'generated_iso': generated.isoformat(),
        'duration_ms': int(duration_ms),
        'host_pins': pins,
        'checks': results,
        'counts': count_statuses(results),
        'overall_verdict': verdict,
        'exit_code': exit_code,
        'exit_code_policy': {
            '0': 'every check PASSed',
            '1': 'one or more checks FAILED or TIMED OUT (loud failure)',
            '2': 'job could not fully run: UNAVAILABLE command, parser ERROR, or receipt write failure',
            'precedence': 'FAIL outranks UNAVAILABLE; a regression is the more actionable signal',
        },
        'source': {
            'script': str(script_path),
            'repo_root': str(repo_root),
        },
        'notes': list(notes or []),
    }


def render_summary(receipt: dict) -> str:
    """Short human-readable SUMMARY.md for the same receipt directory."""
    counts = receipt.get('counts') or {}
    lines = [
        '# Nightly verification receipt - %s' % receipt.get('stamp'),
        '',
        'Target: **%s** (nightly build and continuous verification)  ' % receipt.get('target'),
        'Schema: %s  ' % receipt.get('schema_version'),
        'Generated (UTC): %s  ' % receipt.get('generated_utc'),
        'Duration: %d ms' % int(receipt.get('duration_ms') or 0),
        '',
        '## Verdict: **%s** (exit %s)' % (receipt.get('overall_verdict'),
                                          receipt.get('exit_code')),
        '',
        'Checks: %s total - %s PASS, %s FAIL, %s TIMEOUT, %s UNAVAILABLE, %s ERROR'
        % (counts.get('total'), counts.get('pass'), counts.get('fail'),
           counts.get('timeout'), counts.get('unavailable'), counts.get('error')),
        '',
        '| Check | Status | RC | ms | Parsed result |',
        '|---|---|---|---|---|',
    ]
    for check in receipt.get('checks') or []:
        parsed = check.get('parsed') or {}
        summary_bits = []
        for key in ('tests_ran', 'verdict', 'status', 'checked', 'failure_count'):
            if key in parsed and parsed[key] is not None:
                summary_bits.append('%s=%s' % (key, parsed[key]))
        detail = ', '.join(summary_bits) or (check.get('error') or '-')
        lines.append('| %s | %s | %s | %s | %s |' % (
            check.get('name'), check.get('status'), check.get('returncode'),
            check.get('duration_ms'), detail))

    resolutions = [c.get('manifest_resolution') for c in (receipt.get('checks') or [])
                   if c.get('manifest_resolution')]
    if resolutions:
        resolution = resolutions[0]
        lines += [
            '',
            '## Artifact manifest',
            '',
            '- Selection mode: %s' % resolution.get('mode'),
            '- Resolved: %s' % resolution.get('resolved',
                                              'UNAVAILABLE - %s' % resolution.get('reason')),
        ]
        if resolution.get('candidates'):
            lines.append('- Candidates by filename sort (%d): %s'
                         % (resolution.get('candidate_count'),
                            ', '.join(resolution['candidates'])))

    pins = receipt.get('host_pins') or {}
    python_pins = pins.get('python') or {}
    packages = pins.get('packages') or {}
    gpu = pins.get('gpu_inventory') or {}
    os_build = pins.get('os_build') or {}
    lines += [
        '',
        '## Version pins',
        '',
        '- Platform: %s' % pins.get('platform'),
        '- OS build: %s' % os_build.get('version_string', 'UNAVAILABLE'),
        '- Python: %s (`%s`)' % (python_pins.get('version', 'UNAVAILABLE'),
                                 python_pins.get('executable', 'UNAVAILABLE')),
        '- Compiler: %s' % python_pins.get('compiler', 'UNAVAILABLE'),
        '- Packages: %s' % (', '.join('%s=%s' % (k, v) for k, v in packages.items())
                            or 'UNAVAILABLE'),
        '- GPU inventory (%s): %s' % (
            gpu.get('tool', 'nvidia-smi'),
            ('%s device(s)' % gpu.get('device_count')
             if gpu.get('status') == 'OK' else 'UNAVAILABLE - %s' % gpu.get('reason'))),
    ]
    for device in gpu.get('devices') or []:
        # nvidia-smi's header carries a unit suffix ("memory.total [MiB]"), so match
        # on the prefix rather than an exact key.
        memory = next((value for key, value in device.items()
                       if key.startswith('memory.total')), None)
        lines.append('  - %s | driver %s | %s' % (
            device.get('name'), device.get('driver_version'), memory))

    probes = pins.get('tool_probes') or {}
    if probes:
        lines.append('- Tool probes: %s' % ', '.join(
            '%s=%s' % (name, (probe or {}).get('status'))
            for name, probe in probes.items()))
        ze = probes.get('ze_loader') or {}
        if 'dll_present' in ze:
            lines.append('  - Level Zero `ze_loader.dll` present: **%s**' % ze['dll_present'])

    failed = [c for c in (receipt.get('checks') or []) if not c.get('passed')]
    if failed:
        lines += ['', '## Failures requiring attention', '']
        for check in failed:
            lines.append('### %s - %s' % (check.get('name'), check.get('status')))
            lines.append('')
            lines.append('    %s' % check.get('command_string'))
            lines.append('')
            parsed = check.get('parsed') or {}
            if parsed.get('reason'):
                lines.append('- Reason: %s' % parsed['reason'])
            if check.get('error'):
                lines.append('- Error: %s' % check['error'])
            for label, key in (('stdout', 'stdout_tail'), ('stderr', 'stderr_tail')):
                tail = check.get(key) or []
                if tail:
                    lines.append('- %s tail:' % label)
                    lines.append('')
                    lines.append('      ' + '\n      '.join(tail[-10:]))
                    lines.append('')
    else:
        lines += ['', 'No failures. Every check met its parsed criteria.', '']

    notes = receipt.get('notes') or []
    if notes:
        lines += ['## Notes', '']
        lines += ['- %s' % note for note in notes]
        lines.append('')
    return '\n'.join(lines) + '\n'


def write_receipt(out_root, stamp: str, receipt: dict) -> tuple[Path, Path]:
    """Create <out_root>/<stamp>/ and write receipt.json + SUMMARY.md."""
    directory = Path(out_root) / stamp
    directory.mkdir(parents=True, exist_ok=True)
    receipt_path = directory / 'receipt.json'
    summary_path = directory / 'SUMMARY.md'
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n',
                            encoding='utf-8')
    summary_path.write_text(render_summary(receipt), encoding='utf-8')
    return receipt_path, summary_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='nightly_verify.py',
        description='Nightly T7 verification: run every check, record pins, publish a dated receipt.',
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='list what would run; execute nothing and write nothing')
    parser.add_argument('--out-dir', default=None,
                        help='override the receipt root directory '
                             '(default: <repo>/records/nightly)')
    parser.add_argument('--repo-root', default=None,
                        help='override the repository root used to build check commands')
    parser.add_argument('--manifest', default=None,
                        help='artifact manifest to verify (absolute, or relative to the '
                             'repo root). Default: the newest records/%s by filename sort'
                             % MANIFEST_GLOB)
    parser.add_argument('--python-exe', default=None,
                        help='interpreter for the check subprocesses (default: this one)')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help='per-check wall-clock timeout in seconds (default: %d)'
                             % DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_default()
    python_exe = args.python_exe or sys.executable
    out_root = Path(args.out_dir).resolve() if args.out_dir else repo_root / 'records' / 'nightly'
    checks = build_checks(repo_root, python_exe, manifest=args.manifest)
    manifest_check = next((c for c in checks
                           if c['name'] == 'artifact_manifest_integrity'), None)
    resolution = (manifest_check or {}).get('manifest_resolution') or {}

    if args.dry_run:
        print('NIGHTLY VERIFY - DRY RUN (nothing executed, nothing written)')
        print('repo root : %s' % repo_root)
        print('python exe: %s' % python_exe)
        print('out root  : %s' % out_root)
        print('timeout   : %ss per check' % args.timeout)
        print('manifest  : mode=%s status=%s resolved=%s'
              % (resolution.get('mode'), resolution.get('status'),
                 resolution.get('resolved', resolution.get('reason'))))
        if resolution.get('candidates'):
            print('            candidates by filename sort (%d): %s'
                  % (resolution['candidate_count'], ', '.join(resolution['candidates'])))
        print('checks that would run (%d):' % len(checks))
        for index, spec in enumerate(checks, 1):
            print('  %d. %-26s parser=%-14s %s'
                  % (index, spec['name'], spec['parser'],
                     subprocess.list2cmdline(spec['cmd'])
                     or ('<skipped: %s>' % spec.get('skip_reason'))))
        print('NIGHTLY VERDICT: DRY_RUN - 0 checks executed - exit 0')
        return 0

    started = time.monotonic()
    stamp = utc_stamp()
    notes = ['manifest resolution: mode=%s status=%s resolved=%s'
             % (resolution.get('mode'), resolution.get('status'),
                resolution.get('resolved', resolution.get('reason')))]
    if resolution.get('candidates'):
        notes.append('manifest candidates by filename sort (%d): %s'
                     % (resolution['candidate_count'], ', '.join(resolution['candidates'])))
    try:
        pins = collect_pins()
    except Exception as exc:  # pragma: no cover - collect_pins is already failure-proofed
        pins = {'status': 'UNAVAILABLE', 'reason': '%s: %s' % (type(exc).__name__, exc)}
        notes.append('pin collection raised and was caught: %s' % exc)

    results = run_all(checks, timeout=args.timeout)
    duration_ms = int((time.monotonic() - started) * 1000)
    receipt = build_receipt(results, pins, stamp, duration_ms, repo_root,
                            Path(__file__).resolve(), notes=notes)

    try:
        receipt_path, summary_path = write_receipt(out_root, stamp, receipt)
    except OSError as exc:
        verdict, _ = verdict_from(results)
        counts = count_statuses(results)
        print('NIGHTLY VERDICT: %s - %d/%d checks PASS, %d FAIL, %d UNAVAILABLE '
              '- RECEIPT WRITE FAILED (%s: %s) - exit 2'
              % (verdict, counts['pass'], counts['total'], counts['fail'],
                 counts['unavailable'], type(exc).__name__, exc))
        return 2

    verdict = receipt['overall_verdict']
    exit_code = receipt['exit_code']
    counts = receipt['counts']
    print('NIGHTLY VERDICT: %s - %d/%d checks PASS, %d FAIL, %d TIMEOUT, '
          '%d UNAVAILABLE, %d ERROR - receipt: %s - exit %d'
          % (verdict, counts['pass'], counts['total'], counts['fail'],
             counts['timeout'], counts['unavailable'], counts['error'],
             receipt_path, exit_code))
    print('SUMMARY: %s' % summary_path)
    for result in results:
        parsed = result.get('parsed') or {}
        detail = ''
        for key in ('tests_ran', 'verdict', 'status', 'checked', 'failure_count'):
            if parsed.get(key) is not None:
                detail += ' %s=%s' % (key, parsed[key])
        if not result.get('passed') and result.get('error'):
            detail += ' [%s]' % result['error']
        print('  %-26s %-11s rc=%-4s %6dms%s'
              % (result['name'], result['status'], result['returncode'],
                 result['duration_ms'], detail or ''))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
