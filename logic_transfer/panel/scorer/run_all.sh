#!/bin/sh
# Reproduce every number in findings.md (one thread each; checkpoints are loaded one at a time). About 25 minutes in total.
export PYTHONPATH=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/wt/lt
cd /tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/scorer || exit 1
D1B=/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/diag/D1b/checkpoint-3500.pt
PAR=/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt
python3 s1_controls.py                                                       # C1-C2: integrity + controls via the real evaluate()/analyze(), no checkpoint
python3 s2_positions.py                                                      # C3: option order vs label
python3 s4_depth_readout.py                                                  # C8: by_depth drops depth=None rows
python3 s3_recompute.py --tag d1b --ckpt $D1B --n 400 --bs-sweep --full     # C4-C6: determinism, batch size, full logic_gate vs saved score.json
python3 s6_independent_tally.py                                              # C4: stdlib re-tally of the saved predictions + z-scores
python3 s7_modes_all.py --ckpt $D1B --tag d1b                                # C6-C7: modes / pointer landing on all six files
python3 s3_recompute.py --tag parent --ckpt $PAR --n 400 --full              # parent (its full_vs_saved flag compares with D1b's file: ignore; see findings.md)
python3 s5_positive_control.py --ckpt $PAR --tag parent                      # C9: parent on curriculum word-answer families
python3 s8_saved_consistency.py                                              # C5: all 69 saved score.json files
python3 s9_train_window.py                                                   # C10: 64-token word window, train mode labels
