import hashlib
from datetime import datetime, timezone

def validate_result(receipt, *, now_utc, max_age_seconds=10, trusted_artifact_hashes=frozenset()):
    """
    Pure measured-evidence validator.
    Returns: {status: 'QUALIFIED'|'REFUSED'|'NOT_CHECKED', reasons: [str], qualified_claims: []}
    """
    reasons = []
    qualified_claims = []
    status = 'NOT_CHECKED'

    # 1. Basic Schema & Trust Check
    if not isinstance(receipt, dict):
        return {'status': 'REFUSED', 'reasons': ['INVALID_SCHEMA'], 'qualified_claims': []}
    
    claims = receipt.get('claims', [])
    artifacts = receipt.get('artifacts', [])
    devices = receipt.get('devices', [])
    timestamp_str = receipt.get('timestamp')

    # Verify Artifacts against Trusted Hashes
    for art in artifacts:
        h = art.get('sha256')
        if not h or h not in trusted_artifact_hashes:
            reasons.append(f'UNTRUSTED_ARTIFACT:{h}')
            return {'status': 'NOT_CHECKED', 'reasons': reasons, 'qualified_claims': []}

    # Verify Timestamp Freshness
    try:
        ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        age = (now_utc - ts).total_seconds()
        if age < 0 or age > max_age_seconds:
            reasons.append('STALE_OR_FUTURE_TIMESTAMP')
            return {'status': 'NOT_CHECKED', 'reasons': reasons, 'qualified_claims': []}
    except Exception:
        reasons.append('INVALID_TIMESTAMP_FORMAT')
        return {'status': 'NOT_CHECKED', 'reasons': reasons, 'qualified_claims': []}

    # 2. Device Validation (PCI Normalization & Uniqueness)
    seen_pci = set()
    valid_devices = []
    for dev in devices:
        pci_raw = dev.get('pci_id', '')
        # Normalize PCI: expect 4 hex segments, numeric <= ffff
        parts = pci_raw.split(':')
        if len(parts) != 4:
            reasons.append(f'MALFORMED_PCI:{pci_raw}')
            continue
        try:
            norm_parts = [f'{int(p, 16):04x}' for p in parts]
            if any(int(p, 16) > 0xffff for p in parts):
                reasons.append(f'PCI_OUT_OF_RANGE:{pci_raw}')
                continue
            norm_pci = ':'.join(norm_parts)
            if norm_pci in seen_pci:
                reasons.append(f'DUPLICATE_PCI_ALIAS:{norm_pci}')
                continue
            seen_pci.add(norm_pci)
            valid_devices.append({**dev, 'normalized_pci': norm_pci})
        except ValueError:
            reasons.append(f'NON_HEX_PCI:{pci_raw}')
            continue

    if len(valid_devices) != len(devices):
        reasons.append('DEVICE_VALIDATION_FAILED')
        return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}

    # 3. Claim-Specific Validation
    claim_map = {c['id']: c for c in claims}
    
    # Helper to check memory constraints
    def check_mem(device):
        mem = device.get('memory', {})
        total = mem.get('total_bytes')
        free = mem.get('free_bytes')
        peak = mem.get('allocator_peak_bytes')
        kind = mem.get('kind')
        
        if not all(isinstance(x, int) and x >= 0 for x in [total, free, peak]):
            return False, 'INVALID_MEM_TYPES'
        if free > total:
            return False, 'FREE_GT_TOTAL'
        if peak > total:
            return False, 'PEAK_GT_TOTAL'
        if kind == 'SHARED_HOST':
            return False, 'SHARED_MEMORY_NOT_DEDICATED'
        return True, ''

    # FOUR_PHYSICAL_GPU / DEDICATED_CAPACITY_GT_ONE_CARD / FOUR_REQUIRED_CAPACITY
    if 'FOUR_PHYSICAL_GPU' in claim_map:
        if len(valid_devices) < 4:
            reasons.append('INSUFFICIENT_DISCRETE_GPUS')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
        
        # Check dedicated VRAM and unique ownership
        gpu_count = 0
        for dev in valid_devices:
            ok, err = check_mem(dev)
            if not ok:
                reasons.append(err)
                return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
            if dev['memory']['kind'] == 'DEDICATED':
                gpu_count += 1
        
        if gpu_count < 4:
            reasons.append('FEWER_THAN_4_DEDICATED_VRAM')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
        
        # Check kernel completion and block ownership
        kernels_done = sum(1 for d in valid_devices if d.get('kernels_completed', False))
        if kernels_done < 4:
            reasons.append('INCOMPLETE_KERNEL_EXECUTION')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
            
        blocks_owned = set()
        for d in valid_devices:
            b = d.get('resident_block_hash')
            if not b:
                reasons.append('MISSING_BLOCK_OWNERSHIP')
                return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
            blocks_owned.add(b)
        
        if len(blocks_owned) < 4:
            reasons.append('DUPLICATE_MODEL_REPLICATION')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}

        qualified_claims.append('FOUR_PHYSICAL_GPU')
        qualified_claims.append('DEDICATED_CAPACITY_GT_ONE_CARD')
        qualified_claims.append('FOUR_REQUIRED_CAPACITY')

    # LLM_LOGIT_PARITY
    if 'LLM_LOGIT_PARITY' in claim_map:
        llm_data = claim_map['LLM_LOGIT_PARITY'].get('evidence', {})
        ref_hash = llm_data.get('reference_logit_hash')
        calc_hash = llm_data.get('calculated_logit_hash')
        error = llm_data.get('max_abs_error')
        tol = llm_data.get('tolerance')
        
        if not ref_hash or not calc_hash:
            reasons.append('MISSING_LOGIT_HASHES')
            return {'status': 'NOT_CHECKED', 'reasons': reasons, 'qualified_claims': []}
        
        if ref_hash != calc_hash:
             # Allow small numerical drift if within tolerance
             if error is None or tol is None:
                 reasons.append('NO_TOLERANCE_DATA')
                 return {'status': 'NOT_CHECKED', 'reasons': reasons, 'qualified_claims': []}
             if error > tol:
                 reasons.append('LOGIT_ERROR_EXCEEDS_TOLERANCE')
                 return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
        
        # Ensure it's not just prose
        if llm_data.get('type') != 'NUMERICAL_ARRAY':
            reasons.append('PROSE_ONLY_EVIDENCE')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
            
        qualified_claims.append('LLM_LOGIT_PARITY')

    # DIRECT_P2P
    if 'DIRECT_P2P' in claim_map:
        p2p_data = claim_map['DIRECT_P2P'].get('evidence', {})
        primitive = p2p_data.get('primitive_type')
        if primitive != 'DIRECT_DEVICE':
            reasons.append('HOST_STAGED_OR_SYSTEM_HEAP_P2P')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
        qualified_claims.append('DIRECT_P2P')

    # DURABLE_REPLAY
    if 'DURABLE_REPLAY' in claim_map:
        dur_data = claim_map['DURABLE_REPLAY'].get('evidence', {})
        checkpoint_id = dur_data.get('checkpoint_identity')
        commit_seq = dur_data.get('commit_sequence')
        replay_boundary = dur_data.get('replay_boundary')
        
        if not checkpoint_id or commit_seq is None or replay_boundary is None:
            reasons.append('INCOMPLETE_DURABILITY_EVIDENCE')
            return {'status': 'NOT_CHECKED', 'reasons': reasons, 'qualified_claims': []}
        
        # Atomic final JSON alone is not durability
        if dur_data.get('method') == 'ATOMIC_JSON_WRITE_ONLY':
            reasons.append('ATOMIC_JSON_NOT_DURABILITY')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
            
        qualified_claims.append('DURABLE_REPLAY')

    # TWO_VENDOR_NUMERICAL
    if 'TWO_VENDOR_NUMERICAL' in claim_map:
        # Requires at least 2 distinct vendors in devices
        vendors = set(d.get('vendor') for d in valid_devices)
        if len(vendors) < 2:
            reasons.append('SINGLE_VENDOR_EVIDENCE')
            return {'status': 'REFUSED', 'reasons': reasons, 'qualified_claims': []}
        qualified_claims.append('TWO_VENDOR_NUMERICAL')

    if not reasons:
        status = 'QUALIFIED'
    elif 'NOT_CHECKED' in str(reasons) or any('UNTRUSTED' in r for r in reasons):
        status = 'NOT_CHECKED'
    else:
        status = 'REFUSED'

    return {
        'status': status,
        'reasons': sorted(list(set(reasons))),
        'qualified_claims': sorted(qualified_claims)
    }
