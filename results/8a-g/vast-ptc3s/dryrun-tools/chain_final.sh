#!/bin/bash
# the final CPU dry runs of the b3sweep script, one after the other (they share the dry box folder J). Logs: ptcbox/dry_f_{A,default,profdefault,T,F,S}.log
#  A            PROFILE=1 PROF_PLAN=b3sweep, happy path
#  default      PROFILE unset (the 24,000-update job path, tiny CPU shape as in the earlier full dry run)
#  profdefault  PROFILE=1, PROF_PLAN unset (the six-command PROFILE plan)
#  T            b3sweep: the sweep step fails (bad flag), AT cut by its timeout with data kept
#  F            b3sweep: at_g1 fails (bad flag), at_g2 hangs (replaced by sleep) and is cut by its timeout
#  S            b3sweep: every step skipped for lack of budget (PROF_MIN_LEFT huge)
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
cd $B || exit 1
echo "A start $(date -u +%T)"; bash run_b3.sh dry_f_A
echo "default start $(date -u +%T)"; env -u PROF_PLAN bash run_default.sh dry_f_default
echo "profdefault start $(date -u +%T)"
( export PATH=$B/shimbin:$PATH SHIM_LOCAL_SHA=1d728b99ef7180c567b285b07ede9aac7a46427a
  unset PROF_PLAN PROF_AT_STEPS PROF_AT_FROM_STEP PROF_AT_TRAIN_EXTRA PROF_AT_MIN PROF_DRY_FAIL PROF_DRY_HANG PROF_MIN_LEFT
  bash run_p.sh dry_f_profdefault FAIL_SLEEP=20 PACE=2 )
echo "T start $(date -u +%T)"; PROF_DRY_FAIL=h1_b3g2_accumsweep PROF_AT_STEPS=1000 PROF_AT_MIN=5 bash run_b3.sh dry_f_T
echo "F start $(date -u +%T)"; PROF_DRY_FAIL=at_g1 PROF_DRY_HANG=at_g2 PROF_AT_MIN=2 bash run_b3.sh dry_f_F
echo "S start $(date -u +%T)"; PROF_MIN_LEFT=99999 bash run_b3.sh dry_f_S
echo "chain done $(date -u +%T)"
