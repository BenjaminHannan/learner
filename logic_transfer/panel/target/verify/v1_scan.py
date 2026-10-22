"""Verifier V1: independent streaming scan of all converted row files. No torch model; only checkpoint's char list."""
import json, re, sys, collections, torch
torch.set_num_threads(1)
from custom_io.data import word_spans
SCR='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
ck=torch.load('/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt',map_location='cpu',weights_only=True)
chars=set(ck['chars']); print('vocab chars',len(chars))
del ck
R=SCR+'/lt2/rows'
files={'logic_train':R+'/logic_train.jsonl','placebo_train':R+'/placebo_train.jsonl'}
for n in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']: files[n]=f'{R}/eval/{n}.jsonl'
allids=collections.Counter(); 
OPT={'true','false','unknown'}
for n,p in files.items():
    c=collections.Counter(); lab=collections.Counter(); dup=collections.Counter(); duplab=collections.defaultdict(collections.Counter)
    slot=collections.defaultdict(collections.Counter); maxw=0; maxl=0
    N=0
    for line in open(p):
        r=json.loads(line); N+=1
        allids[(n.split('_')[0],r['id'])]+=1
        pr=r['prompt']; a=r['answer']
        if set(pr)-chars: c['unk']+=1
        if len(pr)>208: c['over208']+=1
        if len(r['accepted'])!=1 or r['accepted'][0]!=a: c['accepted_differs']+=1
        if r['steps']!=['none']: c['steps_not_none']+=1
        if re.search(r'\d',pr): c['digit']+=1
        sp=word_spans(pr); w=[pr[s:e].lower() for s,e in sp]
        maxw=max(maxw,len(w)); maxl=max(maxl,len(pr))
        if len(w)>64: c['words>64']+=1
        # suffix
        m=re.search(r' \((\w+)/(\w+)/(\w+)\)$',pr)
        if not m or set(m.groups())!=OPT: c['bad_suffix']+=1; continue
        order=m.groups()
        # suffix words are the last 3 words?? check separately
        if w[-5:]!=['(',order[0],'/',order[1],'/'][:0] and True:
            pass
        if [x for x in w[-7:] if x in OPT]!=list(order): c['suffix_not_last_words']+=1
        gold=[i for i,x in enumerate(w) if x==a]
        k=len(gold); dup[k]+=1; duplab[k>1][a]+=1
        lab[a]+=1
        slot[order.index(a)][a]+=1
        if r['meta'].get('label')!=a: c['meta_label_differs']+=1
    print(n,N,dict(c),'labels',dict(lab),'goldcount',dict(dup),'maxw',maxw,'maxlen',maxl)
    print('   slot-of-gold by label',{s:dict(v) for s,v in sorted(slot.items())})
    print('   dup rows label share',{k:dict(v) for k,v in duplab.items()})
d=[k for k,v in allids.items() if v>1]; print('duplicate ids within file:',len(d))
ids_l={i for (f,i) in allids if f=='logic'}; ids_p={i for (f,i) in allids if f=='placebo'}
print('logic/placebo id overlap',len(ids_l&ids_p))
# vs sk200k
sk=set()
for line in open(SCR+'/data/sk200k/train.jsonl'):
    sk.add(line.split('"id": "',1)[1].split('"',1)[0]) if '"id": "' in line else None
print('sk200k ids',len(sk),'overlap with converted',len(sk&{i for (_,i) in allids}))
