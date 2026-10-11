"""Fixed home sample: TRAIN rows the domain-mode runs never touched in their pre-mode diary scan, split in two halves per family.

  python -m mainbrain.home_sample --data DATA_DIR --parents P200,P201 --runs RUN1,RUN2 --out-dir DIR [--per-family 80] [--seed home-check-0]

Writes home-H1.jsonl, home-H2.jsonl, home-H12.jsonl (each row plus "half") and home-manifest.json into DIR.
Exclusions per run seed, as domain/mode.py builds its pool: eligible prompts in train order, deduplicated, shuffled with Random(f'{seed}-diary'); the first `scanned` are excluded.
Prompts that appear in any DATA/dev/*.jsonl are excluded too.
"""
import argparse
import glob
import hashlib
import json
import os
import random
import re
import sys

import torch

from custom_io.data import MAX_PROMPT


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def run_info(run):
    """-> (seed, replay_fresh or None, scanned) from a run's log.jsonl; the seed falls back to sNNN in the folder name."""
    seed, fresh, scanned = None, None, None
    with open(os.path.join(run, 'log.jsonl')) as f:
        for line in f:
            if '"event": "start"' in line:
                e = json.loads(line)
                if e.get('seed') is not None:
                    seed = int(e['seed'])
                fresh = (e.get('constants') or {}).get('replay_fresh')
            elif '"event": "diary"' in line:
                scanned = json.loads(line)['scanned']
                break
    if seed is None:
        m = re.search(r's(\d+)', os.path.basename(os.path.normpath(run)))
        assert m, f'no seed in log or folder name of {run}'
        seed = int(m.group(1))
    assert scanned is not None, f'no diary event in {run}'
    return seed, fresh, scanned


def build_pool(train_rows, vchars, seed):
    pool = [r['prompt'] for r in train_rows if len(r['prompt']) <= MAX_PROMPT and set(r['prompt']) <= vchars]
    pool = list(dict.fromkeys(pool))
    random.Random(f'{seed}-diary').shuffle(pool)
    return pool


def sample_rows(eligible, excluded, per_family, seed):
    """eligible: rows in file order (deduplicated). -> (H1 rows, H2 rows, per-family counts)."""
    fams = {}
    for r in eligible:
        if r['prompt'] not in excluded:
            fams.setdefault(r['family'], []).append(r)
    rng = random.Random(seed)
    h1, h2, counts = [], [], {}
    for f in sorted(fams):
        pick = rng.sample(fams[f], min(per_family, len(fams[f])))
        half = len(pick) // 2
        h1 += [dict(r, half='H1') for r in pick[:half]]
        h2 += [dict(r, half='H2') for r in pick[half:]]
        counts[f] = dict(available=len(fams[f]), H1=half, H2=len(pick) - half)
    return h1, h2, counts


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--data', required=True)
    a.add_argument('--parents', required=True)
    a.add_argument('--runs', required=True)
    a.add_argument('--out-dir', required=True)
    a.add_argument('--per-family', type=int, default=80)
    a.add_argument('--seed', default='home-check-0')
    a = a.parse_args(argv)
    os.makedirs(a.out_dir, exist_ok=True)

    vchars = None
    for p in a.parents.split(','):
        c = set(torch.load(p, map_location='cpu', weights_only=True)['chars'])
        vchars = c if vchars is None else vchars & c

    train = []
    with open(os.path.join(a.data, 'train.jsonl')) as f:
        for line in f:
            train.append(json.loads(line))
    eligible, seen = [], set()
    for r in train:
        p = r['prompt']
        if len(p) <= MAX_PROMPT and set(p) <= vchars and p not in seen:
            seen.add(p)
            eligible.append(r)

    dev = set()
    for path in sorted(glob.glob(os.path.join(a.data, 'dev', '*.jsonl'))):
        with open(path) as f:
            for line in f:
                dev.add(json.loads(line)['prompt'])

    scanned_by_seed, seeds_of_runs = {}, {}
    for run in a.runs.split(','):
        seed, fresh, scanned = run_info(run)
        if fresh is True:
            sys.exit(f'error: {run} has replay_fresh true; its replay touched more train prompts')
        seeds_of_runs[run] = dict(seed=seed, replay_fresh=fresh)
        scanned_by_seed[seed] = max(scanned_by_seed.get(seed, 0), scanned)

    excluded, excl_counts = set(dev), {}
    for seed, n in sorted(scanned_by_seed.items()):
        pool = build_pool(train, vchars, seed)
        excl_counts[str(seed)] = len(pool[:n])
        excluded |= set(pool[:n])

    h1, h2, counts = sample_rows(eligible, excluded, a.per_family, a.seed)
    files = {}
    for name, rows in (('home-H1.jsonl', h1), ('home-H2.jsonl', h2), ('home-H12.jsonl', h1 + h2)):
        path = os.path.join(a.out_dir, name)
        with open(path, 'w') as f:
            for r in rows:
                f.write(json.dumps(r) + '\n')
        files[name] = dict(rows=len(rows), sha256=sha256_file(path))
    manifest = dict(args=vars(a), vchars=len(vchars), eligible=len(eligible), dev_prompts=len(dev),
                    excluded_total=len(excluded), excluded_per_seed=excl_counts, scanned_per_seed={str(k): v for k, v in scanned_by_seed.items()},
                    runs=seeds_of_runs, per_family=counts, files=files)
    with open(os.path.join(a.out_dir, 'home-manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)
    print(f'eligible {len(eligible)}  excluded {len(excluded)}  H1 {len(h1)}  H2 {len(h2)}', flush=True)


if __name__ == '__main__':
    main()
