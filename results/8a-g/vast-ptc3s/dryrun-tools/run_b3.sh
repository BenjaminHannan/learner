#!/bin/bash
# PROFILE=1 PROF_PLAN=b3sweep CPU dry run launcher: run_b3.sh NAME [extra VAR=VALUE words ...]  (a thin layer over run_p.sh; tiny shapes for the harness and the AT job)
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
export PROF_DRY_ARGS=${PROF_DRY_ARGS:-'--device cpu --tiny --rows 400 --batch 32 --updates 2 --warmup 1 --pad-updates 5 --pad-rounds-updates 2 --sweep-updates 1 --sweep-warmup 1 --bench-rounds 1 --curve-updates 6 --accum-updates 2 --accum-warmup 1 --accum-rounds 1 --chunk 2'}
export PROF_AT_STEPS=${PROF_AT_STEPS:-6} PROF_AT_FROM_STEP=${PROF_AT_FROM_STEP:-2} PROF_AT_TRAIN_EXTRA=${PROF_AT_TRAIN_EXTRA:-'--log-every 1 --batch 32 --eval-max 16'}
export PROF_AT_MIN=${PROF_AT_MIN:-20}
# the new harness commit is not on GitHub yet: the git shim serves that one commit from the local repository (dry run only; every other fetch is real)
export PATH=$B/shimbin:$PATH SHIM_LOCAL_SHA=${SHIM_LOCAL_SHA:-1d728b99ef7180c567b285b07ede9aac7a46427a}
# a dry run of the AT stages must not find an AT folder of an earlier run
rm -rf /dev/shm/ptcdry/J/work/results/8aPTC3S-pc/at /dev/shm/ptcdry/J/state/at_stopped
nm=$1; shift
exec bash $B/run_p.sh $nm "$@" PROF_PLAN=b3sweep FAIL_SLEEP=20 PACE=2
