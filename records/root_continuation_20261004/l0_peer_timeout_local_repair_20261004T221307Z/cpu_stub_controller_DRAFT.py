from __future__ import annotations
import hashlib,json,os,subprocess,threading,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(r"E:\the_harness\records\root_continuation_20261004\l0_peer_timeout_local_repair_20261004T221307Z")
SRC=ROOT/"peer_copy_local.cpp"
FAKE=ROOT/"fake_level_zero_local.cpp"
FAKEOBJ=ROOT/"fake_level_zero_local.o"
EXE=ROOT/"peer_copy_cpu_fake"
OBJ=ROOT/"peer_copy_local.o"
ADMIT=ROOT/"cpu_stub_execution_admission.pending.json"
REVIEW=ROOT/"STATIC_REVIEW.md"
HDR=Path(r"E:\the_harness\records\toolchains\level_zero_20261004\sdk\include\level_zero\ze_api.h")
PYTHON=Path(r"C:\Users\thoma\AppData\Local\Programs\Python\Python310\python.exe")
WSL=Path(r"C:\windows\system32\wsl.exe")
DISTRO="Ubuntu-24.04"
LINUX_ROOT="/mnt/e/the_harness/records/root_continuation_20261004/l0_peer_timeout_local_repair_20261004T221307Z"
LINUX_INC="/mnt/e/the_harness/records/toolchains/level_zero_20261004/sdk/include"
LINUX_FAKE=LINUX_ROOT+"/fake_level_zero_local.cpp"
LINUX_OBJ=LINUX_ROOT+"/peer_copy_local.o"
LINUX_FAKE_OBJ=LINUX_ROOT+"/fake_level_zero_local.o"
LINUX_EXE=LINUX_ROOT+"/peer_copy_cpu_fake"
CXX="/usr/bin/c++"
TIMEOUT="/usr/bin/timeout"
READELF="/usr/bin/readelf"
EXPECTED={"source":"284e6109f1d32db945ab7719bb77d9a1fc734887c9ebe5068bebc4ac0eef9f59",
"fake":"96e2f0df7108f1ce31a540c18ae3f50f09b97fa54c5628f8556b86873cbe62d2".replace(" ",""),
"header":"c3fb4067e553c31c722cfe934943291b1267402294e7074d34f06b0037ce70de",
"object":"888754880338f9752254dab8a6173239cff630f366716e11f8a4c7705efa6b80",
"python":"3cce33d75d6fdae4e004d0bdf149320b3147482a9caf370079dcb9c191a1b260",
"wsl":"7e9f5cee6d641481e5a942f0e08563bae9c17ee55f0aad888f9aa0be9a5d4757",
"cxx":"1353e9bdd29a7295c7226bf6c63abccce056d8cac31f112e5cdbecc3f28c2769",
"fakeobj":"PENDING_ROOT_LINK_PIN",
"exe":"PENDING_ROOT_LINK_PIN"}
CAP=128*1024
CREATE_NO_WINDOW=getattr(subprocess,"CREATE_NO_WINDOW",0x08000000)
UUIDS=["00112233445566778899aabbccddeeff","ffeeddccbbaa99887766554433221100"]

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()
def utc():return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
def wsl(args):return [str(WSL),"-d",DISTRO,"--exec",*args]
def bounded(args,s,grace=3):return [TIMEOUT,"--signal=TERM",f"--kill-after={grace}s",f"{s}s",*args]
def run(label,argv,outer,run_dir,index):
 started=utc(); t0=time.monotonic(); p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,cwd=str(ROOT),creationflags=CREATE_NO_WINDOW)
 bufs={"stdout":bytearray(),"stderr":bytearray()}; ov=threading.Event()
 def drain(pipe,key):
  while True:
   chunk=pipe.read(8192)
   if not chunk:return
   room=CAP-len(bufs[key])
   if room>0:bufs[key].extend(chunk[:room])
   if len(chunk)>room:ov.set()
 readers=[threading.Thread(target=drain,args=(p.stdout,"stdout"),daemon=True),threading.Thread(target=drain,args=(p.stderr,"stderr"),daemon=True)]
 for x in readers:x.start()
 timed=False; killed=False
 while p.poll() is None:
  if ov.is_set() or time.monotonic()-t0>=outer:
   timed=not ov.is_set();killed=True;p.kill();break
  time.sleep(.05)
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:killed=True
 for x in readers:x.join(timeout=5)
 rec={"label":label,"argv":argv,"pid":p.pid,"started_utc":started,"elapsed_seconds":round(time.monotonic()-t0,3),"returncode":p.poll(),"outer_timeout":timed,"outer_killed_owned_wsl_client":killed,"stream_overflow":ov.is_set(),"owned_wsl_client_exited":p.poll() is not None}
 for key in ("stdout","stderr"):
  data=bytes(bufs[key]);path=run_dir/f"{index:02d}_{label}.{key}.bin";path.write_bytes(data);rec[key+"_path"]=str(path);rec[key+"_sha256"]=hashlib.sha256(data).hexdigest();rec[key+"_bytes"]=len(data)
 return rec

def parse_json(path):return json.loads(Path(path).read_text(encoding="utf-8",errors="strict"))
def main():
 mode=os.environ.get("STUB_PHASE","build")
 if mode not in ("build","run"):raise SystemExit("bad phase")
 if sha(SRC)!=EXPECTED["source"] or sha(FAKE)!=EXPECTED["fake"] or sha(HDR)!=EXPECTED["header"] or sha(OBJ)!=EXPECTED["object"] or sha(PYTHON)!=EXPECTED["python"] or sha(WSL)!=EXPECTED["wsl"]:raise SystemExit("refuse: pinned local input mismatch")
 if mode=="run" and (sha(FAKEOBJ)!=EXPECTED["fakeobj"] or sha(EXE)!=EXPECTED["exe"]):raise SystemExit("refuse: pinned CPU fake artifact mismatch")
 admission=json.loads(ADMIT.read_text(encoding="utf-8-sig"))
 if admission.get("scope")!="STATIC_ABI_AND_STUB_LINK_ADMISSION_FOR_CPU_TESTS_ONLY" or admission.get("admitted") is not True or admission.get("candidate_source_sha256")!=EXPECTED["source"] or admission.get("official_header_sha256")!=EXPECTED["header"] or admission.get("static_review_sha256")!=sha(REVIEW):raise SystemExit("refuse: static ABI/stub admission mismatch")
 if mode=="run" and (sha(FAKEOBJ)!=admission.get("fake_object_sha256") or sha(EXE)!=admission.get("fake_executable_sha256")):raise SystemExit("refuse: execution artifacts differ from static admission")
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ");rd=ROOT/("stub_build_"+stamp if mode=="build" else "stub_runs_"+stamp);rd.mkdir(exist_ok=False)
 li=[LINUX_ROOT+"/peer_copy_local.cpp",LINUX_FAKE,LINUX_INC+"/level_zero/ze_api.h",CXX]
 if mode=="run":li.extend([LINUX_ROOT+"/fake_level_zero_local.o",LINUX_ROOT+"/peer_copy_cpu_fake"])
 hashes=lambda:run("pins",wsl(bounded(["/usr/bin/sha256sum",*li],5,2)),12,rd,1)
 results=[];pre=hashes();results.append(pre)
 if pre["returncode"]!=0 or pre["outer_timeout"] or pre["stream_overflow"]:raise SystemExit("refuse: WSL pin preflight failed")
 premap={line.split(None,1)[1].lstrip(" *"):line.split(None,1)[0].lower() for line in Path(pre["stdout_path"]).read_text(encoding="utf-8").splitlines()}
 need={LINUX_ROOT+"/peer_copy_local.cpp":EXPECTED["source"],LINUX_FAKE:EXPECTED["fake"],LINUX_INC+"/level_zero/ze_api.h":EXPECTED["header"],CXX:EXPECTED["cxx"]}
 if any(premap.get(k)!=v for k,v in need.items()):raise SystemExit("refuse: WSL visible pin mismatch")
 if mode=="build":
  for index,label,args,limit in [
   (2,"fake_object",[CXX,"-std=c++17","-I"+LINUX_INC,"-c",LINUX_FAKE,"-o",LINUX_FAKE_OBJ],60),
   (3,"link_cpu_fake",[CXX,"-std=c++17",LINUX_OBJ,LINUX_FAKE_OBJ,"-o",LINUX_EXE],60),
   (4,"no_level_zero_dependency",[READELF,"-d",LINUX_EXE],5)]:
   rr=run(label,wsl(bounded(args,limit,5)),limit+15,rd,index);results.append(rr)
   if rr["returncode"]!=0 or rr["outer_timeout"] or rr["stream_overflow"] or not rr["owned_wsl_client_exited"]:break
  if results[-1]["label"]=="no_level_zero_dependency" and "libze_loader" in Path(results[-1]["stdout_path"]).read_text(encoding="utf-8",errors="replace"):raise SystemExit("refuse: fake executable links Level Zero loader")
 else:
  cases=[
   (2,"clean","clean",UUIDS,0,"PEER_COPY_PAYLOAD_OBSERVED"),
   (3,"corrupt","clean",UUIDS+ ["--inject-corruption"],1,"FAIL"),
   (4,"peer_unavailable","peer_unavailable",UUIDS,2,"NOT_CHECKED"),
   (5,"fence_timeout","fence_timeout",UUIDS,1,"FAIL"),
   (6,"cleanup_failure","cleanup_failure",UUIDS,1,"FAIL"),
   (7,"malformed_cli","clean",["bad_uuid",UUIDS[1]],2,"NOT_CHECKED"),
   (8,"surplus_cli","clean",UUIDS+["unexpected"],1,"FAIL"),
   (9,"duplicate_flag_cli","clean",UUIDS+["--inject-corruption","--inject-corruption"],1,"FAIL"),
   (10,"fence_timeout_copy","fence_timeout_copy",UUIDS,1,"FAIL"),
   (11,"fence_timeout_readback","fence_timeout_readback",UUIDS,1,"FAIL"),
   (12,"fence_timeout_corrupt","fence_timeout_corrupt",UUIDS+["--inject-corruption"],1,"FAIL")]
  cases_results=[]
  for index,label,fakemode,args,expected_exit,expected_status in cases:
   argv=wsl(bounded(["/usr/bin/env","HARNESS_FAKE_MODE="+fakemode,LINUX_EXE,*args],5,3))
   rr=run(label,argv,12,rd,index);results.append(rr)
   if rr["returncode"]!=expected_exit or rr["outer_timeout"] or rr["stream_overflow"] or not rr["owned_wsl_client_exited"]:raise SystemExit("stub case process gate failed: "+label)
   doc=parse_json(rr["stdout_path"])
   if doc.get("status")!=expected_status:raise SystemExit("stub JSON status mismatch: "+label)
   err=Path(rr["stderr_path"]).read_text(encoding="utf-8",errors="replace")
   if (("FAKE_SUMMARY" not in err and "FAKE_PENDING" not in err) or "backing=HOST_MALLOC_ONLY" not in err):raise SystemExit("missing fake-only trace: "+label)
   doc["fake_summary_line"]=[line for line in err.splitlines() if line.startswith(("FAKE_SUMMARY","FAKE_PENDING"))][-1]
   cases_results.append({"case":label,"mode":fakemode,"argv":args,"exit":expected_exit,"json":doc,"stderr_summary":doc["fake_summary_line"],"stdout_path":rr["stdout_path"],"stderr_path":rr["stderr_path"]})
  (rd/"case_results.json").write_text(json.dumps(cases_results,indent=2)+"\n",encoding="utf-8")
 after=run("pins_after",wsl(bounded(["/usr/bin/sha256sum",*li],5,2)),12,rd,13 if mode=="run" else 5);results.append(after)
 if after["returncode"]!=0 or after["outer_timeout"] or after["stream_overflow"]:raise SystemExit("post-run pins failed")
 aftermap={line.split(None,1)[1].lstrip(" *"):line.split(None,1)[0].lower() for line in Path(after["stdout_path"]).read_text(encoding="utf-8").splitlines()}
 if any(aftermap.get(k)!=premap.get(k) for k in li):raise SystemExit("before/after input hash changed")
 rec={"scope":"CPU_ONLY_OFFICIAL_HEADER_STUB_NO_DEVICE_NO_LEVEL_ZERO_LOADER","phase":mode,"status":"RECORDED","local_pins":{"source":sha(SRC),"fake_stub":sha(FAKE),"header":sha(HDR),"candidate_object":sha(OBJ),"fake_object":sha(FAKEOBJ) if FAKEOBJ.exists() else None,"fake_executable":sha(EXE) if EXE.exists() else None,"python":sha(PYTHON),"wsl":sha(WSL)},"linux_pins_before":premap,"linux_pins_after":aftermap,"results":results,"no_gpu_calls":True,"no_level_zero_loader_linked_or_loaded":True,"device_allocations_are_host_malloc":True,"candidate_or_provider_tests":"not run in build phase" if mode=="build" else "CPU fake API only; no device API"}
 (rd/"receipt.json").write_text(json.dumps(rec,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"phase":mode,"status":"RECORDED","folder":str(rd),"results":[{k:x.get(k) for k in ("label","pid","returncode","elapsed_seconds","outer_timeout","stream_overflow","owned_wsl_client_exited","stdout_bytes","stderr_bytes")} for x in results]}))
if __name__=="__main__":main()

