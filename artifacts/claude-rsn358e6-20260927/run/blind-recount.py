"""Blind recount of rsn-358e6 from raw result.json files and the sealed marks only."""
import json, os
R = '/home/user/learner/artifacts'
SEEDS = range(3, 9)
TESTS = ['grids5', 'grids6', 'sums4', 'sums6', 'maze7']
TORCH = '2.14.0+cu130'

def load(p):
    with open(p) as f:
        return json.load(f)

cand = {s: load(f'{R}/claude-rsn358e6-20260927/runs/eq-replayall-shared-s{s}/result.json') for s in SEEDS}
eq = {s: load(f'{R}/claude-rsn358e4-20260927/runs/eq-replayall-s{s}/result.json') for s in SEEDS}
dn = {s: load(f'{R}/claude-rsn358e4-20260927/runs/dense-replayall-s{s}/result.json') for s in SEEDS}

def sc(d, ph, t):
    return d['phases'][ph][t]['right']

def mean(xs):
    return sum(xs) / len(xs)

print('== metadata ==')
for s in SEEDS:
    for name, d in (('cand', cand[s]), ('eq', eq[s]), ('dense', dn[s])):
        print(f"s{s} {name:5s} arm={d['arm']} seed={d['seed']} torch={d['torch']} device={d['device']} weights={d['weights']} minutes={d.get('minutes')}")

print('\n== REPRO (after-A dev scores, cand vs eq-replayall control; torch) ==')
repro_all = True
repro_all_right_only = True
for s in SEEDS:
    right_eq = all(sc(cand[s], 'after_grids', t) == sc(eq[s], 'after_grids', t) for t in TESTS)
    full_eq = all(cand[s]['phases']['after_grids'][t] == eq[s]['phases']['after_grids'][t] for t in TESTS)
    start_eq = all(cand[s]['phases']['start'][t] == eq[s]['phases']['start'][t] for t in TESTS)
    es_eq = cand[s]['phases']['after_grids'].get('expert_share') == eq[s]['phases']['after_grids'].get('expert_share')
    torch_ok = cand[s]['torch'] == TORCH and eq[s]['torch'] == TORCH
    ok = full_eq and torch_ok
    repro_all &= ok
    repro_all_right_only &= (right_eq and torch_ok)
    diffs = [(t, cand[s]['phases']['after_grids'][t], eq[s]['phases']['after_grids'][t]) for t in TESTS
             if cand[s]['phases']['after_grids'][t] != eq[s]['phases']['after_grids'][t]]
    print(f's{s}: right-equal={right_eq} right/r16/any-equal={full_eq} start-equal={start_eq} '
          f'afterA-expert_share-equal={es_eq} torch_ok={torch_ok} -> REPRO={ok} diffs={diffs}')
print(f'REPRO on all seeds (right,r16,any + torch): {repro_all}; (right only + torch): {repro_all_right_only}')
print('Container condition: result.json has no container/host field; not checkable from raw files.')

print('\n== N = sums4 after B + maze7 after C (of 400) ==')
print('seed | cand sums4B maze7C N | eq sums4B maze7C N | diff | cand>eq | cand<=eq+10')
Nc, Ne = {}, {}
for s in SEEDS:
    Nc[s] = sc(cand[s], 'after_sums', 'sums4') + sc(cand[s], 'after_mazes', 'maze7')
    Ne[s] = sc(eq[s], 'after_sums', 'sums4') + sc(eq[s], 'after_mazes', 'maze7')
    print(f"s{s} | {sc(cand[s],'after_sums','sums4'):4d} {sc(cand[s],'after_mazes','maze7'):4d} {Nc[s]:4d} | "
          f"{sc(eq[s],'after_sums','sums4'):4d} {sc(eq[s],'after_mazes','maze7'):4d} {Ne[s]:4d} | {Nc[s]-Ne[s]:+5d} | "
          f"{Nc[s] > Ne[s]} | {Nc[s] <= Ne[s] + 10}")
mNc, mNe = mean(list(Nc.values())), mean(list(Ne.values()))
print(f'mean N_shared = {mNc:.2f}; mean N_eq = {mNe:.2f}; gap = {mNc - mNe:+.2f}')
p1 = mNc >= mNe + 50
p2 = sum(Nc[s] > Ne[s] for s in SEEDS)
w1 = mNc <= mNe + 10
w2 = sum(Nc[s] <= Ne[s] + 10 for s in SEEDS)
PASS = p1 and p2 >= 5
WRONG = w1 and w2 >= 5
print(f'PASS cond 1 (mean N_shared >= mean N_eq + 50): {p1}')
print(f'PASS cond 2 (N_shared > N_eq on >=5/6): {p2 >= 5} ({p2}/6)')
print(f'PASS: {PASS}')
print(f'WRONG cond 1 (mean N_shared <= mean N_eq + 10): {w1}')
print(f'WRONG cond 2 (N_shared <= N_eq + 10 on >=5/6): {w2 >= 5} ({w2}/6)')
print(f'PROVED WRONG: {WRONG}')
if not repro_all:
    verdict = 'INCONCLUSIVE (REPRO failed)'
elif PASS:
    verdict = 'PASS'
elif WRONG:
    verdict = 'PROVED WRONG'
else:
    verdict = 'FAIL'
print(f'VERDICT: {verdict}')

print('\n== Report only: T = grids5+sums4+maze7 after C (of 600) ==')
T = {}
for name, D in (('cand', cand), ('eq', eq), ('dense', dn)):
    T[name] = {s: sum(sc(D[s], 'after_mazes', t) for t in ('grids5', 'sums4', 'maze7')) for s in SEEDS}
print('seed | T_cand T_eq T_dense | cand-dense | eq-dense')
for s in SEEDS:
    print(f"s{s} | {T['cand'][s]:4d} {T['eq'][s]:4d} {T['dense'][s]:4d} | {T['cand'][s]-T['dense'][s]:+5d} | {T['eq'][s]-T['dense'][s]:+5d}")
mT = {k: mean(list(v.values())) for k, v in T.items()}
print(f"means: T_cand={mT['cand']:.2f} T_eq={mT['eq']:.2f} T_dense={mT['dense']:.2f}; cand-dense={mT['cand']-mT['dense']:+.2f}; eq-dense={mT['eq']-mT['dense']:+.2f}")
nb = sum(T['cand'][s] > T['dense'][s] for s in SEEDS)
nw = sum(T['cand'][s] < T['dense'][s] for s in SEEDS)
print(f"358e4 bar row (cand vs dense): mean T_cand >= mean T_dense + 40: {mT['cand'] >= mT['dense'] + 40}; "
      f"T_cand > T_dense on {nb}/6 (>=5: {nb >= 5}) -> both bars met: {mT['cand'] >= mT['dense'] + 40 and nb >= 5}")
print(f"mirror (358e4 proved-wrong shape): mean T_cand <= mean T_dense - 40: {mT['cand'] <= mT['dense'] - 40}; "
      f"T_cand < T_dense on {nw}/6 (>=5: {nw >= 5})")

print('\n== Report only: grids5 after A / B / C ==')
print('seed | cand A B C | eq A B C | dense A B C')
g = {}
for name, D in (('cand', cand), ('eq', eq), ('dense', dn)):
    g[name] = {s: [sc(D[s], ph, 'grids5') for ph in ('after_grids', 'after_sums', 'after_mazes')] for s in SEEDS}
for s in SEEDS:
    print(f"s{s} | {g['cand'][s]} | {g['eq'][s]} | {g['dense'][s]}")
for name in g:
    print(f"mean {name}: A={mean([g[name][s][0] for s in SEEDS]):.2f} B={mean([g[name][s][1] for s in SEEDS]):.2f} C={mean([g[name][s][2] for s in SEEDS]):.2f}")
lo = sum(g['cand'][s][2] < g['eq'][s][2] for s in SEEDS)
hi = sum(g['cand'][s][2] > g['dense'][s][2] for s in SEEDS)
print(f'grids5 after C: cand < eq on {lo}/6; cand > dense on {hi}/6')

print('\n== Report only: all dev scores after C (context) ==')
for s in SEEDS:
    print(f"s{s} cand {[sc(cand[s],'after_mazes',t) for t in TESTS]} eq {[sc(eq[s],'after_mazes',t) for t in TESTS]} dense {[sc(dn[s],'after_mazes',t) for t in TESTS]}  ({TESTS})")

print('\n== Report only: routing count (358e4 ADDENDUM-3) ==')
def routing(d):
    b = d['phases']['after_sums']['expert_share']['sums4']
    c = d['phases']['after_mazes']['expert_share']['maze7']
    sb = [sum(blk[4:8]) for blk in b]
    scc = [sum(blk[8:12]) for blk in c]
    return sb, scc, (max(sb) >= 0.05 and max(scc) >= 0.05)
for name, D in (('cand', cand), ('eq', eq)):
    n = 0
    for s in SEEDS:
        sb, scc, ok = routing(D[s])
        n += ok
        print(f"{name} s{s}: new-group share sums4 after B per block={[round(x,3) for x in sb]}; maze7 after C (experts 8-11)={[round(x,3) for x in scc]} -> tested={ok}")
    print(f'{name}: {n}/6 seeds tested the routing')
print('dense expert_share present:', {s: bool(dn[s]['phases']['after_sums'].get('expert_share')) for s in SEEDS})

print('\n== Report only: trainable_next_phase and replay counts ==')
for s in SEEDS:
    p = cand[s]['phases']
    print(f"cand s{s}: trainable_next_phase A->{p['after_grids'].get('trainable_next_phase')} B->{p['after_sums'].get('trainable_next_phase')} C->{p['after_mazes'].get('trainable_next_phase')}")
for name, D in (('cand', cand), ('eq', eq), ('dense', dn)):
    for s in SEEDS:
        p = D[s]['phases']
        print(f"{name} s{s}: B replayed={p['after_sums'].get('replayed')} replayed_batches={p['after_sums'].get('replayed_batches')} | C replayed={p['after_mazes'].get('replayed')}")
