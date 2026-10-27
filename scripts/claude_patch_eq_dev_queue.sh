#!/bin/bash
# Dev ladders and fast path, 4 at a time, longest first; one thread each. Idempotent: safe to relaunch
# after a container restart (finished jobs are skipped, unfinished ones resume from their checkpoints).
cd /home/user/learner
A=artifacts/claude-patch-eq-20260928
job() {
  case $1 in
    patch-s*)  s=${1#patch-s};  [ -f $A/eq-runs/patch-s$s/adapt.json ] || python3 -B -u scripts/claude_patch_eq_ladder.py adapt --plugin claude_patch_eq_plugin --seed $s --init pre   --source $A/runs/patch-s$s   --out $A/eq-runs/patch-s$s ;;
    fresh-s*)  s=${1#fresh-s};  [ -f $A/eq-runs/fresh-s$s/adapt.json ] || python3 -B -u scripts/claude_patch_eq_ladder.py adapt --plugin claude_patch_eq_fresh  --seed $s --init fresh --source $A/runs/patch-s$s   --out $A/eq-runs/fresh-s$s ;;
    loopep-s*) s=${1#loopep-s}; [ -f $A/eq-runs/loopep-s$s/adapt.json ] || python3 -B -u scripts/claude_patch_eq_ladder.py adapt --plugin claude_fewex_net --seed $s --init pre --source $A/runs/loop_ep-s$s --out $A/eq-runs/loopep-s$s ;;
    fast-s*)   s=${1#fast-s};   [ -f $A/fastpath-dev-s$s.json ] || python3 -B -u scripts/claude_patch_eq_fastpath.py --seed $s --source $A/runs/patch-s$s --out $A/fastpath-dev-s$s.json ;;
  esac
}
export -f job; export A
mkdir -p $A/eq-runs $A/logs
printf "%s\n" patch-s0 patch-s1 fresh-s0 fresh-s1 loopep-s0 loopep-s1 fast-s0 fast-s1 | \
  xargs -P 4 -I{} bash -c 'job {} >> $A/logs/{}.log 2>&1; echo "{} exit $? $(date -u +%H:%M)"'
