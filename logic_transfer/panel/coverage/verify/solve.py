import json,re,collections,sys
def lit(s):
    s=s.strip(); neg=s.startswith('~'); s=s.lstrip('~')
    m=re.match(r'([a-z]+)\(([a-z]+|x)\)$',s)
    return (neg,m.group(1),m.group(2))
def parse(prog):
    F=[];R=[];Q=None
    for part in prog.split('; '):
        k,rest=part[0],part[2:]
        if k=='F': F.append(lit(rest))
        elif k=='Q': Q=lit(rest)
        else:
            m=re.match(r'([a-z]+): (~?[a-z]+)>(~?[a-z]+)$',rest)
            if m:
                e=m.group(1); a=m.group(2);c=m.group(3)
                f=lambda s:(s.startswith('~'),s.lstrip('~'),e)
                R.append(([f(a)],f(c),e))
            else:
                pre,con=rest.split('>')
                R.append(([lit(p) for p in pre.split('&')],lit(con),None))
    return F,R,Q
def solve(prog):
    F,R,Q=parse(prog)
    ents={l[2] for l in F}|{Q[2]}
    ents|={e for _,_,e in R if e}
    d={}  # (neg,pred,ent)->depth
    for f in F: d[f]=0
    ch=True
    while ch:
        ch=False
        for pre,con,e in R:
            for en in ([e] if e else ents):
                body=[(n,p,en) for n,p,_ in pre]
                if all(b in d for b in body):
                    c=(con[0],con[1],en); dd=max(d[b] for b in body)+1
                    if c not in d or d[c]>dd: d[c]=dd; ch=True
    q=Q
    t=d.get(q); f=d.get((not q[0],q[1],q[2]))
    if t is not None and f is not None: return 'conflict',t,f
    if t is not None: return 'true',t,None
    if f is not None: return 'false',f,None
    return 'unknown',None,None
if __name__=='__main__':
    import glob
    for fn in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']:
        c=collections.Counter(); bad=[]
        for l in open(f'lt2/rows/eval/{fn}.jsonl'):
            x=json.loads(l); m=x['meta']
            lab,dep,_=solve(m['program'])
            ok=(lab==m['label'])
            dok = (dep==m['depth']) if lab in('true','false') else True
            c[(ok,dok)]+=1
            if not(ok and dok) and len(bad)<3: bad.append((m['program'],m['label'],m['depth'],lab,dep))
        print(fn,dict(c),bad)
