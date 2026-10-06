"""ROOT metadata preparation only; does not launch a process or GPU work."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

PHASE = Path("E:/the_harness/records/root_continuation_20261004")
BUILD = Path("E:/the_harness/records/build_vulkan_fp32_staging_20261004T155932Z")
HELPER = PHASE / "fixture_runtime_win32_query_revision2.py"

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def pin(path):
    path = path.resolve(strict=True)
    return {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", choices=("operator", "model"), required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--device", choices=("Vulkan0", "Vulkan1"), default="Vulkan0")
    p.add_argument("--reverse", action="store_true")
    p.add_argument("--corrupt", action="store_true")
    args = p.parse_args()
    if not args.name.isidentifier():
        raise ValueError("fresh identifier required")
    build_result = json.loads((BUILD / "evidence/attempt5_compiler_root_cleanup/controller_result.json").read_text())
    if build_result.get("all_completed") is not True or build_result.get("failure") is not None or build_result.get("integrity_failure") is not None:
        raise ValueError("accepted fresh build missing")
    manifest = json.loads((BUILD / "evidence/attempt5_compiler_root_cleanup/fresh_dll_manifest.json").read_text())
    dlls = [pin(Path(item["path"])) for item in manifest]
    if any(a != b for a, b in zip(dlls, manifest)) or len(dlls) != 5:
        raise ValueError("actual fresh DLL manifest changed")
    spec = importlib.util.spec_from_file_location("runtime_metadata", HELPER)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    model = None
    supporting = []
    if args.fixture == "operator":
        fixture_dir = PHASE / "fp32_staging_operator_fixture_revision2_20261004T155012Z"
        source = fixture_dir / "fp32_staging_operator.cpp"
        executable = fixture_dir / "compile_original_20261004T155012Z/fp32_staging_operator.exe"
        argv = ["--device", args.device]
    else:
        fixture_dir = Path("E:/the_harness/records/vulkan_llm_qualification_20261004/fixture_kv_f32")
        source = Path("E:/the_harness/records/factory_runs/20261004/coherent_repair_kv_20261004T130000Z/grok_kv_f32/llama_logits_kv_f32.cpp")
        executable = fixture_dir / "llama_logits_kv_f32.exe"
        model = pin(Path("E:/the_harness/records/models/qwen3_06b_f32_derived/Qwen3-0.6B-Q8_0-dequant-F32.gguf"))
        supporting = [pin(Path("E:/the_harness/records/build_vulkan_real/build/bin/llama.dll"))]
        argv = ["--model", model["path"], "--expected-sha256", model["sha256"],
                "--devices", "Vulkan1,Vulkan0" if args.reverse else "Vulkan0,Vulkan1", "--kv-f32"]
    if args.corrupt:
        argv.append("--inject-logit-corruption" if args.fixture == "model" else "--inject-corruption")
    destination = PHASE / (args.name + "_admission.json")
    payload = {"schema": 1, "adjudicator": "ROOT", "launch": True,
               "fixture": args.fixture, "helper": pin(HELPER), "python": pin(Path(sys.executable)),
               "source": pin(source), "executable": pin(executable), "dlls": dlls,
               "supporting_dlls": supporting, "system_loader": pin(Path("C:/Windows/System32/vulkan-1.dll")),
               "model": model, "runtime_dir": str(PHASE / args.name), "arguments": argv,
               "timeout_seconds": 30 if args.fixture == "operator" else 60,
               "stream_limit_bytes": 2097152, "child_flags": m.FLAGS,
               "parent_runtime_environment": m.relevant_environment()}
    if (payload["executable"]["sha256"], payload["source"]["sha256"]) != m.PINS[args.fixture][:2]:
        raise ValueError("unchanged fixture identity mismatch")
    with destination.open("x", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(json.dumps({"admission": str(destination), "sha256": digest(destination),
                      "runtime_dir": payload["runtime_dir"], "scope": "metadata only; no execution"}))

if __name__ == "__main__":
    main()
