import json,re,collections
W=re.compile(r"[a-z]+")
tr=[json.loads(l) for i,l in zip(range(40000),open('lt2/rows/logic_train.jsonl'))]
df=collections.Counter()
for x in tr: df.update(set(W.findall(x['prompt'].split(' (')[0].lower())))
# template words: doc freq >= 1.5% of rows; content words: below
tw={w for w,c in df.items() if c>=0.015*len(tr)}
print('template-ish words',len(tw),'of',len(df))
def f(x):
    ws=W.findall(re.sub(r'\s*\([a-z/]+\)\s*$','',x['prompt']))
    # ignore capitalised names: use original-case tokens that start lowercase
    toks=[w for w in re.findall(r"\b[a-z]+\b",re.sub(r'\s*\([a-z/]+\)\s*$','',x['prompt']))]
    c=collections.Counter(w for w in toks if w not in tw)
    return sum(1 for v in c.values() if v==1)
g=[json.loads(l) for l in open('lt2/rows/eval/logic_gate.jsonl')]
for d in range(4):
    t=collections.defaultdict(collections.Counter)
    for x in tr:
        if x['meta']['depth']==d: t[f(x)][x['meta']['label']]+=1
    rr=[x for x in g if x['meta']['depth']==d]
    # fallback: majority overall if unseen
    a=sum((t[f(x)].most_common(1)[0][0] if t[f(x)] else 'true')==x['meta']['label'] for x in rr)/len(rr)
    print('text-only singleton lookup, gate depth',d,round(a,3))
a=0
tall=collections.defaultdict(collections.Counter)
for x in tr: tall[f(x)][x['meta']['label']]+=1
print('pooled gate',sum((tall[f(x)].most_common(1)[0][0] if tall[f(x)] else 'true')==x['meta']['label'] for x in g)/len(g))
