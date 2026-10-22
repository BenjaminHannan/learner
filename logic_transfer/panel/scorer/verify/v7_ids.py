import json, collections
D='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
ev={}
for f in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']:
    ev[f]=[json.loads(l) for l in open(D+'eval/'+f+'.jsonl')]
allid=collections.Counter(r['id'] for rs in ev.values() for r in rs)
print('eval id dups across eval files',sum(1 for v in allid.values() if v>1))
evp={}
for f,rs in ev.items():
    for r in rs: evp.setdefault(r['prompt'],[]).append(f)
print('eval prompt dup across files',sum(1 for v in evp.values() if len(set(v))>1), 'within', sum(1 for v in evp.values() if len(v)>len(set(v))))
ids=set(allid)
hit_id=collections.Counter(); hit_p=collections.Counter(); hit_core=collections.Counter()
import re
core=lambda p: re.sub(r' \([a-z/]+\)$','',p)
evc={}
for f,rs in ev.items():
    for r in rs: evc.setdefault(core(r['prompt']),set()).add(f)
for f in ['logic_train','placebo_train']:
    for l in open(D+f+'.jsonl'):
        r=json.loads(l)
        if r['id'] in ids: hit_id[f]+=1
        if r['prompt'] in evp: hit_p[f]+=1
        c=core(r['prompt'])
        if c in evc:
            for g in evc[c]: hit_core[(f,g)]+=1
print('train id in eval',dict(hit_id),'train prompt in eval',dict(hit_p),'train prompt(core, ignoring option order) in eval',dict(hit_core))
