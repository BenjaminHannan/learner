import json, sys, time, torch
sys.path.insert(0, '/home/user/pt94')
from custom_io.data import load_rows
from custom_io.evalx import evaluate, is_hit
from custom_io.models import load_model
ck, path, out = sys.argv[1:4]
torch.set_num_threads(2)
rows = load_rows(path); m = load_model(ck).eval(); t=time.time()
e = evaluate(m, rows, 128, 'cpu', return_preds=True)
json.dump(dict(hits=[int(is_hit(e['preds'][r['id']], r)) for r in rows], family=[r['family'] for r in rows]), open(out,'w'))
print(out, round(time.time()-t), flush=True)
