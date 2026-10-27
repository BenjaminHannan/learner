#!/bin/bash
# dir-s3 (numbers, nearest valid answer) on ONE vast rental. Copy of handoff/kit/lfszv/box/drive.sh, adapted (helper S3, 2026-09-29).
# Runs ON the rental, detached (setsid nohup), from /root/r. Pins torch 2.11.0+cu128 (fail-closed), checks the three seals (358u 20 lines,
# dir-h2 3, dir-s3 3), runs the selftests and Stage 0 (the "loop  free=3 grad=2 cache=False" line must end in 0/12), trains all 8 nets at once
# (--mode min|random x loop|plain x seeds 13, 14, defaults only), then per net: seal the final.pt sha256, poison, eval (counts only), extra.
# final.pt files are moved to /root/r/CK (not copied back; they are lost when the rental is destroyed). Progress lines go to
# W/drive-state.txt; the last is DONE or FAILED <why>. It never edits code and never deletes anything.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
ORDER="min-loop-s13 min-plain-s13 min-loop-s14 min-plain-s14 random-loop-s13 random-plain-s13 random-loop-s14 random-plain-s14"
mkdir -p W CK
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
st START
st "HOST nproc $(nproc --all) disk $(df -h /root | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > W/pip.log 2>&1 || fail "pip install torch==2.11.0 (see W/pip.log)"
python -c "import torch; print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))" > W/torch.txt 2>&1
grep -q '^torch 2.11.0' W/torch.txt && grep -q ' True ' W/torch.txt || fail "torch check: $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
st "TORCH $(cat W/torch.txt)"
sha256sum -c artifacts/claude-rsn358u-20260927/SEAL-code.sha256.txt > W/seal1.txt 2>&1; n1=$(grep -c ': OK$' W/seal1.txt)
sha256sum -c artifacts/claude-dir-s3-numbers-20260929/SEAL-s3.sha256.txt > W/seal2.txt 2>&1; n2=$(grep -c ': OK$' W/seal2.txt)
sha256sum -c artifacts/claude-dir-h2-numbers-20260928/SEAL-h2.sha256.txt > W/seal3.txt 2>&1; n3=$(grep -c ': OK$' W/seal3.txt)
[ "$n1" = 20 ] && [ "$n2" = 3 ] && [ "$n3" = 3 ] || fail "seal $n1/20 $n2/3 $n3/3"
st "SEAL 20/20 3/3 3/3"
{ python -B scripts/claude_rsn358a_envs.py selftest && python -B scripts/claude_dir_h2_pool.py selftest && python -B scripts/claude_rsn358u_run.py selftest \
  && python -B scripts/claude_dir_s3_labels.py selftest && python -B scripts/claude_dir_s3_run.py selftest && python -B scripts/claude_dir_s3_run.py check-mask; } > W/checks.txt 2>&1
for m in "^selftest ok: [0-9]* four-hands" "^s3 labels selftest ok" "^s3 run selftest ok" "^check-mask ok"; do grep -q "$m" W/checks.txt || fail "checks: '$m' missing (see W/checks.txt)"; done
[ "$(grep -c 'selftest ok' W/checks.txt)" -ge 5 ] || fail "checks: fewer than 5 selftest ok lines (see W/checks.txt)"
st CHECKS-OK
python -B scripts/claude_stage0_autocast_grad.py > W/stage0.txt 2>&1
grep '^loop  free=3 grad=2 cache=False' W/stage0.txt | grep -q ' 0/12$' || fail "FIX-FAILS: Stage 0 cache-off line is not 0/12 (see W/stage0.txt)"
st STAGE0-OK
for R in $ORDER; do { [ -e W/$R ] || [ -e W/$R.log ]; } && fail "$R already exists"; done
( while :; do echo "$(date -u +%T) $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | tr '\n' ';')" >> /root/r/gpumem.live; sleep 60; done ) &
MON=$!
pids=""
for R in $ORDER; do m=${R%%-*}; rest=${R#*-}; arm=${rest%-s*}; s=${rest##*-s}
  python -B scripts/claude_dir_s3_run.py train --mode $m --arm $arm --seed $s --out W/$R > W/$R.log 2> W/$R.err &
  pids="$pids $!"; st "LAUNCH $R pid $!"; done
st LAUNCHED-ALL
for p in $pids; do wait $p; st "RUN-EXIT pid $p rc $?"; done
for R in $ORDER; do m=${R%%-*}
  if [ ! -s W/$R/final.pt ]; then st "DIED $R (no final.pt)"; continue; fi
  echo "$(sha256sum W/$R/final.pt | cut -d' ' -f1)  $m/${R#*-}/final.pt" >> W/SEAL-run.sha256.txt
  python -B scripts/claude_dir_s3_run.py poison --ckpt W/$R/final.pt --out W/$R/poison.json > W/$R.poison.txt 2>&1 || { st "DIED $R (poison failed)"; continue; }
  python -B scripts/claude_dir_s3_run.py eval --ckpt W/$R/final.pt --tests artifacts/claude-rsn358i-20260926/tests --out W/$R/tests.json > W/$R.eval.txt 2>&1 || { st "DIED $R (eval failed)"; continue; }
  python -B scripts/claude_dir_s3_run.py extra --mode $m --ckpt W/$R/final.pt --out W/$R/extra.json > W/$R.extra.txt 2>&1 || { st "DIED $R (extra failed)"; continue; }
  mv W/$R/final.pt CK/$R.pt; st "RESULT $R"
done
kill $MON 2>/dev/null; cp /root/r/gpumem.live W/gpumem.log 2>/dev/null
st DONE
