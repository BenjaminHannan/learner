"""H1, learned rounds on T1 (PASS-MARKS.md addendum 21; sealed spec /mnt/project-files/architecture/redesign-ideas-2026-10-07.md section 8b),
judged exactly as written: H1 (model 'tool_h1') against T1 (queue 40) of the same seed; q33's plain B2 only printed beside the leak values.
python3 -m custom_io.analyze_h1 --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-pc-t1-screen custom_io/results/49-pc-h1-screen
    [--out custom_io/results/H1-ANALYSIS.json]
Screen, seeds 200 and 201, each H1 seed against T1 on the same seed:
  H-a stability: pooled-5 at loops:32 (forced, stop ignored) - pooled-5 at the model's own stop >= -0.3 on both seeds.
  H-b parity: pooled-5 H1 - T1 >= -1.0 on both seeds; chain-5 >= 99.0 on both; no dev split's 2-seed mean of H1 - T1 below -2.0.
  H-c adaptive: mean rounds on chain-5 turns - mean on one-step turns (big in_dist) >= 2.0 on both seeds.
  H-d cap: pooled-5 turns at the cap (32) <= 1% and their median rounds < 16, on both seeds.
  H-e leaks: loops:0 and donor in_dist <= 5 on both seeds (T1's and B2's values beside).
  H-f audit: the run used the learned stop at p >= 0.5 with cap 32 and the sealed 'settled' label (read from the result), no other threshold.
Reported (amendment 1, spec section 8c): pooled-5 rounds on turns right vs wrong at the end; stops already right vs settled as wrong vs at the
cap; rounds on the pooled-5 split x family cells where q33's B2 (same seed) is below 50%.
Pass = H-a to H-f. Proved wrong: pooled-5 H1 - T1 2-seed mean < -2.0, or the H-c gap's 2-seed mean within 0.5 of zero, or H-a < -1.0 on
either seed. Between: not shown. A run counts only if status ok, the recipe below and the right size; missing or invalid: NOT JUDGED."""
import argparse, json, os
from custom_io.analyze import P5, POOL, SPL, C5, g, load, sub
from custom_io.analyze_t1 import fmt
from custom_io.data import DEV_SPLITS

SCREEN = [200, 201]
RECIPE = dict(steps=24000, batch=256, lr=1e-3, bf16=True)
ARMS = {'H1': ('tool_h1', ({'label': 'settled'},), 3277650),     # the stop label sealed by the spec's amendment 1 (section 8c)
        'T1': ('tool', ({},), 3277393), 'B2': ('ledger', ({'copy': True},), 3302481)}


def valid(r, arm):
    model, cfgs, n = ARMS[arm]
    c = g(r, 'config') or {}
    bad = [f'{k}={c.get(k)!r} (want {v!r})' for k, v in RECIPE.items() if c.get(k) != v]
    if c.get('model') != model or (c.get('cfg') or {}) not in cfgs:
        bad.append(f"model {c.get('model')} cfg {c.get('cfg')} (want {model} {cfgs})")
    if r.get('steps') != RECIPE['steps']:
        bad.append(f"trained {r.get('steps')} steps")
    if r.get('n_params') != n:
        bad.append(f"n_params {r.get('n_params')} (want {n})")
    return bad


def low_cells(h, b):
    """Amendment 1 reporting (iii): rounds used on the pooled-5 split x family cells where q33's B2 of the same seed is below 50%, vs the rest."""
    sf = g(h, 'extra', 'h1', 'split_family') or {}
    if b is None or not sf:
        return None
    acc = {'low': [0, 0, 0, 0], 'rest': [0, 0, 0, 0]}          # turns, rounds, turns at the cap, right
    cells = []
    for sp in POOL:
        for f, st in (sf.get(sp) or {}).items():
            c = g(b, 'final_eval', sp, 'by_family', f)
            if not c or not st.get('n'):
                continue
            k = 'low' if c['correct'] < 0.5 * c['n'] else 'rest'
            if k == 'low':
                cells.append(f'{sp}/{f}')
            a = acc[k]
            a[0] += st['n']; a[1] += st['mean'] * st['n']; a[2] += st['at_cap'] * st['n'] / 100; a[3] += st['exact'] * st['n'] / 100
    return {k: dict(n=a[0], mean_rounds=a[1] / a[0] if a[0] else None, at_cap=100 * a[2] / a[0] if a[0] else None, exact=100 * a[3] / a[0] if a[0] else None)
            for k, a in acc.items()} | dict(cells=cells)


def facts(h, t, b):
    x = g(h, 'extra', 'h1') or {}
    p5 = x.get('pooled5') or {}
    lk = lambda r: None if r is None else dict(loops0=SPL('in_dist')(r, 'loops:0'), donor=g(r, 'lesions', 'donor', 'in_dist', 'exact'))
    return dict(d_pooled5=sub(P5(h), P5(t)), h1_pooled5=P5(h), t1_pooled5=P5(t), h1_chain5=C5(h), t1_chain5=C5(t),
                d_split={sp: sub(SPL(sp)(h), SPL(sp)(t)) for sp in DEV_SPLITS},
                forced={k: P5(h, f'loops:{k}') for k in (8, 16, 32)}, stab=sub(P5(h, 'loops:32'), P5(h)),
                rounds=dict(pooled5=x.get('pooled5'), chain5=g(x, 'chain5', 'mean'), one_step=g(x, 'one_step', 'mean'), gap=x.get('hc_gap'),
                            big_in_dist=x.get('big_in_dist'), by_program_len={k: (v.get('mean'), v.get('n')) for k, v in (x.get('by_program_len') or {}).items()}),
                audit=dict(p_stop=x.get('p_stop'), cap=x.get('cap'), label=x.get('label'), cfg=g(h, 'config', 'cfg')),
                report=dict(rounds_right=p5.get('mean_right'), rounds_wrong=p5.get('mean_wrong'), stops=p5.get('stops'), b2_low_cells=low_cells(h, b)),
                leak=lk(h), t1_leak=lk(t), b2_leak=lk(b), machine_differs=[k for k in ('device', 'data') if g(h, 'config', k) != g(t, 'config', k)])


def screen(runs):
    probs, F = {}, {}
    for s in SCREEN:
        h, t, b = runs.get(('H1', s)), runs.get(('T1', s)), runs.get(('B2', s))
        p = (['H1 missing'] if h is None else valid(h, 'H1')) + (['T1 missing'] if t is None else [f'T1: {x}' for x in valid(t, 'T1')])
        if h is not None and not g(h, 'extra', 'h1'):
            p.append('H1 has no extra.h1 (extra_evals failed: see extra_error)')
        probs[s] = p
        if not p:
            F[s] = facts(h, t, None if b is None or valid(b, 'B2') else b)
    out = dict(seeds=SCREEN, problems=probs, judged=len(F) == len(SCREEN))
    if not out['judged']:
        out['verdict'] = 'NOT JUDGED'
        return out
    n = len(F)
    mean = lambda xs: sum(xs) / len(xs)
    dspl = {sp: mean([f['d_split'][sp] for f in F.values()]) for sp in DEV_SPLITS}
    pr = {s: f['rounds']['pooled5'] or {} for s, f in F.items()}
    m = {'H-a stability: pooled-5 at loops:32 - own stop >= -0.3 on both seeds': dict(
             value={s: f['stab'] for s, f in F.items()}, ok=all(f['stab'] is not None and f['stab'] >= -0.3 for f in F.values())),
         'H-b parity: pooled-5 H1 - T1 >= -1.0 and chain-5 >= 99.0 on both seeds, no dev split 2-seed mean < -2.0': dict(
             value=dict(d_pooled5={s: f['d_pooled5'] for s, f in F.items()}, chain5={s: f['h1_chain5'] for s, f in F.items()}, d_split=dspl),
             ok=all(f['d_pooled5'] >= -1.0 and (f['h1_chain5'] or 0) >= 99.0 for f in F.values()) and all(v >= -2.0 for v in dspl.values())),
         'H-c adaptive: mean rounds chain-5 - one-step >= 2.0 on both seeds': dict(
             value={s: dict(chain5=f['rounds']['chain5'], one_step=f['rounds']['one_step'], gap=f['rounds']['gap']) for s, f in F.items()},
             ok=all(f['rounds']['gap'] is not None and f['rounds']['gap'] >= 2.0 for f in F.values())),
         'H-d cap: pooled-5 turns at 32 <= 1% and median < 16 on both seeds': dict(
             value={s: dict(at_cap=p.get('at_cap'), median=p.get('median'), mean=p.get('mean')) for s, p in pr.items()},
             ok=all(p.get('at_cap') is not None and p['at_cap'] <= 1.0 and p['median'] < 16 for p in pr.values())),
         'H-e leaks: loops:0 and donor in_dist <= 5 on both seeds': dict(
             value={s: dict(H1=f['leak'], T1=f['t1_leak'], B2=f['b2_leak']) for s, f in F.items()},
             ok=all(f['leak']['loops0'] is not None and f['leak']['loops0'] <= 5 and f['leak']['donor'] is not None and f['leak']['donor'] <= 5 for f in F.values())),
         'H-f audit: learned stop at p >= 0.5, cap 32, no other threshold': dict(
             value={s: f['audit'] for s, f in F.items()},
             ok=all(f['audit']['p_stop'] == 0.5 and f['audit']['cap'] == 32 and f['audit']['label'] == 'settled' for f in F.values()))}
    gaps = [f['rounds']['gap'] for f in F.values()]
    d5 = mean([f['d_pooled5'] for f in F.values()])
    wrong = dict(pooled5_mean_below_minus2=d5 < -2.0, hc_gap_within_half=None if None in gaps else abs(mean(gaps)) <= 0.5,
                 ha_below_minus1=any(f['stab'] is not None and f['stab'] < -1.0 for f in F.values()))
    out.update(marks=m, facts=F, d_pooled5_mean=d5, proved_wrong=wrong)
    out['verdict'] = ('PASS: H1 goes to B3 (its 6-seed confirm copies these marks)' if all(x['ok'] for x in m.values())
                      else 'PROVED WRONG' if any(wrong.values()) else 'NOT SHOWN at the screen')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--out', default='custom_io/results/H1-ANALYSIS.json')
    a = ap.parse_args(argv)
    runs, skipped = load(a.results)
    res = dict(screen=screen(runs), skipped=skipped)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1, default=str)
    r = res['screen']
    L = ['# H1: learned rounds on T1 (PASS-MARKS.md addendum 21)', '', 'H1 minus queue 40 T1 on the same seed.', '',
         f'## Screen, seeds 200-201: {r["verdict"]}', '']
    if not r['judged']:
        L += [f"- missing or invalid: {fmt({s: p for s, p in r['problems'].items() if p})}"]
    else:
        L += [f'- {k}: {fmt(x["value"])} -> {x["ok"]}' for k, x in r['marks'].items()]
        L += [f"- proved wrong: {fmt(r['proved_wrong'])}", '', '### Reported, not judged (amendment 1)', '']
        for s_, f in r['facts'].items():
            rp = f['report']
            lc = rp['b2_low_cells'] or {}
            L += [f"- seed {s_}: pooled-5 rounds right {fmt(rp['rounds_right'])} vs wrong {fmt(rp['rounds_wrong'])}; stops {fmt(rp['stops'])}; "
                  f"q33 B2 cells below 50% ({len(lc.get('cells', []))} cells): {fmt(lc.get('low'))} vs the rest {fmt(lc.get('rest'))}"]
        L += ['',
              '| seed | pooled-5 H1 / T1 | forced 8 / 16 / 32 | rounds mean / median / at 32 (pooled-5) | chain-5 / one-step rounds | rounds by program length | label | machine differs |',
              '|---|---|---|---|---|---|---|---|']
        for s, f in r['facts'].items():
            p = f['rounds']['pooled5'] or {}
            L += [f"| {s} | {fmt(f['h1_pooled5'])} / {fmt(f['t1_pooled5'])} | {fmt(f['forced'][8])} / {fmt(f['forced'][16])} / {fmt(f['forced'][32])} | "
                  f"{fmt(p.get('mean'))} / {p.get('median')} / {fmt(p.get('at_cap'))}% | {fmt(f['rounds']['chain5'])} / {fmt(f['rounds']['one_step'])} | "
                  f"{fmt({k: v[0] for k, v in f['rounds']['by_program_len'].items()})} | {f['audit']['label']} | {f['machine_differs'] or '-'} |"]
    L += ['']
    md = os.path.join(os.path.dirname(a.out) or '.', 'RESULTS-H1.md')
    open(md, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return res


if __name__ == '__main__':
    main()
