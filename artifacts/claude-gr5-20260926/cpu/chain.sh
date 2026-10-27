#!/bin/bash
# gr-5, the whole registered job on this container's CPU (ADDENDUM-gr5-3). Plain-English puzzles thread, 2026-09-26.
# Run from the repo root with GR5_ADAPTER_DIR set to a folder outside the repo (the adapter stays off git).
# Each step writes its own log under artifacts/claude-gr5-20260926/run/logs; "STEP" lines carry `date -u` times.
set -u
cd "$(git rev-parse --show-toplevel)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONHASHSEED=0
unset SLEEP02C_ADAPTER
BASE=$(ls -d /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*)
D=artifacts/claude-gr5-20260926
PD=artifacts/claude-panel-gr5-20260926
ROWS=$D/train/rows.jsonl
AD="${GR5_ADAPTER_DIR:?set GR5_ADAPTER_DIR}/gr5_adapter.pt"
L=$D/run/logs
stamp() { echo "STEP $1 $(date -u +%Y-%m-%dT%H:%M:%SZ)"; }
last_json() { grep '^{' "$1" | tail -1; }
mkdir -p "$L" "$(dirname "$AD")"
stamp start
python -c "import torch, transformers, sys; print('versions torch', torch.__version__, 'transformers', transformers.__version__, 'python', sys.version.split()[0], 'threads', torch.get_num_threads())"
sha256sum -c $D/SEAL-marks.sha256.txt $D/SEAL-code-gr5.sha256.txt $D/SEAL-addendum1.sha256.txt \
    $D/SEAL-addendum2.sha256.txt $D/SEAL-addendum3.sha256.txt || { echo SEAL-MISMATCH; exit 2; }
(cd $PD && sha256sum -c SEAL-panel.sha256.txt) || { echo SEAL-MISMATCH; exit 2; }
python -B scripts/claude_gr5.py --selftest | grep -qx "gr5 selftest 4/4" || { echo SELFTEST-FAIL gr5; exit 2; }
python -B scripts/claude_gr4.py --selftest | grep -qx "gr4 selftest 15/15" || { echo SELFTEST-FAIL gr4; exit 2; }
python -B scripts/claude_gr5_devclean.py --selftest | grep -qx "gr5 devclean selftest 1/1 (clean 53, shared 19)" \
    || { echo SELFTEST-FAIL devclean; exit 2; }
stamp train
python -B scripts/claude_gr5.py train --model "$BASE" --rows $ROWS --adapter "$AD" > $L/train.log 2>&1 || { echo TRAIN-ERROR; exit 3; }
echo "train $(last_json $L/train.log)"
echo "adapter $(sha256sum "$AD" | cut -d' ' -f1) bytes $(stat -c %s "$AD")"
stamp dev
python -B scripts/claude_gr5.py dev --model "$BASE" --rows $ROWS --adapter "$AD" > $L/dev.log 2>&1 || { echo DEV-ERROR; exit 3; }
DEVJ=$(last_json $L/dev.log)
echo "dev $DEVJ"
stamp devclean
python -B scripts/claude_gr5_devclean.py --model "$BASE" --rows $ROWS --adapter "$AD" > $L/devclean.log 2>&1 || echo DEVCLEAN-ERROR
echo "devclean $(last_json $L/devclean.log)"
if ! echo "$DEVJ" | grep -q '"dev_gate": "PASS"'; then echo DEV-FAIL; stamp stop; exit 4; fi
for t in squares lookalikes unseen general; do
  stamp "L_$t"
  python -B scripts/claude_gr5.py run --task $t --arm L --model "$BASE" --adapter "$AD" --panel-dir $PD --out $D/run \
      > $L/L_$t.log 2>&1 || { echo "RUN-ERROR L_$t"; exit 5; }
  echo "run $(last_json $L/L_$t.log)"
done
for t in squares lookalikes unseen; do
  stamp "P0_$t"
  python -B scripts/claude_gr5.py run --task $t --arm P0 --model "$BASE" --panel-dir $PD --out $D/run \
      > $L/P0_$t.log 2>&1 || { echo "RUN-ERROR P0_$t"; exit 5; }
  echo "run $(last_json $L/P0_$t.log)"
done
stamp score
python -B scripts/claude_gr5.py score --out $D/run --panel-dir $PD --score $D/score > $L/score.log 2>&1 || { echo SCORE-ERROR; exit 6; }
echo "score $(last_json $L/score.log)"
stamp done
