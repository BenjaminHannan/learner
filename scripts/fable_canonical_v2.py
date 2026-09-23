"""Screen v2: Astra's canonical-operator runner, unchanged, pointed at a new folder with a longer
registered exposure and passive training-batch logging (Fable, 2026-09-19 EDT). Additive only."""
from __future__ import annotations
import argparse, datetime, json, os, subprocess, sys, time
from pathlib import Path

import astra_canonical_operator_run as R
A, P, C, torch, ROOT = R.A, R.P, R.C, R.torch, R.ROOT
V1 = P.OUT
OUT = ROOT/'artifacts/fable-canonical-operator-v2-20260920'
R.OUT = OUT                      # worker/check_manifest write and read here; panels stay in V1
_step = A.training_step


def logged_step(model, optimizer, batch, step):
    _step(model, optimizer, batch, step)
    if (step+1) % 500 == 0:
        was = model.training
        model.eval()
        with torch.no_grad():
            c = (model(batch.canonical).argmax(-1) == batch.canonical_targets.answer).float().mean()
            m = (model(batch.monolithic).argmax(-1) == batch.monolithic_targets.answer).float().mean()
        model.train(was)
        print(json.dumps(dict(train_batch=step+1, canonical_acc=round(float(c), 4), monolithic_acc=round(float(m), 4))), flush=True)


A.training_step = logged_step


def freeze(updates, training_seconds):
    v1 = json.loads((V1/'astra_canonical_operator_launch.json').read_text())
    files = {name: C.sha(ROOT/name) for name in v1['files']
             if not name.startswith('design/') and (ROOT/name).exists()}
    changed = [n for n in files if files[n] != v1['files'][n]]
    assert not changed, changed
    for extra in ('scripts/fable_canonical_v2.py', str((OUT/'PREREGISTRATION.md').relative_to(ROOT))):
        files[extra] = C.sha(ROOT/extra)
    manifest = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    schedule=dict(updates=updates, training_seconds=training_seconds, work_seconds=1740,
                                  terminate_seconds=1770, visits_per_update=16),
                    exclusion_path=v1['exclusion_path'], panels=v1['panels'], files=files,
                    v1_launch_sha256=C.sha(V1/'astra_canonical_operator_launch.json'))
    C.write_new(OUT/'astra_canonical_operator_launch.json', manifest)
    print(len(files), 'files frozen', C.sha(OUT/'astra_canonical_operator_launch.json'))


def wave(seeds, name):
    manifest = R.check_manifest()
    folder = OUT/name
    folder.mkdir(exist_ok=False)
    cap, start = manifest['schedule']['terminate_seconds'], time.monotonic()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    procs = []
    for seed in seeds:
        handle = (folder/f'seed-{seed}.log').open('x')
        procs.append(subprocess.Popen([R.PYTHON, '-B', str(Path(__file__).resolve()), 'worker', '--seed', str(seed),
                                       '--wave-start', str(start)], stdout=handle, stderr=subprocess.STDOUT,
                                      env=env, start_new_session=True))
    while any(p.poll() is None for p in procs):
        if time.monotonic()-start >= cap-2:
            for p in procs:
                if p.poll() is None: p.terminate()
            time.sleep(.5)
            for p in procs:
                if p.poll() is None: p.kill()
            break
        time.sleep(.5)
    exits = [p.wait() for p in procs]
    complete = all(c == 0 for c in exits) and all((OUT/f'astra_canonical_operator_seed-{s}/completion.json').exists() for s in seeds)
    C.write_new(folder/'completion.json', dict(seconds=time.monotonic()-start, exit_codes=exits, complete=complete, seeds=list(seeds)))
    print(json.dumps(dict(seconds=time.monotonic()-start, exit_codes=exits, complete=complete)), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['freeze', 'wave', 'worker'])
    ap.add_argument('--seeds', default='0,1,2'); ap.add_argument('--name', default='wave-1')
    ap.add_argument('--seed', type=int); ap.add_argument('--wave-start', type=float)
    ap.add_argument('--updates', type=int, default=9000); ap.add_argument('--training-seconds', type=int, default=1500)
    args = ap.parse_args()
    R.configure()
    if args.command == 'freeze': freeze(args.updates, args.training_seconds)
    elif args.command == 'wave': wave([int(s) for s in args.seeds.split(',')], args.name)
    else: R.worker(args.seed, args.wave_start)
