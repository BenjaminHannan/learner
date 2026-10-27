"""Checks for scripts/fable_operator_reliability_gpu.py.  Prints ALL N CHECKS PASSED.

Everything here runs on the CPU and finishes in seconds: the Mac is busy, and the GPU
claims are measured on the GPU box, not asserted here.

Run whole:   python3.12 -B tests/test_fable_operator_reliability_gpu.py
Run a group: python3.12 -B tests/test_fable_operator_reliability_gpu.py --only parity
Groups: windows, device, batches, manifest, parity.

``parity`` is the load-bearing one: it trains the SAME dev seed for five updates twice,
once through the registered CPU runner and once through the new runner with
``--device cpu``, and requires the two final weight fingerprints to be equal.
"""
from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'scripts'))

import fable_operator_reliability as REL                                  # noqa: E402
import fable_operator_reliability_gpu as GPU                              # noqa: E402
import fable_reliability_bundle as BUN                                    # noqa: E402

VARIANT = 'grow-blind'
DEV_SEED = 998101
CHECKS = 0


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


# ------------------------------------------------------------------ windows-safe imports

BLOCKER = '''
import sys
class Block:
    def find_module(self, name, path=None):
        return None
    def find_spec(self, name, path=None, target=None):
        if name == "resource":
            raise ImportError("no module named resource (simulated Windows)")
        return None
sys.meta_path.insert(0, Block())
try:
    import resource
    print("RESOURCE_STILL_IMPORTABLE")
except ImportError:
    pass
sys.path.insert(0, %r)
import fable_operator_reliability_gpu as GPU
import fable_operator_reliability as REL
usage = sys.modules["resource"].getrusage(sys.modules["resource"].RUSAGE_SELF)
print("STUBBED", GPU.RESOURCE_STUBBED, "RSS_TYPE", type(usage.ru_maxrss).__name__,
      "REL_OK", hasattr(REL, "worker"))
'''


def test_windows():
    source = Path(GPU.__file__).read_text()
    stub_at = source.index('RESOURCE_STUBBED, REAL_RESOURCE = install_resource_stub()')
    import_at = source.index('import fable_operator_reliability as REL')
    check('the resource stub is installed BEFORE the CPU wrapper is imported',
          stub_at < import_at, f'stub at {stub_at}, import at {import_at}')
    check('on a host that has resource, no stub is installed',
          GPU.RESOURCE_STUBBED is False and 'resource' in sys.modules)

    with tempfile.TemporaryDirectory(prefix='fable-gpu-win-') as tmp:
        script = Path(tmp)/'blocked.py'
        script.write_text(BLOCKER % str(HERE.parent/'scripts'))
        done = subprocess.run([sys.executable, '-B', str(script)], capture_output=True,
                              text=True, cwd=tmp)
        out = done.stdout.strip()
    check('the module imports with no `resource` module at all (Windows simulation)',
          done.returncode == 0 and 'STUBBED True' in out and 'REL_OK True' in out
          and 'RESOURCE_STILL_IMPORTABLE' not in out,
          (out + done.stderr).strip()[-400:])
    check('peak RSS is reported without the resource module on Windows',
          'if os.name == \'nt\':' in source and 'GetProcessMemoryInfo' in source)
    check('start_new_session is POSIX-only in the new wave supervisor',
          "if os.name == 'posix':" in inspect.getsource(GPU.popen)
          and 'start_new_session' in inspect.getsource(GPU.popen))
    check('workers are spawned with PYTHONUTF8=1',
          GPU.worker_env()['PYTHONUTF8'] == '1')


# ---------------------------------------------------------------------------- device flag

def test_device():
    r = recipe()
    torch = r['torch']
    refused = ''
    try:
        GPU.resolve_device(r, 'meta', compute=True)
    except SystemExit as exc:
        refused = str(exc)
    check('meta is refused for anything that computes', 'meta only makes sense' in refused,
          refused)
    check('cpu resolves', GPU.resolve_device(r, 'cpu').type == 'cpu')
    if not torch.cuda.is_available():
        refused = ''
        try:
            GPU.resolve_device(r, 'cuda')
        except SystemExit as exc:
            refused = str(exc)
        check('cuda is refused loudly on a host with no CUDA', 'no CUDA device' in refused,
              refused)
    check('an unknown device is refused',
          _raises(lambda: GPU.resolve_device(r, 'mps2'), SystemExit))

    report = GPU.device_report(r, GPU.resolve_device(r, 'cpu'))
    check('every result is tagged with device and torch version',
          report['device'] == 'cpu' and report['torch'] == torch.__version__,
          json.dumps({k: report[k] for k in ('device', 'torch')}))

    # The two runtime re-bindings must be exactly reversible.
    A, P = r['A'], r['P']
    before = (A.select, A.canonical_input, P.chunks)
    restore = GPU.patch_for_device(r, torch.device('cpu'))
    changed = (A.select, A.canonical_input, P.chunks) != before
    restore()
    check('scoring helpers are re-bound at runtime and restored exactly',
          changed and (A.select, A.canonical_input, P.chunks) == before)

    check('development seeds below the floor are refused',
          _raises(lambda: GPU.guard_dev_seeds([100]), SystemExit))
    check('registered seeds are refused even above the floor',
          _raises(lambda: GPU.guard_dev_seeds([0]), SystemExit))
    check('a development seed is accepted', GPU.guard_dev_seeds([DEV_SEED]) == [DEV_SEED])


def _raises(fn, kind):
    try:
        fn()
    except kind:
        return True
    return False


# --------------------------------------------------------------- batches ignore --device

def test_batches():
    repo = source_repo()
    recipe()
    check('batch_digest takes no device argument',
          list(inspect.signature(GPU.batch_digest).parameters) == ['batch', 'torch'])

    cpu = GPU.digests(repo, VARIANT, DEV_SEED, 'cpu', 3, roundtrip=True)
    meta = GPU.digests(repo, VARIANT, DEV_SEED, 'meta', 3, roundtrip=True)
    check('the batch stream is identical under --device cpu and --device meta',
          cpu['chain'] == meta['chain'],
          f'{cpu["chain"][:16]} == {meta["chain"][:16]}')
    check('every individual batch digest matches, not just the chain',
          [r['digest'] for r in cpu['rows']] == [r['digest'] for r in meta['rows']])
    check('a device round-trip is lossless (cpu)',
          all(r['digest'] == r['device_roundtrip_digest'] for r in cpu['rows']))
    check('the meta device really was used for the move',
          all(r['moved_to'] == 'meta' for r in meta['rows']))

    other = GPU.digests(repo, VARIANT, DEV_SEED+1, 'cpu', 3)
    check('a different seed is a different batch stream', other['chain'] != cpu['chain'])
    again = GPU.digests(repo, VARIANT, DEV_SEED, 'cpu', 3)
    check('the same seed reproduces the same batch stream', again['chain'] == cpu['chain'])

    full = GPU.digests(repo, VARIANT, DEV_SEED, 'cpu', 3, phase='full')
    check('--phase full really enlarges the batches (timing-only curriculum shortcut)',
          full['rows'][0]['memory'][1] >= cpu['rows'][0]['memory'][1]
          and full['chain'] != cpu['chain'],
          f'memory lines full={full["rows"][0]["memory"]} early={cpu["rows"][0]["memory"]}')

    # The batch must be the registered builder's output, not a copy living here.
    r = recipe()
    params = GPU.startup_params(repo, VARIANT)
    r['S'].configure_variant(VARIANT, seed=DEV_SEED, **params)
    check('the wrapper still routes through fable_operator_startup.training_batch_blind',
          r['A'].training_batch is r['S'].training_batch_blind)
    direct = r['A'].training_batch(REL.data_stream(DEV_SEED), 16, GPU.exclusion_set(repo, VARIANT))
    check('digest of a directly built batch equals the runner digest',
          GPU.batch_digest(direct, r['torch']) == cpu['rows'][0]['digest'])
    check('the semantic-overlap check is armed by default',
          cpu['armed'] is True and direct.accounting['overlap_checks'] > 0,
          str(direct.accounting['overlap_checks']))


# -------------------------------------------------------------------------- gpu manifest

def test_manifest():
    repo = source_repo()
    recipe()
    manifest = GPU.build_gpu_manifest(repo, VARIANT, list(range(100, 148)), 6000, 1500,
                                      'cuda')
    reference = REL.build_manifest(repo, VARIANT, list(range(100, 148)), 6000, 1500)
    check('the GPU manifest keeps the registered schedule and startup params byte-for-byte',
          manifest['schedule'] == reference['schedule']
          and manifest['startup'] == reference['startup'],
          json.dumps(manifest['schedule']))
    check('the GPU manifest keeps the same ten panels and cutoffs',
          manifest['panels'] == reference['panels'])
    check('the GPU manifest carries its own schema and hashes the new runner',
          manifest['gpu_schema'] == GPU.GPU_SCHEMA
          and manifest['files']['scripts/fable_operator_reliability_gpu.py']
          == REL.sha256_of(Path(GPU.__file__)))
    check('the GPU manifest records the device policy',
          manifest['device_policy']['intended'] == 'cuda'
          and manifest['device_policy']['allowed'] == ['cpu', 'cuda'])
    check('manifest name and output tree are separate from the CPU population',
          GPU.MANIFEST_NAME != REL.MANIFEST_NAME
          and GPU.out_root(repo, VARIANT) != REL.out_root(repo, VARIANT),
          f'{GPU.MANIFEST_NAME} in {GPU.out_root(repo, VARIANT).name}')
    check('no absolute build-host path leaks into the GPU manifest',
          '/Users/' not in json.dumps(manifest))

    with tempfile.TemporaryDirectory(prefix='fable-gpu-mix-') as tmp:
        tmp = Path(tmp)
        for seed, device in ((1, 'cuda'), (2, 'cpu')):
            (tmp/f'seed-{seed}').mkdir()
            (tmp/f'seed-{seed}/completion.json').write_text(
                json.dumps(dict(seed=seed, device=device, results={})))
        (tmp/GPU.MANIFEST_NAME).write_text(json.dumps(manifest))
        refused = ''
        try:
            GPU.summary(repo, VARIANT, tmp, tmp/GPU.MANIFEST_NAME)
        except SystemExit as exc:
            refused = str(exc)
        check('summary refuses to merge a CPU seed with a GPU seed',
              'mixes devices' in refused, refused)


# ------------------------------------------------------------- CPU parity with the runner

def test_parity(updates=5, panel_n=8):
    """Same seed, five updates, registered runner vs new runner --device cpu."""
    assert updates <= 20
    repo = source_repo()
    r = recipe()
    tmp = Path(tempfile.mkdtemp(prefix='fable-gpu-parity-'))
    try:
        # Both runners are exercised from a deploy bundle -- the same layout that is
        # shipped to the GPU box -- so the parity claim covers the deployed files.
        bundle, _ = BUN.build(repo, tmp/'bundle', with_tests=False, tarball=False)
        shutil.copy2(Path(GPU.__file__), bundle/'scripts'/Path(GPU.__file__).name)
        check('the new runner drops into an existing deploy bundle unchanged',
              REL.sha256_of(bundle/'scripts'/Path(GPU.__file__).name)
              == REL.sha256_of(Path(GPU.__file__)))

        panel = r['P'].generate('c1_own_one_hop', n=panel_n,
                                namespace='fable-reliability-gpu-smoke')
        panel_path = tmp/'smoke-panel.pt'
        r['torch'].save(panel, panel_path)

        cpu_manifest = tmp/REL.MANIFEST_NAME
        cpu_manifest.write_text(json.dumps(
            REL.build_manifest(bundle, VARIANT, [DEV_SEED], 6000, 1500)))
        gpu_manifest = tmp/GPU.MANIFEST_NAME
        gpu_manifest.write_text(json.dumps(
            GPU.build_gpu_manifest(bundle, VARIANT, [DEV_SEED], 6000, 1500, 'cpu')))

        # Separate processes, as a real wave runs them (and because torch refuses a
        # second set_num_interop_threads in one process).
        env = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
                   PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
        env.pop('FABLE_RELIABILITY_REPO', None)

        def run(script, extra):
            done = subprocess.run(
                [sys.executable, '-B', str(bundle/'scripts'/script), 'worker',
                 '--repo', str(bundle), '--variant', VARIANT, '--seed', str(DEV_SEED),
                 '--smoke-panel', str(panel_path), '--updates', str(updates)] + extra,
                capture_output=True, text=True, env=env, cwd=tmp)
            assert done.returncode == 0, (done.stdout + done.stderr)[-800:]
            return done

        run('fable_operator_reliability.py',
            ['--manifest', str(cpu_manifest), '--out-dir', str(tmp/'registered')])
        run('fable_operator_reliability_gpu.py',
            ['--device', 'cpu', '--manifest', str(gpu_manifest),
             '--out-dir', str(tmp/'new')])
        old = json.loads((tmp/'registered'/f'seed-{DEV_SEED}'/'training.json').read_text())
        new = json.loads((tmp/'new'/f'seed-{DEV_SEED}'/'training.json').read_text())
        check('initialisation is bit-identical (fingerprint before any device move)',
              old['initial_fingerprint'] == new['initial_fingerprint'],
              new['initial_fingerprint'][:16])
        check(f'after {updates} updates the trained weights are bit-identical on --device cpu',
              old['final_fingerprint'] == new['final_fingerprint'],
              f'{old["final_fingerprint"][:16]} == {new["final_fingerprint"][:16]}')
        check('training actually moved the weights',
              new['final_fingerprint'] != new['initial_fingerprint'])
        check('the counted FLOPs are identical too',
              old['flops'] == new['flops'], str(new['flops']))
        check('the new runner records the device it ran on',
              new['device'] == 'cpu' and 'device' not in old)

        old_done = json.loads(
            (tmp/'registered'/f'seed-{DEV_SEED}'/'completion.json').read_text())
        new_done = json.loads((tmp/'new'/f'seed-{DEV_SEED}'/'completion.json').read_text())
        check('scoring on the device gives the identical panel result on cpu',
              old_done['results']['smoke']['R'] == new_done['results']['smoke']['R']
              and old_done['results']['smoke']['M'] == new_done['results']['smoke']['M']
              and old_done['results']['smoke']['n'] == panel_n,
              f'R={new_done["results"]["smoke"]["R"]}/{panel_n}')
        check('the new completion carries device, torch and peak RSS',
              new_done['device'] == 'cpu' and new_done['torch'] == r['torch'].__version__
              and new_done['peak_rss_bytes'] > 0,
              f'{new_done["peak_rss_bytes"]/1e6:.0f} MB peak RSS')
        check('nothing was written into the source checkout',
              not GPU.out_root(repo, VARIANT).exists()
              and not REL.out_root(repo, VARIANT).exists())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


GROUPS = dict(windows=test_windows, device=test_device, batches=test_batches,
              manifest=test_manifest, parity=test_parity)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', default=None, choices=list(GROUPS))
    ap.add_argument('--updates', type=int, default=5)
    args = ap.parse_args()
    if args.only == 'parity':
        test_parity(args.updates)
    elif args.only:
        GROUPS[args.only]()
    else:
        for key, fn in GROUPS.items():
            fn(args.updates) if key == 'parity' else fn()
    print(f'ALL {CHECKS} CHECKS PASSED')
