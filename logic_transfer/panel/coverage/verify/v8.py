import json,re,collections
NEG=re.compile(r"\b(not|never|isn't|non-)\b|\bsurely not\b",re.I)
def run(fn,depth0=True):
    c=collections.Counter(); tot=0;ok=0;ok_stated=0;stated=0;n_unk_ok=0
    for l in open(f'lt2/rows/eval/{fn}.jsonl'):
        x=json.loads(l); m=x['meta']
        if m['depth'] not in (0,None) and not fn.startswith('placebo'): continue
        if m['depth']!=0 and fn=='logic_gate': continue
        q=m['query']; neg=q.startswith('~'); mm=re.match(r'~?([a-z]+)\(([a-z]+)\)',q); w,e=mm.group(1),mm.group(2)
        p=x['prompt']; p=re.sub(r'\s*\([a-z/]+\)\s*$','',p)
        sents=[s for s in re.split(r'(?<=[.?:!])\s+',p)]
        # context sentences: those not containing '?' and not the last; drop sentence w/ 'unknown' (query framing)
        ctx=[s for s in sents[:-1] if 'unknown' not in s.lower()]
        hits=[s for s in ctx if re.search(r'\b'+e+r'\b',s,re.I) and re.search(r'\b'+w+r'\b',s,re.I)]
        # exclude rule sentences: rule sentences contain predicate but not as "Entity is"; use meta ctx parse: facts only
        if not hits: pred='unknown'
        else:
            s=hits[0]; sneg=len(NEG.findall(s))%2==1
            pred='true' if sneg==neg else 'false'
        ok+= pred==m['label']; tot+=1
    return fn,tot,round(ok/tot,3)
for fn in ['placebo_dev','placebo_test_wording','logic_gate']: print(run(fn))
