#!/usr/bin/env python3
"""Freeze CLOSED V6 tuple against final transport AND stdout hashes. No inference."""
import argparse,json
from pathlib import Path
from sol_assistant_bundle import ROOT,owned,sha,pin,verify_pin,save_new,pack,verify_bundle,Unavailable

def freeze(run,seed,stdout,model,out):
    run=Path(run).resolve();out=owned(out)
    transport=run/'TRANSPORT-RESULT.json';tr=json.loads(transport.read_text())
    if tr['returncode']!=0 or tr['seed']!=seed or tr['sleep_updates']!=0:raise Unavailable('source job did not close cleanly')
    hashes={k.replace('\\','/'):v for k,v in tr['paths_and_hashes'].items()}
    ledger=run/f'grounding-s{seed}.json';l=json.loads(ledger.read_text())
    if l['updates']!=500 or l['parent_frozen'] is not True or l['raw_watermark_update']!=500:
        raise Unavailable('requires closed500 exact snapshot; no rolling first-update assumption')
    roles={'parent':f'parent-s{seed}.pt','reader':f'input-s{seed}.pt','adapter':f'bootstrap-English-s{seed}.pt','resume':f'resume-s{seed}.pt','ledger':f'grounding-s{seed}.json','lm_provenance':'LFM-provenance.json'}
    before={}
    for role,name in roles.items():
        p=run/name;key=p.relative_to(ROOT).as_posix()
        if key not in hashes or sha(p)!=hashes[key]:raise Unavailable('final transport mismatch: '+name)
        before[role]=pin(p)
    log=Path(stdout);logpin=pin(log);receipts=[]
    for line in log.read_text().splitlines():
        try:r=json.loads(line)
        except ValueError:continue
        if r.get('status')=='DURABLE-TRAIN-WEIGHTS' and r.get('seed')==seed:receipts.append(r)
    if not receipts:raise Unavailable('missing stdout DURABLE')
    receipt=receipts[-1]
    if receipt['updates']!=500 or receipt['resume_sha256']!=before['resume']['sha256']:
        raise Unavailable('final stdout receipt and final transport mismatch')
    evidence=owned(str(out)+'-evidence');evidence.mkdir(parents=True,exist_ok=False)
    save_new(evidence/'durable-receipt.json',receipt)
    save_new(evidence/'transport.json',tr)
    with (evidence/'stdout.log').open('xb') as f:f.write(log.read_bytes())
    verify_pin(logpin)
    req={k+'_path':v['path'] for k,v in before.items()}
    req.update(training_seal_path=str(ROOT/'artifacts/sol-translator-20260929/DEPLOYMENT-V6-SEAL.json'),durable_receipt_path=str(evidence/'durable-receipt.json'),lm_path=str(Path(model).resolve()))
    save_new(evidence/'request.json',req)
    bundle=pack(evidence/'request.json',out)
    for record in before.values():verify_pin(record)
    b=verify_bundle(bundle)
    result=dict(status='FROZEN-DIAGNOSTIC',bundle=str(bundle),version=b['version'],seed=seed,updates=500,resume_sha256=before['resume']['sha256'],source_transport=pin(transport),stdout=pin(evidence/'stdout.log'),no_model_loaded=True,optimizer_steps=0,sleep_ready=False,semantic_English='NOT SHOWN')
    save_new(out/'freeze-receipt.json',result);print(json.dumps(result));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--seed',type=int,choices=(0,1),required=True);p.add_argument('--stdout',required=True);p.add_argument('--model',required=True);p.add_argument('--out',required=True);a=p.parse_args();freeze(a.run,a.seed,a.stdout,a.model,a.out)
