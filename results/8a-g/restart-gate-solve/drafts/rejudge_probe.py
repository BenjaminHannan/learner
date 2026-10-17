#!/usr/bin/env python3
"""rejudge_probe.py: re-reads a resume-noise probe (PROBE-RESUME-<job>.json from `g2fa4_supervisor.py probe-resume`) with the PRE-REGISTERED reading below. Python 3, standard library only.

    python rejudge_probe.py PROBE-RESUME-g2fa8.json [--trace-a-mean 0.0282] [--trace-a-json TRACE-A-g2fa8.json | state.json]

It changes nothing of the probe: it reads C, R1, R2 (the run's logged losses for the probed updates and the two resumes), applies the reading, prints a plain-words paragraph and
the numbers, and writes REJUDGE-<job>.json next to the input. The registered rule of the probe (PASS if d <= max(0.10, 3n)) is computed too, unchanged, and is part of the reading.
Exit code: 0 INSIDE healthy noise, 1 UNRESOLVED, 2 OUTSIDE, 3 the input cannot be read (a probe that was refused to judge, no C / R1 / R2, ...).

The value v of trace A is, in this order: --trace-a-mean, else resume.mean_abs from --trace-a-json (a TRACE-A-<job>.json, or the state.json whose jobs.<job>.traceA holds it), else 0.0282.

PRE-REGISTERED READING (text copied verbatim into the output):
  - Restore check: first_r1_c == first_r2_c == 0 exactly (else: "restore differs at the first update: wrong checkpoint or incomplete restore; investigate, do not read").
  - Exchangeability: ratio = Dbar/Nbar <= 2.0 and registered max rule PASS.
  - Verdict on the trace-A value v (default 0.0282): INSIDE healthy noise if restore check and exchangeability hold AND v <= max(0.02, 2*Nbar); UNRESOLVED if restore check and exchangeability hold but v > max(0.02, 2*Nbar) (the probe window 201-250 is calmer than the trace-A window 101-150, so only a same-window measurement can settle it); OUTSIDE if the restore check or exchangeability fails.
  - Print a plain-words paragraph plus the numbers; write a JSON next to the input (REJUDGE-<job>.json).
Definitions: first_r1_c / first_r2_c = |R1 - C| / |R2 - C| at the first probe update; Dbar = mean(mean|R1-C|, mean|R2-C|); Nbar = mean|R1-R2|; ratio = Dbar/Nbar
(inf if Nbar == 0 and Dbar > 0; 1.0 if both are 0); registered max rule: n = max|R1-R2|, d = max(|R1-C|, |R2-C|), PASS if d <= max(0.10, 3n).
"""
import argparse, json, sys
from pathlib import Path

PREREG = (
    '  - Restore check: first_r1_c == first_r2_c == 0 exactly (else: "restore differs at the first update: wrong checkpoint or incomplete restore; investigate, do not read").\n'
    '  - Exchangeability: ratio = Dbar/Nbar <= 2.0 and registered max rule PASS.\n'
    '  - Verdict on the trace-A value v (default 0.0282): INSIDE healthy noise if restore check and exchangeability hold AND v <= max(0.02, 2*Nbar); UNRESOLVED if restore check and exchangeability hold but v > max(0.02, 2*Nbar) (the probe window 201-250 is calmer than the trace-A window 101-150, so only a same-window measurement can settle it); OUTSIDE if the restore check or exchangeability fails.\n'
    '  - Print a plain-words paragraph plus the numbers; write a JSON next to the input (REJUDGE-<job>.json).\n')
RESTORE_MSG = 'restore differs at the first update: wrong checkpoint or incomplete restore; investigate, do not read'
DEFAULT_V = 0.0282
EXIT = {'INSIDE healthy noise': 0, 'UNRESOLVED': 1, 'OUTSIDE': 2}


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def rejudge(C, R1, R2, v=DEFAULT_V):
    """-> dict with every number of the reading and `verdict` in ('INSIDE healthy noise', 'UNRESOLVED', 'OUTSIDE'). Pure function."""
    if not (len(C) == len(R1) == len(R2) and C):
        raise ValueError('C, R1, R2 must have the same non-zero length')
    d12, d1, d2 = ([abs(x - y) for x, y in zip(a, b)] for a, b in ((R1, R2), (R1, C), (R2, C)))
    n, d = max(d12), max(d1 + d2)
    reg_limit = max(0.10, 3 * n)
    reg = 'PASS' if d <= reg_limit else 'FAIL'
    dbar, nbar = mean([mean(d1), mean(d2)]), mean(d12)
    ratio = (float('inf') if dbar > 0 else 1.0) if nbar == 0 else dbar / nbar
    restore_ok = d1[0] == 0 and d2[0] == 0
    exch_ok = ratio <= 2.0 and reg == 'PASS'
    limit = max(0.02, 2 * nbar)
    if restore_ok and exch_ok:
        verdict = 'INSIDE healthy noise' if v <= limit else 'UNRESOLVED'
    else:
        verdict = 'OUTSIDE'
    return dict(verdict=verdict, restore_ok=restore_ok, exchangeability_ok=exch_ok, first_r1_c=d1[0], first_r2_c=d2[0], first_r1_r2=d12[0], Dbar=dbar, Nbar=nbar, ratio=ratio,
                n=n, d=d, registered_limit=reg_limit, registered_verdict=reg, trace_a_value=v, noise_limit=limit, n_updates=len(C))


def words(r, job):
    f = lambda x: f'{x:.4f}'
    v, lim = r['trace_a_value'], r['noise_limit']
    ex = (f'The two restarts differ from the real run by {f(r["Dbar"])} on average and from each other by {f(r["Nbar"])} on average (ratio {r["ratio"]:.2f}); '
          f'the registered rule (largest gap {f(r["d"])} against its limit {f(r["registered_limit"])}) says {r["registered_verdict"]}.')
    if not r['restore_ok']:
        return (f'OUTSIDE. At the very first redone update the restarted run already differs from the real run (|R1-C| = {r["first_r1_c"]:.6f}, |R2-C| = {r["first_r2_c"]:.6f}; it must be exactly 0). '
                f'{RESTORE_MSG}. {ex}')
    if not r['exchangeability_ok']:
        why = 'the registered rule failed' if r['registered_verdict'] != 'PASS' else f'the ratio {r["ratio"]:.2f} is above 2.0'
        return (f'OUTSIDE. The first redone update is exact (the restore looks complete), but a restart is not interchangeable with the run\'s own continuation: {why}. {ex} '
                'The difference between a restart and the real run is larger than the difference between two restarts of each other, so it is not just the card\'s run-to-run noise.')
    if r['verdict'].startswith('INSIDE'):
        return (f'INSIDE healthy noise. The first redone update is exact, a restart behaves like another restart of the same checkpoint (ratio {r["ratio"]:.2f}, at most 2.0), and the trace-A value {v:.4f} '
                f'is at most max(0.02, 2 x Nbar) = {f(lim)}. {ex} The trace-A resume difference is the size the card makes on its own.')
    return (f'UNRESOLVED. The first redone update is exact and a restart behaves like another restart (ratio {r["ratio"]:.2f}), but the trace-A value {v:.4f} is above max(0.02, 2 x Nbar) = {f(lim)}. '
            f'{ex} The probe window (updates 201-250) is calmer than the trace-A window (101-150), so a small noise here does not settle a larger difference there: only a measurement in the same window can.')


def trace_a_value(args, job):
    """-> (v, where it came from)."""
    if args.trace_a_mean is not None:
        return args.trace_a_mean, '--trace-a-mean'
    if args.trace_a_json:
        d = json.load(open(args.trace_a_json, encoding='utf-8'))
        tr = d['jobs'][job]['traceA'] if isinstance(d.get('jobs'), dict) and job in d['jobs'] and 'traceA' in d['jobs'][job] else d
        res = tr.get('resume') if isinstance(tr, dict) else None
        if not res or 'mean_abs' not in res:
            raise ValueError(f'{args.trace_a_json}: no resume.mean_abs (trace A of job {job})')
        return float(res['mean_abs']), args.trace_a_json
    return DEFAULT_V, 'default'


def main(argv=None):
    ap = argparse.ArgumentParser(description='re-read a resume-noise probe with the pre-registered reading')
    ap.add_argument('probe', help='PROBE-RESUME-<job>.json')
    ap.add_argument('--trace-a-mean', type=float, help=f'trace A mean absolute resume difference v (default {DEFAULT_V})')
    ap.add_argument('--trace-a-json', help='TRACE-A-<job>.json or state.json: v = resume.mean_abs from it (--trace-a-mean wins)')
    a = ap.parse_args(argv)
    p = Path(a.probe)
    try:
        pr = json.loads(p.read_text(encoding='utf-8'))
        job = pr['job']
        if pr.get('why_fail') or not all(k in pr for k in ('C', 'R1', 'R2')):
            print(f'cannot re-read {p}: the probe did not judge ({pr.get("why_fail") or "no C / R1 / R2 in the file"})')
            return 3
        v, src = trace_a_value(a, job)
        r = rejudge(pr['C'], pr['R1'], pr['R2'], v)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f'cannot re-read {p}: {e!r}')
        return 3
    r.update(job=job, source=str(p), trace_a_value_from=src, step=pr.get('step'), upto=pr.get('upto'), preregistered_reading=PREREG, plain_words=words(r, job))
    out = p.with_name(f'REJUDGE-{job}.json')
    out.write_text(json.dumps(r, indent=1), encoding='utf-8')
    print(f'REJUDGE {job}: {r["verdict"]}\n')
    print('Pre-registered reading (verbatim):\n' + PREREG)
    print(r['plain_words'] + '\n')
    print(f'numbers ({r["n_updates"]} probe updates, {pr.get("step")}+1..{pr.get("upto")}):')
    print(f'  first update: |R1-C| = {r["first_r1_c"]!r}, |R2-C| = {r["first_r2_c"]!r}, |R1-R2| = {r["first_r1_r2"]!r}  -> restore check {"holds" if r["restore_ok"] else "FAILS"}')
    print(f'  Dbar = {r["Dbar"]:.6f}, Nbar = {r["Nbar"]:.6f}, ratio = {r["ratio"]:.4f}; registered rule: n = {r["n"]:.6f}, d = {r["d"]:.6f}, limit {r["registered_limit"]:.6f} -> {r["registered_verdict"]}  -> exchangeability {"holds" if r["exchangeability_ok"] else "FAILS"}')
    print(f'  trace-A value v = {r["trace_a_value"]} (from {src}); max(0.02, 2*Nbar) = {r["noise_limit"]:.6f}')
    print(f'written: {out}')
    return EXIT[r['verdict']]


if __name__ == '__main__':
    sys.exit(main())
