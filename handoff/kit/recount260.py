import json,sys,collections
P='artifacts/claude-openpanel260-20260922/panel.jsonl'
panel=[json.loads(l) for l in open(P)]
base={r['id']:r for r in map(json.loads,open('artifacts/claude-openpanel260-20260922/base138m.jsonl'))}
def T(x): return set(tuple(t) for t in x)
BAD=["save","understand","couldn't","could not","don't know","not sure"]
def norm(s): return s.lower().strip().strip('.,!?;:"\' ').strip()
def score(rows):
    res={}; junk_total=0; qw_total=0
    for it in panel:
        r=rows[it['id']]; fam=it['family']
        s0=T(r['stored_after_setup']); s1=T(r['stored_after_turn']); s2=T(r['stored_after_followup'])
        exp=T(it['expect_store'])
        junk=bool(((s1|s2)-s0)-exp)
        isq = fam in ('opener_question','greeting_question') or (fam=='control' and it['followup']=='')
        qwrite = (isq and s1!=s0) or (it['followup']!='' and s2!=s1)
        added=s1-s0
        store_ok = exp<=s1 and added<=exp
        scored = r['turn_reply'] if isq or it['followup']=='' else r['followup_reply']
        rok = it['gold']=='' or norm(it['gold']) in norm(scored) or it['gold'].lower() in scored.lower()
        if fam in ('opener_teach','junk_guard','name_trap'): ok=store_ok and rok and not junk and not qwrite
        elif fam in ('opener_question','greeting_question'): ok=rok and not qwrite and not junk
        elif fam=='bare_greeting': ok=(s1==s0) and not any(b in r['turn_reply'].lower() for b in BAD)
        elif fam=='control':
            b=base[it['id']]
            ident = r['setup_replies']==b['setup_replies'] and r['turn_reply']==b['turn_reply'] and r['followup_reply']==b['followup_reply']
            if it['followup']=='' : shape_ok= rok and not qwrite and not junk
            else: shape_ok= store_ok and rok and not junk and not qwrite
            ok=shape_ok and ident
        res[it['id']]=(fam,ok,junk,qwrite)
        junk_total+=junk; qw_total+=qwrite
    return res,junk_total,qw_total
out={}
for arm,f in [('260','artifacts/claude-openers260-20260922/run/panel-260.jsonl'),('138m','artifacts/claude-openers260-20260922/run/panel-138m.jsonl'),('base','artifacts/claude-openpanel260-20260922/base138m.jsonl')]:
    rows={r['id']:r for r in map(json.loads,open(f))}
    res,j,q=score(rows); out[arm]=res
    c=collections.Counter(); n=collections.Counter()
    for i,(fam,ok,junk,qw) in res.items(): n[fam]+=1; c[fam]+=ok
    print(arm,{k:f"{c[k]}/{n[k]}" for k in n},'right',sum(c.values()),'junk',j,'qwrite',q)
moved=[i for i in out['260'] if out['260'][i][1]!=out['138m'][i][1]]
print('moved',len(moved),'toward right',sum(out['260'][i][1] for i in moved))
# 138m arm identical to writer's base?
a={r['id']:r for r in map(json.loads,open('artifacts/claude-openers260-20260922/run/panel-138m.jsonl'))}
keys=['setup_replies','stored_after_setup','turn_reply','stored_after_turn','followup_reply','stored_after_followup']
print('138m arm == base on reply/store fields:',sum(all(a[i][k]==base[i][k] for k in keys) for i in base),'/',len(base))
