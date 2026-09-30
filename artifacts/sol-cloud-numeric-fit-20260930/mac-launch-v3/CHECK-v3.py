#!/usr/bin/env python3
"""Model-free bounded relay launch/import and real-stream failure checks."""
import ast
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest import mock

OWN=Path(__file__).resolve().parent
SOURCE=OWN/'MAC-LAUNCH-v3.py'
spec=importlib.util.spec_from_file_location('numeric_mac_cpu',SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]


def check(name,operation):
    operation();checks.append({'name':name,'pass':True})


def reject(operation):
    try:operation()
    except (ValueError,RuntimeError,TimeoutError):return
    raise AssertionError('required refusal absent')


m.STARTED=time.monotonic()
check('native3.9 source syntax/import with no main or model',lambda:ast.parse(SOURCE.read_text(),feature_version=(3,9)))
inv=m.invocation(b"def run_packet(*args):return 0\n",0,'loop',{'files':[]},'a'*64,[],{'remaining_seconds':600})
check('native3.10 exact generated PC invocation syntax',lambda:ast.parse(inv,feature_version=(3,10)))
try:exec(compile(inv,'model-free-pc-fixture','exec'),{})
except SystemExit as error:assert error.code==0
else:raise AssertionError('expected exact entrypoint exit')
checks.append({'name':'generated PC entrypoint launch with inert stdlib function','pass':True})
check('PC collector path syntax3.10 no archive extraction',lambda:ast.parse(m.collect_source([],0,'loop'),feature_version=(3,10)))
assert m.predecessor_jobs(0,'loop')==[]
assert m.predecessor_jobs(0,'plain')==['sol-cloud-numeric-v1-s0-loop-r3-benspc']
assert m.predecessor_jobs(1,'plain')==['sol-cloud-numeric-v1-s0-loop-r3-benspc','sol-cloud-numeric-v1-s0-plain-r3-benspc','sol-cloud-numeric-v1-s1-loop-r3-benspc']
checks.append({'name':'exact serial order and closed predecessor list','pass':True})
job='sol-cloud-numeric-v1-s0-loop-r3-benspc'
final={'schema':'sol.cloud.numeric-fit.transport.v1','job':job,'seed':0,'arm':'loop','returncode':1,
       'records':[],'worker_log':{'relative':m.DEPLOY+'/worker-s0-loop-r3.log','bytes':0,'sha256':'a'*64},
       'actual_user_day':False,'activated':False,'dispatched':True}
assert m.parse_manifest(json.dumps(final).encode(),0,'loop',job)==final
checks.append({'name':'closed failed worker manifest accepted as failed disposition','pass':True})
for name,data in [('absent',b''),('malformed',b'{'),('notobject',b'[]'),('missingfields',b'{}')]:
    check('refuse '+name+' manifest preserving streams',lambda data=data:reject(lambda:m.parse_manifest(data,0,'loop',job)))
for name,changes in [('boolreturncode',{'returncode':True}),('wrongjob',{'job':'another'}),('wrongarm',{'arm':'plain'}),('activation',{'activated':True})]:
    check('refuse '+name+' finalmanifest',lambda changes=changes:reject(lambda:m.parse_manifest(json.dumps(dict(final,**changes)).encode(),0,'loop',job)))
failure={'schema':'sol.cloud.numeric-bootstrap-failure.v1','stage':'source-deployment','dispatched':False,'optimizer_status':'not-started'}
assert m.parse_manifest(json.dumps(failure).encode(),0,'loop',job)==failure
checks.append({'name':'bootstrap stage failure available without final records','pass':True})
for name in ('../outside','/absolute','C:/outside','a\\outside'):
    check('preaccess reject path '+name,lambda name=name:reject(lambda:m.relative_path(name)))
with mock.patch.object(m.subprocess,'run',side_effect=OSError('optional grep absent')):
    assert m.optional_runner_metadata(job)['optional_runner_lookup_error_type']=='OSError'
checks.append({'name':'optional PID lookup absent nonfatal','pass':True})
with mock.patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired('ownedoptionalpgrep',1)):
    assert m.optional_runner_metadata(job)['optional_runner_lookup_error_type']=='TimeoutExpired'
checks.append({'name':'optional PID lookup timeout nonfatal','pass':True})


def streams(kind):
    with tempfile.TemporaryDirectory(prefix='numeric-mac-transport-',dir='/tmp') as directory:
        m.OUT=Path(directory);m.DISPATCHED=True
        def fake(command,**kwargs):
            kwargs['stdout'].write(b'not-json\n');kwargs['stderr'].write(b'owned stdlib failure details\n')
            if kind=='timeout':raise subprocess.TimeoutExpired(command,1)
            if kind=='spawn-error':raise OSError('owned spawn failure')
            return subprocess.CompletedProcess(command,1)
        with mock.patch.object(m.subprocess,'run',side_effect=fake):
            if kind in ('timeout','spawn-error'):
                try:m.dispatch_pc(['inert-cpu-command'],b'fixture',1)
                except (subprocess.TimeoutExpired,OSError):pass
                else:raise AssertionError('expected timeout/spawn failure')
            else:assert m.dispatch_pc(['inert-cpu-command'],b'fixture',1)['returncode']==1
        assert (m.OUT/'PC-stdout.log').read_bytes()==b'not-json\n'
        assert (m.OUT/'PC-stderr.log').read_bytes()==b'owned stdlib failure details\n'
        exit_record=json.loads((m.OUT/'PC-SSH-EXIT.json').read_bytes())
        assert exit_record['optimizer_status'].startswith('unknown')
        assert exit_record['timed_out']==(kind=='timeout')
        assert m.failure_record(ValueError('missingmanifest'))['optimizer_status'].startswith('unknown')
        assert len(m.failure_record(ValueError('missingmanifest'))['saved_streams'])==3


for kind in ('nonzero','timeout','spawn-error'):check('exact stdout stderr and SSH closure '+kind,lambda kind=kind:streams(kind))
m.DISPATCHED=False;m.OUT=None
assert m.failure_record(ValueError('pre-dispatch source differs'))['optimizer_status']=='not-started'
checks.append({'name':'pre-dispatch failure clearly distinguished from unknown afterdispatch','pass':True})


def small():
    prefix='artifacts/sol-cloud-numeric-fit-20260930/run-v1/seed0/loop/'
    raw={'relative':prefix+'TRAIN-RAW.jsonl','bytes':7,'sha256':'a'*64}
    weights={'relative':prefix+'final-resume.pt','bytes':10000000,'sha256':'b'*64}
    value=dict(final,records=[raw,weights])
    selected,skipped=m.small_records(value,prefix)
    assert selected[0]==raw and skipped==[weights] and len(selected)==2
    reject(lambda:m.small_records(dict(value,records=[dict(raw,relative='outside/file.json')]),prefix))
    reject(lambda:m.small_records(dict(value,records=[raw,raw]),prefix))


check('only exact owned small evidence selected weights retained',small)
report={'schema':'sol.cloud.numeric-mac-relay-CPU-checks.v1','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'checks':checks,'passed':len(checks),'failed':0,
        'model_calls':0,'GPU_calls':0,'optimizer_updates':0,'SSH_calls':0,'live_queue_entries':0,
        'host_qualification':'Linux CPU stdlib engineering plusMac3.9/PC3.10AST; native hosts not executed by this check'}
print(json.dumps(report,indent=2))
