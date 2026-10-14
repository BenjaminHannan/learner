import json,re,random,sys,collections
import numpy as np, torch
torch.set_num_threads(1)
from custom_io.models import load_model
from custom_io.evalx import evaluate, norm
SP='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
m=load_model(SP+'/lt2/diag/D1b/checkpoint-3500.pt','cpu')
SUF=re.compile(r' \((\w+)/(\w+)/(\w+)\)$')
rows=[json.loads(l) for l in open(SP+'/lt2/rows/eval/logic_gate.jsonl')]
rng=random.Random(3); sub=rng.sample(rows,500)
def run(rs):
    r=evaluate(m,rs,64,torch.device('cpu'),return_preds=True); return [norm(r['preds'][x['id']]) for x in rs]
base=run(sub)
alt=[]
for r in sub:
    s=SUF.search(r['prompt']); w=list(s.groups())
    while True:
        p=w[:]; rng.shuffle(p)
        if p!=w: break
    q=dict(r); q['prompt']=r['prompt'][:s.start()]+' ('+'/'.join(p)+')'; alt.append(q)
pa=run(alt)
print('acc base',np.mean([a==r['answer'] for a,r in zip(base,sub)]),'acc perm',np.mean([a==r['answer'] for a,r in zip(pa,sub)]))
print('same word',np.mean([a==b for a,b in zip(base,pa)]),'shuf baseline',np.mean([base[i]==pa[(i+11)%500] for i in range(500)]))
# slot same
def slot(r,p):
    return list(SUF.search(r['prompt']).groups()).index(p)
print('same slot',np.mean([slot(r,a)==slot(q,b) for r,q,a,b in zip(sub,alt,base,pa)]))
# trivial: which word-set. majority word
print(collections.Counter(base),collections.Counter(pa))
