#!/bin/bash
# gr-7d: L7 and G5 on the code-made practice set, then the count (PLAN-gr7d.md). Plain-English puzzles thread,
# 2026-09-27. Run from the repo root. Practice only: never a test, never trained on. "STEP" lines carry `date -u` times.
set -u
cd "$(git rev-parse --show-toplevel)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONHASHSEED=0
unset SLEEP02C_ADAPTER
BASE=$(ls -d /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*)
D=artifacts/claude-gr7d-20260927
PD=$D/practice
L=$D/run/logs
G7AD=/mnt/project-files/plain-english-puzzles/gr7_adapter.pt
G7SHA=c8f9555773d6bb3ac4e99157a37a93e6d65c593dec5abc3e947b5b3b356d05a1
G5AD=/mnt/project-files/plain-english-puzzles/gr5_adapter.pt
G5SHA=9f19edb7503e7a81f78bbe922bb2ae38319b04301a460cbdc2c0c843324dceb4
stamp() { echo "STEP $1 $(date -u +%Y-%m-%dT%H:%M:%SZ)"; }
last_json() { grep '^{' "$1" | tail -1; }
mkdir -p "$L"
stamp start
sha256sum -c $D/SEAL-gr7d.sha256.txt || { echo SEAL-MISMATCH; exit 2; }
(cd $PD && sha256sum -c SEAL-practice.sha256.txt) || { echo SEAL-MISMATCH practice; exit 2; }
[ "$(sha256sum "$G7AD" | cut -d' ' -f1)" = "$G7SHA" ] || { echo "SEAL-MISMATCH gr7 adapter"; exit 2; }
[ "$(sha256sum "$G5AD" | cut -d' ' -f1)" = "$G5SHA" ] || { echo "SEAL-MISMATCH gr5 adapter"; exit 2; }
python -B scripts/claude_gr7_diag.py --selftest | grep -qx "gr7d selftest 8/8" || { echo SELFTEST-FAIL gr7d; exit 2; }
python -B scripts/claude_gr7.py --selftest | grep -qx "gr7 selftest 1/1" || { echo SELFTEST-FAIL gr7; exit 2; }
for arm in L7 G5; do
  AD=$G7AD; [ $arm = G5 ] && AD=$G5AD
  for t in lookalikes squares unseen; do
    stamp "${arm}_$t"
    python -B scripts/claude_gr7.py run --task $t --arm $arm --model "$BASE" --adapter "$AD" --panel-dir $PD \
        --out $D/run > $L/${arm}_$t.log 2>&1 || { echo "RUN-ERROR ${arm}_$t"; exit 5; }
    echo "run $(last_json $L/${arm}_$t.log)"
  done
done
stamp count
python -B scripts/claude_gr7_diag.py count --practice $PD --run $D/run > $L/count.log 2>&1 || { echo COUNT-ERROR; exit 6; }
cat $L/count.log
stamp done
