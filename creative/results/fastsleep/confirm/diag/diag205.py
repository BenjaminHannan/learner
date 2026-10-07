"""Read-only: why did memory+old harm skills on s205 (3.9 points)? No retuning; the confirm verdict stands."""
import os, random, collections, json, torch, torch.nn.functional as F
from creative import fastsleep as fs, sleep
from custom_io.data import load_rows
from custom_io.evalx import CHAIN5, evaluate
out = '/mnt/project-files/fast-sleep/confirm/' + os.environ.get('S', 's205')
N, vocab, meta, s = fs.load_setup(out)
replay = sleep.load_replay('/root/work/data/train.jsonl', None, 0)
recs = s['records']['W']
m, info = fs.m_knn(N, recs, replay, vocab, 'cpu', len(recs), **fs.MEMORY_OLD[1])
print('theta_t', info['theta_t'], 'theta_ans', info['theta_ans'])
rows = [r for r in load_rows('/root/work/data_big/dev/in_dist.jsonl') if r['family'] in CHAIN5]
fam = collections.defaultdict(list)
for r in rows: fam[r['family']].append(r)
N.eval(); m.eval()
for f, rs in sorted(fam.items()):
    a, b = evaluate(N, rs, 256, 'cpu')['exact'], evaluate(m, rs, 256, 'cpu')['exact']
    print(f'{f:22s} n {len(rs):4d}  N {a:5.1f}  M {b:5.1f}  drop {a-b:5.1f}')
cal = random.Random(0).sample(replay, len(recs))
cf = collections.Counter(r['family'] for r in cal)
print('calibration rows', len(cal), 'chain5 among them', sum(v for k, v in cf.items() if k in CHAIN5), dict((k, cf[k]) for k in CHAIN5))
mem = m._mem
best = lambda z, keys: (F.normalize(z.float(), dim=-1) @ keys.T).max(-1).values
def fire_rate(rs, name):
    f = fs.head_inputs(N, rs, vocab, 'cpu')
    fr = [float((best(f['z'][:, t], e['keys']) >= mem.theta_t[t]).float().mean()) for t, e in enumerate(mem.steps)]
    fa = float((best(f['zf'], mem.ans['keys']) >= mem.theta_ans).float().mean())
    print(f'{name:34s} gate fires per step', [round(x, 3) for x in fr], 'answer', round(fa, 3))
fire_rate(cal, 'calibration rows (TRAIN, all fams)')
fire_rate(rows, 'harm rows (DEV chain5)')
tr5 = [r for r in replay if r['family'] in CHAIN5]
fire_rate(random.Random(1).sample(tr5, 1000), 'TRAIN chain5 rows (1000)')
