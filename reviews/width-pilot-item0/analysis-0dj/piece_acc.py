from lib import *
import json
from domain.far import join_gap as JG
def run():
    for L in ['L13','L14']:
        A=json.load(open(S+f'out/audit2-{L}.json'))
        its={r['id']:r for r in items(L)}
        for cell in ['HO','HPO']:
            recs=A[cell]; s=JG.summarize(recs)
            n=len(recs)
            print(f'== {L} {cell}: n={n} split_ok={s["split_ok"]} strict={s["split_strict"]} piece_refused={s["piece_refused"]} join_refused={s["join_refused"]}')
            print(f'   W {s["W"]} ({s["W_pct"]}%)  P(both pieces right alone) {s["P"]} ({s["P_pct"]}%)  T(P and a*b join prompt right) {s["T"]} ({s["T_pct"]}%)  first_error {s["first_error"]}')
            # per piece alone: need K,J gold
            ka=ja=0; m=0; join_ref=0
            for r in recs:
                if not r['op'] or r['piece_refused'] or 'a' not in r: continue
                m+=1
            rows=[r for r in recs if r['op'] and not r['piece_refused']]
            # recompute piece golds
            import itertools
            kc=jc=0
            idmap={}
            for r in rows:
                pass
            print('   pieces answered:',len(rows))
run()
