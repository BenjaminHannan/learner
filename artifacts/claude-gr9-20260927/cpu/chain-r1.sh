#!/bin/bash
# gr-9 dev: separator variety in the reader's training (PASSMARKS-gr9.md). Plain-English puzzles thread, 2026-09-27.
# Re-launch r1 of the sealed chain.sh after the 14:32 stop (RUN-NOTE-gr9-ADDENDUM-2); outputs go to run-r1/. Run from the repo root. Practice only: never a test. "STEP" lines carry `date -u` times. Each file is made once.
set -u
cd "$(git rev-parse --show-toplevel)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONHASHSEED=0
unset SLEEP02C_ADAPTER
BASE=$(ls -d /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*)
D=artifacts/claude-gr9-20260927
DV=$D/dev
R=$D/run-r1
L=$R/logs
PF=/mnt/project-files/plain-english-puzzles
G7AD=$PF/gr7_adapter.pt
G7SHA=c8f9555773d6bb3ac4e99157a37a93e6d65c593dec5abc3e947b5b3b356d05a1
G6ROWS=artifacts/claude-gr6-20260927/train/rows.jsonl
G6SHA=881b999999ffbb495f2e0d46baa98395ec322648fb04bc8a7d7f39d03ebd7651
A9=$PF/gr9_adapter.pt
A7C=$PF/gr9_l7c_adapter.pt
stamp() { echo "STEP $1 $(date -u +%Y-%m-%dT%H:%M:%SZ)"; }
last_json() { grep '^{' "$1" | tail -1; }
mkdir -p "$L"
stamp start
sha256sum -c $D/SEAL-gr9.sha256.txt || { echo SEAL-MISMATCH; exit 2; }
(cd $DV && sha256sum -c SEAL-dev.sha256.txt) || { echo SEAL-MISMATCH dev; exit 2; }
[ "$(sha256sum "$G7AD" | cut -d' ' -f1)" = "$G7SHA" ] || { echo "SEAL-MISMATCH gr7 adapter"; exit 2; }
[ "$(sha256sum "$G6ROWS" | cut -d' ' -f1)" = "$G6SHA" ] || { echo "SEAL-MISMATCH gr6 rows"; exit 2; }
if [ -e "$A9" ] || [ -e "$A7C" ]; then echo "ADAPTER-EXISTS (each adapter is trained once)"; exit 3; fi
python -B scripts/claude_gr9.py --selftest | grep -qx "gr9 selftest 5/5" || { echo SELFTEST-FAIL gr9; exit 2; }
python -B scripts/claude_gr8.py --selftest | grep -qx "gr8 selftest 4/4" || { echo SELFTEST-FAIL gr8; exit 2; }

stamp train_L9
python -B scripts/claude_gr9.py train --model "$BASE" --rows $D/train/rows.jsonl --start "$G7AD" --adapter "$A9" \
    > $L/train_L9.log 2>&1 || { echo "TRAIN-ERROR L9"; exit 4; }
echo "train $(last_json $L/train_L9.log)"
sha256sum "$A9" | sed "s#$PF/##" > $R/adapter-L9.sha256.txt
for t in squares seen heldout lookalikes; do
  stamp "L9_$t"
  python -B scripts/claude_gr9.py run --task $t --arm L9 --model "$BASE" --adapter "$A9" --dev $DV --out $R \
      > $L/L9_$t.log 2>&1 || { echo "RUN-ERROR L9_$t"; exit 5; }
  echo "run $(last_json $L/L9_$t.log)"
done
for t in heldout lookalikes; do
  stamp "L7_$t"
  python -B scripts/claude_gr9.py run --task $t --arm L7 --model "$BASE" --adapter "$G7AD" --dev $DV --out $R \
      > $L/L7_$t.log 2>&1 || { echo "RUN-ERROR L7_$t"; exit 5; }
  echo "run $(last_json $L/L7_$t.log)"
done
stamp count_main
python -B scripts/claude_gr9.py count --dev $DV --run $R > $L/count-main.log 2>&1 || { echo COUNT-ERROR; exit 6; }
tail -1 $L/count-main.log

stamp train_L7c
python -B scripts/claude_gr9.py train --model "$BASE" --rows $G6ROWS --start "$G7AD" --adapter "$A7C" \
    > $L/train_L7c.log 2>&1 || { echo "TRAIN-ERROR L7c"; exit 4; }
echo "train $(last_json $L/train_L7c.log)"
sha256sum "$A7C" | sed "s#$PF/##" > $R/adapter-L7c.sha256.txt
stamp L7c_heldout
python -B scripts/claude_gr9.py run --task heldout --arm L7c --model "$BASE" --adapter "$A7C" --dev $DV --out $R \
    > $L/L7c_heldout.log 2>&1 || { echo "RUN-ERROR L7c_heldout"; exit 5; }
echo "run $(last_json $L/L7c_heldout.log)"
stamp count
python -B scripts/claude_gr9.py count --dev $DV --run $R > $L/count.log 2>&1 || { echo COUNT-ERROR; exit 6; }
cat $L/count.log
stamp done
