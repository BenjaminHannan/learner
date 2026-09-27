#!/bin/bash
# rsn-358t v3 on ONE vast rental (sleep research thread, 2026-09-27). Runs ON the rental, detached (setsid nohup), from /root/r.
# Same design as handoff/kit/sleep358uv/box/drive.sh. Pins torch 2.11.0+cu128 (BensPC's version; fail-closed), checks
# SEAL-code-v3 (22/22), runs the four checks of the BensPC task (envs selftest, 358t3 selftest, check-mask, audit) and Stage 0
# (the "loop  free=3 grad=2 cache=False" line must end in 0/12), then trains the 8 graded runs in the sealed order with the
# sealed command, starting each one only while at least 5 GB of GPU memory is free (at most one start per 90 s), seals both
# checkpoints of each run (final.pt raw, graded; final-ema.pt report only), then evaluates each checkpoint once. The report-only
# loop8-trm runs are not run here. Progress lines go to W/drive-state.txt; the last is DONE or FAILED <why>.
# It never edits code and never deletes anything.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-rsn358t-20260926
ORDER="loop-trm-s1 loop8-s1 loop-trm-s2 loop8-s2 loop-trm-s3 loop8-s3 loop-trm-s4 loop8-s4"
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
n=$(sha256sum -c $A/SEAL-code-v3.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 22 ] || fail "seal $n/22"
st "SEAL 22/22"
{ python -B scripts/claude_rsn358a_envs.py selftest; python -B scripts/claude_rsn358t3_run.py selftest; python -B scripts/claude_rsn358t3_run.py check-mask; python -B scripts/claude_rsn358t3_run.py audit; } > W/checks.txt 2>&1
[ "$(grep -c '^selftest ok' W/checks.txt)" = 2 ] && grep -q '^check-mask ok' W/checks.txt && [ "$(grep -c '300/300 puzzles show every needed symbol' W/checks.txt)" = 4 ] || fail "selftest/check-mask/audit (see W/checks.txt)"
st CHECKS-OK
python -B scripts/claude_stage0_autocast_grad.py > W/stage0.txt 2>&1
grep '^loop  free=3 grad=2 cache=False' W/stage0.txt | grep -q ' 0/12$' || fail "FIX-FAILS: Stage 0 cache-off line is not 0/12 (see W/stage0.txt)"
st STAGE0-OK
for R in $ORDER; do { [ -e W/$R ] || [ -e W/$R.log ]; } && fail "$R already exists"; done
( while :; do echo "$(date -u +%T) $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | tr '\n' ';')" >> /root/r/gpumem.live; sleep 60; done ) &
MON=$!   # per-process GPU memory every minute, so the next kit uses measured per-run memory
pids=""
for R in $ORDER; do arm=${R%-s*}; s=${R##*-s}
  w=0; while [ "$(freemb)" -lt 5120 ] 2>/dev/null; do [ $w = 0 ] && st "WAIT $R: $(freemb) MiB free"; w=1; sleep 60; done
  python -B scripts/claude_rsn358t3_run.py train --arm $arm --seed $s --out W/$R > W/$R.log 2> W/$R.err &
  pids="$pids $!"; st "LAUNCH $R pid $! ($(freemb) MiB free before it loads)"; sleep 90; done
for p in $pids; do wait $p; st "TRAIN-EXIT pid $p rc $?"; done
for R in $ORDER; do
  if [ -f W/$R/final.pt ] && [ -f W/$R/final-ema.pt ]; then
    for C in final.pt final-ema.pt; do echo "$(sha256sum W/$R/$C | cut -c1-64)  $R/$C" >> W/SEAL-run.sha256.txt; done; st "SEALED $R"
  else st "DIED $R (no final.pt/final-ema.pt)"; fi; done
ev() { python -B scripts/claude_rsn358t3_run.py eval --ckpt W/$1/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/$1/tests.json > W/$1.eval.log 2>&1; st "EVAL $1 raw rc $?"
       python -B scripts/claude_rsn358t3_run.py eval --ckpt W/$1/final-ema.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/$1/tests-ema.json > W/$1.eval-ema.log 2>&1; st "EVAL $1 ema rc $?"; }
epids=""; for R in $ORDER; do [ -f W/$R/final-ema.pt ] && grep -q " $R/final.pt\$" W/SEAL-run.sha256.txt && { ev $R & epids="$epids $!"; }; done
for p in $epids; do wait $p; done
kill $MON 2>/dev/null; cp /root/r/gpumem.live W/gpumem.log 2>/dev/null
st DONE
