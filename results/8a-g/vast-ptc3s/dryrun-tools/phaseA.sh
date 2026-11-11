#!/bin/bash
# phase A of the rebuilt CPU dry-run workspace: the committed (frozen, default-path) script from scratch up to and including the skills stage (setup, code, gemma, data, skills)
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
export PTC_DRY_EXTRA='["--device","cpu","--steps","2","--big-data","","--train-extra","--batch 16 --eval-max 16"]'
export PTC_DRY_EG=1 STOP_AFTER=skills
cd $B && bash run_dry.sh $B/dry_phaseA.log MAXH=0 END_SLEEP=20 PACE=2 TICK_EVERY=120
