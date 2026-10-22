#!/bin/bash
# offline Vast-kit create / tail / collect test on a b3sweep dry-run log: fake_b3.sh LOG [OUTFILE]
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
B=$P/ptcbox
K=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
export FAKE_ENV="PROFILE=1 PROF_PLAN=b3sweep MAXH=3 DPH=0.46 END_SLEEP=300 FAIL_SLEEP=300"
export FAKE_EXPECT="b3g2_accumsweep.json,b3g2_accumsweep.md,b3g2_accumcmp.json,b3g2_accumcmp.md,at_g1.json,at_g2.json,at_setup.md,prof_status.txt,at_g1.log.tail,at_g2.log.tail,h1_b3g2_accumsweep.log.tail,h2_b3g2_accumcmp.log.tail,prof_steps.txt,stages.txt"
export FAKE_GREP="prof_status.txt:plan=b3sweep;prof_status.txt:at_g2_accum=8;at_setup.md:6e72a5fae514a343c217c4d95cde37bc3b587c8e"
echo "kit vast.py sha256: $(sha256sum $P/kit/vast.py | cut -c1-64)"
rm -rf $B/fake_b3_out
python3 $B/fake_vast_prof_test.py $P/kit/vast.py $K/vastptc.py "$1" $B/fake_b3_out $K/ptc3s_box.sh 2>&1 | cut -c1-260
