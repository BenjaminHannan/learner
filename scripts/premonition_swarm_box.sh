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
#   DPH      the billed dollars per hour (required off DRYRUN; a positive decimal such as 0.46).
#   CAP      dollars, the TOTAL approved for this box across every invocation (default 4.20, rulings Q28 and Oct 20).
#   MAXH     optional extra hour limit for this invocation (a positive decimal). The money deadline always applies.
#   BOX_START  epoch seconds when the box's billing began (setup and CHECK_ONLY passes included). REQUIRED off DRYRUN
#            until the ledger exists (round 3, eighth pass, item 3: no default, so billed time before the first run
#            is never left out). The running total is (now - BOX_START) x DPH, idle time between invocations
#            included. It is persisted in the box ledger artifacts/<run>/money-ledger.json (one level above OUT, one
#            per box, coordinator ruling Oct 20), written by the first invocation that passes the money checks, so a
#            fresh OUT never resets the money. The ledger also records every C0 stop.
#   PART     c0 | s0 | all (default all). c0 stops after C0. s0 starts at the trains and needs data.json, c0.json
#            and host-c0.txt in OUT (from an earlier c0 part in this OUT, or copied from FROM).
#   FROM     with PART=s0 only, on a fresh OUT: an earlier OUT whose data.json, c0.json and host-c0.txt are copied
#            (read-only sources; their sha256 is logged). This is the rerun route after a VOID: a fresh OUT, the same T.
#   DRYRUN   1 = the CPU dry run: tiny preset and visits, cpu, T = 120 s (one CPU step is ~2% of 30 s, the whole
#            +-2% seconds band of M5, so 30 s voids on one step; see BOX-SPEC), no money ledger, and the S1 tiny arm +
#            lesions are run so that MARKS-S1 is proven computable too. Like the real run it needs a clean tree and
#            the COMMITTED manifest. Its numbers mean nothing.
#   CKPT     checkpoint folder, relative to the repo (default <OUT>/ckpt); must be git-ignored and empty at the start.
#   CHECK_ONLY  1 = run every refusal check, then exit 0 before any step: PIN, clean tree, OUT/CKPT placement, fresh
#            OUT, empty CKPT, manifest, money, CUDA, and for PART=s0 the c0 prerequisites, host tie and C0 gate.
#   STOP_OVERRIDE  non-empty text (the coordinator's ruling) lets the trains start although C0 says stop_and_ask or
#            money_stop. Logged. It never overrides the box's money deadline or the total cap. Once any C0 on this box
#            has stopped (recorded in the ledger), every later invocation needs it: re-measuring C0 in the same or a
#            fresh OUT until it passes is refused (round 3, eighth pass, item 1).
#   OUT, PY, WORKERS, C0_EXTRA, DRY_MAXTOK  output folder, python, data workers, extra c0 args (never --t-override off
#            DRYRUN: an unregistered T is refused), the dry run's per-batch token cap.
# Exit codes: 2 refused (nothing paid ran in this invocation), 3 stop-and-ask (C0's flags, or the runner's C0 stop:
#             D1 or S0m4 cannot run), 4 the money deadline or MAXH was reached, 5 a step failed after it started (a
#             runner refusal mid-run included) or the archive could not be packed. On 3/4/5, copy OUT's JSON and logs
#             back directly (no archive is packed).
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/.." && pwd -P)   # physical, like `realpath` on OUT below (a symlinked /workspace must still match)
cd "$ROOT"
PIN=${PIN:-}
DPH=${DPH:-}
MAXH=${MAXH:-}
CAP=${CAP:-4.20}
PART=${PART:-all}
DRYRUN=${DRYRUN:-0}
FROM=${FROM:-}
PY=${PY:-python}
STOP_OVERRIDE=${STOP_OVERRIDE:-}
C0_EXTRA=${C0_EXTRA:-}
RUN=claude-swarm-screen-20261018
BID_HOURS=8.5                      # FUNDING-BID: C0 1.0 h + S0 7.5 h; above CAP at this DPH -> a revised bid is needed
LEDGER=$ROOT/artifacts/$RUN/money-ledger.json
refuse() { printf 'REFUSED: %s\n' "$*"; exit 2; }
is_decimal() { [[ "$1" =~ ^[0-9]+([.][0-9]+)?$ ]] && awk -v x="$1" 'BEGIN{exit !(x>0)}'; }
if [ "$DRYRUN" = 1 ]; then
  SIZE=tiny; DEVICE=cpu; VISITS=tiny; DRY_MAXTOK=${DRY_MAXTOK:-3000}
  OUT=${OUT:-$ROOT/artifacts/$RUN/dryrun-$(git -C "$ROOT" rev-parse --short=9 HEAD)}   # fresh per commit
  C0_ARGS="--rounds 3 --warmup 2 --timed 4 --chunk 2 --t-override 120 --max-tokens $DRY_MAXTOK $C0_EXTRA"
  TRAIN_ARGS="--max-tokens $DRY_MAXTOK"
else
  SIZE=full; DEVICE=cuda; VISITS=large
  OUT=${OUT:-$ROOT/artifacts/$RUN/out}                            # git-ignored: outputs never dirty the tree
  case " $C0_EXTRA " in *t-override*) refuse "C0_EXTRA may not set --t-override off DRYRUN: T is the registered formula (RUNCARD-S0 §1)";; esac
  C0_ARGS="--rounds 3 --warmup 10 --timed 40 --chunk 5 $C0_EXTRA"
  TRAIN_ARGS=""
fi
case "$PART" in c0|s0|all) ;; *) refuse "PART must be c0, s0 or all (got $PART)";; esac
[ -z "$FROM" ] || [ "$PART" = s0 ] || refuse "FROM is only for PART=s0 (data and C0 would overwrite its files); got PART=$PART"
is_decimal "$CAP" || refuse "CAP must be a positive decimal number of dollars (got '$CAP')"
[ -z "$MAXH" ] || is_decimal "$MAXH" || refuse "MAXH must be a positive decimal number of hours (got '$MAXH')"
WORKERS=${WORKERS:-0}
SCREEN="$PY -B scripts/premonition_swarm_screen.py"
MARKS="$PY -B scripts/premonition_swarm_marks.py"
COMMON="--device $DEVICE --size $SIZE --workers $WORKERS"
# OUT must be inside the repo and git-ignored, and hold no git-tracked file; CKPT (default <OUT>/ckpt) must be
# relative and git-ignored. All of this runs before anything is written.
OUT=$(realpath -m "$OUT")
case "$OUT/" in
  "$ROOT"/*) ;;
  *) refuse "OUT $OUT is outside the repository $ROOT; use a folder under artifacts/ (artifacts/ must be a real folder in the repository, not a symlink). Nothing was written.";;
esac
git -C "$ROOT" check-ignore -q --no-index "$OUT/box.log" \
  || refuse "OUT $OUT is not git-ignored (writing there would dirty the tree); use a folder under artifacts/."
CKPT=${CKPT:-${OUT#"$ROOT"/}/ckpt}
case "$CKPT" in /*|../*|*/../*) refuse "CKPT $CKPT must be a path relative to the repository, inside it.";; esac
git -C "$ROOT" check-ignore -q --no-index "$ROOT/$CKPT/x" || refuse "CKPT $CKPT is not git-ignored; use a folder under artifacts/."
TRACKED=$(git -C "$ROOT" ls-files -- "$OUT")                     # no pipe: a long list must not SIGPIPE (exit 141)
[ -z "$TRACKED" ] || refuse "OUT $OUT holds git-tracked files (for example ${TRACKED%%$'\n'*}). Use a fresh OUT; nothing was written."
# One run per OUT (round 3, sixth pass, item 8): an OUT that already holds results is never written again.
shopt -s nullglob
DONE_FILES=("$OUT"/train-*.json "$OUT"/eval-*.json "$OUT"/MARKS-* "$OUT"/swarm-screen-out.tg[z])   # [z]: a plain name is not a glob
# A part that runs data and C0 also needs an OUT without an earlier C0 (eighth pass, item 1): a stopping c0.json
# is never overwritten by a new measurement. PART=s0 reads them (and re-applies the C0 gate).
if [ "$PART" != s0 ]; then DONE_FILES+=("$OUT"/data.jso[n] "$OUT"/c0.jso[n] "$OUT"/STOP-AND-ASK.tx[t] "$OUT"/host-c0.tx[t]); fi
shopt -u nullglob
[ "${#DONE_FILES[@]}" = 0 ] || refuse "OUT $OUT already holds results (for example $(basename "${DONE_FILES[0]}")); a rerun uses a fresh OUT (PART=s0 FROM=<old OUT> keeps the same T, and its C0 gate)."
mkdir -p "$OUT"
BOXLOG="$OUT/box.log"
START=$(date +%s)

say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$BOXLOG"; }
jget() { "$PY" -B -c 'import json,sys; v=json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."): v=v[k]
print(v)' "$1" "$2"; }
gpu_id() { (nvidia-smi --query-gpu=name,uuid --format=csv,noheader 2>/dev/null || true) | head -1 | sed 's/^ *//'; }

# The copy-back archive is written ONLY at a successful run end (step 8), never on a refusal or a failure, and an
# archive that already exists is never changed. Checkpoints (the actual CKPT) and C0 probes are left out.
pack() {
  if [ -e "$OUT/swarm-screen-out.tgz" ]; then
    say "NOT packing: $OUT/swarm-screen-out.tgz already exists and is never changed"; return 1
  fi
  local skip=() rel
  case "$ROOT/$CKPT/" in "$OUT"/*) rel=${CKPT#"${OUT#"$ROOT"/}"/}; skip+=(--exclude="./${rel%%/*}");; esac
  # tar writes beside OUT, then the archive moves in: tar fails ("file changed as we read it") if it writes into the
  # folder it is reading.
  local tmp
  tmp=$(mktemp -p "$(dirname "$OUT")" .swarm-screen-out.XXXXXX)
  ( cd "$OUT" && tar czf "$tmp" --exclude=./c0-probe "${skip[@]}" . ) || { rm -f "$tmp"; say "pack FAILED"; return 1; }
  mv -n "$tmp" "$OUT/swarm-screen-out.tgz"
  say "packed $OUT/swarm-screen-out.tgz sha256 $(sha256sum "$OUT/swarm-screen-out.tgz" | cut -d' ' -f1) ($(stat -c %s "$OUT/swarm-screen-out.tgz") bytes)"
}
finish() { rc=$?; say "EXIT rc=$rc after $(( $(date +%s) - START )) s"; exit $rc; }
trap finish EXIT

# ---------------------------------------------------------------- 1. refuse unless everything is as sealed
say "swarm screen box: PART=$PART DRYRUN=$DRYRUN SIZE=$SIZE DEVICE=$DEVICE CAP=$CAP DPH=${DPH:-unset} MAXH=${MAXH:-none} OUT=$OUT"
HEAD=$(git rev-parse HEAD)
if [ -z "$PIN" ] || [ "$HEAD" != "$PIN" ]; then say "REFUSED: HEAD $HEAD is not PIN '${PIN}'"; exit 2; fi
# A clean tree, in every mode: HEAD == PIN only proves the commit, so an uncommitted edit to any file the run imports
# would otherwise run unseen. The dry run checks the COMMITTED manifest too.
DIRTY=$(git status --porcelain)
if [ -n "$DIRTY" ]; then
  say "REFUSED: the working tree is not clean (git status --porcelain):"; printf '%s\n' "$DIRTY" | tee -a "$BOXLOG"; exit 2
fi
if ! sha256sum -c scripts/premonition_swarm_manifest.txt > "$OUT/manifest-check.log" 2>&1; then
  say "REFUSED: a pinned file differs from the manifest (see manifest-check.log)"; cat "$OUT/manifest-check.log" | tee -a "$BOXLOG"; exit 2
fi
$PY -B scripts/premonition_swarm_screen.py manifest --check | tee -a "$BOXLOG" || { say "REFUSED: manifest does not cover the pinned file list"; exit 2; }
say "manifest OK ($(wc -l < scripts/premonition_swarm_manifest.txt) files), HEAD == PIN == $HEAD"

# Money (round 3, sixth pass, items 2, 3, 5): CAP is the TOTAL for the box, across every invocation and OUT.
NOW=$(date +%s)
if [ "$DRYRUN" = 1 ]; then
  DEADLINE=$(( START + 8 * 3600 ))
  if [ -n "$MAXH" ]; then DEADLINE=$(( START + $(awk -v m="$MAXH" 'BEGIN{printf "%d", m*3600}') )); fi
  say "DRYRUN: no money ledger; this invocation stops at $(date -u -d "@$DEADLINE" +%FT%TZ)"
else
  is_decimal "$DPH" || { say "REFUSED: DPH (the billed dollars per hour) must be a positive decimal (got '$DPH')"; exit 2; }
  if awk -v h="$BID_HOURS" -v d="$DPH" -v c="$CAP" 'BEGIN{exit !(h*d>c)}'; then
    say "REFUSED: the bid's $BID_HOURS h x DPH $DPH = $(awk -v h="$BID_HOURS" -v d="$DPH" 'BEGIN{printf "%.2f", h*d}') USD exceeds the cap $CAP USD. A revised bid with the new total is needed (coordinator ruling Oct 20); nothing ran."; exit 2
  fi
  if [ -f "$LEDGER" ]; then
    BOX_START=$(jget "$LEDGER" box_start)
    [ "$(jget "$LEDGER" dph)" = "$DPH" ] && [ "$(jget "$LEDGER" cap)" = "$CAP" ] \
      || { say "REFUSED: DPH/CAP differ from the box ledger $LEDGER (dph $(jget "$LEDGER" dph), cap $(jget "$LEDGER" cap))"; exit 2; }
  else
    [[ "$BOX_START" =~ ^[0-9]+$ ]] || { say "REFUSED: BOX_START (epoch seconds when this box's billing began, setup included) is required before the first run (got '${BOX_START:-}')"; exit 2; }
    [ "$BOX_START" -le $(( NOW + 60 )) ] || { say "REFUSED: BOX_START $BOX_START is in the future"; exit 2; }
  fi
  SPENT=$(awk -v n="$NOW" -v s="$BOX_START" -v d="$DPH" 'BEGIN{printf "%.4f", (n-s)/3600*d}')
  DEADLINE=$(awk -v s="$BOX_START" -v c="$CAP" -v d="$DPH" 'BEGIN{printf "%d", s + c/d*3600}')
  if [ -n "$MAXH" ]; then
    LIMIT=$(( START + $(awk -v m="$MAXH" 'BEGIN{printf "%d", m*3600}') ))
    if [ "$LIMIT" -lt "$DEADLINE" ]; then DEADLINE=$LIMIT; fi
  fi
  if [ "$DEADLINE" -le "$NOW" ]; then say "REFUSED: the box has spent $SPENT USD of the $CAP USD total; no money is left"; exit 2; fi
  say "money: box billing since $(date -u -d "@$BOX_START" +%FT%TZ), spent $SPENT USD of $CAP USD; hard stop at $(date -u -d "@$DEADLINE" +%FT%TZ)"
  if [ ! -f "$LEDGER" ]; then                # from here on the box's billing start is fixed, for every OUT
    mkdir -p "$(dirname "$LEDGER")"
    printf '{"box_start": %s, "dph": "%s", "cap": "%s", "first_out": "%s", "c0_stops": []}\n' "$BOX_START" "$DPH" "$CAP" "$OUT" > "$LEDGER"
    say "money ledger started: $LEDGER (box_start $BOX_START)"
  fi
  STOPS=$("$PY" -B -c 'import json,sys; s=json.load(open(sys.argv[1])).get("c0_stops") or []
print("; ".join(str(x.get("reason")) + " in " + str(x.get("out")) for x in s))' "$LEDGER")
  if [ -n "$STOPS" ]; then
    [ -n "$STOP_OVERRIDE" ] || { say "REFUSED: an earlier C0 on this box stopped ($STOPS). Every further run needs the coordinator's STOP_OVERRIDE; a new C0 measurement is not a way around it."; exit 2; }
    say "earlier C0 stops on this box: $STOPS; STOP_OVERRIDE given: $STOP_OVERRIDE"
  fi
  if ! $PY -B -c 'import sys, torch; sys.exit(0 if torch.cuda.is_available() else 1)' 2>/dev/null; then
    say "REFUSED: no CUDA device on this host (the full run is for the GPU box; use DRYRUN=1 on a CPU host)"; exit 2
  fi
fi
# ledger_stop REASON: record a C0 stop in the box ledger (off DRYRUN), so no later invocation can re-measure past it.
ledger_stop() {
  [ "$DRYRUN" != 1 ] || return 0
  "$PY" -B -c 'import json,sys,time; p=sys.argv[1]; d=json.load(open(p))
d.setdefault("c0_stops", []).append({"reason": sys.argv[2], "out": sys.argv[3], "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
json.dump(d, open(p, "w"))' "$LEDGER" "$1" "$OUT"
  say "C0 stop recorded in the box ledger: $1"
}
# A rerun must refuse BEFORE any paid work: save_checkpoint never overwrites.
if [ -d "$ROOT/$CKPT" ] && [ -n "$(ls -A "$ROOT/$CKPT" 2>/dev/null)" ]; then
  say "REFUSED: the checkpoint folder $CKPT already holds checkpoints (a rerun?). Use a fresh OUT (or CKPT); nothing ran."
  exit 2
fi
# PART=s0: its C0 inputs (an earlier c0 part in this OUT, or FROM), and the same GPU as C0 (T is "on this box").
if [ "$PART" = s0 ] && [ -n "$FROM" ]; then
  FROM=$(realpath -m "$FROM")
  for f in data.json c0.json host-c0.txt; do
    [ -f "$FROM/$f" ] || { say "REFUSED: FROM $FROM has no $f"; exit 2; }
    if [ -e "$OUT/$f" ]; then say "REFUSED: OUT already has $f; FROM is for a fresh OUT"; exit 2; fi
  done
fi
if [ "$PART" = s0 ]; then
  for f in data.json c0.json host-c0.txt; do
    [ -f "$OUT/$f" ] || [ -f "${FROM:-/nonexistent}/$f" ] || { say "REFUSED: PART=s0 needs $f in OUT (or FROM)"; exit 2; }
  done
  C0_SRC=$OUT; [ -f "$OUT/c0.json" ] || C0_SRC=$FROM
  WANT=$(sed -n 's/^gpu: //p' "$C0_SRC/host-c0.txt"); HAVE=$(gpu_id); HAVE=${HAVE:-none}
  [ "$WANT" = "$HAVE" ] || { say "REFUSED: this GPU ($HAVE) is not the one C0 measured T on ($WANT)"; exit 2; }
fi
# The C0 gate: the stop-and-ask flags, the registered T, and whether the money left covers the projected S0.
c0_gate() {
  local c0=$1
  LEFT_SHORT=0
  T=$(jget "$c0" T)
  STOP=$(jget "$c0" stop_and_ask); MONEY=$(jget "$c0" money_stop)
  if [ "$DRYRUN" != 1 ]; then
    [ "$(jget "$c0" t_override)" = None ] && [ "$(jget "$c0" T)" = "$(jget "$c0" T_formula)" ] \
      || { say "REFUSED: c0.json's T $(jget "$c0" T) is not the registered formula's ($(jget "$c0" T_formula)); an unregistered T is never trained"; exit 2; }
    NEED=$(jget "$c0" flags.projected_s0_box_hours)
    LEFT=$(awk -v d="$DEADLINE" -v n="$(date +%s)" 'BEGIN{printf "%.3f", (d-n)/3600}')
    if awk -v need="$NEED" -v left="$LEFT" 'BEGIN{exit !(need>left)}'; then
      say "money: projected S0 $NEED box-hours exceed the $LEFT h left before the hard stop; a revised bid is needed"
      MONEY=True; LEFT_SHORT=1                 # never overridable: the total cap is not raised quietly
    fi
  fi
  say "C0: T = $T s; ratio S0m4/D1 = $(jget "$c0" ratio_s0m4_over_d1); stop_and_ask = $STOP; money_stop = $MONEY"
  if [ "$STOP" = True ] || [ "$MONEY" = True ]; then
    {
      echo "STOP-AND-ASK: do not start S0 until the coordinator rules."
      echo "stop_and_ask (S0m4 / D1 weighted s/update > 2.5): $STOP"; echo "money_stop (S0 cap, or the box's money left): $MONEY"
      "$PY" -B -c 'import json,sys; f=json.load(open(sys.argv[1]))["flags"]
for k in ("ratio","stop_ratio","T","eval_seconds_estimate","train_overhead_seconds","projected_s0_box_hours","dph","projected_s0_cost_usd","money_cap_usd"): print(f"{k}: {f[k]}")' "$c0"
    } > "$OUT/STOP-AND-ASK.txt"
    cat "$OUT/STOP-AND-ASK.txt" | tee -a "$BOXLOG"
    if [ "$PART" = c0 ] || [ -z "$STOP_OVERRIDE" ] || [ "${LEFT_SHORT:-0}" = 1 ]; then
      ledger_stop "stop_and_ask=$STOP money_stop=$MONEY"
      say "STOP-AND-ASK: exiting 3 before any training"; exit 3
    fi
    say "STOP_OVERRIDE given, continuing: $STOP_OVERRIDE"
  fi
}
if [ "$PART" = s0 ] && [ "${CHECK_ONLY:-0}" = 1 ]; then c0_gate "$C0_SRC/c0.json"; fi
say "pre-flight OK: OUT $OUT and CKPT $CKPT are git-ignored, OUT is fresh and holds no tracked file, CKPT is empty"
if [ "${CHECK_ONLY:-0}" = 1 ]; then say "CHECK_ONLY: every refusal check passed; stopping before any step"; exit 0; fi
if [ -n "$FROM" ]; then
  for f in data.json c0.json host-c0.txt; do
    cp "$FROM/$f" "$OUT/$f"; say "FROM: copied $f ($(sha256sum "$OUT/$f" | cut -d' ' -f1)) from $FROM"
  done
fi

# step NAME CMD...: log start/end with UTC timestamps and seconds, tee the output to NAME.log, cut at the deadline.
step() {
  local name=$1; shift
  local left
  left=$(( DEADLINE - $(date +%s) ))
  if [ "$left" -le 0 ]; then say "STEP $name not started: the money deadline or MAXH was reached"; exit 4; fi
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
  if [ "$rc" = 124 ]; then say "STEP $name cut by the money deadline or MAXH"; exit 4; fi
  if [ "$name" = c0 ] && [ "$rc" = 3 ]; then         # the runner's C0 stop: D1 or S0m4 cannot run, so no T (item 9)
    { echo "STOP-AND-ASK: C0 could not set T (the runner's C0 stop; see c0.log)."; tail -5 "$OUT/c0.log"; } > "$OUT/STOP-AND-ASK.txt"
    cat "$OUT/STOP-AND-ASK.txt" | tee -a "$BOXLOG"
    ledger_stop "c0 could not set T"
    say "STOP-AND-ASK: exiting 3 before any training"; exit 3
  fi
  if [ "$rc" != 0 ]; then say "STEP $name FAILED (rc $rc): exiting 5"; exit 5; fi
}
host_record() {
  {
    echo "date_utc: $(date -u +%FT%TZ)"; echo "hostname: $(hostname)"; echo "commit: $HEAD"; echo "uname: $(uname -a)"
    local id; id=$(gpu_id); echo "gpu: ${id:-none}"
    echo "--- torch"; $PY -B -c 'import torch,sys; print("python", sys.version.split()[0], "torch", torch.__version__, "cuda", torch.version.cuda, "cuda_available", torch.cuda.is_available())' 2>&1 || true
    echo "--- cpu"; (lscpu | head -20) 2>&1 || true
    echo "--- nvidia-smi -q"; (nvidia-smi -q) 2>&1 || echo "no nvidia-smi on this host"
  } > "$OUT/$1"
  say "host record -> $1 ($(wc -l < "$OUT/$1") lines)"
}

if [ "$PART" != s0 ]; then
  host_record host-c0.txt
  # -------------------------------------------------------------- 3. data
  step data $SCREEN data --visits "$VISITS" --out "$OUT/data.json" $COMMON
  DATA_REL=$(jget "$OUT/data.json" data_rel); TOK=$(jget "$OUT/data.json" tokenizer_path)
  # -------------------------------------------------------------- 4. C0
  rm -rf "$OUT/c0-probe"            # C0's probe checkpoints live apart from CKPT, so a cut C0 never blocks PART=s0
  step c0 $SCREEN c0 --data-rel "$DATA_REL" --tokenizer "$TOK" --dph "${DPH:-0}" --ckpt-dir "${OUT#"$ROOT"/}/c0-probe" --out "$OUT/c0.json" $COMMON $C0_ARGS
else
  DATA_REL=$(jget "$OUT/data.json" data_rel); TOK=$(jget "$OUT/data.json" tokenizer_path)
fi
if [ "$PART" != c0 ]; then host_record host-s0.txt; fi
c0_gate "$OUT/c0.json"
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
if [ "$DRYRUN" = 1 ]; then NOTE="DRY RUN: tiny preset, CPU, T=120 s; the numbers mean nothing"; NOTE_ARGS=(--dry-run); else NOTE=""; NOTE_ARGS=(); fi
step marks-S0 $MARKS --card S0 --dir "$OUT" --out "$OUT/MARKS-S0.json" --note "$NOTE" "${NOTE_ARGS[@]}"
if [ "$DRYRUN" = 1 ]; then
  step marks-S0-minitems1 $MARKS --card S0 --dir "$OUT" --out "$OUT/MARKS-S0-minitems1.json" --min-items 1 --note "$NOTE (second pass: --min-items 1)" "${NOTE_ARGS[@]}"
  # the S1 tiny arm, 3 seeds, and the 3 lesions, so MARKS-S1 is proven computable (S1 itself is NOT booked)
  for seed in 0 1 2; do train S1 $seed; done
  for seed in 0 1 2; do evalone S1 $seed; for lesion in board notes cards; do evalone S1 $seed $lesion; done; done
  step marks-S1 $MARKS --card S1 --dir "$OUT" --out "$OUT/MARKS-S1.json" --note "$NOTE" "${NOTE_ARGS[@]}"
  step marks-S1-minitems1 $MARKS --card S1 --dir "$OUT" --out "$OUT/MARKS-S1-minitems1.json" --min-items 1 --note "$NOTE (second pass: --min-items 1)" "${NOTE_ARGS[@]}"
  say "DRYRUN: removing the checkpoints $CKPT (the dry run keeps JSON and logs only)"
  rm -rf "$ROOT/$CKPT"
fi
# ---------------------------------------------------------------- 8. pack for copy-back
say "S0 verdict: $(grep -h '^VERDICT' "$OUT/MARKS-S0.md" || echo 'no MARKS-S0.md')"
pack || { say "the archive was not packed: exiting 5"; exit 5; }
say "DONE. Copy $OUT/swarm-screen-out.tgz back, check its sha256 above, then the rental agent may destroy the box."
