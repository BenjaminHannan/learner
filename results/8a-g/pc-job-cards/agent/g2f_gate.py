"""The AT-1 gate at the post-G1 chain's first insert check point (spec addendum AD; big-run PLAN.md sixth Addendum 10-11 (3)): AT-1 runs only
if G2f seed 400 (arm B3G2, 3M) is not proved wrong on B3G2-1 to B3G2-3. At this check point g2c3s and G2f have run and B3 group 1 3M has not,
so only the proved-wrong lines that do not need group 1 can be read here:
  B3G2-1  G2f's pooled-5 below g2c3s's (lead under 0.0)
  B3G2-2  thinker-off (loops:0) pooled-5 above 60% of the full score
  B3G2-3  calculator off (noexec) within 10 points of intact on the program questions
B3G2-1's "more than 6.0 below group 1" and B3G2-2's "chain-5 more than 5 below group 1" are read by hand when group 1 lands. Standard library
only; read-only (writes only --out).

  python -I g2f_gate.py --g2f B3G2\\RESULT.json --pair PTS\\RESULT.json [--out FILE.json]

Exit 0 = not proved wrong on the readable lines (AT-1 runs), 3 = proved wrong (AT-1 does not run), 2 = cannot tell (AT-1 does not run).
"""
import argparse, json, sys

POOL = ['in_dist', 'answer', 'frame', 'vocab', 'variant']


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def p5(r, les=None):
    """pooled-5 = sum correct / sum n over the five pooled splits (as b3_readout.py and analyze.P5)."""
    fe = g(r, 'final_eval') if les is None else g(r, 'lesions', les)
    try:
        return 100 * sum(fe[s]['correct'] for s in POOL) / sum(fe[s]['n'] for s in POOL)
    except (TypeError, KeyError, ZeroDivisionError):
        return None


def load(path):
    try:
        r = json.load(open(path))
        return r if isinstance(r, dict) and r.get('status') == 'ok' and r.get('final_eval') else None
    except Exception:
        return None


def f(v):
    return 'n/a' if v is None else f'{v:.2f}'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--g2f', required=True, help="G2f's B3G2 RESULT.json (8aB3G2s400, 3M, seed 400)")
    ap.add_argument('--pair', required=True, help="g2c3s's PTS RESULT.json (8aG2C3S, 3M, seed 400)")
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    say = lambda s: print('g2f gate: ' + s, flush=True)
    b, p = load(a.g2f), load(a.pair)
    rep = dict(g2f=a.g2f, pair=a.pair, lines={}, verdict=None)
    full, pp5 = p5(b), p5(p)
    off = p5(b, 'loops:0')
    nx, nxi = g(b, 'extra', 'noexec', 'program_families'), g(b, 'extra', 'noexec', 'intact')
    seeds = (g(b, 'config', 'seed'), g(p, 'config', 'seed'))
    lines = rep['lines']
    lines['B3G2-1 vs g2c3s'] = dict(g2f=full, g2c3s=pp5, lead=None if None in (full, pp5) else full - pp5,
                                    wrong=None if None in (full, pp5) else full < pp5)
    lines['B3G2-2 thinker-off'] = dict(loops0=off, full=full, share=None if None in (off, full) or not full else off / full,
                                       wrong=None if None in (off, full) or not full else off / full > 0.6)
    lines['B3G2-3 calculator-off'] = dict(calc_off=nx, intact=nxi, gap=None if None in (nx, nxi) else nxi - nx,
                                          wrong=None if None in (nx, nxi) else nxi - nx < 10.0)
    rep['report'] = dict(seeds=seeds, chain5=g(b, 'chain5', 'intact', 'exact'), steps=b.get('steps') if b else None,
                         steps_unparsed=g(b, 'cap_hits', 'steps_unparsed'), n_params=b.get('n_params') if b else None)
    say(f"G2f {a.g2f}: {'ok' if b else 'NO ok final eval'}; g2c3s {a.pair}: {'ok' if p else 'NO ok final eval'}; seeds {seeds}")
    l1, l2, l3 = (lines[k] for k in ('B3G2-1 vs g2c3s', 'B3G2-2 thinker-off', 'B3G2-3 calculator-off'))
    say(f"B3G2-1 (g2c3s clause): pooled-5 G2f {f(full)} - g2c3s {f(pp5)} = {f(l1['lead'])} (proved wrong below 0.0)")
    say(f"B3G2-2 (thinker-off clause): loops:0 pooled-5 {f(off)} = {f(None if l2['share'] is None else 100 * l2['share'])}% of full (proved wrong above 60%)")
    say(f"B3G2-3: calculator off {f(nx)}% vs intact {f(nxi)}% on the program questions (proved wrong if within 10)")
    say(f"reported: chain-5 {f(rep['report']['chain5'])}; steps_unparsed {rep['report']['steps_unparsed']}; group 1 clauses of B3G2-1 and B3G2-2 are read by hand later")
    wrong = [k for k, v in lines.items() if v['wrong']]
    unknown = [k for k, v in lines.items() if v['wrong'] is None]
    if seeds[0] != 400 or seeds[1] != 400:
        unknown.append(f'seeds {seeds} are not both 400')
    if wrong:
        rep['verdict'], rc = 'PROVED WRONG: ' + ', '.join(wrong), 3
    elif unknown:
        rep['verdict'], rc = 'CANNOT TELL: ' + ', '.join(unknown), 2
    else:
        rep['verdict'], rc = 'not proved wrong on the readable lines: AT-1 runs', 0
    say(rep['verdict'])
    if a.out:
        json.dump(rep, open(a.out, 'w'), indent=1)
    return rc


if __name__ == '__main__':
    sys.exit(main())
