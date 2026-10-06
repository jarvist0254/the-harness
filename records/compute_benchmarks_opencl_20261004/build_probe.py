import pathlib,subprocess,tarfile,json,hashlib,sys,time
root=pathlib.Path.cwd();out=root/'records/compute_benchmarks_opencl_20261004';repo=root/'repos/compute-benchmarks';sub=repo/'third_party/googletest';flags=subprocess.CREATE_NO_WINDOW
pins={'main':'1ee56614644622ea9a0c8d702fe483ce19cec97e','googletest':'35b75a2cba6ef72b7ce2b6b94b05c54ca07df866'}
for r,p in [(repo,pins['main']),(sub,pins['googletest'])]:
 assert subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip()==p
baseline={str(r):subprocess.check_output(['git','-C',str(r),'status','--short'],text=True) for r in (repo,sub)}
(out/'dirty_baseline.json').write_text(json.dumps(baseline,indent=2))
for name,r,dest in [('main',repo,out/'source'),('googletest',sub,out/'source/third_party/googletest')]:
 archive=out/(name+'.tar');subprocess.run(['git','-C',str(r),'archive','--format=tar','--output='+str(archive),pins[name]],check=True,timeout=60,creationflags=flags)
 dest.mkdir(parents=True,exist_ok=True)
 with tarfile.open(archive) as t:
  for m in t.getmembers():
   assert (dest/m.name).resolve().is_relative_to(dest.resolve())
  members=[m for m in t.getmembers() if not m.issym() and not m.islnk()]
  (out/(name+'_skipped_links.json')).write_text(json.dumps([{'name':m.name,'target':m.linkname} for m in t.getmembers() if m.issym() or m.islnk()],indent=2))
  assert all(m.isfile() or m.isdir() for m in members)
  t.extractall(dest,members=members)
(out/'provenance.json').write_text(json.dumps({'pins':pins,'archives':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in out.glob('*.tar')},'export':'git archive exact commits; explicit clean googletest export; original dirty trees untouched'},indent=2))
vc=r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
cmake=r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\Scripts\cmake.exe';ninja=r'C:\Users\thoma\AppData\Local\Programs\Python\Python310\Scripts\ninja.exe'
runs=[]
def run(cmd,name,bound):
 with (out/(name+'.stdout.log')).open('wb') as o,(out/(name+'.stderr.log')).open('wb') as e:
  start=time.monotonic();p=subprocess.Popen(cmd,cwd=out,stdout=o,stderr=e,creationflags=flags);print(name,'PID',p.pid,flush=True);timed=False
  try:p.wait(timeout=bound)
  except subprocess.TimeoutExpired:
   timed=True;subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15,creationflags=flags);p.wait(timeout=15)
  result={'name':name,'command':cmd,'pid':p.pid,'exit':p.returncode,'timed_out':timed,'seconds':time.monotonic()-start};runs.append(result);(out/'build_runs.json').write_text(json.dumps(runs,indent=2));print(json.dumps(result),flush=True);return p.returncode==0 and not timed
cmd='cmd.exe /d /s /c ""'+vc+'" >nul && "'+cmake+'" -S "'+str(out/'source')+'" -B "'+str(out/'build')+'" -G Ninja -DCMAKE_MAKE_PROGRAM="'+ninja+'" -DCMAKE_BUILD_TYPE=Release -DBUILD_OCL=ON -DBUILD_L0=OFF -DBUILD_VK=OFF -DBUILD_SYCL=OFF -DBUILD_UR=OFF -DBUILD_OL=OFF -DGENERATE_DOCS=OFF -DALLOW_WARNINGS=ON -DCCACHE_ALLOWED=OFF"'
if not run(cmd,'configure',120):sys.exit(1)
cmd='cmd.exe /d /s /c ""'+vc+'" >nul && "'+cmake+'" --build "'+str(out/'build')+'" --target memory_benchmark_ocl show_devices_ocl -j 4"'
if not run(cmd,'build',600):sys.exit(1)
print('BUILD_COMPLETE',flush=True)
