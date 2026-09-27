#!/usr/bin/env python3
"""Blind recount of rsn-358e5 from raw result.json files and the sealed marks only."""
import json, os
from statistics import mean

R = '/home/user/learner/artifacts'
SEEDS = range(3, 9)
TASKS = ['grids5', 'grids6', 'sums4', 'sums6', 'maze7']
FIELDS = ['right', 'r16', 'any']

def load(p):
    with open(p) as f:
        return json.load(f)

warm = {s: load(f'{R}/claude-rsn358e5-20260927/runs/eq-replayall-warm-s{s}/result.json') for s in SEEDS}
eq = {s: load(f'{R}/claude-rsn358e4-20260927/runs/eq-replayall-s{s}/result.json') for s in SEEDS}
dense = {s: load(f'{R}/claude-rsn358e4-20260927/runs/dense-replayall-s{s}/result.json') for s in SEEDS}
ARMS = [('warm', warm, 'eq-replayall-warm'), ('eq', eq, 'eq-replayall'), ('dense', dense, 'dense-replayall')]

def sc(d, phase, task, field='right'):
    return d['phases'][phase][task][field]

print('=' * 70)
print('1. INTEGRITY')
print('=' * 70)
issues = []
for name, D, want_arm in ARMS:
    for s in SEEDS:
        d = D[s]
        ok = d['arm'] == want_arm and d['seed'] == s
        if not ok:
            issues.append(f'{name} s{s}: arm/seed mismatch {d["arm"]} {d["seed"]}')
        print(f'{name:5s} s{s}: arm={d["arm"]:18s} seed={d["seed"]} size={d.get("size")} weights={d["weights"]} '
              f'torch={d["torch"]} device={d["device"]} minutes={d.get("minutes")} phases={list(d["phases"].keys())}')
print()
print('forced_batches (warm; marks say sums 225 after B, sums 225 + mazes 135 after C):')
for s in SEEDS:
    fb_b = warm[s]['phases']['after_sums'].get('forced_batches')
    fb_c = warm[s]['phases']['after_mazes'].get('forced_batches')
    good = fb_c == {'sums': 225, 'mazes': 135}
    if not good:
        issues.append(f'warm s{s}: forced_batches after C = {fb_c}')
    print(f'  s{s}: after B={fb_b}  after C={fb_c}  {"OK" if good else "MISMATCH"}')
for name, D, _ in [('eq', eq, 0), ('dense', dense, 0)]:
    has = [s for s in SEEDS if any('forced_batches' in D[s]['phases'][p] for p in D[s]['phases'])]
    print(f'  {name}: forced_batches key present in seeds {has} (expected none)')
print()
print('replayed counts (after B / after C), replayed_batches field:')
for name, D, _ in ARMS:
    for s in SEEDS:
        pb, pc = D[s]['phases']['after_sums'], D[s]['phases']['after_mazes']
        print(f'  {name:5s} s{s}: B replayed={pb.get("replayed")} replayed_batches={pb.get("replayed_batches")} | '
              f'C replayed={pc.get("replayed")} replayed_batches={pc.get("replayed_batches")}')
# replay equality warm vs eq
rep_eq = all(warm[s]['phases'][p].get('replayed') == eq[s]['phases'][p].get('replayed')
             for s in SEEDS for p in ['after_sums', 'after_mazes'])
print(f'  warm replayed counts identical to eq on every seed and phase: {rep_eq}')
print('weights warm == eq on every seed:', all(warm[s]['weights'] == eq[s]['weights'] for s in SEEDS))
print('integrity issues:', issues or 'none')

print()
print('=' * 70)
print('2. REPRO: after-A (after_grids) dev scores, warm vs 358e4 eq-replayall')
print('=' * 70)
repro_all = True
for s in SEEDS:
    diffs = []
    for t in TASKS:
        for f in FIELDS:
            a, b = sc(warm[s], 'after_grids', t, f), sc(eq[s], 'after_grids', t, f)
            if a != b:
                diffs.append(f'{t}.{f}: {a} vs {b}')
    es_same = warm[s]['phases']['after_grids'].get('expert_share') == eq[s]['phases']['after_grids'].get('expert_share')
    tv = warm[s]['torch'] == eq[s]['torch']
    dv = warm[s]['device'] == eq[s]['device']
    ok = not diffs
    repro_all &= ok
    right = ' '.join(f'{t}={sc(warm[s], "after_grids", t)}' for t in TASKS)
    print(f'  s{s}: scores identical (15 values: right/r16/any x 5 tasks)={ok} {diffs or ""} | '
          f'after-A expert_share identical={es_same} | torch match={tv} ({warm[s]["torch"]} / {eq[s]["torch"]}) device match={dv}')
    print(f'       warm after-A right: {right}')
torch_all = all(warm[s]['torch'] == eq[s]['torch'] == '2.14.0+cu130' for s in SEEDS)
print(f'REPRO scores: {repro_all}; torch 2.14.0+cu130 on all warm and eq files: {torch_all}')
print('  (same container cannot be checked from result.json; only torch/device are recorded)')
REPRO = repro_all and torch_all

print()
print('=' * 70)
print('3. M: new-group share (sum of experts 4-7 for sums4 after B; 8-11 for maze7 after C), per block')
print('=' * 70)
def group_share(d, phase, task, lo, hi):
    return [round(sum(block[lo:hi + 1]), 4) for block in d['phases'][phase]['expert_share'][task]]
m_seeds = 0
m_rows = {}
for s in SEEDS:
    sb = group_share(warm[s], 'after_sums', 'sums4', 4, 7)
    mc = group_share(warm[s], 'after_mazes', 'maze7', 8, 11)
    okb = any(x >= 0.05 for x in sb)
    okc = any(x >= 0.05 for x in mc)
    ok = okb and okc
    m_seeds += ok
    m_rows[s] = (sb, mc, ok)
    print(f'  s{s}: sums4 after B blocks={sb} ({okb}) | maze7 after C blocks={mc} ({okc}) -> seed meets M: {ok}')
M = m_seeds >= 5
print(f'M: {m_seeds} of 6 seeds meet the 5% rule; need >= 5 -> {M}')
print('  for comparison, 358e4 eq-replayall on the same measure:')
e4_m = 0
for s in SEEDS:
    sb = group_share(eq[s], 'after_sums', 'sums4', 4, 7)
    mc = group_share(eq[s], 'after_mazes', 'maze7', 8, 11)
    ok = any(x >= 0.05 for x in sb) and any(x >= 0.05 for x in mc)
    e4_m += ok
    print(f'    eq s{s}: sums4 B={sb} maze7 C={mc} -> {ok}')
print(f'    eq seeds meeting rule: {e4_m} of 6')
print('  full expert_share lists (warm):')
for s in SEEDS:
    print(f'    s{s} sums4 after B: {warm[s]["phases"]["after_sums"]["expert_share"]["sums4"]}')
    print(f'    s{s} maze7 after C: {warm[s]["phases"]["after_mazes"]["expert_share"]["maze7"]}')

print()
print('=' * 70)
print('4. N = sums4 after B + maze7 after C (right, of 400)')
print('=' * 70)
def N(d):
    return sc(d, 'after_sums', 'sums4') + sc(d, 'after_mazes', 'maze7')
Nw = {s: N(warm[s]) for s in SEEDS}
Ne = {s: N(eq[s]) for s in SEEDS}
for s in SEEDS:
    print(f'  s{s}: warm = {sc(warm[s], "after_sums", "sums4")} + {sc(warm[s], "after_mazes", "maze7")} = {Nw[s]:3d} | '
          f'eq = {sc(eq[s], "after_sums", "sums4")} + {sc(eq[s], "after_mazes", "maze7")} = {Ne[s]:3d} | diff {Nw[s] - Ne[s]:+d}')
mw, me = mean(Nw.values()), mean(Ne.values())
gap = mw - me
n_gt = sum(Nw[s] > Ne[s] for s in SEEDS)
n_le10 = sum(Nw[s] <= Ne[s] + 10 for s in SEEDS)
print(f'  mean N_warm = {mw:.2f}, mean N_eq = {me:.2f}, gap = {gap:+.2f}')
print(f'  seeds N_warm > N_eq: {n_gt} of 6; seeds N_warm <= N_eq + 10: {n_le10} of 6')

print()
print('=' * 70)
print('5. VERDICT (marks in order: REPRO, M, PASS, proved wrong, else FAIL)')
print('=' * 70)
print(f'  REPRO: every after-A score equal on every seed = {repro_all}; torch 2.14.0+cu130 both = {torch_all} -> {REPRO}')
print(f'  M: {m_seeds}/6 seeds >= 5% in both (need 5) -> {M}')
pass1 = mw >= me + 50
pass2 = n_gt >= 5
PASS = pass1 and pass2
print(f'  PASS (a): mean N_warm {mw:.2f} >= mean N_eq + 50 = {me + 50:.2f} -> {pass1}')
print(f'  PASS (b): N_warm > N_eq on {n_gt}/6 (need 5) -> {pass2}')
pw1 = mw <= me + 10
pw2 = n_le10 >= 5
PW = M and pw1 and pw2
print(f'  Proved wrong: M={M}; mean N_warm {mw:.2f} <= mean N_eq + 10 = {me + 10:.2f} -> {pw1}; '
      f'N_warm <= N_eq + 10 on {n_le10}/6 (need 5) -> {pw2} -> {PW}')
if not REPRO:
    verdict = 'INCONCLUSIVE (REPRO failed)'
elif not M:
    verdict = 'INCONCLUSIVE ("warm routing did not route")'
elif PASS:
    verdict = 'PASS'
elif PW:
    verdict = 'PROVED WRONG'
else:
    verdict = 'FAIL'
print(f'  VERDICT: {verdict}')

print()
print('=' * 70)
print('6. REPORT ONLY (never graded)')
print('=' * 70)
def T(d):
    return sum(sc(d, 'after_mazes', t) for t in ['grids5', 'sums4', 'maze7'])
Tw = {s: T(warm[s]) for s in SEEDS}
Td = {s: T(dense[s]) for s in SEEDS}
Te = {s: T(eq[s]) for s in SEEDS}
for s in SEEDS:
    print(f'  s{s}: T warm={Tw[s]} eq={Te[s]} dense={Td[s]} | warm-dense {Tw[s] - Td[s]:+d}')
mtw, mtd, mte = mean(Tw.values()), mean(Td.values()), mean(Te.values())
t_hi = sum(Tw[s] > Td[s] for s in SEEDS)
print(f'  mean T: warm {mtw:.2f}, eq {mte:.2f}, dense {mtd:.2f}; warm - dense = {mtw - mtd:+.2f}; seeds warm > dense: {t_hi}/6')
print(f"  358e4 bar row (+40 mean and 5 of 6 over dense): mean T_warm >= mean T_dense + 40 -> {mtw >= mtd + 40}; "
      f"{t_hi}/6 >= 5 -> {t_hi >= 5}")
for ph, lab in [('after_sums', 'after B'), ('after_mazes', 'after C')]:
    row = []
    for name, D, _ in ARMS:
        vals = [sc(D[s], ph, 'grids5') for s in SEEDS]
        row.append(f'{name} {vals} mean {mean(vals):.2f}')
    print(f'  grids5 {lab}: ' + ' | '.join(row))
print('  other per-seed scores (right), warm / eq / dense:')
for ph in ['after_sums', 'after_mazes']:
    for t in TASKS:
        print(f'    {ph:11s} {t:6s}: warm {[sc(warm[s], ph, t) for s in SEEDS]} eq {[sc(eq[s], ph, t) for s in SEEDS]} '
              f'dense {[sc(dense[s], ph, t) for s in SEEDS]}')

print()
print('=' * 70)
print('7. SENSITIVITY: alternative readings')
print('=' * 70)
# M with share read differently
for thr in [0.05]:
    alt = sum(max(group_share(warm[s], 'after_sums', 'sums4', 4, 7)) >= thr and max(group_share(warm[s], 'after_mazes', 'maze7', 8, 11)) >= thr for s in SEEDS)
    print(f'  M with "all blocks" instead of "at least one block": '
          f'{sum(all(x >= 0.05 for x in group_share(warm[s], "after_sums", "sums4", 4, 7)) and all(x >= 0.05 for x in group_share(warm[s], "after_mazes", "maze7", 8, 11)) for s in SEEDS)}/6')
# N with r16 / any
for f in ['r16', 'any']:
    nw = {s: sc(warm[s], 'after_sums', 'sums4', f) + sc(warm[s], 'after_mazes', 'maze7', f) for s in SEEDS}
    ne = {s: sc(eq[s], 'after_sums', 'sums4', f) + sc(eq[s], 'after_mazes', 'maze7', f) for s in SEEDS}
    print(f'  N using {f}: warm {[nw[s] for s in SEEDS]} mean {mean(nw.values()):.2f} | eq {[ne[s] for s in SEEDS]} '
          f'mean {mean(ne.values()):.2f} | gap {mean(nw.values()) - mean(ne.values()):+.2f} | '
          f'>: {sum(nw[s] > ne[s] for s in SEEDS)}/6, <=+10: {sum(nw[s] <= ne[s] + 10 for s in SEEDS)}/6')
# N using sums4 after C instead of after B
nw = {s: sc(warm[s], 'after_mazes', 'sums4') + sc(warm[s], 'after_mazes', 'maze7') for s in SEEDS}
ne = {s: sc(eq[s], 'after_mazes', 'sums4') + sc(eq[s], 'after_mazes', 'maze7') for s in SEEDS}
print(f'  N with sums4 after C (misreading): warm mean {mean(nw.values()):.2f} eq mean {mean(ne.values()):.2f} '
      f'gap {mean(nw.values()) - mean(ne.values()):+.2f} >: {sum(nw[s] > ne[s] for s in SEEDS)}/6')
# leave-one-out on gap
print('  leave-one-seed-out mean gap (N_warm - N_eq):',
      {s: round(mean(Nw[x] for x in SEEDS if x != s) - mean(Ne[x] for x in SEEDS if x != s), 2) for s in SEEDS})
