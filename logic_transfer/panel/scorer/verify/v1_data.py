# Independent (stdlib only) re-derivation of label/position/depth facts from the raw converted eval files.
import json, re, collections, math
E='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/eval/'
R=re.compile(r'\((\w+)/(\w+)/(\w+)\)$')
out={}
for f in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']:
    rows=[json.loads(l) for l in open(E+f+'.jsonl')]
    n=len(rows); lab=collections.Counter(r['answer'] for r in rows)
    pos=collections.Counter(); bad=0; chi_tab=collections.Counter()
    for r in rows:
        m=R.search(r['prompt'])
        if not m: bad+=1; continue
        p=m.groups().index(r['answer']); pos[p]+=1; chi_tab[(r['answer'],p)]+=1
    # chi-square label x position
    rs={l:lab[l] for l in lab}; cs=pos; chi=0
    for l in lab:
        for p in range(3):
            e=lab[l]*cs[p]/n; chi+=(chi_tab[(l,p)]-e)**2/e
    # constant baselines
    depth_none=collections.Counter(r['answer'] for r in rows if r['meta'].get('depth') is None)
    lvl_none=collections.Counter((r['level'],r['answer']) for r in rows if r['meta'].get('depth') is None)
    dl=collections.Counter((r['meta'].get('depth'),r['answer']) for r in rows)
    lvl_vs_depth=sum(1 for r in rows if r['meta'].get('depth') is not None and r['level']!=r['meta']['depth'])
    out[f]=dict(n=n,labels=dict(lab),pos=dict(pos),no_suffix=bad,chi2_df4=round(chi,2),depth_none=dict(depth_none),
      level_when_depth_none=dict((str(k),v) for k,v in lvl_none.items()),level_ne_depth=lvl_vs_depth,
      depth_label={str(k):v for k,v in sorted(dl.items(),key=lambda x:str(x[0]))},
      acc_all_const={l:round(100*lab[l]/n,2) for l in lab},
      acc_pos={p:round(100*pos[p]/n,2) for p in range(3)},
      all_accepted_eq=all(r['accepted']==[r['answer']] for r in rows))
print(json.dumps(out,indent=1))
