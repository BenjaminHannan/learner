"""Paired slip analysis: per-row harm files -> decision numbers (U-series pairing map; the L13/L14 'is 0.44 points real?' question).

  python3 -m domain.far.slip runs DIR [DIR ...] --step 4000 [--big] [--dev PATH] [--out JSON]
  python3 -m domain.far.slip contrast --x DIR... --y DIR... --metric drop|HO|S5|<cell> --step 4000 --sesoi 5 [--big] [--alpha 0.05]
  python3 -m domain.far.slip pair --parent-rows F --child-rows F [--dev PATH] [--out JSON]

No torch: this reads what learn_probe.py train and the m0 scorers already wrote.
  runs      per run folder, the cells of scores.jsonl at --step (HO, S5, ...) and the paired slip on the per-row harm file
            harm-rows-step{N}.json ({step, dev, dev_sha256, ids, family, parent_hits, child_hits}); --big reads
            harm-rows-big-step{N}.json instead (the 6,800-row DEV, 200 per family). --dev supplies the steps strata (any dev
            in_dist.jsonl; rows are matched by id; a row missing from it, a family differing from the rows file's, or a sha256 differing from the rows'
            dev_sha256 where --dev is not a superset of the rows, is an error, never a silent skip).
  contrast  the house paired form on two arms: runs are paired by the seed recorded in scores.jsonl; an unmatched, duplicated or
            missing seed is refused, never dropped. d_s = x_s - y_s per seed; metric 'drop' is the in_dist drop in points
            (positive = harm), any other name is a cell's pct (HO, S5, ...). A 'drop' contrast refuses unless every run's per-row
            file shares one dev_sha256, one ids list and one parent-hits list (same rows, same parent); a run with no per-row
            file is refused unless --allow-recorded, which uses the rounded scores.jsonl harm record, never mixed with per-row runs.
  pair      the same slip for an already-scored checkpoint pair: --parent-rows / --child-rows are JSON with ids, hits, family
            (and optionally steps), the format of score_dev.py's m0/*.in_dist.json.

Decisions encoded here (each is a place the arithmetic could quietly go wrong):
  * the slip is a PAIRED count: b = parent right and child wrong (lost), c = parent wrong and child right (gained). The drop in
    points is 100*(b-c)/n. Only the discordant rows carry information about the difference (the n rows whose two verdicts agree
    add none). Two standard errors, not to be swapped: item_se = 100*sqrt(b+c)/n is the SE UNDER THE NULL (b = c), the basis of
    the McNemar z = drop/item_se; it is NOT the SE of the drop. se_drop = 100*sqrt((b+c) - (b-c)**2/n)/n is the unrestricted
    paired SE, the one to use for an interval drop +- 1.96*se_drop (L12-LB: item_se 2.07 but se_drop 1.38; for a small slip
    they agree). McNemar exact two-sided p is the binomial test of b against c at one half. Both SEs are over ROWS (one
    checkpoint pair); they say nothing about run-to-run noise, which is what 'contrast' over paired seeds measures.
  * survival: among parent-right rows with k steps, the share the child still gets right. If slip were a per-step coin with a
    single survival p1 (read off the 1-step rows), k-step rows would survive p1**k; a k-step row surviving more than that means
    slip is not independent per step (it is concentrated on a few rows or items), less means it compounds.
  * Student t, not 1.96: the contrast usually has 3 to 8 seeds. t is the inverse of the exact t CDF (regularised incomplete
    beta, bisected), so it matches the tables to 3 decimals for every df; above df 200 the Cornish-Fisher series is used.
  * verdict (only with --sesoi): pass = mean_d >= sesoi and the whole interval above 0; equivalent = the whole interval inside
    (-sesoi, +sesoi); fail = the interval's top is below sesoi (it cannot reach the effect) and it is not equivalent; else open.
    n_needed = the smallest n >= 2 at which t_{n-1}*sd_d/sqrt(n) <= |mean_d| with the observed mean and sd held fixed, i.e. how
    many paired seeds it would take for the interval to exclude 0; None if the mean is 0 or there are fewer than 2 pairs.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from fractions import Fraction
from statistics import NormalDist


# ----------------------------------------------------------------------------------------------------------------- statistics

def mcnemar_exact_p(b, c):
    """Exact two-sided McNemar p: 2 * P(Binomial(b+c, 1/2) <= min(b, c)), capped at 1; 1.0 when there are no discordant rows."""
    n = b + c
    if n == 0:
        return 1.0
    m = min(b, c)
    tail = Fraction(sum(math.comb(n, k) for k in range(m + 1)), 2 ** n)
    return float(min(Fraction(1), 2 * tail))


def _betacf(a, b, x):
    """Continued fraction of the incomplete beta (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 10000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h


def betainc(a, b, x):
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1.0 - x) / b


def t_quantile(df, p=0.975):
    """Student t quantile: the t with P(T <= t) = p, for 0.5 < p < 1 (so p=0.975 is the two-sided 95% multiplier)."""
    assert df >= 1 and 0.5 < p < 1, (df, p)
    if df > 200:   # Cornish-Fisher in 1/df; error far below 1e-4 here
        z = NormalDist().inv_cdf(p)
        g = [(z ** 3 + z) / 4, (5 * z ** 5 + 16 * z ** 3 + 3 * z) / 96,
             (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / 384,
             (79 * z ** 9 + 776 * z ** 7 + 1482 * z ** 5 - 1920 * z ** 3 - 945 * z) / 92160]
        return z + sum(g[i] / df ** (i + 1) for i in range(4))
    tail = 2.0 * (1.0 - p)   # two-sided tail = I_x(df/2, 1/2) with x = df / (df + t^2), increasing in x
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if betainc(df / 2.0, 0.5, mid) > tail:
            hi = mid
        else:
            lo = mid
    x = 0.5 * (lo + hi)
    return math.sqrt(df * (1.0 - x) / x)


def paired_contrast(values_x, values_y, sesoi=None, alpha=0.05):
    """The house paired form: d_s = x_s - y_s per paired seed -> n, mean_d, sd_d (n-1), se, t, 95% (1-alpha) interval, verdict, n_needed."""
    assert len(values_x) == len(values_y), ('paired lists differ in length', len(values_x), len(values_y))
    d = [float(x) - float(y) for x, y in zip(values_x, values_y)]
    n = len(d)
    mean_d = sum(d) / n if n else 0.0
    sd_d = math.sqrt(sum((v - mean_d) ** 2 for v in d) / (n - 1)) if n > 1 else None
    out = dict(n=n, d=d, mean_d=mean_d, sd_d=sd_d, se=None, t=None, ci_low=None, ci_high=None, alpha=alpha, sesoi=sesoi,
               verdict=None, n_needed=None)
    if n < 2:
        return out
    se = sd_d / math.sqrt(n)
    t = t_quantile(n - 1, 1 - alpha / 2)
    lo, hi = mean_d - t * se, mean_d + t * se
    out.update(se=se, t=t, ci_low=lo, ci_high=hi)
    if sesoi is not None:
        if mean_d >= sesoi and lo > 0:
            out['verdict'] = 'pass'
        elif lo > -sesoi and hi < sesoi:
            out['verdict'] = 'equivalent'
        elif hi < sesoi:
            out['verdict'] = 'fail'
        else:
            out['verdict'] = 'open'
    if mean_d != 0:
        need = lambda k: t_quantile(k - 1, 1 - alpha / 2) * sd_d / math.sqrt(k) <= abs(mean_d)
        if need(2):
            out['n_needed'] = 2
        else:   # the left side falls with n; double until it fits, then bisect to the smallest n
            top = 4
            while not need(top) and top < 2 ** 40:
                top *= 2
            if need(top):
                lo_n, hi_n = top // 2, top
                while hi_n - lo_n > 1:
                    mid = (lo_n + hi_n) // 2
                    lo_n, hi_n = (lo_n, mid) if need(mid) else (mid, hi_n)
                out['n_needed'] = hi_n
    return out


# ----------------------------------------------------------------------------------------------------------------- slip

def _pct(k, n):
    return 100.0 * k / n if n else 0.0


def _count(parent, child):
    b = sum(1 for p, q in zip(parent, child) if p and not q)
    c = sum(1 for p, q in zip(parent, child) if q and not p)
    return b, c


def run_slip(parent_hits, child_hits, family, steps=None):
    """Paired slip of child against parent on the same rows -> dict (see the module docstring for b, c, item_se, z, p).
    steps: None, or one entry per row, each a list of steps (its length is the count) or an int."""
    assert len(parent_hits) == len(child_hits) == len(family), (len(parent_hits), len(child_hits), len(family))
    ph, ch = [int(bool(h)) for h in parent_hits], [int(bool(h)) for h in child_hits]
    n = len(ph)
    b, c = _count(ph, ch)
    drop = 100.0 * (b - c) / n if n else 0.0
    se = 100.0 * math.sqrt(b + c) / n if n else 0.0   # null SE (b = c): the McNemar z basis, not the SE of the drop
    se_drop = 100.0 * math.sqrt(max(0.0, (b + c) - (b - c) ** 2 / n)) / n if n else 0.0   # unrestricted paired SE of the drop
    res = dict(n=n, parent_pct=_pct(sum(ph), n), child_pct=_pct(sum(ch), n), drop=drop, b=b, c=c, item_se=se, se_drop=se_drop,
               z=drop / se if se else 0.0, mcnemar_p=mcnemar_exact_p(b, c))
    fams = {}
    for i, f in enumerate(family):
        fams.setdefault(f, []).append(i)
    res['families'] = {}
    for f in sorted(fams):
        ix = fams[f]
        fb, fc = _count([ph[i] for i in ix], [ch[i] for i in ix])
        res['families'][f] = dict(n=len(ix), parent=_pct(sum(ph[i] for i in ix), len(ix)), child=_pct(sum(ch[i] for i in ix), len(ix)),
                                  drop=100.0 * (fb - fc) / len(ix), b=fb, c=fc)
    if steps is not None:
        assert len(steps) == n, ('steps has one entry per row', len(steps), n)
        ks = [len(s) if isinstance(s, (list, tuple)) else int(s) for s in steps]
        by = {}
        for k in sorted(set(ks)):
            ix = [i for i in range(n) if ks[i] == k]
            kb, kc = _count([ph[i] for i in ix], [ch[i] for i in ix])
            right = sum(ph[i] for i in ix)
            by[k] = dict(n=len(ix), parent=_pct(right, len(ix)), child=_pct(sum(ch[i] for i in ix), len(ix)),
                         drop=100.0 * (kb - kc) / len(ix), b=kb, c=kc, parent_right=right,
                         child_right=sum(ch[i] for i in ix if ph[i]))
        res['by_steps'] = by
        p1 = by[1]['child_right'] / by[1]['parent_right'] if 1 in by and by[1]['parent_right'] else None
        res['p1'] = p1
        res['survival'] = {k: dict(parent_right=v['parent_right'], child_right=v['child_right'],
                                   observed=v['child_right'] / v['parent_right'] if v['parent_right'] else None,
                                   predicted=p1 ** k if p1 is not None else None) for k, v in by.items()}
    return res


# ----------------------------------------------------------------------------------------------------------------- files

def load_dev(path):
    """-> {id: (steps, family)} from a dev jsonl."""
    out = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                out[r['id']] = (r.get('steps'), r.get('family'))
    return out


def load_dev_steps(path):
    """-> {id: steps} from a dev jsonl."""
    return {i: v[0] for i, v in load_dev(path).items()}


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def subset_sha256(path, ids):
    """sha256 of b''.join(line + b'\\n') over the raw lines of the jsonl at `path` whose 'id' is in `ids`, taken in `ids` order (the
    construction of learn_probe.big_dev_provenance). An id missing from the file is not hashed: the check_dev id test has already refused it."""
    by_id = {}
    with open(path, 'rb') as f:
        for line in f.read().split(b'\n'):
            if line.strip():
                by_id[json.loads(line)['id']] = line
    return hashlib.sha256(b''.join(by_id[i] + b'\n' for i in ids)).hexdigest()


def check_dev(dev, dev_path, ids, family, want_sha=None, label=''):
    """Refuse a --dev file that is not the rows' DEV. Ids such as 'arith_bare-DI1-4' are positional, so a different build reuses them with
    different content: (1) every id must be in --dev with the family the rows file recorded; (2) when the rows file carries dev_sha256
    and --dev hashes differently, that is allowed only for a --dev that is a strict superset of the rows (the 1,360-row DEV is the
    per-family prefix of the 6,800-row big DEV) AND whose raw lines for the rows' ids, taken in the rows' order, hash to the rows'
    dev_sha256 (the same test as learn_probe.big_dev_provenance: matching ids and families alone would pass a rebuilt DEV that reuses the
    positional ids with other content); said on stderr. -> the {id: steps} map restricted to what was checked."""
    miss = [i for i in ids if i not in dev]
    if miss:
        raise SystemExit(f'{label}--dev lacks {len(miss)} of {len(ids)} rows, first {miss[:3]}')
    bad = [i for i, f in zip(ids, family) if dev[i][1] != f]
    if bad:
        raise SystemExit(f'{label}--dev family differs from the rows file for {len(bad)} of {len(ids)} ids, first {bad[:3]}: not the same DEV')
    if want_sha is not None:
        got = file_sha256(dev_path)
        if got != want_sha:
            if len(dev) <= len(ids):
                raise SystemExit(f'{label}--dev sha256 {got[:12]} != rows dev_sha256 {str(want_sha)[:12]} and it is not a superset of the rows: not the same DEV')
            sub = subset_sha256(dev_path, ids)
            if sub != want_sha:
                raise SystemExit(f'{label}--dev sha256 {got[:12]} != rows dev_sha256 {str(want_sha)[:12]} and its raw lines for the {len(ids)} rows\' ids, in the rows\' order, '
                                 f'hash to {sub[:12]}, not {str(want_sha)[:12]}: a superset in ids but not the same DEV rows')
            print(f'{label}note: --dev sha256 {got[:12]} != rows dev_sha256 {str(want_sha)[:12]}; accepted as a superset of the rows: its lines for the rows\' ids hash to the rows dev_sha256', file=sys.stderr)
    return {i: dev[i][0] for i in ids}


def steps_for(ids, dev_steps):
    miss = [i for i in ids if i not in dev_steps or dev_steps[i] is None]
    if miss:
        raise SystemExit(f'--dev lacks steps for {len(miss)} of {len(ids)} rows, first {miss[:3]}')
    return [dev_steps[i] for i in ids]


def align_pair(p, c):
    """Two per-row dicts (ids, hits, family, optional steps) -> (ids, parent_hits, child_hits, family, steps|None), matched by id."""
    if list(p['ids']) == list(c['ids']):
        pos = list(range(len(p['ids'])))
    else:
        if sorted(p['ids']) != sorted(c['ids']) or len(set(p['ids'])) != len(p['ids']):
            raise SystemExit(f'parent and child rows are not the same set of ids ({len(p["ids"])} vs {len(c["ids"])})')
        where = {i: k for k, i in enumerate(c['ids'])}
        pos = [where[i] for i in p['ids']]
    ids = list(p['ids'])
    steps = p.get('steps')
    return ids, [int(bool(h)) for h in p['hits']], [int(bool(c['hits'][k])) for k in pos], list(p['family']), steps


def read_json(path):
    with open(path) as f:
        return json.load(f)


def read_scores(run, step):
    """The last scores.jsonl record at `step` in a run folder."""
    path = os.path.join(run, 'scores.jsonl')
    if not os.path.exists(path):
        raise SystemExit(f'{run}: no scores.jsonl')
    recs = [json.loads(l) for l in open(path) if l.strip()]
    at = [r for r in recs if r.get('step') == step]
    if not at:
        raise SystemExit(f'{run}: no record at step {step}; steps present {sorted({r.get("step") for r in recs})}')
    return at[-1]


def rows_path(run, step, big):
    return os.path.join(run, f'harm-rows-{"big-" if big else ""}step{step}.json')


def run_slip_from_folder(run, step, big=False, dev=None, dev_path=None):
    """-> (scores record, slip dict | None, the harm-rows header). A missing per-row file is an error under --big, a note otherwise."""
    rec = read_scores(run, step)
    path = rows_path(run, step, big)
    if not os.path.exists(path):
        if big:
            raise SystemExit(f'{run}: {os.path.basename(path)} missing')
        return rec, None, None
    h = read_json(path)
    steps = steps_for(h['ids'], check_dev(dev, dev_path, h['ids'], h['family'], h.get('dev_sha256'), f'{run}: ')) if dev is not None else None
    return rec, run_slip(h['parent_hits'], h['child_hits'], h['family'], steps), {k: h.get(k) for k in ('step', 'dev', 'dev_sha256')}


# ----------------------------------------------------------------------------------------------------------------- printing

def fmt_slip(s, indent=''):
    lines = [f'{indent}n {s["n"]}  parent {s["parent_pct"]:.2f}  child {s["child_pct"]:.2f}  drop {s["drop"]:.2f}  b {s["b"]}  c {s["c"]}  '
             f'item_se(null) {s["item_se"]:.2f}  se_drop {s["se_drop"]:.2f}  z {s["z"]:.2f}  mcnemar_p {s["mcnemar_p"]:.4g}']
    lines.append(f'{indent}family                  n  parent  child   drop    b    c')
    for f, v in s['families'].items():
        lines.append(f'{indent}{f:<20} {v["n"]:>4} {v["parent"]:>7.2f} {v["child"]:>6.2f} {v["drop"]:>6.2f} {v["b"]:>4} {v["c"]:>4}')
    if 'by_steps' in s:
        lines.append(f'{indent}steps      n  parent  child   drop    b    c | parent_right child_right survival  single-p p1**k')
        for k, v in s['by_steps'].items():
            sv = s['survival'][k]
            o = f'{sv["observed"]:.3f}' if sv['observed'] is not None else '  -  '
            p = f'{sv["predicted"]:.3f}' if sv['predicted'] is not None else '  -  '
            lines.append(f'{indent}{k:<6} {v["n"]:>6} {v["parent"]:>7.2f} {v["child"]:>6.2f} {v["drop"]:>6.2f} {v["b"]:>4} {v["c"]:>4} | '
                         f'{v["parent_right"]:>12} {v["child_right"]:>11} {o:>8} {p:>13}')
    return '\n'.join(lines)


def fmt_contrast(metric, step, seeds, xs, ys, r):
    lines = [f'contrast metric {metric} at step {step}: x - y over {r["n"]} paired seeds',
             'seed        x        y        d'] + [f'{s:<8} {x:>8.2f} {y:>8.2f} {d:>8.2f}' for s, x, y, d in zip(seeds, xs, ys, r['d'])]
    if r['n'] < 2:
        return '\n'.join(lines + ['fewer than 2 pairs: no interval'])
    lines.append(f'mean_d {r["mean_d"]:.3f}  sd_d {r["sd_d"]:.3f}  se {r["se"]:.3f}  t(df {r["n"] - 1}, {1 - r["alpha"] / 2:g}) {r["t"]:.3f}  '
                 f'{100 * (1 - r["alpha"]):g}% interval [{r["ci_low"]:.3f}, {r["ci_high"]:.3f}]')
    lines.append(f'sesoi {r["sesoi"]}  verdict {r["verdict"]}  n_needed {r["n_needed"]}')
    return '\n'.join(lines)


# ----------------------------------------------------------------------------------------------------------------- CLI

def cmd_runs(a):
    dev = load_dev(a.dev) if a.dev else None
    out = {}
    for run in a.dirs:
        rec, slip, hdr = run_slip_from_folder(run, a.step, a.big, dev, a.dev)
        cells = {k: v['pct'] for k, v in rec.get('cells', {}).items()}
        print(f'== {run}  arm {rec.get("arm")}  seed {rec.get("seed")}  step {a.step}' + (f'  rows {hdr["dev"]} sha {str(hdr["dev_sha256"])[:12]}' if hdr else ''))
        print('cells: ' + ' '.join(f'{k} {v:.2f}' for k, v in cells.items()))
        harm = rec.get('harm_big') if a.big else rec.get('harm')   # --big: the 6,800-row DEV's record is 'harm_big', not 'harm'
        if harm:
            h = harm
            print(f'recorded harm{" (big DEV)" if a.big else ""}: in_dist {h.get("in_dist_a")} -> {h.get("in_dist_b")} (drop {h.get("in_dist_drop")}), n {h.get("n")}')
        if slip:
            print(fmt_slip(slip, '  '))
        else:
            print(f'  ({os.path.basename(rows_path(run, a.step, a.big))} not found: no per-row slip)')
        out[run] = dict(arm=rec.get('arm'), seed=rec.get('seed'), step=a.step, cells=cells, harm=harm, rows=hdr, slip=slip)
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)


def _digest(x):
    return hashlib.sha256(json.dumps(x).encode()).hexdigest()[:16]


def metric_value(run, step, metric, big, allow_recorded=False):
    """-> (seed, value, source) for one run folder. 'drop' is the in_dist drop in points from the per-row file; the source says what it was
    measured on (kind 'rows': dev_sha256 and hashes of the ids and of the parent hits; kind 'recorded': the 2-dp scores.jsonl harm
    record, only with allow_recorded, since it cannot be tied to a row set). Cells have source None."""
    rec = read_scores(run, step)
    if metric == 'drop':
        path = rows_path(run, step, big)
        if os.path.exists(path):
            h = read_json(path)
            src = dict(kind='rows', dev_sha256=h.get('dev_sha256'), n=len(h['ids']), ids=_digest(h['ids']), parent=_digest(h['parent_hits']))
            return rec.get('seed'), run_slip(h['parent_hits'], h['child_hits'], h['family'])['drop'], src
        if big:
            raise SystemExit(f'{run}: {os.path.basename(path)} missing')
        if not rec.get('harm'):
            raise SystemExit(f'{run}: no per-row file and no recorded harm at step {step}')
        if not allow_recorded:
            raise SystemExit(f'{run}: {os.path.basename(path)} missing; the recorded harm is rounded and not tied to a row set (--allow-recorded to use it)')
        hm = rec['harm']
        return rec.get('seed'), hm['in_dist_drop'], dict(kind='recorded', dev_sha256=hm.get('dev_sha256'), n=hm.get('n'))
    if metric not in rec.get('cells', {}):
        raise SystemExit(f'{run}: no cell {metric!r}; cells {sorted(rec.get("cells", {}))}')
    return rec.get('seed'), rec['cells'][metric]['pct'], None


def seed_map(runs, step, metric, big, label, allow_recorded=False):
    m = {}
    for run in runs:
        seed, v, src = metric_value(run, step, metric, big, allow_recorded)
        if seed is None:
            raise SystemExit(f'{run}: no recorded seed; cannot pair')
        if seed in m:
            raise SystemExit(f'{label}: seed {seed} appears twice ({m[seed][0]} and {run})')
        m[seed] = (run, v, src)
    return m


def check_same_rows(xm, ym):
    """A drop is comparable across runs only if every run measured it on the same DEV rows against the same parent: one kind of source, one
    dev_sha256, one ids hash, one parent-hits hash. Refuse otherwise, naming the first run that differs from the first run."""
    items = [(r, src) for m in (xm, ym) for r, _, src in m.values()]
    ref_run, ref = items[0]
    for r, src in items[1:]:
        if src != ref:
            raise SystemExit(f'drops are not on the same rows: {ref_run} {ref} vs {r} {src}')


def cmd_contrast(a):
    xm = seed_map(a.x, a.step, a.metric, a.big, 'x', a.allow_recorded)
    ym = seed_map(a.y, a.step, a.metric, a.big, 'y', a.allow_recorded)
    if set(xm) != set(ym):
        raise SystemExit(f'unmatched seeds: x only {sorted(set(xm) - set(ym))}, y only {sorted(set(ym) - set(xm))}')
    if a.metric == 'drop':
        check_same_rows(xm, ym)
    seeds = sorted(xm)
    xs, ys = [xm[s][1] for s in seeds], [ym[s][1] for s in seeds]
    r = paired_contrast(xs, ys, a.sesoi, a.alpha)
    print(fmt_contrast(a.metric, a.step, seeds, xs, ys, r))
    if a.out:
        json.dump(dict(metric=a.metric, step=a.step, seeds=seeds, x=xs, y=ys, x_runs=[xm[s][0] for s in seeds],
                       y_runs=[ym[s][0] for s in seeds], source=xm[seeds[0]][2], **r), open(a.out, 'w'), indent=1)


def cmd_pair(a):
    p, c = read_json(a.parent_rows), read_json(a.child_rows)
    ids, ph, ch, fam, steps = align_pair(p, c)
    ps, cs = p.get('dev_sha256'), c.get('dev_sha256')
    if ps and cs and ps != cs:   # align_pair matches ids only: two DEV builds reusing the positional ids would pair silently
        raise SystemExit('parent and child rows carry different dev_sha256: not the same DEV')
    if a.dev:
        steps = steps_for(ids, check_dev(load_dev(a.dev), a.dev, ids, fam, p.get('dev_sha256') or c.get('dev_sha256')))
    s = run_slip(ph, ch, fam, steps)
    print(f'== {a.child_rows} vs {a.parent_rows}')
    print(fmt_slip(s, '  '))
    if a.out:
        json.dump(s, open(a.out, 'w'), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Paired slip analysis of per-row harm files.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('runs', help='per-run cells and paired slip from run folders')
    r.add_argument('dirs', nargs='+')
    r.add_argument('--step', type=int, required=True)
    r.add_argument('--big', action='store_true', help='use harm-rows-big-step{N}.json (the 6,800-row DEV)')
    r.add_argument('--dev', default=None, help='dev in_dist.jsonl supplying the steps strata (match its row set to the rows file)')
    r.add_argument('--out', default=None)
    r.set_defaults(fn=cmd_runs)
    c = sub.add_parser('contrast', help='paired-by-seed contrast of two arms')
    c.add_argument('--x', nargs='+', required=True)
    c.add_argument('--y', nargs='+', required=True)
    c.add_argument('--metric', required=True, help="'drop', 'HO', 'S5' or any cell name")
    c.add_argument('--step', type=int, required=True)
    c.add_argument('--sesoi', type=float, default=None)
    c.add_argument('--alpha', type=float, default=0.05)
    c.add_argument('--big', action='store_true')
    c.add_argument('--allow-recorded', action='store_true', help="metric 'drop' only: use the rounded scores.jsonl harm record for a run with no per-row file (never mixed with per-row runs)")
    c.add_argument('--out', default=None)
    c.set_defaults(fn=cmd_contrast)
    q = sub.add_parser('pair', help='slip of a scored child against a scored parent (m0 per-row files)')
    q.add_argument('--parent-rows', required=True)
    q.add_argument('--child-rows', required=True)
    q.add_argument('--dev', default=None)
    q.add_argument('--out', default=None)
    q.set_defaults(fn=cmd_pair)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == '__main__':
    main()
