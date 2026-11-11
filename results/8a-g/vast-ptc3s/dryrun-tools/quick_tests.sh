#!/bin/bash
# quick refusal tests of the PROFILE guards (they all stop in the first seconds of the script, before any download)
# usage: quick_tests.sh SCRIPT
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
S=${1:-$B/gen/ptc3s_box.new.sh}
export PATH=$B/dry/venv/bin:$PATH
T=/dev/shm/ptcdry/Jq
mkdir -p $B/fakebin && printf '#!/bin/bash\n[ "$1" = "-L" ] && echo "GPU 0: Fake RTX 4090 (UUID: GPU-0)"\nexit 0\n' > $B/fakebin/nvidia-smi && chmod +x $B/fakebin/nvidia-smi
t() {   # label, then VAR=VALUE words for the script, then expected text
  label=$1; want=$2; shift 2
  rm -rf $T
  out=$(env "$@" J=$T FAIL_SLEEP=1 END_SLEEP=1 bash -c "$(cat $S)" cio 2>&1 | grep -E "CIO-FAIL|PROF MODE|PROF START|STAGE (code|prof)|RBEGIN" | cut -c1-200)
  echo "--- $label"; echo "$out" | sed 's/^/    /'
  if echo "$out" | grep -q -- "$want"; then echo "    => as expected (found: $want)"; else echo "    => NOT AS EXPECTED (wanted: $want)"; fi
}
t "PROFILE=yes is refused" "PROFILE must be 0 or 1" PROFILE=yes PTC_DRY=1
t "PROFILE=1 with PROF_DRY_ARGS but without PTC_DRY is refused" "need PTC_DRY=1" PROFILE=1 PTC_DRY=0 PROF_DRY_ARGS="--device cpu"
t "PROFILE=1 with PROF_DRY_FAIL but without PTC_DRY is refused" "need PTC_DRY=1" PROFILE=1 PTC_DRY=0 PROF_DRY_FAIL=c_equiv
t "PROFILE=1 with PROF_DRY_HANG but without PTC_DRY is refused" "need PTC_DRY=1" PROFILE=1 PTC_DRY=0 PROF_DRY_HANG=a_profile
t "PROFILE=1 with PTC_DRY=1 on a box where nvidia-smi -L lists a GPU is refused" "box that has a GPU" PATH=$B/fakebin:$PATH PROFILE=1 PTC_DRY=1
t "EG=0 is still refused" "EG=1 is required" PROFILE=1 PTC_DRY=1 EG=0
rm -rf $T
