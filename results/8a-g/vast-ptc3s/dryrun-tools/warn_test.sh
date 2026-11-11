#!/bin/bash
# the MAXH x DPH warning line of the box script, on three settings
say() { echo "=== $*"; }
for s in "6 0.38" "6 0.9" "6 0"; do
  set -- $s; MAXH=$1; DPH=$2; PROJ_CAP_USD=4.0
  echo "MAXH=$MAXH DPH=$DPH:"
  if [ "$DPH" != 0 ] && [ "$MAXH" != 0 ] && awk "BEGIN{exit !($MAXH * $DPH > $PROJ_CAP_USD + 0.5)}"; then say "WARN MAXH x DPH = $(awk "BEGIN{print $MAXH * $DPH}") USD is above the cap $PROJ_CAP_USD USD plus 0.5: lower MAXH"; fi
done
