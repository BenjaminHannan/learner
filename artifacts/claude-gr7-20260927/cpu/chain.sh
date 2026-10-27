#!/bin/bash
# gr-7, the whole registered job on this container's CPU (PASSMARKS-gr7 "Where it runs"; ADDENDUM-gr5-3's rules).
# Plain-English puzzles thread, 2026-09-27. Run from the repo root with GR7_ADAPTER_DIR set to a folder outside the
# repo (the adapter stays off git). Each step writes its own log under artifacts/claude-gr7-20260927/run/logs; "STEP"
# lines carry `date -u` times.
set -u
cd "$(git rev-parse --show-toplevel)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONHASHSEED=0
unset SLEEP02C_ADAPTER
BASE=$(ls -d /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*)
D=artifacts/claude-gr7-20260927
D6=artifacts/claude-gr6-20260927
PD=artifacts/claude-panel-gr6-20260927
ROWS=$D6/train/rows.jsonl
AD="${GR7_ADAPTER_DIR:?set GR7_ADAPTER_DIR}/gr7_adapter.pt"
G6AD=/mnt/project-files/plain-english-puzzles/gr6_adapter.pt
G6SHA=54feb2fd236aac7263bccefd1bb5ce0dcd56551042ffdc1307b83c6e61109aef
G5AD=/mnt/project-files/plain-english-puzzles/gr5_adapter.pt
G5SHA=9f19edb7503e7a81f78bbe922bb2ae38319b04301a460cbdc2c0c843324dceb4
L=$D/run/logs
stamp() { echo "STEP $1 $(date -u +%Y-%m-%dT%H:%M:%SZ)"; }
last_json() { grep '^{' "$1" | tail -1; }
mkdir -p "$L" "$(dirname "$AD")"
stamp start
python -c "import torch, transformers, sys; print('versions torch', torch.__version__, 'transformers', transformers.__version__, 'python', sys.version.split()[0], 'threads', torch.get_num_threads())"
sha256sum -c $D/SEAL-marks.sha256.txt $D/SEAL-code-gr7.sha256.txt $D6/SEAL-rows-chain.sha256.txt || { echo SEAL-MISMATCH; exit 2; }
(cd $PD && sha256sum -c SEAL-panel.sha256.txt) || { echo SEAL-MISMATCH; exit 2; }
[ "$(sha256sum "$G6AD" | cut -d' ' -f1)" = "$G6SHA" ] || { echo "SEAL-MISMATCH gr6 adapter"; exit 2; }
[ "$(sha256sum "$G5AD" | cut -d' ' -f1)" = "$G5SHA" ] || { echo "SEAL-MISMATCH gr5 adapter"; exit 2; }
python -B scripts/claude_gr7.py --selftest | grep -qx "gr7 selftest 1/1" || { echo SELFTEST-FAIL gr7; exit 2; }
python -B scripts/claude_gr5.py --selftest | grep -qx "gr5 selftest 4/4" || { echo SELFTEST-FAIL gr5; exit 2; }
python -B scripts/claude_gr4.py --selftest | grep -qx "gr4 selftest 15/15" || { echo SELFTEST-FAIL gr4; exit 2; }
stamp train
python -B scripts/claude_gr7.py train --model "$BASE" --rows $ROWS --start "$G6AD" --adapter "$AD" > $L/train.log 2>&1 || { echo TRAIN-ERROR; exit 3; }
TJ=$(last_json $L/train.log)
echo "train $TJ"
echo "adapter $(sha256sum "$AD" | cut -d' ' -f1) bytes $(stat -c %s "$AD")"
LOSS=$(echo "$TJ" | python -c "import sys, json; print(json.loads(sys.stdin.read())['epoch6_loss'])")
stamp dev
python -B scripts/claude_gr7.py dev --model "$BASE" --rows $ROWS --adapter "$AD" --loss "$LOSS" > $L/dev.log 2>&1 || { echo DEV-ERROR; exit 3; }
DEVJ=$(last_json $L/dev.log)
echo "dev $DEVJ"
if ! echo "$DEVJ" | grep -q '"dev_gate": "PASS"'; then echo "DEV-STOP $(echo "$DEVJ" | python -c "import sys, json; print(json.loads(sys.stdin.read())['outcome'])")"; stamp stop; exit 4; fi
for t in squares lookalikes unseen general; do
  stamp "L7_$t"
  python -B scripts/claude_gr7.py run --task $t --arm L7 --model "$BASE" --adapter "$AD" --panel-dir $PD --out $D/run \
      > $L/L7_$t.log 2>&1 || { echo "RUN-ERROR L7_$t"; exit 5; }
  echo "run $(last_json $L/L7_$t.log)"
done
for t in squares lookalikes unseen; do
  stamp "G5_$t"
  python -B scripts/claude_gr7.py run --task $t --arm G5 --model "$BASE" --adapter "$G5AD" --panel-dir $PD --out $D/run \
      > $L/G5_$t.log 2>&1 || { echo "RUN-ERROR G5_$t"; exit 5; }
  echo "run $(last_json $L/G5_$t.log)"
done
stamp score
python -B scripts/claude_gr7.py score --out $D/run --panel-dir $PD --score $D/score > $L/score.log 2>&1 || { echo SCORE-ERROR; exit 6; }
echo "score $(last_json $L/score.log)"
stamp done
