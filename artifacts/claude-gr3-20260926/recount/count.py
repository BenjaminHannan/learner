import json, sys, io, contextlib
P='/home/user/learner/artifacts/claude-panel-gr3-20260926/'
Rn='/home/user/learner/artifacts/claude-gr3-20260926/run/'
def load(p): return [json.loads(l) for l in open(p) if l.strip()]
panel={k:load(P+k+'.jsonl') for k in ['squares','unseen','lookalikes']}
run={k:load(Rn+'L_'+k+'.jsonl') for k in ['squares','unseen','lookalikes','general']}
sys.path.insert(0,'/home/user/learner/scripts')
buf=io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
    import claude_puzzle_reader as R
    import claude_dl1_nights as D1
    gen300=D1.harm_panel()
def readC(t):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        r=R.read_latin(t)
    return r
out={}
# id checks
for k in ['squares','unseen','lookalikes']:
    pid=[r['id'] for r in panel[k]]; rid=[r['id'] for r in run[k]]
    out[f'rows_panel_{k}']=len(pid); out[f'rows_run_{k}']=len(rid)
    out[f'ids_match_order_{k}']=pid==rid
    out[f'ids_match_set_{k}']=(set(pid)==set(rid) and len(set(pid))==len(pid) and len(set(rid))==len(rid))
out['rows_run_general']=len(run['general']); out['general_300']=len(run['general'])==300
out['C_general_items']=len(gen300)
rmap={k:{r['id']:r for r in run[k]} for k in run}
fields={'L':'grid','G2':'grid_gr2','P':'grid_pertoken'}
def reading(arm,k,prow):
    if arm=='C':
        r=readC(prow['text'])
        return None if r is None else r.get('grid')
    return rmap[k][prow['id']].get(fields[arm])
for arm in ['L','G2','P','C']:
    for k in ['squares','unseen']:
        ex=wr=no=0
        for pr in panel[k]:
            g=reading(arm,k,pr)
            if g is None: no+=1
            elif g==pr['grid']: ex+=1
            else: wr+=1
        out[f'{arm}_{k}_exact']=ex; out[f'{arm}_{k}_wrong']=wr; out[f'{arm}_{k}_none']=no
    fs=0
    for pr in panel['lookalikes']:
        if pr['square'] is None:
            if arm=='C':
                r=readC(pr['text']); nn = r is not None
            else:
                nn = reading(arm,'lookalikes',pr) is not None
            if nn: fs+=1
    out[f'{arm}_lookalikes_false_square']=fs
    if arm=='C':
        out['C_general_read_as_square']=sum(readC(d['q']) is not None for d in gen300)
    else:
        out[f'{arm}_general_read_as_square']=sum(r.get(fields[arm]) is not None for r in run['general'])
out['lookalikes_truth_square']=sum(pr['square'] is not None for pr in panel['lookalikes'])
out['lookalikes_truth_none']=sum(pr['square'] is None for pr in panel['lookalikes'])
out['size_said_right_squares']=sum(rmap['squares'][pr['id']].get('size_said')==pr['size'] for pr in panel['squares'])
out['size_said_right_unseen']=sum(rmap['unseen'][pr['id']].get('size_said')==pr['size'] for pr in panel['unseen'])
out['size_said_none_lookalikes_truth_none']=sum(pr['square'] is None and rmap['lookalikes'][pr['id']].get('size_said') is None for pr in panel['lookalikes'])
# L per-size
for s in [4,5,6,7]:
    tot=[pr for pr in panel['squares'] if pr['size']==s]
    out[f'L_squares_size{s}_total']=len(tot)
    out[f'L_squares_size{s}_exact']=sum(rmap['squares'][pr['id']]['grid']==pr['grid'] for pr in tot)
out['squares_other_size_rows']=sum(pr['size'] not in (4,5,6,7) for pr in panel['squares'])
sm=lg=same=0
for pr in panel['squares']:
    g=rmap['squares'][pr['id']]['grid']
    if g is not None and g!=pr['grid']:
        n=len(g)
        if n<pr['size']: sm+=1
        elif n>pr['size']: lg+=1
        else: same+=1
out['L_wrong_smaller']=sm; out['L_wrong_larger']=lg; out['L_wrong_same']=same
out['size_field_equals_truth_rows_squares']=sum(pr['size']==len(pr['grid']) for pr in panel['squares'])
L=out
L['R1']=out['L_squares_exact']>=97; L['R2']=out['L_lookalikes_false_square']<=1
L['R3']=out['L_squares_wrong']<=1; L['R4']=out['L_general_read_as_square']==0
L['U1']=out['L_unseen_exact']>=48; L['U2']=out['L_unseen_wrong']<=2
for k,v in out.items(): print(k, v)
