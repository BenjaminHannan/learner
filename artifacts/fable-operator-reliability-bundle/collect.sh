#!/bin/sh
# Tar the results.  Model checkpoints (final.pt, ~1 MB each) are EXCLUDED unless
# --with-checkpoints is given.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
VARIANT=${VARIANT:-grow-blind}
DIR="artifacts/fable-operator-reliability-$VARIANT-20260920"
OUT=${OUT:-"$HERE/reliability-$VARIANT-results.tar.gz"}
if [ "${1:-}" = "--with-checkpoints" ]; then
  tar -czf "$OUT" -C "$HERE" "$DIR" DONE
else
  tar -czf "$OUT" -C "$HERE" --exclude='*.pt' "$DIR" DONE
fi
echo "$OUT"
ls -l "$OUT"
