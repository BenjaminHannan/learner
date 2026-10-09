"""Test GX marks and readout (design/8a-gx-experts-2026-10-09.md sections 4, 5 and addendum A), computed exactly as written. Read-only.

  python -m custom_io.g8a.analyze_gx --results DIR [DIR...] [--seeds 400,401] [--out FILE.json]

Walks the dirs for .../<QUEUE>-<rung>-s<seed>/<ARM>/RESULT.json, QUEUE = 8aG1d / 8aG1e / 8aG1f (G1 controls) or 8aGX (stage 1) / 8aGXD (stage 2). The arm is told by the
B2 cfg: experts > 0 -> GX, else G-B2; PT is PT. Only status 'ok' runs count; anything missing gives 'n/a' (never a crash). Metric: pooled-5 (analyze.P5), per-seed paired.
Stage 1 (3M): X1 GX - G-B2 >= +1.0 each seed; X2 chain-5 >= 99; X3 (in_dist - loops:0 in_dist) of GX >= 80% of G-B2's; X4 (addendum A) every expert of every block between
0.5 and 2.0 x an even share of picks (hair: up to 2 experts per block in [0.4, 0.5) or (2.0, 2.5]); X5 status ok, finite loss (the shared-memory spill is not in RESULT.json: 'n/a').
Stage 2 (10M): D1 GX-10M - G-B2 10M >= +1.0; D2 (GX-10M - GX-3M) - (PT 10M - PT 3M) >= +1.0; D3-D5 = X2, X3, X4 at 10M.
Hair rule: ONE single-seed miss of <= 0.5 point (or one X4 hair seed) with everything else passing counts as a pass, disclosed.
Readout: GO = all pass; STOP = the X1 / D1 difference <= 0 on both seeds (stage 1: with X4 passing); else UNCLEAR. Proved wrong: 2-seed mean of that difference <= -1.0 (stage 1: with X4 passing).
"""
import argparse, json, math, os, re
from custom_io import analyze as A

QUEUE = re.compile(r'^(8aG1[def]|8aGXD|8aGX)-(3M|10M)-s(\d+)$')
RULE_FAMS = ['fewshot_number_rule', 'seq_next', 'order_chain', 'rule_apply', 'cipher_map']
SEEDS = [400, 401]
IND, SPLITS = A.SPL('in_dist'), ['in_dist', 'answer', 'frame', 'vocab', 'variant', 'family']


def load(dirs):
    """-> runs {(rung, 'GX'|'B2'|'PT', seed): RESULT}, boxes {(queue, rung, seed): box}, logs {key: last train event}, skipped [(path, why)]."""
    runs, boxes, logs, skipped = {}, {}, {}, []
    for d in dirs:
        for root, _, fs in os.walk(d):
            m = QUEUE.match(os.path.basename(root))
            if m and 'box.json' in fs:
                try:
                    boxes[(m.group(1), m.group(2), int(m.group(3)))] = json.load(open(os.path.join(root, 'box.json')))
                except Exception:
                    pass
            arm, m = os.path.basename(root), QUEUE.match(os.path.basename(os.path.dirname(root)))
            if 'RESULT.json' not in fs or not m or arm not in ('B2', 'PT'):
                continue
            try:
                r = json.load(open(os.path.join(root, 'RESULT.json')))
            except Exception as e:
                skipped.append((root, f'unreadable: {e}')); continue
            if r.get('status') != 'ok':
                skipped.append((root, f"status {r.get('status')}")); continue
            kind = 'GX' if arm == 'B2' and (A.g(r, 'config', 'cfg', 'experts') or 0) > 0 else arm
            key = (m.group(2), kind, int(m.group(3)))
            if key in runs:
                skipped.append((root, f'duplicate of {key}')); continue
            runs[key] = r
            if 'stdout.txt' in fs:
                try:
                    last = None
                    for line in open(os.path.join(root, 'stdout.txt'), errors='replace'):
                        if line.startswith('{"event": "train"'):
                            last = line
                    logs[key] = json.loads(last) if last else None
                except Exception:
                    logs[key] = None
    return runs, boxes, logs, skipped


def x4_status(r):
    """addendum A: per block, every expert's share x E in [0.5, 2.0]. -> 'pass' | 'hair' (<= 2 experts per block in [0.4, 0.5) or (2.0, 2.5], rest fine) | 'fail' | 'n/a'."""
    blocks = A.g(r, 'extra', 'moe', 'blocks')
    if not blocks:
        return 'n/a'
    st = 'pass'
    for b in blocks:
        E = len(b['share'])
        x = [s * E for s in b['share']]
        if any(v < 0.4 or v > 2.5 for v in x):
            return 'fail'
        near = sum(v < 0.5 or v > 2.0 for v in x)
        if near > 2:
            return 'fail'
        if near:
            st = 'hair'
    return st


def x5(r, log=None):
    """status ok (loaded runs are ok already) and a finite final training loss; the shared-memory spill is not recorded in RESULT.json."""
    l = r.get('final_train_loss')
    return isinstance(l, (int, float)) and math.isfinite(l)


def drop(r):
    return A.sub(IND(r), IND(r, 'loops:0'))


def seed_mark(mid, desc, seeds, fn):
    """fn(seed) -> (value, threshold) or None. Per seed: ok, shortfall (threshold - value)."""
    per = {}
    for s in seeds:
        v = fn(s)
        per[s] = None if v is None or v[0] is None or v[1] is None else dict(value=v[0], thr=v[1], ok=v[0] >= v[1], shortfall=max(0.0, v[1] - v[0]))
    return dict(id=mid, desc=desc, per_seed=per)


def judge(marks, x4, x5s):
    """-> (verdict True / False / 'n/a', note, hair list). One hair use (a single-seed miss <= 0.5, or one X4 hair seed) with everything else passing is a pass."""
    hard, hair, na = [], [], False
    for m in marks:
        for s, p in m['per_seed'].items():
            if p is None:
                na = True
            elif not p['ok']:
                (hair if p['shortfall'] <= 0.5 else hard).append(f"{m['id']} seed {s}: short by {p['shortfall']:.2f}")
    for s, st in x4.items():
        if st == 'n/a':
            na = True
        elif st == 'fail':
            hard.append(f'X4 seed {s}: experts not evenly used')
        elif st == 'hair':
            hair.append(f'X4 seed {s}: up to 2 experts per block within the hair band')
    for s, ok in x5s.items():
        if ok is False:
            hard.append(f'X5 seed {s}: unclean training')
    if hard:
        return False, hard, hair
    if na:
        return 'n/a', ['some runs missing'], hair
    return (len(hair) <= 1), (['hair rule used: ' + hair[0]] if len(hair) == 1 else []) + (['more than one hair use'] if len(hair) > 1 else []), hair


def ps(runs, rung, kind, seeds, fn, les=None):
    return {s: (fn(runs[(rung, kind, s)], les) if (rung, kind, s) in runs else None) for s in seeds}


def common(runs, rung, seeds, ctrl_rung=None):
    """X2, X3, X4, X5 for the GX run of `rung` against the G-B2 run of `ctrl_rung` (default the same)."""
    gx, ctrl = lambda s: runs.get((rung, 'GX', s)), lambda s: runs.get((ctrl_rung or rung, 'B2', s))
    x2 = seed_mark('X2', 'chain-5 >= 99', seeds, lambda s: (A.C5(gx(s)), 99.0) if gx(s) else None)
    x3 = seed_mark('X3', 'GX (in_dist - loops:0) minus 0.8 x G-B2 (in_dist - loops:0) >= 0', seeds,
                   lambda s: (A.sub(drop(gx(s)), None if drop(ctrl(s)) is None else 0.8 * drop(ctrl(s))), 0.0) if gx(s) and ctrl(s) else None)
    x4 = {s: (x4_status(gx(s)) if gx(s) else 'n/a') for s in seeds}
    x5s = {s: (x5(gx(s)) if gx(s) else 'n/a') for s in seeds}
    return x2, x3, x4, x5s


def readout(diff, x4, strict_x4, stage):
    """STOP / proved wrong from the difference d1 = {seed: GX - G-B2}."""
    v = [d for d in diff.values() if d is not None]
    x4ok = all(st in ('pass', 'hair') for st in x4.values()) if strict_x4 else True
    stop = 'n/a' if len(v) < len(diff) or not v else (all(d <= 0 for d in v) and (x4ok if strict_x4 else True))
    wrong = 'n/a' if len(v) < len(diff) or not v else (sum(v) / len(v) <= -1.0 and x4ok)
    return stop, wrong


def stage1(runs, seeds):
    x1 = seed_mark('X1', 'GX-3M - G-B2 3M >= +1.0', seeds, lambda s: (A.sub(A.P5(runs[('3M', 'GX', s)]), A.P5(runs[('3M', 'B2', s)])), 1.0) if ('3M', 'GX', s) in runs and ('3M', 'B2', s) in runs else None)
    x2, x3, x4, x5s = common(runs, '3M', seeds)
    marks = [x1, x2, x3]
    ok, note, hair = judge(marks, x4, x5s)
    diff = {s: (p['value'] if p else None) for s, p in x1['per_seed'].items()}
    stop, wrong = readout(diff, x4, True, 1)
    return dict(marks=marks, X4=x4, X5=x5s, pass_all=ok, notes=note, hair=hair, diff=diff, x4_failed=[s for s, v in x4.items() if v == 'fail'],
                readout=('GO' if ok is True else 'STOP' if stop is True else 'n/a' if 'n/a' in (ok, stop) and ok is not False else 'UNCLEAR'), stop=stop, proved_wrong=wrong,
                collapsed_note='experts not evenly used: cannot be GO' if any(v == 'fail' for v in x4.values()) else None)


def stage2(runs, seeds):
    d1 = seed_mark('D1', 'GX-10M - G-B2 10M >= +1.0', seeds, lambda s: (A.sub(A.P5(runs[('10M', 'GX', s)]), A.P5(runs[('10M', 'B2', s)])), 1.0) if ('10M', 'GX', s) in runs and ('10M', 'B2', s) in runs else None)

    def d2(s):
        k = [('10M', 'GX', s), ('3M', 'GX', s), ('10M', 'PT', s), ('3M', 'PT', s)]
        if not all(x in runs for x in k):
            return None
        p = [A.P5(runs[x]) for x in k]
        return (None if None in p else (p[0] - p[1]) - (p[2] - p[3]), 1.0)
    d2 = seed_mark('D2', '(GX-10M - GX-3M) - (PT 10M - PT 3M) >= +1.0', seeds, d2)
    x2, x3, x4, x5s = common(runs, '10M', seeds)
    x2['id'], x3['id'] = 'D3 (X2)', 'D4 (X3 vs G-B2 10M)'
    marks = [d1, d2, x2, x3]
    ok, note, hair = judge(marks, x4, x5s)
    diff = {s: (p['value'] if p else None) for s, p in d1['per_seed'].items()}
    stop, wrong = readout(diff, x4, False, 2)
    return dict(marks=marks, D5_X4=x4, X5=x5s, pass_all=ok, notes=note, hair=hair, diff=diff,
                readout=('GO' if ok is True else 'STOP' if stop is True else 'n/a' if 'n/a' in (ok, stop) and ok is not False else 'UNCLEAR'), stop=stop, proved_wrong=wrong)


def reported(runs, boxes, logs, seeds):
    out = {}
    pairs = [('GX3M_minus_B2_3M', ('3M', 'GX'), ('3M', 'B2')), ('GX3M_minus_B2_10M', ('3M', 'GX'), ('10M', 'B2')), ('GX3M_minus_PT_3M', ('3M', 'GX'), ('3M', 'PT')),
             ('GX10M_minus_B2_10M', ('10M', 'GX'), ('10M', 'B2')), ('GX10M_minus_PT_10M', ('10M', 'GX'), ('10M', 'PT'))]
    for name, a, b in pairs:
        out[name] = A.stats({s: (A.sub(A.P5(runs[(a[0], a[1], s)]), A.P5(runs[(b[0], b[1], s)])) if (a[0], a[1], s) in runs and (b[0], b[1], s) in runs else None) for s in seeds})
    for rung in ('3M', '10M'):
        out[f'splits_{rung}'] = {k: {s: A.stats(ps(runs, rung, k, seeds, A.SPL(s)))['mean'] for s in SPLITS} for k in ('GX', 'B2', 'PT')}
        fams = sorted({f for k in ('GX', 'B2') for s in seeds for f in (A.g(runs.get((rung, k, s)), 'final_eval', 'in_dist', 'by_family') or {})})
        out[f'families_in_dist_{rung}'] = {f: dict(rule_family=f in RULE_FAMS, **{k: A.stats(ps(runs, rung, k, seeds, A.FAMS([f], ['in_dist'])))['mean'] for k in ('GX', 'B2', 'PT')}) for f in fams}
        out[f'rule_families_{rung}'] = {f: out[f'families_in_dist_{rung}'].get(f) for f in RULE_FAMS}
    for key, r in sorted(runs.items()):
        if key[1] != 'GX' and key[1] != 'B2' and key[1] != 'PT':
            continue
        log = logs.get(key) or {}
        rec = dict(steps_per_s=r.get('steps_per_s'), wall_s=r.get('wall_s'), peak_mem_mib=r.get('peak_mem_mib'), peak_reserved_mib=r.get('peak_reserved_mib'), n_params=r.get('n_params'),
                   size=A.g(r, 'extra', 'size'), final_train_loss=r.get('final_train_loss'), train_log_last={k: log.get(k) for k in ('step', 'loss', 'prog', 'mode', 'ans', 'word', 'gen', 'moe_lb', 'moe_top', 'moe_low')} if log else 'n/a',
                   accum=A.g(r, 'config', 'accum'))
        if key[1] == 'GX':
            blocks = A.g(r, 'extra', 'moe', 'blocks') or []
            rec['routing'] = [{k: b.get(k) for k in ('dead', 'top_share_x_even', 'share_min_x_even', 'share_max_x_even', 'n_in_half_to_double', 'entropy', 'round_overlap', 'bias')} for b in blocks] or 'n/a'
            bx = next((b for k, b in boxes.items() if k[1:] == key[:1] + (key[2],)), {})
            rec['box_active_params'] = A.g(bx, 'active_params')
        out[f'run {key[0]}/{key[1]}/s{key[2]}'] = rec
    return out


def analyze(runs, boxes=None, logs=None, seeds=SEEDS):
    return dict(seeds=list(seeds), stage1=stage1(runs, seeds), stage2=stage2(runs, seeds), reported=reported(runs, boxes or {}, logs or {}, seeds),
                present=sorted(f'{r}/{k}/s{s}' for r, k, s in runs))


def fmt(v):
    return 'n/a' if v is None else (f'{v:+.2f}' if isinstance(v, float) else str(v))


def show(res):
    for name in ('stage1', 'stage2'):
        st = res[name]
        print(f"{name}: readout {st['readout']}  (all marks pass: {st['pass_all']}; STOP cond {st['stop']}; proved wrong {st['proved_wrong']})")
        for m in st['marks']:
            print(f"  {m['id']}: " + '  '.join(f"s{s} {fmt(p['value'])} vs {p['thr']:g} {'ok' if p['ok'] else 'MISS'}" if p else f's{s} n/a' for s, p in m['per_seed'].items()))
        print('  X4:', st.get('X4') or st.get('D5_X4'), ' X5:', st['X5'], ' notes:', st['notes'])
    for k in ('GX3M_minus_B2_3M', 'GX3M_minus_B2_10M', 'GX3M_minus_PT_3M', 'GX10M_minus_B2_10M'):
        print(f"  {k}: mean {fmt(res['reported'][k]['mean'])} over {res['reported'][k]['n']} seed(s)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', nargs='+', required=True)
    ap.add_argument('--seeds', default=','.join(map(str, SEEDS)))
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    runs, boxes, logs, skipped = load(a.results)
    res = analyze(runs, boxes, logs, [int(x) for x in a.seeds.split(',')])
    res['skipped'] = skipped
    show(res)
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1, default=str)
    return res


if __name__ == '__main__':
    main()
