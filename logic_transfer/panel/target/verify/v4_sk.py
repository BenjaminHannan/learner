import json, itertools, collections, re
from custom_io.models import progparse as pp
SK='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/data/sk200k/train.jsonl'
rows=[]
for i,l in enumerate(open(SK)):
    if i%4==0:
        r=json.loads(l); rows.append({k:r[k] for k in ('id','prompt','answer','accepted','family','level','stage','variant','steps') if k in r})
cov=pp.coverage(rows); print(cov['all'])
for f,c in cov['by_family'].items():
    if c['WORD']>0: print(f,c)
# word-mode rows where an option list appears in prompt?
ex=collections.defaultdict(list)
for r in rows:
    t=pp.row_targets(r)
    if t['mode']==1 and len(ex[r['family']])<2: ex[r['family']].append((r['prompt'][-110:],r['answer']))
for f,v in ex.items(): print(f,v)
