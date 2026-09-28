#!/bin/bash
# Dry-run tests for kit sleeph6r against a FAKE vastai, a FAKE ssh (the "rental" is /root/r on this box) and a FAKE clock and sleep.
# Written 2026-09-28 by helper H7. Linux, run as root (it makes and empties /root/r, but only if that folder is a fake rental it made:
# it refuses to touch a /root/r without the marker file .h7-fake-rental). Nothing here rents anything, reads any key or contacts vast.
# The kit scripts run UNCHANGED: the fakes sit first on PATH (test/bin) and the kit is pointed at test folders through its own
# environment overrides (GH6V, MPUH6, KEYH6, PYMH6). Queue jobs are run from the fenced bash blocks of the queue files themselves.
# Usage: TMPDIR=<scratch dir> bash handoff/kit/sleeph6r/test/run-tests.sh [scenario-number ...]     (no argument = all)
set -u
TESTDIR=$(cd "$(dirname "$0")" && pwd); KITSRC=$(cd "$TESTDIR/.." && pwd); REPOSRC=$(cd "$KITSRC/../../.." && pwd)
A=artifacts/claude-dir-h6-sleeplen-20260928; N3A=artifacts/claude-slp358n3-20260927
T=$(mktemp -d "${TMPDIR:-/tmp}/h7test.XXXXXX"); REAL=/usr/bin/date
export FAKE=$T/fake GH6V=$T/G MPUH6=$T/models/rsn358u KEYH6=$T/key/id_test PYMH6=/usr/bin/python3 FAKE_SPEED=${FAKE_SPEED:-300}
export PATH=$TESTDIR/bin:$PATH
PASS=0; FAILS=0
ok()  { PASS=$((PASS+1)); echo "   ok    $*"; }
bad() { FAILS=$((FAILS+1)); echo "   FAIL  $*"; }
chk() { d=$1; shift; if "$@" > /dev/null 2>&1; then ok "$d"; else bad "$d"; fi; }
has() { if grep -q -E -- "$3" "$2" 2>/dev/null; then ok "$1"; else bad "$1 (no match for /$3/ in $2)"; fi; }
hasnt() { if grep -q -E -- "$3" "$2" 2>/dev/null; then bad "$1 (found /$3/ in $2)"; else ok "$1"; fi; }
show() { echo "   | $(echo "$*" | cut -c1-230)"; }
excerpt() { f=$1; shift; grep -E -- "$1" "$f" 2>/dev/null | head -${2:-6} | while IFS= read -r l; do show "$l"; done; }

# ---------- a fake project (git repo with an origin) built from the real files ----------
build_repo() {
  mkdir -p "$T/origin.git" "$T/repo" "$T/key" "$T/models/rsn358u"; git init -q --bare "$T/origin.git"
  ( cd "$REPOSRC" && { awk '{print $2}' "$N3A/SEAL-code.sha256.txt" "$A/SEAL-code.sha256.txt"; ls "$A"/* "$N3A/SEAL-code.sha256.txt" "$N3A/run-vast/sizes.json" artifacts/claude-rsn358i-20260926/tests/*; ls handoff/queue/*h7-dirh6-*.md; } | sort -u | while read -r f; do
      [ -f "$f" ] && { mkdir -p "$T/repo/$(dirname "$f")"; cp "$f" "$T/repo/$f"; }; done
    tar -cf - --exclude=handoff/kit/sleeph6r/test handoff/kit/sleeph6r | tar -x -C "$T/repo" )
  for s in 13 14 15 16; do mkdir -p "$T/models/rsn358u/loop-s$s"; head -c 300000 /dev/urandom > "$T/models/rsn358u/loop-s$s/final.pt"; cp "$T/models/rsn358u/loop-s$s/final.pt" "$T/models/rsn358u/loop-s$s/final.pt.orig"; done
  mkdir -p "$T/repo/artifacts/claude-rsn358u-20260927"
  ( cd "$T/models/rsn358u" && for s in 13 14 15 16; do echo "$(sha256sum loop-s$s/final.pt | cut -d' ' -f1)  loop-s$s/final.pt"; echo "$(echo plain$s | sha256sum | cut -d' ' -f1)  plain-s$s/final.pt"; done ) > "$T/repo/artifacts/claude-rsn358u-20260927/SEAL-run.sha256.txt"
  echo "ssh-ed25519 AAAAFAKEFAKEFAKE h7-test-only" > "$T/key/id_test.pub"; echo "not a key" > "$T/key/id_test"
  cd "$T/repo" && git init -q -b main && git add -A && git -c user.name=t -c user.email=t@t commit -q -m "test repo" \
    && git remote add origin "$T/origin.git" && git -c push.negotiate=false push -q origin main && git -c push.negotiate=false push -q origin main:builder-outbox && git fetch -q origin
  PIN=$(git rev-parse HEAD)
}
job() {   # job <queue-file-name>: extract the fenced bash block, set its PIN, write it as <name>.bo.sh
  awk '/^```bash/{f=1;next} /^```/{f=0} f' "$T/repo/handoff/queue/$1.md" | sed "s/PIN=[^ ;]*/PIN=$PIN/" > "$T/$1.bo.sh"; echo "$T/$1.bo.sh"; }
runjob() { j=$(job "$1"); ( cd "$T/repo" && bash "$j" ) > "$T/out/$1.txt" 2>&1; rc=$?; echo $rc > "$T/out/$1.rc"; }
kill_fakes() {
  for hp in "$FAKE/py/hang.pids" "$FAKE/ssh/hung.pids"; do [ -f "$hp" ] && while read -r p; do [ -n "$p" ] && kill "$p" 2>/dev/null; done < "$hp"; done
  [ -s "$T/G/guard.pid" ] && kill "$(cat "$T/G/guard.pid")" 2>/dev/null
  [ -f /root/r/W/pids.txt ] && while read -r k n p; do [ -n "${p:-}" ] && kill "$p" 2>/dev/null; done < /root/r/W/pids.txt
  # leftover start jobs of an earlier scenario (a job wrapper and its vstart.sh child); TERM lets vstart's own cleanup run first
  for w in 1 2 3 4 5 6 7 8 9 10; do
    lp=$(pgrep -f "(sleeph6r/vstart\.sh|$T/.*\.bo\.sh)" | grep -v -x "$$" | tr '\n' ' '); [ -z "${lp// /}" ] && break
    for p in $lp; do kill -TERM "$p" 2>/dev/null; done; /usr/bin/sleep 1; done
  return 0; }
reset() {
  kill_fakes
  [ ! -e /root/r ] || [ -e /root/r/.h7-fake-rental ] || { echo "REFUSING: /root/r exists and is not a fake rental made by this test"; exit 2; }
  rm -rf /root/r "$T/G" "$FAKE" "$T/out" "$T/repo/$A/runs" "$T/repo/$A/run-vast"; mkdir -p /root/r "$T/G" "$FAKE/vast" "$FAKE/ssh" "$FAKE/gpu" "$FAKE/py" "$T/out"; : > /root/r/.h7-fake-rental
  cp "$TESTDIR/fixtures/offers.json" "$FAKE/vast/offers.json"; echo 23.73 > "$FAKE/vast/credit"; echo "2.11.0+cu128" > "$FAKE/py/torch-install"
  for s in 13 14 15 16; do cp "$T/models/rsn358u/loop-s$s/final.pt.orig" "$T/models/rsn358u/loop-s$s/final.pt"; done
  export FAKE_V0=$($REAL +%s) FAKE_R0=$($REAL +%s%N)
}
wait_end() { for w in $(seq 1 ${1:-240}); do [ -s "$T/G/END" ] && return 0; /usr/bin/sleep 1; done; return 1; }
wait_file() { for w in $(seq 1 ${2:-120}); do [ -e "$1" ] && return 0; /usr/bin/sleep 1; done; return 1; }
destroyed() { tr '\n' ' ' < "$FAKE/vast/destroyed.log" 2>/dev/null | sed 's/destroyed //g'; }
stopped() { tr '\n' ' ' < "$FAKE/vast/stopped.log" 2>/dev/null | sed 's/stopped //g'; }
title() { echo; echo "== $1"; }
ONLY=" $* "
want() { [ -z "${ONLY// /}" ] && return 0; case "$ONLY" in *" $1 "*) return 0;; esac; return 1; }
alive() { [ -r "/proc/$1/status" ] && ! grep -q '^State:[[:space:]]*Z' "/proc/$1/status"; }
wait_launches() { for w in $(seq 1 ${2:-90}); do [ "$(grep -c ' LAUNCH ' /root/r/W/drive-state.txt 2>/dev/null)" = "$1" ] && return 0; /usr/bin/sleep 1; done; return 1; }

echo "kit sleeph6r dry-run tests, $($REAL -u +%FT%TZ) (real clock; the fakes run a virtual clock $FAKE_SPEED times faster)"
build_repo; echo "test repo $T/repo, PIN $PIN"

if want 0; then title "0. static checks: bash syntax, bash-3.2 safety grep, python compile, no key reads, offers ranking"
  for f in vcommon.sh vstart.sh vguard.sh vcollect.sh box/drive.sh box/halt.sh; do chk "bash -n $f" bash -n "$KITSRC/$f"; done
  for f in run-tests.sh bin/vastai bin/ssh bin/python bin/date bin/sleep; do chk "bash -n test/$f" bash -n "$TESTDIR/$f"; done
  chk "offers.py compiles" python3 -m py_compile "$KITSRC/offers.py"; rm -rf "$KITSRC/__pycache__"
  chk "scripts/claude_dir_h6_sleeplen.py compiles (py_compile only; torch is not installed here)" python3 -m py_compile "$REPOSRC/scripts/claude_dir_h6_sleeplen.py"; rm -rf "$REPOSRC/scripts/__pycache__"
  hasnt "no bash-4-only syntax (declare -A, mapfile, readarray, wait -n, |&, \${x,,}, \${x^^}, &>>)" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh) 'declare -A|mapfile|readarray|wait -n|\|&|\$\{[a-zA-Z_]*(,,|\^\^)|&>>'
  hasnt "kit never uses the timeout command (macOS has none)" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh | grep -v '^#') '(^|[ (;|&])timeout '
  hasnt "kit never reads a vast key or ~/.config/vastai" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh | grep -v '^#') 'config/vastai|\.vast_api_key|vast.*api.?key'
  hasnt "the only ssh key file read is the .pub (no cat of a private key)" <(cat "$KITSRC"/*.sh | grep -v '^#') 'cat "?\$KEY"?( |$)'
  hasnt "the launch line has no unbraced form" <(grep -h 'setsid nohup' "$KITSRC"/*.sh | grep -v '^#') '&& setsid nohup'
  ( cd "$TESTDIR" && python3 ../offers.py 0.60 24 4 6 5 4.0 104.8 0.8 3.0 8 < fixtures/offers.json > "$T/offers.out" ); show "offers.py on the fixture (best TFLOPS per \$/h first): $(tr '\n' '|' < "$T/offers.out")"
  chk "ranking: 1003 (4090) first, then 1002 (3090), then 1001 (5090)" test "$(awk '{print $1}' "$T/offers.out" | tr '\n' ' ')" = "1003 1002 1001 "
  for x in 1004:reliability 1005:memory 1006:price 1007:cuda 1008:compute-capability 1009:same-host 1010:fit-check 1011:cores; do hasnt "offer ${x%%:*} excluded (${x##*:})" "$T/offers.out" "^${x%%:*} "; done
fi

if want 1; then title "1. happy path: start, guard, 4 runs finish, copy-back, destroy, collect (+ a foreign instance that must stay)"
  reset; echo 2400 > "$FAKE/py/run-seconds"
  mkdir -p "$FAKE/vast/instances/999"; echo other-task > "$FAKE/vast/instances/999/label"; echo running > "$FAKE/vast/instances/999/status"; echo 0 > "$FAKE/vast/instances/999/polls"
  runjob h7-dirh6-1-start; O=$T/out/h7-dirh6-1-start.txt; excerpt "$O" 'SEAL-code|inputs:|^offers|^[0-9]{4} |STARTED|STOP|WAITING|DUPLICATE' 8
  has "start: pinned files match both seals" "$O" 'dir-h6 SEAL-code 3 of 3, slp-358n3 SEAL-code 18 of 18'
  has "start: inputs matched" "$O" 'inputs: 358u loop-s13..16/final.pt sealed on main and matching on the Mac'
  has "start: best offer (4090, id 1003) rented first" "$T/G/log.txt" 'rental 1: instance 7000001 \(offer 1003'
  has "start: printed STARTED" "$O" '^STARTED$'
  has "the search asked for compute_cap>=800, cuda_max_good>=12.8, reliability>=0.98" "$FAKE/vast/calls.log" 'compute_cap>=800.*reliability>=0.98.*cuda_max_good>=12.8'
  has "guard state and guard pid existed BEFORE the first upload" "$FAKE/ssh/upload-precheck.txt" 'state-before-upload yes'
  has "  (guard pid too)" "$FAKE/ssh/upload-precheck.txt" 'guard-before-upload yes'
  has "the attach carried only the public key (its exact byte count)" "$FAKE/vast/calls.log" "attached 7000001 key-bytes $(printf %s "$(cat "$T/key/id_test.pub")" | wc -c | tr -d ' ')"
  has "launch used the braces form and answered promptly" "$T/G/log.txt" "launch call answered 'launched'"
  wait_end 240 && ok "guard ended by itself" || bad "guard did not end"; excerpt "$T/G/log.txt" 'GUARD|COPY-CHECK|DESTROYED|SNAPSHOT' 12
  has "END is DONE" "$T/G/END" '^END DONE spent'
  has "one snapshot was taken during the run (a 40 min run, snapshot every 30 min)" "$T/G/log.txt" 'SNAPSHOT: the rental.s small files copied'
  chk "  ...and it holds the rental's progress file" test -s "$T/G/snap/W/drive-state.txt"
  has "copy-back: every manifest file matched" "$T/G/log.txt" 'COPY-CHECK: ([0-9]+) of \1 files arrived and match'
  has "copy-back: all 4 runs accounted for" "$T/G/log.txt" 'all 4 runs, sizes and the torch record accounted for'
  chk "destroyed exactly our id and nothing else" test "$(destroyed)" = "7000001 "
  chk "foreign instance 999 was not touched" test -d "$FAKE/vast/instances/999"
  chk "no weights copied back (no .pt anywhere in the copy)" test -z "$(find "$T/G/out" -name '*.pt')"
  runjob h7-dirh6-2-collect; C=$T/repo/$A/run-vast/COLLECT.txt; excerpt "$T/out/h7-dirh6-2-collect.txt" '^COLLECTED|s1[3-6]:|seed runs|torch record|smoke|guard:' 10
  has "collect: printed COLLECTED" "$T/out/h7-dirh6-2-collect.txt" '^COLLECTED$'
  has "collect: 4 launched, 4 finished, 0 died" "$C" '4 launched, 4 finished, 0 died'
  has "collect: torch recorded 2.11.0+cu128 in each result" "$C" 's13: result file yes; nights finished per arm N 3 of 3, S 3 of 3, L 3 of 3, B 3 of 3; torch 2.11.0\+cu128'
  has "collect: plan flags shown" "$C" 'plan_identical_L_B True'
  hasnt "collect prints no score (no right-answer counts)" "$C" '"right"|day_grids|day_sums'
  for s in 13 14 15 16; do chk "result file in the repo: runs/s$s/dirh6-seed$s.json" test -s "$T/repo/$A/runs/s$s/dirh6-seed$s.json"; done
  chk "run-vast has torch.txt, drive-state.txt, MANIFEST, sizes.json, smoke.txt, seals.txt" test -s "$T/repo/$A/run-vast/torch.txt" -a -s "$T/repo/$A/run-vast/drive-state.txt" -a -s "$T/repo/$A/run-vast/MANIFEST.sha256" -a -s "$T/repo/$A/run-vast/sizes.json" -a -s "$T/repo/$A/run-vast/smoke.txt" -a -s "$T/repo/$A/run-vast/seals.txt"
  has "torch record starts torch 2.11.0" "$T/repo/$A/run-vast/torch.txt" '^torch 2\.11\.0'
  has "drive-state order: TORCH, SEAL, CHECKPOINTS, CHECKS-OK, SIZES, SMOKE ok, then 4 LAUNCH" "$T/repo/$A/run-vast/drive-state.txt" 'SMOKE ok'
  test "$(grep -c ' LAUNCH ' "$T/repo/$A/run-vast/drive-state.txt")" = 4 && ok "4 LAUNCH lines" || bad "LAUNCH lines"
  runjob h7-dirh6-1-start; has "a second start is refused (DUPLICATE)" "$T/out/h7-dirh6-1-start.txt" 'DUPLICATE'
fi

if want 2; then title "2. refusals: nothing may be rented"
  reset; echo 3.10 > "$FAKE/vast/credit"; runjob h7-dirh6-1-start; has "credit under \$4" "$T/out/h7-dirh6-1-start.txt" 'STOP: credit \$3.1 is under the \$4 cap'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'
  reset; echo tampered >> "$T/models/rsn358u/loop-s14/final.pt"; runjob h7-dirh6-1-start; has "Mac checkpoint copy does not match its seal" "$T/out/h7-dirh6-1-start.txt" 'WAITING: loop-s14/final.pt sealed .*Mac copy'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'
  reset; mkdir -p "$FAKE/vast/instances/555"; echo claude-dir-h6-sleeplen > "$FAKE/vast/instances/555/label"; echo running > "$FAKE/vast/instances/555/status"; echo 0 > "$FAKE/vast/instances/555/polls"
  runjob h7-dirh6-1-start; has "a live instance with our label" "$T/out/h7-dirh6-1-start.txt" 'DUPLICATE: live instance\(s\) labelled claude-dir-h6-sleeplen: 555'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'; chk "555 not touched" test -d "$FAKE/vast/instances/555"
  reset; ( cd "$T/repo" && mkdir -p $A && echo verdict > $A/RESULTS.md && git add -A && git -c user.name=t -c user.email=t@t commit -q -m "verdict" && git -c push.negotiate=false push -q origin main && git fetch -q origin ); runjob h7-dirh6-1-start; has "a verdict already on main" "$T/out/h7-dirh6-1-start.txt" 'DUPLICATE: origin/main already has artifacts/claude-dir-h6-sleeplen-20260928/RESULTS.md'
  ( cd "$T/repo" && git rm -q $A/RESULTS.md && git -c user.name=t -c user.email=t@t commit -q -m "undo" && git -c push.negotiate=false push -q origin main && git fetch -q origin )
  reset; ( cd "$T/repo" && echo "# changed after sealing" >> scripts/claude_dir_h6_sleeplen.py && git add -A && git -c user.name=t -c user.email=t@t commit -q -m "edit sealed script" && git -c push.negotiate=false push -q origin main && git fetch -q origin ); PIN0=$PIN; PIN=$(git -C "$T/repo" rev-parse HEAD)
  runjob h7-dirh6-1-start; has "pinned h6 script differs from SEAL-code (2 of 3)" "$T/out/h7-dirh6-1-start.txt" 'match dir-h6.s SEAL-code 2 of 3'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'; PIN=$PIN0
  ( cd "$T/repo" && git reset -q --hard "$PIN0" && git push -q -f origin main && git fetch -q origin )
  reset; ( cd "$T/repo" && git checkout -q -b unpushed && echo x > unpushed.txt && git add -A && git -c user.name=t -c user.email=t@t commit -q -m unpushed ); PIN1=$PIN; PIN=$(git -C "$T/repo" rev-parse HEAD)
  runjob h7-dirh6-1-start; has "pin not on origin/main" "$T/out/h7-dirh6-1-start.txt" "STOP: $PIN is not on origin/main"; PIN=$PIN1; ( cd "$T/repo" && git checkout -q main )
  reset; echo '[]' > "$FAKE/vast/offers.json"; runjob h7-dirh6-1-start; has "no offer fits" "$T/G/log.txt" 'STOP: no offer'; hasnt "no create call" "$FAKE/vast/calls.log" 'create instance'
fi

if want 3; then title "3. an upload hangs on the first host: bounded, that rental destroyed, second host used, guard restarted for it"
  reset; echo 600 > "$FAKE/py/run-seconds"; echo "ck/s14/final.pt" > "$FAKE/ssh/hang-on"; echo 1 > "$FAKE/ssh/hang-count"
  runjob h7-dirh6-1-start; O=$T/out/h7-dirh6-1-start.txt; excerpt "$T/G/log.txt" 'rental [0-9]|guard started|DESTROYED|STOP' 10
  test "$(wc -l < "$FAKE/ssh/hung.log" 2>/dev/null || echo 0)" -ge 1 && ok "a checkpoint upload really hung (fake ssh never returned)" || bad "no hang happened"
  has "the hung host was given up: bail message" "$T/G/log.txt" 'rental 1: checkpoint upload failed or took over 1800 s'
  chk "first rental destroyed by exact id 7000001" grep -q '^destroyed 7000001$' "$FAKE/vast/destroyed.log"
  has "second rental made (offer 1002)" "$T/G/log.txt" 'rental 2: instance 7000002 \(offer 1002'
  has "start still ends STARTED" "$O" '^STARTED$'
  test "$(grep -c 'guard-before-upload yes' "$FAKE/ssh/upload-precheck.txt")" = 2 && ok "guard was running before the upload on BOTH hosts" || bad "guard-before-upload count"
  has "state names the second instance" "$T/G/state" '^7000002 '
  gp1=$(sed -n 's/.*guard started (pid \([0-9]*\)) on 7000001.*/\1/p' "$T/G/log.txt" | head -1); test -n "$gp1" && ! alive "$gp1" && ok "the first host's guard (pid $gp1) was stopped by its exact pid before the second was started" || bad "first guard $gp1 still alive?"
  wait_end 240 && ok "guard ended" || bad "guard did not end"; has "END DONE" "$T/G/END" '^END DONE'; chk "both ids destroyed, nothing else" test "$(destroyed)" = "7000001 7000002 "
fi

if want 4; then title "4. the braces launch returns at once; the unbraced form blocks until the job ends (the 358u bug)"
  reset; mkdir -p /root/r/handoff/kit/sleeph6r/box; printf '#!/bin/bash\nsleep 3000\n' > /root/r/handoff/kit/sleeph6r/box/drive.sh
  r=$( . "$KITSRC/vcommon.sh"; SS=$(sshto 127.0.0.1 22022)
       t0=$($REAL +%s%N); a=$($SS "$LAUNCH_CMD" < /dev/null); t1=$($REAL +%s%N)
       b=$($SS 'cd /root/r && setsid nohup bash handoff/kit/sleeph6r/box/drive.sh > /root/r/drive.log 2>&1 < /dev/null & echo launched' < /dev/null); t2=$($REAL +%s%N)
       echo "$a $(( (t1 - t0) / 1000000 )) $b $(( (t2 - t1) / 1000000 ))" )
  show "braces: '$(echo $r | awk '{print $1}')' after $(echo $r | awk '{print $2}') ms;  unbraced: '$(echo $r | awk '{print $3}')' after $(echo $r | awk '{print $4}') ms (the fake job sleeps 10 s real)"
  test "$(echo $r | awk '{print $2}')" -lt 3000 && ok "braces form returned in under 3 s while the job kept running" || bad "braces form was slow"
  test "$(echo $r | awk '{print $4}')" -gt 7000 && ok "unbraced form blocked for the whole job (negative control: the test can see the bug)" || bad "unbraced form did not block"
fi

if want 5; then title "5. drive.sh refuses on the rental: the guard halts, copies the logs back, destroys; nothing runs"
  for c in torch28 smoke cc75 pipfail; do reset
    case $c in torch28) echo "2.8.0+cu128" > "$FAKE/py/torch-install"; want_re='FAILED torch check';; smoke) : > "$FAKE/py/smoke-fail"; want_re='FAILED smoke did not print';; cc75) echo "7 5" > "$FAKE/py/cc"; want_re='FAILED torch check';; pipfail) : > "$FAKE/py/pip-fail"; want_re='FAILED pip install torch==2.11.0';; esac
    runjob h7-dirh6-1-start; O=$T/out/h7-dirh6-1-start.txt; wait_end 120 && ok "[$c] guard ended" || bad "[$c] guard did not end"
    has "[$c] start reported START-FAIL" "$O" '^START-FAIL: END FAILED'; has "[$c] progress file says why" "$T/G/out/W/drive-state.txt" "$want_re"
    chk "[$c] no seed run was launched" test "$(grep -c ' LAUNCH ' "$T/G/out/W/drive-state.txt")" = 0; chk "[$c] instance destroyed by exact id" test "$(destroyed)" = "7000001 "
    has "[$c] copy-back verified" "$T/G/log.txt" 'COPY-CHECK: [0-9]+ of [0-9]+ files arrived and match'
    [ $c = smoke ] && { runjob h7-dirh6-2-collect; C=$T/repo/$A/run-vast/COLLECT.txt; excerpt "$C" 'smoke|Traceback|Assertion' 5; has "[smoke] collect prints the first traceback verbatim" "$C" 'AssertionError: FAKE smoke failure'; has "[smoke] and says stop" "$C" 'smoke: FAILED, first traceback verbatim'; }
  done
fi

if want 6; then title "6. one seed dies (rc 1): recorded as DIED, the other 3 finish, still verified and destroyed"
  reset; echo 600 > "$FAKE/py/run-seconds"; echo die > "$FAKE/py/run-15"; runjob h7-dirh6-1-start; wait_end 240 && ok "guard ended" || bad "guard did not end"
  has "END DONE" "$T/G/END" '^END DONE'; has "drive-state records DIED s15" "$T/G/out/W/drive-state.txt" 'DIED s15 \(rc 1'; has "copy-back saw the DIED record" "$T/G/log.txt" 's15: DIED on the rental'
  chk "destroyed after the verified copy" test "$(destroyed)" = "7000001 "; runjob h7-dirh6-2-collect; C=$T/repo/$A/run-vast/COLLECT.txt; excerpt "$C" 's15|seed runs' 3
  has "collect: 3 finished, 1 died" "$C" '4 launched, 3 finished, 1 died'; has "collect: s15 has no result file" "$C" 's15: no result file'
fi

if want 7; then title "7. money stop \$3.00: runs halted by exact pid, partial copy-back verified, destroyed"
  reset; for s in 13 14 15 16; do echo hang > "$FAKE/py/run-$s"; done; runjob h7-dirh6-1-start; has "STARTED" "$T/out/h7-dirh6-1-start.txt" '^STARTED$'; wait_launches 4 && ok "all 4 runs launched before the clock jump" || bad "not all runs launched"
  echo $((9 * 3600)) > "$FAKE/clock-jump"   # the virtual clock jumps 9 h ahead: 9 h x 0.35 = 3.15 dollars
  wait_end 120 && ok "guard ended" || bad "guard did not end"; excerpt "$T/G/log.txt" 'GUARD|HALT|halt|COPY-CHECK|DESTROYED' 8
  has "END BUDGET-STOP" "$T/G/END" '^END BUDGET-STOP spent'; has "halt message: TERM sent to 6 pids (drive, 4 runs, monitor)" "$T/G/log.txt" 'halt: TERM to 6 pids'
  has "the halt line is in the copied progress file" "$T/G/out/W/drive-state.txt" 'HALT BUDGET-STOP'
  alive=0; while read -r k n p; do [ "$k" = run ] && alive $p && alive=$((alive+1)); done < "$T/G/out/W/pids.txt"; test $alive = 0 && ok "none of the 4 run pids is alive after the halt" || bad "$alive runs still alive"
  has "partial copy-back verified" "$T/G/log.txt" 'COPY-CHECK: [0-9]+ of [0-9]+ files arrived and match'; chk "destroyed by exact id" test "$(destroyed)" = "7000001 "
  runjob h7-dirh6-2-collect; C=$T/repo/$A/run-vast/COLLECT.txt; has "collect: 4 launched, 0 finished, 0 died; s13 has no result file" "$C" '4 launched, 0 finished, 0 died'; has "  s13 no result file" "$C" 's13: no result file'
fi

if want 8; then title "8. time cap (1.5 x the card's estimate) and STALL (30 min, no log growth, GPU idle)"
  reset; for s in 13 14 15 16; do echo hang > "$FAKE/py/run-$s"; done; runjob h7-dirh6-1-start; wait_launches 4 && ok "[time] all 4 runs launched before the clock jump" || bad "[time] not all runs launched"; echo $((8 * 3600)) > "$FAKE/clock-jump"   # 8 h x 0.35 = 2.80 dollars: under the money stop, over 1.5 x 5.08 h
  wait_end 120 && ok "[time] guard ended" || bad "[time] guard did not end"; has "[time] END TIME-STOP" "$T/G/END" '^END TIME-STOP spent'; chk "[time] destroyed" test "$(destroyed)" = "7000001 "
  reset; for s in 13 14 15 16; do echo hang > "$FAKE/py/run-$s"; done; echo 0 > "$FAKE/gpu/util"; runjob h7-dirh6-1-start
  wait_end 240 && ok "[stall] guard ended" || bad "[stall] guard did not end"; has "[stall] END STALL" "$T/G/END" '^END STALL spent'; has "[stall] guard said why" "$T/G/log.txt" 'GUARD STALL: no log growth for 30 min, GPU idle'; chk "[stall] destroyed" test "$(destroyed)" = "7000001 "
fi

if want 9; then title "9. PRELAUNCH-STOP: drive.sh stuck before the first launch (smoke hangs), guard stops it after 45 min"
  reset; : > "$FAKE/py/smoke-hang"; runjob h7-dirh6-1-start; has "start did not claim success" "$T/out/h7-dirh6-1-start.txt" '^STARTED-NO-LAUNCH-YET$'
  wait_end 240 && ok "guard ended" || bad "guard did not end"; has "END PRELAUNCH-STOP" "$T/G/END" '^END PRELAUNCH-STOP spent'; chk "destroyed" test "$(destroyed)" = "7000001 "; has "logs came back" "$T/G/out/W/drive-state.txt" 'HALT PRELAUNCH-STOP'
fi

if want 10; then title "10. host lost: guard stops (not destroys) the instance, flags the Director; collect uses the 30-minute snapshot"
  reset; echo 2400 > "$FAKE/py/run-seconds"; runjob h7-dirh6-1-start; wait_file "$T/G/snap/W/drive-state.txt" 120 && ok "a snapshot exists before the host dies" || bad "no snapshot"; : > "$FAKE/ssh/dead"
  wait_end 120 && ok "guard ended" || bad "guard did not end"; excerpt "$T/G/log.txt" 'no ssh answer|GUARD|STOPPED' 8
  has "END HOST-FAIL-STOPPED-NOT-DESTROYED" "$T/G/END" '^END HOST-FAIL-STOPPED-NOT-DESTROYED'; chk "stopped, not destroyed" test "$(stopped)" = "7000001 " -a -z "$(destroyed)"
  runjob h7-dirh6-2-collect; C=$T/repo/$A/run-vast/COLLECT.txt; has "collect prints FLAG-DIRECTOR" "$T/out/h7-dirh6-2-collect.txt" 'FLAG-DIRECTOR'; has "collect says its files are the snapshot" "$C" 'files from the 30-minute SNAPSHOT \(NOT checked'
fi

if want 11; then title "11. copy-back mismatch (a file grew after the manifest): first copy_back fails, second passes; permanent mismatch keeps the rental stopped"
  reset; echo 600 > "$FAKE/py/run-seconds"; echo 1 > "$FAKE/ssh/mutate-on-tar"; runjob h7-dirh6-1-start; wait_end 240 && ok "[retry] guard ended" || bad "[retry] guard did not end"; excerpt "$T/G/log.txt" 'copy-back try|COPY-CHECK|DESTROYED' 8
  has "[retry] a mismatch was seen and logged" "$T/G/log.txt" 'copy-back try [0-9]: [0-9]+ of [0-9]+ files match'; has "[retry] second copy_back matched" "$T/G/log.txt" 'COPY-CHECK: ([0-9]+) of \1 files arrived and match'; has "[retry] END DONE" "$T/G/END" '^END DONE spent'; chk "[retry] destroyed" test "$(destroyed)" = "7000001 "
  reset; echo 600 > "$FAKE/py/run-seconds"; echo 99 > "$FAKE/ssh/mutate-on-tar"; runjob h7-dirh6-1-start; wait_end 240 && ok "[perm] guard ended" || bad "[perm] guard did not end"; excerpt "$T/G/log.txt" 'COPY-CHECK|STOPPED|GUARD-END' 6
  has "[perm] COPY-CHECK FAIL logged" "$T/G/log.txt" 'COPY-CHECK FAIL: [0-9]+ of [0-9]+ files match'; has "[perm] END DONE-STOPPED-NOT-DESTROYED" "$T/G/END" '^END DONE-STOPPED-NOT-DESTROYED'; chk "[perm] NOT destroyed, stopped" test -z "$(destroyed)" -a "$(stopped)" = "7000001 "
fi

if want 12; then title "12. destroy and stop only ids this task created (rentals.txt)"
  reset; echo "7000001 0.35 $($REAL +%s)" > "$T/G/rentals.txt"; mkdir -p "$FAKE/vast/instances/999"; echo other > "$FAKE/vast/instances/999/label"; echo running > "$FAKE/vast/instances/999/status"; echo 0 > "$FAKE/vast/instances/999/polls"
  ( . "$KITSRC/vcommon.sh"; destroy 999; echo "destroy rc $?"; stop_inst 999; echo "stop rc $?" ) > "$T/out/safety.txt" 2>&1; excerpt "$T/out/safety.txt" 'REFUSED|rc' 4
  has "destroy 999 refused" "$T/out/safety.txt" 'REFUSED destroy 999: not created by this task'; has "stop 999 refused" "$T/out/safety.txt" 'REFUSED stop 999: not created by this task'; has "both returned 1" "$T/out/safety.txt" 'destroy rc 1'
  test ! -s "$FAKE/vast/destroyed.log" && test ! -s "$FAKE/vast/stopped.log" && ok "the fake vast saw no destroy or stop call at all" || bad "vast was called"
fi

if want 13; then title "13. start job killed after the rental exists but before its guard: (a) TERM to vstart.sh (a process-group kill), (b) SIGALRM to the job wrapper only (what the watcher's 75-minute alarm does)"
  # (a) the wrapper's child is the vstart.sh process; a group kill delivers TERM to it and vstart's trap must destroy the rental
  reset; echo 1000000 > "$FAKE/vast/loading-polls"; j=$(job h7-dirh6-1-start); pushd "$T/repo" > /dev/null; bash "$j" > "$T/out/killed.txt" 2>&1 & echo $! > "$T/out/killed.pid"; popd > /dev/null
  wp=$(cat "$T/out/killed.pid"); for w in $(seq 1 60); do [ -s "$T/G/rentals.txt" ] && break; /usr/bin/sleep 0.5; done; /usr/bin/sleep 1
  vp=$(pgrep -P "$wp" -f 'sleeph6r/vstart\.sh' | head -1); [ -n "$vp" ] && ok "[a] found the vstart.sh child (pid $vp) of the job wrapper (pid $wp)" || bad "[a] no vstart.sh child"
  kill -TERM "$vp" 2>/dev/null; for w in $(seq 1 60); do alive "$vp" || break; /usr/bin/sleep 1; done; alive "$vp" && bad "[a] vstart.sh still alive after TERM" || ok "[a] vstart.sh exited after TERM"
  for w in $(seq 1 30); do alive "$wp" || break; /usr/bin/sleep 1; done
  excerpt "$T/G/log.txt" 'start ended|DESTROYED' 4
  has "[a] cleanup ran" "$T/G/log.txt" 'start ended before the guard was running: destroying 7000001'; chk "[a] instance destroyed" test "$(destroyed)" = "7000001 "; test "$(awk 'NR==1{print NF}' "$T/G/rentals.txt")" = 4 && ok "[a] rentals.txt has its end time" || bad "[a] no end time"
  # (b) SIGALRM kills only the job wrapper (perl alarm + exec); vstart.sh is left running on its own and must finish the job (no hang, no leaked rental)
  reset; echo 1000000 > "$FAKE/vast/loading-polls"; j=$(job h7-dirh6-1-start); pushd "$T/repo" > /dev/null; bash "$j" > "$T/out/alarm.txt" 2>&1 & echo $! > "$T/out/alarm.pid"; popd > /dev/null
  wp=$(cat "$T/out/alarm.pid"); for w in $(seq 1 60); do [ -s "$T/G/rentals.txt" ] && break; /usr/bin/sleep 0.5; done; /usr/bin/sleep 1
  vp=$(pgrep -P "$wp" -f 'sleeph6r/vstart\.sh' | head -1); kill -ALRM "$wp" 2>/dev/null; /usr/bin/sleep 1
  alive "$wp" && bad "[b] job wrapper survived SIGALRM" || ok "[b] job wrapper died of SIGALRM"
  [ -n "$vp" ] && alive "$vp" && ok "[b] vstart.sh (pid $vp) is still running on its own" || bad "[b] vstart.sh died with its wrapper"
  for w in $(seq 1 120); do alive "$vp" || break; /usr/bin/sleep 1; done; alive "$vp" && bad "[b] orphaned vstart.sh never finished" || ok "[b] orphaned vstart.sh finished by itself"
  excerpt "$T/G/log.txt" 'HOST-FAIL|DESTROYED' 6
  has "[b] HOST-FAIL logged by the orphan" "$T/G/log.txt" 'HOST-FAIL: no rental got as far as launching'; chk "[b] all three rentals destroyed by exact id" test "$(destroyed)" = "7000001 7000002 7000003 "
fi

if want 14; then title "14. no host answers ssh, 3 hosts in a row: each destroyed, HOST-FAIL, spend recorded"
  reset; echo 1000000 > "$FAKE/vast/loading-polls"; runjob h7-dirh6-1-start; excerpt "$T/G/log.txt" 'rental [0-9]|HOST-FAIL|DESTROYED' 10
  has "3 rentals tried" "$T/G/log.txt" 'rental 3: instance 7000003'; has "HOST-FAIL logged" "$T/G/log.txt" 'HOST-FAIL: no rental got as far as launching'; chk "all three destroyed by exact id" test "$(destroyed)" = "7000001 7000002 7000003 "
  reset; echo 3 > "$FAKE/vast/create-fail"; runjob h7-dirh6-1-start; has "create failing on all 3 offers: HOST-FAIL and nothing destroyed or left" "$T/G/log.txt" 'HOST-FAIL'; chk "no instances exist" test -z "$(ls "$FAKE/vast/instances" 2>/dev/null)"
fi

if want 15; then title "15. the read-only Mac input check job (000-bash-h7-dirh6-inputs): match, then a tampered checkpoint"
  reset; runjob 000-bash-h7-dirh6-inputs; O=$T/out/000-bash-h7-dirh6-inputs.txt; excerpt "$O" 'of 4|sealed' 6
  has "all 4 match" "$O" '^4 of 4 Mac checkpoints match their seals'; hasnt "prints no key or credential path content" "$O" 'BEGIN|PRIVATE|api'
  echo tampered >> "$T/models/rsn358u/loop-s16/final.pt"; runjob 000-bash-h7-dirh6-inputs; has "a tampered copy is caught" "$O" '^3 of 4 Mac checkpoints match their seals'; has "  and named" "$O" 'loop-s16/final.pt: sealed .*DOES NOT MATCH'
fi

kill_fakes; rm -rf /root/r
echo; echo "SUMMARY: $PASS checks passed, $FAILS failed (scratch folder $T)"; [ $FAILS = 0 ]
