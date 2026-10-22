import json,sys,itertools,collections
sys.path.insert(0,'.'); sys.path.insert(0,'/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt')
import v_parse as P
R='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
def closure(facts,inst):
    k=set(facts); ch=True
    while ch:
        ch=False
        for prem,c in inst:
            if c not in k and all(p in k for p in prem): k.add(c); ch=True
    return k
def mindepth(facts,rules,q):
    ents={f[2] for f in facts}|{q[2]}|{r[0] for r in rules if r[0]}
    fs=set(facts); full=[]
    for ent,lhs,rhs in rules:
        for e in ([ent] if ent else sorted(ents)):
            full.append((tuple((n,p,e) for n,p in lhs),(rhs[0],rhs[1],e)))
    K=closure(fs,full); neg=(not q[0],q[1],q[2])
    tgt=q if q in K else neg if neg in K else None
    if tgt is None: return None
    if tgt in fs: return 0
    # relevant instances: those whose premises are all in K and conclusion not a fact
    rel=[i for i in full if i[1] not in fs and all(p in K for p in i[0])]
    rel=list(dict.fromkeys(rel))
    for k in range(1,min(7,len(rel))+1):
        for sub in itertools.combinations(rel,k):
            if len({s[1] for s in sub})<k: continue
            if tgt in closure(fs,sub): return k
    return -1
for f in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper']:
    n=ok=0; bad=[]
    for r in (json.loads(l) for l in open(R+'eval/'+f+'.jsonl')):
        if r['answer']=='unknown': continue
        (facts,rules,q,_),_e=P.parse(r['prompt']); n+=1
        d=mindepth(facts,rules,q)
        if d==r['level']: ok+=1
        else: bad.append((r['id'],d,r['level']))
    print(f,'tf rows',n,'min proof size == level',ok,bad[:3])
