#!/bin/bash
# rsn-358s on ONE vast rental (sleep research thread, 2026-09-27). Runs ON the rental, detached (setsid nohup), from /root/r.
# Same design as handoff/kit/sleep358tv/box/drive.sh. Pins torch 2.11.0+cu128 (BensPC's version; fail-closed), checks
# SEAL-code (19/19), runs 358s's selftest and check-mask, then trains all 8 3x runs (loop 2 x d896, plain 8 x d448, seeds 9-12)
# in the sealed order with the sealed command, starting each one only while at least 5 GB of GPU memory is free (at most one
# start per 5 minutes, as on BensPC), seals each final.pt, then evaluates each checkpoint once. Progress lines go to
# W/drive-state.txt; the last is DONE or FAILED <why>. It never edits code and never deletes anything.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-rsn358s-20260926
ORDER="loop-s9 plain-s9 loop-s10 plain-s10 loop-s11 plain-s11 loop-s12 plain-s12"
mkdir -p W
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
freemb() { nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
st START
st "HOST nproc $(nproc) disk $(df -h /root | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > W/pip.log 2>&1 || fail "pip install torch==2.11.0 (see W/pip.log)"
python -c "import torch; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))" > W/torch.txt 2>&1
grep -q '^torch 2.11.0' W/torch.txt && grep -q ' True ' W/torch.txt || fail "torch check: $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
st "TORCH $(cat W/torch.txt)"
n=$(sha256sum -c $A/SEAL-code.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 19 ] || fail "seal $n/19"
st "SEAL 19/19"
{ python -B scripts/claude_rsn358s_run.py selftest; python -B scripts/claude_rsn358s_run.py check-mask; } > W/checks.txt 2>&1
grep -q '^selftest ok: 3x arms' W/checks.txt && grep -q '^check-mask ok' W/checks.txt || fail "selftest/check-mask (see W/checks.txt)"
st CHECKS-OK
for R in $ORDER; do { [ -e W/$R ] || [ -e W/$R.log ]; } && fail "$R already exists"; done
( while :; do echo "$(date -u +%T) $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | tr '\n' ';')" >> /root/r/gpumem.live; sleep 60; done ) &
MON=$!   # per-process GPU memory every minute, so the next kit uses measured per-run memory
pids=""
for R in $ORDER; do arm=${R%-s*}; s=${R##*-s}
  w=0; while [ "$(freemb)" -lt 5120 ] 2>/dev/null; do [ $w = 0 ] && st "WAIT $R: $(freemb) MiB free"; w=1; sleep 60; done
  python -B scripts/claude_rsn358s_run.py train --arm $arm --seed $s --out W/$R > W/$R.log 2> W/$R.err &
  pids="$pids $!"; st "LAUNCH $R pid $! ($(freemb) MiB free before it loads)"; sleep 300; done
for p in $pids; do wait $p; st "TRAIN-EXIT pid $p rc $?"; done
for R in $ORDER; do
  if [ -f W/$R/final.pt ]; then echo "$(sha256sum W/$R/final.pt | cut -c1-64)  $R/final.pt" >> W/SEAL-run.sha256.txt; st "SEALED $R"
  else st "DIED $R (no final.pt)"; fi; done
ev() { python -B scripts/claude_rsn358s_run.py eval --ckpt W/$1/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/$1/tests.json > W/$1.eval.log 2>&1; st "EVAL $1 rc $?"; }
epids=""; for R in $ORDER; do grep -q " $R/final.pt\$" W/SEAL-run.sha256.txt 2>/dev/null && { ev $R & epids="$epids $!"; }; done
for p in $epids; do wait $p; done
kill $MON 2>/dev/null; cp /root/r/gpumem.live W/gpumem.log 2>/dev/null
st DONE
