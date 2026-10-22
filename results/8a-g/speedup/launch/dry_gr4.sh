#!/bin/bash
# dry_gr4.sh LOGFILE PART [VAR=VALUE ...]: the CPU dry run of gpu_run_4_box.sh (PREREG-launch-defer.md section 9), run the way vast.py embeds a box script (bash -c "<exports>\n<script>" cio).
# Every stage is the real one (setup, code fetch by sha with every pin checked, gemma download + check, data, skills, pool-building job smoke) except that the job smoke and the harness runs
# get tiny CPU shapes and counts through the box script's own dry-run hooks (PTC_DRY, PTC_DRY_EXTRA, PROF_JOB_*, PROF_DRY_ARGS). PART = full or rep. Never used on Vast.
LOG=$1; PART=$2; shift 2
HERE=$(cd "$(dirname "$0")" && pwd)
BOXSH=${BOXSH:-$HERE/gpu_run_4_box.sh}
export PATH=${DRY_VENV:-/home/user/venv}/bin:$PATH
export PTC_DRY=1 PTC_DRY_EG=1 J=${DRY_J:-/home/user/gr4dry/J}
export PTC_DRY_EXTRA='["--device","cpu","--steps","2","--big-data","","--train-extra","--batch 16 --eval-max 16"]'
export PROF_JOB_STEPS=2 PROF_JOB_TRAIN_EXTRA='--log-every 1 --batch 16 --eval-max 16'
export PROF_DRY_ARGS=${PROF_DRY_ARGS:-'--device cpu --tiny --rows 400 --batch 16 --updates 1 --warmup 1 --ab-warmup 1 --ab-updates 4 --chunk 2 --curve-updates 6'}
rm -rf $J/state/prof_emitted $J/state/maxh $J/state/prof_steps.txt $J/profraw $J/work/results/8aPTC3S-pc/profjob $J/work/results/8aPTC3S-pc/profrun
exp="export MAXPAR=5 QSUB= PROFILE=1 PROF_PLAN=gr4 GR4_PART=$PART DPH=0.40 MAXH=${MAXH_DRY:-3} END_SLEEP=5 FAIL_SLEEP=5 TICK_EVERY=120 PACE=2 $*"
bash -c "$exp
$(cat $BOXSH)" cio > $LOG 2>&1
echo "dry_gr4 exit $?" >> $LOG
