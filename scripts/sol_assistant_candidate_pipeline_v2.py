#!/usr/bin/env python3
"""Actual guarded night candidate → fresh native receipt → day-only full bundle.
Invoke from existing watcher pipeline. Static-cycle receipt is allowed, but it
cannot create an activation ticket through the day-learning branch.
"""
import argparse,importlib.util,json,os,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from sol_assistant_bundle import ROOT,owned,pin,verify_pin,sha,save_new,Unavailable
from sol_assistant_ordered_bundle_v10 import verify
CHECKER_SHA='1b011c35408b2db968d44c215c90818e6244563b5406e37983cd30c1f8bfbb2b'
PACKAGE_SHA='0b02eacfb4dd94a75876fb1c32dc6b2eb2ec40d5409b485aa4050ea960125c5f'
SOURCE_PINS={'scripts/sol_sleep_ordered_v2.py':CHECKER_SHA,'scripts/sol_stop_ordered_receipt_bind_v1.py':'a03c3122202340fa06eeb474551dce5435878557110cab94d5ae057efddb04d2','scripts/sol_stop_ordered_checkpoint_receipt_v1.py':'07da043fe3001d1f3027d7d2e114e42a12814c9995ab6d62c9514335020bf3a9'}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def run(a):
    if not os.environ.get('JOB') or Path(os.environ.get('TREE','')).resolve()!=ROOT.resolve():raise Unavailable('existing watcher JOB/TREE required')
    for path,digest in SOURCE_PINS.items():verify_pin({'path':str(ROOT/path),'sha256':digest})
    if sha(a.package)!=PACKAGE_SHA:raise Unavailable('native receipt source package differs')
    previous=pin(a.previous_bundle);verify(previous['path']);manifest=pin(a.candidate_manifest);m=read(manifest['path']);decision=pin(a.decision);d=read(decision['path'])
    if Path(d['candidate_manifest']).resolve()!=Path(manifest['path']).resolve():raise Unavailable('decision is for a different candidate')
    checker=ROOT/'scripts/sol_sleep_ordered_v2.py'
    spec=importlib.util.spec_from_file_location('_actual_night_check_v2',checker);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if module.check_decision(decision['path'],previous['sha256'],manifest['sha256']) is not True:raise Unavailable('candidate guard rejected; retain prior bundle')
    out=owned(a.out);out.mkdir(parents=True,exist_ok=False)
    receipt_root=Path(a.receipt_out).resolve()
    allowed=(ROOT/'artifacts/sol-stop-20260929/ordered-checkpoint-receipt-v1').resolve()
    if not receipt_root.is_relative_to(allowed) or receipt_root==allowed or receipt_root.exists():raise Unavailable('fresh native owner receipt subdirectory required')
    roles={role:{key:m[role][key] for key in ('path','sha256')} for role in ('parent','reader','prefix','provenance')}
    for item in roles.values():verify_pin(item)
    tuple_path=out/'candidate-fourroles.json';save_new(tuple_path,roles)
    # Isolated subprocess is essential: owner writer inventories every imported repo
    # module, so importing it into this assistant process would violate its closure.
    binding=receipt_root/'binding.json';result=receipt_root/'actual'
    commands=[
        [sys.executable,'-X','utf8','-B',str(ROOT/'scripts/sol_stop_ordered_receipt_bind_v1.py'),'--package',str(a.package),'--tuple',str(tuple_path),'--out',str(binding)],
        [sys.executable,'-X','utf8','-B',str(ROOT/'scripts/sol_stop_ordered_checkpoint_receipt_v1.py'),'--spec',str(binding),'--out',str(result),'--device','cpu']]
    for index,command in enumerate(commands):
        with (out/f'native-step-{index}.log').open('x',encoding='utf-8') as log:
            child=subprocess.run(command,cwd=ROOT,env=dict(os.environ,PYTHONUTF8='1'),stdout=log,stderr=subprocess.STDOUT,timeout=300)
        if child.returncode:raise Unavailable('fresh candidate receipt failed; prior bundle retained')
    receipt=pin(result/'receipt.json');r=read(receipt['path'])
    for role,item in roles.items():
        if r[role+'_sha256']!=item['sha256']:raise Unavailable('fresh receipt tuple mismatch')
    ledger=read(d['ledger']);status={'candidate_manifest':manifest,'decision':decision,'previous_bundle':previous,'native_receipt':receipt,'actual_day_experience':ledger.get('actual_day_experience') is True,'activated':False}
    if status['actual_day_experience']:
        from sol_assistant_postnight_v2 import prepare,attach
        from sol_assistant_night_bundle_v2 import build
        prep=prepare(SimpleNamespace(previous_bundle=previous['path'],checker=str(checker),checker_sha256=CHECKER_SHA,decision=decision['path'],out=str(out/'prepared')))
        request=out/'bundle-request.json'
        attach(SimpleNamespace(preparation=prep['receipt'],safety_receipt=receipt['path'],out=str(request)))
        bundle=build(request,out/'candidate-bundle')
        ticket={'candidate_bundle':pin(bundle),'decision':decision,'previous_bundle':previous,'native_receipt':receipt,'day_batch_sha256':ledger['day_batch_sha256'],'candidate_manifest':manifest}
        save_new(out/'activation-ticket.json',ticket);status['activation_ticket']=pin(out/'activation-ticket.json')
    else:status['day_learning_status']='NOT FULFILLED: static engineering cycle; no day activation ticket'
    save_new(out/'pipeline-receipt.json',status);return status
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for field in ('candidate-manifest','decision','previous-bundle','package','out','receipt-out'):p.add_argument('--'+field,required=True)
    a=p.parse_args();print(json.dumps(run(a),indent=2))
