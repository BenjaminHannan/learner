#!/usr/bin/env python3
"""python3 -I tests/check_queue_a8.py CIO_ROOT [QUEUE_DIR]   (any Linux box, no GPU, a second)

Builds the command line custom_io.local_runner would run for every line of queue/8aB3G2A4-pc.txt and queue/8aB3G2A8-pc.txt and checks that they differ ONLY in the job name / --out folder
(queue name and job name) and in `--accum B3G2=8` (A4: `--accum B3G2=4`); the `# ENV` lines, the `# MEM` numbers, the run kinds and every other token are equal.

CIO_ROOT = a folder that holds the repo's custom_io at commit 74d6e92c75, the code the PC's src-b3g2 is pinned to:
    mkdir X && git archive 74d6e92c75 custom_io | tar -x -C X      (then: python3 -I tests/check_queue_a8.py X)
QUEUE_DIR defaults to the pack's queue/ folder. Nothing is started or written; the paths are only strings (Windows-style, as on the PC)."""
import sys
from pathlib import Path

root = Path(sys.argv[1])
qdir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / 'queue'
sys.path.insert(0, str(root))
from custom_io import local_runner as L

work = Path('C:/Users/benja/custom-io/work')
res = {}
for name in ('8aB3G2A4-pc', '8aB3G2A8-pc'):
    runs = L.parse_queue(qdir / (name + '.txt'), work)
    cmds = [(rname, kind, mem, L.command(kind, args, work, work / 'results' / name / rname, 'cuda')) for rname, kind, args, mem in runs]
    res[name] = (runs, cmds, L.queue_env(qdir / (name + '.txt')))
a, b = res['8aB3G2A4-pc'], res['8aB3G2A8-pc']
assert len(a[0]) == len(b[0]) == 2, 'expected the data line and the job line in both files'
assert a[2] == b[2], 'ENV lines differ'
print('local_runner.parse_queue / command from', L.__file__)
print('A8 runs (name, kind, MEM MiB):', [(r[0], r[1], r[3]) for r in b[0]])
print('ENV lines equal:', a[2] == b[2], '|', b[2])
for (ra, ka, ma, ca), (rb, kb, mb, cb) in zip(a[1], b[1]):
    assert ka == kb and ma == mb and len(ca) == len(cb), (ka, kb, ma, mb, len(ca), len(cb))
    diffs = [(i, x, y) for i, (x, y) in enumerate(zip(ca, cb)) if x != y]
    print(f'--- {ka}: {ra} (A4) vs {rb} (A8); MEM {ma} MiB in both; {len(diffs)} differing token(s) of {len(ca)}')
    for i, x, y in diffs:
        print(f'    token {i}: A4 {x!r}')
        print(f'              A8 {y!r}')
    back = [t.replace('8aB3G2A8', '8aB3G2A4').replace('B3G2=8', 'B3G2=4') for t in cb]
    assert back == ca, 'the commands differ by more than the job / queue name in --out and --accum'
print('OK: after undoing 8aB3G2A8 -> 8aB3G2A4 (in --out) and --accum B3G2=8 -> 4, the A8 command equals the A4 command, token for token')
