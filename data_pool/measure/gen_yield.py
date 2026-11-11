# Needs: origin/claude/b1-teach-gen-data at $B1_TEACH (b1_teach/) and transformers (LFM tokenizer). Run: python3 gen_yield.py 300000 12 > out.json
import os, sys, json, random, collections
sys.path.insert(0, os.environ.get('B1_TEACH','/tmp/b1t/b1_teach')); import gen_english as G
N=int(sys.argv[1]); kinds=int(sys.argv[2])
r=random.Random(777); P=G.Pools("train", G.BLOCK_R6)
fl,nl=(G.FAMS,G.FAM_NAMES) if kinds==6 else (G.FAMS12,G.FAM_NAMES12)
seen=set(); st=collections.defaultdict(lambda: collections.Counter()); chars=0; qs_total=0
curve={}
for i in range(N):
    j=i%len(fl)
    fam,s,para,qs=fl[j](r,P); c=st[nl[j]]; c['draw']+=1
    if any(not x["canonical_answer"] or not x["question"] for x in qs): c['bad']+=1; continue
    if s in seen: c['dup_source']+=1; continue
    if not G.fits([t+" "+x["question"] for t in (s,para) for x in qs]): c['too_long']+=1; continue
    seen.add(s); c['kept']+=1; qs_total+=len(qs); chars+=len(s)+sum(len(x["question"])+len(x["canonical_answer"]) for x in qs)
    if len(seen) in (1000,10000,50000,100000,200000,400000): curve[len(seen)]=sum(v['dup_source'] for v in st.values())
print(json.dumps(dict(kinds=kinds,N=N,unique_sources=len(seen),questions=qs_total,chars=chars,curve_dups_at=curve,per_family={k:dict(v) for k,v in st.items()}),indent=1))
