#!/bin/bash
# Reproduce the COVERAGE panel dimension. One line from anywhere:
#   bash /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/coverage/run_all.sh
# Pure python + numpy, read-only on the repo and data, no torch except pos_table.py (weights only), no GPU, no training. ~25 min total (shortcuts_lr.py is ~16 of them).
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/coverage
for s in chk_align coverage pairs roles family_compare family_distance length_curriculum wording_novelty shortcuts_chi repeat_stats leak_probe leak_text_only word_info ladder audit_eval audit_by_depth pos_table; do
  [ -f $s.py ] && python3 -B $s.py > logs_$s.txt 2>&1
done
# audit.py rerun on raw rows (5000 each, stdlib, ~10 min): see audit_rerun.txt for the saved output
python3 -B shortcuts_lr.py 30000 counts,tids,suffix,delex,words,chars,all logic_train   > lr_logic_train.log 2>&1 &
python3 -B shortcuts_lr.py 30000 counts,tids,suffix,delex,words,chars,all placebo_train > lr_placebo_train.log 2>&1 &
wait
python3 -B make_tables.py > /dev/null
