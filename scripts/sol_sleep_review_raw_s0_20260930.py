#!/usr/bin/env python3
"""Independent stdlib-only recount; explicit seven-file read allowlist, no models."""
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'artifacts/sol-compose-20260929/ordered-night-v2'
RUN = BASE / 'collected-s0/artifacts/sol-compose-20260929/ordered-night-v2/run-s0'
PATHS = {'plan':BASE/'PLAN.json', 'binding':BASE/'BINDING-s0.json',
         **{k:RUN/v for k,v in {'before':'guard-before.json','repeat':'guard-before-repeat.json',
            'after':'guard-after.json','ledger':'night-ledger.json','raw':'night-raw.jsonl'}.items()}}

def main():
    blobs = {k:p.read_bytes() for k,p in PATHS.items()}
    hashes = {k:hashlib.sha256(v).hexdigest() for k,v in blobs.items()}
    d = {k:json.loads(v) for k,v in blobs.items() if k != 'raw'}
    raw = [json.loads(line) for line in blobs['raw'].splitlines()]
    plan,binding,ledger = d['plan'],d['binding'],d['ledger']
    if ledger.get('closed') is not True:
        raise RuntimeError('not closed: no recount')
    checks = []
    def check(name, value): checks.append({'check':name,'pass':bool(value)})
    check('plan digest equals binding pin',hashes['plan']==binding['plan_sha256'])
    check('binding pins reviewed 1b011 source', binding['driver_sha256']=='1b011c35408b2db968d44c215c90818e6244563b5406e37983cd30c1f8bfbb2b')
    check('ledger binds exact BINDING bytes', ledger['source_binding_sha256']==hashes['binding'])
    check('versions/seed match', all(x['version']=='sol-ordered-night-v2' for x in (plan,binding,ledger)) and ledger['seed']==0)
    check('presealed budget', plan['updates']==25 and plan['batch']==2 and plan['fixed_rounds']==4 and plan['context_cap']==512)
    groups = [plan[k+'_ids'] for k in ('experience','replay','guard')]
    check('unique disjoint 16/32/8 roster',list(map(len,groups))==[16,32,8] and len(set(sum(groups,[])))==56)
    check('static experience/replay ledger equals plan',ledger['experience_ids']==groups[0] and ledger['replay_ids']==groups[1])
    check('static replay declared, no day claim',ledger['actual_day_experience'] is False and ledger['day_batch_sha256'] is None)
    check('25 ledger updates and raw watermark', ledger['updates']==25 and ledger['raw_watermark_update']==25)
    check('50 rows, exactly two for each update 1..25',len(raw)==50 and Counter(r['update'] for r in raw)=={i:2 for i in range(1,26)})
    check('raw ordered by update pairs',[r['update'] for r in raw]==[i for i in range(1,26) for _ in range(2)])
    rng=random.Random(2026093010)
    expected=[rng.choice(group) for _ in range(25) for group in groups[:2]]
    check('sampled IDs equal reviewed deterministic experience/replay schedule',[r['id'] for r in raw]==expected)
    check('raw origin tags all human-verbatim',all(r['origin']=='verified-human-origin-verbatim' for r in raw))
    source_pins=set(binding['dependency_pins'].values())
    allrows=raw+d['before']+d['repeat']+d['after']
    def valid_row(r):
        if len(r['labels'])!=1 or len(r['label_mask'])!=1:return False
        labels,mask=r['labels'][0],r['label_mask'][0]
        if not (0<len(labels)<=64 and len(labels)==len(mask) and any(mask)):return False
        if any(type(x) is not int or type(m) is not bool or m!=(x!=-100) for x,m in zip(labels,mask)):return False
        if any(x<0 and x!=-100 for x in labels):return False
        if type(r['eos_token_id']) is not int:return False
        if [x for x,m in zip(labels,mask) if m][-1]!=r['eos_token_id']:return False
        for ik,mk,cap in [('input_ids','input_mask',49),('notebook_ids','notebook_mask',512)]:
            ids,masks=r[ik],r[mk]
            if len(ids)!=1 or len(masks)!=1 or not (0<len(ids[0])<=cap) or len(ids[0])!=len(masks[0]):return False
            if any(type(x) is not int or x<0 for x in ids[0]) or any(type(m) is not bool for m in masks[0]):return False
            if not all(masks[0]):return False
        account={k:r[k] for k in ('input_ids','input_mask','notebook_ids','notebook_mask')}
        identity=hashlib.sha256(json.dumps(account,sort_keys=True).encode()).hexdigest()
        return (identity==r['input_identity_sha256'] and math.isfinite(r['CE']) and r['CE']>=0
                and r['binding_sha256']==hashes['binding'] and r['source_sha256'] in source_pins and r['round']==4)
    valid_count=sum(valid_row(r) for r in allrows)
    check('all 74 rows valid numeric structure/masks/target EOS/hash/binding/source tag',valid_count==74)
    stable_keys=('labels','label_mask','eos_token_id','input_ids','input_mask','notebook_ids','notebook_mask','input_identity_sha256','source_sha256','binding_sha256')
    identities={}
    consistent=True
    for r in allrows:
        values={k:r[k] for k in stable_keys}
        if r['id'] in identities and identities[r['id']]!=values:consistent=False
        identities[r['id']]=values
    check('same ID always has identical inputs/targets/masks/source',consistent)
    for phase in ('before','repeat','after'):
        check(phase+' exact ordered eight guard IDs',[r['id'] for r in d[phase]]==groups[2])
        check(phase+' generated IDs valid',all(isinstance(r['generated_ids'],list) and len(r['generated_ids'])<=64 and all(type(x) is int and x>=0 for x in r['generated_ids']) for r in d[phase]))
    def exact(r):
        target=[x for x,m in zip(r['labels'][0],r['label_mask'][0]) if m]
        if target and target[-1]==r['eos_token_id']:target=target[:-1]
        return r['generated_ids']==target
    means={k:sum(r['CE'] for r in d[k])/len(d[k]) for k in ('before','repeat','after')}
    noise=abs(means['repeat']-means['before']);tol=2*noise+1e-6
    lost=[a['id'] for a,b in zip(d['before'],d['after']) if exact(a) and not exact(b)]
    ce_pass=means['after']<=means['before']+tol
    counts={k:sum(exact(r) for r in d[k]) for k in ('before','repeat','after')}
    check('ledger repeat noise equals independent recount',ledger['repeat_CE_noise_measured']==noise)
    check('before/repeat CE and generated IDs exactly repeated',all(a['CE']==b['CE'] and a['generated_ids']==b['generated_ids'] for a,b in zip(d['before'],d['repeat'])))
    check('raw training IDs exclude guard roster',not (set(r['id'] for r in raw)&set(groups[2])))
    check('authorized files unchanged during recount',all(p.read_bytes()==blobs[k] for k,p in PATHS.items()))
    report={
      'command':'python3 -B scripts/sol_sleep_review_raw_s0_20260930.py',
      'evidence_files':{k:{'path':str(PATHS[k]),'sha256':hashes[k]} for k in PATHS},
      'checks':checks,'structural_failures':[x['check'] for x in checks if not x['pass']],
      'raw_updates':25,'raw_rows':len(raw),'valid_numeric_rows':valid_count,
      'distinct_experience_IDs':len(set(r['id'] for r in raw)&set(groups[0])),
      'distinct_replay_IDs':len(set(r['id'] for r in raw)&set(groups[1])),
      'guard_recount':{'mean_CE':means,'repeat_noise':noise,'tolerance':tol,'mean_CE_pass':ce_pass,
                       'exact_sentence_counts_out_of_8':counts,'lost_prior_exact_IDs':lost,
                       'predicate_pass':ce_pass and not lost},
      'ledger_claims_not_checkpoint_verified':{k:ledger[k] for k in ('closed','updates','core_before','core_after','populated_Adam_states','checkpoint_reload_exact','populated_Adam_reload_exact','optimizer_scope','execution_policy','model_authored_targets','DEV_model_calls','learned_stop_qualified')},
      'ledger_core_fingerprints_differ':ledger['core_before']!=ledger['core_after'],
      'limitations':[
        'Raw files independently support a complete 25-by-2 update log and the recounted guard predicate; logs alone do not independently prove optimizer execution or durable changed weights.',
        'Changed core, 90 populated Adam states and reload flags are ledger claims only until actual checkpoint/optimizer verification; no checkpoint opened.',
        'CE values are saved measurements, not recomputed loss. Generated IDs are recounted, not regenerated. Targets compared numerically across records, not against corpus/tokenizer.',
        'Binding/plan digests and raw linkage checked; Windows dependency paths, actual awake tuple bytes, source bytes and all external dependency files not opened or independently verified here. Pre-run sealing time not independently established.',
        'Only seven authorized files read; no decision.json, candidate manifest, author result narratives, corpus/mixed manifests, model files, inference, rescore or training.',
        'Static HUMAN TRAIN replay only; actual_day_experience=false. No day-learning fulfillment, seed1 result, scientific improvement, learned-stop qualification or activation approval.',
        'Changed-candidate native fixed4 safety, unchanged frozen components/prefix rebinding, complete bundle and pointer activation/rollback remain separate verification.'
      ]}
    output=ROOT/'artifacts/sol-sleep-review-20260930/actual-raw-s0-recount.json'
    with output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','evidence_files','limitations','ledger_claims_not_checkpoint_verified')},indent=2))
    print('checks',sum(c['pass'] for c in checks),'of',len(checks),'report',output)

if __name__=='__main__':main()
