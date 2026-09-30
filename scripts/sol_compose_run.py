"""Minimal joined symbolic driver. Training runs ONLY through watcher queues.

run: serial six-arm, two-seed, bounded TRAIN/dev wake+actual replay sleep.
prepare: deterministic symbolic pool audit only (no forward/fitting/scoring).
infer: trained checkpoint + symbolic input JSON + optional NotebookState .pt;
       output translator receives final board ONLY. No English proof.

The driver owns its experiment directory, never downloads, opens a benchmark,
loads existing source weights, changes a seal, or selects a checkpoint on dev.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import time
import torch
from torch import nn
from torch.nn import functional as F
from sol_compose_data import InputBatch, build_pools, generate
from sol_compose_model import ARMS, ROUNDS, build_model, parameter_counts, Attention, RecordPort
from sol_compose_notebook import NotebookState, NotebookStore

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'artifacts/sol-compose-20260929'
STOP_REQUESTED=False


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path=Path(path)
    with path.open('x') as f:
        json.dump(data,f,indent=2,sort_keys=True);f.write('\n')


def check_seal():
    manifest=json.loads((ART/'CODE-SEAL.json').read_text())
    for relative,sha in manifest['sha256'].items():
        if digest(ROOT/relative)!=sha:
            raise RuntimeError(f'seal mismatch: {relative}')
    return manifest


class WorkMeter:
    """Executed forward MAC accounting, NOT complete FLOPs or runtime claims.

    Linear maps, GRU input/recurrent maps, attention matmuls, binding matmuls,
    and factorized record pair maps included. Norm, nonlinearities, reductions,
    equality incidence, router topk and optimizer work excluded and disclosed.
    Backprop MAC estimate = 2x forward, a convention not a measurement.
    """
    def __init__(self, model):
        self.model,self.linear,self.gru=model,0,0
        self.handles=[]
        for module in model.modules():
            if isinstance(module,nn.Linear):
                self.handles.append(module.register_forward_hook(self._linear))
            if isinstance(module,nn.GRUCell):
                self.handles.append(module.register_forward_hook(self._gru))
        self.reset()

    def _linear(self,m,args,out):
        self.linear+=out.numel()*m.in_features

    def _gru(self,m,args,out):
        self.gru+=out.numel()*3*(m.input_size+m.hidden_size)

    def reset(self):
        self.linear=self.gru=0
        for module in self.model.modules():
            if isinstance(module,(Attention,RecordPort)):
                module.matrix_macs=0

    def result(self):
        matrix=sum(m.matrix_macs for m in self.model.modules() if isinstance(m,(Attention,RecordPort)))
        return dict(linear=self.linear,gru=self.gru,matrix=matrix,total=self.linear+self.gru+matrix,
                    scope='forward MAC subset; excludes pointwise/reductions/equality/optimizer')

    def close(self):
        for handle in self.handles:handle.remove()


def loss_for(model, inputs, targets):
    result=model.rollout(inputs,rounds=ROUNDS)
    mask=inputs.slots.any(-1)
    labels=targets[:,None].expand(-1,ROUNDS,-1)
    selected=mask[:,None].expand(-1,ROUNDS,-1)
    logits=result['logits']
    # All-round content supervision; no target is used in forward/read/infer.
    ce=F.cross_entropy(logits[selected],labels[selected])
    exact=((logits.detach().argmax(-1)==labels)|~selected).all(-1).float()
    halt=F.binary_cross_entropy_with_logits(result['halt'],exact)
    return ce+.05*halt+result['aux'],dict(content=float(ce.detach()),halt=float(halt.detach()))


def _signal(_signum,_frame):
    global STOP_REQUESTED
    STOP_REQUESTED=True


def ensure_budget(started,spec,workdir):
    if spec.get('idle_file') and not Path(spec['idle_file']).exists():
        raise InterruptedError('sleep interrupted because external idle marker disappeared')
    if STOP_REQUESTED or (workdir/'STOP').exists():
        raise InterruptedError('idle sleep/wake interrupted; checkpoint only at complete update')
    if time.monotonic()-started>spec['wall_seconds']:
        raise TimeoutError('sealed wall cap reached; partial only')
    if shutil.disk_usage(workdir).free<spec['free_disk_floor_bytes']:
        raise RuntimeError('sealed disk floor reached; partial only')


def train_steps(model,opt,pool,*,steps,batch,seed,device,started,spec,workdir,replay=None,primitive_pool=None):
    generator=torch.Generator().manual_seed(seed)
    model.train();meter=WorkMeter(model);losses=[];completed=0
    try:
        for step in range(steps):
            ensure_budget(started,spec,workdir)
            if primitive_pool is not None:
                n=batch//2
                a,ay=pool.select(torch.randint(len(pool.targets),(n,),generator=generator))
                b,by=primitive_pool.select(torch.randint(len(primitive_pool.targets),(batch-n,),generator=generator))
                inputs=InputBatch(*(torch.cat((x,y)) for x,y in zip((a.tokens,a.slots,a.valid),(b.tokens,b.slots,b.valid))))
                targets=torch.cat((ay,by))
            elif replay is None:
                ids=torch.randint(len(pool.targets),(batch,),generator=generator)
                inputs,targets=pool.select(ids)
            else:
                # Exactly 26/32 recent-day + 6/32 earlier TRAIN examples.
                n=spec['sleep_recent_per_batch']
                recent_ids=torch.randint(len(pool.targets),(n,),generator=generator)
                old_ids=torch.randint(len(replay.targets),(batch-n,),generator=generator)
                a,ay=pool.select(recent_ids);b,by=replay.select(old_ids)
                inputs=InputBatch(*(torch.cat((x,y)) for x,y in zip(
                    (a.tokens,a.slots,a.valid),(b.tokens,b.slots,b.valid))))
                targets=torch.cat((ay,by))
            inputs,targets=inputs.to(device),targets.to(device)
            opt.zero_grad(set_to_none=True)
            loss,parts=loss_for(model,inputs,targets)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError('nonfinite loss')
            loss.backward()
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
            opt.step();completed+=1
            if step<4 or step>=steps-4:
                losses.append(dict(step=step+1,loss=float(loss.detach()),gradient_norm=float(norm),**parts))
        return dict(completed_updates=completed,presentations=completed*batch,
                    forward_macs=meter.result(),backward_macs_estimate=2*meter.result()['total'],
                    losses_first_last_four=losses)
    except (InterruptedError,TimeoutError):
        # Exact completed-update checkpoint; no in-flight optimizer update.
        tmp=workdir/'sol_compose_interrupt.tmp'
        torch.save(dict(schema='sol_compose.interrupted.v1',model=model.state_dict(),optimizer=opt.state_dict(),
                        completed_updates=completed,generator_state=generator.get_state(),
                        torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
                        utc=utc()),tmp)
        tmp.replace(workdir/'sol_compose_interrupted.pt')
        raise
    finally:
        meter.close()


def save_checkpoint(path,model,seed,phase,spec,notebook_sha):
    torch.save(dict(schema='sol_compose.joined.v1',arm=model.arm,seed=seed,phase=phase,
                    config=dict(round_cap=ROUNDS,latent_width=64,top_k=2,experts=4),
                    model=model.cpu().state_dict(),notebook_sha256=notebook_sha,
                    spec_sha256=digest(ART/'SPEC.json')),path)
    return digest(path)


def load_checkpoint(path,device):
    data=torch.load(path,map_location='cpu',weights_only=True)
    model=build_model(data['arm']);model.load_state_dict(data['model']);model.to(device)
    return model,data


@torch.no_grad()
def score(model,dataset,device,eval_batch=20):
    model.eval();meter=WorkMeter(model);predicted=[];fixed=[];rounds=[];labels=[]
    for start in range(0,len(dataset.targets),eval_batch):
        ids=torch.arange(start,min(start+eval_batch,len(dataset.targets)))
        inp,target=dataset.select(ids);inp=inp.to(device)
        mask=inp.slots.any(-1)
        result=model.infer(inp,cap=ROUNDS,min_rounds=2,threshold=.5)
        fx=model.rollout(inp,rounds=ROUNDS)['logits'][:,-1].argmax(-1)
        predicted.extend(result['logits'].argmax(-1)[mask].cpu().tolist())
        fixed.extend(fx[mask].cpu().tolist());rounds.extend(result['rounds'].cpu().tolist())
        labels.extend(target[mask.cpu()].tolist())
    work=meter.result();meter.close()
    return dict(n=len(labels),exact=sum(a==b for a,b in zip(predicted,labels)),
                fixed_exact=sum(a==b for a,b in zip(fixed,labels)),predictions=predicted,
                fixed_predictions=fixed,labels=labels,rounds=rounds,
                mean_rounds=sum(rounds)/len(rounds),cap_hits=sum(x==ROUNDS for x in rounds),
                query_sha256=dataset.audit['sha256'],forward_macs=work,
                scored_once_per_checkpoint=True,split=dataset.audit['split'])


def notebook_for(pools,path):
    store=NotebookStore(path)
    for split in ('TRAIN','TRAIN_primitives','recent'):
        pool=pools[split]
        for tokens in pool.inputs.tokens:
            facts=tokens[tokens[:,0]==120].tolist()
            raw=json.dumps(facts,separators=(',',':')).encode()
            store.append(raw,origin='symbolic_code',source_ref=f'{split}:seed:{pool.audit["seed"]}',
                         origin_evidence=f'sol_compose_data.py SHA256 {digest(ROOT/"scripts/sol_compose_data.py")}')
    return digest(path)


def prepare(spec):
    audit={}
    for seed in spec['seeds']:
        pools=build_pools(seed,spec['train_n'],spec['dev_n'])
        recent=generate('TRAIN',906000+seed,spec['recent_n'],excluded_tables=pools['TRAIN'].table_hashes)
        audit[str(seed)]={k:v.audit for k,v in {**pools,'recent':recent}.items()}
    return dict(scope='symbolic pool audit only; not fitting or performance',pools=audit)


def run(args):
    # This protects against accidentally invoking training during local checks.
    # Authorization is the user's queue-only policy, not this environment flag.
    if os.environ.get('SOL_COMPOSE_QUEUE_JOB') not in ('sol-compose-20260929-mac','sol-compose-20260929-pc'):
        raise RuntimeError('queue-only: watcher must set SOL_COMPOSE_QUEUE_JOB; local training forbidden')
    seal=check_seal();spec=json.loads((ART/'SPEC.json').read_text())
    if not args.idle_file.exists():
        raise InterruptedError('external operator idle marker prerequisite missing; no training started')
    workdir=args.workdir.resolve();workdir.mkdir(parents=True,exist_ok=True)
    if (workdir/'sol_compose_STARTED.json').exists():
        raise RuntimeError('duplicate run refused; report existing/partial result, never silently rerun')
    write_json(workdir/'sol_compose_STARTED.json',dict(utc=utc(),seal=seal,device=args.device,torch=torch.__version__))
    torch.set_num_threads(spec['threads'])
    if args.device=='cuda':
        if not torch.cuda.is_available():raise RuntimeError('NO CUDA; no automatic fallback')
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    signal.signal(signal.SIGTERM,_signal);signal.signal(signal.SIGINT,_signal)
    started=time.monotonic()
    audits=prepare(spec);write_json(workdir/'sol_compose_DATA.json',audits)
    records={}
    # All training and sleep snapshots finish before ANY dev scores are seen.
    for seed in spec['seeds']:
        pools=build_pools(seed,spec['train_n'],spec['dev_n'])
        recent=generate('TRAIN',906000+seed,spec['recent_n'],excluded_tables=pools['TRAIN'].table_hashes)
        pools['recent']=recent
        notebook_sha=notebook_for(pools,workdir/f'sol_compose_notebook_s{seed}.jsonl')
        for arm in ARMS:
            ensure_budget(started,spec,workdir)
            torch.manual_seed(spec['initialization_base']+seed)
            model=build_model(arm).to(args.device)
            opt=torch.optim.AdamW(model.parameters(),lr=spec['lr'],weight_decay=0.)
            if args.device=='cuda':torch.cuda.reset_peak_memory_stats()
            start=time.monotonic();key=f'{arm}-s{seed}'
            record=dict(seed=seed,arm=arm,counts=parameter_counts(model),notebook_sha256=notebook_sha,
                        training_start_utc=utc(),checkpoints={})
            record['practice']=train_steps(model,opt,pools['TRAIN'],steps=spec['practice_updates'],batch=spec['batch'],
                seed=907000+seed,device=args.device,started=started,spec=spec,workdir=workdir,primitive_pool=pools['TRAIN_primitives'])
            record['recent_day']=train_steps(model,opt,recent,steps=spec['recent_updates'],batch=spec['batch'],
                seed=908000+seed,device=args.device,started=started,spec=spec,workdir=workdir)
            awake=workdir/f'sol_compose_{key}_awake.pt'
            record['checkpoints']['awake']=save_checkpoint(awake,model,seed,'awake',spec,notebook_sha)
            del opt,model;gc.collect()
            record['sleep']=[]
            for draw in spec['sleep_draws']:
                # Idle-only runner: file is owned by the operator/watcher, not
                # synthesized by an answer/model. STOP interrupts at next update.
                if not args.idle_file or not args.idle_file.exists():
                    raise InterruptedError('sleep requires external idle authorization marker')
                model,_=load_checkpoint(awake,args.device)
                opt=torch.optim.AdamW(model.parameters(),lr=spec['sleep_lr'],weight_decay=0.)
                sleep_started=time.monotonic()
                # Keep idle checked during EVERY update as well as at start.
                sleep_spec={**spec,'idle_file':str(args.idle_file)}
                sleep_record=train_steps(model,opt,recent,replay=pools['TRAIN'],steps=spec['sleep_updates'],batch=spec['batch'],
                    seed=909000+seed*10+draw,device=args.device,started=started,spec=sleep_spec,workdir=workdir)
                checkpoint=workdir/f'sol_compose_{key}_sleep{draw}.pt'
                record['checkpoints'][f'sleep{draw}']=save_checkpoint(checkpoint,model,seed,f'sleep{draw}',spec,notebook_sha)
                record['sleep'].append(dict(draw=draw,seconds=time.monotonic()-sleep_started,**sleep_record))
                del opt,model;gc.collect()
            record['seconds']=time.monotonic()-start
            record['cuda_peak_allocated_bytes']=torch.cuda.max_memory_allocated() if args.device=='cuda' else None
            records[key]=record
            write_json(workdir/f'sol_compose_{key}_training.json',record)
            print(json.dumps(dict(utc=utc(),trained=key,seconds=record['seconds'],counts=record['counts'])),flush=True)
    # Checkpoints and budgets are immutable before first query evaluation.
    write_json(workdir/'sol_compose_CHECKPOINT-SEAL.json',{k:v['checkpoints'] for k,v in records.items()})
    results={}
    def evaluate_arm(arm):
        for seed in spec['seeds']:
            key=f'{arm}-s{seed}';pools=build_pools(seed,spec['train_n'],spec['dev_n'])
            ids=torch.arange(spec['retention_n'])
            train=pools['TRAIN']
            # Retention is TRAIN, never a final old-kind gate.
            from sol_compose_data import Dataset
            old=Dataset(train.inputs.select(ids),train.targets[ids],train.structures[:len(ids)],train.table_hashes[:len(ids)],
                        train.expression_keys[:len(ids)],{**train.audit,'split':'TRAIN_retention'})
            results[key]={}
            for phase,sha in records[key]['checkpoints'].items():
                path=workdir/f'sol_compose_{key}_{phase}.pt'
                if digest(path)!=sha:raise RuntimeError('checkpoint changed before score')
                ensure_budget(started,spec,workdir)
                model,_=load_checkpoint(path,args.device)
                results[key][phase]={name:score(model,pool,args.device) for name,pool in
                    {'TRAIN_retention':old,'dev_structure':pools['dev_structure'],'dev_order':pools['dev_order']}.items()}
                del model;gc.collect()
            write_json(workdir/f'sol_compose_{key}_dev.json',results[key])
    for arm in ARMS:
        if arm!='compose':evaluate_arm(arm)
    # Same-platform run-to-run noise recorded BEFORE candidate scoring. Fixed
    # formula was presealed; never tune marks from a candidate score.
    noise={}
    for split in ('dev_structure','dev_order'):
        spans={arm:abs(results[f'{arm}-s0']['awake'][split]['exact']-results[f'{arm}-s1']['awake'][split]['exact'])*100/spec['dev_n']
               for arm in ARMS if arm!='compose'}
        local=max(spans.values())
        noise[split]=dict(control_seed_spans_pp=spans,measured_noise_pp=local,
                          bar_pp=max(spec['minimum_gap_pp'],2*local+1.),
                          caveat='two-seed span, not an SE; different seed pools; conservative but low precision')
    write_json(workdir/'sol_compose_NOISE-BARS.json',noise)
    evaluate_arm('compose')
    summary=summarize(results,noise,spec)
    write_json(workdir/'sol_compose_SUMMARY.json',summary)
    write_json(workdir/'sol_compose_COMPLETE.json',dict(utc=utc(),wall_seconds=time.monotonic()-started,
                state='complete TRAIN/dev only',holdout_opened=False,training_jobs=len(records)))
    print(json.dumps(summary,indent=2),flush=True)


def summarize(results,noise,spec):
    rows=[]
    for seed in spec['seeds']:
        for split in ('dev_structure','dev_order'):
            candidate=results[f'compose-s{seed}']['awake'][split]
            controls={arm:results[f'{arm}-s{seed}']['awake'][split]['exact'] for arm in ARMS if arm!='compose'}
            best=max(controls.values())
            gap=(candidate['exact']-best)*100/spec['dev_n']
            rows.append(dict(seed=seed,split=split,candidate=candidate['exact'],n=spec['dev_n'],controls=controls,
                             gap_pp=gap,bar_pp=noise[split]['bar_pp'],
                             dev_promising=gap>=noise[split]['bar_pp'] and candidate['exact']>=spec['accuracy_floor_count'] and
                               candidate['fixed_exact']-candidate['exact']<=spec['stop_max_loss_count']))
    sleeps=[]
    for seed in spec['seeds']:
        for arm in ARMS:
            awake=results[f'{arm}-s{seed}']['awake']
            for split in ('TRAIN_retention','dev_structure','dev_order'):
                vals=[results[f'{arm}-s{seed}'][f'sleep{x}'][split]['exact'] for x in spec['sleep_draws']]
                mean=sum(vals)/len(vals)
                se=(sum((x-mean)**2 for x in vals)/(len(vals)-1))**.5/len(vals)**.5
                sleeps.append(dict(seed=seed,arm=arm,split=split,awake=awake[split]['exact'],sleep_draw_counts=vals,
                                   sleep_mean=mean,sleep_se=se,report_margin_count=max(6,2*se),n=awake[split]['n']))
    return dict(scope='diagnostic TRAIN/dev only; no final claim, no English/benchmark proof',
                verdict='DEV PROMISING' if all(x['dev_promising'] for x in rows) else 'NOT SHOWN ON DEV',
                rows=rows,sleep_rows=sleeps,F_eq='not evaluated; this is a fixed-budget internal pilot',
                F_few='not evaluated; no few-example/adaptation claim',holdout_opened=False,
                general_reasoner_proven=False,english_proven=False,sleep_general_improvement_proven=False)


def infer(args):
    # Inference only is allowed outside queue. Needs a newly trained checkpoint.
    torch.set_num_threads(2)
    model,metadata=load_checkpoint(args.checkpoint,args.device)
    raw=json.loads(args.input.read_text())
    tokens=torch.tensor(raw['tokens'],dtype=torch.long,device=args.device)
    slots=torch.tensor(raw['slots'],dtype=torch.bool,device=args.device)
    inputs=InputBatch(tokens,slots,torch.ones_like(slots))
    memory=None
    if args.memory:
        packet=torch.load(args.memory,map_location=args.device,weights_only=True)
        memory=NotebookState(packet['translated'],packet['mask'])
    with torch.no_grad():
        result=model.infer(inputs,memory=memory)
        # Same learned thin symbolic decoder; takes board only, no raw facts.
        output=model.head(result['board'])
    torch.save(dict(schema='sol_compose.final-latent.v1',final_state=result['board'].cpu(),
                    rounds=result['rounds'].cpu(),checkpoint_sha256=digest(args.checkpoint)),args.output)
    print(json.dumps(dict(checkpoint_sha256=digest(args.checkpoint),latent_output=str(args.output),
                          symbolic_answer_tokens=output.argmax(-1)[slots.any(-1)].cpu().tolist(),
                          rounds=result['rounds'].cpu().tolist(),english=False)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--workdir',type=Path,required=True);p.add_argument('--idle-file',type=Path,required=True)
    p=sub.add_parser('infer');p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--memory',type=Path);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        check_seal();write_json(args.out,prepare(json.loads((ART/'SPEC.json').read_text())))
    elif args.command=='run':
        run(args)
    else:
        infer(args)
