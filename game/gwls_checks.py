"""DRAFT pending coordinator confirmation (GW-LS). READ-ONLY checks V1 and V2 of the coordinator's code review of commit 28f6fcc42. Writes nothing.

  python -m game.gwls_checks [--root DIR] [--commit 28f6fcc42] [--seeds 200 201]

V1 (per seed, round 1; the review's verdict becomes BLOCKED and the rounds re-run if a gated item fails):
  * iter-1.json mean_unlocks vs Z8's 6.915 / 7.125: absolute difference reported (INFO, no threshold in the review);
  * played agreement (iter-1.json oracle_agreement_all_played.agreement, imitate's 50-game sample, as Z8's z8.A27 field) vs Z8's 0.3651 / 0.3727:
    difference reported (INFO);
  * non-habit unlocks per game from g['first'] (gwls_report.nonhabit_per_game, unrounded) vs the reference 5.72 / 5.87: PASS if within 0.3;
  * play-1-0.json.gz: the first game's seed is 4,980,400 (s200) / 4,990,400 (s201): PASS/FAIL;
  * every game seed of round 1 (all 4 chunks, 400 games) decodes (seed = 1,000,000 + run_seed * 10,000 + day * 100 + i) to run seed 398 / 399 and
    day >= 4, round 1 days are exactly {4, 5, 6, 7} (chunk c on day 4 + c), no seed is a sealed world: PASS/FAIL.
The play-file items are checked as soon as the 4 chunks exist; the iter-1.json items are 'pending' until it is written. The V1 verdict is PASS only when
every gated item of every seed passes, FAIL if any fails, else PENDING.
V2: commit time of the commit (git log -1 --format=%ct) is earlier than iter-3.json's modification time on both seeds; 'pending' per seed until iter-3.json exists.
"""
import argparse
import gzip
import json
import os
import subprocess
import time

from game import gwls_report, play

SCRATCH = '/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad'
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SEED = {200: 398, 201: 399}
Z8_UNLOCKS = {200: 6.915, 201: 7.125}
Z8_AGREE = {200: 0.3651, 201: 0.3727}
FIRST_SEED = {200: 4_980_400, 201: 4_990_400}
NONHABIT_TOL = 0.3
CHUNKS = 4


def decode(seed):
    """-> (run_seed, day, i) of a practice world seed (the inverse of game.play.practice_seed)."""
    r = seed - 1_000_000
    return r // 10_000, (r % 10_000) // 100, r % 100


def check(name, status, detail, gated=True):
    return dict(name=name, status=status, detail=detail, gated=gated)


def v1_seed(root, seed):
    d = os.path.join(root, f's{seed}')
    items = []
    chunk_paths = gwls_report.play_files(d, 1)
    have_play = len(chunk_paths) == CHUNKS
    it = None
    if os.path.exists(os.path.join(d, 'iter-1.json')):
        with open(os.path.join(d, 'iter-1.json')) as f:
            it = json.load(f)
    if it is None:
        items += [check('iter-1 mean_unlocks vs Z8', 'pending', 'iter-1.json not yet written', False),
                  check('iter-1 played agreement vs Z8', 'pending', 'iter-1.json not yet written', False)]
    else:
        items += [check('iter-1 mean_unlocks vs Z8', 'INFO', f'{it["mean_unlocks"]} vs Z8 {Z8_UNLOCKS[seed]}: abs diff {abs(it["mean_unlocks"] - Z8_UNLOCKS[seed]):.3f}', False)]
        ag = it['oracle_agreement_all_played']['agreement']
        items += [check('iter-1 played agreement vs Z8', 'INFO', f'{ag} vs Z8 {Z8_AGREE[seed]}: diff {ag - Z8_AGREE[seed]:+.4f} (imitate 50-game sample, views {it["oracle_agreement_all_played"]["views"]})', False)]
    if not have_play:
        pend = f'{len(chunk_paths)} of {CHUNKS} play-1 chunks exist'
        return items + [check(n, 'pending', pend) for n in ('non-habit per game vs reference', 'first game seed', 'all round-1 seeds on days 4-7')]
    games, _ = gwls_report.read_play(d, 1)
    nh = gwls_report.nonhabit_per_game(games)
    ref = gwls_report.REF[seed]
    items.append(check('non-habit per game vs reference', 'PASS' if abs(nh - ref) <= NONHABIT_TOL + 1e-12 else 'FAIL',
                       f'{nh:.4f} (count {gwls_report.nonhabit_count(games)} / {len(games)}) vs ref {ref}: diff {nh - ref:+.4f}, tolerance {NONHABIT_TOL}'))
    first = games[0]['seed']
    items.append(check('first game seed', 'PASS' if first == FIRST_SEED[seed] else 'FAIL', f'play-1-0 first seed {first:,} (expected {FIRST_SEED[seed]:,})'))
    bad, days, per_chunk = [], set(), []
    for c, path in enumerate(chunk_paths):
        with gzip.open(path, 'rt') as f:
            ch = json.load(f)
        cd = {decode(g['seed'])[1] for g in ch}
        per_chunk.append((len(ch), sorted(cd)))
        for g in ch:
            rs, day, i = decode(g['seed'])
            days.add(day)
            if rs != RUN_SEED[seed] or day < 4 or play.is_sealed(g['seed']) or play.practice_seed(rs, day, i) != g['seed']:
                bad.append(g['seed'])
        if cd != {4 + c}:
            bad.append(f'chunk {c} days {sorted(cd)}')
    ok = not bad and days == {4, 5, 6, 7} and len(games) == 400 and len({g['seed'] for g in games}) == 400
    items.append(check('all round-1 seeds on days 4-7', 'PASS' if ok else 'FAIL',
                       f'games {len(games)}, distinct seeds {len({g["seed"] for g in games})}, days {sorted(days)}, per chunk (n, days) {per_chunk}, bad {bad[:5]}'))
    return items


def commit_time(commit):
    return int(subprocess.run(['git', '-C', REPO_ROOT, 'log', '-1', '--format=%ct', commit], capture_output=True, text=True, check=True).stdout.strip())


def v2(root, seeds, commit):
    t = commit_time(commit)
    now = time.time()
    res = {}
    for s in seeds:
        path = os.path.join(root, f's{s}', 'iter-3.json')
        if not os.path.exists(path):
            res[s] = ('pending', f'pending: iter-3 not yet written (commit time {t} = {time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))} UTC, now {int(now)} = {time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))} UTC)')
        else:
            m = os.path.getmtime(path)
            res[s] = ('PASS' if t < m else 'FAIL', f'commit time {t} {"<" if t < m else ">="} iter-3.json mtime {m:.0f} (iter-3 is {m - t:+.0f} s after the commit)')
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description='GW-LS read-only checks V1 and V2.')
    ap.add_argument('--root', default=os.path.join(SCRATCH, 'gwls'))
    ap.add_argument('--commit', default='28f6fcc42')
    ap.add_argument('--seeds', type=int, nargs='+', default=[200, 201])
    a = ap.parse_args(argv)
    statuses = []
    print('V1 (round 1, per seed)')
    for s in a.seeds:
        print(f'  seed {s}')
        for it in v1_seed(a.root, s):
            print(f'    [{it["status"]:7}] {it["name"]}: {it["detail"]}')
            if it['gated']:
                statuses.append(it['status'])
    v1 = 'FAIL' if 'FAIL' in statuses else ('PENDING' if 'pending' in statuses else 'PASS')
    print(f'  V1 verdict: {v1}' + ('  -> review verdict BLOCKED, rounds re-run: report to the coordinator immediately' if v1 == 'FAIL' else ''))
    print('V2 (commit time earlier than iter-3.json mtime)')
    r2 = v2(a.root, a.seeds, a.commit)
    for s, (st, detail) in r2.items():
        print(f'  seed {s}: [{st}] {detail}')
    sts = [st for st, _ in r2.values()]
    v2v = 'FAIL' if 'FAIL' in sts else ('PENDING' if 'pending' in sts else 'PASS')
    print(f'  V2 verdict: {v2v}')
    return v1, v2v


if __name__ == '__main__':
    main()
