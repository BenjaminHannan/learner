#!/bin/bash
# dir-h6 (sleep length, arm B) on ONE vast rental. Runs ON the rental, detached (setsid nohup), from /root/r.
# Kit sleeph6r (helper H7, 2026-09-28), from handoff/kit/sleep358n3r/box/drive.sh with the changes the queue file of helper H6 asks for:
# no pick-sizes (the sealed slp-358n3 day sizes are copied), no RESUME, no S-final.pt sealing, a smoke step first, arms N S L B in every seed.
# Order: torch check (torch >= 2.11 pinned, CUDA on, compute capability >= 8.0; recorded) -> seals (slp-358n3 18 of 18, dir-h6 3 of 3)
# -> the 4 uploaded 358u loop checkpoints (4 of 4) -> 358u's selftest -> day sizes (sums 12, grids 7) -> `smoke` (stop with FAILED if
# it does not print "smoke ok"; the script is never fixed here) -> the 4 seed runs, each started only while 5 GB of GPU memory is free.
# Progress lines go to W/drive-state.txt; the last is DONE or FAILED <why>. The pids of drive.sh, the runs and the GPU-memory monitor
# go to W/pids.txt (one `kind name pid` line each) so the Mac guard can halt them by exact pid (box/halt.sh). It never edits code,
# never deletes anything and never re-runs a failed seed.
set -u
cd /root/r || exit 1
export PATH=/opt/conda/bin:$PATH
A=artifacts/claude-dir-h6-sleeplen-20260928
N3A=artifacts/claude-slp358n3-20260927
H6=scripts/claude_dir_h6_sleeplen.py
ORDER="s13 s14 s15 s16"
mkdir -p W
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
freemb() { nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '; }
echo "drive drive $$" > W/pids.txt
st START
st "HOST nproc $(nproc) disk $(df -h /root | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | head -1)"
pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128 > W/pip.log 2>&1 || fail "pip install torch==2.11.0 (see W/pip.log)"
pip freeze 2>/dev/null | grep -i -E '^(torch|nvidia-cu|triton)' > W/pip-freeze.txt
python -c "import torch; c = torch.cuda.get_device_capability(0); print('torch', torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0), c[0], c[1])" > W/torch.txt 2>&1
okt=$(head -1 W/torch.txt | awk '$1=="torch" { split($2, v, "."); if ((v[1] > 2 || (v[1] == 2 && v[2] >= 11)) && $4 == "True" && ($(NF-1) * 10 + $NF) >= 80) print "ok" }')
[ "$okt" = ok ] || fail "torch check (needs torch >= 2.11, CUDA available, compute capability >= 8.0): $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
st "TORCH $(head -1 W/torch.txt)"
{ sha256sum -c $N3A/SEAL-code.sha256.txt; sha256sum -c $A/SEAL-code.sha256.txt; } > W/seals.txt 2>&1
n=$(sha256sum -c $N3A/SEAL-code.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 18 ] || fail "slp-358n3 seal $n/18 (see W/seals.txt)"
n=$(sha256sum -c $A/SEAL-code.sha256.txt 2>/dev/null | grep -c ': OK$'); [ "$n" = 3 ] || fail "dir-h6 seal $n/3 (see W/seals.txt)"
st "SEAL slp-358n3 18/18, dir-h6 3/3"
n=$(sha256sum -c ck/expected.sha256 2>/dev/null | grep -c ': OK$'); [ "$n" = 4 ] || fail "checkpoints $n/4"
st "CHECKPOINTS 4/4 (358u loop-s13..16, sha256 as sealed in 358u's SEAL-run)"
python -B scripts/claude_rsn358u_run.py selftest > W/checks.txt 2>&1
grep -q '^selftest ok' W/checks.txt || fail "358u selftest (see W/checks.txt)"
st CHECKS-OK
cp $N3A/run-vast/sizes.json W/sizes.json
sz=$(python -c "import json; d = json.load(open('W/sizes.json'))['sizes']; print(d.get('sums'), d.get('grids'))" 2>&1)
[ "$sz" = "12 7" ] || fail "W/sizes.json is not sums 12, grids 7 (got: $(echo "$sz" | tail -1 | cut -c1-100))"
st "SIZES sums 12 grids 7 (slp-358n3's run-vast/sizes.json, copied not re-picked; sha256 $(sha256sum W/sizes.json | cut -c1-16))"
python -B $H6 smoke > W/smoke.txt 2>&1
grep -q '^smoke ok' W/smoke.txt || fail "smoke did not print 'smoke ok' (first traceback verbatim in W/smoke.txt): $(grep -m1 -E '^[A-Za-z_.]*(Error|Exception)' W/smoke.txt | cut -c1-160)"
st "SMOKE ok"
for R in $ORDER; do { [ -e W/$R ] || [ -e W/$R.log ]; } && fail "$R already exists"; done
( while :; do echo "$(date -u +%T) $(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader 2>/dev/null | tr '\n' ';')" >> /root/r/gpumem.live; sleep 60; done ) &
MON=$!   # per-process GPU memory every minute, so the next kit uses measured per-run memory
echo "mon gpumem $MON" >> W/pids.txt
pids=""
for R in $ORDER; do s=${R#s}
  w=0; while [ "$(freemb)" -lt 5120 ] 2>/dev/null; do [ $w = 0 ] && st "WAIT $R: $(freemb) MiB free"; w=1; sleep 60; done
  python -B $H6 run --ckpt ck/$R/final.pt --seed $s --sizes W/sizes.json --out W/$R > W/$R.log 2> W/$R.err &
  p=$!; pids="$pids $p:$R"; echo "run $R $p" >> W/pids.txt
  st "LAUNCH $R pid $p ($(freemb) MiB free before it loads)"; sleep 60; done
for pr in $pids; do p=${pr%%:*}; R=${pr##*:}; s=${R#s}
  wait $p; rc=$?; st "RUN-EXIT $R pid $p rc $rc"
  if [ $rc = 0 ] && [ -s W/$R/dirh6-seed$s.json ]; then st "FINISHED $R"; else st "DIED $R (rc $rc, result json $([ -s W/$R/dirh6-seed$s.json ] && echo present || echo missing))"; fi; done
kill $MON 2>/dev/null; cp /root/r/gpumem.live W/gpumem.log 2>/dev/null
st DONE
