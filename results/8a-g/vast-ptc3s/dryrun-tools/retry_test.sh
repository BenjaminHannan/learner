#!/bin/bash
# the ptccheck retry block of the box script, cut out of the script and run with stubs: (a) fails once then passes, (b) fails twice
BOX=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s/ptc3s_box.sh
T=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox/retry_t
rm -rf $T; mkdir -p $T/out $T/state
start=$(grep -n '^for k in 1 2; do     # the check is deterministic' $BOX | cut -d: -f1)
end=$(awk -v s=$start 'NR>s && /^done$/ {print NR; exit}' $BOX)
sed -n "${start},${end}p" $BOX > $T/block.sh
echo "block lines $start-$end: $(wc -l < $T/block.sh)"
run_case() {   # fail_count
  FAILS=$1; CALLS=0
  J=$T; S=$T; OV=$T
  say() { echo "=== $*"; }
  die() { echo "DIE: $*"; return 7; }
  runp() { CALLS=$((CALLS + 1)); lf=$1
    if [ $CALLS -le $FAILS ]; then echo "some line" >> $lf; return 1; else echo "PTC CPU CHECK OK" >> $lf; return 0; fi; }
  : > $T/out/ptccheck.log
  . $T/block.sh
  echo "case fails=$FAILS: runp calls=$CALLS, last status $?"
}
( run_case 1 )
( run_case 2 )
