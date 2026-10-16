#!/bin/bash
# the default path (PROFILE unset) of the committed script, with the same parameters as the earlier full dry run of the frozen script (dry_final4.log):
#   MAXH=3 END_SLEEP=20 PACE=2 TICK_EVERY=120 DPH=0.38 PROJ_CAP_USD=4, PTC_DRY_EG=1, PTC_DRY_EXTRA as in DRYRUN.md section 0
# usage: run_default.sh NAME
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
J=/dev/shm/ptcdry/J
rm -rf $J/work/data8a/shard $J/work/data8a/web_build $J/state/maxh $J/state/prof_emitted $J/profraw $J/work/results/8aPTC3S-pc/profjob $J/work/results/8aPTC3S-pc/profrun $J/work/results/8aPTC3S-pc/8aPTC3S-3M-s400
export PTC_DRY_EXTRA='["--device","cpu","--steps","2","--big-data","","--train-extra","--batch 16 --eval-max 16"]'
export PTC_DRY_EG=1
unset PROFILE PROF_DRY_ARGS PROF_DRY_FAIL PROF_DRY_HANG PROF_JOB_STEPS PROF_JOB_TRAIN_EXTRA
cd $B && bash run_dry.sh $B/$1.log MAXH=3 END_SLEEP=20 PACE=2 TICK_EVERY=120 DPH=0.38 PROJ_CAP_USD=4
