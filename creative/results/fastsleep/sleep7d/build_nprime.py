"""Rebuild job 7's N' (= job 8's start) for one parent, exactly as creative/c2_keep.py does it (seed 0): raw B2 -> warm-up (2,048 warm add/mult rows, 4 visits,
lr 3e-4, skills replay) -> stepping-stone sleep with skills + warm-row replay (lr 3e-4, 4 visits). CPU. Saves warm.pt and Nprime.pt."""
import copy, json, math, os, sys, time
import torch
from creative import c2_stones, rules_real as R, sleep, stones
from creative.pilot import skills_eval

ckpt, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
torch.set_num_threads(4)
seed, device, DATA = 0, 'cpu', 'creative/data/c2'
t0 = time.time()
replay = sleep.load_replay(os.path.expanduser('~/work/data/train.jsonl'), None, seed)
warm_rows = R.warm_records(R.load_split(DATA, 'warm'))
m0, vocab, meta, w = c2_stones._warm(ckpt, warm_rows, replay, 4, 3e-4, seed, device)
sleep.save_parent(m0, meta['name'], meta['cfg'], vocab, os.path.join(out, 'warm.pt'), step=(meta['step'] or 0), warmup=True)
print('warm', w, round(time.time() - t0), flush=True)
ss_rows, ss_info = stones.make_stone_rows(2048, seed)
recs = stones.solver_records(ss_rows)
N = copy.deepcopy(m0)
v, lr = 4, 3e-4
u = sleep.max_updates(2048, 64, bool(replay), v)
mv = max(v, math.ceil(u * 32 / max(len(recs), 1)))
so = sleep.sleep(N, recs, replay, vocab, sleep.SleepCfg(updates=u, batch=64, lr=lr, warmup=20, seed=seed, max_visits=mv), device, replay_extra=warm_rows)
sleep.save_parent(N, meta['name'], meta['cfg'], vocab, os.path.join(out, 'Nprime.pt'), step=(meta['step'] or 0), warmup=True)
print('Nprime', dict(updates=u, records=len(recs), last_loss=sum(so['loss'][-10:]) / 10), round(time.time() - t0), flush=True)
sk = skills_eval(N, os.path.expanduser('~/work/data_big'), device)
json.dump(dict(ckpt=ckpt, warm=w, nprime=dict(updates=u, records=len(recs)), skills=sk, seconds=time.time() - t0), open(os.path.join(out, 'build.json'), 'w'), indent=1)
print('done', round(time.time() - t0), flush=True)
