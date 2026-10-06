"""EmbeddingGemma 2 arms for B2 (PASS-MARKS.md addendum 4), Test LR, the per-round readout loss (addendum 5), and the reader without its
letter window, EGR and R0 (addendum 6), EGO, EmbeddingGemma as the whole reader (addendum 7), EGM, the same through a 2-layer adapter (addendum 8), and EGW, a 768-wide thinker with no adapter (addendum 9; on rented 5090s, each judged against
plain B2 trained on the same box, B2V, addendum 10), computed exactly as written.
python3 -m custom_io.analyze_eg --results custom_io/results/33-pc-confirm-b2 custom_io/results/36-pc-eg2 [--out custom_io/results/EG2-ANALYSIS.json]
Arms EGE (eg_embed) and EGT (eg_teach 0.1), each paired by seed (200, 201) with plain B2 (run folders B2_s200, B2_s201). A run counts only if it
is status 'ok', trained 24,000 steps with the B2 flags and its own switch, and the base run is plain B2 with the same flags; otherwise its
marks are NOT JUDGED (never a crash). Writes the JSON and RESULTS-EG2.md next to it."""
import argparse, json, os
from custom_io.analyze import P5, SPL, C5, POOL, g, load, sub, chk, allof

SEEDS, BASE = [200, 201], 'B2'
BASES = (BASE, 'B2V')       # B2V: plain B2 trained on the same rented box as an arm (addendum 10)
ARMS = {'EGE': {'copy': True, 'eg_embed': True}, 'EGT': {'copy': True, 'eg_teach': 0.1}, 'LR': {'copy': True, 'round_readout': 1.0},
        'EGR': {'copy': True, 'eg_embed': True, 'reader_layers': 0}, 'R0': {'copy': True, 'reader_layers': 0},
        'EGO': {'copy': True, 'eg_embed': True, 'reader_layers': 0, 'letters_in': False},
        'EGM': {'copy': True, 'eg_embed': True, 'reader_layers': 0, 'letters_in': False, 'eg_adapter': 'mlp'},
        'EGW': {'copy': True, 'd': 768, 'n_heads': 12, 'eg_embed': True, 'reader_layers': 0, 'letters_in': False, 'eg_adapter': 'none'}}
RECIPE = dict(steps=24000, batch=256, lr=1e-3, bf16=True)
SIZES = {'B2': 3302481, 'EGE': 3500881, 'EGT': 3368785, 'LR': 3302481, 'EGR': 2843985, 'R0': 2645585, 'EGO': 2843985, 'EGM': 2909777, 'EGW': 22164357}


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


def VF(r):
    """exact match pooled over the vocab and frame splits (new words, new wording), addendum 6 mark 2."""
    fe = g(r, 'final_eval')
    try:
        return 100 * sum(fe[s]['correct'] for s in ('vocab', 'frame')) / sum(fe[s]['n'] for s in ('vocab', 'frame'))
    except (TypeError, KeyError, ZeroDivisionError):
        return None


def leak(r):
    return dict(loops0=SPL('in_dist')(r, 'loops:0'), donor=g(r, 'lesions', 'donor', 'in_dist', 'exact'))


def base_for(runs, a, s):
    """Plain B2 of seed s on the same machine as run a (config.device and config.data equal, addendum 10); else the first found, whose
    mismatch judge() then reports."""
    c = [(n, runs[(n, s)]) for n in BASES if (n, s) in runs]
    if a is not None:
        for n, b in c:
            if all(g(a, 'config', k) == g(b, 'config', k) for k in ('device', 'data')):
                return n, b
    return c[0] if c else (None, None)


def judge(runs, arm):
    """Marks 1-5 for one arm -> dict."""
    probs, pairs, used = {}, {}, {}
    for s in SEEDS:
        a = runs.get((arm, s))
        used[s], b = base_for(runs, a, s)
        p = (['missing'] if a is None else valid(a, ARMS[arm], arm)) + (['base missing'] if b is None else [f'base: {x}' for x in valid(b, {'copy': True}, 'B2')])
        if a is not None and b is not None:        # same machine: local_runner passes WORK/data, so the data path names the machine
            for k in ('device', 'data'):
                if g(a, 'config', k) != g(b, 'config', k):
                    p.append(f"arm and base differ in config.{k}: {g(a, 'config', k)!r} vs {g(b, 'config', k)!r}")
        probs[s] = p
        if not p:
            pairs[s] = (a, b)
    out = dict(arm=arm, problems=probs, judged=len(pairs) == len(SEEDS), base={s: used[s] for s in pairs})
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
    if arm in ('EGR', 'R0', 'EGO', 'EGM', 'EGW'):        # addenda 6-9 (EGO, EGM and EGW use EGR's marks)
        return judge_reader(out, arm, pairs, d, mean, full, dp5, dspl, c5, lk, lk_base)
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


def judge_reader(out, arm, pairs, d, mean, full, dp5, dspl, c5, lk, lk_base):
    """Addendum 6. EGR: marks 1-5 vs plain B2 on the same seed; R0: the diagnostic verdict only."""
    drops = {sp: mean(v) for sp, v in dspl.items()}
    ro = dict(per_split=dspl, family_split=d(SPL('family')),
              abs={s: dict(arm_p5=P5(a), base_p5=P5(b), arm_vf=VF(a), base_vf=VF(b)) for s, (a, b) in pairs.items()},
              steps_per_s={s: (a.get('steps_per_s'), b.get('steps_per_s')) for s, (a, b) in pairs.items()},
              size={s: g(a, 'extra', 'size') for s, (a, _) in pairs.items()})
    out['read_only'] = ro
    if arm == 'R0':
        gap = {s: (None if v is None else -v) for s, v in dp5.items()}        # B2 minus R0
        out['marks'] = {'B2 minus R0 pooled-5, per seed': dict(value=gap, ok='read only')}
        ok = out['judged'] and full(gap) and None not in gap.values()
        out['verdict'] = ('NOT JUDGED' if not ok else 'the window matters' if all(v >= 1.0 for v in gap.values())
                          else 'the window does nothing on these tests' if all(abs(v) < 1.0 for v in gap.values()) else 'unclear')
        out['read_only']['per_split_drops_2seed_mean'] = drops
        return out
    dvf = d(VF)
    m = {}
    m['1 pooled-5 change >= -1.0 on both seeds'] = dict(value=dp5, ok=allof(chk(v, '>=', -1.0) for v in dp5.values()) if full(dp5) else 'n/a')
    m['2 new words + new wording change >= 0.0, 2-seed mean'] = dict(value=mean(dvf), per_seed=dvf, ok=chk(mean(dvf), '>=', 0.0))
    m['3 no dev split drops more than 2.0 (2-seed mean)'] = dict(value=drops, ok=allof(chk(v, '>=', -2.0) for v in drops.values()))
    m['4 chain-5 >= 99.0 on both seeds'] = dict(value=c5, ok=allof(chk(v, '>=', 99.0) for v in c5.values()) if full(c5) else 'n/a')
    m['5 loops:0 in_dist <= plain B2 + 1.0 and donor in_dist <= 5 on both seeds'] = dict(value=lk, plain_b2_same_seeds_read_only=lk_base,
        ok=allof([chk(sub(lk[s]['loops0'], lk_base[s]['loops0']), '<=', 1.0) for s in lk] + [chk(v['donor'], '<=', 5) for v in lk.values()]) if full(lk) else 'n/a')
    out['marks'] = m
    oks = [x['ok'] for x in m.values()]
    out['verdict'] = 'NOT JUDGED' if not out['judged'] or 'n/a' in oks else ('PASS' if all(x is True for x in oks) else 'FAIL (stop this arm)')
    if out['verdict'] == 'PASS' and all(v is not None and v >= 1.0 for v in dp5.values()):
        out['verdict'] = 'PASS, better than B2'
    out['proved_wrong'] = dict(pooled5_mean_below_minus3=None if mean(dp5) is None else mean(dp5) < -3.0,
                               chain5_below_95=None if not full(c5) else any(v is not None and v < 95.0 for v in c5.values()))
    return out


LETTER_FAMS = ['letter_ops', 'copy_word', 'cipher_map', 'digits_parity', 'group_induct']


def arm_minus(runs, x, y):
    """Read only (addenda 7 and 8): arm x minus arm y per seed (pooled-5, and in_dist exact on each letter family), when both runs exist and are valid."""
    def fam(r, f):
        x = g(r, 'final_eval', 'in_dist', 'by_family', f)
        return None if not x or not x.get('n') else 100 * x['correct'] / x['n']
    out = {}
    for s in SEEDS:
        a, b = runs.get((x, s)), runs.get((y, s))
        if a is None or b is None or valid(a, ARMS[x], x) or valid(b, ARMS[y], y):
            continue
        out[s] = dict(pooled5=sub(P5(a), P5(b)), **{f: sub(fam(a, f), fam(b, f)) for f in LETTER_FAMS})
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
    res['ego_minus_egr_read_only'] = arm_minus(runs, 'EGO', 'EGR')
    res['egm_minus_ego_read_only'] = arm_minus(runs, 'EGM', 'EGO')
    res['egw_minus_egm_read_only'] = arm_minus(runs, 'EGW', 'EGM')
    # addendum 10: plain B2 on the rented box minus plain B2 on the PC, same seed (read only); over 3 points on a seed = EGW machine-sensitive
    dev = {s: sub(P5(runs[('B2V', s)]), P5(runs[(BASE, s)])) for s in SEEDS if ('B2V', s) in runs and (BASE, s) in runs}
    res['b2v_minus_b2_pooled5_read_only'] = dev
    res['egw_machine_sensitive'] = any(v is not None and abs(v) > 3 for v in dev.values())
    passing = {k: res['arms'][k] for k in ('EGW', 'EGM', 'EGO') if res['arms'][k]['verdict'].startswith('PASS')}
    on_pc = lambda k: set(passing[k]['base'].values()) == {BASE}
    if res['egw_machine_sensitive'] and any(on_pc(k) for k in passing) and not all(on_pc(k) for k in passing):
        # addenda 10-11: an arm judged on a rented box is not picked over a passing PC arm until it is re-run on the PC
        left_out = sorted(k for k in passing if not on_pc(k))
        passing = {k: v for k, v in passing.items() if on_pc(k)}
        res['reader_for_confirm_note'] = f'{", ".join(left_out)} pass but were judged on the rented boxes, which are machine-sensitive (addendum 10): left out of the choice until re-run on the PC'
    if passing:     # addendum 9: the highest 2-seed pooled-5 mean wins, unless a smaller passing arm is within 0.5 of it
        mm = {k: sum(v['marks']['1 pooled-5 change >= -1.0 on both seeds']['value'].values()) / len(SEEDS) for k, v in passing.items()}
        best = max(mm.values())
        res['reader_for_confirm'] = min((k for k in mm if mm[k] >= best - 0.5), key=lambda k: SIZES[k])
        res['reader_for_confirm_means'] = mm
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1, default=str)
    L = ['# EmbeddingGemma 2 arms (PASS-MARKS.md addendum 4), Test LR (addendum 5) and the reader without its window (addendum 6) for B2', '', f'Seeds {SEEDS}, each arm minus plain B2 on the same seed.', '']
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
            L += [f'- proved wrong: {r["proved_wrong"]}']
        L += [f'- read only: family split change {fmt(r["read_only"]["family_split"])}; size {r["read_only"]["size"]}', '']
    for key, title in (('ego_minus_egr_read_only', 'EGO minus EGR (read only, addendum 7)'), ('egm_minus_ego_read_only', 'EGM minus EGO (read only, addendum 8)'),
                       ('egw_minus_egm_read_only', 'EGW minus EGM (read only, addendum 9)')):
        if res[key]:
            L += [f'## {title}', '', f"- {fmt(res[key])}", '']
    if dev:
        L += ['## Device check (read only, addendum 10)', '', f"- plain B2 on the rented 5090 minus plain B2 on the PC, pooled-5: {fmt(dev)}"
              + (' -> rented-box results machine-sensitive' if res['egw_machine_sensitive'] else ''), '']
    if res.get('reader_for_confirm_note'):
        L += [res['reader_for_confirm_note'], '']
    if res.get('reader_for_confirm'):
        L += [f"EmbeddingGemma reader for the 6-seed confirm (addendum 9): {res['reader_for_confirm']} (2-seed pooled-5 change: {fmt(res['reader_for_confirm_means'])})", '']
    md = os.path.join(os.path.dirname(a.out) or '.', 'RESULTS-EG2.md')
    open(md, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return res


if __name__ == '__main__':
    main()
