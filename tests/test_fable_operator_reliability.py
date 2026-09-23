"""Checks for scripts/fable_operator_reliability.py. Plain script; prints ALL N CHECKS PASSED.

Run whole:   python3.12 -B tests/test_fable_operator_reliability.py
Run a group: python3.12 -B tests/test_fable_operator_reliability.py --only stream
Groups: stream, recipe, manifest, summary, model, portable.

``portable`` is the load-bearing one: it builds a deploy bundle into a temporary
directory, freezes a roster there and runs a two-seed ``wave --parallel 2`` of at most
20 updates against a freshly generated throwaway panel.  Nothing in it touches the
registered checkout, the registered panels or a registered seed: the smoke roster is
993601/993602 and the only panel scored is generated on the spot.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'scripts'))

import fable_operator_reliability as REL                                  # noqa: E402
import fable_reliability_bundle as BUN                                    # noqa: E402

SMOKE_SEEDS = (993601, 993602)
CHECKS = 0
VARIANT = 'grow-blind'


def check(name, condition, detail=''):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(f'FAILED [{CHECKS}] {name}: {detail}')
    print(f'ok [{CHECKS}] {name}' + (f' -- {detail}' if detail else ''), flush=True)


def source_repo():
    return REL.find_repo(os.environ.get('FABLE_RELIABILITY_REPO'))


_RECIPE = {}


def recipe():
    if not _RECIPE:
        _RECIPE.update(REL._import_recipe(source_repo()))
        REL.configure_torch(_RECIPE)
    return _RECIPE


def equal_batch(a, b):
    torch = recipe()['torch']

    def tensors(batch):
        out = []
        for part in (batch.canonical, batch.monolithic):
            out += [part.memory, part.questions, part.owner, part.eligible]
        for part in (batch.canonical_targets, batch.monolithic_targets):
            out += [part.answer, part.lines]
        return out
    ta, tb = tensors(a), tensors(b)
    return len(ta) == len(tb) and all(torch.equal(x, y) for x, y in zip(ta, tb))


# ------------------------------------------------------------------------------ stream

def test_stream():
    first = [REL.data_stream(100).random() for _ in range(3)]
    again = [REL.data_stream(100).random() for _ in range(3)]
    other = [REL.data_stream(101).random() for _ in range(3)]
    check('per-seed stream is reproducible', first == again, str(first[:1]))
    check('per-seed stream differs across seeds', first != other,
          f'{first[0]:.6f} vs {other[0]:.6f}')
    seen = {tuple(REL.data_stream(s).random() for _ in range(2)) for s in range(100, 148)}
    check('all 48 roster streams are distinct', len(seen) == 48, f'{len(seen)} distinct')
    check('stream is not the frozen 1101 stream',
          REL.data_stream(100).random() != random.Random(1101).random())
    check('stream tag is namespaced and versioned',
          REL.STREAM_TAG == 'fable-reliability-stream-v1', REL.STREAM_TAG)


# ------------------------------------------------------------------------------ recipe

def test_recipe():
    r = recipe()
    S, A = r['S'], r['A']
    params = REL.build_manifest(source_repo(), VARIANT, [100], 6000, 1500)['startup']
    check('frozen hyperparameters are the registered ones',
          (params['grow_g1'], params['grow_g2'], params['blind_lines'],
           params['hint_updates'], params['balance']) == (1500, 3000, 16, 1000, False),
          json.dumps(params))

    S.configure_variant(VARIANT, seed=100, **params)
    check('grow-blind uses the startup module batch builder, not a copy',
          A.training_batch is S.training_batch_blind)
    wrapped = [c.cell_contents for c in (A.training_step.__closure__ or ())]
    check('grow-blind uses the startup module step, not a copy',
          S._step_answer_only in wrapped, A.training_step.__qualname__)

    mine = A.training_batch(REL.data_stream(100), 16, frozenset())
    S.configure_variant(VARIANT, seed=100, **params)
    theirs = S.training_batch_blind(random.Random(f'{REL.STREAM_TAG}:100'), 16, frozenset())
    check('batch from the per-seed stream == fable_operator_startup on the same RNG',
          equal_batch(mine, theirs))

    S.configure_variant(VARIANT, seed=100, **params)
    frozen_a = S.training_batch_blind(random.Random(1101), 16, frozenset())
    S.configure_variant(VARIANT, seed=100, **params)
    frozen_b = A.training_batch(random.Random(1101), 16, frozenset())
    check('the wrapper changes nothing but the stream (1101 reproduces the frozen batch)',
          equal_batch(frozen_a, frozen_b))

    S.configure_variant(VARIANT, seed=101, **params)
    elsewhere = A.training_batch(REL.data_stream(101), 16, frozenset())
    check('a different seed really is a different data draw',
          not equal_batch(mine, elsewhere))

    # Every question the blind builder could emit for visit 0 of this stream: the check
    # runs against the FULL story, so enumerate one-hop/LINK and two-hop forms over its
    # visible fact rows.  Whichever record it builds first must therefore be forbidden.
    from premonition.toy_ladder import LadderSpec, visit
    rows, _, _ = visit(LadderSpec(), REL.data_stream(100), training=True)
    full = [[] if row.question else list(row.tokens) for row in rows]
    forbidden = set()
    for row in full:
        if (len(row) >= 4 and row[0] == A.WORLD
                and A.ENTITY_MIN <= row[1] < A.ENTITY_MAX and 8 <= row[2] <= A.LINK):
            forbidden.add(A.visible_signature(
                full, [A.QUESTION, row[1], row[2], A.ANSWER]))
            for rel in (8, 9):
                forbidden.add(A.visible_signature(
                    full, [A.QUESTION, row[1], A.LINK, rel, A.ANSWER]))
    S.configure_variant(VARIANT, seed=100, **params)
    kept = False
    try:
        A.training_batch(REL.data_stream(100), 16, forbidden)
    except RuntimeError as exc:
        kept = 'semantic overlap' in str(exc)
    check('the semantic-overlap check is still armed on the per-seed stream', kept,
          f'{len(forbidden)} signatures enumerated for visit 0')

    S.configure_variant('hintwarm', seed=100, **params)
    check('hintwarm reuses the startup module batch builder too',
          A.training_batch is S.training_batch_hintwarm)


# ---------------------------------------------------------------------------- manifest

def test_manifest():
    repo = source_repo()
    recipe()
    manifest = REL.build_manifest(repo, VARIANT, list(range(100, 148)), 6000, 1500)
    text = json.dumps(manifest)
    check('manifest holds no absolute path from the build host',
          str(REL.FROZEN_BASE) not in text and '/Users/' not in text)
    check('manifest addresses ten panels relative to the repository root',
          sorted(manifest['panels']) == sorted(REL.CELLS)
          and all(not Path(r['path']).is_absolute() for r in manifest['panels'].values()))
    source = json.loads((repo/REL.source_launch_rel(VARIANT)).read_text())
    same = all(manifest['panels'][k]['sha256'] == v['sha256']
               and manifest['panels'][k]['cutoff'] == v['cutoff']
               for k, v in source['panels'].items())
    check('panel hashes and cutoffs are copied from the registered launch manifest', same)
    check('panel bytes on disk match those hashes',
          all(REL.sha256_of(repo/r['path']) == r['sha256']
              for r in manifest['panels'].values()))
    check('the schedule is the registered schedule',
          manifest['schedule'] == source['schedule'], json.dumps(manifest['schedule']))
    check('runtime.local.json is deliberately not hashed',
          'runtime.local.json' not in manifest['files'])
    check('roster is exactly the 48 requested seeds and excludes registered seeds',
          manifest['seeds'] == list(range(100, 148))
          and not set(manifest['seeds']) & REL.REGISTERED_SEEDS)

    refused = False
    try:
        REL.build_manifest(repo, VARIANT, [0, 1], 6000, 1500)
        REL.guard_seeds([0, 1], False)
    except SystemExit as exc:
        refused = 'registered' in str(exc)
    check('registered seeds 0-5 are refused', refused)

    refused = False
    try:
        REL.build_manifest(repo, VARIANT, [100], 6000, 900)
    except SystemExit as exc:
        refused = 'schedule differs' in str(exc)
    check('a schedule that is not the registered one is refused', refused)

    # verify_files detects a corrupted file, by hash, with the file named.
    with tempfile.TemporaryDirectory(prefix='fable-rel-hash-') as tmp:
        tmp = Path(tmp)
        (tmp/'artifacts').mkdir()
        good = tmp/'artifacts/panel.pt'
        good.write_bytes(b'not really a panel, but hashed the same way')
        fake = dict(files={'artifacts/panel.pt': REL.sha256_of(good)})
        check('verify_files accepts an intact file', REL.verify_files(tmp, fake) == 1)
        good.write_bytes(b'not really a panel, but hashed the same wayX')
        caught = ''
        try:
            REL.verify_files(tmp, fake)
        except RuntimeError as exc:
            caught = str(exc)
        check('verify_files rejects a corrupted file and names it',
              'registered file changed' in caught and 'panel.pt' in caught, caught)
        good.unlink()
        caught = ''
        try:
            REL.verify_files(tmp, fake)
        except RuntimeError as exc:
            caught = str(exc)
        check('verify_files rejects a missing file', 'missing' in caught, caught)


# ----------------------------------------------------------------------------- summary

def test_summary():
    repo = source_repo()
    recipe()
    with tempfile.TemporaryDirectory(prefix='fable-rel-summary-') as tmp:
        tmp = Path(tmp)
        seeds = [100, 101, 102, 103]
        manifest = REL.build_manifest(repo, VARIANT, seeds, 6000, 1500)
        (tmp/REL.MANIFEST_NAME).write_text(json.dumps(manifest))
        cutoffs = {k: v['cutoff'] for k, v in manifest['panels'].items()}

        def results(bump=0, broken=None, links=512):
            out = {}
            for name in REL.CELLS:
                value = cutoffs[name] + bump
                if broken and name in broken:
                    value = cutoffs[name] - 1
                hops = {'c1': 0, 'p12-1': 0, 's3': 2}.get(name, 1)
                out[name] = dict(n=512, R=value, M=300, gain=0, loss=0,
                                 diagnostics={'a': dict(n=512,
                                                        native_links=[links]*hops,
                                                        oracle_links=[512]*hops,
                                                        terminal_oracle=512,
                                                        native_joint=512)})
            return out

        def write(seed, payload, failure=False):
            folder = tmp/f'seed-{seed}'
            folder.mkdir()
            name = 'failure.json' if failure else 'completion.json'
            (folder/name).write_text(json.dumps(payload))

        write(100, dict(seed=100, complete=True, updates=6000, training_seconds=640.5,
                        results=results(bump=5)))
        write(101, dict(seed=101, complete=True, updates=6000, training_seconds=655.1,
                        results=results(broken={'c3', 's3'})))
        write(102, dict(seed=102, complete=False, updates=1200,
                        error="TimeoutError('registered training time cap')"), failure=True)
        # seed 103 never started: no folder at all.

        _, cells, got_cutoffs, rows = REL.collect(repo, VARIANT, tmp, tmp/REL.MANIFEST_NAME)
        by = {r['seed']: r for r in rows}
        check('summary lists every roster seed, run or not', [r['seed'] for r in rows] == seeds)
        check('a seed over every cutoff passes', by[100]['passed'] and by[100]['gate'])
        check('a seed under two cutoffs fails and both cells are named',
              not by[101]['passed']
              and sorted(c for c in cells if not by[101]['cells'][c]) == ['c3', 's3'],
              str(sorted(c for c in cells if not by[101]['cells'][c])))
        check('the ten R and ten M counts are carried through',
              len(by[100]['R']) == 10 and len(by[100]['M']) == 10)
        check('a crashed seed is recorded as failed, with its error',
              by[102]['state'] == 'failed' and not by[102]['passed']
              and 'training time cap' in by[102]['error'])
        check('a seed that never ran counts as not-run and fails',
              by[103]['state'] == 'not-run' and not by[103]['passed'])
        check('training seconds are reported per seed, never averaged',
              by[100]['training_seconds'] == 640.5 and by[101]['training_seconds'] == 655.1)
        check('total = seeds passing all ten', sum(r['passed'] for r in rows) == 1)

        write(199, dict(seed=199, complete=True, updates=6000, training_seconds=1.,
                        results=results(bump=5, links=486)))
        # 199 is off-roster; re-collect with a roster that includes it.
        m2 = dict(manifest, seeds=seeds + [199])
        (tmp/'m2.json').write_text(json.dumps(m2))
        _, _, _, rows2 = REL.collect(repo, VARIANT, tmp, tmp/'m2.json')
        gated = {r['seed']: r for r in rows2}[199]
        check('the LINK/terminal R gate is reported separately from the cutoffs',
              gated['passed'] and not gated['gate'],
              f'min links {gated["diagnostics"]["c2"]["min_native_links"]}')

        REL.summary(repo, VARIANT, tmp, tmp/REL.MANIFEST_NAME)

    check('Clopper-Pearson 0/10 upper bound', abs(REL.clopper_pearson(0, 10)[1]
                                                  - (1-0.025**(1/10))) < 1e-3,
          str(REL.clopper_pearson(0, 10)))
    check('Clopper-Pearson 10/10 lower bound', abs(REL.clopper_pearson(10, 10)[0]
                                                   - 0.025**(1/10)) < 1e-3,
          str(REL.clopper_pearson(10, 10)))
    check('Clopper-Pearson 48/48 lower bound',
          abs(REL.clopper_pearson(48, 48)[0] - 0.025**(1/48)) < 1e-3,
          str(REL.clopper_pearson(48, 48)))
    check('Clopper-Pearson 24/48 brackets one half',
          REL.clopper_pearson(24, 48)[0] < .5 < REL.clopper_pearson(24, 48)[1],
          str(REL.clopper_pearson(24, 48)))


# ------------------------------------------------------------------------------- model

def test_model():
    r = recipe()
    model = r['A'].new_model(SMOKE_SEEDS[0])
    check('parameter count is 79,316', model.parameters_count() == REL.PARAMETERS_COUNT,
          str(model.parameters_count()))
    check('the wrapper asserts the same count',
          REL.PARAMETERS_COUNT == 79316)
    other = r['A'].new_model(SMOKE_SEEDS[1])
    check('the seed really changes the initialisation',
          r['C'].fingerprint(model) != r['C'].fingerprint(other))


# ---------------------------------------------------------------------------- portable

def test_portable(updates, panel_n, keep=False):
    """Build a bundle in a temp dir and run freeze + a two-seed smoke wave from there."""
    assert updates <= 20, 'the portable smoke must never train more than 20 updates'
    r = recipe()
    repo = source_repo()
    tmp = Path(tempfile.mkdtemp(prefix='fable-rel-bundle-'))
    try:
        started = time.monotonic()
        out, _ = BUN.build(repo, tmp/'bundle', with_tests=True, tarball=False)
        check('bundle builds into a directory that is not the checkout',
              out.is_dir() and out != repo and not str(out).startswith(str(repo)),
              f'{len(list(out.rglob("*")))} entries in {time.monotonic()-started:.1f}s')
        check('bundle carries the frozen snapshot the bootstrap verifies',
              (out/REL.FROZEN_SUMS).exists()
              and (out/'archive/opus-ovn-20260918-235851/frozen/premonition/toy_ladder.py').exists())
        check('bundle carries all ten panels and the exclusion file',
              len(list((out/'artifacts/astra-canonical-operator-screen-20260920/'
                            'astra_canonical_operator_panels').glob('*.pt'))) == 6
              and len(list((out/'artifacts/codex-token-memory-20260920/stress').glob('*.pt'))) == 4
              and (out/'artifacts/astra-canonical-operator-screen-20260920/'
                       'astra_canonical_operator_panels/forbidden-semantics.json').exists())
        check('bundle shell scripts are /bin/sh and thread-pinned',
              (out/'run_remote.sh').read_text().startswith('#!/bin/sh')
              and 'OMP_NUM_THREADS=1' in (out/'run_remote.sh').read_text()
              and (out/'collect.sh').read_text().startswith('#!/bin/sh')
              and (out/'setup_remote.sh').read_text().startswith('#!/bin/sh'))

        # A throwaway panel, generated here, scored instead of the registered ten.
        panel = r['P'].generate('c1_own_one_hop', n=panel_n,
                                namespace='fable-reliability-smoke')
        panel_path = tmp/'smoke-panel.pt'
        r['torch'].save(panel, panel_path)

        env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
                   PYTHONDONTWRITEBYTECODE='1')
        env.pop('FABLE_RELIABILITY_REPO', None)
        rel = str(out/'scripts/fable_operator_reliability.py')
        seeds = f'{SMOKE_SEEDS[0]}-{SMOKE_SEEDS[1]}'

        def run(*argv):
            return subprocess.run([sys.executable, '-B', rel, *argv], env=env,
                                  cwd=str(tmp), capture_output=True, text=True)

        # No --repo anywhere below: the script must find its own root from its location.
        done = run('freeze', '--variant', VARIANT, '--seeds', seeds)
        check('freeze runs from the copied bundle with no --repo and no absolute config',
              done.returncode == 0, (done.stdout + done.stderr).strip()[-400:])
        root = out/f'artifacts/fable-operator-reliability-{VARIANT}-20260920'
        manifest = json.loads((root/REL.MANIFEST_NAME).read_text())
        check('the manifest frozen in the bundle is relative and hash-verified',
              '/Users/' not in json.dumps(manifest)
              and manifest['files'][manifest['panels']['c1']['path']]
              == manifest['panels']['c1']['sha256'])

        done = run('verify', '--variant', VARIANT)
        check('verify passes in the copied bundle', done.returncode == 0,
              (done.stdout + done.stderr).strip()[-300:])

        panel_rel = manifest['panels']['c3']['path']
        original = (out/panel_rel).read_bytes()
        (out/panel_rel).write_bytes(original + b'\0')
        broken = run('verify', '--variant', VARIANT)
        check('verify FAILS on a corrupted panel copy',
              broken.returncode != 0 and 'registered file changed' in broken.stderr,
              broken.stderr.strip()[-200:])
        (out/panel_rel).write_bytes(original)
        check('verify passes again once the panel is restored',
              run('verify', '--variant', VARIANT).returncode == 0)

        started = time.monotonic()
        done = run('wave', '--variant', VARIANT, '--seeds', seeds, '--parallel', '2',
                   '--name', 'smoke-1', '--smoke-panel', str(panel_path),
                   '--updates', str(updates))
        elapsed = time.monotonic()-started
        check('two-seed smoke wave completes from the copied bundle',
              done.returncode == 0, (done.stdout + done.stderr).strip()[-600:])
        wave = json.loads((root/'smoke-1/completion.json').read_text())
        check('the wave records every job, none incomplete',
              wave['complete'] and len(wave['jobs']) == 2
              and all(j['complete'] for j in wave['jobs']),
              f'{elapsed:.1f}s wall for 2 x {updates} updates')
        for seed in SMOKE_SEEDS:
            completion = json.loads((root/f'seed-{seed}/completion.json').read_text())
            check(f'seed {seed} scored the throwaway panel only',
                  list(completion['results']) == ['smoke']
                  and completion['results']['smoke']['n'] == panel_n
                  and completion['stream'] == f'{REL.STREAM_TAG}:{seed}',
                  f'R={completion["results"]["smoke"]["R"]}/{panel_n}, '
                  f'{completion["training_seconds"]:.1f}s train')
            check(f'seed {seed} wrote a per-seed log that was never overwritten',
                  (root/f'smoke-1/seed-{seed}.log').exists())
        a, b = (json.loads((root/f'seed-{s}/training.json').read_text())
                for s in SMOKE_SEEDS)
        check('the two smoke seeds trained to different weights',
              a['final_fingerprint'] != b['final_fingerprint'])

        again = run('wave', '--variant', VARIANT, '--seeds', seeds, '--parallel', '2',
                    '--name', 'smoke-1', '--smoke-panel', str(panel_path),
                    '--updates', str(updates))
        check('a wave never overwrites an existing wave folder', again.returncode != 0,
              again.stderr.strip()[-160:])

        bad = run('wave', '--variant', VARIANT, '--seeds', '0-1', '--parallel', '1',
                  '--name', 'smoke-2')
        check('a wave refuses seeds that are not on the frozen roster',
              bad.returncode != 0 and 'roster' in bad.stderr, bad.stderr.strip()[-160:])

        done = run('summary', '--variant', VARIANT)
        check('summary runs stdlib-only in the bundle and reports both seeds',
              done.returncode == 0 and str(SMOKE_SEEDS[0]) in done.stdout
              and 'PASSED ALL TEN CUTOFFS' in done.stdout,
              done.stdout.strip().splitlines()[-1] if done.stdout else done.stderr[-200:])
        check('nothing was written into the source checkout',
              not (repo/f'artifacts/fable-operator-reliability-{VARIANT}-20260920').exists())
    finally:
        if keep:
            print(f'kept bundle at {tmp}', flush=True)
        else:
            shutil.rmtree(tmp, ignore_errors=True)


GROUPS = dict(stream=test_stream, recipe=test_recipe, manifest=test_manifest,
              summary=test_summary, model=test_model)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', default=None, choices=list(GROUPS) + ['portable'])
    ap.add_argument('--smoke-updates', type=int, default=20)
    ap.add_argument('--smoke-panel', type=int, default=32)
    ap.add_argument('--keep', action='store_true')
    args = ap.parse_args()
    recipe()
    if args.only == 'portable':
        test_portable(args.smoke_updates, args.smoke_panel, args.keep)
    elif args.only:
        GROUPS[args.only]()
    else:
        for fn in GROUPS.values():
            fn()
        test_portable(args.smoke_updates, args.smoke_panel, args.keep)
    print(f'ALL {CHECKS} CHECKS PASSED')
