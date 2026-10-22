# Own re-run: D1b-3500, own batching (shuffled, bs 32), own decode (talk(return_modes)), own hit test, compare to saved score.json;
# plus train-row vs eval-row comparison of the word-pointer loss (forward only, no optimiser).
import json, random, sys, time, collections
import numpy as np, torch
torch.set_num_threads(1)
from custom_io.data import Dataset, collate, load_rows, word_spans
from custom_io.models import load_model, progparse as pp
CK='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/D1b/checkpoint-3500.pt'
SAVED=json.load(open('/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/score-D1b-u3500/score.json'))['splits']
E='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/eval/'
TR='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/logic_train.jsonl'
m=load_model(CK,'cpu'); print('loaded',type(m).__name__,'training',m.training,flush=True)
def batches(rows,bs,seed):
    idx=list(range(len(rows))); random.Random(seed).shuffle(idx)
    ds=Dataset(rows,m.vocab,strict=False)
    for s in range(0,len(idx),bs):
        ii=idx[s:s+bs]; yield ii,collate([ds[i] for i in ii])
out={}
which=sys.argv[1:] or ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']
for f in which:
    rows=load_rows(E+f+'.jsonl',keep=None); t=time.time()
    pred=[None]*len(rows); modes=[None]*len(rows); nll=[]; goldmass_arg=0
    with torch.no_grad():
        for ii,b in batches(rows,32,7):
            st=m.state(b); o,md=m.talk(st,b,return_modes=True)
            for i,p,q in zip(ii,o,md): pred[i]=p; modes[i]=q
    hit=[' '.join(p.strip().lower().split())==r['answer'] for p,r in zip(pred,rows)]
    c=sum(hit); n=len(rows)
    bl=collections.defaultdict(lambda:[0,0])
    for h,r in zip(hit,rows): bl[r['answer']][0]+=h; bl[r['answer']][1]+=1
    pw=collections.Counter(' '.join(p.strip().lower().split()) for p in pred)
    sv=SAVED[f]
    out[f]=dict(correct=c,n=n,saved_correct=sv['correct'],match=c==sv['correct'],by_label={k:v[0] for k,v in bl.items()},
       saved_by_label={k:v['correct'] for k,v in sv['by_label'].items()},pred_words=dict(pw),modes=dict(collections.Counter(modes)),secs=round(time.time()-t))
    print(f,out[f],flush=True)
json.dump(out,open('v3_rerun.json','w'),indent=1)
