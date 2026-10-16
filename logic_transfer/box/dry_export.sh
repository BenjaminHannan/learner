#!/bin/bash
# CPU dry run of the LT-2 checkpoint export chain (Recipe 2 gate, change 2): a short rung-6 course on CPU -> the box's own export code (lt2_export.sh + ck_export.sh, sourced,
# not copied) printing into a saved log -> vast.py collectck reading that saved log (log_text replaced by a file read) -> sha256 of every reassembled checkpoint against the
# original, and torch.load. Usage: bash dry_export.sh WORKDIR   (WORKDIR holds par/t1sdr (parents), data (curriculum build), w/ladder/rows/rung6 (ladder build);
# env: RUNS="s200:1,s201:2" UPDATES=50 PROCS=2 CKPACE=1 CKPOLL=2). Writes WORKDIR/saved.log, WORKDIR/collected/, WORKDIR/DRY-RESULT.txt.
set -u
J=$(cd "$1" && pwd); HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
RUNS=${RUNS:-s200:1,s201:2}; UPDATES=${UPDATES:-50}; PROCS=${PROCS:-2}
export CKPACE=${CKPACE:-1} CKPOLL=${CKPOLL:-2} PYTHONPATH=$REPO
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CKX=$REPO/custom_io/box/ck_export.sh; mkdir -p $J/res; . $HERE/lt2_export.sh
: > $J/saved.log
(
  say "DRY START runs=$RUNS updates=$UPDATES"
  ( cd $REPO && python3 -m logic_transfer.lt2 run --rung 6 --work $J/w/ladder --parents-dir $J/par/t1sdr --sk200k $J/data --device cpu --procs $PROCS --threads 2 \
      --updates $UPDATES --mix-frac 0.5 --lr 1e-4 --eval-n 100 --eval-every $UPDATES --runs $RUNS --no-falsifier > $J/out/rung6-run.log 2>&1 ) &
  RUNPID=$!
  lt2_export_loop 6 &
  EXPID=$!
  wait $RUNPID; say "DRY course exited"; wait $EXPID; say "DRY END"
) > $J/saved.log 2>&1
rm -rf $J/collected; mkdir -p $J/collected
WANT=$(cd $J/w/ladder && ls rung6/*/checkpoint.pt | sed 's|/checkpoint.pt||' | tr '\n' ' ')
python3 - "$J" "$REPO" "$WANT" <<'PY' | tee $J/DRY-RESULT.txt
import hashlib, importlib.util, json, sys, argparse, pathlib
J, REPO, WANT = sys.argv[1], sys.argv[2], sys.argv[3].split()
spec = importlib.util.spec_from_file_location('vast', REPO + '/custom_io/box/vast.py'); v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
v.log_text = lambda i, tail=20000: '\n'.join(open(J + '/saved.log').read().splitlines()[-tail:])     # the log API replaced by the saved log, with the same tail limit
a = argparse.Namespace(id=0, out=J + '/collected', max_min=2, tail=9000, want=' '.join(WANT))
v.time.sleep = lambda s: None
v.collectck(a)
ok = True
for jr in WANT:
    orig = pathlib.Path(J, 'w/ladder', jr, 'checkpoint.pt'); got = pathlib.Path(J, 'collected', jr, 'checkpoint.pt')
    if not got.exists():
        print('MISSING', jr); ok = False; continue
    h1, h2 = hashlib.sha256(orig.read_bytes()).hexdigest(), hashlib.sha256(got.read_bytes()).hexdigest()
    import torch; ck = torch.load(got, map_location='cpu', weights_only=False)
    print(jr, 'bytes', got.stat().st_size, 'sha256 original', h1[:16], 'reassembled', h2[:16], 'SAME' if h1 == h2 else 'DIFFERENT', 'torch.load keys', sorted(ck.keys()))
    ok &= (h1 == h2)
print('DRY RUN', 'PASS' if ok and WANT else 'FAIL', len(WANT), 'checkpoints')
sys.exit(0 if ok and WANT else 1)
PY
