"""Multi-step creative puzzles: the dream-school experiment (design/v1/multistep/PREREG.md). Creative module only (no D, bridge or G1).

  python3 -m creative.multistep --b2 B2.pt --skills SKILLS_DIR --out OUT --device cuda --seeds 0 1 [--arms ...] [--parallel K] [--smoke]

Per seed: the SHARED part once (warm-up -> N' -> pool temperature, OUT/s{seed}/shared), then each arm (OUT/s{seed}/{arm}) in its own subprocess
(K at a time on one GPU) starting from the shared Nprime.pt / setup.json / train.json. After W2.pt: greedy first try by kind on creative dev + labelled
(never test), skills5 of W2 vs the base5 of setup. OUT/results.json = per-seed per-arm numbers, seed means, the PREREG verdict, kind_overlap disclosure.
Resumable: a finished arm (arm_result.json) is skipped; run_creative itself skips finished stages. `oracle` is REPORT-ONLY (not in the verdict)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HARD = ('affine', 'sq_plus', 'double_add')
EASY = ('square', 'last_digit')
SCHOOL_ARMS = ('school5', 'school5_strict', 'school5_curr')
OCCAM_ARMS = ('occam5', 'occam5_strict')
DEEP_ARMS = ('occam_deep',)
ARMS = ('base', 'dream2') + SCHOOL_ARMS + OCCAM_ARMS + DEEP_ARMS + ('oracle',)
FOUND_LENGTHS = (1, 2, 3, 4)
ROUND3_ARMS = ('base', 'occam_deep')
ROUND2_ARMS = ('base', 'occam5', 'occam5_strict', 'oracle')
OCCAM_SIZES = dict(lr=1e-3, visits=4)         # round 2 (PREREG): lr 1e-3, 4 visits
OCCAM_SHARDS = 128                             # fixed (not the core count): the cache key / stream must not depend on the box
OCCAM_LOSS_MARK = 2.0                          # mechanism line: school loss after the school must fall below this
REPORT_ONLY = ('oracle',)
SIZES = dict(school_n=40000, nightly=1000, visits=2, lr=3e-4)
REDUCED = dict(school_n=8000, nightly=300, max_steps=4)   # Mac fallback after the Vast budget cut (2026-10-24): smaller school, drawn programs <= 4 steps (5-step draws dominate generation time); disclosed in results.json
SMOKE = dict(school_n=60, nightly=20, updates_cap=2, pool_limit=64, dev_limit=16, n1=8, n2=16, T=1.0)
log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)


def arm_kwargs(arm: str, sizes: dict, cache: str | None = None, workers: int = 1) -> dict:
    """run_creative kwargs for an arm (PREREG table). sizes = SIZES or the smoke sizes."""
    from creative import sleep
    n, k = sizes['school_n'], sizes['nightly']
    ms = sizes.get('max_steps', 5)
    sch = dict(n=n, max_steps=ms, strict=False, curriculum=False, visits=SIZES['visits'], lr=SIZES['lr'], cache=cache, workers=workers)
    if arm == 'base':
        return {}
    if arm == 'dream2':
        return dict(dream2=k, dream2_max_steps=2)
    if arm == 'school5':
        return dict(school=sch, dream2=k, dream2_max_steps=5)
    if arm == 'school5_strict':
        return dict(school=dict(sch, strict=True), dream2=k, dream2_max_steps=5, dream2_strict=True)
    if arm == 'school5_curr':
        return dict(school=dict(sch, curriculum=True), dream2=k, dream2_max_steps=5)
    if arm == 'occam_deep':      # round 3: school dealt by FOUND length 1-4 (10,000 each), strict; nightly dreams as occam5_strict (drawn-length dealt)
        oc = dict(sch, occam=True, strict=True, found_lengths=FOUND_LENGTHS, shards=OCCAM_SHARDS if sizes is SIZES else 8, **OCCAM_SIZES)
        return dict(school=oc, dream2=k, dream2_max_steps=ms, dream2_occam=True, dream2_strict=True)
    if arm in OCCAM_ARMS:
        oc = dict(sch, occam=True, strict=(arm == 'occam5_strict'), shards=OCCAM_SHARDS if sizes is SIZES else 8, **OCCAM_SIZES)
        return dict(school=oc, dream2=k, dream2_max_steps=ms, dream2_occam=True, **(dict(dream2_strict=True) if arm == 'occam5_strict' else {}))
    if arm == 'oracle':       # report only: pool reference programs, update count matched to school5's, no nightly dreams
        return dict(school=dict(oracle=True, updates=sleep.max_updates(n, 64, True, SIZES['visits']), lr=SIZES['lr'], visits=SIZES['visits']))
    raise KeyError(arm)


def smoke_kwargs(sizes: dict) -> dict:
    return {x: sizes[x] for x in ('updates_cap', 'pool_limit', 'dev_limit', 'n1', 'n2', 'T') if x in sizes}


# ---------------- evaluation ----------------
def evaluate_w2(path: str, skills_data: str, device: str, limit=None) -> dict:
    """Greedy first try by kind on creative dev + labelled (pooled counts), plus skills5 of the model."""
    from creative import fastsleep, sleep
    from v1 import creative_sleep as CS
    rs = {s: CS.dev_report(path, device, limit=limit, split=s) for s in ('dev', 'labelled')}
    kinds = sorted(set(rs['dev']['by_kind']) | set(rs['labelled']['by_kind']))
    n_by = {k: sum(r['n_by_kind'].get(k, 0) for r in rs.values()) for k in kinds}
    right = {k: sum(r['by_kind'].get(k, 0) * r['n_by_kind'].get(k, 0) for r in rs.values()) for k in kinds}
    by_kind = {k: right[k] / n_by[k] for k in kinds}
    m, _, _ = sleep.load_parent(path, device)
    return dict(by_kind=by_kind, n_by_kind=n_by, dev_by_kind=rs['dev']['by_kind'], labelled_by_kind=rs['labelled']['by_kind'],
                hard=mean_of(by_kind, HARD), easy=mean_of(by_kind, EASY), skills5=fastsleep.skills5(m, skills_data, device) if skills_data else None)


def mean_of(by_kind: dict, kinds) -> float:
    v = [by_kind[k] for k in kinds if k in by_kind]
    return sum(v) / len(v) if v else float('nan')


# ---------------- verdict ----------------
def verdict(arms: dict) -> dict:
    """PREREG pass marks, mechanically. arms = {arm: dict(hard, easy, harm)} seed means as FRACTIONS (harm = base5 - skills5 of W2, fraction); points = x100.
    oracle / dream2 are not part of the verdict. -> dict(lines, pass, not_leakage, curriculum_helps, proved_wrong, gains)."""
    pts = lambda x: round(100.0 * x, 9)
    b = arms['base']
    gain = {a: pts(arms[a]['hard'] - b['hard']) for a in SCHOOL_ARMS if a in arms}
    out = dict(gains_hard_points=gain, lines=[])
    ok = {}
    for a in SCHOOL_ARMS:
        if a not in arms:
            continue
        x = arms[a]
        ok[a] = dict(hard_ge_15=pts(x['hard']) >= 15, hard_ge_base_plus_10=gain[a] >= 10, easy_ok=pts(x['easy']) >= pts(b['easy']) - 5, harm_ok=pts(x['harm']) <= 2)
    passed = [a for a, c in ok.items() if all(c.values())]
    out['pass_detail'] = ok
    out['pass'] = bool(passed)
    out['lines'].append(('PASS: ' + ', '.join(passed)) if passed else 'NO PASS: no school arm has Hard >= 15% and >= base + 10 points with Easy within 5 and skills harm <= 2 points')
    if 'school5' in gain and 'school5_strict' in gain:
        if gain['school5'] > 0:
            nl = gain['school5_strict'] >= 0.5 * gain['school5']
            out['not_leakage'] = nl
            out['lines'].append(f"{'NOT LEAKAGE' if nl else 'LEAKAGE SUSPECTED (gain mostly from seeing held-out forms in dreams, not generalisation)'}: strict gain {gain['school5_strict']:.1f} vs school5 gain {gain['school5']:.1f} points")
        else:
            out['not_leakage'] = None
            out['lines'].append(f"LEAKAGE CHECK n/a: school5 has no Hard gain over base ({gain['school5']:.1f} points)")
    if 'school5' in arms and 'school5_curr' in arms:
        ch = pts(arms['school5_curr']['hard'] - arms['school5']['hard']) >= 5
        out['curriculum_helps'] = ch
        out['lines'].append(('CURRICULUM HELPS' if ch else 'NO SHOWN EFFECT OF ORDERING') + f": curr Hard {pts(arms['school5_curr']['hard']):.1f} vs school5 {pts(arms['school5']['hard']):.1f}")
    if gain:
        pw = all(g <= 3 for g in gain.values())
        out['proved_wrong'] = pw
        if pw:
            out['lines'].append('PROVED WRONG: every school arm has Hard <= base + 3 points')
    if 'dream2' in arms:
        out['lines'].append(f"dream2 vs base (report only): Hard {pts(arms['dream2']['hard'] - b['hard']):+.1f} points")
    if 'oracle' in arms:
        out['lines'].append(f"oracle (REPORT ONLY, not in the verdict; uses the answer key's kind/params): Hard {pts(arms['oracle']['hard']):.1f}%")
    return out


def verdict_round2(arms: dict, school_loss: dict | None = None) -> dict:
    """PREREG Round 2 marks, mechanically. arms = {arm: dict(hard, easy, harm)} seed means (fractions); school_loss = {arm: final school loss (mean over seeds)} (the mechanism line).
    PASS: occam5_strict Hard >= base + 10 points AND >= 20%, Easy within 5 of base, harm <= 2 points. Not leakage: occam5_strict keeps >= half of occam5's gain.
    Proved wrong: occam5_strict Hard <= base + 3. Mechanism: school loss < 2.0, else the arm did not learn its dreams. oracle is report only."""
    pts = lambda x: round(100.0 * x, 9)
    b = arms['base']
    gain = {a: pts(arms[a]['hard'] - b['hard']) for a in OCCAM_ARMS if a in arms}
    out = dict(gains_hard_points=gain, lines=[])
    if 'occam5_strict' in arms:
        x = arms['occam5_strict']
        c = dict(hard_ge_base_plus_10=gain['occam5_strict'] >= 10, hard_ge_20=pts(x['hard']) >= 20, easy_ok=pts(x['easy']) >= pts(b['easy']) - 5, harm_ok=pts(x['harm']) <= 2)
        out['pass_detail'], out['pass'] = c, all(c.values())
        out['lines'].append(('PASS: occam5_strict' if out['pass'] else 'NO PASS: occam5_strict') + f" (Hard {pts(x['hard']):.1f}% = base {pts(b['hard']):.1f} + {gain['occam5_strict']:.1f}; Easy {pts(x['easy']):.1f} vs base {pts(b['easy']):.1f}; harm {pts(x['harm']):.1f} pts; failed: {[k for k, v in c.items() if not v]})")
        out['proved_wrong'] = gain['occam5_strict'] <= 3
        if out['proved_wrong']:
            out['lines'].append('PROVED WRONG: occam5_strict Hard <= base + 3 points')
        if 'occam5' in gain:
            if gain['occam5'] > 0:
                nl = gain['occam5_strict'] >= 0.5 * gain['occam5']
                out['not_leakage'] = nl
                out['lines'].append(f"{'NOT LEAKAGE' if nl else 'LEAKAGE SUSPECTED'}: strict gain {gain['occam5_strict']:.1f} vs occam5 gain {gain['occam5']:.1f} points")
            else:
                out['not_leakage'] = None
                out['lines'].append(f"LEAKAGE CHECK n/a: occam5 has no Hard gain over base ({gain['occam5']:.1f} points)")
    if school_loss:
        mech = {a: (l is not None and l < OCCAM_LOSS_MARK) for a, l in school_loss.items()}
        out['school_loss'], out['mechanism_learned'] = school_loss, mech
        for a, l in school_loss.items():
            out['lines'].append(f"MECHANISM {a}: school loss {l if l is None else round(l, 3)} -> " + ('learned its dreams (< 2.0)' if mech[a] else 'DID NOT LEARN ITS DREAMS (>= 2.0)'))
    if 'oracle' in arms:
        out['lines'].append(f"oracle (REPORT ONLY): Hard {pts(arms['oracle']['hard']):.1f}%")
    return out


def verdict_round3(arms: dict, school_loss: dict | None = None, compare: dict | None = None) -> dict:
    """PREREG Round 3, mechanically. arms = {arm: dict(hard, easy, harm)} seed means (fractions). PASS: occam_deep Hard >= base + 10 points AND >= 20%, Easy within 5, harm <= 2.
    Depth helps: occam_deep Hard >= occam5_strict Hard + 5 (occam5_strict from round 2: compare = dict(hard=fraction) or None -> n/a). Proved wrong: occam_deep Hard <= base + 3.
    Mechanism: school loss < 2.0."""
    pts = lambda x: round(100.0 * x, 9)
    b, x = arms['base'], arms['occam_deep']
    gain = pts(x['hard'] - b['hard'])
    c = dict(hard_ge_base_plus_10=gain >= 10, hard_ge_20=pts(x['hard']) >= 20, easy_ok=pts(x['easy']) >= pts(b['easy']) - 5, harm_ok=pts(x['harm']) <= 2)
    out = dict(gain_hard_points=gain, pass_detail=c, **{'pass': all(c.values())}, proved_wrong=gain <= 3, lines=[])
    out['lines'].append(('PASS: occam_deep' if out['pass'] else 'NO PASS: occam_deep') + f" (Hard {pts(x['hard']):.1f}% = base {pts(b['hard']):.1f} + {gain:.1f}; Easy {pts(x['easy']):.1f} vs base {pts(b['easy']):.1f}; harm {pts(x['harm']):.1f} pts; failed: {[k for k, v in c.items() if not v]})")
    if out['proved_wrong']:
        out['lines'].append('PROVED WRONG: occam_deep Hard <= base + 3 points')
    if compare and compare.get('hard') is not None:
        dh = pts(x['hard'] - compare['hard']) >= 5
        out['depth_helps'] = dh
        out['lines'].append(('DEPTH HELPS' if dh else 'DEPTH DOES NOT HELP (< +5)') + f": occam_deep Hard {pts(x['hard']):.1f}% vs round-2 occam5_strict {pts(compare['hard']):.1f}%")
    else:
        out['depth_helps'] = None
        out['lines'].append('DEPTH HELPS: n/a (no round-2 occam5_strict result given; pass --compare round2/results.json)')
    if school_loss:
        out['school_loss'], out['mechanism_learned'] = school_loss, {a: (l is not None and l < OCCAM_LOSS_MARK) for a, l in school_loss.items()}
        for a, l in school_loss.items():
            out['lines'].append(f"MECHANISM {a}: school loss {l if l is None else round(l, 3)} -> " + ('learned its dreams (< 2.0)' if out['mechanism_learned'][a] else 'DID NOT LEARN ITS DREAMS (>= 2.0)'))
    return out


def aggregate(per_seed: dict) -> dict:
    """{seed: {arm: eval dict}} -> {arm: dict(per_seed, mean)}."""
    arms = sorted({a for s in per_seed.values() for a in s}, key=ARMS.index)
    out = {}
    for a in arms:
        rs = {s: v[a] for s, v in per_seed.items() if a in v}
        kinds = sorted({k for r in rs.values() for k in r['by_kind']})
        mean = dict(by_kind={k: sum(r['by_kind'][k] for r in rs.values()) / len(rs) for k in kinds},
                    hard=sum(r['hard'] for r in rs.values()) / len(rs), easy=sum(r['easy'] for r in rs.values()) / len(rs),
                    harm=sum(r['base5'] - r['skills5'] for r in rs.values()) / len(rs) if all(r.get('skills5') is not None for r in rs.values()) else 0.0,
                    n_seeds=len(rs))
        out[a] = dict(per_seed=rs, mean=mean, report_only=a in REPORT_ONLY)
    return out


# ---------------- worker (one arm of one seed) ----------------
def worker(a):
    from v1 import creative_sleep as CS
    cfg = json.load(open(a.cfg))
    d = a.arm_dir
    t0 = time.time()
    info = CS.run_creative(d, cfg['b2'], os.path.join(cfg['skills'], 'train.jsonl'), cfg['skills'], device=cfg['device'], seed=cfg['seed'], **cfg['kwargs'])
    # the final model: W2; if a night found no W records (the pipeline stops, e.g. a tiny smoke model) the latest model that exists, recorded in 'model'
    model = next((f for f in ('W2.pt', 'W1.pt', 'school.pt', 'Nprime.pt') if os.path.exists(os.path.join(d, f))), None)
    ev = evaluate_w2(os.path.join(d, model), cfg['skills'], cfg['device'], limit=cfg['kwargs'].get('dev_limit'))
    ev['model'], ev['stop'] = model, info.get('stop')
    ev['base5'] = json.load(open(os.path.join(d, 'setup.json')))['base5']
    ev['skills_harm_pts'] = round(100 * (ev['base5'] - ev['skills5']), 2) if ev['skills5'] is not None and ev['base5'] is not None else None
    ev['seconds'] = round(time.time() - t0, 1)
    ev['school'] = info.get('school')
    json.dump(ev, open(os.path.join(d, 'arm_result.json'), 'w'), indent=1, default=float)
    log('ARM DONE', d, 'hard', round(ev['hard'], 4), 'easy', round(ev['easy'], 4))


# ---------------- driver ----------------
def shared_part(root: str, seed: int, a, kw: dict):
    from v1 import creative_sleep as CS
    d = os.path.join(root, f's{seed}', 'shared')
    if os.path.exists(os.path.join(d, 'setup.json')):
        log('shared done', d)
        return d
    log('shared part: warm-up, N\', setup', d)
    CS.run_creative(d, a.b2, os.path.join(a.skills, 'train.jsonl'), a.skills, device=a.device, seed=seed, stop_after='setup', **kw)
    return d


def pregen(root: str, seed: int, arms, sizes: dict, kw: dict, workers: int, cache: str):
    """Generate (and cache on disk) the school dreams of the school arms once per seed, and the kind_overlap disclosure of each set."""
    from creative import dream2 as D, c2_stones, rules_real as R
    from v1 import creative_sleep as CS
    pool = c2_stones._with_nums(R.load_split(D.DATA, 'pool')[:kw.get('pool_limit')])
    avoid = [r['prompt'] for r in pool]
    over = {}
    for arm in [x for x in arms if x in SCHOOL_ARMS + OCCAM_ARMS + DEEP_ARMS]:
        sch = arm_kwargs(arm, sizes, cache=cache, workers=workers)['school']
        rows = []
        for night, mx, k in CS.school_plan(sch):
            t0 = time.time()
            st = {}
            rows += D.dream_rows_par(k, seed, avoid, night=night, max_steps=mx, strict=sch['strict'], shards=sch.get('shards', 8), workers=workers, stats=st, cache_dir=cache, occam=bool(sch.get('occam')), found_lengths=sch.get('found_lengths'))
            if sch.get('occam'):
                log(f'occam {arm}: dropped', sum(v['occam_dropped'] for v in st.values()), 'found-length counts', {k_: sum(v[k_] for v in st.values()) for k_ in st[1] if k_.startswith('found_')})
            log(f'dreams {arm} night {night} max_steps {mx} n {k}: {time.time() - t0:.0f}s; accept rate per length', {L: round(v['accepted'] / max(v['draws'], 1), 5) for L, v in st.items()})
        over[arm] = D.kind_overlap(rows)
        log('kind_overlap', arm, {k: v for k, v in over[arm].items() if k in ('n', 'any_held_out_same_function')})
    return over


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--b2'), ap.add_argument('--skills'), ap.add_argument('--out')
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--seeds', type=int, nargs='+', default=[0, 1])
    ap.add_argument('--arms', nargs='+', default=None, choices=ARMS)
    ap.add_argument('--round', type=int, default=1, choices=(1, 2, 3), help='2 = the Occam round: arms base occam5 occam5_strict oracle, round-2 verdict; 3 = depth-balanced Occam: base + occam_deep')
    ap.add_argument('--compare', default=None, help='round 3: round 2 results.json (for the depth-helps line: its occam5_strict Hard)')
    ap.add_argument('--parallel', type=int, default=1)
    ap.add_argument('--threads', type=int, default=2, help='OMP threads per arm subprocess')
    ap.add_argument('--cache-dir', default=None, help='dream cache (default OUT/s<seed>/dreams); keep it out of the exported out/ tree')
    ap.add_argument('--smoke', action='store_true')
    ap.add_argument('--reduced', action='store_true', help='Mac fallback sizes (REDUCED); every arm alike')
    ap.add_argument('--worker', action='store_true'), ap.add_argument('--cfg'), ap.add_argument('--arm-dir')
    a = ap.parse_args()
    if a.worker:
        return worker(a)
    sizes = {**SIZES, **(REDUCED if a.reduced else {}), **(SMOKE if a.smoke else {})}
    kw = smoke_kwargs(sizes) if a.smoke else {}
    root = os.path.abspath(a.out)
    os.makedirs(root, exist_ok=True)
    r2 = a.round == 2
    r3 = a.round == 3
    arms = [x for x in ARMS if x in (a.arms or (ROUND3_ARMS if a.round == 3 else ROUND2_ARMS if r2 else ARMS))]
    ncpu = os.cpu_count() or 1
    per_seed, overlap, failed = {}, {}, []
    for seed in a.seeds:
        shared = shared_part(root, seed, a, kw)
        cache = a.cache_dir or os.path.join(root, f's{seed}', 'dreams')
        overlap[str(seed)] = pregen(root, seed, arms, sizes, kw, ncpu, cache)
        todo, running = [], []
        for arm in arms:
            d = os.path.join(root, f's{seed}', arm)
            if os.path.exists(os.path.join(d, 'arm_result.json')) and 'failed' not in json.load(open(os.path.join(d, 'arm_result.json'))):
                log('skip finished', seed, arm)
                continue
            os.makedirs(d, exist_ok=True)
            for f in ('Nprime.pt', 'setup.json', 'train.json', 'dev_floors.json'):
                if os.path.exists(os.path.join(shared, f)) and not os.path.exists(os.path.join(d, f)):
                    shutil.copy(os.path.join(shared, f), d)
            cfgp = os.path.join(d, 'arm_cfg.json')
            json.dump(dict(b2=os.path.abspath(a.b2), skills=os.path.abspath(a.skills), device=a.device, seed=seed, kwargs={**kw, **arm_kwargs(arm, sizes, cache=cache)}), open(cfgp, 'w'), indent=1)
            todo.append((arm, d, cfgp))
        while todo or running:
            while todo and len(running) < a.parallel:
                arm, d, cfgp = todo.pop(0)
                log('launch', seed, arm)
                env = dict(os.environ, OMP_NUM_THREADS=str(a.threads), MKL_NUM_THREADS=str(a.threads), PYTHONHASHSEED='0')
                p = subprocess.Popen([sys.executable, '-m', 'creative.multistep', '--worker', '--cfg', cfgp, '--arm-dir', d], stdout=open(os.path.join(d, 'log.txt'), 'a'), stderr=subprocess.STDOUT, env=env)
                running.append((arm, p))
            time.sleep(2)
            for arm, p in list(running):
                if p.poll() is not None:
                    running.remove((arm, p))
                    log('arm finished', seed, arm, 'rc', p.returncode)
        for arm in arms:
            f = os.path.join(root, f's{seed}', arm, 'arm_result.json')
            if os.path.exists(f):
                r = json.load(open(f))
                if 'failed' not in r:
                    per_seed.setdefault(seed, {})[arm] = r
                else:
                    failed.append(dict(seed=seed, arm=arm, **r))
    agg = aggregate(per_seed)
    res = dict(prereg='design/v1/multistep/PREREG.md', round=a.round, smoke=a.smoke, seeds=a.seeds, sizes=sizes, hard_kinds=HARD, easy_kinds=EASY, arms=agg, kind_overlap=overlap,
               report_only_arms=list(REPORT_ONLY), failed_arms=failed)
    if (r2 or r3) and 'base' in agg and any(x in agg for x in OCCAM_ARMS + DEEP_ARMS):
        sl = {}
        for ar in OCCAM_ARMS + DEEP_ARMS:
            if ar in agg:
                v = [r['school']['phases'][-1]['final_loss'] for r in agg[ar]['per_seed'].values() if r.get('school') and r['school'].get('phases') and r['school']['phases'][-1].get('final_loss') is not None]
                sl[ar] = sum(v) / len(v) if v else None
        am = {k: dict(hard=v['mean']['hard'], easy=v['mean']['easy'], harm=v['mean']['harm']) for k, v in agg.items()}
        if r3 and 'occam_deep' in am:
            cmp_ = None
            if a.compare and os.path.exists(a.compare):
                cmp_ = dict(hard=json.load(open(a.compare))['arms']['occam5_strict']['mean']['hard'])
            res['verdict'] = verdict_round3(am, sl, cmp_)
        else:
            res['verdict'] = verdict_round2(am, sl)
    elif 'base' in agg and any(x in agg for x in SCHOOL_ARMS):
        res['verdict'] = verdict({k: dict(hard=v['mean']['hard'], easy=v['mean']['easy'], harm=v['mean']['harm']) for k, v in agg.items()})
    json.dump(res, open(os.path.join(root, 'results.json'), 'w'), indent=1, default=float)
    log('RESULTS', os.path.join(root, 'results.json'))
    for l in res.get('verdict', {}).get('lines', []):
        log('VERDICT', l)


if __name__ == '__main__':
    main()
