#!/bin/bash
cd /tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/gwl-code64 && export PYTHONPATH=. OMP_NUM_THREADS=1
/tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/venv/bin/python -m game.probe gen --out /tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/glprobe/run/data64k --train-views 64000 --reuse-heldout /tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/glprobe/run/data
echo "gen64k done $(date -u +%FT%TZ)" >> /tmp/claude-0/-home-user-learner/a35c4c05-cfae-5dd3-a5ce-480213b76700/scratchpad/glprobe/run/progress.log
