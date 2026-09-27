#!/bin/bash
# bm-398w Mac driver (the Benchmarks thread, 2026-09-27). It finishes bm-398w's sealed data steps (PLAN.md; steps 7-10 of
# handoff/queue/bm398w-luna-mac.md) in the first job's folder, with no LLM builder: training sessions, questions (train, then
# panel), build with floors, RESULTS-data.md. Resume-safe: every word/ask pass skips rows already done, so a restart only
# repeats checks. The BASH-ONLY jobs handoff/queue/bm398w-mac-c*.md start it detached and copy its output into the watcher's
# worktree for the push. Counts and hashes only, never Luna's text. It never touches ~/.codex, keys or config files, never
# kills a process, and never reads the panel (its files are only hashed and copied).
# Ends: DRIVER-DONE.txt = DONE / DATA-SHORT / BUILD-ERROR / PARTIAL (time cap); a Luna outage (3 passes in a row with no new
# row and failed calls) exits with STALLED in the log and no DRIVER-DONE.txt, so the next job restarts it.
# Test hooks: DRV_D, DRV_WT, DRV_PY, DRV_CAP_S, DRV_NAP, DRV_NOGIT.
set -u
D=${DRV_D:-/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.oZGCMa5NMn}
WT=${DRV_WT:-/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27}
E=artifacts/claude-bm398w-20260927; O=$E/data; LOG="$WT/$O/RUNLOG-b.txt"; DONE="$WT/$O/DRIVER-DONE.txt"
UV=$(command -v uv || echo "$HOME/.local/bin/uv")
PY=${DRV_PY:-"$UV run --offline --no-project --python 3.12 python -B"}
CAP=${DRV_CAP_S:-39600}; NAP=${DRV_NAP:-600}; T0=$(date +%s)
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1
cd "$D" || exit 9
mkdir -p "$WT/$O"
say() { echo "$*" >> "$LOG"; }
now() { date -u +%FT%TZ; }
over() { [ $(( $(date +%s) - T0 )) -ge "$CAP" ]; }
getw() {
  [ -n "${DRV_NOGIT:-}" ] || git -C "$WT" fetch -q origin main 2>/dev/null
  W=$(git -C "$WT" show origin/main:handoff/luna-w/bm398w.txt 2>/dev/null | tr -dc '0-9' | cut -c1)
  case "$W" in 1|2|3) ;; *) W=1;; esac
}
sync() { cp -R "$D/$O/." "$WT/$O/" && find "$WT/$O" -type f -size +2900k ! -name '*.gz' -exec gzip -n -9 -f {} \; ; }
field() { v=$(sed -n "s/.*\"$1\": \([0-9]*\).*/\1/p" "$2" 2>/dev/null | head -1); echo "${v:-0}"; }
npass() { n=$(grep -c "^== $1 pass" "$LOG" 2>/dev/null); echo "${n:-0}"; }
# a data python already running (e.g. left by a dead builder). The pattern names the python's own argv, not just the file
# name: a builder's opencode argv holds its whole task text, which can name the script.
PYPAT='python[0-9.]* -B scripts/claude_bm398w_data\.py (word|ask|build|count)'
waitpy() {
  if pgrep -f "$PYPAT" >/dev/null; then
    say "waiting for a data python already running (PID $(pgrep -f "$PYPAT" | tr '\n' ' ')) $(now)"
    while pgrep -f "$PYPAT" >/dev/null; do sleep 60; done
    say "it ended $(now)"
  fi
}
# run <tag> <args...>: one code-only command; stdout (a JSON count line) to the log, stderr kept in $D (only its size and
# last error type go in the log, so no text can leak into the pushed log)
run() {
  tag="$1"; shift
  $PY scripts/claude_bm398w_data.py "$@" > "$D/last-$tag.json" 2> "$D/err-$tag.txt"; rc=$?
  cat "$D/last-$tag.json" >> "$LOG"
  el=$(wc -l < "$D/err-$tag.txt" | tr -d ' ')
  [ "$el" = 0 ] || say "stderr lines $el; last error type: $(grep -oE '^[A-Za-z_.]*(Error|Exception|Interrupt)' "$D/err-$tag.txt" | tail -1)"
  return $rc
}
# loop <label> <tag> <max passes> <args...>: resumable passes until every job is done, or <max passes> passes of this label in
# the log (then it goes on, as the first job's "at most N runs"); 3 passes in a row with no new row and failed calls = a Luna
# outage: exit STALLED (a later job restarts the driver, which resumes)
loop() {
  lab="$1"; tag="$2"; mx="$3"; shift 3; strikes=0
  while :; do
    if over; then say "TIME CAP during $lab $(now)"; return 1; fi
    if [ "$(npass "$lab")" -ge "$mx" ]; then say "PASS LIMIT: $mx passes of $lab; going on $(now)"; return 0; fi
    waitpy; getw
    say "== $lab pass W=$W start $(now)"
    run "$tag" "$@" --workers "$W" --max-minutes 45 --max-failed 20; rc=$?
    say "exit=$rc end $(now)"
    sync
    f="$D/last-$tag.json"
    jobs=$(field jobs "$f"); skip=$(field skipped "$f"); ok=$(field ok "$f"); fc=$(field failed_calls "$f")
    if [ "$rc" = 0 ] && [ "$jobs" = "$skip" ]; then return 0; fi
    if [ "$ok" = 0 ] && [ "$fc" -gt 0 ]; then
      strikes=$((strikes + 1))
      if [ "$strikes" -ge 3 ]; then say "STALLED in $lab after 3 passes with 0 new rows and failed calls $(now)"; exit 7; fi
      sleep "$NAP"
    elif [ "$rc" != 0 ] && [ "$ok" = 0 ]; then
      say "STALLED in $lab: exit $rc with 0 new rows $(now)"; exit 8
    else
      strikes=0
    fi
  done
}

[ -e "$DONE" ] && exit 0
say "driver start $(now) pid $$ (uv: $UV)"
V=DONE
loop "train word" tw 14 word --plans "$O/train/plans.jsonl" --out "$O/train/sess.jsonl" || V=PARTIAL
run count-train count --plans "$O/train/plans.jsonl" --sess "$O/train/sess.jsonl"
if [ "$V" = DONE ]; then
  for X in train panel; do
    loop "ask $X" "a$X" 6 ask --plans "$O/$X/plans.jsonl" --sess "$O/$X/sess.jsonl" --out "$O/$X/qa.jsonl" || { V=PARTIAL; break; }
    run "count-$X" count --plans "$O/$X/plans.jsonl" --sess "$O/$X/sess.jsonl" --qa "$O/$X/qa.jsonl"
  done
fi
FT=none; FP=none
if [ "$V" = DONE ]; then
  say "== build $(now)"
  run build-train build --plans "$O/train/plans.jsonl" --sess "$O/train/sess.jsonl" --qa "$O/train/qa.jsonl" --out "$O/train/build"; r1=$?
  run build-panel build --panel --plans "$O/panel/plans.jsonl" --sess "$O/panel/sess.jsonl" --qa "$O/panel/qa.jsonl" --out "$O/panel/build"; r2=$?
  say "build exits: train $r1, panel $r2"
  FT=$(sed -n 's/.*"floor": "\([A-Z-]*\)".*/\1/p' "$D/last-build-train.json"); FP=$(sed -n 's/.*"floor": "\([A-Z-]*\)".*/\1/p' "$D/last-build-panel.json")
  for r in $r1 $r2; do case "$r" in 0) ;; 3) [ "$V" = DONE ] && V=DATA-SHORT;; *) V=BUILD-ERROR;; esac; done
fi
sync
say "driver end $(now): $V"
if [ "$V" != PARTIAL ]; then
  R="$WT/$O/RESULTS-data.md"
  {
    echo "# bm-398w data: RESULTS-data (written by scripts/claude_bm398w_macdrive.sh, $(now); counts and hashes only)"
    echo
    echo "VERDICT: $V"
    echo "Pilot GATE (first job bm398w-luna-mac): kept_chats 5 of 5, bar 3: PASS"
    echo "FLOOR: train ${FT:-none}, panel ${FP:-none}"
    echo
    echo "## First job's printed lines (origin/builder-outbox:runs/bm398w-luna-mac/bm398w-luna-mac.go1.err.txt; W=3 there)"
    echo '```'
    [ -n "${DRV_NOGIT:-}" ] || git -C "$WT" fetch -q origin +builder-outbox:refs/remotes/origin/builder-outbox 2>/dev/null
    git -C "$WT" show origin/builder-outbox:runs/bm398w-luna-mac/bm398w-luna-mac.go1.err.txt 2>/dev/null | perl -pe 's/\e\[[0-9;]*m//g' \
      | awk '/PILOT_RUN1/{f=1} f' | grep -E '^\{"(jobs|chats)"|_EXIT:|_START|^[A-Z][a-z]{2} [A-Z][a-z]{2} +[0-9]+ [0-9:]+ UTC' || echo "(not found)"
    echo '```'
    echo
    echo "## This run: RUNLOG-b.txt, verbatim (W per pass = handoff/luna-w/bm398w.txt, the Director's Luna share for this thread)"
    echo '```'
    cat "$LOG"
    echo '```'
    echo
    echo "## sha256 of every file under data/ in the Mac folder (uncompressed)"
    echo '```'
    (cd "$D" && find "$O" -type f | sort | while read -r x; do shasum -a 256 "$x"; done)
    echo '```'
    echo
    echo "## sha256 of every pushed data file (a .gz is a file over about 3 MB, gzipped with gzip -n -9 because the watcher skips files of 5 MB and more)"
    echo '```'
    (cd "$WT" && find "$O" -type f ! -name RESULTS-data.md ! -name DRIVER-DONE.txt ! -name RUNLOG-b.txt | sort | while read -r x; do shasum -a 256 "$x"; done)
    echo '```'
  } > "$R"
fi
echo "$V $(now)" > "$DONE"
