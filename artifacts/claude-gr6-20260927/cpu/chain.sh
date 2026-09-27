#!/bin/bash
# gr-6, the whole registered job on this container's CPU (PASSMARKS-gr6 "Where it runs"; ADDENDUM-gr5-3's rules).
# Plain-English puzzles thread, 2026-09-27. Run from the repo root with GR6_ADAPTER_DIR set to a folder outside the
# repo (the adapter stays off git). Each step writes its own log under artifacts/claude-gr6-20260927/run/logs; "STEP"
# lines carry `date -u` times.
set -u
cd "$(git rev-parse --show-toplevel)"
export HF_HUB_OFFLINE=1 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 PYTHONHASHSEED=0
unset SLEEP02C_ADAPTER
BASE=$(ls -d /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c*)
D=artifacts/claude-gr6-20260927
PD=artifacts/claude-panel-gr6-20260927
ROWS=$D/train/rows.jsonl
AD="${GR6_ADAPTER_DIR:?set GR6_ADAPTER_DIR}/gr6_adapter.pt"
G5AD=/mnt/project-files/plain-english-puzzles/gr5_adapter.pt
G5SHA=9f19edb7503e7a81f78bbe922bb2ae38319b04301a460cbdc2c0c843324dceb4
L=$D/run/logs
stamp() { echo "STEP $1 $(date -u +%Y-%m-%dT%H:%M:%SZ)"; }
last_json() { grep '^{' "$1" | tail -1; }
mkdir -p "$L" "$(dirname "$AD")"
stamp start
python -c "import torch, transformers, sys; print('versions torch', torch.__version__, 'transformers', transformers.__version__, 'python', sys.version.split()[0], 'threads', torch.get_num_threads())"
(cd $D && sha256sum -c SEAL-marks.sha256.txt) || { echo SEAL-MISMATCH; exit 2; }     # this seal lists a bare file name
sha256sum -c $D/SEAL-layouts-code.sha256.txt $D/SEAL-rows-chain.sha256.txt || { echo SEAL-MISMATCH; exit 2; }
(cd $PD && sha256sum -c SEAL-panel.sha256.txt) || { echo SEAL-MISMATCH; exit 2; }
[ "$(sha256sum "$G5AD" | cut -d' ' -f1)" = "$G5SHA" ] || { echo "SEAL-MISMATCH gr5 adapter"; exit 2; }
python -B scripts/claude_gr6.py --selftest | grep -qx "gr6 selftest 4/4" || { echo SELFTEST-FAIL gr6; exit 2; }
python -B scripts/claude_gr5.py --selftest | grep -qx "gr5 selftest 4/4" || { echo SELFTEST-FAIL gr5; exit 2; }
python -B scripts/claude_gr4.py --selftest | grep -qx "gr4 selftest 15/15" || { echo SELFTEST-FAIL gr4; exit 2; }
stamp train
python -B scripts/claude_gr6.py train --model "$BASE" --rows $ROWS --adapter "$AD" > $L/train.log 2>&1 || { echo TRAIN-ERROR; exit 3; }
echo "train $(last_json $L/train.log)"
echo "adapter $(sha256sum "$AD" | cut -d' ' -f1) bytes $(stat -c %s "$AD")"
stamp dev
python -B scripts/claude_gr6.py dev --model "$BASE" --rows $ROWS --adapter "$AD" > $L/dev.log 2>&1 || { echo DEV-ERROR; exit 3; }
DEVJ=$(last_json $L/dev.log)
echo "dev $DEVJ"
stamp devclean
python -B scripts/claude_gr5_devclean.py --model "$BASE" --rows $ROWS --adapter "$AD" > $L/devclean.log 2>&1 || echo DEVCLEAN-ERROR
echo "devclean $(last_json $L/devclean.log)"
if ! echo "$DEVJ" | grep -q '"dev_gate": "PASS"'; then echo DEV-FAIL; stamp stop; exit 4; fi
for t in squares lookalikes unseen general; do
  stamp "L6_$t"
  python -B scripts/claude_gr6.py run --task $t --arm L6 --model "$BASE" --adapter "$AD" --panel-dir $PD --out $D/run \
      > $L/L6_$t.log 2>&1 || { echo "RUN-ERROR L6_$t"; exit 5; }
  echo "run $(last_json $L/L6_$t.log)"
done
for t in squares lookalikes unseen; do
  stamp "G5_$t"
  python -B scripts/claude_gr6.py run --task $t --arm G5 --model "$BASE" --adapter "$G5AD" --panel-dir $PD --out $D/run \
      > $L/G5_$t.log 2>&1 || { echo "RUN-ERROR G5_$t"; exit 5; }
  echo "run $(last_json $L/G5_$t.log)"
done
stamp score
python -B scripts/claude_gr6.py score --out $D/run --panel-dir $PD --score $D/score > $L/score.log 2>&1 || { echo SCORE-ERROR; exit 6; }
echo "score $(last_json $L/score.log)"
stamp done
