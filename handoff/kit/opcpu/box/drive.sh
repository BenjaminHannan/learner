#!/bin/bash
# opcpu: sealed CPU-only tests on ONE rented many-core box. Runs ON the rental, detached (setsid nohup), from the pinned tree
# $R = <base>/r (base = /root on a rental). Builds a venv with torch 2.14.0 CPU + numpy (fail-closed), then runs, each from its own
# private archive of the pinned tree and each replicating its Mac queue file (see DEVIATIONS.md):
#   1 ks-1-lead0 (rebuilds the loop nets, then lead0)  ->  2 s2think and 3 trn-decode wait for its nets
#   4 pond-a/b/c/z-dev and 5 pond-doubt (after all four)    6 s1-loop and s1-plain
# Progress lines go to W/drive-state.txt: JOB <name> START|END rc N|SKIPPED why; the last line is DONE or FAILED <why> (setup only).
# It never edits sealed code and never deletes anything.
set -u
R=$(cd "$(dirname "$0")/../../../.." && pwd); B=$(dirname "$R"); cd "$B" || exit 1
export HOME=$B PATH=/opt/conda/bin:$PATH PYTHONUTF8=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=""
export OPC_R=$R OPC_IN=$B/in OPC_OUT=$B/out OPC_PYX=$B/venv/bin/python
export KS_SRC=$B/in/artifacts/claude-fewex-20260927 KS_NETS=$B/premonition-ks/nets    # the nets ks rebuilds; s2think, trn and pond-doubt read them
NUMPY=${OPC_NUMPY:-2.4.6}; TORCH=${OPC_TORCH:-2.14.0}
KD=$R/handoff/kit/opcpu/box; A_KS=artifacts/claude-dir-ks-20260928
mkdir -p W out in
st() { echo "$(date -u +%FT%TZ) $*" >> W/drive-state.txt; }
fail() { st "FAILED $*"; exit 1; }
st START
st "HOST nproc $(nproc) mem_gb $(awk '/MemTotal/{printf "%d", $2/1048576}' /proc/meminfo) disk $(df -h "$B" | tail -1 | awk '{print $4}') free; $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1) (GPU never used)"
[ "$(nproc)" -ge "${OPC_MINCORES:-32}" ] || fail "nproc $(nproc) is under ${OPC_MINCORES:-32}"
# inputs from the Mac: hash-checked on the rental against the list the Mac made
[ -s in/INPUTS.sha256 ] && (cd in && sha256sum -c INPUTS.sha256 > ../W/inputs-check.txt 2>&1) || fail "inputs do not match in/INPUTS.sha256 (see W/inputs-check.txt)"
st "INPUTS $(grep -c ': OK$' W/inputs-check.txt) files match"
"${OPC_BOOTPY:-python}" -m venv "$B/venv" > W/venv.log 2>&1 || fail "python -m venv (see W/venv.log)"
"$B/venv/bin/python" -m pip install --no-cache-dir "torch==$TORCH" --index-url https://download.pytorch.org/whl/cpu > W/pip.log 2>&1 \
  && "$B/venv/bin/python" -m pip install --no-cache-dir "numpy==$NUMPY" >> W/pip.log 2>&1 || fail "pip install torch==$TORCH (cpu wheel) and numpy==$NUMPY (see W/pip.log)"
"$B/venv/bin/python" -c "import torch, numpy; print('torch', torch.__version__, 'numpy', numpy.__version__, 'cuda', torch.cuda.is_available(), 'built-with-cuda', torch.version.cuda)" > W/torch.txt 2>&1
grep -q "^torch $TORCH+cpu numpy $NUMPY cuda False built-with-cuda None" W/torch.txt || fail "torch check: $(tr '\n' ' ' < W/torch.txt | cut -c1-200)"
st "TORCH $(cat W/torch.txt)"
skip() { st "JOB $1 SKIPPED $2"; }
run_job() {   # run_job <name> <cap minutes> <script> [args]: the job's own STOP RULE ends only that job
  n=$1; cap=$2; sc=$3; shift 3
  st "JOB $n START"; timeout -k 30 "${cap}m" bash "$KD/$sc" "$@" > "W/$n.out" 2>&1; rc=$?
  st "JOB $n END rc $rc$([ $rc = 124 ] && echo ' (its own time cap)')"; }
ks_ready() { [ -f "$B/premonition-ks/$A_KS/prep/s0.json" ] && [ -f "$B/premonition-ks/$A_KS/prep/s1.json" ]; }
# wave 1: everything that does not need the ks nets (the box has >= 32 cores; every job is single- or 2-thread as its queue file says)
( run_job ks-1-lead0 300 job-ks.sh ) & KSP=$!
st "LAUNCH ks-1-lead0 subshell $KSP"
POND=""
for arm in a b c z; do ( run_job pond-$arm-dev 300 job-pond.sh $arm ) & POND="$POND $!"; st "LAUNCH pond-$arm-dev subshell $!"; done
( run_job s1-loop 330 job-s1.sh loop ) & S1L=$!; st "LAUNCH s1-loop subshell $S1L"
if [ -f in/QUAL-PLAIN-OK ]; then ( run_job s1-plain 330 job-s1.sh plain ) & S1P=$!; st "LAUNCH s1-plain subshell $S1P"
else skip s1-plain "qual-plain sources not sent from the Mac (see in/INPUTS.txt)"; S1P=""; fi
# wave 2: after the ks nets exist (prep done for both seeds) or ks ended without them (then the jobs print their own WAITING / MISSING)
( while ! ks_ready && kill -0 "$KSP" 2>/dev/null; do sleep 30; done
  ( run_job s2think 120 job-s2think.sh ) &
  if [ -f in/TRN-OK ]; then ( run_job trn-decode 300 job-trn.sh ) & else skip trn-decode "trn Mac inputs (source.pt of loop and plain nets, plain k16384) not all sent (see in/INPUTS.txt)"; fi
  wait ) & W2=$!
# wave 3: pond-doubt after all four pond arms have ended (it skips arms that did not finish, as its queue file says)
( for p in $POND; do while kill -0 "$p" 2>/dev/null; do sleep 30; done; done; run_job pond-doubt 120 job-doubt.sh ) & W3=$!
st LAUNCHED-ALL
wait
st DONE
