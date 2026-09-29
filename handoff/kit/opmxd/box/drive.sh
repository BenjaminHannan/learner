#!/bin/bash
# opus-mxd (sparse-MoE mxd-1: GPU smoke + phase 1, NO holdout) on ONE vast rental. Copy of handoff/kit/s3v/box/drive.sh, adapted.
# Runs ON the rental, detached (setsid nohup), from /root/r (OPMXD_ROOT overrides it for the kit's fake-run test only).
# Steps = the science steps of handoff/queue/mxd-1-smoke-phase1-benspc.md: torch pin (fail-closed), SEAL.sha256.txt all OK, loop sources checked,
# selftest ("selftest": "ok"), smoke (PASS true or false, go on either way; a crash = FAILED), phase 1 with --loop-source-root, then done.
# Torch pin: torch==2.14.0 from the cu128 wheel index. 2.14.0 is the version the sealed selftest and CHECKS-before-gpu ran on (as +cpu), so the CPU half of the
# smoke, the GPU half and the sealed checks share one torch release; cu128 because the 5090-class cards need sm_120 and the base image driver is a 12.8 one.
# Checked 2026-09-29 (Opus manager): the cu128 index has no 2.14.0; cu126 has torch-2.14.0+cu126 cp311 manylinux x86_64, so cu126 is used and sm_120 cards are excluded at offer time.
# Phase 1 is run as its six parts in the MONEY ORDER (the driver's own `phase --phase 1` does the same six calls in the order source s0, source s1,
# MX ladder s0, s1, loop control s0, s1): source MX s0, MX ladder s0, loop control s0, then seed 1, so a money stop leaves seed 0 whole. Each part is the
# driver's own subcommand (source / dev, stages kept as in phase 1), each skips what already exists, and each seeds itself; equivalence with the `phase`
# order is expected, not tested. One resume (identical rerun) is allowed in total on a non-zero exit; a second death = FAILED.
# Progress lines go to W/drive-state.txt; the last is DONE or FAILED <why>. The rental's small results are mirrored into W/moe (never a .pt).
# It never edits code and never deletes anything.
set -u
R=${OPMXD_ROOT:-/root/r}
ART=artifacts/claude-moe-deep-20260929
# W/moe mirrors the small result files (the guard's copy-back runs `drive.sh mirror` first, so partial results are not lost)
mirror() { mkdir -p "$R/W/moe"; ( cd "$R/$ART" 2>/dev/null && find runs eq-runs SMOKE-gpu.json TIMING-gpu.json -type f ! -name '*.pt' 2>/dev/null | tar -cf - -T - 2>/dev/null ) | tar -xf - -C "$R/W/moe" 2>/dev/null; return 0; }
[ "${1:-}" = mirror ] && { mirror; exit 0; }
cd "$R" || exit 1
export PATH=/opt/conda/bin:$PATH PYTHONUTF8=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 HF_HUB_OFFLINE=1
TORCH_PIN=2.14.0; CUDA_TAG=cu126
RUN=scripts/claude_moe_deep_run.py
mkdir -p W
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; mirror; exit 1; }
st START
st "HOST nproc $(nproc) disk $(df -h /root | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
pip install --no-cache-dir torch==$TORCH_PIN --index-url https://download.pytorch.org/whl/$CUDA_TAG > W/pip.log 2>&1 || fail "pip install torch==$TORCH_PIN (see W/pip.log)"
python -c "import torch; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))" > W/torch.txt 2>&1
grep -q "^torch $TORCH_PIN" W/torch.txt && grep -q ' True ' W/torch.txt || fail "NO-CUDA or wrong torch: $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
st "TORCH $(cat W/torch.txt)"
free=$(df -BG --output=avail /root | tail -1 | tr -dc '0-9'); [ "${free:-0}" -ge 10 ] || fail "LOW-DISK ${free:-?} GB free under 10"
# SEAL (mxd-1 step 4): every line OK
sha256sum -c $ART/SEAL.sha256.txt > W/seal.txt 2>&1; nok=$(grep -c ': OK$' W/seal.txt); ntot=$(grep -c . $ART/SEAL.sha256.txt)
[ "$nok" = "$ntot" ] && [ "$ntot" = 6 ] || fail "SEAL-MISMATCH $nok/$ntot OK (expected 6/6; see W/seal.txt)"
st "SEAL $nok/$ntot"
# loop control sources (mxd-1 step 2/3): both present and matching the recorded sha256, else go on without them
LOOPARG=""; lok=1
for S in 0 1; do d=loopsrc/qual-loop-s$S
  exp=$(awk -v p="qual-loop-s$S/source.pt" '$2==p {print $1}' artifacts/claude-distill-20260928/checkpoints-sha256.txt)
  [ -n "$exp" ] && [ -s $d/source.pt ] && [ -s $d/source.json ] && [ "$(sha256sum $d/source.pt | cut -d' ' -f1)" = "$exp" ] || lok=0; done
if [ $lok = 1 ]; then LOOPARG="--loop-source-root loopsrc"; st "LOOP-SOURCES ok (2 of 2 match the recorded sha256)"
else st "LOOP-SOURCE-MISSING: loop control ladders will be skipped (no --loop-source-root)"; fi
# selftest (mxd-1 step 5): CPU, no training. (It rewrites selftest.json in the rental's copy of the sealed folder; the seal was checked before and it is not copied back.)
python -B $RUN selftest --threads 2 > W/selftest_rental.txt 2>&1; src=$?
[ $src = 0 ] && grep -q '"selftest": "ok"' W/selftest_rental.txt || fail "SELFTEST-FAIL rc $src (see W/selftest_rental.txt): $(tail -2 W/selftest_rental.txt | tr '\n' ' ' | cut -c1-200)"
st SELFTEST-OK
st CHECKS-OK
( while :; do sleep 600; mirror; done ) &
MON=$!
# smoke and timing (mxd-1 step 6): PASS true/false, go on either way; a crash (no SMOKE-gpu.json, or a non-zero exit that is not SMOKE-FAIL) is FAILED
python -B $RUN smoke --device cuda --threads 2 > W/smoke_log.txt 2>&1; src=$?
if [ ! -s $ART/SMOKE-gpu.json ] || { [ $src != 0 ] && ! grep -q 'SMOKE-FAIL' W/smoke_log.txt; }; then kill $MON 2>/dev/null; fail "SMOKE-CRASH rc $src (see W/smoke_log.txt): $(tail -3 W/smoke_log.txt | tr '\n' ' ' | cut -c1-240)"; fi
if grep -Eq '"PASS": *true' $ART/SMOKE-gpu.json; then sp=true; else sp=false; fi
mirror; st "SMOKE-DONE PASS $sp (rc $src)"
# phase 1, part by part in the money order
RESUMED=0
part() { pname=$1; shift
  st "PART-START $pname"
  while :; do
    n0=$(wc -l < W/log_phase1.txt 2>/dev/null || echo 0)
    python -B $RUN "$@" --device cuda --threads 2 >> W/log_phase1.txt 2>&1; rc=$?
    if [ $rc = 0 ]; then st "PART-DONE $pname"; mirror; return 0; fi
    # a missing or unqualified source skips its ladder, as the driver's own phase loop does (never a death)
    if tail -n +$((n0+1)) W/log_phase1.txt | grep -qE '^(SOURCE-NOT-QUALIFIED|WAITING|LOOP-SOURCE-MISMATCH)'; then st "PART-SKIPPED $pname (rc $rc: $(tail -n +$((n0+1)) W/log_phase1.txt | grep -E '^(SOURCE-NOT-QUALIFIED|WAITING|LOOP-SOURCE-MISMATCH)' | head -1 | cut -c1-120))"; mirror; return 0; fi
    mirror
    if [ $RESUMED = 0 ]; then RESUMED=1; st "RESUME-ONCE $pname rc $rc"; continue; fi
    kill $MON 2>/dev/null; fail "PHASE1-DIED at $pname rc $rc, second death (see W/log_phase1.txt): $(tail -3 W/log_phase1.txt | tr '\n' ' ' | cut -c1-240)"
  done; }
for s in 0 1; do
  part src-s$s source --cfg L8-E64 --seed $s
  part mx-s$s dev --cfg L8-E64 --seed $s --init pre
  if [ -n "$LOOPARG" ]; then part ctl-s$s dev --cfg loopctl --seed $s --init pre $LOOPARG
  else st "PART-SKIPPED ctl-s$s (LOOP-SOURCE-MISSING)"; fi
done
echo '{"phase": "phase1_done", "by": "opmxd drive.sh, six parts in the money order"}' >> W/log_phase1.txt
kill $MON 2>/dev/null; mirror
st DONE
