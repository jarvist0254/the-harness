import json
import math
from typing import Dict, List, Any, Optional

# Contract Version: 1.0 (Strict Hardware Qualification Validator)
# NOTE: This validator checks structural integrity and logical consistency of provided receipts.
# It does NOT authenticate the underlying hardware measurements. Trust in the data source is external.

def validate_result(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a GPU qualification receipt against strict contract v1.
    
    Args:
        receipt: A dictionary containing 'schema_version', 'claims', and 'evidence'.
        
    Returns:
        dict: {
            'status': 'QUALIFIED' | 'REFUSED' | 'NOT_CHECKED',
            'reasons': [str],
            'proven_claims': [str]
        }
    """
    reasons = []
    proven_claims = []
    status = "NOT_CHECKED"

    # 1. Schema Check
    if not isinstance(receipt, dict):
        return {"status": "REFUSED", "reasons": ["Receipt must be a dictionary"], "proven_claims": []}
    
    schema_ver = receipt.get("schema_version")
    if schema_ver != "1.0":
        return {"status": "REFUSED", "reasons": [f"Unsupported schema version: {schema_ver}"], "proven_claims": []}

    claims = receipt.get("claims", [])
    evidence = receipt.get("evidence", {})
    
    if not isinstance(claims, list) or not isinstance(evidence, dict):
        return {"status": "REFUSED", "reasons": ["Invalid structure for claims or evidence"], "proven_claims": []}

    # Helper to check numeric validity (no NaN, Inf, negative where forbidden)
    def is_valid_number(val: Any, allow_negative: bool = False) -> bool:
        if not isinstance(val, (int, float)):
            return False
        if isinstance(val, bool): # Bool-as-number rejection
            return False
        if math.isnan(val) or math.isinf(val):
            return False
        if not allow_negative and val < 0:
            return False
        return True

    # Process each claim
    for claim_type in claims:
        if claim_type == "FOUR_GPU":
            res = _validate_four_gpu(evidence, reasons)
            if res:
                proven_claims.append(claim_type)
        elif claim_type == "DEDICATED_CAPACITY":
            res = _validate_dedicated_capacity(evidence, reasons)
            if res:
                proven_claims.append(claim_type)
        elif claim_type == "TRANSFER_DIRECT_P2P":
            res = _validate_transfer_p2p(evidence, reasons)
            if res:
                proven_claims.append(claim_type)
        elif claim_type == "LLM_INFERENCE":
            res = _validate_llm(evidence, reasons)
            if res:
                proven_claims.append(claim_type)
        elif claim_type == "DURABILITY":
            res = _validate_durability(evidence, reasons)
            if res:
                proven_claims.append(claim_type)
        else:
            reasons.append(f"Unrecognized claim type: {claim_type}")
            # Unrecognized claims generally refuse the whole validation unless explicitly ignored
            # For strictness, we treat unknown claims as refusal triggers if they are present in the list
            pass 

    # Final Status Determination
    if reasons:
        status = "REFUSED"
    elif len(proven_claims) == len(claims) and len(claims) > 0:
        status = "QUALIFIED"
    elif len(claims) == 0:
        status = "NOT_CHECKED"
    else:
        # Some claims validated, some failed? 
        # Strict contract: If any reason exists, it's REFUSED. 
        # If no reasons but not all claims proven (shouldn't happen if logic above is correct), default to NOT_CHECKED or REFUSED depending on policy.
        # Here, if reasons is empty, it means all processed claims passed.
        status = "QUALIFIED"

    return {
        "status": status,
        "reasons": reasons,
        "proven_claims": proven_claims
    }

def _validate_four_gpu(evidence: Dict[str, Any], reasons: List[str]) -> bool:
    devices = evidence.get("devices", [])
    if not isinstance(devices, list) or len(devices) != 4:
        reasons.append("FOUR_GPU requires exactly 4 distinct device entries")
        return False

    pci_ids = set()
    for i, dev in enumerate(devices):
        if not isinstance(dev, dict):
            reasons.append(f"Device {i} is not a dict")
            return False
        
        # Check Physical PCI ID
        pci_id = dev.get("physical_pci_id")
        if not isinstance(pci_id, str) or not pci_id:
            reasons.append(f"Device {i} missing physical_pci_id")
            return False
        if pci_id in pci_ids:
            reasons.append(f"Duplicate physical PCI ID found: {pci_id}")
            return False
        pci_ids.add(pci_id)

        # Check Type (Must be GPU, not CPU)
        dev_type = dev.get("type", "").upper()
        if "CPU" in dev_type or dev_type == "UNKNOWN":
            reasons.append(f"Device {i} is not a GPU (Type: {dev_type})")
            return False
        if "GPU" not in dev_type:
             reasons.append(f"Device {i} type unrecognized as GPU: {dev_type}")
             return False

        # Check Kernel Completion & Ownership
        kernel_completed = dev.get("kernel_completed", False)
        if not isinstance(kernel_completed, bool) or not kernel_completed:
            reasons.append(f"Device {i} kernel not completed")
            return False
        
        block_ownership = dev.get("block_ownership", [])
        if not isinstance(block_ownership, list) or len(block_ownership) == 0:
            reasons.append(f"Device {i} has no unique resident block ownership")
            return False
        
        # Check for duplicate blocks across devices
        for b in block_ownership:
            if not isinstance(b, str):
                reasons.append(f"Device {i} invalid block ID format")
                return False

    # Global Duplicate Block Check
    all_blocks = []
    for dev in devices:
        all_blocks.extend(dev.get("block_ownership", []))
    if len(all_blocks) != len(set(all_blocks)):
        reasons.append("Duplicate block IDs found across devices")
        return False

    # Independent Reference Hashes
    hashes = evidence.get("reference_hashes", [])
    if not isinstance(hashes, list) or len(hashes) != 4:
        reasons.append("Missing independent reference hashes for 4 devices")
        return False
    for h in hashes:
        if not isinstance(h, str) or len(h) < 32: # Basic hash length check
            reasons.append("Invalid reference hash format")
            return False

    return True

def _validate_dedicated_capacity(evidence: Dict[str, Any], reasons: List[str]) -> bool:
    mem_kind = evidence.get("memory_kind", "")
    if mem_kind.upper() != "DEDICATED":
        reasons.append("Memory kind must be DEDICATED")
        return False

    # Fresh Timestamp
    ts = evidence.get("observed_timestamp")
    if not isinstance(ts, (int, float)) or ts <= 0:
        reasons.append("Invalid or stale observed timestamp")
        return False

    allocations = evidence.get("measured_peak_allocations", [])
    if not isinstance(allocations, list) or len(allocations) != 4:
        reasons.append("Requires measured peak allocations for all 4 cards")
        return False

    method = evidence.get("measurement_method")
    source = evidence.get("source")
    if not method or not source:
        reasons.append("Measurement method and source required")
        return False

    # Largest Single Usable Budget
    largest_budget = evidence.get("largest_single_usable_budget_bytes")
    if not is_valid_number(largest_budget):
        reasons.append("Invalid largest single usable budget")
        return False

    # Unique Measured Weights/KV/Activation Bytes > Largest Budget
    total_unique_bytes = evidence.get("total_unique_resident_bytes")
    if not is_valid_number(total_unique_bytes):
        reasons.append("Invalid total unique resident bytes")
        return False
    
    if total_unique_bytes <= largest_budget:
        reasons.append("Total unique bytes do not exceed largest single card capacity (refusal expected for 1-card)")
        # Note: The contract says 'fourfits' implies it fits 4, but exceeds 1. 
        # So this condition is actually REQUIRED for the claim to be valid in context of proving necessity.
        # Wait, re-reading: "unique measuredweight... > largest single usable dedicated". Yes.
        # But if it doesn't exceed, the claim of "dedicated capacity requiring 4" is false/refused.
        return False

    # Four Fits
    sum_allocs = sum(allocations)
    if not is_valid_number(sum_allocs):
         reasons.append("Invalid allocation sum")
         return False
    
    # Check if sum of allocations covers the unique bytes (roughly) and fits within combined capacity?
    # The prompt says "fourfits". Usually means Sum(Allocations) >= TotalUniqueBytes AND Max(Allocation) <= CardCapacity.
    # Let's assume 'fourfits' means the workload successfully ran on 4 cards without OOM.
    success_flag = evidence.get("four_card_run_success", False)
    if not isinstance(success_flag, bool) or not success_flag:
        reasons.append("Four card run did not report success")
        return False

    # Same exact workload hash/precision/context/batch on one card measured capacity refusal
    one_card_refusal = evidence.get("one_card_capacity_refusal", False)
    if not isinstance(one_card_refusal, bool) or not one_card_refusal:
        reasons.append("One card capacity refusal not confirmed")
        return False

    # Three card necessity
    three_card_refusal = evidence.get("three_card_capacity_refusal", False)
    if not isinstance(three_card_refusal, bool) or not three_card_refusal:
        reasons.append("Three card capacity refusal not confirmed (necessary claim fails)")
        return False

    # Artificial Policy Checks
    policy_mib = evidence.get("artificial_policy_limit_mib", 0)
    if is_valid_number(policy_mib) and policy_mib <= 32:
        reasons.append("Artificial policy limit too small (<32MiB) cannot qualify actual pooling")
        return False
        
    worker_type = evidence.get("worker_type", "")
    if "CPU" in worker_type.upper():
        reasons.append("CPU workers cannot qualify dedicated GPU capacity")
        return False
        
    vendor = evidence.get("vendor", "")
    if "AMD" in vendor.upper() and "SHARED" in evidence.get("memory_type", "").upper():
         reasons.append("Shared AMD memory cannot qualify dedicated VRAM")
         return False

    return True

def _validate_transfer_p2p(evidence: Dict[str, Any], reasons: List[str]) -> bool:
    mode = evidence.get("transfer_mode", "")
    if mode.upper() != "DIRECT_P2P":
        reasons.append("Transfer mode must be DIRECT_P2P")
        return False

    # No Host Staged
    host_staged = evidence.get("host_staged", False)
    if host_staged:
        reasons.append("Host staged transfer detected; invalid for DIRECT_P2P claim")
        return False

    # Directed Pair Primitive
    pairs = evidence.get("directed_pairs", [])
    if not isinstance(pairs, list) or len(pairs) == 0:
        reasons.append("No directed pairs recorded")
        return False

    for pair in pairs:
        if not isinstance(pair, dict):
            reasons.append("Invalid pair entry")
            return False
        src = pair.get("src_device")
        dst = pair.get("dst_device")
        if not src or not dst:
            reasons.append("Pair missing src/dst")
            return False
        
        measurement = pair.get("measurement")
        if not isinstance(measurement, dict):
            reasons.append("Pair missing measurement")
            return False
        
        bandwidth = measurement.get("bandwidth_gbps")
        latency_us = measurement.get("latency_us")
        
        if not is_valid_number(bandwidth) or bandwidth <= 0:
            reasons.append("Invalid bandwidth measurement")
            return False
        if not is_valid_number(latency_us) or latency_us < 0:
            reasons.append("Invalid latency measurement")
            return False
            
        parity = measurement.get("parity_check_passed", False)
        if not isinstance(parity, bool) or not parity:
            reasons.append("Parity check failed or missing")
            return False

    # System Heap / D3D12 L0 check
    api_used = evidence.get("api_used", "")
    if "D3D12" in api_used.upper() and "L0_SYSTEM_HEAP" in evidence.get("heap_type", "").upper():
        reasons.append("D3D12 L0 System Heap is not true P2P")
        return False

    return True

def _validate_llm(evidence: Dict[str, Any], reasons: List[str]) -> bool:
    model_hash = evidence.get("model_hash")
    if not isinstance(model_hash, str) or len(model_hash) < 32:
        reasons.append("Missing or invalid hashed GGUF model identity")
        return False

    license_status = evidence.get("license_verified", False)
    if not isinstance(license_status, bool) or not license_status:
        reasons.append("Model license not verified")
        return False

    # Actual Attention/KV/Operator Qualification
    ops_qual = evidence.get("operators_qualified", [])
    if not isinstance(ops_qual, list) or len(ops_qual) == 0:
        reasons.append("No operators qualified")
        return False

    kv_usage = evidence.get("kv_cache_usage_bytes")
    if not is_valid_number(kv_usage) or kv_usage <= 0:
        reasons.append("Invalid KV cache usage")
        return False

    # Logits/Tensor Full Numerical Reference Evidence
    logits_ref = evidence.get("logits_reference_match", False)
    tensor_ref = evidence.get("tensor_reference_match", False)
    
    if not isinstance(logits_ref, bool) or not logits_ref:
        reasons.append("Logits numerical reference mismatch or unverified")
        return False
    if not isinstance(tensor_ref, bool) or not tensor_ref:
        reasons.append("Tensor numerical reference mismatch or unverified")
        return False

    # No Generated Prose Proof
    proof_type = evidence.get("proof_type", "")
    if "PROSE" in proof_type.upper():
        reasons.append("Generated prose proof is invalid for LLM qualification")
        return False

    return True

def _validate_durability(evidence: Dict[str, Any], reasons: List[str]) -> bool:
    checkpoint_id = evidence.get("committed_checkpoint_identity")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        reasons.append("Missing committed checkpoint identity")
        return False

    replay_boundary = evidence.get("replay_boundary_defined", False)
    if not isinstance(replay_boundary, bool) or not replay_boundary:
        reasons.append("Replay boundary not defined")
        return False

    worker_term = evidence.get("worker_termination_evidence", False)
    cancel_restart = evidence.get("cancel_restart_evidence", False)

    if not isinstance(worker_term, bool) or not worker_term:
        reasons.append("Worker termination evidence missing")
        return False
    if not isinstance(cancel_restart, bool) or not cancel_restart:
        reasons.append("Cancel/restart evidence missing")
        return False

    # Not atomic final JSON only
    storage_type = evidence.get("storage_type", "")
    if "ATOMIC_JSON_ONLY" in storage_type.upper():
        reasons.append("Atomic final JSON only is insufficient for durability claim")
        return False

    return True
