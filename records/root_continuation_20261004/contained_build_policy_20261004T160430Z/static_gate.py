"""AST/byte-only static guard; this script never imports the candidate module."""
import ast
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = Path(
    r"E:\the_harness\records\root_continuation_20261004\supervisor_cleanup_root_repair\contained_supervisor_revision2.py"
)
CANDIDATE = HERE / "contained_build_supervisor.py"
TESTS = HERE / "test_build_policy_boundaries.py"
BASELINE_SHA = "3cb1e44e35ea6c2ef9c01e0d329fb0df98c7785056d65e33ced52ec04706e51c"
CANDIDATE_SHA = "fa907e8637870521b573922f6e939e56e388439fa61dc1a76fbeb53f7ad45ef3"
TESTS_SHA = "c9bbbb16a2f4c4eca94a3bf9abfa530d8222874fd185dcd7fc9a2674658fc11c"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


base_bytes = BASELINE.read_bytes()
candidate_bytes = CANDIDATE.read_bytes()
old = b'_int(manifest.get("deadline_seconds"), 1, 60, "deadline")'
new = b'_int(manifest.get("deadline_seconds"), 1, 600, "deadline")'
assert sha(BASELINE) == BASELINE_SHA
assert sha(CANDIDATE) == CANDIDATE_SHA
assert base_bytes.count(old) == 1
assert candidate_bytes == base_bytes.replace(old, new, 1)
assert b'_int(manifest.get("log_limit_bytes"), 1024, 131072, "log_limit")' in candidate_bytes
assert b'_int(manifest.get("startup_seconds"), 1, 10, "startup")' in candidate_bytes

base_tree = ast.parse(base_bytes.decode("utf-8"))
candidate_tree = ast.parse(candidate_bytes.decode("utf-8"))
changed = []
for node in ast.walk(candidate_tree):
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_int"
        and len(node.args) >= 4
        and isinstance(node.args[0], ast.Call)
        and isinstance(node.args[0].func, ast.Attribute)
        and node.args[0].func.attr == "get"
        and isinstance(node.args[0].args[0], ast.Constant)
        and node.args[0].args[0].value == "deadline_seconds"
        and isinstance(node.args[2], ast.Constant)
        and node.args[2].value == 600
    ):
        changed.append(node)
assert len(changed) == 1
changed[0].args[2].value = 60
assert ast.dump(base_tree, include_attributes=False) == ast.dump(candidate_tree, include_attributes=False)

test_source = TESTS.read_text(encoding="utf-8")
assert "DENIED_IMPORTS = {\"_winapi\", \"ctypes\", \"msvcrt\", \"subprocess\"}" in test_source
assert "test_old_supervisor_keeps_original_deadline_boundary" in test_source
assert "test_build_policy_accepts_only_integer_deadlines_through_600" in test_source
assert "test_log_limit_stays_capped_at_131072" in test_source
assert "test_import_and_validation_never_request_native_or_process_modules" in test_source
assert TESTS_SHA != "TO_BE_PINNED" and sha(TESTS) == TESTS_SHA

print("BYTE_GUARD=PASS exactly one literal replacement")
print("AST_GUARD=PASS normalized AST identical after restoring deadline upper bound")
print("UNCHANGED=startup maximum 10; log maximum 131072")
print(f"BASELINE_SHA256={sha(BASELINE)}")
print(f"CANDIDATE_SHA256={sha(CANDIDATE)}")
print(f"TESTS_SHA256={sha(TESTS)}")
print("NATIVE_OR_PROCESS_IMPORT=NOT_ATTEMPTED")
