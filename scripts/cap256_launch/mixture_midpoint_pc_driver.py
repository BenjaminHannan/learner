"""Serial frozen mixture fit with hard owned-process wall caps; no dispatch by import."""
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
    for pin in (cfg['continuation_runner'],cfg['evaluation_runner']):assert dmod.sha_file(d.root/pin['path'])==pin['sha256']
    assert cfg['dispatch_allowed'] is True
    assert cfg['budget']['worker_seconds']==2400 and cfg['budget']['total_fit_seconds']==10800
    assert 0<cfg['budget']['remaining_fit_seconds']<=10800
    assert cfg['budget']['remaining_fit_seconds']+cfg['budget']['failed_attempt_charged_seconds']==10800
    assert cfg['budget']['failed_attempt_charged_seconds']>=1532.770885
    remaining=cfg['budget']['remaining_fit_seconds']
    batchdir=d.state/'mixtures'/d.batch_id;batchdir.mkdir(parents=True,exist_ok=False)
    state={'batch_id':d.batch_id,'commit':request['commit'],'phase':'TRAIN-only-continuation','status':'preflight','jobs':[],'queued_utc':request['queued_utc'],'driver_pid':os.getpid(),'config_sha256':request['config']['sha256']}
    def save():dmod.write_json(batchdir/'BATCH.json',state)
    dmod.write_json(batchdir/'GUIDE-START.json',guide_start,exclusive=True)
    save();locked=False;proc=None
    try:
        if d.lock.exists():raise RuntimeError('existing lock; do not queue behind')
        d.acquire_lock();locked=True
        matrix=d.root/cfg['output_namespace']
        if matrix.exists():raise RuntimeError('output namespace already exists; no duplicate continuation')
        for e in cfg['sources']:
            assert dmod.sha_file(d.root/e['checkpoint']['path'])==e['checkpoint']['sha256']
            assert dmod.sha_file(d.root/e['closed']['path'])==e['closed']['sha256']
        state['status']='running';save()
        for seed,arm in cfg['execution_order']:
            if time.monotonic()-matrix_started>=remaining:raise RuntimeError('remaining aggregate fit wall cap exhausted')
            job='mixture10240-s%d-%s-%s'%(seed,arm,d.batch_id);jobdir=batchdir/job;jobdir.mkdir()
            decision=d.guard(jobdir)
            if not decision['ok']:raise RuntimeError('ownership/GPU guard refused')
            argv=[sys.executable,'-X','utf8','-B',str(d.root/cfg['continuation_runner']['path']),'--root',str(d.root),'--config',str(cfgpath),'--config-sha256',request['config']['sha256'],'--seed',str(seed),'--arm',arm]
            dmod.write_json(jobdir/'RUNNER-ARGV.json',{'argv':argv},exclusive=True)
            env=dict(os.environ,JOB=job,TREE=str(d.root.resolve()),PYTHONUNBUFFERED='1',PYTHONPATH=os.pathsep.join(site.getsitepackages()),PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
            started=dmod.now()
            with (jobdir/'runner-stdout.log').open('xb') as out,(jobdir/'runner-stderr.log').open('xb') as err:
                proc=subprocess.Popen(argv,cwd=str(d.root),env=env,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
            js={'job_id':job,'seed':seed,'arm':arm,'runner_pid':proc.pid,'runner_started_utc':dmod.iso(started),'status':'runner_started','additional_updates':0}
            state['jobs'].append(js);save();raw=matrix/('seed%d'%seed)/arm/'TRAIN-RAW.jsonl';offset=0;count=0;first=False
            while True:
                rc=proc.poll()
                if raw.exists():
                    with raw.open('rb') as f:f.seek(offset);data=f.read()
                    complete=data[:data.rfind(b'\n')+1] if b'\n' in data else b''
                    if complete:
                        if not first:
                            r=json.loads(complete.split(b'\n',1)[0]);assert r['update']==10241 and r['additional_update']==1
                            dmod.write_json(jobdir/'FIRST-UPDATE.json',{'job_id':job,'detected_utc':dmod.iso(),'first_update':r['update'],'first_additional_update':1,'first_visit':r['visit_for_row'],'numeric_CE':r['numeric_CE'],'preclip_norm':r['preclip_norm'],'lr':r['lr'],'runner_start_to_first_update_detected_seconds':(dmod.now()-started).total_seconds()},exclusive=True)
                            first=True
                        offset+=len(complete);count+=complete.count(b'\n')
                elapsed=(dmod.now()-started).total_seconds();js.update(additional_updates=count,status='training' if first else 'runner_started')
                dmod.write_json(jobdir/'PROGRESS.json',{'job_id':job,'utc':dmod.iso(),'additional_updates':count,'target_additional_updates':10240,'elapsed_seconds':elapsed,'optimizer_updates_per_wall_second':count/elapsed if elapsed else None,'runner_returncode':rc});save()
                if rc is not None:break
                if elapsed>2400 or time.monotonic()-matrix_started>remaining:
                    js['cap_exceeded']=True;save()
                    proc.kill();proc.wait(timeout=10);raise RuntimeError('owned mixture runner hard wall cap exceeded')
                time.sleep(1)
            ended=dmod.now();closedpath=matrix/('seed%d'%seed)/arm/'CLOSED.json'
            closed=receipt_io.read_json(closedpath) if closedpath.exists() else None
            success=rc==0 and closed and closed['closed'] is True and count==10240 and closed['additional_optimizer_updates']==10240
            js.update(status='completed' if success else 'failed',returncode=rc,runner_ended_utc=dmod.iso(ended),runner_wall_seconds=(ended-started).total_seconds())
            dmod.write_json(jobdir/'EXIT.json',{**js,'CLOSED':closed,'stdout_sha256':dmod.sha_file(jobdir/'runner-stdout.log'),'stderr_sha256':dmod.sha_file(jobdir/'runner-stderr.log')},exclusive=True);save()
            if not success:state['status']='failed';break
        else:
            state['replacement_fit_and_overhead_seconds']=time.monotonic()-matrix_started
            state['charged_failed_attempt_seconds']=cfg['budget']['failed_attempt_charged_seconds']
            if state['replacement_fit_and_overhead_seconds']>remaining:raise RuntimeError('remaining aggregate fit wall cap exceeded')
            state['status']='final_dev32_evaluation';save()
            jobdir=batchdir/'dev32';jobdir.mkdir()
            if not d.guard(jobdir)['ok']:raise RuntimeError('evaluation ownership/GPU guard refused')
            argv=[sys.executable,'-X','utf8','-B',str(d.root/cfg['evaluation_runner']['path']),'--root',str(d.root),'--config',str(cfgpath),'--config-sha256',request['config']['sha256']]
            dmod.write_json(jobdir/'RUNNER-ARGV.json',{'argv':argv},exclusive=True)
            with (jobdir/'runner-stdout.log').open('xb') as out,(jobdir/'runner-stderr.log').open('xb') as err:
                proc=subprocess.Popen(argv,cwd=str(d.root),env=env,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
            try:rc=proc.wait(timeout=1200)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait(timeout=10);raise RuntimeError('owned evaluation hard1200s wall cap exceeded')
            closed=matrix/'dev32/CLOSED.json'
            success=rc==0 and closed.exists() and receipt_io.read_json(closed)['native_calls']==128
            dmod.write_json(jobdir/'EXIT.json',{'returncode':rc,'closed':success},exclusive=True)
            state['status']='completed' if success else 'failed'

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
