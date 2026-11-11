#!/bin/bash
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/pair
for c in "$@"; do
  echo "################ CASE $c"
  bash $P/stage_test.sh $P/new.sh $c 2>&1 | grep -E -v '^PROF-PAIR cmd|^cut:|^4096|^0 |events.jsonl:|^FAKE-JOB cwd' | cut -c1-330
done
