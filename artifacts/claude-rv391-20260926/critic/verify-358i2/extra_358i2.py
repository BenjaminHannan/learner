import json, random
from collections import defaultdict
RUN = "/home/user/learner/artifacts/claude-rv391-20260926/critic/run-358i2"
def auc(pos, neg):
    allv = sorted([(v,1) for v in pos]+[(v,0) for v in neg]); i=0; n=len(allv); rs=0.0
    while i<n:
        j=i
        while j<n and allv[j][0]==allv[i][0]: j+=1
        mid=(i+1+j)/2
        rs += mid*sum(1 for t in range(i,j) if allv[t][1]); i=j
    P,N=len(pos),len(neg); return (rs-P*(P+1)/2)/(P*N)
tr=["s1","s2","s3","s4"]
rows={}
for n in tr:
    js=json.load(open(f"{RUN}/critic-{n}.json"))
    rr=[json.loads(l) for l in open(f"{RUN}/critic-{n}.rows.jsonl")]
    rows[n]=rr
    for s in ["p-grids7","p-grids6"]:
        its=[r["item"] for r in rr if r["set"]==s]
        print(n,s,"max item idx",max(its),"unfinished",js["sets"][s]["unfinished"],"items with rows",len(set(its)))
# pooled count-only AUC over the four trained nets' p-grids7 states
P=[r["k"] for n in tr for r in rows[n] if r["set"]=="p-grids7" and r["dead"]]
N=[r["k"] for n in tr for r in rows[n] if r["set"]=="p-grids7" and not r["dead"]]
print("pooled count-only AUC p-grids7 (4 trained nets):", round(auc(P,N),4), "states", len(P)+len(N))
# puzzle-level bootstrap of (mean critic AUC - mean count AUC) on p-grids7, for fragility only
random.seed(0)
by={n:defaultdict(list) for n in tr}
for n in tr:
    for r in rows[n]:
        if r["set"]=="p-grids7": by[n][r["item"]].append(r)
B=1000; diffs=[]
for _ in range(B):
    cs=[];ks=[]
    for n in tr:
        keys=list(by[n]); samp=[random.choice(keys) for _ in keys]
        rr=[r for k in samp for r in by[n][k]]
        p=[r for r in rr if r["dead"]]; q=[r for r in rr if not r["dead"]]
        cs.append(auc([r["score"] for r in p],[r["score"] for r in q])); ks.append(auc([r["k"] for r in p],[r["k"] for r in q]))
    diffs.append(sum(cs)/4-sum(ks)/4)
diffs.sort()
print("bootstrap mean(critic)-mean(count) p-grids7: 2.5%%=%.4f 50%%=%.4f 97.5%%=%.4f; share>=0.05: %.3f; share>0: %.3f"%(diffs[25],diffs[500],diffs[974],sum(d>=0.05 for d in diffs)/B,sum(d>0 for d in diffs)/B))
