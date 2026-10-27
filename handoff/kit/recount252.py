import json,ast,re,sys,collections
D='artifacts/claude-corrpanel252-20260922/'
P=[json.loads(l) for l in open(D+'panel.jsonl')]
BK={r['id']:r for r in map(json.loads,open(D+'base138k.jsonl'))}
def L(x):
    if not isinstance(x,str): return x
    try: return json.loads(x)
    except Exception: return ast.literal_eval(x)
def T(ts): return {tuple(p.lower() for p in t) for t in (L(ts) or [])}
def ww(v,t): return re.search(r'(?<!\w)'+re.escape(v)+r'(?!\w)',t or '',re.I) is not None
def score(rows):
    R={}
    for l in open(rows):
        r=json.loads(l); R[r['id']]=r
    out=collections.defaultdict(lambda: collections.Counter()); items=[]
    for p in P:
        r=R[p['id']]; f=p['family']
        sat=T(r['stored_after_turn']); sas=T(r['stored_after_setup']); saf=T(r['stored_after_followup'])
        es=T(p['expect_store']); eg=T(p['expect_gone'])
        junk=not sat<= (sas|es)
        store_ok= es<=sat and not (eg & sat) and not junk
        fr=r['followup_reply'] or ''
        gone_vals=[g[2] for g in L(p['expect_gone'])]
        if p['gold_followup']:
            parts=[x.strip() for x in p['gold_followup'].split(';')]
            fok=all(x.lower() in fr.lower() for x in parts) and not re.match(r"\s*i (don't|do not) know",fr,re.I)
        else:
            fok=not any(ww(v,fr) for v in gone_vals)
        wrong=any(ww(v,fr) for v in gone_vals)
        fw= saf!=sat
        right=store_ok and fok and not fw
        if f=='control':
            b=BK[p['id']]; right=right and r['turn_reply']==b['turn_reply'] and r['followup_reply']==b['followup_reply']
        c=out[f]; c['n']+=1; c['right']+=right; c['wrong']+=wrong; c['junk']+=junk; c['fw']+=fw
        items.append((p['id'],f,right,wrong,junk))
    return out,items
for arm in sys.argv[1:]:
    out,items=score(arm)
    print('==',arm)
    for f,c in out.items(): print(f'  {f:22s} {c["right"]:2d}/{c["n"]:2d} wrong {c["wrong"]} junk {c["junk"]} fw {c["fw"]}')
    print('  TOTAL right',sum(c['right'] for c in out.values()),'wrong',sum(c['wrong'] for c in out.values()),'junk',sum(c['junk'] for c in out.values()),'fw',sum(c['fw'] for c in out.values()))
    print('  junk ids',[i for i,f,r,w,j in items if j])
