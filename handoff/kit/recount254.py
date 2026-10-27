import json,re,sys,collections
D='artifacts/claude-looppanel254-20260922/'
P=[json.loads(l) for l in open(D+'panel.jsonl')]
B={r['id']:r for r in map(json.loads,open(sys.argv[1] if len(sys.argv)>1 else D+'base138l.jsonl'))}
FP={'i','me','my','myself','mine','user'}
def ent(x):
    x=x.strip().strip('.,!?;:"\'()[]').strip().lower()
    x=re.sub(r'^(the|a|an)\s+','',x)
    return 'USER' if x in FP else x
def rel(x): return re.sub(r'[_\- ]+',' ',x.strip().lower())
def fmatch(tr,g):
    s,r,v=tr
    return ent(s)==ent(g['subject']) and ent(v)==ent(g['value']) and rel(r) in {rel(g['relation'])}|{rel(a) for a in g['relation_aliases']}
def key(t): return (ent(t[0]),rel(t[1]),ent(t[2]))
def ww(v,text): return re.search(r'(?<!\w)'+re.escape(v)+r'(?!\w)',text or '',re.I) is not None
def mode(p):
    if p['family'] in ('teach_varied',): return 'T'
    if p['family'] in ('ask_varied','backwards','chain','both_varied'): return 'A'
    if p['family'] in ('casual','control'): return p['note'][:1]
    return 'N'
cnt=collections.Counter(); tot=collections.Counter(); wv=collections.Counter(); junk=collections.Counter(); dis=[]
for p in P:
    b=B[p['id']]; f=p['family']; m=mode(p); tot[f]+=1
    st=[tuple(t) for t in b['stored_after_turn']]; ss={key(t) for t in b['stored_after_setup']}
    wrong=any(ww(v,b['turn_reply']) or ww(v,b['followup_reply'] or '') for v in p['must_not'])
    if f=='no_save':
        right=({key(t) for t in st}==ss) and not wrong
    else:
        store_ok=all(any(fmatch(t,g) for t in st) for g in p['gold_store']) and all(key(t) in ss or any(fmatch(t,g) for g in p['gold_store']) for t in st)
        if any(not(key(t) in ss or any(fmatch(t,g) for g in p['gold_store'])) for t in st): junk[f]+=1
        rep=b['followup_reply'] if m=='T' else b['turn_reply']
        if p['gold_answer']:
            parts=[x.strip() for x in p['gold_answer'].split(';')]
            ans_ok=all(x.lower() in (rep or '').lower() for x in parts) and not re.match(r"\s*i (don't|do not) know",rep or '',re.I)
        else:
            ans_ok=not any(ww(v,rep or '') for v in p['must_not'])
        right=store_ok and ans_ok and not wrong
    cnt[f]+=right; wv[f]+=wrong
    if right!=b['base_right'] or wrong!=b['base_wrong_value']: dis.append((p['id'],f,right,b['base_right'],wrong,b['base_wrong_value']))
for f in tot: print(f'{f:13s} right {cnt[f]:3d}/{tot[f]:3d}  wrong_value {wv[f]}  junk {junk[f]}')
print('TOTAL right',sum(cnt.values()),'/',sum(tot.values()),' wrong',sum(wv.values()),' junk',sum(junk.values()))
print('disagreements with writer:',len(dis)); [print('  ',d) for d in dis[:20]]
