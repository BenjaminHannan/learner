"""Length-only baseline: how well does prompt length (chars) alone predict the label?  Train on 50k logic_train rows (first 50k lines), test on eval files."""
import json, collections, sys, itertools
import numpy as np
SP='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
def rows(path, limit=None):
    for i,l in enumerate(open(path)):
        if limit and i>=limit: break
        r=json.loads(l); yield len(r['prompt']), r['meta']['label'], r
tr=[(L,y) for L,y,_ in rows(f'{SP}/logic_train.jsonl',50000)]
OPT=('true','false','unknown')
for B in (1,4,8):
    tab=collections.defaultdict(collections.Counter)
    for L,y in tr: tab[L//B][y]+=1
    glob=collections.Counter(y for _,y in tr).most_common(1)[0][0]
    print('bin',B, 'train label dist',{k:round(v/len(tr),3) for k,v in collections.Counter(y for _,y in tr).items()})
    for fn in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev']:
        te=[(L,y) for L,y,_ in rows(f'{SP}/eval/{fn}.jsonl')]
        hit=sum((tab[L//B].most_common(1)[0][0] if tab[L//B] else glob)==y for L,y in te)
        print('  ',fn,len(te),'length-only acc',round(hit/len(te),4))
# label vs length in train
tab=collections.defaultdict(collections.Counter)
for L,y in tr: tab[L//20][y]+=1
for k in sorted(tab): print(k*20, dict(tab[k]))
