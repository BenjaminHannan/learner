"""Verifier V5: own loss/grad path check on the PARENT with 32 logic rows (forward+backward only, no optimizer)."""
import json, random, itertools, numpy as np, torch
torch.set_num_threads(1)
from custom_io import data as D
from custom_io.data import Dataset, collate
from custom_io.models import load_model, progparse as pp
D.set_max_ans(8)
SCR='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
m=load_model('/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt'); m.train()
rows=[]
for i,l in enumerate(open(SCR+'/lt2/rows/logic_train.jsonl')):
    if i%4000==5 and len(rows)<32:
        r=json.loads(l); rows.append({k:r[k] for k in D.KEEP if k in r})
OPT=['true','false','unknown']
def run(rs):
    ds=Dataset(rs,m.vocab); b=D.to_device(collate([ds[i] for i in range(len(rs))]),'cpu')
    m._drill_rng=random.Random('x'); m.zero_grad(set_to_none=True)
    tot,aux=m.loss(b); tot.backward()
    g={}
    for n,p in m.named_parameters():
        if p.grad is not None: g[n]=p.grad.clone()
    return float(tot),{k:float(v) for k,v in aux.items() if k in('word','mode','prog','gen','span_call','span_ans','stop')},g
t0,a0,g0=run(rows)
print('gold: total %.4f'%t0,a0)
gn=lambda g: float(torch.sqrt(sum((v**2).sum() for v in g.values())))
print('global grad norm',gn(g0))
# params with nonzero grad by prefix
pre={}
for n,v in g0.items(): pre.setdefault(n.split('.')[0],0.0); pre[n.split('.')[0]]+=float((v**2).sum())
print({k:round(v**.5,3) for k,v in sorted(pre.items())})
# label-swapped copy WITH NEW IDS
rs=[]; rng=np.random.RandomState(1)
for r in rows:
    r2=dict(r); a=OPT[(OPT.index(r['answer'])+1+rng.randint(0,2))%3]; r2['id']='sw|'+r['id']; r2['answer']=a; r2['accepted']=[a]; rs.append(r2)
t1,a1,g1=run(rs); print('all-wrong labels (new ids): total %.4f'%t1,a1)
d=torch.sqrt(sum(((g0[n]-g1.get(n,torch.zeros_like(g0[n])))**2).sum() for n in g0)); print('|g_gold-g_wrong|',float(d))
# X3: same id, different answer -> cache serves old target?
rs2=[]
for r,r_ in zip(rows,rs):
    r2=dict(r); r2['answer']=r_['answer']; r2['accepted']=[r_['answer']]; rs2.append(r2)
t2,a2,_=run(rs2); print('same ids, answer swapped: total %.4f (equals gold-run %.4f ? %s)'%(t2,t0,abs(t2-t0)<1e-6))
