#!/bin/bash
# Exp 252c driver. Run from anywhere; cds to the repo root.
#   stage pre : M2 dev252b, M3 dev258 + dev259, M5 suites, M6 sleep smoke,
#               M7 restart dialogs, M8 latency
#   stage m4  : corrpanel252 (TEST-ONLY) once on 252c
#   stage m1  : corrtail258 once on 252c
# OUT252C = output dir (default artifacts/claude-merge252c-20260922/run);
# WORK252C = scratch work dir (required). Every scorer runs under uv
# Python 3.12 (never bare python3 on this Mac).
set -u
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PY="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
SPY="uv run --offline --no-project --python 3.12 python -B"
D=artifacts/claude-merge252c-20260922
O=${OUT252C:-$D/run}
W=${WORK252C:?set WORK252C to a scratch dir}
A=scripts/claude_loop252c_agent.py
C=$D/loop252c-config.json
BA=scripts/claude_loop252b_agent.py
BC=artifacts/claude-correct252b-20260922/loop252b-config.json
A8=scripts/claude_loop258_agent.py
C8=artifacts/claude-comment258-20260922/loop258-config.json
A9=scripts/claude_loop259_agent.py
C9=artifacts/claude-boundary259-20260922/loop259-config.json
R2B=artifacts/claude-correct252b-20260922/run
R258=artifacts/claude-comment258-20260922/run
R259=artifacts/claude-boundary259-20260922/run
D2=artifacts/claude-correct252b-20260922/dev252b.jsonl
D8=artifacts/claude-comment258-20260922/dev258.jsonl
D9=artifacts/claude-boundary259-20260922/dev259.jsonl
V=artifacts/claude-verify-20260922/138k
SC=scripts/claude_merge252c_score.py
mkdir -p $O $W
gate() {
  uptime; df -g / | tail -1
  while :; do
    l=$(uptime | sed -E 's/.*load averages?: *([0-9.]+).*/\1/')
    awk -v l="$l" 'BEGIN{exit !(l>60)}' || break
    echo "load $l > 60, waiting"; sleep 30
  done
  f=$(df -g / | tail -1 | awk '{print $4}')
  if [ "$f" -lt 3 ]; then echo "free disk ${f} GB < 3: STOP"; exit 5; fi
}
run() { # agent config cases name
  $PY scripts/claude_corr252_run.py --agent $1 --config $2 --cases $3 \
    --work $W/$4 --out $O/$4.jsonl > $O/$4.log 2>&1
  echo "$4 exit $?" >> $O/runs.log
  rm -rf $W/$4
}
stage=${1:?pre, m4 or m1}
if [ "$stage" = pre ]; then
  echo "== M2 dev252b + M3 dev258/dev259 (252c, 252b, and the other arms, one session)"; gate
  run $A $C $D2 dev252b-252c & run $BA $BC $D2 dev252b-252b &
  run $A $C $D8 dev258-252c & run $A $C $D9 dev259-252c & wait
  run $A9 $C9 $D8 dev258-259 & run $A8 $C8 $D9 dev259-258 & wait
  $SPY $SC m2 $D2 $O/dev252b-252c.jsonl $O/dev252b-252b.jsonl $R258/dev252b-258.jsonl $R259/dev252b-259.jsonl > $O/m2-check.txt
  $SPY scripts/claude_corr252b_score.py dev $D2 $O/dev252b-252c.jsonl $O/dev252b-252b.jsonl > $O/m2-check-252b-scorer.txt
  $SPY $SC m3 $D8 $O/dev258-252c.jsonl $R258/dev258-258.jsonl $D/pred-m3-dev258.jsonl $O/dev258-259.jsonl > $O/m3-dev258-check.txt
  $SPY $SC m3 $D9 $O/dev259-252c.jsonl $R259/dev259-259.jsonl $D/pred-m3-dev259.jsonl $O/dev259-258.jsonl > $O/m3-dev259-check.txt
  echo "== M5 suites"; gate
  $PY scripts/fable_suitediff218.py --agent $A --config $C --base-dir artifacts/claude-correct252-20260922/run/base138k-rows --out $O/sd-252c --only rt136,rt143,sessions152,bench > $O/sd-252c.log 2>&1
  $SPY scripts/claude_bound259_score.py suites $O/sd-252c $R2B/sd-252b > $O/m5-check.txt
  $SPY scripts/claude_comment258_score.py suites $R2B/sd-252b $O/sd-252c > $O/m5-check-258scorer.txt
  echo "== M6 sleep smoke"; gate
  $PY scripts/fable_sleepsmoke206.py --agent $A --config $C --root $W/smoke --report $O/smoke-252c.json --label 252c --idle-seconds 5.0 > $O/smoke-252c.log 2>&1
  $SPY scripts/claude_bound259_score.py smoke $O/smoke-252c.json $R2B/smoke-252b.json > $O/m6-check.txt
  rm -rf $W/smoke
  echo "== M7 restart dialogs"; gate
  for f in v-dialogs v-supp; do
    $PY scripts/claude_merge138k_probe.py $A $C $W/m7-$f $V/$f.json $O/m7-252c-$f.json > $O/m7-252c-$f.log 2>&1
    rm -rf $W/m7-$f
  done
  $SPY scripts/claude_corr252_m6check.py m6 $R2B/m6-252b-v-dialogs.json $O/m7-252c-v-dialogs.json $R2B/m6-252b-v-supp.json $O/m7-252c-v-supp.json > $O/m7-check.txt
  echo "== M8 latency (252b, 252c alternating, 3 runs each, 2 reps)"; gate
  for i in 1 2 3; do
    $PY scripts/claude_merge138k_latency.py $BA $BC $W/lb$i 2 $O/lat-252b-$i.json $V/v-dialogs.json $V/v-supp.json >> $O/lat.log 2>&1
    $PY scripts/claude_merge138k_latency.py $A $C $W/lc$i 2 $O/lat-252c-$i.json $V/v-dialogs.json $V/v-supp.json >> $O/lat.log 2>&1
    rm -rf $W/lb$i $W/lc$i
  done
  $SPY scripts/claude_corr252_m6check.py m5 $O/lat-252b-1.json $O/lat-252b-2.json $O/lat-252b-3.json -- $O/lat-252c-1.json $O/lat-252c-2.json $O/lat-252c-3.json > $O/m8-check.txt
  echo "== pre done"; gate
elif [ "$stage" = m4 ]; then
  echo "== M4 corrpanel252 (TEST-ONLY), once"; gate
  run $A $C artifacts/claude-corrpanel252-20260922/panel.jsonl corrpanel252-252c
  $SPY $SC m4 artifacts/claude-corrpanel252-20260922 $O/corrpanel252-252c.jsonl $R2B/panel-252b.jsonl $R258/corrpanel252-258.jsonl $R259/panel252-259.jsonl > $O/m4-check.txt
  echo "scorer exit $?" >> $O/m4-check.txt
elif [ "$stage" = m1 ]; then
  P=artifacts/claude-corrtail258-20260922
  (shasum -a 256 -c $P/SEAL.sha256.txt) > $O/m1-panel-seal-check.txt 2>&1 || { echo "PANEL SEAL CHECK FAILED"; exit 4; }
  echo "== M1 corrtail258, once"; gate
  run $A $C $P/panel.jsonl corrtail258-252c
  $SPY $SC m1 $P $O/corrtail258-252c.jsonl $R258/corrtail258-252b.jsonl $R258/corrtail258-258.jsonl $R259/panel258-259.jsonl > $O/m1-check.txt
  echo "scorer exit $?" >> $O/m1-check.txt
fi
