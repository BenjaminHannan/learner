# Skeptical verifier: own parser + own solver. Templates read as DATA from logicgen/templates.py (text only);
# semantics per kind are hand-assigned here, NOT imported from the generator/checker.
import re, json, sys, collections
sys.path.insert(0,'/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt')
from logicgen.templates import TEMPLATES   # strings only
W=r'[a-z]+'; PH=r'(?:not )?[a-z]+'
def rx(t):
    t=t.lower(); out=''; seen=set(); i=0
    t=re.escape(t).replace(r'\ ',' ')
    def sub(m):
        k=m.group(1)
        if k=='e':
            if 'e' in seen: return '(?P=e)'
            seen.add('e'); return '(?P<e>(?!it )[a-z]+)'
        if k in 'pq' : return f'(?P<{k}>{W})'
        if k in 'abc': return f'(?P<{k}>{PH})'
        if k=='n': return '(?P<n>(?:not )?)'
    t=re.sub(r'\\\{(\w)\\\}',sub,t)
    return re.compile('^'+t+'$')
TABLE=[]
for kind,lst in TEMPLATES.items():
    for i,t in enumerate(lst):
        TABLE.append((f'{kind}:{i}',kind,rx(t)))
def ph(s): s=s.strip(); return (s.startswith('not '), s[4:] if s.startswith('not ') else s)
def meaning(kind,m):
    g=m.groupdict()
    if kind=='R1': return ('rule',None,[(False,g['p'])],(False,g['q']))
    if kind=='R2': return ('rule',None,[(False,g['p'])],(True,g['q']))
    if kind=='R3': return ('rule',None,[(False,g['p']),(False,g['q'])],ph(g['c']))
    if kind=='R4': return ('rule',None,[(True,g['p'])],(False,g['q']))
    if kind=='R5': return ('rule',g['e'],[ph(g['a'])],ph(g['b']))
    if kind=='FP': return ('fact',(False,g['p'],g['e']))
    if kind=='FN': return ('fact',(True,g['p'],g['e']))
    if kind=='Q': return ('q',(g['n']!='',g['p'],g['e']))
def parse(prompt):
    body=re.sub(r'\s*\([a-z/]+\)\s*$','',prompt).lower()
    sents=re.split(r'(?<=[.?])\s+',body.strip())
    facts=[];rules=[];q=None;ids=[]
    for k,s in enumerate(sents):
        hits=[]
        for tid,kind,r in TABLE:
            m=r.match(s)
            if m and (kind=='Q')==(k==len(sents)-1): hits.append((tid,meaning(kind,m)))
        if not hits: return None,'nomatch:'+s
        ms={json.dumps(h[1],sort_keys=True,default=str) for h in hits}
        if len(ms)>1: return None,'ambig:'+s+str([h[0] for h in hits])
        tid,mean=hits[0]; ids.append(tid)
        if mean[0]=='fact': facts.append(mean[1])
        elif mean[0]=='rule': rules.append(mean[1:])
        else: q=mean[1]
    return (facts,rules,q,ids),None
def solve(facts,rules,q):
    ents={f[2] for f in facts}|{q[2]}|{r[0] for r in rules if r[0]}
    known=set(facts); ch=True
    while ch:
        ch=False
        for ent,lhs,rhs in rules:
            for e in ([ent] if ent else ents):
                if all((n,p,e) in known for n,p in lhs):
                    c=(rhs[0],rhs[1],e)
                    if c not in known: known.add(c); ch=True
    contra=any((not n,p,e) in known for n,p,e in known)
    neg=(not q[0],q[1],q[2])
    lab='true' if q in known else 'false' if neg in known else 'unknown'
    return lab,contra
if __name__=='__main__':
    R='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
    files=['eval/logic_gate','eval/logic_dev','eval/logic_test_sampler','eval/logic_test_deeper','eval/placebo_dev','eval/placebo_test_wording']
    lim=int(sys.argv[1]) if len(sys.argv)>1 else 0
    files += ['logic_train','placebo_train']
    for f in files:
        n=ok=fail=amb=contra=idm=0; bad=[]; c=collections.Counter()
        for line in open(R+f+'.jsonl'):
            r=json.loads(line); 
            if 'train' in f and lim and n>=lim: break
            n+=1
            p,err=parse(r['prompt'])
            if p is None:
                fail+=1; bad.append((r['id'],err)); continue
            lab,cn=solve(*p[:3]); contra+=cn
            if lab==r['answer']: ok+=1
            else: bad.append((r['id'],lab,r['answer']))
            if sorted(p[3])==sorted(r['meta']['template_ids']): idm+=1
        print(f,'n',n,'agree',ok,'parsefail',fail,'contra',contra,'tid_match',idm,bad[:3])
