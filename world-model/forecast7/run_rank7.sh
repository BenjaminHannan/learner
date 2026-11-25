#!/bin/zsh
# Driver for Rank 7 dev seeds 42 and 43 (forecast7/PLAN-AMENDMENT.md).
# Trains ONE 2-frame model per seed (5,000 steps) and scores the exact same weights
# under BOTH pinned rollout modes:
#   1. reencode (reencode_res) -> verdict of record (score_dev.json & score_dev_reencode.json)
#   2. plain                   -> one-knob isolation (score_dev_plain.json)
# Sealed exam is NOT included — launch manually once only after a 2-seed dev PASS.
set -u
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm7 || exit 2
PY=~/learner-ops/m3-torch/.venv/bin/python

power_ok() {
  b=$(pmset -g batt)
  echo "$b" | grep -q "AC Power" && return 0
  pct=$(echo "$b" | grep -Eo "[0-9]+%" | head -1 | tr -d %)
  [ "${pct:-0}" -ge 35 ]
}

wait_power() {
  local label=$1
  local n=0
  until power_ok; do
    [ $n -eq 0 ] && echo "waiting for power before $label $(date)" >> rank7_driver.log
    n=$((n + 1))
    [ $n -gt 960 ] && { echo "DONE_NOPOWER label=$label $(date)" >> rank7_driver.log; exit 1; }
    sleep 30
  done
}

run_seed() {
  local seed=$1
  wait_power "seed_${seed}_train_reencode"
  ./withlock.sh run_r7_s${seed}_reencode.log $PY -B -u train_v7.py \
    --size R7conv --n-history 2 --rollout reencode --device mps --steps 5000 --batch 64 \
    --lr 3e-4 --wd 1e-4 --w-lat 0.05 --seed "$seed" --max-minutes 18.0 \
    --save-forecasts \
    --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
    --out run_r7_s${seed}
  rc=$?
  echo "seed $seed train+reencode rc=$rc $(date)" >> rank7_driver.log
  [ $rc -eq 0 ] || exit $rc

  wait_power "seed_${seed}_eval_plain"
  ./withlock.sh run_r7_s${seed}_plain.log $PY -B -u train_v7.py \
    --size R7conv --n-history 2 --rollout plain --device mps \
    --eval-only run_r7_s${seed}/model.pt --save-forecasts \
    --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
    --out run_r7_s${seed}
  rc=$?
  echo "seed $seed eval_plain rc=$rc $(date)" >> rank7_driver.log
  [ $rc -eq 0 ] || exit $rc
}

df -g  | awk 'NR==2{ if ($4<12) {print "DISK LOW " $4 "G"; exit 1} }' >> rank7_driver.log || { echo DONE_DISK >> rank7_driver.log; exit 1; }

run_seed 42
run_seed 43

$PY -B - <<'PYEOF' >> rank7_driver.log 2>&1 || exit $?
import json
s42 = json.load(open("run_r7_s42/score_dev_reencode.json"))
s43 = json.load(open("run_r7_s43/score_dev_reencode.json"))
p42 = json.load(open("run_r7_s42/score_dev_plain.json"))
p43 = json.load(open("run_r7_s43/score_dev_plain.json"))
v42, v43 = s42["rank7_verdict"], s43["rank7_verdict"]
k1_42, k1_43 = s42["k1"]["E_over_B"], s43["k1"]["E_over_B"]
k3_42, k3_43 = s42["k3"]["E_over_B"], s43["k3"]["E_over_B"]
k5_42, k5_43 = s42["k5"]["E_over_B"], s43["k5"]["E_over_B"]
if v42 == "PASS" and v43 == "PASS":
    agg = "PASS"
    winner = "s42" if (k1_42, k5_42, 42) <= (k1_43, k5_43, 43) else "s43"
elif v42 in ("PASS", "PARTIAL") and v43 in ("PASS", "PARTIAL"):
    agg = "PARTIAL"
    winner = "NONE"
else:
    agg = "FAIL"
    winner = "NONE"
print(
    f"RANK7_DEV_SUMMARY(reencode) s42={v42} (k1={k1_42:.4f}, k3={k3_42:.4f}, k5={k5_42:.4f}, std_ok={s42['std_ok']}) "
    f"s43={v43} (k1={k1_43:.4f}, k3={k3_43:.4f}, k5={k5_43:.4f}, std_ok={s43['std_ok']}) "
    f"agg={agg} sealed_candidate={winner}"
)
print(
    f"RANK7_DEV_ISOLATION(plain)  s42={p42['rank7_verdict']} (k1={p42['k1']['E_over_B']:.4f}, k3={p42['k3']['E_over_B']:.4f}, k5={p42['k5']['E_over_B']:.4f}, std_ok={p42['std_ok']}) "
    f"s43={p43['rank7_verdict']} (k1={p43['k1']['E_over_B']:.4f}, k3={p43['k3']['E_over_B']:.4f}, k5={p43['k5']['E_over_B']:.4f}, std_ok={p43['std_ok']})"
)
print(
    f"RANK7_STRIKE(reencode) s42={s42['strike_class']} reasons={s42['strike_reasons']} "
    f"s43={s43['strike_class']} reasons={s43['strike_reasons']}"
)
print(
    f"RANK7_STRIKE(plain)    s42={p42['strike_class']} reasons={p42['strike_reasons']} "
    f"s43={p43['strike_class']} reasons={p43['strike_reasons']}"
)
PYEOF
echo "DONE_ALL $(date)" >> rank7_driver.log
