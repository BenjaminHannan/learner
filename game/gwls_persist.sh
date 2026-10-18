#!/bin/bash
# DRAFT pending coordinator confirmation (GW-LS). Copies the GW-LS outputs from the /tmp scratch folder to a permanent place (no git operation; the
# session lead commits): every iter-k.json and run.log of both seeds, every play-k-c.json.gz of both seeds, report.json / report.md, and the output of
# `python -m game.gwls_checks` (checks.txt, with its exit code on the last line; a failing check does not fail this script).
# Run it after each round (and once more when the run ends). Safe to repeat: copies only, never deletes, never touches the training folder.
#
# Every file is copied to DEST/<name>.tmp.<pid> first and moved into place only when it is whole (iter-k.json and the report JSON must parse with
# python json.load; play files must pass gzip -t), so a half-written source never replaces a good copy. play-k-c.json.gz is copied only if missing or
# different. Any validation or copy failure is reported (file named, on stderr) and makes the script exit non-zero at the end; the other files are
# still copied.
#
#   bash game/gwls_persist.sh [SRC_ROOT] [DEST]
#   defaults: SRC_ROOT = the scratch gwls folder, DEST = game/results/gwls/ of this repo
SCR=/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad
SRC=${1:-$SCR/gwls}
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST=${2:-$HERE/results/gwls}
REPO="$(dirname "$HERE")"
PY=${PY:-$SCR/venv/bin/python}
[ -x "$PY" ] || PY=python3
n=0
fail=0

# copy_one SRC DST KIND   (KIND: json | gz | raw)
copy_one() {
  local src=$1 dst=$2 kind=$3 tmp
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then return 0; fi          # already identical
  tmp="$dst.tmp.$$"
  if ! cp -p "$src" "$tmp"; then
    echo "ERROR: copy failed: $src -> $dst" >&2; rm -f "$tmp"; fail=1; return 1
  fi
  case $kind in
    json) "$PY" -c 'import json, sys; json.load(open(sys.argv[1]))' "$tmp" 2>/dev/null \
            || { echo "ERROR: not valid JSON (half-written or corrupt), not persisted: $src" >&2; rm -f "$tmp"; fail=1; return 1; } ;;
    gz)   gzip -t "$tmp" 2>/dev/null \
            || { echo "ERROR: not a valid gzip file, not persisted: $src" >&2; rm -f "$tmp"; fail=1; return 1; } ;;
  esac
  if ! mv -f "$tmp" "$dst"; then
    echo "ERROR: could not move into place: $dst (from $src)" >&2; rm -f "$tmp"; fail=1; return 1
  fi
  n=$((n + 1))
}

for seed in 200 201; do
  mkdir -p "$DEST/s$seed" || { echo "ERROR: cannot create $DEST/s$seed" >&2; fail=1; continue; }
  for f in "$SRC"/s$seed/iter-*.json; do
    [ -f "$f" ] && copy_one "$f" "$DEST/s$seed/$(basename "$f")" json
  done
  for f in "$SRC"/s$seed/play-*-*.json.gz; do
    [ -f "$f" ] && copy_one "$f" "$DEST/s$seed/$(basename "$f")" gz
  done
  [ -f "$SRC/s$seed/run.log" ] && copy_one "$SRC/s$seed/run.log" "$DEST/s$seed/run.log" raw
done
for f in "$SRC"/report.json "$SRC"/report.md; do
  if [ -f "$f" ]; then
    case $f in *.json) k=json ;; *) k=raw ;; esac
    copy_one "$f" "$DEST/$(basename "$f")" $k
  fi
done

# read-only checks V1 / V2; stdout saved with the exit code; never fails the persist
mkdir -p "$DEST"
ctmp="$DEST/checks.txt.tmp.$$"
( cd "$REPO" && PYTHONPATH="$REPO" "$PY" -m game.gwls_checks --root "$SRC" ) > "$ctmp" 2> "$ctmp.err"
code=$?
{ echo "gwls_checks exit code: $code"; if [ -s "$ctmp.err" ]; then echo "--- stderr ---"; cat "$ctmp.err"; fi; } >> "$ctmp"
rm -f "$ctmp.err"
if mv -f "$ctmp" "$DEST/checks.txt"; then n=$((n + 1)); else echo "ERROR: could not write $DEST/checks.txt" >&2; rm -f "$ctmp"; fail=1; fi
[ "$code" -ne 0 ] && echo "note: game.gwls_checks exited $code (recorded in checks.txt; not a persist failure)" >&2

echo "persisted $n files from $SRC to $DEST"
[ "$fail" -ne 0 ] && { echo "persist FAILED: at least one file was not persisted (see ERROR lines above)" >&2; exit 1; }
exit 0
