import json,re,collections
exec(open('v_misc.py').read().split('# C5')[0])
def chi2(tab):
    rs=[sum(r) for r in tab]; cs=[sum(c) for c in zip(*tab)]; N=sum(rs)
    return sum((tab[i][j]-rs[i]*cs[j]/N)**2/(rs[i]*cs[j]/N) for i in range(len(rs)) for j in range(len(cs)) if rs[i]*cs[j])
for f in ev+['logic_train','placebo_train']:
    t={l:[0,0,0] for l in('true','false','unknown')}; sets=collections.Counter(); n=0
    for r in rows(f):
        m=re.search(r'\(([a-z/]+)\)\s*$',r['prompt']); w=m.group(1).split('/'); sets[tuple(sorted(w))]+=1
        t[r['answer']][w.index(r['answer'])]+=1
    print(f,dict(sets),'pos table',list(t.values()),'chi2',round(chi2(list(t.values())),2),'pos shares',[round(sum(c)/sum(map(sum,t.values())),3) for c in zip(*t.values())])
# label consistency of identical canonical structures within logic_train
c=collections.defaultdict(set)
for r in rows('logic_train'): c[canon(r)].add(r['answer'])
print('logic_train structure groups',len(c),'with >1 label',sum(len(v)>1 for v in c.values()))
c=collections.defaultdict(set)
for r in rows('placebo_train'): c[canon(r)].add(r['answer'])
print('placebo_train structure groups',len(c),'with >1 label',sum(len(v)>1 for v in c.values()))
