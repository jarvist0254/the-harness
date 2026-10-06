"""Data-only build-controller preparation. This module launches no process.
The required 600-second native containment runner remains separately admission-gated.
"""
import argparse,hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 args=argparse.ArgumentParser();args.add_argument('--derived-root',required=True);a=args.parse_args();cfg=json.loads((HERE/'CONTRACT.json').read_text());root=pathlib.Path(a.derived_root).resolve()
 if str(root).casefold()!=cfg['proposed_new_root'].casefold():raise ValueError('root confinement')
 command=root/'build_owned.cmd';evidence=root/'evidence';assert command.is_file() and evidence.is_dir()
 pins=json.loads((evidence/'toolchain_original_pins.json').read_text())
 for item in pins:
  if digest(item['path'])!=item['sha256']:raise ValueError('changed pinned toolchain or baseline')
 request={'status':'AWAITING_ROOT_ADMITTED_NATIVE_CONTAINMENT_RUNNER_NOT_EXECUTED','command':['C:\\Windows\\System32\\cmd.exe','/d','/c',str(command)],'command_sha256':digest(command),'cwd':str(root),'job_policy':'assign suspended child to owned kill-on-close Windows Job before ResumeThread; no breakaway; entire compiler/Ninja/shader descendant tree contained','deadline_seconds':600,'stdout_limit_bytes':2097152,'stderr_limit_bytes':2097152,'heartbeat_seconds':15,'parallel_jobs':4,'gpu_execution':'FORBIDDEN','stop_conditions':['deadline','stream overflow','pin changed','native containment uncertainty','configure/build failure'],'cleanup':'terminate owned job on refusal/deadline, wait retained root handle and query active-process zero before truthful drain receipt; no arbitrary PID killing','receipt':'durable command/pins/PID/exit/log hashes/observed bytes/heartbeat/cleanup uncertainty; PROCESS_COMPLETED only after complete root and job drain','existing_supervisor_incompatibility':'Unchanged revision2 permits60s/128KiB. No automatic widening or importing native supervisor here.','required_outputs':cfg['runtime_dlls'],'original_pins':pins}
 target=evidence/'BUILD_CONTROLLER_REQUEST.json'
 if target.exists():raise ValueError('immutable controller request already exists')
 target.write_text(json.dumps(request,indent=2));print(json.dumps({'status':request['status'],'request':str(target)}))
if __name__=='__main__':main()
