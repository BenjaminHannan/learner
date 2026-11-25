#!/bin/zsh
# Driver for Rank 6 dev seeds 42 and 43 (forecast6/PLAN-AMENDMENT.md).
# Sealed exam is NOT included — launch manually once only after a 2-seed dev PASS.
set -u
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm6 || exit 2
PY=~/learner-ops/m3-torch/.venv/bin/python

power_ok() {
  b=$(pmset -g batt)
  echo "$b" | grep -q "AC Power" && return 0
  pct=$(echo "$b" | grep -o "[0-9]*%" | head -1 | tr -d %)
  [ "${pct:-0}" -ge 35 ]
}

run_seed() {
  local seed=$1
  n=0
  until power_ok; do
    [ $n -eq 0 ] && echo "waiting for power before seed $seed $(date)" >> rank6_driver.log
    n=$((n + 1))
    [ $n -gt 960 ] && { echo "DONE_NOPOWER seed=$seed $(date)" >> rank6_driver.log; exit 1; }
    sleep 30
  done
  ./withlock.sh run_r6_s${seed}.log $PY -B -u train_v6.py \
    --size R6conv --device mps --steps 5000 --batch 64 \
    --lr 3e-4 --wd 1e-4 --w-lat 0.05 --seed "$seed" --max-minutes 14.0 \
    --save-forecasts \
    --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
    --out run_r6_s${seed}
  rc=$?
  echo "seed $seed rc=$rc $(date)" >> rank6_driver.log
  [ $rc -eq 0 ] || exit $rc
}

df -g  | awk 'NR==2{ if ($4<12) {print "DISK LOW " $4 "G"; exit 1} }' >> rank6_driver.log || { echo DONE_DISK >> rank6_driver.log; exit 1; }

run_seed 42
run_seed 43

$PY -c "
import json
s42 = json.load(open('run_r6_s42/score_dev.json'))
s43 = json.load(open('run_r6_s43/score_dev.json'))
v42, v43 = s42['rank6_verdict'], s43['rank6_verdict']
k1_42, k1_43 = s42['k1']['E_over_B'], s43['k1']['E_over_B']
k5_42, k5_43 = s42['k5']['E_over_B'], s43['k5']['E_over_B']
if v42 == 'PASS' and v43 == 'PASS':
    agg = 'PASS'
    winner = 's42' if (k1_42, k5_42, 42) <= (k1_43, k5_43, 43) else 's43'
elif v42 in ('PASS', 'PARTIAL') and v43 in ('PASS', 'PARTIAL'):
    agg = 'PARTIAL'
    winner = 'NONE'
else:
    agg = 'FAIL'
    winner = 'NONE'
print(f'RANK6_DEV_SUMMARY s42={v42} (k1={k1_42:.4f}, k5={k5_42:.4f}) s43={v43} (k1={k1_43:.4f}, k5={k5_43:.4f}) agg={agg} sealed_candidate={winner}')
" >> rank6_driver.log 2>&1
echo "DONE_ALL $(date)" >> rank6_driver.log
