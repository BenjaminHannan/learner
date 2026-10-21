import json, sys, os, time
import torch
sys.path.insert(0, '/home/user/pt94')
from custom_io.data import load_rows, Dataset, collate, to_device
from custom_io.evalx import is_hit
from custom_io.models import load_model
torch.set_num_threads(4)
M0='/tmp/claude-0/-home-user/6e3fd48b-869d-5cdd-b158-7710e164d592/scratchpad/m0/ck/'
rows = load_rows('/home/user/sk200k/dev/in_dist.jsonl')
name=sys.argv[1]; out=sys.argv[2]
m = load_model(M0+name+'.pt').eval()
ds = Dataset(rows, m.vocab, strict=False)
order = sorted(range(len(rows)), key=lambda i: len(rows[i]['prompt']))
res=[None]*len(rows)
with torch.no_grad():
  for s in range(0,len(order),128):
    ids=order[s:s+128]
    b=collate([ds[i] for i in ids])
    o=m.run(b)
    st=m.state_of(o)
    ans,modes=m.talk(st,b,return_modes=True)
    for j,i in enumerate(ids):
        res[i]=dict(calls=[list(c[1:]) for c in o['calls'][j]], ans=ans[j], mode=modes[j], hit=int(is_hit(ans[j],rows[i])))
json.dump(res,open(out,'w'))
print(name, sum(r['hit'] for r in res))
