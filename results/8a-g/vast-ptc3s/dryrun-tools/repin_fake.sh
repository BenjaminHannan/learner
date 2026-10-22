#!/bin/bash
# offline Vast-kit create/tail/collect test of the re-pinned script on the re-pin PROFILE dry-run log; output into repin_out/
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
B=$P/ptcbox
K=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
O=$B/repin_out
mkdir -p $O
bash $B/run_fake_prof.sh $B/dry_p7_repin.log $K/ptc3s_box.sh > $O/fake_vast_prof_test_pin_ca542f77.txt 2>&1
cat $O/fake_vast_prof_test_pin_ca542f77.txt | cut -c1-260 | head -40
