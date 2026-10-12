"""Test TK / TKN marks and readout (design/tokens-experiment-2026-10-09.md sections 4, 5 and addendum A), computed exactly as written. Read-only.

  python -m custom_io.g8a.analyze_tk --results DIR [DIR...] [--seeds 400,401] [--cost 8aTK-cost.json] [--out FILE.json]
  python -m custom_io.g8a.analyze_tk --results DIR [DIR...] --stop-check TK|TKN        (one line, STOP: ... or CONTINUE: ..., exit 0)

Walks the dirs for .../<QUEUE>-3M-s<seed>/B2/RESULT.json. QUEUE = 8aG1d / 8aG1e / 8aG1f (control G-B2: the B2 cfg must NOT have tok_think), 8aTK (cfg tok_think true, reader_layers not 0)
or 8aTKN (cfg tok_think true and reader_layers 0). A run whose name and config disagree, whose seed differs, or whose status is not 'ok' is skipped with the reason. Anything missing
gives 'n/a' (never a crash).

Where the numbers live in RESULT.json (checked on G1's 8aG1d-3M-s400 control):
  pooled-5      = analyze.P5: sum of final_eval[s].correct / sum of final_eval[s].n over in_dist, answer, frame, vocab, variant (6,040 rows) x 100
  split         = final_eval[split].exact (percent); loops:0 in_dist = lesions['loops:0'].in_dist.exact
  family        = final_eval[split].by_family[f] = {correct, n}
  cipher_map    = counts of rows right out of 120: final_eval[in_dist|answer|frame].by_family.cipher_map.correct / .n, summed (40 rows per split)
  chain-5       = chain5.intact.exact (percent, 1,000 rows)
  steps/s       = steps_per_s;  letters per thinker spot = tok_think.ratio (written by train.py for tok_think runs only)

Marks (sec. 5), TK against G-B2 (the control of the same seed):
  M1 pooled-5 TK - G-B2, mean of the 2 seeds >= -1.0     M2 frame and vocab each, 2-seed mean TK - G-B2 >= -3.0
  M3 cipher_map (120 rows per seed, 240 over 2 seeds) TK >= G-B2 - 10 points; judged only if G-B2 s400 and s401 differ by <= 10 points on it
  M4 chain-5 >= 99 on each seed                           M5 per seed (TK in_dist - TK loops:0 in_dist) >= 0.8 x (G-B2 in_dist - G-B2 loops:0 in_dist)
Hair rule (sec. 5): ONE single-seed miss of M4 or M5 by <= 0.5 point, every other mark passing on both seeds, counts as a pass, disclosed. M1-M3 get no tolerance.
Proved wrong: pooled-5 2-seed mean <= -2.0, or (M3 judged) cipher_map more than 20 points below G-B2. Readout: PASS / PASS (hair rule) / PROVED WRONG / NOT SHOWN / n/a.
TKN vs TK: "window can go" if pooled-5 mean >= -1.0, frame and vocab each >= -3.0, cipher_map (240) >= TK - 10, M4 and M5 hold for TKN; "window needed" if pooled-5 mean <= -2.0
or cipher_map more than 20 below TK; else not shown. If TK is proved wrong, TKN is also read against G-B2 with M1-M5.
Addendum A (--stop-check, seed 400 alone): TK: STOP if pooled-5 TK - G-B2 <= -2.0 or (M3 judged, i.e. both G-B2 seeds present and within 10 points) cipher_map (120 rows) more than 20 points
below G-B2. TKN: STOP if pooled-5 TKN - TK <= -2.0 or cipher_map (120 rows) more than 20 points below TK. When a needed run is missing the line says NO DECISION (never CONTINUE).
"""
import argparse, json, math, os, re
from custom_io import analyze as A

QUEUE = re.compile(r'^(8aG1[def]|8aTKN|8aTK)-3M-s(\d+)$')
SEEDS = [400, 401]
SPLITS = ['in_dist', 'answer', 'frame', 'vocab', 'variant', 'family']
CIPHER_SPLITS = ['in_dist', 'answer', 'frame']
LETTER_FAMS = ['cipher_map', 'letter_ops', 'copy_word', 'word_filter', 'seq_next']
IND = A.SPL('in_dist')


def kind_of(queue, r):
    """-> ('GB2'|'TK'|'TKN', None) or (None, reason)."""
    cfg = A.g(r, 'config', 'cfg')
    if not isinstance(cfg, dict):
        return None, 'no config.cfg'
    tt, rl = bool(cfg.get('tok_think')), cfg.get('reader_layers')
    if queue.startswith('8aG1'):
        return ('GB2', None) if not tt else (None, f'{queue} has tok_think true (not a control)')
    if queue == '8aTK':
        return ('TK', None) if tt and rl != 0 else (None, f'8aTK name but cfg tok_think={tt} reader_layers={rl}')
    return ('TKN', None) if tt and rl == 0 else (None, f'8aTKN name but cfg tok_think={tt} reader_layers={rl}')


def load(dirs):
    """-> runs {(kind, seed): RESULT}, skipped [(path, why)]."""
    runs, skipped = {}, []
    for d in dirs:
        for root, _, fs in os.walk(d):
            m = QUEUE.match(os.path.basename(os.path.dirname(root)))
            if 'RESULT.json' not in fs or not m or os.path.basename(root) != 'B2':
                continue
            try:
                r = json.load(open(os.path.join(root, 'RESULT.json')))
            except Exception as e:
                skipped.append((root, f'unreadable: {e}')); continue
            if r.get('status') != 'ok':
                skipped.append((root, f"status {r.get('status')}")); continue
            kind, why = kind_of(m.group(1), r)
            if kind is None:
                skipped.append((root, why)); continue
            seed = int(m.group(2))
            cs = A.g(r, 'config', 'seed')
            if cs is not None and cs != seed:
                skipped.append((root, f'name seed {seed} but config seed {cs}')); continue
            if (kind, seed) in runs:
                skipped.append((root, f'duplicate of {(kind, seed)}')); continue
            runs[(kind, seed)] = r
    return runs, skipped


# ---- per-run numbers -------------------------------------------------------------------------------------------------
def cipher(r, fam='cipher_map'):
    """(correct, n) of `fam` pooled over in_dist + answer + frame, counts of rows (n = 120 for cipher_map), or None."""
    try:
        c = n = 0
        for s in CIPHER_SPLITS:
            b = r['final_eval'][s]['by_family'][fam]
            c, n = c + b['correct'], n + b['n']
        return (c, n) if n else None
    except (TypeError, KeyError):
        return None


def drop(r):
    return A.sub(IND(r), IND(r, 'loops:0'))


def pct(cn):
    return None if cn is None else round(100.0 * cn[0] / cn[1], 9)


def pool(cns):
    """pooled percent over several (correct, n) pairs; None if any is missing."""
    return None if not cns or any(c is None for c in cns) else round(100.0 * sum(c[0] for c in cns) / sum(c[1] for c in cns), 9)


def mean(v):
    v = list(v)
    return None if not v or any(x is None for x in v) else sum(v) / len(v)


def get(runs, kind, s):
    return runs.get((kind, s))


def paired(runs, a, b, seeds, fn):
    """{seed: fn(a) - fn(b)} (None where a run or number is missing)."""
    return {s: (A.sub(fn(runs[(a, s)]), fn(runs[(b, s)])) if (a, s) in runs and (b, s) in runs else None) for s in seeds}


def ok_mark(mid, desc, value, thr, op='>='):
    """2-seed-mean mark, no tolerance."""
    return dict(id=mid, desc=desc, value=value, thr=thr, ok=None if value is None else (value >= thr if op == '>=' else value <= thr), per_seed=None)


def seed_mark(mid, desc, seeds, fn):
    """per-seed mark; fn(seed) -> (value, threshold) or None. shortfall = threshold - value (points)."""
    per = {}
    for s in seeds:
        v = fn(s)
        per[s] = None if v is None or v[0] is None or v[1] is None else dict(value=v[0], thr=v[1], ok=v[0] >= v[1], shortfall=max(0.0, v[1] - v[0]))
    return dict(id=mid, desc=desc, per_seed=per)


def m3_gate(runs, seeds):
    """G-B2's own seeds within 10 points on cipher_map (120 rows each). -> (judged True/False/None, gap points or None, {seed: (c, n)})"""
    cn = {s: cipher(runs[('GB2', s)]) if ('GB2', s) in runs else None for s in seeds}
    if any(v is None for v in cn.values()) or len(cn) < 2:
        return None, None, cn
    p = [pct(v) for v in cn.values()]
    gap = max(p) - min(p)
    return gap <= 10.0, gap, cn


def marks_vs(runs, x, ctl, seeds, judged):
    """M1..M5 of arm x against arm ctl ('GB2' or 'TK'). judged = M3 gate (True / False / None)."""
    d5 = A.stats(paired(runs, x, ctl, seeds, A.P5))
    dfr = A.stats(paired(runs, x, ctl, seeds, A.SPL('frame')))
    dvo = A.stats(paired(runs, x, ctl, seeds, A.SPL('vocab')))
    cx = [cipher(runs[(x, s)]) if (x, s) in runs else None for s in seeds]
    cc = [cipher(runs[(ctl, s)]) if (ctl, s) in runs else None for s in seeds]
    px, pc = pool(cx), pool(cc)
    gap_pts = A.sub(pc, px)                        # control minus arm, points on the pooled 240 rows
    m1 = ok_mark('M1', f'pooled-5 {x} - {ctl}, 2-seed mean >= -1.0', d5['mean'] if d5['n'] == len(seeds) else None, -1.0)
    m2f = ok_mark('M2 frame', f'frame {x} - {ctl}, 2-seed mean >= -3.0', dfr['mean'] if dfr['n'] == len(seeds) else None, -3.0)
    m2v = ok_mark('M2 vocab', f'vocab {x} - {ctl}, 2-seed mean >= -3.0', dvo['mean'] if dvo['n'] == len(seeds) else None, -3.0)
    m3 = ok_mark('M3', f'cipher_map pooled 240 rows {x} - {ctl} >= -10 points (judged only if G-B2 seeds within 10)', None if gap_pts is None else -gap_pts, -10.0)
    if judged is not True:
        m3['ok'] = 'not judged' if judged is False else 'n/a'
    m4 = seed_mark('M4', 'chain-5 >= 99 on each seed', seeds, lambda s: (A.C5(runs[(x, s)]), 99.0) if (x, s) in runs else None)
    m5 = seed_mark('M5', f'{x} (in_dist - loops:0 in_dist) minus 0.8 x {ctl} (same) >= 0', seeds,
                   lambda s: (A.sub(drop(runs[(x, s)]), None if drop(runs[(ctl, s)]) is None else 0.8 * drop(runs[(ctl, s)])), 0.0) if (x, s) in runs and (ctl, s) in runs else None)
    return dict(M1=m1, M2f=m2f, M2v=m2v, M3=m3, M4=m4, M5=m5, d5=d5, cipher_x=px, cipher_ctl=pc, cipher_gap_pts=gap_pts,
                cipher_counts=dict(arm=cx, ctl=cc), loops0_in_dist={s: A.sub(IND(runs[(x, s)]), drop(runs[(x, s)])) if (x, s) in runs else None for s in seeds})


def verdict(mv, judged):
    """-> (readout, notes, hair). PROVED WRONG beats everything."""
    notes, hair, hard, na = [], [], [], False
    wrong = []
    if mv['d5']['n'] and mv['d5']['mean'] is not None and mv['d5']['n'] == len(mv['M4']['per_seed']) and mv['d5']['mean'] <= -2.0:
        wrong.append(f"pooled-5 2-seed mean {mv['d5']['mean']:+.2f} <= -2.0")
    if judged is True and mv['cipher_gap_pts'] is not None and mv['cipher_gap_pts'] > 20.0:
        wrong.append(f"cipher_map {mv['cipher_gap_pts']:.1f} points below the control (> 20)")
    if wrong:
        return 'PROVED WRONG', wrong, hair
    for k in ('M1', 'M2f', 'M2v', 'M3'):
        ok = mv[k]['ok']
        if ok is None or ok == 'n/a':
            na = True
        elif ok is False:
            hard.append(f"{mv[k]['id']} {mv[k]['value']:+.2f} < {mv[k]['thr']:g}")
    for k in ('M4', 'M5'):
        for s, p in mv[k]['per_seed'].items():
            if p is None:
                na = True
            elif not p['ok']:
                (hair if p['shortfall'] <= 0.5 else hard).append(f"{k} seed {s}: short by {p['shortfall']:.2f}")
    if hard:
        return 'NOT SHOWN', hard, hair
    if na:
        return 'n/a', ['some runs or numbers missing'], hair
    if len(hair) > 1:
        return 'NOT SHOWN', ['more than one single-seed miss: hair rule allows one'], hair
    if len(hair) == 1:
        return 'PASS (hair rule)', ['hair rule used: ' + hair[0]], hair
    if mv['M3']['ok'] == 'not judged':
        return 'PASS', ['M3 not judged (G-B2 seeds differ by more than 10 points on cipher_map); M1, M2, M4, M5 pass'], hair
    return 'PASS', [], hair


def readout_window(tkn_gb2, tkn_tk, seeds):
    mv = tkn_tk
    if mv['d5']['n'] != len(seeds) or mv['cipher_gap_pts'] is None:
        return 'n/a', ['TK or TKN runs missing']
    if mv['d5']['mean'] <= -2.0 or mv['cipher_gap_pts'] > 20.0:
        return 'window needed', [f"pooled-5 TKN-TK {mv['d5']['mean']:+.2f}, cipher_map {-mv['cipher_gap_pts']:+.1f} points"]
    holds = all(p is not None and p['ok'] for p in list(tkn_gb2['M4']['per_seed'].values()) + list(tkn_gb2['M5']['per_seed'].values()))
    can_go = (mv['d5']['mean'] >= -1.0 and mv['M2f']['ok'] is True and mv['M2v']['ok'] is True and mv['cipher_gap_pts'] <= 10.0 and holds)
    if can_go:
        return 'window can go', []
    why = []
    if mv['d5']['mean'] < -1.0: why.append(f"pooled-5 {mv['d5']['mean']:+.2f} < -1.0")
    if mv['M2f']['ok'] is not True: why.append(f"frame {mv['M2f']['value']:+.2f} < -3.0")
    if mv['M2v']['ok'] is not True: why.append(f"vocab {mv['M2v']['value']:+.2f} < -3.0")
    if mv['cipher_gap_pts'] > 10.0: why.append(f"cipher_map {-mv['cipher_gap_pts']:+.1f} points vs TK < -10")
    if not holds: why.append('M4 or M5 does not hold for TKN (against G-B2)')
    return 'not shown (window stays)', why


# ---- report-only ------------------------------------------------------------------------------------------------------
def reported(runs, seeds, cost):
    out = {}
    kinds = ['GB2', 'TK', 'TKN']
    pres = {k: [s for s in seeds if (k, s) in runs] for k in kinds}
    out['pooled5'] = {k: {s: A.P5(runs[(k, s)]) for s in pres[k]} for k in kinds}
    out['splits'] = {k: {sp: {s: A.SPL(sp)(runs[(k, s)]) for s in pres[k]} for sp in SPLITS} for k in kinds}
    fams = sorted({f for r in runs.values() for sp in A.POOL for f in (A.g(r, 'final_eval', sp, 'by_family') or {})})
    out['families_pooled5'] = {k: {f: {s: A.FAMS([f])(runs[(k, s)]) for s in pres[k]} for f in fams} for k in kinds}
    out['families_by_split'] = {k: {sp: {s: {f: v for f, v in (A.g(runs[(k, s)], 'final_eval', sp, 'by_family') or {}).items()} for s in pres[k]} for sp in SPLITS} for k in kinds}
    out['letter_families'] = {k: {f: {s: cipher(runs[(k, s)], f) for s in pres[k]} for f in LETTER_FAMS} for k in kinds}
    out['cipher_map_counts_of_120'] = {k: {s: cipher(runs[(k, s)]) for s in pres[k]} for k in kinds}
    out['chain5'] = {k: {s: A.C5(runs[(k, s)]) for s in pres[k]} for k in kinds}
    out['loops0_in_dist'] = {k: {s: A.SPL('in_dist')(runs[(k, s)], 'loops:0') for s in pres[k]} for k in kinds}
    out['loops0_in_dist_vs_old_line_5'] = {k: {s: (None if v is None else v <= 5.0) for s, v in out['loops0_in_dist'][k].items()} for k in kinds}
    out['steps_per_s'] = {k: {s: runs[(k, s)].get('steps_per_s') for s in pres[k]} for k in kinds}
    out['wall_s'] = {k: {s: runs[(k, s)].get('wall_s') for s in pres[k]} for k in kinds}
    out['n_params'] = {k: {s: runs[(k, s)].get('n_params') for s in pres[k]} for k in kinds}
    out['device_bf16'] = {k: {s: dict(device=A.g(runs[(k, s)], 'config', 'device'), bf16=A.g(runs[(k, s)], 'config', 'bf16')) for s in pres[k]} for k in kinds}
    out['tok_think_letters_per_spot'] = {k: {s: runs[(k, s)].get('tok_think') for s in pres[k]} for k in ('TK', 'TKN')}
    out['cost_check'] = cost if cost is not None else 'n/a (no --cost given)'
    return out


def analyze(runs, seeds=SEEDS, cost=None):
    judged, gap, gcn = m3_gate(runs, seeds)
    tk = marks_vs(runs, 'TK', 'GB2', seeds, judged)
    tkn_gb2 = marks_vs(runs, 'TKN', 'GB2', seeds, judged)
    tkn_tk = marks_vs(runs, 'TKN', 'TK', seeds, True)
    tk_read, tk_notes, tk_hair = verdict(tk, judged)
    tkn_read, tkn_notes, tkn_hair = verdict(tkn_gb2, judged)
    win, win_why = readout_window(tkn_gb2, tkn_tk, seeds)
    return dict(seeds=list(seeds), present=sorted(f'{k}/s{s}' for k, s in runs),
                M3_gate=dict(judged=judged, gb2_cipher_gap_points=gap, gb2_cipher_counts=gcn),
                TK=dict(readout=tk_read, notes=tk_notes, hair=tk_hair, marks=tk),
                TKN_vs_GB2=dict(readout=tkn_read, notes=tkn_notes, hair=tkn_hair, marks=tkn_gb2, applies='only if TK is PROVED WRONG (sec. 5); otherwise report-only'),
                TKN_vs_TK=dict(window=win, why=win_why, marks=tkn_tk),
                reported=reported(runs, seeds, cost))


def stop_check(runs, which, seed=400):
    """Addendum A. -> (line, dict). Never raises."""
    seeds = SEEDS
    if which == 'TK':
        a, b, label = ('TK', seed), ('GB2', seed), 'G-B2'
    else:
        a, b, label = ('TKN', seed), ('TK', seed), 'TK'
    if a not in runs or b not in runs:
        need = [f'{k}/s{s}' for k, s in (a, b) if (k, s) not in runs]
        return f"NO DECISION: n/a, missing {', '.join(need)}", dict(decision=None)
    d = A.sub(A.P5(runs[a]), A.P5(runs[b]))
    ca, cb = cipher(runs[a]), cipher(runs[b])
    gap = A.sub(pct(cb), pct(ca))                   # control minus arm, points on 120 rows
    reasons = []
    if d is None:
        return f'NO DECISION: n/a, pooled-5 unreadable for {a} or {b}', dict(decision=None)
    if d <= -2.0:
        reasons.append(f'pooled-5 {which} - {label} = {d:+.2f} <= -2.0')
    txt_c = 'n/a' if gap is None else f'{ca[0]}/{ca[1]} vs {cb[0]}/{cb[1]} ({(-gap or 0.0):+.1f} points)'
    if which == 'TK':
        judged, ggap, _ = m3_gate(runs, seeds)
        m3txt = ('M3 judged' if judged else 'M3 not judged (G-B2 cipher_map seeds differ by more than 10 points)' if judged is False
                 else 'M3 not yet judgeable (G-B2 s401 missing)')
        if judged is True and gap is not None and gap > 20.0:
            reasons.append(f'cipher_map {txt_c} more than 20 points below G-B2')
    else:
        m3txt = 'cipher_map judged against TK s400'
        if gap is not None and gap > 20.0:
            reasons.append(f'cipher_map {txt_c} more than 20 points below TK')
    nums = f'pooled-5 {which} {A.P5(runs[a]):.2f} vs {label} {A.P5(runs[b]):.2f} (diff {d:+.2f}, stop at <= -2.0); cipher_map {txt_c} (stop if > 20 points below); {m3txt}'
    if reasons:
        word = 'proved wrong (seed 400, kill-first); TKN does not run' if which == 'TK' else 'window needed (seed 400, kill-first); TKN seed 401 does not run'
        return f"STOP: {word}: " + '; '.join(reasons) + f'. {nums}', dict(decision='STOP', reasons=reasons)
    return f'CONTINUE: {nums}', dict(decision='CONTINUE')


def fmt(v, p=2):
    return 'n/a' if v is None else (f'{v:+.{p}f}' if isinstance(v, float) else str(v))


def okw(ok):
    return 'ok' if ok is True else 'MISS' if ok is False else str(ok)


def show(res):
    g = res['M3_gate']
    print(f"present: {', '.join(res['present']) or 'none'}")
    print(f"M3 gate: judged {g['judged']} (G-B2 cipher_map counts {g['gb2_cipher_counts']}, gap {fmt(g['gb2_cipher_gap_points'], 1)} points)")
    for name, key in (('TK vs G-B2', 'TK'), ('TKN vs G-B2', 'TKN_vs_GB2')):
        st = res[key]
        print(f"{name}: {st['readout']}  {'; '.join(st['notes'])}")
        mv = st['marks']
        for k in ('M1', 'M2f', 'M2v', 'M3'):
            m = mv[k]
            print(f"  {m['id']}: {fmt(m['value'])} vs {m['thr']:g} {okw(m['ok'])}")
        for k in ('M4', 'M5'):
            print(f"  {k}: " + '  '.join(f"s{s} {fmt(p['value'])} vs {p['thr']:g} {'ok' if p['ok'] else 'MISS'}" if p else f's{s} n/a' for s, p in mv[k]['per_seed'].items()))
        print(f"  cipher_map pooled: arm {fmt(mv['cipher_x'], 1)}%  control {fmt(mv['cipher_ctl'], 1)}%  counts {mv['cipher_counts']}")
    w = res['TKN_vs_TK']
    print(f"TKN vs TK: window {w['window']}  {'; '.join(w['why'])}  (pooled-5 mean {fmt(w['marks']['d5']['mean'])}, frame {fmt(w['marks']['M2f']['value'])}, vocab {fmt(w['marks']['M2v']['value'])}, cipher {fmt(None if w['marks']['cipher_gap_pts'] is None else -w['marks']['cipher_gap_pts'], 1)} points)")
    r = res['reported']
    print('steps/s:', r['steps_per_s'], ' letters per spot:', {k: {s: (v or {}).get('ratio') if isinstance(v, dict) else v for s, v in d.items()} for k, d in r['tok_think_letters_per_spot'].items()})
    print('cost check:', 'n/a' if isinstance(r['cost_check'], str) else [(a.get('arm'), a.get('thinker_keys_per_row'), a.get('total_peak_mib'), a.get('step_s')) for a in r['cost_check'].get('arms', [])])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--seeds', default=','.join(map(str, SEEDS)))
    ap.add_argument('--cost', help='8aTK-cost.json from custom_io.g8a.tok_cost (report-only)')
    ap.add_argument('--stop-check', choices=['TK', 'TKN'], help='addendum A single-seed stop rule on seed 400: one line, exit 0')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    runs, skipped = load(a.results)
    seeds = [int(x) for x in a.seeds.split(',')]
    if a.stop_check:
        line, info = stop_check(runs, a.stop_check)
        print(line)
        if a.out:
            json.dump(dict(stop_check=a.stop_check, line=line, info=info, skipped=skipped), open(a.out, 'w'), indent=1, default=str)
        return line
    cost = None
    if a.cost:
        try:
            cost = json.load(open(a.cost))
        except Exception as e:
            cost = f'n/a (unreadable: {e})'
    res = analyze(runs, seeds, cost)
    res['skipped'] = skipped
    show(res)
    for p, why in skipped:
        print('skipped', p, '-', why)
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1, default=str)
    return res


if __name__ == '__main__':
    main()
