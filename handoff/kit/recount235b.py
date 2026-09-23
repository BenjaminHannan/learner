import json,re,sys
sys.path.insert(0,'scripts')
import claude_smolear235_model as E
D='artifacts/claude-smolear235b-20260922/run/'
A=json.load(open(D+'a_preds_gpu.json'))['preds']
P=[json.loads(l) for l in open('artifacts/claude-earpanel235b-20260922/panel.jsonl')]
FIRST={"i","me","my","myself","mine","user"}
def nv(x):
    x=' '.join(str(x or '').strip(" \t\"'.,;:!?()[]{}").split()).lower()
    x=re.sub(r'^(the|a|an)\s+','',x); return re.sub(r'\s+years old$','',x)
def ns(x): x=nv(x); return 'me' if x in FIRST else x
def plain(x): return re.sub(r'[\s_\-]+',' ',str(x).strip().lower())
def relok(pred,g,rel=None):
    rel=rel if rel is not None else g['relation']
    cands=[rel]+list(g.get('relation_aliases') or [])
    pc=E.canon_rel(pred) or pred
    return any((E.canon_rel(c) or c)==pc or plain(c)==plain(pred) for c in cands)
def tm(f,g): return ns(f['subject'])==ns(g['subject']) and relok(f['relation'],g) and nv(f['value'])==nv(g['value'])
def am(f,g):
    pr=f['relation'] if isinstance(f['relation'],list) else [f['relation']]
    gr=g['chain'] if g.get('chain') else [g['relation']]
    if ns(f['subject'])!=ns(g['subject']) or len(pr)!=len(gr): return False
    # aliases apply to last hop only (235 loader rule); earlier hops exact/canon
    for i,(p,q) in enumerate(zip(pr,gr)):
        ok = relok(p,g,q) if i==len(gr)-1 else ((E.canon_rel(p) or p)==(E.canon_rel(q) or q) or plain(p)==plain(q))
        if not ok: return False
    return True
REC={'plain_teach','varied_teach','full_names','corrections'}; STMT=REC|{'no_save'}
def arm_frames(x,turn,arm):
    if arm=='A': return [f for f in x['gate']['saved'] if f['act']=='TEACH'],[f for f in x['gate']['saved'] if f['act']=='ASK']
    fr=E.brake(E.parse_frames(x['raw']),turn) if arm=='A_brake' else E.parse_frames(x['raw'])
    fr=[f if isinstance(f,dict) else f for f in fr]
    return [f for f in fr if f.get('act')=='TEACH'],[f for f in fr if f.get('act')=='ASK']
for arm in ('A_raw','A_brake','A'):
    hit=gold=wrong=nosave=ahit=agold=uns=0; wids=[]
    for it in P:
        x=A[it['id']]; T,Q=arm_frames(x,it['turn'],arm)
        g=[f for f in it['gold'] if f['act']=='TEACH']; used=set(); extra=0
        for f in T:
            j=next((k for k,gg in enumerate(g) if k not in used and tm(f,gg)),None)
            if j is None: extra+=1
            else: used.add(j)
        if it['family'] in REC: hit+=len(used); gold+=len(g); uns+=len([u for u in x['gate']['unsure']]) if arm=='A' else 0
        if it['family'] in STMT and extra: wrong+=extra; wids.append((it['id'],it['family']))
        if it['family']=='no_save': nosave+=len(T)
        if it['family'] in ('questions','chain_questions'):
            ga=[f for f in it['gold'] if f['act']=='ASK']; agold+=len(ga); u2=set()
            for f in Q:
                j=next((k for k,gg in enumerate(ga) if k not in u2 and am(f,gg)),None)
                if j is not None: u2.add(j)
            ahit+=len(u2)
    print(arm,'recall',hit,'/',gold,f'{100*hit/gold:.1f}%','wrong',wrong,'no_save saved',nosave,'ask',ahit,'/',agold,'unsure',uns)
    if arm=='A': print('  wrong ids:',wids)
