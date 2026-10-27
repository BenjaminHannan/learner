#!/usr/bin/env python3
"""Bounded existing-Mac-watcher→PC idle bridge. Run only inside a repo queue job.
No cron/daemon. Pinned pipeline receives the immutable day batch, never a shell string.
"""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from sol_assistant_bundle import sha,pin,verify_pin,owned,save_new,Unavailable
from sol_assistant_day_v3 import DayStore,read,load_rows

def checked_spec(path,digest):
    if sha(path)!=digest:raise Unavailable('bridge spec changed')
    s=read(path)
    if s['schema']!='sol.assistant.watcher-bridge.v3':raise Unavailable('bridge schema')
    if not (1<=s['idle_seconds']<=3600 and 1<=s['wait_seconds']<=3600 and 1<=s['pipeline_seconds']<=1800):raise Unavailable('bounded watcher budget required')
    if s['wait_seconds']+s['pipeline_seconds']>4200:raise Unavailable('75min watcher outer cap requires headroom')
    if s['pc_host']!='benspc' or not s['pc_root'].startswith('C:/Users/benja/sol-translator-ordered-v10r2'):raise Unavailable('exact approved PC target required')
    if s['pc_python']!='C:/Users/benja/lis300/venv/Scripts/python.exe':raise Unavailable('approved PC Python required')
    return s

def local_pins(s):
    for record in s['dependency_pins']:verify_pin(record)
    verify_pin(s['bundle']);verify_pin(s['remote_source'])
    if sha(__file__)!=s['remote_source']['sha256']:raise Unavailable('bridge source closure drift')

def remote(s,mode):
    if Path.cwd().resolve()!=Path(s['pc_root']).resolve():raise Unavailable('wrong PC checkout')
    local_pins(s);day=DayStore(s['day_state'])
    if mode=='poll':
        from sol_assistant_ordered_bundle_v10 import verify
        verify(s['bundle']['path'])
        result=day.snapshot(s['batch_path'],bundle_pin=s['bundle'],idle_seconds=s['idle_seconds'],claim_id=s['claim_id'])
        if result['ready']:save_new(owned(s['claim_receipt']),result)
        print(json.dumps(result),flush=True);return
    receipt=read(s['claim_receipt']);batch=receipt['batch'];verify_pin(batch);rows=load_rows(batch['path'],batch['sha256'])
    if not day.unchanged(receipt['revision']):raise Unavailable('new user activity after snapshot; no training')
    if not os.environ.get('JOB') or Path(os.environ.get('TREE','')).resolve()!=Path.cwd().resolve():raise Unavailable('watcher JOB/TREE required')
    # Exact pinned commands are authored by integrator, not by day data or model text.
    phases=s['pipeline']
    if [p['name'] for p in phases]!=['night','candidate','activation']:raise Unavailable('complete night/validate-bundle/activate pipeline required')
    start=time.monotonic();completed=[]
    for phase in phases:
        local_pins(s)
        if not day.unchanged(receipt['revision']):raise Unavailable('activity resumed; candidate must remain inactive')
        replacements={'{day_batch}':batch['path'],'{day_batch_sha256}':batch['sha256']}
        command=[replacements.get(x,x) for x in phase['argv']]
        if not command or command[0]!='{python}':raise Unavailable('pinned Python entrypoint required')
        command[0]=sys.executable
        if phase['name']=='night' and not all(x in command for x in ('--day-batch','--day-batch-sha256')):raise Unavailable('night command must consume actual day snapshot')
        activation_lock=None
        if phase['name']=='activation':
            activation_lock=day.connect();activation_lock.execute('BEGIN IMMEDIATE')
            if activation_lock.execute('SELECT revision FROM state WHERE id=1').fetchone()[0]!=receipt['revision']:
                activation_lock.close();raise Unavailable('activity raced activation; candidate remains inactive')
        process=subprocess.Popen(command,env=dict(os.environ,PYTHONUTF8='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1'))
        try:
            while process.poll() is None:
                if time.monotonic()-start>s['pipeline_seconds'] or not day.unchanged(receipt['revision']):
                    process.terminate()
                    try:process.wait(timeout=20)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
                    raise Unavailable('activity/budget interrupt; inspect durable candidate, do not promote')
                time.sleep(1)
            if process.returncode:raise Unavailable('pipeline failed: '+phase['name'])
        finally:
            if process.poll() is None:process.kill();process.wait()
            if activation_lock is not None:activation_lock.close()
        completed.append(phase['name'])
    save_new(owned(s['completion_receipt']),{'completed_phases':completed,'batch':batch,'day_rows':len(rows),'revision':receipt['revision'],'claim':s['claim_id'],'learning_claim':'read actual night ledger; command rc alone is not proof','fixed4_learned_stop_qualified':False})

def mac(s,spec_path,digest):
    if not os.environ.get('JOB'):raise Unavailable('Mac watcher JOB required; no direct dispatch')
    if sys.platform!='darwin':raise Unavailable('Mac watcher transport only')
    # The owning queue uploads this exact spec+source packet before invoking this bridge.
    args=['ssh','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=20',s['pc_host']]
    def invoke(mode):
        # JSON argv travels on stdin; none of its paths are interpolated into shell code.
        payload={'root':s['pc_root'],'python':s['pc_python'],'script':s['remote_source']['path'],'spec':s['remote_spec_path'],'sha':digest,'mode':mode,'job':os.environ['JOB']}
        bootstrap="import json,os,subprocess,sys; a=json.loads(sys.stdin.readline()); os.chdir(a['root']); env=dict(os.environ,JOB=a['job'],TREE=a['root'],PYTHONUTF8='1'); sys.exit(subprocess.call([a['python'],'-X','utf8','-B',a['script'],'--spec',a['spec'],'--sha256',a['sha'],'--remote',a['mode']],env=env))"
        # Fixed executable/command, validated below; JSON is data, never shell interpolation.
        command='C:\\Users\\benja\\lis300\\venv\\Scripts\\python.exe -X utf8 -c "'+bootstrap+'"'
        return subprocess.run(args+[command],input=json.dumps(payload)+'\n',text=True,capture_output=True,timeout=s['pipeline_seconds']+60 if mode=='run' else 120)
    start=time.monotonic()
    while time.monotonic()-start<s['wait_seconds']:
        p=invoke('poll')
        if p.returncode:raise Unavailable('PC poll failed: '+p.stderr[-3000:])
        result=json.loads(p.stdout.strip().splitlines()[-1]);print(json.dumps(result),flush=True)
        if result['ready']:
            p=invoke('run');print(p.stdout,flush=True);print(p.stderr,file=sys.stderr,flush=True)
            if p.returncode:raise Unavailable('night pipeline failed; prior bundle is the recovery reference')
            return
        time.sleep(min(15,max(0,s['wait_seconds']-(time.monotonic()-start))))
    print(json.dumps({'ready':False,'reason':'bounded idle wait expired; no training executed'}))

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--sha256',required=True);p.add_argument('--remote',choices=['poll','run']);a=p.parse_args();s=checked_spec(a.spec,a.sha256)
    if a.remote:remote(s,a.remote)
    else:mac(s,a.spec,a.sha256)
if __name__=='__main__':main()
