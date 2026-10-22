#!/bin/bash
# quick refusal tests of PROF_PLAN (they stop in the first seconds of the script, before any download)
# usage: quick_tests_b3.sh SCRIPT
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
S=${1:-$B/gen/ptc3s_box.new.sh}
export PATH=$B/dry/venv/bin:$PATH
T=/dev/shm/ptcdry/Jq
t() {   # label, expected text, then VAR=VALUE words for the script
  label=$1; want=$2; shift 2
  rm -rf $T
  out=$(env "$@" J=$T FAIL_SLEEP=1 END_SLEEP=1 bash -c "$(cat $S)" cio 2>&1 | grep -E "CIO-FAIL|PROF MODE|PROF PLAN|PROF START|STAGE (code|prof)|RBEGIN" | cut -c1-260)
  echo "--- $label"; echo "$out" | sed 's/^/    /'
  if echo "$out" | grep -q -- "$want"; then echo "    => as expected (found: $want)"; else echo "    => NOT AS EXPECTED (wanted: $want)"; fi
}
t "PROF_PLAN=bogus is refused" "PROF_PLAN must be default or b3sweep" PROFILE=1 PTC_DRY=1 PROF_PLAN=bogus
t "PROF_PLAN=b3sweep without PROFILE=1 is refused" "PROF_PLAN=b3sweep needs PROFILE=1" PTC_DRY=1 PROF_PLAN=b3sweep
t "PROF_PLAN=b3sweep with PROFILE=0 is refused" "PROF_PLAN=b3sweep needs PROFILE=1" PROFILE=0 PTC_DRY=1 PROF_PLAN=b3sweep
t "PROFILE=1 PROF_PLAN=b3sweep: the PROF MODE line names the plan (then stops at the PROF_DRY_ARGS-without-PTC_DRY refusal)" "PROF_PLAN=b3sweep" PROFILE=1 PROF_PLAN=b3sweep PTC_DRY=0 PROF_DRY_ARGS=x
t "PROFILE=1 PROF_PLAN=default: the PROF MODE line is the old one (no plan text)" "PROF_COMPILE=0 end_sleep=1)" PROFILE=1 PROF_PLAN=default PTC_DRY=0 PROF_DRY_ARGS=x
t "PROFILE=1 with PROF_PLAN unset: the PROF MODE line is the old one (no plan text)" "PROF_COMPILE=0 end_sleep=1)" PROFILE=1 PTC_DRY=0 PROF_DRY_ARGS=x
rm -rf $T
