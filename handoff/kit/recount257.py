import json,collections,sys
D='artifacts/claude-smolear257-20260922/'
A=json.load(open(D+'run/a_preds_gpu.json'))['preds']
P={json.loads(l)['id']:json.loads(l) for l in open('artifacts/claude-earpanel257-20260922/panel.jsonl')}
T=json.load(open(D+'relation_table_v2.json'))['relations']
def rn(r): return str(r).lower().strip().replace(' ','_').replace('-','_')
canon={}
for e in T:
    for w in [e['name']]+e.get('aliases',[])+e.get('storage_keys',[]):
        canon.setdefault(rn(w),rn(e['name']))
SPK={'i','me','my','myself','mine'}
def sn(s):
    s=str(s).strip().strip('.,!?;:"\'').lower()
    return 'me' if s in SPK else s
def vn(v): return str(v).strip().strip('.,!?;:"\'').lower()
def relok(pr,g):
    ok={rn(g['relation'])}|{rn(a) for a in g.get('relation_aliases') or []}
    p=rn(pr)
    return p in ok or canon.get(p,'#1')==canon.get(rn(g['relation']),'#2') or canon.get(p,'#1') in ok
def teach_match(f,g):
    return g['act']=='TEACH' and f.get('act')=='TEACH' and sn(f['subject'])==sn(g['subject']) and vn(f['value'])==vn(g['value']) and relok(f['relation'],g)
def ask_match(f,g):
    if not(g['act']=='ASK' and f.get('act')=='ASK' and sn(f['subject'])==sn(g['subject'])): return False
    if g.get('chain'):
        fc=f.get('chain')
        if not fc or len(fc)!=len(g['chain']): return False
        ca=g.get('chain_aliases') or [[]]*len(g['chain'])
        return all(relok(x,{'relation':gc,'relation_aliases':al}) for x,gc,al in zip(fc,g['chain'],ca))
    return not f.get('chain') and relok(f['relation'],g)
tot=collections.Counter(); fam=collections.defaultdict(collections.Counter); wrong=[]
for i,p in P.items():
    a=A[i]['gate']; saved=a['saved']; unsure=a['unsure']
    gt=[g for g in p['gold'] if g['act']=='TEACH']; ga=[g for g in p['gold'] if g['act']=='ASK']
    st=[f for f in saved if f.get('act')=='TEACH']; sa=[f for f in saved if f.get('act')=='ASK']
    hit=sum(any(teach_match(f,g) for f in st) for g in gt)
    uns=sum((not any(teach_match(f,g) for f in st)) and any(teach_match(f,g) for f in unsure) for g in gt)
    w=[f for f in st if not any(teach_match(f,g) for g in gt)]
    ah=sum(any(ask_match(f,g) for f in sa) for g in ga)
    tot['teach_gold']+=len(gt); tot['teach_hit']+=hit; tot['unsure_of_gold']+=uns; tot['wrong']+=len(w)
    tot['ask_gold']+=len(ga); tot['ask_hit']+=ah
    if p['family']=='no_save': tot['no_save_saves']+=len(st)
    fam[p['family']]['gold']+=len(gt); fam[p['family']]['hit']+=hit; fam[p['family']]['wrong']+=len(w)
    for f in w: wrong.append((i,p['family'],f['subject'],f['relation'],f['value']))
print(dict(tot)); print({k:dict(v) for k,v in fam.items()})
print('wrong saves:'); [print(' ',x) for x in wrong]
