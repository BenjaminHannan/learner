import json,lzma,re,collections as C
rows=json.load(lzma.open('rows.json.xz'))
D=json.load(lzma.open('dialogs.json.xz'))
key=lambda i: re.sub(r'-t\d+$','',i[7:])
turn=lambda i:int(re.search(r'-t(\d+)$',i).group(1))
norm=lambda s:' '.join(str(s).lower().split()) if s is not None else None
SM={'ASSERT':'current','CORRECT':'correction','FORMER':'former'}
vec={};lora={}
for l in open('vec_dev_reads.jsonl'):
    if l.strip(): j=json.loads(l); vec[j['id']]=[(c['owner'],c['rel'],c['value'],c['state']) for c in j['cards']]
for l in open('lora_dev_reads.jsonl'):
    if l.strip():
        j=json.loads(l); fs=(j.get('frame') or {}).get('facts') or []
        lora[j['id']]=[(f['owner'],f['rel'],f['value'],SM[f['mode']]) for f in fs if f.get('mode') in SM]
B=[r for r in rows if r[1]=='dev' and r[2]=='backref']
allrows=C.defaultdict(list)
for r in rows: allrows[key(r[0])].append(r)
# person-naming relations: rels that appear only with owner me across whole data and are not property-ish
rel_own=C.defaultdict(lambda:[0,0])
for r in rows:
    for f in r[3]['facts']: rel_own[f['rel']][f['owner']=='me']+=1
PERSON={k for k,(n,m) in rel_own.items() if n==0}
print('person rels',sorted(PERSON)); print('mixed',{k:v for k,v in rel_own.items() if v[0] and v[1]})
def persons(k):
    s=set()
    for r in allrows[k]:
        for f in r[3]['facts']:
            if f['owner'] not in ('me',None,''): s.add(f['owner'])
            if f['rel'] in PERSON and f['value']: s.add(f['value'])
    return s
def seen(r):
    k=key(r[0]);N=turn(r[0]);t=D[k];out=[]
    for i in range(N):
        out.append(t[i][0])
        if i<N-1: out.append(t[i][1])
    return '\n'.join(out)
def lastpos(name,txt):
    m=[x.start() for x in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',txt)]
    return m[-1] if m else -1
def match(emit,gold):
    used=[False]*len(gold);res=[]
    for (o,rel,v,st) in emit:
        cand=[i for i,g in enumerate(gold) if not used[i] and g[1]==rel and g[3]==st]
        pref=[i for i in cand if norm(gold[i][0])==norm(o) and norm(gold[i][2])==norm(v)]
        pick=(pref or cand or [None])[0]
        if pick is None: res.append(((o,rel,v,st),None))
        else: used[pick]=True; res.append(((o,rel,v,st),gold[pick]))
    return res
def run(reads,name):
    S=C.Counter();Dd=[]
    S['rows']=len(B);S['rows_with_read']=sum(1 for r in B if r[0] in reads)
    res={}
    for r in B:
        gold=[(f['owner'],f['rel'],f['value'],SM[f['mode']]) for f in r[3]['facts'] if f['mode'] in SM]
        S['gold']+=len(gold)
        txt=seen(r);P=persons(key(r[0]))
        for e,g in match(reads.get(r[0],[]),gold):
            if g is None: S['unmatched']+=1;continue
            if g[0]=='me': S['matched_gold_me_skipped']+=1;continue
            S['M']+=1
            go=g[0];o=e[0]
            rivals=[p for p in P if norm(p)!=norm(go) and lastpos(p,txt)>=0]
            rv=bool(rivals)
            if norm(o)==norm(go): cls='right'
            elif norm(o)=='me': cls='me'
            else: cls='wrong'
            S[cls]+=1
            if rv: S['M_rival']+=1;S[cls+'_rival']+=1
            res[(r[0],g[1],g[3],g[0])]=(cls,rv)
            if cls=='wrong' and rv:
                pp=lastpos(o,txt);gp=lastpos(go,txt)
                allp={p:lastpos(p,txt) for p in P|{go}}
                mx=max(allp.values())
                S['w_rv_picked_more_recent']+= pp>gp
                S['w_rv_picked_in_text']+= pp>=0
                S['w_rv_picked_is_latest_of_all']+= (pp>=0 and pp==mx)
                S['w_rv_picked_in_personset']+= o in P
    return S,res
sv,rv_=run(vec,'vec');sl,rl=run(lora,'lora')
for n,s in (('VEC',sv),('LORA',sl)): print(n,dict(s))
# (e)
mr=[k for k,(c,rv) in rv_.items() if rv]
e=sum(1 for k in mr if k in rl and rl[k][0]=='right' and rv_[k][0]=='wrong')
e2=sum(1 for k in mr if k in rl and rl[k][0]=='right' and rv_[k][0]!='right')
print('e strict',e,'of',len(mr),'e vec-not-right',e2, 'lora matched among mr',sum(1 for k in mr if k in rl))
