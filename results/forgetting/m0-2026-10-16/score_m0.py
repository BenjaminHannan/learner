import json, sys, os, time
import torch
sys.path.insert(0, '/home/user/pt94')
from custom_io.data import load_rows
from custom_io.evalx import evaluate, is_hit
from custom_io.models import load_model
ck, split, out = sys.argv[1], sys.argv[2], sys.argv[3]
torch.set_num_threads(1)
rows = load_rows(f'/home/user/sk200k/dev/{split}.jsonl')
t = time.time()
m = load_model(ck).eval()
e = evaluate(m, rows, 128, 'cpu', return_preds=True)
hits = [int(is_hit(e['preds'][r['id']], r)) for r in rows]
json.dump(dict(ck=ck, split=split, n=len(rows), exact=e['exact'], hits=hits, ids=[r['id'] for r in rows],
               family=[r['family'] for r in rows], steps=[r.get('steps') for r in rows], level=[r.get('level') for r in rows],
               preds=[e['preds'][r['id']] for r in rows], secs=round(time.time()-t,1)), open(out, 'w'))
print(ck.split('/')[-1], split, sum(hits), len(rows), round(100*sum(hits)/len(rows), 2), e['exact'], round(time.time()-t,1), flush=True)
