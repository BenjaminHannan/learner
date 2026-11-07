"""Audit frozen initial/final policies on a fresh held-out task suite."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import torch
from playwright.async_api import async_playwright
from .browser_env import BrowserEnv
from .model import GymPolicy
from .train import evaluate
from .gpu_gate import Lease


async def audit(args):
    torch.set_num_threads(1)
    root=Path(args.run);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    results=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,args=['--disable-gpu'])
        envs=[BrowserEnv(browser,max_steps=args.max_steps) for _ in range(args.envs)]
        await asyncio.gather(*[e.start() for e in envs])
        try:
            net=GymPolicy().to(args.device)
            for seed in args.seeds:
                row={'seed':seed,'eval_episodes_per_task':args.episodes,'device':args.device,
                     'max_steps':args.max_steps,'source_sha256':{
                         p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in Path(__file__).parent.glob('*.py')},'phases':{}}
                for phase in ('initial','final'):
                    path=root/('seed-'+str(seed))/(phase+'.pt')
                    net.load_state_dict(torch.load(path,map_location=args.device,weights_only=True));net.eval()
                    trace=out/('seed-%d-%s.jsonl'%(seed,phase))
                    result=await evaluate(net,envs,args.device,args.episodes,seed+700,args.max_steps,trace_path=trace)
                    result['checkpoint_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                    result['checkpoint_path']=str(path.resolve())
                    result['trace_sha256']=hashlib.sha256(trace.read_bytes()).hexdigest()
                    row['phases'][phase]=result
                    print(json.dumps({'seed':seed,'phase':phase,**result}),flush=True)
                results.append(row)
                (out/'audit.json').write_text(json.dumps(results,indent=2))
        finally:
            await asyncio.gather(*[e.close() for e in envs]);await browser.close()
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',default='runs/proof')
    p.add_argument('--output',default='runs/audit')
    p.add_argument('--seeds',nargs='+',type=int,default=[11,22,33])
    p.add_argument('--episodes',type=int,default=32)
    p.add_argument('--envs',type=int,default=8)
    p.add_argument('--max-steps',type=int,default=8)
    p.add_argument('--device',default='cuda')
    args=p.parse_args()
    if args.device=='cuda':
        with Lease(Path.cwd()):asyncio.run(audit(args))
    else:asyncio.run(audit(args))

if __name__=='__main__':main()
