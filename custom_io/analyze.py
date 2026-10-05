"""Pass-mark analysis (PASS-MARKS.md, computed exactly as written).
python3 -m custom_io.analyze --stage screen|confirm --results DIR [DIR...] --out FILE.json [--seeds 100,101]
Reads every RESULT.json under the dirs; run folders are <arm>_s<seed> (A_s100, A0_s100, B_s100, tf_s100, tfsteps_s100,
l2x2_s100, pythia31m_s200, pythia31m_fewshot_s200, smollm135_fewshot_s200 ...). Only status 'ok' runs count. Anything
missing -> 'n/a' (never a crash). Mark value True/False/'n/a'."""
import argparse, json, math, os, re
from custom_io.evalx import CHAIN5, ONE_STEP

POOL = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
BASE, STEPS = 'tf', 'tfsteps'
SEEDS = {'screen': [100, 101], 'confirm': [200, 201, 202, 203, 204, 205]}
# wiring check "number and string families": answer-type of the dev in_dist families (fraction numeric 1.0 / <= 0.5)
NUMBER_FAMS = ['arith_bare', 'backward_solve', 'chain_ops', 'chain_story2', 'compare_numbers', 'distance_units', 'div_exact',
               'fewshot_number_rule', 'list_stats', 'odd_one_out', 'percent_rate', 'seq_next', 'state_update', 'story_addsub',
               'table_calc', 'var_chain', 'word_filter']
STRING_FAMS = ['cipher_map', 'copy_word', 'group_induct', 'kin_chain', 'object_track', 'order_chain', 'prop_eval', 'seq_cycle',
               'syllogism', 'verify_claim']
T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110,
        2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def tq(df):
    return T975[df - 1] if 1 <= df <= 30 else 1.96


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def sub(a, b):
    return None if a is None or b is None else a - b


def chk(v, op, thr):
    if v is None:
        return 'n/a'
    return {'>=': v >= thr, '<=': v <= thr, '<': v < thr, '>': v > thr}[op]


def allof(xs):
    xs = list(xs)
    return False if False in xs else 'n/a' if not xs or 'n/a' in xs else True


def stats(ds):
    """ds: {seed: d} (None dropped) -> n, mean, sd, 95% CI = mean +- t(.975, n-1) sd / sqrt(n), seeds positive."""
    v = [x for x in ds.values() if x is not None]
    if not v:
        return {'n': 0, 'mean': None, 'sd': None, 'ci': None, 'pos': 0, 'per_seed': {}}
    n, m = len(v), sum(v) / len(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1)) if n > 1 else None
    h = tq(n - 1) * sd / math.sqrt(n) if sd is not None else None
    return {'n': n, 'mean': m, 'sd': sd, 'ci': None if h is None else [m - h, m + h], 'pos': sum(x > 0 for x in v),
            'per_seed': {s: x for s, x in ds.items() if x is not None}}


def binom_two_sided(b, c):
    """Exact McNemar p = two-sided binomial(b+c, 1/2) on the discordant counts."""
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n)


# ---- metrics of one RESULT.json -------------------------------------------------------------------------------------
def _fe(r, les=None):
    return g(r, 'final_eval') if les is None else g(r, 'lesions', les)


def P5(r, les=None):
    fe = _fe(r, les)
    try:
        c, n = sum(fe[s]['correct'] for s in POOL), sum(fe[s]['n'] for s in POOL)
        return 100 * c / n
    except (TypeError, KeyError, ZeroDivisionError):
        return None


def SPL(split):
    return lambda r, les=None: g(_fe(r, les), split, 'exact')


def C5(r, les=None):
    return g(r, 'chain5', les or 'intact', 'exact')


def ONE(r, les=None):
    bf = g(_fe(r, les), 'in_dist', 'by_family')
    try:
        return 100 * sum(bf[f]['correct'] for f in ONE_STEP) / sum(bf[f]['n'] for f in ONE_STEP)
    except (TypeError, KeyError, ZeroDivisionError):
        return None


def donor_group(r, fams):
    bf = g(r, 'lesions', 'donor', 'in_dist', 'by_family')
    try:
        fs = [f for f in fams if f in bf]
        return sum(bf[f]['donor_match'] * bf[f]['n'] for f in fs) / sum(bf[f]['n'] for f in fs)
    except (TypeError, ZeroDivisionError):
        return None


def xget(r, name, *keys):
    """extra evals: extra[name][key] (percent), or a flat 'name_key' / 'key'."""
    e = g(r, 'extra') or {}
    for k in keys:
        for v in (g(e, name, k), e.get(f'{name}_{k}'), e.get(k)):
            if isinstance(v, (int, float)):
                return v
    return None


def loops_key(r):
    n = g(r, 'config', 'cfg', 'n_loops')
    ks = sorted(int(k.split(':')[1]) for k in (r.get('lesions') or {}) if k.startswith('loops:') and k.split(':')[1].isdigit())
    return f'loops:{2 * n}' if n and f'loops:{2 * n}' in (r.get('lesions') or {}) else (f'loops:{ks[-1]}' if ks and ks[-1] > 2 else None)


def wiring(r):
    """-> {check: True/False/'n/a'} for one run (checks whose lesion the model does not have are 'n/a')."""
    ind, ls = SPL('in_dist'), r.get('lesions') or {}
    w = {'shuffle_state<=10': chk(ind(r, 'shuffle_state'), '<=', 10) if 'shuffle_state' in ls else 'n/a',
         'zero_state<=5': chk(ind(r, 'zero_state'), '<=', 5) if 'zero_state' in ls else 'n/a',
         'loops:0<=5': chk(ind(r, 'loops:0'), '<=', 5) if 'loops:0' in ls else 'n/a'}
    k = loops_key(r)
    w['loops:2n within 3'] = chk(abs(ind(r, k) - ind(r)), '<=', 3) if k and None not in (ind(r, k), ind(r)) else 'n/a'
    d = sub(ind(r), g(r, 'lesions', 'donor', 'in_dist', 'exact'))
    w['donor drop>=20'] = chk(d, '>=', 20)
    for nm, fams in (('number', NUMBER_FAMS), ('string', STRING_FAMS)):
        w[f'donor_match {nm}>=50'] = chk(donor_group(r, fams), '>=', 50)
    return w


# ---- loading --------------------------------------------------------------------------------------------------------
def load(dirs):
    runs, skipped = {}, []
    for d in dirs:
        for root, _, fs in os.walk(d):
            if 'RESULT.json' not in fs:
                continue
            m = re.match(r'^(.+)_s(\d+)$', os.path.basename(root))
            try:
                r = json.load(open(os.path.join(root, 'RESULT.json')))
            except Exception as e:
                skipped.append((root, f'unreadable: {e}')); continue
            if not m:
                skipped.append((root, 'name is not <arm>_s<seed>')); continue
            if r.get('status') != 'ok':
                skipped.append((root, f"status {r.get('status')}")); continue
            runs[(m.group(1), int(m.group(2)))] = r
    return runs, skipped


def paired(runs, arm, seeds, fa, base=BASE, fb=None, la=None, lb=None):
    """per-seed d = fa(arm run, la) - fb(base run, lb) -> {seed: d or None}"""
    fb = fb or fa
    return {s: sub(fa(runs[(arm, s)], la), fb(runs[(base, s)], lb)) if (arm, s) in runs and (base, s) in runs else None for s in seeds}


def mcnemar(runs, arm, base, seeds):
    b = c = 0
    per = {}
    for s in seeds:
        ha, hb = g(runs.get((arm, s)), 'chain5', 'intact', 'hits'), g(runs.get((base, s)), 'chain5', 'intact', 'hits')
        if not ha or not hb:
            continue
        ids = ha.keys() & hb.keys()
        sb, sc = sum(ha[i] and not hb[i] for i in ids), sum(hb[i] and not ha[i] for i in ids)
        per[s] = binom_two_sided(sb, sc); b += sb; c += sc
    return {'b_design_only': b, 'c_base_only': c, 'p': binom_two_sided(b, c) if per else 'not computed', 'per_seed_p': per,
            'note': 'discordant counts pooled over seeds' if per else 'not computed (no per-row hits in RESULT.json chain5)'}


def mark(i, desc, value, op=None, thr=None, ok=None, **kw):
    return {'id': i, 'desc': desc, 'value': value, 'op': op, 'thr': thr, 'ok': chk(value, op, thr) if ok is None else ok, **kw}


def per_seed_mark(i, desc, runs, arm, seeds, fn, op, thr):
    vals = {s: fn(runs[(arm, s)]) if (arm, s) in runs else None for s in seeds}
    oks = {s: chk(v, op, thr) for s, v in vals.items()}
    return mark(i, desc, vals, op, thr, ok=allof(oks.values()), per_seed_ok=oks)


def diff_marks(runs, arm, seeds, stage):
    """The pooled-5 / chain-5 / in_dist / variant paired differences vs plain_tf and plain_tf_steps (+ C1')."""
    D = {}
    for nm, fn in (('pooled5', P5), ('chain5', C5), ('in_dist', SPL('in_dist')), ('variant', SPL('variant'))):
        D[f'{nm}_vs_tf'] = stats(paired(runs, arm, seeds, fn))
    D['pooled5_vs_tfsteps'] = stats(paired(runs, arm, seeds, P5, STEPS))
    D['chain5_vs_tfsteps'] = stats(paired(runs, arm, seeds, C5, STEPS))
    if arm.startswith('B'):
        D['pooled5_vs_C1'] = stats(paired(runs, arm, seeds, P5, STEPS, lb='calc'))
        D['chain5_vs_C1'] = stats(paired(runs, arm, seeds, C5, STEPS, lb='calc'))
    return D


def evidence(runs, arm, seeds):
    """Real-evidence lesion marks for A / A0 / B (every seed)."""
    M, ps = [], lambda i, d, fn, op, thr: per_seed_mark(i, d, runs, arm, seeds, fn, op, thr)
    if arm == 'A':
        M += [ps('A.cf', 'interchange cf_match >= 40', lambda r: xget(r, 'interchange', 'cf_match'), '>=', 40),
              ps('A.own', 'interchange own_match <= 30', lambda r: xget(r, 'interchange', 'own_match'), '<=', 30),
              ps('A.blind', 'blind1 chain-5 <= 10', lambda r: C5(r, 'blind1'), '<=', 10),
              mark('A.A-A0', 'A - A0 chain-5 >= +8 (seed mean; every seed needed)', stats(paired(runs, 'A', seeds, C5, 'A0'))['mean'], '>=', 8,
                   ok=allof([chk(stats(paired(runs, 'A', seeds, C5, 'A0'))['mean'], '>=', 8),
                             'n/a' if stats(paired(runs, 'A', seeds, C5, 'A0'))['n'] < len(seeds) else True]))]
    if arm == 'A0':
        M += [ps('A0.loops1', 'loops:1 chain-5 <= 15', lambda r: C5(r, 'loops:1'), '<=', 15),
              ps('A0.onestep', 'loops:1 one-step families within 5 of intact',
                 lambda r: None if None in (ONE(r), ONE(r, 'loops:1')) else abs(ONE(r) - ONE(r, 'loops:1')), '<=', 5)]
    if arm == 'B':
        M += [ps('B.loops1', 'loops:1 chain-5 <= 5', lambda r: C5(r, 'loops:1'), '<=', 5),
              ps('B.loops2', 'loops:2 cuts chain-5 by >= 40', lambda r: sub(C5(r), C5(r, 'loops:2')), '>=', 40),
              ps('B.onestep', 'loops:2 one-op families within 5 of intact',
                 lambda r: None if None in (ONE(r), ONE(r, 'loops:2')) else abs(ONE(r) - ONE(r, 'loops:2')), '<=', 5),
              ps('B.noexec', 'noexec program families <= 10 (extra.noexec.program_families, else chain-5 noexec)',
                 lambda r: xget(r, 'noexec', 'program_families') if xget(r, 'noexec', 'program_families') is not None else C5(r, 'noexec'), '<=', 10),
              ps('B.opswap', 'opswap >= 90% outputs equal swapped program value',
                 lambda r: xget(r, 'opswap', 'swap_match', 'match'), '>=', 90)]
    return M


def wrong_marks(runs, arm, seeds, D):
    """Results that prove a design wrong (computed on the seed means)."""
    W = []
    c5, ind = D['chain5_vs_tf']['mean'], D['in_dist_vs_tf']['mean']
    if arm in ('A', 'A0'):
        a0 = stats(paired(runs, 'A', seeds, C5, 'A0'))['mean'] if arm == 'A' else None
        a0tf = stats(paired(runs, 'A0', seeds, C5))['mean']
        cf = [xget(runs[(arm, s)], 'interchange', 'cf_match') for s in seeds if (arm, s) in runs]
        cf = sum(cf) / len(cf) if cf and None not in cf else None
        if arm == 'A':
            W += [mark('wrongA.chain5', 'chain-5 d < +3', c5, '<', 3), mark('wrongA.A-A0', 'A - A0 chain-5 < +3', a0, '<', 3),
                  mark('wrongA.cf', 'cf_match < 15', cf, '<', 15), mark('wrongA.in_dist', 'in_dist d < -4', ind, '<', -4),
                  mark('wrongA.answer-only', 'A - A0 < 3 and A0 - plain_tf < 3 (answer-only recursion ruled out)', a0, ok=allof([chk(a0, '<', 3), chk(a0tf, '<', 3)]))]
    if arm == 'B':
        p5, c1p, c1c = D['pooled5_vs_tf']['mean'], D['pooled5_vs_C1']['mean'], D['chain5_vs_C1']['mean']
        W += [mark('wrongB.chain5', 'chain-5 d < +10', c5, '<', 10), mark('wrongB.pooled5', 'pooled-5 d <= 0', p5, '<=', 0),
              mark('wrongB.C1', "C1' within 3 points of B on both chain-5 and pooled-5", [c1c, c1p], ok=allof([chk(c1c, '<=', 3), chk(c1p, '<=', 3)]))]
    return W


def design_arms(runs):
    return sorted({a for a, _ in runs if a not in (BASE, STEPS) and not re.match(r'(pythia|smollm)', a)})


def screen(runs, seeds):
    out = {}
    for arm in design_arms(runs):
        D = diff_marks(runs, arm, seeds, 'screen')
        d_tf5, d_c5, d_in, d_st = (D[k] for k in ('pooled5_vs_tf', 'chain5_vs_tf', 'in_dist_vs_tf', 'pooled5_vs_tfsteps'))
        wire = {s: wiring(runs[(arm, s)]) if (arm, s) in runs else {} for s in seeds}
        w_ok = allof(allof(w.values()) if w else 'n/a' for w in wire.values())
        G = [mark('G1', 'pooled-5 d vs plain_tf >= +1.0', d_tf5['mean'], '>=', 1.0),
             mark('G2', 'chain-5 d vs plain_tf >= +8, all seeds positive', d_c5['mean'], '>=', 8.0,
                  ok=allof([chk(d_c5['mean'], '>=', 8.0), 'n/a' if d_c5['n'] < len(seeds) else d_c5['pos'] == d_c5['n']])),
             mark('G3', 'in_dist d vs plain_tf >= -2.0', d_in['mean'], '>=', -2.0),
             mark('G4', 'pooled-5 d vs plain_tf_steps >= -1.0', d_st['mean'], '>=', -1.0)]
        if arm.startswith('B'):
            G[3]['ok'] = allof([G[3]['ok'], chk(D['pooled5_vs_C1']['mean'], '>=', -1.0)])
            G[3]['desc'] += " and vs C1' (tfsteps calc) >= -1.0"
            G[3]['value'] = [d_st['mean'], D['pooled5_vs_C1']['mean']]
        G.append(mark('G5', 'wiring lesions hold in every seed', {s: w for s, w in wire.items()}, ok=w_ok))
        go = allof(m['ok'] for m in G)
        complete = all((arm, s) in runs and (BASE, s) in runs and (STEPS, s) in runs for s in seeds)
        out[arm] = {'diffs': D, 'G': G, 'verdict': 'incomplete (missing seeds)' if not complete else {True: 'GO', False: 'NO-GO', 'n/a': 'incomplete (n/a marks)'}[go],
                    'complete': complete,
                    'evidence': evidence(runs, arm, seeds), 'prove_wrong': wrong_marks(runs, arm, seeds, D)}
        if arm == 'A':
            out[arm]['A_minus_A0_chain5'] = stats(paired(runs, 'A', seeds, C5, 'A0'))
    return out


def confirm(runs, seeds):
    out = {}
    for arm in design_arms(runs):
        D = diff_marks(runs, arm, seeds, 'confirm')
        p5, c5, ind, var = (D[k] for k in ('pooled5_vs_tf', 'chain5_vs_tf', 'in_dist_vs_tf', 'variant_vs_tf'))
        st = D['pooled5_vs_tfsteps']
        mc = mcnemar(runs, arm, BASE, seeds)
        lo = lambda s: None if not s['ci'] else s['ci'][0]
        need = 5 if len(seeds) >= 6 else len(seeds)
        P1 = [mark('P1.pooled', 'pooled-5 d >= +2.0, CI lo > 0, >= 5 of 6 seeds positive', p5['mean'], '>=', 2.0,
                   ok=allof([chk(p5['mean'], '>=', 2.0), chk(lo(p5), '>', 0), chk(p5['pos'] if p5['n'] else None, '>=', need)])),
              mark('P1.chain5', 'chain-5 d >= +8, CI lo > 0, McNemar p < 0.01', c5['mean'], '>=', 8.0,
                   ok=allof([chk(c5['mean'], '>=', 8.0), chk(lo(c5), '>', 0), chk(mc['p'] if mc['p'] != 'not computed' else None, '<', 0.01)]),
                   mcnemar=mc),
              mark('P1.in_dist', 'in_dist d >= -1.0', ind['mean'], '>=', -1.0)]
        p1 = allof(m['ok'] for m in P1)
        ft = {a: [s for s in seeds if (a, s) in runs] for a in {a for a, _ in runs if a.startswith('pythia31m') and 'shot' not in a and 'fs' not in a}}
        fs = sorted({a for a, _ in runs if re.search(r'shot|fs', a) and (a.startswith('pythia31m') or a.startswith('smollm'))})
        P2 = [mark('P2.steps', 'pooled-5 d vs plain_tf_steps >= +1.0, CI lo > 0', st['mean'], '>=', 1.0,
                   ok=allof([chk(st['mean'], '>=', 1.0), chk(lo(st), '>', 0)]))]
        pyt = {a: stats({s: sub(P5(runs[(arm, s)]), P5(runs[(a, s)])) if (arm, s) in runs and (a, s) in runs else None for s in seeds}) for a in ft}
        P2.append(mark('P2.pythia_ft', 'pooled-5 >= 2 above fine-tuned pythia-31m (paired, seeds present)',
                       {a: s['mean'] for a, s in pyt.items()} or None, ok=allof(chk(s['mean'], '>=', 2.0) for s in pyt.values())))
        mine = [P5(runs[(arm, s)]) for s in seeds if (arm, s) in runs]
        mine = sum(mine) / len(mine) if mine else None
        for a in fs:
            v = [P5(r) for (x, _), r in runs.items() if x == a and P5(r) is not None]
            v = sum(v) / len(v) if v else None
            P2.append(mark(f'P2.{a}', f'pooled-5 above {a} (no fine-tuning)', sub(mine, v), '>', 0))
        for pre in ('smollm', 'pythia31m'):
            if not any(a.startswith(pre) for a in fs):
                P2.append(mark(f'P2.{pre}_fewshot', f'above 8-shot {pre} (no fine-tuning): run missing', None, ok='n/a'))
        p2 = allof([p1] + [m['ok'] for m in P2])
        sec = mark('Secondary', 'variant d vs plain_tf >= +2.0, CI lo > 0', var['mean'], '>=', 2.0, ok=allof([chk(var['mean'], '>=', 2.0), chk(lo(var), '>', 0)]))
        fl = [chk(p5['mean'], '<', 1.0), chk(ind['mean'], '<', -2.0)]
        fail = True if True in fl else 'n/a' if 'n/a' in fl else False
        complete = all((arm, s) in runs and (BASE, s) in runs and (STEPS, s) in runs for s in seeds)
        verdict = ('incomplete (missing seeds)' if not complete else 'FAIL' if fail is True else 'PASS-2' if p2 is True else
                   'PASS-1' if p1 is True else 'n/a (missing inputs)' if p1 == 'n/a' or fail == 'n/a' else 'INCONCLUSIVE')
        if verdict == 'PASS-1' and p2 == 'n/a':
            verdict = 'PASS-1 (PASS-2 pending: n/a marks)'
        out[arm] = {'diffs': D, 'PASS1': P1, 'PASS2': P2, 'secondary': sec, 'FAIL': fail, 'verdict': verdict, 'complete': complete,
                    'evidence': evidence(runs, arm, seeds), 'prove_wrong': wrong_marks(runs, arm, seeds, D),
                    'wiring': {s: wiring(runs[(arm, s)]) for s in seeds if (arm, s) in runs}}
    return out


# ---- output ---------------------------------------------------------------------------------------------------------
def f(v):
    return 'n/a' if v is None else f'{v:.2f}' if isinstance(v, float) else str(v)


def show(res, stage):
    for arm, a in res.items():
        print(f"\n=== {arm}: {a['verdict']}{'' if a['complete'] else '  (not every seed has plain_tf and plain_tf_steps)'}")
        print('  paired differences (design - baseline, same seed): mean [95% CI] pos/n')
        for k, s in a['diffs'].items():
            print(f"    {k:22s} {f(s['mean']):>8} {'' if not s['ci'] else '[%.2f, %.2f]' % tuple(s['ci'])} {s['pos']}/{s['n']}")
        for grp in ('G', 'PASS1', 'PASS2', 'evidence', 'prove_wrong'):
            for m in a.get(grp, []):
                v = m['value']
                v = {k: (f(x) if not isinstance(x, dict) else 'dict') for k, x in v.items()} if isinstance(v, dict) else f(v) if not isinstance(v, list) else [f(x) for x in v]
                print(f"  [{ {True: 'ok', False: 'NO', 'n/a': 'n/a'}[m['ok']]:>3}] {m['id']:12s} {m['desc']}  -> {v}")
        if stage == 'confirm':
            print(f"  [ {a['secondary']['ok']}] secondary: {a['secondary']['desc']} -> {f(a['secondary']['value'])};  FAIL rule: {a['FAIL']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, choices=['screen', 'confirm'])
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seeds', help='comma list (default: 100,101 screen; 200-205 confirm)')
    a = ap.parse_args(argv)
    seeds = [int(x) for x in a.seeds.split(',')] if a.seeds else SEEDS[a.stage]
    runs, skipped = load(a.results)
    res = (screen if a.stage == 'screen' else confirm)(runs, seeds)
    show(res, a.stage)
    for p, why in skipped:
        print(f'skipped {p}: {why}')
    out = {'stage': a.stage, 'seeds': seeds, 'runs': sorted(f'{x}_s{s}' for x, s in runs), 'skipped': skipped, 'arms': res}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    return out


if __name__ == '__main__':
    main()
