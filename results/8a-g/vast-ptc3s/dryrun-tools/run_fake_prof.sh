#!/bin/bash
# offline Vast-kit test on a PROFILE dry-run log: run_fake_prof.sh LOG [SCRIPT]
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
K=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
echo "kit vast.py sha256: $(sha256sum $P/kit/vast.py | cut -c1-64)"
rm -rf $P/ptcbox/fake_prof_out
python3 $P/ptcbox/fake_vast_prof_test.py $P/kit/vast.py $K/vastptc.py "$1" $P/ptcbox/fake_prof_out ${2:-$K/ptc3s_box.sh} 2>&1 | cut -c1-260
