#!/bin/bash
# slp-358n3 on ONE vast rental (sleep research thread, 2026-09-27). Runs ON the rental, detached (setsid nohup), from /root/r.
# Same design as handoff/kit/sleep358sv/box/drive.sh. Pins torch 2.11.0+cu128 (fail-closed), checks SEAL-code (18/18) and the
# 4 uploaded 358u checkpoints (4/4 against ck/expected.sha256, from 358u's SEAL-run), runs 358u's selftest, picks the day sizes
# on the GPU (the sealed rule), starts the RESUME check on the CPU, then runs the 4 seeds (s13 and s14 with the report-only L arm),
# each started only while 5 GB of GPU memory is free, seals each seed's slept S-final.pt, and waits for RESUME. Progress lines go
# to W/drive-state.txt; the last is DONE or FAILED <why>. It never edits code and never deletes anything.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-slp358n3-20260927
N3=scripts/claude_slp358n3_nights.py
ORDER="s13 s14 s15 s16"
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
n=$(sha256sum -c $A/SEAL-code.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 18 ] || fail "seal $n/18"
st "SEAL 18/18"
n=$(sha256sum -c ck/expected.sha256 2>/dev/null | grep -c ': OK$'); [ "$n" = 4 ] || fail "checkpoints $n/4"
st "CHECKPOINTS 4/4 (358u loop-s13..16, sha256 as sealed in 358u's SEAL-run)"
python -B scripts/claude_rsn358u_run.py selftest > W/checks.txt 2>&1
grep -q '^selftest ok' W/checks.txt || fail "358u selftest (see W/checks.txt)"
st CHECKS-OK
python -B $N3 pick-sizes --ckpts ck/s13/final.pt ck/s14/final.pt ck/s15/final.pt ck/s16/final.pt --out W/sizes.json > W/pick-sizes.log 2>&1
[ -s W/sizes.json ] || fail "pick-sizes (see W/pick-sizes.log)"
st "SIZES $(grep '^sizes' W/pick-sizes.log | tail -1)"
CUDA_VISIBLE_DEVICES="" python -B $N3 resume-check --ckpt ck/s13/final.pt --seed 13 --sizes W/sizes.json --out W/resume > W/resume.log 2>&1 &
RP=$!; st "RESUME started pid $RP (CPU)"
( while :; do echo "$(date -u +%T) $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | tr '\n' ';')" >> /root/r/gpumem.live; sleep 60; done ) &
MON=$!   # per-process GPU memory every minute, so the next kit uses measured per-run memory
for R in $ORDER; do { [ -e W/$R ] || [ -e W/$R.log ]; } && fail "$R already exists"; done
pids=""
for R in $ORDER; do s=${R#s}; L=""; { [ $s = 13 ] || [ $s = 14 ]; } && L=--long
  w=0; while [ "$(freemb)" -lt 5120 ] 2>/dev/null; do [ $w = 0 ] && st "WAIT $R: $(freemb) MiB free"; w=1; sleep 60; done
  python -B $N3 run --ckpt ck/$R/final.pt --seed $s --sizes W/sizes.json --out W/$R $L > W/$R.log 2> W/$R.err &
  pids="$pids $!"; st "LAUNCH $R pid $! $L ($(freemb) MiB free before it loads)"; sleep 60; done
for p in $pids; do wait $p; st "RUN-EXIT pid $p rc $?"; done
for R in $ORDER; do
  if [ -f W/$R/S-final.pt ] && [ -s W/$R/slp358n3-seed${R#s}.json ]; then echo "$(sha256sum W/$R/S-final.pt | cut -c1-64)  $R/S-final.pt" >> W/SEAL-run.sha256.txt; st "SEALED $R"
  else st "DIED $R (no S-final.pt or no result json)"; fi; done
while kill -0 $RP 2>/dev/null; do st "RESUME still running on the CPU"; sleep 600; done   # a heartbeat, so the guard does not read a CPU-only stretch as a stall
wait $RP; st "RESUME rc $? $(tr -d '\n ' < W/resume/resume.json 2>/dev/null | grep -o '"RESUME_identical":[a-z]*')"
kill $MON 2>/dev/null; cp /root/r/gpumem.live W/gpumem.log 2>/dev/null
st DONE
