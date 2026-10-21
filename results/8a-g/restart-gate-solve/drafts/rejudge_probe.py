#!/usr/bin/env python3
"""rejudge_probe.py: re-reads a resume-noise probe (PROBE-RESUME-<job>.json from `g2fa4_supervisor.py probe-resume`) with the PRE-REGISTERED reading below, as AMENDED by Amendment 1 and Amendment 2 (B1: ESCALATE). Python 3, standard library only.

    python rejudge_probe.py PROBE-RESUME-g2fa8.json [--trace-a-mean 0.0282] [--trace-a-json TRACE-A-g2fa8.json|state.json] [--calibration PROBE2.json]

It changes nothing of the probe: it reads C, R1, R2 (the run's logged losses for the probed updates and the two resumes), applies the AMENDED reading (the original text and the amendment are both below), prints a plain-words
paragraph and the numbers, and writes REJUDGE-<job>.json next to the input. The registered rule of the probe (PASS if d <= max(0.10, 3n)) is computed too, unchanged, and is part of the reading. The reading of the
ORIGINAL text alone is recorded in the JSON as original_reading_verdict (for comparison only).
--calibration PROBE2.json is a second probe JSON of the SAME job, step and window (its R1, R2 are R3, R4; its C must equal the first file's C, else it is refused; it is also refused, exit 3, if it is the same file or the same content as the probe or if its R1, R2 repeat the probe's R1, R2 in either order: a copy of the first probe would only echo it). It is APPLIED ONLY when the two-resume verdict is UNRESOLVED_CALIBRATE (see the Clarification below); otherwise the two-resume verdict stands, calibration is null and calibration_not_applied in the JSON (and a printed note) says why (this includes ESCALATE: more resumes of a checkpoint whose restarts are bit-identical would repeat them). The two-resume verdict is computed FIRST and the --calibration file is opened, read and validated ONLY when it will be applied (verdict UNRESOLVED_CALIBRATE): for any other verdict the file is not read at all, so a bad calibration file can never hide an INSIDE, UNRESOLVED (window), OUTSIDE or ESCALATE reading; the JSON then has calibration_offered = the path given, calibration_source null and calibration_not_applied (calibration_source is the path only when the calibration was applied). See A1.3 below.
REJUDGE-<job>.json is STRICT JSON (written with allow_nan=False): a ratio of infinity (every ESCALATE has Nbar = 0, so ratio = Dbar/Nbar is infinite) is written as `"ratio": null` with `"ratio_infinite": true` (false otherwise), and any other non-finite float as null with a `<key>_nonfinite` companion ("inf", "-inf" or "nan"); the printed text still says inf.
An earlier REJUDGE-<job>.json is renamed REJUDGE-<job>.json.aside-<stamp> before the new one is written (the first reading is never lost).
Exit code: 0 INSIDE healthy noise, 1 UNRESOLVED (either kind; the output says which: "UNRESOLVED (window)" or "UNRESOLVED_CALIBRATE"), 2 OUTSIDE, 3 the input cannot be read (a probe that was refused to judge, no C / R1 / R2, ...), 4 ESCALATE (framing falsified, PREREG Amendment 2 below: neither a pass nor a fail, the run is not read, no calibration is asked for; the question goes to Ben).

The value v of trace A is, in this order: --trace-a-mean, else resume.mean_abs from --trace-a-json (a TRACE-A-<job>.json, or the state.json whose jobs.<job>.traceA holds it), else 0.0282.

PRE-REGISTERED READING (text copied verbatim into the output):
  - Restore check: first_r1_c == first_r2_c == 0 exactly (else: "restore differs at the first update: wrong checkpoint or incomplete restore; investigate, do not read").
  - Exchangeability: ratio = Dbar/Nbar <= 2.0 and registered max rule PASS.
  - Verdict on the trace-A value v (default 0.0282): INSIDE healthy noise if restore check and exchangeability hold AND v <= max(0.02, 2*Nbar); UNRESOLVED if restore check and exchangeability hold but v > max(0.02, 2*Nbar) (the probe window 201-250 is calmer than the trace-A window 101-150, so only a same-window measurement can settle it); OUTSIDE if the restore check or exchangeability fails.
  - Print a plain-words paragraph plus the numbers; write a JSON next to the input (REJUDGE-<job>.json).
Definitions: first_r1_c / first_r2_c = |R1 - C| / |R2 - C| at the first probe update; Dbar = mean(mean|R1-C|, mean|R2-C|); Nbar = mean|R1-R2|; ratio = Dbar/Nbar
(inf if Nbar == 0 and Dbar > 0; 1.0 if both are 0); registered max rule: n = max|R1-R2|, d = max(|R1-C|, |R2-C|), PASS if d <= max(0.10, 3n).

AMENDMENT 1 (PREREG-trace-a2.md, 2026-10-17 ~22:05 UTC, A1.1 and A1.3; the reading this tool applies; the text above stays as pre-registered):
  - P1 restore check: first_r1_c == first_r2_c == 0 exactly (unchanged).
  - P1b early window: early_max = max over the 2nd and 3rd probe updates (202-203) of max(|R1-C|, |R2-C|) <= 0.005.
  - OUTSIDE only if P1 or P1b fails, or if after the 4-resume calibration Dbar4 > L.
  - If P1, P1b and the registered max rule P2 pass, and P3 (Dbar <= max(0.02, 2*Nbar)) and ratio <= 2 hold: INSIDE healthy noise if v <= max(0.02, 2*Nbar), else UNRESOLVED (window).
  - If P1 and P1b pass but P2 or P3 / ratio fails: UNRESOLVED_CALIBRATE: run 2 more resumes of step-200 and judge Dbar against L = max(0.02, 2 x largest pairwise mean among the 4 resumes).
  - With --calibration PROBE2.json (R3, R4): L = max(0.02, 2 x the largest of the 6 pairwise mean |Ri-Rj| among R1..R4), Dbar4 = mean over the 4 resumes of mean|Ri-C|; OUTSIDE if Dbar4 > L, else INSIDE healthy noise if v <= L (v is the trace-A window value, L comes from the probe window 201-250), else UNRESOLVED (window).
  - Clarification (2026-10-18, after the code review; coordinator ruling): the 4-resume calibration resolves only the borderline UNRESOLVED_CALIBRATE case. It is never applied to a two-resume verdict of INSIDE, OUTSIDE or UNRESOLVED (window). An UNRESOLVED (window) still needs the same-window measurement of §4, so adding resumes cannot turn it into INSIDE.
  - Added here, not in the amendment text: with --calibration, P1 and P1b are also required of R3 and R4 (a failure is OUTSIDE), and the second file must have the same job, step, upto and C.

AMENDMENT 2 (PREREG-trace-a2.md, 2026-10-21 ~03:10 UTC, B1 "framing falsified: escalate"; coordinator ruling Oct 20; written before any probe number exists; DRAFT, like Amendment 1; the text below is copied from the PREREG as corrected by errata E1/E2 of 2026-10-21 (the erratum bracket itself is not copied), only the markdown bold removed and the minus sign and N-bar / D-bar written as - / Nbar / Dbar):
This outcome is an exit only. It moves no bar and changes no pass/fail threshold. Every other outcome of §4 and Amendment 1 stays as written.
Trigger (exact): P1 holds (update 201 exact for both resumes), P1b holds (updates 202-203 within the early limit), and the two resumes are bit-identical over the whole window (|R1-R2| = 0 at every update, so Nbar = 0 and n = 0), and they differ from the logged run (Dbar > 0).
- In that case further resumes of the same checkpoint repeat R1/R2 exactly, so the calibration of Amendment 1 cannot resolve anything. That is the loop found in the code review (REVIEW-VERDICT-2026-10-18, B1).
- This is PREREG §3 falsifier (c): fresh GPU processes do not differ, so the drift is not per-call rounding noise.
Outcome: ESCALATE (framing falsified). The run is neither passed nor failed and is not read. The registered P2 verdict is still recorded beside it, unchanged. The SYSTEMATIC diagnosis and this solve's noise framing are on record as contradicted. The question goes to Ben: what makes a resumed process differ from continuing, if not rounding noise? No calibration is asked for. Re-running the same probe is pointless, because it repeats.
Order: ESCALATE is decided after P1/P1b and before P2/P3/ratio. So a failing P1 or P1b is still OUTSIDE, and the Nbar = 0, Dbar = 0 case (restarts identical *and* equal to the run, a bit-exact card) stays judged by the existing rules: INSIDE, or UNRESOLVED (window) when the trace-A value is above max(0.02, 2·Nbar) = 0.02 (it is for the default 0.0282).
"""
import argparse, json, sys, time
from pathlib import Path

PREREG = (
    '  - Restore check: first_r1_c == first_r2_c == 0 exactly (else: "restore differs at the first update: wrong checkpoint or incomplete restore; investigate, do not read").\n'
    '  - Exchangeability: ratio = Dbar/Nbar <= 2.0 and registered max rule PASS.\n'
    '  - Verdict on the trace-A value v (default 0.0282): INSIDE healthy noise if restore check and exchangeability hold AND v <= max(0.02, 2*Nbar); UNRESOLVED if restore check and exchangeability hold but v > max(0.02, 2*Nbar) (the probe window 201-250 is calmer than the trace-A window 101-150, so only a same-window measurement can settle it); OUTSIDE if the restore check or exchangeability fails.\n'
    '  - Print a plain-words paragraph plus the numbers; write a JSON next to the input (REJUDGE-<job>.json).\n')
AMEND1 = (
    '  - P1 restore check: first_r1_c == first_r2_c == 0 exactly (unchanged).\n'
    '  - P1b early window: early_max = max over the 2nd and 3rd probe updates (202-203) of max(|R1-C|, |R2-C|) <= 0.005.\n'
    '  - OUTSIDE only if P1 or P1b fails, or if after the 4-resume calibration Dbar4 > L.\n'
    '  - If P1, P1b and the registered max rule P2 pass, and P3 (Dbar <= max(0.02, 2*Nbar)) and ratio <= 2 hold: INSIDE healthy noise if v <= max(0.02, 2*Nbar), else UNRESOLVED (window).\n'
    '  - If P1 and P1b pass but P2 or P3 / ratio fails: UNRESOLVED_CALIBRATE: run 2 more resumes of step-200 and judge Dbar against L = max(0.02, 2 x largest pairwise mean among the 4 resumes).\n'
    '  - With --calibration PROBE2.json (R3, R4): L = max(0.02, 2 x the largest of the 6 pairwise mean |Ri-Rj| among R1..R4), Dbar4 = mean over the 4 resumes of mean|Ri-C|; OUTSIDE if Dbar4 > L, else INSIDE healthy noise if v <= L (v is the trace-A window value, L comes from the probe window 201-250), else UNRESOLVED (window).\n'
    '  - Clarification (2026-10-18, after the code review; coordinator ruling): the 4-resume calibration resolves only the borderline UNRESOLVED_CALIBRATE case. It is never applied to a two-resume verdict of INSIDE, OUTSIDE or UNRESOLVED (window). An UNRESOLVED (window) still needs the same-window measurement of §4, so adding resumes cannot turn it into INSIDE.\n'
    '  - Added here, not in the amendment text: with --calibration, P1 and P1b are also required of R3 and R4 (a failure is OUTSIDE), and the second file must have the same job, step, upto and C.\n')
AMEND2 = (
    'This outcome is an exit only. It moves no bar and changes no pass/fail threshold. Every other outcome of §4 and Amendment 1 stays as written.\n'
    'Trigger (exact): P1 holds (update 201 exact for both resumes), P1b holds (updates 202-203 within the early limit), and the two resumes are bit-identical over the whole window (|R1-R2| = 0 at every update, so Nbar = 0 and n = 0), and they differ from the logged run (Dbar > 0).\n'
    '- In that case further resumes of the same checkpoint repeat R1/R2 exactly, so the calibration of Amendment 1 cannot resolve anything. That is the loop found in the code review (REVIEW-VERDICT-2026-10-18, B1).\n'
    '- This is PREREG §3 falsifier (c): fresh GPU processes do not differ, so the drift is not per-call rounding noise.\n'
    "Outcome: ESCALATE (framing falsified). The run is neither passed nor failed and is not read. The registered P2 verdict is still recorded beside it, unchanged. The SYSTEMATIC diagnosis and this solve's noise framing are on record as contradicted. The question goes to Ben: what makes a resumed process differ from continuing, if not rounding noise? No calibration is asked for. Re-running the same probe is pointless, because it repeats.\n"
    'Order: ESCALATE is decided after P1/P1b and before P2/P3/ratio. So a failing P1 or P1b is still OUTSIDE, and the Nbar = 0, Dbar = 0 case (restarts identical *and* equal to the run, a bit-exact card) stays judged by the existing rules: INSIDE, or UNRESOLVED (window) when the trace-A value is above max(0.02, 2·Nbar) = 0.02 (it is for the default 0.0282).\n')
AMEND2_HEAD = 'AMENDMENT 2 (PREREG-trace-a2.md, 2026-10-21 ~03:10 UTC, B1 "framing falsified: escalate"; coordinator ruling Oct 20; written before any probe number exists; DRAFT, like Amendment 1; the text below is copied from the PREREG as corrected by errata E1/E2 of 2026-10-21 (the erratum bracket itself is not copied), only the markdown bold removed and the minus sign and N-bar / D-bar written as - / Nbar / Dbar)'
RESTORE_MSG = 'restore differs at the first update: wrong checkpoint or incomplete restore; investigate, do not read'
EARLY_LIMIT = 0.005          # default for a probe JSON of the old format (no early_limit in it). A new probe records the supervisor's EARLY_LIMIT in the file and that value is used; tests keep this default equal to the supervisor's
FLOOR = 0.02
DEFAULT_V = 0.0282
EXIT = {'INSIDE healthy noise': 0, 'UNRESOLVED': 1, 'UNRESOLVED_CALIBRATE': 1, 'OUTSIDE': 2, 'ESCALATE': 4}


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def absdiff(a, b):
    return [abs(x - y) for x, y in zip(a, b)]


def early_of(ds):
    """largest value over the 2nd and 3rd update of the given |R - C| lists. (The one documented copy of the supervisor's early-window computation in resume_probe_verdict, kept so that this tool runs standalone on a probe JSON; a test checks the two agree on random inputs.)"""
    return max(d[i] for d in ds for i in (1, 2))


def calibration(C, Rs, v, early_limit=EARLY_LIMIT):
    """4 resumes Rs = [R1, R2, R3, R4] of one checkpoint over the window of C. -> dict (pure). OUTSIDE if P1 / P1b fails for any of them or Dbar4 > L; else INSIDE healthy noise if v <= L, else UNRESOLVED."""
    ds = [absdiff(R, C) for R in Rs]
    pairs = {f'R{i + 1}-R{j + 1}': mean(absdiff(Rs[i], Rs[j])) for i in range(4) for j in range(i + 1, 4)}
    L = max(FLOOR, 2 * max(pairs.values()))
    dbar4 = mean(mean(d) for d in ds)
    p1 = all(d[0] == 0 for d in ds)
    em = early_of(ds)
    p1b = em <= early_limit
    if not (p1 and p1b):
        verdict = 'OUTSIDE'
    elif dbar4 > L:
        verdict = 'OUTSIDE'
    else:
        verdict = 'INSIDE healthy noise' if v <= L else 'UNRESOLVED'
    return dict(verdict=verdict, pair_means=pairs, max_pair=max(pairs.values()), L=L, Dbar4=dbar4, mean_abs_ri_c=[mean(d) for d in ds], first_ri_c=[d[0] for d in ds], p1_all=p1,
                early_max4=em, p1b_all=p1b, trace_a_value=v)


def strict(x):
    """-> a copy of x that is STRICT JSON: no float is inf or nan (the JSON standard has no such tokens, and Python would write the non-standard `Infinity` / `NaN`). A non-finite float becomes null; in a dict the key gets a companion
    `<key>_nonfinite` = "inf" / "-inf" / "nan". `ratio` is the one that really occurs (every ESCALATE has ratio = inf): it always gets `ratio_infinite` (true / false) beside it, as well as the `ratio_nonfinite` companion when it is non-finite.
    The printed text is not affected (it may still say "inf")."""
    if isinstance(x, float):
        return None if x != x or x in (float('inf'), float('-inf')) else x
    if isinstance(x, (list, tuple)):
        return [strict(v) for v in x]
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            out[k] = strict(v)
            if isinstance(v, float) and out[k] is None:
                out[f'{k}_nonfinite'] = 'nan' if v != v else 'inf' if v > 0 else '-inf'
        if 'ratio' in x:
            out['ratio_infinite'] = x['ratio'] == float('inf')
        return out
    return x


def strict_json(r):
    """-> the text of REJUDGE-<job>.json: strict JSON (see strict), allow_nan=False so that any non-finite float that slipped past strict() fails loudly instead of writing `Infinity` / `NaN`."""
    return json.dumps(strict(r), indent=1, allow_nan=False)


def not_applied_note(verdict):
    """why a --calibration file is not applied to this two-resume verdict (anything but UNRESOLVED_CALIBRATE)."""
    if verdict == 'ESCALATE':
        return ('two-resume verdict is ESCALATE (framing falsified, PREREG Amendment 2); no calibration is asked for: the two restarts are bit-identical, so further restarts of the same checkpoint repeat them and cannot resolve anything. '
                'The calibration resolves only UNRESOLVED_CALIBRATE (PREREG Amendment 1 clarification)')
    kind = 'UNRESOLVED (window)' if verdict == 'UNRESOLVED' else verdict
    return f'two-resume verdict is {kind}; the calibration resolves only UNRESOLVED_CALIBRATE (PREREG Amendment 1 clarification)'


def rejudge(C, R1, R2, v=DEFAULT_V, R34=None, early_limit=EARLY_LIMIT):
    """-> dict with every number of the reading and `verdict` in ('INSIDE healthy noise', 'UNRESOLVED', 'UNRESOLVED_CALIBRATE', 'OUTSIDE', 'ESCALATE') (the AMENDED reading). Pure function.
    ESCALATE (Amendment 2 / B1): P1 and P1b hold, R1 == R2 at every update (n == 0, Nbar == 0) and Dbar > 0; decided after P1 / P1b and before P2 / P3 / ratio. Every other verdict is what it was before Amendment 2.
    R34 = (R3, R4), optional: the calibration (A1.3), same length as C. It is applied (the verdict becomes the calibration's) ONLY if the two-resume verdict is UNRESOLVED_CALIBRATE (PREREG Amendment 1 clarification);
    otherwise the two-resume verdict stays, `calibration` is None and `calibration_not_applied` says why. early_limit = the P1b bar (the probe JSON's own early_limit when it has one)."""
    if not (len(C) == len(R1) == len(R2) and C):
        raise ValueError('C, R1, R2 must have the same non-zero length')
    if len(C) < 3:
        raise ValueError('at least 3 probe updates are needed (the early window is the 2nd and 3rd)')
    d12, d1, d2 = absdiff(R1, R2), absdiff(R1, C), absdiff(R2, C)
    n, d = max(d12), max(d1 + d2)
    reg_limit = max(0.10, 3 * n)
    reg = 'PASS' if d <= reg_limit else 'FAIL'
    dbar, nbar = mean([mean(d1), mean(d2)]), mean(d12)
    ratio = (float('inf') if dbar > 0 else 1.0) if nbar == 0 else dbar / nbar
    restore_ok = d1[0] == 0 and d2[0] == 0                                               # P1
    em = early_of([d1, d2])
    early_ok = em <= early_limit                                                         # P1b
    limit = max(FLOOR, 2 * nbar)
    p3 = dbar <= limit
    exch_ok = ratio <= 2.0 and reg == 'PASS'                                             # the original reading's exchangeability (P2 and ratio)
    p23_ok = exch_ok and p3                                                              # P2 and ratio <= 2 (exch_ok) and P3
    identical = n == 0                                                                   # R1 == R2 at every update (so Nbar == 0 too)
    escalate = restore_ok and early_ok and identical and dbar > 0                        # Amendment 2 (B1): identical restarts that differ from the run
    if restore_ok and exch_ok:                                                           # the ORIGINAL reading, kept for the record only
        original = 'INSIDE healthy noise' if v <= limit else 'UNRESOLVED'
    else:
        original = 'OUTSIDE'
    if not (restore_ok and early_ok):
        verdict = 'OUTSIDE'
    elif escalate:                                                                       # decided after P1 / P1b, before P2 / P3 / ratio (Amendment 2); Nbar == 0 and Dbar == 0 is not this: it stays INSIDE / UNRESOLVED (window) below
        verdict = 'ESCALATE'
    elif p23_ok:
        verdict = 'INSIDE healthy noise' if v <= limit else 'UNRESOLVED'
    else:
        verdict = 'UNRESOLVED_CALIBRATE'
    out = dict(verdict=verdict, identical_resumes=identical, restore_ok=restore_ok, early_ok=early_ok, early_max=em, early_limit=early_limit, exchangeability_ok=exch_ok, p3_ok=p3, p23_ok=p23_ok,
               first_r1_c=d1[0], first_r2_c=d2[0], first_r1_r2=d12[0], Dbar=dbar, Nbar=nbar, ratio=ratio,
               n=n, d=d, registered_limit=reg_limit, registered_verdict=reg, trace_a_value=v, noise_limit=limit, n_updates=len(C), original_reading_verdict=original, calibration=None, calibration_not_applied=None)
    if R34 is not None:
        R3, R4 = R34
        if not (len(R3) == len(R4) == len(C)):
            raise ValueError('R3 and R4 must have the same length as C')
        if verdict == 'UNRESOLVED_CALIBRATE':
            cal = calibration(C, [R1, R2, R3, R4], v, early_limit)
            out.update(calibration=cal, verdict=cal['verdict'])
        else:                                                                            # the calibration resolves only the borderline case; every other two-resume verdict stands
            out['calibration_not_applied'] = not_applied_note(verdict)
    return out


def words(r, job):
    f = lambda x: f'{x:.4f}'
    v, lim = r['trace_a_value'], r['noise_limit']
    ex = (f'The two restarts differ from the real run by {f(r["Dbar"])} on average and from each other by {f(r["Nbar"])} on average (ratio {r["ratio"]:.2f}); '
          f'the registered rule (largest gap {f(r["d"])} against its limit {f(r["registered_limit"])}) says {r["registered_verdict"]}.')
    cal = r.get('calibration')
    if not r['restore_ok']:
        return (f'OUTSIDE. At the very first redone update the restarted run already differs from the real run (|R1-C| = {r["first_r1_c"]:.6f}, |R2-C| = {r["first_r2_c"]:.6f}; it must be exactly 0). '
                f'{RESTORE_MSG}. {ex}')
    if not r['early_ok']:
        return (f'OUTSIDE. The first redone update is exact, but at the 2nd or 3rd one the restarted run is already {r["early_max"]:.6f} away from the real run (limit {r["early_limit"]}). '
                'That early, rounding noise is still tiny; a gap this size points at state that did not come back with the checkpoint (optimizer moments, the learning-rate step), not at card noise. '
                f'{ex}')
    if r['verdict'] == 'ESCALATE':
        return (f'ESCALATE (framing falsified). The first redone update is exact and the early window is within {r["early_limit"]} (largest {r["early_max"]:.6f}), so the restore checks pass; but the two restarts are identical to each other at every update '
                f'(|R1-R2| = 0 throughout, so they carry no run-to-run noise at all) and both differ from the logged run (by {f(r["Dbar"])} on average). The restarts are identical but differ from the logged run, so the drift is not rounding noise: '
                'the noise framing / the SYSTEMATIC diagnosis is contradicted (PREREG falsifier (c)). This run is neither passed nor failed and is not read. No calibration is asked for: further restarts of the same checkpoint would repeat these two exactly, '
                'and re-running the probe repeats. Escalate to Ben: what makes a resumed process differ from continuing, if not rounding noise? '
                f'{ex}')
    if cal is not None:
        pm = ', '.join(f'{k} {f(x)}' for k, x in cal['pair_means'].items())
        base = (f'With four restarts of the same checkpoint, the six pairwise mean gaps are {pm}; the largest is {f(cal["max_pair"])}, so L = max(0.02, 2 x that) = {f(cal["L"])}. '
                f'The four restarts differ from the real run by {f(cal["Dbar4"])} on average (Dbar4). ')
        if not (cal['p1_all'] and cal['p1b_all']):
            return ('OUTSIDE. One of the extra restarts (R3, R4) fails the first-update or early-window check (first-update gaps ' + ', '.join(f'{x:.6f}' for x in cal['first_ri_c']) +
                    f'; early-window maximum {cal["early_max4"]:.6f}, limit {r["early_limit"]}): the restore is not reliably complete. {base}')
        if r['verdict'] == 'OUTSIDE':
            return f'OUTSIDE. Dbar4 {f(cal["Dbar4"])} is above L = {f(cal["L"])}: the restarts are farther from the real run than restarts are from each other, which is not just the card\'s noise. {base}'
        if r['verdict'].startswith('INSIDE'):
            return (f'INSIDE healthy noise. {base}Dbar4 is at most L, and the trace-A value {v:.4f} is at most L too. The trace-A resume difference is the size the card makes on its own. '
                    '(L was measured in the probe window 201-250.)')
        return (f'UNRESOLVED (window). {base}Dbar4 is at most L, so the restarts look like the real run, but the trace-A value {v:.4f} is above L = {f(cal["L"])}. '
                'L was measured in the probe window (updates 201-250), which is calmer than the trace-A window (101-150): only a measurement in the same window can settle it.')
    if r['verdict'] == 'UNRESOLVED_CALIBRATE':
        parts = []
        if r['registered_verdict'] != 'PASS':
            parts.append('the registered max rule failed')
        if not r['p3_ok']:
            parts.append(f'Dbar {f(r["Dbar"])} is above max(0.02, 2 x Nbar) = {f(lim)}')
        if r['ratio'] > 2.0:
            parts.append(f'the ratio {r["ratio"]:.2f} is above 2.0')
        return (f'UNRESOLVED_CALIBRATE. The first redone update is exact and the early window is within {r["early_limit"]} (largest {r["early_max"]:.6f}), so nothing says the restore is broken; but ' + '; '.join(parts) + '. '
                f'{ex} Two noise draws can look unlike each other by chance (the heavy tail the simulations predict), so this is "measure more", not "broken": run 2 more resumes of step-200 '
                'and judge Dbar against L = max(0.02, 2 x the largest pairwise mean among the 4 resumes) (rerun with --calibration PROBE2.json).')
    if r['verdict'].startswith('INSIDE'):
        return (f'INSIDE healthy noise. The first redone update is exact, the early window is within {r["early_limit"]}, a restart behaves like another restart of the same checkpoint (ratio {r["ratio"]:.2f}, at most 2.0), '
                f'and the trace-A value {v:.4f} is at most max(0.02, 2 x Nbar) = {f(lim)}. {ex} The trace-A resume difference is the size the card makes on its own.')
    return (f'UNRESOLVED (window). The first redone update is exact, the early window is within {r["early_limit"]} and a restart behaves like another restart (ratio {r["ratio"]:.2f}), but the trace-A value {v:.4f} is above max(0.02, 2 x Nbar) = {f(lim)}. '
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


def read_probe(path):
    """-> the probe dict, or raises ValueError / OSError / KeyError"""
    pr = json.loads(Path(path).read_text(encoding='utf-8'))
    if pr.get('why_fail') or not all(k in pr for k in ('C', 'R1', 'R2')):
        raise ValueError(f'the probe {path} did not judge ({pr.get("why_fail") or "no C / R1 / R2 in the file"})')
    return pr


def probe_early_limit(pr, path):
    """-> (the P1b bar, where it came from): the probe JSON's own early_limit when it has one (the supervisor's EARLY_LIMIT at the time), else this tool's default (a probe of the old format)."""
    if 'early_limit' not in pr:
        return EARLY_LIMIT, 'default (the probe has no early_limit: old format)'
    x = pr['early_limit']
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x < float('inf'):
        raise ValueError(f'{path}: early_limit {x!r} is not a non-negative number')
    return float(x), 'the probe json'


def check_calibration(p, pr, cpath, p2, early_limit):
    """the --calibration file must be a DIFFERENT pair of resumes of the same checkpoint: refuse (ValueError) the same file, the same content, a repeat of the probe's R1 / R2 (either order),
    another job / step / upto / C / early_limit. (load_calibration adds the calibration file's name to every message.)"""
    for k in ('job', 'step', 'upto'):
        if p2.get(k) != pr.get(k):
            raise ValueError(f'{k} is {p2.get(k)!r}, the probe has {pr.get(k)!r} (the same job, step and window are needed)')
    if p2['C'] != pr['C']:
        raise ValueError('its C (the run\'s logged losses) is not the probe\'s C')
    try:
        same_path = Path(cpath).resolve() == p.resolve() or Path(cpath).samefile(p)
    except OSError:
        same_path = False
    if same_path or Path(cpath).read_bytes() == p.read_bytes() or p2 == pr:
        raise ValueError(f'it is the same file (or the same content) as the probe {p}: a copy of the first probe would only echo it; run 2 NEW resumes (a new probe-resume) and use that file')
    if (p2['R1'], p2['R2']) in ((pr['R1'], pr['R2']), (pr['R2'], pr['R1'])):
        raise ValueError('its R1 and R2 equal the probe\'s R1 and R2 (same values, in the order given or swapped): these are not 2 new resumes')
    if 'early_limit' in p2 and probe_early_limit(p2, cpath)[0] != early_limit:
        raise ValueError(f'its early_limit {p2["early_limit"]!r} differs from the probe\'s {early_limit!r}')


class CalibrationError(Exception):
    """anything wrong with the --calibration file; main prints it with that file's name (not the first probe's) and exits 3."""


def number_list(x, n, what):
    if not isinstance(x, list) or len(x) != n or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in x):
        raise ValueError(f'{what} is not a list of {n} numbers (the length of the probe\'s C)')
    return x


def load_calibration(cpath, p, pr, early_limit):
    """-> (R3, R4) from the --calibration file. Every problem with that file (unreadable, not JSON, missing or mistyped fields, KeyError / TypeError included, not a different pair of resumes) is a CalibrationError."""
    try:
        p2 = read_probe(cpath)
        check_calibration(p, pr, cpath, p2, early_limit)
        n = len(pr['C'])
        return number_list(p2['R1'], n, 'its R1'), number_list(p2['R2'], n, 'its R2')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise CalibrationError(e if isinstance(e, ValueError) else repr(e)) from e


def aside(p):
    """rename an existing file to <name>.aside-<YYYYmmdd-HHMMSS> (the pack's convention, g2fa4_supervisor.aside; a second one within the same second gets -2, -3, ...); never overwrites, never deletes."""
    p = Path(p)
    if p.exists():
        st = time.strftime('%Y%m%d-%H%M%S')
        q, n = p.with_name(f'{p.name}.aside-{st}'), 1
        while q.exists():
            n += 1
            q = p.with_name(f'{p.name}.aside-{st}-{n}')
        p.replace(q)
        return q


def main(argv=None):
    ap = argparse.ArgumentParser(description='re-read a resume-noise probe with the pre-registered reading, as amended (Amendments 1 and 2)')
    ap.add_argument('probe', help='PROBE-RESUME-<job>.json')
    ap.add_argument('--trace-a-mean', type=float, help=f'trace A mean absolute resume difference v (default {DEFAULT_V})')
    ap.add_argument('--trace-a-json', help='TRACE-A-<job>.json or state.json: v = resume.mean_abs from it (--trace-a-mean wins)')
    ap.add_argument('--calibration', help='a second PROBE-RESUME-<job>.json of the same job / step / window (its resumes are R3, R4): judge Dbar4 against L = max(0.02, 2 x largest pairwise mean among R1..R4)')
    a = ap.parse_args(argv)
    p = Path(a.probe)
    try:
        pr = read_probe(p)
        job = pr['job']
        early_limit, el_from = probe_early_limit(pr, p)
        v, src = trace_a_value(a, job)
        r = rejudge(pr['C'], pr['R1'], pr['R2'], v, None, early_limit)                  # the two-resume verdict FIRST
        if a.calibration and r['verdict'] == 'UNRESOLVED_CALIBRATE':                    # only now is the --calibration file opened, read and validated: it is the one case in which it will be applied (a bad file cannot hide any other reading)
            R34 = load_calibration(a.calibration, p, pr, early_limit)
            r = rejudge(pr['C'], pr['R1'], pr['R2'], v, R34, early_limit)
        elif a.calibration:                                                            # INSIDE / UNRESOLVED (window) / OUTSIDE / ESCALATE: the file is not read at all
            r['calibration_not_applied'] = not_applied_note(r['verdict'])
    except CalibrationError as e:
        print(f'cannot use --calibration {a.calibration}: {e}')
        return 3
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f'cannot re-read {p}: {e if isinstance(e, ValueError) else repr(e)}')
        return 3
    r.update(job=job, source=str(p), calibration_offered=a.calibration, calibration_source=a.calibration if r['calibration'] is not None else None, early_limit_from=el_from, trace_a_value_from=src, step=pr.get('step'), upto=pr.get('upto'), preregistered_reading=PREREG, amendment_1_reading=AMEND1, amendment_2_reading=AMEND2, plain_words=words(r, job))
    note = r['calibration_not_applied']
    if note:
        r['plain_words'] += f' (The calibration file {a.calibration} was not applied: {note}.)'
    out = p.with_name(f'REJUDGE-{job}.json')
    text = strict_json(r)                                                              # strict JSON, built BEFORE anything is moved aside (a failure here must not leave the earlier reading renamed)
    kept = aside(out)                                                                  # an earlier reading is never overwritten
    out.write_text(text, encoding='utf-8')
    kind = {'UNRESOLVED': 'UNRESOLVED (window)', 'ESCALATE': 'ESCALATE (framing falsified)'}.get(r['verdict'], r['verdict'])
    print(f'REJUDGE {job}: {kind}\n')
    print('Pre-registered reading (original, verbatim):\n' + PREREG)
    print('Amendment 1 (the reading applied here, verbatim):\n' + AMEND1)
    print(AMEND2_HEAD + ':\n' + AMEND2)
    print(r['plain_words'] + '\n')
    if note:
        print(f'NOTE: --calibration {a.calibration} was NOT applied: {note}.\n')
    print(f'numbers ({r["n_updates"]} probe updates, {pr.get("step")}+1..{pr.get("upto")}):')
    print(f'  P1 first update: |R1-C| = {r["first_r1_c"]!r}, |R2-C| = {r["first_r2_c"]!r}, |R1-R2| = {r["first_r1_r2"]!r}  -> restore check {"holds" if r["restore_ok"] else "FAILS"}')
    print(f'  P1b early window (2nd and 3rd update): max |R-C| = {r["early_max"]:.6f}, limit {r["early_limit"]}  -> {"holds" if r["early_ok"] else "FAILS"}')
    print(f'  Dbar = {r["Dbar"]:.6f}, Nbar = {r["Nbar"]:.6f}, ratio = {r["ratio"]:.4f}; P2 registered rule: n = {r["n"]:.6f}, d = {r["d"]:.6f}, limit {r["registered_limit"]:.6f} -> {r["registered_verdict"]}; '
          f'P3 Dbar <= max(0.02, 2*Nbar) = {r["noise_limit"]:.6f}: {"holds" if r["p3_ok"] else "FAILS"}  -> P2, P3 and ratio <= 2 {"hold" if r["p23_ok"] else "do not all hold"}')
    print(f'  trace-A value v = {r["trace_a_value"]} (from {src})')
    cal = r['calibration']
    if cal:
        print(f'  calibration ({a.calibration}): pairwise means ' + ', '.join(f'{k} {x:.6f}' for k, x in cal['pair_means'].items()))
        print(f'    L = max(0.02, 2 x {cal["max_pair"]:.6f}) = {cal["L"]:.6f}; Dbar4 = {cal["Dbar4"]:.6f} (mean |Ri-C|: ' + ', '.join(f'{x:.6f}' for x in cal['mean_abs_ri_c']) +
              f'); first-update gaps all exact: {cal["p1_all"]}; early-window max over 4 = {cal["early_max4"]:.6f}')
    print(f'  (the ORIGINAL reading alone would say: {r["original_reading_verdict"]}; recorded for comparison only)')
    if kept:
        print(f'the earlier reading was moved aside: {kept}')
    print(f'written: {out}')
    return EXIT[r['verdict']]


if __name__ == '__main__':
    sys.exit(main())
