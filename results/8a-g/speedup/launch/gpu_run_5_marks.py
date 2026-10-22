"""gpu_run_5_marks.py: the readout of GPU-RUN-5 against PREREG-gpu-run-5.md (the coordinator's ruling of 10-20, point d). Pure: reads e4floor.py's json and nothing else; in
particular GPU-RUN-4's E4 trace never enters (ruling point a).

  python gpu_run_5_marks.py IN.json [--md OUT.md] [--out OUT.json]

Over updates 101-300 (indices 100..299) of each trace:
  AA  = mean |dloss| of each of the 3 B-B pairs;  AB = the same for each of the 9 B-D pairs.
  PASS needs both: (i) median of the 9 AB <= the largest AA; (ii) the 3 D window means do not all lie outside the B range on the same side.
  "It's just drift" proved wrong (defer closed for good): every AA < 0.02 AND every AB > every AA.
  Any AA >= 0.02: record that 0.02 is too tight for FUTURE B3G2 sheets only.
  Fewer than 6 traces or a trace shorter than 300 updates: no PASS (one rental, no re-run bids: recorded as FAIL, incomplete).
"""
import argparse, itertools, json, statistics as st

LO, HI, LIMIT = 100, 300, 0.02


def window(ls):
    return [float(x) for x in ls[LO:HI]]


def mad(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def readout(res):
    tr = res.get('traces') or []
    B = [t for t in tr if t.get('kind') == 'B']
    D = [t for t in tr if t.get('kind') == 'D']
    order = ''.join(t.get('kind', '?') for t in tr)
    complete = order == 'BDBDBD' and all(len(t.get('losses') or []) >= HI for t in tr)
    out = dict(sheet='PREREG-gpu-run-5.md', order=order, complete=complete, window_updates=[LO + 1, HI], K0=res.get('K0'), curve_updates=res.get('curve_updates'),
               traces=[dict(label=t.get('label'), kind=t.get('kind'), n=len(t.get('losses') or []), window_mean=(st.mean(window(t['losses'])) if len(t.get('losses') or []) >= HI else None),
                            started_utc=t.get('started_utc'), wall_s=t.get('wall_s')) for t in tr])
    if not complete:
        out.update(verdict='FAIL', why='incomplete: fewer than 6 traces in the order BDBDBD or a trace shorter than 300 updates (one rental, no re-run bids)', closed_for_good=False)
        return out
    wB, wD = [window(t['losses']) for t in B], [window(t['losses']) for t in D]
    AA = [dict(pair=f'{B[i]["label"]}-{B[j]["label"]}', mad=mad(wB[i], wB[j])) for i, j in itertools.combinations(range(3), 2)]
    AB = [dict(pair=f'{B[i]["label"]}-{D[j]["label"]}', mad=mad(wB[i], wD[j])) for i in range(3) for j in range(3)]
    aa, ab = [x['mad'] for x in AA], [x['mad'] for x in AB]
    mB, mD = [st.mean(w) for w in wB], [st.mean(w) for w in wD]
    lo, hi = min(mB), max(mB)
    all_above, all_below = all(m > hi for m in mD), all(m < lo for m in mD)
    c1 = st.median(ab) <= max(aa)
    c2 = not (all_above or all_below)
    drift_wrong = all(x < LIMIT for x in aa) and min(ab) > max(aa)
    DD = [dict(pair=f'{D[i]["label"]}-{D[j]["label"]}', mad=mad(wD[i], wD[j])) for i, j in itertools.combinations(range(3), 2)]      # INFORMATION ONLY: not a bar, never read by the verdict
    out.update(DD_information_only=DD, AA=AA, AB=AB, max_AA=max(aa), median_AB=st.median(ab), min_AB=min(ab), B_window_means=mB, D_window_means=mD, D_all_above_B=all_above, D_all_below_B=all_below,
               pass_i_median_AB_le_max_AA=c1, pass_ii_D_not_all_outside_B_same_side=c2, drift_proved_wrong=drift_wrong,
               limit_too_tight_for_future_B3G2=any(x >= LIMIT for x in aa))
    out['verdict'] = 'PASS' if (c1 and c2) else 'FAIL'
    out['closed_for_good'] = bool(drift_wrong)
    if out['verdict'] == 'PASS':
        out['allows'] = 'PASS: the defer port goes to code review; defer only in fresh runs from update 0 under new names; no change to 8aB3G2A4/A8'
    elif drift_wrong:
        out['allows'] = 'FAIL, and "it is just drift" is proved wrong: every AA < 0.02 and every AB > every AA. defer is closed for good'
    else:
        out['allows'] = 'FAIL: final (one rental, no re-run bids)'
    out['note_0_02'] = ('at least one B-B pair is >= 0.02: record that 0.02 is too tight for FUTURE B3G2 sheets only (it does not re-judge GPU-RUN-4 or this run)'
                        if out['limit_too_tight_for_future_B3G2'] else 'every B-B pair < 0.02')
    return out


def render(r):
    L = ['# GPU-RUN-5 readout against PREREG-gpu-run-5.md', '', f'**verdict: {r["verdict"]}** — {r.get("allows", r.get("why"))}', '',
         f'order {r["order"]}, complete {r["complete"]}, K0 {r.get("K0")}, window updates {r["window_updates"][0]}-{r["window_updates"][1]}', '']
    L += ['| trace | kind | updates | window mean loss | started |', '|---|---|---|---|---|']
    L += [f'| {t["label"]} | {t["kind"]} | {t["n"]} | {"-" if t["window_mean"] is None else f"{t["window_mean"]:.5f}"} | {t["started_utc"]} |' for t in r['traces']]
    if 'AA' in r:
        L += ['', '| pair | mean abs dloss |', '|---|---|'] + [f'| {x["pair"]} (B-B) | {x["mad"]:.5f} |' for x in r['AA']] + [f'| {x["pair"]} (B-D) | {x["mad"]:.5f} |' for x in r['AB']]
        L += ['', f'- (i) median AB {r["median_AB"]:.5f} <= max AA {r["max_AA"]:.5f}: {r["pass_i_median_AB_le_max_AA"]}',
              f'- (ii) D window means {[round(m, 5) for m in r["D_window_means"]]} not all outside the B range {[round(min(r["B_window_means"]), 5), round(max(r["B_window_means"]), 5)]} on one side: {r["pass_ii_D_not_all_outside_B_same_side"]}',
              f'- drift proved wrong (every AA < 0.02 and min AB {r["min_AB"]:.5f} > max AA): {r["drift_proved_wrong"]}', f'- {r["note_0_02"]}',
              '- information only, not a bar (D-D drift): ' + ', '.join(f'{x["pair"]} {x["mad"]:.5f}' for x in r['DD_information_only'])]
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('--md'); ap.add_argument('--out')
    a = ap.parse_args(argv)
    r = readout(json.load(open(a.inp)))
    if a.out:
        json.dump(r, open(a.out, 'w'), indent=1)
    md = render(r)
    if a.md:
        open(a.md, 'w').write(md)
    print(md)
    return r


if __name__ == '__main__':
    main()
