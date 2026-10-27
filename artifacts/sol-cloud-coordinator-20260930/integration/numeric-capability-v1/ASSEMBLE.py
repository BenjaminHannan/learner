#!/usr/bin/env python3
"""Assemble an immutable small source packet; never launch a model or queue."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OWN=Path(__file__).resolve().parent

def pin(path):
    path=Path(path);data=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def write_new(path,value):
    data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('existing assembly differs; new revision required')
    else:
        with path.open('xb') as f:f.write(data)
    return pin(path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--seal',type=Path,required=True);p.add_argument('--seal-sha256',required=True)
    p.add_argument('--review',type=Path,required=True);p.add_argument('--review-sha256',required=True)
    p.add_argument('--revision',required=True);args=p.parse_args()
    seal_path=(ROOT/args.seal).resolve();review_path=(ROOT/args.review).resolve()
    if pin(seal_path)['sha256']!=args.seal_sha256 or pin(review_path)['sha256']!=args.review_sha256:raise ValueError('frozen source/review pin differs')
    seal=json.loads(seal_path.read_bytes());review=json.loads(review_path.read_bytes())
    if review.get('release_readiness') is not True or review.get('seal_sha256')!=args.seal_sha256:raise ValueError('exact source review release not ready')
    plan_path=ROOT/'artifacts/sol-cloud-numeric-fit-20260930'/('PLAN-'+args.revision+'.json')
    if not plan_path.exists():raise ValueError('exact final plan revision absent')
    plan_pin=pin(plan_path)
    if seal['plan_sha256']!=plan_pin['sha256'] or seal['files'].get(plan_pin['path'])!=plan_pin['sha256']:raise ValueError('plan not bound to source seal')
    package_dir=OWN/args.revision;package_dir.mkdir(exist_ok=True)
    release=write_new(package_dir/'RELEASE.json',{'authorized_by':'Derek','fit_released':True,'seal_sha256':args.seal_sha256,
        'independent_review':{k:pin(review_path)[k] for k in ('path','sha256')},
        'authorization_basis':'Explicit parent conditional four serial numeric fits; exact rows/source review and actual runtime resource gates required',
        'sleep_enabled':False,'activation_allowed':False,'updates_per_arm':800,'seeds':[0,1],'arms':['loop','plain']})
    paths=set(seal['files'])|{pin(seal_path)['path'],pin(review_path)['path'],release['path']}
    files=[]
    for path in sorted(paths):
        if '\\' in path or ':' in path or '..' in Path(path).parts or Path(path).is_absolute():raise ValueError('contained relative source required')
        record=pin(ROOT/path)
        if path in seal['files'] and record['sha256']!=seal['files'][path]:raise ValueError('sealed source changed: '+path)
        files.append(record)
    if sum(r['bytes'] for r in files)>8*1024**2:raise ValueError('included source packet exceeds8MiB')
    package={'schema':'sol.cloud.numeric-fit.source-package.v1','pc_root':'C:/Users/benja/sol-cloud-numeric-capability-v1',
        'plan':{k:plan_pin[k] for k in ('path','sha256')},'seal':{k:pin(seal_path)[k] for k in ('path','sha256')},
        'release':{k:release[k] for k in ('path','sha256')},'files':files,'model_calls':0,'optimizer_updates':0,
        'checkpoint_bytes_in_payload':0,'LM_weights_in_payload':False,'actual_user_day':False,'activated':False}
    frozen=write_new(package_dir/'PACKAGE.json',package)
    print(json.dumps({'package':frozen,'release':release,'source_files':len(files),'source_bytes':sum(r['bytes'] for r in files),'no_launch':True},sort_keys=True))

if __name__=='__main__':main()
