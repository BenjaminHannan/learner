#!/bin/bash
# gr-8 dev: the reader's own likelihood picks the size (PLAN-gr8d.md). Plain-English puzzles thread, 2026-09-27.
# Run from the repo root. Practice only: never a test, never trained on. "STEP" lines carry `date -u` times.
set -u
cd "$(git rev-parse --show-toplevel)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONHASHSEED=0
unset SLEEP02C_ADAPTER
BASE=$(ls -d /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*)
D=artifacts/claude-gr8d-20260927
PD=$D/practice
L=$D/run/logs
G7AD=/mnt/project-files/plain-english-puzzles/gr7_adapter.pt
G7SHA=c8f9555773d6bb3ac4e99157a37a93e6d65c593dec5abc3e947b5b3b356d05a1
stamp() { echo "STEP $1 $(date -u +%Y-%m-%dT%H:%M:%SZ)"; }
last_json() { grep '^{' "$1" | tail -1; }
mkdir -p "$L"
stamp start
sha256sum -c $D/SEAL-gr8d.sha256.txt || { echo SEAL-MISMATCH; exit 2; }
(cd $PD && sha256sum -c SEAL-practice.sha256.txt) || { echo SEAL-MISMATCH practice; exit 2; }
(cd artifacts/claude-gr7d-20260927/practice && sha256sum -c SEAL-practice.sha256.txt) || { echo SEAL-MISMATCH gr7d; exit 2; }
[ "$(sha256sum "$G7AD" | cut -d' ' -f1)" = "$G7SHA" ] || { echo "SEAL-MISMATCH gr7 adapter"; exit 2; }
python -B scripts/claude_gr8.py --selftest | grep -qx "gr8 selftest 4/4" || { echo SELFTEST-FAIL gr8; exit 2; }
python -B scripts/claude_gr7_diag.py --selftest | grep -qx "gr7d selftest 8/8" || { echo SELFTEST-FAIL gr7d; exit 2; }
for t in replay squares unseen lookalikes; do
  stamp "L8_$t"
  python -B scripts/claude_gr8.py run --task $t --model "$BASE" --adapter "$G7AD" --practice $PD --out $D/run \
      > $L/L8_$t.log 2>&1 || { echo "RUN-ERROR L8_$t"; exit 5; }
  echo "run $(last_json $L/L8_$t.log)"
done
stamp count
python -B scripts/claude_gr8.py count --practice $PD --run $D/run > $L/count.log 2>&1 || { echo COUNT-ERROR; exit 6; }
cat $L/count.log
stamp done
