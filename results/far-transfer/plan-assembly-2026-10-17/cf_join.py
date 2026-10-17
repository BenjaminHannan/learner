"""Counterfactual: HO/HPO items with a cell-arithmetic piece, join '*' -> '+' (same pieces, (K)+(J) is a trained layout). Free run + TF."""
import json,re,sys,collections
sys.path.insert(0,'.')
import torch
from custom_io.models import load_model
from domain.mode import greedy
from domain.far import p2_diag as P
from domain.far import join_gap as JG
from domain.tools import sheet
CA=re.compile(r'[AB]\d[+\-][AB]\d\*\d+')
torch.set_num_threads(2)
def roles(prompt):
    f=prompt.split(';',1)[1].strip()[1:]; op,K,J,_=JG.split_formula(f)
    nK=len(sheet.evaluate(JG.piece_prompt(prompt,K))['steps']); nJ=len(sheet.evaluate(JG.piece_prompt(prompt,J))['steps'])
    return K,J,nK,nJ
def score(m,prompts):
    rows=[]
    for p in prompts:
        ev=sheet.evaluate(p); rows.append(dict(prompt=p,steps=[list(s) for s in ev['steps']],tool_value=str(ev['value'])))
    fr=greedy(m,prompts); tf=P.teacher_forced(m,rows)
    acc=collections.defaultdict(lambda:[0,0]); hits=0
    for r,(calls,pred),res in zip(rows,fr,tf):
        hits+= pred.strip()==r['tool_value']
        K,J,nK,nJ=roles(r['prompt']); n=len(r['steps'])
        side='K' if CA.search(K) else 'J'
        if res is None: acc['TF none'][1]+=1; continue
        g,mc=res
        for k in range(n):
            role='R0' if k==0 else 'K_later' if k<nK else 'TRANS' if k==nK else 'J_later' if k<n-1 else 'JOIN'
            ok=JG.same_call(tuple(mc[k])+('',),tuple(r['steps'][k][:3])+('',))
            acc[(side,role)][0]+=ok; acc[(side,role)][1]+=1
    return hits,len(rows),acc
for tag in sys.argv[1:]:
    m=load_model(f'ck/{tag}/checkpoint.pt').eval()
    ev=[json.loads(l) for l in open('inputs/far/eval-rows-l5.jsonl')]
    orig=[r['prompt'] for r in ev if r['split'] in('HO','HPO') and CA.search(r['prompt'].split('=',1)[1])]
    cf=[p.replace(')*(',')+(') for p in orig]
    assert all(')+(' in p for p in cf)
    for name,ps in (('(K)*(J) original',orig),('(K)+(J) counterfactual',cf)):
        h,n,acc=score(m,ps)
        print(f'{tag} {name}: hits {h}/{n}')
        for side in 'KJ':
            print('    CA in',side,'  '.join(f'{r}:{acc[(side,r)][0]}/{acc[(side,r)][1]}' for r in ('R0','K_later','TRANS','J_later','JOIN') if acc[(side,r)][1]))
