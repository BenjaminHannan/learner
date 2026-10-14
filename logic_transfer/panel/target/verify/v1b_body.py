"""Verifier V1b: does the presence of an option word in the BODY (outside the suffix) predict the label? Own code."""
import json, re, collections, itertools
SCR='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
R=SCR+'/lt2/rows'
files={'logic_train':R+'/logic_train.jsonl'}
for n in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']: files[n]=f'{R}/eval/{n}.jsonl'
for n,p in files.items():
    tab=collections.defaultdict(collections.Counter)
    for i,line in enumerate(open(p)):
        if n=='logic_train' and i>=50000: break
        r=json.loads(line); pr=r['prompt']
        body=re.sub(r' \(\w+/\w+/\w+\)$','',pr).lower()
        toks=re.findall(r"[a-z']+",body)
        key=tuple(int(o in toks) for o in ('true','false','unknown'))
        tab[key][r['answer']]+=1
    print(n)
    for k,v in sorted(tab.items()):
        t=sum(v.values()); print('  body(true,false,unknown)=%s n=%d  share true/false/unknown = %.3f/%.3f/%.3f'%(k,t,v['true']/t,v['false']/t,v['unknown']/t))
