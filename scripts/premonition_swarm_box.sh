#!/usr/bin/env bash
# Swarm screen box script (design/swarm/BOX-SPEC.md): pins the commit and file hashes, builds the village data,
# runs C0, then (unless C0 says stop) trains D1 and S0 x seeds 0-2, evaluates, and writes the S0 readout.
# It never destroys the box: the rental agent does that after a checked copy-back of swarm-screen-out.tgz.
#
#   PIN=<sealed commit> DPH=<billed $/h> bash scripts/premonition_swarm_box.sh            # on the box
#   DRYRUN=1 PIN=$(git rev-parse HEAD) bash scripts/premonition_swarm_box.sh             # CPU dry run (tiny preset)
#
# ENV
#   PIN      the sealed commit; the script refuses unless `git rev-parse HEAD` equals it.
#   DPH      the billed dollars per hour (required off DRYRUN). The script refuses MAXH x DPH above CAP.
#   MAXH     hours; the script starts no step after it and cuts a running step at it (default 8.0).
#   CAP      dollars (default 4.20, ruling Q28).
#   PART     c0 | s0 | all (default all). c0 stops after C0 whatever it says. s0 starts at the trains and needs the
#            data.json and c0.json of an earlier c0 part in OUT.
#   DRYRUN   1 = the CPU dry run: tiny preset and visits, cpu, T = 120 s (one CPU step is ~2% of 30 s, the whole
#            +-2% seconds band of M5, so 30 s voids on one step; see BOX-SPEC), no money check, and the S1 tiny arm +
#            lesions are run so that MARKS-S1 is proven computable too. Like the real run it needs a clean tree and
#            the COMMITTED manifest. Its numbers mean nothing.
#   CHECK_ONLY  1 = run every refusal check (PIN, clean tree, OUT holds no tracked file, manifest, money, CUDA), then exit
#            0 before any step: a pre-flight on the box, and what the tests run.
#   STOP_OVERRIDE  non-empty text (the coordinator's ruling) lets the trains start although c0.json says
#            stop_and_ask / money_stop. Logged.
#   OUT, PY, WORKERS, C0_EXTRA, DRY_MAXTOK  output folder, python, data workers, extra c0 args, the dry run's
#            per-batch token cap (a CPU batch of 55,000 tokens takes seconds, which would break the +-2% seconds rule).
# Exit codes: 2 refused, 3 stop-and-ask, 4 MAXH reached, anything else: a step failed.
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
cd "$ROOT"
PIN=${PIN:-}
DPH=${DPH:-}
MAXH=${MAXH:-8.0}
CAP=${CAP:-4.20}
PART=${PART:-all}
DRYRUN=${DRYRUN:-0}
PY=${PY:-python}
STOP_OVERRIDE=${STOP_OVERRIDE:-}
C0_EXTRA=${C0_EXTRA:-}
RUN=claude-swarm-screen-20261018
if [ "$DRYRUN" = 1 ]; then
  SIZE=tiny; DEVICE=cpu; VISITS=tiny; DPH=${DPH:-0.40}; DRY_MAXTOK=${DRY_MAXTOK:-3000}
  OUT=${OUT:-$ROOT/artifacts/$RUN/dryrun-$(git -C "$ROOT" rev-parse --short=9 HEAD)}   # fresh per commit
  CKPT=artifacts/$RUN/ckpt-dryrun
  C0_ARGS="--rounds 3 --warmup 2 --timed 4 --chunk 2 --t-override 120 --max-tokens $DRY_MAXTOK $C0_EXTRA"
  TRAIN_ARGS="--max-tokens $DRY_MAXTOK"
else
  SIZE=full; DEVICE=cuda; VISITS=large
  OUT=${OUT:-$ROOT/artifacts/$RUN/out}; CKPT=artifacts/$RUN/ckpt   # git-ignored: outputs never dirty the tree
  C0_ARGS="--rounds 3 --warmup 10 --timed 40 --chunk 5 $C0_EXTRA"
  TRAIN_ARGS=""
fi
WORKERS=${WORKERS:-0}
SCREEN="$PY -B scripts/premonition_swarm_screen.py"
MARKS="$PY -B scripts/premonition_swarm_marks.py"
COMMON="--device $DEVICE --size $SIZE --workers $WORKERS"
# OUT must hold no git-tracked file (review round 3, third pass, item 1). Writing box.log into a tracked folder dirties
# the tree and trips the clean-tree check below. This runs before anything is written.
TRACKED=$(git -C "$ROOT" ls-files -- "$OUT" | head -5)
if [ -n "$TRACKED" ]; then
  printf 'REFUSED: OUT %s holds git-tracked files (for example %s). Use a fresh OUT; nothing was written.\n' \
    "$OUT" "$(printf '%s' "$TRACKED" | head -1)"
  exit 2
fi
mkdir -p "$OUT"
BOXLOG="$OUT/box.log"
START=$(date +%s)
TARBALL_DONE=0

say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$BOXLOG"; }
jget() { "$PY" -B -c 'import json,sys; v=json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."): v=v[k]
print(v)' "$1" "$2"; }

pack() {
  [ "$TARBALL_DONE" = 1 ] && return 0
  TARBALL_DONE=1
  ( cd "$OUT" && rm -f swarm-screen-out.tgz && \
    tar czf swarm-screen-out.tgz $(ls | grep -v -e '^swarm-screen-out.tgz$' -e '^ckpt' || true) ) \
    && say "packed $OUT/swarm-screen-out.tgz sha256 $(sha256sum "$OUT/swarm-screen-out.tgz" | cut -d' ' -f1) ($(stat -c %s "$OUT/swarm-screen-out.tgz") bytes)"
}
finish() { rc=$?; say "EXIT rc=$rc after $(( $(date +%s) - START )) s"; pack || true; exit $rc; }
trap finish EXIT

# step NAME CMD...: log start/end with UTC timestamps and seconds, tee the output to NAME.log, cut at MAXH.
step() {
  local name=$1; shift
  local left
  left=$(awk -v m="$MAXH" -v s="$START" -v n="$(date +%s)" 'BEGIN{printf "%d", m*3600-(n-s)}')
  if [ "$left" -le 0 ]; then say "STEP $name not started: MAXH $MAXH h reached"; exit 4; fi
  say "STEP $name start: $*"
  local began rc=0
  began=$(date +%s)
  set +e
  timeout "$left" "$@" 2>&1 | tee "$OUT/$name.log"
  rc=${PIPESTATUS[0]}
  set -e
  local took=$(( $(date +%s) - began ))
  printf '%s\t%s\t%s\n' "$name" "$took" "$rc" >> "$OUT/steps.tsv"
  say "STEP $name end rc=$rc seconds=$took"
  if [ "$rc" = 124 ]; then say "STEP $name cut by the MAXH limit"; exit 4; fi
  return "$rc"
}

# ---------------------------------------------------------------- 1. refuse unless everything is as sealed
say "swarm screen box: PART=$PART DRYRUN=$DRYRUN SIZE=$SIZE DEVICE=$DEVICE MAXH=$MAXH CAP=$CAP DPH=${DPH:-unset} OUT=$OUT"
case "$PART" in c0|s0|all) ;; *) say "REFUSED: PART must be c0, s0 or all (got $PART)"; exit 2;; esac
HEAD=$(git rev-parse HEAD)
if [ -z "$PIN" ] || [ "$HEAD" != "$PIN" ]; then say "REFUSED: HEAD $HEAD is not PIN '${PIN}'"; exit 2; fi
# A clean tree, in every mode (review round 3, item 2): HEAD == PIN only proves the commit, so an uncommitted edit
# to any file the run imports would otherwise run unseen. The dry run checks the COMMITTED manifest too.
DIRTY=$(git status --porcelain)
if [ -n "$DIRTY" ]; then
  say "REFUSED: the working tree is not clean (git status --porcelain):"; printf '%s\n' "$DIRTY" | tee -a "$BOXLOG"; exit 2
fi
if ! sha256sum -c scripts/premonition_swarm_manifest.txt > "$OUT/manifest-check.log" 2>&1; then
  say "REFUSED: a pinned file differs from the manifest (see manifest-check.log)"; cat "$OUT/manifest-check.log" | tee -a "$BOXLOG"; exit 2
fi
$PY -B scripts/premonition_swarm_screen.py manifest --check | tee -a "$BOXLOG" || { say "REFUSED: manifest does not cover the pinned file list"; exit 2; }
say "manifest OK ($(wc -l < scripts/premonition_swarm_manifest.txt) files), HEAD == PIN == $HEAD"
if [ "$DRYRUN" != 1 ]; then
  if [ -z "$DPH" ] || ! awk -v d="$DPH" 'BEGIN{exit !(d>0)}'; then say "REFUSED: DPH (the billed dollars per hour) must be set and positive"; exit 2; fi
  if awk -v m="$MAXH" -v d="$DPH" -v c="$CAP" 'BEGIN{exit !(m*d>c)}'; then
    say "REFUSED: MAXH x DPH = $(awk -v m="$MAXH" -v d="$DPH" 'BEGIN{print m*d}') USD is above the cap $CAP USD"; exit 2
  fi
  say "money guard OK: MAXH $MAXH x DPH $DPH = $(awk -v m="$MAXH" -v d="$DPH" 'BEGIN{print m*d}') USD <= cap $CAP USD"
  if ! $PY -B -c 'import sys, torch; sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    say "REFUSED: no CUDA device on this host (the full run is for the GPU box; use DRYRUN=1 on a CPU host)"; exit 2
  fi
fi
if [ "${CHECK_ONLY:-0}" = 1 ]; then say "CHECK_ONLY: every refusal check passed; stopping before any step"; exit 0; fi

# ---------------------------------------------------------------- 2. host record
{
  echo "date_utc: $(date -u +%FT%TZ)"; echo "hostname: $(hostname)"; echo "commit: $HEAD"; echo "uname: $(uname -a)"
  echo "--- torch"; $PY -B -c 'import torch,sys; print("python", sys.version.split()[0], "torch", torch.__version__, "cuda", torch.version.cuda, "cuda_available", torch.cuda.is_available())' 2>&1 || true
  echo "--- cpu"; (lscpu | head -20) 2>&1 || true
  echo "--- nvidia-smi -q"; (nvidia-smi -q) 2>&1 || echo "no nvidia-smi on this host"
} > "$OUT/host.txt"
say "host record -> host.txt ($(wc -l < "$OUT/host.txt") lines)"

if [ "$PART" != s0 ]; then
  # -------------------------------------------------------------- 3. data
  step data $SCREEN data --visits "$VISITS" --out "$OUT/data.json" $COMMON
  DATA_REL=$(jget "$OUT/data.json" data_rel); TOK=$(jget "$OUT/data.json" tokenizer_path)
  # -------------------------------------------------------------- 4. C0
  step c0 $SCREEN c0 --data-rel "$DATA_REL" --tokenizer "$TOK" --dph "${DPH:-0}" --ckpt-dir "$CKPT" --out "$OUT/c0.json" $COMMON $C0_ARGS
else
  for f in data.json c0.json; do [ -f "$OUT/$f" ] || { say "REFUSED: PART=s0 needs $OUT/$f from an earlier c0 part"; exit 2; }; done
  DATA_REL=$(jget "$OUT/data.json" data_rel); TOK=$(jget "$OUT/data.json" tokenizer_path)
fi
T=$(jget "$OUT/c0.json" T)
STOP=$(jget "$OUT/c0.json" stop_and_ask); MONEY=$(jget "$OUT/c0.json" money_stop)
say "C0: T = $T s; ratio S0m4/D1 = $(jget "$OUT/c0.json" ratio_s0m4_over_d1); stop_and_ask = $STOP; money_stop = $MONEY"
if [ "$STOP" = True ] || [ "$MONEY" = True ]; then
  {
    echo "STOP-AND-ASK: do not start S0 until the coordinator rules."
    echo "stop_and_ask (S0m4 / D1 weighted s/update > 2.5): $STOP"; echo "money_stop (projected S0 cost > 3.50 USD): $MONEY"
    "$PY" -B -c 'import json,sys; f=json.load(open(sys.argv[1]))["flags"]
for k in ("ratio","stop_ratio","T","eval_seconds_estimate","projected_s0_box_hours","dph","projected_s0_cost_usd","money_cap_usd"): print(f"{k}: {f[k]}")' "$OUT/c0.json"
  } > "$OUT/STOP-AND-ASK.txt"
  cat "$OUT/STOP-AND-ASK.txt" | tee -a "$BOXLOG"
  if [ "$PART" = c0 ] || [ -z "$STOP_OVERRIDE" ]; then say "STOP-AND-ASK: exiting 3 before any training"; exit 3; fi
  say "STOP_OVERRIDE given, continuing: $STOP_OVERRIDE"
fi
if [ "$PART" = c0 ]; then say "PART=c0: stopping after C0"; exit 0; fi

# ---------------------------------------------------------------- 5. trains (one at a time, interleaved)
train() { step "train-$1-s$2" $SCREEN train --arm "$1" --seed "$2" --seconds "$T" --data-rel "$DATA_REL" --tokenizer "$TOK" \
            --ckpt-dir "$CKPT" --out "$OUT/train-$1-s$2.json" $COMMON $TRAIN_ARGS; }
for seed in 0 1 2; do train D1 $seed; train S0 $seed; done
# ---------------------------------------------------------------- 6. evals
evalone() { step "eval-$1-s$2${3:+-$3}" $SCREEN eval --checkpoint "$CKPT/$1-s$2" ${3:+--lesion $3} \
              --out "$OUT/eval-$1-s$2${3:+-$3}.json" $COMMON; }
for seed in 0 1 2; do evalone D1 $seed; evalone S0 $seed; done
# ---------------------------------------------------------------- 7. readout
if [ "$DRYRUN" = 1 ]; then NOTE="DRY RUN: tiny preset, CPU, T=120 s; the numbers mean nothing"; else NOTE=""; fi
step marks-S0 $MARKS --card S0 --dir "$OUT" --out "$OUT/MARKS-S0.json" --note "$NOTE"
if [ "$DRYRUN" = 1 ]; then
  step marks-S0-minitems1 $MARKS --card S0 --dir "$OUT" --out "$OUT/MARKS-S0-minitems1.json" --min-items 1 --note "$NOTE (second pass: --min-items 1)"
  # the S1 tiny arm, 3 seeds, and the 3 lesions, so MARKS-S1 is proven computable (S1 itself is NOT booked)
  for seed in 0 1 2; do train S1 $seed; done
  for seed in 0 1 2; do evalone S1 $seed; for lesion in board notes cards; do evalone S1 $seed $lesion; done; done
  step marks-S1 $MARKS --card S1 --dir "$OUT" --out "$OUT/MARKS-S1.json" --note "$NOTE"
  step marks-S1-minitems1 $MARKS --card S1 --dir "$OUT" --out "$OUT/MARKS-S1-minitems1.json" --min-items 1 --note "$NOTE (second pass: --min-items 1)"
  say "DRYRUN: removing the checkpoints $CKPT (the dry run keeps JSON and logs only)"
  rm -rf "$ROOT/$CKPT"
fi
# ---------------------------------------------------------------- 8. pack for copy-back
say "S0 verdict: $(grep -h '^VERDICT' "$OUT/MARKS-S0.md" || echo 'no MARKS-S0.md')"
pack
say "DONE. Copy $OUT/swarm-screen-out.tgz back, check its sha256 above, then the rental agent may destroy the box."
