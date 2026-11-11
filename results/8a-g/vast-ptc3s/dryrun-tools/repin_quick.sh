#!/bin/bash
# re-pin checks that do not need the dry box: guard test, bash -n, shellcheck, regen check; output into ptcbox/repin_out/
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
B=$P/ptcbox
K=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
NEW=$K/ptc3s_box.sh
O=$B/repin_out
mkdir -p $O
bash $B/gtest/run_guard.sh > $O/guard_test_pin_ca542f77.txt 2>&1
diff $O/guard_test_pin_ca542f77.txt $K/dryrun-logs/guard_test_current_script.txt > $O/guard_diff.txt 2>&1 && echo "guard output identical to the one of the previous pin" >> $O/guard_test_pin_ca542f77.txt
{ echo "sha256 $(sha256sum $NEW | cut -c1-64)  ptc3s_box.sh"; bash -n $NEW && echo "bash -n ptc3s_box.sh: ok"; bash $P/shck/run_new.sh $NEW; } > $O/bash_n_and_shellcheck_pin_ca542f77.txt 2>&1
bash $B/regen.sh > $O/regen_check_pin_ca542f77.txt 2>&1
diff $B/ptc3s_box.pin6a870a76.sh $NEW > $O/script_diff_pin_6a870a76_vs_ca542f77.txt 2>&1
echo "done"
cat $O/guard_test_pin_ca542f77.txt | tail -4
cat $O/bash_n_and_shellcheck_pin_ca542f77.txt
cat $O/script_diff_pin_6a870a76_vs_ca542f77.txt | cut -c1-120
