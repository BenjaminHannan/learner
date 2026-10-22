import json,re,collections,itertools
R='lt2/rows/'
def load(f,n=None):
    out=[]
    for i,l in enumerate(open(f)):
        if n and i>=n: break
        out.append(json.loads(l))
    return out
def feats(x):
    p=x['meta']['program']
    cnt=collections.Counter(re.findall(r'([a-z]+)\(',p))   # predicates in program
    # also rule predicates parse: all idents before '(' ; 
    sing=sum(1 for k,v in cnt.items() if v==1)
    return (len(cnt),sing,x['meta'].get('n_rules'),x['meta'].get('n_facts'))
def table(rows,key):
    t=collections.defaultdict(collections.Counter)
    for x in rows: t[key(x)][x['meta']['label']]+=1
    return t
def acc(t,rows,key):
    c=0
    for x in rows:
        d=t.get(key(x))
        if d and d.most_common(1)[0][0]==x['meta']['label']: c+=1
        elif not d: pass
    return c/len(rows)
tr=load(R+'logic_train.jsonl',50000)
pl=load(R+'placebo_train.jsonl',50000)
print(tr[0]['meta']['program'])
for nm,key in [('sing',lambda x:feats(x)[1]),('ndist,sing',lambda x:feats(x)[:2]),('ndist,sing,nr,nf',feats)]:
    for tn,trn,ev in [('logic',tr,['logic_gate','logic_dev']),('placebo',pl,['placebo_dev','placebo_test_wording'])]:
        t=table(trn,key)
        print(nm,tn,{e:round(acc(t,load(R+f'eval/{e}.jsonl'),key),3) for e in ev})
# by-depth gate
t=table(tr,lambda x:feats(x)[:2])
g=load(R+'eval/logic_gate.jsonl')
for d in range(4):
    rr=[x for x in g if x['meta']['depth']==d]
    print('gate depth',d,round(acc(t,rr,lambda x:feats(x)[:2]),3))
# mean singletons by label & depth in gate
m=collections.defaultdict(list)
for x in g: m[(x['meta']['depth'],x['meta']['label'])].append(feats(x)[1])
print({k:round(sum(v)/len(v),2) for k,v in sorted(m.items())})
