#!/usr/bin/env python3
"""Single-arm native watcher relay for the sealed capability256 runner.

The PC bootstrap stages only the exact pinned source packet, builds a fresh
bounded process/GPU/disk inventory, and invokes the runner with the inventory
hash. Model code is reached only after the runner's release and inventory gates.
"""
import argparse
import base64
import datetime
import hashlib
import gzip
import importlib.util
import json
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time

W=Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=Path('/Users/ben-hannan/premonition-watch/queue')
OWN='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/mac-launch-v3'
PCROOT='C:/Users/benja/sol-cloud-numeric-capability-v1'
PCPY=r'C:\Users\benja\lis300\venv\Scripts\python.exe'
STRICT=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no',
        '-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2']
ORDER=[(0,'loop'),(0,'plain'),(1,'loop'),(1,'plain')]
STARTED=None


def digest(data):return hashlib.sha256(data).hexdigest()


def left():
    seconds=4500-(time.monotonic()-STARTED)
    if seconds<=0:raise TimeoutError('outer 4500-second arm cap exhausted')
    return seconds


def git_blob(path,expected):
    relative=PurePosixPath(path)
    if relative.is_absolute() or '..' in relative.parts or '\\' in path or ':' in path:
        raise ValueError('contained exact source path required')
    result=subprocess.run(['git','-C',str(W),'show','origin/main:'+path],capture_output=True,
                          check=True,timeout=min(10,left()))
    if len(result.stdout)>8*1024**2 or digest(result.stdout)!=expected:
        raise ValueError('immutable origin/main source bytes differ')
    return result.stdout


def running_gpu_jobs(job):
    jobs=[]
    for marker in Q.glob('*.running'):
        if marker.stem==job:continue
        copied=Q/(marker.stem+'.md')
        if not copied.is_file():raise ValueError('running watcher claim lacks its copied queue')
        if 'GPU: yes' in copied.read_text(encoding='utf8').splitlines():jobs.append(marker.stem)
    return sorted(jobs)


def queue_job(seed,arm):
    base='sol-cloud-capability256-v1-s%d-%s-train'%(seed,arm)
    return base+'-r3' if (seed,arm)==(0,'loop') else base

def predecessor_jobs(seed,arm):
    return [queue_job(*pair) for pair in ORDER[:ORDER.index((seed,arm))]]


def watcher_proof(job,seed,arm):
    if not (Q/(job+'.running')).is_file() or (Q/(job+'.exit')).exists():
        raise ValueError('fresh actual watcher claim required')
    copied=(Q/(job+'.md')).read_bytes()
    if git_blob('handoff/queue/'+job+'.md',digest(copied))!=copied:
        raise ValueError('copied queue differs from origin/main')
    prior=[]
    for name in predecessor_jobs(seed,arm):
        if (Q/(name+'.running')).exists():raise ValueError('previous serial arm is still running')
        marker=Q/(name+'.exit')
        if not marker.is_file() or not re.fullmatch(r'rc=0\s*',marker.read_text()):
            raise ValueError('previous arm lacks successful physical watcher exit')
        prior.append({'job':name,'watcher_exit':'rc=0'})
    others=running_gpu_jobs(job)
    if others:raise ValueError('another GPU queue is active')
    return {'job':job,'seed':seed,'arm':arm,'queue_sha256':digest(copied),
            'copied_queue_matches_origin_main':True,'other_watcher_running_claims':others,
            'predecessor_exits':prior,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'actual_user_day':False}


def pc_source(spec,records,proof):
    """Inline bounded PC bootstrap. No archive/model bytes are copied."""
    return r'''import base64,ctypes,datetime,gzip,hashlib,importlib.util,json,os,pathlib,platform,shutil,subprocess,sys,time
root=pathlib.Path(__ROOT__);spec=__SPEC__;records=__RECORDS__;proof=__PROOF__;started=time.monotonic();bootstrap_stage='runtime_identity';runner_invoked=False
def digest(data):return hashlib.sha256(data).hexdigest()
def fail(stage,error):
 print(json.dumps({'schema':'sol.cloud.capability256.bootstrap-failure.v2','job':spec['job'],
  'stage':stage,'error_type':type(error).__name__,'error':str(error)[:4096],
  'PC_originals_preserved':True,'activation':False,'runner_invoked':runner_invoked,
  'model_calls':None if runner_invoked else 0,
  'GPU_optimizer_start':None if runner_invoked else False}),flush=True);raise SystemExit(2)
try:
 assert platform.system()=='Windows' and sys.version_info[:3]==(3,10,9),'native PC3.10.9 required'
 assert root.is_dir() and not root.is_symlink(),'exact existing owned repo required'
 bootstrap_stage='source_package'
 total=sum(r['bytes'] for r in records);assert total<=8*1024**2,'bounded pinned package required'
 staged=[];record_map={}
 for r in records:
  data=base64.b64decode(r['data_b64'],validate=True)
  assert len(data)==r['bytes'] and digest(data)==r['sha256']
  rel=pathlib.PurePosixPath(r['path']);assert not rel.is_absolute() and '..' not in rel.parts and ':' not in r['path'] and '\\' not in r['path']
  dst=root.joinpath(*rel.parts);assert dst.resolve().is_relative_to(root.resolve())
  parent=dst.parent;parent.mkdir(parents=True,exist_ok=True)
  cursor=dst
  while cursor!=root:
   assert not cursor.is_symlink(),'staged path contains a symlink'
   cursor=cursor.parent
  assert cursor==root and not root.is_symlink(),'staging escaped exact repo root'
  if dst.exists():
   assert dst.is_file() and digest(dst.read_bytes())==r['sha256'],'existing source differs; never overwrite'
  else:
   with dst.open('xb') as stream:stream.write(data)
  assert dst.stat().st_size==r['bytes'] and digest(dst.read_bytes())==r['sha256']
  staged.append((dst,digest(data),len(data)));record_map[r['path']]=dst
 def pin(pin):
  path=pathlib.Path(pin['path']);path=path if path.is_absolute() else root/path
  assert path.resolve().is_relative_to(root.resolve()) and not path.is_symlink()
  data=path.read_bytes();assert digest(data)==pin['sha256'];return path,json.loads(data)
 plan_path,plan=pin(spec['plan']);seal_path,seal=pin(spec['seal']);release_path,release=pin(spec['release'])
 runner_path=record_map[spec['runner']['path']]
 assert digest(runner_path.read_bytes())==spec['runner']['sha256']
 assert plan.get('run_namespace')==spec['run_namespace'] and plan.get('budget',{}).get('delivery_cap_bytes')==8*1024**2
 assert spec['phase']=='train' and spec['seed'] in (0,1) and spec['arm'] in ('loop','plain')
 bootstrap_stage='checkpoint_closure'
 # Verify each seed's exact parent/reader/adapter and numeric16 loop800 warmstart.
 bindings=plan['warmstart']['tuples'];closure=[]
 for seed in (0,1):
  binding=bindings[str(seed)]
  if binding.get('numeric_resume_sha256')!=spec['numeric16_loop_sha256'][str(seed)]:raise ValueError('numeric16 warmstart seal differs')
  for key in ('parent','reader','adapter','numeric_resume'):
   p=pathlib.Path(binding[key+'_path']);expected=binding[key+'_sha256']
   if not p.is_file() or p.is_symlink() or digest(p.read_bytes())!=expected:raise ValueError('source checkpoint closure differs')
   closure.append({'seed':seed,'kind':key,'sha256':expected})
  p=pathlib.Path(binding['lm_provenance'])
  if not p.is_file() or p.is_symlink() or digest(p.read_bytes())!=plan['LM_provenance']['sha256']:
   raise ValueError('frozen LM provenance closure differs')
 bootstrap_stage='runtime_package_smoke'
 helper_path=record_map['scripts/sol_cloud_queue_recovery_v1.py']
 helper_spec=importlib.util.spec_from_file_location('_capability_queue_recovery',helper_path)
 helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
 file_pins=[{key:r[key] for key in ('path','sha256','bytes')} for r in records]
 required=helper.packaged_runtime_pins(spec,plan,seal,release)
 package_smoke=helper.package_smoke(root,file_pins,required_pins=required)
 bootstrap_stage='native_import_help'
 # Native import/help smoke is CPU-only and runs before resource snapshot or runner.
 import_code="import importlib.util,json,pathlib,sys; p=pathlib.Path(sys.argv[1]); s=importlib.util.spec_from_file_location('_capability_runner_smoke',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(json.dumps({'imported':True,'root':str(m.ROOT)}))"
 imported=subprocess.run([sys.executable,'-X','utf8','-B','-c',import_code,str(runner_path)],
  cwd=str(root),capture_output=True,text=True,timeout=20)
 if imported.returncode or len(imported.stdout)>65536 or len(imported.stderr)>65536:
  raise RuntimeError('native runner import smoke failed')
 help_run=subprocess.run([sys.executable,'-X','utf8','-B',str(runner_path),'--help'],
  cwd=str(root),capture_output=True,text=True,timeout=20)
 if (help_run.returncode or '--phase' not in help_run.stdout or '--final-freeze-sha256' not in help_run.stdout
     or len(help_run.stdout)>65536 or len(help_run.stderr)>65536):
  raise RuntimeError('native runner CLI help smoke failed')
 native_smoke={'python_version':platform.python_version(),'import_returncode':imported.returncode,
  'import_stdout_sha256':digest(imported.stdout.encode()),'import_stderr_sha256':digest(imported.stderr.encode()),
  'help_returncode':help_run.returncode,'help_stdout_sha256':digest(help_run.stdout.encode()),
  'help_stderr_sha256':digest(help_run.stderr.encode()),'model_calls':0,'optimizer_updates':0}
 bootstrap_stage='resource_inventory'
 # Snapshot only bounded Python metadata, GPU rows/app PIDs, free bytes and owned-path matches.
 def cmd(argv):
  p=subprocess.run(argv,capture_output=True,text=True,timeout=12)
  if p.returncode:raise RuntimeError('bounded resource probe returned nonzero')
  return p.stdout
 pytext=cmd(['powershell','-NoProfile','-Command',
  "Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('python.exe','pythonw.exe')} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress"])
 py=json.loads(pytext or '[]');py=[py] if isinstance(py,dict) else py
 by_pid={int(x['ProcessId']):x for x in py if isinstance(x,dict) and str(x.get('ProcessId','')).isdecimal()}
 lineage={os.getpid()};cursor=os.getpid()
 while cursor in by_pid:
  parent=int(by_pid[cursor].get('ParentProcessId') or 0)
  if parent<=0 or parent in lineage:break
  lineage.add(parent);cursor=parent
 py_summary=[];project_conflicts=[]
 for x in py:
  if not isinstance(x,dict):raise RuntimeError('malformed Python process inventory')
  pid=int(x['ProcessId']);cmdline=str(x.get('CommandLine') or '').lower();exe=str(x.get('ExecutablePath') or '').lower()
  owned=(str(root).lower() in cmdline or 'sol_cloud_capability256_v1.py' in cmdline)
  py_summary.append({'pid':pid,'parent_pid':x.get('ParentProcessId'),'name':x.get('Name'),
                     'owned_command_match':owned,'bootstrap_lineage':pid in lineage,
                     'base_executable_match':exe==str(pathlib.Path(sys.executable)).lower()})
  # Preserve unrelated CPU Python services; separate project processes and GPU owners are checked independently.
  if pid not in lineage and owned:project_conflicts.append({'pid':pid,'name':x.get('Name')})
 if project_conflicts:raise RuntimeError('unreconciled Python process or project process already active')
 gpu=cmd(['nvidia-smi','--query-gpu=index,utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'])
 gpu_rows=[[int(v.strip()) for v in row.split(',')] for row in gpu.strip().splitlines() if row.strip()]
 apps=cmd(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'])
 gpu_pids=[];gpu_app_memory={}
 for row in apps.strip().splitlines():
  if row.strip():
   parts=[part.strip() for part in row.split(',')]
   if len(parts)!=2 or not parts[0].isdecimal():raise RuntimeError('malformed essential GPU PID inventory')
   pid=int(parts[0]);gpu_pids.append(pid);gpu_app_memory[pid]=parts[1]
 pid_text=','.join(map(str,gpu_pids)) or '-1'
 name_text=cmd(['powershell','-NoProfile','-Command',
  "$ids=@("+pid_text+"); Get-CimInstance Win32_Process | Where-Object {$ids -contains $_.ProcessId} | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"])
 proc=json.loads(name_text or '[]');proc=[proc] if isinstance(proc,dict) else proc
 proc_by_pid={int(x['ProcessId']):x for x in proc if isinstance(x,dict) and str(x.get('ProcessId','')).isdecimal()}
 # This PC's audited WDDM baseline reports desktop/UI processes in nvidia-smi.
 # Unknown owners block; known graphics/browser applications do not claim the optimizer.
 graphics_names={'dwm.exe','oktaverify.exe','explorer.exe','crossdeviceresume.exe','widgetboard.exe',
  'searchhost.exe','startmenuexperiencehost.exe','msedgewebview2.exe','textinputhost.exe',
  'powertoys.advancedpaste.exe','powertoys.colorpickerui.exe','powertoys.fancyzones.exe',
  'powertoys.peek.ui.exe','powertoys.powerlauncher.exe','discord.exe','ivcam.exe','chrome.exe',
  'lively.exe','sharex.exe','applicationframehost.exe','systemsettings.exe','shellexperiencehost.exe',
  'shellhost.exe','edgegameassist.exe','lunar client.exe','msedge.exe','javaw.exe','claude.exe',
  'phoneexperiencehost.exe'}
 project_gpu=[];unknown_gpu=[];gpu_processes=[]
 for pid in gpu_pids:
  x=proc_by_pid.get(pid)
  if x is None:unknown_gpu.append({'pid':pid,'reason':'process name unavailable'});continue
  name=str(x.get('Name') or '').casefold();cmdline=str(x.get('CommandLine') or '').casefold()
  gpu_processes.append({'pid':pid,'name':x.get('Name'),'used_memory':gpu_app_memory.get(pid)})
  model_runtime=any(mark in (name+' '+cmdline) for mark in ('sol_cloud_capability256_v1.py',str(root).lower(),
   'lm studio','lmstudio','llama-server','ollama','vllm','text-generation','kobold','exllama','torchrun'))
  if name in ('python.exe','pythonw.exe') or model_runtime:
   project_gpu.append({'pid':pid,'name':x.get('Name')})
  elif name not in graphics_names:
   unknown_gpu.append({'pid':pid,'name':x.get('Name'),'reason':'not in audited desktop/UI baseline'})
  elif gpu_app_memory.get(pid)!='N/A':
   unknown_gpu.append({'pid':pid,'name':x.get('Name'),'used_memory':gpu_app_memory.get(pid),
                       'reason':'desktop/UI exception requires per-process N/A memory'})
 if project_gpu:raise RuntimeError('competing Python/model-runtime GPU owner already active')
 if unknown_gpu:raise RuntimeError('uncertain GPU process owner blocks exclusive-resource gate')
 if len(gpu_rows)!=1 or len(gpu_rows[0])!=4 or not 0<=gpu_rows[0][2]<3000 or not 0<=gpu_rows[0][1]<=100:
  raise RuntimeError('GPU resource values outside audited desktop baseline')
 if gpu_rows[0][1]>0 and not gpu_pids:
  raise RuntimeError('GPU activity has no attributable process; owner is uncertain')
 # Device utilization is timing noise when reported PIDs are audited desktop/UI
 # processes with WDDM N/A memory; project and unknown owners already fail above.
 unit=65536
 if os.name=='nt':
  sectors,bytes_per_sector,free_clusters,total_clusters=(ctypes.c_ulong() for _ in range(4))
  if not ctypes.windll.kernel32.GetDiskFreeSpaceW('C:\\',ctypes.byref(sectors),ctypes.byref(bytes_per_sector),ctypes.byref(free_clusters),ctypes.byref(total_clusters)):
   raise RuntimeError('filesystem allocation-unit query failed')
  unit=sectors.value*bytes_per_sector.value
 if not 0<unit<=65536:raise RuntimeError('allocation unit exceeds sealed reserve')
 allocated=sum(((n+unit-1)//unit)*unit for _,_,n in staged)
 bootstrap_stage='fresh_inventory_write'
 inv_path=root/spec['inventory_path'];assert inv_path.resolve().is_relative_to(root.resolve()) and not inv_path.exists() and not inv_path.is_symlink()
 inventory={'schema':'sol.cloud.capability256.resource-inventory.v1',
  'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'C_free_bytes':shutil.disk_usage('C:/').free,'C_total_bytes':shutil.disk_usage('C:/').total,
  'gpu_inventory_verified':True,'gpu_rows':gpu_rows,'gpu_compute_pids':gpu_pids,
  'gpu_processes_sanitized':gpu_processes,'unknown_gpu_owners':unknown_gpu,
  'native_runner_smoke':native_smoke,
  'project_gpu_processes':project_gpu,'python_exe_conflicts':project_conflicts,
  'python_processes_sanitized':py_summary,'other_watcher_running_claims':proof['other_watcher_running_claims'],
  'source_checkpoint_closure_verified':True,'source_checkpoint_closure':closure,
  'delivery_package_and_tree_bytes':package_smoke['total_bytes'],'package_smoke':package_smoke,
  'global_shared_storage_verified':True,
  'global_shared_allocated_bytes':allocated,'inventory_file_allocated_bytes':0,
  'global_shared_cap_bytes':8*1024**2,
  'actual_user_day':False,'model_calls':0,'GPU_calls_before_runner':0,'optimizer_updates_before_runner':0}
 inv_path.parent.mkdir(parents=True,exist_ok=True)
 if inv_path.exists() or inv_path.is_symlink():raise RuntimeError('fresh inventory destination already exists')
 def extent(size):return ((size+unit-1)//unit)*unit
 for _ in range(4):
  data=(json.dumps(inventory,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
  inv_alloc=extent(len(data));total_alloc=allocated+inv_alloc
  if inventory['inventory_file_allocated_bytes']==inv_alloc and inventory['global_shared_allocated_bytes']==total_alloc:break
  inventory['inventory_file_allocated_bytes']=inv_alloc
  inventory['global_shared_allocated_bytes']=total_alloc
 else:raise RuntimeError('inventory allocation accounting did not converge')
 if total>inventory['global_shared_cap_bytes'] or total_alloc>inventory['global_shared_cap_bytes']:
  raise RuntimeError('global 8MiB shared cap exhausted before runner')
 with inv_path.open('xb') as f:
  if f.write(data)!=len(data):raise OSError('partial inventory write')
  f.flush();os.fsync(f.fileno())
 if inv_path.stat().st_size!=len(data) or extent(inv_path.stat().st_size)!=inventory['inventory_file_allocated_bytes']:
  raise RuntimeError('physical inventory allocation differs from fresh resource proof')
 inv_sha=digest(data);inventory['inventory_sha256']=inv_sha
 env=dict(os.environ,JOB=spec['job'],TREE=str(root.resolve()))
 argv=[sys.executable,'-X','utf8','-B',str(runner_path),'--phase','train','--seed',str(spec['seed']),'--arm',spec['arm'],
  '--plan',str(plan_path),'--plan-sha256',spec['plan']['sha256'],
  '--seal',str(seal_path),'--seal-sha256',spec['seal']['sha256'],
  '--release',str(release_path),'--release-sha256',spec['release']['sha256'],
  '--inventory',str(inv_path),'--inventory-sha256',inv_sha]
 launched=time.monotonic()
 bootstrap_stage='runner_invocation'
 runner_invoked=True
 try:p=subprocess.run(argv,cwd=str(root),env=env,capture_output=True,timeout=max(1,4500-(time.monotonic()-started)))
 except subprocess.TimeoutExpired as e:
  pout=e.stdout or b'';perr=e.stderr or b'';rc=None;timed=True
 else:pout=p.stdout;perr=p.stderr;rc=p.returncode;timed=False
 if len(pout)>2*1024**2 or len(perr)>2*1024**2:raise RuntimeError('runner console exceeds bounded 2MiB cap; PC originals preserved')
 run=root/'artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1'/spec['run_namespace']/('seed%d'%spec['seed'])/spec['arm']
 files=[];compressed_bytes=0;return_cap=3*1024**2
 # Preserve a complete manifest even when a raw evidence file is too large to relay.
 # Terminal receipts are prioritized; raw files that do not fit remain on the PC
 # with their exact size/SHA for later read-only collection, and never fail a fit.
 priorities=('CLOSED.json','FAILED.json','LAUNCH.json','INITIAL-STATE.json','INITIAL-FUNCTION-PARITY.json',
             'INPUT-FRAMES.json','MEMORY-PREFLIGHT.json','TRAIN-RAW.jsonl','DIAGNOSTIC-RAW.jsonl')
 if run.is_dir():
  for name in priorities:
   pth=run/name
   if pth.is_file():
    st=pth.stat();assert not pth.is_symlink()
    blob=pth.read_bytes();assert len(blob)==st.st_size
    item={'path':str(pth.relative_to(root)).replace('\\','/'),'bytes':len(blob),'sha256':digest(blob),
          'PC_original_preserved':True,'transported':False}
    packed=gzip.compress(blob,compresslevel=6,mtime=0)
    if len(packed)<=return_cap-compressed_bytes:
     compressed_bytes+=len(packed)
     item.update({'transported':True,'codec':'gzip','transport_bytes':len(packed),
                  'transport_sha256':digest(packed),'data_b64':base64.b64encode(packed).decode('ascii')})
    files.append(item)
 summary={'schema':'sol.cloud.capability256.arm-return.v1','job':spec['job'],'seed':spec['seed'],'arm':spec['arm'],
  'phase':'train','runner_returncode':rc,'runner_timed_out':timed,'runner_stdout_sha256':digest(pout),
  'runner_stderr_sha256':digest(perr),'runner_wall_seconds':time.monotonic()-launched,
  'inventory_sha256':inv_sha,'inventory_path':spec['inventory_path'],'files':files,'compressed_transport_bytes':compressed_bytes,'compressed_transport_cap_bytes':return_cap,
  'PC_originals_preserved':True,'activation':False}
 print(json.dumps({'summary':summary,'runner_stdout_b64':base64.b64encode(pout).decode('ascii'),
                   'runner_stderr_b64':base64.b64encode(perr).decode('ascii')},sort_keys=True),flush=True)
 raise SystemExit(rc if rc is not None else 124)
except SystemExit:raise
except Exception as e:fail(bootstrap_stage,e)
'''.replace('__ROOT__',repr(PCROOT)).replace('__SPEC__',repr(spec)).replace('__RECORDS__',repr(records)).replace('__PROOF__',repr(proof))


def main():
    global STARTED
    STARTED=time.monotonic()
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--spec-sha256',required=True)
    args=p.parse_args()
    if (platform.system()!='Darwin' or sys.version_info[:3]!=(3,9,6) or Path.cwd().resolve()!=W.resolve()):
        raise ValueError('verified native Mac3.9.6 watcher root required')
    raw=git_blob(args.spec,args.spec_sha256);spec=json.loads(raw)
    if spec.get('schema')!='sol.cloud.capability256.mac-launch-spec.v1' or spec.get('phase')!='train':
        raise ValueError('exact pinned capability256 training launch spec required')
    seed,arm=spec.get('seed'),spec.get('arm');job=spec.get('job')
    expected_job=queue_job(seed,arm) if (seed,arm) in ORDER else None
    if ((seed,arm) not in ORDER or job!=expected_job
            or spec.get('pc_root')!=PCROOT or spec.get('runner') is None):
        raise ValueError('exact unique seed/arm/PC/runner identity required')
    files=spec.get('files')
    if not isinstance(files,list) or not files:raise ValueError('exact bounded package file pins required')
    helper_pin=next(pin for pin in files if pin['path']=='scripts/sol_cloud_queue_recovery_v1.py')
    helper_source=git_blob(helper_pin['path'],helper_pin['sha256'])
    helper_scope={'__name__':'_capability_queue_recovery'}
    exec(compile(helper_source,helper_pin['path'],'exec'),helper_scope)
    layout=helper_scope['output_layout'](OWN,job,run_root='artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1',
                         run_namespace=spec['run_namespace'],seed=seed,arm=arm)
    out=W/layout['execution_path'];out.mkdir(parents=True,exist_ok=False)
    proof=watcher_proof(job,seed,arm)
    records=[];total=0
    for pin in files:
        data=git_blob(pin['path'],pin['sha256'])
        if len(data)!=pin['bytes']:raise ValueError('pinned package member byte count differs')
        total+=len(data)
        if total>8*1024**2:raise ValueError('package exceeds global 8MiB allowance')
        records.append(dict(pin,data_b64=base64.b64encode(data).decode('ascii')))
    proof.update(package_file_count=len(records),package_bytes=total)
    (out/'MAC-WATCHER-PROOF.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n',encoding='utf8')
    source=pc_source(spec,records,proof).encode('utf8')
    command=['ssh','-T',*STRICT,'benspc',PCPY+' -X utf8 -B -']
    rc=None;stdout=b'';stderr=b'';error=None;timed=False
    try:
        p=subprocess.run(command,input=source,capture_output=True,timeout=left())
        rc=p.returncode;stdout=p.stdout;stderr=p.stderr
    except subprocess.TimeoutExpired as e:
        stdout=e.stdout or b'';stderr=e.stderr or b'';timed=True
    except OSError as e:error=type(e).__name__
    (out/'PC-stdout-transport.json').write_text(json.dumps({'bytes':len(stdout),'sha256':digest(stdout),
        'packet_summary_embedded':True},sort_keys=True)+'\n',encoding='utf8')
    with (out/'PC-stderr.log.gz').open('xb') as f:f.write(gzip.compress(stderr,compresslevel=6,mtime=0))
    with (out/'PC-SSH-EXIT.json').open('x',encoding='utf8') as f:
        f.write(json.dumps({'returncode':rc,'timed_out':timed,'error_type':error,
            'stdout_bytes':len(stdout),'stdout_sha256':digest(stdout),'stderr_bytes':len(stderr),
            'stderr_sha256':digest(stderr),'PC_originals_preserved':True},indent=2,sort_keys=True)+'\n')
    try:packet=json.loads(stdout.decode('utf8').splitlines()[-1])
    except (ValueError,UnicodeError,IndexError):packet=None
    if isinstance(packet,dict) and packet.get('schema')=='sol.cloud.capability256.bootstrap-failure.v2':
        if packet.get('job')!=job:raise ValueError('bootstrap failure job differs')
        raw_failure=(json.dumps(packet,sort_keys=True,indent=2)+'\n').encode('utf8')
        if len(raw_failure)>16384:raise ValueError('bootstrap failure receipt exceeds bounded error cap')
        with (out/'PC-BOOTSTRAP-FAILED.json').open('xb') as stream:stream.write(raw_failure)
    success=(rc==0 and not timed and isinstance(packet,dict)
             and packet.get('summary',{}).get('schema')=='sol.cloud.capability256.arm-return.v1'
             and packet['summary'].get('job')==job and packet['summary'].get('seed')==seed
             and packet['summary'].get('arm')==arm and packet['summary'].get('runner_returncode')==0
             and packet['summary'].get('runner_timed_out') is False)
    if isinstance(packet,dict) and packet.get('summary',{}).get('job')==job:
        result=packet['summary'];
        compact=dict(result);compact['files']=[{k:v for k,v in item.items() if k!='data_b64'} for item in result.get('files',[])]
        (out/'PC-ARM-RETURN.json').write_text(json.dumps(compact,indent=2,sort_keys=True)+'\n',encoding='utf8')
        for item in result.get('files',[]):
            rel=PurePosixPath(item['path'])
            if rel.is_absolute() or '..' in rel.parts or '\\' in item['path'] or ':' in item['path']:
                raise ValueError('remote return path escapes package root')
            if not item.get('transported'):
                continue
            packed=base64.b64decode(item['data_b64'],validate=True)
            if len(packed)!=item['transport_bytes'] or digest(packed)!=item['transport_sha256']:
                raise ValueError('remote compressed receipt bytes differ')
            data=gzip.decompress(packed)
            if len(data)!=item['bytes'] or digest(data)!=item['sha256']:
                raise ValueError('remote exact receipt bytes differ')
            dest=out/'copied'/(item['path']+'.gz');dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write(packed)
        for name,value,expected in (('runner-stdout.log.gz',packet.get('runner_stdout_b64',''),
                result.get('runner_stdout_sha256')),('runner-stderr.log.gz',packet.get('runner_stderr_b64',''),
                result.get('runner_stderr_sha256'))):
            data=base64.b64decode(value,validate=True)
            if digest(data)!=expected:raise ValueError('runner console hash differs')
            with (out/name).open('xb') as f:f.write(gzip.compress(data,compresslevel=6,mtime=0))
    print(json.dumps({'job':job,'transport_returncode':rc,'timed_out':timed,
                      'success':success,'PC_originals_preserved':True,
                      'PC_stdout_sha256':digest(stdout),'PC_stderr_sha256':digest(stderr)},sort_keys=True),flush=True)
    return 0 if success else 1


if __name__=='__main__':raise SystemExit(main())
