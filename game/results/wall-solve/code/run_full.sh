#!/bin/bash
# Full Z7/Z8 run. Both seeds in parallel, 2 torch threads each. Resumable per day file (play_run.py skips existing play-d{d}.json.gz; re-running this script resumes).
# Usage: nohup setsid bash run_full.sh > /dev/null 2>&1 &
export PYTHONPATH=/home/user/benjaminhannan/learner
cd /home/user/benjaminhannan/learner
PY=/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad/venv/bin/python
Z=/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad/z78
for s in 200 201; do
  rs=$((s + 198))
  ( echo "start $(date -u +%FT%TZ)"; $PY $Z/code/play_run.py $s --threads 2 && $PY $Z/code/analyze.py $s && echo "ANALYZE_DONE $(date -u +%FT%TZ)" && $PY $Z/code/recheck_lp.py $s; echo "EXIT $? $(date -u +%FT%TZ)"; touch $Z/s$rs/DONE ) >> $Z/s$rs/run.log 2>&1 &
done
wait
