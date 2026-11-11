#!/usr/bin/env bash
# TC-1 full run: pretrain per seed, pick-only pretests, 7 arms x 3 seeds, analysis. Resumable: finished outputs are skipped.
# Usage: [PRIOR=touching] bash tc1/run_all.sh OUT_DIR CKPT_DIR   (run from /home/user/learner/taste)
# PRIOR=touching is TC-1b (structured day-0 programs); default clutter is TC-1.
set -u
OUT=${1:?out dir}; CK=${2:?ckpt dir}; PAR=${PAR:-4}; PRIOR=${PRIOR:-clutter}
SEEDS=${SEEDS:-"1 2 3"}; DAYS=${DAYS:-6}; DISTINCT=${DISTINCT:+--distinct}  # TC-1c: DISTINCT=1   # extension: SEEDS="1 2 3 4 5 6" DAYS=12
mkdir -p "$OUT" "$CK" "$OUT/logs"
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$OUT/progress.log"; }

phase=${PHASE:-all}
if [ "$phase" = all ] || [ "$phase" = pre ]; then
  for s in $SEEDS; do
    if ls "$CK"/maker-s${s}-* >/dev/null 2>&1; then log "pretrain s$s: checkpoint exists, skip"; continue; fi
    log "pretrain s$s start"
    python3 -m tc1.run --arm N --seed "$s" --out "$OUT" --ckpt-dir "$CK" --pretrain-only --prior "$PRIOR" --threads 4 > "$OUT/logs/pretrain-s$s.log" 2>&1
    log "pretrain s$s exit $?"
  done
  for s in $SEEDS; do
    if ls "$OUT"/pretest*s${s}*.json >/dev/null 2>&1; then log "pretest s$s exists, skip"; continue; fi
    ( python3 -m tc1.pretest --seed "$s" --out "$OUT" --ckpt-dir "$CK" --prior "$PRIOR" --threads 1 > "$OUT/logs/pretest-s$s.log" 2>&1; log "pretest s$s exit $?" ) &
  done
  wait
fi
if [ "$phase" = all ] || [ "$phase" = arms ]; then
  jobs=()
  for s in $SEEDS; do for a in C R O B H R07 N; do
    [ -f "$OUT/$a-s$s.json" ] && { log "arm $a s$s exists, skip"; continue; }
    jobs+=("$a $s")
  done; done
  log "arms to run: ${#jobs[@]} at $PAR in parallel"
  printf '%s\n' "${jobs[@]}" | PRIOR="$PRIOR" DAYS="$DAYS" DISTINCT="$DISTINCT" xargs -P "$PAR" -L 1 bash -c '
    a=$0; s=$1
    echo "$(date -u +%FT%TZ) arm $a s$s start" >> "'"$OUT"'/progress.log"
    python3 -m tc1.run --arm "$a" --seed "$s" --out "'"$OUT"'" --ckpt-dir "'"$CK"'" --prior "$PRIOR" --days "$DAYS" $DISTINCT --threads 1 > "'"$OUT"'/logs/$a-s$s.log" 2>&1
    echo "$(date -u +%FT%TZ) arm $a s$s exit $?" >> "'"$OUT"'/progress.log"'
  python3 -m tc1.analyze "$OUT" > "$OUT/logs/analyze.log" 2>&1
  log "analyze exit $?"
fi
log "done phase=$phase"
