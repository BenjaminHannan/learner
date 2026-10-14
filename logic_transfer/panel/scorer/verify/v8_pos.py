import json, collections, torch
torch.set_num_threads(1)
from custom_io.data import load_rows
from custom_io.evalx import evaluate
from custom_io.models import load_model
D='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/data/sk200k/dev/'
rows=load_rows(D+'in_dist.jsonl')
by=collections.defaultdict(list)
for r in rows: by[r['family']].append(r)
m=load_model('/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt','cpu')
for fam in ['prop_eval','copy_word','syllogism','object_track']:
    rs=by[fam][:60]
    r=evaluate(m,rs,32,torch.device('cpu'),return_preds=True)
    ans=collections.Counter(x['answer'] for x in rs)
    print(fam,r['correct'],r['n'],dict(ans.most_common(4)),'sample prompt:',rs[0]['prompt'][-90:],'->',rs[0]['answer'],flush=True)
