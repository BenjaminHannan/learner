# Re-print checkpoint parts (and result tarballs) that the collector missed, from the part files ck_export.sh left in
# $J/res. Sourced by a queue job with PARTS="job/run:k ..." and optionally RESULTS="job ..."; same line format and pacing
# as ck_export.sh, so vast.py collectck picks them up.
PACE=${PACE:-100}
PFX=${PFX:-rp}      # block-label prefix (see ck_export.sh)
LOG=${LOG:-/proc/1/fd/1}
for r in ${RESULTS:-}; do
  T=$J/res/re-$r.tgz; tar -czf $T --exclude='*.pt' --exclude='stdout.txt' -C $J/w $r 2>/dev/null
  ( flock 9; echo "RBEGIN|$r|$(sha256sum $T | cut -c1-64)|$(stat -c %s $T)"; base64 -w 480 $T | sed "s/^/R|$r|/"; echo "REND|$r" ) 9>$J/print.lock >> $LOG
  sleep 60
done
N=0
for x in ${PARTS:-}; do
  jr=${x%:*}; k=${x##*:}; job=${jr%/*}; run=${jr#*/}
  p=$(printf '%s/res/ck-%s-%s.part.%03d' $J $job $run $k)
  [ -f $p ] || { echo "missing $p"; continue; }
  n=$(ls $J/res/ck-$job-$run.part.* | wc -l); N=$((N + 1)); h=$(sha256sum $p | cut -c1-64)
  ( flock 9; echo "RBEGIN|$PFX$N|$h|$(stat -c %s $p)|$job/$run|$k|$n"; base64 -w 480 $p | sed "s/^/R|$PFX$N|/"; echo "REND|$PFX$N" ) 9>$J/print.lock >> $LOG
  echo "reprinted $jr part $k"
  sleep $PACE
done
echo "CKDONE|$N" >> $LOG
