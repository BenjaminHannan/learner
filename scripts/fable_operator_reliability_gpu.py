"""Device-portable (CUDA/CPU) runner for the frozen lookup-operator reliability wave.

``scripts/fable_operator_reliability.py`` trains the 79,316-parameter ``grow-blind``
recipe on one CPU core per seed.  This wrapper answers a purely *operational* question:
**does the same recipe run faster on a CUDA GPU?**  It changes the arithmetic device and
nothing else.

WHAT IS AND IS NOT CHANGED
    * The training-data stream is untouched.  Every batch is still built by the
      registered ``fable_operator_startup.training_batch_blind`` from the *CPU* streams
      ``random.Random(f"{STREAM_TAG}:{seed}")`` (data) and ``random.Random(
      f"fable-startup-{variant}:{seed}")`` (curriculum), producing CPU tensors, and is
      only then moved to the device.  ``--device`` therefore cannot perturb the data:
      ``digest`` hashes the CPU batch before the move and can re-hash it after a
      round-trip through the device to prove the move is lossless.
    * Model initialisation still runs on the CPU (``A.new_model(seed)`` =
      ``torch.manual_seed(seed)`` + the registered rescale) and the initial fingerprint is
      taken *before* the move, so it is the same on every device.  The model is moved to
      the device only afterwards, and moved back to the CPU before the final fingerprint
      and ``torch.save``, so a checkpoint never carries a device tag.
    * Hyperparameters, schedule, panels, cutoffs, exclusion file, freeze/verify hash
      discipline: all inherited verbatim from ``fable_operator_reliability``.
    * Scoring runs on the device too.  Two registered functions build tensors inside the
      scoring loop and would otherwise pin it to the CPU; they are re-bound *at runtime*
      (never edited on disk) to byte-identical device-aware versions:
      ``astra_canonical_operator.canonical_input`` / ``.select`` (build the query tensor
      on the inputs' device) and ``astra_canonical_operator_panels.chunks`` (move each
      panel's ``Inputs`` to the device as it is yielded).  ``verify_files`` still hashes
      the on-disk sources before and after every seed.

    A GPU population is NOT the CPU population.  Floating-point reductions differ, so two
    devices give different weights from the same seed (see ``bench --loss-trace`` for the
    measured divergence).  Results are tagged with ``device``/``torch``/``gpu_name`` and
    land in their own output tree under their own manifest name, and ``summary`` refuses
    to mix devices.

WINDOWS
    Three things stop the registered runner dead on Windows.  All three are handled here,
    in this new file, without editing anything on disk:

    * ``astra_canonical_operator_run`` and the CPU wrapper both ``import resource`` at
      module scope.  A stdlib-only stub is installed into ``sys.modules`` *before* those
      imports; peak RSS comes from ``GetProcessMemoryInfo`` instead.
    * ``fable_operator_startup`` asserts ``Path(V.__file__).resolve().parent ==
      BASE/'scripts'`` with a drive-less macOS ``BASE``.  On Windows ``resolve()``
      attaches the current drive, so the assertion is unsatisfiable rather than false.
      ``posix_style_resolve`` makes an already-absolute drive-less path resolve to itself
      for the duration of the import only -- exactly the macOS behaviour the assertion
      was written against.
    * ``start_new_session`` is POSIX-only, so the wave supervisor omits it there.

    PY -B scripts/fable_operator_reliability_gpu.py bench   --variant grow-blind \\
        --device cuda --seed 998001 --updates 200 --phase full
    PY -B scripts/fable_operator_reliability_gpu.py bench   --variant grow-blind \\
        --device cuda --seeds 998001-998006 --parallel 6 --updates 200 --phase full
    PY -B scripts/fable_operator_reliability_gpu.py digest  --variant grow-blind \\
        --device cuda --seed 998001 --count 5 --roundtrip
    PY -B scripts/fable_operator_reliability_gpu.py freeze  --variant grow-blind --seeds 100-147
    PY -B scripts/fable_operator_reliability_gpu.py wave    --variant grow-blind \\
        --device cuda --seeds 100-147 --parallel 4
    PY -B scripts/fable_operator_reliability_gpu.py summary --variant grow-blind
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
import traceback
import types

HERE = Path(__file__).resolve().parent


# ------------------------------------------------------- Windows: stub ``resource`` first

def windows_peak_rss_bytes():
    """``PeakWorkingSetSize`` via psapi; stdlib ctypes only, no install."""
    import ctypes
    import ctypes.wintypes as wintypes

    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                    ('PeakWorkingSetSize', ctypes.c_size_t),
                    ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t),
                    ('PeakPagefileUsage', ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    # HANDLE is pointer-sized: without these the 64-bit pseudo-handle is truncated to
    # a 32-bit int and the call quietly fails.
    kernel32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters),
                                           wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(),
                                    ctypes.byref(counters), counters.cb)
    return int(counters.PeakWorkingSetSize) if ok else None


def install_resource_stub():
    """Give Windows a ``resource`` module so the registered imports succeed unedited.

    Returns (stubbed, real_module).  ``ru_maxrss`` is reported in kibibytes, the Linux
    convention the registered ``_rusage_bytes`` normalises, so a registered code path
    that reads it still gets a sane number.  Nothing on disk is touched.
    """
    try:
        import resource
        return False, resource
    except ImportError:
        pass
    module = types.ModuleType('resource')
    module.RUSAGE_SELF = 0
    module.RUSAGE_CHILDREN = -1

    class _Usage(tuple):
        @property
        def ru_maxrss(self):
            return self[2]

    def getrusage(who=0):
        peak = (windows_peak_rss_bytes() or 0) if os.name == 'nt' else 0
        return _Usage((0., 0., peak//1024) + (0,)*13)

    module.getrusage = getrusage
    module.__doc__ = 'stdlib-only Windows stand-in installed by ' + __file__
    sys.modules['resource'] = module
    return True, None


RESOURCE_STUBBED, REAL_RESOURCE = install_resource_stub()


def peak_rss_bytes():
    """Peak resident set of this process, in bytes, on macOS / Linux / Windows."""
    if os.name == 'nt':
        return windows_peak_rss_bytes()
    if REAL_RESOURCE is None:
        return None
    raw = REAL_RESOURCE.getrusage(REAL_RESOURCE.RUSAGE_SELF).ru_maxrss
    return raw if platform.system() == 'Darwin' else raw*1024


sys.path.insert(0, str(HERE))
import fable_operator_reliability as REL                                  # noqa: E402

# --------------------------------------------------------------------------- constants

GPU_SCHEMA = 'fable-operator-reliability-gpu-v1'
MANIFEST_NAME = 'reliability_gpu_launch.json'
DEVICES = ('cpu', 'cuda', 'meta')
COMPUTE_DEVICES = ('cpu', 'cuda')
# ``meta`` carries shapes but no data.  It exists so a machine with no GPU can still
# prove that the ``--device`` flag has no influence on batch construction.
DEV_SEED_MIN = 998000
BENCH_MAX_UPDATES = 300
PHASES = ('early', 'full')
STREAM_TAG = REL.STREAM_TAG


def out_root(repo, variant):
    assert variant in REL.VARIANTS, variant
    return Path(repo)/f'artifacts/fable-operator-reliability-gpu-{variant}-20260920'


def bench_root(repo, variant):
    return Path(repo)/f'artifacts/fable-operator-gpu-bench-{variant}-20260920'


def guard_dev_seeds(seeds):
    """Benchmarks and digests may only ever touch development seeds."""
    bad = sorted(s for s in seeds if s < DEV_SEED_MIN)
    if bad:
        raise SystemExit(f'benchmark seeds must be >= {DEV_SEED_MIN}; got {bad}')
    REL.guard_seeds(seeds, False)
    return list(seeds)


# ------------------------------------------------------------------------------ device

@contextlib.contextmanager
def posix_style_resolve():
    """Windows only, import-time only: keep a drive-less absolute path drive-less.

    ``fable_operator_startup`` asserts, at module scope,

        assert Path(V.__file__).resolve().parent == BASE/'scripts'

    with ``BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')``, and
    ``fable_operator_reliability._import_recipe`` satisfies it by pointing
    ``V.__file__`` at exactly that path for the duration of the import.  On POSIX
    ``resolve()`` is then the identity and the assertion holds.  On Windows
    ``resolve()`` attaches the current drive (``C:\\Users\\...``) while ``BASE`` has no
    drive, so the two can never compare equal and the import dies -- the assertion is
    unsatisfiable on Windows rather than false.

    Inside this context an already-absolute path that carries no drive resolves to
    itself (normalised), exactly as it would on macOS; every other path, including every
    real file the recipe touches, resolves normally.  Nothing on disk is modified, no
    assertion is skipped, and the comparison made is the one made on the Mac.
    """
    if os.name != 'nt':
        yield
        return
    import pathlib
    original = pathlib.Path.resolve

    def resolve(self, *args, **kwargs):
        if self.root and not self.drive:
            return type(self)(os.path.normpath(str(self)))
        return original(self, *args, **kwargs)

    pathlib.Path.resolve = resolve
    try:
        yield
    finally:
        pathlib.Path.resolve = original


def import_recipe(repo):
    """The registered import closure, with the Windows ``resolve()`` shim around it."""
    with posix_style_resolve():
        return REL._import_recipe(repo)


_CONFIGURED = []


def configure_torch_once(recipe):
    """``torch.set_num_interop_threads`` may only be called once per process.

    The registered ``configure_torch`` asserts the result, so calling it twice in one
    process (a test that exercises several commands) raises.  This calls it exactly once
    and then only re-asserts the thread counts.
    """
    torch = recipe['torch']
    if not _CONFIGURED:
        try:
            REL.configure_torch(recipe)
        except RuntimeError:
            # Already set by an earlier caller in this process (torch refuses a second
            # set_num_interop_threads).  The assertion below is the real requirement.
            torch.set_num_threads(1)
        _CONFIGURED.append(True)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1
    return torch


def resolve_device(recipe, name, compute=True):
    torch = recipe['torch']
    if name not in DEVICES:
        raise SystemExit(f'--device must be one of {DEVICES}; got {name!r}')
    if compute and name == 'meta':
        raise SystemExit('--device meta only makes sense for `digest`')
    if name == 'cuda' and not torch.cuda.is_available():
        raise SystemExit('--device cuda asked for, but torch reports no CUDA device')
    return torch.device(name)


def device_report(recipe, device):
    torch = recipe['torch']
    row = dict(device=device.type, torch=torch.__version__,
               python=platform.python_version(), platform=platform.platform(),
               executable=sys.executable, resource_stubbed=RESOURCE_STUBBED)
    if device.type == 'cuda':
        index = device.index or 0
        free, total = torch.cuda.mem_get_info(index)
        row.update(gpu_name=torch.cuda.get_device_name(index),
                   gpu_capability=list(torch.cuda.get_device_capability(index)),
                   cuda=torch.version.cuda, cudnn=torch.backends.cudnn.version(),
                   vram_free_bytes=int(free), vram_total_bytes=int(total))
    return row


def to_device(obj, device, torch):
    """Move every tensor inside a batch/target/dataclass tree; leave scalars alone."""
    import dataclasses
    if isinstance(obj, torch.Tensor):
        return obj.to(device)
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        fields = {f.name: to_device(getattr(obj, f.name), device, torch)
                  for f in dataclasses.fields(obj)}
        return type(obj)(**fields)
    if isinstance(obj, dict):
        return {k: to_device(v, device, torch) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(to_device(v, device, torch) for v in obj)
    return obj


def walk_tensors(obj, torch, prefix=''):
    """(dotted name, tensor) in a deterministic order, for hashing."""
    import dataclasses
    if isinstance(obj, torch.Tensor):
        yield prefix, obj
        return
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        for field in dataclasses.fields(obj):
            yield from walk_tensors(getattr(obj, field.name), torch,
                                    f'{prefix}.{field.name}')
        return
    if isinstance(obj, dict):
        for key in sorted(obj, key=str):
            yield from walk_tensors(obj[key], torch, f'{prefix}[{key}]')
        return
    if isinstance(obj, (list, tuple)):
        for i, value in enumerate(obj):
            yield from walk_tensors(value, torch, f'{prefix}[{i}]')


def batch_digest(batch, torch):
    """sha256 over every tensor in a batch: name, dtype, shape and raw bytes.

    Deliberately takes NO device argument: this is the proof that batch construction is
    device-independent.  Tensors that are already on a device are pulled back to the CPU
    here, so the same digest is produced from a CPU batch and from its device copy.
    """
    h = hashlib.sha256()
    for name, tensor in walk_tensors(batch, torch):
        h.update(name.encode())
        h.update(str(tensor.dtype).encode())
        h.update(repr(tuple(tensor.shape)).encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


# ------------------------------------------------- runtime re-binding for device scoring

def patch_for_device(recipe, device):
    """Re-bind the two registered helpers that would otherwise pin scoring to the CPU.

    Both replacements are the registered bodies with ``device=`` added; nothing on disk
    is modified and the CPU behaviour is unchanged (``torch.tensor(..., device=cpu)`` is
    the default).  Returns a callable that restores the originals.
    """
    A, P, torch = recipe['A'], recipe['P'], recipe['torch']
    original_select, original_input, original_chunks = A.select, A.canonical_input, P.chunks

    def select(inputs, indices, questions=None):
        ix = torch.as_tensor(indices, dtype=torch.long, device=inputs.memory.device)
        return A.data.Inputs(inputs.memory,
                             inputs.questions[ix] if questions is None else questions,
                             inputs.owner[ix], inputs.eligible[ix])

    def canonical_input(inputs, entities, operations, indices=None):
        if indices is None:
            indices = list(range(len(entities)))
        q = torch.tensor([[A.QUESTION, int(e), int(op), A.ANSWER]
                          for e, op in zip(entities, operations)],
                         dtype=torch.long, device=inputs.questions.device)
        return select(inputs, indices, q)

    def chunks(panel):
        for sides in original_chunks(panel):
            yield {side: (x.to(device), targets) for side, (x, targets) in sides.items()}

    A.select, A.canonical_input, P.chunks = select, canonical_input, chunks

    def restore():
        A.select, A.canonical_input, P.chunks = (original_select, original_input,
                                                 original_chunks)
    return restore


def startup_params(repo, variant, phase='early'):
    """The registered startup hyperparameters, optionally with the curriculum fast-forwarded.

    ``phase='full'`` sets ``grow_g1 = grow_g2 = 0`` so a short benchmark sees the
    expensive full-story batches from update 0.  It is a TIMING-ONLY setting: every
    command that can write a scored result refuses it.
    """
    _, source, _ = REL.read_source_launch(repo, variant)
    params = dict(source['startup'])
    if phase == 'full':
        params['grow_g1'] = params['grow_g2'] = 0
    elif phase != 'early':
        raise SystemExit(f'--phase must be one of {PHASES}')
    return params


def exclusion_set(repo, variant):
    _, source, _ = REL.read_source_launch(repo, variant)
    rel = REL._relative_to_frozen_base(source['exclusion_path'])
    return set(json.loads((repo/rel).read_text()))


# ------------------------------------------------------------------------ training core

def prepare(recipe, repo, variant, seed, device, params):
    """Configure the variant and build the model/optimizer, model on ``device``."""
    A, C, S = recipe['A'], recipe['C'], recipe['S']
    S.configure_variant(variant, seed=seed, **params)
    model = A.new_model(seed)                       # CPU: identical on every host/device
    assert model.parameters_count() == REL.PARAMETERS_COUNT, model.parameters_count()
    initial = C.fingerprint(model)                  # taken before the move
    model = model.to(device)
    optimizer = A.T.optimizer_for(model)
    return model, optimizer, initial


def sync(recipe, device):
    if device.type == 'cuda':
        recipe['torch'].cuda.synchronize()


# ------------------------------------------------------------------------------ freeze

def build_gpu_manifest(repo, variant, seeds, updates, training_seconds, device_name):
    manifest = REL.build_manifest(repo, variant, seeds, updates, training_seconds)
    manifest['gpu_schema'] = GPU_SCHEMA
    manifest['device_policy'] = dict(
        allowed=list(COMPUTE_DEVICES), intended=device_name,
        note=('batches and initialisation are built on the CPU and only then moved; a '
              'population trained on one device is never merged with another device'))
    manifest['files']['scripts/fable_operator_reliability_gpu.py'] = REL.sha256_of(
        Path(__file__).resolve())
    return manifest


def freeze(repo, variant, seeds, updates, training_seconds, device_name):
    recipe = import_recipe(repo)
    manifest = build_gpu_manifest(repo, variant, seeds, updates, training_seconds,
                                  device_name)
    frozen = dict(recipe['S'].DEFAULTS, **manifest['startup'])
    assert frozen == manifest['startup'], 'startup params are not a full record'
    root = out_root(repo, variant)
    root.mkdir(parents=True, exist_ok=True)
    prereg = root/'PREREGISTRATION.md'
    if prereg.exists():
        manifest['files'][str(prereg.relative_to(repo))] = REL.sha256_of(prereg)
    recipe['C'].write_new(root/MANIFEST_NAME, manifest)
    print(json.dumps(dict(variant=variant, gpu_schema=GPU_SCHEMA,
                          manifest=str((root/MANIFEST_NAME).relative_to(repo)),
                          sha256=REL.sha256_of(root/MANIFEST_NAME),
                          files=len(manifest['files']), seeds=len(manifest['seeds']))),
          flush=True)


def load_manifest(repo, variant, manifest_path=None):
    path = Path(manifest_path) if manifest_path else out_root(repo, variant)/MANIFEST_NAME
    if not path.exists():
        raise SystemExit(f'no frozen roster at {path}; run `freeze` first')
    manifest = json.loads(path.read_text())
    assert manifest['schema'] == REL.SCHEMA, manifest['schema']
    assert manifest.get('gpu_schema') == GPU_SCHEMA, manifest.get('gpu_schema')
    assert manifest['variant'] == variant, (manifest['variant'], variant)
    return path, manifest


# ------------------------------------------------------------------------------ worker

def worker(repo, variant, seed, device_name, wave_start, manifest_path=None,
           smoke_panel=None, updates_override=None, out_dir=None):
    recipe = import_recipe(repo)
    configure_torch_once(recipe)
    A, C, P, R, S = recipe['A'], recipe['C'], recipe['P'], recipe['R'], recipe['S']
    torch = recipe['torch']
    device = resolve_device(recipe, device_name)
    smoke = smoke_panel is not None
    REL.guard_seeds([seed], smoke)
    path, manifest = load_manifest(repo, variant, manifest_path)
    root = Path(out_dir) if out_dir else out_root(repo, variant)
    folder = root/f'seed-{seed}'
    folder.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    wave_start = started if wave_start is None else wave_start
    count = 0
    restore = patch_for_device(recipe, device)
    try:
        REL.verify_files(repo, manifest)
        params = dict(manifest['schedule'])
        if updates_override is not None:
            if not smoke:
                raise SystemExit('--updates only overrides the schedule in smoke mode')
            assert updates_override <= 30, 'a smoke must never train more than 30 updates'
            params['updates'] = updates_override
        forbidden = set(json.loads((repo/manifest['exclusion_path']).read_text()))
        model, optimizer, initial = prepare(recipe, repo, variant, seed, device,
                                            manifest['startup'])
        R.OUT = folder

        rng = REL.data_stream(seed)
        training_start = time.monotonic()
        flops = 0
        for step in range(params['updates']):
            R.deadline(wave_start, params['work_seconds'])
            if time.monotonic()-training_start >= params['training_seconds']:
                raise TimeoutError('registered training time cap')
            batch = A.training_batch(rng, 16, forbidden)     # CPU stream, CPU tensors
            flops += A.training_flops(batch, model)
            A.training_step(model, optimizer, to_device(batch, device, torch), step)
            count += 1
            if count % 500 == 0:
                sync(recipe, device)
                print(json.dumps(dict(seed=seed, updates=count, device=device.type,
                                      training_seconds=time.monotonic()-training_start)),
                      flush=True)
        sync(recipe, device)
        train_seconds = time.monotonic()-training_start

        model = model.to('cpu')                      # checkpoints never carry a device tag
        checkpoint = folder/'final.pt'
        torch.save(dict(state_dict=model.state_dict(), seed=seed, updates=count,
                        architecture=dict(vocab=68, width=48, heads=4, steps=3),
                        launch_sha256=REL.sha256_of(path)), checkpoint)
        final = C.fingerprint(model)
        checkpoint_sha256 = REL.sha256_of(checkpoint)
        C.write_new(folder/'training.json', dict(
            seed=seed, variant=variant, device=device.type, torch=torch.__version__,
            updates=count, seconds=train_seconds, flops=flops,
            stream=f'{STREAM_TAG}:{seed}', initial_fingerprint=initial,
            final_fingerprint=final, checkpoint_sha256=checkpoint_sha256,
            canonical_records=count*16*6, monolithic_records=count*16*2,
            overlap_checks=count*16*8))
        import gc
        del optimizer, batch
        gc.collect()

        saved = P.load(checkpoint)
        scorer = A.CanonicalOperator(**saved['architecture'])
        scorer.load_state_dict(saved['state_dict'], strict=True)
        scorer.eval()
        assert C.fingerprint(scorer) == final
        scorer = scorer.to(device)
        if smoke:
            cells = {'smoke': dict(path=str(smoke_panel),
                                   sha256=REL.sha256_of(smoke_panel), cutoff=0, n=None)}
        else:
            cells = manifest['panels']
        results, scoring_seconds = {}, {}
        for name, row in cells.items():
            R.deadline(wave_start, params['work_seconds'])
            panel_path = Path(row['path']) if smoke else repo/row['path']
            assert REL.sha256_of(panel_path) == row['sha256'], f'panel changed: {name}'
            panel = P.load(panel_path)
            cell_start = time.monotonic()
            result = R.score_cell(scorer, panel, wave_start, params['work_seconds'])
            sync(recipe, device)
            scoring_seconds[name] = time.monotonic()-cell_start
            C.write_new(folder/f'{name}.json', result)
            results[name] = {k: v for k, v in result.items() if k != 'records'}
            print(json.dumps(dict(seed=seed, cell=name, n=result['n'],
                                  R=result['R'], M=result['M'])), flush=True)
        assert C.fingerprint(scorer) == final
        assert REL.sha256_of(checkpoint) == checkpoint_sha256
        REL.verify_files(repo, manifest)
        R.deadline(wave_start, params['work_seconds'])
        completion = dict(
            seed=seed, variant=variant, complete=True, smoke=smoke, updates=count,
            stream=f'{STREAM_TAG}:{seed}', training_seconds=train_seconds,
            scoring_seconds=scoring_seconds, seconds=time.monotonic()-started,
            wave_elapsed=time.monotonic()-wave_start, peak_rss_bytes=peak_rss_bytes(),
            rss_units='bytes', final_checkpoint_only=True, weights_unchanged=True,
            registered_files_unchanged=True, results=results,
            **device_report(recipe, device))
        if device.type == 'cuda':
            completion['peak_vram_allocated_bytes'] = int(torch.cuda.max_memory_allocated())
            completion['peak_vram_reserved_bytes'] = int(torch.cuda.max_memory_reserved())
        C.write_new(folder/'completion.json', completion)
        return folder
    except BaseException as exc:
        C.write_new(folder/'failure.json', dict(
            seed=seed, variant=variant, device=device_name, complete=False, smoke=smoke,
            updates=count, seconds=time.monotonic()-started, error=repr(exc),
            traceback=traceback.format_exc()))
        raise
    finally:
        restore()


# -------------------------------------------------------------------------------- wave

def popen(args, **kwargs):
    """``start_new_session`` is POSIX-only; on Windows it is simply not passed."""
    if os.name == 'posix':
        kwargs['start_new_session'] = True
    return subprocess.Popen(args, **kwargs)


def worker_env():
    return dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
                NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')


def wave(repo, variant, seeds, device_name, parallel, name, manifest_path=None,
         smoke_panel=None, updates_override=None, out_dir=None):
    path, manifest = load_manifest(repo, variant, manifest_path)
    roster = list(manifest['seeds'])
    seeds = list(seeds) if seeds else roster
    unknown = [s for s in seeds if s not in roster]
    if unknown:
        raise SystemExit(f'seeds {unknown} are not on the frozen roster; re-freeze first')
    REL.guard_seeds(seeds, smoke_panel is not None)
    assert parallel >= 1
    REL.verify_files(repo, manifest)
    root = Path(out_dir) if out_dir else out_root(repo, variant)
    folder = root/name
    folder.mkdir(parents=True, exist_ok=False)
    cap = manifest['schedule']['terminate_seconds']
    env = worker_env()
    base = [sys.executable, '-B', str(Path(__file__).resolve()), 'worker',
            '--repo', str(repo), '--variant', variant, '--device', device_name,
            '--manifest', str(path)]
    if out_dir:
        base += ['--out-dir', str(root)]
    if smoke_panel is not None:
        base += ['--smoke-panel', str(smoke_panel)]
    if updates_override is not None:
        base += ['--updates', str(updates_override)]

    started = time.monotonic()
    pending, live, records, handles = list(seeds), [], {}, []
    while pending or live:
        while pending and len(live) < parallel:
            seed = pending.pop(0)
            launched = time.monotonic()
            handle = (folder/f'seed-{seed}.log').open('x')
            handles.append(handle)
            proc = popen(base + ['--seed', str(seed), '--wave-start', str(launched)],
                         stdout=handle, stderr=subprocess.STDOUT, env=env)
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
    summary_row = dict(variant=variant, name=name, device=device_name,
                       seconds=time.monotonic()-started, parallel=parallel,
                       seeds=list(seeds), jobs=ordered, complete=not failed,
                       failed_seeds=failed, smoke=smoke_panel is not None,
                       manifest_sha256=REL.sha256_of(path), executable=sys.executable,
                       platform=platform.platform())
    with (folder/'completion.json').open('x') as fh:
        json.dump(summary_row, fh, indent=2, allow_nan=False)
        fh.write('\n')
    print(json.dumps({k: v for k, v in summary_row.items() if k != 'jobs'}), flush=True)
    if failed:
        sys.exit(1)


# ------------------------------------------------------------------------------ digest

def digests(repo, variant, seed, device_name, count, phase='early', roundtrip=False,
            armed=True):
    """Hash the first ``count`` batches of a seed, built exactly as the worker builds them.

    The digest is taken from the CPU batch *before* any move.  With ``--roundtrip`` the
    batch is also moved to the device and pulled straight back, and the digest of the
    round-tripped copy is reported: equal digests prove the move is lossless.
    """
    recipe = import_recipe(repo)
    configure_torch_once(recipe)
    A, S, torch = recipe['A'], recipe['S'], recipe['torch']
    device = resolve_device(recipe, device_name, compute=False)
    guard_dev_seeds([seed])
    params = startup_params(repo, variant, phase)
    S.configure_variant(variant, seed=seed, **params)
    forbidden = exclusion_set(repo, variant) if armed else frozenset()
    rng = REL.data_stream(seed)
    rows = []
    for step in range(count):
        batch = A.training_batch(rng, 16, forbidden)
        row = dict(step=step, digest=batch_digest(batch, torch),
                   canonical=list(batch.canonical.questions.shape),
                   monolithic=list(batch.monolithic.questions.shape),
                   memory=list(batch.canonical.memory.shape))
        if roundtrip:
            moved = to_device(batch, device, torch)
            row['device_roundtrip_digest'] = (batch_digest(moved, torch)
                                              if device.type != 'meta' else None)
            row['moved_to'] = device.type
        rows.append(row)
    return dict(variant=variant, seed=seed, phase=phase,
                count=count, armed=armed, rows=rows,
                chain=hashlib.sha256(''.join(r['digest'] for r in rows).encode()).hexdigest(),
                **device_report(recipe, device))


# ------------------------------------------------------------------------------- bench

def nvidia_sampler(stop, samples, interval=.5):
    query = ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,power.draw',
             '--format=csv,noheader,nounits']
    while not stop.is_set():
        try:
            out = subprocess.run(query, capture_output=True, text=True, timeout=5)
            if out.returncode == 0:
                parts = out.stdout.strip().splitlines()[0].split(',')
                samples.append([float(p) for p in parts])
        except Exception:                                              # noqa: BLE001
            pass
        stop.wait(interval)


def bench_one(repo, variant, seed, device_name, updates, phase, warmup, loss_trace):
    """Time ``updates`` training updates.  No panel is scored and nothing is checkpointed."""
    recipe = import_recipe(repo)
    configure_torch_once(recipe)
    A, C, V, torch = recipe['A'], recipe['C'], recipe['V'], recipe['torch']
    device = resolve_device(recipe, device_name)
    guard_dev_seeds([seed])
    if updates > BENCH_MAX_UPDATES:
        raise SystemExit(f'bench is capped at {BENCH_MAX_UPDATES} updates; got {updates}')
    params = startup_params(repo, variant, phase)
    forbidden = exclusion_set(repo, variant)
    model, optimizer, initial = prepare(recipe, repo, variant, seed, device, params)

    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats()
    rng = REL.data_stream(seed)
    build, step_time, trace = [], [], []
    started = time.monotonic()
    for step in range(updates):
        t0 = time.monotonic()
        batch = A.training_batch(rng, 16, forbidden)
        moved = to_device(batch, device, torch)
        sync(recipe, device)
        t1 = time.monotonic()
        if loss_trace:
            with torch.no_grad():
                answer = float(V._answer_ce(model, moved.canonical,
                                            moved.canonical_targets))
                mono = float(V._answer_ce(model, moved.monolithic,
                                          moved.monolithic_targets))
            trace.append(dict(step=step, canonical_ce=answer, monolithic_ce=mono))
        A.training_step(model, optimizer, moved, step)
        sync(recipe, device)
        t2 = time.monotonic()
        build.append(t1-t0)
        step_time.append(t2-t1)
    elapsed = time.monotonic()-started

    timed = slice(min(warmup, max(0, updates-1)), None)
    hot_build, hot_step = build[timed], step_time[timed]
    hot = [b+s for b, s in zip(hot_build, hot_step)]
    row = dict(variant=variant, seed=seed, phase=phase, updates=updates, warmup=warmup,
               seconds=elapsed, updates_per_second=updates/elapsed,
               hot_updates=len(hot), hot_updates_per_second=len(hot)/sum(hot),
               mean_seconds_per_update=sum(hot)/len(hot),
               median_seconds_per_update=sorted(hot)[len(hot)//2],
               mean_batch_build_seconds=sum(hot_build)/len(hot_build),
               mean_step_seconds=sum(hot_step)/len(hot_step),
               initial_fingerprint=initial,
               final_fingerprint=C.fingerprint(model),
               mean_kept_lines=None, peak_rss_bytes=peak_rss_bytes(),
               **device_report(recipe, device))
    curriculum = batch.accounting.get('curriculum', {})
    kept = curriculum.get('kept_lines') or []
    if kept:
        row['mean_kept_lines'] = sum(kept)/len(kept)
        row['story_lines'] = curriculum.get('original_lines')
        row['kept_fraction'] = curriculum.get('fraction')
    row['tokens_per_batch'] = int(batch.canonical.memory.ne(0).sum())
    if device.type == 'cuda':
        row['peak_vram_allocated_bytes'] = int(torch.cuda.max_memory_allocated())
        row['peak_vram_reserved_bytes'] = int(torch.cuda.max_memory_reserved())
    if loss_trace:
        row['loss_trace'] = trace
    return row


def bench_wave(repo, variant, seeds, device_name, updates, phase, warmup, parallel,
               out_dir, loss_trace=False):
    """Run ``parallel`` bench processes at once and report aggregate throughput."""
    guard_dev_seeds(seeds)
    root = Path(out_dir) if out_dir else bench_root(repo, variant)
    stamp = datetime.datetime.now().strftime('%H%M%S')
    folder = root/f'{device_name}-{phase}-p{parallel}-{stamp}'
    folder.mkdir(parents=True, exist_ok=False)
    env = worker_env()
    base = [sys.executable, '-B', str(Path(__file__).resolve()), 'bench',
            '--repo', str(repo), '--variant', variant, '--device', device_name,
            '--updates', str(updates), '--phase', phase, '--warmup', str(warmup)]
    if loss_trace:
        base.append('--loss-trace')

    samples, stop = [], threading.Event()
    sampler = None
    if device_name == 'cuda':
        sampler = threading.Thread(target=nvidia_sampler, args=(stop, samples),
                                   daemon=True)
        sampler.start()

    started = time.monotonic()
    live, handles = [], []
    roster = list(seeds)[:parallel]
    if len(roster) < parallel:
        raise SystemExit(f'need {parallel} seeds for --parallel {parallel}; got {len(roster)}')
    for seed in roster:
        handle = (folder/f'seed-{seed}.json').open('x')
        handles.append(handle)
        live.append(dict(seed=seed, handle=handle, proc=popen(
            base + ['--seed', str(seed), '--out', str(folder/f'seed-{seed}.json')],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)))
    for handle in handles:
        handle.close()
    rows, errors = [], []
    for job in live:
        out, err = job['proc'].communicate()
        if job['proc'].returncode != 0:
            errors.append(dict(seed=job['seed'], returncode=job['proc'].returncode,
                               stderr=err[-1200:]))
            continue
        rows.append(json.loads((folder/f'seed-{job["seed"]}.json').read_text()))
    elapsed = time.monotonic()-started
    stop.set()
    if sampler is not None:
        sampler.join(timeout=3)

    per = [r['hot_updates_per_second'] for r in rows]
    report = dict(variant=variant, device=device_name, phase=phase, parallel=parallel,
                  seeds=roster, updates=updates, wall_seconds=elapsed,
                  processes_completed=len(rows), errors=errors,
                  per_process_updates_per_second=per,
                  aggregate_updates_per_second=sum(per) if per else 0.,
                  wall_aggregate_updates_per_second=len(rows)*updates/elapsed,
                  rows=[{k: v for k, v in r.items() if k != 'loss_trace'} for r in rows])
    if samples:
        report['gpu_samples'] = len(samples)
        report['gpu_utilisation_percent'] = dict(
            mean=sum(s[0] for s in samples)/len(samples), max=max(s[0] for s in samples))
        report['gpu_memory_used_mib'] = dict(
            mean=sum(s[1] for s in samples)/len(samples), max=max(s[1] for s in samples))
        if all(len(s) > 2 for s in samples):
            report['gpu_power_watts'] = dict(
                mean=sum(s[2] for s in samples)/len(samples), max=max(s[2] for s in samples))
    (folder/'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    if errors:
        sys.exit(1)
    return report


# ----------------------------------------------------------------------------- summary

def summary(repo, variant, out_dir=None, manifest_path=None, as_json=False):
    """Delegates to the CPU wrapper's summary, against the GPU tree and GPU manifest."""
    path = Path(manifest_path) if manifest_path else out_root(repo, variant)/MANIFEST_NAME
    root = Path(out_dir) if out_dir else out_root(repo, variant)
    devices = set()
    for folder in sorted(root.glob('seed-*')):
        done = folder/'completion.json'
        if done.exists():
            devices.add(json.loads(done.read_text()).get('device', 'unknown'))
    if len(devices) > 1:
        raise SystemExit(f'this tree mixes devices {sorted(devices)}; refusing to summarise')
    if devices and not as_json:
        print(f'device: {sorted(devices)[0]}   (never merge with another device)')
    REL.summary(repo, variant, root, path, as_json)


# --------------------------------------------------------------------------------- cli

def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['freeze', 'wave', 'worker', 'summary', 'verify',
                                        'digest', 'bench'])
    ap.add_argument('--repo', default=None)
    ap.add_argument('--variant', required=True, choices=list(REL.VARIANTS))
    ap.add_argument('--device', default='cpu', choices=list(DEVICES))
    ap.add_argument('--seeds', default=None)
    ap.add_argument('--seed', type=int)
    ap.add_argument('--parallel', type=int, default=1)
    ap.add_argument('--name', default='wave-1')
    ap.add_argument('--wave-start', type=float)
    ap.add_argument('--manifest', default=None)
    ap.add_argument('--out-dir', default=None)
    ap.add_argument('--out', default=None, help='bench/digest: write the JSON here too')
    ap.add_argument('--smoke-panel', default=None)
    ap.add_argument('--updates', type=int, default=None)
    ap.add_argument('--training-seconds', type=int, default=1500)
    ap.add_argument('--phase', default='early', choices=list(PHASES),
                    help='bench/digest only: `full` fast-forwards the grow curriculum')
    ap.add_argument('--warmup', type=int, default=20,
                    help='bench: updates excluded from the hot rate')
    ap.add_argument('--count', type=int, default=5, help='digest: how many batches')
    ap.add_argument('--roundtrip', action='store_true',
                    help='digest: also hash the batch after a device round-trip')
    ap.add_argument('--unarmed', action='store_true',
                    help='digest: skip the semantic-overlap check (timing comparisons)')
    ap.add_argument('--loss-trace', action='store_true',
                    help='bench: record per-update answer cross-entropy (numerics check)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--panels', action='store_true')
    return ap


def emit(payload, out):
    text = json.dumps(payload, indent=2)
    if out:
        Path(out).write_text(text + '\n')
    print(text, flush=True)


def main(argv=None):
    args = build_parser().parse_args(argv)
    repo = REL.find_repo(args.repo)
    if args.command == 'summary':
        summary(repo, args.variant, args.out_dir, args.manifest, args.json)
        return
    if args.command == 'verify':
        path, manifest = load_manifest(repo, args.variant, args.manifest)
        checked = REL.verify_files(repo, manifest)
        report = dict(variant=args.variant, manifest=str(path), files_verified=checked,
                      seeds=len(manifest['seeds']), gpu_schema=manifest['gpu_schema'])
        if args.panels:
            recipe = import_recipe(repo)
            configure_torch_once(recipe)
            device = resolve_device(recipe, args.device, compute=False)
            for name, row in manifest['panels'].items():
                panel = recipe['P'].load(repo/row['path'])
                assert panel['n'] == row['n'], (name, panel['n'], row['n'])
            report.update(device_report(recipe, device), panels_loaded=True)
        report['ok'] = True
        print(json.dumps(report), flush=True)
        return
    if args.command == 'freeze':
        seeds = REL.guard_seeds(REL.parse_seeds(args.seeds), args.smoke_panel is not None)
        freeze(repo, args.variant, seeds, 6000, args.training_seconds, args.device)
        return
    if args.command == 'wave':
        seeds = REL.parse_seeds(args.seeds) if args.seeds else None
        wave(repo, args.variant, seeds, args.device, args.parallel, args.name,
             args.manifest, args.smoke_panel, args.updates, args.out_dir)
        return
    if args.command == 'digest':
        assert args.seed is not None, 'digest needs --seed'
        emit(digests(repo, args.variant, args.seed, args.device, args.count, args.phase,
                     args.roundtrip, not args.unarmed), args.out)
        return
    if args.command == 'bench':
        updates = args.updates if args.updates is not None else 200
        if args.seeds:
            # --seeds (even one) goes through the supervisor, which also samples
            # nvidia-smi for GPU utilisation and VRAM while the children run.
            bench_wave(repo, args.variant, REL.parse_seeds(args.seeds), args.device,
                       updates, args.phase, args.warmup, args.parallel, args.out_dir,
                       args.loss_trace)
            return
        if args.parallel > 1:
            raise SystemExit('bench --parallel needs --seeds')
        assert args.seed is not None, 'bench needs --seed'
        emit(bench_one(repo, args.variant, args.seed, args.device, updates, args.phase,
                       args.warmup, args.loss_trace), args.out)
        return
    assert args.seed is not None, 'worker needs --seed'
    worker(repo, args.variant, args.seed, args.device, args.wave_start, args.manifest,
           args.smoke_panel, args.updates, args.out_dir)


if __name__ == '__main__':
    main()
