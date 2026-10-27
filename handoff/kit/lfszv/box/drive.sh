#!/bin/bash
# lf-sz (same-size depth check: loop8 vs a widened 2-layer loop and a 4-layer loop at ~6.4M weights) on ONE vast rental (lf-sz Director helper, 2026-09-28). Copy of the lf-8 kit (handoff/kit/lf8v). Runs ON the rental,
# detached (setsid nohup), from /root/r. Same design as handoff/kit/sleep358tv/box/drive.sh at 7a1e0b85e: pins torch
# 2.11.0+cu128 (fail-closed), checks every line of $A/SEAL.sha256.txt (16), runs the lf-sz selftest
# and Stage 0 (the "loop  free=3 grad=2 cache=False" line must end in 0/12), then starts all 6 runs at once with the sealed
# command and waits for them. Progress lines go to W/drive-state.txt; the last is DONE or FAILED <why>.
# It never edits code and never deletes anything.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-lfsz-20260928
ORDER="loop8-s9 loop2w-s9 loop4w-s9 loop8-s10 loop2w-s10 loop4w-s10"
mkdir -p W
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
st START
st "HOST nproc $(nproc) disk $(df -h /root | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > W/pip.log 2>&1 || fail "pip install torch==2.11.0 (see W/pip.log)"
python -c "import torch; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))" > W/torch.txt 2>&1
grep -q '^torch 2.11.0' W/torch.txt && grep -q ' True ' W/torch.txt || fail "torch check: $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
st "TORCH $(cat W/torch.txt)"
want=$(wc -l < $A/SEAL.sha256.txt | tr -d ' '); n=$(sha256sum -c $A/SEAL.sha256.txt 2>/dev/null | grep -c ': OK$')
[ "$n" = "$want" ] && [ "$n" = 16 ] || fail "seal $n/$want"
st "SEAL $n/$want"
python -B scripts/claude_lfsz_run.py selftest > W/checks.txt 2>&1
grep -q '^lfsz selftest ok: loop8 6386174, loop2w 6438814, loop4w 6334182 weights' W/checks.txt || fail "selftest (see W/checks.txt)"
st CHECKS-OK
python -B scripts/claude_stage0_autocast_grad.py > W/stage0.txt 2>&1
grep '^loop  free=3 grad=2 cache=False' W/stage0.txt | grep -q ' 0/12$' || fail "FIX-FAILS: Stage 0 cache-off line is not 0/12 (see W/stage0.txt)"
st STAGE0-OK
for R in $ORDER; do { [ -e W/$R ] || [ -e W/$R.log ]; } && fail "$R already exists"; done
( while :; do echo "$(date -u +%T) $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | tr '\n' ';')" >> /root/r/gpumem.live; sleep 60; done ) &
MON=$!   # per-process GPU memory every minute
pids=""
for R in $ORDER; do arm=${R%-s*}; s=${R##*-s}
  python -B scripts/claude_lfsz_run.py run --arm $arm --seed $s --out W/$R > W/$R.log 2> W/$R.err &
  pids="$pids $!"; st "LAUNCH $R pid $!"; done
st LAUNCHED-ALL
for p in $pids; do wait $p; st "RUN-EXIT pid $p rc $?"; done
for R in $ORDER; do [ -s W/$R/result.json ] && st "RESULT $R" || st "DIED $R (no result.json)"; done
kill $MON 2>/dev/null; cp /root/r/gpumem.live W/gpumem.log 2>/dev/null
st DONE
