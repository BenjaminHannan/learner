#!/bin/bash
# Reproduce the whole probe dimension.  One line:  bash /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe/reproduce.sh
# Inference only: 1 thread, one checkpoint loaded at a time (each run_*.py loads one and exits), ~50 min total on a shared CPU.
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/probe
mkdir -p res logs analysis
python3 build_conds.py && python3 build_extra.py && python3 build_extra2.py        # row sets (no model); asserts the train-index stream matches run.json's ex_idx_sha256
for t in D1b3500 parent D1b1500 L1000 P1000 D1b2500 D1b3000 D1b2000 D1b1000 D1b500 D1_1500; do python3 run_probe.py $t; done   # forward passes -> res/TAG.pkl
python3 item5.py D1b3500                                                           # training-slice loss through model.loss (real batch path)
for t in D1b3500 parent D1b1500 L1000 P1000; do python3 run_extra.py $t; python3 run_extra2.py $t; done    # whitespace / reorder / predicate-swap / fact-flip edits
python3 make_report.py                                                             # analysis/summary.json (all tables)
python3 lenonly.py                                                                 # prompt-length-only baseline (pure python)
