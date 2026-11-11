"""One exclusive PC owner for the approved fixed eight-checkpoint range comparison."""
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
        mf=d.root/r['manifest']['path'];assert dmod.sha_file(mf)==r['manifest']['sha256']
        m=json.loads(mf.read_bytes());assert dmod.sha_file(d.root/m['runner']['path'])==m['runner']['sha256']
        matrix=d.root/m['output_namespace'];assert not matrix.exists(),'existing fresh attempt; no duplicate'
        argv=[sys.executable,'-X','utf8','-B',str(d.root/m['runner']['path']),'--root',str(d.root),'--manifest',str(mf),'--manifest-sha256',r['manifest']['sha256']]
        dmod.write_json(out/'RUNNER-ARGV.json',{'argv':argv},exclusive=True)
        env=dict(os.environ,JOB=job,TREE=str(d.root.resolve()),PYTHONUNBUFFERED='1',PYTHONPATH=os.pathsep.join(site.getsitepackages()),PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        with (out/'runner-stdout.log').open('xb') as stdout,(out/'runner-stderr.log').open('xb') as stderr:
            proc=subprocess.Popen(argv,cwd=str(d.root),env=env,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
        started=dmod.now();state.update(status='runner_started',runner_pid=proc.pid,runner_started_utc=dmod.iso(started));save()
        while proc.poll() is None:
            elapsed=(dmod.now()-started).total_seconds()
            counts={}
            for key in m['checkpoint_keys']:
                raw=matrix/key/'RAW.jsonl';counts[key]=sum(l.endswith(b'\n') for l in raw.open('rb')) if raw.exists() else 0
            dmod.write_json(out/'PROGRESS.json',{'utc':dmod.iso(),'saved_predictions':counts,'expected_per_checkpoint':32,'elapsed_seconds':elapsed,'model_loaded':(matrix/'MODEL-LOADED.json').exists(),'optimizer_updates':0})
            if elapsed>1800:
                # Only this wrapper's owned process, under the approved wall watchdog.
                proc.terminate();proc.wait(timeout=30);raise RuntimeError('owned evaluation exceeded1800second wall cap')
            time.sleep(5)
        ended=dmod.now();closed=json.loads((matrix/'CLOSED.json').read_bytes()) if (matrix/'CLOSED.json').exists() else None
        state.update(status='completed' if proc.returncode==0 and closed and closed['closed'] else 'failed',returncode=proc.returncode,runner_ended_utc=dmod.iso(ended),runner_wall_seconds=(ended-started).total_seconds())
        dmod.write_json(out/'EXIT.json',{**state,'CLOSED':closed,'stderr_sha256':dmod.sha_file(out/'runner-stderr.log'),'stdout_sha256':dmod.sha_file(out/'runner-stdout.log')},exclusive=True);save()
    except Exception as e:
        state.update(status='failed',error_type=type(e).__name__,error=str(e));save()
        if proc is not None and proc.poll() is None:
            state.update(status='monitor_error_owned_runner_still_running',runner_pid=proc.pid);save();proc.wait()
    finally:
        if locked and json.loads(d.lock.read_bytes()).get('pid')==os.getpid():os.replace(d.lock,out/'LOCK.released.json')
    return 0 if state['status']=='completed' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);raise SystemExit(execute(p.parse_args().request))
