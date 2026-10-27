import json,re,sys,collections
D='artifacts/claude-corrtail258-20260922/'
P={}
for l in open(D+'panel.jsonl'):
    p=json.loads(l); P[p['id']]=p
BASE={json.loads(l)['id']:json.loads(l) for l in open(D+'base252b.jsonl')}
def T(ts): return {tuple(str(x).lower() for x in t) for t in (ts or [])}
def ww(v,s): return re.search(r'(?<!\w)'+re.escape(str(v).lower())+r'(?!\w)',(s or '').lower()) is not None
def score(r,p,base):
    sa=T(r['stored_after_setup']); st=T(r['stored_after_turn']); sf=T(r['stored_after_followup'])
    es=T(p['expect_store']); eg=T(p['expect_gone'])
    store_ok = es<=st and not (eg&st) and st<=(sa|es)
    junk = not st<=(sa|es) or not sf<=(sa|es)
    g=p['gold_followup']; fr=r['followup_reply'] or ''
    if g:
        parts=g if isinstance(g,list) else [g]
        fok = all(str(x).lower() in fr.lower() for x in parts) and not fr.lower().startswith(("i don't know","i do not know"))
    else:
        fok = not any(ww(t[2],fr) for t in eg)
    wv = any(ww(t[2],fr) for t in eg)
    fw = sf!=st
    tg=p['target']; tr=r['turn_reply'] or ''
    fc = bool(tg) and tuple(str(x).lower() for x in tg) in sa and tuple(str(x).lower() for x in tg) in st and ('don\'t have' in tr.lower() or 'do not have' in tr.lower()) and ww(tg[2],tr)
    right = store_ok and fok and not fw and not fc
    if p['family'] in ('keep','control'):
        right = right and all(r[k]==base[k] for k in ('turn_reply','followup_reply','stored_after_setup','stored_after_turn','stored_after_followup'))
    if p['family']=='unstored_tail' and ('removed' in tr.lower() or 'updated' in tr.lower()): right=False
    return dict(right=right,junk=junk,wv=wv,fc=fc,fw=fw)
res={}
for f in sys.argv[1:]:
    R={json.loads(l)['id']:json.loads(l) for l in open(f)}
    assert set(R)==set(P), 'id mismatch'
    res[f]={i:score(R[i],P[i],BASE[i]) for i in P}
fams=['that_denial','that_correction','pure_denial_that','other_tail_denial','keep','question_tail','unstored_tail','control']
for f,S in res.items():
    print(f)
    for fam in fams:
        ids=[i for i in P if P[i]['family']==fam]
        print(f'  {fam:18s} n={len(ids):2d} right={sum(S[i]["right"] for i in ids):2d} junk={sum(S[i]["junk"] for i in ids)} wv={sum(S[i]["wv"] for i in ids):2d} fc={sum(S[i]["fc"] for i in ids)} fw={sum(S[i]["fw"] for i in ids)}')
if len(res)==2:
    a,b=list(res.values())
    print('became right:',sorted(i for i in P if b[i]['right'] and not a[i]['right']))
    print('became wrong:',sorted(i for i in P if a[i]['right'] and not b[i]['right']))
