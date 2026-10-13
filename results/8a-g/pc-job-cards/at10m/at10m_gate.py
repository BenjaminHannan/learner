"""The 10M gate of the agent model (big-run PLAN.md eighteenth Addendum 10-12 (2); AT-1a to AT-1f are sealed in the sixth Addendum 10-11 (5)):
WORK\\insert\\16-at10m.txt (queue 8aAT10M) runs only if AT-1 (8aAT, 3M, seed 400) is not proved wrong on these lines, or cannot be read. Read here, from RESULT.json files:
  AT-1a  proved wrong = pooled-5 more than 6.0 below G2f's (same dev rows), or below g2c3s's
  AT-1c  proved wrong = calculator off (noexec) within 10 points of the full score on the program questions (extra.noexec.program_families vs extra.noexec.intact; as B3-3)
  AT-1d  proved wrong = chain-5 more than 5 below G2f's, or thinker-off (loops:0) pooled-5 above 60% of the full score
  AT-1f  proved wrong = any cap counter above 0 in AT's run (turns_over, tape_entry_over, writer_over, unended, turn_rounds_over, steps_unparsed, no_trace, steps_over, answer_is_call),
         gated only if the counters (RESULT.json cap_hits) are there; otherwise "AT-1f counters not in RESULT.json: reported later, not gated".
  AT-1b (reply swap) and AT-1e (stop and long input) are not gated: reported after the run.
pooled-5 = 100 * sum(correct) / sum(n) over in_dist, answer, frame, vocab, variant (final_eval; lesions['loops:0'] for the lesion). The thresholds are the sealed ones, unchanged.
Standard library only; read-only (writes only --out).

  python -I at10m_gate.py --at AT\\RESULT.json --g2f B3G2\\RESULT.json --pair PTS\\RESULT.json [--out FILE.json]
  python -I at10m_gate.py --selftest

Exit 0 = not proved wrong (16-at10m runs), 3 = proved wrong (it does not), 2 = cannot tell: a file or key missing, a seed that is not 400 (it does not).
"""
import argparse, json, os, sys, tempfile

POOL = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
COUNTERS = ['turns_over', 'tape_entry_over', 'writer_over', 'unended', 'turn_rounds_over', 'steps_unparsed', 'no_trace', 'steps_over', 'answer_is_call']


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def p5(r, les=None):
    """pooled-5 = sum correct / sum n over the five pooled splits (as b3_readout.py and analyze.P5); returns (percent, n)."""
    fe = g(r, 'final_eval') if les is None else g(r, 'lesions', les)
    try:
        n = sum(fe[s]['n'] for s in POOL)
        return 100 * sum(fe[s]['correct'] for s in POOL) / n, n
    except (TypeError, KeyError, ZeroDivisionError):
        return None, None


def load(path):
    try:
        r = json.load(open(path))
        return r if isinstance(r, dict) and r.get('status') == 'ok' and r.get('final_eval') else None
    except Exception:
        return None


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def f(v):
    return 'n/a' if v is None else f'{v:.2f}'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--at', help="AT-1's AT RESULT.json (8aAT, 3M, seed 400)")
    ap.add_argument('--g2f', help="G2f's B3G2 RESULT.json (8aB3G2s400, 3M, seed 400)")
    ap.add_argument('--pair', help="g2c3s's PTS RESULT.json (8aG2C3S, 3M, seed 400)")
    ap.add_argument('--out')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.at and a.g2f and a.pair):
        ap.error('--at, --g2f and --pair are required')
    say = lambda s: print('at10m gate: ' + s, flush=True)
    t, b, p = load(a.at), load(a.g2f), load(a.pair)
    rep = dict(at=a.at, g2f=a.g2f, pair=a.pair, lines={}, verdict=None)
    full, n_at = p5(t)
    gfull, n_g = p5(b)
    pfull, n_p = p5(p)
    off, _ = p5(t, 'loops:0')
    nx, nxi = num(g(t, 'extra', 'noexec', 'program_families')), num(g(t, 'extra', 'noexec', 'intact'))
    c5, c5g = num(g(t, 'chain5', 'intact', 'exact')), num(g(b, 'chain5', 'intact', 'exact'))
    seeds = (g(t, 'config', 'seed'), g(b, 'config', 'seed'), g(p, 'config', 'seed'))
    L = rep['lines']
    d = None if None in (full, gfull) else full - gfull
    L['AT-1a vs G2f'] = dict(at=full, g2f=gfull, diff=d, wrong=None if d is None else d < -6.0)
    d2 = None if None in (full, pfull) else full - pfull
    L['AT-1a vs g2c3s'] = dict(at=full, g2c3s=pfull, lead=d2, wrong=None if d2 is None else d2 < 0.0)
    L['AT-1c calculator-off'] = dict(calc_off=nx, intact=nxi, gap=None if None in (nx, nxi) else nxi - nx,
                                    wrong=None if None in (nx, nxi) else nxi - nx <= 10.0)
    share = None if None in (off, full) or not full else off / full
    L['AT-1d thinker-off'] = dict(loops0=off, full=full, share=share, wrong=None if share is None else share > 0.6)
    d3 = None if None in (c5, c5g) else c5 - c5g
    L['AT-1d chain-5 vs G2f'] = dict(at=c5, g2f=c5g, diff=d3, wrong=None if d3 is None else d3 < -5.0)
    ch = g(t, 'cap_hits')
    if isinstance(ch, dict) and all(k in ch for k in COUNTERS[:5]):
        bad = {k: ch[k] for k in COUNTERS if num(ch.get(k)) is not None and ch[k] > 0}
        L['AT-1f counters'] = dict(counters={k: ch.get(k) for k in COUNTERS}, nonzero=bad, wrong=bool(bad))
    else:
        L['AT-1f counters'] = dict(counters=None, wrong=False, note='not in RESULT.json')
    rep['report'] = dict(seeds=seeds, n_pooled=(n_at, n_g, n_p), steps=g(t, 'steps'), steps_per_s=g(t, 'steps_per_s'), peak_mem_mib=g(t, 'peak_mem_mib'),
                         n_params=g(t, 'n_params'), reply_swap_extra_keys=sorted(g(t, 'extra') or {}))
    say(f"AT-1 {a.at}: {'ok' if t else 'NO ok final eval'}; G2f {a.g2f}: {'ok' if b else 'NO ok final eval'}; g2c3s {a.pair}: {'ok' if p else 'NO ok final eval'}; seeds {seeds}")
    say(f"AT-1a: pooled-5 AT {f(full)} - G2f {f(gfull)} = {f(d)} (proved wrong below -6.0); AT {f(full)} - g2c3s {f(pfull)} = {f(d2)} (proved wrong below 0.0)")
    say(f"AT-1c: calculator off {f(nx)}% vs intact {f(nxi)}% on the program questions (proved wrong if within 10)")
    say(f"AT-1d: chain-5 AT {f(c5)} - G2f {f(c5g)} = {f(d3)} (proved wrong below -5.0); loops:0 pooled-5 {f(off)} = {f(None if share is None else 100 * share)}% of full (proved wrong above 60%)")
    if L['AT-1f counters'].get('counters') is None:
        say('AT-1f counters not in RESULT.json: reported later, not gated')
    else:
        say(f"AT-1f: cap counters {L['AT-1f counters']['counters']} (proved wrong if any is above 0)")
    say('AT-1b (reply swap) and AT-1e (stop and long input) are not gated: reported after the run')
    if len({n for n in (n_at, n_g, n_p) if n is not None}) > 1:
        say(f'WARNING: pooled-5 row counts differ (AT, G2f, g2c3s) = {(n_at, n_g, n_p)}: the "same dev rows" premise is not shown')
    say(f"reported: steps_per_s {f(rep['report']['steps_per_s'])}, peak_mem_mib {rep['report']['peak_mem_mib']}")
    wrong = [k for k, v in L.items() if v['wrong']]
    unknown = [k for k, v in L.items() if v['wrong'] is None]
    if any(s != 400 for s in seeds):
        unknown.append(f'seeds {seeds} are not all 400')
    if wrong:
        rep['verdict'], rc = 'PROVED WRONG: ' + ', '.join(wrong), 3
    elif unknown:
        rep['verdict'], rc = 'CANNOT TELL: ' + ', '.join(unknown), 2
    else:
        rep['verdict'], rc = 'not proved wrong: 16-at10m runs', 0
    say(rep['verdict'])
    if a.out:
        json.dump(rep, open(a.out, 'w'), indent=1)
    return rc


# ---- self-test: fake RESULT.json sets in the real key layout (train.py: final_eval, lesions, chain5, extra.noexec, cap_hits, config.seed) ----
def fake(pooled=60.0, loops0=20.0, chain5=99.5, nx=2.0, nxi=88.0, counters=True, seed=400, n=1000, bump=None):
    sp = lambda pct: {s: dict(correct=round(pct * n / 100), n=n, exact=pct) for s in POOL + ['hold']}
    r = dict(status='ok', config=dict(seed=seed), n_params=1, steps=100, steps_per_s=1.0, peak_mem_mib=1.0, final_eval=sp(pooled), lesions={'loops:0': sp(loops0), 'noexec': sp(pooled)},
             chain5={'intact': dict(exact=chain5, n=200)}, extra={'noexec': dict(program_families=nx, intact=nxi, n=100)})
    if counters:
        r['cap_hits'] = dict({k: 0 for k in COUNTERS}, total=0, reported=dict(turn_cap=3, turn_rounds_capped=1))
    return r


def selftest():
    td = tempfile.mkdtemp(prefix='at10mgate-')
    ok = True

    def run(name, want, at=True, g2f=True, pair=True, **kw):
        nonlocal ok
        paths = {}
        for k, present, r in (('at', at, kw.get('at_r') or fake()), ('g2f', g2f, fake(pooled=61.0, chain5=99.8)), ('pair', pair, fake(pooled=55.0))):
            pth = os.path.join(td, name.replace(' ', '_') + '-' + k + '.json')
            if present:
                json.dump(r, open(pth, 'w'))
            paths[k] = pth
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(['--at', paths['at'], '--g2f', paths['g2f'], '--pair', paths['pair']])
        good = rc == want
        ok &= good
        print(f"selftest {'ok  ' if good else 'FAIL'} {name}: exit {rc} (want {want}): {buf.getvalue().strip().splitlines()[-1]}")

    run('all pass', 0, at_r=fake(pooled=59.0, loops0=20.0, chain5=99.2))
    run('AT-1a exactly 6.0 below G2f and level with g2c3s is not wrong', 0, at_r=fake(pooled=55.0))
    run('AT-1a more than 6 below G2f', 3, at_r=fake(pooled=54.9))
    run('AT-1a below g2c3s only', 3, at_r=fake(pooled=54.0))
    run('AT-1c calculator-off within 10 (78.5 vs 88.0)', 3, at_r=fake(pooled=60.0, nx=78.5, nxi=88.0))
    run('AT-1d thinker-off above 60%', 3, at_r=fake(pooled=60.0, loops0=40.0))
    run('AT-1d chain-5 more than 5 below G2f', 3, at_r=fake(pooled=60.0, chain5=94.7))
    run('AT-1f a counter above 0', 3, at_r=dict(fake(pooled=60.0), cap_hits=dict({k: 0 for k in COUNTERS}, turns_over=2)))
    run('AT-1f counters not in RESULT.json: not gated', 0, at_r=fake(pooled=60.0, counters=False))
    run('AT-1 missing', 2, at=False)
    run('G2f missing', 2, g2f=False)
    run('g2c3s missing', 2, pair=False)
    r = fake(pooled=60.0)
    del r['extra']['noexec']
    run('key missing (noexec)', 2, at_r=r)
    r = fake(pooled=60.0)
    del r['chain5']
    run('key missing (chain5)', 2, at_r=r)
    r = fake(pooled=60.0)
    del r['lesions']['loops:0']
    run('key missing (loops:0)', 2, at_r=r)
    r = fake(pooled=60.0)
    del r['final_eval']['vocab']
    run('key missing (final_eval split)', 2, at_r=r)
    run('seed not 400', 2, at_r=fake(pooled=60.0, seed=401))
    print('at10m_gate self-test ' + ('OK' if ok else 'FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
