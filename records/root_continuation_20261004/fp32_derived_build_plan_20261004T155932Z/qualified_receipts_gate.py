"""Invoke only the admitted build controller's pure receipt validator."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CONTROLLER = HERE / "build_controller_DRAFT.py"
ADMISSION = HERE / "ROOT_BUILD_NATIVE_ADMISSION.json"
CONTROLLER_SHA256 = "c989cc4c8ccd915d499d1e441c5de6048064f1ca1aec37e00cbc4ecc81022202"
ADMISSION_SHA256 = "de83be81c64c08596bb87b7ffea8374a7ad8bbfd80973abf00d833729d47bfeb"
PYTHON_SHA256 = "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if digest(CONTROLLER) != CONTROLLER_SHA256:
        raise SystemExit("controller_pin_mismatch")
    if digest(ADMISSION) != ADMISSION_SHA256:
        raise SystemExit("admission_pin_mismatch")
    if digest(sys.executable) != PYTHON_SHA256:
        raise SystemExit("python_pin_mismatch")
    admission = json.loads(ADMISSION.read_text(encoding="utf-8"))
    watched = [
        CONTROLLER, ADMISSION,
        Path(admission["variant_path"]), Path(admission["cmd_exe"]),
        HERE / "CONTRACT.json",
        Path(admission["pure44_receipt_path"]),
        Path(admission["boundary_receipt_path"]),
        Path(admission["boundary_stderr_path"]),
        Path(admission["native_suite_receipt_path"]),
    ]
    before = {str(p): digest(p) for p in watched}
    spec = importlib.util.spec_from_file_location("pinned_build_controller_pure_gate", CONTROLLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.qualified_receipts(admission)
    after = {str(p): digest(p) for p in watched}
    if before != after:
        raise SystemExit("input_hash_changed")
    print(json.dumps({
        "status": "QUALIFIED_RECEIPTS_PASS",
        "result": result,
        "controller_sha256": CONTROLLER_SHA256,
        "root_admission_sha256": ADMISSION_SHA256,
        "python_sha256": PYTHON_SHA256,
        "input_hashes_unchanged": True,
        "native_or_build_calls": "NOT_ATTEMPTED",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
