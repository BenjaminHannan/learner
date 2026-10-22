"""One exclusive PC owner for the approved initial-only four-fit notebook/inline pilot."""
import argparse
import json
import os
from pathlib import Path
import site
import subprocess
import sys
import time


def execute(path):
    r=json.loads(Path(path).read_bytes());sys.path.insert(0,r['pkg'])
    import pc_driver as dmod
    import pc_guard
    assert pc_guard.DRIVER_MARK=='pc_driver.py'
    for n,h in r['launcher_sha256'].items():assert dmod.sha_file(Path(r['pkg'])/n)==h
    d=dmod.Driver(r);job=d.batch_id;out=d.state/'fresh-evaluations'/job;out.mkdir(parents=True,exist_ok=False)
    state={'job_id':job,'driver_pid':os.getpid(),'driver_started_utc':dmod.iso(),'status':'preflight','optimizer_updates':0,'commit':r['commit']}
    def save():dmod.write_json(out/'STATE.json',state)
    save();locked=False;proc=None
    try:
        assert not d.lock.exists(),'another lock; no queue behind'
        d.acquire_lock();locked=True
        decision=d.guard(out);assert decision['ok'],'ownership/GPU guard refused'
        mf=d.root/r['plan']['path'];assert dmod.sha_file(mf)==r['plan']['sha256']
        m=json.loads(mf.read_bytes());assert dmod.sha_file(d.root/m['runner']['path'])==m['runner']['sha256']
        matrix=d.root/m['output_namespace'];assert not matrix.exists(),'existing fresh attempt; no duplicate'
        argv=[sys.executable,'-X','utf8','-B',str(d.root/m['runner']['path']),'--root',str(d.root),'--plan',str(mf),'--plan-sha256',r['plan']['sha256']]
        dmod.write_json(out/'RUNNER-ARGV.json',{'argv':argv},exclusive=True)
        env=dict(os.environ,JOB=job,TREE=str(d.root.resolve()),PYTHONUNBUFFERED='1',PYTHONPATH=os.pathsep.join(site.getsitepackages()),PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        with (out/'runner-stdout.log').open('xb') as stdout,(out/'runner-stderr.log').open('xb') as stderr:
            proc=subprocess.Popen(argv,cwd=str(d.root),env=env,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
        started=dmod.now();state.update(status='runner_started',runner_pid=proc.pid,runner_started_utc=dmod.iso(started));save()
        while proc.poll() is None:
            elapsed=(dmod.now()-started).total_seconds()
            raw=matrix/'ANSWERS.jsonl';count=sum(l.endswith(b'\n') for l in raw.open('rb')) if raw.exists() else 0
            updates=sum(sum(l.endswith(b'\n') for l in f.open('rb')) for f in matrix.glob('seed*/*/TRAIN-RAW.jsonl')) if matrix.exists() else 0
            dmod.write_json(out/'PROGRESS.json',{'utc':dmod.iso(),'saved_native_calls':count,'expected':128,'elapsed_seconds':elapsed,'optimizer_updates':updates})
            if elapsed>600:
                # Only this wrapper's owned process, under the approved wall watchdog.
                proc.terminate();proc.wait(timeout=30);raise RuntimeError('owned pilot exceeded600second wall cap')
            time.sleep(1)
        ended=dmod.now();closed=json.loads((matrix/'CLOSED.json').read_bytes()) if (matrix/'CLOSED.json').exists() else None
        state.update(status='completed' if proc.returncode==0 and closed and closed['closed'] else 'failed',returncode=proc.returncode,runner_ended_utc=dmod.iso(ended),runner_wall_seconds=(ended-started).total_seconds())
        dmod.write_json(out/'EXIT.json',{**state,'CLOSED':closed,'stderr_sha256':dmod.sha_file(out/'runner-stderr.log'),'stdout_sha256':dmod.sha_file(out/'runner-stdout.log')},exclusive=True);save()
    except Exception as e:
        state.update(status='failed',error_type=type(e).__name__,error=str(e));save()
        if proc is not None and proc.poll() is None:
            state.update(status='monitor_error_owned_runner',runner_pid=proc.pid);save();proc.terminate();proc.wait(timeout=30)
    finally:
        if locked and json.loads(d.lock.read_bytes()).get('pid')==os.getpid():os.replace(d.lock,out/'LOCK.released.json')
    return 0 if state['status']=='completed' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);raise SystemExit(execute(p.parse_args().request))
