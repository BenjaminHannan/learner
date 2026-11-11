# Can T1 twin pairs (two P targets per number set, different sign patterns) be sign-balanced? Also the
# share of a uniform rule-valid choice that hits the target (natural R hit rate), by definition of rule-valid.
import itertools, collections
exec(open('blind.py').read().split("print('P-tier instances'")[0])
pat_sets=collections.defaultdict(set); by=collections.defaultdict(dict)
for nums,t,c,v in inst:
    pats=[s for s in itertools.product((1,-1),repeat=3) if sum(si*x for si,x in zip(s,nums))==t]
    for s in pats: pat_sets[s].add(nums)
    by[nums][t]=pats
print('number sets offering each sign pattern as a P target:')
for s,ns in sorted(pat_sets.items(), key=lambda kv:-len(kv[1])): print(' ',s,len(ns))
# greedy balanced draw of 128 pairs (x3 sets T1,T1b,T2 + DEV 64 = 448 pairs) from distinct sets
import random; random.seed(1)
sets=[n for n in by if len(by[n])>=2]; random.shuffle(sets)
need=collections.Counter(); target_per=2*448/5
used=0; cnt=collections.Counter()
for n in sets:
    if used==448: break
    opts=[]
    for t1,t2 in itertools.combinations(by[n],2):
        p1=by[n][t1][0]; p2=by[n][t2][0]
        if p1!=p2: opts.append((cnt[p1]+cnt[p2],p1,p2))
    if not opts: continue
    sc,p1,p2=min(opts)
    if cnt[p1]<target_per and cnt[p2]<target_per:
        cnt[p1]+=1; cnt[p2]+=1; used+=1
print('greedy balanced draw of %d pairs:'%used, dict(cnt))
# natural hit rate among rule-valid (no-ERROR) two-call trees, uniform over them
print('uniform among rule-valid trees: mean hit %.3f ; per try incl. erroring shapes: %.3f'%(
  sum(c/v for _,_,c,v in inst)/len(inst), sum(c/48 for _,_,c,v in inst)/len(inst)))
