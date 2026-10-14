import time, json, torch
torch.set_num_threads(1)
from custom_io import data as D
from custom_io.data import Dataset, collate, load_rows, to_device
from custom_io.models import load_model
D.set_max_ans(8)
m=load_model('/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/D1b/checkpoint-3500.pt')
rows=load_rows('/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/eval/logic_gate.jsonl',keep=None)[:64]
ds=Dataset(rows,m.vocab)
with torch.no_grad():
    b=to_device(collate([ds[i] for i in range(64)]),torch.device('cpu'))
    t=time.time(); o=m.run(b); print('free',time.time()-t)
    g=m.gold(b['rows'],torch.device('cpu'))
    t=time.time(); o2=m.run(b,gold=g); print('tf',time.time()-t)
    print('lword diff',(o['lword']-o2['lword']).abs().max().item(),'lmode diff',(o['lmode']-o2['lmode']).abs().max().item())
    print('free ops any>0', sum(int((s[0].argmax(-1)>0).sum()) for s in o['steps']), 'tf ops',sum(int((s[0].argmax(-1)>0).sum()) for s in o2['steps']))
    print('gold mode', g['mode'][:10], g['word'].sum(1)[:10], g['op'].sum())
    L,aux=m.loss(b)
    print('loss',float(L),{k:float(v) for k,v in aux.items()})
