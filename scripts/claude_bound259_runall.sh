#!/bin/bash
# Exp 259 registered driver. Run from the repo root. Stage "pre" = M2..M7
# (+ dev259 info run); stage "m1" = the corrtail258 panel on both arms.
set -u
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
SC="/usr/bin/python3 scripts/claude_bound259_score.py"
D=artifacts/claude-boundary259-20260922
O=$D/run
W=${WORK259:?set WORK259 to a scratch dir}
A=scripts/claude_loop259_agent.py
C=$D/loop259-config.json
BA=scripts/claude_loop252b_agent.py
BC=artifacts/claude-correct252b-20260922/loop252b-config.json
R252B=artifacts/claude-correct252b-20260922/run
V=artifacts/claude-verify-20260922/138k
mkdir -p $O
stage=${1:?pre or m1}
if [ "$stage" = pre ]; then
  uptime
  echo "== M2 dev252b (252b and 259, same session)"
  $PY scripts/claude_corr252_run.py --agent $BA --config $BC --cases artifacts/claude-correct252b-20260922/dev252b.jsonl --work $W/m2-252b --out $O/dev252b-252b.jsonl > $O/dev252b-252b.log 2>&1
  $PY scripts/claude_corr252_run.py --agent $A --config $C --cases artifacts/claude-correct252b-20260922/dev252b.jsonl --work $W/m2-259 --out $O/dev252b-259.jsonl > $O/dev252b-259.log 2>&1
  /usr/bin/python3 scripts/claude_corr252b_score.py dev artifacts/claude-correct252b-20260922/dev252b.jsonl $O/dev252b-259.jsonl $O/dev252b-252b.jsonl > $O/m2-check-252b-scorer.txt
  $SC m2 artifacts/claude-correct252b-20260922/dev252b.jsonl $O/dev252b-259.jsonl $O/dev252b-252b.jsonl > $O/m2-check.txt
  uptime
  echo "== M3 corrpanel252 (TEST-ONLY) on 259 vs 252b registered rows"
  $PY scripts/claude_corr252_run.py --agent $A --config $C --cases artifacts/claude-corrpanel252-20260922/panel.jsonl --work $W/m3-259 --out $O/panel252-259.jsonl > $O/panel252-259.log 2>&1
  $SC m3 artifacts/claude-corrpanel252-20260922/panel.jsonl $O/panel252-259.jsonl $R252B/panel-252b.jsonl > $O/m3-check.txt
  uptime
  echo "== M4 suites"
  $PY scripts/fable_suitediff218.py --agent $A --config $C --base-dir artifacts/claude-correct252-20260922/run/base138k-rows --out $O/sd-259 --only rt136,rt143,sessions152,bench > $O/sd-259.log 2>&1
  $SC suites $O/sd-259 $R252B/sd-252b > $O/m4-check.txt
  uptime
  echo "== M5 sleep smoke"
  $PY scripts/fable_sleepsmoke206.py --agent $A --config $C --root $W/smoke --report $O/smoke-259.json --label 259 --idle-seconds 5.0 > $O/smoke-259.log 2>&1
  $SC smoke $O/smoke-259.json $R252B/smoke-252b.json > $O/m5-check.txt
  uptime
  echo "== M6 restart dialogs"
  for f in v-dialogs v-supp; do
    $PY scripts/claude_merge138k_probe.py $A $C $W/m6-$f $V/$f.json $O/m6-259-$f.json > $O/m6-259-$f.log 2>&1
  done
  /usr/bin/python3 scripts/claude_corr252_m6check.py m6 $R252B/m6-252b-v-dialogs.json $O/m6-259-v-dialogs.json $R252B/m6-252b-v-supp.json $O/m6-259-v-supp.json > $O/m6-check.txt
  uptime
  echo "== M7 latency (252b, 259 alternating, 3 runs each)"
  for i in 1 2 3; do
    $PY scripts/claude_merge138k_latency.py $BA $BC $W/lat 2 $O/lat-252b-$i.json $V/v-dialogs.json $V/v-supp.json > /dev/null 2>&1
    $PY scripts/claude_merge138k_latency.py $A $C $W/lat 2 $O/lat-259-$i.json $V/v-dialogs.json $V/v-supp.json > /dev/null 2>&1
  done
  /usr/bin/python3 scripts/claude_corr252_m6check.py m5 $O/lat-252b-1.json $O/lat-252b-2.json $O/lat-252b-3.json -- $O/lat-259-1.json $O/lat-259-2.json $O/lat-259-3.json > $O/m7-check.txt
  echo "== dev259 (information, both arms)"
  $PY scripts/claude_corr252_run.py --agent $BA --config $BC --cases $D/dev259.jsonl --work $W/dev-252b --out $O/dev259-252b.jsonl > $O/dev259-252b.log 2>&1
  $PY scripts/claude_corr252_run.py --agent $A --config $C --cases $D/dev259.jsonl --work $W/dev-259 --out $O/dev259-259.jsonl > $O/dev259-259.log 2>&1
  $SC dev $D/dev259.jsonl $O/dev259-259.jsonl $O/dev259-252b.jsonl > $O/dev259-check.txt
  uptime
elif [ "$stage" = m1 ]; then
  P=artifacts/claude-corrtail258-20260922
  (shasum -a 256 -c $P/SEAL.sha256.txt) > $O/m1-panel-seal-check.txt 2>&1 || { echo "PANEL SEAL CHECK FAILED"; exit 4; }
  $SC schema $P > $O/m1-schema.txt; rc=$?
  if [ $rc -ne 0 ]; then echo "SCHEMA-MISMATCH: VOID"; exit 3; fi
  uptime
  $PY scripts/claude_corr252_run.py --agent $BA --config $BC --cases $P/panel.jsonl --work $W/m1-252b --out $O/panel258-252b.jsonl > $O/panel258-252b.log 2>&1
  $PY scripts/claude_corr252_run.py --agent $A --config $C --cases $P/panel.jsonl --work $W/m1-259 --out $O/panel258-259.jsonl > $O/panel258-259.log 2>&1
  $SC panel $P $O/panel258-259.jsonl $O/panel258-252b.jsonl > $O/m1-check.txt; echo "scorer exit $?"
fi
