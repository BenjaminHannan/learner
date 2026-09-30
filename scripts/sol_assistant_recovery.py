#!/usr/bin/env python3
"""No-step real Adam restoration/RNG audit; never calls backward or step."""
import argparse,json,random,sys,time
from pathlib import Path
from sol_assistant_bundle import ROOT,owned,save_new,verify_bundle,validate_tuple,verify_pin,source_closure
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))

def equal(a,b):
    import torch
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a.cpu(),b.cpu())
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return type(a)==type(b) and len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b

def run(bundle,out):
    import torch
    from sol_spatial_attention_core import load_bundle
    from sol_translator_grounding_v6 import HumanInputProjection
    from sol_translator_english_v6 import StatePrefix
    start=time.monotonic();torch.set_num_threads(1);out=owned(out);out.mkdir(parents=True,exist_ok=False)
    b=verify_bundle(bundle);a=b['assets'];sources=source_closure([__file__])
    save_new(out/'marks.json',dict(scope='single actual checkpoint no-step restoration; both seeds required for completed two-seed engineering claim',seed=b['checkpoint']['seed'],bundle=b['version'],sources=sources,budget_seconds=120,passmark='all model/Adam tensors and 64 next random values exact',comparator='actual durable state before and after owner-module restoration',noise='exact CPU storage and RNG comparator, two repeats; no model scores',training_steps=0))
    meta=validate_tuple(*(a[k]['path'] for k in ('parent','reader','adapter','resume','ledger')))
    ck=torch.load(a['resume']['path'],map_location='cpu',weights_only=True)
    raw=torch.load(a['reader']['path'],map_location='cpu',weights_only=True)
    prefix=torch.load(a['adapter']['path'],map_location='cpu',weights_only=True)
    core,_=load_bundle(a['parent']['path'],'cpu')
    reader=HumanInputProjection(raw['lm_width']);reader.load_state_dict(raw['state_dict'])
    adapter=StatePrefix(prefix['state_width'],raw['lm_width'],prefix['hidden'],prefix['prefix_tokens']);adapter.load_state_dict(prefix['adapter_state'])
    params=list(core.parameters())+list(reader.parameters())+list(adapter.parameters())
    opt=torch.optim.AdamW(params,lr=.001,weight_decay=.01);opt.load_state_dict(ck['optimizer'])
    checks={name+'_exact':equal(model.state_dict(),ck[name]) for name,model in [('core',core),('reader',reader),('adapter',adapter)]}
    checks['populated_adam_restore_exact']=equal(opt.state_dict(),ck['optimizer']) and meta['populated_adam_states']>0
    py=random.Random();py.setstate(ck['sample_rng']);first=[py.randrange(2**31) for _ in range(64)]
    py.setstate(ck['sample_rng']);checks['python_rng_continuation_exact']=first==[py.randrange(2**31) for _ in range(64)]
    generator=torch.Generator(device='cpu');generator.set_state(ck['torch_rng'].cpu());first=torch.rand(64,generator=generator)
    generator.set_state(ck['torch_rng'].cpu());checks['torch_cpu_rng_continuation_exact']=torch.equal(first,torch.rand(64,generator=generator))
    for record in sources:verify_pin(record)
    verify_bundle(bundle)
    raw=dict(seed=meta['seed'],updates=meta['updates'],bundle=b['version'],resume_sha256=a['resume']['sha256'],checks=checks,passed=sum(checks.values()),total=len(checks),populated_adam_states=meta['populated_adam_states'],rng_draws_per_repeat=64,repeat_noise=0,cuda_rng_saved_states=len(ck['cuda_rng']),cuda_continuation_tested=False,optimizer_steps=0,optimizer_step_continuation_tested=False,LM_loaded=False,semantic_English='NOT SHOWN',seconds=time.monotonic()-start)
    save_new(out/'raw.json',raw);print(json.dumps(raw));assert all(checks.values()) and raw['seconds']<120
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.bundle,a.out)
