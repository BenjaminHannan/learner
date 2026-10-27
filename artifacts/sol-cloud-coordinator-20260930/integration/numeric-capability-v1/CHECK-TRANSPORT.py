#!/usr/bin/env python3
"""CPU exact-source deployment and essential inventory negative checks."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import types

SOURCE=Path(__file__).with_name('PC-BOOTSTRAP.py')
module=types.ModuleType('isolated_numeric_transport')
exec(compile(SOURCE.read_bytes(),str(SOURCE),'exec'),module.__dict__)
checks=[]

def checked(name,call,raises=False):
    try:
        call()
        passed=not raises
    except (ValueError,RuntimeError):passed=raises
    checks.append({'name':name,'passed':passed})
    if not passed:raise AssertionError(name)

def package(records):
    p={'files':[{k:r[k] for k in ('path','bytes','sha256')} for r in records]}
    return p,hashlib.sha256(json.dumps(p,sort_keys=True,indent=2).encode()+b'\n').hexdigest()

import base64
with tempfile.TemporaryDirectory(prefix='sol-numeric-transport-') as d:
    module.ROOT=Path(d)/'fresh';data=b'pinned source bytes\n'
    r={'path':'scripts/example.py','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'data_b64':base64.b64encode(data).decode()}
    p,h=package([r])
    checked('exact source deployment',lambda:module.deploy([r],p,h))
    checked('same exact bytes preserved',lambda:module.deploy([r],p,h))
    assert (module.ROOT/r['path']).read_bytes()==data
    module.DEPLOY=module.ROOT/'transport-telemetry'
    retained=module.ROOT/'artifacts/sol-cloud-numeric-fit-20260930/run-v2/seed0/loop/final-resume.pt'
    retained.parent.mkdir(parents=True);retained.write_bytes(b'old checkpoint retained')
    checked('retained model output excluded from source delivery bytes',lambda: (_ for _ in ()).throw(AssertionError()) if module.deploy([r],p,h)!=module.allocated(len(data)) else None)
    assert retained.read_bytes()==b'old checkpoint retained'
    for path in ['../outside.py','/absolute.py','C:/outside.py','a\\outside.py']:
        bad=dict(r,path=path);p,h=package([bad]);checked('refuse path '+path,lambda:module.deploy([bad],p,h),True)
    bad=dict(r,sha256='0'*64);p,h=package([bad]);checked('refuse mismatched source hash',lambda:module.deploy([bad],p,h),True)
    p,h=package([r]);checked('refuse mismatched package hash',lambda:module.deploy([r],p,'0'*64),True)
    (module.ROOT/r['path']).write_bytes(b'preserved conflicting source')
    checked('refuse existing source mismatch without overwrite',lambda:module.deploy([r],p,h),True)
    assert (module.ROOT/r['path']).read_bytes()==b'preserved conflicting source'

original=module.subprocess.run
probe=module.os.getpid()
def query(pid_output='123',gpu_output='1836, 0',names=None):
    def run(argv,**kwargs):
        if argv[0]=='powershell' and 'ParentProcessId' in argv[-1]:
            value=json.dumps([{'ProcessId':probe,'ParentProcessId':1,'Name':'python.exe'}])
        elif argv[0]=='powershell':value=json.dumps([] if names is None else names)
        elif '--query-compute-apps=pid' in argv:value=pid_output
        else:value=gpu_output
        return types.SimpleNamespace(stdout=value)
    module.subprocess.run=run
    return module.inventory()
checked('desktop GPU baseline accepted',lambda:query())
checked('empty optional vanished process names accepted',lambda:query(names=[]))
checked('malformed essential GPU PID refused',lambda:query(pid_output='garbage'),True)
checked('negative GPU memory refused',lambda:query(gpu_output='-1, 0'),True)
checked('GPU utilization101 refused',lambda:query(gpu_output='1836, 101'),True)
checked('explicit Python GPU process refused',lambda:query(names=[{'ProcessId':123,'Name':'pythonw.exe'}]),True)
def failed_optional(argv,**kwargs):
    if argv[0]=='powershell' and 'ParentProcessId' not in argv[-1]:raise module.subprocess.TimeoutExpired(argv,15)
    if argv[0]=='powershell':return types.SimpleNamespace(stdout=json.dumps([{'ProcessId':probe,'ParentProcessId':1,'Name':'python.exe'}]))
    if '--query-compute-apps=pid' in argv:return types.SimpleNamespace(stdout='123')
    return types.SimpleNamespace(stdout='1836, 0')
module.subprocess.run=failed_optional
checked('optional name query timeout nonfatal',lambda:module.inventory())
module.subprocess.run=original
import subprocess,sys,threading
with tempfile.TemporaryDirectory(prefix='sol-global-stream-check-') as d:
    module.ROOT=Path(d);module.DEPLOY=module.ROOT/'transport';module.DEPLOY.mkdir()
    fixed=module.ROOT/'source.py';fixed.write_bytes(b'fixed source')
    module.GLOBAL_SOURCE_PATHS={fixed};module.GLOBAL_ACTIVE=True;module.ALLOCATION_UNIT=4096
    disk_usage=module.shutil.disk_usage;module.shutil.disk_usage=lambda path:types.SimpleNamespace(free=10*1024**3)
    path=module.DEPLOY/'accepted.log';failures=[];event=threading.Event()
    child=subprocess.Popen([sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'z'*1048576)"],stdout=subprocess.PIPE)
    with path.open('xb') as stream:module.pump_owned_stream(child.stdout,stream,path,failures,event)
    assert child.wait(timeout=5)==0 and not failures and path.read_bytes()==b'z'*1048576
    checks.append({'name':'actual CPU child stream exact1MiB accepted','passed':True})
    overflow=module.DEPLOY/'overflow.log';failures=[];event=threading.Event()
    child=subprocess.Popen([sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'x'*7340032)"],stdout=subprocess.PIPE)
    with overflow.open('xb') as stream:module.pump_owned_stream(child.stdout,stream,overflow,failures,event)
    if child.poll() is None:child.kill()
    child.wait(timeout=5)
    assert event.is_set() and failures and len(overflow.read_bytes())==failures[0]['accepted_stream_bytes']
    assert overflow.read_bytes()==b'x'*overflow.stat().st_size
    assert module.global_allocated()+module.GLOBAL_SLACK<=module.GLOBAL_CAP
    checks.append({'name':'overflow refuses before cap and preserves accepted stream prefix','passed':True})
    module.shutil.disk_usage=disk_usage;module.GLOBAL_ACTIVE=False
ast.parse(SOURCE.read_bytes(),feature_version=(3,10))
out={'schema':'sol.cloud.numeric-transport-CPU-checks.v1','source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'checks':checks,'passed':sum(x['passed'] for x in checks),'failed':sum(not x['passed'] for x in checks),'GPU_calls':0,'model_calls':0,'optimizer_updates':0,'SSH_calls':0,'native310_AST':True}
Path(__file__).with_name('TRANSPORT-CHECKS-v5.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='checks'},sort_keys=True))
