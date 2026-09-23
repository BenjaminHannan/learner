import json,ast,sys,collections
D='artifacts/claude-correct252b-20260922/'
P=[json.loads(l) for l in open(D+'dev252b.jsonl')]
def L(x):
    if not isinstance(x,str): return x
    try: return json.loads(x)
    except Exception: return ast.literal_eval(x)
def T(ts): return {tuple(str(p).lower().strip() for p in t) for t in (L(ts) or [])}
def rows(f): return {r['id']:r for r in map(json.loads,open(f))}
A=rows(sys.argv[1]); B=rows(sys.argv[2]) if len(sys.argv)>2 else None
junk=[];rem=[];qw=[];fw=[];cd=[]
for p in P:
    r=A[p['id']]; sas=T(r['stored_after_setup']); sat=T(r['stored_after_turn']); saf=T(r['stored_after_followup'])
    es=T(p['expect_store']); eg=T(p['expect_gone'])
    for st,name in ((sat,'turn'),(saf,'followup')):
        extra=st-sas-es
        if extra: junk.append((p['id'],name,sorted(extra)))
        lost=sas-st-eg
        if lost: rem.append((p['id'],name,sorted(lost)))
    if p['family']=='question_tail' and sat!=sas: qw.append(p['id'])
    if saf!=sat: fw.append(p['id'])
    if p['family']=='control' and B is not None:
        b=B[p['id']]
        if any(r[k]!=b[k] for k in r if k!='ms_per_turn'): cd.append(p['id'])
print('junk',junk); print('wrong_removals',rem); print('question_writes',qw); print('followup_writes',fw); print('control_diffs',cd)
if B is not None:
    diff=[i for i in A if any(A[i][k]!=B[i][k] for k in A[i] if k!='ms_per_turn')]
    print('rows differing from ref:',len(diff),diff)
