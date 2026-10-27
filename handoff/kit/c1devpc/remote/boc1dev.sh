#!/bin/bash
# c1-dev builder-free helper, run on BensPC in Git Bash (Everyday chat thread, 2026-09-27). Modelled on the tested
# handoff/kit/y1tpc/remote/boy1t.sh. Copied here as a file by handoff/kit/c1devpc/pass.sh (never piped into bash).
# Actions:  kithash | mark-tree PIN | state | checks | launch-chain | gpulog (started by launch-chain only)
# It never edits sealed code, never stops a process, never deletes anything, and never starts the chain a second time
# (W/chain.started). Eval only: it trains nothing and writes no weights.
set -u
B=${BC1:-/c/Users/benja/lis301/work/c1dev/tree}
KW=${KWC1:-'C:\Users\benja\lis301\work\c1dev\tree\handoff\kit\c1devpc\remote'}
PYW=${PYC1:-/c/Users/benja/lis300/venv/Scripts/python.exe}
HF=${HFC1:-/c/Users/benja/.cache/huggingface/hub}
A=artifacts/claude-c1dev-20260927
SEAL=$A/SEAL-2.sha256.txt
WINNL=${WINNLC1:-"winnl2: Windows text-mode writes use Linux line endings (newline='')"}
MB=models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
MQ=models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc
ML=models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
ARMS="D T Q L"
cd "$B" || { echo "ERR no folder $B"; exit 3; }

# the real BensPC commands are the y1t kit's tested ones; the *C1 variables only point a mock run at stand-ins
procs() { if [ -n "${PROCSC1:-}" ]; then $PROCSC1; else MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\procs.ps1"; fi 2>&1 | tr -d '\r'; }
freegb() { df -BG "${DFC1:-/c}" | tail -1 | awk '{gsub("G","",$4); print $4}'; }
gpu() { if [ -n "${GPUC1:-}" ]; then $GPUC1; else nvidia-smi --query-gpu=memory.used,memory.total,power.draw --format=csv,noheader,nounits; fi | tr -d '\r' | tr -d ' ' | tr ',' ' ' | head -1; }
gpuname() { if [ -n "${GPUC1:-}" ]; then echo mock-gpu; else nvidia-smi --query-gpu=name,driver_version --format=csv,noheader; fi 2>&1 | tr -d '\r' | head -1; }
launch() { if [ -n "${LAUNCHC1:-}" ]; then $LAUNCHC1 "$1"; else MSYS_NO_PATHCONV=1 powershell -NoProfile -ExecutionPolicy Bypass -File "$KW\\launch.ps1" -Cmd "$1"; fi 2>&1 | tr -d '\r'; }
pyenv() { PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 "$PYW" -B "$@"; }
age() { [ -e "$1" ] && echo $(( ( $(date +%s) - $(date -r "$1" +%s) ) / 60 )) || echo -1; }

state() {
  local P x f
  echo "PIN $(cat W/tree-pin.txt 2>/dev/null | tr -d '\r')"
  echo "SEAL $(sha256sum -c $SEAL 2>/dev/null | grep -c ': OK$') $(grep -c . $SEAL 2>/dev/null)"
  echo "MODELS $([ -d "$HF/$MB" ] && echo 1 || echo 0) $([ -d "$HF/$MQ" ] && echo 1 || echo 0) $([ -d "$HF/$ML" ] && echo 1 || echo 0)"
  echo "DISK $(freegb)"
  echo "GPU $(gpu)"
  echo "MARKER $(cat "${MKC1:-/c/Users/benja/GPU-BUSY.txt}" 2>/dev/null | tr -d '\r' | cut -c1-120)"
  P=$(procs)
  echo "PY $(echo "$P" | grep -c '^PROC ') $(echo "$P" | grep '^PROC ' | grep -c 'claude_ch403_run\|c1dev')"
  echo "$P" | grep '^PROC ' | cut -c1-240 | sed 's/^/PROCLINE /'
  echo "CHECKS $([ -f W/checks.txt ] && grep -c '^CHECK .* ok=1 ' W/checks.txt || echo -) $([ -f W/checks.txt ] && grep -c '^CHECK ' W/checks.txt || echo -)"
  [ -f W/checks.txt ] && grep '^VERSIONS ' W/checks.txt | head -1
  echo "CHAIN started=$([ -f W/chain.started ] && echo 1 || echo 0) done=$([ -f W/chain.done ] && echo 1 || echo 0)"
  [ -f W/steps.txt ] && tr -d '\r' < W/steps.txt | sed 's/^/STEP /'
  for x in $ARMS; do
    for f in "W/log$x.txt" "W/log$x-retry.txt"; do
      [ -f "$f" ] && echo "LAST $(basename "$f" .txt) age=$(age "$f")m $(tail -c 800 "$f" | tr -d '\r' | grep . | tail -1 | cut -c1-200)"
    done
    f=outC1/chat_$x.jsonl
    echo "ROWS $x $([ -f "$f" ] && grep -c . "$f" || echo 0) $([ -f "$f" ] && grep -o '"item_id": "[^"]*"' "$f" | sort -u | wc -l | tr -d ' ' || echo 0)"
  done
  [ -s W/gpu_log.txt ] && echo "GPULOG $(tr -d '\r' < W/gpu_log.txt | awk '{n++; if($2+0>m)m=$2+0; if($4+0>p)p=$4+0; l=$0} END{printf "lines=%d peak_used=%d peak_power=%.1f last=%s", n, m, p, l}')"
  echo "END-STATE"
}

# each test goes through the winnl2 wrapper, as the job said: its first line must be the winnl2 line and its last line
# the test's own pass line
chk() {
  local name=$1 want=$2 out rc first last; shift 2
  out=$(pyenv scripts/claude_winnl2_wrap.py "$@" 2>&1 | tr -d '\r'); rc=$?
  first=$(echo "$out" | head -1); last=$(echo "$out" | grep . | tail -1)
  echo "CHECK $name ok=$([ "$first" = "$WINNL" ] && [ "$last" = "$want" ] && echo 1 || echo 0) rc=$rc $(echo "$last" | cut -c1-160)"
}

checks() {
  [ -f W/checks.txt ] && { echo "CHECKS already done"; cat W/checks.txt; return 0; }
  mkdir -p W
  {
    chk talker "c1dev talker selftest: 6/6 OK" scripts/claude_c1dev_talker.py --selftest
    chk ch403 "ch-403 run selftest: 6/6 OK" scripts/claude_ch403_run.py selftest
    chk c1rival "c1rival selftest: 5/5 OK" scripts/claude_c1rival_run.py selftest
    chk noise "c1dev noise selftest: 5/5 OK" scripts/claude_c1dev_noise.py --selftest
    echo "VERSIONS $(pyenv -c 'import torch, transformers, sys; print(torch.__version__, torch.version.cuda, transformers.__version__, sys.version.split()[0])' 2>&1 | tr -d '\r' | tail -1)"
    echo "GPUNAME $(gpuname)"
  } > W/checks.txt
  cat W/checks.txt
}

case "${1:-}" in
  kithash) cd "$B/handoff/kit/c1devpc/remote" && sha256sum boc1dev.sh procs.ps1 launch.ps1 chain.cmd gpulog.cmd ;;
  mark-tree)
    [ -n "${2:-}" ] || { echo "ERR no pin"; exit 4; }
    [ -e W/tree-pin.txt ] && { echo "TREE already marked $(cat W/tree-pin.txt)"; exit 0; }
    mkdir -p W && echo "$2" > W/tree-pin.txt && echo "TREE marked $2" ;;
  state) state ;;
  checks) checks ;;
  launch-chain)
    [ -e W/chain.started ] && { echo "REFUSED: W/chain.started exists (never a second chain)"; exit 5; }
    [ -f W/checks.txt ] || { echo "REFUSED: checks not run"; exit 5; }
    [ "$(grep -c '^CHECK .* ok=1 ' W/checks.txt)" = 4 ] || { echo "REFUSED: not every selftest passed"; exit 5; }
    [ "$(sha256sum -c $SEAL 2>/dev/null | grep -c ': OK$')" = 24 ] || { echo "REFUSED: $SEAL is not 24 of 24"; exit 5; }
    [ "$(echo "$(procs)" | grep -c '^PROC ')" = 0 ] || { echo "REFUSED: a python.exe is running"; exit 5; }
    [ "$(freegb)" -ge 4 ] || { echo "REFUSED: C: has under 4 GB free ($(freegb) GB)"; exit 5; }
    echo "LAUNCH chain $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\chain.cmd")"
    sleep "${SLC1:-5}"
    echo "LAUNCH gpulog $(date -u +%FT%TZ) $(launch "cmd.exe /c $KW\\gpulog.cmd")" ;;
  gpulog)
    # one nvidia-smi line a minute (UTC time, MiB used, MiB total, watts) until W/chain.done exists, at most 5 hours
    i=0; while [ ! -e W/chain.done ] && [ $i -lt 300 ]; do echo "$(date -u +%FT%TZ) $(gpu)" >> W/gpu_log.txt; i=$((i+1)); sleep "${GLC1:-60}"; done ;;
  *) echo "ERR unknown action ${1:-}"; exit 2 ;;
esac
