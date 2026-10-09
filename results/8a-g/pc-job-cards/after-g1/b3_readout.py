"""B3 group 1 readout: marks B3-1 to B3-6 (big-run PLAN.md sec. 5, sealed 12:10 PM ET 10-09) from one B3 3M run and its pair g2c3 (spec
design/8a-g-gemma-growth-2026-10-08.md addendum O). Read-only: it trains nothing and writes only --out.

  python b3_readout.py --b3 B3\\RESULT.json --pair PT\\RESULT.json [--ckpt B3\\checkpoint.pt --src SRC] [--long-dev FILE.jsonl] [--out FILE.json]

Everything but --ckpt is the standard library. --ckpt (with --src = the custom_io code folder the run used) adds the two numbers RESULT.json
does not hold: B3-4's long chains (8 to 16 steps) at the model's own stop vs the loops:32 lesion, and B3-5 on --long-dev (held-out rows up to
2,000 letters; the dev splits stop at 280 letters). Exit 0 = alive (B3-1 at least +1.0: seed 401 may run), 3 = dead (below +1.0), 2 = cannot tell.
"""
import argparse, json, os, sys

POOL = ['in_dist', 'answer', 'frame', 'vocab', 'variant']
BUCKETS = ['0-280', '281-700', '701-1300', '1301-2000']       # models/b3.py BUCKETS
HAIR = 0.5                                                      # Ben's hair rule on a screen (a miss of at most 0.5 point counts as met)


def g(d, *ks):
    for k in ks:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def p5(r, les=None):
    """pooled-5 = sum correct / sum n over the five pooled splits (analyze.P5)."""
    fe = g(r, 'final_eval') if les is None else g(r, 'lesions', les)
    try:
        return 100 * sum(fe[s]['correct'] for s in POOL) / sum(fe[s]['n'] for s in POOL)
    except (TypeError, KeyError, ZeroDivisionError):
        return None


def f(v, p=2):
    return 'n/a' if v is None else (f'{v:.{p}f}' if isinstance(v, float) else str(v))


def verdict(ok, wrong=False, hair=False):
    return 'n/a' if ok is None else ('PROVED WRONG' if wrong else 'pass' if ok else 'pass (hair)' if hair else 'MISS')


def load(path):
    try:
        return json.load(open(path))
    except Exception as e:
        print(f'B3 readout: cannot read {path}: {e}')
        return None


def train_cap_hits(stdout):
    """The last cap_hits event printed at the end of training (before the final evals), from stdout.txt."""
    last = None
    try:
        for line in open(stdout, errors='replace'):
            if line.startswith('{') and '"cap_hits"' in line and '"final"' not in line:
                try:
                    e = json.loads(line)
                    if e.get('event') == 'cap_hits':
                        last = e
                except ValueError:
                    pass
    except OSError:
        pass
    return last


def ckpt_part(res, ckpt, src, long_dev, device):
    """Loads the trained B3 under the run's own caps and evaluates (no training): rows of the big in_dist by gold program length at the model's
    own stop and at loops:32; --long-dev rows by input-length bucket at the model's own stop."""
    sys.path.insert(0, src)
    import contextlib
    import torch
    from custom_io.g8a import caps as CP
    cfg = res.get('config') or {}
    if cfg.get('caps'):
        CP.apply(json.load(open(cfg['caps'])))
    from custom_io.data import load_rows
    from custom_io.evalx import evaluate, is_hit, _dev_rows
    from custom_io.models import load_model, progparse as pp
    from custom_io.models.b3 import bucket
    dev = torch.device(device if device != 'auto' else ('cuda' if torch.cuda.is_available() else 'cpu'))
    amp = (lambda: torch.autocast(dev.type, dtype=torch.bfloat16)) if cfg.get('bf16') and dev.type == 'cuda' else contextlib.nullcontext
    m = load_model(ckpt, dev)
    out = dict(device=str(dev))

    def hits(rows, lesion=None):
        with amp():
            p = evaluate(m, rows, 64, dev, lesion, return_preds=True)['preds']
        return {r['id']: bool(is_hit(p[r['id']], r)) for r in rows}

    rows = _dev_rows(cfg.get('big_data') or cfg['data'], 'in_dist', None)
    L = {r['id']: len(pp.row_targets(r)['prog']) for r in rows}
    long_ = [r for r in rows if 8 <= L[r['id']] <= 16]
    out['program_len_counts'] = {str(k): sum(1 for v in L.values() if v == k) for k in sorted(set(L.values()))}
    if long_:
        own, les = hits(long_), hits(long_, 'loops:32')
        per = {}
        for r in long_:
            e = per.setdefault(str(L[r['id']]), [0, 0, 0])
            e[0] += 1
            e[1] += own[r['id']]
            e[2] += les[r['id']]
        out['long_chains'] = dict(n=len(long_), own=100 * sum(own.values()) / len(long_), loops32=100 * sum(les.values()) / len(long_),
                                  by_len={k: dict(n=v[0], own=100 * v[1] / v[0], loops32=100 * v[2] / v[0]) for k, v in sorted(per.items(), key=lambda x: int(x[0]))})
    if long_dev and os.path.exists(long_dev):
        mp = int(json.load(open(cfg['caps'])).get('max_prompt', 2000)) if cfg.get('caps') else 2000
        lrows = [r for r in load_rows(long_dev) if len(r['prompt']) <= mp]
        h = hits(lrows)
        bk = {}
        for r in lrows:
            e = bk.setdefault(bucket(len(r['prompt'])), [0, 0])
            e[0] += 1
            e[1] += h[r['id']]
        out['long_dev'] = dict(file=long_dev, n=len(lrows), by_length={k: dict(n=v[0], exact=100 * v[1] / v[0]) for k, v in sorted(bk.items())})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--b3', required=True, help="the B3 arm's RESULT.json")
    ap.add_argument('--pair', required=True, help="g2c3's PT RESULT.json (same seed, pool and caps)")
    ap.add_argument('--ckpt', help="the B3 arm's checkpoint.pt (adds B3-4's long chains and B3-5 on --long-dev)")
    ap.add_argument('--src', help='the custom_io code folder the run used (needed with --ckpt)')
    ap.add_argument('--long-dev', help='held-out rows up to 2,000 letters, dev row format (B3-5)')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    b3, pair = load(a.b3), load(a.pair)
    rep = dict(b3=a.b3, pair=a.pair, marks={}, notes=[])
    say = lambda s: print('B3 readout: ' + s, flush=True)
    if not b3 or b3.get('status') != 'ok' or not b3.get('final_eval'):
        say(f"the B3 run has no ok final eval (status {g(b3, 'status')}): cannot tell")
        if a.out:
            json.dump(rep, open(a.out, 'w'), indent=1)
        return 2
    jd, pd = os.path.dirname(os.path.dirname(os.path.abspath(a.b3))), os.path.dirname(os.path.dirname(os.path.abspath(a.pair)))
    box, pbox = load(os.path.join(jd, 'box.json')) or {}, load(os.path.join(pd, 'box.json')) or {}
    full = p5(b3)
    say(f"B3 3M seed {g(b3, 'config', 'seed')}: trained params {b3.get('n_params')}, {b3.get('steps')} updates, {f(b3.get('steps_per_s'), 3)} updates/s, "
        f"wall {f((b3.get('wall_s') or 0) / 3600)} h, peak {b3.get('peak_mem_mib')} MiB allocated / {b3.get('peak_reserved_mib')} reserved, accum {g(box, 'accum')}")

    # B3-1 beats its pair
    pp5 = p5(pair) if pair and pair.get('status') == 'ok' else None
    d = None if full is None or pp5 is None else full - pp5
    same_pool = (box.get('pool_train_sha256') == pbox.get('pool_train_sha256')) if box and pbox else None
    same_caps = (box.get('caps') == pbox.get('caps')) if box and pbox else None
    same_seed = g(b3, 'config', 'seed') == g(pair, 'config', 'seed') if pair else None
    m1 = dict(b3=full, pair=pp5, diff=d, same_pool=same_pool, same_caps=same_caps, same_seed=same_seed,
              ok=None if d is None else d >= 3.0, hair=d is not None and 3.0 - HAIR <= d < 3.0, dead=None if d is None else d < 1.0)
    rep['marks']['B3-1'] = m1
    say(f"B3-1 beats its pair: pooled-5 B3 {f(full)} - g2c3 {f(pp5)} = {f(d)} (pass >= +3.0; below +1.0 = no seed 401)  same pool {same_pool}, same caps {same_caps}, "
        f"same seed {same_seed}  -> {verdict(m1['ok'], m1['dead'], m1['hair'])}")

    # B3-2 thinker drives
    off = p5(b3, 'loops:0')
    ratio = None if off is None or not full else off / full
    c5 = g(b3, 'chain5', 'intact', 'exact')
    donor = g(b3, 'lesions', 'donor', 'in_dist', 'exact')
    oki = [ratio is not None and ratio <= 0.5, c5 is not None and c5 >= 99.0, donor is not None and donor <= 5.0]
    hair2 = c5 is not None and 99.0 - HAIR <= c5 < 99.0 and oki[0] and oki[2]
    m2 = dict(loops0=off, full=full, ratio=ratio, loops0_in_dist=g(b3, 'lesions', 'loops:0', 'in_dist', 'exact'), chain5=c5, donor_in_dist=donor,
              ok=None if None in (ratio, c5, donor) else all(oki), hair=hair2, wrong=ratio is not None and ratio > 0.6)
    rep['marks']['B3-2'] = m2
    say(f"B3-2 thinker drives: thinker-off (loops:0) pooled-5 {f(off)} = {f(None if ratio is None else 100 * ratio, 1)}% of full (pass <= 50%, wrong > 60%); "
        f"loops:0 in_dist {f(m2['loops0_in_dist'])}; chain-5 {f(c5)} (>= 99); donor in_dist {f(donor)} (<= 5)  -> {verdict(m2['ok'], m2['wrong'], m2['hair'])}")

    # B3-3 the tool is used
    nx, nxi = g(b3, 'extra', 'noexec', 'program_families'), g(b3, 'extra', 'noexec', 'intact')
    m3 = dict(calc_off=nx, intact=nxi, n=g(b3, 'extra', 'noexec', 'n'), ok=None if nx is None else nx < 5.0, hair=nx is not None and 5.0 <= nx < 5.0 + HAIR,
              wrong=None not in (nx, nxi) and nxi - nx < 10.0)
    rep['marks']['B3-3'] = m3
    say(f"B3-3 tool used: calculator off (noexec), program questions {f(nx)}% (pass < 5) vs intact {f(nxi)}% on the same {m3['n']} rows "
        f"(wrong if within 10)  -> {verdict(m3['ok'], m3['wrong'], m3['hair'])}")

    # B3-4 learned stop (H1 marks, addendum 21 and amendment 2, plus the 2d shape)
    h1 = g(b3, 'extra', 'h1') or {}
    l32 = p5(b3, 'loops:32')
    ha = None if None in (l32, full) else l32 - full
    hc = h1.get('hc_gap')
    hd_cap, hd_med = g(h1, 'pooled5', 'at_cap'), g(h1, 'pooled5', 'median')
    he0 = g(b3, 'lesions', 'loops:0', 'in_dist', 'exact')
    bpl = h1.get('by_program_len') or {}
    lens = sorted((int(k) for k in bpl if g(bpl, k, 'n')), key=int)
    top = 12 if 12 in lens else (max(lens) if lens else None)
    r1, rtop = g(bpl, '1', 'mean'), (g(bpl, str(top), 'mean') if top else None)
    fam_means = {k: v.get('mean') for k, v in (h1.get('by_family') or {}).items() if v.get('n')}
    never_early = bool(fam_means) and all(v is not None and v >= 0.9 * 32 for v in fam_means.values())      # the sealed cap of 32, whatever the run's own cap
    m4 = dict(Ha=ha, Hc=hc, Hd_at_cap=hd_cap, Hd_median=hd_med, He_loops0_in_dist=he0, He_donor_in_dist=donor,
              Hf=dict(cap=h1.get('cap'), p_stop=h1.get('p_stop'), label=h1.get('label')),
              rounds_by_len={str(k): g(bpl, str(k), 'mean') for k in lens}, rounds_1step=r1, rounds_longest=rtop, longest_len=top,
              shape_ok=None if None in (r1, rtop) else r1 <= 0.5 * rtop, never_stops_early=never_early, long_chains=None)
    parts = [ha is not None and ha >= -0.3, hc is not None and hc >= 2.0, None not in (hd_cap, hd_med) and hd_cap <= 1.0 and hd_med < 16,
             None not in (he0, donor) and he0 <= 5.0 and donor <= 5.0,
             (h1.get('cap'), h1.get('p_stop'), h1.get('label')) == (32, 0.5, 'settled'), bool(m4['shape_ok'])]
    say(f"B3-4 learned stop: H-a loops:32 minus own stop {f(ha)} (>= -0.3; wrong < -1.0); H-b is B3-1 here (no T1 on this pool); "
        f"H-c chain-5 minus one-step rounds {f(hc)} (>= 2.0); H-d at cap {f(hd_cap)}% (<= 1) median {f(hd_med)} (< 16); "
        f"H-e loops:0 in_dist {f(he0)} donor {f(donor)} (<= 5 each, flat: T1SDR is not on this pool); H-f cap/p_stop/label {m4['Hf']}")
    say(f"B3-4 shape: mean rounds by gold program length {', '.join(f'{k}: {f(v, 1)}' for k, v in m4['rounds_by_len'].items())}; "
        f"1-step {f(r1, 1)} vs {top}-step {f(rtop, 1)} (pass if at most half{'' if top == 12 else '; no 12-step rows under these caps, the longest is used'}); "
        f"every family within 10% of the cap: {never_early} (wrong if True)")
    wrong4 = (ha is not None and ha < -1.0) or never_early
    m4['parts_ok'] = parts
    m4['wrong'] = wrong4
    rep['marks']['B3-4'] = m4

    # B3-5 reads long input
    bl = {}
    for sp in POOL:
        for k, v in (g(b3, 'extra', 'b3', 'splits', sp, 'by_length') or {}).items():
            e = bl.setdefault(k, [0, 0.0])
            e[0] += v['n']
            e[1] += v['n'] * v['exact'] / 100
    dev_b = {k: dict(n=n, exact=100 * c / n) for k, (n, c) in bl.items() if n}
    rep['dev_by_length'] = dev_b
    say('B3-5 dev splits by input length (pooled-5 rows): ' + ', '.join(f"{k} letters {f(v['exact'], 1)} (n {v['n']})" for k, v in sorted(dev_b.items(), key=lambda x: BUCKETS.index(x[0]) if x[0] in BUCKETS else 9)))

    # B3-6 no cut answers
    rep_caps = load(os.path.join(jd, 'caps_report.json')) or {}
    roc = rep_caps.get('rows_over_caps') or {}
    rocd = rep_caps.get('rows_over_caps_dev_with_programs') or {}
    tr = train_cap_hits(os.path.join(os.path.dirname(os.path.abspath(a.b3)), 'stdout.txt'))
    fin = b3.get('cap_hits') or {}
    # steps_unparsed (rows with worked steps progparse cannot read train answer-only) is reported, not gated: Ben chose "Run, disclosed", 1:32 PM ET 10-09
    names = [k for k in fin if k not in ('total', 'number_clipped', 'steps_unparsed')]
    unp = dict(training=tr.get('steps_unparsed') if tr else None, after_evals=fin.get('steps_unparsed'))
    over = {k: v for k, v in list(roc.items()) + [('dev ' + k, v) for k, v in rocd.items()] if v}
    over.update({f'training {k}': tr.get(k) for k in names if tr and tr.get(k)})
    over.update({f'after evals {k}': fin.get(k) for k in names if fin.get(k)})
    m6 = dict(rows_over_caps=roc, rows_over_caps_dev=rocd, training=tr, after_evals=fin, number_clipped=fin.get('number_clipped'), steps_unparsed=unp, over=over,
              ok=None if not roc and not fin else not over, wrong=bool(roc and any(roc.values())) or bool(tr and any(tr.get(k) for k in names)))
    rep['marks']['B3-6'] = m6
    say(f"B3-6 cap counters: rows_over_caps {roc or 'n/a'}; training {({k: tr.get(k) for k in names} if tr else 'n/a')}; after evals {({k: fin.get(k) for k in names} or 'n/a')}; "
        f"number_clipped {fin.get('number_clipped')}, steps_unparsed training {unp['training']} / after evals {unp['after_evals']} (both reported)  -> {verdict(m6['ok'], m6['wrong'])}{'  nonzero: ' + json.dumps(over) if over else ''}")

    # the part that needs the checkpoint
    ck = None
    if a.ckpt and a.src and os.path.exists(a.ckpt):
        try:
            ck = ckpt_part(b3, a.ckpt, a.src, a.long_dev, a.device)
        except Exception as e:
            say(f'checkpoint part failed: {type(e).__name__}: {e}')
    rep['ckpt'] = ck
    lc = g(ck, 'long_chains')
    if lc:
        m4['long_chains'] = lc
        lc_ok, lc_wrong = lc['own'] >= lc['loops32'] - 2.0, lc['own'] < lc['loops32'] - 5.0
        parts.append(lc_ok)
        wrong4 = wrong4 or lc_wrong
        say(f"B3-4 long chains (8-16 steps, n {lc['n']}): own stop {f(lc['own'])} vs loops:32 {f(lc['loops32'])} (pass within 2; wrong if more than 5 below); by length "
            + ', '.join(f"{k}: {f(v['own'], 1)}/{f(v['loops32'], 1)} (n {v['n']})" for k, v in lc['by_len'].items()))
    else:
        parts.append(None)
        say('B3-4 long chains: n/a (' + ('no rows of 8-16 steps in the big in_dist; program lengths ' + json.dumps(g(ck, 'program_len_counts')) if ck else 'checkpoint part not run') + ')')
    m4['wrong'] = wrong4
    m4['ok'] = None if None in parts else all(parts)
    say(f"B3-4 -> {verdict(m4['ok'], wrong4)}  (parts H-a, H-c, H-d, H-e, H-f, shape, long chains: {parts})")

    lb = g(ck, 'long_dev', 'by_length') or {k: v for k, v in dev_b.items()}
    src5 = 'held-out long rows (--long-dev)' if g(ck, 'long_dev') else 'dev splits'
    short = g(lb, '0-280', 'exact')
    others = {k: v['exact'] for k, v in lb.items() if k != '0-280' and v['n']}
    if short is None or not others:
        m5 = dict(source=src5, by_length=lb, ok=None, wrong=False,
                  note='no rows above 280 letters' + ('' if g(ck, 'long_dev') else ' in the dev splits and no --long-dev file') + ': B3-5 cannot be read')
        say(f"B3-5 reads long input: n/a ({m5['note']})")
    else:
        worst = min(others.values())
        lw = others.get('1301-2000')
        m5 = dict(source=src5, by_length=lb, short=short, worst=worst, ok=worst >= short - 10.0, hair=short - 10.0 - HAIR <= worst < short - 10.0,
                  wrong=lw is not None and lw < short - 20.0)
        say(f"B3-5 reads long input ({src5}): " + ', '.join(f"{k} {f(v['exact'], 1)} (n {v['n']})" for k, v in sorted(lb.items(), key=lambda x: BUCKETS.index(x[0]) if x[0] in BUCKETS else 9))
            + f"; worst long bucket {f(worst, 1)} vs short {f(short, 1)} (pass within 10; wrong if 1,301-2,000 is more than 20 under)  -> {verdict(m5['ok'], m5['wrong'], m5['hair'])}")
    rep['marks']['B3-5'] = m5

    alive = None if d is None else d >= 1.0
    rep['alive'] = alive
    say('summary: ' + '  '.join(f"{k} {verdict(v.get('ok'), v.get('wrong') or v.get('dead'), v.get('hair'))}" for k, v in sorted(rep['marks'].items()))
        + f"  -> seed 401 {'MAY RUN (B3-1 at least +1.0)' if alive else 'does NOT run (B3-1 below +1.0)' if alive is False else ': cannot tell'}")
    if a.out:
        json.dump(rep, open(a.out, 'w'), indent=1, default=str)
    return 2 if alive is None else (0 if alive else 3)


if __name__ == '__main__':
    sys.exit(main())
