#!/bin/bash
# rd-378g builder-free helper, run on BensPC in Git Bash (Trustworthy notes thread, 2026-09-27). Modelled on the
# Answering-from-memory thread's handoff/kit/y1tpc/remote/boy1t.sh (itself from the sleep research thread's tested
# kit). Copied here as a file by handoff/kit/rd378gpc/pass.sh (never piped into bash over ssh stdin).
# Actions: kithash | mark-tree PIN | state | checks | find-r | launch-chain | copy-adapter | gpulog (launch-chain only)
# It never edits sealed code, never stops a process, never deletes anything, and never starts the chain a second
# time (W/chain.started). LoCoMo files stay in $PV (outside the tree, outside git); it prints counts, hashes and
# the last log lines only.
set -u
B=${B378G:-/c/Users/benja/rd378g2/tree}
KW=${KW378G:-'C:\Users\benja\rd378g2\tree\handoff\kit\rd378gpc\remote'}
PV=${PV378G:-/c/Users/benja/rd378g2-private}
MD=${MD378G:-/c/Users/benja/premonition-models}
PYW=${PY378G:-/c/Users/benja/lis300/venv/Scripts/python.exe}
BASE=${BASE378G:-/c/Users/benja/lis300/model}
DATA=${DATA378G:-/c/Users/benja/lis301/work/bm390/data2}
N=artifacts/claude-rd378g-20260926
R_SHA=${RSHA378G:-dbcc8db5a5840d839fe049f720bdfeacf094deb78f2652984c28c53f8c388510}
LOCOMO_SHA=${LSHA378G:-79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4}
MINILM=${MINILM378G:-1110a243fdf4706b3f48f1d95db1a4f5529b4d41}
STEPS="dialogs train devcheck write59 score whenoff g5G g5R"
cd "$B" || { echo "ERR no folder $B"; exit 3; }

procs() { MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\procs.ps1" 2>&1 | tr -d '\r'; }
freegb() { df -BG "${DF378G:-/c}" | tail -1 | awk '{gsub("G","",$4); print $4}'; }
gpu() { nvidia-smi --query-gpu=memory.used,memory.total,power.draw --format=csv,noheader,nounits | tr -d '\r' | tr -d ' ' | tr ',' ' ' | head -1; }
launch() { MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\launch.ps1" -Cmd "$1" 2>&1 | tr -d '\r'; }
pyenv() { PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 "$PYW" -B "$@"; }
age() { [ -e "$1" ] && echo $(( ( $(date +%s) - $(date -r "$1" +%s) ) / 60 )) || echo -1; }
okc() { sha256sum -c "$1" 2>/dev/null | grep -c ': OK$'; }

state() {
  local P
  echo "PIN $(cat W/tree-pin.txt 2>/dev/null | tr -d '\r')"
  echo "SEALB $(okc $N/SEAL-B.sha256.txt) $(grep -c . $N/SEAL-B.sha256.txt)"
  echo "SEALK $(okc $N/SEAL-ADD-K.sha256.txt) $(grep -c . $N/SEAL-ADD-K.sha256.txt)"
  echo "SEALAB $(( $(okc $N/SEAL-ADD-A.sha256.txt) + $(okc $N/SEAL-ADD-B.sha256.txt) )) $(( $(grep -c . $N/SEAL-ADD-A.sha256.txt) + $(grep -c . $N/SEAL-ADD-B.sha256.txt) ))"
  echo "SEAL0 $(okc $N/SEAL.sha256.txt) $(sha256sum -c $N/SEAL.sha256.txt 2>/dev/null | grep -v ': OK$' | grep -c ': FAILED') $(sha256sum -c $N/SEAL.sha256.txt 2>/dev/null | grep ': FAILED' | cut -d: -f1 | tr '\n' ' ')"
  echo "DISK $(freegb)"
  echo "GPU $(gpu)"
  echo "MARKER $(cat "${MK378G:-/c/Users/benja/GPU-BUSY.txt}" 2>/dev/null | tr -d '\r' | cut -c1-120)"
  P=$(procs)
  echo "PY $(echo "$P" | grep -c '^PROC ') $(echo "$P" | grep '^PROC ' | grep -c 'rd378g2\|claude_lis300_train\|claude_rd378_write\|claude_rd378u_confirm\|claude_rd378g_whenoff\|claude_rd378L_recall')"
  echo "$P" | grep '^PROC ' | cut -c1-240 | sed 's/^/PROCLINE /'
  echo "CHECKS $([ -f W/checks.txt ] && grep -c '^CHECK .* rc=0 ' W/checks.txt || echo -) $([ -f W/checks.txt ] && grep -c '^CHECK ' W/checks.txt || echo -)"
  [ -f W/checks.txt ] && grep -E '^(VERSIONS|DATA|MINILM) ' W/checks.txt
  echo "RPATH $(cat W/r-path.txt 2>/dev/null | tr -d '\r')"
  echo "CHAIN started=$([ -f W/chain.started ] && echo 1 || echo 0) done=$([ -f W/chain.done ] && echo 1 || echo 0)"
  [ -f W/steps.txt ] && tr -d '\r' < W/steps.txt | sed 's/^/STEP /'
  for f in $STEPS; do
    [ -f "W/${f}_log.txt" ] && echo "LAST $f age=$(age "W/${f}_log.txt")m $(tail -c 800 "W/${f}_log.txt" | tr -d '\r' | grep . | tail -1 | cut -c1-200)"
  done
  # ADDENDUM-M: size and age of each step's output file (the write steps log only at their end), counts only
  for f in W/g/train_log.jsonl W/g_b8/train_log.jsonl W/gdev.jsonl "$PV/g59.jsonl" W/g5_G.jsonl W/g5_R.jsonl; do
    [ -f "$f" ] && echo "OUT ${f/#$PV/PV} bytes=$(wc -c < "$f" | tr -d ' ') age=$(age "$f")m"
  done
  echo "GDIR $(cat W/g-dir.txt 2>/dev/null | tr -d '\r')"
  [ -s W/gpu_log.txt ] && echo "GPULOG $(tr -d '\r' < W/gpu_log.txt | awk '{n++; if($2+0>m)m=$2+0; if($4+0>p)p=$4+0; l=$0} END{printf "lines=%d peak_used=%d peak_power=%.1f last=%s", n, m, p, l}')"
  echo "FILES g=$([ -d W/g/merged ] && echo 1 || echo 0) g_b8=$([ -d W/g_b8/merged ] && echo 1 || echo 0) gdev=$([ -f W/gdev.jsonl ] && echo 1 || echo 0) g59=$([ -f $PV/g59.jsonl ] && echo 1 || echo 0) outg=$([ -f $PV/outg/notes_confirm.json ] && echo 1 || echo 0) whenoff=$([ -f $PV/outg_whenoff/notes_confirm.json ] && echo 1 || echo 0) g5G=$([ -f W/g5_G.jsonl ] && echo 1 || echo 0) g5R=$([ -f W/g5_R.jsonl ] && echo 1 || echo 0)"
  echo "END-STATE"
}

checks() {
  [ -f W/checks.txt ] && { echo "CHECKS already done"; cat W/checks.txt; return 0; }
  mkdir -p W
  local rc out s want
  {
    for s in "claude_rd378u_confirm.py selftest|RD378U-SELFTEST PASS" "claude_ep382_store_v4.py selftest|EP382-V4-SELFTEST PASS" \
             "claude_rd378L_recall.py selftest|RD378L-SELFTEST PASS" "claude_rd378g_whenoff.py selftest|RD378G-WHENOFF-SELFTEST PASS"; do
      want=${s#*|}; s=${s%|*}
      out=$(pyenv scripts/$s 2>&1 | tr -d '\r'); rc=$?
      echo "$out" | grep -q "$want" || { [ "$rc" = 0 ] && rc=97; }
      echo "CHECK ${s% *} rc=$rc $(echo "$out" | grep . | tail -1 | cut -c1-160)"
    done
    echo "VERSIONS $(pyenv -c 'import torch, transformers, peft; print(torch.__version__, torch.version.cuda, transformers.__version__, peft.__version__)' 2>&1 | tr -d '\r' | tail -1)"
    echo "GPUNAME $(nvidia-smi --query-gpu=name,driver_version --format=csv,noheader | tr -d '\r' | head -1)"
    m=$(pyenv -c "import sys; sys.path.insert(0, 'scripts'); import fable_self122_train as T; print(T.resolve_snapshot(None))" 2>&1 | tr -d '\r' | tail -1)
    case "$m" in *"$MINILM") echo "MINILM ok";; *) echo "MINILM bad $(echo "$m" | cut -c1-160)";; esac
    d=$(sha256sum "$DATA/locomo10.json" 2>/dev/null | cut -c1-64)
    [ "$d" = $LOCOMO_SHA ] && echo "DATA ok" || echo "DATA bad ${d:-missing}"
    echo "BASESHA $(sha256sum "$BASE/model.safetensors" 2>/dev/null | cut -c1-64)"
  } > W/checks.txt
  cat W/checks.txt
}

find_r() {
  # R = the rd-378 writer (merged sha256 $R_SHA). Look in every premonition-models folder and in folders named *rd378*
  # up to depth 3 under C:\Users\benja (never inside this tree, never a *rd378g* folder); hash at most 12 candidates.
  [ -s W/r-path.txt ] && { echo "RFOUND $(cat W/r-path.txt) (already)"; return 0; }
  local f d n=0
  # ADDENDUM-M: first the folder rd-378's run record names (artifacts/claude-rd378-20260925/RESULTS-benspc.md:143)
  for f in "${RP378G:-/c/Users/benja/rd378/tree/WORK/nrun/merged}/model.safetensors" "$MD"/*/model.safetensors /c/Users/benja/*rd378*/model.safetensors /c/Users/benja/*rd378*/*/model.safetensors \
           /c/Users/benja/*/*rd378*/model.safetensors /c/Users/benja/*/*rd378*/*/model.safetensors /c/Users/benja/*/*/*rd378*/model.safetensors; do
    [ -f "$f" ] || continue
    d=$(dirname "$f"); case "$d" in *rd378g*|"$B"*) continue;; esac
    case "$d" in "$MD"/*) ;; *) case "$(echo "$d" | tr 'A-Z' 'a-z')" in *rd378*) ;; *) continue;; esac;; esac
    n=$((n+1)); [ $n -gt 12 ] && break
    # r-path.txt is read by chain.cmd for Windows python, so it holds a C:/... path (cygpath -m), not /c/...
    if [ "$(sha256sum "$f" | cut -c1-64)" = $R_SHA ]; then mkdir -p W; d=$(cygpath -m "$d" 2>/dev/null || echo "$d"); echo "$d" > W/r-path.txt; echo "RFOUND $d"; return 0; fi
    echo "RCAND $d no-match"
  done
  echo "RNONE ($n candidates hashed)"
}

case "${1:-}" in
  kithash) cd "$B/handoff/kit/rd378gpc/remote" && sha256sum bo378g.sh procs.ps1 launch.ps1 chain.cmd gpulog.cmd check378g.py ;;
  mark-tree)
    [ -n "${2:-}" ] || { echo "ERR no pin"; exit 4; }
    [ -e W/tree-pin.txt ] && { echo "TREE already marked $(cat W/tree-pin.txt)"; exit 0; }
    mkdir -p W && echo "$2" > W/tree-pin.txt && echo "TREE marked $2" ;;
  state) state ;;
  checks) checks ;;
  find-r) find_r ;;
  launch-chain)
    [ -e W/chain.started ] && { echo "REFUSED: W/chain.started exists (never a second chain)"; exit 5; }
    [ -f W/checks.txt ] || { echo "REFUSED: checks not run"; exit 5; }
    [ "$(grep -c '^CHECK .* rc=0 ' W/checks.txt)" = 4 ] || { echo "REFUSED: not every selftest passed"; exit 5; }
    grep -q '^MINILM ok' W/checks.txt && grep -q '^DATA ok' W/checks.txt || { echo "REFUSED: MiniLM or LoCoMo data check failed"; exit 5; }
    [ "$(echo "$(procs)" | grep -c '^PROC ')" = 0 ] || { echo "REFUSED: a python.exe is running"; exit 5; }
    [ "$(freegb)" -ge 6 ] || { echo "REFUSED: C: has under 6 GB free ($(freegb) GB)"; exit 5; }
    mkdir -p "$PV"
    echo "LAUNCH chain $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\chain.cmd")"
    sleep 5
    echo "LAUNCH gpulog $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\gpulog.cmd")" ;;
  gpulog)
    # one nvidia-smi line a minute (UTC time, MiB used, MiB total, watts) until W/chain.done exists, at most 6 hours; stops itself
    i=0; while [ ! -e W/chain.done ] && [ $i -lt 360 ]; do echo "$(date -u +%FT%TZ) $(gpu)" >> W/gpu_log.txt; i=$((i+1)); sleep "${GL378G:-60}"; done ;;
  copy-adapter)
    # G's adapter only (small) goes to premonition-models\rd378g; the merged model stays in the tree (no 2 GB copy)
    [ -f W/chain.done ] || { echo "ERR chain not done"; exit 4; }
    g=$(cat W/g-dir.txt 2>/dev/null | tr -d '\r'); [ -n "$g" ] && [ -d "$g/adapter" ] || { echo "ERR no adapter"; exit 4; }
    mkdir -p "$MD/rd378g"
    if [ -d "$MD/rd378g/adapter" ]; then echo "COPY adapter already ($(ls "$MD/rd378g/adapter" | wc -l) files)"
    else cp -r "$g/adapter" "$MD/rd378g/adapter" && echo "COPY adapter $(ls "$MD/rd378g/adapter" | wc -l) files, $(du -sm "$MD/rd378g/adapter" | cut -f1) MB" || echo "ERR adapter copy failed"; fi
    echo "MERGED $(sha256sum "$g/merged/model.safetensors" 2>/dev/null | cut -c1-64)" ;;
  *) echo "ERR unknown action ${1:-}"; exit 2 ;;
esac
