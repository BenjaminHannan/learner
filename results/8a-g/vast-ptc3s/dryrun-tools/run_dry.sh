#!/bin/bash
# dry-run launcher: runs ptc3s_box.sh the way vast.py embeds it (bash -c "<exports>\n<script>" cio) on the CPU box
# usage: [BOXSH=path/to/script] run_dry.sh LOGFILE [VAR=VALUE ...]      (BOXSH defaults to the committed script; variables with spaces go in the environment, not in the VAR=VALUE words)
S=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
BOXSH=${BOXSH:-/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s/ptc3s_box.sh}
LOG=$1; shift
export PATH=$S/dry/venv/bin:$PATH
export PTC_DRY=1 J=/dev/shm/ptcdry/J
exp="export MAXPAR=5 QSUB= $*"
bash -c "$exp
$(cat $BOXSH)" cio > $LOG 2>&1
echo "run_dry exit $?" >> $LOG
