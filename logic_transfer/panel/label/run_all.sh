#!/bin/bash
# Reproduces every number in findings.md (about 10 minutes, one CPU, no torch, no GPU, no network).
#   bash /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/label/run_all.sh
set -e
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd "$(dirname "$0")"
python3 audit_rows.py          # per-row re-derivation -> perrow/*.jsonl  (reader A + solvers)
python3 analyze1.py            # coverage, agreement by file/label/level, balance          -> agg1.json
python3 analyze2.py            # documented vs textbook semantics confusion                 -> agg2.json
python3 analyze3.py            # stored depth vs independent minimum proof depth            -> agg3.json
python3 analyze4.py            # alternative readings (MT, textbook, DIST, PNEG)            -> agg4.json
python3 reader_b.py            # template-free second reader cross-check                    -> readerb.json
python3 leak.py                # duplicates / skeleton leakage                              -> leak.json
python3 train_cross.py         # logic_train vs placebo_train overlap                       -> train_cross.json
python3 holdout.py             # template hold-out check from text-inferred ids             -> holdout.json
python3 structure_overlap.py   # alpha-renamed logic-structure overlap                      -> structure.json
python3 analyze6.py            # lookup-only solver, polarity, sensitivity controls         -> agg6.json
python3 analyze7.py            # raw-vs-converted fidelity, option-order independence       -> agg7.json
python3 analyze8.py            # agreement by template id                                   -> agg8.json
python3 analyze9.py            # test_sampler composition                                   -> agg9.json
python3 examples.py > examples.txt
