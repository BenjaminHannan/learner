# Forward-only: does the free-run (scorer) path give the same word-pointer loss as the teacher-forced training loss() on the same rows?
import json, random, torch, numpy as np
torch.set_num_threads(1)
from custom_io.data import Dataset, collate, load_rows
from custom_io.models import load_model, progparse as pp
CK='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/D1b/checkpoint-3500.pt'
D='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
m=load_model(CK,'cpu')
def seg(rows,name,mode_train):
    ds=Dataset(rows,m.vocab,strict=False); res=dict(loss=[],lword_free=[],acc=[],lmode=[]); 
    m.train(mode_train)
    with torch.no_grad():
        for s in range(0,len(rows),32):
            b=collate([ds[i] for i in range(s,min(s+32,len(rows)))])
            tot,aux=m.loss(b); res['loss'].append(float(tot)*len(b['rows'])); res['lmode'].append(float(aux['mode'])*len(b['rows']))
            g=m.gold(b['rows'],torch.device('cpu'))
            o=m.run(b)   # free run, no gold
            lg=o['lword'].float(); gm=g['word']
            nll=-(torch.logsumexp(lg.masked_fill(~gm,-1e9),-1)-torch.logsumexp(lg,-1))
            res['lword_free'].extend(nll.tolist())
            pr=lg.argmax(-1); res['acc'].extend([bool(gm[i,pr[i]]) for i in range(len(pr))])
    m.eval()
    n=len(rows)
    print(name,'train_mode' if mode_train else 'eval_mode','n',n,'loss()/row',round(sum(res['loss'])/n,4),'free-run lword NLL',round(np.mean(res['lword_free']),4),'ptr acc',round(np.mean(res['acc']),4),flush=True)
tr=[]
for i,l in enumerate(open(D+'logic_train.jsonl')):
    if i>=640: break
    tr.append(json.loads(l))
for r in tr: r.pop('meta',None)
gate=load_rows(D+'eval/logic_gate.jsonl')
random.Random(1).shuffle(gate); gate=gate[:640]
seg(tr,'logic_train[:640]',True); seg(tr,'logic_train[:640]',False)
seg(gate,'gate[640 random]',True); seg(gate,'gate[640 random]',False)
