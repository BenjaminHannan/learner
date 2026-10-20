"""E0 (forgetting solve, DRAFT for coordinator review): score Main brain's final guard checkpoints on the 1,360 and the
6,800-row DEV in_dist under the house rule (domain/harm.py harm_measure 5.0 / 1.5). Measurement only; never writes to a run folder.

  CUSTOM_IO_DATA=<seed-1 build> python e0_score.py --repo <learner checkout> --big <sk200k_big>/dev/in_dist.jsonl \
      --out e0.json RUN_DIR [RUN_DIR ...]

RUN_DIR = a Main brain run folder (summary.json + night_K/checkpoint.pt), e.g. /mnt/project-files/main-brain/runs/sheet-s200-kf99n-kl10-soft10.
Final checkpoint exactly as domain/analyze.py picks it (final_checkpoint_of): every night 1..N must exist; summary['final_checkpoint']
if on disk, else night_N; notes when it is not the run folder's night_N file. Parent: summary['parent'].
Both DEV files are identified by sha256 (check_devs); a file with any other content stops the run before any scoring.
"""
import argparse, base64, glob, hashlib, json, os, re, sys, time

SMALL_SHA = 'f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86'   # 1,360-row DEV, seed-1 build, --dev-per-cell 40
BIG_SHA = '3e3a5edb05c7eee8c412edc224a3daa144ee6f9ee048a28db945e577db42aeaa'     # 6,800-row DEV, seed-1 build, --dev-per-cell 200 (ship instrument)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def check_devs(small, big, small_sha=SMALL_SHA, big_sha=BIG_SHA):
    """Refuse unless both DEV files are the expected ones: SystemExit naming the file whose sha256 differs. -> (small_sha, big_sha)."""
    got = {'small': (small, sha(small), small_sha), 'big': (big, sha(big), big_sha)}
    for tag, (p, s, want) in got.items():
        if s != want:
            raise SystemExit(f'E0: the {tag} DEV {p} has sha256 {s[:12]}, expected {want[:12]}: wrong DEV file, nothing scored')
    return got['small'][1], got['big'][1]


def night_checkpoints(run):
    """[(K, path)] sorted, as domain/score.py night_checkpoints."""
    found = []
    for p in glob.glob(os.path.join(run, 'night_*', 'checkpoint.pt')):
        found.append((int(re.search(r'night_(\d+)', p).group(1)), p))
    return sorted(found)


def final_checkpoint_of(run, summary):
    """-> (final checkpoint path, notes), the rule of domain/analyze.py: nights 1..N must all exist (SystemExit naming the missing ones),
    summary['final_checkpoint'] if on disk else the night_N file, plus a note when the two differ."""
    n = int(summary['nights_run'])
    nights = dict(night_checkpoints(run))
    missing = [k for k in range(1, n + 1) if k not in nights]
    if missing:
        raise SystemExit(f'E0: {run}: missing night checkpoints {missing}')
    notes = []
    fin = summary.get('final_checkpoint')
    if not fin or not os.path.exists(fin):
        notes.append(f'summary final_checkpoint not on disk ({fin}); used the night_{n} file in the run folder')
        fin = nights[n]
    if os.path.realpath(fin) != os.path.realpath(nights[n]):
        notes.append(f'summary final_checkpoint is not the run folder night_{n} file (path differs)')
    return fin, notes


def pack(bits):
    return base64.b64encode(bytes(int(''.join(map(str, bits[i:i + 8])).ljust(8, '0'), 2) for i in range(0, len(bits), 8))).decode()


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('runs', nargs='+'); a.add_argument('--repo', required=True); a.add_argument('--big', required=True)
    a.add_argument('--small', default=None); a.add_argument('--out', required=True); a.add_argument('--threads', type=int, default=4)
    a = a.parse_args(argv)
    sys.path.insert(0, a.repo)
    import torch
    from custom_io.data import load_rows, DEFAULT_DATA
    from domain import harm
    torch.set_num_threads(a.threads)
    small = a.small or os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl')
    s_sha, b_sha = check_devs(small, a.big)   # before any model is loaded
    devs = {'small': load_rows(small), 'big': load_rows(a.big)}
    cache, out = {}, {'dev_small_sha256': s_sha, 'dev_big_sha256': b_sha, 'runs': {}}

    def hits(ck, tag):
        k = (os.path.realpath(ck), tag)
        if k not in cache:
            t = time.time(); h, _ = harm.in_dist_hits(ck, devs[tag]); cache[k] = h
            print(f'  scored {os.path.basename(os.path.dirname(ck))}/{os.path.basename(ck)} on {tag} ({len(h)} rows) {100 * sum(h) / len(h):.2f} in {time.time() - t:.0f}s', flush=True)
        return cache[k]

    for run in a.runs:
        s = json.load(open(os.path.join(run, 'summary.json')))
        fin, notes = final_checkpoint_of(run, s)
        par = s['parent']
        print(f'{run}: nights_run {s["nights_run"]}, final {fin}, parent {par}' + ''.join(f'\n  NOTE {x}' for x in notes), flush=True)
        res = {'final_checkpoint': fin, 'final_sha256': sha(fin), 'parent': par, 'parent_sha256': sha(par), 'nights_run': int(s['nights_run']), 'notes': notes}
        for tag in ('small', 'big'):
            rows = devs[tag]; ph, ch = hits(par, tag), hits(fin, tag)
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


if __name__ == '__main__':
    main()
