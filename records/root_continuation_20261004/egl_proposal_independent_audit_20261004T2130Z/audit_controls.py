import ast, builtins, hashlib, importlib.util, json, os, pathlib, sys, traceback

SOURCE = pathlib.Path(r"E:\the_harness\records\factory_runs\20261004\intel_egl_two_prep_20261004T205649Z\root_budget_32k_16k\qwen_intel_exporter_sync_contract\source.qwen_untrusted.py")
SOURCE_SHA = "9da36c9700d1ecedde8f63913d4d72a953bfaf572e87df6753fc8388ca9742b0"
ROOT = pathlib.Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
if sha(SOURCE) != SOURCE_SHA:
    raise SystemExit("source pin mismatch before controls")
raw=SOURCE.read_text(encoding="utf-8")
tree=ast.parse(raw, filename=str(SOURCE))
allowed_top=(ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef, ast.ClassDef, ast.Expr)
for node in tree.body:
    if not isinstance(node, allowed_top):
        raise SystemExit("unexpected executable top-level node: "+type(node).__name__)
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        if any(alias.name.split('.')[0] not in {"json"} for alias in node.names):
            raise SystemExit("unexpected import")
    if isinstance(node, ast.ImportFrom) and (node.module or "").split('.')[0] not in {""}:
        raise SystemExit("unexpected from-import")

spec=importlib.util.spec_from_file_location("egl_contract_candidate_pinned", SOURCE)
module=importlib.util.module_from_spec(spec)
sys.dont_write_bytecode=True
spec.loader.exec_module(module)
if sha(SOURCE) != SOURCE_SHA:
    raise SystemExit("source pin changed after import")

# Prepare only fixture JSON within this owned evidence folder before activating the guard.
base={
  "schema_version": module.SCHEMA_VERSION,
  "evidence_id": "independent-audit-001",
  "scope": "SOURCE_PREP",
  "host": {"os":"Linux","kernel":"NOT_CHECKED","arch":"x86_64","native_linux":False},
  "producer": {"route":"raw_l0","device":{"pci":"NOT_CHECKED","uuid":"NOT_CHECKED","driver_version":"NOT_CHECKED"},"allocation":{"size_bytes":65536,"owner":"NOT_CHECKED","type":"DEVICE"},"layout":{"fourcc":"NOT_CHECKED","modifier":"NOT_CHECKED","stride":"NOT_CHECKED","offset":"NOT_CHECKED","plane_count":"NOT_CHECKED"},"fence":{"kind":"NOT_CHECKED"},"cache":{"flush_contract":"NOT_CHECKED"}},
  "consumer": {"platform":"EGL_PLATFORM_DEVICE_EXT","device":{"egl_device":"NOT_CHECKED","drm_render_node":"NOT_CHECKED","sysfs_pci_path":"NOT_CHECKED","vendor":"NOT_CHECKED"},"extensions":[],"format_query":{"fourcc":"NOT_CHECKED","modifier":"NOT_CHECKED","external_only":"NOT_CHECKED"},"import":dict(module.IMAGE_DESCRIPTOR),"sync":{"import_sync_type":"NOT_CHECKED"}},
  "payload":{"baseline_hash":"NOT_CHECKED","corruption_hash":"NOT_CHECKED","word_count":16384,"context_binding":"NOT_CHECKED","actual_work_proof":False},
  "artifacts":[{"name":name,"sha256":meta["sha256"],"path":str(ROOT/"MISSING"/name),"spans":["invented span"]} for name,meta in module.PRIMARY_SPANS.items()],
  "claims":{},
  "prerequisites":[{"id":"prep_only","scope":"no allocation or GPU work","status":"DECLARED"}],
  "driver_identity_binding":{"level_zero_driver_version":"NOT_CHECKED","egl_driver_version":"NOT_CHECKED","kernel_version":"NOT_CHECKED","bound":False,"tied_to_evidence_id":"independent-audit-001"},
  "requested_operations":{"allocate_export":False,"egl_import":False,"producer_write":False,"consumer_read":False,"parity":False},
  "declared_contract_ids":[]
}
cases={"baseline":base}
# Same trusted hashes but nonexistent artifact paths and fabricated nonempty spans.
cases["missing_paths_invented_spans"] = json.loads(json.dumps(base))
# Non-bool values bypass `is True` checks used for forbidden proof claims.
cases["string_claim"] = json.loads(json.dumps(base)); cases["string_claim"]["claims"]["p2p_proof"]="true"
cases["integer_claim"] = json.loads(json.dumps(base)); cases["integer_claim"]["claims"]["fence_proof"]=1
# Duplicate required artifact name is accepted when the last copy matches.
cases["duplicate_artifact_name"] = json.loads(json.dumps(base)); a=cases["duplicate_artifact_name"]["artifacts"][0]; cases["duplicate_artifact_name"]["artifacts"].insert(0,{"name":a["name"],"sha256":"0"*64,"path":"wrong","spans":["bad"]})
# An impossible operation ordering is not validated; metadata alone still returns ANALYSIS.
cases["consumer_without_producer"] = json.loads(json.dumps(base)); cases["consumer_without_producer"]["requested_operations"]={"consumer_read":True,"producer_write":False}
# Candidate's own claimed word count/digest and payload proof are not reconciled against supplied bytes.
cases["contradictory_payload_claim"] = json.loads(json.dumps(base)); cases["contradictory_payload_claim"]["payload"].update({"word_count":1,"baseline_hash":"0"*64,"actual_work_proof":True,"rmse":float("nan")})
# Operation flags are not type-checked. A string false is truthy; with its declared key this reaches ANALYSIS.
cases["string_false_operation"] = json.loads(json.dumps(base)); cases["string_false_operation"]["producer"]["device"]["driver_version"]="v1"; cases["string_false_operation"]["requested_operations"]={"allocate_export":"false"}; cases["string_false_operation"]["declared_contract_ids"]=["l0_dma_buf_export_api_exists"]
# A malformed nested object escapes validate_candidate instead of returning a shaped refusal.
cases["malformed_producer_type"] = json.loads(json.dumps(base)); cases["malformed_producer_type"]["producer"]=[]
paths={}
for name,obj in cases.items():
    p=ROOT/(name+".json")
    p.write_text(json.dumps(obj,sort_keys=True,separators=(",",":")),encoding="utf-8")
    paths[str(p.resolve())]=p

# Runtime guard: only read the staged JSON case paths; reject writes, network, process, and ctypes.
real_open=builtins.open
attempts={"blocked_imports":[],"blocked_open":[],"process_calls":0,"native_calls":0}
def guarded_open(file, mode="r", *args, **kwargs):
    path=str(pathlib.Path(file).resolve())
    if mode not in ("r","rt") or path not in paths:
        attempts["blocked_open"].append({"path":path,"mode":mode})
        raise PermissionError("pure audit permits only staged JSON reads")
    return real_open(path,mode,*args,**kwargs)
real_import=builtins.__import__
def guarded_import(name, *args, **kwargs):
    root=name.split('.')[0]
    if root in {"socket","urllib","http","subprocess","multiprocessing","ctypes","win32api","win32process"}:
        attempts["blocked_imports"].append(root)
        raise PermissionError("pure audit blocked import: "+root)
    return real_import(name,*args,**kwargs)
builtins.open=guarded_open
builtins.__import__=guarded_import
for name in ("system","popen","fork","forkpty","spawnl","spawnle","spawnlp","spawnlpe","spawnv","spawnve","spawnvp","spawnvpe","startfile"):
    if hasattr(os,name):
        setattr(os,name,lambda *a,_n=name,**k: (_ for _ in ()).throw(PermissionError("blocked process API "+_n)))

results=[]
for name,p in paths.items():
    try:
        r=module.validate_candidate(name)
        results.append({"case":pathlib.Path(name).stem,"result":r})
    except Exception as exc:
        results.append({"case":pathlib.Path(name).stem,"exception":type(exc).__name__,"detail":str(exc)})

builtins.open=real_open
builtins.__import__=real_import
if sha(SOURCE) != SOURCE_SHA:
    raise SystemExit("source pin mismatch after controls")
summary={"source_sha256":SOURCE_SHA,"cases":results,"guard_observations":attempts,"native_calls":0,"process_calls":0,"network_calls":0,"candidate_module_imported":True,"native_api_execution":False,"note":"Candidate validator functions were called on owned JSON fixtures only; no GPU/API/ctypes/process/network operation occurred."}
(ROOT/"pure_control_results.json").write_text(json.dumps(summary,indent=2,sort_keys=True),encoding="utf-8")
print(json.dumps(summary,sort_keys=True))


