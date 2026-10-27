#!/bin/bash
# rsn-358u builder-free helper, run on BensPC in Git Bash (sleep research thread, 2026-09-27).
# Copied here as a file by handoff/kit/sleep358u/pass.sh (never piped into bash over ssh stdin: that corrupted bytes, 10:43 UTC probe).
# Actions:  kithash | hastree | checks | state | copy-model R | launch-train R | launch-evals R=SHA256 [R=SHA256 ...]
# (rsn-358u copy of handoff/kit/sleep358s/remote/bo358s.sh; evals run V1 poison first, then the test eval)
# It never edits sealed code, never stops a process, and never launches a run that already has W/<R> or W/<R>.log.
set -u
B=${B358:-/c/Users/benja/rsn358u}
KW=${KW358:-'C:\Users\benja\rsn358u\handoff\kit\sleep358u\remote'}
MD=${MD358:-/c/Users/benja/premonition-models/rsn358u}
ORDER="loop-s13 plain-s13 loop-s14 plain-s14 loop-s15 plain-s15 loop-s16 plain-s16"
TESTS=artifacts/claude-rsn358i-20260926/tests
cd "$B" || { echo "ERR no folder $B"; exit 3; }

procs() { MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\procs.ps1" 2>&1 | tr -d '\r'; }
in_order() { case " $ORDER " in *" $1 "*) return 0;; esac; return 1; }
ntrain() { echo "$1" | grep -E 'claude_rsn358u_run\.py.* train ' | grep -cE "[/\\\\]$2([^0-9]|\$)"; }
neval() { echo "$1" | grep -E 'claude_rsn358u_run\.py.* (eval|poison) ' | grep -cE "[/\\\\]$2[/\\\\]final"; }
freegb() { df -BG /c | tail -1 | awk '{gsub("G","",$4); print $4}'; }
gpu() { nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits | tr -d '\r' | tr ',' ' ' | head -1; }
launch() { MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\launch.ps1" -Cmd "$1" 2>&1 | tr -d '\r'; }

state() {
  local P R log dir fin tj el tn en
  echo "SEAL $(sha256sum -c artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt 2>/dev/null | grep -c ': OK$') $(grep -c . artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt)"
  echo "DISK $(freegb)"
  echo "GPU $(gpu)"
  echo "MARKER $(cat /c/Users/benja/GPU-BUSY.txt 2>/dev/null | tr -d '\r' | cut -c1-120)"
  echo "TESTSDIR $([ -d "$TESTS" ] && echo 1 || echo 0)"
  echo "WDIR $([ -d W ] && echo 1 || echo 0)"
  echo "CHECKS $(grep -q '^selftest ok: every item gets env 0' W/checks.txt 2>/dev/null && grep -q '^check-mask ok' W/checks.txt && echo 1 || echo 0)"
  P=$(procs)
  echo "PY $(echo "$P" | grep -c '^PROC ') $(echo "$P" | grep '^PROC ' | grep -vc 'claude_rsn358u_run\.py')"
  echo "$P" | grep '^PROC ' | cut -c1-240 | sed 's/^/PROCLINE /'
  for R in $ORDER; do
    log=0; dir=0; fin=0; tj=0; el=0
    [ -f "W/$R.log" ] && log=1; [ -d "W/$R" ] && dir=1; [ -f "W/$R/final.pt" ] && fin=1
    [ -f "W/$R/tests.json" ] && tj=1; { [ -f "W/$R.eval.log" ] || [ -f "W/$R.poison.log" ]; } && el=1
    tn=$(ntrain "$P" "$R"); en=$(neval "$P" "$R")
    echo "RUN $R log=$log dir=$dir final=$fin tests=$tj evallog=$el train_proc=$tn eval_proc=$en"
    [ $fin = 1 ] && echo "SHA $R $(sha256sum "W/$R/final.pt" | cut -c1-64)"
    if [ $log = 1 ]; then echo "LAST $R $(tail -c 600 "W/$R.log" | tr -d '\r' | grep . | tail -1 | cut -c1-240)"
    elif [ -f "W/$R/train_log.jsonl" ]; then echo "LAST $R $(tail -1 "W/$R/train_log.jsonl" | cut -c1-240)"; fi
    [ $fin = 0 ] && [ -s "W/$R.err" ] && echo "ERRTAIL $R $(tail -c 400 "W/$R.err" | tr -d '\r' | grep . | tail -1 | cut -c1-200)"
    [ -f "W/$R/train_summary.json" ] && echo "MIN $R $(grep -o '"minutes": *[0-9.]*' "W/$R/train_summary.json" | grep -o '[0-9.]*$')"
  done
  echo "END-STATE"
}

case "${1:-}" in
  hastree) [ -f artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt ] && echo "TREE 1" || echo "TREE 0" ;;
  checks)
    [ -f W/checks.txt ] && { echo "CHECKS already run:"; cat W/checks.txt; exit 0; }
    mkdir -p W
    PY=${PY358:-/c/Users/benja/lis300/venv/Scripts/python.exe}
    { $PY -B scripts/claude_rsn358a_envs.py selftest 2>&1 | tail -1; $PY -B scripts/claude_rsn358u_run.py selftest 2>&1 | tail -1
      $PY -B scripts/claude_rsn358u_run.py check-mask 2>&1 | tail -1
      $PY -c "import torch; print('torch', torch.__version__, torch.version.cuda)" 2>&1 | tail -1; } | tr -d '\r' > W/checks.txt
    cat W/checks.txt
    grep -q '^selftest ok: every item gets env 0' W/checks.txt && grep -q '^check-mask ok' W/checks.txt && echo "CHECKS 1" || echo "CHECKS 0" ;;
  kithash) cd "$B/handoff/kit/sleep358u/remote" && sha256sum bo358u.sh procs.ps1 launch.ps1 train1.cmd evals.cmd eval1.cmd ;;
  state) state ;;
  copy-model)
    R=${2:-}; in_order "$R" || { echo "ERR bad run $R"; exit 4; }
    [ -f "W/$R/final.pt" ] || { echo "ERR no W/$R/final.pt"; exit 4; }
    src=$(sha256sum "W/$R/final.pt" | cut -c1-64)
    if [ -f "$MD/$R/final.pt" ] && [ "$(sha256sum "$MD/$R/final.pt" | cut -c1-64)" = "$src" ]; then echo "COPY $R $src already"
    else mkdir -p "$MD/$R" && cp "W/$R/final.pt" "$MD/$R/final.pt" && echo "COPY $R $(sha256sum "$MD/$R/final.pt" | cut -c1-64)" || echo "ERR copy $R failed"; fi ;;
  launch-train)
    R=${2:-}; in_order "$R" || { echo "ERR bad run $R"; exit 4; }
    [ -e "W/$R" ] || [ -e "W/$R.log" ] && { echo "REFUSED $R: W/$R or W/$R.log already exists (never a second copy)"; exit 5; }
    [ "$(ntrain "$(procs)" "$R")" = 0 ] || { echo "REFUSED $R: a process for it is running"; exit 5; }
    [ "$(freegb)" -ge 3 ] || { echo "REFUSED $R: C: under 3 GB free"; exit 5; }
    arm=${R%-s*}; seed=${R##*-s}
    echo "LAUNCH $R $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\train1.cmd $arm $seed")" ;;
  launch-evals)
    shift; list=""
    [ -d "$TESTS" ] || { echo "REFUSED evals: no $TESTS"; exit 5; }
    P=$(procs)
    for a in "$@"; do R=${a%%=*}; want=${a#*=}
      in_order "$R" || { echo "REFUSED evals: bad run $R"; exit 5; }
      [ -f "W/$R/final.pt" ] || { echo "REFUSED evals: no W/$R/final.pt"; exit 5; }
      [ -e "W/$R/tests.json" ] || [ -e "W/$R.eval.log" ] || [ -e "W/$R.poison.log" ] || [ -e "W/$R/poison.json" ] && { echo "REFUSED evals: $R already evaluated or started (eval once)"; exit 5; }
      [ "$(neval "$P" "$R")" = 0 ] || { echo "REFUSED evals: eval of $R running"; exit 5; }
      got=$(sha256sum "W/$R/final.pt" | cut -c1-64)
      [ "$got" = "$want" ] || { echo "REFUSED evals: $R sha256 $got does not match SEAL-run $want"; exit 5; }
      list="$list $R"
    done
    [ -n "$list" ] || { echo "REFUSED evals: empty list"; exit 5; }
    echo "LAUNCH-EVALS$list $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\evals.cmd$list")" ;;
  *) echo "ERR unknown action ${1:-}"; exit 2 ;;
esac
