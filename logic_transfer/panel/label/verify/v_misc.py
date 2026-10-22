import json,collections,re,sys
R='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/'
def rows(f):
    for l in open(R+f+'.jsonl'): yield json.loads(l)
ev=['eval/'+x for x in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']]
# C5 balance + C10 lookup-only
def lookup(r):
    prog=r['meta']['program']; facts=set(); q=None
    for it in prog.split(';'):
        it=it.strip()
        if it.startswith('F '): facts.add(it[2:].replace(' ',''))
        if it.startswith('Q '): q=it[2:].replace(' ','')
    if q in facts: return 'true'
    neg=q[1:] if q.startswith('~') else '~'+q
    return 'false' if neg in facts else 'unknown'
def canon(r):
    prog=r['meta']['program']; m={}
    def rn(w):
        if w not in m: m[w]='w%d'%len(m)
        return m[w]
    toks=re.findall(r'[a-z][a-z0-9_]*|[^a-z\s]',prog)
    out=[]
    for t in toks:
        out.append(t if t in 'FRQ' and len(t)==1 else (rn(t) if re.match('[a-z]',t) and t!='x' else t))
    return ''.join(out)
store={}
for f in ev+['logic_train','placebo_train']:
    lab=collections.Counter(); lk=0;n=0; bylevel=collections.defaultdict(lambda:[0,0]); ok_all=True
    for r in rows(f):
        n+=1; lab[r['answer']]+=1
        lk+= lookup(r)==r['answer']
        b=bylevel[r['level']]; b[0]+= lookup(r)==r['answer']; b[1]+=1
        if f in('logic_train','placebo_train') and 'logic' in f or f=='placebo_train': pass
    print(f,n,dict(lab),'lookup-only',round(lk/n,4),{k:round(v[0]/v[1],3) for k,v in sorted(bylevel.items())})
# C11 exact body dup across all
body=lambda p: re.sub(r'\s*\([a-z/]+\)\s*$','',p)
seen={}; dup=collections.Counter()
for f in ev+['logic_train','placebo_train']:
    for r in rows(f):
        b=body(r['prompt'])
        if b in seen: dup[(seen[b],f)]+=1
        else: seen[b]=f
print('exact body dups (first-seen file, later file):',dict(dup))
# C12 structure overlap
trainC={'logic':set(),'placebo':set()}
for r in rows('logic_train'): trainC['logic'].add(canon(r))
for r in rows('placebo_train'): trainC['placebo'].add(canon(r))
print('distinct structures in logic_train',len(trainC['logic']),'placebo_train',len(trainC['placebo']))
for f in ev:
    k='placebo' if 'placebo' in f else 'logic'; n=hit=0
    for r in rows(f):
        n+=1; hit+= canon(r) in trainC[k]
    print('structure in train',f,hit,n)
