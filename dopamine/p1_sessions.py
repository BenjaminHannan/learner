"""P1 "session sheets": offline test of proactive helping (DESIGN-AND-MARKS-2026-10-10.md, B12; marks sealed there).

  python -m dopamine.p1_sessions cache --seed 200 --ckpt PATH --out DIR [--threads 2] [--smoke]
  python -m dopamine.p1_sessions sim --dir DIR [--helper menu|top1] [--tag P1]
P2 (B13): cache --sealed-seed 93003, sim --helper top1 --tag P2 (HELPER's V judges only the next-need head's top candidate).

A scripted person asks 2-4 sheet requests per session on one grid (3-4 rows, values 1-99). After each request the frozen
model may add one unasked "extra" from a menu of candidate formulas built on the same cells. Rewards: wanted (equals the
person's next request exactly) and right (model's greedy answer == tool value) +1; not wanted -0.25; wanted and wrong -1.
Person effort per session = L - sum(extra rewards). Arms NONE / EAGER / HELPER / ORACLE; heads: sklearn MLP (64, alpha
1e-3), N = next need, V = help value; refit after each day on all past days; frozen for the sealed sessions.

BUILDER (fixed before any run). A focus is (column c in {A,B}, rows r1..r2), length 2-4, inside the grid. Cells x, y =
the first two focus cells (c r1, c r1+1). One formula per kind:
  SUM/MAX/MIN/PRODUCT   KIND(c r1:c r2)
  COUNTIF               COUNTIF(c r1:c r1+1,">k"), k = (x+y)//2   (first 2 cells; deterministic threshold)
  cell arithmetic       x+y*2          (the help shape x+y*k, k=2)
  division              x/y
  MOD                   MOD(x,y)
  ABS                   ABS(x-y)
  IF                    IF(c r1>c' r1, c r2, c' r2), c' = the other column  (4 distinct cells, both columns, focus rows)
A candidate/request is dropped (redrawn) when the tool answer is '?', the prompt is over MAX_PROMPT, the answer over
MAX_ANS, the step count over N_RES (7), or the prompt has more than N_NUM numbers (caps from domain.tools, as panel.py).
Person: request 1 = random kind of 10 on a random focus. Later requests: with prob 0.6 the habit kind on the SAME focus
(SUM->MAX, MAX->MIN, MIN->SUM, PRODUCT->SUM, cell arithmetic->ABS, division->cell arithmetic, MOD->division, ABS->MOD,
COUNTIF->SUM, IF->MAX), else a random kind on a random focus; a '?' (or capped) request is redrawn (the whole choice).
Menu after request i = the builder's candidate of every kind on request i's focus ('?' dropped). Sessions depend only on
the person seed (93001 training, 93002 sealed) and the session index, never on the model.
"""
import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import warnings

import numpy as np

KINDS = ['SUM', 'MAX', 'MIN', 'PRODUCT', 'cell arithmetic', 'division', 'MOD', 'ABS', 'COUNTIF', 'IF']
HABIT = {'SUM': 'MAX', 'MAX': 'MIN', 'MIN': 'SUM', 'PRODUCT': 'SUM', 'cell arithmetic': 'ABS', 'division': 'cell arithmetic',
         'MOD': 'division', 'ABS': 'MOD', 'COUNTIF': 'SUM', 'IF': 'MAX'}
P_HABIT = 0.6
TRAIN_SEED, SEALED_SEED = 93001, 93002
DAYS, PER_DAY, N_SEALED = 6, 150, 400
R_RIGHT, R_UNWANTED, R_WRONG = 1.0, -0.25, -1.0


# ---------- builder ----------

def formula(kind, focus, n):
    """The builder's formula text for a kind on a focus (c, r1, r2). n = grid rows (unused by the rules, kept for clarity)."""
    c, r1, r2 = focus
    o = 'B' if c == 'A' else 'A'
    if kind in ('SUM', 'MAX', 'MIN', 'PRODUCT'):
        return f'{kind}({c}{r1}:{c}{r2})'
    x, y = f'{c}{r1}', f'{c}{r1 + 1}'
    if kind == 'COUNTIF':
        return f'COUNTIF({x}:{y},">K")'     # K filled in by prompt_for (needs the grid)
    if kind == 'cell arithmetic':
        return f'{x}+{y}*2'
    if kind == 'division':
        return f'{x}/{y}'
    if kind == 'MOD':
        return f'MOD({x},{y})'
    if kind == 'ABS':
        return f'ABS({x}-{y})'
    if kind == 'IF':
        return f'IF({c}{r1}>{o}{r1},{c}{r2},{o}{r2})'
    raise ValueError(kind)


def prompt_for(kind, focus, grid):
    """(prompt, tool answer) or None when '?' or a cap is broken."""
    from domain.tools import MAX_ANS, MAX_PROMPT, N_NUM, N_RES
    from domain.tools import sheet as sheet_tool
    f = formula(kind, focus, len(grid['A']))
    if kind == 'COUNTIF':
        c, r1, _ = focus
        k = (grid[c][r1 - 1] + grid[c][r1]) // 2
        f = f.replace('K', str(k))
    p = f"A: {' '.join(map(str, grid['A']))} | B: {' '.join(map(str, grid['B']))} ; ={f}"
    res = sheet_tool.evaluate(p)
    if res['value'] == '?' or len(p) > MAX_PROMPT or len(res['value']) > MAX_ANS or len(res['steps']) > N_RES:
        return None
    if len(re.findall(r'[0-9]+', p)) > N_NUM:
        return None
    return p, res['value']


def random_focus(rng, n):
    L = rng.randint(2, min(4, n))
    return (rng.choice('AB'), (r1 := rng.randint(1, n - L + 1)), r1 + L - 1)


def menu_for(focus, grid):
    return [(k, *pa) for k in KINDS if (pa := prompt_for(k, focus, grid)) is not None]


def make_session(person_seed, index):
    """One session: dict(grid, L, requests=[(kind, focus, prompt, value)], menus=[[(kind, prompt, value)] per request])."""
    rng = random.Random(person_seed * 1000003 + index)
    n = rng.choice([3, 4])
    grid = {c: [rng.randint(1, 99) for _ in range(n)] for c in 'AB'}
    L = rng.choice([2, 3, 4])
    reqs = []
    while len(reqs) < L:
        if reqs and rng.random() < P_HABIT:
            kind, focus = HABIT[reqs[-1][0]], reqs[-1][1]
        else:
            kind, focus = rng.choice(KINDS), random_focus(rng, n)
        pa = prompt_for(kind, focus, grid)
        if pa is None:
            continue
        reqs.append((kind, focus, pa[0], pa[1]))
    menus = [menu_for(r[1], grid) for r in reqs]
    return {'grid': grid, 'L': L, 'requests': reqs, 'menus': menus}


def all_sessions(smoke=False, sealed_seed=SEALED_SEED):
    """[(split, day, index_in_split, session)]; split 0 training (days 1..6), 1 sealed (day 0)."""
    days, per, sealed = (2, 10, 20) if smoke else (DAYS, PER_DAY, N_SEALED)
    out = []
    for d in range(days):
        for j in range(per):
            out.append((0, d + 1, d * per + j, make_session(TRAIN_SEED, d * per + j)))
    for j in range(sealed):
        out.append((1, 0, j, make_session(sealed_seed, j)))
    return out


# ---------- cache step ----------

def code_sha():
    return hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()


def log(msg, t0=[time.time()]):
    print(f'[{time.time() - t0[0]:8.1f}s] {msg}', flush=True)


def do_cache(a):
    import torch
    torch.set_num_threads(a.threads)
    from custom_io.models import load_model
    from domain.mode import greedy
    from dopamine.motivator import reader_features
    out = a.out
    os.makedirs(out, exist_ok=True)
    sess = all_sessions(a.smoke, a.sealed_seed)
    log(f'{len(sess)} sessions built')
    pid, prompts, value = {}, [], {}

    def P(p):
        if p not in pid:
            pid[p] = len(prompts)
            prompts.append(p)
        return pid[p]
    s_day, s_split, s_L = [], [], []
    r_sess, r_idx, r_cur, r_next = [], [], [], []
    c_ptr, c_pid, c_kind, c_wanted = [0], [], [], []
    cand_set = set()
    with open(os.path.join(out, 'sessions.jsonl'), 'w') as f:
        for si, (split, day, ix, s) in enumerate(sess):
            s_day.append(day), s_split.append(split), s_L.append(s['L'])
            for t, (req, menu) in enumerate(zip(s['requests'], s['menus'])):
                nxt = s['requests'][t + 1][2] if t + 1 < s['L'] else None
                r_sess.append(si), r_idx.append(t), r_cur.append(P(req[2])), r_next.append(P(nxt) if nxt else -1)
                for k, p, v in menu:
                    c_pid.append(P(p)), c_kind.append(KINDS.index(k)), c_wanted.append(int(p == nxt))
                    cand_set.add(p)
                    value[p] = v
                c_ptr.append(len(c_pid))
            f.write(json.dumps({'split': split, 'day': day, 'index': ix, 'L': s['L'], 'grid': s['grid'],
                                'requests': [[r[0], list(r[1]), r[2], r[3]] for r in s['requests']],
                                'menus': [[list(m) for m in mn] for mn in s['menus']]}) + '\n')
    log(f'{len(prompts)} distinct prompts, {len(cand_set)} distinct candidates, {len(c_pid)} menu entries, {len(r_sess)} rounds')
    ckpt_m = load_model(a.ckpt).eval()   # the saved checkpoints hold the add-on merged into the weights (= add-on on)
    # features for all distinct prompts, in order of first use, batch 128
    t = time.time()
    F = []
    for s in range(0, len(prompts), 128):
        F.append(reader_features(ckpt_m, prompts[s:s + 128]).astype(np.float32))
        if (s // 128) % 20 == 0:
            log(f'features {min(s + 128, len(prompts))}/{len(prompts)}  {time.time() - t:.0f}s')
    F = np.concatenate(F)
    tf = time.time() - t
    log(f'features done {F.shape} in {tf:.0f}s ({tf / len(prompts) * 1000:.1f} ms/prompt)')
    # greedy-answer correctness for every distinct candidate prompt
    cands = [p for p in prompts if p in cand_set]
    correct = np.full(len(prompts), -1, np.int8)
    t = time.time()
    for s in range(0, len(cands), 256):
        chunk = cands[s:s + 256]
        res = greedy(ckpt_m, chunk)
        for p, (_, ans) in zip(chunk, res):
            correct[pid[p]] = int(ans == value[p])
        if (s // 256) % 10 == 0:
            log(f'answers {min(s + 256, len(cands))}/{len(cands)}  {time.time() - t:.0f}s')
    tg = time.time() - t
    log(f'answers done {len(cands)} in {tg:.0f}s ({tg / len(cands) * 1000:.1f} ms per candidate answer); '
        f'overall right {correct[correct >= 0].mean():.3f}')
    np.savez_compressed(os.path.join(out, 'cache.npz'), prompts=np.array(prompts), feats=F, correct=correct,
                        sess_day=np.array(s_day), sess_split=np.array(s_split), sess_L=np.array(s_L),
                        round_sess=np.array(r_sess), round_idx=np.array(r_idx), round_cur=np.array(r_cur),
                        round_next=np.array(r_next), cand_ptr=np.array(c_ptr), cand_pid=np.array(c_pid),
                        cand_kind=np.array(c_kind), cand_wanted=np.array(c_wanted, np.int8),
                        seed=np.array(a.seed), ckpt=np.array(a.ckpt), smoke=np.array(bool(a.smoke)), sealed_seed=np.array(a.sealed_seed),
                        code_sha256=np.array(code_sha()))
    json.dump({'seed': a.seed, 'ckpt': a.ckpt, 'smoke': a.smoke, 'code_sha256': code_sha(), 'feature_secs': tf, 'answer_secs': tg,
               'n_candidate_answers': len(cands), 'n_prompts': len(prompts)}, open(os.path.join(out, 'cache_info.json'), 'w'))
    log('cache saved')


# ---------- sim step ----------

def reward(wanted, right):
    return (R_RIGHT if right else R_WRONG) if wanted else R_UNWANTED


def load_cache(d):
    z = np.load(os.path.join(d, 'cache.npz'))
    return {k: z[k] for k in z.files}


def onehot(idx):
    o = np.zeros((len(idx), 4), np.float32)
    o[np.arange(len(idx)), idx] = 1
    return o


def mlp(kind, seed):
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    cls = MLPClassifier if kind == 'clf' else MLPRegressor
    return make_pipeline(StandardScaler(), cls(hidden_layer_sizes=(64,), alpha=1e-3, random_state=seed, max_iter=200))


def simulate(Z, helper='menu'):
    from sklearn.exceptions import ConvergenceWarning
    warnings.simplefilter('ignore', ConvergenceWarning)
    F, correct = Z['feats'], Z['correct']
    R = len(Z['round_sess'])
    ptr, cpid, ckind, cwant = Z['cand_ptr'], Z['cand_pid'], Z['cand_kind'], Z['cand_wanted']
    n_per = np.diff(ptr)
    row_round = np.repeat(np.arange(R), n_per)            # candidate -> round
    ridx = Z['round_idx']
    sess_day = Z['sess_day']
    round_day = np.where(Z['sess_split'][Z['round_sess']] == 1, 0, sess_day[Z['round_sess']])
    cand_day = round_day[row_round]
    Xn = np.concatenate([F[Z['round_cur']][row_round], F[cpid], onehot(ridx[row_round])], 1)
    right = (correct[cpid] == 1)
    rew = np.where(cwant == 1, np.where(right, R_RIGHT, R_WRONG), R_UNWANTED)

    # decision for each arm in a set of rounds (given N probabilities pn for every candidate row, V values or None)
    def rows_of(r):
        return np.arange(ptr[r], ptr[r + 1])

    N_models, V_models = {}, {}
    taken = {'EAGER': {}, 'HELPER': {}}      # round -> candidate row
    helper_rows, helper_pn, helper_rew = [], [], []   # bandit data for V: candidate rows, N prob used, reward
    rs = {'EAGER': np.random.RandomState(11), 'HELPER': np.random.RandomState(12)}
    nfit = lambda mask, seed: mlp('clf', seed).fit(Xn[mask], cwant[mask])
    n_model = v_model = None
    for day in list(range(1, DAYS + 1)) + [0]:
        dr = np.where(round_day == day)[0]
        sealed = day == 0
        if len(dr) == 0:
            continue
        if n_model is not None:
            rows_d = np.where(cand_day == day)[0]
            pn_all = np.zeros(len(cwant))
            pn_all[rows_d] = n_model.predict_proba(Xn[rows_d])[:, 1] if len(n_model.classes_) == 2 else 0.0
        for r in dr:
            rr = rows_of(r)
            if len(rr) == 0:
                continue
            # EAGER
            if n_model is None:
                eg = rr[rs['EAGER'].randint(len(rr))]
            else:
                eg = rr[np.argmax(pn_all[rr])]
            taken['EAGER'][r] = eg
            # HELPER
            hp = None
            if n_model is None:   # day 1
                if rs['HELPER'].rand() < 0.5:
                    hp = rr[rs['HELPER'].randint(len(rr))]
                    helper_rows.append(hp), helper_pn.append(0.0), helper_rew.append(rew[hp])
            else:
                explore = (not sealed) and rs['HELPER'].rand() < 0.10
                if explore:
                    hp = rr[np.argmax(pn_all[rr])]
                elif v_model is not None and helper == 'top1':   # P2: V judges only N's top candidate
                    c0 = rr[np.argmax(pn_all[rr])]
                    Xv = np.concatenate([[[pn_all[c0]]], F[cpid[[c0]]], onehot(ridx[[r]])], 1)
                    if v_model.predict(Xv)[0] > 0:
                        hp = c0
                elif v_model is not None:
                    Xv = np.concatenate([pn_all[rr][:, None], F[cpid[rr]], onehot(ridx[[r] * len(rr)])], 1)
                    vv = v_model.predict(Xv)
                    j = int(np.argmax(vv))
                    if vv[j] > 0:
                        hp = rr[j]
                if hp is not None and not sealed:
                    helper_rows.append(hp), helper_pn.append(pn_all[hp]), helper_rew.append(rew[hp])
            if hp is not None:
                taken['HELPER'][r] = hp
        if sealed:
            break
        # refit heads after this day on all past days (N: every round; V: HELPER's own extras only)
        mask = (cand_day >= 1) & (cand_day <= day)
        n_model = nfit(mask, 100 + day)
        # N prob for the V training rows is the prob that was used when the extra was taken (stored in helper_pn)
        if len(helper_rows) >= 5:
            hr = np.array(helper_rows)
            Xv = np.concatenate([np.array(helper_pn)[:, None], F[cpid[hr]], onehot(ridx[row_round[hr]])], 1)
            v_model = mlp('reg', 200 + day).fit(Xv, np.array(helper_rew))
        # sealed pass uses these frozen heads; the loop continues to the next day (uses them for that day too)

    # sealed results
    sealed_sess = np.where(Z['sess_split'] == 1)[0]
    sdx = {s: i for i, s in enumerate(sealed_sess)}
    L = Z['sess_L'][sealed_sess].astype(float)
    arms = {a: np.zeros(len(sealed_sess)) for a in ['NONE', 'EAGER', 'HELPER', 'ORACLE']}
    stats = {a: {'extras': 0, 'wanted': 0, 'right': 0, 'unwanted': 0, 'last': 0, 'kinds': np.zeros(len(KINDS), int)}
             for a in ['EAGER', 'HELPER', 'ORACLE']}
    saving = {a: np.zeros(len(sealed_sess)) for a in arms}
    for r in np.where(round_day == 0)[0]:
        i = sdx[Z['round_sess'][r]]
        last = ridx[r] == Z['sess_L'][Z['round_sess'][r]] - 1
        for a in ['EAGER', 'HELPER']:
            c = taken[a].get(r)
            if c is None:
                continue
            saving[a][i] += rew[c]
            st = stats[a]
            st['extras'] += 1; st['wanted'] += int(cwant[c]); st['right'] += int(right[c])
            st['unwanted'] += int(not cwant[c]); st['last'] += int(last); st['kinds'][ckind[c]] += 1
        rr = rows_of(r)
        good = [c for c in rr if cwant[c] == 1 and right[c]]
        if good:
            c = good[0]
            saving['ORACLE'][i] += 1.0
            st = stats['ORACLE']
            st['extras'] += 1; st['wanted'] += 1; st['right'] += 1; st['kinds'][ckind[c]] += 1
    for a in arms:
        arms[a] = L - saving[a]
    return arms, stats, L


def boot(diff, n=10000, seed=0):
    rng = np.random.RandomState(seed)
    idx = rng.randint(0, len(diff), (n, len(diff)))
    m = diff[idx].mean(1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def do_sim(a):
    Z = load_cache(a.dir)
    t = time.time()
    arms, stats, L = simulate(Z, a.helper)
    T = a.tag
    S = len(L)
    res = {'test': T, 'helper_rule': a.helper, 'n_sealed_sessions': S, 'model_seed': int(Z['seed']), 'ckpt': str(Z['ckpt']),
           'sealed_seed': int(Z['sealed_seed']) if 'sealed_seed' in Z else SEALED_SEED,
           'smoke': bool(Z['smoke']) if 'smoke' in Z else None,
           'cache_code_sha256': str(Z['code_sha256']) if 'code_sha256' in Z else None,
           'mean_effort': {k: float(v.mean()) for k, v in arms.items()},
           'mean_L': float(L.mean())}
    d1, d2 = arms['HELPER'] - arms['NONE'], arms['HELPER'] - arms['EAGER']
    for name, d in (('HELPER-NONE', d1), ('HELPER-EAGER', d2)):
        lo, hi = boot(d)
        res[name] = {'diff': float(d.mean()), 'ci95': [lo, hi]}
    r1, r2 = res['HELPER-NONE'], res['HELPER-EAGER']
    lo1, hi1 = r1['ci95']
    res[f'{T}-1'] = {'verdict': 'PASS' if (r1['diff'] <= -0.05 and hi1 < 0) else
                   ('PROVED WRONG (on this seed)' if lo1 > 0 else 'neither pass nor wrong'),
                   'rule': 'pass: diff <= -0.05 and CI upper < 0; wrong: CI lower > 0 on either seed'}
    res[f'{T}-2'] = {'verdict': 'PASS' if (r2['diff'] <= -0.10 and r2['ci95'][1] < 0) else
                   ('wrong on this seed (diff >= 0; proved wrong only if also on the other seed)' if r2['diff'] >= 0
                    else 'neither pass nor wrong'),
                   'rule': 'pass: diff <= -0.10 and CI upper < 0; wrong: diff >= 0 on both seeds'}
    res['ORACLE_saving_per_session'] = float(L.mean() - arms['ORACLE'].mean())
    res['arms'] = {}
    for k, st in stats.items():
        e = max(st['extras'], 1)
        res['arms'][k] = {'extras': st['extras'], 'extras_per_session': st['extras'] / S,
                          'wanted_share': st['wanted'] / e, 'right_share': st['right'] / e,
                          'unwanted_share': st['unwanted'] / e, 'extras_on_last_request': st['last'],
                          'extras_per_kind': {KINDS[i]: int(st['kinds'][i]) for i in range(len(KINDS))}}
    res['p1_sessions_py_sha256'] = code_sha()
    res['sim_secs'] = round(time.time() - t, 1)
    json.dump(res, open(os.path.join(a.dir, 'RESULT.json'), 'w'), indent=1)
    md = [f"# {T} session sheets, model seed {res['model_seed']}, helper rule {a.helper}", '', f"checkpoint: {res['ckpt']}",
          f"sealed person seed: {res['sealed_seed']}",
          f"sealed sessions: {S}, mean requests per session {res['mean_L']:.3f}", '',
          '| Arm | mean effort (person actions / session) |', '|---|---|']
    md += [f'| {k} | {v:.4f} |' for k, v in res['mean_effort'].items()]
    md += ['', '| Paired difference | mean | 95% interval (10,000 resamples, seed 0) |', '|---|---|---|']
    for n in ('HELPER-NONE', 'HELPER-EAGER'):
        md.append(f"| {n} | {res[n]['diff']:+.4f} | [{res[n]['ci95'][0]:+.4f}, {res[n]['ci95'][1]:+.4f}] |")
    md += ['', f"{T}-1: {res[f'{T}-1']['verdict']}  ({res[f'{T}-1']['rule']})",
           f"{T}-2: {res[f'{T}-2']['verdict']}  ({res[f'{T}-2']['rule']})", '',
           f"ORACLE saving per session: {res['ORACLE_saving_per_session']:.4f}", '',
           '| Arm | extras/session | wanted | right | unwanted | extras on last request |', '|---|---|---|---|---|---|']
    for k, v in res['arms'].items():
        md.append(f"| {k} | {v['extras_per_session']:.3f} | {v['wanted_share']:.3f} | {v['right_share']:.3f} | "
                  f"{v['unwanted_share']:.3f} | {v['extras_on_last_request']} |")
    md += ['', 'Extras per kind (kind labels used for scoring only):', '', '| Kind | ' + ' | '.join(res['arms']) + ' |',
           '|---|' + '---|' * len(res['arms'])]
    for kd in KINDS:
        md.append(f'| {kd} | ' + ' | '.join(str(res['arms'][k]['extras_per_kind'][kd]) for k in res['arms']) + ' |')
    md += ['', f"p1_sessions.py sha256: {res['p1_sessions_py_sha256']}"]
    open(os.path.join(a.dir, 'RESULT.md'), 'w').write('\n'.join(md) + '\n')
    print('\n'.join(md))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('cache')
    c.add_argument('--seed', type=int, required=True)
    c.add_argument('--ckpt', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--threads', type=int, default=2)
    c.add_argument('--smoke', action='store_true')
    c.add_argument('--sealed-seed', type=int, default=SEALED_SEED)
    s = sub.add_parser('sim')
    s.add_argument('--dir', required=True)
    s.add_argument('--helper', choices=['menu', 'top1'], default='menu')
    s.add_argument('--tag', default='P1')
    a = ap.parse_args(argv)
    if a.cmd == 'cache':
        do_cache(a)
    else:
        do_sim(a)


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
