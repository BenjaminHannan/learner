#!/usr/bin/env python3
"""PC watcher transport target. TRAIN only, bound time, durable checkpoints."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tarfile,time
from pathlib import Path


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()


def run(a):
    root=Path(a.root).resolve();own=root/'artifacts/sol-translator-20260929'
    manifest=json.loads((root/'package.json').read_text())
    assert digest(root/'payload.tar.gz')==manifest['sha256'],'PACKAGE HASH'
    assert shutil.disk_usage(root).free>=2*1024**3,'DISK FLOOR2GiB'
    with tarfile.open(root/'payload.tar.gz') as archive:
        for member in archive.getmembers():
            assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts,'UNSAFE PACKAGE'
        archive.extractall(root)
    os.chdir(root)
    seal=json.loads((own/'DEPLOYMENT-V6-SEAL.json').read_text())
    for path,expected in seal['files'].items():assert digest(root/path)==expected,'PIN MISMATCH '+path
    work=own/f'ground-v6-s{a.seed}';work.mkdir(exist_ok=True)
    receipt=work/'LAUNCH.json'
    if receipt.exists() and not a.resume:raise ValueError('duplicate TRAIN launch; explicit resume and NEW watcher job required')
    env=dict(os.environ,PYTHONPATH=str(root)+os.pathsep+str(root/'scripts'),JOB=a.job,TREE=str(root),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUTF8='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
    start=time.monotonic();lm='C:/Users/benja/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b'
    receipt.write_text(json.dumps({'job':a.job,'seed':a.seed,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'stage':'TRAIN','package_sha256':manifest['sha256'],'seal_sha256':digest(own/'DEPLOYMENT-V6-SEAL.json'),'resume':a.resume,'no_dev_scoring':True,'precision_policy':'full frozen FP32 LFM including embedding/head; reader/core FP32; actual tensor dtypes/VRAM recorded'})+'\n')
    print(receipt.read_text(),flush=True)
    rc=1
    try:
        subprocess.run([sys.executable,'-B','scripts/sol_translator_pc_preflight_v6.py','--model',lm,'--source',str(own/f'seed-sources/qualified-source-s{a.seed}.pt'),'--seed',str(a.seed),'--out',str(work),'--device','cuda'],check=True,env=env,timeout=350)
        assert shutil.disk_usage(root).free>=2*1024**3,'DISK FLOOR before TRAIN'
        command=[sys.executable,'-B','scripts/sol_translator_grounding_v6.py','--model',lm,'--model-provenance',str(work/'LFM-provenance.json'),'--seed',str(a.seed),'--source',str(own/f'seed-sources/qualified-source-s{a.seed}.pt'),'--out',str(work),'--device','cuda']
        if a.resume:command+=['--resume',str(work/f'resume-s{a.seed}.pt')]
        proc=subprocess.Popen(command,env=env)
        try:rc=proc.wait(timeout=3200)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:rc=proc.wait(timeout=90)
            except subprocess.TimeoutExpired:proc.kill();rc=proc.wait()
        if sum(p.stat().st_size for p in own.glob('ground-v6-s*/*') if p.is_file())>512*1024**2:raise RuntimeError('NEW output disk allowance exceeded')
    finally:
        record={'returncode':rc,'seed':a.seed,'wall_seconds':time.monotonic()-start,'paths_and_hashes':{str(p.relative_to(root)):digest(p) for p in work.glob('*') if p.is_file()},'stage':'TRAIN only; no DEV scored','first_weight_estimate':'use measured DURABLE-TRAIN-WEIGHTS stdout; no speculative success','sleep_updates':0}
        (work/'TRANSPORT-RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
        with tarfile.open(root/f'raw-s{a.seed}.tar.gz','w:gz') as archive:
            for p in work.rglob('*'):
                if p.is_file() and p.suffix not in ('.pt','.tmp'):archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
        print(json.dumps(record),flush=True)
    return rc


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--seed',required=True,type=int,choices=(0,1));p.add_argument('--job',required=True);p.add_argument('--resume',action='store_true');sys.exit(run(p.parse_args()))
