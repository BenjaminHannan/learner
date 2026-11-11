#!/bin/bash
# 8b 6-seed confirm (design/8b-gemma-growth-2026-10-08.md section 3): seeds 402-405 for ONE arm at both rungs, plus the 8a LLM-10M seed 404
# that the 8a cost cap cut. Run only after the 2-seed screen says "go" for that arm AND Ben has OK'd the spend (about $25-30; the 8b total would pass $40).
#   bash g8b/launch_confirm.sh EGA36|EGE36 OFFER_ID...   (9 offer ids: 4 x 3M, 4 x 10M, 1 for LLM-10M s404; cheapest RTX 5090s with fast CPUs)
set -eu
ARM=$1; shift
OVL=${OVL:-8084ebaecea234c0434cf705f397e3522332e0ee}
case $ARM in EGA36) B2X=eg_embed:true,gen_ar:true ;; EGE36) B2X=eg_embed:true ;; *) echo "arm?"; exit 1 ;; esac
[ $# -eq 9 ] || { echo "need 9 offer ids"; exit 1; }
cd "$(dirname "$0")/.."
i=0
for rung in 3M 10M; do
  for seed in 402 403 404 405; do
    i=$((i + 1)); off=${!i}
    if [ $rung = 10M ]; then extra="ACCUM=2 MAXH=9.5 JOBH=9"; else extra="MAXH=6 JOBH=5.5"; fi
    python3 g8b/vast8b.py create --offer $off --label 8b-$ARM-$rung-s$seed --env "OVL=$OVL RUNG=$rung SEED=$seed ARMS=B2 B2X=$B2X $extra"
  done
done
# the plain LLM at 10M, seed 404, exactly as 8a ran it (no Gemma, no overlay change touches plain_lm): EG=0 skips the Gemma download
python3 g8b/vast8b.py create --offer ${9} --label 8b-LLM-10M-s404 --env "OVL=$OVL RUNG=10M SEED=404 ARMS=LLM EG=0 TFVER=5.17.0 MAXH=4 JOBH=3.5"
