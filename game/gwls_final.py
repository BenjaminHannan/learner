"""DRAFT pending coordinator confirmation (GW-LS). The one sealed read of GW-LS (game/WALL-SOLVE-RESULT.md section 3) and its sealed marks. NOT to be run before round 8 exists.

  python -m game.gwls_final [--dry-run] [--analyze-only] [--selftest] [--root DIR] [--arm-c DIR] [--persist-dir DIR]

Scores DIR/s<seed>/checkpoint-iter8.pt on the 100 sealed maps ONCE per seed, both seeds in parallel (2 threads each), by exactly
    python -m game.score --arm model --ckpt <ckpt> --picker sample --temp 1.0 --out DIR/s<seed>/score-sample.json --threads 2
(the output is a per-world file in the format of arm C's score-sample.json). Before it plays anything it REFUSES (all problems are listed) unless:
  * round 8 is complete on both seeds: iter-8.json and checkpoint-iter8.pt exist AND state.pt (written last, atomically, by game.imitate) says k == 8,
    run seed 398 / 399 and day offset 4 (a run that is still training is not read);
  * the round-4 leading indicator is not STOP: gwls_report.indicator is recomputed from the iter-*.json and play files of rounds 3 and 4 under the
    reading fixed in the start record (a seed trips if ratio_w <= 0.5 or non-habit <= ref - 0.5, over rounds 3-4; STOP only if both seeds trip). A STOP
    run gets no sealed read, and an unfinished round 3 / 4 gives no read either;
  * arm C's file is the one on record: sha256 equal to the committed file's (constants below), picker sample, T 1.0, 100 worlds, checkpoint the n64000
    one of that seed, and its means equal the record (total 6.50 / 7.10, non-habit 5.46 / 5.85, stone 40 / 43%);
  * no result file for either checkpoint exists, and no score-started.lock of an earlier attempt is there (a crashed attempt is not silently
    re-played; delete the lock by hand only on a decision).
--analyze-only never plays: it reads existing result files (arm C is still checked). --dry-run prints the plan, arm C's numbers and every refusal
reason, and plays nothing (exit status 1 if it would refuse).
Straight after the sealed read the score files, and after the analysis final.json, are copied to --persist-dir (default game/results/gwls/; no git
operation: the session lead commits).

Then, per seed, paired by world seed against arm C (glprobe/s<seed>/n64000/score-sample.json) with game.analyze.boot_diff (2000 draws, seed 0):
total unlocks diff and 95% CI, NON-HABIT unlocks diff and 95% CI (unlocks whose name is not collect_sapling, place_plant, eat_plant, wake_up),
stone maps (collect_stone share) diff in points. Sealed marks, applied verbatim:
  PASS (screen) iff on both seeds: non-habit diff >= +0.3 with CI low > 0, total diff >= +0.5, stone diff >= +10 points.
  PROVED WRONG iff on both seeds non-habit diff <= -0.5, OR stone diff <= -15 points on both seeds.
  else NO VERDICT (no extension without new marks).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

from game import analyze, gwls_report

SCRATCH = '/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad'
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSIST_DIR = os.path.join(REPO_ROOT, 'game', 'results', 'gwls')
HABIT = {'collect_sapling', 'place_plant', 'eat_plant', 'wake_up'}
SEEDS = (200, 201)
RUN_SEED = {200: 398, 201: 399}
DAY_OFFSET = 4
PASS_NH, PASS_TOTAL, PASS_STONE = 0.3, 0.5, 10.0
WRONG_NH, WRONG_STONE = -0.5, -15.0
# Arm C as on record: the committed files origin/claude/project-thread-yha868:results/game-world/glprobe-run/s20X/n64000/score-sample.json
ARM_C_SHA256 = {200: '516f7329d74486d74075243217ee4e62559b92316efed9fad47a0c470ab631dc',
                201: '4ec56fd9b260d04d38c3a9dd57c25c9c679e7b11167936caf9e6da7e6522f7f1'}
ARM_C_RECORD = {200: dict(total=6.50, nonhabit=5.46, stone=40.0), 201: dict(total=7.10, nonhabit=5.85, stone=43.0)}


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
    """Every path is absolute (the scorer child runs with cwd=REPO_ROOT, so a relative --root would point at other files there)."""
    root, arm_c = os.path.abspath(root), os.path.abspath(arm_c)
    d = os.path.join(root, f's{seed}')
    return dict(dir=d, ckpt=os.path.join(d, 'checkpoint-iter8.pt'), out=os.path.join(d, 'score-sample.json'), lock=os.path.join(d, 'score-started.lock'),
                iter8=os.path.join(d, 'iter-8.json'), state=os.path.join(d, 'state.pt'), base=os.path.join(arm_c, f's{seed}', 'n64000', 'score-sample.json'))


def command(p):
    return [sys.executable, '-m', 'game.score', '--arm', 'model', '--ckpt', p['ckpt'], '--picker', 'sample', '--temp', '1.0',
            '--out', p['out'], '--threads', '2']


# ---------- the refusals ----------

def arm_c_problems(seed, raw, b, check_hash=True):
    """Problems (strings) with arm C's file for `seed`: raw = its bytes, b = the parsed JSON. [] when it is the one on record."""
    bad = []
    if check_hash and hashlib.sha256(raw).hexdigest() != ARM_C_SHA256[seed]:
        bad.append(f'arm C seed {seed}: sha256 {hashlib.sha256(raw).hexdigest()[:16]}... is not the committed file ({ARM_C_SHA256[seed][:16]}...)')
    if b.get('arm') != 'model':
        bad.append(f'arm C seed {seed}: arm is {b.get("arm")!r}, not model')
    if b.get('picker') != 'sample':
        bad.append(f'arm C seed {seed}: picker is {b.get("picker")!r}, not sample')
    if b.get('temp') != 1.0:
        bad.append(f'arm C seed {seed}: temp is {b.get("temp")!r}, not 1.0')
    pw = b.get('per_world') or []
    if not (b.get('worlds') == len(pw) == 100):
        bad.append(f'arm C seed {seed}: worlds {b.get("worlds")} / per_world {len(pw)}, not 100')
    tail = ['s%d' % seed, 'n64000', 'checkpoint.pt']
    if os.path.normpath(str(b.get('ckpt'))).split(os.sep)[-3:] != tail:
        bad.append(f'arm C seed {seed}: ckpt {b.get("ckpt")!r} does not end with {"/".join(tail)} (the GW-L 64k checkpoint)')
    if pw and len(pw) == 100:
        rec = ARM_C_RECORD[seed]
        got = dict(total=round(float(b.get('mean_unlocks', -1)), 2), nonhabit=round(sum(map(nonhabit, pw)) / 100, 2), stone=round(sum(map(stone, pw)) / 100, 1))
        if any(abs(got[k] - rec[k]) > 1e-9 for k in rec):
            bad.append(f'arm C seed {seed}: means {got} differ from the record {rec}')
    return bad


def load_arm_c(p, seed):
    """-> (parsed arm C file or None, [problems])."""
    if not os.path.exists(p['base']):
        return None, [f'arm C file missing: {p["base"]}']
    try:
        with open(p['base'], 'rb') as f:
            raw = f.read()
        b = json.loads(raw)
        return b, arm_c_problems(seed, raw, b)
    except (OSError, ValueError, AssertionError, KeyError, TypeError, AttributeError) as e:
        return None, [f'arm C seed {seed}: {p["base"]} cannot be read: {type(e).__name__}: {e}']


def read_state(path):
    import torch
    return torch.load(path, map_location='cpu', weights_only=False)


def round8_problems(seed, p):
    bad = []
    for name in ('iter8', 'ckpt', 'state'):
        if not os.path.exists(p[name]):
            bad.append(f'seed {seed}: round 8 is not complete, {p[name]} missing')
    st = None
    if os.path.exists(p['state']):
        try:
            st = read_state(p['state'])
            st.get('k')
        except Exception as e:                                       # a torn / corrupt / non-dict state.pt is a refusal reason, not a crash
            st = None
            bad.append(f'seed {seed}: {p["state"]} cannot be read: {type(e).__name__}: {e}')
    if st is not None:
        if st.get('k') != 8:
            bad.append(f'seed {seed}: state.pt says k = {st.get("k")}, not 8 (training has not finished; state.pt is written last)')
        if (st.get('run_seed'), st.get('day_offset')) != (RUN_SEED[seed], DAY_OFFSET):
            bad.append(f'seed {seed}: state.pt is run seed {st.get("run_seed")} / day offset {st.get("day_offset")}, not {RUN_SEED[seed]} / {DAY_OFFSET}')
        if os.path.normpath(str(st.get('parent'))).split(os.sep)[-3:] != ['s%d' % seed, 'n64000', 'checkpoint.pt']:
            bad.append(f'seed {seed}: state.pt parent {st.get("parent")!r} is not the n64000 checkpoint of this seed')
    return bad


def gate(root):
    """-> (problems, indicator). The round-4 leading indicator recomputed from rounds 3 and 4 of both seeds (no cache); STOP or unfinished refuses."""
    errors = []
    rows = gwls_report.build_rows(root, SEEDS, rounds=(3, 4), errors=errors)        # unreadable / inconsistent rounds become strings, all of them listed
    try:
        ind = gwls_report.indicator(rows, gwls_report.REF)
    except (AssertionError, ValueError, OSError, KeyError, TypeError, ZeroDivisionError) as e:
        errors.append(f'round-4 leading indicator cannot be computed: {type(e).__name__}: {e}')
        ind = None
    if errors:
        return [f'round-4 leading indicator: {x}' for x in errors], dict(branch=None, note='; '.join(errors))
    if ind['branch'] is None:
        return [f'round-4 leading indicator cannot be read: {ind["note"]}'], ind
    if ind['branch'] != 'CONTINUE':
        return [f'round-4 leading indicator is {ind["branch"]} (per-seed reading of the start record): {json.dumps(ind["per_seed"])}; no sealed read for a stopped run'], ind
    return [], ind


def play_problems(P, root, arm_c_bad):
    bad = list(arm_c_bad)
    for s, p in P.items():
        bad += round8_problems(s, p)
        if os.path.exists(p['out']):
            bad.append(f'seed {s}: a sealed result already exists: {p["out"]}')
        if os.path.exists(p['lock']):
            bad.append(f'seed {s}: an earlier scoring attempt left {p["lock"]}')
    g, ind = gate(root)
    return bad + g, ind


def persist(files, root, persist_dir):
    for src in files:
        dst = os.path.join(persist_dir, os.path.relpath(src, root))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print('persisted', dst)


# ---------- selftest ----------

def synthetic_arm_c(seed):
    """A per-world arm C dict (100 worlds) with exactly the recorded means of `seed`; for the selftest and the tests."""
    rec = ARM_C_RECORD[seed]
    n_nh, n_tot = round(rec['nonhabit'] * 100), round(rec['total'] * 100)
    n_stone = round(rec['stone'])
    base, extra = divmod(n_nh, 100)                      # extra worlds get one more non-habit unlock
    names = ['collect_wood', 'place_table', 'collect_drink', 'eat_cow', 'defeat_zombie', 'make_wood_pickaxe', 'make_wood_sword', 'collect_coal']
    habit_total = n_tot - n_nh
    worlds = []
    for i in range(100):
        k = base + (1 if i < extra else 0)
        h = habit_total // 100 + (1 if i < habit_total % 100 else 0)
        unlocks = [[j, names[j % len(names)] if j < len(names) else f'x{j}'] for j in range(k)] + [[50 + j, 'wake_up'] for j in range(h)]
        worlds.append(dict(seed=7000000 + i, unlocks=unlocks, n_unlocks=float(len(unlocks)), ach_rate=dict(collect_stone=1.0 if i < n_stone else 0.0)))
    return dict(arm='model', ckpt=f'/x/glprobe/run/s{seed}/n64000/checkpoint.pt', gate=None, picker='sample', ppo_picker=None, temp=1.0, worlds=100, cap=1000,
                per_world=worlds, mean_unlocks=round(sum(w['n_unlocks'] for w in worlds) / 100, 3))


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
    # arm C checks: the synthetic file has the recorded means, so only the hash differs; each tamper is caught on its own
    for s in SEEDS:
        b = synthetic_arm_c(s)
        raw = json.dumps(b).encode()
        assert arm_c_problems(s, raw, b, check_hash=False) == [], arm_c_problems(s, raw, b, check_hash=False)
        assert len(arm_c_problems(s, raw, b)) == 1 and 'sha256' in arm_c_problems(s, raw, b)[0]
        for key, val, word in (('picker', 'top', 'picker'), ('temp', 0.5, 'temp'), ('ckpt', f'/x/s{s}/n32000/checkpoint.pt', 'ckpt'),
                               ('ckpt', f'/x/s{1000 - s}/n64000/checkpoint.pt', 'ckpt'), ('arm', 'random', 'arm'), ('worlds', 99, 'worlds')):
            t = dict(b, **{key: val})
            probs = arm_c_problems(s, raw, t, check_hash=False)
            assert len(probs) >= 1 and any(word in x for x in probs), (key, probs)
        w0 = b['per_world'][0]                                                                  # one world's unlocks changed: the means move off the record
        t = dict(b, per_world=[dict(w0, unlocks=w0['unlocks'] + [[99, 'collect_diamond']], n_unlocks=w0['n_unlocks'] + 1)] + b['per_world'][1:])
        assert any('means' in x for x in arm_c_problems(s, raw, t, check_hash=False))
    assert any('means' in x for x in arm_c_problems(200, b'', dict(synthetic_arm_c(200), mean_unlocks=6.6), check_hash=False))
    # the round-4 gate: STOP and unfinished both refuse; CONTINUE passes (indicator itself is exercised in game/tests/test_gwls.py)
    row = lambda r, nh, ratio: dict(round=r, games=400, nonhabit_sum=nh, ratio_w_exact=ratio)
    ok = {200: [row(3, 2300, 2.0), row(4, 2300, 2.0)], 201: [row(3, 2300, 2.0), row(4, 2300, 2.0)]}
    assert gwls_report.indicator(ok, gwls_report.REF)['branch'] == 'CONTINUE'
    stop = {200: [row(3, 2300, 0.4), row(4, 2300, 0.5)], 201: [row(3, 2300, 0.4), row(4, 2300, 0.4)]}
    assert gwls_report.indicator(stop, gwls_report.REF)['branch'] == gwls_report.STOP
    # every path handed to the scorer child (cwd = REPO_ROOT) is absolute, whatever the cwd and a relative --root
    pp = paths('some/rel/root', 'rel/armc', 200)
    assert all(os.path.isabs(v) for v in pp.values()) and all(os.path.isabs(x) for x in (command(pp)[command(pp).index('--ckpt') + 1], command(pp)[command(pp).index('--out') + 1]))
    print('selftest ok')


def parse_args(argv=None):
    """The command line, with --root / --arm-c / --persist-dir made absolute here, once, so nothing later depends on the cwd."""
    ap = argparse.ArgumentParser(description='GW-LS: the one sealed read at round 8 and the sealed marks.')
    ap.add_argument('--root', default=os.path.join(SCRATCH, 'gwls'))
    ap.add_argument('--arm-c', default=os.path.join(SCRATCH, 'glprobe'))
    ap.add_argument('--persist-dir', default=PERSIST_DIR, help='where the score files and final.json are copied (no git operation)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--analyze-only', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    a.root, a.arm_c, a.persist_dir = (os.path.abspath(x) for x in (a.root, a.arm_c, a.persist_dir))
    return a


def main(argv=None):
    a = parse_args(argv)
    if a.selftest:
        return selftest()
    P = {s: paths(a.root, a.arm_c, s) for s in SEEDS}
    arm_c, arm_c_bad = {}, []
    for s, p in P.items():
        arm_c[s], bad = load_arm_c(p, s)
        arm_c_bad += bad
    if a.dry_run:
        for s, p in P.items():
            print(s, 'ckpt', p['ckpt'], 'exists' if os.path.exists(p['ckpt']) else 'MISSING', '| result', 'EXISTS (would refuse)' if os.path.exists(p['out']) else 'absent',
                  '| lock', 'EXISTS (would refuse)' if os.path.exists(p['lock']) else 'absent')
            print('  would run:', ' '.join(command(p)))
            b = arm_c[s]
            if b is not None:
                print('  arm C: total', round(b['mean_unlocks'], 3), 'non-habit', round(sum(map(nonhabit, b['per_world'])) / b['worlds'], 3),
                      'stone %', round(sum(map(stone, b['per_world'])) / b['worlds'], 1))
        bad, ind = play_problems(P, a.root, arm_c_bad)
        print('round-4 branch:', ind['branch'] if ind['branch'] else f'unavailable ({ind["note"]})')
        if bad:
            print('DRY RUN: WOULD REFUSE to play, %d problem(s):' % len(bad))
            for x in bad:
                print('  -', x)
            sys.exit(1)
        print('DRY RUN: all preconditions hold; it would play.')
        return
    if a.analyze_only:
        assert not arm_c_bad, 'arm C is not the one on record: ' + '; '.join(arm_c_bad)
    else:
        bad, _ = play_problems(P, a.root, arm_c_bad)
        if bad:
            sys.exit('refusing to play the sealed worlds, %d problem(s):\n  - ' % len(bad) + '\n  - '.join(bad))
        for p in P.values():
            open(p['lock'], 'w').write('sealed scoring started; delete only on a decision\n')
        env = dict(os.environ, PYTHONPATH=REPO_ROOT)
        procs = [subprocess.Popen(command(p), env=env, cwd=REPO_ROOT) for p in P.values()]
        codes = [pr.wait() for pr in procs]
        assert codes == [0, 0], f'game.score failed: {codes} (locks kept: no re-play without a decision)'
        persist([p['out'] for p in P.values()], a.root, a.persist_dir)                    # straight after the sealed read
        for p in P.values():
            os.remove(p['lock'])
    per_seed = {}
    for s, p in P.items():
        with open(p['out']) as f:
            m = json.load(f)
        b = arm_c[s]
        assert m['picker'] == 'sample' and m['temp'] == 1.0 and m['worlds'] == b['worlds'] == 100, 'not the sealed configuration'
        assert os.path.basename(m['ckpt']) == 'checkpoint-iter8.pt' and os.path.basename(os.path.dirname(os.path.abspath(m['ckpt']))) == f's{s}', m['ckpt']
        per_seed[s] = compare(m, b)
        c = per_seed[s]
        print(f'seed {s}: total {c["mean_total"][0]:.3f} vs C {c["mean_total"][1]:.3f} diff {c["total"]["diff"]:+.3f} [{c["total"]["lo"]:+.3f}, {c["total"]["hi"]:+.3f}] | '
              f'non-habit {c["mean_nonhabit"][0]:.3f} vs {c["mean_nonhabit"][1]:.3f} diff {c["nonhabit"]["diff"]:+.3f} [{c["nonhabit"]["lo"]:+.3f}, {c["nonhabit"]["hi"]:+.3f}] | '
              f'stone {c["stone_pct"][0]:.1f}% vs {c["stone_pct"][1]:.1f}% diff {c["stone_points"]:+.1f} points')
    v = verdict(per_seed)
    print('VERDICT:', v)
    fpath = os.path.join(a.root, 'final.json')
    with open(fpath, 'w') as f:
        json.dump(dict(per_seed={str(k): x for k, x in per_seed.items()}, verdict=v), f, indent=1)
    persist([fpath] + [p['out'] for p in P.values()], a.root, a.persist_dir)


if __name__ == '__main__':
    main()
