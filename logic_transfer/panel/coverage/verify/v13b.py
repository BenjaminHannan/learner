import json,re,collections
def feats(x):
    p=x['meta']['program']; cnt=collections.Counter(re.findall(r'([a-z]+)\(',p))
    return (sum(1 for v in cnt.values() if v==1),)
tr=[json.loads(l) for i,l in zip(range(50000),open('lt2/rows/logic_train.jsonl'))]
g=[json.loads(l) for l in open('lt2/rows/eval/logic_gate.jsonl')]
for d in range(4):
    t=collections.defaultdict(collections.Counter)
    for x in tr:
        if x['meta']['depth']==d: t[feats(x)][x['meta']['label']]+=1
    rr=[x for x in g if x['meta']['depth']==d]
    a=sum(t[feats(x)].most_common(1)[0][0]==x['meta']['label'] for x in rr if t[feats(x)])/len(rr)
    print('depth',d,'n',len(rr),'acc',round(a,3),'SE',round((a*(1-a)/len(rr))**.5,3), {k:dict(v) for k,v in sorted(t.items())})
