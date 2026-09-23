#!/bin/bash
# Full-corpus reading-list processing for the talker (design 24, build task 1).
#
#   bash run_data_full.sh [WORKERS]        # WORKERS defaults to 4
#
# Environment overrides:
#   WORKERS=8              worker processes for the encode stage
#   SEED=24                the one seed that fixes name codes and the document shuffle
#   NAMES_BYTES            raw bytes per source used to build the lexicon   (default 200 MiB)
#   TOKENIZER_BYTES        raw bytes per source used to train the BPE       (default 200 MiB)
#   SHARD_TOKENS           tokens per shard                                 (default 134217728)
#   S0_TOKENS              tokens in the smoke-test shard                   (default 100000000)
#   FORCE=1                redo the lexicon and the tokenizer instead of reusing them
#
# RESUMABLE. Kill it at any point and run it again:
#   * the download skips any file already present at its exact byte size;
#   * the lexicon and the tokenizer are reused if they exist (FORCE=1 to redo them);
#   * the encode stage writes one part file per input unit and skips every unit whose
#     part is already finished, so a kill only costs the unit that was in flight;
#   * merge / stats / s0 are pure functions of the parts and are simply re-run.
#
# It needs no network once data/raw is complete, and installs nothing: it uses the
# project venv beside this script.

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PY="$HERE/venv/bin/python"
SCRIPT="$REPO/scripts/fable_talker24_data.py"

WORKERS="${1:-${WORKERS:-4}}"
SEED="${SEED:-24}"
NAMES_BYTES="${NAMES_BYTES:-209715200}"
TOKENIZER_BYTES="${TOKENIZER_BYTES:-209715200}"
SHARD_TOKENS="${SHARD_TOKENS:-134217728}"
S0_TOKENS="${S0_TOKENS:-100000000}"
FORCE="${FORCE:-0}"

RAW="$HERE/data/raw"
OUT="$HERE/shards"
LOGS="$HERE/reports"
mkdir -p "$LOGS" "$OUT"
printf '*\n' > "$OUT/.gitignore" 2>/dev/null || true

[ -x "$PY" ] || { echo "no venv at $PY -- see INTERFACE-data.md section 0"; exit 2; }
[ -f "$SCRIPT" ] || { echo "no producer at $SCRIPT"; exit 2; }

COMMON=(--raw "$RAW" --out "$OUT" --seed "$SEED"
        --names-bytes "$NAMES_BYTES" --tokenizer-bytes "$TOKENIZER_BYTES"
        --shard-tokens "$SHARD_TOKENS" --s0-tokens "$S0_TOKENS")

stamp () { date -u +%Y-%m-%dT%H:%M:%SZ; }
run () {  # run <stage-name> <args...>
  local name="$1"; shift
  echo "=== $(stamp)  $name"
  local t0=$SECONDS
  "$PY" -B "$SCRIPT" "$@" 2>&1 | tee -a "$LOGS/run_data_full.log"
  local rc=${PIPESTATUS[0]}
  echo "=== $(stamp)  $name finished rc=$rc in $((SECONDS - t0))s"
  [ "$rc" = 0 ] || exit "$rc"
}

echo "run_data_full: workers=$WORKERS seed=$SEED  raw=$RAW  out=$OUT" \
  | tee -a "$LOGS/run_data_full.log"

# 0. data ------------------------------------------------------------------------------
bash "$HERE/data/download.sh" 6 2>&1 | tee -a "$LOGS/run_data_full.log"
if [ ! -f "$HERE/data/MANIFEST-raw.json" ] || [ "$FORCE" = 1 ]; then
  run manifest-raw manifest-raw "${COMMON[@]}"
else
  echo "=== $(stamp)  manifest-raw: reusing $HERE/data/MANIFEST-raw.json"
fi

# 1. a sample build must never be mistaken for a full one ------------------------------
if [ -f "$OUT/tokenizer_meta.json" ] &&
   grep -q '"profile": "sample"' "$OUT/tokenizer_meta.json" 2>/dev/null; then
  echo "=== $(stamp)  found a SAMPLE build in $OUT -- moving it aside and starting clean"
  mv "$OUT" "$OUT-sample-$(date -u +%Y%m%dT%H%M%SZ)"
  mkdir -p "$OUT"; printf '*\n' > "$OUT/.gitignore"
fi

# 2. lexicon (pass A) ------------------------------------------------------------------
if [ ! -f "$OUT/lexicon.json" ] || [ "$FORCE" = 1 ]; then
  run names names "${COMMON[@]}"
else
  echo "=== $(stamp)  names: reusing $OUT/lexicon.json"
fi

# 3. tokenizer -------------------------------------------------------------------------
if [ ! -f "$OUT/tokenizer.json" ] || [ "$FORCE" = 1 ]; then
  run tokenizer tokenizer "${COMMON[@]}"
else
  echo "=== $(stamp)  tokenizer: reusing $OUT/tokenizer.json"
fi

# 4. encode (pass B) -- the long one; resumable per input unit --------------------------
run encode encode "${COMMON[@]}" --workers "$WORKERS"

# 5. shards, stats, smoke-test shard ---------------------------------------------------
run merge merge "${COMMON[@]}"
run stats stats "${COMMON[@]}"
run s0    s0    "${COMMON[@]}"

echo "=== $(stamp)  DONE"
echo "shards:   $OUT"
echo "manifest: $OUT/manifest.json"
echo "stats:    $OUT/stats.md"
echo "s0 shard: $OUT/s0/s0-00000.tokens.u16"
