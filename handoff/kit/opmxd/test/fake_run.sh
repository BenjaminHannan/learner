#!/bin/bash
# Dry-run tests for kit opmxd against a FAKE vastai, FAKE ssh/scp (the "rental" is a scratch folder $T/rental; /root/r is rewritten to it), a FAKE python/pip/nvidia-smi
# (the driver is replaced by a stand-in that writes the same file names) and a FAKE clock and sleep. Nothing here rents anything, reads any key, or contacts vast.
# The kit scripts run UNCHANGED, from a git archive of a scratch repo (like the queue jobs), pointed at scratch folders by their own env overrides (GOPMXD, LSRCOPMXD, ...).
# Modelled on handoff/kit/sleeph6r/test/run-tests.sh. Usage: bash handoff/kit/opmxd/test/fake_run.sh [scenario-number ...]   (no argument = all)
set -u
TESTDIR=$(cd "$(dirname "$0")" && pwd); KITSRC=$(cd "$TESTDIR/.." && pwd); REPOSRC=$(cd "$KITSRC/../../.." && pwd)
A=artifacts/claude-moe-deep-20260929; OUT=artifacts/opus-manager-20260929/mxd-vast
T=$(mktemp -d "${TMPDIR:-/tmp}/opmxdtest.XXXXXX"); REAL=/usr/bin/date; PY3=$(command -v python3)
export FAKE=$T/fake RENTAL=$T/rental GOPMXD=$T/G KEYOPMXD=$T/key/id_test PYMOPMXD=$PY3 LSRCOPMXD=$T/mac/runs FAKE_SPEED=${FAKE_SPEED:-300}
export PATH=$TESTDIR/bin:$PATH
PASS=0; FAILS=0
ok()  { PASS=$((PASS+1)); echo "   ok    $*"; }
bad() { FAILS=$((FAILS+1)); echo "   FAIL  $*"; }
chk() { d=$1; shift; if "$@" > /dev/null 2>&1; then ok "$d"; else bad "$d"; fi; }
has() { if grep -q -E -- "$3" "$2" 2>/dev/null; then ok "$1"; else bad "$1 (no match for /$3/ in $2)"; fi; }
hasnt() { if grep -q -E -- "$3" "$2" 2>/dev/null; then bad "$1 (found /$3/ in $2)"; else ok "$1"; fi; }
title() { echo; echo "== $1"; }
ONLY=" $* "
want() { [ -z "${ONLY// /}" ] && return 0; case "$ONLY" in *" $1 "*) return 0;; esac; return 1; }
destroyed() { { tr '\n' ' ' < "$FAKE/vast/destroyed.log" | sed 's/destroyed //g'; } 2>/dev/null; }
stopped() { { tr '\n' ' ' < "$FAKE/vast/stopped.log" | sed 's/stopped //g'; } 2>/dev/null; }

build_repo() {
  mkdir -p "$T/origin.git" "$T/repo" "$T/key" "$T/mac/runs/qual-loop-s0" "$T/mac/runs/qual-loop-s1"; git init -q --bare "$T/origin.git"
  head -c 200000 /dev/urandom > "$T/mac/runs/qual-loop-s0/source.pt"; head -c 200000 /dev/urandom > "$T/mac/runs/qual-loop-s1/source.pt"
  export LSHA0OPMXD=$(sha256sum "$T/mac/runs/qual-loop-s0/source.pt" | cut -d' ' -f1) LSHA1OPMXD=$(sha256sum "$T/mac/runs/qual-loop-s1/source.pt" | cut -d' ' -f1)
  cd "$T/repo"; mkdir -p $A scripts artifacts/claude-fewex-20260927/runs/qual-loop-s0 artifacts/claude-fewex-20260927/runs/qual-loop-s1 artifacts/claude-distill-20260928
  for f in $A/PASSMARKS.md $A/DESIGN.md $A/selftest.json scripts/claude_moe_deep_net.py scripts/claude_moe_deep_run.py scripts/claude_moe_deep_report.py; do echo "sealed stand-in $f" > $f; done
  for f in $A/PASSMARKS.md $A/DESIGN.md $A/selftest.json scripts/claude_moe_deep_net.py scripts/claude_moe_deep_run.py scripts/claude_moe_deep_report.py; do sha256sum $f; done > $A/SEAL.sha256.txt
  echo '{"stand-in": true}' > artifacts/claude-fewex-20260927/runs/qual-loop-s0/source.json; echo '{"stand-in": true}' > artifacts/claude-fewex-20260927/runs/qual-loop-s1/source.json
  printf '%s  qual-loop-s0/source.pt\n%s  qual-loop-s1/source.pt\n' "$LSHA0OPMXD" "$LSHA1OPMXD" > artifacts/claude-distill-20260928/checkpoints-sha256.txt
  mkdir -p handoff/kit handoff/queue; tar -cf - -C "$REPOSRC" --exclude=handoff/kit/opmxd/test handoff/kit/opmxd | tar -x -C .
  cp "$REPOSRC/handoff/queue/opus-mxd-vast-1-start.md" "$REPOSRC/handoff/queue/opus-mxd-vast-2-collect.md" handoff/queue/
  echo "ssh-ed25519 AAAAFAKEFAKEFAKE opmxd-test-only" > "$T/key/id_test.pub"; echo "not a key" > "$T/key/id_test"
  git init -q -b main && git add -A && git -c user.name=t -c user.email=t@t commit -q -m "test repo" && git remote add origin "$T/origin.git" \
    && git -c push.negotiate=false push -q origin main && git -c push.negotiate=false push -q origin main:builder-outbox && git fetch -q origin
  PIN=$(git rev-parse HEAD); cd "$TESTDIR"
}
job() {   # job <queue-file-name>: extract the fenced bash block of the REAL queue file, set its PIN, write it as <name>.bo.sh
  awk '/^```bash/{f=1;next} /^```/{f=0} f' "$REPOSRC/handoff/queue/$1.md" | sed "s/PIN=[^ ;]*/PIN=$PIN/" > "$T/$1.bo.sh"; echo "$T/$1.bo.sh"; }
runjob() { j=$(job "$1"); ( cd "$T/repo" && bash "$j" ) > "$T/out/$1.txt" 2>&1; echo $? > "$T/out/$1.rc"; }
kill_fakes() {
  [ -s "$T/G/guard.pid" ] && kill "$(cat "$T/G/guard.pid")" 2>/dev/null
  pkill -f "vguard.sh $T/G" 2>/dev/null; pkill -f "handoff/kit/opmxd/box/drive.sh" 2>/dev/null; pkill -f "claude_moe_deep_run.py" 2>/dev/null
  [ -f "$FAKE/py/pids" ] && while read -r a b; do kill $a $b 2>/dev/null; done < "$FAKE/py/pids"; return 0; }
reset() {
  kill_fakes; /usr/bin/sleep 0.3; rm -rf "$T/repo/artifacts/opus-manager-20260929"
  rm -rf "$RENTAL" "$T/G" "$FAKE" "$T/out"; mkdir -p "$RENTAL" "$T/G" "$FAKE/vast" "$FAKE/ssh" "$FAKE/gpu" "$FAKE/py" "$T/out"
  cp "$TESTDIR/fixtures/offers.json" "$FAKE/vast/offers.json"; echo 23.73 > "$FAKE/vast/credit"
  export FAKE_V0=$($REAL +%s) FAKE_R0=$($REAL +%s%N)
}
wait_end() { for w in $(seq 1 ${1:-240}); do [ -s "$T/G/END" ] && return 0; /usr/bin/sleep 1; done; return 1; }
wait_state() { for w in $(seq 1 ${2:-120}); do grep -q -E -- "$1" "$RENTAL/W/drive-state.txt" 2>/dev/null && return 0; /usr/bin/sleep 1; done; return 1; }

echo "kit opmxd fake-run tests, $($REAL -u +%FT%TZ) (real clock; the fakes run a virtual clock $FAKE_SPEED times faster)"
build_repo; echo "test repo $T/repo, PIN $PIN"

if want 0; then title "0. static checks: bash syntax, bash-3.2 safety, no key reads, constants"
  for f in vcommon.sh vstart.sh vguard.sh vcollect.sh box/drive.sh test/fake_run.sh; do chk "bash -n $f" bash -n "$KITSRC/$f"; done
  for f in bin/ssh bin/scp bin/python bin/pip bin/nvidia-smi; do chk "bash -n test/$f" bash -n "$TESTDIR/$f"; done
  hasnt "no bash-4-only syntax in the kit" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh) 'declare -A|mapfile|readarray|wait -n|\|&|\$\{[a-zA-Z_]*(,,|\^\^)|&>>'
  hasnt "kit never uses the timeout command (macOS has none)" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh | grep -v '^#') '(^|[ (;|&])timeout '
  hasnt "kit never reads a vast key or ~/.config/vastai or ~/.ssh files other than the .pub" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh | grep -v '^#') 'config/vastai|\.vast_api_key|api.?key|cat "?\$KEY"?( |$)'
  for c in "CAP_STOP=2.50" "MAXDPH=0.50" "MINRAM_GB=16" "LABEL=opus-mxd" "BASE_H=5.25"; do has "constant $c" "$KITSRC/vcommon.sh" "^$c( |\$)"; done
  has "state dir default is ~/premonition-watch/opmxd-vast" "$KITSRC/vcommon.sh" 'premonition-watch/opmxd-vast'
  hasnt "kit never writes into the sealed moe folder in the repo (no OUT under claude-moe-deep in vcollect)" <(grep -v '^#' "$KITSRC/vcollect.sh") 'cp .*"?\$A/'
  has "credit floor uses CAP_STOP" "$KITSRC/vstart.sh" 'over "\$\{CR:-0\}" "\$CAP_STOP"'
fi

if want 1; then title "1. normal path: start, guard, smoke, six parts in the money order, DONE, verified copy, destroy, collect"
  reset; runjob opus-mxd-vast-1-start; O=$T/out/opus-mxd-vast-1-start.txt; has "start printed STARTED" "$O" '^STARTED$'
  has "offers ranked best TFLOPS per \$/h first: 1002 (3090 @0.10), 1003 (4090 @0.25), 1001 (5090 @0.36)" <(grep -E '^100[0-9] ' "$O" | awk '{print $1}' | tr '\n' ' ') '^1002 1003 1001 $'
  for x in 1004:price 1005:memory 1006:fit-check; do hasnt "offer ${x%%:*} excluded (${x##*:})" <(grep -E '^100[0-9] ' "$O") "^${x%%:*} "; done
  has "the search asked for compute_cap>=800, cuda_max_good>=12.6, reliability>=0.98, cores>=8, gpu_ram>=16" "$FAKE/vast/calls.log" 'gpu_ram>=16 compute_cap>=800 reliability>=0.98.*cpu_cores_effective>=8 cuda_max_good>=12.6'
  has "loop sources on the Mac matched" "$T/G/log.txt" 'loop control sources on the Mac: both match'
  has "loop sources were sent" "$T/G/log.txt" 'loop control sources sent to the rental'
  has "estimate logged with the 1.5x time cap" "$T/G/log.txt" 'estimate 15\.3[0-9]* h .*time cap [0-9]+ s \(1\.5x\); money stop \$2\.50'
  wait_end 240 && ok "guard ended by itself" || bad "guard did not end"; S=$T/G/out/W/drive-state.txt
  has "END is DONE" "$T/G/END" '^END DONE spent'
  has "torch pin recorded" "$S" 'TORCH torch 2\.14\.0\+cu126 12\.6 True'; has "seal 6/6" "$S" ' SEAL 6/6'; has "loop sources ok on the rental" "$S" 'LOOP-SOURCES ok'
  has "selftest ok" "$S" ' SELFTEST-OK'; has "smoke PASS true recorded" "$S" 'SMOKE-DONE PASS true'
  has "parts finished in the money order" <(grep PART-DONE "$S" | awk '{print $3}' | tr '\n' ' ') '^src-s0 mx-s0 ctl-s0 src-s1 mx-s1 ctl-s1 $'
  has "phase1_done in the phase log" "$T/G/out/W/log_phase1.txt" 'phase1_done'; has "state ends DONE" <(tail -1 "$S") ' DONE$'
  has "driver called with the loop root for loopctl only" <(grep 'loopctl' "$FAKE/py/calls.log" | tr '\n' ' ') 'dev cfg=loopctl seed=0 loop-root=loopsrc.*dev cfg=loopctl seed=1 loop-root=loopsrc'
  has "torch pin passed to pip with the cu126 index" <(grep -h 'fake pip' "$FAKE/py/calls.log") 'torch==2\.14\.0 --index-url https://download\.pytorch\.org/whl/cu126'
  has "copy-back: every manifest file matched" "$T/G/log.txt" 'COPY-CHECK: ([0-9]+) of \1 files arrived and match'
  has "copy-back: every finished part accounted for" "$T/G/log.txt" 'every part the rental recorded as finished is accounted for'
  chk "destroyed exactly our id" test "$(destroyed)" = "7000001 "
  chk "no .pt anywhere in the copy" test -z "$(find "$T/G/out" -name '*.pt')"
  chk "the rental really had .pt files (so the exclusion is tested)" test -n "$(find "$RENTAL/artifacts" -name '*.pt')"
  chk "selftest.json (rewritten on the rental) not copied back" test -z "$(find "$T/G/out" -name selftest.json)"
  chk "mirror holds runs/, eq-runs/, SMOKE-gpu.json, TIMING-gpu.json" test -s "$T/G/out/W/moe/runs/L8-E64-s1/qualified.json" -a -s "$T/G/out/W/moe/eq-runs/loopctl-pre-s1/adapt.json" -a -s "$T/G/out/W/moe/SMOKE-gpu.json" -a -s "$T/G/out/W/moe/TIMING-gpu.json"
  ( cd "$T/repo" && git status --short > "$T/git0.txt" ); runjob opus-mxd-vast-2-collect; C=$T/out/opus-mxd-vast-2-collect.txt
  has "collect printed COLLECTED" "$C" '^COLLECTED$'
  chk "results in $OUT: runs, eq-runs, SMOKE, TIMING, logs, run-vast" test -s "$T/repo/$OUT/runs/L8-E64-s0/qualified.json" -a -s "$T/repo/$OUT/eq-runs/L8-E64-pre-s1/adapt.json" -a -s "$T/repo/$OUT/SMOKE-gpu.json" -a -s "$T/repo/$OUT/TIMING-gpu.json" -a -s "$T/repo/$OUT/logs/log_phase1.txt" -a -s "$T/repo/$OUT/logs/smoke_log.txt" -a -s "$T/repo/$OUT/logs/selftest_rental.txt" -a -s "$T/repo/$OUT/run-vast/COLLECT.txt" -a -s "$T/repo/$OUT/run-vast/drive-state.txt"
  chk "collect wrote NOTHING into the sealed folder $A (git status shows no change there)" test -z "$(cd "$T/repo" && git status --short -- $A scripts)"
  chk "no .pt and no holdout file in $OUT" test -z "$(find "$T/repo/$OUT" \( -name '*.pt' -o -name 'holdout*' \))"
  has "COLLECT.txt lists sha256 of adapt.json files" "$T/repo/$OUT/run-vast/COLLECT.txt" '[0-9a-f]{64}  .*adapt\.json'
  runjob opus-mxd-vast-1-start; has "a second start is refused (DUPLICATE)" "$T/out/opus-mxd-vast-1-start.txt" 'DUPLICATE'
  runjob opus-mxd-vast-2-collect; has "a second collect is only a no-op here (local repo has no COLLECT on origin, guard ended: collects again)" "$T/out/opus-mxd-vast-2-collect.txt" 'COLLECTED|DUPLICATE'
fi

if want 2; then title "2. budget stop \$2.50: seed 0 whole (in money order), seed 1 source running; partial copy-back verified, destroyed"
  reset; touch "$FAKE/py/hang-source-L8-E64-1"; runjob opus-mxd-vast-1-start; has "STARTED" "$T/out/opus-mxd-vast-1-start.txt" '^STARTED$'
  wait_state 'PART-START src-s1' 200 && ok "seed 0 finished, seed 1 source running" || bad "did not reach seed 1"
  echo $((26 * 3600)) > "$FAKE/clock-jump"   # the virtual clock jumps 26 h ahead: 26 h x 0.10 = 2.60 dollars
  wait_end 120 && ok "guard ended" || bad "guard did not end"
  has "END BUDGET-STOP" "$T/G/END" '^END BUDGET-STOP spent'; has "copy verified" "$T/G/log.txt" 'COPY-CHECK: every part the rental recorded as finished is accounted for'
  has "seed 0 parts copied" <(cd "$T/G/out/W/moe" && find . -name '*.json' | sort | tr '\n' ' ') 'eq-runs/L8-E64-pre-s0/adapt.json'
  has "loop control s0 copied" <(cd "$T/G/out/W/moe" && find . -name '*.json' | tr '\n' ' ') 'eq-runs/loopctl-pre-s0/adapt.json'
  chk "seed 1 source not in the copy (it was still running)" test ! -e "$T/G/out/W/moe/runs/L8-E64-s1/qualified.json"
  chk "destroyed by exact id after the verified copy" test "$(destroyed)" = "7000001 "; chk "not merely stopped" test -z "$(stopped)"
fi

if want 3; then title "3. LOOP-SOURCE-MISSING (sources absent on the Mac; and one with a wrong sha): loop control ladders skipped, driver never given --loop-source-root"
  for v in missing wrongsha; do reset; SAVE0=$LSHA0OPMXD
    [ $v = missing ] && export LSRCOPMXD=$T/mac/none; [ $v = wrongsha ] && export LSHA1OPMXD=0000000000000000000000000000000000000000000000000000000000000000
    runjob opus-mxd-vast-1-start; has "[$v] start logged LOOP-SOURCE-MISSING" "$T/G/log.txt" 'LOOP-SOURCE-MISSING'; has "[$v] start still printed STARTED" "$T/out/opus-mxd-vast-1-start.txt" '^STARTED$'
    hasnt "[$v] no scp of a loop source" "$FAKE/ssh/calls.log" 'scp .*source\.pt'
    wait_end 240 && ok "[$v] guard ended" || bad "[$v] guard did not end"; S=$T/G/out/W/drive-state.txt
    has "[$v] drive-state: LOOP-SOURCE-MISSING" "$S" 'LOOP-SOURCE-MISSING'; has "[$v] ctl-s0 and ctl-s1 skipped" <(grep 'PART-SKIPPED ctl' "$S" | awk '{print $3}' | tr '\n' ' ') '^ctl-s0 ctl-s1 $'
    hasnt "[$v] the driver never ran the loop control" "$FAKE/py/calls.log" 'loopctl|loop-root=loopsrc'; has "[$v] END DONE" "$T/G/END" '^END DONE spent'
    has "[$v] copy-check passes with skipped parts" "$T/G/log.txt" 'every part the rental recorded as finished is accounted for'; chk "[$v] destroyed" test "$(destroyed)" = "7000001 "
    export LSRCOPMXD=$T/mac/runs LSHA1OPMXD=$(sha256sum "$T/mac/runs/qual-loop-s1/source.pt" | cut -d' ' -f1); done
fi

if want 4; then title "4. drive.sh FAILED and its variants"
  reset; touch "$FAKE/py/selftest-fail"; runjob opus-mxd-vast-1-start; has "[selftest fail] start reports the stop" "$T/G/log.txt" 'STOPPED: drive.sh did not pass its checks'; has "  END START-FAIL" "$T/G/END" '^END START-FAIL spent'
  has "  progress file says why" "$T/G/out/W/drive-state.txt" 'FAILED SELFTEST-FAIL'; chk "  destroyed after copy of the logs" test "$(destroyed)" = "7000001 "; chk "  nothing ran (no smoke, no part)" test "$(grep -c -E 'SMOKE|PART' "$T/G/out/W/drive-state.txt")" = 0
  reset; echo 2.8.0+cu128 > "$FAKE/py/torch-ver"; runjob opus-mxd-vast-1-start; has "[wrong torch] fail-closed" "$T/G/out/W/drive-state.txt" 'FAILED NO-CUDA or wrong torch'; chk "  destroyed" test "$(destroyed)" = "7000001 "
  reset; touch "$FAKE/py/pip-fail"; runjob opus-mxd-vast-1-start; has "[pip fails] FAILED at once" "$T/G/out/W/drive-state.txt" 'FAILED pip install torch==2\.14\.0'; chk "  destroyed" test "$(destroyed)" = "7000001 "
  reset; ( cd "$T/repo" && echo "changed after sealing" >> scripts/claude_moe_deep_net.py && git add -A && git -c user.name=t -c user.email=t@t commit -q -m "edit sealed script" && git -c push.negotiate=false push -q origin main && git fetch -q origin ); PIN0=$PIN; PIN=$(git -C "$T/repo" rev-parse HEAD)
  runjob opus-mxd-vast-1-start; has "[seal] SEAL-MISMATCH 5/6" "$T/G/out/W/drive-state.txt" 'FAILED SEAL-MISMATCH 5/6 OK'; chk "  destroyed" test "$(destroyed)" = "7000001 "; PIN=$PIN0
  ( cd "$T/repo" && git reset -q --hard "$PIN0" && git -c push.negotiate=false push -q -f origin main && git fetch -q origin )
  reset; touch "$FAKE/py/smoke-crash"; runjob opus-mxd-vast-1-start; wait_end 240 && ok "[smoke crash] guard ended" || bad "[smoke crash] guard did not end"
  has "  END FAILED" "$T/G/END" '^END FAILED spent'; has "  SMOKE-CRASH recorded with the traceback tail" "$T/G/out/W/drive-state.txt" 'FAILED SMOKE-CRASH rc 1.*RuntimeError'; chk "  no phase part ran" test "$(grep -c PART "$T/G/out/W/drive-state.txt")" = 0; chk "  destroyed" test "$(destroyed)" = "7000001 "
  reset; touch "$FAKE/py/smoke-fail"; runjob opus-mxd-vast-1-start; wait_end 240 && ok "[smoke FAIL] guard ended" || bad "[smoke FAIL] guard did not end"
  has "  SMOKE PASS false recorded and phase 1 went on" "$T/G/out/W/drive-state.txt" 'SMOKE-DONE PASS false'; has "  END DONE" "$T/G/END" '^END DONE spent'; chk "  all six parts finished" test "$(grep -c PART-DONE "$T/G/out/W/drive-state.txt")" = 6
  reset; echo 1 > "$FAKE/py/die-dev-L8-E64-0"; runjob opus-mxd-vast-1-start; wait_end 240 && ok "[one death] guard ended" || bad "[one death] guard did not end"
  has "  resumed once and finished" "$T/G/out/W/drive-state.txt" 'RESUME-ONCE mx-s0 rc 1'; has "  END DONE" "$T/G/END" '^END DONE spent'
  reset; echo 5 > "$FAKE/py/die-source-L8-E64-1"; runjob opus-mxd-vast-1-start; wait_end 240 && ok "[two deaths] guard ended" || bad "[two deaths] guard did not end"
  has "  second death: FAILED PHASE1-DIED at src-s1" "$T/G/out/W/drive-state.txt" 'FAILED PHASE1-DIED at src-s1'; has "  guard END FAILED" "$T/G/END" '^END FAILED spent'
  has "  seed 0 results were copied before destroy" <(cd "$T/G/out/W/moe" && find . -name adapt.json | tr '\n' ' ') 'loopctl-pre-s0'; chk "  destroyed" test "$(destroyed)" = "7000001 "
  reset; touch "$FAKE/py/unqualified-1"; runjob opus-mxd-vast-1-start; wait_end 240 && ok "[unqualified source] guard ended" || bad "[unqualified source] guard did not end"
  has "  mx-s1 skipped (not a death)" "$T/G/out/W/drive-state.txt" 'PART-SKIPPED mx-s1 \(rc 1: SOURCE-NOT-QUALIFIED'; has "  END DONE" "$T/G/END" '^END DONE spent'
fi

if want 5; then title "5. copy check fails (a file changes under the copy, twice): STOP, not destroy"
  reset; echo 99 > "$FAKE/ssh/mutate-on-tar"; runjob opus-mxd-vast-1-start; has "STARTED" "$T/out/opus-mxd-vast-1-start.txt" '^STARTED$'
  wait_end 240 && ok "guard ended" || bad "guard did not end"
  has "COPY-CHECK FAIL logged" "$T/G/log.txt" 'COPY-CHECK FAIL: [0-9]+ of [0-9]+ files match'
  has "END is ...-STOPPED-NOT-DESTROYED" "$T/G/END" '^END DONE-STOPPED-NOT-DESTROYED spent'
  chk "nothing destroyed" test -z "$(destroyed)"; chk "the instance was stopped by exact id" test "$(stopped)" = "7000001 "
  chk "the instance is still listed (files kept on its disk)" test -d "$FAKE/vast/instances/7000001"
  runjob opus-mxd-vast-2-collect; has "collect flags the Director" "$T/out/opus-mxd-vast-2-collect.txt" 'FLAG-DIRECTOR: instance 7000001 of opus-mxd was NOT destroyed'
fi

if want 6; then title "6. refusals: nothing may be rented"
  reset; echo 2.00 > "$FAKE/vast/credit"; runjob opus-mxd-vast-1-start; has "credit under \$2.50" "$T/out/opus-mxd-vast-1-start.txt" 'STOP: credit \$2\.0* is under the \$2\.50 cap'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'
  reset; mkdir -p "$FAKE/vast/instances/555"; echo opus-mxd > "$FAKE/vast/instances/555/label"; echo running > "$FAKE/vast/instances/555/status"; echo 0 > "$FAKE/vast/instances/555/polls"
  runjob opus-mxd-vast-1-start; has "a live instance with our label" "$T/out/opus-mxd-vast-1-start.txt" 'DUPLICATE: live instance\(s\) labelled opus-mxd: 555'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'; chk "555 untouched" test -d "$FAKE/vast/instances/555"
  reset; echo '[]' > "$FAKE/vast/offers.json"; runjob opus-mxd-vast-1-start; has "no offer fits" "$T/G/log.txt" 'STOP: no offer'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'
  reset; python3 - "$FAKE/vast/offers.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); [o.update(dph_total=0.60) for o in d]; json.dump(d, open(sys.argv[1], "w"))
PY
  runjob opus-mxd-vast-1-start; has "every offer above MAXDPH 0.50: nothing rented" "$T/G/log.txt" 'STOP: no offer at or under \$0\.50/h'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'
  reset; ( cd "$T/repo" && mkdir -p $A && echo '{}' > $A/SMOKE-gpu.json && git add -A -f && git -c user.name=t -c user.email=t@t commit -q -m "mxd-1 ran" && git -c push.negotiate=false push -q origin main && git fetch -q origin ); PIN0=$PIN; PIN=$(git -C "$T/repo" rev-parse HEAD)
  runjob opus-mxd-vast-1-start; has "BensPC mxd-1 already produced SMOKE-gpu.json on main: DUPLICATE" "$T/out/opus-mxd-vast-1-start.txt" 'DUPLICATE: origin/main already has .*SMOKE-gpu.json'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'; PIN=$PIN0
  ( cd "$T/repo" && git reset -q --hard "$PIN0" && git -c push.negotiate=false push -q -f origin main && git fetch -q origin )
fi
kill_fakes
echo; echo "RESULT: $PASS passed, $FAILS failed  (scratch: $T)"
[ $FAILS = 0 ]
