import json,sys,collections
sys.path.insert(0,'.'); sys.path.insert(0,'/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt')
import v_parse as P
R='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
def clauses(facts,rules,q):
    ents={f[2] for f in facts}|{q[2]}|{r[0] for r in rules if r[0]}
    cl=[]
    for f in facts: cl.append([(f[1],f[2],not f[0])])           # literal = (pred,ent,positive)
    for ent,lhs,rhs in rules:
        for e in ([ent] if ent else ents):
            cl.append([(p,e,n) for n,p in lhs]+[(rhs[1],e,not rhs[0])])  # not(lhs lit true) or rhs
    return cl
def lit_neg(l): return (l[0],l[1],not l[2])
# note lhs literal "(n,p)": true when atom has polarity (not n). clause disjunct = negation of that.
def clauses(facts,rules,q):
    ents={f[2] for f in facts}|{q[2]}|{r[0] for r in rules if r[0]}
    cl=[]
    for n,p,e in facts: cl.append([(p,e,not n)])
    for ent,lhs,rhs in rules:
        for e in ([ent] if ent else sorted(ents)):
            cl.append([(p,e,n) for n,p in lhs]+[(rhs[1],e,not rhs[0])])
    return cl
def sat(cl,assign=None):
    assign=dict(assign or {})
    cl=[list(c) for c in cl]
    while True:
        unit=None; new=[]
        for c in cl:
            if any(assign.get((p,e))==s for p,e,s in c): continue
            c2=[(p,e,s) for p,e,s in c if (p,e) not in assign]
            if not c2: return False
            if len(c2)==1: unit=c2[0]
            new.append(c2)
        cl=new
        if unit is None: break
        assign[(unit[0],unit[1])]=unit[2]
    if not cl: return True
    p,e,_=cl[0][0]
    for v in (True,False):
        a=dict(assign); a[(p,e)]=v
        if sat(cl,a): return True
    return False
def classical(facts,rules,q):
    cl=clauses(facts,rules,q)
    if not sat(cl): return 'inconsistent'
    qt=(q[1],q[2],not q[0])
    can_q=sat(cl+[[qt]]); can_nq=sat(cl+[[lit_neg(qt)]])
    return 'unknown' if can_q and can_nq else 'true' if can_q else 'false'
import re
def go(f,lim=0):
    n=d=0; conf=collections.Counter()
    for r in (json.loads(l) for l in open(R+f+'.jsonl')):
        if lim and n>=lim: break
        n+=1
        (facts,rules,q,ids),err=P.parse(r['prompt'])
        c=classical(facts,rules,q)
        if c!=r['answer']: d+=1; conf[(r['answer'],c)]+=1
    print(f,n,'classical differs',d,round(100*d/n,2),dict(conf))
for f in ['eval/logic_gate','eval/logic_dev','eval/logic_test_sampler','eval/logic_test_deeper','eval/placebo_dev','eval/placebo_test_wording']: go(f)
