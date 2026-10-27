#!/usr/bin/env python3
"""Sealed numeric packet deployment and serial actual watcher dispatch."""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
import threading
import ctypes

ROOT=Path('C:/Users/benja/sol-cloud-numeric-capability-v1')
DEPLOY=ROOT/'artifacts/sol-cloud-coordinator-20260930/integration/numeric-capability-v1'
MIB=1024**2
GLOBAL_CAP=8*MIB
GLOBAL_SLACK=2*MIB
GLOBAL_SOURCE_PATHS=set()
ALLOCATION_UNIT=4096
GLOBAL_ACTIVE=False
GLOBAL_LOCK=threading.Lock()

def allocated(size):return ((size+ALLOCATION_UNIT-1)//ALLOCATION_UNIT)*ALLOCATION_UNIT

def allocation_unit():
    if os.name!='nt':return 4096
    sectors=ctypes.c_ulong();bytes_per_sector=ctypes.c_ulong();free=ctypes.c_ulong();total=ctypes.c_ulong()
    if not ctypes.windll.kernel32.GetDiskFreeSpaceW('C:\\',ctypes.byref(sectors),ctypes.byref(bytes_per_sector),ctypes.byref(free),ctypes.byref(total)):raise OSError('native filesystem allocation query failed')
    unit=sectors.value*bytes_per_sector.value
    if not 0<unit<=65536:raise ValueError('unsupported allocation unit')
    return unit

def global_paths():
    telemetry={p for p in DEPLOY.rglob('*') if p.is_file()} if DEPLOY.exists() else set()
    return GLOBAL_SOURCE_PATHS|telemetry

def global_allocated():
    return sum(allocated(p.stat().st_size) for p in global_paths() if p.exists())

def global_extent(path,new_size):
    if not GLOBAL_ACTIVE:return
    old=allocated(path.stat().st_size) if path.exists() else 0
    increase=max(0,allocated(new_size)-old)
    if global_allocated()+increase+GLOBAL_SLACK>GLOBAL_CAP:raise RuntimeError('shared source/log/telemetry cap exceeded before write')
    if shutil.disk_usage('C:/').free<1073741824+increase+ALLOCATION_UNIT:raise RuntimeError('shared stream reserve refused before write')

def digest(data):return hashlib.sha256(data).hexdigest()

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(MIB),b''):h.update(chunk)
    return h.hexdigest()

def write_new(path,record):
    path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(record,sort_keys=True,indent=2)+'\n').encode()
    with GLOBAL_LOCK:
        global_extent(path,len(data))
        with path.open('xb') as f:
            if f.write(data)!=len(data):raise OSError('partial telemetry write; accepted bytes preserved')
            f.flush();os.fsync(f.fileno())

def inventory():
    process=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,ParentProcessId,Name | ConvertTo-Json -Compress"],capture_output=True,text=True,check=True,timeout=15)
    rows=json.loads(process.stdout or '[]');rows=[rows] if isinstance(rows,dict) else rows
    by={int(x['ProcessId']):x for x in rows};lineage={os.getpid()};pid=os.getpid()
    while pid in by:
        pid=int(by[pid]['ParentProcessId'])
        if pid in lineage:break
        lineage.add(pid)
    conflicts=[int(x['ProcessId']) for x in rows if int(x['ProcessId']) not in lineage]
    if conflicts:raise RuntimeError('unreconciled Python process before optimizer')
    result=subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10)
    tokens=result.stdout.split()
    if not all(x.isdecimal() for x in tokens):raise ValueError('malformed essential GPU PID inventory')
    gpu_pids=[int(x) for x in tokens]
    if any(int(x['ProcessId']) in gpu_pids for x in rows):raise RuntimeError('Python GPU ownership conflict')
    optional_names=[];optional_name_error=None
    if gpu_pids:
        command='$ids=@('+','.join(tokens)+'); Get-CimInstance Win32_Process | Where-Object {$ids -contains $_.ProcessId} | Select-Object ProcessId,Name | ConvertTo-Json -Compress'
        try:
            result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,check=True,timeout=15)
            optional_names=json.loads(result.stdout or '[]');optional_names=[optional_names] if isinstance(optional_names,dict) else optional_names
            if not isinstance(optional_names,list) or any(not isinstance(row,dict) or not isinstance(row.get('Name'),str) for row in optional_names):raise ValueError('optional name lookup malformed')
        except (OSError,subprocess.TimeoutExpired,subprocess.CalledProcessError,ValueError) as error:
            optional_names=[];optional_name_error=type(error).__name__
        if any(row.get('Name','').casefold() in ('python.exe','pythonw.exe') for row in optional_names):raise RuntimeError('Python GPU ownership conflict')
    result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10)
    gpus=[[int(x.strip()) for x in row.split(',')] for row in result.stdout.strip().splitlines()]
    if len(gpus)!=1 or len(gpus[0])!=2 or not 0<=gpus[0][0]<3000 or not 0<=gpus[0][1]<=100:raise ValueError('essential GPU resource inventory differs')
    return {'GPU_compute_PIDs':gpu_pids,'optional_GPU_process_names':optional_names,'optional_GPU_name_lookup_error_type':optional_name_error,'bootstrap_lineage_PIDs':sorted(lineage),'python_exe_conflicts':conflicts,'GPU_memory_used_MiB':gpus[0][0],'GPU_utilization_percent':gpus[0][1]}


def pump_owned_stream(pipe,stream,path,failures,failed_event):
    chunk=b''
    try:
        while True:
            chunk=pipe.read1(16384)
            if not chunk:break
            with GLOBAL_LOCK:
                # Closing disposition has separate64KiB headroom insideglobal8.
                global_extent(path,stream.tell()+len(chunk)+65536)
                written=stream.write(chunk);stream.flush()
                if written!=len(chunk):raise OSError('partial owned worker stream write')
    except Exception as error:
        failures.append({'error_type':type(error).__name__,'accepted_stream_bytes':stream.tell(),'refused_chunk_bytes':len(chunk),'refused_chunk_sha256':digest(chunk),'existing_bytes_preserved':True})
        failed_event.set()

def deploy(records,package,package_sha):
    if digest(json.dumps(package,sort_keys=True,indent=2).encode()+b'\n')!=package_sha:raise ValueError('canonical package bytes differ')
    listed={r['path']:r for r in package['files']}
    if len(listed)!=len(package['files']) or set(listed)!=set(r['path'] for r in records):raise ValueError('exact source member set differs')
    decoded=[]
    for r in records:
        relative=PurePosixPath(r['path'])
        if relative.is_absolute() or '..' in relative.parts or ':' in r['path'] or '\\' in r['path']:raise ValueError('contained source path required')
        b=base64.b64decode(r['data_b64'],validate=True);pin=listed[r['path']]
        if len(b)!=pin['bytes'] or digest(b)!=pin['sha256']:raise ValueError('package source size/hash differs')
        target=ROOT/r['path']
        if target.is_symlink() or not target.resolve().is_relative_to(ROOT.resolve()):raise ValueError('source containment differs')
        if target.exists() and file_sha(target)!=pin['sha256']:raise ValueError('existing source differs; preserved')
        decoded.append((target,b))
    if sum(len(b) for _,b in decoded)>8*MIB:raise ValueError('bounded exact source packet exceeded')
    for target,b in decoded:
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            with GLOBAL_LOCK:
                global_extent(target,len(b))
                with target.open('xb') as f:
                    if f.write(b)!=len(b):raise OSError('partial source write; accepted bytes preserved')
                    f.flush()
    source_paths={ROOT/r['path'] for r in package['files']}
    telemetry_paths={p for p in DEPLOY.rglob('*') if p.is_file()} if DEPLOY.exists() else set()
    # Old model outputs remain on the same volume and are included in free
    # disk measurements, but are not duplicate delivery/source payload bytes.
    return sum(allocated(p.stat().st_size) for p in source_paths|telemetry_paths)

def run_packet(seed,arm,package,package_sha,records,proof):
    global GLOBAL_ACTIVE,GLOBAL_SOURCE_PATHS,ALLOCATION_UNIT
    started=time.monotonic();stage='initial';dispatched=False;result=None
    job='sol-cloud-numeric-v1-s%d-%s-benspc'%(seed,arm)
    try:
        if type(seed) is not int or seed not in (0,1) or arm not in ('loop','plain'):raise ValueError('predeclared arm/seed required')
        if sys.version_info[:3]!=(3,10,9):raise ValueError('verified native runtime required')
        if proof['job']!=job or not proof['running_marker_exists'] or not proof['copied_queue_equals_origin_main'] or proof['other_watcher_running_claims']!=[]:raise ValueError('actual exclusive watcher proof differs')
        stage='watcher-GPU-claim'
        claim=Path('C:/Users/benja/claims/'+job.removesuffix('-benspc'))
        if not claim.is_dir():raise ValueError('actual shared GPU claim absent')
        marker=Path('C:/Users/benja/GPU-BUSY.txt')
        for _ in range(20):
            if marker.is_file() and ('queue job '+job+' since ') in marker.read_text(encoding='utf8'):break
            time.sleep(.25)
        else:raise ValueError('actual shared GPU marker differs')
        stage='serial-predecessors'
        execution_order=[(0,'loop'),(0,'plain'),(1,'loop'),(1,'plain')]
        for prior_seed,prior_arm in execution_order[:execution_order.index((seed,arm))]:
            prior_path=DEPLOY/('TRANSPORT-s%d-%s.json'%(prior_seed,prior_arm))
            prior=json.loads(prior_path.read_bytes())
            if type(prior.get('returncode')) is not int or prior.get('seed')!=prior_seed or prior.get('arm')!=prior_arm or prior.get('job')!='sol-cloud-numeric-v1-s%d-%s-benspc'%(prior_seed,prior_arm):raise ValueError('exact predecessor terminal disposition absent')
        stage='source-deployment'
        if package['pc_root']!=ROOT.as_posix():raise ValueError('fixed new PC source root differs')
        plan_pin=package['plan'];plan_record=next(r for r in records if r['path']==plan_pin['path']);plan_bytes=base64.b64decode(plan_record['data_b64'],validate=True)
        if digest(plan_bytes)!=plan_pin['sha256']:raise ValueError('plan differs before deployment')
        plan=json.loads(plan_bytes);pair=ROOT/'artifacts/sol-cloud-numeric-fit-20260930'/plan['run_namespace']/('seed%d'%seed)
        out=pair/arm
        if out.exists():raise ValueError('owned run namespace already exists; no restart')
        existing=sum(p.stat().st_size for p in pair.rglob('*') if p.is_file()) if pair.exists() else 0
        floor=plan['budget']['retained_free_bytes'];planned=plan['budget']['planned_pair_peak_bytes']
        ALLOCATION_UNIT=allocation_unit();GLOBAL_SOURCE_PATHS={ROOT/r['path'] for r in package['files']};GLOBAL_ACTIVE=True
        retained=sum(allocated(p.stat().st_size) for p in pair.parent.rglob('*') if p.is_file()) if pair.parent.exists() else 0
        future=2*planned+GLOBAL_CAP-global_allocated()-retained
        if shutil.disk_usage('C:/').free<floor+max(0,future):raise RuntimeError('BOTH-seed conservative matrix storage unavailable before writes')
        ROOT.mkdir(exist_ok=True);delivered=deploy(records,package,package_sha)
        if delivered>8*MIB:raise ValueError('delivered tree exceeds included source budget')
        stage='fresh-essential-inventory';facts=inventory()
        facts.update(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gpu_inventory_verified=True,project_gpu_processes=[],other_watcher_running_claims=[],source_checkpoint_closure_verified=True,delivery_package_and_tree_bytes=delivered,global_shared_storage_verified=True,global_shared_allocated_bytes=global_allocated(),global_shared_cap_bytes=GLOBAL_CAP,filesystem_allocation_unit_bytes=ALLOCATION_UNIT,global_metadata_and_partial_write_slack_bytes=GLOBAL_SLACK,C_free_bytes=shutil.disk_usage(ROOT).free,actual_user_day=False,activated=False)
        # Exact source checkpoint byte hashes are verified again by the sealed
        # driver before any Torch import; this preflight makes no model call.
        for binding in [plan['warmstart']['tuples'][str(seed)]]:
            for name in ('parent','reader','adapter','connected_resume'):
                if file_sha(binding[name+'_path'])!=binding[name+'_sha256']:raise ValueError('actual warmstart checkpoint bytes differ')
        proof_path=DEPLOY/('WATCHER-PROOF-s%d-%s.json'%(seed,arm));write_new(proof_path,proof)
        inventory_path=DEPLOY/('INVENTORY-s%d-%s.json'%(seed,arm));write_new(inventory_path,facts)
        stage='native-driver-dispatch'
        env=dict(os.environ,JOB=job,TREE=str(ROOT),PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'scripts'),r'C:\Users\benja\lis300\venv\Lib\site-packages']))
        argv=[sys._base_executable,'-X','utf8','-B',str(ROOT/'scripts/sol_cloud_numeric_fit_v1.py'),'--seed',str(seed),'--arm',arm]
        for name in ('plan','seal','release'):
            pin=package[name];argv+=['--'+name,str(ROOT/pin['path']),'--'+name+'-sha256',pin['sha256']]
        argv+=['--inventory',str(inventory_path),'--inventory-sha256',file_sha(inventory_path)]
        log=DEPLOY/('worker-s%d-%s.log'%(seed,arm));dispatched=True
        stream_failures=[];stream_failed=threading.Event()
        with log.open('xb') as f:
            child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
            reader=threading.Thread(target=pump_owned_stream,args=(child.stdout,f,log,stream_failures,stream_failed),daemon=True);reader.start()
            remaining=max(1,min(570,proof['remaining_seconds']-(time.monotonic()-started)-12));deadline=time.monotonic()+remaining
            while child.poll() is None:
                if stream_failed.is_set() or time.monotonic()>=deadline:
                    if os.name=='nt':subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],check=True,timeout=8)
                    else:child.kill()
                    child.wait(timeout=5);result=125 if stream_failed.is_set() else 124;break
                try:result=child.wait(timeout=.25)
                except subprocess.TimeoutExpired:pass
            if result is None:result=child.returncode
            reader.join(timeout=5)
            if reader.is_alive():raise RuntimeError('owned worker stream did not close; accepted log preserved')
            if stream_failures:result=125
        stage='small-return-manifest';records_out=[]
        for p in sorted(out.rglob('*')) if out.is_dir() else []:
            if p.is_file():records_out.append({'relative':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':file_sha(p)})
        report={'schema':'sol.cloud.numeric-fit.transport.v1','job':job,'seed':seed,'arm':arm,'returncode':result,'records':records_out,'worker_log':{'relative':log.relative_to(ROOT).as_posix(),'bytes':log.stat().st_size,'sha256':file_sha(log)},'actual_user_day':False,'activated':False,'dispatched':True,'bounded_stream_failures':stream_failures,'shared_global_allocated_bytes':global_allocated(),'shared_global_cap_bytes':GLOBAL_CAP,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_seconds':time.monotonic()-started}
        write_new(DEPLOY/('TRANSPORT-s%d-%s.json'%(seed,arm)),report);print(json.dumps(report,sort_keys=True),flush=True)
        return result
    except Exception as e:
        print(json.dumps({'schema':'sol.cloud.numeric-bootstrap-failure.v1','job':job,'seed':seed,'arm':arm,'stage':stage,'error_type':type(e).__name__,'error':str(e),'dispatched':dispatched,'optimizer_status':'unknown' if dispatched else 'not-started','actual_user_day':False,'activated':False,'wall_seconds':time.monotonic()-started}),flush=True)
        raise
