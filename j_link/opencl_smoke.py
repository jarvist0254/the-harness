#!/usr/bin/env python3
"""Bounded experimental OpenCL arithmetic/host-staging probe; no allocator product.

Each direction runs one single sample at three sizes, at most 1 MiB per FP32
vector. Results are smoke timings, not performance benchmarks. The supervisor
terminates its child after 60 seconds. No direct P2P or unified pool is tested.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import textwrap
from datetime import datetime, timezone


COUNTS = (32, 2048, 262144)


def probe(inject_corruption, probe_invalid_context=False):
    import numpy as np
    import pyopencl as cl

    result = {
        'status': 'NOT_CHECKED',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'experimental': True,
        'transport': 'EXPLICIT_HOST_STAGED',
        'timing_scope': 'single smoke sample per count and direction; not a performance benchmark',
        'counts': list(COUNTS), 'max_vector_bytes': 1048576,
        'inject_corruption': inject_corruption,
        'numpy_version': np.__version__, 'pyopencl_version': cl.VERSION_TEXT,
        'devices': [], 'negative_controls': {}, 'runs': [],
        'limitations': [
            'No direct P2P, shared allocation, VRAM pool or LLM execution tested',
            'AMD integrated GPU memory is shared host memory, not dedicated VRAM',
            'Extensions describe advertised availability, not exercised interoperability',
            'Intel GPU execution NOT_CHECKED; this probe requires AMD and NVIDIA',
            'Runtime IDs are session-local unless a physical PCI identity is exposed',
        ],
    }
    selected = {}
    for pi, platform in enumerate(cl.get_platforms()):
        for di, device in enumerate(platform.get_devices()):
            if not device.type & cl.device_type.GPU:
                continue
            extensions = device.extensions.split()
            identity = {'runtime_id': f'platform_{pi}/device_{di}',
                        'confidence': 'REPORTED_RUNTIME_ID_ONLY', 'pci_identity': None}
            if 'cl_nv_device_attribute_query' in extensions:
                try:
                    identity.update(confidence='RUNTIME_REPORTED_PCI_IDENTITY',
                                    pci_identity={'domain': int(device.pci_domain_id_nv),
                                                  'bus': int(device.pci_bus_id_nv),
                                                  'slot_raw_nv': int(device.pci_slot_id_nv)})
                except Exception as exc:
                    identity['pci_query_error'] = str(exc)
            elif 'cl_khr_pci_bus_info' in extensions:
                try:
                    pci = device.pci_bus_info_khr
                    identity.update(confidence='RUNTIME_REPORTED_PCI_IDENTITY',
                                    pci_identity={name: int(getattr(pci, name)) for name in
                                                  ('pci_domain', 'pci_bus', 'pci_device', 'pci_function')})
                except Exception as exc:
                    identity['pci_query_error'] = str(exc)
            info = {
                'identity': identity, 'platform': platform.name,
                'platform_vendor': platform.vendor, 'platform_version': platform.version,
                'name': device.name, 'vendor': device.vendor,
                'device_type': cl.device_type.to_string(device.type),
                'global_mem_bytes_reported': int(device.global_mem_size),
                'host_unified_memory': bool(device.host_unified_memory),
                'memory_classification': ('SHARED_HOST_MEMORY_NOT_DEDICATED_VRAM'
                                          if device.host_unified_memory else
                                          'DEVICE_LOCAL_MEMORY_REPORTED'),
                'max_alloc_bytes_reported': int(device.max_mem_alloc_size),
                'interop_extensions_advertised_only': [e for e in extensions
                    if 'external_memory' in e or 'external_semaphore' in e or 'svm' in e],
            }
            try:
                info['svm_capabilities_advertised_only'] = int(device.svm_capabilities)
            except Exception:
                info['svm_capabilities_advertised_only'] = None
            result['devices'].append(info)
            vendor = device.vendor.lower()
            key = 'NVIDIA' if 'nvidia' in vendor else 'AMD' if ('advanced micro' in vendor or 'amd' in vendor) else None
            if key and key not in selected:
                selected[key] = (device, info)
    result['required_pairs'] = ['AMD->NVIDIA', 'NVIDIA->AMD']
    if len(selected) != 2:
        result['reason'] = 'Required AMD and NVIDIA GPU pair unavailable'
        return result, 2

    result['negative_controls']['cross_platform_single_context'] = {
        'status': 'NOT_CHECKED', 'reason': 'Opt-in invalid-context probe disabled; known native access violation'}
    if probe_invalid_context:
        # Some vendor runtimes terminate the process for this invalid combination.
        # Isolate the negative control so it cannot abort valid staged execution.
        context_code = '''
    import pyopencl as cl
    devices = [d for p in cl.get_platforms() for d in p.get_devices()
               if d.type & cl.device_type.GPU]
    amd = next(d for d in devices if 'advanced micro' in d.vendor.lower() or 'amd' in d.vendor.lower())
    nv = next(d for d in devices if 'nvidia' in d.vendor.lower())
    print('ATTEMPT_CROSS_PLATFORM_CONTEXT', flush=True)
    try:
        ctx = cl.Context([amd, nv])
        print('ACCEPTED', flush=True)
    except cl.Error as exc:
        print('REJECTED_EXCEPTION', type(exc).__name__, str(exc), flush=True)
        raise SystemExit(3)
    '''
        control = subprocess.run([sys.executable, '-u', '-c', textwrap.dedent(context_code)],
                                 capture_output=True, text=True, timeout=15,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        reached = 'ATTEMPT_CROSS_PLATFORM_CONTEXT' in control.stdout
        rejected = reached and control.returncode != 0 and 'ACCEPTED' not in control.stdout
        result['negative_controls']['cross_platform_single_context'] = {
            'status': ('PASS' if 'REJECTED_EXCEPTION' in control.stdout
                       else 'NATIVE_FAILURE' if rejected else 'FAIL'),
            'rejected': rejected,
            'clean_api_rejection': 'REJECTED_EXCEPTION' in control.stdout,
            'returncode': control.returncode, 'stdout': control.stdout[:2048],
            'stderr': control.stderr[:2048],
            'rejection_kind': ('OPENCL_EXCEPTION' if 'REJECTED_EXCEPTION' in control.stdout
                               else 'NATIVE_PROCESS_EXIT' if rejected else 'NOT_REJECTED'),
        }
        if rejected and 'REJECTED_EXCEPTION' not in control.stdout:
            result['status'] = 'FAIL'
            result['reason'] = 'Invalid-context control caused native process failure, not clean API rejection'
            return result, 1
        if not rejected:
            result['negative_controls']['cross_platform_single_context'] = {
                'status': 'FAIL', 'reason': 'Cross-platform device context unexpectedly accepted'}
            result['status'] = 'FAIL'
            return result, 1

    source = '''
    __kernel void stage_one(__global const float *a, __global float *b) {
        int i = get_global_id(0); b[i] = 2.0f*a[i]+1.0f;
    }
    __kernel void stage_two(__global const float *a, __global float *b) {
        int i = get_global_id(0); b[i] = 3.0f*a[i]-2.0f;
    }
    '''
    runtime = {}
    for vendor, (device, info) in selected.items():
        context = cl.Context([device])
        queue = cl.CommandQueue(context, properties=cl.command_queue_properties.PROFILING_ENABLE)
        program = cl.Program(context, source).build()
        runtime[vendor] = (context, queue, cl.Kernel(program, 'stage_one'),
                           cl.Kernel(program, 'stage_two'), info)

    failed = False
    corrupted_detected = True
    for src_vendor, dst_vendor in [('AMD', 'NVIDIA'), ('NVIDIA', 'AMD')]:
        src_ctx, src_q, kernel_one, _, src_info = runtime[src_vendor]
        dst_ctx, dst_q, _, kernel_two, dst_info = runtime[dst_vendor]
        for count in COUNTS:
            started = time.perf_counter()
            x = np.arange(count, dtype=np.float32)
            intermediate = np.empty_like(x)
            out = np.empty_like(x)
            expected_one = 2*x+1
            expected_two = 6*x+1
            src_input = cl.Buffer(src_ctx, cl.mem_flags.READ_ONLY, x.nbytes)
            src_output = cl.Buffer(src_ctx, cl.mem_flags.WRITE_ONLY, x.nbytes)
            upload_one = cl.enqueue_copy(src_q, src_input, x, is_blocking=False)
            event_one = kernel_one(src_q, (count,), None, src_input, src_output,
                                   wait_for=[upload_one])
            read_one = cl.enqueue_copy(src_q, intermediate, src_output,
                                      is_blocking=False, wait_for=[event_one])
            read_one.wait()
            src_q.finish()
            source_error = float(np.max(np.abs(intermediate-expected_one)))
            source_pass = bool(np.array_equal(intermediate, expected_one))
            if inject_corruption:
                intermediate[0] += np.float32(1)
            dst_input = cl.Buffer(dst_ctx, cl.mem_flags.READ_ONLY, x.nbytes)
            dst_output = cl.Buffer(dst_ctx, cl.mem_flags.WRITE_ONLY, x.nbytes)
            # Explicit NumPy host staging, including between different platforms.
            upload_two = cl.enqueue_copy(dst_q, dst_input, intermediate, is_blocking=False)
            event_two = kernel_two(dst_q, (count,), None, dst_input, dst_output,
                                   wait_for=[upload_two])
            read_two = cl.enqueue_copy(dst_q, out, dst_output,
                                      is_blocking=False, wait_for=[event_two])
            read_two.wait()
            dst_q.finish()
            final_error = float(np.max(np.abs(out-expected_two)))
            final_pass = bool(np.array_equal(out, expected_two))
            # Independent corruption negative control always exercises the
            # destination kernel using a separately corrupted host intermediate.
            corrupt = expected_one.copy()
            corrupt[0] += np.float32(1)
            control_upload = cl.enqueue_copy(dst_q, dst_input, corrupt, is_blocking=False)
            control_kernel = kernel_two(dst_q, (count,), None, dst_input, dst_output,
                                        wait_for=[control_upload])
            control_out = np.empty_like(x)
            cl.enqueue_copy(dst_q, control_out, dst_output, is_blocking=False,
                            wait_for=[control_kernel]).wait()
            dst_q.finish()
            rejected_corrupt = not bool(np.array_equal(control_out, expected_two))
            corrupt_error = float(np.max(np.abs(control_out-expected_two)))
            corrupted_detected &= rejected_corrupt and corrupt_error == 3.0
            source_executed = event_one.command_execution_status == cl.command_execution_status.COMPLETE
            destination_executed = event_two.command_execution_status == cl.command_execution_status.COMPLETE
            parity = (source_pass and final_pass and source_executed and destination_executed
                      and rejected_corrupt and corrupt_error == 3.0)
            failed |= not parity
            result['runs'].append({
                'direction': f'{src_vendor}->{dst_vendor}', 'count': count,
                'vector_bytes': x.nbytes, 'status': 'PASS' if parity else 'FAIL',
                'source_runtime_id': src_info['identity']['runtime_id'],
                'destination_runtime_id': dst_info['identity']['runtime_id'],
                'source_kernel_executed': source_executed,
                'destination_kernel_executed': destination_executed,
                'source_max_abs_error': source_error, 'final_max_abs_error': final_error,
                'source_parity': source_pass, 'final_parity': final_pass,
                'final_sum': float(out.sum(dtype=np.float64)),
                'corrupted_intermediate_rejected': rejected_corrupt,
                'corrupted_control_max_abs_error': corrupt_error,
                'source_kernel_event_ms': (event_one.profile.end-event_one.profile.start)/1e6,
                'destination_kernel_event_ms': (event_two.profile.end-event_two.profile.start)/1e6,
                'wall_ms_including_copies_and_negative_control': (time.perf_counter()-started)*1000,
            })
            for buffer in (src_input, src_output, dst_input, dst_output):
                buffer.release()
    result['negative_controls']['corrupted_intermediate'] = {
        'status': 'PASS' if corrupted_detected else 'FAIL',
        'detected_in_all_runs': corrupted_detected}
    result['status'] = 'FAIL' if failed else 'PASS'
    return result, 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inject-corruption', action='store_true')
    parser.add_argument('--probe-invalid-context', action='store_true',
                        help='Opt in to invalid mixed-platform context control; known driver native crash')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        try:
            result, code = probe(args.inject_corruption, args.probe_invalid_context)
        except Exception as exc:
            result = {'status': 'FAIL', 'experimental': True,
                      'transport': 'EXPLICIT_HOST_STAGED',
                      'error_type': type(exc).__name__, 'error': str(exc)}
            code = 1
    else:
        command = [sys.executable, str(Path(__file__).resolve()), '--child']
        if args.inject_corruption:
            command.append('--inject-corruption')
        if args.probe_invalid_context:
            command.append('--probe-invalid-context')
        try:
            child = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            result = json.loads(child.stdout)
            code = child.returncode
            if child.stderr:
                result['child_stderr'] = child.stderr[:8192]
        except subprocess.TimeoutExpired:
            result = {'status': 'FAIL', 'reason': '60-second child timeout', 'experimental': True}
            code = 1
        except Exception as exc:
            result = {'status': 'FAIL', 'error_type': type(exc).__name__, 'error': str(exc)}
            code = 1
    serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if len(serialized.encode('utf-8')) > 131072:
        serialized = json.dumps({'status': 'FAIL', 'reason': 'Result exceeds 128 KiB output bound'})+'\n'
        code = 1
    if args.output:
        temporary = args.output.with_name(args.output.name+f'.{os.getpid()}.tmp')
        try:
            temporary.write_text(serialized, encoding='utf-8')
            os.replace(temporary, args.output)
        finally:
            temporary.unlink(missing_ok=True)
    print(serialized, end='')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
