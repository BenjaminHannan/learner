#!/bin/bash
# Dry-run tests for kit opcpu against a FAKE vastai, a FAKE ssh (the "rental" is a scratch folder on this box), a FAKE python (answers the sealed scripts in
# shape only), and a FAKE clock and sleep. Written by the Opus manager session, 2026-09-29, following handoff/kit/sleeph6r/test. Linux. Nothing here rents
# anything, reads any key, or contacts vast or any host. It never touches /root/r or any real rental folder: the rental is $T/box.
# The kit scripts run UNCHANGED (only their own ...OPC environment overrides point them at test folders). The queue jobs are run from the fenced bash
# blocks of the real queue files (handoff/queue/opus-cpu-vast-*.md) with PIN set to a fake repo's commit. The fake repo holds the REAL sealed files
# (so every sha256sum -c seal check on the "rental" is the real one), except that the qual-loop / qual-plain / runs sha lines are rewritten to match the
# fake Mac nets (and the seal lines of that one file with them): the real Mac nets are not here.
# Usage: TMPDIR=<scratch dir> bash handoff/kit/opcpu/test/fake_run.sh [scenario-number ...]     (no argument = all)
set -u
TESTDIR=$(cd "$(dirname "$0")" && pwd); KITSRC=$(cd "$TESTDIR/.." && pwd); REPOSRC=$(cd "$KITSRC/../../.." && pwd)
T=$(mktemp -d "${TMPDIR:-/tmp}/opctest.XXXXXX"); REAL=/usr/bin/date
export FAKE=$T/fake GOPC=$T/G BROPC=$T/box MBOPC=$T/mac KEYOPC=$T/key/id_test PYMOPC=/usr/bin/python3 FAKE_SPEED=${FAKE_SPEED:-60} OPC_MINCORES=1 OPC_BOOTPY=$TESTDIR/bin/python
export PATH=$TESTDIR/bin:$PATH
FR=artifacts/claude-fewex-20260927; OUTD=artifacts/opus-manager-20260929/cpu-vast
PASS=0; FAILS=0
ok()  { PASS=$((PASS+1)); echo "   ok    $*"; }
bad() { FAILS=$((FAILS+1)); echo "   FAIL  $*"; }
chk() { d=$1; shift; if "$@" > /dev/null 2>&1; then ok "$d"; else bad "$d"; fi; }
has() { if grep -q -E -- "$3" "$2" 2>/dev/null; then ok "$1"; else bad "$1 (no match for /$3/ in $2)"; fi; }
hasnt() { if grep -q -E -- "$3" "$2" 2>/dev/null; then bad "$1 (found /$3/ in $2)"; else ok "$1"; fi; }
show() { echo "   | $(echo "$*" | cut -c1-230)"; }
excerpt() { f=$1; shift; grep -E -- "$1" "$f" 2>/dev/null | head -${2:-6} | while IFS= read -r l; do show "$l"; done; }

# ---------- a fake Mac: the Mac-only nets, made of random bytes (made once, copied fresh for every scenario) ----------
mkmac() {
  rm -rf "${1:?}"; M=$1/$FR
  for S in 0 1; do for AR in loop plain; do
    for d in runs/qual-$AR-s$S runs/$AR-s$S; do mkdir -p "$M/$d"; head -c 4000 /dev/urandom > "$M/$d/source.pt"; echo "{\"arm\": \"$AR\", \"seed\": $S, \"fake\": \"$d\"}" > "$M/$d/source.json"; done
    done; mkdir -p "$M/eq-runs/plain-s$S-pre"; head -c 5000 /dev/urandom > "$M/eq-runs/plain-s$S-pre/k16384.pt"; done
}
# ---------- a fake project (git repo with an origin) built from the real files ----------
build_repo() {
  mkdir -p "$T/origin.git" "$T/repo" "$T/key"; git init -q --bare "$T/origin.git"
  ( cd "$REPOSRC" && git archive HEAD scripts artifacts/claude-fewex-20260927 artifacts/claude-distill-20260928 artifacts/claude-dir-ks-20260928 artifacts/claude-sweep-s2-20260929 \
      artifacts/claude-dir-trn-20260929 artifacts/claude-dir-pond-20260928 artifacts/claude-dir-h12-stop-20260928 | tar -x -C "$T/repo"
    mkdir -p "$T/repo/handoff/queue"; cp handoff/queue/opus-cpu-vast-*.md "$T/repo/handoff/queue/"
    tar -cf - --exclude=handoff/kit/opcpu/test handoff/kit/opcpu | tar -x -C "$T/repo" )
  mkmac "$T/mac.orig"
  # rewrite the sha lines of the nets that exist only on the Mac to match the fake ones (and the seal lines of that one file)
  python3 - "$T/repo" "$T/mac.orig" <<'PY'
import hashlib, sys, pathlib, re
repo, mac = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
FR = "artifacts/claude-fewex-20260927"
def rewrite(f, fn):
    p = repo / f; out = []
    for l in p.read_text().splitlines():
        h, _, path = l.partition("  "); out.append(fn(h, path, l))
    p.write_text("\n".join(out) + "\n")
def eqfix(h, path, l):
    m = re.match(FR + r"/runs/(qual-(?:loop|plain)-s\d|(?:loop|plain)-s\d)/source\.json$", path)
    return sha(mac / FR / "runs" / m.group(1) / "source.json") + "  " + path if m else l
rewrite(FR + "/SHA256-EQ-RAW.txt", eqfix); rewrite(FR + "/SHA256-RAW.txt", eqfix)
def ckfix(h, path, l):
    m = re.match(r"qual-(loop-s\d)/source\.pt$", path)
    return sha(mac / FR / "runs" / ("qual-" + m.group(1)) / "source.pt") + "  " + path if m else l
rewrite("artifacts/claude-distill-20260928/checkpoints-sha256.txt", ckfix)
new = sha(repo / FR / "SHA256-EQ-RAW.txt")
for s in repo.glob("artifacts/*/SEAL*.txt"):
    t = s.read_text()
    if FR + "/SHA256-EQ-RAW.txt" in t:
        s.write_text(re.sub(r"[0-9a-f]{64}(  " + re.escape(FR) + r"/SHA256-EQ-RAW\.txt)", new + r"\1", t))
PY
  echo "ssh-ed25519 AAAAFAKEFAKEFAKE opc-test-only" > "$T/key/id_test.pub"; echo "not a key" > "$T/key/id_test"
  cd "$T/repo" && git init -q -b main && git add -A && git -c user.name=t -c user.email=t@t commit -q -m "test repo without the s1 folder"
  PIN0=$(git rev-parse HEAD)
  ( cd "$REPOSRC" && git archive HEAD artifacts/claude-s1-d4-20260929 | tar -x -C "$T/repo" )
  git add -A && git -c user.name=t -c user.email=t@t commit -q -m "test repo" \
    && git remote add origin "$T/origin.git" && git -c push.negotiate=false push -q origin main && git -c push.negotiate=false push -q origin main:builder-outbox && git fetch -q origin
  PIN=$(git rev-parse HEAD); cd "$TESTDIR"
}
job() {   # job <queue-file-name> <pin>: extract the fenced bash block, set its PIN, write it as <name>.bo.sh
  awk '/^```bash/{f=1;next} /^```/{f=0} f' "$T/repo/handoff/queue/$1.md" | sed "s/PIN=[^ ;]*/PIN=${2:-$PIN}/" > "$T/$1.bo.sh"; echo "$T/$1.bo.sh"; }
runjob() { j=$(job "$1" "${3:-$PIN}"); ( cd "$T/repo" && bash "$j" ) > "$T/out/$2.txt" 2>&1; rc=$?; echo $rc > "$T/out/$2.rc"; }   # runjob <queue file> <out name> [pin]
kill_fakes() {
  for w in 1 2 3 4 5 6 7 8; do
    lp=$(pgrep -f "($T/box|$T/G/vguard|$T/.*\.bo\.sh|opcpu/vstart\.sh|venv/bin/python)" | grep -v -x "$$" | tr '\n' ' '); [ -z "${lp// /}" ] && break
    for p in $lp; do kill -TERM "$p" 2>/dev/null; done; /usr/bin/sleep 0.5; done
  return 0; }
reset() {
  kill_fakes
  rm -rf "${T:?}/box" "${T:?}/G" "${T:?}/fake" "${T:?}/out" "${T:?}/repo/$OUTD"; mkdir -p "$T/box" "$T/G" "$FAKE/vast" "$FAKE/ssh" "$FAKE/py" "$T/out"
  cp "$TESTDIR/fixtures/offers.json" "$FAKE/vast/offers.json"; echo 23.73 > "$FAKE/vast/credit"
  rm -rf "${MBOPC:?}"; cp -a "$T/mac.orig" "$MBOPC"
  unset CAPSTOPOPC BASEHOPC TIMECAPOPC
  export FAKE_V0=$($REAL +%s) FAKE_R0=$($REAL +%s%N)
}
wait_end() { for w in $(seq 1 ${1:-240}); do [ -s "$T/G/END" ] && return 0; /usr/bin/sleep 1; done; return 1; }
destroyed() { { tr '\n' ' ' < "$FAKE/vast/destroyed.log"; } 2>/dev/null | sed 's/destroyed //g'; }
stopped() { { tr '\n' ' ' < "$FAKE/vast/stopped.log"; } 2>/dev/null | sed 's/stopped //g'; }
title() { echo; echo "== $1"; }
ONLY=" $* "
want() { [ -z "${ONLY// /}" ] && return 0; case "$ONLY" in *" $1 "*) return 0;; esac; return 1; }
nodrive() { ! pgrep -f "$T/box.*(drive\.sh|venv/bin/python)|box/job-" > /dev/null; }

echo "kit opcpu dry-run tests, $($REAL -u +%FT%TZ) (real clock; the fakes run a virtual clock $FAKE_SPEED times faster)"
build_repo; echo "test repo $T/repo, PIN $PIN (PIN0 without the s1 folder: $PIN0)"

if want 0; then title "0. static checks"
  for f in vcommon.sh vstart.sh vguard.sh vcollect.sh box/drive.sh box/pack.sh box/jlib.sh box/job-ks.sh box/job-s2think.sh box/job-trn.sh box/job-pond.sh box/job-doubt.sh box/job-s1.sh; do chk "bash -n $f" bash -n "$KITSRC/$f"; done
  for f in fake_run.sh bin/vastai bin/ssh bin/date bin/sleep bin/caffeinate; do chk "bash -n test/$f" bash -n "$TESTDIR/$f"; done
  chk "fake python parses" python3 -c "import ast; ast.parse(open('$TESTDIR/bin/python').read())"
  hasnt "no bash-4-only syntax in the Mac-side scripts (declare -A, mapfile, readarray, wait -n, |&, \${x,,}, &>>)" <(cat "$KITSRC"/v*.sh) 'declare -A|mapfile|readarray|wait -n|\|&|\$\{[a-zA-Z_]*(,,|\^\^)|&>>'
  hasnt "the Mac-side scripts never use the timeout command (macOS has none)" <(cat "$KITSRC"/v*.sh | grep -v '^#') '(^|[ (;|&])timeout '
  hasnt "kit never reads a vast key or ~/.config/vastai" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh | grep -v '^#') 'config/vastai|\.vast_api_key|vast.*api.?key'
  hasnt "the only ssh key file read is the .pub (no cat of a private key)" <(cat "$KITSRC"/*.sh | grep -v '^#') 'cat "?\$KEY"?( |$)'
  hasnt "the launch line has no unbraced form" <(grep -h 'setsid nohup' "$KITSRC"/*.sh | grep -v '^#') '&& setsid nohup'
  hasnt "guard and drive read no GPU utilisation" <(cat "$KITSRC/vguard.sh" "$KITSRC/box/drive.sh" | grep -v '^#') 'utilization'
  hasnt "no git commit / push / checkout / add / reset in the kit scripts" <(cat "$KITSRC"/*.sh "$KITSRC"/box/*.sh | grep -v '^#') 'git (commit|push|checkout|add|reset)'
  hasnt "no job opens holdout / test.pt / readpanel / blind panels" <(cat "$KITSRC"/box/job-*.sh | grep -v '^#') 'holdout|test\.pt|readpanel|blind'
  has "vcollect writes only under the cpu-vast folder" "$KITSRC/vcommon.sh" '^A=artifacts/opus-manager-20260929/cpu-vast'
  has "the collect queue file's PUSH is only that folder" "$T/repo/handoff/queue/opus-cpu-vast-2-collect.md" '^PUSH: artifacts/opus-manager-20260929/cpu-vast$'
  has "collect file is HELD" "$T/repo/handoff/queue/opus-cpu-vast-2-collect.md" '^STATUS: HELD'; hasnt "no LOAD-LIGHT line in either queue file" <(cat "$T"/repo/handoff/queue/opus-cpu-vast-*.md) 'LOAD-LIGHT'
  has "start file has BASH-ONLY: yes" "$T/repo/handoff/queue/opus-cpu-vast-1-start.md" '^BASH-ONLY: yes'; has "start file has the PIN placeholder" "$T/repo/handoff/queue/opus-cpu-vast-1-start.md" 'PIN=__PIN__'
fi

if want 1; then title "1. happy path: start, guard, verified copy, destroy by exact id, collect, second start refused"; reset
  runjob opus-cpu-vast-1-start start
  has "start prints STARTED" "$T/out/start.txt" '^STARTED$'; excerpt "$T/out/start.txt" 'offers|rental 1|estimate|inputs|LAUNCH|TORCH|INPUTS' 12
  has "the cheapest \$/h per core was rented (offer 2006: 40 cores at \$0.15/h)" "$FAKE/vast/calls.log" 'create instance 2006 .*--label opus-cpu'
  hasnt "the excluded host, the too-few-core and the over-price offers were never created" "$FAKE/vast/calls.log" 'create instance (2003|2004|2005)'
  has "the image is a plain pytorch image" "$FAKE/vast/calls.log" 'create instance 2006 --image pytorch/pytorch'
  chk "the rental venv python is the FAKE (the real pip/python never runs in these tests)" test "$(readlink "$T/box/venv/bin/python")" = "$TESTDIR/bin/python"
  has "drive-state: torch check ok (2.14.0+cpu, cuda False)" "$T/box/W/drive-state.txt" 'TORCH torch 2.14.0\+cpu numpy 2.4.6 cuda False'
  has "drive-state: inputs hash-checked on the rental (4 + 4 plain + 6 trn = 14 files)" "$T/box/W/drive-state.txt" 'INPUTS 14 files match'
  wait_end 240; show "END: $(cat "$T/G/END" 2>/dev/null)"
  has "guard ended DONE" "$T/G/END" '^END DONE spent'
  n=$(grep -c ' JOB .* END rc 0$' "$T/box/W/drive-state.txt"); [ "$n" = 10 ] && ok "all 10 jobs ended rc 0" || bad "jobs ended rc 0: $n of 10"
  has "wave 1 launched ks, pond a/b/c/z, s1-loop, s1-plain before LAUNCHED-ALL" "$T/box/W/drive-state.txt" 'LAUNCH s1-plain'
  has "COPY-CHECK passed" "$T/G/log.txt" 'COPY-CHECK: all jobs accounted for'
  has "destroyed by exact id 7000001" <(destroyed) '^7000001 $'; [ -z "$(stopped)" ] && ok "nothing was stopped-not-destroyed" || bad "stopped: $(stopped)"
  chk "no .pt file was copied back" test -z "$(find "$T/G/out" -name '*.pt')"
  chk "the rental did have .pt files (nets stay there)" test -n "$(find "$T/box" -name '*.pt')"
  chk "ks nets are where the later jobs read them (KS_NETS)" test -f "$T/box/premonition-ks/nets/loop-s1-pre/k16384.pt"
  hasnt "no .pt in the copied manifest" "$T/G/out/W/MANIFEST.sha256" '\.pt$'
  mkdir -p "$T/box/out/planted"; head -c 100 /dev/urandom > "$T/box/out/planted/net.pt"; echo x > "$T/box/out/planted/holdout.json"; echo x > "$T/box/out/planted/blind-panel.json"; echo ok > "$T/box/out/planted/fine.json"
  bash "$KITSRC/box/pack.sh" "$T/box" 2>/dev/null | tar -t > "$T/packed.lst"
  has "pack.sh keeps a normal small file" "$T/packed.lst" 'planted/fine.json'; hasnt "pack.sh drops a .pt, a holdout file and a blind panel file" "$T/packed.lst" 'planted/(net.pt|holdout.json|blind-panel.json)'
  has "pack.sh recorded them as excluded" "$T/box/W/EXCLUDED.txt" 'planted/net.pt pt'
  for arm in a b c z; do chk "pond-$arm ran in its own private folder" test -d "$T/box/premonition-pond-$arm/artifacts/claude-dir-pond-20260928/eq-runs/pond-$arm-pre-s0"; done
  chk "s1-loop and s1-plain ran in private folders" test -d "$T/box/premonition-s1-loop" -a -d "$T/box/premonition-s1-plain"
  has "pond-doubt saw the arms through links" "$T/box/W/pond-doubt.out" 'pond-b seed 1 pid'; hasnt "pond-doubt skipped no arm" "$T/box/W/pond-doubt.out" 'not finished'
  has "s2think traced the rebuilt nets (k64, k16384)" "$T/box/W/s2think.out" 'seed 1 k16384 ck=.*/premonition-ks/nets/loop-s1-pre/k16384.pt'
  has "trn-decode ran (the fake checks it found the loop k16384 link)" "$T/box/W/trn-decode.out" 'sums pid'
  runjob opus-cpu-vast-2-collect collect
  has "collect prints COLLECTED" "$T/out/collect.txt" '^COLLECTED$'; excerpt "$T/out/collect.txt" '^(ks-1|s2think|trn|pond|s1)' 12
  for f in ks-1-lead0/artifacts/claude-dir-ks-20260928/lead0/s0-k64.json ks-1-lead0/artifacts/claude-dir-ks-20260928/prep/s1.json s2think/artifacts/claude-sweep-s2-20260929/JUDGE.txt \
           trn-decode/artifacts/claude-dir-trn-20260929/run/mazes.json pond-a-dev/artifacts/claude-dir-pond-20260928/JUDGE-dev-a.json pond-z-dev/artifacts/claude-dir-pond-20260928/SHA256-pond-z-dev.txt \
           pond-doubt/artifacts/claude-dir-pond-20260928/doubt/DOUBT-TABLE-c.txt s1-loop/artifacts/claude-s1-d4-20260929/eq-runs/s1-loop-pre-s0/vote.json s1-plain/artifacts/claude-s1-d4-20260929/SHA256-s1-plain-dev.txt \
           _rental/COLLECT.txt _rental/DEVIATIONS.md _rental/drive-state.txt _rental/INPUTS.txt _rental/ks-1-lead0.stdout.txt; do chk "collected $f" test -s "$T/repo/$OUTD/$f"; done
  chk "no .pt in the repo folder" test -z "$(find "$T/repo/$OUTD" -name '*.pt')"
  outside=$(cd "$T/repo" && git status --porcelain -uall | grep -v "$OUTD" | head -3); [ -z "$outside" ] && ok "nothing outside artifacts/opus-manager-20260929/cpu-vast/ changed in the repo" || bad "changed outside: $outside"
  sealed=$(cd "$T/repo" && git status --porcelain -uall | grep -E "^.. (artifacts/claude-|scripts/)" | head -3); [ -z "$sealed" ] && ok "no sealed folder touched" || bad "sealed touched: $sealed"
  runjob opus-cpu-vast-1-start start2; has "a second start is refused (DUPLICATE)" "$T/out/start2.txt" '^DUPLICATE'
fi

if want 2; then title "2. start refusals: nothing is rented"
  refuse() { # refuse <label> <pattern>: the start job ran, printed the pattern, created no instance and no rental record
    has "$1" "$T/out/start.txt" "$2"; hasnt "  nothing rented ($1)" "$FAKE/vast/calls.log" 'create instance'; [ ! -e "$T/G/rentals.txt" ] && ok "  no rental record" || bad "  rental record exists"; }
  reset; rm -f "${MBOPC:?}/$FR/runs/qual-loop-s1/source.pt"; runjob opus-cpu-vast-1-start start; refuse "a missing Mac input (qual-loop-s1 source.pt)" 'STOP: Mac input missing'
  reset; echo tampered >> "$MBOPC/$FR/runs/qual-loop-s0/source.json"; runjob opus-cpu-vast-1-start start; refuse "a Mac source.json that does not match SHA256-EQ-RAW.txt" 'source.json sha256 .* does not match the sealed'
  reset; echo tampered >> "$MBOPC/$FR/runs/qual-loop-s1/source.pt"; runjob opus-cpu-vast-1-start start; refuse "a Mac source.pt that does not match checkpoints-sha256.txt" 'source.pt sha256 .* does not match the sealed'
  reset; echo 2.10 > "$FAKE/vast/credit"; runjob opus-cpu-vast-1-start start; has "credit under \$2.50" "$T/out/start.txt" 'STOP: credit .*under'; hasnt "  nothing rented (credit)" "$FAKE/vast/calls.log" 'create instance'
  reset; mkdir -p "$FAKE/vast/instances/6999999"; echo opus-cpu > "$FAKE/vast/instances/6999999/label"; echo running > "$FAKE/vast/instances/6999999/status"; echo 9 > "$FAKE/vast/instances/6999999/polls"
  runjob opus-cpu-vast-1-start start; refuse "a live instance with the label" '^DUPLICATE: live instance'
  reset; runjob opus-cpu-vast-1-start start "$PIN0"; refuse "a pinned commit that lacks the s1 seal" 'STOP: pinned commit .* has no artifacts/claude-s1-d4-20260929/SEAL-code.sha256.txt'
  reset; python3 -c "import json; d=json.load(open('$FAKE/vast/offers.json')); json.dump([o for o in d if o['id'] in (2003,2004,2005)], open('$FAKE/vast/offers.json','w'))"
  runjob opus-cpu-vast-1-start start; has "no offer fits (over-price, excluded host, too few cores)" "$T/out/start.txt" 'STOP: no offer'; hasnt "  nothing rented (no offer)" "$FAKE/vast/calls.log" 'create instance'
  reset; BASEHOPC=20 runjob opus-cpu-vast-1-start start; has "no offer fits the estimate x price <= 0.8 x cap rule (est 20 h)" "$T/out/start.txt" 'STOP: no offer'; hasnt "  nothing rented (fit rule)" "$FAKE/vast/calls.log" 'create instance'
fi

if want 3; then title "3. budget stop: jobs still running, jobs halted, partial copy verified, destroyed"; reset
  export CAPSTOPOPC=0.9 BASEHOPC=1; touch "$FAKE/py/hang"
  runjob opus-cpu-vast-1-start start; has "start prints STARTED" "$T/out/start.txt" '^STARTED$'
  /usr/bin/sleep 3; echo 22000 > "$FAKE/clock-jump"      # 6.1 h at $0.15/h = $0.92 >= the $0.90 cap (the 7 h time cap is not reached)
  wait_end 120; show "END: $(cat "$T/G/END" 2>/dev/null)"
  has "guard ended BUDGET-STOP" "$T/G/END" '^END BUDGET-STOP spent'; has "the jobs were halted before the copy" "$T/G/log.txt" 'halting the rental.s jobs before the copy: halted'
  chk "no drive/job/python process is left on the rental" nodrive
  has "partial copy verified against its manifest" "$T/G/log.txt" 'COPY-CHECK: [0-9]+ of [0-9]+ files arrived and match'; has "destroyed by exact id" <(destroyed) '^7000001 $'
  unset CAPSTOPOPC BASEHOPC
fi

if want 4; then title "4. drive.sh FAILED (torch pin; pip failure; too few cores): logs copied back, destroyed, START-FAIL"
  reset; echo 2.13.0+cpu > "$FAKE/py/torch-install"; runjob opus-cpu-vast-1-start start
  has "start says drive.sh did not launch the jobs" "$T/out/start.txt" 'FAILED torch check: torch 2.13.0\+cpu'; has "END START-FAIL" "$T/G/END" '^END START-FAIL spent'
  has "instance destroyed after a verified logs copy" <(destroyed) '^7000001 $'; chk "no job ran" test ! -e "$T/box/premonition-ks"
  reset; touch "$FAKE/py/pip-fail"; runjob opus-cpu-vast-1-start start; has "a failed pip install fails closed" "$T/box/W/drive-state.txt" 'FAILED pip install torch==2.14.0'; has "END START-FAIL" "$T/G/END" '^END START-FAIL spent'
  reset; OPC_MINCORES=9999 runjob opus-cpu-vast-1-start start; has "a box with too few cores fails closed" "$T/box/W/drive-state.txt" 'FAILED nproc'; has "END START-FAIL" "$T/G/END" '^END START-FAIL spent'
fi

if want 5; then title "5. copy check fails twice: instance STOPPED, not destroyed; collect flags the Director"; reset
  echo 2 > "$FAKE/ssh/mutate-on-tar"
  runjob opus-cpu-vast-1-start start; has "start prints STARTED" "$T/out/start.txt" '^STARTED$'
  wait_end 240; show "END: $(cat "$T/G/END" 2>/dev/null)"
  has "COPY-CHECK FAIL logged" "$T/G/log.txt" 'COPY-CHECK FAIL'; has "guard ended DONE-STOPPED-NOT-DESTROYED" "$T/G/END" '^END DONE-STOPPED-NOT-DESTROYED spent'
  [ -z "$(destroyed)" ] && ok "the instance was NOT destroyed" || bad "destroyed: $(destroyed)"; has "it was stopped by exact id" <(stopped) '^7000001 $'
  runjob opus-cpu-vast-2-collect collect; has "collect prints FLAG-DIRECTOR" "$T/out/collect.txt" '^FLAG-DIRECTOR'
fi

if want 6; then title "6. missing optional inputs and one failing job: s1-plain and trn-decode SKIPPED, the failure recorded, the rest finish"; reset
  rm -rf "${MBOPC:?}/$FR/runs/qual-plain-s0" "${MBOPC:?}/$FR/eq-runs/plain-s1-pre"
  echo "--plugin claude_dir_pond_c" > "$FAKE/py/fail"
  runjob opus-cpu-vast-1-start start; has "start prints STARTED" "$T/out/start.txt" '^STARTED$'
  wait_end 240; show "END: $(cat "$T/G/END" 2>/dev/null)"
  has "s1-plain SKIPPED with its reason" "$T/box/W/drive-state.txt" 'JOB s1-plain SKIPPED qual-plain sources not sent'; has "trn-decode SKIPPED with its reason" "$T/box/W/drive-state.txt" 'JOB trn-decode SKIPPED trn Mac inputs'
  has "the failing job's return code is recorded" "$T/box/W/drive-state.txt" 'JOB pond-c-dev END rc 8'; has "the other pond arms finished rc 0" "$T/box/W/drive-state.txt" 'JOB pond-b-dev END rc 0'
  has "pond-doubt noted the arm that did not finish and went on" "$T/box/W/pond-doubt.out" 'note: pond-c-pre-s0 not finished'; has "pond-doubt ended rc 0" "$T/box/W/drive-state.txt" 'JOB pond-doubt END rc 0'
  has "guard ended DONE (every job accounted for)" "$T/G/END" '^END DONE spent'; has "destroyed" <(destroyed) '^7000001 $'
  has "INPUTS.txt says why" "$T/G/INPUTS.txt" 'qual-plain s0: missing on the Mac'
fi

if want 7; then title "7. time stop at the time cap: jobs halted, partial copy verified, destroyed"; reset
  export TIMECAPOPC=3600; touch "$FAKE/py/hang"
  runjob opus-cpu-vast-1-start start; has "start prints STARTED" "$T/out/start.txt" '^STARTED$'
  /usr/bin/sleep 3; echo 4000 > "$FAKE/clock-jump"; wait_end 120; show "END: $(cat "$T/G/END" 2>/dev/null)"
  has "guard ended TIME-STOP" "$T/G/END" '^END TIME-STOP spent'; chk "no drive/job/python process is left" nodrive; has "destroyed by exact id" <(destroyed) '^7000001 $'
  unset TIMECAPOPC
fi

echo; echo "passed $PASS, failed $FAILS"
kill_fakes
[ -n "${KEEP:-}" ] && { echo "scratch kept: $T"; exit 0; }   # KEEP=1 keeps the scratch folder for a look
rm -rf "${T:?}"
[ "$FAILS" = 0 ]
