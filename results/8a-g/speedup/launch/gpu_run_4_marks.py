"""gpu_run_4_marks.py: the readout of GPU-RUN-4 against PREREG-launch-defer.md (as amended per the gate ruling). Pure: it reads the box outputs and computes every mark, prediction
and the section-5 outcome; it decides nothing the sheet does not say.

  python gpu_run_4_marks.py --box1 DIR [--box2 DIR] [--box1-machine ID] [--box2-machine ID] [--box1-image IMG] [--box2-image IMG] [--box1-dph X] [--box2-dph X] --out OUT.json --md OUT.md

DIR = a box's profrun folder (gr4_*.json, hostmon.csv, gr4_host.txt, *.launch.json). Box 1 = GR4_PART=full, box 2 = GR4_PART=rep. Missing files give 'missing' / 'undecided', never a guess.
"""
import argparse, csv, glob, json, math, os, statistics as st

BAR_LOSS_REL, BAR_GRAD_COS = 1e-4, 0.9999           # mark 2 bf16 bar (prof_train AB_EQ_LOSS_REL / AB_EQ_GRAD_COS)
WIN_DROP, MEM_GB, NEED_ROUNDS = 0.95, 10.0, 3        # mark 1
REF_X, CHUNK_LO, CHUNK_HI = 1.10, 0.95, 1.05         # mark 3 (a), (b)
STEAL_MAX, MHZ_FRAC, OK_THROTTLE = 2.0, 0.90, {0x0, 0x1}   # mark 3 (c), (d), (e)
AA_MAX = 0.01                                        # mark 5
SYNC_MAX, DTOH_MAX, KERN_FRAC = 300, 150, 0.65       # mark 7
P1_X, KILL_X, KERN_EXTRA, P3_LO, P3_HI, P5_GB, P6_DEAD = 1.25, 1.10, 1.10, 1.00, 1.10, 0.5, 0.90


def load(d, name):
    p = os.path.join(d, name)
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return None


def section(js, name):
    return ((js or {}).get('sections') or {}).get(name)


def hostmon(d):
    rows = []
    try:
        for r in csv.DictReader(open(os.path.join(d, 'hostmon.csv'))):
            rows.append(r)
    except OSError:
        return None
    return rows


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def throttle(x):
    try:
        return int(str(x), 16) if str(x).lower().startswith('0x') else int(x)
    except (TypeError, ValueError):
        return None


# ---- runs and setups -------------------------------------------------------------------------------------------------------------------------------------
ARMS = dict(d4=('gr4_bench_d4.json', 'defer', 'base4', 'defer4', False), aa=('gr4_bench_aa.json', 'same', 'base4', 'base4', False),
            k4=('gr4_bench_k4.json', 'kvcat', 'defer4', 'kvdefer4', True), d8=('gr4_bench_d8.json', 'defer', 'base8', 'defer8', True))


def runs_of(box):
    """-> {arm: dict(a=[runs], b=[runs], arm_record)} with each run tagged with its setup (mark 3(a) groups)."""
    out = {}
    for key, (fn, armname, sa, sb, secondary) in ARMS.items():
        ab = section(load(box, fn), 'abbench')
        rec = (ab or {}).get('arms', {}).get(armname)
        if not rec:
            out[key] = dict(missing=True, file=fn)
            continue
        a = [dict(r, setup=sa, arm=key, who='A', i=i) for i, r in enumerate(rec.get('a_runs', []))]
        b = [dict(r, setup=sb, arm=key, who='B', i=i) for i, r in enumerate(rec.get('b_runs', []))]
        out[key] = dict(a=a, b=b, record=rec, secondary=secondary, error=rec.get('error'), skipped=rec.get('skipped'))
    return out


def references(arms):
    """Mark 3(a), condition 2: baseline accum 4 = fastest A round of D4 or AA; defer accum 4 = fastest of D4's B rounds and K4's A rounds; K4's B and D8's setups = fastest within their own arm."""
    def vals(*pairs):
        v = []
        for arm, who in pairs:
            x = arms.get(arm) or {}
            v += [r['round_median'] for r in x.get(who, []) if r.get('round_median')]
        return min(v) if v else None
    return dict(base4=vals(('d4', 'a'), ('aa', 'a')), defer4=vals(('d4', 'b'), ('k4', 'a')), kvdefer4=vals(('k4', 'b')), base8=vals(('d8', 'a')), defer8=vals(('d8', 'b')))


def chunk_medians(arms):
    """Mark 3(b): per setup, the median of each same-numbered chunk over every run of that setup on the box (AA's B runs the baseline code: it is in setup base4)."""
    g = {}
    for x in arms.values():
        for r in x.get('a', []) + x.get('b', []):
            if r.get('chunk_values'):
                g.setdefault(r['setup'], []).append(r['chunk_values'])
    return {s: [st.median(c[i] for c in cs if len(c) > i) for i in range(max(len(c) for c in cs))] for s, cs in g.items()}


def samples_in(hm, t0, t1):
    return [r for r in (hm or []) if t0 is not None and t1 is not None and t0 <= num(r.get('epoch')) <= t1 + 10]


def normal(run, refs, cmed, hm, mhz_med, mhz_struck):
    """Mark 3 (a)-(e) for one run -> (ok, reasons)."""
    why = []
    rv, ref = run.get('round_median'), refs.get(run['setup'])
    if not rv or ref is None:
        return False, ['no round value' if not rv else 'no reference']
    if rv > REF_X * ref:
        why.append(f'(a) {rv:.4f} > {REF_X} x ref {ref:.4f}')
    cm = cmed.get(run['setup']) or []
    for i, c in enumerate(run.get('chunk_values') or []):
        if i < len(cm) and cm[i] and not (CHUNK_LO <= c / cm[i] <= CHUNK_HI):
            why.append(f'(b) chunk {i + 1} {c:.4f} / median {cm[i]:.4f} = {c / cm[i]:.3f}')
    t0, t1 = run.get('t_timed_start'), run.get('t_timed_end')
    if t0 is None:
        why.append('no timed window (run record has no clock times)')
    sm = samples_in(hm, t0, t1)
    if hm is not None and t0 is not None and not sm:
        why.append('no host-monitor sample in the timed window')
    for r in sm:
        th = throttle(r.get('throttle_active'))
        if r.get('throttle_active') not in (None, 'NA') and th not in OK_THROTTLE:
            why.append(f'(c) throttle {r.get("throttle_active")} at {r.get("utc")}')
        s = num(r.get('cpu_steal_pct'))
        if s is not None and s >= STEAL_MAX:
            why.append(f'(d) steal {s} at {r.get("utc")}')
        m = num(r.get('trainer_cpu_mhz'))
        if not mhz_struck and m is not None and mhz_med and m < MHZ_FRAC * mhz_med:
            why.append(f'(e) trainer core {m:.0f} MHz < {MHZ_FRAC} x {mhz_med:.0f}')
    return (not why), why


def arm_result(key, x, refs, cmed, hm, mhz_med, mhz_struck, mark2_ok):
    if x.get('missing'):
        return dict(arm=key, status='missing', file=x['file'])
    a, b = x['a'], x['b']
    seqs = [tuple(r.get('rounds_seq') or ()) for r in a + b]
    ref_seq = max(set(seqs), key=seqs.count) if seqs else ()
    rounds = []
    for i in range(min(len(a), len(b))):
        na, wa = normal(a[i], refs, cmed, hm, mhz_med, mhz_struck)
        nb, wb = normal(b[i], refs, cmed, hm, mhz_med, mhz_struck)
        m4 = bool(a[i].get('rounds_seq')) and tuple(a[i]['rounds_seq']) == ref_seq and tuple(b[i].get('rounds_seq') or ()) == ref_seq
        rounds.append(dict(round=i + 1, a=a[i].get('round_median'), b=b[i].get('round_median'), a_normal=na, b_normal=nb, a_why=wa, b_why=wb, mark4=m4, read=na and nb and m4,
                           a_window=[a[i].get('timed_start_utc'), a[i].get('timed_end_utc')], b_window=[b[i].get('timed_start_utc'), b[i].get('timed_end_utc')]))
    rd = [r for r in rounds if r['read']]
    res = dict(arm=key, secondary=x['secondary'], rounds=rounds, read_rounds=len(rd), error=x.get('error'), skipped=x.get('skipped'),
               peak_b_gb=max([r['peak_mem']['allocated_gb'] for r in b if (r.get('peak_mem') or {}).get('allocated_gb') is not None] or [None], key=lambda v: -1 if v is None else v),
               peak_a_gb=max([r['peak_mem']['allocated_gb'] for r in a if (r.get('peak_mem') or {}).get('allocated_gb') is not None] or [None], key=lambda v: -1 if v is None else v))
    if len(rd) < NEED_ROUNDS:
        res.update(status='regime-confounded' if rounds else 'no rounds', decided=False)
        return res
    ma, mb = st.median(r['a'] for r in rd), st.median(r['b'] for r in rd)
    res.update(a_median=ma, b_median=mb, speed=ma / mb, b_over_a=mb / ma, all_b_below=all(r['b'] < r['a'] for r in rd), decided=True)
    res['mark1'] = bool(res['all_b_below'] and mb <= WIN_DROP * ma and (res['peak_b_gb'] is not None and res['peak_b_gb'] <= MEM_GB) and mark2_ok)
    res['status'] = 'decided'
    return res


# ---- the per-box readout ---------------------------------------------------------------------------------------------------------------------------------
def mark2(box1):
    eq, det, e4 = section(load(box1, 'gr4_abequiv.json'), 'abequiv'), section(load(box1, 'gr4_abequiv_det.json'), 'abequiv'), section(load(box1, 'gr4_e4.json'), 'equiv')
    out = {}
    v = ((eq or {}).get('variants') or {}).get('defer') or {}
    bf = v.get('bf16') or v.get('fp32') or {}
    bar = None if not bf else bool(bf.get('rel_loss_diff', 1) <= BAR_LOSS_REL and bf.get('grad_cos', 0) >= BAR_GRAD_COS)
    curve = (((e4 or {}).get('specs') or {}).get('defer') or {}).get('curve') or {}
    E4 = curve.get('E4') or {}
    e4ok = None if not E4 else (bool(E4.get('passed')) if E4.get('registered_window') else None)
    out['defer'] = dict(bar=bar, bar_precision='bf16' if v.get('bf16') else ('fp32' if v.get('fp32') else None), rel_loss_diff=bf.get('rel_loss_diff'), grad_cos=bf.get('grad_cos'),
                        E4=dict(passed=E4.get('passed'), registered_window=E4.get('registered_window'), mean_abs_diff=E4.get('mean_abs_diff'), diff_of_means=E4.get('diff_of_means'), updates=curve.get('updates')),
                        holds=(bar and e4ok) if (bar is not None and e4ok is not None) else (False if (bar is False or e4ok is False) else None), label='numerics-changing')
    kd = ((det or {}).get('variants') or {}).get('kvcat') or {}
    prec = 'bf16' if kd.get('bf16') else 'fp32'
    rr = (((det or {}).get('reference') or {}).get(prec) or {}).get('rerun') or {}
    kv = kd.get(prec) or {}
    if not kv:
        kres = dict(holds=None, how='missing')
    elif rr.get('bit_exact'):
        kres = dict(holds=bool(kv.get('bit_exact')), how=f'baseline rerun bitwise in {prec}: kvcat must be bitwise', kvcat_bit_exact=kv.get('bit_exact'))
    elif kv.get('rel_loss_diff', 1) <= rr.get('rel_loss_diff', -1) and kv.get('grad_rel_l2', 1) <= rr.get('grad_rel_l2', -1):
        kres = dict(holds=True, how=f'within the baseline rerun ({prec}): loss rel {kv.get("rel_loss_diff")} <= {rr.get("rel_loss_diff")}, grad relL2 {kv.get("grad_rel_l2")} <= {rr.get("grad_rel_l2")}')
    else:
        b2 = bool(kv.get('rel_loss_diff', 1) <= BAR_LOSS_REL and kv.get('grad_cos', 0) >= BAR_GRAD_COS)
        kres = dict(holds=b2, how='fell to the bf16 bar: relabelled near', relabelled='near')
    kres.update(label='exact-candidate (treated as numbers-changing in this run)', deterministic=((load(box1, 'gr4_abequiv_det.launch.json') or {}).get('deterministic')))
    out['kvcat'] = kres
    return out


def mark7(box1):
    pb, pd = section(load(box1, 'gr4_prof_base.json'), 'profiler'), section(load(box1, 'gr4_prof_defer.json'), 'profiler')
    cb, cd = (pb or {}).get('cuda') or {}, (pd or {}).get('cuda') or {}
    if not cb or not cd:
        return dict(holds=None, why='profiler cuda counts missing (CPU run or failed step)', base=cb or None, defer=cd or None)
    s, d, kb, kd = cd.get('stream_syncs_per_update'), cd.get('dtoh_copies_per_update'), cb.get('kernels_per_update'), cd.get('kernels_per_update')
    ok = dict(syncs=s is not None and s <= SYNC_MAX, dtoh=d is not None and d <= DTOH_MAX, kernels=(kb and kd is not None and kd <= KERN_FRAC * kb))
    return dict(holds=all(ok.values()), parts=ok, defer_syncs=s, defer_dtoh=d, base_syncs=cb.get('stream_syncs_per_update'), base_dtoh=cb.get('dtoh_copies_per_update'),
                base_kernels=kb, defer_kernels=kd, kernel_ratio=(kd / kb) if kb and kd is not None else None,
                base_kernel_ms=cb.get('kernel_time_ms_per_update'), defer_kernel_ms=cd.get('kernel_time_ms_per_update'),
                kernel_ms_ratio=(cd.get('kernel_time_ms_per_update') / cb['kernel_time_ms_per_update']) if cb.get('kernel_time_ms_per_update') and cd.get('kernel_time_ms_per_update') is not None else None)


def host(box):
    side = None
    for p in sorted(glob.glob(os.path.join(box, '*.launch.json'))):
        side = side or load(box, os.path.basename(p))
    txt = ''
    try:
        txt = open(os.path.join(box, 'gr4_host.txt')).read()
    except OSError:
        pass
    return dict(hostname=(side or {}).get('host'), cpu_model=(side or {}).get('cpu_model'), torch=(side or {}).get('torch'), cuda=(side or {}).get('cuda'), gpu=(side or {}).get('gpu'), host_txt=txt.strip()[:600])


def box_readout(box, m2):
    arms = runs_of(box)
    refs, cmed, hm = references(arms), chunk_medians(arms), hostmon(box)
    mhz = [num(r.get('trainer_cpu_mhz')) for r in (hm or []) if num(r.get('trainer_cpu_mhz')) is not None]
    struck = not mhz
    mhz_med = st.median(mhz) if mhz else None
    util = [num(r.get('gpu_util_pct')) for r in (hm or []) if num(r.get('gpu_util_pct')) is not None]
    res = dict(box=box, host=host(box), references=refs, hostmon=dict(samples=len(hm or []), trainer_mhz_median=mhz_med, rule_e_struck=struck,
                                                                      gpu_util_median=st.median(util) if util else None), arms={})
    for key, x in arms.items():
        ok2 = (m2.get('defer') or {}).get('holds') if key in ('d4', 'd8') else ((m2.get('kvcat') or {}).get('holds') if key == 'k4' else True)
        res['arms'][key] = arm_result(key, x, refs, cmed, hm, mhz_med, struck, bool(ok2))
    aa = res['arms'].get('aa') or {}
    res['mark5'] = None if not aa.get('decided') else bool(abs(aa['b_median'] / aa['a_median'] - 1) < AA_MAX)
    res['mark5_value'] = (aa['b_median'] / aa['a_median'] - 1) if aa.get('decided') else None
    res['box_counts'] = res['mark5'] is True
    return res


def outcome(boxes, m2, m7):
    """Section 5 of the sheet: what the result allows."""
    d4 = [b['arms'].get('d4') or {} for b in boxes]
    counts = [b['box_counts'] for b in boxes]
    wins = [bool(c and x.get('decided') and x.get('mark1') and x['speed'] >= P1_X) for c, x in zip(counts, d4)]     # a port-grade win: mark 1 AND >= 1.25x (section 5: 1.10-1.25x = no port)
    hosts = [(b['host'].get('hostname'), b.get('machine')) for b in boxes]
    same_env = len({(b['host'].get('torch'), b['host'].get('cuda'), b.get('image')) for b in boxes}) == 1
    distinct = len(boxes) == 2 and hosts[0] != hosts[1] and all(h[0] for h in hosts) and (hosts[0][0] != hosts[1][0]) and (not all(h[1] for h in hosts) or hosts[0][1] != hosts[1][1])
    speeds = [x.get('speed') for x in d4]
    k_ms = m7.get('kernel_ms_ratio')
    v = dict(d4_wins=wins, d4_speeds=speeds, boxes_count=counts, replication_hosts_distinct=distinct, replication_same_env=same_env, mark7=m7.get('holds'), mark2_defer=(m2.get('defer') or {}).get('holds'))
    kill = [bool(c and x.get('decided') and x['speed'] < KILL_X and m7.get('holds') and k_ms is not None and k_ms <= KERN_EXTRA) for c, x in zip(counts, d4)]
    inefficient = [bool(c and x.get('decided') and x['speed'] < KILL_X and k_ms is not None and k_ms > KERN_EXTRA) for c, x in zip(counts, d4)]
    p6 = boxes[0].get('P6') or {}
    two = len(boxes) == 2 and distinct and same_env
    v.update(p1_kill_by_box=kill, defer_inefficient_by_box=inefficient, p6_R=p6.get('R'), p6_dead=p6.get('dead'), voided_boxes=[i + 1 for i, c in enumerate(counts) if not c])
    # the kill, like the win, needs both hosts (amended 10-17 before sealing, from the dry-run tests): a verdict on one host only, or two hosts that disagree, buys one more replication box
    if v['mark2_defer'] is False:
        v['allows'] = 'mark 2 fails for defer: defer is not used however fast'
    elif m7.get('holds') is False:
        v['allows'] = 'mark 7 misses: the speed result is an artifact; debug offline, no more rentals for this'
    elif p6.get('dead'):
        v['allows'] = 'framing kill holds (P6: the baseline was GPU-bound): defer and CUDA graphs are closed as launch fixes'
    elif two and all(kill):
        v['allows'] = 'framing kill holds (P1 on both hosts): defer and CUDA graphs are closed as launch fixes'
    elif two and all(inefficient):
        v['allows'] = 'defer is inefficient on CUDA (D4 < 1.10x with defer adding GPU work, both hosts): not a framing kill; no port'
    elif two and all(wins) and m7.get('holds') and v['mark2_defer']:
        v['allows'] = 'D4 wins on both hosts: production port of defer may be written and reviewed, and a PC test bid; fresh runs from update 0 only; no change to 8aB3G2A4/A8'
    elif any(wins) and (any(kill) or any(inefficient)):
        v['allows'] = 'hosts disagree (a win on one host, a kill or an inefficiency verdict on the other): one more replication box under this sheet'
    elif any(wins):
        v['allows'] = 'D4 wins on one host only: one more replication box under this sheet'
    elif any(kill) or any(inefficient):
        v['allows'] = 'a kill or inefficiency verdict on one host only: one more replication box under this sheet'
    elif not all(counts):
        v['allows'] = 'a box failed mark 5 (or its AA is undecided): nothing on that box counts; undecided'
    elif any(not x.get('decided') for x in d4):
        v['allows'] = 'D4 regime-confounded or missing on a box: undecided'
    else:
        v['allows'] = 'D4 between 1.10x and 1.25x or mark 1 fails: no port; next is a GPU profile by code region under a new prereg'
    return v


def predictions(boxes, m7):
    b1 = boxes[0]['arms']
    d4, d8, k4 = b1.get('d4') or {}, b1.get('d8') or {}, b1.get('k4') or {}
    out = dict(P1=[dict(box=i + 1, speed=(b['arms'].get('d4') or {}).get('speed'), right=((b['arms'].get('d4') or {}).get('speed') or 0) >= P1_X if (b['arms'].get('d4') or {}).get('decided') else None) for i, b in enumerate(boxes)])
    out['P2'] = dict(d8=d8.get('speed'), d4=d4.get('speed'), right=(d8['speed'] >= d4['speed']) if (d8.get('decided') and d4.get('decided')) else None, secondary=True)
    out['P3'] = dict(k4=k4.get('speed'), right=(P3_LO <= k4['speed'] <= P3_HI) if k4.get('decided') else None)
    out['P4'] = 'not tested in this run (PC)'
    pa, pb = d4.get('peak_a_gb'), d4.get('peak_b_gb')
    out['P5'] = dict(base_gb=pa, defer_gb=pb, right=(pb <= pa + P5_GB) if (pa is not None and pb is not None) else None)
    out['K4_peak_gb'] = k4.get('peak_b_gb')
    return out


def p6(box, m7):
    d4 = box['arms'].get('d4') or {}
    am = d4.get('a_median') or (st.median([r['a'] for r in d4.get('rounds', []) if r.get('a')]) if d4.get('rounds') else None)
    k = m7.get('base_kernel_ms')
    if not am or k is None:
        return dict(R=None, dead=None, why='needs the baseline profiled kernel ms and the in-box unprofiled A median')
    R = k / (am * 1000.0)
    return dict(R=R, dead=R >= P6_DEAD, kernel_ms=k, a_median_s=am)


def render(r):
    L = ['# GPU-RUN-4 readout against PREREG-launch-defer.md', '', f'outcome (section 5): **{r["outcome"]["allows"]}**', '']
    m2, m7 = r['mark2'], r['mark7']
    L += ['## Mark 2 (same maths, box 1)', '', f'- defer: bar {m2["defer"]["bar"]} ({m2["defer"]["bar_precision"]}: rel loss {m2["defer"]["rel_loss_diff"]}, grad cos {m2["defer"]["grad_cos"]}); E4 {m2["defer"]["E4"]}; holds {m2["defer"]["holds"]}; {m2["defer"]["label"]}',
          f'- kvcat: holds {m2["kvcat"].get("holds")} ({m2["kvcat"].get("how")}); {m2["kvcat"]["label"]}', '',
          '## Mark 7 (mechanism, box 1 profiler)', '', f'- holds {m7.get("holds")}; defer syncs {m7.get("defer_syncs")} (base {m7.get("base_syncs")}), DtoH {m7.get("defer_dtoh")} (base {m7.get("base_dtoh")}), kernels {m7.get("defer_kernels")} / {m7.get("base_kernels")} = {m7.get("kernel_ratio")}, kernel ms ratio {m7.get("kernel_ms_ratio")}', '']
    for i, b in enumerate(r['boxes']):
        L += [f'## Box {i + 1}: {b["host"].get("hostname")} | {b["host"].get("cpu_model")} | torch {b["host"].get("torch")} cuda {b["host"].get("cuda")} | machine {b.get("machine")} | image {b.get("image")}', '',
              f'references {json.dumps({k: (round(v, 4) if v else v) for k, v in b["references"].items()})}; host monitor {b["hostmon"]}; mark 5 (AA) {b["mark5"]} ({b["mark5_value"]}); box counts: {b["box_counts"]}', '',
              '| arm | status | read rounds | A median | B median | speed | all B<A | peak B GB | mark 1 |', '|---|---|---|---|---|---|---|---|---|']
        for k, a in b['arms'].items():
            f = lambda x, n=4: '-' if x is None else (f'{x:.{n}f}' if isinstance(x, float) else str(x))
            L.append(f'| {k}{" (secondary)" if a.get("secondary") else ""} | {a.get("status")} | {a.get("read_rounds", "-")} | {f(a.get("a_median"))} | {f(a.get("b_median"))} | {f(a.get("speed"), 3)} | {a.get("all_b_below", "-")} | {f(a.get("peak_b_gb"), 2)} | {a.get("mark1", "-")} |')
        L.append('')
        for k, a in b['arms'].items():
            for rr in a.get('rounds', []):
                if not rr['read']:
                    L.append(f'- {k} round {rr["round"]} not read: A {rr["a_why"] or "ok"}; B {rr["b_why"] or "ok"}; mark 4 {rr["mark4"]}')
        L.append('')
    L += ['## Predictions', '', '```', json.dumps(r['predictions'], indent=1, default=str), '```', '', f'P6: {json.dumps(r["P6"])}', '', '## Outcome detail', '', '```', json.dumps(r['outcome'], indent=1, default=str), '```']
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--box1', required=True); ap.add_argument('--box2')
    for k in ('machine', 'image', 'dph'):
        ap.add_argument(f'--box1-{k}'); ap.add_argument(f'--box2-{k}')
    ap.add_argument('--out'); ap.add_argument('--md')
    a = ap.parse_args(argv)
    m2, m7 = mark2(a.box1), mark7(a.box1)
    boxes = []
    for i, d in enumerate([a.box1, a.box2]):
        if not d:
            continue
        b = box_readout(d, m2)
        b['machine'], b['image'], b['dph'] = getattr(a, f'box{i + 1}_machine'), getattr(a, f'box{i + 1}_image'), getattr(a, f'box{i + 1}_dph')
        boxes.append(b)
    boxes[0]['P6'] = p6(boxes[0], m7)
    r = dict(sheet='PREREG-launch-defer.md (amended 10-17)', mark2=m2, mark7=m7, boxes=boxes, P6=boxes[0]['P6'], predictions=predictions(boxes, m7))
    r['outcome'] = outcome(boxes, m2, m7)
    if a.out:
        json.dump(r, open(a.out, 'w'), indent=1, default=str)
    md = render(r)
    if a.md:
        open(a.md, 'w').write(md)
    print(md)
    return r


if __name__ == '__main__':
    main()
