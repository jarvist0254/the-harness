# Independent comparator RED gate

Actual source SHA `56a55d66798f476cc0cd39d0fd21942b046d24e13985e76af41ecf85ca9de1da`: 62 controls, 21 failures, zero errors, zero skips, zero forbidden native/process/network/GPU calls. Exact hash was checked before and after candidate execution. Owned evaluator exited within sixty seconds and is absent.

Meaningful failures:
- Caller authority optional (lines 205): Empty expected dictionary yields match; six expected pins are not required.
- Token sequence insufficient (lines 76): Short same sequences and different CPU/GPU sequences yield match instead of exact sixteen0..15 refusal.
- Integer fields compare numerically (lines 52): Float model_bytes/context/ordinal/strides accepted; float nbytes reaches struct.error.
- Canonical alias not canonicalized (lines 93): attn_norm-00 accepted, violating strict canonical identity.
- Root link erased before check (lines 129): Actual owned root symlink is resolved away before reparse inspection and falsely matches.
- Metadata classified as numeric divergence (lines 218): Missing/extra/order/op/shape mismatches return DIAGNOSTIC_DIVERGENCE instead of CaptureError/NOT_CHECKED artifact refusal.
- Fixed tolerance policy not enforced (lines 213): 0.02 and0 are accepted despite root exact0.01 policy.
- All-capture statistics missing (lines 251): Only first threshold-divergent capture emits stats; matching captures and within-tolerance noise are not reported.
- Authority extras ignored (lines 187): Origin qualificationGPU_PASS, manifest production_pass and node reference_scale fields ignored.

Synthetic metadata pins do not authenticate source, model, or native execution. Passing comparison cannot qualify GPU/model/capacity/P2P operation. Input files remained unchanged. Provider-generated tests were not executed. Source was not edited.

Detailed results, actual observations, source bindings, and limits are in INDEPENDENT_REVIEW.json and RED_results.json.
