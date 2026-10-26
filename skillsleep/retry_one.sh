#!/usr/bin/env bash
# Retry one failed train task with the reviewer critique in the agent's system prompt. usage: retry_one.sh TASK_ID (env OUT SS ARGS FIX_TRIALS FIX_CONC FIX_TASK_MIN)
t=$1
export SKILLSLEEP_HINT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' $OUT/fix/hints.json $t)
bash $SS/t2.sh ss_fix_$t retail train $FIX_TRIALS $FIX_CONC $((FIX_TASK_MIN * 60)) --task-ids $t > $OUT/fix/log_$t.txt 2>&1
echo "retry task $t rc=$?"
