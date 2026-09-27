#!/usr/bin/env python3
"""Mac-side single-rental lis-320 runner. All auth stays inside vastai and ssh.
Mock injection is via explicit CLI paths; no auth or key file is opened here.
"""
import argparse, hashlib, json, os, shlex, shutil, subprocess, sys, time
from pathlib import Path
A='artifacts/claude-lis320-20260926'
LABEL='claude-reading-lis320-codex-20260927'
OLD_SHA='970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b'
CAP=4.0;STOP=3.25;MAX_DPH=.85
QUERY='num_gpus=1 gpu_ram>=24 compute_cap>=800 cuda_max_good>=12.8 reliability>=0.98 cpu_cores_effective>=8 disk_space>=60 inet_down>=200 direct_port_count>=1 rentable=true'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def utc():return subprocess.check_output(['date','-u','+%FT%TZ'],text=True).strip()
class Runner:
    def __init__(self,args):
        self.a=args;self.g=Path(args.state);self.g.mkdir(parents=True,exist_ok=True)
        self.vast=os.environ.get('LIS320_VAST','vastai');self.sshbin=os.environ.get('LIS320_SSH','ssh')
        self.r=None;self.host=None;self.port=None
    def log(self,event,**kw):
        rec=dict(utc=utc(),event=event,**kw)
        with (self.g/'events.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
    def cmd(self,args,timeout=90,check=True,input=None):
        r=subprocess.run(args,input=input,capture_output=True,timeout=timeout)
        if check and r.returncode:raise RuntimeError('command failed: '+Path(args[0]).name)
        return r
    def vastjson(self,*args):
        return json.loads(self.cmd([self.vast,*args,'--raw']).stdout)
    def instances(self):
        d=self.vastjson('show','instances');return d.get('instances',[]) if isinstance(d,dict) else d
    def own(self):
        if not self.r:raise RuntimeError('no rental owned by this task')
        matches=[x for x in self.instances() if int(x['id'])==self.r['id']]
        if not matches:return None
        if matches[0].get('label')!=LABEL:raise RuntimeError('ownership label mismatch; refusing lifecycle action')
        return matches[0]
    def spent(self):return self.r['dph']*(time.time()-self.r['started'])/3600 if self.r else 0.
    def ssh(self,command,timeout=90,check=True):
        if not self.host or not self.port:raise RuntimeError('ssh address unavailable')
        return self.cmd(self.sshargs()+[command],timeout=timeout,check=check)
    def sshargs(self):
        return [self.sshbin,'-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','ConnectTimeout=15','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','-p',str(self.port),'root@'+self.host]
    def finish_instance(self,destroy):
        i=self.own()
        if i is None:self.log('ALREADY-GONE',id=self.r['id']);return 'gone'
        if destroy:
            receipt=self.g/'COPY-VERIFIED.json';manifest=self.g/'copy/COPY.sha256'
            if not receipt.exists() or not manifest.exists():raise RuntimeError('destroy refused: no verified copy')
            if json.loads(receipt.read_text())['manifest_sha256']!=sha(manifest):raise RuntimeError('destroy refused: manifest changed')
            for line in manifest.read_text().splitlines():
                expected,rel=line.split('  ',1)
                if sha(self.g/'copy'/rel)!=expected:raise RuntimeError('destroy refused: copied file changed')
        action='destroy' if destroy else 'stop'
        for attempt in range(3):
            self.cmd([self.vast,action,'instance',str(self.r['id'])],input=b'y\n',check=False)
            for poll in range(6):
                time.sleep(10)
                i=self.own()
                if i is None or (not destroy and i.get('actual_status') in ('exited','stopped')):
                    self.r.update(ended=time.time(),end_action=action,rental_dollars_estimate=round(self.spent(),6))
                    (self.g/'rental.json').write_text(json.dumps(self.r,indent=2)+'\n');self.log(action.upper()+'-CONFIRMED',id=self.r['id']);return action
        raise RuntimeError(action.upper()+'-UNCONFIRMED')
    def kill_owned_commands(self):
        # These PID files were written only by this job, inside its own rental.
        self.ssh("cd /root/lis320; for f in W/child.pid W/drive.pid; do if test -f \"$f\"; then p=$(cat \"$f\"); case \"$p\" in ''|*[!0-9]*) exit 9;; esac; kill -TERM \"$p\" 2>/dev/null || true; fi; done",check=False)
        time.sleep(5)
    def copy_back(self,complete):
        out=self.g/'copy';out.mkdir(exist_ok=True)
        # Quiescent snapshot. Results and adapter/merged files are all covered.
        command="cd /root/lis320 && mkdir -p W && find W drive.log -type f ! -name COPY.sha256 -print | LC_ALL=C sort | while IFS= read -r f; do sha256sum \"$f\"; done > COPY.sha256 && tar -cf - COPY.sha256 W drive.log"
        with (self.g/'copy-error.log').open('ab') as err:
            source=subprocess.Popen(self.sshargs()+[command],stdout=subprocess.PIPE,stderr=err,stdin=subprocess.DEVNULL)
            target=subprocess.Popen(['tar','-xf','-','-C',str(out)],stdin=source.stdout,stderr=err)
            source.stdout.close()
            try:
                target.wait(timeout=600);source.wait(timeout=30)
            except subprocess.TimeoutExpired:
                source.terminate();target.terminate();source.wait(timeout=30);target.wait(timeout=30);return False
        if source.returncode or target.returncode:return False
        manifest=out/'COPY.sha256'
        if not manifest.is_file() or not manifest.stat().st_size:return False
        count=0
        for line in manifest.read_text().splitlines():
            h,rel=line.split('  ',1);p=Path(rel)
            if p.is_absolute() or '..' in p.parts or len(h)!=64:return False
            if not (out/p).is_file() or sha(out/p)!=h:return False
            count+=1
        if complete:
            for f in ('train_summary.json','reads_panel_old.jsonl','reads_panel_new.jsonl','extra_old.json','extra_new.json','dev_score_new.txt','panel-old.completed','panel-new.completed'):
                if not (out/'W/results'/f).is_file():return False
            for kind in ('adapter','merged'):
                src=out/'W/model'/kind;dest=Path.home()/'premonition-models'/('lis320-'+kind)
                if not src.is_dir() or dest.exists():return False
                shutil.copytree(src,dest,copy_function=os.link)
                if any(sha(p)!=sha(dest/p.name) for p in src.iterdir() if p.is_file()):return False
        self.log('COPY-VERIFIED',files=count,complete=complete)
        (self.g/'COPY-VERIFIED.json').write_text(json.dumps(dict(files=count,complete=complete,manifest_sha256=sha(manifest),utc=utc()))+'\n')
        return True
    def export(self,outcome,lifecycle):
        dest=Path(self.a.repo)/A/'run-vast'
        dest.mkdir(parents=True,exist_ok=True)
        copied=self.g/'copy/W/results'
        if copied.exists():
            for p in copied.iterdir():
                if p.is_file():
                    q=dest/p.name
                    if q.exists():raise RuntimeError('export would overwrite existing result')
                    shutil.copyfile(p,q)
        for name in ('rental.json','events.jsonl','COPY-VERIFIED.json'):
            p=self.g/name
            if p.exists():shutil.copyfile(p,dest/('mac-'+name))
        # New ledger record: the user requires add-only changes to the repository.
        report=dict(utc=utc(),outcome=outcome,lifecycle=lifecycle,cap_usd=CAP,
                    rental=self.r,model_adapter=str(Path.home()/'premonition-models/lis320-adapter'),
                    model_merged=str(Path.home()/'premonition-models/lis320-merged'),
                    verdict='UNTESTED; R1-R7 and C1 await two fresh blind judges')
        (dest/'RENTAL-RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
        (self.g/'END.json').write_text(json.dumps(report,indent=2)+'\n')
    def release_gate(self):
        self.cmd(['git','-C',self.a.repo,'fetch','-q','origin','main'])
        path='handoff/queue/'+self.a.job+'.md'
        now=self.cmd(['git','-C',self.a.repo,'show','origin/main:'+path]).stdout
        pinned=self.cmd(['git','-C',self.a.repo,'show',self.a.pin+':'+path]).stdout
        if now!=pinned or b'STATUS: HELD' in now:raise RuntimeError('queue release changed or held')
    def main(self):
        if (self.g/'rental.json').exists() or (self.g/'STARTED').exists():raise RuntimeError('DUPLICATE: state already exists')
        with (self.g/'STARTED').open('x') as f:f.write(utc()+'\n')
        self.release_gate()
        for ref in ('origin/main','origin/builder-outbox'):
            for p in ('RESULTS.md','run-vast/RENTAL-RESULT.json'):
                if self.cmd(['git','-C',self.a.repo,'cat-file','-e',ref+':'+A+'/'+p],check=False).returncode==0:raise RuntimeError('DUPLICATE results')
        for name in ('DATA.md','SEAL-DATA.sha256.txt','SEAL-EXECUTION.sha256.txt','MOCK-TEST.json'):
            self.cmd(['git','-C',self.a.repo,'cat-file','-e',self.a.pin+':'+A+'/'+name])
        test=json.loads(self.cmd(['git','-C',self.a.repo,'show',self.a.pin+':'+A+'/MOCK-TEST.json']).stdout)
        if test.get('status')!='PASS':raise RuntimeError('MOCK-TEST not PASS')
        for path,want in test['tested_sha256'].items():
            content=self.cmd(['git','-C',self.a.repo,'show',self.a.pin+':'+path]).stdout
            if hashlib.sha256(content).hexdigest()!=want:raise RuntimeError('kit changed since mock test')
        for kind in ('adapter','merged'):
            if (Path.home()/'premonition-models'/('lis320-'+kind)).exists():raise RuntimeError('DUPLICATE existing lis320 model')
        old=Path.home()/'premonition-models/lis319f-merged'
        if sha(old/'model.safetensors')!=OLD_SHA:raise RuntimeError('OLD-READER-MISMATCH')
        if any(x.get('label')==LABEL for x in self.instances()):raise RuntimeError('DUPLICATE labelled rental')
        user=self.vastjson('show','user');self.log('CREDIT',credit=user.get('credit'))
        offers=self.vastjson('search','offers',QUERY,'-o','dph')
        if isinstance(offers,dict):offers=offers.get('offers',[])
        offers=[x for x in offers if x.get('gpu_name') in ('RTX_5090','RTX_4090','RTX 5090','RTX 4090') and 0<float(x.get('dph_total',0))<=MAX_DPH and float(x.get('reliability2',x.get('reliability',0)))>=.98 and int(x.get('gpu_ram',0))>=24000 and float(x.get('cpu_cores_effective',0))>=8]
        offers.sort(key=lambda x:float(x['dph_total'])/float(x.get('total_flops') or 1))
        if not offers:raise RuntimeError('NO-OFFER within registered fit')
        offer=offers[0];self.release_gate()
        start=time.time()
        created=self.vastjson('create','instance',str(offer['id']),'--image','pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime','--disk','60','--label',LABEL,'--ssh','--direct')
        if not created.get('success',True) or not created.get('new_contract'):raise RuntimeError('CREATE-FAILED; no retry')
        self.r=dict(id=int(created['new_contract']),label=LABEL,dph=float(offer['dph_total']),started=start,gpu=offer['gpu_name'],offer=offer['id'],pin=self.a.pin,outbox=self.a.outbox)
        (self.g/'rental.json').write_text(json.dumps(self.r,indent=2)+'\n');self.log('CREATED',**self.r)
        try:
            ready=False
            while time.time()-start<360:
                i=self.own()
                if i and i.get('actual_status')=='running' and i.get('ssh_host') and i.get('ssh_port'):
                    self.host=i['ssh_host'];self.port=int(i['ssh_port'])
                    if self.ssh('printf ssh-ok',timeout=30,check=False).stdout==b'ssh-ok':ready=True;break
                time.sleep(10)
            if not ready:raise RuntimeError('START-STOP: no ready SSH within six minutes')
            self.ssh('mkdir -p /root/lis320/W /root/lis320/old/lis319f-merged')
            paths=['scripts',A,'artifacts/claude-readpanel320-20260926','handoff/kit/lis320v']
            # Stream from pinned commits; no complete repository tarball is staged on the Mac.
            self.stream(['git','-C',self.a.repo,'archive',self.a.pin,*paths],'tar -xf - -C /root/lis320')
            counts=json.loads(self.cmd(['git','-C',self.a.repo,'show',self.a.pin+':'+A+'/full-luna/final/COUNTS.json']).stdout)
            chunks=[A+f'/full-luna/chunk{x["chunk"]}' for x in counts['chunks']]
            self.stream(['git','-C',self.a.repo,'archive',self.a.outbox,*chunks],'tar -xf - -C /root/lis320')
            self.stream(['tar','-cf','-','-C',str(old),'.'],'tar -xf - -C /root/lis320/old/lis319f-merged')
            self.ssh("cd /root/lis320 && nohup python3 -B handoff/kit/lis320v/box/drive.py > drive.log 2>&1 < /dev/null &")
            # Exact drive PID is recorded by the remote driver, not discovered by process-name kill.
            last_size=None;last_growth=time.time();phase='START';outcome='UNKNOWN'
            while True:
                if self.spent()>=STOP:raise RuntimeError('BUDGET-STOP at reserve threshold')
                reply=self.ssh("cd /root/lis320 && python3 -c 'import json,pathlib; w=pathlib.Path(\"W\"); s=json.loads((w/\"state.json\").read_text()) if (w/\"state.json\").exists() else {}; print(json.dumps(dict(state=s,bytes=sum(p.stat().st_size for p in w.rglob(\"*\") if p.is_file()))))'",timeout=60)
                status=json.loads(reply.stdout);phase=status['state'].get('phase','START')
                if phase=='DONE':outcome='DONE';break
                if phase=='FAILED':raise RuntimeError('REMOTE-FAILED: '+status['state'].get('reason','unknown'))
                size=status['bytes']
                if size!=last_size:last_growth=time.time();last_size=size
                if time.time()-last_growth>600:raise RuntimeError('STALL: no output growth for ten minutes')
                time.sleep(30)
            verified=self.copy_back(True)
            lifecycle=self.finish_instance(verified)
            self.export(outcome if verified else 'COPY-FAILED',lifecycle)
        except Exception as e:
            reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__
            self.log('STOP',reason=reason)
            try:self.kill_owned_commands()
            except Exception:pass
            try:verified=self.copy_back(False)
            except Exception:verified=False
            try:lifecycle=self.finish_instance(verified)
            except Exception:lifecycle='UNCONFIRMED'
            self.export(reason,lifecycle)
    def stream(self,source,remote):
        with (self.g/'stream-error.log').open('ab') as err:
            p=subprocess.Popen(source,stdout=subprocess.PIPE,stderr=err)
            q=subprocess.Popen(self.sshargs()+[remote],stdin=p.stdout,stdout=subprocess.DEVNULL,stderr=err)
            p.stdout.close()
            try:q.wait(timeout=600);p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                p.terminate();q.terminate();p.wait(timeout=30);q.wait(timeout=30);raise RuntimeError('STREAM-TIMEOUT')
            if p.returncode or q.returncode:raise RuntimeError('STREAM-FAILED')
def main():
    ap=argparse.ArgumentParser()
    for name in ('repo','pin','outbox','job','state'):ap.add_argument('--'+name,required=True)
    a=ap.parse_args();r=Runner(a)
    try:r.main()
    except Exception as e:
        r.log('PRE-RENT-STOP',reason=str(e) if isinstance(e,RuntimeError) else type(e).__name__)
        raise SystemExit(1)
if __name__=='__main__':main()
