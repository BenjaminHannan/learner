#!/bin/bash
# PROFILE=1 CPU dry run launcher: run_p.sh NAME [extra VAR=VALUE words ...]
#   frees /dev/shm memory first (the shard and web_build are not needed once data8a is READY; the cgroup counts tmpfs as memory) and, with FRESH_POOL=1, removes the pool so the job smoke builds it
#   BOXSH defaults to the generated new script; the log goes to ptcbox/NAME.log. Variables already in the environment (PROF_DRY_ARGS, PROF_JOB_TRAIN_EXTRA ...) win over the defaults below.
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
J=/dev/shm/ptcdry/J
rm -rf $J/work/data8a/shard $J/work/data8a/web_build
[ "${FRESH_POOL:-0}" = 1 ] && rm -rf $J/work/g8a
rm -rf $J/state/prof_emitted $J/state/maxh $J/state/prof_steps.txt $J/profraw $J/work/results/8aPTC3S-pc/profjob $J/work/results/8aPTC3S-pc/profrun
nm=$1; shift
export BOXSH=${BOXSH:-$B/gen/ptc3s_box.new.sh}
export PTC_DRY_EXTRA='["--device","cpu","--steps","2","--big-data","","--train-extra","--batch 16 --eval-max 16"]'
export PTC_DRY_EG=1
export PROF_JOB_STEPS=${PROF_JOB_STEPS:-2} PROF_JOB_TRAIN_EXTRA=${PROF_JOB_TRAIN_EXTRA:-'--log-every 1 --batch 16 --eval-max 16'}
export PROF_DRY_ARGS=${PROF_DRY_ARGS:-'--device cpu --tiny --rows 400 --batch 32 --updates 2 --warmup 1 --pad-updates 5 --pad-rounds-updates 2 --sweep-updates 1 --sweep-warmup 1 --bench-rounds 1 --curve-updates 6'}
cd $B && bash run_dry.sh $B/$nm.log PROFILE=1 MAXH=${MAXH_DRY:-3} END_SLEEP=20 TICK_EVERY=120 DPH=0.4 "$@"
