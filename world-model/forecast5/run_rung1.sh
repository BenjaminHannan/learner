#!/bin/zsh
# Lead driver for Rung 1 dev arms (PLAN-AMENDMENT §6.4/§6.6). Sealed exam not included.
set -u
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm5 || exit 2
PY=~/learner-ops/m3-torch/.venv/bin/python
power_ok() {
  b=$(pmset -g batt)
  echo "$b" | grep -q "AC Power" && return 0
  pct=$(echo "$b" | grep -o "[0-9]*%" | head -1 | tr -d %)
  [ "${pct:-0}" -ge 35 ]
}
run_arm() {
  # wait (up to 8 h) for AC power or battery >= 35% before each arm
  n=0; until power_ok; do [ $n -eq 0 ] && echo "waiting for power before $1 $(date)" >> rung1_driver.log; n=$((n+1)); [ $n -gt 960 ] && { echo DONE_NOPOWER >> rung1_driver.log; exit 1; }; sleep 30; done
  ./withlock.sh run_r1_$1.log $PY -B -u train_v5.py --arm $1 --size P7toy --device mps --steps 3000 --batch 64 \
    --lr 3e-4 --wd 1e-4 --seed 42 --max-minutes 28.0 --save-forecasts \
    --train-data data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz --out run_r1_$1
  echo "arm $1 rc=$? $(date)" >> rung1_driver.log
}
df -g  | awk 'NR==2{ if ($4<12) {print "DISK LOW " $4 "G"; exit 1} }' >> rung1_driver.log || { echo DONE_DISK >> rung1_driver.log; exit 1; }
run_arm bundle
wrong=$($PY -c "import json;print(json.load(open('run_r1_bundle/score_dev.json'))['rank3_proved_wrong'])" 2>>rung1_driver.log || echo MISSING)
echo "bundle rank3_proved_wrong=$wrong" >> rung1_driver.log
if [ "$wrong" != "False" ]; then echo DONE_STOPPED >> rung1_driver.log; exit 0; fi
for a in no_signal_path no_act_film abs_loss_only; do run_arm $a; done
echo DONE_ALL >> rung1_driver.log
