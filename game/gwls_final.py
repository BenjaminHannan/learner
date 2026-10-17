"""DRAFT pending coordinator review (GW-LS). The one sealed read of GW-LS (game/WALL-SOLVE-RESULT.md section 3) and its sealed marks. NOT to be run before round 8 exists.

  python -m game.gwls_final [--dry-run] [--analyze-only] [--selftest] [--root DIR] [--arm-c DIR]

Scores DIR/s<seed>/checkpoint-iter8.pt on the 100 sealed maps ONCE per seed, both seeds in parallel (2 threads each), by exactly
    python -m game.score --arm model --ckpt <ckpt> --picker sample --temp 1.0 --out DIR/s<seed>/score-sample.json --threads 2
(the output is a per-world file in the format of arm C's score-sample.json). It refuses to play when round 8 is incomplete (no iter-8.json or checkpoint), when
a result file for either checkpoint already exists, or when the score-started.lock of an earlier attempt is there (a crashed attempt is not silently
re-played; delete the lock by hand only on a decision). --analyze-only never plays: it reads existing result files. --dry-run prints the plan and arm C's
numbers and plays nothing.

Then, per seed, paired by world seed against arm C (glprobe/s<seed>/n64000/score-sample.json) with game.analyze.boot_diff (2000 draws, seed 0):
total unlocks diff and 95% CI, NON-HABIT unlocks diff and 95% CI (unlocks whose name is not collect_sapling, place_plant, eat_plant, wake_up),
stone maps (collect_stone share) diff in points. Sealed marks, applied verbatim:
  PASS (screen) iff on both seeds: non-habit diff >= +0.3 with CI low > 0, total diff >= +0.5, stone diff >= +10 points.
  PROVED WRONG iff on both seeds non-habit diff <= -0.5, OR stone diff <= -15 points on both seeds.
  else NO VERDICT (no extension without new marks).
"""
import argparse
import json
import os
import subprocess
import sys

from game import analyze

SCRATCH = '/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad'
HABIT = {'collect_sapling', 'place_plant', 'eat_plant', 'wake_up'}
SEEDS = (200, 201)
PASS_NH, PASS_TOTAL, PASS_STONE = 0.3, 0.5, 10.0
WRONG_NH, WRONG_STONE = -0.5, -15.0


def nonhabit(w):
    return float(sum(1 for _, n in w['unlocks'] if n not in HABIT))


def stone(w):
    return 100.0 * w['ach_rate']['collect_stone']


def compare(model_res, base_res):
    """-> the per-seed paired numbers (model minus arm C), paired by world seed."""
    mw, bw = model_res['per_world'], base_res['per_world']
    assert [w['seed'] for w in mw] == [w['seed'] for w in bw], 'arms are on different worlds'
    tot = analyze.boot_diff([w['n_unlocks'] for w in mw], [w['n_unlocks'] for w in bw], 2000, 0)
    nh = analyze.boot_diff([nonhabit(w) for w in mw], [nonhabit(w) for w in bw], 2000, 0)
    st = sum(stone(w) for w in mw) / len(mw) - sum(stone(w) for w in bw) / len(bw)
    return dict(total=dict(diff=tot[0], lo=tot[1], hi=tot[2]), nonhabit=dict(diff=nh[0], lo=nh[1], hi=nh[2]), stone_points=st,
                mean_total=[sum(w['n_unlocks'] for w in mw) / len(mw), sum(w['n_unlocks'] for w in bw) / len(bw)],
                mean_nonhabit=[sum(map(nonhabit, mw)) / len(mw), sum(map(nonhabit, bw)) / len(bw)],
                stone_pct=[sum(map(stone, mw)) / len(mw), sum(map(stone, bw)) / len(bw)])


def verdict(per_seed):
    """per_seed: {seed: compare(...)} -> 'PASS' | 'PROVED WRONG' | 'NO VERDICT', the sealed marks verbatim."""
    r = lambda x: round(x, 6)
    ps = list(per_seed.values())
    assert len(ps) == 2
    if all(r(p['nonhabit']['diff']) >= PASS_NH and r(p['nonhabit']['lo']) > 0 and r(p['total']['diff']) >= PASS_TOTAL
           and r(p['stone_points']) >= PASS_STONE for p in ps):
        return 'PASS'
    if all(r(p['nonhabit']['diff']) <= WRONG_NH for p in ps) or all(r(p['stone_points']) <= WRONG_STONE for p in ps):
        return 'PROVED WRONG'
    return 'NO VERDICT'


def paths(root, arm_c, seed):
    d = os.path.join(root, f's{seed}')
    return dict(dir=d, ckpt=os.path.join(d, 'checkpoint-iter8.pt'), out=os.path.join(d, 'score-sample.json'), lock=os.path.join(d, 'score-started.lock'),
                iter8=os.path.join(d, 'iter-8.json'), base=os.path.join(arm_c, f's{seed}', 'n64000', 'score-sample.json'))


def command(p):
    return [sys.executable, '-m', 'game.score', '--arm', 'model', '--ckpt', p['ckpt'], '--picker', 'sample', '--temp', '1.0',
            '--out', p['out'], '--threads', '2']


def selftest():
    def fake(nh, tot, st):
        return dict(nonhabit=dict(diff=nh[0], lo=nh[1], hi=nh[1] + 1), total=dict(diff=tot, lo=0, hi=0), stone_points=st)
    good = fake((0.3, 0.01), 0.5, 10.0)
    assert verdict({200: good, 201: good}) == 'PASS'
    assert verdict({200: good, 201: fake((0.3, 0.0), 0.5, 10.0)}) == 'NO VERDICT'           # CI low must be > 0
    assert verdict({200: good, 201: fake((0.29, 0.1), 0.5, 10.0)}) == 'NO VERDICT'
    assert verdict({200: good, 201: fake((0.3, 0.01), 0.49, 10.0)}) == 'NO VERDICT'
    assert verdict({200: good, 201: fake((0.3, 0.01), 0.5, 9.9)}) == 'NO VERDICT'
    bad = fake((-0.5, -1), -1, 0.0)
    assert verdict({200: bad, 201: bad}) == 'PROVED WRONG'
    assert verdict({200: bad, 201: fake((0.0, -1), 0, 0.0)}) == 'NO VERDICT'
    assert verdict({200: fake((0, -1), 0, -15.0), 201: fake((0.2, -1), 0, -20.0)}) == 'PROVED WRONG'
    assert verdict({200: fake((0, -1), 0, -15.0), 201: fake((0.2, -1), 0, -14.0)}) == 'NO VERDICT'
    assert verdict({200: bad, 201: fake((0, 0), 0, -15.0)}) == 'NO VERDICT'                  # one seed by non-habit, one by stone: neither "on both"
    print('selftest ok')


def main(argv=None):
    ap = argparse.ArgumentParser(description='GW-LS: the one sealed read at round 8 and the sealed marks.')
    ap.add_argument('--root', default=os.path.join(SCRATCH, 'gwls'))
    ap.add_argument('--arm-c', default=os.path.join(SCRATCH, 'glprobe'))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--analyze-only', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    P = {s: paths(a.root, a.arm_c, s) for s in SEEDS}
    for s, p in P.items():
        assert os.path.exists(p['base']), f'arm C file missing: {p["base"]}'
    if a.dry_run:
        for s, p in P.items():
            print(s, 'ckpt', p['ckpt'], 'exists' if os.path.exists(p['ckpt']) else 'MISSING', '| result', 'EXISTS (would refuse)' if os.path.exists(p['out']) else 'absent',
                  '| lock', 'EXISTS (would refuse)' if os.path.exists(p['lock']) else 'absent')
            print('  would run:', ' '.join(command(p)))
            with open(p['base']) as f:
                b = json.load(f)
            print('  arm C: total', round(b['mean_unlocks'], 3), 'non-habit', round(sum(map(nonhabit, b['per_world'])) / b['worlds'], 3),
                  'stone %', round(sum(map(stone, b['per_world'])) / b['worlds'], 1))
        return
    if not a.analyze_only:
        for s, p in P.items():
            for need in ('iter8', 'ckpt'):
                assert os.path.exists(p[need]), f'round 8 is not complete for seed {s}: {p[need]} missing'
            assert not os.path.exists(p['out']), f'refusing: a sealed result for seed {s} already exists: {p["out"]}'
            assert not os.path.exists(p['lock']), f'refusing: an earlier scoring attempt for seed {s} left {p["lock"]}'
        for p in P.values():
            open(p['lock'], 'w').write('sealed scoring started; delete only on a decision\n')
        env = dict(os.environ, PYTHONPATH=os.getcwd())
        procs = [subprocess.Popen(command(p), env=env) for p in P.values()]
        codes = [pr.wait() for pr in procs]
        assert codes == [0, 0], f'game.score failed: {codes} (locks kept: no re-play without a decision)'
        for p in P.values():
            os.remove(p['lock'])
    per_seed = {}
    for s, p in P.items():
        with open(p['out']) as f:
            m = json.load(f)
        with open(p['base']) as f:
            b = json.load(f)
        assert m['picker'] == 'sample' and m['temp'] == 1.0 and m['worlds'] == b['worlds'] == 100, 'not the sealed configuration'
        per_seed[s] = compare(m, b)
        c = per_seed[s]
        print(f'seed {s}: total {c["mean_total"][0]:.3f} vs C {c["mean_total"][1]:.3f} diff {c["total"]["diff"]:+.3f} [{c["total"]["lo"]:+.3f}, {c["total"]["hi"]:+.3f}] | '
              f'non-habit {c["mean_nonhabit"][0]:.3f} vs {c["mean_nonhabit"][1]:.3f} diff {c["nonhabit"]["diff"]:+.3f} [{c["nonhabit"]["lo"]:+.3f}, {c["nonhabit"]["hi"]:+.3f}] | '
              f'stone {c["stone_pct"][0]:.1f}% vs {c["stone_pct"][1]:.1f}% diff {c["stone_points"]:+.1f} points')
    v = verdict(per_seed)
    print('VERDICT:', v)
    with open(os.path.join(a.root, 'final.json'), 'w') as f:
        json.dump(dict(per_seed={str(k): x for k, x in per_seed.items()}, verdict=v), f, indent=1)


if __name__ == '__main__':
    main()
