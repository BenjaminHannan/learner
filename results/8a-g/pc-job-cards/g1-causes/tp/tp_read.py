# Read-only readout of test T-P (self-found programs, 3M s400) against G1's 3M s400 B2 and the sealed marks of
# G1-OTHER-CAUSES-RANKED-2026-10-12 section 3. Run:  python tp_read.py [RESULTS_ROOT] [--tp DIR_OF_B2] [--g1 DIR_OF_B2]
# RESULTS_ROOT default C:\Users\benja\custom-io\work\results. Writes nothing. ASCII output only.
#   T-P run  = the newest of 8aTP-pc/8aTP-3M-s400, 8aTPb-pc/8aTPb-3M-s400, 8aTPc-pc/... (spill relaunches) that has B2\RESULT.json
#   baseline = 8aG1d-pc/8aG1d-3M-s400/B2 (G1 3M s400 B2: four families 219/720 = 30.4%)
# Marks (sealed): PASS = four families >= 38.4% AND pooled-5 >= 72.5 AND chain-5 >= 99; PROVED WRONG = four families <= 32.4%; otherwise BETWEEN -> run s401.
import argparse, json, os, sys

SPLITS = ['in_dist', 'answer', 'frame', 'vocab', 'variant']          # pooled-5 (NOT 'family')
FOUR = ['table_lookup', 'seq_next', 'fewshot_number_rule', 'rule_apply']
PASS_FOUR, PASS_POOLED, PASS_CHAIN, WRONG_FOUR = 38.4, 72.5, 99.0, 32.4
G1_FOUR = (219, 720)
DEFAULT_ROOT = r'C:\Users\benja\custom-io\work\results'


def load(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def scores(res):
    """RESULT.json -> dict(pooled5, chain5, four (c, n), fam {name: (c, n)}, status, steps, n_params)."""
    fe = res.get('final_eval') or {}
    c = sum(fe[s]['correct'] for s in SPLITS if s in fe)
    n = sum(fe[s]['n'] for s in SPLITS if s in fe)
    fam = {f: (sum(fe[s].get('by_family', {}).get(f, {}).get('correct', 0) for s in SPLITS if s in fe),
               sum(fe[s].get('by_family', {}).get(f, {}).get('n', 0) for s in SPLITS if s in fe)) for f in FOUR}
    chain = ((res.get('chain5') or {}).get('intact') or {}).get('exact')
    return dict(pooled5=100.0 * c / n if n else None, pooled_cn=(c, n), chain5=chain, fam=fam,
                four=(sum(v[0] for v in fam.values()), sum(v[1] for v in fam.values())), splits={s: fe[s]['exact'] for s in SPLITS if s in fe},
                status=res.get('status'), steps=res.get('steps'), n_params=res.get('n_params'), wall_s=res.get('wall_s'))


def events(stdout):
    out = []
    try:
        with open(stdout, encoding='utf-8', errors='replace') as f:
            for ln in f:
                if ln.startswith('{') and '"event": "train"' in ln:
                    try:
                        out.append(json.loads(ln))
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def find_tp(root):
    """-> (B2 dir, queue name) of the newest T-P run with a RESULT.json; else of the newest folder that exists at all; else (None, None)."""
    names = ['8aTP'] + ['8aTP' + c for c in 'bcdefgh']
    have, any_ = [], []
    for q in names:
        d = os.path.join(root, q + '-pc', q + '-3M-s400', 'B2')
        if os.path.isdir(d):
            any_.append((d, q))
            if os.path.exists(os.path.join(d, 'RESULT.json')):
                have.append((d, q))
    return (have or any_ or [(None, None)])[-1]


def pct(c, n):
    return 100.0 * c / n if n else float('nan')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('root', nargs='?', default=DEFAULT_ROOT)
    ap.add_argument('--tp', help='the T-P B2 folder (default: found under ROOT)')
    ap.add_argument('--g1', help="G1's 3M s400 B2 folder (default: ROOT/8aG1d-pc/8aG1d-3M-s400/B2)")
    a = ap.parse_args(argv)
    g1d = a.g1 or os.path.join(a.root, '8aG1d-pc', '8aG1d-3M-s400', 'B2')
    tpd, q = (a.tp, 'given') if a.tp else find_tp(a.root)
    g1r = load(os.path.join(g1d, 'RESULT.json'))
    tpr = load(os.path.join(tpd, 'RESULT.json')) if tpd else None
    print('T-P readout (3M s400, B2)   root %s' % a.root)
    print('  G1 baseline : %s %s' % (g1d, 'ok' if g1r else 'MISSING'))
    print('  T-P run     : %s (queue %s) %s' % (tpd, q, 'ok' if tpr else 'NOT FINISHED / MISSING (no B2\\RESULT.json)'))
    G = scores(g1r) if g1r else None
    T = scores(tpr) if tpr else None
    if G and G['four'] != G1_FOUR:
        print('  WARNING: the baseline four-family count %d/%d is not the sealed %d/%d' % (G['four'] + G1_FOUR))
    if T:
        print('  T-P status %s, steps %s, params %s, wall %.1f h' % (T['status'], T['steps'], '{:,}'.format(T['n_params'] or 0), (T['wall_s'] or 0) / 3600))
    print()
    print('Scores (correct/n pooled over in_dist answer frame vocab variant)')
    print('  %-26s %12s %12s %9s' % ('', 'G1 3M s400', 'T-P', 'T-P - G1'))
    row = lambda name, g, t, fmt: print('  %-26s %12s %12s %9s' % (name, fmt % g if g is not None else '-', fmt % t if t is not None else '-', ('%+.2f' % (t - g)) if g is not None and t is not None else '-'))
    row('four-family score (%)', pct(*G['four']) if G else None, pct(*T['four']) if T else None, '%.2f')
    print('  %-26s %12s %12s' % ('  (correct/n)', '%d/%d' % G['four'] if G else '-', '%d/%d' % T['four'] if T else '-'))
    row('pooled-5', G['pooled5'] if G else None, T['pooled5'] if T else None, '%.2f')
    row('chain-5 (intact)', G['chain5'] if G else None, T['chain5'] if T else None, '%.1f')
    for s in SPLITS:
        row('  %s' % s, G['splits'].get(s) if G else None, T['splits'].get(s) if T else None, '%.2f')
    print()
    print('The four families, pooled over the 5 splits (the 18 cells of 40 rows that exist for them)')
    print('  %-22s %10s %10s %8s %8s %8s' % ('family', 'G1 c/n', 'T-P c/n', 'G1 %', 'T-P %', 'diff'))
    for f in FOUR:
        g, t = (G['fam'][f] if G else (0, 0)), (T['fam'][f] if T else (0, 0))
        print('  %-22s %10s %10s %8.1f %8.1f %+8.1f' % (f, '%d/%d' % g, '%d/%d' % t, pct(*g), pct(*t), pct(*t) - pct(*g)))
    print()
    ev = events(os.path.join(tpd, 'stdout.txt')) if tpd else []
    print('Training events of the T-P run (every 1000 steps, and the last): sp_cand = candidate rows / rows, sp_hit = hits / candidates, sp_len = mean program length of the hits')
    if ev:
        keys = ['loss', 'prog', 'op_acc', 'mode', 'ans', 'gen', 'sp_cand', 'sp_hit', 'sp_len']
        print('  %6s ' % 'step' + ' '.join('%8s' % k for k in keys))
        for e in ev:
            if e['step'] % 1000 == 0 or e is ev[-1]:
                print('  %6d ' % e['step'] + ' '.join('%8s' % ('%.4f' % e[k] if k in e else '-') for k in keys))
        sp = [e for e in ev if 'sp_hit' in e]
        if sp:
            print('  sp_hit first %.3f, max %.3f, last %.3f; sp_cand mean %.4f; sp_len last %.2f' % (sp[0]['sp_hit'], max(e['sp_hit'] for e in sp), sp[-1]['sp_hit'],
                                                                                              sum(e['sp_cand'] for e in sp) / len(sp), sp[-1]['sp_len']))
        else:
            print('  no sp_* values in the log: this run did not have self_prog on')
        bad = [e['step'] for e in ev if not all(isinstance(e.get(k), (int, float)) and abs(e.get(k)) < 1e9 for k in ('loss',))]
        if bad:
            print('  WARNING: non-finite loss at steps %s' % bad[:5])
    else:
        print('  (no train events: B2\\stdout.txt missing or empty)')
    print()
    print('Verdict by the sealed marks (written before any run)')
    if not T or not G:
        print('  VERDICT: NOT READY (no finished T-P result)')
        return 2
    four, pooled, chain = pct(*T['four']), T['pooled5'], T['chain5']
    if T['status'] != 'ok':
        print('  note: the run status is %r, not ok; report it before reading the marks' % T['status'])
    c1, c2, c3 = four >= PASS_FOUR, pooled >= PASS_POOLED, chain is not None and chain >= PASS_CHAIN
    print('  four families >= %.1f%% : %s (%.2f%%)' % (PASS_FOUR, 'yes' if c1 else 'NO', four))
    print('  pooled-5      >= %.1f   : %s (%.2f)' % (PASS_POOLED, 'yes' if c2 else 'NO', pooled))
    print('  chain-5       >= %.0f     : %s (%s)' % (PASS_CHAIN, 'yes' if c3 else 'NO', chain))
    print('  four families <= %.1f%% (proved wrong): %s' % (WRONG_FOUR, 'YES' if four <= WRONG_FOUR else 'no'))
    if c1 and c2 and c3:
        v = 'PASS (all three marks met). Size follow-up allowed: the same change at 10M s400, scaling mark = own gain >= +3.3.'
    elif four <= WRONG_FOUR:
        v = 'PROVED WRONG (four families <= %.1f%%): self-found programs do not lift the four families.' % WRONG_FOUR
    else:
        why = [n for n, c in (('four families', c1), ('pooled-5', c2), ('chain-5', c3)) if not c]
        v = 'BETWEEN (not met: %s; not proved wrong): run s401.' % ', '.join(why)
    print('  VERDICT: ' + v)
    return 0


if __name__ == '__main__':
    sys.exit(main())
