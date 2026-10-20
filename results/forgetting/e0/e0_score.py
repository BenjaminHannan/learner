"""E0 (forgetting solve, DRAFT for coordinator review): score Main brain's final guard checkpoints on the 1,360 and the
6,800-row DEV in_dist under the house rule (domain/harm.py harm_measure 5.0 / 1.5). Measurement only; never writes to a run folder.

  CUSTOM_IO_DATA=<seed-1 build> python results/forgetting/e0/e0_score.py --big <sk200k_big>/dev/in_dist.jsonl \
      --out e0.json RUN_DIR [RUN_DIR ...]

--repo defaults to the learner checkout this script sits in (it must hold custom_io/ and domain/: claude/forgetting-round-g);
e0.json records that checkout's path, git commit and CUSTOM_IO_DATA. --parent overrides every summary's parent (as analyze.py's --parent).
An existing --out is refused unless --overwrite. Runs with summary addon 'per_tool' are refused (analyze.py's A18 makes DM3 pass by
construction there, which E0 does not reproduce).

RUN_DIR = a Main brain run folder (summary.json + night_K/checkpoint.pt), e.g. /mnt/project-files/main-brain/runs/sheet-s200-kf99n-kl10-soft10.
Final checkpoint by domain/analyze.py's rule, notes worded as analyze.py words them (final_checkpoint_of, night discovery =
domain/score.py night_checkpoints). Before any model loads: both DEV files are identified by sha256 (check_devs) and every run is
resolved (resolve_runs: summary, nights_run >= 1, nights, final checkpoint, parent on disk); any problem stops the run with nothing scored.
e0.json is written atomically (temp file + rename) once before scoring (with the planned runs, replacing any older file) and again after
each run, so a later failure keeps the runs already scored.
"""
import argparse, base64, hashlib, json, os, sys, time

SMALL_SHA = 'f975d9fb312c02d759df991fa3bbb9ac73912d5f77cdc0e6991abd7980158b86'   # 1,360-row DEV = learn_probe.DEV_IN_DIST_SHA256 (asserted in main)
BIG_SHA = '3e3a5edb05c7eee8c412edc224a3daa144ee6f9ee048a28db945e577db42aeaa'     # 6,800-row DEV, seed-1 build, --dev-per-cell 200 (ship instrument)


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def check_devs(small, big, small_sha=SMALL_SHA, big_sha=BIG_SHA):
    """Refuse unless both DEV files are the expected ones: SystemExit naming a missing file or the file whose sha256 differs. -> (small_sha, big_sha)."""
    for tag, p in (('small', small), ('big', big)):
        if not os.path.exists(p):
            raise SystemExit(f'E0: the {tag} DEV {p} does not exist (small: set CUSTOM_IO_DATA to the seed-1 build or pass --small; big: --big)')
    got = {'small': (small, sha(small), small_sha), 'big': (big, sha(big), big_sha)}
    for tag, (p, s, want) in got.items():
        if s != want:
            raise SystemExit(f'E0: the {tag} DEV {p} has sha256 {s[:12]}, expected {want[:12]}: wrong DEV file, nothing scored')
    return got['small'][1], got['big'][1]


def final_checkpoint_of(run, summary, night_checkpoints=None):
    """-> (final checkpoint path, notes) by domain/analyze.py's rule and wording: nights 1..N must all exist (SystemExit: missing night
    checkpoints [...]), nights after N are ignored with a note, summary['final_checkpoint'] if on disk else the night_N file (note),
    and a note when the final is not the run folder's night_N file. night_checkpoints defaults to domain/score.py's."""
    if night_checkpoints is None:
        from domain.score import night_checkpoints
    if 'nights_run' not in summary:
        raise SystemExit(f'E0: {run}: summary.json has no nights_run')
    n = int(summary['nights_run'])
    if n < 1:
        raise SystemExit(f'E0: {run}: nights_run is {n}: the run has no night checkpoint to score')
    nights = dict(night_checkpoints(run))
    missing = [k for k in range(1, n + 1) if k not in nights]
    if missing:
        raise SystemExit(f'E0: {run}: missing night checkpoints {missing}')
    notes = []
    extra = sorted(k for k in nights if k > n)
    if extra:
        notes.append(f'night checkpoints after nights_run={n} were ignored: {extra}')
    fin = summary.get('final_checkpoint')
    if not fin or not os.path.exists(fin):
        notes.append(f'summary final_checkpoint not on disk ({fin}); used the night_{n} file in the run folder')
        fin = nights[n]
    if os.path.realpath(fin) != os.path.realpath(nights[n]):
        notes.append('summary final_checkpoint is not the run folder night_%d file (path differs)' % n)
    return fin, notes


def resolve_runs(runs, night_checkpoints=None, parent=None):
    """Every run checked before anything is scored: summary.json readable, not an A18 per_tool add-on run, final checkpoint by
    final_checkpoint_of, parent on disk (parent, when given, replaces every summary's parent, as analyze.py's --parent).
    -> [(run, summary, final, notes)]; SystemExit naming the first bad run."""
    out = []
    for run in runs:
        sp = os.path.join(run, 'summary.json')
        if not os.path.exists(sp):
            raise SystemExit(f'E0: {run}: no summary.json')
        s = json.load(open(sp))
        if s.get('addon') == 'per_tool':
            raise SystemExit(f"E0: {run}: summary addon 'per_tool' (analyze.py A18: DM3 passes by construction); not an E0 run")
        if parent:
            s = dict(s, parent=parent)
        fin, notes = final_checkpoint_of(run, s, night_checkpoints)
        if not s.get('parent') or not os.path.exists(s['parent']):
            raise SystemExit(f'E0: {run}: parent checkpoint {s.get("parent")} not on disk')
        out.append((run, s, fin, notes))
    return out


def write_json_atomic(obj, path):
    """Write obj as JSON to a temp file next to path, then rename it over path (os.replace): a kill mid-write leaves the old file whole."""
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def pack(bits):
    return base64.b64encode(bytes(int(''.join(map(str, bits[i:i + 8])).ljust(8, '0'), 2) for i in range(0, len(bits), 8))).decode()


def main(argv=None):
    a = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    a.add_argument('runs', nargs='+'); a.add_argument('--repo', default=os.path.normpath(os.path.join(here, '..', '..', '..')))
    a.add_argument('--big', required=True); a.add_argument('--parent', default=None)
    a.add_argument('--small', default=None); a.add_argument('--out', required=True); a.add_argument('--threads', type=int, default=4)
    a.add_argument('--overwrite', action='store_true')
    a = a.parse_args(argv)
    if not all(os.path.isdir(os.path.join(a.repo, d)) for d in ('custom_io', 'domain')):
        raise SystemExit(f'E0: --repo {a.repo} has no custom_io/ and domain/: use a checkout of claude/forgetting-round-g')
    if os.path.exists(a.out) and not a.overwrite:
        raise SystemExit(f'E0: {a.out} exists; pass --overwrite to replace it (or pick another --out)')
    sys.path.insert(0, a.repo)
    import torch
    from custom_io.data import load_rows, DEFAULT_DATA
    from domain import harm
    from domain.analyze import sha256_file
    from domain.far.learn_probe import DEV_IN_DIST_SHA256
    if SMALL_SHA != DEV_IN_DIST_SHA256:
        raise SystemExit('E0: the pinned 1,360-row DEV sha changed in the repo: update SMALL_SHA')
    torch.set_num_threads(a.threads)
    small = a.small or os.path.join(DEFAULT_DATA, 'dev', 'in_dist.jsonl')
    s_sha, b_sha = check_devs(small, a.big)   # before any model is loaded
    plan = resolve_runs(a.runs, parent=a.parent)   # every run checked before any scoring
    import subprocess
    head = subprocess.run(['git', '-C', a.repo, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip() or None
    devs = {'small': load_rows(small), 'big': load_rows(a.big)}
    cache, out = {}, {'dev_small_sha256': s_sha, 'dev_big_sha256': b_sha, 'repo': os.path.abspath(a.repo), 'repo_commit': head,
                      'custom_io_data': os.environ.get('CUSTOM_IO_DATA'), 'parent_override': a.parent, 'runs': {}, 'planned': [r for r, _, _, _ in plan]}
    write_json_atomic(out, a.out)   # replaces any e0.json from an earlier invocation before the first run is scored

    def hits(ck, tag):
        k = (os.path.realpath(ck), tag)
        if k not in cache:
            t = time.time(); h, _ = harm.in_dist_hits(ck, devs[tag]); cache[k] = h
            print(f'  scored {os.path.basename(os.path.dirname(ck))}/{os.path.basename(ck)} on {tag} ({len(h)} rows) {100 * sum(h) / len(h):.2f} in {time.time() - t:.0f}s', flush=True)
        return cache[k]

    for run, s, fin, notes in plan:
        par = s['parent']
        print(f'{run}: nights_run {s["nights_run"]}, final {fin}, parent {par}' + ''.join(f'\n  NOTE {x}' for x in notes), flush=True)
        res = {'final_checkpoint': fin, 'final_sha256': sha256_file(fin), 'parent': par, 'parent_sha256': sha256_file(par),
               'nights_run': int(s['nights_run']), 'notes': notes}
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
        write_json_atomic(out, a.out)   # after each run: a later failure keeps what is scored
    print('wrote', a.out)


if __name__ == '__main__':
    main()
