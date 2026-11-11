#!/bin/bash
# b3sweep checks that do not need the dry box: guard test, bash -n, shellcheck, regen check, diff against the previous script (pin ca542f77a9); output into b3_out/
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
B=$P/ptcbox
K=/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s
NEW=$K/ptc3s_box.sh
O=$B/b3_out
mkdir -p $O
cd /home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1 || exit 1
[ -f $B/ptc3s_box.pin_ca542f77.sh ] || git show 69a6eadd49:results/8a-g/vast-ptc3s/ptc3s_box.sh > $B/ptc3s_box.pin_ca542f77.sh
echo "previous script sha256 $(sha256sum $B/ptc3s_box.pin_ca542f77.sh | cut -c1-64)"
bash $B/gtest/run_guard.sh > $O/guard_test_b3sweep.txt 2>&1
diff $O/guard_test_b3sweep.txt $K/dryrun-logs/guard_test_pin_ca542f77.txt > $O/guard_diff.txt 2>&1 && echo "guard output identical to the one of the previous pin" >> $O/guard_test_b3sweep.txt
{ echo "sha256 $(sha256sum $NEW | cut -c1-64)  ptc3s_box.sh"; bash -n $NEW && echo "bash -n ptc3s_box.sh: ok"; bash $P/shck/run_new.sh $NEW; } > $O/bash_n_and_shellcheck_b3sweep.txt 2>&1
bash $B/regen.sh > $O/regen_check_b3sweep.txt 2>&1
diff $B/ptc3s_box.pin_ca542f77.sh $NEW > $O/script_diff_pin_ca542f77_vs_b3sweep.txt 2>&1
echo "done"
tail -4 $O/guard_test_b3sweep.txt
cat $O/bash_n_and_shellcheck_b3sweep.txt
cat $O/regen_check_b3sweep.txt | cut -c1-200
grep -c '^<' $O/script_diff_pin_ca542f77_vs_b3sweep.txt; grep -c '^>' $O/script_diff_pin_ca542f77_vs_b3sweep.txt
