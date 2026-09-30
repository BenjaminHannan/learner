"""Awake-only successor. Does NOT call sleep, create idle markers, or train English.

Original sol_compose_run.py and SPEC.json remain unchanged as draft history.
Only watcher queue may invoke run. Contract mode never creates an optimizer.
Shared fixed dev pools across seeds remove varying-query-pool confound, but
TWO seeds still give a diagnostic span, NOT statistical proof or a final claim.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import signal
import time
import torch
from sol_compose_data import build_pools, Dataset
from sol_compose_model import ARMS, ROUNDS, build_model, parameter_counts
from sol_compose_notebook import NotebookStore
from sol_compose_run import train_steps, ensure_budget, write_json, digest, utc, score, load_checkpoint, _signal

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/sol-compose-20260929'


def check_seal():
    seal=json.loads((ART/'SEAL-AWAKE.json').read_text())
    for path,sha in seal['sha256'].items():
        if digest(ROOT/path)!=sha:raise RuntimeError(f'awake seal mismatch: {path}')
    return seal


def prepare(spec):
    pools={seed:build_pools(seed,spec['train_n'],spec['dev_n']) for seed in spec['seeds']}
    return {str(seed):{key:value.audit for key,value in pool.items()} for seed,pool in pools.items()}


def local_noise(results,spec):
    noise={}
    for split in ('dev_structure','dev_order'):
        spans={arm:abs(results[f'{arm}-s0'][split]['exact']-results[f'{arm}-s1'][split]['exact'])*100/spec['dev_n']
               for arm in ARMS if arm!='compose'}
        largest=max(spans.values())
        noise[split]=dict(control_seed_spans_pp=spans,measured_diagnostic_span_pp=largest,
                         screen_bar_pp=max(10.,2*largest+1.),same_query_pool_both_seeds=True,
                         provenance='saved control predictions, seeds0/1, shared fixed dev query pool seed0',
                         insufficient_for_statistical_proof=True,
                         caveat='two initializations with differing TRAIN pools; not an SE or confidence interval')
    return noise


def readiness(raw,sha):
    x=raw['TRAIN_retention'];loss=x['fixed_exact']-x['exact']
    ready=(x['exact']>=90 and loss<=2 and x['mean_rounds']<=4.5 and x['cap_hits']<=10)
    return dict(checkpoint_sha256=sha,split='TRAIN_retention',n=100,
                learned_stop_exact=x['exact'],fixed_exact=x['fixed_exact'],stop_loss_count=loss,
                mean_rounds=x['mean_rounds'],cap_hits=x['cap_hits'],
                frozen_marks=dict(exact_min=90,stop_loss_max=2,mean_rounds_max=4.5,cap_hits_max=10),
                ready_for_SEPARATE_stop_review=ready,authorizes_sleep=False,
                independent_stop_audit_required=True)


def summarize(results,noise,spec,checkpoints):
    rows=[];stops={}
    for seed in spec['seeds']:
        for arm in ARMS:
            key=f'{arm}-s{seed}'
            stops[key]=readiness(results[key],checkpoints[key]['sha256'])
        for split in ('dev_structure','dev_order'):
            candidate=results[f'compose-s{seed}'][split]
            controls={arm:results[f'{arm}-s{seed}'][split]['exact'] for arm in ARMS if arm!='compose'}
            gap=(candidate['exact']-max(controls.values()))*100/spec['dev_n']
            bar=noise[split]['screen_bar_pp']
            rows.append(dict(seed=seed,split=split,candidate=candidate['exact'],n=spec['dev_n'],
                             controls=controls,gap_pp=gap,screen_bar_pp=bar,
                             screen_met=(candidate['exact']>=160 and gap>=bar and
                                         candidate['fixed_exact']-candidate['exact']<=4)))
    return dict(scope='AWAKE TRAIN/dev diagnostic only',rows=rows,stop_readiness=stops,
                decision='SCREEN MET; NEEDS INDEPENDENT RECOUNT' if all(x['screen_met'] for x in rows)
                         else 'SCREEN NOT MET; DIAGNOSE WITHOUT PROMOTION',
                statistical_claim='INSUFFICIENT: two-seed diagnostic span only',
                sleep_updates=0,sleep_authorized=False,holdout_opened=False,
                english_proven=False,general_reasoner_proven=False,F_eq='NOT EVALUATED',F_few='NOT EVALUATED')


def run(args):
    if os.environ.get('SOL_COMPOSE_QUEUE_JOB')!='sol-compose-awake-20260929':
        raise RuntimeError('watcher queue only; no direct training')
    seal=check_seal();spec=json.loads((ART/'SPEC-AWAKE.json').read_text())
    workdir=args.workdir.resolve();workdir.mkdir(parents=True,exist_ok=True)
    if (workdir/'sol_compose_awake_STARTED.json').exists():raise RuntimeError('duplicate/partial run refused')
    ensure_budget(time.monotonic(),spec,workdir)
    if args.device=='cuda':
        if not torch.cuda.is_available():raise RuntimeError('NO CUDA; no fallback')
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.set_num_threads(2);signal.signal(signal.SIGTERM,_signal);signal.signal(signal.SIGINT,_signal)
    started=time.monotonic()
    write_json(workdir/'sol_compose_awake_STARTED.json',dict(utc=utc(),device=args.device,torch=torch.__version__,seal=seal))
    audits=prepare(spec);write_json(workdir/'sol_compose_awake_DATA.json',audits)
    records={};checkpoints={}
    for seed in spec['seeds']:
        pools=build_pools(seed,spec['train_n'],spec['dev_n'])
        store=NotebookStore(workdir/f'sol_compose_awake_notebook_s{seed}.jsonl')
        for split in ('TRAIN','TRAIN_primitives'):
            for token in pools[split].inputs.tokens:
                facts=token[token[:,0]==120].tolist()
                store.append(json.dumps(facts,separators=(',',':')).encode(),origin='symbolic_code',
                             source_ref=f'{split}:seed:{pools[split].audit["seed"]}',
                             origin_evidence=f'generator SHA256 {digest(ROOT/"scripts/sol_compose_data.py")}')
        notebook_sha=digest(store.path)
        for arm in ARMS:
            ensure_budget(started,spec,workdir)
            torch.manual_seed(spec['initialization_base']+seed)
            model=build_model(arm).to(args.device)
            if args.device=='cuda':torch.cuda.reset_peak_memory_stats()
            opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=0.)
            before=time.monotonic();key=f'{arm}-s{seed}'
            record=train_steps(model,opt,pools['TRAIN'],primitive_pool=pools['TRAIN_primitives'],
                               steps=spec['practice_updates'],batch=32,seed=907000+seed,
                               device=args.device,started=started,spec=spec,workdir=workdir)
            record.update(seed=seed,arm=arm,counts=parameter_counts(model),seconds=time.monotonic()-before,
                          cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated() if args.device=='cuda' else None,
                          sleep_updates=0,checkpoint_selection='fixed final update; no dev scores read')
            path=workdir/f'sol_compose_awake_{key}.pt'
            torch.save(dict(schema='sol_compose.joined.v1',arm=arm,seed=seed,phase='awake_only',
                            model=model.cpu().state_dict(),notebook_sha256=notebook_sha,
                            spec_sha256=digest(ART/'SPEC-AWAKE.json'),
                            config=dict(round_cap=6,latent_width=64,top_k=2,experts=4)),path)
            checkpoints[key]=dict(path=path.name,sha256=digest(path));records[key]=record
            write_json(workdir/f'sol_compose_awake_{key}_training.json',record)
            print(json.dumps(dict(utc=utc(),completed=key,seconds=record['seconds'],sleep_updates=0)),flush=True)
            del opt,model;gc.collect()
    write_json(workdir/'sol_compose_awake_CHECKPOINT-SEAL.json',checkpoints)
    results={}
    # Identical dev pools for both initializations. Never select a checkpoint.
    dev=build_pools(0,spec['train_n'],spec['dev_n'])
    def evaluate_arm(arm):
        for seed in spec['seeds']:
            ensure_budget(started,spec,workdir)
            key=f'{arm}-s{seed}';entry=checkpoints[key];path=workdir/entry['path']
            if digest(path)!=entry['sha256']:raise RuntimeError('checkpoint changed before scoring')
            model,_=load_checkpoint(path,args.device)
            train=build_pools(seed,spec['train_n'],spec['dev_n'])['TRAIN'];ids=torch.arange(100)
            retention=Dataset(train.inputs.select(ids),train.targets[ids],train.structures[:100],train.table_hashes[:100],
                              train.expression_keys[:100],{**train.audit,'split':'TRAIN_retention'})
            results[key]={name:score(model,pool,args.device) for name,pool in
                {'TRAIN_retention':retention,'dev_structure':dev['dev_structure'],'dev_order':dev['dev_order']}.items()}
            write_json(workdir/f'sol_compose_awake_{key}_raw.json',results[key])
            del model;gc.collect()
    for arm in ARMS:
        if arm!='compose':evaluate_arm(arm)
    noise=local_noise(results,spec);write_json(workdir/'sol_compose_awake_NOISE.json',noise)
    evaluate_arm('compose')
    summary=summarize(results,noise,spec,checkpoints)
    write_json(workdir/'sol_compose_awake_SUMMARY.json',summary)
    write_json(workdir/'sol_compose_awake_COMPLETE.json',dict(utc=utc(),seconds=time.monotonic()-started,
                                                           sleep_updates=0,holdout_opened=False))
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--device',choices=('cpu','cuda'),default='cpu');p.add_argument('--workdir',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        check_seal();write_json(args.out,prepare(json.loads((ART/'SPEC-AWAKE.json').read_text())))
    else:run(args)
