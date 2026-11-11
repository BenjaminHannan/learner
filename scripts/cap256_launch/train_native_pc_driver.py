"""Conditional train_native with existing ownership lock and hard600s cap; no dispatch by import."""
import argparse
import json
import os
from pathlib import Path
import site
import subprocess
import sys
import time


def execute(request_path):
    matrix_started=time.monotonic()
    request=json.loads(Path(request_path).read_bytes());sys.path.insert(0,request['pkg'])
    import pc_driver as dmod
    import pc_guard
    import receipt_io
    import recovery_guide
    assert pc_guard.DRIVER_MARK=='pc_driver.py'
    assert all(name in request['launcher_sha256'] for name in ('receipt_io.py','recovery_guide.py'))
    for name,h in request['launcher_sha256'].items():assert dmod.sha_file(Path(request['pkg'])/name)==h
    guide_start=recovery_guide.require_start(request['root'],request)
    dmod.write_json=receipt_io.write_json
    d=dmod.Driver(request);cfgpath=d.root/request['config']['path']
    assert dmod.sha_file(cfgpath)==request['config']['sha256'];cfg=json.loads(cfgpath.read_bytes())
    for pin in (cfg['evaluation_runner'],):assert dmod.sha_file(d.root/pin['path'])==pin['sha256']
    assert cfg['dispatch_allowed'] is True
    assert cfg['budget']['wall_seconds']==600 and cfg['budget']['new_output_bytes']==67108864
    proof=receipt_io.read_json(d.root/cfg['source_verification']['path'])
    assert dmod.sha_file(d.root/cfg['source_verification']['path'])==cfg['source_verification']['sha256']
    assert proof['recount_pass']
    batchdir=d.state/'train_natives'/d.batch_id;batchdir.mkdir(parents=True,exist_ok=False)
    state={'batch_id':d.batch_id,'commit':request['commit'],'phase':'TRAIN-native-diagnostic-only','status':'preflight','jobs':[],'queued_utc':request['queued_utc'],'driver_pid':os.getpid(),'config_sha256':request['config']['sha256']}
    def save():dmod.write_json(batchdir/'BATCH.json',state)
    dmod.write_json(batchdir/'GUIDE-START.json',guide_start,exclusive=True)
    save();locked=False;proc=None
    try:
        if d.lock.exists():raise RuntimeError('existing lock; do not queue behind')
        d.acquire_lock();locked=True
        matrix=d.root/cfg['output_namespace']
        if matrix.exists():raise RuntimeError('output namespace already exists; no duplicate continuation')
        for e in cfg['endpoints']:
            assert dmod.sha_file(d.root/e['checkpoint']['path'])==e['checkpoint']['sha256']
            assert dmod.sha_file(d.root/e['closed']['path'])==e['closed']['sha256']
        state['status']='train_native_evaluation';save()
        jobdir=batchdir/'train64';jobdir.mkdir()
        if not d.guard(jobdir)['ok']:raise RuntimeError('train_native ownership/GPU guard refused')
        argv=[sys.executable,'-X','utf8','-B',str(d.root/cfg['evaluation_runner']['path']),'--root',str(d.root),'--config',str(cfgpath),'--config-sha256',request['config']['sha256']]
        dmod.write_json(jobdir/'RUNNER-ARGV.json',{'argv':argv},exclusive=True)
        env=dict(os.environ,JOB=d.batch_id,TREE=str(d.root.resolve()),PYTHONUNBUFFERED='1',PYTHONPATH=os.pathsep.join(site.getsitepackages()),PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        started=dmod.now()
        with (jobdir/'runner-stdout.log').open('xb') as out,(jobdir/'runner-stderr.log').open('xb') as err:
            proc=subprocess.Popen(argv,cwd=str(d.root),env=env,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
        state.update(runner_pid=proc.pid,runner_started_utc=dmod.iso(started));save()
        raw=matrix/'train64/OBSERVATIONS.jsonl';offset=0;count=0;first=False
        while True:
            rc=proc.poll()
            if raw.exists():
                with raw.open('rb') as f:f.seek(offset);data=f.read()
                complete=data[:data.rfind(b'\n')+1] if b'\n' in data else b''
                if complete:
                    if not first:
                        r=json.loads(complete.splitlines()[0])
                        dmod.write_json(jobdir/'FIRST-GENERATION.json',{'call_index':r['call_index'],'seed':r['seed'],'arm':r['arm'],'detected_utc':dmod.iso(),'optimizer_updates':0},exclusive=True);first=True
                    offset+=len(complete);count+=complete.count(b'\n');assert count<=256
            elapsed=time.monotonic()-matrix_started
            dmod.write_json(jobdir/'PROGRESS.json',{'native_calls':count,'target_native_calls':256,'optimizer_updates':0,'elapsed_seconds':elapsed,'utc':dmod.iso(),'runner_returncode':rc});state.update(native_calls=count,elapsed_seconds=elapsed);save()
            if rc is not None:break
            if elapsed+cfg.get('preparation_charged_seconds',0)>600:
                proc.kill();proc.wait(timeout=10);raise RuntimeError('owned train_native total600s cap exceeded')
            time.sleep(1)
        assert time.monotonic()-matrix_started+cfg.get('preparation_charged_seconds',0)<=600,'train_native total charged cap exceeded'
        closedpath=matrix/'train64/CLOSED.json';closed=receipt_io.read_json(closedpath) if closedpath.exists() else None
        success=rc==0 and closed and closed['closed'] is True and closed['native_calls']==256 and closed['teacherforced_dev_examples']==0 and closed['optimizer_updates']==0 and count==256
        dmod.write_json(jobdir/'EXIT.json',{'returncode':rc,'closed':bool(success),'CLOSED':closed,'stdout_sha256':dmod.sha_file(jobdir/'runner-stdout.log'),'stderr_sha256':dmod.sha_file(jobdir/'runner-stderr.log')},exclusive=True)
        state.update(status='completed' if success else 'failed',runner_ended_utc=dmod.iso(),total_charged_wall_seconds=time.monotonic()-matrix_started+cfg.get('preparation_charged_seconds',0));save()
        if state['status']=='failed':
            state['guide_failure_consultation']=recovery_guide.consult_failure(d.root,d.batch_id,RuntimeError('owned runner returned non-success'),'Stop the batch; preserve all receipts and output; no automatic retry or cap change.')
        state['driver_ended_utc']=dmod.iso();save()
    except Exception as error:
        state.update(status='failed',error_type=type(error).__name__,error=str(error),driver_ended_utc=dmod.iso())
        if proc is not None and proc.poll() is None:
            proc.kill()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                state.update(status='owned_runner_exit_unconfirmed_lock_preserved',owned_runner_pid=proc.pid)
            else:state.update(status='failed',owned_runner_returncode=proc.returncode,driver_ended_utc=dmod.iso())
        try:
            state['guide_failure_consultation']=recovery_guide.consult_failure(d.root,d.batch_id,error,'Stop only the owned runner and preserve evidence; apply bounded receipt handling; no scientific retry or cap increase.')
        except Exception as guide_error:
            state['guide_consultation_error']=repr(guide_error)
        receipt_io.write_terminal_failure(batchdir/'BATCH.json',state)
    finally:
        if locked and (proc is None or proc.poll() is not None):
            holder=receipt_io.read_json(d.lock)
            if holder.get('pid')==os.getpid():os.replace(d.lock,batchdir/'LOCK.released.json')
    return 0 if state['status']=='completed' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);raise SystemExit(execute(p.parse_args().request))
