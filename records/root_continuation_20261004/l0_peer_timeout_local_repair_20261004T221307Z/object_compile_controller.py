from __future__ import annotations
import hashlib, json, os, subprocess, threading, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"E:\the_harness\records\root_continuation_20261004\l0_peer_timeout_local_repair_20261004T221307Z")
ORIGINAL = Path(r"E:\the_harness\records\root_continuation_20261004\l0_peer_errorcode_compile_20261004T2151Z\peer_copy_compile.cpp")
SOURCE = ROOT / "peer_copy_local.cpp"
HEADER = Path(r"E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h")
PYTHON = Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
WSL = Path(r"C:\windows\system32\wsl.exe")
DISTRO = "Ubuntu-24.04"
LINUX_ROOT = "/mnt/e/the_harness/records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z"
LINUX_SOURCE = LINUX_ROOT + "/peer_copy_local.cpp"
LINUX_HEADER = "/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include"
LINUX_OBJ = LINUX_ROOT + "/peer_copy_local.o"
COMPILER = "/usr/bin/c++"
TIMEOUT = "/usr/bin/timeout"
HASH_TOOL = "/usr/bin/sha256sum"
EXPECTED = {
    "original_sha256": "6185dcf242e4c847544c07455468119d67fae35d5aaf341ebaa8d14a0b920aa6",
    "candidate_sha256": "284e6109f1d32db945ab7719bb77d9a1fc734887c9ebe5068bebc4ac0eef9f59",
    "header_sha256": "c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de",
    "python_sha256": "3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260",
    "wsl_sha256": "7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757",
    "compiler_sha256": "1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769",
}
CAP = 128 * 1024
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def write_new(path: Path, data: bytes) -> None:
    with path.open("xb") as f:
        f.write(data)

def run_owned(label: str, argv: list[str], outer_seconds: int) -> dict:
    started = time.monotonic()
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            shell=False, cwd=str(ROOT), creationflags=CREATE_NO_WINDOW)
    b = {"stdout": bytearray(), "stderr": bytearray()}
    overflow = threading.Event()
    def drain(pipe, key):
        while True:
            chunk = pipe.read(8192)
            if not chunk: return
            room = CAP - len(b[key])
            if room > 0: b[key].extend(chunk[:room])
            if len(chunk) > room: overflow.set()
    readers = [threading.Thread(target=drain,args=(proc.stdout,"stdout"),daemon=True),
               threading.Thread(target=drain,args=(proc.stderr,"stderr"),daemon=True)]
    for t in readers: t.start()
    timeout = False
    while proc.poll() is None:
        if overflow.is_set() or time.monotonic() - started >= outer_seconds:
            timeout = not overflow.is_set()
            proc.kill()  # only this retained WSL client handle
            break
        time.sleep(.05)
    try: proc.wait(timeout=5)
    except subprocess.TimeoutExpired: pass
    for t in readers: t.join(timeout=5)
    return {"label":label,"argv":argv,"pid":proc.pid,"returncode":proc.poll(),
            "elapsed_seconds":round(time.monotonic()-started,3),"outer_timeout":timeout,
            "stream_overflow":overflow.is_set(),"owned_wsl_client_exited":proc.poll() is not None,
            "stdout":bytes(b["stdout"]),"stderr":bytes(b["stderr"])}

def save(run_dir: Path, i: int, result: dict) -> dict:
    for key in ("stdout","stderr"):
        data=result.pop(key); p=run_dir/f"{i:02d}_{result['label']}.{key}.bin"; write_new(p,data)
        result[key+"_path"]=str(p); result[key+"_sha256"]=hashlib.sha256(data).hexdigest(); result[key+"_bytes"]=len(data)
    return result

def wsl(args: list[str]) -> list[str]: return [str(WSL),"-d",DISTRO,"--exec",*args]
def bounded(args: list[str], seconds: int, grace: int=5) -> list[str]:
    return [TIMEOUT,"--signal=TERM",f"--kill-after={grace}s",f"{seconds}s",*args]
def main() -> int:
    run_dir=ROOT/"compile_run"
    run_dir.mkdir(exist_ok=False)
    if sha(ORIGINAL)!=EXPECTED["original_sha256"] or sha(SOURCE)!=EXPECTED["candidate_sha256"] or sha(HEADER)!=EXPECTED["header_sha256"] or sha(PYTHON)!=EXPECTED["python_sha256"] or sha(WSL)!=EXPECTED["wsl_sha256"]:
        raise SystemExit("local preflight pin mismatch")
    orig=ORIGINAL.read_text(encoding="utf-8"); cand=SOURCE.read_text(encoding="utf-8")
    if (ROOT/"peer_copy_local.o").exists(): raise SystemExit("refuse overwrite existing object")
    results=[]; failure=None; version=None
    hash_targets=[LINUX_SOURCE,LINUX_HEADER+"/level_zero/ze_api.h",COMPILER]
    r=run_owned("pins_before",wsl(bounded([HASH_TOOL,*hash_targets],5,2)),12); r=save(run_dir,1,r); results.append(r)
    if r["returncode"]!=0 or r["outer_timeout"] or r["stream_overflow"]: failure="PIN_PREFLIGHT_FAILED"
    else:
        lines=Path(r["stdout_path"]).read_text(encoding="utf-8",errors="strict").splitlines()
        pinmap={line.split(None,1)[1].lstrip(" *"):line.split(None,1)[0].lower() for line in lines if len(line.split(None,1))==2}
        required={LINUX_SOURCE:EXPECTED["candidate_sha256"],LINUX_HEADER+"/level_zero/ze_api.h":EXPECTED["header_sha256"],COMPILER:EXPECTED["compiler_sha256"]}
        if any(pinmap.get(k)!=v for k,v in required.items()): failure="PIN_PREFLIGHT_MISMATCH"
    if failure is None:
        r=run_owned("compiler_version",wsl(bounded([COMPILER,"--version"],5,2)),12); r=save(run_dir,2,r); results.append(r)
        if r["returncode"]!=0 or r["outer_timeout"] or r["stream_overflow"]: failure="COMPILER_VERSION_FAILED"
        else:
            version=Path(r["stdout_path"]).read_text(encoding="utf-8",errors="replace")
            if "13.3.0" not in version: failure="UNEXPECTED_COMPILER_VERSION"
    if failure is None:
        args=[COMPILER,"-std=c++17","-c","-I"+LINUX_HEADER,LINUX_SOURCE,"-o",LINUX_OBJ]
        r=run_owned("compile",wsl(bounded(args,45,5)),60); r=save(run_dir,3,r); results.append(r)
        if r["returncode"]!=0 or r["outer_timeout"] or r["stream_overflow"] or not r["owned_wsl_client_exited"]: failure="COMPILE_FAILED_OR_BOUNDED_STOP"
    after=run_owned("pins_after",wsl(bounded([HASH_TOOL,*hash_targets],5,2)),12); after=save(run_dir,4,after); results.append(after)
    beforemap=None; aftermap=None
    try:
        if results[0]["returncode"]==0 and results[3]["returncode"]==0:
            def parse(p):
                ret={}
                for line in Path(p).read_text(encoding="utf-8",errors="strict").splitlines():
                    h,path=line.split(None,1); ret[path.lstrip(" *")]=h.lower()
                return ret
            beforemap=parse(results[0]["stdout_path"]); aftermap=parse(after["stdout_path"])
            if any(beforemap.get(k)!=aftermap.get(k) for k in hash_targets): failure=failure or "PIN_CHANGED_DURING_COMPILE"
    except Exception as e: failure=failure or "POST_PIN_PARSE_FAILED: "+repr(e)
    obj=ROOT/"peer_copy_local.o"
    if failure is None and (not obj.is_file() or obj.stat().st_size<=0): failure="OBJECT_OUTPUT_MISSING"
    receipt={"scope":"OBJECT_ONLY_CXX17_COMPILE_NO_LINK_NO_RUNTIME","status":"COMPILE_PASS" if failure is None else "COMPILE_FAIL_OR_REFUSED",
             "candidate":str(SOURCE),"candidate_sha256":sha(SOURCE),"original":str(ORIGINAL),"original_sha256":sha(ORIGINAL),
             "header":str(HEADER),"header_sha256":sha(HEADER),"compiler_linux":"/usr/bin/c++","compiler_version":version,
             "object_path":str(obj) if obj.exists() else None,"object_bytes":obj.stat().st_size if obj.exists() else None,
             "object_sha256":sha(obj) if obj.exists() else None,"change_gate":{"local_derivative_attribution":"Root-authorized finite-wait quarantine and strictCLI correction; original immutable"},
             "failure":failure,"results":results,"input_pins_before":beforemap,"input_pins_after":aftermap,"provider_tests_executed":False,"candidate_executed":False,"native_level_zero_calls":False,"gpu_calls":False}
    (ROOT/"compile_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":receipt["status"],"failure":failure,"candidate_sha256":receipt["candidate_sha256"],"object_bytes":receipt["object_bytes"],"results":[{k:v for k,v in x.items() if k in ("label","pid","returncode","elapsed_seconds","outer_timeout","stream_overflow","owned_wsl_client_exited","stdout_bytes","stderr_bytes")} for x in results]}))
    return 0 if failure is None else 1
if __name__=="__main__": raise SystemExit(main())
