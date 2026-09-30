#!/usr/bin/env python3
"""Bounded native Mac relay for accepted-only offline CPU tokenizer counts."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import time

W=Path('/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27')
Q=Path('/Users/ben-hannan/premonition-watch/queue')
OWN='artifacts/sol-cloud-question-token-count-20260930/all1965-v1'
JOB='sol-cloud-question-token-count-1965-v1'
PCROOT='C:/Users/benja/sol-cloud-question-token-count-1965-v1'
PCPY=r'C:\Users\benja\lis300\venv\Scripts\python.exe'
STRICT=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no',
        '-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2']
STARTED=None


def digest(data):return hashlib.sha256(data).hexdigest()


def left():
    remaining=300-(time.monotonic()-STARTED)
    if remaining<=0:raise TimeoutError('total CPU transport budget exhausted')
    return remaining


def git_blob(path,expected):
    relative=PurePosixPath(path)
    if relative.is_absolute() or '..' in relative.parts or '\\' in path or ':' in path:
        raise ValueError('fixed contained source path required')
    result=subprocess.run(['git','-C',str(W),'show','origin/main:'+path],capture_output=True,
                          check=True,timeout=min(10,left()))
    if len(result.stdout)>1024**2 or digest(result.stdout)!=expected:raise ValueError('pinned main blob differs')
    return result.stdout


def pc_source(records,spec_sha):
    # Only accepted question strings, their IDs/hashes, spec, and helper are
    # shipped. No archive, labels, model bytes, or mixed source is included.
    return '''import base64,hashlib,json,os,pathlib,shutil,sys
root=pathlib.Path(__ROOT__)
assert sys.version_info[:3]==(3,10,9),'known native PC interpreter'
assert not root.exists(),'fresh owned CPU packet; no silent rerun'
assert shutil.disk_usage('C:/').free>=1073741824+8388608,'project copy preserves1GiB reserve'
records=__RECORDS__
assert sum(r['bytes'] for r in records)<=1048576,'bounded accepted-only CPU input packet'
for r in records:
 data=base64.b64decode(r['data_b64'],validate=True)
 assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
 relative=pathlib.PurePosixPath(r['path'])
 assert not relative.is_absolute() and '..' not in relative.parts and ':' not in r['path'] and '\\\\' not in r['path']
root.mkdir()
for r in records:
 path=root/r['path'];path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as f:f.write(base64.b64decode(r['data_b64'],validate=True))
 assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']
os.chdir(root)
os.environ.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1',CUDA_VISIBLE_DEVICES='')
helper=root/'scripts/sol_cloud_question_token_count_1965_v1.py'
sys.argv=[str(helper),'--spec',__SPEC__,'--spec-sha256',__SPEC_SHA__]
exec(compile(helper.read_bytes(),str(helper),'exec'),{'__name__':'__main__','__file__':str(helper)})
'''.replace('__ROOT__',repr(PCROOT)).replace('__SPEC_SHA__',repr(spec_sha)).replace('__SPEC__',repr(OWN+'/SPEC-v1.json')).replace('__RECORDS__',repr(records))


def classify(returncode,stdout):
    try:
        value=json.loads(stdout)
    except (ValueError,UnicodeError):return {'success':False,'failure':'missing or malformed actual PC JSON'}
    success=(returncode==0 and isinstance(value,dict) and value.get('schema')=='sol.cloud.question-token-counts.v2'
             and value.get('actual_host_tokenizer_execution') is True and value.get('actual_user_day') is False
             and value.get('model_calls')==0 and value.get('GPU_calls')==0 and value.get('optimizer_updates')==0
             and value.get('target_labels_loaded') is False and value.get('eos_appended_once') is True
             and isinstance(value.get('rows'),list) and len(value['rows'])==1965)
    return {'success':success,'pc_json_schema':value.get('schema') if isinstance(value,dict) else None,
            'actual_host_tokenizer_execution':value.get('actual_host_tokenizer_execution',False) if isinstance(value,dict) else False}


def main():
    global STARTED
    STARTED=time.monotonic();p=argparse.ArgumentParser();p.add_argument('--packet-sha256',required=True);args=p.parse_args()
    if Path.cwd().resolve()!=W.resolve() or platform.system()!='Darwin' or sys.version_info[:3]!=(3,9,6):
        raise ValueError('known native watcher cwd/runtime required')
    if not (Q/(JOB+'.running')).is_file() or (Q/(JOB+'.exit')).exists():raise ValueError('actual fresh watcher claim required')
    if (Q/(JOB+'.md')).read_bytes()!=git_blob('handoff/queue/'+JOB+'.md',digest((Q/(JOB+'.md')).read_bytes())):
        raise ValueError('actual copied queue must equal main')
    packet=json.loads(git_blob(OWN+'/PACKET-v1.json',args.packet_sha256))
    if packet.get('schema')!='sol.cloud.question-token-count-packet.v2' or packet.get('job')!=JOB:
        raise ValueError('fixed accepted-only question CPU packet required')
    out=W/OWN/'execution-v1';out.mkdir()
    records=[]
    for pin in packet['files']:
        data=git_blob(pin['path'],pin['sha256'])
        if len(data)!=pin['bytes']:raise ValueError('packet source size differs')
        records.append(dict(pin,data_b64=base64.b64encode(data).decode('ascii')))
    spec_sha=next(r['sha256'] for r in records if r['path']==OWN+'/SPEC-v1.json')
    source=pc_source(records,spec_sha);command=['ssh','-T',*STRICT,'benspc',PCPY+' -X utf8 -B -']
    rc=None;stdout=b'';stderr=b'';error_type=None
    try:
        completed=subprocess.run(command,input=source.encode('utf8'),capture_output=True,timeout=left())
        rc=completed.returncode;stdout=completed.stdout;stderr=completed.stderr
    except subprocess.TimeoutExpired as error:
        stdout=error.stdout or b'';stderr=error.stderr or b'';error_type=type(error).__name__
    except OSError as error:error_type=type(error).__name__
    for name,data in (('PC-STDOUT.json',stdout),('PC-STDERR.log',stderr)):
        with (out/name).open('xb') as f:f.write(data)
    result=classify(rc,stdout)
    result.update(schema='sol.cloud.question-token-count-transport.v1',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  ssh_returncode=rc,error_type=error_type,wall_seconds=time.monotonic()-STARTED,
                  pc_stdout_sha256=digest(stdout),pc_stderr_sha256=digest(stderr),packet_sha256=args.packet_sha256,
                  source_files=[{k:r[k] for k in ('path','bytes','sha256')} for r in records],actual_user_day=False,
                  LM_weights_loaded=False,model_calls=0,GPU_calls=0,optimizer_updates=0,generated_report_training_eligible=False)
    with (out/'TRANSPORT-v1.json').open('x',encoding='utf8') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,sort_keys=True))
    return 0 if result['success'] else 1


if __name__=='__main__':raise SystemExit(main())
