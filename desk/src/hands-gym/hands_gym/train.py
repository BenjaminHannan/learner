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
from .curriculum import ReverseCurriculum


class SuccessBuffer:
    def __init__(self,envs,capacity=128,seed=0):
        self.capacity=capacity
        self.episodes=[]
        self.pending=[[] for _ in range(envs)]
        self.rng=random.Random(seed)

    def record(self,inputs,actions,replies):
        for index,(_,_,done,info) in enumerate(replies):
            packed=tuple(value[index].detach().cpu().mul(255).round().byte()
                         if slot<2 else value[index].detach().cpu().clone()
                         for slot,value in enumerate(inputs))
            self.pending[index].append((packed,actions[index].detach().cpu().clone()))
            if done:
                if info['success']:
                    self.episodes.append(self.pending[index])
                    self.episodes=self.episodes[-self.capacity:]
                self.pending[index]=[]

    def sample(self,count,device):
        transitions=[transition for episode in self.episodes for transition in episode]
        if not transitions:return None
        selected=self.rng.choices(transitions,k=min(count,len(transitions)))
        inputs=tuple(torch.stack([transition[0][slot] for transition in selected]).to(device)
                     for slot in range(4))
        inputs=tuple(value.float()/255 if slot<2 else value for slot,value in enumerate(inputs))
        actions=torch.stack([transition[1] for transition in selected]).to(device)
        return inputs,actions

    def state_dict(self):
        return {'episodes':self.episodes,'pending':self.pending,'rng':self.rng.getstate()}

    def load_state_dict(self,state):
        self.episodes=state['episodes'];self.pending=state['pending']
        self.rng.setstate(state['rng'])


def cloning_loss(net,buffer,count,device):
    sample=buffer.sample(count,device)
    if sample is None:return None
    inputs,actions=sample
    _,logp,_,_=net.act(inputs,actions=actions)
    return -logp.mean()


def save_training(state,path):
    temp=path.with_suffix('.tmp')
    torch.save(state,temp)
    temp.replace(path)


def observation_hash(observation):
    return hashlib.sha256(b''.join(observation[key].tobytes()
                                 for key in ('overview','detail'))).hexdigest()


async def reset_task(environment,task):
    if task.get('start_k') is not None:
        return await environment.reset(task['kind'],task['seed'],start_k=task['start_k'])
    return await environment.reset(task['kind'],task['seed'])


async def restore_environments(envs,live_tasks,max_steps):
    observations=[]
    for environment,task in zip(envs,live_tasks):
        observation=await reset_task(environment,task)
        environment.episode['max_steps']=max_steps
        for action in task['actions']:
            observation,_,done,_=await environment.step(action)
            if done:raise RuntimeError('resume replay unexpectedly terminated')
        if observation_hash(observation)!=task['observation_sha256']:
            raise RuntimeError('resume replay screenshot mismatch; refusing altered continuation')
        observations.append(observation)
    return observations


def save(net,path):
    temp=path.with_suffix('.tmp')
    torch.save(net.state_dict(),temp)
    temp.replace(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def evaluate(net,envs,device,episodes,seed,max_steps,trace_path=None,task_families=None):
    """Fixed, disjoint task seeds. Stochastic policy with paired action RNG."""
    torch.manual_seed(seed)
    results={k:[] for k in (task_families or tasks.TASK_TYPES[:7])}
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
                traces.append({'kind':kind,'task_seed':10_000_000+seed*1000+offset+i,'start_k':None,
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
    resume=None
    if args.resume_training:
        resume=torch.load(args.resume_training,map_location='cpu',weights_only=False)
        settings={key:value for key,value in vars(args).items() if key!='resume_training'}
        expected_settings={**resume['settings'],'design_typing':resume['settings'].get('design_typing',False)}
        settings.setdefault('design_typing',False)
        if expected_settings!=settings or resume['seed']!=seed:
            raise ValueError('resume requires identical seed, output, budget and training settings')
        net.load_state_dict(resume['net']);opt.load_state_dict(resume['optimizer'])
    initial_hash=resume['initial_sha256'] if resume else save(net,out/'initial.pt')
    buffer=SuccessBuffer(args.envs,args.success_buffer_episodes,seed+1700) if args.self_imitation_weight else None
    curriculum=ReverseCurriculum(args.start_k) if getattr(args,'start_k',None) else None
    family_options={'task_families':args.task_families} if getattr(args,'task_families',None) else {}
    envs=[]
    for endpoint in args.remote_endpoints:
        host,port=endpoint.rsplit(':',1)
        e=RemoteEnv(host,int(port),max_steps=args.max_steps)
        await e.connect();envs.append(e)
    locals_=[BrowserEnv(browser,max_steps=args.max_steps,design_typing=getattr(args,'design_typing',False))
             for _ in range(args.envs-len(envs))]
    await asyncio.gather(*[e.start() for e in locals_])
    envs.extend(locals_)
    evaluation_envs=[]
    try:
        if args.eval_every:
            evaluation_envs=[BrowserEnv(browser,max_steps=args.max_steps,
                            design_typing=getattr(args,'design_typing',False)) for _ in range(args.envs)]
            await asyncio.gather(*[environment.start() for environment in evaluation_envs])
        baseline=resume['baseline'] if resume else await evaluate(
            net,envs,device,args.eval_episodes,seed+700,args.max_steps,**family_options)
        if not resume:
            print(json.dumps({'seed':seed,'phase':'baseline',**baseline}),flush=True)
            (out/'baseline.json').write_text(json.dumps(baseline,indent=2))
        rng=random.Random(seed)
        episode_serial=0
        def new_task(update):
            nonlocal episode_serial
            episode_serial+=1
            # Unique low seeds, evaluation uses a separate high range.
            if family_options:
                kind=rng.choice(args.task_families)
            else:
                kind='close_popup' if update<args.updates*0.7 else rng.choices(
                    ['close_popup','click_button','click_link','dropdown','menu_select','drag_slider','type_text'],
                    weights=[70,10,5,5,4,4,2])[0]
            task={'kind':kind,'seed':seed*100000+episode_serial,'actions':[]}
            if curriculum:task['start_k']=curriculum.for_kind(kind)
            return task
        held_out_curve=resume['held_out_curve'] if resume else [
            {'update':0,'environment_steps':0,'checkpoint_sha256':initial_hash,**baseline}]
        if resume:
            if curriculum:curriculum.load_state_dict(resume['reverse_curriculum'])
            episode_serial=resume['episode_serial'];rng.setstate(resume['task_rng'])
            live_tasks=resume['live_tasks']
            obs=await restore_environments(envs,live_tasks,args.max_steps)
            curve=resume['curve'];env_steps=resume['environment_steps'];completed=resume['completed']
            if buffer:buffer.load_state_dict(resume['success_buffer'])
            random.setstate(resume['python_rng']);np.random.set_state(resume['numpy_rng'])
            torch.set_rng_state(resume['torch_rng'])
            if device.type=='cuda':torch.cuda.set_rng_state(resume['cuda_rng'],device)
        else:
            scheduled=[new_task(0) for _ in envs]
            live_tasks=scheduled
            obs=await asyncio.gather(*[reset_task(environment,task) for environment,task in zip(envs,scheduled)])
            for environment in envs:environment.episode['max_steps']=args.max_steps
            curve=[];env_steps=0;completed=[]
        (out/'held-out-curve.json').write_text(json.dumps(held_out_curve,indent=2))
        prior_seconds=resume['elapsed_seconds'] if resume else 0
        started=time.monotonic()
        first_update=resume['update']+1 if resume else 1
        for update in range(first_update,args.updates+1):
            storage=[]
            for _ in range(args.rollout):
                inputs=batch(obs,[e.episode['instruction'] for e in envs],device)
                with torch.no_grad():acts,logp,_,values=net.act(inputs)
                decoded=native_actions(acts)
                replies=await asyncio.gather(*[e.step(a) for e,a in zip(envs,decoded)])
                if buffer:buffer.record(inputs,acts,replies)
                for task,action in zip(live_tasks,decoded):task['actions'].append(action)
                rewards=torch.tensor([r[1] for r in replies],device=device)
                dones=torch.tensor([r[2] for r in replies],device=device)
                # Store rollouts on CPU without retaining GPU autograd graphs.
                storage.append((tuple(x.detach().cpu() for x in inputs),acts.cpu(),logp.cpu(),values.cpu(),rewards.cpu(),dones.cpu()))
                obs=[r[0] for r in replies]
                reset_ids=[i for i,r in enumerate(replies) if r[2]]
                for i in reset_ids:completed.append(replies[i][3]['success'])
                if curriculum:
                    for index in reset_ids:
                        task=live_tasks[index]
                        curriculum.record(task['kind'],task.get('start_k'),replies[index][3]['success'])
                scheduled=[new_task(update) for _ in reset_ids]
                resets=await asyncio.gather(*[reset_task(envs[index],task) for index,task in zip(reset_ids,scheduled)])
                for index,observation,task in zip(reset_ids,resets,scheduled):
                    obs[index]=observation;envs[index].episode['max_steps']=args.max_steps
                    live_tasks[index]=task
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
                    if buffer:
                        imitation=cloning_loss(net,buffer,args.minibatch,device)
                        if imitation is not None:loss=loss+args.self_imitation_weight*imitation
                    opt.zero_grad(set_to_none=True);loss.backward()
                    torch.nn.utils.clip_grad_norm_(net.parameters(),0.5);opt.step()
            if update%10==0 or update==1:
                row={'seed':seed,'update':update,'environment_steps':env_steps,
                     'recent_train_success':float(np.mean(completed[-100:])) if completed else 0,
                     'steps_per_second':env_steps/(prior_seconds+time.monotonic()-started),
                     'gpu_allocated_mb':torch.cuda.max_memory_allocated()/2**20 if device.type=='cuda' else 0,
                     'loss':float(loss.detach()),'success_buffer_episodes':len(buffer.episodes) if buffer else 0}
                if curriculum:row['reverse_curriculum']=curriculum.state_dict()
                curve.append(row)
                print(json.dumps(row),flush=True)
                (out/'curve.json').write_text(json.dumps(curve,indent=2))
                save(net,out/'latest.pt')
            if args.eval_every and (update%args.eval_every==0 or update==args.updates):
                checkpoint_hash=save(net,out/('update-%04d.pt'%update))
                evaluation_options=dict(family_options)
                if family_options and update==args.updates:
                    evaluation_options['trace_path']=out/'final-trace.jsonl'
                with torch.random.fork_rng(devices=[torch.cuda.current_device()] if device.type=='cuda' else []):
                    measured=await evaluate(net,evaluation_envs,device,args.eval_episodes,seed+700,args.max_steps,**evaluation_options)
                point={'update':update,'environment_steps':env_steps,'checkpoint_sha256':checkpoint_hash,**measured}
                held_out_curve.append(point)
                (out/'held-out-curve.json').write_text(json.dumps(held_out_curve,indent=2))
                print(json.dumps({'seed':seed,'phase':'held_out',**point}),flush=True)
            if update%10==0 or update==1 or update==args.updates:
                for task,observation in zip(live_tasks,obs):task['observation_sha256']=observation_hash(observation)
                state={'settings':{key:value for key,value in vars(args).items() if key!='resume_training'},
                       'seed':seed,'update':update,'environment_steps':env_steps,'net':net.state_dict(),
                       'optimizer':opt.state_dict(),'initial_sha256':initial_hash,'baseline':baseline,
                       'curve':curve,'held_out_curve':held_out_curve,'completed':completed,
                       'episode_serial':episode_serial,'task_rng':rng.getstate(),'live_tasks':live_tasks,
                       'success_buffer':buffer.state_dict() if buffer else None,
                       'reverse_curriculum':curriculum.state_dict() if curriculum else None,
                       'python_rng':random.getstate(),'numpy_rng':np.random.get_state(),
                       'torch_rng':torch.get_rng_state(),
                       'cuda_rng':torch.cuda.get_rng_state(device) if device.type=='cuda' else None,
                       'elapsed_seconds':prior_seconds+time.monotonic()-started}
                save_training(state,out/'training-state.pt')
            if device.type=='cuda' and update%50==0:
                status=inspect()
                print(json.dumps({'gpu_monitor':status}),flush=True)
                if device.type=='cuda' and foreign_clients(status,os.getpid()):
                    save(net,out/'latest.pt')
                    raise RuntimeError('foreign CUDA client appeared; checkpoint saved; yielding GPU')
        train_seconds=prior_seconds+time.monotonic()-started
        final_hash=save(net,out/'final.pt')
        final=held_out_curve[-1] if args.eval_every else await evaluate(
            net,envs,device,args.eval_episodes,seed+700,args.max_steps,**family_options)
        result={'seed':seed,'starting_policy':args.resume_checkpoint or args.native_checkpoint or 'fresh HANDS NativeActionPolicy architecture + categorical RL positions',
                'initial_sha256':initial_hash,'final_sha256':final_hash,'baseline':baseline,'final':final,
                'curve':curve,'held_out_curve':held_out_curve,'train_steps':env_steps,'train_seconds':train_seconds,
                'train_steps_per_second':env_steps/train_seconds,'args':vars(args),
                'parameters':sum(p.numel() for p in net.parameters())}
        if curriculum:result['reverse_curriculum']=curriculum.state_dict()
        (out/'result.json').write_text(json.dumps(result,indent=2))
        print(json.dumps({'seed':seed,'phase':'final',**final}),flush=True)
        return result
    finally:
        await asyncio.gather(*[e.close() for e in envs+evaluation_envs])


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
    p.add_argument('--self-imitation-weight',type=float,default=0.0)
    p.add_argument('--success-buffer-episodes',type=int,default=128)
    p.add_argument('--eval-every',type=int,default=0)
    p.add_argument('--task-families',nargs='+',choices=tasks.TASK_TYPES)
    p.add_argument('--start-k',type=int,default=None)
    p.add_argument('--design-typing',action='store_true',
                   help='plain-code next character and toy-equivalent typing progress; default off')
    p.add_argument('--device',default='cuda')
    initialization=p.add_mutually_exclusive_group()
    initialization.add_argument('--native-checkpoint')
    initialization.add_argument('--resume-checkpoint')
    initialization.add_argument('--resume-training')
    p.add_argument('--remote-endpoints',nargs='*',default=[])
    a=p.parse_args()
    if len(a.remote_endpoints)>a.envs:p.error('remote workers exceed --envs')
    if not np.isfinite(a.self_imitation_weight) or a.self_imitation_weight<0:
        p.error('--self-imitation-weight must be finite and nonnegative')
    if a.success_buffer_episodes<1 or a.eval_every<0:p.error('invalid buffer capacity or evaluation interval')
    if a.resume_training and len(a.seeds)!=1:p.error('--resume-training requires exactly one seed')
    if a.start_k is not None and a.start_k<1:p.error('--start-k must be positive')
    if a.start_k is not None and a.remote_endpoints:p.error('--start-k requires local browser environments')
    if a.design_typing and a.remote_endpoints:p.error('--design-typing requires local browser environments')
    if a.task_families and len(set(a.task_families))!=len(a.task_families):p.error('duplicate task family')
    Path(a.output).mkdir(parents=True,exist_ok=True)
    if a.device=='cuda':
        with Lease(Path.cwd()):asyncio.run(main_async(a))
    else:asyncio.run(main_async(a))

if __name__=='__main__':main()
