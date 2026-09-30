#!/usr/bin/env python3
"""Native Mac serial watcher relay; sealed source packet, complete failure bytes."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time

W=Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=Path('/Users/ben-hannan/premonition-watch/queue')
PCROOT='C:/Users/benja/sol-cloud-numeric-capability-v1'
PCPY=r'C:\Users\benja\lis300\venv\Scripts\python.exe'
OWN='artifacts/sol-cloud-numeric-fit-20260930/mac-launch-v2'
DEPLOY='artifacts/sol-cloud-coordinator-20260930/integration/numeric-capability-v1'
STRICT=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no',
        '-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2']
ORDER=[(0,'loop'),(0,'plain'),(1,'loop'),(1,'plain')]
STARTED=None
OUT=None
STAGE='initial'
DISPATCHED=False


def digest(data):return hashlib.sha256(data).hexdigest()


def file_sha(path):return digest(Path(path).read_bytes())


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8') as stream:stream.write(json.dumps(value,indent=2,sort_keys=True)+'\n')


def remaining(reserve=0):
    left=600-(time.monotonic()-STARTED)-reserve
    if left<=0:raise TimeoutError('shared600second transport budget exhausted')
    return left


def relative_path(text):
    path=PurePosixPath(text)
    if path.is_absolute() or '..' in path.parts or '\\' in text or ':' in text or not text:
        raise ValueError('contained exact source/receipt path required')
    return path


def git_blob(pin):
    global STAGE
    relative_path(pin['path']);STAGE='pinned origin/main source '+pin['path']
    result=subprocess.run(['git','-C',str(W),'show','origin/main:'+pin['path']],capture_output=True,
                          check=True,timeout=min(10,remaining()))
    if digest(result.stdout)!=pin['sha256']:raise ValueError('immutable main source SHA differs')
    if 'bytes' in pin and len(result.stdout)!=pin['bytes']:raise ValueError('immutable main source size differs')
    return result.stdout


def running_gpu_jobs(job):
    jobs=[]
    for marker in Q.glob('*.running'):
        if marker.stem==job:continue
        copied=Q/(marker.stem+'.md')
        if not copied.is_file():raise ValueError('running watcher claim has no copied job')
        if 'GPU: yes' in copied.read_text(encoding='utf8').splitlines():jobs.append(marker.stem)
    return sorted(jobs)


def optional_runner_metadata(job):
    pattern=r'rungo[45]\.sh '+re.escape(str(Q/(job+'.md')))
    try:
        result=subprocess.run(['pgrep','-f',pattern],capture_output=True,timeout=min(2,remaining()))
        pids=[int(value) for value in result.stdout.decode('ascii',errors='ignore').split() if value.isdecimal()] if result.returncode==0 else []
        return {'optional_runner_PIDs':pids,'optional_runner_lookup_returncode':result.returncode}
    except (OSError,subprocess.TimeoutExpired) as error:
        return {'optional_runner_PIDs':[],'optional_runner_lookup_error_type':type(error).__name__}


def predecessor_jobs(seed,arm):
    return ['sol-cloud-numeric-v1-s%d-%s-r3-benspc'%pair for pair in ORDER[:ORDER.index((seed,arm))]]


def watcher_proof(job,seed,arm):
    if not (Q/(job+'.running')).is_file() or (Q/(job+'.exit')).exists():raise ValueError('fresh actual watcher claim required')
    copied=(Q/(job+'.md')).read_bytes()
    actual=git_blob({'path':'handoff/queue/'+job+'.md','sha256':digest(copied)})
    if actual!=copied:raise ValueError('actual copied queue differs from main')
    predecessors=[]
    for previous in predecessor_jobs(seed,arm):
        if (Q/(previous+'.running')).exists():raise ValueError('prior serial job stillrunning')
        text=(Q/(previous+'.exit')).read_text().strip()
        if not re.fullmatch(r'rc=-?[0-9]+',text):raise ValueError('prior actual physical watcher exit is not closed')
        predecessors.append({'job':previous,'actual_watcher_exit':text})
    others=running_gpu_jobs(job)
    if others:raise ValueError('another GPU watcher claim is running')
    return {'job':job,'running_marker_exists':True,'copied_queue_equals_origin_main':True,
            'other_watcher_running_claims':others,'queue_sha256':digest(copied),'actual_user_day':False,
            'predecessor_watcher_exits':predecessors,'native_Mac_version':sys.version,
            'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**optional_runner_metadata(job)}


def invocation(bootstrap,seed,arm,package,package_sha,records,proof):
    # Fixed contained members are byte pinned before this inline execution.
    # There is no archive extraction or PC checkpoint/model-weight copy.
    return '''import base64,sys
source=base64.b64decode(__BOOTSTRAP__,validate=True)
namespace={'__name__':'sealed_numeric_pc_transport'}
exec(compile(source,'sealed-numeric-PC-BOOTSTRAP.py','exec'),namespace)
raise SystemExit(namespace['run_packet'](__SEED__,__ARM__,__PACKAGE__,__PACKAGE_SHA__,__RECORDS__,__PROOF__))
'''.replace('__BOOTSTRAP__',repr(base64.b64encode(bootstrap).decode('ascii'))).replace('__SEED__',repr(seed)).replace('__ARM__',repr(arm)).replace('__PACKAGE_SHA__',repr(package_sha)).replace('__PACKAGE__',repr(package)).replace('__PROOF__',repr(proof)).replace('__RECORDS__',repr(records))


def dispatch_pc(command,source,seconds,prefix="PC"):
    record={'schema':'sol.cloud.numeric-mac.ssh-exit.v1','returncode':None,'timed_out':False,'spawned':False,
            'optimizer_status':'unknown; inspect actual saved PC evidence','actual_user_day':False,'activated':False}
    try:
        with (OUT/(prefix+'-stdout.log')).open('xb') as stdout,(OUT/(prefix+'-stderr.log')).open('xb') as stderr:
            try:
                process=subprocess.run(command,input=source,stdout=stdout,stderr=stderr,timeout=seconds)
                record.update(spawned=True,returncode=process.returncode)
            except subprocess.TimeoutExpired:
                record.update(spawned=True,timed_out=True);raise
    finally:
        record['streams']=[{'name':name,'bytes':(OUT/name).stat().st_size,'sha256':file_sha(OUT/name)}
                           for name in (prefix+'-stdout.log',prefix+'-stderr.log') if (OUT/name).is_file()]
        write_new(OUT/(prefix+'-SSH-EXIT.json'),record)
    return record


def parse_manifest(stdout,seed,arm,job):
    if not stdout or len(stdout)>1024**2:raise ValueError('missing/overbound saved PC manifest')
    try:final=json.loads(stdout.decode('utf8').splitlines()[-1])
    except (ValueError,UnicodeError,IndexError):raise ValueError('malformed saved PC manifest')
    if not isinstance(final,dict):raise ValueError('PC manifest must be an object')
    if final.get('schema')=='sol.cloud.numeric-bootstrap-failure.v1':return final
    fields={'job','seed','arm','returncode','records','worker_log','actual_user_day','activated','dispatched'}
    if not fields.issubset(final):raise ValueError('missing PC manifest fields; rawstreams preserved')
    if (final.get('schema')!='sol.cloud.numeric-fit.transport.v1' or final['job']!=job
            or final['seed']!=seed or type(final['seed']) is not int or final['arm']!=arm
            or type(final['returncode']) is not int or not isinstance(final['records'],list)
            or final['actual_user_day'] is not False or final['activated'] is not False or final['dispatched'] is not True):
        raise ValueError('PC identity/disposition differs; rawstreams preserved')
    return final


def small_records(final,prefix):
    selected=[];skipped=[]
    for record in final['records']:
        relative_path(record['relative'])
        if (not record['relative'].startswith(prefix) or type(record['bytes']) is not int or record['bytes']<0
                or not re.fullmatch('[0-9a-f]{64}',record['sha256'])):raise ValueError('exact owned final receipt member differs')
        if PurePosixPath(record['relative']).suffix in ('.json','.jsonl','.log') and record['bytes']<=1024**2:
            selected.append(record)
        else:skipped.append(record)
    if len({r['relative'] for r in final['records']})!=len(final['records']):raise ValueError('duplicated final member')
    if sum(r['bytes'] for r in selected)>4*1024**2:raise ValueError('bounded initial small receipt return exceeded; PC originals preserved')
    worker=final['worker_log'];relative_path(worker['relative'])
    if (worker['relative']!=DEPLOY+'/worker-s%d-%s-r3.log'%(final['seed'],final['arm'])
            or type(worker['bytes']) is not int or not 0<=worker['bytes']<=1024**2
            or not re.fullmatch('[0-9a-f]{64}',worker['sha256'])):raise ValueError('bounded exact worker log required')
    return selected+[worker],skipped


def collect_source(records,seed,arm):
    extras=[DEPLOY+'/TRANSPORT-s%d-%s-r3.json'%(seed,arm),DEPLOY+'/WATCHER-PROOF-s%d-%s-r3.json'%(seed,arm),DEPLOY+'/INVENTORY-s%d-%s-r3.json'%(seed,arm)]
    return '''import base64,hashlib,json,pathlib
root=pathlib.Path(__PCROOT__).resolve();expected=__RECORDS__;extras=__EXTRAS__
paths=[r['relative'] for r in expected]+extras
assert len(paths)==len(set(paths))
returned=[];total=0
for relative in paths:
 pure=pathlib.PurePosixPath(relative);assert not pure.is_absolute() and '..' not in pure.parts and ':' not in relative and '\\\\' not in relative
 path=root/relative;assert not path.is_symlink() and path.resolve().is_relative_to(root)
 before=path.stat();assert before.st_size<=1048576
 data=path.read_bytes();value=hashlib.sha256(data).hexdigest();after=path.stat()
 assert len(data)==before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
 matches=[r for r in expected if r['relative']==relative]
 if matches:assert matches[0]['bytes']==len(data) and matches[0]['sha256']==value
 total+=len(data);assert total<=8388608
 returned.append({'relative':relative,'bytes':len(data),'sha256':value,'mtime_ns':after.st_mtime_ns,'data_b64':base64.b64encode(data).decode('ascii')})
print(json.dumps({'schema':'sol.cloud.numeric.small-return.v1','records':returned,'PC_archive_created':False,'source_deletions':0,'actual_user_day':False,'activated':False}),flush=True)
'''.replace('__PCROOT__',repr(PCROOT)).replace('__EXTRAS__',repr(extras)).replace('__RECORDS__',repr(records))


def failure_record(error):
    return {'schema':'sol.cloud.numeric.mac-failure.v1','stage':STAGE,'exception_type':type(error).__name__,
            'PC_bootstrap_dispatched':DISPATCHED,'PC_originals_preserved':True,
            'optimizer_status':'unknown; inspect actual saved PC evidence' if DISPATCHED else 'not-started',
            'actual_user_day':False,'activated':False,'saved_streams':[
                {'name':name,'bytes':(OUT/name).stat().st_size,'sha256':file_sha(OUT/name)}
                for name in ('PC-stdout.log','PC-stderr.log','PC-SSH-EXIT.json','SMALL-COLLECT-stdout.log','SMALL-COLLECT-stderr.log','SMALL-COLLECT-SSH-EXIT.json')
                if OUT is not None and (OUT/name).is_file()]}


def main():
    global STARTED,OUT,STAGE,DISPATCHED
    parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,choices=(0,1),required=True)
    parser.add_argument('--arm',choices=('loop','plain'),required=True);parser.add_argument('--spec',required=True)
    parser.add_argument('--spec-sha256',required=True);parser.add_argument('--started-monotonic',type=float,required=True)
    args=parser.parse_args();STARTED=args.started_monotonic
    if platform.system()!='Darwin' or sys.version_info[:3]!=(3,9,6) or Path.cwd().resolve()!=W.resolve():
        raise ValueError('verified native Mac3.9.6 and actual watcher sourcecwd required')
    OUT=W/OWN/('execution-r3-s%d-%s'%(args.seed,args.arm));OUT.mkdir(parents=True,exist_ok=False)
    write_new(OUT/'MAC-LAUNCH-START.json',{'seed':args.seed,'arm':args.arm,'actual_user_day':False,'outer_seconds':600})
    STAGE='specification';raw=Path(args.spec).read_bytes()
    if digest(raw)!=args.spec_sha256:raise ValueError('exact transport spec pin differs')
    spec=json.loads(raw);job='sol-cloud-numeric-v1-s%d-%s-r3-benspc'%(args.seed,args.arm)
    if (spec.get('schema')!='sol.cloud.numeric-mac-launch-spec.v1' or spec.get('seed')!=args.seed
            or spec.get('arm')!=args.arm or spec.get('job')!=job or spec.get('pc_root')!=PCROOT):
        raise ValueError('fixed sealed transport identity differs')
    STAGE='actual watcher ownership';proof=watcher_proof(job,args.seed,args.arm)
    package_raw=git_blob(spec['package']);package=json.loads(package_raw);bootstrap=git_blob(spec['bootstrap'])
    if package.get('pc_root')!=PCROOT:raise ValueError('fixed package PCroot differs')
    plan_pin=package['plan'];plan=json.loads(git_blob(plan_pin));namespace=plan['run_namespace']
    if not re.fullmatch('run-[a-z0-9-]+',namespace):raise ValueError('literal owned run namespace required')
    records=[]
    for pin in package['files']:
        data=git_blob(pin);records.append(dict(pin,data_b64=base64.b64encode(data).decode('ascii')))
    if sum(r['bytes'] for r in records)>8*1024**2:raise ValueError('exact included source packet exceeds8MiB')
    proof['remaining_seconds']=remaining(5);write_new(OUT/'MAC-WATCHER-PROOF.json',proof)
    source=invocation(bootstrap,args.seed,args.arm,package,spec['package']['sha256'],records,proof)
    STAGE='native PC bootstrap dispatch';DISPATCHED=True
    exit_record=dispatch_pc(['ssh','-T',*STRICT,'benspc',PCPY+' -X utf8 -B -'],source.encode('utf8'),remaining(5))
    STAGE='parse exact saved PC manifest';stdout=(OUT/'PC-stdout.log').read_bytes();final=parse_manifest(stdout,args.seed,args.arm,job)
    if final.get('schema')=='sol.cloud.numeric-bootstrap-failure.v1':
        write_new(OUT/'PC-BOOTSTRAP-FAILURE.json',final);raise RuntimeError('PC bootstrap failed; exactstage/stdout/stderr preserved')
    if exit_record['returncode']!=final['returncode']:raise ValueError('SSH and PC disposition differ')
    write_new(OUT/'PC-FINAL-MANIFEST.json',final)
    records,skipped=small_records(final,'artifacts/sol-cloud-numeric-fit-20260930/'+namespace+'/seed%d/'%args.seed+args.arm+'/')
    STAGE='copy bounded exact saved small evidence'
    collection_exit=dispatch_pc(['ssh','-T',*STRICT,'benspc',PCPY+' -X utf8 -B -'],
                                collect_source(records,args.seed,args.arm).encode('utf8'),remaining(),prefix='SMALL-COLLECT')
    if collection_exit['returncode']!=0:raise RuntimeError('saved small-return SSH failed; rawbytes retained')
    packet=json.loads((OUT/'SMALL-COLLECT-stdout.log').read_bytes())
    if packet.get('schema')!='sol.cloud.numeric.small-return.v1' or packet.get('PC_archive_created') is not False or packet.get('source_deletions')!=0:
        raise ValueError('small-return protocol differs')
    expected_paths=[r['relative'] for r in records]+[DEPLOY+'/TRANSPORT-s%d-%s-r3.json'%(args.seed,args.arm),
                    DEPLOY+'/WATCHER-PROOF-s%d-%s-r3.json'%(args.seed,args.arm),DEPLOY+'/INVENTORY-s%d-%s-r3.json'%(args.seed,args.arm)]
    if ([r['relative'] for r in packet['records']]!=expected_paths or len(set(expected_paths))!=len(expected_paths)):
        raise ValueError('exact small-return member set/order differs')
    for item in packet['records']:
        relative_path(item['relative']);data=base64.b64decode(item.pop('data_b64'),validate=True)
        if len(data)!=item['bytes'] or digest(data)!=item['sha256']:raise ValueError('small-return byte closure differs')
        target=OUT/'copied'/item['relative'];target.parent.mkdir(parents=True,exist_ok=True)
        if not target.resolve().is_relative_to(OUT.resolve()):raise ValueError('local small-return containment differs')
        with target.open('xb') as stream:stream.write(data)
    packet.update(outer_wall_seconds=time.monotonic()-STARTED,job=job,returncode=final['returncode'],
                  skipped_large_evidence=skipped,PC_weights_and_originals_preserved=True)
    write_new(OUT/'SMALL-RETURN.json',packet)
    if packet['outer_wall_seconds']>600:raise TimeoutError('shared transport deadline exceeded; originals preserved')
    print(json.dumps({'job':job,'returncode':final['returncode'],'small_records':len(packet['records']),
                      'actual_user_day':False,'activated':False,'PC_originals_preserved':True}),flush=True)
    return final['returncode']


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        failure=failure_record(error)
        if OUT is not None and OUT.is_dir() and not (OUT/'MAC-FAILURE.json').exists():write_new(OUT/'MAC-FAILURE.json',failure)
        print(json.dumps(failure,sort_keys=True),flush=True);raise SystemExit(1)
