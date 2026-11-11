"""Pre-staged, serial four-arm TRAIN continuation using committed lock/guard."""
import argparse
import json
import os
from pathlib import Path
import site
import subprocess
import sys
import time


def execute(request_path):
    request=json.loads(Path(request_path).read_bytes());sys.path.insert(0,request['pkg'])
    import pc_driver as dmod
    import pc_guard
    assert pc_guard.DRIVER_MARK=='pc_driver.py'
    for name,h in request['launcher_sha256'].items():assert dmod.sha_file(Path(request['pkg'])/name)==h
    d=dmod.Driver(request);cfgpath=d.root/request['config']['path']
    assert dmod.sha_file(cfgpath)==request['config']['sha256'];cfg=json.loads(cfgpath.read_bytes())
    for pin in (cfg['continuation_runner'],):assert dmod.sha_file(d.root/pin['path'])==pin['sha256']
    batchdir=d.state/'continuations'/d.batch_id;batchdir.mkdir(parents=True,exist_ok=False)
    state={'batch_id':d.batch_id,'commit':request['commit'],'phase':'TRAIN-only-continuation','status':'preflight','jobs':[],'queued_utc':request['queued_utc'],'driver_pid':os.getpid(),'config_sha256':request['config']['sha256']}
    def save():dmod.write_json(batchdir/'BATCH.json',state)
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
        for seed,arm in ((0,'loop'),(0,'plain'),(1,'loop'),(1,'plain')):
            job='continue40-s%d-%s-%s'%(seed,arm,d.batch_id);jobdir=batchdir/job;jobdir.mkdir()
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
                            r=json.loads(complete.split(b'\n',1)[0]);assert r['update']==5121 and r['additional_update']==1 and r['visit_for_row']==21
                            dmod.write_json(jobdir/'FIRST-UPDATE.json',{'job_id':job,'detected_utc':dmod.iso(),'first_update':r['update'],'first_additional_update':1,'first_visit':r['visit_for_row'],'numeric_CE':r['numeric_CE'],'preclip_norm':r['preclip_norm'],'lr':r['lr'],'runner_start_to_first_update_detected_seconds':(dmod.now()-started).total_seconds()},exclusive=True)
                            first=True
                        offset+=len(complete);count+=complete.count(b'\n')
                elapsed=(dmod.now()-started).total_seconds();js.update(additional_updates=count,status='training' if first else 'runner_started')
                dmod.write_json(jobdir/'PROGRESS.json',{'job_id':job,'utc':dmod.iso(),'additional_updates':count,'target_additional_updates':5120,'elapsed_seconds':elapsed,'optimizer_updates_per_wall_second':count/elapsed if elapsed else None,'runner_returncode':rc});save()
                if rc is not None:break
                time.sleep(10)
            ended=dmod.now();closedpath=matrix/('seed%d'%seed)/arm/'CLOSED.json'
            closed=json.loads(closedpath.read_bytes()) if closedpath.exists() else None
            success=rc==0 and closed and closed['closed'] is True and count==5120 and closed['additional_optimizer_updates']==5120
            js.update(status='completed' if success else 'failed',returncode=rc,runner_ended_utc=dmod.iso(ended),runner_wall_seconds=(ended-started).total_seconds())
            dmod.write_json(jobdir/'EXIT.json',{**js,'CLOSED':closed,'stdout_sha256':dmod.sha_file(jobdir/'runner-stdout.log'),'stderr_sha256':dmod.sha_file(jobdir/'runner-stderr.log')},exclusive=True);save()
            if not success:state['status']='failed';break
        else:state['status']='completed'
        state['driver_ended_utc']=dmod.iso();save()
    except Exception as error:
        state.update(status='failed',error_type=type(error).__name__,error=str(error),driver_ended_utc=dmod.iso());save()
        if proc is not None and proc.poll() is None:
            state.update(status='monitor_error_owned_runner_still_running',owned_runner_pid=proc.pid);save()
            proc.wait()
            state.update(status='failed',owned_runner_returncode=proc.returncode,driver_ended_utc=dmod.iso());save()
    finally:
        if locked:
            holder=json.loads(d.lock.read_bytes())
            if holder.get('pid')==os.getpid():os.replace(d.lock,batchdir/'LOCK.released.json')
    return 0 if state['status']=='completed' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);raise SystemExit(execute(p.parse_args().request))
