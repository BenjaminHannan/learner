"""E0 (forgetting solve, DRAFT for coordinator review): score Main brain's final guard checkpoints on the 1,360 and the
6,800-row DEV in_dist under the house rule (domain/harm.py harm_measure 5.0 / 1.5). Measurement only; never writes to a run folder.

  CUSTOM_IO_DATA=<seed-1 build> python e0_score.py --repo <learner checkout> --big <sk200k_big>/dev/in_dist.jsonl \
      --out e0.json RUN_DIR [RUN_DIR ...]

RUN_DIR = a Main brain run folder (summary.json + night_K/checkpoint.pt), e.g. /mnt/project-files/main-brain/runs/sheet-s200-kf99n-kl10-soft10.
Final checkpoint as domain/analyze.py picks it: summary['final_checkpoint'] if on disk, else night_{nights_run}. Parent: summary['parent'].
"""
import argparse, base64, glob, hashlib, json, os, re, sys, time
a = argparse.ArgumentParser()
a.add_argument('runs', nargs='+'); a.add_argument('--repo', required=True); a.add_argument('--big', required=True)
a.add_argument('--small', default=None); a.add_argument('--out', required=True); a.add_argument('--threads', type=int, default=4)
a = a.parse_args()
sys.path.insert(0, a.repo)
import torch
from custom_io.data import load_rows, DEFAULT_DATA
from domain import harm
torch.set_num_threads(a.threads)
small = a.small or os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
assert sha(small) == 'f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86', 'wrong 1,360-row DEV'
devs = {'small': (small, load_rows(small)), 'big': (a.big, load_rows(a.big))}
assert len(devs['big'][1]) == 6800 and [r['id'] for r in devs['big'][1] if r['id'] in {x['id'] for x in devs['small'][1]}] is not None
pack = lambda bits: base64.b64encode(bytes(int(''.join(map(str, bits[i:i+8])).ljust(8, '0'), 2) for i in range(0, len(bits), 8))).decode()
cache, out = {}, {'dev_small_sha256': sha(small), 'dev_big_sha256': sha(a.big), 'runs': {}}
def hits(ck, tag):
    k = (os.path.realpath(ck), tag)
    if k not in cache:
        t = time.time(); h, acc = harm.in_dist_hits(ck, devs[tag][1]); cache[k] = h
        print(f'  scored {os.path.basename(os.path.dirname(ck))}/{os.path.basename(ck)} on {tag} ({len(h)} rows) {100*sum(h)/len(h):.2f} in {time.time()-t:.0f}s', flush=True)
    return cache[k]
for run in a.runs:
    s = json.load(open(os.path.join(run, 'summary.json')))
    n = int(s['nights_run'])
    nights = {int(re.search(r'night_(\d+)', p).group(1)): p for p in glob.glob(os.path.join(run, 'night_*', 'checkpoint.pt'))}
    fin = s.get('final_checkpoint')
    if not fin or not os.path.exists(fin):
        fin = nights[n]
    par = s['parent']
    print(f'{run}: nights_run {n}, final {fin}, parent {par}', flush=True)
    res = {'final_checkpoint': fin, 'final_sha256': sha(fin), 'parent': par, 'parent_sha256': sha(par), 'nights_run': n}
    for tag in ('small', 'big'):
        rows = devs[tag][1]; ph, ch = hits(par, tag), hits(fin, tag)
        h = harm.harm_measure(ph, ch, rows, 5.0, 1.5)
        b = sum(p and not c for p, c in zip(ph, ch)); c = sum(c and not p for p, c in zip(ph, ch))
        res[tag] = dict(n=len(rows), parent=round(h['in_dist_a'], 2), final=round(h['in_dist_b'], 2), drop=round(h['in_dist_drop'], 2), lost=b, gained=c,
                        fired=h['fired'], passes=bool(h['passes']),
                        worst=sorted(({'family': f, 'a': round(v['a'], 1), 'b': round(v['b'], 1), 'drop': round(v['drop'], 1), 'lo': round(v['lo'], 1), 'hi': round(v['hi'], 1)}
                                      for f, v in h['families'].items()), key=lambda x: -x['drop'])[:4],
                        parent_hits=pack(ph), final_hits=pack(ch))
        print(f'  {tag}: {res[tag]["parent"]} -> {res[tag]["final"]} drop {res[tag]["drop"]} (lost {b}, gained {c}) fired {h["fired"]} '
              f'{"PASS" if h["passes"] else "FAIL"}', flush=True)
    out['runs'][run] = res
json.dump(out, open(a.out, 'w'))
print('wrote', a.out)
