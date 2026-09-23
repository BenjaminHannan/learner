"""Independent recount of 138m marks M1, M2 (row-level), M4, M5, M6 from saved rows."""
import json, hashlib, statistics, glob, os, re
M='artifacts/claude-merge138m-20260922/run'; L='artifacts/claude-merge138l-20260922/run'
P=json.load(open('artifacts/claude-merge138m-20260922/predicted_moves138m.json'))
out={}
# ---- M1
HEAD={'219':'head','230':'head','227':'head','227b':'head'}
m1={'moved':0,'unpred':[],'wrong':[],'not_moved':[],'own_vs_m_same_nonpred':0,'per_piece':{}}
for piece in ['219','230','230c','227','227b','227c','224c','233','234']:
    ref=json.load(open(f'{M}/l1/{piece}-{HEAD.get(piece,"own")}.json'))
    mm=json.load(open(f'{M}/l1/{piece}-m.json'))
    key=lambda r:(r.get('id'))
    R={key(r):r for r in ref}; MM={key(r):r for r in mm}
    assert len(R)==len(ref) and len(MM)==len(mm) and set(R)==set(MM), piece
    pred=P['m1'].get(piece,{})
    rec=lambda r:{k:r.get(k) for k in ('lines','writes','snap')}
    moved=[i for i in R if rec(R[i])!=rec(MM[i])]
    m1['per_piece'][piece]={'n':len(R),'moved':len(moved)}
    m1['moved']+=len(moved)
    for i in moved:
        if i not in pred: m1['unpred'].append(f'{piece}:{i}')
        elif rec(MM[i])!={k:pred[i]['expect_m'].get(k) for k in ('lines','writes','snap')}: m1['wrong'].append(f'{piece}:{i}')
    for i in pred:
        if i not in moved: m1['not_moved'].append(f'{piece}:{i}')
    # own-arm vs head for pieces where head differs (information only)
out['M1']=m1
# ---- M2 direct row compare 138m vs 138l
def diffrows(a,b,drop=('seconds',)):
    A={r['id']:r for r in a}; B={r['id']:r for r in b}
    strip=lambda r:{k:v for k,v in r.items() if k not in drop}
    return sorted(i for i in set(A)|set(B) if strip(A.get(i,{}))!=strip(B.get(i,{}))), len(A), len(B)
def jl(p): return [json.loads(x) for x in open(p) if x.strip()]
m2={}
for f in ['bench-bench132_4hop-rows.jsonl','bench-edit200-rows.jsonl','bench-new_121_4hop-rows.jsonl','bench-old_s2fresh_4hop-rows.jsonl']:
    d,na,nb=diffrows(jl(f'{L}/sd/{f}'),jl(f'{M}/sd/{f}')); m2[f]={'n':[na,nb],'moved':d}
for f in ['bench-rows-fable_edit_200.jsonl','bench-rows-s2fresh_4hop.jsonl']:
    d,na,nb=diffrows(jl(f'{L}/sd/marks123/{f}'),jl(f'{M}/sd/marks123/{f}')); m2['marks123/'+f]={'n':[na,nb],'moved':d}
d,na,nb=diffrows(jl(f'{L}/sd136/rt136-rows.json'),jl(f'{M}/sd136/rt136-rows.json')); m2['rt136']={'n':[na,nb],'moved':d}
# sessions152: dict family -> list
sl=json.load(open(f'{L}/sd/sessions152-rows.json')); sm=json.load(open(f'{M}/sd/sessions152-rows.json'))
mv=[];nt=0
for fam in sl:
    for a,b in zip(sl[fam],sm[fam]):
        nt+=1
        if a!=b: mv.append(f"{fam}#{a['n']}")
m2['sessions152']={'n':nt,'moved':mv,'bad_label_m':[f"{fam}#{r['n']}:{r['verdict']}" for fam in sm for r in sm[fam] if r['verdict'] not in ('OK',)]}
# rt143 nogate
a=json.load(open(f'{L}/rt143nogate-l.json')); b=json.load(open(f'{M}/rt143nogate-m.json'))
A={r['id']:r for r in a}; B={r['id']:r for r in b}
m2['rt143']={'n':[len(A),len(B)],'moved':sorted(i for i in A if A[i]!=B.get(i)),'triples_changed':sorted(i for i in A if A[i].get('triples')!=B[i].get('triples') or A[i].get('teach_replies')!=B[i].get('teach_replies'))}
# verdict labels compare for bench/rt136
for k in ['bench-bench132_4hop-rows.jsonl','bench-edit200-rows.jsonl','bench-new_121_4hop-rows.jsonl','bench-old_s2fresh_4hop-rows.jsonl']:
    A={r['id']:r for r in jl(f'{L}/sd/{k}')}; B={r['id']:r for r in jl(f'{M}/sd/{k}')}
    m2[k]['verdict_flips']=[(i,A[i].get('verdict'),B[i].get('verdict')) for i in A if A[i].get('verdict')!=B[i].get('verdict')]
    m2[k]['exact_flips']=[i for i in A if A[i].get('exact')!=B[i].get('exact')]
A={r['id']:r for r in jl(f'{L}/sd136/rt136-rows.json')}; B={r['id']:r for r in jl(f'{M}/sd136/rt136-rows.json')}
m2['rt136']['verdict_flips']=[(i,A[i]['verdict'],B[i]['verdict']) for i in A if A[i]['verdict']!=B[i]['verdict']]
m2['rt136']['stored_changed']=[i for i in A if A[i]['stored']!=B[i]['stored']]
m2['rt136']['replies']={i:[A[i]['reply'],B[i]['reply']] for i in m2['rt136']['moved']}
out['M2']=m2
# ---- M4
h={}
for i in (1,2,3):
    for f in sorted(glob.glob(f'{M}/bench{i}/bench-*-rows.jsonl')):
        h.setdefault(os.path.basename(f),[]).append(hashlib.sha256(open(f,'rb').read()).hexdigest())
out['M4']={k:len(set(v))==1 and len(v)==3 for k,v in h.items()}
# ---- M5
def lat(pref):
    xs=[]
    for f in glob.glob(f'{M}/lat-{pref}-*.json'):
        d=json.load(open(f))
        def walk(o):
            if isinstance(o,dict):
                for k,v in o.items():
                    if k in('times_ms',) and isinstance(v,list): xs.extend(v)
                    else: walk(v)
            elif isinstance(o,list):
                for v in o: walk(v)
        walk(d)
    return xs
xl,xm=lat('l'),lat('m')
out['M5']={'n':[len(xl),len(xm)],'med':[statistics.median(xl) if xl else None, statistics.median(xm) if xm else None]}
# ---- M6
m6={'changes':[],'ev_diff':[],'stored_diff':[],'dup_fail':[],'unpred':[],'pred_missing':[]}
pred6=P['m6']['reply_changes']
for f in ['p3-dialogs','p3c-restart2','p3d-ghost','v-dialogs','v-supp']:
    a=json.load(open(f'{M}/probe/l-{f}.json'))['rows']; b=json.load(open(f'{M}/probe/m-{f}.json'))['rows']
    assert len(a)==len(b)
    for da,db in zip(a,b):
        if not db.get('dup_ok_all',True): m6['dup_fail'].append(f"{f}:{db['dialog']}")
        if da.get('stored')!=db.get('stored'): m6['stored_diff'].append(f"{f}:{db['dialog']}")
        if [x.get('fast') for x in da.get('audits',[])]!=[x.get('fast') for x in db.get('audits',[])]: m6['stored_diff'].append(f"{f}:{db['dialog']}:audit")
        for j,(ta,tb) in enumerate(zip(da['turns'],db['turns'])):
            k=f"{f}:d{db['dialog']:02d}:t{j:02d}"
            if ta.get('events')!=tb.get('events'): m6['ev_diff'].append(k)
            if ta['reply']!=tb['reply']:
                m6['changes'].append([k,tb['turn'],ta['reply'],tb['reply']])
                if k not in pred6 or pred6[k]['m']!=tb['reply']: m6['unpred'].append(k)
for k in pred6:
    if k not in [c[0] for c in m6['changes']]: m6['pred_missing'].append(k)
out['M6']=m6
json.dump(out,open('artifacts/claude-verify-20260922/138m/recount.json','w'),indent=1)
print(json.dumps({'M1':{k:(v if not isinstance(v,list) else len(v)) for k,v in m1.items()},'M4':out['M4'],'M5':out['M5']},indent=0))
for k,v in m2.items(): print('M2',k,v.get('n'),len(v['moved']),{kk:(vv if not isinstance(vv,(list,dict)) or len(vv)<8 else len(vv)) for kk,vv in v.items() if kk not in('n','moved')})
print('M6',{k:(len(v)) for k,v in m6.items()}, m6['unpred'], m6['pred_missing'])
# ---- M1 for 224c/233 (their own schemas)
res={}
for piece in ['224c','233']:
    a={r['id']:r for r in json.load(open(f'{M}/l1/{piece}-own.json'))}; b={r['id']:r for r in json.load(open(f'{M}/l1/{piece}-m.json'))}
    rec=lambda r:{'setup':r['setup_replies'],'reply':r['reply'],'w':r.get('writes',r.get('triples_after')),'q':r.get('qwrite')}
    mv=[i for i in a if rec(a[i])!=rec(b[i])]; bad=[]
    for i in mv:
        e=P['m1'][piece].get(i)
        if not e: bad.append(('unpred',i)); continue
        e=e['expect_m']
        if e['setup']!=b[i]['setup_replies'] or e['reply']!=b[i]['reply'] or e.get('triples_after',b[i].get('triples_after'))!=b[i].get('triples_after') or e.get('writes',b[i].get('writes'))!=b[i].get('writes'): bad.append(('wrong',i))
    res[piece]={'n':len(a),'moved':len(mv),'bad':bad,'not_moved':[i for i in P['m1'][piece] if i not in mv]}
out['M1_224c_233']=res
json.dump(out,open('artifacts/claude-verify-20260922/138m/recount.json','w'),indent=1)
print('M1 224c/233',res)
