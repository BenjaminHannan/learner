"""Independent verifier: official evalx.evaluate (model.generate) on D1b3500; own text-level counterfactuals labelled by logicgen.checker.
python v1.py  (PYTHONPATH=<wt>/lt)"""
import json, re, random, sys, pickle, collections, copy
import numpy as np, torch
torch.set_num_threads(1)
from custom_io.models import load_model
from custom_io.evalx import evaluate, norm
from logicgen import checker as C
SP='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
OUT=SP+'/panel/probe/verify'
CK=sys.argv[1] if len(sys.argv)>1 else SP+'/lt2/diag/D1b/checkpoint-3500.pt'
TAG=sys.argv[2] if len(sys.argv)>2 else 'D1b3500'
m=load_model(CK,'cpu')
def load(f): return [json.loads(l) for l in open(f'{SP}/lt2/rows/eval/{f}.jsonl')]
def run(rows):
    r=evaluate(m,rows,64,torch.device('cpu'),return_preds=True)
    return [norm(r['preds'][x['id']]) for x in rows], r['correct']
SUF=re.compile(r' \((\w+)/(\w+)/(\w+)\)$')
def ent_of(row):
    q=row['meta']['query']; return re.match(r'~?\w+\((\w+)\)',q).group(1)
def split_sents(body):
    return re.findall(r'[^.!?]*[.!?]?\s*', body)  # keeps whitespace
res={}
out={}
for fname in ['logic_gate','placebo_dev']:
    rows=load(fname)
    preds,c=run(rows)
    print(fname,'official evaluate correct',c,len(rows),flush=True)
    res[fname]=(c,len(rows))
    pm={r['id']:p for r,p in zip(rows,preds)}
    rng=random.Random(7)
    sub=rng.sample(rows,400)
    # E1 entity swap in the question (last occurrence of capitalised name)
    e1=[];e2=[]
    for r in sub:
        name=ent_of(r); N=name.capitalize(); p=r['prompt']
        k=p.rfind(N)
        suf=SUF.search(p)
        if k<0 or k<len(p)-len(suf.group(0))-70: continue
        # label by checker with fresh entity
        prog=r['meta']['program']
        qlit=r['meta']['query']
        newprog=re.sub(r'Q (~?\w+)\('+name+r'\)', r'Q \1(zzfresh)', prog)
        lab=C.run_program(newprog)
        if lab=='error': continue
        q=dict(r); fresh=(('Zq'+'vkxj'*3)[:len(N)]); q['prompt']=p[:k]+fresh+p[k+len(N):]; q['id']=r['id']+'-e1'; q['answer']=lab; q['accepted']=[lab]
        e1.append((r,q))
    # E2: delete every sentence (not the question) containing the query entity name
    for r in sub:
        if r['meta']['label']=='unknown': continue
        name=ent_of(r); N=name.capitalize(); p=r['prompt']; suf=SUF.search(p)
        body=p[:suf.start()]; ss=[s for s in split_sents(body) if s.strip()]
        qi=len(ss)-1  # question is last sentence
        keep=[];rem=0
        for i,s in enumerate(ss):
            if i!=qi and re.search(r'\b'+N+r'\b',s): rem+=1; continue
            keep.append(s)
        facts,rules,qq=C.parse_program(r['meta']['program'])
        nf=[f for f in facts if f[2]!=name]; nr=[x for x in rules if x.ent!=name]
        if rem!=(len(facts)-len(nf))+(len(rules)-len(nr)) or rem==0: continue
        lab=C.solve(nf,nr,qq).label
        np_=''.join(keep)+suf.group(0)
        if len(np_)<20: continue
        q=dict(r); q['prompt']=np_; q['id']=r['id']+'-e2'; q['answer']=lab; q['accepted']=[lab]
        e2.append((r,q))
    for nm,pairs in (('entswap',e1),('del_entity_sents',e2)):
        if not pairs: continue
        pp,_=run([q for _,q in pairs])
        orig=[pm[r['id']] for r,_ in pairs]
        n=len(pairs)
        unch=np.mean([a==b for a,b in zip(orig,pp)])
        # shuffled baseline
        sh=np.mean([orig[i]==pp[(i+17)%n] for i in range(n)])
        punk0=np.mean([a=='unknown' for a in orig]); punk1=np.mean([b=='unknown' for b in pp])
        newlab=collections.Counter(q['answer'] for _,q in pairs)
        acc_new=np.mean([b==q['answer'] for (_,q),b in zip(pairs,pp)]); acc_old=np.mean([a==r['answer'] for (r,_),a in zip(pairs,orig)])
        # rows where orig answer was true/false: flip to opposite?
        tf=[(a,b) for a,b in zip(orig,pp) if a in('true','false')]
        flip=np.mean([a!=b and b in('true','false') for a,b in tf])
        d=dict(n=n,unchanged=float(unch),shuf_base=float(sh),punk_before=float(punk0),punk_after=float(punk1),newlab=dict(newlab),acc_new=float(acc_new),acc_old=float(acc_old),opp_flip=float(flip))
        print(fname,nm,d,flush=True); out[f'{fname}.{nm}']=d
json.dump(dict(res=res,cf=out),open(f'{OUT}/v1_{TAG}.json','w'),indent=1)
