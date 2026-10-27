import json,re,sys,collections
sys.path.insert(0,'scripts')
import claude_smolear235_model as E
s=json.load(open('artifacts/claude-smolear235-20260922/run/score.json'))
FIRST={"i","me","my","myself","mine","user"}
def nv(x):
    x=' '.join(str(x or '').strip(" \t\"'.,;:!?()[]{}").split()).lower()
    x=re.sub(r'^(the|a|an)\s+','',x); return re.sub(r'\s+years old$','',x)
def ns(x): x=nv(x); return 'me' if x in FIRST else x
def plain(x): return re.sub(r'[\s_\-]+',' ',str(x).strip().lower())
def relok(pred,g):
    pc=E.canon_rel(pred) or pred
    cands=list(g['relation'] if isinstance(g['relation'],list) else [g['relation']])
    for al in g.get('aliases') or []: cands+= (al if isinstance(al,list) else [al])
    return any((E.canon_rel(c) or c)==pc or plain(c)==plain(pred) for c in cands)
def m(f,g): return ns(f['subject'])==ns(g['subject']) and relok(f['relation'],g) and nv(f['value'])==nv(g['value'])
STMT={'plain_teach','varied_teach','full_names','corrections','no_save'}; REC={'plain_teach','varied_teach','full_names','corrections'}
for arm in ('A','B'):
    hit=gold=wrong=0; wrong_ids=[]; nosave=0
    for r in s['rows']:
        golds=[g for g in r['gold'] if g.get('act')=='TEACH']
        fr=[f for f in r['kept'] if f.get('act')=='TEACH'] if arm=='A' else [{'subject':t[0],'relation':t[1],'value':t[2]} for t in ((r.get('b') or {}).get('triples') or [])]
        used=set(); h=0; extra=0
        for f in fr:
            j=next((k for k,g in enumerate(golds) if k not in used and m(f,g)),None)
            if j is None: extra+=1
            else: used.add(j); h+=1
        if r['family'] in REC: hit+=h; gold+=len(golds)
        if r['family'] in STMT and extra: wrong+=extra; wrong_ids.append(r['id'])
        if r['family']=='no_save': nosave+=len(fr)
    print(arm,'M3',hit,'/',gold,'M2 wrong saves',wrong,wrong_ids,'M1 no_save saves',nosave)
