"""Interim reading of PREREG-G.md bars from G SNAP lines (same rule as g_score.py: T* = first read step with mean HO% >= 36.6; success = C1 on both seeds at T*)."""
import json, os, sys
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snaps')
READS = (4000, 6000, 8000, 10000, 12000, 14000, 16000)
for arm in sys.argv[1:]:
    S = {s: {r['step']: r for r in map(json.loads, open(os.path.join(D, f'g-{arm}-s{s}.jsonl')))} for s in ('93301', '31001')
         if os.path.exists(os.path.join(D, f'g-{arm}-s{s}.jsonl'))}
    if len(S) < 2:
        print(arm, 'incomplete'); continue
    print(f'== {arm}')
    tstar = None
    for st in READS:
        if not all(st in S[s] for s in S):
            continue
        ho = [100 * S[s][st]['HO'] / 420 for s in S]
        c1 = [S[s][st]['big'][2] and S[s][st]['big'][0] <= 1.0 for s in S]
        m = sum(ho) / 2
        flag = ''
        if tstar is None and m >= 36.6:
            tstar = st; flag = '  <- T*  ' + ('SUCCESS' if all(c1) else 'FAIL')
        print(f"  {st:>5} HO {ho[0]:5.1f}/{ho[1]:5.1f} mean {m:5.1f} | 6800 drop {[S[s][st]['big'][0] for s in S]} fired {[S[s][st]['big'][1] for s in S]} C1 {c1}"
              f" | worst {[S[s][st]['big'][3][0] for s in S]}{flag}")
    if tstar is None:
        print('  no T* yet')
