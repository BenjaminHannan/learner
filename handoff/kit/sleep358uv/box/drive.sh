#!/bin/bash
# rsn-358u on ONE vast rental (sleep research thread, 2026-09-27). Runs ON the rental, detached (setsid nohup), from /root/r.
# Pins torch 2.11.0+cu128 (BensPC's version), checks the seal and the selftests, trains all 8 sealed runs at once with the
# sealed command, seals each final.pt, then runs V1 poison and the test eval once per checkpoint. Progress lines go to
# W/drive-state.txt; the last line is DONE or FAILED <why>. It never edits code and never deletes anything.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-rsn358u-20260927
ORDER="loop-s13 plain-s13 loop-s14 plain-s14 loop-s15 plain-s15 loop-s16 plain-s16"
mkdir -p W
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
st START
st "HOST nproc $(nproc) disk $(df -h /root | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > W/pip.log 2>&1 || fail "pip install torch==2.11.0 (see W/pip.log)"
python -c "import torch; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))" > W/torch.txt 2>&1
grep -q '^torch 2.11.0' W/torch.txt && grep -q ' True ' W/torch.txt || fail "torch check: $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
st "TORCH $(cat W/torch.txt)"
n=$(sha256sum -c $A/SEAL-code.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 20 ] || fail "seal $n/20"
st "SEAL 20/20"
{ python -B scripts/claude_rsn358a_envs.py selftest; python -B scripts/claude_rsn358u_run.py selftest; python -B scripts/claude_rsn358u_run.py check-mask; } > W/checks.txt 2>&1
grep -q '^selftest ok: every item gets env 0' W/checks.txt && grep -q '^check-mask ok' W/checks.txt || fail "selftest/check-mask (see W/checks.txt)"
st CHECKS-OK
for R in $ORDER; do { [ -e W/$R ] || [ -e W/$R.log ]; } && fail "$R already exists"; done
pids=""
for R in $ORDER; do arm=${R%-s*}; s=${R##*-s}
  python -B scripts/claude_rsn358u_run.py train --arm $arm --seed $s --out W/$R > W/$R.log 2> W/$R.err &
  pids="$pids $!"; st "LAUNCH $R pid $!"; done
for p in $pids; do wait $p; st "TRAIN-EXIT pid $p rc $?"; done
for R in $ORDER; do
  if [ -f W/$R/final.pt ]; then echo "$(sha256sum W/$R/final.pt | cut -c1-64)  $R/final.pt" >> W/SEAL-run.sha256.txt; st "SEALED $R"
  else st "DIED $R (no final.pt)"; fi; done
ev() { python -B scripts/claude_rsn358u_run.py poison --ckpt W/$1/final.pt --out W/$1/poison.json > W/$1.poison.log 2>&1; st "POISON $1 rc $?"
       python -B scripts/claude_rsn358u_run.py eval --ckpt W/$1/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/$1/tests.json > W/$1.eval.log 2>&1; st "EVAL $1 rc $?"; }
epids=""; for R in $ORDER; do [ -f W/$R/final.pt ] && { ev $R & epids="$epids $!"; }; done
for p in $epids; do wait $p; done
st DONE
