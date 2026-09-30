#!/usr/bin/env python3
"""CPU-only transport failure checks; no SSH, model, optimizer or queue."""
import ast
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

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('exposure_mac_failure_cpu', HERE/'MAC-LAUNCH-v2.py')
m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]


def check(name, operation):
    evidence=operation()
    checks.append({'name':name,'pass':True,'evidence':evidence})


def rejected(data):
    try:m.parse_final_manifest(data,0,'sol-cloud-exposure16-r5-s0-r1-benspc')
    except ValueError as e:return {'type':type(e).__name__,'message':str(e)}
    raise AssertionError('invalid manifest admitted')


valid={'job':'sol-cloud-exposure16-r5-s0-r1-benspc','seed':0,'returncode':0,'records':[],
       'actual_user_day':False,'activated':False}
check('valid closed manifest',lambda:{'accepted':m.parse_final_manifest(json.dumps(valid).encode(),0,valid['job'])==valid})
for name,data in [('absent',b''),('malformed',b'not-json'),('nonobject',b'[]'),
                  ('partial actual PC failure',b'{"status":"SAFE EXPOSURE TRANSPORT FAILURE; originals preserved","type":"AssertionError","actual_user_day":false}'),
                  ('missing records',json.dumps({k:v for k,v in valid.items() if k!='records'}).encode()),
                  ('missing returncode',json.dumps({k:v for k,v in valid.items() if k!='returncode'}).encode()),
                  ('Boolean returncode',json.dumps(dict(valid,returncode=False)).encode()),
                  ('wrong job',json.dumps(dict(valid,job='different')).encode()),
                  ('activated',json.dumps(dict(valid,activated=True)).encode()),
                  ('oversize',b'x'*(256*1024+1))]:
    check('refuse '+name,lambda data=data:rejected(data))


def dispatch_case(source,seconds,expected,timeout=False,missing_command=False):
    with tempfile.TemporaryDirectory(prefix='sol-exposure-transport-cpu-') as temporary:
        out=Path(temporary)
        command=['/nonexistent/sol-owned-command'] if missing_command else [sys.executable,'-B','-']
        try:
            result=m.dispatch_pc(command,source.encode(),out,seconds)
            assert not timeout and not missing_command
        except subprocess.TimeoutExpired:
            assert timeout
        except FileNotFoundError:
            assert missing_command
        result=json.loads((out/'PC-SSH-EXIT.json').read_text())
        assert result['returncode']==expected and result['timed_out']==timeout
        assert result['optimizer_updates'].startswith('unknown')
        assert {r['name'] for r in result['streams']}=={'PC-stdout.log','PC-stderr.log'}
        for r in result['streams']:
            assert m.sha(out/r['name'])==r['sha256'] and (out/r['name']).stat().st_size==r['bytes']
        if expected==1:
            assert b'RuntimeError: owned CPU failure' in (out/'PC-stderr.log').read_bytes()
        if timeout:
            assert (out/'PC-stdout.log').read_bytes()==b'owned-before-timeout\n'
        return {'returncode':result['returncode'],'timed_out':result['timed_out'],
                'exact_stream_hashes_verified':True,'optimizer_updates':result['optimizer_updates']}


check('successful dispatch exact streams',lambda:dispatch_case('print("owned-success",flush=True)',2,0))
check('PC failure exact stderr and exit retained',lambda:dispatch_case('raise RuntimeError("owned CPU failure")',2,1))
check('timeout retains streams and unknown steps',lambda:dispatch_case('import time;print("owned-before-timeout",flush=True);time.sleep(5)',0.2,None,True))
check('spawn failure still writes exit and streams',lambda:dispatch_case('',2,None,missing_command=True))


def failure(dispatched):
    m.OUT=None;m.DISPATCHED=dispatched;m.STAGE='CPU preflight' if not dispatched else 'parse saved PC final manifest'
    r=m.failure_record(ValueError('owned error'))
    assert r['optimizer_updates']==('unknown; inspect original saved ledger' if dispatched else 0)
    assert r['stage']==m.STAGE and r['PC_bootstrap_dispatched']==dispatched
    return r


check('pre-dispatch failure proves no dispatch only',lambda:failure(False))
check('post-dispatch failure never infers zero steps',lambda:failure(True))


def optional_metadata():
    m.STARTED=time.monotonic()
    with mock.patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'')):
        missing=m.optional_runner_metadata(valid['job']);assert missing['actual_runner_pids']==[]
    with mock.patch.object(m.subprocess,'run',side_effect=subprocess.TimeoutExpired([],0.1)):
        timeout=m.optional_runner_metadata(valid['job']);assert timeout['actual_runner_pids']==[]
    with mock.patch.object(m.subprocess,'run',side_effect=FileNotFoundError('owned missing lookup')):
        unavailable=m.optional_runner_metadata(valid['job']);assert unavailable['actual_runner_pids']==[]
    return {'missing_lookup_nonfatal':True,'timeout_lookup_nonfatal':True,'unavailable_lookup_nonfatal':True}


check('optional runner metadata remains nonfatal',optional_metadata)


def syntax():
    source=(HERE/'MAC-LAUNCH-v2.py').read_text()
    ast.parse(source,feature_version=(3,9));compile(source,'sealed-launch-v2','exec')
    for name in ('PC-stderr.log','PC-SSH-EXIT.json','parse_final_manifest','failure_record'):
        assert name in source
    assert "stderr=subprocess.DEVNULL, timeout=remaining(5)" not in source
    return {'Mac39_syntax':True,'direct_GPU_model_calls':0,'SSH_calls_during_checks':0}


check('Mac3.9 syntax and failure stream wiring',syntax)
report={'schema':'sol.cloud.exposure16.mac-failure-checks.v2',
        'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'passed':len(checks),'total':len(checks),'checks':checks,
        'wrapper_sha256':hashlib.sha256((HERE/'MAC-LAUNCH-v2.py').read_bytes()).hexdigest(),
        'model_calls':0,'optimizer_updates':0,'SSH_calls':0,'queue_entries':0,
        'limits':['Local CPU subprocesses and mocked lookup only; no real remote host execution.','Original failed dispatch step count is determined by separate pinned PC postmortem, never these mocks.']}
print(json.dumps(report,indent=2))
