#!/bin/bash
# y1t builder-free helper, run on BensPC in Git Bash (Answering-from-memory thread, 2026-09-27). Modelled on the sleep
# research thread's tested handoff/kit/sleep358s/remote/bo358s.sh. Copied here as a file by handoff/kit/y1tpc/pass.sh
# (never piped into bash over ssh stdin).
# Actions:  kithash | mark-tree PIN | state | checks | launch-chain | copy-model | gpulog (started by launch-chain only)
# It never edits sealed code, never stops a process, and never starts the chain a second time (W/chain.started).
set -u
B=${BY1T:-/c/Users/benja/y1t/tree}
KW=${KWY1T:-'C:\Users\benja\y1t\tree\handoff\kit\y1tpc\remote'}
MD=${MDY1T:-/c/Users/benja/premonition-models/y1t}
PYW=${PYY1T:-/c/Users/benja/lis300/venv/Scripts/python.exe}
A=artifacts/claude-y1t-20260926
I=$A/glm2/items
cd "$B" || { echo "ERR no folder $B"; exit 3; }

procs() { MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\procs.ps1" 2>&1 | tr -d '\r'; }
freegb() { df -BG "${DFY1T:-/c}" | tail -1 | awk '{gsub("G","",$4); print $4}'; }
gpu() { nvidia-smi --query-gpu=memory.used,memory.total,power.draw --format=csv,noheader,nounits | tr -d '\r' | tr -d ' ' | tr ',' ' ' | head -1; }
launch() { MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\launch.ps1" -Cmd "$1" 2>&1 | tr -d '\r'; }
pyenv() { PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 "$PYW" -B "$@"; }
age() { [ -e "$1" ] && echo $(( ( $(date +%s) - $(date -r "$1" +%s) ) / 60 )) || echo -1; }

state() {
  local P f
  echo "PIN $(cat W/tree-pin.txt 2>/dev/null | tr -d '\r')"
  echo "SEALR $(sha256sum -c $A/SEAL-y1t-rental.sha256.txt 2>/dev/null | grep -c ': OK$') $(grep -c . $A/SEAL-y1t-rental.sha256.txt)"
  echo "SEALH $(sha256sum -c $A/SEAL-y1tH1-runner.sha256.txt 2>/dev/null | grep -c ': OK$') $(grep -c . $A/SEAL-y1tH1-runner.sha256.txt)"
  echo "SEALP $(cd artifacts/claude-spare401-20260926 2>/dev/null && grep ' panel/turns.jsonl$' SEAL-spare401.sha256.txt | sha256sum -c 2>/dev/null | grep -c ': OK$') 1"
  echo "ITEMS $(sha256sum $I/items_train.jsonl | cut -c1-64) $(sha256sum $I/items_dev.jsonl | cut -c1-64)"
  echo "DISK $(freegb)"
  echo "GPU $(gpu)"
  echo "MARKER $(cat "${MKY1T:-/c/Users/benja/GPU-BUSY.txt}" 2>/dev/null | tr -d '\r' | cut -c1-120)"
  P=$(procs)
  echo "PY $(echo "$P" | grep -c '^PROC ') $(echo "$P" | grep '^PROC ' | grep -c 'y1t\\tree\|y1t/tree\|claude_y1t_data\|claude_bm398r_train\|claude_y1g_doubt\|claude_y1t_h1run')"
  echo "$P" | grep '^PROC ' | cut -c1-240 | sed 's/^/PROCLINE /'
  echo "CHECKS $([ -f W/checks.txt ] && grep -c '^CHECK .* rc=0 ' W/checks.txt || echo -) $([ -f W/checks.txt ] && grep -c '^CHECK ' W/checks.txt || echo -)"
  [ -f W/checks.txt ] && grep '^VERSIONS ' W/checks.txt | head -1
  echo "CHAIN started=$([ -f W/chain.started ] && echo 1 || echo 0) done=$([ -f W/chain.done ] && echo 1 || echo 0)"
  [ -f W/steps.txt ] && tr -d '\r' < W/steps.txt | sed 's/^/STEP /'
  for f in drafts train eval eval_plain h1_A h1_B; do
    [ -f "W/${f}_log.txt" ] && echo "LAST $f age=$(age "W/${f}_log.txt")m $(tail -c 800 "W/${f}_log.txt" | tr -d '\r' | grep . | tail -1 | cut -c1-200)"
  done
  [ -f tr/adapter398r.pt ] && echo "ADAPTER $(sha256sum tr/adapter398r.pt | cut -c1-64) $(wc -c < tr/adapter398r.pt | tr -d ' ')"
  [ -s W/gpu_log.txt ] && echo "GPULOG $(tr -d '\r' < W/gpu_log.txt | awk '{n++; if($2+0>m)m=$2+0; if($4+0>p)p=$4+0; l=$0} END{printf "lines=%d peak_used=%d peak_power=%.1f last=%s", n, m, p, l}')"
  echo "FILES adapter=$([ -f tr/adapter398r.pt ] && echo 1 || echo 0) merged=$([ -d tr/merged ] && echo 1 || echo 0) eval=$([ -d eval ] && echo 1 || echo 0) eval_plain=$([ -d eval_plain ] && echo 1 || echo 0) h1A=$([ -f h1/rows_A.jsonl ] && echo 1 || echo 0) h1B=$([ -f h1/rows_B.jsonl ] && echo 1 || echo 0)"
  echo "END-STATE"
}

checks() {
  [ -f W/checks.txt ] && { echo "CHECKS already done"; cat W/checks.txt; return 0; }
  mkdir -p W
  local rc out
  {
    for s in claude_y1t_data.py claude_y1g_doubt.py claude_y1t_h1run.py; do
      out=$(pyenv scripts/$s --selftest 2>&1 | tr -d '\r'); rc=$?
      echo "CHECK $s rc=$rc $(echo "$out" | grep . | tail -1 | cut -c1-160)"
    done
    out=$(pyenv scripts/claude_bm398r_train.py selftest 2>&1 | tr -d '\r'); rc=$?
    echo "CHECK claude_bm398r_train.py rc=$rc $(echo "$out" | grep . | tail -1 | cut -c1-160)"
    echo "VERSIONS $(pyenv -c 'import torch, transformers; print(torch.__version__, torch.version.cuda, transformers.__version__)' 2>&1 | tr -d '\r' | tail -1)"
    echo "GPUNAME $(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | tr -d '\r' | head -1)"
  } > W/checks.txt
  cat W/checks.txt
}

case "${1:-}" in
  kithash) cd "$B/handoff/kit/y1tpc/remote" && sha256sum boy1t.sh procs.ps1 launch.ps1 chain.cmd gpulog.cmd ;;
  mark-tree)
    [ -n "${2:-}" ] || { echo "ERR no pin"; exit 4; }
    [ -e W/tree-pin.txt ] && { echo "TREE already marked $(cat W/tree-pin.txt)"; exit 0; }
    mkdir -p W && echo "$2" > W/tree-pin.txt && echo "TREE marked $2" ;;
  state) state ;;
  checks) checks ;;
  launch-chain)
    [ -e W/chain.started ] && { echo "REFUSED: W/chain.started exists (never a second chain)"; exit 5; }
    [ -f W/checks.txt ] || { echo "REFUSED: checks not run"; exit 5; }
    [ "$(grep -c '^CHECK .* rc=0 ' W/checks.txt)" = 4 ] || { echo "REFUSED: not every selftest passed"; exit 5; }
    [ "$(echo "$(procs)" | grep -c '^PROC ')" = 0 ] || { echo "REFUSED: a python.exe is running"; exit 5; }
    [ "$(freegb)" -ge 10 ] || { echo "REFUSED: C: has under 10 GB free ($(freegb) GB)"; exit 5; }
    echo "LAUNCH chain $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\chain.cmd")"
    sleep 5
    echo "LAUNCH gpulog $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\gpulog.cmd")" ;;
  gpulog)
    # one nvidia-smi line a minute (UTC time, MiB used, MiB total, watts) until W/chain.done exists, at most 8 hours; stops itself
    i=0; while [ ! -e W/chain.done ] && [ $i -lt 480 ]; do echo "$(date -u +%FT%TZ) $(gpu)" >> W/gpu_log.txt; i=$((i+1)); sleep "${GLY1T:-60}"; done ;;
  copy-model)
    [ -f W/chain.done ] || { echo "ERR chain not done"; exit 4; }
    [ -f tr/adapter398r.pt ] || { echo "ERR no tr/adapter398r.pt"; exit 4; }
    src=$(sha256sum tr/adapter398r.pt | cut -c1-64)
    mkdir -p "$MD"
    if [ -f "$MD/adapter398r.pt" ] && [ "$(sha256sum "$MD/adapter398r.pt" | cut -c1-64)" = "$src" ]; then echo "COPY adapter $src already"
    else cp tr/adapter398r.pt "$MD/adapter398r.pt" && echo "COPY adapter $(sha256sum "$MD/adapter398r.pt" | cut -c1-64)" || echo "ERR adapter copy failed"; fi
    if [ -d tr/merged ]; then
      need=$(( $(du -sm tr/merged | cut -f1) / 1024 + 3 ))
      if [ -d "$MD/merged" ]; then echo "COPY merged already ($(ls "$MD/merged" | wc -l) files)"
      elif [ "$(freegb)" -lt "$need" ]; then echo "COPY merged skipped: C: has $(freegb) GB free, needs $need; tr/merged stays in the tree"
      else cp -r tr/merged "$MD/merged" && echo "COPY merged $(ls "$MD/merged" | wc -l) files, $(du -sm "$MD/merged" | cut -f1) MB" || echo "ERR merged copy failed"; fi
    else echo "COPY merged: no tr/merged"; fi ;;
  *) echo "ERR unknown action ${1:-}"; exit 2 ;;
esac
