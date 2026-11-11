#!/bin/bash
# shellcheck at every severity on a given script: run_new.sh SCRIPT
SC=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/shck
BOX=$1
$SC/bin/shellcheck --version | sed -n 1,2p
for s in error warning info style; do
  $SC/bin/shellcheck -s bash -S $s $BOX > $SC/new_$s.txt 2>&1
  echo "severity>=$s: exit $? ; findings: $(grep -c '^In ' $SC/new_$s.txt) ; codes: $(grep -o 'SC[0-9]*' $SC/new_$s.txt | sort | uniq -c | tr '\n' ' ')"
done
