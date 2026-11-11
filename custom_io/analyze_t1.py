"""T1, the calculator outside the model (PASS-MARKS.md addendum 17; sealed marks /mnt/project-files/architecture/MARKS-D0-T1-2026-10-07.md),
judged exactly as written: T1 (model 'tool') against q33's plain B2 of the same seed (inside, not retrained).
python3 -m custom_io.analyze_t1 --results custom_io/results/33-pc-confirm-b2 custom_io/results/40-pc-t1-screen [--out custom_io/results/T1-ANALYSIS.json]
Screen (200, 201): pooled-5 T1 - B2 >= -2.0 and chain-5 >= 95 on both; tightening (addendum 17): write_copy operand and answer copy >= 99 on both.
Confirm (200-205): (1) parity, re-sealed before any run (Amendment 2): mean T1 - B2 >= -1.0, its 95% CI lower bound >= -2.0, and T1 >= B2 - 1.0
on at least 5 of 6 seeds (the old "CI inside +-1.0" could not pass at the observed seed spread); (2) chain-5 mean within 1.0 of B2's and >= 99 on 5 of 6 seeds; (3) tool off
(noexec program set) < 5 on every seed; (4) loops:0 and donor in_dist <= 5 on every seed (B2's beside); (5) opswap swap_match >= 99 on every seed;
(6) no dev split's 6-seed mean drops > 2.0. Proved wrong: mean < -2.0 or chain-5 mean < 95; between: not shown. "Every seed" in (3) and (5) is
this file's stricter reading. A run counts only if status ok, the q33 recipe and the right size; a missing or invalid run: NOT JUDGED."""
import argparse, json, math, os
from custom_io.analyze import P5, SPL, C5, POOL, g, load, sub
from custom_io.data import DEV_SPLITS

SCREEN, CONFIRM = [200, 201], [200, 201, 202, 203, 204, 205]
RECIPE = dict(steps=24000, batch=256, lr=1e-3, bf16=True)
ARMS = {'T1': ('tool', {}, 3277393), 'B2': ('ledger', {'copy': True}, 3302481)}
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365}


def valid(r, arm):
    model, cfg, n = ARMS[arm]
    c = g(r, 'config') or {}
    bad = [f'{k}={c.get(k)!r} (want {v!r})' for k, v in RECIPE.items() if c.get(k) != v]
    if c.get('model') != model or (c.get('cfg') or {}) != cfg:
        bad.append(f"model {c.get('model')} cfg {c.get('cfg')} (want {model} {cfg})")
    if r.get('steps') != RECIPE['steps']:
        bad.append(f"trained {r.get('steps')} steps")
    if r.get('n_params') != n:
        bad.append(f"n_params {r.get('n_params')} (want {n})")
    return bad


def pairs_for(runs, seeds):
    probs, pairs = {}, {}
    for s in seeds:
        a, b = runs.get(('T1', s)), runs.get(('B2', s))
        p = (['T1 missing'] if a is None else valid(a, 'T1')) + (['B2 missing'] if b is None else [f'B2: {x}' for x in valid(b, 'B2')])
        probs[s] = p
        if not p:
            pairs[s] = (a, b)
    return probs, pairs


def facts(a, b):
    """Per seed: everything the marks and the link diagnosis read."""
    ex = g(a, 'extra') or {}
    wc, oa = ex.get('write_copy') or {}, ex.get('op_acc') or {}
    lk = lambda r: dict(loops0=SPL('in_dist')(r, 'loops:0'), donor=g(r, 'lesions', 'donor', 'in_dist', 'exact'))
    return dict(d_pooled5=sub(P5(a), P5(b)), t1_pooled5=P5(a), b2_pooled5=P5(b), t1_chain5=C5(a), b2_chain5=C5(b),
                d_split={sp: sub(SPL(sp)(a), SPL(sp)(b)) for sp in DEV_SPLITS}, operand_copy=wc.get('operand_copy'), answer_copy=wc.get('answer_copy'),
                write_copy_n=dict(operand=wc.get('op_n'), answer=wc.get('ans_n'), path_changed=wc.get('path_changed'), too_long=wc.get('too_long')),
                write_copy_by_len=dict(operand=wc.get('op_by_len'), answer=wc.get('ans_by_len')),
                tool_off=g(ex, 'noexec', 'program_families'), tool_off_chain5=g(ex, 'noexec', 'chain5'), swap_match=g(ex, 'opswap', 'swap_match'),
                swap_n=g(ex, 'opswap', 'n_affected'), call_acc=dict(teacher_forced=g(oa, 'teacher_forced', 'call'), free_run=g(oa, 'free_run', 'call'),
                free_run_program=g(oa, 'free_run', 'program'), free_run_answer=g(oa, 'free_run', 'answer')),
                leak=lk(a), b2_leak=lk(b), b2_noexec=g(b, 'extra', 'noexec', 'program_families'), b2_swap=g(b, 'extra', 'opswap', 'swap_match'),
                copy_gate=g(ex, 'copy_gate', 'overall'), machine_differs=[k for k in ('device', 'data') if g(a, 'config', k) != g(b, 'config', k)])


def screen(runs):
    probs, pairs = pairs_for(runs, SCREEN)
    out = dict(seeds=SCREEN, problems=probs, judged=len(pairs) == len(SCREEN))
    if not out['judged']:
        out['verdict'] = 'NOT JUDGED'
        return out
    F = {s: facts(a, b) for s, (a, b) in pairs.items()}
    m = {'S1 pooled-5 T1 - B2 >= -2.0 on both seeds': dict(value={s: f['d_pooled5'] for s, f in F.items()}, ok=all(f['d_pooled5'] >= -2.0 for f in F.values())),
         'S2 chain-5 >= 95 on both seeds': dict(value={s: f['t1_chain5'] for s, f in F.items()}, ok=all(f['t1_chain5'] >= 95 for f in F.values())),
         'S3 write_copy operand and answer exact copy >= 99 on both seeds (D0 writing, addendum 17)': dict(
             value={s: dict(operand=f['operand_copy'], answer=f['answer_copy']) for s, f in F.items()},
             ok=all((f['operand_copy'] or 0) >= 99 and (f['answer_copy'] or 0) >= 99 and (f['write_copy_n']['operand'] or 0) > 0 and (f['write_copy_n']['answer'] or 0) > 0
                    for f in F.values()))}
    out.update(marks=m, facts=F)
    out['verdict'] = 'PASS: run the 6-seed confirm' if all(x['ok'] for x in m.values()) else 'NOT SHOWN at the screen: diagnose the link, no 6-seed run'
    return out


def confirm(runs):
    probs, pairs = pairs_for(runs, CONFIRM)
    out = dict(seeds=CONFIRM, problems=probs, judged=len(pairs) == len(CONFIRM))
    if not out['judged']:
        out['verdict'] = 'NOT JUDGED'
        return out
    F = {s: facts(a, b) for s, (a, b) in pairs.items()}
    n = len(F)
    d = [f['d_pooled5'] for f in F.values()]
    mean = sum(d) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1))
    h = T975[n - 1] * sd / math.sqrt(n)
    c5, c5b = [f['t1_chain5'] for f in F.values()], [f['b2_chain5'] for f in F.values()]
    dspl = {sp: sum(f['d_split'][sp] for f in F.values()) / n for sp in DEV_SPLITS}
    near = sum(f['d_pooled5'] >= -1.0 for f in F.values())
    m = {'1 parity (Amendment 2): mean T1 - B2 >= -1.0, 95% CI lower >= -2.0, T1 >= B2 - 1.0 on >= 5 of 6 seeds': dict(
             value=dict(mean=mean, sd=sd, ci=[mean - h, mean + h], seeds_within_1=near, per_seed={s: f['d_pooled5'] for s, f in F.items()}),
             ok=mean >= -1.0 and mean - h >= -2.0 and near >= 5),
         '2 chain-5 mean within 1.0 of B2 and >= 99 on 5 of 6 seeds': dict(value=dict(t1_mean=sum(c5) / n, b2_mean=sum(c5b) / n, per_seed={s: f['t1_chain5'] for s, f in F.items()}),
                                                                          ok=abs(sum(c5) / n - sum(c5b) / n) <= 1.0 and sum(x >= 99 for x in c5) >= 5),
         '3 tool off: noexec program set < 5 on every seed': dict(value={s: f['tool_off'] for s, f in F.items()}, ok=all(f['tool_off'] is not None and f['tool_off'] < 5 for f in F.values())),
         '4 loops:0 and donor in_dist <= 5 on every seed': dict(value={s: dict(T1=f['leak'], B2=f['b2_leak']) for s, f in F.items()},
                                                                ok=all(f['leak']['loops0'] <= 5 and (f['leak']['donor'] or 0) <= 5 for f in F.values())),
         '5 opswap: >= 99% of affected chain-5 rows follow the swap, every seed': dict(value={s: f['swap_match'] for s, f in F.items()},
                                                                                      ok=all(f['swap_match'] is not None and f['swap_match'] >= 99 and f['swap_n'] for f in F.values())),
         '6 no dev split 6-seed mean drop > 2.0': dict(value=dspl, ok=all(v >= -2.0 for v in dspl.values()))}
    out.update(marks=m, facts=F)
    wrong = mean < -2.0 or sum(c5) / n < 95
    out['proved_wrong'] = wrong
    out['verdict'] = ('PASS: the model works as well with the calculator outside' if all(x['ok'] for x in m.values())
                      else 'PROVED WRONG' if wrong else 'NOT SHOWN: fix the link the diagnosis names, one change, re-screen')
    return out


def fmt(v):
    if isinstance(v, float):
        return f'{v:+.2f}'
    if isinstance(v, dict):
        return '{' + ', '.join(f'{k}: {fmt(x)}' for k, x in v.items()) + '}'
    if isinstance(v, list):
        return '[' + ', '.join(fmt(x) for x in v) + ']'
    return str(v)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--out', default='custom_io/results/T1-ANALYSIS.json')
    a = ap.parse_args(argv)
    runs, skipped = load(a.results)
    res = dict(screen=screen(runs), confirm=confirm(runs), skipped=skipped)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1, default=str)
    L = ['# T1: the calculator outside the model (PASS-MARKS.md addendum 17)', '', 'T1 minus q33 plain B2 on the same seed.', '']
    for key, title in (('screen', 'Screen, seeds 200-201'), ('confirm', '6-seed confirm, seeds 200-205')):
        r = res[key]
        L += [f'## {title}: {r["verdict"]}', '']
        if not r['judged']:
            L += [f"- missing or invalid: {fmt({s: p for s, p in r['problems'].items() if p})}", '']
            continue
        L += [f'- {k}: {fmt(x["value"])} -> {x["ok"]}' for k, x in r['marks'].items()]
        if 'proved_wrong' in r:
            L += [f"- proved wrong: {r['proved_wrong']}"]
        L += ['', '| seed | call acc TF / free | free-run program | tool off | swap | loops:0 T1 / B2 | donor T1 / B2 | copy gate | machine differs |', '|---|---|---|---|---|---|---|---|---|']
        for s, f in r['facts'].items():
            ca = f['call_acc']
            L += [f"| {s} | {fmt(ca['teacher_forced'])} / {fmt(ca['free_run'])} | {fmt(ca['free_run_program'])} | {fmt(f['tool_off'])} | {fmt(f['swap_match'])} | "
                  f"{fmt(f['leak']['loops0'])} / {fmt(f['b2_leak']['loops0'])} | {fmt(f['leak']['donor'])} / {fmt(f['b2_leak']['donor'])} | {fmt(f['copy_gate'])} | {f['machine_differs'] or '-'} |"]
        L += ['']
    md = os.path.join(os.path.dirname(a.out) or '.', 'RESULTS-T1.md')
    open(md, 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return res


if __name__ == '__main__':
    main()
