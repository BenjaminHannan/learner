"""Unregistered throughput diagnostic; generated puzzle data, no test panel."""
import json, random, sys, time
from pathlib import Path
import torch
import claude_rsn358i_run as I
R,E=I.R,I.E
out=Path('artifacts/codex-numbers-20260927/diagnostics');out.mkdir(parents=True,exist_ok=True)
records=[]
for width,batch in [(64,64),(128,64),(128,128)]:
    torch.manual_seed(9276192);rng=random.Random(9276192)
    R.ARMS['loop']=dict(d=width,layers=2,heads=8)
    net=R.Net('loop').to('mps');opt=torch.optim.AdamW(net.parameters(),lr=3e-4,weight_decay=.1,betas=(.9,.95))
    pools=[[E.make_sum(rng,4) for _ in range(batch)], [E.latin_item(rng,*E.make_latin_base(rng,5)) for _ in range(batch)], [E.number_item(rng,[1,2,3,4],24,E.B1.solve([1,2,3,4],24)) for _ in range(batch)]]
    data=[]
    for items in pools:
        t,s,y,_=R.tensors(items,'mps');env=torch.zeros(batch,dtype=torch.long,device='mps');data.append((t,s,y,env))
    start=time.monotonic()
    for i in range(18):
        t,s,y,env=data[i%3]
        outs=net.loop_train(t,s,env,5,3)
        loss=sum(R.ce_and_exact(lg,s,y)[0]+.5*torch.nn.functional.binary_cross_entropy_with_logits(q,R.ce_and_exact(lg,s,y)[1]) for lg,q in outs)/3
        opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),1.);opt.step();torch.mps.synchronize()
        if i==2:start=time.monotonic()
    rec=dict(width=width,batch=batch,weights=sum(p.numel() for p in net.parameters()),seconds_per_step=(time.monotonic()-start)/15,device='mps',dtype='float32',torch=torch.__version__)
    records.append(rec);print(json.dumps(rec),flush=True)
    del net,opt,outs,loss,data,pools
    torch.mps.empty_cache()
(out/'throughput.json').write_text(json.dumps(records,indent=2)+'\n')
