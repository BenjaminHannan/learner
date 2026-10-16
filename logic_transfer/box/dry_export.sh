#!/bin/bash
# CPU dry run of the LT-2 checkpoint export chain (Recipe 2 gate, change 2): a short rung-6 course on CPU -> the box's own export code (lt2_export.sh + ck_export.sh, sourced,
# not copied) printing into a saved log -> vast.py collectck reading that saved log (log_text replaced by a file read) -> sha256 of every reassembled checkpoint against the
# original, and torch.load. Usage: bash dry_export.sh WORKDIR   (WORKDIR holds par/t1sdr (parents), data (curriculum build), w/ladder/rows/rung6 (ladder build);
# env: RUNS="s200:1,s201:2" UPDATES=50 PROCS=2 CKPACE=1 CKPOLL=2). Writes WORKDIR/saved.log, WORKDIR/collected/, WORKDIR/DRY-RESULT.txt.
set -u
J=$(cd "$1" && pwd); HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
RUNS=${RUNS:-s200:1,s201:2}; UPDATES=${UPDATES:-50}; PROCS=${PROCS:-2}
export CKPACE=${CKPACE:-1} CKPOLL=${CKPOLL:-2} CKPART=${CKPART:-1000000} PYTHONPATH=$REPO
say() { echo "=== $* $(date -u +%FT%TZ)"; }
CKX=$REPO/custom_io/box/ck_export.sh; mkdir -p $J/res; . $HERE/lt2_export.sh
if [ "${SKIP_RUN:-0}" != 1 ]; then   # SKIP_RUN=1: only re-read an existing saved.log (e.g. with REPLAY_JUMP_AT=8 REPLAY_JUMP=14000, a stalled poll)
: > $J/saved.log
(
  say "DRY START runs=$RUNS updates=$UPDATES"
  ( cd $REPO && python3 -m logic_transfer.lt2 run --rung 6 --work $J/w/ladder --parents-dir $J/par/t1sdr --sk200k $J/data --device cpu --procs $PROCS --threads 2 \
      --updates $UPDATES --mix-frac 0.5 --lr 1e-4 --eval-n 100 --eval-every $UPDATES --runs $RUNS --no-falsifier > $J/out/rung6-run.log 2>&1 ) &
  RUNPID=$!
  lt2_export_loop 6 &
  EXPID=$!
  wait $RUNPID; say "DRY course exited"; wait $EXPID; say "DRY END"
) 2>&1 | cat > $J/saved.log      # a pipe, like the container log (stdout of a file would let the shell's own writes overwrite what `>> /dev/stdout` appended)
fi
rm -rf $J/collected; mkdir -p $J/collected
WANT=$(cd $J/w/ladder && ls rung6/*/checkpoint.pt | sed 's|/checkpoint.pt||' | tr '\n' ' ')
python3 - "$J" "$REPO" "$WANT" <<'PY' | tee $J/DRY-RESULT.txt
import hashlib, importlib.util, json, sys, argparse, pathlib
J, REPO, WANT = sys.argv[1], sys.argv[2], sys.argv[3].split()
spec = importlib.util.spec_from_file_location('vast', REPO + '/custom_io/box/vast.py'); v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
import os
lines = open(J + '/saved.log').read().splitlines()
st = {'shown': 0, 'polls': 0}
STEP, JUMP_AT, JUMP = int(os.environ.get('REPLAY_STEP', '2800')), int(os.environ.get('REPLAY_JUMP_AT', '0')), int(os.environ.get('REPLAY_JUMP', '0'))
def log_text(i, tail=20000):
    # the live log API replaced by a replay of the saved log: every poll reveals STEP more lines (a 1 MB part is about 2,800 lines and the box prints one per 40 s, the collector polls
    # every 40 s) and returns only the newest `tail` revealed lines, as the API does; REPLAY_JUMP_AT=k makes poll k reveal REPLAY_JUMP lines at once (a stalled poll: parts fall out of the window)
    st['polls'] += 1
    if st['shown'] >= len(lines):
        st['after'] = st.get('after', 0) + 1
        if st['after'] > 3:
            raise RuntimeError('replay ended: the whole log was shown and the collector still lacks checkpoints')
    st['shown'] = min(len(lines), st['shown'] + (JUMP if st['polls'] == JUMP_AT else STEP))
    return '\n'.join(lines[max(0, st['shown'] - tail):st['shown']])
v.log_text = log_text
a = argparse.Namespace(id=0, out=J + '/collected', max_min=2000, tail=9000, want=' '.join(WANT))
print('replay: %d log lines, step %d, jump at poll %d of %d lines' % (len(lines), STEP, JUMP_AT, JUMP))
v.time.sleep = lambda s: None
try:
    v.collectck(a)
except RuntimeError as e:
    print('COLLECTOR STOPPED:', e)
ok = True
for jr in WANT:
    orig = pathlib.Path(J, 'w/ladder', jr, 'checkpoint.pt'); got = pathlib.Path(J, 'collected', jr, 'checkpoint.pt')
    if not got.exists():
        print('MISSING', jr); ok = False; continue
    h1, h2 = hashlib.sha256(orig.read_bytes()).hexdigest(), hashlib.sha256(got.read_bytes()).hexdigest()
    import torch; ck = torch.load(got, map_location='cpu', weights_only=False)
    print(jr, 'bytes', got.stat().st_size, 'sha256 original', h1[:16], 'reassembled', h2[:16], 'SAME' if h1 == h2 else 'DIFFERENT', 'torch.load keys', sorted(ck.keys()))
    sf = pathlib.Path(J, 'collected', jr.replace('/', '__') + '.sha256')
    line = sf.read_text().strip() if sf.exists() else 'NO .sha256 FILE'
    print('   collector record:', line[:200])
    ok &= (h1 == h2) and ('(box: ' in line and 'not printed' not in line and h2 in line)    # the box printed this file sha (CKSHA) and the collector checked against it
print('DRY RUN', 'PASS' if ok and WANT else 'FAIL', len(WANT), 'checkpoints')
sys.exit(0 if ok and WANT else 1)
PY
