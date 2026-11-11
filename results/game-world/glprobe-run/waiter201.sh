#!/bin/bash
R=/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/glprobe/run
for i in $(seq 1 115); do
  [ -f $R/DONE201 ] && { echo "DONE201"; tail -3 $R/progress.log; exit 0; }
  if ! pgrep -f "pipeline3.sh" >/dev/null; then echo "pipeline3 not running"; tail -3 $R/progress.log; exit 0; fi
  sleep 60
done
echo "cap reached"; tail -2 $R/progress.log
