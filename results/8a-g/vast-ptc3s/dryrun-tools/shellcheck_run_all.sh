#!/bin/bash
# shellcheck at every severity, and the three other scripts of the dry run harness are not checked (only the deliverable)
SC=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/shck
BOX=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s/ptc3s_box.sh
$SC/bin/shellcheck --version | sed -n 1,2p
for s in error warning info style; do
  $SC/bin/shellcheck -s bash -S $s $BOX > $SC/out_$s.txt 2>&1
  echo "severity>=$s: exit $? ; findings: $(grep -c '^In ' $SC/out_$s.txt) ; codes: $(grep -o 'SC[0-9]*' $SC/out_$s.txt | sort | uniq -c | tr '\n' ' ')"
done
