#!/bin/bash
# ADDENDUM-2 job list: the sealed dev ladders and fast path, plus the writes-off ladders, then the sleep draws.
# Idempotent (a finished job is skipped; an unfinished ladder resumes from its 32-batch checkpoint).
# Phase 1 runs $JOBS at a time (default 4), one thread each, longest first; phase 2 (draws) after every ladder.
# CPU, fp32, torch 2.14.0, no GPU. Run from the repo root. Needs runs/*/source.pt (sha256 in checkpoints-sha256.txt).
cd "$(dirname "$0")/.." || exit 1
A=artifacts/claude-patch-eq-20260928
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
bash scripts/claude_patch_eq_fetch_sources.sh || exit 1
job() {
  case $1 in
    patch-s*)  s=${1#patch-s};  [ -f $A/eq-runs/patch-s$s/adapt.json ] || python3 -B -u scripts/claude_patch_eq_ladder.py adapt --plugin claude_patch_eq_plugin --seed $s --init pre   --source $A/runs/patch-s$s   --out $A/eq-runs/patch-s$s ;;
    wsoff-s*)  s=${1#wsoff-s};  [ -f $A/eq-runs/writesoff-s$s/adapt.json ] || python3 -B -u scripts/claude_patch_eq_ladder.py adapt --plugin claude_patch_eq_writesoff --seed $s --init pre --source $A/runs/patch-s$s --out $A/eq-runs/writesoff-s$s ;;
    fresh-s*)  s=${1#fresh-s};  [ -f $A/eq-runs/fresh-s$s/adapt.json ] || python3 -B -u scripts/claude_patch_eq_ladder.py adapt --plugin claude_patch_eq_fresh  --seed $s --init fresh --source $A/runs/patch-s$s   --out $A/eq-runs/fresh-s$s ;;
    loopep-s*) s=${1#loopep-s}; [ -f $A/eq-runs/loopep-s$s/adapt.json ] || python3 -B -u scripts/claude_patch_eq_ladder.py adapt --plugin claude_fewex_net --seed $s --init pre --source $A/runs/loop_ep-s$s --out $A/eq-runs/loopep-s$s ;;
    fast-s*)   s=${1#fast-s};   [ -f $A/fastpath-dev-s$s.json ] || python3 -B -u scripts/claude_patch_eq_fastpath.py --seed $s --source $A/runs/patch-s$s --out $A/fastpath-dev-s$s.json ;;
    draw-*)    IFS=- read -r _ arm s k d <<< "$1"; [ -f $A/eq-runs/sleepdraws/$arm-s$s-k$k-d$d.json ] || python3 -B -u scripts/claude_patch_eq_add2_sleepdraws.py --arm $arm --seed $s --k $k --draw $d ;;
  esac
}
export -f job; export A
mkdir -p $A/eq-runs $A/logs
printf "%s\n" patch-s0 patch-s1 wsoff-s0 wsoff-s1 loopep-s0 loopep-s1 fresh-s0 fresh-s1 fast-s0 fast-s1 | \
  xargs -P ${JOBS:-4} -I{} bash -c 'job {} >> $A/logs/{}.log 2>&1; echo "{} exit $? $(date -u +%H:%M)"'
for f in patch-s0 patch-s1 loopep-s0 loopep-s1; do [ -f $A/eq-runs/${f%%-*}-s${f##*s}/adapt.json ] || { echo "ladder $f unfinished; not running draws"; exit 1; }; done
for arm in patch loop_ep; do for s in 0 1; do for k in 64 16384; do for d in 1 2; do echo draw-$arm-$s-$k-$d; done; done; done; done | \
  xargs -P ${JOBS:-4} -I{} bash -c 'job {} >> $A/logs/{}.log 2>&1; echo "{} exit $? $(date -u +%H:%M)"'
echo "queue done $(date -u +%H:%M)"
