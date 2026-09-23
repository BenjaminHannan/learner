"""Build a self-contained, host-portable deploy bundle for the reliability wave.

The bundle is a miniature repository: the same relative layout as the checkout, holding
EXACTLY the import closure plus the data the wave reads.  Unpacked anywhere -- a scratch
directory on the Mac, ``/workspace/bm`` on a rented Linux box -- ``scripts/
fable_operator_reliability.py`` derives its repository root from its own location, so no
absolute path from this machine survives into the run.

Contents
    scripts/                     the fifteen registered modules the recipe imports, plus
                                 fable_operator_reliability.py (and the check suite)
    archive/opus-ovn-.../        FROZEN.SHA256SUMS and the whole frozen snapshot it
                                 verifies (premonition + learnlab); ``data.bootstrap()``
                                 re-checks every line before importing ``premonition``
    artifacts/.../panels/        the six fresh panels and forbidden-semantics.json
    artifacts/codex-.../stress/  the four stress panels
    artifacts/fable-operator-*/  the two registered launch manifests, kept so the panel
                                 hashes and the frozen hyperparameters can be re-derived
    runtime.local.json           GENERATED, see below
    setup_remote.sh              probes the target python and rewrites runtime.local.json
    run_remote.sh                freeze -> wave -> summary, one thread per process, DONE
    collect.sh                   tar of the results, checkpoints excluded by default
    BUNDLE.json                  sha256 of every file in the bundle

runtime.local.json
    ``premonition_memnn.local_runtime()`` reads it ONLY when ``torch`` cannot be imported,
    and then prepends its ``import_roots`` to ``sys.path``.  On the Mac that is how the
    uv-cached wheels are found, so the generated file carries this host's roots.  On a
    box whose python already has torch the file is never opened; ``setup_remote.sh``
    empties it anyway so a stale macOS path can never be prepended.

    PY -B scripts/fable_reliability_bundle.py build --out <dir>
    PY -B scripts/fable_reliability_bundle.py build --out <dir> --no-tarball
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

sys.path.insert(0, str(HERE))
import fable_operator_reliability as REL                                  # noqa: E402

FROZEN_DIR = 'archive/opus-ovn-20260918-235851/frozen'
FROZEN_SUMS = REL.FROZEN_SUMS
PANEL_DIRS = ('artifacts/astra-canonical-operator-screen-20260920/'
              'astra_canonical_operator_panels',)
TEST_FILE = 'tests/test_fable_operator_reliability.py'
DEFAULT_OUT = 'artifacts/fable-operator-reliability-bundle'
# New, unregistered files.  They live in the worktree this bundler is executed from,
# never in the registered checkout that supplies the frozen sources and panels.
NEW_FILES = ('scripts/fable_operator_reliability.py',
             'scripts/fable_reliability_bundle.py', TEST_FILE)


def prereg_rel(variant):
    return f'artifacts/fable-operator-reliability-{variant}-20260920/PREREGISTRATION.md'


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_of(repo, name):
    """Registered files come from ``repo``; the new wrapper/tests/prereg from this tree."""
    if name in NEW_FILES or name.endswith('/PREREGISTRATION.md'):
        return REPO/name
    path = repo/name
    return path if path.exists() else REPO/name


def frozen_members(repo):
    """Every path FROZEN.SHA256SUMS names, verified before it is copied."""
    out = []
    for line in (repo/FROZEN_SUMS).read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        rel = f'{FROZEN_DIR}/{name.strip().lstrip("./")}'
        if sha256_of(repo/rel) != digest:
            raise SystemExit(f'frozen source changed, refusing to bundle: {rel}')
        out.append(rel)
    return out


def bundle_members(repo, with_tests=True):
    members = [f'scripts/{name}' for name in REL.CLOSURE]
    members.append('scripts/fable_operator_reliability.py')
    members.append('scripts/fable_reliability_bundle.py')
    if with_tests and source_of(repo, TEST_FILE).exists():
        members.append(TEST_FILE)
    members.append(FROZEN_SUMS)
    members.extend(frozen_members(repo))
    panels = {}
    for variant in REL.VARIANTS:
        rel, source, _ = REL.read_source_launch(repo, variant)
        members.append(rel)
        if (REPO/prereg_rel(variant)).exists():
            members.append(prereg_rel(variant))
        for row in source['panels'].values():
            panels[REL._relative_to_frozen_base(row['path'])] = row['sha256']
        panels[REL._relative_to_frozen_base(source['exclusion_path'])] = None
    for name, expected in sorted(panels.items()):
        if expected is not None and sha256_of(repo/name) != expected:
            raise SystemExit(f'panel differs from the registered bytes: {name}')
        members.append(name)
    seen, ordered = set(), []
    for name in members:
        if name in seen:
            continue
        if not source_of(repo, name).exists():
            raise SystemExit(f'missing from this checkout: {name}')
        seen.add(name)
        ordered.append(name)
    return ordered


RUNTIME_NOTE = ('Read by premonition_memnn.local_runtime() ONLY when torch cannot be '
                'imported. setup_remote.sh empties import_roots on a host whose python '
                'already has torch, so no macOS path is ever prepended there.')


def runtime_json(repo):
    roots, shared, python = [], [], sys.executable
    source = repo/'runtime.local.json'
    if source.exists():
        data = json.loads(source.read_text())
        roots = [p for p in data.get('import_roots', []) if Path(p).is_dir()]
        shared = data.get('shared_roots', [])
        python = data.get('python', python)
    return dict(python=python, shared_roots=shared, import_roots=roots,
                generated_by='scripts/fable_reliability_bundle.py', note=RUNTIME_NOTE)


SETUP_SH = '''#!/bin/sh
# Prepare an unpacked bundle for this host.  POSIX sh; no bashisms, no zsh-isms.
# Run this on a Linux box before run_remote.sh.  On the Mac it is OPTIONAL and will
# report that torch is not importable directly - that is expected, because the bundled
# runtime.local.json points at the uv wheel cache, which is exactly how the Mac finds it.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}
echo "bundle root : $HERE"
echo "interpreter : $PY"
"$PY" - "$HERE" <<'EOF'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
try:
    import torch
except Exception as exc:                       # noqa: BLE001
    print('torch is NOT importable directly with this interpreter:', exc)
    print('LEAVING runtime.local.json import_roots as bundled (the Mac path).')
    print('On Linux this means the wrong interpreter: set PY=/opt/conda/bin/python.')
    raise SystemExit(0)
print('torch', torch.__version__, 'from', torch.__file__)
path = root/'runtime.local.json'
data = json.loads(path.read_text())
data['import_roots'] = []
data['shared_roots'] = []
data['python'] = sys.executable
path.write_text(json.dumps(data, indent=2) + '\\n')
print('runtime.local.json import_roots cleared (torch resolves natively)')
EOF
"$PY" -B -c 'import sys; sys.path.insert(0, sys.argv[1]+"/scripts"); import fable_operator_reliability as R; print("repo root resolved to", R.find_repo())' "$HERE"
"$PY" -B "$HERE/scripts/fable_operator_reliability.py" verify \\
      --repo "$HERE" --variant "${VARIANT:-grow-blind}" 2>/dev/null \\
  || echo "no frozen roster yet - run_remote.sh will create one"
echo "setup ok"
'''

RUN_SH = '''#!/bin/sh
# freeze -> wave -> summary.  One torch thread per worker process.
# Env: PY (interpreter), VARIANT, SEEDS, NAME, PARALLEL.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}
VARIANT=${VARIANT:-grow-blind}
SEEDS=${SEEDS:-100-147}
NAME=${NAME:-wave-1}
REL="$HERE/scripts/fable_operator_reliability.py"

OMP_NUM_THREADS=1; MKL_NUM_THREADS=1; OPENBLAS_NUM_THREADS=1
VECLIB_MAXIMUM_THREADS=1; NUMEXPR_NUM_THREADS=1; PYTHONDONTWRITEBYTECODE=1
PYTHONUTF8=1
export OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS PYTHONUTF8
export VECLIB_MAXIMUM_THREADS NUMEXPR_NUM_THREADS PYTHONDONTWRITEBYTECODE

# Fail early and loudly if this torch cannot read panels written by a newer torch.
"$PY" -B "$HERE/scripts/fable_operator_reliability.py" verify --repo "$HERE" \\
      --variant "$VARIANT" --panels >/dev/null 2>&1 \\
  || echo "note: --panels verify needs a frozen roster; it runs again after freeze"

CPUS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
ROSTER=$("$PY" -B -c 'import sys;sys.path.insert(0,sys.argv[1]);import fable_operator_reliability as R;print(len(R.parse_seeds(sys.argv[2])))' "$HERE/scripts" "$SEEDS")
PARALLEL=${PARALLEL:-$CPUS}
if [ "$PARALLEL" -gt "$ROSTER" ]; then PARALLEL=$ROSTER; fi
echo "variant=$VARIANT seeds=$SEEDS roster=$ROSTER cpus=$CPUS parallel=$PARALLEL"

OUT="$HERE/artifacts/fable-operator-reliability-$VARIANT-20260920"
rm -f "$HERE/DONE" "$HERE/FAILED"
"$PY" -B "$REL" freeze --repo "$HERE" --variant "$VARIANT" --seeds "$SEEDS"
"$PY" -B "$REL" verify --repo "$HERE" --variant "$VARIANT" --panels
set +e
"$PY" -B "$REL" wave --repo "$HERE" --variant "$VARIANT" --seeds "$SEEDS" \\
      --parallel "$PARALLEL" --name "$NAME"
WAVE=$?
set -e
"$PY" -B "$REL" summary --repo "$HERE" --variant "$VARIANT" | tee "$OUT/summary.txt"
"$PY" -B "$REL" summary --repo "$HERE" --variant "$VARIANT" --json > "$OUT/summary.json"
date -u +%Y-%m-%dT%H:%M:%SZ > "$HERE/DONE"
echo "wave exit $WAVE" >> "$HERE/DONE"
if [ "$WAVE" -ne 0 ]; then echo "$WAVE" > "$HERE/FAILED"; fi
echo "DONE written; wave exit $WAVE (non-zero only means >=1 seed did not complete)"
'''

COLLECT_SH = '''#!/bin/sh
# Tar the results.  Model checkpoints (final.pt, ~1 MB each) are EXCLUDED unless
# --with-checkpoints is given.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
VARIANT=${VARIANT:-grow-blind}
DIR="artifacts/fable-operator-reliability-$VARIANT-20260920"
OUT=${OUT:-"$HERE/reliability-$VARIANT-results.tar.gz"}
if [ "${1:-}" = "--with-checkpoints" ]; then
  tar -czf "$OUT" -C "$HERE" "$DIR" DONE
else
  tar -czf "$OUT" -C "$HERE" --exclude='*.pt' "$DIR" DONE
fi
echo "$OUT"
ls -l "$OUT"
'''


def build(repo, out, with_tests=True, tarball=True):
    out = Path(out).resolve()
    if out.exists():
        raise SystemExit(f'refusing to overwrite {out}')
    members = bundle_members(repo, with_tests)
    out.mkdir(parents=True)
    for name in members:
        dest = out/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_of(repo, name), dest)
    (out/'runtime.local.json').write_text(
        json.dumps(runtime_json(repo), indent=2) + '\n')
    for name, body, mode in (('setup_remote.sh', SETUP_SH, 0o755),
                             ('run_remote.sh', RUN_SH, 0o755),
                             ('collect.sh', COLLECT_SH, 0o755)):
        (out/name).write_text(body)
        os.chmod(out/name, mode)
    listing = sorted(p for p in out.rglob('*') if p.is_file())
    manifest = dict(
        schema='fable-reliability-bundle-v1',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_repo=str(repo), stream_tag=REL.STREAM_TAG, variants=list(REL.VARIANTS),
        files={str(p.relative_to(out)): sha256_of(p) for p in listing},
        bytes=sum(p.stat().st_size for p in listing))
    (out/'BUNDLE.json').write_text(json.dumps(manifest, indent=2) + '\n')

    listing = sorted(p for p in out.rglob('*') if p.is_file())
    total = sum(p.stat().st_size for p in listing)
    archive = None
    if tarball:
        archive = out.parent/f'{out.name}.tar.gz'
        if archive.exists():
            raise SystemExit(f'refusing to overwrite {archive}')
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(out, arcname=out.name)
    print(f'bundle : {out}')
    print(f'files  : {len(listing)}')
    print(f'size   : {total/1e6:.2f} MB unpacked')
    if archive:
        print(f'tarball: {archive}  ({archive.stat().st_size/1e6:.2f} MB gzipped)')
        print(f'sha256 : {sha256_of(archive)}')
    print()
    for p in listing:
        rel = p.relative_to(out)
        print(f'  {p.stat().st_size:>9}  {rel}')
    return out, archive


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['build', 'list'])
    ap.add_argument('--repo', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-tests', dest='with_tests', action='store_false')
    ap.add_argument('--no-tarball', dest='tarball', action='store_false')
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    repo = REL.find_repo(args.repo)
    if args.command == 'list':
        for name in bundle_members(repo, args.with_tests):
            print(name)
        return
    out = args.out or (REPO/DEFAULT_OUT)
    build(repo, out, args.with_tests, args.tarball)


if __name__ == '__main__':
    main()
