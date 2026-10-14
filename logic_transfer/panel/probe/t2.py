import sys, json, collections
sys.path.insert(0,'.')
import cf
from probelib import *
for fn in ['logic_gate','placebo_dev','logic_dev']:
    rows=load_rows(f'{ROWS}/eval/{fn}.jsonl',keep=None)
    ok=0; cnt=collections.Counter(); exps=collections.defaultdict(collections.Counter)
    for r in rows:
        b=cf.build(r, rows)
        if b is None: continue
        ok+=1
        for k,v in b.items():
            cnt[k]+=len(v)
            for x in v: exps[k][x['exp']]+=1
    print(fn,len(rows),'parsed',ok,dict(cnt))
    for k in exps: print('  ',k,dict(exps[k]))
r=load_rows(f'{ROWS}/eval/logic_gate.jsonl',keep=None)[1]
b=cf.build(r,[r])
print(r['prompt'],r['meta']['label'])
for k,v in b.items():
    for x in v: print(k,'|',x['prompt'],'|',x['exp'])
