"""Verifier V2: own forward pass of a checkpoint on eval files; own word-pointer NLL per candidate label, own decode, own permutation test.
usage: python v2_forward.py CKPT TAG   (one checkpoint, 1 thread, batch 50)"""
import json, sys, re, collections, numpy as np, torch
torch.set_num_threads(1)
from custom_io import data as D
from custom_io.data import Dataset, collate, word_spans
from custom_io.models import load_model
D.set_max_ans(8)
SCR='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad'
R=SCR+'/lt2/rows'
ck,tag=sys.argv[1],sys.argv[2]
files=sys.argv[3:] or ['logic_dev','logic_gate','logic_test_deeper','placebo_dev']
m=load_model(ck); m.eval()
OPT=('true','false','unknown')
out={}
rng=np.random.RandomState(0)
for fn in files:
    rows=[json.loads(l) for l in open(f'{R}/eval/{fn}.jsonl')]
    rows=[{k:r[k] for k in D.KEEP if k in r} for r in rows]
    NLL=np.zeros((len(rows),3)); dec_ok=np.zeros(len(rows),bool); gen_ok=np.zeros(len(rows),bool); modes=[]
    top3=np.zeros(len(rows))
    for s in range(0,len(rows),50):
        chunk=rows[s:s+50]
        ds=Dataset(chunk,m.vocab,strict=False)
        b=D.to_device(collate([ds[i] for i in range(len(chunk))]),'cpu')
        with torch.no_grad():
            o=m.run(b)
            lw=o['lword'].float(); lm=o['lmode'].argmax(-1).tolist()
            gtxt=m.generate(b)
        lp=torch.log_softmax(lw,-1)
        for i,r in enumerate(chunk):
            pr=r['prompt']; sp=word_spans(pr)[:64]; w=[pr[a:e].lower() for a,e in sp]
            for j,L in enumerate(OPT):
                pos=[k for k,x in enumerate(w) if x==L]
                NLL[s+i,j]=-torch.logsumexp(lp[i,pos],0).item()
            top3[s+i]=sum(torch.exp(lp[i,[k for k,x in enumerate(w) if x in OPT]]).tolist()) if False else float(torch.exp(torch.logsumexp(lp[i,[k for k,x in enumerate(w) if x in OPT]],0)))
            k=int(lw[i].argmax()); dec_ok[s+i]=(k<len(w) and w[k]==r['answer'])
            gen_ok[s+i]=(gtxt[i].strip().lower()==r['answer'])
            modes.append(lm[i])
    y=np.array([OPT.index(r['answer']) for r in rows])
    gold=NLL[np.arange(len(rows)),y]; wrong=(NLL.sum(1)-gold)/2
    # permutation null: assign each row a uniformly random label, 20000 draws
    obs=gold.mean(); null=np.array([NLL[np.arange(len(rows)),rng.randint(0,3,len(rows))].mean() for _ in range(20000)])
    p_nll=(null<=obs).mean()
    # accuracy null: permute labels across rows
    acc=dec_ok.mean(); nacc=np.array([(dec_ok if False else (np.array([0])[0]==0) and 0) for _ in range(0)])
    # decoded-label-based: predicted word -> label index (or -1)
    pred=np.full(len(rows),-1)
    for i,r in enumerate(rows):
        pass
    out[fn]=dict(n=len(rows),acc_argmax_word=float(acc),acc_generate=float(gen_ok.mean()),agree=float((dec_ok==gen_ok).mean()),
        gold_nll=float(gold.mean()),wrong_nll=float(wrong.mean()),perm_null_mean=float(null.mean()),p_nll=float(p_nll),
        gold_better_rows=int((gold<wrong).sum()),mass_on_options=float(top3.mean()),mode_word_frac=float((np.array(modes)==1).mean()))
    # binomial p for accuracy under 1/3 (exact via normal approx and by label-permutation of the 3x3 table)
    n=len(rows); from math import sqrt
    out[fn]['z_acc']=float((acc-1/3)/sqrt(1/3*2/3/n))
    np.save(f'/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/target/verify/nll_{tag}_{fn}.npy',NLL)
    print(fn,json.dumps(out[fn]),flush=True)
json.dump(out,open(f'/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/target/verify/v2_{tag}.json','w'),indent=1)
