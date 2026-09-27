#!/usr/bin/env python3
"""Score existing single reads using two complete blind judgments; print counts only.
This is never a reader, trainer or threshold sweep. Existing RESULTS are not replaced.
"""
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from claude_lis319_fullclaim import load
from claude_lis319k_score import score
from claude_lis320_score import decide

def dump(p,d):
    with p.open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dir',required=True);ap.add_argument('--judge1',required=True);ap.add_argument('--judge2',required=True);a=ap.parse_args()
    d=Path(a.dir);pairs=load(d/'blind_pairs.jsonl');js=[load(a.judge1),load(a.judge2)]
    expected={r['pid'] for r in pairs}
    if len(expected)!=len(pairs):raise ValueError('duplicate pair IDs')
    for j in js:
        if len(j)!=len(pairs) or {r['pid'] for r in j}!=expected or any(type(r['same']) is not bool for r in j):raise ValueError('judge coverage or boolean schema failed')
    panel=load('artifacts/claude-readpanel320-20260926/panel.jsonl')
    pids={r['id'] for r in panel};ks={};xs={};bykind={}
    if len(panel)!=336 or len(pids)!=336:raise ValueError('sealed panel row count mismatch')
    for arm in ('old','new'):
        reads=load(d/f'reads_panel_{arm}.jsonl')
        if len(reads)!=336 or {r['id'] for r in reads}!=pids:raise ValueError('read coverage failed')
        # No re-inference: the registered scorer processes saved read files.
        k=score(panel,reads,pairs,js);ks[arm]=k;dump(d/f'score_{arm}.json',k)
        x=json.loads((d/f'extra_{arm}.json').read_text());xs[arm]=x
        if x['missing_rows'] or x['rows']!=336:raise ValueError('extra count coverage failed')
        bykind[arm]={kind:score([r for r in panel if r['kind']==kind],reads,pairs,js) for kind in sorted({r['kind'] for r in panel})}
        earlier=[]
        for row in panel:
            facts=[g for g in row['facts'] if g.get('correction') and g.get('needs_history')]
            if facts:earlier.append(dict(row,facts=facts))
        sub=score(earlier,reads,pairs,js)
        bykind[arm]['corrections_owner_in_history']={k:sub[k] for k in ('correction_right','correction_gold')}
    decision=decide(ks['old'],ks['new'],xs['old'],xs['new'])
    cvalid=ks['old']['correction_gold']-ks['old']['correction_right']>=20
    delta=ks['new']['correction_right']-ks['old']['correction_right']
    c1=dict(verdict='INCONCLUSIVE' if not cvalid else 'PASS' if delta>=10 else 'FAIL',valid=cvalid,proved_wrong=cvalid and delta<=2,improvement=delta,old_missed=ks['old']['correction_gold']-ks['old']['correction_right'])
    verdict=dict(registered=decision,C1=c1,old=ks['old'],new=ks['new'],extra_old=xs['old'],extra_new=xs['new'],judge_pairs=len(pairs),judge_disagreements=sum(x['same']!=next(r['same'] for r in js[1] if r['pid']==x['pid']) for x in js[0]))
    dump(d/'VERDICT.json',verdict);dump(d/'PER-KIND.json',bykind)
    print(json.dumps({'R1-R7':decision,'C1':c1,'panel_rows':336,'judge_pairs':len(pairs)}))
if __name__=='__main__':main()
