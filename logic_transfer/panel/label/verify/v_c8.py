import json,sys,collections,re
sys.path.insert(0,'.')
sys.path.insert(0,'/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt')
import v_parse as P
R='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
PN={'R2:4','R2:5','R2:6','R2:9','R2:13'}; DI={'R3:1','R3:2','R3:7','R3:9'}
def parse_ids(prompt):
    body=re.sub(r'\s*\([a-z/]+\)\s*$','',prompt).lower()
    sents=re.split(r'(?<=[.?])\s+',body.strip()); facts=[];rules=[];q=None
    for k,s in enumerate(sents):
        for tid,kind,r in P.TABLE:
            m=r.match(s)
            if m and (kind=='Q')==(k==len(sents)-1):
                me=P.meaning(kind,m)
                if me[0]=='fact':facts.append(me[1])
                elif me[0]=='rule':rules.append(me[1:]+(tid,))
                else:q=me[1]
                break
    return facts,rules,q
for f,lim in [('logic_train',130000)]:
    n=pn=di=0
    for r in (json.loads(l) for l in open(R+f+'.jsonl')):
        if lim and n>=lim: break
        n+=1
        facts,rules,q=parse_ids(r['prompt'])
        base=P.solve(facts,[x[:3] for x in rules],q)[0]
        r2=[x[:3] for x in rules if x[3] not in PN]
        pn+= P.solve(facts,r2,q)[0]!=base
        r3=[]
        for e,lhs,rhs,t in rules:
            if t in DI: r3+= [(e,[l],rhs) for l in lhs]
            else: r3.append((e,lhs,rhs))
        di+= P.solve(facts,r3,q)[0]!=base
    print(f,n,'PNEG',pn,round(100*pn/n,1),'DIST',di,round(100*di/n,1))
