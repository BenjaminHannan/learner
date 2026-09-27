#!/bin/bash
# gr-9 post hoc, practice data only, report only (no marks). The question: were L9's row-skip misses on familiar
# squares caused by the separator rows or by the 3 extra epochs? And does gr-7's reader miss the same items?
# It reads squares and seen with L7 (gr-7) and L7c (gr-7 + 3 epochs on gr-6 rows), greedy, after chain-r1 has ended.
set -u
cd "$(git rev-parse --show-toplevel)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONHASHSEED=0
unset SLEEP02C_ADAPTER
BASE=$(ls -d /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*)
D=artifacts/claude-gr9-20260927
O=$D/posthoc/run
PF=/mnt/project-files/plain-english-puzzles
stamp() { echo "STEP $1 $(date -u +%Y-%m-%dT%H:%M:%SZ)"; }
while pgrep -f "cpu/chain-r1.sh" >/dev/null; do sleep 60; done
stamp start
[ -e $PF/gr9_l7c_adapter.pt ] || { echo "NO-L7C-ADAPTER"; exit 3; }
mkdir -p $O/logs
for arm in L7 L7c; do
  A=$PF/gr7_adapter.pt; [ $arm = L7c ] && A=$PF/gr9_l7c_adapter.pt
  for t in squares seen; do
    stamp "${arm}_$t"
    python -B scripts/claude_gr9.py run --task $t --arm $arm --model "$BASE" --adapter "$A" --dev $D/dev --out $O \
        > $O/logs/${arm}_$t.log 2>&1 || { echo "RUN-ERROR ${arm}_$t"; exit 5; }
    grep '^{' $O/logs/${arm}_$t.log | tail -1
  done
done
stamp done
