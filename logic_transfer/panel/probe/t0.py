import time, json, torch
torch.set_num_threads(1)
from custom_io import data as D
from custom_io.data import Dataset, collate, load_rows, to_device
from custom_io.models import load_model
D.set_max_ans(8)
t=time.time()
m=load_model('/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/D1b/checkpoint-3500.pt')
print('load',time.time()-t, type(m).__name__, m.n_params(), m.span_copy, m.ans_drill, m.n_loops, m.training)
rows=load_rows('/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/eval/logic_gate.jsonl',keep=None)[:64]
ds=Dataset(rows,m.vocab,strict=False)
t=time.time()
with torch.no_grad():
    b=to_device(collate([ds[i] for i in range(64)]),torch.device('cpu'))
    o=m.run(b); st=m.state_of(o)
    ans,modes=m.talk(st,b,return_modes=True)
print('fwd',time.time()-t, ans[:5], modes[:10], [x.shape for x in st])
print(len(o['steps']), o['steps'][0][0].argmax(-1)[:10])
