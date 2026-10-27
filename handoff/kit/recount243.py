# Director recount for 243-fix panels: python3 recount243.py <exp> <rowsfile> <format>
import json,re,sys,collections
P={x['id']:x for x in map(json.loads,open('artifacts/claude-askpanel243-20260922/panel.jsonl'))}
B={x['id']:x for x in map(json.loads,open('artifacts/claude-askpanel243-20260922/base228.jsonl'))}
exp,f,fmt=sys.argv[1],sys.argv[2],sys.argv[3]
rows={x['id']:x for x in map(json.loads,open(f))}
def get(i):
    r=rows[i]
    if fmt=='nested': n=r[exp]; return n['reply'],n['stored_after_setup'],n['stored_after_question']
    return r['reply'],r.get('stored_after_setup'),r.get('stored_after_question')
def wv(p,rep):
    low=rep.lower(); vals=[v for s,rl,v in p['stated_facts']]
    ok=set() if p['expect']=='ABSTAIN' else {g.strip().lower() for g in (p['gold'] or '').split(';')}|{a.lower() for a in p['allowed_mentions']}
    return [v for v in vals if v.lower() not in ok and re.search(r'\b'+re.escape(v.lower())+r'\b',low)]
def right(p,rep):
    low=rep.lower().strip()
    return all(g.strip().lower() in low for g in p['gold'].split(';')) and not low.startswith(("i don't know","i do not know"))
t=collections.Counter(); wrong=[]; added=[]; qw=[]; ctrl=0; lost=[]
for i,p in P.items():
    rep,sa,sq=get(i); fam=p['family']; b=B[i]
    if p['expect'] in('ANSWER',): t[fam]+=right(p,rep)
    if p['expect']=='ABSTAIN': t[fam]+= not wv(p,rep)
    if p['expect']=='UNCHANGED': ctrl+= rep==b['base_reply']
    w=wv(p,rep)
    if w: wrong.append(i); 
    if w and rep!=b['base_reply']: added.append((i,w))
    if sa is not None and sq is not None and sorted(map(tuple,sa))!=sorted(map(tuple,sq)): qw.append(i)
    if b['base_right'] and p['expect']=='ANSWER' and not right(p,rep): lost.append(i)
print(exp,'right by family',dict(t)); print('controls identical',ctrl,'/12')
print('wrong-value items',len(wrong),wrong); print('ADDED wrong (reply differs from base228)',added)
print('question writes',qw); print('lost (base right -> not right)',lost)
