#!/bin/bash
# the earlier offline Vast-kit tests (create/search/collect/collectck, and the two defects of the unpatched kit) on the DEFAULT-path dry-run log of the new script: run_fake_default.sh LOG
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
K=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
rm -rf $P/ptcbox/fake_out $P/ptcbox/kit_bug_out
echo "##### fake_vast_test.py (vastptc.py + the kit's vast.py, urllib replaced)"
timeout 150 python3 $P/ptcbox/fake_vast_test.py $P/kit/vast.py $K/vastptc.py "$1" $P/ptcbox/fake_out 2>&1
echo "##### kit_bug_test.py (the unpatched kit on the same log)"
timeout 100 python3 $P/ptcbox/kit_bug_test.py $P/kit/vast.py "$1" $P/ptcbox/kit_bug_out 2>&1
