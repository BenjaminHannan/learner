"""Many-seed reliability screen for the frozen lookup-operator recipe (2026-09-20 EDT).

The frozen ``grow-blind`` / ``hintwarm`` runs answer "does the recipe work?" on three
initialisation seeds that all shared ONE training-data stream, ``random.Random(1101)``.
This wrapper answers the harder question: **how often does the same recipe pass all ten
answer cutoffs when BOTH the initialisation and the training data are fresh?**

Per job ``--seed N`` now sets two independent things:

* the model initialisation, ``A.new_model(N)``, exactly as before; and
* the world/data stream, ``random.Random(f"{STREAM_TAG}:{N}")`` in place of the fixed
  ``random.Random(1101)``.  ``training_batch_*`` consume the stream identically
  (``toy_ladder.visit`` per visit plus one trailing ``randrange`` per batch), so a seed is
  a fresh draw of worlds, memories and generator questions, not a re-shuffle of one draw.

Every other knob is the frozen recipe, read out of the registered launch manifest rather
than re-typed: ``grow-blind`` g1 1500 / g2 3000 / blind-lines 16, ``hintwarm`` H = 1000,
6,000 updates, 16 visits, training cap 1,500 s, work/terminate 1,740/1,770 s, the same ten
panels at the same ten cutoffs, final-checkpoint-only scoring.  ``freeze`` refuses to
write a manifest whose hyperparameters or schedule differ from the registered ones.

The semantic-overlap ``forbidden`` check stays on for every record of every update.

PORTABILITY.  The registered manifests name the panels by ABSOLUTE macOS paths, which is
useless on a rented Linux box.  Here the repository root is derived from this file's
location (``Path(__file__).resolve().parents[1]``), every panel, the exclusion file and
the output tree are addressed RELATIVE to that root, and each panel's sha256 is checked
against the value in the registered ``grow-blind`` / ``hintwarm`` launch manifest, so the
panels are provably the same bytes wherever they are unpacked.  Workers are spawned with
``sys.executable``.  Nothing reads ``runtime.local.json`` unless torch is missing.

    PY -B scripts/fable_operator_reliability.py freeze  --variant grow-blind --seeds 100-147
    PY -B scripts/fable_operator_reliability.py wave    --variant grow-blind --seeds 100-147 --parallel 6
    PY -B scripts/fable_operator_reliability.py summary --variant grow-blind
    PY -B scripts/fable_operator_reliability.py verify  --variant grow-blind   # panels + sources only

``summary`` and ``verify-sources`` are stdlib-only and never import torch.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import traceback

# --------------------------------------------------------------------------- constants

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# The macOS checkout the registered manifests and the two frozen wrapper modules were
# written against.  Used for exactly two things: turning the manifests' absolute panel
# paths into repository-relative ones, and satisfying the hard-coded assertions inside
# the frozen wrappers during import (see ``_import_recipe``).  Never used as a real path.
FROZEN_BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')

STREAM_TAG = 'fable-reliability-stream-v1'
EXTRA_TAG = 'fable-reliability-extra-v1'
SCHEMA = 'fable-operator-reliability-v1'
MANIFEST_NAME = 'reliability_launch.json'
VARIANTS = ('grow-blind', 'hintwarm')
PARAMETERS_COUNT = 79316
# Seeds 0-5 were trained under the registered grow-blind / hintwarm manifests.  A
# reliability job must never re-train one of them, whatever a caller asks for.
REGISTERED_SEEDS = frozenset(range(6))
SMOKE_SEED_MIN = 993600
FROZEN_SUMS = 'archive/opus-ovn-20260918-235851/FROZEN.SHA256SUMS'
# The fifteen registered modules that the recipe actually imports, plus this wrapper.
CLOSURE = (
    'astra_canonical_operator.py',
    'astra_canonical_operator_panels.py',
    'astra_canonical_operator_run.py',
    'fable_operator_startup.py',
    'fable_operator_variants.py',
    'premonition_first_card_probe.py',
    'premonition_handoff_diag.py',
    'premonition_memnn.py',
    'premonition_memnn_compare.py',
    'premonition_ovn_ladder.py',
    'premonition_ovn_retrieval.py',
    'premonition_pair_suite.py',
    'premonition_token_evidence.py',
    'premonition_token_initialization_probe.py',
    'premonition_token_memory.py',
)
CELLS = ('c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'p12-1', 'p12-2', 'p12-3', 's3')
# Astra's R gate, reported beside the ten answer cutoffs but never folded into them.
LINK_GATE = 487
TERMINAL_ORACLE_GATE = 487
S3_NATIVE_JOINT_GATE = 461


def sha256_of(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def out_root(repo, variant):
    assert variant in VARIANTS, variant
    return Path(repo)/f'artifacts/fable-operator-reliability-{variant}-20260920'


def source_launch_rel(variant):
    return f'artifacts/fable-operator-{variant}-20260920/astra_canonical_operator_launch.json'


def parse_seeds(text):
    """``100-147`` (inclusive), ``100,101,102`` or a mix.  Order preserved, no duplicates."""
    seeds = []
    for piece in str(text).split(','):
        piece = piece.strip()
        if not piece:
            continue
        if '-' in piece.lstrip('-'):
            lo, hi = piece.split('-', 1)
            lo, hi = int(lo), int(hi)
            assert lo <= hi, piece
            seeds.extend(range(lo, hi+1))
        else:
            seeds.append(int(piece))
    assert seeds, f'no seeds parsed from {text!r}'
    assert len(set(seeds)) == len(seeds), 'duplicate seed in roster'
    return seeds


def guard_seeds(seeds, smoke):
    bad = sorted(set(seeds) & REGISTERED_SEEDS)
    if bad:
        raise SystemExit(f'refusing to train registered seeds {bad}')
    if smoke:
        low = sorted(s for s in seeds if s < SMOKE_SEED_MIN)
        if low:
            raise SystemExit(f'smoke seeds must be >= {SMOKE_SEED_MIN}; got {low}')
    return list(seeds)


def _is_repo(root):
    return (root/FROZEN_SUMS).exists() and (root/'scripts/premonition_memnn.py').exists()


def find_repo(explicit=None):
    """Repository root: --repo, then $FABLE_RELIABILITY_REPO, then this file's location.

    In a deploy bundle the script's own parent directory IS the root and the search stops
    there immediately, so nothing about the build host leaks in.  The walk up the
    ancestors only matters in the development worktree, whose ``scripts/`` holds the new
    wrapper but not the registered modules; there it lands on the main checkout.
    """
    for candidate in (explicit, os.environ.get('FABLE_RELIABILITY_REPO')):
        if candidate:
            root = Path(candidate).resolve()
            if _is_repo(root):
                return root
            raise SystemExit(f'not a repository root (no {FROZEN_SUMS}): {root}')
    for root in (REPO, *REPO.parents):
        if _is_repo(root):
            return root
    raise SystemExit(f'no repository root found (looked for {FROZEN_SUMS}); pass --repo')


# ------------------------------------------------------------------- the frozen recipe

_RECIPE = {}


def _import_recipe(repo):
    """Import the registered modules from ``repo`` without editing any of them.

    ``fable_operator_variants.py`` and ``fable_operator_startup.py`` are hashed by the
    registered manifests and may not be touched.  Both open with

        BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
        if Path(__file__).resolve().parent != (BASE/'scripts'): <prepend BASE to sys.path>
        ...
        assert ROOT == BASE

    which is exactly right on the macOS checkout and fatal anywhere else.  Rather than
    edit them or disable assertions (``-O`` would also disable the integrity checks the
    recipe depends on) this function:

      1. imports the whole closure from ``repo`` FIRST, so the ``sys.path`` entries those
         two modules prepend can never re-resolve an already-imported module;
      2. for the duration of their import only, sets the two attributes their assertions
         read -- ``astra_canonical_operator_run.ROOT`` (the single name both modules take
         ``ROOT`` from) and ``fable_operator_variants.__file__``;
      3. restores both, restores ``sys.path``, and repairs the copies the two modules
         captured, then re-checks that every module points back at ``repo``.

    No file is modified, no assertion is skipped, and the only values that were ever
    wrong are restored before any work happens.
    """
    if _RECIPE.get('repo') == repo:
        return _RECIPE
    assert not _RECIPE, 'the recipe is imported once per process'
    for entry in (str(repo/'scripts'), str(repo)):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)

    import premonition_memnn as mem
    assert mem.ROOT == repo, (mem.ROOT, repo)
    mem.bootstrap()                      # binds ``premonition`` to repo's frozen snapshot
    import premonition
    frozen = repo/'archive/opus-ovn-20260918-235851/frozen'
    assert Path(premonition.__file__).resolve().is_relative_to(frozen), premonition.__file__

    import astra_canonical_operator as A            # noqa: F841 - bound below
    import astra_canonical_operator_panels as P
    import astra_canonical_operator_run as R
    import premonition_memnn_compare as C
    import premonition_handoff_diag                 # noqa: F401 - needed by P.chunks

    saved_path = list(sys.path)
    R.ROOT = FROZEN_BASE                                  # temporary, for their assertions
    try:
        import fable_operator_variants as V
        # V's body has just prepended the macOS checkout to sys.path.  Undo that BEFORE
        # resolving the next module, or ``fable_operator_startup`` is imported from the
        # build host instead of from this repository (caught by the assertions below).
        sys.path[:] = saved_path
        real_v_file = V.__file__
        V.__file__ = str(FROZEN_BASE/'scripts'/'fable_operator_variants.py')
        try:
            import fable_operator_startup as S
        finally:
            V.__file__ = real_v_file
    finally:
        R.ROOT = repo
        sys.path[:] = saved_path
    V.ROOT = S.ROOT = repo
    S.BASE = repo
    assert Path(S.__file__).resolve().parent == repo/'scripts', S.__file__
    assert Path(V.__file__).resolve().parent == repo/'scripts', V.__file__
    for module in (mem, C, P, R, V, S):
        assert getattr(module, 'ROOT') == repo, (module.__name__, module.ROOT)
    assert P.OUT == repo/'artifacts/astra-canonical-operator-screen-20260920', P.OUT
    assert S.V1 == P.OUT, S.V1
    _RECIPE.update(repo=repo, A=R.A, P=P, R=R, C=C, V=V, S=S, torch=R.torch)
    return _RECIPE


def configure_torch(recipe):
    torch = recipe['torch']
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1


# -------------------------------------------------------------------------- freeze

def _relative_to_frozen_base(path):
    """``/Users/.../beautiful-model/artifacts/x`` -> ``artifacts/x``; else fail loudly."""
    p = Path(path)
    try:
        return str(p.relative_to(FROZEN_BASE))
    except ValueError:
        raise SystemExit(f'registered manifest path is outside the checkout: {path}')


def read_source_launch(repo, variant):
    rel = source_launch_rel(variant)
    path = repo/rel
    if not path.exists():
        raise SystemExit(f'registered launch manifest missing: {rel}')
    return rel, json.loads(path.read_text()), sha256_of(path)


def build_manifest(repo, variant, seeds, updates, training_seconds):
    rel, source, source_sha = read_source_launch(repo, variant)
    assert source['variant'] == variant, (source['variant'], variant)
    schedule = dict(updates=updates, training_seconds=training_seconds,
                    work_seconds=training_seconds+240,
                    terminate_seconds=training_seconds+270, visits_per_update=16)
    if schedule != source['schedule']:
        raise SystemExit(f'schedule differs from the registered run: {schedule} vs '
                         f'{source["schedule"]}; the recipe must be reused verbatim')
    panels = {}
    for name, row in source['panels'].items():
        relpath = _relative_to_frozen_base(row['path'])
        local = repo/relpath
        if not local.exists():
            raise SystemExit(f'panel missing from this checkout: {relpath}')
        got = sha256_of(local)
        if got != row['sha256']:
            raise SystemExit(f'panel {name} differs from the registered bytes: {relpath}')
        panels[name] = dict(path=relpath, sha256=row['sha256'], cutoff=row['cutoff'],
                            n=row['n'], fresh=row.get('fresh'))
    missing = sorted(set(CELLS) - set(panels))
    assert not missing, f'registered manifest is missing panels {missing}'
    exclusion_rel = _relative_to_frozen_base(source['exclusion_path'])
    if not (repo/exclusion_rel).exists():
        raise SystemExit(f'exclusion file missing: {exclusion_rel}')

    files = {FROZEN_SUMS: sha256_of(repo/FROZEN_SUMS), rel: source_sha,
             exclusion_rel: sha256_of(repo/exclusion_rel)}
    for name in CLOSURE:
        files[f'scripts/{name}'] = sha256_of(repo/'scripts'/name)
    files['scripts/fable_operator_reliability.py'] = sha256_of(Path(__file__).resolve())
    for row in panels.values():
        files[row['path']] = row['sha256']
    # runtime.local.json is deliberately NOT hashed: it names this host's interpreter and
    # wheel cache and is regenerated per machine.  It is only read when torch is missing.

    return dict(
        schema=SCHEMA,
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        variant=variant,
        paths='repository-relative',
        startup=dict(source['startup']),
        schedule=schedule,
        stream=dict(tag=STREAM_TAG, extra_tag=EXTRA_TAG,
                    formula=f'random.Random(f"{STREAM_TAG}:{{seed}}")',
                    replaces='random.Random(1101)'),
        seeds=list(seeds),
        exclusion_path=exclusion_rel,
        panels=panels,
        source_launch=dict(variant=variant, path=rel, sha256=source_sha),
        files=files,
        parameters_count=PARAMETERS_COUNT)


def freeze(repo, variant, seeds, updates, training_seconds):
    recipe = _import_recipe(repo)
    manifest = build_manifest(repo, variant, seeds, updates, training_seconds)
    # Prove the hyperparameters the workers will use are the registered ones.
    frozen_params = dict(recipe['S'].DEFAULTS, **manifest['startup'])
    assert frozen_params == manifest['startup'], 'startup params are not a full record'
    root = out_root(repo, variant)
    root.mkdir(parents=True, exist_ok=True)
    # As in the registered runs: the preregistration is hashed here and re-verified
    # before every worker and every wave, so it cannot be edited after the roster is set.
    prereg = root/'PREREGISTRATION.md'
    if prereg.exists():
        manifest['files'][str(prereg.relative_to(repo))] = sha256_of(prereg)
    else:
        print('WARNING: no PREREGISTRATION.md beside the roster; it will not be hashed',
              file=sys.stderr)
    recipe['C'].write_new(root/MANIFEST_NAME, manifest)
    print(json.dumps(dict(variant=variant, manifest=str((root/MANIFEST_NAME).relative_to(repo)),
                          sha256=sha256_of(root/MANIFEST_NAME), files=len(manifest['files']),
                          seeds=len(manifest['seeds']),
                          panels=sorted(manifest['panels']))), flush=True)


# ------------------------------------------------------------------------- verification

def load_manifest(repo, variant, manifest_path=None):
    path = Path(manifest_path) if manifest_path else out_root(repo, variant)/MANIFEST_NAME
    if not path.exists():
        raise SystemExit(f'no frozen roster at {path}; run `freeze` first')
    manifest = json.loads(path.read_text())
    assert manifest['schema'] == SCHEMA, manifest['schema']
    assert manifest['variant'] == variant, (manifest['variant'], variant)
    return path, manifest


def verify_files(repo, manifest, skip=()):
    """Every registered file is byte-identical.  Returns the number checked."""
    checked = 0
    for name, expected in manifest['files'].items():
        if name in skip:
            continue
        path = repo/name
        if not path.exists():
            raise RuntimeError(f'registered file missing: {name}')
        if sha256_of(path) != expected:
            raise RuntimeError(f'registered file changed: {name}')
        checked += 1
    return checked


# ------------------------------------------------------------------------------ worker

def _rusage_bytes(raw):
    """``ru_maxrss`` is bytes on macOS and kibibytes on Linux.  Normalise, keep the raw."""
    return raw if platform.system() == 'Darwin' else raw*1024


def data_stream(seed):
    """The per-seed training-data stream that replaces the frozen ``random.Random(1101)``."""
    import random
    return random.Random(f'{STREAM_TAG}:{seed}')


def worker(repo, variant, seed, wave_start, manifest_path=None, smoke_panel=None,
           updates_override=None, out_dir=None):
    recipe = _import_recipe(repo)
    configure_torch(recipe)
    A, C, P, R, S = recipe['A'], recipe['C'], recipe['P'], recipe['R'], recipe['S']
    torch = recipe['torch']
    smoke = smoke_panel is not None
    guard_seeds([seed], smoke)
    path, manifest = load_manifest(repo, variant, manifest_path)
    root = Path(out_dir) if out_dir else out_root(repo, variant)
    folder = root/f'seed-{seed}'
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    wave_start = started if wave_start is None else wave_start
    count = 0
    try:
        verify_files(repo, manifest)
        params = dict(manifest['schedule'])
        if updates_override is not None:
            if not smoke:
                raise SystemExit('--updates only overrides the schedule in smoke mode')
            assert updates_override <= 30, 'a smoke must never train more than 30 updates'
            params['updates'] = updates_override
        forbidden = set(json.loads((repo/manifest['exclusion_path']).read_text()))
        S.configure_variant(variant, seed=seed, **manifest['startup'])
        # configure_variant points the runner's own OUT at the registered folder; the
        # reliability wave writes nowhere near it.
        R.OUT = folder

        model = A.new_model(seed)
        assert model.parameters_count() == PARAMETERS_COUNT, model.parameters_count()
        initial = C.fingerprint(model)
        optimizer = A.T.optimizer_for(model)
        rng = data_stream(seed)
        training_start = time.monotonic()
        flops = 0
        for step in range(params['updates']):
            R.deadline(wave_start, params['work_seconds'])
            if time.monotonic()-training_start >= params['training_seconds']:
                raise TimeoutError('registered training time cap')
            batch = A.training_batch(rng, 16, forbidden)
            flops += A.training_flops(batch, model)
            A.training_step(model, optimizer, batch, step)
            count += 1
            if count % 500 == 0:
                print(json.dumps(dict(seed=seed, updates=count,
                                      training_seconds=time.monotonic()-training_start)), flush=True)
        train_seconds = time.monotonic()-training_start
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=model.state_dict(), seed=seed, updates=count,
                        architecture=dict(vocab=68, width=48, heads=4, steps=3),
                        launch_sha256=sha256_of(path)), checkpoint)
        final = C.fingerprint(model)
        training = dict(seed=seed, variant=variant, updates=count, seconds=train_seconds,
                        flops=flops, stream=f'{STREAM_TAG}:{seed}',
                        initial_fingerprint=initial, final_fingerprint=final,
                        checkpoint_sha256=sha256_of(checkpoint),
                        canonical_records=count*16*6, monolithic_records=count*16*2,
                        overlap_checks=count*16*8)
        C.write_new(folder/'training.json', training)
        import gc
        del model, optimizer, batch
        gc.collect()

        saved = P.load(checkpoint)
        scorer = A.CanonicalOperator(**saved['architecture'])
        scorer.load_state_dict(saved['state_dict'], strict=True)
        scorer.eval()
        assert C.fingerprint(scorer) == final
        if smoke:
            cells = {'smoke': dict(path=str(smoke_panel), sha256=sha256_of(smoke_panel),
                                   cutoff=0, n=None)}
        else:
            cells = manifest['panels']
        results = {}
        for name, row in cells.items():
            R.deadline(wave_start, params['work_seconds'])
            panel_path = Path(row['path']) if smoke else repo/row['path']
            assert sha256_of(panel_path) == row['sha256'], f'panel changed: {name}'
            panel = P.load(panel_path)
            result = R.score_cell(scorer, panel, wave_start, params['work_seconds'])
            C.write_new(folder/f'{name}.json', result)
            results[name] = {k: v for k, v in result.items() if k != 'records'}
            print(json.dumps(dict(seed=seed, cell=name, n=result['n'],
                                  R=result['R'], M=result['M'])), flush=True)
        assert C.fingerprint(scorer) == final
        assert sha256_of(checkpoint) == training['checkpoint_sha256']
        verify_files(repo, manifest)
        R.deadline(wave_start, params['work_seconds'])
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        C.write_new(folder/'completion.json', dict(
            seed=seed, variant=variant, complete=True, smoke=smoke, updates=count,
            stream=f'{STREAM_TAG}:{seed}', training_seconds=train_seconds,
            seconds=time.monotonic()-started, wave_elapsed=time.monotonic()-wave_start,
            peak_rss_bytes=_rusage_bytes(raw), peak_rss_raw=raw,
            rss_units='bytes' if platform.system() == 'Darwin' else 'kibibytes',
            platform=platform.platform(), torch=torch.__version__,
            python=platform.python_version(), executable=sys.executable,
            final_checkpoint_only=True, weights_unchanged=True,
            registered_files_unchanged=True, results=results))
        return folder
    except BaseException as exc:
        C.write_new(folder/'failure.json', dict(
            seed=seed, variant=variant, complete=False, smoke=smoke, updates=count,
            seconds=time.monotonic()-started, error=repr(exc),
            traceback=traceback.format_exc()))
        raise


# -------------------------------------------------------------------------------- wave

def wave(repo, variant, seeds, parallel, name, manifest_path=None, smoke_panel=None,
         updates_override=None, out_dir=None):
    """Run the roster ``parallel`` at a time.  Never overwrites; incomplete = failed.

    Stdlib only: the supervisor never imports torch, so its memory stays out of the way
    of the workers.  Each worker gets its own ``--wave-start``, so the registered work
    and terminate caps are per-seed budgets measured from that seed's own launch.
    """
    path, manifest = load_manifest(repo, variant, manifest_path)
    roster = list(manifest['seeds'])
    seeds = list(seeds) if seeds else roster
    unknown = [s for s in seeds if s not in roster]
    if unknown:
        raise SystemExit(f'seeds {unknown} are not on the frozen roster; re-freeze to change it')
    guard_seeds(seeds, smoke_panel is not None)
    assert parallel >= 1
    verify_files(repo, manifest)
    root = Path(out_dir) if out_dir else out_root(repo, variant)
    folder = root/name
    folder.mkdir(parents=True, exist_ok=False)          # never overwrite a previous wave
    schedule = manifest['schedule']
    cap = schedule['terminate_seconds']
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    base = [sys.executable, '-B', str(Path(__file__).resolve()), 'worker',
            '--repo', str(repo), '--variant', variant, '--manifest', str(path)]
    if out_dir:
        base += ['--out-dir', str(root)]
    if smoke_panel is not None:
        base += ['--smoke-panel', str(smoke_panel)]
    if updates_override is not None:
        base += ['--updates', str(updates_override)]

    started = time.monotonic()
    pending, live, records = list(seeds), [], {}
    handles = []
    while pending or live:
        while pending and len(live) < parallel:
            seed = pending.pop(0)
            launched = time.monotonic()
            handle = (folder/f'seed-{seed}.log').open('x')
            handles.append(handle)
            proc = subprocess.Popen(
                base + ['--seed', str(seed), '--wave-start', str(launched)],
                stdout=handle, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            live.append(dict(seed=seed, proc=proc, launched=launched, killed=False))
        time.sleep(.25)
        for job in list(live):
            if job['proc'].poll() is None:
                if time.monotonic()-job['launched'] >= cap:
                    job['killed'] = True
                    job['proc'].terminate()
                    time.sleep(.5)
                    if job['proc'].poll() is None:
                        job['proc'].kill()
                else:
                    continue
            code = job['proc'].wait()
            seed = job['seed']
            done = (root/f'seed-{seed}'/'completion.json').exists()
            records[seed] = dict(seed=seed, exit_code=code, killed=job['killed'],
                                 seconds=round(time.monotonic()-job['launched'], 3),
                                 completion=done, complete=bool(code == 0 and done))
            print(json.dumps(records[seed]), flush=True)
            live.remove(job)
    for handle in handles:
        handle.close()
    ordered = [records[s] for s in seeds]
    failed = [r['seed'] for r in ordered if not r['complete']]
    summary = dict(variant=variant, name=name, seconds=time.monotonic()-started,
                   parallel=parallel, seeds=list(seeds), jobs=ordered,
                   complete=not failed, failed_seeds=failed,
                   smoke=smoke_panel is not None, manifest_sha256=sha256_of(path),
                   executable=sys.executable, platform=platform.platform())
    with (folder/'completion.json').open('x') as fh:
        json.dump(summary, fh, indent=2, allow_nan=False)
        fh.write('\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'jobs'}), flush=True)
    if failed:
        sys.exit(1)


# ----------------------------------------------------------------------------- summary

def clopper_pearson(k, n, alpha=.05):
    """Exact binomial interval by bisection on the binomial CDF.  Stdlib only."""
    if n == 0:
        return (0., 1.)

    def cdf(p, upto):
        return sum(math.comb(n, i)*p**i*(1-p)**(n-i) for i in range(upto+1))

    def solve(target, upto, lo, hi):
        for _ in range(200):
            mid = (lo+hi)/2
            if cdf(mid, upto) > target:
                lo = mid
            else:
                hi = mid
        return (lo+hi)/2

    low = 0. if k == 0 else solve(1-alpha/2, k-1, 0., 1.)
    high = 1. if k == n else solve(alpha/2, k, 0., 1.)
    return (round(low, 4), round(high, 4))


def _diagnostics(result):
    """(min native-link count over sides and hops, min terminal-oracle, min native-joint)."""
    links, terminals, joints = [], [], []
    for row in result['diagnostics'].values():
        links.extend(row['native_links'])
        terminals.append(row['terminal_oracle'])
        joints.append(row['native_joint'])
    return (min(links) if links else None, min(terminals), min(joints))


def collect(repo, variant, out_dir=None, manifest_path=None):
    root = Path(out_dir) if out_dir else out_root(repo, variant)
    path, manifest = load_manifest(repo, variant, manifest_path)
    cutoffs = {name: row['cutoff'] for name, row in manifest['panels'].items()}
    cells = [c for c in CELLS if c in cutoffs]
    rows = []
    for seed in manifest['seeds']:
        folder = root/f'seed-{seed}'
        done, fail = folder/'completion.json', folder/'failure.json'
        row = dict(seed=seed, state='not-run', R={}, M={}, cells={}, passed=False,
                   training_seconds=None, diagnostics={}, error=None, gate=None)
        if done.exists():
            data = json.loads(done.read_text())
            row['state'] = 'complete'
            row['training_seconds'] = data.get('training_seconds')
            row['updates'] = data.get('updates')
            gate_ok = True
            for name in cells:
                result = data['results'].get(name)
                if result is None:
                    row['cells'][name] = None
                    gate_ok = False
                    continue
                row['R'][name] = result['R']
                row['M'][name] = result['M']
                row['cells'][name] = bool(result['R'] >= cutoffs[name])
                link, terminal, joint = _diagnostics(result)
                row['diagnostics'][name] = dict(min_native_links=link,
                                                min_terminal_oracle=terminal,
                                                min_native_joint=joint)
                if link is not None and link < LINK_GATE:
                    gate_ok = False
                if terminal < TERMINAL_ORACLE_GATE:
                    gate_ok = False
                if name == 's3' and joint < S3_NATIVE_JOINT_GATE:
                    gate_ok = False
            row['passed'] = bool(row['cells']) and all(row['cells'].get(c) for c in cells)
            row['gate'] = gate_ok
        elif fail.exists():
            data = json.loads(fail.read_text())
            row['state'] = 'failed'
            row['updates'] = data.get('updates')
            row['error'] = data.get('error')
        rows.append(row)
    return manifest, cells, cutoffs, rows


def summary(repo, variant, out_dir=None, manifest_path=None, as_json=False):
    manifest, cells, cutoffs, rows = collect(repo, variant, out_dir, manifest_path)
    passed = [r for r in rows if r['passed']]
    k, n = len(passed), len(rows)
    lo, hi = clopper_pearson(k, n)
    if as_json:
        print(json.dumps(dict(variant=variant, seeds=n, passed=k,
                              clopper_pearson_95=[lo, hi], rows=rows), indent=2))
        return
    width = max(6, max((len(c) for c in cells), default=6))
    head = ' seed | st |' + '|'.join(f' {c:>{width}} ' for c in cells) + '| all | gate |  train s'
    print(f'reliability wave: variant={variant}  roster={n} seeds  '
          f'stream={STREAM_TAG}:<seed>')
    print('cutoffs: ' + '  '.join(f'{c}>={cutoffs[c]}' for c in cells))
    print()
    print(head)
    print('-'*len(head))
    for row in rows:
        state = {'complete': 'ok', 'failed': 'XX', 'not-run': '--'}[row['state']]
        cs = []
        for c in cells:
            if c in row['R']:
                mark = '+' if row['cells'][c] else '!'
                cs.append(f' {row["R"][c]:>{width-1}}{mark} ')
            else:
                cs.append(' '*width + '. ')
        allc = ' PASS' if row['passed'] else ' fail'
        gate = ' ok ' if row['gate'] else (' -- ' if row['gate'] is None else ' NO ')
        secs = f'{row["training_seconds"]:8.1f}' if row['training_seconds'] else '       .'
        print(f'{row["seed"]:>5} | {state} |' + '|'.join(cs) + f'|{allc}|{gate} |{secs}')
    print('-'*len(head))
    print('M (monolithic, descriptive only)')
    for row in rows:
        if row['M']:
            print(f'{row["seed"]:>5} | ' + '  '.join(f'{c}={row["M"][c]}' for c in cells))
    print()
    print(f'PASSED ALL TEN CUTOFFS: {k} / {n}   '
          f'Clopper-Pearson 95% [{lo:.4f}, {hi:.4f}]')
    print(f'also clearing Astra R gate (links>={LINK_GATE}, terminal-oracle>='
          f'{TERMINAL_ORACLE_GATE}, s3 joint>={S3_NATIVE_JOINT_GATE}): '
          f'{sum(1 for r in rows if r["passed"] and r["gate"])} / {n}')
    print()
    failing = [r for r in rows if not r['passed']]
    if not failing:
        print('no failing seed.')
    for row in failing:
        if row['state'] != 'complete':
            print(f'  seed {row["seed"]}: {row["state"]}'
                  + (f' after {row.get("updates")} updates: {row["error"]}'
                     if row['error'] else ''))
            continue
        bad = [f'{c} R={row["R"][c]}<{cutoffs[c]}' for c in cells
               if c in row['R'] and not row['cells'][c]]
        missing = [c for c in cells if c not in row['R']]
        detail = '; '.join(bad + ([f'missing {missing}'] if missing else []))
        gate = '' if row['gate'] else '  [R gate not cleared]'
        print(f'  seed {row["seed"]}: {detail}{gate}')
    print()
    print('Nothing above is averaged: every seed and every cell is printed.')


# -------------------------------------------------------------------------------- cli

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command',
                    choices=['freeze', 'wave', 'worker', 'summary', 'verify'])
    ap.add_argument('--repo', default=None,
                    help='repository root (default: this file\'s parent directory)')
    ap.add_argument('--variant', required=True, choices=list(VARIANTS))
    ap.add_argument('--seeds', default=None, help='e.g. 100-147 or 100,101,102')
    ap.add_argument('--seed', type=int)
    ap.add_argument('--parallel', type=int, default=1)
    ap.add_argument('--name', default='wave-1')
    ap.add_argument('--wave-start', type=float)
    ap.add_argument('--manifest', default=None)
    ap.add_argument('--out-dir', default=None,
                    help='override the output root (tests and smokes only)')
    ap.add_argument('--smoke-panel', default=None,
                    help='score this throwaway panel instead of the registered ten')
    ap.add_argument('--updates', type=int, default=None,
                    help='smoke-only override of the registered update count')
    ap.add_argument('--training-seconds', type=int, default=1500)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--panels', action='store_true',
                    help='verify: also unpickle every panel with this torch build')
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    repo = find_repo(args.repo)
    if args.command == 'summary':
        summary(repo, args.variant, args.out_dir, args.manifest, args.json)
        return
    if args.command == 'verify':
        path, manifest = load_manifest(repo, args.variant, args.manifest)
        checked = verify_files(repo, manifest)
        report = dict(variant=args.variant, manifest=str(path), files_verified=checked,
                      seeds=len(manifest['seeds']), panels=sorted(manifest['panels']))
        if args.panels:
            # Deep check: actually unpickle every panel with THIS torch.  Run it first on
            # a new host -- the panels were written by a newer torch than a rented box
            # usually carries, and this is the one step that can only fail there.
            recipe = _import_recipe(repo)
            configure_torch(recipe)
            loaded = {}
            for name, row in manifest['panels'].items():
                panel = recipe['P'].load(repo/row['path'])
                groups = list(recipe['P'].chunks(panel))
                sides = sorted({s for g in groups for s in g})
                units = sum(len(next(iter(g.values()))[1]) for g in groups)
                assert panel['n'] == row['n'] == units, (name, panel['n'], row['n'], units)
                loaded[name] = dict(n=panel['n'], chunks=len(groups), sides=sides)
            report['loaded'] = loaded
            report['torch'] = recipe['torch'].__version__
            report['parameters_count'] = recipe['A'].new_model(
                SMOKE_SEED_MIN).parameters_count()
        report['ok'] = True
        print(json.dumps(report), flush=True)
        return
    if args.command == 'freeze':
        seeds = guard_seeds(parse_seeds(args.seeds), args.smoke_panel is not None)
        freeze(repo, args.variant, seeds, 6000, args.training_seconds)
        return
    if args.command == 'wave':
        seeds = parse_seeds(args.seeds) if args.seeds else None
        wave(repo, args.variant, seeds, args.parallel, args.name, args.manifest,
             args.smoke_panel, args.updates, args.out_dir)
        return
    assert args.seed is not None, 'worker needs --seed'
    worker(repo, args.variant, args.seed, args.wave_start, args.manifest,
           args.smoke_panel, args.updates, args.out_dir)


if __name__ == '__main__':
    main()
