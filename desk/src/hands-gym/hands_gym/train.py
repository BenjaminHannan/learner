"""On-policy PPO, screenshots only, independent reproducible seeds, quarantine.

The curriculum focuses on popup dismissal initially. All seven task families
are measured independently; success on other families is never inferred.
"""
import argparse
import asyncio
import hashlib
import json
import os
import random
import time
from pathlib import Path
import numpy as np
import torch
from playwright.async_api import async_playwright
from . import tasks
from .browser_env import BrowserEnv
from .model import GymPolicy, batch, native_actions
from .gpu_gate import Lease, inspect, foreign_clients
from .remote import RemoteEnv


def save(net,path):
    temp=path.with_suffix('.tmp')
    torch.save(net.state_dict(),temp)
    temp.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def evaluate(net,envs,device,episodes,seed,max_steps,trace_path=None):
    """Fixed, disjoint task seeds. Stochastic policy with paired action RNG."""
    torch.manual_seed(seed)
    results={k:[] for k in tasks.TASK_TYPES[:7]}
    traces=[]
    steps=0
    started=time.monotonic()
    for kind in results:
        for offset in range(0,episodes,len(envs)):
            active=envs[:min(len(envs),episodes-offset)]
            obs=await asyncio.gather(*[e.reset(kind,10_000_000+seed*1000+offset+i) for i,e in enumerate(active)])
            for e in active:e.episode['max_steps']=max_steps
            instructions=[e.episode['instruction'] for e in active]
            alive=list(range(len(active)))
            success=[False]*len(active)
            histories=[[] for _ in active]
            initial_hashes=[hashlib.sha256(o['overview'].tobytes()).hexdigest() for o in obs]
            while alive:
                with torch.no_grad():
                    acts,*_=net.act(batch([obs[i] for i in alive],[instructions[i] for i in alive],device))
                decoded=native_actions(acts)
                for i,a in zip(alive,decoded):histories[i].append(a)
                replies=await asyncio.gather(*[active[i].step(a) for i,a in zip(alive,decoded)])
                steps+=len(alive)
                nxt=[]
                for i,(o,r,d,info) in zip(alive,replies):
                    obs[i]=o
                    if d:success[i]=info['success']
                    else:nxt.append(i)
                alive=nxt
            results[kind].extend(success)
            for i,e in enumerate(active):
                traces.append({'kind':kind,'task_seed':10_000_000+seed*1000+offset+i,
                    'instruction':instructions[i],'success':success[i],'steps':e.t,
                    'initial_overview_sha256':initial_hashes[i],
                    'final_overview_sha256':hashlib.sha256(obs[i]['overview'].tobytes()).hexdigest(),
                    'actions':histories[i],'terminal_state':e.state})
    if trace_path:
        Path(trace_path).write_text(''.join(json.dumps(t)+'\n' for t in traces))
    return {'overall':float(np.mean([v for rows in results.values() for v in rows])),
            'per_task':{k:{'successes':int(sum(v)),'episodes':len(v),'rate':float(np.mean(v))} for k,v in results.items()},
            'steps':steps,'steps_per_second':steps/(time.monotonic()-started),'eval_seed':seed}


async def run_seed(args,seed,browser):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    device=torch.device(args.device)
    net=GymPolicy().to(device)
    if args.native_checkpoint:net.load_native(args.native_checkpoint)
    if args.resume_checkpoint:
        net.load_state_dict(torch.load(args.resume_checkpoint,map_location=device,weights_only=True))
    opt=torch.optim.Adam(net.parameters(),lr=args.lr,eps=1e-5)
    out=Path(args.output)/('seed-'+str(seed));out.mkdir(parents=True,exist_ok=True)
    initial_hash=save(net,out/'initial.pt')
    envs=[]
    for endpoint in args.remote_endpoints:
        host,port=endpoint.rsplit(':',1)
        e=RemoteEnv(host,int(port),max_steps=args.max_steps)
        await e.connect();envs.append(e)
    locals_=[BrowserEnv(browser,max_steps=args.max_steps)
             for _ in range(args.envs-len(envs))]
    await asyncio.gather(*[e.start() for e in locals_])
    envs.extend(locals_)
    try:
        baseline=await evaluate(net,envs,device,args.eval_episodes,seed+700,args.max_steps)
        print(json.dumps({'seed':seed,'phase':'baseline',**baseline}),flush=True)
        (out/'baseline.json').write_text(json.dumps(baseline,indent=2))
        rng=random.Random(seed)
        episode_serial=0
        def new_task(update):
            nonlocal episode_serial
            episode_serial+=1
            # Unique low seeds, evaluation uses a separate high range.
            kind='close_popup' if update<args.updates*0.7 else rng.choices(
                ['close_popup','click_button','click_link','dropdown','menu_select','drag_slider','type_text'],
                weights=[70,10,5,5,4,4,2])[0]
            return kind,seed*100000+episode_serial
        obs=await asyncio.gather(*[e.reset(*new_task(0)) for e in envs])
        for e in envs:e.episode['max_steps']=args.max_steps
        curve=[];env_steps=0;completed=[]
        started=time.monotonic()
        for update in range(1,args.updates+1):
            storage=[]
            for _ in range(args.rollout):
                inputs=batch(obs,[e.episode['instruction'] for e in envs],device)
                with torch.no_grad():acts,logp,_,values=net.act(inputs)
                replies=await asyncio.gather(*[e.step(a) for e,a in zip(envs,native_actions(acts))])
                rewards=torch.tensor([r[1] for r in replies],device=device)
                dones=torch.tensor([r[2] for r in replies],device=device)
                # Store rollouts on CPU without retaining GPU autograd graphs.
                storage.append((tuple(x.detach().cpu() for x in inputs),acts.cpu(),logp.cpu(),values.cpu(),rewards.cpu(),dones.cpu()))
                obs=[r[0] for r in replies]
                reset_ids=[i for i,r in enumerate(replies) if r[2]]
                for i in reset_ids:completed.append(replies[i][3]['success'])
                resets=await asyncio.gather(*[envs[i].reset(*new_task(update)) for i in reset_ids])
                for i,o in zip(reset_ids,resets):obs[i]=o;envs[i].episode['max_steps']=args.max_steps
                env_steps+=len(envs)
            with torch.no_grad():_,next_value=net(*batch(obs,[e.episode['instruction'] for e in envs],device))
            gae=torch.zeros(args.envs);returns=[];advantages=[]
            next_value=next_value.cpu()
            for row in reversed(storage):
                _,_,_,value,reward,done=row
                live=(~done).float()
                delta=reward+0.99*next_value*live-value
                gae=delta+0.99*0.95*live*gae
                advantages.append(gae);returns.append(gae+value);next_value=value
            advantages=torch.cat(list(reversed(advantages))).to(device)
            returns=torch.cat(list(reversed(returns))).to(device)
            inputs=tuple(torch.cat([s[0][j] for s in storage]) for j in range(4))
            acts=torch.cat([s[1] for s in storage]).to(device)
            oldlog=torch.cat([s[2] for s in storage]).to(device)
            advantages=(advantages-advantages.mean())/(advantages.std()+1e-8)
            for epoch in range(args.epochs):
                order=torch.randperm(len(acts))
                for ix in order.split(args.minibatch):
                    inp=tuple(x[ix].to(device) for x in inputs)
                    _,logp,entropy,value=net.act(inp,actions=acts[ix])
                    ratio=(logp-oldlog[ix]).exp()
                    policy=-torch.minimum(ratio*advantages[ix],ratio.clamp(0.8,1.2)*advantages[ix]).mean()
                    loss=policy+0.5*(value-returns[ix]).square().mean()-args.entropy*entropy.mean()
                    opt.zero_grad(set_to_none=True);loss.backward()
                    torch.nn.utils.clip_grad_norm_(net.parameters(),0.5);opt.step()
            if update%10==0 or update==1:
                row={'seed':seed,'update':update,'environment_steps':env_steps,
                     'recent_train_success':float(np.mean(completed[-100:])) if completed else 0,
                     'steps_per_second':env_steps/(time.monotonic()-started),
                     'gpu_allocated_mb':torch.cuda.max_memory_allocated()/2**20 if device.type=='cuda' else 0,
                     'loss':float(loss.detach())}
                curve.append(row)
                print(json.dumps(row),flush=True)
                (out/'curve.json').write_text(json.dumps(curve,indent=2))
                save(net,out/'latest.pt')
            if device.type=='cuda' and update%50==0:
                status=inspect()
                print(json.dumps({'gpu_monitor':status}),flush=True)
                if device.type=='cuda' and foreign_clients(status,os.getpid()):
                    save(net,out/'latest.pt')
                    raise RuntimeError('foreign CUDA client appeared; checkpoint saved; yielding GPU')
        train_seconds=time.monotonic()-started
        final_hash=save(net,out/'final.pt')
        final=await evaluate(net,envs,device,args.eval_episodes,seed+700,args.max_steps)
        result={'seed':seed,'starting_policy':args.resume_checkpoint or args.native_checkpoint or 'fresh HANDS NativeActionPolicy architecture + categorical RL positions',
                'initial_sha256':initial_hash,'final_sha256':final_hash,'baseline':baseline,'final':final,
                'curve':curve,'train_steps':env_steps,'train_seconds':train_seconds,
                'train_steps_per_second':env_steps/train_seconds,'args':vars(args),
                'parameters':sum(p.numel() for p in net.parameters())}
        (out/'result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps({'seed':seed,'phase':'final',**final}),flush=True)
        return result
    finally:
        await asyncio.gather(*[e.close() for e in envs])


async def main_async(args):
    torch.set_num_threads(1)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,args=['--disable-gpu'])
        try:
            results=[]
            for seed in args.seeds:
                results.append(await run_seed(args,seed,browser))
            Path(args.output,'results.json').write_text(json.dumps(results,indent=2))
        finally:await browser.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='runs/proof')
    p.add_argument('--seeds',type=int,nargs='+',default=[11,22,33])
    p.add_argument('--updates',type=int,default=200)
    p.add_argument('--envs',type=int,default=8)
    p.add_argument('--rollout',type=int,default=8)
    p.add_argument('--max-steps',type=int,default=8)
    p.add_argument('--eval-episodes',type=int,default=16)
    p.add_argument('--epochs',type=int,default=3)
    p.add_argument('--minibatch',type=int,default=32)
    p.add_argument('--lr',type=float,default=0.0003)
    p.add_argument('--entropy',type=float,default=0.005)
    p.add_argument('--device',default='cuda')
    initialization=p.add_mutually_exclusive_group()
    initialization.add_argument('--native-checkpoint')
    initialization.add_argument('--resume-checkpoint')
    p.add_argument('--remote-endpoints',nargs='*',default=[])
    a=p.parse_args()
    if len(a.remote_endpoints)>a.envs:p.error('remote workers exceed --envs')
    Path(a.output).mkdir(parents=True,exist_ok=True)
    if a.device=='cuda':
        with Lease(Path.cwd()):asyncio.run(main_async(a))
    else:asyncio.run(main_async(a))

if __name__=='__main__':main()
