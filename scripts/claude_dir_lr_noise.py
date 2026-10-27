"""Noise of F_eq / F_few from the raw eq-runs files (dev panel, 9x9, learned-stop 'right')."""
import json, math, statistics as st
R = 'artifacts/claude-fewex-20260927/eq-runs/'
KS = ['1', '4', '16', '64', '256', '1024', '4096', '16384']
def curve(arm, seed, init, f):
    d = json.load(open(f'{R}{arm}-s{seed}-{init}/{f}.json'))
    r = d['rungs'] if f == 'adapt' else d['scores']
    return [100 * r[k]['9']['right'] / r[k]['9']['n'] for k in KS]
def feq(c): return sum(c) / 8
def ffew(c): return sum(c[:4]) / 4
out = []
for f in ('adapt', 'holdout'):
    out.append(f'## {f} ({"dev" if f=="adapt" else "holdout"}) F_eq / F_few per run')
    diffs = {}
    for arm in ('loop', 'plain'):
        for init in ('pre', 'fresh'):
            c0, c1 = curve(arm, 0, init, f), curve(arm, 1, init, f)
            out.append(f'{arm}-{init}: seed0 F_eq {feq(c0):.2f} F_few {ffew(c0):.2f} | seed1 F_eq {feq(c1):.2f} F_few {ffew(c1):.2f}')
            diffs[(arm, init)] = ([a - b for a, b in zip(c0, c1)])
    allrung = [x for v in diffs.values() for x in v]
    rms = math.sqrt(sum(x * x for x in allrung) / len(allrung))
    out.append(f'seed0-minus-seed1 F_eq gaps by arm: ' + ', '.join(f'{a}-{i} {feq(v):+.2f}' for (a, i), v in diffs.items()))
    out.append(f'rung-gap RMS over 32 (arm x rung) pairs: {rms:.2f} points; /sqrt(8) = {rms/math.sqrt(8):.2f} (this is the H12 3.33 recipe: sd of a difference of two runs)')
    g = [feq(v) for v in diffs.values()]
    out.append(f'directly measured: 4 seed-gaps of F_eq = {", ".join(f"{x:+.2f}" for x in g)}; RMS {math.sqrt(sum(x*x for x in g)/4):.2f}; max |gap| {max(abs(x) for x in g):.2f}')
    # gap of the practised-loop minus fresh-loop effect between seeds (an effect-size replication)
open('artifacts/claude-dir-lr-20260928/noise-from-raw.txt', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
