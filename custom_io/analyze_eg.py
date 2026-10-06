"""EmbeddingGemma 2 arms for B2 (PASS-MARKS.md addendum 4) and Test LR, the per-round readout loss (addendum 5), computed exactly as written.
python3 -m custom_io.analyze_eg --results custom_io/results/33-pc-confirm-b2 custom_io/results/36-pc-eg2 [--out custom_io/results/EG2-ANALYSIS.json]
Arms EGE (eg_embed) and EGT (eg_teach 0.1), each paired by seed (200, 201) with plain B2 (run folders B2_s200, B2_s201). A run counts only if it
is status 'ok', trained 24,000 steps with the B2 flags and its own switch, and the base run is plain B2 with the same flags; otherwise its
marks are NOT JUDGED (never a crash). Writes the JSON and RESULTS-EG2.md next to it."""
import argparse, json, os
from custom_io.analyze import P5, SPL, C5, POOL, g, load, sub, chk, allof

SEEDS, BASE = [200, 201], 'B2'
ARMS = {'EGE': {'copy': True, 'eg_embed': True}, 'EGT': {'copy': True, 'eg_teach': 0.1}, 'LR': {'copy': True, 'round_readout': 1.0}}
RECIPE = dict(steps=24000, batch=256, lr=1e-3, bf16=True)
SIZES = {'B2': 3302481, 'EGE': 3500881, 'EGT': 3368785, 'LR': 3302481}


def valid(r, cfg, arm):
    """-> list of problems (empty = valid)."""
    c = g(r, 'config') or {}
    bad = [f'{k}={c.get(k)!r} (want {v!r})' for k, v in RECIPE.items() if c.get(k) != v]
    if (c.get('cfg') or {}) != cfg:
        bad.append(f"cfg {c.get('cfg')} (want {cfg})")
    if r.get('steps') != RECIPE['steps']:
        bad.append(f"trained {r.get('steps')} steps")
    if r.get('n_params') != SIZES[arm]:
        bad.append(f"n_params {r.get('n_params')} (want {SIZES[arm]})")
    return bad


def leak(r):
    return dict(loops0=SPL('in_dist')(r, 'loops:0'), donor=g(r, 'lesions', 'donor', 'in_dist', 'exact'))


def judge(runs, arm):
    """Marks 1-5 for one arm -> dict."""
    probs, pairs = {}, {}
    for s in SEEDS:
        a, b = runs.get((arm, s)), runs.get((BASE, s))
        p = (['missing'] if a is None else valid(a, ARMS[arm], arm)) + (['base missing'] if b is None else [f'base: {x}' for x in valid(b, {'copy': True}, 'B2')])
        if a is not None and b is not None:        # same machine: local_runner passes WORK/data, so the data path names the machine
            for k in ('device', 'data'):
                if g(a, 'config', k) != g(b, 'config', k):
                    p.append(f"arm and base differ in config.{k}: {g(a, 'config', k)!r} vs {g(b, 'config', k)!r}")
        probs[s] = p
        if not p:
            pairs[s] = (a, b)
    out = dict(arm=arm, problems=probs, judged=len(pairs) == len(SEEDS))
    d = lambda fn: {s: sub(fn(a), fn(b)) for s, (a, b) in pairs.items()}
    mean = lambda dd: sum(dd.values()) / len(dd) if dd and len(dd) == len(SEEDS) and None not in dd.values() else None
    dp5, dvar = d(P5), d(SPL('variant'))
    dspl = {sp: d(SPL(sp)) for sp in POOL}
    c5 = {s: C5(a) for s, (a, _) in pairs.items()}
    lk = {s: leak(a) for s, (a, _) in pairs.items()}
    lk_base = {s: leak(b) for s, (_, b) in pairs.items()}
    m = {}
    m['1 pooled-5 gain >= +1.0 on both seeds'] = dict(value=dp5, ok=allof(chk(v, '>=', 1.0) for v in dp5.values()) if len(dp5) == len(SEEDS) else 'n/a')
    m['2 variant gain >= +3.0, 2-seed mean'] = dict(value=mean(dvar), per_seed=dvar, ok=chk(mean(dvar), '>=', 3.0))
    drops = {sp: mean(v) for sp, v in dspl.items()}
    m['3 no dev split drops more than 2.0 (2-seed mean)'] = dict(value=drops, ok=allof(chk(v, '>=', -2.0) for v in drops.values()))
    m['4 chain-5 >= 99.0 on both seeds'] = dict(value=c5, ok=allof(chk(v, '>=', 99.0) for v in c5.values()) if len(c5) == len(SEEDS) else 'n/a')
    full = lambda dd: len(dd) == len(SEEDS)
    if arm != 'LR':
        m['5 loops:0 in_dist <= 5 and donor in_dist <= 5 on both seeds'] = dict(
            value=lk, plain_b2_same_seeds_read_only=lk_base,
            ok=allof([chk(v['loops0'], '<=', 5) for v in lk.values()] + [chk(v['donor'], '<=', 5) for v in lk.values()]) if full(lk) else 'n/a')
    else:       # addendum 5: marks 2, 4 and 5 differ from the EG arms'
        stab = {s: sub(SPL('in_dist')(a, 'loops:16'), SPL('in_dist')(a)) for s, (a, _) in pairs.items()}
        stab_b = {s: sub(SPL('in_dist')(b, 'loops:16'), SPL('in_dist')(b)) for s, (_, b) in pairs.items()}
        m.pop('2 variant gain >= +3.0, 2-seed mean')
        m['2 in_dist at loops:16 minus at 8 >= -0.3 on both seeds'] = dict(value=stab, plain_b2_same_seeds_read_only=stab_b,
                                                                             ok=allof(chk(v, '>=', -0.3) for v in stab.values()) if full(stab) else 'n/a')
        l1 = {s: C5(a, 'loops:1') for s, (a, _) in pairs.items()}
        m['4 chain-5 >= 99.0 and loops:1 chain-5 <= 5 on both seeds'] = dict(value=dict(chain5=c5, loops1_chain5=l1),
            ok=allof([chk(v, '>=', 99.0) for v in c5.values()] + [chk(v, '<=', 5) for v in l1.values()]) if full(c5) else 'n/a')
        m.pop('4 chain-5 >= 99.0 on both seeds')
        m['5 loops:0 in_dist <= plain B2 + 1.0 and donor in_dist <= 5 on both seeds'] = dict(value=lk, plain_b2_same_seeds_read_only=lk_base,
            ok=allof([chk(sub(lk[s]['loops0'], lk_base[s]['loops0']), '<=', 1.0) for s in lk] + [chk(v['donor'], '<=', 5) for v in lk.values()]) if full(lk) else 'n/a')
        m = {k: m[k] for k in sorted(m)}
        out['proved_wrong'] = dict(pooled5_mean_below_0=None if mean(dp5) is None else mean(dp5) < 0,
                                   stability_missed_both=None if not full(stab) else all(v is not None and v < -0.3 for v in stab.values()))
    out['marks'] = m
    oks = [x['ok'] for x in m.values()]
    out['verdict'] = 'NOT JUDGED' if not out['judged'] or 'n/a' in oks else ('PASS' if all(x is True for x in oks) else 'FAIL (stop this arm)')
    out['read_only'] = dict(
        per_split=dspl, family_split=d(SPL('family')),
        abs={s: dict(arm_p5=P5(a), base_p5=P5(b), arm_variant=SPL('variant')(a), base_variant=SPL('variant')(b)) for s, (a, b) in pairs.items()},
        steps_per_s={s: (a.get('steps_per_s'), b.get('steps_per_s')) for s, (a, b) in pairs.items()},
        peak_mem_mib={s: (a.get('peak_mem_mib'), b.get('peak_mem_mib')) for s, (a, b) in pairs.items()},
        size={s: g(a, 'extra', 'size') for s, (a, _) in pairs.items()})
    return out


def fmt(v, signed=True):
    if isinstance(v, float):
        return f'{v:+.2f}' if signed and abs(v) < 50 else f'{v:.2f}'
    if isinstance(v, dict):
        return ', '.join(f'{k}: {fmt(x, signed)}' for k, x in v.items())
    return str(v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--out', default='custom_io/results/EG2-ANALYSIS.json')
    a = ap.parse_args(argv)
    runs, skipped = load(a.results)
    res = dict(seeds=SEEDS, arms={arm: judge(runs, arm) for arm in ARMS}, skipped=skipped)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1, default=str)
    L = ['# EmbeddingGemma 2 arms (PASS-MARKS.md addendum 4) and Test LR (addendum 5) for B2', '', f'Seeds {SEEDS}, each arm minus plain B2 on the same seed.', '']
    for arm, r in res['arms'].items():
        L += [f'## {arm}: {r["verdict"]}', '']
        if any(r['problems'].values()):
            L += [f'- problems: {r["problems"]}']
        for k, x in r['marks'].items():
            gain = k[0] in '123'        # marks 1-3 are signed differences; 4-5 are absolute values
            L += [f'- {k}: {fmt(x["value"], gain)} -> {x["ok"]}']
            if 'plain_b2_same_seeds_read_only' in x:
                L += [f'  - plain B2 on the same seeds (read only): {fmt(x["plain_b2_same_seeds_read_only"], False)}']
        if 'proved_wrong' in r:
            L += [f'- proved wrong (addendum 5): {r["proved_wrong"]}']
        L += [f'- read only: family split change {fmt(r["read_only"]["family_split"])}; size {r["read_only"]["size"]}', '']
    md = os.path.join(os.path.dirname(a.out) or '.', 'RESULTS-EG2.md')
    open(md, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return res


if __name__ == '__main__':
    main()
