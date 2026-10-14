#!/bin/bash
# the variable block of the box script (defaults) evaluated for each plan: prints the values; the default plan must give the previous script's values
# (75 45 25 300 '--log-every 50', MAXH 2 / END 300 / FAIL 600 with PROFILE=1; 6 / 600 / 1800 without)
S=${1:-/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s/ptc3s_box.sh}
blk=$(awk '/^PROFILE=\$\{PROFILE:-0\}/{on=1} on{print} /^PSTEP_MIN=/{exit}' $S)
show() {
  env -i PATH=$PATH "$@" bash -c "$blk"'
echo "PROFILE=$PROFILE PROF_PLAN=$PROF_PLAN MAXH=$MAXH END_SLEEP=$END_SLEEP FAIL_SLEEP=$FAIL_SLEEP PROF_MAXMIN=$PROF_MAXMIN PROF_JOB_MIN=$PROF_JOB_MIN PROF_STEP_MIN=$PROF_STEP_MIN PROF_JOB_STEPS=$PROF_JOB_STEPS PROF_JOB_TRAIN_EXTRA=[$PROF_JOB_TRAIN_EXTRA] PROF_SWEEP_MIN=$PROF_SWEEP_MIN PROF_CMP_MIN=$PROF_CMP_MIN PROF_AT_MIN=$PROF_AT_MIN PROF_AT_STEPS=$PROF_AT_STEPS PROF_AT_FROM_STEP=$PROF_AT_FROM_STEP PROF_AT_TRAIN_EXTRA=[$PROF_AT_TRAIN_EXTRA]"'
}
echo "default job (PROFILE unset):";            show
echo "PROFILE=1, PROF_PLAN unset:";             show PROFILE=1
echo "PROFILE=1, PROF_PLAN=default:";           show PROFILE=1 PROF_PLAN=default
echo "PROFILE=1, PROF_PLAN=b3sweep:";           show PROFILE=1 PROF_PLAN=b3sweep
echo "PROFILE=1, b3sweep, explicit overrides:"; show PROFILE=1 PROF_PLAN=b3sweep MAXH=4 PROF_MAXMIN=100 PROF_JOB_STEPS=60 PROF_AT_MIN=30 "PROF_JOB_TRAIN_EXTRA=--log-every 5"
echo "PROFILE=1, PROF_PLAN=default, explicit overrides:"; show PROFILE=1 MAXH=4 PROF_MAXMIN=100 PROF_JOB_STEPS=60
echo "PROFILE=1, PROF_PLAN=b3ab:";              show PROFILE=1 PROF_PLAN=b3ab
echo "PROFILE=1, b3ab, explicit overrides:";    show PROFILE=1 PROF_PLAN=b3ab MAXH=4 PROF_MAXMIN=100 PROF_JOB_STEPS=60 "PROF_JOB_TRAIN_EXTRA=--log-every 5"
