"""Gain tests beside the no-hard-coding ladder (PASS-MARKS.md addenda 18 and 19), judged exactly as written, 2-seed screens (200, 201).
python3 -m custom_io.analyze_gain --results custom_io/results/33-pc-confirm-b2 custom_io/results/41-pc-gain-u0 custom_io/results/42-pc-gain-w1 [--out custom_io/results/GAIN-ANALYSIS.json]
U0 (INPUT-UNITS-2026-10-07.md): plain_tf_steps with the prompt in byte-level BPE (cfg bpe 308, 416 ids) minus q33's plain_tf_steps, same seed.
  "Ben right": pooled-5 >= +2.0 on both seeds; "letters fine": <= +1.0 on both; else tie. The pre-registered prediction (letters fine,
  cipher_map falls by 10 or more, arithmetic falls, frame and vocab move less than 2) is proved wrong if cipher_map pooled over its 3 splits
  (120 rows, 2-seed mean) is at or above letters - 5 rows for word pieces.
W1 (redesign-ideas-2026-10-07.md sec. 8, family line re-sealed in sec. 8a): B2 with one low-rank global attention block in the reader
  (cfg gattn 32) minus q33's B2, same seed. Pass: pooled-5 >= +1.0 on both seeds; cipher_map in_dist >= 95 (2-seed mean); F1: cipher_map,
  fewshot_number_rule, group_induct and seq_cycle pooled as one in_dist number, 2-seed mean not down > 2.0; no dev split down > 2.0 (2-seed mean);
  chain-5 >= 99.0 on both; loops:0 in_dist <= B2's + 1.0 and donor in_dist <= 5 on both. Proved wrong: pooled-5 mean < 0, or cipher_map
  in_dist (2-seed mean) down > 2.0.
  F2: F1's failure rate with no change (two plain q33 B2 runs of different seeds, 2-seed means, all 360 ordered choices of 4 of the 6 seeds) is
  printed with every verdict; above 25% F1 is reported, not judged (then only the cipher_map >= 95 line and the split mark apply).
  F3: every other family (rows pooled over the five pooled splits) is reported beside its null spread, never judged.
A run counts only with status ok, the q33 recipe and the right size; a missing or invalid run: NOT JUDGED."""
import argparse, itertools, json, os
from custom_io.analyze import C5, P5, POOL, SPL, g, load, sub

SEEDS = [200, 201]
RECIPE = dict(steps=24000, batch=256, lr=1e-3, bf16=True)
ARMS = {'U0': ('plain_tf_steps', {'bpe': 308}, 3339776), 'tfsteps': ('plain_tf_steps', {}, 3260928),
        'W1': ('ledger', {'copy': True, 'gattn': 32}, 3336113), 'B2': ('ledger', {'copy': True}, 3302481)}
CIPHER3 = ['in_dist', 'answer', 'frame']
F1 = ['cipher_map', 'fewshot_number_rule', 'group_induct', 'seq_cycle']     # sec. 8a: the four lookup-style families, pooled on in_dist
ARITH = ['arith_bare', 'div_exact', 'story_addsub', 'distance_units', 'chain_ops', 'chain_story2', 'story_chain3', 'var_chain', 'state_update', 'percent_rate']


def valid(r, arm):
    model, cfg, n = ARMS[arm]
    c = g(r, 'config') or {}
    bad = [f'{k}={c.get(k)!r} (want {v!r})' for k, v in RECIPE.items() if c.get(k) != v]
    if r.get('status') != 'ok':
        bad.append(f"status {r.get('status')}")
    if c.get('model') != model or (c.get('cfg') or {}) != cfg:
        bad.append(f"model {c.get('model')} cfg {c.get('cfg')} (want {model} {cfg})")
    if r.get('steps') != RECIPE['steps']:
        bad.append(f"trained {r.get('steps')} steps")
    if r.get('n_params') != n:
        bad.append(f"n_params {r.get('n_params')} (want {n})")
    return bad


def pairs_for(runs, x, y):
    probs, pairs = {}, {}
    for s in SEEDS:
        a, b = runs.get((x, s)), runs.get((y, s))
        p = ([f'{x} missing'] if a is None else [f'{x}: {e}' for e in valid(a, x)]) + ([f'{y} missing'] if b is None else [f'{y}: {e}' for e in valid(b, y)])
        probs[s] = p
        if not p:
            pairs[s] = (a, b)
    return probs, pairs


def fam_rows(r, f, splits=POOL):
    c = n = 0
    for sp in splits:
        x = g(r, 'final_eval', sp, 'by_family', f)
        if x:
            c, n = c + x['correct'], n + x['n']
    return c, n


def fam_pct(r, f, splits=POOL):
    c, n = fam_rows(r, f, splits)
    return 100 * c / n if n else None


def f1(r):
    c, n = 0, 0
    for f in F1:
        x = g(r, 'final_eval', 'in_dist', 'by_family', f)
        if x:
            c, n = c + x['correct'], n + x['n']
    return 100 * c / n if n else None


def families(r):
    return sorted(g(r, 'final_eval', 'in_dist', 'by_family') or {})


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def u0(runs):
    probs, pairs = pairs_for(runs, 'U0', 'tfsteps')
    out = dict(test='U0 word pieces (BPE prompt) minus letters, plain_tf_steps', problems=probs, judged=len(pairs) == len(SEEDS))
    if not out['judged']:
        out['verdict'] = 'NOT JUDGED'
        return out
    d = {s: sub(P5(a), P5(b)) for s, (a, b) in pairs.items()}
    cm = {s: dict(U0=fam_rows(a, 'cipher_map', CIPHER3)[0], letters=fam_rows(b, 'cipher_map', CIPHER3)[0]) for s, (a, b) in pairs.items()}
    cm_u, cm_l = mean(v['U0'] for v in cm.values()), mean(v['letters'] for v in cm.values())
    dsplit = {sp: mean(sub(SPL(sp)(a), SPL(sp)(b)) for a, b in pairs.values()) for sp in POOL + ['family']}
    arith = {f: mean(sub(fam_pct(a, f), fam_pct(b, f)) for a, b in pairs.values()) for f in ARITH}
    out.update(d_pooled5=d, cipher_map_rows_of_120=cm, d_split_2seed=dsplit, d_arith_family_2seed=arith,
               calc_on=dict(d_pooled5={s: sub(P5(a, 'calc'), P5(b, 'calc')) for s, (a, b) in pairs.items()},
                            chain5={s: dict(U0=C5(a, 'calc'), letters=C5(b, 'calc')) for s, (a, b) in pairs.items()}),
               chain5={s: dict(U0=C5(a), letters=C5(b)) for s, (a, b) in pairs.items()})
    out['verdict'] = ('Ben right: word pieces help (add a from-scratch word-piece side channel next to the letters in B2 as the next gain test)'
                      if all(v >= 2.0 for v in d.values()) else 'Letters fine: no evidence word pieces help at this size'
                      if all(v <= 1.0 for v in d.values()) else 'Tie: letters stay, no evidence word pieces help at this size')
    out['prediction'] = dict(cipher_map_2seed_rows=dict(U0=cm_u, letters=cm_l, drop=cm_l - cm_u),
                             proved_wrong=cm_u >= cm_l - 5, frame_vocab_move=dict(frame=dsplit['frame'], vocab=dsplit['vocab']))
    return out


def w1(runs, null):
    probs, pairs = pairs_for(runs, 'W1', 'B2')
    out = dict(test='W1 global attention in the reader minus B2', problems=probs, judged=len(pairs) == len(SEEDS))
    if not out['judged']:
        out['verdict'] = 'NOT JUDGED'
        return out
    d = {s: sub(P5(a), P5(b)) for s, (a, b) in pairs.items()}
    cm_in = {s: fam_pct(a, 'cipher_map', ['in_dist']) for s, (a, _) in pairs.items()}
    cm_d = mean(sub(fam_pct(a, 'cipher_map', ['in_dist']), fam_pct(b, 'cipher_map', ['in_dist'])) for a, b in pairs.values())
    fams = [f for f in families(next(iter(pairs.values()))[0]) if f not in F1]
    dfam = {f: mean(sub(fam_pct(a, f), fam_pct(b, f)) for a, b in pairs.values()) for f in fams}
    df1 = {s: sub(f1(a), f1(b)) for s, (a, b) in pairs.items()}
    dspl = {sp: mean(sub(SPL(sp)(a), SPL(sp)(b)) for a, b in pairs.values()) for sp in POOL}
    lk = {s: dict(loops0=SPL('in_dist')(a, 'loops:0'), b2_loops0=SPL('in_dist')(b, 'loops:0'), donor=g(a, 'lesions', 'donor', 'in_dist', 'exact'))
          for s, (a, b) in pairs.items()}
    c5 = {s: C5(a) for s, (a, _) in pairs.items()}
    f1_rate = g(null, 'false_fail_rate', 'F1')
    f1_usable = f1_rate is not None and f1_rate <= 0.25
    m = {'pooled-5 W1 - B2 >= +1.0 on both seeds': dict(value=d, ok=all(v >= 1.0 for v in d.values())),
         'cipher_map in_dist >= 95 (2-seed mean)': dict(value=dict(per_seed=cm_in, mean=mean(cm_in.values())), ok=mean(cm_in.values()) >= 95),
         'F1 four lookup families pooled on in_dist, 2-seed mean W1 - B2 not down > 2.0': dict(
             value=dict(per_seed=df1, mean=mean(df1.values()), null_fail_rate=f1_rate, judged=f1_usable), ok=mean(df1.values()) >= -2.0),
         'no dev split down > 2.0 (2-seed mean)': dict(value=dspl, ok=all(v >= -2.0 for v in dspl.values())),
         'chain-5 >= 99.0 on both seeds': dict(value=c5, ok=all(v is not None and v >= 99.0 for v in c5.values())),
         "loops:0 in_dist <= B2's + 1.0 and donor in_dist <= 5 on both seeds": dict(value=lk, ok=all(
             v['loops0'] is not None and v['b2_loops0'] is not None and v['loops0'] <= v['b2_loops0'] + 1.0 and (v['donor'] if v['donor'] is not None else 99) <= 5
             for v in lk.values()))}
    fam_null = g(null, 'family_null') or {}
    f3 = {f: dict(change=v, null=fam_null.get(f)) for f, v in sorted(dfam.items(), key=lambda kv: kv[1])}
    out.update(marks=m, f2=dict(f1_null_fail_rate=f1_rate, f1_judged=f1_usable), f3_other_families=f3)
    wrong = mean(d.values()) < 0 or cm_d < -2.0
    out['proved_wrong'] = dict(value=dict(pooled5_mean=mean(d.values()), cipher_map_in_dist_2seed_change=cm_d), wrong=wrong)
    judged = [x['ok'] for k, x in m.items() if f1_usable or not k.startswith('F1')]
    out['verdict'] = 'PASS: run the 6-seed confirm' if all(judged) else 'PROVED WRONG' if wrong else 'NOT SHOWN'
    return out


def null_check(runs, arm='B2', seeds=range(200, 206)):
    """How often each W1 mark fails with no change at all: two plain B2 runs of different seeds standing in for W1 and B2, averaged over two
    such pairs (every ordered choice of 4 of the 6 q33 seeds). Also each other family's null spread (rows pooled over the five pooled splits)."""
    R = {s: runs[(arm, s)] for s in seeds if (arm, s) in runs and not valid(runs[(arm, s)], arm)}
    if len(R) < 4:
        return dict(note='fewer than 4 valid q33 B2 runs')
    fams = [f for f in families(next(iter(R.values()))) if f not in F1]
    tot, fail, spread = 0, dict(F1=0, split=0, cipher_map_down=0, old_family_line=0), {f: [] for f in fams}
    for a, b, c, e in itertools.permutations(sorted(R), 4):
        tot += 1
        m2 = lambda fn: ((fn(R[a]) - fn(R[b])) + (fn(R[c]) - fn(R[e]))) / 2
        fam = {f: m2(lambda r, f=f: fam_pct(r, f)) for f in fams}
        for f, v in fam.items():
            spread[f].append(v)
        fail['F1'] += m2(f1) < -2.0
        fail['split'] += min(m2(SPL(sp)) for sp in POOL) < -2.0
        fail['cipher_map_down'] += m2(lambda r: fam_pct(r, 'cipher_map', ['in_dist'])) < -2.0
        fail['old_family_line'] += min(fam.values()) < -2.0 or m2(lambda r: fam_pct(r, 'cipher_map')) < -2.0
    q = lambda xs, p: sorted(xs)[min(len(xs) - 1, int(p * len(xs)))]
    return dict(n=tot, false_fail_rate={k: round(v / tot, 3) for k, v in fail.items()},
                family_null={f: dict(p05=round(q(v, 0.05), 2), p95=round(q(v, 0.95), 2)) for f, v in spread.items()})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--out', default='custom_io/results/GAIN-ANALYSIS.json')
    a = ap.parse_args(argv)
    runs, skipped = load(a.results)
    null = null_check(runs)
    res = dict(U0=u0(runs), W1=w1(runs, null), w1_null_check=null, skipped=skipped)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1, default=str)
    f = lambda v: f'{v:+.2f}' if isinstance(v, float) else json.dumps(v, default=str) if isinstance(v, (dict, list, tuple)) else str(v)
    L = ['# Gain tests U0 and W1 (PASS-MARKS.md addenda 18 and 19)', '']
    for k in ('U0', 'W1'):
        r = res[k]
        L += [f"## {k}: {r['verdict']}", '', f"{r['test']}.", '']
        if not r['judged']:
            L += [f"- missing or invalid: {f({s: p for s, p in r['problems'].items() if p})}", '']
            continue
        if k == 'U0':
            L += [f"- pooled-5 U0 - letters: {f(r['d_pooled5'])}", f"- cipher_map rows of 120: {f(r['cipher_map_rows_of_120'])}",
                  f"- prediction proved wrong: {r['prediction']['proved_wrong']} ({f(r['prediction']['cipher_map_2seed_rows'])})",
                  f"- split changes (2-seed mean): {f(r['d_split_2seed'])}", f"- arithmetic families (2-seed mean): {f(r['d_arith_family_2seed'])}",
                  f"- calculator on: {f(r['calc_on'])}", '']
        else:
            L += [f"- {m}: {f(x['value'])} -> {x['ok']}" + ('' if r['f2']['f1_judged'] or not m.startswith('F1') else ' (reported, not judged: F2)')
                  for m, x in r['marks'].items()] + [f"- proved wrong: {f(r['proved_wrong'])}",
                  f"- F2: F1 fails {100 * (r['f2']['f1_null_fail_rate'] or 0):.1f}% of the time with no change -> {'judged' if r['f2']['f1_judged'] else 'not judged'}", '',
                  'F3, every other family (rows pooled over the five pooled splits), report only:', '', '| family | W1 - B2 (2-seed mean) | no-change 5th to 95th percentile |', '|---|---|---|']
            L += [f"| {fm} | {f(v['change'])} | {f(g(v, 'null', 'p05'))} to {f(g(v, 'null', 'p95'))} |" for fm, v in r['f3_other_families'].items()] + ['']
    L += [f"W1 null check (no change, q33 B2 vs B2, {g(res, 'w1_null_check', 'n')} draws): failure rates {f(g(res, 'w1_null_check', 'false_fail_rate'))}", '']
    md = os.path.join(os.path.dirname(a.out) or '.', 'RESULTS-GAIN.md')
    open(md, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return res


if __name__ == '__main__':
    main()
