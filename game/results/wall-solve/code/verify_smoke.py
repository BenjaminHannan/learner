"""Smoke checks: (a) the recording wrapper changes nothing (plain imitate.play_games on the same worlds gives the same views and moves);
(b) the log-probs saved at play time have the same argmax as a fresh play.move_logprobs batch over the same views (the probe eval path).
python verify_smoke.py SEED ROOT"""
import gzip, json, os, sys
import numpy as np, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from game import imitate, play
from custom_io.models import load_model

seed, root = int(sys.argv[1]), sys.argv[2]
torch.set_num_threads(2)
rs = common.RUN_SEED[seed]
out = f'{root}/s{rs}'
with gzip.open(f'{out}/play-d0.json.gz', 'rt') as f:
    saved = json.load(f)
z = np.load(f'{out}/play-d0.lp.npz')
m = load_model(common.ckpt(seed)).eval()
n = len(saved)
pol = play.move_policy(m, 'sample', bs=64, temp=1.0)
g = imitate.play_games(pol, [play.practice_seed(rs, 0, i) for i in range(n)], [[imitate.ACT_TAG, rs, 0, i] for i in range(n)], 0.10, 1000)
same = all(a['views'] == b['views'] and a['actions'] == b['actions'] and a['events'] == [tuple(e) for e in b['events']] or
           (a['views'] == b['views'] and a['actions'] == b['actions'] and [list(e) for e in a['events']] == b['events']) for a, b in zip(g, saved))
print('plain play == recorded play:', same)
views = [v for s in saved for v in s['views']]
lp2 = play.move_logprobs(m, views)
lp1 = z['lp'].astype(np.float64)
print('argmax equal:', float((lp1.argmax(1) == lp2.argmax(1)).mean()), 'max abs lp diff', float(np.abs(lp1 - lp2).max()))
