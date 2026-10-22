import sys, json
sys.path.insert(0,'/home/user/wtfar')
from domain.far import learn_probe as L, join_gap as JG
import torch
from custom_io.models import load_model
S='/tmp/claude-0/-home-user/7b4cc9f0-8b9c-5e78-99b7-c110382faf97/scratchpad/'
D=S+'far-data/'
tag=sys.argv[1]
sets=L.eval_sets(L.load_jsonl(D+'learn/train-rows-l5.jsonl'),'l5',L.L5_SEED,probe_path=D+'diag/sheet-probe.jsonl',l5_path=D+'learn/eval-rows-l5.jsonl')
torch.set_num_threads(2)
m=load_model(S+f'ckpt/{tag}/checkpoint.pt').eval()
out={}
for c in ['HO','HPO','HP','S','S5','F4-two']:
    recs=JG.audit(m,sets[c]); out[c]=recs
    s=JG.summarize(recs); print(tag,c,'W',s['W'],'P',s['P'],'T',s['T'],'n',s['rows'],flush=True)
json.dump(out,open(S+f'out/audit-{tag}.json','w'))
